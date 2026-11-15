// Stub props (CONTRACT 6.2): every catalogue prop as a box of its catalogue size with one collider and
// the catalogue surface. Good enough to block bullets, cast shadows and lay out a level against.
//
// Stateful props keep their contract methods:
//   master_case    a case with a gold beacon; setState('live' | 'grabbing' | 'taken', t), update(dt)
//   ipx_truck      blinking hazard lights; setState('idle' | 'open'), update(dt)
//   propane_tank,
//   welding_rack   setState('idle' | 'lit' | 'gone'): 'gone' hides the prop

import * as THREE from 'three';
import { PROPS } from '../config/catalog.js';
import { palette } from '../config/look.js';
import { boxGeo, planeGeo } from '../core/geo.js';
import { clamp } from '../core/util.js';

// Catalogue surface → catalogue material for the box.
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

// Props that read better with their own material or colour: [material, colour override].
const LOOKS = {
  taxi: ['car_paint', 0xf2c21a],
  burned_car: ['steel_rust'],
  ipx_truck: ['paint_white'],
  food_cart: ['metal_galv', 0xb8bcc0],
  traffic_barrel: ['plastic_orange'],
  traffic_cone: ['plastic_orange'],
  barricade: ['paint_white'],
  dumpster: ['paint_green'],
  trash_bags: ['trash_bag'],
  mailbox: ['paint_blue'],
  newspaper_box: ['paint_red'],
  hydrant: ['paint_red'],
  hydrant_open: ['paint_red'],
  milk_crates: ['paint_blue'],
  mattress: ['fabric', 0x8a8474],
  sandbags: ['dirt', 0x8a7a5c],
  tire_stack: ['tire'],
  oil_drum: ['paint_blue'],
  porta_potty: ['paint_blue'],
  street_lamp: ['metal_dark'],
  court_light: ['metal_dark'],
  traffic_light: ['metal_dark'],
  tree: ['leaves'],
  planter: ['concrete_dark'],
  fence_panel: ['chainlink'],
  fence_tall: ['chainlink'],
  manhole: ['metal_dark'],
  master_case: ['metal_dark'],
  propane_tank: ['paint_white'],
  welding_rack: ['paint_red'],
  billboard: ['metal_dark'],
  water_tower: ['wood'],
  awning: ['fabric_awning'],
  cardboard_boxes: ['cardboard'],
  pallet: ['plywood'],
  pallet_stack: ['plywood'],
};

const CAR_COLORS = [0x7a1d1d, 0x1d2a4a, 0x2a2c30, 0x8a8f96, 0xd8d6cf, 0x14301f, 0x3a2a1c];

// Lamp hints for atmos: prop → {kind, colour, intensity, range, height below the top}.
const LAMPS = {
  street_lamp: { kind: 'street', color: palette.sodium, intensity: 90, range: 20, drop: 0.3 },
  court_light: { kind: 'flood', color: 0xdfe8ff, intensity: 160, range: 30, drop: 0.3 },
  floodlight_stand: { kind: 'work', color: 0xfff1d0, intensity: 60, range: 14, drop: 0.2 },
};

