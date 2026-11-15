// The El: the elevated line over Jamaica Ave, the block's signature. Two rows of riveted H-columns on
// flared bases, a cross girder at every pair, longitudinal girders and stringers, lateral bracing, an
// open deck of ties and rails with plank walkways, sodium lamps hung underneath, and the sealed station
// at the west end (mezzanine under the tracks, a covered stair down to each sidewalk, platforms above).
//
// Only the columns, the girders, the deck, the mezzanine and the stairs collide. Everything is steel_el.

import * as THREE from 'three';
import { BOUNDS, EL, KERB, STATION } from './layout.js';

const FAR = 96;
const STEEL = 'steel_el';
const SODIUM = 0xffb45e;
const TIE_PITCH = 0.56;
const DOWN = new THREE.Vector3(0, -1, 0);

export function buildEl(kit) {
  const { minX, maxX } = BOUNDS;
  const tie = ['wood', { color: 0x2b221b }]; // creosoted timber
  const plank = ['wood', { color: 0x4a3c2c }];
  const top = EL.y;

  // ---------------------------------------------------------------------------------------------
  // Columns and cross girders
  // ---------------------------------------------------------------------------------------------

  function column(x, z, detailed) {
    const inward = -Math.sign(z);
    kit.box('concrete', x - 0.52, x + 0.52, 0, 0.26, z - 0.52, z + 0.52, { noBottom: true });
    // Flared base: a four-sided frustum from the footing up to the shaft.
    kit.cyl(STEEL, x, 0.26, 1.2, z, 0.63, 4, { radiusTop: 0.36 }).rotation.y = Math.PI / 4;
    // H shaft: two flanges across the street's axis and a web between them.
    kit.box(STEEL, x - 0.25, x - 0.19, 1.2, EL.columnTop, z - 0.24, z + 0.24, { noTop: true, noBottom: true });
    kit.box(STEEL, x + 0.19, x + 0.25, 1.2, EL.columnTop, z - 0.24, z + 0.24, { noTop: true, noBottom: true });
    kit.box(STEEL, x - 0.19, x + 0.19, 1.2, EL.columnTop, z - 0.05, z + 0.05, { noTop: true, noBottom: true });
    kit.box(STEEL, x - 0.31, x + 0.31, EL.columnTop - 0.22, EL.columnTop, z - 0.31, z + 0.31); // cap plate
    if (detailed) {
      // Batten plates tie the flanges together every metre or so: the riveted, built-up look.
      for (const y of [1.55, 2.5, 3.45, 4.4]) {
        for (const side of [-1, 1]) kit.box(STEEL, x - 0.2, x + 0.2, y, y + 0.3, z + side * 0.2, z + side * 0.24);
      }
      // Knee braces: across to the cross girder and along to the longitudinal girder.
      kit.beam(STEEL, [x, 4.15, z + inward * 0.24], [x, EL.columnTop + 0.1, z + inward * 1.45], 0.16, 0.14);
      for (const side of [-1, 1]) kit.beam(STEEL, [x + side * 0.25, 4.35, z], [x + side * 1.35, 5.56, z], 0.14, 0.14);
    }
    kit.solid(x - 0.32, x + 0.32, 0, EL.columnTop, z - 0.32, z + 0.32, { surface: 'metal', tag: 'el-column' });
  }

  function bent(x, detailed) {
    for (const z of [-EL.rowZ, EL.rowZ]) column(x, z, detailed);
    // Cross girder: a plate girder with flange plates and vertical stiffeners.
    kit.box(STEEL, x - 0.2, x + 0.2, EL.columnTop, top, -5.05, 5.05);
    kit.box(STEEL, x - 0.33, x + 0.33, EL.columnTop, EL.columnTop + 0.07, -5.05, 5.05);
    if (detailed) {
      for (let z = -4; z <= 4.01; z += 1) kit.box(STEEL, x - 0.27, x + 0.27, EL.columnTop + 0.07, top, z - 0.03, z + 0.03, { noTop: true });
    }
    kit.solid(x - 0.3, x + 0.3, EL.columnTop, top, -5.05, 5.05, { surface: 'metal', tag: 'el-girder', noNav: true });
  }

  for (const x of EL.bents) bent(x, true);
  for (const x of EL.far) bent(x, false);

  // ---------------------------------------------------------------------------------------------
  // Longitudinal steel
  // ---------------------------------------------------------------------------------------------

  for (const z of [-EL.rowZ, EL.rowZ]) {
    kit.box(STEEL, -FAR, FAR, 5.5, top, z - 0.17, z + 0.17);
    kit.box(STEEL, -FAR, FAR, 5.5, 5.57, z - 0.29, z + 0.29);
    for (let x = minX + 1; x < maxX; x += 2.5) {
      if (Math.abs(((x + 45) % 10) - 0) < 0.3) continue; // a cross girder stands here
      kit.box(STEEL, x - 0.03, x + 0.03, 5.57, top, z - 0.25, z + 0.25, { noTop: true });
    }
    kit.solid(minX, maxX, 5.5, top, z - 0.2, z + 0.2, { surface: 'metal', tag: 'el-girder', noNav: true });
    // Fascia along the deck edge, on short cantilevers off the main girder.
    const edge = Math.sign(z) * EL.half;
    kit.box(STEEL, -FAR, FAR, 6.15, 6.72, Math.min(edge, edge - Math.sign(z) * 0.1), Math.max(edge, edge - Math.sign(z) * 0.1));
    for (let x = minX + 1; x < maxX; x += 2.5) {
      kit.box(STEEL, x - 0.05, x + 0.05, 6.25, top, Math.min(z, edge), Math.max(z, edge), { noTop: true });
    }
  }

  // A stringer under every rail.
  const railZ = [];
  for (const track of EL.tracks) railZ.push(track - EL.gauge / 2, track + EL.gauge / 2);
  for (const z of railZ) kit.box(STEEL, -FAR, FAR, 5.92, top, z - 0.1, z + 0.1, { noTop: true });

  // Cross frames at mid-span and a zigzag of lateral bracing, read against the sky from below.
  const bays = [-EL.rowZ + 0.2, railZ[0], railZ[1], railZ[2], railZ[3], EL.rowZ - 0.2];
  for (let i = 0; i < EL.bents.length - 1; i++) {
    const x0 = EL.bents[i];
    const mid = x0 + EL.spacing / 2;
    kit.box(STEEL, mid - 0.07, mid + 0.07, 6.02, 6.42, -EL.rowZ, EL.rowZ, { noTop: true });
    for (const [a, b] of [[x0 + 0.3, mid - 0.1], [mid + 0.1, x0 + EL.spacing - 0.3]]) {
      for (let k = 0; k < bays.length - 1; k += 2) {
        const flip = (i + k / 2) % 2 === 0;
        kit.beam(STEEL, [a, 6.3, flip ? bays[k] : bays[k + 1]], [b, 6.3, flip ? bays[k + 1] : bays[k]], 0.09, 0.09);
      }
    }
  }

  // ---------------------------------------------------------------------------------------------
  // Deck: ties, rails, third rails, walkways, handrails
  // ---------------------------------------------------------------------------------------------

  for (const track of EL.tracks) {
    for (let x = minX + 0.2; x < maxX; x += TIE_PITCH) {
      kit.box(tie, x - 0.11, x + 0.11, top, EL.tieTop, track - 1.35, track + 1.35, { noBottom: false });
    }
    // Past the closures nobody is ever underneath: one slab stands in for the ties.
    kit.box(tie, -FAR, minX, top, EL.tieTop, track - 1.35, track + 1.35);
    kit.box(tie, maxX, FAR, top, EL.tieTop, track - 1.35, track + 1.35);
    for (const side of [-1, 1]) {
      const z = track + (side * EL.gauge) / 2;
      kit.box('metal_dark', -FAR, FAR, EL.tieTop, EL.railTop, z - 0.035, z + 0.035, { noBottom: true });
    }
    // Third rail on the outer side of each track, under its cover board.
    const third = track + Math.sign(track) * 1.12;
    kit.box('metal_dark', -FAR, FAR, EL.tieTop, EL.tieTop + 0.11, third - 0.04, third + 0.04, { noBottom: true });
    kit.box(plank, -FAR, FAR, EL.tieTop + 0.17, EL.tieTop + 0.2, third - 0.13, third + 0.13);
  }
  kit.box(plank, -FAR, FAR, top + 0.08, top + 0.14, -0.6, 0.6);
  for (const side of [-1, 1]) {
    const z0 = side * 3.9;
    const z1 = side * (EL.half - 0.1);
    kit.box(plank, -FAR, FAR, top + 0.08, top + 0.14, Math.min(z0, z1), Math.max(z0, z1));
    const rail = side * (EL.half - 0.05);
    for (const y of [7.25, 7.75]) kit.box(STEEL, -FAR, FAR, y - 0.025, y + 0.025, rail - 0.025, rail + 0.025);
    for (let x = minX + 1; x < maxX; x += 2.5) kit.box(STEEL, x - 0.03, x + 0.03, 6.7, 7.75, rail - 0.03, rail + 0.03);
  }
  kit.solid(minX, maxX, top, EL.railTop + 0.07, -EL.half, EL.half, { surface: 'metal', tag: 'el-deck', noNav: true });

  // ---------------------------------------------------------------------------------------------
  // Lamps hung under the deck: one over each travel lane per bay, staggered
  // ---------------------------------------------------------------------------------------------

  const bulb = kit.glow(SODIUM, 5);
  for (let i = 0; i < EL.bents.length - 1; i++) {
    const x = EL.bents[i] + EL.spacing / 2;
    const z = i % 2 === 0 ? 2.1 : -2.1;
    kit.box('metal_dark', x - 0.025, x + 0.025, 5.74, 6.02, z - 0.025, z + 0.025);
    kit.cyl('metal_dark', x, 5.58, 5.76, z, 0.3, 10, { radiusTop: 0.09, open: true });
    kit.cyl(bulb, x, 5.56, 5.6, z, 0.2, 10, { cast: false, receive: false });
    kit.lamp(x, 5.5, z, 'el', SODIUM, 30, 13, { dir: DOWN });
  }

  buildStation(kit);

  return { y: top, minX, maxX, minZ: -EL.half, maxZ: EL.half, deckTop: EL.railTop, tracks: EL.tracks.slice() };
}

