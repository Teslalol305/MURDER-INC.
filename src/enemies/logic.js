// Enemy rules that need no scene and no game object: attack tokens, perception, the accuracy ramp,
// fire-position scoring, hit-volume ray tests, bolt sweeps and flight planning around the El.
// Everything here is plain arithmetic on numbers and small records, and is unit tested
// (test/enemies-logic.test.js). Metres, seconds, radians; yaw 0 faces −Z and grows counter-clockwise.

const TAU = Math.PI * 2;

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);

/** Shortest signed rotation from `from` to `to`, in (−π, π]. */
function angleDelta(from, to) {
  let d = (to - from + Math.PI) % TAU;
  if (d <= 0) d += TAU;
  return d - Math.PI;
}

/* ------------------------------------------------------------------------------------- tokens */

/**
 * Attack tokens: one global counter that limits how many enemies may run a ranged attack at once.
 * A token is asked for when a telegraph starts and handed back when the burst ends or is cancelled.
 *
 *   - at most `ai.tokens` out at a time (`ai.tokensCrowd` while more than `ai.crowdAbove` enemies live)
 *   - at least `ai.tokenGap` seconds between two grants
 *   - fairness: a type that got the previous token is refused while the other type has been asking
 *     (refused within `refusedWithin` seconds), until `gapFactor` gaps have passed. Goons and Buzzards
 *     therefore alternate whenever both want to fire.
 */
export function createTokens() {
  const refusedAt = { goon: -Infinity, buzzard: -Infinity };
  const state = { held: 0, lastGrantAt: -Infinity, lastGrantType: '' };

  return {
    get held() {
      return state.held;
    },
    get lastGrantType() {
      return state.lastGrantType;
    },
    limit: (alive, ai) => (alive > ai.crowdAbove ? ai.tokensCrowd : ai.tokens),
    /** True when `type` ('goon' | 'buzzard') gets a token at time `now` with `alive` enemies living. */
    request(type, now, alive, ai) {
      const sinceGrant = now - state.lastGrantAt;
      let ok = state.held < (alive > ai.crowdAbove ? ai.tokensCrowd : ai.tokens) && sinceGrant >= ai.tokenGap;
      if (ok && state.lastGrantType === type) {
        const other = type === 'goon' ? 'buzzard' : 'goon';
        const fair = ai.tokenFairness;
        if (now - refusedAt[other] <= fair.refusedWithin && sinceGrant < fair.gapFactor * ai.tokenGap) ok = false;
      }
      if (!ok) {
        refusedAt[type] = now;
        return false;
      }
      state.held++;
      state.lastGrantAt = now;
      state.lastGrantType = type;
      return true;
    },
    release() {
      if (state.held > 0) state.held--;
    },
    reset() {
      state.held = 0;
      state.lastGrantAt = -Infinity;
      state.lastGrantType = '';
      refusedAt.goon = refusedAt.buzzard = -Infinity;
    },
  };
}

/* --------------------------------------------------------------------------------- perception */

/** Is the bearing (dx, dz) inside a horizontal field of view of `fov` radians (total) centred on `yaw`? */
export function inFov(yaw, dx, dz, fov) {
  const len = Math.hypot(dx, dz);
  if (len < 1e-6) return true;
  return (-Math.sin(yaw) * dx - Math.cos(yaw) * dz) / len >= Math.cos(fov * 0.5);
}

/**
 * Could a unit notice a target `dist` metres away in direction (dx, dz)? Range and cone only; the world
 * ray is the caller's business. The cone is ignored once engaged and at point-blank range.
 */
export function inSight(dist, dx, dz, yaw, engaged, ai) {
  if (!(dist < ai.sightRange)) return false;
  if (engaged || dist <= ai.closeRange) return true;
  return inFov(yaw, dx, dz, ai.fov);
}

/** The "seen" accumulator: grows with every tick in view, drains slowly out of view (peeks add up). */
export const seenStep = (seen, visible, tick, ai) => (visible ? seen + tick : Math.max(0, seen - ai.seenDecay * tick));

/** Seconds of sight a unit needs before it engages: shorter once it is already suspicious. */
export const reactionTime = (base, mode, ai) => (mode === 'patrol' ? base : base * ai.investigateReaction);

/** Exposure 0…1: rises while the unit holds line of sight, falls quickly without. */
export const exposureStep = (exposure, sees, dt, ai) => clamp01(exposure + (sees ? ai.exposureUp : -ai.exposureDown) * dt);

