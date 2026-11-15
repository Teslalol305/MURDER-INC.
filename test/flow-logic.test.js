// The flow's pure rules (src/game/*, src/config/flow.js, src/config/text.js): wave composition and
// arrival order, the holdout formulas at n = 1, 5, 10 and their caps, kill scoring, spawn-point scoring,
// the 8-way compass, the debrief rating, the music-intensity driver, the radio queue timing, the card
// data and the title camera's loop and fades.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import * as flow from '../src/config/flow.js';
import * as text from '../src/config/text.js';
import { musicIntensity, waveIsOver } from '../src/game/music.js';
import { createRadio } from '../src/game/radio.js';
import { compassSector, pickSpawn, spawnScore } from '../src/game/spawn.js';
import { accuracy, cardData } from '../src/game/stats.js';
import { createTitleCamera } from '../src/game/titlecam.js';
import { BUZZARD, GOON, holdoutOrder, holdoutWave, killScore, missionOrder, pursuitType } from '../src/game/waves.js';

const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps, `${a} ≉ ${b}`);
const count = (order, type) => order.filter((t) => t === type).length;
const H = flow.holdout;

// ------------------------------------------------------------------------------------------------
// Waves
// ------------------------------------------------------------------------------------------------

test('flow: a story wave alternates from a Buzzard, the rest follow', () => {
  assert.deepEqual(missionOrder(2, 5), [BUZZARD, GOON, BUZZARD, GOON, GOON, GOON, GOON]);
  assert.deepEqual(missionOrder(3, 1), [BUZZARD, GOON, BUZZARD, BUZZARD]);
  assert.deepEqual(missionOrder(0, 2), [GOON, GOON]);
  assert.deepEqual(missionOrder(0, 0), []);
  assert.deepEqual(missionOrder(-1, 'x'), []);
});

test('flow: every difficulty row gives the DESIGN 3.1 wave sizes and patrols', () => {
  const want = {
    hustler: { patrol: [1, 3], waves: [[2, 3], [2, 4], [3, 5]], maxAlive: 9, every: 7, budget: 5, regen: [4, 25] },
    boss: { patrol: [2, 4], waves: [[2, 5], [3, 6], [4, 7]], maxAlive: 11, every: 5.5, budget: 8, regen: [5.5, 16] },
    kingpin: { patrol: [2, 5], waves: [[3, 6], [4, 7], [5, 8]], maxAlive: 13, every: 4.5, budget: 12, regen: [7, 10] },
  };
  assert.deepEqual(Object.keys(flow.difficulty), flow.difficulties);
  assert.equal(flow.defaultDifficulty, 'boss');
  for (const [name, w] of Object.entries(want)) {
    const d = flow.difficulty[name];
    assert.deepEqual([d.patrol.buzzard, d.patrol.goon], w.patrol, name);
    assert.deepEqual(d.waves.map((x) => [x.buzzard, x.goon]), w.waves, name);
    assert.equal(d.maxAlive, w.maxAlive);
    assert.equal(d.pursuitEvery, w.every);
    assert.equal(d.pursuitBudget, w.budget);
    assert.deepEqual([d.regen.delay, d.regen.rate], w.regen);
    for (const x of d.waves) {
      const order = missionOrder(x.buzzard, x.goon);
      assert.equal(count(order, BUZZARD), x.buzzard);
      assert.equal(count(order, GOON), x.goon);
      assert.equal(order[0], BUZZARD);
    }
  }
});

