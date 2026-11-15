// The solid buildings of the block: brick walk-ups with storefronts at street level, window facades
// above (G.mats.facade), cornices, parapets, fire escapes and rooftop clutter, plus the backs of the
// neighbours that close the block's north, east and south edges. Each building is one or a few colliders.
//
// Everything is built in the local frame of a wall face: `u` runs along the wall, `d` is the distance
// out of it (negative = recessed), y is world height.

import { BOUNDS, BUILDINGS, FLOOR, GROUND_FLOOR, KERB, PADS, SHED, SHOP, buildingHeight } from './layout.js';

const PARAPET = 0.9;
const BAY = 3.1; // nominal width of one window bay
const WARM = 0xffc98a;
const COOL = 0xcfe4ff;

/** Local frame of a wall face. `facing` is the outward normal: '+x' | '-x' | '+z' | '-z'. */
export function wallFrame(kit, facing, plane) {
  const sign = facing[0] === '+' ? 1 : -1;
  const alongX = facing[1] === 'z'; // a wall that faces ±z runs along x
  const at = (u, d) => (alongX ? [u, plane + sign * d] : [plane + sign * d, u]);
  return {
    facing,
    plane,
    sign,
    alongX,
    at,
    box(m, u0, u1, y0, y1, d0, d1, o) {
      const a = plane + sign * d0;
      const b = plane + sign * d1;
      const p0 = Math.min(a, b);
      const p1 = Math.max(a, b);
      return alongX ? kit.box(m, u0, u1, y0, y1, p0, p1, o) : kit.box(m, p0, p1, y0, y1, u0, u1, o);
    },
    quad(m, u0, u1, y0, y1, d, o) {
      const [x, z] = at((u0 + u1) / 2, d);
      return kit.quad(m, facing, x, (y0 + y1) / 2, z, u1 - u0, y1 - y0, o);
    },
    overlay(item, u, y, d = 0.02, o) {
      const [x, z] = at(u, d);
      return kit.overlay(item, facing, x, y, z, o);
    },
    /** Prism whose profile is given as [[d, y], …] and runs along the wall from u0 to u1. */
    prism(m, profile, u0, u1, o) {
      return kit.prism(m, profile.map(([d, y]) => [plane + sign * d, y]), alongX ? 'x' : 'z', u0, u1, o);
    },
    lamp(u, y, d, kind, color, intensity, range, o) {
      const [x, z] = at(u, d);
      return kit.lamp(x, y, z, kind, color, intensity, range, o);
    },
    /** A wall-mounted catalogue prop whose back sits on the wall (props are built facing +z). */
    mount(name, u, y, depth, o = {}) {
      const [x, z] = at(u, depth / 2);
      const yaw = { '+z': 0, '-z': Math.PI, '+x': Math.PI / 2, '-x': -Math.PI / 2 }[facing];
      return kit.place(name, x, z, yaw, { y, collide: false, ...o });
    },
  };
}

/**
 * One face, from y0 to y1, as a window facade. spec:
 *   base    wall material          floors   storeys the facade counts from its foot to the roof
 *   floorH  storey height          yBase    height of the facade's foot (default 0). On a street front it
 *   bays, lit, seed                         sits below y0, so the row hidden behind the shops is skipped.
 * With the real library the windows are a painted layer in the material (one repeat spans the face);
 * without it (the stub, or the layer switched off) plain brick gets modelled windows instead.
 */
