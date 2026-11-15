// Collision: rays, flags, capsule movement, oriented boxes. Run with `node --test test/`.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { createPhysics } from '../src/physics.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const RADIUS = 0.32;
const HEIGHT = 1.8;
const GRAVITY = 21;
const DT = 1 / 60;

function near(actual, expected, eps = 1e-6, label = '') {
  assert.ok(Math.abs(actual - expected) <= eps, `${label} expected ${expected} ± ${eps}, got ${actual}`);
}

function world(G = {}) {
  const physics = createPhysics(G);
  physics.setBounds({ minX: -50, maxX: 50, minZ: -50, maxZ: 50 });
  return physics;
}

const body = (x, y, z) => ({ pos: V(x, y, z), vel: V(0, 0, 0), grounded: true, hitWall: false, hitCeil: false, airFrames: 0 });

/** Minimal walker: constant horizontal velocity, gravity, grounded state fed back as allowStep. */
function walk(physics, b, frames, { vx = 0, vz = 0, height = HEIGHT, each } = {}) {
  let res = null;
  for (let i = 0; i < frames; i++) {
    b.vel.x = vx;
    b.vel.z = vz;
    b.vel.y -= GRAVITY * DT;
    res = physics.moveCapsule(b.pos, b.vel, DT, RADIUS, height, b.grounded);
    b.grounded = res.onGround;
    b.hitWall = b.hitWall || res.hitWall;
    b.hitCeil = b.hitCeil || res.hitCeil;
    if (!res.onGround) b.airFrames++;
    if (each) each(res, i);
  }
  return res;
}

test('raycast: hits the entered face of a box on every axis', () => {
  const p = world();
  const box = p.addBox({ min: [5, 0, -1], max: [7, 2, 1], surface: 'brick', tag: 'wall' });

  let hit = p.raycast(V(0, 1, 0), V(1, 0, 0));
  near(hit.dist, 5);
  assert.deepEqual(hit.point.toArray(), [5, 1, 0]);
  assert.deepEqual(hit.normal.toArray(), [-1, 0, 0]);
  assert.equal(hit.surface, 'brick');
  assert.equal(hit.box, box);

  hit = p.raycast(V(10, 1, 0), V(-1, 0, 0));
  near(hit.dist, 3);
  assert.deepEqual(hit.normal.toArray(), [1, 0, 0]);

  hit = p.raycast(V(6, 5, 0), V(0, -1, 0));
  near(hit.dist, 3);
  assert.deepEqual(hit.normal.toArray(), [0, 1, 0]);

  hit = p.raycast(V(6, 1, -5), V(0, 0, 1));
  near(hit.dist, 4);
  assert.deepEqual(hit.normal.toArray(), [0, 0, -1]);

  hit = p.raycast(V(6, 1, 5), V(0, 0, -1));
  near(hit.dist, 4);
  assert.deepEqual(hit.normal.toArray(), [0, 0, 1]);

  // A diagonal ray reports the face it actually crosses.
  hit = p.raycast(V(3, 1, -1.5), V(1, 0, 0.5).normalize());
  assert.deepEqual(hit.normal.toArray(), [-1, 0, 0]);
  near(hit.point.x, 5);
  near(hit.point.z, -0.5);
});

test('raycast: the ground plane is hit with box = null and the level names its surface', () => {
  let p = world();
  let hit = p.raycast(V(3, 2, 4), V(0, -1, 0));
  near(hit.dist, 2);
  assert.equal(hit.box, null);
  assert.deepEqual(hit.normal.toArray(), [0, 1, 0]);
  assert.equal(hit.surface, 'asphalt');
  assert.equal(p.raycast(V(0, 2, 0), V(0, 1, 0)), null, 'nothing above');
  assert.equal(p.raycast(V(0, 2, 0), V(1, 0, 0)), null, 'a level ray never meets the ground');

  p = world({ level: { groundSurfaceAt: (x) => (x > 0 ? 'concrete' : 'dirt') } });
  hit = p.raycast(V(3, 2, 0), V(0, -1, 0));
  assert.equal(hit.surface, 'concrete');
  hit = p.raycast(V(-3, 2, 0), V(0, -1, 0));
  assert.equal(hit.surface, 'dirt');
});

