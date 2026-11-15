// Prop census without a browser: triangles, meshes and material slots per prop, and the distinct
// materials of the whole catalogue placed once (CONTRACT 11.2). The material library is a stand-in
// that only counts what it is asked for.
//
//   node tools/scenarios/props-census.mjs            table + totals
//   node tools/scenarios/props-census.mjs --slots    also list every distinct material

import * as THREE from 'three';
import * as brand from '../../src/config/brand.js';
import * as catalog from '../../src/config/catalog.js';
import * as look from '../../src/config/look.js';
import { createRng } from '../../src/core/rng.js';
import { createProps } from '../../src/props.js';

const SHOW_SLOTS = process.argv.includes('--slots');
const VERTEX_TINT = !process.argv.includes('--no-tint'); // --no-tint: a library without {tint: 'vertex'}

const made = new Map();
const flat = (name) => Object.assign(new THREE.MeshBasicMaterial(), { name });
const mats = {
  get(name, opts) {
    const key = opts ? `${name}|${JSON.stringify(opts)}` : name;
    let m = made.get(key);
    if (!m) {
      m = new THREE.MeshStandardMaterial();
      m.name = key;
      if (opts && ((opts.tint === 'vertex' && VERTEX_TINT) || opts.vertexColors)) m.vertexColors = true;
      made.set(key, m);
    }
    return m;
  },
  emissive: () => flat('emissive'),
  sign: (spec = {}) => ({ material: flat('mats_sign_page'), w: spec.w ?? 2, h: spec.h ?? 0.6, uv: [0, 0, 1, 1] }),
  poster: () => ({ material: flat('mats_paper_page'), w: 0.6, h: 0.9 }),
  graffiti: (text = '') => ({ material: flat('mats_paper_page'), w: Math.max(1, text.length * 0.42), h: 0.9 }),
  decal: () => ({ material: flat('mats_paper_page'), w: 0.9, h: 0.9 }),
  drawIPX: () => 100,
  canvasTexture: () => new THREE.Texture(),
};
// Signs and tags share atlas pages in the real library: one stand-in material per page class.
const pages = new Map();
for (const fn of ['sign', 'poster', 'graffiti', 'decal']) {
  const make = mats[fn];
  mats[fn] = (...args) => {
    const r = make(...args);
    const page = r.material.name;
    if (!pages.has(page)) pages.set(page, r.material);
    return { ...r, material: pages.get(page) };
  };
}

const G = {
  THREE,
  rng: createRng(1994),
  mats,
  quality: { name: 'medium' },
  config: { brand, catalog, look },
  time: { t: 0, dt: 1 / 60 },
  camera: new THREE.PerspectiveCamera(),
};
const props = createProps(G);

const all = new Map(); // material → {name, props:Set, tris}
let total = 0;
const rows = [];
for (const name of props.names()) {
  const prop = props.build(name, { seed: 3 });
  let tris = 0;
  let meshes = 0;
  let shadow = 0;
  const own = new Set();
  prop.object.traverse((o) => {
    if (!o.isMesh) return;
    const n = (o.geometry.index ? o.geometry.index.count : o.geometry.getAttribute('position').count) / 3;
    tris += n;
    meshes++;
    if (o.castShadow) shadow++;
    own.add(o.material);
    let e = all.get(o.material);
    if (!e) all.set(o.material, (e = { name: o.material.name || o.name, props: new Set(), tris: 0 }));
    e.props.add(name);
    e.tris += n;
  });
  total += tris;
  rows.push({ name, tris, meshes, materials: own.size, shadow, fallback: !!prop.fallback, dynamic: !!prop.dynamic });
}

console.log('prop                    tris  meshes  mats  shadow-casters');
for (const r of rows) {
  console.log(
    `${r.name.padEnd(22)} ${String(r.tris).padStart(5)} ${String(r.meshes).padStart(6)} ${String(r.materials).padStart(5)} ${String(r.shadow).padStart(6)}` +
      `${r.dynamic ? '  dyn' : ''}${r.fallback ? '  FALLBACK' : ''}`,
  );
}
console.log(`\n${rows.length} props, ${total} triangles, ${all.size} distinct materials`);
if (SHOW_SLOTS) {
  const list = [...all.values()].sort((a, b) => b.props.size - a.props.size);
  for (const e of list) console.log(`  ${e.name.padEnd(64)} ${String(e.props.size).padStart(3)} props ${String(e.tris).padStart(6)} tris`);
}
