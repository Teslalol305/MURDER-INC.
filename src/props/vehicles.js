// Vehicles: the avenue's cover and most of its look.
//
// A car is a side outline pushed across its width and chamfered (wheel arches are part of the outline),
// a narrower greenhouse on top with separate glass, four lathe wheels and a handful of boxes for
// bumpers, lamps, mirrors and trim. The body is then bent: tapered in plan toward nose and tail, tucked
// under at the sills, leaned in above the belt line. One spec (lengths and heights in metres, x forward)
// describes a body style; sedan, taxi, SUV, pickup, van and the truck cab are all the same code.

import { palette } from '../config/look.js';
import { clamp01 } from '../core/util.js';
import { M, Soup, arc, glow, latheGeo, prism, xf } from './kit.js';

const ARCH_SEGMENTS = 8;
const HULL_BEVEL = 0.04;
const CAB_BEVEL = 0.035;
const CAB_INSET = 0.055; // the greenhouse sits this far inside the body side
const GLASS_LIFT = 0.012;
const WHEEL_SEGMENTS = 12;

const DARK = 'plastic_dark';
const TAIL = glow(0xff1a10, 0.6); // parked: lenses catching the street light
const AMBER = glow(0xff8a1a, 0.5);
const HEAD = glow(0xfff0d0, 3.2); // headlights that are on
const LENS = glow(0xcfd8e0, 0.2); // …and off: glass that still finds some light
const MARKER = glow(0xffa030, 1.6);

// Believable street colours in the afternoon sun: silvers, whites and greys, a few strong reds and blues,
// one black. Nothing so dark that a row of parked cars turns into a black wall by day.
export const CAR_COLORS = [
  0x8f959c, 0xd9d7d0, 0xb9bcc0, 0x3a3e45, 0x9c2320, 0x24508f, 0x2c5a3e, 0xa89878, 0x6f8aa8, 0x6a1c22, 0x1e2b48,
  0xc9bea4, 0x1a1c20, 0x5d6168,
];
const SUV_COLORS = [0x0b0c0e, 0x0b0c0e, 0x14161a, 0x1c2029, 0x2a2c30, 0x3a1416]; // black, or nearly: Rule's ride
const TRUCK_COLORS = [0xd9d7d0, 0x8f1f1c, 0x1b2a4a, 0x2a2d33, 0x16342a, 0xb9bcc0];
const VAN_COLORS = [0xd9d7d0, 0x8f959c, 0x1b2a4a, 0xb9b4a6, 0x5a1a1c];
const BOX_COLORS = [0xd8d6cf, 0xb9b4a6, 0xc9a23a, 0x8a8f96];
const VULTURE_VAN = 0x1a1c20;

/** Body style defaults (a full-size sedan). x is measured from the middle of the car, nose at +x. */
const CAR = {
  L: 4.6,
  H: 1.45,
  hw: 0.865, // half width of the sheet metal (mirrors reach further)
  nose: 0.06, // how far the bumpers stand proud of the sheet metal
  tail: 0.06,
  wheel: { r: 0.325, w: 0.21, rim: 0.22, style: 'cap' },
  axleF: 1.42,
  axleR: -1.38, // null: no rear axle (a truck cab)
  clearance: 0.2,
  belt: 1.02, // top of the doors, base of the glass
  hood: [0.9, 1.0], // bonnet height at the nose and at the cowl
  deck: 1.01, // boot lid height; null = the greenhouse runs to the tail
  cowl: 0.98, // x of the windscreen base
  screenTop: 0.3,
  rearTop: -1.0,
  rearBase: -1.52,
  tumble: 0.17, // how much narrower the roof is than the belt
  taperF: 0.09, // how much narrower the nose is than the doors
  taperR: 0.06,
  tuck: 0.035,
  pillarA: 0.07,
  pillarB: -0.2,
  pillarC: 0.14,
  rearGlass: true, // rear door windows
  quarterGlass: false,
  backGlass: true,
  cabBack: null, // x where a two-door cab's side glass ends
  bed: null, // pickup: {x1, floor}
  openTail: null, // van with its back doors open: floor height
  paint: '@paint',
  cabinPaint: null,
  underSlot: DARK,
  bumper: DARK,
  grille: DARK,
  mirror: null,
  wheels: 'full', // 'full' | 'rims' (burned out) | 'hubs' (on stands) | 'none'
  drop: 0, // how far the caller lowers the whole body (a car sitting on its rims)
  glass: true,
  trim: true,
  tailTrim: true,
  doorsOff: false,
  headlights: false, // true = switched on
  cover: 1.08, // top of the lower collider: a crouched eye (1.05) is hidden behind any part of the body
};

const ARCH_GAP = 0.055; // wheel arch radius beyond the tyre

/** Half the width of a wheel arch opening where it meets the sill. */
const archReach = (c) => Math.sqrt((c.wheel.r + ARCH_GAP) ** 2 - (c.wheel.r - c.clearance) ** 2);

/**
 * Half widths of the bent body, as functions of where you are on it. In plan the flanks are three flat
 * facets: straight between the wheel arches, angled in toward the nose and toward the tail from a hinge
 * line just inside each arch.
 */
function shapeOf(c) {
  const hF = c.L / 2 - c.nose;
  const hR = c.L / 2 - c.tail;
  // Hinges stand clear of the arch ends, or the chamfer there would fold over itself.
  const hingeF = c.taperF > 0 ? c.axleF - archReach(c) - 0.1 : Infinity;
  const hingeR = c.taperR > 0 && c.axleR !== null ? c.axleR + archReach(c) + 0.1 : -Infinity;
  const plan = (x) => {
    if (x > hingeF) return 1 - (c.taperF * (x - hingeF)) / (hF - hingeF);
    if (x < hingeR) return 1 - (c.taperR * (hingeR - x)) / (hR + hingeR);
    return 1;
  };
  const sec = (y) => 1 - c.tuck * clamp01((c.belt - y) / (c.belt - c.clearance));
  const tumble = (y) => 1 - c.tumble * clamp01((y - c.belt) / (c.H - c.belt));
  const lean = (c.hw * c.tuck) / (c.belt - c.clearance); // how far the body side leans out per metre of height
  const leanCab = ((c.hw - CAB_INSET) * c.tumble) / (c.H - c.belt); // and how far the greenhouse leans in
  return {
    hF,
    hR,
    hingeF,
    hingeR,
    plan,
    tumble,
    /** Half width of the body side at (x, y). */
    side: (x, y) => c.hw * plan(x) * sec(y),
    /** Half width of the greenhouse at height y (it is not tapered in plan: its sides stay flat). */
    cab: (x, y) => (c.hw - CAB_INSET) * tumble(y),
    /** Decal axes that lie flat on the leaning body side (s = +1 for the +Z flank). */
    flank: (s) => {
      const k = 1 / Math.hypot(1, lean);
      return { right: [s, 0, 0], up: [0, k, s * lean * k] };
    },
    /** The same for the greenhouse side, which leans the other way. */
    cabFlank: (s) => {
      const k = 1 / Math.hypot(1, leanCab);
      return { right: [s, 0, 0], up: [0, k, -s * leanCab * k] };
    },
    warpHull: (p) => {
      p[2] *= plan(p[0]) * sec(p[1]);
    },
    warpCab: (p) => {
      p[2] *= tumble(p[1]);
    },
  };
}

/**
 * Adds a point at `x` on the outline's upper edge (searched from index `start`, where x decreases) and
 * returns it. It inherits the tag of the wall it splits.
 */
function splitTop(pts, x, start) {
  for (let i = start; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    if (Math.abs(a[0] - x) < 1e-4) return a;
    if (a[0] > x && b[0] < x) {
      const t = (a[0] - x) / (a[0] - b[0]);
      const p = [x, a[1] + (b[1] - a[1]) * t];
      if (a[2] !== undefined) p.push(a[2]);
      pts.splice(i + 1, 0, p);
      return p;
    }
  }
  return null;
}

/**
 * Side outline of the lower body, counter-clockwise from the tail's underside, and the chords along
 * which its flanks fold. 'u' walls are the dark underside, 'x' walls are left out.
 */
