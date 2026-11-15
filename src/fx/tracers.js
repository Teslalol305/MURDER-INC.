// Pooled tracers: a streak that travels from the muzzle to where the shot landed.
//
// The simulation is a handful of numbers per tracer (origin, direction, how far the head has come); the
// drawing is one instanced ribbon stretched between tail and head, turned to face the eye, with a hot
// white head and a body in the shooter's colour that thins out toward the tail.

import * as THREE from 'three';
import { FOG_GLSL } from './shared.js';

const FIELDS = 14; // ox oy oz, dx dy dz, total, head, streak, speed, r g b, width
const INSTANCE = 12; // tail xyz + width, head xyz + brightness, rgb + head share
const STREAK_PER_SPEED = 0.022; // streak length = speed × this, clamped below
const STREAK_MIN = 2;
const STREAK_MAX = 7;

/** The simulation alone (exported for tests). */
export function createTracerSim(capacity) {
  const data = new Float32Array(capacity * FIELDS);
  let recycle = 0; // next entry to give up when the pool is full
  const sim = {
    data,
    count: 0,
    capacity,
    /** A tracer along the unit direction (dx, dy, dz) for `total` metres. A full pool recycles its entries in turn. */
    add(ox, oy, oz, dx, dy, dz, total, speed, r, g, b, width) {
      let i = sim.count;
      if (i >= capacity) {
        i = recycle;
        recycle = (recycle + 1) % capacity;
      } else {
        sim.count = i + 1;
      }
      const o = i * FIELDS;
      data[o] = ox;
      data[o + 1] = oy;
      data[o + 2] = oz;
      data[o + 3] = dx;
      data[o + 4] = dy;
      data[o + 5] = dz;
      data[o + 6] = total;
      data[o + 7] = 0;
      data[o + 8] = Math.min(STREAK_MAX, Math.max(STREAK_MIN, speed * STREAK_PER_SPEED));
      data[o + 9] = speed;
      data[o + 10] = r;
      data[o + 11] = g;
      data[o + 12] = b;
      data[o + 13] = width;
    },
    /** Moves every head forward; a tracer is done when its tail reaches the end of the path. */
    update(dt) {
      let n = sim.count;
      let i = 0;
      while (i < n) {
        const o = i * FIELDS;
        const head = data[o + 7] + data[o + 9] * dt;
        if (head - data[o + 8] >= data[o + 6]) {
          n--;
          if (i !== n) data.copyWithin(o, n * FIELDS, n * FIELDS + FIELDS);
        } else {
          data[o + 7] = head;
          i++;
        }
      }
      sim.count = n;
    },
    /** Writes tail / head points for drawing. Returns the number of instances. */
    write(out) {
      for (let i = 0; i < sim.count; i++) {
        const o = i * FIELDS;
        const w = i * INSTANCE;
        const total = data[o + 6];
        const head = Math.min(data[o + 7], total);
        const tail = Math.max(0, data[o + 7] - data[o + 8]);
        out[w] = data[o] + data[o + 3] * tail;
        out[w + 1] = data[o + 1] + data[o + 4] * tail;
        out[w + 2] = data[o + 2] + data[o + 5] * tail;
        out[w + 3] = data[o + 13];
        out[w + 4] = data[o] + data[o + 3] * head;
        out[w + 5] = data[o + 1] + data[o + 4] * head;
        out[w + 6] = data[o + 2] + data[o + 5] * head;
        // A streak squeezed against its target fades as it shortens.
        out[w + 7] = Math.min(1, (head - tail) / (data[o + 8] * 0.35));
        out[w + 8] = data[o + 10];
        out[w + 9] = data[o + 11];
        out[w + 10] = data[o + 12];
        // Share of the ribbon that is "head": constant in metres, so short streaks are mostly head.
        out[w + 11] = Math.min(0.6, 0.9 / Math.max(head - tail, 0.01));
      }
      return sim.count;
    },
  };
  return sim;
}

