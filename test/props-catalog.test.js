// The prop factory against the catalogue: every prop builds, fits its box, has sane colliders and lamp
// hints, stays inside the triangle budget, and the stateful ones do what the contract says. The props
// are built for real here; only the material library is a stand-in (flat materials, no canvas).

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import * as brand from '../src/config/brand.js';
import * as catalog from '../src/config/catalog.js';
import * as look from '../src/config/look.js';
import { createRng } from '../src/core/rng.js';
import { createPhysics } from '../src/physics.js';
import { createProps } from '../src/props.js';

const { PROPS } = catalog;

// Parts that are allowed outside the catalogue footprint (docs/CONTRACT.md 6.2 "Overhang"): metres per side.
const OVERHANG = {
  street_lamp: { z: 2.6 },
  traffic_light: { z: 3.3, x: 0.15 },
  tree: { x: 2.4, z: 2.4 },
  court_light: { x: 0.5, z: 0.5 },
  hydrant_open: { x: 1.2, z: 4 },
  master_case: { x: 0.02, z: 0.04, y: 0.32 }, // the beacon mast stands clear of waist-high cover
};
const FIT = 0.03; // everything else: three centimetres

function mockMats() {
  const cache = new Map();
  const unknown = [];
  const flat = () => new THREE.MeshBasicMaterial();
  return {
    unknown,
    get(name, opts) {
      if (!catalog.MATERIALS[name] && !unknown.includes(name)) unknown.push(name);
      const key = `${name}|${JSON.stringify(opts || {})}`;
      if (!cache.has(key)) {
        const m = new THREE.MeshStandardMaterial({ color: (opts && opts.color) ?? 0x808080 });
        m.name = name;
        m.userData.opts = opts || {};
        cache.set(key, m);
      }
      return cache.get(key);
    },
    emissive: flat,
    sign: (spec = {}) => ({ material: flat(), w: spec.w ?? 2, h: spec.h ?? 0.6 }),
    poster: () => ({ material: flat(), w: 0.6, h: 0.9 }),
    graffiti: (text = '') => ({ material: flat(), w: Math.max(1, text.length * 0.42), h: 0.9 }),
    decal: () => ({ material: flat(), w: 0.9, h: 0.9 }),
    drawIPX: () => 100,
    canvasTexture: () => new THREE.Texture(),
  };
}

function setup(seed = 1994) {
  const mats = mockMats();
  const G = {
    THREE,
    rng: createRng(seed),
    mats,
    quality: { name: 'medium' },
    config: { brand, catalog, look },
    time: { t: 0, dt: 1 / 60 },
    camera: new THREE.PerspectiveCamera(),
  };
  return { G, mats, props: createProps(G) };
}

const hiddenBy = (o) => {
  for (let p = o; p; p = p.parent) if (!p.visible) return true;
  return false;
};
const isEffect = (mesh) => mesh.material.name === 'props_additive';

/** Bounds of what is solid and showing (light shafts, flames and hidden parts do not count). */
function solidBounds(prop) {
  prop.object.updateMatrixWorld(true);
  const box = new THREE.Box3();
  prop.object.traverse((o) => {
    if (o.isMesh && !isEffect(o) && !hiddenBy(o)) box.union(new THREE.Box3().setFromObject(o));
  });
  return box;
}

function triangles(prop, visibleOnly = false) {
  let n = 0;
  prop.object.traverse((o) => {
    if (!o.isMesh || (visibleOnly && hiddenBy(o))) return;
    n += (o.geometry.index ? o.geometry.index.count : o.geometry.getAttribute('position').count) / 3;
  });
  return n;
}

function insideOut(mesh) {
  const geo = mesh.geometry;
  const pos = geo.getAttribute('position');
  const nor = geo.getAttribute('normal');
  const idx = geo.index;
  const count = idx ? idx.count : pos.count;
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const c = new THREE.Vector3();
  const n = new THREE.Vector3();
  const f = new THREE.Vector3();
  let bad = 0;
  for (let i = 0; i < count; i += 3) {
    const [ia, ib, ic] = [0, 1, 2].map((k) => (idx ? idx.getX(i + k) : i + k));
    a.fromBufferAttribute(pos, ia);
    b.fromBufferAttribute(pos, ib);
    c.fromBufferAttribute(pos, ic);
    f.subVectors(b, a).cross(n.subVectors(c, a));
    if (f.lengthSq() < 1e-14) continue;
    n.fromBufferAttribute(nor, ia).add(b.fromBufferAttribute(nor, ib)).add(c.fromBufferAttribute(nor, ic));
    if (f.dot(n) <= 0) bad++;
  }
  return bad;
}

