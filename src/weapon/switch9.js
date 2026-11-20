// The SWITCH: a compact polymer 9 mm, striker-fired, converted to full-auto. A squared matte-black
// slide over a black polymer frame with a textured grip and a squared trigger guard, plain three-dot
// sights, no hammer and no safety lever; on the back plate of the slide sits the gold block of the
// auto sear (the "switch") with its selector nub, and a 33-round stick magazine stands as far out of
// the grip as the grip is long.
//
// Gun space: origin on the bore axis at the back of the slide, −Z down the barrel, +Y up, +X right.
// Profiles are [s, y] with s = distance forward of the origin.

import * as THREE from 'three';
import { makePose } from './arms.js';
import { FINISH, Soup, block, fillet, lathe, paint, prism, rod, sweep } from './build.js';
import { FINISH_BLUED } from './material.js';
import { POSES, gunPose, handKey, sampleTrack, shiftKey } from './handling.js';
import { ease } from './springs.js';

const SIGHT_Y = 0.017;
const SLIDE_TRAVEL = 0.042;
const SLIDE_END = 0.175; // front face of the slide
const MUZZLE_S = 0.178;
// Cross-section of the slide: flat sides, a flat top and a bevelled shoulder between them.
const HALF = 0.01275;
const TOP = 0.0118;
const BOTTOM = -0.0125;
const SHOULDER = [0.0034, 0.0038]; // run in, rise
// Ejection port: from … to along the slide, cut in from the right as far as PORT_X, down to PORT_Y.
const PORT = [0.0715, 0.1055];
const PORT_X = -0.0036;
const PORT_Y = 0.0016;

// The grip and the magazine in it lean back by RAKE.
const RAKE = 0.35;
const SIN = Math.sin(RAKE);
const COS = Math.cos(RAKE);
const MAG_AXIS = new THREE.Vector3(0, COS, -SIN); // from base to lips
const MAG_FRONT = new THREE.Vector3(0, -SIN, -COS); // across it, toward the muzzle
const MAG_TOP = [0.0557, -0.019]; // [s, y] of the lips, on the centre line
const MAG_LENGTH = 0.213; // lips to the underside of the base plate
const MAG_DEPTH = 0.033; // front to back
const MAG_WIDTH = 0.0215;
const WELL = 0.0947; // how much of the magazine is inside the gun
// The grip's rounded straps: where their centre lines run, forward of the magazine's.
const STRAP_FRONT = 0.0105;
const STRAP_BACK = -0.0185;
const ROUND_PITCH = 0.0054; // height one round adds to the stack

/** A point of the magazine as [s, y]: `u` down its axis from the lips, `v` forward of its centre line. */
const magPoint = (u, v = 0) => [MAG_TOP[0] - u * SIN + v * COS, MAG_TOP[1] - u * COS - v * SIN];
/** The same in gun space. */
const magSpace = (u, v = 0, x = 0) => {
  const [s, y] = magPoint(u, v);
  return [x, y, -s];
};

/** A flat convex face through `pts` ([x, y, z], counter-clockwise seen from the side it looks at). */
function face(pts) {
  const pos = [];
  for (let i = 1; i < pts.length - 1; i++) pos.push(...pts[0], ...pts[i], ...pts[i + 1]);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
  return geo;
}

/** A flat patch on a side of the gun: s0…s1 by y0…y1 at `x`, facing the way x points. */
function patch(s0, s1, y0, y1, x) {
  return face(
    x > 0
      ? [[x, y0, -s0], [x, y0, -s1], [x, y1, -s1], [x, y1, -s0]]
      : [[x, y0, -s1], [x, y0, -s0], [x, y1, -s0], [x, y1, -s1]],
  );
}

/** A flat disc of `n` sides at `centre`, facing `normal`. */
function disc(centre, normal, r, n = 8) {
  const w = new THREE.Vector3(normal[0], normal[1], normal[2]).normalize();
  const u = new THREE.Vector3().crossVectors(Math.abs(w.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0), w).normalize();
  const v = new THREE.Vector3().crossVectors(w, u);
  const pts = [];
  for (let i = 0; i < n; i++) {
    const a = ((i + 0.5) / n) * Math.PI * 2;
    const c = Math.cos(a) * r;
    const s = Math.sin(a) * r;
    pts.push([centre[0] + u.x * c + v.x * s, centre[1] + u.y * c + v.y * s, centre[2] + u.z * c + v.z * s]);
  }
  return face(pts);
}

