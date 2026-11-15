// The real player module (src/player.js) on the real physics, driven by a scripted input: the same
// loop order as main.js, no browser needed. Covers the pure parts (speed rule, acceleration model,
// recoil, shake, landing spring) and the controller as a whole (jump apex, coyote time, jump buffer,
// crouch headroom, step-up, fall damage, regeneration, death, the camera layers).

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import * as TUNING from '../src/config/player.js';
import { MODULES, missingFrom } from '../src/core/contract.js';
import { createEvents } from '../src/core/events.js';
import { createPhysics } from '../src/physics.js';
import {
  approachVelocity, createPlayer, createRecoil, createShake, createSpring, jumpSpeed, sprintWanted, targetSpeed,
} from '../src/player.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const DT = 1 / 60;
const EAST = -Math.PI / 2; // yaw that looks toward +X

function near(actual, expected, eps, label = '') {
  assert.ok(Math.abs(actual - expected) <= eps, `${label} expected ${expected} ± ${eps}, got ${actual}`);
}

/** Scripted stand-in for G.input with the members the player reads. */
function makeInput() {
  const held = new Set();
  const edges = new Set();
  return {
    move: { x: 0, y: 0 },
    look: { dx: 0, dy: 0 },
    down: (a) => held.has(a),
    pressed: (a) => edges.has(a),
    released: () => false,
    hold(a) {
      held.add(a);
      edges.add(a);
    },
    /** A press edge with no hold: one frame of `pressed`. */
    tap: (a) => edges.add(a),
    release: (a) => held.delete(a),
    endFrame() {
      edges.clear();
      this.look.dx = this.look.dy = 0;
    },
  };
}

function setup({ build, params = {}, dt = DT, weapon = false } = {}) {
  const events = createEvents();
  const count = {};
  const last = {};
  const log = [];
  const G = {
    THREE,
    params,
    events,
    time: { t: 0, dt, frame: 0 },
    input: makeInput(),
    camera: new THREE.PerspectiveCamera(74, 16 / 9, 0.08, 700),
    render: { post: { damage: 0, lowHealth: 0, ads: 0 } },
    level: { playerStart: { pos: V(0, 0, 0), yaw: EAST } },
    count,
    last,
    log,
  };
  G.camera.rotation.order = 'YXZ';
  if (weapon) G.weapon = { update() {} }; // something else owns player.ads
  for (const name of ['player:step', 'player:jump', 'player:land', 'player:hit', 'player:dead']) {
    events.on(name, (e) => {
      count[name] = (count[name] || 0) + 1;
      last[name] = e;
      log.push(name);
    });
  }
  G.physics = createPhysics(G);
  G.physics.setBounds({ minX: -46, maxX: 46, minZ: -34, maxZ: 34 });
  if (build) build(G.physics);
  G.player = createPlayer(G);
  G.frames = (n, each) => {
    for (let i = 0; i < n; i++) {
      G.time.t += dt;
      G.time.frame++;
      G.player.update(dt);
      G.input.endFrame();
      if (each) each(i);
    }
  };
  G.seconds = (s, each) => G.frames(Math.round(s / dt), each);
  return G;
}

// ------------------------------------------------------------------------------------ pure parts

test('player: jump speed gives a one metre apex', () => {
  const v = jumpSpeed(TUNING.jump.gravity, TUNING.jump.apex);
  near(v, 6.4807, 1e-3);
  near((v * v) / (2 * TUNING.jump.gravity), 1.0, 1e-12, 'apex');
  near((2 * v) / TUNING.jump.gravity, 0.617, 1e-3, 'air time on flat ground');
});

test('player: target speed — walk, crouch, sprint, aim cap, backpedal', () => {
  const s = TUNING.speed;
  assert.equal(targetSpeed(s, false, false, 0, 1), 3.8);
  assert.equal(targetSpeed(s, true, false, 0, 1), 1.9);
  assert.equal(targetSpeed(s, false, true, 0, 1), 6.4);
  assert.equal(targetSpeed(s, true, true, 0, 1), 1.9, 'crouch wins over sprint');
  near(targetSpeed(s, false, false, 1, 1), 2.4, 1e-12, 'aiming caps at 2.4');
  near(targetSpeed(s, false, false, 0.5, 1), 3.1, 1e-12, 'half-way into the aim');
  near(targetSpeed(s, true, false, 1, 1), 1.9, 1e-12, 'crouch + aim stays 1.9');
  near(targetSpeed(s, false, false, 0, -1), 3.8 * 0.82, 1e-12, 'full backpedal');
  near(targetSpeed(s, false, false, 0, -0.5), 3.8 * 0.91, 1e-12, 'half backpedal');
  assert.equal(targetSpeed(s, false, false, 0, 0), 3.8, 'no strafe penalty');
});

