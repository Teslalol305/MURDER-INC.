// The weapon rules (src/weapon/logic.js through src/weapon.js) with scripted input, a scripted player
// and recording stand-ins for combat, fx and lights. No renderer: G has no viewmodel camera, so the
// module runs on its rules alone, which is also the path a failed viewmodel takes.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import * as playerConfig from '../src/config/player.js';
import * as weapons from '../src/config/weapons.js';
import { missingMembers } from '../src/core/contract.js';
import { createEvents } from '../src/core/events.js';
import { createRng } from '../src/core/rng.js';
import { createWeapon } from '../src/weapon.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const DT = 1 / 60;
const { chopper, nine, ar15, switch9, rocket, melee, common } = weapons;

function near(actual, expected, eps, label = '') {
  assert.ok(Math.abs(actual - expected) <= eps, `${label} expected ${expected} ± ${eps}, got ${actual}`);
}

/** Scripted stand-in for G.input. `hold` keeps an action down, `tap` presses it for one frame. */
function makeInput() {
  const held = new Set();
  const edges = new Set();
  const taps = new Set();
  return {
    move: { x: 0, y: 0 },
    look: { dx: 0, dy: 0 },
    device: 'kbm',
    aimSlow: 1,
    rumbles: 0,
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
    rumble() {
      this.rumbles++;
    },
    endFrame() {
      edges.clear();
      for (const a of taps) held.delete(a);
      taps.clear();
    },
  };
}

function setup() {
  const events = createEvents();
  const log = []; // [name, payload] of every weapon event, in order
  for (const name of ['weapon:fire', 'weapon:reload', 'weapon:dry', 'weapon:switch', 'weapon:melee', 'weapon:swing']) {
    events.on(name, (e) => log.push([name, e]));
  }
  const blasts = []; // every combat.explode() call
  const G = {
    THREE,
    params: {},
    events,
    log,
    rng: createRng(1994),
    time: { t: 0, dt: DT, frame: 0 },
    config: { weapons, player: playerConfig },
    input: makeInput(),
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
      kicks: [],
      shakes: [],
      addRecoil(pitch, yaw) {
        this.kicks.push([pitch, yaw]);
      },
      addShake(x) {
        this.shakes.push(x);
      },
    },
    combat: {
      stats: { shots: 0, hits: 0, kills: 0, headshots: 0, damageTaken: 0 },
      rays: [],
      strikes: [],
      strikeLands: false,
      hitscan(spec) {
        this.rays.push({ ...spec, origin: spec.origin.clone(), dir: spec.dir.clone(), at: G.clock });
        return { type: 'world', point: spec.origin.clone().addScaledVector(spec.dir, 20), normal: V(0, 0, 1), dist: 20 };
      },
      melee(spec) {
        this.strikes.push({ ...spec, at: G.clock });
        return { type: this.strikeLands ? 'enemy' : 'none' };
      },
      explode(spec) {
        blasts.push({ ...spec, pos: spec.pos.clone(), at: G.clock });
      },
    },
    blasts,
    fx: {
      tracers: [],
      flashes: [],
      shells: [],
      tracer(from, to, color, speed) {
        this.tracers.push({ from: from.clone(), to: to.clone(), color, speed });
      },
      muzzleFlash(pos, dir, scale, world) {
        this.flashes.push({ scale, world });
      },
      shell(pos, vel, kind) {
        this.shells.push(kind);
      },
    },
    render: {
      post: { ads: 0 },
      lights: {
        flashes: [],
        flash(pos, color, intensity, range, ttl) {
          this.flashes.push({ color, intensity, range, ttl });
        },
      },
    },
    wallAt: Infinity, // a wall across the street this far down −Z from the origin
    physics: {
      raycast: (origin, dir, maxDist, out) => {
        const dist = dir.z < 0 ? (origin.z + G.wallAt) / -dir.z : Infinity;
        if (!(dist >= 0 && dist <= maxDist)) return null;
        out.dist = dist;
        return out;
      },
    },
    aimOn: false,
    enemies: { aimTarget: () => G.aimOn },
    clock: 0,
  };
  G.weapon = createWeapon(G);
  /** Advances n frames of dt (the weapon's part of the loop, then the end of the frame). */
  G.step = (n = 1, dt = DT) => {
    for (let i = 0; i < n; i++) {
      G.clock += dt;
      G.weapon.update(dt);
      G.input.endFrame();
    }
  };
  G.run = (seconds, dt = DT) => G.step(Math.round(seconds / dt), dt);
  G.shots = () => G.combat.rays.length;
  G.names = (name) => log.filter((e) => e[0] === name).map((e) => e[1]);
  G.phases = () => G.names('weapon:reload').map((e) => e.phase);
  /** Swaps to the next gun and waits for the draw to finish. */
  G.swap = () => {
    G.input.tap('swap');
    G.run(common.holster + common.draw + 0.05);
  };
  /** Draws gun number n (1-based, the order of the weapon bar) and waits for it. */
  G.draw = (n) => {
    G.input.tap(`weapon${n}`);
    G.run(common.holster + common.draw + 0.05);
  };
  /** The weapon bar's entry for a gun. */
  G.slot = (id) => G.weapon.slots.find((slot) => slot.id === id);
  /** Fires n single rounds (works for both guns), then lets the gun settle. */
  G.fire = (n) => {
    const before = G.shots();
    for (let guard = 0; G.shots() - before < n && guard < 10000; guard++) {
      G.input.hold('fire');
      G.step(1);
      G.input.release('fire');
      if (!G.weapon.def.auto) G.step(1);
    }
    G.input.release('fire');
    assert.equal(G.shots() - before, n, `asked for ${n} rounds`);
    G.run(0.3);
  };
  return G;
}

