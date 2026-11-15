// The gameplay stubs (player, weapon, enemies, explosives) running on the real physics and combat
// modules with a scripted input: the same loop order as main.js, no browser needed.
// They run on their built-in defaults here (no G.config), which is also the path a broken config takes.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { createCombat } from '../src/combat.js';
import { createEvents } from '../src/core/events.js';
import { createRng } from '../src/core/rng.js';
import { createPhysics } from '../src/physics.js';
import { createEnemies } from '../src/stubs/enemies.js';
import { createExplosives } from '../src/stubs/explosives.js';
import { createPlayer } from '../src/stubs/player.js';
import { createWeapon } from '../src/stubs/weapon.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const DT = 1 / 60;
const EAST = -Math.PI / 2; // yaw that looks toward +X

function near(actual, expected, eps, label = '') {
  assert.ok(Math.abs(actual - expected) <= eps, `${label} expected ${expected} ± ${eps}, got ${actual}`);
}

/** Scripted stand-in for G.input with the members the stubs read. */
function makeInput() {
  const held = new Set();
  const edges = new Set();
  return {
    move: { x: 0, y: 0 },
    look: { dx: 0, dy: 0 },
    down: (a) => held.has(a),
    pressed: (a) => edges.has(a),
    released: () => false,
    hold(a) {
      held.add(a);
      edges.add(a);
    },
    release: (a) => held.delete(a),
    endFrame() {
      edges.clear();
      this.look.dx = this.look.dy = 0;
    },
  };
}

function setup({ explosives = [], build } = {}) {
  const events = createEvents();
  const count = {};
  const last = {};
  const G = {
    THREE,
    params: {},
    events,
    rng: createRng(1994),
    time: { t: 0, dt: DT, frame: 0 },
    input: makeInput(),
    scene: new THREE.Scene(),
    camera: new THREE.PerspectiveCamera(74, 16 / 9, 0.08, 700),
    render: { post: { damage: 0, lowHealth: 0, ads: 0 } },
    fx: { tracers: 0, tracer() { this.tracers++; } },
    level: { playerStart: { pos: V(0, 0, 0), yaw: EAST }, explosives, enemySpawns: [] },
    count,
    last,
  };
  for (const name of [
    'player:step', 'player:jump', 'player:land', 'player:hit', 'player:dead',
    'weapon:fire', 'weapon:reload', 'weapon:dry', 'weapon:melee',
    'enemy:spawn', 'enemy:alert', 'enemy:telegraph', 'enemy:fire', 'enemy:hit', 'enemy:killed',
    'explosive:lit', 'explosive:blast', 'explosion', 'impact', 'player:hitEnemy',
  ]) {
    events.on(name, (e) => {
      count[name] = (count[name] || 0) + 1;
      last[name] = e;
    });
  }
  G.physics = createPhysics(G);
  G.physics.setBounds({ minX: -46, maxX: 46, minZ: -34, maxZ: 34 });
  if (build) build(G.physics);
  // Boot order of the modules under test (CONTRACT section 3).
  G.player = createPlayer(G);
  G.combat = createCombat(G);
  G.explosives = createExplosives(G);
  G.weapon = createWeapon(G);
  G.enemies = createEnemies(G);
  G.frames = (n, each) => {
    for (let i = 0; i < n; i++) {
      G.time.t += DT;
      G.time.frame++;
      G.player.update(DT);
      G.weapon.update(DT);
      G.enemies.update(DT);
      G.explosives.update(DT);
      G.input.endFrame();
      if (each) each(i);
    }
  };
  return G;
}

/** Points the player's view at a world position. */
function lookAt(G, target) {
  G.frames(1); // refresh the eye in case the player was just moved
  const d = target.clone().sub(G.player.eye).normalize();
  G.player.yaw = Math.atan2(-d.x, -d.z);
  G.player.pitch = Math.asin(d.y);
  G.frames(1);
}