test('player: the sprint rule needs every condition', () => {
  const r = TUNING.sprint;
  assert.equal(sprintWanted(r, true, 1, 0, false, 0, false), true);
  assert.equal(sprintWanted(r, false, 1, 0, false, 0, false), false, 'not held');
  assert.equal(sprintWanted(r, true, 0.55, 0, false, 0, false), false, 'forward must exceed 0.55');
  assert.equal(sprintWanted(r, true, 0.8, 0.59, false, 0, false), true, 'a little strafe is fine');
  assert.equal(sprintWanted(r, true, 0.8, -0.6, false, 0, false), false, 'too much strafe');
  assert.equal(sprintWanted(r, true, 1, 0, true, 0, false), false, 'crouching');
  assert.equal(sprintWanted(r, true, 1, 0, false, 0.35, false), false, 'aiming');
  assert.equal(sprintWanted(r, true, 1, 0, false, 0.34, false), true);
  assert.equal(sprintWanted(r, true, 1, 0, false, 0, true), false, 'firing');
});

test('player: acceleration is a constant-rate move toward the wish velocity', () => {
  const a = TUNING.accel;
  const v = { x: 0, z: 0 };
  // 0 → walk on the ground takes 3.8 / 34 s, in a straight line.
  let t = 0;
  while (v.x < 3.8 && t < 1) {
    approachVelocity(v, 3.8, 0, a.ground, 1 / 240, true);
    t += 1 / 240;
  }
  near(t, 3.8 / 34, 1 / 240 + 1e-9, 'time to walk speed');
  assert.equal(v.x, 3.8, 'snaps onto the target');
  assert.equal(v.z, 0);

  // Walk → stop without input: 3.8 / 26 s.
  t = 0;
  while (v.x > 0 && t < 1) {
    approachVelocity(v, 0, 0, a.groundStop, 1 / 240, true);
    t += 1 / 240;
  }
  near(t, 3.8 / 26, 1 / 240 + 1e-9, 'time to stop');
  assert.equal(v.x, 0);

  // One step covers exactly rate · dt, whatever the direction.
  v.x = 0;
  v.z = 0;
  approachVelocity(v, 3, 4, a.air, 0.05, true);
  near(Math.hypot(v.x, v.z), 9 * 0.05, 1e-12);
  near(v.x / v.z, 3 / 4, 1e-12, 'straight toward the target');

  // The path does not depend on the frame rate.
  const slow = { x: 6.4, z: 0 };
  const fast = { x: 6.4, z: 0 };
  for (let i = 0; i < 4; i++) approachVelocity(slow, 0, 3.8, a.ground, 1 / 20, true);
  for (let i = 0; i < 48; i++) approachVelocity(fast, 0, 3.8, a.ground, 1 / 240, true);
  near(slow.x, fast.x, 1e-9);
  near(slow.z, fast.z, 1e-9);

  // In the air without input the velocity is not snapped to rest: momentum is kept.
  const drift = { x: 0.004, z: 0 };
  approachVelocity(drift, 0, 0, a.airStop, 0.05, false);
  assert.equal(drift.x, 0.004);
});

test('player: recoil — 65 % springs back after a 0.09 s hold, clamped, frame-rate independent', () => {
  const tune = TUNING.recoil;
  const run = (dt, seconds, kicks = [[0, 0.01, 0.004]]) => {
    const r = createRecoil(tune);
    const samples = [];
    let t = 0;
    let next = 0;
    for (let i = 0; i < Math.round(seconds / dt); i++) {
      while (next < kicks.length && kicks[next][0] <= t + 1e-9) {
        r.kick(kicks[next][1], kicks[next][2]);
        next++;
      }
      r.update(dt);
      t += dt;
      samples.push([t, r.pitch, r.yaw, r.targetPitch]);
    }
    return { r, samples, at: (time) => samples[Math.round(time / dt) - 1] };
  };

  const a = run(1 / 240, 1.5);
  // The recoverable share is 65 % of the kick and the view reaches it fast (rate 34).
  near(a.at(0.085)[3], 0.0065, 1e-12, 'target holds for 0.09 s');
  assert.ok(a.at(0.085)[1] > 0.0065 * 0.9, `view has snapped on: ${a.at(0.085)[1]}`);
  near(a.at(0.085)[2] / a.at(0.085)[1], 0.4, 1e-9, 'yaw follows the same curve');
  // Then the target lets go at rate 6.5.
  near(a.at(0.59)[3], 0.0065 * Math.exp(-6.5 * 0.5), 2e-5, 'target after 0.5 s of recovery');
  assert.ok(Math.abs(a.r.pitch) < 2e-5, 'recentred after 1.5 s');

  // Same curve at 30 fps.
  const b = run(1 / 30, 1.5);
  near(b.at(0.6)[3], a.at(0.6)[3], 1e-9, 'target does not depend on the frame rate');
  near(b.at(0.6)[1], a.at(0.6)[1], 2e-4, 'view offset at 30 fps vs 240 fps');

  // Sustained fire at 12 rounds a second never lets go (each round restarts the hold) and is clamped.
  const burst = [];
  for (let i = 0; i < 120; i++) burst.push([i / 12, 0.02, 0.02]);
  const c = run(1 / 120, 10, burst);
  near(c.r.targetPitch, tune.maxPitch, 1e-12, 'pitch clamp');
  near(c.r.targetYaw, tune.maxYaw, 1e-12, 'yaw clamp');
  near(c.r.pitch, tune.maxPitch, 1e-3);
});

