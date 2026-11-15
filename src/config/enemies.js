// Enemy tuning: the Vultures. Goons (masked gunmen on foot) are the majority type, Buzzards (armed
// quadcopters) harass from the air. Metres, seconds, radians; [a, b] is a uniform random range.
//
// `buzzard`, `goon` and `ai` hold the base ("Hustler") values plus everything that never changes with
// difficulty. `difficulty[name]` lists only the fields that differ; enemies.setDifficulty(table)
// restores the base values and overlays the table. HP is fixed at spawn, everything else is read live.

/** Default `?eseed`: enemies draw from their own stream so level changes do not reshuffle the fight. */
export const seed = 9001;

/** Hard caps on simultaneous instances (pools are built once at boot). */
export const pool = { goon: 12, buzzard: 8, bodies: 6, bolts: 32 };

/**
 * Readability per time of day (atmos.time): `glow` scales the self-lit parts (mask, oxblood trim,
 * sneakers), `rim` the cool rim light. Night lifts the silhouettes off a dark street; in full sun the
 * albedo reads on its own and only a trace stays. The flares (telegraph, eye, bolts) must read in
 * sunlight too: by day they cover `cover` of the bright background behind them instead of only adding
 * to it, and flares are `flare` times larger.
 */
export const look = {
  day: { glow: 0.12, rim: 0.12, cover: 0.6, flare: 1.35 },
  night: { glow: 1, rim: 0.8, cover: 0, flare: 1 },
};

export const buzzard = {
  hp: 45,
  radius: 0.5, // hit volume: one flattened ellipsoid, no weak point
  halfHeight: 0.22,
  reaction: 0.4, // seconds of continuous sight before it engages
  spawnAlertTime: 8, // how long a reinforcement hunts before giving up

  // Flight: steering toward a target point, no pathfinding.
  maxSpeed: 8,
  investigateSpeed: 5.5,
  patrolSpeed: 3,
  accel: 11,
  yawRate: 3.2,
  pull: { horizontal: [2.2, 2.4], vertical: [5, 3.6] }, // [toward offset, against velocity]
  minHeight: 2.2,
  floorClearance: 1.1,
  ceilingClearance: 1.3,
  feelers: { forward: 2.2, forwardPerSpeed: 0.5, down: 2.4, up: 4, bounce: -0.25 },
  patrol: { radius: [4, 9], turn: 0.28 },
  investigate: { radius: 4.5, turn: 0.5, maxHeight: 5.5 },
  maxAltitude: 15, // never climbs above this…
  overshoot: 0.5, // …and is never knocked more than this above it
  climbLook: 6, // metres of the leg ahead checked for roofs to climb over (logic.js climbOver)
  boundsMargin: 1.2, // kept this far inside the play bounds
  // Flight planning around level.el (the track deck): pass `under` its underside or stay `over` its top,
  // never through it. `margin` grows the footprint, `hold` is how far outside a drone waits to descend.
  // `slide`: how far along the deck's edge a drone looks for room to come down when something tall stands
  // under its hold point or across its way in (logic.js deckSlide).
  deck: { under: 1.5, over: 3.6, thickness: 1, margin: 1.5, hold: 2.5, slide: 5 },
  // Last resort (buzzard.js detour): wanting to be more than `far` m (|dx|+|dy|+|dz|) away but not having
  // moved `moved` m for `after` s, it flies `distance` m off in a clear direction and `up` m higher, for `time` s.
  detour: { far: 2.5, moved: 0.5, after: 2.5, distance: 4, up: 1.5, time: 1.5 },
  orbit: {
    radius: [14, 22], // initial personal orbit radius…
    radiusClamp: [13, 23], // …which drifts inside this band
    radiusDrift: 3,
    altitude: [4.8, 7.2], // above the player
    speed: 3.6, // tangential, m/s
    speedFiring: 0.9, // it steadies to shoot
    rethink: [3, 8], // seconds between direction / radius changes
    reverseChance: 0.6,
    lostAfter: 1.5, // without sight it flies to the last known position instead
  },

  // Attack: a telegraphed burst of slow, dodgeable tracer bolts.
  boltDamage: 7,
  boltSpeed: 70,
  boltLife: 1.3,
  burst: 3,
  burstGap: 0.12,
  telegraph: 0.55,
  cooldown: [1.9, 3.3],
  firstCooldown: [1, 2.5],
  fireRange: 42,
  aimTolerance: 0.35,
  lead: [0.2, 0.85], // share of perfect lead, rolled once per burst
  aimHeight: 1.05, // chest, above the player's feet
  recoilPush: 0.35,
  spreadFar: 0.065, // at exposure 0
  spreadNear: 0.018, // at exposure 1
  spreadPerSpeed: 0.45, // × (1 + player speed · this)
  // Bolts hit a vertical capsule around the player; crouching lowers its top.
  boltTarget: { radius: 0.36, bottom: 0.35, top: 1.5, crouchTop: 1.0 },

  // Damage and death: it spins down and bursts where it lands.
  damagedBelow: 0.5, // of max HP: wobble, smoke, spread × damagedSpread
  damagedSpread: 1.5,
  damagedJitter: 1.6, // m/s² of sinusoidal steering noise
  smokeEvery: [0.1, 0.22], // seconds between smoke puffs while damaged
  hitKick: 0.5, // random roll / pitch impulse per hit, rad/s
  knockback: { perDamage: 0.09, max: 3 },
  deathKick: { up: 1.5, along: 2.5 },
  fallGravity: 9.5,
  fallMaxTime: 5,
  burstRadius: 3,
  burstDamage: 30, // the player takes burstDamage × burstPlayerScale at most
  burstPlayerScale: 0.5,
  score: 100,
};

