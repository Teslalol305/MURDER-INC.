// Sample-level synthesis toolkit: everything the game hears is computed here into Float32Arrays
// (no WebAudio, so the same code runs in node for the level tests). All helpers work in place or add
// into a destination buffer, times are in seconds, frequencies in Hz.

export const TAU = Math.PI * 2;

/** Small fast seeded PRNG (mulberry32) → float in [0, 1). */
export function seeded(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** FNV-1a: sound name → seed, so a build always renders the same buffers. */
export function hashName(text) {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

export const buffer = (sr, secs) => new Float32Array(Math.max(1, Math.round(sr * secs)));

/** White noise in [-1, 1]. */
export function white(n, rnd) {
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) x[i] = rnd() * 2 - 1;
  return x;
}

/** Pink-ish noise (Paul Kellet's economy filter), roughly unit peak. */
export function pink(n, rnd) {
  const x = new Float32Array(n);
  let b0 = 0;
  let b1 = 0;
  let b2 = 0;
  for (let i = 0; i < n; i++) {
    const w = rnd() * 2 - 1;
    b0 = 0.99765 * b0 + w * 0.099046;
    b1 = 0.963 * b1 + w * 0.2965164;
    b2 = 0.57 * b2 + w * 1.0526913;
    x[i] = (b0 + b1 + b2 + w * 0.1848) * 0.25;
  }
  return x;
}

/** Brown noise (leaky integrator), roughly unit peak. */
export function brown(n, rnd) {
  const x = new Float32Array(n);
  let y = 0;
  for (let i = 0; i < n; i++) {
    y = (y + (rnd() * 2 - 1) * 0.045) * 0.996;
    x[i] = y * 3.2;
  }
  return x;
}

// ---- filters -------------------------------------------------------------------------------------

const co = new Float64Array(5);

/** RBJ cookbook coefficients, normalised by a0, into `co` = [b0, b1, b2, a1, a2]. */
function coefs(type, f, q, sr, gainDb) {
  const w = (TAU * Math.min(Math.max(f, 5), sr * 0.49)) / sr;
  const cs = Math.cos(w);
  const sn = Math.sin(w);
  const alpha = sn / (2 * q);
  let b0;
  let b1;
  let b2;
  let a0;
  let a1;
  let a2;
  if (type === 'lowpass') {
    b0 = (1 - cs) / 2; b1 = 1 - cs; b2 = b0; a0 = 1 + alpha; a1 = -2 * cs; a2 = 1 - alpha;
  } else if (type === 'highpass') {
    b0 = (1 + cs) / 2; b1 = -(1 + cs); b2 = b0; a0 = 1 + alpha; a1 = -2 * cs; a2 = 1 - alpha;
  } else if (type === 'bandpass') {
    b0 = alpha; b1 = 0; b2 = -alpha; a0 = 1 + alpha; a1 = -2 * cs; a2 = 1 - alpha;
  } else if (type === 'notch') {
    b0 = 1; b1 = -2 * cs; b2 = 1; a0 = 1 + alpha; a1 = -2 * cs; a2 = 1 - alpha;
  } else {
    const A = Math.pow(10, gainDb / 40);
    if (type === 'peaking') {
      b0 = 1 + alpha * A; b1 = -2 * cs; b2 = 1 - alpha * A; a0 = 1 + alpha / A; a1 = -2 * cs; a2 = 1 - alpha / A;
    } else {
      const k = 2 * Math.sqrt(A) * alpha;
      if (type === 'lowshelf') {
        b0 = A * (A + 1 - (A - 1) * cs + k); b1 = 2 * A * (A - 1 - (A + 1) * cs); b2 = A * (A + 1 - (A - 1) * cs - k);
        a0 = A + 1 + (A - 1) * cs + k; a1 = -2 * (A - 1 + (A + 1) * cs); a2 = A + 1 + (A - 1) * cs - k;
      } else {
        b0 = A * (A + 1 + (A - 1) * cs + k); b1 = -2 * A * (A - 1 + (A + 1) * cs); b2 = A * (A + 1 + (A - 1) * cs - k);
        a0 = A + 1 - (A - 1) * cs + k; a1 = 2 * (A - 1 - (A + 1) * cs); a2 = A + 1 - (A - 1) * cs - k;
      }
    }
  }
  co[0] = b0 / a0; co[1] = b1 / a0; co[2] = b2 / a0; co[3] = a1 / a0; co[4] = a2 / a0;
}

/**
 * Biquad in place. `f` is a frequency, or a function of progress 0..1 (a sweep: coefficients are then
 * refreshed every 48 samples). type: lowpass | highpass | bandpass | notch | peaking | lowshelf | highshelf.
 */
export function biquad(x, sr, type, f, q = 0.707, gainDb = 0) {
  const n = x.length;
  const sweep = typeof f === 'function';
  let x1 = 0;
  let x2 = 0;
  let y1 = 0;
  let y2 = 0;
  for (let i = 0; i < n; i += 48) {
    if (i === 0 || sweep) coefs(type, sweep ? f(i / n) : f, q, sr, gainDb);
    const b0 = co[0];
    const b1 = co[1];
    const b2 = co[2];
    const a1 = co[3];
    const a2 = co[4];
    const end = Math.min(n, i + 48);
    for (let j = i; j < end; j++) {
      const xi = x[j];
      const y = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
      x2 = x1; x1 = xi; y2 = y1; y1 = y;
      x[j] = y;
    }
  }
  return x;
}

export const lowpass = (x, sr, f, q) => biquad(x, sr, 'lowpass', f, q);
export const highpass = (x, sr, f, q) => biquad(x, sr, 'highpass', f, q);
export const bandpass = (x, sr, f, q) => biquad(x, sr, 'bandpass', f, q);

/** Exponential glide between two frequencies, as a sweep function for biquad(). */
export const glide = (f0, f1) => (t) => f0 * Math.pow(f1 / f0, t);

/** Sum of band-passed copies: a formant bank. bands = [[f, q, gain], …]. Returns a new buffer. */
export function formants(x, sr, bands) {
  const out = new Float32Array(x.length);
  for (const [f, q, g] of bands) {
    const y = biquad(Float32Array.from(x), sr, 'bandpass', f, q);
    for (let i = 0; i < y.length; i++) out[i] += y[i] * g;
  }
  return out;
}

// ---- envelopes and level -------------------------------------------------------------------------

/** Multiplies by `(1 − e^(−t/attack)) · e^(−t/tau)` (attack 0 = instant). */
export function shape(x, sr, attack, tau) {
  const ka = attack > 0 ? Math.exp(-1 / (attack * sr)) : 0;
  const kd = tau > 0 ? Math.exp(-1 / (tau * sr)) : 1;
  let a = 1;
  let d = 1;
  for (let i = 0; i < x.length; i++) {
    x[i] *= (1 - a) * d;
    a *= ka;
    d *= kd;
  }
  return x;
}

/** Multiplies by a piecewise-linear envelope: points = [[t, level], …] in seconds, held after the last. */
export function envelope(x, sr, points) {
  let k = 0;
  for (let i = 0; i < x.length; i++) {
    const t = i / sr;
    while (k < points.length - 2 && t >= points[k + 1][0]) k++;
    const [t0, v0] = points[k];
    const [t1, v1] = points[Math.min(k + 1, points.length - 1)];
    const u = t1 > t0 ? Math.min(1, Math.max(0, (t - t0) / (t1 - t0))) : 1;
    x[i] *= v0 + (v1 - v0) * u;
  }
  return x;
}

export function gain(x, g) {
  for (let i = 0; i < x.length; i++) x[i] *= g;
  return x;
}

/** Short linear fades at both ends (clicks). */
export function fade(x, sr, inSecs = 0.002, outSecs = 0.01) {
  const a = Math.min(x.length, Math.round(inSecs * sr));
  const b = Math.min(x.length, Math.round(outSecs * sr));
  for (let i = 0; i < a; i++) x[i] *= i / a;
  for (let i = 0; i < b; i++) x[x.length - 1 - i] *= i / b;
  return x;
}

export function measure(x) {
  let peak = 0;
  let sum = 0;
  for (let i = 0; i < x.length; i++) {
    const v = x[i];
    const a = v < 0 ? -v : v;
    if (a > peak) peak = a;
    sum += v * v;
  }
  return { peak, rms: Math.sqrt(sum / Math.max(1, x.length)) };
}

/** Removes any offset, then scales so the largest sample is `peak`. */
export function normalize(x, peak = 0.9) {
  let mean = 0;
  for (let i = 0; i < x.length; i++) mean += x[i];
  mean /= Math.max(1, x.length);
  let top = 0;
  for (let i = 0; i < x.length; i++) {
    x[i] -= mean;
    const a = Math.abs(x[i]);
    if (a > top) top = a;
  }
  if (top > 1e-9) gain(x, peak / top);
  return x;
}

/** tanh saturation: `amount` 1 is gentle, 4 is crushed. Output stays within ±1. */
export function drive(x, amount = 2) {
  const k = 1 / Math.tanh(amount);
  for (let i = 0; i < x.length; i++) x[i] = Math.tanh(x[i] * amount) * k;
  return x;
}

/** Adds `src × g` into `dst` starting at `at` seconds (clipped to dst). */
export function mix(dst, src, sr, at = 0, g = 1) {
  const o = Math.round(at * sr);
  const n = Math.min(src.length, dst.length - o);
  for (let i = Math.max(0, -o); i < n; i++) dst[o + i] += src[i] * g;
  return dst;
}

// ---- sources -------------------------------------------------------------------------------------

/**
 * Sine whose pitch falls (or rises) exponentially from f0 to f1 with time constant fTau, with an
 * attack / decay envelope: kicks, thumps, zaps, booms. Added into dst.
 */
export function sweep(dst, sr, at, dur, f0, f1, amp, { tau = dur / 3, fTau = dur / 4, attack = 0.0008, phase = 0 } = {}) {
  const o = Math.round(at * sr);
  const n = Math.min(Math.round(dur * sr), dst.length - o);
  const kf = Math.exp(-1 / (fTau * sr));
  const kd = Math.exp(-1 / (tau * sr));
  const ka = attack > 0 ? Math.exp(-1 / (attack * sr)) : 0;
  let df = f0 - f1;
  let ph = phase;
  let d = amp;
  let a = 1;
  const tail = Math.max(1, Math.round(0.004 * sr));
  for (let i = 0; i < n; i++) {
    const end = i > n - tail ? (n - i) / tail : 1;
    dst[o + i] += Math.sin(ph) * d * (1 - a) * end;
    ph += (TAU * (f1 + df)) / sr;
    df *= kf;
    d *= kd;
    a *= ka;
  }
  return dst;
}

/** Steady or vibrato sine with attack / decay / release. `f` may be a function of seconds. */
export function tone(dst, sr, at, dur, f, amp, { attack = 0.003, tau = 0, release = 0.01, vib = 0, vibRate = 5, phase = 0 } = {}) {
  const o = Math.round(at * sr);
  const n = Math.min(Math.round(dur * sr), dst.length - o);
  const fn = typeof f === 'function';
  const kd = tau > 0 ? Math.exp(-1 / (tau * sr)) : 1;
  const na = Math.max(1, Math.round(attack * sr));
  const nr = Math.max(1, Math.round(release * sr));
  let ph = phase;
  let d = amp;
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    let e = d;
    if (i < na) e *= i / na;
    if (i > n - nr) e *= (n - i) / nr;
    dst[o + i] += Math.sin(ph) * e;
    const fq = (fn ? f(t) : f) * (vib ? 1 + vib * Math.sin(TAU * vibRate * t) : 1);
    ph += (TAU * fq) / sr;
    d *= kd;
  }
  return dst;
}

