// Geometry helpers. Everything here produces plain indexed BufferGeometries whose UVs are in METRES,
// so a material that sets `map.repeat` once tiles at real-world scale on every surface.
//
//   boxGeo(w, h, d, opts)          box, UVs per face in metres
//   planeGeo(w, h, opts)           one quad facing any axis
//   cylGeo(r, h, segments, opts)   cylinder / cone / frustum
//   tubeGeo(points, r, opts)       tube along a smooth curve (cables, pipes, hoses)
//   mergeGeos(list)                many geometries → one (attributes normalised)
//   bakeTransform(mesh)            copy of a mesh's geometry in world space
//   mergeStatic(root)              whole subtree → one mesh per material

import {
  BufferAttribute,
  BufferGeometry,
  CatmullRomCurve3,
  Color,
  CylinderGeometry,
  Group,
  Matrix3,
  Mesh,
  TubeGeometry,
  Vector3,
} from 'three';

const _color = new Color();
const _normalMatrix = new Matrix3();

// ------------------------------------------------------------------------------------------------
// Primitive builders
// ------------------------------------------------------------------------------------------------

/** Collects quads into flat arrays, then turns them into an indexed geometry. */
function quadBuilder() {
  const position = [];
  const normal = [];
  const uv = [];
  const index = [];
  return {
    /** Corners a, b, c, d counter-clockwise seen from the front; u runs a→b (length uw), v runs a→d (length vh). */
    quad(a, b, c, d, n, uw, vh) {
      const base = position.length / 3;
      position.push(...a, ...b, ...c, ...d);
      normal.push(...n, ...n, ...n, ...n);
      uv.push(0, 0, uw, 0, uw, vh, 0, vh);
      index.push(base, base + 1, base + 2, base, base + 2, base + 3);
    },
    build(opts) {
      const geo = new BufferGeometry();
      geo.setAttribute('position', new BufferAttribute(new Float32Array(position), 3));
      geo.setAttribute('normal', new BufferAttribute(new Float32Array(normal), 3));
      geo.setAttribute('uv', new BufferAttribute(new Float32Array(uv), 2));
      geo.setIndex(index);
      return finish(geo, opts);
    },
  };
}

/** Shared option handling: uvScale / uvOffset, translation (`at`), baked vertex colour, bounds. */
function finish(geo, opts = {}) {
  const { at, uvScale, uvOffset, color } = opts;
  if (uvScale !== undefined || uvOffset) {
    const su = Array.isArray(uvScale) ? uvScale[0] : uvScale ?? 1;
    const sv = Array.isArray(uvScale) ? uvScale[1] : uvScale ?? 1;
    const ou = uvOffset ? uvOffset[0] : 0;
    const ov = uvOffset ? uvOffset[1] : 0;
    const uv = geo.getAttribute('uv').array;
    for (let i = 0; i < uv.length; i += 2) {
      uv[i] = uv[i] * su + ou;
      uv[i + 1] = uv[i + 1] * sv + ov;
    }
  }
  if (at) geo.translate(at[0], at[1], at[2]);
  if (color !== undefined) {
    _color.set(color);
    const n = geo.getAttribute('position').count;
    const arr = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      arr[i * 3] = _color.r;
      arr[i * 3 + 1] = _color.g;
      arr[i * 3 + 2] = _color.b;
    }
    geo.setAttribute('color', new BufferAttribute(arr, 3));
  }
  geo.computeBoundingBox();
  geo.computeBoundingSphere();
  return geo;
}

/**
 * Box of w (x) × h (y) × d (z) metres centred on the origin. On the four sides u runs to the right
 * and v runs up (seen from outside), so brick courses and roll-gate ribs stay level.
 * opts: { bottom: true   base on y = 0 instead of centred,
 *         at: [x, y, z]  extra translation,
 *         noTop, noBottom  leave a cap out (faces nobody can see),
 *         uvScale: n | [su, sv], uvOffset: [u, v], color: hex }
 */
export function boxGeo(w = 1, h = 1, d = 1, opts = {}) {
  const x = w / 2;
  const z = d / 2;
  const y0 = opts.bottom ? 0 : -h / 2;
  const y1 = y0 + h;
  const b = quadBuilder();
  b.quad([-x, y0, z], [x, y0, z], [x, y1, z], [-x, y1, z], [0, 0, 1], w, h); // south (+z)
  b.quad([x, y0, -z], [-x, y0, -z], [-x, y1, -z], [x, y1, -z], [0, 0, -1], w, h); // north (−z)
  b.quad([x, y0, z], [x, y0, -z], [x, y1, -z], [x, y1, z], [1, 0, 0], d, h); // east (+x)
  b.quad([-x, y0, -z], [-x, y0, z], [-x, y1, z], [-x, y1, -z], [-1, 0, 0], d, h); // west (−x)
  if (!opts.noTop) b.quad([-x, y1, z], [x, y1, z], [x, y1, -z], [-x, y1, -z], [0, 1, 0], w, d);
  if (!opts.noBottom) b.quad([-x, y0, -z], [x, y0, -z], [x, y0, z], [-x, y0, z], [0, -1, 0], w, d);
  return b.build(opts);
}