const { props, mats } = setup();
const built = new Map(Object.keys(PROPS).map((name) => [name, props.build(name, { seed: 3 })]));

test('props: the factory answers for the whole catalogue', () => {
  assert.deepEqual(props.names(), Object.keys(PROPS));
  assert.ok(props.has('sedan') && !props.has('unicorn'));
  assert.deepEqual(props.stats().fallbacks, [], 'no prop falls back to a box');
  assert.deepEqual(mats.unknown, [], 'every material is a catalogue name');
  for (const [name, prop] of built) {
    const def = PROPS[name];
    assert.ok(prop.object.isGroup, name);
    assert.equal(prop.object.name, name);
    assert.deepEqual(prop.size, def.size, `${name} size`);
    assert.notEqual(prop.size, def.size, `${name}: the size is a copy`);
    assert.equal(prop.surface, def.surface, `${name} surface`);
    assert.ok(Array.isArray(prop.colliders), name);
    assert.equal(prop.fallback, undefined, `${name} is modelled`);
    if (def.dynamic) assert.equal(prop.dynamic, true, `${name} is dynamic`);
    if (prop.dynamic) assert.equal(prop.object.userData.noMerge, true, `${name} is kept out of the merge`);
    if (prop.update || prop.setState) assert.equal(prop.dynamic, true, `${name} animates, so it is dynamic`);
    let meshes = 0;
    prop.object.traverse((o) => {
      if (!o.isMesh) return;
      meshes++;
      for (const attr of ['position', 'normal', 'uv']) assert.ok(o.geometry.getAttribute(attr), `${name}: ${o.name} has ${attr}`);
      const pos = o.geometry.getAttribute('position').array;
      for (let i = 0; i < pos.length; i++) assert.ok(Number.isFinite(pos[i]), `${name}: ${o.name} has a bad vertex`);
    });
    assert.ok(meshes > 0 && meshes <= 30, `${name}: ${meshes} meshes`);
  }
});

test('props: an unknown name or a broken builder gives a plain box, not an exception', () => {
  const warn = console.warn;
  const said = [];
  console.warn = (...args) => said.push(args.join(' '));
  try {
    const { props: fresh } = setup();
    const ghost = fresh.build('no_such_prop');
    assert.equal(ghost.fallback, true);
    assert.deepEqual(ghost.size, [1, 1, 1]);
    assert.equal(ghost.colliders.length, 1);
    fresh.build('no_such_prop');
    assert.equal(said.length, 1, 'warned once');
    assert.deepEqual(fresh.stats().fallbacks, ['no_such_prop']);
  } finally {
    console.warn = warn;
  }
});

test('props: every model fits its catalogue box', () => {
  for (const [name, prop] of built) {
    const [L, H, W] = prop.size;
    const box = solidBounds(prop);
    const slack = OVERHANG[name] || {};
    const sx = FIT + (slack.x || 0);
    const sz = FIT + (slack.z || 0);
    const where = `${name}: x ${box.min.x.toFixed(2)}…${box.max.x.toFixed(2)}, y ${box.min.y.toFixed(2)}…${box.max.y.toFixed(2)}, z ${box.min.z.toFixed(2)}…${box.max.z.toFixed(2)}`;
    assert.ok(box.min.x >= -L / 2 - sx && box.max.x <= L / 2 + sx, where);
    assert.ok(box.min.z >= -W / 2 - sz && box.max.z <= W / 2 + sz, where);
    assert.ok(box.min.y >= -FIT && box.max.y <= H + FIT + (slack.y || 0), where);
    // …and fills a fair part of it: nothing is a token placeholder.
    assert.ok(box.max.y >= H * 0.6, `${name} is only ${box.max.y.toFixed(2)} m tall in a ${H} m box`);
  }
});