function facade(kit, F, u0, u1, y0, y1, spec) {
  const w = u1 - u0;
  const floorH = spec.floorH || FLOOR;
  const yBase = spec.yBase || 0;
  const bays = spec.bays || Math.max(1, Math.round(w / BAY));
  const lit = spec.lit ?? 0.22;
  const material = kit.mats.facade({ base: spec.base, floors: spec.floors, bays, floorH, w, lit, seed: spec.seed ?? 1, shopfront: false });
  if (material.userData && material.userData.facade) {
    F.quad(material, u0, u1, y0, y1, 0, { uvOffset: [0, y0 - yBase] });
    return;
  }
  F.quad(material, u0, u1, y0, y1, 0);
  const rng = kit.rng;
  const bayW = w / bays;
  for (let f = 1; f < spec.floors; f++) {
    const sill = yBase + f * floorH + 0.95;
    if (sill < y0 + 0.3 || sill + 1.9 > y1) continue;
    for (let b = 0; b < bays; b++) {
      const c = u0 + (b + 0.5) * bayW;
      const glass = rng.next() < lit ? (rng.chance(0.25) ? 'glass_lit_cool' : 'glass_lit_warm') : 'glass_dark';
      F.quad(glass, c - 0.55, c + 0.55, sill, sill + 1.65, 0.03, { cast: false });
      F.box('concrete', c - 0.68, c + 0.68, sill - 0.1, sill, 0, 0.1);
      F.box('concrete', c - 0.66, c + 0.66, sill + 1.65, sill + 1.83, 0, 0.06);
      F.box('metal_dark', c - 0.02, c + 0.02, sill, sill + 1.65, 0.03, 0.05, { cast: false });
      F.box('metal_dark', c - 0.55, c + 0.55, sill + 0.8, sill + 0.84, 0.03, 0.05, { cast: false });
    }
  }
}

/**
 * One storefront between u0 and u1 on a street face. def:
 *   name, sub      sign text            style 'neon' | 'box' | 'painted' | 'awning'
 *   fg, bg, glow   sign colours         lit      bright interior (a glowing window group)
 *   gate           roll gate down       door     0…1 where the door sits along the front
 *   awning         fabric colour        bulk     bulkhead material
 *   light          colour of the interior light
 */
function storefront(kit, F, u0, u1, y0, base, def) {
  const { mats } = kit;
  const top = GROUND_FLOOR;
  const a = u0 + 0.32;
  const b = u1 - 0.32;
  const head = 2.84;
  const sill = 0.78;
  const mid = (a + b) / 2;

  // Piers, the belt course under the upper storeys, the sign band.
  F.box(base, u0, a, y0, top, 0, 0.1);
  F.box(base, b, u1, y0, top, 0, 0.1);
  F.box('concrete', u0, u1, top - 0.14, top + 0.04, 0, 0.18);
  F.box(def.band || 'paint_black', a, b, head + 0.08, top - 0.14, 0, 0.13);
  const signW = Math.min(b - a - 0.5, def.signW || 7.5);
  const sign = mats.sign({ text: def.name, sub: def.sub, w: signW, h: def.sub ? 0.74 : 0.62, style: def.style || 'box', fg: def.fg, bg: def.bg, glow: def.glow, lit: def.signLit !== false });
  F.overlay(sign, mid, (head + 0.08 + top - 0.14) / 2, 0.15);
  if (def.signLit !== false) F.lamp(mid, 3.25, 0.7, 'neon', def.glow || def.fg || 0xfff1d0, def.style === 'neon' ? 12 : 9, 9);

  if (def.gate) {
    // Closed for the night: ribbed steel from the sidewalk to the head, its roller in a box above.
    F.box('roll_gate', a, b, y0, head, 0.05, 0.11);
    F.box('metal_dark', a, b, head, head + 0.08, 0, 0.2);
    F.box('metal_dark', a - 0.04, a + 0.06, y0, head, 0.05, 0.16);
    F.box('metal_dark', b - 0.06, b + 0.04, y0, head, 0.05, 0.16);
  } else {
    const glass = def.lit ? (def.light === COOL ? 'glass_lit_cool' : 'glass_lit_warm') : 'glass_store';
    const doorW = 1.25;
    const door0 = a + 0.2 + (b - a - 0.4 - doorW) * (def.door ?? 0.5);
    const door1 = door0 + doorW;
    // Display windows on both sides of the door, split into panes of at most 1.9 m.
    for (const [w0, w1] of [[a, door0], [door1, b]]) {
      if (w1 - w0 < 0.3) continue;
      const panes = Math.max(1, Math.ceil((w1 - w0) / 1.9));
      F.box(def.bulk || 'metal_dark', w0, w1, y0, sill, 0, 0.08);
      F.quad(glass, w0, w1, sill, head, 0.035, { cast: false });
      for (let i = 1; i < panes; i++) {
        const u = w0 + ((w1 - w0) * i) / panes;
        F.box('metal_dark', u - 0.03, u + 0.03, sill, head, 0, 0.09);
      }
    }
    F.box('metal_dark', a, b, sill - 0.05, sill, 0, 0.12);
    F.box('metal_dark', a, b, head, head + 0.08, 0, 0.12);
    // The door: set back in a shallow recess, glazed, with a kick plate and a push bar.
    const back = -0.36;
    F.box(base, door0 - 0.05, door0, y0, head, back, 0.08);
    F.box(base, door1, door1 + 0.05, y0, head, back, 0.08);
    F.box('concrete', door0, door1, y0, y0 + 0.02, back, 0, { cast: false });
    F.box('metal_dark', door0, door1, head - 0.42, head, back, back + 0.06);
    F.quad(def.lit ? glass : 'glass_dark', door0 + 0.08, door1 - 0.08, y0 + 0.3, head - 0.44, back + 0.03, { cast: false });
    F.box('metal_dark', door0, door1, y0, y0 + 0.3, back, back + 0.05);
    F.box('metal_dark', door0, door0 + 0.08, y0, head, back, back + 0.06);
    F.box('metal_dark', door1 - 0.08, door1, y0, head, back, back + 0.06);
    F.box('chrome', door0 + 0.14, door1 - 0.14, y0 + 1.02, y0 + 1.07, back + 0.06, back + 0.1, { cast: false });
    if (def.lit) F.lamp(mid, 1.9, 1.5, 'window', def.light || WARM, 10, 9);
  }

  if (def.awning !== undefined) {
    const cloth = ['fabric_awning', { color: def.awning }];
    F.prism(cloth, [[0.12, 3.0], [1.35, 2.52], [1.35, 2.3], [0.12, 2.9]], a + 0.05, b - 0.05);
    for (const u of [a + 0.08, b - 0.08]) F.box('metal_dark', u - 0.015, u + 0.015, 2.29, 2.33, 0.1, 1.33, { cast: false });
  }
}