/**
 * Single quad of w × h metres centred on the origin.
 * opts.facing: '+y' (default: lies flat, w along x, h along z), '-y', '+x', '-x', '+z', '-z'
 *              (upright quads: w is the horizontal extent, h the vertical one).
 * Also takes at / uvScale / uvOffset / color like boxGeo.
 */
export function planeGeo(w = 1, h = 1, opts = {}) {
  const a = w / 2;
  const c = h / 2;
  const b = quadBuilder();
  switch (opts.facing ?? '+y') {
    case '+y':
      b.quad([-a, 0, c], [a, 0, c], [a, 0, -c], [-a, 0, -c], [0, 1, 0], w, h);
      break;
    case '-y':
      b.quad([-a, 0, -c], [a, 0, -c], [a, 0, c], [-a, 0, c], [0, -1, 0], w, h);
      break;
    case '+z':
      b.quad([-a, -c, 0], [a, -c, 0], [a, c, 0], [-a, c, 0], [0, 0, 1], w, h);
      break;
    case '-z':
      b.quad([a, -c, 0], [-a, -c, 0], [-a, c, 0], [a, c, 0], [0, 0, -1], w, h);
      break;
    case '+x':
      b.quad([0, -c, a], [0, -c, -a], [0, c, -a], [0, c, a], [1, 0, 0], w, h);
      break;
    case '-x':
      b.quad([0, -c, -a], [0, -c, a], [0, c, a], [0, c, -a], [-1, 0, 0], w, h);
      break;
    default:
      throw new Error(`planeGeo: unknown facing '${opts.facing}'`);
  }
  return b.build(opts);
}

/**
 * Upright cylinder (or cone / frustum with opts.radiusTop) centred on the origin.
 * UVs: around the side u is arc length and v is height; caps are mapped flat. All in metres.
 * opts: { radiusTop, bottom: true, open: true (no caps), at, uvScale, uvOffset, color }
 */
export function cylGeo(radius = 0.5, height = 1, segments = 12, opts = {}) {
  const rTop = opts.radiusTop ?? radius;
  const geo = new CylinderGeometry(rTop, radius, height, segments, 1, !!opts.open);
  geo.clearGroups();
  const uv = geo.getAttribute('uv').array;
  const sideVerts = (segments + 1) * 2;
  const around = Math.PI * 2 * Math.max(radius, rTop);
  const capSize = 2 * Math.max(radius, rTop);
  for (let i = 0; i < uv.length / 2; i++) {
    const side = i < sideVerts;
    uv[i * 2] *= side ? around : capSize;
    uv[i * 2 + 1] *= side ? height : capSize;
  }
  if (opts.bottom) geo.translate(0, height / 2, 0);
  return finish(geo, opts);
}

/**
 * Tube of the given radius along a smooth curve through `points` (Vector3s or [x, y, z] triples).
 * UVs: u is distance along the tube, v is arc length around it, in metres.
 * opts: { segments (along, default 6 per point), radial (around, default 6), closed, uvScale, uvOffset, color }
 */
export function tubeGeo(points, radius = 0.03, opts = {}) {
  const pts = points.map((p) => (p.isVector3 ? p : new Vector3(p[0], p[1], p[2])));
  if (pts.length < 2) throw new Error('tubeGeo: needs at least two points');
  const curve = new CatmullRomCurve3(pts, !!opts.closed, 'centripetal');
  const geo = new TubeGeometry(curve, opts.segments ?? pts.length * 6, radius, opts.radial ?? 6, !!opts.closed);
  const uv = geo.getAttribute('uv').array;
  const length = curve.getLength();
  const around = Math.PI * 2 * radius;
  for (let i = 0; i < uv.length; i += 2) {
    uv[i] *= length;
    uv[i + 1] *= around;
  }
  return finish(geo, opts);
}

// ------------------------------------------------------------------------------------------------
// Merging
// ------------------------------------------------------------------------------------------------

/** A list of geometry parts waiting to be fused into one indexed geometry. */
function createBatch() {
  return { parts: [], vertices: 0, indices: 0, hasColor: false };
}

/**
 * Queues `geo` (optionally transformed by `matrix`, optionally only the index range start…start+count).
 * Geometries without a position attribute are ignored.
 */