/**
 * A skin over closed outlines: `stations` is [{s, pts}], rear to front, every `pts` a loop of [x, y]
 * listed counter-clockwise seen from behind the gun, all of the same count. `worn(j, i)` says whether
 * the strip from point i to i + 1 between stations j and j + 1 is a chamfer that takes the paint's wear.
 */
function shell(stations, caps = [true, true], worn = null) {
  const pos = [];
  const tag = [];
  const n = stations[0].pts.length;
  const at = (j, i) => {
    const p = stations[j].pts[i % n];
    return [p[0], p[1], -stations[j].s];
  };
  const tri = (a, b, c, t) => {
    pos.push(...a, ...b, ...c);
    tag.push(t, t, t);
  };
  for (let j = 0; j < stations.length - 1; j++) {
    for (let i = 0; i < n; i++) {
      const t = worn && worn(j, i) ? 1 : 0;
      tri(at(j, i), at(j + 1, i + 1), at(j, i + 1), t);
      tri(at(j, i), at(j + 1, i), at(j + 1, i + 1), t);
    }
  }
  const cap = (j, front) => {
    const loop = stations[j].pts.map(([x, y]) => new THREE.Vector2(x, y));
    for (const [i0, i1, i2] of THREE.ShapeUtils.triangulateShape(loop, [])) {
      const a = at(j, i0);
      const b = at(j, i1);
      const c = at(j, i2);
      const ccw = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 0;
      if (ccw !== front) tri(a, b, c, 0);
      else tri(a, c, b, 0);
    }
  };
  if (caps[0]) cap(0, false);
  if (caps[1]) cap(stations.length - 1, true);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
  geo.setAttribute('tag', new THREE.BufferAttribute(new Float32Array(tag), 1));
  return geo;
}

/** The slide's outline, counter-clockwise seen from behind, pulled in by `inset` all round. */
function slideSection(inset = 0) {
  const e = 0.00045; // width of the worn edges
  const [run, rise] = SHOULDER;
  const len = Math.hypot(run, rise);
  const dx = (-run / len) * e;
  const dy = (rise / len) * e;
  const right = [
    [HALF - 0.0008, BOTTOM],
    [HALF, BOTTOM + 0.0008],
    [HALF, TOP - rise - e],
    [HALF + dx, TOP - rise + dy],
    [HALF - run - dx, TOP - dy],
    [HALF - run - e, TOP],
  ];
  const mid = (TOP + BOTTOM) / 2;
  return [...right, ...right.map(([x, y]) => [-x, y]).reverse()].map(([x, y]) => [x - Math.sign(x) * inset, y - Math.sign(y - mid) * inset]);
}