test('props: colliders are inside the footprint, well formed, and absent where the catalogue says so', () => {
  const SURFACES = ['asphalt', 'concrete', 'metal', 'wood', 'rubber', 'glass', 'dirt', 'brick', 'car', 'cloth'];
  for (const [name, prop] of built) {
    const def = PROPS[name];
    const [L, H, W] = prop.size;
    if (def.noCollide) {
      assert.equal(prop.colliders.length, 0, `${name} must not collide`);
      continue;
    }
    assert.ok(prop.colliders.length >= 1 && prop.colliders.length <= 5, `${name}: ${prop.colliders.length} colliders`);
    for (const c of prop.colliders) {
      for (let k = 0; k < 3; k++) assert.ok(c.max[k] > c.min[k], `${name}: an empty collider`);
      assert.ok(c.min[0] >= -L / 2 - 0.02 && c.max[0] <= L / 2 + 0.02, `${name}: collider leaves the box in x`);
      assert.ok(c.min[2] >= -W / 2 - 0.02 && c.max[2] <= W / 2 + 0.02, `${name}: collider leaves the box in z`);
      assert.ok(c.min[1] >= 0 && c.max[1] <= H + 0.02, `${name}: collider leaves the box in y`);
      if (!c.playerOnly) assert.ok(SURFACES.includes(c.surface), `${name}: surface '${c.surface}'`);
    }
    // The colliders are the instance's own: changing them must not leak into the next build.
    prop.colliders[0].min[0] = -99;
    assert.notEqual(props.build(name, { seed: 3 }).colliders[0].min[0], -99, `${name}: colliders are copies`);
  }
});

test('props: triangle budgets', () => {
  let total = 0;
  for (const [name, prop] of built) {
    const n = triangles(prop);
    total += n;
    assert.ok(n >= 8 && n <= 2200, `${name}: ${n} triangles`);
  }
  const sedan = triangles(built.get('sedan'));
  assert.ok(sedan >= 600 && sedan <= 1200, `a parked sedan is ${sedan} triangles (600…1200)`);
  assert.ok(total < 150000, `the catalogue is ${total} triangles (budget 150 000)`);
  assert.ok(total < 45000, `the catalogue grew to ${total} triangles: was that meant?`);
});

test('props: no face is inside out', () => {
  for (const [name, prop] of built) {
    let bad = 0;
    prop.object.traverse((o) => {
      // Lattices and light shafts are drawn from both sides; their winding carries no meaning.
      if (!o.isMesh || isEffect(o) || o.material.name === 'props_grid' || o.material.side === THREE.DoubleSide) return;
      bad += insideOut(o);
    });
    // Hoses bent through a tight curve may fold a sliver or two.
    assert.ok(bad <= 2, `${name}: ${bad} triangles face inward`);
  }
});

test('props: geometry is shared between instances, materials follow the options', () => {
  const { props: fresh, mats: lib } = setup();
  const a = fresh.build('sedan', { seed: 8 });
  const b = fresh.build('sedan', { seed: 8 });
  const c = fresh.build('sedan', { seed: 8, color: 0x123456 });
  const paint = (prop) => prop.object.children.find((m) => m.name === '@paint');
  assert.equal(paint(a).geometry, paint(b).geometry, 'same seed, same geometry object');
  assert.equal(paint(a).material, paint(b).material, 'same seed, same paint');
  assert.equal(paint(c).geometry, paint(a).geometry);
  assert.equal(paint(c).material.userData.opts.color, 0x123456, 'opts.color repaints');
  assert.equal(paint(a).material.name, 'car_paint');
  // Seeds spread over the palette, and nothing but the catalogue's materials is asked for.
  const colours = new Set();
  for (let seed = 0; seed < 40; seed++) colours.add(paint(fresh.build('sedan', { seed })).material.userData.opts.color);
  assert.ok(colours.size >= 6, `40 sedans in only ${colours.size} colours`);
  assert.equal(paint(fresh.build('taxi', { seed: 5 })).material.userData.opts.color, look.palette.taxi);
  assert.equal(paint(fresh.build('van', { variant: 'vulture' })).material.userData.opts.color, 0x1a1c20);
  assert.equal(paint(fresh.build('van', { variant: 'vulture', color: 0x16181b })).material.userData.opts.color, 0x16181b);
  assert.deepEqual(lib.unknown, []);
  // Without a seed the props stream decides, the same way for the same world seed.
  const one = setup(7).props.build('sedan');
  const two = setup(7).props.build('sedan');
  assert.equal(paint(one).material.userData.opts.color, paint(two).material.userData.opts.color);
  // A dome light is a material choice, never a different mesh.
  const lit = fresh.build('sedan', { seed: 8, lit: true });
  const glass = (prop) => prop.object.children.find((m) => m.name === '@glass');
  assert.equal(glass(lit).geometry, glass(a).geometry);
  // Lit glass is its own catalogue material (it glows at night only), the unlit one plain car glass.
  assert.equal(glass(lit).material.name, 'glass_car_lit', 'lit glass glows');
  assert.ok(catalog.MATERIALS.glass_car_lit.emissive, 'the lit glass carries its glow in the catalogue');
  assert.equal(glass(fresh.build('sedan', { seed: 8, lit: false })).material.name, 'glass_car');
});

