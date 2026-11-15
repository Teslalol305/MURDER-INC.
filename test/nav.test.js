// Navigation: the occupancy grid, A*, string pulling and the helper queries of physics.nav.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { createPhysics } from '../src/physics.js';

const V = (x, z) => new THREE.Vector3(x, 0, z);

/** Small seeded generator with the two members physics uses from G.rng. */
function makeRng(seed) {
  let s = seed >>> 0;
  const next = () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return { next, fork: () => makeRng(seed + 1) };
}

/** An empty field from (0, 0) to (w, d). */
function field(w = 20, d = 20, G = {}) {
  const physics = createPhysics(G);
  physics.setBounds({ minX: 0, maxX: w, minZ: 0, maxZ: d });
  return physics;
}

const wall = (physics, x0, z0, x1, z1, opts = {}) => physics.addBox({ min: [x0, 0, z0], max: [x1, 3, z1], ...opts });

function pathLength(path) {
  let sum = 0;
  for (let i = 1; i < path.length; i++) sum += path[i].distanceTo(path[i - 1]);
  return sum;
}

/** A path is sound when it starts and ends where asked and every leg is a straight walkable segment. */
function assertSound(nav, path, a, b) {
  assert.ok(Array.isArray(path) && path.length >= 2, 'a path has at least a start and an end');
  for (const p of path) {
    assert.ok(p.isVector3 && p.y === 0);
    assert.ok(nav.isWalkable(p.x, p.z), `waypoint (${p.x}, ${p.z}) is walkable`);
  }
  for (let i = 1; i < path.length; i++) assert.ok(nav.clearLine(path[i - 1], path[i]), `leg ${i} is clear`);
  if (a) assert.ok(path[0].distanceTo(a) < 1e-9, 'starts at the start');
  if (b) assert.ok(path[path.length - 1].distanceTo(b) < 1e-9, 'ends at the goal');
}

test('grid: 0.5 m cells over the bounds, outer ring blocked', () => {
  const p = createPhysics({});
  p.setBounds({ minX: -46, maxX: 46, minZ: -34, maxZ: 34 });
  assert.equal(p.nav.cell, 0.5);
  assert.equal(p.nav.cols, 184);
  assert.equal(p.nav.rows, 136);
  assert.deepEqual(p.nav.origin, { x: -46, z: -34 });
  assert.equal(p.nav.isWalkable(-45.75, 0), false, 'border cell');
  assert.equal(p.nav.isWalkable(-45.25, 0), true, 'one cell in');
  assert.equal(p.nav.isWalkable(45.75, 0), false);
  assert.equal(p.nav.isWalkable(0, 33.75), false);
  assert.equal(p.nav.isWalkable(0, -33.75), false);
  assert.equal(p.nav.isWalkable(0, 0), true);
  assert.equal(p.nav.isWalkable(60, 0), false, 'outside the bounds');
  assert.equal(p.nav.isWalkable(0, -40), false);
});

test('grid: obstacles block the cells whose centre lies within 0.5 m of them', () => {
  const p = field();
  wall(p, 8, 8, 10, 10);
  // Cell centres sit at …, 7.25, 7.75, 8.25, …: 7.75 is inside the inflated box (7.5 … 10.5), 7.25 is not.
  assert.equal(p.nav.isWalkable(9, 9), false, 'inside');
  assert.equal(p.nav.isWalkable(7.75, 9), false, 'inflated west');
  assert.equal(p.nav.isWalkable(7.25, 9), true);
  assert.equal(p.nav.isWalkable(10.25, 9), false, 'inflated east');
  assert.equal(p.nav.isWalkable(10.75, 9), true);
  assert.equal(p.nav.isWalkable(9, 7.75), false, 'inflated north');
  assert.equal(p.nav.isWalkable(9, 7.25), true);
  assert.equal(p.nav.isWalkable(7.75, 7.75), false, 'inflated corner');
  assert.equal(p.nav.isWalkable(7.25, 7.25), true);
  // The whole cell answers the same as its centre.
  assert.equal(p.nav.isWalkable(7.51, 9.49), false);
  assert.equal(p.nav.isWalkable(7.49, 9.49), true);
});

