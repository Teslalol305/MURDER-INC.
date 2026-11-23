// Golden vectors for the Unreal port: runs the web game's own logic modules (src/player.js, src/weapon/logic.js,
// src/explosives.js, src/combat.js, src/core/rng.js) in Node with scripted input, and writes what they did to
// unreal/MurderInc/Content/Data/golden/*.json. The automation tests MurderInc.Golden.* replay the same scripts
// against the C++ rules and must match these numbers, so the C++ is checked against the real game, not against a
// reading of it.
//
// Usage: node tools/ue-export/golden.mjs            (from the repository root; needs node_modules/three)
//
// Every file is in web units (metres, seconds, radians, +Y up, yaw 0 = north, + = left); the C++ tests convert.
// Harnesses follow test/input-player-player.test.js, test/weapon-logic.test.js and test/fx-explosives.test.js.

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { createCombat } from '../../src/combat.js';
import * as playerConfig from '../../src/config/player.js';
import * as weapons from '../../src/config/weapons.js';
import { createEvents } from '../../src/core/events.js';
import { createRng } from '../../src/core/rng.js';
import { KINDS as explosiveKinds, createExplosives } from '../../src/explosives.js';
import { createPhysics } from '../../src/physics.js';
import {
  approachVelocity, createPlayer, createRecoil, createShake, createSpring, sprintWanted, targetSpeed,
} from '../../src/player.js';
import { createWeapon } from '../../src/weapon.js';
import * as enemiesConfig from '../../src/config/enemies.js';
import * as flowConfig from '../../src/config/flow.js';
import { goldenDirectors, goldenEnemies, goldenEnemyLogic, goldenFlowRules, goldenWorld, loadLevel } from './golden-ai.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const OUT = join(ROOT, 'unreal', 'MurderInc', 'Content', 'Data', 'golden');
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const EAST = -Math.PI / 2; // web yaw that looks toward +X (Unreal yaw 0)
const SEED = 1994;

/** Numbers to 12 significant digits: exact enough for every comparison, half the file size. */
function write(name, data) {
  const text = JSON.stringify(data, (k, v) => (typeof v === 'number' && Number.isFinite(v) && !Number.isInteger(v) ? Number(v.toPrecision(12)) : v));
  mkdirSync(OUT, { recursive: true });
  writeFileSync(join(OUT, name), text + '\n');
  console.log(`${name}: ${text.length} bytes`);
}

const about = (what) =>
  `Golden vectors written by tools/ue-export/golden.mjs from the web game's own modules (${what}). Web units: metres, seconds, radians, +Y up, yaw + = left. Do not edit: run the script.`;

// ------------------------------------------------------------------------------------------------ rng

function goldenRng() {
  const root = createRng(SEED);
  const next = Array.from({ length: 16 }, () => root.next());
  const forks = {};
  for (const label of ['weapon', 'explosives']) {
    const f = createRng(SEED).fork(label);
    forks[label] = { seed: f.seed, next: Array.from({ length: 8 }, () => f.next()) };
  }
  write('rng.json', { about: about('src/core/rng.js'), seed: SEED, next, forks });
}

// ------------------------------------------------------------------------------------ player: pure parts