test('weapon: exposes the contract and starts with a full Chopper', () => {
  const G = setup();
  const w = G.weapon;
  assert.deepEqual(missingMembers('weapon', w), []);
  assert.equal(w.current, 'chopper');
  assert.equal(w.def, chopper);
  assert.deepEqual([w.mag, w.reserve, w.magSize], [30, 150, 30]);
  assert.deepEqual(w.other, { id: 'nine', name: 'NINE', mag: 15, reserve: Infinity });
  assert.deepEqual(
    w.slots.map((slot) => [slot.id, slot.name, slot.kind, slot.mag, slot.reserve, slot.magSize]),
    [
      ['chopper', 'CHOPPER', 'rifle', 30, 150, 30],
      ['nine', 'NINE', 'pistol', 15, Infinity, 15],
      ['ar15', 'AR-15', 'rifle', 30, 120, 30],
      ['switch9', 'SWITCH', 'pistol', 33, 132, 33],
      ['rocket', 'ROCKET', 'launcher', 1, 3, 1],
    ],
    'all five guns are carried from the start',
  );
  assert.equal(w.state, 'idle');
  assert.equal(w.cue, '');
  near(w.spread, chopper.spread.hip, 1e-12);
  G.step(3);
  assert.equal(G.shots(), 0, 'nothing fires on its own');
});

test('weapon: the Chopper fires 720 rounds a minute at any frame rate', () => {
  const counts = {};
  for (const fps of [20, 30, 60, 144, 240]) {
    const G = setup();
    G.input.hold('fire');
    G.run(2, 1 / fps);
    counts[fps] = G.shots();
    assert.equal(G.combat.stats.shots, G.shots());
    assert.equal(G.weapon.mag, 30 - G.shots());
  }
  // 12 rounds a second: the first at once, then one per 1/12 s. Two seconds hold 24 intervals.
  for (const fps in counts) assert.ok(counts[fps] === 24 || counts[fps] === 25, `${fps} fps fired ${counts[fps]} rounds in 2 s`);

  // Shot times do not drift: at 60 fps the n-th round leaves within a frame of n / 12 s.
  const G = setup();
  G.input.hold('fire');
  G.run(2);
  G.combat.rays.forEach((ray, n) => near(ray.at - DT, n / 12, DT + 1e-9, `round ${n}`));

  // A hitch fires at most three catch-up rounds and banks nothing beyond that.
  const H = setup();
  H.input.hold('fire');
  H.step(1, 0.5);
  assert.equal(H.shots(), 1, 'the first frame has nothing to catch up on');
  H.step(1, 0.5);
  assert.equal(H.shots(), 1 + common.maxCatchUpShots);
  H.step(1, DT);
  assert.equal(H.shots(), 1 + common.maxCatchUpShots + 1, 'the next round is due at once, the rest of the backlog is gone');
  H.step(1, DT);
  assert.equal(H.shots(), 1 + common.maxCatchUpShots + 1);
});

test('weapon: every round is a ray from the eye plus tracer, flash, casing, light and event', () => {
  const G = setup();
  G.fire(1);
  const ray = G.combat.rays[0];
  assert.deepEqual(ray.origin.toArray(), G.player.eye.toArray());
  assert.deepEqual([ray.range, ray.damage, ray.from, ray.weapon, ray.headMult], [300, 26, 'player', 'chopper', 2.2]);
  near(ray.dir.length(), 1, 1e-9);

  assert.equal(G.fx.tracers.length, 1);
  near(G.fx.tracers[0].to.distanceTo(G.player.eye), 20, 1e-6, 'tracer ends on the hit');
  assert.ok(G.fx.tracers[0].from.distanceTo(G.player.eye) < 1.2, 'tracer starts at the muzzle');
  assert.deepEqual([G.fx.tracers[0].color, G.fx.tracers[0].speed], [common.tracer.color, common.tracer.speed]);
  assert.deepEqual(G.fx.flashes, [{ scale: chopper.flash.scale, world: false }]);
  assert.deepEqual(G.fx.shells, ['rifle']);
  assert.deepEqual(G.render.lights.flashes, [{ color: 0xffb020, intensity: 45, range: 9, ttl: 0.05 }]);
  assert.equal(G.input.rumbles, 1);

  const fired = G.names('weapon:fire');
  assert.equal(fired.length, 1);
  assert.deepEqual(Object.keys(fired[0]).sort(), ['ads', 'dir', 'pos', 'weapon']);
  assert.equal(fired[0].weapon, 'chopper');
  assert.ok(fired[0].pos.isVector3 && fired[0].dir.isVector3);

  // The Nine: its own damage, range, casing and a smaller flash.
  G.swap();
  G.fire(1);
  const second = G.combat.rays[1];
  assert.deepEqual([second.range, second.damage, second.weapon], [120, 34, 'nine']);
  assert.equal(G.fx.shells[1], 'pistol');
  near(G.fx.flashes[1].scale, nine.flash.scale, 1e-12);
  assert.equal(G.render.lights.flashes[1].intensity, 30);
});

