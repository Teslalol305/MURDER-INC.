// The pure enemy rules (src/enemies/logic.js) against the numbers in docs/DESIGN.md 3.1 and the
// reference notes: attack tokens and their fairness, sight, the reaction and exposure ramps, aim
// spread, fire-position scoring, hit-volume rays, the bolt sweep and flight planning around the El.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as config from '../src/config/enemies.js';
import {
  aimSpread,
  createTokens,
  exposureStep,
  firePositionCost,
  followSpeed,
  inFireBand,
  inFov,
  inSight,
  leadPoint,
  planAroundDeck,
  rayCapsule,
  rayEllipsoid,
  raySphere,
  reactionTime,
  seenStep,
  segmentEntersRect,
  segmentHitsUpright,
} from '../src/enemies/logic.js';

const near = (actual, expected, eps = 1e-9, label = '') =>
  assert.ok(Math.abs(actual - expected) <= eps, `${label} expected ${expected} ± ${eps}, got ${actual}`);

/** Base tables with one difficulty laid over them, the way enemies.setDifficulty() does it. */
function tuned(name) {
  const d = config.difficulty[name];
  return {
    ai: { ...config.ai, ...d.ai },
    goon: { ...config.goon, ...d.goon },
    buzzard: { ...config.buzzard, ...d.buzzard },
  };
}

// ---------------------------------------------------------------------------------------- tokens

test('tokens: the limit, the crowd limit and the gap between grants', () => {
  const { ai } = tuned('boss'); // 2 normal, 3 in a crowd, 1.25 s apart
  const tokens = createTokens();
  assert.equal(tokens.limit(5, ai), 2);
  assert.equal(tokens.limit(6, ai), 3);

  assert.equal(tokens.request('goon', 0, 4, ai), true);
  assert.equal(tokens.request('goon', 0.5, 4, ai), false, 'inside the gap');
  assert.equal(tokens.request('goon', 1.25, 4, ai), true, 'the gap has passed');
  assert.equal(tokens.held, 2);
  assert.equal(tokens.request('goon', 5, 4, ai), false, 'both tokens are out');
  assert.equal(tokens.request('goon', 5, 6, ai), true, 'a crowd unlocks the third');
  assert.equal(tokens.request('goon', 9, 6, ai), false);

  tokens.release();
  assert.equal(tokens.held, 2);
  assert.equal(tokens.request('goon', 9.1, 6, ai), true);
  tokens.release();
  tokens.release();
  tokens.release();
  tokens.release(); // one too many is harmless
  assert.equal(tokens.held, 0);

  tokens.request('buzzard', 20, 1, ai);
  tokens.reset();
  assert.equal(tokens.held, 0);
  assert.equal(tokens.request('buzzard', 20.1, 1, ai), true, 'a reset also clears the gap');
});

test('tokens: Goons and Buzzards alternate when both want to fire', () => {
  for (const name of ['hustler', 'boss', 'kingpin']) {
    const { ai } = tuned(name);
    const tokens = createTokens();
    const grants = [];
    // Both types ask every frame; a burst takes about a second, then the token comes back.
    const busy = [];
    for (let frame = 0; frame < 60 * 40; frame++) {
      const now = frame / 60;
      while (busy.length && busy[0] <= now) {
        busy.shift();
        tokens.release();
      }
      // The Goon asks first every frame: without the fairness rule it would win every time.
      for (const type of ['goon', 'buzzard']) {
        if (tokens.request(type, now, 4, ai)) {
          grants.push(type);
          busy.push(now + 1);
        }
      }
    }
    assert.ok(grants.length > 12, `${name}: ${grants.length} grants`);
    for (let i = 1; i < grants.length; i++) assert.notEqual(grants[i], grants[i - 1], `${name}: grant ${i} repeats ${grants[i]}`);
  }
});

