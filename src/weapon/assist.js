// Aim assist (the `aimAssist` setting, on by default): pulling the aim trigger locks the view onto the
// Vulture nearest the crosshair and holds it there while the trigger stays down.
//
//   take   among the living within `range` and inside a cone around the aim, the one nearest the
//          crosshair that the eye can see
//   hold   the view turns to its chest (a Buzzard's hull): fast while the lock is taken, then it simply
//          stays on, recoil included, so a held burst keeps landing
//   pass   when it drops, the lock goes to the next one near where the gun is pointing
//   break  a hard flick of the mouse or stick lets go (and takes whatever the gun then points at);
//          so does losing sight of it for a moment, or letting the trigger go
//
// Numbers: src/config/weapons.js `assist`. No objects on screen: `lock` is what the HUD draws from.

import * as THREE from 'three';
import { clamp, wrapAngle } from '../core/util.js';

const DEFAULTS = {
  range: 75,
  cone: 0.3,
  coneTouch: 0.42,
  keep: 0.6,
  snap: 14,
  snapSecs: 0.22,
  track: 30,
  lostSecs: 0.45,
  flickRate: 2.6,
  reacquire: 0.18,
  retry: 0.1,
  chest: 0.7,
  seeEvery: 0.08,
  distanceWeight: 0.0015,
  tries: 4,
};

const has = (obj, method) => !!obj && typeof obj[method] === 'function';

export function createAssist(G, tuning) {
  const cfg = { ...DEFAULTS, ...tuning };
  /** What is locked right now: `point` is where the view is being held (world space). */
  const lock = { on: false, enemy: null, point: new THREE.Vector3() };

  const target = new THREE.Vector3();
  const to = new THREE.Vector3();
  const candidates = [];
  let held = 0; // seconds this lock has been on
  let lost = 0; // seconds since the target was last seen
  let wait = 0; // seconds before the next attempt to take a lock
  let seeIn = 0;
  let visible = true;
  let passOn = false; // the last lock ended in a kill: the next one may be a little further off the aim

  const enabled = () => !G.settings || typeof G.settings.get !== 'function' || G.settings.get('aimAssist') !== false;

  /** Where on a Vulture the lock holds: a Goon's upper chest, a Buzzard's middle. */
  function aimPoint(e, out) {
    if (e.type !== 'buzzard' && e.bodyLow && e.bodyHigh) return out.copy(e.bodyLow).lerp(e.bodyHigh, 0.8);
    out.copy(e.pos);
    if (e.type !== 'buzzard') out.y += (e.height || 1.8) * cfg.chest;
    return out;
  }

  const sees = (eye, point) => !has(G.physics, 'lineOfSight') || G.physics.lineOfSight(eye, point);

  /** The Vulture nearest the crosshair inside `cone` that the eye can see, or null. */
  function pick(player, cone) {
    const list = G.enemies && G.enemies.list;
    if (!Array.isArray(list)) return null;
    candidates.length = 0;
    const f = player.forward;
    for (let i = 0; i < list.length; i++) {
      const e = list[i];
      if (!e || !e.alive || !e.pos) continue;
      to.subVectors(aimPoint(e, target), player.eye);
      const dist = to.length();
      if (dist > cfg.range || dist < 0.4) continue;
      const angle = Math.acos(clamp(to.dot(f) / dist, -1, 1));
      if (angle > cone) continue;
      candidates.push({ e, score: angle + dist * cfg.distanceWeight });
    }
    candidates.sort((a, b) => a.score - b.score);
    for (let i = 0; i < candidates.length && i < cfg.tries; i++) {
      if (sees(player.eye, aimPoint(candidates[i].e, target))) return candidates[i].e;
    }
    return null;
  }

  function release(pause = 0) {
    lock.on = false;
    lock.enemy = null;
    held = 0;
    lost = 0;
    if (pause > wait) wait = pause;
  }

  function reset() {
    release();
    wait = 0;
    passOn = false;
  }

  /**
   * One frame. `aiming` is true while the aim trigger is down and the gun can come up to the eye.
   * Turns the player (player.turn when there is one) and keeps `lock` current.
   */
  function update(dt, player, input, aiming) {
    if (!aiming || !enabled() || !player || player.alive === false || !player.eye || !player.forward) {
      if (lock.on || wait > 0) reset();
      return;
    }
    wait -= dt;
    const look = input && input.look ? Math.hypot(input.look.dx || 0, input.look.dy || 0) : 0;
    const touch = !!input && input.device === 'touch';

    if (lock.enemy) {
      if (!lock.enemy.alive) {
        passOn = true;
        release(cfg.reacquire);
      } else if (dt > 0 && look / dt > cfg.flickRate) {
        passOn = false;
        release(cfg.reacquire);
      }
    }
    if (!lock.enemy) {
      if (wait > 0) return;
      const e = pick(player, passOn ? cfg.keep : touch ? cfg.coneTouch : cfg.cone);
      passOn = false;
      if (!e) {
        wait = cfg.retry;
        return;
      }
      lock.enemy = e;
      lock.on = true;
      held = 0;
      lost = 0;
      seeIn = 0;
      visible = true;
      aimPoint(e, lock.point);
    }

    // Sight is checked a few times a second; in between the point simply follows the target.
    aimPoint(lock.enemy, target);
    seeIn -= dt;
    if (seeIn <= 0) {
      seeIn = cfg.seeEvery;
      visible = sees(player.eye, target);
    }
    if (visible) {
      lost = 0;
      lock.point.copy(target);
    } else {
      lost += dt;
      if (lost > cfg.lostSecs) {
        release(cfg.reacquire);
        return;
      }
    }

    // From where the gun points now (recoil included) to the point, as yaw and pitch.
    const f = player.forward;
    to.subVectors(lock.point, player.eye);
    const flat = Math.hypot(to.x, to.z);
    if (flat < 1e-4 && Math.abs(to.y) < 1e-4) return;
    const yawError = wrapAngle(Math.atan2(-to.x, -to.z) - Math.atan2(-f.x, -f.z));
    const pitchError = Math.atan2(to.y, flat) - Math.asin(clamp(f.y, -1, 1));
    if (Math.hypot(yawError, pitchError) > cfg.keep) {
      release(cfg.reacquire);
      return;
    }
    held += dt;
    const k = 1 - Math.exp(-(held < cfg.snapSecs ? cfg.snap : cfg.track) * dt);
    if (has(player, 'turn')) player.turn(yawError * k, pitchError * k);
    else {
      player.yaw = wrapAngle((player.yaw || 0) + yawError * k);
      player.pitch = (player.pitch || 0) + pitchError * k;
    }
  }

  return { lock, update, reset };
}