test('raycast: nearest box wins, maxDist is respected, direction length does not matter', () => {
  const p = world();
  const far = p.addBox({ min: [20, 0, -1], max: [21, 2, 1] });
  const nearBox = p.addBox({ min: [8, 0, -1], max: [9, 2, 1] });
  assert.equal(p.raycast(V(0, 1, 0), V(1, 0, 0)).box, nearBox);
  assert.equal(p.raycast(V(0, 1, 0), V(1, 0, 0), 7.9), null);
  near(p.raycast(V(0, 1, 0), V(250, 0, 0)).dist, 8);
  near(p.raycast(V(0, 1, 0), V(0.001, 0, 0)).dist, 8);
  assert.equal(p.raycast(V(0, 1, 0), V(0, 0, 0)), null, 'zero direction');
  p.removeBox(nearBox);
  assert.equal(p.raycast(V(0, 1, 0), V(1, 0, 0)).box, far);
});

test('raycast: a box containing the origin is ignored; a reused result object is filled in place', () => {
  const p = world();
  p.addBox({ min: [-1, 0, -1], max: [1, 2, 1], tag: 'around the origin' });
  const wall = p.addBox({ min: [4, 0, -1], max: [5, 2, 1] });
  const out = { dist: 0, point: V(0, 0, 0), normal: V(0, 0, 0), surface: null, box: null };
  const hit = p.raycast(V(0, 1, 0), V(1, 0, 0), 500, out);
  assert.equal(hit, out);
  assert.equal(out.box, wall);
  near(out.dist, 4);
  // Touching a face and shooting into it still counts.
  near(p.raycast(V(4, 1, 0), V(1, 0, 0)).dist, 0);
});

test('flags: playerOnly stops bodies but not rays, bulletOnly stops rays but not bodies', () => {
  const p = world();
  const glass = p.addBox({ min: [3, 0, -5], max: [3.2, 3, 5], playerOnly: true });
  const mesh = p.addBox({ min: [-3.2, 0, -5], max: [-3, 3, 5], bulletOnly: true });

  assert.equal(p.raycast(V(0, 1, 0), V(1, 0, 0)), null, 'ray passes the player-only wall');
  assert.equal(p.raycast(V(0, 1, 0), V(-1, 0, 0)).box, mesh, 'ray stops on the bullet-only box');
  assert.equal(p.lineOfSight(V(0, 1, 0), V(6, 1, 0)), true);
  assert.equal(p.lineOfSight(V(0, 1, 0), V(-6, 1, 0)), false);

  const east = body(0, 0, 0);
  walk(p, east, 120, { vx: 4 });
  near(east.pos.x, 3 - RADIUS, 1e-3, 'stopped by the player-only wall');
  assert.equal(east.hitWall, true);

  const west = body(0, 0, 0);
  walk(p, west, 120, { vx: -4 });
  near(west.pos.x, -8, 1e-6, 'walked straight through the bullet-only box');
  assert.equal(west.hitWall, false);

  // Neither kind is ground, and neither blocks the nav grid.
  assert.equal(p.groundHeight(3.1, 0), 0);
  assert.equal(p.groundHeight(-3.1, 0), 0);
  assert.equal(p.nav.isWalkable(3.1, 0), true);
  assert.equal(p.nav.isWalkable(-3.1, 0), true);
  assert.equal(p.overlapsCylinder(3.1, 0, 0.3, 0, 1.8), true);
  assert.equal(p.overlapsCylinder(-3.1, 0, 0.3, 0, 1.8), false);
  assert.ok(glass.playerOnly && mesh.bulletOnly);
});

