// Buzzard flight over and out of things (src/enemies/logic.js): climbing over what stands on the leg
// ahead, backing out of geometry into free air, and the two ways past an obstacle at the El's edge.
// Review finding enemies #0: reinforcements pinned to (and sunk into) facades they could not climb.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import * as config from '../src/config/enemies.js';
import { createPhysics } from '../src/physics.js';
import {
  climbHit,
  climbOver,
  createSolids,
  deckEntry,
  deckSlide,
  droneOverlaps,
  droneSolid,
  groundHit,
  groundUnder,
  inRoom,
  isPole,
  packSolids,
  planAroundDeck,
  pushOut,
  routeIndoors,
  solidsStale,
} from '../src/enemies/logic.js';

const K = config.buzzard;
const v = (x, y, z) => ({ x, y, z });
const box = (min, max, extra = {}) => ({ min: v(...min), max: v(...max), bulletOnly: false, playerOnly: false, tag: '', ...extra });
const near = (a, b, eps = 1e-9, label = '') => assert.ok(Math.abs(a - b) <= eps, `${label} expected ${b} ± ${eps}, got ${a}`);

// A rear wall like S3's (roof 7.8 m) between a drone in the lane and a player on the avenue.
const WALL = box([-4, 0, 11], [22, 7.8, 26]);
const EL = { y: 6.5, minX: -46, maxX: 46, minZ: -5.4, maxZ: 5.4 };
/** The packed form the flight loops read. */
const S = (list, el = EL) => packSolids(createSolids(), list, el);
/** climbOver, answering the height it raised the wanted point to (0: it did not). */
const climb = (pack, pos, want, K) => (climbOver(pack, pos, want, K) ? climbHit.height : 0);

test('flight: what is solid for a drone', () => {
  assert.equal(droneSolid(WALL), true);
  assert.equal(droneSolid(box([0, 0, 0], [1, 8, 1], { playerOnly: true, tag: 'cage-fence' })), false, 'the Cage fence is not an 8 m wall');
  assert.equal(droneSolid(box([0, 0, 0], [1, 8, 1], { playerOnly: true, tag: 'seal' })), false);
  assert.equal(droneSolid(box([0, 0, 0], [1, 8, 1], { playerOnly: true, tag: 'hoist' })), true, 'the hoist netting is');
  assert.equal(droneSolid(box([0, 0, 0], [1, 8, 1], { playerOnly: true, tag: 'office-glass' })), true, 'and the office glass');
  assert.equal(droneSolid(box([0, 0, 0], [1, 8, 1], { playerOnly: true, tag: 'railing' })), false);
  assert.equal(droneSolid(box([0, 0, 0], [1, 8, 1], { bulletOnly: true })), false);
  assert.equal(isPole(box([22.8, 0, 7.5], [23, 7.4, 7.8])), true, 'a street lamp');
  assert.equal(isPole(box([1, 2.9, 7.5], [19, 4, 7.55])), false, 'a long thin hoarding is a wall');
});

test('flight: climbOver raises the wanted height over a roof on the leg, and only then', () => {
  // Behind the wall at 5 m, wanting 5 m on the far side: climb to roof + minHeight.
  const want = [5, 5, -2];
  near(climb(S([WALL]), v(4, 5, 27), want, K), 7.8 + K.minHeight);
  near(want[1], 7.8 + K.minHeight);
  // Already above the roof: a floor, stay clear of it but no higher than needed.
  want[1] = 5;
  climb(S([WALL]), v(4, 9.5, 24), want, K);
  near(want[1], 7.8 + K.floorClearance + K.halfHeight, 1e-9, 'over the roof');
  // Wanting higher than the roof needs anyway: untouched.
  want[1] = 12;
  assert.equal(climb(S([WALL]), v(4, 5, 27), want, K), 0);
  assert.equal(want[1], 12);
  // Leg pointing away from the wall, or the wall further than climbLook ahead: nothing to climb.
  want[1] = 5;
  want[2] = 40;
  assert.equal(climb(S([WALL]), v(4, 5, 27), want, K), 0);
  want[2] = -2;
  assert.equal(climb(S([WALL]), v(4, 5, 26 + 0.5 + K.climbLook + 0.6), want, K), 0, 'out of reach');
  // The leg is widened by the airframe radius: a corner just beside the centre line still counts.
  const want2 = [30, 5, 30];
  assert.ok(climb(S([WALL]), v(22.4, 5, 30), [22.4, 5, 0], K) > 0, 'passing the corner 0.4 m off');
  assert.equal(climb(S([WALL]), v(22.7, 5, 30), [22.7, 5, 0], K), 0, '0.7 m off: clear');
  assert.equal(climb(S([WALL]), v(25, 5, 20), want2, K), 0);
});

