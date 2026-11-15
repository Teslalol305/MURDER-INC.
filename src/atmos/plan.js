// Planning logic for the atmosphere: everything that can be decided without three.js or a canvas.
// Plain numbers and arrays in, plain objects out, so it runs under `node --test` (test/atmos-plan.test.js).
//
//   fitShadowFrustum   light position and orthographic frustum that wrap the block, snapped to shadow texels
//   pickRealLights / lampClaim  which lamps hold the few real lights: at boot, and from where the camera is
//   rowStep / continueRow  spacing of a row of lamps, and the row carried on past the bounds
//   trainTimeline      when a train enters, covers and leaves the block
//   createTrainSchedule  start times of the passes
//   planCity           footprints of the buildings beyond the bounds
//   skylineProfile     roof line of a far skyline card
//   hazeOutside / fogTransmittance   the same haze the shaders compute

const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

function normalize(v) {
  const len = Math.hypot(v[0], v[1], v[2]) || 1;
  return [v[0] / len, v[1] / len, v[2] / len];
}

// ------------------------------------------------------------------------------------------------
// Shadow frustum
// ------------------------------------------------------------------------------------------------

/**
 * Axes of a camera that looks along `dir` with +Y up: the same basis Matrix4.lookAt builds, so a
 * DirectionalLight placed with the result of fitShadowFrustum() sees exactly the fitted rectangle.
 * @returns {{right: number[], up: number[], forward: number[]}}
 */
export function lightBasis(dir) {
  const forward = normalize(dir);
  const back = [-forward[0], -forward[1], -forward[2]];
  let right = cross([0, 1, 0], back);
  // Straight down has no sideways: pick one (three.js nudges the same way).
  if (Math.hypot(right[0], right[1], right[2]) < 1e-6) right = [1, 0, 0];
  right = normalize(right);
  return { right, up: cross(back, right), forward };
}

/**
 * Fits an orthographic shadow frustum around the box [minX…maxX] × [minY…maxY] × [minZ…maxZ] for a
 * light travelling along `dir`.
 *
 * - The rectangle is padded by `margin` and rounded up to whole metres, and its centre is snapped to
 *   the shadow-map texel grid (the grid is anchored at the world origin). A box that grows or shifts
 *   a little therefore moves the frustum by whole texels: shadow edges do not crawl.
 * - near / far hug the box (the eye sits `backoff` metres in front of its nearest corner), which keeps
 *   all of the depth precision on the block.
 *
 * @returns {{position: number[], target: number[], left: number, right: number, top: number, bottom: number,
 *            near: number, far: number, width: number, height: number, depth: number, texel: number[]}}
 */
export function fitShadowFrustum({ bounds, minY = 0, maxY = 30, dir, mapSize = 2048, margin = 2, backoff = 40, pad = 1 }) {
  const basis = lightBasis(dir);
  const lo = [Infinity, Infinity, Infinity];
  const hi = [-Infinity, -Infinity, -Infinity];
  for (const x of [bounds.minX, bounds.maxX]) {
    for (const y of [minY, maxY]) {
      for (const z of [bounds.minZ, bounds.maxZ]) {
        const p = [x, y, z];
        const c = [dot(p, basis.right), dot(p, basis.up), dot(p, basis.forward)];
        for (let i = 0; i < 3; i++) {
          if (c[i] < lo[i]) lo[i] = c[i];
          if (c[i] > hi[i]) hi[i] = c[i];
        }
      }
    }
  }

  const size = Math.max(1, mapSize | 0);
  const width = Math.ceil(hi[0] - lo[0] + 2 * margin);
  const height = Math.ceil(hi[1] - lo[1] + 2 * margin);
  const texel = [width / size, height / size];
  const cx = Math.round((lo[0] + hi[0]) / 2 / texel[0]) * texel[0];
  const cy = Math.round((lo[1] + hi[1]) / 2 / texel[1]) * texel[1];
  const depth = hi[2] - lo[2];
  const eyeDepth = lo[2] - backoff;

  const at = (d) => [
    basis.right[0] * cx + basis.up[0] * cy + basis.forward[0] * d,
    basis.right[1] * cx + basis.up[1] * cy + basis.forward[1] * d,
    basis.right[2] * cx + basis.up[2] * cy + basis.forward[2] * d,
  ];

  return {
    position: at(eyeDepth),
    target: at(lo[2] + depth / 2),
    left: -width / 2,
    right: width / 2,
    top: height / 2,
    bottom: -height / 2,
    near: Math.max(0.5, backoff - pad),
    far: backoff + depth + pad,
    width,
    height,
    depth,
    texel,
  };
}

