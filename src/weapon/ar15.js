// The AR-15: a flat-top carbine in black anodised aluminium, worn bright along its edges. An
// eight-sided free-float handguard slotted on its flats, one rail from the charging handle to the
// front sight, flip-up irons (an aperture at the back, a post between two ears at the front), a thin
// barrel ending in a birdcage, a straight 30-round magazine that sweeps forward, an A2 grip and a
// collapsed stock on its buffer tube. The ejection port is on the right, its cover hanging open: the
// bare bolt carrier shows in it.
//
// Gun space: origin on the bore axis at the back of the upper receiver, −Z down the barrel, +Y up,
// +X right. Profiles are [s, y] with s = distance forward of the origin.

import * as THREE from 'three';
import { makePose } from './arms.js';
import { FINISH, Soup, block, fillet, lathe, loft, paint, pin, prism, rod, sweep } from './build.js';
import { FINISH_BLUED } from './material.js';
import { POSES, gunPose, handKey, sampleCurve, sampleTrack, shiftKey, turnKey } from './handling.js';

const SIGHT_Y = 0.066; // height of the sight line over the bore
const RAIL_Y = 0.031; // top of the rail
const DECK_Y = -0.016; // where the upper receiver sits on the lower
const REAR_S = 0.031; // rear aperture
const FRONT_S = 0.431; // front post
const MUZZLE_S = 0.585;
const PORT = [0.112, 0.172]; // ejection port, back and front
const HANDLE_TRAVEL = 0.072; // the charging handle, all the way back
const PITCH = 0.0102; // rail: one land and one slot
const LAND = 0.0052;

// The magazine drops straight out of the well, then sweeps forward.
const magS = (y) => 0.149 + (y < -0.07 ? 1.15 * (y + 0.07) ** 2 : 0);

/**
 * Loose flat faces gathered into one geometry, for the shapes the kit's solids would waste triangles
 * on. A face is a convex polygon of [x, y, z] corners, wound here to look along `out`; `worn` tags it
 * as a chamfer, which takes the paint's wear.
 */
function facets() {
  const pos = [];
  const tag = [];
  return {
    add(corners, out, worn = false) {
      const [a, b, c] = corners;
      const nx = (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]);
      const ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]);
      const nz = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
      const flip = nx * out[0] + ny * out[1] + nz * out[2] < 0;
      for (let i = 1; i < corners.length - 1; i++) {
        for (const p of flip ? [a, corners[i + 1], corners[i]] : [a, corners[i], corners[i + 1]]) {
          pos.push(p[0], p[1], p[2]);
          tag.push(worn ? 1 : 0);
        }
      }
      return this;
    },
    build() {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
      geo.setAttribute('tag', new THREE.BufferAttribute(new Float32Array(tag), 1));
      return geo;
    },
  };
}

/**
 * A flat patch lying on a face of the gun, a hair proud of it: the outline [s, v] is laid on the plane
 * through `at` ([x, y]) that faces `out` ([x, y]), v running along `across`. Painted dark it reads as
 * a slot cut into the face.
 */
function patch(pts, at, out, across = [-out[1], out[0]]) {
  return facets()
    .add(pts.map(([s, v]) => [at[0] + across[0] * v, at[1] + across[1] * v, -s]), [out[0], out[1], 0])
    .build();
}

/** Outline of a slot from s0 to s1, `half` wide either side of v, its corners cut by `c`. */
function slot(s0, s1, half, v = 0, c = half * 0.6) {
  return [[s0 + c, v - half], [s1 - c, v - half], [s1, v - half + c], [s1, v + half - c], [s1 - c, v + half], [s0 + c, v + half], [s0, v + half - c], [s0, v - half + c]];
}

/** Outline of a small disc: the head of a pin. */
function disc(s, v, r, n = 6) {
  return Array.from({ length: n }, (_, i) => [s + r * Math.cos((i / n) * Math.PI * 2), v + r * Math.sin((i / n) * Math.PI * 2)]);
}

/**
 * A stretch of accessory rail: `count` lands of dovetail section, PITCH apart, the first starting at
 * s0, their tops at RAIL_Y. They are open underneath (they stand on a base); the chamfers take the wear.
 */