test('props: a crouched player is hidden behind a sedan, a standing one sees over the bonnet', () => {
  const physics = createPhysics({ THREE });
  physics.setBounds({ minX: -20, maxX: 20, minZ: -20, maxZ: 20 });
  const sedan = built.get('sedan');
  for (const c of sedan.colliders) {
    physics.addBox({ min: c.min, max: c.max, surface: c.surface });
  }
  const [L, , W] = sedan.size;
  const crouch = 1.05;
  const stand = 1.68;
  const see = (ax, ay, az, bx, by, bz) => physics.lineOfSight(new THREE.Vector3(ax, ay, az), new THREE.Vector3(bx, by, bz));
  // Crouched just behind the car: nobody on the other side sees that eye, whichever part of the car is between.
  for (let x = -L / 2 + 0.15; x <= L / 2 - 0.15; x += 0.25) {
    assert.equal(see(x, crouch, -W / 2 - 0.5, x, crouch, W / 2 + 6), false, `a level sight line across the car at x = ${x.toFixed(2)}`);
    assert.equal(see(x, crouch, -W / 2 - 0.5, x, 1.6, W / 2 + 12), false, `a Goon's eye 12 m off, x = ${x.toFixed(2)}`);
  }
  assert.equal(see(-L / 2 - 0.5, crouch, 0, L / 2 + 8, 1.6, 0), false, 'along the length of the car too');
  // Standing behind the bonnet: the far side is in plain view, and so is a man 4 m beyond it.
  const bonnet = L / 2 - 0.9;
  assert.equal(see(bonnet, stand, -W / 2 - 0.5, bonnet, stand, W / 2 + 6), true, 'level over the bonnet');
  assert.equal(see(bonnet, stand, -W / 2 - 0.5, bonnet, 1.2, W / 2 + 4), true, 'down at a chest beyond the bonnet');
  assert.equal(see(-L / 2 + 0.7, stand, -W / 2 - 0.5, -L / 2 + 0.7, 1.2, W / 2 + 4), true, 'and over the boot');
  // The roof still blocks: standing eye to standing eye across the cabin from close up.
  assert.equal(see(-0.2, 1.3, -W / 2 - 0.3, -0.2, 1.3, W / 2 + 0.3), false, 'the cabin is solid at 1.3 m');
  // The lower box is the whole footprint and tops out just above a crouched eye.
  const lower = sedan.colliders[0];
  assert.ok(lower.max[1] > crouch && lower.max[1] < 1.15, `body collider top ${lower.max[1]}`);
  assert.equal(lower.surface, 'car');
  assert.equal(sedan.colliders[1].surface, 'glass');
  assert.ok(Math.abs(sedan.colliders[1].max[1] - 1.45) < 0.01, 'the cabin collider reaches the roof');
});

test('props: taller vehicles are hard cover, low props are waist high', () => {
  const top = (name) => Math.max(...built.get(name).colliders.map((c) => c.max[1]));
  for (const name of ['van', 'box_truck', 'ipx_truck']) assert.ok(top(name) > 2.1, `${name} is hard cover`);
  for (const [name, height] of [['jersey_barrier', 0.81], ['trash_bags', 0.62], ['milk_crates', 0.9], ['traffic_barrel', 0.98], ['dumpster', 1.3], ['mailbox', 1.2]]) {
    assert.ok(Math.abs(top(name) - height) < 0.02, `${name} collider top ${top(name)}`);
  }
  // You can walk under a car on the lift and under the bus shelter's roof.
  const lift = setup().props.build('car_lift', { variant: 'car' });
  const body = lift.colliders.filter((c) => c.surface === 'car' || c.surface === 'glass');
  assert.equal(body.length, 2);
  assert.ok(Math.min(...body.map((c) => c.min[1])) > 1.85, 'the raised car clears a standing player');
  assert.ok(body.every((c) => c.noNav));
  assert.ok(built.get('bus_shelter').colliders.some((c) => c.min[1] > 2.2 && c.noNav), 'the shelter roof');
  // Bleachers are stairs: each row at most a step (0.42 m) above the one before.
  const rows = built.get('bleachers').colliders.map((c) => c.max[1]).sort((a, b) => a - b);
  assert.equal(rows.length, 4);
  rows.reduce((prev, y) => {
    assert.ok(y - prev <= 0.42 + 1e-9, `a ${(y - prev).toFixed(2)} m step`);
    return y;
  }, 0);
});

