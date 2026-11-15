// The two billboard pools as instanced quads: one draw call each.
//
//   lit       alpha blended, drawn back to front; shaded per vertex from the sampled scene light
//             (sky / ground ambient + key + nearby effect lights) so smoke sits in the night instead of
//             glowing in it; particles carry `heat` (a glow in their dense core that cools quickly)
//   additive  unsorted, HDR: sparks, flashes, embers, fire; velocity-stretched streaks when asked for
//
// Instance layout (fx/sim.js writeInstances): 4 × vec4
//   iPos   xyz centre, w size (m)
//   iCol   rgb, a opacity / intensity
//   iMisc  rotation, atlas cell, shade, heat
//   iAxis  xyz streak (velocity × stretch), w floor height

import * as THREE from 'three';
import { COLS, ROWS } from './atlas.js';
import { INSTANCE } from './sim.js';
import { DEPTH_BIAS_GLSL, FOG_GLSL, FX_LIGHTS } from './shared.js';

const ATLAS_GLSL = /* glsl */ `
  vec2 atlasUv(float cell, vec2 corner) {
    float f = floor(cell + 0.5);
    vec2 at = vec2(mod(f, ${COLS}.0), floor(f / ${COLS}.0));
    return (at + clamp(corner + 0.5, 0.004, 0.996)) / vec2(${COLS}.0, ${ROWS}.0);
  }
`;

const LIT_VERTEX = /* glsl */ `
  attribute vec4 iPos;
  attribute vec4 iCol;
  attribute vec4 iMisc;
  attribute vec4 iAxis;

  uniform vec4 uFog;
  uniform vec3 uSky;
  uniform vec3 uGround;
  uniform vec3 uKey;
  uniform vec3 uKeyDir;
  uniform vec4 uLightPos[${FX_LIGHTS}];
  uniform vec3 uLightCol[${FX_LIGHTS}];
  uniform vec3 uHeat;
  uniform float uBias;

  varying vec2 vUv;
  varying vec4 vColor;
  varying vec3 vGlow;
  varying float vGround;
  varying float vFog;

  ${FOG_GLSL}
  ${ATLAS_GLSL}
  ${DEPTH_BIAS_GLSL}

  void main() {
    float size = iPos.w;
    float sn = sin(iMisc.x);
    float cs = cos(iMisc.x);
    vec2 c = vec2(position.x * cs - position.y * sn, position.x * sn + position.y * cs);

    vec4 mv = modelViewMatrix * vec4(iPos.xyz, 1.0);
    mv.xy += c * size;
    gl_Position = projectionMatrix * mv;
    fxDepthBias(mv, min(size * 0.5, uBias));

    // The camera's axes in world space: the billboard's plane, and the way back to the eye.
    vec3 right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
    vec3 up = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
    vec3 back = vec3(viewMatrix[0][2], viewMatrix[1][2], viewMatrix[2][2]);
    vec3 world = iPos.xyz + (right * c.x + up * c.y) * size;
    // Pretend the quad is a ball: corners lean outward, so the top catches the key and the bottom the street.
    vec3 n = normalize(back + (right * c.x + up * c.y) * 1.1);

    vec3 light = mix(uGround, uSky, n.y * 0.5 + 0.5);
    float wrap = max(dot(n, uKeyDir) * 0.6 + 0.4, 0.0);
    light += uKey * (wrap * wrap * iMisc.z);
    for (int i = 0; i < ${FX_LIGHTS}; i++) {
      vec3 d = uLightPos[i].xyz - world;
      float d2 = dot(d, d);
      float reach = clamp(1.0 - d2 / (uLightPos[i].w * uLightPos[i].w), 0.0, 1.0);
      float facing = dot(n, d) * inversesqrt(d2 + 0.0001) * 0.5 + 0.5;
      light += uLightCol[i] * (reach * reach / (d2 + 1.0) * (0.3 + 0.7 * facing));
    }

    vColor = vec4(iCol.rgb * light * 0.31831, iCol.a);
    vGlow = uHeat * iMisc.w;
    vUv = atlasUv(iMisc.y, position.xy);
    // Fades the part of the quad that dips into the ground it stands on, instead of a hard cut.
    vGround = (world.y - iAxis.w) / (0.3 * size) + 0.15;
    vFog = fxFog(-mv.z);
  }
`;