test('player: shake is trauma squared, decays linearly and is capped', () => {
  const tune = TUNING.shake;
  const s = createShake(tune);
  s.add(0.6);
  s.add(0.7);
  assert.equal(s.trauma, 1, 'capped at 1');
  let peak = 0;
  for (let i = 0; i < 60; i++) {
    s.update(1 / 240);
    peak = Math.max(peak, Math.abs(s.roll));
  }
  near(s.trauma, 1 - tune.decay * 0.25, 1e-9, 'linear decay');
  assert.ok(peak > tune.roll * 0.5 && peak <= tune.roll * 2, `roll peak ${peak}`);
  // Half the trauma: a quarter of the motion bound.
  const q = createShake(tune);
  q.add(0.5);
  q.update(1e-6);
  assert.ok(Math.abs(q.pitch) <= tune.pitch * 2 * 0.25 + 1e-9);
  for (let i = 0; i < 100; i++) s.update(0.05);
  assert.equal(s.trauma, 0);
  assert.deepEqual([s.pitch, s.yaw, s.roll], [0, 0, 0]);
  s.add(-1);
  assert.equal(s.trauma, 0, 'negative trauma is ignored');
});

test('player: the landing spring dips, stays inside its limits and settles the same at any frame rate', () => {
  const tune = TUNING.bob.spring;
  const run = (dt, impulse, seconds = 1.2) => {
    const s = createSpring(tune);
    s.kick(impulse);
    let low = 0;
    let high = 0;
    for (let i = 0; i < Math.round(seconds / dt); i++) {
      s.update(dt);
      low = Math.min(low, s.offset);
      high = Math.max(high, s.offset);
    }
    return { s, low, high };
  };
  const jumpLanding = -Math.min(6.48 * TUNING.fall.dipPerSpeed, TUNING.fall.dipMax);
  const fine = run(1 / 240, jumpLanding);
  assert.ok(fine.low < -0.06 && fine.low > -0.12, `a jump landing dips about 9 cm: ${fine.low}`);
  assert.ok(Math.abs(fine.s.offset) < 1e-3 && Math.abs(fine.s.velocity) < 1e-2, 'settled');
  const coarse = run(1 / 20, jumpLanding);
  near(coarse.low, fine.low, 0.012, 'depth of the dip at 20 fps');
  const hard = run(1 / 240, -40);
  assert.equal(hard.low, tune.min, 'never below the stop');
  assert.ok(hard.high <= tune.max, 'never above the stop');
});

// ---------------------------------------------------------------------------------- the controller

test('player: exposes the whole contract and starts at the level start', () => {
  const G = setup();
  const p = G.player;
  assert.deepEqual(missingFrom(p, MODULES.player), []);
  assert.deepEqual(p.pos.toArray(), [0, 0, 0]);
  near(p.forward.x, 1, 1e-9, 'facing east');
  assert.deepEqual(G.camera.position.toArray(), [0, 1.68, 0]);
  assert.equal(G.camera.rotation.order, 'YXZ');
  assert.equal(p.health, 100);
  assert.deepEqual(p.regen, { delay: 5.5, rate: 16 });
});

test('player: walks, stops at a wall, sprints with a wider view, stops', () => {
  const G = setup({ weapon: true, build: (p) => p.addBox({ min: [10, 0, -5], max: [10.3, 3, 5], surface: 'brick' }) });
  const p = G.player;
  G.input.move.y = 1;
  let t = 0;
  G.frames(60, (i) => {
    if (!t && p.speed >= 3.8) t = (i + 1) * DT;
  });
  near(t, 3.8 / 34, DT + 1e-9, 'reaches walk speed in 0.11 s');
  near(p.speed, 3.8, 1e-9, 'walk speed');
  G.frames(180);
  near(p.pos.x, 10 - 0.32, 1e-3, 'held one radius from the wall');
  near(p.speed, 0, 1e-9, 'pressed against the wall');
  assert.ok(G.count['player:step'] >= 5, 'footsteps on the way');
  assert.equal(G.last['player:step'].surface, 'asphalt');
  assert.equal(G.last['player:step'].sprint, false);
  assert.ok(G.last['player:step'].pos.isVector3);

  p.yaw = Math.PI / 2; // turn round
  G.input.hold('sprint');
  G.frames(60);
  assert.equal(p.sprinting, true);
  near(p.speed, 6.4, 1e-9, 'sprint speed');
  near(G.camera.fov, 80, 0.5, 'sprint widens the view by 6°');
  // Firing drops the sprint at once.
  G.input.hold('fire');
  G.frames(1);
  assert.equal(p.sprinting, false);
  G.input.release('fire');
  G.frames(30);
  assert.equal(p.sprinting, true);
  // Backing up is slower.
  G.input.release('sprint');
  G.input.move.y = -1;
  G.frames(60);
  near(p.speed, 3.8 * 0.82, 1e-9, 'backpedal');
  G.input.move.y = 0;
  let stop = 0;
  G.frames(30, (i) => {
    if (!stop && p.speed === 0) stop = (i + 1) * DT;
  });
  near(stop, (3.8 * 0.82) / 26, DT + 1e-9, 'time to stop');
  near(G.camera.fov, 74, 1.5, 'the view comes back');
});