/**
 * Aim spread (radians, per axis): loose at exposure 0, tight at 1, opened up by the target's speed.
 * `extra` multiplies the result (a damaged Buzzard shoots worse).
 */
export const aimSpread = (far, near, exposure, targetSpeed, perSpeed, extra = 1) =>
  (far + (near - far) * clamp01(exposure)) * (1 + targetSpeed * perSpeed) * extra;

/* -------------------------------------------------------------------------- Goon fire positions */

const SAME_BEARING = (30 * Math.PI) / 180;
const CROWD_RADIUS = 3;

/**
 * Cost of a Goon standing at candidate `c` to shoot at the player. Lowest cost wins.
 *
 * @param {{x:number, z:number, kind:'authored'|'random'|'arc', sight:boolean, cover:boolean}} c
 * @param {{x:number, z:number}} self      where the Goon is now
 * @param {{x:number, z:number}} player
 * @param {Array<{x:number, z:number, destX:number, destZ:number}>} others   the other engaged Goons
 * @param {number} count                   how many entries of `others` are in use
 * @param {number} jitter                  uniform 0…1
 * @param {object} K                       config/enemies.js `goon.positionCost`
 */
export function firePositionCost(c, self, player, others, count, jitter, K) {
  let cost = K.travel * Math.hypot(c.x - self.x, c.z - self.z) + K[c.kind] + K.jitter * jitter;
  const bearing = Math.atan2(c.x - player.x, c.z - player.z);
  for (let i = 0; i < count; i++) {
    const o = others[i];
    // Spread out around the player: no two Goons on the same line of fire…
    const off = Math.abs(angleDelta(bearing, Math.atan2(o.destX - player.x, o.destZ - player.z)));
    if (off < SAME_BEARING) cost += K.sameBearing * (1 - off / SAME_BEARING);
    // …and never shoulder to shoulder.
    if (Math.hypot(c.x - o.x, c.z - o.z) < CROWD_RADIUS || Math.hypot(c.x - o.destX, c.z - o.destZ) < CROWD_RADIUS) cost += K.crowded;
  }
  if (!c.sight) cost += K.noSight;
  else if (c.cover) cost += K.cover;
  return cost;
}

/** Is a spot `dist` metres from the player inside the band a Goon fights from? */
export const inFireBand = (dist, goon) => dist >= goon.rangeMin && dist <= goon.rangeMax;

/**
 * Speed along a path: stop and turn when badly off heading, slow for corners and ease in on arrival.
 * @param cap       speed limit of the current gait
 * @param error     |heading error| in radians
 * @param remaining metres left to the goal
 */
export function followSpeed(cap, error, remaining, goon) {
  if (error > goon.turnInPlace) return 0;
  return Math.min(cap * (1 - 0.5 * error), 0.4 + 2.6 * remaining);
}

/* ------------------------------------------------------------------------------- hit volumes */

/** Entry distance of a unit ray into a sphere; 0 when it starts inside; Infinity on a miss. */
export function raySphere(ox, oy, oz, dx, dy, dz, cx, cy, cz, radius) {
  const px = ox - cx;
  const py = oy - cy;
  const pz = oz - cz;
  const c = px * px + py * py + pz * pz - radius * radius;
  if (c <= 0) return 0;
  const b = px * dx + py * dy + pz * dz;
  if (b > 0) return Infinity;
  const disc = b * b - c;
  return disc < 0 ? Infinity : -b - Math.sqrt(disc);
}

/**
 * Entry distance of a unit ray into a capsule (segment a → b, radius r); 0 when it starts inside;
 * Infinity on a miss.
 */
