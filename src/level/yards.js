// The open ground off the avenue: the alley, the cut beside the deli, The Cage, the vacant lot with the
// mural, the rear service lane and the parking lot with the IPX truck.

import * as THREE from 'three';
import { LIFT, blob } from './ground.js';
import { ALLEY, BOUNDS, BUILDINGS, CAGE, CUT, FRONT_Z, KERB, LANE, LOT, VACANT } from './layout.js';
import { wallFrame } from './buildings.js';
import { chainlink, hoarding } from './fences.js';

export function buildYards(kit) {
  const { mats, rng } = kit;
  const steam = [];
  const out = { steam, truck: null };

  buildAlley(kit, steam);
  buildCut(kit);
  buildCage(kit);
  buildVacantLot(kit, rng);
  buildLane(kit, steam);
  out.truck = buildLot(kit, mats, rng);
  return out;
}

// -------------------------------------------------------------------------------------------------
// The alley between the shop and the deli
// -------------------------------------------------------------------------------------------------

function buildAlley(kit, steam) {
  const { mats } = kit;
  const A = ALLEY;
  kit.flat(['asphalt', { color: 0x121316 }], A.minX, A.maxX, A.gateZ, A.maxZ, LIFT.patch);
  kit.flat('concrete', 8.15, 8.85, A.gateZ, A.maxZ, LIFT.wet); // the gutter down the middle
  blob(kit, 'asphalt_wet', 8.4, -18, 1.3, 3.4, LIFT.paint);
  blob(kit, 'asphalt_wet', 7.8, -27.5, 1.1, 2.2, LIFT.paint);
  const grime = mats.decal('grime');
  for (const [x, z] of [[10.2, -13.5], [6.9, -26], [9.8, -21], [7.2, -16]]) kit.overlay(grime, '+y', x, LIFT.decal, z, { yaw: x });

  kit.place('dumpster', 10.3, -12.95, Math.PI / 2);
  kit.place('dumpster', 6.72, -27.3, Math.PI / 2);
  kit.place('trash_bags', 10.2, -18.3, 0.4);
  kit.place('trash_bags', 6.9, -29.6, 1.9);
  kit.place('milk_crates', 10.45, -19.9);
  kit.place('cardboard_boxes', 10.3, -23.6, 0.2);
  kit.place('pallet_stack', 10.25, -26.4, Math.PI / 2);
  kit.place('oil_drum', 6.55, -17.6);
  kit.place('pallet', 7.1, -14.6, 0.3);
  steam.push(new THREE.Vector3(8.5, 0.05, -24.6));
  kit.box('metal_dark', 8.1, 8.9, 0, 0.02, -25, -24.2, { noBottom: true, cast: false }); // the grate it rises from

  // Tags and paper on both walls.
  const shopWall = wallFrame(kit, '+x', A.minX);
  const deliWall = wallFrame(kit, '-x', A.maxX);
  shopWall.overlay(mats.graffiti('VULTURES', 5, 0x8a1a22), -15.2, 1.7, 0.02, { w: 3.2, h: 1 });
  shopWall.overlay(mats.graffiti('188', 2), -26.2, 1.5);
  deliWall.overlay(mats.graffiti('HOLLIS', 9), -24.5, 1.6, 0.02, { w: 2.8, h: 1 });
  deliWall.overlay(mats.poster('show', 21), -17.4, 1.7);
  deliWall.overlay(mats.poster('torn', 22), -16.7, 1.6);
  deliWall.overlay(mats.poster('wanted', 23), -28.6, 1.6);

  // North end: a chained gate in chain-link with a tarp tied across it. Nothing gets past.
  const z = A.gateZ;
  chainlink(kit, A.minX, z, A.maxX, z, 0, 2.6, { spacing: 2.5 });
  kit.quad(['fabric', { color: 0x1f3a2c, doubleSide: true }], '+z', 8.5, 1.3, z + 0.03, 4.6, 2.1, { cast: true });
  kit.box('metal_dark', 8.42, 8.58, 1.05, 1.25, z + 0.04, z + 0.1, { cast: false });
  kit.solid(A.minX, A.maxX, 0, 2.6, z - 0.05, z + 0.05, { surface: 'metal', tag: 'alley-gate' });
  kit.solid(A.minX, A.maxX, 0, 8, z - 0.6, z, { tag: 'seal', playerOnly: true });
}

