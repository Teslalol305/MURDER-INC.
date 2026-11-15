// The Vultures: the Buzzard (rotor loop, charge-up, bolt, spin-down) and the Goon (SMG, the cue before
// a burst, the rush with the pipe, wordless grunts), plus the stab when one of them makes you.

import { biquad, burst, drive, fade, formants, glide, lowpass, mix, reverb, ring, saw, seamless, shape, sweep, tone, white, TAU } from './dsp.js';

/** Four motors a few Hz apart, blade noise on top. Whole-number frequencies over 1 s: the loop closes exactly. */
function rotor(c) {
  const { sr } = c;
  const x = c.buf(1);
  const motors = [187, 194, 203, 209];
  for (let m = 0; m < motors.length; m++) {
    const ph = c.rnd() * TAU;
    for (let h = 1; h <= 7; h++) {
      const w = (TAU * motors[m] * h) / sr;
      const a = 0.25 / h ** 1.15;
      for (let i = 0; i < x.length; i++) x[i] += a * Math.sin(w * i + ph * h);
    }
  }
  // Blade wash: noise, amplitude-modulated at the blade-pass rate.
  const wash = seamless(biquad(white(x.length + Math.round(0.1 * sr), c.rnd), sr, 'bandpass', 2400, 0.6), sr, 0.1);
  for (let i = 0; i < x.length; i++) {
    const t = i / sr;
    const am = 0.55 + 0.45 * Math.sin(TAU * 97 * t) * Math.sin(TAU * 3 * t);
    x[i] = x[i] * (0.85 + 0.15 * Math.sin(TAU * 6 * t)) + wash[i] * 0.5 * am;
  }
  return x;
}

/** The Buzzard's gun spooling up: a rising whine that ticks faster and ends on a blip. Played at 0.5 s / telegraph. */
function charge(c) {
  const { sr } = c;
  const len = 0.5;
  const x = c.buf(len + 0.05);
  const f = (t) => 420 * Math.pow(5.6, Math.min(1, t / len));
  saw(x, sr, 0, len, f, 0.4);
  tone(x, sr, 0, len, (t) => f(t) * 2.01, 0.3, { attack: 0.02, release: 0.01 });
  biquad(x, sr, 'bandpass', glide(900, 3600), 1.2);
  for (let i = 0; i < x.length; i++) {
    const t = i / sr;
    const u = Math.min(1, t / len);
    const tick = 0.6 + 0.4 * Math.sin(TAU * (9 * t + 22 * t * t)); // 9 Hz speeding to about 30
    x[i] *= (0.15 + 0.85 * u * u) * tick;
  }
  ring(x, sr, len - 0.035, [[3320, 0.6, 0.012], [4980, 0.3, 0.008]], 0.5);
  return x;
}

/** A bolt leaving: an electric crack with a falling tone and a small thump. */
function boltShot(c) {
  const { sr, rnd } = c;
  const x = c.buf(0.4);
  const f0 = c.r(1900, 2500);
  saw(x, sr, 0, 0.16, (t) => 260 + f0 * Math.exp(-t / 0.028), 0.6, { pulse: 0.3 });
  shape(x, sr, 0.0005, 0.05);
  biquad(x, sr, 'lowpass', 5200, 0.8);
  burst(x, sr, 0, 0.04, rnd, 0.9, { tau: 0.006, type: 'highpass', f: 2400 });
  sweep(x, sr, 0, 0.14, 230, 80, 0.8, { tau: 0.035, fTau: 0.02 });
  drive(x, 1.8);
  const out = reverb(x, sr, { time: 0.5, damp: 0.5, mix: 0.2 }).subarray(0, x.length);
  return out;
}