test('tokens: one type alone is only held back by the gap, and a silent type does not block the other for long', () => {
  const { ai } = tuned('kingpin'); // gap 0.85
  const tokens = createTokens();
  const times = [];
  for (let frame = 0; frame < 60 * 6; frame++) {
    const now = frame / 60;
    if (tokens.request('goon', now, 3, ai)) {
      times.push(now);
      tokens.release();
    }
  }
  assert.ok(times.length >= 7, `${times.length} grants in 6 s`);
  for (let i = 1; i < times.length; i++) near(times[i] - times[i - 1], 0.85, 1 / 60 + 1e-9);

  // A Buzzard asked once and then lost sight: the Goons wait at most gapFactor × gap for it.
  tokens.reset();
  assert.equal(tokens.request('goon', 10, 3, ai), true);
  tokens.release();
  assert.equal(tokens.request('buzzard', 10.8, 3, ai), false, 'inside the gap');
  assert.equal(tokens.request('goon', 10.9, 3, ai), false, 'the Buzzard asked a moment ago');
  assert.equal(tokens.request('goon', 10.8 + ai.tokenFairness.refusedWithin + 0.05, 3, ai), true, 'the Buzzard went quiet');
  tokens.release();
  tokens.reset();
  tokens.request('goon', 20, 3, ai);
  tokens.release();
  let granted = -1;
  for (let now = 20.5; now < 24 && granted < 0; now += 1 / 60) {
    tokens.request('buzzard', now, 3, { ...ai, tokens: 0, tokensCrowd: 0 }); // keeps asking, never gets one
    if (tokens.request('goon', now, 3, ai)) granted = now;
  }
  near(granted - 20, ai.tokenFairness.gapFactor * ai.tokenGap, 0.03, 'a Goon fires again after 2.2 gaps');
});

// ------------------------------------------------------------------------------------ perception

test('sight: 45 m range, a 200° horizontal cone, ignored when engaged or within 3.5 m', () => {
  const { ai } = tuned('kingpin');
  const deg = (d) => (d * Math.PI) / 180;
  near(ai.fov, deg(200));
  // Facing −Z (yaw 0): straight ahead, 99° off to either side, 101° off, directly behind.
  const at = (angle, dist = 10) => [-Math.sin(angle) * dist, -Math.cos(angle) * dist];
  assert.equal(inFov(0, ...at(0), ai.fov), true);
  assert.equal(inFov(0, ...at(deg(99)), ai.fov), true);
  assert.equal(inFov(0, ...at(deg(-99)), ai.fov), true);
  assert.equal(inFov(0, ...at(deg(101)), ai.fov), false);
  assert.equal(inFov(0, ...at(deg(180)), ai.fov), false);
  // The cone turns with the unit: yaw +90° looks toward −X.
  assert.equal(inFov(deg(90), -10, 0, ai.fov), true);
  assert.equal(inFov(deg(90), 10, 0, ai.fov), false);

  const behind = at(deg(180), 10);
  assert.equal(inSight(10, ...behind, 0, false, ai), false, 'behind an unaware unit');
  assert.equal(inSight(10, ...behind, 0, true, ai), true, 'an engaged unit has no blind side');
  assert.equal(inSight(3.4, ...at(deg(180), 3.4), 0, false, ai), true, 'point blank');
  assert.equal(inSight(3.6, ...at(deg(180), 3.6), 0, false, ai), false);
  assert.equal(inSight(44.9, ...at(0, 44.9), 0, false, ai), true);
  assert.equal(inSight(45, ...at(0, 45), 0, false, ai), false, 'out of range');
  assert.equal(inSight(45, ...at(0, 45), 0, true, ai), false, 'out of range even when engaged');
});

test('reaction: 0.55 s for a Goon and 0.4 s for a Buzzard on patrol, × 0.45 once suspicious; peeks add up', () => {
  const { ai, goon, buzzard } = tuned('kingpin');
  near(reactionTime(goon.reaction, 'patrol', ai), 0.55);
  near(reactionTime(buzzard.reaction, 'patrol', ai), 0.4);
  near(reactionTime(goon.reaction, 'investigate', ai), 0.2475);
  near(reactionTime(buzzard.reaction, 'search', ai), 0.18);

  // 0.3 s in view, 0.2 s behind a column, 0.3 s in view again: the accumulator keeps most of the first peek.
  let seen = 0;
  for (let i = 0; i < 2; i++) seen = seenStep(seen, true, 0.15, ai);
  seen = seenStep(seen, false, 0.2, ai);
  near(seen, 0.3 - 0.6 * 0.2);
  for (let i = 0; i < 2; i++) seen = seenStep(seen, true, 0.15, ai);
  assert.ok(seen < goon.reaction && seen > 0.45, `0.6 s of peeking is not quite enough: ${seen}`);
  assert.equal(seenStep(0.05, false, 0.15, ai), 0, 'never negative');
});

