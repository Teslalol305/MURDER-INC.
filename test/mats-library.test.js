// The material library's tables (src/mats.js and src/mats/*): every catalogue material is dressed,
// every look points at something that exists, and sign specs resolve the way the contract says.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as brand from '../src/config/brand.js';
import { MATERIALS } from '../src/config/catalog.js';
import { palette } from '../src/config/look.js';
import { MODULES } from '../src/core/contract.js';
import { LOOKS } from '../src/mats.js';
import { DECALS } from '../src/mats/decals.js';
import { POSTER_SIZE, POSTER_VARIANTS } from '../src/mats/paper.js';
import { createSignPainter } from '../src/mats/signs.js';
import { SETS } from '../src/mats/surfaces.js';

test('mats: every catalogue material has a look, and every look uses sets that exist', () => {
  for (const name of Object.keys(MATERIALS)) assert.ok(LOOKS[name], `no look for catalogue material '${name}'`);
  for (const [name, look] of Object.entries(LOOKS)) {
    assert.ok(MATERIALS[name], `look '${name}' is not in the catalogue`);
    for (const key of ['set', 'relief', 'gloss']) {
      if (look[key]) assert.ok(SETS[look[key]], `${name}.${key} names the unknown set '${look[key]}'`);
    }
    if (look.world) {
      assert.equal(look.world.length, 3);
      assert.ok(look.set, `${name}: the world patch needs a full texture set`);
      for (const v of look.world) assert.ok(v >= 0 && v <= 1);
    }
  }
  // The street is wet, the shop floor and the walls are not.
  assert.ok(LOOKS.asphalt.world[1] > LOOKS.sidewalk.world[1] && LOOKS.sidewalk.world[1] > 0);
  for (const dry of ['concrete', 'concrete_dark', 'cinder', 'brick_red', 'stucco']) assert.equal(LOOKS[dry].world[1], 0, dry);
});

test('mats: surface sets keep real-world scale and one pixel density on both axes', () => {
  for (const [name, set] of Object.entries(SETS)) {
    assert.equal(typeof set.build, 'function', name);
    assert.ok(set.tile[0] > 0 && set.tile[1] > 0, name);
    assert.ok(set.res > 0 && set.res <= 1, name);
    assert.ok(set.rough > 0 && set.rough <= 1, name);
    assert.ok(['ground', 'wall', 'prop'].includes(set.aniso), name);
  }
  // A brick is 0.2 m on a 67 mm course: 12 × 36 of them per repeat. A sidewalk flag is 1.5 m.
  assert.equal(Math.round(SETS.brick.tile[0] / 0.2), 12);
  assert.equal(Math.round(SETS.sidewalk.tile[0] / 1.5), 3);
  assert.equal(Math.round(SETS.cinder.tile[0] / 0.4), 6);
  for (const [name, unit] of [['brick', 0.2], ['sidewalk', 1.5], ['cinder', 0.4]]) {
    const count = SETS[name].tile[0] / unit;
    assert.ok(Math.abs(count - Math.round(count)) < 1e-9, `${name}: a repeat must hold a whole number of units`);
  }
  // The El's plate is one column face wide.
  assert.deepEqual(SETS.steel_el.tile, [0.6, 2.4]);
});

test('mats: posters and decals cover the contract kinds', () => {
  assert.deepEqual(Object.keys(POSTER_SIZE).sort(), ['ad', 'ipx', 'show', 'torn', 'wanted']);
  for (const kind of Object.keys(POSTER_SIZE)) assert.ok(POSTER_VARIANTS[kind] >= 1, kind);
  for (const kind of ['oil', 'crack', 'manhole', 'grime', 'scorch', 'bullet', 'crosswalk', 'arrow', 'lane']) {
    const def = DECALS[kind];
    assert.ok(def, `no decal '${kind}'`);
    assert.ok(def.size[0] > 0 && def.size[1] > 0 && def.variants >= 1 && def.roughness > 0);
  }
  assert.equal(DECALS.lane.size[0], 0.12); // a lane line is 12 cm wide
  assert.ok(DECALS.lane.tile > 0 && DECALS.lane_yellow.tile > 0); // road paint tiles: any length of line
});

