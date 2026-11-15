// G.level (CONTRACT 6.10): the block. One avenue under the El between two rows of brick, the chop
// shop, the alley, the cage, the vacant lot, the rear lane and the parking lot (docs/DESIGN.md 4).
//
//   src/level/layout.js     every footprint and height as data, plus zoneAt / floorAt / groundSurfaceAt
//   src/level/kit.js        the building kit: boxes, colliders, props, lamps
//   src/level/ground.js     roadway, sidewalks, kerbs, paint, repairs, puddles
//   src/level/el.js         the elevated line and its sealed station
//   src/level/buildings.js  the solid buildings and the backs that close the block
//   src/level/shop.js       V&R AUTO BODY, the only interior
//   src/level/yards.js      alley, cut, cage, vacant lot, rear lane, parking lot
//   src/level/street.js     closures, vehicles and cover on the avenue, street furniture, the shed
//   src/level/data.js       reels, spawns, cover points, explosives, the title fly-through
//
// Everything static is merged per material at the end; stateful props (reel cases, the truck, the
// hydrant, the fan) stay under `dynamic`.

import * as THREE from 'three';
import { mergeStatic } from './core/geo.js';
import { clamp01 } from './core/util.js';
import { buildBuildings } from './level/buildings.js';
import { AIR_SPAWNS, CINEMATIC, COVER_POINTS, EXPLOSIVES, EXTRACTION, GROUND_SPAWNS, REELS, START, TRUCK } from './level/data.js';
import { buildEl } from './level/el.js';
import { buildGround } from './level/ground.js';
import { createKit } from './level/kit.js';
import { BOUNDS, CAGE_NAME, ROAD_Z, ZONES, floorAt, groundSurfaceAt, zoneAt } from './level/layout.js';
import { buildShop } from './level/shop.js';
import { buildStreet } from './level/street.js';
import { buildYards } from './level/yards.js';

const INTERIOR_FADE = 1.5; // metres over which interiorAt() falls from 1 to 0 outside the box
const SEAL = 0.6; // thickness of the player-only walls around the block
const SEAL_HEIGHT = 8;
const NUDGE = 2.5; // how far an AI point may be moved to reach a walkable cell

const v = (x, y, z) => new THREE.Vector3(x, y, z);

// The boot bar's span while the level builds (src/modules.js: level 0.36, atmos 0.52).
const BOOT_FROM = 0.36;
const BOOT_TO = 0.52;

/**
 * Lets the browser paint between build phases (or moves on after 60 ms when the tab is hidden, like
 * main.js paint()), nudging the boot bar along `share` of the level's span. Outside a page (node tests)
 * it only yields to the microtask queue.
 */
function breathe(share) {
  if (typeof document === 'undefined' || typeof requestAnimationFrame !== 'function') return Promise.resolve();
  const fill = document.getElementById('boot-fill');
  if (fill) fill.style.transform = `scaleX(${BOOT_FROM + (BOOT_TO - BOOT_FROM) * share})`;
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, 60);
    requestAnimationFrame(() => {
      clearTimeout(timer);
      resolve();
    });
  });
}

