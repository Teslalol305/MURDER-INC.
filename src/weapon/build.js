// Modelling kit for the viewmodels: a handful of solid generators and a triangle soup that bakes
// their paint into vertex attributes. Everything is real scale (metres) in gun space:
//   +X right, +Y up, −Z forward (down the barrel). Side profiles are written as [s, y] pairs where
//   s is the distance forward, so z = −s.
//
// Every vertex carries, besides position and normal:
//   color  linear RGB albedo
//   mre    roughness, metalness, emissive strength, finish code (see material.js)
//   rest   the model-space position the procedural finishes are painted in
// One material (material.js) reads all of it, so a whole gun is a few draw calls.

import * as THREE from 'three';

const TAU = Math.PI * 2;
const X = [1, 0, 0];
const Y = [0, 1, 0];
const _color = new THREE.Color();

export const FINISH = { plain: 0, brushed: 1, wood: 2, checker: 3, skin: 4, glove: 5 };

/**
 * A surface description. `hex` is an sRGB colour; `wear` (optional) is what chamfered edges show.
 */
export function paint(hex, rough, metal = 0, { glow = 0, finish = FINISH.plain, wear = null } = {}) {
  _color.set(hex);
  return { r: _color.r, g: _color.g, b: _color.b, rough, metal, glow, finish, wear };
}

// ------------------------------------------------------------------------------------------------
// Triangle soup
// ------------------------------------------------------------------------------------------------

const HASH = 1e5; // 0.01 mm: vertices closer than this share their normal

/**
 * Per-corner normals of a triangle list, averaged over the faces that meet at a position and lie
 * within `crease` radians of each other. Hard edges stay hard, curved skins come out smooth.
 */
function creasedNormals(pos, crease) {
  const count = pos.length / 3;
  const faces = count / 3;
  const faceN = new Float32Array(faces * 3);
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const c = new THREE.Vector3();
  const map = new Map();
  for (let f = 0; f < faces; f++) {
    const o = f * 9;
    a.set(pos[o], pos[o + 1], pos[o + 2]);
    b.set(pos[o + 3], pos[o + 4], pos[o + 5]);
    c.set(pos[o + 6], pos[o + 7], pos[o + 8]);
    b.sub(a);
    c.sub(a);
    b.cross(c); // length = twice the area: big faces weigh more
    faceN[f * 3] = b.x;
    faceN[f * 3 + 1] = b.y;
    faceN[f * 3 + 2] = b.z;
    for (let k = 0; k < 3; k++) {
      const p = o + k * 3;
      const key = `${Math.round(pos[p] * HASH)},${Math.round(pos[p + 1] * HASH)},${Math.round(pos[p + 2] * HASH)}`;
      let list = map.get(key);
      if (!list) map.set(key, (list = []));
      list.push(f);
    }
  }
  const out = new Float32Array(count * 3);
  const cosCrease = Math.cos(crease);
  for (let f = 0; f < faces; f++) {
    const fx = faceN[f * 3];
    const fy = faceN[f * 3 + 1];
    const fz = faceN[f * 3 + 2];
    const fl = Math.hypot(fx, fy, fz) || 1;
    for (let k = 0; k < 3; k++) {
      const p = f * 9 + k * 3;
      const key = `${Math.round(pos[p] * HASH)},${Math.round(pos[p + 1] * HASH)},${Math.round(pos[p + 2] * HASH)}`;
      const list = map.get(key);
      let nx = 0;
      let ny = 0;
      let nz = 0;
      for (let i = 0; i < list.length; i++) {
        const g = list[i] * 3;
        const gl = Math.hypot(faceN[g], faceN[g + 1], faceN[g + 2]) || 1;
        const dot = (fx * faceN[g] + fy * faceN[g + 1] + fz * faceN[g + 2]) / (fl * gl);
        if (dot >= cosCrease) {
          nx += faceN[g];
          ny += faceN[g + 1];
          nz += faceN[g + 2];
        }
      }
      const len = Math.hypot(nx, ny, nz) || 1;
      out[p] = nx / len;
      out[p + 1] = ny / len;
      out[p + 2] = nz / len;
    }
  }
  return out;
}

/** Collects painted solids and turns them into one BufferGeometry. */
export class Soup {
  constructor() {
    this.pos = [];
    this.nor = [];
    this.col = [];
    this.mre = [];
  }

