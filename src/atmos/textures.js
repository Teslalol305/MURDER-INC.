// Canvas-painted textures for the atmosphere: the facade sheet of the far city, the skyline strips, the
// subway car, loose paper. No text, no files; everything is drawn with rectangles and gradients.

import * as THREE from 'three';
import { skylineProfile } from './plan.js';

/** Texture edge in pixels for the active quality (CONTRACT 6.1: test 256, low 512, otherwise 1024). */
export function textureSize(G, full = 1024) {
  const name = G.quality.name;
  return name === 'test' ? full / 4 : name === 'low' ? full / 2 : full;
}

function canvasTexture(w, h, draw, { repeatX = false, srgb = true, aniso = 4 } = {}) {
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(2, Math.round(w));
  canvas.height = Math.max(2, Math.round(h));
  const result = draw(canvas.getContext('2d'), canvas.width, canvas.height);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  texture.wrapS = repeatX ? THREE.RepeatWrapping : THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.anisotropy = aniso;
  return { texture, result };
}

const rgb = (r, g, b, a = 1) => `rgba(${Math.round(r)},${Math.round(g)},${Math.round(b)},${a})`;

// ------------------------------------------------------------------------------------------------
// Facade sheet: 8 bays wide (tiles sideways), 8 rows tall
//   row 7 (top)      blank brick (side walls, parapets, roof clutter)
//   rows 1…6         upper floors: a window per bay, some lit
//   row 0 (bottom)   the ground floor: roll-down gates and lit shop fronts
// ------------------------------------------------------------------------------------------------

export const SHEET = {
  bays: 8,
  rows: 8,
  windowRows: 6,
  // The window opening inside a cell, as fractions of the cell (v measured from the cell's bottom).
  window: { u0: 0.25, u1: 0.75, v0: 0.24, v1: 0.8 },
};

const LIT = [
  [255, 214, 150], // tungsten
  [255, 198, 120],
  [250, 226, 180],
  [208, 232, 218], // kitchen fluorescent
  [128, 168, 255], // television
  [255, 132, 96], // red curtain
];

/**
 * @returns {{texture: THREE.Texture, lit: boolean[][]}}  lit[row 0…5 from the bottom][bay]
 */
