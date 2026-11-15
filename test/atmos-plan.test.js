// The atmosphere's planning logic (src/atmos/plan.js): shadow frustum, light budget, lamp rows, the
// train's timetable, the city layout, the haze. Run with `node --test test/atmos-plan.test.js`.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as look from '../src/config/look.js';
import { presets } from '../src/config/quality.js';
import { createRng } from '../src/core/rng.js';
import {
  continueRow,
  createTrainSchedule,
  distanceOutside,
  endHazeK,
  fitShadowFrustum,
  fogTransmittance,
  hazeOutside,
  interiorTarget,
  lampClaim,
  lightBasis,
  pickRealLights,
  planCity,
  skylineProfile,
  trainTimeline,
} from '../src/atmos/plan.js';

const BOUNDS = { minX: -46, maxX: 46, minZ: -34, maxZ: 34 };
const near = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) <= eps, `expected ${b}, got ${a}`);
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];

// ------------------------------------------------------------------------------------------------
// Shadow frustum
// ------------------------------------------------------------------------------------------------

test('lightBasis: orthonormal, forward along the light, up never points down', () => {
  for (const dir of [look.sun.direction, [0.3, -1, 0.9], [-1, -0.2, 0], [0, -1, 0]]) {
    const b = lightBasis(dir);
    for (const axis of [b.right, b.up, b.forward]) near(Math.hypot(...axis), 1);
    near(dot(b.right, b.up), 0);
    near(dot(b.right, b.forward), 0);
    near(dot(b.up, b.forward), 0);
    const len = Math.hypot(...dir);
    near(dot(b.forward, dir) / len, 1);
    assert.ok(b.up[1] >= -1e-9, 'up has no downward component');
  }
});

test('fitShadowFrustum: every corner of the block is inside, with the margin to spare', () => {
  const fit = fitShadowFrustum({ bounds: BOUNDS, minY: -0.5, maxY: 22, dir: look.sun.direction, mapSize: 2048, margin: 2 });
  const basis = lightBasis(look.sun.direction);
  for (const x of [BOUNDS.minX, BOUNDS.maxX]) {
    for (const y of [-0.5, 22]) {
      for (const z of [BOUNDS.minZ, BOUNDS.maxZ]) {
        const rel = sub([x, y, z], fit.position);
        const px = dot(rel, basis.right);
        const py = dot(rel, basis.up);
        const depth = dot(rel, basis.forward);
        assert.ok(px >= fit.left + 1 && px <= fit.right - 1, `x ${px} within ${fit.left}…${fit.right}`);
        assert.ok(py >= fit.bottom + 1 && py <= fit.top - 1, `y ${py} within ${fit.bottom}…${fit.top}`);
        assert.ok(depth >= fit.near && depth <= fit.far, `depth ${depth} within ${fit.near}…${fit.far}`);
      }
    }
  }
  // The light looks along its direction, at a point inside the box.
  const aim = sub(fit.target, fit.position);
  near(dot(aim, basis.forward) / Math.hypot(...aim), 1, 1e-9);
});

test('fitShadowFrustum: near and far hug the block', () => {
  const fit = fitShadowFrustum({ bounds: BOUNDS, minY: 0, maxY: 20, dir: look.sun.direction, mapSize: 1024, backoff: 40, pad: 1 });
  near(fit.near, 39);
  near(fit.far - fit.near, fit.depth + 2);
  // A steep light over a 92 × 68 × 20 m block: nowhere near the 500 m default range.
  assert.ok(fit.depth < 75, `depth range ${fit.depth}`);
  assert.ok(fit.width <= 125 && fit.height <= 125, `${fit.width} × ${fit.height}`);
});

