// The Vultures (`G.enemies`, CONTRACT 6.6): Goons on foot and Buzzards in the air.
//
// This file is the part both types share: the pools, the public API, the mode machine
// (patrol → investigate / search → engage), sight and hearing, the accuracy ramp, the attack tokens,
// hit tests and damage, bodies, and the per-frame budgets. What each type does inside a mode lives in
// enemies/goon.js and enemies/buzzard.js; the rules as pure functions in enemies/logic.js; the models
// and their procedural animation in enemies/*-model.js and enemies/goon-anim.js.
//
// Tuning is src/config/enemies.js. setDifficulty(table) restores the base values and lays the table
// over them; everything except hit points is read live, hit points are fixed when a unit spawns.
//
// Beyond the contract: spawn() also takes {yaw, passive} (passive units never sense or act: showcase),
// every enemy carries `mode` / `yaw` / `vel` / `sees` / `exposure` / `lastActive`, and `enemies.debug()`
// reports pools, tokens and budgets for tests.

import * as THREE from 'three';
import { damp } from './core/util.js';
import { createRng, toSeed } from './core/rng.js';
import { createBolts } from './enemies/bolts.js';
import { createBuzzards } from './enemies/buzzard.js';
import { createGlow } from './enemies/glow.js';
import { createGoons } from './enemies/goon.js';
import { createTokens, exposureStep, inSight, rayCapsule, rayEllipsoid, raySphere, reactionTime, seenStep } from './enemies/logic.js';

const KILLED = Object.freeze({ killed: true });
const SURVIVED = Object.freeze({ killed: false });
const noop = () => {};

/** Deep copy of plain tuning data (numbers, arrays, nested objects). */
function cloneTable(value) {
  if (Array.isArray(value)) return value.map(cloneTable);
  if (value && typeof value === 'object') {
    const out = {};
    for (const key of Object.keys(value)) out[key] = cloneTable(value[key]);
    return out;
  }
  return value;
}

/** Restores `live` to `base`, then lays `overlay` over it. In place: the modules hold on to `live`. */
function retune(live, base, overlay) {
  for (const key of Object.keys(base)) live[key] = cloneTable(base[key]);
  if (overlay) for (const key of Object.keys(overlay)) if (key in base) live[key] = cloneTable(overlay[key]);
}