test('flow: holdout formulas at n = 1, 5, 10 and at their caps', () => {
  const rows = [
    // n, total, buzzards, stagger, hp, damage, cooldown, extraAlive
    [1, 7, 3, 0.86, 1, 1, 1, 0],
    [5, 15, 5, 0.7, 1.28, 1.2, 0.88, 2],
    [10, 25, 6, 0.5, 1.63, 1.45, 0.73, 5],
  ];
  for (const [n, total, buzzards, stagger, hp, damage, cooldown, extra] of rows) {
    const w = holdoutWave(n, H);
    assert.equal(w.wave, n);
    assert.equal(w.total, total, `total at ${n}`);
    assert.equal(w.buzzards, buzzards, `buzzards at ${n}`);
    assert.equal(w.goons, total - buzzards);
    assert.equal(w.order.length, total);
    assert.equal(count(w.order, BUZZARD), buzzards);
    near(w.stagger, stagger);
    near(w.scale.hp, hp);
    near(w.scale.damage, damage);
    near(w.scale.cooldown, cooldown);
    assert.equal(w.extraAlive, extra);
  }
  // caps
  assert.equal(H.total(13), 30);
  assert.equal(H.total(40), 30);
  near(H.buzzardShare(10), 0.25);
  near(H.buzzardShare(30), 0.25);
  near(H.stagger(14), 0.35);
  near(H.stagger(50), 0.35);
  near(H.hpScale(23), 2.5);
  near(H.hpScale(99), 2.5);
  near(H.damageScale(21), 2);
  near(H.damageScale(99), 2);
  near(H.cooldownScale(15), 0.6);
  near(H.cooldownScale(99), 0.6);
  assert.equal(H.extraAlive(10), 5);
  assert.equal(H.extraAlive(99), 5);
  const capped = holdoutWave(20, H);
  assert.equal(capped.total, 30);
  assert.equal(capped.buzzards, 8); // round(30 × 0.25)
  // a wave number below 1 is wave 1
  assert.equal(holdoutWave(0, H).total, 7);
});

test('flow: holdout Buzzards are spread evenly through the arrival order', () => {
  assert.deepEqual(holdoutOrder(7, 3), [GOON, BUZZARD, GOON, BUZZARD, GOON, BUZZARD, GOON]);
  for (const [total, b] of [[7, 3], [15, 5], [25, 6], [30, 8], [5, 5], [3, 0], [4, 9]]) {
    const order = holdoutOrder(total, b);
    assert.equal(order.length, total);
    assert.equal(count(order, BUZZARD), Math.min(total, b), `${total}/${b}`);
  }
  // no long run of one type in a mid-size wave
  const order = holdoutOrder(25, 6).join('');
  assert.ok(!/(goon){7}/.test(order), order);
});

test('flow: holdout kill score and wave bonus', () => {
  const S = H.score;
  assert.equal(killScore('goon', 1, S), 150);
  assert.equal(killScore('buzzard', 1, S), 100);
  assert.equal(killScore('goon', 5, S), 210);
  assert.equal(killScore('buzzard', 10, S), 190);
  assert.equal(killScore('something', 1, S), 100);
  assert.equal(killScore('goon', 0, S), 150);
  assert.equal(S.waveClear(1), 500);
  assert.equal(S.waveClear(4), 2000);
  assert.deepEqual([H.resupply.reserve, H.resupply.reserveCap, H.resupply.heal, H.resupply.explosivesEvery], [90, 240, 35, 2]);
});

test('flow: pursuit arrivals are 35 % Buzzard', () => {
  assert.equal(flow.pursuit.buzzardShare, 0.35);
  assert.equal(pursuitType(0.1, 0.35), BUZZARD);
  assert.equal(pursuitType(0.349, 0.35), BUZZARD);
  assert.equal(pursuitType(0.35, 0.35), GOON);
  assert.equal(pursuitType(0.9, 0.35), GOON);
});

// ------------------------------------------------------------------------------------------------
// Spawn points and the compass
// ------------------------------------------------------------------------------------------------

test('flow: compass sectors, clockwise from north = −Z', () => {
  const cases = [
    [0, -1, 'NORTH'], [1, -1, 'NORTH-EAST'], [1, 0, 'EAST'], [1, 1, 'SOUTH-EAST'],
    [0, 1, 'SOUTH'], [-1, 1, 'SOUTH-WEST'], [-1, 0, 'WEST'], [-1, -1, 'NORTH-WEST'],
    [0.3, -5, 'NORTH'], [-5, -0.3, 'WEST'], [0, 0, 'NORTH'],
  ];
  for (const [dx, dz, name] of cases) assert.equal(text.compass[compassSector(dx, dz)], name, `${dx},${dz}`);
  assert.equal(text.banners.contact('NORTH-EAST'), 'Contact — NORTH-EAST');
  assert.equal(text.banners.wave(3, 'EAST'), 'Wave 3 — EAST');
  assert.equal(text.banners.countdown(2, 3), 'Wave 2 in 3');
});

