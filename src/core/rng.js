// Seeded pseudo-random numbers (mulberry32). Everything that affects layout or gameplay draws from
// `G.rng` or a fork of it, so a given `?seed` always produces the same block and the same fight.

/** 32-bit string hash (FNV-1a), used to derive independent labelled streams. */
function hashString(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** Normalises any seed-like value (number, numeric string, text) to an unsigned 32-bit integer. */
export function toSeed(value, fallback = 1994) {
  if (value === undefined || value === null || value === '') return fallback >>> 0;
  const n = Number(value);
  if (Number.isFinite(n)) return Math.floor(n) >>> 0;
  return hashString(String(value));
}

export function createRng(seed = 1994) {
  const seed0 = toSeed(seed);
  let state = seed0;

  /** Uniform float in [0, 1). */
  function next() {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  return {
    seed: seed0,
    next,
    /** Uniform float in [a, b). */
    range: (a, b) => a + (b - a) * next(),
    /** Uniform integer in [a, b], both ends included. */
    int: (a, b) => Math.floor(a + (b - a + 1) * next()),
    /** Random element of a non-empty array (undefined for an empty one). */
    pick: (arr) => arr[Math.floor(next() * arr.length)],
    /** −1 or +1. */
    sign: () => (next() < 0.5 ? -1 : 1),
    /** True with probability p. */
    chance: (p) => next() < p,
    /**
     * Child stream. Without a label the child is seeded from this stream's next value (order dependent).
     * With a label (`rng.fork('enemies')`) it depends only on the root seed and the label, so a module's
     * stream stays the same no matter how many numbers other modules drew before it.
     */
    fork: (label) =>
      createRng(label === undefined ? Math.floor(next() * 4294967296) : hashString(`${seed0}:${label}`)),
  };
}
