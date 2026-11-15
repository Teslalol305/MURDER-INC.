// The avenue itself: the closures at both ends, the start area, the parked and abandoned vehicles that
// make the lanes, the ring of cover around reel 1, street furniture on both sidewalks, and the
// construction sidewalk shed in front of S3 (the vantage).
//
// Lane plan (z):  −11…−7 north sidewalk · −7…−5 parking · −4…0 westbound · 0…4 eastbound · 5…7 parking
//                 · 7…11 south sidewalk. El columns stand at z = ±4.6, between travel and parking lanes.
//
// Sightlines: two curtains of tall things cross the whole avenue, near x = −18 and x = +14. Each is
// staggered (a truck in one travel lane, a van in the other a few metres on; a kiosk at the kerb, a
// cage against the wall further along) so every lane stays walkable as a chicane while no straight
// line at eye height runs much past 45 m.

import * as THREE from 'three';
import { BOUNDS, FRONT_Z, KERB, ROAD_Z, SHED, STATION } from './layout.js';
import { wallFrame } from './buildings.js';
import { chainlink, hoarding } from './fences.js';

const NORTH = -5.98; // centre line of the parking lanes
const SOUTH = 5.98;
const WEST = Math.PI; // yaw of a car whose nose points west
const HOARDING_GREEN = 0x23463c;
const WARM = 0xffc98a;

