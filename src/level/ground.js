// The ground of the avenue: roadway, raised sidewalks with kerbs and dropped kerbs, markings, repairs,
// puddles, manholes and street decals. The yards (court, lot, vacant lot, lane, alley) paint their own.

import * as THREE from 'three';
import { BOUNDS, DRIVEWAYS, FRONT_Z, KERB, ROAD_Z, SIDEWALKS } from './layout.js';

const FAR = 96; // how far the avenue runs on past the closures (decor only)
const KERB_STONE = 0.28;
const FLARE = 0.9; // length of the slope at each side of a dropped kerb
// Heights of the flat layers over the road plane, far enough apart not to fight in the depth buffer.
export const LIFT = { patch: 0.008, wet: 0.014, paint: 0.021, decal: 0.028 };

const CROSSWALK = [23, 26.6]; // the mid-block crossing between the cage and the lot

/** Irregular flat patch (a puddle, a stain): a fan whose rim wanders around an ellipse. */
export function blob(kit, m, x, z, rx, rz, y, yaw = 0) {
  const { rng } = kit;
  const n = 14;
  const position = [0, 0, 0];
  const uv = [0, 0];
  const index = [];
  let wobble = rng.range(-0.15, 0.15);
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    wobble = wobble * 0.5 + rng.range(-0.22, 0.22);
    const px = Math.cos(a) * rx * (1 + wobble);
    const pz = Math.sin(a) * rz * (1 + wobble);
    position.push(px, 0, pz);
    uv.push(px, pz);
    // counter-clockwise seen from above (+y): centre, next, current
    index.push(0, 1 + ((i + 1) % n), 1 + i);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(position), 3));
  geo.setAttribute('normal', new THREE.BufferAttribute(new Float32Array((n + 1) * 3).map((_, i) => (i % 3 === 1 ? 1 : 0)), 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(uv), 2));
  geo.setIndex(index);
  const mesh = kit.mesh(geo, m, { cast: false });
  mesh.position.set(x, y, z);
  mesh.rotation.y = yaw;
  return mesh;
}