// ------------------------------------------------------------------------------------------------
// Lamps
// ------------------------------------------------------------------------------------------------

/**
 * Indices of the lamps that get a real light: the `budget` highest priorities, brighter first among
 * equals, earlier first after that (so the choice never depends on sort stability).
 */
export function pickRealLights(lamps, budget) {
  const n = Math.max(0, Math.min(lamps.length, Math.floor(budget) || 0));
  if (n === 0) return [];
  const order = lamps.map((lamp, index) => ({ index, priority: Number(lamp.priority) || 0, intensity: Number(lamp.intensity) || 0 }));
  order.sort((a, b) => b.priority - a.priority || b.intensity - a.intensity || a.index - b.index);
  return order.slice(0, n).map((o) => o.index);
}

/**
 * How strongly a lamp claims one of the few real lights: its priority (the level's call) weighed against
 * its distance from the point of interest. At `reach` metres the claim has halved.
 */
export function lampClaim(priority, distance, reach) {
  const d = distance / reach;
  return (priority + 1) / (1 + d * d);
}

/** Spacing of a row of positions: the median gap (one missing member does not double it). */
export function rowStep(positions, fallbackStep = 10) {
  const xs = positions.filter(Number.isFinite).sort((a, b) => a - b);
  const gaps = [];
  for (let i = 1; i < xs.length; i++) if (xs[i] - xs[i - 1] > 0.5) gaps.push(xs[i] - xs[i - 1]);
  gaps.sort((a, b) => a - b);
  const step = gaps.length ? gaps[gaps.length >> 1] : fallbackStep;
  return step > 0.5 ? step : fallbackStep;
}

/**
 * Carries an evenly spaced row on past [min, max]: given the positions already there (any order), returns
 * the positions that continue the row out to `reach` metres beyond both ends. Rows with fewer than two
 * members use `fallbackStep`, anchored on the one member (or on `min`).
 * @returns {number[]} ascending
 */
export function continueRow(existing, min, max, reach, fallbackStep = 10) {
  const xs = existing.filter(Number.isFinite).sort((a, b) => a - b);
  const step = rowStep(xs, fallbackStep);
  const anchor = xs.length ? xs[0] : min;
  const out = [];
  const first = Math.floor((min - reach - anchor) / step);
  const last = Math.ceil((max + reach - anchor) / step);
  for (let i = first; i <= last; i++) {
    const x = anchor + i * step;
    if (x < min - reach || x > max + reach) continue;
    if (x >= min && x <= max) continue; // the level's own stretch: what hangs there is its business
    out.push(x);
  }
  return out;
}

// ------------------------------------------------------------------------------------------------
// The train
// ------------------------------------------------------------------------------------------------

/**
 * One pass of a train of `length` metres along x at `speed`, heading `dir` (+1 east, −1 west), appearing
 * `runUp` metres outside [minX, maxX] and vanishing the same distance past the other side.
 * Times are seconds since the train appeared; `head(t)` is the x of its nose.
 *
 *   approach   0 … tOver        the nose is still outside the block
 *   over       tOver … tGone    some of the train is above the block
 *   gone       tGone … tEnd     the tail has left; the train runs out into the haze
 */