export async function createLevel(G) {
  const { physics } = G;
  const text = G.config.text;
  const kit = createKit(G);

  // ---------------------------------------------------------------------------------------------
  // Build, one phase at a time: each one paints its materials, so the boot screen gets a frame between
  // them instead of freezing for the whole block.
  // ---------------------------------------------------------------------------------------------

  const ground = buildGround(kit);
  await breathe(0.1);
  const el = buildEl(kit);
  await breathe(0.2);
  buildBuildings(kit);
  await breathe(0.4);
  const shop = buildShop(kit);
  await breathe(0.55);
  const yards = buildYards(kit);
  await breathe(0.7);
  const street = buildStreet(kit);
  await breathe(0.85);
  const animated = [...kit.animated, ...shop.animated];

  // Player-only walls right behind the block's edges: nothing that can be climbed leads out.
  const { minX, maxX, minZ, maxZ } = BOUNDS;
  for (const [x0, x1, z0, z1] of [
    [minX - SEAL, minX, minZ - SEAL, maxZ + SEAL],
    [maxX, maxX + SEAL, minZ - SEAL, maxZ + SEAL],
    [minX, maxX, minZ - SEAL, minZ],
    [minX, maxX, maxZ, maxZ + SEAL],
  ]) {
    kit.solid(x0, x1, 0, SEAL_HEIGHT, z0, z1, { tag: 'seal', playerOnly: true });
  }

  // ---------------------------------------------------------------------------------------------
  // Objectives and extraction
  // ---------------------------------------------------------------------------------------------

  const objectives = REELS.map((reel, i) => {
    const info = text.reels.list[i];
    const prop = kit.place('master_case', reel.x, reel.z, reel.yaw);
    return { id: info.id, code: info.code, label: info.label, zone: reel.zone, pos: v(reel.x, floorAt(reel.x, reel.z), reel.z), prop };
  });

  const extraction = {
    pos: v(EXTRACTION.x, floorAt(EXTRACTION.x, EXTRACTION.z), EXTRACTION.z),
    radius: G.config.flow.extraction.radius,
    label: text.extraction.label,
    code: text.extraction.code,
    prop: yards.truck,
  };

  // ---------------------------------------------------------------------------------------------
  // Data for AI, flow and atmosphere
  // ---------------------------------------------------------------------------------------------

  // Display names for the minimap band come from the copy deck when it has them (config/text.js zones).
  const names = text.zones || {};
  const zones = ZONES.map((zone) => ({ ...zone, name: names[zone.id] || zone.name }));
  const zoneNames = Object.fromEntries(zones.map((zone) => [zone.id, zone.name]));
  const cageName = names.cage || CAGE_NAME;
  const avenueName = zoneNames.avenue;

  /**
   * Display name of the place at (x, z). The east zone is two places split by the avenue: the cage north
   * of it, the parking lot south of it; the roadway between them reads as the avenue.
   */
  function zoneName(x, z) {
    const id = zoneAt(x, z);
    if (id !== 'lot') return zoneNames[id] || avenueName;
    if (z < -ROAD_Z) return cageName;
    return z > ROAD_Z ? zoneNames.lot : avenueName;
  }

  const enemySpawns = [
    ...GROUND_SPAWNS.map(([x, z]) => ({ pos: v(x, floorAt(x, z), z), zone: zoneAt(x, z), type: 'ground' })),
    ...AIR_SPAWNS.map(([x, y, z]) => ({ pos: v(x, y, z), zone: zoneAt(x, z), type: 'air' })),
  ];

  const coverPoints = COVER_POINTS.map(([x, z, y]) => ({ pos: v(x, y ?? floorAt(x, z), z), zone: zoneAt(x, z) }));

  const cinematicPath = CINEMATIC.map(([x, y, z, lx, ly, lz]) => ({ pos: v(x, y, z), look: v(lx, ly, lz) }));

  const explosives = EXPLOSIVES.map(([type, x, z, yaw, y]) => ({ type, pos: v(x, y ?? floorAt(x, z), z), yaw }));

  const interiorBoxes = [shop.interior];

  /** 1 inside the shop, falling to 0 over a metre and a half outside its walls. */
  function interiorAt(pos) {
    let best = 0;
    for (let i = 0; i < interiorBoxes.length; i++) {
      const box = interiorBoxes[i];
      const dx = Math.max(box.min.x - pos.x, 0, pos.x - box.max.x);
      const dy = Math.max(box.min.y - pos.y, 0, pos.y - box.max.y);
      const dz = Math.max(box.min.z - pos.z, 0, pos.z - box.max.z);
      const amount = clamp01(1 - Math.hypot(dx, dy, dz) / INTERIOR_FADE);
      if (amount > best) best = amount;
    }
    return best;
  }

  // ---------------------------------------------------------------------------------------------
  // Finish: merge, publish the bounds, move AI points onto walkable ground
  // ---------------------------------------------------------------------------------------------

  const root = new THREE.Group();
  root.name = 'level';
  const sunless = stopHiddenCasters(G, kit.placed);
  const merged = mergeStatic(kit.staticRoot);
  root.add(merged, kit.dynamicRoot);
  const retint = groundRetint(G, merged);
  if (G.scene) G.scene.add(root);
  physics.setBounds(BOUNDS);

  // Ground-level cover points and spawns that ended up inside an obstacle's margin go to the nearest
  // walkable cell (the explosives are not standing yet: their module adds them, and they are small).
  for (const point of [...coverPoints, ...enemySpawns]) {
    const p = point.pos;
    if (point.type === 'air' || p.y > 0.5 || physics.nav.isWalkable(p.x, p.z)) continue;
    const near = physics.nav.nearestWalkable(p.x, p.z, NUDGE);
    if (near) p.set(near.x, floorAt(near.x, near.z), near.z);
  }

  return {
    root,
    bounds: { ...BOUNDS },
    playerStart: { pos: v(START.x, floorAt(START.x, START.z), START.z), yaw: START.yaw },
    objectives,
    extraction,
    enemySpawns,
    zones,
    zoneAt,
    zoneName,
    interiorBoxes,
    interiorAt,
    coverPoints,
    cinematicPath,
    explosives,
    lamps: kit.lamps,
    steam: [...ground.steam, ...yards.steam, ...street.steam],
    el,
    vantage: street.vantage,
    groundSurfaceAt,
    /** Height of the level's own walking surface at (x, z): 0 on the road, 0.15 on a sidewalk. */
    floorAt,
    /** Where water stands on the street: [{x, z, r}] (splash and reflection cues). */
    puddles: ground.puddles,
    /** What was built: counts for the boot log, tests and the perf scenario. */
    stats: { ...merged.userData.mergeStats, props: kit.placed.length, colliders: physics.boxes.length, lamps: kit.lamps.length, sunless },
    update(dt) {
      for (let i = 0; i < animated.length; i++) animated[i].update(dt);
      retint();
    },
  };
}