test('lineOfSight {movement: true}: player-only boxes block it, bullet-only ones do not', () => {
  const p = world();
  // A chain-link fence: see and shoot through, not walk through. A bullet-only mesh: the other way round.
  p.addBox({ min: [3, 0, -5], max: [3.2, 8, 5], playerOnly: true, tag: 'cage-fence' });
  p.addBox({ min: [-3.2, 0, -5], max: [-3, 3, 5], bulletOnly: true });
  p.addBox({ min: [-1, 0, 6], max: [1, 3, 7] });
  const MOVE = { movement: true };
  // Through the fence: clear to the eye, blocked for a body; a point 0.3 m past it is still behind it.
  assert.equal(p.lineOfSight(V(0, 1, 0), V(6, 1, 0)), true, 'sight passes the fence');
  assert.equal(p.lineOfSight(V(0, 1, 0), V(6, 1, 0), MOVE), false, 'a body does not');
  assert.equal(p.lineOfSight(V(2, 1, 0), V(3.5, 1, 0), MOVE), false, 'just past the mesh');
  assert.equal(p.lineOfSight(V(3.5, 1, 0), V(2, 1, 0), MOVE), false, 'and from the other side');
  // The bullet-only box is the other way round.
  assert.equal(p.lineOfSight(V(0, 1, 0), V(-6, 1, 0)), false);
  assert.equal(p.lineOfSight(V(0, 1, 0), V(-6, 1, 0), MOVE), true, 'a body passes the bullet-only box');
  // Ordinary walls block both; open ground blocks neither; an option without `movement` is plain sight.
  assert.equal(p.lineOfSight(V(0, 1, 0), V(0, 1, 10), MOVE), false);
  assert.equal(p.lineOfSight(V(0, 1, 0), V(2.5, 1, 3), MOVE), true);
  assert.equal(p.lineOfSight(V(0, 1, 0), V(6, 1, 0), {}), true);
  // Plain rays still pass the player-only box after a movement query (the mask does not stick).
  assert.equal(p.raycast(V(0, 1, 0), V(1, 0, 0)), null);
});

test('lineOfSight: walls block, low cover does not, a point on a surface is visible', () => {
  const p = world();
  p.addBox({ min: [4, 0, -3], max: [5, 3, 3] });
  p.addBox({ min: [-5, 0, -3], max: [-4, 0.8, 3] });
  assert.equal(p.lineOfSight(V(0, 1.6, 0), V(8, 1.6, 0)), false);
  assert.equal(p.lineOfSight(V(0, 1.6, 0), V(8, 1.6, 10)), true, 'past the end of the wall');
  assert.equal(p.lineOfSight(V(0, 1.6, 0), V(-8, 1.6, 0)), true, 'over the low cover');
  assert.equal(p.lineOfSight(V(0, 0.5, 0), V(-8, 0.5, 0)), false, 'through the low cover');
  assert.equal(p.lineOfSight(V(0, 1.6, 0), V(4, 1.6, 0)), true, 'the wall face itself');
  assert.equal(p.lineOfSight(V(0, 1.6, 0), V(2, 0, 0)), true, 'a point on the ground');
  assert.equal(p.lineOfSight(V(0, 1.6, 0), V(2, -1, 0)), false, 'a point under the ground');
});

test('moveCapsule: slides along a wall instead of stopping', () => {
  const p = world();
  p.addBox({ min: [1, 0, -20], max: [2, 3, 20] });
  const b = body(0, 0, 0);
  const res = walk(p, b, 60, { vx: 3, vz: 2 });
  near(b.pos.x, 1 - RADIUS, 1e-4, 'held one radius from the wall');
  near(b.pos.z, 2, 1e-6, 'kept all of its sideways motion');
  assert.equal(res.hitWall, true);
  assert.equal(b.vel.x, 0, 'the velocity into the wall is removed');
  near(b.vel.z, 2);
  assert.equal(res.onGround, true);
});

test('moveCapsule: fast bodies do not tunnel through thin walls, corners hold', () => {
  const p = world();
  p.addBox({ min: [2, 0, -20], max: [2.08, 3, 20], tag: 'fence' });
  p.addBox({ min: [-20, 0, 2], max: [20, 3, 2.08], tag: 'fence' });
  const b = { pos: V(0, 0, 0), vel: V(60, 0, 60) };
  for (let i = 0; i < 30; i++) {
    b.vel.set(60, 0, 60);
    p.moveCapsule(b.pos, b.vel, 0.05, RADIUS, HEIGHT, true);
  }
  near(b.pos.x, 2 - RADIUS, 1e-3);
  near(b.pos.z, 2 - RADIUS, 1e-3);
});

test('moveCapsule: a body that finds itself inside a box is pushed out through the nearest face', () => {
  const p = world();
  p.addBox({ min: [-1, 0, -1], max: [1, 3, 1] });
  const b = { pos: V(0.7, 0, 0.1), vel: V(0, 0, 0) };
  p.moveCapsule(b.pos, b.vel, DT, RADIUS, HEIGHT, true);
  near(b.pos.x, 1 + RADIUS, 1e-6);
  near(b.pos.z, 0.1, 1e-6);
});

