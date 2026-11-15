// Combat resolution: hitscan ordering and damage, melee, explosions, stats.
// The world is the real physics module; enemies, explosives and the player are small fakes.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { createPhysics } from '../src/physics.js';
import { createCombat } from '../src/combat.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const EAST = V(1, 0, 0);
const HEAD_Y = 1.63;

function near(actual, expected, eps = 1e-6, label = '') {
  assert.ok(Math.abs(actual - expected) <= eps, `${label} expected ${expected} ± ${eps}, got ${actual}`);
}

function makeEvents() {
  const handlers = new Map();
  const log = [];
  return {
    log,
    on(name, fn) {
      handlers.set(name, [...(handlers.get(name) || []), fn]);
    },
    emit(name, payload) {
      log.push({ name, payload });
      for (const fn of handlers.get(name) || []) fn(payload);
    },
    named: (name) => log.filter((e) => e.name === name).map((e) => e.payload),
  };
}

/** Ray against a sphere: entry distance or Infinity. */
function raySphere(origin, dir, centre, radius) {
  const o = origin.clone().sub(centre);
  const b = o.dot(dir);
  const disc = b * b - (o.lengthSq() - radius * radius);
  if (disc < 0) return Infinity;
  const t = -b - Math.sqrt(disc);
  return t >= 0 ? t : Infinity;
}

/** Goons: a body sphere at chest height plus a head sphere. Buzzards: one sphere at pos. */
function makeEnemies(G) {
  const list = [];
  const volumes = (e) =>
    e.type === 'buzzard'
      ? [{ part: 'body', centre: e.pos.clone(), radius: e.radius }]
      : [
          { part: 'head', centre: V(e.pos.x, e.pos.y + HEAD_Y, e.pos.z), radius: 0.17 },
          { part: 'body', centre: V(e.pos.x, e.pos.y + 0.9, e.pos.z), radius: 0.45 },
        ];
  return {
    list,
    damaged: [],
    add(type, x, y, z, hp = 100) {
      const shape = type === 'goon' ? { radius: 0.35, height: 1.8 } : { radius: 0.45, height: 0.45 };
      const enemy = { id: list.length + 1, type, pos: V(x, y, z), alive: true, hp, maxHp: hp, ...shape };
      list.push(enemy);
      return enemy;
    },
    raycast(origin, dir, maxDist) {
      let best = null;
      for (const enemy of list) {
        if (!enemy.alive) continue;
        for (const v of volumes(enemy)) {
          const dist = raySphere(origin, dir, v.centre, v.radius);
          if (dist <= maxDist && (!best || dist < best.dist)) {
            const point = origin.clone().addScaledVector(dir, dist);
            best = { enemy, dist, point, normal: point.clone().sub(v.centre).normalize(), part: v.part };
          }
        }
      }
      return best;
    },
    damage(enemy, amount, info) {
      this.damaged.push({ enemy, amount, info });
      enemy.hp -= amount;
      if (enemy.hp > 0) return { killed: false };
      enemy.alive = false;
      G.events.emit('enemy:killed', { enemy, type: enemy.type, part: info.part });
      return { killed: true };
    },
  };
}

/** Explosives are colliders in the world list, exactly like the real ones. */
function makeExplosives(G) {
  const items = [];
  return {
    items,
    damaged: [],
    add(x, z, type = 'propane') {
      const item = { type, pos: V(x, 0, z), hp: 50, state: 'idle', box: null };
      item.box = G.physics.addBox({
        min: [x - 0.16, 0, z - 0.16],
        max: [x + 0.16, 0.6, z + 0.16],
        surface: 'metal',
        owner: item,
      });
      items.push(item);
      return item;
    },
    raycast(origin, dir, maxDist) {
      let best = null;
      for (const item of items) {
        if (item.state === 'gone') continue;
        const hit = new THREE.Ray(origin, dir).intersectBox(new THREE.Box3(item.box.min, item.box.max), V(0, 0, 0));
        if (!hit) continue;
        const dist = hit.distanceTo(origin);
        if (dist <= maxDist && (!best || dist < best.dist)) best = { item, dist, point: hit, normal: dir.clone().negate() };
      }
      return best;
    },
    damage(item, amount, from) {
      this.damaged.push({ item, amount, from });
    },
  };
}

function makePlayer(G) {
  return {
    pos: V(0, 0, 0),
    eye: V(0, 1.68, 0),
    crouching: false,
    alive: true,
    health: 100,
    hits: [],
    damage(amount, from, kind) {
      this.hits.push({ amount, from, kind });
      this.health -= amount;
      G.events.emit('player:hit', { amount, from, health: this.health, kind });
    },
  };
}

