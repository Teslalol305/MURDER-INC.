// The block, built for real in node (real physics, stub props, texture-free materials): the contract
// shape of G.level, the authored data, walkability between everything that matters, the cover rules
// around the reels, the explosive placement rules, sightlines along the avenue and the seals.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { missingMembers } from '../src/core/contract.js';
import { REELS } from '../src/level/data.js';
import { BOUNDS, BUILDINGS, CAGE, SHED, SHOP, floorAt, zoneAt } from '../src/level/layout.js';
import { buildLevel } from './level-helpers.js';

const G = buildLevel();
const { level, physics } = G;
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const flat = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
const at = (p) => `(${p.x.toFixed(1)}, ${p.z.toFixed(1)})`;

// The explosives module stands a solid collider at every entry of level.explosives: do the same here,
// so walkability is judged with the tanks and racks in place.
const EXPLOSIVE_SIZE = { propane: [0.32, 0.6, 0.32], rack: [0.9, 1.6, 0.5] };
const explosiveBoxes = level.explosives.map((e) => {
  const [length, height, width] = EXPLOSIVE_SIZE[e.type];
  const sin = Math.abs(Math.sin(e.yaw));
  const cos = Math.abs(Math.cos(e.yaw));
  const hx = (cos * length + sin * width) / 2;
  const hz = (sin * length + cos * width) / 2;
  return { entry: e, min: V(e.pos.x - hx, e.pos.y, e.pos.z - hz), max: V(e.pos.x + hx, e.pos.y + height, e.pos.z + hz) };
});
const worldBoxes = physics.boxes.slice(); // before the explosives go in
for (const b of explosiveBoxes) physics.addBox({ min: b.min, max: b.max, surface: 'metal', tag: 'explosive' });

const groundSpawns = level.enemySpawns.filter((s) => s.type === 'ground');
const airSpawns = level.enemySpawns.filter((s) => s.type === 'air');

// ------------------------------------------------------------------------------------------------

test('contract: G.level exposes every member of CONTRACT 6.10', () => {
  assert.deepEqual(missingMembers('level', level), []);
  assert.ok(level.root.isObject3D);
  assert.deepEqual(level.bounds, BOUNDS);
  assert.deepEqual(physics.bounds, BOUNDS, 'physics.setBounds was called');
  assert.equal(level.root.parent, G.scene, 'the level adds its root to the scene itself');
});

test('static geometry is merged: a mesh per material, dynamic props kept apart', () => {
  const [merged, dynamic] = level.root.children;
  assert.equal(merged.name, 'static');
  assert.equal(dynamic.name, 'dynamic');
  const materials = new Set();
  for (const mesh of merged.children) {
    assert.ok(mesh.isMesh, 'only merged meshes under the static group');
    assert.equal(mesh.matrixAutoUpdate, false);
    materials.add(`${mesh.material.uuid}|${mesh.castShadow}|${mesh.receiveShadow}`);
  }
  assert.equal(materials.size, merged.children.length, 'no two merged meshes share a material and shadow flags');
  assert.ok(level.stats.sourceMeshes > 2000, 'thousands of parts went in');
  assert.ok(level.stats.triangles > 30000 && level.stats.triangles < 400000, `${level.stats.triangles} triangles`);
  for (const o of level.objectives) assert.ok(dynamic.getObjectById(o.prop.object.id), 'reel cases are dynamic');
  assert.ok(dynamic.getObjectById(level.extraction.prop.object.id), 'the truck is dynamic');
});

test('objectives, extraction and start follow the blueprint', () => {
  assert.deepEqual(level.objectives.map((o) => o.id), ['reel1', 'reel2', 'reel3']);
  assert.deepEqual(level.objectives.map((o) => o.code), ['1', '2', '3']);
  assert.deepEqual(level.objectives.map((o) => o.zone), ['avenue', 'shop', 'lot']);
  for (const o of level.objectives) {
    assert.equal(zoneAt(o.pos.x, o.pos.z), o.zone, `${o.id} stands in its zone`);
    assert.equal(typeof o.prop.setState, 'function');
    assert.ok(o.label.length > 0);
  }
  const [r1, r2, r3] = level.objectives.map((o) => o.pos);
  assert.ok(flat(r1, V(-4, 0, 1)) < 3, 'reel 1 mid-avenue');
  assert.ok(flat(r2, V(-9, 0, -21)) < 3, 'reel 2 on the shop floor');
  assert.ok(r3.x > CAGE.minX && r3.x < CAGE.maxX && r3.z > CAGE.minZ && r3.z < CAGE.maxZ, 'reel 3 inside the cage');
  assert.equal(level.interiorAt(r2), 1, 'reel 2 is indoors');
  assert.equal(level.interiorAt(r1), 0);

  const ex = level.extraction;
  assert.equal(ex.radius, 2.5);
  assert.equal(ex.code, 'IPX');
  assert.equal(ex.label, 'IPX truck');
  assert.ok(ex.pos.x > 30 && ex.pos.z > 22, 'the truck waits in the south-east corner of the lot');
  assert.equal(typeof ex.prop.setState, 'function');

  const start = level.playerStart;
  assert.equal(zoneAt(start.pos.x, start.pos.z), 'west');
  assert.ok(start.pos.z > 7 && start.pos.z < 11, 'on the south sidewalk');
  assert.equal(start.pos.y, 0.15, 'standing on the sidewalk slab');
  assert.ok(Math.abs(start.yaw + Math.PI / 2) < 1e-9, 'facing east');
  assert.equal(physics.overlapsCylinder(start.pos.x, start.pos.z, 0.32, start.pos.y + 0.45, start.pos.y + 1.8), false, 'room to stand');
});

