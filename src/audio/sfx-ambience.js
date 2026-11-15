// The block around you: the day and night beds, wind in the El, neon and steam, the far one-shots of a
// Queens afternoon (bus, kids and a ball, pigeons, a jackhammer, an ice-cream chime) and of the night
// (siren, dog, horn), and the El train. Everything here renders at 22.05 kHz; the beds are stereo.

import { CHUNK, biquad, biquadSteps, brown, burst, drive, driveSteps, fade, formants, glide, mix, pink, reverbSteps, ring, saw, sawSteps, seamless, shape, sweep, tone, toneSteps, white, wrap, midi, TAU } from './dsp.js';

const AMB_SR = 22050;

/** One car going by, far off: a band of tyre noise whose pitch and level swell and fall (a soft Doppler). */
function carPass(dst, c, at, dur, amp, f) {
  const n = Math.round(dur * c.sr);
  const x = pink(n, c.rnd);
  biquad(x, c.sr, 'bandpass', (u) => f * (1.25 - 0.5 * u), 0.9);
  for (let i = 0; i < n; i++) {
    const u = i / n;
    x[i] *= Math.exp(-(((u - 0.5) / 0.22) ** 2));
  }
  mix(dst, x, c.sr, at, amp);
}

/** A stereo street bed: low city wash under a scatter of passing cars, each side its own traffic. */
function* bed(c, { len, cars, carAmp, wash, hum, washF }) {
  const { sr } = c;
  const extra = 1;
  const total = len + extra;
  const low = brown(Math.round(total * sr), c.rnd);
  yield;
  yield* biquadSteps(low, sr, 'lowpass', washF, 0.6);
  const out = [];
  for (let ch = 0; ch < 2; ch++) {
    const x = c.buf(total);
    mix(x, low, sr, 0, wash);
    const air = pink(x.length, c.rnd);
    yield;
    yield* biquadSteps(air, sr, 'lowpass', 2400, 0.5);
    yield* biquadSteps(air, sr, 'highpass', 300, 0.5);
    mix(x, air, sr, 0, wash * 0.16);
    for (let k = 0; k < cars; k++) {
      const dur = c.r(2.2, 4.6);
      carPass(x, c, c.r(-1, total - 1), dur, carAmp * c.r(0.4, 1), c.r(420, 900));
      yield;
    }
    if (hum) {
      for (let from = 0; from < x.length; from += CHUNK) {
        mainsHum(x, sr, hum, from, Math.min(x.length, from + CHUNK));
        yield;
      }
    }
    out.push(seamless(x, sr, extra));
    yield;
  }
  return out;
}

function mainsHum(x, sr, hum, from, to) {
  for (let i = from; i < to; i++) x[i] += hum * (Math.sin((TAU * 60 * i) / sr) * 0.6 + Math.sin((TAU * 120 * i) / sr) * 0.4);
}

/** Wind worrying the El's steel: a breathy band with two girder whistles that come and go (loop). */
function* windEl(c) {
  const { sr } = c;
  const len = 10;
  const x = pink(Math.round((len + 1) * sr), c.rnd);
  yield* biquadSteps(x, sr, 'bandpass', 520, 0.5);
  const w1 = white(x.length, c.rnd);
  yield* biquadSteps(w1, sr, 'bandpass', 610, 40);
  const w2 = white(x.length, c.rnd);
  yield* biquadSteps(w2, sr, 'bandpass', 935, 50);
  for (let from = 0; from < x.length; from += CHUNK) {
    gusts(x, w1, w2, sr, from, Math.min(x.length, from + CHUNK));
    yield;
  }
  return seamless(x, sr, 1);
}

function gusts(x, w1, w2, sr, from, to) {
  for (let i = from; i < to; i++) {
    const t = i / sr;
    const gust = 0.55 + 0.45 * Math.sin(TAU * 0.11 * t + 1) * Math.sin(TAU * 0.047 * t);
    x[i] = x[i] * gust + w1[i] * 3 * Math.max(0, gust - 0.5) + w2[i] * 2.4 * Math.max(0, Math.sin(TAU * 0.083 * t));
  }
}

/** A neon tube's transformer: 120 Hz and its odd harmonics, with the gas crackling now and then (1 s loop). */
function* neonBuzz(c) {
  const { sr } = c;
  const x = c.buf(1);
  for (let from = 0; from < x.length; from += CHUNK) {
    tubeHum(x, sr, from, Math.min(x.length, from + CHUNK));
    yield;
  }
  for (let k = 0; k < 7; k++) burst(x, sr, c.r(0, 0.95), 0.012, c.rnd, c.r(0.2, 0.6), { tau: 0.002, type: 'highpass', f: 3000 });
  return x;
}

