// Ground and wall decals: stains, damage and road paint as transparent quads.
//
//   oil, crack, manhole, grime, scorch, bullet      one painting per variant, mapped once over w × h
//   crosswalk                                       ladder bars, repeats along u (any width)
//   arrow                                           a lane arrow
//   lane, lane_yellow                               worn road paint that tiles both ways: the quad is the line
//   puddle                                          standing water: dark, flat and mirror-smooth
//
// Each entry gives the size in metres, the surface response and how the texture wraps.

import { canvas2d, css, erase, stain } from './canvas.js';
import { prng } from './noise.js';

const TAU = Math.PI * 2;

/** kind → {size [w, h] metres, roughness, metalness, wrap, variants, ppm (pixels per metre at the top tier)} */
export const DECALS = {
  oil: { size: [1.6, 1.2], roughness: 0.16, variants: 3, ppm: 150 },
  crack: { size: [2, 0.6], roughness: 0.95, variants: 3, ppm: 200 },
  manhole: { size: [0.9, 0.9], roughness: 0.55, metalness: 0.65, variants: 1, ppm: 420 },
  grime: { size: [2, 2], roughness: 0.95, variants: 3, ppm: 100 },
  scorch: { size: [3, 3], roughness: 1, variants: 2, ppm: 110 },
  bullet: { size: [0.12, 0.12], roughness: 0.9, variants: 3, ppm: 1024 },
  crosswalk: { size: [4, 3], roughness: 0.6, variants: 1, ppm: 110, wrap: ['repeat', 'clamp'] },
  arrow: { size: [1.2, 3], roughness: 0.6, variants: 1, ppm: 150 },
  lane: { size: [0.12, 3], roughness: 0.6, variants: 1, ppm: 256, tile: 1 },
  lane_yellow: { size: [0.12, 3], roughness: 0.6, variants: 1, ppm: 256, tile: 1 },
  puddle: { size: [2.4, 1.6], roughness: 0.04, variants: 3, ppm: 100 },
};

const TIER = { 256: 0.34, 512: 0.6, 1024: 1 };

