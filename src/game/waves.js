// Who arrives, and in which order. Pure functions over the tables in src/config/flow.js.
//
// Story: a reinforcement wave is `{buzzard, goon}` from the difficulty row; the two types alternate from
// the first slot (a Buzzard leads: it is the one the player sees coming) and whoever is left follows.
// Hold the Block: wave n is mostly Goons with the Buzzards spread evenly through the arrival order.

export const BUZZARD = 'buzzard';
export const GOON = 'goon';

const whole = (n) => Math.max(0, Math.floor(Number(n) || 0));

/**
 * Arrival order of a story reinforcement wave.
 * (2, 5) → buzzard, goon, buzzard, goon, goon, goon, goon
 * @returns {string[]} enemy types, first to arrive first
 */
export function missionOrder(buzzards, goons) {
  let b = whole(buzzards);
  let g = whole(goons);
  const order = [];
  while (b > 0 || g > 0) {
    if (b > 0) {
      order.push(BUZZARD);
      b--;
    }
    if (g > 0) {
      order.push(GOON);
      g--;
    }
  }
  return order;
}

/**
 * Arrival order of a holdout wave: `total` slots of Goons, Buzzard i takes slot
 * min(total − 1, 1 + floor(i × total / buzzards)), or the next free one after it.
 * The counts always come out exact.
 */
export function holdoutOrder(total, buzzards) {
  const n = whole(total);
  const b = Math.min(n, whole(buzzards));
  const order = new Array(n).fill(GOON);
  for (let i = 0; i < b; i++) {
    let slot = Math.min(n - 1, 1 + Math.floor((i * n) / b));
    while (order[slot] === BUZZARD) slot = (slot + 1) % n;
    order[slot] = BUZZARD;
  }
  return order;
}

/**
 * Everything about holdout wave n (1-based), from config/flow.js `holdout`.
 * @returns {{wave, total, buzzards, goons, order: string[], stagger, scale: {hp, damage, cooldown}, extraAlive}}
 */
export function holdoutWave(n, H) {
  const wave = Math.max(1, whole(n));
  const total = H.total(wave);
  const buzzards = Math.min(total, Math.round(total * H.buzzardShare(wave)));
  return {
    wave,
    total,
    buzzards,
    goons: total - buzzards,
    order: holdoutOrder(total, buzzards),
    stagger: H.stagger(wave),
    scale: { hp: H.hpScale(wave), damage: H.damageScale(wave), cooldown: H.cooldownScale(wave) },
    extraAlive: H.extraAlive(wave),
  };
}

/** Points for one kill in holdout wave `wave` (unknown types score like a Buzzard). */
export function killScore(type, wave, S) {
  const base = typeof S[type] === 'number' ? S[type] : S[BUZZARD];
  return Math.round(base * S.killScale(Math.max(1, wave)));
}

/** A pursuit arrival: `roll` is uniform 0…1. */
export const pursuitType = (roll, buzzardShare) => (roll < buzzardShare ? BUZZARD : GOON);
