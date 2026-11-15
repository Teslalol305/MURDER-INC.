// Rule himself: footsteps per surface (walk and sprint sets), jump, land, taking a hit, the ear-ring,
// the low-health heartbeat, and the reel: the grab loop while holding and the latch when it is his.

import { biquad, burst, drive, fade, glide, mix, ring, seamless, sweep, tone, white, TAU } from './dsp.js';

/** Grit under a sole: noise broken into grains. */
function grit(x, c, at, dur, amp, f, q = 0.9) {
  const n = white(Math.round(dur * c.sr), c.rnd);
  let g = 0;
  for (let i = 0; i < n.length; i++) {
    if (c.rnd() < 0.012) g = c.rnd();
    g *= 0.9985;
    const u = i / n.length;
    n[i] *= (0.25 + g) * Math.exp(-u * 4) * Math.min(1, u * 30);
  }
  biquad(n, c.sr, 'bandpass', f, q);
  mix(x, n, c.sr, at, amp);
}

/** One footfall: heel, then the sole rolling down. `run` = harder, shorter, more scuff. */
function step(c, surface, run) {
  const { sr, rnd } = c;
  const x = c.buf(surface === 'metal' ? 0.34 : 0.24);
  const hard = run ? 1.25 : 1;
  const toe = run ? 0.035 : 0.055 + c.r(0, 0.012);
  const heel = (f0, f1, amp, tau) => sweep(x, sr, 0, 0.12, f0 * c.r(0.92, 1.08), f1, amp * hard, { tau, fTau: tau * 0.6 });

  if (surface === 'asphalt') {
    heel(150, 70, 0.8, 0.02);
    burst(x, sr, 0, 0.05, rnd, 0.5 * hard, { tau: 0.01, type: 'bandpass', f: c.r(1500, 2100), q: 0.8 });
    grit(x, c, toe, 0.13, run ? 0.9 : 0.6, c.r(2600, 3800));
  } else if (surface === 'concrete') {
    heel(170, 85, 0.7, 0.016);
    burst(x, sr, 0, 0.045, rnd, 0.75 * hard, { tau: 0.008, type: 'bandpass', f: c.r(1100, 1500), q: 1.1 });
    burst(x, sr, toe, 0.06, rnd, 0.4, { tau: 0.012, type: 'bandpass', f: c.r(2000, 2600), q: 0.9 });
    grit(x, c, toe, 0.09, run ? 0.5 : 0.25, 4200);
  } else if (surface === 'metal') {
    heel(190, 100, 0.6, 0.02);
    const k = c.r(0.9, 1.1);
    ring(x, sr, 0.002, [[312 * k, 0.5, 0.09], [547 * k, 0.4, 0.07], [866 * k, 0.3, 0.05], [1390 * k, 0.2, 0.03], [2210 * k, 0.12, 0.02]], 0.55 * hard);
    burst(x, sr, 0, 0.03, rnd, 0.5 * hard, { tau: 0.005, type: 'bandpass', f: 2400, q: 1 });
    ring(x, sr, toe, [[420 * k, 0.3, 0.06], [1130 * k, 0.2, 0.03]], 0.4); // the tread plate answers the toe
  } else if (surface === 'wood') {
    heel(230, 120, 0.9, 0.028);
    const k = c.r(0.92, 1.08);
    ring(x, sr, 0.001, [[176 * k, 0.6, 0.05], [338 * k, 0.4, 0.035], [610 * k, 0.2, 0.02]], 0.7 * hard);
    burst(x, sr, 0, 0.04, rnd, 0.35 * hard, { tau: 0.008, type: 'bandpass', f: 900, q: 1 });
    burst(x, sr, toe, 0.05, rnd, 0.25, { tau: 0.012, type: 'bandpass', f: 1500, q: 1 });
  } else {
    // dirt: no edge at all, then a crunch of loose stuff
    heel(120, 60, 0.75, 0.03);
    burst(x, sr, 0, 0.08, rnd, 0.5 * hard, { tau: 0.02, type: 'lowpass', f: 700 });
    grit(x, c, toe * 0.6, 0.16, run ? 1 : 0.8, c.r(1300, 1900), 0.6);
  }
  return x;
}

function jump(c) {
  const { sr } = c;
  const x = c.buf(0.3);
  // Clothes and gear lifting: a soft upward rush, and the push-off scuff under it.
  const n = white(x.length, c.rnd);
  biquad(n, sr, 'bandpass', glide(700, 2400), 1);
  for (let i = 0; i < n.length; i++) n[i] *= Math.sin((Math.PI * i) / n.length) ** 2;
  mix(x, n, sr, 0, 0.7);
  grit(x, c, 0, 0.09, 0.6, 3000);
  sweep(x, sr, 0, 0.1, 130, 70, 0.5, { tau: 0.025, fTau: 0.02 });
  return x;
}

function land(c) {
  const { sr, rnd } = c;
  const x = c.buf(0.4);
  sweep(x, sr, 0, 0.28, 125, 48, 1, { tau: 0.06, fTau: 0.035 });
  burst(x, sr, 0, 0.1, rnd, 0.6, { tau: 0.02, type: 'lowpass', f: 1100 });
  grit(x, c, 0.01, 0.2, 0.5, 2600);
  // Gear settling a moment later.
  burst(x, sr, 0.07, 0.2, rnd, 0.2, { attack: 0.02, tau: 0.05, type: 'bandpass', f: 1900, q: 0.8 });
  ring(x, sr, 0.09, [[3100, 0.3, 0.006], [1700, 0.3, 0.01]], 0.12);
  drive(x, 1.5);
  return x;
}

