// V&R Auto Body: the chop shop's floor. Everything with a front faces +Z (stand it with its back to a wall).

import { M, glow, latheGeo, xf } from './kit.js';
import { CAR_COLORS, car, carColliders } from './vehicles.js';

const IRON = 'metal_dark';
const GALV = 'metal_galv';
const LIFT_BLUE = M('paint_blue', { color: 0x1a4a8a });
const PRIMER = [0x6b6f73, 0x7a3b2c, 0x4c5055, 0x8a8f96];
const HOIST_COLORS = [0x1f4f9a, 0xb3261e, 0xd9621a];
const LIFT_HEIGHT = 1.95; // how far a raised car's wheels are off the floor

/** A tyre lying flat (the same section the tyre stacks use, lighter). */
function tyre(b, m) {
  const r = 0.36;
  const h = 0.22;
  b.add('tire', latheGeo([[0.2, 0.02], [r - 0.06, 0], [r, 0.05], [r, h - 0.05], [r - 0.06, h], [0.2, h - 0.02], [0.2, 0.02]], 8, { crease: 50 }), m);
}

/** A jack stand: a pyramid of plate with a ratchet post, `h` tall. */
function jackStand(b, x, z, h) {
  b.lathe(IRON, [[0.15, 0], [0.04, h * 0.7]], [x, 0, z], { seg: 4, rot: [0, Math.PI / 4, 0] });
  b.box(GALV, [0.04, h * 0.4, 0.04], [x, h * 0.8, z]);
  b.box(GALV, [0.1, 0.02, 0.06], [x, h - 0.01, z]);
}

