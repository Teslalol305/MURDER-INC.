// Noise fields and height-field maths behind the generated textures (src/mats/noise.js), and the
// chain-link coverage pattern. Pure functions on typed arrays.

import test from 'node:test';
import assert from 'node:assert/strict';
import { blur, cellular, fbm, gradientNoise, hash2, heightToNormal, normalise, prng, resample, sampleField, whiteNoise } from '../src/mats/noise.js';
import { chainlinkPixels } from '../src/mats/surfaces.js';

const maxStep = (field, w, h, x0, x1) => {
  let worst = 0;
  for (let y = 0; y < h; y++) worst = Math.max(worst, Math.abs(field[y * w + x0] - field[y * w + x1]));
  return worst;
};

test('mats noise: generators are deterministic and stay in range', () => {
  const a = prng(7);
  const b = prng(7);
  for (let i = 0; i < 100; i++) {
    const v = a();
    assert.equal(v, b());
    assert.ok(v >= 0 && v < 1);
  }
  assert.notEqual(prng(7)(), prng(8)());
  for (let i = 0; i < 200; i++) {
    const v = hash2(i * 3 - 100, i * 7, 5);
    assert.ok(v >= 0 && v < 1);
  }
  assert.equal(hash2(3, 4, 5), hash2(3, 4, 5));
  assert.notEqual(hash2(3, 4, 5), hash2(4, 3, 5));
  assert.deepEqual(whiteNoise(8, 8, 3), whiteNoise(8, 8, 3));
});

test('mats noise: gradient noise repeats at its edges, so textures made from it tile', () => {
  const w = 64;
  const h = 48;
  const field = gradientNoise(w, h, 4, 3, 11);
  assert.equal(field.length, w * h);
  assert.deepEqual(field, gradientNoise(w, h, 4, 3, 11));
  assert.notDeepEqual(field, gradientNoise(w, h, 4, 3, 12));
  // The jump from the last column back to the first is no bigger than a jump between neighbours inside.
  const inside = Math.max(maxStep(field, w, h, 10, 11), maxStep(field, w, h, 30, 31), maxStep(field, w, h, 50, 51));
  assert.ok(maxStep(field, w, h, w - 1, 0) <= inside * 1.5 + 1e-6, 'left and right edges do not meet');
  let worstInside = 0;
  let worstWrap = 0;
  for (let x = 0; x < w; x++) {
    worstInside = Math.max(worstInside, Math.abs(field[20 * w + x] - field[21 * w + x]));
    worstWrap = Math.max(worstWrap, Math.abs(field[(h - 1) * w + x] - field[x]));
  }
  assert.ok(worstWrap <= worstInside * 1.5 + 1e-6, 'top and bottom edges do not meet');
});

test('mats noise: fbm is normalised to 0..1 and periodic; ridged noise too', () => {
  for (const ridged of [false, true]) {
    const field = fbm(64, 64, 3, 3, 4, 5, 0.5, ridged);
    let min = Infinity;
    let max = -Infinity;
    for (const v of field) {
      min = Math.min(min, v);
      max = Math.max(max, v);
    }
    assert.ok(Math.abs(min) < 1e-6 && Math.abs(max - 1) < 1e-6, `range ${min}..${max}`);
    assert.ok(maxStep(field, 64, 64, 63, 0) < 0.25, 'fbm seam');
  }
  assert.deepEqual(normalise(new Float32Array([2, 2, 2])), new Float32Array([0.5, 0.5, 0.5]));
  assert.deepEqual(normalise(new Float32Array([1, 3, 2])), new Float32Array([0, 1, 0.5]));
});

test('mats noise: cellular noise gives a distance and a per-cell id, and wraps', () => {
  const { dist, id } = cellular(48, 48, 6, 9);
  for (let i = 0; i < dist.length; i++) {
    assert.ok(dist[i] >= 0 && dist[i] < 1.5);
    assert.ok(id[i] >= 0 && id[i] < 1);
  }
  // Every cell id covers more than one pixel (cells are regions, not noise).
  const ids = new Set(Array.from(id, (v) => Math.round(v * 1e6)));
  assert.ok(ids.size <= 36 && ids.size >= 20, `${ids.size} distinct cells`);
  assert.ok(maxStep(dist, 48, 48, 47, 0) < 0.3, 'cell distance seam');
});