test('player: analog input scales the speed; diagonal input is not faster', () => {
  const G = setup();
  const p = G.player;
  G.input.move.y = 0.5;
  G.frames(60);
  near(p.speed, 1.9, 1e-9, 'half deflection, half speed');
  G.input.move.x = Math.SQRT1_2;
  G.input.move.y = Math.SQRT1_2;
  G.frames(60);
  near(p.speed, 3.8, 1e-9);
  // An over-long vector from a careless input module is cut back to unit length.
  G.input.move.x = 1;
  G.input.move.y = 1;
  G.frames(60);
  near(p.speed, 3.8, 1e-9);
});

for (const fps of [30, 60, 144]) {
  test(`player: a jump peaks at about one metre (${fps} fps)`, () => {
    const G = setup({ dt: 1 / fps });
    const p = G.player;
    let apex = 0;
    let air = 0;
    G.input.hold('jump');
    G.seconds(1, () => {
      apex = Math.max(apex, p.pos.y);
      if (!p.onGround) air++;
    });
    G.input.release('jump');
    near(apex, 1.0, 0.03, 'apex');
    near(air / fps, 0.617, 2 / fps, 'air time');
    assert.equal(G.count['player:jump'], 1, 'holding jump does not repeat it');
    assert.equal(G.count['player:land'], 1);
    near(G.last['player:land'].speed, 6.48, 0.4, 'landing speed');
    assert.equal(p.health, 100, 'a jump does not hurt');
    assert.equal(p.onGround, true);
  });
}

test('player: coyote time — a jump still works 0.12 s after walking off a ledge, not later', () => {
  const ledge = (p) => p.addBox({ min: [-2, 0, -2], max: [2, 3, 2], surface: 'concrete' });
  const tryJump = (delayFrames) => {
    const G = setup({ build: ledge, dt: 1 / 120 });
    const p = G.player;
    p.pos.set(1.2, 3, 0);
    G.input.move.y = 1; // east, off the edge
    let left = -1;
    for (let i = 0; i < 400 && left < 0; i++) {
      G.frames(1);
      if (!p.onGround) left = i;
    }
    assert.ok(left >= 0, 'walked off the ledge');
    G.frames(delayFrames - 1); // the frame that noticed the fall was the first airborne one
    G.input.tap('jump');
    G.frames(1);
    return { jumped: (G.count['player:jump'] || 0) === 1, vy: p.vel.y };
  };
  // 0.12 s at 120 fps is 14.4 frames.
  assert.equal(tryJump(6).jumped, true, '0.05 s after the edge');
  assert.equal(tryJump(14).jumped, true, '0.117 s after the edge');
  assert.ok(tryJump(14).vy > 6, 'a full jump, whatever the fall speed was');
  assert.equal(tryJump(16).jumped, false, '0.133 s after the edge');
  assert.equal(tryJump(40).jumped, false, 'long gone');
});

test('player: jump buffer — a press up to 0.13 s before landing jumps on touchdown', () => {
  const run = (pressAtHeight) => {
    const G = setup({ dt: 1 / 120 });
    const p = G.player;
    p.pos.set(0, 2, 0);
    p.onGround = false;
    let pressedAt = -1;
    let landedAt = -1;
    G.frames(200, (i) => {
      if (pressedAt < 0 && p.pos.y <= pressAtHeight && !p.onGround) {
        pressedAt = i;
        G.input.tap('jump'); // read by the next frame
      }
      if (landedAt < 0 && G.count['player:land']) landedAt = i;
    });
    return { jumped: (G.count['player:jump'] || 0) === 1, gap: (landedAt - pressedAt) / 120, landed: landedAt >= 0 };
  };
  const late = run(0.35); // falling at about 5.9 m/s: 0.35 m is about 0.06 s from the ground
  assert.equal(late.landed, true);
  assert.ok(late.gap > 0.02 && late.gap < 0.13, `pressed ${late.gap.toFixed(3)} s before landing`);
  assert.equal(late.jumped, true, 'buffered');
  const early = run(1.2); // about 0.25 s before the ground
  assert.ok(early.gap > 0.13, `pressed ${early.gap.toFixed(3)} s before landing`);
  assert.equal(early.jumped, false, 'too early: forgotten');
});

test('player: crouch lowers the eye and the speed; no standing up without headroom; a jump needs it too', () => {
  const G = setup({ build: (p) => p.addBox({ min: [3, 1.3, -1], max: [6, 2, 1] }) }); // a low beam to the east
  const p = G.player;
  G.input.hold('crouch');
  G.frames(40);
  assert.equal(p.crouching, true);
  near(p.eye.y, 1.05, 0.01, 'crouched eye');
  near(G.camera.position.y, 1.05, 0.01);
  G.input.move.y = 1;
  G.frames(30);
  near(p.speed, 1.9, 1e-9, 'crouch speed');
  G.frames(110);
  assert.ok(p.pos.x > 3.3 && p.pos.x < 5.7, `under the beam at x = ${p.pos.x.toFixed(2)}`);
  G.input.release('crouch');
  G.input.move.y = 0;
  G.frames(20);
  assert.equal(p.crouching, true, 'no headroom: stays down');
  G.input.tap('jump');
  G.frames(20);
  assert.equal(G.count['player:jump'] || 0, 0, 'cannot jump under the beam');
  assert.equal(p.pos.y, 0);
  G.input.move.y = 1;
  G.frames(150);
  assert.ok(p.pos.x > 6.4);
  assert.equal(p.crouching, false, 'stood up once clear');
  near(p.eye.y, 1.68, 0.06);

  // In the open a jump from a crouch stands up first.
  G.input.move.y = 0;
  G.input.hold('crouch');
  G.frames(30);
  G.input.release('crouch');
  G.input.hold('crouch'); // keep it held, press jump
  G.input.tap('jump');
  G.frames(1);
  assert.equal(G.count['player:jump'], 1);
  assert.ok(p.vel.y > 6);
});

