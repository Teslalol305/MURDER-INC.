// Procedural atlases for the effects, painted pixel by pixel (no canvas, no files).
//
// Three sheets of 4 × 2 cells:
//   lit       smoke, dust, steam, lint          R = density, G = internal shading
//   additive  glow, streak, flash, flame, ember R = intensity, G = white-hot core
//   decals    bullet holes by surface, scorch   RGB = albedo (linear), A = opacity
// Every cell fades to nothing before its border, so mip levels never bleed into a neighbour.
// The painters are pure functions of (u, v) in −1…1: the sheets are the same on every machine.

export const COLS = 4;
export const ROWS = 2;

// Cells of the lit sheet.
export const LIT = { smokeA: 0, smokeB: 1, smokeC: 2, wisp: 3, dust: 4, steam: 5, lint: 6, roll: 7 };
// Cells of the additive sheet.
export const ADD = { glow: 0, streak: 1, star: 2, flameA: 3, flameB: 4, ember: 5, glint: 6, ring: 7 };
// Cells of the decal sheet.
export const DECAL = { stone: 0, brick: 1, metal: 2, glass: 3, wood: 4, soot: 5, scorchA: 6, scorchB: 7 };

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const smooth = (a, b, x) => {
  const t = clamp01((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};

function hash(x, y, seed) {
  let h = (Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(seed, 1442695041)) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

/** Smooth value noise, 0…1. */
function noise(x, y, seed) {
  const xi = Math.floor(x);
  const yi = Math.floor(y);
  const xf = x - xi;
  const yf = y - yi;
  const u = xf * xf * (3 - 2 * xf);
  const v = yf * yf * (3 - 2 * yf);
  const a = hash(xi, yi, seed);
  const b = hash(xi + 1, yi, seed);
  const c = hash(xi, yi + 1, seed);
  const e = hash(xi + 1, yi + 1, seed);
  return a + (b - a) * u + (c - a) * v + (a - b - c + e) * u * v;
}

/** Fractal noise, 0…1. */
function fbm(x, y, seed, octaves = 4) {
  let sum = 0;
  let amp = 0.5;
  let norm = 0;
  for (let i = 0; i < octaves; i++) {
    sum += noise(x, y, seed + i * 17) * amp;
    norm += amp;
    x = x * 2.03 + 11.7;
    y = y * 2.03 - 5.3;
    amp *= 0.5;
  }
  return sum / norm;
}

/** 1 inside the cell, falling to 0 just before its border. */
const windowed = (r) => 1 - smooth(0.8, 0.97, r);

// ------------------------------------------------------------------------------------------------
// Lit sheet: [density, shading]
// ------------------------------------------------------------------------------------------------

/** A billowing puff: a ball whose surface is pushed in and out by noise. */
function puff(seed, lumpiness, softness) {
  return (u, v, out) => {
    const r = Math.hypot(u, v);
    const n = fbm(u * 2.1 + seed, v * 2.1 - seed * 0.7, seed, 4);
    const body = clamp01((0.86 - r - (0.5 - n) * lumpiness) / softness);
    const density = body * body * (3 - 2 * body) * windowed(r);
    // Shading: lumps catch light on their upper left, creases stay dark.
    const lump = fbm(u * 3.4 - seed, v * 3.4 + seed * 1.3, seed + 5, 3);
    out[0] = density;
    out[1] = clamp01(0.42 + lump * 0.7 + v * 0.18 - u * 0.06);
  };
}

function wisp(u, v, out) {
  const r = Math.hypot(u, v);
  // Ridged noise: thin curling strands.
  const a = Math.abs(fbm(u * 2.6 + 3.1, v * 2.6 + 8.2, 41, 4) - 0.5) * 2;
  const strands = clamp01(1 - a * 2.6);
  out[0] = strands * strands * clamp01(1.15 - r * 1.25) * windowed(r);
  out[1] = 0.6 + 0.4 * fbm(u * 4 + 1.3, v * 4 - 2.2, 43, 2);
}

function dust(u, v, out) {
  const r = Math.hypot(u, v);
  const grain = fbm(u * 5.2 + 2.2, v * 5.2 - 1.4, 53, 4);
  out[0] = Math.exp(-r * r * 3.4) * (0.5 + 0.65 * grain) * windowed(r);
  out[1] = 0.6 + 0.4 * grain;
}

function steam(u, v, out) {
  const r = Math.hypot(u, v);
  const soft = fbm(u * 1.7 + 6.1, v * 1.7 + 0.4, 61, 3);
  out[0] = Math.exp(-r * r * 2.7) * (0.62 + 0.5 * soft) * windowed(r);
  out[1] = 0.72 + 0.28 * soft;
}

/** Lint and grit: a scatter of specks in a faint cloud (cloth and body hits). */
function lint(u, v, out) {
  const r = Math.hypot(u, v);
  // One speck per cell of a jittered grid, most cells empty.
  const grid = 7;
  const gx = (u + 1) * grid;
  const gy = (v + 1) * grid;
  let speck = 0;
  for (let j = -1; j <= 1; j++) {
    for (let i = -1; i <= 1; i++) {
      const cx = Math.floor(gx) + i;
      const cy = Math.floor(gy) + j;
      if (hash(cx, cy, 71) > 0.55) continue;
      const px = cx + 0.2 + 0.6 * hash(cx, cy, 72);
      const py = cy + 0.2 + 0.6 * hash(cx, cy, 73);
      const radius = 0.1 + 0.2 * hash(cx, cy, 74);
      speck = Math.max(speck, 1 - smooth(radius * 0.4, radius, Math.hypot(gx - px, gy - py)));
    }
  }
  const cloud = Math.exp(-r * r * 3.2) * 0.26 * (0.5 + fbm(u * 3 + 9, v * 3 + 2, 75, 3));
  out[0] = clamp01(speck * clamp01(1.25 - r * 1.4) + cloud) * windowed(r);
  out[1] = 0.85;
}

/** A low rolling bank: wide, flat-bottomed (ground dust rings, kicked-up dirt). */
function roll(u, v, out) {
  const r = Math.hypot(u, v * 1.7 - 0.25);
  const n = fbm(u * 2.4 + 12.5, v * 2.4 + 3.3, 83, 4);
  const body = clamp01((0.84 - r - (0.5 - n) * 0.6) / 0.5);
  out[0] = body * body * (3 - 2 * body) * windowed(Math.hypot(u, v));
  out[1] = clamp01(0.45 + n * 0.6 + v * 0.2);
}

// ------------------------------------------------------------------------------------------------
// Additive sheet: [intensity, white core]
// ------------------------------------------------------------------------------------------------

function glow(u, v, out) {
  const r2 = u * u + v * v;
  out[0] = Math.exp(-r2 * 4.6) * windowed(Math.sqrt(r2));
  out[1] = Math.exp(-r2 * 22);
}

/** A streak for velocity-stretched quads: the head is at +v, the tail thins out toward −v. */
function streak(u, v, out) {
  const along = smooth(-0.98, 0.45, v) * (1 - smooth(0.6, 0.94, v));
  const width = 0.16 + 0.2 * smooth(-1, 0.7, v);
  const across = Math.exp(-(u * u) / (width * width));
  out[0] = across * along * (1 - smooth(0.82, 0.98, Math.abs(u)));
  out[1] = Math.exp(-(u * u) / (width * width * 0.25)) * smooth(-0.1, 0.6, v) * (1 - smooth(0.6, 0.9, v));
}

/** Muzzle flash seen head on: a hot ball with uneven spikes. */
function star(u, v, out) {
  const r = Math.hypot(u, v);
  const angle = Math.atan2(v, u);
  const lobes = Math.pow(Math.abs(Math.cos(angle * 2.5 + 0.4)), 6) * 0.6 + Math.pow(Math.abs(Math.cos(angle * 3.5 - 1.1)), 12) * 0.5;
  const reach = 0.3 + lobes * (0.5 + 0.3 * noise(angle * 3 + 20, 0.5, 91));
  out[0] = clamp01(Math.exp(-(r * r) / (reach * reach)) * 1.15) * windowed(r);
  out[1] = Math.exp(-r * r * 26);
}

/** A ball of flame: bright where the noise is dense, torn at the edge. */
function flame(seed) {
  return (u, v, out) => {
    const r = Math.hypot(u * 1.06, v);
    const n = fbm(u * 2.4 + seed * 1.7, v * 2.4 - seed, seed, 4);
    const fine = fbm(u * 5.5 - seed, v * 5.5 + seed * 2.1, seed + 9, 3);
    const body = clamp01((0.9 - r - (0.5 - n) * 0.95) / 0.5);
    const density = body * body * (0.65 + 0.5 * fine) * windowed(r);
    out[0] = clamp01(density);
    out[1] = clamp01((density - 0.82) * 2.5);
  };
}

function ember(u, v, out) {
  const r2 = u * u + v * v;
  out[0] = clamp01(Math.exp(-r2 * 26) + 0.2 * Math.exp(-r2 * 4.5)) * windowed(Math.sqrt(r2));
  out[1] = Math.exp(-r2 * 60);
}

/** A four-point glint (glass shards, electric sparks at rest). */
function glint(u, v, out) {
  const au = Math.abs(u);
  const av = Math.abs(v);
  const cross = Math.exp(-au * 16) * Math.exp(-av * 3.4) + Math.exp(-av * 16) * Math.exp(-au * 3.4);
  const r = Math.hypot(u, v);
  out[0] = clamp01(cross + Math.exp(-r * r * 40)) * windowed(r);
  out[1] = Math.exp(-r * r * 70);
}

function ring(u, v, out) {
  const r = Math.hypot(u, v);
  const band = (r - 0.74) / 0.075;
  const breakup = 0.65 + 0.35 * noise(Math.atan2(v, u) * 4 + 30, 0.5, 97);
  out[0] = Math.exp(-band * band) * breakup * windowed(r);
  out[1] = 0;
}

// ------------------------------------------------------------------------------------------------
// Decal sheet: [r, g, b, a], albedo in linear light
// ------------------------------------------------------------------------------------------------

/**
 * A bullet strike in masonry: a dark pit, a ragged crater of freshly broken material around it and a
 * thin halo of dust. `chip` is the colour of the broken face.
 */
function crater(seed, chip) {
  return (u, v, out) => {
    const r = Math.hypot(u, v);
    const angle = Math.atan2(v, u);
    const ragged = 0.36 + 0.2 * noise(angle * 2.2 + seed, 1.5, seed) + 0.1 * noise(angle * 6 + seed * 2, 4.5, seed + 3);
    // A dark pit big enough to read from across a sunlit street, broken masonry around it in the
    // shadow of the crater, and a sooty powder halo that darkens the wall further out.
    const pit = 1 - smooth(0.11, 0.22, r);
    const broken = (1 - smooth(ragged - 0.1, ragged, r)) * (0.75 + 0.25 * fbm(u * 7 + seed, v * 7, seed + 7, 2));
    const halo = (1 - smooth(ragged * 0.8, 0.9, r)) * (0.3 + 0.25 * fbm(u * 4 - seed, v * 4 + seed, seed + 11, 3));
    const shade = (0.65 + 0.5 * fbm(u * 9, v * 9 + seed, seed + 13, 2) - v * 0.12) * (0.45 + 0.4 * smooth(0.2, ragged, r));
    const alpha = clamp01(Math.max(pit * 0.97, broken * 0.85, halo));
    const chipped = broken > halo ? 1 : 0.15; // beyond the broken edge only soot remains
    const mix = pit;
    out[0] = (chip[0] * shade * chipped + 0.02 * (1 - chipped)) * (1 - mix) + 0.012 * mix;
    out[1] = (chip[1] * shade * chipped + 0.018 * (1 - chipped)) * (1 - mix) + 0.011 * mix;
    out[2] = (chip[2] * shade * chipped + 0.016 * (1 - chipped)) * (1 - mix) + 0.01 * mix;
    out[3] = alpha * windowed(r);
  };
}

/** A hole punched through sheet metal: black hole, a rim of bare metal, flaked paint, a little soot. */
function metalHole(u, v, out) {
  const r = Math.hypot(u, v);
  const angle = Math.atan2(v, u);
  const edge = 0.17 + 0.035 * noise(angle * 3 + 7, 2.5, 101);
  const hole = 1 - smooth(edge - 0.035, edge, r);
  const rim = smooth(edge - 0.02, edge + 0.02, r) * (1 - smooth(edge + 0.06, edge + 0.13, r));
  const flake = (1 - smooth(0.24, 0.5 + 0.2 * noise(angle * 4 + 2, 6.5, 103), r)) * 0.55;
  const soot = (1 - smooth(0.3, 0.86, r)) * 0.28 * (0.5 + noise(angle * 9, r * 3, 107));
  const bare = 0.42 + 0.3 * noise(angle * 14, r * 9, 109);
  const alpha = clamp01(Math.max(hole, rim * 0.92, flake, soot));
  const tone = hole > 0.5 ? 0.006 : rim > 0.4 ? bare : flake > soot ? 0.1 : 0.02;
  out[0] = tone;
  out[1] = tone * 0.97;
  out[2] = tone * (rim > 0.4 ? 1.04 : 0.94);
  out[3] = alpha * windowed(r);
}

/** Shot glass: a small hole, a crushed white ring and long radial cracks joined by a few rings. */
function glassCrack(u, v, out) {
  const r = Math.hypot(u, v);
  const angle = Math.atan2(v, u);
  let line = 0;
  for (let i = 0; i < 9; i++) {
    const a = (i / 9) * Math.PI * 2 - Math.PI + hash(i, 3, 113) * 0.5;
    const reach = 0.45 + 0.42 * hash(i, 7, 113);
    let delta = Math.abs(angle - a) % (Math.PI * 2);
    if (delta > Math.PI) delta = Math.PI * 2 - delta;
    if (delta > 1.5) continue;
    const dist = Math.sin(delta) * r; // distance to the crack's ray
    const along = Math.cos(delta) * r;
    if (along > 0.06 && along < reach) line = Math.max(line, 1 - smooth(0.004, 0.022, dist));
  }
  const web = Math.max(
    1 - smooth(0, 0.016, Math.abs(r - 0.3 - 0.05 * noise(angle * 3, 1.5, 127))),
    (1 - smooth(0, 0.014, Math.abs(r - 0.55 - 0.07 * noise(angle * 2.5, 5.5, 131)))) * 0.7,
  );
  const crush = (1 - smooth(0.08, 0.2, r)) * (0.55 + 0.45 * noise(u * 30, v * 30, 137));
  const hole = 1 - smooth(0.04, 0.075, r);
  const alpha = clamp01(Math.max(hole, crush * 0.85, line * 0.8, web * line * 0.9 + web * 0.3 * (1 - smooth(0.3, 0.7, r))));
  const white = hole > 0.5 ? 0.02 : 0.62;
  out[0] = white * 0.92;
  out[1] = white;
  out[2] = white * 1.04;
  out[3] = alpha * windowed(r);
}

/** A hole in timber: dark hole, pale splinters torn out along the grain (vertical in the cell). */
function woodHole(u, v, out) {
  const r = Math.hypot(u * 1.5, v * 0.8);
  const hole = 1 - smooth(0.1, 0.19, Math.hypot(u, v));
  const fibre = noise(u * 26 + 3, v * 2.2 + 9, 139);
  const torn = (1 - smooth(0.22, 0.62, r)) * smooth(0.35, 0.7, fibre);
  const bruise = (1 - smooth(0.2, 0.7, r)) * 0.3;
  const alpha = clamp01(Math.max(hole * 0.95, torn * 0.85, bruise));
  const pale = torn > bruise && hole < 0.5;
  out[0] = hole > 0.5 ? 0.012 : pale ? 0.5 : 0.05;
  out[1] = hole > 0.5 ? 0.009 : pale ? 0.36 : 0.035;
  out[2] = hole > 0.5 ? 0.006 : pale ? 0.2 : 0.02;
  out[3] = alpha * windowed(Math.hypot(u, v));
}

/** A dark smudge with a small hole: rubber, cloth, dirt. */
function soot(u, v, out) {
  const r = Math.hypot(u, v);
  const n = fbm(u * 3.2 + 17, v * 3.2 - 4, 149, 4);
  const smudge = clamp01((0.7 - r - (0.5 - n) * 0.55) / 0.45);
  const hole = 1 - smooth(0.07, 0.15, r);
  out[0] = 0.014;
  out[1] = 0.012;
  out[2] = 0.011;
  out[3] = clamp01(Math.max(hole * 0.95, smudge * smudge * 0.62)) * windowed(r);
}

/** A blast mark: burnt black in the middle, streaks thrown outward, a brown singed fringe. */
function scorch(seed) {
  return (u, v, out) => {
    const r = Math.hypot(u, v);
    const angle = Math.atan2(v, u);
    const rays = 0.5 * noise(angle * 5 + seed, 1.5, seed) + 0.5 * noise(angle * 13 + seed * 3, 7.5, seed + 3);
    const reach = 0.46 + 0.42 * rays;
    const cloud = fbm(u * 3.1 + seed, v * 3.1 - seed, seed + 5, 4);
    const burnt = clamp01((reach - r) / 0.34) * (0.55 + 0.6 * cloud);
    const heart = 1 - smooth(0.1, 0.42, r);
    const alpha = clamp01(Math.max(heart * 0.9, burnt * 0.86));
    const singe = smooth(0.25, 0.8, r); // 0 = charcoal, 1 = brown fringe
    out[0] = 0.008 + 0.03 * singe;
    out[1] = 0.007 + 0.017 * singe;
    out[2] = 0.007 + 0.008 * singe;
    out[3] = alpha * windowed(r);
  };
}

// ------------------------------------------------------------------------------------------------
// Sheets
// ------------------------------------------------------------------------------------------------

/**
 * Paints a sheet of COLS × ROWS cells. `painters[i](u, v, out)` writes `channels` values in 0…1 for the
 * point (u, v) of cell i (−1…1, +v up). Returns {data: Uint8Array RGBA, width, height}; unpainted
 * channels are 0 and, for sheets without an opacity channel, alpha is 255.
 */
function paint(cell, painters, channels) {
  const width = cell * COLS;
  const height = cell * ROWS;
  const data = new Uint8Array(width * height * 4);
  const out = [0, 0, 0, 0];
  for (let i = 0; i < painters.length; i++) {
    const cx = (i % COLS) * cell;
    const cy = Math.floor(i / COLS) * cell;
    for (let py = 0; py < cell; py++) {
      const v = ((py + 0.5) / cell) * 2 - 1;
      for (let px = 0; px < cell; px++) {
        const u = ((px + 0.5) / cell) * 2 - 1;
        out[0] = out[1] = out[2] = out[3] = 0;
        painters[i](u, v, out);
        const o = ((cy + py) * width + cx + px) * 4;
        data[o] = Math.round(clamp01(out[0]) * 255);
        data[o + 1] = Math.round(clamp01(out[1]) * 255);
        data[o + 2] = Math.round(clamp01(out[2]) * 255);
        data[o + 3] = channels === 4 ? Math.round(clamp01(out[3]) * 255) : 255;
      }
    }
  }
  return { data, width, height };
}

export function litSheet(cell = 128) {
  return paint(cell, [puff(3, 0.75, 0.42), puff(19, 0.95, 0.5), puff(37, 0.6, 0.34), wisp, dust, steam, lint, roll], 2);
}

export function additiveSheet(cell = 128) {
  return paint(cell, [glow, streak, star, flame(5), flame(23), ember, glint, ring], 2);
}

export function decalSheet(cell = 128) {
  return paint(
    cell,
    [crater(7, [0.3, 0.29, 0.27]), crater(29, [0.34, 0.13, 0.08]), metalHole, glassCrack, woodHole, soot, scorch(11), scorch(47)],
    4,
  );
}