test('flight: climbOver ignores poles, overhangs, player-only walls, the El and anything above maxAltitude', () => {
  const at = v(0, 5, 10);
  const want = () => [0, 5, 0];
  const lamp = box([-0.1, 0, 6], [0.1, 7.4, 6.3]);
  assert.equal(climb(S([lamp]), at, want(), K), 0, 'a lamp post: go around it');
  const awning = box([-2, 7.5, 5.5], [2, 7.7, 8]);
  assert.equal(climb(S([awning]), at, want(), K), 0, 'an overhang it passes under');
  const fence = box([-5, 0, 7], [5, 8, 7.2], { playerOnly: true, tag: 'cage-fence' });
  assert.equal(climb(S([fence]), at, want(), K), 0, 'the Cage fence');
  const hoist = box([-1.5, 2.8, 7], [1.5, 9.4, 9], { playerOnly: true, tag: 'hoist' });
  near(climb(S([hoist]), at, want(), K), 9.4 + K.minHeight, 1e-9, 'the hoist netting');
  const girder = box([-46, 5.5, 4.4], [46, 6.5, 4.8]);
  assert.equal(climb(S([girder]), at, want(), K), 0, 'the El is planAroundDeck\'s');
  const tower = box([-5, 0, 6], [5, K.maxAltitude + 2, 8]);
  assert.equal(climb(S([tower]), at, want(), K), 0, 'nothing to gain above maxAltitude');
});

test('flight: pushOut puts an airframe sunk into a wall back into free air, never freezing it', () => {
  // Sunk into the wall face under the roof edge, the way the reviewers found them.
  const pos = v(4, 7.6, 26.1);
  const vel = v(0.5, -1, -2);
  assert.equal(droneOverlaps(S([WALL]), pos, K), true);
  assert.ok(pushOut(S([WALL]), pos, vel, K, { minX: -46, maxX: 46, minZ: -34, maxZ: 34 }) > 0);
  assert.equal(droneOverlaps(S([WALL]), pos, K), false);
  // The shortest way out here is back out of the face (0.42 m) rather than up over the roof edge
  // (0.44 m), and the velocity no longer points back in.
  near(pos.z, 26 + K.radius + 0.02, 1e-9, 'out of the face');
  near(pos.y, 7.6);
  assert.equal(vel.z, 0);
  // A little higher up the face, up over the edge is shorter.
  const high = v(4, 7.75, 26.1);
  pushOut(S([WALL]), high, v(0, -1, 0), K, null);
  near(high.y, 7.8 + K.halfHeight + 0.02, 1e-9, 'up over the edge');
  // Deep inside a wall (the middle of a building): out through the nearest face.
  const deep = v(4, 4, 25.2);
  pushOut(S([WALL]), deep, v(0, 0, 0), K, null);
  assert.equal(droneOverlaps(S([WALL]), deep, K), false);
  near(deep.z, 26 + K.radius + 0.02, 1e-9, 'out the back face, 1.3 m');
  // In free air nothing moves.
  const free = v(4, 5, 30);
  assert.equal(pushOut(S([WALL]), free, v(0, 0, 0), K, null), 0);
  assert.deepEqual(free, v(4, 5, 30));
});