function addPart(batch, geo, matrix = null, start = 0, count = Infinity) {
  const position = geo.getAttribute('position');
  if (!position || position.count === 0) return;
  // Vertex normals are required; derive them on a private copy when the source has none.
  if (!geo.getAttribute('normal')) {
    geo = geo.clone();
    geo.computeVertexNormals();
  }
  const total = geo.index ? geo.index.count : position.count;
  const from = Math.max(0, Math.min(start, total));
  let n = Math.min(count, total - from);
  n -= n % 3;
  if (n <= 0) return;
  batch.parts.push({ geo, matrix, start: from, count: n });
  batch.vertices += position.count;
  batch.indices += n;
  if (geo.getAttribute('color')) batch.hasColor = true;
}

/** Copies an attribute into `out` at `offset` (in items), reading at most `size` components per vertex. */
function copyAttribute(attr, size, out, offset) {
  const n = attr.count;
  const fast =
    attr.isBufferAttribute && !attr.isInterleavedBufferAttribute && !attr.normalized && attr.itemSize === size;
  if (fast) {
    out.set(attr.array.subarray(0, n * size), offset * size);
    return;
  }
  // Generic path: interleaved buffers, normalised integer data, colours with alpha.
  let o = offset * size;
  for (let i = 0; i < n; i++) {
    out[o++] = attr.getX(i);
    if (size > 1) out[o++] = attr.itemSize > 1 ? attr.getY(i) : 0;
    if (size > 2) out[o++] = attr.itemSize > 2 ? attr.getZ(i) : 0;
  }
}

function buildBatch(batch) {
  const { parts, vertices, indices, hasColor } = batch;
  const position = new Float32Array(vertices * 3);
  const normal = new Float32Array(vertices * 3);
  const uv = new Float32Array(vertices * 2);
  const color = hasColor ? new Float32Array(vertices * 3).fill(1) : null;
  const index = vertices > 65535 ? new Uint32Array(indices) : new Uint16Array(indices);

  let v0 = 0; // first vertex of the current part
  let i0 = 0; // first index of the current part
  for (const { geo, matrix, start, count } of parts) {
    const pos = geo.getAttribute('position');
    const n = pos.count;
    copyAttribute(pos, 3, position, v0);
    copyAttribute(geo.getAttribute('normal'), 3, normal, v0);
    const uvAttr = geo.getAttribute('uv');
    if (uvAttr) copyAttribute(uvAttr, 2, uv, v0);
    const colAttr = geo.getAttribute('color');
    if (colAttr) copyAttribute(colAttr, 3, color, v0);

    let mirrored = false;
    if (matrix) {
      const e = matrix.elements;
      const m = _normalMatrix.getNormalMatrix(matrix).elements;
      mirrored = matrix.determinant() < 0;
      for (let i = v0 * 3, end = (v0 + n) * 3; i < end; i += 3) {
        const x = position[i];
        const y = position[i + 1];
        const z = position[i + 2];
        position[i] = e[0] * x + e[4] * y + e[8] * z + e[12];
        position[i + 1] = e[1] * x + e[5] * y + e[9] * z + e[13];
        position[i + 2] = e[2] * x + e[6] * y + e[10] * z + e[14];
        const nx = normal[i];
        const ny = normal[i + 1];
        const nz = normal[i + 2];
        const tx = m[0] * nx + m[3] * ny + m[6] * nz;
        const ty = m[1] * nx + m[4] * ny + m[7] * nz;
        const tz = m[2] * nx + m[5] * ny + m[8] * nz;
        const len = Math.hypot(tx, ty, tz) || 1;
        normal[i] = tx / len;
        normal[i + 1] = ty / len;
        normal[i + 2] = tz / len;
      }
    }

    const src = geo.index ? geo.index.array : null;
    for (let k = 0; k < count; k += 3) {
      const a = src ? src[start + k] : start + k;
      const b = src ? src[start + k + 1] : start + k + 1;
      const c = src ? src[start + k + 2] : start + k + 2;
      index[i0 + k] = v0 + a;
      // A mirroring transform turns triangles inside out: swap two corners to restore the winding.
      index[i0 + k + 1] = v0 + (mirrored ? c : b);
      index[i0 + k + 2] = v0 + (mirrored ? b : c);
    }
    v0 += n;
    i0 += count;
  }

  const out = new BufferGeometry();
  out.setAttribute('position', new BufferAttribute(position, 3));
  out.setAttribute('normal', new BufferAttribute(normal, 3));
  out.setAttribute('uv', new BufferAttribute(uv, 2));
  if (color) out.setAttribute('color', new BufferAttribute(color, 3));
  out.setIndex(new BufferAttribute(index, 1));
  out.computeBoundingBox();
  out.computeBoundingSphere();
  return out;
}

