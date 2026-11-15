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
  let t0 = 0;
  let t1 = 1;
  const dx = bx - ax;
  const dz = bz - az;
  if (Math.abs(dx) < 1e-9) {
    if (ax < minX || ax > maxX) return -1;
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
    if (t0 > t1) return -1;
  }
  if (Math.abs(dz) < 1e-9) {
    if (az < minZ || az > maxZ) return -1;
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
    if (t0 > t1) return -1;
  }
  return t0;
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
  if (!el) return 0;
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

  const enter = segmentEntersRect(px, pz, out[0], out[2], minX, maxX, minZ, maxZ);
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