export function facadeSheet(size, rng, litFraction) {
  const lit = [];
  const { texture } = canvasTexture(
    size,
    size,
    (ctx, S) => {
      const c = S / 8;
      // Brick: very dark (the material lifts it), with courses and a little grain.
      ctx.fillStyle = rgb(42, 35, 33);
      ctx.fillRect(0, 0, S, S);
      const course = Math.max(2, Math.round(c / 20));
      ctx.fillStyle = rgb(20, 17, 16, 0.45);
      for (let y = 0; y < S; y += course) ctx.fillRect(0, y, S, 1);
      for (let i = 0; i < S * 5; i++) {
        const shade = rng.next();
        ctx.fillStyle = shade < 0.5 ? rgb(0, 0, 0, 0.12) : rgb(120, 100, 90, 0.07);
        ctx.fillRect(rng.next() * S, rng.next() * S, c * rng.range(0.05, 0.22), course);
      }
      // Soot streaks under the sills, darker toward the top of each floor band.
      for (let row = 1; row <= 6; row++) {
        const g = ctx.createLinearGradient(0, row * c, 0, (row + 1) * c);
        g.addColorStop(0, rgb(0, 0, 0, 0.18));
        g.addColorStop(1, rgb(0, 0, 0, 0));
        ctx.fillStyle = g;
        ctx.fillRect(0, row * c, S, c);
      }

      const w = SHEET.window;
      for (let j = 0; j < SHEET.windowRows; j++) {
        const rowLit = [];
        const top = (6 - j) * c; // canvas y of this row's top edge (row j counted from the bottom)
        for (let bay = 0; bay < 8; bay++) {
          const x0 = bay * c + w.u0 * c;
          const x1 = bay * c + w.u1 * c;
          const y0 = top + (1 - w.v1) * c;
          const y1 = top + (1 - w.v0) * c;
          const on = rng.chance(litFraction);
          rowLit.push(on);

          // Stone lintel and sill.
          ctx.fillStyle = rgb(74, 68, 62);
          ctx.fillRect(x0 - c * 0.03, y0 - c * 0.05, x1 - x0 + c * 0.06, c * 0.05);
          ctx.fillRect(x0 - c * 0.05, y1, x1 - x0 + c * 0.1, c * 0.045);

          if (on) {
            const [r, g, b] = rng.pick(LIT);
            const dim = rng.range(0.55, 1);
            const grad = ctx.createLinearGradient(0, y0, 0, y1);
            grad.addColorStop(0, rgb(r * dim, g * dim, b * dim));
            grad.addColorStop(1, rgb(r * dim * 0.72, g * dim * 0.68, b * dim * 0.62));
            ctx.fillStyle = grad;
            ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
            // A blind pulled part of the way down, or a curtain to one side.
            if (rng.chance(0.55)) {
              ctx.fillStyle = rgb(r * 0.55, g * 0.5, b * 0.42, 0.75);
              ctx.fillRect(x0, y0, x1 - x0, (y1 - y0) * rng.range(0.2, 0.6));
            } else if (rng.chance(0.5)) {
              ctx.fillStyle = rgb(40, 28, 22, 0.55);
              ctx.fillRect(rng.chance(0.5) ? x0 : x0 + (x1 - x0) * 0.68, y0, (x1 - x0) * 0.32, y1 - y0);
            }
            // Someone, or something, on the sill.
            if (rng.chance(0.25)) {
              ctx.fillStyle = rgb(18, 14, 12, 0.85);
              const px = x0 + (x1 - x0) * rng.range(0.2, 0.7);
              ctx.fillRect(px, y1 - (y1 - y0) * rng.range(0.25, 0.5), (x1 - x0) * 0.16, (y1 - y0) * 0.5);
            }
          } else {
            const grad = ctx.createLinearGradient(0, y0, 0, y1);
            grad.addColorStop(0, rgb(30, 38, 54)); // a little sky in the glass
            grad.addColorStop(1, rgb(10, 12, 16));
            ctx.fillStyle = grad;
            ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
            if (rng.chance(0.3)) {
              ctx.fillStyle = rgb(60, 58, 60, 0.35); // a pale blind behind dark glass
              ctx.fillRect(x0, y0, x1 - x0, (y1 - y0) * rng.range(0.3, 0.9));
            }
          }
          // Sash bars.
          ctx.fillStyle = rgb(12, 11, 11);
          ctx.fillRect(x0, (y0 + y1) / 2 - 1, x1 - x0, Math.max(1, c * 0.02));
          ctx.fillRect((x0 + x1) / 2 - 1, y0, Math.max(1, c * 0.02), y1 - y0);
          // The odd air conditioner.
          if (rng.chance(0.14)) {
            ctx.fillStyle = rgb(66, 66, 64);
            ctx.fillRect(x0 + (x1 - x0) * 0.2, y1 - c * 0.13, (x1 - x0) * 0.6, c * 0.15);
            ctx.fillStyle = rgb(24, 24, 24);
            ctx.fillRect(x0 + (x1 - x0) * 0.26, y1 - c * 0.1, (x1 - x0) * 0.48, c * 0.07);
          }
        }
        lit.push(rowLit);
      }

      // Ground floor (bottom row of the canvas): a sign band over gates and shop fronts.
      const gy = 7 * c;
      ctx.fillStyle = rgb(26, 23, 22);
      ctx.fillRect(0, gy, S, c);
      const signs = [[255, 70, 150], [60, 220, 255], [255, 196, 60], [255, 60, 50], [90, 255, 150], [245, 240, 225]];
      for (let bay = 0; bay < 8; bay++) {
        const x0 = bay * c + c * 0.06;
        const bw = c * 0.88;
        const open = rng.chance(0.4);
        if (open) {
          const [r, g, b] = rng.pick(signs);
          // Lit sign band and its glow on the wall around it.
          const glow = ctx.createLinearGradient(0, gy, 0, gy + c * 0.34);
          glow.addColorStop(0, rgb(r, g, b, 0));
          glow.addColorStop(0.5, rgb(r, g, b, 0.45));
          glow.addColorStop(1, rgb(r, g, b, 0));
          ctx.fillStyle = glow;
          ctx.fillRect(bay * c, gy, c, c * 0.34);
          ctx.fillStyle = rgb(r, g, b);
          ctx.fillRect(x0 + bw * 0.08, gy + c * 0.12, bw * 0.84, c * 0.1);
          // Shop glass: warm inside, shelving as dark bars.
          const grad = ctx.createLinearGradient(0, gy + c * 0.3, 0, gy + c * 0.94);
          grad.addColorStop(0, rgb(255, 226, 170));
          grad.addColorStop(1, rgb(190, 150, 96));
          ctx.fillStyle = grad;
          ctx.fillRect(x0, gy + c * 0.3, bw, c * 0.64);
          ctx.fillStyle = rgb(30, 22, 16, 0.7);
          for (let k = 1; k < 4; k++) ctx.fillRect(x0, gy + c * (0.3 + 0.16 * k), bw, c * 0.03);
          ctx.fillRect(x0 + bw * rng.range(0.3, 0.6), gy + c * 0.3, bw * 0.05, c * 0.64);
        } else {
          // Roll-down gate.
          ctx.fillStyle = rgb(52, 54, 58);
          ctx.fillRect(x0, gy + c * 0.26, bw, c * 0.7);
          ctx.fillStyle = rgb(22, 23, 25, 0.8);
          for (let y = gy + c * 0.28; y < gy + c * 0.96; y += Math.max(2, c * 0.045)) ctx.fillRect(x0, y, bw, 1);
          if (rng.chance(0.6)) {
            ctx.strokeStyle = rgb(rng.range(90, 200), rng.range(60, 160), rng.range(60, 200), 0.5); // a tag
            ctx.lineWidth = Math.max(1, c * 0.025);
            ctx.beginPath();
            let px = x0 + bw * 0.15;
            let py = gy + c * rng.range(0.5, 0.75);
            ctx.moveTo(px, py);
            for (let k = 0; k < 5; k++) {
              px += bw * 0.14;
              py += c * rng.range(-0.12, 0.12);
              ctx.lineTo(px, py);
            }
            ctx.stroke();
          }
        }
        ctx.fillStyle = rgb(14, 13, 13);
        ctx.fillRect(bay * c, gy, c * 0.06, c); // pier between bays
      }
    },
    { repeatX: true },
  );
  return { texture, lit };
}

