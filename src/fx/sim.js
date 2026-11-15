// Particle simulation for the billboard pools (pure: typed arrays in, typed arrays out, no three.js).
//
// A store is one Float32Array holding STRIDE floats per particle. Live particles are kept dense at the
// front: a dead one is overwritten by the last one, so the renderer draws exactly `count` instances and
// a frame costs nothing for empty slots.
//
// Everything a particle needs to move and fade is in its record, so integrate() needs no lookups:
// exponential drag toward the wind, gravity, sinusoidal turbulence, a size curve, fades, a colour ramp
// and an optional floor (bounce / die / stick flags).

export const STRIDE = 34;

// Field offsets inside one record.
export const X = 0;
export const Y = 1;
export const Z = 2;
export const VX = 3;
export const VY = 4;
export const VZ = 5;
export const AGE = 6;
export const LIFE = 7;
export const SIZE0 = 8; // world size (m) at birth …
export const SIZE1 = 9; // … and at death
export const CURVE = 10; // size = lerp(SIZE0, SIZE1, t ^ CURVE)
export const ROT = 11;
export const SPIN = 12;
export const R = 13; // colour at birth …
export const G = 14;
export const B = 15;
export const R1 = 16; // … and at death (lerped with t ^ RAMP)
export const G1 = 17;
export const B1 = 18;
export const ALPHA = 19; // peak opacity (lit pool) / intensity (additive pool)
export const FADE_IN = 20; // fraction of the life spent fading in
export const FADE_OUT = 21; // fraction of the life at which the fade-out begins
export const DRAG = 22; // 1/s, pulls the velocity toward wind × WIND
export const GRAV = 23; // multiples of g; negative rises
export const WIND = 24; // how much of the global wind the particle picks up
export const TURB = 25; // turbulence acceleration, m/s²
export const STRETCH = 26; // seconds of travel drawn as a streak (0 = round billboard)
export const FRAME = 27; // atlas cell
export const FLAGS = 28;
export const FLOOR = 29; // height of the ground under the particle
export const HEAT = 30; // lit pool: self-glow at birth, cools quickly
export const SHADE = 31; // lit pool: how much of the key light reaches the particle (0 = in shadow)
export const SEED = 32; // 0..1, decorrelates turbulence and bounces
export const RAMP = 33;

// FLAGS bits.
export const BOUNCE = 1; // bounces off the floor, losing energy
export const DIE = 2; // dies on the floor
export const STICK = 4; // stops dead on the floor
const RESTING = 8; // came to rest after bouncing

export const GRAVITY = 9.81;
const FLOOR_SKIN = 0.012; // particles rest this far above their floor
const REST_SPEED = 0.45; // a bounce slower than this ends the bouncing
const SOFT_FILL = 0.85; // low-priority spawns are refused above this share of the budget
const STEAL_PROBES = 6;
const HEAT_LOSS = 6; // 1/s: the glow inside fresh smoke is gone in about half a second

export function createStore(capacity) {
  return {
    data: new Float32Array(capacity * STRIDE),
    count: 0,
    capacity,
    budget: capacity, // soft cap, lowered by the quality preset
    spawned: 0,
    dropped: 0,
    stolen: 0,
  };
}

/** A blank spawn description. Recipes keep one, fill it in and hand it to spawn() over and over. */
export function createSpec() {
  return resetSpec({});
}

export function resetSpec(s) {
  s.x = s.y = s.z = 0;
  s.vx = s.vy = s.vz = 0;
  s.age = 0;
  s.life = 1;
  s.size = 0.5;
  s.size1 = -1; // negative: same as size
  s.curve = 1;
  s.rot = 0;
  s.spin = 0;
  s.r = s.g = s.b = 1;
  s.r1 = -1; // negative: the colour does not change
  s.g1 = s.b1 = 0;
  s.alpha = 1;
  s.fadeIn = 0.08;
  s.fadeOut = 0.5;
  s.drag = 0;
  s.gravity = 0;
  s.wind = 0;
  s.turb = 0;
  s.stretch = 0;
  s.frame = 0;
  s.flags = 0;
  s.floor = 0;
  s.heat = 0;
  s.shade = 1;
  s.seed = 0;
  s.ramp = 1;
  return s;
}

/** Index of the particle closest to the end of its life among a few spread-out probes. */
function mostSpent(store) {
  const d = store.data;
  const n = store.count;
  let best = 0;
  let bestT = -1;
  let i = (store.spawned * 7919) % n;
  const stride = Math.max(1, Math.floor(n / STEAL_PROBES));
  for (let k = 0; k < STEAL_PROBES; k++) {
    const o = i * STRIDE;
    const t = d[o + AGE] / d[o + LIFE];
    if (t > bestT) {
      bestT = t;
      best = i;
    }
    i = (i + stride) % n;
  }
  return best;
}