function tubeHum(x, sr, from, to) {
  for (let i = from; i < to; i++) {
    const t = i / sr;
    let v = 0;
    for (let h = 1; h <= 9; h += 2) v += Math.sin(TAU * 120 * h * t) / h ** 0.8;
    x[i] = Math.tanh(v * 1.5) * 0.5;
  }
}

/** Steam out of a manhole: a soft, unsteady roar (loop). */
function* steam(c) {
  const { sr } = c;
  const x = white(Math.round(3.5 * sr), c.rnd);
  yield* biquadSteps(x, sr, 'highpass', 900, 0.6);
  yield* biquadSteps(x, sr, 'lowpass', 6500, 0.6);
  for (let i = 0; i < x.length; i++) {
    const t = i / sr;
    x[i] *= 0.75 + 0.25 * Math.sin(TAU * 1.3 * t) * Math.sin(TAU * 0.4 * t + 2);
  }
  return seamless(x, sr, 0.5);
}

/** A far siren: the wail sweeping up and down, through blocks of buildings. */
function* siren(c) {
  const { sr } = c;
  const len = 7.5;
  const x = c.buf(len);
  const yelp = c.v === 1;
  const f = (t) => {
    const p = yelp ? (t * 3.1) % 1 : 0.5 - 0.5 * Math.cos((TAU * t) / 2.4);
    return (yelp ? 700 + 650 * p : 640 + 720 * p) * (1 - 0.03 * (t / len)); // drifting off as it goes
  };
  yield* sawSteps(x, sr, 0, len, f, 0.3, { pulse: 0.5 });
  yield* toneSteps(x, sr, 0, len, f, 0.5, { attack: 0.3, release: 0.3 });
  yield* biquadSteps(x, sr, 'lowpass', 1900, 0.7);
  for (let i = 0; i < x.length; i++) {
    const u = i / x.length;
    x[i] *= Math.sin(Math.PI * u) ** 1.2;
    if (i % CHUNK === CHUNK - 1) yield;
  }
  return (yield* reverbSteps(x, sr, { time: 2.2, damp: 0.6, mix: 0.6, size: 1.8 })).subarray(0, x.length);
}

/** A voice without words (shared with kids): a pulse through glided formants. */
function vocal(c, dur, f0, f1, v0, v1, breath) {
  const { sr } = c;
  const n = Math.round(dur * sr);
  const src = new Float32Array(n);
  saw(src, sr, 0, dur, (t) => f0 + (f1 - f0) * (t / dur), 0.7, { pulse: 0.4 });
  const air = white(n, c.rnd);
  for (let i = 0; i < n; i++) src[i] += air[i] * breath;
  return formants(src, sr, v0.map(([f, q, g], i) => [glide(f, v1[i][0]), q, g]));
}

const WO = [[480, 4, 1], [900, 6, 0.5], [2400, 6, 0.2]];
const OF = [[360, 4, 1], [700, 6, 0.4], [2200, 6, 0.15]];
const EE = [[380, 5, 1], [2300, 7, 0.5], [2950, 7, 0.3]];
const AH = [[800, 5, 1], [1250, 7, 0.6], [2600, 7, 0.3]];
const OH = [[500, 5, 1], [850, 7, 0.5], [2500, 7, 0.2]];

/** A dog a few blocks over: two to four barks. */
function* dog(c) {
  const { sr } = c;
  const x = c.buf(3);
  const barks = 2 + Math.floor(c.rnd() * 3);
  let at = 0.05;
  const f = c.r(260, 380);
  for (let k = 0; k < barks; k++) {
    const dur = c.r(0.12, 0.18);
    const b = vocal(c, dur, f * 1.25, f * 0.8, WO, OF, 0.6);
    for (let i = 0; i < b.length; i++) {
      const u = i / b.length;
      b[i] *= Math.min(1, u * 20) * (1 - u) ** 1.5;
    }
    mix(x, b, sr, at, 1);
    at += dur + c.r(0.18, 0.42);
    yield;
  }
  yield* biquadSteps(x, sr, 'lowpass', 2200, 0.7);
  return (yield* reverbSteps(x, sr, { time: 1.8, damp: 0.6, mix: 0.7, size: 1.7 })).subarray(0, x.length);
}

