// The score: an original boom-bap beat in F minor at 92 BPM, rendered in code. Seven stems of exactly
// eight bars each (so they can loop side by side forever without drifting), the riser and impact for a
// rise to full intensity, the boombox mix the reel cases play, and four stings.
// Pure sample math (dsp.js): no WebAudio here, so node can render and measure every part.
// Every generator here yields between notes and runs its buffer-wide passes through the stepped forms
// (`yield* reverbSteps(…)`), so no single step of the render queue runs long; the samples are the same.

import { CHUNK, biquadSteps, burst, drive, driveSteps, echoSteps, fade, fm, glide, mix, pink, reverbSteps, ring, saw, sawSteps, seamless, sweep, tone, white, wrapSteps, midi, TAU } from './dsp.js';

export const MUSIC_SR = 22050;
export const BPM = 92;
export const BEAT = 60 / BPM;
export const BAR = BEAT * 4;
export const STEP = BAR / 16;
export const BARS = 8;
export const LOOP = BAR * BARS;
export const LOOP_SAMPLES = Math.round(LOOP * MUSIC_SR);
/** Loop length in samples at a stem's own rate (the bass and the boombox render lower: they have no top end). */
export const loopSamples = (sr) => Math.round(LOOP * sr);
const SWING = 0.17; // how far (in 16ths) the off-16ths lag: a lazy, head-nod swing

/** Seconds from the top of the loop to a 16th step. */
export function stepTime(bar, step) {
  return bar * BAR + step * STEP + (step % 2 === 1 ? SWING * STEP : 0) + (step % 4 === 2 ? 0.04 * STEP : 0);
}

// Fm9 · Fm9 · Dbmaj9 · Dbmaj9 · Bbm9 · Bbm9 · C7(b9) · C7(b9). Bass roots an octave under the keys.
const ROOTS = [41, 41, 37, 37, 34, 34, 36, 36];
const VOICINGS = [
  [53, 56, 60, 63, 67],
  [53, 56, 60, 63, 67],
  [49, 53, 56, 60, 63],
  [49, 53, 56, 60, 63],
  [49, 53, 56, 58, 60],
  [49, 53, 56, 58, 60],
  [52, 55, 58, 60, 61],
  [52, 55, 58, 60, 61],
];

// The bell hook: [bar, step, note, length in 16ths]. Written for this game.
const HOOK = [
  [0, 0, 84, 3], [0, 3, 80, 3], [0, 6, 79, 2], [0, 8, 77, 6],
  [1, 6, 75, 2], [1, 8, 77, 2], [1, 10, 79, 2], [1, 12, 80, 4],
  [2, 0, 80, 3], [2, 3, 77, 3], [2, 6, 75, 2], [2, 8, 73, 6],
  [3, 6, 72, 2], [3, 8, 73, 2], [3, 10, 75, 2], [3, 12, 77, 4],
  [4, 0, 85, 3], [4, 3, 82, 3], [4, 6, 80, 2], [4, 8, 77, 6],
  [5, 8, 80, 2], [5, 10, 82, 2], [5, 12, 84, 4],
  [6, 0, 85, 3], [6, 3, 84, 3], [6, 6, 82, 2], [6, 8, 79, 6],
  [7, 6, 76, 2], [7, 8, 79, 2], [7, 10, 82, 2], [7, 12, 84, 4],
];

const KICK_A = [[0, 1], [7, 0.55], [10, 0.92]];
const KICK_B = [[0, 1], [3, 0.6], [10, 0.9], [13, 0.72]];
const GHOSTS_A = [[6, 0.16], [9, 0.13], [15, 0.2]];
const GHOSTS_B = [[6, 0.16], [11, 0.14], [14, 0.26], [15, 0.32]];

// ---- instruments --------------------------------------------------------------------------------

function kick(x, c, at, v) {
  sweep(x, c.sr, at, 0.42, 128, 44, 1.1 * v, { tau: 0.16, fTau: 0.032, attack: 0.001 });
  burst(x, c.sr, at, 0.02, c.rnd, 0.35 * v, { tau: 0.003, type: 'lowpass', f: 3200 });
}