test('grid: only boxes in the body band count, and the nav flags are honoured', () => {
  const p = field(40, 10);
  const at = (x) => p.nav.isWalkable(x, 5);
  p.addBox({ min: [4, 0, 4], max: [6, 0.4, 6], tag: 'kerb-high step' });
  p.addBox({ min: [9, 0, 4], max: [11, 0.47, 6], tag: 'just too tall to step over' });
  p.addBox({ min: [14, 1.6, 4], max: [16, 3, 6], tag: 'overhead' });
  p.addBox({ min: [19, 1.5, 4], max: [21, 3, 6], tag: 'head height' });
  p.addBox({ min: [24, 0, 4], max: [26, 2, 6], noNav: true });
  p.addBox({ min: [29, 0, 4], max: [31, 2, 6], bulletOnly: true });
  p.addBox({ min: [34, 0, 4], max: [36, 2, 6], playerOnly: true });
  assert.equal(at(5), true, 'low box is walked over');
  assert.equal(at(10), false, '0.47 m blocks');
  assert.equal(at(15), true, 'box starting above 1.5 m is walked under');
  assert.equal(at(20), false, 'box starting at 1.5 m blocks');
  assert.equal(at(25), true, 'noNav');
  assert.equal(at(30), true, 'bulletOnly');
  assert.equal(at(35), true, 'playerOnly');
});

test('grid: rebuilt lazily when boxes or bounds change', () => {
  const p = field();
  assert.equal(p.nav.isWalkable(10, 10), true);
  const box = wall(p, 9, 9, 11, 11);
  assert.equal(p.nav.isWalkable(10, 10), false, 'seen without an explicit rebuild');
  p.removeBox(box);
  assert.equal(p.nav.isWalkable(10, 10), true);
  p.setBounds({ minX: 0, maxX: 8, minZ: 0, maxZ: 8 });
  assert.equal(p.nav.isWalkable(10, 10), false, 'now outside');
  assert.equal(p.nav.cols, 16);
  p.nav.rebuild(); // explicit rebuild is allowed any time
  assert.equal(p.nav.isWalkable(4, 4), true);
});

test('grid: only a change that matters to walkers costs a rebuild, and only at the next query', () => {
  const p = field();
  assert.equal(p.nav.rebuilds, 0, 'nothing is built before the first query');
  const a = V(2, 2);
  const b = V(18, 18);
  for (let i = 0; i < 50; i++) {
    p.nav.isWalkable(10, 10);
    p.nav.findPath(a, b);
    p.nav.clearLine(a, b);
    p.nav.nearestWalkable(10, 10);
    p.nav.randomPoint(a, 4);
  }
  assert.equal(p.nav.rebuilds, 1, 'queries never rebuild a clean grid');

  // Boxes walkers ignore: bullet-only, player-only, noNav, too low to matter, overhead.
  p.addBox({ min: [5, 0, 5], max: [6, 2, 6], bulletOnly: true });
  p.addBox({ min: [5, 0, 7], max: [6, 2, 8], playerOnly: true });
  p.addBox({ min: [5, 0, 9], max: [6, 2, 10], noNav: true });
  p.addBox({ min: [7, 0, 5], max: [8, 0.3, 6] });
  const beam = p.addBox({ min: [7, 2.5, 7], max: [8, 3, 8] });
  p.removeBox(beam);
  p.nav.findPath(a, b);
  assert.equal(p.nav.rebuilds, 1);

  // A real obstacle: many changes, one rebuild, at the next query.
  const crate = wall(p, 9, 9, 11, 11);
  const more = [wall(p, 13, 3, 14, 4), wall(p, 3, 13, 4, 14)];
  assert.equal(p.nav.rebuilds, 1, 'adding does not rebuild by itself');
  assert.equal(p.nav.isWalkable(10, 10), false);
  p.nav.findPath(a, b);
  assert.equal(p.nav.rebuilds, 2);
  p.removeBox(crate);
  p.removeBoxes(more);
  assert.equal(p.nav.isWalkable(10, 10), true);
  assert.equal(p.nav.rebuilds, 3);
});