test('flow: spawn score follows the reference terms', () => {
  const S = flow.spawn.score;
  const base = { distance: 18, hidden: false, usedAgo: Infinity, random: 0 };
  near(spawnScore(base, S, 18), 2);
  near(spawnScore({ ...base, distance: 48 }, S, 18), 2.5);
  near(spawnScore({ ...base, distance: 98 }, S, 18), 2.5);
  near(spawnScore({ ...base, distance: 10 }, S, 18), -2);
  near(spawnScore({ ...base, hidden: true }, S, 18), 4.5);
  near(spawnScore({ ...base, usedAgo: 2 }, S, 18), -1);
  near(spawnScore({ ...base, usedAgo: 6 }, S, 18), 2);
  near(spawnScore({ ...base, random: 1 }, S, 18), 3.5);
});

test('flow: spawn picking prefers far, hidden and unused points of the right kind', () => {
  const S = flow.spawn.score;
  const P = (x, z, type = 'ground', tag = '') => ({ pos: { x, y: 0, z }, type, tag });
  const query = (over = {}) => ({ x: 0, z: 0, minDistance: 18, strict: false, hidden: () => false, usedAgo: () => Infinity, random: () => 0, ...over });

  const nearP = P(5, 0);
  const farP = P(30, 0);
  assert.equal(pickSpawn([nearP, farP], 'ground', query(), S), farP);
  // kind
  const air = P(40, 0, 'air');
  assert.equal(pickSpawn([nearP, air], 'air', query(), S), air);
  assert.equal(pickSpawn([air], 'ground', query(), S), null);
  assert.equal(pickSpawn([], 'ground', query(), S), null);
  // hidden beats visible at the same distance
  const a = P(25, 0);
  const b = P(0, 25);
  assert.equal(pickSpawn([a, b], 'ground', query({ hidden: (p) => p === b }), S), b);
  // a point used a moment ago loses to a fresh one
  assert.equal(pickSpawn([a, b], 'ground', query({ usedAgo: (p) => (p === a ? 1 : Infinity) }), S), b);
  // strict: a near hidden point never beats a far visible one
  const nearHidden = P(10, 0);
  assert.equal(pickSpawn([nearHidden, farP], 'ground', query({ minDistance: 32, strict: true, hidden: (p) => p === nearHidden }), S), farP);
  // strict with nothing far enough: the best of the near ones
  const n1 = P(5, 0);
  const n2 = P(12, 0);
  assert.equal(pickSpawn([n1, n2], 'ground', query({ minDistance: 32, strict: true }), S), n2);
  // the random term is bounded: it can reorder close calls but never overturn the hidden bonus
  let hiddenWins = 0;
  for (let i = 0; i < 200; i++) {
    const r = [Math.random(), Math.random()];
    let k = 0;
    if (pickSpawn([a, b], 'ground', query({ hidden: (p) => p === b, random: () => r[k++ % 2] }), S) === b) hiddenWins++;
  }
  assert.equal(hiddenWins, 200);
});

// ------------------------------------------------------------------------------------------------
// Rating and card data
// ------------------------------------------------------------------------------------------------

test('flow: the rating table, 0…5 points to Demo…Diamond', () => {
  const r = (time, shots, hits, retries) => flow.ratingPoints({ time, shots, hits, retries });
  assert.equal(r(200, 100, 60, 0), 5);
  assert.equal(r(269.9, 100, 50, 0), 5);
  assert.equal(r(270, 100, 50, 0), 4); // time 1
  assert.equal(r(399, 100, 30, 0), 3); // 1 + 1 + 1
  assert.equal(r(400, 100, 29, 0), 1); // only no retries
  assert.equal(r(400, 100, 29, 2), 0);
  assert.equal(r(100, 0, 0, 1), 2); // no shots: no accuracy points
  assert.equal(r(300, 10, 5, 1), 3);
  assert.deepEqual(text.ratings, ['Demo', 'Mixtape', 'Single', 'Gold', 'Platinum', 'Diamond']);
});

test('flow: card data for the death and debrief cards', () => {
  assert.equal(accuracy({ shots: 0, hits: 0 }), null);
  assert.equal(accuracy({ shots: 10, hits: 4 }), 0.4);
  assert.equal(accuracy({ shots: 2, hits: 5 }), 1);
  const run = { time: 250, reels: 3, total: 3, retries: 0, wave: 0, score: 0, kills: 17, shots: 120, hits: 66 };
  const d = cardData(run, { mode: 'mission', difficulty: 'boss', wavesCleared: 0, best: 0, newBest: false, headshots: 4 }, flow, text.ratings);
  for (const key of ['mode', 'time', 'reels', 'total', 'wave', 'kills', 'score', 'best', 'newBest', 'accuracy', 'retries', 'rating']) {
    assert.ok(key in d, `card data has ${key}`);
  }
  assert.equal(d.rating, 5);
  assert.equal(d.ratingName, 'Diamond');
  assert.equal(d.accuracy, 0.55);
  assert.equal(d.kills, 17);
  const h = cardData({ ...run, score: 1399.6, shots: 0, hits: 0 }, { mode: 'holdout', wavesCleared: 2, best: 1400, newBest: true }, flow, text.ratings);
  assert.equal(h.score, 1400);
  assert.equal(h.wave, 2);
  assert.equal(h.newBest, true);
  assert.equal(h.accuracy, null);
});