/**
 * Colliders of things that stop the sun: the buildings, the shop's shell, the station, the El's steel
 * (not its deck, whose ties let the light through in stripes) and the solid hoardings. Props, fences,
 * the scaffold and the cage never count: light gets through or around them.
 */
export const SUN_BLOCKERS = new Set([
  'tenement', 'deli', 'station house', 'pawn', 'S3', 'garages', 'backs', 'lot-wall',
  'shop-wall', 'shop-roof', 'mezzanine', 'office', 'bulkhead', 'dock',
  'station', 'el-girder', 'el-column', 'hoarding', 'kiosk', 'shed-deck',
]);

const SUN_INSET = 0.03; // sample points sit this far inside a prop's bounds
const SUN_REACH = 150; // metres: past this a ray is in the open sky

/** Every direction the key light travels in, one per time of day (config/look.js `times`). */
export function sunDirections(look) {
  const times = look && look.times ? Object.values(look.times) : [];
  const dirs = times.filter((t) => t && t.sun && t.sun.direction).map((t) => new THREE.Vector3().fromArray(t.sun.direction).normalize());
  if (!dirs.length && look && look.sun) dirs.push(new THREE.Vector3().fromArray(look.sun.direction).normalize());
  return dirs;
}

/**
 * Does the sunlight travelling along `dir` reach `point`? Walks the ray back toward the sun through
 * props and see-through things until it meets a SUN_BLOCKERS collider (no) or open sky (yes).
 */
