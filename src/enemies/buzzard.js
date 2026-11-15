// The Buzzard: the armed quadcopter. A free-flying body with velocity, steered toward a target point
// that depends on the mode (the mode machine, perception and attack tokens are shared: ../enemies.js).
//
//   patrol       slow circle around its home point at spawn height
//   investigate  tight circle over the last known position
//   engage       orbits the player at its own radius and height, steadying to shoot; flies to the
//                last known position when it loses sight
//
// No pathfinding: it climbs over whatever stands on the leg ahead (logic.js climbOver), one ray feeler
// per frame (ahead, down, up in rotation) nudges it around things, the flight plan around the El keeps
// it under or beside the track deck (logic.js planAroundDeck), collision rays along its motion stop it
// at any surface it still reaches, and an airframe that ends a step overlapping something is put back
// into free air (logic.js pushOut).
// Attack: a telegraphed burst of slow tracer bolts with partial lead. Death: it spins down trailing
// smoke and bursts where it lands.

import * as THREE from 'three';
import { angleDelta, clamp, damp, moveToward, wrapAngle } from '../core/util.js';
import {
  BUZZARD_LAMP,
  buildBuzzardGeometry,
  BZ_SLOTS,
  createBuzzardAnim,
  createBuzzardMaterial,
  OUT_BOLT,
  OUT_EYE,
  poseBuzzard,
  resetBuzzardAnim,
  ROTOR_RADIUS,
  ROTORS,
  STROBES,
} from './buzzard-model.js';
import { aimSpread, climbHit, climbOver, deckEntry, deckSlide, inRoom, isPole, leadPoint, planAroundDeck, pushOut, routeIndoors } from './logic.js';
import { createRig, m3Euler } from './rig.js';

const UP = new THREE.Vector3(0, 1, 0);
const DOWN = new THREE.Vector3(0, -1, 0);
const TILT_PER_ACCEL = 0.034; // radians of bank per m/s²
const MAX_TILT = 0.5;
const STROBE_PERIOD = 1.3;
const POLE_STEP = 2; // m/s sideways off a pole it was coming down onto
const ROOM_MARGIN = 1.5; // an orbit indoors keeps this far inside the walls
const MOVEMENT = { movement: true }; // physics.lineOfSight: nothing that blocks a body in between

