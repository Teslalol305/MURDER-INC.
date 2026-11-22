// Golden vectors for gameplay slice 2 (the enemies and the flow): runs the web game's own modules in Node and
// writes what they did to unreal/MurderInc/Content/Data/golden/*.json, for the automation tests
// MurderInc.Golden.World / EnemyLogic / Enemies / Flow. Called by golden.mjs (node tools/ue-export/golden.mjs).
//
// The world of every enemy scenario is src/physics.js filled with the block's colliders from level.json (the nav grid
// it builds equals level.json nav cell for cell; the script stops if not), the real src/enemies.js with its Goons,
// Buzzards and bolts, and a scripted player. Effects are no-ops; combat.hitscan and combat.explode are recorded,
// not resolved (the C++ host resolves them with engine traces), so the comparison is the AI's own decisions.
// Web units throughout: metres, seconds, radians, +Y up, north -Z, yaw 0 = north, + = left.

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import * as THREE from 'three';
import * as enemiesConfig from '../../src/config/enemies.js';
import * as flowConfig from '../../src/config/flow.js';
import * as textConfig from '../../src/config/text.js';
import * as weaponsConfig from '../../src/config/weapons.js';
import { createEvents } from '../../src/core/events.js';
import { createRng } from '../../src/core/rng.js';
import { createEnemies } from '../../src/enemies.js';
import * as L from '../../src/enemies/logic.js';
import { cardData, accuracy } from '../../src/game/stats.js';
import { compassSector, pickSpawn, spawnScore } from '../../src/game/spawn.js';
import { holdoutOrder, holdoutWave, killScore, missionOrder, pursuitType } from '../../src/game/waves.js';
import { createPhysics } from '../../src/physics.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
/** Inputs are drawn at the 12 digits the files keep, so the C++ reads exactly what the web game was given. */
const q = (x) => Number(x.toPrecision(12));
const vec = (v) => [v.x, v.y, v.z];

export function loadLevel(root) {
  return JSON.parse(readFileSync(join(root, 'unreal', 'MurderInc', 'Content', 'Data', 'level.json'), 'utf8'));
}

/** src/physics.js with the block's colliders, as the game builds it (bounds = level bounds). */
export function blockPhysics(level, G = {}) {
  const physics = createPhysics(G);
  const b = level.bounds.web;
  physics.setBounds(b);
  for (const c of level.colliders.boxes) {
    physics.addBox({ min: c.web.min, max: c.web.max, tag: c.tag, surface: c.surface, bulletOnly: c.flags.bulletOnly, playerOnly: c.flags.playerOnly, noNav: c.flags.noNav });
  }
  const nav = physics.nav;
  const rows = level.nav.grid.cells;
  let diff = 0;
  for (let j = 0; j < nav.rows; j++) for (let i = 0; i < nav.cols; i++) if ((nav.grid[j * nav.cols + i] ? '#' : '.') !== rows[j][i]) diff++;
  if (diff) throw new Error(`nav grid differs from level.json in ${diff} cells`);
  return physics;
}

/** G.level as src/enemies.js reads it. */
function blockLevel(level) {
  const d = level.el.deck.web;
  return {
    coverPoints: level.coverPoints.points.map((p) => ({ pos: V(p.web.pos.x, p.web.pos.y, p.web.pos.z) })),
    el: { y: d.underside, minX: d.minX, maxX: d.maxX, minZ: d.minZ, maxZ: d.maxZ },
    interiorBoxes: level.interior.boxes.map((b) => ({ min: V(b.web.min.x, b.web.min.y, b.web.min.z), max: V(b.web.max.x, b.web.max.y, b.web.max.z) })),
  };
}

// ------------------------------------------------------------------------------------------- the world