export function createDecalPainter(env) {
  const { size, bank } = env;

  /** A soft-edged irregular blob: several overlapping lobes of radial gradient. */
  function blob(A, cx, cy, r, rand, inner, outer, lobes = 7) {
    for (let i = 0; i < lobes; i++) {
      const a = rand() * TAU;
      const d = rand() * r * 0.55;
      const x = cx + Math.cos(a) * d;
      const y = cy + Math.sin(a) * d;
      const rr = r * (0.35 + rand() * 0.45);
      const g = A.createRadialGradient(x, y, 0, x, y, rr);
      g.addColorStop(0, inner);
      g.addColorStop(0.6, inner);
      g.addColorStop(1, outer);
      A.fillStyle = g;
      A.beginPath();
      A.arc(x, y, rr, 0, TAU);
      A.fill();
    }
  }

  /** Fades the whole canvas out toward its edges so no decal ends on a hard line. */
  function vignette(A, cw, ch, start = 0.55) {
    A.save();
    A.globalCompositeOperation = 'destination-in';
    A.translate(cw / 2, ch / 2);
    A.scale(cw / 2, ch / 2);
    const g = A.createRadialGradient(0, 0, start, 0, 0, 1);
    g.addColorStop(0, 'rgba(0,0,0,1)');
    g.addColorStop(1, 'rgba(0,0,0,0)');
    A.fillStyle = g;
    A.fillRect(-1, -1, 2, 2);
    A.restore();
  }

  /** Road paint worn by tyres: scuffs, pinholes, a cracked crust. */
  function wear(A, cw, ch, amount = 1) {
    erase(A, bank.mask('fine', 0.66, 0.88), Math.max(1, Math.round(cw / 200)), Math.max(1, Math.round(ch / 200)), { alpha: 0.55 * amount });
    erase(A, bank.mask('clouds', 0.64, 0.9), 1, 1, { alpha: 0.5 * amount });
    erase(A, bank.mask('ridges', 0.86, 0.96), 1, 1, { alpha: 0.6 * amount });
    // Dirt on what is left ('source-atop' keeps the holes clear).
    stain(A, bank.mask('clouds', 0.4, 0.9), 'rgb(52,50,46)', { alpha: 0.3, mode: 'source-atop' });
  }

  const PAINTERS = {
    /** Sump oil: black at the heart, a rainbow film at the rim. */
    oil(A, cw, ch, rand) {
      const r = Math.min(cw, ch) * 0.46;
      blob(A, cw / 2, ch / 2, r, rand, 'rgba(6,6,8,0.78)', 'rgba(6,6,8,0)', 9);
      A.save();
      A.globalCompositeOperation = 'source-atop';
      // The film: broken arcs of colour, barely there.
      for (const [k, tint] of [[0.95, 'rgba(120,60,160,0.13)'], [0.8, 'rgba(40,150,150,0.12)'], [0.64, 'rgba(190,150,40,0.1)']]) {
        A.strokeStyle = tint;
        A.lineWidth = r * (0.08 + rand() * 0.1);
        const from = rand() * TAU;
        A.beginPath();
        A.ellipse(cw / 2 + (rand() - 0.5) * r * 0.3, ch / 2 + (rand() - 0.5) * r * 0.3, r * k, r * k * (0.6 + rand() * 0.25), rand() * 3, from, from + 2 + rand() * 3);
        A.stroke();
      }
      A.restore();
      vignette(A, cw, ch, 0.7);
    },

    /** A crack that has opened along the road and branched. */
    crack(A, cw, ch, rand) {
      const branch = (rng, x, y, angle, len, wide, depth) => {
        A.lineWidth = wide;
        A.beginPath();
        A.moveTo(x, y);
        const step = cw * 0.02;
        const forks = [];
        for (let d = 0; d < len; d += step) {
          angle = (angle + (rng() - 0.5) * 0.7) * 0.88; // keeps drifting back along the main direction
          x += Math.cos(angle) * step;
          y += Math.sin(angle) * step;
          A.lineTo(x, y);
          if (depth === 0 && rng() < 0.1) forks.push([x, y, angle + (rng() < 0.5 ? 1 : -1) * (0.6 + rng() * 0.5)]);
        }
        A.stroke();
        for (const [fx, fy, fa] of forks) branch(rng, fx, fy, fa, len * 0.25, wide * 0.55, 1);
      };
      A.lineCap = 'round';
      A.lineJoin = 'round';
      const wide = Math.max(1.5, ch * 0.035);
      const seed = Math.floor(rand() * 1e6);
      const y0 = ch * (0.4 + rand() * 0.2);
      // The same crack twice: its crumbled shoulders, then the dark gap itself.
      for (const [style, k] of [['rgba(120,118,110,0.35)', 2.4], ['rgba(8,8,9,0.9)', 1]]) {
        A.strokeStyle = style;
        branch(prng(seed), cw * 0.04, y0, 0, cw * 0.9, wide * k, 0);
      }
      vignette(A, cw, ch, 0.8);
    },

    /** Cast-iron cover: rim, waffle tread, two pick holes, set in a collar of patched tar. */
    manhole(A, cw, ch, rand) {
      const cx = cw / 2;
      const cy = ch / 2;
      const r = cw * 0.47;
      const g = A.createRadialGradient(cx, cy, r * 0.9, cx, cy, cw * 0.5);
      g.addColorStop(0, 'rgba(10,10,11,0.85)');
      g.addColorStop(1, 'rgba(10,10,11,0)');
      A.fillStyle = g;
      A.fillRect(0, 0, cw, ch);
      A.fillStyle = css(0x2a2b2d);
      A.beginPath();
      A.arc(cx, cy, r * 0.94, 0, TAU);
      A.fill();
      // Tread: raised squares, lit from the upper left.
      A.save();
      A.beginPath();
      A.arc(cx, cy, r * 0.8, 0, TAU);
      A.clip();
      const cell = r * 0.16;
      for (let y = cy - r; y < cy + r; y += cell) {
        for (let x = cx - r; x < cx + r; x += cell) {
          A.fillStyle = 'rgba(0,0,0,0.55)';
          A.fillRect(x + cell * 0.2, y + cell * 0.2, cell * 0.72, cell * 0.72);
          A.fillStyle = css(0x47484a);
          A.fillRect(x + cell * 0.12, y + cell * 0.12, cell * 0.68, cell * 0.68);
          A.fillStyle = 'rgba(255,255,255,0.12)';
          A.fillRect(x + cell * 0.12, y + cell * 0.12, cell * 0.68, cell * 0.12);
        }
      }
      A.restore();
      for (const [rr, style, wide] of [[0.94, 'rgba(0,0,0,0.7)', 0.03], [0.87, css(0x55575a), 0.045], [0.8, 'rgba(0,0,0,0.6)', 0.02], [0.3, css(0x505255), 0.04]]) {
        A.strokeStyle = style;
        A.lineWidth = r * wide;
        A.beginPath();
        A.arc(cx, cy, r * rr, 0, TAU);
        A.stroke();
      }
      for (const sx of [-1, 1]) {
        A.fillStyle = 'rgba(0,0,0,0.9)';
        A.beginPath();
        A.ellipse(cx + sx * r * 0.58, cy, r * 0.07, r * 0.035, 0, 0, TAU);
        A.fill();
      }
      stain(A, bank.mask('mottle', 0.5, 0.85), 'rgb(92,58,36)', { alpha: 0.3, mode: 'source-atop', ox: rand() });
    },

    /** Ground-in dirt: where bins stood, where a car dripped for a year. */
    grime(A, cw, ch, rand) {
      blob(A, cw / 2, ch / 2, cw * 0.44, rand, 'rgba(10,9,8,0.5)', 'rgba(10,9,8,0)', 10);
      erase(A, bank.mask('clouds', 0.45, 0.85), 1, 1, { alpha: 0.75, ox: rand(), oy: rand() });
      erase(A, bank.mask('mottle', 0.55, 0.9), 2, 2, { alpha: 0.35, ox: rand(), oy: rand() });
      vignette(A, cw, ch, 0.5);
    },

    /** Blast mark: soot thrown outward from a burnt centre. */
    scorch(A, cw, ch, rand) {
      const cx = cw / 2;
      const cy = ch / 2;
      const g = A.createRadialGradient(cx, cy, 0, cx, cy, cw * 0.5);
      g.addColorStop(0, 'rgba(4,4,4,0.92)');
      g.addColorStop(0.25, 'rgba(8,7,6,0.8)');
      g.addColorStop(0.55, 'rgba(24,18,12,0.4)');
      g.addColorStop(1, 'rgba(24,18,12,0)');
      A.fillStyle = g;
      A.fillRect(0, 0, cw, ch);
      for (let i = 0; i < 46; i++) {
        const a = rand() * TAU;
        const len = cw * (0.22 + rand() * 0.26);
        const wide = 0.03 + rand() * 0.08;
        const ray = A.createLinearGradient(cx, cy, cx + Math.cos(a) * len, cy + Math.sin(a) * len);
        ray.addColorStop(0, 'rgba(5,5,5,0.6)');
        ray.addColorStop(1, 'rgba(5,5,5,0)');
        A.fillStyle = ray;
        A.beginPath();
        A.moveTo(cx, cy);
        A.lineTo(cx + Math.cos(a - wide) * len, cy + Math.sin(a - wide) * len);
        A.lineTo(cx + Math.cos(a + wide) * len, cy + Math.sin(a + wide) * len);
        A.fill();
      }
      erase(A, bank.mask('fine', 0.6, 0.9), 3, 3, { alpha: 0.4 });
      vignette(A, cw, ch, 0.6);
    },

    /** A round through masonry: a dark hole in a pale crater with hairline cracks. */
    bullet(A, cw, ch, rand) {
      const cx = cw / 2;
      const cy = ch / 2;
      const r = cw * 0.5;
      blob(A, cx, cy, r * 0.72, rand, 'rgba(176,170,158,0.75)', 'rgba(176,170,158,0)', 6);
      A.strokeStyle = 'rgba(12,12,12,0.7)';
      A.lineWidth = Math.max(1, cw * 0.016);
      for (let i = 0; i < 6; i++) {
        const a = rand() * TAU;
        A.beginPath();
        A.moveTo(cx + Math.cos(a) * r * 0.15, cy + Math.sin(a) * r * 0.15);
        A.lineTo(cx + Math.cos(a + (rand() - 0.5) * 0.4) * r * (0.5 + rand() * 0.4), cy + Math.sin(a + (rand() - 0.5) * 0.4) * r * (0.5 + rand() * 0.4));
        A.stroke();
      }
      const g = A.createRadialGradient(cx, cy, 0, cx, cy, r * 0.3);
      g.addColorStop(0, 'rgba(0,0,0,1)');
      g.addColorStop(0.7, 'rgba(8,8,8,0.95)');
      g.addColorStop(1, 'rgba(8,8,8,0)');
      A.fillStyle = g;
      A.beginPath();
      A.arc(cx, cy, r * 0.3, 0, TAU);
      A.fill();
    },

    /** Ladder crossing: one bar per metre, 0.45 m wide, running the depth of the quad. */
    crosswalk(A, cw, ch) {
      const bars = 4;
      A.fillStyle = 'rgb(226,224,214)';
      for (let i = 0; i < bars; i++) A.fillRect(((i + 0.275) * cw) / bars, ch * 0.02, (cw / bars) * 0.45, ch * 0.96);
      wear(A, cw, ch, 1);
    },

    /** Straight-ahead lane arrow. */
    arrow(A, cw, ch) {
      A.fillStyle = 'rgb(226,224,214)';
      A.beginPath();
      A.moveTo(cw * 0.5, ch * 0.02);
      A.lineTo(cw * 0.96, ch * 0.4);
      A.lineTo(cw * 0.66, ch * 0.4);
      A.lineTo(cw * 0.62, ch * 0.98);
      A.lineTo(cw * 0.38, ch * 0.98);
      A.lineTo(cw * 0.34, ch * 0.4);
      A.lineTo(cw * 0.04, ch * 0.4);
      A.closePath();
      A.fill();
      wear(A, cw, ch, 0.9);
    },

    lane(A, cw, ch) {
      A.fillStyle = 'rgb(226,224,214)';
      A.fillRect(0, 0, cw, ch);
      wear(A, cw, ch, 0.8);
    },

    lane_yellow(A, cw, ch) {
      A.fillStyle = 'rgb(222,170,28)';
      A.fillRect(0, 0, cw, ch);
      wear(A, cw, ch, 0.8);
    },

    /** Standing water. Nearly black: what you see in it is the reflection. */
    puddle(A, cw, ch, rand) {
      blob(A, cw / 2, ch / 2, Math.min(cw, ch) * 0.5, rand, 'rgba(6,8,12,0.82)', 'rgba(6,8,12,0)', 11);
      // A firm shoreline: only the well-covered middle of the blob survives.
      const image = A.getImageData(0, 0, cw, ch);
      const data = image.data;
      for (let i = 3; i < data.length; i += 4) {
        const a = data[i] / 255;
        const t = a < 0.42 ? 0 : a > 0.6 ? 1 : (a - 0.42) / 0.18;
        data[i] = t * t * (3 - 2 * t) * 205;
      }
      A.putImageData(image, 0, 0);
    },
  };

  /**
   * Paints decal `kind`, variant `v`: {canvas, w, h, def}.
   * Tiling paints (`def.tile`) come back as a square tile of `def.tile` metres.
   */
  function decal(kind, v) {
    const def = DECALS[kind];
    const [w, h] = def.size;
    const ppm = Math.min(def.ppm * (TIER[size] || 1), (size * 1.5) / Math.max(def.tile || w, def.tile || h));
    const cw = Math.max(16, Math.round((def.tile || w) * ppm));
    const ch = Math.max(16, Math.round((def.tile || h) * ppm));
    const A = canvas2d(cw, ch, kind === 'puddle');
    PAINTERS[kind](A, cw, ch, prng(500 + v * 7919 + kind.length * 31));
    return { canvas: A.canvas, w, h, def };
  }

  return { decal };
}
