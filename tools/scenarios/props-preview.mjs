// Prop preview without a browser: builds props in node and draws them with a small software rasteriser
// (flat material colours, one key light, no textures) to PNG contact sheets. It is for checking
// silhouettes, proportions, colliders and inside-out faces in a second; the real look needs the game
// (tools/scenarios/props-gallery.cjs).
//
//   node tools/scenarios/props-preview.mjs sedan taxi 'van:{"variant":"vulture"}'
//   node tools/scenarios/props-preview.mjs --all             every catalogue prop, one sheet each
//   options: --out=shots/props/preview  --colliders  --size=960x540  --state=open  --t=0.5  --view=3
//            --grid=4x3   contact sheets: twelve props per picture, one view each
//
// Each sheet shows four views: front three-quarter at eye height (1.68 m), rear three-quarter from above,
// a long-lens side elevation and a plan view. The striped post is 1.8 m tall.

import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { deflateSync } from 'node:zlib';
import * as THREE from 'three';
import * as brand from '../../src/config/brand.js';
import * as catalog from '../../src/config/catalog.js';
import * as look from '../../src/config/look.js';
import { createRng } from '../../src/core/rng.js';
import { createProps } from '../../src/props.js';

// ---- arguments ----------------------------------------------------------------------------------

const args = process.argv.slice(2);
const flag = (name, fallback) => {
  const hit = args.find((a) => a === `--${name}` || a.startsWith(`--${name}=`));
  if (!hit) return fallback;
  return hit.includes('=') ? hit.slice(hit.indexOf('=') + 1) : true;
};
const OUT = flag('out', 'shots/props/preview');
const [W, H] = String(flag('size', '960x540')).split('x').map(Number);
const SHOW_COLLIDERS = !!flag('colliders', false);
const STATE = flag('state', '');
const STATE_T = Number(flag('t', 0.5));
const ONE_VIEW = Number(flag('view', 0)); // 1…4: that view alone, full frame
const GRID = flag('grid', ''); // '4x3': many props per sheet, one view each (--view picks which, default 1)
const SS = 2; // supersampling

// ---- a stand-in material library: catalogue colours, nothing else ---------------------------------

const made = new Map();
const mats = {
  get(name, opts = {}) {
    const key = `${name}|${JSON.stringify(opts)}`;
    let m = made.get(key);
    if (!m) {
      const def = catalog.MATERIALS[name];
      if (!def) console.warn(`unknown material '${name}'`);
      const o = { ...(def || { color: 0xff00ff }), ...opts };
      m = new THREE.MeshStandardMaterial({ color: o.color, roughness: o.roughness ?? 0.8, metalness: o.metalness ?? 0 });
      if (o.emissive !== undefined) m.emissive.set(o.emissive).multiplyScalar(o.emissiveIntensity ?? 1);
      if (o.transparent) {
        m.transparent = true;
        m.opacity = o.opacity ?? 1;
      }
      if (o.doubleSide) m.side = THREE.DoubleSide;
      m.name = name;
      made.set(key, m);
    }
    return m;
  },
  emissive: (color, intensity = 2) => {
    const m = new THREE.MeshBasicMaterial({ color });
    m.color.multiplyScalar(intensity);
    return m;
  },
  sign: (spec = {}) => ({ material: flat(0xe8e4d8), w: spec.w ?? 2, h: spec.h ?? 0.6 }),
  poster: () => ({ material: flat(0xd8d2c0), w: 0.6, h: 0.9 }),
  graffiti: (text = 'RULE') => ({ material: flat(0xe2222b), w: Math.max(1, text.length * 0.42), h: 0.9 }),
  decal: () => ({ material: flat(0x202020), w: 0.9, h: 0.9 }),
  drawIPX: () => 100,
  canvasTexture: () => new THREE.Texture(),
};
function flat(color) {
  const m = new THREE.MeshBasicMaterial({ color });
  m.userData.preview = 'decal';
  return m;
}

const G = {
  THREE,
  rng: createRng(1994),
  mats,
  quality: { name: 'medium' },
  config: { brand, catalog, look },
  time: { t: 0, dt: 1 / 30 },
  camera: new THREE.PerspectiveCamera(),
};
const props = createProps(G);

// ---- rasteriser ------------------------------------------------------------------------------------

const KEY = new THREE.Vector3(0.45, 0.8, 0.4).normalize();
const SKY = [0.62, 0.68, 0.8];
const BOUNCE = [0.32, 0.28, 0.24];

