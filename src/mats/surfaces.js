// The tiling surface sets: asphalt, sidewalk, brick, concrete, steel … painted on canvases at real-world
// scale. Each set is a few textures that share one layout:
//
//   albedo   colour (sRGB). Some sets carry several colourways over one relief (brick).
//   normal   derived from a painted height canvas
//   orm      G = roughness, B = metalness (relative), R = "low spots" (ground sets: where water collects)
//
// A set is built the first time a material asks for it. Sizes follow the quality tier (`size` is 256,
// 512 or 1024) times the set's own factor, and every set keeps the same pixels-per-metre on both axes.

import { canvas2d, canvasToField, css, fieldToCanvas, fillTiled, grey, jitter, mixHex, normalCanvas, ormCanvas, shade, stain, wrapDraw } from './canvas.js';
import { blur, cellular, fbm, prng, resample, smooth, whiteNoise } from './noise.js';

const TAU = Math.PI * 2;

// ------------------------------------------------------------------------------------------------
// Painter scaffolding
// ------------------------------------------------------------------------------------------------

/**
 * The working state of one set while it is painted.
 * `albedo` and `height` always exist; `rough` and `metal` are created on first use (grey levels:
 * absolute roughness, relative metalness).
 */
function painter(spec, size, bank, seed) {
  const [tu, tv] = spec.tile;
  const w = Math.max(32, Math.round(size * (spec.res ?? 1) * (spec.px ? spec.px[0] : 1)));
  const h = Math.max(32, Math.round((w * tv) / tu));
  const P = {
    w,
    h,
    bank,
    ppm: w / tu,
    rand: prng(seed),
    albedo: canvas2d(w, h),
    height: canvas2d(w, h, true),
    _rough: null,
    _metal: null,
    get rough() {
      if (!this._rough) {
        this._rough = canvas2d(w, h, true);
        this._rough.fillStyle = grey(spec.rough ?? 0.9);
        this._rough.fillRect(0, 0, w, h);
      }
      return this._rough;
    },
    get metal() {
      if (!this._metal) {
        this._metal = canvas2d(w, h, true);
        this._metal.fillStyle = '#fff';
        this._metal.fillRect(0, 0, w, h);
      }
      return this._metal;
    },
    /** Metres → pixels. */
    m: (metres) => (metres * w) / tu,
  };
  return P;
}

function fill(ctx, style) {
  ctx.fillStyle = style;
  ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}

/**
 * Turns the painted canvases into the normal and ORM canvases.
 * o: { depth   metres of relief between height 0 and 1,
 *      soften  blur radius in metres (rounds hard painted edges into bevels),
 *      grain   amount of per-pixel noise added to the height (micro relief),
 *      post(height) → {rough, metal, low}?  hook that may reshape the height and supply fields }
 */
function finish(P, o = {}) {
  const { w, h } = P;
  let height = canvasToField(P.height);
  const r = Math.round((o.soften ?? 0) * P.ppm);
  if (r > 0) height = blur(height, w, h, r);
  if (o.grain) {
    const noise = whiteNoise(w, h, 91);
    for (let i = 0; i < height.length; i++) height[i] += (noise[i] - 0.5) * o.grain;
  }
  const extra = (o.post && o.post(height)) || {};
  const rough = extra.rough || (P._rough ? canvasToField(P._rough) : null);
  const metal = extra.metal || (P._metal ? canvasToField(P._metal) : null);
  return {
    normal: normalCanvas(height, w, h, (o.depth ?? 0.004) * P.ppm),
    orm: rough || metal || extra.low ? ormCanvas(w, h, rough, metal, extra.low || null) : null,
  };
}

/**
 * Scatters `count` small ellipses over several layers at once (same geometry in each).
 * pick(rand, r) → one fill style per layer (a falsy entry skips that layer).
 */
function specks(P, layers, count, rMin, rMax, pick) {
  const { w, h, rand } = P;
  for (let i = 0; i < count; i++) {
    const x = rand() * w;
    const y = rand() * h;
    const r = rMin + (rMax - rMin) * rand() * rand();
    const ry = r * (0.55 + rand() * 0.45);
    const rot = rand() * Math.PI;
    const styles = pick(rand, r);
    wrapDraw(w, h, x, y, r + 1, (dx, dy) => {
      for (let k = 0; k < layers.length; k++) {
        if (!styles[k]) continue;
        const ctx = layers[k];
        ctx.fillStyle = styles[k];
        ctx.beginPath();
        ctx.ellipse(x + dx, y + dy, r, ry, rot, 0, TAU);
        ctx.fill();
      }
    });
  }
}

/** Courses of bricks or blocks in running bond; every `headerEvery`-th course is headers (half length). */
function bondLayout(w, h, cols, rows, headerEvery, rand) {
  const out = [];
  const bw = w / cols;
  const bh = h / rows;
  for (let row = 0; row < rows; row++) {
    const header = headerEvery > 0 && row % headerEvery === headerEvery - 1;
    const len = header ? bw / 2 : bw;
    const offset = header ? bw / 4 : (row % 2) * (bw / 2);
    const n = Math.round(w / len);
    for (let i = 0; i < n; i++) out.push({ x: offset + i * len, y: row * bh, w: len, h: bh, a: rand(), b: rand(), c: rand() });
  }
  return out;
}

/** Fills a brick-like rect inset by half a joint, wrapping around the right edge. */
function unit(ctx, W, b, joint) {
  const x = b.x + joint / 2;
  const y = b.y + joint / 2;
  const w = b.w - joint;
  const h = b.h - joint;
  ctx.fillRect(x, y, w, h);
  if (x + w > W) ctx.fillRect(x - W, y, w, h);
}

/** Thin random-walk line (cracks, scratches) on several layers; wraps by drawing the neighbours. */
function wander(P, layers, styles, x, y, angle, length, widthPx, wobble = 0.5) {
  const { w, h, rand } = P;
  const pts = [[x, y]];
  const step = Math.max(2, length / 14);
  let a = angle;
  for (let d = 0; d < length; d += step) {
    a += (rand() - 0.5) * wobble;
    x += Math.cos(a) * step;
    y += Math.sin(a) * step;
    pts.push([x, y]);
  }
  for (let k = 0; k < layers.length; k++) {
    if (!styles[k]) continue;
    const ctx = layers[k];
    ctx.strokeStyle = styles[k];
    ctx.lineWidth = widthPx;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    for (let dy = -1; dy <= 1; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        ctx.beginPath();
        ctx.moveTo(pts[0][0] + dx * w, pts[0][1] + dy * h);
        for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0] + dx * w, pts[i][1] + dy * h);
        ctx.stroke();
      }
    }
  }
}

/** Multiplies the RGB of a canvas by a per-pixel field (darkening wet ground, baking occlusion). */
function multiply(ctx, factor) {
  const { width: w, height: h } = ctx.canvas;
  const image = ctx.getImageData(0, 0, w, h);
  const data = image.data;
  for (let i = 0, o = 0; i < factor.length; i++, o += 4) {
    const k = factor[i];
    data[o] *= k;
    data[o + 1] *= k;
    data[o + 2] *= k;
  }
  ctx.putImageData(image, 0, 0);
}

// ------------------------------------------------------------------------------------------------
// Ground
// ------------------------------------------------------------------------------------------------

/**
 * Asphalt, hosed down: dark binder, pale aggregate, damp patches that go glossy and small puddles
 * where the stones stand in water. The relief is flattened to the water level inside the puddles.
 */