export function createBuzzards(ctx) {
  const { G, cfg } = ctx;
  const geometry = buildBuzzardGeometry();
  const material = createBuzzardMaterial();

  // Scratch.
  const want = [0, 0, 0];
  const aimAt = [0, 0, 0];
  const origin = new THREE.Vector3();
  const to = new THREE.Vector3();
  const dir = new THREE.Vector3();
  const boltDir = new THREE.Vector3();
  const hit = { dist: 0, point: new THREE.Vector3(), normal: new THREE.Vector3(), surface: null, box: null };
  const rot = new Float64Array(9);

  function makeBuzzard(slot) {
    const rig = createRig(geometry, material, BZ_SLOTS);
    rig.mesh.name = `buzzard-${slot}`;
    rig.mesh.visible = false;
    ctx.root.add(rig.mesh);
    return {
      // ---- the contract (CONTRACT 6.6) ----
      id: 0,
      type: 'buzzard',
      pos: new THREE.Vector3(),
      alive: false,
      hp: 0,
      maxHp: 0,
      radius: cfg.buzzard.radius,
      height: cfg.buzzard.halfHeight * 2,
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
      // ---- Buzzard ----
      rig,
      anim: createBuzzardAnim(),
      altitude: 6, // personal height above the player while engaged
      orbitRadius: 18,
      orbitAngle: 0,
      orbitDir: 1,
      patrolRadius: 6,
      rethinkIn: 5,
      flipIn: 0,
      push: new THREE.Vector3(), // what the feelers ask for, fading
      stuckX: 0, // where it was when it last got anywhere, and for how long it has not (detour)
      stuckY: 0,
      stuckZ: 0,
      stuckT: 0,
      detourIn: 0,
      detourX: 0,
      detourY: 0,
      detourZ: 0,
      ceiling: Infinity,
      ceilingAge: 0,
      feeler: 0,
      pitch: 0,
      roll: 0,
      kickPitch: 0,
      kickRoll: 0,
      wobble: 0,
      lead: 0.5,
      burstLeft: 0,
      burstTimer: 0,
      smokeIn: 0,
      sparkIn: 0,
      spin: 0,
      strobe: 0,
      // ---- what the pose reads ----
      rotorWant: 1,
      eyeYawWant: 0,
      eyePitchWant: 0,
      lampWant: 0,
      // ---- world-space points ----
      eye: new THREE.Vector3(),
      gun: new THREE.Vector3(),
    };
  }

  const pool = Array.from({ length: cfg.pool.buzzard }, (_, i) => makeBuzzard(i));

  /* ------------------------------------------------------------------------------------ indoors */

  // The level's interiors (level.interiorBoxes: the shop) and their doorways, found once, the first time a
  // drone needs them, by casting rays in through the walls: a run of at least DOOR_WIDTH metres where both
  // a low and a high ray pass, tall enough for an airframe.
  const DOOR_WIDTH = 2;
  const DOOR_RAYS = [2.4, 3.2];
  let rooms = null;

  function wallClear(x, y, z, dx, dz) {
    origin.set(x, y, z);
    dir.set(dx, 0, dz);
    return !G.physics.raycast(origin, dir, 3.2, hit);
  }

  function findRooms() {
    rooms = [];
    const list = (G.level && G.level.interiorBoxes) || [];
    for (let k = 0; k < list.length; k++) {
      const box = list[k];
      const room = { box, list: [] };
      // The four walls: along x (normal ±z) and along z (normal ±x).
      for (let w = 0; w < 4; w++) {
        const alongX = w < 2;
        const sign = w % 2 === 0 ? 1 : -1;
        const wall = alongX ? (sign > 0 ? box.max.z : box.min.z) : sign > 0 ? box.max.x : box.min.x;
        const a0 = (alongX ? box.min.x : box.min.z) + 0.6;
        const a1 = (alongX ? box.max.x : box.max.z) - 0.6;
        let run = 0;
        for (let a = a0; a <= a1 + 0.25; a += 0.5) {
          const out = wall + sign * 1.5;
          let clear = a <= a1;
          for (let r = 0; clear && r < DOOR_RAYS.length; r++) {
            clear = alongX ? wallClear(a, DOOR_RAYS[r], out, 0, -sign) : wallClear(out, DOOR_RAYS[r], a, -sign, 0);
          }
          if (clear) {
            run++;
            continue;
          }
          if (run * 0.5 >= DOOR_WIDTH) {
            const c = a - 0.25 * (run + 1); // centre of the run (the samples a - 0.5, a - 1, …)
            let top = DOOR_RAYS[DOOR_RAYS.length - 1];
            while (top < box.max.y && (alongX ? wallClear(c, top + 0.2, out, 0, -sign) : wallClear(out, top + 0.2, c, -sign, 0))) top += 0.2;
            const y = Math.max(DOOR_RAYS[0], top - 0.6);
            const o = wall + sign * 2.5;
            const i = wall - sign * 2.5;
            room.list.push(alongX ? { ox: c, oz: o, ix: c, iz: i, y } : { ox: o, oz: c, ix: i, iz: c, y });
          }
          run = 0;
        }
      }
      rooms.push(room);
    }
  }

  /** Airframe rotation as a row-major 3 × 3 in `rot`, and the eye and muzzle in world space. */
  function place(e) {
    e.object.position.copy(e.pos);
    e.object.rotation.set(e.pitch, e.yaw, e.roll);
    m3Euler(rot, 0, e.pitch, e.yaw, e.roll);
    const out = e.anim.out;
    for (let k = 0; k < 2; k++) {
      const o = k === 0 ? OUT_EYE : OUT_BOLT;
      const x = out[o];
      const y = out[o + 1];
      const z = out[o + 2];
      (k === 0 ? e.eye : e.gun).set(
        e.pos.x + rot[0] * x + rot[1] * y + rot[2] * z,
        e.pos.y + rot[3] * x + rot[4] * y + rot[5] * z,
        e.pos.z + rot[6] * x + rot[7] * y + rot[8] * z,
      );
    }
  }

  function spawn(e, pos, opts) {
    const t = ctx.tune.buzzard;
    e.pos.copy(pos);
    // Asked for at street level: come in at a sensible height instead.
    const ground = G.physics.groundHeight(pos.x, pos.z, pos.y + 0.5);
    if (e.pos.y < ground + t.minHeight) e.pos.y = ground + 5 + ctx.random() * 0.6;
    const el = G.level && G.level.el;
    if (el && pos.x > el.minX && pos.x < el.maxX && pos.z > el.minZ - 1 && pos.z < el.maxZ + 1 && e.pos.y > el.y - t.deck.under && e.pos.y < el.y + t.deck.thickness + 1) {
      e.pos.y = el.y - t.deck.under; // never inside the track deck
    }
    e.vel.set(0, 0, 0);
    pushOut(G.physics.boxes, e.pos, e.vel, t, G.physics.bounds);
    e.home.copy(e.pos);
    e.yaw = opts.yaw !== undefined ? opts.yaw : ctx.random() * Math.PI * 2;
    e.cooldown = ctx.range(t.firstCooldown);
    e.altitude = ctx.range(t.orbit.altitude);
    e.orbitRadius = ctx.range(t.orbit.radius);
    e.orbitAngle = ctx.random() * Math.PI * 2;
    e.orbitDir = ctx.random() < 0.5 ? -1 : 1;
    e.patrolRadius = ctx.range(t.patrol.radius);
    e.rethinkIn = ctx.range(t.orbit.rethink);
    e.flipIn = 0;
    e.push.set(0, 0, 0);
    e.stuckX = e.pos.x;
    e.stuckY = e.pos.y;
    e.stuckZ = e.pos.z;
    e.stuckT = e.detourIn = 0;
    e.ceiling = Infinity;
    e.ceilingAge = 0;
    e.feeler = e.slot % 3;
    e.pitch = e.roll = e.kickPitch = e.kickRoll = 0;
    e.wobble = ctx.random() * 10;
    e.burstLeft = 0;
    e.burstTimer = 0;
    e.smokeIn = e.sparkIn = 0;
    e.spin = 0;
    e.strobe = ctx.random() * STROBE_PERIOD;
    e.rotorWant = 1;
    e.eyeYawWant = e.eyePitchWant = 0;
    e.lampWant = 0.6;
    resetBuzzardAnim(e.anim, e.id);
    e.object.visible = true;
    poseBuzzard(e, e.anim, 0, e.rig.matrices);
    e.rig.touch();
    place(e);
  }

  function retire(e) {
    e.object.visible = false;
    e.hasToken = false;
  }

  /* ------------------------------------------------------------------------------------ flight */

  /** Fills `want` with the point this mode steers for; returns the speed cap. */
  function target(e, dt, t) {
    const p = ctx.player;
    if (e.mode === 'engage') {
      if (e.sinceSeen > t.orbit.lostAfter) {
        // Lost him: go and look where he was.
        want[0] = e.lastKnown.x;
        want[1] = e.lastKnown.y + e.altitude + 1;
        want[2] = e.lastKnown.z;
        return t.maxSpeed;
      }
      const steady = e.telegraph > 0 || e.burstLeft > 0;
      e.orbitAngle += (e.orbitDir * (steady ? t.orbit.speedFiring : t.orbit.speed) * dt) / e.orbitRadius;
      e.rethinkIn -= dt;
      if (e.rethinkIn <= 0) {
        e.rethinkIn = ctx.range(t.orbit.rethink);
        if (ctx.random() < t.orbit.reverseChance) e.orbitDir = -e.orbitDir;
        e.orbitRadius = clamp(e.orbitRadius + (ctx.random() * 2 - 1) * t.orbit.radiusDrift, t.orbit.radiusClamp[0], t.orbit.radiusClamp[1]);
      }
      want[0] = p.pos.x + Math.cos(e.orbitAngle) * e.orbitRadius;
      want[1] = p.pos.y + e.altitude;
      want[2] = p.pos.z + Math.sin(e.orbitAngle) * e.orbitRadius;
      // Indoors with him: the orbit stays inside the walls (the ceiling feeler keeps it under the roof).
      for (let k = 0; k < rooms.length; k++) {
        const b = rooms[k].box;
        if (!inRoom(b, p.pos, 0, true) || !inRoom(b, e.pos, 0, true)) continue;
        want[0] = clamp(want[0], b.min.x + ROOM_MARGIN, b.max.x - ROOM_MARGIN);
        want[2] = clamp(want[2], b.min.z + ROOM_MARGIN, b.max.z - ROOM_MARGIN);
      }
      return t.maxSpeed;
    }
    if (e.mode === 'patrol') {
      e.orbitAngle += e.orbitDir * t.patrol.turn * dt;
      want[0] = e.home.x + Math.cos(e.orbitAngle) * e.patrolRadius;
      want[1] = e.home.y;
      want[2] = e.home.z + Math.sin(e.orbitAngle) * e.patrolRadius;
      return t.patrolSpeed;
    }
    e.orbitAngle += e.orbitDir * t.investigate.turn * dt;
    want[0] = e.lastKnown.x + Math.cos(e.orbitAngle) * t.investigate.radius;
    want[1] = e.lastKnown.y + Math.min(e.altitude, t.investigate.maxHeight);
    want[2] = e.lastKnown.z + Math.sin(e.orbitAngle) * t.investigate.radius;
    return t.investigateSpeed;
  }

  /** One ray per frame, in rotation: ahead, down, up. What they find becomes a push that fades. */
  function feel(e, t, speed) {
    const F = t.feelers;
    e.feeler = (e.feeler + 1) % 3;
    if (e.feeler === 0) {
      if (speed < 0.3) return;
      dir.set(e.vel.x / speed, e.vel.y / speed, e.vel.z / speed);
      const reach = F.forward + F.forwardPerSpeed * speed;
      if (!G.physics.raycast(e.pos, dir, reach, hit)) return;
      // Away from the surface, and up and over it.
      const k = (1 - hit.dist / reach) * t.accel * 1.6;
      e.push.x += hit.normal.x * k;
      e.push.y += hit.normal.y * k + k * 0.5;
      e.push.z += hit.normal.z * k;
      if (hit.dist < reach * 0.5 && e.flipIn <= 0) {
        e.orbitDir = -e.orbitDir;
        e.flipIn = 1.2;
      }
    } else if (e.feeler === 1) {
      if (G.physics.raycast(e.pos, DOWN, F.down, hit)) e.push.y += (1 - hit.dist / F.down) * t.accel * 1.5;
    } else if (G.physics.raycast(e.pos, UP, F.up, hit)) {
      e.ceiling = hit.point.y;
      e.ceilingAge = 0;
    } else if (e.ceilingAge > 0.5) {
      e.ceiling = Infinity;
    }
  }

  /**
   * Moves along one axis with a collision ray: stops `clear` short of whatever is in the way and bounces.
   * axis 0 = x, 1 = y, 2 = z. Returns whether it was stopped (then `hit` says by what).
   */
  function slide(e, axis, dt, clear, bounce) {
    const v = axis === 0 ? e.vel.x : axis === 1 ? e.vel.y : e.vel.z;
    if (v === 0) return false;
    const sign = v > 0 ? 1 : -1;
    dir.set(axis === 0 ? sign : 0, axis === 1 ? sign : 0, axis === 2 ? sign : 0);
    const travel = Math.abs(v) * dt;
    let move = travel;
    let stopped = false;
    if (G.physics.raycast(e.pos, dir, travel + clear, hit)) {
      move = Math.max(0, hit.dist - clear);
      if (move < travel) {
        stopped = true;
        if (axis === 0) e.vel.x = v * bounce;
        else if (axis === 1) e.vel.y = v * bounce;
        else e.vel.z = v * bounce;
      } else {
        move = travel;
      }
    }
    if (axis === 0) e.pos.x += sign * move;
    else if (axis === 1) e.pos.y += sign * move;
    else e.pos.z += sign * move;
    return stopped;
  }

  /**
   * The last resort: a drone that has not got anywhere for a while although it wants to (wedged between
   * a lamp post and a wall, say, where none of the rules above sees the trap) flies off a few metres in
   * a direction that is clear, and a little up, then carries on. Rewrites `want` while it lasts.
   */
  function detour(e, dt, t) {
    const D = t.detour;
    if (e.detourIn > 0) {
      e.detourIn -= dt;
      want[0] = e.detourX;
      want[1] = e.detourY;
      want[2] = e.detourZ;
      return;
    }
    const far = Math.abs(want[0] - e.pos.x) + Math.abs(want[1] - e.pos.y) + Math.abs(want[2] - e.pos.z) > D.far;
    const dx = e.pos.x - e.stuckX;
    const dy = e.pos.y - e.stuckY;
    const dz = e.pos.z - e.stuckZ;
    if (!far || dx * dx + dy * dy + dz * dz > D.moved * D.moved) {
      e.stuckX = e.pos.x;
      e.stuckY = e.pos.y;
      e.stuckZ = e.pos.z;
      e.stuckT = 0;
      return;
    }
    e.stuckT += dt;
    if (e.stuckT < D.after) return;
    e.stuckT = 0;
    // A clear way out: a few random directions, the first that nothing solid blocks (to the eye or a body).
    const up = Math.min(t.maxAltitude, e.ceiling - t.ceilingClearance, e.pos.y + D.up);
    for (let k = 0; k < 6; k++) {
      const a = ctx.random() * Math.PI * 2;
      to.set(e.pos.x + Math.cos(a) * D.distance, Math.max(e.pos.y, up), e.pos.z + Math.sin(a) * D.distance);
      if (k < 5 && !G.physics.lineOfSight(e.pos, to, MOVEMENT)) continue;
      e.detourX = to.x;
      e.detourY = to.y;
      e.detourZ = to.z;
      e.detourIn = D.time;
      return;
    }
  }

  function fly(e, dt, t) {
    if (!rooms) findRooms();
    const cap = target(e, dt, t);
    // Wanted inside the shop from out here: in through a doorway, not down onto the roof.
    let indoors = 0;
    for (let k = 0; k < rooms.length && !indoors; k++) indoors = routeIndoors(e.pos, want, rooms[k]);
    const damaged = e.hp < e.maxHp * t.damagedBelow;
    const el = G.level && G.level.el;

    // Height limits: off the ground, under any ceiling it has seen, never through the track deck, and
    // over the roofs on the way. The climb comes after the deck plan: a drone that must drop under the
    // deck beyond a building first goes over the building (the plan then holds it outside the deck's
    // footprint until it is low enough), but one already under the deck never climbs into it.
    const ground = G.physics.groundHeight(e.pos.x, e.pos.z, e.pos.y + 0.3);
    e.ceilingAge += dt;
    const top = Math.min(t.maxAltitude, e.ceiling - t.ceilingClearance);
    want[1] = Math.min(Math.max(want[1], ground + t.minHeight), top);
    const plan = planAroundDeck(e.pos.x, e.pos.y, e.pos.z, want, el, t.deck);
    const dm = t.deck.margin;
    const underDeck = el && e.pos.y < el.y && e.pos.x > el.minX - dm && e.pos.x < el.maxX + dm && e.pos.z > el.minZ - dm && e.pos.z < el.maxZ + dm;
    if (!underDeck) {
      climbOver(G.physics.boxes, e.pos, want, t, el);
      // Sent under the deck and already at its edge, but something tall is in the way in or right under
      // the hold: go straight across the edge, else slide along it until there is room to come down
      // (logic.js deckEntry). Further out, climbing over what is in the way is the right answer.
      if ((plan === 1 || plan === 3) && el) {
        const ox = e.pos.x < el.minX - dm ? el.minX - dm - e.pos.x : e.pos.x > el.maxX + dm ? e.pos.x - el.maxX - dm : 0;
        const oz = e.pos.z < el.minZ - dm ? el.minZ - dm - e.pos.z : e.pos.z > el.maxZ + dm ? e.pos.z - el.maxZ - dm : 0;
        const free = el.y - t.deck.under + 0.6;
        if (ox * ox + oz * oz <= (t.deck.hold + 1) * (t.deck.hold + 1) && want[1] > free) {
          if (plan === 1) {
            deckEntry(e.pos, want, el, t.deck);
            climbOver(G.physics.boxes, e.pos, want, t, el);
          }
          if (want[1] > free && climbHit.box) deckSlide(e.pos, want, climbHit.box, t.deck);
        }
      }
      if (want[1] > top) want[1] = top;
    }
    detour(e, dt, t);

    // A damped pull toward the point, plus what the feelers ask for.
    const H = t.pull.horizontal;
    const Vp = t.pull.vertical;
    let ax = H[0] * (want[0] - e.pos.x) - H[1] * e.vel.x + e.push.x;
    let ay = Vp[0] * (want[1] - e.pos.y) - Vp[1] * e.vel.y + e.push.y;
    let az = H[0] * (want[2] - e.pos.z) - H[1] * e.vel.z + e.push.z;
    if (damaged) {
      e.wobble += dt;
      ax += Math.sin(e.wobble * 5.3) * t.damagedJitter;
      ay += Math.sin(e.wobble * 7.1 + 1) * t.damagedJitter * 0.7;
      az += Math.cos(e.wobble * 4.7) * t.damagedJitter;
    }
    const a = Math.hypot(ax, ay, az);
    if (a > t.accel) {
      const k = t.accel / a;
      ax *= k;
      ay *= k;
      az *= k;
    }
    e.vel.x += ax * dt;
    e.vel.y += ay * dt;
    e.vel.z += az * dt;
    let speed = Math.hypot(e.vel.x, e.vel.y, e.vel.z);
    if (speed > cap) {
      e.vel.multiplyScalar(cap / speed);
      speed = cap;
    }
    const fade = Math.exp(-6 * dt);
    e.push.multiplyScalar(fade);
    e.flipIn -= dt;
    feel(e, t, speed);

    // Move, one axis at a time, never closer to a surface than its own size.
    const bounce = t.feelers.bounce;
    const px = e.pos.x;
    const py = e.pos.y;
    const pz = e.pos.z;
    slide(e, 0, dt, t.radius + 0.1, bounce);
    slide(e, 2, dt, t.radius + 0.1, bounce);
    if (slide(e, 1, dt, t.halfHeight + 0.2, bounce) && e.vel.y >= 0 && hit.box && isPole(hit.box)) {
      // Coming down onto a lamp post or a column: step off it sideways, or it would perch there for good.
      const q = hit.box;
      const ox = e.pos.x - (q.min.x + q.max.x) * 0.5;
      const oz = e.pos.z - (q.min.z + q.max.z) * 0.5;
      const d = Math.sqrt(ox * ox + oz * oz);
      e.vel.x = d > 0.01 ? (ox / d) * POLE_STEP : POLE_STEP;
      e.vel.z = d > 0.01 ? (oz / d) * POLE_STEP : 0;
    }
    if (e.pos.y < ground + t.floorClearance) {
      e.pos.y = ground + t.floorClearance;
      if (e.vel.y < 0) e.vel.y = 0;
    }
    // Inside the block, whatever the walls there look like.
    const b = G.physics.bounds;
    if (b) {
      const m = t.boundsMargin;
      if (e.pos.x < b.minX + m) {
        e.pos.x = b.minX + m;
        if (e.vel.x < 0) e.vel.x = 0;
      } else if (e.pos.x > b.maxX - m) {
        e.pos.x = b.maxX - m;
        if (e.vel.x > 0) e.vel.x = 0;
      }
      if (e.pos.z < b.minZ + m) {
        e.pos.z = b.minZ + m;
        if (e.vel.z < 0) e.vel.z = 0;
      } else if (e.pos.z > b.maxZ - m) {
        e.pos.z = b.maxZ - m;
        if (e.vel.z > 0) e.vel.z = 0;
      }
    }
    // The collision rays run from the centre: a corner beside the centre line can still end up inside
    // the airframe. Never leave it there (and never freeze it there): back out into free air.
    pushOut(G.physics.boxes, e.pos, e.vel, t, b);
    const moved = Math.hypot(e.pos.x - px, e.pos.y - py, e.pos.z - pz);
    if (moved > 0.02) e.lastActive = ctx.clock.now;

    // Attitude: bank into the acceleration, wobble when damaged, shake from hits.
    const sin = Math.sin(e.yaw);
    const cos = Math.cos(e.yaw);
    const forward = -ax * sin - az * cos;
    const right = ax * cos - az * sin;
    e.kickPitch = damp(e.kickPitch, 0, 5, dt);
    e.kickRoll = damp(e.kickRoll, 0, 5, dt);
    let pitch = clamp(-forward * TILT_PER_ACCEL, -MAX_TILT, MAX_TILT) + e.kickPitch;
    let roll = clamp(-right * TILT_PER_ACCEL, -MAX_TILT, MAX_TILT) + e.kickRoll;
    if (damaged) {
      pitch += Math.sin(e.wobble * 9.1) * 0.1;
      roll += Math.cos(e.wobble * 7.7) * 0.13;
    }
    e.pitch = damp(e.pitch, pitch, 7, dt);
    e.roll = damp(e.roll, roll, 7, dt);
    e.rotorWant = 0.75 + 0.25 * Math.min(1, a / t.accel);
  }

  /* ------------------------------------------------------------------------------------ attack */

  function fireBolt(e, t) {
    const p = ctx.player;
    const chest = p.crouching ? Math.min(0.75, t.aimHeight) : t.aimHeight;
    leadPoint(e.gun.x, e.gun.y, e.gun.z, p.pos.x, p.pos.y + chest, p.pos.z, p.vx, p.vy, p.vz, t.boltSpeed, e.lead, aimAt);
    boltDir.set(aimAt[0] - e.gun.x, aimAt[1] - e.gun.y, aimAt[2] - e.gun.z).normalize();
    const damaged = e.hp < e.maxHp * t.damagedBelow;
    const spread = aimSpread(t.spreadFar, t.spreadNear, e.exposure, p.speed, t.spreadPerSpeed, damaged ? t.damagedSpread : 1);
    boltDir.x += (ctx.random() * 2 - 1) * spread;
    boltDir.y += (ctx.random() * 2 - 1) * spread;
    boltDir.z += (ctx.random() * 2 - 1) * spread;
    boltDir.normalize();
    // From the airframe's centre line, so a bolt never starts inside something the gun pokes into.
    origin.set(e.pos.x, e.gun.y, e.pos.z);
    ctx.bolts.spawn(origin, boltDir, t.boltDamage * ctx.scale.damage, e);
    e.vel.addScaledVector(boltDir, -t.recoilPush);
    e.kickPitch += 0.06;
    e.anim.lamp = 12;
    ctx.fx.muzzleFlash(e.gun, boltDir, 0.6, true);
    ctx.flash(e.gun, ctx.palette.tracer, 10, 6, 0.05);
    ctx.emit('enemy:fire', { enemy: e, type: 'buzzard', pos: e.gun.clone(), dir: boltDir.clone() });
    e.lastActive = ctx.clock.now;
  }

  function attack(e, dt, t, bearing, dist) {
    if (e.telegraph > 0) {
      e.telegraph -= dt;
      const k = 1 - Math.max(0, e.telegraph) / t.telegraph;
      e.lampWant = 2.5 + 16 * k * k;
      if (e.telegraph <= 0) {
        e.telegraph = 0;
        if (e.mode === 'engage') {
          e.burstLeft = t.burst;
          e.burstTimer = 0;
          e.lead = ctx.range(t.lead);
        } else {
          ctx.releaseToken(e);
        }
      }
      return;
    }
    if (e.burstLeft > 0) {
      e.lampWant = 7;
      e.burstTimer -= dt;
      while (e.burstLeft > 0 && e.burstTimer <= 0) {
        fireBolt(e, t);
        e.burstLeft--;
        e.burstTimer += t.burstGap;
      }
      if (e.burstLeft === 0) {
        ctx.releaseToken(e);
        e.cooldown = ctx.range(t.cooldown) * ctx.scale.cooldown;
      }
      return;
    }
    e.cooldown -= dt;
    if (
      e.mode === 'engage' &&
      e.sees &&
      e.cooldown <= 0 &&
      dist < t.fireRange &&
      Math.abs(angleDelta(e.yaw, bearing)) < t.aimTolerance &&
      ctx.requestToken(e)
    ) {
      e.telegraph = t.telegraph;
      ctx.emit('enemy:telegraph', { enemy: e, type: 'buzzard', duration: t.telegraph, pos: e.pos.clone() });
    }
  }

  /* ------------------------------------------------------------------------------------ update */

  function update(e, dt) {
    const t = ctx.tune.buzzard;
    const p = ctx.player;
    if (!e.passive) fly(e, dt, t);

    // Facing: the player or the place it is curious about; its own heading on patrol.
    let faceX = e.vel.x;
    let faceZ = e.vel.z;
    let lookY = e.pos.y - 3;
    if (e.mode === 'engage' && e.sinceSeen <= t.orbit.lostAfter) {
      faceX = p.pos.x - e.pos.x;
      faceZ = p.pos.z - e.pos.z;
      lookY = p.pos.y + t.aimHeight;
    } else if (e.mode !== 'patrol') {
      faceX = e.lastKnown.x - e.pos.x;
      faceZ = e.lastKnown.z - e.pos.z;
      lookY = e.lastKnown.y + 1;
    }
    const flat = Math.hypot(faceX, faceZ);
    const bearing = flat > 0.3 ? Math.atan2(-faceX, -faceZ) : e.yaw;
    e.yaw = wrapAngle(e.yaw + moveToward(0, angleDelta(e.yaw, bearing), t.yawRate * dt));
    e.eyeYawWant = angleDelta(e.yaw, bearing);
    e.eyePitchWant = Math.atan2(lookY - e.pos.y, Math.max(flat, 1)) - e.pitch;

    // The eye: dim on patrol, searching pulse, hard red when it has you.
    e.strobe += dt;
    e.lampWant = e.mode === 'engage' ? 2.5 : e.mode === 'patrol' ? 0.7 : 1.3 + 0.6 * Math.sin(e.strobe * 6);
    if (!e.passive) attack(e, dt, t, Math.atan2(-(p.pos.x - e.pos.x), -(p.pos.z - e.pos.z)), Math.hypot(p.pos.x - e.pos.x, p.pos.y - e.pos.y, p.pos.z - e.pos.z));

    // Damage shows: smoke, the odd spark.
    if (e.hp < e.maxHp * t.damagedBelow) {
      e.smokeIn -= dt;
      if (e.smokeIn <= 0) {
        e.smokeIn = ctx.range(t.smokeEvery);
        ctx.fx.smoke(e.pos, 0.45);
      }
      e.sparkIn -= dt;
      if (e.sparkIn <= 0) {
        e.sparkIn = 0.5 + ctx.random() * 1.2;
        ctx.fx.sparks(e.pos, DOWN, 5);
      }
    }

    poseBuzzard(e, e.anim, dt, e.rig.matrices);
    e.rig.touch();
    place(e);
  }

  /** Knock-back and a shake on every hit. */
  function onHit(e, amount, info) {
    const t = ctx.tune.buzzard;
    if (info.dir) e.vel.addScaledVector(info.dir, Math.min(t.knockback.max, amount * t.knockback.perDamage));
    e.kickPitch += (ctx.random() * 2 - 1) * t.hitKick;
    e.kickRoll += (ctx.random() * 2 - 1) * t.hitKick;
    e.anim.flash = Math.min(1, e.anim.flash + 0.7);
  }

  function onKilled(e, info) {
    const t = ctx.tune.buzzard;
    e.vel.y += t.deathKick.up;
    if (info.dir) e.vel.addScaledVector(info.dir, t.deathKick.along);
    e.spin = (ctx.random() < 0.5 ? -1 : 1) * 3;
    e.anim.lost = Math.floor(ctx.random() * 4) % 4;
    e.rotorWant = 0.25;
    e.lampWant = 0.4;
    e.smokeIn = e.sparkIn = 0;
    // The rotor that came off.
    const hub = ROTORS[e.anim.lost];
    origin.set(e.pos.x + hub[0], e.pos.y + hub[1], e.pos.z + hub[2]);
    ctx.fx.sparks(origin, UP, 10);
    ctx.fx.debris(origin, 4, 0x30333a, 5);
    ctx.fx.smoke(e.pos, 0.8);
  }

  /** The fall. Returns true when it has hit something and burst (the caller then retires it). */
  function updateDying(e, dt) {
    const t = ctx.tune.buzzard;
    e.vel.y -= t.fallGravity * dt;
    e.vel.x *= Math.exp(-0.4 * dt);
    e.vel.z *= Math.exp(-0.4 * dt);
    e.spin += Math.sign(e.spin || 1) * 9 * dt;
    e.yaw = wrapAngle(e.yaw + e.spin * dt);
    e.pitch = damp(e.pitch, 0.5, 2, dt);
    e.roll += e.spin * 0.25 * dt;

    const speed = Math.hypot(e.vel.x, e.vel.y, e.vel.z);
    const travel = speed * dt;
    let landed = false;
    if (speed > 1e-3) {
      dir.set(e.vel.x / speed, e.vel.y / speed, e.vel.z / speed);
      if (G.physics.raycast(e.pos, dir, travel + 0.25, hit)) {
        e.pos.addScaledVector(dir, Math.max(0, hit.dist - 0.25));
        landed = true;
      }
    }
    if (!landed) e.pos.addScaledVector(e.vel, dt);
    if (e.deadTime > t.fallMaxTime || e.pos.y < -3) landed = true;

    e.smokeIn -= dt;
    if (e.smokeIn <= 0) {
      e.smokeIn = 0.05;
      ctx.fx.smoke(e.pos, 0.7);
    }
    e.sparkIn -= dt;
    if (e.sparkIn <= 0) {
      e.sparkIn = 0.16;
      ctx.fx.sparks(e.pos, UP, 4);
    }
    e.lampWant = e.deadTime < 0.5 ? 1.5 * Math.abs(Math.sin(e.deadTime * 40)) : 0;
    poseBuzzard(e, e.anim, dt, e.rig.matrices);
    e.rig.touch();
    place(e);
    return landed;
  }

  /** What is left of it when it lands: a burst that hurts whatever stands close, Goons included. */
  function burst(e) {
    const t = ctx.tune.buzzard;
    G.combat.explode({
      pos: e.pos.clone(),
      radius: t.burstRadius,
      damage: t.burstDamage,
      playerScale: t.burstPlayerScale,
      source: e,
      size: 'small',
    });
  }

  function sensor(e, out) {
    return out.copy(e.eye);
  }

  /** Rotor discs, the eye flare, the nav strobes. */
  function drawGlow(e, glow) {
    m3Euler(rot, 0, e.pitch, e.yaw, e.roll);
    const level = e.anim.rotorSpeed;
    for (let i = 0; i < 4; i++) {
      if (e.anim.lost === i) continue;
      const h = ROTORS[i];
      glow.disc(
        e.pos.x + rot[0] * h[0] + rot[1] * (h[1] + 0.022) + rot[2] * h[2],
        e.pos.y + rot[3] * h[0] + rot[4] * (h[1] + 0.022) + rot[5] * h[2],
        e.pos.z + rot[6] * h[0] + rot[7] * (h[1] + 0.022) + rot[8] * h[2],
        ROTOR_RADIUS,
        rot,
        0,
        level,
      );
    }
    const lamp = e.anim.lamp;
    if (lamp > 0.05) {
      const k = Math.min(1, lamp / 18);
      const size = 0.16 + 0.75 * Math.sqrt(k);
      glow.flare(e.eye.x, e.eye.y, e.eye.z, size, BUZZARD_LAMP.r * lamp, BUZZARD_LAMP.g * lamp + lamp * 0.02, BUZZARD_LAMP.b * lamp);
    }
    if (!e.alive) return;
    // Strobes: red to port and green to starboard flash twice, the white tail light once, per cycle.
    const c = e.strobe % STROBE_PERIOD;
    const side = c < 0.05 || (c > 0.16 && c < 0.21);
    const tail = c > 0.65 && c < 0.71;
    for (let i = 0; i < 3; i++) {
      if (i < 2 ? !side : !tail) continue;
      const s = STROBES[i];
      const x = e.pos.x + rot[0] * s[0] + rot[1] * s[1] + rot[2] * s[2];
      const y = e.pos.y + rot[3] * s[0] + rot[4] * s[1] + rot[5] * s[2];
      const z = e.pos.z + rot[6] * s[0] + rot[7] * s[1] + rot[8] * s[2];
      if (i === 0) glow.flare(x, y, z, 0.22, 5, 0.25, 0.2);
      else if (i === 1) glow.flare(x, y, z, 0.22, 0.25, 5, 0.6);
      else glow.flare(x, y, z, 0.26, 4.5, 4.5, 5);
    }
  }

  return {
    pool,
    material,
    spawn,
    retire,
    update,
    updateDying,
    burst,
    onHit,
    onKilled,
    sensor,
    drawGlow,
    /** For enemies.debug(): every doorway found, as [outside x, z, inside x, z, height]. */
    doorways() {
      if (!rooms) findRooms();
      return rooms.flatMap((r) => r.list.map((d) => [d.ox, d.oz, d.ix, d.iz, +d.y.toFixed(2)]));
    },
    onLeaveEngage(e) {
      e.burstLeft = 0;
    },
    onEngage(e) {
      // Start the orbit from where it is, so it does not cut across the player to get on station.
      const p = ctx.player;
      e.orbitAngle = Math.atan2(e.pos.z - p.pos.z, e.pos.x - p.pos.x);
      e.rethinkIn = ctx.range(ctx.tune.buzzard.orbit.rethink);
    },
    onInvestigate(e) {
      e.orbitAngle = Math.atan2(e.pos.z - e.lastKnown.z, e.pos.x - e.lastKnown.x);
    },
    onPatrol(e) {
      e.orbitAngle = Math.atan2(e.pos.z - e.home.z, e.pos.x - e.home.x);
      e.patrolRadius = Math.max(1.5, Math.min(e.patrolRadius, 9));
    },
  };
}