test('exposure: full accuracy after 1 / gain seconds in sight, gone about two seconds after breaking it', () => {
  for (const [name, seconds] of [['hustler', 1 / 0.08], ['boss', 10], ['kingpin', 1 / 0.14]]) {
    const { ai } = tuned(name);
    let exposure = 0;
    let t = 0;
    while (exposure < 1 && t < 30) {
      exposure = exposureStep(exposure, true, 1 / 60, ai);
      t += 1 / 60;
    }
    near(t, seconds, 0.05, name);
    assert.equal(exposureStep(1, true, 1, ai), 1, 'clamped at 1');
    t = 0;
    while (exposure > 0) {
      exposure = exposureStep(exposure, false, 1 / 60, ai);
      t += 1 / 60;
    }
    near(t, 1 / 0.45, 0.05, `${name}: falls at 0.45 per second`);
    assert.equal(exposureStep(0, false, 1, ai), 0, 'clamped at 0');
  }
});

test('spread: far → near with exposure, × (1 + speed · 0.30) for Goons and × (1 + speed · 0.45) for Buzzards', () => {
  const { goon, buzzard } = tuned('boss');
  const g = (exposure, speed) => aimSpread(goon.spreadFar, goon.spreadNear, exposure, speed, goon.spreadPerSpeed);
  const b = (exposure, speed, extra) => aimSpread(buzzard.spreadFar, buzzard.spreadNear, exposure, speed, buzzard.spreadPerSpeed, extra);
  near(g(0, 0), 0.12);
  near(g(1, 0), 0.045);
  near(g(0.5, 0), 0.0825);
  near(g(0, 5) / g(0, 0), 2.5, 1e-9, 'a player at 5 m/s makes a Goon 2.5 times worse');
  near(b(0, 0), 0.065);
  near(b(1, 0), 0.018);
  near(b(0, 5) / b(0, 0), 3.25, 1e-9, 'and a Buzzard 3.25 times worse');
  near(b(1, 0, buzzard.damagedSpread), 0.027, 1e-9, 'a damaged Buzzard: × 1.5');
  near(g(2, 0), 0.045, 1e-9, 'exposure is clamped');
  // Sprinting (6.4 m/s) against a fresh Boss Goon: 0.095 × 2.92 rad, nearly 16° either way.
  const boss = tuned('kingpin').goon;
  near(aimSpread(boss.spreadFar, boss.spreadNear, 0, 6.4, boss.spreadPerSpeed), 0.095 * (1 + 6.4 * 0.3));
});

// -------------------------------------------------------------------------------- fire positions

test('fire positions: the 8–18 m band, travel, kind bias, jitter', () => {
  const { goon } = tuned('kingpin');
  assert.equal(inFireBand(7.9, goon), false);
  assert.equal(inFireBand(8, goon), true);
  assert.equal(inFireBand(18, goon), true);
  assert.equal(inFireBand(18.1, goon), false);

  const K = goon.positionCost;
  const player = { x: 0, z: 0 };
  const self = { x: 0, z: 20 };
  const spot = (x, z, kind = 'random', sight = true, cover = false) => ({ x, z, kind, sight, cover });
  const cost = (c, others = [], jitter = 0) => firePositionCost(c, self, player, others, others.length, jitter, K);

  near(cost(spot(0, 10)), 0.9 * 10, 1e-9, 'travel only');
  near(cost(spot(0, 10, 'authored')) - cost(spot(0, 10)), -2, 1e-9, 'authored points are preferred');
  near(cost(spot(0, 10, 'arc')) - cost(spot(0, 10)), 1, 1e-9, 'arc points are the last resort');
  near(cost(spot(0, 10), [], 1) - cost(spot(0, 10)), 3, 1e-9, 'jitter 0…3');
  near(cost(spot(0, 10, 'random', false)) - cost(spot(0, 10)), 22, 1e-9, 'no line of sight');
  near(cost(spot(0, 10, 'authored', true, true)) - cost(spot(0, 10, 'authored')), -4, 1e-9, 'cover that still sees the player');
  near(cost(spot(0, 10, 'authored', false, true)) - cost(spot(0, 10, 'authored', false)), 0, 1e-9, 'cover without a shot is no bonus');
  // A spot with a shot 15 m of walking further away still beats a blind one next door…
  assert.ok(cost(spot(12, 0)) < cost(spot(0, 12, 'authored', false)));
  // …but not one on the far side of the block.
  assert.ok(cost(spot(12, -12)) > cost(spot(0, 12, 'authored', false)));
});