function rail(s0, count) {
  const f = facets();
  const half = 0.0106;
  const flat = 0.0089;
  const waist = RAIL_Y - 0.0017;
  const foot = RAIL_Y - 0.0034;
  const ring = (z) => [[-half, foot, z], [-half, waist, z], [-flat, RAIL_Y, z], [flat, RAIL_Y, z], [half, waist, z], [half, foot, z]];
  for (let i = 0; i < count; i++) {
    const a = ring(-(s0 + i * PITCH));
    const b = ring(-(s0 + i * PITCH + LAND));
    f.add([a[2], a[3], b[3], b[2]], [0, 1, 0]);
    f.add([a[1], a[2], b[2], b[1]], [-1, 1, 0], true);
    f.add([a[3], a[4], b[4], b[3]], [1, 1, 0], true);
    f.add([a[0], a[1], b[1], b[0]], [-1, 0, 0]);
    f.add([a[4], a[5], b[5], b[4]], [1, 0, 0]);
    f.add(a, [0, 0, 1]);
    f.add(b, [0, 0, -1]);
  }
  return f.build();
}

export function buildAr15(material, def) {
  // Hard-anodised aluminium: a satin near-black that shows the light as soft shapes, bare metal
  // where the edges have rubbed through. Furniture is black polymer.
  const wear = paint(0x7b8189, 0.32, 1);
  const P = {
    upper: paint(0x474a50, 0.48, 0.9, { wear, finish: FINISH_BLUED }),
    lower: paint(0x44474d, 0.5, 0.9, { wear, finish: FINISH_BLUED }),
    guard: paint(0x40434a, 0.55, 0.9, { wear, finish: FINISH_BLUED }),
    dark: paint(0x34363b, 0.46, 0.9, { wear }),
    steel: paint(0x36383d, 0.42, 0.9, { wear }), // phosphated: barrel and muzzle
    bare: paint(0xa6abb2, 0.28, 1, { finish: FINISH.brushed }),
    shade: paint(0x70757c, 0.34, 1), // the round of the carrier turning away from the light
    notch: paint(0x4a4d52, 0.4, 1),
    polymer: paint(0x16171a, 0.58, 0),
    grip: paint(0x17181b, 0.66, 0, { finish: FINISH.checker }),
    black: paint(0x050506, 0.92, 0),
    mag: paint(0x5c5f65, 0.42, 0.85, { wear, finish: FINISH_BLUED }),
    brass: paint(0xcaa23d, 0.28, 1),
    copper: paint(0xb5683a, 0.3, 1),
    dot: paint(0xf2f0e4, 0.6, 0, { glow: 0.55 }),
  };
  const side = (x) => [[x, 0], [Math.sign(x), 0], [0, 1]]; // a patch on a flat side of the gun: [s, y] at x

  // ---------------------------------------------------------------------------------------------
  // Body: everything that never moves relative to the receiver
  // ---------------------------------------------------------------------------------------------
  const body = new Soup();

  // Upper receiver: flat sides rounding over into the riser the rail stands on.
  const upper = (s, w, top) => ({ c: [0, DECK_Y, -s], w, h: 0, top, bot: 0.0004, exp: 3.6 });
  body.add(loft([upper(0, 0.0274, 0.0335), upper(0.003, 0.029, 0.0345), upper(0.193, 0.029, 0.0345), upper(0.198, 0.027, 0.0328)], 12), P.upper, { crease: 0.9 });
  body.add(block(0.0105, 0.198, 0.0145, 0.0278, -0.0092, 0.0092, 0.001), P.upper);
  body.add(rail(0.0145 + 4 * PITCH, 14), P.dark);

  // Lower receiver: the buffer ring at the back, the grip boss, the trigger pocket.
  const lower = fillet(
    [
      [-0.021, -0.005],
      [-0.021, -0.027, 0.004],
      [-0.008, -0.041, 0.004],
      [0.002, -0.048],
      [0.036, -0.048],
      [0.039, -0.072],
      [0.0495, -0.072],
      [0.0515, -0.048],
      [0.115, -0.048],
      [0.115, DECK_Y],
      [0.0005, DECK_Y],
      [0.0005, -0.005],
    ],
    2,
  );
  body.add(prism(lower, 0.0265, { bevel: 0.001 }), P.lower);
  body.add(lathe([[-0.021, 0.017], [0.0005, 0.017]], 12), P.lower, { crease: 0.9 });
  // The magazine well is a little wider: its fence line runs up the back toward the bolt catch,
  // the pivot lug juts out at the top of its front.
  const well = fillet(
    [[0.1125, -0.0708], [0.1862, -0.0786], [0.1905, -0.0745], [0.1905, -0.0335, 0.002], [0.197, -0.03, 0.002], [0.197, DECK_Y], [0.125, DECK_Y], [0.1105, -0.036, 0.004], [0.1105, -0.052]],
    2,
  );
  body.add(prism(well, 0.0285, { bevel: 0.001 }), P.lower);
  // Its mouth, seen when the magazine is out.
  const mouth = (s) => -0.0711 - (s - 0.1125) * 0.1058;
  const lips = [[-0.0119, mouth(0.1165), -0.1165], [0.0119, mouth(0.1165), -0.1165], [0.0119, mouth(0.184), -0.184], [-0.0119, mouth(0.184), -0.184]];
  body.add(facets().add(lips, [0, -1, 0]).build(), P.black, { ao: 0 });

  // Takedown and pivot pins right through; the hammer and trigger pins show as heads.
  body.add(pin(0.014, -0.0235, 0.0031, -0.0141, 0.0146, 6), P.dark);
  body.add(pin(0.178, -0.0245, 0.0031, -0.0151, 0.0156, 6), P.dark);
  for (const x of [-0.01336, 0.01336]) {
    for (const [s, y] of [[0.0895, -0.0305], [0.068, -0.0385]]) body.add(patch(disc(s, y, 0.0019), ...side(x)), P.dark);
  }

  // Left side: bolt catch paddle, fire selector (turned back: automatic), the magazine catch's bar.
  const paddle = [[0.107, -0.031], [0.115, -0.031], [0.1152, -0.021], [0.1195, -0.0172], [0.1195, -0.0032], [0.1052, -0.0032], [0.1052, -0.0172], [0.107, -0.021]];
  body.add(prism(paddle, 0.0038, { x: -0.0147, bevel: 0.0007 }), P.dark);
  for (const y of [-0.006, -0.009, -0.012, -0.015]) body.add(patch([[0.1068, y - 0.0006], [0.118, y - 0.0006], [0.118, y + 0.0006], [0.1068, y + 0.0006]], ...side(-0.0167)), P.black, { ao: 0 });
  body.add(pin(0.04, -0.031, 0.0042, -0.0156, -0.013, 8), P.dark);
  body.add(prism([[0.018, -0.0288], [0.04, -0.0272], [0.0436, -0.031], [0.04, -0.0348], [0.018, -0.0332]], 0.0022, { x: -0.0162, bevel: 0.0005 }), P.dark);
  body.add(block(0.113, 0.128, -0.041, -0.036, -0.01505, -0.0141, 0.0004), P.dark);

  // Right side: the magazine button behind its fence, the end of the selector's shaft.
  body.add(block(0.094, 0.1105, -0.0395, -0.0235, 0.013, 0.0146, 0.0006), P.lower);
  body.add(pin(0.1025, -0.031, 0.0043, 0.013, 0.0176, 8), P.dark);
  body.add(patch(disc(0.04, -0.031, 0.0036, 8), ...side(0.01336)), P.dark);

  // Right side of the upper: the ejection port in its seat, the cover hanging open under it, the
  // brass deflector and the forward assist behind.
  body.add(block(0.106, 0.178, -0.0135, 0.0075, 0.0125, 0.0153, 0.0008), P.upper);
  body.add(patch(slot(PORT[0], PORT[1], 0.0078, -0.0025, 0.0025), ...side(0.01538)), P.black, { ao: 0 });
  body.add(rod([0.0162, -0.0145, -0.104], [0.0162, -0.0145, -0.18], 0.0016, 0.0016, 6), P.dark, { crease: 0.9 });
  body.add(block(0.1095, 0.1755, -0.0335, -0.0145, 0.0147, 0.0161, 0.0005), P.upper);
  body.add(block(0.1175, 0.1675, -0.03, -0.019, 0.0161, 0.0168, 0.0004), P.dark);
  body.add(loft([{ c: [0.0176, -0.002, -0.1072], w: 0.0072, h: 0.014, exp: 20 }, { c: [0.0147, -0.002, -0.092], w: 0.0006, h: 0.009, exp: 20 }], 4), P.upper);
  body.add(rod([0.0118, -0.0015, -0.102], [0.0212, -0.0015, -0.066], 0.0068, 0.0066, 8, [false, true]), P.upper, { crease: 0.9 });
  body.add(rod([0.0212, -0.0015, -0.066], [0.0232, -0.0015, -0.0585], 0.006, 0.006, 8, [false, true]), P.dark, { crease: 0.9 });

  // Trigger guard.
  body.add(prism([[0.046, -0.0735], [0.1135, -0.0728], [0.1135, -0.0703], [0.046, -0.071]], 0.0135, { bevel: 0.0006 }), P.dark);

  // Pistol grip: raked back, a finger rest on the front strap, a beavertail up under the receiver.
  const gripW = [0.027, 0.029, 0.0298, 0.03, 0.0298, 0.0285];
  const gripBack = [0.026, 0.0215, 0.0195, 0.0195, 0.0195, 0.019];
  const gripFront = [0.0195, 0.0205, 0.0235, 0.02, 0.0195, 0.019];
  body.add(
    sweep(
      [[0.0265, -0.046], [0.0225, -0.059], [0.0165, -0.075], [0.0085, -0.097], [-0.001, -0.119], [-0.0105, -0.14]],
      (t, i) => ({ w: gripW[i], d: 0.04, plus: gripBack[i], minus: gripFront[i], exp: 2.8 }),
      12,
      [false, true],
    ),
    P.grip,
    { crease: 0.9 },
  );

  // Buffer tube with its castle nut, and the stock collapsed along it: a sleeve round the tube, a
  // slimmer butt under it with an open triangle, grooves down the sleeve, a pad, the length latch.
  body.add(lathe([[-0.034, 0.0186], [-0.021, 0.0186]], 12), P.dark, { crease: 0.5 });
  body.add(lathe([[-0.205, 0.0146], [-0.034, 0.0146]], 10, { caps: [true, false] }), P.upper, { crease: 0.9 });
  const sleeve = fillet([[-0.045, -0.0235], [-0.045, 0.016], [-0.05, 0.0215], [-0.2, 0.0215, 0.004], [-0.212, 0.014], [-0.212, -0.0235]], 2);
  body.add(prism(sleeve, 0.035, { bevel: 0.004 }), P.polymer, { crease: 0.5 });
  const butt = fillet(
    [[-0.214, -0.097, 0.004], [-0.197, -0.097], [-0.085, -0.0315, 0.004], [-0.058, -0.0315], [-0.058, -0.018], [-0.204, -0.018], [-0.204, 0.0165], [-0.2185, 0.0125, 0.003], [-0.2215, -0.089, 0.004]],
    2,
  );
  body.add(prism(butt, 0.028, { bevel: 0.003, holes: [[[-0.118, -0.0245], [-0.2, -0.073], [-0.2, -0.0245]]] }), P.polymer, { crease: 0.5 });
  for (const x of [-0.01762, 0.01762]) {
    for (const y of [-0.012, 0.009]) body.add(patch(slot(-0.192, -0.066, 0.0016, y), ...side(x)), P.black, { ao: 0 });
  }
  body.add(block(-0.2265, -0.2205, -0.091, 0.012, -0.0125, 0.0125, 0.0015), P.black);
  body.add(prism([[-0.1, -0.0315], [-0.062, -0.0315], [-0.064, -0.037], [-0.096, -0.041]], 0.012, { bevel: 0.0006 }), P.polymer);

  // Handguard: an eight-sided tube, taller above the bore where the gas tube runs; its top flat
  // carries the rail on from the receiver. A clamp collar at the back, slots along the other flats.
  const GUARD = { r: 0.0212, top: 0.0262 };
  const guard = (s, k = 1) => ({ c: [0, 0, -s], w: GUARD.r * 2 * k, h: 0, top: GUARD.top * k, bot: GUARD.r * k });
  body.add(loft([guard(0.198, 0.9), guard(0.2015, 1.04), guard(0.221, 1.04), guard(0.2225), guard(0.4415), guard(0.446, 0.93), guard(0.446, 0.84)], 8, [false, false]), P.guard, { crease: 0.5 });
  body.add(loft([guard(0.446, 0.84), guard(0.39, 0.8)], 8, [false, true], true), P.black, { crease: 0.5, ao: 0 });
  body.add(block(0.1985, 0.446, 0.0235, 0.0278, -0.0092, 0.0092, 0.001), P.guard);
  body.add(rail(0.0145 + 18 * PITCH, 22), P.dark);
  for (const s of [0.2065, 0.2165]) body.add(pin(s, -0.0145, 0.0024, -0.0152, 0.0152, 6), P.dark);
  const corner = (i) => {
    const a = Math.PI / 8 + (i * Math.PI) / 4;
    return [Math.cos(a) * GUARD.r, Math.sin(a) * (Math.sin(a) > 0 ? GUARD.top : GUARD.r)];
  };
  for (const i of [0, 2, 3, 4, 5, 6, 7]) {
    const a = corner(i);
    const b = corner(i + 1);
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const across = [(b[0] - a[0]) / len, (b[1] - a[1]) / len];
    const out = [across[1], -across[0]];
    const at = [(a[0] + b[0]) / 2 + out[0] * 0.0002, (a[1] + b[1]) / 2 + out[1] * 0.0002];
    for (let s = 0.232; s < 0.41; s += 0.042) body.add(patch(slot(s, s + 0.03, 0.0034), at, out, across), P.black, { ao: 0 });
  }

  // Barrel and the birdcage on its muzzle: five slots, closed underneath.
  body.add(lathe([[0.392, 0.0079], [0.542, 0.0079]], 10, { caps: [false, false] }), P.steel, { crease: 0.9 });
  body.add(
    lathe([[0.5395, 0.0074], [0.5425, 0.0098], [0.548, 0.0098], [0.549, 0.0109], [0.5795, 0.0109], [0.5842, 0.0094], [MUZZLE_S + 0.0004, 0.0074]], 12, { caps: [false, false] }),
    P.steel,
    { crease: 0.5 },
  );
  body.add(lathe([[MUZZLE_S + 0.0004, 0.0074], [0.579, 0.0048], [0.553, 0.0042]], 12, { caps: [false, true], inside: true }), P.black, { crease: 0.9, ao: 0 });
  for (const deg of [90, 30, 150, 210, 330]) {
    const out = [Math.cos((deg * Math.PI) / 180), Math.sin((deg * Math.PI) / 180)];
    body.add(patch(slot(0.5535, 0.5775, 0.0017), [out[0] * 0.01068, out[1] * 0.01068], out), P.black, { ao: 0 });
  }

  // Rear sight, flipped up: a clamp on the rail, the leaf with its aperture, the windage knob.
  body.add(block(0.0185, 0.0475, 0.0262, 0.0358, -0.0124, 0.0124, 0.0012), P.dark);
  body.add(pin(0.033, 0.0308, 0.0034, -0.0168, -0.0124, 6), P.dark);
  const leaf = [[-0.0036, 0.0352], [0.0036, 0.0352]];
  for (let i = 0; i <= 14; i++) {
    const a = -1.063 + (i / 14) * (Math.PI + 2.126); // a ring on a stem
    leaf.push([0.0074 * Math.cos(a), SIGHT_Y + 0.0074 * Math.sin(a)]);
  }
  const across = new THREE.Matrix4().makeRotationY(-Math.PI / 2); // a profile drawn in [x, y], made solid along the bore
  body.add(prism(leaf, 0.0042, { holes: [disc(0, SIGHT_Y, 0.0052, 16)] }), P.dark, { m: across.clone().setPosition(0, 0, -REAR_S) });
  body.add(pin(REAR_S, 0.0358, 0.0026, -0.0124, 0.0124, 6), P.dark);
  body.add(pin(REAR_S, 0.0485, 0.0034, 0.0036, 0.0102, 6), P.dark);

  // Front sight: the same clamp, a post between two ears.
  body.add(block(0.4185, 0.4445, 0.0262, 0.0378, -0.0132, 0.0132, 0.0012), P.dark);
  body.add(pin(0.4315, 0.0312, 0.0036, -0.0178, -0.0132, 6), P.dark);
  body.add(block(0.4265, 0.4365, 0.0378, 0.0475, -0.0096, 0.0096, 0.0008), P.dark);
  const ear = fillet([[0.4262, 0.0475], [0.4368, 0.0475], [0.4368, 0.066], [0.4345, 0.0722, 0.002], [0.4285, 0.0722, 0.002], [0.4262, 0.066]], 1);
  for (const x of [-0.0085, 0.0085]) body.add(prism(ear, 0.0022, { x, bevel: 0.0004 }), P.dark);
  body.add(rod([0, 0.0475, -FRONT_S], [0, SIGHT_Y, -FRONT_S], 0.0015, 0.0013, 6, [false, true]), P.dark);
  body.add(block(FRONT_S - 0.0019, FRONT_S - 0.0014, SIGHT_Y - 0.0075, SIGHT_Y - 0.0003, -0.0008, 0.0008), P.dot);

  // ---------------------------------------------------------------------------------------------
  // Moving parts
  // ---------------------------------------------------------------------------------------------

  // Charging handle: the T at the back of the upper, its latch on the left, the shaft that runs in under the rail.
  const handle = new Soup();
  handle.add(prism([[-0.0125, 0.0168], [0.0015, 0.0168], [0.0015, 0.0222], [-0.0005, 0.0238], [-0.0105, 0.0238], [-0.0125, 0.0222]], 0.043, { bevel: 0.0014 }), P.dark);
  handle.add(block(0, 0.118, 0.0172, 0.0224, -0.0055, 0.0055), P.dark);
  handle.add(block(-0.004, 0.0065, 0.0174, 0.0232, -0.0245, -0.0165, 0.0008), P.dark);

  // Bolt carrier, as much of it as the port shows: bare steel, the forward assist's notches, two gas vents.
  const bolt = new Soup();
  bolt.add(patch(slot(PORT[0] + 0.0006, PORT[1] - 0.0006, 0.007, -0.0025, 0.002), ...side(0.01562)), P.bare);
  for (const y of [-0.0083, 0.0033]) bolt.add(patch(slot(PORT[0] + 0.0028, PORT[1] - 0.0028, 0.0012, y, 0.0008), ...side(0.01567)), P.shade, { ao: 0 });
  for (let i = 0; i < 6; i++) {
    const s = 0.1165 + i * 0.0036;
    bolt.add(patch([[s, -0.0068], [s + 0.0015, -0.0068], [s + 0.0015, -0.0022], [s, -0.0022]], ...side(0.01573)), P.notch, { ao: 0 });
  }
  for (const s of [0.149, 0.157]) bolt.add(patch(disc(s, -0.0035, 0.0012), ...side(0.01573)), P.black, { ao: 0 });

  // Trigger, modelled around its pin: the bow hangs ahead of it.
  const trigger = new Soup();
  trigger.add(
    prism(
      [[0.002, -0.004], [0.0135, -0.004], [0.0138, -0.0105], [0.0118, -0.0185], [0.0128, -0.0262], [0.0105, -0.027], [0.0078, -0.0185], [0.0066, -0.0105], [0.002, -0.0085]],
      0.0062,
      { bevel: 0.0008 },
    ),
    P.dark,
  );

  // Magazine: an aluminium box with two pressed ribs a side, a seam down the back, a polymer floor plate.
  const mag = new Soup();
  const magLine = [-0.014, -0.045, -0.075, -0.1, -0.125, -0.15, -0.172, -0.19].map((y) => [magS(y), y]);
  mag.add(sweep(magLine, () => ({ w: 0.0226, d: 0.0605, exp: 6 }), 12, [true, false]), P.mag, { crease: 0.8 });
  for (const off of [-0.0125, 0.011]) {
    mag.add(sweep(magLine.slice(2).map(([s, y]) => [s + off, y]), () => ({ w: 0.0276, d: 0.0064, exp: 2.4 }), 6, [true, true]), P.mag, { crease: 0.5 });
  }
  mag.add(sweep(magLine.slice(1).map(([s, y]) => [s - 0.0302, y]), () => ({ w: 0.0075, d: 0.0026, exp: 20 }), 4, [true, true]), P.mag);
  mag.add(sweep([[magS(-0.189), -0.189], [magS(-0.197) + 0.0004, -0.197]], () => ({ w: 0.0248, d: 0.064, exp: 6 }), 12, [true, true]), P.polymer, { crease: 0.8 });

  // The round on top of a loaded magazine (hidden inside the receiver when the magazine is in).
  const round = new Soup();
  round.add(lathe([[0.1205, 0.0042], [0.1215, 0.0048], [0.157, 0.0048], [0.1605, 0.0032]], 8, { y: -0.0112, caps: [true, false] }), P.brass, { crease: 0.9 });
  round.add(lathe([[0.1605, 0.0032], [0.1665, 0.0029], [0.176, 0.0008]], 8, { y: -0.0112, caps: [false, true] }), P.copper, { crease: 0.9 });

  // ---------------------------------------------------------------------------------------------
  // Assembly
  // ---------------------------------------------------------------------------------------------
  const root = new THREE.Group();
  root.name = 'ar15';
  const part = (soup, name) => {
    const mesh = new THREE.Mesh(soup.build(), material);
    mesh.name = `ar15-${name}`;
    mesh.frustumCulled = false; // always in view, and close enough to the near plane to be culled wrongly
    return mesh;
  };
  const meshes = {
    body: part(body, 'body'),
    handle: part(handle, 'handle'),
    bolt: part(bolt, 'bolt'),
    trigger: part(trigger, 'trigger'),
    mag: part(mag, 'mag'),
    round: part(round, 'round'),
  };
  meshes.trigger.position.set(0, -0.0385, -0.068);
  // The carrier is drawn from the back edge of the port: as it runs back, less and less of it shows.
  meshes.bolt.geometry.translate(0, 0, PORT[0]);
  meshes.bolt.position.z = -PORT[0];
  meshes.mag.add(meshes.round);
  root.add(meshes.body, meshes.handle, meshes.bolt, meshes.trigger, meshes.mag);

  // ---------------------------------------------------------------------------------------------
  // Handling: where the hands go and how the reload is played
  // ---------------------------------------------------------------------------------------------
  const R = def.reload;

  // Firing hand high on the grip, its web under the beavertail: the index finger lies along the
  // receiver over the guard, goes through it for the trigger, presses in on the magazine button.
  const firing = (index) => makePose({ index, middle: [1.25, 1.45, 0.75, 0.02], ring: [1.3, 1.5, 0.8, 0], pinky: [1.35, 1.5, 0.8, -0.04], thumb: [-0.25, 0.8, 1.6, 0.7, 0.7] });
  const hold = firing([0.1, 0.2, 0.15, 0.35]);
  const squeeze = firing([0.42, 0.95, 0.5, 0.12]);
  const press = firing([0, 0.2, 0.8, 0.5]);
  const grip = handKey(1, 'gun', [0.0152, -0.088, -0.001], [-1, 0, -0.15], [0.08, -0.12, -0.99], hold);
  const gripFire = { ...grip, pose: squeeze };
  const gripPress = { ...grip, pose: press };
  // Support hand wrapped under the handguard, fingers up its right flats, thumb forward along the left.
  const cup = makePose({ index: [0.99, 1.31, 0.29, 0.2], middle: [1.16, 1.34, 0.34, 0], ring: [1.32, 1.12, 0.46, 0], pinky: [1.3, 1.04, 0.42, -0.05], thumb: [-0.27, -0.18, 0.29, 0.03, 0.01] });
  const support = handKey(-1, 'gun', [-0.0067, -0.0234, -0.33], [0.405, 0.914, 0], [0.802, -0.41, -0.48], cup);
  // Around the magazine: palm on its left face, fingers across the front.
  const magHold = handKey(-1, 'gun', [-0.0128, -0.128, -0.153], [1, 0, 0], [0, 0.14, -0.99], POSES.magHold);
  const magFree = shiftKey(magHold, [0, -0.075, 0]); // straight down, clear of the well
  const magAway = shiftKey(magFree, [-0.05, -0.13, 0.05]);
  const pouch = handKey(-1, 'rig', [-0.2, -0.46, -0.2], [0.4, 0.3, -0.85], [0.35, 0.85, -0.4], POSES.magHold);
  const magBelow = shiftKey(magHold, [-0.006, -0.1, 0.004]); // lined up under the well
  const magLips = shiftKey(magHold, [0, -0.06, 0]); // the lips in its mouth
  const magTug = shiftKey(magHold, [0, -0.005, 0]);
  // For the charging handle the arm comes up from the lower left, palm toward the face, the hand
  // leaning in over the receiver: two fingers hook the front of the handle's left wing.
  const hook = makePose({ index: [0.25, 0.35, 0.3, 0.02], middle: [0.45, 0.6, 0.5, 0], ring: [1.35, 1.5, 0.8, 0], pinky: [1.4, 1.5, 0.8, -0.04], thumb: [0.4, 0.4, 0, 0.2, 0.2] });
  const pull = turnKey(handKey(-1, 'gun', [-0.127, -0.015, -0.034], [0, 0, 1], [1, 0, 0], hook), [-0.018, 0.02, -0.01], [0, 0, 1], 0.5);
  const pullBack = shiftKey(pull, [0, 0, HANDLE_TRAVEL]);
  const pullOff = shiftKey(pullBack, [-0.03, -0.02, -0.03], POSES.relaxed);

  const swap = [
    [0, support],
    [0.26, magHold],
    [R.magOut, magHold], // the button is pressed, the magazine comes free
    [R.magOut + 0.12, magFree],
    [R.magOut + 0.28, magAway],
    [R.magShow - 0.06, pouch], // out of sight: the old one goes, a fresh one comes
    [R.magShow, pouch],
    [R.magInsert - 0.1, magBelow],
    [R.magInsert, magLips],
    [R.magIn, magHold], // pushed home
    [R.tug - 0.03, magHold],
    [R.tug, magTug], // a pull to make sure it has latched
    [R.tug + 0.07, magHold],
  ];
  const tactical = [...swap, [R.tactical - 0.04, support]];
  const empty = [...swap, [R.boltBack, pull], [R.boltBack + 0.11, pullBack], [R.boltRelease, pullBack], [R.boltRelease + 0.12, pullOff], [R.empty - 0.05, support]];
  const rack = [[R.boltBack, 0], [R.boltBack + 0.11, 1], [R.boltRelease, 1], [R.boltRelease + 0.03, 0]];
  // The left elbow swings out and up while that arm is across at the charging handle.
  const reach = [[R.boltBack - 0.24, 0], [R.boltBack - 0.04, 1], [R.boltRelease + 0.06, 1], [R.boltRelease + 0.3, 0]];
  const elbows = { right: new THREE.Vector3(0.34, -0.4, 0.02), left: new THREE.Vector3(-0.22, -0.44, -0.24) };
  const elbowDown = elbows.left.clone();
  const elbowOut = new THREE.Vector3(-0.44, -0.3, -0.16);
  const magGone = [R.magOut + 0.3, R.magShow]; // while the hand is out of sight

  // The magazine rides in the left hand between "out" and "in": this is the hand → magazine transform.
  const magInHand = new THREE.Matrix4().compose(magHold.pos, magHold.quat, new THREE.Vector3(1, 1, 1)).invert();

  /** Carrier position (0 forward … 1 back) this long after a shot: back fast, forward a little slower. */
  const cycle = (age) => (age < 0.022 ? age / 0.022 : Math.max(0, 1 - (age - 0.022) / 0.05));

  return {
    id: 'ar15',
    root,
    meshes,
    triangles: body.triangles + handle.triangles + bolt.triangles + trigger.triangles + mag.triangles + round.triangles,
    muzzle: new THREE.Vector3(0, 0, -MUZZLE_S),
    eject: new THREE.Vector3(0.018, -0.002, -0.142),
    sightRear: new THREE.Vector3(0, SIGHT_Y, -REAR_S),
    /** Eye to rear aperture when aimed. */
    relief: 0.085,
    /** Where recoil rotates the gun about: behind the receiver, between the firing hand and the shoulder. */
    pivot: new THREE.Vector3(0, -0.035, 0.05),
    flash: { star: 0.17, jet: 0.3 },
    poses: {
      hip: def.views.map((v) => gunPose(...v)),
      sprint: gunPose(0.05, -0.22, -0.27, -0.32, 0.8, -0.3),
      reload: gunPose(0.07, -0.02, -0.35, 0.4, 0.28, -0.3),
      wall: gunPose(0.09, -0.15, -0.14, 0.62, 0.12, -0.1),
      holster: gunPose(0.2, -0.46, -0.2, -0.55, 0.25, -0.45),
    },
    /** Butt stroke: [time, x, y, z, pitch, yaw, roll] offsets from the hip pose. */
    melee: [
      [0, 0, 0, 0, 0, 0, 0],
      [0.08, 0.027, -0.024, 0.056, 0.082, -0.365, 0.112], // drawn back to the right
      [0.16, -0.278, 0.078, -0.256, 0.136, 2.172, 0.721], // swung round: the butt lands where the gun was pointing
      [0.27, -0.327, 0.068, -0.229, 0.167, 2.328, 0.766],
      [0.55, 0, 0, 0, 0, 0, 0],
    ],
    elbows,
    magInHand,

    /**
     * Per frame: moves the parts and says where the hands are.
     * ctx: {anim, shotAge, trigger (0…1), left, right (outputs: {a, b, t}), magHeld (output)}
     */
    animate(ctx) {
      const { anim } = ctx;
      meshes.trigger.rotation.x = -0.3 * ctx.trigger;
      ctx.right.a = grip;
      ctx.right.b = gripFire;
      ctx.right.t = ctx.trigger;

      let boltK = cycle(ctx.shotAge);
      let handleK = 0;
      let out = 0;
      let held = false;
      let visible = true;
      let loaded = anim.mag > 0;
      // The magazine is in its well unless the left hand has it (the viewmodel then puts it in that
      // hand): a reload that is broken off leaves it seated.
      meshes.mag.position.set(0, 0, 0);
      meshes.mag.quaternion.identity();
      if (anim.reloading) {
        const t = anim.reloadT;
        sampleTrack(anim.reloadEmpty ? empty : tactical, t, ctx.left);
        if (anim.reloadEmpty) {
          // The bolt has locked back on the empty magazine: it stays there until the handle lets it go.
          handleK = sampleCurve(rack, t);
          out = sampleCurve(reach, t);
          boltK = t < R.boltRelease ? 1 : Math.max(0, 1 - (t - R.boltRelease) / 0.03);
        }
        const pressed = 1 - Math.abs(t - R.magOut) / 0.14;
        if (pressed > 0) {
          ctx.right.b = gripPress;
          ctx.right.t = pressed;
        }
        if (t >= R.magOut && t < R.magIn) {
          held = true;
          visible = t < magGone[0] || t >= magGone[1];
          if (t >= magGone[1]) loaded = true;
        }
      } else {
        ctx.left.a = ctx.left.b = support;
        ctx.left.t = 0;
        if (anim.mag === 0) boltK = 1;
      }
      elbows.left.lerpVectors(elbowDown, elbowOut, out * out * (3 - 2 * out));
      meshes.handle.position.z = HANDLE_TRAVEL * handleK;
      meshes.bolt.scale.z = Math.max(0.001, 1 - boltK);
      meshes.mag.visible = visible;
      meshes.round.visible = loaded;
      ctx.magHeld = held;
    },
  };
}
