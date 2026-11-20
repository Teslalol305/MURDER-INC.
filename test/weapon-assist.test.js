// The aim-assist lock (src/weapon/assist.js) on a scripted player and a handful of scripted Vultures.
// No renderer and no weapon: the lock only needs an eye, an aim and a list of targets.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { assist as tuning } from '../src/config/weapons.js';
import { createAssist } from '../src/weapon/assist.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const DT = 1 / 60;

/** A player standing at the origin, eye at 1.68 m, looking down −Z. `turn` is the real player's. */
function makePlayer() {
  const player = {
    alive: true,
    yaw: 0,
    pitch: 0,
    eye: V(0, 1.68, 0),
    forward: V(0, 0, -1),
    turns: 0,
    aimAt() {
      const cp = Math.cos(this.pitch);
      this.forward.set(-Math.sin(this.yaw) * cp, Math.sin(this.pitch), -Math.cos(this.yaw) * cp);
    },
    turn(yaw, pitch = 0) {
      this.yaw += yaw;
      this.pitch += pitch;
      this.turns++;
      this.aimAt();
    },
  };
  return player;
}

const goon = (x, z, extra = {}) => ({ type: 'goon', alive: true, pos: V(x, 0, z), height: 1.8, radius: 0.35, ...extra });
const buzzard = (x, y, z) => ({ type: 'buzzard', alive: true, pos: V(x, y, z), height: 0.5, radius: 0.5 });

function setup(list, settings) {
  const blocked = new Set(); // enemies the eye cannot see
  const G = {
    enemies: { list },
    physics: {
      lineOfSight: (from, to) => !list.some((e) => blocked.has(e) && Math.hypot(e.pos.x - to.x, e.pos.z - to.z) < 0.01),
    },
    settings: settings ? { get: (key) => settings[key] } : undefined,
  };
  const player = makePlayer();
  const input = { look: { dx: 0, dy: 0 }, device: 'kbm' };
  const assist = createAssist(G, tuning);
  const run = (seconds, aiming = true) => {
    for (let i = 0; i < Math.round(seconds / DT); i++) assist.update(DT, player, input, aiming);
  };
  /** Angle between where the player aims and a point. */
  const off = (point) => player.forward.angleTo(point.clone().sub(player.eye));
  return { G, player, input, assist, run, off, blocked };
}

test('assist: aiming takes the Vulture nearest the crosshair and brings the sights onto its chest', () => {
  // Three in front: one dead ahead but far, one a little left and near, one well off to the right.
  const far = goon(0.6, -40);
  const near = goon(-2.2, -12);
  const wide = goon(9, -10);
  const { player, assist, run, off } = setup([wide, far, near]);
  assert.equal(assist.lock.on, false);
  run(DT);
  assert.equal(assist.lock.on, true);
  assert.equal(assist.lock.enemy, far, 'nearest to the crosshair, not nearest to the player');
  const chest = far.pos.clone().setY(far.height * tuning.chest);
  assert.ok(off(chest) > 0.01, 'the first frame only starts the turn');
  run(tuning.snapSecs);
  assert.ok(off(chest) < 0.006, `on target after the snap, ${off(chest)} rad off`);
  run(0.3);
  assert.ok(off(chest) < 1e-4);
  assert.ok(assist.lock.point.distanceTo(chest) < 1e-9, 'the HUD is told where the lock holds');
  assert.ok(player.turns > 10, 'through player.turn');
});

test('assist: nothing in the cone, out of range, out of sight or switched off means no lock', () => {
  const side = setup([goon(12, -6)]); // 63° off the aim
  side.run(0.5);
  assert.equal(side.assist.lock.on, false);
  assert.equal(side.player.turns, 0);

  const distant = setup([goon(0, -(tuning.range + 5))]);
  distant.run(0.5);
  assert.equal(distant.assist.lock.on, false);

  const hidden = goon(0.5, -15);
  const behind = setup([hidden, goon(3.5, -15)]);
  behind.blocked.add(hidden);
  behind.run(DT);
  assert.equal(behind.assist.lock.enemy, behind.G.enemies.list[1], 'the nearest one it can see');

  const off = setup([goon(0.5, -15)], { aimAssist: false });
  off.run(0.5);
  assert.equal(off.assist.lock.on, false);
  assert.equal(off.player.turns, 0);

  const hip = setup([goon(0.5, -15)]);
  hip.run(0.5, false);
  assert.equal(hip.assist.lock.on, false, 'only while aiming');
  assert.equal(hip.player.turns, 0);
});