test('weapon: the Nine fires once per press, buffers an early press and caps at 420 rounds a minute', () => {
  const G = setup();
  G.swap();
  assert.equal(G.weapon.current, 'nine');

  G.input.hold('fire');
  G.run(1);
  assert.equal(G.shots(), 1, 'holding the trigger is one round');
  G.input.release('fire');
  G.run(0.3);

  // Spam: a fresh press every frame for a second.
  const before = G.shots();
  for (let i = 0; i < 60; i++) {
    G.input.tap('fire');
    G.step(1);
  }
  const spam = G.shots() - before;
  assert.ok(spam === 7 || spam === 8, `420 rpm is 7 a second, got ${spam}`);
  G.run(0.3);

  // A press 0.1 s before the gun is ready still fires; one 0.2 s early is lost.
  const interval = 60 / nine.rpm;
  for (const [early, fires] of [[0.1, true], [0.2, false]]) {
    const n = G.shots();
    G.input.tap('fire');
    G.step(1);
    assert.equal(G.shots(), n + 1);
    G.run(interval - early - DT);
    G.input.tap('fire');
    G.run(early + 0.05);
    assert.equal(G.shots(), n + (fires ? 2 : 1), `a press ${early} s early ${fires ? 'fires' : 'is dropped'}`);
    G.run(0.3);
  }
});

test('weapon: a tactical reload moves the rounds when the magazine is seated', () => {
  const G = setup();
  const w = G.weapon;
  G.fire(10);
  assert.deepEqual([w.mag, w.reserve], [20, 150]);

  G.input.tap('reload');
  G.step(1);
  assert.equal(w.state, 'reloading');
  assert.equal(w.cue, 'reloading');
  G.run(chopper.reload.magIn - 3 * DT);
  assert.deepEqual([w.mag, w.reserve], [20, 150], 'nothing moves before the magazine is in');
  G.step(4);
  assert.deepEqual([w.mag, w.reserve], [30, 140], 'rounds count from the seated magazine');
  assert.equal(w.state, 'reloading', 'but the gun is not ready yet');
  G.input.hold('fire');
  G.run(chopper.reload.tactical - chopper.reload.magIn - 5 * DT);
  assert.equal(G.shots(), 10, 'no firing during a reload');
  G.input.release('fire');
  G.step(8);
  assert.equal(w.state, 'idle');
  assert.deepEqual(G.phases(), ['start', 'magout', 'magin', 'bolt', 'done']);
  assert.ok(G.names('weapon:reload').every((e) => e.weapon === 'chopper' && e.empty === false));

  // A full magazine does not reload.
  G.input.tap('reload');
  G.step(2);
  assert.equal(w.state, 'idle');
});

test('weapon: an empty reload takes longer, and the reserve runs out for the Chopper only', () => {
  const G = setup();
  const w = G.weapon;
  G.fire(30);
  assert.deepEqual([w.mag, w.cue], [0, 'reload']);
  G.input.tap('reload');
  G.run(chopper.reload.tactical + 0.1);
  assert.equal(w.state, 'reloading', 'the empty variant is still going after the tactical time');
  assert.deepEqual([w.mag, w.reserve], [30, 120]);
  G.run(chopper.reload.empty - chopper.reload.tactical);
  assert.equal(w.state, 'idle');
  assert.ok(G.names('weapon:reload').every((e) => e.empty === true));
  assert.deepEqual(G.phases(), ['start', 'magout', 'magin', 'bolt', 'done']);

  // Burn the reserve down to nothing.
  for (let left = 120; left > 0; left -= 30) {
    G.fire(30);
    G.input.tap('reload');
    G.run(chopper.reload.empty + 0.1);
    assert.deepEqual([w.mag, w.reserve], [30, left - 30]);
  }
  G.fire(10);
  assert.deepEqual([w.mag, w.reserve, w.cue], [20, 0, '']);
  G.input.tap('reload');
  G.step(2);
  assert.equal(w.state, 'idle', 'nothing to reload with');

  // Resupply tops up the Chopper (up to the cap) whichever gun is in hand; a short reserve gives a short magazine.
  w.addReserve(5, 240);
  assert.equal(w.reserve, 5);
  G.input.tap('reload');
  G.run(chopper.reload.tactical + 0.1);
  assert.deepEqual([w.mag, w.reserve], [25, 0]);
  G.fire(25);
  assert.equal(w.cue, 'empty');
  G.input.hold('fire');
  G.run(1);
  G.input.release('fire');
  assert.equal(w.state, 'idle', 'an empty gun with no reserve never reloads');

  G.swap();
  w.addReserve(90, 240);
  w.addReserve(90, 240);
  w.addReserve(90, 240);
  assert.equal(G.slot('chopper').reserve, 240, 'capped');
  assert.equal(w.reserve, Infinity, 'the Nine is untouched');
  assert.equal(G.slot('rocket').reserve, 3, 'rounds for the launcher do not come by the hundred');
  w.addReserve(2, 6, 'rocket');
  assert.equal(G.slot('rocket').reserve, 5, 'unless they are asked for by name');

  // The Nine never runs dry.
  G.fire(15);
  assert.deepEqual([w.mag, w.cue], [0, 'reload']);
  G.input.tap('reload');
  G.run(nine.reload.magIn - 3 * DT);
  assert.equal(w.mag, 0);
  G.step(4);
  assert.deepEqual([w.mag, w.reserve], [15, Infinity]);
  G.run(nine.reload.empty - nine.reload.magIn);
  assert.equal(w.state, 'idle');
  assert.deepEqual(G.phases().slice(-5), ['start', 'magout', 'magin', 'bolt', 'done']);

  // Its tactical reload has no slide to drop.
  G.fire(5);
  G.input.tap('reload');
  G.run(nine.reload.tactical + 0.05);
  assert.equal(w.state, 'idle');
  assert.equal(w.mag, 15);
  assert.deepEqual(G.phases().slice(-4), ['start', 'magout', 'magin', 'done']);
});

