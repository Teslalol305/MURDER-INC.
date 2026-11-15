// Street furniture: what stands on the avenue's kerbs. Everything with a front faces +Z.

import { BufferAttribute } from 'three';
import { palette } from '../config/look.js';
import { M, RIGGED, Soup, arc, glow, lattice, latheGeo, scaleUV, xf } from './kit.js';

const IRON = 'metal_dark';
const GALV = 'metal_galv';
const TAU = Math.PI * 2;

const GLASS = M('glass_store', { transparent: true, opacity: 0.32 });
const CHAINLINK = M('chainlink', { transparent: true, opacity: 0.4, doubleSide: true });
const SODIUM = glow(palette.sodium, 4.5);

// Sign faces a post can carry: atlas region, width, height.
const SIGN_FACES = {
  nopark: ['sign_nopark', 0.32, 0.44],
  bus: ['sign_bus', 0.32, 0.44],
  oneway: ['sign_oneway', 0.58, 0.18],
  stop: ['sign_stop', 0.52, 0.52],
};
const SIGN_KINDS = ['nopark', 'bus', 'oneway'];

// Signal timing, seconds.
const SIGNAL = { green: 14, amber: 3, red: 13, walk: 8, flash: 0.5 };

// The open hydrant's jet: muzzle speed (m/s) up and out, and how it widens. The numbers match the
// droplets atmos adds (config/look.js life.hydrant), so the two read as one stream.
const JET = { up: 1.56, out: 5.2, mouth: 0.05, spread: 0.5, steps: 9, sides: 6 };

// Height of the hydrant's outlets and how far the front one stands out: the water starts here.
const OUTLET = { y: 0.47, z: 0.17 };

function hydrantBody(b, open) {
  b.lathe('@paint', [[0, 0], [0.15, 0], [0.15, 0.04], [0.1, 0.06], [0.095, 0.55], [0.115, 0.57], [0.115, 0.6], [0.095, 0.62]], [0, 0, 0], { seg: 10 });
  b.lathe(GALV, [[0.095, 0.62], [0.07, 0.68], [0.03, 0.705], [0.03, 0.73], [0, 0.735]], [0, 0, 0], { seg: 10 });
  b.cyl(GALV, 0.022, 0.03, [0, 0.735, 0], { seg: 5 });
  for (const s of [1, -1]) {
    b.cyl('@paint', 0.045, 0.07, [s * 0.125, OUTLET.y, 0], { axis: 'x', seg: 8 });
    b.cyl(GALV, 0.052, 0.025, [s * 0.16, OUTLET.y, 0], { axis: 'x', seg: 5 });
  }
  b.cyl('@paint', 0.06, 0.07, [0, OUTLET.y, 0.125], { axis: 'z', seg: 8 });
  if (!open) b.cyl(GALV, 0.068, 0.03, [0, OUTLET.y, 0.158], { axis: 'z', seg: 5 });
  b.collide([-0.16, 0, -0.16], [0.16, 0.74, 0.16], { surface: 'metal' });
}

/** The arc of water from an open hydrant: bright at the mouth, thinning to mist where it lands. */
function jetGeo(y0, z0) {
  const g = 9.8;
  const flight = (JET.up + Math.sqrt(JET.up * JET.up + 2 * g * y0)) / g;
  const ring = (t) => {
    const y = y0 + JET.up * t - 0.5 * g * t * t;
    const r = JET.mouth + t * JET.spread;
    const pts = [];
    for (let k = 0; k < JET.sides; k++) {
      const a = (k / JET.sides) * TAU;
      pts.push([Math.cos(a) * r, Math.max(0.02, y + Math.sin(a) * r * 0.7), z0 + JET.out * t]);
    }
    return pts;
  };
  const soup = new Soup();
  for (let i = 0; i < JET.steps; i++) {
    const r0 = ring((i / JET.steps) * flight);
    const r1 = ring(((i + 1) / JET.steps) * flight);
    for (let k = 0; k < JET.sides; k++) soup.quad(r0[k], r0[(k + 1) % JET.sides], r1[(k + 1) % JET.sides], r1[k]);
  }
  const geo = soup.build(60);
  const pos = geo.getAttribute('position');
  const fade = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) {
    const f = 1 - Math.min(1, (pos.getZ(i) - z0) / (JET.out * flight));
    fade.fill(0.2 + 0.8 * f, i * 3, i * 3 + 3);
  }
  geo.setAttribute('color', new BufferAttribute(fade, 3));
  return { geo, reach: z0 + JET.out * flight };
}