/** Parapet with coping around a roof, and the roof itself. */
function roof(kit, x0, x1, z0, z1, h, base) {
  kit.flat('concrete_dark', x0, x1, z0, z1, h);
  const t = 0.3;
  for (const [a0, a1, b0, b1] of [[x0, x1, z0, z0 + t], [x0, x1, z1 - t, z1], [x0, x0 + t, z0 + t, z1 - t], [x1 - t, x1, z0 + t, z1 - t]]) {
    kit.box(base, a0, a1, h, h + PARAPET, b0, b1, { noBottom: true });
    kit.box('concrete', a0 - 0.04, a1 + 0.04, h + PARAPET, h + PARAPET + 0.07, b0 - 0.04, b1 + 0.04);
  }
}

/** Projecting cornice with dentils along the top of a street face. */
function cornice(kit, F, u0, u1, h) {
  F.box('concrete', u0, u1, h + 0.05, h + 0.38, 0, 0.42);
  F.box('concrete', u0, u1, h - 0.18, h + 0.05, 0, 0.24);
  for (let u = u0 + 0.3; u < u1 - 0.2; u += 0.62) F.box('concrete', u - 0.11, u + 0.11, h - 0.42, h - 0.18, 0, 0.2);
}

/** A stack of fire-escape balconies up a face, one per storey above the shops. */
function fireEscape(kit, F, u, floors) {
  for (let f = 1; f < floors; f++) F.mount('fire_escape', u, GROUND_FLOOR + (f - 1) * FLOOR + 0.25, 1.1);
}