  get triangles() {
    return this.pos.length / 9;
  }

  /**
   * Adds a solid. `geo` is a BufferGeometry (indexed or not; it is consumed).
   * opts: { crease   smoothing angle in radians (default 0.6),
   *         m        Matrix4 applied first,
   *         ao       0…1 how strongly downward faces are darkened (default 0.5) }
   * A `tag` attribute (0 / 1 per vertex) on the geometry marks chamfers that take `paint.wear`.
   */
  add(geo, p, { crease = 0.6, m = null, ao = 0.5 } = {}) {
    if (m) geo.applyMatrix4(m);
    const flat = geo.index ? geo.toNonIndexed() : geo;
    const pos = flat.getAttribute('position').array;
    const tag = flat.getAttribute('tag');
    const nor = creasedNormals(pos, crease);
    const wear = p.wear;
    for (let i = 0; i < pos.length; i += 3) {
      const ny = nor[i + 1];
      // Baked ambient shading: undersides sit in their own shadow, tops catch the sky.
      const shade = 1 + (ny > 0 ? 0.1 * ny : ao * 0.5 * ny);
      const worn = wear && tag && tag.array[i / 3] > 0.5;
      const src = worn ? wear : p;
      this.pos.push(pos[i], pos[i + 1], pos[i + 2]);
      this.nor.push(nor[i], ny, nor[i + 2]);
      this.col.push(src.r * shade, src.g * shade, src.b * shade);
      this.mre.push(src.rough, src.metal, src.glow, worn ? FINISH.plain : p.finish);
    }
    geo.dispose();
    if (flat !== geo) flat.dispose();
    return this;
  }

  build() {
    const geo = new THREE.BufferGeometry();
    const position = new Float32Array(this.pos);
    geo.setAttribute('position', new THREE.BufferAttribute(position, 3));
    geo.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(this.nor), 3));
    geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(this.col), 3));
    geo.setAttribute('mre', new THREE.BufferAttribute(new Float32Array(this.mre), 4));
    geo.setAttribute('rest', new THREE.BufferAttribute(position.slice(), 3));
    geo.computeBoundingBox();
    geo.computeBoundingSphere();
    return geo;
  }
}

// ------------------------------------------------------------------------------------------------
// Solids
// ------------------------------------------------------------------------------------------------

/**
 * Rounds the corners of an outline. Points are [s, y] or [s, y, radius]; a corner with a radius is
 * replaced by an arc of `segments` pieces.
 */
export function fillet(pts, segments = 3) {
  const out = [];
  const n = pts.length;
  for (let i = 0; i < n; i++) {
    const p = pts[i];
    const r = p[2] || 0;
    if (!(r > 0)) {
      out.push([p[0], p[1]]);
      continue;
    }
    const a = pts[(i + n - 1) % n];
    const b = pts[(i + 1) % n];
    let ax = a[0] - p[0];
    let ay = a[1] - p[1];
    let bx = b[0] - p[0];
    let by = b[1] - p[1];
    const al = Math.hypot(ax, ay);
    const bl = Math.hypot(bx, by);
    ax /= al;
    ay /= al;
    bx /= bl;
    by /= bl;
    const half = Math.acos(Math.max(-1, Math.min(1, ax * bx + ay * by))) / 2;
    // Never eat more than 45 % of either edge.
    const cut = Math.min(r / Math.tan(half), al * 0.45, bl * 0.45);
    const p0 = [p[0] + ax * cut, p[1] + ay * cut];
    const p1 = [p[0] + bx * cut, p[1] + by * cut];
    for (let k = 0; k <= segments; k++) {
      const t = k / segments;
      const u = 1 - t;
      // Quadratic curve through the corner: close enough to an arc at this size.
      out.push([u * u * p0[0] + 2 * u * t * p[0] + t * t * p1[0], u * u * p0[1] + 2 * u * t * p[1] + t * t * p1[1]]);
    }
  }
  return out;
}

/**
 * A side profile made solid: the closed outline `pts` ([[s, y], …], s forward, y up) extruded to
 * `width` across X, centred on `x`. `bevel` chamfers both faces; chamfer vertices are tagged for wear.
 * `holes` are further outlines cut out of the profile.
 */