/** Somebody leaning on a horn two streets away. */
function* horn(c) {
  const { sr } = c;
  const x = c.buf(1.6);
  const long = c.v % 2 === 0;
  const blips = long ? [[0, 0.55]] : [[0, 0.14], [0.22, 0.16]];
  for (const [at, dur] of blips) {
    saw(x, sr, at, dur, 405 * c.r(0.97, 1.03), 0.4, { pulse: 0.5 });
    saw(x, sr, at, dur, 507 * c.r(0.97, 1.03), 0.35, { pulse: 0.45 });
  }
  yield* biquadSteps(x, sr, 'bandpass', 900, 0.7);
  yield* biquadSteps(x, sr, 'lowpass', 1800);
  fade(x, sr, 0.003, 0.02);
  return (yield* reverbSteps(x, sr, { time: 1.4, damp: 0.6, mix: 0.6, size: 1.6 })).subarray(0, x.length);
}

/** A city bus leaving its stop: the brakes letting go, then the diesel winding up and away. */
function* busPull(c) {
  const { sr, rnd } = c;
  const len = 6.5;
  const x = c.buf(len);
  burst(x, sr, 0, 0.9, rnd, 0.5, { attack: 0.01, tau: 0.25, type: 'highpass', f: 2600 }); // air brake
  yield;
  // Engine: firing pulses whose rate climbs with the revs, through a low body.
  const rate = (t) => 9 + 13 * Math.min(1, t / 3.5) - 5 * Math.max(0, (t - 3.6) / 1.2) * (t < 4.8 ? 1 : 0) + (t > 4.8 ? 6 * Math.min(1, (t - 4.8) / 1.5) : 0);
  let ph = 0;
  const eng = new Float32Array(x.length);
  const grit = white(x.length, rnd);
  for (let i = Math.round(0.6 * sr); i < x.length; i++) {
    const t = i / sr;
    ph += rate(t) / sr;
    const p = ph % 1;
    eng[i] = Math.exp(-p * 7) * (0.7 + 0.3 * grit[i]);
    if (i % CHUNK === CHUNK - 1) yield;
  }
  yield* biquadSteps(eng, sr, 'lowpass', 340, 0.9);
  yield;
  for (let i = 0; i < eng.length; i++) {
    const t = i / sr;
    eng[i] *= Math.min(1, (t - 0.6) * 2) * Math.max(0, 1 - Math.max(0, t - 3.5) / 3.2);
    if (i % CHUNK === CHUNK - 1) yield;
  }
  mix(x, eng, sr, 0, 2.2);
  yield;
  tone(x, sr, 0.8, 5, (t) => 420 + 260 * Math.min(1, t / 3), 0.04, { attack: 0.5, release: 1.5 }); // gear whine
  yield* biquadSteps(x, sr, 'lowpass', 2600);
  return (yield* reverbSteps(x, sr, { time: 1.6, damp: 0.6, mix: 0.4, size: 1.7 })).subarray(0, x.length);
}

/** Kids on a court somewhere: a call, an answer, a rubber ball bouncing. No words in it. */
function* kids(c) {
  const { sr } = c;
  const x = c.buf(4.5);
  const calls = [[0.1, EE, AH], [0.62, AH, OH], [1.9, OH, EE]];
  for (const [at, v0, v1] of calls) {
    if (c.rnd() < 0.25) continue;
    const dur = c.r(0.25, 0.45);
    const f0 = c.r(340, 470);
    const v = vocal(c, dur, f0, f0 * c.r(0.85, 1.3), v0, v1, 0.25);
    for (let i = 0; i < v.length; i++) {
      const u = i / v.length;
      v[i] *= Math.min(1, u * 12) * Math.min(1, (1 - u) * 5);
    }
    mix(x, v, sr, at * c.r(0.9, 1.1), 0.8);
    yield;
  }
  yield;
  // The ball: a hollow rubber "pank" and its bounces closing up.
  let at = c.r(1, 1.4);
  let gap = c.r(0.5, 0.65);
  let amp = 0.9;
  for (let k = 0; k < 6 && at < 4.2; k++) {
    sweep(x, sr, at, 0.08, 220, 120, amp * 0.6, { tau: 0.015, fTau: 0.01 });
    ring(x, sr, at, [[c.r(610, 660), 0.5, 0.03], [1190, 0.25, 0.015]], amp * 0.6);
    at += gap;
    gap *= 0.78;
    amp *= 0.8;
  }
  yield* biquadSteps(x, sr, 'lowpass', 3200);
  return (yield* reverbSteps(x, sr, { time: 1.5, damp: 0.5, mix: 0.6, size: 1.5 })).subarray(0, x.length);
}