export const goon = {
  hp: 90,
  radius: 0.3, // body
  height: 1.8,
  crouchHeight: 1.25, // between bursts behind cover
  head: { radius: 0.155, height: 1.62 }, // weak point: sphere centred this high above the feet
  bodyRadius: 0.27, // hit capsule from shin to shoulder
  eyeHeight: 1.6,
  gunHeight: 1.46, // shots leave from the body axis at this height (the shouldered SMG)
  // At a player up high whose chest is hidden (the deck's parapet, the office sill): rounds go `below` his
  // eye (or at the eye if that is hidden too), with the vertical spread × `spreadY`.
  overCover: { below: 0.25, spreadY: 0.3 },
  reaction: 0.55,
  spawnAlertTime: 10,

  // Movement on the nav grid.
  runSpeed: 4.5,
  stalkSpeed: 2,
  patrolSpeed: 1.5,
  accel: 7,
  decel: 9.8,
  turnRate: 2.5, // standing: turning to face a target
  pathTurnRate: 5, // walking: steering along a path
  aimRate: 4.5,
  replan: [0.6, 0.75],
  waypointReach: 0.55,
  goalReach: 0.45,
  turnInPlace: 1.1, // heading error above this: stop and turn
  separation: { goon: 1.7, player: 1.25 },
  blockedRay: { length: 0.75, perSpeed: 0.12, every: 0.12 },
  stuckTime: 0.5,
  patrol: { radius: 7, wait: [1.5, 4.5] },
  // `elevated`: a last known position this far above his feet is up on something (the scaffold deck, the
  // mezzanine office): he looks at it from a stand-off point that sees it (goon.js pickStand), chosen
  // again when the spot moves more than `restand` or, if the point turned out blind, after `restandAfter`
  // seconds of looking round; until then, or if there is no point at all, he stops `standFallback` short.
  investigate: { stalkWithin: 8, stopWithin: 2.2, sweep: 0.9, elevated: 1.2, restand: 1.5, restandAfter: 2.5, standFallback: 4.5 },

  // Fire positions: scored candidates between rangeMin and rangeMax from the player.
  rangeMin: 8,
  rangeMax: 18,
  repick: { playerMoved: 7, randomPoints: 7, arcPoints: 5, arc: 1.3, arcRange: [9, 17], minMove: 3 }, // minMove: a relocation goes at least this far
  positionCost: {
    travel: 0.9,
    authored: -2,
    random: 0,
    arc: 1,
    jitter: 3,
    sameBearing: 14, // within ~30° of another engaged Goon's bearing from the player
    crowded: 16, // within 3 m of another Goon's position or destination
    noSight: 22,
    cover: -4, // next to a level.coverPoints entry that still sees the player
  },
  cover: { snap: 1.6, crouchBetweenBursts: true, maxStep: 1 }, // maxStep: cover points this much above / below are out of reach
  move: { aimEarlyAfter: 1.4, aimEarlyRange: [7, 20], aimEarlyChance: 0.7, giveUp: 7 },
  hold: { tooClose: 5, tooCloseTime: 0.8, noSightTime: 1.1, maxWait: 3, aimTolerance: 0.14 },
  burstsBeforeMove: { one: 0.6 }, // chance to relocate after a single burst, else after two

  // Attack: a telegraphed hitscan SMG burst.
  shotDamage: 4,
  burst: 4,
  burstGap: 0.11,
  telegraph: 0.5,
  cooldown: [1.8, 3],
  firstCooldown: [0.6, 1.6],
  shotRange: 200,
  aimHeight: 1.0,
  spreadFar: 0.12,
  spreadNear: 0.045,
  spreadPerSpeed: 0.3,
  // A shot hits when the ray passes this close to the player's body centre.
  shotTarget: { horizontal: 0.38, vertical: 0.95 },

  // Rush: a pipe swing when the player is close. Needs no attack token.
  rushDamage: 15,
  rush: {
    range: 3, // starts inside this distance
    windup: 0.28,
    speed: 9.5,
    time: 0.36,
    reach: 1.35, // connects inside this distance during the dash
    recovery: 0.55,
    cooldown: 3.5,
  },

  // Death: a short collapse, then a non-colliding body that fades when it is the oldest.
  collapse: 0.9,
  bodyFade: 3.2,
  bodyStay: 45, // a body that is not pushed out by newer ones fades after this long
  staggerMax: 1.6, // hit reaction scale: min(staggerMax, damage / 28), cosmetic only
  score: 150,
};

