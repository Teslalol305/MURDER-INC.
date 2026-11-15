// Prop construction kit: the geometry primitives and the part collector every prop builder uses.
//
// Everything here is plain data in, plain BufferGeometry out (position / normal / uv, UVs in metres so the
// material library's textures tile at real scale). Nothing touches the DOM or the renderer, so the whole
// catalogue can be built and measured in node (test/props-*.test.js).
//
//   Soup                 triangle collector: faces in, shaded (flat or creased) indexed geometry out
//   prism()              a 2D outline pushed along an axis, optionally chamfered (car bodies, barriers)
//   latheGeo()           a profile turned around the Y axis (drums, hydrants, tyres)
//   blobGeo()            a lumpy ball (trash bags, tree crowns)     roundBoxGeo()   a pillow (sandbags)
//   Builder              collects parts per material slot, colliders, lamp hints and anchors for one prop

import {
  BoxGeometry,
  BufferAttribute,
  BufferGeometry,
  Color,
  Euler,
  IcosahedronGeometry,
  Matrix4,
  Quaternion,
  ShapeUtils,
  Vector2,
  Vector3,
} from 'three';
import { boxGeo, cylGeo, mergeGeos, tubeGeo } from '../core/geo.js';

const TAU = Math.PI * 2;
const _color = new Color();
const _v0 = new Vector3();
const _v1 = new Vector3();
const _up = new Vector3(0, 1, 0);
const _quat = new Quaternion();
const _euler = new Euler();
const _one = new Vector3(1, 1, 1);

// ------------------------------------------------------------------------------------------------
// Small helpers
// ------------------------------------------------------------------------------------------------

/** Transform matrix: translation, then yaw (ry), pitch (rx), roll (rz), then scale. */
export function xf(x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, sx = 1, sy = sx, sz = sx) {
  _quat.setFromEuler(_euler.set(rx, ry, rz, 'YXZ'));
  return new Matrix4().compose(_v0.set(x, y, z), _quat, _v1.set(sx, sy, sz));
}