export function rayCapsule(ox, oy, oz, dx, dy, dz, ax, ay, az, bx, by, bz, radius) {
  const bax = bx - ax;
  const bay = by - ay;
  const baz = bz - az;
  const oax = ox - ax;
  const oay = oy - ay;
  const oaz = oz - az;
  const baba = bax * bax + bay * bay + baz * baz;
  const bard = bax * dx + bay * dy + baz * dz;
  const baoa = bax * oax + bay * oay + baz * oaz;
  const rdoa = dx * oax + dy * oay + dz * oaz;
  const oaoa = oax * oax + oay * oay + oaz * oaz;
  const r2 = radius * radius;
  if (baba < 1e-10) return raySphere(ox, oy, oz, dx, dy, dz, ax, ay, az, radius);

  // Starting inside (nearest point of the axis closer than the radius) counts as a hit at zero.
  const s = clamp01(baoa / baba);
  if (oaoa - 2 * s * baoa + s * s * baba <= r2) return 0;

  const a = baba - bard * bard;
  const b = baba * rdoa - baoa * bard;
  const c = baba * oaoa - baoa * baoa - r2 * baba;
  if (a > 1e-10) {
    const h = b * b - a * c;
    if (h < 0) return Infinity;
    const t = (-b - Math.sqrt(h)) / a;
    const y = baoa + t * bard;
    if (y > 0 && y < baba) return t >= 0 ? t : Infinity; // the cylinder wall
    // One of the end caps: the one on the side the ray came in from.
    return y <= 0
      ? raySphere(ox, oy, oz, dx, dy, dz, ax, ay, az, radius)
      : raySphere(ox, oy, oz, dx, dy, dz, bx, by, bz, radius);
  }
  // Ray parallel to the axis: only the caps can be hit.
  return Math.min(raySphere(ox, oy, oz, dx, dy, dz, ax, ay, az, radius), raySphere(ox, oy, oz, dx, dy, dz, bx, by, bz, radius));
}

/**
 * Entry distance of a unit ray into an ellipsoid of revolution about Y (horizontal radius `radius`,
 * vertical half height `half`); 0 when it starts inside; Infinity on a miss.
 */
export function rayEllipsoid(ox, oy, oz, dx, dy, dz, cx, cy, cz, radius, half) {
  // Stretch Y so the ellipsoid becomes a sphere; the ray parameter is unchanged by the stretch.
  const k = radius / half;
  const px = ox - cx;
  const py = (oy - cy) * k;
  const pz = oz - cz;
  const ey = dy * k;
  const c = px * px + py * py + pz * pz - radius * radius;
  if (c <= 0) return 0;
  const a = dx * dx + ey * ey + dz * dz;
  const b = px * dx + py * ey + pz * dz;
  if (b > 0) return Infinity;
  const disc = b * b - a * c;
  return disc < 0 ? Infinity : (-b - Math.sqrt(disc)) / a;
}

/* ------------------------------------------------------------------------------------- bolts */

/**
 * Does the segment p → q pass within `radius` of the upright segment (cx, y0…y1, cz)? Returns the
 * parameter 0…1 along p → q of the closest approach, or -1 when it stays outside. This is the swept test of
 * a bolt against the player's body capsule.
 */
export function segmentHitsUpright(px, py, pz, qx, qy, qz, cx, y0, y1, cz, radius) {
  // Closest points of two segments (Ericson, Real-Time Collision Detection 5.1.9), second one vertical.
  const d1x = qx - px;
  const d1y = qy - py;
  const d1z = qz - pz;
  const d2y = y1 - y0;
  const rx = px - cx;
  const ry = py - y0;
  const rz = pz - cz;
  const a = d1x * d1x + d1y * d1y + d1z * d1z;
  const e = d2y * d2y;
  const f = d2y * ry;
  let s;
  let t;
  if (a <= 1e-12) {
    s = 0;
    t = e > 1e-12 ? clamp01(f / e) : 0;
  } else {
    const c = d1x * rx + d1y * ry + d1z * rz;
    if (e <= 1e-12) {
      t = 0;
      s = clamp01(-c / a);
    } else {
      const b = d1y * d2y;
      const denom = a * e - b * b;
      s = denom > 1e-12 ? clamp01((b * f - c * e) / denom) : 0;
      t = (b * s + f) / e;
      if (t < 0) {
        t = 0;
        s = clamp01(-c / a);
      } else if (t > 1) {
        t = 1;
        s = clamp01((b - c) / a);
      }
    }
  }
  const x = rx + d1x * s;
  const y = ry + d1y * s - d2y * t;
  const z = rz + d1z * s;
  return x * x + y * y + z * z <= radius * radius ? s : -1;
}

/**
 * Where to aim a slow bolt: the target's position plus a share (`lead`, 0…1) of the distance it will
 * cover while the bolt is in flight. Writes [x, y, z] to `out`.
 */
