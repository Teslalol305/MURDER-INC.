// Every sound renders, is finite, sane in level, deterministic, and the whole library fits the budget.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SOUNDS, renderNow, renderOrder, variantsOf } from '../src/audio/library.js';
import { measure } from '../src/audio/dsp.js';
import { loopSamples } from '../src/audio/music.js';

const BUSES = new Set(['world', 'near', 'gun', 'tail', 'amb', 'dry', 'music']);

test('every definition is well formed', () => {
  for (const [name, d] of Object.entries(SOUNDS)) {
    assert.ok(BUSES.has(d.bus), `${name}: bus ${d.bus}`);
    assert.equal(typeof d.gen, 'function', `${name}: gen`);
    assert.ok(d.peak > 0 && d.peak <= 1, `${name}: peak ${d.peak}`);
  }
});

test('render order puts the guns first and covers every sound once', () => {
  const order = renderOrder();
  assert.deepEqual(order.slice(0, 2).sort(), ['chopper_shot', 'nine_shot']);
  assert.equal(new Set(order).size, Object.keys(SOUNDS).length);
});

test('every variant renders finite, at its peak, never silent; the library stays under 40 MB', () => {
  let bytes = 0;
  for (const name of Object.keys(SOUNDS)) {
    const d = SOUNDS[name];
    for (let v = 0; v < variantsOf(name); v++) {
      const r = renderNow(name, v);
      assert.ok(r.channels.length >= 1 && r.channels.length <= 2, name);
      for (const ch of r.channels) {
        const m = measure(ch);
        assert.ok(Number.isFinite(m.rms) && Number.isFinite(m.peak), `${name}#${v} not finite`);
        assert.ok(m.peak <= d.peak + 1e-4, `${name}#${v} peak ${m.peak} over ${d.peak}`);
        assert.ok(m.rms > 1e-4, `${name}#${v} silent`);
        bytes += ch.length * 4;
      }
    }
  }
  assert.ok(bytes < 40e6, `library is ${(bytes / 1e6).toFixed(1)} MB`);
});

test('renders are deterministic and variants differ', () => {
  const a = renderNow('chopper_shot', 1).channels[0];
  const b = renderNow('chopper_shot', 1).channels[0];
  const c = renderNow('chopper_shot', 2).channels[0];
  assert.deepEqual(a, b);
  assert.notDeepEqual(a, c);
});

test('music stems and the boombox are exactly eight bars at their own rate', () => {
  for (const [name, d] of Object.entries(SOUNDS)) {
    if (!d.stem && name !== 'boombox') continue;
    const r = renderNow(name, 0);
    assert.equal(r.channels[0].length, loopSamples(r.sr), name);
  }
});

test('loops close on themselves: no step at the seam', () => {
  for (const [name, d] of Object.entries(SOUNDS)) {
    if (!d.loop) continue;
    const ch = renderNow(name, 0).channels[0];
    const m = measure(ch);
    // The jump across the seam is no larger than the signal's own sample-to-sample movement.
    let maxStep = 0;
    for (let i = 1; i < ch.length; i++) maxStep = Math.max(maxStep, Math.abs(ch[i] - ch[i - 1]));
    const seam = Math.abs(ch[0] - ch[ch.length - 1]);
    assert.ok(seam <= maxStep * 1.05 + 1e-3, `${name}: seam ${seam.toFixed(4)} vs max step ${maxStep.toFixed(4)} (peak ${m.peak.toFixed(2)})`);
  }
});