test('zones tile the block; zoneAt, floorAt, groundSurfaceAt and interiorAt answer sensibly', () => {
  assert.deepEqual(level.zones.map((z) => z.id), ['west', 'shop', 'avenue', 'lot']);
  assert.equal(level.zoneAt(-40, 0), 'west');
  assert.equal(level.zoneAt(-10, -20), 'shop');
  assert.equal(level.zoneAt(0, 0), 'avenue');
  assert.equal(level.zoneAt(0, 28), 'avenue');
  assert.equal(level.zoneAt(35, -20), 'lot');
  assert.equal(level.zoneAt(35, 25), 'lot');
  assert.equal(level.zoneAt(200, 0), 'lot', 'points outside go to the nearest zone');

  assert.equal(floorAt(0, 0), 0, 'road');
  assert.equal(floorAt(-30, 9), 0.15, 'south sidewalk');
  assert.equal(floorAt(-12, -9), 0, 'the roll door driveway is at road level');
  assert.equal(floorAt(31, 9), 0, 'the lot entrance too');
  for (const [x, z] of [[-30, 9], [-30, -9], [15.6, -7.6], [40, 9], [27, -11.5]]) {
    assert.equal(physics.groundHeight(x, z, 1), 0.15, `a slab under (${x}, ${z})`);
  }
  for (const [x, z] of [[0, 0], [-12, -9], [31, 9], [8.5, -9], [-10, 9]]) {
    assert.equal(physics.groundHeight(x, z, 0.5), 0, `road level at (${x}, ${z})`);
  }

  assert.equal(level.groundSurfaceAt(0, 0), 'asphalt');
  assert.equal(level.groundSurfaceAt(-10, -20), 'concrete');
  assert.equal(level.groundSurfaceAt(-10, 18), 'dirt');
  assert.equal(level.groundSurfaceAt(35, -22), 'concrete');
  assert.equal(level.groundSurfaceAt(30, 20), 'asphalt');

  const box = level.interiorBoxes[0];
  assert.deepEqual([box.min.x, box.max.x, box.min.z, box.max.z], [SHOP.minX, SHOP.maxX, SHOP.minZ, SHOP.maxZ]);
  assert.equal(level.interiorAt(V(-9, 1.7, -21)), 1);
  assert.equal(level.interiorAt(V(-12, 1.7, -9)), 0, 'the sidewalk outside is outdoors');
  const doorstep = level.interiorAt(V(-12, 1.7, -10.4));
  assert.ok(doorstep > 0 && doorstep < 1, 'it fades across the doorway');
});

test('spawn points: about 28 on the ground and 16 in the air, by zone, none at the start', () => {
  assert.ok(groundSpawns.length >= 26 && groundSpawns.length <= 32, `${groundSpawns.length} ground spawns`);
  assert.ok(airSpawns.length >= 14 && airSpawns.length <= 18, `${airSpawns.length} air spawns`);
  for (const zone of ['shop', 'avenue', 'lot']) {
    assert.ok(groundSpawns.filter((s) => s.zone === zone).length >= 6, `ground spawns in ${zone}`);
    assert.ok(airSpawns.filter((s) => s.zone === zone).length >= 4, `air spawns in ${zone}`);
  }
  const start = level.playerStart.pos;
  for (const s of level.enemySpawns) {
    assert.notEqual(s.zone, 'west', `no spawn in the west zone ${at(s.pos)}`);
    assert.equal(s.zone, zoneAt(s.pos.x, s.pos.z));
    assert.ok(flat(s.pos, start) > 14, `spawn ${at(s.pos)} is well away from the start`);
    assert.ok(s.pos.x > BOUNDS.minX + 1 && s.pos.x < BOUNDS.maxX - 0.5 && s.pos.z > BOUNDS.minZ + 1 && s.pos.z < BOUNDS.maxZ - 0.5);
  }
  for (const s of groundSpawns) {
    assert.ok(physics.nav.isWalkable(s.pos.x, s.pos.z), `ground spawn ${at(s.pos)} is on a walkable cell`);
    assert.equal(s.pos.y, floorAt(s.pos.x, s.pos.z), 'and stands on the level floor');
    assert.equal(physics.overlapsCylinder(s.pos.x, s.pos.z, 0.3, s.pos.y + 0.45, s.pos.y + 1.8), false, `room for a Goon at ${at(s.pos)}`);
  }
  for (const s of airSpawns) {
    assert.ok(s.pos.y >= 8 && s.pos.y <= 17, `air spawn at a flying height (${s.pos.y})`);
    assert.equal(physics.overlapsCylinder(s.pos.x, s.pos.z, 0.6, s.pos.y - 0.6, s.pos.y + 0.6), false, `air spawn ${at(s.pos)} is in open air`);
    assert.ok(s.pos.y > physics.groundHeight(s.pos.x, s.pos.z) + 1.5, 'clear of the roof below it');
    // Never above the tracks: that is where the train runs.
    assert.ok(Math.abs(s.pos.z) > level.el.maxZ + 1.5, `air spawn ${at(s.pos)} is beside the El, not over it`);
  }
});

