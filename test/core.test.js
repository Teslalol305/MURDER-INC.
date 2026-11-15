// Shared helpers: events, rng, util, settings. Run with `node --test test/`.

import test from 'node:test';
import assert from 'node:assert/strict';
import { createEvents } from '../src/core/events.js';
import { createRng, toSeed } from '../src/core/rng.js';
import { BEST_KEY, DEFAULTS, SETTINGS_KEY, createSettings } from '../src/core/settings.js';
import * as util from '../src/core/util.js';

const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps, `expected ${b}, got ${a}`);

/** In-memory stand-in for localStorage. */
function fakeStorage(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {
    data,
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => data.set(k, String(v)),
  };
}

/** Runs fn with console.error silenced; returns what was logged. */
function quiet(fn) {
  const original = console.error;
  const logged = [];
  console.error = (...args) => logged.push(args);
  try {
    fn();
  } finally {
    console.error = original;
  }
  return logged;
}

// ---------------------------------------------------------------------------------------- events

test('events: on returns an unsubscribe, off removes, emit passes the payload', () => {
  const events = createEvents();
  const seen = [];
  const stop = events.on('a', (p) => seen.push(['first', p]));
  const second = (p) => seen.push(['second', p]);
  events.on('a', second);
  events.emit('a', 1);
  stop();
  events.emit('a', 2);
  events.off('a', second);
  events.emit('a', 3);
  events.emit('nobody-listens', 4);
  assert.deepEqual(seen, [['first', 1], ['second', 1], ['second', 2]]);
  assert.equal(events.count('a'), 0);
});

test('events: a throwing handler is logged and does not stop the others', () => {
  const events = createEvents();
  let reached = false;
  events.on('x', () => {
    throw new Error('boom');
  });
  events.on('x', () => {
    reached = true;
  });
  const logged = quiet(() => events.emit('x'));
  assert.ok(reached);
  assert.equal(logged.length, 1);
});

test('events: handlers may subscribe and unsubscribe while an emit is running', () => {
  const events = createEvents();
  const calls = [];
  const stopSelf = events.on('x', () => {
    calls.push('self');
    stopSelf();
    events.on('x', () => calls.push('late'));
  });
  events.on('x', () => calls.push('other'));
  events.emit('x');
  assert.deepEqual(calls, ['self', 'other']); // the late handler waits for the next emit
  events.emit('x');
  assert.deepEqual(calls, ['self', 'other', 'other', 'late']);
});

// ------------------------------------------------------------------------------------------- rng

test('rng: the same seed gives the same sequence, another seed another one', () => {
  const a = createRng(1994);
  const b = createRng(1994);
  const c = createRng(1995);
  const seqA = Array.from({ length: 8 }, () => a.next());
  assert.deepEqual(seqA, Array.from({ length: 8 }, () => b.next()));
  assert.notDeepEqual(seqA, Array.from({ length: 8 }, () => c.next()));
  assert.ok(seqA.every((x) => x >= 0 && x < 1));
});

test('rng: seeds from URL parameters', () => {
  assert.equal(toSeed(undefined), 1994);
  assert.equal(toSeed(''), 1994);
  assert.equal(toSeed('42'), 42);
  assert.equal(toSeed('block'), toSeed('block'));
  assert.notEqual(toSeed('block'), toSeed('avenue'));
  assert.equal(createRng('42').next(), createRng(42).next());
});

test('rng: helpers stay in range', () => {
  const rng = createRng(7);
  const ints = new Set();
  for (let i = 0; i < 2000; i++) {
    const r = rng.range(-2, 3);
    assert.ok(r >= -2 && r < 3);
    const n = rng.int(1, 4);
    assert.ok(Number.isInteger(n) && n >= 1 && n <= 4);
    ints.add(n);
    assert.ok([-1, 1].includes(rng.sign()));
    assert.ok(['a', 'b', 'c'].includes(rng.pick(['a', 'b', 'c'])));
  }
  assert.deepEqual([...ints].sort(), [1, 2, 3, 4]); // both ends are reachable
  assert.equal(rng.chance(0), false);
  assert.equal(rng.chance(1), true);
});

test('rng: labelled forks do not depend on how much the parent was used', () => {
  const fresh = createRng(5);
  const used = createRng(5);
  for (let i = 0; i < 100; i++) used.next();
  assert.equal(fresh.fork('enemies').next(), used.fork('enemies').next());
  assert.notEqual(fresh.fork('enemies').next(), fresh.fork('nav').next());
  // an unlabelled fork draws from the parent, so it does depend on it
  assert.notEqual(createRng(5).fork().next(), used.fork().next());
});

// ------------------------------------------------------------------------------------------ util

test('util: clamp, lerp, remap, moveToward', () => {
  assert.equal(util.clamp(5, 0, 1), 1);
  assert.equal(util.clamp(-5, 0, 1), 0);
  assert.equal(util.clamp01(0.3), 0.3);
  assert.equal(util.lerp(2, 6, 0.25), 3);
  assert.equal(util.invLerp(2, 6, 3), 0.25);
  assert.equal(util.remap(15, 10, 20, 0, 100), 50);
  assert.equal(util.remap(99, 10, 20, 0, 100), 100);
  assert.equal(util.moveToward(0, 10, 3), 3);
  assert.equal(util.moveToward(9, 10, 3), 10);
  assert.equal(util.moveToward(0, -10, 3), -3);
});