function setup() {
  const G = { events: makeEvents(), params: {} };
  G.physics = createPhysics(G);
  G.physics.setBounds({ minX: -50, maxX: 50, minZ: -50, maxZ: 50 });
  G.enemies = makeEnemies(G);
  G.explosives = makeExplosives(G);
  G.player = makePlayer(G);
  G.combat = createCombat(G);
  return G;
}

const shot = (G, origin, dir, extra = {}) =>
  G.combat.hitscan({ origin, dir, range: 300, damage: 26, from: 'player', weapon: 'chopper', headMult: 2.2, ...extra });

test('hitscan: an enemy in front of a wall is hit, an enemy behind it is not', () => {
  const G = setup();
  const wall = G.physics.addBox({ min: [10, 0, -5], max: [11, 3, 5], surface: 'brick' });
  const front = G.enemies.add('goon', 6, 0, 0);
  const behind = G.enemies.add('goon', 14, 0, 0);

  let res = shot(G, V(0, 0.9, 0), EAST);
  assert.equal(res.type, 'enemy');
  assert.equal(res.enemy, front);
  assert.equal(res.part, 'body');
  near(res.dist, 6 - 0.45);
  near(res.point.x, 5.55);
  near(res.normal.x, -1);
  assert.equal(res.surface, 'flesh');
  assert.equal(res.killed, false);
  assert.equal(front.hp, 74);
  assert.equal(behind.hp, 100);

  front.alive = false; // out of the way: now the wall is next
  res = shot(G, V(0, 0.9, 0), EAST);
  assert.equal(res.type, 'world');
  assert.equal(res.box, wall);
  assert.equal(res.surface, 'brick');
  near(res.dist, 10);
  assert.deepEqual(res.normal.toArray(), [-1, 0, 0]);
  assert.equal(res.enemy, null);
  assert.equal(behind.hp, 100, 'no shooting through cover');
  assert.equal(G.enemies.damaged.length, 1);
});

test('hitscan: nearest of enemy and explosive wins, and an explosive beats its own collider', () => {
  let G = setup();
  let tank = G.explosives.add(5, 0);
  let goon = G.enemies.add('goon', 9, 0, 0);
  let res = shot(G, V(0, 0.4, 0), EAST);
  assert.equal(res.type, 'explosive', 'tank in front of the goon');
  assert.equal(res.item, tank);
  assert.equal(res.box, tank.box);
  assert.equal(res.surface, 'metal');
  near(res.dist, 5 - 0.16);
  assert.deepEqual(G.explosives.damaged, [{ item: tank, amount: 26, from: 'player' }]);
  assert.equal(goon.hp, 100);
  assert.equal(G.combat.stats.hits, 0, 'an explosive is not a hit for accuracy');

  G = setup();
  goon = G.enemies.add('goon', 5, 0, 0);
  tank = G.explosives.add(9, 0);
  res = shot(G, V(0, 0.5, 0), EAST);
  assert.equal(res.type, 'enemy', 'goon in front of the tank');
  assert.equal(res.enemy, goon);
  assert.equal(G.explosives.damaged.length, 0);

  // A wall in front of both.
  G = setup();
  G.physics.addBox({ min: [2, 0, -5], max: [2.3, 3, 5] });
  G.explosives.add(5, 0);
  G.enemies.add('goon', 9, 0, 0);
  res = shot(G, V(0, 0.4, 0), EAST);
  assert.equal(res.type, 'world');
  assert.equal(G.explosives.damaged.length + G.enemies.damaged.length, 0);
});