function goldenPlayerPure() {
  const s = playerConfig.speed;
  const targetCases = [];
  for (const crouching of [false, true])
    for (const sprinting of [false, true])
      for (const ads of [0, 0.5, 1])
        for (const forward of [1, 0, -0.5, -1]) targetCases.push([crouching, sprinting, ads, forward, targetSpeed(s, crouching, sprinting, ads, forward)]);

  const sprintCases = [];
  const r = playerConfig.sprint;
  for (const [held, forward, strafe, crouching, ads, firing] of [
    [true, 1, 0, false, 0, false], [false, 1, 0, false, 0, false], [true, 0.55, 0, false, 0, false],
    [true, 0.56, 0, false, 0, false], [true, 0.707, 0.707, false, 0, false], [true, 0.8, 0.59, false, 0, false],
    [true, 1, 0, true, 0, false], [true, 1, 0, false, 0.35, false], [true, 1, 0, false, 0.34, false], [true, 1, 0, false, 0, true],
  ]) sprintCases.push([held, forward, strafe, crouching, ads, firing, sprintWanted(r, held, forward, strafe, crouching, ads, firing)]);

  const approach = [];
  for (const [vx, vz, wx, wz, rate, dt, snap, steps] of [
    [0, 0, 0, -3.8, 34, 1 / 60, true, 10], [0, -3.8, 0, 0, 26, 1 / 60, true, 12], [0, -3.8, 3.8, 0, 34, 1 / 60, true, 12],
    [2, 1, 0, 0, 0.6, 1 / 60, false, 5], [0, 0, 1, 1, 9, 1 / 30, true, 10], [6.4, 0, 3.8, 0, 34, 1 / 144, true, 12],
  ]) {
    const vel = { x: vx, z: vz };
    const out = [];
    for (let i = 0; i < steps; i++) {
      approachVelocity(vel, wx, wz, rate, dt, snap);
      out.push([vel.x, vel.z]);
    }
    approach.push({ vel: [vx, vz], wish: [wx, wz], rate, dt, snap, out });
  }

  // Recoil: a Chopper-like burst of 12 kicks at 1/60 with a kick every 5 frames, then 60 frames of recovery.
  const recoil = createRecoil(playerConfig.recoil);
  const recoilScript = [];
  for (let i = 0; i < 120; i++) {
    const dt = i < 60 ? 1 / 60 : 1 / 30;
    const kick = i < 60 && i % 5 === 0 ? [0.0068 * (1 + 0.1 * Math.sin(i)), 0.0011 * Math.cos(i * 1.7)] : null;
    if (kick) recoil.kick(kick[0], kick[1]);
    recoil.update(dt);
    recoilScript.push({ dt, kick, out: [recoil.pitch, recoil.yaw, recoil.targetPitch, recoil.targetYaw] });
  }

  // Shake: impulses, a trickle (a train overhead) and an explosion's "at least".
  const shake = createShake(playerConfig.shake);
  const shakeScript = [];
  for (let i = 0; i < 150; i++) {
    const dt = 1 / 60;
    const ops = [];
    if (i === 0) ops.push(['add', 0.31]);
    if (i === 20) ops.push(['add', 0.12], ['add', 0.12]);
    if (i >= 40 && i < 100) ops.push(['add', 0.42 * dt]);
    if (i === 70) ops.push(['atLeast', 0.6]);
    if (i === 75) ops.push(['atLeast', 0.2]);
    for (const [op, x] of ops) shake[op](x);
    shake.update(dt);
    shakeScript.push({ dt, ops, out: [shake.trauma, shake.pitch, shake.yaw, shake.roll] });
  }

  // The landing spring and the stair-glide spring.
  const springs = [];
  const step = playerConfig.bob.step;
  for (const [name, tune, kicks, dt] of [
    ['landing', playerConfig.bob.spring, { 0: -2.3, 50: -3.2, 52: -3.2 }, 1 / 60],
    ['landing30', playerConfig.bob.spring, { 0: -3.2 }, 1 / 30],
    ['stepLag', { stiffness: step.frequency * step.frequency, damping: 2 * step.frequency, min: -step.max, max: step.max }, {}, 1 / 60],
  ]) {
    const sp = createSpring(tune);
    if (name === 'stepLag') sp.offset = -0.233;
    const out = [];
    for (let i = 0; i < 80; i++) {
      if (kicks[i] !== undefined) sp.kick(kicks[i]);
      sp.update(dt);
      out.push([sp.offset, sp.velocity]);
    }
    springs.push({ name, tune, kicks, dt, start: name === 'stepLag' ? -0.233 : 0, out });
  }

  write('player_pure.json', {
    about: about('src/player.js pure parts'),
    targetSpeed: { fields: ['crouching', 'sprinting', 'ads', 'forward', 'speed'], cases: targetCases },
    sprintWanted: { fields: ['held', 'forward', 'strafe', 'crouching', 'ads', 'firing', 'wanted'], cases: sprintCases },
    approach,
    recoil: recoilScript,
    shake: shakeScript,
    springs,
  });
}

// ---------------------------------------------------------------------------------- player: whole update

function makePlayerInput() {
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
    tap: (a) => edges.add(a),
    release: (a) => held.delete(a),
    endFrame() {
      edges.clear();
      this.look.dx = this.look.dy = 0;
    },
  };
}

/**
 * One player scenario on an empty world (the ground plane only, bounds far away). `script(frame, G)` sets the
 * input of a frame before the update. Records every frame and every player event.
 */