test('player stub: walks, is stopped by a wall, sprints, jumps one metre, crouches', () => {
  const G = setup({ build: (p) => p.addBox({ min: [10, 0, -5], max: [10.3, 3, 5], surface: 'brick' }) });
  const p = G.player;
  assert.deepEqual(p.pos.toArray(), [0, 0, 0]);
  near(p.forward.x, 1, 1e-9, 'facing east');
  assert.deepEqual(G.camera.position.toArray(), [0, 1.68, 0]);

  G.input.move.y = 1;
  G.frames(60);
  near(p.speed, 3.8, 1e-9, 'walk speed');
  G.frames(180);
  near(p.pos.x, 10 - 0.32, 1e-3, 'held at the wall');
  near(p.pos.z, 0, 1e-9);
  near(p.speed, 0, 1e-9, 'pressed against the wall');
  assert.ok(G.count['player:step'] >= 5, 'footsteps on the way');
  assert.equal(G.last['player:step'].surface, 'asphalt');

  // Turn round and sprint.
  p.yaw = Math.PI / 2;
  G.input.hold('sprint');
  G.frames(60);
  assert.equal(p.sprinting, true);
  near(p.speed, 6.4, 1e-9, 'sprint speed');
  near(G.camera.fov, 80, 0.5, 'sprint widens the view');
  G.input.release('sprint');
  G.input.move.y = 0;
  G.frames(30);
  assert.equal(p.speed, 0, 'stops without input');

  // Jump: 1 m apex, one jump event, one landing.
  let apex = 0;
  G.input.hold('jump');
  G.frames(60, () => {
    apex = Math.max(apex, p.pos.y);
  });
  G.input.release('jump');
  near(apex, 1.0, 0.02, 'jump apex');
  assert.equal(G.count['player:jump'], 1);
  assert.equal(G.count['player:land'], 1);
  assert.ok(G.last['player:land'].speed > 5 && G.last['player:land'].speed < 7);
  assert.equal(p.onGround, true);
  assert.equal(p.health, 100, 'a jump does not hurt');

  // Crouch lowers the eye; the camera follows.
  G.input.hold('crouch');
  G.frames(40);
  assert.equal(p.crouching, true);
  near(p.eye.y, 1.05, 0.01);
  near(G.camera.position.y, 1.05, 0.01);
  G.input.release('crouch');
  G.frames(40);
  assert.equal(p.crouching, false);
  near(p.eye.y, 1.68, 0.01);
});

test('player stub: climbs stairs, stays crouched under a low beam, takes fall damage', () => {
  const G = setup({
    build(p) {
      for (let i = 0; i < 11; i++) p.addBox({ min: [3 + i * 0.3, 0, -1], max: [3.3 + i * 0.3, (i + 1) * (2.8 / 11), 1], surface: 'wood' });
      p.addBox({ min: [6.3, 2.6, -1], max: [12, 2.8, 1], surface: 'wood' }); // deck
      p.addBox({ min: [-6, 1.3, -1], max: [-3, 2, 1] }); // low beam to the west
    },
  });
  const p = G.player;
  G.input.move.y = 1;
  G.frames(150);
  near(p.pos.y, 2.8, 1e-9, 'on the deck');
  assert.equal(p.surface, 'wood');
  assert.equal(G.count['player:land'] || 0, 0, 'never left the ground on the way up');

  // Off the end of the deck: a 2.8 m drop lands without damage, a 9 m one hurts.
  G.frames(120);
  assert.equal(p.pos.y, 0);
  assert.equal(G.count['player:land'], 1);
  assert.equal(p.health, 100);
  p.pos.set(20, 9, 0);
  p.vel.set(0, 0, 0);
  G.input.move.y = 0;
  G.frames(90);
  assert.equal(p.pos.y, 0);
  near(p.health, 100 - (Math.sqrt(2 * 21 * 9) - 13) * 7, 3, 'fall damage from 9 m');
  assert.equal(G.last['player:hit'].kind, 'fall');

  // Under the beam there is no room to stand: releasing crouch keeps the player down until clear.
  p.pos.set(-1.5, 0, 0);
  p.yaw = Math.PI / 2; // west
  G.input.hold('crouch');
  G.input.move.y = 1;
  G.frames(80);
  assert.ok(p.pos.x < -3.2 && p.pos.x > -5.8, `under the beam at x = ${p.pos.x.toFixed(2)}`);
  G.input.release('crouch');
  G.frames(5);
  assert.equal(p.crouching, true, 'no headroom');
  G.frames(120);
  assert.ok(p.pos.x < -6.4);
  assert.equal(p.crouching, false, 'stood up once clear');
});

