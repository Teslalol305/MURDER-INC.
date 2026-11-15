// The player's guns and hands: shots, tails, dry fire, reload foley, holster / draw, melee, brass.
// Each entry: {bus, sr, n (variants), peak (normalisation target), gen(c) → Float32Array, + playback
// defaults read by the mixer: vol, jitter, prio, max, gap}. `c` = {sr, v, rnd, r(a, b), buf(secs)}.

import { biquad, burst, drive, echo, glide, mix, reverb, ring, sweep, white, shape, fade } from './dsp.js';

/** A struck steel part: a few inharmonic partials plus a tick of noise. */
function clack(x, c, at, f, amp, tau = 0.012) {
  const k = c.r(0.94, 1.06);
  ring(x, c.sr, at, [
    [f * k, 0.5, tau],
    [f * 1.78 * k, 0.4, tau * 0.7],
    [f * 2.65 * k, 0.3, tau * 0.5],
    [f * 0.47 * k, 0.3, tau * 1.6],
  ], amp);
  burst(x, c.sr, at, 0.03, c.rnd, amp * 0.6, { tau: 0.005, type: 'bandpass', f: f * 2, q: 1.1 });
}

/** Cloth and sling: a soft band of noise that swells and dies. */
function rustle(x, c, at, dur, amp, f = 1800) {
  const n = white(Math.round(dur * c.sr), c.rnd);
  biquad(n, c.sr, 'bandpass', glide(f * c.r(0.7, 0.9), f * c.r(1.1, 1.4)), 0.8);
  for (let i = 0; i < n.length; i++) {
    const u = i / n.length;
    n[i] *= Math.sin(Math.PI * u) ** 1.5 * (0.6 + 0.4 * Math.sin(u * 40 + c.v));
  }
  mix(x, n, c.sr, at, amp);
}

function chopperShot(c) {
  const { sr, rnd } = c;
  const x = c.buf(0.36);
  // The crack: the muzzle blast's first milliseconds, bright and very short.
  burst(x, sr, 0, 0.07, rnd, 1.1, { tau: 0.007, type: 'highpass', f: 1700 });
  // The bark: the mid band that makes it sound like a rifle and not a cap gun.
  burst(x, sr, 0, 0.2, rnd, 0.95, { tau: c.r(0.03, 0.038), type: 'bandpass', f: c.r(560, 760), q: 0.7 });
  // The body: a chest thump under it.
  sweep(x, sr, 0, 0.28, c.r(165, 185), 52, 1.05, { tau: 0.06, fTau: 0.028 });
  burst(x, sr, 0.002, 0.32, rnd, 0.55, { tau: 0.075, type: 'lowpass', f: 360 });
  // The action: bolt carrier back, then home.
  clack(x, c, 0.027, 1750, 0.3);
  clack(x, c, 0.066, 2300, 0.2, 0.009);
  drive(x, 2.4);
  return x;
}

function nineShot(c) {
  const { sr, rnd } = c;
  const x = c.buf(0.26);
  burst(x, sr, 0, 0.05, rnd, 1.2, { tau: 0.0045, type: 'highpass', f: 2600 });
  burst(x, sr, 0, 0.14, rnd, 0.9, { tau: c.r(0.026, 0.032), type: 'bandpass', f: c.r(1050, 1400), q: 0.8 });
  sweep(x, sr, 0, 0.18, c.r(280, 320), 100, 1.0, { tau: 0.045, fTau: 0.018 });
  burst(x, sr, 0.001, 0.2, rnd, 0.3, { tau: 0.04, type: 'lowpass', f: 520 });
  // Slide back and forward: higher and tighter than the carbine's bolt.
  clack(x, c, 0.02, 2900, 0.3, 0.007);
  clack(x, c, 0.05, 3500, 0.22, 0.006);
  drive(x, 2.6);
  return x;
}

/** The shot coming back off the block: slap echoes from the facades and the El, darkening as they go. */
function streetTail(c, bright, len) {
  const { sr, rnd } = c;
  const x = c.buf(len);
  const wash = white(x.length, rnd);
  shape(wash, sr, 0.03, len / 4.6);
  biquad(wash, sr, 'lowpass', glide(bright, 420), 0.6);
  biquad(wash, sr, 'highpass', 110, 0.7);
  mix(x, wash, sr, 0, 0.55);
  const slaps = [0.075, 0.16, 0.25, 0.39, 0.58, 0.83];
  for (let i = 0; i < slaps.length; i++) {
    const at = slaps[i] * c.r(0.9, 1.12);
    if (at > len - 0.3) break;
    const g = 0.9 * Math.pow(0.66, i);
    burst(x, sr, at, 0.22, rnd, g, { tau: 0.05 + i * 0.012, type: 'bandpass', f: (bright * 0.22) / (1 + i * 0.35), q: 0.6 });
    sweep(x, sr, at, 0.2, 120, 60, g * 0.5, { tau: 0.06, fTau: 0.04 });
  }
  const out = reverb(x, sr, { time: 0.9, damp: 0.55, mix: 0.35, size: 1.4 }).subarray(0, x.length);
  return fade(out, sr, 0.012, 0.25);
}

