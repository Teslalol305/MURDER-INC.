// G.props — the prop factory (CONTRACT 6.2).
//
// props.build(name, opts) → {object, colliders, size, surface, dynamic?, update?, setState?, lights?, anchors?}
//
// Every catalogue prop (src/config/catalog.js PROPS) has a builder in src/props/*.js that models it as
// low-poly geometry inside its catalogue box. Geometry is built once per distinct shape and shared by
// every instance; an instance only chooses materials (paint colour, dome light) and, for the few props
// with state, gets its own moving parts. A prop is a Group holding one mesh per material, which is what
// the level's static merge wants.
//
// Conventions (also in docs/CONTRACT.md 6.2):
//   origin on the ground at the footprint centre, length along +X, up +Y
//   vehicles point their nose at +X; everything with a front (benches, booths, signs, lamps) faces +Z
//   opts: {color, seed, variant, open, lit, on, text}

import { Group, Mesh } from 'three';
import { PROPS } from './config/catalog.js';
import { palette } from './config/look.js';
import { boxGeo } from './core/geo.js';
import { registerClutter } from './props/clutter.js';
import { registerGameplay } from './props/gameplay.js';
import { Builder } from './props/kit.js';
import { registerLot } from './props/lot.js';
import { createPropMaterials } from './props/materials.js';
import { registerShop } from './props/shop.js';
import { registerStreet } from './props/street.js';
import { registerVehicles } from './props/vehicles.js';

// Fallback box: catalogue surface → catalogue material.
const SURFACE_MATERIAL = {
  car: 'car_paint',
  metal: 'metal_galv',
  concrete: 'concrete',
  wood: 'wood',
  rubber: 'rubber',
  cloth: 'fabric',
  glass: 'glass_store',
  dirt: 'dirt',
};

const UNKNOWN = { size: [1, 1, 1], surface: 'metal' };

/** Scrambles a seed so that picks made from the same seed (shape, colour, dome light) do not line up. */
const scramble = (seed, salt) => (Math.imul((seed + salt) | 0, 0x9e3779b1) >>> 8) & 0xffff;

const noShadow = (slot) =>
  slot === '@decal' || slot === '@lit' || slot === '@glow' || slot.startsWith('#') || slot.includes('"transparent":true');

