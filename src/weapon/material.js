// The viewmodel's look: one physically based material for both guns and the arms, its own small
// environments (day and night) so steel and gold always have something to catch, and the muzzle-flash
// shader.
//
// The material is a MeshStandardMaterial that reads its surface from vertex attributes (build.js):
//   color   albedo
//   mre     x roughness · y metalness · z emissive strength · w finish code
//   rest    where the procedural finish is painted (model space; bind pose for the arms)
// Finishes are evaluated per pixel: brushed steel (streaks along the bore), wood grain, grip
// checkering, skin mottling. No textures.

import * as THREE from 'three';

const VERTEX_HEAD = /* glsl */ `
attribute vec4 mre;
attribute vec3 rest;
varying vec4 vMre;
varying vec3 vRest;
`;

const FRAGMENT_HEAD = /* glsl */ `
varying vec4 vMre;
varying vec3 vRest;
float vmHash(vec2 p) {
  vec3 q = fract(vec3(p.xyx) * 0.1031);
  q += dot(q, q.yzx + 33.33);
  return fract((q.x + q.y) * q.z);
}
float vmNoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(vmHash(i), vmHash(i + vec2(1.0, 0.0)), f.x), mix(vmHash(i + vec2(0.0, 1.0)), vmHash(i + vec2(1.0, 1.0)), f.x), f.y);
}
// x: albedo multiplier, y: roughness offset
vec2 vmFinish(float code, vec3 p) {
  if (code < 0.5) return vec2(1.0, 0.0);
  if (code < 1.5) {
    // Brushed steel: fine streaks that run the length of the part.
    float across = p.x * 1700.0 + p.y * 2300.0;
    float s = vmNoise(vec2(across, p.z * 9.0)) * 0.65 + vmNoise(vec2(across * 0.31, p.z * 3.0)) * 0.35;
    return vec2(0.86 + 0.26 * s, (s - 0.5) * 0.3);
  }
  if (code < 2.5) {
    // Wood: long grain with a slow wander, a few dark pores.
    float wander = vmNoise(p.zy * vec2(14.0, 40.0)) * 3.0;
    float g = vmNoise(vec2(p.x * 520.0 + p.y * 760.0 + wander, p.z * 11.0));
    float fine = vmNoise(vec2(p.x * 2600.0 + p.y * 3400.0, p.z * 60.0));
    float v = g * 0.7 + fine * 0.3;
    return vec2(0.58 + 0.62 * v, (0.5 - v) * 0.25);
  }
  if (code < 3.5) {
    // Checkering: a diagonal diamond grid pressed into the grip.
    vec2 d = vec2(p.y + p.z, p.y - p.z) * 420.0;
    vec2 c = abs(fract(d) - 0.5);
    float groove = smoothstep(0.30, 0.48, max(c.x, c.y));
    return vec2(1.0 - 0.45 * groove, 0.12 * groove);
  }
  if (code < 4.5) {
    // Skin: soft mottling so large areas are not one flat tone.
    float m = vmNoise(p.xz * 160.0 + p.y * 90.0) * 0.6 + vmNoise(p.zy * 520.0 + p.x * 300.0) * 0.4;
    return vec2(0.93 + 0.14 * m, (m - 0.5) * 0.12);
  }
  // Glove: a fine synthetic weave with a slow sheen variation.
  vec2 w = abs(fract(vec2(p.x * 700.0 + p.y * 480.0, p.z * 700.0 - p.y * 220.0)) - 0.5);
  float weave = smoothstep(0.2, 0.45, max(w.x, w.y));
  float m = vmNoise(p.xz * 210.0 + p.y * 140.0);
  return vec2(0.92 + 0.16 * m - 0.05 * weave, 0.05 * weave + (m - 0.5) * 0.1);
}
`;

/** The shared surface material. `environment` is a PMREM texture (see buildEnvironment). */
export function createViewMaterial(environment) {
  const material = new THREE.MeshStandardMaterial({
    vertexColors: true,
    roughness: 1,
    metalness: 1,
    envMap: environment,
    envMapIntensity: 0.55,
  });
  material.name = 'viewmodel';
  material.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>\n${VERTEX_HEAD}`)
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvMre = mre;\nvRest = rest;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>\n${FRAGMENT_HEAD}`)
      .replace(
        '#include <color_fragment>',
        '#include <color_fragment>\nvec2 vmFin = vmFinish(vMre.w, vRest);\ndiffuseColor.rgb *= vmFin.x;',
      )
      .replace(
        '#include <roughnessmap_fragment>',
        '#include <roughnessmap_fragment>\nroughnessFactor = clamp(roughnessFactor * vMre.x + vmFin.y, 0.04, 1.0);',
      )
      .replace('#include <metalnessmap_fragment>', '#include <metalnessmap_fragment>\nmetalnessFactor *= vMre.y;')
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += diffuseColor.rgb * vMre.z;');
  };
  material.customProgramCacheKey = () => 'murderinc-viewmodel';
  return material;
}

/**
 * A light box for the viewmodel only. Reflections are what make blued steel, brushed steel and gold
 * read, and the gun needs them whatever the world's own sky is doing.
 *   night  dark sky, a warm sodium panel overhead, a cool panel behind the shoulder, thin neon strips
 *   day    blue sky over a bright haze line, the sun, sunlit pavement below, brick on one side and the
 *          dark girders of the El overhead (hard dark bands in a bright sky are what polished steel shows)
 */