function makeTarget(w, h) {
  return { w, h, color: new Float32Array(w * h * 3), depth: new Float32Array(w * h) }; // depth holds 1 / w: bigger is nearer
}

/** Draws triangles (world space) into the target through `camera` inside the viewport rectangle. */
function drawMesh(target, camera, vp, tris, shade) {
  const m = camera.projectionMatrix.clone().multiply(camera.matrixWorldInverse).elements;
  const { w, color, depth } = target;
  const p = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
  for (let t = 0; t < tris.count; t++) {
    let clipped = false;
    for (let k = 0; k < 3; k++) {
      const o = (t * 3 + k) * 3;
      const x = tris.pos[o];
      const y = tris.pos[o + 1];
      const z = tris.pos[o + 2];
      const cw = m[3] * x + m[7] * y + m[11] * z + m[15];
      if (cw < 0.05) {
        clipped = true;
        break;
      }
      p[k][0] = vp.x + ((m[0] * x + m[4] * y + m[8] * z + m[12]) / cw * 0.5 + 0.5) * vp.w;
      p[k][1] = vp.y + (0.5 - (m[1] * x + m[5] * y + m[9] * z + m[13]) / cw * 0.5) * vp.h;
      p[k][2] = 1 / cw; // 1 / w is what interpolates linearly on screen
    }
    if (clipped) continue;
    const [a, b, c] = p;
    const area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    const front = area < 0; // screen y runs down
    if (!front && !tris.double) continue;
    if (Math.abs(area) < 1e-9) continue;
    const x0 = Math.max(vp.x, Math.floor(Math.min(a[0], b[0], c[0])));
    const x1 = Math.min(vp.x + vp.w - 1, Math.ceil(Math.max(a[0], b[0], c[0])));
    const y0 = Math.max(vp.y, Math.floor(Math.min(a[1], b[1], c[1])));
    const y1 = Math.min(vp.y + vp.h - 1, Math.ceil(Math.max(a[1], b[1], c[1])));
    const col = shade(t, front);
    for (let py = y0; py <= y1; py++) {
      for (let px = x0; px <= x1; px++) {
        const sx = px + 0.5;
        const sy = py + 0.5;
        const w0 = ((b[0] - sx) * (c[1] - sy) - (b[1] - sy) * (c[0] - sx)) / area;
        const w1 = ((c[0] - sx) * (a[1] - sy) - (c[1] - sy) * (a[0] - sx)) / area;
        const w2 = 1 - w0 - w1;
        if (w0 < 0 || w1 < 0 || w2 < 0) continue;
        if (tris.stipple && ((px >> 1) + (py >> 1)) % tris.stipple !== 0) continue;
        const z = (w0 * a[2] + w1 * b[2] + w2 * c[2]) * (1 + (tris.bias || 0));
        const i = py * w + px;
        if (z <= depth[i]) continue;
        if (!tris.noDepth) depth[i] = z;
        if (tris.alpha < 1) {
          color[i * 3] += (col[0] - color[i * 3]) * tris.alpha;
          color[i * 3 + 1] += (col[1] - color[i * 3 + 1]) * tris.alpha;
          color[i * 3 + 2] += (col[2] - color[i * 3 + 2]) * tris.alpha;
        } else {
          color[i * 3] = col[0];
          color[i * 3 + 1] = col[1];
          color[i * 3 + 2] = col[2];
        }
      }
    }
  }
}

const _n = new THREE.Vector3();
const _c = new THREE.Color();
const _out = [0, 0, 0];