/** Matrix that carries the +Y axis onto the segment a → b, centred on its midpoint. */
export function alongSegment(a, b, roll = 0) {
  const dir = _v0.set(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
  const length = dir.length() || 1e-6;
  dir.divideScalar(length);
  _quat.setFromUnitVectors(_up, dir);
  const m = new Matrix4().compose(_v1.set((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2), _quat, _one);
  if (roll) m.multiply(new Matrix4().makeRotationY(roll));
  return m;
}

export const dist3 = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);

/** Points on a circular arc from angle a0 to a1 (radians, counter-clockwise positive), n segments. */
export function arc(cx, cy, r, a0, a1, n, tag) {
  const out = [];
  for (let i = 0; i <= n; i++) {
    const a = a0 + ((a1 - a0) * i) / n;
    const p = [cx + Math.cos(a) * r, cy + Math.sin(a) * r];
    if (tag !== undefined) p.push(tag);
    out.push(p);
  }
  return out;
}

export function signedArea(poly) {
  let area = 0;
  for (let i = 0; i < poly.length; i++) {
    const p = poly[i];
    const q = poly[(i + 1) % poly.length];
    area += p[0] * q[1] - q[0] * p[1];
  }
  return area / 2;
}

/** A counter-clockwise polygon moved inward by d (mitred corners, mitre length capped at 2d). */
export function insetPolygon(poly, d) {
  const n = poly.length;
  const out = [];
  for (let i = 0; i < n; i++) {
    const a = poly[(i + n - 1) % n];
    const p = poly[i];
    const b = poly[(i + 1) % n];
    // Outward normals of the two edges that meet at p.
    let n0x = p[1] - a[1];
    let n0y = -(p[0] - a[0]);
    let n1x = b[1] - p[1];
    let n1y = -(b[0] - p[0]);
    const l0 = Math.hypot(n0x, n0y) || 1;
    const l1 = Math.hypot(n1x, n1y) || 1;
    n0x /= l0;
    n0y /= l0;
    n1x /= l1;
    n1y /= l1;
    const k = d / Math.max(0.5, 1 + n0x * n1x + n0y * n1y);
    const q = [p[0] - (n0x + n1x) * k, p[1] - (n0y + n1y) * k];
    if (p.length > 2) q.push(p[2]);
    out.push(q);
  }
  return out;
}

/** Sets a uniform vertex colour on a geometry (hex or [r, g, b] linear), scaled by `gain`. */
export function tint(geo, color, gain = 1) {
  if (Array.isArray(color)) _color.setRGB(color[0], color[1], color[2]);
  else _color.set(color);
  const n = geo.getAttribute('position').count;
  const arr = new Float32Array(n * 3);
  const r = _color.r * gain;
  const g = _color.g * gain;
  const b = _color.b * gain;
  for (let i = 0; i < n; i++) {
    arr[i * 3] = r;
    arr[i * 3 + 1] = g;
    arr[i * 3 + 2] = b;
  }
  geo.setAttribute('color', new BufferAttribute(arr, 3));
  return geo;
}

/** Multiplies a geometry's UVs: metres → cells for the cut-out lattice, or stretch for a striped fabric. */
export function scaleUV(geo, su, sv = su) {
  const uv = geo.getAttribute('uv').array;
  for (let i = 0; i < uv.length; i += 2) {
    uv[i] *= su;
    uv[i + 1] *= sv;
  }
  return geo;
}

export function triangleCount(geo) {
  return (geo.index ? geo.index.count : geo.getAttribute('position').count) / 3;
}

// ------------------------------------------------------------------------------------------------
// Soup: faces in, shaded geometry out
// ------------------------------------------------------------------------------------------------

const GRID = 2000; // position hash resolution: 0.5 mm
const HALF = 32; // metres either side of the origin that the hash covers
const SPAN = 131072; // 2 · HALF · GRID

const hashPosition = (x, y, z) =>
  (Math.round((x + HALF) * GRID) * SPAN + Math.round((y + HALF) * GRID)) * SPAN + Math.round((z + HALF) * GRID);

/**
 * Collects triangles and quads (each face owns its vertices) and turns them into an indexed geometry.
 * build(0) shades every face flat; build(angle) smooths across edges shallower than `angle` degrees and
 * keeps sharper ones crisp, which is what gives a car body its shoulder line.
 */
export class Soup {
  constructor() {
    this.pos = [];
    this.uv = [];
    this.idx = [];
  }

  get vertexCount() {
    return this.pos.length / 3;
  }

  tri(a, b, c, ua = null, ub = null, uc = null) {
    const i = this.pos.length / 3;
    this.pos.push(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]);
    if (ua) this.uv.push(ua[0], ua[1], ub[0], ub[1], uc[0], uc[1]);
    else this.uv.push(0, 0, dist3(a, b), 0, 0, dist3(a, c));
    this.idx.push(i, i + 1, i + 2);
    return this;
  }

  /**
   * Corners counter-clockwise seen from the front. Without `uv` the quad is mapped in metres
   * (u along a → b, v along a → d); `uv` is [u0, v0, u1, v1] for a → c.
   */
  quad(a, b, c, d, uv = null) {
    const i = this.pos.length / 3;
    this.pos.push(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2], d[0], d[1], d[2]);
    if (uv) this.uv.push(uv[0], uv[1], uv[2], uv[1], uv[2], uv[3], uv[0], uv[3]);
    else {
      const w = dist3(a, b);
      const h = dist3(a, d);
      this.uv.push(0, 0, w, 0, w, h, 0, h);
    }
    this.idx.push(i, i + 1, i + 2, i, i + 2, i + 3);
    return this;
  }

  /** quad() that turns itself to face along `hint` whatever order the corners came in. */
  quadFacing(hint, a, b, c, d, uv = null) {
    const nx = (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]);
    const ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]);
    const nz = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    if (nx * hint[0] + ny * hint[1] + nz * hint[2] >= 0) return this.quad(a, b, c, d, uv);
    return this.quad(d, c, b, a, uv ? [uv[0], uv[3], uv[2], uv[1]] : null);
  }

  triFacing(hint, a, b, c, ua = null, ub = null, uc = null) {
    const nx = (b[1] - a[1]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[1] - a[1]);
    const ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]);
    const nz = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    if (nx * hint[0] + ny * hint[1] + nz * hint[2] >= 0) return this.tri(a, b, c, ua, ub, uc);
    return this.tri(c, b, a, uc, ub, ua);
  }

  /** A flat polygon (corners counter-clockwise seen from the front), fan-triangulated: convex outlines only. */
  fan(points, uvOf = null) {
    for (let i = 1; i < points.length - 1; i++) {
      if (uvOf) this.tri(points[0], points[i], points[i + 1], uvOf(points[0]), uvOf(points[i]), uvOf(points[i + 1]));
      else this.tri(points[0], points[i], points[i + 1]);
    }
    return this;
  }

  /** Moves every vertex: fn receives and mutates an [x, y, z] triple. */
  warp(fn) {
    const p = [0, 0, 0];
    const pos = this.pos;
    for (let i = 0; i < pos.length; i += 3) {
      p[0] = pos[i];
      p[1] = pos[i + 1];
      p[2] = pos[i + 2];
      fn(p);
      pos[i] = p[0];
      pos[i + 1] = p[1];
      pos[i + 2] = p[2];
    }
    return this;
  }

  /** @param {number} crease  0 = flat faces; otherwise the smoothing angle in degrees */
  build(crease = 0) {
    const count = this.pos.length / 3;
    const pos = this.pos;
    const idx = this.idx;
    // Area-weighted normal of each face, accumulated on the vertices the face owns (a quad's two
    // triangles share four vertices, so a slightly bent quad shades as one soft face).
    const acc = new Float32Array(count * 3);
    for (let t = 0; t < idx.length; t += 3) {
      const a = idx[t] * 3;
      const b = idx[t + 1] * 3;
      const c = idx[t + 2] * 3;
      const e1x = pos[b] - pos[a];
      const e1y = pos[b + 1] - pos[a + 1];
      const e1z = pos[b + 2] - pos[a + 2];
      const e2x = pos[c] - pos[a];
      const e2y = pos[c + 1] - pos[a + 1];
      const e2z = pos[c + 2] - pos[a + 2];
      const nx = e1y * e2z - e1z * e2y;
      const ny = e1z * e2x - e1x * e2z;
      const nz = e1x * e2y - e1y * e2x;
      for (const v of [a, b, c]) {
        acc[v] += nx;
        acc[v + 1] += ny;
        acc[v + 2] += nz;
      }
    }
    const unit = new Float32Array(count * 3);
    for (let i = 0; i < count * 3; i += 3) {
      const len = Math.hypot(acc[i], acc[i + 1], acc[i + 2]) || 1;
      unit[i] = acc[i] / len;
      unit[i + 1] = acc[i + 1] / len;
      unit[i + 2] = acc[i + 2] / len;
    }

    if (!(crease > 0)) return makeGeometry(new Float32Array(pos), unit, new Float32Array(this.uv), idx);

    // Smooth: every vertex takes the sum of the face normals at its position that lie within the
    // crease angle of its own face.
    const cos = Math.cos((crease * Math.PI) / 180);
    const groups = new Map();
    for (let i = 0; i < count; i++) {
      const key = hashPosition(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]);
      const list = groups.get(key);
      if (list) list.push(i);
      else groups.set(key, [i]);
    }
    const normal = new Float32Array(count * 3);
    const remap = new Int32Array(count).fill(-1);
    const uv = this.uv;
    const outPos = [];
    const outNormal = [];
    const outUv = [];
    for (const list of groups.values()) {
      for (const i of list) {
        const i3 = i * 3;
        let nx = 0;
        let ny = 0;
        let nz = 0;
        for (const j of list) {
          const j3 = j * 3;
          if (unit[i3] * unit[j3] + unit[i3 + 1] * unit[j3 + 1] + unit[i3 + 2] * unit[j3 + 2] < cos) continue;
          nx += acc[j3];
          ny += acc[j3 + 1];
          nz += acc[j3 + 2];
        }
        const len = Math.hypot(nx, ny, nz) || 1;
        normal[i3] = nx / len;
        normal[i3 + 1] = ny / len;
        normal[i3 + 2] = nz / len;
      }
      // Weld vertices of this position that ended up with the same normal and UV.
      const first = outPos.length / 3;
      for (const i of list) {
        const i3 = i * 3;
        let found = -1;
        for (let k = first; k < outPos.length / 3 && found < 0; k++) {
          const same =
            Math.abs(outNormal[k * 3] - normal[i3]) < 2e-3 &&
            Math.abs(outNormal[k * 3 + 1] - normal[i3 + 1]) < 2e-3 &&
            Math.abs(outNormal[k * 3 + 2] - normal[i3 + 2]) < 2e-3 &&
            Math.abs(outUv[k * 2] - uv[i * 2]) < 1e-4 &&
            Math.abs(outUv[k * 2 + 1] - uv[i * 2 + 1]) < 1e-4;
          if (same) found = k;
        }
        if (found < 0) {
          found = outPos.length / 3;
          outPos.push(pos[i3], pos[i3 + 1], pos[i3 + 2]);
          outNormal.push(normal[i3], normal[i3 + 1], normal[i3 + 2]);
          outUv.push(uv[i * 2], uv[i * 2 + 1]);
        }
        remap[i] = found;
      }
    }
    const outIdx = new Array(idx.length);
    for (let t = 0; t < idx.length; t++) outIdx[t] = remap[idx[t]];
    return makeGeometry(new Float32Array(outPos), new Float32Array(outNormal), new Float32Array(outUv), outIdx);
  }
}