/** Getting hit: a punch in the chest, felt more than heard. */
function hurt(c) {
  const { sr, rnd } = c;
  const x = c.buf(0.42);
  sweep(x, sr, 0, 0.36, 110 * c.r(0.92, 1.08), 42, 1, { tau: 0.085, fTau: 0.05 });
  burst(x, sr, 0, 0.12, rnd, 0.7, { tau: 0.022, type: 'lowpass', f: 650 });
  burst(x, sr, 0, 0.05, rnd, 0.35, { tau: 0.008, type: 'bandpass', f: 1800, q: 0.8 });
  drive(x, 2.2);
  return x;
}

/** The whine after a hit: two close high partials beating, fading for two seconds. */
function earRing(c) {
  const { sr } = c;
  const x = c.buf(2.4);
  tone(x, sr, 0, 2.4, 4130, 0.6, { attack: 0.02, tau: 0.7, release: 0.4 });
  tone(x, sr, 0, 2.4, 4171, 0.4, { attack: 0.05, tau: 0.6, release: 0.4 });
  tone(x, sr, 0, 2.0, 6240, 0.12, { attack: 0.03, tau: 0.35, release: 0.3 });
  return x;
}

/** One lub-dub, as a loop: the mixer plays it faster as health drops. */
function heartbeat(c) {
  const { sr, rnd } = c;
  const x = c.buf(0.86);
  const beat = (at, f, amp) => {
    sweep(x, sr, at, 0.2, f, f * 0.55, amp, { tau: 0.045, fTau: 0.04, attack: 0.004 });
    burst(x, sr, at, 0.08, rnd, amp * 0.25, { attack: 0.004, tau: 0.02, type: 'lowpass', f: 180 });
  };
  beat(0.02, 62, 1);
  beat(0.25, 78, 0.7);
  return x;
}

/** Hands working the case's latches: a ratchet over the reel's flywheel hum (loop; pitch follows progress). */
function reelGrab(c) {
  const { sr, rnd } = c;
  const len = 0.6;
  const x = c.buf(len);
  for (let i = 0; i < x.length; i++) {
    const t = i / sr;
    // 110 Hz whirr: exactly 66 cycles in the loop, so it closes on itself.
    x[i] += 0.22 * Math.sin(TAU * 110 * t) + 0.12 * Math.sin(TAU * 220 * t + 1) + 0.06 * Math.sin(TAU * 330 * t);
    x[i] *= 0.8 + 0.2 * Math.sin((TAU * t * 5) / len);
  }
  for (let k = 0; k < 12; k++) {
    const at = (k / 12) * len;
    ring(x, sr, at, [[2400, 0.5, 0.004], [3900, 0.4, 0.003], [1300, 0.3, 0.006]], 0.5);
  }
  const hiss = white(x.length, rnd);
  biquad(hiss, sr, 'bandpass', 5200, 1.5);
  mix(x, hiss, sr, 0, 0.05);
  return fade(x, sr, 0.001, 0.001);
}

/** The reel is secured: latch, lid, and a bright two-note confirm (the music sting follows on its own). */
function reelSecure(c) {
  const { sr, rnd } = c;
  const x = c.buf(1.1);
  ring(x, sr, 0, [[1500, 0.5, 0.015], [2650, 0.4, 0.01], [690, 0.4, 0.03]], 0.7);
  burst(x, sr, 0, 0.04, rnd, 0.4, { tau: 0.006, type: 'bandpass', f: 3000, q: 1 });
  sweep(x, sr, 0.06, 0.14, 180, 70, 0.8, { tau: 0.035, fTau: 0.025 });
  ring(x, sr, 0.1, [[1568, 0.5, 0.22], [3136, 0.2, 0.12], [4700, 0.1, 0.06]], 0.5); // G6
  ring(x, sr, 0.22, [[2349, 0.5, 0.3], [4698, 0.2, 0.16], [7040, 0.08, 0.08]], 0.5); // D7
  return x;
}

const SURFACES = ['asphalt', 'concrete', 'metal', 'wood', 'dirt'];
const steps = {};
for (const s of SURFACES) {
  const peak = { asphalt: 0.42, concrete: 0.44, metal: 0.5, wood: 0.48, dirt: 0.38 }[s];
  const shared = { bus: 'near', prio: 3, max: 3, jitter: 0.06 };
  steps[`step_${s}`] = { ...shared, n: 4, peak, gen: (c) => step(c, s, false) };
  steps[`step_${s}_run`] = { ...shared, n: 3, peak: peak * 1.3, gen: (c) => step(c, s, true) };
}

export const PLAYER = {
  ...steps,
  jump: { bus: 'near', n: 1, peak: 0.4, prio: 4, jitter: 0.05, gen: jump },
  land: { bus: 'near', n: 2, peak: 0.75, prio: 5, jitter: 0.05, gen: land },
  hurt: { bus: 'dry', n: 3, peak: 0.85, prio: 9, max: 3, gap: 0.06, jitter: 0.05, gen: hurt },
  ear_ring: { bus: 'dry', n: 1, peak: 0.22, prio: 5, max: 1, gap: 1.8, jitter: 0.01, sr: 22050, gen: earRing },
  heartbeat: { bus: 'dry', n: 1, peak: 0.5, loop: true, sr: 22050, gen: heartbeat },
  reel_grab: { bus: 'near', n: 1, peak: 0.3, loop: true, gen: reelGrab },
  reel_secure: { bus: 'dry', n: 1, peak: 0.6, prio: 8, gen: reelSecure },
};

export const STEP_SURFACES = SURFACES;
