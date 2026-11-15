// Stub effects (CONTRACT 6.8): every method exists and most do nothing. Tracers are real enough to see
// where shots go (a pooled line that fades in a few frames), and explosions flash a pooled light.

import * as THREE from 'three';

const TRACERS = 32;
const TRACER_LIFE = 0.09; // seconds
const TRACER_GLOW = 3; // HDR multiplier so the line blooms

export function createFx(G) {
  // One LineSegments draws the whole pool: two vertices per tracer, colour fades with age.
  const positions = new Float32Array(TRACERS * 6);
  const colors = new Float32Array(TRACERS * 6);
  const geometry = new THREE.BufferGeometry();
  const positionAttr = new THREE.BufferAttribute(positions, 3).setUsage(THREE.DynamicDrawUsage);
  const colorAttr = new THREE.BufferAttribute(colors, 3).setUsage(THREE.DynamicDrawUsage);
  geometry.setAttribute('position', positionAttr);
  geometry.setAttribute('color', colorAttr);
  const lines = new THREE.LineSegments(
    geometry,
    new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }),
  );
  lines.name = 'fx-stub-tracers';
  lines.frustumCulled = false; // vertices move every frame; skip recomputing bounds
  G.scene.add(lines);

  const life = new Float32Array(TRACERS); // seconds left
  const tint = new Float32Array(TRACERS * 3); // full-brightness colour of each tracer
  const color = new THREE.Color();
  let next = 0;
  let live = 0;

  function tracer(from, to, hex = 0xffe2a8) {
    const i = next;
    next = (next + 1) % TRACERS;
    if (life[i] <= 0) live++;
    life[i] = TRACER_LIFE;
    const p = i * 6;
    positions[p] = from.x;
    positions[p + 1] = from.y;
    positions[p + 2] = from.z;
    positions[p + 3] = to.x;
    positions[p + 4] = to.y;
    positions[p + 5] = to.z;
    positionAttr.needsUpdate = true;
    color.set(hex).multiplyScalar(TRACER_GLOW);
    tint[i * 3] = color.r;
    tint[i * 3 + 1] = color.g;
    tint[i * 3 + 2] = color.b;
  }

  function update(dt) {
    if (live === 0) return;
    for (let i = 0; i < TRACERS; i++) {
      if (life[i] <= 0) continue;
      life[i] -= dt;
      const k = life[i] > 0 ? life[i] / TRACER_LIFE : 0;
      if (k === 0) live--;
      for (let c = 0; c < 3; c++) {
        // The head stays brighter than the tail.
        colors[i * 6 + c] = tint[i * 3 + c] * k * 0.35;
        colors[i * 6 + 3 + c] = tint[i * 3 + c] * k;
      }
    }
    colorAttr.needsUpdate = true;
  }

  function clear() {
    life.fill(0);
    colors.fill(0);
    colorAttr.needsUpdate = true;
    live = 0;
  }

  G.events.on('explosion', (e) => {
    G.render.lights.flash(e.pos, 0xffa040, e.size === 'big' ? 160 : 80, e.radius * 2.5, 0.3);
  });

  const noop = () => {};
  const emitter = { stop: noop, setPos: noop };

  return {
    muzzleFlash: noop,
    tracer,
    impact: noop,
    sparks: noop,
    smoke: noop,
    dust: noop,
    puff: noop,
    explosion: noop,
    shell: noop,
    debris: noop,
    decal: noop,
    addEmitter: () => emitter,
    clear,
    stats: () => ({ tracers: live }),
    update,
  };
}
