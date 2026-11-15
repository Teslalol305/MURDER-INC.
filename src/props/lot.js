// The court, the parking lot, and what hangs on roofs and facades. Everything with a front faces +Z;
// wall-mounted pieces (awning, fire escape) have the wall at their back (−Z).

import { M, Soup, glow, lattice, latheGeo, scaleUV, xf } from './kit.js';

const IRON = 'metal_dark';
const GALV = 'metal_galv';
const FLOOD = 0xdfe8ff;
const GRATING = lattice(0x23262a);

/** A ladder between two heights at (x, z): two rails and a rung every 0.3 m, the rungs running along x. */
function ladder(b, x, z, y0, y1, half = 0.2) {
  for (const s of [1, -1]) b.box(IRON, [0.03, y1 - y0, 0.03], [x + s * half, (y0 + y1) / 2, z]);
  for (let y = y0 + 0.15; y < y1; y += 0.3) b.box(IRON, [2 * half, 0.02, 0.02], [x, y, z]);
}

export function registerLot(R) {
  R.add('hoop', {
    build(b) {
      // Playground steel, a long prop like a car: the gooseneck post stands at −X, the board faces +X
      // and the rim with its chain net reaches out over the court.
      const xPost = -0.78;
      b.cyl(IRON, 0.1, 0.03, [xPost, 0.015, 0], { seg: 8 });
      b.tube(IRON, [[xPost, 0, 0], [xPost, 2.4, 0], [xPost + 0.05, 3.2, 0], [xPost + 0.3, 3.52, 0], [xPost + 0.86, 3.56, 0]], 0.06, { radial: 7, segments: 10 });
      const xBoard = 0.12;
      b.box('paint_white', [0.035, 1.05, 1.2], [xBoard, 3.45, 0]);
      b.decal('backboard', [xBoard + 0.0175, 3.45, 0], 1.2, 1.05, '+x', { lift: 0.003 });
      b.box(IRON, [0.03, 0.05, 1.0], [xBoard - 0.03, 3.2, 0]);
      b.box(IRON, [0.03, 0.9, 0.05], [xBoard - 0.03, 3.45, 0]);
      const xRim = xBoard + 0.38;
      const orange = M('paint_red', { color: 0xd9521a });
      b.lathe(orange, [[0.218, 0], [0.228, -0.011], [0.238, 0], [0.228, 0.011], [0.218, 0]], [xRim, 3.05, 0], { seg: 12, crease: 80 });
      b.box(orange, [0.16, 0.012, 0.12], [xBoard + 0.09, 3.05, 0]);
      b.box(orange, [0.012, 0.12, 0.14], [xBoard + 0.022, 3.02, 0]);
      const net = scaleUV(latheGeo([[0.14, 2.66], [0.226, 3.045]], 10), 16);
      net.translate(xRim, 0, 0);
      b.add(lattice(0x9aa0a4), net);
      b.collide([xPost - 0.08, 0, -0.08], [xPost + 0.08, 3.4, 0.08], { surface: 'metal' });
      b.collide([xBoard - 0.05, 2.9, -0.6], [xBoard + 0.03, 4.0, 0.6], { surface: 'metal', noNav: true });
    },
  });

  R.add('bleachers', {
    build(b) {
      // Four rows of aluminium plank on three steel frames; the lowest row is at the front.
      const rows = 4;
      const seatY = (i) => 0.42 + i * 0.36;
      const seatZ = (i) => 0.74 - i * 0.49;
      for (let i = 0; i < rows; i++) {
        b.box(GALV, [4.0, 0.04, 0.26], [0, seatY(i) - 0.02, seatZ(i)]);
        if (i > 0) b.box(GALV, [4.0, 0.03, 0.22], [0, seatY(i) - 0.4, seatZ(i) + 0.27]);
      }
      for (const x of [-1.85, 0, 1.85]) {
        b.bar(IRON, [x, 0.03, 0.95], [x, seatY(rows - 1) - 0.06, seatZ(rows - 1) - 0.1], 0.05);
        b.box(IRON, [0.05, 0.05, 1.96], [x, 0.03, 0]);
        b.box(IRON, [0.05, 1.56, 0.05], [x, 0.8, -0.95]);
        for (let i = 0; i < rows; i++) b.box(IRON, [0.05, seatY(i) - 0.06, 0.05], [x, (seatY(i) - 0.06) / 2, seatZ(i)]);
      }
      for (const y of [1.58, 1.2]) b.box(IRON, [4.0, 0.04, 0.04], [0, y, -0.95]);
      // Stepped colliders: you can climb the rows and stand on the top one.
      for (let i = 0; i < rows; i++) b.collide([-2, 0, seatZ(i) - 0.245], [2, seatY(i), seatZ(i) + 0.245], { surface: 'metal' });
    },
  });

  R.add('court_light', {
    key: (o) => (o.on === false || o.lit === false ? 'off' : ''),
    build(b, o) {
      const on = !(o.on === false || o.lit === false);
      // A tall steel mast with a crown of four floods, one to each side: it lights whatever it stands in.
      b.lathe(GALV, [[0.19, 0], [0.19, 0.04], [0.13, 0.08], [0.1, 0.6], [0.065, 8.5], [0, 8.55]], [0, 0, 0], { seg: 8 });
      b.box(IRON, [0.16, 0.3, 0.16], [0, 8.62, 0]);
      b.box(IRON, [1.0, 0.05, 0.05], [0, 8.7, 0]);
      b.box(IRON, [0.05, 0.05, 1.0], [0, 8.7, 0]);
      const lens = on ? glow(FLOOD, 6) : 'glass_dark';
      for (let i = 0; i < 4; i++) {
        b.push(xf(0, 8.7, 0, 0, (i * Math.PI) / 2, 0));
        b.box(IRON, [0.42, 0.28, 0.16], [0, 0, 0.5], { rot: [0.7, 0, 0] });
        b.box(lens, [0.36, 0.22, 0.012], [0, -0.054, 0.564], { rot: [0.7, 0, 0] });
        b.pop();
      }
      if (on) b.lamp([0, 8.5, 0], { color: FLOOD, intensity: 160, range: 30, kind: 'flood', dir: [0, -1, 0] });
      b.collide([-0.14, 0, -0.14], [0.14, 8.55, 0.14], { surface: 'metal' });
    },
  });

  R.add('lot_booth', {
    key: (o) => (o.lit === false ? 'off' : ''),
    build(b, o) {
      const lit = o.lit !== false;
      const wall = 'paint_white';
      const pane = lit ? 'glass_lit_warm' : 'glass_dark';
      // A parking attendant's hut: steel to the sill, glass above, a flat roof with a lip.
      b.box('concrete', [2.2, 0.1, 1.8], [0, 0.05, 0]);
      b.box(wall, [2.1, 0.95, 1.7], [0, 0.575, 0]);
      b.box(IRON, [2.14, 0.04, 1.74], [0, 1.07, 0]);
      for (const sx of [1, -1]) for (const sz of [1, -1]) b.box(wall, [0.09, 1.2, 0.09], [sx * 1.005, 1.65, sz * 0.805]);
      b.box(wall, [2.1, 1.2, 0.06], [0, 1.65, -0.82]); // blind back wall
      b.box(pane, [1.92, 1.1, 0.03], [0, 1.64, 0.82]);
      b.box(IRON, [0.04, 1.14, 0.05], [0.1, 1.64, 0.83]);
      b.box(pane, [0.03, 1.1, 1.52], [-1.02, 1.64, 0]);
      // Door on the east side with its own small window.
      b.box(wall, [0.04, 1.96, 0.8], [1.045, 1.1, -0.3]);
      b.box(pane, [0.03, 0.7, 0.5], [1.055, 1.6, -0.3]);
      b.box('chrome', [0.03, 0.1, 0.03], [1.075, 1.05, -0.02]);
      b.box(pane, [0.03, 1.1, 0.62], [1.02, 1.64, 0.44]);
      b.box(IRON, [2.2, 0.12, 1.8], [0, 2.31, 0]);
      // Signs: PARK under the window, the tariff by the door.
      b.decal('booth_sign', [0, 0.6, 0.85], 1.6, 0.56, '+z', { lit, lift: 0.004 });
      b.decal('booth_rates', [1.05, 0.62, 0.42], 0.5, 0.65, '+x', { lift: 0.004 });
      b.box(GALV, [0.5, 0.27, 0.3], [-0.5, 2.455, -0.5]); // roof unit
      b.box('plastic_dark', [0.44, 0.18, 0.012], [-0.5, 2.455, -0.344]);
      if (lit) {
        b.lamp([0, 1.6, 1.0], { color: 0xffc48a, intensity: 14, range: 6, kind: 'window' });
        b.lamp([0, 0.6, 1.0], { color: 0xf6c21a, intensity: 6, range: 4, kind: 'neon' });
      }
      b.collide([-1.1, 0, -0.9], [1.1, 2.37, 0.9], { surface: 'metal' });
    },
  });

  R.add('billboard', {
    key: (o) => (o.lit === false ? 'off' : ''),
    build(b, o, env) {
      const lit = o.lit !== false;
      const steel = 'steel_el';
      const y0 = 6.7; // underside of the face
      const y1 = 10.8;
      const zFace = 0.22;
      // Two riveted legs, braced; a truss behind the face; a catwalk and lamp arms in front of it.
      for (const x of [-2.6, 2.6]) {
        b.box(steel, [0.34, y1 - 0.2, 0.34], [x, (y1 - 0.2) / 2, -0.2]);
        b.box(steel, [0.7, 0.06, 0.7], [x, 0.03, -0.2]);
      }
      for (const [ya, yb] of [[1.2, 3.6], [3.6, 6.0]]) {
        b.bar(steel, [-2.6, ya, -0.2], [2.6, yb, -0.2], 0.09);
        b.bar(steel, [2.6, ya, -0.2], [-2.6, yb, -0.2], 0.09);
      }
      for (const y of [1.2, 3.6, 6.0]) b.box(steel, [5.2, 0.12, 0.12], [0, y, -0.2]);
      for (const y of [y0 + 0.1, (y0 + y1) / 2, y1 - 0.1]) b.box(steel, [9.0, 0.12, 0.12], [0, y, 0.06]);
      for (const x of [-4.3, -2.6, 0, 2.6, 4.3]) b.box(steel, [0.1, y1 - y0, 0.1], [x, (y0 + y1) / 2, 0.06]);
      b.box(IRON, [9.0, y1 - y0, 0.06], [0, (y0 + y1) / 2, zFace - 0.04]);
      const face = b.own(env.materials.billboardFace());
      b.quad(face, [-4.45, y0 + 0.05, zFace], [4.45, y0 + 0.05, zFace], [4.45, y1 - 0.05, zFace], [-4.45, y1 - 0.05, zFace], { uv: [0, 0, 1, 1] });
      // Catwalk under the face.
      const yWalk = y0 - 0.35;
      const walk = new Soup().quad([-4.5, yWalk, 0.59], [4.5, yWalk, 0.59], [4.5, yWalk, 0.16], [-4.5, yWalk, 0.16]);
      b.add(GRATING, scaleUV(walk.build(0), 12, 30));
      b.box(steel, [9.0, 0.06, 0.05], [0, yWalk - 0.03, 0.57]);
      b.box(steel, [9.0, 0.04, 0.04], [0, yWalk + 0.9, 0.57]);
      for (let x = -4.4; x <= 4.41; x += 2.2) {
        b.box(steel, [0.04, 0.9, 0.04], [x, yWalk + 0.45, 0.57]);
        b.bar(steel, [x, yWalk - 0.03, 0.55], [x, yWalk - 0.5, 0.1], 0.05);
      }
      ladder(b, 2.6, 0.02, 0.4, yWalk, 0.18);
      // Lamps on arms, throwing their light up the face.
      for (const x of [-3.3, -1.1, 1.1, 3.3]) {
        b.box(IRON, [0.4, 0.1, 0.14], [x, yWalk - 0.02, 0.5], { rot: [0.5, 0, 0] });
        if (lit) b.box(glow(0xfff1d6, 3.2), [0.34, 0.012, 0.1], [x, yWalk + 0.03, 0.475], { rot: [0.5, 0, 0] });
      }
      if (lit) {
        for (const x of [-2.2, 2.2]) b.lamp([x, y0 + 0.4, 0.6], { color: 0xfff1d6, intensity: 40, range: 12, kind: 'flood', dir: [0, 0.9, -0.44] });
      }
      for (const x of [-2.6, 2.6]) b.collide([x - 0.2, 0, -0.4], [x + 0.2, y0, 0], { surface: 'metal' });
      b.collide([-4.5, y0 - 0.4, -0.1], [4.5, y1, 0.6], { surface: 'metal', noNav: true });
    },
  });

  R.add('water_tower', {
    build(b) {
      const steel = 'steel_el';
      // A wooden tank on a steel stand, the way one sits on every roof in the borough.
      for (const sx of [1, -1]) {
        for (const sz of [1, -1]) {
          b.box(steel, [0.12, 1.9, 0.12], [sx * 1.0, 0.95, sz * 1.0]);
          b.box(steel, [0.3, 0.04, 0.3], [sx * 1.0, 0.02, sz * 1.0]);
        }
        b.bar(steel, [sx * 1.0, 0.1, -1.0], [sx * 1.0, 1.8, 1.0], 0.06);
        b.bar(steel, [-1.0, 0.1, sx * 1.0], [1.0, 1.8, sx * 1.0], 0.06);
        b.box(steel, [2.6, 0.14, 0.12], [0, 1.95, sx * 1.0]);
        b.box(steel, [0.12, 0.14, 2.6], [sx * 1.0, 1.95, 0]);
      }
      for (const x of [-0.5, 0, 0.5]) b.box('wood', [0.14, 0.12, 2.7], [x, 2.07, 0]);
      const r = 1.3;
      b.lathe('wood', [[0, 2.13], [r, 2.13], [r - 0.05, 4.1]], [0, 0, 0], { seg: 14 });
      for (const y of [2.3, 2.75, 3.2, 3.6, 3.95]) {
        const ry = r - ((y - 2.13) / 1.97) * 0.05;
        b.lathe(IRON, [[ry + 0.004, y - 0.025], [ry + 0.012, y], [ry + 0.004, y + 0.025]], [0, 0, 0], { seg: 14, crease: 80 });
      }
      b.lathe(IRON, [[r - 0.05, 4.1], [r + 0.1, 4.08], [0.1, 4.86], [0.06, 4.96], [0, 4.98]], [0, 0, 0], { seg: 14 });
      b.cyl(IRON, 0.07, 2.1, [0.2, 1.05, 0.15], { seg: 6 });
      ladder(b, 0, r + 0.06, 0.3, 4.3, 0.17);
    },
  });

  R.add('ac_unit', {
    build(b) {
      for (const z of [-0.3, 0.3]) b.box(IRON, [1.2, 0.08, 0.08], [0, 0.04, z]);
      b.box(GALV, [1.16, 0.74, 0.86], [0, 0.45, 0]);
      b.box(GALV, [1.2, 0.03, 0.9], [0, 0.835, 0]);
      // A fan under its guard on top, louvres along the front, a conduit down the side.
      b.ring('plastic_dark', 0, 0.3, [0.22, 0.852, 0], { seg: 12 });
      b.lathe(IRON, [[0.3, 0.85], [0.31, 0.89], [0.29, 0.9]], [0.22, 0, 0], { seg: 12, crease: 60 });
      for (let i = 0; i < 2; i++) b.box(IRON, [0.6, 0.012, 0.03], [0.22, 0.89, 0], { rot: [0, i * (Math.PI / 2), 0] });
      for (let i = 0; i < 6; i++) b.box('plastic_dark', [0.9, 0.035, 0.012], [-0.08, 0.2 + i * 0.09, 0.432], { rot: [0.35, 0, 0] });
      b.box(IRON, [0.2, 0.3, 0.012], [0.44, 0.5, 0.436]);
      b.cyl(IRON, 0.025, 0.7, [-0.57, 0.4, -0.2], { seg: 5 });
      b.collide([-0.6, 0, -0.45], [0.6, 0.86, 0.45], { surface: 'metal' });
    },
  });

  R.add('fire_escape', {
    key: (o) => (o.variant === 'top' || o.variant === 'bottom' ? o.variant : ''),
    build(b, o) {
      // One storey: a landing with its railing against the wall (−Z), and the way up to the next one.
      const y = 0.25; // landing deck
      const wallZ = -0.55;
      const frontZ = 0.5;
      // Deck in two strips: the hatch for the stair from below stays open at the west end by the wall.
      const deck = new Soup();
      deck.quad([-1.45, y, frontZ], [1.45, y, frontZ], [1.45, y, 0], [-1.45, y, 0]);
      deck.quad([-0.5, y, 0], [1.45, y, 0], [1.45, y, wallZ + 0.03], [-0.5, y, wallZ + 0.03]);
      b.add(GRATING, scaleUV(deck.build(0), 9, 34));
      for (const z of [frontZ, wallZ + 0.03]) b.box(IRON, [2.96, 0.07, 0.05], [0, y - 0.03, z]);
      for (const x of [-1.47, 1.47]) b.box(IRON, [0.05, 0.07, 1.04], [x, y - 0.03, -0.005]);
      b.box(IRON, [2.9, 0.05, 0.04], [0, y - 0.03, 0]);
      for (const x of [-1.3, 1.3]) b.bar(IRON, [x, 0.02, wallZ + 0.04], [x, y - 0.06, frontZ - 0.05], 0.04); // brackets
      // Railing: two rails and a row of square bars.
      const top = y + 0.95;
      const rail = (a, c) => {
        b.bar(IRON, [a[0], top, a[1]], [c[0], top, c[1]], 0.045, 0.03);
        b.bar(IRON, [a[0], y + 0.45, a[1]], [c[0], y + 0.45, c[1]], 0.03, 0.02);
      };
      rail([-1.46, frontZ], [1.46, frontZ]);
      rail([-1.46, wallZ + 0.04], [-1.46, frontZ]);
      rail([1.46, wallZ + 0.04], [1.46, frontZ]);
      for (let x = -1.46; x <= 1.461; x += 0.365) b.box(IRON, [0.025, 0.95, 0.025], [x, y + 0.475, frontZ]);
      for (const x of [-1.46, 1.46]) for (const z of [-0.25, 0.1]) b.box(IRON, [0.025, 0.95, 0.025], [x, y + 0.475, z]);

      if (o.variant === 'top') {
        // The last flight is a ladder hooked over the parapet.
        ladder(b, -1.0, wallZ + 0.12, y, 2.98);
      } else {
        // A steep stair up to the hatch of the landing above.
        const foot = [0.95, y];
        const head = [-0.62, 3.25];
        const at = (t) => [foot[0] + (head[0] - foot[0]) * t, foot[1] + (head[1] - foot[1]) * t];
        const cut = (2.97 - foot[1]) / (head[1] - foot[1]); // the module ends at 3 m; the next one carries on
        for (const z of [-0.47, -0.07]) {
          b.bar(IRON, [foot[0], foot[1], z], [at(cut)[0], at(cut)[1], z], 0.12, 0.025);
          b.bar(IRON, [foot[0] - 0.12, foot[1] + 0.9, z], [at(cut)[0] - 0.12, 2.97, z], 0.03);
        }
        for (let i = 1; i <= 9; i++) {
          const [sx, sy] = at(i / 10);
          if (sy < 2.95) b.box(IRON, [0.16, 0.02, 0.4], [sx, sy, -0.27]);
        }
      }
      if (o.variant === 'bottom') {
        // The drop ladder, hauled up and waiting.
        ladder(b, -1.0, -0.27, -1.6, y + 0.9);
        b.box(IRON, [0.5, 0.04, 0.04], [-1.0, y + 0.9, -0.27]);
      }
    },
  });

  R.add('awning', {
    paint: 'fabric_awning',
    key: (o) => `${o.variant === 'striped' ? 'striped' : ''}|${o.text || ''}|${o.text ? o.color ?? '' : ''}`,
    build(b, o, env) {
      // A shed awning: slope, scalloped valance, closed ends, on a pipe frame bolted to the wall (−Z).
      const back = [-0.65, 0.9];
      const lip = [0.63, 0.34];
      const hem = 0.1;
      const panels = 8;
      const fabric = (i) => (o.variant === 'striped' && i % 2 ? 'paint_white' : '@paint');
      for (let i = 0; i < panels; i++) {
        const x0 = -2 + (i * 4) / panels;
        const x1 = x0 + 4 / panels;
        const xm = (x0 + x1) / 2;
        const soup = new Soup();
        soup.quad([x0, lip[1], lip[0]], [x1, lip[1], lip[0]], [x1, back[1], back[0]], [x0, back[1], back[0]]);
        soup.quad([x1, lip[1], lip[0]], [x0, lip[1], lip[0]], [x0, back[1], back[0]], [x1, back[1], back[0]]);
        // Valance: one scallop per panel, seen from both sides.
        const flap = [[x0, lip[1]], [x0, hem + 0.07], [xm, hem], [x1, hem + 0.07], [x1, lip[1]]].map(([x, y]) => [x, y, lip[0]]);
        soup.fan(flap);
        soup.fan(flap.slice().reverse());
        b.add(fabric(i), soup.build(0));
      }
      for (const s of [1, -1]) {
        const x = s * 2;
        const a = [x, back[1], back[0]];
        const c = [x, lip[1], lip[0]];
        const d = [x, lip[1], back[0]];
        b.add(fabric(s > 0 ? panels - 1 : 0), new Soup().tri(a, c, d).tri(a, d, c).build(0));
        b.stick(GALV, [x * 0.985, lip[1], back[0]], [x * 0.985, lip[1], lip[0] - 0.01], 0.015, { seg: 5 });
      }
      b.stick(GALV, [-1.97, lip[1], lip[0] - 0.01], [1.97, lip[1], lip[0] - 0.01], 0.015, { seg: 5 });
      if (o.text) {
        // The shop's name along the valance, painted by the material library.
        const sign = env.materials.sign({ text: o.text, w: 3.4, h: 0.19, style: 'awning', fg: 0xf4f2ec, bg: o.color ?? 0x7a1f24, lit: false });
        const y = hem + 0.165;
        const z = lip[0] + 0.004;
        b.quad(b.own(sign.material), [-1.7, y - 0.095, z], [1.7, y - 0.095, z], [1.7, y + 0.095, z], [-1.7, y + 0.095, z], { uv: sign.uv || [0, 0, 1, 1] });
      }
    },
  });
}
