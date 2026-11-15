// Game-flow tuning: state timings, interaction, spawning, reinforcement waves, pursuit, the holdout
// formulas and the debrief rating. Seconds and metres. Difficulty keys: hustler / boss / kingpin.

export const defaultDifficulty = 'boss';
export const difficulties = ['hustler', 'boss', 'kingpin'];
export const modes = ['mission', 'holdout'];

/** State machine: title → intro → playing ⇄ paused, playing → dead | complete. */
export const timing = {
  intro: 2.4, // first start
  introQuick: 1.1, // retry / restart / redeploy
  introFade: [0.05, 1.3], // black → clear between these times (end capped by the intro length)
  locationCardAt: 0.25, // full intro only
  introRadioAt: 0.9, // full intro only
  pauseDebounce: 0.35,
  deathCard: 1.5, // seconds after death
  debriefCard: 3.3, // seconds after reaching the truck
  lookHintEvery: 6, // desktop, mouse not captured: the look-mode hint comes back this often…
  lookHintSecs: 2.6, // …and stays this long
};

/** Screen treatment the game eases render.post toward: [target, rate]. */
export const post = {
  dead: { saturation: [0.12, 2.2], fade: [0.55, 1.4] },
  complete: { saturation: [0.7, 1.4], fade: [0.72, 1.2] },
};

/** Title fly-through along level.cinematicPath. */
export const titleCamera = {
  minLoop: 26, // loop length = max(minLoop, path length / speed)
  speed: 1.15,
  fov: 50,
  fadeIn: 1.8,
  fadeOut: 1.6,
  ease: 0.25, // progress along the loop = ease × smoothstep + (1 − ease) × linear
  sway: { rate: 0.42, side: 0.07, lift: 0.04, roll: 0.005 }, // a hand-held breath: rad/s, metres, metres, radians
};

/** Holding Interact on a master reel. The player stays free to move and can be shot. */
export const interact = {
  range: 2.2, // horizontal
  vertical: 2.5,
  facingDot: 0.45, // about a 63° half-cone…
  freeRange: 0.9, // …waived this close
  hold: 2.4, // seconds to grab
  decay: 1.6, // progress lost per second when the hold breaks
  shake: 0.18, // camera shake on a grab
};

export const extraction = {
  radius: 2.5,
  vertical: 3.5,
  refuseSecs: 3.5, // "Reels still out there…" message
  refuseEvery: 8,
};

/** Choosing where an enemy appears: every candidate point is scored, the best one wins. */
export const spawn = {
  firstDelay: 1.6, // first reinforcement after a grab…
  stagger: 0.85, // …then one every this long
  far: 18, // preferred minimum distance from the player
  patrolMinDistance: 32, // starting patrol: at least this far from the player start
  score: {
    random: 1.5, // + uniform 0…this
    far: 2, // + when at least `far` away…
    farExtra: 0.5, // …plus up to this more…
    farExtraOver: 30, // …spread over the next this many metres
    nearDivisor: 4, // − (far − distance) / this when closer
    hidden: 2.5, // + when the player's eye cannot see the point
    recent: -3, // when the point was used in the last `recentSecs`
    recentSecs: 6,
  },
  jitter: 1.2, // ± on x and z (ground points only if still walkable)
  airMinHeight: 2.5, // Buzzards spawned lower are lifted into…
  airLift: [6, 9],
  eyeHeight: 1.6, // sightline checks run from this high above the player's feet…
  probeHeight: 1.2, // …to this high above a ground point
  tooClose: 9, // a ground point picked earlier is swapped for a fresh one if the player now stands this near
  capRetry: 1, // a due spawn waits this long while the alive cap is reached
  poolRetry: 1.5, // and this long when the pool refused it…
  poolTries: 6, // …this many times before it is dropped
  alertRadius: 60, // each arrival re-alerts the area around the player
  fallbackRing: 26, // with no authored points: a ring around the player
  bannerSecs: 3.4, // "Contact — NORTH-EAST"
};

/** After the last reel: a finite pursuit while the player runs for the truck. */
export const pursuit = {
  firstDelay: 12,
  minAlive: 4, // one more spawns whenever fewer than this are alive…
  spawnDelay: 0.5,
  buzzardShare: 0.35, // …35 % Buzzard / 65 % Goon
  realertEvery: 4, // everyone is re-pointed at the player this often
  realertRadius: 90,
};

/**
 * Per-difficulty flow numbers (docs/DESIGN.md 3.1). `waves[n]` arrives after the (n + 1)-th reel.
 * `regen` is copied to player.regen.
 */
