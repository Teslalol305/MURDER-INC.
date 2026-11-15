// G.fx as a whole (src/fx.js), created without a browser: the contract surface, the automatic effects on
// `impact` / `explosion` / `player:land`, budgets following G.quality.fx, emitters, clear(), and the
// promise that nothing throws on missing arguments.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { missingKeys, missingMembers } from '../src/core/contract.js';
import { createEvents } from '../src/core/events.js';
import { createFx } from '../src/fx.js';
import { EMITTER_KINDS } from '../src/fx/emitters.js';
import { createPhysics } from '../src/physics.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const DT = 1 / 60;

function makeWorld({ fx = 1 } = {}) {
  const events = createEvents();
  const log = [];
  const emit = events.emit;
  events.emit = (name, payload) => {
    log.push({ name, payload });
    emit(name, payload);
  };
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x0b0e18, 0.006);
  scene.add(new THREE.HemisphereLight(0x6f8fd0, 0x4a3a2c, 4.2));
  const sun = new THREE.DirectionalLight(0xffb46a, 3.2);
  sun.position.set(38, 100, 30);
  scene.add(sun, sun.target);
  const camera = new THREE.PerspectiveCamera(74, 16 / 9, 0.08, 700);
  camera.position.set(0, 1.7, 10);
  scene.add(camera);
  const vmScene = new THREE.Scene();
  const vmCamera = new THREE.PerspectiveCamera(54, 16 / 9, 0.01, 10);
  vmScene.add(vmCamera);

  const flashes = [];
  const held = [];
  const G = {
    THREE,
    events,
    time: { t: 0, dt: DT, frame: 0 },
    quality: { name: 'test', fx, scale: 1 },
    scene,
    camera,
    vmScene,
    vmCamera,
    renderer: { domElement: { height: 540 } },
    render: {
      post: { flash: 0 },
      lights: {
        flash: (pos, color, intensity, range, ttl) => flashes.push({ pos: pos.clone(), color, intensity, range, ttl }),
        acquire() {
          if (held.length >= 4) return null;
          const handle = { light: new THREE.PointLight(), release: () => held.splice(held.indexOf(handle), 1) };
          held.push(handle);
          return handle;
        },
      },
    },
    atmos: { sun },
    level: { groundSurfaceAt: (x) => (x > 50 ? 'dirt' : 'asphalt') },
    player: { pos: V(0, 0, 9) },
  };
  G.physics = createPhysics(G);
  // A brick wall north of the origin and a parked car to the east.
  G.physics.addBox({ min: [-10, 0, -6], max: [10, 6, -5], surface: 'brick' });
  G.physics.addBox({ min: [3, 0, -1], max: [7.6, 1.45, 0.85], surface: 'car' });
  G.fx = createFx(G);
  const step = (seconds = DT) => {
    for (let t = 0; t < seconds - 1e-9; t += DT) {
      G.time.frame++;
      G.fx.update(DT);
    }
  };
  const named = (name) => log.filter((e) => e.name === name).map((e) => e.payload);
  return { G, fx: G.fx, step, named, flashes, held };
}

test('fx: exposes the whole contract API and adds its draw calls to the scenes', () => {
  const { G, fx } = makeWorld();
  assert.deepEqual(missingMembers('fx', fx), []);
  const root = G.scene.getObjectByName('fx');
  assert.ok(root, 'a group named fx in the world scene');
  assert.deepEqual(
    root.children.map((c) => c.name).sort(),
    ['fx-additive', 'fx-debris', 'fx-decals', 'fx-lit', 'fx-shells', 'fx-tracers'],
    'six draw calls, no more',
  );
  assert.ok(root.children.every((c) => c.visible === false), 'nothing is drawn while nothing is alive');
  assert.equal(G.vmCamera.children.length, 1, 'the viewmodel flash pool rides on the viewmodel camera');
  const s = fx.stats();
  for (const key of ['lit', 'additive', 'tracers', 'debris', 'shells', 'decals', 'emitters']) assert.equal(s[key], 0, key);
  assert.deepEqual(s.budget, { lit: 1400, additive: 3040, tracers: 48, debris: 256, shells: 60, decals: 256, emitters: 24 });
});