export function buildSwitch9(material, def, strike = 0.55, goldHex = 0xe7b53a) {
  const wear = paint(0x767b83, 0.32, 1);
  const P = {
    slide: paint(0x2a2c30, 0.5, 0.9, { wear, finish: FINISH_BLUED }), // black nitride
    polymer: paint(0x161719, 0.66, 0, { wear: paint(0x2b2c30, 0.5, 0) }),
    grip: paint(0x141416, 0.82, 0, { finish: FINISH.checker }),
    dark: paint(0x33353a, 0.45, 0.85, { wear }),
    blade: paint(0x2c2d31, 0.55, 0),
    groove: paint(0x08080a, 0.85, 0.3),
    edge: paint(0x4b4f57, 0.38, 0.9),
    barrel: paint(0x62656b, 0.26, 1),
    black: paint(0x040405, 0.92, 0),
    gold: paint(goldHex, 0.24, 1),
    steel: paint(0xa3a7ad, 0.32, 1, { finish: FINISH.brushed }),
    mag: paint(0x1f2023, 0.4, 0),
    brass: paint(0xcaa23d, 0.28, 1),
    copper: paint(0xb5683a, 0.3, 1),
    dot: paint(0xf2f0e4, 0.6, 0, { glow: 0.5 }),
  };

  // ---------------------------------------------------------------------------------------------
  // Frame: everything that stays put
  // ---------------------------------------------------------------------------------------------
  const frame = new Soup();
  // One flat-sided core from the dust cover (with the accessory rail and its one cross slot) down
  // to the mouth of the magazine well; the rounded straps of the grip are added to it below.
  const core = fillet(
    [
      [0.0008, -0.0122],
      [0.1722, -0.0122],
      [0.1722, -0.0215],
      [0.1708, -0.0318, 0.0014],
      [0.156, -0.0318],
      [0.156, -0.0293],
      [0.1505, -0.0293],
      [0.1505, -0.0318],
      [0.137, -0.0318, 0.0012],
      [0.134, -0.0296],
      [0.063, -0.0296],
      magPoint(WELL - 0.0005, STRAP_FRONT),
      magPoint(WELL - 0.0005, STRAP_BACK),
      magPoint(0.02, STRAP_BACK),
      [0.018, -0.0262],
      [0.0008, -0.0225],
    ],
    3,
  );
  frame.add(prism(core, 0.0268, { bevel: 0.0014, steps: 2 }), P.polymer, { crease: 0.6 });
  // The grooves that make the rail, one along each side of the dust cover.
  for (const side of [-1, 1]) frame.add(patch(0.1375, 0.1716, -0.0262, -0.0246, side * 0.01352), P.groove);
  // Beavertail: a rounded tongue over the web of the hand.
  frame.add(
    sweep(
      [[0.024, -0.0215], [0.012, -0.0205], [0.002, -0.0198], [-0.006, -0.0202], [-0.0115, -0.0222]],
      (t) => ({ w: 0.0262 - 0.0092 * t ** 1.6, d: 0.0135 - 0.009 * t, exp: 2.6 }),
      12,
      [false, true],
    ),
    P.polymer,
    { crease: 0.9 },
  );

  // Squared trigger guard.
  const guard = fillet([[0.066, -0.027], [0.125, -0.027], [0.125, -0.034], [0.1235, -0.0595, 0.004], [0.089, -0.0605, 0.007], [0.075, -0.052, 0.004], [0.064, -0.05]], 3);
  const guardHole = fillet([[0.0795, -0.0285], [0.1195, -0.0285], [0.119, -0.0548, 0.0035], [0.0915, -0.056, 0.006], [0.0815, -0.0495, 0.004]], 3);
  frame.add(prism(guard, 0.0142, { bevel: 0.0011, holes: [guardHole] }), P.polymer, { crease: 0.6 });

  // Grip: rounded front and back straps, smooth where they leave the frame and at the mouth of the
  // well, textured in between; a textured panel on each side joins them.
  const texture = [0.038, WELL - 0.007]; // from … to, down the grip
  for (const v of [STRAP_FRONT, STRAP_BACK]) {
    const from = v > 0 ? 0.012 : 0.016;
    frame.add(sweep([from, 0.05, WELL - 0.0005].map((u) => magPoint(u, v)), () => ({ w: 0.0263, d: 0.0196, exp: 2.6 }), 12, [false, true]), P.polymer, { crease: 0.9 });
    frame.add(sweep([texture[0], 0.06, texture[1]].map((u) => magPoint(u, v)), () => ({ w: 0.027, d: 0.0204, exp: 2.6 }), 12, [true, true]), P.grip, { crease: 0.9 });
  }
  const panel = fillet(
    [[texture[0], STRAP_BACK], [texture[0], STRAP_FRONT], [texture[1], STRAP_FRONT], [texture[1], STRAP_BACK]].map(([u, v]) => [...magPoint(u, v), 0.003]),
    2,
  );
  for (const side of [-1, 1]) frame.add(prism(panel, 0.0008, { x: side * 0.0137, bevel: 0.0003 }), P.grip, { crease: 0.5 });

  // Slide stop (left), take-down tabs, magazine catch, pins.
  frame.add(
    prism([[0.028, -0.014], [0.074, -0.014], [0.076, -0.0152], [0.074, -0.0164], [0.044, -0.016], [0.04, -0.0185], [0.029, -0.0185], [0.0275, -0.0165]], 0.0013, { x: -0.014, bevel: 0.0004 }),
    P.dark,
  );
  for (const side of [-1, 1]) {
    frame.add(block(0.083, 0.092, -0.0236, -0.0206, side > 0 ? 0.0132 : -0.0143, side > 0 ? 0.0143 : -0.0132, 0.0004), P.dark);
    frame.add(disc([side * 0.01352, -0.0235, -0.0905], [side, 0, 0], 0.0019), P.dark);
    frame.add(disc([side * 0.01352, -0.0172, -0.0965], [side, 0, 0], 0.0015), P.dark);
  }
  frame.add(block(0.0575, 0.0685, -0.0455, -0.0385, -0.0156, -0.013, 0.0005), P.polymer);
  // Recoil spring guide under the barrel: it shows when the slide is back.
  frame.add(rod([0, -0.0088, -0.108], [0, -0.0088, -0.1756], 0.0031, 0.0031, 8, [false, true]), P.steel, { crease: 0.9 });

  // ---------------------------------------------------------------------------------------------
  // Slide (moves back) with the sights and the switch, barrel (tilts as the slide unlocks)
  // ---------------------------------------------------------------------------------------------
  const slide = new Soup();
  const full = slideSection();
  const edges = (j, i) => i === 2 || i === 4 || i === 6 || i === 8;
  slide.add(
    shell([{ s: 0, pts: slideSection(0.0007) }, { s: 0.0007, pts: full }, { s: PORT[0], pts: full }], [true, true], (j, i) => j === 0 || edges(j, i)),
    P.slide,
    { crease: 0.5 },
  );
  slide.add(
    shell([{ s: PORT[1], pts: full }, { s: SLIDE_END - 0.0007, pts: full }, { s: SLIDE_END, pts: slideSection(0.0007) }], [true, true], (j, i) => j === 1 || edges(j, i)),
    P.slide,
    { crease: 0.5 },
  );
  // Between them the port is cut out of the top and the right side.
  const cut = [full[0], full[1], [HALF, PORT_Y], [PORT_X, PORT_Y], [PORT_X, TOP], ...full.slice(6)];
  slide.add(shell([{ s: PORT[0], pts: cut }, { s: PORT[1], pts: cut }], [false, false], (j, i) => i === 5 || i === 7), P.slide, { crease: 0.5 });
  const lip = 0.00012;
  const corner = [[PORT_X, PORT_Y], [HALF, PORT_Y], [HALF, TOP - SHOULDER[1]], [HALF - SHOULDER[0], TOP], [PORT_X, TOP]];
  slide.add(face(corner.map(([x, y]) => [x, y, -PORT[0] - lip]).reverse()), P.black);
  slide.add(face(corner.map(([x, y]) => [x, y, -PORT[1] + lip])), P.black);
  slide.add(face([[PORT_X, PORT_Y + lip, -PORT[0]], [HALF, PORT_Y + lip, -PORT[0]], [HALF, PORT_Y + lip, -PORT[1]], [PORT_X, PORT_Y + lip, -PORT[1]]]), P.black);
  slide.add(patch(PORT[0], PORT[1], PORT_Y, TOP, PORT_X + lip), P.black);
  // Extractor behind the port.
  slide.add(patch(0.0495, PORT[0], 0.0004, 0.0036, HALF + lip), P.dark);

  // Cocking serrations, rear and front: a dark groove and the edge beside it that catches the light.
  const sideTop = TOP - SHOULDER[1] - 0.0009;
  for (const [from, count] of [[0.0205, 6], [0.1275, 4]]) {
    for (let i = 0; i < count; i++) {
      const s = from + i * 0.0047;
      for (const side of [-1, 1]) {
        slide.add(patch(s, s + 0.0027, -0.0106, sideTop, side * (HALF + lip)), P.groove);
        slide.add(patch(s + 0.0027, s + 0.0036, -0.0106, sideTop, side * (HALF + lip)), P.edge);
      }
    }
  }

  // Sights: a squared rear notch with two dots, a front post with one.
  slide.add(block(0.0045, 0.0165, TOP - 0.0003, 0.0136, -0.0092, 0.0092, 0.0005), P.dark);
  for (const side of [-1, 1]) {
    slide.add(prism([[0.0048, 0.0134], [0.0165, 0.0134], [0.015, SIGHT_Y], [0.0048, SIGHT_Y]], 0.0071, { x: side * 0.00565, bevel: 0.0004 }), P.dark);
    slide.add(disc([side * 0.0054, 0.0151, -0.0047], [0, 0, 1], 0.00135), P.dot);
  }
  slide.add(prism([[0.1575, TOP - 0.0003], [0.1705, TOP - 0.0003], [0.1665, SIGHT_Y], [0.158, SIGHT_Y]], 0.0038, { bevel: 0.0004 }), P.dark);
  slide.add(disc([0, 0.0148, -0.15755], [0, 0, 1], 0.00135), P.dot);

  // Muzzle end: the holes the barrel and the spring guide come through.
  slide.add(disc([0, 0, -SLIDE_END - lip], [0, 0, -1], 0.0079, 12), P.black);
  slide.add(disc([0, -0.0088, -SLIDE_END - lip], [0, 0, -1], 0.0038, 8), P.black);

  // Back plate, and on it the switch: the auto sear's housing with its selector across it.
  slide.add(face([[-0.0084, -0.0116, lip], [0.0084, -0.0116, lip], [0.0084, 0.0072, lip], [-0.0084, 0.0072, lip]]), P.polymer);
  slide.add(
    prism([[0.0002, -0.01], [0.0002, 0.0066], [-0.0098, 0.0066], [-0.0116, 0.0048], [-0.0116, -0.0082], [-0.0098, -0.01]], 0.0134, { bevel: 0.0009 }),
    P.gold,
    { crease: 0.5 },
  );
  slide.add(rod([-0.0066, 0.0018, 0.006], [-0.0086, 0.0018, 0.006], 0.0021, 0.0021, 8, [false, false]), P.steel, { crease: 0.9 });
  slide.add(rod([-0.0086, 0.0018, 0.006], [-0.0098, 0.0018, 0.006], 0.0027, 0.0027, 8), P.steel, { crease: 0.5 });
  slide.add(rod([0.0066, 0.0018, 0.006], [0.0074, 0.0018, 0.006], 0.0021, 0.0021, 8, [false, true]), P.steel, { crease: 0.5 });
  slide.add(disc([0, -0.0046, 0.0116 + lip], [0, 0, 1], 0.0017), P.dark);

  const barrel = new Soup();
  barrel.add(lathe([[0.104, 0.0071], [MUZZLE_S - 0.0008, 0.0071], [MUZZLE_S, 0.0063]], 12, { caps: [false, false] }), P.barrel, { crease: 0.6 });
  barrel.add(lathe([[MUZZLE_S, 0.0063], [MUZZLE_S - 0.0015, 0.0046], [0.15, 0.0045]], 12, { caps: [false, true], inside: true }), P.black, { crease: 0.9, ao: 0 });
  // The chamber block, which fills the port while the slide is forward.
  barrel.add(block(PORT[0] + 0.0022, PORT[1] - 0.0012, PORT_Y + 0.0006, TOP - 0.001, PORT_X + 0.0003, 0.0086, 0.0004), P.barrel);

  // Trigger, modelled around its pivot, and the safety blade let into its face.
  const trigger = new Soup();
  trigger.add(
    prism(
      fillet(
        [
          [-0.0035, 0.0015],
          [0.0035, 0.0015],
          [0.0038, -0.006],
          [0.003, -0.014, 0.004],
          [0.0042, -0.022, 0.004],
          [0.0062, -0.0265],
          [0.004, -0.0275],
          [0.0005, -0.021, 0.004],
          [-0.0012, -0.012, 0.004],
          [-0.003, -0.004],
        ],
        2,
      ),
      0.0068,
      { bevel: 0.001 },
    ),
    P.polymer,
  );
  const blade = new Soup();
  blade.add(prism([[0.0036, -0.0085], [0.0048, -0.0092], [0.0042, -0.0145], [0.0054, -0.0215], [0.0069, -0.0256], [0.0058, -0.0262], [0.004, -0.0218], [0.003, -0.0145]], 0.002), P.blade);

  // Magazine: a long polymer-skinned stick with steel lips, witness holes and a base plate.
  const mag = new Soup();
  const half = MAG_DEPTH / 2;
  const bodyEnd = MAG_LENGTH - 0.0065;
  const lipsY = MAG_TOP[1];
  const lipsS = (v) => MAG_TOP[0] + v / COS;
  mag.add(prism([[lipsS(-half), lipsY - 0.004], [lipsS(half), lipsY - 0.004], magPoint(bodyEnd, half), magPoint(bodyEnd, -half)], MAG_WIDTH, { bevel: 0.0026, steps: 2 }), P.mag, { crease: 0.5 });
  mag.add(
    prism(
      [[lipsS(-half) + 0.001, lipsY + 0.001], [lipsS(half) - 0.006, lipsY + 0.001], [lipsS(half) - 0.004, lipsY - 0.0045], [lipsS(-half) + 0.001, lipsY - 0.0045]],
      MAG_WIDTH - 0.004,
      { bevel: 0.0006 },
    ),
    P.dark,
  );
  const plate = [-half - 0.0012, half + 0.003]; // the base plate stands proud of the body, most at the front
  mag.add(
    prism(
      fillet([magPoint(bodyEnd - 0.0005, plate[0]), magPoint(bodyEnd - 0.0005, plate[1]), [...magPoint(MAG_LENGTH, plate[1]), 0.002], [...magPoint(MAG_LENGTH, plate[0]), 0.002]], 2),
      MAG_WIDTH + 0.0026,
      { bevel: 0.0014, steps: 2 },
    ),
    P.polymer,
    { crease: 0.5 },
  );
  // The round on top of a loaded magazine, and the brass that shows in the witness holes.
  const round = new Soup();
  round.add(lathe([[0.0405, 0.0048], [0.0585, 0.0048], [0.0595, 0.0044]], 8, { y: lipsY + 0.0012, caps: [true, false] }), P.brass, { crease: 0.9 });
  round.add(lathe([[0.0595, 0.0044], [0.0655, 0.0036], [0.07, 0.0012]], 8, { y: lipsY + 0.0012, caps: [false, true] }), P.copper, { crease: 0.9 });
  const cartridge = round.triangles * 3; // vertices of the round itself
  // Witness holes: a column down the back, a few on each side where the magazine stands clear.
  const windows = []; // [{need, end}]: rounds it takes to show brass, vertices drawn up to there
  const back = [-MAG_FRONT.x, -MAG_FRONT.y, -MAG_FRONT.z];
  const holes = [];
  for (let u = 0.034; u < 0.19; u += 0.022) holes.push({ u, sides: false });
  for (let u = 0.111; u < 0.18; u += 0.022) holes.push({ u, sides: true });
  holes.sort((a, b) => a.u - b.u);
  for (const hole of holes) {
    const spots = hole.sides
      ? [-1, 1].map((side) => ({ at: magSpace(hole.u, -0.004, side * MAG_WIDTH * 0.5), n: [side, 0, 0] }))
      : [{ at: magSpace(hole.u, -half), n: back }];
    for (const { at, n } of spots) {
      mag.add(disc([at[0] + n[0] * lip, at[1] + n[1] * lip, at[2] + n[2] * lip], n, 0.002), P.black);
      round.add(disc([at[0] + n[0] * lip * 2, at[1] + n[1] * lip * 2, at[2] + n[2] * lip * 2], n, 0.0015), P.brass);
    }
    windows.push({ need: (hole.u - 0.01) / ROUND_PITCH, end: round.triangles * 3 });
  }

  // ---------------------------------------------------------------------------------------------
  // Assembly
  // ---------------------------------------------------------------------------------------------
  const root = new THREE.Group();
  root.name = 'switch9';
  const part = (soup, name) => {
    const mesh = new THREE.Mesh(soup.build(), material);
    mesh.name = `switch9-${name}`;
    mesh.frustumCulled = false;
    return mesh;
  };
  const meshes = {
    frame: part(frame, 'frame'),
    slide: part(slide, 'slide'),
    barrel: part(barrel, 'barrel'),
    trigger: part(trigger, 'trigger'),
    blade: part(blade, 'blade'),
    mag: part(mag, 'mag'),
    round: part(round, 'round'),
  };
  // The barrel pivots about its locking block, the trigger about its pin.
  const lug = new THREE.Vector3(0, -0.006, -0.104);
  meshes.barrel.geometry.translate(-lug.x, -lug.y, -lug.z);
  meshes.barrel.position.copy(lug);
  meshes.trigger.position.set(0, -0.0235, -0.0905);
  meshes.trigger.add(meshes.blade);
  meshes.mag.add(meshes.round);
  root.add(meshes.frame, meshes.slide, meshes.barrel, meshes.trigger, meshes.mag);

  // ---------------------------------------------------------------------------------------------
  // Handling
  // ---------------------------------------------------------------------------------------------
  const R = def.reload;
  const poses = {
    hip: def.views.map((v) => gunPose(...v)),
    sprint: gunPose(0.05, -0.2, -0.3, -0.6, 0.6, -0.2),
    reload: gunPose(0.135, -0.01, -0.46, 0.5, 0.3, -1.15),
    wall: gunPose(0.07, -0.13, -0.24, 0.75, 0.1, 0),
    holster: gunPose(0.17, -0.44, -0.24, -0.6, 0.2, -0.4),
  };

  // Firing hand: three fingers round the grip, the index along the frame until it goes to the trigger.
  const wrapped = { middle: [1.25, 1.5, 0.8, 0], ring: [1.3, 1.5, 0.8, 0], pinky: [1.35, 1.5, 0.8, -0.03] };
  const straight = [0.16, 0.22, 0.14, 0.16];
  const grip = handKey(1, 'gun', [0.0152, -0.06, -0.0175], [-1, 0, -0.12], [0.06, -0.2, -0.98], makePose({ ...wrapped, index: straight, thumb: [0.2, 0.35, 0, 0.3, 0.25] }));
  const gripFire = { ...grip, pose: makePose({ ...wrapped, index: [0.4, 0.92, 0.5, 0.08], thumb: [0.2, 0.35, 0, 0.3, 0.25] }) };
  // Thumb down on the magazine catch / up on the slide stop.
  const gripThumb = { ...grip, pose: makePose({ ...wrapped, index: straight, thumb: [0.45, 0.6, 0, 0.55, 0.6] }) };
  // Support hand over the firing hand's fingers, thumb forward along the frame.
  const support = handKey(-1, 'gun', [-0.0168, -0.08, -0.03], [1, 0.05, -0.2], [0.05, -0.55, -0.83], POSES.pistolSupport);

  // The left hand on a magazine: a fist round its lower end, the base plate against the heel of the
  // hand, the stick standing out of the top of the fist.
  const axis = (d) => [0, MAG_AXIS.y * d, MAG_AXIS.z * d];
  const across = [0, MAG_FRONT.y * 0.92 + MAG_AXIS.y * 0.39, MAG_FRONT.z * 0.92 + MAG_AXIS.z * 0.39]; // fingers round the front, a little upward
  const fist = makePose({ fingers: [1.2, 1.35, 0.7, 0], index: [1.05, 1.25, 0.65, 0.02], thumb: [0.25, 0.5, 0, 0.4, 0.4] });
  const SHORT = 0.02; // where the magazine stops before the hand shoves it the rest of the way
  const hold = handKey(-1, 'gun', magSpace(0.19, -0.006, -MAG_WIDTH / 2 - 0.001), [1, 0, -0.15], across, fist); // (the magazine home)
  const lined = shiftKey(hold, [-0.02, MAG_AXIS.y * -(WELL + 0.05), MAG_AXIS.z * -(WELL + 0.05) + 0.02]); // under the well
  const lips = shiftKey(hold, axis(-WELL)); // lips entering the well
  const short = shiftKey(hold, axis(-SHORT));
  const away = handKey(-1, 'rig', [-0.14, -0.36, -0.3], [0.3, 0.5, -0.8], [0.4, 0.8, -0.4], POSES.relaxed);
  // The pouch: below the view, the hand already turned the way it will hold the magazine up to the gun.
  const pouch = { space: 'rig', pos: new THREE.Vector3(-0.16, -0.5, -0.3), quat: poses.reload.quat.clone().multiply(hold.quat), pose: fist };

  const span = R.magIn - R.magInsert;
  const tShort = R.magInsert + span * 0.5;
  const tPush = R.magInsert + span * 0.66;
  const swap = [
    [0, support],
    [0.14, away],
    [R.magShow - 0.08, pouch],
    [R.magShow, pouch], // a fresh magazine in the hand
    [R.magInsert - 0.1, lined],
    [R.magInsert, lips],
    [tShort, short], // most of the way in …
    [tPush, short],
    [R.magIn, hold], // … and the heel of the hand drives it home
    [R.magIn + 0.06, hold],
  ];
  const tactical = [...swap, [R.tactical - 0.03, support]];
  // Empty: the hand stays clear while the firing thumb drops the slide, then comes back as the gun does.
  const empty = [...swap, [R.magIn + 0.3, away], [R.slideRelease, away], [R.empty - 0.04, support]];
  const magInHand = new THREE.Matrix4().compose(hold.pos, hold.quat, new THREE.Vector3(1, 1, 1)).invert();
  /** How far short of home the magazine is while it goes up the well. */
  const inserted = (t) => (t < tShort ? WELL + (SHORT - WELL) * ease((t - R.magInsert) / (tShort - R.magInsert)) : SHORT * (1 - ease((t - tPush) / (R.magIn - tPush))));

  /** Slide position (0 forward … 1 back) this long after a shot: one cycle fits between two shots. */
  const cycle = (age) => (age < 0.013 ? age / 0.013 : Math.max(0, 1 - (age - 0.013) / 0.029));
  // A dropped magazine: how long it takes to run down the well ((0.2 + 2 t) t = WELL) and which way it
  // then falls, in gun space, while the gun is held up for the reload.
  const CLEAR = (Math.sqrt(0.04 + 8 * WELL) - 0.2) / 4;
  const down = new THREE.Vector3(0, -1, 0).applyQuaternion(poses.reload.quat.clone().invert());
  const centre = new THREE.Vector3(...magSpace(MAG_LENGTH * 0.5));
  const tumble = new THREE.Quaternion();
  const axisX = new THREE.Vector3(1, 0, 0);
  const offset = new THREE.Vector3();

  return {
    id: 'switch9',
    root,
    meshes,
    triangles: frame.triangles + slide.triangles + barrel.triangles + trigger.triangles + blade.triangles + mag.triangles + round.triangles,
    muzzle: new THREE.Vector3(0, 0, -MUZZLE_S),
    eject: new THREE.Vector3(0.012, 0.012, -0.089),
    sightRear: new THREE.Vector3(0, SIGHT_Y, -0.0048),
    relief: 0.36,
    /** Recoil turns the pistol about the wrist. */
    pivot: new THREE.Vector3(0, -0.08, 0.035),
    flash: { star: 0.11, jet: 0.12 },
    poses,
    /** Pistol whip: [time, x, y, z, pitch, yaw, roll] offsets from the hip pose. */
    melee: [
      [0, 0, 0, 0, 0, 0, 0],
      [0.08, 0.02, 0.07, 0.07, 0.6, -0.3, 0.3], // wound up: back, up and to the right
      [0.16, -0.17, 0.0, -0.17, 1.1, 0.4, -0.7], // butt first across the front
      [0.27, -0.185, -0.025, -0.15, 1.15, 0.45, -0.75],
      [0.55, 0, 0, 0, 0, 0, 0],
    ],
    elbows: { right: new THREE.Vector3(0.46, -0.34, 0), left: new THREE.Vector3(-0.25, -0.42, -0.05) },
    magInHand,

    animate(ctx) {
      const { anim } = ctx;
      meshes.trigger.rotation.x = -0.26 * ctx.trigger;
      meshes.blade.position.z = 0.0012 * Math.min(1, ctx.trigger * 3);
      ctx.right.a = grip;
      ctx.right.b = gripFire;
      ctx.right.t = ctx.trigger;

      // Slide: cycles with every shot, stays back on an empty magazine until the stop is thumbed.
      let slideK = cycle(ctx.shotAge);
      let held = false;
      let rounds = anim.mag;
      const mesh = meshes.mag;
      mesh.position.set(0, 0, 0);
      mesh.quaternion.identity();
      if (anim.reloading) {
        const t = anim.reloadT;
        sampleTrack(anim.reloadEmpty ? empty : tactical, t, ctx.left);
        if (anim.reloadEmpty) slideK = t < R.slideRelease ? 1 : Math.max(0, 1 - (t - R.slideRelease) / 0.03);
        // Thumb: down on the magazine catch, later up on the slide stop.
        const press = Math.max(0, 1 - Math.abs(t - R.magOut) / 0.12, anim.reloadEmpty ? 1 - Math.abs(t - R.slideRelease) / 0.1 : 0);
        if (press > 0) {
          ctx.right.b = gripThumb;
          ctx.right.t = press;
        }
        if (t >= R.magOut && t < R.magShow) {
          // The old magazine runs down the well under its own weight, then falls clear and turns over.
          const since = t - R.magOut;
          const free = since - CLEAR;
          if (free < 0) mesh.position.copy(MAG_AXIS).multiplyScalar(-(0.2 + 2 * since) * since);
          else {
            mesh.position.copy(MAG_AXIS).multiplyScalar(-WELL - (0.2 + 4 * CLEAR) * free).addScaledVector(down, 4.9 * free * free);
            tumble.setFromAxisAngle(axisX, -4 * free);
            offset.copy(centre).applyQuaternion(tumble).sub(centre);
            mesh.position.sub(offset);
            mesh.quaternion.copy(tumble);
          }
        } else if (t >= R.magShow && t < R.magIn) {
          rounds = def.magSize;
          // The fresh magazine rides in the hand up to the well; in it, it can only go along it.
          if (t < R.magInsert) held = true;
          else mesh.position.copy(MAG_AXIS).multiplyScalar(-inserted(t));
        }
      } else {
        // A pistol whip is thrown one-handed: the support hand lets go for the length of the strike.
        ctx.left.a = support;
        ctx.left.b = away;
        ctx.left.t = anim.melee ? Math.min(ease(anim.meleeT / 0.08), ease((strike - anim.meleeT) / 0.16)) : 0;
        if (anim.mag === 0) slideK = 1;
      }
      meshes.slide.position.z = SLIDE_TRAVEL * slideK;
      meshes.barrel.rotation.x = 0.04 * Math.min(1, slideK * 3);
      // Brass shows in as many witness holes as the stack of rounds reaches.
      let drawn = cartridge;
      for (let i = 0; i < windows.length && rounds >= windows[i].need; i++) drawn = windows[i].end;
      meshes.round.visible = rounds > 0;
      meshes.round.geometry.setDrawRange(0, drawn);
      ctx.magHeld = held;
    },
  };
}