export function buildStreet(kit) {
  const { mats, rng } = kit;
  const text = kit.G.config.text.world;
  const steam = [];

  buildWestClosure(kit, mats);
  buildRoadblock(kit, mats);
  const vantage = buildShed(kit, mats, text);
  buildSidewalkBlockers(kit, mats, steam);

  // ---------------------------------------------------------------------------------------------
  // Parked at the kerbs. Gaps every few car lengths are the crossings between the lanes.
  // ---------------------------------------------------------------------------------------------

  kit.place('van', -38.2, NORTH, WEST, { color: 0x3d4f66 });
  kit.place('sedan', -27.4, NORTH, WEST, { seed: 1 });
  kit.place('van', -20.2, NORTH, WEST, { color: 0xd8d6cf });
  kit.place('motorbike', -5.7, -6.35, 0.08);
  kit.place('taxi', 4, NORTH, WEST);
  kit.place('sedan', 13.6, NORTH, WEST, { seed: 4 });
  kit.place('van', 19.4, NORTH, WEST, { color: 0x8a8f96 });
  kit.place('sedan', 31.4, NORTH, WEST, { seed: 3 });

  kit.place('suv', -34.3, SOUTH, 0, { color: 0x0b0c0e }); // Rule's ride
  kit.place('taxi', -24.6, SOUTH, 0);
  kit.place('van', -18.9, SOUTH, 0, { color: 0x6a7480 });
  kit.place('van', -3, SOUTH, 0, { color: 0x1c2029 });
  kit.place('sedan', 4.6, SOUTH, 0, { seed: 6 });
  kit.place('van', 13.4, SOUTH, 0, { color: 0x7a1d1d });
  kit.place('sedan', 39.6, SOUTH, 0, { seed: 0 });

  // ---------------------------------------------------------------------------------------------
  // In the travel lanes, west to east.
  // ---------------------------------------------------------------------------------------------

  // The El repair crew's rolling scaffold stands across the eastbound lane near the closure; a sedan was
  // left askew in the westbound one. Then the first curtain's truck: a rental box truck stopped dead.
  rollingScaffold(kit, -30.2, -28.6, -0.3, 4.7);
  kit.place('sedan', -35.2, -2.3, 0.42, { seed: 4 });
  kit.place('box_truck', -19.2, -2.4, -0.28, { color: 0xd9b23a });
  kit.place('traffic_barrel', -13.6, -2.9);
  kit.place('traffic_barrel', -12.9, -2.1);
  kit.place('motorbike', -14.6, 3.6, 0.5);
  kit.place('trash_bags', -25.4, 1.6, 0.7);
  kit.place('barricade', -11.9, -3.6, 0.25);

  // The arena around reel 1 at (−4, 1). The Vultures' van stands slewed across the eastbound lane, its
  // back doors open three metres from the case; low cover closes the ring, and a second rolling scaffold
  // walls off the westbound lane behind it.
  kit.place('van', -9.4, 1.8, Math.PI + 0.55, { variant: 'vulture', color: 0x16181b, open: true });
  rollingScaffold(kit, -1.9, -0.3, -4.7, 0.4);
  kit.place('jersey_barrier', -1.1, 3.1, 0.08);
  kit.place('jersey_barrier', 1, -1.9, Math.PI / 2 + 0.1);
  kit.place('sandbags', -4.3, -2.9, 0.1);
  kit.place('trash_bags', -6.2, 4.3, 0.5);
  kit.place('milk_crates', 0.1, 1.2);
  kit.place('tire_stack', -7.6, -2.5);
  kit.place('crate_wood', -2.4, 4.25, 0.3);
  kit.overlay(mats.graffiti('VULTURES', 21, 0x8a1a22), '+y', -3.4, 0.03, -0.7, { w: 3.4, h: 1, yaw: -0.3 });

  // The second curtain: a box truck double-parked in the eastbound lane, a van in the westbound one.
  kit.place('box_truck', 5.85, 2.35, 0.28, { color: 0xb9b4a6 });
  kit.place('van', 16.3, -2.6, 0.55, { color: 0x24352c });
  kit.place('jersey_barrier', 10.6, -2.3, 0.05);
  kit.place('traffic_barrel', 9.9, -0.5);
  kit.place('traffic_barrel', 12.6, -0.3);
  kit.place('trash_bags', 6.2, -3.3, 1.1);
  kit.place('barricade', 2.9, -3.8, -0.2);
  kit.place('sandbags', 20.4, 2, Math.PI / 2);
  kit.place('tire_stack', 15.2, 2.6);

  // Between the crossing and the roadblock.
  kit.place('jersey_barrier', 27.6, 2.6, Math.PI / 2);
  kit.place('jersey_barrier', 28.4, -2.9, Math.PI / 2 + 0.2);
  kit.place('traffic_barrel', 30.2, 0.4);
  kit.place('traffic_barrel', 31, -0.3);
  kit.place('traffic_barrel', 30.4, -1.2);
  kit.place('sedan', 33.8, 2.3, 0.3, { seed: 1 });
  kit.place('van', 36.9, -2.5, Math.PI + 0.1, { color: 0x4a4e55 });

  // ---------------------------------------------------------------------------------------------
  // North sidewalk furniture
  // ---------------------------------------------------------------------------------------------

  kit.place('phone_booth', -44.5, -10.25, 0);
  kit.place('trash_can', -42.2, -10.4);
  kit.place('mailbox', -32, -7.7, 0);
  kit.place('newspaper_box', -31.2, -7.62, 0);
  kit.place('street_lamp', -22.4, -7.62, Math.PI);
  kit.place('tire_stack', -17.3, -10.4);
  kit.place('oil_drum', -16.8, -9.6);
  kit.place('food_cart', -5.7, -8.3, 0);
  kit.place('vending_machine', 3.5, -10.55, 0);
  kit.place('newspaper_box', 1.7, -7.62, 0);
  kit.place('street_lamp', 2.6, -7.62, Math.PI);
  kit.place('mailbox', 9.6, -7.7, 0);
  kit.place('street_lamp', 23.9, -7.62, Math.PI);
  kit.place('newspaper_box', 26.2, -7.62, 0);
  kit.place('bus_shelter', 29.2, -8.05, 0);
  kit.place('bench', 30.4, -11.55, 0);
  kit.place('planter', 32.1, -11.4);
  kit.place('planter', 36.9, -11.4);
  kit.place('hydrant', 37.4, -7.5);
  kit.place('tree', 39.8, -8.3);
  kit.place('street_lamp', 41.6, -7.62, Math.PI);
  for (const x of [-34.2, -24.6, 9.2, 33.6]) kit.place('parking_meter', x, -7.42);

  // ---------------------------------------------------------------------------------------------
  // South sidewalk furniture
  // ---------------------------------------------------------------------------------------------

  kit.place('trash_bags', -41.2, 10.3, 0.2);
  kit.place('newspaper_box', -40.1, 10.5, Math.PI);
  kit.place('trash_can', -36.4, 7.68);
  kit.place('bench', -33.6, 10.5, Math.PI);
  kit.place('street_lamp', -31.4, 7.62, 0);
  kit.place('phone_booth', -29.2, 10.25, Math.PI);
  kit.place('bench', -27.1, 10.5, Math.PI);
  kit.place('trash_can', -22.7, 7.68);
  for (const x of [-21.7, -21.1]) kit.place('newspaper_box', x, 7.62, Math.PI);
  kit.place('milk_crates', -19.7, 10.5);
  kit.place('milk_crates', -18.9, 10.45);
  kit.place('hydrant_open', -12.25, 7.34, Math.PI); // on the gateway's apron, hosing the avenue down
  kit.place('trash_bags', -13.6, 10.3, 0.9);
  kit.place('street_lamp', 22.9, 7.62, 0);
  kit.place('tree', 25.4, 8.3);
  kit.place('newspaper_box', 26.9, 7.62, Math.PI);
  kit.place('phone_booth', 27.3, 10.25, Math.PI);
  kit.place('street_lamp', 36.4, 7.62, 0);
  kit.place('hydrant', 38.2, 7.5);
  kit.place('planter', 39.6, 10.25);
  kit.place('trash_can', 41.4, 7.68);
  kit.place('tree', 43.2, 8.3);
  for (const x of [-26.6, 1.6, 7.6, 39.9]) kit.place('parking_meter', x, 7.42);

  // Scattered cones: nothing to hide behind, plenty to kick over.
  for (const [x, z] of [[-42.1, -3.9], [-42.4, 0.4], [-41.9, 4.3], [-13.9, -0.6], [-24.2, 0.9], [11.9, -0.9], [13.4, 1], [29.4, 1.6], [39.2, 4.2], [38.6, -6.2]]) {
    kit.place('traffic_cone', x, z, rng.range(0, 6));
  }
  return { vantage, steam };
}