test('findPath: straight across open ground is just start and goal', () => {
  const p = field();
  const a = V(2.1, 2.3);
  const b = V(17.4, 13.2);
  const path = p.nav.findPath(a, b);
  assertSound(p.nav, path, a, b);
  assert.equal(path.length, 2, 'string pulling removed every intermediate cell');
  assert.notEqual(path[0], a, 'waypoints are new vectors');

  // Same cell: still a start and an end.
  const tiny = p.nav.findPath(V(5.1, 5.1), V(5.3, 5.4));
  assert.equal(tiny.length, 2);
  assert.ok(tiny[1].distanceTo(V(5.3, 5.4)) < 1e-9);
});

test('findPath: goes around an obstacle and string pulling keeps it short', () => {
  const p = field();
  wall(p, 9.5, 0, 10.5, 14); // leaves a gap between z = 14 and the far edge
  const a = V(3, 5);
  const b = V(17, 5);
  assert.equal(p.nav.clearLine(a, b), false);
  const path = p.nav.findPath(a, b);
  assertSound(p.nav, path, a, b);

  // The taut route rounds the two inflated corners at about (9, 14.5) and (11, 14.5).
  const taut = Math.hypot(6, 9.5) * 2 + 2;
  const length = pathLength(path);
  assert.ok(length >= taut - 0.2, `not shorter than possible: ${length.toFixed(2)} vs ${taut.toFixed(2)}`);
  assert.ok(length <= taut * 1.06, `close to the taut route: ${length.toFixed(2)} vs ${taut.toFixed(2)}`);
  assert.ok(path.length <= 5, `${path.length} waypoints for a path of about ${Math.round(length / 0.5)} cells`);
  assert.ok(Math.max(...path.map((q) => q.z)) > 14.4, 'passes through the gap');
});

test('findPath: winding route through two walls', () => {
  const p = field(30, 20);
  wall(p, 9.5, 0, 10.5, 15);
  wall(p, 19.5, 5, 20.5, 20);
  const a = V(3, 3);
  const b = V(27, 17);
  const path = p.nav.findPath(a, b);
  assertSound(p.nav, path, a, b);
  const xs = path.map((q) => q.x);
  assert.deepEqual([...xs].sort((m, n) => m - n), xs, 'never doubles back in x');
  assert.ok(pathLength(path) < 50);
  assert.ok(p.nav.lastExpansions > 0 && p.nav.lastExpansions < 60 * 40);
});

test('findPath: an unreachable goal returns null without searching', () => {
  const p = field(40, 40);
  // A sealed yard, 20 m square on the inside.
  wall(p, 9.5, 9.5, 30.5, 10);
  wall(p, 9.5, 30, 30.5, 30.5);
  wall(p, 9.5, 9.5, 10, 30.5);
  wall(p, 30, 9.5, 30.5, 30.5);
  const outside = V(4, 4);
  const centre = V(20, 20);
  assert.equal(p.nav.isWalkable(centre.x, centre.z), true, 'the goal itself is free ground');

  p.nav.findPath(outside, V(6, 30)); // prime the counter with a real search
  const before = p.nav.lastExpansions;
  assert.ok(before > 0);
  assert.equal(p.nav.findPath(outside, centre), null);
  assert.equal(p.nav.findPath(centre, outside), null);
  assert.equal(p.nav.lastExpansions, before, 'rejected by the area labels, not by a search');

  // Inside the yard everything still connects.
  assertSound(p.nav, p.nav.findPath(centre, V(12, 28)), centre, V(12, 28));

  // A goal just behind the wall is replaced by the nearest spot that can be reached.
  const behind = V(11.5, 20);
  const path = p.nav.findPath(outside, behind);
  assertSound(p.nav, path, outside);
  const end = path[path.length - 1];
  assert.ok(end.x < 9.5, 'stops on the outside of the wall');
  assert.ok(end.distanceTo(behind) < 3.5);
});