function playerScenario(name, { dt = 1 / 60, frames, start = [0, 0, 0], weapon = false, regen, script }) {
  const events = createEvents();
  const G = {
    THREE,
    params: {},
    events,
    time: { t: 0, dt, frame: 0 },
    input: makePlayerInput(),
    camera: new THREE.PerspectiveCamera(74, 16 / 9, 0.08, 700),
    render: { post: { damage: 0, lowHealth: 0, ads: 0 } },
    level: { playerStart: { pos: V(...start), yaw: EAST } },
  };
  G.camera.rotation.order = 'YXZ';
  if (weapon) G.weapon = { update() {} }; // the scenario writes player.ads itself
  const log = [];
  let frame = -1;
  for (const ev of ['player:step', 'player:jump', 'player:land', 'player:hit', 'player:dead']) {
    events.on(ev, (e) => {
      const p = {};
      if (e && e.speed !== undefined) p.speed = e.speed;
      if (e && e.amount !== undefined) p.amount = e.amount;
      if (e && e.health !== undefined) p.health = e.health;
      if (e && e.kind !== undefined) p.kind = e.kind;
      if (e && e.sprint !== undefined) p.sprint = e.sprint;
      log.push([frame, ev, p]);
    });
  }
  G.physics = createPhysics(G);
  G.physics.setBounds({ minX: -460, maxX: 460, minZ: -340, maxZ: 340 });
  G.player = createPlayer(G);
  if (regen) G.player.regen = { ...regen };
  const rows = [];
  const inputs = [];
  for (frame = 0; frame < frames; frame++) {
    const before = { move: null, look: null, held: [], taps: [], ads: null, damage: null, recoilAfter: null };
    const ctl = {
      move: (x, y) => {
        G.input.move.x = x;
        G.input.move.y = y;
        before.move = [x, y];
      },
      look: (dx, dy) => {
        G.input.look.dx = dx;
        G.input.look.dy = dy;
        before.look = [dx, dy];
      },
      hold: (a) => {
        G.input.hold(a);
        before.held.push(a);
      },
      release: (a) => {
        G.input.release(a);
        before.held.push('-' + a);
      },
      tap: (a) => {
        G.input.tap(a);
        before.taps.push(a);
      },
      ads: (x) => {
        G.player.ads = x;
        before.ads = x;
      },
      damage: (amount, from, kind) => {
        before.damage = [amount, from ? [from.x, from.y, from.z] : null, kind];
        G.player.damage(amount, from, kind);
      },
      recoil: (pitch, yaw) => {
        before.recoilAfter = [pitch, yaw];
      },
    };
    script(frame, ctl, G);
    G.time.t += dt;
    G.time.frame++;
    G.player.update(dt);
    // After the update, as the weapon would: a recoil kick lands after the camera was placed.
    if (before.recoilAfter) G.player.addRecoil(...before.recoilAfter);
    G.input.endFrame();
    const p = G.player;
    const c = G.camera;
    inputs.push(before);
    rows.push([
      p.pos.x, p.pos.y, p.pos.z, p.vel.x, p.vel.y, p.vel.z, p.onGround ? 1 : 0, p.crouching ? 1 : 0, p.sprinting ? 1 : 0,
      p.eyeHeight, c.fov, p.health, p.stridePhase, p.eye.x, p.eye.y, p.eye.z, p.yaw, p.pitch,
      c.rotation.x, c.rotation.y, c.rotation.z, p.alive ? 1 : 0, G.render.post.damage, G.render.post.lowHealth, p.trauma,
    ]);
  }
  return {
    name,
    dt,
    frames,
    start,
    startYaw: EAST,
    regen: G.player.regen,
    inputs,
    fields: ['x', 'y', 'z', 'vx', 'vy', 'vz', 'onGround', 'crouching', 'sprinting', 'eyeHeight', 'fov', 'health', 'stridePhase',
      'eyeX', 'eyeY', 'eyeZ', 'yaw', 'pitch', 'camPitch', 'camYaw', 'camRoll', 'alive', 'hurt', 'lowHealth', 'trauma'],
    rows,
    events: log,
  };
}