test('fitShadowFrustum: the frustum only ever moves by whole texels', () => {
  const basis = lightBasis(look.sun.direction);
  const base = fitShadowFrustum({ bounds: BOUNDS, minY: 0, maxY: 20, dir: look.sun.direction, mapSize: 2048 });
  assert.equal(base.width, Math.round(base.width), 'whole metres wide');
  assert.equal(base.height, Math.round(base.height), 'whole metres tall');
  near(base.texel[0], base.width / 2048);

  // Nudge the box by amounts that keep the rounded size: the centre snaps to the same texel grid.
  for (const shift of [0.013, 0.2, 0.61]) {
    const moved = fitShadowFrustum({
      bounds: { minX: BOUNDS.minX + shift, maxX: BOUNDS.maxX + shift, minZ: BOUNDS.minZ - shift / 2, maxZ: BOUNDS.maxZ - shift / 2 },
      minY: 0,
      maxY: 20,
      dir: look.sun.direction,
      mapSize: 2048,
    });
    assert.equal(moved.width, base.width);
    assert.equal(moved.height, base.height);
    const delta = sub(moved.position, base.position);
    const texelsX = dot(delta, basis.right) / base.texel[0];
    const texelsY = dot(delta, basis.up) / base.texel[1];
    near(texelsX, Math.round(texelsX), 1e-6);
    near(texelsY, Math.round(texelsY), 1e-6);
  }
});

test('fitShadowFrustum: texels stay a few centimetres wide on every preset', () => {
  for (const preset of Object.values(presets)) {
    if (!preset.shadow) continue;
    const fit = fitShadowFrustum({ bounds: BOUNDS, minY: -0.5, maxY: 24, dir: look.sun.direction, mapSize: preset.shadow, margin: look.sun.shadowMargin });
    assert.ok(Math.max(...fit.texel) < 0.13, `${preset.name}: ${fit.texel}`);
  }
});

// ------------------------------------------------------------------------------------------------
// Lamps
// ------------------------------------------------------------------------------------------------

test('pickRealLights: highest priority first, brighter first among equals, never more than the budget', () => {
  const lamps = [
    { priority: 3, intensity: 30 }, // 0 el
    { priority: 10, intensity: 34 }, // 1 work
    { priority: 8, intensity: 160 }, // 2 flood
    { priority: 10, intensity: 34 }, // 3 work
    { priority: 5, intensity: 90 }, // 4 street
    { priority: 5, intensity: 120 }, // 5 street, brighter
    { priority: 8, intensity: 160 }, // 6 flood
  ];
  assert.deepEqual(pickRealLights(lamps, 0), []);
  assert.deepEqual(pickRealLights(lamps, 2), [1, 3]);
  assert.deepEqual(pickRealLights(lamps, 4), [1, 3, 2, 6]);
  assert.deepEqual(pickRealLights(lamps, 5), [1, 3, 2, 6, 5]);
  assert.deepEqual(pickRealLights(lamps, 99), [1, 3, 2, 6, 5, 4, 0]);
  assert.deepEqual(pickRealLights([], 4), []);
  assert.deepEqual(pickRealLights(lamps, -3), []);
  assert.deepEqual(pickRealLights(lamps, NaN), []);
});

test('pickRealLights: every quality preset stays within its budget', () => {
  const lamps = Array.from({ length: 40 }, (_, i) => ({ priority: i % 7, intensity: 10 + i }));
  for (const preset of Object.values(presets)) {
    const picked = pickRealLights(lamps, preset.lights);
    assert.equal(picked.length, Math.min(lamps.length, preset.lights), preset.name);
    assert.equal(new Set(picked).size, picked.length, 'no lamp twice');
  }
});

test('lampClaim: priority decides at equal distance, nearness beats priority, the claim halves at the reach', () => {
  const reach = look.lamps.rig.reach;
  near(lampClaim(5, reach, reach), lampClaim(5, 0, reach) / 2);
  assert.ok(lampClaim(10, 20, reach) > lampClaim(5, 20, reach));
  // On the avenue a lamp under the El (priority 5) a few metres off outranks a shop work light (10) 25 m away…
  assert.ok(lampClaim(5, 6, reach) > lampClaim(10, 25, reach));
  // …and inside the shop it is the other way round.
  assert.ok(lampClaim(10, 6, reach) > lampClaim(5, 14, reach));
  // A holder's advantage is not enough to keep a light on the far side of the block.
  assert.ok(lampClaim(10, 60, reach) * look.lamps.rig.keep < lampClaim(5, 8, reach));
  let last = Infinity;
  for (let d = 0; d < 100; d += 5) {
    const c = lampClaim(4, d, reach);
    assert.ok(c < last && c > 0);
    last = c;
  }
});