/** Two-operator FM voice (electric piano tines, bells): carrier fc, modulator fc × ratio, decaying index. */
export function fm(dst, sr, at, dur, fc, ratio, index, amp, { tau = dur / 3, indexTau = dur / 6, attack = 0.002, release = 0.02 } = {}) {
  const o = Math.round(at * sr);
  const n = Math.min(Math.round(dur * sr), dst.length - o);
  const wc = (TAU * fc) / sr;
  const wm = wc * ratio;
  const kd = Math.exp(-1 / (tau * sr));
  const ki = Math.exp(-1 / (indexTau * sr));
  const na = Math.max(1, Math.round(attack * sr));
  const nr = Math.max(1, Math.round(release * sr));
  let d = amp;
  let ix = index;
  for (let i = 0; i < n; i++) {
    let e = d;
    if (i < na) e *= i / na;
    if (i > n - nr) e *= (n - i) / nr;
    dst[o + i] += Math.sin(wc * i + ix * Math.sin(wm * i)) * e;
    d *= kd;
    ix *= ki;
  }
  return dst;
}

/**
 * Band-limited-ish sawtooth (polyBLEP) added into dst. `f` may be a function of seconds.
 * `pulse` > 0 turns it into a pulse wave of that duty cycle.
 */
export function saw(dst, sr, at, dur, f, amp, { phase = 0, pulse = 0 } = {}) {
  const o = Math.round(at * sr);
  const n = Math.min(Math.round(dur * sr), dst.length - o);
  const fn = typeof f === 'function';
  let ph = phase % 1;
  for (let i = 0; i < n; i++) {
    const dt = (fn ? f(i / sr) : f) / sr;
    let v = 2 * ph - 1;
    if (ph < dt) {
      const t = ph / dt;
      v -= t + t - t * t - 1;
    } else if (ph > 1 - dt) {
      const t = (ph - 1) / dt;
      v -= t * t + t + t + 1;
    }
    if (pulse > 0) {
      let p2 = ph + pulse;
      if (p2 >= 1) p2 -= 1;
      let w = 2 * p2 - 1;
      if (p2 < dt) {
        const t = p2 / dt;
        w -= t + t - t * t - 1;
      } else if (p2 > 1 - dt) {
        const t = (p2 - 1) / dt;
        w -= t * t + t + t + 1;
      }
      v -= w;
    }
    dst[o + i] += v * amp;
    ph += dt;
    if (ph >= 1) ph -= 1;
  }
  return dst;
}

