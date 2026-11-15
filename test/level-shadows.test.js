// The shadow pass at its source: the block built with the real prop factory (texture-free materials).
// Props that stop casting must be out of the sun at every time of day, vehicle and clutter hulls must sit
// inside what they stand for, and the level's casting triangles stay inside a budget.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import * as brand from '../src/config/brand.js';
import * as catalog from '../src/config/catalog.js';
import * as flow from '../src/config/flow.js';
import * as look from '../src/config/look.js';
import * as text from '../src/config/text.js';
import { createEvents } from '../src/core/events.js';
import { createRng } from '../src/core/rng.js';
import { createLevel, sunDirections, sunReaches } from '../src/level.js';
import { carve } from '../src/level/buildings.js';
import { createPhysics } from '../src/physics.js';
import { createProps } from '../src/props.js';
import { fakeMats } from './level-helpers.js';

const G = {
  THREE,
  params: {},
  events: createEvents(),
  rng: createRng(1994),
  time: { t: 0, dt: 1 / 60, frame: 0, real: 0 },
  config: { brand, text, flow, catalog, look },
  quality: { name: 'low' },
  scene: new THREE.Scene(),
  camera: new THREE.PerspectiveCamera(),
};
G.mats = fakeMats();
G.physics = createPhysics(G);
G.props = createProps(G);
const built = [];
const build = G.props.build.bind(G.props);
G.props.build = (name, o) => {
  const prop = build(name, o);
  built.push({ name, prop });
  return prop;
};
G.level = await createLevel(G);

const tris = (m) => (m.geometry.index ? m.geometry.index.count : m.geometry.getAttribute('position').count) / 3;
const meshes = (object) => {
  const out = [];
  object.traverse((m) => {
    if (m.isMesh) out.push(m);
  });
  return out;
};

test('a prop that casts nothing is out of the sun by day and by night', () => {
  const dirs = sunDirections(look);
  assert.equal(dirs.length, 2, 'day and night');
  const box = new THREE.Box3();
  const p = new THREE.Vector3();
  let checked = 0;
  for (const { name, prop } of built) {
    const all = meshes(prop.object);
    if (prop.dynamic || !all.length || all.some((m) => m.castShadow)) continue;
    if (all.every((m) => m.name === 'shadow-hull' || !m.castShadow) && all.some((m) => m.name === 'shadow-hull')) continue;
    if (prop.object.position.y > 4) continue; // rooftop clutter: its shadow lands on its own roof
    if (catalog.PROPS[name] && catalog.PROPS[name].size[1] <= 0.3) continue; // flat things never cast
    box.setFromObject(prop.object);
    const top = p.set((box.min.x + box.max.x) / 2, box.max.y - 0.03, (box.min.z + box.max.z) / 2);
    for (const d of dirs) assert.equal(sunReaches(G.physics, top, d), false, `${name} at (${top.x.toFixed(1)}, ${top.z.toFixed(1)}) sees the sun`);
    checked++;
  }
  assert.ok(G.level.stats.sunless >= 40, `${G.level.stats.sunless} props found out of the sun`);
  assert.ok(checked >= 40);
  // …and props standing in the open keep their shadows.
  const open = built.filter(({ name, prop }) => name === 'traffic_barrel' && Math.abs(prop.object.position.z) < 4);
  assert.ok(open.length >= 3);
  for (const { prop } of open) assert.ok(meshes(prop.object).some((m) => m.castShadow), 'a barrel in the road casts');
});

test('vehicles, pallet stacks and crates cast through a hull inside their own colliders', () => {
  let hulls = 0;
  for (const { name, prop } of built) {
    if (!['sedan', 'taxi', 'suv', 'van', 'pickup', 'box_truck', 'burned_car', 'pallet_stack', 'crate_wood'].includes(name)) continue;
    const all = meshes(prop.object);
    const hull = all.filter((m) => m.name === 'shadow-hull');
    assert.ok(hull.length >= 1 && hull.length <= 12, `${name}: ${hull.length} hull boxes`);
    assert.equal(hull[0].material.colorWrite, false, 'shadow map only');
    assert.equal(hull[0].material.depthWrite, false);
    if (meshes(prop.object).some((m) => m.castShadow)) {
      for (const m of all) assert.equal(m.castShadow, m.name === 'shadow-hull', `${name}: only the hull casts (${m.name})`);
    }
    // In the prop's own frame every hull box lies inside one of its colliders.
    for (const m of hull) {
      m.geometry.computeBoundingBox();
      const b = m.geometry.boundingBox.clone().translate(m.position);
      const inside = prop.colliders.some((c) => b.min.x >= c.min[0] - 1e-6 && b.max.x <= c.max[0] + 1e-6 && b.min.y >= c.min[1] - 1e-6 && b.max.y <= c.max[1] + 1e-6 && b.min.z >= c.min[2] - 1e-6 && b.max.z <= c.max[2] + 1e-6);
      assert.ok(inside, `${name}: a hull box sticks out of its colliders`);
    }
    hulls++;
  }
  assert.ok(hulls >= 40, `${hulls} props with hulls`);
});

test('the level casts at most 110 k triangles into the shadow map', () => {
  let cast = 0;
  let all = 0;
  G.level.root.traverse((m) => {
    if (!m.isMesh) return;
    all += tris(m);
    if (m.castShadow) cast += tris(m);
  });
  assert.ok(cast <= 110000, `${cast} casting triangles of ${all}`);
  assert.ok(all <= 200000, `${all} triangles in the level`);
});

test('carve: a box less a cut is the slabs around it', () => {
  const box = { min: [0, 0, 0], max: [4, 3, 2] };
  assert.deepEqual(carve(box, { min: [5, 0, 0], max: [6, 1, 1] }), [box], 'a miss leaves it whole');
  const pieces = carve(box, { min: [1, 0.2, -1], max: [2, 2, 0.4] });
  const volume = (b) => (b.max[0] - b.min[0]) * (b.max[1] - b.min[1]) * (b.max[2] - b.min[2]);
  const total = pieces.reduce((sum, b) => sum + volume(b), 0);
  assert.ok(Math.abs(total - (24 - 1 * 1.8 * 0.4)) < 1e-9, `volume ${total}`);
  for (const b of pieces) for (let a = 0; a < 3; a++) assert.ok(b.min[a] < b.max[a]);
});

test('door recesses are open to rounds: a shot into a shop door lands on the door', () => {
  // The pawn shop's door (storefront x −30…−24, door at 0.9 of the front): the recess goes 0.36 m in.
  const hit = G.physics.raycast(new THREE.Vector3(-25.5, 1.4, 8), new THREE.Vector3(0, 0, 1), 10);
  assert.ok(hit && hit.point.z > 11.3 && hit.point.z < 11.4, `door hit at z ${hit && hit.point.z.toFixed(3)}`);
  // …and a shot at its display window stops on the glass, not on the wall behind it.
  const glass = G.physics.raycast(new THREE.Vector3(-28.5, 1.6, 8), new THREE.Vector3(0, 0, 1), 10);
  assert.ok(glass && glass.point.z > 10.9 && glass.point.z < 10.97, `window hit at z ${glass && glass.point.z.toFixed(3)}`);
});