// ------------------------------------------------------------------------------------------------
// Music, radio, title camera
// ------------------------------------------------------------------------------------------------

test('flow: music intensity driver', () => {
  const M = flow.music;
  const calm = { allDone: false, queued: 0, alive: 0, waveAge: Infinity, sinceAlert: Infinity, sinceHit: Infinity, nearest: Infinity };
  assert.equal(musicIntensity(calm, M), 0.15);
  assert.equal(musicIntensity({ ...calm, allDone: true }, M), 1);
  assert.equal(musicIntensity({ ...calm, queued: 2 }, M), 1);
  assert.equal(musicIntensity({ ...calm, waveAge: 12, alive: 3 }, M), 1);
  assert.equal(musicIntensity({ ...calm, waveAge: 12, alive: 0 }, M), 0.15);
  assert.equal(musicIntensity({ ...calm, waveAge: 31, alive: 3, nearest: 40 }, M), 0.15);
  assert.equal(musicIntensity({ ...calm, sinceAlert: 9 }, M), 0.6);
  assert.equal(musicIntensity({ ...calm, sinceAlert: 10 }, M), 0.15);
  assert.equal(musicIntensity({ ...calm, sinceHit: 7.9 }, M), 0.6);
  assert.equal(musicIntensity({ ...calm, nearest: 25 }, M), 0.6);
  assert.equal(musicIntensity({ ...calm, nearest: 26 }, M), 0.15);
  // the hot window closes early once a wave is out and gone
  assert.equal(waveIsOver({ ...calm, waveAge: 6 }, M), true);
  assert.equal(waveIsOver({ ...calm, waveAge: 5 }, M), false);
  assert.equal(waveIsOver({ ...calm, waveAge: 7, alive: 1 }, M), false);
  assert.equal(waveIsOver({ ...calm, waveAge: 7, queued: 1 }, M), false);
});

test('flow: the radio queue types, holds, then plays the next line', () => {
  const lines = [];
  let cleared = 0;
  const radio = createRadio({ charsPerSec: 10, gap: 0.5, onLine: (t, s) => lines.push([t, s]), onClear: () => cleared++ });
  radio.say('0123456789', 2); // 1 s typing + 2 s hold + 0.5 s gap
  radio.say('abcde', 1);
  radio.say('', 1); // ignored
  assert.equal(radio.pending, 2);
  radio.update(0.1);
  assert.deepEqual(lines, [['0123456789', 2]]);
  for (let t = 0; t < 3.3; t += 0.1) radio.update(0.1);
  assert.equal(lines.length, 1, 'still on the first line');
  radio.update(0.25);
  assert.equal(lines.length, 2);
  assert.deepEqual(lines[1], ['abcde', 1]);
  assert.equal(radio.active, true);
  radio.clear();
  assert.equal(cleared, 1);
  assert.equal(radio.active, false);
  radio.clear();
  assert.equal(cleared, 1, 'clearing an idle radio says nothing');
  // every scripted line exists and holds as DESIGN 2 says
  const R = text.radio;
  assert.equal(R.speaker, 'IPX VAULT');
  assert.deepEqual([R.intro.secs, R.contact.secs, R.reel[0].secs, R.reel[1].secs, R.reel[2].secs, R.lowHealth.secs, R.done.secs, R.waveClear.secs], [4.4, 3.2, 3.6, 3.6, 4.5, 3.0, 2.4, 3.4]);
  assert.equal(R.waveClear.text(4), 'Wave 4 down. Resupply at your feet — 9 seconds.');
});