export function goldenWorld(level, seed, write, about) {
  const rng = createRng(seed).fork('golden-world');
  const R = (a, b) => q(a + (b - a) * rng.next());
  const physics = blockPhysics(level, { rng: createRng(seed) });
  const b = level.bounds.web;
  const rays = [];
  for (let k = 0; k < 160; k++) {
    const o = [R(b.minX, b.maxX), R(0.2, 9), R(b.minZ, b.maxZ)];
    const a = R(0, Math.PI * 2);
    const e = R(-0.6, 0.4);
    const d = [Math.cos(a) * Math.cos(e), Math.sin(e), Math.sin(a) * Math.cos(e)];
    const hit = physics.raycast(V(...o), V(...d), 40);
    rays.push([o, d, hit ? [hit.dist, hit.normal.x, hit.normal.y, hit.normal.z, hit.box ? physics.boxes.indexOf(hit.box) : -1] : null]);
  }
  const sight = [];
  for (let k = 0; k < 160; k++) {
    const a = [R(b.minX, b.maxX), R(0.2, 6), R(b.minZ, b.maxZ)];
    const c = [a[0] + R(-25, 25), R(0.2, 6), a[2] + R(-25, 25)];
    sight.push([a, c, physics.lineOfSight(V(...a), V(...c)), physics.lineOfSight(V(...a), V(...c), { movement: true })]);
  }
  const ground = [];
  for (let k = 0; k < 120; k++) {
    const x = R(b.minX, b.maxX);
    const z = R(b.minZ, b.maxZ);
    const maxY = R(0.2, 12);
    ground.push([x, z, maxY, physics.groundHeight(x, z, maxY), physics.overlapsCylinder(x, z, 0.3, 0.1, 1.8)]);
  }
  // A body walking scripted velocities over the block: walls, steps, kerbs, the play bounds.
  const walks = [];
  for (const [name, start, legs] of [
    ['avenue', [-37.4, 0.15, 8.15], [[4, 0, 60], [0, 4, 90], [-3, -3, 80], [5, 1, 120], [0, -5, 150]]],
    ['shop', [-12.15, 0, -8.5], [[0, -3, 120], [3, 0, 90], [0, 3, 90], [-6, 0, 60]]],
    ['lot', [30, 0, 25], [[3, 2, 120], [-2, 3, 90], [6, -6, 90]]],
  ]) {
    const pos = V(...start);
    pos.y = physics.groundHeight(pos.x, pos.z, pos.y + 0.6);
    const vel = V(0, 0, 0);
    let onGround = true;
    const out = [];
    for (const [vx, vz, frames] of legs) {
      for (let f = 0; f < frames; f++) {
        vel.x = vx;
        vel.z = vz;
        vel.y = onGround ? 0 : vel.y - 20 / 60;
        const r = physics.moveCapsule(pos, vel, 1 / 60, 0.3, 1.8, onGround);
        onGround = r.onGround;
        out.push([vx, vz, pos.x, pos.y, pos.z, vel.x, vel.y, vel.z, r.onGround ? 1 : 0, r.hitWall ? 1 : 0]);
      }
    }
    walks.push({ name, start: vec(pos.clone().set(...start)), radius: 0.3, height: 1.8, gravity: 20, dt: 1 / 60, out });
  }
  // The nav grid: paths, straight lines, random points (its own fork 'nav' of the root seed), snaps.
  const nav = physics.nav;
  const paths = [];
  for (let k = 0; k < 60; k++) {
    const a = [R(b.minX, b.maxX), 0, R(b.minZ, b.maxZ)];
    const c = [R(b.minX, b.maxX), 0, R(b.minZ, b.maxZ)];
    const p = nav.findPath(V(...a), V(...c));
    paths.push([a, c, p ? p.map((q) => [q.x, q.z]) : null]);
  }
  const lines = [];
  for (let k = 0; k < 100; k++) {
    const a = [R(b.minX, b.maxX), 0, R(b.minZ, b.maxZ)];
    const c = [a[0] + R(-12, 12), 0, a[2] + R(-12, 12)];
    lines.push([a, c, nav.clearLine(V(...a), V(...c)), nav.isWalkable(a[0], a[2])]);
  }
  const randoms = [];
  for (let k = 0; k < 40; k++) {
    const c = [R(b.minX, b.maxX), 0, R(b.minZ, b.maxZ)];
    const radius = R(2, 9);
    const p = nav.randomPoint(V(...c), radius);
    randoms.push([c, radius, p ? [p.x, p.z] : null]);
  }
  const snaps = [];
  for (let k = 0; k < 60; k++) {
    const x = R(b.minX, b.maxX);
    const z = R(b.minZ, b.maxZ);
    const p = nav.nearestWalkable(x, z, 4);
    snaps.push([x, z, 4, p ? [p.x, p.z] : null]);
  }
  write('world.json', { about: about('src/physics.js filled with level.json colliders'), seed, rays, sight, ground, walks, paths, lines, randoms, snaps });
}