test('player: steps up 0.4 m, is stopped by 0.5 m, jumps onto 0.9 m, climbs a stair without leaving the ground', () => {
  const G = setup({
    build(p) {
      p.addBox({ min: [3, 0, -1], max: [5, 0.4, 1], surface: 'wood' }); // a 0.4 m ledge to the east
      p.addBox({ min: [-12, 0, -1], max: [-3, 0.5, 1], surface: 'metal' }); // a 0.5 m ledge to the west
      p.addBox({ min: [-1, 0, 5], max: [1, 0.9, 13], surface: 'concrete' }); // a 0.9 m dock to the south
      for (let i = 0; i < 11; i++) p.addBox({ min: [20 + i * 0.3, 0, -1], max: [20.3 + i * 0.3, (i + 1) * (2.8 / 11), 1], surface: 'wood' });
      p.addBox({ min: [23.3, 2.6, -1], max: [30, 2.8, 1], surface: 'wood' }); // deck
    },
  });
  const p = G.player;
  G.input.move.y = 1;
  G.frames(80);
  near(p.pos.y, 0.4, 1e-9, 'walked onto the 0.4 m ledge');
  assert.equal(p.surface, 'wood');
  assert.equal(G.count['player:land'] || 0, 0, 'a step, not a jump');
  assert.equal(G.count['player:jump'] || 0, 0);

  p.pos.set(0, 0, 0);
  p.vel.set(0, 0, 0);
  p.yaw = Math.PI / 2; // west
  G.frames(120);
  near(p.pos.x, -3 + 0.32, 1e-3, 'held by the 0.5 m ledge');
  assert.equal(p.pos.y, 0);
  G.input.hold('jump');
  G.frames(60);
  G.input.release('jump');
  near(p.pos.y, 0.5, 1e-9, 'a jump clears it');
  assert.equal(p.surface, 'metal');

  p.pos.set(0, 0, 2);
  p.vel.set(0, 0, 0);
  p.yaw = Math.PI; // south
  G.frames(70);
  near(p.pos.z, 5 - 0.32, 1e-3, 'held by the 0.9 m dock');
  assert.equal(p.pos.y, 0);
  G.input.hold('jump');
  G.frames(70);
  G.input.release('jump');
  near(p.pos.y, 0.9, 1e-9, 'a jump reaches the 0.9 m dock');

  p.pos.set(17, 0, 0);
  p.vel.set(0, 0, 0);
  p.yaw = EAST;
  const lands = G.count['player:land'];
  G.frames(1);
  let airborne = 0;
  let worstEyeStep = 0;
  let eyeY = p.eye.y;
  G.frames(150, () => {
    if (!p.onGround) airborne++;
    worstEyeStep = Math.max(worstEyeStep, Math.abs(p.eye.y - eyeY));
    eyeY = p.eye.y;
  });
  near(p.pos.y, 2.8, 1e-9, 'on the deck');
  assert.equal(airborne, 0, 'never left the ground on the stair');
  assert.equal(G.count['player:land'], lands);
  assert.ok(worstEyeStep < 0.075, `the eye glides up the 0.25 m risers (largest frame-to-frame move ${worstEyeStep.toFixed(3)} m)`);
});

test('player: fall damage starts above 13 m/s, lands with a dip, and a long fall kills', () => {
  const G = setup({ weapon: true });
  const p = G.player;
  // 2.8 m: no damage (7.67 m/s... below 13).
  p.pos.set(0, 2.8, 0);
  p.onGround = false;
  let lowestEye = Infinity;
  G.seconds(1.4, () => {
    if (p.onGround) lowestEye = Math.min(lowestEye, p.eye.y);
  });
  assert.equal(p.health, 100);
  assert.equal(G.count['player:land'], 1);
  near(G.last['player:land'].speed, Math.sqrt(2 * 21 * 2.8), 0.4);
  assert.ok(lowestEye < 1.68 - 0.08 && lowestEye > 1.68 - 0.21, `the landing dips the eye: ${lowestEye.toFixed(3)}`);
  near(p.eye.y, 1.68, 5e-3, 'and it settles');

  // 9 m: (speed − 13) × 7.
  p.pos.set(5, 9, 0);
  p.vel.set(0, 0, 0);
  p.onGround = false;
  let flash = 0;
  let rocked = 0;
  G.seconds(2, () => {
    flash = Math.max(flash, G.render.post.damage);
    rocked = Math.max(rocked, p.trauma);
  });
  assert.equal(p.pos.y, 0);
  near(p.health, 100 - (Math.sqrt(2 * 21 * 9) - 13) * 7, 3, 'fall damage from 9 m');
  assert.equal(G.last['player:hit'].kind, 'fall');
  assert.equal(G.last['player:hit'].from, null);
  assert.ok(flash > 0.9, `it flashes red: ${flash}`);
  assert.ok(rocked > 0.5, `a hard landing rocks the camera: ${rocked}`);
  assert.equal(p.alive, true);

  // 20 m: dead on the spot, in the right order.
  G.log.length = 0;
  p.pos.set(10, 20, 0);
  p.vel.set(0, 0, 0);
  p.onGround = false;
  p.health = 100;
  G.seconds(3);
  assert.equal(p.alive, false);
  assert.equal(p.health, 0);
  assert.deepEqual(G.log.filter((n) => n !== 'player:step'), ['player:land', 'player:hit', 'player:dead']);
});

