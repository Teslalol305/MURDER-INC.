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
// x: albedo multiplier, y: roughness offset. Frequencies are per metre in model space: the gun is seen
// from 0.2-0.6 m, where a pixel is about half a millimetre, so nothing here repeats finer than ~2 mm.
vec2 vmFinish(float code, vec3 p) {
  if (code < 0.5) return vec2(1.0, 0.0);
  if (code > 5.5) {
    // Blued steel: uneven bluing and handling marks (a slow mottle in tone and gloss) over faint
    // machining lines along the bore, so a flat face never reflects as one flat colour.
    float m = vmNoise(p.zy * vec2(28.0, 40.0) + p.x * 31.0) * 0.6 + vmNoise(p.zx * vec2(90.0, 70.0) + p.y * 80.0) * 0.4;
    float lines = vmNoise(vec2(p.y * 900.0 + p.x * 700.0, p.z * 3.0));
    return vec2(0.86 + 0.26 * m + 0.03 * lines, (0.5 - m) * 0.16 + (lines - 0.5) * 0.04);
  }
  if (code < 1.5) {
    // Brushed steel: streaks that run the length of the part.
    float across = p.x * 560.0 + p.y * 760.0;
    float s = vmNoise(vec2(across, p.z * 6.0)) * 0.65 + vmNoise(vec2(across * 0.31, p.z * 2.0)) * 0.35;
    return vec2(0.84 + 0.3 * s, (s - 0.5) * 0.3);
  }
  if (code < 2.5) {
    // Wood: long grain with a slow wander, darker late-wood lines and a few pores.
    float wander = vmNoise(p.zy * vec2(5.0, 14.0)) * 2.5 + vmNoise(p.zx * vec2(9.0, 30.0)) * 0.8;
    float g = vmNoise(vec2(p.x * 150.0 + p.y * 210.0 + wander, p.z * 5.0));
    float lines = smoothstep(0.55, 0.8, fract(g * 3.0 + wander * 0.5)) * smoothstep(0.25, 0.6, g);
    float fine = vmNoise(vec2(p.x * 700.0 + p.y * 900.0, p.z * 18.0));
    float v = g * 0.55 + fine * 0.2 + 0.25 - 0.6 * lines;
    return vec2(0.42 + 0.85 * v, (0.5 - v) * 0.3 + 0.12 * lines);
  }
  if (code < 3.5) {
    // Checkering: a diagonal diamond grid pressed into the grip.
    vec2 d = vec2(p.y + p.z, p.y - p.z) * 300.0;
    vec2 c = abs(fract(d) - 0.5);
    float groove = smoothstep(0.30, 0.48, max(c.x, c.y));
    return vec2(1.0 - 0.5 * groove, 0.14 * groove);
  }
  if (code < 4.5) {
    // Skin: soft mottling so large areas are not one flat tone.
    float m = vmNoise(p.xz * 70.0 + p.y * 40.0) * 0.6 + vmNoise(p.zy * 200.0 + p.x * 120.0) * 0.4;
    return vec2(0.92 + 0.16 * m, (m - 0.5) * 0.14);
  }
  // Glove: synthetic leather with a slow sheen variation and a faint grain.
  vec2 w = abs(fract(vec2(p.x * 300.0 + p.y * 200.0, p.z * 300.0 - p.y * 90.0)) - 0.5);
  float weave = smoothstep(0.2, 0.45, max(w.x, w.y));
  float m = vmNoise(p.xz * 90.0 + p.y * 60.0);
  return vec2(0.9 + 0.2 * m - 0.06 * weave, 0.06 * weave + (m - 0.5) * 0.16);
}
`;

/** Finish code for blued steel (after build.js FINISH, which stops at glove = 5). */
export const FINISH_BLUED = 6;

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
 *   day    the avenue at 4 PM in world orientation (the avenue runs along X): a blue sky with the sun
 *          and a cloud, the dark girders of the El overhead, a sunlit brick row on one side and a
 *          shaded one with bright windows on the other, the hazy vista down the street both ways,
 *          and pavement striped with shadow. Radiances sit near the street's own, so a steel face
 *          turned up shows sky, a face turned sideways the darker buildings, and every bevel between
 *          the two catches a bright line: the form of the gun.
 * `sun` is the direction the day light travels (config/look.js times.day.sun.direction).
 */
export function buildEnvironment(renderer, time = 'night', sun = [0.553, -0.788, -0.271]) {
  const day = time === 'day';
  const scene = new THREE.Scene();
  const dome = new THREE.SphereGeometry(30, 32, 16);
  const colors = new Float32Array(dome.attributes.position.count * 3);
  const top = day ? new THREE.Color(0.16, 0.34, 0.9) : new THREE.Color(0x0b1326).multiplyScalar(1.6);
  const rim = day ? new THREE.Color(0.9, 0.95, 1.05) : new THREE.Color(0x3a2a30).multiplyScalar(1.5);
  const floor = day ? new THREE.Color(0.36, 0.32, 0.28) : new THREE.Color(0x1a1410);
  const tint = new THREE.Color();
  for (let i = 0; i < colors.length / 3; i++) {
    const h = dome.attributes.position.getY(i) / 30;
    if (h >= 0) tint.lerpColors(rim, top, Math.min(1, Math.pow(h, day ? 0.6 : 1) * (day ? 1.1 : 2.2)));
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
    return mesh;
  };
  /** The same with a linear colour [r, g, b]. */
  const glow = (rgb, at, w, h) => {
    const mesh = panel(0xffffff, 1, at, w, h);
    mesh.material.color.setRGB(rgb[0], rgb[1], rgb[2]);
    return mesh;
  };
  /** A horizontal panel w (along X) × d (along Z) at height y, facing the origin. */
  const flat = (rgb, x, y, z, w, d) => {
    const mesh = glow(rgb, [x, y, z], w, d);
    mesh.rotation.set(y > 0 ? Math.PI / 2 : -Math.PI / 2, 0, 0);
    return mesh;
  };
  if (day) {
    const toSun = new THREE.Vector3(-sun[0], -sun[1], -sun[2]).normalize();
    glow([42, 39, 33], toSun.clone().multiplyScalar(24).toArray(), 2.6, 2.6); // the sun
    glow([1.7, 1.7, 1.75], [-13, 14, 12], 10, 4); // a bright cumulus
    glow([1.4, 1.4, 1.5], [9, 16, -10], 7, 3);
    // The two rows of buildings, along X: the north side faces the sun, the south side is in shade.
    const north = Math.sign(sun[2]) || -1; // the light travels this way along Z: that side is lit
    glow([0.3, 0.19, 0.14], [0, 6.5, 18 * north], 70, 17); // sunlit brick
    for (const x of [-21, -13, -5, 3, 11, 19]) {
      glow([0.05, 0.055, 0.065], [x, 8.5, 17.6 * north], 3.2, 2.2); // its windows (dark glass)
      glow([0.05, 0.055, 0.065], [x, 3.5, 17.6 * north], 3.2, 2.2);
    }
    glow([0.06, 0.065, 0.075], [0, 6.5, -18 * north], 70, 17); // the shaded row
    for (const x of [-18, -8, 2, 12, 22]) glow([0.55, 0.62, 0.75], [x, 7, -17.6 * north], 3, 2.2); // sky in its windows
    glow([0.14, 0.13, 0.12], [0, 1, -17.5 * north], 70, 2.6); // shop fronts and awnings
    // The El overhead: two dark girders along the avenue and the cross ties between them.
    for (const z of [-5, 5]) flat([0.025, 0.027, 0.03], 0, 16, z, 60, 2.2);
    for (const x of [-16, -6, 4, 14]) flat([0.03, 0.032, 0.035], x, 16.5, 0, 1.4, 12);
    // Pavement: sunlit, with the El's shadow lying across it in stripes.
    for (const x of [-15, -5, 5, 15]) flat([0.06, 0.06, 0.065], x, -8, 0, 4, 40);
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
    forceSinglePass: true, // additive and unlit: one pass looks the same and skips a program rebuild
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