function makeGeometry(position, normal, uv, index) {
  const geo = new BufferGeometry();
  geo.setAttribute('position', new BufferAttribute(position, 3));
  geo.setAttribute('normal', new BufferAttribute(normal, 3));
  geo.setAttribute('uv', new BufferAttribute(uv, 2));
  geo.setIndex(index);
  return geo;
}

// ------------------------------------------------------------------------------------------------
// Shapes
// ------------------------------------------------------------------------------------------------

/** One quad from four corners (counter-clockwise seen from the front). `uv` = [u0, v0, u1, v1]. */
export function quadGeo(a, b, c, d, uv = null) {
  return new Soup().quad(a, b, c, d, uv).build(0);
}

const AXIS_MAP = {
  z: (a, b, t) => [a, b, t],
  x: (a, b, t) => [t, b, a],
  y: (a, b, t) => [a, t, b],
};

/**
 * Pushes a closed 2D outline along an axis from t0 to t1 (t0 < t1).
 *   axis 'z': outline [x, y]      axis 'x': outline [z, y]      axis 'y': outline [x, z]
 * Outline points may carry a tag as third element: the wall that starts at a tagged point goes to
 * opts.soups[tag] instead of the main soup (a car's wheel wells are darker than its paint).
 * opts: { axis, bevel (chamfer the two end faces by this much), caps: true, soup, soups,
 *         chords: [[i, j], …] pairs of outline indices (of a counter-clockwise outline) along which the end faces are cut }
 * Returns the main soup; shade it with .build(angle).
 */