test('continueRow: carries the spacing of the row on past both ends', () => {
  // The testbed hangs a lamp every 10 m from −35 to 45.
  const own = [];
  for (let x = -35; x <= 45; x += 10) own.push(x);
  const more = continueRow(own, -46, 46, 60, 7);
  assert.ok(more.length >= 10);
  for (const x of more) {
    assert.ok(x < -46 || x > 46, `${x} is outside the block`);
    near(((x + 35) % 10 + 10) % 10, 0, 1e-9); // on the same 10 m grid
    assert.ok(x >= -106 && x <= 106);
  }
  assert.ok(more.includes(55) && more.includes(-45) === false && more.includes(-55));
  // Sorted, no duplicates.
  for (let i = 1; i < more.length; i++) assert.ok(more[i] > more[i - 1]);
});

test('continueRow: one missing lamp does not double the step; short rows fall back', () => {
  const gappy = continueRow([0, 10, 20, 40, 50], -5, 55, 30, 7);
  assert.ok(gappy.includes(60) && gappy.includes(70) && gappy.includes(-10));
  const single = continueRow([3], 0, 20, 30, 8);
  assert.ok(single.every((x) => x < 0 || x > 20));
  assert.ok(single.includes(27) && single.includes(-5));
  const none = continueRow([], 0, 20, 25, 10);
  assert.ok(none.length > 0 && none.every((x) => x < 0 || x > 20));
});

// ------------------------------------------------------------------------------------------------
// The train
// ------------------------------------------------------------------------------------------------

test('trainTimeline: approach, over and gone add up, in both directions', () => {
  for (const dir of [1, -1]) {
    const tl = trainTimeline({ minX: -46, maxX: 46, dir, speed: 16, length: 80, runUp: 140 });
    near(tl.approach, 140 / 16);
    near(tl.over, (92 + 80) / 16);
    near(tl.gone, 140 / 16);
    near(tl.tEnd, tl.approach + tl.over + tl.gone);
    // The nose is at the near edge when "over" begins, the tail at the far edge when it ends.
    near(tl.head(tl.tOver), dir > 0 ? -46 : 46);
    near(tl.head(tl.tGone) - dir * 80, dir > 0 ? 46 : -46);
    assert.equal(tl.phase(-0.1), null);
    assert.equal(tl.phase(0), 'approach');
    assert.equal(tl.phase(tl.tOver - 0.01), 'approach');
    assert.equal(tl.phase(tl.tOver + 0.01), 'over');
    assert.equal(tl.phase(tl.tGone + 0.01), 'gone');
    assert.equal(tl.phase(tl.tEnd), null);
    // It starts and ends far outside the block.
    assert.ok(Math.abs(tl.head(0)) >= 46 + 140 - 1e-9);
  }
});

test('trainTimeline: the configured train spends a few seconds overhead', () => {
  const cfg = look.train;
  const length = cfg.cars * cfg.carLength + (cfg.cars - 1) * cfg.carGap;
  const tl = trainTimeline({ minX: -46, maxX: 46, dir: 1, speed: cfg.speed, length, runUp: cfg.runUp });
  assert.ok(tl.over > 6 && tl.over < 16, `over for ${tl.over} s`);
  assert.ok(tl.tEnd < cfg.every[0], 'a pass is finished before the next may start');
});