export function sunReaches(physics, point, dir, hit = { dist: 0, point: new THREE.Vector3(), normal: new THREE.Vector3(), surface: null, box: null }) {
  const toSun = new THREE.Vector3().copy(dir).negate();
  const o = point.clone();
  for (let i = 0; i < 16; i++) {
    const h = physics.raycast(o, toSun, SUN_REACH, hit);
    if (!h) return true;
    if (h.box && SUN_BLOCKERS.has(h.box.tag)) return false;
    o.copy(h.point).addScaledVector(toSun, 0.02);
  }
  return true;
}

/**
 * A static prop that no sunlight reaches (inside the shop, deep under the shed, in a building's own
 * shadow) at any time of day only darkens ground that is already dark: it stops casting. Its corners
 * and top centre are all checked; if any of them sees the sun, it keeps its shadow. Returns how many
 * props stopped.
 */
function stopHiddenCasters(G, placed) {
  const dirs = sunDirections(G.config.look);
  if (!dirs.length) return 0;
  const box = new THREE.Box3();
  const p = new THREE.Vector3();
  let count = 0;
  for (const { prop } of placed) {
    if (prop.dynamic || !prop.object) continue;
    prop.object.updateMatrixWorld(true);
    box.setFromObject(prop.object);
    if (box.isEmpty()) continue;
    const { min, max } = box;
    for (const axis of ['x', 'y', 'z']) {
      const inset = Math.min(SUN_INSET, (max[axis] - min[axis]) / 4);
      min[axis] += inset;
      max[axis] -= inset;
    }
    const samples = [[(min.x + max.x) / 2, max.y, (min.z + max.z) / 2]];
    for (const x of [min.x, max.x]) for (const y of [min.y, max.y]) for (const z of [min.z, max.z]) samples.push([x, y, z]);
    const lit = dirs.some((d) => samples.some(([x, y, z]) => sunReaches(G.physics, p.set(x, y, z), d)));
    if (lit) continue;
    prop.object.traverse((o) => {
      if (o.isMesh) o.castShadow = false;
    });
    count++;
  }
  return count;
}

/**
 * The library lightens ground materials by day (a dry street), but only untinted ones. The level's
 * tinted repairs (asphalt patches, authored against the catalogue's night colour) follow along: their
 * vertex colours are scaled by how far the plain material has moved from that colour. Returns a cheap
 * per-frame check that rewrites the colours only when the plain material changes.
 */
function groundRetint(G, merged) {
  const entries = [];
  for (const name of ['asphalt']) {
    const tinted = G.mats.get(name, { tint: 'vertex' });
    const def = G.config.catalog.MATERIALS[name];
    if (!tinted.vertexColors || !def) continue;
    const plain = G.mats.get(name);
    const night = new THREE.Color(def.color);
    merged.traverse((mesh) => {
      const color = mesh.isMesh && mesh.material === tinted && mesh.geometry.getAttribute('color');
      if (color) entries.push({ color, base: color.array.slice(), plain, tinted, night, last: -1 });
    });
  }
  return () => {
    for (let i = 0; i < entries.length; i++) {
      const e = entries[i];
      const r = e.plain.color.r / Math.max(e.tinted.color.r, 1e-4) / Math.max(e.night.r, 1e-4);
      const g = e.plain.color.g / Math.max(e.tinted.color.g, 1e-4) / Math.max(e.night.g, 1e-4);
      const b = e.plain.color.b / Math.max(e.tinted.color.b, 1e-4) / Math.max(e.night.b, 1e-4);
      const k = r + g * 7 + b * 49;
      if (Math.abs(k - e.last) < 1e-4) continue;
      e.last = k;
      const out = e.color.array;
      for (let j = 0; j < out.length; j += 3) {
        out[j] = e.base[j] * r;
        out[j + 1] = e.base[j + 1] * g;
        out[j + 2] = e.base[j + 2] * b;
      }
      e.color.needsUpdate = true;
    }
  };
}

