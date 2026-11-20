// Stub weapon (CONTRACT 6.5): the Chopper as a bare trigger, no viewmodel.
//
// Hold fire for full auto through G.combat.hitscan, R reloads, right mouse aims (feeds player.ads),
// F strikes through G.combat.melee. The other guns are listed for the HUD but never drawn: swap does
// nothing.
// Emits weapon:fire / weapon:reload / weapon:dry / weapon:melee and draws a tracer per shot.
// Numbers come from src/config/weapons.js when it is there.

import * as THREE from 'three';
import { lerp, moveToward } from '../core/util.js';

const CHOPPER = {
  id: 'chopper',
  name: 'CHOPPER',
  auto: true,
  damage: 26,
  rpm: 720,
  magSize: 30,
  reserve: 150,
  range: 300,
  adsTime: 0.18,
  reload: { tactical: 2.24, empty: 2.72 },
  spread: { hip: 0.0125, ads: 0.0012 },
};
const NINE = { id: 'nine', name: 'NINE', magSize: 15 };
const MELEE = { duration: 0.55, reach: 2.3, cone: (50 * Math.PI) / 180, damage: 60, cooldown: 0.75 };
const COMMON = { headMultiplier: 2.2, lowAmmoFraction: 0.27, maxCatchUpShots: 3 };
const FIRING_HOLD = 0.14; // seconds the state reads 'firing' after a shot