function snare(x, c, at, v) {
  burst(x, c.sr, at, 0.26, c.rnd, 0.9 * v, { tau: 0.065 + 0.02 * v, type: 'bandpass', f: 1900, q: 0.6 });
  sweep(x, c.sr, at, 0.12, 215, 175, 0.55 * v, { tau: 0.04, fTau: 0.05 });
  burst(x, c.sr, at, 0.03, c.rnd, 0.4 * v, { tau: 0.004, type: 'highpass', f: 4000 });
}

function hat(x, c, at, v, open) {
  burst(x, c.sr, at, open ? 0.4 : 0.07, c.rnd, 0.7 * v, { tau: open ? 0.13 : 0.018, type: 'highpass', f: 6800 });
  ring(x, c.sr, at, [[7310, 0.2, open ? 0.08 : 0.012], [8790, 0.15, open ? 0.06 : 0.01]], v * 0.5);
}

/** Rhodes-ish tine: FM with a quick bark, tremolo applied by the caller's stem. */
function rhodes(x, sr, at, dur, note, v) {
  const f = midi(note);
  fm(x, sr, at, dur + 0.35, f, 1, 1.5 * v + 0.4, 0.5 * v, { tau: 0.9, indexTau: 0.22, attack: 0.003, release: 0.25 });
  fm(x, sr, at, 0.25, f * 2, 7, 0.8, 0.08 * v, { tau: 0.05, indexTau: 0.03, attack: 0.001 });
}

function bell(x, sr, at, note, v, len = 1.6) {
  const f = midi(note);
  fm(x, sr, at, len, f, 3.5, 2.6, 0.5 * v, { tau: 0.55, indexTau: 0.07, attack: 0.001, release: 0.3 });
  tone(x, sr, at, len, f, 0.3 * v, { attack: 0.002, tau: 0.8, release: 0.3 });
  tone(x, sr, at, 0.6, f * 2.76, 0.06 * v, { attack: 0.001, tau: 0.12, release: 0.1 });
}

/** A string-section stab: three detuned saws per note under a closing low-pass (stepped: `yield*`). */
function* stringStab(x, sr, at, dur, notes, v) {
  const n = Math.round((dur + 0.4) * sr);
  const y = new Float32Array(n);
  for (const note of notes) {
    const f = midi(note);
    for (const d of [-0.006, 0, 0.0055]) saw(y, sr, 0, dur + 0.4, f * (1 + d), 0.16 * v, { phase: Math.abs(d) * 37 });
    yield;
  }
  yield* biquadSteps(y, sr, 'lowpass', glide(4200, 900), 0.8);
  stabEnvelope(y, sr, n, dur);
  mix(x, y, sr, at, 1);
}

function stabEnvelope(y, sr, n, dur) {
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    y[i] *= Math.min(1, t / 0.012) * Math.exp(-t / (dur * 0.55 + 0.05)) * (t > dur ? Math.exp(-(t - dur) / 0.08) : 1);
  }
}

function bassNote(x, sr, at, dur, note, v, glideTo = 0) {
  const f0 = midi(note);
  const f1 = glideTo ? midi(glideTo) : f0;
  const n = Math.round((dur + 0.04) * sr);
  const y = new Float32Array(n);
  let ph = 0;
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    const u = Math.min(1, t / dur);
    const f = f0 + (f1 - f0) * Math.max(0, (u - 0.6) / 0.4);
    ph += (TAU * f) / sr;
    const env = Math.min(1, t / 0.006) * Math.exp(-t / (dur * 1.6)) * (t > dur ? Math.max(0, 1 - (t - dur) / 0.04) : 1);
    y[i] = (Math.sin(ph) + 0.28 * Math.sin(2 * ph) + 0.1 * Math.sin(3 * ph)) * env;
  }
  drive(y, 1.4);
  mix(x, y, sr, at, v);
}

// ---- stems --------------------------------------------------------------------------------------

const TAIL = 1.4; // rendered past the loop end, then folded back onto the top so the loop is seamless

