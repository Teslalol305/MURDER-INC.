// The Goon: a masked gunman on foot. This file is his body in the world and his behaviour per mode
// (the mode machine itself, perception and the attack tokens are shared: see ../enemies.js).
//
//   patrol       wanders around his home point, pausing to look around
//   investigate  runs, then stalks, to the last known position and sweeps the area
//   engage       move → aim → telegraph → burst → (cool → telegraph → burst)? → new fire position …
//                and inside 3 m: wind-up → dash with the pipe → recovery
//
// Fire positions are scored candidates 8–18 m from the player (logic.js firePositionCost); authored
// cover points that still have a shot are preferred and he kneels there between bursts.
// He walks on the nav grid: string-pulled paths from physics.nav.findPath (budgeted in ../enemies.js),
// moved with physics.moveCapsule, kept apart from the others, with stuck detection.

import * as THREE from 'three';
import { angleDelta, moveToward, wrapAngle } from '../core/util.js';
import {
  createGoonAnim,
  kickFlinch,
  kickRecoil,
  OUT_BODY_HIGH,
  OUT_BODY_LOW,
  OUT_HEAD,
  OUT_LAMP,
  OUT_MUZZLE,
  poseCollapse,
  poseGoon,
  resetGoonAnim,
  startCollapse,
  startSwing,
  writeGoonParams,
} from './goon-anim.js';
import { buildGoonGeometry, createGoonMaterial, GOON_LAMP, SLOTS } from './goon-model.js';
import { aimSpread, firePositionCost, followSpeed, inFireBand } from './logic.js';
import { createRig } from './rig.js';

const GRAVITY = 20;
const MAX_CANDIDATES = 96;
const STEP_AUDIBLE = 45; // footsteps further than this from the player are not announced
const SEPARATION_PUSH = 2.2; // m/s at zero distance
const PLAYER_PUSH = 3;