test('flight: pushOut respects the bounds, steps off poles sideways, and frees a drone wedged in a gap', () => {
  // Against a wall at the edge of the block: the way out sideways would leave the bounds, so it goes up.
  const bounds = { minX: -46, maxX: 46, minZ: -34, maxZ: 34 };
  const edge = box([40, 0, -10], [46, 9, 10]);
  const pos = v(44.6, 6, 0);
  pushOut(S([edge]), pos, v(0, 0, 0), K, bounds);
  assert.equal(droneOverlaps(S([edge]), pos, K), false);
  assert.ok(pos.x >= bounds.minX + K.boundsMargin && pos.x <= bounds.maxX - K.boundsMargin, 'still inside the bounds');
  // Coming down onto a lamp post: off it sideways, not up onto it.
  const lamp = box([22.8, 0, 7.5], [23, 7.4, 7.8]);
  const perch = v(22.95, 7.5, 7.6);
  pushOut(S([lamp]), perch, v(0, -1, 0), K, bounds);
  assert.equal(droneOverlaps(S([lamp]), perch, K), false);
  near(perch.y, 7.5, 1e-9, 'not lifted');
  // Wedged between two boxes 0.8 m apart: the sideways pushes would only trade one for the other.
  const a = box([0, 0, 0], [2, 6, 4]);
  const b = box([2.8, 0, 0], [5, 6.5, 4]);
  const wedged = v(2.4, 3, 2);
  pushOut(S([a, b]), wedged, v(0, 0, 0), K, bounds);
  assert.equal(droneOverlaps(S([a, b]), wedged, K), false, `free at ${JSON.stringify(wedged)}`);
});

test('flight: deck entry and slide past an obstacle at the El edge', () => {
  const D = config.buzzard.deck;
  // Low beside the deck: straight across the edge, at the plan's height.
  const want = [5, 9, -2];
  deckEntry(v(19.2, 5.4, 8), want, EL, D);
  assert.deepEqual(want, [19.2, EL.y - D.under, EL.maxZ - 1]);
  deckEntry(v(19.2, 5.4, -8), want, EL, D);
  near(want[2], EL.minZ + 1);
  // Holding over the hoist: slide along the edge away from it, at its height.
  const hoist = box([19.1, 2.8, 7], [22, 9.4, 11], { playerOnly: true, tag: 'hoist' });
  const w = [0, 10.7, 9.4];
  assert.ok(climb(S([hoist]), v(19.2, 10.7, 7.9), w, K) > 0);
  assert.equal(climbHit.box, hoist, 'the climb says what was in the way');
  near(w[1], 9.4 + K.floorClearance + K.halfHeight, 1e-9, 'over the netting: a floor');
  deckSlide(v(19.2, 10.7, 7.9), w, climbHit.box, D);
  near(w[0], 19.2 - D.slide, 1e-9, 'west of its middle: further west');
  near(w[2], 7.9);
  deckSlide(v(22.5, 5, 8.2), w, hoist, D);
  near(w[0], 22.5 + D.slide, 1e-9, 'east of it: further east');
  assert.equal(climb(S([hoist]), v(30, 5, 8), [35, 5, 8], K), 0);
  assert.equal(climbHit.box, null);
  // The plan still decides the rest: a drone already low beside the deck is told to go in (plan 1).
  const w2 = [5, 9, -2];
  assert.equal(planAroundDeck(19.2, 5.4, 8, w2, EL, D), 1);
});

