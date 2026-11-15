// Small math helpers shared by every module. Pure functions, no allocations (except v3).

import { Vector3 } from 'three';

const TAU = Math.PI * 2;

export const clamp = (x, min, max) => (x < min ? min : x > max ? max : x);

/** clamp(x, 0, 1) */
export const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);

export const lerp = (a, b, t) => a + (b - a) * t;

/** Where x sits between a and b (0 at a, 1 at b), unclamped. */
export const invLerp = (a, b, x) => (a === b ? 0 : (x - a) / (b - a));

/** Maps x from [inMin, inMax] to [outMin, outMax], clamped. */
export const remap = (x, inMin, inMax, outMin, outMax) =>
  lerp(outMin, outMax, clamp01(invLerp(inMin, inMax, x)));

/**
 * Frame-rate independent exponential approach: moves `current` toward `target`, covering
 * (1 − e^(−rate·dt)) of the remaining distance. rate 11 ≈ 90 % in 0.2 s.
 */
export const damp = (current, target, rate, dt) => target + (current - target) * Math.exp(-rate * dt);

/** damp() for angles: always takes the short way round. */
export const dampAngle = (current, target, rate, dt) =>
  current + angleDelta(current, target) * (1 - Math.exp(-rate * dt));

/** Exponential decay of a value toward zero: value · e^(−rate·dt). */
export const expDecay = (value, rate, dt) => value * Math.exp(-rate * dt);

/** Cubic Hermite step: 0 below e0, 1 above e1, 3t² − 2t³ in between. */
export function smoothstep(e0, e1, x) {
  const t = clamp01(invLerp(e0, e1, x));
  return t * t * (3 - 2 * t);
}

/** Quintic step (zero first and second derivative at both ends): t³(6t² − 15t + 10). */
export function smootherstep(e0, e1, x) {
  const t = clamp01(invLerp(e0, e1, x));
  return t * t * t * (t * (t * 6 - 15) + 10);
}

/** Wraps an angle to (−π, π]. */
export function wrapAngle(a) {
  a = (a + Math.PI) % TAU;
  if (a <= 0) a += TAU;
  return a - Math.PI;
}

/** Shortest signed rotation that takes `from` to `to`, in (−π, π]. */
export const angleDelta = (from, to) => wrapAngle(to - from);

/** Moves `current` toward `target` by at most `maxDelta` (never overshoots). */
export function moveToward(current, target, maxDelta) {
  const d = target - current;
  if (Math.abs(d) <= maxDelta) return target;
  return current + Math.sign(d) * maxDelta;
}

/** Shorthand for a new THREE.Vector3. Do not call in per-frame code: keep scratch vectors instead. */
export const v3 = (x = 0, y = 0, z = 0) => new Vector3(x, y, z);

/** True when a URL parameter is present and not switched off: `?shot`, `?shot=1`; `?shot=0` is off. */
export const paramOn = (params, name) =>
  params[name] !== undefined && params[name] !== '0' && params[name] !== 'false';

/** Numeric URL parameter, or `fallback` when it is absent or not a number. */
export function paramNumber(params, name, fallback) {
  const n = params[name] === undefined || params[name] === '' ? NaN : Number(params[name]);
  return Number.isFinite(n) ? n : fallback;
}