// ------------------------------------------------------------------------------------------------
// Skyline strips: a roof line with lit windows, cut out by alpha
// ------------------------------------------------------------------------------------------------

/**
 * @param {object} opts  {body: [r,g,b], lit: 0…1, tall: 0…1 (a cluster of towers mid-strip), dots: px}
 * @returns {{texture, towers: [{at, top}]}}  towers: tops (u, v) worth an aviation light
 */
export function skylineStrip(w, h, rng, { body = [15, 16, 22], lit = 0.2, tall = 0, variance = 0.3, base = 0.22 } = {}) {
  const { texture, result } = canvasTexture(
    w,
    h,
    (ctx, W, H) => {
      ctx.clearRect(0, 0, W, H);
      const colW = Math.max(2, Math.round(W / 256));
      const columns = Math.floor(W / colW);
      const { heights, towers } = skylineProfile(rng, columns, { base, variance, tall });

      let i = 0;
      while (i < columns) {
        // One building = a run of equal heights.
        let j = i;
        while (j < columns && heights[j] === heights[i]) j++;
        const x = i * colW;
        const bw = (j - i) * colW;
        const top = H - heights[i] * H;
        const shade = rng.range(0.82, 1.18);
        ctx.fillStyle = rgb(body[0] * shade, body[1] * shade, body[2] * shade);
        ctx.fillRect(x, top, bw, H - top);

        // Roof clutter: a tank, a bulkhead, a mast.
        if (bw > colW * 3 && rng.chance(0.45)) {
          const tw = Math.max(2, bw * rng.range(0.15, 0.3));
          ctx.fillRect(x + bw * rng.range(0.1, 0.6), top - H * 0.022, tw, H * 0.022);
        }
        if (rng.chance(0.18)) ctx.fillRect(x + bw * rng.range(0.2, 0.8), top - H * rng.range(0.03, 0.09), 1, H * 0.09);

        // Windows: a grid of dots, each building lit to its own taste.
        const mood = lit * rng.range(0.2, 2.2);
        const office = rng.chance(0.25);
        const stepX = Math.max(2, Math.round(H / 96));
        const stepY = Math.max(3, Math.round(H / 72));
        for (let wy = top + stepY; wy < H - stepY; wy += stepY) {
          const floorOn = office && rng.chance(0.2); // offices leave whole floors on
          for (let wx = x + 1; wx < x + bw - 1; wx += stepX) {
            if (!(floorOn ? rng.chance(0.85) : rng.chance(mood))) continue;
            const warm = rng.chance(office ? 0.25 : 0.72);
            const v = rng.range(0.45, 1);
            ctx.fillStyle = warm ? rgb(255 * v, 205 * v, 132 * v) : rgb(190 * v, 222 * v, 255 * v);
            ctx.fillRect(wx, wy, Math.max(1, stepX - 1), Math.max(1, stepY - 2));
          }
        }
        i = j;
      }
      return towers;
    },
    { repeatX: true, aniso: 2 },
  );
  return { texture, towers: result };
}