export function createGoons(ctx) {
  const { G, cfg } = ctx;
  const nav = G.physics.nav;
  const geometries = [buildGoonGeometry(0), buildGoonGeometry(1), buildGoonGeometry(2)];
  const material = createGoonMaterial();

  // Scratch.
  const moved = { onGround: true, hitWall: false, hitCeil: false, surface: 'asphalt' };
  const goalVec = new THREE.Vector3();
  const from = new THREE.Vector3();
  const to = new THREE.Vector3();
  const shotDir = new THREE.Vector3();
  const candidates = Array.from({ length: MAX_CANDIDATES }, () => ({ x: 0, z: 0, kind: 'random', sight: false, cover: false }));
  const others = Array.from({ length: cfg.pool.goon }, () => ({ x: 0, z: 0, destX: 0, destZ: 0 }));

  function makeGoon(slot) {
    const rig = createRig(geometries[slot % 3], material, SLOTS);
    rig.mesh.name = `goon-${slot}`;
    rig.mesh.visible = false;
    ctx.root.add(rig.mesh);
    return {
      // ---- the contract (CONTRACT 6.6) ----
      id: 0,
      type: 'goon',
      pos: new THREE.Vector3(),
      alive: false,
      hp: 0,
      maxHp: 0,
      radius: cfg.goon.radius,
      height: cfg.goon.height,
      state: 'idle',
      object: rig.mesh,
      // ---- shared AI state ----
      active: false,
      slot,
      yaw: 0,
      vel: new THREE.Vector3(),
      mode: 'patrol',
      modeTime: 0,
      seen: 0,
      sees: false,
      sinceSeen: 0,
      senseIn: 0,
      exposure: 0,
      lastKnown: new THREE.Vector3(),
      home: new THREE.Vector3(),
      cooldown: 0,
      telegraph: 0,
      hasToken: false,
      passive: false,
      lastActive: 0,
      deadTime: 0,
      // ---- Goon ----
      rig,
      anim: createGoonAnim(),
      variant: slot % 3,
      sub: 'move', // engage sub-state
      subT: 0,
      path: [],
      pathIndex: 0,
      hasPath: false,
      needPath: false,
      pathFails: 0,
      hasGoal: false,
      arrived: false,
      goalX: 0,
      goalZ: 0,
      replanIn: 0,
      wantSpeed: 0,
      faceYaw: 0,
      facing: false, // turn to faceYaw when not walking a path
      turnScale: 1,
      moveSpeed: 0,
      stuck: 0,
      stuckCount: 0,
      travel: 0,
      wait: 0,
      onGround: true,
      surface: 'asphalt',
      hasFirePos: false,
      wantPick: false,
      pickAway: false, // the next fire position must be somewhere else
      atCover: false,
      goalFireX: 0,
      goalFireZ: 0,
      pickX: 0,
      pickZ: 0,
      bursts: 0,
      burstsToMove: 1,
      burstLeft: 0,
      burstTimer: 0,
      noSight: 0,
      waited: 0,
      tooClose: 0,
      rushCooldown: 0,
      rushHit: false,
      aimYaw: 0,
      sweep: 0,
      sweepBase: 0,
      scan: 0,
      dusted: false,
      bodyAge: 0,
      fading: false,
      show: null, // passive units only: a pose to hold (showcase scenes)
      // ---- what the pose solver reads ----
      speed: 0,
      yawRate: 0,
      wantCrouch: 0,
      wantAim: 0,
      aimYawRel: 0,
      aimPitch: 0,
      lookYawRel: 0,
      lookPitch: 0,
      rushPhase: 0,
      rushK: 0,
      lampWant: 0,
      // ---- world-space points, refreshed after every pose ----
      head: new THREE.Vector3(),
      muzzle: new THREE.Vector3(),
      lamp: new THREE.Vector3(),
      bodyLow: new THREE.Vector3(),
      bodyHigh: new THREE.Vector3(),
    };
  }

  const pool = Array.from({ length: cfg.pool.goon }, (_, i) => makeGoon(i));

  /* ------------------------------------------------------------------------------- transforms */

  function toWorld(e, out, offset, target) {
    const c = Math.cos(e.yaw);
    const s = Math.sin(e.yaw);
    const x = out[offset];
    const z = out[offset + 2];
    target.set(e.pos.x + x * c + z * s, e.pos.y + out[offset + 1], e.pos.z - x * s + z * c);
  }

  function place(e) {
    e.object.position.copy(e.pos);
    e.object.rotation.y = e.yaw;
    const out = e.anim.out;
    toWorld(e, out, OUT_HEAD, e.head);
    toWorld(e, out, OUT_MUZZLE, e.muzzle);
    toWorld(e, out, OUT_LAMP, e.lamp);
    toWorld(e, out, OUT_BODY_LOW, e.bodyLow);
    toWorld(e, out, OUT_BODY_HIGH, e.bodyHigh);
  }

  /* ------------------------------------------------------------------------------------ spawn */

  function spawn(e, pos, opts) {
    const t = ctx.tune.goon;
    e.pos.copy(pos);
    // On walkable ground, at the height of whatever he stands on.
    if (!nav.isWalkable(pos.x, pos.z)) {
      const near = nav.nearestWalkable(pos.x, pos.z, 4);
      if (near) e.pos.set(near.x, pos.y, near.z);
    }
    e.pos.y = G.physics.groundHeight(e.pos.x, e.pos.z, pos.y + 0.6);
    e.vel.set(0, 0, 0);
    e.home.copy(e.pos);
    e.yaw = opts.yaw !== undefined ? opts.yaw : ctx.random() * Math.PI * 2;
    e.aimYaw = e.yaw;
    e.cooldown = ctx.range(t.firstCooldown);
    const pickVariant = Math.floor(ctx.random() * 3) % 3; // drawn either way: the stream stays the same
    e.variant = opts.variant >= 0 && opts.variant < 3 ? opts.variant | 0 : pickVariant;
    e.object.geometry = geometries[e.variant];
    e.object.visible = true;
    e.object.castShadow = true;
    resetGoonAnim(e.anim, e.id);
    e.sub = 'move';
    e.subT = 0;
    e.hasPath = e.needPath = e.hasGoal = e.arrived = false;
    e.pathFails = 0;
    e.replanIn = ctx.range(t.replan);
    e.wantSpeed = e.moveSpeed = e.speed = e.yawRate = 0;
    e.facing = false;
    e.turnScale = 1;
    e.stuck = e.stuckCount = e.travel = 0;
    e.wait = ctx.random() * 1.5;
    e.onGround = true;
    e.hasFirePos = e.wantPick = e.pickAway = e.atCover = false;
    e.show = opts.show || null;
    e.bursts = e.burstLeft = 0;
    e.burstsToMove = 1;
    e.burstTimer = e.noSight = e.waited = e.tooClose = 0;
    e.rushCooldown = 0;
    e.rushHit = false;
    e.sweep = ctx.random() * 6;
    e.scan = ctx.random() * 6;
    e.dusted = false;
    e.bodyAge = 0;
    e.fading = false;
    e.wantCrouch = e.wantAim = e.aimYawRel = e.aimPitch = e.lookYawRel = e.lookPitch = 0;
    e.rushPhase = e.rushK = e.lampWant = 0;
    poseGoon(e, e.anim, 0, e.rig.matrices);
    e.rig.touch();
    place(e);
  }

  function retire(e) {
    e.object.visible = false;
    e.hasToken = false;
  }

  /* ---------------------------------------------------------------------------------- walking */

  function setGoal(e, x, z) {
    if (e.hasGoal && Math.abs(e.goalX - x) < 0.3 && Math.abs(e.goalZ - z) < 0.3) return;
    e.goalX = x;
    e.goalZ = z;
    e.hasGoal = true;
    e.needPath = true;
    e.arrived = false;
    e.pathFails = 0;
  }

  function clearGoal(e) {
    e.hasGoal = e.hasPath = e.needPath = e.arrived = false;
  }

  /** One budgeted nav query (called from ../enemies.js, at most a couple per frame over all Goons). */
  function plan(e) {
    goalVec.set(e.goalX, 0, e.goalZ);
    const path = nav.findPath(e.pos, goalVec, e.path);
    e.needPath = false;
    e.replanIn = ctx.range(ctx.tune.goon.replan);
    if (!path || path.length < 2) {
      e.hasPath = false;
      e.pathFails++;
      return;
    }
    e.hasPath = true;
    e.pathIndex = 1;
    e.pathFails = 0;
  }

  /**
   * Turns and moves the Goon for this frame: along his path at up to `e.wantSpeed`, or the dash of the
   * rush, with separation from the other Goons and the player, collision, and stuck detection.
   */
  function locomote(e, dt, t) {
    const dashing = e.sub === 'lunge' && e.mode === 'engage';
    const p = ctx.player;
    let targetSpeed = 0;
    let wantYaw = e.yaw;
    let turning = e.facing;
    if (turning) wantYaw = e.faceYaw;

    if (dashing) {
      targetSpeed = t.rush.speed;
      wantYaw = Math.atan2(e.pos.x - p.pos.x, e.pos.z - p.pos.z);
      turning = true;
    } else if (e.hasGoal && e.hasPath && !e.arrived && e.wantSpeed > 0) {
      const path = e.path;
      const last = path.length - 1;
      if (e.pathIndex > last) e.pathIndex = last;
      let wp = path[e.pathIndex];
      let dx = wp.x - e.pos.x;
      let dz = wp.z - e.pos.z;
      let d = Math.hypot(dx, dz);
      while (e.pathIndex < last && d < t.waypointReach) {
        e.pathIndex++;
        wp = path[e.pathIndex];
        dx = wp.x - e.pos.x;
        dz = wp.z - e.pos.z;
        d = Math.hypot(dx, dz);
      }
      if (e.pathIndex === last && d < t.goalReach) {
        e.arrived = true;
      } else {
        wantYaw = Math.atan2(-dx, -dz);
        turning = true;
        const error = Math.abs(angleDelta(e.yaw, wantYaw));
        targetSpeed = followSpeed(e.wantSpeed, error, e.pathIndex === last ? d : d + 2, t);
      }
    }

    // Body yaw.
    const before = e.yaw;
    if (turning) {
      const rate = (dashing ? t.turnRate * 2 : targetSpeed > 0 || e.moveSpeed > 0.3 ? t.pathTurnRate : t.turnRate) * e.turnScale;
      e.yaw = wrapAngle(e.yaw + moveToward(0, angleDelta(e.yaw, wantYaw), rate * dt));
    }
    e.yawRate = dt > 0 ? angleDelta(before, e.yaw) / dt : 0;

    // Speed along the facing.
    if (dashing) e.moveSpeed = targetSpeed;
    else e.moveSpeed = moveToward(e.moveSpeed, targetSpeed, (targetSpeed > e.moveSpeed ? t.accel : t.decel) * dt);
    let vx = -Math.sin(e.yaw) * e.moveSpeed;
    let vz = -Math.cos(e.yaw) * e.moveSpeed;

    // Keep apart: from the other Goons always, from the player unless this is the dash at him.
    const list = ctx.list;
    for (let i = 0; i < list.length; i++) {
      const o = list[i];
      if (o === e || o.type !== 'goon' || !o.alive) continue;
      const ox = e.pos.x - o.pos.x;
      const oz = e.pos.z - o.pos.z;
      const d2 = ox * ox + oz * oz;
      const reach = t.separation.goon;
      if (d2 >= reach * reach || Math.abs(e.pos.y - o.pos.y) > 1.5) continue;
      const d = Math.sqrt(d2);
      const push = (1 - d / reach) * SEPARATION_PUSH;
      if (d > 1e-3) {
        vx += (ox / d) * push;
        vz += (oz / d) * push;
      } else {
        // Exactly on top of each other: step apart by slot.
        vx += Math.cos(e.slot * 2.4) * push;
        vz += Math.sin(e.slot * 2.4) * push;
      }
    }
    if (!dashing && p.alive) {
      const ox = e.pos.x - p.pos.x;
      const oz = e.pos.z - p.pos.z;
      const d = Math.hypot(ox, oz);
      if (d < t.separation.player && d > 1e-3 && Math.abs(e.pos.y - p.pos.y) < 1.5) {
        const push = (1 - d / t.separation.player) * PLAYER_PUSH;
        vx += (ox / d) * push;
        vz += (oz / d) * push;
      }
    }

    e.vel.x = vx;
    e.vel.z = vz;
    e.vel.y = e.onGround ? 0 : e.vel.y - GRAVITY * dt;
    const px = e.pos.x;
    const pz = e.pos.z;
    G.physics.moveCapsule(e.pos, e.vel, dt, t.radius, t.height, e.onGround, moved);
    e.onGround = moved.onGround;
    e.surface = moved.surface;
    const step = Math.hypot(e.pos.x - px, e.pos.z - pz);
    e.speed = dt > 0 ? step / dt : 0;

    // Getting nowhere while trying to move: after a moment, make a new plan.
    if (e.moveSpeed > 0.6 && step < e.moveSpeed * dt * 0.3) e.stuck += dt;
    else e.stuck = Math.max(0, e.stuck - dt * 2);
    e.travel += step;
    if (e.travel > 0.5) {
      e.travel = 0;
      e.stuckCount = 0;
      e.lastActive = ctx.clock.now;
    }

    // Periodic check that the next waypoint is still straight ahead of us on the grid.
    if (e.hasGoal && !e.arrived && !dashing) {
      e.replanIn -= dt;
      if (e.replanIn <= 0) {
        e.replanIn = ctx.range(t.replan);
        if (!e.hasPath || !nav.clearLine(e.pos, e.path[Math.min(e.pathIndex, e.path.length - 1)])) e.needPath = true;
      }
    }
    return moved.hitWall;
  }

  /* ----------------------------------------------------------------------------- fire positions */

  /** Fills `others` with the other engaged Goons and returns how many. */
  function collectOthers(e) {
    let n = 0;
    const list = ctx.list;
    for (let i = 0; i < list.length && n < others.length; i++) {
      const o = list[i];
      if (o === e || o.type !== 'goon' || !o.alive || o.mode !== 'engage') continue;
      const rec = others[n++];
      rec.x = o.pos.x;
      rec.z = o.pos.z;
      rec.destX = o.hasFirePos ? o.goalFireX : o.pos.x;
      rec.destZ = o.hasFirePos ? o.goalFireZ : o.pos.z;
    }
    return n;
  }

  function addCandidate(n, x, z, kind, cover, e, t, p) {
    if (n >= MAX_CANDIDATES) return n;
    if (!inFireBand(Math.hypot(x - p.pos.x, z - p.pos.z), t) || !nav.isWalkable(x, z)) return n;
    // Relocating means going somewhere else.
    if (e.pickAway && Math.hypot(x - e.pos.x, z - e.pos.z) < t.repick.minMove) return n;
    const c = candidates[n];
    c.x = x;
    c.z = z;
    c.kind = kind;
    c.cover = cover;
    // Would a shot from here reach him? From gun height at the spot to his eye.
    from.set(x, e.pos.y + t.gunHeight, z);
    c.sight = G.physics.lineOfSight(from, p.eye);
    return n + 1;
  }

  /**
   * Chooses where to fight from (one of these per frame over all Goons: it casts a ray per candidate).
   * Candidates: the level's cover points, random walkable spots around the player, and an arc on the
   * Goon's own side of him. Returns false when there was nowhere to go.
   */
  function pickFirePosition(e) {
    const t = ctx.tune.goon;
    const p = ctx.player;
    const R = t.repick;
    let n = 0;
    const cover = (G.level && G.level.coverPoints) || [];
    for (let i = 0; i < cover.length; i++) {
      const c = cover[i].pos;
      if (Math.abs(c.y - e.pos.y) > t.cover.maxStep) continue;
      n = addCandidate(n, c.x, c.z, 'authored', true, e, t, p);
    }
    for (let i = 0; i < R.randomPoints; i++) {
      const angle = ctx.random() * Math.PI * 2;
      const r = t.rangeMin + (t.rangeMax - t.rangeMin) * Math.sqrt(ctx.random());
      n = addCandidate(n, p.pos.x + Math.cos(angle) * r, p.pos.z + Math.sin(angle) * r, 'random', false, e, t, p);
    }
    const side = Math.atan2(e.pos.x - p.pos.x, e.pos.z - p.pos.z);
    for (let i = 0; i < R.arcPoints; i++) {
      const angle = side + R.arc * ((i / (R.arcPoints - 1)) * 2 - 1) + (ctx.random() - 0.5) * 0.3;
      const r = ctx.range(R.arcRange);
      n = addCandidate(n, p.pos.x + Math.sin(angle) * r, p.pos.z + Math.cos(angle) * r, 'arc', false, e, t, p);
    }
    e.wantPick = false;
    e.pickAway = false;
    e.pickX = p.pos.x;
    e.pickZ = p.pos.z;
    e.bursts = 0;
    e.burstsToMove = ctx.random() < t.burstsBeforeMove.one ? 1 : 2;
    if (n === 0) return false;

    const count = collectOthers(e);
    let best = candidates[0];
    let bestCost = Infinity;
    for (let i = 0; i < n; i++) {
      const cost = firePositionCost(candidates[i], e.pos, p.pos, others, count, ctx.random(), t.positionCost);
      if (cost < bestCost) {
        bestCost = cost;
        best = candidates[i];
      }
    }
    e.hasFirePos = true;
    e.goalFireX = best.x;
    e.goalFireZ = best.z;
    e.atCover = best.cover && best.sight;
    return true;
  }

  /** Budgeted entry point for ../enemies.js: gives an engaged Goon that asked for one a new fire position. */
  function pick(e) {
    const t = ctx.tune.goon;
    const p = ctx.player;
    if (!pickFirePosition(e)) {
      // Nowhere in the band (the player is somewhere odd): close in on him, or hold and shoot.
      const d = Math.hypot(p.pos.x - e.pos.x, p.pos.z - e.pos.z);
      if (d <= t.rangeMax) {
        e.hasFirePos = false;
        if (e.sub === 'move') toAim(e);
        return;
      }
      const k = (d - (t.rangeMin + t.rangeMax) * 0.5) / d;
      e.goalFireX = e.pos.x + (p.pos.x - e.pos.x) * k;
      e.goalFireZ = e.pos.z + (p.pos.z - e.pos.z) * k;
      e.hasFirePos = true;
      e.atCover = false;
    }
    if (Math.hypot(e.goalFireX - e.pos.x, e.goalFireZ - e.pos.z) < 0.7) {
      if (e.sub === 'move') toAim(e);
      return;
    }
    if (e.sub === 'aim' || e.sub === 'cool' || e.sub === 'move') {
      e.sub = 'move';
      e.subT = 0;
      e.hasGoal = false;
      setGoal(e, e.goalFireX, e.goalFireZ);
    }
  }

  /* ----------------------------------------------------------------------------------- attacks */

  function toAim(e) {
    e.sub = 'aim';
    e.subT = 0;
    clearGoal(e);
    e.noSight = e.waited = e.tooClose = 0;
  }

  function relocate(e) {
    e.wantPick = true;
    e.pickAway = true;
    e.noSight = e.waited = e.tooClose = 0;
  }

  function fire(e, t) {
    const p = ctx.player;
    from.set(e.pos.x, e.pos.y + t.gunHeight, e.pos.z);
    to.set(p.pos.x, p.pos.y + (p.crouching ? Math.min(0.8, t.aimHeight) : t.aimHeight), p.pos.z);
    shotDir.subVectors(to, from).normalize();
    const spread = aimSpread(t.spreadFar, t.spreadNear, e.exposure, p.speed, t.spreadPerSpeed);
    shotDir.x += (ctx.random() * 2 - 1) * spread;
    shotDir.y += (ctx.random() * 2 - 1) * spread;
    shotDir.z += (ctx.random() * 2 - 1) * spread;
    shotDir.normalize();
    const hit = G.combat.hitscan({
      origin: from,
      dir: shotDir,
      range: t.shotRange,
      damage: t.shotDamage * ctx.scale.damage,
      from: e,
      weapon: 'goon',
    });
    ctx.fx.tracer(e.muzzle, hit.point, ctx.palette.tracer);
    ctx.fx.muzzleFlash(e.muzzle, shotDir, 0.7, true);
    if (e.burstLeft % 2 === 1) ctx.flash(e.muzzle, ctx.palette.muzzle, 14, 7, 0.05);
    ctx.emit('enemy:fire', { enemy: e, type: 'goon', pos: e.muzzle.clone(), dir: shotDir.clone() });
    kickRecoil(e.anim);
    e.lastActive = ctx.clock.now;
  }

  function startRush(e) {
    ctx.cancelAttack(e);
    e.sub = 'windup';
    e.subT = 0;
    e.rushHit = false;
    clearGoal(e);
    ctx.emit('enemy:melee', { enemy: e, phase: 'windup', pos: e.pos.clone() });
    e.lastActive = ctx.clock.now;
  }

  function swing(e) {
    if (e.anim.swing >= 0) return;
    startSwing(e.anim);
    ctx.emit('enemy:melee', { enemy: e, phase: 'strike', pos: e.pos.clone() });
  }

  /* ------------------------------------------------------------------------------------- modes */

  function patrol(e, dt, t) {
    e.scan += dt;
    e.lookYawRel = Math.sin(e.scan * 0.55) * 0.9;
    e.wantSpeed = t.patrolSpeed;
    if (e.wait > 0) {
      e.wait -= dt;
      e.wantSpeed = 0;
      return;
    }
    if (!e.hasGoal) {
      const point = nav.randomPoint(e.home, t.patrol.radius);
      if (point) setGoal(e, point.x, point.z);
      else e.wait = 1;
    } else if (e.arrived || e.pathFails > 1) {
      clearGoal(e);
      e.wait = ctx.range(t.patrol.wait);
    }
  }

  function investigate(e, dt, t) {
    const lk = e.lastKnown;
    const dx = lk.x - e.pos.x;
    const dz = lk.z - e.pos.z;
    const d = Math.hypot(dx, dz);
    const bearing = Math.atan2(-dx, -dz);
    const I = t.investigate;
    e.lookYawRel = angleDelta(e.yaw, bearing);
    if (d > I.stopWithin && !(e.arrived && Math.abs(e.goalX - lk.x) < 0.3 && Math.abs(e.goalZ - lk.z) < 0.3) && e.pathFails < 2) {
      setGoal(e, lk.x, lk.z);
      const stalking = d <= I.stalkWithin;
      e.wantSpeed = stalking ? t.stalkSpeed : t.runSpeed;
      if (stalking) {
        // Creeping in with the gun up.
        e.wantAim = 0.85;
        e.wantCrouch = 0.4;
        e.aimYaw = e.yaw;
      }
      e.sweep = 0;
      return;
    }
    // There: look the place over, gun up, sweeping left and right of the way he came in.
    e.wantSpeed = 0;
    if (e.sweep === 0) e.sweepBase = d > 0.5 ? bearing : e.yaw;
    e.sweep += dt;
    e.aimYaw = wrapAngle(e.sweepBase + Math.sin(e.sweep * 1.3) * I.sweep);
    e.facing = true;
    e.faceYaw = e.aimYaw; // the body follows the gun
    e.turnScale = 0.6;
    e.lookYawRel = angleDelta(e.yaw, e.aimYaw);
    e.wantAim = 0.85;
  }

  function engage(e, dt, t) {
    const p = ctx.player;
    const dx = p.pos.x - e.pos.x;
    const dz = p.pos.z - e.pos.z;
    const dist = Math.hypot(dx, dz);
    const bearing = Math.atan2(-dx, -dz);
    const hold = t.hold;
    const free = e.sub === 'move' || e.sub === 'aim' || e.sub === 'cool';
    e.lookYawRel = angleDelta(e.yaw, bearing);

    if (free) {
      // The rush: close, on the same level, off cooldown, and nothing solid in between.
      if (p.alive && e.rushCooldown <= 0 && dist < t.rush.range && Math.abs(p.pos.y - e.pos.y) < 1.4) {
        from.set(e.pos.x, e.pos.y + 1.2, e.pos.z);
        to.set(p.pos.x, p.pos.y + 1, p.pos.z);
        if (G.physics.lineOfSight(from, to)) {
          startRush(e);
          return;
        }
      }
      if (!e.hasFirePos && !e.wantPick && e.sub === 'move') e.wantPick = true;
      if (e.hasFirePos && Math.hypot(p.pos.x - e.pickX, p.pos.z - e.pickZ) > t.repick.playerMoved) e.wantPick = true;
    }

    switch (e.sub) {
      case 'move': {
        e.subT += dt;
        e.wantSpeed = t.runSpeed;
        e.aimYaw = e.yaw;
        if (e.arrived) toAim(e);
        else if (e.subT > t.move.giveUp) toAim(e);
        else if (
          e.subT > t.move.aimEarlyAfter &&
          e.sees &&
          dist >= t.move.aimEarlyRange[0] &&
          dist <= t.move.aimEarlyRange[1] &&
          ctx.random() < t.move.aimEarlyChance * dt
        ) {
          toAim(e);
        } else if (e.hasGoal && e.pathFails > 1) {
          // The spot cannot be reached after all.
          toAim(e);
          relocate(e);
        }
        break;
      }
      case 'aim':
      case 'cool': {
        e.subT += dt;
        e.wantSpeed = 0;
        e.facing = true;
        e.faceYaw = bearing;
        e.aimYaw = wrapAngle(e.aimYaw + moveToward(0, angleDelta(e.aimYaw, bearing), t.aimRate * dt));
        e.wantAim = 1;
        // Behind cover he kneels until the gun is nearly ready again.
        if (e.sub === 'cool' && e.atCover && t.cover.crouchBetweenBursts && e.cooldown > 0.4) {
          e.wantCrouch = 1;
          e.wantAim = 0.3;
        }
        if (e.sees) {
          e.noSight = 0;
          if (dist < hold.tooClose) {
            e.tooClose += dt;
            if (e.tooClose > hold.tooCloseTime) {
              relocate(e);
              e.tooClose = 0;
            }
          } else {
            e.tooClose = 0;
          }
          if (e.cooldown <= 0 && !e.wantPick) {
            if (Math.abs(angleDelta(e.aimYaw, bearing)) < hold.aimTolerance && ctx.requestToken(e)) {
              e.sub = 'telegraph';
              e.telegraph = t.telegraph;
              e.waited = 0;
              ctx.emit('enemy:telegraph', { enemy: e, type: 'goon', duration: t.telegraph, pos: e.pos.clone() });
            } else {
              e.waited += dt;
              if (e.waited > hold.maxWait) relocate(e);
            }
          }
        } else {
          e.noSight += dt;
          if (e.noSight > hold.noSightTime) {
            relocate(e);
            e.noSight = 0;
          }
        }
        break;
      }
      case 'telegraph': {
        e.wantSpeed = 0;
        e.facing = true;
        e.faceYaw = bearing;
        e.aimYaw = wrapAngle(e.aimYaw + moveToward(0, angleDelta(e.aimYaw, bearing), t.aimRate * dt));
        e.wantAim = 1;
        e.telegraph -= dt;
        const k = 1 - Math.max(0, e.telegraph) / t.telegraph;
        e.lampWant = 1.5 + 14 * k * k;
        if (e.telegraph <= 0) {
          e.sub = 'burst';
          e.burstLeft = t.burst;
          e.burstTimer = 0;
        }
        break;
      }
      case 'burst': {
        e.wantSpeed = 0;
        e.facing = true;
        e.faceYaw = bearing;
        e.aimYaw = wrapAngle(e.aimYaw + moveToward(0, angleDelta(e.aimYaw, bearing), t.aimRate * dt));
        e.wantAim = 1;
        e.lampWant = 6;
        e.burstTimer -= dt;
        while (e.burstLeft > 0 && e.burstTimer <= 0) {
          fire(e, t);
          e.burstLeft--;
          e.burstTimer += t.burstGap;
        }
        if (e.burstLeft === 0) {
          ctx.releaseToken(e);
          e.cooldown = ctx.range(t.cooldown) * ctx.scale.cooldown;
          e.bursts++;
          e.waited = e.noSight = 0;
          e.sub = 'cool';
          e.subT = 0;
          if (e.bursts >= e.burstsToMove) relocate(e);
        }
        break;
      }
      case 'windup': {
        e.subT += dt;
        e.wantSpeed = 0;
        e.facing = true;
        e.faceYaw = bearing;
        e.turnScale = 3;
        e.rushPhase = 1;
        e.rushK = Math.min(1, e.subT / t.rush.windup);
        if (e.subT >= t.rush.windup) {
          e.sub = 'lunge';
          e.subT = 0;
          e.yaw = bearing; // snaps round to face him, then goes
        }
        break;
      }
      case 'lunge': {
        e.subT += dt;
        e.rushPhase = 2;
        e.rushK = Math.min(1, e.subT / t.rush.time);
        if (!e.rushHit && p.alive && dist < t.rush.reach && Math.abs(p.pos.y - e.pos.y) < 1.3) {
          e.rushHit = true;
          swing(e);
          from.set(e.pos.x, e.pos.y + 1.3, e.pos.z);
          G.player.damage(t.rushDamage * ctx.scale.damage, from.clone(), 'melee');
          e.sub = 'recover';
          e.subT = 0;
        } else {
          if (e.subT > t.rush.time * 0.6) swing(e);
          // Out of time, or the dash ran into something solid.
          if (e.subT >= t.rush.time || (e.subT > 0.08 && e.speed < t.rush.speed * 0.3)) {
            swing(e);
            e.sub = 'recover';
            e.subT = 0;
          }
        }
        e.lastActive = ctx.clock.now;
        break;
      }
      case 'recover': {
        e.subT += dt;
        e.wantSpeed = 0;
        e.moveSpeed = moveToward(e.moveSpeed, 0, 40 * dt);
        e.rushPhase = 3;
        e.rushK = Math.min(1, e.subT / t.rush.recovery);
        if (e.subT >= t.rush.recovery) {
          e.rushCooldown = t.rush.cooldown;
          e.sub = 'aim';
          e.subT = 0;
          e.aimYaw = e.yaw;
          relocate(e);
        }
        break;
      }
      default:
        e.sub = 'aim';
    }
  }

  /* ------------------------------------------------------------------------------------ update */

  function update(e, dt) {
    const t = ctx.tune.goon;
    const p = ctx.player;
    if (e.sub !== 'telegraph' && e.sub !== 'burst') e.cooldown -= dt;
    e.rushCooldown -= dt;
    e.wantCrouch = 0;
    e.wantAim = 0;
    e.lampWant = 0;
    e.rushPhase = 0;
    e.wantSpeed = 0;
    e.facing = false;
    e.turnScale = 1;
    e.lookPitch = 0;

    if (e.passive) {
      e.scan += dt;
      e.lookYawRel = Math.sin(e.scan * 0.55) * 0.7;
      if (e.show) {
        // Showcase: hold the pose that was asked for.
        e.wantAim = e.show.aim || 0;
        e.wantCrouch = e.show.crouch || 0;
        e.lampWant = e.show.lamp || 0;
        e.lookYawRel = e.show.look || 0;
        e.aimYaw = e.yaw + (e.show.aimYaw || 0);
      }
    } else if (e.mode === 'engage') engage(e, dt, t);
    else if (e.mode === 'patrol') patrol(e, dt, t);
    else investigate(e, dt, t);

    locomote(e, dt, t);
    if (e.passive && e.show) e.speed = e.show.speed || 0;
    if (e.stuck > t.stuckTime) {
      e.stuck = 0;
      e.stuckCount++;
      // A new plan: another fire position, another patrol point, another route.
      if (e.mode === 'engage') {
        if (e.sub === 'move') relocate(e);
      } else if (e.mode === 'patrol') {
        clearGoal(e);
        e.wait = 0.5;
      } else if (e.stuckCount > 2) {
        e.arrived = true;
      } else {
        e.needPath = true;
      }
    }

    // What the pose needs to know about the target.
    e.aimYawRel = angleDelta(e.yaw, e.aimYaw);
    if (e.mode === 'engage' && p.alive) {
      const d = Math.hypot(p.pos.x - e.pos.x, p.pos.z - e.pos.z);
      e.aimPitch = Math.atan2(p.pos.y + t.aimHeight - (e.pos.y + t.gunHeight), Math.max(d, 0.5));
      e.lookPitch = Math.atan2(p.eye.y - (e.pos.y + t.eyeHeight), Math.max(d, 0.5));
    } else {
      e.aimPitch = 0;
    }
    poseGoon(e, e.anim, dt, e.rig.matrices);
    e.rig.touch();
    place(e);

    if (e.anim.step !== 0 && e.onGround) {
      const dx = p.pos.x - e.pos.x;
      const dz = p.pos.z - e.pos.z;
      if (dx * dx + dz * dz < STEP_AUDIBLE * STEP_AUDIBLE) ctx.emit('enemy:step', { enemy: e, pos: e.pos.clone(), surface: e.surface });
    }
  }

  /** A hit that did not kill: the body flinches along the shot (cosmetic only). */
  function onHit(e, amount, info) {
    const t = ctx.tune.goon;
    let dx = 0;
    let dz = 0;
    if (info.dir) {
      // World direction → model space (inverse of the body yaw).
      const c = Math.cos(e.yaw);
      const s = Math.sin(e.yaw);
      dx = info.dir.x * c - info.dir.z * s;
      dz = info.dir.x * s + info.dir.z * c;
    }
    const strength = Math.min(t.staggerMax, amount / 28) * (info.part === 'head' ? 1.5 : 1);
    kickFlinch(e.anim, dx, dz, strength);
  }

  function onKilled(e, info) {
    let dx = 0;
    let dz = 1;
    if (info.dir) {
      const c = Math.cos(e.yaw);
      const s = Math.sin(e.yaw);
      dx = info.dir.x * c - info.dir.z * s;
      dz = info.dir.x * s + info.dir.z * c;
    }
    kickFlinch(e.anim, dx, dz, 0.6);
    startCollapse(e.anim, dx, dz);
    e.dusted = false;
    e.moveSpeed = e.speed = 0;
    e.lampWant = 0;
  }

  /** The collapse. Returns true when the body has come to rest. */
  function updateDying(e, dt) {
    const t = ctx.tune.goon;
    const done = poseCollapse(e.anim, dt, e.rig.matrices, t.collapse);
    e.rig.touch();
    if (!e.dusted && e.deadTime > t.collapse * 0.7) {
      e.dusted = true;
      ctx.fx.dust(e.pos, 0.8);
    }
    return done;
  }

  /** A body lying on the street: fades out when told to, or after a while. Returns true when it is gone. */
  function updateBody(e, dt) {
    const t = ctx.tune.goon;
    e.bodyAge += dt;
    if (!e.fading && e.bodyAge > t.bodyStay) startFade(e);
    if (!e.fading) return false;
    e.anim.fade = Math.min(1, e.anim.fade + dt / t.bodyFade);
    writeGoonParams(e.anim, e.rig.matrices);
    e.rig.touch();
    return e.anim.fade >= 1;
  }

  function startFade(e) {
    e.fading = true;
    e.object.castShadow = false; // the dither does not reach the shadow pass
  }

  /** Where he sees from: standing eye height on the body axis, also while he kneels behind cover. */
  function sensor(e, out) {
    return out.set(e.pos.x, e.pos.y + ctx.tune.goon.eyeHeight, e.pos.z);
  }

  /** The weapon light: a flare that grows through the telegraph. */
  function drawGlow(e, glow) {
    const lamp = e.anim.lamp;
    if (lamp < 0.05 || !e.alive) return;
    const k = Math.min(1, lamp / 15);
    const size = 0.1 + 0.55 * Math.sqrt(k);
    const level = lamp * 0.9;
    glow.flare(e.lamp.x, e.lamp.y, e.lamp.z, size, GOON_LAMP.r * level, GOON_LAMP.g * level, GOON_LAMP.b * level);
  }

  return {
    pool,
    material,
    spawn,
    retire,
    update,
    updateDying,
    updateBody,
    startFade,
    onHit,
    onKilled,
    plan,
    pick,
    sensor,
    drawGlow,
    /** Leaving engage (lost the player, died): drop whatever the engage state machine was doing. */
    onLeaveEngage(e) {
      e.sub = 'move';
      e.subT = 0;
      e.hasFirePos = false;
      e.wantPick = false;
      e.burstLeft = 0;
      clearGoal(e);
    },
    onEngage(e) {
      e.sub = 'move';
      e.subT = 0;
      e.hasFirePos = false;
      e.wantPick = true;
      e.bursts = 0;
      e.aimYaw = e.yaw;
      clearGoal(e);
    },
    onInvestigate(e) {
      e.sweep = 0;
      e.stuckCount = 0;
      e.pathFails = 0;
      if (e.wait > 0) e.wait = 0;
    },
    onPatrol(e) {
      clearGoal(e);
      e.wait = ctx.range(ctx.tune.goon.patrol.wait) * 0.5;
    },
  };
}