test('moveCapsule: steps up 0.4 m, is blocked by 0.5 m', () => {
  let p = world();
  p.addBox({ min: [1, 0, -5], max: [6, 0.4, 5], surface: 'concrete' });
  let b = body(0, 0, 0);
  let res = walk(p, b, 60, { vx: 2 });
  near(b.pos.x, 2, 1e-6, 'walked on');
  near(b.pos.y, 0.4, 1e-9, 'on top of the step');
  assert.equal(res.onGround, true);
  assert.equal(res.surface, 'concrete');
  assert.equal(b.airFrames, 0, 'never left the ground');

  p = world();
  p.addBox({ min: [1, 0, -5], max: [6, 0.5, 5] });
  b = body(0, 0, 0);
  res = walk(p, b, 60, { vx: 2 });
  near(b.pos.x, 1 - RADIUS, 1e-4, 'stopped at the ledge');
  assert.equal(b.pos.y, 0);
  assert.equal(b.hitWall, true);

  // Exactly at the limit still works, and an airborne body gets no step-up.
  p = world();
  p.addBox({ min: [1, 0, -5], max: [6, 0.42, 5] });
  b = body(0, 0, 0);
  walk(p, b, 60, { vx: 2 });
  near(b.pos.y, 0.42, 1e-9);
  const air = { pos: V(0.5, 0.05, 0), vel: V(4, 0, 0) };
  for (let i = 0; i < 10; i++) {
    air.vel.set(4, 0, 0);
    p.moveCapsule(air.pos, air.vel, DT, RADIUS, HEIGHT, false);
  }
  near(air.pos.x, 1 - RADIUS, 1e-4, 'no step-up in the air');
});

test('moveCapsule: climbs and descends a flight of stairs without leaving the ground', () => {
  const p = world();
  // Ten 0.28 m risers, 0.4 m treads, then a deck at 2.8 m.
  for (let i = 0; i < 10; i++) p.addBox({ min: [1 + i * 0.4, 0, -1], max: [1.4 + i * 0.4, 0.28 * (i + 1), 1] });
  p.addBox({ min: [5, 2.7, -1], max: [9, 2.8, 1], surface: 'wood' });
  const b = body(0, 0, 0);
  let res = walk(p, b, 150, { vx: 3 });
  near(b.pos.y, 2.8, 1e-9, 'on the deck');
  assert.equal(res.surface, 'wood');
  assert.equal(b.airFrames, 0, 'going up');
  res = walk(p, b, 150, { vx: -3 });
  assert.equal(b.pos.y, 0, 'back on the street');
  assert.equal(b.airFrames, 0, 'going down: snapped from tread to tread');
});

test('moveCapsule: falls, lands on a box top and reports its surface', () => {
  const p = world();
  p.addBox({ min: [-1, 0, -1], max: [1, 1, 1], surface: 'metal' });
  const b = body(0, 3, 0);
  b.grounded = false;
  let landedAt = -1;
  const res = walk(p, b, 120, {
    each: (r, i) => {
      if (r.onGround && landedAt < 0) landedAt = i;
    },
  });
  assert.equal(b.pos.y, 1);
  assert.equal(b.vel.y, 0);
  assert.equal(res.onGround, true);
  assert.equal(res.surface, 'metal');
  // 2 m at 21 m/s² takes 0.44 s.
  assert.ok(landedAt >= 24 && landedAt <= 28, `landed on frame ${landedAt}`);

  // Terminal velocity with a long frame does not pass through a thin platform.
  const q = world();
  q.addBox({ min: [-1, 0.9, -1], max: [1, 1, 1] });
  const fast = { pos: V(0, 1.5, 0), vel: V(0, -40, 0) };
  const hit = q.moveCapsule(fast.pos, fast.vel, 0.05, RADIUS, HEIGHT, false);
  assert.equal(fast.pos.y, 1);
  assert.equal(hit.onGround, true);
});