export function createEnemies(G) {
  const cfg = G.config.enemies;
  const look = G.config.look || {};
  const palette = look.palette || {};

  const rng = createRng(toSeed(G.params && G.params.eseed, cfg.seed));
  const random = () => rng.next();

  const root = new THREE.Group();
  root.name = 'enemies';
  if (G.scene) G.scene.add(root);

  // Effects and lights may be stubs, or missing altogether in tests: resolve them once.
  const fxOf = (name) => (G.fx && typeof G.fx[name] === 'function' ? G.fx[name].bind(G.fx) : noop);
  const lights = G.render && G.render.lights;

  const tune = { goon: {}, buzzard: {}, ai: {} };
  const scale = { hp: 1, damage: 1, cooldown: 1 };
  const tokens = createTokens();
  const list = []; // living and dying
  const bodies = []; // Goons lying on the street, oldest first

  const player = {
    pos: new THREE.Vector3(),
    eye: new THREE.Vector3(),
    alive: false,
    crouching: false,
    speed: 0, // horizontal, smoothed: what opens up the enemies' aim
    vx: 0,
    vy: 0,
    vz: 0,
  };

  const ctx = {
    G,
    cfg,
    tune,
    scale,
    root,
    list,
    player,
    tokens,
    random,
    range: (pair) => pair[0] + (pair[1] - pair[0]) * rng.next(),
    clock: { now: 0 },
    budget: { paths: 0, picks: 0 },
    alive: 0,
    emit: (name, payload) => {
      if (G.events) G.events.emit(name, payload);
    },
    fx: {
      tracer: fxOf('tracer'),
      muzzleFlash: fxOf('muzzleFlash'),
      smoke: fxOf('smoke'),
      sparks: fxOf('sparks'),
      dust: fxOf('dust'),
      debris: fxOf('debris'),
    },
    flash: lights && typeof lights.flash === 'function' ? (pos, color, intensity, range, ttl) => lights.flash(pos, color, intensity, range, ttl) : noop,
    palette: { tracer: palette.tracerEnemy ?? 0xff3a22, muzzle: 0xff7a3c },
    bolts: null,
    requestToken,
    releaseToken,
    cancelAttack,
  };

  retune(tune.goon, cfg.goon, cfg.difficulty.boss.goon);
  retune(tune.buzzard, cfg.buzzard, cfg.difficulty.boss.buzzard);
  retune(tune.ai, cfg.ai, cfg.difficulty.boss.ai);

  const goons = createGoons(ctx);
  const buzzards = createBuzzards(ctx);
  const brains = { goon: goons, buzzard: buzzards };
  const bolts = (ctx.bolts = createBolts(ctx));
  const glow = createGlow(root, 160, cfg.pool.buzzard * 4);

  let nextId = 1;
  let sinceGunfire = Infinity;
  let pathCursor = 0;
  let pickCursor = 0;

  // Scratch.
  const sensorPos = new THREE.Vector3();
  const probe = new THREE.Vector3();
  const trace = { enemy: null, dist: 0, part: 'body', cx: 0, cy: 0, cz: 0 };

  /* ------------------------------------------------------------------------------------ tokens */

  function requestToken(e) {
    if (e.hasToken) return true;
    if (!tokens.request(e.type, ctx.clock.now, ctx.alive, tune.ai)) return false;
    e.hasToken = true;
    return true;
  }

  function releaseToken(e) {
    if (!e.hasToken) return;
    e.hasToken = false;
    tokens.release();
  }

  /** Drops a telegraph or burst in progress and hands the token back. */
  function cancelAttack(e) {
    e.telegraph = 0;
    e.burstLeft = 0;
    releaseToken(e);
  }

  /* ------------------------------------------------------------------------------------- modes */

  function setMode(e, mode) {
    if (e.mode === mode) return;
    const prev = e.mode;
    if (prev === 'engage') {
      cancelAttack(e);
      brains[e.type].onLeaveEngage(e);
    }
    e.mode = e.state = mode;
    return prev;
  }

  /** Everyone not yet fighting within `radius` of `e` comes to look at `pos`. */
  function rally(e, radius, pos) {
    for (let i = 0; i < list.length; i++) {
      const o = list[i];
      if (o === e || !o.alive || o.passive || o.mode === 'engage') continue;
      if (o.pos.distanceToSquared(e.pos) <= radius * radius) investigate(o, pos, ctx.range(tune.ai.noiseTime), false);
    }
  }

  function engage(e) {
    if (!e.alive || e.passive || e.mode === 'engage') return;
    setMode(e, 'engage');
    e.sinceSeen = 0;
    brains[e.type].onEngage(e);
    ctx.emit('enemy:alert', { enemy: e, pos: e.pos.clone() });
    rally(e, tune.ai.rallyOnSight, player.pos);
  }

  /**
   * Sends a unit that is not fighting to look at `pos` for `seconds`. With `announce`, a unit that was
   * unaware until now says so (enemy:alert).
   */
  function investigate(e, pos, seconds, announce) {
    if (!e.alive || e.passive || e.mode === 'engage') return;
    const wasPatrol = e.mode === 'patrol';
    // Where to go: the ground under the noise (a muzzle is at eye height, a blast may be in the air).
    e.lastKnown.set(pos.x, G.physics.groundHeight(pos.x, pos.z, pos.y + 0.3), pos.z);
    setMode(e, e.mode === 'search' ? 'search' : 'investigate');
    e.modeTime = seconds;
    brains[e.type].onInvestigate(e);
    if (announce && wasPatrol) ctx.emit('enemy:alert', { enemy: e, pos: new THREE.Vector3().copy(pos) });
  }

  function toPatrol(e) {
    setMode(e, 'patrol');
    e.home.copy(e.pos); // it does not walk back: wherever it gave up is home now
    e.seen = 0;
    brains[e.type].onPatrol(e);
  }

  /* -------------------------------------------------------------------------------- perception */

  function sense(e, dt) {
    const ai = tune.ai;
    e.senseIn -= dt;
    if (e.senseIn > 0) return;
    const tick = ai.senseEvery[0] + (ai.senseEvery[1] - ai.senseEvery[0]) * random();
    e.senseIn = tick;
    let visible = false;
    if (player.alive) {
      const brain = brains[e.type];
      brain.sensor(e, sensorPos);
      const dx = player.eye.x - sensorPos.x;
      const dy = player.eye.y - sensorPos.y;
      const dz = player.eye.z - sensorPos.z;
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
      // A Goon looks where his head is turned, a Buzzard where its nose points.
      const facing = e.type === 'goon' ? e.yaw + e.anim.headYaw : e.yaw;
      visible = inSight(dist, dx, dz, facing, e.mode === 'engage', ai) && G.physics.lineOfSight(sensorPos, player.eye);
    }
    e.sees = visible;
    e.seen = seenStep(e.seen, visible, tick, ai);
    if (visible) {
      e.lastKnown.copy(player.pos);
      e.sinceSeen = 0;
      if (e.mode !== 'engage' && e.seen >= reactionTime(tune[e.type].reaction, e.mode, ai)) engage(e);
    }
  }

  function think(e, dt) {
    const ai = tune.ai;
    e.sinceSeen += dt;
    sense(e, dt);
    e.exposure = exposureStep(e.exposure, e.sees, dt, ai);
    if (e.mode === 'engage') {
      // An engaged unit knows where the player is until it has lost him for a while.
      if (!player.alive || e.sinceSeen >= ai.loseSightAfter) {
        if (e.sinceSeen < ai.loseSightAfter) e.lastKnown.copy(player.pos);
        setMode(e, 'search');
        e.modeTime = ctx.range(ai.searchTime);
        brains[e.type].onInvestigate(e);
      }
    } else if (e.mode !== 'patrol') {
      e.modeTime -= dt;
      if (e.modeTime <= 0) toPatrol(e);
    }
  }

  /* ------------------------------------------------------------------------------- spawn, retire */

  function retire(e) {
    releaseToken(e);
    brains[e.type].retire(e);
    e.active = false;
    e.alive = false;
    e.state = 'idle';
    let i = list.indexOf(e);
    if (i >= 0) list.splice(i, 1);
    i = bodies.indexOf(e);
    if (i >= 0) bodies.splice(i, 1);
  }

  function spawn(type, pos, opts = {}) {
    const brain = brains[type];
    if (!brain || !pos) return null;
    const pool = brain.pool;
    // A free slot; else the oldest body; else one that is still falling; null when all are alive.
    let e = null;
    for (let i = 0; i < pool.length && !e; i++) if (!pool[i].active) e = pool[i];
    if (!e && bodies.length && type === 'goon') e = bodies[0];
    for (let i = 0; i < pool.length && !e; i++) if (!pool[i].alive) e = pool[i];
    if (!e) return null;
    if (e.active) retire(e);

    const t = tune[type];
    e.id = nextId++;
    e.active = true;
    e.alive = true;
    e.maxHp = e.hp = t.hp * scale.hp;
    e.passive = !!opts.passive;
    e.seen = 0;
    e.sees = false;
    e.sinceSeen = Infinity;
    e.senseIn = random() * tune.ai.senseEvery[1];
    e.exposure = 0;
    e.telegraph = 0;
    e.hasToken = false;
    e.lastActive = ctx.clock.now;
    e.deadTime = 0;
    e.mode = e.state = 'patrol';
    e.modeTime = 0;
    brain.spawn(e, pos, opts);
    e.lastKnown.copy(e.pos);
    list.push(e);
    if (opts.alerted && !e.passive) {
      // Reinforcements arrive already hunting: toward the given point, else toward the player.
      const at = opts.target || (G.player && G.player.pos) || e.pos;
      investigate(e, at, t.spawnAlertTime, false);
    }
    ctx.emit('enemy:spawn', { enemy: e });
    return e;
  }

  function clear() {
    for (let i = list.length - 1; i >= 0; i--) retire(list[i]);
    for (let i = bodies.length - 1; i >= 0; i--) retire(bodies[i]);
    tokens.reset();
    bolts.clear();
    glow.begin();
    glow.end();
  }

  /* --------------------------------------------------------------------------------- hit tests */

  /** Nearest living enemy along a unit ray. Fills `trace`; allocates nothing. */
  function traceRay(origin, dir, maxDist) {
    trace.enemy = null;
    trace.dist = maxDist;
    const ox = origin.x;
    const oy = origin.y;
    const oz = origin.z;
    const dx = dir.x;
    const dy = dir.y;
    const dz = dir.z;
    const g = tune.goon;
    const b = tune.buzzard;
    for (let i = 0; i < list.length; i++) {
      const e = list[i];
      if (!e.alive) continue;
      const p = e.pos;
      // Cheap reject: the ray's closest approach to the unit is further than it could reach.
      const rx = p.x - ox;
      const ry = p.y + (e.type === 'goon' ? 0.9 : 0) - oy;
      const rz = p.z - oz;
      const along = rx * dx + ry * dy + rz * dz;
      if (along < -1.5 || along > trace.dist + 1.5) continue;
      const off = rx * rx + ry * ry + rz * rz - along * along;
      if (off > 1.5 * 1.5) continue;

      if (e.type === 'buzzard') {
        const t = rayEllipsoid(ox, oy, oz, dx, dy, dz, p.x, p.y, p.z, b.radius, b.halfHeight);
        if (t < trace.dist) {
          trace.dist = t;
          trace.enemy = e;
          trace.part = 'body';
          trace.cx = p.x;
          trace.cy = p.y;
          trace.cz = p.z;
        }
        continue;
      }
      const h = e.head;
      const head = raySphere(ox, oy, oz, dx, dy, dz, h.x, h.y, h.z, g.head.radius);
      if (head < trace.dist) {
        trace.dist = head;
        trace.enemy = e;
        trace.part = 'head';
        trace.cx = h.x;
        trace.cy = h.y;
        trace.cz = h.z;
      }
      const lo = e.bodyLow;
      const hi = e.bodyHigh;
      const body = rayCapsule(ox, oy, oz, dx, dy, dz, lo.x, lo.y, lo.z, hi.x, hi.y, hi.z, g.bodyRadius);
      if (body < trace.dist) {
        trace.dist = body;
        trace.enemy = e;
        trace.part = 'body';
        // The normal points away from the nearest point of the body axis.
        const px = ox + dx * body;
        const py = oy + dy * body;
        const pz = oz + dz * body;
        const ax = hi.x - lo.x;
        const ay = hi.y - lo.y;
        const az = hi.z - lo.z;
        const len2 = ax * ax + ay * ay + az * az || 1;
        const s = Math.min(1, Math.max(0, ((px - lo.x) * ax + (py - lo.y) * ay + (pz - lo.z) * az) / len2));
        trace.cx = lo.x + ax * s;
        trace.cy = lo.y + ay * s;
        trace.cz = lo.z + az * s;
      }
    }
    return trace.enemy !== null;
  }

  function raycast(origin, dir, maxDist = 500) {
    if (!traceRay(origin, dir, maxDist)) return null;
    const point = new THREE.Vector3().copy(origin).addScaledVector(dir, trace.dist);
    const normal = new THREE.Vector3(point.x - trace.cx, point.y - trace.cy, point.z - trace.cz);
    if (normal.lengthSq() < 1e-10) normal.copy(dir).negate();
    else normal.normalize();
    return { enemy: trace.enemy, dist: trace.dist, point, normal, part: trace.part };
  }

  function aimTarget(origin, dir, maxDist = 60) {
    if (!traceRay(origin, dir, maxDist)) return false;
    probe.copy(origin).addScaledVector(dir, trace.dist);
    return G.physics.lineOfSight(origin, probe);
  }

  /* ------------------------------------------------------------------------------------ damage */

  function damage(e, amount, info = {}) {
    if (!e || !e.alive || !(amount > 0)) return SURVIVED;
    const part = info.part || 'body';
    const brain = brains[e.type];
    e.hp -= amount;
    ctx.emit('enemy:hit', { enemy: e, part, damage: amount, point: new THREE.Vector3().copy(info.point || e.pos) });
    brain.onHit(e, amount, info);

    if (e.hp > 0) {
      // Provoked: it comes for the player at once, and takes its friends along.
      if (e.mode !== 'engage' && !e.passive && player.alive) {
        investigate(e, player.pos, tune.ai.provokedTime, true);
        e.seen = Math.max(e.seen, 1);
        e.senseIn = 0;
        rally(e, tune.ai.rallyOnHit, player.pos);
      }
      return SURVIVED;
    }

    e.hp = 0;
    e.alive = false;
    cancelAttack(e);
    if (e.mode === 'engage') brain.onLeaveEngage(e);
    e.mode = e.state = 'dying';
    e.deadTime = 0;
    e.sees = false;
    brain.onKilled(e, info);
    ctx.emit('enemy:killed', {
      enemy: e,
      type: e.type,
      pos: e.pos.clone(),
      part,
      byPlayer: info.from === 'player' || info.from === 'blast',
      weapon: info.weapon || null,
    });
    return KILLED;
  }

  /* ------------------------------------------------------------------------------------ hearing */

  /** Everyone within `radius` of `pos` who is not fighting yet goes to look. */
  function alert(pos, radius = tune.ai.alertDefaultRadius) {
    if (!pos) return;
    for (let i = 0; i < list.length; i++) {
      const e = list[i];
      if (!e.alive || e.passive || e.mode === 'engage') continue;
      if (e.pos.distanceToSquared(pos) <= radius * radius) investigate(e, pos, ctx.range(tune.ai.noiseTime), true);
    }
  }

  /** Softer: only units that are still unaware go to look; the ones already hunting keep their lead. */
  function hear(pos, radius = tune.ai.alertDefaultRadius) {
    if (!pos) return;
    for (let i = 0; i < list.length; i++) {
      const e = list[i];
      if (!e.alive || e.passive || e.mode !== 'patrol') continue;
      if (e.pos.distanceToSquared(pos) <= radius * radius) investigate(e, pos, ctx.range(tune.ai.noiseTime), true);
    }
  }

  if (G.events) {
    G.events.on('weapon:fire', (ev) => {
      if (!ev || !ev.pos || sinceGunfire < tune.ai.gunfireEvery) return;
      sinceGunfire = 0;
      alert(ev.pos, tune.ai.hear.gunfire);
    });
    G.events.on('explosion', (ev) => {
      if (ev && ev.pos) alert(ev.pos, tune.ai.hear.explosion);
    });
    G.events.on('explosive:blast', (ev) => {
      if (ev && ev.pos) alert(ev.pos, tune.ai.hear.explosive);
    });
  }

  /* ------------------------------------------------------------------------------------ update */

  function readPlayer(dt) {
    const p = G.player;
    if (!p || !p.pos) {
      player.alive = false;
      return;
    }
    player.pos.copy(p.pos);
    if (p.eye) player.eye.copy(p.eye);
    else player.eye.set(p.pos.x, p.pos.y + 1.68, p.pos.z);
    player.alive = p.alive !== false;
    player.crouching = !!p.crouching;
    const v = p.vel;
    player.vx = v ? v.x : 0;
    player.vy = v ? v.y : 0;
    player.vz = v ? v.z : 0;
    const speed = player.alive ? Math.hypot(player.vx, player.vz) : 0;
    player.speed = damp(player.speed, speed, 6, dt);
  }

  /** Goon work that is rationed per frame: fire-position choices first, then path queries. */
  function spendBudgets() {
    const pool = goons.pool;
    const n = pool.length;
    for (let k = 0; k < n && ctx.budget.picks > 0; k++) {
      const e = pool[(pickCursor + k) % n];
      if (!e.alive || e.mode !== 'engage' || !e.wantPick) continue;
      if (e.sub !== 'move' && e.sub !== 'aim' && e.sub !== 'cool') continue;
      ctx.budget.picks--;
      goons.pick(e);
      pickCursor = (pickCursor + k + 1) % n;
    }
    for (let k = 0; k < n && ctx.budget.paths > 0; k++) {
      const e = pool[(pathCursor + k) % n];
      if (!e.alive || !e.needPath || !e.hasGoal) continue;
      ctx.budget.paths--;
      goons.plan(e);
      pathCursor = (pathCursor + k + 1) % n;
    }
  }

  function update(dt) {
    if (!(dt > 0)) return;
    ctx.clock.now += dt;
    sinceGunfire += dt;
    readPlayer(dt);
    ctx.budget.paths = tune.ai.pathsPerFrame;
    ctx.budget.picks = tune.ai.picksPerFrame;
    let alive = 0;
    for (let i = 0; i < list.length; i++) if (list[i].alive) alive++;
    ctx.alive = alive;

    for (let i = list.length - 1; i >= 0; i--) {
      const e = list[i];
      const brain = brains[e.type];
      if (e.alive) {
        if (!e.passive) think(e, dt);
        brain.update(e, dt);
        continue;
      }
      e.deadTime += dt;
      if (!brain.updateDying(e, dt)) continue;
      if (e.type === 'buzzard') {
        // It has landed: gone from the world before the burst, so the burst cannot touch it.
        retire(e);
        buzzards.burst(e);
      } else {
        // The Goon has come to rest: now a body, no longer in the list of the living and dying.
        list.splice(i, 1);
        e.state = 'dead';
        bodies.push(e);
        if (bodies.length > cfg.pool.bodies) goons.startFade(bodies[0]);
      }
    }
    spendBudgets();

    for (let i = bodies.length - 1; i >= 0; i--) {
      const e = bodies[i];
      // The oldest fades whenever there is one too many.
      if (bodies.length - i > cfg.pool.bodies) goons.startFade(e);
      if (goons.updateBody(e, dt)) retire(e);
    }

    bolts.update(dt);

    glow.begin();
    for (let i = 0; i < list.length; i++) brains[list[i].type].drawGlow(list[i], glow);
    bolts.draw(glow);
    glow.end();
  }

  /* --------------------------------------------------------------------------------------- API */

  return {
    list,
    aliveCount() {
      let n = 0;
      for (let i = 0; i < list.length; i++) if (list[i].alive) n++;
      return n;
    },
    countByType(type) {
      let n = 0;
      for (let i = 0; i < list.length; i++) if (list[i].alive && list[i].type === type) n++;
      return n;
    },
    spawn,
    clear,
    raycast,
    damage,
    alert,
    hear,
    /** table = config.enemies.difficulty[name]: base values restored, the table laid over them. */
    setDifficulty(table) {
      const t = table || cfg.difficulty.boss;
      retune(tune.goon, cfg.goon, t.goon);
      retune(tune.buzzard, cfg.buzzard, t.buzzard);
      retune(tune.ai, cfg.ai, t.ai);
    },
    /** Holdout wave multipliers: hp applies to units spawned from now on, damage and cooldown at once. */
    setScale(s = {}) {
      scale.hp = s.hp > 0 ? s.hp : 1;
      scale.damage = s.damage > 0 ? s.damage : 1;
      scale.cooldown = s.cooldown > 0 ? s.cooldown : 1;
    },
    nearestDistance() {
      const p = G.player;
      let best = Infinity;
      if (!p || !p.pos) return best;
      for (let i = 0; i < list.length; i++) {
        if (list[i].alive) best = Math.min(best, list[i].pos.distanceTo(p.pos));
      }
      return best;
    },
    aimTarget,
    update,
    /** For tests and tuning: what the pools, tokens and budgets are doing. */
    debug() {
      return {
        goons: goons.pool.filter((e) => e.active).length,
        buzzards: buzzards.pool.filter((e) => e.active).length,
        bodies: bodies.length,
        bolts: bolts.live,
        tokens: tokens.held,
        glow: glow.count,
        clock: ctx.clock.now,
        tune,
      };
    },
  };
}