test('player: damage, hurt pulse, shake, regeneration after the delay, heal', () => {
  const G = setup({ weapon: true });
  const p = G.player;
  p.regen.delay = 4;
  p.regen.rate = 25;
  const from = V(10, 1, 0);
  p.damage(30, from, 'bullet');
  assert.equal(p.health, 70);
  assert.deepEqual(G.last['player:hit'], { amount: 30, from, health: 70, kind: 'bullet' });
  G.frames(1);
  near(G.render.post.damage, Math.min(1, 0.35 + 30 / 40) - 1.9 * DT, 1e-9, 'hurt pulse (capped at 1)');
  near(p.trauma, 0.22 + 30 / 70 - 1.7 * DT, 1e-9, 'shake');
  assert.ok(Math.abs(G.camera.rotation.z) > 0, 'the camera rolls with the hit');
  near(Math.hypot(p.forward.x, p.forward.y, p.forward.z), 1, 1e-12);
  near(p.forward.x, 1, 1e-12, 'the aim does not shake');

  G.seconds(3.9);
  assert.equal(p.health, 70, 'nothing yet');
  p.damage(10, from, 'bolt'); // a hit restarts the delay
  G.seconds(3.9);
  assert.equal(p.health, 60);
  G.seconds(0.2);
  assert.ok(p.health > 60, 'regeneration has started');
  G.seconds(1.6);
  near(p.health, 100, 1e-9, '25 a second');
  near(G.render.post.damage, 0, 1e-12);
  near(G.render.post.lowHealth, 0, 1e-3);

  p.damage(80, null, 'blast');
  G.seconds(1.5);
  // 20 % health sits 0.186 of the way from "full effect" (12 %) to "none" (55 %): 1 − smoothstep = 0.909.
  near(G.render.post.lowHealth, 0.909, 0.005, 'health 20 %: the low-health look is nearly full');
  p.heal(35);
  assert.equal(p.health, 55);
  p.heal(500);
  assert.equal(p.health, 100, 'capped');

  // Ignored: nothing, negative, nonsense, while invulnerable.
  const hits = G.count['player:hit'];
  p.damage(0);
  p.damage(-5);
  p.damage(NaN);
  p.invulnerable = true;
  p.damage(50);
  assert.equal(p.health, 100);
  assert.equal(G.count['player:hit'], hits);
});

test('player: ?god=1 takes no damage', () => {
  const G = setup({ params: { god: '1' } });
  G.player.damage(500, null, 'bullet');
  assert.equal(G.player.health, 100);
  assert.equal(G.player.alive, true);
});

test('player: death — the camera collapses to the floor and onto its side, the body stops, reset restores', () => {
  const G = setup({ weapon: true });
  const p = G.player;
  G.input.move.y = 1;
  G.frames(30);
  p.damage(150, V(0, 1, 50), 'bullet'); // from the south = the right-hand side when facing east
  assert.equal(p.alive, false);
  assert.equal(p.health, 0);
  assert.equal(G.count['player:dead'], 1);
  assert.equal(G.last['player:dead'].from.z, 50);
  assert.equal(p.sprinting, false);
  const x0 = p.pos.x;
  G.seconds(0.4);
  assert.ok(G.camera.position.y < 1.6 && G.camera.position.y > 0.3, `on the way down: ${G.camera.position.y}`);
  G.seconds(1.1);
  near(G.camera.position.y, 0.22, 0.01, 'eye on the floor');
  near(G.camera.rotation.z, 1.15, 0.01, 'on its left side: away from the shot that came from the right');
  near(G.camera.rotation.x, -0.25, 0.01, 'looking slightly down');
  assert.ok(p.pos.x > x0 && p.pos.x < x0 + 1.2, 'the body slid to rest');
  near(p.speed, 0, 0.01);
  near(G.render.post.lowHealth, 1, 1e-12);
  // Dead men take no more damage and do not heal.
  p.damage(10);
  p.heal(50);
  assert.equal(p.health, 0);
  assert.equal(G.count['player:dead'], 1);

  p.reset({ pos: V(3, 0, 4), yaw: 1 });
  assert.equal(p.alive, true);
  p.yaw = EAST;
  p.damage(150, V(3, 1, -50), 'bullet'); // from the north = the left-hand side when facing east
  G.seconds(1.5);
  near(G.camera.rotation.z, -1.15, 0.01, 'a shot from the left drops the camera onto its right side');
  p.reset({ pos: V(3, 0, 4), yaw: 1 });
  assert.equal(p.health, 100);
  assert.deepEqual(p.pos.toArray(), [3, 0, 4]);
  assert.equal(p.yaw, 1);
  assert.equal(p.pitch, 0);
  assert.deepEqual(G.camera.position.toArray(), [3, 1.68, 4]);
  near(G.camera.rotation.z, 0, 1e-12);
  near(G.render.post.lowHealth, 0, 1e-12);
});