function goldenPlayerSim() {
  const smootherstep = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * t * (t * (t * 6 - 15) + 10));
  const scenarios = [
    playerScenario('walk_stop', {
      frames: 70,
      script: (f, c) => {
        if (f === 0) c.move(0, 1);
        if (f === 35) c.move(0, 0);
      },
    }),
    playerScenario('sprint_diagonal_back', {
      frames: 120,
      script: (f, c) => {
        if (f === 0) {
          c.hold('sprint');
          c.move(0, 1);
        }
        if (f === 50) c.move(1, 1); // a keyboard diagonal: normalised, too much strafe to sprint
        if (f === 80) {
          c.release('sprint');
          c.move(0, -1);
        }
      },
    }),
    playerScenario('strafe_look', {
      frames: 60,
      script: (f, c) => {
        if (f === 0) c.move(1, 0);
        if (f < 30) c.look(4 + (f % 3), -2);
        if (f === 30) c.move(-0.5, 0.3);
      },
    }),
    playerScenario('jump_and_buffer', {
      frames: 110,
      script: (f, c) => {
        if (f === 2) c.hold('jump');
        if (f === 20) c.release('jump');
        if (f === 35) c.tap('jump'); // 0.03 s before touch-down: jumps on landing
        if (f === 40) c.move(0, 1);
      },
    }),
    playerScenario('jump_30fps', {
      dt: 1 / 30,
      frames: 40,
      script: (f, c) => {
        if (f === 1) c.tap('jump');
        if (f === 0) c.move(0, 1);
      },
    }),
    playerScenario('coyote_ok', {
      frames: 50,
      start: [0, 2, 0],
      script: (f, c) => {
        if (f === 6) c.tap('jump');
      },
    }),
    playerScenario('coyote_late', {
      frames: 50,
      start: [0, 2, 0],
      script: (f, c) => {
        if (f === 9) c.tap('jump');
      },
    }),
    playerScenario('fall_8m', { frames: 90, start: [0, 8, 0], script: () => {} }),
    playerScenario('fall_death', {
      frames: 150,
      start: [0, 20, 0],
      script: (f, c) => {
        if (f === 0) c.move(0, 1);
      },
    }),
    playerScenario('crouch_walk', {
      frames: 90,
      script: (f, c) => {
        if (f === 0) {
          c.hold('crouch');
          c.move(0, 1);
        }
        if (f === 45) c.release('crouch');
        if (f === 60) c.hold('sprint');
      },
    }),
    playerScenario('aim_fov', {
      frames: 70,
      weapon: true,
      script: (f, c) => {
        const t = (f + 1) / 60;
        const lin = f < 35 ? Math.min(1, t / 0.18) : Math.max(0, 1 - (t - 35 / 60) / 0.18);
        c.ads(smootherstep(lin));
        if (f === 10) c.move(0, 1);
      },
    }),
    playerScenario('regen_boss', {
      dt: 1 / 30,
      frames: 400,
      regen: { delay: 5.5, rate: 16 },
      script: (f, c) => {
        if (f === 1) c.damage(30, V(2, 1, 0), 'bullet');
        if (f === 90) c.damage(22, V(0, 1, -3), 'melee');
      },
    }),
    playerScenario('death_from_left', {
      frames: 90,
      script: (f, c) => {
        if (f === 5) c.damage(60, V(0, 1, -5), 'bullet'); // north of a player looking east: his left
        if (f === 6) c.damage(60, V(0, 1, -5), 'bullet');
        if (f === 7) c.damage(60, V(0, 1, -5), 'bullet'); // dead already: ignored
      },
    }),
  ];
  // Recoil through the player: kicks after the update, as the weapon applies them.
  scenarios.push(
    playerScenario('recoil_kicks', {
      frames: 60,
      script: (f, c) => {
        if (f < 24 && f % 5 === 0) c.recoil(0.0068, f < 15 ? 0.0011 : -0.004);
        if (f === 30) c.look(-3, 1);
      },
    }),
  );
  write('player_sim.json', { about: about('src/player.js createPlayer on src/physics.js, empty world'), scenarios });
}

// ------------------------------------------------------------------------------------------------ weapon

function makeWeaponInput() {
  const held = new Set();
  const edges = new Set();
  const taps = new Set();
  return {
    move: { x: 0, y: 0 },
    look: { dx: 0, dy: 0 },
    device: 'kbm',
    aimSlow: 1,
    down: (a) => held.has(a),
    pressed: (a) => edges.has(a),
    released: () => false,
    hold(a) {
      if (!held.has(a)) edges.add(a);
      held.add(a);
    },
    release: (a) => held.delete(a),
    tap(a) {
      this.hold(a);
      taps.add(a);
    },
    rumble() {},
    endFrame() {
      edges.clear();
      for (const a of taps) held.delete(a);
      taps.clear();
    },
  };
}