function asphalt(P) {
  const { w, h, bank, ppm } = P;
  const A = P.albedo;
  const H = P.height;
  fill(A, css(0x202124));
  fill(H, grey(0.42));

  // Aggregate: thousands of small stones, a few of them warm or nearly white. Scattered over a
  // quarter of the tile and laid four times: nobody can tell one pebble from another.
  const hw = Math.round(w / 2);
  const hh = Math.round(h / 2);
  const stonesA = canvas2d(hw, hh);
  const stonesH = canvas2d(hw, hh);
  specks({ w: hw, h: hh, rand: P.rand }, [stonesA, stonesH], Math.round(hw * hh * 0.03), 0.0025 * ppm, 0.01 * ppm, (rand) => {
    const v = 0.12 + rand() * 0.17;
    const warm = rand() < 0.16 ? 1.12 : 1;
    const pale = rand() < 0.025 ? 1.5 : 1;
    const tone = Math.min(255, v * 255 * pale);
    return [`rgba(${tone * warm},${tone},${tone * 0.96},0.75)`, grey(0.5 + rand() * 0.48, 0.9)];
  });
  fillTiled(A, stonesA.canvas, 2, 2);
  fillTiled(H, stonesH.canvas, 2, 2);
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.42 });
  fillTiled(H, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.55 });
  fillTiled(A, bank.grey('mottle'), 2, 2, { mode: 'soft-light', alpha: 0.45 });
  fillTiled(A, bank.grey('clouds'), 1, 1, { mode: 'soft-light', alpha: 0.2 });
  fillTiled(H, bank.grey('mottle'), 2, 2, { mode: 'overlay', alpha: 0.25 });

  const mottle = bank.spread('mottle', w, h, 1);
  const clouds = bank.spread('clouds', w, h, 1);
  const blobs = bank.spread('blobs', w, h, 1);
  const LEVEL = 0.5; // water level in height units

  const maps = finish(P, {
    depth: 0.009,
    grain: 0.06,
    post(height) {
      const n = w * h;
      const rough = new Float32Array(n);
      const low = new Float32Array(n);
      const dark = new Float32Array(n);
      const wide = blur(height, w, h, Math.max(1, Math.round(0.02 * ppm)));
      for (let i = 0; i < n; i++) {
        const damp = smooth(0.3, 0.75, 0.75 * mottle[i] + 0.25 * clouds[i]);
        const puddle = smooth(0.78, 0.86, blobs[i] + (0.5 - wide[i]) * 0.5);
        const hgt = height[i];
        const above = smooth(LEVEL, LEVEL + 0.1, hgt); // stones standing clear of the water
        // Dry asphalt is matt; damp asphalt shines; standing water is a mirror.
        let r = 0.92 - 0.36 * damp - 0.08 * smooth(0.55, 0.9, hgt);
        r += (0.06 + 0.42 * above - r) * puddle;
        rough[i] = r;
        height[i] = hgt + (Math.max(hgt, LEVEL) - hgt) * puddle;
        low[i] = Math.min(1, Math.max(0, 0.5 + (0.5 - wide[i]) * 1.6 + (mottle[i] - 0.5) * 0.5));
        dark[i] = 1 - 0.16 * damp - 0.28 * puddle * (1 - above);
      }
      multiply(A, dark);
      return { rough, low };
    },
  });

  // Court paint and other coatings over asphalt: a pale, worn skin with the stone showing through.
  const coat = () => {
    const C = canvas2d(w, h);
    fill(C, css(0xeeeeea));
    fillTiled(C, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.35 });
    fillTiled(C, bank.grey('mottle'), 2, 2, { mode: 'multiply', alpha: 0.3 });
    stain(C, bank.mask('fine', 0.62, 0.8), css(0x4a4a48), { alpha: 0.5, tilesX: 2 });
    stain(C, bank.mask('clouds', 0.6, 0.85), css(0x55554f), { alpha: 0.35 });
    return C.canvas;
  };

  return { albedo: { base: A.canvas, coat }, ...maps };
}

/** Sidewalk: 1.5 m flags, tooled joints, broom finish, a generous helping of chewing gum. */
function sidewalk(P) {
  const { w, h, bank, ppm, rand } = P;
  const A = P.albedo;
  const H = P.height;
  const R = P.rough;
  const n = Math.round(P.w / P.m(1.5));
  const s = w / n;

  // Slabs, each poured on a different day.
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      A.fillStyle = css(jitter(0x75726b, rand, 0.07, 0.012));
      A.fillRect(i * s, j * s, s + 1, s + 1);
      H.fillStyle = grey(0.6 + (rand() - 0.5) * 0.05);
      H.fillRect(i * s, j * s, s + 1, s + 1);
    }
  }
  // Broom finish: faint strokes across the direction of travel.
  for (let x = 0; x < w; x += 2) {
    const a = 0.02 + rand() * 0.05;
    const light = rand() < 0.5;
    A.fillStyle = light ? `rgba(255,255,255,${a})` : `rgba(0,0,0,${a})`;
    A.fillRect(x, 0, 1, h);
    H.fillStyle = light ? `rgba(255,255,255,${a * 2})` : `rgba(0,0,0,${a * 2})`;
    H.fillRect(x, 0, 1, h);
  }
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.38 });
  fillTiled(H, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.3 });
  fillTiled(A, bank.grey('mottle'), 3, 3, { mode: 'soft-light', alpha: 0.5 });
  fillTiled(A, bank.grey('clouds'), 1, 1, { mode: 'multiply', alpha: 0.12 });
  // Pits and exposed aggregate.
  specks(P, [A, H], Math.round(w * h * 0.0022), 0.0015 * ppm, 0.005 * ppm, (r) => {
    const pit = r() < 0.6;
    return [pit ? `rgba(30,28,26,${0.3 + r() * 0.4})` : `rgba(190,186,176,${0.25 + r() * 0.3})`, pit ? grey(0.2, 0.7) : grey(0.8, 0.5)];
  });
  // Grime that has settled in, and paler patches where a slab was scrubbed.
  stain(A, bank.mask('clouds', 0.5, 0.8), css(0x2c2a27), { alpha: 0.14, ox: 0.37, oy: 0.11 });
  stain(A, bank.mask('mottle', 0.62, 0.85), css(0x3a352d), { alpha: 0.22, tilesX: 2 });
  stain(R, bank.mask('mottle', 0.5, 0.85), grey(0.62), { alpha: 0.7, tilesX: 2 });

  // A couple of hairline cracks.
  for (let i = 0; i < 3; i++) {
    wander(P, [A, H], ['rgba(28,26,24,0.55)', grey(0.12, 0.8)], rand() * w, rand() * h, rand() * TAU, P.m(0.5 + rand() * 0.9), Math.max(1, 0.003 * ppm), 0.7);
  }

  // Joints: a tooled shoulder either side of a dark groove packed with dirt.
  const joint = Math.max(1.5, 0.012 * ppm);
  const shoulder = Math.max(joint + 2, 0.035 * ppm);
  for (let k = 0; k <= n; k++) {
    const p = k * s;
    for (const [ctx, wide, narrow] of [
      [A, 'rgba(150,146,136,0.28)', css(0x35322e)],
      [H, grey(0.5, 0.6), grey(0.08)],
      [R, grey(0.8, 0.5), grey(0.98)],
    ]) {
      ctx.fillStyle = wide;
      ctx.fillRect(p - shoulder / 2, 0, shoulder, h);
      ctx.fillRect(0, p - shoulder / 2, w, shoulder);
      ctx.fillStyle = narrow;
      ctx.fillRect(p - joint / 2, 0, joint, h);
      ctx.fillRect(0, p - joint / 2, w, joint);
    }
  }

  // Gum: black with age, flattened into the slab.
  specks(P, [A, H, R], Math.round(34 * (w / P.m(4.5)) ** 2), 0.011 * ppm, 0.026 * ppm, (r) => {
    const fresh = r() < 0.12;
    const tone = fresh ? css(mixHex(0x9a938a, 0xb9a9a2, r()), 0.8) : css(shade(0x24221f, 0.7 + r() * 0.6), 0.86);
    return [tone, grey(0.66, 0.6), grey(0.45, 0.9)];
  });

  const wide = blur(canvasToField(H), w, h, Math.max(1, Math.round(0.03 * ppm)));
  const mottle = bank.spread('mottle', w, h, 1);
  const low = new Float32Array(w * h);
  for (let i = 0; i < low.length; i++) low[i] = Math.min(1, Math.max(0, 0.5 + (0.58 - wide[i]) * 1.2 + (mottle[i] - 0.5) * 0.6));

  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.012, soften: 0.0025, grain: 0.05, post: () => ({ low }) }) };
}