const LIT_FRAGMENT = /* glsl */ `
  uniform sampler2D map;
  uniform vec3 uFogColor;

  varying vec2 vUv;
  varying vec4 vColor;
  varying vec3 vGlow;
  varying float vGround;
  varying float vFog;

  void main() {
    vec4 texel = texture2D(map, vUv);
    float alpha = texel.r * vColor.a * clamp(vGround, 0.0, 1.0);
    vec3 color = vColor.rgb * (0.4 + 0.85 * texel.g) + vGlow * (texel.r * texel.r);
    color = mix(color, uFogColor, vFog);
    gl_FragColor = vec4(color * alpha, alpha); // premultiplied
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

const ADD_VERTEX = /* glsl */ `
  attribute vec4 iPos;
  attribute vec4 iCol;
  attribute vec4 iMisc;
  attribute vec4 iAxis;

  uniform vec4 uFog;
  uniform float uPixel;
  uniform float uBias;
  uniform float uWorld; // 1: world-space pool (ground fade, fog); 0: view-space pool on the viewmodel

  varying vec2 vUv;
  varying vec3 vColor;
  varying float vGround;

  ${FOG_GLSL}
  ${ATLAS_GLSL}
  ${DEPTH_BIAS_GLSL}

  void main() {
    vec4 mv = modelViewMatrix * vec4(iPos.xyz, 1.0);
    // Never thinner than a pixel and a bit: a spark across the avenue must not flicker in and out.
    float size = max(iPos.w, -mv.z * uPixel);
    float gain = sqrt(iPos.w / size);

    vec3 axis = (modelViewMatrix * vec4(iAxis.xyz, 0.0)).xyz;
    float len2 = dot(axis, axis);
    vGround = 1.0;
    if (len2 > 1e-10) {
      // A streak: the particle is the head, the tail trails back along the velocity.
      vec3 side = cross(mv.xyz, axis);
      float sl = length(side);
      side = sl > 1e-6 ? side / sl : vec3(1.0, 0.0, 0.0);
      vec3 ahead = axis * inversesqrt(len2);
      mv.xyz += side * (position.x * size) + axis * (position.y - 0.5) + ahead * (position.y * size);
    } else {
      float sn = sin(iMisc.x);
      float cs = cos(iMisc.x);
      vec2 c = vec2(position.x * cs - position.y * sn, position.x * sn + position.y * cs);
      mv.xy += c * size;
      float upY = viewMatrix[1][1] * c.y + viewMatrix[1][0] * c.x;
      vGround = mix(1.0, (iPos.y + upY * size - iAxis.w) / (0.3 * size) + 0.15, uWorld);
    }
    gl_Position = projectionMatrix * mv;
    fxDepthBias(mv, min(size * 0.5, uBias));

    vColor = iCol.rgb * (iCol.a * gain * (1.0 - fxFog(-mv.z) * uWorld));
    vUv = atlasUv(iMisc.y, position.xy);
  }
`;

const ADD_FRAGMENT = /* glsl */ `
  uniform sampler2D map;

  varying vec2 vUv;
  varying vec3 vColor;
  varying float vGround;

  void main() {
    vec4 texel = texture2D(map, vUv);
    // The texture's second channel is the white-hot core.
    vec3 color = vColor * texel.r + vec3(dot(vColor, vec3(0.3333))) * texel.g * 0.7;
    gl_FragColor = vec4(color * clamp(vGround, 0.0, 1.0), 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

/** One quad, instanced `capacity` times from a single interleaved buffer. */
function instancedQuad(capacity) {
  const geometry = new THREE.InstancedBufferGeometry();
  geometry.setAttribute(
    'position',
    new THREE.BufferAttribute(new Float32Array([-0.5, -0.5, 0, 0.5, -0.5, 0, 0.5, 0.5, 0, -0.5, 0.5, 0]), 3),
  );
  geometry.setIndex([0, 1, 2, 0, 2, 3]);
  const array = new Float32Array(capacity * INSTANCE);
  const buffer = new THREE.InstancedInterleavedBuffer(array, INSTANCE, 1).setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute('iPos', new THREE.InterleavedBufferAttribute(buffer, 4, 0));
  geometry.setAttribute('iCol', new THREE.InterleavedBufferAttribute(buffer, 4, 4));
  geometry.setAttribute('iMisc', new THREE.InterleavedBufferAttribute(buffer, 4, 8));
  geometry.setAttribute('iAxis', new THREE.InterleavedBufferAttribute(buffer, 4, 12));
  geometry.instanceCount = 0;
  return { geometry, buffer, array };
}

/**
 * A drawable pool. `kind` is 'lit' or 'additive'; `space` is 'world' (a mesh for the scene) or 'view'
 * (additive only: positions are relative to the camera it is parented to).
 */
export function createPoolMesh({ kind, capacity, texture, common, name, renderOrder, space = 'world' }) {
  const { geometry, buffer, array } = instancedQuad(capacity);
  const lit = kind === 'lit';
  const world = space === 'world';

  const uniforms = { map: { value: texture }, uFog: common.uFog, uBias: { value: world ? 0.45 : 0 } };
  if (lit) {
    Object.assign(uniforms, {
      uFogColor: common.uFogColor,
      uSky: common.uSky,
      uGround: common.uGround,
      uKey: common.uKey,
      uKeyDir: common.uKeyDir,
      uLightPos: common.uLightPos,
      uLightCol: common.uLightCol,
      uHeat: { value: new THREE.Vector3(2.2, 0.55, 0.07) }, // the glow inside fresh blast smoke
    });
  } else {
    uniforms.uPixel = common.uPixel;
    uniforms.uWorld = { value: world ? 1 : 0 };
  }

  const material = new THREE.ShaderMaterial({
    name,
    uniforms,
    vertexShader: lit ? LIT_VERTEX : ADD_VERTEX,
    fragmentShader: lit ? LIT_FRAGMENT : ADD_FRAGMENT,
    transparent: true,
    depthWrite: false,
    depthTest: world, // the viewmodel pool always draws over the weapon
    blending: lit ? THREE.NormalBlending : THREE.AdditiveBlending,
    premultipliedAlpha: true,
    side: THREE.DoubleSide, // streaks may turn either face to the eye…
    forceSinglePass: true, // …and are still drawn once
    fog: false,
  });

  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = name;
  mesh.frustumCulled = false; // instances move every frame; the pool is everywhere
  mesh.renderOrder = renderOrder;
  mesh.visible = false;
  mesh.matrixAutoUpdate = false;

  const range = { start: 0, count: 0 }; // reused: one upload range per frame, no garbage

  return {
    mesh,
    array,
    /** Call after writing `count` instances into `array`. */
    commit(count) {
      geometry.instanceCount = count;
      mesh.visible = count > 0;
      if (count === 0) return;
      range.count = count * INSTANCE;
      if (buffer.updateRanges.length === 0) buffer.updateRanges.push(range);
      buffer.needsUpdate = true;
    },
  };
}