test('hitscan: a round that stops on an explosive\'s collider hits the explosive, whatever its raycast says', () => {
  // A module that tests a tighter shape than its collider: here, one that never reports a hit at all.
  let G = setup();
  let tank = G.explosives.add(5, 0);
  G.explosives.raycast = () => null;
  let res = shot(G, V(0, 0.4, 0), EAST);
  assert.equal(res.type, 'explosive');
  assert.equal(res.item, tank);
  assert.equal(res.box, tank.box);
  near(res.dist, 5 - 0.16);
  assert.deepEqual(res.normal.toArray(), [-1, 0, 0]);
  assert.deepEqual(G.explosives.damaged, [{ item: tank, amount: 26, from: 'player' }]);
  assert.equal(G.events.named('impact').length, 1);

  // The collider may also be tied to the item by `owner` alone, and an enemy round follows the same rule.
  G = setup();
  tank = G.explosives.add(5, 0);
  const collider = tank.box;
  tank.box = null;
  delete G.explosives.raycast;
  const shooter = G.enemies.add('goon', 12, 0, 0);
  res = G.combat.hitscan({ origin: V(11.5, 0.4, 0), dir: V(-1, 0, 0), range: 200, damage: 30, from: shooter });
  assert.equal(res.type, 'explosive');
  assert.equal(res.item, tank);
  assert.equal(res.box, collider);
  assert.deepEqual(G.explosives.damaged, [{ item: tank, amount: 9, from: shooter }]);

  // Once it has blown the leftover collider is plain world again, and an enemy in front still comes first.
  tank.state = 'gone';
  res = shot(G, V(0, 0.4, 0), EAST);
  assert.equal(res.type, 'world');
  tank.state = 'idle';
  tank.box = collider;
  const goon = G.enemies.add('goon', 3, 0, 0);
  res = shot(G, V(0, 0.9, 0), EAST);
  assert.equal(res.type, 'enemy');
  assert.equal(res.enemy, goon);
});

test('hitscan: a miss reports the end of the ray; the world result carries surface and box', () => {
  const G = setup();
  let res = shot(G, V(0, 1.5, 0), EAST, { range: 120 });
  assert.equal(res.type, 'none');
  assert.equal(res.dist, 120);
  assert.deepEqual(res.point.toArray(), [120, 1.5, 0]);
  assert.equal(G.events.named('impact').length, 0);

  res = shot(G, V(0, 1.5, 0), V(1, -1, 0)); // into the street
  assert.equal(res.type, 'world');
  assert.equal(res.box, null);
  assert.equal(res.surface, 'asphalt');
  near(res.point.y, 0);
  const [impact] = G.events.named('impact');
  assert.equal(impact.from, 'player');
  assert.equal(impact.surface, 'asphalt');
  assert.equal(impact.enemy, null);
  assert.equal(impact.point, res.point);
  assert.deepEqual(impact.normal.toArray(), [0, 1, 0]);
  near(impact.dir.length(), 1, 1e-12, 'direction is normalised');
});

test('hitscan: head hits are multiplied; hits, kills and headshots are counted; events fire', () => {
  const G = setup();
  const goon = G.enemies.add('goon', 8, 0, 0, 100);
  const stats = G.combat.stats;

  let res = shot(G, V(0, HEAD_Y, 0), EAST);
  assert.equal(res.part, 'head');
  near(G.enemies.damaged[0].amount, 26 * 2.2);
  assert.deepEqual(
    { ...G.enemies.damaged[0].info, point: null, dir: null },
    { point: null, dir: null, part: 'head', from: 'player', weapon: 'chopper' },
  );
  assert.equal(res.killed, false);
  assert.deepEqual({ ...stats }, { shots: 0, hits: 1, kills: 0, headshots: 0, damageTaken: 0 }, 'shots belong to the weapon');

  res = shot(G, V(0, HEAD_Y, 0), EAST);
  assert.equal(res.killed, true);
  assert.equal(stats.hits, 2);
  assert.equal(stats.kills, 1);
  assert.equal(stats.headshots, 1, 'the killing blow landed on the head');

  const marks = G.events.named('player:hitEnemy');
  assert.equal(marks.length, 2);
  assert.equal(marks[0].enemy, goon);
  assert.equal(marks[0].part, 'head');
  assert.equal(marks[0].killed, false);
  near(marks[0].damage, 57.2);
  assert.equal(marks[0].weapon, 'chopper');
  assert.equal(marks[1].killed, true);
  const impacts = G.events.named('impact');
  assert.equal(impacts.length, 2);
  assert.equal(impacts[0].enemy, goon);
  assert.equal(impacts[0].surface, 'flesh');
  assert.equal(impacts[0].from, 'player');

  // A body kill is a kill but not a headshot; a buzzard is 'drone' and has no head bonus.
  const second = G.enemies.add('goon', 8, 0, 4, 20);
  shot(G, V(0, 0.9, 4), EAST);
  assert.equal(second.alive, false);
  assert.equal(stats.kills, 2);
  assert.equal(stats.headshots, 1);
  const drone = G.enemies.add('buzzard', 8, 6, 8, 55);
  res = shot(G, V(0, 6, 8), EAST);
  assert.equal(res.surface, 'drone');
  assert.equal(drone.hp, 29);

  G.combat.reset();
  assert.deepEqual({ ...stats }, { shots: 0, hits: 0, kills: 0, headshots: 0, damageTaken: 0 });
  assert.equal(G.combat.stats, stats, 'reset keeps the same object');
});

