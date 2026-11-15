// Rounds meeting the block (impacts per surface, ricochets, the whizz of a near miss), the hit and kill
// confirms, explosions, the propane jet, and the interface ticks.

import { biquad, burst, drive, echo, fade, glide, lowpass, mix, reverb, ring, seamless, shape, sweep, tone, white, brown, TAU } from './dsp.js';

function impact(c, surface) {
  const { sr, rnd } = c;
  const x = c.buf({ metal: 0.5, glass: 0.5, car: 0.38 }[surface] || 0.26);
  const k = c.r(0.9, 1.12);
  // Every hit starts with the same thing: a very short, bright snap.
  burst(x, sr, 0, 0.02, rnd, 0.7, { tau: 0.0035, type: 'highpass', f: 2200 });

  if (surface === 'concrete') {
    burst(x, sr, 0, 0.09, rnd, 0.9, { tau: 0.018, type: 'bandpass', f: 1500 * k, q: 0.8 });
    sweep(x, sr, 0, 0.08, 240 * k, 110, 0.6, { tau: 0.018, fTau: 0.012 });
    burst(x, sr, 0.015, 0.2, rnd, 0.3, { attack: 0.01, tau: 0.05, type: 'bandpass', f: 3600, q: 0.7 }); // chips
  } else if (surface === 'brick') {
    burst(x, sr, 0, 0.1, rnd, 0.9, { tau: 0.022, type: 'bandpass', f: 950 * k, q: 0.9 });
    sweep(x, sr, 0, 0.09, 200 * k, 90, 0.7, { tau: 0.022, fTau: 0.014 });
    burst(x, sr, 0.02, 0.22, rnd, 0.35, { attack: 0.015, tau: 0.06, type: 'bandpass', f: 2400, q: 0.6 }); // crumbs
  } else if (surface === 'metal') {
    // A ping: steel plate rings on after the snap.
    ring(x, sr, 0.001, [
      [1870 * k, 0.5, 0.11], [2930 * k, 0.4, 0.08], [4410 * k, 0.3, 0.06], [6120 * k, 0.2, 0.04], [830 * k, 0.35, 0.07],
    ], 0.8);
    burst(x, sr, 0, 0.03, rnd, 0.5, { tau: 0.006, type: 'bandpass', f: 3200, q: 1 });
  } else if (surface === 'car') {
    // Sheet metal: a hollow thunk with a short wobble.
    sweep(x, sr, 0, 0.16, 210 * k, 120, 0.9, { tau: 0.04, fTau: 0.03 });
    ring(x, sr, 0.001, [[285 * k, 0.5, 0.07], [472 * k, 0.4, 0.05], [735 * k, 0.3, 0.035], [1620 * k, 0.15, 0.02]], 0.8);
    burst(x, sr, 0, 0.05, rnd, 0.55, { tau: 0.01, type: 'bandpass', f: 1300, q: 0.8 });
  } else if (surface === 'glass') {
    // A tick, then fragments.
    ring(x, sr, 0, [[5200 * k, 0.5, 0.012], [7400 * k, 0.4, 0.01], [3300 * k, 0.4, 0.016]], 0.9);
    for (let i = 0; i < 9; i++) {
      const f = c.r(3500, 9000);
      ring(x, sr, 0.02 + c.r(0, 0.3) * c.rnd(), [[f, 0.5, c.r(0.01, 0.03)], [f * 1.47, 0.3, 0.012]], c.r(0.1, 0.35));
    }
  } else if (surface === 'wood') {
    sweep(x, sr, 0, 0.1, 320 * k, 170, 0.8, { tau: 0.024, fTau: 0.016 });
    ring(x, sr, 0, [[410 * k, 0.5, 0.03], [760 * k, 0.3, 0.02]], 0.7);
    burst(x, sr, 0, 0.07, rnd, 0.6, { tau: 0.014, type: 'bandpass', f: 1800, q: 0.9 }); // splinters
  } else if (surface === 'dirt') {
    sweep(x, sr, 0, 0.1, 150 * k, 70, 0.8, { tau: 0.03, fTau: 0.02 });
    burst(x, sr, 0, 0.16, rnd, 0.8, { tau: 0.035, type: 'lowpass', f: 1400 });
  } else if (surface === 'flesh') {
    // A body under a coat: dull slap, cloth, no ring. Kept dry and short.
    sweep(x, sr, 0, 0.12, 190 * k, 80, 0.9, { tau: 0.028, fTau: 0.02 });
    burst(x, sr, 0, 0.09, rnd, 0.8, { tau: 0.02, type: 'bandpass', f: 600 * k, q: 0.7 });
    burst(x, sr, 0.005, 0.1, rnd, 0.3, { attack: 0.005, tau: 0.025, type: 'bandpass', f: 2600, q: 0.7 });
  } else {
    // drone: carbon and thin alloy, a brittle clank
    ring(x, sr, 0, [[1240 * k, 0.5, 0.03], [2110 * k, 0.4, 0.022], [3350 * k, 0.3, 0.015], [5400 * k, 0.2, 0.01]], 0.8);
    burst(x, sr, 0, 0.05, rnd, 0.6, { tau: 0.01, type: 'bandpass', f: 2800, q: 0.8 });
    sweep(x, sr, 0, 0.06, 420, 240, 0.4, { tau: 0.014, fTau: 0.01 });
  }
  return x;
}

