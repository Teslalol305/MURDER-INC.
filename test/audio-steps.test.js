// The render queue's step size: the stepped dsp forms give the same samples as the plain calls, a
// suspended pass is not disturbed by other sounds rendering in between, the long generators keep every
// step short, and a queue slice does not start a step it is not expected to finish.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as D from '../src/audio/dsp.js';
import { SOUNDS, renderNow, renderVariant } from '../src/audio/library.js';
import { createQueue } from '../src/audio/queue.js';

const SR = 22050;
const noise = (n, seed = 7) => D.white(n, D.seeded(seed));
const same = (a, b, what) => {
  assert.equal(a.length, b.length, `${what}: length`);
  for (let i = 0; i < a.length; i++) if (!Object.is(a[i], b[i])) assert.fail(`${what}: sample ${i} ${a[i]} vs ${b[i]}`);
};

test('stepped forms give the plain calls bit for bit, and yield on long buffers', () => {
  const n = 3 * D.CHUNK + 123;
  const cases = [
    ['biquad', (x) => D.biquad(x, SR, 'lowpass', 1800, 0.8), (x) => D.biquadSteps(x, SR, 'lowpass', 1800, 0.8)],
    ['biquad sweep', (x) => D.biquad(x, SR, 'bandpass', D.glide(300, 6000), 1.2), (x) => D.biquadSteps(x, SR, 'bandpass', D.glide(300, 6000), 1.2)],
    ['drive', (x) => D.drive(x, 2.2), (x) => D.driveSteps(x, 2.2)],
    ['reverb', (x) => D.reverb(x, SR, { time: 1.2, damp: 0.5, mix: 0.3, size: 1.3, pre: 0.01 }), (x) => D.reverbSteps(x, SR, { time: 1.2, damp: 0.5, mix: 0.3, size: 1.3, pre: 0.01 })],
    ['echo', (x) => D.echo(x, SR, 0.21, 0.4, 0.4, { lp: 2800, tail: 1 }), (x) => D.echoSteps(x, SR, 0.21, 0.4, 0.4, { lp: 2800, tail: 1 })],
    ['wrap', (x) => D.wrap(x, 5000), (x) => D.wrapSteps(x, 5000)],
    ['saw', (x) => D.saw(x, SR, 0.01, 0.6, (t) => 200 + 300 * t, 0.3, { pulse: 0.4 }), (x) => D.sawSteps(x, SR, 0.01, 0.6, (t) => 200 + 300 * t, 0.3, { pulse: 0.4 })],
    ['tone', (x) => D.tone(x, SR, 0.02, 0.6, 440, 0.5, { attack: 0.1, tau: 0.3, vib: 0.02 }), (x) => D.toneSteps(x, SR, 0.02, 0.6, 440, 0.5, { attack: 0.1, tau: 0.3, vib: 0.02 })],
  ];
  for (const [what, plain, stepped] of cases) {
    const a = plain(noise(n));
    const it = stepped(noise(n));
    let steps = 0;
    let r;
    while (!(r = it.next()).done) steps++;
    same(a, r.value, what);
    assert.ok(steps >= 2, `${what}: ${steps} yields over ${n} samples`);
  }
});

test('a suspended biquad keeps its own coefficients while another filter runs in between', () => {
  const ref = D.biquad(noise(4 * D.CHUNK), SR, 'highpass', 900, 0.7);
  const x = noise(4 * D.CHUNK);
  const it = D.biquadSteps(x, SR, 'highpass', 900, 0.7);
  it.next();
  D.biquad(noise(500, 3), SR, 'lowpass', 120, 4); // rewrites the shared coefficient scratch
  while (!it.next().done);
  same(ref, x, 'interleaved biquad');
});

test('the long sounds render in short steps, the same samples as one synchronous render', () => {
  for (const name of ['stem_drums', 'stem_bell', 'sting_complete', 'chopper_tail_out', 'siren_far', 'bed_day']) {
    assert.ok(SOUNDS[name], name);
    const it = renderVariant(name, 0);
    let steps = 0;
    let r;
    while (!(r = it.next()).done) steps++;
    const ref = renderNow(name, 0);
    r.value.channels.forEach((ch, i) => same(ref.channels[i], ch, name));
    // A step is at most a few CHUNKs of work: many steps for many seconds of sound.
    const samples = r.value.channels[0].length;
    assert.ok(steps >= samples / (8 * D.CHUNK), `${name}: ${steps} steps for ${samples} samples`);
  }
});

test('queue: a slice does not start a step it cannot finish, but always does one', () => {
  let t = 0;
  const pending = [];
  const q = createQueue({ slice: 6, interval: 1, now: () => t, schedule: (fn) => pending.push(fn) });
  const done = [];
  const job = (key, cost, steps) =>
    (function* () {
      for (let i = 0; i < steps; i++) {
        t += cost;
        yield;
      }
      return key;
    })();
  q.add('slow', 0, job('slow', 4, 3), (r) => done.push(r)); // 4 ms steps in a 6 ms slice
  q.start();
  pending.shift()();
  assert.equal(t, 4, 'first slice: one step (no history yet), then the next 4 ms would overrun');
  pending.shift()();
  assert.equal(t, 8, 'one 4 ms step per slice');
  // A slow step still runs alone in a slice: the queue never stalls.
  const big = createQueue({ slice: 2, interval: 1, now: () => t, schedule: (fn) => pending.push(fn) });
  big.add('huge', 0, job('huge', 10, 1), (r) => done.push(r));
  big.run();
  big.run();
  assert.deepEqual(done.slice(-1), ['huge']);
});