export function createProps(G) {
  const rng = G.rng.fork('props');
  const geometries = new Map(); // prop name → shared box geometry
  const warned = new Set();

  function geometryFor(name, size) {
    let geo = geometries.get(name);
    if (!geo) {
      geo = boxGeo(size[0], size[1], size[2], { bottom: true });
      geometries.set(name, geo);
    }
    return geo;
  }

  function materialFor(name, def, opts) {
    const [material, tint] = LOOKS[name] || [SURFACE_MATERIAL[def.surface] || 'metal_galv'];
    let color = opts.color ?? tint;
    if (color === undefined && def.surface === 'car' && material === 'car_paint') {
      const i = opts.seed !== undefined ? Math.abs(Math.floor(opts.seed)) : rng.int(0, CAR_COLORS.length - 1);
      color = CAR_COLORS[i % CAR_COLORS.length];
    }
    return G.mats.get(material, color === undefined ? undefined : { color });
  }

  /** A small unlit glowing box, used for beacons, lamp heads and hazard lights. */
  function glowBox(parent, w, h, d, x, y, z, color, intensity) {
    const mesh = new THREE.Mesh(boxGeo(w, h, d), G.mats.emissive(color, intensity));
    mesh.position.set(x, y, z);
    parent.add(mesh);
    return mesh;
  }

  // ---- stateful props -----------------------------------------------------------------------

  function masterCase(prop, [, height]) {
    const body = prop.object.children[0];
    // Beacon: a thin gold column over the case with a slowly turning marker on top.
    const column = glowBox(prop.object, 0.06, 5, 0.06, 0, height + 2.9, 0, palette.beacon, 2.2);
    const marker = glowBox(prop.object, 0.22, 0.22, 0.22, 0, height + 0.4, 0, palette.beacon, 2.2);
    marker.rotation.set(Math.PI / 4, 0, Math.PI / 4);
    let state = 'live';
    let progress = 0;
    prop.setState = (next, t = 0) => {
      state = next;
      progress = t;
      body.visible = next !== 'taken';
      column.visible = marker.visible = next !== 'taken';
    };
    prop.update = (dt) => {
      if (state === 'taken') return;
      marker.rotation.y += dt * (state === 'grabbing' ? 6 : 1.2);
      // Slow pulse while live; the column thickens as the grab completes. It also widens with
      // distance, so it reads from across the block without flaring up close.
      const pulse = state === 'grabbing' ? 1 + progress * 2 : 1 + 0.3 * Math.sin(G.time.t * 2.2);
      const far = clamp(G.camera.position.distanceTo(prop.object.position) / 10, 0.35, 3);
      column.scale.set(pulse * far, 1, pulse * far);
    };
  }

  function ipxTruck(prop, [length, height, width]) {
    // Livery on both sides and hazard lights at the rear (the nose points to +X).
    const livery = G.mats.sign({ text: 'IPX', sub: 'IPX.EXCHANGE', w: length * 0.5, h: height * 0.4, style: 'plate', lit: false });
    for (const side of [1, -1]) {
      // The livery's texture spans its quad once: UVs 0 … 1, not metres.
      const facing = side > 0 ? '+z' : '-z';
      const quad = new THREE.Mesh(planeGeo(livery.w, livery.h, { facing, uvScale: [1 / livery.w, 1 / livery.h] }), livery.material);
      quad.position.set(-length * 0.1, height * 0.6, side * (width / 2 + 0.01));
      prop.object.add(quad);
    }
    const hazards = [-1, 1].map((side) =>
      glowBox(prop.object, 0.06, 0.16, 0.3, -length / 2 - 0.03, 0.9, side * (width / 2 - 0.25), palette.hazard, 5),
    );
    prop.state = 'idle';
    prop.setState = (next) => {
      prop.state = next;
    };
    prop.update = () => {
      hazards[0].visible = hazards[1].visible = G.time.t % 1 < 0.5;
    };
  }

  function explosive(prop) {
    prop.setState = (next) => {
      prop.object.visible = next !== 'gone';
    };
  }

  const STATEFUL = {
    master_case: masterCase,
    ipx_truck: ipxTruck,
    propane_tank: explosive,
    welding_rack: explosive,
  };

  // ---- factory ------------------------------------------------------------------------------

  function build(name, opts = {}) {
    let def = PROPS[name];
    if (!def) {
      if (!warned.has(name)) {
        warned.add(name);
        console.warn(`[props] unknown prop '${name}': add it to src/config/catalog.js`);
      }
      def = { size: [1, 1, 1], surface: 'metal' };
    }
    const size = def.size.slice();
    const [length, height, width] = size;

    const object = new THREE.Group();
    object.name = name;
    const body = new THREE.Mesh(geometryFor(name, size), materialFor(name, def, opts));
    body.castShadow = height > 0.3;
    body.receiveShadow = true;
    object.add(body);

    const prop = {
      object,
      colliders: def.noCollide
        ? []
        : [{ min: [-length / 2, 0, -width / 2], max: [length / 2, height, width / 2], surface: def.surface }],
      size,
      surface: def.surface,
    };

    const lamp = LAMPS[name];
    if (lamp) {
      const y = height - lamp.drop;
      if (opts.lit !== false && opts.on !== false) glowBox(object, 0.5, 0.14, 0.5, 0, y, 0, lamp.color, 4);
      prop.lights = [{ pos: [0, y - 0.2, 0], color: lamp.color, intensity: lamp.intensity, range: lamp.range, kind: lamp.kind }];
    }

    if (STATEFUL[name]) STATEFUL[name](prop, size);
    if (def.dynamic || prop.update || prop.setState) {
      prop.dynamic = true;
      object.userData.noMerge = true;
    }
    return prop;
  }

  return {
    build,
    has: (name) => name in PROPS,
    names: () => Object.keys(PROPS),
  };
}