/**
 * Adds one particle described by `s`. Returns its index, or -1 when it was refused.
 * A full store recycles the particle nearest its end; `soft` spawns (trails, ambience) give way instead.
 */
export function spawn(store, s, soft = false) {
  let i = store.count;
  const budget = Math.min(store.budget, store.capacity);
  if (i >= budget) {
    if (soft || i === 0) {
      store.dropped++;
      return -1;
    }
    i = mostSpent(store);
    store.stolen++;
  } else {
    if (soft && i >= budget * SOFT_FILL) {
      store.dropped++;
      return -1;
    }
    store.count = i + 1;
  }
  const d = store.data;
  const o = i * STRIDE;
  d[o + X] = s.x;
  d[o + Y] = s.y;
  d[o + Z] = s.z;
  d[o + VX] = s.vx;
  d[o + VY] = s.vy;
  d[o + VZ] = s.vz;
  d[o + AGE] = s.age;
  d[o + LIFE] = s.life > 1e-4 ? s.life : 1e-4;
  d[o + SIZE0] = s.size;
  d[o + SIZE1] = s.size1 < 0 ? s.size : s.size1;
  d[o + CURVE] = s.curve;
  d[o + ROT] = s.rot;
  d[o + SPIN] = s.spin;
  d[o + R] = s.r;
  d[o + G] = s.g;
  d[o + B] = s.b;
  const same = s.r1 < 0;
  d[o + R1] = same ? s.r : s.r1;
  d[o + G1] = same ? s.g : s.g1;
  d[o + B1] = same ? s.b : s.b1;
  d[o + ALPHA] = s.alpha;
  d[o + FADE_IN] = s.fadeIn;
  d[o + FADE_OUT] = s.fadeOut < 0.999 ? s.fadeOut : 0.999;
  d[o + DRAG] = s.drag;
  d[o + GRAV] = s.gravity;
  d[o + WIND] = s.wind;
  d[o + TURB] = s.turb;
  d[o + STRETCH] = s.stretch;
  d[o + FRAME] = s.frame;
  d[o + FLAGS] = s.flags;
  d[o + FLOOR] = s.floor;
  d[o + HEAT] = s.heat;
  d[o + SHADE] = s.shade;
  d[o + SEED] = s.seed;
  d[o + RAMP] = s.ramp;
  store.spawned++;
  return i;
}

/**
 * Advances every particle. `env` is [dt, time, windX, windZ]: the step, the clock that drives the
 * turbulence and the global wind (a typed array, so the numbers cross the call without being boxed).
 * Dead particles are removed by moving the last record into their slot.
 */
export function integrate(store, env) {
  const dt = env[0];
  const time = env[1];
  const windX = env[2];
  const windZ = env[3];
  const d = store.data;
  let n = store.count;
  let i = 0;
  while (i < n) {
    const o = i * STRIDE;
    const age = d[o + AGE] + dt;
    let dead = age >= d[o + LIFE];
    if (!dead) {
      d[o + AGE] = age;
      const flags = d[o + FLAGS];
      if (!(flags & RESTING)) {
        let vx = d[o + VX];
        let vy = d[o + VY];
        let vz = d[o + VZ];
        const drag = d[o + DRAG] * dt;
        if (drag > 0) {
          const k = drag / (1 + drag); // implicit step: stable for any dt
          const w = d[o + WIND];
          vx += (windX * w - vx) * k;
          vy -= vy * k;
          vz += (windZ * w - vz) * k;
        }
        vy -= GRAVITY * d[o + GRAV] * dt;
        const turb = d[o + TURB] * dt;
        if (turb > 0) {
          const phase = d[o + SEED] * 61.7;
          vx += Math.sin(phase + time * 3.1 + d[o + Y] * 1.7) * turb;
          vy += Math.sin(phase * 1.9 + time * 2.3) * turb * 0.35;
          vz += Math.cos(phase * 1.3 + time * 2.7 + d[o + X] * 1.3) * turb;
        }
        d[o + X] += vx * dt;
        let y = d[o + Y] + vy * dt;
        d[o + Z] += vz * dt;
        if (flags !== 0 && vy < 0) {
          const floor = d[o + FLOOR] + FLOOR_SKIN;
          if (y < floor) {
            if (flags & DIE) {
              dead = true;
            } else if (flags & BOUNCE) {
              y = floor;
              // Keeps 25–55 % of the vertical speed and 65 % of the horizontal.
              vy = -vy * (0.25 + 0.3 * ((d[o + SEED] * 7.31 + age * 3.7) % 1));
              vx *= 0.65;
              vz *= 0.65;
              if (vy < REST_SPEED) {
                vx = vy = vz = 0;
                d[o + FLAGS] = flags | RESTING;
              }
            } else {
              y = floor;
              vx = vy = vz = 0;
              d[o + FLAGS] = flags | RESTING;
            }
          }
        }
        d[o + Y] = y;
        d[o + VX] = vx;
        d[o + VY] = vy;
        d[o + VZ] = vz;
        d[o + ROT] += d[o + SPIN] * dt;
      }
    }
    if (dead) {
      n--;
      if (i !== n) d.copyWithin(o, n * STRIDE, n * STRIDE + STRIDE);
    } else {
      i++;
    }
  }
  store.count = n;
}