test('spawn points are hidden from the main sightlines', () => {
  // Seen from the start and from the middle of each travel lane's long stretches, at eye height.
  const eyes = [level.playerStart.pos.clone().setY(1.83), V(-30, 1.68, 2), V(-12, 1.68, -2), V(0, 1.68, 2), V(14, 1.68, 2), V(30, 1.68, -1)];
  let exposed = 0;
  for (const s of groundSpawns) {
    const chest = s.pos.clone().setY(s.pos.y + 1.2);
    const seenBy = eyes.filter((eye) => physics.lineOfSight(eye, chest)).length;
    assert.ok(seenBy <= 1, `ground spawn ${at(s.pos)} is visible from ${seenBy} of the avenue's vantage points`);
    exposed += seenBy;
  }
  assert.ok(exposed <= 6, `${exposed} spawn / vantage pairs are in plain sight`);
});

test('cover points: 50 or more, walkable, spread over every zone', () => {
  assert.ok(level.coverPoints.length >= 50, `${level.coverPoints.length} cover points`);
  for (const zone of ['shop', 'avenue', 'lot']) {
    assert.ok(level.coverPoints.filter((c) => c.zone === zone).length >= 12, `cover in ${zone}`);
  }
  const raised = level.coverPoints.filter((c) => c.pos.y > 0.5);
  assert.equal(raised.length, 3, 'two on the shed deck, one on the mezzanine');
  for (const c of level.coverPoints) {
    assert.equal(c.zone, zoneAt(c.pos.x, c.pos.z));
    if (c.pos.y > 0.5) continue;
    assert.ok(physics.nav.isWalkable(c.pos.x, c.pos.z), `cover point ${at(c.pos)} is on a walkable cell`);
    // A cover point is next to something: an obstacle that blocks walking within 1.6 m.
    let near = false;
    for (let a = 0; a < 16 && !near; a++) {
      const x = c.pos.x + Math.cos((a * Math.PI) / 8) * 1.5;
      const z = c.pos.z + Math.sin((a * Math.PI) / 8) * 1.5;
      near = !physics.nav.isWalkable(x, z);
    }
    assert.ok(near, `cover point ${at(c.pos)} stands beside cover`);
  }
});

test('each reel sits in an arena ringed by 4 to 8 pieces of low cover at 2–5 m', () => {
  for (const [i, reel] of REELS.entries()) {
    const pieces = new Set();
    for (const b of worldBoxes) {
      if (b.playerOnly || b.bulletOnly || !b.owner) continue; // props only
      const top = b.max.y - floorAt(reel.x, reel.z);
      if (b.min.y > 0.3 || top < 0.6 || top > 1.5) continue; // waist to chest high, standing on the ground
      const cx = Math.max(b.min.x, Math.min(reel.x, b.max.x));
      const cz = Math.max(b.min.z, Math.min(reel.z, b.max.z));
      const d = Math.hypot(cx - reel.x, cz - reel.z);
      if (d >= 1.5 && d <= 5) pieces.add(b.owner);
    }
    assert.ok(pieces.size >= 4, `reel ${i + 1} has ${pieces.size} pieces of low cover around it`);
    // Nothing crowds the case itself: the player can walk right round it.
    for (let a = 0; a < 12; a++) {
      const x = reel.x + Math.cos((a * Math.PI) / 6) * 1.4;
      const z = reel.z + Math.sin((a * Math.PI) / 6) * 1.4;
      assert.equal(physics.overlapsCylinder(x, z, 0.32, 0.45, 1.8), false, `clear ground beside reel ${i + 1} at angle ${a * 30}°`);
    }
  }
});