/** The round carrying on: a whine falling away. */
function ricochet(c) {
  const { sr } = c;
  const x = c.buf(0.6);
  const f0 = c.r(2600, 3600);
  const f1 = c.r(700, 1100);
  const wob = c.r(18, 32);
  tone(x, sr, 0, 0.55, (t) => f1 + (f0 - f1) * Math.exp(-t / 0.16) + 60 * Math.sin(TAU * wob * t), 0.8, { attack: 0.004, tau: 0.14, release: 0.1 });
  tone(x, sr, 0, 0.45, (t) => (f1 + (f0 - f1) * Math.exp(-t / 0.16)) * 1.51, 0.3, { attack: 0.004, tau: 0.09, release: 0.1 });
  const air = white(x.length, c.rnd);
  biquad(air, sr, 'bandpass', (t) => f1 + (f0 - f1) * Math.exp(-(t * 0.6) / 0.16), 6);
  shape(air, sr, 0.004, 0.12);
  mix(x, air, sr, 0, 0.5);
  return x;
}

/** An enemy round passing the head: a crack of air and a band of noise falling in pitch. */
function whizz(c) {
  const { sr } = c;
  const x = white(Math.round(0.24 * sr), c.rnd);
  const f0 = c.r(3800, 5200);
  biquad(x, sr, 'bandpass', glide(f0, f0 * 0.42), 3.2);
  for (let i = 0; i < x.length; i++) {
    const u = i / x.length;
    x[i] *= Math.exp(-(((u - 0.3) / 0.2) ** 2));
  }
  burst(x, sr, 0.062, 0.02, c.rnd, 0.6, { tau: 0.003, type: 'highpass', f: 3000 });
  return x;
}

/** Hit marker tick: `head` is higher, shorter and doubled. */
function hitConfirm(c, head) {
  const { sr } = c;
  const x = c.buf(head ? 0.12 : 0.1);
  const f = head ? 2350 : 1480;
  ring(x, sr, 0, [[f, 0.6, head ? 0.012 : 0.018], [f * 2.02, 0.3, 0.008], [f * 3.1, 0.15, 0.005]], 1);
  if (head) ring(x, sr, 0.032, [[f * 1.26, 0.6, 0.014], [f * 2.52, 0.3, 0.008]], 0.8);
  burst(x, sr, 0, 0.008, c.rnd, 0.3, { tau: 0.002, type: 'highpass', f: 4000 });
  return x;
}

/** Kill confirm: a muted knock and a falling fourth, unmistakably not a hit tick. */
function killConfirm(c) {
  const { sr } = c;
  const x = c.buf(0.34);
  sweep(x, sr, 0, 0.08, 320, 150, 0.8, { tau: 0.02, fTau: 0.012 });
  ring(x, sr, 0.004, [[1568, 0.6, 0.05], [3136, 0.2, 0.025]], 0.8); // G6
  ring(x, sr, 0.075, [[1175, 0.6, 0.09], [2350, 0.25, 0.05], [3525, 0.1, 0.03]], 0.9); // D6
  return x;
}