/**
 * The El repair crew's rolling scaffold: two wheeled towers bridged by a work platform under the
 * girders, wrapped in debris netting. It stands across one travel lane (long in z) and is solid.
 */
function rollingScaffold(kit, x0, x1, z0, z1) {
  const deck = 3.7;
  const net = ['fabric', { color: 0xb8521a, doubleSide: true }];
  kit.solid(x0, x1, 0, deck + 0.1, z0, z1, { surface: 'metal', tag: 'scaffold' });
  const xs = [x0 + 0.05, x1 - 0.05];
  const zs = [z0 + 0.05, z0 + 1.5, z1 - 1.5, z1 - 0.05];
  for (const x of xs) {
    for (const z of zs) {
      kit.cyl('metal_galv', x, 0.18, deck + 1.05, z, 0.035, 6);
      kit.cyl('rubber', x, 0, 0.2, z, 0.1, 8, { cast: false }); // castor
    }
    for (const y of [0.45, 2.1, deck - 0.12, deck + 1.0]) kit.pipe('metal_galv', [x, y, z0 + 0.05], [x, y, z1 - 0.05], 0.028, 5, { cast: false });
    // Netting on the faces the street sees, a diagonal brace showing through at each tower.
    kit.quad(net, x === xs[0] ? '-x' : '+x', x, 2.1, (z0 + z1) / 2, z1 - z0 - 0.1, 3.3);
    kit.pipe('metal_galv', [x, 0.5, zs[0]], [x, 2.05, zs[1]], 0.022, 5, { cast: false });
    kit.pipe('metal_galv', [x, 0.5, zs[3]], [x, 2.05, zs[2]], 0.022, 5, { cast: false });
  }
  for (const z of zs) {
    for (const y of [0.45, 2.1, deck - 0.12]) kit.pipe('metal_galv', [xs[0], y, z], [xs[1], y, z], 0.028, 5, { cast: false });
  }
  kit.box('plywood', x0, x1, deck - 0.08, deck, z0, z1);
  kit.box('wood', x0, x1, deck, deck + 0.16, z0, z0 + 0.03, { cast: false }); // toe boards
  kit.box('wood', x0, x1, deck, deck + 0.16, z1 - 0.03, z1, { cast: false });
  const tag = kit.mats.sign({ text: 'EL REPAIRS', sub: 'KEEP CLEAR', w: 1.3, h: 0.5, style: 'box', bg: 0xe8641b, fg: 0x101113, lit: false });
  kit.overlay(tag, '-x', x0 - 0.02, 1.5, (z0 + z1) / 2);
  kit.overlay(tag, '+x', x1 + 0.02, 1.5, (z0 + z1) / 2);
}

// -------------------------------------------------------------------------------------------------
// Tall things on the sidewalks. Each curtain has a piece at the kerb and a piece against the wall a few
// metres apart, their depths overlapping, so the sidewalk stays a walkable zigzag but not a firing lane.
// -------------------------------------------------------------------------------------------------

/** A shut kiosk: sheet-steel box with a roll shutter on its `front` side and an overhanging roof. */
function kiosk(kit, x0, x1, z0, z1, front, label, y0 = KERB) {
  const { mats } = kit;
  const body = ['corrugated', { color: 0x24463a }];
  const top = y0 + 2.5;
  kit.block(body, x0, x1, y0, top, z0, z1, { tag: 'kiosk' });
  kit.box('metal_dark', x0 - 0.25, x1 + 0.25, top, top + 0.1, z0 - 0.25, z1 + 0.25);
  const alongX = front[1] === 'z';
  const F = wallFrame(kit, front, front === '+z' ? z1 : front === '-z' ? z0 : front === '+x' ? x1 : x0);
  const u0 = alongX ? x0 : z0;
  const u1 = alongX ? x1 : z1;
  F.box('roll_gate', u0 + 0.15, u1 - 0.15, y0 + 0.8, y0 + 2.05, 0, 0.05);
  F.box('metal_dark', u0 + 0.1, u1 - 0.1, y0 + 0.7, y0 + 0.8, 0, 0.16);
  F.overlay(mats.sign({ text: label, w: Math.min(2.4, u1 - u0 - 0.3), h: 0.26, style: 'painted', fg: 0xf4f2ec, bg: 0x24463a, lit: false }), (u0 + u1) / 2, y0 + 2.27, 0.012);
  F.overlay(mats.poster('show', 2), u0 + 0.5, y0 + 0.42);
  F.overlay(mats.poster('torn', 1), u1 - 0.55, y0 + 0.4);
  return F;
}

