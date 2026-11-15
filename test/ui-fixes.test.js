// Interface fix pass: edge-pin placement, the HUD clocks behind the pause card, and the copy the review
// found wrong (touch controls, crouch keys, difficulty note, the "generated in your browser" line).

import assert from 'node:assert/strict';
import { test } from 'node:test';
import * as player from '../src/config/player.js';
import * as text from '../src/config/text.js';
import * as copy from '../src/ui/copy.js';
import * as L from '../src/ui/logic.js';

const box = (l, t, r, b) => ({ l, t, r, b });
const out = () => ({ x: 0, y: 0 });

test('edge pins: a free spot is kept', () => {
  const placed = new Float64Array(10);
  const o = L.separatePin(64, 345, placed, 0, [], 0, true, 80, 600, 384, out());
  assert.deepEqual(o, { x: 64, y: 345 });
});

test('edge pins: two pins on one point are spread along the edge', () => {
  const placed = new Float64Array([64, 345]);
  const o = L.separatePin(64, 345, placed, 1, [], 0, true, 80, 600, 384, out());
  assert.equal(o.x, 64);
  assert.ok(Math.abs(o.y - 345) >= L.PIN.gapY, `moved ${o.y}`);
});

test('edge pins: a pin keeps out of the kill feed', () => {
  const feed = box(16, 288, 220, 400);
  const o = L.separatePin(64, 345, new Float64Array(10), 0, [feed], 1, true, 80, 600, 384, out());
  assert.equal(o.x, 64);
  const clear = o.y + L.PIN.below < feed.t || o.y - L.PIN.above > feed.b;
  assert.ok(clear, `pin at ${o.y} is still drawn over the feed ${feed.t}…${feed.b}`);
});

test('edge pins: with the edge full, a pin moves in from it, clear of every plate', () => {
  // the badge above, the feed, the stick below: no room on the left edge at all
  const blocks = [box(16, 8, 222, 95), box(16, 104, 176, 177), box(27, 160, 129, 344)];
  const o = L.separatePin(33, 188, new Float64Array(10), 0, blocks, 3, true, 41, 238, 200, out());
  assert.ok(o.x > 33 && o.x <= 200, `x ${o.x}`); // moved in, no further than the inward limit
  for (const b of blocks) {
    const hit = o.x + L.PIN.half > b.l && o.x - L.PIN.half < b.r && o.y + L.PIN.below > b.t && o.y - L.PIN.above < b.b;
    assert.ok(!hit, `pin ${o.x},${o.y} over ${JSON.stringify(b)}`);
  }
});

test('edge pins: nowhere clear of the plates, they still do not stack', () => {
  const wall = box(0, 0, 1000, 1000);
  const placed = new Float64Array([33, 188]);
  const o = L.separatePin(33, 188, placed, 1, [wall], 1, true, 41, 300, 200, out());
  assert.ok(Math.abs(o.y - 188) >= L.PIN.gapY || Math.abs(o.x - 33) >= L.PIN.gapX, JSON.stringify(o));
});

test('edge pins along the top edge move across it, inside their range', () => {
  const placed = new Float64Array([400, 40]);
  const o = L.separatePin(400, 40, placed, 1, [], 0, false, 64, 1216, 216, out());
  assert.equal(o.y, 40);
  assert.ok(o.x >= 64 && o.x <= 1216 && Math.abs(o.x - 400) >= L.PIN.gapX);
});

test('radio and feed hold their time while the clock passes 0 (the paused HUD)', () => {
  const radio = L.createRadioQueue(58);
  radio.push('IPX VAULT', 'The truck is idling at the south end of the lot.', 2);
  radio.update(0.5);
  const line = radio.current();
  const shown = radio.shown();
  for (let i = 0; i < 300; i++) radio.update(0); // ten seconds behind the pause card
  assert.equal(radio.current(), line);
  assert.equal(radio.shown(), shown);
  const feed = L.createFeed(4, 4.2, 0.6);
  feed.push('Goon down', '', 'chopper');
  feed.update(1);
  for (let i = 0; i < 300; i++) feed.update(0);
  assert.equal(feed.lines.length, 1);
});

test('touch controls table: every glyph key names a real touch glyph, and the left trigger and sprint lock are there', () => {
  const rows = copy.controls.touch.rows;
  const glyphs = rows.flatMap(([, keys]) => keys.filter((k) => typeof k === 'object').map((k) => k.glyph));
  assert.ok(glyphs.length >= 10);
  for (const g of glyphs) assert.ok(player.touchGlyphs[g], `no touch glyph "${g}"`);
  // the old text captions, which no button carries, are gone
  const words = rows.flatMap(([, keys]) => keys.filter((k) => typeof k === 'string'));
  for (const gone of ['RLD', 'DUCK', 'HIT', 'AIM', 'SWAP', 'JUMP', 'Hold FIRE']) assert.ok(!words.includes(gone), gone);
  for (const action of ['Fire, left thumb', 'Sprint lock']) assert.ok(rows.some(([a]) => a === action), action);
});

test('crouch is C only (Ctrl+W closes the tab)', () => {
  const crouch = copy.controls.kbm.rows.find(([a]) => a === 'Crouch');
  assert.deepEqual(crouch[1], ['C']);
  assert.ok(!JSON.stringify(copy).includes('Ctrl'));
});

test('copy: the difficulty note and the generated-in-browser line say what is true', () => {
  assert.match(text.notes.difficulty, /at once/);
  assert.match(text.notes.difficulty, /health/);
  assert.match(copy.panel.noteDifficulty, /at once/);
  assert.doesNotMatch(text.title.note, /Nothing is downloaded/);
});