test('explosives: 18 to 22, both kinds, clear of the start, the reels and each other', () => {
  const list = level.explosives;
  assert.ok(list.length >= 18 && list.length <= 22, `${list.length} explosives`);
  assert.ok(list.filter((e) => e.type === 'propane').length >= 8);
  assert.ok(list.filter((e) => e.type === 'rack').length >= 5);
  const start = level.playerStart.pos;
  for (const [i, e] of list.entries()) {
    assert.ok(e.type === 'propane' || e.type === 'rack');
    assert.equal(typeof e.yaw, 'number');
    assert.ok(flat(e.pos, start) >= 7, `explosive ${at(e.pos)} is at least 7 m from the start`);
    for (const o of level.objectives) assert.ok(flat(e.pos, o.pos) >= 2.2, `explosive ${at(e.pos)} is at least 2.2 m from ${o.id}`);
    for (let j = 0; j < i; j++) {
      const other = list[j];
      if (Math.abs(other.pos.y - e.pos.y) > 1) continue;
      assert.ok(flat(e.pos, other.pos) >= 0.8, `explosives ${at(e.pos)} and ${at(other.pos)} do not stand in each other`);
    }
    // It stands on something: the road, a sidewalk or a deck.
    assert.ok(Math.abs(physics.groundHeight(e.pos.x, e.pos.z, e.pos.y + 0.05) - e.pos.y) < 0.02, `explosive ${at(e.pos)} stands on the floor`);
  }
  // No explosive is buried in a wall or a prop.
  for (const b of explosiveBoxes) {
    for (const w of worldBoxes) {
      if (w.playerOnly || w.max.y <= b.min.y + 0.05) continue;
      const dx = Math.min(b.max.x, w.max.x) - Math.max(b.min.x, w.min.x);
      const dy = Math.min(b.max.y, w.max.y) - Math.max(b.min.y, w.min.y);
      const dz = Math.min(b.max.z, w.max.z) - Math.max(b.min.z, w.min.z);
      assert.ok(!(dx > 0.04 && dy > 0.04 && dz > 0.04), `explosive ${at(b.entry.pos)} overlaps '${w.tag}'`);
    }
  }
  // Part of the cover layout: the named places of the design each have one.
  const nearAny = (x, z, r) => list.some((e) => Math.hypot(e.pos.x - x, e.pos.z - z) < r);
  assert.ok(nearAny(-5.7, -8.3, 2.5), 'propane at the food cart');
  assert.ok(nearAny(10, 9, 9.5), 'propane at the scaffold');
  assert.ok(nearAny(27.3, 12.6, 2.5), 'propane at the lot booth');
  assert.ok(list.some((e) => e.type === 'rack' && level.interiorAt(e.pos) === 1), 'a welding rack inside the shop');
  assert.ok(list.some((e) => e.type === 'rack' && level.interiorAt(e.pos) < 1 && e.pos.z < -7), 'and one outside it');
});

test('nav: the start, every reel, the truck, every ground spawn and cover point are connected', () => {
  const start = level.playerStart.pos;
  const targets = [
    ...level.objectives.map((o) => [o.id, o.pos, 1.3]), // the case itself is solid: stop beside it
    ['truck', level.extraction.pos, 0.6],
    ...groundSpawns.map((s, i) => [`ground spawn ${i} ${at(s.pos)}`, s.pos, 0.6]),
    ...level.coverPoints.filter((c) => c.pos.y < 0.5).map((c, i) => [`cover point ${i} ${at(c.pos)}`, c.pos, 0.6]),
  ];
  for (const [label, pos, slack] of targets) {
    const path = physics.nav.findPath(start, pos);
    assert.ok(path, `a path from the start to ${label}`);
    const end = path[path.length - 1];
    assert.ok(flat(end, pos) <= slack, `the path to ${label} ends ${flat(end, pos).toFixed(2)} m short`);
  }
  // And back again from the far end: reel 3 to the truck, the truck to the start.
  assert.ok(physics.nav.findPath(level.objectives[2].pos, level.extraction.pos));
  assert.ok(physics.nav.findPath(level.extraction.pos, start));
});

test('nav: every doorway and gate is open to walkers', () => {
  const doors = {
    'roll-up door': [(SHOP.roll.x0 + SHOP.roll.x1) / 2, SHOP.maxZ - 0.2],
    'second bay': [(SHOP.bay.x0 + SHOP.bay.x1) / 2, SHOP.maxZ - 0.2],
    'side door into the alley': [SHOP.maxX - 0.2, (SHOP.side.z0 + SHOP.side.z1) / 2],
    'alley mouth': [8.5, -11],
    'cage south gate': [(CAGE.southGate[0] + CAGE.southGate[1]) / 2, CAGE.maxZ],
    'cage west gate': [CAGE.minX, (CAGE.westGate[0] + CAGE.westGate[1]) / 2],
    'vacant lot gateway': [-10.3, 11.15],
    'lot entrance': [31.8, 11.15],
    'rear lane mouth': [22, 28.5],
    'gangway': [-25.1, -12],
    'foot of the shed stair': [level.vantage.stairsFoot.x, level.vantage.stairsFoot.z],
  };
  for (const [name, [x, z]] of Object.entries(doors)) assert.ok(physics.nav.isWalkable(x, z), `${name} at (${x}, ${z})`);
});

test('nav: the loops of the blueprint exist', () => {
  const length = (path) => path.reduce((sum, p, i) => (i ? sum + p.distanceTo(path[i - 1]) : 0), 0);
  const route = (a, b) => {
    const path = physics.nav.findPath(V(a[0], 0, a[1]), V(b[0], 0, b[1]));
    assert.ok(path, `path from (${a}) to (${b})`);
    return length(path);
  };
  // Vacant lot → rear lane → lot, without going back out onto the avenue (that way is over 65 m).
  assert.ok(route([-10, 14], [26, 28.5]) < 56, 'the rear lane links the vacant lot and the lot');
  // Through the shop: roll door → side door → alley.
  assert.ok(route([-12, -13], [8.5, -22]) < 27, 'the side door links the shop floor and the alley');
  // The alley is a way round the shop front.
  assert.ok(route([8.5, -28], [8.5, -9]) < 22, 'the alley runs out to the north sidewalk');
  // Both cage gates lead to the centre circle.
  assert.ok(route([34.5, -9], [35.2, -20]) < 16, 'south gate');
  assert.ok(route([23.5, -13], [30, -27.5]) < 26, 'west gate, by the cut');
  // The avenue is passable end to end on the road and on both sidewalks.
  assert.ok(route([-40, 0], [36, 0]) < 105, 'the roadway, chicanes and all');
  assert.ok(route([-36, -9.5], [40, -9.5]) < 100, 'north sidewalk');
  assert.ok(route([-36, 9.6], [40, 9.5]) < 100, 'south sidewalk');
});

