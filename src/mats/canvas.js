// Canvas-2D plumbing for the generated textures: canvases, colour helpers, the shared bank of tileable
// noise layers, and the conversion of painted canvases into three.js textures.

import {
  CanvasTexture,
  ClampToEdgeWrapping,
  Color,
  LinearFilter,
  LinearMipmapLinearFilter,
  NoColorSpace,
  RepeatWrapping,
  SRGBColorSpace,
} from 'three';
import { fbm, heightToNormal, whiteNoise } from './noise.js';

// ------------------------------------------------------------------------------------------------
// Canvases
// ------------------------------------------------------------------------------------------------

/** A w × h pixel canvas; returns its 2D context (`ctx.canvas` is the canvas). */
export function canvas2d(w, h, readback = false) {
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(w));
  canvas.height = Math.max(1, Math.round(h));
  // Canvases that are read back (height maps) stay in main memory: reads are then cheap.
  return canvas.getContext('2d', readback ? { willReadFrequently: true } : undefined);
}

const scratch = new Map();

/** A reusable transparent work canvas of the given size (cleared on every call). */
export function scratchCanvas(w, h) {
  const key = `${w}x${h}`;
  let ctx = scratch.get(key);
  if (!ctx) {
    ctx = canvas2d(w, h);
    scratch.set(key, ctx);
  }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
  ctx.clearRect(0, 0, w, h);
  return ctx;
}

/** Frees the work canvases (called once the block is built). */
export function dropScratch() {
  for (const ctx of scratch.values()) ctx.canvas.width = ctx.canvas.height = 1;
  scratch.clear();
}

// ------------------------------------------------------------------------------------------------
// Colour (sRGB hex integers in, CSS strings out)
// ------------------------------------------------------------------------------------------------

const _color = new Color();

/** Any colour-like value (hex number, CSS string, THREE.Color) → sRGB hex integer. */
export function toHex(value, fallback = 0x808080) {
  if (value === undefined || value === null) return fallback;
  if (typeof value === 'number') return value & 0xffffff;
  if (value.isColor) return value.getHex();
  try {
    return _color.set(value).getHex();
  } catch {
    return fallback;
  }
}

const byte = (v) => (v < 0 ? 0 : v > 255 ? 255 : Math.round(v));

export const rgbOf = (hex) => [(hex >> 16) & 255, (hex >> 8) & 255, hex & 255];
export const hexOf = (r, g, b) => (byte(r) << 16) | (byte(g) << 8) | byte(b);

/** CSS colour string for a hex integer. */
export function css(hex, alpha = 1) {
  const r = (hex >> 16) & 255;
  const g = (hex >> 8) & 255;
  const b = hex & 255;
  return alpha >= 1 ? `rgb(${r},${g},${b})` : `rgba(${r},${g},${b},${Math.max(0, alpha)})`;
}

/** Grey level v (0 … 1) as a CSS colour. */
export function grey(v, alpha = 1) {
  const n = byte(v * 255);
  return alpha >= 1 ? `rgb(${n},${n},${n})` : `rgba(${n},${n},${n},${Math.max(0, alpha)})`;
}

/** Brightness × k. */
export function shade(hex, k) {
  return hexOf(((hex >> 16) & 255) * k, ((hex >> 8) & 255) * k, (hex & 255) * k);
}

export function mixHex(a, b, t) {
  return hexOf(
    ((a >> 16) & 255) + (((b >> 16) & 255) - ((a >> 16) & 255)) * t,
    ((a >> 8) & 255) + (((b >> 8) & 255) - ((a >> 8) & 255)) * t,
    (a & 255) + ((b & 255) - (a & 255)) * t,
  );
}

/** Random brightness within ± amount and a slight warm / cool drift: no two bricks alike. */
export function jitter(hex, rand, amount = 0.08, drift = 0.02) {
  const k = 1 + (rand() * 2 - 1) * amount;
  const d = (rand() * 2 - 1) * drift;
  return hexOf(((hex >> 16) & 255) * (k + d), ((hex >> 8) & 255) * k, (hex & 255) * (k - d));
}

/** Perceived lightness of a hex colour, 0 … 1. */
export const luma = (hex) => (((hex >> 16) & 255) * 0.2126 + ((hex >> 8) & 255) * 0.7152 + (hex & 255) * 0.0722) / 255;

// ------------------------------------------------------------------------------------------------
// Fields ↔ canvases
// ------------------------------------------------------------------------------------------------

/**
 * Paints a field into a new canvas: grey levels, or (mask) white with the field as alpha.
 * Values are remapped so that `lo` becomes 0 and `hi` becomes 1.
 */