test('fx: every `impact` event runs a burst; walls and floors get a mark, bodies do not', () => {
  const { G, fx, step } = makeWorld();
  const shot = (surface, enemy = null) =>
    G.events.emit('impact', { point: V(0, 1.5, -5), normal: V(0, 0, 1), surface, dir: V(0, 0, -1), from: 'player', enemy });
  const before = fx.stats();
  shot('brick');
  let s = fx.stats();
  assert.equal(s.decals, 1);
  assert.ok(s.lit >= 2, `dust: ${s.lit}`);
  assert.ok(s.debris >= 1, `chips: ${s.debris}`);

  shot('metal');
  s = fx.stats();
  assert.equal(s.decals, 2);
  assert.ok(s.additive >= 12, `sparks on metal: ${s.additive}`);

  const additive = s.additive;
  shot('flesh', { type: 'goon' });
  shot('drone', { type: 'buzzard' });
  s = fx.stats();
  assert.equal(s.decals, 2, 'no mark hangs in the air where a body was');
  assert.ok(s.additive > additive, 'a Buzzard throws sparks');
  assert.ok(s.spawned > before.spawned);

  // An unknown surface is treated like masonry, missing vectors get defaults.
  assert.doesNotThrow(() => {
    G.events.emit('impact', { point: V(1, 1, -5), normal: null, surface: 'marzipan', dir: null, from: 'enemy', enemy: null });
    G.events.emit('impact', null);
  });
  step(3);
  s = fx.stats();
  assert.equal(s.lit + s.additive + s.debris, 0, 'impacts burn out');
  assert.equal(s.decals, 2, 'only known surfaces leave a mark, and marks stay');
});

test('fx: every `explosion` event runs a blast sized by its radius, with a light, a scorch and an aftermath', () => {
  const { G, fx, step, flashes } = makeWorld();
  G.events.emit('explosion', { pos: V(0, 0.3, 0), radius: 6.5, size: 'big', source: null });
  const big = fx.stats();
  assert.ok(big.lit >= 20 && big.additive >= 50 && big.debris >= 8, `a propane blast: ${JSON.stringify(big)}`);
  assert.equal(big.decals, 1, 'scorch mark');
  assert.equal(big.emitters, 2, 'something smoulders and throws embers for a while');
  assert.equal(flashes.length, 1);
  assert.ok(flashes[0].intensity >= 80 && flashes[0].ttl > 0.2, 'a pooled light, not a blink');
  step(DT);
  assert.ok(G.render.post.flash > 0.05, `a blast 10 m away lifts the screen: ${G.render.post.flash}`);

  fx.clear();
  G.events.emit('explosion', { pos: V(0, 0.4, 0), radius: 3, size: 'small', source: { type: 'buzzard' } });
  const small = fx.stats();
  assert.ok(small.lit < big.lit && small.debris < big.debris, 'a Buzzard burst is the smaller blast');
  assert.ok(flashes[1].intensity < flashes[0].intensity);

  step(12);
  const after = fx.stats();
  assert.equal(after.lit + after.additive + after.debris + after.emitters, 0, 'burnt out after 12 s');
  assert.equal(after.decals, 1, 'the scorch stays');
  assert.equal(G.render.post.flash, 0, 'the screen flash is given back');
});

test('fx: another module that takes over render.post.flash is left alone', () => {
  const { G, fx, step } = makeWorld();
  fx.explosion(V(0, 0.3, 4), 1);
  step(DT);
  assert.ok(G.render.post.flash > 0);
  G.render.post.flash = 0.9; // the game whites the screen out for its own reasons
  step(1);
  assert.equal(G.render.post.flash, 0.9);
});

