// G.explosives (src/explosives.js) against the real physics and combat modules: hit points, fuses,
// what enemy rounds do, the blast, the chain reaction, colliders coming and going, reset.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { createCombat } from '../src/combat.js';
import * as weapons from '../src/config/weapons.js';
import { missingMembers } from '../src/core/contract.js';
import { createEvents } from '../src/core/events.js';
import { createRng } from '../src/core/rng.js';
import { KINDS, chainFuse, chainRange, createExplosives, sizeFromRadius } from '../src/explosives.js';
import { createPhysics } from '../src/physics.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const DT = 1 / 60;

const near = (actual, expected, eps, label = '') =>
  assert.ok(Math.abs(actual - expected) <= eps, `${label} expected ${expected} ± ${eps}, got ${actual}`);

/** A small world: real physics and combat, a recording event bus, fakes for everything else. */
function makeWorld(entries) {
  const events = createEvents();
  const log = [];
  const emit = events.emit;
  events.emit = (name, payload) => {
    log.push({ name, payload });
    emit(name, payload);
  };
  const emitters = [];
  const G = {
    THREE,
    events,
    rng: createRng(7),
    time: { t: 0, dt: DT, frame: 0 },
    config: { weapons },
    scene: new THREE.Scene(),
    level: { explosives: entries, groundSurfaceAt: () => 'asphalt' },
    props: {
      build(name) {
        const object = new THREE.Group();
        const states = [];
        const size = name === 'propane_tank' ? [0.32, 0.6, 0.32] : [0.9, 1.6, 0.5];
        return { object, size, states, dynamic: true, setState: (s) => states.push(s) };
      },
    },
    fx: {
      addEmitter(pos, kind, opts) {
        const e = { pos: pos.clone(), kind, opts: { ...opts, dir: opts.dir.clone() }, stopped: false };
        emitters.push(e);
        return { stop: () => (e.stopped = true), setPos() {}, setDir() {} };
      },
    },
    player: {
      pos: V(100, 0, 100),
      eye: V(100, 1.6, 100),
      alive: true,
      crouching: false,
      hits: [],
      shakes: [],
      damage(amount, from, kind) {
        this.hits.push({ amount, kind });
      },
      addShake(x) {
        this.shakes.push(x);
      },
    },
    enemies: {
      list: [],
      alerts: [],
      raycast: () => null,
      damage(enemy, amount) {
        enemy.hp -= amount;
        enemy.took = (enemy.took || 0) + amount;
        return { killed: enemy.hp <= 0 };
      },
      alert(pos, radius) {
        this.alerts.push({ pos: pos.clone(), radius });
      },
    },
  };
  G.physics = createPhysics(G);
  G.combat = createCombat(G);
  G.explosives = createExplosives(G);
  const step = (seconds) => {
    for (let t = 0; t < seconds - 1e-9; t += DT) {
      G.time.frame++;
      G.time.t += DT;
      G.explosives.update(DT);
    }
  };
  const named = (name) => log.filter((e) => e.name === name).map((e) => e.payload);
  /** A player round fired east at the item from two metres west of it. */
  const shoot = (item, damage = 26, from = 'player') =>
    G.combat.hitscan({ origin: V(item.pos.x - 2, item.pos.y + 0.3, item.pos.z), dir: V(1, 0, 0), range: 50, damage, from });
  return { G, log, named, step, shoot, emitters, items: G.explosives.items };
}

const propane = (x, z = 0) => ({ type: 'propane', pos: V(x, 0, z), yaw: 0 });
const rack = (x, z = 0, yaw = 0) => ({ type: 'rack', pos: V(x, 0, z), yaw });

test('explosives: the module has the contract members and builds one solid item per level entry', () => {
  const { G, items } = makeWorld([propane(0), rack(10, 0, Math.PI / 2)]);
  assert.deepEqual(missingMembers('explosives', G.explosives), []);
  assert.equal(items.length, 2);
  assert.deepEqual(items.map((i) => [i.type, i.hp, i.state]), [['propane', 50, 'idle'], ['rack', 70, 'idle']]);
  // Solid cover: a collider each, tagged so combat knows whose it is.
  const tank = items[0].box;
  assert.ok(G.physics.boxes.includes(tank));
  assert.equal(tank.owner, items[0]);
  near(tank.max.y, 0.6, 1e-9, 'tank height');
  near(tank.max.x - tank.min.x, 0.32, 1e-9, 'tank width');
  // The rack is turned a quarter: its long side lies along Z.
  const r = items[1].box;
  near(r.max.x - r.min.x, 0.5, 1e-6, 'rack depth after the turn');
  near(r.max.z - r.min.z, 0.9, 1e-6, 'rack length after the turn');
  assert.equal(G.physics.raycast(V(-5, 0.3, 0), V(1, 0, 0), 50).box, tank, 'bullets stop on it');
  assert.equal(G.scene.getObjectByName('explosives').children.length, 2, 'props are in the scene');
});