// --------------------------------------------------------------------------------------- enemy logic

export function goldenEnemyLogic(seed, write, about) {
  const rng = createRng(seed).fork('golden-logic');
  const R = (a, b) => q(a + (b - a) * rng.next());
  // The tables as the AI reads them on the default difficulty (base + boss overlay, config.json enemiesResolved.boss).
  const ai = { ...enemiesConfig.ai, ...enemiesConfig.difficulty.boss.ai };
  const goon = { ...enemiesConfig.goon, ...enemiesConfig.difficulty.boss.goon };

  // Tokens: a script of requests and releases at times; the answer of every request.
  const tokens = L.createTokens();
  const tokenScript = [];
  let now = 0;
  for (let k = 0; k < 200; k++) {
    now += R(0, 0.6);
    const op = q(rng.next()) < 0.7 ? 'request' : 'release';
    const type = q(rng.next()) < 0.5 ? 'goon' : 'buzzard';
    const alive = 1 + Math.floor(R(0, 9));
    const result = op === 'request' ? tokens.request(type, now, alive, ai) : (tokens.release(), null);
    tokenScript.push([op, type, now, alive, result, tokens.held]);
  }
  const sight = [];
  for (let k = 0; k < 120; k++) {
    const dist = R(0, 50);
    const dx = R(-1, 1);
    const dz = R(-1, 1);
    const yaw = R(-Math.PI, Math.PI);
    const engaged = q(rng.next()) < 0.3;
    sight.push([dist, dx, dz, yaw, engaged, L.inSight(dist, dx, dz, yaw, engaged, ai), L.inFov(yaw, dx, dz, ai.fov)]);
  }
  const accum = [];
  for (let k = 0; k < 60; k++) {
    const seen = R(0, 1);
    const vis = q(rng.next()) < 0.5;
    const tick = R(0.11, 0.19);
    const exp = R(0, 1);
    const dt = R(0, 0.05);
    const mode = ['patrol', 'investigate', 'search'][k % 3];
    accum.push([seen, vis, tick, exp, dt, mode, L.seenStep(seen, vis, tick, ai), L.exposureStep(exp, vis, dt, ai), L.reactionTime(goon.reaction, mode, ai)]);
  }
  const spread = [];
  for (let k = 0; k < 40; k++) {
    const e = R(-0.2, 1.2);
    const s = R(0, 7);
    const x = R(0.5, 1.5);
    spread.push([goon.spreadFar, goon.spreadNear, e, s, goon.spreadPerSpeed, x, L.aimSpread(goon.spreadFar, goon.spreadNear, e, s, goon.spreadPerSpeed, x)]);
  }
  const cost = [];
  const kinds = ['authored', 'random', 'arc'];
  for (let k = 0; k < 60; k++) {
    const c = { x: R(-20, 20), z: R(-20, 20), kind: kinds[k % 3], sight: q(rng.next()) < 0.7, cover: q(rng.next()) < 0.4 };
    const self = { x: R(-20, 20), z: R(-20, 20) };
    const player = { x: R(-5, 5), z: R(-5, 5) };
    const others = Array.from({ length: k % 4 }, () => ({ x: R(-20, 20), z: R(-20, 20), destX: R(-20, 20), destZ: R(-20, 20) }));
    const jitter = q(rng.next());
    cost.push([c, self, player, others, jitter, L.firePositionCost(c, self, player, others, others.length, jitter, goon.positionCost)]);
  }
  const follow = [];
  for (let k = 0; k < 40; k++) {
    const cap = R(0, 6);
    const err = R(0, 2);
    const rem = R(0, 5);
    follow.push([cap, err, rem, L.followSpeed(cap, err, rem, goon)]);
  }
  const rays = [];
  for (let k = 0; k < 90; k++) {
    const o = [R(-3, 3), R(0, 3), R(-3, 3)];
    const t = [R(-1, 1), R(0, 2), R(-1, 1)];
    const d = [t[0] - o[0], t[1] - o[1], t[2] - o[2]];
    const l = Math.hypot(...d);
    const u = d.map((x) => x / l);
    const sphere = L.raySphere(...o, ...u, 0, 1.6, 0, 0.155);
    const capsule = L.rayCapsule(...o, ...u, 0, 0.8, 0, 0.1, 1.5, 0.05, 0.27);
    const ellipsoid = L.rayEllipsoid(...o, ...u, 0, 1, 0, 0.5, 0.22);
    rays.push([o, u, Number.isFinite(sphere) ? sphere : -1, Number.isFinite(capsule) ? capsule : -1, Number.isFinite(ellipsoid) ? ellipsoid : -1]);
  }
  const upright = [];
  for (let k = 0; k < 60; k++) {
    const p = [R(-3, 3), R(0, 3), R(-3, 3)];
    const q = [R(-3, 3), R(0, 3), R(-3, 3)];
    upright.push([p, q, L.segmentHitsUpright(...p, ...q, 0, 0.1, 1.75, 0, 0.42)]);
  }
  const lead = [];
  for (let k = 0; k < 20; k++) {
    const s = [R(-10, 10), R(2, 8), R(-10, 10)];
    const t = [R(-10, 10), R(0, 2), R(-10, 10)];
    const v = [R(-5, 5), R(-1, 1), R(-5, 5)];
    const out = [0, 0, 0];
    const share = R(0, 1);
    L.leadPoint(...s, ...t, ...v, 70, share, out);
    lead.push([s, t, v, share, out]);
  }
  write('enemy_logic.json', { about: about('src/enemies/logic.js'), ai, tokens: tokenScript, sight, accum, spread, cost, follow, rays, upright, lead });
}