test('hitscan: enemy shots hit the player cylinder, never other enemies', () => {
  const G = setup();
  const shooter = G.enemies.add('goon', 12, 0, 0);
  const bystander = G.enemies.add('goon', 6, 0, 0); // right in the line of fire
  const muzzle = V(11.5, 1.35, 0);
  const west = V(-1, 0, 0);

  const res = G.combat.hitscan({ origin: muzzle, dir: west, range: 200, damage: 6, from: shooter, weapon: 'goon' });
  assert.equal(res.type, 'player');
  near(res.dist, 11.5 - 0.38);
  near(res.normal.x, 1);
  assert.equal(bystander.hp, 100);
  assert.equal(G.enemies.damaged.length, 0);
  assert.equal(G.player.hits.length, 1);
  assert.equal(G.player.hits[0].amount, 6);
  assert.equal(G.player.hits[0].kind, 'bullet');
  assert.ok(G.player.hits[0].from.equals(muzzle) && G.player.hits[0].from !== muzzle, 'from is a copy of the muzzle position');
  assert.equal(G.combat.stats.damageTaken, 6);
  assert.equal(G.combat.stats.hits, 0);
  assert.equal(G.events.named('impact').length, 0, 'the player is not an impact surface');
  assert.equal(G.events.named('player:hitEnemy').length, 0);

  // A near miss carries on to the world.
  const wide = G.combat.hitscan({ origin: V(11.5, 1.35, 0.5), dir: west, range: 200, damage: 6, from: shooter });
  assert.equal(wide.type, 'none');
  assert.equal(G.player.hits.length, 1);
});

test('hitscan: crouching lowers the player target; cover and death stop the shot', () => {
  const G = setup();
  const shooter = G.enemies.add('goon', 12, 0, 0);
  const fire = (y, dir = V(-1, 0, 0)) =>
    G.combat.hitscan({ origin: V(11.5, y, 0), dir, range: 200, damage: 6, from: shooter }).type;

  assert.equal(fire(1.5), 'player', 'standing: 1.5 m is inside the body');
  assert.equal(fire(1.85), 'none', 'over the head');
  G.player.crouching = true;
  assert.equal(fire(1.5), 'none', 'crouched: the same shot passes overhead');
  assert.equal(fire(1.0), 'player');
  G.player.crouching = false;

  // Straight down onto the head: the top cap.
  const down = G.combat.hitscan({ origin: V(0.1, 5, 0), dir: V(0, -1, 0), range: 50, damage: 1, from: shooter });
  assert.equal(down.type, 'player');
  near(down.dist, 5 - 1.8);
  assert.deepEqual(down.normal.toArray(), [0, 1, 0]);
  // A muzzle inside the body still hits.
  assert.equal(G.combat.hitscan({ origin: V(0.2, 1, 0), dir: V(1, 0, 0), range: 50, damage: 1, from: shooter }).dist, 0);

  G.physics.addBox({ min: [5, 0, -2], max: [5.5, 1.2, 2], surface: 'concrete' });
  assert.equal(fire(1.0), 'world', 'low cover stops a low shot');
  assert.equal(fire(1.5), 'player', 'but not one over the top');

  G.player.alive = false;
  assert.equal(fire(1.5), 'none', 'a dead player is not a target');
});

test('hitscan: an enemy round does a fixed small damage to an explosive', () => {
  const G = setup();
  const shooter = G.enemies.add('goon', 12, 0, 0);
  const tank = G.explosives.add(6, 0);
  const res = G.combat.hitscan({ origin: V(11.5, 0.4, 0), dir: V(-1, 0, 0), range: 200, damage: 30, from: shooter });
  assert.equal(res.type, 'explosive');
  assert.deepEqual(G.explosives.damaged, [{ item: tank, amount: 9, from: shooter }]);
  assert.equal(G.events.named('impact')[0].from, 'enemy');
  assert.equal(G.player.hits.length, 0);

  G.config = { weapons: { common: { explosiveHitFromEnemy: 4 } } };
  G.combat.hitscan({ origin: V(11.5, 0.4, 0), dir: V(-1, 0, 0), range: 200, damage: 30, from: shooter });
  assert.equal(G.explosives.damaged[1].amount, 4, 'taken from the config when present');
});