// -------------------------------------------------------------------------------------------------
// The cut: a strip of concrete between the deli and the cage, leading to the cage's west gate
// -------------------------------------------------------------------------------------------------

function buildCut(kit) {
  const { mats } = kit;
  kit.flat('concrete', CUT.minX, CUT.maxX, BOUNDS.minZ + 0.5, CUT.maxZ, LIFT.patch);
  kit.place('dumpster', 22.62, -16.4, Math.PI / 2);
  kit.place('trash_bags', 22.7, -19, 1.2);
  kit.place('milk_crates', 22.5, -30.6);
  kit.place('cardboard_boxes', 22.6, -31.9, 0.6);
  kit.place('pallet', 23.4, -13.6, 0.2);
  const wall = wallFrame(kit, '+x', CUT.minX);
  wall.overlay(mats.graffiti('KOQ', 4, 0x35e0ff), -22.5, 1.5);
  wall.overlay(mats.poster('ipx', 31), -13.2, 1.8);
  wall.overlay(mats.poster('show', 32), -12.5, 1.75);
}

// -------------------------------------------------------------------------------------------------
// The Cage
// -------------------------------------------------------------------------------------------------

function buildCage(kit) {
  const { mats } = kit;
  const C = CAGE;
  const K = C.court;
  const top = C.height;

  /**
   * One fenced side between two points: a concrete knee wall that stops walkers and low rounds, mesh
   * above it that stops only the player, so the court can be shot into and out of.
   */
  function side(x0, z0, x1, z1, plinthTop) {
    const alongX = z0 === z1;
    const t = 0.1;
    const bx0 = alongX ? x0 : x0 - t;
    const bx1 = alongX ? x1 : x1 + t;
    const bz0 = alongX ? z0 - t : z0;
    const bz1 = alongX ? z1 + t : z1;
    kit.block('concrete', bx0, bx1, 0, plinthTop, bz0, bz1, { tag: 'cage-plinth' });
    chainlink(kit, x0, z0, x1, z1, plinthTop, top);
    kit.solid(bx0, bx1, plinthTop, 8, bz0, bz1, { surface: 'metal', tag: 'cage-fence', playerOnly: true });
  }
  const south = C.plinth + KERB; // the avenue side stands on the back edge of the sidewalk
  side(C.minX, C.maxZ, C.southGate[0], C.maxZ, south);
  side(C.southGate[1], C.maxZ, C.maxX, C.maxZ, south);
  side(C.minX, C.minZ, C.maxX, C.minZ, C.plinth);
  side(C.maxX, C.minZ, C.maxX, C.maxZ, C.plinth);
  side(C.minX, C.minZ, C.minX, C.westGate[0], C.plinth);
  side(C.minX, C.westGate[1], C.minX, C.maxZ, C.plinth);

  // Gates: tall posts with a header pipe, the leaves chained back flat against the inside of the fence.
  for (const x of C.southGate) kit.cyl('metal_galv', x, 0, top + 0.5, C.maxZ, 0.07, 8);
  kit.pipe('metal_galv', [C.southGate[0], top + 0.4, C.maxZ], [C.southGate[1], top + 0.4, C.maxZ], 0.035);
  chainlink(kit, C.southGate[0] - 1.5, C.maxZ - 0.22, C.southGate[0] - 0.05, C.maxZ - 0.22, 0.12, 2.3, { spacing: 1.5 });
  chainlink(kit, C.southGate[1] + 0.05, C.maxZ - 0.22, C.southGate[1] + 1.5, C.maxZ - 0.22, 0.12, 2.3, { spacing: 1.5 });
  for (const z of C.westGate) kit.cyl('metal_galv', C.minX, 0, top + 0.5, z, 0.07, 8);
  kit.pipe('metal_galv', [C.minX, top + 0.4, C.westGate[0]], [C.minX, top + 0.4, C.westGate[1]], 0.035);
  chainlink(kit, C.minX + 0.22, C.westGate[0] - 1.5, C.minX + 0.22, C.westGate[0] - 0.05, 0.12, 2.3, { spacing: 1.5 });
  chainlink(kit, C.minX + 0.22, C.westGate[1] + 0.05, C.minX + 0.22, C.westGate[1] + 1.5, 0.12, 2.3, { spacing: 1.5 });
  // A threshold strip in each gateway, flush with the court.
  kit.flat('concrete', C.southGate[0], C.southGate[1], C.maxZ - 0.3, C.maxZ + 0.1, LIFT.wet);

  // The court: green acrylic, red keys, white lines.
  const y = LIFT.paint;
  const W = 0.07;
  const P = 'white';
  const cx = (K.x0 + K.x1) / 2;
  const cz = (K.z0 + K.z1) / 2;
  kit.flat(['court', { color: 0x2f4f46 }], C.minX + 0.1, C.maxX - 0.1, C.minZ + 0.1, C.maxZ - 0.1, LIFT.patch);
  const key = ['court', { color: 0x7a2e26 }];
  for (const end of [-1, 1]) {
    const base = end < 0 ? K.x0 : K.x1;
    const inward = -end;
    const hoop = base + inward * 1.25;
    const keyEnd = base + inward * 4.6;
    kit.flat(key, Math.min(base, keyEnd), Math.max(base, keyEnd), cz - 1.8, cz + 1.8, LIFT.wet);
    kit.paint(P, base, cz - 1.8, keyEnd, cz - 1.8, W, y);
    kit.paint(P, base, cz + 1.8, keyEnd, cz + 1.8, W, y);
    kit.paint(P, keyEnd, cz - 1.8, keyEnd, cz + 1.8, W, y);
    // Free-throw circle (the half outside the key) and the three-point arc.
    const a = end < 0 ? -Math.PI / 2 : Math.PI / 2;
    kit.paintArc(P, keyEnd, cz, 1.8, a, a + Math.PI, W, y, 12);
    const r = 6.2;
    const reach = Math.acos(0.02);
    const centre = end < 0 ? 0 : Math.PI;
    kit.paintArc(P, hoop, cz, r, centre - reach, centre + reach, W, y, 22);
    for (const s of [-1, 1]) kit.paint(P, base, cz + s * r, hoop + inward * 0.12, cz + s * r, W, y);
  }
  for (const z of [K.z0, K.z1]) kit.paint(P, K.x0, z, K.x1, z, W, y);
  for (const x of [K.x0, K.x1, cx]) kit.paint(P, x, K.z0, x, K.z1, W, y);
  kit.paintArc(P, cx, cz, 1.8, 0, Math.PI * 2, W, y, 26);

  kit.place('hoop', K.x0 - 0.35, cz, 0);
  kit.place('hoop', K.x1 + 0.35, cz, Math.PI);
  for (const x of [29.6, 35.25, 40.9]) kit.place('bleachers', x, C.minZ + 1.3, 0);
  kit.place('court_light', C.minX + 0.6, C.maxZ - 0.75, 0);
  kit.place('court_light', C.maxX - 0.6, C.minZ + 0.7, 0);
  kit.place('bench', 28.6, C.maxZ - 0.75, 0);
  kit.place('bench', 40.6, C.maxZ - 0.75, 0);
  kit.place('trash_can', 31.3, C.maxZ - 0.7);

  // The Vultures' corner of the court, around reel 3 at the centre circle.
  kit.place('sandbags', 34.1, -19.1, 0.25);
  kit.place('crate_wood', 32.7, -21.3, 0.5);
  kit.place('oil_drum', 32.5, -24.6);
  kit.place('motorbike', 31.3, -22.9, 1.25);
  kit.place('pallet_stack', 35.9, -26.4, 0.15);
  kit.place('milk_crates', 37.3, -24.7);
  kit.place('tire_stack', 37.8, -20.2);
  kit.place('tire_stack', 38.6, -20.9);
  kit.place('cardboard_boxes', 43.3, -17.2, 0.4);
  kit.place('shopping_cart', 28.4, -16.6, 0.7);
  kit.overlay(mats.graffiti('VULTURES', 11, 0x8a1a22), '+y', cx + 3.4, LIFT.decal, cz + 4.3, { w: 4.2, h: 1.2, yaw: 0.25 });
}

