// Second-order springs and small easing helpers for the weapon module.
// A spring is a plain {x, v} pair; every step is the exact solution of
//   x'' = −w² (x − target) − 2 z w x'
// so the motion does not depend on the frame rate and cannot blow up on a slow frame.

/** A spring at rest at `x`. */
export const spring = (x = 0) => ({ x, v: 0 });

/**
 * Advances `s` by `dt` toward `target`. `w` is the angular frequency in rad/s, `z` the damping ratio
 * (1 = critically damped, below 1 it overshoots). Returns the new position.
 */
export function stepSpring(s, target, w, z, dt) {
  if (!(dt > 0)) return s.x;
  const y0 = s.x - target;
  const v0 = s.v;
  if (z >= 0.999) {
    const e = Math.exp(-w * dt);
    const k = v0 + w * y0;
    s.x = target + e * (y0 + k * dt);
    s.v = e * (v0 - w * k * dt);
  } else {
    const wd = w * Math.sqrt(1 - z * z);
    const e = Math.exp(-z * w * dt);
    const c = Math.cos(wd * dt);
    const sn = Math.sin(wd * dt);
    const b = (v0 + z * w * y0) / wd;
    const y = e * (y0 * c + b * sn);
    s.x = target + y;
    s.v = -z * w * y + e * wd * (b * c - y0 * sn);
  }
  return s.x;
}

/** Velocity impulse. */
export function kick(s, impulse) {
  s.v += impulse;
}

export function resetSpring(s, x = 0) {
  s.x = x;
  s.v = 0;
}

/** Quintic smootherstep on a clamped 0…1 input. */
export function ease(t) {
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  return t * t * t * (t * (t * 6 - 15) + 10);
}

/** 0 before `a`, 1 after `b`, eased in between. */
export const easeBetween = (a, b, t) => ease((t - a) / (b - a));

/** Overshooting ease-out ("back"): reaches 1 at t = 1 after passing it by about `s` · 10 %. */
export function easeOutBack(t, s = 1.25) {
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  const u = t - 1;
  return 1 + u * u * ((s + 1) * u + s);
}

/** Soft clamp to ±limit: linear near zero, flattening toward the limit. */
export const softLimit = (x, limit) => (limit * x) / (limit + Math.abs(x));