export function fieldToCanvas(field, w, h, { lo = 0, hi = 1, mask = false } = {}) {
  const ctx = canvas2d(w, h);
  const image = ctx.createImageData(w, h);
  const data = image.data;
  const k = 255 / (hi - lo || 1);
  for (let i = 0, o = 0; i < field.length; i++, o += 4) {
    const v = (field[i] - lo) * k;
    if (mask) {
      data[o] = data[o + 1] = data[o + 2] = 255;
      data[o + 3] = v;
    } else {
      data[o] = data[o + 1] = data[o + 2] = v;
      data[o + 3] = 255;
    }
  }
  ctx.putImageData(image, 0, 0);
  return ctx.canvas;
}

/** The red channel of a canvas as a field in 0 … 1. */
export function canvasToField(ctx) {
  const { width: w, height: h } = ctx.canvas;
  const data = ctx.getImageData(0, 0, w, h).data;
  const out = new Float32Array(w * h);
  for (let i = 0, o = 0; i < out.length; i++, o += 4) out[i] = data[o] / 255;
  return out;
}

/**
 * Fills the whole target with a tileable source repeated tilesX × tilesY times.
 * A pattern fill wraps while filtering, so scaled noise meets itself cleanly at the edges.
 */
export function fillTiled(ctx, source, tilesX = 1, tilesY = tilesX, { alpha = 1, mode = 'source-over', ox = 0, oy = 0 } = {}) {
  const W = ctx.canvas.width;
  const H = ctx.canvas.height;
  const sx = W / (tilesX * source.width);
  const sy = H / (tilesY * source.height);
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.globalCompositeOperation = mode;
  ctx.translate(ox * W, oy * H);
  ctx.scale(sx, sy);
  ctx.fillStyle = ctx.createPattern(source, 'repeat');
  ctx.fillRect((-ox * W) / sx, (-oy * H) / sy, W / sx, H / sy);
  ctx.restore();
}

/** Rubs the target out through a tileable alpha mask: opaque parts of the mask become holes. */
export function erase(ctx, mask, tilesX = 1, tilesY = tilesX, opts = {}) {
  fillTiled(ctx, mask, tilesX, tilesY, { ...opts, mode: 'destination-out' });
}

/**
 * Lays a colour over the target through a tileable alpha mask (stains, rust, grime, damp).
 */
export function stain(ctx, mask, color, { alpha = 1, tilesX = 1, tilesY = tilesX, mode = 'source-over', ox = 0, oy = 0 } = {}) {
  const W = ctx.canvas.width;
  const H = ctx.canvas.height;
  const work = scratchCanvas(W, H);
  fillTiled(work, mask, tilesX, tilesY, { ox, oy });
  work.globalCompositeOperation = 'source-in';
  work.fillStyle = color;
  work.fillRect(0, 0, W, H);
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.globalCompositeOperation = mode;
  ctx.drawImage(work.canvas, 0, 0);
  ctx.restore();
}

/**
 * Calls draw(dx, dy) for the tile itself and for every neighbouring copy a shape of radius r at
 * (x, y) reaches into, so shapes that cross an edge come back in on the other side.
 */
export function wrapDraw(W, H, x, y, r, draw) {
  for (let dy = -1; dy <= 1; dy++) {
    if ((dy < 0 && y + r < H) || (dy > 0 && y - r > 0)) continue;
    for (let dx = -1; dx <= 1; dx++) {
      if ((dx < 0 && x + r < W) || (dx > 0 && x - r > 0)) continue;
      draw(dx * W, dy * H);
    }
  }
}

// ------------------------------------------------------------------------------------------------
// The noise bank: a handful of tileable layers shared by every surface
// ------------------------------------------------------------------------------------------------

/**
 * @param {number} size  pixels per side of the stored layers (a power of two; 256 is plenty for the
 *                       broad ones, the two fine-grained ones are kept at `detail`)
 * @param {number} detail  pixels per side of the 'fine' and 'streaks' layers
 */