test('findPath: blocked start and goal snap to the nearest free cell', () => {
  const p = field();
  wall(p, 8, 8, 12, 12);
  const inside = V(8.3, 10.1); // inside the box, nearest free ground is to the west
  const b = V(17, 17);
  const path = p.nav.findPath(inside, b);
  assertSound(p.nav, path, null, b);
  assert.deepEqual(path[0].toArray(), [7.25, 0, 10.25], 'start moved to the nearest free cell centre');

  const back = p.nav.findPath(b, inside);
  assertSound(p.nav, back, b);
  assert.deepEqual(back[back.length - 1].toArray(), [7.25, 0, 10.25]);

  // Nothing free within 12 cells of a point far outside the grid.
  assert.equal(p.nav.findPath(V(-30, -30), b), null);
});

test('findPath: never squeezes diagonally between two obstacles', () => {
  const p = field(12, 12);
  // Two posts placed on cell corners block 2 × 2 cells each; the blocks touch at (5.5, 5.5).
  p.addBox({ min: [4.99, 0, 4.99], max: [5.01, 2, 5.01] });
  p.addBox({ min: [5.99, 0, 5.99], max: [6.01, 2, 6.01] });
  const a = V(5.25, 5.75);
  const b = V(5.75, 5.25);
  assert.equal(p.nav.isWalkable(a.x, a.z), true);
  assert.equal(p.nav.isWalkable(b.x, b.z), true);
  assert.equal(p.nav.isWalkable(5.25, 5.25), false);
  assert.equal(p.nav.isWalkable(5.75, 5.75), false);
  assert.equal(p.nav.clearLine(a, b), false, 'the diagonal clips both blocked cells');
  const path = p.nav.findPath(a, b);
  assertSound(p.nav, path, a, b);
  assert.ok(pathLength(path) > 3, 'walks around one of the posts instead');
});

test('findPath: refills a caller-supplied array', () => {
  const p = field();
  wall(p, 9.5, 0, 10.5, 14);
  const out = [];
  const first = p.nav.findPath(V(3, 5), V(17, 5), out);
  assert.equal(first, out);
  const kept = out[0];
  const n = out.length;
  assert.ok(n > 2);
  const second = p.nav.findPath(V(3, 5), V(6, 6), out);
  assert.equal(second, out);
  assert.equal(out.length, 2, 'shrinks to the new path');
  assert.equal(out[0], kept, 'reuses its vectors');
});

test('clearLine: straight walkable segments only', () => {
  const p = field();
  wall(p, 9.5, 0, 10.5, 14);
  assert.equal(p.nav.clearLine(V(3, 3), V(8, 12)), true);
  assert.equal(p.nav.clearLine(V(3, 3), V(3, 3)), true);
  assert.equal(p.nav.clearLine(V(3, 3), V(17, 3)), false, 'through the wall');
  assert.equal(p.nav.clearLine(V(3, 17), V(17, 17)), true, 'through the gap');
  assert.equal(p.nav.clearLine(V(3, 3), V(-5, 3)), false, 'out of the grid');
  // Grazing the inflated corner is not allowed either.
  assert.equal(p.nav.clearLine(V(8, 13), V(12, 15.9)), false);
});

test('randomPoint: walkable, in range, reachable, and deterministic with G.rng', () => {
  const build = () => {
    const p = field(40, 40, { rng: makeRng(7) });
    wall(p, 9.5, 9.5, 30.5, 10);
    wall(p, 9.5, 30, 30.5, 30.5);
    wall(p, 9.5, 9.5, 10, 30.5);
    wall(p, 30, 9.5, 30.5, 30.5);
    return p;
  };
  const p = build();
  const centre = V(20, 20); // inside the sealed yard
  const points = [];
  for (let i = 0; i < 200; i++) {
    const q = p.nav.randomPoint(centre, 18);
    assert.ok(q, 'plenty of room: a point is found');
    assert.ok(q.distanceTo(centre) <= 18 + 1e-9);
    assert.ok(p.nav.isWalkable(q.x, q.z));
    assert.ok(q.x > 10 && q.x < 30 && q.z > 10 && q.z < 30, 'never on the far side of the wall');
    points.push(q);
  }
  assert.ok(new Set(points.map((q) => q.x)).size > 150, 'actually random');

  const again = build();
  for (let i = 0; i < 20; i++) {
    assert.deepEqual(again.nav.randomPoint(centre, 18).toArray(), points[i].toArray());
  }
  assert.equal(p.nav.randomPoint(V(-40, -40), 3), null, 'no free ground anywhere near');
});