export function trainTimeline({ minX, maxX, dir = 1, speed = 16, length = 80, runUp = 140 }) {
  const sign = dir < 0 ? -1 : 1;
  const start = sign > 0 ? minX - runUp : maxX + runUp;
  const span = maxX - minX;
  const tOver = runUp / speed;
  const tGone = (runUp + span + length) / speed;
  const tEnd = (runUp + span + length + runUp) / speed;
  return {
    dir: sign,
    start,
    speed,
    length,
    tOver,
    tGone,
    tEnd,
    approach: tOver,
    over: tGone - tOver,
    gone: tEnd - tGone,
    head: (t) => start + sign * speed * t,
    /** 'approach' | 'over' | 'gone', or null once the pass has ended (or before it began). */
    phase: (t) => (t < 0 || t >= tEnd ? null : t < tOver ? 'approach' : t < tGone ? 'over' : 'gone'),
  };
}

/**
 * Start times of the train passes. The first pass is timed so the train is overhead `firstPass`
 * seconds after boot; after that a train sets off every `every[0]…every[1]` seconds.
 * @param {{next: () => number}} rng
 */
export function createTrainSchedule({ rng, firstPass = 20, every = [40, 70], approach = 9 }) {
  let at = Math.max(1, firstPass - approach);
  let count = 0;
  return {
    /** Time (seconds on the atmosphere clock) at which the next pass begins. */
    get nextAt() {
      return at;
    },
    get count() {
      return count;
    },
    /** Call when a pass begins: books the following one and returns the direction of this one. */
    begin(now) {
      const dir = count % 2 === 0 ? 1 : -1; // eastbound first, then alternating tracks
      count++;
      at = now + every[0] + (every[1] - every[0]) * rng.next();
      return dir;
    },
    /** Moves the next pass (debug / tests). */
    setNext(time) {
      at = time;
    },
  };
}

// ------------------------------------------------------------------------------------------------
// Haze (mirrors the GLSL in src/atmos/fog.js)
// ------------------------------------------------------------------------------------------------

/** FogExp2 transmittance over `distance` metres. */
export const fogTransmittance = (distance, density) => Math.exp(-density * density * distance * distance);

/** Constant k for which the haze outside the bounds leaves 2 % of an object `reach` metres out. */
export const endHazeK = (reach) => (reach > 0 ? Math.sqrt(-Math.log(0.02)) / reach : 0);

/** How far (metres) a point lies outside the bounds grown by `clear`; 0 inside. */
export function distanceOutside(x, z, bounds, clear = 0) {
  const cx = (bounds.minX + bounds.maxX) / 2;
  const cz = (bounds.minZ + bounds.maxZ) / 2;
  const dx = Math.max(Math.abs(x - cx) - (bounds.maxX - bounds.minX) / 2 - clear, 0);
  const dz = Math.max(Math.abs(z - cz) - (bounds.maxZ - bounds.minZ) / 2 - clear, 0);
  return Math.hypot(dx, dz);
}

/** Transmittance of the extra haze that sits outside the block (1 inside the bounds). */
export function hazeOutside(x, z, bounds, k, clear = 0) {
  const d = distanceOutside(x, z, bounds, clear) * k;
  return Math.exp(-d * d);
}

// ------------------------------------------------------------------------------------------------
// The city beyond the bounds
// ------------------------------------------------------------------------------------------------

const FLOOR_H = 3.1;
const GROUND_FLOOR_H = 4.1;
const BAY_W = 3.2;

/**
 * Footprints of the buildings around the block, as rows of terraced houses and walk-ups along streets
 * that continue the block's own grid:
 *
 *   - the avenue runs on east and west past the bounds, lined on both sides, with a cross street right
 *     outside each end of the block and another one further out;
 *   - behind the block's north and south edges, across an alley, stand the backs of the next row, and
 *     beyond the following avenue a taller row for the roof line;
 *   - across both cross streets stand the fronts of the neighbouring blocks.
 *
 * Nothing is placed inside the bounds grown by `clearance`, nor on the avenue or the cross streets.
 * `core` buildings are the ones every quality preset draws.
 *
 * @returns {Array<{x0, x1, z0, z1, h, floors, bays, tone, face, core, tower}>}
 *          face: the side that looks at the block ('+z' | '-z' | '+x' | '-x'); tower: wants a water tower
 */