export function buildGround(kit) {
  const { rng, mats } = kit;
  const puddles = []; // {x, z, r}: where the street holds water (steam and splash cues can use it)

  // One sheet of asphalt under everything, well past the bounds so the avenue never ends in a void.
  kit.flat('asphalt', -FAR - 14, FAR + 14, -72, 72, 0);

  // ---------------------------------------------------------------------------------------------
  // Sidewalks, kerbs, dropped kerbs
  // ---------------------------------------------------------------------------------------------

  function slab(x0, x1, z0, z1, collide) {
    const north = z1 <= 0;
    const kerb0 = north ? z1 - KERB_STONE : z0;
    const kerb1 = north ? z1 : z0 + KERB_STONE;
    kit.box('sidewalk', x0, x1, 0, KERB, north ? z0 : kerb1, north ? kerb0 : z1, { noBottom: true });
    kit.box('curb', x0, x1, 0, KERB, kerb0, kerb1, { noBottom: true });
    if (collide) kit.solid(x0, x1, 0, KERB, z0, z1, { surface: 'concrete', tag: 'sidewalk' });
  }
  for (const s of SIDEWALKS) slab(s.x0, s.x1, s.z0, s.z1, true);
  for (const side of [-1, 1]) {
    const z0 = side < 0 ? -FRONT_Z : ROAD_Z;
    slab(-FAR, BOUNDS.minX, z0, z0 + 4, false);
    slab(BOUNDS.maxX, FAR, z0, z0 + 4, false);
  }

  for (const [x0, x1, side] of DRIVEWAYS) {
    const z0 = side < 0 ? -FRONT_Z : ROAD_Z;
    const z1 = z0 + 4;
    // The apron: concrete at road level between the slabs, a flush kerb stone, a slope up at each end.
    kit.flat('concrete', x0, x1, z0, z1, LIFT.patch);
    const kz = side < 0 ? -ROAD_Z - KERB_STONE : ROAD_Z;
    kit.box('curb', x0, x1, 0, 0.03, kz, kz + KERB_STONE, { noBottom: true, cast: false });
    kit.prism('sidewalk', [[x0, 0], [x0 + FLARE, 0], [x0, KERB]], 'z', z0, z1, { noCaps: true });
    kit.prism('sidewalk', [[x1, 0], [x1, KERB], [x1 - FLARE, 0]], 'z', z0, z1, { noCaps: true });
  }

  // ---------------------------------------------------------------------------------------------
  // Paint
  // ---------------------------------------------------------------------------------------------

  // Double yellow down the middle, broken at the crossing.
  for (const z of [-0.15, 0.15]) {
    kit.paint('yellow', -FAR, z, CROSSWALK[0] - 0.4, z, 0.12, LIFT.paint);
    kit.paint('yellow', CROSSWALK[1] + 0.4, z, FAR, z, 0.12, LIFT.paint);
  }

  // Parking stall ticks at the kerbs, left out at driveways and the crossing.
  const clearOfDriveways = (x, side) =>
    !DRIVEWAYS.some(([a, b, s]) => s === side && x > a - 1 && x < b + 1) && !(x > CROSSWALK[0] - 3 && x < CROSSWALK[1] + 3);
  for (let x = -40.6; x <= 44; x += 5.8) {
    for (const side of [-1, 1]) {
      if (clearOfDriveways(x, side)) kit.paint('white', x, side * 5.1, x, side * 6.98, 0.12, LIFT.paint);
    }
  }

  // The crossing: ladder bars across the full roadway and a stop bar for each direction. The bars
  // repeat along the decal's width, which is laid across the road.
  const zebra = mats.decal('crosswalk');
  const crossX = (CROSSWALK[0] + CROSSWALK[1]) / 2;
  const crossW = CROSSWALK[1] - CROSSWALK[0];
  if (kit.tiles(zebra)) {
    kit.overlay(zebra, '+y', crossX, LIFT.decal, 0, { w: 13.6, h: crossW, yaw: Math.PI / 2 });
  } else {
    for (let i = 0; i < 4; i++) kit.overlay(zebra, '+y', crossX, LIFT.decal, -5.25 + i * 3.5, { w: 3.5, h: crossW, yaw: Math.PI / 2 });
  }
  kit.paint('white', CROSSWALK[0] - 1.1, 0.5, CROSSWALK[0] - 1.1, 6.9, 0.4, LIFT.paint);
  kit.paint('white', CROSSWALK[1] + 1.1, -6.9, CROSSWALK[1] + 1.1, -0.5, 0.4, LIFT.paint);

  // Lane arrows: eastbound on the south side, westbound on the north side.
  const arrow = mats.decal('arrow');
  for (const [x, z, yaw] of [[-29, 2.3, -Math.PI / 2], [15.5, 2.3, -Math.PI / 2], [-12, -2.3, Math.PI / 2], [34, -2.3, Math.PI / 2]]) {
    kit.overlay(arrow, '+y', x, LIFT.decal, z, { yaw });
  }

  // Yellow kerb paint: the hydrant on the south side, the bus stop on the north side.
  for (const [x0, x1, side] of [[-16.4, -12.6, 1], [27.2, 31.2, -1]]) {
    const kz = side < 0 ? -ROAD_Z - KERB_STONE - 0.004 : ROAD_Z - 0.004;
    kit.box('paint_yellow', x0, x1, 0.01, KERB + 0.004, kz, kz + KERB_STONE + 0.008, { noBottom: true, cast: false });
  }

  // ---------------------------------------------------------------------------------------------
  // Repairs, water, wear
  // ---------------------------------------------------------------------------------------------

  // Patched repairs: utility cuts across the road and long strips where a trench was filled.
  const dark = ['asphalt', { color: 0x121316 }];
  const pale = ['asphalt', { color: 0x2a2b2e }];
  const patches = [
    [dark, -41, -37.5, -6.5, -1.2],
    [pale, -33.5, -32.4, -6.8, 6.8],
    [dark, -27, -9, -3.3, -2.1],
    [pale, -22.5, -19.5, 1.2, 4.4],
    [dark, -14, -12.9, -6.9, 2.4],
    [pale, -3.5, 2.5, -1, 0.6],
    [dark, 3, 21, 2.2, 3.5],
    [pale, 8.5, 12, -5.5, -2.6],
    [dark, 17.2, 18.3, -6.9, 6.9],
    [pale, 28, 33, -4.2, -1.4],
    [dark, 30.5, 43, 1, 2.1],
    [pale, 37, 40, 3.2, 6.6],
    [dark, 50, 61, -5, -1],
    [pale, -64, -52, 0.8, 4],
  ];
  for (const [m, x0, x1, z0, z1] of patches) kit.flat(m, x0, x1, z0, z1, LIFT.patch);

  // Standing water. The open hydrant at the south kerb (x ≈ −12) has hosed the street down: a sheet of
  // water at its foot, a wet gutter running east, pools in every low spot.
  const water = (x, z, rx, rz, yaw = 0) => {
    blob(kit, 'asphalt_wet', x, z, rx, rz, LIFT.wet, yaw);
    puddles.push({ x, z, r: Math.min(rx, rz) });
  };
  water(-11.6, 4.6, 5.2, 2.4, 0.1);
  water(-6.5, 6.1, 5, 0.8);
  water(1.5, 6.2, 4.4, 0.7);
  water(9.5, 6.25, 4.6, 0.6);
  for (const [x, z, rx, rz, yaw] of [
    [-38.5, -6, 3.2, 0.8, 0], [-34, 1.4, 2.6, 1.5, 0.4], [-27.5, 6.2, 3, 0.7, 0], [-24, -1.6, 2.2, 1.3, -0.3],
    [-20.5, -6.15, 4.2, 0.7, 0], [-17.5, 2.9, 1.8, 1.1, 0.8], [-9.5, -4, 3, 1.6, 0.2], [-2.6, -5.9, 3.6, 0.9, 0],
    [-0.5, 1.9, 2.2, 1.4, -0.5], [5.8, -1.8, 2.8, 1.7, 0.3], [12.5, -6.2, 3.8, 0.7, 0], [14.5, 0.8, 2.4, 1.2, 0.6],
    [19.5, 5.2, 2.6, 1.5, -0.2], [21.5, -3.4, 2, 1.2, 0.2], [27.5, 0.6, 3.4, 1.9, 0.1], [31, -6.1, 4, 0.8, 0],
    [33.5, 5.9, 3.5, 0.9, 0], [36.5, -1.4, 2.4, 1.5, -0.4], [40.5, 3.4, 2.2, 1.2, 0.5], [43, -5.4, 2.4, 1.1, 0],
    [52, 2, 4, 2, 0.2], [60, -3, 5, 2, 0], [-55, -2.5, 4.5, 1.8, 0.1], [-66, 3, 5, 2.2, -0.2],
  ]) {
    water(x, z, rx, rz, yaw);
  }

  // Cracks, oil and grime: densest where cars stand and where the gutter collects dirt.
  const crack = mats.decal('crack');
  const oil = mats.decal('oil');
  const grime = mats.decal('grime');
  for (let i = 0; i < 16; i++) {
    kit.overlay(crack, '+y', rng.range(-44, 44), LIFT.decal, rng.range(-6, 6), { yaw: rng.range(0, Math.PI), w: crack.w * rng.range(0.9, 1.7) });
  }
  for (let i = 0; i < 14; i++) {
    const side = rng.sign();
    kit.overlay(oil, '+y', rng.range(-42, 42), LIFT.decal, side * rng.range(5.4, 6.4), { yaw: rng.range(0, Math.PI * 2), w: oil.w * rng.range(0.6, 1), h: oil.h * rng.range(0.6, 1) });
  }
  for (let i = 0; i < 12; i++) {
    const side = rng.sign();
    kit.overlay(grime, '+y', rng.range(-44, 44), LIFT.decal, side * rng.range(6.2, 6.8), { yaw: rng.range(0, Math.PI * 2), w: grime.w * 1.4, h: grime.h * 0.6 });
  }

  // Manholes: three of them breathe steam (level.steam).
  const steam = [];
  for (const [x, z, vents] of [[-22.5, -1.8, true], [-9.5, 2.6, false], [6.4, -2.4, true], [18.6, 1.9, false], [30.5, -0.9, true], [-36, 2.2, false]]) {
    kit.place('manhole', x, z, rng.range(0, Math.PI));
    if (vents) steam.push(new THREE.Vector3(x, 0.05, z));
  }

  return { puddles, steam };
}