function buildSidewalkBlockers(kit, mats, steam) {
  // ---- north side, first curtain: a newsstand at the kerb, the tyre cage against the shop wall ----
  kiosk(kit, -30.2, -27.2, -9.5, -7.04, '-z', 'NEWS  ·  MAGAZINES  ·  LOTTO');
  {
    const c = { x0: -20.4, x1: -18, z0: -10.96, z1: -8.6, top: KERB + 2.25 };
    kit.solid(c.x0, c.x1, KERB, c.top, c.z0, c.z1, { surface: 'rubber', tag: 'tyre-cage' });
    for (const x of [c.x0 + 0.04, c.x1 - 0.04]) {
      for (const z of [c.z0 + 0.04, c.z1 - 0.04]) kit.box('metal_dark', x - 0.04, x + 0.04, KERB, c.top, z - 0.04, z + 0.04);
    }
    chainlink(kit, c.x0, c.z1, c.x1, c.z1, KERB + 0.05, c.top - 0.05, { spacing: 1.2 });
    chainlink(kit, c.x0, c.z0, c.x0, c.z1, KERB + 0.05, c.top - 0.05, { spacing: 1.2 });
    chainlink(kit, c.x1, c.z0, c.x1, c.z1, KERB + 0.05, c.top - 0.05, { spacing: 1.2 });
    kit.box(['corrugated', { color: 0x1c2224 }], c.x0 - 0.12, c.x1 + 0.12, c.top, c.top + 0.05, c.z0, c.z1 + 0.15);
    // Stacks of used tyres fill it to the roof.
    for (let i = 0; i < 3; i++) {
      for (let j = 0; j < 3; j++) {
        const x = c.x0 + 0.42 + i * 0.78;
        const z = c.z0 + 0.42 + j * 0.76;
        const h = 1.55 + ((i * 3 + j * 5) % 4) * 0.2;
        kit.cyl('tire', x, KERB, KERB + h, z, 0.34, 10, { cast: false });
        kit.cyl('rubber', x, KERB + h - 0.02, KERB + h + 0.004, z, 0.19, 10, { cast: false });
      }
    }
    const price = mats.sign({ text: 'USED TIRES', sub: 'ALL SIZES  ·  MOUNTED FREE', w: 2, h: 0.5, style: 'stencil', fg: 0xf2c21a, lit: false });
    kit.overlay(price, '+z', (c.x0 + c.x1) / 2, c.top + 0.36, c.z1 + 0.1);
    kit.box('metal_dark', c.x0, c.x1, c.top + 0.08, c.top + 0.64, c.z1 + 0.04, c.z1 + 0.09);
  }

  // ---- north side, second curtain: the deli's produce stand at the wall, a utility dig at the kerb ----
  {
    const s = { x0: 11.4, x1: 15.2, z0: -10.98, z1: -8.6 };
    const top = KERB + 2.35;
    kit.solid(s.x0, s.x1, KERB, top, s.z0, s.z1, { surface: 'wood', tag: 'produce-stand' });
    for (const x of [s.x0, s.x1 - 0.06]) kit.box(['plywood', { color: 0x2d5a3a }], x, x + 0.06, KERB, top, s.z0, s.z1);
    for (const x of [s.x0 + 0.05, s.x1 - 0.05]) kit.box('wood', x - 0.05, x + 0.05, KERB, top - 0.1, s.z1 - 0.1, s.z1);
    // Canopy sloping to the street, bare bulbs under it, three tiers of crates.
    kit.prism(['fabric_awning', { color: 0x1f5a3a }], [[s.z0, top + 0.5], [s.z1 + 0.25, top - 0.1], [s.z1 + 0.25, top - 0.2], [s.z0, top + 0.42]], 'x', s.x0 - 0.1, s.x1 + 0.1);
    const tiers = [[s.z1 - 0.75, s.z1 - 0.05, 0.5], [s.z1 - 1.5, s.z1 - 0.75, 0.82], [s.z0 + 0.1, s.z1 - 1.5, 1.14]];
    for (const [z0, z1, h] of tiers) kit.box('wood', s.x0 + 0.1, s.x1 - 0.1, KERB, KERB + h, z0, z1);
    const fruit = [0xd9601a, 0xb3261e, 0xd9b23a, 0x3f7a2e, 0xd9601a, 0x8a2a5a];
    tiers.forEach(([z0, z1, h], row) => {
      for (let i = 0; i < 5; i++) {
        const x = s.x0 + 0.5 + i * 0.7;
        // A slatted crate with a rounded heap of fruit in it.
        const c0 = z0 + 0.1;
        const c1 = Math.min(z1 - 0.06, z0 + 0.62);
        const y = KERB + h;
        const mid = (c0 + c1) / 2;
        kit.box('wood', x - 0.28, x + 0.28, y, y + 0.1, c0, c1, { cast: false });
        const heap = [[c0 + 0.03, y + 0.08], [c1 - 0.03, y + 0.08], [c1 - 0.08, y + 0.17], [mid + 0.1, y + 0.22], [mid - 0.1, y + 0.22], [c0 + 0.08, y + 0.17]];
        kit.prism(['plastic_orange', { color: fruit[(i + row * 2) % fruit.length] }], heap, 'x', x - 0.25, x + 0.25, { cast: false });
      }
    });
    const bulb = kit.glow(WARM, 4);
    for (const x of [s.x0 + 0.9, s.x1 - 0.9]) {
      kit.box(bulb, x - 0.05, x + 0.05, top - 0.02, top + 0.08, -9.3, -9.2, { cast: false, receive: false });
    }
    kit.lamp((s.x0 + s.x1) / 2, top - 0.1, -9.2, 'window', WARM, 12, 8, { priority: 3 });
  }
  {
    // The dig: an orange plywood pen around an open vault, a striped stack venting steam over it.
    const d = { x0: 17.8, x1: 21.2, z0: -9.2, z1: -7.04 };
    const orange = 0xc4571a;
    const top = KERB + 2.2;
    const south = hoarding(kit, d.x0, d.x1, d.z1, KERB, top, orange, '+z');
    const north = hoarding(kit, d.x0, d.x1, d.z0, KERB, top, orange, '-z');
    hoarding(kit, d.z0, d.z1, d.x0, KERB, top, orange, '-x');
    hoarding(kit, d.z0, d.z1, d.x1, KERB, top, orange, '+x');
    kit.solid(d.x0, d.x1, KERB, top, d.z0, d.z1, { surface: 'wood', tag: 'dig' });
    const danger = mats.sign({ text: 'DANGER', sub: 'STEAM  ·  KEEP OUT', w: 1.5, h: 0.6, style: 'box', bg: 0xf4f2ec, fg: 0xb3261e, lit: false });
    south.overlay(danger, d.x0 + 1.1, KERB + 1.5, 0.012);
    north.overlay(danger, d.x1 - 1.1, KERB + 1.5, 0.012);
    north.overlay(mats.graffiti('188', 2), d.x0 + 1.1, KERB + 0.9, 0.012);
    const sx = 19.5;
    const sz = -8.1;
    for (let i = 0; i < 9; i++) {
      kit.cyl(i % 2 ? 'paint_white' : 'plastic_orange', sx, KERB + i * 0.4, KERB + (i + 1) * 0.4, sz, 0.21, 10, { open: true });
    }
    kit.solid(sx - 0.2, sx + 0.2, top, KERB + 3.6, sz - 0.2, sz + 0.2, { surface: 'metal', tag: 'dig', noNav: true });
    steam.push(new THREE.Vector3(sx, KERB + 3.7, sz));
  }

  // ---- south side, first curtain: the site shanty against the wall, two portable toilets at the kerb ----
  {
    const s = { x0: -17.4, x1: -14.6, z0: 8.6, z1: 10.98 };
    const top = KERB + 2.7;
    kit.block(['plywood', { color: HOARDING_GREEN }], s.x0, s.x1, KERB, top, s.z0, s.z1, { tag: 'shanty' });
    kit.prism(['corrugated', { color: 0x1c2224 }], [[s.z0 - 0.2, top + 0.02], [s.z1, top + 0.3], [s.z1, top + 0.36], [s.z0 - 0.2, top + 0.08]], 'x', s.x0 - 0.15, s.x1 + 0.15);
    const F = wallFrame(kit, '-z', s.z0);
    F.box('wood', -16.5, -15.5, KERB, KERB + 2.05, 0, 0.04); // the door, chained shut
    F.box('chrome', -15.72, -15.62, KERB + 1, KERB + 1.14, 0.04, 0.08, { cast: false });
    F.overlay(mats.sign({ text: 'POST NO BILLS', w: 1.5, h: 0.24, style: 'stencil', fg: 0xe6e4dc, lit: false }), -16, KERB + 2.4, 0.012);
    const west = wallFrame(kit, '-x', s.x0);
    west.overlay(mats.poster('show', 0), 9.3, KERB + 1.5);
    west.overlay(mats.poster('ad', 1), 10.05, KERB + 1.45);
    west.overlay(mats.graffiti('KOQ', 4, 0x35e0ff), 9.8, KERB + 0.7, 0.012);
    F.box('metal_dark', -16.1, -15.9, KERB + 2.5, KERB + 2.58, 0, 0.22);
    F.box(kit.glow(0xfff1d0, 3.5), -16.06, -15.94, KERB + 2.4, KERB + 2.5, 0.08, 0.2, { cast: false, receive: false });
    F.lamp(-16, KERB + 2.35, 0.4, 'work', 0xfff1d0, 9, 7, { priority: 3 });
  }
  kit.place('porta_potty', -6.8, 7.66, Math.PI / 2);
  kit.place('porta_potty', -6.8, 8.86, Math.PI / 2);

  // ---- south side, second curtain: the hoist tower at the east end of the shed closes the sidewalk;
  // a row of barriers makes a walkway round it in the parking lane ----
  {
    const t = { x0: 19.06, x1: 22, z0: ROAD_Z + 0.04, z1: FRONT_Z - 0.03 };
    const base = KERB + 2.6;
    const top = 9.4;
    kit.block(['plywood', { color: HOARDING_GREEN }], t.x0, t.x1, KERB, base, t.z0, t.z1, { tag: 'hoist' });
    // The netting stops climbers, not rounds: you can see (and shoot) the scaffold through it.
    kit.solid(t.x0, t.x1, base, top, t.z0, t.z1, { surface: 'cloth', tag: 'hoist', noNav: true, playerOnly: true });
    // Scaffold standards and ledgers above the hoarding, wrapped in debris netting on the three open sides.
    for (const x of [t.x0 + 0.06, t.x1 - 0.06]) {
      for (const z of [t.z0 + 0.06, t.z1 - 0.06]) kit.cyl('metal_galv', x, base, top + 0.5, z, 0.04, 6);
    }
    for (let y = base + 0.2; y < top + 0.3; y += 1.9) {
      kit.pipe('metal_galv', [t.x0 + 0.06, y, t.z0 + 0.06], [t.x1 - 0.06, y, t.z0 + 0.06], 0.03, 5, { cast: false });
      kit.pipe('metal_galv', [t.x0 + 0.06, y, t.z1 - 0.06], [t.x1 - 0.06, y, t.z1 - 0.06], 0.03, 5, { cast: false });
      for (const x of [t.x0 + 0.06, t.x1 - 0.06]) kit.pipe('metal_galv', [x, y, t.z0 + 0.06], [x, y, t.z1 - 0.06], 0.03, 5, { cast: false });
    }
    const net = ['chainlink', { color: 0x2c5a3a }]; // debris netting: a see-through green weave
    kit.quad(net, '-z', (t.x0 + t.x1) / 2, (base + top) / 2, t.z0 + 0.01, t.x1 - t.x0, top - base);
    kit.quad(net, '-x', t.x0 + 0.01, (base + top) / 2, (t.z0 + t.z1) / 2, t.z1 - t.z0, top - base);
    kit.quad(net, '+x', t.x1 - 0.01, (base + top) / 2, (t.z0 + t.z1) / 2, t.z1 - t.z0, top - base);
    kit.box('wood', t.x0, t.x1, top, top + 0.05, t.z0, t.z1);
    const closed = mats.sign({ text: 'SIDEWALK CLOSED', sub: 'USE WALKWAY', w: 2.2, h: 0.7, style: 'box', bg: 0xe8641b, fg: 0x101113, lit: false });
    wallFrame(kit, '+x', t.x1).overlay(closed, 9, KERB + 1.6, 0.012);
    wallFrame(kit, '-z', t.z0).overlay(closed, (t.x0 + t.x1) / 2, KERB + 1.6, 0.012);
    wallFrame(kit, '+x', t.x1).overlay(mats.poster('ipx', 1), 10.3, KERB + 1.2);
    wallFrame(kit, '-z', t.z0).overlay(mats.graffiti('VLTR', 3, 0x8a1a22), t.x0 + 0.9, KERB + 0.8, 0.012);
  }
  kit.place('jersey_barrier', 18.4, 5.02, 0);
  kit.place('jersey_barrier', 21.5, 5.02, 0);
  kit.place('traffic_barrel', 23.6, 5.1);
  kit.place('traffic_barrel', 16.4, 5.1);
}