/**
 * Bank of decaying sinusoids (struck metal, glass, brass casings, bells), as two-pole resonators so
 * each partial costs two multiplies a sample. partials = [[f, amp, tau], …]. Added into dst.
 */
export function ring(dst, sr, at, partials, g = 1) {
  const o = Math.round(at * sr);
  for (const [f, amp, tau] of partials) {
    if (f >= sr * 0.48) continue;
    const n = Math.min(Math.round(tau * 7 * sr), dst.length - o);
    const r = Math.exp(-1 / (tau * sr));
    const w = (TAU * f) / sr;
    const c = 2 * r * Math.cos(w);
    const r2 = r * r;
    let y1 = Math.sin(w) * amp * g; // starts as a sine at phase 0
    let y2 = 0;
    for (let i = 0; i < n; i++) {
      dst[o + i] += y2;
      const y = c * y1 - r2 * y2;
      y2 = y1;
      y1 = y;
    }
  }
  return dst;
}

/**
 * Filtered noise burst with an attack / decay envelope, added into dst.
 * opts: {attack, tau, type, f (Hz or sweep fn), q, color: 'white' | 'pink' | 'brown'}
 */
export function burst(dst, sr, at, dur, rnd, amp, { attack = 0, tau = dur / 4, type = '', f = 1000, q = 0.707, color = 'white' } = {}) {
  const n = Math.round(dur * sr);
  const x = color === 'pink' ? pink(n, rnd) : color === 'brown' ? brown(n, rnd) : white(n, rnd);
  if (type) biquad(x, sr, type, f, q);
  shape(x, sr, attack, tau);
  fade(x, sr, 0, Math.min(dur * 0.3, 0.02));
  return mix(dst, x, sr, at, amp);
}