const VERTEX = /* glsl */ `
  attribute vec4 iTail;  // xyz, width
  attribute vec4 iHead;  // xyz, brightness
  attribute vec4 iTint;  // rgb, head share

  uniform vec4 uFog;
  uniform float uPixel;

  varying vec2 vUv;
  varying vec3 vColor;
  varying float vHeadShare;

  ${FOG_GLSL}

  void main() {
    vec3 a = (modelViewMatrix * vec4(iTail.xyz, 1.0)).xyz;
    vec3 b = (modelViewMatrix * vec4(iHead.xyz, 1.0)).xyz;
    vec3 p = mix(a, b, position.y);
    vec3 along = b - a;
    vec3 side = cross(p, along);
    float sl = length(side);
    side = sl > 1e-6 ? side / sl : vec3(1.0, 0.0, 0.0);
    // At least a pixel and a half wide wherever it is; dimmer when it had to be widened.
    float width = max(iTail.w, -p.z * uPixel * 1.6);
    float gain = pow(iTail.w / width, 0.55);
    p += side * (position.x * width);
    gl_Position = projectionMatrix * vec4(p, 1.0);
    vUv = vec2(position.x * 2.0, position.y);
    vColor = iTint.rgb * (iHead.w * gain * (1.0 - fxFog(-p.z)));
    vHeadShare = iTint.w;
  }
`;

const FRAGMENT = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vColor;
  varying float vHeadShare;

  void main() {
    float across = exp(-vUv.x * vUv.x * 5.0) - 0.0067;
    float body = pow(vUv.y, 1.7);
    float head = smoothstep(1.0 - vHeadShare, 1.0 - vHeadShare * 0.3, vUv.y);
    float tip = 1.0 - smoothstep(0.985, 1.0, vUv.y);
    float core = exp(-vUv.x * vUv.x * 22.0);
    vec3 color = vColor * (body * across) + vec3(dot(vColor, vec3(0.3333))) * (head * core * 0.9);
    gl_FragColor = vec4(max(color, 0.0) * tip, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

export function createTracers({ capacity, common, renderOrder }) {
  const sim = createTracerSim(capacity);

  const geometry = new THREE.InstancedBufferGeometry();
  geometry.setAttribute(
    'position',
    new THREE.BufferAttribute(new Float32Array([-0.5, 0, 0, 0.5, 0, 0, 0.5, 1, 0, -0.5, 1, 0]), 3),
  );
  geometry.setIndex([0, 1, 2, 0, 2, 3]);
  const array = new Float32Array(capacity * INSTANCE);
  const buffer = new THREE.InstancedInterleavedBuffer(array, INSTANCE, 1).setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute('iTail', new THREE.InterleavedBufferAttribute(buffer, 4, 0));
  geometry.setAttribute('iHead', new THREE.InterleavedBufferAttribute(buffer, 4, 4));
  geometry.setAttribute('iTint', new THREE.InterleavedBufferAttribute(buffer, 4, 8));
  geometry.instanceCount = 0;

  const material = new THREE.ShaderMaterial({
    name: 'fx-tracers',
    uniforms: { uFog: common.uFog, uPixel: common.uPixel },
    vertexShader: VERTEX,
    fragmentShader: FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    premultipliedAlpha: true,
    side: THREE.DoubleSide, // the ribbon may turn either face to the eye…
    forceSinglePass: true, // …and must still be drawn only once
    fog: false,
  });

  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = 'fx-tracers';
  mesh.frustumCulled = false;
  mesh.renderOrder = renderOrder;
  mesh.visible = false;
  mesh.matrixAutoUpdate = false;

  return {
    mesh,
    sim,
    update(dt) {
      if (sim.count === 0) {
        mesh.visible = false;
        return;
      }
      sim.update(dt);
      const n = sim.write(array);
      geometry.instanceCount = n;
      mesh.visible = n > 0;
      if (n > 0) buffer.needsUpdate = true;
    },
    clear() {
      sim.count = 0;
      geometry.instanceCount = 0;
      mesh.visible = false;
    },
  };
}