export function createProps(G) {
  const rng = G.rng.fork('props');
  const materials = createPropMaterials(G);
  const registry = new Map(); // name → spec
  const protos = new Map(); // shape key → built geometry, colliders, lamp hints
  const warned = new Set();
  const counts = { built: 0, fallbacks: [] };
  const env = { G, materials, palette };

  /**
   * spec: {
   *   build(b, o)        fills a Builder (src/props/kit.js) with the static shape
   *   variants           how many different shapes a seed can pick (default 1)
   *   key(o)             the options that change the shape, as a string
   *   paint, colors      catalogue material behind the '@paint' slot and its palette when opts.color is absent
   *   color(o)           a colour forced by the options (wins over the palette, loses to opts.color)
   *   dome               chance that a parked car has its interior light on
   *   rig(prop, o, env)  per instance: moving parts, update(dt), setState()
   * }
   */
  const R = {
    add(name, spec) {
      registry.set(name, spec);
    },
    env,
  };
  registerVehicles(R);
  registerStreet(R);
  registerClutter(R);
  registerShop(R);
  registerLot(R);
  registerGameplay(R);

  function warnOnce(key, ...message) {
    if (warned.has(key)) return;
    warned.add(key);
    console.warn(...message);
  }

  function protoFor(name, def, spec, o) {
    const variant = spec.variants > 1 ? o.seed % spec.variants : 0;
    const key = `${name}|${spec.key ? spec.key(o) : ''}|${variant}`;
    let proto = protos.get(key);
    if (!proto) {
      const b = new Builder({ name, size: def.size, rng: G.rng.fork(`props:${key}`), atlas: materials.rect });
      spec.build(b, { ...o, variantIndex: variant }, env);
      proto = b.finish();
      protos.set(key, proto);
    }
    return proto;
  }

  function construct(name, def, spec, o) {
    const proto = protoFor(name, def, spec, o);
    const inst = {
      paint: spec.paint || 'car_paint',
      color:
        o.color ??
        (spec.color ? spec.color(o) : undefined) ??
        (spec.colors ? spec.colors[scramble(o.seed, 17) % spec.colors.length] : undefined),
      lit: o.lit ?? (spec.dome ? scramble(o.seed, 91) / 0xffff < spec.dome : false),
    };

    const object = new Group();
    object.name = name;
    const nodes = {};
    const castShadows = def.size[1] > 0.3;
    for (const node of proto.nodes) {
      let group = object;
      if (node.name) {
        group = new Group();
        group.name = node.name;
        group.position.fromArray(node.pivot);
        object.add(group);
        nodes[node.name] = group;
      }
      for (const [slot, geometry] of node.parts) {
        const mesh = new Mesh(geometry, proto.materials.get(slot) || materials.resolve(slot, inst));
        mesh.name = slot;
        mesh.castShadow = castShadows && !noShadow(slot);
        mesh.receiveShadow = slot !== '@glow' && slot !== '@lit';
        group.add(mesh);
      }
    }
    object.userData.triangles = proto.triangles;

    const prop = {
      object,
      // The catalogue has the last word on whether a prop collides at all.
      colliders: def.noCollide ? [] : proto.colliders.map((c) => ({ ...c, min: c.min.slice(), max: c.max.slice() })),
      size: def.size.slice(),
      surface: def.surface,
      nodes,
    };
    if (proto.lights.length) prop.lights = proto.lights.map((l) => ({ ...l, pos: l.pos.slice() }));
    if (Object.keys(proto.anchors).length) {
      prop.anchors = {};
      for (const [id, a] of Object.entries(proto.anchors)) prop.anchors[id] = { pos: a.pos.slice(), dir: a.dir.slice() };
    }
    if (spec.rig) spec.rig(prop, o, env);
    return prop;
  }

  /** The stand-in when a builder is missing or throws: a plain box of the catalogue size. */
  function fallback(name, def) {
    const [length, height, width] = def.size;
    const object = new Group();
    object.name = name;
    const body = new Mesh(boxGeo(length, height, width, { bottom: true }), G.mats.get(SURFACE_MATERIAL[def.surface] || 'metal_galv'));
    body.castShadow = height > 0.3;
    body.receiveShadow = true;
    object.add(body);
    if (!counts.fallbacks.includes(name)) counts.fallbacks.push(name);
    return {
      object,
      colliders: def.noCollide
        ? []
        : [{ min: [-length / 2, 0, -width / 2], max: [length / 2, height, width / 2], surface: def.surface }],
      size: def.size.slice(),
      surface: def.surface,
      nodes: {},
      fallback: true,
    };
  }

  function build(name, opts = {}) {
    let def = PROPS[name];
    if (!def) {
      warnOnce(`unknown ${name}`, `[props] unknown prop '${name}': add it to src/config/catalog.js`);
      def = UNKNOWN;
    }
    const seed = Number.isFinite(opts.seed) ? Math.abs(Math.floor(opts.seed)) : rng.int(0, 0xffff);
    const o = { ...opts, seed };
    const spec = registry.get(name);
    let prop = null;
    if (spec) {
      try {
        prop = construct(name, def, spec, o);
      } catch (err) {
        warnOnce(`failed ${name}`, `[props] '${name}' could not be built, a plain box stands in:`, err);
      }
    }
    if (!prop) prop = fallback(name, def);
    if (def.dynamic || prop.update || prop.setState) {
      prop.dynamic = true;
      prop.object.userData.noMerge = true;
    }
    counts.built++;
    return prop;
  }

  return {
    build,
    has: (name) => name in PROPS,
    names: () => Object.keys(PROPS),
    /** Debug: how many props were built, which names fell back to a box, how many shapes are cached. */
    stats: () => ({ built: counts.built, fallbacks: counts.fallbacks.slice(), shapes: protos.size }),
  };
}