export function prism(pts, width, { bevel = 0, x = 0, holes = null, steps = 1 } = {}) {
  const shape = new THREE.Shape(pts.map(([s, y]) => new THREE.Vector2(s, y)));
  if (holes) for (const hole of holes) shape.holes.push(new THREE.Path(hole.map(([s, y]) => new THREE.Vector2(s, y))));
  const depth = Math.max(1e-5, width - 2 * bevel);
  const geo = new THREE.ExtrudeGeometry(shape, {
    depth,
    steps: 1,
    curveSegments: 4,
    bevelEnabled: bevel > 0,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelOffset: -bevel,
    bevelSegments: steps,
  });
  geo.deleteAttribute('uv');
  geo.deleteAttribute('normal');
  geo.clearGroups();
  geo.translate(0, 0, -depth / 2);
  geo.rotateY(Math.PI / 2); // profile s → −Z, extrusion → +X
  if (x) geo.translate(x, 0, 0);
  if (bevel > 0) tagChamfers(geo, x, width / 2, bevel);
  return geo;
}

/** Marks every vertex of a triangle that spans the chamfer band of a prism (|x| between face and side). */
function tagChamfers(geo, cx, half, bevel) {
  const pos = geo.getAttribute('position');
  const tag = new Float32Array(pos.count);
  const inner = half - bevel + 1e-6;
  for (let i = 0; i < pos.count; i += 3) {
    let lo = Infinity;
    let hi = -Infinity;
    for (let k = 0; k < 3; k++) {
      const d = Math.abs(pos.getX(i + k) - cx);
      lo = Math.min(lo, d);
      hi = Math.max(hi, d);
    }
    // A chamfer triangle has one end on the side wall and the other on the inset face.
    if (hi - lo > bevel * 0.5 && lo >= inner - bevel * 0.01) tag[i] = tag[i + 1] = tag[i + 2] = 1;
  }
  geo.setAttribute('tag', new THREE.BufferAttribute(tag, 1));
}

/** Axis-aligned block from s0…s1, y0…y1, across x0…x1, chamfered on its two X faces. */
export function block(s0, s1, y0, y1, x0, x1, bevel = 0) {
  return prism([[s0, y0], [s1, y0], [s1, y1], [s0, y1]], x1 - x0, { bevel, x: (x0 + x1) / 2 });
}

/**
 * Rings joined into a skin. A ring is
 *   { c: [x, y, z]   centre,
 *     w, h           full extents along the section axes,
 *     exp            superellipse exponent (2 = ellipse, 4+ = rounded box),
 *     top, bot       optional half-heights above / below the centre (default h / 2),
 *     ax, ay         section axes (default X and Y),
 *     turn }         rotation of the section about its own normal, radians
 * All rings get `n` points. `caps`: [start, end] booleans. `inside` turns the skin inside out.
 */
export function loft(rings, n = 12, caps = [true, true], inside = false) {
  const pos = [];
  const index = [];
  const count = rings.length;
  for (let j = 0; j < count; j++) {
    const ring = rings[j];
    const ax = ring.ax || X;
    const ay = ring.ay || Y;
    const e = 2 / (ring.exp || 2);
    const hw = ring.w / 2;
    const top = ring.top ?? ring.h / 2;
    const bot = ring.bot ?? ring.h / 2;
    const turn = (ring.turn || 0) + Math.PI / n; // flats, not corners, face the axes
    for (let i = 0; i < n; i++) {
      const a = (i / n) * TAU + turn;
      const cs = Math.cos(a);
      const sn = Math.sin(a);
      const u = Math.sign(cs) * Math.abs(cs) ** e * hw;
      const v = Math.sign(sn) * Math.abs(sn) ** e * (sn >= 0 ? top : bot);
      pos.push(ring.c[0] + ax[0] * u + ay[0] * v, ring.c[1] + ax[1] * u + ay[1] * v, ring.c[2] + ax[2] * u + ay[2] * v);
    }
  }
  // Winding: decided once from the direction the first two rings run along the section normal.
  const r0 = rings[0];
  const r1 = rings[1];
  const ax = r0.ax || X;
  const ay = r0.ay || Y;
  const nx = ax[1] * ay[2] - ax[2] * ay[1];
  const ny = ax[2] * ay[0] - ax[0] * ay[2];
  const nz = ax[0] * ay[1] - ax[1] * ay[0];
  const along = (r1.c[0] - r0.c[0]) * nx + (r1.c[1] - r0.c[1]) * ny + (r1.c[2] - r0.c[2]) * nz;
  const flip = along < 0 !== inside; // `inside`: the skin faces its own axis (a bore, a socket)
  const tri = (a, b, c) => (flip ? index.push(a, c, b) : index.push(a, b, c));
  for (let j = 0; j < count - 1; j++) {
    for (let i = 0; i < n; i++) {
      const a = j * n + i;
      const b = j * n + ((i + 1) % n);
      const c = (j + 1) * n + ((i + 1) % n);
      const d = (j + 1) * n + i;
      tri(a, b, c);
      tri(a, c, d);
    }
  }
  const cap = (j, outwardAlong) => {
    const ring = rings[j];
    const centre = pos.length / 3;
    pos.push(ring.c[0], ring.c[1], ring.c[2]);
    for (let i = 0; i < n; i++) {
      const a = j * n + i;
      const b = j * n + ((i + 1) % n);
      if (outwardAlong) tri(centre, a, b);
      else tri(centre, b, a);
    }
  };
  if (caps[0]) cap(0, false);
  if (caps[1]) cap(count - 1, true);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pos), 3));
  geo.setIndex(index);
  return geo;
}