export const difficulty = {
  hustler: {
    regen: { delay: 4, rate: 25 },
    patrol: { buzzard: 1, goon: 3 },
    waves: [
      { buzzard: 2, goon: 3 },
      { buzzard: 2, goon: 4 },
      { buzzard: 3, goon: 5 },
    ],
    maxAlive: 9,
    pursuitEvery: 7,
    pursuitBudget: 5,
  },
  boss: {
    regen: { delay: 5.5, rate: 16 },
    patrol: { buzzard: 2, goon: 4 },
    waves: [
      { buzzard: 2, goon: 5 },
      { buzzard: 3, goon: 6 },
      { buzzard: 4, goon: 7 },
    ],
    maxAlive: 11,
    pursuitEvery: 5.5,
    pursuitBudget: 8,
  },
  kingpin: {
    regen: { delay: 7, rate: 10 },
    patrol: { buzzard: 2, goon: 5 },
    waves: [
      { buzzard: 3, goon: 6 },
      { buzzard: 4, goon: 7 },
      { buzzard: 5, goon: 8 },
    ],
    maxAlive: 13,
    pursuitEvery: 4.5,
    pursuitBudget: 12,
  },
};

/** Hold the Block: endless growing waves. n is the wave number, starting at 1. */
export const holdout = {
  firstDelay: 3.5, // before wave 1
  breather: 9, // between waves
  countdownFrom: 3, // "Wave N in 3 / 2 / 1" during the last seconds of a breather
  firstSpawn: 1.2, // first member after the wave starts
  bannerSecs: 3.6, // "Wave N — EAST"
  realertEvery: 5, // once a wave is all out, stragglers are pointed at the player this often…
  realertRadius: 90, // …so a wave never stalls on someone who lost the trail
  total: (n) => Math.min(5 + 2 * n, 30),
  buzzardShare: (n) => Math.max(0.25, 0.45 - 0.02 * n),
  stagger: (n) => Math.max(0.35, 0.9 - 0.04 * n),
  // Multipliers on the chosen difficulty's base values (not compounding): enemies.setScale({hp, damage, cooldown}).
  hpScale: (n) => Math.min(2.5, 1 + 0.07 * (n - 1)),
  damageScale: (n) => Math.min(2, 1 + 0.05 * (n - 1)),
  cooldownScale: (n) => Math.max(0.6, 1 - 0.03 * (n - 1)),
  extraAlive: (n) => Math.min(5, Math.floor(n / 2)), // added to the difficulty's maxAlive
  score: {
    buzzard: 100,
    goon: 150,
    killScale: (wave) => 1 + 0.1 * (wave - 1),
    waveClear: (wave) => 500 * wave,
  },
  resupply: {
    reserve: 90, // Chopper rounds…
    reserveCap: 240, // …up to this many
    heal: 35,
    explosivesEvery: 2, // explosives come back after every even wave
  },
};

/** Debrief certification: 0…5 points → config/text.js `ratings`. */
export const rating = {
  time: [
    [270, 2], // under 270 s: 2 points
    [400, 1],
  ],
  accuracy: [
    [0.5, 2], // at least 50 %: 2 points
    [0.3, 1],
  ],
  noRetries: 1,
};

/**
 * Rating points for a finished mission.
 * @param {{time: number, shots: number, hits: number, retries: number}} run
 */
export function ratingPoints(run) {
  let points = 0;
  for (const [limit, value] of rating.time) {
    if (run.time < limit) {
      points += value;
      break;
    }
  }
  const accuracy = run.shots > 0 ? run.hits / run.shots : 0;
  for (const [limit, value] of rating.accuracy) {
    if (accuracy >= limit) {
      points += value;
      break;
    }
  }
  if (!run.retries) points += rating.noRetries;
  return points;
}

/** Music intensity the game sends to audio.setMusicIntensity, re-evaluated while playing. */
export const music = {
  calm: 0.15, // also title, death card, debrief
  alert: 0.6,
  hot: 1,
  alertHold: 10, // seconds at `alert` after any enemy alert…
  hitHold: 8, // …or after the player is hit…
  nearDistance: 26, // …or while a living enemy is this close
  waveHot: 30, // seconds at `hot` after a wave is queued while anything is alive
  waveMinOut: 6, // that window ends early once the wave has been out this long and nothing is left
};

/** Text pacing shared by the flow and the HUD. */
export const pacing = {
  radioCharsPerSec: 58,
  objectiveCharsPerSec: 46,
  countdownSecs: 1,
  radioGap: 0.3, // silence between two queued radio lines
};