/** Packed earth of the vacant lot: pebbles, damp hollows, bits of glass. */
function dirt(P) {
  const { w, h, bank, ppm } = P;
  const A = P.albedo;
  const H = P.height;
  fill(A, css(0x3d342a));
  fill(H, grey(0.5));
  fillTiled(H, bank.grey('mottle'), 2, 2, { mode: 'overlay', alpha: 0.9 });
  fillTiled(H, bank.grey('clouds'), 1, 1, { mode: 'overlay', alpha: 0.6 });
  fillTiled(A, bank.grey('mottle'), 2, 2, { mode: 'overlay', alpha: 0.55 });
  fillTiled(A, bank.grey('clouds'), 1, 1, { mode: 'soft-light', alpha: 0.6 });
  stain(A, bank.mask('blobs', 0.55, 0.75), css(0x231d17), { alpha: 0.55 });
  stain(A, bank.mask('fine', 0.6, 0.85), css(0x5a4d3c), { alpha: 0.4, tilesX: 2 });
  specks(P, [A, H], Math.round(w * h * 0.004), 0.004 * ppm, 0.022 * ppm, (r) => {
    const v = 0.6 + r() * 0.7;
    const glass = r() < 0.03;
    return [glass ? `rgba(150,190,170,0.7)` : css(shade(r() < 0.5 ? 0x6b6258 : 0x57493a, v), 0.9), grey(0.62 + r() * 0.35, 0.9)];
  });
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.4 });
  fillTiled(H, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.35 });
  const blobs = bank.spread('blobs', w, h, 1);
  return {
    albedo: { base: A.canvas },
    ...finish(P, {
      depth: 0.02,
      soften: 0.003,
      grain: 0.04,
      post(height) {
        const low = new Float32Array(w * h);
        const rough = new Float32Array(w * h);
        for (let i = 0; i < low.length; i++) {
          low[i] = Math.min(1, Math.max(0, 0.5 + (0.5 - height[i]) * 0.9 + (blobs[i] - 0.5) * 0.9));
          rough[i] = 1 - 0.3 * smooth(0.55, 0.75, blobs[i]);
        }
        return { low, rough };
      },
    }),
  };
}

// ------------------------------------------------------------------------------------------------
// Masonry
// ------------------------------------------------------------------------------------------------

const BRICKS = {
  red: { tones: [0x7a3327, 0x6d2d23, 0x86392b, 0x74311f], burnt: 0x45201b, pale: 0x9a523b, mortar: 0x7b756a },
  brown: { tones: [0x5a4032, 0x4f382c, 0x654838, 0x574030], burnt: 0x35261e, pale: 0x7a5a45, mortar: 0x6a645b },
  tan: { tones: [0x9a8262, 0x8e7759, 0xa58c6a, 0x94805e], burnt: 0x6c5942, pale: 0xb49b79, mortar: 0x7c7466 },
};

/**
 * Brick in common bond (five stretcher courses, then one of headers): a 0.2 m brick on a 67 mm course.
 * One relief, four skins: red, brown, tan, and red under flaking paint.
 */
function brick(P) {
  const { w, h, bank, ppm } = P;
  const H = P.height;
  const R = P.rough;
  const cols = Math.round(w / P.m(0.2));
  const rows = cols * 3;
  const joint = Math.max(1, 0.011 * ppm);
  const layout = bondLayout(w, h, cols, rows, 6, prng(4401));

  fill(H, grey(0.2));
  fill(R, grey(0.98));
  for (const b of layout) {
    H.fillStyle = grey(0.62 + (b.a - 0.5) * 0.2);
    unit(H, w, b, joint);
    R.fillStyle = grey(b.b > 0.9 ? 0.62 : 0.84 + b.c * 0.1); // burnt bricks are glazed
    unit(R, w, b, joint);
  }
  fillTiled(H, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.4 });
  fillTiled(H, bank.grey('fine'), 3, 3, { mode: 'overlay', alpha: 0.3 });
  // Chipped arrises and spalled faces.
  specks(P, [H], Math.round(cols * rows * 0.5), 0.004 * ppm, 0.014 * ppm, (r) => [grey(0.25, 0.5 + r() * 0.4)]);

  const skins = new Map();
  function skin(name) {
    if (skins.has(name)) return skins.get(name);
    const A = canvas2d(w, h);
    const rand = prng(977 + name.length * 131);
    if (name === 'painted') {
      const paint = 0xbcb7a9;
      fill(A, css(shade(paint, 0.8)));
      for (const b of layout) {
        A.fillStyle = css(jitter(paint, rand, 0.035, 0.008));
        unit(A, w, b, joint * 0.8);
      }
      // Where the paint has let go the old red brick shows.
      const work = canvas2d(w, h);
      work.drawImage(skin('red'), 0, 0);
      fillTiled(work, bank.mask('mottle', 0.66, 0.72), 2, 2, { mode: 'destination-in' });
      A.drawImage(work.canvas, 0, 0);
      stain(A, bank.mask('streaks', 0.5, 0.9), css(0x57534a), { alpha: 0.28 });
    } else {
      const c = BRICKS[name];
      fill(A, css(c.mortar));
      for (const b of layout) {
        let tone = c.tones[Math.floor(b.a * c.tones.length) % c.tones.length];
        if (b.b > 0.9) tone = c.burnt;
        else if (b.b < 0.07) tone = c.pale;
        A.fillStyle = css(jitter(tone, rand, 0.07, 0.02));
        unit(A, w, b, joint);
      }
      // Mortar smeared and weathered over the brick edges.
      stain(A, bank.mask('fine', 0.55, 0.9), css(c.mortar), { alpha: 0.2, tilesX: 2 });
    }
    fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.32 });
    fillTiled(A, bank.grey('mottle'), 2, 2, { mode: 'soft-light', alpha: 0.4 });
    fillTiled(A, bank.grey('clouds'), 1, 1, { mode: 'multiply', alpha: 0.1 });
    skins.set(name, A.canvas);
    return A.canvas;
  }

  return {
    albedo: { red: () => skin('red'), brown: () => skin('brown'), tan: () => skin('tan'), painted: () => skin('painted') },
    ...finish(P, { depth: 0.011, soften: 0.0022, grain: 0.03 }),
  };
}

/** Cinder block: 0.4 × 0.2 m units, coarse open faces, struck joints. */
function cinder(P) {
  const { w, h, bank, ppm, rand } = P;
  const A = P.albedo;
  const H = P.height;
  const cols = Math.round(w / P.m(0.4));
  const rows = cols * 2;
  const joint = Math.max(1, 0.011 * ppm);
  const layout = bondLayout(w, h, cols, rows, 0, prng(7103));
  fill(A, css(0x5d5b55));
  fill(H, grey(0.22));
  for (const b of layout) {
    A.fillStyle = css(jitter(0x8c8a82, rand, 0.07, 0.012));
    unit(A, w, b, joint);
    H.fillStyle = grey(0.6 + (b.a - 0.5) * 0.08);
    unit(H, w, b, joint);
  }
  // The open texture of the block face: countless pits.
  specks(P, [A, H], Math.round(w * h * 0.006), 0.002 * ppm, 0.007 * ppm, (r) => [`rgba(38,37,34,${0.25 + r() * 0.45})`, grey(0.18, 0.75)]);
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.42 });
  fillTiled(H, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.5 });
  fillTiled(A, bank.grey('mottle'), 2, 2, { mode: 'soft-light', alpha: 0.45 });
  fillTiled(A, bank.grey('clouds'), 1, 1, { mode: 'multiply', alpha: 0.1 });
  stain(A, bank.mask('streaks', 0.55, 0.9), css(0x3d3b36), { alpha: 0.3 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.009, soften: 0.002, grain: 0.05 }) };
}