function hullOutline(c, S) {
  const { hF, hR } = S;
  const { r } = c.wheel;
  const gc = c.clearance;
  const ra = r + ARCH_GAP;
  const reach = archReach(c);
  const a0 = -Math.asin((r - gc) / ra);
  const pts = [[-hR + 0.04, gc + 0.14, 'u']];
  let lowR = null;
  if (c.axleR !== null) {
    pts.push([c.axleR - reach - 0.1, gc + 0.03, 'u'], ...arc(c.axleR, r, ra, Math.PI - a0, a0, ARCH_SEGMENTS, 'u'));
    if (Number.isFinite(S.hingeR)) pts.push((lowR = [S.hingeR, gc, 'u']));
  } else {
    pts.push([-hR + 0.2, gc, 'u']);
  }
  let lowF = null;
  if (Number.isFinite(S.hingeF)) pts.push((lowF = [S.hingeF, gc, 'u']));
  pts.push(...arc(c.axleF, r, ra, Math.PI - a0, a0, ARCH_SEGMENTS, 'u'));
  pts.push(
    [hF - 0.1, gc + 0.07], // front valance: paint from here up
    [hF - 0.01, gc + 0.17],
    [hF, c.hood[0] - 0.3],
    [hF - 0.02, c.hood[0] - 0.1],
  );
  const lead = pts.length; // the bonnet's leading edge: the upper edge runs back from here
  pts.push(
    [hF - 0.1, c.hood[0]],
    [(hF - 0.1 + c.cowl) / 2, c.hood[0] + (c.hood[1] - c.hood[0]) * 0.55 + 0.015],
    // With the back doors open the deck under the greenhouse goes too.
    c.openTail === null ? [c.cowl + 0.02, c.hood[1]] : [c.cowl + 0.02, c.hood[1], 'x'],
  );
  if (c.doorsOff) {
    // Stripped: the door openings are a notch right through the body.
    const sill = gc + 0.2;
    pts.push([c.cowl - 0.28, c.belt], [c.cowl - 0.3, sill], [c.rearBase + 0.5, sill], [c.rearBase + 0.42, c.belt]);
  }
  if (c.bed) {
    // Pickup: the load floor behind the cab; the bed walls are added as boxes.
    pts.push([c.bed.x1, c.belt], [c.bed.x1 - 0.02, c.bed.floor], [-hR + 0.02, c.bed.floor], [-hR, gc + 0.3]);
  } else if (c.deck !== null) {
    pts.push([c.rearBase - 0.02, c.deck], [-hR + 0.3, c.deck], [-hR + 0.06, c.deck - 0.03], [-hR, c.deck - 0.14], [-hR, gc + 0.3]);
  } else if (c.openTail !== null) {
    pts.push([-hR + 0.03, c.belt], [-hR, c.belt - 0.06, 'x'], [-hR, c.openTail], [-hR, gc + 0.3]);
  } else {
    pts.push([-hR + 0.03, c.belt], [-hR, c.belt - 0.06], [-hR, gc + 0.3]);
  }
  // Fold lines: a point on the upper edge above each hinge point on the sill.
  const chords = [];
  for (const low of [lowF, lowR]) {
    const high = low && splitTop(pts, low[0], lead);
    if (high) chords.push([pts.indexOf(high), pts.indexOf(low)]);
  }
  return { pts, chords };
}

/** Side outline of the greenhouse. Its underside is buried in the body. */
function cabinOutline(c) {
  const yb = c.belt - 0.06;
  const open = c.openTail === null ? [] : ['x']; // back wall and underside go when the doors are open
  return [
    [c.rearBase, yb, ...open],
    [c.cowl, yb],
    [c.screenTop, c.H - 0.03],
    [(c.screenTop + c.rearTop) / 2, c.H],
    [c.rearTop, c.H - 0.035, ...open],
  ];
}

/** Side windows, windscreen and back glass, a finger's width proud of the greenhouse. */
function glazing(b, c, S) {
  const yb = c.belt - 0.06;
  const hFront = c.H - 0.03 - yb;
  const hRear = c.H - 0.035 - yb;
  const xScreen = (y) => c.cowl + ((c.screenTop - c.cowl) * (y - yb)) / hFront;
  const xBack = (y) => c.rearBase + ((c.rearTop - c.rearBase) * (y - yb)) / hRear;
  const y0 = c.belt + 0.035;
  const y1 = c.H - 0.085;
  const soup = new Soup();

  for (const s of [1, -1]) {
    const at = (x, y) => [x, y, s * (S.cab(x, y) + GLASS_LIFT)];
    const pane = (xa0, xb0, xa1, xb1) => soup.quadFacing([0, 0, s], at(xa0, y0), at(xb0, y0), at(xb1, y1), at(xa1, y1));
    const frontEdge = c.rearGlass ? c.pillarB + 0.035 : c.cabBack;
    pane(frontEdge, xScreen(y0) - c.pillarA, frontEdge, xScreen(y1) - c.pillarA);
    if (c.rearGlass) pane(xBack(y0) + c.pillarC, c.pillarB - 0.035, xBack(y1) + c.pillarC, c.pillarB - 0.035);
    if (c.quarterGlass) pane(xBack(y0) + 0.14, xBack(y0) + c.pillarC - 0.08, xBack(y1) + 0.14, xBack(y1) + c.pillarC - 0.08);
  }

  // Windscreen and back glass lie on the sloping faces, a little inside the pillars.
  const face = (xOf, nx, ny, yLow, yHigh) => {
    const len = Math.hypot(nx, ny);
    const ox = (nx / len) * GLASS_LIFT;
    const oy = (ny / len) * GLASS_LIFT;
    const half = (y) => (c.hw - CAB_INSET - CAB_BEVEL) * S.tumble(y) - 0.04;
    soup.quadFacing(
      [nx, ny, 0],
      [xOf(yLow) + ox, yLow + oy, half(yLow)], [xOf(yLow) + ox, yLow + oy, -half(yLow)],
      [xOf(yHigh) + ox, yHigh + oy, -half(yHigh)], [xOf(yHigh) + ox, yHigh + oy, half(yHigh)],
    );
  };
  face(xScreen, hFront, c.cowl - c.screenTop, c.belt + 0.03, c.H - 0.075);
  if (c.backGlass) face(xBack, -hRear, c.rearTop - c.rearBase, c.belt + 0.04, c.H - 0.08);
  b.add('@glass', soup.build(0));
}

/** Roof on six posts: what is left of a greenhouse when the glass is gone. */
function cabinFrame(b, c, S, slot) {
  const yb = c.belt - 0.02;
  const top = c.H - 0.06;
  const roof = [
    [c.rearTop, c.H - 0.095],
    [c.screenTop, c.H - 0.09],
    [c.screenTop, c.H - 0.03],
    [(c.screenTop + c.rearTop) / 2, c.H],
    [c.rearTop, c.H - 0.035],
  ];
  const soup = prism(roof, -(c.hw - CAB_INSET), c.hw - CAB_INSET, { bevel: 0.03 });
  soup.warp(S.warpCab);
  b.add(slot, soup.build(40));
  for (const s of [1, -1]) {
    const post = (x0, x1) => b.bar(slot, [x0, yb, s * (S.cab(x0, yb) - 0.03)], [x1, top, s * (S.cab(x1, top) - 0.03)], 0.055);
    post(c.cowl - 0.04, c.screenTop);
    post(c.pillarB, c.pillarB);
    post(c.rearBase + 0.06, c.rearTop);
  }
}

/** A road wheel at (x, y, z); `side` = +1 when its outer face looks toward +Z. */
export function wheel(b, x, y, z, side, w, style, tyre = true) {
  const half = w.w / 2;
  const m = xf(x, y, z, (side * Math.PI) / 2, 0, 0);
  const N = WHEEL_SEGMENTS;
  if (tyre) b.add('tire', latheGeo([[0, -half], [w.r, -half], [w.r, half], [w.rim, half]], N), m);
  if (style === 'alloy') {
    b.add('chrome', latheGeo([[w.rim, half], [w.rim - 0.015, half - 0.055]], N), m);
    b.add('metal_dark', latheGeo([[w.rim - 0.015, half - 0.055], [0, half - 0.055]], N), m);
    const spokes = new Soup();
    for (let k = 0; k < 5; k++) {
      const a = (k / 5) * Math.PI * 2;
      const c = Math.cos(a);
      const s = Math.sin(a);
      const at = (r, t) => [c * r - s * t, half - 0.012, s * r + c * t];
      spokes.quadFacing([0, 1, 0], at(0.03, -0.04), at(w.rim - 0.012, -0.028), at(w.rim - 0.012, 0.028), at(0.03, 0.04));
    }
    b.add('chrome', spokes.build(0), m);
    return;
  }
  const slot = style === 'steel' ? 'metal_dark' : style === 'rust' ? 'steel_rust' : 'chrome';
  b.add(slot, latheGeo([[w.rim, half], [w.rim - 0.012, half - 0.04], [0, half - 0.012]], N), m);
  if (style === 'steel') b.add('chrome', latheGeo([[0.075, half - 0.03], [0.055, half + 0.004], [0, half + 0.008]], 8), m);
  if (!tyre) b.add(slot, latheGeo([[0, -half], [w.rim, -half], [w.rim, half]], N), m);
}

/** The inner tyre of a twin rear wheel. */
function innerTyre(b, x, y, z, side, w) {
  const half = w.w / 2;
  b.add('tire', latheGeo([[0, -half], [w.r, -half], [w.r, half], [0, half]], WHEEL_SEGMENTS), xf(x, y, z, (side * Math.PI) / 2, 0, 0));
}