/** A blast: the crack, the pressure wave under it, a long rolling tail off the buildings, debris last. */
function* explosion(c, big) {
  const { sr, rnd } = c;
  const len = big ? 3.4 : 2.1;
  const x = c.buf(len);
  const s = big ? 1 : 0.72;
  burst(x, sr, 0, 0.09, rnd, 1.2, { tau: 0.012, type: 'highpass', f: big ? 900 : 1400 });
  burst(x, sr, 0, 0.5, rnd, 1.1, { tau: 0.09 * s, type: 'bandpass', f: big ? 420 : 600, q: 0.5 });
  sweep(x, sr, 0, len * 0.6, big ? 95 : 130, big ? 28 : 40, 1.6, { tau: 0.32 * s, fTau: 0.16 * s, attack: 0.002 });
  yield;
  // The roll: brown noise, darkening, with slow lumps in it.
  const roll = brown(x.length, rnd);
  shape(roll, sr, 0.03, len / 4.2);
  biquad(roll, sr, 'lowpass', glide(big ? 2600 : 3400, 240), 0.6);
  const lump = c.r(3, 5);
  for (let i = 0; i < roll.length; i++) roll[i] *= 0.7 + 0.3 * Math.sin((TAU * lump * i) / sr + 1);
  mix(x, roll, sr, 0.01, 1.3);
  yield;
  // Slap off the far side of the avenue.
  burst(x, sr, 0.19, 0.5, rnd, 0.5, { attack: 0.01, tau: 0.11, type: 'bandpass', f: 300, q: 0.5 });
  sweep(x, sr, 0.19, 0.4, 80, 38, 0.6, { tau: 0.12, fTau: 0.08 });
  // Debris coming down.
  const bits = big ? 26 : 12;
  for (let i = 0; i < bits; i++) {
    const at = 0.25 + c.rnd() ** 1.5 * (len - 0.9);
    const f = c.r(900, 4200);
    if (c.rnd() < 0.5) ring(x, sr, at, [[f, 0.5, c.r(0.008, 0.03)], [f * 1.6, 0.3, 0.01]], c.r(0.03, 0.1));
    else burst(x, sr, at, 0.05, rnd, c.r(0.04, 0.12), { tau: 0.012, type: 'bandpass', f, q: 1 });
  }
  yield;
  drive(x, big ? 2.6 : 2.1);
  const out = reverb(x, sr, { time: big ? 1.6 : 1.1, damp: 0.6, mix: 0.25, size: 1.6 }).subarray(0, x.length);
  return fade(out, sr, 0.001, 0.5);
}

/** Gas under pressure escaping a hole: a tight, bright, slightly unstable hiss with a whistle in it (loop). */
function hiss(c) {
  const { sr } = c;
  const x = white(Math.round(1.9 * sr), c.rnd);
  biquad(x, sr, 'highpass', 1800, 0.7);
  biquad(x, sr, 'peaking', 5200, 2.5, 9);
  const whistle = white(x.length, c.rnd);
  biquad(whistle, sr, 'bandpass', 3350, 30);
  for (let i = 0; i < x.length; i++) {
    const t = i / sr;
    x[i] = x[i] * (0.8 + 0.2 * Math.sin(TAU * 7.3 * t) * Math.sin(TAU * 0.9 * t)) + whistle[i] * 2.2;
  }
  return seamless(x, sr, 0.4);
}

// ---- interface -----------------------------------------------------------------------------------

function uiClick(c) {
  const x = c.buf(0.1);
  ring(x, c.sr, 0, [[1245, 0.6, 0.02], [1870, 0.35, 0.014], [3740, 0.2, 0.008]], 1);
  sweep(x, c.sr, 0, 0.04, 320, 160, 0.4, { tau: 0.01, fTau: 0.008 });
  return x;
}

function uiHover(c) {
  const x = c.buf(0.06);
  ring(x, c.sr, 0, [[2490, 0.6, 0.01], [3735, 0.3, 0.007]], 1);
  return x;
}

function uiTick(c) {
  const x = c.buf(0.03);
  ring(x, c.sr, 0, [[3100 * c.r(0.95, 1.05), 0.6, 0.004], [1550, 0.3, 0.005]], 1);
  return x;
}