/** Cast concrete: lift lines from the formwork, tie holes, bug holes, water stains. */
function concrete(P) {
  const { w, h, bank, ppm, rand } = P;
  const A = P.albedo;
  const H = P.height;
  const R = P.rough;
  fill(A, css(0x7d7c77));
  fill(H, grey(0.55));
  fillTiled(A, bank.grey('clouds'), 1, 1, { mode: 'soft-light', alpha: 0.18 });
  fillTiled(A, bank.grey('mottle'), 2, 2, { mode: 'soft-light', alpha: 0.4 });
  fillTiled(H, bank.grey('mottle'), 2, 2, { mode: 'overlay', alpha: 0.25 });

  // Form lines every 0.6 m, panel joints every 1.2 m: a dark seam with a pale fin of grout beside it.
  const line = Math.max(1, 0.006 * ppm);
  const lifts = Math.round(h / P.m(0.6));
  for (let i = 0; i < lifts; i++) {
    const y = (i * h) / lifts;
    for (const [ctx, dark, pale] of [
      [A, 'rgba(40,40,38,0.5)', 'rgba(205,203,196,0.22)'],
      [H, grey(0.3, 0.9), grey(0.72, 0.8)],
    ]) {
      ctx.fillStyle = dark;
      ctx.fillRect(0, y - line / 2, w, line);
      ctx.fillRect(0, y - line / 2 + h, w, line);
      ctx.fillStyle = pale;
      ctx.fillRect(0, y + line / 2, w, line);
    }
    // Each lift came out a slightly different grey.
    A.fillStyle = rand() < 0.5 ? `rgba(0,0,0,${rand() * 0.07})` : `rgba(255,255,255,${rand() * 0.06})`;
    A.fillRect(0, y, w, h / lifts);
  }
  const panels = Math.round(w / P.m(1.2));
  for (let i = 0; i < panels; i++) {
    const x = (i * w) / panels;
    A.fillStyle = 'rgba(40,40,38,0.35)';
    A.fillRect(x - line / 2, 0, line, h);
    A.fillRect(x - line / 2 + w, 0, line, h);
    H.fillStyle = grey(0.34, 0.8);
    H.fillRect(x - line / 2, 0, line, h);
    H.fillRect(x - line / 2 + w, 0, line, h);
  }
  // Tie holes on a 0.6 m grid, some weeping rust.
  const tie = 0.013 * ppm;
  for (let j = 0; j < lifts; j++) {
    for (let i = 0; i < panels * 2; i++) {
      const x = ((i + 0.5) * w) / (panels * 2);
      const y = ((j + 0.5) * h) / lifts;
      if (rand() < 0.4) {
        const len = P.m(0.08 + rand() * 0.25);
        const g = A.createLinearGradient(0, y, 0, y + len);
        g.addColorStop(0, 'rgba(96,58,34,0.5)');
        g.addColorStop(1, 'rgba(96,58,34,0)');
        A.fillStyle = g;
        A.fillRect(x - tie * 0.7, y, tie * 1.4, len);
      }
      for (const [ctx, style] of [[A, 'rgba(26,25,24,0.8)'], [H, grey(0.05)]]) {
        ctx.fillStyle = style;
        ctx.beginPath();
        ctx.arc(x, y, tie, 0, TAU);
        ctx.fill();
      }
    }
  }
  specks(P, [A, H], Math.round(w * h * 0.0012), 0.0015 * ppm, 0.006 * ppm, (r) => [`rgba(30,30,28,${0.3 + r() * 0.5})`, grey(0.1, 0.8)]);
  stain(A, bank.mask('streaks', 0.5, 0.9), css(0x3a3935), { alpha: 0.35 });
  stain(R, bank.mask('streaks', 0.5, 0.9), grey(0.7), { alpha: 0.5 });
  stain(A, bank.mask('mottle', 0.66, 0.9), css(0xb5b3aa), { alpha: 0.16, ox: 0.5, oy: 0.3 }); // efflorescence
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.3 });
  fillTiled(H, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.25 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.006, soften: 0.002, grain: 0.03 }) };
}

/** Stucco: a pale, lumpy render. Neutral in colour so the material tint decides. */
function stucco(P) {
  const { w, h, bank } = P;
  const A = P.albedo;
  const H = P.height;
  fill(A, css(0xf0eee8));
  fill(H, grey(0.5));
  fillTiled(H, bank.grey('fine'), 2, 2, { mode: 'overlay', alpha: 1 });
  fillTiled(H, bank.grey('mottle'), 2, 2, { mode: 'overlay', alpha: 0.5 });
  fillTiled(H, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.4 });
  fillTiled(A, bank.grey('fine'), 2, 2, { mode: 'multiply', alpha: 0.2 });
  fillTiled(A, bank.grey('clouds'), 1, 1, { mode: 'multiply', alpha: 0.12 });
  stain(A, bank.mask('streaks', 0.5, 0.9), css(0x6a665c), { alpha: 0.3 });
  // A hairline crack where the render has moved.
  wander(P, [A, H], ['rgba(60,56,50,0.3)', grey(0.2, 0.7)], P.rand() * w, P.rand() * h, Math.PI / 2 + (P.rand() - 0.5), P.m(0.5), Math.max(1, 0.002 * P.ppm), 0.6);
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.008, soften: 0.002, grain: 0.04 }) };
}

/** White glazed wall tile in running bond with grimy grout. */
function tile(P) {
  const { w, h, bank, ppm, rand } = P;
  const A = P.albedo;
  const H = P.height;
  const R = P.rough;
  const cols = Math.round(w / P.m(0.15));
  const rows = cols * 2;
  const joint = Math.max(1, 0.004 * ppm);
  const layout = bondLayout(w, h, cols, rows, 0, prng(311));
  fill(A, css(0x5d5a52));
  fill(H, grey(0.25));
  fill(R, grey(0.9));
  for (const b of layout) {
    const cracked = b.b > 0.95;
    A.fillStyle = css(jitter(cracked ? 0xc4c0b2 : 0xdcd9cf, rand, 0.03, 0.01));
    unit(A, w, b, joint);
    H.fillStyle = grey(0.7);
    unit(H, w, b, joint);
    R.fillStyle = grey(cracked ? 0.5 : 0.2 + b.c * 0.08);
    unit(R, w, b, joint);
    if (cracked) wander(P, [A, H], ['rgba(70,66,58,0.7)', grey(0.3)], b.x + b.w * 0.2, b.y + b.h * 0.5, (rand() - 0.5) * 1.2, b.w * 0.7, 1, 0.9);
  }
  stain(A, bank.mask('clouds', 0.5, 0.85), css(0x77725f), { alpha: 0.2 });
  stain(R, bank.mask('clouds', 0.5, 0.85), grey(0.5), { alpha: 0.5 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.003, soften: 0.0015 }) };
}

// ------------------------------------------------------------------------------------------------
// Metal
// ------------------------------------------------------------------------------------------------

/** Plain sheet metal, neutral: faint brushing, scuffs and handling marks. Tinted by the material. */
function metal(P) {
  const { w, h, bank, rand } = P;
  const A = P.albedo;
  const H = P.height;
  const R = P.rough;
  fill(A, css(0xf2f2f2));
  fill(H, grey(0.5));
  fill(R, grey(0.5));
  fillTiled(A, bank.grey('streaks'), 1, 1, { mode: 'multiply', alpha: 0.16 });
  fillTiled(A, bank.grey('mottle'), 2, 2, { mode: 'multiply', alpha: 0.2 });
  fillTiled(R, bank.grey('mottle'), 2, 2, { mode: 'overlay', alpha: 0.7 });
  fillTiled(R, bank.grey('streaks'), 1, 1, { mode: 'overlay', alpha: 0.5 });
  for (let i = 0; i < 26; i++) {
    const style = rand() < 0.5 ? 'rgba(255,255,255,0.35)' : 'rgba(40,40,40,0.3)';
    wander(P, [A, H, R], [style, grey(0.35, 0.6), grey(0.75, 0.7)], rand() * w, rand() * h, rand() * TAU, P.m(0.05 + rand() * 0.3), 1, 0.25);
  }
  stain(A, bank.mask('clouds', 0.55, 0.9), css(0x55524c), { alpha: 0.3 });
  stain(P.metal, bank.mask('clouds', 0.55, 0.9), grey(0.6), { alpha: 0.5 });

  // Galvanised steel: the same sheet under a spangle of zinc crystals.
  const galv = () => {
    const G = canvas2d(w, h);
    const cells = cellular(w, h, Math.round(P.w / P.m(0.022)), 53);
    const field = new Float32Array(w * h);
    for (let i = 0; i < field.length; i++) field[i] = 0.74 + 0.26 * cells.id[i];
    G.drawImage(fieldToCanvas(field, w, h), 0, 0);
    G.globalAlpha = 0.5;
    G.globalCompositeOperation = 'multiply';
    G.drawImage(A.canvas, 0, 0);
    return G.canvas;
  };
  return { albedo: { base: A.canvas, galv }, ...finish(P, { depth: 0.0008, grain: 0.03 }) };
}

/**
 * The El's steel: built-up riveted plate under layers of dark green paint, rust weeping from the
 * rivets. 0.6 m wide (a column face) and 2.4 m tall, with a splice plate half way up.
 */