test('mats noise: sampling and resampling wrap around and keep the field', () => {
  const field = new Float32Array([0, 1, 2, 3]); // 2 × 2
  assert.equal(sampleField(field, 2, 0, 0), 0);
  assert.equal(sampleField(field, 2, 0.5, 0), 1);
  assert.equal(sampleField(field, 2, 1, 1), 0); // one whole tile further on
  assert.equal(sampleField(field, 2, 0.25, 0), 0.5); // halfway between two texels
  assert.equal(sampleField(field, 2, 0.75, 0), 0.5); // halfway between the last texel and the first again
  const big = resample(field, 2, 4, 4, 1);
  assert.equal(big.length, 16);
  assert.equal(big[0], 0);
  assert.equal(big[2], 1);
  const twice = resample(field, 2, 4, 4, 2);
  assert.deepEqual(Array.from(twice.slice(0, 4)), [0, 1, 0, 1]);
});

test('mats noise: blur keeps the average and smooths across the edges', () => {
  const w = 16;
  const h = 8;
  const field = new Float32Array(w * h);
  field[0] = 1; // one bright pixel in the corner
  const out = blur(field, w, h, 2);
  const sum = out.reduce((a, b) => a + b, 0);
  assert.ok(Math.abs(sum - 1) < 1e-5, `sum ${sum}`);
  assert.ok(out[w - 1] > 0 && out[(h - 1) * w] > 0, 'the blur did not wrap');
  assert.deepEqual(blur(field, w, h, 0), field);
  assert.notEqual(blur(field, w, h, 0), field); // a copy, never the input itself
});

test('mats noise: a height field becomes a +Y-up tangent-space normal map', () => {
  const w = 8;
  const h = 8;
  const flat = heightToNormal(new Float32Array(w * h).fill(0.3), w, h, 4);
  for (let i = 0; i < flat.length; i += 4) assert.deepEqual([flat[i], flat[i + 1], flat[i + 2], flat[i + 3]], [128, 128, 255, 255]);

  // Height rising to the right: the surface faces left (−x), so red drops below mid grey.
  const east = new Float32Array(w * h);
  // Height rising down the canvas, i.e. falling as v rises: the surface faces +v, so green goes up.
  const south = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      east[y * w + x] = x / w;
      south[y * w + x] = y / h;
    }
  }
  const ne = heightToNormal(east, w, h, 4, undefined, false, false);
  const ns = heightToNormal(south, w, h, 4, undefined, false, false);
  const mid = (3 * w + 3) * 4;
  assert.ok(ne[mid] < 120 && Math.abs(ne[mid + 1] - 128) <= 1 && ne[mid + 2] > 128, `east ${ne[mid]},${ne[mid + 1]},${ne[mid + 2]}`);
  assert.ok(ns[mid + 1] > 136 && Math.abs(ns[mid] - 128) <= 1, `south ${ns[mid]},${ns[mid + 1]}`);
  // A steeper slope tilts the normal further.
  const steep = heightToNormal(east, w, h, 16, undefined, false, false);
  assert.ok(steep[mid] < ne[mid]);
  // Normals are unit length.
  const nx = ne[mid] / 127.5 - 1;
  const ny = ne[mid + 1] / 127.5 - 1;
  const nz = ne[mid + 2] / 127.5 - 1;
  assert.ok(Math.abs(Math.hypot(nx, ny, nz) - 1) < 0.03);
});

test('mats: the chain-link weave is mostly air, tiles, and keeps the wire colour under clear pixels', () => {
  const { data, size } = chainlinkPixels(128);
  assert.equal(data.length, 128 * 128 * 4);
  let cover = 0;
  let darkest = 255;
  for (let i = 0; i < size * size; i++) {
    cover += data[i * 4 + 3] / 255;
    darkest = Math.min(darkest, data[i * 4]);
  }
  const share = cover / (size * size);
  assert.ok(share > 0.1 && share < 0.3, `wire covers ${(share * 100).toFixed(1)} %`);
  // Colour is wire everywhere (no black to bleed into the edges when the texture is filtered).
  assert.ok(darkest > 100, `darkest red ${darkest}`);
  // Periodic: the pattern one diamond over is the same pattern.
  const d = size / 8;
  for (const [x, y] of [[3, 5], [40, 17], [100, 90]]) {
    const a = data[(y * size + x) * 4 + 3];
    const b = data[(y * size + ((x + d) % size)) * 4 + 3];
    const c = data[(((y + d) % size) * size + x) * 4 + 3];
    assert.equal(a, b);
    assert.equal(a, c);
  }
});