test('melee: nearest enemy inside reach and cone, with line of sight', () => {
  const G = setup();
  const cone = (50 * Math.PI) / 180;
  const strike = (dir = EAST) => G.combat.melee({ origin: V(0, 1.6, 0), dir, reach: 2.3, cone, damage: 60 });

  const far = G.enemies.add('goon', 3.0, 0, 0, 100); // surface 2.65 m away: out of reach
  assert.equal(strike().type, 'none');
  far.pos.x = 2.4;
  const close = G.enemies.add('goon', 1.5, 0, 0.3, 100);

  let res = strike();
  assert.equal(res.type, 'enemy');
  assert.equal(res.enemy, close, 'the nearer of the two');
  assert.equal(res.part, 'body');
  near(res.dist, Math.hypot(1.5, 0.3) - 0.35, 1e-9);
  assert.equal(close.hp, 40);
  assert.equal(far.hp, 100);
  assert.deepEqual(
    { part: G.enemies.damaged[0].info.part, from: G.enemies.damaged[0].info.from, weapon: G.enemies.damaged[0].info.weapon },
    { part: 'body', from: 'player', weapon: 'melee' },
  );
  assert.equal(G.events.named('player:hitEnemy')[0].weapon, 'melee');
  assert.equal(G.events.named('impact').length, 1);

  res = strike();
  assert.equal(res.killed, true);
  assert.equal(G.combat.stats.kills, 1, 'a melee kill is a kill');
  assert.equal(G.combat.stats.hits, 0, 'but a strike is not a hit for accuracy');
  assert.equal(G.combat.stats.headshots, 0);

  // Facing away, or 60° off to the side: nothing.
  assert.equal(strike(V(-1, 0, 0)).type, 'none');
  assert.equal(strike(V(Math.cos(1.05), 0, Math.sin(1.05))).type, 'none');
  // 20° off still lands (the cone is 25° either side, plus the body's width).
  assert.equal(strike(V(Math.cos(0.35), 0, Math.sin(0.35))).enemy, far);

  // Behind a wall: the strike reports the wall instead.
  G.physics.addBox({ min: [1, 0, -2], max: [1.2, 3, 2], surface: 'wood' });
  res = strike();
  assert.equal(res.type, 'world');
  assert.equal(res.surface, 'wood');
  near(res.dist, 1);
  assert.equal(far.hp, 40);
});

test('explode: damage falls off linearly with distance and stops at the radius', () => {
  const G = setup();
  const radius = 6.5;
  // Body centres sit 0.9 m up; put the blast at the same height so distances are plain.
  const at2 = G.enemies.add('goon', 2, 0, 0, 1000);
  const at5 = G.enemies.add('goon', 0, 0, 5, 1000);
  const edge = G.enemies.add('goon', -6.4, 0, 0, 1000);
  const outside = G.enemies.add('goon', 0, 0, -6.6, 1000);
  const drone = G.enemies.add('buzzard', 0, 3.9, 0, 1000); // 3 m straight up
  const pos = V(0, 0.9, 0);
  G.combat.explode({ pos, radius, damage: 170, source: 'test' });

  near(1000 - at2.hp, 170 * (1 - 2 / radius), 1e-9);
  near(1000 - at5.hp, 170 * (1 - 5 / radius), 1e-9);
  near(1000 - edge.hp, 170 * (1 - 6.4 / radius), 1e-9);
  assert.equal(outside.hp, 1000);
  near(1000 - drone.hp, 170 * (1 - 3 / radius), 1e-9);
  const info = G.enemies.damaged.find((d) => d.enemy === at2).info;
  assert.equal(info.from, 'blast');
  assert.equal(info.weapon, 'blast');
  assert.equal(info.part, 'body');
  near(info.dir.x, 1);
  assert.equal(G.combat.stats.hits, 0, 'blast damage is not a hit for accuracy');

  const [boom] = G.events.named('explosion');
  assert.deepEqual(boom.pos.toArray(), [0, 0.9, 0]);
  assert.notEqual(boom.pos, pos);
  assert.equal(boom.radius, radius);
  assert.equal(boom.size, 'big');
  assert.equal(boom.source, 'test');
});

