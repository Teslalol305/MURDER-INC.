// Persisted user settings (`G.settings`) and the best holdout score.
// All storage access is wrapped: a blocked or full localStorage just means nothing is remembered.

export const SETTINGS_KEY = 'murderinc.settings.v1';
export const BEST_KEY = 'murderinc.holdout.best';

export const DEFAULTS = Object.freeze({
  quality: 'auto',
  sens: 1,
  invertY: false,
  volume: 0.8,
  fov: 74,
  difficulty: 'hustler',
  mode: 'mission',
  view: 1,
  time: 'day',
  aimAssist: true, // aiming locks on to the nearest Vulture
  guide: true, // the line on the ground to the next objective
});

const oneOf = (list) => (v) => (list.includes(v) ? v : undefined);
const bool = (v) => (typeof v === 'boolean' ? v : undefined);
const numberIn = (min, max, round = false) => (v) => {
  const n = typeof v === 'string' && v.trim() !== '' ? Number(v) : v;
  if (typeof n !== 'number' || !Number.isFinite(n)) return undefined;
  const c = Math.min(max, Math.max(min, n));
  return round ? Math.round(c) : c;
};

// key → function returning the cleaned value, or undefined when the input cannot be used.
const VALIDATORS = {
  quality: oneOf(['auto', 'low', 'medium', 'high', 'ultra']),
  sens: numberIn(0.2, 3),
  invertY: bool,
  volume: numberIn(0, 1),
  fov: numberIn(60, 95, true),
  difficulty: oneOf(['hustler', 'boss', 'kingpin']),
  mode: oneOf(['mission', 'holdout']),
  view: (v) => oneOf([1, 2, 3])(Number(v)),
  time: oneOf(['day', 'night']),
  aimAssist: bool,
  guide: bool,
};

function safeStorage() {
  try {
    const s = globalThis.localStorage;
    // Touch it once: some browsers hand out the object but throw on use.
    s.getItem(SETTINGS_KEY);
    return s;
  } catch {
    return null;
  }
}

/**
 * @param {{emit: Function}} [events]   bus that receives `settings:change {key, value}`
 * @param {Storage|null} [storage]      defaults to localStorage (tests pass a fake)
 */
export function createSettings(events, storage = safeStorage()) {
  const values = { ...DEFAULTS };

  function read(key) {
    try {
      return storage ? storage.getItem(key) : null;
    } catch {
      return null;
    }
  }

  function write(key, text) {
    try {
      if (storage) storage.setItem(key, text);
    } catch {
      /* private mode, quota: carry on without persistence */
    }
  }

  // Load: keep only known keys whose values survive validation.
  try {
    const saved = JSON.parse(read(SETTINGS_KEY) || 'null');
    if (saved && typeof saved === 'object') {
      for (const key of Object.keys(DEFAULTS)) {
        const clean = VALIDATORS[key](saved[key]);
        if (clean !== undefined) values[key] = clean;
      }
    }
  } catch {
    /* corrupt JSON: defaults stand */
  }

  function get(key) {
    return values[key];
  }

  /** Validates, stores and announces a setting. Returns false (and changes nothing) for bad input. */
  function set(key, value) {
    const validate = VALIDATORS[key];
    if (!validate) return false;
    const clean = validate(value);
    if (clean === undefined) return false;
    if (values[key] === clean) return true;
    values[key] = clean;
    write(SETTINGS_KEY, JSON.stringify(values));
    if (events) events.emit('settings:change', { key, value: clean });
    return true;
  }

  function all() {
    return { ...values };
  }

  let sessionBest = 0; // keeps the record honest when storage is unavailable

  /** Best holdout score so far (0 when none). */
  function best() {
    const n = parseInt(read(BEST_KEY) || '0', 10);
    return Math.max(sessionBest, Number.isFinite(n) && n > 0 ? n : 0);
  }

  /** Stores `n` if it beats the best so far. Returns true when it is a new record. */
  function setBest(n) {
    const score = Math.round(Number(n) || 0);
    if (score <= best()) return false;
    sessionBest = score;
    write(BEST_KEY, String(score));
    return true;
  }

  return { get, set, all, best, setBest };
}