// --------------------------------------------------------------------------------------- enemy scenarios

/**
 * One fight in the block. `setup(E, P)` spawns; `script(frame, E, P)` moves the player and pokes the enemies.
 * Every frame records each enemy of the list and every event; the player is plain data (pos, eye, vel).
 */
function enemyScenario(level, seed, name, { frames, player, setup, script, dt = 1 / 60 }) {
  const events = createEvents();
  const log = [];
  let frame = -1;
  const G = {
    config: { enemies: enemiesConfig, flow: flowConfig, weapons: weaponsConfig, look: {} },
    events,
    rng: createRng(seed),
  };
  G.physics = blockPhysics(level, G);
  G.level = blockLevel(level);
  const P = {
    pos: V(...player.pos),
    eye: V(player.pos[0], player.pos[1] + 1.68, player.pos[2]),
    vel: V(0, 0, 0),
    alive: true,
    crouching: !!player.crouching,
    damage(amount, from, kind) {
      log.push([frame, 'player:damage', { amount, kind, from: from ? vec(from) : null }]);
    },
  };
  G.player = P;
  G.combat = {
    hitscan(o) {
      log.push([frame, 'hitscan', { origin: vec(o.origin), dir: vec(o.dir), range: o.range, damage: o.damage }]);
      return { point: o.origin.clone().addScaledVector(o.dir, 10) };
    },
    explode(o) {
      log.push([frame, 'explode', { pos: vec(o.pos), radius: o.radius, damage: o.damage, playerScale: o.playerScale }]);
    },
  };
  const E = createEnemies(G);
  for (const ev of ['enemy:spawn', 'enemy:alert', 'enemy:telegraph', 'enemy:fire', 'enemy:melee', 'enemy:hit', 'enemy:killed']) {
    events.on(ev, (e) => {
      const p = { id: e.enemy ? e.enemy.id : 0 };
      if (e.phase) p.phase = e.phase;
      if (e.dir) p.dir = vec(e.dir);
      if (e.part) p.part = e.part;
      if (e.damage !== undefined) p.damage = e.damage;
      if (e.duration !== undefined) p.duration = e.duration;
      log.push([frame, ev, p]);
    });
  }
  const spawns = [];
  const ctl = {
    spawn(type, pos, opts = {}) {
      const e = E.spawn(type, V(...pos), opts);
      spawns.push([frame, type, pos, opts.yaw !== undefined ? opts.yaw : null, !!opts.alerted, opts.target || null, e ? e.id : 0]);
      return e;
    },
    damage(id, amount, part, dir) {
      const e = E.list.find((x) => x.id === id);
      if (!e) return;
      log.push([frame, 'poke:damage', { id, amount, part, dir }]);
      E.damage(e, amount, { part, dir: dir ? V(...dir).normalize() : null, from: 'player', weapon: 'chopper' });
    },
    alert(pos, radius) {
      log.push([frame, 'poke:alert', { pos, radius }]);
      E.alert(V(...pos), radius);
    },
    hear(pos, radius) {
      log.push([frame, 'poke:hear', { pos, radius }]);
      E.hear(V(...pos), radius);
    },
    gunfire(pos) {
      log.push([frame, 'poke:gunfire', { pos }]);
      events.emit('weapon:fire', { pos: V(...pos) });
    },
    move(x, y, z, vx, vy, vz) {
      P.pos.set(x, y, z);
      P.eye.set(x, y + (P.crouching ? 1.15 : 1.68), z);
      P.vel.set(vx, vy, vz);
    },
    crouch(on) {
      P.crouching = on;
    },
    kill() {
      P.alive = false;
    },
  };
  frame = -1;
  setup(ctl);
  const rows = [];
  const players = [];
  for (frame = 0; frame < frames; frame++) {
    script(frame, ctl);
    players.push([P.pos.x, P.pos.y, P.pos.z, P.vel.x, P.vel.y, P.vel.z, P.crouching ? 1 : 0, P.alive ? 1 : 0, P.eye.x, P.eye.y, P.eye.z]);
    E.update(dt);
    const row = [];
    for (const e of [...E.list].sort((a, b) => a.id - b.id)) {
      row.push([e.id, e.type, e.mode, e.type === 'goon' ? e.sub : e.telegraph > 0 ? 'telegraph' : e.burstLeft > 0 ? 'burst' : '-', e.pos.x, e.pos.y, e.pos.z, e.yaw, e.hp, e.exposure, e.seen, e.alive ? 1 : 0]);
    }
    rows.push(row);
  }
  const d = E.debug();
  return { name, dt, frames, player, spawns, players, rows, events: log, final: { goons: d.goons, buzzards: d.buzzards, bodies: d.bodies, bolts: d.bolts, tokens: d.tokens }, doorways: d.doorways };
}

