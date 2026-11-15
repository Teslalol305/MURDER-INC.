// Loose cover and clutter: what the block leaves lying around, most of it waist high.

import { M, Soup, glow, lattice, latheGeo, roundBoxGeo, scaleUV, xf } from './kit.js';

const IRON = 'metal_dark';
const GALV = 'metal_galv';
const TAU = Math.PI * 2;

const CRATE_COLORS = [0x1f4f9a, 0xb3261e, 0x202326, 0x1f5a3a];
const DRUM_COLORS = [0x1f4f9a, 0x202326, 0x2f5a3a, 0x6b4a2e, 0x8d949a];
const POTTY_COLORS = [0x1f4f9a, 0x2f6b4f, 0x8d949a];
const SANDBAG = M('dirt', { color: 0x8f7f5f });
const MATTRESS = M('fabric', { color: 0x8a8474 });
const WORK_LIGHT = 0xfff1d0;

/** One milk crate: lattice sides and floor, a solid rim. Origin at the centre of its base. */
function milkCrate(b, m, color) {
  const s = 0.165; // half the footprint
  const h = 0.28;
  const cells = 26; // lattice cells per metre
  const soup = new Soup();
  const corners = [[s, s], [-s, s], [-s, -s], [s, -s]];
  for (let i = 0; i < 4; i++) {
    const [ax, az] = corners[i];
    const [bx, bz] = corners[(i + 1) % 4];
    soup.quad([ax, 0, az], [bx, 0, bz], [bx, h, bz], [ax, h, az]);
  }
  soup.quad([-s, 0.004, s], [s, 0.004, s], [s, 0.004, -s], [-s, 0.004, -s]);
  b.add(lattice(color), scaleUV(soup.build(0), cells), m);
  // Rim and base band: the outside and the top of a 14 mm frame (the inside is behind the lattice).
  for (const [y, t] of [[h - 0.02, 0.04], [0.02, 0.04]]) b.add('@vc', crateBand(s, y, t), m, color);
}

/** The band round a crate at height y (t tall), half-footprint s: four outer faces and a top ring. */
function crateBand(s, y, t) {
  const soup = new Soup();
  const o = s + 0.007;
  const i = s - 0.007;
  const y0 = y - t / 2;
  const y1 = y + t / 2;
  for (const [nx, nz] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
    // u runs along the side, r out from the centre
    const P = (u, yy, r) => (nz !== 0 ? [u, yy, nz * r] : [nx * r, yy, u]);
    soup.quadFacing([nx, 0, nz], P(-o, y0, o), P(o, y0, o), P(o, y1, o), P(-o, y1, o));
    soup.quadFacing([0, 1, 0], P(-o, y1, o), P(o, y1, o), P(i, y1, i), P(-i, y1, i));
  }
  return soup.build(0);
}

/** One pallet with its top at y + 0.144. `full` adds the bottom boards and every deck board. */
function pallet(b, m, full) {
  b.push(m);
  for (const z of [-0.45, 0, 0.45]) b.box('wood', [1.2, 0.09, 0.09], [0, 0.067, z]);
  if (full) {
    for (let i = 0; i < 7; i++) b.box('plywood', [0.1, 0.022, 1.0], [-0.55 + i * 0.1833, 0.133, 0]);
    for (const x of [-0.55, 0, 0.55]) b.box('plywood', [0.1, 0.022, 1.0], [x, 0.011, 0]);
  } else {
    for (let i = 0; i < 4; i++) b.box('plywood', [0.24, 0.022, 1.0], [-0.48 + i * 0.32, 0.133, 0]);
  }
  b.pop();
}

/** A tyre lying flat, its underside at y = 0. */
function tyreFlat(b, m, r = 0.385, h = 0.245) {
  // Five facets round the section and eight round the ring: the smoothed normals do the rounding.
  const profile = [[0.2, 0.025], [r - 0.05, 0], [r, h / 2], [r - 0.05, h], [0.2, h - 0.025], [0.2, 0.025]];
  b.add('tire', latheGeo(profile, 8, { crease: 50 }), m);
}