function steelEl(P) {
  const { w, h, bank, ppm, rand } = P;
  const A = P.albedo;
  const H = P.height;
  const R = P.rough;
  const M = P.metal;
  const paint = 0x212d28;
  const rust = 0x6b3a1e;
  fill(A, css(paint));
  fill(H, grey(0.4));
  fill(R, grey(0.52));
  fill(M, grey(0.45)); // paint over steel: only half as metallic as the bare catalogue value
  stain(A, bank.mask('streaks', 0.4, 0.9), css(shade(paint, 0.6)), { alpha: 0.5, tilesX: 1, tilesY: 4 });
  stain(A, bank.mask('mottle', 0.5, 0.9), css(shade(paint, 1.5)), { alpha: 0.25, tilesX: 1, tilesY: 4 });

  // Splice plate.
  const p0 = P.m(1.05);
  const p1 = P.m(1.35);
  for (const [ctx, face, top, bottom] of [
    [A, css(shade(paint, 1.12)), 'rgba(255,255,255,0.12)', 'rgba(0,0,0,0.5)'],
    [H, grey(0.56), null, null],
  ]) {
    ctx.fillStyle = face;
    ctx.fillRect(0, p0, w, p1 - p0);
    if (top) {
      ctx.fillStyle = top;
      ctx.fillRect(0, p0, w, Math.max(1, 0.004 * ppm));
      ctx.fillStyle = bottom;
      ctx.fillRect(0, p1, w, Math.max(1, 0.006 * ppm));
    }
  }

  // Rivets: two rows up the edges, two rows across the splice plate.
  const rivets = [];
  for (let y = 0.06; y < 2.4; y += 0.12) for (const x of [0.06, 0.54]) rivets.push([x, y]);
  for (const y of [1.11, 1.29]) for (const x of [0.18, 0.3, 0.42]) rivets.push([x, y]);
  const rr = 0.016 * ppm;
  for (const [mx, my] of rivets) {
    const x = P.m(mx);
    const y = P.m(my);
    const rusty = rand() < 0.4;
    if (rusty) {
      // A drip that has run down from under the rivet head.
      const len = P.m(0.08 + rand() * rand() * 0.6);
      const wd = rr * (1 + rand() * 0.8);
      for (const [ctx, c0, c1] of [
        [A, css(rust, 0.75), css(rust, 0)],
        [R, grey(0.92, 0.8), grey(0.92, 0)],
        [M, grey(0.2, 0.8), grey(0.2, 0)],
      ]) {
        for (const dy of [0, -h]) {
          const g = ctx.createLinearGradient(0, y + dy, 0, y + dy + len);
          g.addColorStop(0, c0);
          g.addColorStop(1, c1);
          ctx.fillStyle = g;
          ctx.fillRect(x - wd / 2, y + dy, wd, len);
        }
      }
    }
    const g = H.createRadialGradient(x, y, 0, x, y, rr);
    g.addColorStop(0, grey(0.95));
    g.addColorStop(0.7, grey(0.8));
    g.addColorStop(1, grey(0.4, 0));
    H.fillStyle = g;
    H.beginPath();
    H.arc(x, y, rr, 0, TAU);
    H.fill();
    A.fillStyle = 'rgba(0,0,0,0.45)';
    A.beginPath();
    A.arc(x, y + rr * 0.25, rr * 1.15, 0, TAU);
    A.fill();
    A.fillStyle = css(rusty ? mixHex(paint, rust, 0.6) : shade(paint, 1.25));
    A.beginPath();
    A.arc(x, y, rr * 0.92, 0, TAU);
    A.fill();
  }
  // Paint chips and scabs of rust.
  specks(P, [A, H, R, M], Math.round(70 * (h / P.m(2.4))), 0.004 * ppm, 0.03 * ppm, (r) => [
    css(shade(rust, 0.7 + r() * 0.6), 0.85),
    grey(0.3, 0.7),
    grey(0.92),
    grey(0.2),
  ]);
  stain(A, bank.mask('blobs', 0.62, 0.8), css(rust), { alpha: 0.45, tilesX: 1, tilesY: 4 });
  stain(R, bank.mask('blobs', 0.62, 0.8), grey(0.92), { alpha: 0.6, tilesX: 1, tilesY: 4 });
  stain(M, bank.mask('blobs', 0.62, 0.8), grey(0.2), { alpha: 0.6, tilesX: 1, tilesY: 4 });
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.25 });
  fillTiled(H, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.2 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.012, soften: 0.001, grain: 0.02 }) };
}

/** Steel that has been left out for years: scale, pits, the last flakes of paint. */
function rust(P) {
  const { w, h, bank, ppm } = P;
  const A = P.albedo;
  const H = P.height;
  const R = P.rough;
  const M = P.metal;
  fill(A, css(0x5c3a25));
  fill(H, grey(0.5));
  fill(R, grey(0.88));
  fill(M, grey(0.6));
  stain(A, bank.mask('mottle', 0.35, 0.75), css(0x7c4420), { alpha: 0.8, tilesX: 2 });
  stain(A, bank.mask('clouds', 0.45, 0.8), css(0x2f2019), { alpha: 0.5 });
  stain(A, bank.mask('fine', 0.55, 0.8), css(0x9a5a26), { alpha: 0.45, tilesX: 2 });
  stain(A, bank.mask('blobs', 0.7, 0.76), css(0x464d48), { alpha: 0.6, ox: 0.2, tilesX: 2 }); // paint that still holds
  stain(R, bank.mask('blobs', 0.7, 0.76), grey(0.55), { alpha: 0.9, ox: 0.2, tilesX: 2 });
  stain(M, bank.mask('clouds', 0.45, 0.8), grey(0.2), { alpha: 0.8 });
  fillTiled(H, bank.grey('fine'), 2, 2, { mode: 'overlay', alpha: 0.9 });
  fillTiled(H, bank.grey('mottle'), 2, 2, { mode: 'overlay', alpha: 0.6 });
  specks(P, [A, H], Math.round(w * h * 0.003), 0.002 * ppm, 0.008 * ppm, (r) => [`rgba(30,18,12,${0.3 + r() * 0.5})`, grey(0.15, 0.8)]);
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.35 });
  fillTiled(H, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.4 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.004, soften: 0.001, grain: 0.05 }) };
}

/** Roll-down security gate: 75 mm curved slats, grime in the laps, streaks from above. */
function rollGate(P) {
  const { w, h, bank, ppm, rand } = P;
  const A = P.albedo;
  const H = P.height;
  const R = P.rough;
  const slats = Math.round(h / P.m(0.075));
  const sh = h / slats;
  fill(R, grey(0.52));
  for (let i = 0; i < slats; i++) {
    const y = i * sh;
    // Each slat bows outward and tucks under the one above.
    const g = H.createLinearGradient(0, y, 0, y + sh);
    g.addColorStop(0, grey(0.08));
    g.addColorStop(0.16, grey(0.62));
    g.addColorStop(0.55, grey(0.92));
    g.addColorStop(0.9, grey(0.6));
    g.addColorStop(1, grey(0.3));
    H.fillStyle = g;
    H.fillRect(0, y, w, sh + 1);
    A.fillStyle = css(jitter(0xf0f0f0, rand, 0.04, 0));
    A.fillRect(0, y, w, sh + 1);
    const lap = A.createLinearGradient(0, y, 0, y + sh * 0.3);
    lap.addColorStop(0, 'rgba(20,20,20,0.75)');
    lap.addColorStop(1, 'rgba(20,20,20,0)');
    A.fillStyle = lap;
    A.fillRect(0, y, w, sh * 0.3);
    R.fillStyle = grey(0.85, 0.8);
    R.fillRect(0, y, w, Math.max(1, sh * 0.14));
  }
  fillTiled(A, bank.grey('streaks'), 1, 1, { mode: 'multiply', alpha: 0.45 });
  fillTiled(A, bank.grey('mottle'), 2, 2, { mode: 'multiply', alpha: 0.25 });
  stain(A, bank.mask('clouds', 0.58, 0.85), css(0x6b4a30), { alpha: 0.25 });
  fillTiled(R, bank.grey('streaks'), 1, 1, { mode: 'overlay', alpha: 0.6 });
  stain(P.metal, bank.mask('streaks', 0.55, 0.95), grey(0.55), { alpha: 0.6 });
  // Dents and scrapes at random.
  for (let i = 0; i < 10; i++) {
    wander(P, [A, H], ['rgba(250,250,250,0.3)', grey(0.4, 0.5)], rand() * w, rand() * h, (rand() - 0.5) * 0.6, P.m(0.05 + rand() * 0.2), Math.max(1, 0.004 * ppm), 0.3);
  }
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.18 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.014, soften: 0.001, grain: 0.012 }) };
}