test('explode: needs line of sight; the player takes the scaled share', () => {
  const G = setup();
  G.physics.addBox({ min: [2, 0, -3], max: [2.4, 3, 3] });
  const shielded = G.enemies.add('goon', 4, 0, 0, 100);
  const exposed = G.enemies.add('goon', -4, 0, 0, 90); // takes about 98
  G.player.pos.set(0, 0, 3);
  G.combat.explode({ pos: V(0, 1, 0), radius: 7.5, damage: 210, playerScale: 0.5, source: null });

  assert.equal(shielded.hp, 100, 'the wall takes it');
  assert.equal(exposed.alive, false);
  assert.equal(G.combat.stats.kills, 1, 'a blast kill is a kill');
  assert.equal(G.player.hits.length, 1);
  near(G.player.hits[0].amount, 210 * 0.5 * (1 - 3 / 7.5), 1e-9);
  assert.equal(G.player.hits[0].kind, 'blast');
  assert.deepEqual(G.player.hits[0].from.toArray(), [0, 1, 0]);
  near(G.combat.stats.damageTaken, 63, 1e-9);

  // Behind the wall the player is safe too; a small blast is announced as small.
  G.player.pos.set(4, 0, 1);
  G.combat.explode({ pos: V(0, 1, 0), radius: 3, damage: 30 });
  assert.equal(G.player.hits.length, 1);
  assert.equal(G.events.named('explosion')[1].size, 'small');
  assert.equal(G.combat.explode({ pos: V(0, 1, 0), radius: 3, damage: 30, size: 'big' }), undefined);
  assert.equal(G.events.named('explosion')[2].size, 'big');
});

test('explode: chains to other explosives, skips the source and anything that is gone', () => {
  const G = setup();
  const source = G.explosives.add(0, 0);
  const neighbour = G.explosives.add(3, 0);
  const spent = G.explosives.add(0, 3);
  const distant = G.explosives.add(0, -9);
  const hidden = G.explosives.add(-3, 0);
  spent.state = 'gone';
  G.physics.addBox({ min: [-1.6, 0, -2], max: [-1.4, 3, 2] }); // between the blast and `hidden`
  G.player.alive = false;

  G.combat.explode({ pos: V(0, 0.3, 0), radius: 6.5, damage: 170, source });
  assert.equal(G.explosives.damaged.length, 1);
  const hit = G.explosives.damaged[0];
  assert.equal(hit.item, neighbour, "its own collider does not shield it, the source's does not either");
  assert.equal(hit.from, 'blast');
  near(hit.amount, 170 * (1 - 3 / 6.5), 1e-9);
  assert.ok(![source, spent, distant, hidden].includes(hit.item));
});

test('stats: damageTaken follows every player:hit, whoever caused it', () => {
  const G = setup();
  G.events.emit('player:hit', { amount: 12, from: null, health: 88, kind: 'fall' });
  G.events.emit('player:hit', { amount: 7.5, from: V(1, 2, 3), health: 80.5, kind: 'bolt' });
  assert.equal(G.combat.stats.damageTaken, 19.5);
});

test('robustness: missing or half-built modules never make combat throw', () => {
  const G = { events: makeEvents(), params: {} };
  G.physics = createPhysics(G);
  G.physics.addBox({ min: [5, 0, -1], max: [6, 2, 1] });
  G.combat = createCombat(G);

  let res = G.combat.hitscan({ origin: V(0, 1, 0), dir: EAST });
  assert.equal(res.type, 'world');
  res = G.combat.hitscan({ origin: V(0, 1, 0), dir: EAST, from: {}, damage: 5 });
  assert.equal(res.type, 'world');
  assert.equal(G.combat.melee({ origin: V(0, 1, 0), dir: EAST }).type, 'none');
  G.combat.explode({ pos: V(0, 1, 0), radius: 5, damage: 100 });

  // Stubs that only expose part of the API.
  G.enemies = { list: [{ type: 'goon', pos: V(2, 0, 0), alive: true, radius: 0.35, height: 1.8 }] };
  G.explosives = { items: [{ type: 'propane', pos: V(1, 0, 1), state: 'idle' }] };
  G.player = { pos: V(0, 0, 0), alive: true };
  assert.equal(G.combat.hitscan({ origin: V(0, 1, 0), dir: EAST }).type, 'world');
  assert.equal(G.combat.melee({ origin: V(0, 1, 0), dir: EAST }).type, 'enemy');
  G.combat.explode({ pos: V(0, 1, 0), radius: 5, damage: 100 });
  assert.equal(G.combat.hitscan({ origin: V(3, 1, 0), dir: V(-1, 0, 0), from: {}, damage: 5 }).type, 'player');

  // No event bus at all.
  const bare = { physics: G.physics };
  assert.equal(createCombat(bare).hitscan({ origin: V(0, 1, 0), dir: EAST }).type, 'world');
});