test('fx: budgets and recipes follow G.quality.fx, live', () => {
  const full = makeWorld({ fx: 1 });
  const low = makeWorld({ fx: 0.4 });
  for (const w of [full, low]) w.fx.explosion(V(0, 0.3, 0), 1);
  const a = full.fx.stats();
  const b = low.fx.stats();
  assert.deepEqual([b.budget.lit, b.budget.additive, b.budget.debris], [560, 1216, 102]);
  assert.ok(b.additive < a.additive * 0.6 && b.lit < a.lit * 0.75, `thinner at 0.4: ${b.additive}/${a.additive}, ${b.lit}/${a.lit}`);

  // Sustained abuse never exceeds the budget.
  for (let i = 0; i < 40; i++) low.fx.explosion(V(i % 5, 0.3, i % 3), 1.5);
  const s = low.fx.stats();
  assert.ok(s.lit <= 560 && s.additive <= 1216 && s.debris <= 102, JSON.stringify(s));
  assert.ok(s.recycled + s.refused > 0, 'the overflow was recycled or turned away');

  // The preset changes under a running game.
  low.G.quality.fx = 1;
  low.step(DT);
  assert.equal(low.fx.stats().budget.lit, 1400);
});

test('fx: nothing is spawned for things out of sight, and far effects are thinned', () => {
  const { fx } = makeWorld();
  fx.sparks(V(0, 1, -400), V(0, 1, 0), 20);
  fx.smoke(V(0, 1, -400), 1);
  assert.equal(fx.stats().spawned, 0);
  fx.sparks(V(0, 1, 0), V(0, 1, 0), 40);
  const nearCount = fx.stats().additive;
  fx.clear();
  fx.sparks(V(0, 1, -80), V(0, 1, 0), 40);
  const farCount = fx.stats().additive;
  assert.ok(farCount < nearCount * 0.7 && farCount > 0, `${farCount} far vs ${nearCount} near`);
});

test('fx: tracers fly and finish; muzzle flashes go to the world or to the viewmodel', () => {
  const { G, fx, step, flashes } = makeWorld();
  fx.tracer(V(0, 1.5, 9), V(0, 1.5, -5));
  fx.tracer(V(0, 1.5, 9), V(0.2, 1.5, 9.1)); // too short to draw
  assert.equal(fx.stats().tracers, 1);
  step(DT);
  assert.ok(G.scene.getObjectByName('fx-tracers').visible);
  step(0.2);
  assert.equal(fx.stats().tracers, 0);

  fx.clear();
  fx.muzzleFlash(V(2, 1.4, 2), V(0, 0, -1), 1, true);
  const world = fx.stats();
  assert.ok(world.additive >= 4, 'flash sprites and sparks in the world');
  assert.equal(flashes.length, 0, 'no pooled light: the shooter flashes its own');

  // First person, and the weapon has no flash of its own: fx draws it on the viewmodel.
  fx.clear();
  fx.muzzleFlash(V(0.16, 1.57, 9.4), V(0, 0, -1), 1, false);
  const view = G.vmCamera.children[0];
  step(DT);
  assert.ok(fx.stats().additive <= 3, 'at most a few sparks in the world pool');
  assert.ok(view.visible && view.geometry.instanceCount >= 3, 'sprites on the viewmodel');
  assert.equal(flashes.length, 0);
  // In front of the camera, right of centre, below the eye line.
  const p = view.geometry.attributes.iPos;
  assert.ok(p.getZ(0) < -0.3 && p.getX(0) > 0 && p.getY(0) < 0, `camera space: ${p.getX(0)}, ${p.getY(0)}, ${p.getZ(0)}`);
  // … rescaled from the world camera's 74° to the viewmodel's 54°, so it lands on the same pixel.
  const ratio = Math.tan((54 * Math.PI) / 360) / Math.tan((74 * Math.PI) / 360);
  assert.ok(Math.abs(p.getX(0) - 0.16 * ratio) < 0.02, `x = ${p.getX(0)}, expected about ${0.16 * ratio}`);
  step(0.1);
  assert.equal(view.visible, false, 'gone within three frames');
});