/** Flattens one mesh to world-space triangles with per-triangle colour. */
function meshTriangles(mesh) {
  const g = mesh.geometry;
  const pos = g.getAttribute('position');
  const nor = g.getAttribute('normal');
  const colAttr = g.getAttribute('color');
  const idx = g.index;
  const count = (idx ? idx.count : pos.count) / 3;
  const out = { count, pos: new Float32Array(count * 9), nrm: new Float32Array(count * 3), col: new Float32Array(count * 3) };
  const material = mesh.material;
  const v = new THREE.Vector3();
  const nm = new THREE.Matrix3().getNormalMatrix(mesh.matrixWorld);
  const base = material.color ? material.color : new THREE.Color(1, 1, 1);
  for (let t = 0; t < count; t++) {
    _n.set(0, 0, 0);
    _c.setRGB(0, 0, 0);
    for (let k = 0; k < 3; k++) {
      const i = idx ? idx.getX(t * 3 + k) : t * 3 + k;
      v.fromBufferAttribute(pos, i).applyMatrix4(mesh.matrixWorld);
      out.pos.set([v.x, v.y, v.z], (t * 3 + k) * 3);
      _n.add(v.fromBufferAttribute(nor, i));
      if (colAttr && material.vertexColors) _c.r += colAttr.getX(i) / 3, _c.g += colAttr.getY(i) / 3, _c.b += colAttr.getZ(i) / 3;
    }
    _n.applyMatrix3(nm).normalize();
    out.nrm.set([_n.x, _n.y, _n.z], t * 3);
    if (colAttr && material.vertexColors) out.col.set([_c.r * base.r, _c.g * base.g, _c.b * base.b], t * 3);
    else out.col.set([base.r, base.g, base.b], t * 3);
  }
  out.unlit = !!material.isMeshBasicMaterial;
  out.decal = material.userData.preview === 'decal' || material.name === 'props_decal' || material.name === 'props_lit' || material.name === 'props_billboard';
  out.double = material.side === THREE.DoubleSide;
  out.alpha = material.name === 'props_additive' ? 0.25 : material.transparent && !out.decal ? Math.max(0.25, material.opacity * 0.9) : 1;
  out.stipple = material.name === 'props_grid' ? 2 : 0;
  out.noDepth = material.name === 'props_additive';
  out.bias = out.decal ? 0.004 : 0;
  out.metal = material.metalness ?? 0;
  out.emissive = material.emissive ? [material.emissive.r, material.emissive.g, material.emissive.b] : null;
  if (out.decal) for (let t = 0; t < count; t++) out.col.set(material.name === 'props_lit' ? [1.0, 0.95, 0.8] : [0.82, 0.8, 0.74], t * 3);
  return out;
}

function shader(tris) {
  return (t, front) => {
    const r = tris.col[t * 3];
    const g = tris.col[t * 3 + 1];
    const b = tris.col[t * 3 + 2];
    if (tris.unlit || tris.decal) {
      _out[0] = r;
      _out[1] = g;
      _out[2] = b;
      return _out;
    }
    const s = front ? 1 : -1;
    const nx = tris.nrm[t * 3] * s;
    const ny = tris.nrm[t * 3 + 1] * s;
    const nz = tris.nrm[t * 3 + 2] * s;
    const diffuse = Math.max(0, nx * KEY.x + ny * KEY.y + nz * KEY.z) * 0.95;
    const up = ny * 0.5 + 0.5;
    const lift = 0.05 + tris.metal * 0.1; // keep dark metals readable
    for (let k = 0; k < 3; k++) {
      const albedo = Math.max([r, g, b][k], lift);
      const ambient = (SKY[k] * up + BOUNCE[k] * (1 - up)) * 0.55;
      _out[k] = albedo * (diffuse + ambient) + (tris.emissive ? tris.emissive[k] : 0);
    }
    return _out;
  };
}

/** Line box as thin triangles would be overkill: plot the 12 edges of a collider as dotted lines. */
function drawBoxEdges(target, camera, vp, min, max, color) {
  const m = camera.projectionMatrix.clone().multiply(camera.matrixWorldInverse).elements;
  const corner = (i) => [i & 1 ? max[0] : min[0], i & 2 ? max[1] : min[1], i & 4 ? max[2] : min[2]];
  const project = ([x, y, z]) => {
    const cw = m[3] * x + m[7] * y + m[11] * z + m[15];
    if (cw < 0.05) return null;
    return [vp.x + ((m[0] * x + m[4] * y + m[8] * z + m[12]) / cw * 0.5 + 0.5) * vp.w, vp.y + (0.5 - (m[1] * x + m[5] * y + m[9] * z + m[13]) / cw * 0.5) * vp.h];
  };
  for (const [i, j] of [[0, 1], [2, 3], [4, 5], [6, 7], [0, 2], [1, 3], [4, 6], [5, 7], [0, 4], [1, 5], [2, 6], [3, 7]]) {
    const a = project(corner(i));
    const b = project(corner(j));
    if (!a || !b) continue;
    const steps = Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]));
    for (let s = 0; s <= steps; s++) {
      const x = Math.round(a[0] + ((b[0] - a[0]) * s) / steps);
      const y = Math.round(a[1] + ((b[1] - a[1]) * s) / steps);
      if (x < vp.x || y < vp.y || x >= vp.x + vp.w || y >= vp.y + vp.h) continue;
      for (const [dx, dy] of [[0, 0], [1, 0], [0, 1]]) target.color.set(color, ((y + dy) * target.w + x + dx) * 3);
    }
  }
}