test('explosives: the first hit lights a 1.6 s fuse with a jet at the hole; then it blows', () => {
  const { G, named, step, shoot, emitters, items } = makeWorld([propane(0)]);
  const tank = items[0];
  const hit = shoot(tank);
  assert.equal(hit.type, 'explosive');
  assert.equal(hit.item, tank);
  assert.equal(tank.hp, 24);
  assert.equal(tank.state, 'lit');
  assert.deepEqual(tank.prop.states, ['idle', 'lit']);

  const lit = named('explosive:lit');
  assert.equal(lit.length, 1);
  assert.equal(lit[0].item, tank);
  assert.equal(lit[0].fuse, 1.6);

  // The jet comes out of the hole (west face), outward and up, for as long as the fuse.
  assert.equal(emitters.length, 1);
  const jet = emitters[0];
  assert.equal(jet.kind, 'jet');
  near(jet.pos.x, -0.16 - 0.02, 1e-6, 'at the west face');
  near(jet.pos.y, 0.3, 1e-6);
  assert.ok(jet.opts.dir.x < -0.5 && jet.opts.dir.y > 0.2, `out and up: ${jet.opts.dir.toArray()}`);
  near(jet.opts.dir.length(), 1, 1e-6);
  assert.ok(jet.opts.ttl >= 1.6);

  step(1.5);
  assert.equal(tank.state, 'lit', 'still hissing at 1.5 s');
  assert.equal(named('explosion').length, 0);
  step(0.15);
  assert.equal(tank.state, 'gone');
  assert.equal(tank.hp, 0);
  assert.equal(tank.box, null);
  assert.ok(jet.stopped, 'the jet stops with the blast');
  assert.deepEqual(tank.prop.states, ['idle', 'lit', 'gone']);

  const blast = named('explosion');
  assert.equal(blast.length, 1);
  assert.equal(blast[0].radius, 6.5);
  assert.equal(blast[0].size, 'big');
  assert.equal(blast[0].source, tank);
  near(blast[0].pos.y, 0.3, 1e-9, 'centred on the tank');
  assert.equal(named('explosive:blast').length, 1);
  assert.equal(G.physics.raycast(V(-5, 0.3, 0), V(1, 0, 0), 50), null, 'the collider went with it');
});

test('explosives: hit points at zero pop it 0.06 s later; a welding rack takes three rounds', () => {
  const { named, step, shoot, items } = makeWorld([propane(0), rack(40)]);
  const [tank, cart] = items;
  shoot(tank);
  step(0.2);
  shoot(tank); // 52 damage in all: more than its 50
  assert.equal(tank.hp, 0);
  step(0.05);
  assert.equal(tank.state, 'lit');
  step(0.03);
  assert.equal(tank.state, 'gone', 'popped 0.06 s after the killing round');

  shoot(cart);
  shoot(cart);
  assert.equal(cart.hp, 18);
  assert.equal(named('explosive:lit').length, 2, 'lit once each');
  step(0.5);
  assert.equal(cart.state, 'lit', 'two rounds: the rack still burns down its 1.1 s fuse');
  shoot(cart);
  step(0.08);
  assert.equal(cart.state, 'gone');
  assert.equal(named('explosion')[1].radius, 7.5);
});

test('explosives: an enemy round does 9, whatever it would do to a person', () => {
  const { G, step, shoot, items } = makeWorld([propane(0)]);
  const tank = items[0];
  const goon = { type: 'goon', pos: V(-2, 0, 0) };
  shoot(tank, 40, goon);
  assert.equal(tank.hp, 41);
  assert.equal(tank.state, 'lit', 'enemy fire lights it too');
  // A direct call (a Buzzard bolt landing) is held to the same rule.
  G.explosives.damage(tank, 13, goon);
  assert.equal(tank.hp, 32);
  step(1.7);
  assert.equal(tank.state, 'gone');
});

