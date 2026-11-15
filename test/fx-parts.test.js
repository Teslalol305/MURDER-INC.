// The smaller pieces of the effects module that are pure logic: the tracer simulation, the rigid-body
// step behind brass and debris, the decal basis and the generated sprite sheets.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { ADD, COLS, DECAL, LIT, ROWS, additiveSheet, decalSheet, litSheet } from '../src/fx/atlas.js';
import { BODY, FLYING, RESTING, stepBody } from '../src/fx/bits.js';
import { decalBasis } from '../src/fx/decals.js';
import { createTracerSim } from '../src/fx/tracers.js';

const near = (actual, expected, eps, label = '') =>
  assert.ok(Math.abs(actual - expected) <= eps, `${label} expected ${expected} ± ${eps}, got ${actual}`);

// ---------------------------------------------------------------------------------------------
// Tracers
// ---------------------------------------------------------------------------------------------

test('fx tracers: the head travels at the given speed and the streak trails 0.022 s behind (2…7 m)', () => {
  const sim = createTracerSim(4);
  const out = new Float32Array(4 * 12);
  sim.add(0, 1.5, 0, 1, 0, 0, 100, 260, 1, 1, 1, 0.03);
  sim.update(0.1);
  assert.equal(sim.write(out), 1);
  near(out[4], 26, 1e-3, 'head after 0.1 s');
  near(out[0], 26 - 5.72, 1e-3, 'tail = head − 260 × 0.022');
  near(out[1], 1.5, 1e-6, 'stays on its line');
  assert.equal(out[3], Math.fround(0.03), 'width');

  const slow = createTracerSim(1);
  slow.add(0, 0, 0, 0, 0, -1, 50, 70, 1, 0, 0, 0.03); // a Buzzard bolt: short streak
  slow.update(0.2);
  slow.write(out);
  near(out[6], -14, 1e-3, 'head');
  near(out[2], -12, 1e-3, 'streak clamps at 2 m');

  const fast = createTracerSim(1);
  fast.add(0, 0, 0, 0, 0, -1, 500, 900, 1, 0, 0, 0.03);
  fast.update(0.1);
  fast.write(out);
  near(out[2] - out[6], 7, 1e-3, 'streak clamps at 7 m');
});

test('fx tracers: a tracer stops at its target, shrinks into it and is then removed', () => {
  const sim = createTracerSim(4);
  const out = new Float32Array(4 * 12);
  sim.add(0, 0, 0, 1, 0, 0, 20, 260, 1, 1, 1, 0.03);
  sim.update(0.08); // head would be at 20.8
  sim.write(out);
  near(out[4], 20, 1e-4, 'head held at the target');
  near(out[0], 20.8 - 5.72, 1e-3, 'tail still on its way');
  assert.ok(out[7] === 1, 'full brightness while most of the streak is left');
  sim.update(0.02);
  assert.equal(sim.count, 0, 'gone once the tail has arrived');
});

test('fx tracers: a full pool recycles its entries in turn, and removal keeps the others', () => {
  const sim = createTracerSim(3);
  const out = new Float32Array(3 * 12);
  for (let i = 0; i < 5; i++) sim.add(i, 0, 0, 0, 1, 0, 300, 260, 1, 1, 1, 0.03);
  assert.equal(sim.count, 3);
  sim.write(out);
  assert.deepEqual([out[0], out[12], out[24]], [3, 4, 2], 'the two oldest gave way to the two newest');

  const mixed = createTracerSim(3);
  mixed.add(0, 0, 0, 0, 1, 0, 10, 260, 1, 1, 1, 0.03);
  mixed.add(1, 0, 0, 0, 1, 0, 300, 260, 1, 1, 1, 0.03);
  mixed.add(2, 0, 0, 0, 1, 0, 12, 260, 1, 1, 1, 0.03);
  mixed.update(0.07); // 18.2 m: the two short ones are done, tail and all
  assert.equal(mixed.write(out), 1);
  assert.equal(out[0], 1, 'the long one flies on');
  near(out[5], 18.2, 1e-3, 'and is 18.2 m along');
});

// ---------------------------------------------------------------------------------------------
// Brass and debris
// ---------------------------------------------------------------------------------------------

function body({ y = 1.2, vx = 2.5, vy = 1.5, floor = 0, radius = 0.0085 } = {}) {
  const d = new Float32Array(BODY);
  d[1] = y;
  d[3] = vx;
  d[4] = vy;
  d[9] = 5;
  d[10] = 20;
  d[11] = 9;
  d[12] = floor;
  d[14] = radius;
  d[15] = FLYING;
  return d;
}