test('the vantage: a walkable stair of low steps onto the shed deck', () => {
  const { stairsFoot, deck } = level.vantage;
  assert.equal(deck.y, SHED.deck);
  assert.equal(physics.groundHeight(deck.x, deck.z, deck.y + 0.1), SHED.deck, 'the deck is solid');
  // Walk it: a capsule pushed east from the foot climbs to the deck without jumping.
  const pos = stairsFoot.clone();
  const vel = V(0, 0, 0);
  let grounded = true;
  for (let i = 0; i < 400 && pos.x < SHED.x0 + 1.5; i++) {
    vel.set(3.2, grounded ? 0 : vel.y - 21 / 60, 0);
    grounded = physics.moveCapsule(pos, vel, 1 / 60, 0.32, 1.8, grounded).onGround;
  }
  assert.ok(pos.x >= SHED.x0 + 1.5, `the capsule got up the stair (stopped at x ${pos.x.toFixed(2)})`);
  assert.ok(Math.abs(pos.y - SHED.deck) < 0.01, `and stands on the deck (y ${pos.y.toFixed(2)})`);
  // The parapet is cover for a crouching player and can be shot over standing.
  const eye = V(3, SHED.deck + 1.68, 8.4);
  const crouch = V(3, SHED.deck + 1.05, 8.4);
  const target = level.objectives[0].pos.clone().setY(1.3);
  assert.equal(physics.lineOfSight(eye, target), true, 'standing: a clear shot down at reel 1');
  assert.equal(physics.lineOfSight(crouch, target), false, 'crouched: hidden behind the parapet');
});

test('the mezzanine: reached by its stair, glass that stops a player but not a bullet', () => {
  const M = SHOP.mezz;
  const pos = V(SHOP.stair.x1 + 0.7, 0, (SHOP.stair.z0 + SHOP.stair.z1) / 2);
  const vel = V(0, 0, 0);
  let grounded = true;
  for (let i = 0; i < 400 && pos.x > M.x1 - 1; i++) {
    vel.set(-3.2, grounded ? 0 : vel.y - 21 / 60, 0);
    grounded = physics.moveCapsule(pos, vel, 1 / 60, 0.32, 1.8, grounded).onGround;
  }
  assert.ok(Math.abs(pos.y - M.y) < 0.01, `the stair leads onto the deck (y ${pos.y.toFixed(2)}, x ${pos.x.toFixed(2)})`);
  // Steps of at most 0.25 m.
  const steps = physics.boxes.filter((b) => b.tag === 'shop-stair').map((b) => b.max.y).sort((a, b) => a - b);
  assert.equal(steps.length, SHOP.stair.risers);
  for (let i = 0; i < steps.length; i++) assert.ok(steps[i] - (i ? steps[i - 1] : 0) <= 0.25 + 1e-9, 'riser of 0.25 m or less');

  // From the catwalk toward the office glass: the capsule is stopped, the ray is not.
  const walker = V(-21, M.y, M.officeZ + 0.9);
  const push = V(0, 0, -3);
  for (let i = 0; i < 90; i++) {
    push.set(0, 0, -3);
    physics.moveCapsule(walker, push, 1 / 60, 0.32, 1.8, true);
  }
  assert.ok(walker.z > M.officeZ, `the glass front stops the player (z ${walker.z.toFixed(2)})`);
  const through = physics.raycast(V(-21, M.y + 1.6, M.officeZ + 0.9), V(0, 0, -1), 10);
  assert.ok(through && through.point.z < M.officeZ - 1, 'a round goes through the glass to the back wall');
  // …while the timber panel under it stops rounds: cover on the deck.
  const low = physics.raycast(V(-21, M.y + 0.5, M.officeZ + 0.9), V(0, 0, -1), 10);
  assert.ok(low && Math.abs(low.point.z - M.officeZ) < 0.1, 'the panel under the glass is solid');
  // The doorway at the east end of the front is open.
  const visitor = V(-18.2, M.y, M.officeZ + 0.9);
  for (let i = 0; i < 120; i++) {
    push.set(0, 0, -3);
    physics.moveCapsule(visitor, push, 1 / 60, 0.32, 1.8, true);
  }
  assert.ok(visitor.z < M.officeZ - 1, 'the office can be entered by its doorway');
});