test('moveCapsule: ground snap follows a small drop, a tall ledge means falling', () => {
  // 0.3 m kerb: stays grounded all the way down.
  let p = world();
  p.addBox({ min: [-5, 0, -5], max: [1, 0.3, 5] });
  let b = body(0, 0.3, 0);
  walk(p, b, 60, { vx: 3 });
  assert.equal(b.pos.y, 0);
  assert.equal(b.airFrames, 0);

  // The same kerb without the grounded hint is a short fall.
  b = { pos: V(0.95, 0.3, 0), vel: V(3, 0, 0) };
  let res = null;
  for (let i = 0; i < 8; i++) {
    b.vel.x = 3;
    b.vel.y -= GRAVITY * DT;
    res = p.moveCapsule(b.pos, b.vel, DT, RADIUS, HEIGHT, false);
  }
  assert.equal(res.onGround, false, 'no snap without allowStep');
  assert.ok(b.pos.y > 0 && b.pos.y < 0.3);

  // 1 m crate: airborne for the time a 1 m drop takes.
  p = world();
  p.addBox({ min: [-5, 0, -5], max: [1, 1, 5] });
  b = body(0, 1, 0);
  walk(p, b, 90, { vx: 3 });
  assert.equal(b.pos.y, 0);
  assert.ok(b.airFrames >= 15 && b.airFrames <= 22, `airborne for ${b.airFrames} frames`);
});

test('moveCapsule: a ceiling stops a jump, low beams block standing bodies only', () => {
  const p = world();
  p.addBox({ min: [-2, 2.2, -2], max: [2, 2.6, 2], tag: 'ceiling' });
  const b = body(0, 0, 0);
  b.vel.y = 6.5;
  b.grounded = false;
  let top = 0;
  let stopped = false;
  walk(p, b, 60, {
    each: (r) => {
      top = Math.max(top, b.pos.y);
      if (r.hitCeil) {
        stopped = true;
        assert.equal(b.vel.y, 0, 'upward speed is cancelled');
      }
    },
  });
  assert.equal(stopped, true);
  near(top, 2.2 - HEIGHT, 1e-9, 'head stopped at the ceiling');
  assert.equal(b.pos.y, 0, 'and came back down');

  // Standing beside the slab with only the rim of the body under it: the jump is stopped all the same,
  // so the body never ends up inside the slab's edge.
  const beside = body(2.25, 0, 0);
  beside.vel.y = 6.5;
  beside.grounded = false;
  let rimTop = 0;
  walk(p, beside, 60, {
    each: () => {
      rimTop = Math.max(rimTop, beside.pos.y);
    },
  });
  near(rimTop, 2.2 - HEIGHT, 1e-9, 'rim of the body under the slab');
  assert.equal(beside.hitCeil, true);
  near(beside.pos.x, 2.25, 1e-9, 'not shoved sideways');
  // Clear of it, the same jump reaches its full height.
  const clear = body(2.4, 0, 0);
  clear.vel.y = 6.5;
  clear.grounded = false;
  let clearTop = 0;
  walk(p, clear, 60, {
    each: () => {
      clearTop = Math.max(clearTop, clear.pos.y);
    },
  });
  assert.ok(clearTop > 0.9, `full jump: ${clearTop.toFixed(2)} m`);
  assert.equal(clear.hitCeil, false);

  // A beam with its underside at 1.5 m: a wall for a standing body, clear for a crouched one.
  const q = world();
  q.addBox({ min: [1, 1.5, -5], max: [1.4, 3, 5] });
  const standing = body(0, 0, 0);
  walk(q, standing, 60, { vx: 3 });
  near(standing.pos.x, 1 - RADIUS, 1e-4);
  const crouched = body(0, 0, 0);
  walk(q, crouched, 60, { vx: 3, height: 1.15 });
  near(crouched.pos.x, 3, 1e-6);
  assert.equal(crouched.hitWall, false);
  assert.equal(q.overlapsCylinder(1.2, 0, RADIUS, 1.1, 1.8), true, 'no room to stand up under the beam');
  assert.equal(q.overlapsCylinder(3, 0, RADIUS, 1.1, 1.8), false);
});