/** The sealed station at the west end. */
function buildStation(kit) {
  const { mezz, bridgeX, stair } = STATION;
  const panel = ['corrugated', { color: 0x2f4038 }]; // painted sheet steel
  const roofing = ['corrugated', { color: 0x1c2224 }];
  const tube = kit.glow(0xcfe4ff, 3.2);
  const globe = kit.glow(0x55ff8a, 3.5);

  // Mezzanine: a fare-control box hung under the tracks.
  kit.box(STEEL, mezz.x0, mezz.x1, mezz.y0, mezz.y0 + 0.16, mezz.z0, mezz.z1);
  kit.box(panel, mezz.x0, mezz.x1, mezz.y0 + 0.16, mezz.y1, mezz.z0, mezz.z1, { noTop: true, noBottom: true });
  // A band of windows along its east face and both street sides; a few panes still lit.
  const band = [4.95, 5.75];
  const pane = (m, facing, cx, cz, w) => kit.quad(m, facing, cx, (band[0] + band[1]) / 2, cz, w, band[1] - band[0], { cast: false });
  for (let i = 0; i < 6; i++) {
    const z = mezz.z0 + 0.75 + i * 1.32;
    pane(i === 1 || i === 4 ? 'glass_lit_warm' : 'glass_dark', '+x', mezz.x1 + 0.012, z, 1.1);
  }
  for (const [facing, z] of [['-z', mezz.z0 - 0.012], ['+z', mezz.z1 + 0.012]]) {
    for (let i = 0; i < 4; i++) pane(i === 2 ? 'glass_lit_warm' : 'glass_dark', facing, mezz.x0 + 0.95 + i * 1.5, z, 1.2);
  }
  kit.box(STEEL, mezz.x1, mezz.x1 + 0.05, band[0] - 0.08, band[0], mezz.z0, mezz.z1);
  kit.box(STEEL, mezz.x1, mezz.x1 + 0.05, band[1], band[1] + 0.08, mezz.z0, mezz.z1);
  const name = kit.mats.sign({ text: '188 ST', sub: 'ELEVATED  ·  CLOSED 1 AM – 5 AM', w: 4.6, h: 0.82, style: 'plate' });
  kit.overlay(name, '+x', mezz.x1 + 0.03, 4.47, 0);
  kit.lamp(mezz.x1 + 0.6, 5.3, 0, 'window', 0xffc98a, 8, 7);
  kit.solid(mezz.x0, mezz.x1, mezz.y0, EL.y, mezz.z0, mezz.z1, { surface: 'metal', tag: 'station', noNav: true });

  for (const side of [-1, 1]) {
    const zIn = side * stair.zIn;
    const zOut = side * stair.zOut;
    const z0 = Math.min(zIn, zOut);
    const z1 = Math.max(zIn, zOut);
    const mz = side < 0 ? mezz.z0 : mezz.z1;

    // The covered walk from the mezzanine out over the parking lane to the stair head.
    const b0 = Math.min(mz, zOut);
    const b1 = Math.max(mz, zOut);
    kit.box(STEEL, bridgeX[0], bridgeX[1], mezz.y0, mezz.y0 + 0.16, b0, b1);
    for (const x of bridgeX) kit.box(panel, x - 0.04, x + 0.04, mezz.y0 + 0.16, mezz.y0 + 1.25, b0, b1);
    kit.box(roofing, bridgeX[0] - 0.15, bridgeX[1] + 0.15, mezz.y1 - 0.1, mezz.y1, b0 - (side < 0 ? 0.15 : 0), b1 + (side > 0 ? 0.15 : 0));
    kit.box(panel, bridgeX[0], bridgeX[1], mezz.y0 + 0.16, mezz.y1 - 0.1, zOut - 0.04, zOut + 0.04); // end wall
    kit.solid(bridgeX[0], bridgeX[1], mezz.y0, mezz.y1, b0, b1, { surface: 'metal', tag: 'station', noNav: true });
    for (const x of bridgeX) {
      // Posts under the stair head, down to the sidewalk.
      kit.box(STEEL, x - 0.07, x + 0.07, KERB, mezz.y0, Math.min(zOut - side * 0.14, zOut), Math.max(zOut - side * 0.14, zOut));
      kit.solid(x - 0.1, x + 0.1, KERB, mezz.y0, Math.min(zOut - side * 0.2, zOut), Math.max(zOut - side * 0.2, zOut), { surface: 'metal', tag: 'station' });
    }

    // The stair: treads, plate balustrades, a mid-flight trestle, a roof that follows the slope.
    kit.stairs(STEEL, stair.top, stair.foot, z0, z1, KERB, mezz.y0, stair.risers, '-x', { collide: false });
    const slope = (mezz.y0 - KERB) / (stair.foot - stair.top);
    const yAt = (x) => KERB + (stair.foot - x) * slope;
    for (const z of [z0, z1]) {
      kit.prism(
        panel,
        [[stair.foot + 0.25, KERB], [stair.foot + 0.25, KERB + 1.05], [stair.top, mezz.y0 + 1.25], [stair.top, mezz.y0 - 0.5]],
        'z',
        z - 0.04,
        z + 0.04,
      );
    }
    const mid = (stair.top + stair.foot) / 2;
    for (const z of [z0 + 0.08, z1 - 0.08]) kit.box(STEEL, mid - 0.06, mid + 0.06, KERB, yAt(mid) - 0.2, z - 0.06, z + 0.06);
    kit.box(STEEL, mid - 0.06, mid + 0.06, yAt(mid) - 0.36, yAt(mid) - 0.2, z0, z1);
    kit.prism(
      roofing,
      [[stair.foot + 0.6, KERB + 2.5], [stair.foot + 0.6, KERB + 2.58], [stair.top - 0.1, mezz.y1 + 0.08], [stair.top - 0.1, mezz.y1]],
      'z',
      z0 - 0.12,
      z1 + 0.12,
    );
    for (const z of [z0, z1]) {
      // Portal posts at the foot, each with a green globe.
      kit.box(STEEL, stair.foot + 0.2, stair.foot + 0.32, KERB, KERB + 2.5, z - 0.06, z + 0.06);
      kit.cyl(STEEL, stair.foot + 0.26, KERB + 2.58, KERB + 2.86, z, 0.035, 6);
      kit.mesh(new THREE.SphereGeometry(0.17, 10, 8), globe, { cast: false, receive: false }).position.set(stair.foot + 0.26, KERB + 3.0, z);
    }
    kit.lamp(stair.foot + 0.26, KERB + 3.0, (z0 + z1) / 2, 'neon', 0x55ff8a, 6, 6, { priority: 3 });
    // Closed for the night: a folding gate across the foot, and nobody climbs past it.
    kit.box('roll_gate', stair.foot + 0.14, stair.foot + 0.2, KERB, KERB + 2.5, z0 + 0.04, z1 - 0.04);
    kit.solid(stair.foot + 0.05, stair.foot + 0.3, KERB, KERB + 2.6, z0, z1, { surface: 'metal', tag: 'station' });
    const closed = kit.mats.sign({ text: '188 ST', sub: 'STATION CLOSED', w: 1.5, h: 0.42, style: 'plate' });
    kit.overlay(closed, '+x', stair.foot + 0.34, KERB + 2.24, (z0 + z1) / 2);
    // Coarse colliders under the flight, so rounds stop on it and nothing walks through it.
    const blocks = 5;
    for (let i = 0; i < blocks; i++) {
      const xa = stair.top + ((stair.foot - stair.top) * i) / blocks;
      const xb = stair.top + ((stair.foot - stair.top) * (i + 1)) / blocks;
      kit.solid(xa, xb, KERB, yAt(xb) + 1.1, z0 - 0.05, z1 + 0.05, { surface: 'metal', tag: 'station' });
    }

    // Platform above: slab on cantilever brackets, a windscreen with a window band, a canopy.
    const p0 = side * 3.75;
    const p1 = side * 7.05;
    const pEnd = -29.5;
    kit.box('concrete', -FAR, pEnd, 7.55, 7.75, Math.min(p0, p1), Math.max(p0, p1));
    kit.box('paint_yellow', -FAR, pEnd, 7.75, 7.762, Math.min(p0, p0 + side * 0.3), Math.max(p0, p0 + side * 0.3), { cast: false });
    const wz = side * 7;
    kit.box(panel, -FAR, pEnd - 1.5, 7.75, 10.15, Math.min(wz, p1), Math.max(wz, p1));
    for (let x = -45.2; x < pEnd - 2.2; x += 2.4) {
      const lit = Math.round(x * 10) % 3 !== 0;
      kit.quad(lit ? 'glass_lit_cool' : 'glass_dark', side > 0 ? '+z' : '-z', x, 9.05, p1 + side * 0.012, 1.7, 0.75, { cast: false });
    }
    kit.prism(
      roofing,
      [[side * 3.9, 10.42], [side * 7.25, 10.15], [side * 7.25, 10.22], [side * 3.9, 10.5]],
      'x',
      -FAR,
      pEnd - 1,
    );
    for (const x of [...EL.far.filter((f) => f < 0), -45, -35]) {
      kit.box(STEEL, x - 0.07, x + 0.07, 7.75, 10.2, side * 6.75 - 0.07, side * 6.75 + 0.07);
      kit.beam(STEEL, [x, 6.2, side * 4.8], [x, 7.5, side * 6.9], 0.14, 0.12);
      kit.box(STEEL, x - 0.07, x + 0.07, 7.4, 7.55, Math.min(side * 3.8, side * 7), Math.max(side * 3.8, side * 7));
    }
    // End-of-platform railing and the tubes under the canopy that keep the station glowing all night.
    kit.box(STEEL, pEnd - 0.04, pEnd, 7.75, 8.85, Math.min(p0, p1), Math.max(p0, p1));
    for (const x of [-43.5, -38, -32.5]) {
      kit.box(tube, x - 0.6, x + 0.6, 10.02, 10.07, side * 5.4 - 0.05, side * 5.4 + 0.05, { cast: false, receive: false });
      kit.lamp(x, 9.9, side * 5.4, 'el', 0xcfe4ff, 10, 9, { priority: 2 });
    }
    kit.solid(BOUNDS.minX, pEnd, 7.55, 7.75, Math.min(p0, p1), Math.max(p0, p1), { surface: 'concrete', tag: 'station', noNav: true });
    kit.solid(BOUNDS.minX, pEnd - 1.5, 7.75, 10.2, Math.min(wz, p1), Math.max(wz, p1), { surface: 'metal', tag: 'station', noNav: true });
  }
}