test('mats: sign specs resolve to style defaults, and equal specs share a key', () => {
  const signs = createSignPainter({ size: 512, type: null, bank: null, brand, palette });
  const neon = signs.resolve({ text: 'OPEN', style: 'neon' });
  assert.deepEqual([neon.style, neon.w, neon.h, neon.lit, neon.fg], ['neon', 2, 0.6, true, palette.neonPink]);
  assert.equal(signs.resolve({ text: 'OPEN', style: 'neon', lit: false }).lit, false);

  // Painted boards and stencils only glow when asked to; a stencil never does.
  assert.equal(signs.resolve({ text: 'PAWN', style: 'painted' }).lit, false);
  assert.equal(signs.resolve({ text: 'PAWN', style: 'painted', lit: true }).lit, true);
  assert.equal(signs.resolve({ text: 'KEEP CLEAR', style: 'stencil', lit: true }).lit, false);
  for (const style of ['box', 'awning', 'street', 'plate']) assert.equal(signs.resolve({ text: 'X', style }).lit, true, style);

  // Unknown styles fall back to a box sign; sizes must be positive.
  assert.equal(signs.resolve({ text: 'X', style: 'hologram' }).style, 'box');
  assert.deepEqual([signs.resolve({ w: -1, h: 0 }).w, signs.resolve({ w: -1, h: 0 }).h], [2, 0.6]);

  // Colours may come as numbers, CSS strings or THREE.Color-likes.
  assert.equal(signs.resolve({ text: 'X', fg: '#ff0000' }).fg, 0xff0000);
  assert.equal(signs.resolve({ text: 'X', fg: 0x00ff00 }).fg, 0x00ff00);

  const a = signs.resolve({ text: 'WINES & LIQUORS', sub: 'LOTTO', w: 5, h: 1, style: 'box' });
  const b = signs.resolve({ style: 'box', h: 1, w: 5, sub: 'LOTTO', text: 'WINES & LIQUORS' });
  assert.equal(a.key, b.key);
  assert.notEqual(a.key, signs.resolve({ text: 'WINES & LIQUORS', sub: 'LOTTO', w: 5, h: 1, style: 'box', fg: 0x111111 }).key);
  assert.notEqual(a.key, signs.resolve({ text: 'WINES & LIQUORS', sub: 'LOTTO', w: 5, h: 1, style: 'box', lit: false }).key);

  // A plate takes a route bullet; other styles ignore it.
  const plate = signs.resolve({ text: 'Jamaica Av', style: 'plate', bullet: 1, bulletColor: 0xe2222b });
  assert.deepEqual([plate.bullet, plate.bulletColor], ['1', 0xe2222b]);
  assert.equal(signs.resolve({ text: 'X', style: 'box', bullet: 'J' }).bullet, '');
  // The same painted board always gets the same colour.
  assert.equal(signs.resolve({ text: 'PAWN & GOLD', style: 'painted' }).bg, signs.resolve({ text: 'PAWN & GOLD', style: 'painted' }).bg);
});

test('mats: the module table in the contract lists what createMats returns', () => {
  for (const member of ['get()', 'emissive()', 'sign()', 'facade()', 'poster()', 'graffiti()', 'decal()', 'drawIPX()', 'canvasTexture()', 'names()', 'update()']) {
    assert.ok(MODULES.mats.includes(member), member);
  }
});

test('mats: by day lit glass is dark glass, and the night lamp blobs stay off car bodies', async () => {
  const { WET_REACH } = await import('../src/mats.js');
  for (const name of ['glass_lit_warm', 'glass_lit_cool', 'glass_car_lit']) {
    assert.equal(LOOKS[name].dayGlow, 0, `${name} does not glow by day`);
    assert.ok(MATERIALS[name].emissive !== undefined, `${name} glows at night (catalogue emissive)`);
    assert.ok(MATERIALS[name].color < 0x202020, `${name} is dark glass`);
  }
  assert.ok(LOOKS.glass_store.dayGlow <= 0.05);
  // The skylights change colour, not only brightness.
  assert.ok(LOOKS.glass_skylight.dayEmissive !== undefined && MATERIALS.glass_skylight.emissive !== LOOKS.glass_skylight.dayEmissive);
  for (const name of ['car_paint', 'glass_car', 'glass_car_lit']) assert.ok(LOOKS[name].nightEnv > 0 && LOOKS[name].nightEnv < 1, name);
  // Car paint is an even clear coat: no painted roughness pattern.
  assert.equal(LOOKS.car_paint.gloss, undefined);
  // Standing water is a world material with its own day albedo, wet only where the hydrant reaches by day.
  for (const [name, look] of Object.entries(LOOKS)) if (look.soak) assert.ok(look.world && look.day !== undefined, name);
  assert.ok(LOOKS.asphalt_wet.soak);
  assert.equal(LOOKS.asphalt_wet.day, LOOKS.asphalt.day, 'outside the reach it is the dry street');
  assert.ok(WET_REACH.radius[0] > WET_REACH.radius[1] && WET_REACH.gutter > 0);
});

test('mats: the world patch gates the wet street by the hydrant and greys the day sky light', async () => {
  const THREE = await import('three');
  const { patchWorld } = await import('../src/mats/shader.js');
  const material = new THREE.MeshStandardMaterial();
  const v = (x) => ({ value: x });
  const uniforms = { miMacro: v(null), miLook: v(new THREE.Vector4()), miDry: v(1), miWetLine: v(new THREE.Vector4()), miWetSize: v(new THREE.Vector3()), miSoak: v(0) };
  patchWorld(material, uniforms, true);
  const lib = THREE.ShaderLib.physical;
  const shader = { uniforms: {}, vertexShader: lib.vertexShader, fragmentShader: lib.fragmentShader };
  material.onBeforeCompile(shader);
  for (const name of ['miWetLine', 'miWetSize', 'miSoak', 'miDry']) assert.ok(shader.uniforms[name], name);
  assert.match(shader.fragmentShader, /uniform vec4 miWetLine;/);
  assert.match(shader.fragmentShader, /float miReach = /);
  assert.match(shader.fragmentShader, /iblIrradiance = mix\( iblIrradiance, vec3\( dot\( iblIrradiance/);
  // The grey-down comes after three.js gathers the image-based light.
  const f = shader.fragmentShader;
  assert.ok(f.indexOf('#include <lights_fragment_maps>') >= 0 && f.indexOf('iblIrradiance = mix') > f.indexOf('#include <lights_fragment_maps>'));
  assert.ok(f.indexOf('iblIrradiance = mix') < f.indexOf('#include <lights_fragment_end>'));
});