test('util: damp and expDecay are frame-rate independent', () => {
  let coarse = 0;
  let fine = 0;
  for (let i = 0; i < 10; i++) coarse = util.damp(coarse, 1, 11, 0.02);
  for (let i = 0; i < 100; i++) fine = util.damp(fine, 1, 11, 0.002);
  near(coarse, fine, 1e-9);
  near(coarse, 1 - Math.exp(-11 * 0.2));
  near(util.expDecay(8, 5, 0.1), 8 * Math.exp(-0.5));
});

test('util: smoothstep and smootherstep', () => {
  assert.equal(util.smoothstep(0, 1, -1), 0);
  assert.equal(util.smoothstep(0, 1, 2), 1);
  assert.equal(util.smoothstep(0, 2, 1), 0.5);
  assert.equal(util.smootherstep(0, 2, 1), 0.5);
  assert.equal(util.smoothstep(1, 1, 5), 0); // degenerate edge pair does not divide by zero
});

test('util: angles wrap to (−π, π] and deltas take the short way', () => {
  near(util.wrapAngle(Math.PI * 3), Math.PI);
  near(util.wrapAngle(-Math.PI), Math.PI);
  near(util.wrapAngle(0.5), 0.5);
  near(util.wrapAngle(-Math.PI * 1.5), Math.PI / 2);
  near(util.angleDelta(3, -3), Math.PI * 2 - 6);
  near(util.angleDelta(-3, 3), 6 - Math.PI * 2);
  near(util.dampAngle(3, -3, 1e9, 1), 3 + (Math.PI * 2 - 6)); // arrives the short way round
});

test('util: URL parameter helpers', () => {
  const params = { shot: '', step: '1', post: '0', dt: '0.02', bad: 'x' };
  assert.equal(util.paramOn(params, 'shot'), true);
  assert.equal(util.paramOn(params, 'step'), true);
  assert.equal(util.paramOn(params, 'post'), false);
  assert.equal(util.paramOn(params, 'missing'), false);
  assert.equal(util.paramNumber(params, 'dt', 1), 0.02);
  assert.equal(util.paramNumber(params, 'bad', 7), 7);
  assert.equal(util.paramNumber(params, 'shot', 7), 7);
  assert.equal(util.paramNumber(params, 'missing', 7), 7);
});

// -------------------------------------------------------------------------------------- settings

test('settings: defaults when nothing is stored', () => {
  const settings = createSettings(null, fakeStorage());
  assert.deepEqual(settings.all(), { ...DEFAULTS });
  assert.equal(settings.get('difficulty'), 'boss');
  assert.equal(settings.best(), 0);
});

test('settings: stored values are validated and clamped on load', () => {
  const stored = { quality: 'ludicrous', sens: 99, invertY: 'yes', volume: -3, fov: 120.4, difficulty: 'kingpin', mode: 'holdout', view: 9, extra: 1 };
  const settings = createSettings(null, fakeStorage({ [SETTINGS_KEY]: JSON.stringify(stored) }));
  assert.deepEqual(settings.all(), { quality: 'auto', sens: 3, invertY: false, volume: 0, fov: 95, difficulty: 'kingpin', mode: 'holdout', view: 1, time: 'day' });
});

test('settings: corrupt or unavailable storage falls back to defaults', () => {
  assert.deepEqual(createSettings(null, fakeStorage({ [SETTINGS_KEY]: '{not json' })).all(), { ...DEFAULTS });
  const hostile = {
    getItem() {
      throw new Error('denied');
    },
    setItem() {
      throw new Error('denied');
    },
  };
  const settings = createSettings(null, hostile);
  assert.equal(settings.set('fov', 80), true); // still works in memory
  assert.equal(settings.get('fov'), 80);
  assert.equal(settings.setBest(10), true); // remembered for the session at least
  assert.equal(settings.setBest(5), false);
  assert.equal(settings.best(), 10);
  assert.deepEqual(createSettings(null, null).all(), { ...DEFAULTS });
});

test('settings: set validates, saves and emits settings:change', () => {
  const storage = fakeStorage();
  const events = createEvents();
  const changes = [];
  events.on('settings:change', (e) => changes.push(e));
  const settings = createSettings(events, storage);

  assert.equal(settings.set('sens', 5), true); // clamped
  assert.equal(settings.get('sens'), 3);
  assert.equal(settings.set('difficulty', 'godfather'), false);
  assert.equal(settings.set('nope', 1), false);
  assert.equal(settings.set('invertY', true), true);
  assert.equal(settings.set('invertY', true), true); // unchanged: no second event
  assert.deepEqual(changes, [
    { key: 'sens', value: 3 },
    { key: 'invertY', value: true },
  ]);
  assert.equal(JSON.parse(storage.getItem(SETTINGS_KEY)).sens, 3);
  // a second instance reads what the first one saved
  assert.equal(createSettings(null, storage).get('invertY'), true);
});

test('settings: the best holdout score only goes up', () => {
  const storage = fakeStorage();
  const settings = createSettings(null, storage);
  assert.equal(settings.setBest(1200.4), true);
  assert.equal(settings.setBest(900), false);
  assert.equal(settings.setBest(1200), false);
  assert.equal(settings.best(), 1200);
  assert.equal(storage.getItem(BEST_KEY), '1200');
});