export function prism(outline, t0, t1, opts = {}) {
  const { axis = 'z', bevel = 0, caps = true } = opts;
  const map = AXIS_MAP[axis];
  const main = opts.soup || new Soup();
  let pts = outline;
  if (signedArea(outline) < 0) {
    // A tag marks the wall that STARTS at its point: turned round, that wall starts at the next point.
    const turned = outline.slice().reverse();
    pts = turned.map((p, i) => [p[0], p[1], turned[(i + 1) % turned.length][2]]);
  }
  const n = pts.length;
  const inner = bevel > 0 ? insetPolygon(pts, bevel) : pts;
  const ta = t0 + bevel;
  const tb = t1 - bevel;

  let along = 0;
  for (let i = 0; i < n; i++) {
    const p = pts[i];
    const q = pts[(i + 1) % n];
    const length = Math.hypot(q[0] - p[0], q[1] - p[1]);
    if (length < 1e-6) continue;
    const out = [q[1] - p[1], -(q[0] - p[0])]; // outward in the outline's plane
    const soup = (opts.soups && p[2] !== undefined && opts.soups[p[2]]) || main;
    soup.quadFacing(
      map(out[0], out[1], 0),
      map(p[0], p[1], tb), map(p[0], p[1], ta), map(q[0], q[1], ta), map(q[0], q[1], tb),
      [tb, along, ta, along + length],
    );
    if (bevel > 0) {
      const pi = inner[i];
      const qi = inner[(i + 1) % n];
      main.quadFacing(
        map(out[0], out[1], length),
        map(pi[0], pi[1], t1), map(p[0], p[1], tb), map(q[0], q[1], tb), map(qi[0], qi[1], t1),
      );
      main.quadFacing(
        map(out[0], out[1], -length),
        map(p[0], p[1], ta), map(pi[0], pi[1], t0), map(qi[0], qi[1], t0), map(q[0], q[1], ta),
      );
    }
    along += length;
  }

  if (caps) {
    // The end faces, cut into pieces along the chords first: each piece is triangulated on its own, so
    // a face that is later bent along a chord stays flat on either side of it.
    let pieces = [inner.map((_, i) => i)];
    for (const [from, to] of opts.chords || []) {
      const next = [];
      for (const piece of pieces) {
        const a = piece.indexOf(from);
        const b = piece.indexOf(to);
        if (a < 0 || b < 0) {
          next.push(piece);
          continue;
        }
        const lo = Math.min(a, b);
        const hi = Math.max(a, b);
        next.push(piece.slice(lo, hi + 1), [...piece.slice(hi), ...piece.slice(0, lo + 1)]);
      }
      pieces = next;
    }
    const front = map(0, 0, 1);
    const back = map(0, 0, -1);
    for (const piece of pieces) {
      if (piece.length < 3) continue;
      const ring = piece.map((i) => inner[i]);
      for (const [i, j, k] of ShapeUtils.triangulateShape(ring.map((p) => new Vector2(p[0], p[1])), [])) {
        const a = ring[i];
        const b = ring[j];
        const c = ring[k];
        if (caps !== 'back') main.triFacing(front, map(a[0], a[1], t1), map(b[0], b[1], t1), map(c[0], c[1], t1), a, b, c);
        if (caps !== 'front') main.triFacing(back, map(a[0], a[1], t0), map(b[0], b[1], t0), map(c[0], c[1], t0), a, b, c);
      }
    }
  }
  return main;
}

/** prism() shaded and returned as a geometry. */
export function prismGeo(outline, t0, t1, opts = {}) {
  return prism(outline, t0, t1, opts).build(opts.crease ?? 0);
}

/**
 * A profile [[radius, y], …] turned around the Y axis. List the points so that the outside of the
 * shape is on the right when walking along them (bottom centre → out → up → top centre for a solid).
 * Normals are smooth around the axis; along the profile they are smooth where the bend is shallower
 * than opts.crease (default 38°). opts: { crease, arc (radians, default full turn), open }
 */