export function leadPoint(sx, sy, sz, tx, ty, tz, vx, vy, vz, speed, lead, out) {
  const flight = Math.hypot(tx - sx, ty - sy, tz - sz) / speed;
  out[0] = tx + vx * flight * lead;
  out[1] = ty + vy * flight * lead;
  out[2] = tz + vz * flight * lead;
  return out;
}

/* ----------------------------------------------------------------------------- flight planning */

/** Parameter 0…1 at which the 2D segment a → b first touches the rectangle; 0 if a is inside; -1 if never. */
export function segmentEntersRect(ax, az, bx, bz, minX, maxX, minZ, maxZ) {
  SEG[0] = ax;
  SEG[1] = az;
  SEG[2] = bx;
  SEG[3] = bz;
  SEG[4] = minX;
  SEG[5] = maxX;
  SEG[6] = minZ;
  SEG[7] = maxZ;
  segmentEntersRectA();
  return SEG[8];
}

// segmentEntersRectA reads (ax, az, bx, bz, minX, maxX, minZ, maxZ) from SEG[0…7] and leaves the
// answer in SEG[8]: the flight code calls it every step, and doubles passed to a call are garbage.
const SEG = new Float64Array(9);
function segmentEntersRectA() {
  SEG[8] = -1;
  const ax = SEG[0];
  const az = SEG[1];
  const bx = SEG[2];
  const bz = SEG[3];
  const minX = SEG[4];
  const maxX = SEG[5];
  const minZ = SEG[6];
  const maxZ = SEG[7];
  let t0 = 0;
  let t1 = 1;
  const dx = bx - ax;
  const dz = bz - az;
  if (Math.abs(dx) < 1e-9) {
    if (ax < minX || ax > maxX) return;
  } else {
    let u0 = (minX - ax) / dx;
    let u1 = (maxX - ax) / dx;
    if (u0 > u1) {
      const s = u0;
      u0 = u1;
      u1 = s;
    }
    if (u0 > t0) t0 = u0;
    if (u1 < t1) t1 = u1;
    if (t0 > t1) return;
  }
  if (Math.abs(dz) < 1e-9) {
    if (az < minZ || az > maxZ) return;
  } else {
    let u0 = (minZ - az) / dz;
    let u1 = (maxZ - az) / dz;
    if (u0 > u1) {
      const s = u0;
      u0 = u1;
      u1 = s;
    }
    if (u0 > t0) t0 = u0;
    if (u1 < t1) t1 = u1;
    if (t0 > t1) return;
  }
  SEG[8] = t0;
}

/**
 * Flight planning around the El. The track deck is a long slab over the avenue: a drone may pass under
 * it or beside it, or stay above it, but never through it. Given the drone at (px, py, pz) and the point
 * it wants (`out` = [x, y, z]), rewrites `out` so that steering straight at it is safe:
 *
 *   under the deck         stay below it until clear of its footprint
 *   over the deck          leave sideways, at height, before descending
 *   outside, path crosses  drop below the deck first (hold outside until low enough), then go under
 *
 * @param {{y:number, minX:number, maxX:number, minZ:number, maxZ:number}} el   level.el (y = underside)
 * @param {{under:number, over:number, margin:number, thickness:number, hold:number}} K   config `buzzard.deck`
 * @returns {number} 0 untouched, 1 capped under, 2 leaving over the top, 3 holding outside to descend
 */
export function planAroundDeck(px, py, pz, out, el, K) {
  return planAroundDeckAt({ x: px, y: py, z: pz }, out, el, K);
}