function fence(b, height, o) {
  const top = height - 0.035;
  for (const x of [-1.5, 1.5]) {
    b.cyl(GALV, 0.028, height - 0.02, [x, (height - 0.02) / 2, 0], { seg: 6 });
    b.cyl(GALV, 0.028, 0.03, [x, height - 0.015, 0], { seg: 6 });
  }
  b.cyl(GALV, 0.022, 3.0, [0, top, 0], { axis: 'x', seg: 5 });
  b.cyl(GALV, 0.012, 3.0, [0, 0.07, 0], { axis: 'x', seg: 4 });
  if (height > 3) {
    b.cyl(GALV, 0.022, 3.0, [0, 2.0, 0], { axis: 'x', seg: 5 });
    b.cyl(GALV, 0.026, top, [0, top / 2, 0], { seg: 5 });
  }
  b.quad(CHAINLINK, [-1.5, 0.05, 0], [1.5, 0.05, 0], [1.5, top, 0], [-1.5, top, 0]);
  if (o.variant === 'scrim') {
    // Site scrim tied to the street side: nobody sees through it, bullets do not care.
    const y1 = Math.min(top - 0.25, 2.3);
    const scrim = M('fabric', { color: 0x1d3b2a, doubleSide: true });
    b.quad(scrim, [-1.46, 0.12, 0.034], [1.46, 0.12, 0.034], [1.46, y1, 0.034], [-1.46, y1, 0.034]);
    for (const x of [-1.4, -0.7, 0, 0.7, 1.4]) b.box(GALV, [0.02, 0.02, 0.012], [x, y1 - 0.03, 0.034]);
  }
  b.collide([-1.5, 0, -0.04], [1.5, height, 0.04], { surface: 'metal' });
}