/** A brake disc on a hub: what a car on stands shows where its wheels were. */
function hub(b, x, y, z, side) {
  const m = xf(x, y, z, (side * Math.PI) / 2, 0, 0);
  b.add('steel_rust', latheGeo([[0, -0.02], [0.15, -0.02], [0.15, 0.02], [0.08, 0.02], [0.08, 0.07], [0, 0.07]], 10), m);
}

function bumper(b, slot, xFace, y, halfWidth, dir, height = 0.19) {
  const d = 0.17;
  const h = height / 2;
  const outline = [[0, -h + 0.035], [0.05, -h], [d, -h], [d, h], [0.05, h], [0, h - 0.035]].map(([dx, dy]) => [xFace - dir * dx, y + dy]);
  b.prism(slot, outline, -halfWidth, halfWidth, { bevel: 0.02 });
}

/** An open-topped box seen from inside: floor, roof, two walls and the far end (at x1). */
function loadSpace(b, slot, x0, x1, y0, y1, zi) {
  const inner = new Soup();
  inner.quadFacing([0, 1, 0], [x0, y0, zi], [x1, y0, zi], [x1, y0, -zi], [x0, y0, -zi]);
  inner.quadFacing([0, -1, 0], [x0, y1, zi], [x1, y1, zi], [x1, y1, -zi], [x0, y1, -zi]);
  inner.quadFacing([0, 0, -1], [x0, y0, zi], [x1, y0, zi], [x1, y1, zi], [x0, y1, zi]);
  inner.quadFacing([0, 0, 1], [x0, y0, -zi], [x1, y0, -zi], [x1, y1, -zi], [x0, y1, -zi]);
  inner.quadFacing([-1, 0, 0], [x1, y0, zi], [x1, y0, -zi], [x1, y1, -zi], [x1, y1, zi]);
  b.add(slot, inner.build(0));
}

/**
 * Builds a car from a spec (see CAR) and returns the numbers its callers decorate with.
 * `plate` is the licence plate picture (atlas region).
 */
export function car(b, over = {}, plate = 'plate_0') {
  const c = { ...CAR, ...over, wheel: { ...CAR.wheel, ...over.wheel } };
  const S = shapeOf(c);
  const { hF, hR } = S;
  const gc = c.clearance;
  const front = c.L / 2;
  const skip = new Soup();

  // ---- sheet metal ----
  const body = new Soup();
  const under = new Soup();
  const outline = hullOutline(c, S);
  prism(outline.pts, -c.hw, c.hw, { bevel: HULL_BEVEL, soup: body, soups: { u: under, x: skip }, chords: outline.chords });
  body.warp(S.warpHull);
  under.warp(S.warpHull);
  b.add(c.paint, body.build(40));
  b.add(c.underSlot, under.build(40));

  if (c.glass) {
    const cab = prism(cabinOutline(c), -(c.hw - CAB_INSET), c.hw - CAB_INSET, { bevel: CAB_BEVEL, soups: { x: skip } });
    cab.warp(S.warpCab);
    b.add(c.cabinPaint || c.paint, cab.build(40));
    glazing(b, c, S);
  } else {
    cabinFrame(b, c, S, c.cabinPaint || c.paint);
  }

  // ---- wheels ----
  const w = c.wheel;
  for (const axle of [c.axleF, c.axleR]) {
    if (axle === null) continue;
    for (const s of [1, -1]) {
      const z = s * (S.side(axle, w.r) - w.w / 2 - 0.02);
      if (c.wheels === 'full') wheel(b, axle, w.r, z, s, w, w.style);
      else if (c.wheels === 'rims') wheel(b, axle, w.rim + c.drop, z, s, w, 'rust', false);
      else if (c.wheels === 'hubs') hub(b, axle, w.r, z - s * 0.06, s);
    }
  }

  // ---- nose ----
  const yBumper = gc + 0.3;
  const yLamp = c.hood[0] - 0.2;
  if (c.bumper) bumper(b, c.bumper, front, yBumper, S.side(hF, yBumper) + 0.03, 1);
  if (c.trim) {
    const zLamp = S.side(hF, yLamp) - 0.215;
    for (const s of [1, -1]) {
      b.box(c.headlights ? HEAD : LENS, [0.03, 0.125, 0.3], [hF - 0.002, yLamp, s * zLamp]);
      b.box(AMBER, [0.014, 0.05, 0.14], [front + 0.001, yBumper + 0.02, s * (S.side(hF, yBumper) - 0.16)]);
    }
    if (c.grille) b.box(c.grille, [0.024, 0.115, 2 * (zLamp - 0.175)], [hF - 0.004, yLamp, 0]);
    b.decal(plate, [front + 0.001, yBumper, 0], 0.3, 0.15, '+x');
  }

  // ---- tail ----
  const yTail = (c.deck ?? c.belt) - 0.24;
  if (c.tailTrim) {
    if (c.bumper) bumper(b, c.bumper, -front, yBumper, S.side(-hR, yBumper) + 0.03, -1);
    if (c.trim) {
      const zTail = S.side(-hR, yTail) - 0.23;
      for (const s of [1, -1]) b.box(TAIL, [0.03, 0.13, 0.34], [-hR + 0.004, yTail, s * zTail]);
      if (c.openTail === null && !c.bed) b.decal(plate, [-hR - 0.001, yTail, 0], 0.3, 0.15, '-x');
    }
  }

  // ---- flanks: mirrors, handles, door seams, rub strip ----
  if (c.trim) {
    const ra = w.r + ARCH_GAP;
    const seamTop = c.belt - HULL_BEVEL - 0.01;
    const seamLow = gc + 0.07;
    const doorFront = c.cowl - 0.02;
    const doors = c.rearGlass ? [doorFront, c.pillarB, c.rearBase + 0.42] : [doorFront, c.cabBack];
    const yStrip = gc + 0.42;
    const strip = [(c.axleR === null ? -hR : c.axleR + ra) + 0.06, c.axleF - ra - 0.06];
    const seams = new Soup();
    for (const s of [1, -1]) {
      b.box(c.mirror || c.paint, [0.11, 0.08, 0.07], [c.cowl - 0.1, c.belt + 0.07, s * (S.side(c.cowl, c.belt) + 0.025)]);
      b.box(DARK, [strip[1] - strip[0], 0.05, 0.014], [(strip[0] + strip[1]) / 2, yStrip, s * (S.side(0, yStrip) + 0.004)]);
      for (const x of doors) {
        const zt = s * (S.side(x, seamTop) + 0.003);
        const zl = s * (S.side(x, seamLow) + 0.003);
        seams.quadFacing([0, 0, s], [x - 0.007, seamLow, zl], [x + 0.007, seamLow, zl], [x + 0.007, seamTop, zt], [x - 0.007, seamTop, zt]);
      }
      for (const x of doors.slice(1)) {
        const y = c.belt - 0.15;
        b.box('chrome', [0.1, 0.022, 0.014], [x + 0.11, y, s * (S.side(x, y) + 0.004)]);
      }
    }
    b.add(DARK, seams.build(0));
  }

  return { c, S, hF, hR, yBumper, yLamp, yTail, front };
}

/** Lower body + greenhouse boxes: you can shoot over the bonnet, and a crouching player is hidden behind the body. */
export function carColliders(b, c, lift = 0, flags = {}) {
  const half = c.hw + 0.02;
  // A raised car (on a lift) leaves the space under its sills free.
  b.collide([-c.L / 2, lift > 0 ? lift + c.clearance : 0, -half], [c.L / 2, lift + c.cover, half], { surface: 'car', ...flags });
  const zc = (c.hw - CAB_INSET) * (1 - c.tumble * 0.5);
  b.collide(
    [(c.rearBase + c.rearTop) / 2, lift + c.cover, -zc],
    [(c.cowl + c.screenTop) / 2, lift + c.H, zc],
    { surface: c.glass ? 'glass' : 'car', ...flags },
  );
}

// ------------------------------------------------------------------------------------------------
// Body styles
// ------------------------------------------------------------------------------------------------

const SUV = {
  L: 4.9, H: 1.78, hw: 0.94,
  wheel: { r: 0.4, w: 0.27, rim: 0.27, style: 'alloy' },
  axleF: 1.5, axleR: -1.42, clearance: 0.27,
  belt: 1.22, hood: [1.12, 1.2], deck: null,
  cowl: 1.0, screenTop: 0.45, rearTop: -2.12, rearBase: -2.33,
  tumble: 0.12, taperF: 0.07, taperR: 0.03,
  pillarB: -0.12, pillarC: 0.74, quarterGlass: true,
  bumper: '@paint', grille: 'chrome', cover: 1.24,
};