/**
 * Fuses geometries into one indexed geometry with position / normal / uv (+ colour when any input has it).
 * Inputs may be indexed or not and may lack normals, UVs or colours; extra attributes are dropped.
 * Entries may also be `{geo, matrix}` to transform a geometry while merging. Inputs are not modified.
 */
export function mergeGeos(list) {
  const batch = createBatch();
  for (const item of list) {
    if (!item) continue;
    if (item.isBufferGeometry) addPart(batch, item);
    else addPart(batch, item.geo, item.matrix ?? null);
  }
  return buildBatch(batch);
}

/**
 * Returns a NEW geometry: the mesh's geometry with its world matrix applied (attributes normalised
 * as in mergeGeos). The mesh and its possibly shared source geometry are left untouched.
 */
export function bakeTransform(mesh) {
  mesh.updateWorldMatrix(true, false);
  const batch = createBatch();
  addPart(batch, mesh.geometry, mesh.matrixWorld);
  return buildBatch(batch);
}

const isPlainMesh = (o) =>
  o.isMesh && !o.isInstancedMesh && !o.isSkinnedMesh && !o.isBatchedMesh && !o.morphTargetInfluences;

/**
 * Collapses a static subtree into one mesh per material (and per shadow-flag combination), with all
 * world transforms baked in. This is what keeps the block at a few dozen draw calls.
 *
 * Returns a new Group holding the merged meshes plus everything that cannot or must not be merged,
 * re-parented with its world transform intact:
 *   - subtrees flagged `userData.noMerge` (dynamic props, animated parts),
 *   - hidden subtrees (`visible === false`),
 *   - lights, lines, points, sprites, instanced and skinned meshes.
 * The source `root` is left gutted and should be discarded. Source geometries are not disposed
 * (they may be shared with dynamic instances) and materials are reused as they are.
 * Note: transparent meshes sharing a material become one draw call and no longer sort against each other.
 */
export function mergeStatic(root) {
  root.updateMatrixWorld(true);

  const buckets = new Map();
  const keep = [];
  let sourceMeshes = 0;

  function bucketFor(mesh, material) {
    const key = `${material.uuid}|${mesh.castShadow ? 1 : 0}${mesh.receiveShadow ? 1 : 0}|${mesh.renderOrder}|${mesh.layers.mask}`;
    let bucket = buckets.get(key);
    if (!bucket) {
      bucket = { material, mesh, batch: createBatch() };
      buckets.set(key, bucket);
    }
    return bucket.batch;
  }

  function collect(mesh) {
    const { geometry, material } = mesh;
    sourceMeshes++;
    if (Array.isArray(material)) {
      // Multi-material mesh: each geometry group goes to its own material's bucket.
      const groups = geometry.groups.length ? geometry.groups : [{ start: 0, count: Infinity, materialIndex: 0 }];
      for (const g of groups) {
        const m = material[g.materialIndex];
        if (m) addPart(bucketFor(mesh, m), geometry, mesh.matrixWorld, g.start, g.count);
      }
    } else {
      const { start, count } = geometry.drawRange;
      addPart(bucketFor(mesh, material), geometry, mesh.matrixWorld, start, count);
    }
  }

  (function walk(obj) {
    if (obj !== root) {
      if (obj.userData.noMerge || !obj.visible) {
        keep.push(obj);
        return;
      }
      const mergeable = isPlainMesh(obj) && obj.geometry && obj.material;
      if (!mergeable && (obj.isMesh || obj.isLight || obj.isLine || obj.isPoints || obj.isSprite || obj.isLOD)) {
        keep.push(obj);
        return;
      }
      if (mergeable) collect(obj);
    }
    for (const child of obj.children) walk(child);
  })(root);

  const out = new Group();
  out.name = 'static';
  let vertices = 0;
  let triangles = 0;

  for (const { material, mesh, batch } of buckets.values()) {
    if (batch.indices === 0) continue;
    const merged = new Mesh(buildBatch(batch), material);
    merged.name = `merged:${material.name || material.type}`;
    merged.castShadow = mesh.castShadow;
    merged.receiveShadow = mesh.receiveShadow;
    merged.renderOrder = mesh.renderOrder;
    merged.layers.mask = mesh.layers.mask;
    merged.matrixAutoUpdate = false;
    vertices += batch.vertices;
    triangles += batch.indices / 3;
    out.add(merged);
  }

  // attach() keeps each object's world transform while moving it under the new group.
  for (const obj of keep) out.attach(obj);

  out.userData.mergeStats = { sourceMeshes, mergedMeshes: out.children.length - keep.length, kept: keep.length, vertices, triangles };
  return out;
}
