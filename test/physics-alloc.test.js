// The physics queries that run many times a frame must not leave garbage behind once the code is warm.
// (V8 boxes a double on the heap when it crosses a call as an argument or result, or lands in a closure
// variable: physics.js keeps such numbers in typed arrays. This test is what holds that in place.)

import test from 'node:test';
import assert from 'node:assert/strict';
import v8 from 'node:v8';
import vm from 'node:vm';
import * as THREE from 'three';
import { createPhysics } from '../src/physics.js';

// gc() without having to start node with --expose-gc.
v8.setFlagsFromString('--expose-gc');
const gc = vm.runInNewContext('gc');

/** A block's worth of colliders: 150 boxes scattered over the play bounds, plus the El deck overhead. */
function makeWorld() {
  const physics = createPhysics({});
  physics.setBounds({ minX: -46, maxX: 46, minZ: -34, maxZ: 34 });
  let seed = 12345;
  const random = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
  for (let i = 0; i < 150; i++) {
    const x = -44 + random() * 88;
    const z = -32 + random() * 64;
    physics.addBox({ min: [x, 0, z], max: [x + 0.4 + random() * 4, 0.5 + random() * 5, z + 0.4 + random() * 3], surface: 'metal' });
  }
  physics.addBox({ min: [-46, 6.4, -5.2], max: [46, 7, 5.2], noNav: true });
  return physics;
}

/** Heap growth over `n` calls, measured from a fresh collection. */
function grown(fn, n) {
  gc();
  const before = process.memoryUsage().heapUsed;
  for (let i = 0; i < n; i++) fn();
  return process.memoryUsage().heapUsed - before;
}

/**
 * Passes when `fn` allocates next to nothing per call: every batch must stay under a fixed allowance
 * for the measurement itself plus `perCall` bytes a call. Small batches catch heavy allocation before a
 * collection can hide it, large ones catch a single boxed number per call. A batch that fails is tried
 * again after more warm-up, because the optimising compiler works in the background.
 */
function assertQuiet(name, fn, { warm = 100000, perCall = 8 } = {}) {
  for (let i = 0; i < warm; i++) fn();
  for (const n of [50, 400, 3200]) {
    let bytes = grown(fn, n);
    for (let attempt = 0; attempt < 4 && bytes > 4096 + n * perCall; attempt++) {
      for (let i = 0; i < warm; i++) fn();
      bytes = grown(fn, n);
    }
    assert.ok(bytes <= 4096 + n * perCall, `${name}: ${Math.round(bytes / n)} B per call over ${n} calls`);
  }
}

test('allocation: rays, line of sight and movement leave no garbage once warm', () => {
  const physics = makeWorld();
  const a = new THREE.Vector3(-30, 1.6, 3);
  const b = new THREE.Vector3(25, 1.2, -9);
  const dir = new THREE.Vector3(0.9, -0.02, 0.2).normalize();
  const hit = { dist: 0, point: new THREE.Vector3(), normal: new THREE.Vector3(), surface: null, box: null };
  assert.ok(physics.raycast(a, dir, 300, hit), 'the test ray hits something');

  assertQuiet('lineOfSight', () => physics.lineOfSight(a, b));
  const MOVE = { movement: true };
  assertQuiet('lineOfSight for movement', () => physics.lineOfSight(a, b, MOVE));
  assertQuiet('raycast into a reused result', () => physics.raycast(a, dir, 300, hit));
  assertQuiet('groundHeight', () => physics.groundHeight(3.3, 1.2));
  assertQuiet('overlapsCylinder', () => physics.overlapsCylinder(3.3, 1.2, 0.3, 1.1, 1.8));
  assertQuiet('nav.isWalkable', () => physics.nav.isWalkable(3.3, 1.2));

  // A body walking under the El deck: floor, ceiling and wall tests every call.
  const pos = new THREE.Vector3();
  const vel = new THREE.Vector3();
  const moved = { onGround: false, hitWall: false, hitCeil: false, surface: '' };
  assertQuiet('moveCapsule into a reused result', () => {
    pos.set(-20, 0, 0);
    vel.set(2.1, 0, 1.3);
    physics.moveCapsule(pos, vel, 1 / 60, 0.32, 1.8, true, moved);
  });
});

test('allocation: a path into a reused array costs no more than a few numbers', () => {
  // A small yard with a wall to walk around, so the search and the string pulling both have work to do.
  const physics = createPhysics({});
  physics.setBounds({ minX: 0, maxX: 30, minZ: 0, maxZ: 30 });
  physics.addBox({ min: [14, 0, 0], max: [15, 3, 22] });
  physics.addBox({ min: [20, 0, 10], max: [21, 3, 30] });
  const from = new THREE.Vector3(3, 0, 4);
  const to = new THREE.Vector3(27, 0, 5);
  const path = [];
  assert.ok(physics.nav.findPath(from, to, path) && path.length >= 4, 'the route bends around both walls');
  // The two end points are snapped to cells through ordinary calls (four numbers per path); nothing may
  // scale with the length of the path or the size of the search.
  assertQuiet('nav.findPath into a reused array', () => physics.nav.findPath(from, to, path), { warm: 6000, perCall: 96 });
});