test('player: recoil — 35 % stays in the aim, the rest shows at once and recovers; bullets follow the view', () => {
  const G = setup({ weapon: true });
  const p = G.player;
  G.frames(2);
  p.addRecoil(0.02, 0.01);
  near(p.pitch, 0.02 * 0.35, 1e-12, 'permanent share of the pitch');
  near(p.yaw, EAST + 0.01 * 0.35, 1e-12, 'permanent share of the yaw');
  near(p.forward.y, Math.sin(0.02 * 0.35), 1e-12, 'the aim vector carries it in the same frame');
  near(G.camera.rotation.x, 0.02 * 0.35, 1e-12, 'and so does the picture');
  G.frames(4);
  const shown = G.camera.rotation.x;
  assert.ok(shown > 0.02 * 0.35 + 0.013 * 0.8, `the recoverable share has snapped on: ${shown}`);
  near(p.forward.y, Math.sin(shown), 1e-9, 'aim = view');
  G.seconds(1.5);
  near(G.camera.rotation.x, 0.02 * 0.35, 2e-5, 'back to the aim');
  near(p.pitch, 0.02 * 0.35, 1e-12, 'which keeps its share');
  // The aim clamp holds.
  for (let i = 0; i < 400; i++) p.addRecoil(0.05, 0);
  assert.equal(p.pitch, 1.5);
  G.frames(10);
  assert.ok(G.camera.rotation.x <= 1.55 + 1e-12, 'rendered pitch clamp');
  p.addRecoil(NaN, 0);
  p.addShake(NaN);
  G.frames(1);
  assert.ok(Number.isFinite(G.camera.rotation.x) && Number.isFinite(p.yaw));
});

test('player: look — sign convention, pitch clamp, slower while aiming', () => {
  const G = setup({ weapon: true });
  const p = G.player;
  G.input.look.dx = 0.1;
  G.input.look.dy = 0.05;
  G.frames(1);
  near(p.yaw, EAST - 0.1, 1e-12, 'dx > 0 turns right');
  near(p.pitch, -0.05, 1e-12, 'dy > 0 looks down');
  p.ads = 1;
  G.input.look.dx = 0.1;
  G.frames(1);
  near(p.yaw, EAST - 0.1 - 0.06, 1e-12, '× 0.6 at full aim');
  G.input.look.dy = -10;
  G.frames(1);
  assert.equal(p.pitch, 1.5, 'clamped');
  G.input.look.dx = NaN;
  G.frames(1);
  assert.ok(Number.isFinite(p.yaw), 'nonsense look input is ignored');
});

test('player: the view — aim FOV, bob, strafe lean, and no aim amount without a weapon', () => {
  const G = setup({ weapon: true });
  const p = G.player;
  p.ads = 1;
  G.seconds(1);
  near(G.camera.fov, 52, 0.05, 'aim field of view');
  G.input.move.y = 1;
  G.seconds(1);
  near(p.speed, 2.4, 1e-9, 'aim speed cap');
  p.ads = 0;
  G.seconds(1);
  near(G.camera.fov, 74, 0.1);

  // Walking bobs the eye by ±2.4 cm in step with the stride; standing still it rests.
  let lo = Infinity;
  let hi = -Infinity;
  G.seconds(2, () => {
    lo = Math.min(lo, p.eye.y);
    hi = Math.max(hi, p.eye.y);
  });
  near(hi - 1.68, 0.024, 0.004, 'bob up');
  near(1.68 - lo, 0.024, 0.004, 'bob down');
  G.input.move.y = 0;
  G.seconds(1.5);
  near(p.eye.y, 1.68, 1e-3, 'at rest');
  assert.equal(p.stridePhase % 1, 0, 'feet together');

  // Strafing right leans right (negative roll), about 0.68° at walk speed.
  G.input.move.x = 1;
  G.seconds(1.5);
  near(G.camera.rotation.z, -(3.8 / 6.4) * 0.02, 0.006, 'lean into the strafe');
  G.input.move.x = 0;

  // setFov clamps to 55…100.
  p.setFov(120);
  G.seconds(2);
  near(G.camera.fov, 100, 0.05);
  p.setFov(74);

  // With no weapon module the aim amount follows the aim input.
  const solo = setup();
  solo.input.hold('ads');
  solo.seconds(0.5);
  assert.ok(solo.player.ads > 0.99);
  solo.input.release('ads');
  solo.seconds(0.5);
  assert.ok(solo.player.ads < 0.01);
});