// -------------------------------------------------------------------------------------------------
// Vacant lot: the cut-through, and the mural on the pawn shop's side wall
// -------------------------------------------------------------------------------------------------

function buildMural(kit, wall) {
  const { mats } = kit;
  const brand = kit.G.config.brand;
  const W = 12;
  const H = 7.6;
  const px = kit.G.quality && kit.G.quality.name === 'test' ? 512 : 1024;
  const texture = mats.canvasTexture(px, Math.round((px * H) / W), (ctx, w, h) => {
    // Night-blue field with a gold record rising like a sun behind the El.
    const field = ctx.createLinearGradient(0, 0, 0, h);
    field.addColorStop(0, '#111a33');
    field.addColorStop(0.62, '#3b1420');
    field.addColorStop(1, '#0b0c12');
    ctx.fillStyle = field;
    ctx.fillRect(0, 0, w, h);
    const rx = w * 0.3;
    const ry = h * 0.56;
    const rr = h * 0.4;
    ctx.save();
    ctx.translate(rx, ry);
    for (let i = 0; i < 18; i++) {
      ctx.rotate((Math.PI * 2) / 18);
      ctx.fillStyle = i % 2 ? 'rgba(246,194,26,0.20)' : 'rgba(226,34,43,0.14)';
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(w, -h * 0.07);
      ctx.lineTo(w, h * 0.07);
      ctx.fill();
    }
    ctx.restore();
    ctx.fillStyle = '#d9a514';
    ctx.beginPath();
    ctx.arc(rx, ry, rr, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = 'rgba(60,38,4,0.55)';
    for (let r = rr * 0.42; r < rr * 0.97; r += rr * 0.045) {
      ctx.lineWidth = Math.max(1, rr * 0.008);
      ctx.beginPath();
      ctx.arc(rx, ry, r, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.fillStyle = '#8a1a22';
    ctx.beginPath();
    ctx.arc(rx, ry, rr * 0.34, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#0b0c12';
    ctx.beginPath();
    ctx.arc(rx, ry, rr * 0.045, 0, Math.PI * 2);
    ctx.fill();
    // The El in silhouette along the bottom: deck, girders, columns.
    ctx.fillStyle = '#07080c';
    ctx.fillRect(0, h * 0.78, w, h * 0.045);
    for (let x = w * 0.04; x < w; x += w * 0.115) {
      ctx.fillRect(x, h * 0.78, w * 0.014, h * 0.22);
      ctx.beginPath();
      ctx.moveTo(x - w * 0.03, h * 0.825);
      ctx.lineTo(x + w * 0.044, h * 0.825);
      ctx.lineTo(x + w * 0.014, h * 0.87);
      ctx.lineTo(x, h * 0.87);
      ctx.fill();
    }
    ctx.fillRect(0, h * 0.955, w, h * 0.045);
    // The mark and its address. No slogan.
    mats.drawIPX(ctx, w * 0.77, h * 0.6, h * 0.17, '#f4f2ec');
    ctx.fillStyle = '#f4f2ec';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = `600 ${Math.round(h * 0.05)}px ${brand.fonts.ui}`;
    ctx.fillText(brand.ipx.url, w * 0.77, h * 0.725);
    ctx.strokeStyle = '#f6c21a';
    ctx.lineWidth = Math.max(2, h * 0.012);
    ctx.strokeRect(h * 0.02, h * 0.02, w - h * 0.04, h - h * 0.04);
  });
  const material = new THREE.MeshStandardMaterial({ map: texture, roughness: 0.92, metalness: 0, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
  material.name = 'mural';
  wall.overlay({ material, w: W, h: H }, 18.4, 4.5, 0.02, { receive: true });
  // The name, sprayed big over the paint by a surer hand than the tags around it.
  wall.overlay(mats.graffiti('RULE', 1, 0xf6c21a), 15.6, 6.55, 0.035, { w: 6.4, h: 2.3 });
  wall.overlay(mats.graffiti('HOLLIS', 6, 0xf4f2ec), 22.9, 1.25, 0.03, { w: 2.6, h: 0.8 });
  wall.overlay(mats.graffiti('QUEENS', 8, 0x35e0ff), 12.6, 1.05, 0.03, { w: 2.2, h: 0.75 });
  wall.overlay(mats.graffiti('NO SLEEP', 14), 26.6, 1.4, 0.03);
}

function buildVacantLot(kit, rng) {
  const { mats } = kit;
  const V = VACANT;
  kit.flat('dirt', V.minX, V.maxX, V.minZ + 0.2, V.maxZ + 0.6, LIFT.patch);
  blob(kit, 'asphalt_wet', -8.4, 22.6, 2.2, 1.3, LIFT.wet, 0.4);
  blob(kit, 'asphalt_wet', -13.2, 16.2, 1.4, 1, LIFT.wet, 1.1);

  // Hoarding along the sidewalk with a gateway in it; the chain-link gate leaves stand open inside.
  const y0 = KERB - 0.15;
  for (const [x0, x1] of [[V.minX, V.gate[0]], [V.gate[1], V.maxX]]) {
    const F = hoarding(kit, x0, x1, FRONT_Z + 0.14, y0, 2.55, 0x23463c, '-z');
    const posters = ['show', 'ad', 'torn', 'wanted', 'show', 'ipx'];
    let u = x0 + 0.6;
    for (let i = 0; u < x1 - 0.6; i++) {
      const p = mats.poster(posters[(i + (x0 < -12 ? 0 : 3)) % posters.length], 40 + i);
      F.overlay(p, u + p.w / 2, 1.05 + p.h / 2 + rng.range(-0.06, 0.06), 0.012);
      u += p.w + rng.range(0.08, 0.5);
    }
    const bills = mats.sign({ text: 'POST NO BILLS', w: 1.5, h: 0.24, style: 'stencil', fg: 0xe6e4dc, lit: false });
    F.overlay(bills, (x0 + x1) / 2, 2.3, 0.012);
  }
  for (const x of V.gate) kit.cyl('metal_galv', x, 0, 2.75, FRONT_Z + 0.14, 0.06, 8);
  chainlink(kit, V.gate[0] - 1.62, FRONT_Z + 0.34, V.gate[0] - 0.04, FRONT_Z + 0.34, 0.1, 2.3, { spacing: 1.6 });
  chainlink(kit, V.gate[1] + 0.04, FRONT_Z + 0.34, V.gate[1] + 1.62, FRONT_Z + 0.34, 0.1, 2.3, { spacing: 1.6 });

  const scorch = mats.decal('scorch');
  kit.overlay(scorch, '+y', -11.2, LIFT.decal, 18.6, { w: 5.5, h: 4.2, yaw: 0.9 });
  kit.place('burned_car', -11.2, 18.6, 0.9);
  kit.place('tire_stack', -14.7, 14.1);
  kit.place('tire_stack', -13.8, 14.9);
  kit.place('mattress', -6.3, 14.3, 0.3);
  kit.place('shopping_cart', -7.4, 21.9, 1.2);
  kit.place('shopping_cart', -5.4, 23.4, 2.6);
  kit.place('shopping_cart', -14.2, 22.8, 0.5);
  kit.place('trash_bags', -5.1, 12.4, 0.2);
  kit.place('trash_bags', -15, 24.8, 1.4);
  kit.place('oil_drum', -8.3, 15.9);
  kit.place('cardboard_boxes', -14.8, 19, 0.3);
  kit.place('pallet', -13.3, 19.9, 0.5);
  kit.place('crate_wood', -6.2, 19.1, 0.4);
  kit.place('milk_crates', -8.9, 24.1);
  // A work light somebody left pointed at the wall.
  kit.place('floodlight_stand', -9.6, 13.3, Math.PI);

  buildMural(kit, wallFrame(kit, '+x', V.minX));
  const east = wallFrame(kit, '-x', V.maxX);
  east.overlay(mats.graffiti('VLTR', 3, 0x8a1a22), 15.2, 1.5, 0.02, { w: 2.4, h: 0.9 });
  east.overlay(mats.graffiti('JAMAICA AVE', 10), 19, 1.2);
  east.overlay(mats.poster('ad', 51), 13.1, 1.9);

  // Weeds along the walls: crossed blades of grass, nothing you could hide behind.
  const leaf = ['leaves', { doubleSide: true }];
  for (let i = 0; i < 26; i++) {
    const wallSide = rng.chance(0.5);
    const x = wallSide ? V.minX + rng.range(0.15, 0.9) : rng.range(V.minX + 1, V.maxX - 0.3);
    const z = wallSide ? rng.range(V.minZ + 1, V.maxZ) : rng.chance(0.5) ? rng.range(11.5, 12.4) : rng.range(21, 26);
    const h = rng.range(0.25, 0.6);
    const yaw = rng.range(0, Math.PI);
    for (const a of [yaw, yaw + Math.PI / 2]) {
      const blade = kit.quad(leaf, '+z', x, h / 2, z, rng.range(0.3, 0.6), h, { cast: false });
      blade.rotation.y = a;
    }
  }
}

// -------------------------------------------------------------------------------------------------
// Rear service lane
// -------------------------------------------------------------------------------------------------

function buildLane(kit, steam) {
  const { mats } = kit;
  const L = LANE;
  kit.flat(['asphalt', { color: 0x121316 }], -4, L.maxX, L.minZ, L.maxZ, LIFT.patch);
  kit.flat(['asphalt', { color: 0x232427 }], 2, 9, 28, 29.4, LIFT.wet);
  blob(kit, 'asphalt_wet', 14.5, 28.6, 3, 1.1, LIFT.paint);
  blob(kit, 'asphalt_wet', -1.5, 29.6, 2.2, 0.9, LIFT.paint);
  const grime = mats.decal('grime');
  const oil = mats.decal('oil');
  for (const [x, z] of [[-2.5, 27], [6, 30.2], [16, 30.4], [20, 27]]) kit.overlay(grime, '+y', x, LIFT.decal, z, { yaw: x * 0.7 });
  for (const [x, z] of [[-7.4, 29.4], [17.4, 29.9], [11, 29.5]]) kit.overlay(oil, '+y', x, LIFT.decal, z, { yaw: x });

  // Loading dock on the back of S3: a metre of concrete with rubber bumpers, steps at its west end,
  // a delivery shutter above it.
  const S3 = BUILDINGS.s3;
  const dock = { x0: 6.4, x1: 12.4, z0: S3.z1, z1: S3.z1 + 1.5, y: 1 };
  kit.block('concrete', dock.x0, dock.x1, 0, dock.y, dock.z0, dock.z1, { tag: 'dock' });
  kit.box('paint_yellow', dock.x0, dock.x1, dock.y - 0.12, dock.y + 0.004, dock.z1 - 0.004, dock.z1 + 0.004, { cast: false });
  for (const x of [7.4, 9.4, 11.4]) kit.box('rubber', x - 0.15, x + 0.15, 0.45, 0.9, dock.z1, dock.z1 + 0.09);
  kit.stairs('concrete', dock.x0 - 1, dock.x0, dock.z0, dock.z1, 0, dock.y, 4, '+x', { tag: 'dock' });
  const back = wallFrame(kit, '+z', S3.z1);
  back.box('roll_gate', 7.6, 11.2, dock.y, dock.y + 2.5, 0.02, 0.08);
  back.box('metal_dark', 7.5, 11.3, dock.y + 2.5, dock.y + 2.7, 0, 0.16);
  kit.place('pallet_stack', 11.7, dock.z0 + 0.7, 0, { y: dock.y });
  kit.place('cardboard_boxes', 7, dock.z0 + 0.6, 0.3, { y: dock.y });
  back.overlay(mats.graffiti('INC', 12, 0xf6c21a), 2.4, 1.5);
  back.overlay(mats.poster('torn', 61), 4.4, 1.7);
  back.overlay(mats.sign({ text: 'NO PARKING', sub: 'LOADING ZONE', w: 1.6, h: 0.6, style: 'stencil', fg: 0xe6e4dc, lit: false }), 16, 2.6, 0.02);

  kit.place('dumpster', -2.3, L.minZ + 0.62, 0);
  kit.place('dumpster', -1.7, L.maxZ - 0.62, 0);
  kit.place('trash_bags', 1.5, L.maxZ - 0.6, 0.3);
  kit.place('trash_bags', 21.1, L.minZ + 0.7, 1.1);
  kit.place('pallet_stack', -13.8, L.maxZ - 0.7, 0.1);
  kit.place('oil_drum', -15.2, 27.1);
  kit.place('oil_drum', -14.5, 27.8);
  kit.place('crate_wood', 4.5, L.maxZ - 0.6, 0.2);
  kit.place('milk_crates', 13.9, L.minZ + 0.45);
  kit.place('van', -7.6, 29.6, 0.04, { color: 0xb9b4a6 });
  kit.place('pickup', 17.4, 29.85, Math.PI, { seed: 6 });
  steam.push(new THREE.Vector3(1.8, 0.05, 28.4));
  kit.box('metal_dark', 1.4, 2.2, 0, 0.02, 28, 28.8, { noBottom: true, cast: false });
}

// -------------------------------------------------------------------------------------------------
// The parking lot
// -------------------------------------------------------------------------------------------------

function buildLot(kit, mats, rng) {
  const L = LOT;
  const P = 'white';
  const y = LIFT.paint;

  // Low wall along the sidewalk on both sides of the entrance, with a pipe rail on it.
  for (const [x0, x1] of [[L.minX, 26.05], [L.entry[1], L.maxX]]) {
    kit.block('concrete', x0, x1, 0, KERB + 0.62, L.minZ, L.minZ + 0.3, { tag: 'lot-wall' });
    kit.pipe('metal_galv', [x0 + 0.1, KERB + 0.98, L.minZ + 0.15], [x1 - 0.1, KERB + 0.98, L.minZ + 0.15], 0.028);
    for (let x = x0 + 0.1; x <= x1 - 0.05; x += (x1 - x0 - 0.2) / Math.max(1, Math.round((x1 - x0) / 2.2))) {
      kit.cyl('metal_galv', x, KERB + 0.62, KERB + 0.98, L.minZ + 0.15, 0.024, 6, { cast: false });
    }
  }

  // The booth, its barrier arm (up), the PARK sign on a pole across the entrance.
  kit.place('lot_booth', 27.3, 12.55, 0);
  kit.box('paint_yellow', 28.5, 28.72, 0, 1.1, 11.5, 11.72);
  kit.beam('paint_white', [28.61, 1.0, 11.61], [30.3, 3.6, 11.61], 0.07, 0.1);
  kit.beam('paint_red', [29.2, 1.92, 11.6], [29.75, 2.77, 11.6], 0.075, 0.105, { cast: false });
  kit.solid(28.45, 28.77, 0, 1.1, 11.45, 11.77, { surface: 'metal', tag: 'lot-gate' });
  const poleX = L.entry[1] + 0.35;
  kit.cyl('metal_dark', poleX, 0, 5.6, 11.65, 0.09, 8);
  kit.solid(poleX - 0.12, poleX + 0.12, 0, 5.6, 11.53, 11.77, { surface: 'metal', tag: 'lot-sign' });
  kit.box('metal_dark', poleX - 0.1, poleX + 0.1, 3.9, 5.5, 10.75, 12.55);
  const park = mats.sign({ text: 'PARK', sub: '24 HR', w: 1.7, h: 1.5, style: 'neon', fg: 0x35e0ff, glow: 0x35e0ff });
  kit.overlay(park, '-x', poleX - 0.11, 4.7, 11.65);
  kit.overlay(park, '+x', poleX + 0.11, 4.7, 11.65);
  kit.lamp(poleX - 0.7, 4.7, 11.65, 'neon', 0x35e0ff, 12, 9);

  // Bays: a row against S3, a row down the middle, a few against the south wall.
  const west = [14.2, 16.8, 19.4, 22, 24.6];
  for (const z of west) kit.paint(P, 22.4, z, 27.4, z, 0.1, y);
  kit.paint(P, 27.4, west[0], 27.4, west[west.length - 1], 0.1, y);
  const mid = [14.5, 17.1, 19.7, 22.3, 24.9];
  for (const z of mid) kit.paint(P, 34, z, 39, z, 0.1, y);
  kit.paint(P, 34, mid[0], 34, mid[mid.length - 1], 0.1, y);
  const south = [23.2, 25.8, 28.4, 31, 33.6];
  for (const x of south) kit.paint(P, x, 29.2, x, 34, 0.1, y);
  // Wheel stops at the head of the wall-side bays.
  for (let i = 0; i < west.length - 1; i++) kit.box('concrete', 22.5, 22.72, 0, 0.12, west[i] + 0.4, west[i + 1] - 0.4, { noBottom: true });
  const arrow = mats.decal('arrow');
  kit.overlay(arrow, '+y', 30.4, LIFT.decal, 14.2, { yaw: Math.PI });
  kit.overlay(arrow, '+y', 33.2, LIFT.decal, 14.2);
  const oil = mats.decal('oil');
  const crack = mats.decal('crack');
  for (const [x, z] of [[24.9, 15.5], [24.9, 20.7], [36.5, 18.4], [36.5, 21], [26.8, 31.6], [42, 23]]) kit.overlay(oil, '+y', x, LIFT.decal, z, { yaw: x + z });
  for (const [x, z] of [[30.5, 20], [41.5, 17], [31.5, 27.5], [43.5, 26]]) kit.overlay(crack, '+y', x, LIFT.decal, z, { yaw: x, w: crack.w * 1.6 });
  blob(kit, 'asphalt_wet', 30.6, 22.6, 2.6, 1.7, LIFT.wet, 0.5);
  blob(kit, 'asphalt_wet', 42.3, 19.6, 2.2, 1.5, LIFT.wet, 1.2);
  blob(kit, 'asphalt_wet', 35.2, 30.2, 2.4, 1.2, LIFT.wet);

  // Cars. Yaw π points a nose west, −π/2 south.
  kit.place('sedan', 24.95, 15.5, Math.PI, { seed: 2 });
  kit.place('suv', 25.05, 18.1, Math.PI, { seed: 4 });
  kit.place('pickup', 25.2, 23.3, 0, { seed: 6 });
  kit.place('taxi', 36.5, 15.8, Math.PI);
  kit.place('van', 36.6, 18.4, 0, { color: 0x3a4a5a });
  kit.place('sedan', 36.5, 23.6, Math.PI, { seed: 0 });
  kit.place('sedan', 24.5, 31.6, -Math.PI / 2, { seed: 3 });
  kit.place('sedan', 29.7, 31.55, Math.PI / 2, { seed: 5 });

  // Loose cover between the lane mouth and the truck.
  kit.place('pallet_stack', 33.2, 26.6, 0.2);
  kit.place('oil_drum', 34.4, 27.3);
  kit.place('jersey_barrier', 31.4, 28.6, Math.PI / 2 + 0.15);
  kit.place('pallet_stack', 34.6, 32.8, 0.1);
  kit.place('tire_stack', 39.6, 26.4);
  kit.place('jersey_barrier', 41.6, 25.9, 0.1);
  kit.place('dumpster', 44.9, 23.6, Math.PI / 2);
  kit.place('trash_bags', 44.7, 32.9, 0.6);
  kit.place('shopping_cart', 40.6, 14.9, 0.8);
  kit.place('traffic_barrel', 30.6, 16.9);
  kit.place('traffic_barrel', 31.4, 17.6);
  kit.place('crate_wood', 42.4, 14.4, 0.3);

  // The billboard over the north-east corner, two light poles, and the truck in the south-east corner.
  kit.place('billboard', 40.7, 12.4, 0);
  kit.place('street_lamp', 39.3, 13.95, 0);
  kit.place('street_lamp', 30.9, 33.45, Math.PI);
  const truck = kit.place('ipx_truck', 41.3, 29.7, 0);

  // East wall art: a faded stencil for the towing company that used to own the lot.
  const east = wallFrame(kit, '-x', BOUNDS.maxX);
  east.overlay(mats.sign({ text: 'VIOLATORS TOWED', sub: 'AT OWNER\'S EXPENSE', w: 3.4, h: 0.9, style: 'stencil', fg: 0xe6e4dc, lit: false }), 19.5, 2.4, 0.02);
  east.overlay(mats.graffiti('188', 16, 0xff3d9a), 26.4, 1.4);
  const southWall = wallFrame(kit, '-z', BOUNDS.maxZ);
  southWall.overlay(mats.graffiti('QUEENS', 15), 27.2, 1.5, 0.02, { w: 2.8, h: 0.95 });
  southWall.overlay(mats.poster('ipx', 71), 38.2, 1.8);
  return truck;
}