const PICKUP = {
  L: 5.3, H: 1.78, hw: 0.94,
  wheel: { r: 0.39, w: 0.27, rim: 0.25, style: 'steel' },
  axleF: 1.72, axleR: -1.5, clearance: 0.3,
  belt: 1.25, hood: [1.12, 1.22], deck: null,
  cowl: 1.22, screenTop: 0.72, rearTop: -0.42, rearBase: -0.5,
  tumble: 0.12, taperF: 0.06, taperR: 0,
  pillarB: 0.05, rearGlass: false, cabBack: -0.38,
  bed: { x1: -0.56, floor: 0.92 },
  bumper: 'chrome', grille: 'chrome', cover: 1.27,
};

const VAN = {
  L: 5.2, H: 2.14, hw: 0.94,
  wheel: { r: 0.36, w: 0.24, rim: 0.22, style: 'steel' },
  axleF: 1.7, axleR: -1.5, clearance: 0.26,
  belt: 1.16, hood: [1.02, 1.14], deck: null,
  cowl: 1.92, screenTop: 1.42, rearTop: -2.5, rearBase: -2.52,
  tumble: 0.07, taperF: 0.04, taperR: 0.015,
  pillarB: 0.52, rearGlass: false, backGlass: false, cabBack: 0.52,
  mirror: DARK, cover: 1.2,
};

/** The cab of the box truck, in its own frame (2.9 m long, no rear axle). */
const TRUCK_CAB = {
  L: 2.9, H: 2.28, hw: 1.04,
  wheel: { r: 0.44, w: 0.28, rim: 0.27, style: 'steel' },
  axleF: 0.7, axleR: null, clearance: 0.42,
  belt: 1.5, hood: [1.3, 1.45], deck: null,
  cowl: 0.28, screenTop: -0.06, rearTop: -1.3, rearBase: -1.33,
  tumble: 0.08, taperF: 0.08, taperR: 0,
  pillarB: -1.0, rearGlass: false, backGlass: false, cabBack: -0.9,
  bumper: 'chrome', grille: 'chrome', mirror: DARK, tailTrim: false,
};

// ------------------------------------------------------------------------------------------------
// Registration
// ------------------------------------------------------------------------------------------------

export function registerVehicles(R) {
  R.add('sedan', {
    variants: 4,
    colors: CAR_COLORS,
    dome: 0.14,
    build(b, o) {
      const { c } = car(b, { wheel: { style: o.variantIndex % 2 ? 'steel' : 'cap' } }, `plate_${o.variantIndex}`);
      carColliders(b, c);
    },
  });

  R.add('taxi', {
    colors: [palette.taxi],
    dome: 0.3,
    build(b) {
      const { c, S } = car(b, { wheel: { style: 'steel' } }, 'plate_taxi');
      carColliders(b, c);
      // Roof light: a lit box with the medallion number, on a dark foot.
      const x = (c.screenTop + c.rearTop) / 2 + 0.18;
      b.box(DARK, [0.3, 0.025, 0.2], [x, c.H + 0.008, 0]);
      b.box(glow(0xffd24a, 1.15), [0.16, 0.085, 0.4], [x, c.H + 0.058, 0]);
      b.decal('taxi_roof', [x + 0.08, c.H + 0.058, 0], 0.36, 0.075, '+x', { lit: true, lift: 0.002 });
      b.decal('taxi_roof', [x - 0.08, c.H + 0.058, 0], 0.36, 0.075, '-x', { lit: true, lift: 0.002 });
      for (const s of [1, -1]) {
        // Lettering on the front door, the checker band under the windows.
        const yDoor = c.belt - 0.37;
        b.decal('taxi_door', [(c.pillarB + c.cowl) / 2, yDoor, s * S.side(0, yDoor)], 0.92, 0.37, S.flank(s));
        const yBand = c.belt - 0.09;
        const x0 = c.rearBase + 0.05;
        const x1 = c.cowl - 0.05;
        b.decal('checker', [(x0 + x1) / 2, yBand, s * S.side(0, yBand)], x1 - x0, 0.07, S.flank(s));
      }
    },
  });

  R.add('suv', {
    variants: 2,
    colors: SUV_COLORS,
    dome: 0.1,
    build(b, o) {
      const { c, S } = car(b, SUV, `plate_${1 + o.variantIndex}`);
      carColliders(b, c);
      // Roof rails and running boards.
      for (const s of [1, -1]) {
        const z = s * (S.cab(0, c.H) - 0.1);
        b.box(DARK, [2.3, 0.022, 0.045], [-0.75, c.H + 0.03, z]);
        for (const x of [-1.8, -0.75, 0.3]) b.box(DARK, [0.06, 0.03, 0.045], [x, c.H + 0.008, z]);
        b.box('chrome', [2.0, 0.035, 0.13], [0.04, c.clearance + 0.045, s * (S.side(0, c.clearance) + 0.03)]);
      }
    },
  });

  R.add('pickup', {
    variants: 2,
    colors: TRUCK_COLORS,
    dome: 0.08,
    build(b, o) {
      const plate = `plate_${2 + o.variantIndex}`;
      const { c, hR, yBumper } = car(b, PICKUP, plate);
      b.collide([-c.L / 2, 0, -0.96], [c.L / 2, c.cover, 0.96], { surface: 'car' });
      b.collide([-0.45, c.cover, -0.8], [(c.cowl + c.screenTop) / 2, c.H, 0.8], { surface: 'glass' });
      // Bed: two walls and a tailgate on the load floor, a dark liner inside.
      const { x1, floor } = c.bed;
      const wallH = c.belt - floor + 0.02;
      const len = x1 + hR - 0.02;
      const xm = (x1 - hR) / 2 - 0.01;
      const yWall = floor + wallH / 2 - 0.02;
      for (const s of [1, -1]) b.box('@paint', [len, wallH, 0.07], [xm, yWall, s * (c.hw - 0.03)]);
      b.box('@paint', [0.06, wallH, 2 * c.hw - 0.02], [-hR + 0.03, yWall, 0]);
      b.box(DARK, [len - 0.08, 0.02, 2 * c.hw - 0.16], [xm, floor + 0.012, 0]);
      b.decal(plate, [-c.L / 2 - 0.001, yBumper, 0], 0.3, 0.15, '-x');
      // Something in the back: a spare and a crate.
      b.cyl('tire', 0.33, 0.2, [-1.3, floor + 0.12, 0.3], { seg: 10 });
      b.box('wood', [0.5, 0.4, 0.42], [-2.0, floor + 0.22, -0.36], { rot: [0, 0.25, 0] });
    },
  });

  R.add('van', {
    colors: VAN_COLORS,
    // The Vultures' van is always the same dark thing unless the level says otherwise.
    color: (o) => (o.variant === 'vulture' ? VULTURE_VAN : undefined),
    key: (o) => `${o.variant === 'vulture' ? 'vulture' : ''}${vanOpen(o) ? ' open' : ''}`,
    build(b, o) {
      buildVan(b, o.variant === 'vulture', vanOpen(o));
    },
  });

  R.add('box_truck', {
    variants: 2,
    colors: BOX_COLORS,
    build: buildBoxTruck,
  });

  R.add('burned_car', {
    paint: 'steel_rust',
    build: buildBurnedCar,
  });

  R.add('motorbike', {
    colors: [0x8f1f1c, 0x14161a, 0x1b2a4a, 0xc9a23a],
    build: buildMotorbike,
  });

  R.add('food_cart', {
    key: (o) => (o.lit === false ? 'off' : ''),
    build(b, o) {
      buildFoodCart(b, o.lit !== false);
    },
  });

  R.add('ipx_truck', {
    // Gloss black in the car paint (it shares the cars' material and holds a clean sheen in the sun).
    paint: 'car_paint',
    color: () => 0x17191d,
    // Never merged (doors and lamps move): the dull parts share one vertex-coloured paint.
    flatten: { keep: ['gold', 'chrome', 'metal_galv'] },
    build: buildIpxTruck,
    rig: rigIpxTruck,
  });
}

const vanOpen = (o) => (o.variant === 'vulture' ? o.open !== false : !!o.open);

// ------------------------------------------------------------------------------------------------
// Van
// ------------------------------------------------------------------------------------------------

