// Decal ring buffer: bullet holes and scorch marks as instanced quads laid flat on the surface they hit.
//
// A decal is a point, the surface normal, a size, a roll about the normal and an atlas cell. The vertex
// shader builds the surface basis from the normal (so it is right on walls, floors and ceilings alike)
// and shades the mark with the same sampled ambient + key as the smoke: a pale chip is never brighter
// than the wall around it. The newest decal overwrites the oldest.

import * as THREE from 'three';
import { COLS, ROWS } from './atlas.js';
import { DEPTH_BIAS_GLSL, FOG_GLSL } from './shared.js';

const INSTANCE = 12; // xyz + size, normal xyz + roll, cell + opacity + key share + spare
// Metres off the surface, on top of the polygon offset. Floors get more: road markings and pavement
// overlays tend to sit a couple of centimetres above the collision plane a round is reported on.
const LIFT_WALL = 0.008;
const LIFT_FLOOR = 0.035;

/** The two in-plane axes of a decal for a unit normal (exported for tests; mirrors the shader). */
export function decalBasis(nx, ny, nz, tangent, bitangent) {
  if (Math.abs(ny) > 0.99) {
    // Floors and ceilings: world X is as good a tangent as any.
    tangent.set(1, 0, 0);
  } else {
    // Walls: horizontal tangent, so an unrolled decal stands upright.
    const len = Math.hypot(nz, nx);
    tangent.set(nz / len, 0, -nx / len);
  }
  bitangent.set(
    ny * tangent.z - nz * tangent.y,
    nz * tangent.x - nx * tangent.z,
    nx * tangent.y - ny * tangent.x,
  );
}

const VERTEX = /* glsl */ `
  attribute vec4 iPos;   // xyz, size
  attribute vec4 iNrm;   // normal, roll
  attribute vec4 iInfo;  // atlas cell, opacity, key share

  uniform vec4 uFog;
  uniform vec3 uSky;
  uniform vec3 uGround;
  uniform vec3 uKey;
  uniform vec3 uKeyDir;

  varying vec2 vUv;
  varying vec4 vLight; // rgb light, a opacity
  varying float vFog;

  ${FOG_GLSL}
  ${DEPTH_BIAS_GLSL}

  void main() {
    vec3 n = iNrm.xyz;
    vec3 t = abs(n.y) > 0.99 ? vec3(1.0, 0.0, 0.0) : normalize(vec3(n.z, 0.0, -n.x));
    vec3 b = cross(n, t);
    float sn = sin(iNrm.w);
    float cs = cos(iNrm.w);
    vec2 c = vec2(position.x * cs - position.y * sn, position.x * sn + position.y * cs) * iPos.w;
    vec3 world = iPos.xyz + t * c.x + b * c.y + n * (n.y > 0.7 ? ${LIFT_FLOOR.toFixed(4)} : ${LIFT_WALL.toFixed(4)});
    vec4 mv = viewMatrix * vec4(world, 1.0);
    gl_Position = projectionMatrix * mv;
    // Drawn where it is, depth-tested a few centimetres nearer: the drawn wall or pavement rarely lies
    // exactly on the collision box the round was reported on (relief, kerbs, slabs, paint).
    fxDepthBias(mv, 0.07 + 0.003 * -mv.z);

    vec3 light = mix(uGround, uSky, n.y * 0.5 + 0.5) + uKey * (max(dot(n, uKeyDir), 0.0) * iInfo.z);
    vLight = vec4(light * 0.31831, iInfo.y);
    float f = floor(iInfo.x + 0.5);
    vUv = (vec2(mod(f, ${COLS}.0), floor(f / ${COLS}.0)) + clamp(position.xy + 0.5, 0.004, 0.996)) / vec2(${COLS}.0, ${ROWS}.0);
    vFog = fxFog(-mv.z);
  }
`;

