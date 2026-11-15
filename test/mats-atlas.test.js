// The atlas shelf packer (src/mats/atlas.js): rectangles never overlap, stay inside their page with
// their padding, keep their alignment, never move, and fill a page before opening the next one.

import test from 'node:test';
import assert from 'node:assert/strict';
import { createPacker, rectUv } from '../src/mats/atlas.js';
import { prng } from '../src/mats/noise.js';

function overlaps(a, b, pad) {
  return a.page === b.page && a.x - pad < b.x + b.w + pad && b.x - pad < a.x + a.w + pad && a.y - pad < b.y + b.h + pad && b.y - pad < a.y + a.h + pad;
}

test('mats atlas: placed rectangles are disjoint (padding included) and inside the page', () => {
  const W = 1024;
  const pad = 4;
  const packer = createPacker(W, W, pad, 4);
  const rand = prng(7);
  const placed = [];
  for (let i = 0; i < 300; i++) {
    const w = Math.round(16 + rand() * (rand() < 0.2 ? 700 : 180));
    const h = Math.round(16 + rand() * (rand() < 0.2 ? 300 : 120));
    const r = packer.place(w, h);
    assert.ok(r, `rect ${i} (${w}×${h}) was refused`);
    assert.equal(r.w, w);
    assert.equal(r.h, h);
    assert.ok(r.x - pad >= 0 && r.y - pad >= 0 && r.x + w + pad <= W && r.y + h + pad <= W, `rect ${i} leaves the page`);
    assert.equal((r.x - pad) % 4, 0, 'padded box starts on the alignment');
    assert.equal((r.y - pad) % 4, 0, 'padded box starts on the alignment');
    placed.push({ ...r });
  }
  for (let i = 0; i < placed.length; i++) {
    for (let j = i + 1; j < placed.length; j++) assert.ok(!overlaps(placed[i], placed[j], pad), `rects ${i} and ${j} overlap`);
  }
  // Packed reasonably: the opened pages are mostly used.
  assert.ok(packer.fill() > 0.5, `fill ${packer.fill()}`);
});

test('mats atlas: a page is used up before the next one opens, and nothing too big is placed', () => {
  const packer = createPacker(512, 512, 2, 1);
  // A tall shelf first, then many short items: they must still go on page 0 while there is room.
  packer.place(100, 300);
  for (let i = 0; i < 20; i++) assert.equal(packer.place(60, 40).page, 0);
  assert.equal(packer.pageCount(), 1);
  assert.equal(packer.place(600, 10), null);
  assert.deepEqual(packer.fit(2000, 500), [507, 126]);
  assert.deepEqual(packer.fit(100, 50), [100, 50]);
});

test('mats atlas: uv rects follow three.js canvas orientation (v up)', () => {
  const uv = rectUv({ x: 0, y: 0, w: 256, h: 128 }, 1024, 512);
  assert.deepEqual(uv, [0, 0.75, 0.25, 1]);
  const [u0, v0, u1, v1] = rectUv({ x: 512, y: 256, w: 512, h: 256 }, 1024, 512);
  assert.deepEqual([u0, v0, u1, v1], [0.5, 0, 1, 0.5]);
});