export function registerStreet(R) {
  R.add('jersey_barrier', {
    variants: 3,
    build(b, o) {
      const outline = [[-0.3, 0], [0.3, 0], [0.3, 0.075], [0.165, 0.33], [0.085, 0.81], [-0.085, 0.81], [-0.165, 0.33], [-0.3, 0.075]];
      b.prism('concrete', outline, -1.5, 1.5, { axis: 'x', bevel: 0.02 });
      // Fork-lift slots, and on some a tag or what is left of a hazard stripe.
      for (const x of [-0.8, 0.8]) b.box('concrete_dark', [0.34, 0.07, 0.605], [x, 0.036, 0]);
      const slope = { right: [1, 0, 0], up: [0, 0.986, -0.165] };
      if (o.variantIndex === 1) b.decal('tag_c', [0.5, 0.56, 0.127], 0.8, 0.34, slope);
      if (o.variantIndex === 2) b.decal('stripes_ow', [0, 0.57, 0.125], 2.6, 0.2, slope);
      b.collide([-1.5, 0, -0.3], [1.5, 0.81, 0.3], { surface: 'concrete' });
    },
  });

  R.add('traffic_barrel', {
    build(b) {
      const orange = 'plastic_orange';
      const seg = 10;
      // The base ring has no underside (it stands on it); each band is one tapered skin, the next one
      // a hair narrower: the step between them shows without a ledge of its own.
      b.lathe('rubber', [[0.3, 0], [0.3, 0.06], [0.27, 0.08]], [0, 0, 0], { seg });
      const tiers = [[0.27, 0.08, 0.3, orange], [0.255, 0.3, 0.5, 'paint_white'], [0.24, 0.5, 0.68, orange], [0.225, 0.68, 0.84, 'paint_white']];
      for (const [r, y0, y1, slot] of tiers) b.lathe(slot, [[r, y0], [r - 0.006, y1]], [0, 0, 0], { seg });
      b.lathe(orange, [[0.205, 0.84], [0.2, 0.93], [0.15, 0.96], [0, 0.96]], [0, 0, 0], { seg });
      b.box(orange, [0.26, 0.04, 0.05], [0, 0.98, 0]);
      b.collide([-0.28, 0, -0.28], [0.28, 0.98, 0.28], { surface: 'rubber' });
    },
  });

  R.add('traffic_cone', {
    build(b) {
      b.box('plastic_orange', [0.36, 0.03, 0.36], [0, 0.015, 0]);
      b.lathe('plastic_orange', [[0.13, 0.03], [0.095, 0.3]], [0, 0, 0], { seg: 10 });
      b.lathe('paint_white', [[0.095, 0.3], [0.07, 0.48]], [0, 0, 0], { seg: 10 });
      b.lathe('plastic_orange', [[0.07, 0.48], [0.036, 0.69], [0, 0.7]], [0, 0, 0], { seg: 10 });
    },
  });

  R.add('barricade', {
    build(b) {
      // A sawhorse: two A-frames, two striped boards, an amber flasher on one end.
      for (const x of [-1.02, 1.02]) {
        for (const s of [1, -1]) b.bar('paint_white', [x, 0, s * 0.23], [x, 1.0, s * 0.03], 0.07, 0.045);
        b.box('paint_white', [0.045, 0.06, 0.3], [x, 0.4, 0]);
      }
      for (const [y, h] of [[0.9, 0.2], [0.5, 0.14]]) {
        b.box('paint_white', [2.4, h, 0.03], [0, y, 0]);
        b.decal('stripes_ow', [0, y, 0.015], 2.4, h, '+z', { lift: 0.002 });
        b.decal('stripes_ow', [0, y, -0.015], 2.4, h, '-z', { lift: 0.002 });
      }
      b.box(IRON, [0.1, 0.05, 0.08], [0.95, 1.025, 0]);
      b.cyl(glow(palette.hazard, 1.6), 0.045, 0.05, [0.95, 1.075, 0], { seg: 8 });
      b.collide([-1.2, 0, -0.25], [1.2, 1.0, 0.25], { surface: 'wood' });
    },
  });

  R.add('dumpster', {
    variants: 2,
    paint: 'paint_green',
    build(b, o) {
      // A hopper with a sloping front on four casters.
      const outline = [[-0.5, 0.14], [0.42, 0.14], [0.53, 1.12], [-0.5, 1.12]];
      b.prism('@paint', outline, -0.9, 0.9, { axis: 'x', bevel: 0.02 });
      b.box('@paint', [1.86, 0.06, 1.08], [0, 1.13, 0.01]); // rim
      const tilt = { right: [1, 0, 0], up: [0, 0.994, 0.111] };
      for (const x of [-0.6, 0, 0.6]) b.box('@paint', [0.05, 0.9, 0.03], [x, 0.63, 0.49], { rot: [0.112, 0, 0] });
      b.decal('dumpster', [0.3, 0.74, 0.498], 0.5, 0.1, tilt, { lift: 0.006 });
      if (o.variantIndex === 1) b.decal('tag_a', [-0.3, 0.46, 0.468], 0.5, 0.22, tilt, { lift: 0.006 });
      for (const s of [1, -1]) {
        b.box(IRON, [0.1, 0.16, 0.66], [s * 0.9, 0.78, -0.02]); // fork pockets
        for (const z of [-0.38, 0.32]) b.cyl('rubber', 0.07, 0.05, [s * 0.74, 0.07, z], { axis: 'x', seg: 8 });
      }
      // Lids: one shut, one thrown back with a bag showing.
      b.box('plastic_dark', [0.9, 0.035, 1.08], [-0.46, 1.19, 0], { rot: [-0.06, 0, 0] });
      b.box('plastic_dark', [0.9, 0.035, 0.36], [0.46, 1.19, -0.42], { rot: [-1.15, 0, 0] });
      b.blob('trash_bag', 0.3, [0.42, 1.12, 0.12], { seed: 4, scale: [1.2, 0.55, 1], crease: 60 });
      b.collide([-0.95, 0, -0.55], [0.95, 1.3, 0.55], { surface: 'metal' });
    },
  });

  R.add('trash_can', {
    build(b) {
      // The city's wire litter basket: mesh sides you can see the liner through.
      b.add(lattice(0x8d949a), scaleUV(latheGeo([[0.23, 0.05], [0.285, 0.9]], 12), 15));
      b.lathe(GALV, [[0.275, 0.88], [0.3, 0.89], [0.3, 0.93], [0.275, 0.94]], [0, 0, 0], { crease: 20 });
      b.lathe(GALV, [[0, 0], [0.24, 0], [0.24, 0.06], [0.22, 0.06]]);
      b.lathe('trash_bag', [[0.2, 0.07], [0.255, 0.86], [0.285, 0.9], [0.3, 0.86]]);
      b.blob('trash_bag', 0.24, [0, 0.83, 0], { seed: 2, scale: [1, 0.4, 1], crease: 60 });
      b.box('@vc', [0.13, 0.1, 0.09], [0.06, 0.89, 0.05], { rot: [0.3, 0.5, 0.2], color: 0xd8d2c0 });
      b.cyl('@vc', 0.035, 0.11, [-0.08, 0.89, -0.04], { rot: [0.6, 0, 0.4], seg: 6, color: 0xc2261e });
      b.collide([-0.29, 0, -0.29], [0.29, 0.95, 0.29], { surface: 'metal' });
    },
  });

  R.add('trash_bags', {
    variants: 3,
    build(b) {
      const rng = b.rng;
      const spots = [[-0.36, 0.2], [0.14, 0.18], [0.38, -0.18], [-0.12, -0.2], [-0.02, 0.02]];
      spots.forEach(([x, z], i) => {
        const r = 0.24 + rng.range(0, 0.05);
        const y = i === 4 ? 0.4 : r * 0.9; // the last one sits on the others
        const slot = i === 1 ? M('trash_bag', { color: 0xc9c9c2 }) : 'trash_bag';
        const bx = x + rng.range(-0.04, 0.04);
        const bz = z + rng.range(-0.03, 0.03);
        b.blob(slot, r, [bx, y, bz], { seed: rng.int(0, 99), rough: 0.3, scale: [1.1, 0.8, 1], crease: 62, rot: [0, rng.range(0, 6), 0] });
        // The tied neck.
        b.lathe(slot, [[0.05, 0], [0.025, 0.04], [0.055, 0.075]], [bx, y + r * 0.6, bz], { seg: 4, rot: [rng.range(-0.3, 0.3), 0, rng.range(-0.3, 0.3)] });
      });
      b.collide([-0.66, 0, -0.48], [0.68, 0.62, 0.46], { surface: 'cloth' });
    },
  });

  R.add('mailbox', {
    variants: 2,
    paint: 'paint_blue',
    build(b, o) {
      // A collection box: barrel top, four feet, a pull-down door.
      const outline = [[-0.24, 0.26], [0.24, 0.26], ...arc(0, 0.96, 0.24, 0, Math.PI, 7)];
      b.prism('@paint', outline, -0.26, 0.26, { axis: 'x', bevel: 0.015, crease: 35 });
      for (const sx of [1, -1]) for (const sz of [1, -1]) b.box('@paint', [0.05, 0.27, 0.05], [sx * 0.2, 0.135, sz * 0.18]);
      b.box('@paint', [0.42, 0.16, 0.035], [0, 1.0, 0.225], { rot: [-0.35, 0, 0] });
      b.box('chrome', [0.2, 0.025, 0.03], [0, 1.03, 0.25]);
      b.decal('mail', [0, 0.66, 0.24], 0.36, 0.27, '+z');
      if (o.variantIndex === 1) b.decal('tag_a', [0.26, 0.7, 0], 0.4, 0.18, '+x', { lift: 0.004 });
      b.collide([-0.27, 0, -0.25], [0.27, 1.2, 0.25], { surface: 'metal' });
    },
  });

  R.add('newspaper_box', {
    paint: 'paint_red',
    colors: [0xb3261e, 0x1f4f9a, 0xe9b21a, 0x1f5a3a, 0xd9d7d0],
    build(b) {
      b.box(IRON, [0.36, 0.03, 0.34], [0, 0.015, 0]);
      b.box(IRON, [0.12, 0.42, 0.12], [0, 0.24, 0]);
      b.box('@paint', [0.46, 0.6, 0.4], [0, 0.75, -0.01]);
      b.box('@paint', [0.48, 0.03, 0.42], [0, 1.065, -0.01]);
      b.decal('news', [0, 0.8, 0.19], 0.33, 0.41, '+z');
      b.box(GLASS, [0.36, 0.44, 0.008], [0, 0.8, 0.202]);
      b.box(IRON, [0.1, 0.11, 0.05], [0.15, 0.56, 0.195]);
      b.box('chrome', [0.3, 0.02, 0.022], [0, 1.045, 0.205]);
      b.collide([-0.24, 0, -0.21], [0.24, 1.08, 0.21], { surface: 'metal' });
    },
  });

  R.add('hydrant', {
    paint: 'paint_red',
    build(b) {
      hydrantBody(b, false);
    },
  });

  R.add('hydrant_open', {
    paint: 'paint_red',
    key: (o) => (o.spray === false ? 'dry' : ''),
    build(b, o) {
      hydrantBody(b, true);
      // The cap someone took off, the dark mouth, the street it has soaked.
      b.cyl(GALV, 0.068, 0.03, [0.2, 0.016, 0.12], { seg: 5 });
      b.ring('plastic_dark', 0, 0.05, [0, OUTLET.y, 0.161], { rot: [Math.PI / 2, 0, 0], seg: 8 });
      const jet = jetGeo(OUTLET.y, OUTLET.z);
      b.ring('asphalt_wet', 0, 0.9, [0, 0.012, 0.3], { seg: 14 });
      b.ring('asphalt_wet', 0, 1.3, [0, 0.011, jet.reach - 0.1], { seg: 14 });
      b.anchor('spray', [0, OUTLET.y, OUTLET.z], [0, 0.29, 0.96]);
      if (o.spray !== false) {
        b.node('jet');
        b.add(RIGGED, jet.geo);
        b.root();
      }
    },
    rig(prop, o, env) {
      // atmos looks for this on the object to aim its droplets (local-space nozzle direction).
      prop.object.userData.spray = { x: 0, y: 0.29, z: 0.96 };
      const jet = prop.nodes.jet;
      if (!jet) return;
      const material = env.materials.additive(0xcfe4ff, 0.3);
      const mesh = jet.children[0];
      mesh.material = material;
      mesh.castShadow = false;
      mesh.receiveShadow = false;
      let clock = 0;
      prop.update = (dt) => {
        clock += dt;
        // Pressure is never steady: the jet breathes and shivers.
        jet.scale.set(1 + 0.06 * Math.sin(clock * 23), 1 + 0.04 * Math.sin(clock * 17 + 1), 1 + 0.03 * Math.sin(clock * 5));
        material.opacity = 0.26 + 0.08 * Math.sin(clock * 31) * Math.sin(clock * 7);
      };
    },
  });

  R.add('phone_booth', {
    variants: 2,
    key: (o) => (o.lit === false ? 'off' : ''),
    build(b, o) {
      const lit = o.lit !== false;
      // A kerbside pay phone: steel back, two half-glazed wings, a lit head.
      b.box(GALV, [0.86, 1.94, 0.04], [0, 0.99, -0.41]);
      b.box(IRON, [0.9, 0.04, 0.9], [0, 0.02, 0]);
      for (const s of [1, -1]) {
        b.box(GALV, [0.035, 0.9, 0.72], [s * 0.43, 0.47, -0.05]);
        b.box(GLASS, [0.012, 1.02, 0.7], [s * 0.43, 1.45, -0.05]);
        b.box(GALV, [0.04, 1.94, 0.04], [s * 0.43, 0.99, 0.31]);
      }
      b.box(IRON, [0.9, 0.22, 0.9], [0, 2.09, 0]);
      if (lit) {
        b.decal('phone_sign', [0, 2.09, 0.45], 0.8, 0.2, '+z', { lit: true, lift: 0.002 });
        for (const s of [1, -1]) b.decal('phone_sign', [s * 0.45, 2.09, 0], 0.8, 0.2, s > 0 ? '+x' : '-x', { lit: true, lift: 0.002 });
        b.box(glow(0xe9f1ff, 1.4), [0.6, 0.015, 0.5], [0, 1.975, 0]);
        b.lamp([0, 1.9, 0.1], { color: 0xdfe8ff, intensity: 7, range: 4.5, kind: 'window' });
      }
      // The phone itself, a shelf, the cord.
      b.box(IRON, [0.36, 0.52, 0.13], [0, 1.3, -0.33]);
      b.decal('phone_unit', [0.03, 1.3, -0.265], 0.26, 0.33, '+z', { lift: 0.002 });
      b.box('plastic_dark', [0.06, 0.24, 0.06], [-0.13, 1.34, -0.24]);
      b.tube('plastic_dark', [[-0.13, 1.22, -0.24], [-0.16, 1.02, -0.2], [-0.06, 0.98, -0.26], [0.0, 1.06, -0.3]], 0.008, { radial: 4 });
      b.box(GALV, [0.6, 0.03, 0.28], [0, 0.98, -0.26]);
      b.decal('stickers', [-0.412, 1.2, 0.1], 0.3, 0.4, '+x', { lift: 0.002 });
      if (o.variantIndex === 1) b.decal('tag_b', [0.4475, 0.52, -0.05], 0.56, 0.24, '+x', { lift: 0.002 });
      b.collide([-0.45, 0, -0.45], [0.45, 2.2, 0.36], { surface: 'metal' });
    },
  });

  R.add('bus_shelter', {
    key: (o) => (o.lit === false ? 'off' : ''),
    build(b, o) {
      const lit = o.lit !== false;
      const post = (x, z) => b.box(IRON, [0.07, 2.4, 0.07], [x, 1.2, z]);
      for (const x of [-1.72, 0, 1.72]) post(x, -0.66);
      post(1.72, 0.62);
      // Roof: a shallow tray with a light strip under it.
      b.box(IRON, [3.6, 0.07, 1.5], [0, 2.44, 0]);
      b.box(IRON, [3.6, 0.1, 0.04], [0, 2.4, 0.73]);
      // Glass back in two panes between rails, a half pane at the east end.
      for (const x of [-0.86, 0.86]) b.box(GLASS, [1.64, 1.86, 0.012], [x, 1.3, -0.66]);
      b.box(IRON, [3.5, 0.05, 0.05], [0, 0.36, -0.66]);
      b.box(IRON, [3.5, 0.05, 0.05], [0, 2.26, -0.66]);
      b.box(GLASS, [0.012, 1.86, 0.9], [1.72, 1.3, -0.16]);
      // The ad panel closes the west end: an IPX one-sheet, lit from inside.
      b.box(IRON, [0.14, 1.96, 1.26], [-1.72, 1.2, 0]);
      for (const s of [1, -1]) b.decal('ipx_ad', [-1.72 + s * 0.07, 1.2, 0], 1.14, 1.72, s > 0 ? '+x' : '-x', { lit, lift: 0.003 });
      // Bench, and the stop flag on the open corner.
      b.box('wood', [1.9, 0.05, 0.36], [0.5, 0.47, -0.42]);
      for (const x of [-0.3, 1.3]) b.box(IRON, [0.05, 0.45, 0.3], [x, 0.225, -0.42]);
      b.box(GALV, [0.3, 0.4, 0.016], [1.62, 2.05, 0.662]);
      b.decal('sign_bus', [1.62, 2.05, 0.67], 0.26, 0.36, '+z', { lift: 0.003 });
      if (lit) {
        b.box(glow(0xe9f1ff, 2.2), [2.6, 0.02, 0.1], [0.3, 2.395, 0.1]);
        b.lamp([-1.4, 1.3, 0.2], { color: 0xdfe8ff, intensity: 12, range: 6, kind: 'neon' });
        b.lamp([0.4, 2.2, 0.1], { color: 0xdfe8ff, intensity: 10, range: 5, kind: 'window' });
      }
      b.collide([-1.76, 0, -0.69], [1.76, 2.3, -0.63], { surface: 'glass' });
      b.collide([-1.8, 0, -0.63], [-1.64, 2.2, 0.63], { surface: 'metal' });
      b.collide([-0.45, 0, -0.6], [1.45, 0.5, -0.24], { surface: 'wood' });
      b.collide([-1.8, 2.38, -0.75], [1.8, 2.48, 0.75], { surface: 'metal', noNav: true });
    },
  });

  R.add('street_lamp', {
    variants: 2,
    key: (o) => (o.on === false || o.lit === false ? 'off' : ''),
    build(b, o) {
      const on = !(o.on === false || o.lit === false);
      // Octagonal steel pole on a transformer base, a long arm, a cobra head over the road.
      b.lathe(GALV, [[0.17, 0], [0.17, 0.04], [0.13, 0.08], [0.12, 0.62], [0.09, 0.7], [0.055, 7.2], [0, 7.25]], [0, 0, 0], { seg: 8 });
      b.box(IRON, [0.14, 0.2, 0.012], [0, 0.36, 0.125]);
      b.tube(GALV, [[0, 7.1, 0], [0, 7.5, 0.5], [0, 7.74, 1.2], [0, 7.8, 1.86]], 0.035, { radial: 6, segments: 8 });
      b.stick(GALV, [0, 6.6, 0.05], [0, 7.5, 0.56], 0.016, { seg: 4 }); // brace
      // Head: a flat teardrop with the lens underneath.
      const head = latheGeo([[0, -0.36], [0.1, -0.33], [0.15, -0.1], [0.13, 0.22], [0.05, 0.36], [0, 0.37]], 8);
      b.add(GALV, head, xf(0, 7.8, 2.16, Math.PI / 2, 0, 0, 1, 1, 0.55));
      b.box(on ? SODIUM : 'glass_dark', [0.2, 0.03, 0.4], [0, 7.7, 2.16]);
      if (o.variantIndex === 1) b.decal('stickers', [0, 1.5, 0.094], 0.16, 0.22, '+z', { lift: 0.004 });
      if (on) b.lamp([0, 7.6, 2.16], { color: palette.sodium, intensity: 90, range: 20, kind: 'street', dir: [0, -1, 0] });
      b.collide([-0.13, 0, -0.13], [0.13, 7.3, 0.13], { surface: 'metal' });
    },
  });

  R.add('traffic_light', {
    build(b) {
      // Pole, a mast arm reaching over the road (+Z), two heads back to back that face up and down it.
      b.lathe(IRON, [[0.16, 0], [0.16, 0.05], [0.11, 0.1], [0.07, 5.5], [0, 5.55]], [0, 0, 0], { seg: 8 });
      b.tube(IRON, [[0, 5.2, 0], [0, 5.62, 0.9], [0, 5.72, 2.0], [0, 5.72, 3.25]], 0.04, { radial: 6, segments: 8 });
      b.stick(IRON, [0, 4.6, 0.05], [0, 5.6, 1.0], 0.016, { seg: 4 });
      const zHead = 3.05;
      const yHead = 5.18;
      b.box('paint_yellow', [0.34, 1.02, 0.34], [0, yHead, zHead]);
      b.stick(IRON, [0, 5.72, zHead], [0, yHead + 0.5, zHead], 0.02, { seg: 5 });
      const lamps = [['red', 0xff2a1a, 0.33], ['amber', 0xffb020, 0], ['green', 0x30ff8a, -0.33]];
      for (const [, color, dy] of lamps) {
        for (const s of [1, -1]) {
          // An unlit lens and a visor on both faces.
          b.ring(glow(color, 0.1), 0, 0.1, [s * 0.172, yHead + dy, zHead], { rot: [0, 0, (-s * Math.PI) / 2], seg: 10 });
          b.box(IRON, [0.14, 0.012, 0.24], [s * 0.24, yHead + dy + 0.11, zHead]);
        }
      }
      // Pedestrian head on the pole, facing across the road.
      b.box(IRON, [0.36, 0.36, 0.14], [0, 2.7, 0.14]);
      b.box(IRON, [0.4, 0.012, 0.1], [0, 2.89, 0.25]);

      for (const [name, color, dy] of lamps) {
        b.node(name);
        for (const s of [1, -1]) b.ring(glow(color, 4.5), 0, 0.1, [s * 0.174, yHead + dy, zHead], { rot: [0, 0, (-s * Math.PI) / 2], seg: 10 });
      }
      b.node('stop');
      b.decal('ped_stop', [0, 2.7, 0.21], 0.3, 0.3, '+z', { lit: true, lift: 0.002 });
      b.node('walk');
      b.decal('ped_walk', [0, 2.7, 0.21], 0.3, 0.3, '+z', { lit: true, lift: 0.002 });
      b.root();
      b.collide([-0.14, 0, -0.14], [0.14, 5.55, 0.14], { surface: 'metal' });
    },
    rig(prop, o) {
      const { red, amber, green, stop, walk } = prop.nodes;
      const cycle = SIGNAL.green + SIGNAL.amber + SIGNAL.red;
      let clock = (o.seed * 7.3) % cycle; // lights along the avenue should not all change together
      const apply = () => {
        const t = clock % cycle;
        const sinceRed = t - SIGNAL.green - SIGNAL.amber;
        green.visible = t < SIGNAL.green;
        amber.visible = t >= SIGNAL.green && sinceRed < 0;
        red.visible = sinceRed >= 0;
        // Walk while the avenue is stopped, then a flashing hand, otherwise a steady one.
        const walking = sinceRed >= 0 && sinceRed < SIGNAL.walk;
        walk.visible = walking;
        stop.visible = sinceRed >= SIGNAL.walk ? Math.floor(sinceRed / SIGNAL.flash) % 2 === 0 : !walking;
      };
      apply();
      prop.update = (dt) => {
        clock += dt;
        apply();
      };
    },
  });

  R.add('parking_meter', {
    build(b) {
      b.cyl(GALV, 0.028, 1.04, [0, 0.52, 0], { seg: 6 });
      b.cyl(GALV, 0.05, 0.03, [0, 0.015, 0], { seg: 6 });
      b.lathe(IRON, [[0, 1.02], [0.06, 1.03], [0.09, 1.1], [0.09, 1.2], [0.06, 1.28], [0, 1.3]], [0, 0, 0], { seg: 8, rot: [0, Math.PI / 8, 0] });
      b.decal('meter', [0, 1.165, 0.084], 0.1, 0.15, '+z', { lift: 0.003 });
      b.decal('meter', [0, 1.165, -0.084], 0.1, 0.15, '-z', { lift: 0.003 });
      b.collide([-0.09, 0, -0.09], [0.09, 1.3, 0.09], { surface: 'metal' });
    },
  });

  R.add('bench', {
    build(b) {
      // Cast-iron ends, timber slats.
      for (const x of [-0.84, 0, 0.84]) {
        b.box(IRON, [0.05, 0.43, 0.05], [x, 0.215, 0.2]);
        b.bar(IRON, [x, 0, -0.2], [x, 0.82, -0.26], 0.05);
        b.box(IRON, [0.05, 0.045, 0.44], [x, 0.415, 0]);
        if (x !== 0) {
          b.box(IRON, [0.05, 0.035, 0.5], [x, 0.63, 0.01]);
          b.box(IRON, [0.05, 0.2, 0.04], [x, 0.53, 0.23]);
        }
      }
      for (const z of [-0.13, -0.02, 0.09, 0.2]) b.box('wood', [1.76, 0.035, 0.09], [0, 0.455, z]);
      for (const [y, z] of [[0.58, -0.21], [0.69, -0.22], [0.795, -0.23]]) b.box('wood', [1.76, 0.085, 0.03], [0, y, z], { rot: [-0.08, 0, 0] });
      b.collide([-0.88, 0, -0.26], [0.88, 0.47, 0.26], { surface: 'wood' });
      b.collide([-0.88, 0.47, -0.3], [0.88, 0.85, -0.18], { surface: 'wood' });
    },
  });

  R.add('planter', {
    variants: 2,
    build(b) {
      // A tapered concrete tub, soil, a low hedge.
      const soup = new Soup();
      const lo = 0.5;
      const hi = 0.59;
      const h = 0.56;
      const corners = [[1, 1], [-1, 1], [-1, -1], [1, -1]];
      for (let i = 0; i < 4; i++) {
        const [ax, az] = corners[i];
        const [bx, bz] = corners[(i + 1) % 4];
        soup.quadFacing([ax + bx, 0, az + bz], [ax * lo, 0, az * lo], [bx * lo, 0, bz * lo], [bx * hi, h, bz * hi], [ax * hi, h, az * hi]);
      }
      b.add('concrete', soup.build(0));
      b.box('concrete', [1.2, 0.07, 1.2], [0, h + 0.005, 0]);
      b.box('dirt', [1.06, 0.02, 1.06], [0, h + 0.045, 0]);
      const rng = b.rng;
      for (const [x, z] of [[-0.25, -0.2], [0.26, -0.18], [0.02, 0.24], [-0.3, 0.26], [0.3, 0.25]]) {
        const r = 0.2 + rng.range(0, 0.04);
        b.blob('leaves', r, [x, 0.8 - r * 0.86, z], { seed: rng.int(0, 99), rough: 0.5, scale: [1.15, 0.8, 1.15], detail: 0 });
      }
      b.collide([-0.6, 0, -0.6], [0.6, 0.8, 0.6], { surface: 'concrete' });
    },
  });

  R.add('tree', {
    variants: 3,
    build(b) {
      const rng = b.rng;
      // Trunk with a lean, three boughs, a crown of leaf masses.
      const lean = [rng.range(-0.12, 0.12), rng.range(-0.1, 0.1)];
      const mid = [lean[0] * 0.4, 1.4, lean[1] * 0.4];
      const fork = [lean[0], 2.7, lean[1]];
      b.stick('wood', [0, 0, 0], mid, 0.13, { seg: 7, rTop: 0.105 });
      b.stick('wood', mid, fork, 0.105, { seg: 7, rTop: 0.085 });
      const crowns = [[fork[0], 4.9, fork[2], 1.3]];
      for (let i = 0; i < 3; i++) {
        const a = (i / 3) * TAU + rng.range(-0.4, 0.4);
        const reach = rng.range(0.8, 1.15);
        const tip = [fork[0] + Math.cos(a) * reach, 3.8 + rng.range(0, 0.4), fork[2] + Math.sin(a) * reach];
        b.stick('wood', fork, tip, 0.07, { seg: 5, rTop: 0.03 });
        crowns.push([tip[0] * 1.15, tip[1] + 0.3, tip[2] * 1.15, rng.range(1.15, 1.4)]);
      }
      for (const [x, y, z, r] of crowns) {
        b.blob('leaves', r, [x, Math.min(y, 5.98 - r * 0.92), z], { seed: rng.int(0, 99), rough: 0.5, scale: [1.05, 0.8, 1.05] });
      }
      // The pit and its guard.
      b.box('dirt', [0.58, 0.02, 0.58], [0, 0.01, 0]);
      for (const sx of [1, -1]) for (const sz of [1, -1]) b.box(IRON, [0.03, 0.55, 0.03], [sx * 0.28, 0.275, sz * 0.28]);
      for (const y of [0.53, 0.28]) {
        for (const s of [1, -1]) {
          b.box(IRON, [0.59, 0.025, 0.02], [0, y, s * 0.28]);
          b.box(IRON, [0.02, 0.025, 0.59], [s * 0.28, y, 0]);
        }
      }
      b.collide([-0.3, 0, -0.3], [0.3, 0.55, 0.3], { surface: 'metal' });
      b.collide([-0.14, 0.55, -0.14], [0.14, 3.0, 0.14], { surface: 'wood' });
    },
  });

  R.add('bollard', {
    paint: 'paint_yellow',
    build(b) {
      b.lathe('@paint', [[0, 0], [0.1, 0], [0.1, 0.025], [0.085, 0.035], [0.085, 0.7]], [0, 0, 0], { seg: 8 });
      b.lathe('paint_black', [[0.087, 0.7], [0.087, 0.8]], [0, 0, 0], { seg: 8 });
      b.lathe('@paint', [[0.085, 0.8], [0.085, 0.93], [0.06, 0.99], [0, 1.0]], [0, 0, 0], { seg: 8 });
      b.collide([-0.09, 0, -0.09], [0.09, 1.0, 0.09], { surface: 'metal' });
    },
  });

  R.add('sign_post', {
    variants: 3,
    key: (o) => (o.variant ? `${o.variant}:${o.text || ''}` : ''),
    build(b, o, env) {
      b.box(GALV, [0.05, 2.8, 0.025], [0, 1.4, -0.02]);
      if (o.variant === 'street') {
        // A street-name blade from the material library's sign painter.
        const sign = env.materials.sign({ text: o.text || 'JAMAICA AV', w: 0.58, h: 0.15, style: 'street', lit: false });
        const slot = b.own(sign.material);
        const uv = sign.uv || [0, 0, 1, 1]; // the library's atlas rect (the stub has none)
        const y = 2.7;
        b.box('paint_green', [0.6, 0.17, 0.012], [0, y, 0]);
        b.quad(slot, [-0.29, y - 0.075, 0.008], [0.29, y - 0.075, 0.008], [0.29, y + 0.075, 0.008], [-0.29, y + 0.075, 0.008], { uv });
        b.quad(slot, [0.29, y - 0.075, -0.008], [-0.29, y - 0.075, -0.008], [-0.29, y + 0.075, -0.008], [0.29, y + 0.075, -0.008], { uv });
      } else {
        const kind = SIGN_FACES[o.variant] ? o.variant : SIGN_KINDS[o.variantIndex];
        const [region, w, h] = SIGN_FACES[kind];
        const y = 2.78 - h / 2;
        if (kind === 'stop') b.prism(GALV, arc(0, y, 0.285, Math.PI / 8, Math.PI / 8 + TAU, 8).slice(0, 8), -0.006, 0.006);
        else b.box(GALV, [w + 0.02, h + 0.02, 0.012], [0, y, 0]);
        b.decal(region, [0, y, 0.006], w, h, '+z', { lift: 0.003 });
      }
      b.collide([-0.04, 0, -0.04], [0.04, 2.8, 0.04], { surface: 'metal' });
    },
  });

  const fenceKey = (o) => (o.variant === 'scrim' ? 'scrim' : '');
  R.add('fence_panel', { key: fenceKey, build: (b, o) => fence(b, 2.4, o) });
  R.add('fence_tall', { key: fenceKey, build: (b, o) => fence(b, 4.0, o) });

  R.add('manhole', {
    build(b) {
      b.ring('concrete_dark', 0.4, 0.45, [0, 0.011, 0], { seg: 16 });
      b.cyl(IRON, 0.405, 0.016, [0, 0.008, 0], { seg: 16 });
      b.ring(IRON, 0.26, 0.3, [0, 0.0195, 0], { seg: 16 });
      b.ring(IRON, 0.1, 0.14, [0, 0.0195, 0], { seg: 12 });
      for (let i = 0; i < 6; i++) {
        const a = (i / 6) * TAU;
        b.box(IRON, [0.1, 0.004, 0.03], [Math.cos(a) * 0.2, 0.018, Math.sin(a) * 0.2], { rot: [0, -a, 0] });
        b.box(IRON, [0.08, 0.004, 0.03], [Math.cos(a + 0.5) * 0.35, 0.018, Math.sin(a + 0.5) * 0.35], { rot: [0, -a - 0.5, 0] });
      }
      b.anchor('steam', [0, 0.02, 0], [0, 1, 0]);
    },
  });
}