/** Motors dying: pitch and level fall away over a second and a half, sputtering, sparks spitting. */
function* buzzardDeath(c) {
  const { sr, rnd } = c;
  const len = 1.6;
  const x = c.buf(len);
  const fall = (t) => 40 + 175 * Math.exp(-t / 0.55);
  for (const k of [1, 1.035, 0.96]) saw(x, sr, 0, len, (t) => fall(t) * k * (1 + 0.04 * Math.sin(TAU * 11 * t)), 0.3);
  yield;
  tone(x, sr, 0, 1.1, (t) => 300 + 1700 * Math.exp(-t / 0.3), 0.25, { attack: 0.01, tau: 0.5, release: 0.2 });
  biquad(x, sr, 'lowpass', glide(4200, 700), 0.8);
  let gate = 1;
  for (let i = 0; i < x.length; i++) {
    const t = i / sr;
    if (i % 441 === 0) gate = rnd() < 0.18 + t * 0.25 ? 0.25 : 1; // cutting out more as it goes
    x[i] *= gate * Math.exp(-t / 0.9);
  }
  yield;
  burst(x, sr, 0, 0.08, rnd, 0.9, { tau: 0.012, type: 'bandpass', f: 2600, q: 0.7 }); // the hit that killed it
  ring(x, sr, 0, [[1240, 0.5, 0.04], [2110, 0.4, 0.03], [3350, 0.3, 0.02]], 0.6);
  for (let i = 0; i < 14; i++) burst(x, sr, c.r(0.05, 1.2), 0.02, rnd, c.r(0.15, 0.45), { tau: 0.003, type: 'highpass', f: 3000 });
  return fade(x, sr, 0.001, 0.3);
}

/** A Goon's SMG, heard from across the street: lighter than the Chopper, with its own slap baked in. */
function smgShot(c) {
  const { sr, rnd } = c;
  const x = c.buf(0.55);
  burst(x, sr, 0, 0.05, rnd, 1, { tau: 0.005, type: 'highpass', f: 2100 });
  burst(x, sr, 0, 0.14, rnd, 0.9, { tau: c.r(0.02, 0.026), type: 'bandpass', f: c.r(850, 1100), q: 0.8 });
  sweep(x, sr, 0, 0.16, c.r(230, 260), 85, 0.8, { tau: 0.035, fTau: 0.018 });
  ring(x, sr, 0.018, [[2100, 0.4, 0.008], [3600, 0.3, 0.006]], 0.25);
  drive(x, 2);
  // One slap off the opposite wall and a short wash.
  burst(x, sr, c.r(0.085, 0.11), 0.2, rnd, 0.28, { tau: 0.045, type: 'bandpass', f: 700, q: 0.6 });
  const out = reverb(x, sr, { time: 0.7, damp: 0.55, mix: 0.22, size: 1.3 }).subarray(0, x.length);
  return fade(out, sr, 0, 0.15);
}

/** About to fire: the gun coming up. Sling, a hand on the bolt. Played at 0.5 s / telegraph. */
function goonReady(c) {
  const { sr, rnd } = c;
  const x = c.buf(0.5);
  burst(x, sr, 0, 0.3, rnd, 0.4, { attack: 0.08, tau: 0.1, type: 'bandpass', f: glide(1100, 2300), q: 0.8 });
  const at = 0.3;
  ring(x, sr, at, [[1750, 0.5, 0.012], [2900, 0.4, 0.008], [820, 0.3, 0.02]], 0.9);
  ring(x, sr, at + 0.075, [[2200, 0.5, 0.012], [3700, 0.4, 0.008], [1040, 0.3, 0.02]], 1);
  burst(x, sr, at + 0.075, 0.03, rnd, 0.5, { tau: 0.005, type: 'bandpass', f: 3200, q: 1 });
  return x;
}

/** A voice with no words in it: a glottal buzz and breath through three formants, behind a mask. */
function voice(c, dur, f0, f1, vowel0, vowel1, breath = 0.3) {
  const { sr, rnd } = c;
  const n = Math.round(dur * sr);
  const src = new Float32Array(n);
  const wobble = c.r(0.02, 0.05);
  saw(src, sr, 0, dur, (t) => (f0 + (f1 - f0) * (t / dur)) * (1 + wobble * Math.sin(TAU * 31 * t + 1)), 0.7, { pulse: 0.42 });
  const air = white(n, rnd);
  for (let i = 0; i < n; i++) src[i] += air[i] * breath;
  // The mouth closes over the sound: glide every formant from the first vowel to the second.
  const bands = vowel0.map(([f, q, g], i) => [glide(f, vowel1[i][0]), q, g]);
  const out = formants(src, sr, bands);
  lowpass(out, sr, 3400, 0.7);
  return out;
}