function buildVan(b, vulture, open) {
  const floor = 0.6;
  const { c, S, hR } = car(b, { ...VAN, openTail: open ? floor : null }, vulture ? 'plate_3' : 'plate_1');
  b.collide([-c.L / 2, 0, -0.96], [c.L / 2, c.H, 0.96], { surface: 'car' });

  const doorTop = c.H - 0.1;
  const doorH = doorTop - floor;
  const doorW = c.hw - 0.09;
  const yDoor = floor + doorH / 2;
  if (!open) {
    // Closed barn doors: a seam, two handles, two small dark panes.
    b.box(DARK, [0.012, doorH, 0.014], [-hR - 0.002, yDoor, 0]);
    for (const s of [1, -1]) {
      b.box('chrome', [0.02, 0.1, 0.03], [-hR - 0.008, 1.05, s * 0.07]);
      b.box('@glass', [0.012, 0.36, 0.5], [-hR - 0.004, 1.62, s * 0.4]);
    }
  } else {
    // Open: both doors swung wide, a bare load space with whatever the crew left behind.
    const x0 = -hR + 0.02;
    const zi = c.hw - 0.18;
    const top = c.H - 0.1;
    loadSpace(b, 'metal_dark', x0, c.cabBack - 0.1, floor, top, zi);
    // The door frame closes the gap between the load space and the skin.
    b.box('@paint', [0.05, 0.1, 2 * c.hw - 0.1], [-hR + 0.035, floor - 0.045, 0]);
    b.box('@paint', [0.05, 0.1, 2 * c.hw - 0.2], [-hR + 0.035, top + 0.04, 0]);
    for (const s of [1, -1]) {
      b.box('@paint', [0.05, top - floor + 0.1, 0.13], [-hR + 0.035, (top + floor) / 2, s * (zi + 0.055)]);
      // A door is authored hinged at its outer edge, then turned about the hinge: one further round than the other.
      b.push(xf(-hR + 0.01, yDoor, s * (c.hw - 0.05), 0, s * (s > 0 ? 1.95 : 1.55), 0));
      b.box('@paint', [0.045, doorH, doorW], [0, 0, (-s * doorW) / 2]);
      b.box('@glass', [0.012, 0.36, doorW * 0.6], [-0.03, 0.42, (-s * doorW) / 2]);
      b.box(DARK, [0.02, doorH - 0.12, doorW - 0.12], [0.026, 0, (-s * doorW) / 2]);
      b.pop();
    }
    b.box('cardboard', [0.5, 0.36, 0.42], [x0 + 0.5, floor + 0.18, 0.3], { rot: [0, 0.2, 0] });
    b.box('cardboard', [0.4, 0.3, 0.36], [x0 + 0.45, floor + 0.51, 0.28], { rot: [0, -0.15, 0] });
    b.box('wood', [0.7, 0.34, 0.5], [x0 + 1.3, floor + 0.17, -0.34]);
  }
  b.box(DARK, [0.5, 0.06, 0.5], [-0.9, c.H + 0.02, 0]); // roof vent

  if (vulture) {
    // The crew's mark sprayed on both flanks, a blood-red stripe, a scrawl by the door.
    for (const s of [1, -1]) {
      b.decal('vulture', [-1.0, 1.64, s * S.cab(-1.0, 1.64)], 1.15, 0.92, S.cabFlank(s));
      b.box(M('paint_red', { color: 0x5a0f14 }), [3.7, 0.09, 0.012], [-0.6, 0.78, s * (S.side(0, 0.78) + 0.004)]);
      b.decal(s > 0 ? 'tag_b' : 'tag_a', [1.1, 0.98, s * S.side(1.1, 0.98)], 0.66, 0.29, S.flank(s));
    }
  }
}

// ------------------------------------------------------------------------------------------------
// Box truck
// ------------------------------------------------------------------------------------------------

function buildBoxTruck(b, o, env) {
  const L = 7.4;
  const cabX = L / 2 - TRUCK_CAB.L / 2; // origin of the cab's own frame
  const plate = `plate_${o.variantIndex}`;
  b.push(xf(cabX, 0, 0));
  const { c } = car(b, { ...TRUCK_CAB, paint: M('car_paint', { color: 0xd9d7d0 }) }, plate);
  for (const s of [1, -1]) {
    // Mirrors on stalks.
    b.box(DARK, [0.05, 0.36, 0.14], [c.cowl - 0.1, c.belt + 0.3, s * (c.hw + 0.1)]);
    b.stick(DARK, [c.cowl - 0.1, c.belt + 0.15, s * (c.hw - 0.02)], [c.cowl - 0.1, c.belt + 0.3, s * (c.hw + 0.1)], 0.015, { seg: 4 });
  }
  for (const z of [-0.6, -0.3, 0, 0.3, 0.6]) b.box(MARKER, [0.05, 0.035, 0.09], [c.screenTop - 0.12, c.H + 0.012, z]);
  b.pop();

  // Cargo box on a ladder frame.
  const x1 = cabX - TRUCK_CAB.L / 2 + 0.12; // front wall of the box, tucked behind the cab
  const x0 = -L / 2 + 0.06;
  const floor = 1.05;
  const top = 3.3;
  const hw = 1.2;
  const len = x1 - x0;
  const xm = (x0 + x1) / 2;
  const ym = (top + floor) / 2;
  b.box('@paint', [len, top - floor, 2 * hw], [xm, ym, 0]);
  // Aluminium corner rails and the roll-up door.
  for (const s of [1, -1]) {
    const z = s * (hw + 0.006);
    b.box('metal_galv', [len + 0.02, 0.07, 0.03], [xm, top - 0.03, z]);
    b.box('metal_galv', [len + 0.02, 0.09, 0.03], [xm, floor + 0.04, z]);
    b.box('metal_galv', [0.07, top - floor, 0.03], [x1 - 0.03, ym, z]);
    b.box('metal_galv', [0.07, top - floor, 0.03], [x0 + 0.03, ym, z]);
    b.box('metal_galv', [0.03, top - floor, 0.08], [x0 - 0.006, ym, s * (hw - 0.04)]);
  }
  b.box('metal_galv', [0.03, 0.1, 2 * hw], [x0 - 0.006, top - 0.05, 0]);
  const xd = x0 - 0.004;
  b.quad('roll_gate', [xd, floor + 0.06, -hw + 0.08], [xd, floor + 0.06, hw - 0.08], [xd, top - 0.1, hw - 0.08], [xd, top - 0.1, -hw + 0.08]);
  b.box(DARK, [0.03, 0.05, 0.3], [x0 - 0.02, floor + 0.2, 0]);
  // Chassis: rails, cross members, rear axle with twin tyres, tank, battery box, step bumper, mud flaps.
  for (const s of [1, -1]) b.box('metal_dark', [len + 0.6, 0.2, 0.09], [xm + 0.3, floor - 0.16, s * 0.42]);
  for (const x of [x0 + 0.5, xm, x1 - 0.4]) b.box('metal_dark', [0.1, 0.12, 2 * hw - 0.2], [x, floor - 0.06, 0]);
  const axle = x0 + 1.55;
  const w = { r: 0.44, w: 0.26, rim: 0.27 };
  for (const s of [1, -1]) {
    wheel(b, axle, w.r, s * (hw - 0.16), s, w, 'steel');
    innerTyre(b, axle, w.r, s * (hw - 0.46), s, w);
    b.box('rubber', [0.02, 0.5, 0.56], [axle - 0.62, 0.52, s * (hw - 0.3)]);
    b.box(TAIL, [0.03, 0.1, 0.2], [x0 - 0.01, floor - 0.12, s * (hw - 0.22)]);
    b.box(glow(0xff1a10, 1.2), [0.03, 0.035, 0.08], [x0 - 0.01, top - 0.04, s * (hw - 0.1)]);
    b.box('metal_dark', [0.08, 0.4, 0.08], [x0 + 0.06, 0.74, s * 0.5]);
  }
  b.box('metal_dark', [0.12, 0.14, 2 * hw - 0.1], [x0 + 0.02, 0.55, 0]);
  b.cyl('metal_galv', 0.26, 0.9, [xm + 0.9, 0.62, hw - 0.36], { axis: 'x', seg: 10 });
  b.box('metal_dark', [0.5, 0.36, 0.4], [xm + 0.9, 0.6, -(hw - 0.3)]);
  b.decal(plate, [x0 - 0.02, floor - 0.12, 0], 0.3, 0.15, '-x');

  // No box truck in Queens stays clean: a tag on each flank, from the material library's spray can.
  const tags = [['RULE', 0xe9e4d6], ['HOLLIS', 0xf6c21a]];
  [1, -1].forEach((s, i) => {
    const [text, color] = tags[(i + o.variantIndex) % tags.length];
    const tag = env.G.mats.graffiti(text, o.variantIndex * 2 + i, color);
    const k = Math.min(2.6 / tag.w, 1.2 / tag.h);
    const gw = (tag.w * k) / 2;
    const gh = (tag.h * k) / 2;
    const z = s * (hw + 0.008);
    const x = xm - 0.4 + i * 0.8;
    const y = floor + 0.85;
    b.quad(
      b.own(tag.material),
      [x - s * gw, y - gh, z], [x + s * gw, y - gh, z], [x + s * gw, y + gh, z], [x - s * gw, y + gh, z],
      { uv: tag.uv || [0, 0, 1, 1] },
    );
  });

  b.collide([x0, 0, -hw], [x1 + 0.2, top, hw], { surface: 'car' });
  b.collide([x1 + 0.2, 0, -1.06], [L / 2, 2.28, 1.06], { surface: 'car' });
}

// ------------------------------------------------------------------------------------------------
// Burned-out car
// ------------------------------------------------------------------------------------------------