test('flow: title camera loop length, eased path and fades', () => {
  const T = flow.titleCamera;
  const path = [];
  for (let i = 0; i < 12; i++) path.push({ pos: new THREE.Vector3(-40 + i * 7, 3, 0), look: new THREE.Vector3(-36 + i * 7, 2, 1) });
  const cam = createTitleCamera(path, T);
  assert.ok(cam.usable);
  near(cam.length, 77, 1e-6);
  near(cam.duration, Math.max(26, 77 / 1.15), 1e-6);
  const camera = new THREE.PerspectiveCamera();
  assert.ok(cam.apply(0, camera) > 0.99, 'black at the loop start');
  near(cam.apply(cam.duration / 2, camera), 0, 1e-6);
  assert.equal(camera.fov, 50);
  assert.ok(camera.position.x > -10 && camera.position.x < 0, `mid-loop x ${camera.position.x}`);
  assert.ok(cam.apply(cam.duration - 0.01, camera) > 0.99, 'black at the loop end');
  assert.ok(cam.apply(cam.duration + 0.9, camera) > 0.2, 'fading in again on the next loop');
  // the ease: slower than linear at the ends
  cam.apply(cam.duration * 0.05, camera);
  assert.ok(camera.position.x < -40 + 77 * 0.05);
  // no path: the camera is left alone but the fade still runs
  const none = createTitleCamera([], T);
  const c2 = new THREE.PerspectiveCamera();
  c2.position.set(1, 2, 3);
  assert.equal(none.duration, 26);
  assert.ok(none.apply(0, c2) > 0.99);
  assert.deepEqual(c2.position.toArray(), [1, 2, 3]);
});

// ------------------------------------------------------------------------------------------------
// Copy (DESIGN 2 and 8.1)
// ------------------------------------------------------------------------------------------------

test('flow: v2 copy — eyebrow without a clock, location by time of day, boot line, zones', () => {
  assert.equal(text.title.eyebrow, 'IPX PRESENTS · HOLLIS, QUEENS');
  assert.equal(text.location.byTime.day, 'Hollis, Queens · Jamaica Ave · 4:15 PM');
  assert.equal(text.location.byTime.night, 'Hollis, Queens · Jamaica Ave · 02:14 AM');
  assert.equal(text.location.tagline, 'Three reels. One block. No backup.');
  assert.equal(text.boot.wait, 'Waiting on the next train');
  assert.equal(text.zoneName('west'), 'WEST END');
  assert.equal(text.zoneName('avenue'), 'THE AVENUE');
  assert.equal(text.zoneName('shop'), 'CHOP SHOP');
  assert.equal(text.zoneName('lot', -20), 'THE CAGE');
  assert.equal(text.zoneName('lot', 20), 'THE LOT');
  assert.equal(text.zoneName('nowhere'), 'THE AVENUE');
  assert.deepEqual(text.objectives.mission, ['Take back the three master reels', 'Two reels left', 'Last reel', 'Get to the IPX truck']);
  assert.equal(text.objectives.tally.wave(3, 12345), 'Wave 3 · 12,345');
  assert.equal(text.prompts.grab('E', '1'), 'Hold E — Grab reel 1');
  assert.equal(text.prompts.refuse, "Reels still out there — the truck won't roll without all three");
});

test('flow: timings and interaction numbers from the notes', () => {
  const t = flow.timing;
  assert.deepEqual([t.intro, t.introQuick, t.locationCardAt, t.introRadioAt, t.pauseDebounce, t.deathCard, t.debriefCard], [2.4, 1.1, 0.25, 0.9, 0.35, 1.5, 3.3]);
  const i = flow.interact;
  assert.deepEqual([i.range, i.vertical, i.facingDot, i.freeRange, i.hold, i.decay], [2.2, 2.5, 0.45, 0.9, 2.4, 1.6]);
  const s = flow.spawn;
  assert.deepEqual([s.firstDelay, s.stagger, s.far, s.patrolMinDistance, s.capRetry, s.poolRetry, s.poolTries, s.alertRadius, s.bannerSecs], [1.6, 0.85, 18, 32, 1, 1.5, 6, 60, 3.4]);
  const p = flow.pursuit;
  assert.deepEqual([p.firstDelay, p.minAlive, p.spawnDelay, p.realertEvery, p.realertRadius], [12, 4, 0.5, 4, 90]);
  assert.deepEqual([H.firstDelay, H.breather, H.firstSpawn, H.bannerSecs], [3.5, 9, 1.2, 3.6]);
  assert.deepEqual([flow.extraction.radius, flow.extraction.vertical, flow.extraction.refuseSecs, flow.extraction.refuseEvery], [2.5, 3.5, 3.5, 8]);
});