test('props: lamp hints', () => {
  const KINDS = ['street', 'el', 'work', 'flood', 'neon', 'window'];
  for (const [name, prop] of built) {
    for (const hint of prop.lights || []) {
      assert.equal(hint.pos.length, 3, name);
      assert.ok(Number.isFinite(hint.color) && hint.intensity > 0 && hint.range > 0, name);
      assert.ok(KINDS.includes(hint.kind), `${name}: lamp kind '${hint.kind}'`);
      if (hint.dir) assert.ok(Math.abs(Math.hypot(...hint.dir) - 1) < 0.05, `${name}: lamp dir is a unit vector`);
    }
  }
  const lamp = built.get('street_lamp').lights;
  assert.equal(lamp.length, 1);
  assert.equal(lamp[0].kind, 'street');
  assert.equal(lamp[0].color, look.palette.sodium);
  assert.ok(lamp[0].pos[1] > 7 && lamp[0].pos[2] > 1.5, 'the hint sits at the head, out over the +Z side');
  assert.equal(built.get('court_light').lights[0].kind, 'flood');
  assert.equal(built.get('floodlight_stand').lights[0].kind, 'work');
  for (const name of ['bus_shelter', 'phone_booth', 'vending_machine', 'lot_booth', 'billboard', 'food_cart', 'ipx_truck']) {
    assert.ok(built.get(name).lights.length >= 1, `${name} lights the street`);
  }
  // Switched off, a lamp is dark and says nothing to atmos.
  const { props: fresh } = setup();
  for (const name of ['street_lamp', 'court_light', 'floodlight_stand']) assert.equal(fresh.build(name, { on: false }).lights, undefined, name);
  for (const name of ['bus_shelter', 'vending_machine', 'lot_booth', 'billboard']) assert.equal(fresh.build(name, { lit: false }).lights, undefined, name);
  // Hints are copies too.
  lamp[0].pos[1] = -1;
  assert.ok(fresh.build('street_lamp').lights[0].pos[1] > 7);
});

test('props: anchors', () => {
  const need = {
    food_cart: ['steam', 'propane'], manhole: ['steam'], burned_car: ['smolder'], generator: ['exhaust'], hydrant_open: ['spray'],
    propane_tank: ['jet'], welding_rack: ['jet'], master_case: ['boombox', 'beacon', 'reel'], ipx_truck: ['rearDoor', 'exhaust'],
  };
  for (const [name, ids] of Object.entries(need)) {
    for (const id of ids) {
      const a = built.get(name).anchors[id];
      assert.ok(a && a.pos.length === 3 && a.dir.length === 3, `${name}.anchors.${id}`);
    }
  }
  const spray = built.get('hydrant_open');
  assert.ok(spray.anchors.spray.dir[2] > 0.9, 'the hydrant sprays toward +Z');
  assert.ok(spray.object.userData.spray.z > 0.9, 'and tells atmos so');
});

