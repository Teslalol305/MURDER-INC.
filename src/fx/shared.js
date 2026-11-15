// What every effect material has in common: fog, the sampled scene light, a small PRNG and colour helpers.

import * as THREE from 'three';

/** Up to this many effect lights (blasts, fires) shine on the lit particles. */
export const FX_LIGHTS = 4;

/**
 * One set of uniform objects shared by all effect materials: assign a value once and every shader sees
 * it. Light values follow three.js conventions (colour × intensity; the shaders divide by π).
 */
export function createCommonUniforms() {
  const lightPos = [];
  const lightCol = [];
  for (let i = 0; i < FX_LIGHTS; i++) {
    lightPos.push(new THREE.Vector4(0, -1000, 0, 1)); // xyz, range
    lightCol.push(new THREE.Vector3());
  }
  return {
    uFog: { value: new THREE.Vector4(0, 0, 1, 0) }, // density, near, far, mode (0 none, 1 exp², 2 linear)
    uFogColor: { value: new THREE.Color(0, 0, 0) },
    uSky: { value: new THREE.Color(0.2, 0.25, 0.4) }, // ambient from above
    uGround: { value: new THREE.Color(0.1, 0.08, 0.06) }, // ambient from below
    uKey: { value: new THREE.Color(1, 0.7, 0.4) },
    uKeyDir: { value: new THREE.Vector3(0.3, 0.9, 0.3) }, // toward the key light
    uLightPos: { value: lightPos },
    uLightCol: { value: lightCol },
    uPixel: { value: 0.002 }, // world size of the thinnest drawable line at distance 1
    uDay: { value: 0 }, // 0 at night … 1 in sunlight: glowing effects get a body that hides what is behind them
  };
}

/** GLSL: fog factor for a view-space distance. Needs `uniform vec4 uFog`. */
export const FOG_GLSL = /* glsl */ `
  float fxFog(float dist) {
    if (uFog.w > 1.5) return smoothstep(uFog.y, uFog.z, dist);
    if (uFog.w > 0.5) return 1.0 - exp(-uFog.x * uFog.x * dist * dist);
    return 0.0;
  }
`;

/**
 * GLSL: lets a billboard win the depth test against geometry it would otherwise be cut by. The quad is
 * drawn where it is, but tested as if it were up to `bias` metres nearer (never past the near plane).
 */
export const DEPTH_BIAS_GLSL = /* glsl */ `
  void fxDepthBias(vec4 mv, float bias) {
    bias = min(bias, max(0.0, -mv.z - 0.25));
    vec4 nearer = projectionMatrix * vec4(mv.xy, mv.z + bias, 1.0);
    gl_Position.z = nearer.z / nearer.w * gl_Position.w;
  }
`;

/** Copies the scene's fog into the shared uniforms (none, FogExp2 or Fog). */
export function readFog(common, scene) {
  const fog = scene && scene.fog;
  const u = common.uFog.value;
  if (!fog) {
    u.w = 0;
    return;
  }
  common.uFogColor.value.copy(fog.color);
  if (fog.isFogExp2) u.set(fog.density, 0, 1, 1);
  else u.set(0, fog.near, fog.far, 2);
}

/**
 * Finds what lights the scene: hemisphere / ambient lights and the key (atmos.sun, or the strongest
 * directional light). Returns a function that copies their current values into the shared uniforms;
 * call it now and then, lights may be retuned at runtime.
 */
export function createLightSampler(common, scene, getKey) {
  const ambients = [];
  let fallbackKey = null;
  const tint = new THREE.Color();
  const dir = new THREE.Vector3();
  const target = new THREE.Vector3();

  function scan() {
    ambients.length = 0;
    fallbackKey = null;
    scene.traverse((obj) => {
      if (obj.isHemisphereLight || obj.isAmbientLight) ambients.push(obj);
      else if (obj.isDirectionalLight && (!fallbackKey || obj.intensity > fallbackKey.intensity)) fallbackKey = obj;
    });
  }

  function sample() {
    const sky = common.uSky.value.setRGB(0, 0, 0);
    const ground = common.uGround.value.setRGB(0, 0, 0);
    for (let i = 0; i < ambients.length; i++) {
      const light = ambients[i];
      if (!light.visible) continue;
      tint.copy(light.color).multiplyScalar(light.intensity);
      sky.add(tint);
      if (light.isHemisphereLight) tint.copy(light.groundColor).multiplyScalar(light.intensity);
      ground.add(tint);
    }
    const key = getKey() || fallbackKey;
    if (key && key.visible !== false) {
      common.uKey.value.copy(key.color).multiplyScalar(key.intensity);
      key.getWorldPosition(dir);
      if (key.target) dir.sub(key.target.getWorldPosition(target));
      if (dir.lengthSq() > 1e-8) common.uKeyDir.value.copy(dir).normalize();
    } else {
      common.uKey.value.setRGB(0, 0, 0);
    }
  }

  return { scan, sample };
}

/**
 * Small deterministic PRNG for cosmetics (mulberry32): the same run draws the same sparks.
 * The state sits in a typed array: a closure variable would box every new value on the heap.
 */
export function createRandom(seed = 0x2f6e2b1) {
  const state = new Int32Array([seed]);
  const next = () => {
    let t = (state[0] = (state[0] + 0x6d2b79f5) | 0);
    t = Math.imul(t ^ (t >>> 15), 1 | t);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  next.range = (a, b) => a + (b - a) * next();
  next.signed = () => next() * 2 - 1;
  return next;
}

const scratch = new THREE.Color();

/** Linear RGB of a hex colour as a plain [r, g, b] (for recipe tables built at load). */
export function rgb(hex, scale = 1) {
  scratch.set(hex);
  return [scratch.r * scale, scratch.g * scale, scratch.b * scale];
}

/** A DataTexture for one of the atlas sheets (linear data, mip-mapped). */
export function sheetTexture(sheet, name) {
  const texture = new THREE.DataTexture(sheet.data, sheet.width, sheet.height, THREE.RGBAFormat, THREE.UnsignedByteType);
  texture.name = name;
  texture.colorSpace = THREE.NoColorSpace;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.wrapS = texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.needsUpdate = true;
  return texture;
}
