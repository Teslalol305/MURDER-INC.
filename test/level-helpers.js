// Builds the real level in node: real physics, the stub prop factory, and a material library that
// hands out plain materials (no canvas, no DOM). Shared by the level tests.

import * as THREE from 'three';
import * as brand from '../src/config/brand.js';
import * as catalog from '../src/config/catalog.js';
import * as flow from '../src/config/flow.js';
import * as look from '../src/config/look.js';
import * as text from '../src/config/text.js';
import { createEvents } from '../src/core/events.js';
import { createRng } from '../src/core/rng.js';
import { createLevel } from '../src/level.js';
import { createPhysics } from '../src/physics.js';
import { createProps } from '../src/stubs/props.js';

/** The mats API (CONTRACT 6.1) without textures: every call returns a material of its own kind. */
export function fakeMats() {
  const cache = new Map();
  const made = (key, make) => {
    if (!cache.has(key)) cache.set(key, make());
    return cache.get(key);
  };
  const standard = (name) => {
    const m = new THREE.MeshStandardMaterial();
    m.name = name;
    return m;
  };
  const sized = (kind, key, w, h) => ({ material: made(`${kind}|${key}`, () => standard(kind)), w, h });
  return {
    get: (name, opts) => made(`get|${name}|${JSON.stringify(opts || {})}`, () => standard(name)),
    emissive: (color, intensity = 2) => made(`emissive|${color}|${intensity}`, () => new THREE.MeshBasicMaterial({ color })),
    sign: (spec = {}) => sized('sign', JSON.stringify(spec), spec.w ?? 2, spec.h ?? 0.6),
    facade: (spec = {}) => made(`facade|${JSON.stringify(spec)}`, () => standard(spec.base || 'brick_red')),
    poster: (kind = 'ad', seed = 0) => sized('poster', `${kind}|${seed}`, 0.6, 0.9),
    graffiti: (label = 'RULE', seed = 0) => sized('graffiti', `${label}|${seed}`, Math.max(1, label.length * 0.42), 0.9),
    decal: (kind = 'grime') => sized('decal', kind, kind === 'lane' ? 0.15 : 2, kind === 'lane' ? 3 : 2),
    drawIPX: () => 0,
    canvasTexture: () => new THREE.Texture(),
    names: () => Object.keys(catalog.MATERIALS),
    update() {},
  };
}

/** A fresh G with everything the level reads, and the level built into it. */
export function buildLevel(seed = 1994) {
  const G = {
    THREE,
    params: {},
    events: createEvents(),
    rng: createRng(seed),
    time: { t: 0, dt: 1 / 60, frame: 0, real: 0 },
    config: { brand, text, flow, catalog, look },
    quality: { name: 'test' },
    scene: new THREE.Scene(),
    camera: new THREE.PerspectiveCamera(),
  };
  G.mats = fakeMats();
  G.physics = createPhysics(G);
  G.props = createProps(G);
  G.level = createLevel(G);
  return G;
}