test('props: master_case states', () => {
  const { props: fresh } = setup();
  const reel = fresh.build('master_case', { seed: 1 });
  const { lid, bar, reel: tape, beacon, shaft, pool } = reel.nodes;
  assert.equal(typeof reel.setState, 'function');
  assert.equal(typeof reel.update, 'function');
  assert.equal(bar.parent, lid, 'the progress bar rides on the lid');

  // live: lid up, reel on show, lights on, no bar.
  reel.setState('live', 0);
  reel.update(1 / 60);
  assert.ok(lid.rotation.x < -1.2, 'lid open');
  assert.ok(tape.visible && beacon.visible && shaft.visible && pool.visible);
  assert.equal(bar.visible, false);

  // grabbing: the bar grows with t and nothing else changes.
  reel.setState('grabbing', 0.25);
  assert.equal(bar.visible, true);
  const quarter = bar.scale.x;
  reel.setState('grabbing', 0.75);
  assert.ok(Math.abs(quarter - 0.25) < 1e-6 && Math.abs(bar.scale.x - 0.75) < 1e-6);
  assert.ok(lid.rotation.x < -1.2 && tape.visible && beacon.visible);
  reel.setState('grabbing', 7);
  assert.equal(bar.scale.x, 1, 't is clamped');

  // letting go: back to live, bar gone.
  reel.setState('live', 0);
  assert.equal(bar.visible, false);

  // taken: lights out at once, the lid drops over the next third of a second.
  reel.setState('taken', 1);
  assert.equal(reel.state, 'taken');
  assert.ok(!tape.visible && !beacon.visible && !shaft.visible && !pool.visible && !bar.visible);
  assert.ok(lid.rotation.x < -1.2, 'still open on the frame it was taken');
  for (let i = 0; i < 30; i++) reel.update(1 / 60);
  assert.ok(Math.abs(lid.rotation.x) < 1e-9, 'shut');

  // A new run puts everything back.
  reel.setState('live', 0);
  reel.update(1 / 60);
  assert.ok(lid.rotation.x < -1.2 && tape.visible && beacon.visible);

  // Nobody calling update(): the state still shows.
  const idle = fresh.build('master_case', { seed: 2 });
  idle.setState('taken', 1);
  assert.ok(Math.abs(idle.nodes.lid.rotation.x) < 1e-9, 'without a loop the lid is simply shut');
  assert.equal(idle.nodes.reel.visible, false);

  // The solid part of the prop fits its box in every state.
  for (const state of ['live', 'grabbing', 'taken']) {
    const p = fresh.build('master_case', { seed: 3 });
    p.setState(state, 0.5);
    const box = solidBounds(p);
    assert.ok(box.max.y <= 1.05 + FIT + OVERHANG.master_case.y && box.min.z >= -0.3 - 0.05 && box.max.z <= 0.3 + 0.05, `${state}: ${box.max.y.toFixed(2)} tall, z ${box.min.z.toFixed(2)}…${box.max.z.toFixed(2)}`);
  }
});

test('props: ipx_truck states', () => {
  const truck = setup().props.build('ipx_truck');
  const { doorL, doorR, hazards, vaultLight } = truck.nodes;
  assert.equal(truck.state, 'idle');
  assert.equal(vaultLight.visible, false);
  // Idle: hazards blink, doors stay shut.
  const seen = new Set();
  for (let i = 0; i < 120; i++) {
    truck.update(1 / 30);
    seen.add(hazards.visible);
  }
  assert.deepEqual([...seen].sort(), [false, true], 'the hazards blink');
  assert.equal(doorL.rotation.y, 0);
  // Open: the doors swing apart, the vault lights up, the hazards hold.
  truck.setState('open');
  for (let i = 0; i < 60; i++) truck.update(1 / 30);
  assert.ok(doorL.rotation.y > 1.5 && doorR.rotation.y < -1.5, 'both doors wide');
  assert.equal(vaultLight.visible, true);
  assert.equal(hazards.visible, true);
  // Reset for the next run.
  truck.setState('idle');
  assert.equal(doorL.rotation.y, 0);
  assert.equal(vaultLight.visible, false);
  // The livery: IPX on both flanks (two quads), and the truck is a catalogue-sized hard cover.
  assert.ok(truck.colliders.every((c) => c.surface === 'car'));
});

test('props: explosives states', () => {
  const { props: fresh } = setup();
  for (const name of ['propane_tank', 'welding_rack']) {
    const prop = fresh.build(name);
    const { body, flame, wreck } = prop.nodes;
    assert.equal(prop.state, 'idle');
    assert.ok(body.visible && !flame.visible && !wreck.visible, `${name} idle`);
    const shell = body.children.find((mesh) => mesh.name === '@vc');
    const cold = shell.material;
    prop.setState('lit');
    assert.ok(body.visible && flame.visible && !wreck.visible, `${name} lit`);
    assert.equal(shell.material.name, 'props_vc_hot', `${name} glows while lit`);
    const before = flame.scale.y;
    prop.update(0.05);
    prop.update(0.05);
    assert.notEqual(flame.scale.y, before, `${name}: the flame moves`);
    prop.setState('gone');
    assert.ok(!body.visible && !flame.visible && wreck.visible, `${name} gone`);
    prop.setState('idle');
    assert.ok(body.visible && !flame.visible && !wreck.visible, `${name} restored`);
    assert.equal(shell.material, cold, `${name} cools down`);
    // One draw call for the body: twenty of these stand on the block.
    assert.ok(body.children.length <= 2, `${name} body is ${body.children.length} meshes`);
    assert.equal(prop.colliders.length, 1);
    // Idle, it fits its box.
    const [L, H, W] = prop.size;
    const box = solidBounds(prop);
    assert.ok(box.max.y <= H + FIT && box.max.x <= L / 2 + FIT && box.max.z <= W / 2 + FIT, `${name} idle bounds`);
  }
});