test('the cage: mesh that stops walkers and lets rounds through, two gates', () => {
  const inside = V(35, 1.4, -22);
  const outside = V(35, 1.55, -9);
  assert.equal(physics.lineOfSight(outside, inside), true, 'you can see and shoot into the court from the sidewalk');
  const low = physics.raycast(V(27, 0.3, -9), V(0, 0, -1), 10);
  assert.ok(low && Math.abs(low.point.z - CAGE.maxZ) < 0.2, 'the knee wall under the mesh is solid');
  // A capsule cannot walk through the fence, only through a gate.
  const walk = (x, z, vx, vz, steps = 240) => {
    const pos = V(x, floorAt(x, z), z);
    const vel = V(0, 0, 0);
    for (let i = 0; i < steps; i++) {
      vel.set(vx, 0, vz);
      physics.moveCapsule(pos, vel, 1 / 60, 0.32, 1.8, true);
    }
    return pos;
  };
  assert.ok(walk(29, -9, 0, -3).z > CAGE.maxZ, 'fence: stopped');
  assert.ok(walk(34.5, -9, 0, -3).z < CAGE.maxZ - 2, 'south gate: through');
  assert.ok(walk(23.5, -27.9, 3, 0).x > CAGE.minX + 2, 'west gate: through');
});

test('the El: columns, a deck over the avenue, lamps underneath, a line for the train', () => {
  const { el } = level;
  assert.equal(el.y, 6.5);
  assert.equal(el.minX, BOUNDS.minX);
  assert.equal(el.maxX, BOUNDS.maxX);
  assert.ok(el.minZ < -5 && el.maxZ > 5);
  assert.ok(el.deckTop > el.y && el.deckTop < el.y + 0.6);
  assert.equal(el.tracks.length, 2);
  const columns = physics.boxes.filter((b) => b.tag === 'el-column');
  assert.ok(columns.length >= 20, `${columns.length} column colliders`);
  for (const c of columns) assert.ok(c.max.x - c.min.x < 0.8 && c.max.y > 5, 'a slim column the full height');
  // Underside clear for a jumping player everywhere on the roadway; the deck stops rounds from below.
  const up = physics.raycast(V(3, 1.7, 0.2), V(0, 1, 0), 20);
  assert.ok(up && up.point.y >= 5.2, `first steel overhead is at ${up && up.point.y.toFixed(2)} m`);
  const lamps = level.lamps.filter((l) => l.kind === 'el');
  assert.ok(lamps.length >= 9, `${lamps.length} El lamps`);
  for (const l of lamps.filter((lamp) => lamp.pos.y < el.y)) assert.ok(Math.abs(l.pos.z) < el.maxZ && l.pos.y > 5, 'hung under the deck');
});

test('lamps: every kind is listed, with usable numbers; the shop has four top-priority work lights', () => {
  const kinds = new Set(level.lamps.map((l) => l.kind));
  for (const kind of ['street', 'el', 'work', 'flood', 'neon', 'window']) assert.ok(kinds.has(kind), `a lamp of kind '${kind}'`);
  for (const l of level.lamps) {
    assert.ok(l.pos.isVector3 && Number.isFinite(l.pos.x + l.pos.y + l.pos.z));
    assert.ok(l.intensity > 0 && l.range > 1 && Number.isFinite(l.priority));
    assert.ok(l.color !== undefined && l.color !== null);
    if (l.dir) assert.ok(Math.abs(l.dir.length() - 1) < 1e-6, 'dir is a unit vector');
  }
  const top = Math.max(...level.lamps.map((l) => l.priority));
  const work = level.lamps.filter((l) => l.kind === 'work' && l.priority === top);
  assert.equal(work.length, 4, 'four work lights lead the list');
  for (const l of work) assert.equal(level.interiorAt(l.pos), 1, 'and hang inside the shop');
  assert.ok(level.lamps.filter((l) => l.kind === 'flood').length >= 2, 'two court floods');
  assert.ok(level.lamps.filter((l) => l.kind === 'street').length >= 8);
  assert.ok(level.lamps.filter((l) => l.kind === 'neon').length >= 10, 'lit signs');
  assert.ok(level.steam.length >= 4 && level.steam.every((p) => p.isVector3), 'steam points');
});

test('title fly-through: 10 to 14 held shots, start to truck, never inside anything', () => {
  const path = level.cinematicPath;
  assert.ok(path.length >= 10 && path.length <= 14, `${path.length} points`);
  const first = path[0].pos;
  const last = path[path.length - 1].pos;
  assert.equal(zoneAt(first.x, first.z), 'west', 'opens at the station end');
  assert.ok(flat(last, level.extraction.pos) < 6, 'ends at the truck');
  // The route passes each reel in order, then the truck.
  const closest = (target) => path.reduce((best, p, i) => (flat(p.pos, target) < flat(path[best].pos, target) ? i : best), 0);
  const order = [...level.objectives.map((o) => closest(o.pos)), closest(level.extraction.pos)];
  for (let i = 1; i < order.length; i++) assert.ok(order[i] > order[i - 1], `stop ${i + 1} comes after stop ${i}`);
  for (const o of level.objectives) assert.ok(flat(path[closest(o.pos)].pos, o.pos) < 14, `the camera comes near ${o.id}`);

  for (const [i, p] of path.entries()) {
    assert.ok(p.pos.isVector3 && p.look.isVector3);
    assert.ok(p.pos.y >= 1.2 && p.pos.y <= 6, `shot ${i} is at a human-ish height`);
    assert.ok(p.pos.distanceTo(p.look) > 3, 'looks at something, not at its own feet');
    assert.equal(physics.overlapsCylinder(p.pos.x, p.pos.z, 0.3, p.pos.y - 0.3, p.pos.y + 0.3), false, `shot ${i} is in free space`);
    if (i === 0) continue;
    // The straight leg from the previous shot clears every collider by a hand's width.
    const a = path[i - 1].pos;
    const steps = Math.ceil(a.distanceTo(p.pos) / 0.25);
    for (let k = 1; k < steps; k++) {
      const q = a.clone().lerp(p.pos, k / steps);
      assert.equal(physics.overlapsCylinder(q.x, q.z, 0.22, q.y - 0.2, q.y + 0.2), false, `leg ${i} hits something at (${q.x.toFixed(1)}, ${q.y.toFixed(1)}, ${q.z.toFixed(1)})`);
    }
  }
});