/** planAroundDeck for the drone at `pos` ({x, y, z}): the form the flight code calls (no numbers passed). */
export function planAroundDeckAt(pos, out, el, K) {
  if (!el) return 0;
  const px = pos.x;
  const py = pos.y;
  const pz = pos.z;
  const m = K.margin;
  const minX = el.minX - m;
  const maxX = el.maxX + m;
  const minZ = el.minZ - m;
  const maxZ = el.maxZ + m;
  const lowCap = el.y - K.under;
  const highFloor = el.y + K.thickness + K.over;
  const selfIn = px >= minX && px <= maxX && pz >= minZ && pz <= maxZ;

  if (selfIn) {
    if (py > el.y) {
      // Over the deck. Fine while the wanted point is up here too; otherwise get clear of it sideways.
      if (out[1] >= highFloor) return 0;
      const mid = (el.minZ + el.maxZ) * 0.5;
      const wantsOut = out[2] < minZ || out[2] > maxZ;
      const toMax = wantsOut ? out[2] > mid : pz > mid;
      out[2] = toMax ? maxZ + K.hold + 1 : minZ - K.hold - 1;
      out[1] = Math.max(py, highFloor);
      return 2;
    }
    if (out[1] > lowCap) out[1] = lowCap;
    return 1;
  }

  SEG[0] = px;
  SEG[1] = pz;
  SEG[2] = out[0];
  SEG[3] = out[2];
  SEG[4] = minX;
  SEG[5] = maxX;
  SEG[6] = minZ;
  SEG[7] = maxZ;
  segmentEntersRectA();
  const enter = SEG[8];
  if (enter < 0) return 0;
  // Crossing above is fine when both ends of the leg are high enough.
  if (out[1] >= highFloor && py >= highFloor - 0.5) return 0;
  if (out[1] > lowCap) out[1] = lowCap;
  if (py <= lowCap + 0.6) return 1;
  // Still too high to go in: wait just outside the footprint while descending.
  const len = Math.hypot(out[0] - px, out[2] - pz);
  const stop = Math.max(0, enter * len - K.hold);
  const k = len > 1e-6 ? stop / len : 0;
  out[0] = px + (out[0] - px) * k;
  out[2] = pz + (out[2] - pz) * k;
  return 3;
}

/* --------------------------------------------------------------------- flight over and out of things */

/**
 * What a Buzzard's airframe must stay out of: everything that blocks movement, except the invisible
 * walls and see-through mesh that exist only to stop the player (the block seals, the Cage fence, which
 * is 8 m of collider over a 3 m fence, railings). The hoist tower's netting at the end of the scaffold and
 * the mezzanine office's glass count as solid: a drone flying through either would show.
 */
export const droneSolid = (q) => !q.bulletOnly && (!q.playerOnly || q.tag === 'hoist' || q.tag === 'office-glass');

const POLE = 1; // narrower than this both ways is a pole (a lamp post, a column) to go around, not a wall to go over

/** A lamp post, a column, a sign pole: something a drone goes around, never over (and never perches on). */
export const isPole = (q) => q.max.x - q.min.x < POLE && q.max.z - q.min.z < POLE;

/**
 * The boxes a drone must stay out of (droneSolid), packed for the flight loops, which run for every
 * drone every step: STRIDE numbers a box (min x y z, max x y z, 1 if a pole, 1 if inside the El's
 * footprint, 1 if player-only: solid for a drone, not ground) in `data`, the box objects in `boxes`. `packSolids` fills it from physics.boxes; `solidsStale` says
 * when it must be filled again (the list changed length, or its first or last box is another one: boxes
 * are only ever pushed on the end or spliced out).
 */
const STRIDE = 9;

export function createSolids() {
  return { data: new Float64Array(STRIDE * 256), boxes: [], n: 0, count: -1, first: null, last: null };
}

export const solidsStale = (pack, list) =>
  pack.count !== list.length || pack.first !== (list.length ? list[0] : null) || pack.last !== (list.length ? list[list.length - 1] : null);

/** Fills `pack` from `list` (physics.boxes); `el` (level.el or null) marks what planAroundDeck owns. */
export function packSolids(pack, list, el) {
  pack.count = list.length;
  pack.first = list.length ? list[0] : null;
  pack.last = list.length ? list[list.length - 1] : null;
  pack.boxes.length = 0;
  let n = 0;
  for (let i = 0; i < list.length; i++) {
    const q = list[i];
    if (!droneSolid(q)) continue;
    if (STRIDE * (n + 1) > pack.data.length) {
      const grown = new Float64Array(pack.data.length * 2);
      grown.set(pack.data);
      pack.data = grown;
    }
    const d = pack.data;
    const o = STRIDE * n;
    d[o] = q.min.x;
    d[o + 1] = q.min.y;
    d[o + 2] = q.min.z;
    d[o + 3] = q.max.x;
    d[o + 4] = q.max.y;
    d[o + 5] = q.max.z;
    d[o + 6] = isPole(q) ? 1 : 0;
    const cx = (q.min.x + q.max.x) * 0.5;
    const cz = (q.min.z + q.max.z) * 0.5;
    d[o + 7] = el && cx >= el.minX && cx <= el.maxX && cz >= el.minZ && cz <= el.maxZ ? 1 : 0;
    d[o + 8] = q.playerOnly ? 1 : 0;
    pack.boxes.push(q);
    n++;
  }
  pack.n = n;
  return pack;
}

