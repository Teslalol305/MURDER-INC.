// The score's clock and layering rules, and the render queue.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { BAR, BEAT, BPM, LOOP, STEP, stepTime, STEMS } from '../src/audio/music.js';
import { layerGains, nextTier, nextGrid, STEM_NAMES } from '../src/audio/conductor.js';
import { createQueue } from '../src/audio/queue.js';

test('tempo and grid', () => {
  assert.equal(BPM, 92);
  assert.ok(Math.abs(BAR - 240 / 92) < 1e-12);
  assert.ok(Math.abs(LOOP - 8 * BAR) < 1e-12);
  assert.equal(stepTime(0, 0), 0);
  assert.ok(Math.abs(stepTime(1, 0) - BAR) < 1e-12);
  assert.ok(Math.abs(stepTime(0, 4) - BEAT) < 1e-12, 'beats are straight');
  assert.ok(stepTime(0, 1) > STEP, 'off-16ths swing late');
  assert.ok(stepTime(0, 1) < STEP * 1.3);
});

test('nextGrid lands on the clock, at or after t + ahead', () => {
  const t0 = 3.21;
  for (const t of [3.21, 4, 10.5, 33.3]) {
    const g = nextGrid(t0, t, 0.05, BAR);
    assert.ok(g >= t + 0.05 - 1e-9);
    assert.ok(g - (t + 0.05) < BAR + 1e-9);
    const k = (g - t0) / BAR;
    assert.ok(Math.abs(k - Math.round(k)) < 1e-9, `on a bar line: ${k}`);
  }
  assert.ok(Math.abs(nextGrid(0, BEAT * 2, 0, BEAT) - BEAT * 2) < 1e-9, 'exactly on the grid counts');
});

test('layers: calm is filtered drums and a bass sketch, 0.6 full drums and keys, 1.0 everything', () => {
  const calm = layerGains(0.15);
  const alert = layerGains(0.6);
  const hot = layerGains(1);
  assert.ok(calm.drumCut < 1000 && alert.drumCut > 15000, 'drums open up');
  assert.ok(calm.keys < 0.01 && alert.keys > 0.9);
  assert.ok(calm.bass > 0.3 && calm.bass < alert.bass);
  assert.ok(calm.strings === 0 && alert.strings < 0.01 && hot.strings > 0.99);
  assert.ok(hot.bell > 0.8 && hot.drums === 1 && hot.hats === 1);
  assert.ok(layerGains(1, 'play', 0).strings === 0, 'the gate holds the top layers back');
  for (const n of STEM_NAMES) assert.ok(n in calm && n in hot, n);
  assert.deepEqual(STEM_NAMES.sort(), Object.keys(STEMS).sort());
  const dead = layerGains(1, 'dead');
  assert.ok(dead.drums === 0 && dead.bass === 0 && dead.crackle > 0);
  // Monotone in intensity.
  let prev = layerGains(0);
  for (let i = 1; i <= 20; i++) {
    const g = layerGains(i / 20);
    for (const n of ['drums', 'hats', 'bass', 'strings', 'bell', 'drumCut']) assert.ok(g[n] >= prev[n] - 1e-9, `${n} at ${i / 20}`);
    prev = g;
  }
});

test('tiers have hysteresis', () => {
  assert.equal(nextTier(0, 0.15), 0);
  assert.equal(nextTier(0, 0.45), 1);
  assert.equal(nextTier(1, 0.35), 1);
  assert.equal(nextTier(1, 0.3), 0);
  assert.equal(nextTier(1, 0.82), 2);
  assert.equal(nextTier(2, 0.7), 2);
  assert.equal(nextTier(2, 0.6), 1);
});

test('queue: priority order, promote, finish, time slices', () => {
  let t = 0;
  const pending = [];
  const q = createQueue({ slice: 5, interval: 1, now: () => t, schedule: (fn) => pending.push(fn) });
  const done = [];
  const job = (key, steps) =>
    (function* () {
      for (let i = 0; i < steps; i++) {
        t += 1; // each step costs a millisecond
        yield;
      }
      return key;
    })();
  q.add('late', 9, job('late', 3), (r) => done.push(r));
  q.add('gun', 0, job('gun', 3), (r) => done.push(r));
  q.add('mid', 4, job('mid', 3), (r) => done.push(r));
  q.add('gun', 0, job('dup', 1), (r) => done.push(r)); // same key twice: ignored
  q.start();
  assert.equal(pending.length, 1);
  pending.shift()(); // one 5 ms slice: gun finishes, mid has started
  assert.deepEqual(done, ['gun']);
  q.promote('late');
  q.finish('mid');
  assert.deepEqual(done, ['gun', 'mid']);
  while (pending.length) pending.shift()();
  assert.deepEqual(done, ['gun', 'mid', 'late']);
  assert.equal(q.size, 0);
  assert.equal(q.has('late'), false);
});