// -------------------------------------------------------------------------------------------------
// West end: road works under the station. Hoarding from wall to wall, barriers, a generator.
// -------------------------------------------------------------------------------------------------

function buildWestClosure(kit, mats) {
  const x = BOUNDS.minX + 0.7;
  const stair = STATION.stair;
  let face = null;
  for (const [z0, z1, y0] of [[-FRONT_Z, -ROAD_Z, KERB], [-ROAD_Z, ROAD_Z, 0], [ROAD_Z, FRONT_Z, KERB]]) {
    const F = hoarding(kit, z0, z1, x, y0, 2.7, HOARDING_GREEN, '+x');
    if (y0 === 0) face = F;
  }
  kit.solid(BOUNDS.minX, x, 0, 8, -FRONT_Z, FRONT_Z, { tag: 'seal', playerOnly: true });
  const closed = mats.sign({ text: 'ROAD CLOSED', sub: 'EL STRUCTURE REPAIRS  ·  NO THRU TRAFFIC', w: 3.4, h: 1.05, style: 'box', bg: 0xe8641b, fg: 0x101113, lit: false });
  face.overlay(closed, -2.6, 1.75, 0.012);
  face.overlay(closed, 3.4, 1.75, 0.012);
  face.overlay(mats.graffiti('HOLLIS', 6, 0xf4f2ec), 0.4, 0.9, 0.012);
  face.overlay(mats.poster('show', 1), -5.6, 1.4);
  face.overlay(mats.poster('ipx', 1), -4.9, 1.45);
  face.overlay(mats.poster('torn', 2), 5.8, 1.3);

  // Barriers in front of it, and the contractor's kit in the gap behind them.
  for (const z of [-4.6, -1.55, 1.5, 4.55]) kit.place('jersey_barrier', x + 1.75, z, Math.PI / 2);
  kit.place('traffic_barrel', x + 1.7, -6.45);
  kit.place('traffic_barrel', x + 1.7, 6.4);
  kit.place('generator', x + 0.62, 3.1, Math.PI / 2);
  kit.place('floodlight_stand', x + 0.65, -2.9, -Math.PI / 2);
  kit.place('pallet_stack', x + 0.62, 0.3, Math.PI / 2);
  kit.place('barricade', -41.3, -2.3, Math.PI / 2 + 0.25);
  kit.place('barricade', -41.5, 2.7, Math.PI / 2 - 0.2);

  // The shut news kiosk tucked in beside the south stair.
  kiosk(kit, x + 0.06, -42.5, stair.zOut + 0.2, FRONT_Z - 0.1, '+x', 'CANDY  ·  SODA');
}