test('assist: the lock follows a moving target, a posed body and a Buzzard', () => {
  const runner = goon(-3, -14);
  const a = setup([runner]);
  a.run(0.4);
  for (let i = 0; i < 120; i++) {
    runner.pos.x += 5 * DT; // sprinting across the street
    a.assist.update(DT, a.player, a.input, true);
  }
  const chest = runner.pos.clone().setY(runner.height * tuning.chest);
  assert.ok(a.off(chest) < 0.03, `held on a runner, ${a.off(chest)} rad behind`);

  // A Goon with a body pose (crouched behind a car): the lock uses the pose, not the standing height.
  const crouched = goon(1, -10, { bodyLow: V(1, 0.25, -10), bodyHigh: V(1, 0.95, -10) });
  const b = setup([crouched]);
  b.run(0.6);
  assert.ok(Math.abs(b.assist.lock.point.y - 0.81) < 1e-9);
  assert.ok(b.off(V(1, 0.81, -10)) < 1e-3);

  const drone = buzzard(2, 6, -18);
  const c = setup([drone]);
  c.run(0.6);
  assert.ok(c.off(drone.pos) < 1e-3, 'a Buzzard is held at its middle');
  assert.ok(c.player.pitch > 0.2, 'looking up at it');
});

test('assist: recoil is taken out again, so a held burst stays on the target', () => {
  const target = goon(0, -20);
  const { player, run, off } = setup([target]);
  run(0.5);
  const chest = target.pos.clone().setY(target.height * tuning.chest);
  for (let shot = 0; shot < 20; shot++) {
    // A round kicks the view up and a little aside, as player.addRecoil does.
    player.pitch += 0.012;
    player.yaw += shot % 2 ? 0.004 : -0.004;
    player.aimAt();
    run(1 / 12);
    assert.ok(off(chest) < 0.004, `round ${shot}: ${off(chest)} rad off after the kick`);
  }
});

test('assist: a kill passes the lock on, a flick or lost sight drops it, letting go ends it', () => {
  const first = goon(0.5, -15);
  const second = goon(6, -16); // 20° to the right: outside the taking cone, inside the passing one
  const s = setup([first, second]);
  s.run(0.4);
  assert.equal(s.assist.lock.enemy, first);
  first.alive = false;
  s.run(DT);
  assert.equal(s.assist.lock.on, false, 'a beat before the next one');
  s.run(tuning.reacquire + 2 * DT);
  assert.equal(s.assist.lock.enemy, second, 'the next Vulture near the aim');
  s.run(0.4);
  assert.ok(s.off(second.pos.clone().setY(second.height * tuning.chest)) < 0.01);

  // A hard flick of the mouse breaks the lock; with the gun now pointing elsewhere nothing is taken.
  s.input.look.dx = 0.2;
  s.run(DT);
  s.input.look.dx = 0;
  assert.equal(s.assist.lock.on, false);
  s.player.yaw += 1.2;
  s.player.aimAt();
  s.run(0.5);
  assert.equal(s.assist.lock.on, false);

  // Small corrections do not break it.
  const t = setup([goon(0.5, -15)]);
  t.run(0.4);
  t.input.look.dx = 0.01;
  t.run(0.2);
  assert.equal(t.assist.lock.on, true);
  t.input.look.dx = 0;

  // Out of sight: held on the last point seen for a moment, then dropped.
  t.blocked.add(t.G.enemies.list[0]);
  t.run(tuning.lostSecs - 0.1);
  assert.equal(t.assist.lock.on, true);
  t.run(0.3);
  assert.equal(t.assist.lock.on, false);
  t.blocked.clear();
  t.run(tuning.reacquire + 0.2);
  assert.equal(t.assist.lock.on, true, 'taken again when it steps back out');

  // Letting the aim trigger go ends it at once; a dead player has no lock either.
  t.run(DT, false);
  assert.equal(t.assist.lock.on, false);
  assert.equal(t.assist.lock.enemy, null);
  t.run(0.3);
  assert.equal(t.assist.lock.on, true);
  t.player.alive = false;
  t.run(DT);
  assert.equal(t.assist.lock.on, false);
});

test('assist: a thumb gets a wider cone than a mouse', () => {
  const offAxis = goon(5.6, -15); // about 20.5° off the aim
  const mouse = setup([offAxis]);
  mouse.run(0.3);
  assert.equal(mouse.assist.lock.on, false);
  const thumb = setup([offAxis]);
  thumb.input.device = 'touch';
  thumb.run(0.3);
  assert.equal(thumb.assist.lock.on, true);
});