// ------------------------------------------------------------------------------------------------
// The subway car: one sheet for colour, one for what glows
//   top half     a car side (tiles once per car)
//   bottom left  a car end
//   bottom right bare steel (roof), and a black corner for the running gear
// ------------------------------------------------------------------------------------------------

export const CAR_UV = {
  side: [0, 0.5, 1, 1], // u0, v0, u1, v1
  end: [0, 0, 0.25, 0.5],
  steel: [0.3, 0.3, 0.7, 0.45],
  dark: [0.8, 0.05, 0.95, 0.2],
};

export function carSheets(size, rng) {
  const W = size;
  const H = size / 2;
  // Window and door layout along a 15.4 m side, in fractions of the length.
  const doors = [0.115, 0.37, 0.63, 0.885];
  const doorW = 0.085;
  const panes = [];
  let cursor = 0.025;
  for (const d of doors) {
    const end = d - doorW / 2 - 0.012;
    const n = Math.max(1, Math.round((end - cursor) / 0.1));
    const pw = (end - cursor) / n;
    for (let k = 0; k < n; k++) panes.push([cursor + pw * k + 0.008, cursor + pw * (k + 1) - 0.008]);
    cursor = d + doorW / 2 + 0.012;
  }
  panes.push([cursor + 0.008, 0.975]);

  const sideH = H / 2; // the side strip occupies the top half of the canvas
  const band = [0.2, 0.52]; // window band, from the top of the strip

  const map = canvasTexture(W, H, (ctx) => {
    // Steel everywhere first (also the roof patch).
    ctx.fillStyle = rgb(118, 123, 130);
    ctx.fillRect(0, 0, W, H);
    // Side: fluted lower panels, a darker skirt, a belt line.
    const flute = Math.max(2, Math.round(sideH / 40));
    ctx.fillStyle = rgb(70, 74, 80, 0.5);
    for (let y = sideH * 0.58; y < sideH * 0.9; y += flute) ctx.fillRect(0, y, W, 1);
    ctx.fillStyle = rgb(34, 36, 40);
    ctx.fillRect(0, sideH * 0.9, W, sideH * 0.1);
    ctx.fillStyle = rgb(24, 40, 96);
    ctx.fillRect(0, sideH * 0.55, W, sideH * 0.03);
    ctx.fillStyle = rgb(88, 92, 98);
    ctx.fillRect(0, 0, W, sideH * 0.08); // roof edge
    // Grime, heavier toward the bottom.
    const grime = ctx.createLinearGradient(0, 0, 0, sideH);
    grime.addColorStop(0, rgb(20, 16, 12, 0.05));
    grime.addColorStop(1, rgb(20, 16, 12, 0.4));
    ctx.fillStyle = grime;
    ctx.fillRect(0, 0, W, sideH);
    for (let i = 0; i < 90; i++) {
      ctx.fillStyle = rgb(18, 15, 12, rng.range(0.04, 0.14));
      ctx.fillRect(rng.next() * W, sideH * rng.range(0.1, 0.9), 1 + rng.next() * 2, sideH * rng.range(0.05, 0.3));
    }
    // Glass and door outlines (the glow sheet lights them).
    ctx.fillStyle = rgb(16, 20, 24);
    for (const [a, b] of panes) ctx.fillRect(a * W, band[0] * sideH, (b - a) * W, (band[1] - band[0]) * sideH);
    for (const d of doors) {
      const x0 = (d - doorW / 2) * W;
      const dw = doorW * W;
      ctx.fillStyle = rgb(96, 100, 106);
      ctx.fillRect(x0, sideH * 0.12, dw, sideH * 0.78);
      ctx.fillStyle = rgb(30, 32, 36);
      ctx.fillRect(x0 + dw / 2 - 1, sideH * 0.12, 2, sideH * 0.78);
      ctx.strokeStyle = rgb(30, 32, 36);
      ctx.lineWidth = 1;
      ctx.strokeRect(x0, sideH * 0.12, dw, sideH * 0.78);
      ctx.fillStyle = rgb(16, 20, 24);
      ctx.fillRect(x0 + dw * 0.1, sideH * 0.2, dw * 0.33, sideH * 0.3);
      ctx.fillRect(x0 + dw * 0.57, sideH * 0.2, dw * 0.33, sideH * 0.3);
    }
    // End: bottom-left quarter. A door between two windows, an anticlimber bar.
    const ex = 0;
    const ey = sideH;
    const ew = W * 0.25;
    const eh = sideH;
    ctx.fillStyle = rgb(104, 108, 114);
    ctx.fillRect(ex, ey, ew, eh);
    ctx.fillStyle = rgb(60, 63, 68);
    ctx.fillRect(ex + ew * 0.36, ey + eh * 0.12, ew * 0.28, eh * 0.76);
    ctx.fillStyle = rgb(16, 20, 24);
    ctx.fillRect(ex + ew * 0.4, ey + eh * 0.2, ew * 0.2, eh * 0.3);
    ctx.fillRect(ex + ew * 0.08, ey + eh * 0.2, ew * 0.22, eh * 0.3);
    ctx.fillRect(ex + ew * 0.7, ey + eh * 0.2, ew * 0.22, eh * 0.3);
    ctx.fillStyle = rgb(30, 32, 36);
    ctx.fillRect(ex, ey + eh * 0.88, ew, eh * 0.12);
    // Running gear: black.
    ctx.fillStyle = rgb(14, 14, 15);
    ctx.fillRect(W * 0.75, H * 0.75, W * 0.25, H * 0.25);
  });

  const glow = canvasTexture(W, H, (ctx) => {
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);
    const y0 = band[0] * sideH;
    const bh = (band[1] - band[0]) * sideH;
    const paint = (x, y, w, h) => {
      const grad = ctx.createLinearGradient(0, y, 0, y + h);
      grad.addColorStop(0, rgb(255, 255, 255));
      grad.addColorStop(0.55, rgb(214, 220, 214));
      grad.addColorStop(1, rgb(120, 126, 124)); // seat backs
      ctx.fillStyle = grad;
      ctx.fillRect(x, y, w, h);
    };
    for (const [a, b] of panes) {
      const x = a * W;
      const pw = (b - a) * W;
      paint(x, y0, pw, bh);
      ctx.fillStyle = '#000';
      ctx.fillRect(x + pw * rng.range(0.3, 0.7), y0, Math.max(1, pw * 0.04), bh); // a grab pole
      if (rng.chance(0.3)) {
        // A rider: head and shoulders against the light.
        const px = x + pw * rng.range(0.15, 0.7);
        ctx.fillRect(px, y0 + bh * 0.45, pw * 0.2, bh * 0.55);
        ctx.beginPath();
        ctx.arc(px + pw * 0.1, y0 + bh * 0.4, pw * 0.075, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    for (const d of doors) {
      const x0 = (d - doorW / 2) * W;
      const dw = doorW * W;
      paint(x0 + dw * 0.1, sideH * 0.2, dw * 0.33, sideH * 0.3);
      paint(x0 + dw * 0.57, sideH * 0.2, dw * 0.33, sideH * 0.3);
    }
    // End windows, and an amber destination bar over the door.
    const ey = sideH;
    const ew = W * 0.25;
    const eh = sideH;
    paint(ew * 0.4, ey + eh * 0.2, ew * 0.2, eh * 0.3);
    paint(ew * 0.08, ey + eh * 0.2, ew * 0.22, eh * 0.3);
    paint(ew * 0.7, ey + eh * 0.2, ew * 0.22, eh * 0.3);
    ctx.fillStyle = rgb(255, 150, 30);
    ctx.fillRect(ew * 0.38, ey + eh * 0.05, ew * 0.24, eh * 0.05);
  });

  return { map: map.texture, emissiveMap: glow.texture };
}

// ------------------------------------------------------------------------------------------------
// Loose paper
// ------------------------------------------------------------------------------------------------

export function paperTexture(rng) {
  return canvasTexture(64, 96, (ctx, W, H) => {
    ctx.fillStyle = rgb(196, 190, 174);
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = rgb(40, 38, 36, 0.75);
    ctx.fillRect(W * 0.1, H * 0.08, W * 0.8, H * 0.12); // a headline
    ctx.fillStyle = rgb(60, 58, 54, 0.5);
    for (let y = H * 0.28; y < H * 0.92; y += 5) ctx.fillRect(W * 0.1, y, W * rng.range(0.5, 0.8), 2);
    ctx.fillStyle = rgb(90, 70, 40, 0.25);
    ctx.fillRect(0, H * rng.range(0.4, 0.7), W, H * 0.2); // a stain
  }).texture;
}