export function createWeapon(G) {
  const config = (G.config && G.config.weapons) || {};
  const def = config.chopper || CHOPPER;
  const nine = config.nine || NINE;
  const strike = { ...MELEE, ...config.melee };
  const common = { ...COMMON, ...config.common };
  const interval = 60 / def.rpm;
  const rng = G.rng && typeof G.rng.fork === 'function' ? G.rng.fork('weapon') : null;
  const random = rng ? () => rng.next() : Math.random;

  const dir = new THREE.Vector3();
  const right = new THREE.Vector3();
  const up = new THREE.Vector3();
  const muzzle = new THREE.Vector3();
  const WORLD_UP = new THREE.Vector3(0, 1, 0);

  let cooldown = 0;
  let reloadLeft = 0; // > 0 while reloading
  let sinceShot = Infinity;
  let meleeLeft = 0; // strike in progress
  let meleeWait = 0; // until the next strike is allowed

  const weapon = {
    current: def.id,
    def,
    state: 'idle',
    mag: def.magSize,
    reserve: def.reserve,
    magSize: def.magSize,
    other: { id: nine.id, name: nine.name, mag: nine.magSize, reserve: Infinity },
    slots: [
      { id: def.id, name: def.name, kind: 'rifle', mag: def.magSize, reserve: def.reserve, magSize: def.magSize },
      { id: nine.id, name: nine.name, kind: 'pistol', mag: nine.magSize, reserve: Infinity, magSize: nine.magSize },
    ],
    spread: def.spread.hip,
    cue: '',
    reset,
    setVisible() {}, // nothing to show
    setView() {},
    addReserve(n, cap = Infinity) {
      weapon.reserve = Math.min(cap, weapon.reserve + n);
    },
    /** An ammo drop: `share` of the Chopper's pickup, up to its cap. Returns what was added. */
    resupply(share = 1) {
      const give = def.pickup || { rounds: 60, cap: 240 };
      const rounds = Math.min(Math.max(1, Math.round(give.rounds * share)), Math.max(0, give.cap - weapon.reserve));
      if (!(share > 0) || rounds <= 0) return [];
      weapon.reserve += rounds;
      return [{ id: def.id, name: def.name, rounds }];
    },
    drop() {
      cancelReload();
      weapon.state = 'lowered';
    },
    update,
  };

  const emit = (name, payload) => G.events && G.events.emit(name, payload);

  function reset() {
    weapon.mag = def.magSize;
    weapon.reserve = def.reserve;
    weapon.state = 'idle';
    weapon.cue = '';
    cooldown = reloadLeft = meleeLeft = meleeWait = 0;
    sinceShot = Infinity;
  }

  function startReload() {
    if (reloadLeft > 0 || weapon.mag >= def.magSize || weapon.reserve <= 0) return;
    const empty = weapon.mag === 0;
    reloadLeft = empty ? def.reload.empty : def.reload.tactical;
    emit('weapon:reload', { weapon: def.id, phase: 'start', empty });
  }

  function cancelReload() {
    if (reloadLeft <= 0) return;
    reloadLeft = 0;
    emit('weapon:reload', { weapon: def.id, phase: 'cancel', empty: weapon.mag === 0 });
  }

  function finishReload() {
    const empty = weapon.mag === 0;
    const n = Math.min(def.magSize - weapon.mag, weapon.reserve);
    weapon.mag += n;
    weapon.reserve -= n;
    emit('weapon:reload', { weapon: def.id, phase: 'done', empty });
  }

  function shoot(player) {
    weapon.mag--;
    if (G.combat.stats) G.combat.stats.shots++;
    sinceShot = 0;

    // A uniformly random direction inside the spread cone around the view direction.
    right.crossVectors(player.forward, WORLD_UP).normalize();
    up.crossVectors(right, player.forward);
    const r = Math.tan(weapon.spread) * Math.sqrt(random());
    const a = random() * Math.PI * 2;
    dir.copy(player.forward).addScaledVector(right, r * Math.cos(a)).addScaledVector(up, r * Math.sin(a)).normalize();

    const hit = G.combat.hitscan({
      origin: player.eye,
      dir,
      range: def.range,
      damage: def.damage,
      from: 'player',
      weapon: def.id,
      headMult: common.headMultiplier,
    });

    // Where a muzzle would be: ahead of the eye, low and to the right.
    muzzle.copy(player.eye).addScaledVector(player.forward, 0.6).addScaledVector(right, 0.16).addScaledVector(up, -0.13);
    if (G.fx && typeof G.fx.tracer === 'function') G.fx.tracer(muzzle, hit.point);
    emit('weapon:fire', { weapon: def.id, pos: muzzle.clone(), dir: dir.clone(), ads: player.ads });
  }

  function update(dt) {
    const input = G.input;
    const player = G.player;
    if (!input || !player) return;
    if (!player.alive || player.enabled === false) {
      if (weapon.state !== 'lowered') weapon.drop();
      player.ads = moveToward(player.ads, 0, dt / def.adsTime);
      return;
    }

    if (cooldown > 0) cooldown -= dt;
    sinceShot += dt;
    meleeLeft -= dt;
    meleeWait -= dt;

    if (input.pressed('melee') && meleeWait <= 0) {
      cancelReload();
      meleeLeft = strike.duration;
      meleeWait = strike.cooldown;
      const hit = G.combat.melee({
        origin: player.eye,
        dir: player.forward,
        reach: strike.reach,
        cone: strike.cone,
        damage: strike.damage,
      });
      emit('weapon:melee', { hit: hit.type === 'enemy' });
    }
    const striking = meleeLeft > 0;

    if (reloadLeft > 0) {
      reloadLeft -= dt;
      if (reloadLeft <= 0) finishReload();
    } else if (input.pressed('reload') && !striking) {
      startReload();
    }
    const reloading = reloadLeft > 0;

    // Aim: a linear ramp over the weapon's ADS time, blocked while reloading or striking.
    const wantAds = input.down('ads') && !reloading && !striking;
    player.ads = moveToward(player.ads, wantAds ? 1 : 0, dt / def.adsTime);
    if (G.render && G.render.post) G.render.post.ads = player.ads;
    weapon.spread = lerp(def.spread.hip, def.spread.ads, player.ads);

    const firing = !reloading && !striking && input.down('fire') && weapon.mag > 0;
    if (firing) {
      // The remainder carries over and a slow frame fires catch-up shots, so the rate of fire does not
      // depend on the frame rate.
      for (let n = 0; n < common.maxCatchUpShots && cooldown <= 0 && weapon.mag > 0; n++) {
        shoot(player);
        cooldown += interval;
      }
    } else {
      if (cooldown < 0) cooldown = 0; // an idle gun is simply ready: no banked shots
      if (!reloading && !striking && weapon.mag === 0 && input.pressed('fire')) {
        emit('weapon:dry', { weapon: def.id });
        startReload();
      }
    }

    weapon.state = striking ? 'melee' : reloadLeft > 0 ? 'reloading' : sinceShot < FIRING_HOLD ? 'firing' : 'idle';
    weapon.slots[0].mag = weapon.mag;
    weapon.slots[0].reserve = weapon.reserve;
    weapon.cue =
      reloadLeft > 0
        ? 'reloading'
        : weapon.mag === 0
          ? weapon.reserve > 0 ? 'reload' : 'empty'
          : weapon.mag <= Math.ceil(def.magSize * common.lowAmmoFraction) ? 'low' : '';
  }

  return weapon;
}