test('fire positions: Goons spread around the player and do not stack', () => {
  const { goon } = tuned('kingpin');
  const K = goon.positionCost;
  const player = { x: 0, z: 0 };
  const self = { x: 0, z: 14 };
  const spot = (x, z) => ({ x, z, kind: 'random', sight: true, cover: false });
  const other = (x, z, destX = x, destZ = z) => ({ x, z, destX, destZ });
  const cost = (c, others) => firePositionCost(c, self, player, others, others.length, 0, K);
  const alone = cost(spot(0, 12), []);

  near(cost(spot(0, 12), [other(0, 30)]) - alone, 14, 1e-9, 'same bearing as another Goon, far apart');
  near(cost(spot(0, 12), [other(0, 12.5)]) - alone, 14 + 16, 1e-9, 'same bearing and shoulder to shoulder');
  near(cost(spot(0, 12), [other(40, 0, 1, 12)]) - alone, 16 + 14 * (1 - Math.atan2(1, 12) / (Math.PI / 6)), 1e-6, 'his destination counts, not where he stands');
  near(cost(spot(0, 12), [other(12, 0)]) - alone, 0, 1e-9, '90° round the player: no penalty');
  const off15 = cost(spot(0, 12), [other(Math.sin(Math.PI / 12) * 30, Math.cos(Math.PI / 12) * 30)]) - alone;
  near(off15, 7, 1e-6, '15° off his line: half the penalty');
  // Only the first `count` records are read (the caller reuses a scratch array).
  near(firePositionCost(spot(0, 12), self, player, [other(0, 30), other(0, 12.5)], 1, 0, K) - alone, 14, 1e-9);

  // Two Goons choosing in turn out of a ring of spots end up on different sides.
  const ring = [];
  for (let i = 0; i < 12; i++) ring.push(spot(Math.sin((i * Math.PI) / 6) * 12, Math.cos((i * Math.PI) / 6) * 12));
  const best = (others) => ring.reduce((a, b) => (cost(a, others) <= cost(b, others) ? a : b));
  const first = best([]);
  const second = best([other(first.x, first.z)]);
  assert.deepEqual([first.x, first.z], [ring[0].x, ring[0].z]);
  const apart = Math.abs(Math.atan2(second.x, second.z) - Math.atan2(first.x, first.z));
  assert.ok(apart >= Math.PI / 6 - 1e-9, `the second Goon stands ${Math.round((apart * 180) / Math.PI)}° round`);
});

test('path following: full speed on heading, slow in corners, stop to turn, ease in on arrival', () => {
  const { goon } = tuned('kingpin');
  near(followSpeed(5, 0, 10, goon), 5);
  near(followSpeed(5, 0.5, 10, goon), 3.75);
  near(followSpeed(5, 1.1, 10, goon), 2.25);
  assert.equal(followSpeed(5, 1.11, 10, goon), 0, 'over 1.1 rad off: turn in place');
  near(followSpeed(5, 0, 0.5, goon), 1.7, 1e-9, '0.4 + 2.6 × remaining');
  near(followSpeed(1.5, 0, 0.1, goon), 0.66);
});

// ----------------------------------------------------------------------------------- hit volumes