export function latheGeo(profile, segments = 12, opts = {}) {
  const cos = Math.cos(((opts.crease ?? 38) * Math.PI) / 180);
  const sweep = opts.arc ?? TAU;
  const n = profile.length;
  // Unit normal of each profile segment in the (radius, y) plane.
  const segN = [];
  for (let k = 0; k < n - 1; k++) {
    const dr = profile[k + 1][0] - profile[k][0];
    const dy = profile[k + 1][1] - profile[k][1];
    const len = Math.hypot(dr, dy) || 1;
    segN.push([dy / len, -dr / len]);
  }
  const blend = (a, b) => {
    if (!a || !b || a[0] * b[0] + a[1] * b[1] < cos) return null;
    const x = a[0] + b[0];
    const y = a[1] + b[1];
    const len = Math.hypot(x, y) || 1;
    return [x / len, y / len];
  };
  let rMax = 0;
  for (const p of profile) rMax = Math.max(rMax, p[0]);

  const position = [];
  const normal = [];
  const uv = [];
  const index = [];
  let v = 0;
  for (let k = 0; k < n - 1; k++) {
    const [r0, y0] = profile[k];
    const [r1, y1] = profile[k + 1];
    const length = Math.hypot(r1 - r0, y1 - y0);
    if (length < 1e-6) continue;
    const n0 = blend(segN[k - 1], segN[k]) || segN[k];
    const n1 = blend(segN[k], segN[k + 1]) || segN[k];
    const base = position.length / 3;
    for (let i = 0; i <= segments; i++) {
      const a = (i / segments) * sweep;
      const c = Math.cos(a);
      const s = Math.sin(a);
      position.push(r0 * c, y0, r0 * s, r1 * c, y1, r1 * s);
      normal.push(n0[0] * c, n0[1], n0[0] * s, n1[0] * c, n1[1], n1[0] * s);
      const u = (i / segments) * sweep * rMax;
      uv.push(u, v, u, v + length);
    }
    for (let i = 0; i < segments; i++) {
      const a = base + i * 2; // lower ring, this column
      const b = a + 1; // upper ring, this column
      const c = a + 2; // lower ring, next column
      const d = a + 3; // upper ring, next column
      if (r0 > 1e-6) index.push(a, b, c);
      if (r1 > 1e-6) index.push(b, d, c);
    }
    v += length;
  }
  return makeGeometry(new Float32Array(position), new Float32Array(normal), new Float32Array(uv), index);
}

/** Cheap deterministic value noise on a direction: three sines per axis, good enough for lumps. */
function lump(x, y, z, seed) {
  return (
    Math.sin(x * 2.1 + seed * 1.7) * Math.cos(y * 2.7 + seed * 0.9) +
    Math.sin(z * 2.4 + seed * 2.3 + y * 1.3) * 0.8 +
    Math.cos(x * 4.3 - z * 3.7 + seed * 3.1) * 0.45
  ) / 2.25;
}

/**
 * A lumpy ball: an icosphere pushed in and out by smooth noise.
 * opts: { detail (0 = 20 faces, 1 = 80), seed, rough (0…1 lump depth), scale: [x, y, z],
 *         crease (0 = faceted), shape(p) to bend the unit sphere before scaling }
 */
export function blobGeo(radius = 0.5, opts = {}) {
  const { detail = 1, seed = 0, rough = 0.25, scale = [1, 1, 1], crease = 0, shape = null } = opts;
  const src = new IcosahedronGeometry(1, detail);
  const sp = src.getAttribute('position');
  const soup = new Soup();
  const corner = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  for (let i = 0; i < sp.count; i += 3) {
    for (let k = 0; k < 3; k++) {
      const p = corner[k];
      p[0] = sp.getX(i + k);
      p[1] = sp.getY(i + k);
      p[2] = sp.getZ(i + k);
      const f = radius * (1 + rough * lump(p[0], p[1], p[2], seed));
      if (shape) shape(p);
      p[0] *= f * scale[0];
      p[1] *= f * scale[1];
      p[2] *= f * scale[2];
    }
    const [a, b, c] = corner;
    soup.tri(a, b, c, [a[0] + a[2], a[1]], [b[0] + b[2], b[1]], [c[0] + c[2], c[1]]);
  }
  src.dispose();
  return soup.build(crease);
}

/**
 * A soft box (sandbag, mattress, cushion): a subdivided box whose faces bulge and whose corners pull in.
 * opts: { round (0…1), segments: [x, y, z], crease }
 */