test('fx: a viewmodel with its own muzzle flash keeps it to itself', () => {
  const { G, fx, step } = makeWorld();
  const own = new THREE.Object3D();
  own.name = 'muzzle-flash';
  G.vmCamera.add(own);
  fx.muzzleFlash(V(0.16, 1.57, 9.4), V(0, 0, -1), 1, false);
  step(DT);
  const view = G.vmCamera.children.find((c) => c.name === 'fx-viewmodel-flash');
  assert.equal(view.visible, false, 'no second flash over the weapon\'s own');
});

test('fx: brass lands on what is under it and reports its first bounce with the surface', () => {
  const { fx, step, named } = makeWorld();
  fx.shell(V(0, 1.4, 4), V(1.5, 1.2, 0), 'rifle'); // onto the road
  fx.shell(V(5, 2.2, 0), V(0.2, 0.5, 0), 'pistol'); // onto the car roof
  fx.shell(V(60, 1.4, 4), V(0, 1, 0)); // far east: the level says dirt there
  assert.equal(fx.stats().shells, 3);
  step(3);
  const bounces = named('shell:bounce');
  assert.equal(bounces.length, 3, 'one event per casing');
  for (const b of bounces) assert.deepEqual(missingKeys('shell:bounce', b), []);
  const road = bounces.find((b) => Math.abs(b.pos.z - 4) < 0.5 && b.pos.x < 10);
  const roof = bounces.find((b) => b.pos.y > 1);
  const dirt = bounces.find((b) => b.pos.x > 50);
  assert.equal(road.surface, 'asphalt');
  assert.ok(road.pos.y < 0.05);
  assert.equal(roof.surface, 'car');
  assert.ok(Math.abs(roof.pos.y - 1.45) < 0.05, `on the roof: ${roof.pos.y}`);
  assert.equal(dirt.surface, 'dirt');
  assert.equal(fx.stats().shells, 3, 'brass stays where it fell');

  for (let i = 0; i < 100; i++) fx.shell(V(0, 1, 4), V(1, 1, 0), 'rifle');
  assert.equal(fx.stats().shells, 60, 'the ring holds 60');
});

test('fx: emitters of every kind run, move, aim and stop; clear() keeps the endless ones', () => {
  const { fx, step, held } = makeWorld();
  const handles = EMITTER_KINDS.map((kind, i) => fx.addEmitter(V(i * 2 - 5, kind === 'drip' ? 3 : 0, 2), kind, { ttl: kind === 'steam' ? undefined : 4, dir: V(1, 0.4, 0) }));
  for (const h of handles) assert.deepEqual(Object.keys(h).sort(), ['setDir', 'setPos', 'stop']);
  assert.equal(fx.stats().emitters, 6);
  step(1);
  const s = fx.stats();
  assert.ok(s.lit >= 15, `steam, smoulder and fire smoke: ${s.lit}`);
  assert.ok(s.additive >= 40, `flames, embers, jet: ${s.additive}`);
  assert.equal(held.length, 2, 'the fire and the jet each hold a pooled light');
  assert.ok(held.every((h) => h.light.intensity > 0), 'and it burns');

  handles[3].setPos(V(1, 0.5, 2));
  handles[5].setDir(V(0, 1, 0));
  step(0.5);
  handles[3].stop(); // the fire
  handles[3].stop(); // twice is harmless
  assert.equal(held.length, 1, 'its light went back to the pool');
  assert.equal(fx.stats().emitters, 5);

  fx.clear();
  assert.equal(fx.stats().emitters, 1, 'only the endless steam survives clear()');
  assert.equal(held.length, 0);
  step(6);
  assert.equal(fx.stats().emitters, 1);
  assert.ok(fx.stats().lit > 5, 'and it is still steaming');
  handles[0].stop();
  assert.equal(fx.stats().emitters, 0);

  // A stale handle must not touch whoever has the slot now.
  const next = fx.addEmitter(V(0, 0, 0), 'embers', { ttl: 5 });
  handles[0].stop();
  assert.equal(fx.stats().emitters, 1);
  next.stop();

  // Unknown kinds and a full house give a handle that does nothing.
  assert.doesNotThrow(() => fx.addEmitter(V(0, 0, 0), 'confetti').stop());
  for (let i = 0; i < 30; i++) fx.addEmitter(V(i, 0, 0), 'steam');
  assert.equal(fx.stats().emitters, 24);
  assert.doesNotThrow(() => fx.addEmitter(V(0, 0, 0), 'steam').setPos(V(1, 1, 1)));
});