test('player: disabled — no movement, no look, the camera is left alone; the red flash still fades', () => {
  const G = setup({ weapon: true });
  const p = G.player;
  p.damage(40, null, 'bullet');
  G.frames(1);
  p.enabled = false;
  G.camera.position.set(7, 7, 7);
  G.camera.rotation.set(0.3, 0.2, 0.1, 'YXZ');
  G.camera.fov = 50;
  G.input.move.y = 1;
  G.input.look.dx = 0.4;
  const yaw = p.yaw;
  const flash = G.render.post.damage;
  G.seconds(1);
  assert.deepEqual(p.pos.toArray(), [0, 0, 0]);
  assert.equal(p.yaw, yaw);
  assert.deepEqual(G.camera.position.toArray(), [7, 7, 7]);
  assert.deepEqual([G.camera.rotation.x, G.camera.rotation.y, G.camera.rotation.z], [0.3, 0.2, 0.1]);
  assert.equal(G.camera.fov, 50);
  assert.ok(G.render.post.damage < flash, 'the hurt pulse decays');
  assert.equal(p.health, 60, 'no regeneration while disabled');
  p.addRecoil(0.02, 0); // a stray kick must not move the borrowed camera either
  assert.deepEqual(G.camera.position.toArray(), [7, 7, 7]);
  p.enabled = true;
  G.input.look.dx = 0;
  G.frames(1);
  near(G.camera.position.y, 1.68, 0.03, 'takes the camera back');
});

test('player: explosions shake the camera by distance, once', () => {
  const G = setup({ weapon: true });
  const p = G.player;
  const half = 0.15 + 0.9 * 0.25; // half the range away
  G.frames(1);
  G.events.emit('explosion', { pos: V(14, 1.68, 0), radius: 6.5, size: 'big', source: null });
  G.frames(1);
  near(p.trauma, half - 1.7 * DT, 1e-6, 'half the range away');
  G.seconds(1);
  G.events.emit('explosion', { pos: V(14, 1.68, 0), radius: 3, size: 'small', source: null });
  G.frames(1);
  near(p.trauma, half * 0.6 - 1.7 * DT, 1e-6, 'a small blast shakes less');
  G.seconds(1);
  G.events.emit('explosion', { pos: V(40, 1.68, 0), radius: 6.5, size: 'big', source: null });
  G.frames(1);
  assert.equal(p.trauma, 0, 'out of range');
  // The explosives module adds the same shake itself for a tank or a rack: the two do not stack.
  G.events.emit('explosion', { pos: V(14, 1.68, 0), radius: 6.5, size: 'big', source: null });
  p.addShake(half);
  G.frames(1);
  near(p.trauma, half - 1.7 * DT, 1e-6, 'not doubled');
});

test('player: a trickle of shake (a train overhead) holds a steady rumble instead of vanishing', () => {
  const G = setup({ weapon: true });
  const p = G.player;
  // 0.42 trauma per second in per-frame slivers, as src/atmos does under the El.
  let peak = 0;
  G.seconds(2, () => {
    p.addShake(0.42 * DT);
    peak = Math.max(peak, Math.abs(G.camera.rotation.z));
  });
  near(p.trauma, 0.42 / 1.7, 0.01, 'held at rate / decay');
  assert.ok(peak > 0.002 && peak < 0.01, `a faint rumble: roll up to ${peak.toFixed(4)} rad`);
  G.seconds(1.5);
  assert.equal(p.trauma, 0, 'gone with the train');
  // The same at 144 fps and at 20 fps.
  for (const fps of [20, 144]) {
    const H = setup({ weapon: true, dt: 1 / fps });
    H.seconds(2, () => H.player.addShake(0.42 / fps));
    near(H.player.trauma, 0.42 / 1.7, 0.01, `${fps} fps`);
  }
  // An impulse on top still reads as an impulse.
  G.seconds(1, () => p.addShake(0.42 * DT));
  p.addShake(0.5);
  near(p.trauma, 0.5, 1e-9);
});

test('player: stays inside the play bounds and survives nonsense', () => {
  const G = setup();
  const p = G.player;
  p.pos.set(45, 0, 0);
  G.input.move.y = 1;
  G.seconds(2);
  near(p.pos.x, 46 - 0.4, 1e-9, 'kept 0.4 m inside the bounds');
  p.pos.set(NaN, 0, 0);
  G.frames(2);
  assert.ok(Number.isFinite(p.pos.x) && Number.isFinite(G.camera.position.x), 'a broken position is put back on solid ground');
  p.pos.set(0, -80, 0);
  G.frames(2);
  assert.ok(p.pos.y >= 0);
  G.player.update(0);
  G.player.update(NaN);
});

test('player: a step is announced once per stride, with the surface underfoot', () => {
  const G = setup({ weapon: true, build: (p) => p.addBox({ min: [4, -0.2, -3], max: [30, 0, 3], surface: 'wood' }) });
  const p = G.player;
  G.input.move.y = 1;
  G.seconds(4);
  // 3.8 m/s for 4 s is about 15.0 m: one step per 1.55 m.
  const walked = p.pos.x;
  assert.ok(Math.abs(G.count['player:step'] - Math.floor(walked / 1.55)) <= 1, `${G.count['player:step']} steps over ${walked.toFixed(1)} m`);
  G.count['player:step'] = 0;
  G.input.hold('sprint');
  const x0 = p.pos.x;
  G.seconds(3);
  assert.equal(G.last['player:step'].sprint, true);
  assert.ok(Math.abs(G.count['player:step'] - Math.floor((p.pos.x - x0) / 2.1)) <= 1, 'sprint stride is 2.1 m');
});