export function roundBoxGeo(w, h, d, opts = {}) {
  const { round = 0.5, segments = [3, 2, 2], crease = 70 } = opts;
  const src = new BoxGeometry(w, h, d, segments[0], segments[1], segments[2]);
  const sp = src.getAttribute('position');
  const su = src.getAttribute('uv');
  const si = src.index;
  const soup = new Soup();
  const hx = w / 2;
  const hy = h / 2;
  const hz = d / 2;
  const at = (i) => {
    const u = sp.getX(i) / hx;
    const v = sp.getY(i) / hy;
    const s = sp.getZ(i) / hz;
    // Each axis shrinks as the other two approach the box's edges: corners round off, faces stay full.
    const fx = 1 - round * 0.5 * (v * v * v * v + s * s * s * s) * 0.5;
    const fy = 1 - round * (u * u * u * u + s * s * s * s) * 0.5;
    const fz = 1 - round * 0.5 * (u * u * u * u + v * v * v * v) * 0.5;
    return [u * hx * fx, v * hy * fy, s * hz * fz];
  };
  for (let t = 0; t < si.count; t += 3) {
    const a = si.getX(t);
    const b = si.getX(t + 1);
    const c = si.getX(t + 2);
    soup.tri(at(a), at(b), at(c), [su.getX(a) * w, su.getY(a) * h], [su.getX(b) * w, su.getY(b) * h], [su.getX(c) * w, su.getY(c) * h]);
  }
  src.dispose();
  return soup.build(crease);
}

/** A flat ring (annulus) in the XZ plane facing +Y, or a disc when rInner is 0. */
export function ringGeo(rInner, rOuter, segments = 12) {
  const soup = new Soup();
  for (let i = 0; i < segments; i++) {
    const a0 = (i / segments) * TAU;
    const a1 = ((i + 1) / segments) * TAU;
    const o0 = [Math.cos(a0) * rOuter, 0, -Math.sin(a0) * rOuter];
    const o1 = [Math.cos(a1) * rOuter, 0, -Math.sin(a1) * rOuter];
    const uvOf = (p) => [p[0] + rOuter, p[2] + rOuter];
    if (rInner > 1e-6) {
      const i0 = [Math.cos(a0) * rInner, 0, -Math.sin(a0) * rInner];
      const i1 = [Math.cos(a1) * rInner, 0, -Math.sin(a1) * rInner];
      soup.tri(i0, o0, o1, uvOf(i0), uvOf(o0), uvOf(o1));
      soup.tri(i0, o1, i1, uvOf(i0), uvOf(o1), uvOf(i1));
    } else {
      soup.tri([0, 0, 0], o0, o1, uvOf([0, 0, 0]), uvOf(o0), uvOf(o1));
    }
  }
  return soup.build(0);
}

// ------------------------------------------------------------------------------------------------
// Builder: the parts of one prop
// ------------------------------------------------------------------------------------------------

/** Unit vectors (right, up) of a decal that faces the given axis, so its picture reads the right way round. */
const FACING = {
  '+z': [[1, 0, 0], [0, 1, 0]],
  '-z': [[-1, 0, 0], [0, 1, 0]],
  '+x': [[0, 0, -1], [0, 1, 0]],
  '-x': [[0, 0, 1], [0, 1, 0]],
  '+y': [[1, 0, 0], [0, 0, -1]],
  '-y': [[1, 0, 0], [0, 0, 1]],
};

const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];

/** Slot name of an unlit glowing part: colour and brightness (above about 1 it blooms). */
export const glow = (color, intensity = 2) => `@glow:${color.toString(16).padStart(6, '0')}:${intensity}`;

/** Slot of a part whose material the prop's rig supplies per instance (a light shaft, a jet of water). */
export const RIGGED = '#rig';

/** Slot name of the cut-out lattice in a colour (wire baskets, milk crates, gratings, chain nets). */
export const lattice = (color) => `@grid:${color.toString(16).padStart(6, '0')}`;

/** Slot name of a catalogue material with options, e.g. M('glass_store', {transparent: true, opacity: 0.3}). */
export const M = (name, opts) => (opts ? `${name}|${JSON.stringify(opts)}` : name);

/**
 * Collects the geometry of one prop per material slot (and per named node for parts that move),
 * plus its colliders, lamp hints and anchors. Positions are in prop space: origin on the ground at the
 * footprint centre, length along +X, front toward +Z, up +Y.
 *
 * Slots: a catalogue material name ('metal_dark'), M(name, opts), '@paint' (the instance colour),
 * '@glass' (car glass, glowing when the dome light is on), glow(color, intensity), '@decal' / '@lit'
 * (atlas quads, see decal()), '@grid:rrggbb' (cut-out lattice), '@vc' (vertex-coloured).
 */
export class Builder {
  /** @param {{name: string, size: number[], rng: object, atlas: (name: string) => number[]}} ctx */
  constructor(ctx) {
    this.name = ctx.name;
    this.size = ctx.size;
    this.rng = ctx.rng;
    this.atlasRect = ctx.atlas;
    this.rootNode = { name: '', pivot: [0, 0, 0], parts: new Map() };
    this.nodes = [this.rootNode];
    this.current = this.rootNode;
    this.colliders = [];
    this.lights = [];
    this.anchors = {};
    this.stack = [];
    this.materials = new Map();
  }