function* drumsStem(c) {
  const { sr } = c;
  const x = c.buf(LOOP + TAIL);
  for (let bar = 0; bar < BARS; bar++) {
    const b = bar % 4 === 3;
    for (const [s, v] of b ? KICK_B : KICK_A) kick(x, c, stepTime(bar, s), v);
    for (const s of [4, 12]) snare(x, c, stepTime(bar, s) + c.r(-0.003, 0.004), c.r(0.92, 1));
    for (const [s, v] of b ? GHOSTS_B : GHOSTS_A) snare(x, c, stepTime(bar, s), v * c.r(0.85, 1.15));
    if (bar === BARS - 1) for (const s of [13, 14, 15]) snare(x, c, stepTime(bar, s), 0.35 + 0.15 * (s - 13)); // the turnaround
    yield;
  }
  yield* biquadSteps(x, sr, 'lowpass', 7400, 0.6); // dusty: nothing above the old sampler's band
  yield* driveSteps(x, 1.6);
  const wet = yield* reverbSteps(x, sr, { time: 0.55, damp: 0.5, mix: 0.16, size: 0.8 });
  return yield* wrapSteps(wet, loopSamples(sr));
}

function* hatsStem(c) {
  const x = c.buf(LOOP + TAIL);
  for (let bar = 0; bar < BARS; bar++) {
    for (let s = 0; s < 16; s += 2) {
      const open = s === 14 && bar % 2 === 1;
      const v = (s % 4 === 0 ? 0.85 : 0.55) * c.r(0.85, 1.1);
      hat(x, c, stepTime(bar, s) + c.r(-0.002, 0.003), v, open);
    }
    if (bar % 4 === 1) hat(x, c, stepTime(bar, 11), 0.3, false); // a pickup now and then
    if (bar % 4 === 3) hat(x, c, stepTime(bar, 15), 0.35, false);
    yield;
  }
  return yield* wrapSteps(x, loopSamples(c.sr));
}

function* bassStem(c) {
  const { sr } = c;
  const x = c.buf(LOOP + TAIL);
  for (let bar = 0; bar < BARS; bar++) {
    const r = ROOTS[bar];
    const next = ROOTS[(bar + 1) % BARS];
    if (bar % 2 === 0) {
      bassNote(x, sr, stepTime(bar, 0), STEP * 5.5, r, 1);
      bassNote(x, sr, stepTime(bar, 7), STEP * 2, r, 0.6);
      bassNote(x, sr, stepTime(bar, 10), STEP * 5, r, 0.9);
    } else {
      bassNote(x, sr, stepTime(bar, 0), STEP * 6, r, 1);
      bassNote(x, sr, stepTime(bar, 10), STEP * 3, r, 0.85);
      // The walk into the next chord: from the fifth, or from a step above the new root, gliding down.
      const from = next === r ? r + 7 : next + 2;
      bassNote(x, sr, stepTime(bar, 14), STEP * 2, from, 0.7, next === r ? 0 : next);
    }
    yield;
  }
  yield* biquadSteps(x, sr, 'lowpass', 900, 0.7);
  return yield* wrapSteps(x, loopSamples(sr));
}

function* keysStem(c) {
  const { sr } = c;
  const x = c.buf(LOOP + TAIL + 1);
  for (let bar = 0; bar < BARS; bar++) {
    const ch = VOICINGS[bar];
    const at = (s) => stepTime(bar, s) + c.r(0, 0.008);
    if (bar % 2 === 0) {
      ch.slice(0, 4).forEach((n, i) => rhodes(x, sr, at(0) + i * 0.007, STEP * 7, n, 0.75));
      yield;
      for (const n of ch.slice(3)) rhodes(x, sr, at(7), STEP * 2, n, 0.42);
      rhodes(x, sr, at(10), STEP * 2, ch[4], 0.5);
      rhodes(x, sr, at(12), STEP * 2, ch[3], 0.46);
      rhodes(x, sr, at(14), STEP * 3, ch[2], 0.44);
    } else {
      ch.slice(1).forEach((n, i) => rhodes(x, sr, at(2) + i * 0.006, STEP * 4, n, 0.58));
      yield;
      rhodes(x, sr, at(8), STEP * 3, ch[0], 0.48);
      rhodes(x, sr, at(8), STEP * 3, ch[2], 0.44);
      rhodes(x, sr, at(12), STEP * 4, ch[4] + (bar === 7 ? 3 : 0), 0.44);
    }
    yield;
  }
  // Tremolo and a dark, close room.
  for (let from = 0; from < x.length; from += CHUNK) {
    tremolo(x, sr, from, Math.min(x.length, from + CHUNK));
    yield;
  }
  yield* biquadSteps(x, sr, 'lowpass', 3000, 0.7);
  const wet = yield* reverbSteps(x, sr, { time: 1.4, damp: 0.55, mix: 0.3, size: 1.1 });
  return yield* wrapSteps(wet, loopSamples(sr));
}

