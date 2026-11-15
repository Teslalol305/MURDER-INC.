// Props on a small shared material set (CONTRACT 11.2): paint colours live in vertex colours when the
// material library offers {tint: 'vertex'}, and fall back to a material per colour when it does not.
import assert from 'node:assert/strict';
import test from 'node:test';
import * as THREE from 'three';
import * as brand from '../src/config/brand.js';
import * as catalog from '../src/config/catalog.js';
import * as look from '../src/config/look.js';
import { createRng } from '../src/core/rng.js';
import { createProps } from '../src/props.js';

function setup(tintable) {
  const cache = new Map();
  const flat = () => new THREE.MeshBasicMaterial();
  const mats = {
    get(name, opts = {}) {
      const key = `${name}|${JSON.stringify(opts)}`;
      if (!cache.has(key)) {
        const m = new THREE.MeshStandardMaterial({ color: opts.color ?? catalog.MATERIALS[name]?.color ?? 0x808080 });
        m.name = name;
        m.vertexColors = tintable && opts.tint === 'vertex';
        m.userData.opts = opts;
        cache.set(key, m);
      }
      return cache.get(key);
    },
    emissive: flat,
    sign: (spec = {}) => ({ material: flat(), w: spec.w ?? 2, h: spec.h ?? 0.6, uv: [0.25, 0.5, 0.5, 0.75] }),
    poster: () => ({ material: flat(), w: 0.6, h: 0.9 }),
    graffiti: () => ({ material: flat(), w: 2, h: 0.9, uv: [0.1, 0.1, 0.3, 0.2] }),
    decal: () => ({ material: flat(), w: 0.9, h: 0.9 }),
    drawIPX: () => 100,
    canvasTexture: () => new THREE.Texture(),
  };
  const G = { THREE, rng: createRng(7), mats, quality: { name: 'medium' }, config: { brand, catalog, look }, camera: new THREE.PerspectiveCamera() };
  return createProps(G);
}

const meshes = (prop) => {
  const out = [];
  prop.object.traverse((o) => o.isMesh && out.push(o));
  return out;
};
const paintOf = (prop) => meshes(prop).find((m) => m.name === '@paint');

test('tint: two sedans of different colours share one paint material, the colour is in the geometry', () => {
  const props = setup(true);
  const red = paintOf(props.build('sedan', { seed: 1, color: 0x9c2320 }));
  const blue = paintOf(props.build('sedan', { seed: 1, color: 0x24508f }));
  assert.equal(red.material, blue.material);
  assert.equal(red.material.vertexColors, true);
  const r = red.geometry.getAttribute('color');
  const b = blue.geometry.getAttribute('color');
  assert.ok(r && b, 'paint geometry carries a colour attribute');
  assert.ok(r.getX(0) > r.getZ(0) && b.getZ(0) > b.getX(0), 'red is red, blue is blue');
  // Same colour again: the same geometry, not another copy.
  assert.equal(paintOf(props.build('sedan', { seed: 1, color: 0x9c2320 })).geometry, red.geometry);
});

test('tint: without library support every colour keeps a material of its own', () => {
  const props = setup(false);
  const red = paintOf(props.build('sedan', { seed: 1, color: 0x9c2320 }));
  const blue = paintOf(props.build('sedan', { seed: 1, color: 0x24508f }));
  assert.notEqual(red.material, blue.material);
  assert.equal(red.material.userData.opts.color, 0x9c2320);
});

test('tint: lattices of every colour share one material; plain paints join their tinted twins', () => {
  const props = setup(true);
  const grids = new Set();
  for (const name of ['milk_crates', 'trash_can', 'shopping_cart', 'hoop']) {
    for (const m of meshes(props.build(name, { seed: 2 }))) if (m.material.name === 'props_grid') grids.add(m.material);
  }
  assert.equal(grids.size, 1);
  const names = new Set();
  for (const name of props.names()) {
    for (const m of meshes(props.build(name, { seed: 3 }))) {
      if (m.material.name === 'paint_red') names.add(JSON.stringify(m.material.userData.opts));
    }
  }
  assert.deepEqual([...names], ['{"tint":"vertex"}'], 'every red on the catalogue is one material');
});

test('tint: atlas rects from the material library are mapped onto the quads that show them', () => {
  const props = setup(true);
  const blade = props.build('sign_post', { variant: 'street', text: 'JAMAICA AV' });
  const own = meshes(blade).find((m) => m.name.startsWith('#own'));
  const uv = own.geometry.getAttribute('uv');
  for (let i = 0; i < uv.count; i++) {
    assert.ok(uv.getX(i) >= 0.25 - 1e-6 && uv.getX(i) <= 0.5 + 1e-6 && uv.getY(i) >= 0.5 - 1e-6 && uv.getY(i) <= 0.75 + 1e-6);
  }
});

test('tint: the unmerged gameplay props stay within a few draw calls', () => {
  const props = setup(true);
  assert.ok(meshes(props.build('master_case', { seed: 1 })).length <= 14);
  assert.ok(meshes(props.build('ipx_truck', { seed: 1 })).length <= 24);
});