/** The earpiece keying up (`open`) or letting go: a squelch chirp through a small speaker. */
function radio(c, open) {
  const { sr, rnd } = c;
  const x = c.buf(open ? 0.22 : 0.16);
  const n = white(x.length, rnd);
  shape(n, sr, 0.002, open ? 0.05 : 0.03);
  mix(x, n, sr, 0, 0.6);
  tone(x, sr, 0.01, 0.07, open ? glideFn(1250, 1900, 0.07) : glideFn(1700, 1100, 0.07), 0.6, { attack: 0.003, release: 0.02 });
  if (open) tone(x, sr, 0.1, 0.06, 2100, 0.4, { attack: 0.003, release: 0.02 });
  biquad(x, sr, 'bandpass', 1900, 1.1);
  lowpass(x, sr, 3600);
  return x;
}

const glideFn = (f0, f1, dur) => (t) => f0 + (f1 - f0) * Math.min(1, t / dur);

const imp = (surface, n, peak, extra) => ({
  bus: 'world', n, peak, prio: 4, max: 4, gap: 0.022, jitter: 0.07, ref: 5, roll: 1, gen: (c) => impact(c, surface), ...extra,
});

export const WORLD = {
  imp_concrete: imp('concrete', 3, 0.6),
  imp_brick: imp('brick', 3, 0.6),
  imp_metal: imp('metal', 3, 0.6),
  imp_car: imp('car', 3, 0.66),
  imp_glass: imp('glass', 2, 0.5),
  imp_wood: imp('wood', 2, 0.58),
  imp_dirt: imp('dirt', 2, 0.5),
  imp_flesh: imp('flesh', 3, 0.6, { prio: 6, ref: 7 }),
  imp_drone: imp('drone', 2, 0.6, { prio: 6, ref: 7 }),
  ricochet: { bus: 'world', n: 3, peak: 0.42, prio: 3, max: 2, gap: 0.22, jitter: 0.1, ref: 6, roll: 1, gen: ricochet },
  whizz: { bus: 'world', n: 3, peak: 0.6, prio: 7, max: 3, gap: 0.09, jitter: 0.1, ref: 2.5, roll: 0.6, gen: whizz },
  hit_confirm: { bus: 'dry', n: 1, peak: 0.42, prio: 8, max: 3, gap: 0.03, jitter: 0.03, gen: (c) => hitConfirm(c, false) },
  hit_head: { bus: 'dry', n: 1, peak: 0.46, prio: 8, max: 3, gap: 0.03, jitter: 0.02, gen: (c) => hitConfirm(c, true) },
  kill_confirm: { bus: 'dry', n: 1, peak: 0.5, prio: 9, max: 2, gap: 0.05, jitter: 0.015, gen: killConfirm },
  explosion_small: { bus: 'world', n: 2, sr: 32000, peak: 0.9, prio: 9, max: 3, gap: 0.05, jitter: 0.06, ref: 12, roll: 0.8, gen: (c) => explosion(c, false) },
  explosion_big: { bus: 'world', n: 2, sr: 32000, peak: 0.92, prio: 10, max: 3, gap: 0.05, jitter: 0.05, ref: 18, roll: 0.7, gen: (c) => explosion(c, true) },
  hiss: { bus: 'world', n: 1, peak: 0.4, loop: true, ref: 3, roll: 1.2, gen: hiss },
  ui_click: { bus: 'dry', n: 1, peak: 0.34, prio: 6, max: 2, jitter: 0.01, gen: uiClick },
  ui_hover: { bus: 'dry', n: 1, peak: 0.16, prio: 2, max: 2, gap: 0.03, jitter: 0.01, gen: uiHover },
  ui_tick: { bus: 'dry', n: 2, peak: 0.1, prio: 1, max: 2, gap: 0.025, jitter: 0.04, gen: uiTick },
  radio_in: { bus: 'dry', n: 1, peak: 0.3, prio: 6, max: 1, jitter: 0.01, gen: (c) => radio(c, true) },
  radio_out: { bus: 'dry', n: 1, peak: 0.22, prio: 5, max: 1, jitter: 0.01, gen: (c) => radio(c, false) },
};