test('props: with the real fx module the explosives leave the flame to it', () => {
  const { G, props: fresh } = setup();
  G.build = { dev: true, stubbed: ['audio'] };
  const tank = fresh.build('propane_tank');
  tank.setState('lit');
  assert.equal(tank.nodes.flame.visible, false, 'fx draws the jet');
  assert.equal(tank.nodes.body.children.find((mesh) => mesh.name === '@vc').material.name, 'props_vc_hot');
  G.build.stubbed.push('fx');
  tank.setState('lit');
  assert.equal(tank.nodes.flame.visible, true, 'with fx stubbed the prop shows its own');
});

test('props: traffic_light cycles', () => {
  const light = setup().props.build('traffic_light', { seed: 0 });
  const { red, amber, green, stop, walk } = light.nodes;
  const seen = { red: 0, amber: 0, green: 0, walk: 0 };
  for (let i = 0; i < 31 * 20; i++) {
    light.update(1 / 20);
    const on = [red, amber, green].filter((n) => n.visible);
    assert.equal(on.length, 1, 'exactly one signal lamp is lit');
    if (red.visible) seen.red++;
    if (amber.visible) seen.amber++;
    if (green.visible) seen.green++;
    if (walk.visible) {
      seen.walk++;
      assert.ok(red.visible && !stop.visible, 'walk only while the avenue has red');
    }
  }
  assert.ok(seen.green > seen.red * 0.8 && seen.amber > 0 && seen.amber < seen.green / 3 && seen.walk > 0, JSON.stringify(seen));
});

test('props: variants', () => {
  const { props: fresh } = setup();
  const count = (prop) => triangles(prop);
  // The Vultures' van has its doors open (more geometry, wider than its box); a plain van can too.
  const plain = fresh.build('van', { seed: 1 });
  const vulture = fresh.build('van', { variant: 'vulture' });
  assert.ok(count(vulture) > count(plain));
  assert.ok(solidBounds(vulture).min.x < -2.7, 'the open doors swing out behind');
  assert.equal(count(fresh.build('van', { variant: 'vulture', open: false })) < count(vulture), true);
  assert.ok(solidBounds(fresh.build('van', { open: true })).min.x < -2.7);
  // Lift: arms up and empty by default, 'car' brings a sedan, 'down' lowers the arms.
  const lift = fresh.build('car_lift');
  const withCar = fresh.build('car_lift', { variant: 'car' });
  assert.ok(count(withCar) > count(lift) + 600);
  assert.equal(lift.colliders.length, 2);
  // Scrim, cart on its side, the fire escape's ends, sign faces, awning lettering.
  assert.ok(count(fresh.build('fence_tall', { variant: 'scrim' })) > count(fresh.build('fence_tall')));
  assert.ok(solidBounds(fresh.build('shopping_cart', { variant: 'tipped' })).max.y < 0.7);
  assert.ok(solidBounds(fresh.build('fire_escape', { variant: 'bottom' })).min.y < -1);
  assert.ok(solidBounds(fresh.build('fire_escape', { variant: 'top' })).max.y <= 3.01);
  for (const variant of ['nopark', 'bus', 'oneway', 'stop', 'street']) assert.ok(count(fresh.build('sign_post', { variant, text: '187 ST' })) > 12, variant);
  assert.ok(count(fresh.build('awning', { text: 'PAWN & GOLD', color: 0x1f5a3a })) > count(fresh.build('awning')));
  assert.ok(fresh.build('hydrant_open', { spray: false }).nodes.jet === undefined, 'no built-in jet on request');
  assert.deepEqual(fresh.stats().fallbacks, []);
});
