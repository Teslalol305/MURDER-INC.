// Tileable procedural noise fields and the height-field maths behind every generated texture.
// Pure functions on typed arrays (no DOM, no three.js): unit-tested in test/mats-noise.test.js.
//
// A "field" is a Float32Array of w × h values, row by row from the top. Everything here wraps around
// both edges, so a texture made from these fields tiles without a seam.

/** Small deterministic PRNG (mulberry32) for fields; returns a function giving floats in [0, 1). */
export function prng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Integer lattice hash → [0, 1). */
export function hash2(x, y, seed = 0) {
  let h = Math.imul(x | 0, 0x27d4eb2d) ^ Math.imul(y | 0, 0x165667b1) ^ Math.imul(seed | 0, 0x9e3779b1);
  h = Math.imul(h ^ (h >>> 15), 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

/** One value per pixel, uniform in [0, 1). */
export function whiteNoise(w, h, seed = 1) {
  const rand = prng(seed);
  const out = new Float32Array(w * h);
  for (let i = 0; i < out.length; i++) out[i] = rand();
  return out;
}

/**
 * Periodic gradient noise with `cx` × `cy` lattice cells across the field. Values are roughly in
 * [−0.7, 0.7]; the field repeats exactly at its edges.
 */
export function gradientNoise(w, h, cx, cy, seed = 1) {
  cx = Math.max(1, Math.round(cx));
  cy = Math.max(1, Math.round(cy));
  const rand = prng(seed);
  const gx = new Float32Array(cx * cy);
  const gy = new Float32Array(cx * cy);
  for (let i = 0; i < gx.length; i++) {
    const a = rand() * Math.PI * 2;
    gx[i] = Math.cos(a);
    gy[i] = Math.sin(a);
  }
  // Per-column lookups: cell index, next cell index, fraction and its quintic weight.
  const x0 = new Int32Array(w);
  const x1 = new Int32Array(w);
  const fx = new Float32Array(w);
  const wx = new Float32Array(w);
  for (let x = 0; x < w; x++) {
    const u = (x / w) * cx;
    const i = Math.floor(u);
    const t = u - i;
    x0[x] = i % cx;
    x1[x] = (i + 1) % cx;
    fx[x] = t;
    wx[x] = t * t * t * (t * (t * 6 - 15) + 10);
  }
  const out = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const v = (y / h) * cy;
    const j = Math.floor(v);
    const fy = v - j;
    const wy = fy * fy * fy * (fy * (fy * 6 - 15) + 10);
    const r0 = (j % cy) * cx;
    const r1 = ((j + 1) % cy) * cx;
    const row = y * w;
    for (let x = 0; x < w; x++) {
      const a = r0 + x0[x];
      const b = r0 + x1[x];
      const c = r1 + x0[x];
      const d = r1 + x1[x];
      const tx = fx[x];
      const n00 = gx[a] * tx + gy[a] * fy;
      const n10 = gx[b] * (tx - 1) + gy[b] * fy;
      const n01 = gx[c] * tx + gy[c] * (fy - 1);
      const n11 = gx[d] * (tx - 1) + gy[d] * (fy - 1);
      const top = n00 + (n10 - n00) * wx[x];
      const bottom = n01 + (n11 - n01) * wx[x];
      out[row + x] = top + (bottom - top) * wy;
    }
  }
  return out;
}

/** Rescales a field in place so that it spans exactly [0, 1]. A flat field becomes 0.5. */
export function normalise(field) {
  let min = Infinity;
  let max = -Infinity;
  for (let i = 0; i < field.length; i++) {
    const v = field[i];
    if (v < min) min = v;
    if (v > max) max = v;
  }
  const span = max - min;
  if (!(span > 1e-9)) return field.fill(0.5);
  const k = 1 / span;
  for (let i = 0; i < field.length; i++) field[i] = (field[i] - min) * k;
  return field;
}

/**
 * Fractal sum of gradient noise, normalised to [0, 1] and periodic.
 * `cx` × `cy` cells in the first octave; every octave doubles the cell count and scales by `gain`.
 * `ridged` folds every octave around zero: thin bright creases instead of soft blobs.
 */
export function fbm(w, h, cx, cy, octaves = 4, seed = 1, gain = 0.5, ridged = false) {
  const out = new Float32Array(w * h);
  let amp = 1;
  for (let o = 0; o < octaves; o++) {
    const cellsX = cx * 2 ** o;
    const cellsY = cy * 2 ** o;
    if (cellsX > w / 2 || cellsY > h / 2) break; // finer than the pixels: nothing left to add
    const layer = gradientNoise(w, h, cellsX, cellsY, seed + o * 101);
    if (ridged) for (let i = 0; i < out.length; i++) out[i] += (1 - Math.abs(layer[i]) * 2.4) * amp;
    else for (let i = 0; i < out.length; i++) out[i] += layer[i] * amp;
    amp *= gain;
  }
  return normalise(out);
}

/**
 * Periodic cellular (Worley) noise with `cells` × `cells` feature points.
 * Returns {dist, id}: distance to the nearest feature point in cell units (0 … ~1) and a random
 * value in [0, 1) that is constant over each cell (for flakes, cobbles, leaves).
 */
export function cellular(w, h, cells, seed = 1) {
  cells = Math.max(1, Math.round(cells));
  const rand = prng(seed);
  const px = new Float32Array(cells * cells);
  const py = new Float32Array(cells * cells);
  const pid = new Float32Array(cells * cells);
  for (let i = 0; i < px.length; i++) {
    px[i] = rand();
    py[i] = rand();
    pid[i] = rand();
  }
  const dist = new Float32Array(w * h);
  const id = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const v = (y / h) * cells;
    const j = Math.floor(v);
    for (let x = 0; x < w; x++) {
      const u = (x / w) * cells;
      const i = Math.floor(u);
      let best = Infinity;
      let bestId = 0;
      for (let dj = -1; dj <= 1; dj++) {
        const cj = (((j + dj) % cells) + cells) % cells;
        for (let di = -1; di <= 1; di++) {
          const ci = (((i + di) % cells) + cells) % cells;
          const k = cj * cells + ci;
          const dx = i + di + px[k] - u;
          const dy = j + dj + py[k] - v;
          const d = dx * dx + dy * dy;
          if (d < best) {
            best = d;
            bestId = pid[k];
          }
        }
      }
      dist[y * w + x] = Math.sqrt(best);
      id[y * w + x] = bestId;
    }
  }
  return { dist, id };
}