test('explosives: the blast does 170 falling off to nothing at 6.5 m; the player takes half; enemies are alerted', () => {
  const { G, step, shoot, items } = makeWorld([propane(0)]);
  const goon = { type: 'goon', pos: V(3.25, 0, 0), alive: true, hp: 500, height: 1.8 };
  const far = { type: 'goon', pos: V(0, 0, 7), alive: true, hp: 500, height: 1.8 };
  G.enemies.list.push(goon, far);
  G.player.pos.set(-3.25, 0, 0);
  shoot(items[0]);
  step(1.7);

  // Distances are measured to mid-body (0.9 m up) from the tank's middle (0.3 m up).
  const d = Math.hypot(3.25, 0.6);
  near(goon.took, 170 * (1 - d / 6.5), 1e-6, 'enemy damage');
  assert.equal(far.took, undefined, 'out of range');
  const dp = Math.hypot(3.25, 0.7); // the player is measured 1 m above the feet
  const blastHit = G.player.hits.find((hit) => hit.kind === 'blast');
  near(blastHit.amount, 85 * (1 - dp / 6.5), 1e-6, 'player damage is half');

  assert.equal(G.player.shakes.length, 1);
  const g = 1 - G.player.pos.distanceTo(V(0, 0.3, 0)) / 28;
  near(G.player.shakes[0], 0.15 + 0.9 * g * g, 1e-6, 'camera shake');
  assert.deepEqual(G.enemies.alerts.map((a) => a.radius), [60], 'a prop blast is heard 60 m away');
});

test('explosives: chain rule numbers', () => {
  near(chainRange(KINDS.propane.size), 5.24, 1e-9, 'propane sets off tanks within 5.24 m');
  near(chainRange(KINDS.rack.size), 5.88, 1e-9, 'a rack within 5.88 m');
  near(chainRange(sizeFromRadius(3)), 4.12, 0.02, 'a Buzzard crash within about 4.1 m');
  near(chainFuse(0, 0), 0.14, 1e-12);
  near(chainFuse(5, 0.999), 0.14 + 0.2997 + 0.15, 1e-9);
});

test('explosives: a blast sets off the tanks in range after a short ripple, not the ones beyond', () => {
  const { named, step, shoot, items } = makeWorld([propane(0), propane(3), propane(5.1), propane(6.2), propane(13)]);
  const [first, close, edge, outside, distant] = items;
  shoot(first);
  shoot(first);
  step(0.08);
  assert.equal(first.state, 'gone');
  assert.equal(close.state, 'lit');
  assert.equal(edge.state, 'lit', '5.1 m is inside the 5.24 m chain range');
  assert.equal(outside.state, 'idle', '6.2 m is inside the blast but outside the chain range');
  assert.equal(outside.hp, 50, 'and takes no damage from it');
  assert.equal(distant.state, 'idle');
  for (const item of [close, edge]) {
    const d = item.pos.x;
    assert.ok(item.fuse >= 0.14 + 0.03 * d - DT * 2 && item.fuse <= 0.44 + 0.03 * d, `ripple fuse at ${d} m: ${item.fuse}`);
  }
  assert.equal(named('explosive:lit').length, 3);

  step(0.7);
  assert.equal(close.state, 'gone');
  assert.equal(edge.state, 'gone');
  // The tank at 5.1 m carries the reaction on to the one at 6.2 m; the one at 13 m is out of everyone's reach.
  step(0.7);
  assert.equal(outside.state, 'gone', 'caught by the second ring');
  assert.equal(distant.state, 'idle');
  assert.equal(named('explosion').length, 4);
});

test('explosives: a lit tank caught by a blast goes early, and any explosion can start a chain', () => {
  const { G, step, shoot, items } = makeWorld([propane(0), propane(40)]);
  const [tank, other] = items;
  shoot(tank);
  assert.equal(tank.fuse, 1.6);
  // A Buzzard comes down two metres away.
  G.combat.explode({ pos: V(2, 0.4, 0), radius: 3, damage: 30, source: { type: 'buzzard' } });
  assert.ok(tank.fuse < 0.52, `fuse cut short: ${tank.fuse}`);
  assert.equal(tank.hp, 24, 'a blast does not wear down hit points');
  step(0.6);
  assert.equal(tank.state, 'gone');
  assert.equal(other.state, 'idle');

  // The same crash 4.5 m from an idle tank is too far (about 4.1 m reach).
  G.combat.explode({ pos: V(44.5, 0.3, 0), radius: 3, damage: 30, source: { type: 'buzzard' } });
  assert.equal(other.state, 'idle');
  G.combat.explode({ pos: V(43.5, 0.3, 0), radius: 3, damage: 30, source: { type: 'buzzard' } });
  assert.equal(other.state, 'lit');
});