test('weapon + enemies stubs: shooting a dummy, head multiplier, kill, reload', () => {
  const G = setup();
  const goon = G.enemies.spawn('goon', V(10, 0, 0));
  assert.equal(goon.type, 'goon');
  assert.equal(goon.hp, 110);
  assert.equal(goon.radius, 0.35);
  assert.equal(goon.height, 1.8);
  assert.equal(goon.state, 'patrol');
  assert.equal(goon.object.visible, true);
  assert.equal(G.enemies.aliveCount(), 1);
  assert.equal(G.enemies.countByType('goon'), 1);
  near(G.enemies.nearestDistance(), 10, 1e-9);

  // Eye level is head level: the crosshair is on the head.
  assert.equal(G.enemies.aimTarget(G.player.eye, G.player.forward, 60), true);
  const sight = G.enemies.raycast(G.player.eye, G.player.forward, 60);
  assert.equal(sight.enemy, goon);
  assert.equal(sight.part, 'head');
  near(sight.dist, 10 - 0.17, 0.02);

  G.input.hold('fire');
  G.frames(10); // two rounds at 12 per second
  assert.equal(G.weapon.state, 'firing');
  G.frames(20);
  G.input.release('fire');
  assert.equal(goon.alive, false, 'two head hits at 57.2 kill 110 hp');
  assert.equal(G.count['enemy:killed'], 1);
  assert.equal(G.last['enemy:killed'].part, 'head');
  assert.equal(G.last['enemy:killed'].byPlayer, true);
  assert.equal(G.last['enemy:killed'].weapon, 'chopper');
  const stats = G.combat.stats;
  assert.equal(stats.shots, 6, '0.5 s of automatic fire');
  assert.equal(stats.hits, 2, 'the dead dummy stops counting');
  assert.equal(stats.kills, 1);
  assert.equal(stats.headshots, 1);
  assert.equal(G.weapon.mag, 24);
  assert.equal(G.fx.tracers, 6);
  assert.equal(G.count['weapon:fire'], 6);
  assert.equal(G.last['weapon:fire'].weapon, 'chopper');
  assert.equal(G.enemies.aliveCount(), 0);
  assert.equal(G.enemies.list.length, 1, 'still listed while it lies there');
  G.frames(180);
  assert.equal(G.enemies.list.length, 0, 'then retired');

  // Reload tops the magazine up from the reserve.
  G.input.hold('reload');
  G.frames(1);
  G.input.release('reload');
  assert.equal(G.weapon.state, 'reloading');
  assert.equal(G.weapon.cue, 'reloading');
  G.frames(150);
  assert.equal(G.weapon.mag, 30);
  assert.equal(G.weapon.reserve, 144);
  assert.equal(G.weapon.state, 'idle');
  assert.equal(G.count['weapon:reload'], 2, 'start and done');

  // Empty magazine and no reserve: a dry click and the 'empty' cue.
  G.weapon.mag = 0;
  G.weapon.reserve = 0;
  G.input.hold('fire');
  G.frames(2);
  G.input.release('fire');
  assert.equal(G.count['weapon:dry'], 1);
  assert.equal(G.weapon.cue, 'empty');
  G.weapon.addReserve(90, 240);
  assert.equal(G.weapon.reserve, 90);
  G.weapon.reset();
  assert.equal(G.weapon.mag, 30);
  assert.equal(G.weapon.reserve, 150);
});

