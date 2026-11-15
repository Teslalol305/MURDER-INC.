// Weapon rules (CONTRACT 6.5): ammo, fire control, spread, recoil, aiming, reloads, switching, melee.
//
// This file owns no objects on screen. It returns the public `G.weapon` object and talks to the
// viewmodel through a small `view` interface (see NO_VIEW below), so the whole rule set also runs in a
// unit test with no renderer. Numbers live in src/config/weapons.js.
//
// One update, in order: timers → weapon select → melee → reload → timelines (switch, reload, strike)
// → sprint-lower blend → aim → spread → trigger → public state.

import * as THREE from 'three';
import * as WEAPONS from '../config/weapons.js';
import { clamp01, damp, lerp, moveToward, smootherstep } from '../core/util.js';
import { resetSpring, spring, stepSpring } from './springs.js';

const TAU = Math.PI * 2;
const WORLD_UP = new THREE.Vector3(0, 1, 0);
const CREDIT = 0.001; // an idle gun may bank this much of a shot interval, no more
const SHORT_TRACER = 0.9; // metres: nothing to draw between the muzzle and a hit this close

/** What the rules need from a viewmodel. Every method is optional work: this one does none of it. */
const NO_VIEW = {
  equip() {},
  fire() {},
  dry() {},
  reloadPhase() {},
  switchPhase() {},
  meleeStart() {},
  meleeLand() {},
  drop() {},
  pickUp() {},
  reset() {},
  /** Writes the muzzle in world space to `out`; false when there is no model to ask. */
  muzzleWorld: () => false,
  /** Writes the ejection port and a casing velocity in world space; false when there is no model. */
  ejectWorld: () => false,
};