test('sightlines: no clear line along the avenue runs much past 45 m at eye height', () => {
  const origin = V(0, 0, 0);
  const dir = V(0, 0, 0);
  let longest = 0;
  let over46 = 0;
  let total = 0;
  for (let z = -10.75; z <= 10.75; z += 0.5) {
    for (let x = -45; x <= 45; x += 1) {
      const y = floorAt(x, z) + 1.68;
      if (physics.overlapsCylinder(x, z, 0.25, y - 1.5, y + 0.1)) continue; // nobody can stand here
      for (let a = -10; a <= 10; a += 2) {
        for (const s of [1, -1]) {
          dir.set(s * Math.cos((a * Math.PI) / 180), 0, Math.sin((a * Math.PI) / 180));
          const hit = physics.raycast(origin.set(x, y, z), dir, 200);
          const d = hit ? hit.dist : 200;
          total++;
          if (d > 46) over46++;
          if (d > longest) longest = d;
        }
      }
    }
  }
  assert.ok(total > 50000);
  assert.ok(longest < 58, `the longest clear line is ${longest.toFixed(1)} m`);
  // A handful of lines thread a few centimetres of daylight between a kiosk and a cage: no more.
  assert.ok(over46 / total < 0.0006, `${over46} of ${total} sampled lines run past 46 m`);
});

test('perimeter: sealed on every side by something solid plus a player-only wall', () => {
  // Rounds stop on something visible before they leave the block, in every direction, at chest height
  // (the two avenue closures and the alley gate included).
  const probes = [];
  for (let x = -44; x <= 44; x += 2) probes.push([x, -9.5, 0, -1], [x, 9.5, 0, 1]);
  for (let z = -9.5; z <= 9.5; z += 1) probes.push([-30, z, -1, 0], [30, z, 1, 0]);
  for (const [x, z, dx, dz] of [[8.5, -20, 0, -1], [23.5, -20, 0, -1], [35, -20, 0, -1], [35, -20, 1, 0], [35, 20, 1, 0], [35, 20, 0, 1], [0, 28.5, 0, 1], [-10, 20, -1, 0]]) probes.push([x, z, dx, dz]);
  for (const [x, z, dx, dz] of probes) {
    const hit = physics.raycast(V(x, floorAt(x, z) + 1.3, z), V(dx, 0, dz), 200);
    assert.ok(hit && hit.box, `a round from (${x}, ${z}) heading (${dx}, ${dz}) hits something solid`);
    const p = hit.point;
    assert.ok(p.x >= BOUNDS.minX - 3.01 && p.x <= BOUNDS.maxX + 3.01 && p.z >= BOUNDS.minZ - 3.01 && p.z <= BOUNDS.maxZ + 3.01, `it stops at the edge (${p.x.toFixed(1)}, ${p.z.toFixed(1)})`);
  }
  // Player-only walls: 0.6 m thick, 8 m high, all the way round.
  const seals = physics.boxes.filter((b) => b.tag === 'seal');
  for (const b of seals) {
    assert.equal(b.playerOnly, true);
    assert.ok(b.max.y >= 8, 'eight metres high');
  }
  const sealed = (x, z) => seals.some((b) => x >= b.min.x && x <= b.max.x && z >= b.min.z && z <= b.max.z);
  for (let x = BOUNDS.minX; x <= BOUNDS.maxX; x += 1) {
    assert.ok(sealed(x, BOUNDS.minZ - 0.3) && sealed(x, BOUNDS.maxZ + 0.3), `north and south edge at x ${x}`);
  }
  for (let z = BOUNDS.minZ; z <= BOUNDS.maxZ; z += 1) {
    assert.ok(sealed(BOUNDS.minX - 0.3, z) && sealed(BOUNDS.maxX + 0.3, z), `west and east edge at z ${z}`);
  }
  // A capsule thrown at each closure from a running jump stays inside.
  for (const [x, z, vx, vz] of [[-42, 0, -7, 0], [42, 6.3, 7, 0], [8.5, -29, 0, -7], [-42, 9.8, -7, 0], [43, -9.5, 7, 0]]) {
    const pos = V(x, floorAt(x, z) + 1.2, z);
    const vel = V(vx, 4, vz);
    for (let i = 0; i < 120; i++) {
      vel.x = vx;
      vel.z = vz;
      vel.y -= 21 / 60;
      physics.moveCapsule(pos, vel, 1 / 60, 0.32, 1.8, false);
    }
    assert.ok(pos.x > BOUNDS.minX && pos.x < BOUNDS.maxX && pos.z > BOUNDS.minZ + 2.5, `stopped at the closure (${pos.x.toFixed(1)}, ${pos.z.toFixed(1)})`);
  }
});