export function goldenEnemies(level, seed, write, about) {
  const start = level.playerStart.web.pos;
  const scenarios = [
    enemyScenario(level, seed, 'goon_engage', {
      frames: 720,
      player: { pos: [0, 0, 8] },
      setup: (c) => c.spawn('goon', [0, 0, -6], { yaw: Math.PI }),
      script: () => {},
    }),
    enemyScenario(level, seed, 'goon_rush', {
      frames: 360,
      player: { pos: [2, 0, 3] },
      setup: (c) => c.spawn('goon', [2, 0, 0.6], { yaw: Math.PI }),
      script: () => {},
    }),
    enemyScenario(level, seed, 'goon_patrol_hear_hit_kill', {
      frames: 900,
      player: { pos: [20, 0, 20] },
      setup: (c) => {
        c.spawn('goon', [8, 0, 18], {});
        c.spawn('goon', [-6, 0, 16], {});
      },
      script: (f, c) => {
        if (f === 120) c.gunfire([20, 1.5, 20]);
        if (f === 400) c.damage(1, 30, 'body', [-1, 0, 0]);
        if (f === 430) c.damage(1, 40, 'head', [-1, 0, 0]);
        if (f === 460) c.damage(1, 60, 'body', [-1, 0, 0]);
        if (f > 500) c.move(20 - (f - 500) * 0.0313, 0, 20, -1.878, 0, 0);
      },
    }),
    enemyScenario(level, seed, 'buzzard_engage', {
      frames: 720,
      player: { pos: [-10, 0, 12] },
      setup: (c) => c.spawn('buzzard', [-10, 5, 0], { yaw: Math.PI }),
      script: (f, c) => {
        if (f > 300 && f < 420) c.move(-10 + (f - 300) * 0.0517, 0, 12, 3.102, 0, 0);
        if (f === 420) c.move(-4, 0, 12, 0, 0, 0);
      },
    }),
    enemyScenario(level, seed, 'buzzard_deck_and_crash', {
      frames: 900,
      player: { pos: [5, 0, 1] },
      setup: (c) => c.spawn('buzzard', [20, 10, -20], { alerted: true }),
      script: (f, c) => {
        if (f === 600) c.damage(1, 30, 'body', [0, 0, 1]);
        if (f === 640) c.damage(1, 40, 'body', [0, 0, 1]);
      },
    }),
    enemyScenario(level, seed, 'squad', {
      frames: 1200,
      player: { pos: [start.x, start.y, start.z] },
      setup: (c) => {
        c.spawn('goon', [-20, 0.15, -2], { alerted: true });
        c.spawn('goon', [-14, 0, 14], { alerted: true });
        c.spawn('goon', [-30, 0, -9], {});
        c.spawn('buzzard', [-25, 7, 12], { alerted: true });
        c.spawn('buzzard', [-15, 8, -12], {});
      },
      script: (f, c) => {
        // Rule walks east along the north sidewalk, ducks, and comes back.
        if (f >= 200 && f < 500) c.move(start.x + (f - 200) * 0.0517, start.y, start.z, 3.102, 0, 0);
        if (f === 500) c.crouch(true);
        if (f === 700) c.crouch(false);
        if (f >= 700 && f < 900) c.move(start.x + 15 - (f - 700) * 0.0413, start.y, start.z, -2.478, 0, 0);
        if (f === 900) c.move(start.x + 7, start.y, start.z, 0, 0, 0);
        if (f === 1000) c.damage(4, 55, 'body', [0, 0, -1]);
      },
    }),
  ];
  write('enemies.json', { about: about('src/enemies.js, src/enemies/goon.js, buzzard.js, bolts.js on src/physics.js with level.json'), seed: enemiesConfig.seed, navSeed: seed, scenarios });
}