test('enemies stub: dummies notice the player, shoot back, and health regenerates', () => {
  const G = setup({ build: (p) => p.addBox({ min: [-8, 0, -1], max: [-7.6, 3, 1] }) });
  const p = G.player;
  p.regen.delay = 2;
  p.regen.rate = 50;
  const seen = G.enemies.spawn('goon', V(12, 0, 0));
  const hidden = G.enemies.spawn('goon', V(-12, 0, 0)); // behind the wall
  G.frames(90);
  assert.equal(seen.state, 'engage', 'noticed after a moment in view');
  assert.equal(hidden.state, 'patrol');
  assert.equal(G.count['enemy:alert'], 1);
  assert.equal(G.last['enemy:alert'].enemy, seen);

  let lowest = 100;
  G.frames(60 * 25, () => {
    lowest = Math.min(lowest, p.health);
  });
  assert.ok(G.count['enemy:telegraph'] >= 4, 'a warning before each shot');
  assert.equal(G.count['enemy:fire'], G.count['enemy:telegraph']);
  assert.equal(G.last['enemy:fire'].type, 'goon');
  assert.ok(G.count['player:hit'] >= 2, 'some of the shots land');
  assert.equal(G.last['player:hit'].kind, 'bullet');
  assert.equal(G.last['player:hit'].amount, 6);
  assert.ok(lowest < 100 && lowest > 40, `weak fire: lowest health ${lowest}`);
  assert.equal(G.combat.stats.damageTaken, G.count['player:hit'] * 6);
  assert.equal(hidden.state, 'patrol', 'no line of sight, no fight');

  // Behind cover the health comes back.
  G.enemies.clear();
  assert.equal(G.enemies.list.length, 0);
  assert.equal(seen.object.visible, false);
  G.frames(60 * 5);
  assert.equal(p.health, 100);

  // Gunfire and alert() wake dummies up; damage does too.
  const a = G.enemies.spawn('goon', V(-12, 0, 0));
  const b = G.enemies.spawn('buzzard', V(-20, 6, 10));
  const c = G.enemies.spawn('goon', V(30, 0, -30), { alerted: true });
  assert.equal(c.state, 'engage');
  G.enemies.alert(V(-12, 0, 2), 5);
  assert.equal(a.state, 'engage');
  assert.equal(b.state, 'patrol');
  assert.deepEqual(G.enemies.damage(b, 5, { part: 'body', from: 'player' }), { killed: false });
  assert.equal(b.state, 'engage');
  assert.equal(b.hp, 50);
});

test('enemies stub: pools cap at 12 goons and 8 buzzards; a shot-down buzzard bursts', () => {
  const G = setup();
  G.player.invulnerable = true;
  const goons = [];
  for (let i = 0; i < 12; i++) goons.push(G.enemies.spawn('goon', V(-40 + i * 2, 0, 30)));
  assert.ok(goons.every(Boolean));
  assert.equal(G.enemies.spawn('goon', V(0, 0, 30)), null, 'thirteenth goon');
  for (let i = 0; i < 8; i++) assert.ok(G.enemies.spawn('buzzard', V(-40 + i * 3, 8, -30)));
  assert.equal(G.enemies.spawn('buzzard', V(0, 8, -30)), null, 'ninth buzzard');
  assert.equal(G.enemies.spawn('turret', V(0, 0, 0)), null, 'unknown type');
  assert.equal(G.enemies.aliveCount(), 20);
  assert.equal(G.enemies.countByType('buzzard'), 8);
  assert.equal(G.count['enemy:spawn'], 20);
  assert.equal(new Set(G.enemies.list.map((e) => e.id)).size, 20);

  // A dead dummy's slot can be reused at once.
  assert.deepEqual(G.enemies.damage(goons[0], 999, { part: 'body', from: 'player' }), { killed: true });
  assert.ok(G.enemies.spawn('goon', V(0, 0, 30)));
  assert.equal(G.enemies.countByType('goon'), 12);
  G.enemies.clear();
  assert.equal(G.enemies.aliveCount(), 0);

  // A buzzard over a goon: shot down, it falls and its burst (r 3, 30 dmg) hurts what is underneath.
  const under = G.enemies.spawn('goon', V(15, 0, 0));
  const drone = G.enemies.spawn('buzzard', V(15, 6, 0.5));
  lookAt(G, drone.pos);
  G.input.hold('fire');
  G.frames(20);
  G.input.release('fire');
  assert.equal(drone.alive, false);
  assert.equal(G.last['enemy:killed'].type, 'buzzard');
  G.frames(120);
  assert.equal(G.count.explosion, 1);
  assert.equal(G.last.explosion.size, 'small');
  assert.equal(G.last.explosion.radius, 3);
  assert.equal(G.last.explosion.source, drone);
  assert.ok(under.hp < under.maxHp && under.alive, `goon below took ${under.maxHp - under.hp}`);
  assert.equal(G.enemies.list.includes(drone), false);
});

