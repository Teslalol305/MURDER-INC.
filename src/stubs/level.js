// Stub level (CONTRACT 6.10): the TESTBED. A 92 × 68 m block of boxes that satisfies the whole level
// schema, laid out like the real blueprint (docs/DESIGN.md section 4) so that everything built against
// it meets the same situations: an avenue under the El with cars as cover, one hollow building with a
// door (the only interior), a stair up to a 2.8 m deck, a fenced court, a lot with the truck, a flanking
// loop behind the south buildings, sealed bounds.
//
//  z -34 ┌──────────────┬──────────────────┬───────┬─────────┬──────────────┐
//        │  tenement    │  SHOP (hollow)   │ alley │  deli   │  THE CAGE    │
//        │              │  reel 2          │       │         │  reel 3      │
//    -12 ├──────────────┴─────[door]───────┴───────┴─────────┴──[gate]──────┤
//     -7 │ ═══════ avenue under the El: cars, barriers, reel 1 ═════════════ │ roadblock
//      7 │ start →                      [stair + deck]                       │
//     12 ├──────────┬──────────┬────────┬──────────────────┬────────────────┤
//        │ station  │  pawn    │ vacant │  S3              │  LOT           │
//        │          │          │  lot   ├──────────────────┘   IPX truck    │
//     34 └──────────┴──────────┴────────┴── rear lane ──────────────────────┘
//      x -46      -30        -16       -4                 22               46

import * as THREE from 'three';
import { boxGeo, mergeStatic, planeGeo } from '../core/geo.js';
import { clamp01 } from '../core/util.js';

const BOUNDS = { minX: -46, maxX: 46, minZ: -34, maxZ: 34 };
const EL_Y = 6.5; // underside of the track deck
const EL_ROW = 4.6; // |z| of the two column rows: between the travel lanes and the parked cars
const EL_HALF = 5.2; // half width of the track deck
const DECK_Y = 2.8; // the vantage
const STEPS = 11; // stair risers of about 0.25 m
const SHOP = { minX: -20, maxX: -2, minZ: -30, maxZ: -12, eave: 6, wall: 0.4, door: [-13, -7], doorH: 4 };
const COURT = { minX: 24, maxX: 44, minZ: -32, maxZ: -12 };
const INTERIOR_FADE = 1.5; // metres over which interiorAt() falls from 1 to 0 outside the box

// Impact / footstep surface for the catalogue materials the testbed is built from.
const SURFACE = {
  brick_red: 'brick',
  brick_brown: 'brick',
  brick_tan: 'brick',
  cinder: 'concrete',
  concrete: 'concrete',
  concrete_dark: 'concrete',
  steel_el: 'metal',
  metal_dark: 'metal',
  plywood: 'wood',
  chainlink: 'metal',
};

const v = (x, y, z) => new THREE.Vector3(x, y, z);