// -------------------------------------------------------------------------------------------------
// East end: the Vultures' roadblock. A jack-knifed box truck, barriers, a fence with scrim behind it.
// -------------------------------------------------------------------------------------------------

function buildRoadblock(kit, mats) {
  const x = BOUNDS.maxX - 0.75;
  const scrim = ['fabric', { color: 0x1f3a2c, doubleSide: true }];
  for (const [z0, z1, y0] of [[-12.2, -ROAD_Z, KERB], [-ROAD_Z, ROAD_Z, 0], [ROAD_Z, FRONT_Z, KERB]]) {
    chainlink(kit, x, z0, x, z1, y0, y0 + 2.5, { spacing: 2.4 });
    kit.quad(scrim, '-x', x - 0.03, y0 + 1.3, (z0 + z1) / 2, z1 - z0 - 0.2, 2.1);
    kit.solid(x - 0.05, x + 0.05, y0, y0 + 2.5, z0, z1, { surface: 'metal', tag: 'roadblock' });
  }
  kit.solid(x, BOUNDS.maxX, 0, 8, -12.2, FRONT_Z, { tag: 'seal', playerOnly: true });
  // Feet of the fence panels: concrete blocks every panel.
  for (let z = -6.6; z <= 6.7; z += 2.4) kit.box('concrete', x - 0.18, x + 0.18, 0, 0.14, z - 0.35, z + 0.35, { noBottom: true });

  kit.place('box_truck', 41.4, 0.3, 1.05, { color: 0x5a5d62 });
  kit.place('jersey_barrier', 43.9, -5.5, Math.PI / 2);
  kit.place('jersey_barrier', 43.9, 5.6, Math.PI / 2);
  kit.place('jersey_barrier', 38.9, -5.3, 0.25);
  kit.place('barricade', 41.6, -6.4, 0.15);
  kit.place('barricade', 37.4, 4.4, -0.3);
  kit.place('oil_drum', 44.2, 2.7);
  kit.place('oil_drum', 43.7, 3.4);
  kit.place('floodlight_stand', 44.2, 7.9, Math.PI / 2);
  const front = wallFrame(kit, '-x', x - 0.04);
  front.overlay(mats.graffiti('VULTURES', 5, 0x8a1a22), -4.6, 1.4, 0.012, { w: 3.6, h: 1.1 });
  front.overlay(mats.graffiti('VLTR', 3, 0x8a1a22), 5.4, 1.2, 0.012);
}