test('flight: into the shop through a doorway, not down onto its roof', () => {
  // The shop: 30 × 20 m, its roll-up door in the south wall (z = -11), a doorway found there.
  const room = { box: { min: v(-24, 0, -31), max: v(6, 6.3, -11) }, list: [{ ox: -12, oz: -8.5, ix: -12, iz: -13.5, y: 3.6 }] };
  // Wanted in the office, the drone out over the avenue: to the outside point, at the doorway's height.
  const want = [-21, 8.3, -29];
  assert.equal(routeIndoors(v(5, 6, -2), want, room), 1);
  assert.deepEqual(want, [-12, 3.6, -8.5]);
  // At the outside point but too high: still lining up.
  const w2 = [-21, 8.3, -29];
  assert.equal(routeIndoors(v(-12, 4.4, -8.6), w2, room), 1);
  // Lined up: through to the inside point.
  const w3 = [-21, 8.3, -29];
  assert.equal(routeIndoors(v(-12.3, 3.7, -9), w3, room), 2);
  assert.deepEqual(w3, [-12, 3.6, -13.5]);
  // In the doorway, still going; past the wall's outer face it is inside, and steers for the spot itself.
  const w4 = [-21, 8.3, -29];
  assert.equal(routeIndoors(v(-12, 3.6, -10.8), w4, room), 2);
  assert.equal(routeIndoors(v(-12, 3.6, -11.2), [-21, 8.3, -29], room), 0);
  // Inside already, or not wanted inside, or no doorway: untouched.
  for (const [pos, w, r] of [
    [v(-12, 3.6, -14), [-21, 8.3, -29], room],
    [v(5, 6, -2), [-21, 8.3, 0], room],
    [v(5, 6, -2), [-21, 8.3, -29], { box: room.box, list: [] }],
  ]) {
    const copy = w.slice();
    assert.equal(routeIndoors(pos, w, r), 0);
    assert.deepEqual(w, copy);
  }
  // Over the roof counts as outside.
  assert.equal(inRoom(room.box, v(-12, 8, -20), 0, true), false);
  assert.equal(inRoom(room.box, v(-12, 4, -20), 0, true), true);
});

test('flight: the packed solids follow the collider list', () => {
  const list = [WALL, box([0, 0, 0], [1, 8, 1], { playerOnly: true, tag: 'seal' }), box([22.8, 0, 7.5], [23, 7.4, 7.8])];
  const pack = S(list);
  assert.equal(pack.n, 2, 'the seal is left out');
  assert.equal(pack.boxes[0], WALL);
  assert.equal(pack.data[9 + 6], 1, 'the lamp is a pole');
  assert.equal(solidsStale(pack, list), false);
  list.push(box([5, 0, 5], [6, 3, 6]));
  assert.equal(solidsStale(pack, list), true, 'one added');
  packSolids(pack, list, EL);
  list.splice(0, 1);
  assert.equal(solidsStale(pack, list), true, 'one removed');
  // More boxes than the first allocation holds.
  const many = Array.from({ length: 600 }, (_, i) => box([i, 0, 0], [i + 0.5, 3, 2]));
  assert.equal(S(many).n, 600);
  assert.equal(S(many).data[9 * 599], 599);
});

test('flight: groundUnder gives the same answer as physics.groundHeight', () => {
  const physics = createPhysics({});
  physics.setBounds({ minX: -20, maxX: 20, minZ: -20, maxZ: 20 });
  let seed = 7;
  const random = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  for (let i = 0; i < 60; i++) {
    const x = -18 + random() * 36;
    const z = -18 + random() * 36;
    const y = random() < 0.3 ? 2 + random() * 3 : 0;
    physics.addBox({ min: [x, y, z], max: [x + 0.5 + random() * 5, y + 0.3 + random() * 6, z + 0.5 + random() * 4], playerOnly: random() < 0.1, bulletOnly: random() < 0.1 });
  }
  physics.addBox({ min: [-3, 0, -3], max: [3, 9, 3], playerOnly: true, tag: 'hoist' }); // solid for a drone, not ground
  const pack = S(physics.boxes, null);
  for (let i = 0; i < 400; i++) {
    const pos = new THREE.Vector3(-20 + random() * 40, random() * 12, -20 + random() * 40);
    groundUnder(pack, pos, 0.3);
    assert.equal(groundHit.y, physics.groundHeight(pos.x, pos.z, pos.y + 0.3), `at ${pos.x}, ${pos.y}, ${pos.z}`);
  }
});