test('fx: a hard landing raises dust, a soft one does not; deaths are left to the enemies module', () => {
  const { G, fx } = makeWorld();
  G.events.emit('player:land', { speed: 1.5, surface: 'asphalt' });
  assert.equal(fx.stats().lit, 0);
  G.events.emit('player:land', { speed: 9, surface: 'asphalt' });
  assert.ok(fx.stats().lit >= 4, `dust ring: ${fx.stats().lit}`);

  fx.clear();
  G.events.emit('enemy:killed', { enemy: {}, type: 'buzzard', pos: V(0, 6, 0), part: 'body', byPlayer: true, weapon: 'chopper' });
  assert.equal(fx.stats().lit + fx.stats().additive + fx.stats().debris, 0, 'the enemies module plays its own death effects');
});

test('fx: smoke is dark and rolling at scale, a pale wisp when small', () => {
  const { fx } = makeWorld();
  fx.smoke(V(0, 1, 0), 0.8);
  const rolling = fx.stats().lit;
  assert.ok(rolling >= 2, `a puff of several particles: ${rolling}`);
  fx.smoke(V(0, 1.5, 9.5), 0.22); // the weapon's barrel smoke
  assert.equal(fx.stats().lit, rolling + 1, 'one thin wisp');
});

test('fx: decals hold the newest 256 and marks on a blown-up prop are wiped', () => {
  const { G, fx } = makeWorld();
  for (let i = 0; i < 300; i++) fx.decal(V(-9 + (i % 60) * 0.3, 1 + Math.floor(i / 60) * 0.5, -5), V(0, 0, 1), i % 2 ? 'bullet' : 'metal');
  let s = fx.stats();
  assert.equal(s.decals, 256);
  assert.equal(s.decalsPlaced, 300);
  fx.decal(V(0, 0, 0), V(0, 1, 0), 'no-such-mark');
  assert.equal(fx.stats().decalsPlaced, 300, 'unknown kinds are ignored');

  fx.clear();
  fx.decal(V(5, 0.3, 5), V(1, 0, 0), 'metal', 0.15);
  fx.decal(V(5.1, 0.4, 5), V(1, 0, 0), 'metal');
  fx.decal(V(9, 0.3, 5), V(1, 0, 0), 'metal');
  G.events.emit('explosive:blast', { item: {}, pos: V(5, 0.3, 5) });
  assert.equal(fx.stats().decals, 1, 'only the mark away from the blast is left');
});

test('fx: the public calls shrug off missing arguments', () => {
  const { fx, step } = makeWorld();
  assert.doesNotThrow(() => {
    fx.muzzleFlash();
    fx.muzzleFlash(V(0, 1, 0));
    fx.tracer();
    fx.tracer(V(0, 0, 0));
    fx.impact();
    fx.impact(V(0, 0, 0));
    fx.sparks();
    fx.sparks(V(0, 1, 0));
    fx.smoke();
    fx.dust();
    fx.puff();
    fx.puff(V(0, 1, 0));
    fx.explosion();
    fx.shell();
    fx.shell(V(0, 1, 0));
    fx.debris();
    fx.debris(V(0, 1, 0));
    fx.decal();
    fx.decal(V(0, 0, 0));
    fx.addEmitter();
    fx.addEmitter(null, 'fire').stop();
    step(0.5);
    fx.update(0);
    fx.update(0.25);
    fx.clear();
    fx.clear();
  });
});