test('moveCapsule: a step with no headroom above it is not climbed', () => {
  const p = world();
  p.addBox({ min: [1, 0, -5], max: [6, 0.3, 5], tag: 'kerb' });
  p.addBox({ min: [0, 2.0, -5], max: [6, 3, 5], tag: 'overhang 0.2 m above a standing head' });
  const standing = body(0, 0, 0);
  const res = walk(p, standing, 90, { vx: 2 });
  assert.equal(standing.pos.y, 0, 'stayed down');
  assert.ok(standing.pos.x < 1 - 0.7 * RADIUS + 1e-9 && standing.pos.x > 0.6, `stopped at the kerb: x = ${standing.pos.x.toFixed(3)}`);
  assert.equal(res.hitWall, true);
  assert.equal(res.onGround, true);

  // Crouched there is room: 0.3 + 1.15 fits under 2.0.
  const crouched = body(0, 0, 0);
  walk(p, crouched, 90, { vx: 2, height: 1.15 });
  near(crouched.pos.y, 0.3, 1e-9);
  near(crouched.pos.x, 3, 1e-6);
});

test('moveCapsule: the play bounds are walls; the result object can be reused', () => {
  const p = createPhysics({});
  p.setBounds({ minX: -10, maxX: 10, minZ: -6, maxZ: 6 });
  const b = { pos: V(0, 0, 0), vel: V(0, 0, 0) };
  const out = {};
  let res = null;
  for (let i = 0; i < 200; i++) {
    b.vel.set(9, 0, -9);
    res = p.moveCapsule(b.pos, b.vel, DT, RADIUS, HEIGHT, true, out);
  }
  assert.equal(res, out);
  near(b.pos.x, 10 - RADIUS, 1e-9);
  near(b.pos.z, -6 + RADIUS, 1e-9);
  assert.equal(out.hitWall, true);
  assert.equal(out.onGround, true);
  assert.equal(out.surface, 'asphalt');
  assert.deepEqual(p.bounds, { minX: -10, maxX: 10, minZ: -6, maxZ: 6 });
});

test('groundHeight: highest top under the point, limited by maxY', () => {
  const p = world();
  p.addBox({ min: [0, 0, 0], max: [2, 1, 2] });
  p.addBox({ min: [0, 2.7, 0], max: [2, 2.8, 2] });
  assert.equal(p.groundHeight(1, 1), 2.8);
  assert.equal(p.groundHeight(1, 1, 2), 1);
  assert.equal(p.groundHeight(1, 1, 0.5), 0);
  assert.equal(p.groundHeight(5, 5), 0);
});

test('addBox: accepts arrays or vectors, orders min / max, copies its input', () => {
  const p = world();
  const min = V(2, 3, 1);
  const box = p.addBox({ min, max: [0, 0, 4], owner: 'me' });
  assert.deepEqual(box.min.toArray(), [0, 0, 1]);
  assert.deepEqual(box.max.toArray(), [2, 3, 4]);
  assert.equal(box.surface, 'concrete');
  assert.equal(box.owner, 'me');
  assert.equal(box.noNav, false);
  min.set(9, 9, 9);
  assert.deepEqual(box.max.toArray(), [2, 3, 4]);
  assert.equal(p.boxes.length, 1);
  assert.equal(p.boxes[0], box);
});

test('addOriented: axis-aligned yaws give one exact box', () => {
  const p = world();
  let [box, ...rest] = p.addOriented([10, 1, 5], [4, 2, 1], 0, { surface: 'car', tag: 't' });
  assert.equal(rest.length, 0);
  assert.deepEqual(box.min.toArray(), [8, 0, 4.5]);
  assert.deepEqual(box.max.toArray(), [12, 2, 5.5]);
  assert.equal(box.surface, 'car');
  assert.equal(box.tag, 't');

  [box, ...rest] = p.addOriented(V(10, 1, 5), V(4, 2, 1), Math.PI / 2);
  assert.equal(rest.length, 0);
  near(box.min.x, 9.5);
  near(box.max.x, 10.5);
  near(box.min.z, 3);
  near(box.max.z, 7);

  // A degree or two of jitter still snaps to the axis.
  [box, ...rest] = p.addOriented([0, 1, 0], [4, 2, 1], Math.PI + 0.03);
  assert.equal(rest.length, 0);
  near(box.max.x - box.min.x, 4);
  near(box.max.z - box.min.z, 1);
});