/** A steel service door with a caged lamp over it. */
function serviceDoor(kit, F, u, y0, lampColor = WARM) {
  F.box('concrete', u - 0.62, u + 0.62, y0, y0 + 2.2, 0, 0.05);
  F.box('metal_dark', u - 0.5, u + 0.5, y0, y0 + 2.1, 0.02, 0.09);
  F.box('chrome', u + 0.3, u + 0.36, y0 + 1, y0 + 1.12, 0.09, 0.14, { cast: false });
  F.box('metal_dark', u - 0.12, u + 0.12, y0 + 2.42, y0 + 2.5, 0, 0.22);
  F.box(kit.glow(lampColor, 4), u - 0.08, u + 0.08, y0 + 2.3, y0 + 2.42, 0.08, 0.2, { cast: false, receive: false });
  F.lamp(u, y0 + 2.3, 0.4, 'street', lampColor, 14, 8, { priority: 3 });
}

export function buildBuildings(kit) {
  const { rng, mats } = kit;
  const text = kit.G.config.text.world;
  const [DELI, BARBER, PAWN, RECORDS, CHICKEN, LIQUOR, NAILS, LAUNDRY, CHECKS, PIZZA] = text.storefronts;

  // Colliders: every building is solid from the ground to the top of its parapet.
  for (const b of Object.values(BUILDINGS)) {
    const h = buildingHeight(b) + PARAPET;
    for (const [x0, x1, z0, z1] of b.boxes) kit.solid(x0, x1, 0, h, z0, z1, { surface: 'brick', tag: b.name });
  }

  /** Plain brick over a whole face (ground storey of side walls, party walls). */
  const brick = (F, base, u0, u1, y0, y1) => F.quad(base, u0, u1, y0, y1, 0);

  // ---------------------------------------------------------------------------------------------
  // N1: the tenement. Laundromat, the residents' door, the barber; four storeys of windows above.
  // ---------------------------------------------------------------------------------------------
  {
    const b = BUILDINGS.n1;
    const h = buildingHeight(b);
    const F = wallFrame(kit, '+z', b.z1);
    storefront(kit, F, -46, -37.2, KERB, b.base, { name: LAUNDRY, style: 'box', bg: 0x0d3550, fg: 0xf4f2ec, glow: COOL, lit: true, light: COOL, door: 0.8, bulk: 'tile_white', band: 'metal_dark' });
    // The residents' entrance: a stoop of two steps, a panelled door, a transom light.
    F.box(b.base, -37.2, -34.4, KERB, GROUND_FLOOR, 0, 0.1);
    F.box('concrete', -36.7, -34.9, KERB, KERB + 0.16, 0.1, 0.75);
    F.box('concrete', -36.5, -35.1, KERB + 0.16, KERB + 0.32, 0.1, 0.45);
    F.box('wood', -36.3, -35.3, KERB + 0.32, 2.5, 0.1, 0.16);
    F.quad('glass_lit_warm', -36.3, -35.3, 2.55, 3.0, 0.13, { cast: false });
    F.box('concrete', -36.5, -35.1, 3.0, 3.2, 0.1, 0.3);
    F.lamp(-35.8, 2.8, 0.5, 'window', WARM, 6, 6);
    storefront(kit, F, -34.4, -26.2, KERB, b.base, { name: BARBER, style: 'neon', fg: 0xff3030, glow: 0xff3030, door: 0.15, bulk: 'tile_white', awning: 0x1c2f5a });
    // Barber pole beside the door.
    const [px, pz] = F.at(-34.05, 0.22);
    kit.cyl(kit.glow(0xf4f2ec, 2.2), px, 1.55, 2.25, pz, 0.075, 8, { cast: false, receive: false });
    for (const y of [1.47, 2.25]) kit.cyl('chrome', px, y, y + 0.08, pz, 0.09, 8, { cast: false });
    facade(kit, F, -46, -26.2, GROUND_FLOOR, h, { floors: b.floors, yBase: GROUND_FLOOR - FLOOR, base: b.base, bays: 6, seed: 11, lit: 0.26 });
    cornice(kit, F, -46, -26.2, h);
    fireEscape(kit, F, -30.6, b.floors);
    // The gangway beside it: bare brick both ways, a service door at the back.
    const G1 = wallFrame(kit, '+x', -26.2);
    brick(G1, b.base, -16, -11, 0, h);
    const G2 = wallFrame(kit, '+z', -16);
    brick(G2, b.base, -26.2, -24, 0, h);
    serviceDoor(kit, G2, -25.1, 0);
    // East wall above the shop roof: a blind party wall with the body shop's painted advert.
    const E = wallFrame(kit, '+x', -24);
    brick(E, b.base, -34, -16, SHOP.eave, h);
    const ad = mats.sign({ text: text.shop, sub: 'COLLISION  ·  FRAME  ·  PAINT', w: 12, h: 3.2, style: 'painted', fg: 0xe9e2cf, bg: 0x1d2f3f, lit: false });
    E.overlay(ad, -24.5, 11.4, 0.03);
    roof(kit, b.x0, -26.2, b.z0, b.z1, h, b.base);
    kit.flat('concrete_dark', -26.2, -24, b.z0, -16, h);
    kit.place('water_tower', -40, -24, 0, { y: h, collide: false });
    kit.place('ac_unit', -31, -15, 0.3, { y: h, collide: false });
    kit.place('ac_unit', -33.5, -27, 1.2, { y: h, collide: false });
    kit.block(b.base, -37, -34, h, h + 2.6, -20, -16.5, { tag: 'bulkhead', noNav: true });
  }

  // ---------------------------------------------------------------------------------------------
  // N2: the deli, with the alley on one side and the cut to the cage on the other.
  // ---------------------------------------------------------------------------------------------
  {
    const b = BUILDINGS.n2;
    const h = buildingHeight(b);
    const F = wallFrame(kit, '+z', b.z1);
    storefront(kit, F, 11, 22, KERB, b.base, { name: DELI, sub: 'OPEN 24 HRS  ·  COLD CUTS  ·  COFFEE  ·  LOTTO', style: 'box', bg: 0xf2c21a, fg: 0x8a1410, glow: 0xffd24a, lit: true, door: 0.5, awning: 0x1f5a3a, signW: 8.4 });
    facade(kit, F, 11, 22, GROUND_FLOOR, h, { floors: b.floors, yBase: GROUND_FLOOR - FLOOR, base: b.base, bays: 4, seed: 23, lit: 0.3 });
    cornice(kit, F, 11, 22, h);
    const W = wallFrame(kit, '-x', b.x0); // the alley side
    facade(kit, W, -31.4, -11, 0, h, { floors: b.floors, floorH: h / b.floors, base: b.base, bays: 5, seed: 24, lit: 0.16 });
    fireEscape(kit, W, -20.5, b.floors);
    serviceDoor(kit, W, -15.5, 0);
    const E = wallFrame(kit, '+x', b.x1); // the cut
    facade(kit, E, -33.5, -11, 0, h, { floors: b.floors, floorH: h / b.floors, base: b.base, bays: 6, seed: 25, lit: 0.12 });
    serviceDoor(kit, E, -27.5, 0, COOL);
    roof(kit, b.x0, b.x1, b.z0, b.z1, h, b.base);
    kit.place('ac_unit', 14, -15, 0, { y: h, collide: false });
    kit.place('ac_unit', 18.5, -22, 1.57, { y: h, collide: false });
    kit.place('water_tower', 16.5, -29, 0, { y: h, collide: false });
  }

  // ---------------------------------------------------------------------------------------------
  // S1: the station house block at the start. Cheque casher and the pizza counter.
  // ---------------------------------------------------------------------------------------------
  {
    const b = BUILDINGS.s1;
    const h = buildingHeight(b);
    const F = wallFrame(kit, '-z', b.z0);
    storefront(kit, F, -46, -38.3, KERB, b.base, { name: CHECKS, sub: 'MONEY ORDERS  ·  BILLS PAID', style: 'neon', fg: 0x55ff8a, glow: 0x55ff8a, door: 0.3, bulk: 'metal_dark' });
    storefront(kit, F, -38.3, -30, KERB, b.base, { name: PIZZA, sub: 'SLICES ALL NIGHT', style: 'box', bg: 0xb3261e, fg: 0xfff1d0, glow: 0xff5a3a, lit: true, door: 0.75, awning: 0xb3261e, bulk: 'tile_white' });
    facade(kit, F, -46, -30, GROUND_FLOOR, h, { floors: b.floors, yBase: GROUND_FLOOR - FLOOR, base: b.base, bays: 5, seed: 31, lit: 0.3 });
    cornice(kit, F, -46, -30, h);
    fireEscape(kit, F, -42.5, b.floors);
    roof(kit, b.x0, b.x1, b.z0, b.z1, h, b.base);
    kit.place('ac_unit', -41, 15, 0, { y: h, collide: false });
    kit.place('ac_unit', -34, 22, 0.8, { y: h, collide: false });
  }

  // ---------------------------------------------------------------------------------------------
  // S2: pawn shop and record store around a shared gated vestibule. Its east wall carries the mural.
  // ---------------------------------------------------------------------------------------------
  {
    const b = BUILDINGS.s2;
    const h = buildingHeight(b);
    const F = wallFrame(kit, '-z', b.z0);
    storefront(kit, F, -30, -24, KERB, b.base, { name: PAWN, sub: 'WE BUY GOLD  ·  LOANS', style: 'neon', fg: 0xf6c21a, glow: 0xf6c21a, door: 0.9, bulk: 'metal_dark' });
    storefront(kit, F, -21.8, -16, KERB, b.base, { name: RECORDS, style: 'neon', fg: 0x35e0ff, glow: 0x35e0ff, door: 0.1, bulk: 'wood' });
    // The vestibule: display windows down both sides, a gated door at the back, a lamp in the soffit.
    const VW = wallFrame(kit, '+x', -24);
    const VE = wallFrame(kit, '-x', -21.8);
    for (const V of [VW, VE]) {
      V.box('metal_dark', 11, 13.4, KERB, 0.78, 0, 0.06);
      V.quad('glass_store', 11.1, 13.3, 0.78, 2.7, 0.03, { cast: false });
      V.box('metal_dark', 11, 13.4, 2.7, 2.78, 0, 0.08);
    }
    const VB = wallFrame(kit, '-z', 13.4);
    brick(VB, b.base, -24, -21.8, KERB, 2.78);
    VB.box('roll_gate', -23.6, -22.2, KERB, 2.4, 0.03, 0.09);
    kit.box('concrete', -24, -21.8, 2.78, GROUND_FLOOR, 11, 13.4);
    kit.box('concrete', PADS[0].x0, PADS[0].x1, 0, KERB, PADS[0].z0, PADS[0].z1, { noBottom: true });
    kit.solid(PADS[0].x0, PADS[0].x1, 0, KERB, PADS[0].z0, PADS[0].z1, { surface: 'concrete', tag: 'sidewalk' });
    kit.solid(-24, -21.8, 2.78, GROUND_FLOOR, 11, 13.4, { surface: 'concrete', tag: b.name, noNav: true });
    kit.box(kit.glow(WARM, 3), -23.1, -22.7, 2.74, 2.78, 12, 12.4, { cast: false, receive: false });
    kit.lamp(-22.9, 2.6, 12.2, 'window', WARM, 7, 6);
    facade(kit, F, -30, -16, GROUND_FLOOR, h, { floors: b.floors, yBase: GROUND_FLOOR - FLOOR, base: b.base, bays: 5, seed: 41, lit: 0.24 });
    cornice(kit, F, -30, -16, h);
    fireEscape(kit, F, -27, b.floors);
    // West wall above the station house, east wall over the vacant lot and the lane.
    brick(wallFrame(kit, '-x', b.x0), b.base, 11, 34, buildingHeight(BUILDINGS.s1), h);
    const E = wallFrame(kit, '+x', b.x1);
    brick(E, b.base, 11, 31, 0, h);
    brick(E, b.base, 31, 34, buildingHeight(BUILDINGS.garages), h);
    roof(kit, b.x0, b.x1, b.z0, b.z1, h, b.base);
    kit.place('water_tower', -23, 24, 0, { y: h, collide: false });
    kit.place('ac_unit', -27, 16, 0, { y: h, collide: false });
    kit.block(b.base, -21, -18, h, h + 2.6, 27, 30.5, { tag: 'bulkhead', noNav: true });
  }

  // ---------------------------------------------------------------------------------------------
  // S3: chicken, liquor, nails, behind the sidewalk shed. Loading dock and back doors on the lane.
  // ---------------------------------------------------------------------------------------------
  {
    const b = BUILDINGS.s3;
    const h = buildingHeight(b);
    const F = wallFrame(kit, '-z', b.z0);
    storefront(kit, F, -4, 5, KERB, b.base, { name: CHICKEN, sub: 'FRIED  ·  WINGS  ·  BISCUITS', style: 'box', bg: 0xf2c21a, fg: 0xb3261e, glow: 0xffc84a, lit: true, door: 0.25, bulk: 'tile_white' });
    storefront(kit, F, 5, 13.5, KERB, b.base, { name: LIQUOR, style: 'neon', fg: 0xff3030, glow: 0xff3030, door: 0.5, bulk: 'metal_dark' });
    storefront(kit, F, 13.5, 22, KERB, b.base, { name: NAILS, sub: 'MANICURE  ·  PEDICURE', style: 'neon', fg: 0xff3d9a, glow: 0xff3d9a, gate: true });
    facade(kit, F, -4, 22, GROUND_FLOOR, h, { floors: b.floors, yBase: GROUND_FLOOR - FLOOR, base: b.base, bays: 8, seed: 51, lit: 0.34 });
    cornice(kit, F, -4, 22, h);
    const W = wallFrame(kit, '-x', b.x0); // vacant lot side
    facade(kit, W, 11, 26, 0, h, { floors: b.floors, floorH: h / b.floors, base: b.base, bays: 4, seed: 52, lit: 0.2 });
    serviceDoor(kit, W, 22.8, 0);
    const S = wallFrame(kit, '+z', b.z1); // the lane
    facade(kit, S, -4, 22, 0, h, { floors: b.floors, floorH: h / b.floors, base: b.base, bays: 8, seed: 53, lit: 0.18 });
    serviceDoor(kit, S, -1.6, 0);
    serviceDoor(kit, S, 17.4, 0, COOL);
    S.box('roll_gate', 13.2, 15.8, 0, 2.7, 0.02, 0.08); // a delivery shutter
    S.box('metal_dark', 13.1, 15.9, 2.7, 2.9, 0, 0.16);
    const E = wallFrame(kit, '+x', b.x1); // the lot
    facade(kit, E, 11, 26, 0, h, { floors: b.floors, floorH: h / b.floors, base: b.base, bays: 4, seed: 54, lit: 0.2 });
    const park = mats.sign({ text: 'PARK', sub: '24 HR  ·  PAY AT BOOTH', w: 5, h: 1.6, style: 'painted', fg: 0xf4f2ec, bg: 0x1f4f9a, lit: false });
    E.overlay(park, 18.5, 2.3, 0.03);
    roof(kit, b.x0, b.x1, b.z0, b.z1, h, b.base);
    for (const [x, z, yaw] of [[1, 15, 0], [9.5, 22, 1.57], [17, 14.5, 0.4]]) kit.place('ac_unit', x, z, yaw, { y: h, collide: false });
    kit.block(b.base, 11.5, 14.5, h, h + 2.5, 19, 22.5, { tag: 'bulkhead', noNav: true });
  }

  // ---------------------------------------------------------------------------------------------
  // The garages on the south side of the rear lane.
  // ---------------------------------------------------------------------------------------------
  {
    const b = BUILDINGS.garages;
    const h = buildingHeight(b);
    const F = wallFrame(kit, '-z', b.z0);
    const doors = [-13.6, -9.2, -4.8, -0.4, 4, 8.4, 12.8, 17.2];
    brick(F, b.base, b.x0, b.x1, 0, h);
    doors.forEach((u, i) => {
      F.box('roll_gate', u - 1.7, u + 1.7, 0, 2.75, 0.02, 0.09);
      F.box('concrete', u - 1.85, u + 1.85, 2.75, 3.0, 0, 0.12);
      const tag = mats.sign({ text: String(41 + i), w: 0.7, h: 0.42, style: 'stencil', fg: 0xe6e4dc, lit: false });
      F.overlay(tag, u, 3.3, 0.02);
      if (i % 3 === 1) {
        F.box('metal_dark', u + 1.95, u + 2.25, 3.2, 3.3, 0, 0.3);
        F.box(kit.glow(0xffb45e, 4), u + 2.0, u + 2.2, 3.08, 3.2, 0.1, 0.28, { cast: false, receive: false });
        F.lamp(u + 2.1, 3.0, 0.4, 'street', 0xffb45e, 18, 10, { priority: 4 });
      }
    });
    kit.box('concrete', b.x0, b.x1, h, h + 0.3, b.z0 - 0.06, b.z0 + 0.3);
    kit.flat('concrete_dark', b.x0, b.x1, b.z0, b.z1, h);
    // Their gable end closes the lot's south-west corner.
    brick(wallFrame(kit, '+x', b.x1), b.base, b.z0, b.z1, 0, h);
  }

  buildBacks(kit, rng);
  return { shedSigns: [CHICKEN, LIQUOR, NAILS], shed: SHED };
}