function tremolo(x, sr, from, to) {
  for (let i = from; i < to; i++) x[i] *= 1 + 0.16 * Math.sin((TAU * 4.6 * i) / sr);
}

const STABS = [[0, 0, 10], [2, 6, 3], [2, 10, 3], [4, 0, 10], [6, 0, 4], [6, 6, 3], [7, 10, 2], [7, 14, 2]];

function* stringsStem(c) {
  const { sr } = c;
  const x = c.buf(LOOP + TAIL + 1);
  for (const [bar, step, len] of STABS) {
    const notes = VOICINGS[bar].slice(1).map((n) => n + 12);
    yield* stringStab(x, sr, stepTime(bar, step), STEP * len, notes, len > 5 ? 0.9 : 0.75);
    yield;
  }
  const wet = yield* reverbSteps(x, sr, { time: 2.2, damp: 0.5, mix: 0.42, size: 1.5 });
  return yield* wrapSteps(wet, loopSamples(sr));
}

function* bellStem(c) {
  const { sr } = c;
  const x = c.buf(LOOP + TAIL + 1);
  for (const [bar, step, note, len] of HOOK) {
    bell(x, sr, stepTime(bar, step), note, len >= 4 ? 0.9 : 0.75, Math.max(0.9, len * STEP + 0.6));
    yield;
  }
  // A dub echo on the dotted eighth, then the room.
  const wet = yield* echoSteps(x, sr, BEAT * 0.75, 0.38, 0.4, { lp: 2800, tail: 2 });
  const room = yield* reverbSteps(wet, sr, { time: 1.6, damp: 0.5, mix: 0.25, size: 1.2 });
  return yield* wrapSteps(room, loopSamples(sr));
}

function* crackleStem(c) {
  const { sr, rnd } = c;
  const extra = Math.round(0.5 * sr);
  const x = new Float32Array(loopSamples(sr) + extra);
  const hiss = pink(x.length, rnd);
  yield;
  yield* biquadSteps(hiss, sr, 'lowpass', 5000, 0.6);
  yield* biquadSteps(hiss, sr, 'highpass', 700, 0.6);
  mix(x, hiss, sr, 0, 0.035);
  for (let from = 0; from < x.length; from += CHUNK) {
    yield;
    crackles(x, sr, rnd, from, Math.min(x.length, from + CHUNK));
  }
  yield* biquadSteps(x, sr, 'highpass', 1200, 0.7);
  return seamless(x, sr, extra / sr);
}

/** Vinyl ticks over [from, to): the random draws come in the same order whatever the step size. */
function crackles(x, sr, rnd, from, to) {
  for (let i = from; i < to; i++) {
    if (rnd() < 26 / sr) {
      const a = (rnd() ** 3) * (rnd() < 0.5 ? -1 : 1);
      x[i] += a;
      if (i + 1 < x.length) x[i + 1] -= a * 0.6;
    }
  }
}

/** Every stem: playback gains come from layerGains() in the conductor. */
export const STEMS = {
  drums: { gen: drumsStem, peak: 0.85, pan: 0 },
  hats: { gen: hatsStem, peak: 0.42, pan: 0.18 },
  bass: { gen: bassStem, peak: 0.8, pan: 0, sr: 11025 },
  keys: { gen: keysStem, peak: 0.5, pan: -0.22 },
  strings: { gen: stringsStem, peak: 0.6, pan: 0.25 },
  bell: { gen: bellStem, peak: 0.5, pan: 0.12 },
  crackle: { gen: crackleStem, peak: 0.3, pan: 0, sr: 11025 },
};