test('nearestWalkable: the point itself, else the closest free cell centre within range', () => {
  const p = field();
  wall(p, 8, 8, 12, 12);
  assert.deepEqual(p.nav.nearestWalkable(3.3, 4.4).toArray(), [3.3, 0, 4.4]);
  assert.deepEqual(p.nav.nearestWalkable(8.3, 10.1).toArray(), [7.25, 0, 10.25]);
  assert.deepEqual(p.nav.nearestWalkable(10.1, 11.9).toArray(), [10.25, 0, 12.75]);
  assert.equal(p.nav.nearestWalkable(10, 10, 1), null, 'nothing free within a metre of the middle');
  assert.ok(p.nav.nearestWalkable(10, 10, 3));
  assert.deepEqual(p.nav.nearestWalkable(-1, 5.1).toArray(), [0.75, 0, 5.25], 'from just outside the bounds');
  assert.equal(p.nav.nearestWalkable(-30, 5.1), null, 'from far outside');
});

test('performance: paths across a street-sized grid stay cheap', () => {
  const rng = makeRng(1994);
  const p = createPhysics({});
  p.setBounds({ minX: -46, maxX: 46, minZ: -34, maxZ: 34 });
  // Buildings north and south of an avenue, parked cars in four lanes, columns and clutter.
  p.addBox({ min: [-46, 0, -34], max: [-30, 12, -11] });
  p.addBox({ min: [11, 0, -34], max: [22, 12, -11] });
  p.addBox({ min: [-46, 0, 11], max: [-16, 12, 34] });
  p.addBox({ min: [-4, 0, 11], max: [22, 12, 26] });
  for (const z of [-6, -2.2, 2.2, 6]) {
    for (let x = -28; x < 20; x += 6.5) {
      if (rng.next() < 0.25) continue;
      p.addOriented([x + rng.next() * 1.5, 0.72, z], [4.6, 1.45, 1.85], rng.next() < 0.3 ? rng.next() - 0.5 : 0);
    }
  }
  for (let x = -44; x <= 44; x += 10) for (const z of [-5, 5]) p.addBox({ min: [x - 0.3, 0, z - 0.3], max: [x + 0.3, 6.5, z + 0.3] });
  for (let k = 0; k < 300; k++) {
    const x = -45 + rng.next() * 90;
    const z = -33 + rng.next() * 66;
    p.addBox({ min: [x - 0.4, 0, z - 0.4], max: [x + 0.4, 1.2, z + 0.4] });
  }
  assert.equal(p.nav.cols * p.nav.rows, 184 * 136);

  const points = [];
  while (points.length < 400) {
    const x = -45 + rng.next() * 90;
    const z = -33 + rng.next() * 66;
    if (p.nav.isWalkable(x, z)) points.push(V(x, z));
  }
  const run = () => {
    let found = 0;
    for (let i = 0; i < points.length; i += 2) {
      const path = p.nav.findPath(points[i], points[i + 1]);
      if (path) {
        found++;
        assertSound(p.nav, path);
      }
    }
    return found;
  };
  run(); // warm up the JIT
  const t0 = performance.now();
  const found = run();
  const perPath = (performance.now() - t0) / (points.length / 2);
  assert.ok(found > 150, `${found} of 200 random pairs connect`);
  // Typically 0.2 to 0.4 ms including the checks above; the bound only catches an accidental blow-up.
  assert.ok(perPath < 5, `${perPath.toFixed(3)} ms per path`);
});