/**
 * The backs of the neighbouring buildings just outside the bounds: what the block's north, east and
 * south edges are sealed with wherever no building of its own stands there. Solid, a few storeys of
 * windows, nothing else: the far city behind them is the atmosphere's.
 */
function buildBacks(kit) {
  const { minX, maxX, minZ, maxZ } = BOUNDS;
  const DEPTH = 3; // they only have to be thick enough to hide what is behind them

  /** A slab of building whose `facing` side looks into the block. */
  function back(x0, x1, z0, z1, floors, base, facing, seed, lit, y0 = 0) {
    const h = GROUND_FLOOR + (floors - 1) * FLOOR;
    kit.solid(x0, x1, 0, h + PARAPET, z0, z1, { surface: 'brick', tag: 'backs' });
    const alongX = facing[1] === 'z';
    const plane = facing === '+z' ? z1 : facing === '-z' ? z0 : facing === '+x' ? x1 : x0;
    const F = wallFrame(kit, facing, plane);
    const u0 = alongX ? x0 : z0;
    const u1 = alongX ? x1 : z1;
    facade(kit, F, u0, u1, y0, h, { base, floors, floorH: h / floors, seed, lit });
    F.box('concrete', u0, u1, h + PARAPET - 0.1, h + PARAPET, 0, 0.1);
    F.quad(base, u0, u1, h, h + PARAPET - 0.1, 0);
    // The other three sides are bare brick: seen only at a glancing angle past a corner.
    for (const [side, a0, a1, at] of [['+z', x0, x1, z1], ['-z', x0, x1, z0], ['+x', z0, z1, x1], ['-x', z0, z1, x0]]) {
      if (side !== facing) wallFrame(kit, side, at).quad(base, a0, a1, 0, h + PARAPET, 0);
    }
    kit.flat('concrete_dark', x0, x1, z0, z1, h + PARAPET - 0.02);
    return F;
  }

  // North: behind the shop and across the end of the alley; behind the cut and the cage.
  back(SHOP.minX, SHOP.maxX, minZ - DEPTH, SHOP.minZ, 4, 'brick_brown', '+z', 61, 0.2, SHOP.parapet - 0.4);
  back(SHOP.maxX, 11, minZ - DEPTH, minZ, 4, 'brick_brown', '+z', 62, 0.14);
  back(22, maxX + DEPTH, minZ - DEPTH, minZ + 0.5, 3, 'brick_red', '+z', 63, 0.22);
  // East: beside the cage, then beside the lot.
  back(maxX - 0.2, maxX + DEPTH, minZ + 0.5, -12.2, 3, 'brick_tan', '-x', 64, 0.2);
  back(maxX, maxX + DEPTH, 11, maxZ + DEPTH, 2, 'brick_brown', '-x', 65, 0.16);
  // South: behind the garages and behind the lot.
  back(-16, 22, maxZ, maxZ + DEPTH, 4, 'brick_red', '-z', 66, 0.3, buildingHeight(BUILDINGS.garages));
  back(22, maxX, maxZ, maxZ + DEPTH, 3, 'brick_tan', '-z', 67, 0.2);
}
