// The particle simulation behind both billboard pools (src/fx/sim.js): spawning against a budget,
// integration (gravity, drag toward the wind, floors), what is written for drawing, and the depth sort.

import test from 'node:test';
import assert from 'node:assert/strict';
import {
  AGE, BOUNCE, DIE, GRAVITY, INSTANCE, STICK, STRIDE, VX, VY, X, Y,
  createSpec, createStore, integrate, resetSpec, sortBackToFront, spawn, stochasticRound, writeInstances,
} from '../src/fx/sim.js';

/** integrate() with its environment spelled out: (store, dt, time, windX, windZ). */
const step = (store, dt, time, windX, windZ) => integrate(store, Float64Array.of(dt, time, windX, windZ));

const near = (actual, expected, eps, label = '') =>
  assert.ok(Math.abs(actual - expected) <= eps, `${label} expected ${expected} ± ${eps}, got ${actual}`);

function one(fill) {
  const store = createStore(8);
  const s = createSpec();
  fill(s);
  spawn(store, s);
  return store;
}

test('fx sim: a particle lives exactly its life and the store stays dense', () => {
  const store = createStore(4);
  const s = createSpec();
  for (const life of [0.1, 1, 0.2, 1]) {
    resetSpec(s);
    s.life = life;
    s.x = life; // tag
    spawn(store, s);
  }
  assert.equal(store.count, 4);
  step(store, 0.15, 0, 0, 0);
  // The 0.1 s particle is gone; the last one took its slot.
  assert.equal(store.count, 3);
  assert.equal(store.data[0 * STRIDE + X], 1);
  step(store, 0.1, 0, 0, 0);
  assert.equal(store.count, 2);
  for (let i = 0; i < 2; i++) near(store.data[i * STRIDE + X], 1, 1e-6, 'a 1 s particle survives');
  step(store, 1, 0, 0, 0);
  assert.equal(store.count, 0);
});

test('fx sim: gravity is 9.81 m/s² times the particle factor, and negative factors rise', () => {
  const falling = one((s) => {
    s.life = 10;
    s.gravity = 1;
    s.y = 100;
  });
  const rising = one((s) => {
    s.life = 10;
    s.gravity = -0.5;
  });
  for (let i = 0; i < 100; i++) {
    step(falling, 0.01, 0, 0, 0);
    step(rising, 0.01, 0, 0, 0);
  }
  near(falling.data[VY], -GRAVITY, 1e-3, 'speed after 1 s');
  near(falling.data[Y], 100 - GRAVITY / 2, 0.06, 'height after 1 s');
  near(rising.data[VY], GRAVITY * 0.5, 1e-3, 'buoyant speed after 1 s');
});

test('fx sim: drag pulls the velocity toward the wind the particle picks up', () => {
  const store = one((s) => {
    s.life = 100;
    s.vx = 20;
    s.vy = 5;
    s.drag = 4;
    s.wind = 0.5;
  });
  for (let i = 0; i < 400; i++) step(store, 0.016, 0, 2, 0);
  near(store.data[VX], 1, 0.01, 'settles at wind × factor');
  near(store.data[VY], 0, 0.01, 'vertical speed dies away');

  // A huge step must not overshoot or blow up.
  const stiff = one((s) => {
    s.life = 100;
    s.vx = 20;
    s.drag = 50;
  });
  step(stiff, 1, 0, 0, 0);
  assert.ok(stiff.data[VX] >= 0 && stiff.data[VX] < 1, `stable with a long frame: ${stiff.data[VX]}`);
});

test('fx sim: floors — bounce loses energy and comes to rest, die removes, stick stops', () => {
  const bouncing = one((s) => {
    s.life = 100;
    s.gravity = 1;
    s.y = 2;
    s.vx = 3;
    s.flags = BOUNCE;
    s.floor = 0.5;
    s.seed = 0.3;
  });
  let peak = 0;
  let bounced = false;
  for (let i = 0; i < 600; i++) {
    step(bouncing, 1 / 120, 0, 0, 0);
    const y = bouncing.data[Y];
    assert.ok(y >= 0.5, `never below its floor: ${y}`);
    if (bouncing.data[VY] > 0) bounced = true;
    if (bounced) peak = Math.max(peak, y);
  }
  assert.ok(bounced, 'it bounced');
  assert.ok(peak < 0.5 + 1.5 * 0.56 ** 2 + 0.05, `a bounce keeps at most 55 % of the speed: peak ${peak}`);
  assert.equal(bouncing.data[VX], 0, 'came to rest');
  assert.equal(bouncing.data[VY], 0);
  near(bouncing.data[Y], 0.512, 1e-3, 'rests just above the floor');

  const dying = one((s) => {
    s.life = 100;
    s.gravity = 1;
    s.y = 1;
    s.flags = DIE;
  });
  for (let i = 0; i < 120 && dying.count; i++) step(dying, 1 / 60, 0, 0, 0);
  assert.equal(dying.count, 0, 'a DIE particle ends on the floor');

  const sticking = one((s) => {
    s.life = 100;
    s.gravity = 1;
    s.y = 1;
    s.vx = 4;
    s.flags = STICK;
  });
  for (let i = 0; i < 120; i++) step(sticking, 1 / 60, 0, 0, 0);
  assert.equal(sticking.count, 1);
  assert.equal(sticking.data[VX], 0);
  const x = sticking.data[X];
  step(sticking, 1 / 60, 0, 5, 5);
  assert.equal(sticking.data[X], x, 'a stuck particle no longer moves');
});

