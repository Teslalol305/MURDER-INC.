// V&R AUTO BODY: the chop shop, the block's only interior. A cinder-block garage with a 6 m roll-up
// door and a smaller bay on the avenue, a side door into the alley, skylights, two lifts, a stripped
// car on stands, a mezzanine office with a glass front in the north-west corner, four work lights.

import * as THREE from 'three';
import { LIFT } from './ground.js';
import { SHOP } from './layout.js';
import { wallFrame } from './buildings.js';

// Painted block (catalogue colour) on the vertex-tinted material, the same one the dado below uses.
const WALL = ['cinder', { color: 0x8a8880 }];
const WORK = 0xffc48a;
const DOWN = new THREE.Vector3(0, -1, 0);

export function buildShop(kit) {
  const { mats, rng } = kit;
  const S = SHOP;
  const t = S.wall;
  const ix0 = S.minX + t; // inner faces
  const ix1 = S.maxX - t;
  const iz0 = S.minZ + t;
  const iz1 = S.maxZ - t;
  const top = S.parapet;
  const text = kit.G.config.text.world;
  const animated = [];

  // ---------------------------------------------------------------------------------------------
  // Shell: walls with their openings, floor, roof with skylights
  // ---------------------------------------------------------------------------------------------

  const wall = (x0, x1, y0, y1, z0, z1) => kit.block(WALL, x0, x1, y0, y1, z0, z1, { tag: 'shop-wall' });

  wall(S.minX, S.maxX, 0, top, S.minZ, iz0); // north
  wall(S.minX, ix0, 0, top, iz0, S.maxZ); // west
  // South wall: the roll-up door and the second bay.
  wall(ix0, S.roll.x0, 0, top, iz1, S.maxZ);
  wall(S.roll.x0, S.roll.x1, S.roll.h, top, iz1, S.maxZ);
  wall(S.roll.x1, S.bay.x0, 0, top, iz1, S.maxZ);
  wall(S.bay.x0, S.bay.x1, S.bay.h, top, iz1, S.maxZ);
  wall(S.bay.x1, S.maxX, 0, top, iz1, S.maxZ);
  // East wall: the side door, with the extractor fan in the wall above it.
  const fan = { y0: 3.9, y1: 5.1, z: (S.side.z0 + S.side.z1) / 2 };
  wall(ix1, S.maxX, 0, top, iz0, S.side.z0);
  wall(ix1, S.maxX, S.side.h, fan.y0, S.side.z0, S.side.z1);
  wall(ix1, S.maxX, fan.y1, top, S.side.z0, S.side.z1);
  wall(ix1, S.maxX, 0, top, S.side.z1, iz1);
  kit.solid(ix1, S.maxX, fan.y0, fan.y1, S.side.z0, S.side.z1, { surface: 'metal', tag: 'shop-wall', noNav: true });
  for (const z of [S.side.z0, S.side.z1 - 0.4]) kit.box(WALL, ix1, S.maxX, fan.y0, fan.y1, z, z + 0.4);

  // Floor: sealed concrete right through the door openings, bay lines, a drain, oil where cars stood.
  kit.flat('concrete_dark', ix0, ix1, iz0, iz1, LIFT.patch);
  kit.flat('concrete_dark', S.roll.x0, S.roll.x1, iz1, S.maxZ, LIFT.patch);
  kit.flat('concrete_dark', S.bay.x0, S.bay.x1, iz1, S.maxZ, LIFT.patch);
  kit.flat('concrete_dark', ix1, S.maxX, S.side.z0, S.side.z1, LIFT.patch);
  for (const [x0, x1, z0, z1] of [[-21.6, -16.8, -20.4, -14.2], [-3.4, 0.8, -22.6, -16.6], [-14.6, -9.4, -18.4, -12.4]]) {
    kit.flat('paint_yellow', x0, x1, z0, z0 + 0.1, LIFT.paint);
    kit.flat('paint_yellow', x0, x0 + 0.1, z0, z1, LIFT.paint);
    kit.flat('paint_yellow', x1 - 0.1, x1, z0, z1, LIFT.paint);
  }
  kit.box('metal_dark', -5.2, -4.5, 0, 0.022, -17.3, -16.6, { noBottom: true, cast: false });
  const oil = mats.decal('oil');
  const grime = mats.decal('grime');
  for (const [x, z] of [[-19.2, -17.3], [-12.3, -15.6], [-1.3, -19.6], [-9, -24], [-4.5, -13.2], [2.8, -24.5], [-15.5, -21.8], [-7.6, -27.8]]) {
    kit.overlay(rng.chance(0.6) ? oil : grime, '+y', x, LIFT.decal, z, { yaw: rng.range(0, Math.PI * 2), w: oil.w * rng.range(0.8, 1.5), h: oil.h * rng.range(0.8, 1.5) });
  }

  // Roof slab, with four skylights: night-blue panes in steel frames below, kerbs on top.
  kit.block('concrete_dark', S.minX + 0.02, S.maxX - 0.02, S.eave, S.eave + S.roof, S.minZ + 0.02, S.maxZ - 0.02, { tag: 'shop-roof', noNav: true });
  // From below the panes are the sky (night-blue, or the bright afternoon: mats follows the time of day);
  // from above they are dark glass that mirrors it.
  const sky = 'glass_skylight';
  const skyTop = 'glass_dark';
  for (const [x, z] of S.skylights) {
    kit.flat(sky, x - 1.2, x + 1.2, z - 1.7, z + 1.7, S.eave - 0.012, { down: true, receive: false });
    for (const dx of [-1.2, 0, 1.2]) kit.box('metal_dark', x + dx - 0.04, x + dx + 0.04, S.eave - 0.1, S.eave, z - 1.7, z + 1.7, { cast: false });
    for (const dz of [-1.7, 0, 1.7]) kit.box('metal_dark', x - 1.2, x + 1.2, S.eave - 0.1, S.eave, z + dz - 0.04, z + dz + 0.04, { cast: false });
    kit.box('metal_galv', x - 1.35, x + 1.35, S.eave + S.roof, S.eave + S.roof + 0.3, z - 1.85, z + 1.85, { noBottom: true });
    kit.flat(skyTop, x - 1.25, x + 1.25, z - 1.75, z + 1.75, S.eave + S.roof + 0.305, { receive: false });
  }
  // Steel under the roof: four beams across the short span on two columns, purlins the long way.
  for (const x of [-18, -12, -6, 0]) {
    kit.box('steel_el', x - 0.11, x + 0.11, S.eave - 0.45, S.eave, iz0, iz1, { noTop: true });
    kit.box('steel_el', x - 0.2, x + 0.2, S.eave - 0.45, S.eave - 0.4, iz0, iz1);
  }
  for (const z of [-27, -22.6, -18.2, -13.8]) kit.box('steel_el', ix0, ix1, S.eave - 0.16, S.eave, z - 0.06, z + 0.06, { noTop: true });
  for (const [x, z] of [[-18, -21], [-6, -21]]) {
    kit.block('steel_el', x - 0.14, x + 0.14, 0, S.eave - 0.45, z - 0.14, z + 0.14, { tag: 'shop-column' });
    kit.box('paint_yellow', x - 0.15, x + 0.15, 0, 1.2, z - 0.15, z + 0.15, { noTop: true, noBottom: true, cast: false });
  }

  // Painted dado on the inside of the walls, and the kind of paper a shop wall collects.
  const dado = ['cinder', { color: 0x27414b }];
  const inner = {
    n: wallFrame(kit, '+z', iz0),
    s: wallFrame(kit, '-z', iz1),
    w: wallFrame(kit, '+x', ix0),
    e: wallFrame(kit, '-x', ix1),
  };
  const dadoRuns = [
    [inner.n, -15.4, ix1], [inner.w, -25, iz1], [inner.s, ix0, S.roll.x0], [inner.s, S.roll.x1, S.bay.x0], [inner.s, S.bay.x1, ix1],
    [inner.e, iz0, S.side.z0], [inner.e, S.side.z1, iz1],
  ];
  for (const [F, u0, u1] of dadoRuns) {
    F.quad(dado, u0, u1, 0, 1.35, 0.006, { cast: false });
    F.box('paint_yellow', u0, u1, 1.35, 1.42, 0, 0.012, { cast: false });
  }
  inner.n.overlay(mats.poster('ad', 3), -2.6, 2.3);
  inner.n.overlay(mats.poster('show', 5), -1.2, 2.2);
  inner.n.overlay(mats.poster('wanted', 2), 2.6, 2.0);
  inner.e.overlay(mats.poster('show', 9), -15, 2.2);
  inner.e.overlay(mats.poster('torn', 4), -14.2, 2.05);
  inner.w.overlay(mats.poster('ad', 6), -17.6, 2.3);
  inner.s.overlay(mats.graffiti('VULTURES', 3, 0x8a1a22), -6.1, 2.5, 0.02, { w: 3.6, h: 1.1 });
  const exit = mats.sign({ text: 'EXIT', w: 0.7, h: 0.3, style: 'box', bg: 0x7a1410, fg: 0xfff1d0, glow: 0xff3030 });
  inner.e.overlay(exit, fan.z, S.side.h + 0.35, 0.03);
  inner.e.lamp(fan.z, S.side.h + 0.35, 0.3, 'neon', 0xff3030, 4, 4, { priority: 2 });

  // ---------------------------------------------------------------------------------------------
  // Doors
  // ---------------------------------------------------------------------------------------------

  // Roll-up doors: rolled into their boxes, a few slats still hanging in the opening.
  for (const d of [S.roll, S.bay]) {
    kit.box('roll_gate', d.x0, d.x1, d.h - 0.55, d.h, S.maxZ - 0.26, S.maxZ - 0.2);
    kit.box('metal_dark', d.x0, d.x1, d.h - 0.62, d.h - 0.55, S.maxZ - 0.29, S.maxZ - 0.17);
    kit.box('metal_dark', d.x0 - 0.1, d.x1 + 0.1, d.h, d.h + 0.42, iz1 - 0.34, iz1);
    for (const x of [d.x0, d.x1]) kit.box('metal_dark', x - 0.05, x + 0.05, 0, d.h, S.maxZ - 0.3, S.maxZ - 0.16);
    for (const x of [d.x0 - 0.45, d.x1 + 0.45]) kit.place('bollard', x, S.maxZ + 0.35, 0, { color: 0xf2c21a });
  }
  // Side door: the leaf swung back flat against the alley wall, a lamp over it.
  kit.box('metal_dark', S.maxX, S.maxX + 0.06, 0, S.side.h - 0.08, S.side.z1, S.side.z1 + 1.9);
  kit.box('metal_dark', ix1 - 0.03, S.maxX + 0.03, S.side.h - 0.08, S.side.h, S.side.z0, S.side.z1);
  const alleyFace = wallFrame(kit, '+x', S.maxX);
  alleyFace.box('metal_dark', fan.z - 0.14, fan.z + 0.14, S.side.h + 0.5, S.side.h + 0.58, 0, 0.3);
  alleyFace.box(kit.glow(WORK, 4), fan.z - 0.09, fan.z + 0.09, S.side.h + 0.38, S.side.h + 0.5, 0.1, 0.28, { cast: false, receive: false });
  alleyFace.lamp(fan.z, S.side.h + 0.35, 0.5, 'street', WORK, 16, 9, { priority: 4 });

  // The extractor fan: a guard on both faces of the wall and blades that never stop.
  for (const x of [ix1 + 0.02, S.maxX - 0.02]) {
    for (const dy of [0.1, 0.35, 0.6, 0.85, 1.1]) kit.box('metal_dark', x - 0.015, x + 0.015, fan.y0 + dy - 0.015, fan.y0 + dy + 0.015, S.side.z0 + 0.4, S.side.z1 - 0.4, { cast: false });
  }
  const blades = new THREE.Group();
  blades.userData.noMerge = true;
  blades.position.set((ix1 + S.maxX) / 2, (fan.y0 + fan.y1) / 2, fan.z);
  for (let i = 0; i < 4; i++) {
    const blade = kit.mesh(new THREE.BoxGeometry(0.03, 0.5, 0.2), 'metal_galv', { parent: blades, cast: false });
    blade.position.set(0, Math.cos((i * Math.PI) / 2) * 0.3, Math.sin((i * Math.PI) / 2) * 0.3);
    blade.rotation.x = (i * Math.PI) / 2;
    blade.rotation.y = 0.5;
  }
  kit.dynamicRoot.add(blades);
  animated.push({
    update(dt) {
      blades.rotation.x += dt * 1.7;
    },
  });

  // ---------------------------------------------------------------------------------------------
  // Mezzanine office (north-west corner)
  // ---------------------------------------------------------------------------------------------
  {
    const M = S.mezz;
    const deck = M.y;
    kit.box('metal_dark', M.x0, M.x1, deck - 0.12, deck, M.z0, M.z1);
    kit.solid(M.x0, M.x1, deck - 0.14, deck, M.z0, M.z1, { surface: 'metal', tag: 'mezzanine' });
    kit.box('paint_yellow', M.x0, M.x1, deck - 0.3, deck, M.z1 - 0.08, M.z1 + 0.02); // edge beams
    kit.box('paint_yellow', M.x1 - 0.08, M.x1 + 0.02, deck - 0.3, deck, M.z0, M.z1);
    for (const [x, z] of [[M.x1 - 0.1, M.z1 - 0.1], [-19.5, M.z1 - 0.1], [M.x0 + 0.1, M.z1 - 0.1], [M.x1 - 0.1, M.z0 + 0.1]]) {
      kit.block('steel_el', x - 0.08, x + 0.08, 0, deck - 0.3, z - 0.08, z + 0.08, { tag: 'mezzanine' });
    }

    // The office: timber panel to waist height, glass above, a doorway at the east end of its front.
    const oTop = deck + 2.5;
    const sill = deck + 0.95;
    const panel = ['plywood', { color: 0x6b5a43 }];
    const runs = [
      // [x0, x1, z0, z1, facing of the outside]
      [M.x0, M.doorX[0], M.officeZ - 0.05, M.officeZ + 0.05, '+z'],
      [M.officeX - 0.05, M.officeX + 0.05, M.z0, M.officeZ, '+x'],
    ];
    for (const [x0, x1, z0, z1] of runs) {
      kit.block(panel, x0, x1, deck, sill, z0, z1, { tag: 'office' });
      kit.box('metal_dark', x0 - 0.01, x1 + 0.01, sill, sill + 0.05, z0 - 0.01, z1 + 0.01);
      kit.box('metal_dark', x0 - 0.01, x1 + 0.01, oTop - 0.3, oTop, z0 - 0.01, z1 + 0.01);
      // Glass you can shoot through but not walk through.
      kit.solid(x0, x1, sill, oTop, z0, z1, { surface: 'glass', tag: 'office-glass', playerOnly: true });
    }
    const glass = ['glass_store', { transparent: true, opacity: 0.3 }];
    kit.quad(glass, '+z', (M.x0 + M.doorX[0]) / 2, (sill + oTop - 0.3) / 2 + 0.025, M.officeZ + 0.02, M.doorX[0] - M.x0, oTop - 0.35 - sill, { cast: false, receive: false });
    kit.quad(glass, '+x', M.officeX + 0.02, (sill + oTop - 0.3) / 2 + 0.025, (M.z0 + M.officeZ) / 2, M.officeZ - M.z0, oTop - 0.35 - sill, { cast: false, receive: false });
    for (let x = M.x0; x <= M.doorX[0] + 0.01; x += (M.doorX[0] - M.x0) / 3) kit.box('metal_dark', x - 0.03, x + 0.03, sill, oTop - 0.3, M.officeZ - 0.04, M.officeZ + 0.04);
    for (const z of [M.z0 + 0.03, (M.z0 + M.officeZ) / 2, M.officeZ]) kit.box('metal_dark', M.officeX - 0.04, M.officeX + 0.04, sill, oTop - 0.3, z - 0.03, z + 0.03);
    // Door frame (the door itself is long gone) and the office roof.
    kit.box('metal_dark', M.doorX[0] - 0.04, M.doorX[0] + 0.04, deck, oTop, M.officeZ - 0.05, M.officeZ + 0.05);
    kit.box('metal_dark', M.doorX[0], M.doorX[1], deck + 2.1, oTop, M.officeZ - 0.05, M.officeZ + 0.05);
    kit.solid(M.doorX[0], M.doorX[1], deck + 2.1, oTop, M.officeZ - 0.05, M.officeZ + 0.05, { surface: 'metal', tag: 'office' });
    kit.block(panel, M.x0, M.officeX + 0.05, oTop, oTop + 0.1, M.z0, M.officeZ + 0.05, { tag: 'office' });
    // Inside: a desk, a cabinet, a safe, a tube on the ceiling that is still on.
    kit.place('workbench', -21.2, -29.9, 0, { y: deck });
    kit.place('tool_chest', -23.1, -28.2, Math.PI / 2, { y: deck });
    kit.block('metal_dark', -18.5, -17.7, deck, deck + 0.85, -30.4, -29.6, { tag: 'safe' });
    kit.box('chrome', -18.2, -18.0, deck + 0.4, deck + 0.5, -29.6, -29.56, { cast: false });
    kit.box(kit.glow(0xfff1d0, 3), -21.4, -19.8, oTop - 0.06, oTop - 0.02, -28.9, -28.75, { cast: false, receive: false });
    kit.lamp(-20.6, oTop - 0.3, -28.8, 'work', 0xfff1d0, 14, 8, { priority: 5 });
    inner.n.overlay(mats.poster('ad', 8), -20.2, deck + 1.7);
    inner.w.overlay(mats.poster('ipx', 1), -28.6, deck + 1.6);

    // Railings (thin rails: they stop a walker, not a bullet) along the open edges and down the stair.
    const railTop = deck + 1.05;
    const rail = (x0, z0, x1, z1) => {
      for (const y of [railTop, deck + 0.55]) kit.beam('paint_yellow', [x0, y, z0], [x1, y, z1], 0.045, 0.045, { cast: false });
      const n = Math.max(1, Math.round(Math.hypot(x1 - x0, z1 - z0) / 1.4));
      for (let i = 0; i <= n; i++) {
        const x = x0 + ((x1 - x0) * i) / n;
        const z = z0 + ((z1 - z0) * i) / n;
        kit.box('paint_yellow', x - 0.022, x + 0.022, deck, railTop, z - 0.022, z + 0.022, { cast: false });
      }
      kit.solid(Math.min(x0, x1) - 0.04, Math.max(x0, x1) + 0.04, deck, railTop, Math.min(z0, z1) - 0.04, Math.max(z0, z1) + 0.04, { surface: 'metal', tag: 'railing', playerOnly: true });
    };
    const st = S.stair;
    rail(M.x0, M.z1 - 0.04, M.x1, M.z1 - 0.04);
    rail(M.x1 - 0.04, M.z0, M.x1 - 0.04, st.z0);

    // The stair: twelve open treads of 0.23 m, steel stringers, a handrail on both sides.
    kit.stairs('metal_dark', st.x0, st.x1, st.z0, st.z1, 0, deck, st.risers, '-x', { open: true, tag: 'shop-stair', surface: 'metal' });
    for (const z of [st.z0 + 0.03, st.z1 - 0.03]) {
      kit.beam('steel_el', [st.x1, 0.02, z], [st.x0, deck - 0.08, z], 0.06, 0.26);
      kit.beam('paint_yellow', [st.x1, 1.0, z], [st.x0, railTop, z], 0.045, 0.045, { cast: false });
      for (const f of [0, 0.5, 1]) {
        const x = st.x1 + (st.x0 - st.x1) * f;
        const y = deck * f;
        kit.box('paint_yellow', x - 0.022, x + 0.022, y, y + 1.03, z - 0.022, z + 0.022, { cast: false });
      }
    }
    for (const z of [st.z0, st.z1]) kit.solid(st.x0, st.x1, 0, deck + 1.05, z - 0.04, z + 0.04, { surface: 'metal', tag: 'railing', playerOnly: true });

    // Under the deck: tyres, drums and boxes in the half dark, a tube that flickers on the wall.
    kit.place('tire_stack', -22.6, -29.6);
    kit.place('tire_stack', -21.6, -29.9);
    kit.place('oil_drum', -17.2, -30.0);
    kit.place('oil_drum', -16.4, -29.7);
    kit.place('pallet_stack', -19.4, -29.8);
    kit.place('cardboard_boxes', -22.8, -26.4, 0.3);
    kit.place('compressor', -16.6, -26.6, Math.PI / 2);
    kit.box(kit.glow(0xcfe4ff, 2.4), -20.6, -19.4, deck - 0.2, deck - 0.16, iz0 + 0.02, iz0 + 0.1, { cast: false, receive: false });
    kit.lamp(-20, deck - 0.4, iz0 + 0.4, 'work', 0xcfe4ff, 8, 6, { priority: 3 });
  }

  // ---------------------------------------------------------------------------------------------
  // The floor: lifts, cars, the ring of cover around reel 2, the benches and racks along the walls
  // ---------------------------------------------------------------------------------------------

  kit.place('car_lift', -19.2, -17.3, Math.PI / 2);
  kit.place('sedan', -19.2, -17.3, Math.PI / 2, { y: 1.95, seed: 2, noNav: true }); // the one car in the air
  kit.place('car_lift', -1.3, -19.6, Math.PI / 2);
  kit.place('sedan', -1.3, -19.5, -Math.PI / 2, { seed: 5 });
  kit.place('car_on_stands', -12.2, -15.4, Math.PI / 2 + 0.12);

  // Around the reel (−9.5, −21.5): low cover at 2–5 m on every side, the column as the one hard piece.
  kit.place('tool_chest', -7.1, -19.5, 0.4);
  kit.place('tool_chest', -12.6, -23.1, 1.35);
  kit.place('oil_drum', -12.1, -19.4);
  kit.place('oil_drum', -11.4, -20.1);
  kit.place('tire_stack', -6.5, -23.4);
  kit.place('tire_stack', -7.3, -24.1);
  kit.place('engine_hoist', -9.9, -25.3, 0.2);
  kit.place('crate_wood', -13.4, -20.9, 0.2);
  kit.place('milk_crates', -9.2, -18.2);

  // Along the walls.
  kit.place('workbench', -6.5, iz0 + 0.5);
  kit.place('tool_chest', -4.6, iz0 + 0.38);
  kit.place('shelf_rack', -0.4, iz0 + 0.55);
  kit.place('pallet_stack', 2.9, -29.6, 0.1);
  kit.place('cardboard_boxes', 1.4, -27.6, 0.5);
  kit.place('shelf_rack', ix1 - 0.55, -28.5, Math.PI / 2);
  kit.place('shelf_rack', ix1 - 0.55, -25.4, Math.PI / 2);
  kit.place('shelf_rack', ix1 - 0.55, -17.3, Math.PI / 2);
  kit.place('vending_machine', ix1 - 0.5, -13.2, -Math.PI / 2);
  kit.place('tire_stack', -8.2, iz1 - 0.6);
  kit.place('tire_stack', -7.3, iz1 - 0.7);
  kit.place('oil_drum', -4.2, iz1 - 0.55);
  kit.place('workbench', -21.6, iz1 - 0.55);
  kit.place('shelf_rack', ix0 + 0.55, -22.3, Math.PI / 2);
  kit.place('compressor', 3.6, iz1 - 0.5);
  kit.place('crate_wood', 2.6, -15.2, 0.4);
  kit.place('engine_hoist', -16.9, -12.7, 1.2);

  // Four work lights: high-bay lamps on conduit drops. These are the real lights of the interior.
  const bulb = kit.glow(0xffd9a8, 6);
  for (const [x, z] of S.workLights) {
    kit.box('metal_dark', x - 0.02, x + 0.02, 5.32, S.eave - 0.16, z - 0.02, z + 0.02, { cast: false });
    kit.cyl('metal_dark', x, 5.08, 5.34, z, 0.36, 12, { radiusTop: 0.11, open: true, cast: false });
    kit.cyl(bulb, x, 5.06, 5.1, z, 0.24, 12, { cast: false, receive: false });
    kit.lamp(x, 5, z, 'work', WORK, 34, 13, { dir: DOWN });
  }

  // ---------------------------------------------------------------------------------------------
  // Outside: fascia and signs on the avenue front, rooftop plant
  // ---------------------------------------------------------------------------------------------
  {
    const F = wallFrame(kit, '+z', S.maxZ);
    F.box(['corrugated', { color: 0x1a2b3a }], S.minX + 0.3, S.maxX - 0.3, 4.75, 6.05, 0, 0.1);
    const main = mats.sign({ text: text.shop, w: 8, h: 1.05, style: 'box', bg: 0x101113, fg: 0xf6c21a, glow: 0xf6c21a });
    F.overlay(main, (S.roll.x0 + S.roll.x1) / 2, 5.4, 0.13);
    F.lamp((S.roll.x0 + S.roll.x1) / 2, 5.4, 0.8, 'neon', 0xf6c21a, 14, 10);
    const side = mats.sign({ text: 'TIRES  ·  BRAKES  ·  EXHAUST', w: 5.4, h: 0.6, style: 'painted', fg: 0xe9e2cf, bg: 0x1a2b3a, lit: false });
    F.overlay(side, (S.bay.x0 + S.bay.x1) / 2, 5.4, 0.13);
    const tow = mats.sign({ text: 'INSPECTIONS  ·  24 HR TOWING', w: 5.6, h: 0.6, style: 'painted', fg: 0xe9e2cf, bg: 0x1a2b3a, lit: false });
    F.overlay(tow, -19.6, 5.4, 0.13);
    const flat = mats.sign({ text: 'FLAT FIX', sub: 'NO APPOINTMENT', w: 2.6, h: 1.1, style: 'stencil', fg: 0xe6e4dc, lit: false });
    F.overlay(flat, -6.1, 2.6, 0.02);
    F.overlay(mats.graffiti('VLTR', 7, 0x8a1a22), 3.6, 1.5, 0.02);
    F.overlay(mats.poster('show', 12), 2.2, 1.7);
    F.overlay(mats.poster('torn', 13), 2.95, 1.6);
    // Gooseneck lamps over the fascia.
    for (const u of [-21.5, -12, -1.3]) {
      F.box('metal_dark', u - 0.02, u + 0.02, 6.1, 6.5, 0.1, 0.14, { cast: false });
      F.box('metal_dark', u - 0.02, u + 0.02, 6.46, 6.5, 0.1, 0.72, { cast: false });
      F.box('metal_dark', u - 0.17, u + 0.17, 6.34, 6.46, 0.55, 0.89, { cast: false });
      F.box(kit.glow(WORK, 4.5), u - 0.11, u + 0.11, 6.31, 6.34, 0.61, 0.83, { cast: false, receive: false });
      F.lamp(u, 6.2, 0.72, 'street', WORK, 16, 10, { priority: 4, dir: DOWN });
    }
    kit.box('concrete', S.minX - 0.04, S.maxX + 0.04, top, top + 0.08, S.maxZ - t - 0.04, S.maxZ + 0.04);
    kit.box('concrete', S.maxX - t - 0.04, S.maxX + 0.04, top, top + 0.08, S.minZ, S.maxZ - t);
    kit.place('ac_unit', -15, -27, 0, { y: S.eave + S.roof, collide: false });
    kit.place('ac_unit', 2.5, -14.5, Math.PI / 2, { y: S.eave + S.roof, collide: false });
    kit.cyl('metal_galv', -3, S.eave + S.roof, S.eave + S.roof + 1.3, -27.5, 0.22, 10);
  }

  return {
    animated,
    interior: { min: new THREE.Vector3(S.minX, 0, S.minZ), max: new THREE.Vector3(S.maxX, S.eave + S.roof, S.maxZ) },
  };
}