/**
 * Climbing over what lies ahead (there is no pathing). Looks along the flat leg from `pos` toward the
 * wanted point (`want` = [x, y, z]), at most `K.climbLook` metres of it, with the leg widened by the
 * airframe radius, at every solid box it crosses whose top is not above `K.maxAltitude`:
 *
 *   an obstacle (its top above the airframe's underside)   want[1] ≥ top + `K.minHeight`: climb over it
 *   a floor (the airframe is already above its top)        want[1] ≥ top + `K.floorClearance` + `K.halfHeight`:
 *                                                          stay above it, but free to come down to it
 *
 * Not counted: boxes whose underside is above both the drone and the wanted height (an overhang it
 * passes under: a roof seen from inside, an awning), anything inside the El's footprint (planAroundDeck
 * owns that), and poles (under `POLE` m across both ways: it steers around a lamp or a post, the
 * collision rays handle those). The airframe's own footprint is part of the leg, so it does not sink
 * past a roof edge it is leaving. Returns whether it raised want[1], and leaves the box that decided it
 * and the height in `climbHit` (null and 0 when it did not).
 *
 * @param {ReturnType<typeof createSolids>} pack   packSolids(physics.boxes, level.el)
 * @param {{x:number, y:number, z:number}} pos
 * @param {number[]} want
 * @param {{radius:number, halfHeight:number, minHeight:number, floorClearance:number, maxAltitude:number, climbLook:number}} K
 */
export function climbOver(pack, pos, want, K) {
  const x0 = pos.x;
  const z0 = pos.z;
  let dx = want[0] - x0;
  let dz = want[2] - z0;
  const len = Math.sqrt(dx * dx + dz * dz);
  if (len > K.climbLook) {
    const s = K.climbLook / len;
    dx *= s;
    dz *= s;
  }
  const r = K.radius;
  const above = (pos.y > want[1] ? pos.y : want[1]) + K.halfHeight + 0.3;
  const bottom = pos.y - K.halfHeight;
  const overFloor = K.floorClearance + K.halfHeight;
  const minHeight = K.minHeight;
  const maxAltitude = K.maxAltitude;
  const d = pack.data;
  let best = want[1];
  let raised = 0;
  let hitAt = -1;
  for (let i = 0, o = 0; i < pack.n; i++, o += STRIDE) {
    const top = d[o + 4];
    const need = top + (top > bottom ? minHeight : overFloor);
    if (need <= best || top > maxAltitude || d[o + 1] > above || d[o + 6] !== 0 || d[o + 7] !== 0) continue;
    const minX = d[o] - r;
    const maxX = d[o + 3] + r;
    const minZ = d[o + 2] - r;
    const maxZ = d[o + 5] + r;
    let t0 = 0;
    let t1 = 1;
    if (Math.abs(dx) < 1e-9) {
      if (x0 < minX || x0 > maxX) continue;
    } else {
      let u0 = (minX - x0) / dx;
      let u1 = (maxX - x0) / dx;
      if (u0 > u1) {
        const s = u0;
        u0 = u1;
        u1 = s;
      }
      if (u0 > t0) t0 = u0;
      if (u1 < t1) t1 = u1;
      if (t0 > t1) continue;
    }
    if (Math.abs(dz) < 1e-9) {
      if (z0 < minZ || z0 > maxZ) continue;
    } else {
      let u0 = (minZ - z0) / dz;
      let u1 = (maxZ - z0) / dz;
      if (u0 > u1) {
        const s = u0;
        u0 = u1;
        u1 = s;
      }
      if (u0 > t0) t0 = u0;
      if (u1 < t1) t1 = u1;
      if (t0 > t1) continue;
    }
    best = need;
    raised = need;
    hitAt = i;
  }
  climbHit.box = hitAt >= 0 ? pack.boxes[hitAt] : null;
  climbHit.height = raised;
  want[1] = best;
  return hitAt >= 0;
}

/** What the last climbOver call found: the box that set the height (null if none) and that height (0). */
export const climbHit = { box: null, height: 0.5 };

/**
 * The ground under a drone at `pos`: the highest top of a solid box (not a player-only one) that holds
 * (pos.x, pos.z) and is not above pos.y + lift, or 0. The same answer as physics.groundHeight for those
 * boxes, read from the pack (and left in `groundHit.y`, so no number crosses the call).
 */