/** Perception, alerting and attack pacing shared by both types. */
export const ai = {
  sightRange: 45,
  fov: (200 * Math.PI) / 180, // total, horizontal only
  closeRange: 3.5, // inside this the cone is ignored
  senseEvery: [0.11, 0.19],
  investigateReaction: 0.45, // multiplier on `reaction` once suspicious
  seenDecay: 0.6,
  loseSightAfter: 4,
  searchTime: [8, 11],
  noiseTime: [9, 13],
  provokedTime: 10,
  rallyOnSight: 18, // allies this close join when one engages
  rallyOnHit: 20,

  // Accuracy ramp: spread goes from far to near while an enemy keeps line of sight.
  exposureUp: 0.1,
  exposureDown: 0.45,

  // Attack tokens limit simultaneous ranged attackers. Rushes need none.
  tokens: 2,
  tokensCrowd: 3,
  crowdAbove: 5, // alive count that unlocks the crowd limit
  tokenGap: 1.25,
  tokenFairness: { refusedWithin: 0.5, gapFactor: 2.2 }, // types alternate when both want to fire

  // Hearing: alert(pos, radius) radii by cause.
  hear: {
    gunfire: 45,
    explosion: 30,
    explosive: 60, // a propane tank or welding rack
    reinforcement: 60, // centred on the player at each arrival
    escape: 90, // centred on the player every few seconds once all reels are out
  },
  alertDefaultRadius: 40,
  gunfireEvery: 0.3, // gunfire alerts at most this often

  // Budgets: the work that is spread over frames.
  pathsPerFrame: 2, // nav.findPath calls
  picksPerFrame: 1, // fire-position selections (each one casts a few dozen rays)
};

/** Per-difficulty overlays (docs/DESIGN.md 3.1). Boss is the default and the fallback. */
export const difficulty = {
  hustler: {
    buzzard: { hp: 45, boltDamage: 7, telegraph: 0.55, cooldown: [1.9, 3.3], spreadFar: 0.065, spreadNear: 0.018 },
    goon: { hp: 90, shotDamage: 4, burst: 4, cooldown: [1.8, 3], spreadFar: 0.12, spreadNear: 0.045, rushDamage: 15, runSpeed: 4.5 },
    ai: { tokens: 2, tokensCrowd: 3, tokenGap: 1.25, exposureUp: 0.1 },
  },
  boss: {
    buzzard: { hp: 55, boltDamage: 10, telegraph: 0.46, cooldown: [1.4, 2.5], spreadFar: 0.052, spreadNear: 0.016 },
    goon: { hp: 110, shotDamage: 6, burst: 5, cooldown: [1.4, 2.4], spreadFar: 0.095, spreadNear: 0.038, rushDamage: 22, runSpeed: 5 },
    ai: { tokens: 3, tokensCrowd: 4, tokenGap: 0.85, exposureUp: 0.14 },
  },
  kingpin: {
    buzzard: { hp: 60, boltDamage: 13, telegraph: 0.38, cooldown: [1, 1.9], spreadFar: 0.042, spreadNear: 0.014 },
    goon: { hp: 130, shotDamage: 8, burst: 6, cooldown: [1, 1.9], spreadFar: 0.08, spreadNear: 0.032, rushDamage: 30, runSpeed: 5.4 },
    ai: { tokens: 4, tokensCrowd: 5, tokenGap: 0.6, exposureUp: 0.18 },
  },
};