test('rays: sphere, capsule and ellipsoid entry distances', () => {
  // Sphere of radius 1 at the origin.
  near(raySphere(0, 0, 5, 0, 0, -1, 0, 0, 0, 1), 4);
  assert.equal(raySphere(0, 1.01, 5, 0, 0, -1, 0, 0, 0, 1), Infinity);
  assert.equal(raySphere(0, 0, 5, 0, 0, 1, 0, 0, 0, 1), Infinity, 'pointing away');
  assert.equal(raySphere(0, 0.5, 0, 1, 0, 0, 0, 0, 0, 1), 0, 'starting inside');

  // Upright capsule: axis (0, 0.3, 0) → (0, 1.4, 0), radius 0.27.
  const cap = (ox, oy, oz, dx, dy, dz) => rayCapsule(ox, oy, oz, dx, dy, dz, 0, 0.3, 0, 0, 1.4, 0, 0.27);
  near(cap(0, 1, 5, 0, 0, -1), 5 - 0.27, 1e-9, 'the side');
  near(cap(0.2, 1, 5, 0, 0, -1), 5 - Math.sqrt(0.27 ** 2 - 0.2 ** 2), 1e-9);
  assert.equal(cap(0.28, 1, 5, 0, 0, -1), Infinity, 'just past the side');
  near(cap(0, 5, 0, 0, -1, 0), 5 - 1.67, 1e-9, 'straight down onto the top cap');
  near(cap(0, 1.6, 5, 0, 0, -1), 5 - Math.sqrt(0.27 ** 2 - 0.2 ** 2), 1e-9, 'the rounded top');
  assert.equal(cap(0, 1.68, 5, 0, 0, -1), Infinity, 'over the top');
  assert.equal(cap(0, 0.02, 5, 0, 0, -1), Infinity, 'under the bottom cap');
  assert.equal(cap(0.1, 1, 0.1, 0, 0, -1), 0, 'starting inside');
  assert.equal(cap(0, 1, 5, 0, 0, 1), Infinity, 'pointing away');
  // A leaning capsule (a Goon bent forward): the hit follows the axis.
  near(rayCapsule(0, 1, 5, 0, 0, -1, 0, 0, 0, 0, 1, -1, 0.25), 5 + 1 - 0.25 * Math.SQRT2, 1e-9);
  // Degenerate capsule = sphere.
  near(rayCapsule(0, 0, 5, 0, 0, -1, 0, 0, 0, 0, 0, 0, 1), 4);

  // Buzzard: horizontal radius 0.5, half height 0.22.
  const ell = (ox, oy, oz, dx, dy, dz) => rayEllipsoid(ox, oy, oz, dx, dy, dz, 10, 6, 0, 0.5, 0.22);
  near(ell(0, 6, 0, 1, 0, 0), 9.5, 1e-9, 'from the side');
  near(ell(10, 10, 0, 0, -1, 0), 4 - 0.22, 1e-9, 'from above');
  assert.equal(ell(0, 6.23, 0, 1, 0, 0), Infinity, 'over it');
  assert.equal(ell(0, 6.21, 0, 1, 0, 0) < 10, true, 'grazing the top');
  assert.equal(ell(10, 6.1, 0, 1, 0, 0), 0, 'starting inside');
  assert.equal(ell(20, 6, 0, 1, 0, 0), Infinity, 'behind the ray');
  const diagonal = Math.SQRT1_2;
  const t = ell(10 - 3, 6 + 3, 0, diagonal, -diagonal, 0);
  const hit = [10 - 3 + diagonal * t - 10, 6 + 3 - diagonal * t - 6];
  near((hit[0] / 0.5) ** 2 + (hit[1] / 0.22) ** 2, 1, 1e-9, 'the diagonal hit lies on the surface');
});