const AH = [[730, 5, 1], [1150, 7, 0.6], [2500, 8, 0.3]];
const UH = [[560, 5, 1], [950, 7, 0.5], [2350, 8, 0.25]];
const OH = [[430, 5, 1], [780, 7, 0.45], [2300, 8, 0.2]];
const EH = [[620, 5, 1], [1650, 7, 0.6], [2550, 8, 0.35]];

function gruntHit(c) {
  const { sr } = c;
  const dur = c.r(0.15, 0.2);
  const f0 = c.r(135, 165);
  const x = voice(c, dur, f0, f0 * 0.72, c.v % 2 ? AH : UH, OH, 0.4);
  for (let i = 0; i < x.length; i++) {
    const u = i / x.length;
    x[i] *= Math.min(1, u * 14) * Math.exp(-u * 3.2);
  }
  burst(x, sr, 0, 0.03, c.rnd, 0.06, { tau: 0.008, type: 'bandpass', f: 1500, q: 0.7 }); // the breath knocked out
  return x;
}

function gruntDeath(c) {
  const { sr } = c;
  const dur = c.r(0.42, 0.56);
  const f0 = c.r(125, 150);
  const x = voice(c, dur, f0, f0 * 0.5, c.v % 2 ? UH : AH, OH, 0.55);
  for (let i = 0; i < x.length; i++) {
    const u = i / x.length;
    x[i] *= Math.min(1, u * 18) * (1 - u) ** 1.3 * (0.85 + 0.15 * Math.sin(u * 60));
  }
  // The air going out at the end.
  burst(x, sr, dur * 0.5, dur * 0.5, c.rnd, 0.05, { attack: 0.05, tau: 0.12, type: 'bandpass', f: 1300, q: 0.6 });
  return x;
}

/** A Goon spots you: one sharp, rising shout with no word in it. */
function alertGoon(c) {
  const dur = 0.24;
  const f0 = c.r(185, 215);
  const x = voice(c, dur, f0, f0 * 1.28, EH, AH, 0.25);
  for (let i = 0; i < x.length; i++) {
    const u = i / x.length;
    x[i] *= Math.min(1, u * 25) * Math.min(1, (1 - u) * 6);
  }
  drive(x, 1.4);
  return reverb(x, c.sr, { time: 0.5, damp: 0.5, mix: 0.25 });
}

/** A Buzzard acquires you: two quick rising chirps. */
function alertBuzzard(c) {
  const { sr } = c;
  const x = c.buf(0.36);
  for (const [at, f] of [[0, 1500], [0.13, 2000]]) {
    saw(x, sr, at, 0.09, (t) => f * (1 + 2.2 * t), 0.35, { pulse: 0.5 });
    tone(x, sr, at, 0.09, (t) => f * 2 * (1 + 2.2 * t), 0.3, { attack: 0.003, release: 0.02 });
  }
  for (let i = 0; i < x.length; i++) {
    const t = i / sr;
    const e = t < 0.13 ? Math.min(1, (0.1 - t) / 0.02) : Math.min(1, (0.23 - t) / 0.02);
    x[i] *= Math.max(0, Math.min(1, e));
  }
  biquad(x, sr, 'lowpass', 5200, 0.8);
  return x;
}

/** The rush: a growl coming up from the chest while the pipe drags on the asphalt. Played at 0.6 s / wind-up. */
function goonRush(c) {
  const { sr, rnd } = c;
  const dur = 0.6;
  const x = c.buf(dur + 0.1);
  const growl = voice(c, dur, 88, 150, OH, AH, 0.5);
  for (let i = 0; i < growl.length; i++) {
    const u = i / growl.length;
    growl[i] *= u ** 1.4 * Math.min(1, (1 - u) * 12) * (0.75 + 0.25 * Math.sin(TAU * 27 * (i / sr))); // fry
  }
  mix(x, growl, sr, 0, 0.9);
  // The pipe: grains of scrape exciting a tube's partials.
  const k = c.r(0.95, 1.06);
  for (let at = 0.02; at < dur - 0.08; at += c.r(0.012, 0.03)) {
    const g = (at / dur) * c.r(0.05, 0.16);
    ring(x, sr, at, [[1380 * k, 0.5, 0.02], [2510 * k, 0.4, 0.014], [3890 * k, 0.3, 0.01]], g);
    burst(x, sr, at, 0.012, rnd, g * 1.5, { tau: 0.003, type: 'bandpass', f: 4200, q: 1 });
  }
  return x;
}