test('fx sim: the budget — soft spawns give way early, hard spawns recycle the most spent particle', () => {
  const store = createStore(100);
  store.budget = 20;
  const s = createSpec();
  for (let i = 0; i < 40; i++) {
    resetSpec(s);
    s.life = 10;
    spawn(store, s, true);
  }
  assert.equal(store.count, 17, 'soft spawns stop at 85 % of the budget');
  assert.equal(store.dropped, 23);

  for (let i = 0; i < 3; i++) spawn(store, s, false);
  assert.equal(store.count, 20);

  // Age one particle far more than the rest, then overflow: it is the one replaced.
  step(store, 1, 0, 0, 0);
  for (let i = 0; i < 20; i++) store.data[i * STRIDE + AGE] = 1;
  const old = (store.spawned * 7919) % 20; // first probe of the recycler
  store.data[old * STRIDE + AGE] = 9.5;
  resetSpec(s);
  s.life = 10;
  s.x = 777;
  const index = spawn(store, s, false);
  assert.equal(store.count, 20, 'the budget holds');
  assert.equal(index, old);
  assert.equal(store.data[old * STRIDE + X], 777);
  assert.equal(store.stolen, 1);
});

test('fx sim: instances carry the size curve, the fades and the colour ramp', () => {
  const store = one((s) => {
    s.life = 2;
    s.size = 1;
    s.size1 = 3;
    s.r = 1;
    s.g = 0.5;
    s.b = 0;
    s.r1 = 0;
    s.g1 = 0.5;
    s.b1 = 1;
    s.alpha = 0.8;
    s.fadeIn = 0.25;
    s.fadeOut = 0.5;
    s.frame = 5;
    s.floor = 0.15;
  });
  const out = new Float32Array(INSTANCE);

  step(store, 0.25, 0, 0, 0); // t = 0.125: half way through the fade-in
  assert.equal(writeInstances(store, out, null), 1);
  near(out[3], 1.25, 1e-5, 'size');
  near(out[7], 0.4, 1e-5, 'fading in');
  near(out[4], 0.875, 1e-5, 'red');
  near(out[6], 0.125, 1e-5, 'blue');
  assert.equal(out[9], 5, 'atlas cell');
  near(out[15], 0.15, 1e-6, 'floor');

  step(store, 0.75, 0, 0, 0); // t = 0.5: fully there
  writeInstances(store, out, null);
  near(out[7], 0.8, 1e-5, 'peak');

  step(store, 0.5, 0, 0, 0); // t = 0.75: half way through the fade-out
  writeInstances(store, out, null);
  near(out[3], 2.5, 1e-5, 'size');
  near(out[7], 0.4, 1e-5, 'fading out');
});

test('fx sim: a streak is as long as the distance covered in `stretch` seconds, within a cap', () => {
  const store = one((s) => {
    s.life = 5;
    s.size = 0.02;
    s.vx = 10;
    s.stretch = 0.05;
  });
  const out = new Float32Array(INSTANCE);
  step(store, 0.001, 0, 0, 0);
  writeInstances(store, out, null);
  near(out[12], 0.5, 1e-4, 'axis = velocity × stretch');
  assert.equal(out[13], 0);

  store.data[VX] = 1000; // absurdly fast: capped at 45 × the width
  writeInstances(store, out, null);
  near(out[12], 0.9, 1e-4, 'capped');
});

test('fx sim: heat cools within a second', () => {
  const store = one((s) => {
    s.life = 4;
    s.heat = 1;
  });
  const out = new Float32Array(INSTANCE);
  writeInstances(store, out, null);
  near(out[11], 1, 1e-6);
  for (let i = 0; i < 60; i++) step(store, 1 / 60, 0, 0, 0);
  writeInstances(store, out, null);
  assert.ok(out[11] < 0.01, `still glowing after a second: ${out[11]}`);
});

test('fx sim: the lit pool is ordered far to near along the view direction', () => {
  const store = createStore(64);
  const s = createSpec();
  const depths = [];
  let seed = 7;
  for (let i = 0; i < 64; i++) {
    seed = (seed * 16807) % 2147483647;
    const depth = (seed % 1000) / 10;
    depths.push(depth);
    resetSpec(s);
    s.z = -depth; // camera at the origin looking down −Z
    s.x = (i % 5) - 2;
    spawn(store, s);
  }
  const order = new Uint16Array(64);
  const keys = new Float32Array(64);
  assert.equal(sortBackToFront(store, order, keys, Float64Array.of(0, 0, 0, 0, 0, -1)), 64);
  assert.deepEqual([...order].sort((a, b) => a - b), [...Array(64).keys()], 'a permutation');
  for (let i = 1; i < 64; i++) assert.ok(depths[order[i - 1]] >= depths[order[i]], `position ${i} is nearer than the one before`);

  const out = new Float32Array(64 * INSTANCE);
  writeInstances(store, out, order);
  near(-out[2], Math.max(...depths), 1e-4, 'the farthest particle is drawn first');
});

test('fx sim: stochastic rounding keeps the average', () => {
  let total = 0;
  for (let i = 0; i < 1000; i++) total += stochasticRound(2.3, (i + 0.5) / 1000);
  near(total / 1000, 2.3, 1e-9);
  assert.equal(stochasticRound(3, 0.99), 3);
  assert.equal(stochasticRound(0.2, 0.5), 0);
});