test('explosives: raycast reports the nearest live item, the entry point and the face normal', () => {
  const { G, step, shoot, items } = makeWorld([propane(0), propane(2)]);
  const hit = G.explosives.raycast(V(-5, 0.3, 0.05), V(1, 0, 0), 50);
  assert.equal(hit.item, items[0]);
  near(hit.dist, 5 - 0.16, 1e-9);
  assert.deepEqual(hit.normal.toArray(), [-1, 0, 0]);
  near(hit.point.x, -0.16, 1e-9);
  const down = G.explosives.raycast(V(2, 3, 0), V(0, -1, 0), 50);
  assert.equal(down.item, items[1]);
  assert.deepEqual(down.normal.toArray(), [0, 1, 0]);
  assert.equal(G.explosives.raycast(V(-5, 0.3, 0), V(1, 0, 0), 4), null, 'out of reach');
  assert.equal(G.explosives.raycast(V(-5, 2, 0), V(1, 0, 0), 50), null, 'over the top');

  shoot(items[0]);
  shoot(items[0]);
  step(0.1);
  // The first tank is gone: rays pass through where it stood. Its neighbour was caught and is lit.
  assert.equal(G.explosives.raycast(V(-5, 0.3, 0), V(1, 0, 0), 50).item, items[1]);
});

test('explosives: reset restores every item, its collider and its hit points, and quenches jets', () => {
  const { G, step, shoot, emitters, items } = makeWorld([propane(0), propane(20)]);
  shoot(items[0]);
  shoot(items[0]);
  shoot(items[1]);
  step(0.2);
  assert.deepEqual(items.map((i) => i.state), ['gone', 'lit']);
  const boxesBefore = G.physics.boxes.length;

  G.explosives.reset();
  assert.equal(G.explosives.items, items, 'the list keeps its identity');
  assert.deepEqual(items.map((i) => [i.state, i.hp]), [['idle', 50], ['idle', 50]]);
  assert.equal(G.physics.boxes.length, boxesBefore + 1, 'the blown tank is solid again');
  assert.ok(items.every((i) => i.box && G.physics.boxes.includes(i.box)));
  assert.ok(emitters.every((e) => e.stopped), 'no jet survives a reset');
  assert.equal(items[1].prop.states.at(-1), 'idle');
  step(2);
  assert.deepEqual(items.map((i) => i.state), ['idle', 'idle'], 'a reset tank does not go off by itself');

  // A new level list rebuilds the set.
  G.level.explosives = [rack(5)];
  G.explosives.reset();
  assert.equal(G.explosives.items.length, 1);
  assert.equal(G.explosives.items[0].type, 'rack');
  assert.equal(G.scene.getObjectByName('explosives').children.length, 1);
  assert.equal(G.physics.boxes.filter((b) => b.tag === 'explosive').length, 1);
});

test('explosives: a lit tank hisses louder and louder at its own position until it goes', () => {
  const { G, step, shoot, items } = makeWorld([propane(0), propane(30)]);
  const loops = [];
  G.audio = {
    loop(name, opts) {
      const handle = { name, pos: opts.pos, volumes: [opts.volume], stopped: false, setPos() {}, setVolume: (v) => handle.volumes.push(v), stop: () => (handle.stopped = true) };
      loops.push(handle);
      return handle;
    },
  };
  shoot(items[0]);
  assert.equal(loops.length, 1);
  assert.equal(loops[0].name, 'hiss');
  assert.equal(loops[0].pos, items[0].pos);
  step(1.5);
  const v = loops[0].volumes;
  assert.ok(v.length > 60 && v.every((x, i) => i === 0 || x >= v[i - 1]), 'the volume only rises');
  assert.ok(v[0] <= 0.3 && v.at(-1) > 0.85 && v.at(-1) <= 1, `from quiet to full: ${v[0]} … ${v.at(-1)}`);
  assert.equal(loops[0].stopped, false);
  step(0.2);
  assert.ok(loops[0].stopped, 'cut by the blast');

  // Audio that does not know the sound, or throws, changes nothing.
  G.audio = { loop: () => null };
  shoot(items[1]);
  G.explosives.reset();
  G.audio = {
    loop() {
      throw new Error('no such loop');
    },
  };
  assert.doesNotThrow(() => shoot(items[1]));
  step(1.7);
  assert.equal(items[1].state, 'gone');
});

test('explosives: tolerates stubs and odd input', () => {
  const { G, items } = makeWorld([propane(0), { type: 'mystery', pos: V(3, 0, 0) }, null, { type: 'rack' }]);
  assert.equal(items.length, 2, 'entries without a position are skipped');
  assert.equal(items[1].type, 'propane', 'an unknown type is a propane tank');
  assert.doesNotThrow(() => {
    G.explosives.damage(null, 10, 'player');
    G.explosives.damage(items[0], 0, 'player');
    G.explosives.damage(items[0], -5, 'player');
    G.explosives.damage(items[0], 10, 'blast'); // no blast in progress: nothing happens
    G.fx = null;
    G.props = null;
    G.explosives.damage(items[0], 10, 'player');
    G.explosives.update(2);
  });
  assert.equal(items[0].state, 'gone');
});