/** The same shot inside the garage: dense, short, with the room's steel ringing. */
function shopTail(c, bright, len) {
  const { sr, rnd } = c;
  const x = c.buf(len);
  const wash = white(x.length, rnd);
  shape(wash, sr, 0.008, len / 5.5);
  biquad(wash, sr, 'lowpass', glide(bright, 1300), 0.7);
  biquad(wash, sr, 'highpass', 180, 0.7);
  mix(x, wash, sr, 0, 0.7);
  ring(x, sr, 0.01, [[236 * c.r(0.97, 1.03), 0.5, 0.16], [412, 0.35, 0.12], [655, 0.25, 0.09], [1180, 0.12, 0.05]], 0.5);
  // Flutter between the parallel walls.
  const flutter = echo(x, sr, 0.0093, 0.55, 0.5, { lp: 5000, tail: 0.05 }).subarray(0, x.length);
  return fade(flutter, sr, 0.006, 0.15);
}

function dryFire(c) {
  const x = c.buf(0.12);
  clack(x, c, 0.002, 2700, 0.9, 0.006);
  clack(x, c, 0.03 + c.r(0, 0.006), 1900, 0.4, 0.008);
  return x;
}

function magOut(c, pistol) {
  const x = c.buf(0.3);
  const f = pistol ? 2500 : 1500;
  clack(x, c, 0.004, f * 1.3, 0.45, 0.006); // the release
  // The magazine sliding out: a short scrape, then it clears the well.
  burst(x, c.sr, 0.03, 0.12, c.rnd, 0.35, { attack: 0.01, tau: 0.04, type: 'bandpass', f: glide(f * 1.6, f * 0.8), q: 2 });
  clack(x, c, 0.13, f * 0.62, 0.55, 0.02);
  rustle(x, c, 0.1, 0.18, 0.12);
  return x;
}

function magIn(c, pistol) {
  const x = c.buf(0.34);
  const f = pistol ? 2300 : 1350;
  burst(x, c.sr, 0, 0.1, c.rnd, 0.3, { attack: 0.012, tau: 0.035, type: 'bandpass', f: glide(f * 0.8, f * 1.5), q: 2 });
  clack(x, c, 0.085, f * 0.55, 0.7, 0.022); // seated
  sweep(x, c.sr, 0.085, 0.08, pistol ? 260 : 170, 90, 0.5, { tau: 0.02, fTau: 0.015 });
  clack(x, c, 0.115, f * 1.5, 0.5, 0.008); // the catch
  return x;
}

/** Charging handle back and released (rifle), or the slide racked (pistol). */
function bolt(c, pistol) {
  const x = c.buf(0.36);
  const f = pistol ? 2800 : 1650;
  const gap = pistol ? 0.09 : 0.13;
  burst(x, c.sr, 0, gap, c.rnd, 0.3, { attack: 0.008, tau: gap * 0.5, type: 'bandpass', f: glide(f * 0.9, f * 1.9), q: 3 });
  clack(x, c, 0.012, f, 0.55, 0.01);
  ring(x, c.sr, 0.02, [[f * 0.31, 0.2, 0.06]], 0.6); // the spring
  clack(x, c, gap + 0.02, f * 0.78, 0.95, 0.016);
  sweep(x, c.sr, gap + 0.02, 0.07, pistol ? 300 : 190, 90, 0.45, { tau: 0.018, fTau: 0.012 });
  return x;
}

function cloth(c) {
  const x = c.buf(0.32);
  rustle(x, c, 0, 0.3, 0.8, c.v ? 2300 : 1700);
  clack(x, c, 0.12 + c.r(0, 0.05), 3300, 0.07, 0.005); // sling hardware
  return x;
}

function holster(c, draw) {
  const x = c.buf(0.4);
  rustle(x, c, 0, 0.34, 0.7, draw ? 2100 : 1500);
  // Draw ends on the grip settling in the hand; holster on the gun dropping onto its sling.
  if (draw) clack(x, c, 0.27, 1500, 0.35, 0.012);
  else {
    sweep(x, c.sr, 0.22, 0.1, 150, 80, 0.4, { tau: 0.03, fTau: 0.02 });
    clack(x, c, 0.23, 950, 0.2, 0.015);
  }
  return x;
}

function whoosh(c) {
  const { sr } = c;
  const x = white(Math.round(0.3 * sr), c.rnd);
  const peak = c.r(0.42, 0.5);
  biquad(x, sr, 'bandpass', (t) => 500 + 2600 * Math.exp(-(((t - peak) / 0.22) ** 2)), 1.4);
  for (let i = 0; i < x.length; i++) x[i] *= Math.exp(-((((i / x.length) - peak) / 0.2) ** 2));
  return x;
}