export function buildEnvironment(renderer, time = 'night') {
  const day = time === 'day';
  const scene = new THREE.Scene();
  const dome = new THREE.SphereGeometry(30, 24, 12);
  const colors = new Float32Array(dome.attributes.position.count * 3);
  const top = day ? new THREE.Color(0.2, 0.42, 0.95).multiplyScalar(1.5) : new THREE.Color(0x0b1326).multiplyScalar(1.6);
  const rim = day ? new THREE.Color(0.78, 0.86, 1).multiplyScalar(2.1) : new THREE.Color(0x3a2a30).multiplyScalar(1.5);
  const floor = day ? new THREE.Color(0.5, 0.46, 0.41).multiplyScalar(0.95) : new THREE.Color(0x1a1410);
  const tint = new THREE.Color();
  for (let i = 0; i < colors.length / 3; i++) {
    const h = dome.attributes.position.getY(i) / 30;
    if (h >= 0) tint.lerpColors(rim, top, Math.min(1, h * (day ? 1.5 : 2.2)));
    else tint.lerpColors(rim, floor, Math.min(1, -h * 4));
    tint.toArray(colors, i * 3);
  }
  dome.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  const sky = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide });
  scene.add(new THREE.Mesh(dome, sky));

  const made = [dome, sky];
  /** A glowing panel of w × h facing the origin from `at`. */
  const panel = (hex, gain, at, w, h) => {
    const geo = new THREE.PlaneGeometry(w, h);
    const mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(hex).multiplyScalar(gain), side: THREE.DoubleSide });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(at[0], at[1], at[2]);
    mesh.lookAt(0, 0, 0);
    scene.add(mesh);
    made.push(geo, mat);
  };
  if (day) {
    panel(0xfff1d6, 42, [7, 20, 6], 5, 5); // the sun, high and a little behind the right shoulder
    panel(0xffffff, 3.2, [-14, 9, -12], 9, 5); // a bright cumulus
    panel(0x8a3b2a, 0.9, [22, 5, -3], 30, 16); // sunlit brick, right
    panel(0x2a2d33, 0.5, [-22, 4, 4], 26, 12); // a shaded facade, left
    for (const z of [-11, -2, 7]) panel(0x14161a, 0.6, [0, 17, z], 44, 1.7); // El girders across the sky
  } else {
    panel(0xffb45e, 18, [3, 16, -6], 9, 5); // sodium lamp, ahead and above
    panel(0xffc890, 8, [-12, 12, 8], 8, 8); // a second lamp behind the left shoulder
    panel(0x9fc0ff, 4, [-16, 6, -4], 10, 12); // cool sky fill from the left
    panel(0xff3d9a, 2.5, [18, 2, -10], 1.2, 8); // neon, right
    panel(0x35e0ff, 2.5, [-10, 1.5, -18], 10, 1.0); // neon, far left ahead
    panel(0xf6c21a, 3, [8, 3, 16], 6, 2.5); // taxi-yellow shop light behind
  }

  const pmrem = new THREE.PMREMGenerator(renderer);
  const target = pmrem.fromScene(scene, 0.035);
  pmrem.dispose();
  for (const item of made) item.dispose();
  return target.texture;
}

/**
 * Muzzle flash: additive, HDR, shaped in the shader. Each quad carries `kind` (0 = the star seen from
 * behind the gun, 1 = the jet seen from the side) and unit UVs centred on the muzzle.
 */
export function createFlashMaterial() {
  return new THREE.ShaderMaterial({
    name: 'muzzle-flash',
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    uniforms: {
      uSeed: { value: 0 },
      uPower: { value: 0 }, // 0…1, falls over the life of the flash
      uJet: { value: 1 }, // forward jet strength (1 Chopper, 0.25 Nine)
    },
    vertexShader: /* glsl */ `
      attribute float kind;
      varying vec2 vUv;
      varying float vKind;
      void main() {
        vUv = uv;
        vKind = kind;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: /* glsl */ `
      uniform float uSeed;
      uniform float uPower;
      uniform float uJet;
      varying vec2 vUv;
      varying float vKind;
      float hash(float n) { return fract(sin(n * 91.345 + uSeed * 7.13) * 47453.5453); }
      void main() {
        vec2 p = vUv * 2.0 - 1.0;
        float glow;
        if (vKind < 0.5) {
          // Star: a hot core and five or six uneven petals.
          float r = length(p);
          float a = atan(p.y, p.x);
          float petals = 0.0;
          for (int i = 0; i < 6; i++) {
            float dir = hash(float(i)) * 6.2831853;
            float len = 0.45 + 0.55 * hash(float(i) + 11.0);
            float d = abs(sin((a - dir) * 0.5));
            petals += smoothstep(0.22, 0.0, d) * smoothstep(len, len * 0.15, r);
          }
          glow = exp(-r * r * 9.0) * 1.6 + petals * 0.9 * (1.0 - r);
          glow *= smoothstep(1.0, 0.7, r);
        } else {
          // Jet: a teardrop along +u, widest just ahead of the muzzle.
          float u = vUv.x;
          float width = 0.07 + 0.30 * u * (1.0 - u) * (0.7 + 0.6 * hash(3.0));
          float core = exp(-pow(p.y / width, 2.0));
          glow = core * smoothstep(1.0, 0.25, u) * smoothstep(0.0, 0.06, u) * 1.5 * uJet;
        }
        vec3 hot = vec3(1.0, 0.93, 0.74);
        vec3 edge = vec3(1.0, 0.42, 0.08);
        vec3 col = mix(edge, hot, clamp(glow * 0.75, 0.0, 1.0)) * glow * uPower * 9.0;
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}