test('weapon: a cancelled reload keeps the rounds only if the magazine was seated', () => {
  // Switching away before the magazine is in: nothing gained.
  const G = setup();
  const w = G.weapon;
  G.fire(12);
  G.input.tap('reload');
  G.run(1);
  G.input.tap('swap');
  G.step(1);
  assert.equal(w.state, 'switching');
  assert.deepEqual(G.phases(), ['start', 'magout', 'cancel']);
  G.run(1);
  assert.equal(w.current, 'nine');
  assert.deepEqual([G.slot('chopper').mag, G.slot('chopper').reserve], [18, 150]);

  // Switching away after it is seated: the rounds are in the gun.
  const H = setup();
  H.fire(12);
  H.input.tap('reload');
  H.run(chopper.reload.magIn + 0.1);
  H.input.tap('swap');
  H.run(1);
  assert.deepEqual(H.phases(), ['start', 'magout', 'magin', 'cancel']);
  assert.deepEqual([H.slot('chopper').mag, H.slot('chopper').reserve], [30, 138]);

  // A melee strike cancels a reload too.
  const M = setup();
  M.fire(12);
  M.input.tap('reload');
  M.run(0.5);
  M.input.tap('melee');
  M.step(1);
  assert.equal(M.weapon.state, 'melee');
  assert.deepEqual(M.phases(), ['start', 'magout', 'cancel']);
  assert.deepEqual([M.weapon.mag, M.weapon.reserve], [18, 150]);
});

test('weapon: a dry pull clicks once and reloads by itself; an emptied magazine alone does not', () => {
  const G = setup();
  const w = G.weapon;
  G.input.hold('fire');
  G.run(30 / 12 + 0.2); // empties the magazine and keeps the trigger down
  assert.equal(G.shots(), 30);
  assert.equal(G.names('weapon:dry').length, 1, 'one click per trigger pull');
  const clickAt = G.clock;
  G.run(chopper.dryReloadDelay - 0.25);
  assert.equal(w.state, 'idle');
  G.run(0.2);
  assert.equal(w.state, 'reloading', 'the reload starts 0.32 s after the click');
  assert.ok(G.clock - clickAt < 0.5);
  G.input.release('fire');
  G.run(chopper.reload.empty);
  assert.deepEqual([w.mag, w.state], [30, 'idle']);

  // Emptying the magazine and letting go: no click, no reload.
  const H = setup();
  H.fire(30);
  H.run(2);
  assert.equal(H.names('weapon:dry').length, 0);
  assert.equal(H.weapon.state, 'idle');
  assert.equal(H.weapon.cue, 'reload');

  // The Nine: a click per press, then the reload 0.28 s on.
  const N = setup();
  N.swap();
  N.fire(15);
  N.input.tap('fire');
  N.step(1);
  assert.equal(N.names('weapon:dry').length, 1);
  assert.deepEqual(N.names('weapon:dry')[0], { weapon: 'nine' });
  N.run(nine.dryReloadDelay - 0.05);
  assert.equal(N.weapon.state, 'idle');
  N.run(0.1);
  assert.equal(N.weapon.state, 'reloading');
});

test('weapon: the spread cone in every stance', () => {
  const G = setup();
  const w = G.weapon;
  const p = G.player;
  const settle = () => G.run(1.2);
  const s = chopper.spread;

  settle();
  near(w.spread, 0.0125, 1e-6, 'hip');
  p.speed = 3;
  settle();
  near(w.spread, 0.0125 + 0.5 * 0.013, 1e-6, 'walking');
  p.speed = 6.4;
  settle();
  near(w.spread, 0.0125 + 0.013, 1e-6, 'sprint speed caps the penalty');
  p.speed = 0;
  p.onGround = false;
  settle();
  near(w.spread, 0.0125 + 0.022, 1e-6, 'airborne');
  p.onGround = true;
  p.crouching = true;
  settle();
  near(w.spread, 0.0125 - 0.002, 1e-6, 'crouched');

  G.input.hold('ads');
  settle();
  assert.equal(p.ads, 1);
  near(w.spread, 0.0012, 1e-6, 'aimed: crouching adds nothing');
  p.crouching = false;
  p.speed = 6;
  settle();
  near(w.spread, 0.0012 + 0.004, 1e-6, 'aimed and moving');
  p.speed = 0;
  G.input.release('ads');
  settle();

  // Bloom: each round adds 0.17 of the bloom term; six rapid rounds saturate it.
  G.input.hold('fire');
  G.run(6 / 12);
  G.input.release('fire');
  G.step(6);
  assert.ok(w.spread > s.hip + 0.85 * s.bloomHip, `six rapid rounds saturate the bloom: ${w.spread}`);
  assert.ok(w.spread <= s.hip + s.bloomHip + 1e-9);
  // It holds for a moment, then drains at 1.5 a second.
  G.run(common.bloomHold + 1 / s.decay + 0.4);
  near(w.spread, s.hip, 2e-5, 'and it recovers');
  // Paced single rounds never build it up.
  for (let i = 0; i < 6; i++) {
    G.input.hold('fire');
    G.step(1);
    G.input.release('fire');
    G.run(0.4);
  }
  assert.ok(w.spread < s.hip + 0.3 * s.bloomHip, `paced fire stays tight: ${w.spread}`);
  G.run(1);

  // Every round leaves inside the cone that was reported when it was fired.
  const H = setup();
  let widest = 0;
  H.input.hold('fire');
  for (let i = 0; i < 150; i++) {
    const cone = H.weapon.spread; // the cone the next round uses is at most one damp step wider
    const n = H.shots();
    H.step(1);
    if (H.shots() > n) {
      const angle = H.combat.rays[n].dir.angleTo(H.player.forward);
      widest = Math.max(widest, angle);
      assert.ok(angle <= Math.max(cone, H.weapon.spread) + 1e-9, `round ${n} left the cone: ${angle} > ${cone}`);
    }
  }
  assert.ok(widest > 0.004, 'and the cone is actually used');

  // The Nine has its own table.
  const N = setup();
  N.swap();
  N.run(1);
  near(N.weapon.spread, nine.spread.hip, 1e-6, 'nine hip');
  N.input.hold('ads');
  N.run(1);
  near(N.weapon.spread, nine.spread.ads, 1e-6, 'nine aimed');
});