test('addOriented: off-axis boxes are sliced into overlapping pieces that follow the shape', () => {
  const p = world();
  const yaw = Math.PI / 4;
  const owner = {};
  const pieces = p.addOriented([0, 1, 0], [8, 2, 1], yaw, { surface: 'car', owner });
  assert.equal(pieces.length, 8);
  assert.equal(p.boxes.length, 8);
  for (const b of pieces) {
    assert.equal(b.surface, 'car');
    assert.equal(b.owner, owner);
    assert.equal(b.min.y, 0);
    assert.equal(b.max.y, 2);
  }

  // Local +X points along (cos yaw, −sin yaw): the whole centre line is covered, without holes.
  const ax = Math.cos(yaw);
  const az = -Math.sin(yaw);
  for (let t = -3.9; t <= 3.9; t += 0.05) {
    assert.equal(p.groundHeight(ax * t, az * t), 2, `gap on the centre line at t = ${t.toFixed(2)}`);
  }
  // Beyond the ends and well off to the side there is nothing.
  assert.equal(p.groundHeight(ax * 4.6, az * 4.6), 0);
  assert.equal(p.groundHeight(-az * 1.3, ax * 1.3), 0);

  // A ray across the middle meets the surface near where the real face is (0.5 m from the axis).
  const from = V(-az * 5, 1, ax * 5);
  const hit = p.raycast(from, V(az, 0, -ax));
  near(hit.dist, 4.5, 0.3, 'side face');
  // Rays aimed at the seams between pieces never slip through.
  for (let t = -3.5; t <= 3.5; t += 0.25) {
    const o = V(ax * t - az * 5, 1, az * t + ax * 5);
    assert.ok(p.raycast(o, V(az, 0, -ax), 10), `slit at t = ${t}`);
  }

  // The union stays close to the true footprint: a body cannot stand more than a few centimetres inside.
  const b = { pos: V(-az * 3, 0, ax * 3), vel: V(0, 0, 0) };
  for (let i = 0; i < 120; i++) {
    b.vel.set(az * 3, 0, -ax * 3);
    p.moveCapsule(b.pos, b.vel, DT, RADIUS, HEIGHT, true);
  }
  const distance = Math.abs(b.pos.x * -az + b.pos.z * ax); // from the long axis
  assert.ok(distance > 0.5 + RADIUS - 0.25 && distance < 0.5 + RADIUS + 0.45, `stopped ${distance.toFixed(2)} m from the axis`);
});

test('addOriented: never more than ten pieces, and the long side may be Z', () => {
  const p = world();
  assert.equal(p.addOriented([0, 1, 0], [30, 2, 0.2], 0.6).length, 10);
  const pieces = p.addOriented([20, 1, 20], [1, 2, 6], 0.5);
  assert.equal(pieces.length, 6);
  // Local +Z points along (sin yaw, cos yaw).
  for (let t = -2.9; t <= 2.9; t += 0.1) {
    assert.equal(p.groundHeight(20 + Math.sin(0.5) * t, 20 + Math.cos(0.5) * t), 2);
  }
  // A square footprint is a single shrunk box.
  assert.equal(p.addOriented([-20, 1, -20], [2, 2, 2], 0.7).length, 1);
});

test('removeBox / removeBoxes: gone for rays, bodies and the nav grid', () => {
  const p = world();
  const keep = p.addBox({ min: [8, 0, -1], max: [9, 2, 1] });
  const pieces = p.addOriented([3, 1, 0], [1, 2, 6], 0.5);
  assert.equal(p.nav.isWalkable(3, 0), false);
  assert.notEqual(p.raycast(V(0, 1, 0), V(1, 0, 0)).box, keep);
  p.removeBoxes(pieces);
  assert.equal(p.boxes.length, 1);
  assert.equal(p.raycast(V(0, 1, 0), V(1, 0, 0)).box, keep);
  assert.equal(p.nav.isWalkable(3, 0), true);
  p.removeBox(keep);
  p.removeBox(keep); // harmless twice
  assert.equal(p.boxes.length, 0);
  assert.equal(p.raycast(V(0, 1, 0), V(1, 0, 0)), null);
  const b = body(0, 0, 0);
  walk(p, b, 60, { vx: 6 });
  near(b.pos.x, 6, 1e-6);
});