const FRAGMENT = /* glsl */ `
  uniform sampler2D map;
  uniform vec3 uFogColor;

  varying vec2 vUv;
  varying vec4 vLight;
  varying float vFog;

  void main() {
    vec4 texel = texture2D(map, vUv);
    float alpha = texel.a * vLight.a;
    vec3 color = mix(texel.rgb * vLight.rgb, uFogColor, vFog);
    gl_FragColor = vec4(color * alpha, alpha); // premultiplied
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

export function createDecals({ capacity, texture, common, renderOrder }) {
  const geometry = new THREE.InstancedBufferGeometry();
  geometry.setAttribute(
    'position',
    new THREE.BufferAttribute(new Float32Array([-0.5, -0.5, 0, 0.5, -0.5, 0, 0.5, 0.5, 0, -0.5, 0.5, 0]), 3),
  );
  geometry.setIndex([0, 1, 2, 0, 2, 3]);
  const array = new Float32Array(capacity * INSTANCE);
  const buffer = new THREE.InstancedInterleavedBuffer(array, INSTANCE, 1).setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute('iPos', new THREE.InterleavedBufferAttribute(buffer, 4, 0));
  geometry.setAttribute('iNrm', new THREE.InterleavedBufferAttribute(buffer, 4, 4));
  geometry.setAttribute('iInfo', new THREE.InterleavedBufferAttribute(buffer, 4, 8));
  geometry.instanceCount = 0;

  const material = new THREE.ShaderMaterial({
    name: 'fx-decals',
    uniforms: {
      map: { value: texture },
      uFog: common.uFog,
      uFogColor: common.uFogColor,
      uSky: common.uSky,
      uGround: common.uGround,
      uKey: common.uKey,
      uKeyDir: common.uKeyDir,
    },
    vertexShader: VERTEX,
    fragmentShader: FRAGMENT,
    transparent: true,
    depthWrite: false,
    premultipliedAlpha: true,
    side: THREE.DoubleSide,
    forceSinglePass: true,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -4,
    fog: false,
  });

  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = 'fx-decals';
  mesh.frustumCulled = false;
  mesh.renderOrder = renderOrder;
  mesh.visible = false;
  mesh.matrixAutoUpdate = false;

  let next = 0; // slot the next decal goes into
  let used = 0; // slots that have ever been written (≤ capacity)
  let live = 0; // decals on show
  let total = 0; // decals ever placed

  /**
   * Places a decal. `normal` must be a unit vector; `roll` turns the mark about it; `shade` is how much
   * of the key light the spot receives (0 in shadow or indoors).
   */
  function add(x, y, z, nx, ny, nz, size, roll, cell, opacity, shade) {
    const o = next * INSTANCE;
    if (used === capacity) {
      if (array[o + 9] <= 0) live++; // the slot it replaces had been wiped
    } else {
      used++;
      live++;
    }
    array[o] = x;
    array[o + 1] = y;
    array[o + 2] = z;
    array[o + 3] = size;
    array[o + 4] = nx;
    array[o + 5] = ny;
    array[o + 6] = nz;
    array[o + 7] = roll;
    array[o + 8] = cell;
    array[o + 9] = opacity;
    array[o + 10] = shade;
    array[o + 11] = 0;
    next = (next + 1) % capacity;
    total++;
    geometry.instanceCount = used;
    mesh.visible = true;
    buffer.needsUpdate = true;
  }

  /**
   * Wipes the decals within `radius` of a point (the thing they were on is gone). Marks of `keepFrom`
   * metres and more (blast scorches on the ground) stay.
   */
  function removeNear(x, y, z, radius, keepFrom = Infinity) {
    const r2 = radius * radius;
    let changed = false;
    for (let i = 0; i < used; i++) {
      const o = i * INSTANCE;
      if (array[o + 9] <= 0 || array[o + 3] >= keepFrom) continue;
      const dx = array[o] - x;
      const dy = array[o + 1] - y;
      const dz = array[o + 2] - z;
      if (dx * dx + dy * dy + dz * dz > r2) continue;
      array[o + 9] = 0;
      array[o + 3] = 0;
      live--;
      changed = true;
    }
    if (changed) buffer.needsUpdate = true;
  }

  function clear() {
    next = used = live = 0;
    geometry.instanceCount = 0;
    mesh.visible = false;
  }

  return {
    mesh,
    capacity,
    add,
    removeNear,
    clear,
    get count() {
      return live;
    },
    get total() {
      return total;
    },
  };
}