/** Corrugated sheet: 75 mm waves running up the wall, dirt in the troughs, a fixing line per sheet. */
function corrugated(P) {
  const { w, h, bank, ppm, rand } = P;
  const A = P.albedo;
  const H = P.height;
  const R = P.rough;
  const waves = Math.round(w / P.m(0.075));
  const pitch = w / waves;
  const profile = canvas2d(Math.max(2, Math.round(pitch)), 1);
  const shadow = canvas2d(Math.max(2, Math.round(pitch)), 1);
  for (let x = 0; x < profile.canvas.width; x++) {
    const s = 0.5 - 0.5 * Math.cos((x / profile.canvas.width) * TAU);
    profile.fillStyle = grey(s);
    profile.fillRect(x, 0, 1, 1);
    shadow.fillStyle = grey(0.72 + 0.28 * s);
    shadow.fillRect(x, 0, 1, 1);
  }
  fillTiled(H, profile.canvas, waves, 1);
  fill(A, css(0xf0f0f0));
  fillTiled(A, shadow.canvas, waves, 1, { mode: 'multiply' });
  fill(R, grey(0.58));
  fillTiled(A, bank.grey('streaks'), 1, 1, { mode: 'multiply', alpha: 0.4 });
  fillTiled(A, bank.grey('clouds'), 1, 1, { mode: 'multiply', alpha: 0.3 });
  stain(A, bank.mask('streaks', 0.6, 0.95), css(0x6e4526), { alpha: 0.5, ox: 0.3 });
  stain(R, bank.mask('streaks', 0.6, 0.95), grey(0.9), { alpha: 0.7, ox: 0.3 });
  stain(P.metal, bank.mask('streaks', 0.6, 0.95), grey(0.3), { alpha: 0.7, ox: 0.3 });
  // Sheet lap with a row of fixings at the top of the tile.
  A.fillStyle = 'rgba(0,0,0,0.35)';
  A.fillRect(0, 0, w, Math.max(1, 0.006 * ppm));
  H.fillStyle = grey(0, 0.5);
  H.fillRect(0, 0, w, Math.max(1, 0.006 * ppm));
  for (let i = 0; i < waves; i += 2) {
    const x = (i + 0.5) * pitch;
    const y = P.m(0.05);
    for (const [ctx, style, r] of [[A, 'rgba(30,30,30,0.8)', 0.007], [H, grey(1), 0.008]]) {
      ctx.fillStyle = style;
      ctx.beginPath();
      ctx.arc(x, y, r * ppm, 0, TAU);
      ctx.fill();
    }
    if (rand() < 0.3) {
      const g = A.createLinearGradient(0, y, 0, y + P.m(0.3));
      g.addColorStop(0, 'rgba(110,69,38,0.6)');
      g.addColorStop(1, 'rgba(110,69,38,0)');
      A.fillStyle = g;
      A.fillRect(x - 0.006 * ppm, y, 0.012 * ppm, P.m(0.3));
    }
  }
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.2 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.016, grain: 0.012 }) };
}

/**
 * Chain-link mesh as coverage: RGBA bytes with the wire colour everywhere (so filtering never drags in
 * black) and alpha = how much of the pixel a wire covers. 8 diamonds across 0.6 m.
 * Returns {data, size}.
 */
export function chainlinkPixels(size, diamonds = 8, wire = 0.085) {
  const data = new Uint8Array(size * size * 4);
  const d = size / diamonds; // diagonal period in pixels
  const half = (wire * d) / 2; // half wire width, measured along the diagonal axis
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      // Distance to the nearest wire of each family (lines x ± y = k·d), anti-aliased over one pixel.
      const a = (((x + y) % d) + d) % d;
      const b = (((x - y) % d) + d) % d;
      const da = Math.min(a, d - a) * Math.SQRT1_2;
      const db = Math.min(b, d - b) * Math.SQRT1_2;
      const dist = Math.min(da, db);
      const cover = Math.min(1, Math.max(0, half - dist + 0.5));
      // The wire is round: brighter along its crown. One family passes over the other at each knuckle.
      const crown = 1 - Math.min(1, dist / Math.max(0.5, half));
      const over = da < db ? 1 : 0.86;
      const v = (150 + 90 * crown) * over;
      const o = (y * size + x) * 4;
      data[o] = v;
      data[o + 1] = v * 1.02 > 255 ? 255 : v * 1.02;
      data[o + 2] = v * 1.05 > 255 ? 255 : v * 1.05;
      data[o + 3] = cover * 255;
    }
  }
  return { data, size };
}

// ------------------------------------------------------------------------------------------------
// Paint, plastics, rubber
// ------------------------------------------------------------------------------------------------

/** Painted surface, neutral: orange peel, runs, grime in the low places, the odd chip. */
function paint(P) {
  const { w, h, bank, ppm } = P;
  const A = P.albedo;
  const H = P.height;
  const R = P.rough;
  fill(A, css(0xf6f6f4));
  fill(H, grey(0.5));
  fill(R, grey(0.5));
  fillTiled(H, bank.grey('fine'), 4, 4, { mode: 'overlay', alpha: 0.5 });
  fillTiled(A, bank.grey('clouds'), 1, 1, { mode: 'multiply', alpha: 0.22 });
  fillTiled(A, bank.grey('mottle'), 2, 2, { mode: 'multiply', alpha: 0.14 });
  stain(A, bank.mask('streaks', 0.55, 0.95), css(0x4a4741), { alpha: 0.3 });
  fillTiled(R, bank.grey('clouds'), 1, 1, { mode: 'overlay', alpha: 0.8 });
  fillTiled(R, bank.grey('streaks'), 1, 1, { mode: 'overlay', alpha: 0.5 });
  specks(P, [A, H, R], Math.round(60 * (w / P.m(1.5)) ** 2), 0.002 * ppm, 0.009 * ppm, (r) => [`rgba(52,44,38,${0.4 + r() * 0.5})`, grey(0.2, 0.8), grey(0.85)]);
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.0012, grain: 0.02 }) };
}

/** Fine pebble grain for moulded plastic and rubber: relief only. */
function pebble(P) {
  const { w, h, bank } = P;
  const H = P.height;
  fill(H, grey(0.5));
  fillTiled(H, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.9 });
  fillTiled(H, bank.grey('fine'), 2, 2, { mode: 'overlay', alpha: 0.6 });
  return { albedo: null, ...finish(P, { depth: 0.0009, soften: 0.0005 }) };
}

/** Tyre tread: ribs and grooves round the tyre, sipes cut across the ribs. */
function tire(P) {
  const { w, h, ppm } = P;
  const A = P.albedo;
  const H = P.height;
  const ribs = Math.round(h / P.m(0.06));
  const rh = h / ribs;
  const groove = Math.max(2, 0.012 * ppm);
  fill(A, css(0x070707));
  fill(H, grey(0.1));
  for (let i = 0; i < ribs; i++) {
    const y = i * rh + groove / 2;
    A.fillStyle = css(0x1b1b1c);
    A.fillRect(0, y, w, rh - groove);
    H.fillStyle = grey(0.85);
    H.fillRect(0, y, w, rh - groove);
    // Sipes: slanted cuts, mirrored rib to rib.
    const step = P.m(0.03);
    const lean = (i % 2 ? 1 : -1) * (rh - groove) * 0.6;
    for (const [ctx, style] of [[A, css(0x050505)], [H, grey(0.2)]]) {
      ctx.strokeStyle = style;
      ctx.lineWidth = Math.max(1, 0.004 * ppm);
      ctx.beginPath();
      for (let x = -step; x < w + step; x += step) {
        ctx.moveTo(x, y + (rh - groove) * 0.1);
        ctx.lineTo(x + lean, y + (rh - groove) * 0.9);
      }
      ctx.stroke();
    }
  }
  // Road dust rubbed into the faces.
  fillTiled(A, P.bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.25 });
  stain(A, P.bank.mask('mottle', 0.5, 0.9), css(0x3a3833), { alpha: 0.3 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.007, soften: 0.001, grain: 0.03 }) };
}