/** A gun butt landing on a body: dull, with a crack of hard plastic on top. */
function meleeThud(c) {
  const { sr, rnd } = c;
  const x = c.buf(0.3);
  sweep(x, sr, 0, 0.22, 150, 55, 1, { tau: 0.05, fTau: 0.03 });
  burst(x, sr, 0, 0.12, rnd, 0.7, { tau: 0.025, type: 'lowpass', f: 900 });
  burst(x, sr, 0, 0.04, rnd, 0.35, { tau: 0.006, type: 'bandpass', f: 2400, q: 1 });
  clack(x, c, 0.004, 1200, 0.25, 0.01);
  drive(x, 1.6);
  return x;
}

/** A spent case on the ground: two or three bright bounces that speed up and die. */
function brass(c, metal) {
  const { sr } = c;
  const x = c.buf(metal ? 0.55 : 0.42);
  const f = c.r(4100, 5200);
  let at = 0.002;
  let gap = c.r(0.09, 0.13);
  let amp = 1;
  for (let i = 0; i < 4 && at < 0.4; i++) {
    const k = c.r(0.96, 1.05);
    const tau = (metal ? 0.05 : 0.022) * (1 - i * 0.15);
    ring(x, sr, at, [
      [f * k, 0.5, tau],
      [f * 1.52 * k, 0.4, tau * 0.8],
      [f * 2.21 * k, 0.25, tau * 0.6],
      [f * 0.61 * k, 0.2, tau * 0.5],
    ], amp);
    burst(x, sr, at, 0.012, c.rnd, amp * (metal ? 0.25 : 0.45), { tau: 0.003, type: 'highpass', f: 2500 });
    if (metal) ring(x, sr, at, [[c.r(700, 900), 0.3, 0.06]], amp); // the surface answers
    at += gap;
    gap *= 0.55;
    amp *= 0.5;
  }
  return x;
}

export const WEAPONS = {
  chopper_shot: { bus: 'gun', n: 4, peak: 0.97, vol: 1, jitter: 0.012, prio: 10, max: 5, gen: chopperShot },
  nine_shot: { bus: 'gun', n: 4, peak: 0.93, vol: 0.95, jitter: 0.012, prio: 10, max: 4, gen: nineShot },
  chopper_tail_out: { bus: 'tail', n: 2, peak: 0.66, vol: 1, prio: 6, max: 3, gen: (c) => streetTail(c, 4600, 1.7) },
  chopper_tail_in: { bus: 'tail', n: 2, peak: 0.72, vol: 1, prio: 6, max: 3, gen: (c) => shopTail(c, 6500, 0.95) },
  nine_tail_out: { bus: 'tail', n: 1, peak: 0.55, vol: 1, prio: 6, max: 3, gen: (c) => streetTail(c, 5600, 1.3) },
  nine_tail_in: { bus: 'tail', n: 1, peak: 0.62, vol: 1, prio: 6, max: 3, gen: (c) => shopTail(c, 7500, 0.8) },
  dry_fire: { bus: 'near', n: 2, peak: 0.5, prio: 7, max: 2, gen: dryFire },
  rifle_magout: { bus: 'near', n: 1, peak: 0.55, prio: 6, gen: (c) => magOut(c, false) },
  rifle_magin: { bus: 'near', n: 1, peak: 0.62, prio: 6, gen: (c) => magIn(c, false) },
  rifle_bolt: { bus: 'near', n: 1, peak: 0.7, prio: 6, gen: (c) => bolt(c, false) },
  pistol_magout: { bus: 'near', n: 1, peak: 0.5, prio: 6, gen: (c) => magOut(c, true) },
  pistol_magin: { bus: 'near', n: 1, peak: 0.56, prio: 6, gen: (c) => magIn(c, true) },
  pistol_slide: { bus: 'near', n: 1, peak: 0.66, prio: 6, gen: (c) => bolt(c, true) },
  cloth: { bus: 'near', n: 2, peak: 0.3, prio: 3, jitter: 0.08, gen: cloth },
  holster: { bus: 'near', n: 1, peak: 0.4, prio: 4, gen: (c) => holster(c, false) },
  draw: { bus: 'near', n: 1, peak: 0.42, prio: 4, gen: (c) => holster(c, true) },
  whoosh: { bus: 'near', n: 2, peak: 0.5, prio: 6, jitter: 0.06, gen: whoosh },
  melee_thud: { bus: 'near', n: 2, peak: 0.62, prio: 8, jitter: 0.05, gen: meleeThud },
  brass_asphalt: { bus: 'world', n: 4, peak: 0.34, prio: 2, max: 3, gap: 0.04, jitter: 0.06, ref: 1.6, roll: 1.4, gen: (c) => brass(c, false) },
  brass_metal: { bus: 'world', n: 3, peak: 0.36, prio: 2, max: 3, gap: 0.04, jitter: 0.06, ref: 1.6, roll: 1.4, gen: (c) => brass(c, true) },
};