test('weapon: the Chopper climbs then flattens and weaves; the Nine snaps; aim and crouch tame both', () => {
  const R = chopper.recoil;
  const G = setup();
  G.input.hold('fire');
  G.run(1.5); // 18 or 19 rounds
  G.input.release('fire');
  const kicks = G.player.kicks;
  assert.ok(kicks.length >= 18);
  kicks.forEach(([pitch, yaw], i) => {
    const n = i + 1;
    const k = n >= R.lateFrom ? R.lateScale : 1;
    assert.ok(pitch >= R.pitch * k * 0.85 - 1e-12 && pitch <= R.pitch * k * 1.15 + 1e-12, `round ${n} pitch ${pitch}`);
    const limit = n < R.weaveFrom ? R.yawEarly : R.weaveAmp + R.weaveRandom;
    assert.ok(Math.abs(yaw) <= limit + 1e-12, `round ${n} yaw ${yaw}`);
  });
  // The weave really swings both ways.
  const late = kicks.slice(R.weaveFrom - 1).map((k) => k[1]);
  assert.ok(Math.max(...late) > 0.002 && Math.min(...late) < -0.002, 'side-to-side weave');
  G.player.shakes.forEach((x) => near(x, R.shake, 1e-12));

  // A pause of more than 0.24 s starts a new burst: the climb is back at full strength.
  G.run(0.3);
  G.fire(1);
  assert.ok(G.player.kicks.at(-1)[0] >= R.pitch * 0.85 - 1e-12);

  // Aimed × 0.55, crouched × 0.85.
  const A = setup();
  A.input.hold('ads');
  A.player.crouching = true;
  A.run(0.5);
  A.fire(1);
  const scale = common.adsRecoilScale * common.crouchRecoilScale;
  const [pitch] = A.player.kicks[0];
  assert.ok(pitch >= R.pitch * scale * 0.85 - 1e-12 && pitch <= R.pitch * scale * 1.15 + 1e-12, `aimed crouched pitch ${pitch}`);
  near(A.player.shakes[0], R.shake * scale, 1e-12);

  const N = setup();
  N.swap();
  N.fire(8);
  for (const [p, y] of N.player.kicks) {
    assert.ok(p >= nine.recoil.pitch * 0.9 - 1e-12 && p <= nine.recoil.pitch * 1.1 + 1e-12);
    assert.ok(Math.abs(y) <= nine.recoil.yaw + 1e-12);
  }
  N.player.shakes.forEach((x) => near(x, nine.recoil.shake, 1e-12));
});

test('weapon: aiming is a held, eased ramp, blocked by reloads, switching and the sprint pose', () => {
  const G = setup();
  const p = G.player;
  G.input.hold('ads');
  G.step(5);
  const linear = (5 * DT) / chopper.adsTime;
  near(p.ads, linear ** 3 * (linear * (linear * 6 - 15) + 10), 1e-9, 'a linear ramp through a quintic ease');
  assert.ok(p.ads > 0.35 && p.ads < 0.5);
  near(G.render.post.ads, p.ads, 1e-12, 'the vignette follows');
  G.run(chopper.adsTime - 5 * DT + DT);
  assert.equal(p.ads, 1);
  G.input.release('ads');
  G.run(chopper.adsTime + DT);
  assert.equal(p.ads, 0);

  // Reloading drops the aim and keeps it down.
  G.fire(5);
  G.input.hold('ads');
  G.run(0.3);
  assert.equal(p.ads, 1);
  G.input.tap('reload');
  G.run(0.5);
  assert.equal(p.ads, 0);
  G.run(chopper.reload.tactical);
  assert.equal(p.ads, 1, 'and it comes back when the gun is ready');

  // So does switching.
  G.input.tap('swap');
  G.run(0.3);
  assert.equal(p.ads, 0);
  G.run(0.8);
  assert.equal(G.weapon.current, 'nine');
  assert.equal(p.ads, 1);
  G.input.release('ads');
  G.run(0.3);

  // The Nine comes up faster.
  G.input.hold('ads');
  G.run(nine.adsTime + DT);
  assert.equal(p.ads, 1);
  G.input.release('ads');
  G.run(0.3);
});