// ---- one-shots ----------------------------------------------------------------------------------

/** Two bars of noise and tone climbing to the downbeat it lands on (the buffer ends exactly there). */
export const RISER_SECS = BAR * 2;

function* riser(c) {
  const { sr } = c;
  const x = c.buf(RISER_SECS);
  const n = white(x.length, c.rnd);
  yield* biquadSteps(n, sr, 'bandpass', glide(300, 7500), 1.2);
  mix(x, n, sr, 0, 0.8);
  yield;
  yield* sawSteps(x, sr, 0, RISER_SECS, (t) => 87.3 * Math.pow(4, t / RISER_SECS), 0.12);
  yield* sawSteps(x, sr, 0, RISER_SECS, (t) => 130.8 * Math.pow(4, t / RISER_SECS), 0.08);
  for (let i = 0; i < x.length; i++) {
    const u = i / x.length;
    x[i] *= u ** 2.4;
    if (i % CHUNK === CHUNK - 1) yield;
  }
  yield* biquadSteps(x, sr, 'lowpass', 8000);
  return fade(x, sr, 0.05, 0.004);
}

function* impact(c) {
  const { sr } = c;
  const x = c.buf(3);
  sweep(x, sr, 0, 1.6, 85, 30, 1, { tau: 0.5, fTau: 0.18 });
  yield;
  burst(x, sr, 0, 2.6, c.rnd, 0.55, { tau: 0.6, type: 'highpass', f: 2800 }); // the crash
  yield;
  snare(x, c, 0, 1);
  yield* driveSteps(x, 1.6);
  return (yield* reverbSteps(x, sr, { time: 2, damp: 0.5, mix: 0.3, size: 1.5 })).subarray(0, x.length);
}

/** The reel cases' boombox: the beat and the hook through a small, overdriven speaker. */
export function* boombox(c) {
  const { sr } = c;
  const parts = [drumsStem, hatsStem, bassStem, bellStem];
  const gains = [0.9, 0.5, 0.7, 0.8];
  const x = new Float32Array(loopSamples(sr));
  for (let k = 0; k < parts.length; k++) {
    const y = yield* parts[k](c);
    let peak = 0;
    for (let i = 0; i < y.length; i++) peak = Math.max(peak, Math.abs(y[i]));
    yield;
    for (let i = 0; i < x.length; i++) {
      x[i] += (y[i] / (peak || 1)) * gains[k];
      if (i % CHUNK === CHUNK - 1) yield;
    }
  }
  yield* biquadSteps(x, sr, 'highpass', 260, 0.8);
  yield* biquadSteps(x, sr, 'peaking', 1400, 1, 6);
  yield* biquadSteps(x, sr, 'lowpass', 3600, 0.8);
  return yield* driveSteps(x, 2.4);
}

// Stings: each answers a moment of the run.
function* stingReel(c) {
  const { sr } = c;
  const x = c.buf(3.4);
  kick(x, c, 0, 0.9);
  yield* stringStab(x, sr, 0, 0.5, [65, 68, 72, 77], 0.8);
  for (const [t, n] of [[0, 77], [0.11, 80], [0.22, 84], [0.44, 89]]) {
    bell(x, sr, t, n, 0.85, 1.6);
    yield;
  }
  return (yield* reverbSteps(x, sr, { time: 1.8, damp: 0.5, mix: 0.3, size: 1.3 })).subarray(0, x.length);
}