// ---- time effects --------------------------------------------------------------------------------

/** Feedback delay (slapback, echo). Returns a new buffer, `tail` seconds longer. */
export function echo(x, sr, delay, feedback, wet, { lp = 0, tail = delay * 4 } = {}) {
  const d = Math.max(1, Math.round(delay * sr));
  const out = new Float32Array(x.length + Math.round(tail * sr));
  const line = new Float32Array(out.length);
  const k = lp > 0 ? 1 - Math.exp((-TAU * lp) / sr) : 1;
  let s = 0;
  for (let i = 0; i < out.length; i++) {
    const dry = i < x.length ? x[i] : 0;
    const back = i >= d ? line[i - d] : 0;
    s += (back - s) * k;
    line[i] = dry + s * feedback;
    out[i] = dry + s * wet;
  }
  return out;
}

const COMBS = [0.0297, 0.0371, 0.0411, 0.0437, 0.0353, 0.0461];
const ALLPASSES = [0.005, 0.0017, 0.0113];

/**
 * Small Schroeder reverb (damped combs into all-passes). Returns a new buffer with the tail attached.
 * opts: {time (RT60-ish seconds), damp 0..1, mix (wet level, dry stays at 1), size (scales the delays), pre}
 */
export function reverb(x, sr, { time = 1, damp = 0.4, mix: wet = 0.3, size = 1, pre = 0 } = {}) {
  const tailN = Math.round((time * 1.1 + pre) * sr);
  const n = x.length + tailN;
  const acc = new Float32Array(n);
  const p = Math.round(pre * sr);
  for (const t of COMBS) {
    const d = Math.max(2, Math.round(t * size * sr));
    const g = Math.pow(10, (-3 * d) / (time * sr));
    const line = new Float32Array(d);
    let lpState = 0;
    let w = 0;
    for (let i = 0; i < n; i++) {
      const j = i - p;
      const input = j >= 0 && j < x.length ? x[j] : 0;
      const y = line[w];
      lpState = y + (lpState - y) * damp;
      line[w] = input + lpState * g;
      acc[i] += y;
      if (++w === d) w = 0;
    }
  }
  for (const t of ALLPASSES) {
    const d = Math.max(2, Math.round(t * size * sr));
    const line = new Float32Array(d);
    let w = 0;
    for (let i = 0; i < n; i++) {
      const delayed = line[w];
      const input = acc[i];
      line[w] = input + delayed * 0.5;
      acc[i] = delayed - input * 0.5;
      if (++w === d) w = 0;
    }
  }
  const k = wet / COMBS.length;
  for (let i = 0; i < n; i++) acc[i] = acc[i] * k + (i < x.length ? x[i] : 0);
  return acc;
}