export function registerShop(R) {
  R.add('car_lift', {
    variants: 2,
    colors: CAR_COLORS,
    key: (o) => (o.variant === 'car' || o.variant === 'down' ? o.variant : ''),
    build(b, o) {
      // Two posts either side of the bay, tied by a beam overhead; carriages with swing arms and pads.
      // The arms are up, pads LIFT_HEIGHT + 0.19 off the floor: a car placed at y = LIFT_HEIGHT rests on
      // them ('car' brings its own, 'down' lowers the arms).
      const armY = o.variant === 'down' ? 0.16 : LIFT_HEIGHT + 0.12;
      for (const s of [1, -1]) {
        const z = s * 1.4;
        b.box(IRON, [0.62, 0.025, 0.36], [0, 0.0125, z]);
        b.box(LIFT_BLUE, [0.3, 3.46, 0.26], [0, 1.755, z]);
        b.box(IRON, [0.05, 3.3, 0.02], [0, 1.75, z - s * 0.135]); // the carriage track
        b.box(LIFT_BLUE, [0.36, 0.42, 0.14], [0, armY + 0.1, z - s * 0.2]);
        for (const x of [1, -1]) {
          const pad = [x * 1.0, armY, s * 0.62];
          b.bar(IRON, [x * 0.12, armY, z - s * 0.26], pad, 0.07, 0.1);
          b.cyl(IRON, 0.07, 0.04, [pad[0], armY + 0.05, pad[2]], { seg: 8 });
        }
      }
      b.box(LIFT_BLUE, [0.22, 0.12, 3.1], [0, 3.52, 0]);
      b.box(IRON, [0.2, 0.5, 0.2], [0.26, 1.3, 1.45]); // power unit
      b.cyl(GALV, 0.07, 0.3, [0.26, 1.7, 1.45], { seg: 8 });
      b.stick(IRON, [0.34, 1.3, 1.45], [0.52, 1.42, 1.45], 0.012, { seg: 4 });
      for (const s of [1, -1]) b.collide([-0.2, 0, s * 1.4 - 0.16], [0.2, 3.5, s * 1.4 + 0.16], { surface: 'metal' });
      if (o.variant !== 'car') return;
      // A car up in the air: you walk under it, bullets do not go through it.
      b.push(xf(0, LIFT_HEIGHT, 0));
      const { c } = car(b, { wheel: { style: o.variantIndex ? 'steel' : 'cap' } }, `plate_${o.variantIndex}`);
      b.pop();
      carColliders(b, c, LIFT_HEIGHT, { noNav: true });
    },
  });

  R.add('car_on_stands', {
    colors: PRIMER,
    build(b) {
      // Stripped to the shell: no doors, no glass, no wheels, in primer, on four stands.
      const lift = 0.15;
      b.push(xf(0, lift, 0));
      const { c, S } = car(b, {
        L: 4.5, hw: 0.86, glass: false, trim: false, bumper: null, wheels: 'hubs', doorsOff: true,
        underSlot: IRON,
      });
      // Bare floor where the seats were, a gutted dash, an open engine bay.
      const zi = c.hw - 0.09;
      const sill = c.clearance + 0.205;
      b.quad(IRON, [c.rearBase + 0.52, sill, zi], [c.cowl - 0.32, sill, zi], [c.cowl - 0.32, sill, -zi], [c.rearBase + 0.52, sill, -zi]);
      b.box(IRON, [0.16, 0.2, 2 * zi], [c.cowl - 0.2, c.belt - 0.12, 0]);
      const hz = S.side(1.6, 0.95) - 0.08;
      b.quad(IRON, [c.cowl + 0.06, 1.012, hz], [S.hF - 0.14, 0.925, hz], [S.hF - 0.14, 0.925, -hz], [c.cowl + 0.06, 1.012, -hz]);
      b.box(GALV, [0.5, 0.2, 0.5], [1.5, 0.92, 0]);
      b.pop();
      for (const x of [1.0, -1.0]) for (const z of [0.66, -0.66]) jackStand(b, x, z, c.clearance + lift);
      carColliders(b, { ...c, cover: c.cover + lift, H: c.H + lift });
    },
  });

  R.add('tool_chest', {
    paint: 'paint_red',
    build(b) {
      // Roller cabinet with a top chest: drawer fronts a finger proud, an aluminium pull on each.
      for (const sx of [1, -1]) for (const sz of [1, -1]) b.cyl('rubber', 0.05, 0.04, [sx * 0.45, 0.05, sz * 0.2], { axis: 'x', seg: 8 });
      b.box('@paint', [1.06, 0.62, 0.5], [0, 0.43, -0.01]);
      b.box('@paint', [1.02, 0.33, 0.46], [0, 0.905, -0.02]);
      b.box(IRON, [1.08, 0.02, 0.52], [0, 0.745, -0.01]);
      b.box('@paint', [1.04, 0.025, 0.48], [0, 1.08, -0.02]);
      let y = 0.14;
      for (const h of [0.16, 0.12, 0.12, 0.09, 0.09]) {
        b.box('@paint', [1.0, h - 0.012, 0.014], [0, y + h / 2, 0.245]);
        b.box(GALV, [0.98, 0.014, 0.02], [0, y + h - 0.014, 0.256]);
        y += h;
      }
      y = 0.76;
      for (const h of [0.11, 0.09, 0.09]) {
        b.box('@paint', [0.96, h - 0.012, 0.014], [0, y + h / 2, 0.215]);
        b.box(GALV, [0.94, 0.014, 0.02], [0, y + h - 0.014, 0.226]);
        y += h;
      }
      b.pipe(GALV, [[0.525, 0.55, -0.15], [0.538, 0.55, -0.15], [0.538, 0.55, 0.13], [0.525, 0.55, 0.13]], 0.01, { seg: 5 });
      b.collide([-0.54, 0, -0.27], [0.54, 1.09, 0.27], { surface: 'metal' });
    },
  });

  R.add('workbench', {
    build(b) {
      // Angle-iron frame, a thick timber top, a shelf of junk, a vise on the front corner.
      for (const sx of [1, -1]) for (const sz of [1, -1]) b.box(IRON, [0.06, 0.74, 0.06], [sx * 1.04, 0.37, sz * 0.33]);
      for (const sz of [1, -1]) b.box(IRON, [2.08, 0.05, 0.04], [0, 0.7, sz * 0.33]);
      b.box('wood', [2.2, 0.06, 0.78], [0, 0.77, 0]);
      b.box('plywood', [2.06, 0.025, 0.62], [0, 0.2, 0]);
      b.box(M('paint_red', { color: 0x8a1c1c }), [0.5, 0.22, 0.24], [-0.6, 0.325, 0.02]);
      b.box('cardboard', [0.4, 0.3, 0.36], [0.5, 0.365, -0.05], { rot: [0, 0.2, 0] });
      b.cyl(GALV, 0.09, 0.26, [0.05, 0.345, 0.1], { seg: 8 });
      // Vise: body, jaws, screw handle.
      b.box(M('paint_blue', { color: 0x234a7a }), [0.16, 0.1, 0.2], [-0.82, 0.85, 0.22]);
      b.box(GALV, [0.14, 0.05, 0.03], [-0.82, 0.925, 0.3]);
      b.box(GALV, [0.14, 0.05, 0.03], [-0.82, 0.925, 0.2]);
      b.stick(GALV, [-0.92, 0.85, 0.36], [-0.72, 0.85, 0.36], 0.008, { seg: 4 });
      // What was being worked on: a carburettor on a rag, a tray of sockets, a coffee.
      b.box(M('fabric', { color: 0x7a2a2a }), [0.34, 0.008, 0.26], [0.1, 0.804, 0.08], { rot: [0, 0.3, 0] });
      b.box(GALV, [0.16, 0.11, 0.14], [0.1, 0.862, 0.08], { rot: [0, 0.3, 0] });
      b.cyl(GALV, 0.035, 0.05, [0.1, 0.93, 0.08], { seg: 6 });
      b.box(IRON, [0.4, 0.03, 0.22], [0.72, 0.815, -0.12]);
      for (let i = 0; i < 5; i++) b.cyl('chrome', 0.014 + i * 0.002, 0.04, [0.58 + i * 0.07, 0.85, -0.12], { seg: 6 });
      b.cyl('paint_white', 0.038, 0.1, [-0.3, 0.85, -0.2], { seg: 8 });
      b.collide([-1.1, 0, -0.39], [1.1, 0.8, 0.39], { surface: 'wood' });
    },
  });

  R.add('engine_hoist', {
    paint: 'paint_blue',
    colors: HOIST_COLORS,
    build(b) {
      // A cherry picker: splayed legs on casters, a mast, a boom on a ram, an engine swinging from the hook.
      const mast = -0.6;
      for (const s of [1, -1]) {
        b.bar('@paint', [mast, 0.1, s * 0.16], [0.7, 0.1, s * 0.5], 0.08, 0.07);
        b.cyl('rubber', 0.045, 0.04, [0.7, 0.045, s * 0.5], { axis: 'z', seg: 8 });
        b.cyl('rubber', 0.045, 0.04, [mast - 0.06, 0.045, s * 0.26], { axis: 'z', seg: 8 });
      }
      b.box('@paint', [0.1, 0.08, 0.62], [mast - 0.06, 0.1, 0]);
      b.box('@paint', [0.1, 1.5, 0.1], [mast, 0.85, 0]);
      const tip = [0.44, 1.92, 0];
      b.bar('@paint', [mast, 1.58, 0], tip, 0.09);
      b.stick(IRON, [mast + 0.1, 0.45, 0], [mast + 0.42, 1.36, 0], 0.045, { seg: 7, caps: true });
      b.stick('chrome', [mast + 0.42, 1.36, 0], [mast + 0.55, 1.72, 0], 0.022, { seg: 6 });
      b.stick(GALV, [mast + 0.14, 0.5, 0.05], [mast + 0.42, 0.62, 0.3], 0.012, { seg: 4 }); // pump handle
      // Chain, hook, and the lump.
      b.box(IRON, [0.02, 0.5, 0.02], [tip[0], tip[1] - 0.27, 0]);
      b.box(IRON, [0.3, 0.02, 0.02], [tip[0], tip[1] - 0.52, 0]);
      const ey = 1.08;
      b.box(IRON, [0.52, 0.34, 0.4], [tip[0], ey, 0]);
      for (const s of [1, -1]) {
        b.box(GALV, [0.48, 0.12, 0.16], [tip[0], ey + 0.19, s * 0.15], { rot: [s * 0.6, 0, 0] });
        b.box(M('paint_red', { color: 0x8a1c1c }), [0.44, 0.04, 0.13], [tip[0], ey + 0.27, s * 0.19], { rot: [s * 0.6, 0, 0] });
      }
      b.cyl(GALV, 0.09, 0.05, [tip[0] + 0.29, ey - 0.02, 0], { axis: 'x', seg: 8 });
      b.cyl(GALV, 0.05, 0.05, [tip[0] + 0.29, ey + 0.16, 0.1], { axis: 'x', seg: 8 });
      b.box(IRON, [0.16, 0.2, 0.3], [tip[0] - 0.33, ey - 0.02, 0]);
      b.collide([mast - 0.1, 0, -0.1], [mast + 0.1, 1.6, 0.1], { surface: 'metal' });
      b.collide([tip[0] - 0.4, 0.85, -0.3], [tip[0] + 0.33, 1.38, 0.3], { surface: 'metal' });
      b.collide([mast - 0.1, 0, -0.55], [0.76, 0.16, 0.55], { surface: 'metal' }); // the legs: low enough to step over
    },
  });

  R.add('shelf_rack', {
    variants: 2,
    build(b) {
      const rng = b.rng;
      const frame = LIFT_BLUE;
      const beam = M('paint_red', { color: 0xd9621a });
      // Pallet racking: two frames, four beam levels, loaded with parts.
      for (const sx of [1, -1]) {
        for (const sz of [1, -1]) b.box(frame, [0.08, 3.0, 0.07], [sx * 1.31, 1.5, sz * 0.4]);
        for (const y of [0.3, 1.2, 2.1, 2.9]) b.box(frame, [0.04, 0.04, 0.74], [sx * 1.31, y, 0]);
        b.bar(frame, [sx * 1.31, 0.3, -0.37], [sx * 1.31, 1.2, 0.37], 0.035);
        b.bar(frame, [sx * 1.31, 1.2, 0.37], [sx * 1.31, 2.1, -0.37], 0.035);
      }
      const levels = [0.14, 0.98, 1.82, 2.62];
      for (const y of levels) {
        for (const sz of [1, -1]) b.box(beam, [2.56, 0.1, 0.05], [0, y, sz * 0.4]);
        b.box('plywood', [2.54, 0.025, 0.78], [0, y + 0.06, 0]);
      }
      const deck = (i) => levels[i] + 0.0725;
      // Bottom: tyres. Then cartons, parts bins, a row of oil cans; the top shelf half empty.
      for (const [x, n] of [[-0.82, 3], [0, 2], [0.82, 3]]) {
        for (let k = 0; k < n; k++) tyre(b, xf(x + rng.range(-0.02, 0.02), deck(0) + k * 0.215, rng.range(-0.02, 0.02)));
      }
      let x = -1.12;
      while (x < 1.0) {
        const w = rng.range(0.3, 0.52);
        const h = rng.range(0.24, 0.5);
        b.box('cardboard', [w, h, rng.range(0.4, 0.62)], [x + w / 2, deck(1) + h / 2, rng.range(-0.05, 0.05)], { rot: [0, rng.range(-0.08, 0.08), 0] });
        x += w + rng.range(0.03, 0.12);
      }
      for (const bx of [-0.9, -0.36, 0.2]) b.box(M('paint_blue', { color: 0x2c5c9a }), [0.46, 0.26, 0.6], [bx, deck(2) + 0.13, 0]);
      for (let i = 0; i < 4; i++) b.cyl(GALV, 0.09, 0.3, [0.66 + (i % 2) * 0.2, deck(2) + 0.15, -0.12 + Math.floor(i / 2) * 0.24], { seg: 7 });
      b.box('cardboard', [0.6, 0.3, 0.5], [-0.7, deck(3) + 0.15, 0], { rot: [0, 0.12, 0] });
      b.box('wood', [0.9, 0.22, 0.4], [0.5, deck(3) + 0.11, 0.05]);
      b.collide([-1.35, 0, -0.45], [1.35, 3.0, 0.45], { surface: 'metal' });
    },
  });

  R.add('compressor', {
    paint: 'paint_red',
    colors: [0xb3261e, 0x1f4f9a, 0x202326],
    build(b) {
      // A wheeled shop compressor: tank on its side, motor and pump on top under a belt guard.
      const tank = latheGeo([[0, -0.46], [0.12, -0.44], [0.19, -0.38], [0.2, -0.3], [0.2, 0.3], [0.19, 0.38], [0.12, 0.44], [0, 0.46]], 10);
      b.add('@paint', tank, xf(-0.05, 0.36, 0, 0, 0, Math.PI / 2));
      for (const s of [1, -1]) {
        const m = xf(-0.38, 0.12, s * 0.24, (s * Math.PI) / 2, 0, 0);
        b.add('tire', latheGeo([[0, -0.025], [0.12, -0.025], [0.12, 0.025], [0.06, 0.025]], 10), m);
        b.add(GALV, latheGeo([[0.06, 0.025], [0, 0.03]], 8), m);
      }
      b.box(IRON, [0.06, 0.16, 0.3], [0.32, 0.08, 0]);
      b.box(IRON, [0.6, 0.03, 0.3], [-0.05, 0.57, 0]);
      b.cyl(GALV, 0.1, 0.28, [-0.24, 0.69, -0.02], { axis: 'x', seg: 8 });
      b.box(IRON, [0.18, 0.24, 0.2], [0.14, 0.7, -0.04]);
      for (let i = 0; i < 4; i++) b.box(GALV, [0.2, 0.012, 0.22], [0.14, 0.64 + i * 0.045, -0.04]);
      b.box(IRON, [0.56, 0.26, 0.035], [-0.05, 0.7, 0.14]); // belt guard
      b.cyl(GALV, 0.035, 0.03, [0.3, 0.5, 0.17], { axis: 'z', seg: 8 }); // gauge
      b.pipe(GALV, [[0.42, 0.3, -0.16], [0.56, 0.86, -0.16], [0.56, 0.86, 0.16], [0.42, 0.3, 0.16]], 0.014, { seg: 5 });
      // Hose coiled over the handle.
      const coil = [];
      for (let i = 0; i <= 16; i++) {
        const a = (i / 16) * Math.PI * 4;
        coil.push([0.56 + i * 0.002, 0.7 + Math.cos(a) * 0.14, Math.sin(a) * 0.12]);
      }
      b.tube(M('plastic_orange', { color: 0xd9a21a }), coil, 0.012, { radial: 4, segments: 28 });
      b.collide([-0.55, 0, -0.28], [0.58, 0.9, 0.28], { surface: 'metal' });
    },
  });

  R.add('vending_machine', {
    key: (o) => (o.lit === false ? 'off' : ''),
    build(b, o) {
      const lit = o.lit !== false;
      // A soda machine: one big lit face, a column of buttons, a slot for the cans.
      b.box('paint_black', [0.9, 1.84, 0.76], [0, 0.93, -0.02]);
      b.box(IRON, [0.9, 0.02, 0.8], [0, 0.01, 0]);
      b.decal('vend', [-0.12, 1.14, 0.36], 0.6, 1.2, '+z', { lit, lift: 0.004 });
      b.box(IRON, [0.64, 1.24, 0.02], [-0.12, 1.14, 0.36]);
      b.box(IRON, [0.2, 1.24, 0.02], [0.33, 1.14, 0.36]);
      for (let i = 0; i < 6; i++) {
        b.box(lit ? glow(i === 2 ? 0xff5a3a : 0xdfe8ff, 1.5) : 'plastic_dark', [0.12, 0.06, 0.012], [0.33, 1.58 - i * 0.11, 0.376]);
      }
      b.box('chrome', [0.1, 0.14, 0.012], [0.33, 0.82, 0.376]);
      b.box('plastic_dark', [0.03, 0.06, 0.016], [0.33, 0.84, 0.384]);
      b.box('plastic_dark', [0.62, 0.2, 0.03], [-0.12, 0.34, 0.352]);
      b.box(IRON, [0.58, 0.14, 0.012], [-0.12, 0.33, 0.372], { rot: [0.25, 0, 0] });
      if (lit) b.lamp([-0.1, 1.2, 0.6], { color: 0x9fd4ff, intensity: 12, range: 5, kind: 'neon' });
      b.collide([-0.45, 0, -0.4], [0.45, 1.85, 0.38], { surface: 'metal' });
    },
  });
}