export function groundUnder(pack, pos, lift) {
  const x = pos.x;
  const z = pos.z;
  const maxY = pos.y + lift;
  const d = pack.data;
  let h = 0;
  for (let i = 0, o = 0; i < pack.n; i++, o += STRIDE) {
    if (d[o + 8] !== 0) continue;
    const top = d[o + 4];
    if (top <= h || top > maxY) continue;
    if (x < d[o] || x > d[o + 3] || z < d[o + 2] || z > d[o + 5]) continue;
    h = top;
  }
  groundHit.y = h;
}

export const groundHit = { y: 0.5 };

const OUT_EPS = 0.02;

/**
 * Puts an airframe (an upright cylinder of `K.radius`, `K.halfHeight` either side of `pos.y`) that
 * overlaps something solid back into free air: for each box it overlaps, the shortest way out (up,
 * down, or sideways along x or z) that keeps it inside `bounds` less `K.boundsMargin` and above
 * `K.floorClearance`; off a pole (isPole) always sideways. The velocity component pointing back in is
 * dropped. After three passes only "up" is tried, so a drone wedged between two boxes always comes free.
 * Mutates pos and vel; returns how many pushes it made (0: it was in free air).
 */
export function pushOut(pack, pos, vel, K, bounds) {
  const r = K.radius;
  const hh = K.halfHeight;
  const m = K.boundsMargin;
  const d = pack.data;
  let pushes = 0;
  for (let pass = 0; pass < 8; pass++) {
    const upOnly = pass >= 3;
    let any = false;
    for (let i = 0, o = 0; i < pack.n; i++, o += STRIDE) {
      const px = pos.x;
      const py = pos.y;
      const pz = pos.z;
      if (d[o + 4] <= py - hh || d[o + 1] >= py + hh) continue;
      const cx = px < d[o] ? d[o] : px > d[o + 3] ? d[o + 3] : px;
      const cz = pz < d[o + 2] ? d[o + 2] : pz > d[o + 5] ? d[o + 5] : pz;
      if ((px - cx) * (px - cx) + (pz - cz) * (pz - cz) >= r * r) continue;
      let axis = 1;
      let to = d[o + 4] + hh + OUT_EPS;
      if (!upOnly) {
        // Off a pole sideways, even when up is shorter: a drone sinking onto a lamp post would perch on it.
        const pole = d[o + 6] !== 0;
        let best = pole ? Infinity : to - py;
        const down = d[o + 1] - hh - OUT_EPS;
        if (!pole && py - down < best && down >= K.floorClearance) {
          best = py - down;
          to = down;
        }
        const left = d[o] - r - OUT_EPS;
        if (px - left < best && (!bounds || left >= bounds.minX + m)) {
          best = px - left;
          axis = 0;
          to = left;
        }
        const right = d[o + 3] + r + OUT_EPS;
        if (right - px < best && (!bounds || right <= bounds.maxX - m)) {
          best = right - px;
          axis = 0;
          to = right;
        }
        const back = d[o + 2] - r - OUT_EPS;
        if (pz - back < best && (!bounds || back >= bounds.minZ + m)) {
          best = pz - back;
          axis = 2;
          to = back;
        }
        const front = d[o + 5] + r + OUT_EPS;
        if (front - pz < best && (!bounds || front <= bounds.maxZ - m)) {
          axis = 2;
          to = front;
        }
      }
      // (a pole with no way out sideways inside the bounds leaves axis = 1: up after all)
      if (axis === 0) {
        if (to < px ? vel.x > 0 : vel.x < 0) vel.x = 0;
        pos.x = to;
      } else if (axis === 2) {
        if (to < pz ? vel.z > 0 : vel.z < 0) vel.z = 0;
        pos.z = to;
      } else {
        if (to < py ? vel.y > 0 : vel.y < 0) vel.y = 0;
        pos.y = to;
      }
      any = true;
      pushes++;
    }
    if (!any) break;
  }
  return pushes;
}