test('explosives stub: colliders, fuse, blast, chain reaction, reset', () => {
  const G = setup({
    explosives: [
      { type: 'propane', pos: V(10, 0, 0), yaw: 0 },
      { type: 'rack', pos: V(12, 0, 1), yaw: Math.PI / 2 },
      { type: 'propane', pos: V(10, 0, 30), yaw: 0 }, // far away
    ],
  });
  const [tank, rack, far] = G.explosives.items;
  assert.equal(G.explosives.items.length, 3);
  assert.equal(tank.type, 'propane');
  assert.equal(tank.hp, 50);
  assert.equal(tank.state, 'idle');
  assert.equal(rack.type, 'rack');
  assert.equal(rack.hp, 70);
  assert.equal(G.physics.boxes.length, 3, 'one collider each');
  assert.equal(tank.box.owner, tank);
  // The rack is turned a quarter: its 0.9 m side runs along z.
  near(rack.box.max.z - rack.box.min.z, 0.9, 1e-9);
  near(rack.box.max.x - rack.box.min.x, 0.5, 1e-9);
  assert.equal(G.physics.nav.isWalkable(12, 1), false, 'solid for navigation');
  assert.equal(G.scene.getObjectByName('explosives-stub').children.length, 3);

  const victim = G.enemies.spawn('goon', V(13, 0, -2));
  const hits = [];
  G.events.on('player:hit', (e) => hits.push(e));
  G.player.pos.set(4, 0, 0);
  lookAt(G, V(10, 0.3, 0));
  const sight = G.explosives.raycast(G.player.eye, G.player.forward, 60);
  assert.equal(sight.item, tank);

  // One round lights the fuse (26 < 50); 1.6 s later it blows.
  G.input.hold('fire');
  G.frames(1);
  G.input.release('fire');
  assert.equal(tank.state, 'lit');
  assert.equal(tank.hp, 24);
  assert.equal(G.count['explosive:lit'], 1);
  assert.equal(G.last.impact.surface, 'metal');
  G.frames(90);
  assert.equal(tank.state, 'lit', 'still burning at 1.5 s');
  G.frames(12);
  assert.equal(tank.state, 'gone');
  assert.equal(tank.box, null);
  assert.equal(G.count['explosive:blast'], 1);
  assert.equal(G.last.explosion.source, tank);
  assert.equal(G.last.explosion.size, 'big');
  assert.equal(G.last.explosion.radius, 6.5);
  near(110 - victim.hp, 170 * (1 - Math.hypot(3, 0.6, 2) / 6.5), 0.01, 'goon 3.7 m from the tank');
  assert.equal(victim.alive, true);
  // The player, 6 m away, takes the scaled share (the goon may have got a shot in as well).
  const blast = hits.find((h) => h.kind === 'blast');
  near(blast.amount, 170 * 0.5 * (1 - Math.hypot(6, 0.7) / 6.5), 1e-6, 'player blast damage');
  assert.deepEqual(blast.from.toArray(), [10, 0.3, 0], 'from the middle of the tank');

  // The rack next to it was set off by the blast and follows within half a second; the far tank is fine.
  assert.equal(rack.state, 'lit');
  assert.equal(G.count['explosive:lit'], 2);
  G.frames(30);
  assert.equal(rack.state, 'gone');
  assert.equal(G.count['explosive:blast'], 2);
  assert.equal(victim.alive, false, 'the second, bigger blast finishes the goon');
  assert.equal(G.combat.stats.kills, 1);
  assert.equal(G.combat.stats.hits, 0);
  assert.equal(far.state, 'idle');
  assert.equal(G.physics.boxes.length, 1);
  assert.equal(G.physics.nav.isWalkable(12, 1), true, 'the way is open again');

  // An enemy round does 9; two shots from the player finish a tank at once.
  G.explosives.damage(far, 9, {});
  assert.equal(far.hp, 41);
  G.explosives.damage(far, 26, 'player');
  G.explosives.damage(far, 26, 'player');
  G.frames(5);
  assert.equal(far.state, 'gone', 'hit points gone: instant');

  G.explosives.reset();
  assert.deepEqual(G.explosives.items.map((i) => [i.state, i.hp]), [['idle', 50], ['idle', 70], ['idle', 50]]);
  assert.equal(G.explosives.items[0], tank, 'same items, restored in place');
  assert.equal(G.physics.boxes.length, 3);
  assert.equal(tank.object.visible, true);
});