test('weapon: sprinting lowers the gun; firing or aiming waits for it to come back up', () => {
  const G = setup();
  const p = G.player;
  p.sprinting = true;
  G.run(0.5);
  assert.equal(G.weapon.state, 'lowered');
  near(G.weapon.anim.sprint, 1, 0.01);

  // The trigger: about a tenth of a second before the first round.
  G.input.hold('fire');
  let frames = 0;
  while (G.shots() === 0 && frames < 60) {
    G.step(1);
    frames++;
  }
  assert.ok(frames * DT > 0.03 && frames * DT < 0.15, `sprint-out took ${frames * DT} s`);
  assert.ok(G.weapon.anim.sprint < common.sprintFireGate);
  G.input.release('fire');
  G.run(0.5);
  assert.equal(G.weapon.state, 'lowered');

  // Aim: the ramp starts only once the gun is most of the way up.
  G.input.hold('ads');
  G.step(1);
  assert.equal(p.ads, 0);
  G.run(0.4);
  assert.equal(p.ads, 1);
  G.input.release('ads');

  // Not sprinting: instant.
  p.sprinting = false;
  G.run(0.5);
  const n = G.shots();
  G.input.hold('fire');
  G.step(1);
  assert.equal(G.shots(), n + 1);
});

test('weapon: switching takes 0.28 + 0.32 s, keeps each magazine and can be reversed', () => {
  const G = setup();
  const w = G.weapon;
  G.fire(7);
  G.input.tap('swap');
  G.step(1);
  assert.equal(w.state, 'switching');
  assert.equal(w.cue, '');
  assert.equal(w.current, 'chopper', 'still the Chopper while it goes down');
  G.input.hold('fire');
  G.run(common.holster - 3 * DT);
  assert.equal(w.current, 'chopper');
  G.step(4);
  assert.equal(w.current, 'nine');
  assert.equal(w.def, nine);
  assert.deepEqual([w.mag, w.reserve, w.magSize], [15, Infinity, 15]);
  assert.deepEqual(w.other, { id: 'ar15', name: 'AR-15', mag: 30, reserve: 120 }, 'the next one along the rack');
  assert.deepEqual([G.slot('chopper').mag, G.slot('chopper').reserve], [23, 150]);
  G.run(common.draw - 4 * DT);
  assert.equal(w.state, 'switching');
  assert.equal(G.shots(), 7, 'no firing mid-switch');
  G.input.release('fire');
  G.step(6);
  assert.equal(w.state, 'idle');
  assert.deepEqual(G.names('weapon:switch'), [
    { from: 'chopper', to: 'nine', phase: 'holster' },
    { from: 'chopper', to: 'nine', phase: 'draw' },
  ]);

  // Direct selection: 2 is already in hand, 1 goes back.
  G.input.tap('weapon2');
  G.step(2);
  assert.equal(w.state, 'idle');
  G.input.tap('weapon1');
  G.run(0.7);
  assert.equal(w.current, 'chopper');
  assert.equal(w.mag, 23);

  // Changing your mind on the way down: the same gun comes straight back, faster than a full switch.
  G.input.tap('swap');
  G.run(0.14);
  G.input.tap('weapon1');
  G.step(1);
  assert.equal(w.state, 'switching');
  G.run(common.draw * 0.5 + 2 * DT);
  assert.equal(w.state, 'idle');
  assert.equal(w.current, 'chopper');

  // Changing your mind on the way up: the new gun goes back down from where it was.
  G.input.tap('swap');
  G.run(common.holster + 0.08);
  assert.equal(w.current, 'nine');
  G.input.tap('weapon1');
  G.run(common.holster * 0.75 + 0.02);
  assert.equal(w.current, 'chopper', 'the reversal skips most of the holster');
  G.run(0.4);
  assert.equal(w.state, 'idle');
});

test('weapon: a melee strike lands at 0.16 s, lasts 0.55 s and needs 0.75 s between strikes', () => {
  const G = setup();
  const w = G.weapon;
  G.combat.strikeLands = true;
  G.input.tap('melee');
  G.step(1);
  assert.equal(w.state, 'melee');
  assert.deepEqual(G.names('weapon:swing'), [{ weapon: 'chopper' }]);
  assert.equal(G.combat.strikes.length, 0, 'the blow is still on its way');
  G.run(melee.hitAt - 3 * DT);
  assert.equal(G.combat.strikes.length, 0);
  G.step(4);
  assert.equal(G.combat.strikes.length, 1);
  const blow = G.combat.strikes[0];
  assert.deepEqual([blow.reach, blow.damage], [2.3, 60]);
  near(blow.cone, (50 * Math.PI) / 180, 1e-12);
  assert.equal(blow.origin, G.player.eye);
  assert.deepEqual(G.names('weapon:melee'), [{ hit: true }]);
  near(G.player.shakes.at(-1), melee.shake, 1e-12);

  // The gun is busy for the whole strike.
  G.input.hold('fire');
  G.input.hold('ads');
  G.run(melee.duration - melee.hitAt - 4 * DT);
  assert.equal(w.state, 'melee');
  assert.equal(G.shots(), 0);
  assert.equal(G.player.ads, 0);
  G.input.release('fire');
  G.input.release('ads');
  G.step(8);
  assert.equal(w.state, 'idle');

  // 0.75 s between strikes, measured from the start of the last one.
  G.input.tap('melee');
  G.step(1);
  assert.equal(w.state, 'idle', 'too soon');
  G.run(melee.cooldown - melee.duration);
  G.input.tap('melee');
  G.step(1);
  assert.equal(w.state, 'melee');
  G.run(1);
  assert.equal(G.combat.strikes.length, 2);
  assert.equal(G.combat.stats.shots, 0, 'a strike is not a shot');

  // A miss reports a miss.
  G.combat.strikeLands = false;
  G.input.tap('melee');
  G.run(0.3);
  assert.deepEqual(G.names('weapon:melee').at(-1), { hit: false });
  G.run(1);

  // Blocked while switching; a swap asked for mid-strike goes through afterwards.
  G.input.tap('swap');
  G.step(2);
  G.input.tap('melee');
  G.step(1);
  assert.equal(w.state, 'switching');
  G.run(1);
  assert.equal(w.current, 'nine');
  G.input.tap('melee');
  G.step(1);
  G.input.tap('swap');
  G.step(1);
  assert.equal(w.state, 'melee');
  assert.equal(w.current, 'nine');
  G.run(melee.duration);
  assert.equal(w.state, 'switching');
  G.run(1);
  assert.equal(w.current, 'ar15');
});