/** The pipe coming round. */
function pipeSwing(c) {
  const { sr } = c;
  const x = white(Math.round(0.32 * sr), c.rnd);
  biquad(x, sr, 'bandpass', (t) => 380 + 1500 * Math.exp(-(((t - 0.5) / 0.2) ** 2)), 1.6);
  for (let i = 0; i < x.length; i++) x[i] *= Math.exp(-((((i / x.length) - 0.5) / 0.19) ** 2));
  ring(x, sr, 0.17, [[1380, 0.5, 0.05], [2510, 0.3, 0.03]], 0.12);
  return x;
}

/** A body going down on the pavement. */
function bodyFall(c) {
  const { sr, rnd } = c;
  const x = c.buf(0.5);
  sweep(x, sr, 0, 0.25, 105, 45, 1, { tau: 0.06, fTau: 0.04 });
  burst(x, sr, 0, 0.12, rnd, 0.6, { tau: 0.03, type: 'lowpass', f: 800 });
  burst(x, sr, 0.03, 0.3, rnd, 0.3, { attack: 0.03, tau: 0.08, type: 'bandpass', f: 1700, q: 0.7 }); // the coat
  sweep(x, sr, 0.14, 0.2, 90, 50, 0.4, { tau: 0.04, fTau: 0.03 }); // an arm, a moment later
  return x;
}

const world = (extra) => ({ bus: 'world', jitter: 0.05, ...extra });

export const ENEMIES = {
  rotor: world({ n: 1, peak: 0.4, loop: true, sr: 22050, ref: 6, roll: 1, gen: rotor }),
  buzzard_charge: world({ n: 1, peak: 0.55, prio: 8, max: 3, gap: 0.05, ref: 8, roll: 0.9, jitter: 0.02, gen: charge }),
  bolt_shot: world({ n: 3, peak: 0.66, prio: 8, max: 4, gap: 0.03, ref: 10, roll: 0.8, gen: boltShot }),
  buzzard_death: world({ n: 1, peak: 0.7, prio: 8, max: 2, ref: 9, roll: 0.9, gen: buzzardDeath }),
  smg_shot: world({ n: 4, peak: 0.74, prio: 8, max: 5, gap: 0.035, ref: 11, roll: 0.8, jitter: 0.04, gen: smgShot }),
  goon_ready: world({ n: 1, peak: 0.42, prio: 6, max: 2, gap: 0.08, ref: 6, roll: 1, jitter: 0.03, gen: goonReady }),
  goon_rush: world({ n: 2, peak: 0.7, prio: 8, max: 2, gap: 0.1, ref: 7, roll: 0.9, jitter: 0.03, gen: goonRush }),
  pipe_swing: world({ n: 1, peak: 0.55, prio: 7, max: 2, ref: 5, roll: 1, gen: pipeSwing }),
  grunt_hit: world({ n: 4, peak: 0.5, prio: 5, max: 2, gap: 0.12, ref: 7, roll: 0.9, jitter: 0.07, sr: 22050, gen: gruntHit }),
  grunt_death: world({ n: 3, peak: 0.6, prio: 7, max: 2, gap: 0.1, ref: 8, roll: 0.9, jitter: 0.07, sr: 22050, gen: gruntDeath }),
  alert_goon: world({ n: 3, peak: 0.6, prio: 7, max: 2, gap: 0.12, ref: 10, roll: 0.8, jitter: 0.06, sr: 22050, gen: alertGoon }),
  alert_buzzard: world({ n: 1, peak: 0.5, prio: 7, max: 2, gap: 0.12, ref: 10, roll: 0.8, jitter: 0.04, gen: alertBuzzard }),
  body_fall: world({ n: 2, peak: 0.5, prio: 4, max: 2, ref: 5, roll: 1, jitter: 0.08, sr: 22050, gen: bodyFall }),
};