test('fx brass: a casing arcs, bounces a few times losing height, and comes to rest lying flat', () => {
  const d = body();
  let touches = 0;
  let lastPeak = Infinity;
  let peak = 0;
  let steps = 0;
  while (d[15] === FLYING && steps < 2000) {
    const touched = stepBody(d, 0, 1 / 120, 0.4, 0.6, 4);
    if (touched) {
      if (touches > 0) {
        assert.ok(peak < lastPeak, `bounce ${touches} is lower than the one before (${peak} < ${lastPeak})`);
        lastPeak = peak;
      }
      touches++;
      peak = 0;
    }
    peak = Math.max(peak, d[1]);
    assert.ok(d[1] >= 0.0085 - 1e-6, 'never below the floor');
    steps++;
  }
  assert.equal(d[15], RESTING);
  assert.ok(touches >= 2 && touches <= 4, `2 to 4 touches, got ${touches}`);
  assert.ok(steps / 120 < 2.5, `settles within 2.5 s (${steps / 120})`);
  near(d[1], 0.0085, 1e-6, 'rests on its side: one radius above the floor');
  assert.equal(d[7], 0, 'pitch is flat');
  assert.deepEqual([d[3], d[4], d[5], d[9], d[10], d[11]], [0, 0, 0, 0, 0, 0], 'stopped');
  assert.ok(d[0] > 1 && d[0] < 4, `landed a metre or three to the side: ${d[0]}`);
  const x = d[0];
  assert.equal(stepBody(d, 0, 1 / 60, 0.4, 0.6, 4), 0);
  assert.equal(d[0], x, 'a resting body no longer moves');
});

test('fx brass: the floor under a body is honoured (a car bonnet, a deck)', () => {
  const d = body({ y: 3.6, floor: 2.8 });
  for (let i = 0; i < 600 && d[15] === FLYING; i++) stepBody(d, 0, 1 / 120, 0.4, 0.6, 4);
  assert.equal(d[15], RESTING);
  near(d[1], 2.8085, 1e-5, 'at rest on the deck');
});

// ---------------------------------------------------------------------------------------------
// Decal orientation
// ---------------------------------------------------------------------------------------------

test('fx decals: the basis is orthonormal and right-handed about any surface normal', () => {
  const t = new THREE.Vector3();
  const b = new THREE.Vector3();
  const n = new THREE.Vector3();
  const cross = new THREE.Vector3();
  const normals = [[0, 1, 0], [0, -1, 0], [1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1], [0.6, 0, 0.8], [0.36, 0.48, 0.8], [0.1, 0.99, 0.1]];
  for (const raw of normals) {
    n.fromArray(raw).normalize();
    decalBasis(n.x, n.y, n.z, t, b);
    near(t.length(), 1, 1e-9, `|t| for ${raw}`);
    near(b.length(), 1, 1e-6, `|b| for ${raw}`);
    near(t.dot(n), 0, 1e-6, `t ⟂ n for ${raw}`);
    near(b.dot(n), 0, 1e-6, `b ⟂ n for ${raw}`);
    near(t.dot(b), 0, 1e-6, `t ⟂ b for ${raw}`);
    near(cross.crossVectors(t, b).dot(n), 1, 1e-6, `t × b = n for ${raw}: the quad faces out of the surface`);
  }
});

test('fx decals: on a wall the mark stands upright; on the ground it lies in the XZ plane', () => {
  const t = new THREE.Vector3();
  const b = new THREE.Vector3();
  for (const [nx, nz] of [[1, 0], [-1, 0], [0, 1], [0, -1], [0.6, 0.8]]) {
    decalBasis(nx, 0, nz, t, b);
    assert.equal(t.y, 0, 'tangent is horizontal');
    near(b.y, 1, 1e-9, 'bitangent points up');
  }
  decalBasis(0, 1, 0, t, b);
  assert.equal(t.y, 0);
  near(b.y, 0, 1e-12);
});

// ---------------------------------------------------------------------------------------------
// Sheets
// ---------------------------------------------------------------------------------------------

test('fx atlas: three 4 × 2 sheets whose cells are filled in the middle and empty at their borders', () => {
  const cell = 32; // small: the painters are resolution independent
  const sheets = { lit: [litSheet(cell), 0], additive: [additiveSheet(cell), 0], decals: [decalSheet(cell), 3] };
  for (const [name, [sheet, channel]] of Object.entries(sheets)) {
    assert.equal(sheet.width, cell * COLS);
    assert.equal(sheet.height, cell * ROWS);
    assert.equal(sheet.data.length, sheet.width * sheet.height * 4);
    const at = (x, y) => sheet.data[(y * sheet.width + x) * 4 + channel];
    for (let i = 0; i < COLS * ROWS; i++) {
      const cx = (i % COLS) * cell;
      const cy = Math.floor(i / COLS) * cell;
      let border = 0;
      let inside = 0;
      for (let k = 0; k < cell; k++) {
        border = Math.max(border, at(cx + k, cy), at(cx + k, cy + cell - 1), at(cx, cy + k), at(cx + cell - 1, cy + k));
        for (let j = 0; j < cell; j++) inside = Math.max(inside, at(cx + k, cy + j));
      }
      assert.equal(border, 0, `${name} cell ${i} bleeds over its border`);
      assert.ok(inside > 120, `${name} cell ${i} is nearly empty (max ${inside})`);
    }
  }
});

test('fx atlas: painting is deterministic and the cell tables cover all eight cells', () => {
  const a = additiveSheet(16);
  const b = additiveSheet(16);
  assert.deepEqual(a.data, b.data);
  for (const table of [LIT, ADD, DECAL]) {
    assert.deepEqual(Object.values(table).sort(), [0, 1, 2, 3, 4, 5, 6, 7]);
  }
});