/** The weapon rules with a scripted player and a recording combat stand-in (test/weapon-logic.test.js). */
function weaponScenario(name, { dt = 1 / 60, frames, script, strikeLands = false }) {
  const events = createEvents();
  const log = [];
  let frame = -1;
  const G = {
    THREE,
    params: {},
    events,
    rng: createRng(SEED),
    time: { t: 0, dt, frame: 0 },
    config: { weapons, player: playerConfig },
    input: makeWeaponInput(),
    player: {
      eye: V(0, 1.68, 0),
      forward: V(0, 0, -1),
      vel: V(0, 0, 0),
      alive: true,
      enabled: true,
      onGround: true,
      sprinting: false,
      crouching: false,
      speed: 0,
      ads: 0,
      addRecoil(pitch, yaw) {
        shots.length && (shots[shots.length - 1].kick = [pitch, yaw]);
      },
      addShake(x) {
        if (shots.length && shots[shots.length - 1].frame === frame && shots[shots.length - 1].shake === undefined) shots[shots.length - 1].shake = x;
        else shakes.push([frame, x]);
      },
    },
    combat: {
      stats: { shots: 0, hits: 0, kills: 0, headshots: 0, damageTaken: 0 },
      hitscan(spec) {
        const f = G.player.forward;
        const right = new THREE.Vector3().crossVectors(f, new THREE.Vector3(0, 1, 0)).normalize();
        const up = new THREE.Vector3().crossVectors(right, f);
        shots.push({ frame, spread: G.weapon.spread, side: spec.dir.dot(right), lift: spec.dir.dot(up), range: spec.range, damage: spec.damage, headMult: spec.headMult, weapon: spec.weapon });
        return { type: 'world', point: spec.origin.clone().addScaledVector(spec.dir, 20), normal: V(0, 0, 1), dist: 20 };
      },
      melee(spec) {
        strikes.push([frame, spec.reach, spec.cone, spec.damage]);
        return { type: strikeLands ? 'enemy' : 'none' };
      },
    },
    physics: { raycast: () => null },
    enemies: { aimTarget: () => false },
  };
  const shots = [];
  const shakes = [];
  const strikes = [];
  for (const ev of ['weapon:fire', 'weapon:reload', 'weapon:dry', 'weapon:switch', 'weapon:melee', 'weapon:swing']) {
    events.on(ev, (e) => {
      const p = {};
      for (const k of ['weapon', 'phase', 'empty', 'from', 'to', 'hit', 'ads']) if (e && e[k] !== undefined) p[k] = e[k];
      log.push([frame, ev, p]);
    });
  }
  G.weapon = createWeapon(G);
  const rows = [];
  const inputs = [];
  for (frame = 0; frame < frames; frame++) {
    const rec = { held: [], taps: [], player: null };
    const ctl = {
      hold: (a) => {
        G.input.hold(a);
        rec.held.push(a);
      },
      release: (a) => {
        G.input.release(a);
        rec.held.push('-' + a);
      },
      tap: (a) => {
        G.input.tap(a);
        rec.taps.push(a);
      },
      player: (fields) => {
        Object.assign(G.player, fields);
        rec.player = fields;
      },
    };
    script(frame, ctl, G);
    G.weapon.update(dt);
    G.input.endFrame();
    inputs.push(rec);
    const w = G.weapon;
    rows.push([w.current, w.state, w.cue, w.mag, Number.isFinite(w.reserve) ? w.reserve : -1, w.spread, G.player.ads, w.anim.adsLinear, w.anim.sprint,
      w.other.mag]);
  }
  return {
    name,
    dt,
    frames,
    strikeLands,
    inputs,
    fields: ['current', 'state', 'cue', 'mag', 'reserve', 'spread', 'ads', 'adsLinear', 'sprint', 'otherMag'],
    rows,
    shots,
    shakes,
    strikes,
    events: log,
  };
}