/** Does the airframe overlap anything solid for a drone? (the test pushOut resolves) */
export function droneOverlaps(pack, pos, K) {
  const r = K.radius;
  const hh = K.halfHeight;
  const d = pack.data;
  for (let i = 0, o = 0; i < pack.n; i++, o += STRIDE) {
    if (d[o + 4] <= pos.y - hh || d[o + 1] >= pos.y + hh) continue;
    const cx = pos.x < d[o] ? d[o] : pos.x > d[o + 3] ? d[o + 3] : pos.x;
    const cz = pos.z < d[o + 2] ? d[o + 2] : pos.z > d[o + 5] ? d[o + 5] : pos.z;
    if ((pos.x - cx) * (pos.x - cx) + (pos.z - cz) * (pos.z - cz) < r * r) return true;
  }
  return false;
}

/**
 * When planAroundDeck sends a drone under the El (plan 1: low enough, go in; 3: hold outside and come
 * down first) but climbOver finds something tall on the way in or right under the hold, the two would
 * fight for ever. Two ways out, tried in this order by the flight code:
 *
 *   deckEntry   plan 1: go straight across the deck's edge from where it is (the shortest way in,
 *               which usually clears whatever stood on the diagonal), at the plan's height
 *   deckSlide   still blocked, or plan 3: slide `K.slide` metres along the deck's edge, away from the
 *               box in the way (climbHit.box), at the height the climb asked for, until there is room
 *               to come down
 *
 * Both rewrite `want` in place. `el` is level.el, `K` config `buzzard.deck`.
 */
export function deckEntry(pos, want, el, K) {
  want[0] = pos.x < el.minX ? el.minX + 1 : pos.x > el.maxX ? el.maxX - 1 : pos.x;
  want[2] = pos.z < el.minZ ? el.minZ + 1 : pos.z > el.maxZ ? el.maxZ - 1 : pos.z;
  want[1] = el.y - K.under;
}

export function deckSlide(pos, want, box, K) {
  want[0] = pos.x + (pos.x >= (box.min.x + box.max.x) * 0.5 ? K.slide : -K.slide);
  want[2] = pos.z;
}

/* -------------------------------------------------------------------------------- indoors */

const DOOR_LEVEL = 0.35; // routeIndoors: how close to the doorway's height a drone must be to go through

/** Is (p.x, p.z) inside the interior box `b` shrunk by `m` on every side (and, with `checkY`, under its top)? */
export function inRoom(b, p, m, checkY) {
  return p.x > b.min.x + m && p.x < b.max.x - m && p.z > b.min.z + m && p.z < b.max.z - m && (!checkY || p.y < b.max.y);
}

/**
 * Getting into an interior (the shop) without pathing. `room` is {box: {min, max}, list: [{ox, oz, ix, iz,
 * y}]}: its openings, each a point outside the doorway and one inside it, at a height that clears the
 * doorway's top. When the wanted point is inside the box and the drone is not, rewrites `want`: to the
 * outside point of the opening that makes the shortest way, then, once the drone is in the doorway's
 * corridor (between the two points, within 1 m of its centre line, within DOOR_LEVEL of its height),
 * through it to the inside point. Returns 0 untouched, 1 heading for the doorway, 2 going through.
 */
export function routeIndoors(pos, want, room) {
  const box = room.box;
  if (!room.list.length || inRoom(box, pos, 0, true)) return 0;
  if (!(want[0] > box.min.x + 0.2 && want[0] < box.max.x - 0.2 && want[2] > box.min.z + 0.2 && want[2] < box.max.z - 0.2)) return 0;
  let best = null;
  let bestCost = Infinity;
  for (let i = 0; i < room.list.length; i++) {
    const en = room.list[i];
    const cost = Math.hypot(pos.x - en.ox, pos.z - en.oz) + Math.hypot(want[0] - en.ix, want[2] - en.iz);
    if (cost < bestCost) {
      bestCost = cost;
      best = en;
    }
  }
  // Where the drone is along the corridor from the outside point (u = 0) to the inside point (u = 1).
  const cx = best.ix - best.ox;
  const cz = best.iz - best.oz;
  const len2 = cx * cx + cz * cz;
  const u = ((pos.x - best.ox) * cx + (pos.z - best.oz) * cz) / len2;
  const side = Math.abs((pos.x - best.ox) * cz - (pos.z - best.oz) * cx) / Math.sqrt(len2);
  const through = u > -0.25 && u < 1.2 && side < 1 && Math.abs(pos.y - best.y) < DOOR_LEVEL;
  want[0] = through ? best.ix : best.ox;
  want[2] = through ? best.iz : best.oz;
  want[1] = best.y;
  return through ? 2 : 1;
}