/**
 * Body of revolution about the bore: `profile` is [[s, r], …] (distance forward, radius).
 * A profile that doubles back paints the inside of a tube.
 */
export function lathe(profile, n = 12, { x = 0, y = 0, caps = [true, true], inside = false } = {}) {
  return loft(
    profile.map(([s, r]) => ({ c: [x, y, -s], w: r * 2, h: r * 2 })),
    n,
    caps,
    inside,
  );
}

/** Straight tube from p0 to p1 ([x, y, z]) with end radii r0 / r1. */
export function rod(p0, p1, r0, r1 = r0, n = 8, caps = [true, true]) {
  const d = new THREE.Vector3(p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]).normalize();
  const helper = Math.abs(d.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
  const u = new THREE.Vector3().crossVectors(helper, d).normalize();
  const v = new THREE.Vector3().crossVectors(d, u); // u × v = d
  const ax = u.toArray();
  const ay = v.toArray();
  return loft(
    [
      { c: p0, w: r0 * 2, h: r0 * 2, ax, ay },
      { c: p1, w: r1 * 2, h: r1 * 2, ax, ay },
    ],
    n,
    caps,
  );
}

/** A pin or boss across the gun: a short cylinder along X at (s, y). */
export function pin(s, y, r, x0, x1, n = 8) {
  return rod([x0, y, -s], [x1, y, -s], r, r, n);
}

/** Round bar through a list of points ([x, y, z]); bends are tight. */
export function bar(points, r, n = 6) {
  const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(p[0], p[1], p[2])), false, 'catmullrom', 0.08);
  const geo = new THREE.TubeGeometry(curve, Math.max(2, (points.length - 1) * 4), r, n, false);
  geo.deleteAttribute('uv');
  geo.deleteAttribute('normal');
  return geo;
}

/**
 * Rings along a path in the side plane: `path` is [[s, y], …]; `section(t, i)` returns
 * {w, d, exp, x} for the ring at path point i (t = 0…1): w across the gun, d along the path normal
 * (for a path that runs down the normal points back; for one that runs forward it points down).
 * `plus` / `minus` override the half-depths on the normal side and the opposite one.
 */
export function sweep(path, section, n = 12, caps = [true, true]) {
  const rings = [];
  const last = path.length - 1;
  for (let i = 0; i <= last; i++) {
    const a = path[Math.max(0, i - 1)];
    const b = path[Math.min(last, i + 1)];
    let ts = b[0] - a[0];
    let ty = b[1] - a[1];
    const len = Math.hypot(ts, ty) || 1;
    ts /= len;
    ty /= len;
    // Tangent in gun space is (0, ty, −ts); the in-plane normal that keeps ax × ay along it follows.
    const sec = section(i / last, i);
    rings.push({
      c: [sec.x || 0, path[i][1], -path[i][0]],
      w: sec.w,
      h: sec.d,
      exp: sec.exp,
      top: sec.plus,
      bot: sec.minus,
      ax: X,
      ay: [0, -ts, -ty],
    });
  }
  return loft(rings, n, caps);
}