test('melee, death and reset', () => {
  const G = setup();
  const p = G.player;
  const goon = G.enemies.spawn('goon', V(1.6, 0, 0));
  G.input.hold('melee');
  G.frames(1);
  G.input.release('melee');
  assert.equal(goon.hp, 50);
  assert.equal(G.weapon.state, 'melee');
  assert.deepEqual(G.last['weapon:melee'], { hit: true });
  assert.equal(G.last['player:hitEnemy'].weapon, 'melee');
  G.input.hold('melee'); // still cooling down
  G.frames(1);
  G.input.release('melee');
  assert.equal(goon.hp, 50);
  G.frames(50);
  G.input.hold('melee');
  G.frames(1);
  G.input.release('melee');
  assert.equal(goon.alive, false);
  assert.equal(G.combat.stats.kills, 1);
  assert.equal(G.combat.stats.shots, 0);

  p.damage(40, V(5, 1, 5), 'bullet');
  assert.equal(p.health, 60);
  G.frames(1);
  assert.ok(G.render.post.damage > 0.5, 'hurt flash');
  p.heal(15);
  assert.equal(p.health, 75);
  p.invulnerable = true;
  p.damage(500, null, 'blast');
  assert.equal(p.health, 75);
  p.invulnerable = false;
  p.damage(500, V(5, 1, 5), 'bullet');
  assert.equal(p.alive, false);
  assert.equal(p.health, 0);
  assert.equal(G.count['player:dead'], 1);
  G.frames(90);
  near(p.eye.y, 0.22, 0.05, 'the camera is on the floor');
  near(G.camera.rotation.z, 1.15, 0.01, 'on its side');
  assert.equal(G.weapon.state, 'lowered');
  assert.equal(G.render.post.lowHealth, 1);

  // A disabled player leaves the camera alone.
  p.reset({ pos: V(-5, 0, 3), yaw: 0 });
  assert.equal(p.alive, true);
  assert.equal(p.health, 100);
  assert.deepEqual(G.camera.position.toArray(), [-5, 1.68, 3]);
  p.enabled = false;
  G.camera.position.set(1, 2, 3);
  G.input.move.y = 1;
  G.frames(30);
  assert.deepEqual(G.camera.position.toArray(), [1, 2, 3]);
  assert.deepEqual(p.pos.toArray(), [-5, 0, 3]);
  assert.equal(G.weapon.state, 'lowered');
});