function buildBurnedCar(b) {
  const char = M('steel_rust', { color: 0x1c1613 });
  const drop = 0.125; // it sits on its rims
  b.push(xf(0, -drop, 0));
  const { c, S } = car(b, {
    L: 4.5, H: 1.425, hw: 0.86, drop,
    glass: false, trim: false, bumper: null, wheels: 'rims',
    cabinPaint: char, underSlot: char,
  });
  // Charred cabin floor, what is left of the seats, the wheel.
  const zi = c.hw - 0.1;
  const yf = c.belt + 0.006;
  b.quad(char, [c.rearBase + 0.1, yf, zi], [c.cowl - 0.05, yf, zi], [c.cowl - 0.05, yf, -zi], [c.rearBase + 0.1, yf, -zi]);
  for (const z of [0.38, -0.38]) b.box(char, [0.1, 0.34, 0.46], [0.05, c.belt + 0.14, z], { rot: [0, 0, 0.2] });
  b.box(char, [0.1, 0.3, 1.3], [-0.95, c.belt + 0.12, 0], { rot: [0, 0, 0.25] });
  b.cyl(char, 0.17, 0.03, [0.55, c.belt + 0.12, 0.38], { rot: [0, 0, 1.0], seg: 8 });
  // Bonnet sprung open over a black engine bay.
  const hood0 = S.hF - 0.14;
  const hood1 = c.cowl + 0.04;
  const hz = S.side(1.6, 1.0) - 0.07;
  b.quad(char, [hood1, 1.062, hz], [hood0, 0.975, hz], [hood0, 0.975, -hz], [hood1, 1.062, -hz]);
  b.push(xf(hood1, 1.07, 0, 0, 0, 0.27));
  b.box('@paint', [hood0 - hood1, 0.03, 2 * hz], [(hood0 - hood1) / 2, 0, 0]);
  b.pop();
  b.pop();
  b.collide([-2.25, 0, -0.88], [2.25, 0.96, 0.88], { surface: 'car' });
  b.collide([-1.3, 0.96, -0.72], [0.65, 1.3, 0.72], { surface: 'car', bulletOnly: true });
  b.anchor('smolder', [1.5, 1.0, 0], [0, 1, 0]);
}

// ------------------------------------------------------------------------------------------------
// Motorbike
// ------------------------------------------------------------------------------------------------

function buildMotorbike(b) {
  // Leaning on its side stand: everything is authored upright, then tipped.
  b.push(xf(0, 0, 0.05, -0.12, 0, 0));
  const r = 0.31;
  const tyre = [[0.2, -0.05], [r - 0.03, -0.062], [r, -0.03], [r, 0.03], [r - 0.03, 0.062], [0.2, 0.05]];
  for (const x of [0.66, -0.66]) {
    const m = xf(x, r, 0, Math.PI / 2, 0, 0);
    b.add('tire', latheGeo(tyre, 14), m);
    b.add('chrome', latheGeo([[0.2, 0.035], [0.2, -0.035]], 14), m);
    b.add('metal_dark', latheGeo([[0, -0.02], [0.2, -0.012]], 10), m);
    b.add('metal_dark', latheGeo([[0.2, 0.012], [0, 0.02]], 10), m);
    b.cyl('chrome', 0.045, 0.14, [x, r, 0], { axis: 'z', seg: 8 });
  }
  // Fork, frame, swing arm, shocks, exhausts.
  for (const s of [1, -1]) {
    b.stick('chrome', [0.66, r, s * 0.075], [0.4, 0.92, s * 0.075], 0.022, { seg: 6 });
    b.stick('metal_dark', [-0.66, r, s * 0.07], [-0.15, 0.42, s * 0.07], 0.022, { seg: 5 });
    b.stick('chrome', [-0.62, 0.36, s * 0.13], [0.0, 0.3, s * 0.13], 0.04, { seg: 7, caps: true });
    b.stick('chrome', [-0.2, 0.42, s * 0.1], [-0.52, 0.72, s * 0.1], 0.016, { seg: 5 });
  }
  b.pipe('metal_dark', [[0.4, 0.86, 0], [-0.1, 0.72, 0], [-0.55, 0.74, 0]], 0.028, { seg: 6 });
  b.pipe('metal_dark', [[0.36, 0.8, 0], [0.2, 0.36, 0], [-0.2, 0.34, 0], [-0.3, 0.7, 0]], 0.024, { seg: 6 });
  // Engine, tank, seat, tail, lamp.
  b.box('metal_galv', [0.34, 0.26, 0.26], [0.0, 0.46, 0]);
  b.box('metal_dark', [0.24, 0.12, 0.3], [0.02, 0.62, 0]);
  b.cyl('metal_galv', 0.1, 0.3, [-0.02, 0.36, 0], { axis: 'z', seg: 8 });
  const tank = latheGeo([[0, -0.26], [0.11, -0.23], [0.15, -0.05], [0.13, 0.16], [0.07, 0.25], [0, 0.26]], 8);
  b.add('@paint', tank, xf(0.08, 0.86, 0, 0, 0, Math.PI / 2 - 0.1, 1, 1, 0.95));
  b.box('rubber', [0.56, 0.08, 0.24], [-0.38, 0.84, 0], { rot: [0, 0, 0.04] });
  b.box('@paint', [0.3, 0.07, 0.2], [-0.74, 0.8, 0], { rot: [0, 0, -0.22] });
  b.box('@paint', [0.3, 0.03, 0.13], [0.72, r + 0.36, 0], { rot: [0, 0, -0.25] }); // front mudguard
  b.cyl('chrome', 0.085, 0.12, [0.5, 0.9, 0], { axis: 'x', seg: 10 });
  b.box(glow(0xfff0d0, 0.5), [0.012, 0.11, 0.11], [0.565, 0.9, 0]);
  b.box(TAIL, [0.02, 0.05, 0.1], [-0.9, 0.76, 0]);
  // Bars, mirrors.
  b.pipe('chrome', [[0.36, 1.0, -0.25], [0.38, 0.97, -0.1], [0.38, 0.97, 0.1], [0.36, 1.0, 0.25]], 0.014, { seg: 5 });
  for (const s of [1, -1]) {
    b.cyl('rubber', 0.02, 0.1, [0.36, 1.0, s * 0.24], { axis: 'z', seg: 6 });
    b.stick('chrome', [0.37, 0.99, s * 0.17], [0.34, 1.055, s * 0.2], 0.006, { seg: 4 });
    b.box('chrome', [0.012, 0.045, 0.07], [0.34, 1.06, s * 0.21]);
  }
  b.pop();
  b.stick('metal_dark', [-0.1, 0.3, 0.02], [-0.16, 0.01, 0.3], 0.014, { seg: 4 }); // side stand
  b.collide([-0.98, 0, -0.3], [0.98, 0.95, 0.3], { surface: 'metal' });
}

// ------------------------------------------------------------------------------------------------
// Food cart
// ------------------------------------------------------------------------------------------------