test('bolts: the sweep against the player capsule, standing and crouched', () => {
  const T = config.buzzard.boltTarget; // radius 0.36, 0.35 … 1.5 above the feet, 1.0 when crouched
  const hits = (p, q, top = T.top) => segmentHitsUpright(...p, ...q, 0, T.bottom, top, 0, T.radius);
  near(hits([0, 1, 5], [0, 1, -5]), 0.5, 1e-9, 'through the middle: closest approach half way');
  assert.ok(hits([0.35, 1, 5], [0.35, 1, -5]) >= 0, 'inside the radius');
  assert.equal(hits([0.37, 1, 5], [0.37, 1, -5]), -1, 'just outside it');
  assert.ok(hits([0, 1.8, 5], [0, 1.8, -5]) >= 0, 'the rounded top reaches 1.86');
  assert.equal(hits([0, 1.9, 5], [0, 1.9, -5]), -1, 'over the head');
  assert.equal(hits([0, 1.5, 5], [0, 1.5, -5], T.crouchTop), -1, 'crouching ducks under a head-high bolt');
  assert.ok(hits([0, 1.3, 5], [0, 1.3, -5], T.crouchTop) >= 0);
  assert.equal(hits([0, 1, 5], [0, 1, 1]), -1, 'a step that ends short of the player');
  assert.ok(hits([0, 1, 1], [0, 1, 0.3]) >= 0, 'the step that reaches him');
  near(hits([0, 1, 0.2], [0, 1, -3]), 0.2 / 3.2, 1e-9, 'starting inside: the closest approach is on the axis');
  // A diving bolt from a drone 6 m up, 14 m out.
  const from = [14, 7, 0];
  const dir = [-14, -6, 0];
  assert.ok(hits(from, [from[0] + dir[0] * 1.2, from[1] + dir[1] * 1.2, 0]) >= 0);
  assert.equal(hits([from[0], from[1], 0.6], [from[0] + dir[0] * 1.2, from[1] + dir[1] * 1.2, 0.6]), -1, 'a side step of 0.6 m dodges it');
  assert.equal(segmentHitsUpright(1, 1, 1, 1, 1, 1, 0, 0, 2, 0, 0.5), -1, 'a point outside');
  assert.equal(segmentHitsUpright(0.2, 1, 0, 0.2, 1, 0, 0, 0, 2, 0, 0.5), 0, 'a point inside');
});

test('bolts: partial lead on a moving target', () => {
  const out = [0, 0, 0];
  // 35 m away, bolt speed 70: half a second of flight. The player strafes at 4 m/s.
  leadPoint(0, 0, 0, 35, 0, 0, 0, 0, 4, 70, 1, out);
  assert.deepEqual(out, [35, 0, 2]);
  leadPoint(0, 0, 0, 35, 0, 0, 0, 0, 4, 70, 0.5, out);
  assert.deepEqual(out, [35, 0, 1]);
  leadPoint(0, 0, 0, 35, 0, 0, 0, 0, 4, 70, 0, out);
  assert.deepEqual(out, [35, 0, 0]);
  const [lo, hi] = config.buzzard.lead;
  assert.ok(lo > 0 && hi < 1, 'never no lead, never perfect lead');
});

// ------------------------------------------------------------------------------- flight planning

test('segmentEntersRect: entry parameter of a 2D segment into a rectangle', () => {
  const rect = [-10, 10, -2, 2];
  near(segmentEntersRect(0, -6, 0, 6, ...rect), 4 / 12);
  assert.equal(segmentEntersRect(0, 0, 0, 6, ...rect), 0, 'starting inside');
  assert.equal(segmentEntersRect(0, -6, 0, -3, ...rect), -1, 'stops short');
  assert.equal(segmentEntersRect(-20, -6, 20, -6, ...rect), -1, 'passes beside');
  assert.equal(segmentEntersRect(12, -6, 12, 6, ...rect), -1, 'passes beyond the end');
  near(segmentEntersRect(-14, -4, 14, 4, ...rect), (14 - 7) / 28, 1e-9, 'a diagonal comes in through the long side');
});