test('weapon: five guns on the rack: next, previous, by number, and quick presses run through it', () => {
  const G = setup();
  const w = G.weapon;
  const seen = [];
  for (let i = 0; i < 5; i++) {
    G.swap();
    seen.push(w.current);
  }
  assert.deepEqual(seen, ['nine', 'ar15', 'switch9', 'rocket', 'chopper'], 'swap steps to the next gun and wraps');

  G.input.tap('weaponPrev');
  G.run(common.holster + common.draw + 0.05);
  assert.equal(w.current, 'rocket', 'previous wraps the other way');
  assert.equal(w.def, rocket);
  assert.deepEqual([w.mag, w.reserve, w.magSize], [1, 3, 1]);

  for (const [n, id, def] of [[3, 'ar15', ar15], [4, 'switch9', switch9], [5, 'rocket', rocket], [2, 'nine', nine], [1, 'chopper', chopper]]) {
    G.draw(n);
    assert.equal(w.current, id, `key ${n}`);
    assert.equal(w.def, def);
    assert.equal(w.magSize, def.magSize);
  }

  // Three quick presses: the gun in hand goes down once and the third one along comes up.
  const before = G.names('weapon:switch').length;
  G.input.tap('swap');
  G.step(2);
  G.input.tap('swap');
  G.step(2);
  G.input.tap('swap');
  G.step(1);
  assert.equal(w.state, 'switching');
  assert.equal(w.current, 'chopper', 'still on its way down');
  G.run(common.holster + common.draw + 0.05);
  assert.equal(w.current, 'switch9');
  assert.equal(w.state, 'idle');
  assert.deepEqual(G.names('weapon:switch').slice(before), [
    { from: 'chopper', to: 'nine', phase: 'holster' },
    { from: 'chopper', to: 'switch9', phase: 'draw' },
  ]);
});

test('weapon: the AR-15 and the SWITCH are automatics with their own rate, magazine and reserve', () => {
  for (const [n, def] of [[3, ar15], [4, switch9]]) {
    const G = setup();
    const w = G.weapon;
    G.draw(n);
    assert.equal(w.def, def);
    G.input.hold('fire');
    G.run(1);
    G.input.release('fire');
    const perSecond = def.rpm / 60;
    assert.ok(Math.abs(G.shots() - perSecond) <= 1.01, `${def.name}: ${G.shots()} rounds in a second, wanted about ${perSecond}`);
    assert.equal(w.mag, def.magSize - G.shots());
    assert.ok(G.combat.rays.every((ray) => ray.weapon === def.id && ray.damage === def.damage && ray.range === def.range));
    assert.deepEqual(new Set(G.fx.shells), new Set([def.kind === 'pistol' ? 'pistol' : 'rifle']));

    // Run it dry: the reload brings a full magazine out of the gun's own reserve.
    G.input.hold('fire');
    G.run(def.magSize / perSecond + 0.5);
    G.input.release('fire');
    assert.equal(G.shots(), def.magSize);
    G.run(def.reload.empty + def.dryReloadDelay + 0.3);
    assert.deepEqual([w.mag, w.reserve], [def.magSize, def.reserve - def.magSize], def.name);
    assert.equal(w.state, 'idle');
    assert.equal(G.slot('chopper').reserve, chopper.reserve, 'every gun draws on its own reserve');
  }
});