function buildFoodCart(b, lit) {
  const steel = 'metal_galv';
  // Stainless body on two wheels and a jockey leg.
  b.box(steel, [1.7, 0.72, 0.86], [-0.1, 0.62, 0]);
  b.box('chrome', [1.78, 0.035, 0.94], [-0.1, 0.995, 0]);
  b.box('chrome', [1.74, 0.02, 0.9], [-0.1, 0.27, 0]);
  for (const s of [1, -1]) {
    const m = xf(-0.25, 0.2, s * 0.5, (s * Math.PI) / 2, 0, 0);
    b.add('tire', latheGeo([[0, -0.05], [0.2, -0.05], [0.2, 0.05], [0.12, 0.05]], 10), m);
    b.add(steel, latheGeo([[0.12, 0.05], [0, 0.035]], 10), m);
    b.box(steel, [0.52, 0.03, 0.14], [-0.25, 0.43, s * 0.5]); // mudguard
  }
  b.stick('metal_dark', [0.62, 0.3, 0], [0.62, 0.0, 0], 0.025, { seg: 6 });
  b.pipe('metal_dark', [[0.75, 0.32, 0], [1.12, 0.32, 0], [1.19, 0.4, 0]], 0.022, { seg: 5 }); // tow bar
  // Worktop: steam pan with its lid ajar, a griddle, bottles, a napkin box.
  b.box('metal_dark', [0.52, 0.03, 0.36], [0.28, 1.02, 0.12]);
  b.box('chrome', [0.5, 0.012, 0.34], [0.3, 1.08, 0.1], { rot: [0.28, 0, 0] });
  b.box('metal_dark', [0.56, 0.05, 0.4], [-0.5, 1.03, 0.1]);
  for (const [x, z, color] of [[-0.86, -0.3, 0xc2261e], [-0.76, -0.3, 0xf2c21a], [-0.66, -0.32, 0x6b4a1e]]) {
    b.cyl('@vc', 0.032, 0.17, [x, 1.1, z], { seg: 6, color });
    b.cyl('@vc', 0.012, 0.05, [x, 1.21, z], { seg: 5, color: 0xf4f2ec });
  }
  b.box('@vc', [0.2, 0.1, 0.14], [0.08, 1.06, -0.3], { color: 0xd9d7d0 });
  // Sneeze guard and the menu board, on both long sides.
  b.box(M('glass_store', { transparent: true, opacity: 0.32 }), [1.5, 0.3, 0.012], [-0.1, 1.17, 0.44]);
  for (const x of [-0.84, 0.64]) b.box('chrome', [0.02, 0.32, 0.02], [x, 1.17, 0.44]);
  b.decal('cart_menu', [-0.1, 0.62, 0.43], 1.5, 0.52, '+z');
  b.decal('cart_menu', [-0.1, 0.62, -0.43], 1.5, 0.52, '-z');
  // Umbrella: eight panels in two colours, on a mast through the worktop.
  const mast = [-0.1, -0.03];
  b.stick(steel, [mast[0], 1.0, mast[1]], [mast[0], 2.2, mast[1]], 0.02, { seg: 6 });
  const yRim = 1.9;
  const top = [mast[0], 2.23, mast[1]];
  const panels = [new Soup(), new Soup()];
  for (let i = 0; i < 8; i++) {
    // The canopy is wider along the cart than across it.
    const corner = (k) => {
      const a = (k / 8) * Math.PI * 2;
      return [mast[0] + Math.cos(a) * 1.08, yRim, mast[1] + Math.sin(a) * 0.66];
    };
    const p0 = corner(i);
    const p1 = corner(i + 1);
    const d0 = [p0[0], yRim - 0.12, p0[2]];
    const d1 = [p1[0], yRim - 0.12, p1[2]];
    const soup = panels[i % 2];
    soup.tri(top, p1, p0).tri(top, p0, p1); // both faces: you stand under it
    soup.quad(p0, p1, d1, d0).quad(p1, p0, d0, d1); // valance flap
    b.stick(steel, top, p0, 0.008, { seg: 3 });
  }
  b.add(M('fabric_awning', { color: 0xc2261e }), panels[0].build(0));
  b.add(M('fabric_awning', { color: 0xe9c21a }), panels[1].build(0));
  if (lit) {
    b.box(glow(0xffe2a8, 2.6), [0.07, 0.07, 0.07], [mast[0] + 0.3, 1.78, 0.1]);
    b.lamp([mast[0] + 0.3, 1.7, 0.1], { color: 0xffd9a0, intensity: 16, range: 6, kind: 'work' });
  }
  b.collide([-0.98, 0, -0.5], [0.78, 1.25, 0.5], { surface: 'metal' });
  b.collide([-0.95, 1.85, -0.5], [0.75, 2.25, 0.5], { surface: 'cloth', bulletOnly: true, noNav: true });
  b.anchor('steam', [0.28, 1.1, 0.12], [0, 1, 0]);
  b.anchor('propane', [0.95, 0, -0.25], [0, 1, 0]);
}

// ------------------------------------------------------------------------------------------------
// The IPX truck
// ------------------------------------------------------------------------------------------------

const TRUCK = {
  L: 6.8,
  hw: 1.17,
  roof: 2.86,
  cabRoof: 2.58,
  floor: 1.02, // vault floor
  belt: 1.72, // base of the cab glass
  doorH: 1.62,
  doorSwing: 1.9, // radians, each rear door
  doorTime: 1.1, // seconds to swing open
  blink: 1.1, // hazard period, seconds
};