// Layout of one drawn instance (see fx/particles.js): 16 floats.
export const INSTANCE = 16;

/**
 * Writes the drawable state of the particles into `out` (INSTANCE floats each), in the order given by
 * `order` (a list of particle indices, e.g. back to front) or in store order. Returns the instance count.
 */
export function writeInstances(store, out, order) {
  const d = store.data;
  const n = store.count;
  for (let k = 0; k < n; k++) {
    const o = (order ? order[k] : k) * STRIDE;
    const w = k * INSTANCE;
    const t = d[o + AGE] / d[o + LIFE];

    const curve = d[o + CURVE];
    const st = curve === 1 ? t : Math.pow(t, curve);
    const size = d[o + SIZE0] + (d[o + SIZE1] - d[o + SIZE0]) * st;

    const fadeIn = d[o + FADE_IN];
    const fadeOut = d[o + FADE_OUT];
    let fade = fadeIn > 0 && t < fadeIn ? t / fadeIn : 1;
    if (t > fadeOut) fade *= (1 - t) / (1 - fadeOut);

    const ramp = d[o + RAMP];
    const ct = ramp === 1 ? t : Math.pow(t, ramp);

    out[w] = d[o + X];
    out[w + 1] = d[o + Y];
    out[w + 2] = d[o + Z];
    out[w + 3] = size;
    out[w + 4] = d[o + R] + (d[o + R1] - d[o + R]) * ct;
    out[w + 5] = d[o + G] + (d[o + G1] - d[o + G]) * ct;
    out[w + 6] = d[o + B] + (d[o + B1] - d[o + B]) * ct;
    out[w + 7] = d[o + ALPHA] * fade;
    out[w + 8] = d[o + ROT];
    out[w + 9] = d[o + FRAME];
    out[w + 10] = d[o + SHADE];
    const heat = d[o + HEAT];
    out[w + 11] = heat > 0 ? heat * Math.exp(-HEAT_LOSS * d[o + AGE]) : 0;
    const stretch = d[o + STRETCH];
    if (stretch > 0) {
      // The streak is as long as the distance covered in `stretch` seconds, capped so that a fast
      // spark does not turn into a laser beam.
      let k2 = stretch;
      const vx = d[o + VX];
      const vy = d[o + VY];
      const vz = d[o + VZ];
      const len = Math.sqrt(vx * vx + vy * vy + vz * vz) * stretch;
      const cap = size * 45;
      if (len > cap) k2 *= cap / len;
      out[w + 12] = vx * k2;
      out[w + 13] = vy * k2;
      out[w + 14] = vz * k2;
    } else {
      out[w + 12] = out[w + 13] = out[w + 14] = 0;
    }
    out[w + 15] = d[o + FLOOR];
  }
  return n;
}

/**
 * Fills `order` with the particle indices sorted far to near for a viewer `view` = [eye x, y, z,
 * forward x, y, z]. `keys` is scratch of the same length. Shell sort: in place, no garbage, and quick
 * on the nearly sorted input a smoke column produces frame after frame.
 */
export function sortBackToFront(store, order, keys, view) {
  const ex = view[0];
  const ey = view[1];
  const ez = view[2];
  const fx = view[3];
  const fy = view[4];
  const fz = view[5];
  const d = store.data;
  const n = store.count;
  for (let i = 0; i < n; i++) {
    const o = i * STRIDE;
    order[i] = i;
    keys[i] = (d[o + X] - ex) * fx + (d[o + Y] - ey) * fy + (d[o + Z] - ez) * fz;
  }
  for (let gap = n >> 1; gap > 0; gap = gap === 2 ? 1 : Math.floor(gap / 2.2)) {
    for (let i = gap; i < n; i++) {
      const idx = order[i];
      const key = keys[idx];
      let j = i;
      while (j >= gap && keys[order[j - gap]] < key) {
        order[j] = order[j - gap];
        j -= gap;
      }
      order[j] = idx;
    }
  }
  return n;
}

/**
 * Turns an expected particle count into a whole number without bias: 2.3 becomes 2 seven times in ten
 * and 3 otherwise. `roll` is a uniform random number in [0, 1).
 */
export function stochasticRound(expected, roll) {
  const whole = Math.floor(expected);
  return whole + (roll < expected - whole ? 1 : 0);
}