test('createTrainSchedule: first train overhead on time, then one every 40–70 s, alternating direction', () => {
  const rng = createRng(7);
  const schedule = createTrainSchedule({ rng, firstPass: 20, every: [40, 70], approach: 8.8 });
  near(schedule.nextAt, 11.2);
  let now = schedule.nextAt;
  const dirs = [];
  for (let i = 0; i < 40; i++) {
    dirs.push(schedule.begin(now));
    const gap = schedule.nextAt - now;
    assert.ok(gap >= 40 && gap <= 70, `gap ${gap}`);
    now = schedule.nextAt;
  }
  assert.equal(schedule.count, 40);
  assert.deepEqual(dirs.slice(0, 4), [1, -1, 1, -1]);
  // The same seed gives the same timetable.
  const again = createTrainSchedule({ rng: createRng(7), firstPass: 20, every: [40, 70], approach: 8.8 });
  again.begin(11.2);
  const first = createTrainSchedule({ rng: createRng(7), firstPass: 20, every: [40, 70], approach: 8.8 });
  first.begin(11.2);
  assert.equal(again.nextAt, first.nextAt);
});

test('createTrainSchedule: a long approach never schedules the first train in the past', () => {
  const schedule = createTrainSchedule({ rng: createRng(1), firstPass: 5, every: [40, 70], approach: 30 });
  assert.ok(schedule.nextAt >= 1);
  schedule.setNext(3);
  assert.equal(schedule.nextAt, 3);
});

// ------------------------------------------------------------------------------------------------
// Haze
// ------------------------------------------------------------------------------------------------

test('haze: clear inside the block, 2 % left at the configured reach, gameplay distances stay readable', () => {
  const k = endHazeK(look.fog.endReach);
  assert.equal(hazeOutside(0, 0, BOUNDS, k, look.fog.endClear), 1);
  assert.equal(hazeOutside(45, -33, BOUNDS, k, look.fog.endClear), 1);
  assert.equal(distanceOutside(46 + look.fog.endClear, 0, BOUNDS, look.fog.endClear), 0);
  near(hazeOutside(46 + look.fog.endClear + look.fog.endReach, 0, BOUNDS, k, look.fog.endClear), 0.02, 1e-9);
  // Monotonic along the avenue.
  let last = 1;
  for (let x = 46; x < 200; x += 5) {
    const t = hazeOutside(x, 0, BOUNDS, k, look.fog.endClear);
    assert.ok(t <= last + 1e-12);
    last = t;
  }
  near(distanceOutside(56, 44, BOUNDS), Math.hypot(10, 10));
  assert.equal(endHazeK(0), 0);
  // An enemy 40 m away keeps almost all of his contrast; the far end of the avenue keeps most of it.
  assert.ok(fogTransmittance(40, look.fog.density) > 0.92);
  assert.ok(fogTransmittance(92, look.fog.density) > 0.6);
});

// ------------------------------------------------------------------------------------------------
// The city
// ------------------------------------------------------------------------------------------------

test('planCity: nothing inside the bounds, on the avenue or on the cross streets', () => {
  for (const seed of [1994, 1, 77]) {
    const rng = createRng(seed);
    const city = planCity(rng, BOUNDS, { avenueZ: 0 });
    assert.ok(city.length > 30, `${city.length} buildings`);
    for (const b of city) {
      assert.ok(b.x1 > b.x0 && b.z1 > b.z0 && b.h > 6 && b.h < 40, JSON.stringify(b));
      const inBounds = b.x1 > BOUNDS.minX - 3 && b.x0 < BOUNDS.maxX + 3 && b.z1 > BOUNDS.minZ - 3 && b.z0 < BOUNDS.maxZ + 3;
      assert.ok(!inBounds, `building inside the block: ${JSON.stringify(b)}`);
      const onAvenue = b.z1 > -11.49 && b.z0 < 11.49;
      assert.ok(!onAvenue, `building on the avenue: ${JSON.stringify(b)}`);
      assert.ok(['+z', '-z', '+x', '-x'].includes(b.face));
      assert.ok(b.floors >= 2 && b.bays >= 2);
    }
    // The avenue is lined on both sides beyond both ends.
    for (const [side, dir] of [['+z', 1], ['-z', 1], ['+z', -1], ['-z', -1]]) {
      const row = city.filter((b) => b.face === side && (dir > 0 ? b.x0 > 46 : b.x1 < -46) && Math.abs((side === '+z' ? b.z1 : b.z0)) < 12);
      assert.ok(row.length >= 3, `avenue row ${side} ${dir}: ${row.length}`);
    }
    assert.ok(city.some((b) => b.core) && city.some((b) => !b.core), 'both core and optional buildings');
    assert.ok(city.some((b) => b.tower), 'some water towers');
  }
});