// -------------------------------------------------------------------------------------------------
// The sidewalk shed in front of S3: scaffold posts, a plywood deck 2.8 m up, a parapet, a stair.
// -------------------------------------------------------------------------------------------------

function buildShed(kit, mats, text) {
  const S = SHED;
  const deck = S.deck;
  const green = ['plywood', { color: HOARDING_GREEN }];
  const postsX = [];
  for (let x = S.x0 + 0.12; x <= S.x1 - 0.05; x += (S.x1 - S.x0 - 0.24) / 6) postsX.push(x);
  const rows = [S.z0 + 0.15, S.z1 - 0.15];

  for (const x of postsX) {
    for (const z of rows) {
      kit.cyl('metal_galv', x, KERB, deck - 0.16, z, 0.045, 6);
      kit.box('wood', x - 0.16, x + 0.16, KERB, KERB + 0.045, z - 0.13, z + 0.13, { noBottom: true, cast: false }); // mud sill
      kit.solid(x - 0.07, x + 0.07, KERB, deck - 0.16, z - 0.07, z + 0.07, { surface: 'metal', tag: 'shed-post' });
    }
    kit.pipe('metal_galv', [x, deck - 0.34, rows[0]], [x, deck - 0.34, rows[1]], 0.035, 5);
  }
  for (const z of rows) {
    kit.pipe('metal_galv', [S.x0, deck - 0.24, z], [S.x1, deck - 0.24, z], 0.035, 5);
    // Knee braces at the heads of the posts: above head height, so the sidewalk stays clear.
    for (let i = 0; i < postsX.length - 1; i++) {
      const a = postsX[i];
      const b = postsX[i + 1];
      kit.pipe('metal_galv', [a, 2.05, z], [a + 0.75, deck - 0.26, z], 0.025, 5, { cast: false });
      kit.pipe('metal_galv', [b, 2.05, z], [b - 0.75, deck - 0.26, z], 0.025, 5, { cast: false });
    }
  }

  // Deck on timber joists.
  kit.block('plywood', S.x0, S.x1, deck - 0.16, deck, S.z0, S.z1, { tag: 'shed-deck', surface: 'wood', noNav: true });
  for (let x = S.x0 + 0.6; x < S.x1; x += 1.2) kit.box('wood', x - 0.04, x + 0.04, deck - 0.3, deck - 0.16, S.z0, S.z1, { cast: false });

  // Parapet: painted boards, waist high from the deck. Open where the stair arrives and along the wall.
  const P = S.parapet;
  const kerbSide = hoarding(kit, S.x0, S.x1, S.z0 + 0.04, deck, deck + P, HOARDING_GREEN, '-z');
  hoarding(kit, S.z0, S.z1, S.x1 - 0.04, deck, deck + P, HOARDING_GREEN, '+x');
  hoarding(kit, S.z0, S.stair.z0, S.x0 + 0.04, deck, deck + P, HOARDING_GREEN, '-x');
  // A skirt below the deck edge hides the joists from the street. The shops' banners hang on the
  // parapet: the shed covers their own signs.
  const skirt = wallFrame(kit, '-z', S.z0);
  skirt.box(green, S.x0, S.x1, deck - 0.5, deck, 0, 0.03);
  const banners = [
    [text.storefronts[4], 4.1, 0xf2c21a, 0xb3261e],
    [text.storefronts[5], 10, 0x101113, 0xff3030],
    [text.storefronts[6], 15.9, 0x2a0f1e, 0xff3d9a],
  ];
  for (const [name, u, bg, fg] of banners) {
    const banner = mats.sign({ text: name, w: 4.9, h: 0.78, style: 'awning', bg, fg, lit: false });
    kerbSide.overlay(banner, u, deck + P / 2, 0.012);
  }
  skirt.overlay(mats.sign({ text: 'SIDEWALK SHED  ·  PERMIT 0214  ·  STORES OPEN DURING WORK', w: 5.6, h: 0.24, style: 'stencil', fg: 0xe6e4dc, lit: false }), 10, deck - 0.25, 0.04);

  // Caged bulbs strung under the deck.
  const bulb = kit.glow(0xfff1d0, 3.5);
  for (let i = 0; i < postsX.length - 1; i++) {
    const x = (postsX[i] + postsX[i + 1]) / 2;
    kit.box(bulb, x - 0.06, x + 0.06, deck - 0.44, deck - 0.32, 9.14, 9.26, { cast: false, receive: false });
    if (i % 2 === 0) kit.lamp(x, deck - 0.5, 9.2, 'work', 0xfff1d0, 9, 7, { priority: 3 });
  }

  // The scaffold stair at the west end: twelve treads up against the building.
  const st = S.stair;
  kit.stairs('plywood', st.x0, st.x1, st.z0, st.z1, KERB, deck, st.risers, '+x', { open: true, tag: 'shed-stair', surface: 'wood' });
  for (const z of [st.z0 + 0.03, st.z1 - 0.03]) kit.beam('wood', [st.x0, KERB + 0.02, z], [st.x1, deck - 0.08, z], 0.05, 0.24);
  // Handrail on the open (street) side; the building is on the other.
  kit.beam('metal_galv', [st.x0, KERB + 1.0, st.z0], [st.x1, deck + 1.0, st.z0], 0.04, 0.04, { cast: false });
  kit.beam('metal_galv', [st.x0, KERB + 0.5, st.z0], [st.x1, deck + 0.5, st.z0], 0.04, 0.04, { cast: false });
  for (const f of [0, 0.33, 0.66, 1]) {
    const x = st.x0 + (st.x1 - st.x0) * f;
    const y = KERB + (deck - KERB) * f;
    kit.box('metal_galv', x - 0.02, x + 0.02, y, y + 1.0, st.z0 - 0.02, st.z0 + 0.02, { cast: false });
  }
  kit.solid(st.x0, st.x1, KERB, deck + 1.0, st.z0 - 0.04, st.z0 + 0.02, { surface: 'metal', tag: 'railing', playerOnly: true });

  // Up top: sandbags along the parapet and whatever the crew left.
  kit.place('sandbags', 5.4, S.z0 + 0.45, 0, { y: deck });
  kit.place('sandbags', 12.8, S.z0 + 0.45, 0, { y: deck });
  kit.place('crate_wood', 17.2, 10.2, 0.2, { y: deck });
  kit.place('cardboard_boxes', 2.2, 8.4, 0.4, { y: deck });
  kit.place('pallet', 8.6, 10.2, 0, { y: deck });

  // Under it, against the shop fronts.
  kit.place('cardboard_boxes', 8.5, 10.45, 0.1);
  kit.place('milk_crates', 14.4, 10.5);
  kit.place('trash_can', 3.3, 10.45);

  return {
    stairsFoot: new THREE.Vector3(st.x0 - 0.6, KERB, (st.z0 + st.z1) / 2),
    deck: new THREE.Vector3((S.x0 + S.x1) / 2, deck, 9.3),
  };
}