/** Wrinkled bin-bag plastic: relief and gloss only. */
function wrinkle(P) {
  const { w, h, bank } = P;
  const ridges = resample(fbm(bank.size, bank.size, 5, 5, 4, 131, 0.6, true), bank.size, w, h, 1);
  const soft = bank.spread('mottle', w, h, 1);
  const H = P.height;
  H.drawImage(fieldToCanvas(ridges, w, h), 0, 0);
  const rough = new Float32Array(w * h);
  for (let i = 0; i < rough.length; i++) rough[i] = 0.75 + 0.5 * (soft[i] - 0.5) + 0.25 * (0.5 - ridges[i]);
  return { albedo: null, ...finish(P, { depth: 0.02, soften: 0.002, post: () => ({ rough }) }) };
}

// ------------------------------------------------------------------------------------------------
// Wood, board, cloth, leaves
// ------------------------------------------------------------------------------------------------

/** Weathered boards 150 mm wide running along u: grain, knots, gaps, nail heads. */
function wood(P) {
  const { w, h, bank, ppm, rand } = P;
  const A = P.albedo;
  const H = P.height;
  const planks = Math.round(h / P.m(0.15));
  const ph = h / planks;
  const grain = bank.grey('streaks');
  for (let i = 0; i < planks; i++) {
    const y = i * ph;
    A.fillStyle = css(jitter(0x70543a, rand, 0.12, 0.03));
    A.fillRect(0, y, w, ph + 1);
    H.fillStyle = grey(0.6 + (rand() - 0.5) * 0.1);
    H.fillRect(0, y, w, ph + 1);
    // Grain: the vertical-streak layer turned on its side, shifted per board.
    for (const [ctx, alpha, mode] of [[A, 0.55, 'multiply'], [H, 0.5, 'overlay']]) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, y, w, ph);
      ctx.clip();
      ctx.translate(0, y + ph);
      ctx.rotate(-Math.PI / 2);
      ctx.globalAlpha = alpha;
      ctx.globalCompositeOperation = mode;
      const scale = (ph * 3) / grain.width;
      ctx.scale(scale, w / grain.height);
      ctx.fillStyle = ctx.createPattern(grain, 'repeat');
      ctx.translate(rand() * grain.width, 0);
      ctx.fillRect(-grain.width, 0, grain.width * 3, grain.height);
      ctx.restore();
    }
    // A butt joint somewhere along the board, with nails either side.
    const jx = rand() * w;
    for (const [ctx, style] of [[A, 'rgba(18,13,9,0.8)'], [H, grey(0.1)]]) {
      ctx.fillStyle = style;
      ctx.fillRect(jx, y, Math.max(1, 0.004 * ppm), ph);
      for (const nx of [jx - 0.03 * ppm, jx + 0.035 * ppm]) {
        for (const ny of [y + ph * 0.25, y + ph * 0.75]) {
          ctx.beginPath();
          ctx.arc(nx, ny, Math.max(1, 0.004 * ppm), 0, TAU);
          ctx.fill();
        }
      }
    }
    if (rand() < 0.5) {
      const kx = rand() * w;
      const ky = y + ph * (0.3 + rand() * 0.4);
      const kr = ph * (0.08 + rand() * 0.1);
      const g = A.createRadialGradient(kx, ky, 0, kx, ky, kr * 2.2);
      g.addColorStop(0, 'rgba(24,15,9,0.9)');
      g.addColorStop(0.45, 'rgba(48,31,18,0.6)');
      g.addColorStop(1, 'rgba(48,31,18,0)');
      A.fillStyle = g;
      A.beginPath();
      A.ellipse(kx, ky, kr * 3, kr * 1.6, 0, 0, TAU);
      A.fill();
    }
  }
  const gap = Math.max(1, 0.005 * ppm);
  for (let i = 0; i <= planks; i++) {
    A.fillStyle = 'rgba(10,8,6,0.9)';
    A.fillRect(0, i * ph - gap / 2, w, gap);
    H.fillStyle = grey(0);
    H.fillRect(0, i * ph - gap / 2, w, gap);
  }
  stain(A, bank.mask('clouds', 0.5, 0.85), css(0x8a8578), { alpha: 0.3 }); // silvered by weather
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.2 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.006, soften: 0.001, grain: 0.03 }) };
}

/** Plywood sheet, 2.44 × 1.22 m: rotary-cut grain, boat patches, screws along the edges. */
function plywood(P) {
  const { w, h, bank, ppm, rand } = P;
  const A = P.albedo;
  const H = P.height;
  const warp = bank.spread('clouds', w, h, 2, 1);
  const fine = bank.spread('streaks', h, w, 2, 1); // read sideways below
  const image = A.createImageData(w, h);
  const data = image.data;
  const base = [0xae, 0x8e, 0x5f];
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x;
      // Wide wandering bands: the cathedral figure of peeled veneer.
      const band = Math.sin((y / h) * 9 * TAU + warp[i] * 16);
      const fibre = fine[x * h + y];
      const k = 0.88 + 0.04 * band + 0.14 * (fibre - 0.5);
      const o = i * 4;
      data[o] = base[0] * k;
      data[o + 1] = base[1] * k;
      data[o + 2] = base[2] * (k - 0.02 * band);
      data[o + 3] = 255;
    }
  }
  A.putImageData(image, 0, 0);
  fill(H, grey(0.5));
  // Boat-shaped repairs let into the face veneer.
  for (let i = 0; i < 5; i++) {
    const x = rand() * w;
    const y = rand() * h;
    const len = P.m(0.09 + rand() * 0.05);
    A.fillStyle = css(jitter(0xbb9c6c, rand, 0.06));
    A.strokeStyle = 'rgba(60,42,22,0.6)';
    A.lineWidth = 1;
    A.beginPath();
    A.ellipse(x, y, len, len * 0.3, 0, 0, TAU);
    A.fill();
    A.stroke();
  }
  stain(A, bank.mask('clouds', 0.52, 0.8), css(0x4c3a25), { alpha: 0.35, tilesX: 2, tilesY: 1 });
  stain(A, bank.mask('streaks', 0.6, 0.95), css(0x3c3024), { alpha: 0.3, tilesX: 2, tilesY: 1 });
  // Sheet edge and its screws.
  const edge = Math.max(1, 0.004 * ppm);
  for (const [ctx, style] of [[A, 'rgba(20,14,8,0.85)'], [H, grey(0.05)]]) {
    ctx.fillStyle = style;
    ctx.fillRect(0, 0, w, edge);
    ctx.fillRect(0, 0, edge, h);
    for (let x = P.m(0.2); x < w; x += P.m(0.4)) {
      for (const y of [P.m(0.04), h - P.m(0.04)]) {
        ctx.beginPath();
        ctx.arc(x, y, Math.max(1, 0.005 * ppm), 0, TAU);
        ctx.fill();
      }
    }
  }
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.2 });
  fillTiled(H, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.25 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.003, soften: 0.001, grain: 0.03 }) };
}

/** Corrugated cardboard: kraft liner, the flutes telegraphing through, creases and tape. */
function cardboard(P) {
  const { w, h, bank, ppm, rand } = P;
  const A = P.albedo;
  const H = P.height;
  fill(A, css(0x9d7e55));
  fill(H, grey(0.5));
  const flute = Math.max(3, Math.round(0.008 * ppm));
  for (let x = 0; x < w; x += flute) {
    A.fillStyle = 'rgba(60,42,22,0.12)';
    A.fillRect(x, 0, Math.max(1, flute / 3), h);
    H.fillStyle = grey(0.35, 0.6);
    H.fillRect(x, 0, Math.max(1, flute / 3), h);
  }
  fillTiled(A, bank.grey('clouds'), 1, 1, { mode: 'soft-light', alpha: 0.5 });
  fillTiled(A, bank.grey('mottle'), 2, 2, { mode: 'multiply', alpha: 0.2 });
  stain(A, bank.mask('blobs', 0.6, 0.8), css(0x5e4830), { alpha: 0.4 });
  for (let i = 0; i < 5; i++) {
    wander(P, [A, H], ['rgba(214,190,150,0.5)', grey(0.75, 0.8)], rand() * w, rand() * h, rand() * TAU, P.m(0.2 + rand() * 0.4), Math.max(1, 0.004 * ppm), 0.2);
  }
  // A band of packing tape.
  const ty = h * 0.5;
  const th = P.m(0.05);
  A.fillStyle = 'rgba(196,170,120,0.55)';
  A.fillRect(0, ty - th / 2, w, th);
  P.rough.fillStyle = grey(0.35);
  P.rough.fillRect(0, ty - th / 2, w, th);
  fillTiled(A, bank.grain(w, h), 1, 1, { mode: 'overlay', alpha: 0.25 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.0015, grain: 0.03 }) };
}