export function planCity(rng, bounds, { avenueZ = 0, avenueHalf = 11.5, reach = 130, clearance = 3 } = {}) {
  const out = [];
  const crossHalf = 7; // half width of a cross street
  const eastStreet = bounds.maxX + clearance + crossHalf; // centre lines
  const westStreet = bounds.minX - clearance - crossHalf;
  const farEast = eastStreet + 78;
  const farWest = westStreet - 78;
  const streetsX = [westStreet, eastStreet, farEast, farWest];

  const blocked = (x0, x1) => streetsX.some((s) => x1 > s - crossHalf && x0 < s + crossHalf);

  /** A terrace along x between xa and xb whose depth runs from z0 to z1. */
  function rowX(xa, xb, z0, z1, face, { minH, maxH, core, towers = 0.16 }) {
    let x = xa;
    while (x < xb - 6) {
      const bays = rng.int(3, 6);
      const w = Math.min(bays * BAY_W, xb - x);
      if (w < 7) break;
      if (!blocked(x, x + w)) {
        const floors = Math.max(2, Math.round((rng.range(minH, maxH) - GROUND_FLOOR_H) / FLOOR_H) + 1);
        out.push({
          x0: x, x1: x + w, z0, z1,
          h: GROUND_FLOOR_H + (floors - 1) * FLOOR_H + rng.range(0.6, 1.4), // parapet
          floors, bays: Math.max(2, Math.round(w / BAY_W)),
          tone: rng.int(0, 3), face, core, tower: rng.chance(towers),
        });
      }
      x += w + (rng.chance(0.12) ? rng.range(1.5, 4) : 0); // the odd gap between houses
    }
  }

  /** A terrace along z between za and zb whose depth runs from x0 to x1. */
  function rowZ(za, zb, x0, x1, face, { minH, maxH, core, towers = 0.16 }) {
    let z = za;
    while (z < zb - 6) {
      const bays = rng.int(3, 6);
      const w = Math.min(bays * BAY_W, zb - z);
      if (w < 7) break;
      const floors = Math.max(2, Math.round((rng.range(minH, maxH) - GROUND_FLOOR_H) / FLOOR_H) + 1);
      out.push({
        x0, x1, z0: z, z1: z + w,
        h: GROUND_FLOOR_H + (floors - 1) * FLOOR_H + rng.range(0.6, 1.4),
        floors, bays: Math.max(2, Math.round(w / BAY_W)),
        tone: rng.int(0, 3), face, core, tower: rng.chance(towers),
      });
      z += w + (rng.chance(0.12) ? rng.range(1.5, 4) : 0);
    }
  }

  const north = avenueZ - avenueHalf; // building lines along the avenue
  const south = avenueZ + avenueHalf;
  const depth = () => rng.range(14, 19);

  // The avenue beyond both ends of the block.
  for (const [xa, xb] of [[bounds.maxX + clearance, bounds.maxX + reach], [bounds.minX - reach, bounds.minX - clearance]]) {
    rowX(xa, xb, north - depth(), north, '+z', { minH: 10, maxH: 20, core: true });
    rowX(xa, xb, south, south + depth(), '-z', { minH: 10, maxH: 20, core: true });
  }

  // Behind the block: backs of the next row across an alley, then a taller row across the next avenue.
  const alley = 4;
  const backN = bounds.minZ - clearance - alley;
  const backS = bounds.maxZ + clearance + alley;
  rowX(bounds.minX - 2, bounds.maxX + 2, backN - depth(), backN, '+z', { minH: 11, maxH: 20, core: true, towers: 0.3 });
  rowX(bounds.minX - 2, bounds.maxX + 2, backS, backS + depth(), '-z', { minH: 11, maxH: 20, core: true, towers: 0.3 });
  rowX(bounds.minX - 60, bounds.maxX + 60, backN - 58, backN - 40, '+z', { minH: 17, maxH: 30, core: false, towers: 0.4 });
  rowX(bounds.minX - 60, bounds.maxX + 60, backS + 40, backS + 58, '-z', { minH: 17, maxH: 30, core: false, towers: 0.4 });

  // Across the two cross streets: the fronts of the neighbouring blocks, north and south of the avenue.
  const eastFront = eastStreet + crossHalf;
  const westFront = westStreet - crossHalf;
  for (const [za, zb] of [[backN - 22, north - 19], [south + 19, backS + 22]]) {
    rowZ(za, zb, eastFront, eastFront + depth(), '-x', { minH: 10, maxH: 22, core: true, towers: 0.25 });
    rowZ(za, zb, westFront - depth(), westFront, '+x', { minH: 10, maxH: 22, core: true, towers: 0.25 });
  }

  // Drop anything that pokes into the keep-out areas (defensive: the rows above are laid out clear of them).
  const keepOut = {
    minX: bounds.minX - clearance, maxX: bounds.maxX + clearance,
    minZ: bounds.minZ - clearance, maxZ: bounds.maxZ + clearance,
  };
  return out.filter((b) => {
    const inBounds = b.x1 > keepOut.minX && b.x0 < keepOut.maxX && b.z1 > keepOut.minZ && b.z0 < keepOut.maxZ;
    const onAvenue = b.z1 > north + 0.01 && b.z0 < south - 0.01;
    return !inBounds && !onAvenue;
  });
}