/** Pigeons on a ledge: a few coos and a clatter of wings taking off. */
function* pigeons(c) {
  const { sr, rnd } = c;
  const x = c.buf(3.2);
  for (let k = 0; k < 3; k++) {
    const at = 0.1 + k * c.r(0.4, 0.55);
    const f = c.r(290, 340);
    tone(x, sr, at, 0.34, (t) => f * (1 + 0.25 * Math.sin(Math.PI * Math.min(1, t / 0.3))), 0.4, { attack: 0.06, release: 0.12, vib: 0.02, vibRate: 28 });
  }
  yield;
  if (c.v !== 2) {
    const at = c.r(1.4, 1.9);
    const n = Math.round(1.1 * sr);
    const w = white(n, rnd);
    yield* biquadSteps(w, sr, 'bandpass', 1600, 0.7);
    const flap = c.r(11, 15);
    for (let i = 0; i < n; i++) {
      const t = i / sr;
      w[i] *= (0.5 + 0.5 * Math.sin(TAU * flap * t)) ** 3 * Math.exp(-t * 2.2);
    }
    mix(x, w, sr, at, 0.9);
    yield;
  }
  yield* biquadSteps(x, sr, 'lowpass', 4200);
  return (yield* reverbSteps(x, sr, { time: 0.8, damp: 0.5, mix: 0.35 })).subarray(0, x.length);
}

/** A jackhammer a block away: two runs of hits with a pause for breath. */
function* jackhammer(c) {
  const { sr, rnd } = c;
  const x = c.buf(5);
  const runs = [[0.1, c.r(1.2, 1.8)], [c.r(2.3, 2.7), c.r(1.2, 2)]];
  for (const [start, dur] of runs) {
    const hz = c.r(18, 23);
    for (let t = start; t < Math.min(4.8, start + dur); t += 1 / hz) {
      burst(x, sr, t, 0.045, rnd, c.r(0.5, 0.8), { tau: 0.008, type: 'bandpass', f: c.r(1400, 2200), q: 0.9 });
      sweep(x, sr, t, 0.04, 160, 90, 0.4, { tau: 0.01, fTau: 0.008 });
    }
    yield;
  }
  yield* biquadSteps(x, sr, 'lowpass', 3000);
  return (yield* reverbSteps(x, sr, { time: 1.5, damp: 0.6, mix: 0.5, size: 1.6 })).subarray(0, x.length);
}

// An original eight-bar chime for the ice-cream-style truck (C major): not any real truck's jingle.
const CHIME = [
  [0, 79], [0.5, 84], [1, 83], [1.5, 79], [2, 81], [2.75, 76], [3, 77], [3.5, 74],
  [4, 76], [4.5, 79], [5, 84], [5.5, 86], [6, 83], [6.75, 79], [7, 84],
];

/** The chime off a truck's tinny speaker: music-box tines with a little warble. */
function* chime(c) {
  const { sr } = c;
  const beat = 0.36;
  const x = c.buf(beat * 9 + 2);
  for (const [b, note] of CHIME) {
    const f = midi(note);
    ring(x, sr, 0.05 + b * beat, [[f, 0.6, 0.35], [f * 2, 0.25, 0.18], [f * 3.01, 0.12, 0.1], [f * 4.2, 0.06, 0.05]], 0.5);
    yield;
  }
  // Old speaker: wow (slow pitch wobble, faked by a tiny moving delay) and a narrow band.
  const out = new Float32Array(x.length);
  for (let i = 0; i < x.length; i++) {
    const d = 40 + 30 * Math.sin((TAU * 0.7 * i) / sr);
    const j = i - d;
    const j0 = Math.floor(j);
    out[i] = j0 >= 0 ? x[j0] + (x[j0 + 1] - x[j0]) * (j - j0) : 0;
    if (i % CHUNK === CHUNK - 1) yield;
  }
  yield* biquadSteps(out, sr, 'bandpass', 1500, 0.6);
  yield* driveSteps(out, 1.6);
  return (yield* reverbSteps(out, sr, { time: 1.6, damp: 0.5, mix: 0.55, size: 1.6 })).subarray(0, out.length);
}