// --------------------------------------------------------------------------------------- flow rules

export function goldenFlowRules(level, seed, write, about) {
  const rng = createRng(seed).fork('golden-flow');
  const S = flowConfig.spawn.score;
  const sectors = [];
  for (let k = 0; k < 40; k++) {
    const dx = k === 0 ? 0 : q((rng.next() * 2 - 1) * 30);
    const dz = k === 0 ? 0 : q((rng.next() * 2 - 1) * 30);
    sectors.push([dx, dz, compassSector(dx, dz)]);
  }
  const scores = [];
  for (let k = 0; k < 40; k++) {
    const c = { distance: q(rng.next() * 50), hidden: q(rng.next()) < 0.5, usedAgo: q(rng.next()) < 0.3 ? Infinity : q(rng.next() * 12), random: q(rng.next()) };
    scores.push([c.distance, c.hidden, Number.isFinite(c.usedAgo) ? c.usedAgo : -1, c.random, spawnScore(c, S, flowConfig.spawn.far)]);
  }
  // pickSpawn over the level's points with recorded answers for hidden / usedAgo / random.
  const points = level.enemySpawns.points.map((p) => ({ index: p.index, pos: p.web.pos, type: p.type }));
  const picks = [];
  for (let k = 0; k < 30; k++) {
    const query = { x: q((rng.next() * 2 - 1) * 40), z: q((rng.next() * 2 - 1) * 30), minDistance: k % 3 === 0 ? flowConfig.spawn.patrolMinDistance : flowConfig.spawn.far, strict: k % 2 === 0 };
    const wanted = k % 4 === 3 ? 'air' : 'ground';
    const answers = [];
    query.hidden = (p) => {
      const h = q(rng.next()) < 0.5;
      answers.push(['hidden', p.index, h]);
      return h;
    };
    query.usedAgo = (p) => {
      const u = q(rng.next()) < 0.7 ? Infinity : q(rng.next() * 10);
      answers.push(['usedAgo', p.index, Number.isFinite(u) ? u : -1]);
      return u;
    };
    query.random = () => {
      const r = q(rng.next());
      answers.push(['random', -1, r]);
      return r;
    };
    const best = pickSpawn(points, wanted, query, S);
    picks.push({ q: { x: query.x, z: query.z, minDistance: query.minDistance, strict: query.strict }, wanted, answers, best: best ? best.index : -1 });
  }
  const mission = [];
  for (const [b, g] of [[0, 0], [2, 5], [3, 6], [4, 7], [5, 8], [1, 3], [2, 4], [0, 3], [3, 0]]) mission.push([b, g, missionOrder(b, g)]);
  const holdout = [];
  for (let n = 1; n <= 30; n++) {
    const w = holdoutWave(n, flowConfig.holdout);
    holdout.push({ ...w, killGoon: killScore('goon', n, flowConfig.holdout.score), killBuzzard: killScore('buzzard', n, flowConfig.holdout.score), waveClear: flowConfig.holdout.score.waveClear(n) });
  }
  const orders = [];
  for (const [t, b] of [[7, 3], [9, 4], [30, 8], [5, 5], [6, 0], [10, 1]]) orders.push([t, b, holdoutOrder(t, b)]);
  const pursuit = [];
  for (let k = 0; k < 20; k++) {
    const r = q(rng.next());
    pursuit.push([r, pursuitType(r, flowConfig.pursuit.buzzardShare)]);
  }
  const cards = [];
  const ratings = textConfig.ratings;
  for (let k = 0; k < 40; k++) {
    const run = { time: q(rng.next() * 600), reels: k % 4, total: 3, retries: k % 3 === 0 ? 1 : 0, wave: 0, score: q(rng.next() * 9000), kills: Math.floor(q(rng.next()) * 40), shots: k % 7 === 0 ? 0 : Math.floor(q(rng.next()) * 300), hits: 0 };
    run.hits = Math.floor(run.shots * q(rng.next()));
    const info = { mode: k % 2 ? 'holdout' : 'mission', difficulty: flowConfig.difficulties[k % 3], wavesCleared: k % 5, best: Math.floor(q(rng.next()) * 8000), newBest: k % 6 === 0, headshots: k % 4 };
    const c = cardData(run, info, flowConfig, ratings);
    cards.push({ run, info, card: { ...c, accuracy: c.accuracy === null ? -1 : c.accuracy }, accuracy: accuracy(run) === null ? -1 : accuracy(run) });
  }
  write('flow_rules.json', { about: about('src/game/spawn.js, waves.js, stats.js and config/flow.js'), sectors, scores, picks, mission, holdout, orders, pursuit, cards });
}