test('weapon: the ROCKET sends a round that flies and goes off on what it meets', () => {
  const G = setup();
  const w = G.weapon;
  G.draw(5);
  G.wallAt = 40; // metres ahead of the eye
  G.input.tap('fire');
  G.step(1);
  assert.equal(G.shots(), 0, 'no ray: the round travels');
  assert.equal(G.combat.stats.shots, 0, 'and is not counted for accuracy');
  assert.deepEqual(G.names('weapon:fire').map((e) => e.weapon), ['rocket']);
  assert.equal(w.rockets.live, 1);
  assert.equal(w.mag, 0);
  assert.deepEqual(G.fx.shells, [], 'nothing to eject');
  assert.equal(G.blasts.length, 0);

  // 40 m at 62 m/s: a little under two thirds of a second.
  G.run(40 / rocket.projectile.speed - 0.05);
  assert.equal(G.blasts.length, 0, 'still in the air');
  G.run(0.1);
  assert.equal(G.blasts.length, 1);
  assert.equal(w.rockets.live, 0);
  const blast = G.blasts[0];
  assert.deepEqual([blast.radius, blast.damage, blast.playerScale], [rocket.projectile.radius, rocket.damage, rocket.projectile.playerScale]);
  assert.equal(blast.weapon, 'rocket', 'a kill by the blast is credited to the launcher');
  near(blast.pos.z, -40, 0.5, 'at the wall');
  assert.ok(blast.pos.z > -40, 'a little short of it, so the wall does not shield the blast');

  // One round in the tube: the next one is reached for at once, out of the reserve.
  assert.equal(w.state, 'reloading');
  G.run(rocket.reload.empty + rocket.reloadAfterShot);
  assert.deepEqual([w.mag, w.reserve], [1, 2]);
  assert.equal(w.state, 'idle');
  assert.deepEqual(G.phases(), ['start', 'magout', 'magin', 'done']);

  // With nothing in the way it goes off by itself when its motor is spent.
  G.wallAt = Infinity;
  G.input.tap('fire');
  G.run(rocket.projectile.life - 0.1);
  assert.equal(G.blasts.length, 1);
  G.run(0.2);
  assert.equal(G.blasts.length, 2);
  near(G.blasts[1].pos.z, -rocket.projectile.speed * rocket.projectile.life, 3);

  // A new run clears the air without a blast.
  G.run(rocket.reload.empty + 0.1);
  assert.deepEqual([w.mag, w.reserve], [1, 1]);
  G.input.tap('fire');
  G.step(2);
  assert.equal(w.rockets.live, 1);
  w.reset();
  assert.equal(w.rockets.live, 0);
  G.run(1);
  assert.equal(G.blasts.length, 2);
});

test('weapon: an ammo drop tops up every gun by its own measure, up to its own cap', () => {
  const G = setup();
  const w = G.weapon;
  assert.deepEqual(w.resupply(), [
    { id: 'chopper', name: 'CHOPPER', rounds: chopper.pickup.rounds },
    { id: 'ar15', name: 'AR-15', rounds: ar15.pickup.rounds },
    { id: 'switch9', name: 'SWITCH', rounds: switch9.pickup.rounds },
    { id: 'rocket', name: 'ROCKET', rounds: rocket.pickup.rounds },
  ]);
  assert.equal(w.reserve, chopper.reserve + chopper.pickup.rounds);
  assert.equal(G.slot('nine').reserve, Infinity, 'the Nine needs none');

  // Half a drop, for one gun only.
  assert.deepEqual(w.resupply(0.5, 'ar15'), [{ id: 'ar15', name: 'AR-15', rounds: ar15.pickup.rounds / 2 }]);
  assert.deepEqual(w.resupply(0.4, ['switch9']), [{ id: 'switch9', name: 'SWITCH', rounds: Math.round(switch9.pickup.rounds * 0.4) }]);

  // Up to the cap and no further; a full rack takes nothing.
  for (let i = 0; i < 12; i++) w.resupply();
  for (const def of [chopper, ar15, switch9, rocket]) assert.equal(G.slot(def.id).reserve, def.pickup.cap, def.name);
  assert.deepEqual(w.resupply(), []);
  assert.deepEqual(w.resupply(0), []);
});

test('weapon: dropped on death, back in hand after reset', () => {
  const G = setup();
  const w = G.weapon;
  G.fire(20);
  G.input.tap('reload');
  G.run(0.6);
  G.input.hold('ads');
  G.player.alive = false;
  G.step(1);
  assert.equal(w.state, 'lowered');
  assert.equal(w.cue, '');
  assert.equal(G.phases().at(-1), 'cancel');
  G.input.hold('fire');
  G.run(1);
  assert.equal(G.shots(), 20, 'a dead man does not shoot');
  assert.equal(G.player.ads, 0);
  G.input.release('fire');
  G.input.release('ads');

  G.swap(); // ignored
  assert.equal(w.current, 'chopper');

  G.player.alive = true;
  w.reset();
  assert.deepEqual([w.current, w.mag, w.reserve, w.state, w.cue], ['chopper', 30, 150, 'idle', '']);
  assert.deepEqual([w.other.mag, w.other.reserve], [15, Infinity]);
  G.fire(1);
  assert.equal(w.mag, 29);

  // drop() from outside behaves the same, and the gun is back as soon as the player is.
  w.drop();
  assert.equal(w.state, 'lowered');
  G.step(1);
  assert.equal(w.state, 'idle');
});

test('weapon: the wall probe and the gamepad aim slow-down', () => {
  const G = setup();
  const [from, full] = chopper.wallPull;
  G.wallAt = (from + full) / 2;
  G.run(1);
  near(G.weapon.anim.wall, 0.5, 0.01, 'halfway between start and full');
  G.wallAt = 0.2;
  G.run(1);
  near(G.weapon.anim.wall, 1, 0.01);
  G.input.hold('ads');
  G.run(1);
  near(G.weapon.anim.wall, common.wallAdsScale, 0.01, 'mostly suppressed when aimed');
  G.input.release('ads');
  G.wallAt = Infinity;
  G.run(1);
  near(G.weapon.anim.wall, 0, 0.01);

  // Mouse and touch: never slowed.
  G.aimOn = true;
  G.run(0.5);
  assert.equal(G.input.aimSlow, 1);
  // Pad: eases to 0.55 with an enemy under the crosshair, and back.
  G.input.device = 'pad';
  G.run(0.6);
  near(G.input.aimSlow, 0.55, 0.005);
  G.aimOn = false;
  G.run(0.6);
  near(G.input.aimSlow, 1, 0.005);
  G.aimOn = true;
  G.run(0.6);
  G.input.device = 'kbm';
  G.step(1);
  assert.equal(G.input.aimSlow, 1);
});