  /**
   * A slot for a material the builder made or fetched itself (a sign or graffiti from the material
   * library, the billboard face). Returns the slot name to add geometry to.
   */
  own(material) {
    for (const [slot, m] of this.materials) if (m === material) return slot;
    const slot = `#own${this.materials.size}`;
    this.materials.set(slot, material);
    return slot;
  }

  /** Everything added until the matching pop() is moved by `matrix` (sub-assemblies: a car on a lift). */
  push(matrix) {
    const top = this.stack[this.stack.length - 1];
    this.stack.push(top ? top.clone().multiply(matrix) : matrix);
    return this;
  }

  pop() {
    this.stack.pop();
    return this;
  }

  /** Opens (or re-opens) a named group that the prop animates on its own; `pivot` becomes its origin. */
  node(name, pivot = [0, 0, 0]) {
    let node = this.nodes.find((n) => n.name === name);
    if (!node) {
      node = { name, pivot, parts: new Map() };
      this.nodes.push(node);
    }
    this.current = node;
    return this;
  }

  /** Back to the static body. */
  root() {
    this.current = this.rootNode;
    return this;
  }

  /** Adds a geometry to a slot, optionally transformed and tinted (vertex colour for '@vc' / glow slots). */
  add(slot, geo, matrix = null, color = undefined) {
    if (color !== undefined) tint(geo, color);
    let list = this.current.parts.get(slot);
    if (!list) this.current.parts.set(slot, (list = []));
    const top = this.stack[this.stack.length - 1];
    list.push({ geo, matrix: top ? (matrix ? top.clone().multiply(matrix) : top) : matrix });
    return this;
  }

  /** Box of size [w, h, d] centred on `at`. o: { rot: [rx, ry, rz], color, noTop, noBottom, base: true (at.y is the underside) } */
  box(slot, size, at, o = {}) {
    const geo = boxGeo(size[0], size[1], size[2], { noTop: o.noTop, noBottom: o.noBottom });
    const y = o.base ? at[1] + size[1] / 2 : at[1];
    const r = o.rot;
    return this.add(slot, geo, r ? xf(at[0], y, at[2], r[0], r[1], r[2]) : xf(at[0], y, at[2]), o.color);
  }

  /** Cylinder centred on `at`. o: { seg, rTop, axis: 'x' | 'y' | 'z', open, rot, color, base: true } */
  cyl(slot, radius, height, at, o = {}) {
    const geo = cylGeo(radius, height, o.seg ?? 10, { radiusTop: o.rTop, open: o.open });
    let rx = 0;
    let ry = 0;
    let rz = 0;
    if (o.axis === 'x') rz = -Math.PI / 2;
    else if (o.axis === 'z') rx = Math.PI / 2;
    if (o.rot) [rx, ry, rz] = o.rot;
    const y = o.base ? at[1] + height / 2 : at[1];
    return this.add(slot, geo, xf(at[0], y, at[2], rx, ry, rz), o.color);
  }

  /** Round bar from a to b. o: { seg, rTop (radius at b), caps, color } */
  stick(slot, a, b, radius, o = {}) {
    const geo = cylGeo(radius, dist3(a, b), o.seg ?? 6, { radiusTop: o.rTop, open: !o.caps });
    return this.add(slot, geo, alongSegment(a, b), o.color);
  }

  /** Rectangular bar from a to b, `w` wide and `t` thick. o: { roll, color } */
  bar(slot, a, b, w, t = w, o = {}) {
    const geo = boxGeo(w, dist3(a, b), t);
    return this.add(slot, geo, alongSegment(a, b, o.roll ?? 0), o.color);
  }

  /** A chain of sticks through the points (handrails, frames). */
  pipe(slot, points, radius, o = {}) {
    for (let i = 0; i < points.length - 1; i++) this.stick(slot, points[i], points[i + 1], radius, o);
    return this;
  }

  /** Smooth tube through the points (hoses, cables). o: { radial, segments, color } */
  tube(slot, points, radius, o = {}) {
    return this.add(slot, tubeGeo(points, radius, { radial: o.radial ?? 5, segments: o.segments }), null, o.color);
  }

  /** One quad, corners counter-clockwise seen from the front. o: { uv: [u0, v0, u1, v1], color, both: true (two-sided) } */
  quad(slot, a, b, c, d, o = {}) {
    this.add(slot, quadGeo(a, b, c, d, o.uv), null, o.color);
    if (o.both) this.add(slot, quadGeo(d, c, b, a, o.uv ? [o.uv[0], o.uv[3], o.uv[2], o.uv[1]] : null), null, o.color);
    return this;
  }

  /** Lathe (see latheGeo) with its axis base at `at`. o: { seg, crease, rot, color, arc } */
  lathe(slot, profile, at = [0, 0, 0], o = {}) {
    const geo = latheGeo(profile, o.seg ?? 12, { crease: o.crease, arc: o.arc });
    const r = o.rot;
    return this.add(slot, geo, r ? xf(at[0], at[1], at[2], r[0], r[1], r[2]) : xf(at[0], at[1], at[2]), o.color);
  }