test('planCity: the same seed plans the same city', () => {
  const a = planCity(createRng(5), BOUNDS, { avenueZ: 0 });
  const b = planCity(createRng(5), BOUNDS, { avenueZ: 0 });
  assert.deepEqual(a, b);
});

test('skylineProfile: a filled roof line with towers worth a light, taller in the middle when asked', () => {
  const plain = skylineProfile(createRng(3), 256, { base: 0.2, variance: 0.3 });
  assert.equal(plain.heights.length, 256);
  for (const h of plain.heights) assert.ok(h > 0.05 && h <= 0.97);
  for (const t of plain.towers) assert.ok(t.at >= 0 && t.at <= 1 && t.top > 0.2);

  const mean = (arr, from, to) => {
    let s = 0;
    for (let i = from; i < to; i++) s += arr[i];
    return s / (to - from);
  };
  let centre = 0;
  let edges = 0;
  for (let seed = 1; seed <= 12; seed++) {
    const p = skylineProfile(createRng(seed), 256, { base: 0.16, variance: 0.3, tall: 0.75 });
    centre += mean(p.heights, 108, 148);
    edges += (mean(p.heights, 0, 40) + mean(p.heights, 216, 256)) / 2;
  }
  assert.ok(centre > edges * 1.25, `centre ${centre} vs edges ${edges}`);
});

// ------------------------------------------------------------------------------------------------
// Interior
// ------------------------------------------------------------------------------------------------

test('interiorTarget: a fresh setInterior() wins, a stale one yields to the camera', () => {
  assert.equal(interiorTarget(null, Infinity, 0.7), 0.7);
  assert.equal(interiorTarget(1, 0.1, 0, 0.25), 1);
  assert.equal(interiorTarget(1, 0.3, 0, 0.25), 0);
  assert.equal(interiorTarget(0, 0, 1, 0.25), 0);
  assert.equal(interiorTarget(2, 0, 0), 1);
  assert.equal(interiorTarget(undefined, 0, -3), 0);
  assert.equal(interiorTarget(null, 0, NaN), 0);
});

// ------------------------------------------------------------------------------------------------
// Config
// ------------------------------------------------------------------------------------------------

test('look.js: every lamp kind is drawable and every quality preset has a detail row', () => {
  const kinds = ['street', 'el', 'work', 'flood', 'neon', 'window'];
  for (const kind of kinds) {
    const style = look.lamps.kinds[kind];
    assert.ok(style, kind);
    assert.ok(style.pool && style.pool.radius > 0 && style.pool.max >= style.pool.min, kind);
    assert.ok(style.glow && style.glow.size > 0, kind);
    assert.ok(style.ref > 0 && style.realGain > 0, kind);
  }
  assert.ok(look.lamps.kinds[look.lamps.fallbackKind]);
  for (const name of Object.keys(presets)) {
    const d = look.detail[name];
    assert.ok(d, name);
    for (const key of ['cones', 'motes', 'cityFull', 'farRing', 'switchers', 'grit']) assert.equal(typeof d[key], 'boolean', `${name}.${key}`);
  }
  // Test and low: no cones, no motes, fewer cards.
  for (const name of ['test', 'low']) {
    assert.equal(look.detail[name].cones, false);
    assert.equal(look.detail[name].motes, false);
    assert.equal(look.detail[name].farRing, false);
  }
  assert.ok(look.train.every[0] >= 40 && look.train.every[1] <= 70);
  near(Math.hypot(...look.sun.direction) > 0 ? 1 : 0, 1);
  assert.deepEqual(look.viewmodel.keyDirection, look.sun.direction, 'the viewmodel key matches the street key');
});