/** A portable stereo, 0.6 wide, its back on z = 0 of its own frame and its face toward +Z. */
export function boombox(b, m) {
  b.push(m);
  b.box('plastic_dark', [0.6, 0.28, 0.19], [0, 0.14, 0.095]);
  b.decal('boombox', [0, 0.14, 0.19], 0.58, 0.232, '+z', { lift: 0.003 });
  b.box('chrome', [0.6, 0.012, 0.2], [0, 0.283, 0.095]);
  for (const x of [-0.2, -0.12, -0.04, 0.04]) b.box(IRON, [0.05, 0.016, 0.03], [x, 0.292, 0.13]);
  b.pipe('plastic_dark', [[-0.25, 0.28, 0.09], [-0.25, 0.34, 0.09], [0.25, 0.34, 0.09], [0.25, 0.28, 0.09]], 0.012, { seg: 5 });
  b.stick('chrome', [0.27, 0.28, 0.03], [0.14, 0.35, 0.03], 0.004, { seg: 3 });
  b.pop();
}

export function registerClutter(R) {
  R.add('milk_crates', {
    variants: 3,
    build(b) {
      const rng = b.rng;
      // Three tiers on a two-by-two base, stacked the way they get thrown down.
      const tiers = [
        [[-0.168, -0.168], [0.168, -0.168], [-0.168, 0.168], [0.168, 0.168]],
        [[-0.13, -0.11], [0.14, 0.08], [-0.09, 0.14]],
        [[0.02, -0.03], [-0.11, 0.1]],
      ];
      tiers.forEach((tier, level) => {
        const count = level === 2 ? 1 + rng.int(0, 1) : tier.length;
        for (let i = 0; i < count; i++) {
          const [x, z] = tier[i];
          const yaw = level === 0 ? 0 : rng.range(-0.25, 0.25);
          milkCrate(b, xf(x, level * 0.285, z, 0, yaw, 0), rng.pick(CRATE_COLORS));
        }
      });
      b.collide([-0.34, 0, -0.34], [0.34, 0.9, 0.34], { surface: 'rubber' });
    },
  });

  R.add('pallet', {
    build(b) {
      pallet(b, xf(0, 0, 0), true);
      b.collide([-0.6, 0, -0.5], [0.6, 0.144, 0.5], { surface: 'wood' });
    },
  });

  R.add('pallet_stack', {
    variants: 2,
    build(b) {
      const rng = b.rng;
      for (let i = 0; i < 8; i++) {
        pallet(b, xf(rng.range(-0.012, 0.012), i * 0.1435, rng.range(-0.012, 0.012), 0, rng.range(-0.02, 0.02), 0), i === 7);
      }
      b.collide([-0.6, 0, -0.5], [0.6, 1.15, 0.5], { surface: 'wood' });
    },
  });

  R.add('crate_wood', {
    variants: 2,
    build(b, o) {
      // Plywood on skids, framed and braced.
      b.box('plywood', [1.04, 0.9, 0.84], [0, 0.53, 0]);
      for (const z of [-0.3, 0.3]) b.box('wood', [1.1, 0.07, 0.1], [0, 0.035, z]);
      for (const sx of [1, -1]) for (const sz of [1, -1]) b.box('wood', [0.08, 0.92, 0.08], [sx * 0.51, 0.53, sz * 0.41]);
      for (const y of [0.115, 0.955]) {
        for (const s of [1, -1]) {
          b.box('wood', [0.94, 0.08, 0.03], [0, y, s * 0.435]);
          b.box('wood', [0.03, 0.08, 0.74], [s * 0.535, y, 0]);
        }
      }
      for (const s of [1, -1]) b.bar('wood', [-0.46, 0.16, s * 0.435], [0.46, 0.91, s * 0.435], 0.07, 0.025);
      b.box('wood', [1.1, 0.03, 0.9], [0, 0.985, 0]);
      b.decal('crate_stencil', [0.05, 0.56, 0.42], 0.66, 0.44, '+z', { lift: 0.032 });
      if (o.variantIndex === 1) b.decal('vulture', [0.55, 0.55, 0], 0.5, 0.4, '+x', { lift: 0.004 });
      b.collide([-0.55, 0, -0.45], [0.55, 1.0, 0.45], { surface: 'wood' });
    },
  });

  R.add('cardboard_boxes', {
    variants: 2,
    build(b, o) {
      const tape = 0xcbb892;
      const flip = o.variantIndex === 1 ? -1 : 1;
      const boxes = [
        // [w, h, d], [x, z], yaw, base y
        [[0.52, 0.38, 0.44], [-0.2 * flip, -0.14], 0.05, 0],
        [[0.38, 0.32, 0.36], [0.26 * flip, 0.1], -0.2, 0],
        [[0.4, 0.28, 0.36], [-0.2 * flip, -0.13], -0.18, 0.38],
        [[0.28, 0.2, 0.24], [0.25 * flip, 0.1], 0.3, 0.32],
        [[0.3, 0.2, 0.26], [-0.26 * flip, 0.22], 0.12, 0],
      ];
      for (const [[w, h, d], [x, z], yaw, y] of boxes) {
        b.push(xf(x, y, z, 0, yaw, 0));
        b.box('cardboard', [w, h, d], [0, h / 2, 0]);
        b.box('@vc', [w + 0.004, 0.003, 0.05], [0, h + 0.002, 0], { color: tape });
        b.box('@vc', [0.05, h * 0.4, d + 0.004], [0, h * 0.8, 0], { color: tape });
        b.pop();
      }
      // The top one is open: two flaps up.
      b.push(xf(-0.2 * flip, 0.66, -0.13, 0, -0.18, 0));
      b.box('cardboard', [0.4, 0.012, 0.17], [0, 0.05, 0.2], { rot: [-0.7, 0, 0] });
      b.box('cardboard', [0.4, 0.012, 0.17], [0, 0.03, -0.22], { rot: [1.3, 0, 0] });
      b.pop();
      b.decal('cardboard', [-0.2 * flip + 0.01, 0.19, 0.08], 0.3, 0.3, { right: [0.9988, 0, -0.05], up: [0, 1, 0] }, { lift: 0.004 });
      b.collide([-0.5, 0, -0.4], [0.5, 0.72, 0.4], { surface: 'wood' });
    },
  });

  R.add('shopping_cart', {
    key: (o) => (o.variant === 'tipped' ? 'tipped' : ''),
    build(b, o) {
      const tipped = o.variant === 'tipped';
      // On its side the cart lies across its own footprint.
      if (tipped) b.push(xf(0, 0.275, 0.02, Math.PI / 2, 0.4, 0).multiply(xf(0, -0.5, 0)));
      const wire = lattice(0x9aa0a4);
      // Basket: wider and longer at the top, its nose toward +X.
      const lo = { x0: -0.26, x1: 0.34, z: 0.19, y: 0.5 };
      const hi = { x0: -0.36, x1: 0.44, z: 0.25, y: 0.93 };
      const soup = new Soup();
      const corner = (level, sx, sz) => [sx > 0 ? level.x1 : level.x0, level.y, sz * level.z];
      for (const [sx, sz, tx, tz] of [[1, 1, -1, 1], [-1, 1, -1, -1], [-1, -1, 1, -1], [1, -1, 1, 1]]) {
        soup.quad(corner(lo, sx, sz), corner(lo, tx, tz), corner(hi, tx, tz), corner(hi, sx, sz));
      }
      soup.quad(corner(lo, -1, 1), corner(lo, 1, 1), corner(lo, 1, -1), corner(lo, -1, -1));
      // Child seat flap and the tray underneath.
      soup.quad([-0.2, 0.52, 0.18], [-0.2, 0.52, -0.18], [-0.3, 0.9, -0.22], [-0.3, 0.9, 0.22]);
      soup.quad([-0.22, 0.2, 0.2], [0.36, 0.2, 0.2], [0.36, 0.2, -0.2], [-0.22, 0.2, -0.2]);
      b.add(wire, scaleUV(soup.build(0), 22));
      const tube = { seg: 5 };
      b.pipe(GALV, [corner(hi, -1, 1), corner(hi, 1, 1), corner(hi, 1, -1), corner(hi, -1, -1), corner(hi, -1, 1)], 0.011, tube);
      for (const s of [1, -1]) {
        // Side frame: rear wheel, up to the handle; along the bottom to the front wheel.
        b.pipe(GALV, [[-0.3, 0.1, s * 0.22], [-0.24, 0.5, s * 0.2], [-0.44, 1.0, s * 0.24]], 0.013, tube);
        b.pipe(GALV, [[-0.3, 0.12, s * 0.22], [0.4, 0.2, s * 0.17], [0.34, 0.5, s * 0.19]], 0.013, tube);
        for (const x of [-0.3, 0.4]) {
          b.cyl('rubber', 0.055, 0.03, [x, 0.055, s * (x < 0 ? 0.22 : 0.17)], { axis: 'z', seg: 8 });
          b.box(GALV, [0.03, 0.07, 0.04], [x, 0.11, s * (x < 0 ? 0.22 : 0.17)]);
        }
      }
      b.cyl(M('paint_red', { color: 0xb3261e }), 0.017, 0.5, [-0.44, 1.0, 0], { axis: 'z', seg: 6 });
      if (tipped) {
        b.pop();
        b.collide([-0.5, 0, -0.5], [0.5, 0.5, 0.5], { surface: 'metal' });
      } else {
        b.collide([-0.45, 0, -0.26], [0.45, 0.95, 0.26], { surface: 'metal' });
      }
    },
  });

  R.add('mattress', {
    variants: 2,
    build(b, o) {
      // Dumped flat, a corner riding up on whatever is under it.
      const tilt = o.variantIndex === 1 ? 0.035 : 0;
      b.push(xf(0, 0.12 + tilt * 0.4, 0, 0, 0, tilt));
      b.add(MATTRESS, roundBoxGeo(1.88, 0.2, 0.93, { round: 0.3, segments: [4, 1, 3] }));
      b.decal('ticking', [0, 0.1, 0], 1.62, 0.76, '+y', { lift: 0.004 });
      b.pop();
    },
  });

  R.add('tire_stack', {
    variants: 2,
    build(b) {
      const rng = b.rng;
      for (let i = 0; i < 4; i++) {
        tyreFlat(b, xf(i ? rng.range(-0.012, 0.012) : 0, i * 0.243, i ? rng.range(-0.012, 0.012) : 0, 0, rng.range(0, TAU), 0));
      }
      b.collide([-0.39, 0, -0.39], [0.39, 0.98, 0.39], { surface: 'rubber' });
    },
  });

  R.add('oil_drum', {
    variants: 2,
    paint: 'paint_blue',
    colors: DRUM_COLORS,
    build(b, o) {
      const r = 0.28;
      const profile = [
        [r + 0.008, 0], [r + 0.008, 0.03], [r, 0.035], // no underside: it stands on it
        [r, 0.285], [r + 0.012, 0.3], [r, 0.315],
        [r, 0.585], [r + 0.012, 0.6], [r, 0.615],
        [r, 0.865], [r + 0.008, 0.87], [r + 0.008, 0.9], [r - 0.012, 0.9], [r - 0.012, 0.872], [0, 0.872],
      ];
      b.lathe('@paint', profile, [0, 0, 0], { seg: 10 });
      b.cyl(GALV, 0.035, 0.016, [0.15, 0.88, 0.02], { seg: 6 });
      b.cyl(GALV, 0.018, 0.014, [-0.14, 0.879, -0.08], { seg: 5 });
      if (o.variantIndex === 0) b.decal('drum_label', [0, 0.45, r - 0.004], 0.19, 0.12, '+z', { lift: 0.012 });
      b.collide([-0.29, 0, -0.29], [0.29, 0.9, 0.29], { surface: 'metal' });
    },
  });

  R.add('sandbags', {
    variants: 2,
    build(b) {
      const rng = b.rng;
      const bag = (x, y, z, yaw) => {
        const m = xf(x, y + 0.165, z, rng.range(-0.025, 0.025), yaw, rng.range(-0.025, 0.025));
        b.add(SANDBAG, roundBoxGeo(0.55, 0.335, 0.59, { round: 0.3, segments: [2, 1, 2] }), m);
      };
      // Three courses, the middle one shifted half a bag so the joints break.
      for (let course = 0; course < 3; course++) {
        const shifted = course === 1;
        const n = shifted ? 3 : 4;
        for (let i = 0; i < n; i++) {
          const x = (shifted ? -0.49 : -0.715) + i * 0.477 + rng.range(-0.01, 0.01);
          bag(x, course * 0.282, rng.range(-0.01, 0.01), rng.range(-0.04, 0.04));
        }
      }
      b.collide([-1.0, 0, -0.3], [1.0, 0.9, 0.3], { surface: 'dirt' });
    },
  });

  R.add('generator', {
    paint: 'paint_yellow',
    build(b) {
      // A skid-mounted diesel set in a weather enclosure.
      for (const z of [-0.42, 0.42]) b.box(IRON, [2.2, 0.11, 0.1], [0, 0.055, z]);
      for (const x of [-0.9, 0, 0.9]) b.box(IRON, [0.1, 0.08, 0.9], [x, 0.06, 0]);
      b.box('@paint', [2.04, 1.06, 0.94], [0, 0.64, 0]);
      b.box('@paint', [2.1, 0.05, 1.0], [0, 1.195, 0]);
      // Louvres at the radiator end and along both flanks, doors with a recessed handle.
      const slat = 'plastic_dark';
      for (let i = 0; i < 6; i++) b.box(slat, [0.02, 0.07, 0.7], [1.024, 0.42 + i * 0.11, 0], { rot: [0, 0, -0.35] });
      for (const s of [1, -1]) {
        for (let i = 0; i < 5; i++) b.box(slat, [0.46, 0.06, 0.02], [0.66, 0.46 + i * 0.11, s * 0.474], { rot: [s * 0.35, 0, 0] });
        for (const x of [-0.42, 0.34]) b.box(slat, [0.012, 0.92, 0.012], [x, 0.64, s * 0.474]);
        b.box(IRON, [0.1, 0.03, 0.012], [0.22, 0.66, s * 0.476]);
      }
      b.decal('gauges', [-0.74, 0.76, 0.47], 0.34, 0.34, '+z', { lift: 0.004 });
      b.decal('gen_label', [-0.1, 0.9, 0.47], 0.42, 0.175, '+z', { lift: 0.004 });
      b.decal('gen_label', [0.1, 0.9, -0.47], 0.42, 0.175, '-z', { lift: 0.004 });
      // Exhaust with a rain cap, lifting eye, filler.
      b.cyl(IRON, 0.05, 0.13, [0.7, 1.285, 0.2], { seg: 8 });
      b.box(IRON, [0.13, 0.012, 0.12], [0.71, 1.365, 0.2], { rot: [0, 0, 0.35] });
      b.box(IRON, [0.16, 0.08, 0.03], [0, 1.26, 0]);
      b.cyl(IRON, 0.045, 0.04, [-0.8, 1.24, -0.25], { seg: 8 });
      b.collide([-1.1, 0, -0.5], [1.1, 1.22, 0.5], { surface: 'metal' });
      b.anchor('exhaust', [0.7, 1.4, 0.2], [0, 1, 0]);
    },
  });

  R.add('floodlight_stand', {
    key: (o) => (o.on === false || o.lit === false ? 'off' : ''),
    build(b, o) {
      const on = !(o.on === false || o.lit === false);
      // A tripod with a telescopic mast and two halogen heads aimed forward and a little down.
      const hub = [0, 0.82, 0];
      for (let i = 0; i < 3; i++) {
        const a = (i / 3) * TAU + Math.PI / 2;
        const foot = [Math.cos(a) * 0.47, 0.01, Math.sin(a) * 0.47];
        b.stick(IRON, hub, foot, 0.016, { seg: 5 });
        b.stick(IRON, [0, 0.34, 0], [foot[0] * 0.52, 0.4, foot[2] * 0.52], 0.009, { seg: 4 });
        b.cyl('rubber', 0.026, 0.03, [foot[0], 0.015, foot[2]], { seg: 6 });
      }
      b.cyl(IRON, 0.024, 0.9, [0, 0.75, 0], { seg: 6 });
      b.cyl(GALV, 0.017, 1.0, [0, 1.5, 0], { seg: 6 });
      b.box(IRON, [0.06, 0.06, 0.06], [0, 1.2, 0]);
      b.box(IRON, [0.84, 0.035, 0.035], [0, 2.0, 0]);
      for (const x of [-0.3, 0.3]) {
        b.push(xf(x, 2.03, 0.04, 0.32, 0, 0));
        b.box('paint_yellow', [0.34, 0.25, 0.1], [0, 0, 0]);
        b.box(on ? glow(WORK_LIGHT, 5) : 'glass_dark', [0.29, 0.2, 0.012], [0, 0, 0.052]);
        b.box(IRON, [0.36, 0.012, 0.07], [0, 0.13, 0.07]);
        b.pop();
      }
      b.tube('rubber', [[0.02, 1.95, -0.03], [0.05, 1.3, -0.06], [0.03, 0.6, -0.04], [0.12, 0.03, -0.2], [0.34, 0.012, -0.44]], 0.01, { radial: 4, segments: 10 });
      if (on) b.lamp([0, 2.0, 0.25], { color: WORK_LIGHT, intensity: 60, range: 14, kind: 'work', dir: [0, -0.32, 0.95] });
      b.collide([-0.22, 0, -0.22], [0.22, 2.15, 0.22], { surface: 'metal' });
    },
  });

  R.add('porta_potty', {
    paint: 'paint_blue',
    colors: POTTY_COLORS,
    build(b) {
      b.box('plastic_dark', [1.2, 0.12, 1.2], [0, 0.06, 0]);
      b.box('@paint', [1.12, 1.96, 1.12], [0, 1.1, 0]);
      // A white translucent cap with a raised crown.
      b.box('paint_white', [1.18, 0.09, 1.18], [0, 2.12, 0]);
      b.box('paint_white', [0.84, 0.1, 0.84], [0, 2.2, 0]);
      // Door, a hand's width proud, with its latch and the hire company's plate.
      b.box('@paint', [0.84, 1.82, 0.03], [-0.06, 1.07, 0.572]);
      b.box('plastic_dark', [0.03, 1.82, 0.02], [0.375, 1.07, 0.575]);
      b.box('plastic_dark', [0.1, 0.16, 0.03], [0.3, 1.1, 0.595]);
      b.ring(glow(0x3ddc6a, 0.9), 0, 0.022, [0.3, 1.15, 0.611], { rot: [Math.PI / 2, 0, 0], seg: 8 });
      b.decal('porta', [-0.06, 1.62, 0.587], 0.44, 0.33, '+z', { lift: 0.002 });
      for (const s of [1, -1]) {
        for (const y of [1.76, 1.86]) b.box('plastic_dark', [0.012, 0.045, 0.7], [s * 0.562, y, 0]);
      }
      b.cyl('plastic_dark', 0.045, 0.3, [-0.42, 2.14, -0.42], { seg: 6 });
      b.collide([-0.6, 0, -0.6], [0.6, 2.25, 0.6], { surface: 'rubber' });
    },
  });

  R.add('boombox', {
    build(b) {
      boombox(b, xf(0, 0, -0.1));
    },
  });
}