  /** Flat ring or disc facing +Y at `at`. o: { seg, rot, color } */
  ring(slot, rInner, rOuter, at, o = {}) {
    const r = o.rot || [0, 0, 0];
    return this.add(slot, ringGeo(rInner, rOuter, o.seg ?? 12), xf(at[0], at[1], at[2], r[0], r[1], r[2]), o.color);
  }

  /** Lumpy ball (see blobGeo) centred on `at`. o: blobGeo options + { rot, color } */
  blob(slot, radius, at, o = {}) {
    const r = o.rot || [0, 0, 0];
    return this.add(slot, blobGeo(radius, o), xf(at[0], at[1], at[2], r[0], r[1], r[2]), o.color);
  }

  /** Extruded outline (see prism). o: { axis, bevel, crease, caps, at: [x, y, z], rot, color } */
  prism(slot, outline, t0, t1, o = {}) {
    const geo = prismGeo(outline, t0, t1, o);
    let m = null;
    if (o.at || o.rot) {
      const p = o.at || [0, 0, 0];
      const r = o.rot || [0, 0, 0];
      m = xf(p[0], p[1], p[2], r[0], r[1], r[2]);
    }
    return this.add(slot, geo, m, o.color);
  }

  /**
   * A picture from the prop atlas on a quad of w × h metres centred on `at`.
   * facing: '+z' | '-z' | '+x' | '-x' | '+y' | '-y', or { right: [x, y, z], up: [x, y, z] } unit vectors.
   * o: { lit: true (glows), lift: metres off the surface (default 0.006), slot }
   */
  decal(region, at, w, h, facing = '+z', o = {}) {
    const [right, up] = typeof facing === 'string' ? FACING[facing] : [facing.right, facing.up];
    const n = cross(right, up);
    const lift = o.lift ?? 0.006;
    const c = [at[0] + n[0] * lift, at[1] + n[1] * lift, at[2] + n[2] * lift];
    const corner = (sr, su) => [
      c[0] + (right[0] * sr * w) / 2 + (up[0] * su * h) / 2,
      c[1] + (right[1] * sr * w) / 2 + (up[1] * su * h) / 2,
      c[2] + (right[2] * sr * w) / 2 + (up[2] * su * h) / 2,
    ];
    const uv = this.atlasRect(region);
    return this.add(o.slot || (o.lit ? '@lit' : '@decal'), quadGeo(corner(-1, -1), corner(1, -1), corner(1, 1), corner(-1, 1), uv));
  }

  /** Local-space collider. flags: { surface, bulletOnly, playerOnly, noNav } */
  collide(min, max, flags = {}) {
    this.colliders.push({ min: min.slice(), max: max.slice(), ...flags });
    return this;
  }

  /** Collider from a centre (x, z), a footprint (w along x, d along z) and a height range. */
  collideBox(x, z, w, d, y0, y1, flags = {}) {
    return this.collide([x - w / 2, y0, z - d / 2], [x + w / 2, y1, z + d / 2], flags);
  }

  /** Lamp hint for atmos. spec: { color, intensity, range, kind, dir: [x, y, z] } */
  lamp(pos, spec) {
    this.lights.push({ pos: pos.slice(), ...spec });
    return this;
  }

  /** A named attachment point other modules can use (steam, water, flame jets, sound). */
  anchor(name, pos, dir = [0, 1, 0]) {
    this.anchors[name] = { pos: pos.slice(), dir: dir.slice() };
    return this;
  }

  /**
   * Fuses every slot into one geometry per node. Glow slots of all colours are baked into vertex
   * colours and share the single '@glow' slot, so a whole street of tail lights is one draw call.
   */
  finish() {
    let triangles = 0;
    const nodes = this.nodes.map((node) => {
      const merged = new Map();
      const glowParts = [];
      for (const [slot, list] of node.parts) {
        if (slot.startsWith('@glow:')) {
          const [, hex, intensity] = slot.split(':');
          for (const part of list) {
            tint(part.geo, parseInt(hex, 16), Number(intensity));
            glowParts.push(part);
          }
        } else {
          merged.set(slot, mergeGeos(list));
        }
      }
      if (glowParts.length) merged.set('@glow', mergeGeos(glowParts));
      for (const geo of merged.values()) {
        triangles += triangleCount(geo);
        // A node's geometry is authored in prop space; its group sits at the pivot.
        if (node.name) geo.translate(-node.pivot[0], -node.pivot[1], -node.pivot[2]);
        geo.computeBoundingBox();
        geo.computeBoundingSphere();
      }
      return { name: node.name, pivot: node.pivot, parts: merged };
    });
    return { nodes, colliders: this.colliders, lights: this.lights, anchors: this.anchors, materials: this.materials, triangles };
  }
}