/** Folds everything past `length` samples back onto the start: a rendered tail becomes part of the loop. */
export function wrap(x, length) {
  const out = new Float32Array(length);
  for (let i = 0; i < x.length; i++) out[i % length] += x[i];
  return out;
}

/** Makes a noise bed loop seamlessly: the last `secs` are cross-faded (equal power) into the first. */
export function seamless(x, sr, secs = 0.5) {
  const f = Math.min(Math.round(secs * sr), x.length >> 1);
  const length = x.length - f;
  const out = x.slice(0, length);
  for (let i = 0; i < f; i++) {
    const u = i / f;
    out[i] = x[i] * Math.sin((u * Math.PI) / 2) + x[length + i] * Math.cos((u * Math.PI) / 2);
  }
  return out;
}

/** Synthetic impulse response (one channel): early reflections, then a decaying, darkening noise tail. */
export function impulse(sr, secs, rnd, { bright = 6000, dark = 900, early = [], density = 1 } = {}) {
  const n = Math.round(secs * sr);
  const x = white(n, rnd);
  const tau = secs / 6.9; // −60 dB at the end
  shape(x, sr, 0.004, tau);
  if (density < 1) for (let i = 0; i < n; i++) if (rnd() > density) x[i] = 0;
  biquad(x, sr, 'lowpass', glide(bright, dark), 0.6);
  for (const [t, g] of early) {
    const i = Math.round(t * sr);
    if (i < n) x[i] += g * (rnd() < 0.5 ? -1 : 1);
  }
  fade(x, sr, 0, secs * 0.2);
  // A unit-energy response keeps the wet level predictable whatever its length.
  let e = 0;
  for (let i = 0; i < n; i++) e += x[i] * x[i];
  return gain(x, 1 / Math.sqrt(e || 1));
}

/** Equal-tempered pitch: midi note number → Hz. */
export const midi = (note) => 440 * Math.pow(2, (note - 69) / 12);