/** The El's roar: steel and concrete under load, a body you feel more than hear (loop). */
function* trainRumble(c) {
  const { sr } = c;
  const x = brown(Math.round(4.5 * sr), c.rnd);
  yield* biquadSteps(x, sr, 'lowpass', 220, 0.7);
  const hi = pink(x.length, c.rnd);
  yield* biquadSteps(hi, sr, 'bandpass', 1100, 0.6);
  const mid = white(x.length, c.rnd);
  yield* biquadSteps(mid, sr, 'bandpass', 380, 4);
  for (let i = 0; i < x.length; i++) {
    const t = i / sr;
    x[i] = x[i] * 1.6 + hi[i] * 0.35 * (0.8 + 0.2 * Math.sin(TAU * 2.3 * t)) + mid[i] * 0.6;
  }
  return seamless(x, sr, 0.5);
}

/** Wheels on the rail joints: two trucks per car, two axles per truck, at 16.5 m/s over a 16.3 m car (loop). */
function trainClack(c) {
  const { sr, rnd } = c;
  const len = 16.3 / 16.5;
  const x = c.buf(len + 0.2);
  const axle = 2.4 / 16.5;
  for (const at of [0.02, 0.02 + axle, 0.02 + 10.4 / 16.5, 0.02 + 10.4 / 16.5 + axle]) {
    sweep(x, sr, at, 0.12, 140, 60, 0.9, { tau: 0.03, fTau: 0.02 });
    ring(x, sr, at, [[c.r(480, 540), 0.5, 0.04], [c.r(1230, 1350), 0.3, 0.025], [2380, 0.15, 0.012]], 0.5);
    burst(x, sr, at, 0.04, rnd, 0.5, { tau: 0.008, type: 'bandpass', f: 1800, q: 0.8 });
  }
  return wrap(x, Math.round(len * sr));
}

/** The squeal of flanges in the curve past the station. */
function* trainSqueal(c) {
  const { sr } = c;
  const len = 3.2;
  const x = white(Math.round(len * sr), c.rnd);
  const f0 = c.r(2700, 3300);
  yield* biquadSteps(x, sr, 'bandpass', (u) => f0 * (1 + 0.04 * Math.sin(u * 23)), 60);
  tone(x, sr, 0, len, (t) => f0 * (1 + 0.015 * Math.sin(TAU * 5.5 * t)), 0.05, { attack: 0.4, release: 0.8 });
  for (let i = 0; i < x.length; i++) {
    const u = i / x.length;
    x[i] *= Math.sin(Math.PI * u) ** 2 * (0.6 + 0.4 * Math.sin(TAU * 1.7 * u * len));
  }
  return x;
}

const loopDef = (gen, peak, extra) => ({ bus: 'amb', n: 1, peak, loop: true, sr: AMB_SR, gen, ...extra });
const far = (gen, n, peak, extra) => ({ bus: 'amb', n, peak, sr: AMB_SR, prio: 1, max: 2, jitter: 0.04, ref: 30, roll: 1, gen, ...extra });

export const AMBIENCE = {
  bed_day: loopDef((c) => bed(c, { len: 12, cars: 10, carAmp: 0.9, wash: 1, hum: 0.006, washF: 520 }), 0.5, { stereo: true }),
  bed_night: loopDef((c) => bed(c, { len: 12, cars: 4, carAmp: 0.7, wash: 0.65, hum: 0.012, washF: 380 }), 0.36, { stereo: true }),
  wind_el: loopDef(windEl, 0.32),
  neon_buzz: loopDef(neonBuzz, 0.18, { bus: 'world', ref: 1.4, roll: 1.6 }),
  steam: loopDef(steam, 0.3, { bus: 'world', ref: 2.5, roll: 1.3 }),
  train_rumble: loopDef(trainRumble, 0.6, { bus: 'world', ref: 14, roll: 0.7 }),
  train_clack: loopDef(trainClack, 0.62, { bus: 'world', ref: 12, roll: 0.75 }),
  train_squeal: far(trainSqueal, 1, 0.22, { bus: 'world', prio: 5, ref: 14, roll: 0.7 }),
  siren_far: far(siren, 2, 0.4),
  dog_far: far(dog, 2, 0.42),
  horn_far: far(horn, 3, 0.36),
  bus_pull: far(busPull, 1, 0.5),
  kids_far: far(kids, 2, 0.36),
  pigeons: far(pigeons, 2, 0.32, { ref: 10 }),
  jackhammer: far(jackhammer, 1, 0.34),
  chime_far: far(chime, 1, 0.34),
};