export function createBank(size, detail = size) {
  const recipes = {
    clouds: () => fbm(size, size, 3, 3, 5, 11), // broad soft blotches
    blobs: () => fbm(size, size, 6, 6, 3, 71), // rounder, puddle-sized
    mottle: () => fbm(size, size, 12, 12, 4, 23), // hand-sized variation
    ridges: () => fbm(size, size, 7, 7, 4, 89, 0.55, true), // creases and cracks
    fine: () => fbm(detail, detail, 44, 44, 3, 37), // coarse grain
    streaks: () => fbm(detail, detail, 56, 3, 3, 53), // long vertical runs
  };
  const sizeOf = (name) => (name === 'fine' || name === 'streaks' ? detail : size);
  const fields = new Map();
  const canvases = new Map();
  const grains = new Map();

  /** The named field (floats in 0 … 1, sizeOf(name) pixels square). */
  function field(name) {
    let f = fields.get(name);
    if (!f) {
      if (!recipes[name]) throw new Error(`mats: no noise layer called '${name}'`);
      f = recipes[name]();
      fields.set(name, f);
    }
    return f;
  }

  function cached(key, make) {
    let c = canvases.get(key);
    if (!c) {
      c = make();
      canvases.set(key, c);
    }
    return c;
  }

  const grey = (name, lo = 0, hi = 1) => cached(`g:${name}:${lo}:${hi}`, () => fieldToCanvas(field(name), sizeOf(name), sizeOf(name), { lo, hi }));

  return {
    size,
    field,
    /** Grey canvas of a layer (for 'overlay' / 'multiply' / 'soft-light' compositing). */
    grey,
    /** Alpha-mask canvas of a layer: opaque where the layer exceeds `hi`, clear below `lo`. */
    mask: (name, lo = 0, hi = 1) => cached(`m:${name}:${lo}:${hi}`, () => fieldToCanvas(field(name), sizeOf(name), sizeOf(name), { lo, hi, mask: true })),
    /**
     * A layer stretched over w × h pixels, repeated tilesX × tilesY times, as a field in 0 … 1.
     * The browser does the filtering (a pattern fill), which is far quicker than doing it here.
     */
    spread(name, w, h, tilesX = 1, tilesY = tilesX) {
      const ctx = canvas2d(w, h, true);
      fillTiled(ctx, grey(name), tilesX, tilesY);
      return canvasToField(ctx);
    },
    /** Per-pixel grain centred on mid grey (for 'overlay'): w × h, cached per size. */
    grain(w, h) {
      const key = `${w}x${h}`;
      let c = grains.get(key);
      if (!c) {
        const a = whiteNoise(w, h, 7);
        const b = whiteNoise(w, h, 8);
        for (let i = 0; i < a.length; i++) a[i] = (a[i] + b[i]) * 0.5; // triangular: fewer extremes
        c = fieldToCanvas(a, w, h);
        grains.set(key, c);
      }
      return c;
    },
    /** Drops the cached canvases (the float fields are small and stay). */
    trim() {
      canvases.clear();
      grains.clear();
    },
  };
}

// ------------------------------------------------------------------------------------------------
// Textures
// ------------------------------------------------------------------------------------------------

/**
 * Wraps a canvas as a texture.
 * opts: { srgb = true, repeat: [u, v], wrap: 'repeat' | 'clamp' | [s, t], aniso = 4, mipmaps = true }
 */
export function makeTexture(canvas, opts = {}) {
  const texture = new CanvasTexture(canvas);
  texture.colorSpace = opts.srgb === false ? NoColorSpace : SRGBColorSpace;
  const wrap = opts.wrap ?? (opts.repeat ? 'repeat' : 'clamp');
  const [ws, wt] = Array.isArray(wrap) ? wrap : [wrap, wrap];
  texture.wrapS = ws === 'repeat' ? RepeatWrapping : ClampToEdgeWrapping;
  texture.wrapT = wt === 'repeat' ? RepeatWrapping : ClampToEdgeWrapping;
  if (opts.repeat) texture.repeat.set(opts.repeat[0], opts.repeat[1]);
  texture.anisotropy = opts.aniso ?? 4;
  if (opts.mipmaps === false) {
    texture.generateMipmaps = false;
    texture.minFilter = LinearFilter;
  } else {
    texture.minFilter = LinearMipmapLinearFilter;
  }
  return texture;
}

/** A 1 × 1 texture of one colour: the stand-in for a map a material does not need. */
export function pixelTexture(r, g, b, srgb) {
  const ctx = canvas2d(1, 1);
  ctx.fillStyle = `rgb(${r},${g},${b})`;
  ctx.fillRect(0, 0, 1, 1);
  const texture = makeTexture(ctx.canvas, { srgb, wrap: 'repeat', aniso: 1, mipmaps: false });
  texture.magFilter = LinearFilter;
  return texture;
}

/**
 * Normal-map canvas from a height field (see noise.js heightToNormal for `slope`).
 */
export function normalCanvas(height, w, h, slope, wrapX = true, wrapY = true) {
  const ctx = canvas2d(w, h);
  const image = ctx.createImageData(w, h);
  heightToNormal(height, w, h, slope, image.data, wrapX, wrapY);
  ctx.putImageData(image, 0, 0);
  return ctx.canvas;
}

/**
 * Packs the occlusion / roughness / metalness texture three.js reads (G = roughness, B = metalness).
 * `rough` and `metal` are fields in 0 … 1 or null (255); `red` is a free channel: the ground sets
 * store their "low spots" there for the wet-street shader.
 */
export function ormCanvas(w, h, rough, metal = null, red = null) {
  const ctx = canvas2d(w, h);
  const image = ctx.createImageData(w, h);
  const data = image.data;
  for (let i = 0, o = 0; i < w * h; i++, o += 4) {
    data[o] = red ? red[i] * 255 : 255;
    data[o + 1] = rough ? rough[i] * 255 : 255;
    data[o + 2] = metal ? metal[i] * 255 : 255;
    data[o + 3] = 255;
  }
  ctx.putImageData(image, 0, 0);
  return ctx.canvas;
}