function goldenWeapon() {
  const every = (f, start, period, count) => f >= start && (f - start) % period === 0 && (f - start) / period < count;
  const scenarios = [
    weaponScenario('chopper_hold', {
      frames: 400,
      script: (f, c) => {
        if (f === 0) c.hold('fire');
        if (f === 200) c.release('fire');
      },
    }),
    weaponScenario('chopper_hold_144', {
      dt: 1 / 144,
      frames: 300,
      script: (f, c) => {
        if (f === 0) c.hold('fire');
      },
    }),
    weaponScenario('chopper_hold_20', {
      dt: 1 / 20,
      frames: 40,
      script: (f, c) => {
        if (f === 0) c.hold('fire');
      },
    }),
    weaponScenario('chopper_tactical', {
      frames: 220,
      script: (f, c) => {
        if (every(f, 0, 2, 5)) c.tap('fire');
        if (f === 20) c.tap('reload');
        if (f === 200) c.tap('reload'); // full magazine: refused
      },
    }),
    weaponScenario('nine_presses', {
      frames: 260,
      script: (f, c) => {
        if (f === 0) c.tap('swap');
        if (every(f, 40, 6, 12)) c.tap('fire'); // a press every 0.1 s: the 0.13 s buffer catches the early ones
        if (f === 130) c.tap('reload');
      },
    }),
    weaponScenario('nine_empty', {
      frames: 360,
      script: (f, c) => {
        if (f === 0) c.tap('weapon2');
        if (every(f, 40, 10, 17)) c.tap('fire');
      },
    }),
    weaponScenario('aim_ramp', {
      frames: 150,
      script: (f, c) => {
        if (f === 0) c.hold('ads');
        if (f === 30) c.release('ads');
        if (f === 60) c.hold('ads');
        if (f === 70) c.tap('reload'); // magazine full: refused, the aim stays
        if (f === 80) c.tap('fire');
        if (f === 82) c.tap('reload'); // reload ramps the aim out
        if (f === 140) c.release('ads');
      },
    }),
    weaponScenario('switch_reverse', {
      frames: 160,
      script: (f, c) => {
        if (f === 0) c.tap('swap');
        if (f === 10) c.tap('swap'); // mid-holster: comes back up
        if (f === 40) c.tap('weapon2');
        if (f === 62) c.tap('weapon1'); // mid-draw of the NINE: holster again
        if (f === 63) c.tap('weapon1'); // already on its way: nothing
        if (f === 120) c.tap('melee');
        if (f === 122) c.tap('swap'); // queued until the strike ends
      },
    }),
    weaponScenario('melee_reload', {
      frames: 360,
      script: (f, c) => {
        if (every(f, 0, 2, 3)) c.tap('fire');
        if (f === 10) c.tap('reload');
        if (f === 70) c.tap('melee'); // 1.0 s in: before magIn, rounds stay out
        if (f === 150) c.tap('fire');
        if (f === 152) c.tap('reload');
        if (f === 250) c.tap('melee'); // 1.63 s in: after magIn, rounds stay in
      },
    }),
    weaponScenario('melee_land', {
      frames: 120,
      strikeLands: true,
      script: (f, c) => {
        if (f === 0) c.tap('melee');
        if (f === 20) c.tap('melee'); // still striking: refused
        if (f === 40) c.tap('melee'); // 0.67 s after the first began: refused
        if (f === 46) c.tap('melee'); // 0.77 s: a second strike
      },
    }),
    weaponScenario('spread_stances', {
      frames: 230,
      script: (f, c) => {
        if (f === 0) c.player({ speed: 6 });
        if (f === 30) c.player({ speed: 3.8, onGround: false });
        if (f === 60) c.player({ speed: 0, onGround: true, crouching: true });
        if (f === 90) c.hold('ads');
        if (f === 120) c.hold('fire');
        if (f === 140) c.release('fire');
        if (f === 160) {
          c.release('ads');
          c.player({ crouching: false });
          c.hold('fire');
        }
        if (f === 180) c.release('fire');
        if (f === 200) c.tap('swap');
      },
    }),
    weaponScenario('sprint_lower', {
      frames: 120,
      script: (f, c) => {
        if (f === 0) c.player({ sprinting: true, speed: 6.4 });
        if (f === 30) c.hold('fire');
        if (f === 50) c.release('fire');
        if (f === 60) c.hold('ads');
        if (f === 80) {
          c.release('ads');
          c.player({ sprinting: false, speed: 0 });
        }
      },
    }),
    weaponScenario('death_drop', {
      frames: 80,
      script: (f, c, G) => {
        if (f === 0) c.tap('reload');
        if (f === 0) c.tap('fire');
        if (f === 30) c.player({ alive: false });
        if (f === 50) {
          c.player({ alive: true });
          G.weapon.reset();
        }
      },
    }),
  ];
  write('weapon.json', { about: about('src/weapon/logic.js through src/weapon.js, scripted player and combat'), seed: SEED, scenarios });
}