function buildIpxTruck(b) {
  const T = TRUCK;
  const h = T.L / 2;
  const hF = h - 0.14;
  const hR = h - 0.1;
  const r = 0.5;
  const gc = 0.46;
  const ra = r + 0.08;
  const reach = Math.sqrt(ra * ra - (r - gc) ** 2);
  const a0 = -Math.asin((r - gc) / ra);
  const axleF = 2.05;
  const axleR = -1.75;
  const cabBack = 0.55; // where the cab ends and the vault begins
  const gold = 'gold';

  // One armoured shell: sloped nose, upright split screen, a vault body a hand taller than the cab.
  const fold = 1.3; // the flanks are flat plate, angled in toward the nose from here
  const foldLow = [fold, gc, 'u'];
  const foldHigh = [fold, T.cabRoof];
  const outline = [
    [-hR, gc + 0.08, 'u'],
    [axleR - reach - 0.12, gc, 'u'],
    ...arc(axleR, r, ra, Math.PI - a0, a0, 8, 'u'),
    foldLow,
    ...arc(axleF, r, ra, Math.PI - a0, a0, 8, 'u'),
    [hF - 0.12, gc + 0.04],
    [hF, gc + 0.2],
    [hF, 1.12],
    [hF - 0.16, 1.32],
    [1.86, 1.52], // cowl
    [1.72, T.belt],
    [1.52, 2.5], // screen top
    foldHigh,
    [cabBack + 0.08, T.cabRoof],
    [cabBack - 0.06, T.roof],
    [-hR + 0.08, T.roof],
    [-hR, T.roof - 0.08, 'x'], // the rear wall is the vault doors
    [-hR, T.floor - 0.1],
  ];
  const body = new Soup();
  const under = new Soup();
  prism(outline, -T.hw, T.hw, {
    bevel: 0.06,
    soup: body,
    soups: { u: under, x: new Soup() },
    chords: [[outline.indexOf(foldHigh), outline.indexOf(foldLow)]],
  });
  const warp = (p) => {
    if (p[0] > fold) p[2] *= 1 - (0.07 * (p[0] - fold)) / (hF - fold);
  };
  body.warp(warp);
  under.warp(warp);
  b.add('@paint', body.build(38));
  b.add(DARK, under.build(38));
  const sideAt = (x, y) => {
    const p = [x, y, T.hw];
    warp(p);
    return p[2];
  };

  // ---- wheels: tall, twin at the back ----
  const w = { r, w: 0.3, rim: 0.3 };
  for (const s of [1, -1]) {
    wheel(b, axleF, r, s * (T.hw - 0.2), s, w, 'steel');
    wheel(b, axleR, r, s * (T.hw - 0.2), s, w, 'steel');
    innerTyre(b, axleR, r, s * (T.hw - 0.53), s, w);
  }

  // ---- glass: narrow and deep-set ----
  const glass = new Soup();
  const y0 = T.belt + 0.12;
  const y1 = 2.42;
  const xScreen = (y) => 1.72 + ((1.52 - 1.72) * (y - T.belt)) / (2.5 - T.belt);
  for (const s of [1, -1]) {
    const edge0 = s * (sideAt(xScreen(y0), y0) - 0.16);
    const edge1 = s * (sideAt(xScreen(y1), y1) - 0.16);
    glass.quadFacing(
      [1, 0.26, 0],
      [xScreen(y0) + 0.012, y0, s * 0.05], [xScreen(y0) + 0.012, y0, edge0],
      [xScreen(y1) + 0.012, y1, edge1], [xScreen(y1) + 0.012, y1, s * 0.05],
    );
    // Door window: a slot, not a pane.
    const zs0 = s * (sideAt(1.1, 1.9) + 0.008);
    const zs1 = s * (sideAt(1.1, 2.36) + 0.008);
    glass.quadFacing([0, 0, s], [0.82, 1.9, zs0], [1.5, 1.9, zs0], [1.42, 2.36, zs1], [0.82, 2.36, zs1]);
  }
  b.add('@glass', glass.build(0));
  b.box('@paint', [0.05, 0.75, 0.09], [1.63, 2.1, 0], { rot: [0, 0, 0.27] }); // centre post

  // ---- livery: a gold waist band, the mark on both flanks and the bonnet ----
  for (const s of [1, -1]) {
    const facing = s > 0 ? '+z' : '-z';
    const z = s * (T.hw + 0.006);
    b.box(gold, [cabBack + hR - 0.14, 0.11, 0.012], [(cabBack - hR) / 2 - 0.02, 1.36, z]);
    b.box(gold, [1.2, 0.11, 0.012], [1.22, 1.36, s * (sideAt(1.3, 1.36) + 0.006)]);
    b.decal('ipx_side', [-1.42, 2.1, z], 3.5, 0.875, facing);
    // Cab door: outline, handle, step.
    b.box(DARK, [0.014, 1.38, 0.012], [0.74, 1.72, s * (sideAt(0.74, 1.7) + 0.004)]);
    b.box(DARK, [0.014, 0.92, 0.012], [1.56, 1.5, s * (sideAt(1.56, 1.5) + 0.004)]);
    b.box('chrome', [0.14, 0.03, 0.02], [0.9, 1.58, s * (sideAt(0.9, 1.58) + 0.012)]);
    b.box('metal_galv', [0.72, 0.04, 0.2], [1.12, 0.74, s * (T.hw - 0.03)]);
    // Gun ports on the vault, a mirror on the cab, marker lamps under the roof line.
    for (const x of [-0.2, -2.3]) b.cyl(DARK, 0.06, 0.03, [x, 1.62, z], { axis: 'z', seg: 8 });
    b.box(DARK, [0.05, 0.3, 0.1], [1.58, 2.0, s * (T.hw + 0.02)]);
    for (const x of [-hR + 0.3, cabBack - 0.3]) b.box(MARKER, [0.1, 0.04, 0.012], [x, T.roof - 0.16, z]);
  }
  b.decal('ipx_mark', [2.5, 1.417, 0], 0.8, 0.33, { right: [0, 0, -1], up: [-0.987, 0.159, 0] }, { lift: 0.01 });

  // ---- nose: ram bumper, grille, lamps that are on (it is idling) ----
  bumper(b, 'metal_dark', h, gc + 0.22, T.hw * 0.95, 1, 0.3);
  b.box(DARK, [0.03, 0.34, 1.0], [hF + 0.002, 0.98, 0]);
  for (let i = 0; i < 4; i++) b.box('metal_galv', [0.02, 0.022, 0.96], [hF + 0.018, 0.86 + i * 0.08, 0]);
  for (const s of [1, -1]) {
    b.box(HEAD, [0.03, 0.17, 0.24], [hF + 0.004, 0.98, s * 0.68]);
    b.box(AMBER, [0.03, 0.08, 0.14], [hF + 0.004, 0.98, s * 0.9]);
    b.lamp([h + 0.6, 0.9, s * 0.68], { color: 0xfff0d0, intensity: 22, range: 9, kind: 'work', dir: [1, -0.25, 0] });
  }
  // Roof: clearance lamps over the screen, a hatch and a vent on the vault.
  for (const z of [-0.7, -0.35, 0, 0.35, 0.7]) b.box(MARKER, [0.05, 0.04, 0.1], [1.4, T.cabRoof + 0.02, z]);
  b.box('@paint', [0.8, 0.07, 0.8], [-1.2, T.roof + 0.03, 0]);
  b.box(DARK, [0.3, 0.1, 0.3], [-2.5, T.roof + 0.05, 0.5]);

  // ---- tail: step bumper, lamps, the door surround and the light over it ----
  const xTail = -hR;
  b.box('metal_dark', [0.24, 0.12, 2 * T.hw - 0.04], [-h + 0.12, T.floor - 0.34, 0]);
  b.decal('stripes_yb', [-h - 0.001, T.floor - 0.34, 0], 2 * T.hw - 0.2, 0.1, '-x');
  b.box('metal_galv', [0.2, 0.03, 1.5], [-h + 0.1, T.floor - 0.27, 0]);
  for (const s of [1, -1]) {
    b.box(glow(0xff1a10, 1.0), [0.03, 0.2, 0.12], [xTail - 0.004, 1.3, s * (T.hw - 0.11)]);
    b.box('@paint', [0.06, T.roof - T.floor - 0.04, 0.2], [xTail + 0.03, (T.roof + T.floor) / 2, s * (T.hw - 0.16)]); // jambs
  }
  b.box('@paint', [0.06, 0.3, 2 * T.hw - 0.12], [xTail + 0.03, T.roof - 0.21, 0]);
  b.box('@paint', [0.06, 0.14, 2 * T.hw - 0.12], [xTail + 0.03, T.floor - 0.04, 0]);
  b.box(DARK, [0.12, 0.05, 0.36], [xTail - 0.05, T.roof - 0.2, 0]);
  b.box(glow(0xfff1d6, 3.0), [0.08, 0.02, 0.3], [xTail - 0.06, T.roof - 0.235, 0]);
  b.lamp([xTail - 0.5, T.roof - 0.4, 0], { color: 0xfff1d6, intensity: 26, range: 9, kind: 'work', dir: [-0.3, -1, 0] });
  b.decal('plate_2', [xTail - 0.004, T.floor - 0.16, 0.62], 0.3, 0.15, '-x', { lift: 0.035 });

  // ---- the vault: only seen once the doors swing ----
  const vx0 = xTail + 0.07;
  const vx1 = cabBack - 0.2;
  const vz = T.hw - 0.27;
  const vTop = T.roof - 0.28;
  loadSpace(b, 'metal_galv', vx0, vx1, T.floor, vTop, vz);
  for (const s of [1, -1]) {
    // Racks along both walls with shelves for the reels.
    for (const y of [1.45, 1.9, 2.3]) b.box('metal_dark', [vx1 - vx0 - 0.3, 0.03, 0.26], [(vx0 + vx1) / 2, y, s * (vz - 0.14)]);
    for (const x of [vx0 + 0.3, (vx0 + vx1) / 2, vx1 - 0.3]) b.box('metal_dark', [0.04, vTop - T.floor, 0.04], [x, (T.floor + vTop) / 2, s * (vz - 0.26)]);
  }
  b.decal('ipx_mark', [vx1 - 0.001, 1.9, 0], 1.1, 0.46, '-x');

  // ---- moving parts ----
  const doorW = T.hw - 0.27;
  const yDoor = T.floor + 0.03 + T.doorH / 2;
  for (const s of [1, -1]) {
    b.node(s > 0 ? 'doorL' : 'doorR', [xTail, yDoor, s * (T.hw - 0.26)]);
    const zc = s * (T.hw - 0.26 - doorW / 2);
    b.box('@paint', [0.07, T.doorH, doorW - 0.01], [xTail - 0.005, yDoor, zc]);
    b.box(DARK, [0.03, T.doorH - 0.24, doorW - 0.24], [xTail - 0.04, yDoor, zc]);
    b.box(gold, [0.012, 0.11, doorW - 0.02], [xTail - 0.047, 1.36, zc]);
    b.box('@glass', [0.012, 0.22, 0.34], [xTail - 0.058, 2.2, zc]);
    b.cyl('chrome', 0.035, 0.05, [xTail - 0.07, 1.62, s * 0.12], { axis: 'x', seg: 8 });
    b.box('chrome', [0.03, 0.9, 0.035], [xTail - 0.07, 1.62, s * 0.05]);
    for (const y of [yDoor - 0.55, yDoor + 0.55]) b.box('metal_dark', [0.05, 0.14, 0.07], [xTail - 0.03, y, s * (T.hw - 0.27)]);
    if (s > 0) b.decal('ipx_mark', [xTail - 0.057, 1.75, zc], 0.62, 0.26, '-x', { lift: 0.002 });
    else b.decal('ipx_url', [xTail - 0.057, 1.75, zc], 0.74, 0.092, '-x', { lift: 0.002 });
  }

  // Hazards: all corners, switched as one.
  b.node('hazards');
  const hazard = glow(palette.hazard, 3.4);
  for (const s of [1, -1]) {
    b.box(hazard, [0.035, 0.11, 0.13], [xTail - 0.006, 1.52, s * (T.hw - 0.11)]);
    b.box(hazard, [0.035, 0.09, 0.15], [hF + 0.006, 0.98, s * 0.9]);
    b.box(hazard, [0.12, 0.05, 0.014], [h - 0.6, 1.2, s * (sideAt(h - 0.6, 1.2) + 0.006)]);
  }

  // The vault light: off until the doors open.
  b.node('vaultLight');
  b.box(glow(0xffe2a0, 3.2), [1.6, 0.03, 0.5], [(vx0 + vx1) / 2, vTop - 0.02, 0]);
  b.root();

  b.collide([-h, 0, -T.hw], [cabBack, T.roof, T.hw], { surface: 'car' });
  b.collide([cabBack, 0, -T.hw], [h, T.cabRoof, T.hw], { surface: 'car' });
  b.anchor('rearDoor', [-h - 0.9, 0, 0], [-1, 0, 0]);
  b.anchor('exhaust', [0.3, 0.5, -T.hw + 0.1], [0, 0, -1]);
}

/**
 * Extraction truck states (CONTRACT 6.2): 'idle' = hazards blinking, vault shut;
 * 'open' = the rear doors swing wide, the vault lights up and the hazards hold steady.
 */
function rigIpxTruck(prop) {
  const { doorL, doorR, hazards, vaultLight } = prop.nodes;
  let state = 'idle';
  let swing = 0; // 0 shut … 1 open
  let clock = 0;

  function pose() {
    const eased = swing * swing * (3 - 2 * swing);
    doorL.rotation.y = TRUCK.doorSwing * eased;
    doorR.rotation.y = -TRUCK.doorSwing * eased;
    vaultLight.visible = swing > 0.15;
  }
  pose();

  prop.state = state;
  prop.setState = (next) => {
    state = next === 'open' ? 'open' : 'idle';
    prop.state = state;
    if (state === 'idle') {
      swing = 0;
      pose();
    }
  };
  prop.update = (dt) => {
    clock += dt;
    hazards.visible = state === 'open' || clock % TRUCK.blink < TRUCK.blink * 0.5;
    if (state === 'open' && swing < 1) {
      swing = Math.min(1, swing + dt / TRUCK.doorTime);
      pose();
    }
  };
}