// ---- PNG -------------------------------------------------------------------------------------------

const CRC = new Uint32Array(256).map((_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body));
  return Buffer.concat([len, body, crc]);
}
function writePng(file, target) {
  const w = target.w / SS;
  const h = target.h / SS;
  const raw = Buffer.alloc((w * 3 + 1) * h);
  const tone = (v) => Math.round(255 * Math.min(1, Math.max(0, v)) ** (1 / 2.2));
  for (let y = 0; y < h; y++) {
    raw[y * (w * 3 + 1)] = 0;
    for (let x = 0; x < w; x++) {
      for (let k = 0; k < 3; k++) {
        let sum = 0;
        for (let sy = 0; sy < SS; sy++) for (let sx = 0; sx < SS; sx++) sum += target.color[((y * SS + sy) * target.w + x * SS + sx) * 3 + k];
        raw[y * (w * 3 + 1) + 1 + x * 3 + k] = tone(sum / (SS * SS));
      }
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr.set([8, 2, 0, 0, 0], 8);
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]));
}

// ---- one sheet per prop ----------------------------------------------------------------------------

function ground(size) {
  const s = Math.max(size * 2.2, 4);
  const geo = new THREE.PlaneGeometry(s, s, 1, 1).rotateX(-Math.PI / 2);
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: 0x55575c }));
  mesh.updateMatrixWorld();
  return mesh;
}

function post(x, z) {
  const group = new THREE.Group();
  for (let i = 0; i < 6; i++) {
    const seg = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.3, 0.05), new THREE.MeshBasicMaterial({ color: i % 2 ? 0xe2222b : 0xf4f2ec }));
    seg.position.set(x, 0.15 + i * 0.3, z);
    group.add(seg);
  }
  group.updateMatrixWorld(true);
  return group;
}

/** Builds a prop and everything needed to draw it: triangle batches, bounds, the four camera views. */
function stage(name, opts, aspect) {
  const prop = props.build(name, opts);
  if (STATE && prop.setState) prop.setState(STATE, STATE_T);
  if (prop.update) for (let i = 0; i < 40; i++) prop.update(1 / 30);
  prop.object.updateMatrixWorld(true);
  const [L, Hh, Wd] = prop.size;
  // Bounds of what is solid and showing: light shafts, flames and hidden parts do not count.
  const box = new THREE.Box3();
  prop.object.traverse((o) => {
    if (!o.isMesh || o.material.name === 'props_additive') return;
    for (let p = o; p; p = p.parent) if (!p.visible) return;
    box.union(new THREE.Box3().setFromObject(o));
  });
  const size = Math.max(box.max.x - box.min.x, box.max.z - box.min.z, 0.6);
  const cy = Math.min((box.max.y + box.min.y) / 2, 2.4);
  const cx = (box.max.x + box.min.x) / 2;
  const cz = (box.max.z + box.min.z) / 2;

  const scene = [ground(size), post(-L / 2 - 0.3, Wd / 2 + 0.25), prop.object];
  const batches = [];
  let triangles = 0;
  for (const root of scene) {
    root.traverse((o) => {
      if (!o.isMesh || !o.visible) return;
      let hidden = false;
      for (let p = o.parent; p; p = p.parent) if (!p.visible) hidden = true;
      if (hidden) return;
      const tris = meshTriangles(o);
      if (root === prop.object) triangles += tris.count;
      batches.push(tris);
    });
  }
  // Opaque first, see-through after.
  batches.sort((a, b) => (a.alpha < 1 || a.decal ? 1 : 0) - (b.alpha < 1 || b.decal ? 1 : 0));

  // Each view backs off just far enough for the prop to fill its part of the sheet.
  const corners = [];
  for (let i = 0; i < 8; i++) corners.push(new THREE.Vector3(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z));
  const probe = new THREE.PerspectiveCamera(40, aspect, 0.05, 400);
  const from = (dx, dy, dz, fov, lookY = cy) => {
    const dir = new THREE.Vector3(dx, dy, dz).normalize();
    let dist = size * 2;
    probe.fov = fov;
    probe.updateProjectionMatrix();
    for (let pass = 0; pass < 4; pass++) {
      probe.position.set(cx, lookY, cz).addScaledVector(dir, dist);
      probe.lookAt(cx, lookY, cz);
      probe.updateMatrixWorld(true);
      let worst = 0;
      for (const corner of corners) {
        const p = corner.clone().project(probe);
        worst = Math.max(worst, Math.abs(p.x), Math.abs(p.y));
      }
      dist *= worst / 0.86;
    }
    return { eye: [cx + dir.x * dist, Math.max(0.25, lookY + dir.y * dist), cz + dir.z * dist], fov, look: [cx, lookY, cz] };
  };
  const views = [from(0.75, 0.2, 0.85, 40), from(-0.85, 0.5, -0.75, 40), from(0, 0.02, 1, 14), from(0.001, 1, 0.12, 16, 0)];
  const fit = [box.min.x + L / 2, L / 2 - box.max.x, box.min.y, Hh - box.max.y, box.min.z + Wd / 2, Wd / 2 - box.max.z].map((v) => v.toFixed(2));
  return { prop, batches, views, triangles, fit };
}