test('buildings are solid and only the shop can be entered', () => {
  for (const b of Object.values(BUILDINGS)) {
    const cx = (b.boxes[0][0] + b.boxes[0][1]) / 2;
    const cz = (b.boxes[0][2] + b.boxes[0][3]) / 2;
    assert.equal(physics.nav.isWalkable(cx, cz), false, `${b.name} is solid`);
    assert.ok(physics.groundHeight(cx, cz) > 4, `${b.name} has a roof`);
  }
  assert.ok(physics.nav.isWalkable(-4, -25), 'the shop floor is open');
  const roof = physics.raycast(V(-4, 1.7, -25), V(0, 1, 0), 30);
  assert.ok(roof && Math.abs(roof.point.y - SHOP.eave) < 0.6, 'under a roof');
});

test('no pockets: every place a player can stand at ground level connects to the start', () => {
  // Coarse flood fill of standable cells (capsule radius 0.32, 0.25 m grid). A cell joins its neighbour
  // when nothing taller than a jump (1.1 m above the floor) stands between them, so hopping a barrier
  // counts as connected; what is left over is sealed in by walls and must be out of reach on purpose.
  const cell = 0.25;
  const cols = Math.round((BOUNDS.maxX - BOUNDS.minX) / cell);
  const rows = Math.round((BOUNDS.maxZ - BOUNDS.minZ) / cell);
  const state = new Uint8Array(cols * rows); // 1 standable, 2 passable only (jumpable obstacle), 3 reached
  const solid = physics.boxes.filter((b) => !b.bulletOnly);
  for (let j = 0; j < rows; j++) {
    for (let i = 0; i < cols; i++) {
      const x = BOUNDS.minX + (i + 0.5) * cell;
      const z = BOUNDS.minZ + (j + 0.5) * cell;
      const f = floorAt(x, z);
      let stand = true;
      let pass = true;
      for (const b of solid) {
        if (b.max.y <= f + 0.42 || b.min.y >= f + 1.8) continue;
        const dx = x - Math.max(b.min.x, Math.min(x, b.max.x));
        const dz = z - Math.max(b.min.z, Math.min(z, b.max.z));
        if (dx * dx + dz * dz >= 0.32 * 0.32) continue;
        stand = false;
        if (b.max.y > f + 1.1) {
          pass = false;
          break;
        }
      }
      state[j * cols + i] = stand ? 1 : pass ? 2 : 0;
    }
  }
  const index = (x, z) => Math.floor((z - BOUNDS.minZ) / cell) * cols + Math.floor((x - BOUNDS.minX) / cell);
  const stack = [index(level.playerStart.pos.x, level.playerStart.pos.z)];
  assert.ok(state[stack[0]] === 1, 'the start is standable');
  const reached = new Uint8Array(cols * rows);
  reached[stack[0]] = 1;
  while (stack.length) {
    const c = stack.pop();
    const i = c % cols;
    const j = (c / cols) | 0;
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const ni = i + di;
      const nj = j + dj;
      if (ni < 0 || nj < 0 || ni >= cols || nj >= rows) continue;
      const n = nj * cols + ni;
      if (reached[n] || state[n] === 0) continue;
      reached[n] = 1;
      stack.push(n);
    }
  }
  // Places sealed off on purpose: behind the alley gate, between the cage and the walls behind it.
  const allowed = (x, z) => (x > 6 && x < 11 && z < -31.3) || z < CAGE.minZ + 0.2 || (x > CAGE.maxX - 0.2 && z < CAGE.maxZ);
  const pockets = [];
  for (let c = 0; c < state.length; c++) {
    if (state[c] !== 1 || reached[c]) continue;
    const x = BOUNDS.minX + ((c % cols) + 0.5) * cell;
    const z = BOUNDS.minZ + (((c / cols) | 0) + 0.5) * cell;
    if (!allowed(x, z)) pockets.push(`(${x.toFixed(1)}, ${z.toFixed(1)})`);
  }
  // A few cells always remain in slots only just wide enough for a body (between two bumpers, behind
  // a column): under a square metre in all. A sealed yard would be hundreds.
  assert.ok(pockets.length <= 14, `${pockets.length} sealed-in standable cells, e.g. ${pockets.slice(0, 12).join(' ')}`);
});

test('the same seed builds the same block', () => {
  const again = buildLevel();
  assert.equal(again.physics.boxes.length, worldBoxes.length);
  assert.deepEqual(again.level.stats, level.stats);
  for (let i = 0; i < worldBoxes.length; i += 37) {
    assert.deepEqual(again.physics.boxes[i].min.toArray(), worldBoxes[i].min.toArray());
  }
  assert.deepEqual(again.level.coverPoints.map((c) => c.pos.toArray()), level.coverPoints.map((c) => c.pos.toArray()));
});