// ------------------------------------------------------------------------------------- explosives, blast

/** Real physics, combat and explosives; a fake player and fake enemies (test/fx-explosives.test.js). */
function blastScenario(name, { entries, walls = [], player, enemies = [], frames, script }) {
  const events = createEvents();
  const log = [];
  let frame = -1;
  const emit = events.emit;
  events.emit = (ev, payload) => {
    if (ev === 'explosive:lit') log.push([frame, ev, { item: items.indexOf(payload.item), fuse: payload.fuse }]);
    if (ev === 'explosive:blast') log.push([frame, ev, { item: items.indexOf(payload.item), pos: [payload.pos.x, payload.pos.y, payload.pos.z] }]);
    if (ev === 'explosion') log.push([frame, ev, { pos: [payload.pos.x, payload.pos.y, payload.pos.z], radius: payload.radius, size: payload.size }]);
    emit(ev, payload);
  };
  const G = {
    THREE,
    events,
    rng: createRng(SEED),
    time: { t: 0, dt: 1 / 60, frame: 0 },
    config: { weapons },
    scene: new THREE.Scene(),
    level: { explosives: entries.map(([type, x, y, z, yaw]) => ({ type, pos: V(x, y, z), yaw })), groundSurfaceAt: () => 'asphalt' },
    props: {
      build(propName) {
        const object = new THREE.Group();
        const size = propName === 'propane_tank' ? [0.32, 0.6, 0.32] : [0.9, 1.6, 0.5];
        return { object, size, dynamic: true, setState() {} };
      },
    },
    fx: { addEmitter: () => ({ stop() {}, setPos() {}, setDir() {} }) },
    player: {
      pos: V(...player.pos),
      eye: V(player.pos[0], player.pos[1] + 1.6, player.pos[2]),
      alive: true,
      crouching: !!player.crouching,
      damage(amount, from, kind) {
        log.push([frame, 'player:damage', { amount, kind }]);
      },
      addShake(x) {
        log.push([frame, 'player:shake', { x }]);
      },
    },
    enemies: {
      list: enemies.map(([x, y, z, height, type], i) => ({ id: i, type: type || 'goon', pos: V(x, y, z), height, alive: true, hp: 1000 })),
      raycast: () => null,
      damage(enemy, amount) {
        log.push([frame, 'enemy:damage', { enemy: enemy.id, amount }]);
        return { killed: false };
      },
      alert() {},
    },
  };
  G.physics = createPhysics(G);
  for (const [min, max] of walls) G.physics.addBox({ min, max, surface: 'brick' });
  G.combat = createCombat(G);
  G.explosives = createExplosives(G);
  const items = G.explosives.items;
  const actions = [];
  for (frame = 0; frame < frames; frame++) {
    const ctl = {
      /** A round straight east into the item from 2 m west of it, 0.3 m up. */
      shoot: (index, damage, from = 'player') => {
        const item = items[index];
        actions.push([frame, 'shoot', index, damage, from === 'player' ? 'player' : 'enemy']);
        G.combat.hitscan({ origin: V(item.pos.x - 2, item.pos.y + 0.3, item.pos.z), dir: V(1, 0, 0), range: 50, damage, from: from === 'player' ? 'player' : { enemy: true } });
      },
      explode: (pos, radius, damage) => {
        actions.push([frame, 'explode', pos, radius, damage]);
        G.combat.explode({ pos: V(...pos), radius, damage });
      },
    };
    script(frame, ctl);
    G.time.frame++;
    G.time.t += 1 / 60;
    G.explosives.update(1 / 60);
  }
  return {
    name,
    dt: 1 / 60,
    frames,
    entries,
    walls,
    player,
    enemies,
    actions,
    final: items.map((i) => [i.state, i.hp]),
    events: log,
  };
}