/** Bilinear, wrapping sample of a field at any resolution: (u, v) in tile units, `tiles` repeats per unit. */
export function sampleField(field, size, u, v) {
  const x = (u - Math.floor(u)) * size;
  const y = (v - Math.floor(v)) * size;
  const x0 = Math.floor(x) % size;
  const y0 = Math.floor(y) % size;
  const x1 = (x0 + 1) % size;
  const y1 = (y0 + 1) % size;
  const tx = x - Math.floor(x);
  const ty = y - Math.floor(y);
  const a = field[y0 * size + x0];
  const b = field[y0 * size + x1];
  const c = field[y1 * size + x0];
  const d = field[y1 * size + x1];
  const top = a + (b - a) * tx;
  return top + (c + (d - c) * tx - top) * ty;
}

/**
 * Resamples a square periodic field of `size` to w × h, repeating it `tilesX` × `tilesY` times
 * (bilinear). Used to stretch a shared noise field over a texture at a chosen scale.
 */
export function resample(field, size, w, h, tilesX = 1, tilesY = tilesX) {
  const out = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const v = (y / h) * tilesY;
    for (let x = 0; x < w; x++) out[y * w + x] = sampleField(field, size, (x / w) * tilesX, v);
  }
  return out;
}

/** Separable box blur of radius r pixels (wrapping). Returns a new field. */
export function blur(field, w, h, r = 1) {
  r = Math.max(0, Math.round(r));
  if (r === 0) return field.slice();
  const k = 1 / (2 * r + 1);
  const tmp = new Float32Array(w * h);
  const out = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const row = y * w;
    let sum = 0;
    for (let d = -r; d <= r; d++) sum += field[row + ((d + w) % w)];
    for (let x = 0; x < w; x++) {
      tmp[row + x] = sum * k;
      sum += field[row + ((x + r + 1) % w)] - field[row + ((x - r + w) % w)];
    }
  }
  for (let x = 0; x < w; x++) {
    let sum = 0;
    for (let d = -r; d <= r; d++) sum += tmp[((d + h) % h) * w + x];
    for (let y = 0; y < h; y++) {
      out[y * w + x] = sum * k;
      sum += tmp[((y + r + 1) % h) * w + x] - tmp[((y - r + h) % h) * w + x];
    }
  }
  return out;
}

export const smooth = (e0, e1, x) => {
  const t = x <= e0 ? 0 : x >= e1 ? 1 : (x - e0) / (e1 - e0);
  return t * t * (3 - 2 * t);
};

/**
 * Tangent-space normal map (RGBA bytes, +Y up as three.js expects) from a height field.
 *
 * `slope` converts a height difference of 1 between neighbouring pixels into a surface slope:
 * for relief that is `depth` metres tall on a texture with `ppm` pixels per metre, slope = depth × ppm.
 * Rows run top to bottom (canvas order) and the texture is flipped on upload, so "up" in UV space is
 * −y here. Wraps around both edges unless `wrapY` is false (facades, signs).
 */
export function heightToNormal(height, w, h, slope = 1, out = new Uint8ClampedArray(w * h * 4), wrapX = true, wrapY = true) {
  for (let y = 0; y < h; y++) {
    const up = y > 0 ? y - 1 : wrapY ? h - 1 : 0;
    const down = y < h - 1 ? y + 1 : wrapY ? 0 : h - 1;
    for (let x = 0; x < w; x++) {
      const left = x > 0 ? x - 1 : wrapX ? w - 1 : 0;
      const right = x < w - 1 ? x + 1 : wrapX ? 0 : w - 1;
      // Sobel: smoother than central differences on 8-bit sources.
      const tl = height[up * w + left];
      const tc = height[up * w + x];
      const tr = height[up * w + right];
      const ml = height[y * w + left];
      const mr = height[y * w + right];
      const bl = height[down * w + left];
      const bc = height[down * w + x];
      const br = height[down * w + right];
      const dx = (tr + 2 * mr + br - tl - 2 * ml - bl) * 0.125;
      const dy = (bl + 2 * bc + br - tl - 2 * tc - tr) * 0.125;
      const nx = -dx * slope;
      const ny = dy * slope;
      const inv = 1 / Math.sqrt(nx * nx + ny * ny + 1);
      const o = (y * w + x) * 4;
      out[o] = (nx * inv * 0.5 + 0.5) * 255;
      out[o + 1] = (ny * inv * 0.5 + 0.5) * 255;
      out[o + 2] = (inv * 0.5 + 0.5) * 255;
      out[o + 3] = 255;
    }
  }
  return out;
}