/** Plain-weave canvas, neutral: for awnings, tarps, hoodies. */
function fabric(P) {
  const { w, h, bank } = P;
  const A = P.albedo;
  const H = P.height;
  const pitch = Math.max(4, Math.round(P.m(0.004) / 2) * 2);
  const cell = canvas2d(pitch, pitch);
  const half = pitch / 2;
  // Two threads over, two under: each quadrant is a short bowed thread, running across or up.
  for (let q = 0; q < 4; q++) {
    const qx = (q % 2) * half;
    const qy = Math.floor(q / 2) * half;
    const horizontal = q === 0 || q === 3;
    const g = horizontal ? cell.createLinearGradient(0, qy, 0, qy + half) : cell.createLinearGradient(qx, 0, qx + half, 0);
    g.addColorStop(0, grey(0.25));
    g.addColorStop(0.5, grey(horizontal ? 0.95 : 0.8));
    g.addColorStop(1, grey(0.25));
    cell.fillStyle = g;
    cell.fillRect(qx, qy, half, half);
  }
  fillTiled(H, cell.canvas, w / pitch, h / pitch);
  fill(A, css(0xf4f4f2));
  fillTiled(A, cell.canvas, w / pitch, h / pitch, { mode: 'multiply', alpha: 0.3 });
  fillTiled(A, bank.grey('clouds'), 1, 1, { mode: 'multiply', alpha: 0.16 });
  stain(A, bank.mask('streaks', 0.62, 0.95), css(0x3c3a36), { alpha: 0.12 });
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.0014 }) };
}

/** A mass of leaves seen from outside the canopy. */
function leaves(P) {
  const { w, h, ppm, rand } = P;
  const A = P.albedo;
  const H = P.height;
  fill(A, css(0x0c160e));
  fill(H, grey(0.1));
  const count = Math.round(900 * (w / P.m(1.2)) ** 2);
  for (let i = 0; i < count; i++) {
    const x = rand() * w;
    const y = rand() * h;
    const len = (0.03 + rand() * 0.035) * ppm;
    const rot = rand() * TAU;
    const depth = i / count; // later leaves lie on top
    const tone = css(jitter(mixHex(0x14261a, 0x2f4a2c, depth * (0.5 + rand() * 0.5)), rand, 0.12, 0.03));
    wrapDraw(w, h, x, y, len + 1, (dx, dy) => {
      for (const [ctx, style] of [[A, tone], [H, grey(0.25 + depth * 0.7)]]) {
        ctx.save();
        ctx.translate(x + dx, y + dy);
        ctx.rotate(rot);
        ctx.fillStyle = style;
        ctx.beginPath();
        ctx.moveTo(-len, 0);
        ctx.quadraticCurveTo(0, -len * 0.55, len, 0);
        ctx.quadraticCurveTo(0, len * 0.55, -len, 0);
        ctx.fill();
        if (ctx === A) {
          ctx.strokeStyle = 'rgba(120,150,100,0.25)';
          ctx.lineWidth = Math.max(0.5, len * 0.05);
          ctx.beginPath();
          ctx.moveTo(-len * 0.9, 0);
          ctx.lineTo(len * 0.9, 0);
          ctx.stroke();
        }
        ctx.restore();
      }
    });
  }
  return { albedo: { base: A.canvas }, ...finish(P, { depth: 0.02, soften: 0.001 }) };
}

/** Handling marks, dried rain and dust for glass and car bodies: roughness only. */
function smudge(P) {
  const { w, h, bank } = P;
  const clouds = bank.spread('clouds', w, h, 1);
  const streaks = bank.spread('streaks', w, h, 1);
  const mottle = bank.spread('mottle', w, h, 2);
  const rough = new Float32Array(w * h);
  for (let i = 0; i < rough.length; i++) {
    rough[i] = 0.4 + 0.3 * smooth(0.45, 0.8, clouds[i]) + 0.25 * smooth(0.55, 0.9, streaks[i]) + 0.12 * (mottle[i] - 0.5);
  }
  return { albedo: null, normal: null, orm: ormCanvas(w, h, rough) };
}

// ------------------------------------------------------------------------------------------------
// Registry
// ------------------------------------------------------------------------------------------------

/**
 * tile   metres covered by one repeat [u, v]
 * res    size relative to the quality tier's texture size (the tile's width)
 * rough  the roughness the set's ORM is painted around (a material's own roughness scales it)
 * aniso  'ground' | 'wall' | 'prop': how hard the set is filtered at glancing angles
 */
export const SETS = {
  asphalt: { tile: [4, 4], res: 1, rough: 0.82, aniso: 'ground', build: asphalt },
  sidewalk: { tile: [4.5, 4.5], res: 1, rough: 0.9, aniso: 'ground', build: sidewalk },
  dirt: { tile: [3, 3], res: 0.5, rough: 1, aniso: 'ground', build: dirt },
  brick: { tile: [2.4, 2.4], res: 1, rough: 0.9, aniso: 'wall', build: brick },
  cinder: { tile: [2.4, 2.4], res: 1, rough: 0.95, aniso: 'wall', build: cinder },
  concrete: { tile: [2.4, 2.4], res: 1, rough: 0.9, aniso: 'wall', build: concrete },
  stucco: { tile: [2, 2], res: 0.5, rough: 1, aniso: 'wall', build: stucco },
  tile: { tile: [0.6, 0.6], res: 0.5, rough: 0.35, aniso: 'wall', build: tile },
  metal: { tile: [1.5, 1.5], res: 0.5, rough: 0.5, aniso: 'prop', build: metal },
  steel_el: { tile: [0.6, 2.4], res: 1, px: [0.25], rough: 0.6, aniso: 'wall', build: steelEl },
  rust: { tile: [1.5, 1.5], res: 0.5, rough: 0.85, aniso: 'prop', build: rust },
  roll_gate: { tile: [1.2, 1.2], res: 0.5, rough: 0.55, aniso: 'wall', build: rollGate },
  corrugated: { tile: [1.2, 1.2], res: 0.5, rough: 0.6, aniso: 'wall', build: corrugated },
  paint: { tile: [1.5, 1.5], res: 0.5, rough: 0.5, aniso: 'prop', build: paint },
  pebble: { tile: [0.25, 0.25], res: 0.25, rough: 1, aniso: 'prop', build: pebble },
  tire: { tile: [0.24, 0.24], res: 0.25, rough: 1, aniso: 'prop', build: tire },
  wrinkle: { tile: [0.7, 0.7], res: 0.25, rough: 0.75, aniso: 'prop', build: wrinkle },
  wood: { tile: [1.2, 1.2], res: 0.5, rough: 1, aniso: 'wall', build: wood },
  plywood: { tile: [2.44, 1.22], res: 1, rough: 1, aniso: 'wall', build: plywood },
  cardboard: { tile: [1, 1], res: 0.5, rough: 0.95, aniso: 'prop', build: cardboard },
  fabric: { tile: [0.25, 0.25], res: 0.25, rough: 1, aniso: 'prop', build: fabric },
  leaves: { tile: [1.2, 1.2], res: 0.5, rough: 1, aniso: 'prop', build: leaves },
  smudge: { tile: [1.6, 1.6], res: 0.25, rough: 0.5, aniso: 'prop', build: smudge },
};

/**
 * Paints the canvases of one set.
 * @returns {{albedo: object|null, normal: HTMLCanvasElement|null, orm: HTMLCanvasElement|null, w: number, h: number}}
 */
export function paintSet(name, size, bank) {
  const spec = SETS[name];
  if (!spec) throw new Error(`mats: no surface set called '${name}'`);
  let seed = 17;
  for (let i = 0; i < name.length; i++) seed = (Math.imul(seed, 31) + name.charCodeAt(i)) | 0;
  const P = painter(spec, size, bank, seed);
  const out = spec.build(P);
  return { ...out, w: P.w, h: P.h };
}