test('flight planning: a drone never steers through the El deck', () => {
  const el = { y: 6.5, minX: -46, maxX: 46, minZ: -5.2, maxZ: 5.2 };
  const K = config.buzzard.deck;
  const lowCap = el.y - K.under;
  const highFloor = el.y + K.thickness + K.over;
  const plan = (p, want) => {
    const out = [...want];
    const code = planAroundDeck(...p, out, el, K);
    return { code, out };
  };

  // Far from the El, a leg that never comes near it: untouched.
  assert.deepEqual(plan([0, 9, 20], [10, 9, 14]), { code: 0, out: [10, 9, 14] });

  // Under the deck: the wanted height is capped until the drone is clear of the footprint.
  let r = plan([0, 4, 0], [10, 9, 0]);
  assert.equal(r.code, 1);
  near(r.out[1], lowCap);
  r = plan([0, 4, 0], [0, 9, 20]);
  near(r.out[1], lowCap, 1e-9, 'heading out: still capped while under it');
  assert.deepEqual(plan([0, 4, 0], [10, 3, 0]).out, [10, 3, 0], 'lower is fine');

  // Outside and low enough, wanting a point under the deck: go under.
  r = plan([0, 4.5, 12], [0, 9, 0]);
  assert.equal(r.code, 1);
  assert.deepEqual([r.out[0], r.out[2]], [0, 0]);
  near(r.out[1], lowCap);

  // Outside and too high: hold short of the footprint while descending.
  r = plan([0, 9, 14], [0, 9, 0]);
  assert.equal(r.code, 3);
  near(r.out[1], lowCap);
  near(r.out[2], el.maxZ + K.margin + K.hold, 1e-9, 'held outside');
  r = plan([0, 9, el.maxZ + K.margin + 1], [0, 9, 0]);
  assert.equal(r.code, 3);
  near(r.out[2], el.maxZ + K.margin + 1, 1e-9, 'already at the edge: hold position');
  // The same leg once low enough goes through.
  assert.equal(plan([0, lowCap + 0.5, 9], [0, 9, 0]).code, 1);

  // A leg right across the avenue (an orbit over a player on the far sidewalk) is planned the same way.
  r = plan([0, 8, 14], [3, 8, -14]);
  assert.equal(r.code, 3);
  assert.ok(r.out[2] > el.maxZ + K.margin, 'waits on its own side');

  // Over the deck (a patrol circle that drifted there): leave sideways at height, never straight down.
  r = plan([0, 9.5, 1], [0, 5, 0]);
  assert.equal(r.code, 2);
  assert.ok(r.out[1] >= highFloor && r.out[2] > el.maxZ + K.margin, JSON.stringify(r.out));
  r = plan([0, 9.5, -1], [0, 5, -1]);
  assert.ok(r.out[2] < el.minZ - K.margin, 'toward the nearer side');
  r = plan([0, 9.5, 1], [4, 6, -20]);
  assert.ok(r.out[2] < el.minZ - K.margin, 'or the side the wanted point is on');
  // High above it and staying high: nothing to do.
  assert.equal(plan([0, highFloor + 1, 0], [10, highFloor + 0.5, 3]).code, 0);
  assert.equal(plan([0, highFloor + 1, 14], [0, highFloor + 0.5, -14]).code, 0, 'crossing well above');

  // No El in the level: untouched.
  const out = [0, 9, 0];
  assert.equal(planAroundDeck(0, 9, 14, out, null, K), 0);
  assert.deepEqual(out, [0, 9, 0]);

  // Simulated approach: a drone steering at the planned point every step never enters the slab.
  for (const start of [[20, 10, 16], [-8, 8, -15], [5, 12, 2], [0, 3, 0], [30, 7.2, 9]]) {
    for (const goal of [[0, 6, 0], [10, 11, -18], [-20, 5.5, 3], [12, 9, 20]]) {
      const p = [...start];
      for (let step = 0; step < 4000; step++) {
        const out2 = [...goal];
        planAroundDeck(...p, out2, el, K);
        const d = [out2[0] - p[0], out2[1] - p[1], out2[2] - p[2]];
        const len = Math.hypot(...d);
        if (len < 0.05) break;
        const move = Math.min(len, 0.1);
        for (let i = 0; i < 3; i++) p[i] += (d[i] / len) * move;
        const inSlab = p[2] > el.minZ && p[2] < el.maxZ && p[1] > el.y - 0.3 && p[1] < el.y + K.thickness + 0.3;
        assert.ok(!inSlab, `from ${start} to ${goal}: inside the deck at ${p.map((n) => n.toFixed(2))}`);
      }
    }
  }
});