function drawView(target, staged, view, vp) {
  const camera = new THREE.PerspectiveCamera(view.fov, vp.w / vp.h, 0.05, 400);
  camera.position.fromArray(view.eye);
  camera.lookAt(...view.look);
  camera.updateMatrixWorld(true);
  camera.updateProjectionMatrix();
  for (const tris of staged.batches) drawMesh(target, camera, vp, tris, shader(tris));
  if (SHOW_COLLIDERS) {
    for (const c of staged.prop.colliders) drawBoxEdges(target, camera, vp, c.min, c.max, c.bulletOnly ? [1, 0.8, 0.1] : [0.2, 1, 0.4]);
  }
}

function blank() {
  const target = makeTarget(W * SS, H * SS);
  const bg = [0.09, 0.1, 0.13];
  for (let i = 0; i < target.color.length; i += 3) target.color.set(bg, i);
  return target;
}

function report(label, staged, file) {
  const { prop, triangles, fit } = staged;
  console.log(`${prop.fallback ? 'BOX ' : ''}${label.padEnd(20)} ${String(triangles).padStart(5)} tris  ${prop.colliders.length} col  margins x[${fit[0]} ${fit[1]}] y[${fit[2]} ${fit[3]}] z[${fit[4]} ${fit[5]}]  → ${file}`);
}

function sheet(label, name, opts) {
  const single = ONE_VIEW >= 1 && ONE_VIEW <= 4;
  const staged = stage(name, opts, W / H);
  const target = blank();
  const vw = single ? W * SS : (W * SS) / 2;
  const vh = single ? H * SS : (H * SS) / 2;
  (single ? [staged.views[ONE_VIEW - 1]] : staged.views).forEach((view, i) => {
    drawView(target, staged, view, { x: (i % 2) * vw, y: Math.floor(i / 2) * vh, w: vw, h: vh });
  });
  const file = join(OUT, `${label.replace(/\W+/g, '_')}.png`);
  writePng(file, target);
  report(label, staged, file);
}

/** Contact sheets: cols × rows props per picture. */
function contactSheets(entries) {
  const [cols, rows] = GRID.split('x').map(Number);
  const per = cols * rows;
  const vw = Math.floor((W * SS) / cols);
  const vh = Math.floor((H * SS) / rows);
  for (let first = 0; first < entries.length; first += per) {
    const target = blank();
    const file = join(OUT, `sheet_${String(first / per).padStart(2, '0')}.png`);
    entries.slice(first, first + per).forEach(([label, name, opts], i) => {
      const staged = stage(name, opts, vw / vh);
      drawView(target, staged, staged.views[Math.max(1, ONE_VIEW) - 1], { x: (i % cols) * vw, y: Math.floor(i / cols) * vh, w: vw, h: vh });
      report(label, staged, file);
    });
    writePng(file, target);
  }
}

const wanted = args.filter((a) => !a.startsWith('--'));
const list = flag('all', false) ? props.names() : wanted;
if (!list.length) {
  console.log('usage: node tools/scenarios/props-preview.mjs <prop>[:{"opts":…}] … | --all  [--out=dir] [--colliders] [--state=s]');
  process.exit(1);
}
const entries = list.map((spec) => {
  const cut = spec.indexOf(':');
  const name = cut < 0 ? spec : spec.slice(0, cut);
  const opts = cut < 0 ? { seed: 3 } : { seed: 3, ...JSON.parse(spec.slice(cut + 1)) };
  return [cut < 0 ? name : `${name}_${Object.values(opts).join('_')}`, name, opts];
});
if (GRID) contactSheets(entries);
else for (const [label, name, opts] of entries) sheet(label, name, opts);