export function createLogic(G, view = NO_VIEW) {
  const config = (G.config && G.config.weapons) || WEAPONS;
  const common = config.common;
  const strikeDef = config.melee;
  const order = common.order;
  const defs = {};
  for (const id of order) defs[id] = config[id];
  const pad = (G.config && G.config.player && G.config.player.input && G.config.player.input.pad) || {};
  const aim = {
    slow: pad.aimSlow ?? 0.55,
    range: pad.aimRange ?? 60,
    every: pad.aimEvery ?? 0.05,
    rate: pad.aimRate ?? 14,
  };

  const rng = G.rng && typeof G.rng.fork === 'function' ? G.rng.fork('weapon') : null;
  const random = rng ? rng.next : Math.random;
  const signed = () => random() * 2 - 1;
  const emit = (name, payload) => {
    if (G.events) G.events.emit(name, payload);
  };

  // Reload timelines, one per weapon and variant: [{t, phase}], in time order.
  const timelines = {};
  for (const id of order) {
    const r = defs[id].reload;
    const marks = (empty) => {
      const list = [
        { t: r.magOut, phase: 'magout' },
        { t: r.magIn, phase: 'magin' },
      ];
      const bolt = empty ? r.boltBack ?? r.slideRelease : r.pressCheck && r.pressCheck[0];
      if (bolt !== undefined) list.push({ t: bolt, phase: 'bolt' });
      list.push({ t: empty ? r.empty : r.tactical, phase: 'done' });
      return list;
    };
    timelines[id] = [marks(false), marks(true)];
  }

  // ---------------------------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------------------------

  const ammo = {};
  for (const id of order) ammo[id] = { mag: defs[id].magSize, reserve: defs[id].reserve };

  let current = order[0];
  let def = defs[current];
  let cooldown = 0; // seconds until the next shot may leave; negative = time owed to the next shot
  let sinceShot = Infinity;
  let burst = 0; // shots in the current burst
  let weavePhase = 0; // phase of the Chopper's side-to-side recoil weave, new for every burst
  let bloom = 0; // 0…1
  let heat = 0;
  let fireBuffer = 0; // semi-auto: a press is remembered this long
  let dryLatch = false; // one dry click per trigger pull
  let sustained = false; // full-auto fire carried over from the previous frame
  let autoReload = 0; // > 0: a dry pull scheduled a reload this far ahead
  let adsLinear = 0; // the aim ramp before easing
  let ads = 0;
  const sprint = spring(0); // sprint-lowered blend 0…1
  let wall = 0; // wall pull-back 0…1
  let wallTarget = 0;
  let wallTimer = 0;
  let reload = null; // {t, empty, marks, next}
  let swap = null; // {phase: 'holster' | 'draw', t, to}
  let strike = null; // {t, landed}
  let strikeWait = 0;
  let queuedSwap = null; // weapon asked for during a strike
  let dropped = false;
  let aimTimer = 0;
  let aimTarget = 1;

  const dir = new THREE.Vector3();
  const right = new THREE.Vector3();
  const up = new THREE.Vector3();
  const muzzle = new THREE.Vector3();
  const port = new THREE.Vector3();
  const casing = new THREE.Vector3();
  const probe = { dist: 0, point: new THREE.Vector3(), normal: new THREE.Vector3(), surface: null, box: null };

  /** What the viewmodel animates from, refreshed every update. */
  const anim = {
    id: current,
    ads: 0,
    adsLinear: 0,
    sprint: 0,
    wall: 0,
    heat: 0,
    reloading: false,
    reloadT: 0,
    reloadEmpty: false,
    switching: null, // 'holster' | 'draw'
    switchK: 0, // progress through that phase, 0…1
    switchTo: current,
    melee: false,
    meleeT: 0,
    trigger: false,
    mag: def.magSize,
    dropped: false,
  };

  const weapon = {
    current,
    def,
    state: 'idle',
    mag: def.magSize,
    reserve: def.reserve,
    magSize: def.magSize,
    other: { id: '', name: '', mag: 0, reserve: 0 },
    spread: def.spread.hip,
    cue: '',
    anim,
    reset,
    setVisible() {},
    setView() {},
    addReserve,
    drop,
    update,
  };

  const otherId = (id) => order[(order.indexOf(id) + 1) % order.length];
  const busy = () => reload !== null || swap !== null || strike !== null;

  // ---------------------------------------------------------------------------------------------
  // Public state
  // ---------------------------------------------------------------------------------------------

  function cueNow() {
    if (dropped || swap) return '';
    if (reload) return 'reloading';
    const a = ammo[current];
    if (a.mag === 0) return a.reserve > 0 ? 'reload' : 'empty';
    return a.mag <= Math.ceil(def.magSize * common.lowAmmoFraction) ? 'low' : '';
  }

  function stateNow() {
    if (dropped) return 'lowered';
    if (swap) return 'switching';
    if (strike) return 'melee';
    if (reload) return 'reloading';
    if (sprint.x > 0.5) return 'lowered';
    return sinceShot < common.firingHold ? 'firing' : 'idle';
  }

  function sync() {
    const a = ammo[current];
    weapon.current = current;
    weapon.def = def;
    weapon.mag = a.mag;
    weapon.reserve = a.reserve;
    weapon.magSize = def.magSize;
    weapon.state = stateNow();
    weapon.cue = cueNow();
    const id = otherId(current);
    weapon.other.id = id;
    weapon.other.name = defs[id].name;
    weapon.other.mag = ammo[id].mag;
    weapon.other.reserve = ammo[id].reserve;

    anim.id = current;
    anim.ads = ads;
    anim.adsLinear = adsLinear;
    anim.sprint = sprint.x;
    anim.wall = wall;
    anim.heat = heat;
    anim.reloading = reload !== null;
    anim.reloadT = reload ? reload.t : 0;
    anim.reloadEmpty = reload ? reload.empty : false;
    anim.switching = swap ? swap.phase : null;
    anim.switchK = swap ? clamp01(swap.t / (swap.phase === 'holster' ? common.holster : common.draw)) : 0;
    anim.switchTo = swap ? swap.to : current;
    anim.melee = strike !== null;
    anim.meleeT = strike ? strike.t : 0;
    anim.mag = a.mag;
    anim.dropped = dropped;
  }

  /** Clears everything that belongs to the gun in hand rather than to the run. */
  function settle() {
    cooldown = 0;
    sinceShot = Infinity;
    burst = 0;
    bloom = 0;
    heat = 0;
    fireBuffer = 0;
    dryLatch = false;
    sustained = false;
    autoReload = 0;
  }

  function equip(id) {
    current = id;
    def = defs[id];
    settle();
    view.equip(id);
  }

  function reset() {
    for (const id of order) {
      ammo[id].mag = defs[id].magSize;
      ammo[id].reserve = defs[id].reserve;
    }
    reload = swap = strike = queuedSwap = null;
    strikeWait = 0;
    dropped = false;
    adsLinear = ads = 0;
    resetSpring(sprint);
    wall = wallTarget = wallTimer = 0;
    aimTimer = 0;
    aimTarget = 1;
    current = order[0];
    def = defs[current];
    settle();
    weapon.spread = def.spread.hip;
    if (G.input) G.input.aimSlow = 1;
    view.reset(current);
    sync();
  }

  /** Resupply: tops up the reserve of every gun that has a finite one (the Chopper). */
  function addReserve(n, cap = Infinity) {
    if (!(n > 0)) return;
    for (const id of order) {
      const a = ammo[id];
      if (Number.isFinite(a.reserve) && a.reserve < cap) a.reserve = Math.min(cap, a.reserve + n);
    }
    sync();
  }

  /** The gun leaves Rule's hands (death). Everything in progress stops. */
  function drop() {
    if (dropped) return;
    cancelReload();
    swap = strike = queuedSwap = null;
    autoReload = 0;
    fireBuffer = 0;
    dropped = true;
    view.drop();
    sync();
  }

  // ---------------------------------------------------------------------------------------------
  // Reload
  // ---------------------------------------------------------------------------------------------

  function reloadEvent(phase, empty) {
    emit('weapon:reload', { weapon: def.id, phase, empty });
    view.reloadPhase(phase, empty);
  }

  function startReload() {
    const a = ammo[current];
    if (busy() || dropped || a.mag >= def.magSize || a.reserve <= 0) return false;
    const empty = a.mag === 0;
    autoReload = 0;
    fireBuffer = 0;
    reload = { t: 0, empty, marks: timelines[current][empty ? 1 : 0], next: 0 };
    reloadEvent('start', empty);
    return true;
  }

  /** Stops a reload. Rounds stay where they are: in the gun if the magazine was already seated. */
  function cancelReload() {
    if (!reload) return;
    const { empty } = reload;
    reload = null;
    reloadEvent('cancel', empty);
  }

  function advanceReload(dt) {
    reload.t += dt;
    while (reload && reload.next < reload.marks.length && reload.t >= reload.marks[reload.next].t) {
      const { phase } = reload.marks[reload.next++];
      const { empty } = reload;
      if (phase === 'magin') {
        // The rounds count from the moment the magazine is seated, not from the end of the reload.
        const a = ammo[current];
        const n = Math.min(def.magSize - a.mag, a.reserve);
        a.mag += n;
        a.reserve -= n;
      } else if (phase === 'done') {
        reload = null;
      }
      reloadEvent(phase, empty);
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Switching
  // ---------------------------------------------------------------------------------------------

  function switchEvent(from, to, phase) {
    emit('weapon:switch', { from, to, phase });
    view.switchPhase(phase, from, to);
  }

  function requestSwitch(id) {
    if (!defs[id] || dropped) return;
    if (strike) {
      queuedSwap = id; // goes through when the strike is over
      return;
    }
    if (!swap) {
      if (id === current) return;
      cancelReload();
      autoReload = 0;
      fireBuffer = 0;
      swap = { phase: 'holster', t: 0, to: id };
      switchEvent(current, id, 'holster');
    } else if (swap.phase === 'holster') {
      if (id === swap.to) return;
      // Changed their mind: the gun on its way down comes straight back up from where it got to.
      const from = swap.to;
      swap.phase = 'draw';
      swap.t = common.draw * (1 - swap.t / common.holster);
      swap.to = current;
      switchEvent(from, current, 'draw');
    } else if (id !== current) {
      // Mid-draw and they want the other gun back: holster again, as far along as the draw was short.
      swap.phase = 'holster';
      swap.t = common.holster * (1 - swap.t / common.draw);
      swap.to = id;
      switchEvent(current, id, 'holster');
    }
  }

  function advanceSwitch(dt) {
    swap.t += dt;
    if (swap.phase === 'holster' && swap.t >= common.holster) {
      const from = current;
      equip(swap.to);
      swap.phase = 'draw';
      swap.t -= common.holster;
      switchEvent(from, current, 'draw');
    }
    if (swap.phase === 'draw' && swap.t >= common.draw) swap = null;
  }

  // ---------------------------------------------------------------------------------------------
  // Melee
  // ---------------------------------------------------------------------------------------------

  function startStrike() {
    if (reload) {
      if (!strikeDef.cancelsReload) return;
      cancelReload();
    }
    autoReload = 0;
    fireBuffer = 0;
    strike = { t: 0, landed: false };
    strikeWait = strikeDef.cooldown;
    emit('weapon:swing', { weapon: def.id });
    view.meleeStart();
  }

  function advanceStrike(dt, player) {
    strike.t += dt;
    if (!strike.landed && strike.t >= strikeDef.hitAt) {
      strike.landed = true;
      const result = G.combat.melee({
        origin: player.eye,
        dir: player.forward,
        reach: strikeDef.reach,
        cone: strikeDef.cone,
        damage: strikeDef.damage,
      });
      const hit = !!result && result.type === 'enemy';
      const solid = hit || (!!result && result.type === 'world');
      if (solid && typeof player.addShake === 'function') player.addShake(hit ? strikeDef.shake : strikeDef.shake * 0.5);
      emit('weapon:melee', { hit });
      view.meleeLand(hit, solid);
      if (hit && G.input && typeof G.input.rumble === 'function') G.input.rumble(0.6, 0.4, 90);
    }
    if (strike.t >= strikeDef.duration) {
      strike = null;
      if (queuedSwap) {
        const id = queuedSwap;
        queuedSwap = null;
        requestSwitch(id);
      }
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Firing
  // ---------------------------------------------------------------------------------------------

  /** Stand-in positions when there is no model: ahead of the eye, low and to the right. */
  function guessMuzzle(player) {
    muzzle.copy(player.eye).addScaledVector(player.forward, 0.6).addScaledVector(right, 0.16).addScaledVector(up, -0.13);
  }

  function guessPort(player) {
    port.copy(player.eye).addScaledVector(player.forward, 0.35).addScaledVector(right, 0.17).addScaledVector(up, -0.12);
    casing
      .set(0, 0, 0)
      .addScaledVector(right, 2 + Math.random() * 1.2)
      .addScaledVector(up, 1.2 + Math.random() * 0.8)
      .addScaledVector(player.forward, Math.random() - 0.5);
    if (player.vel) casing.add(player.vel);
  }

  function shoot(player) {
    const a = ammo[current];
    a.mag--;
    burst++;
    sinceShot = 0;
    heat = Math.min(common.heat.max, heat + common.heat.perShot);
    if (G.combat.stats) G.combat.stats.shots++;

    // A uniformly random direction inside the spread cone around the aim.
    right.crossVectors(player.forward, WORLD_UP);
    if (right.lengthSq() < 1e-10) right.set(1, 0, 0);
    right.normalize();
    up.crossVectors(right, player.forward);
    const r = Math.tan(weapon.spread) * Math.sqrt(random());
    const angle = random() * TAU;
    dir.copy(player.forward).addScaledVector(right, r * Math.cos(angle)).addScaledVector(up, r * Math.sin(angle)).normalize();

    // The round leaves the eye, not the barrel: what the crosshair covers is what gets hit.
    const hit = G.combat.hitscan({
      origin: player.eye,
      dir,
      range: def.range,
      damage: def.damage,
      from: 'player',
      weapon: def.id,
      headMult: common.headMultiplier,
    });

    if (!view.muzzleWorld(muzzle)) guessMuzzle(player);
    if (!view.ejectWorld(port, casing)) guessPort(player);
    const fx = G.fx;
    if (fx) {
      if (hit.type === 'none' || hit.dist > SHORT_TRACER) fx.tracer(muzzle, hit.point, common.tracer.color, common.tracer.speed);
      fx.muzzleFlash(muzzle, dir, def.flash.scale * lerp(1, common.adsFlashScale, ads), false);
      fx.shell(port, casing, def.auto ? 'rifle' : 'pistol');
    }
    const flash = def.flash;
    if (G.render && G.render.lights) G.render.lights.flash(muzzle, flash.lightColor, flash.light, flash.lightRange, flash.lightTtl);
    emit('weapon:fire', { weapon: def.id, pos: muzzle.clone(), dir: dir.clone(), ads });

    // Recoil into the camera: the Chopper climbs, then weaves; the Nine snaps.
    const scale = lerp(1, common.adsRecoilScale, ads) * (player.crouching ? common.crouchRecoilScale : 1);
    const R = def.recoil;
    let pitch = R.pitch * scale * lerp(R.pitchRandom[0], R.pitchRandom[1], random());
    let yaw;
    if (R.weaveAmp === undefined) {
      yaw = signed() * R.yaw * scale;
    } else {
      if (burst >= R.lateFrom) pitch *= R.lateScale;
      yaw =
        burst < R.weaveFrom
          ? signed() * R.yawEarly * scale
          : (Math.sin(burst * R.weaveFreq + weavePhase) * R.weaveAmp + signed() * R.weaveRandom) * scale;
    }
    player.addRecoil(pitch, yaw);
    if (typeof player.addShake === 'function') player.addShake(R.shake * scale);

    bloom = Math.min(1, bloom + def.spread.shot);
    view.fire(burst, a.mag === 0, ads, !!player.crouching);
    if (G.input && typeof G.input.rumble === 'function') G.input.rumble(def.rumble.strong, def.rumble.weak, def.rumble.ms);
  }

  function dryFire() {
    dryLatch = true;
    if (def.dryCooldown) cooldown = def.dryCooldown;
    if (ammo[current].reserve > 0) autoReload = def.dryReloadDelay;
    emit('weapon:dry', { weapon: def.id });
    view.dry();
  }

  function pullTrigger(input, player) {
    const a = ammo[current];
    const held = input.down('fire');
    const canFire = !busy() && sprint.x < common.sprintFireGate;
    if (!held) dryLatch = false;

    // Only a gun that was already firing carries time over from the last frame; a fresh pull starts
    // from "ready" and banks nothing.
    const firing = def.auto && held && canFire && a.mag > 0;
    if (!(firing && sustained) && cooldown < -CREDIT) cooldown = -CREDIT;
    sustained = firing;

    if (def.auto) {
      if (firing) {
        // The remainder of the interval carries over and a slow frame fires catch-up shots, so the
        // rate of fire does not depend on the frame rate.
        for (let n = 0; n < common.maxCatchUpShots && cooldown <= 0 && a.mag > 0; n++) {
          shoot(player);
          cooldown += 60 / def.rpm;
        }
      } else if (held && canFire && !dryLatch && cooldown <= 0) {
        dryFire();
      }
    } else {
      // Semi-auto: one shot per press; a press a moment early still counts.
      if (input.pressed('fire')) fireBuffer = def.fireBuffer;
      if (fireBuffer > 0 && canFire && cooldown <= 0) {
        fireBuffer = 0;
        if (a.mag > 0) {
          shoot(player);
          cooldown = 60 / def.rpm;
        } else {
          dryFire();
        }
      }
    }
    if (cooldown < -CREDIT) cooldown = -CREDIT;
    anim.trigger = held && canFire;
  }

  // ---------------------------------------------------------------------------------------------
  // Per-frame pieces
  // ---------------------------------------------------------------------------------------------

  /** How close the wall straight ahead is: 0 (clear) … 1 (muzzle against it). Checked a few times a second. */
  function probeWall(dt, player) {
    wallTimer -= dt;
    if (wallTimer <= 0 && G.physics) {
      wallTimer = common.wallEvery;
      const [from, full] = def.wallPull;
      const hit = G.physics.raycast(player.eye, player.forward, from, probe);
      wallTarget = hit ? clamp01((from - hit.dist) / (from - full)) : 0;
    }
    wall = damp(wall, wallTarget * lerp(1, common.wallAdsScale, ads), common.wallRate, dt);
  }

  /** Gamepad aim assist: the look rate drops while an enemy is under the crosshair. Never a snap. */
  function assistAim(dt, input, player) {
    if (input.device !== 'pad') {
      aimTarget = 1;
      input.aimSlow = 1;
      return;
    }
    aimTimer -= dt;
    if (aimTimer <= 0) {
      aimTimer = aim.every;
      const enemies = G.enemies;
      const on = !!enemies && typeof enemies.aimTarget === 'function' && enemies.aimTarget(player.eye, player.forward, aim.range);
      aimTarget = on ? aim.slow : 1;
    }
    input.aimSlow = damp(typeof input.aimSlow === 'number' ? input.aimSlow : 1, aimTarget, aim.rate, dt);
  }

  function setAim(player, want, dt) {
    adsLinear = moveToward(adsLinear, want ? 1 : 0, dt / def.adsTime);
    ads = smootherstep(0, 1, adsLinear);
    player.ads = ads;
    if (G.render && G.render.post) G.render.post.ads = ads;
  }

  function update(dt) {
    const input = G.input;
    const player = G.player;
    if (!input || !player) return;

    if (player.alive === false) {
      drop();
      setAim(player, false, dt);
      input.aimSlow = 1;
      sync();
      return;
    }
    if (dropped) {
      // Back on his feet without a full reset: the gun is simply in hand again.
      dropped = false;
      view.pickUp();
    }

    cooldown -= dt;
    sinceShot += dt;
    strikeWait -= dt;
    fireBuffer -= dt;
    // Bloom holds for a moment after every round, so rapid fire stacks it and paced fire sheds it.
    if (sinceShot > common.bloomHold) bloom = Math.max(0, bloom - def.spread.decay * dt);
    heat = Math.max(0, heat - common.heat.cool * dt);
    if (burst > 0 && sinceShot > common.burstReset) {
      burst = 0;
      weavePhase = random() * TAU;
    }

    if (input.pressed('swap')) requestSwitch(otherId(swap && swap.phase === 'holster' ? swap.to : current));
    else if (input.pressed('weapon1')) requestSwitch(order[0]);
    else if (input.pressed('weapon2')) requestSwitch(order[1]);

    if (input.pressed('melee') && !strike && strikeWait <= 0 && !(swap && strikeDef.blockedWhileSwitching)) startStrike();

    if (input.pressed('reload')) startReload();
    if (autoReload > 0 && (autoReload -= dt) <= 0) {
      autoReload = 0;
      startReload();
    }

    if (swap) advanceSwitch(dt);
    if (reload) advanceReload(dt);
    if (strike) advanceStrike(dt, player);

    // Sprinting lowers the gun; wanting to use it brings it back up, a little faster.
    const wantsGun = busy() || input.down('fire') || input.down('ads');
    stepSpring(sprint, player.sprinting && !wantsGun ? 1 : 0, common.sprintRate * (wantsGun ? common.sprintHurry : 1), 1, dt);
    sprint.x = clamp01(sprint.x);

    setAim(player, input.down('ads') && !busy() && sprint.x < common.sprintAdsGate, dt);

    const s = def.spread;
    const cone =
      lerp(s.hip, s.ads, ads) +
      clamp01((player.speed || 0) / common.spreadSpeedRef) * lerp(s.moveHip, s.moveAds, ads) +
      bloom * lerp(s.bloomHip, s.bloomAds, ads) +
      (player.onGround === false ? s.air : 0) -
      (player.crouching ? s.crouch * (1 - ads) : 0);
    weapon.spread = damp(weapon.spread, Math.max(0, cone), common.spreadRate, dt);

    pullTrigger(input, player);
    probeWall(dt, player);
    assistAim(dt, input, player);
    sync();
  }

  reset();
  return weapon;
}