function goldenBlast() {
  const scenarios = [
    blastScenario('propane_one_round', {
      entries: [['propane', 0, 0, 0, 0]],
      player: { pos: [3, 0, 0] },
      enemies: [[-2, 0, 0, 1.8], [0, 0, 5, 1.8], [0, 0, 20, 1.8]],
      frames: 120,
      script: (f, c) => {
        if (f === 0) c.shoot(0, 26);
      },
    }),
    blastScenario('propane_two_rounds_and_chain', {
      entries: [['propane', 0, 0, 0, 0], ['propane', 3, 0, 0, 0], ['rack', 0, 0, 5, 0], ['propane', 6, 0, 0, 0], ['propane', 0, 0, -9, 0]],
      player: { pos: [-4, 0, 0], crouching: true },
      enemies: [[2, 0, 2, 1.8], [1, 1.5, 0, 0.44, 'buzzard']],
      frames: 150,
      script: (f, c) => {
        if (f === 0) {
          c.shoot(0, 26);
          c.shoot(0, 26);
        }
      },
    }),
    blastScenario('rack_three_rounds_wall', {
      entries: [['rack', 0, 0, 0, 0], ['propane', 4, 0, 0, 0], ['rack', -3, 0, 2, Math.PI / 2]],
      walls: [[[1.5, 0, -3], [1.8, 3, 3]]],
      player: { pos: [3, 0, 0.5] },
      enemies: [[3, 0, -1, 1.8], [-3, 0, -3, 1.8]],
      frames: 150,
      script: (f, c) => {
        if (f === 0) c.shoot(0, 26);
        if (f === 6) c.shoot(0, 26);
        if (f === 12) c.shoot(0, 26);
      },
    }),
    blastScenario('enemy_rounds', {
      entries: [['propane', 0, 0, 0, 0]],
      player: { pos: [30, 0, 0] },
      frames: 140,
      script: (f, c) => {
        for (let i = 0; i < 6; i++) if (f === i * 4) c.shoot(0, 30, 'enemy'); // 9 each, whatever the round does
      },
    }),
    blastScenario('outside_blast_chains', {
      entries: [['propane', 0, 0, 0, 0], ['rack', 4, 0, 0, 0]],
      player: { pos: [1, 0, 1] },
      frames: 90,
      script: (f, c) => {
        if (f === 0) c.explode([2, 0.5, 0], 3, 30); // a Buzzard crash: size from its radius
      },
    }),
  ];
  write('blast.json', { about: about('src/explosives.js and src/combat.js on src/physics.js'), seed: SEED, scenarios });
}

/**
 * config.json is written with every number rounded to four decimals (lib/convert.cjs), which is not the game:
 * shake.onHit.perDamage is 1/70, not 0.0143, and the replay drifts by it. Every number of the player, weapon and
 * explosive tables whose source value rounds to the exported one is put back to the source value; nothing else
 * changes (a value the running game overrides differs from its module value and is left as exported).
 */
function refineConfig() {
  const file = join(ROOT, 'unreal', 'MurderInc', 'Content', 'Data', 'config.json');
  const { round, stringify } = createRequire(import.meta.url)('./lib/convert.cjs');
  const config = JSON.parse(readFileSync(file, 'utf8'));
  let refined = 0;
  const walk = (exported, source) => {
    if (!exported || !source || typeof exported !== 'object' || typeof source !== 'object') return;
    for (const key of Object.keys(exported)) {
      const e = exported[key];
      const v = source[key];
      if (typeof e === 'number' && typeof v === 'number' && v !== e && Number.isFinite(v) && round(v) === e) {
        exported[key] = v;
        refined++;
      } else {
        walk(e, v);
      }
    }
  };
  walk(config.player, playerConfig);
  walk(config.weapons, weapons);
  walk(config.explosives && config.explosives.kinds, explosiveKinds);
  walk(config.enemies, enemiesConfig);
  walk(config.flow, flowConfig);
  // enemiesResolved: the base tables with each difficulty's overlay laid over them (src/enemies.js retune).
  for (const d of Object.keys(config.enemiesResolved || {})) {
    if (!enemiesConfig.difficulty[d]) continue;
    const merged = {};
    for (const part of ['goon', 'buzzard', 'ai']) merged[part] = { ...enemiesConfig[part], ...(enemiesConfig.difficulty[d][part] || {}) };
    walk(config.enemiesResolved[d], merged);
  }
  writeFileSync(file, stringify(config, { exact: true }));
  console.log(`config.json: ${refined} numbers back to full precision`);
}

refineConfig();
goldenRng();
goldenPlayerPure();
goldenPlayerSim();
goldenWeapon();
goldenBlast();
{
  const level = loadLevel(ROOT);
  goldenWorld(level, SEED, write, about);
  goldenEnemyLogic(SEED, write, about);
  goldenEnemies(level, SEED, write, about);
  goldenFlowRules(level, SEED, write, about);
  goldenDirectors(level, SEED, write, about);
}