function* stingAll(c) {
  const { sr } = c;
  const x = c.buf(5.4);
  const hits = [[0, [61, 65, 68, 73]], [BEAT, [63, 67, 70, 75]], [BEAT * 2, [65, 68, 72, 77]]];
  for (const [t, notes] of hits) {
    kick(x, c, t, 0.85);
    yield* stringStab(x, sr, t, t === BEAT * 2 ? 1.6 : 0.4, notes, 0.85);
  }
  for (let i = 0; i < 5; i++) {
    bell(x, sr, BEAT * 2 + i * 0.1, [77, 80, 84, 89, 92][i], 0.8, 2.2);
    yield;
  }
  sweep(x, sr, BEAT * 2, 1.6, 70, 34, 0.8, { tau: 0.5, fTau: 0.2 });
  return (yield* reverbSteps(x, sr, { time: 2.4, damp: 0.5, mix: 0.35, size: 1.5 })).subarray(0, x.length);
}

function* stingDead(c) {
  const { sr } = c;
  const x = c.buf(4.6);
  // A low minor chord whose pitch sags like a tape machine losing power.
  const notes = [29, 41, 44, 48, 52];
  for (const n of notes) {
    const f = midi(n);
    saw(x, sr, 0, 3.8, (t) => f * (1 - 0.45 * Math.min(1, (t / 3.2) ** 1.6)), n < 40 ? 0.22 : 0.1);
    yield;
  }
  yield* biquadSteps(x, sr, 'lowpass', glide(2400, 300), 0.8);
  for (let i = 0; i < x.length; i++) {
    const t = i / sr;
    x[i] *= Math.min(1, t / 0.01) * Math.exp(-t / 1.6);
  }
  yield;
  sweep(x, sr, 0, 1.8, 70, 26, 0.9, { tau: 0.6, fTau: 0.4 });
  return (yield* reverbSteps(x, sr, { time: 2.6, damp: 0.6, mix: 0.4, size: 1.6 })).subarray(0, x.length);
}

function* stingComplete(c) {
  const { sr } = c;
  const x = c.buf(7);
  // Db · Eb · F major: the minor key lifts for once.
  const chords = [[0, [49, 61, 65, 68, 72]], [BEAT * 2, [51, 63, 67, 70, 75]], [BEAT * 4, [53, 65, 69, 72, 77]]];
  for (const [t, notes] of chords) {
    const last = t === BEAT * 4;
    kick(x, c, t, 0.8);
    for (const n of notes) {
      rhodes(x, sr, t, last ? 2.6 : BEAT * 1.8, n, 0.6);
      yield;
    }
    yield* stringStab(x, sr, t, last ? 2.8 : BEAT * 1.6, notes.slice(1).map((n) => n + 12), 0.7);
  }
  for (let i = 0; i < 3; i++) {
    bell(x, sr, BEAT * 4 + 0.2 + i * 0.16, [81, 84, 89][i], 0.8, 2.6);
    yield;
  }
  return (yield* reverbSteps(x, sr, { time: 2.6, damp: 0.5, mix: 0.35, size: 1.6 })).subarray(0, x.length);
}

/** Music one-shots (rendered by the library like any sound; bus 'music'). */
export const MUSIC_SFX = {
  m_riser: { bus: 'music', n: 1, peak: 0.5, sr: MUSIC_SR, gen: riser, noFade: true },
  m_impact: { bus: 'music', n: 1, peak: 0.7, sr: MUSIC_SR, gen: impact },
  sting_reel: { bus: 'music', n: 1, peak: 0.62, sr: MUSIC_SR, gen: stingReel },
  sting_all: { bus: 'music', n: 1, peak: 0.66, sr: MUSIC_SR, gen: stingAll },
  sting_dead: { bus: 'music', n: 1, peak: 0.6, sr: MUSIC_SR, gen: stingDead },
  sting_complete: { bus: 'music', n: 1, peak: 0.66, sr: MUSIC_SR, gen: stingComplete },
  boombox: { bus: 'world', n: 1, peak: 0.5, loop: true, sr: 11025, ref: 2.2, roll: 1.25, gen: boombox },
};

// Stems are loops on the music bus, exactly eight bars long at their own rate.
for (const [name, s] of Object.entries(STEMS)) {
  MUSIC_SFX[`stem_${name}`] = { bus: 'music', n: 1, peak: s.peak, loop: true, sr: s.sr || MUSIC_SR, gen: s.gen, stem: name, pan: s.pan };
}