/**
 * Roof line of a skyline card: `columns` heights in 0…1 across the card, as blocks of equal height
 * (buildings) with the odd tower. `tall` (0…1) lifts a centred cluster: the far downtown.
 * @returns {{heights: Float32Array, towers: Array<{at: number, top: number}>}}  towers: where aviation lights go
 */
export function skylineProfile(rng, columns, { base = 0.22, variance = 0.3, towerChance = 0.08, tall = 0 } = {}) {
  const heights = new Float32Array(columns);
  const towers = [];
  let i = 0;
  while (i < columns) {
    const w = Math.max(1, Math.round(columns * rng.range(0.012, 0.045)));
    const u = (i + w / 2) / columns;
    const cluster = tall * Math.exp(-(((u - 0.5) / 0.16) ** 2)); // bump in the middle of the card
    let h = base + variance * rng.next() * rng.next() + cluster * rng.range(0.25, 0.6);
    const isTower = rng.chance(towerChance + cluster * 0.2);
    if (isTower) h += rng.range(0.18, 0.4);
    h = Math.min(0.97, h);
    for (let k = 0; k < w && i + k < columns; k++) heights[i + k] = h;
    if (isTower) towers.push({ at: u, top: h });
    i += w + (rng.chance(0.3) ? 1 : 0); // street gaps stay at 0 until filled below
  }
  // Gaps between buildings: low filler so the card has no holes down to the ground.
  for (let k = 0; k < columns; k++) if (heights[k] === 0) heights[k] = base * 0.6;
  return { heights, towers };
}

// ------------------------------------------------------------------------------------------------
// Interior
// ------------------------------------------------------------------------------------------------

/**
 * The interior amount the atmosphere should move toward: a value passed to setInterior() wins while it
 * is fresh (`age` seconds old, at most `hold`), otherwise the camera position decides.
 */
export function interiorTarget(explicit, age, polled, hold = 0.25) {
  const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
  if (explicit !== null && explicit !== undefined && age <= hold) return clamp01(Number(explicit) || 0);
  return clamp01(Number(polled) || 0);
}
