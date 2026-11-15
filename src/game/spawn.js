// Where an enemy appears. Pure functions: the game supplies distances, sightlines and random numbers.
//
// Every authored point of the right kind is scored and the best one wins (config/flow.js `spawn.score`):
//   + uniform 0…random
//   + far (+ up to farExtra over the next farExtraOver metres) when at least `minDistance` from the player,
//     else − (minDistance − distance) / nearDivisor
//   + hidden when the player's eye cannot see the point
//   + recent (negative) when the point was used in the last recentSecs

/** Compass sector 0…7 of the horizontal offset (dx, dz), clockwise from north. North is −Z, east is +X. */
export function compassSector(dx, dz) {
  const sector = Math.round(Math.atan2(dx, -dz) / (Math.PI / 4));
  return ((sector % 8) + 8) % 8;
}

/**
 * Score of one candidate point.
 * @param {{distance: number, hidden: boolean, usedAgo: number, random: number}} c  `random` is uniform 0…1,
 *        `usedAgo` the seconds since the point was last picked (Infinity: never)
 * @param {object} S            config/flow.js `spawn.score`
 * @param {number} minDistance  preferred minimum distance from the player
 */
export function spawnScore(c, S, minDistance) {
  let score = c.random * S.random;
  if (c.distance >= minDistance) {
    const over = Math.min(1, (c.distance - minDistance) / S.farExtraOver);
    score += S.far + S.farExtra * over;
  } else {
    score -= (minDistance - c.distance) / S.nearDivisor;
  }
  if (c.hidden) score += S.hidden;
  if (c.usedAgo < S.recentSecs) score += S.recent;
  return score;
}

/**
 * The best point of kind `wanted` ('ground' | 'air'), or null when the list has none.
 * @param {Array<{pos: {x, y, z}, type: string}>} points
 * @param {object} q
 *   q.x, q.z          the player's position
 *   q.minDistance     preferred minimum distance
 *   q.strict          when true, points nearer than minDistance are only used if nothing else exists
 *   q.hidden(point)   → true when the player cannot see the point
 *   q.usedAgo(point)  → seconds since it was last picked
 *   q.random()        → uniform 0…1
 * @param {object} S   config/flow.js `spawn.score`
 */
export function pickSpawn(points, wanted, q, S) {
  let best = null;
  let bestScore = -Infinity;
  let bestFar = false;
  for (let i = 0; i < points.length; i++) {
    const point = points[i];
    if (point.type !== wanted) continue;
    const distance = Math.hypot(point.pos.x - q.x, point.pos.z - q.z);
    const far = distance >= q.minDistance;
    if (q.strict && bestFar && !far) continue;
    const score = spawnScore({ distance, hidden: q.hidden(point), usedAgo: q.usedAgo(point), random: q.random() }, S, q.minDistance);
    if (score > bestScore || (q.strict && far && !bestFar)) {
      best = point;
      bestScore = score;
      bestFar = far;
    }
  }
  return best;
}