export function createLevel(G) {
  const { mats, props, physics } = G;
  const text = G.config.text;

  const root = new THREE.Group();
  root.name = 'level';
  const staticRoot = new THREE.Group(); // merged per material at the end
  const dynamicRoot = new THREE.Group(); // stateful props, kept as they are
  dynamicRoot.name = 'dynamic';
  const animated = []; // props with update(dt)
  const lamps = [];

  // ---------------------------------------------------------------------------------------------
  // Builders
  // ---------------------------------------------------------------------------------------------

  /** A visible axis-aligned block from (x0, y0, z0) to (x1, y1, z1) with a matching collider. */
  function block(material, x0, x1, y0, y1, z0, z1, opts = {}) {
    const mesh = new THREE.Mesh(boxGeo(x1 - x0, y1 - y0, z1 - z0), opts.mat || mats.get(material));
    mesh.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
    mesh.castShadow = opts.shadow !== false;
    mesh.receiveShadow = true;
    staticRoot.add(mesh);
    if (opts.collide !== false) {
      physics.addBox({
        min: [x0, y0, z0],
        max: [x1, y1, z1],
        surface: opts.surface || SURFACE[material] || 'concrete',
        tag: opts.tag,
        noNav: opts.noNav,
      });
    }
    return mesh;
  }

  /** A flat coloured patch just above the ground plane (no collision: the ground is y = 0). */
  function patch(material, x0, x1, z0, z1, lift = 0.02) {
    const mesh = new THREE.Mesh(planeGeo(x1 - x0, z1 - z0), mats.get(material));
    mesh.position.set((x0 + x1) / 2, lift, (z0 + z1) / 2);
    mesh.receiveShadow = true;
    staticRoot.add(mesh);
  }

  /** Builds a catalogue prop at (x, z), yawed about +Y, and registers its colliders. */
  function place(name, x, z, yaw = 0, opts = {}) {
    const y = opts.y || 0;
    const prop = props.build(name, opts);
    prop.object.position.set(x, y, z);
    prop.object.rotation.y = yaw;
    (prop.dynamic ? dynamicRoot : staticRoot).add(prop.object);

    const sin = Math.sin(yaw);
    const cos = Math.cos(yaw);
    prop.boxes = [];
    for (const c of prop.colliders) {
      const sy = c.max[1] - c.min[1];
      if (sy < 0.2 && c.max[1] < 0.3) continue; // flat things are walked over
      const lx = (c.min[0] + c.max[0]) / 2;
      const lz = (c.min[2] + c.max[2]) / 2;
      // rotation.y maps local +X to (cos, −sin) and local +Z to (sin, cos) in world XZ
      const centre = [x + lx * cos + lz * sin, y + (c.min[1] + c.max[1]) / 2, z - lx * sin + lz * cos];
      const size = [c.max[0] - c.min[0], sy, c.max[2] - c.min[2]];
      prop.boxes.push(
        ...physics.addOriented(centre, size, yaw, {
          surface: c.surface || prop.surface,
          bulletOnly: c.bulletOnly,
          playerOnly: c.playerOnly,
          noNav: c.noNav,
          owner: prop,
        }),
      );
    }

    for (const hint of prop.lights || []) {
      const [hx, hy, hz] = hint.pos;
      lamps.push({
        pos: v(x + hx * cos + hz * sin, y + hy, z - hx * sin + hz * cos),
        color: hint.color,
        intensity: hint.intensity,
        range: hint.range,
        kind: hint.kind,
        priority: hint.kind === 'flood' ? 8 : 5,
      });
    }
    if (prop.update) animated.push(prop);
    return prop;
  }

  /** A sign quad on a wall that faces +Z (south) or −Z. */
  function wallSign(spec, x, y, z, facing = '+z') {
    const sign = mats.sign(spec);
    // A sign's texture spans its quad once: UVs 0 … 1, not metres.
    const mesh = new THREE.Mesh(planeGeo(sign.w, sign.h, { facing, uvScale: [1 / sign.w, 1 / sign.h] }), sign.material);
    mesh.position.set(x, y, z);
    staticRoot.add(mesh);
  }

  // ---------------------------------------------------------------------------------------------
  // Ground and perimeter
  // ---------------------------------------------------------------------------------------------

  const ground = new THREE.Mesh(planeGeo(260, 240), mats.get('asphalt'));
  ground.name = 'ground';
  ground.receiveShadow = true;
  staticRoot.add(ground);
  patch('sidewalk', BOUNDS.minX, BOUNDS.maxX, -11, -7);
  patch('sidewalk', BOUNDS.minX, BOUNDS.maxX, 7, 11);
  patch('court', COURT.minX, COURT.maxX, COURT.minZ, COURT.maxZ);
  patch('concrete_dark', SHOP.minX, SHOP.maxX, SHOP.minZ, SHOP.maxZ);
  patch('dirt', -16, -4, 12, 25);

  // Lane dashes down the middle of the avenue.
  const dash = mats.decal('lane');
  for (let x = -42; x <= 42; x += 6) {
    const mesh = new THREE.Mesh(planeGeo(dash.h, dash.w), dash.material);
    mesh.position.set(x, 0.03, 0);
    staticRoot.add(mesh);
  }

  // Walls just outside the bounds, each doubled by a tall player-only wall so nothing can be hopped.
  const { minX, maxX, minZ, maxZ } = BOUNDS;
  const edges = [
    [minX - 1, maxX + 1, minZ - 1, minZ],
    [minX - 1, maxX + 1, maxZ, maxZ + 1],
    [minX - 1, minX, minZ, maxZ],
    [maxX, maxX + 1, minZ, maxZ],
  ];
  for (const [x0, x1, z0, z1] of edges) {
    block('concrete_dark', x0, x1, 0, 5, z0, z1, { tag: 'perimeter' });
    physics.addBox({ min: [x0, 0, z0], max: [x1, 24, z1], playerOnly: true, tag: 'seal' });
  }

  // ---------------------------------------------------------------------------------------------
  // Buildings: solid blocks, except the shop
  // ---------------------------------------------------------------------------------------------

  block('brick_red', -46, -20, 0, 12, -34, -12, { tag: 'tenement' });
  block('brick_tan', 10, 22, 0, 8, -34, -12, { tag: 'deli' });
  block('brick_brown', -46, -30, 0, 10, 12, 34, { tag: 'station' });
  block('brick_red', -30, -16, 0, 8, 12, 34, { tag: 'pawn' });
  block('brick_tan', -4, 22, 0, 7, 12, 25, { tag: 's3' });

  // The shop: four walls, a roof, a 6 m door in the south wall. The only interior.
  {
    const s = SHOP;
    const t = s.wall;
    block('cinder', s.minX, s.maxX, 0, s.eave, minZ, s.minZ + t); // north wall, thick: fills the strip behind
    block('cinder', s.minX, s.minX + t, 0, s.eave, s.minZ + t, s.maxZ); // west
    block('cinder', s.maxX - t, s.maxX, 0, s.eave, s.minZ + t, s.maxZ); // east
    block('cinder', s.minX + t, s.door[0], 0, s.eave, s.maxZ - t, s.maxZ); // south, left of the door
    block('cinder', s.door[1], s.maxX - t, 0, s.eave, s.maxZ - t, s.maxZ); // south, right of the door
    block('cinder', s.door[0], s.door[1], s.doorH, s.eave, s.maxZ - t, s.maxZ); // lintel
    block('concrete_dark', s.minX, s.maxX, s.eave, s.eave + 0.3, s.minZ, s.maxZ, { tag: 'roof' });
    wallSign({ text: text.world.shop, w: 8, h: 1.1, style: 'box', bg: 0x101113, fg: 0xf6c21a }, -10, 5, s.maxZ + 0.02);

    place('car_lift', -15, -24.5, Math.PI / 2);
    place('tool_chest', -19, -17, Math.PI / 2);
    place('workbench', -11, -28.9);
    place('shelf_rack', -3, -22, Math.PI / 2);
    place('tire_stack', -6, -27.5);
    place('oil_drum', -12.5, -19.5);
    place('crate_wood', -6.2, -19.2);
    for (const [x, z] of [[-15.5, -25], [-6.5, -25], [-15.5, -17], [-6.5, -17]]) {
      lamps.push({ pos: v(x, 5.2, z), color: 0xffc48a, intensity: 34, range: 13, kind: 'work', priority: 10 });
    }
  }
  wallSign({ text: text.world.storefronts[0], w: 9, h: 0.9, style: 'neon', fg: 0x35e0ff }, 16, 4.2, -11.98);
  lamps.push({ pos: v(16, 4.2, -11.5), color: 0x35e0ff, intensity: 14, range: 9, kind: 'neon', priority: 4 });
  lamps.push({ pos: v(-10, 5, -11.5), color: 0xf6c21a, intensity: 14, range: 9, kind: 'neon', priority: 4 });

  // ---------------------------------------------------------------------------------------------
  // The El: two rows of columns, girders, ties. One collider stands in for the deck.
  // ---------------------------------------------------------------------------------------------

  for (let x = -40; x <= 40; x += 10) {
    for (const z of [-EL_ROW, EL_ROW]) block('steel_el', x - 0.3, x + 0.3, 0, EL_Y, z - 0.3, z + 0.3, { tag: 'el-column' });
    lamps.push({ pos: v(x + 5, EL_Y - 0.4, 0), color: 0xffb45e, intensity: 30, range: 12, kind: 'el', priority: 3 });
  }
  for (const z of [-EL_ROW, EL_ROW]) block('steel_el', minX, maxX, EL_Y - 0.6, EL_Y, z - 0.25, z + 0.25, { collide: false });
  for (let x = minX + 1; x < maxX; x += 2.3) block('steel_el', x - 0.14, x + 0.14, EL_Y, EL_Y + 0.2, -EL_HALF, EL_HALF, { collide: false });
  physics.addBox({ min: [minX, EL_Y - 0.1, -EL_HALF], max: [maxX, EL_Y + 0.5, EL_HALF], surface: 'metal', tag: 'el-deck', noNav: true });

  // ---------------------------------------------------------------------------------------------
  // The avenue: cover in lanes, the start, the roadblock
  // ---------------------------------------------------------------------------------------------

  // Parked cars sit at |z| ≈ 6.05, between the column rows and the kerbs.
  place('suv', -38, 6.05, 0, { color: 0x1c2029 }); // Rule's ride at the kerb
  place('sedan', -24, -6.05, 0, { seed: 0 });
  place('taxi', -17, 6.05, Math.PI);
  place('suv', -10.5, -6.05, 0, { seed: 3 });
  place('van', -7.2, -1.4, 0.32, { color: 0x23262a }); // the Vultures' van, left open beside reel 1
  place('taxi', 4, -6.05, Math.PI);
  place('box_truck', 9, 6.3, 0, { color: 0xb9b4a6 });
  place('sedan', 16, -6.05, 0, { seed: 1 });
  place('sedan', 18.5, 2.2, -0.5, { seed: 4 }); // double-parked, off-axis
  place('jersey_barrier', -1.2, 3.4);
  place('jersey_barrier', -1.6, -1.2, Math.PI / 2);
  place('trash_bags', -5.6, 3.3);
  place('milk_crates', -2.6, -2.9);
  place('traffic_barrel', 11.2, 0.6);
  place('traffic_barrel', 12.3, -0.7);
  place('sandbags', 24, 1.4, Math.PI / 2);
  place('dumpster', -28, 9.2);
  place('mailbox', -12, 8.4);
  place('newspaper_box', -11, 8.4);
  place('food_cart', -17.5, -8.8);
  place('bus_shelter', 19, 9.4);
  place('hydrant', -31, 7.6);
  for (const x of [-35, -12, 14.5, 32]) place('street_lamp', x, 7.5);
  for (const x of [-24, 0, 24]) place('street_lamp', x, -7.5);
  // East end: sealed by a roadblock under the El.
  place('box_truck', 41.5, 0.3, 1.05, { color: 0x5a5d62 });
  for (const z of [-5.8, 5.9]) place('jersey_barrier', 43.6, z, Math.PI / 2);
  for (const [x, z] of [[-15, 0.6], [9, -3], [27, 3]]) place('manhole', x, z);

  // The vantage: a plywood deck on posts in front of S3, reached by a stair at its west end.
  {
    const x0 = 2;
    const x1 = 14;
    const z0 = 8.2;
    const z1 = 11.4;
    block('plywood', x0, x1, DECK_Y - 0.2, DECK_Y, z0, z1, { tag: 'deck' });
    for (const x of [x0 + 0.1, (x0 + x1) / 2, x1 - 0.1]) {
      for (const z of [z0 + 0.1, z1 - 0.1]) block('metal_dark', x - 0.08, x + 0.08, 0, DECK_Y - 0.2, z - 0.08, z + 0.08);
    }
    block('plywood', x0, x1, DECK_Y, DECK_Y + 0.9, z0, z0 + 0.12, { tag: 'parapet' }); // faces the avenue
    block('plywood', x1 - 0.12, x1, DECK_Y, DECK_Y + 0.9, z0, z1);
    const run = 0.3;
    const rise = DECK_Y / STEPS;
    for (let i = 1; i <= STEPS; i++) {
      const sx = x0 - (STEPS - i + 1) * run;
      block('plywood', sx, sx + run, 0, i * rise, z1 - 1.4, z1, { tag: 'stair' });
    }
    place('sandbags', 8, 9, 0, { y: DECK_Y });
  }

  // ---------------------------------------------------------------------------------------------
  // The cage (reel 3) and the lot (extraction)
  // ---------------------------------------------------------------------------------------------

  {
    const c = COURT;
    const fence = mats.get('chainlink', { transparent: true, opacity: 0.4, doubleSide: true });
    const run = (x0, x1, z0, z1) => block('chainlink', x0, x1, 0, 4, z0, z1, { mat: fence, shadow: false, tag: 'fence' });
    run(c.minX, c.maxX, c.minZ, c.minZ + 0.08);
    run(c.maxX - 0.08, c.maxX, c.minZ, c.maxZ);
    run(c.minX, 31.5, c.maxZ - 0.08, c.maxZ); // south side, with a gate gap at x 31.5 … 34.5
    run(34.5, c.maxX, c.maxZ - 0.08, c.maxZ);
    run(c.minX, c.minX + 0.08, c.minZ, -25); // west side, gate gap at z −25 … −22
    run(c.minX, c.minX + 0.08, -22, c.maxZ);
    place('hoop', 25.4, -22, 0);
    place('hoop', 42.6, -22, Math.PI);
    place('bleachers', 34, -30.6);
    place('court_light', 25, -13);
    place('court_light', 43, -31);
    place('crate_wood', 30.5, -19.5);
    place('tire_stack', 35.6, -24.4);
    place('milk_crates', 31.2, -24.8);
  }

  place('sedan', 28, 16, Math.PI / 2, { seed: 2 });
  place('sedan', 33, 16.4, Math.PI / 2, { seed: 5 });
  place('pickup', 28.5, 24.5, Math.PI / 2, { seed: 6 });
  place('lot_booth', 24.5, 12.6);
  place('billboard', 40, 13.2, 0);
  place('pallet_stack', 34.5, 24);
  place('oil_drum', 36.2, 21.4);
  place('street_lamp', 30, 32.6);
  // Rear lane behind S3.
  place('dumpster', 4, 26.2);
  place('dumpster', 14, 33);
  place('trash_bags', -10, 27.5);
  place('burned_car', -10, 17, 1.2);

  const truck = place('ipx_truck', 40.5, 28.5, 0);

  // ---------------------------------------------------------------------------------------------
  // Objectives
  // ---------------------------------------------------------------------------------------------

  const REELS = [
    { zone: 'avenue', pos: v(-4, 0, 1) },
    { zone: 'shop', pos: v(-9, 0, -21) },
    { zone: 'lot', pos: v(33, 0, -22) },
  ];
  const objectives = REELS.map((reel, i) => {
    const info = text.reels.list[i];
    const prop = place('master_case', reel.pos.x, reel.pos.z, i * 0.7);
    return { id: info.id, code: info.code, label: info.label, zone: reel.zone, pos: reel.pos, prop };
  });

  const extraction = {
    pos: v(35.6, 0, 28.5), // behind the truck's rear doors
    radius: G.config.flow.extraction.radius,
    label: text.extraction.label,
    code: text.extraction.code,
    prop: truck,
  };

  // ---------------------------------------------------------------------------------------------
  // Data for AI, flow and atmosphere
  // ---------------------------------------------------------------------------------------------

  const zones = [
    { id: 'west', name: 'The station end', minX: -46, maxX: -30, minZ: -34, maxZ: 34 },
    { id: 'shop', name: 'Chop shop', minX: -30, maxX: 22, minZ: -34, maxZ: -11 },
    { id: 'avenue', name: 'The avenue', minX: -30, maxX: 22, minZ: -11, maxZ: 34 },
    { id: 'lot', name: 'The lot', minX: 22, maxX: 46, minZ: -34, maxZ: 34 },
  ];

  function zoneAt(x, z) {
    for (const zone of zones) {
      if (x >= zone.minX && x <= zone.maxX && z >= zone.minZ && z <= zone.maxZ) return zone.id;
    }
    return 'avenue';
  }

  const spawn = (x, y, z, type) => ({ pos: v(x, y, z), zone: zoneAt(x, z), type });
  // No spawns in the west zone: the start stays quiet.
  const enemySpawns = [
    spawn(-26, 0, -9, 'ground'),
    spawn(4, 0, -9.5, 'ground'),
    spawn(20.5, 0, 6.2, 'ground'),
    spawn(-10, 0, 22, 'ground'),
    spawn(8, 0, 30, 'ground'),
    spawn(-17.9, 0, -28.2, 'ground'),
    spawn(-4.5, 0, -15.5, 'ground'),
    spawn(4, 0, -27, 'ground'),
    spawn(27, 0, -29.5, 'ground'),
    spawn(43.5, 0, -9, 'ground'),
    spawn(25, 0, 31.5, 'ground'),
    spawn(44, 0, 15, 'ground'),
    spawn(-11, 9, -21, 'air'), // over the shop roof
    spawn(16, 10.5, -22, 'air'), // over the deli
    spawn(0, 9.5, -8, 'air'), // beside the El deck
    spawn(8, 10, 18, 'air'), // over S3
    spawn(34, 10, -22, 'air'), // over the court
    spawn(34, 11, 22, 'air'), // over the lot
  ];

  const coverPoints = [
    [-26.5, -4.4], [-21.5, -4.5], [-19.5, 4.5], [-13, -4.4], [-8, -4.3], [-9.5, 0.6], [-3, 4.4], [-0.4, -1.4],
    [6.5, -4.4], [5, 4.2], [12.5, 4], [13.4, -4.4], [20.8, 1.2], [25, 1.4], [-18.5, -10], [-11, 9.6],
    [-13.5, -18.6], [-7.3, -20.2], [-16, -27], [-4, -26.5], [29.6, -20.6], [36.8, -24.6], [29.6, 16], [34.5, 22.6],
    [35.4, 24.6], [5.4, 27.6],
  ].map(([x, z]) => ({ pos: v(x, 0, z), zone: zoneAt(x, z) }));
  coverPoints.push({ pos: v(6, DECK_Y, 9.6), zone: 'avenue' }); // on the deck

  const cinematicPath = [
    [-43, 2.2, 9, -30, 1.5, 4],
    [-34, 2, 6, -15, 1.5, 1],
    [-22, 2.4, 3.6, -4, 1, 1],
    [-10.5, 2.6, 4.6, -4, 0.8, 1],
    [-6, 2.4, -5.2, -9, 1.5, -14],
    [-10, 2.2, -13.5, -9, 1, -21],
    [-12, 2.6, -20, -6, 1.5, -26],
    [-8.5, 2.4, -9, 10, 3, -9.5],
    [8, 3.2, -8.6, 33, 1.5, -22],
    [26, 3.6, -15.5, 33, 1, -22],
    [30, 4.6, -2, 38, 1.5, 22],
    [33.5, 3, 17, 40.5, 1.5, 28.5],
  ].map(([x, y, z, lx, ly, lz]) => ({ pos: v(x, y, z), look: v(lx, ly, lz) }));

  const explosives = [
    { type: 'propane', pos: v(-15.9, 0, -8.6), yaw: 0 }, // at the food cart
    { type: 'propane', pos: v(1.4, 0, 7.6), yaw: 0 }, // at the foot of the deck
    { type: 'propane', pos: v(26.3, 0, 12.4), yaw: 0 }, // at the lot booth
    { type: 'rack', pos: v(-4.6, 0, -13.2), yaw: Math.PI / 2 }, // inside the shop, right of the door
  ];

  const interiorBoxes = [{ min: v(SHOP.minX, 0, SHOP.minZ), max: v(SHOP.maxX, SHOP.eave, SHOP.maxZ) }];

  /** 1 inside the shop, falling to 0 over a metre and a half outside its walls. */
  function interiorAt(pos) {
    let best = 0;
    for (const box of interiorBoxes) {
      const dx = Math.max(box.min.x - pos.x, 0, pos.x - box.max.x);
      const dy = Math.max(box.min.y - pos.y, 0, pos.y - box.max.y);
      const dz = Math.max(box.min.z - pos.z, 0, pos.z - box.max.z);
      best = Math.max(best, clamp01(1 - Math.hypot(dx, dy, dz) / INTERIOR_FADE));
    }
    return best;
  }

  /** Surface of the bare ground (things standing on it report their own). */
  function groundSurfaceAt(x, z) {
    if (x > SHOP.minX && x < SHOP.maxX && z > SHOP.minZ && z < SHOP.maxZ) return 'concrete';
    if (x > COURT.minX && x < COURT.maxX && z > COURT.minZ && z < COURT.maxZ) return 'concrete';
    if (x > -16 && x < -4 && z > 12 && z < 25) return 'dirt';
    return Math.abs(z) >= 7 && Math.abs(z) <= 11 ? 'concrete' : 'asphalt';
  }

  // ---------------------------------------------------------------------------------------------
  // Finish: merge, publish bounds, nudge AI points onto walkable ground
  // ---------------------------------------------------------------------------------------------

  root.add(mergeStatic(staticRoot), dynamicRoot);
  G.scene.add(root);
  physics.setBounds(BOUNDS);

  for (const point of [...coverPoints, ...enemySpawns]) {
    if (point.type === 'air' || point.pos.y > 0.5 || physics.nav.isWalkable(point.pos.x, point.pos.z)) continue;
    const near = physics.nav.nearestWalkable(point.pos.x, point.pos.z, 2);
    if (near) point.pos.set(near.x, 0, near.z);
  }

  return {
    root,
    bounds: { ...BOUNDS },
    playerStart: { pos: v(-40, 0, 8.6), yaw: -Math.PI / 2 }, // facing east down the avenue
    objectives,
    extraction,
    enemySpawns,
    zones,
    zoneAt,
    interiorBoxes,
    interiorAt,
    coverPoints,
    cinematicPath,
    explosives,
    lamps,
    steam: [v(-15, 0, 0.6), v(9, 0, -3), v(27, 0, 3)],
    el: { y: EL_Y, minX: BOUNDS.minX, maxX: BOUNDS.maxX, minZ: -EL_HALF, maxZ: EL_HALF },
    vantage: { stairsFoot: v(-1.9, 0, 10.7), deck: v(8, DECK_Y, 10.2) },
    groundSurfaceAt,
    update(dt) {
      for (let i = 0; i < animated.length; i++) animated[i].update(dt);
    },
  };
}
