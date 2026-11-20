// Weapon tuning. The four guns are hitscan from the eye, one ray per shot, no falloff, no penetration;
// the ROCKET flies (see its `projectile`). Metres, seconds, radians. Spread values are cone half-angles.
//
// `kind` is the family a gun handles like: 'rifle' (two hands on a long gun), 'pistol', 'launcher'.
// `pickup` is what one ammo drop is worth to the gun: that many rounds for the reserve, up to `cap`.

export const chopper = {
  id: 'chopper',
  name: 'CHOPPER',
  slot: 1,
  kind: 'rifle',
  auto: true,
  damage: 26,
  rpm: 720,
  magSize: 30,
  reserve: 150, // at the start of every run
  pickup: { rounds: 60, cap: 240 },
  range: 300,
  adsTime: 0.18, // linear ramp, then quintic smootherstep
  dryReloadDelay: 0.32, // dry trigger pull schedules a reload after this long
  // Timeline of a reload. Ammo moves at `magIn`; `tactical` / `empty` are the totals.
  reload: {
    tactical: 2.24,
    empty: 2.72,
    magOut: 0.4,
    magShow: 0.8,
    magInsert: 1.15,
    magIn: 1.44,
    tug: 1.565,
    pressCheck: [1.89, 1.93], // tactical only
    boltBack: 1.96, // empty only
    boltRelease: 2.155,
  },
  spread: {
    hip: 0.0125,
    ads: 0.0012,
    moveHip: 0.013,
    moveAds: 0.004,
    bloomHip: 0.0065,
    bloomAds: 0.0022,
    air: 0.022,
    crouch: 0.002,
    shot: 0.17, // bloom added per shot (bloom is 0…1)
    decay: 1.5, // bloom lost per second
  },
  recoil: {
    pitch: 0.0068,
    pitchRandom: [0.85, 1.15],
    lateFrom: 10, // from this shot of a burst the climb flattens…
    lateScale: 0.38, // …to this share
    yawEarly: 0.0011, // random ± for shots 1–3
    weaveFrom: 4, // then a side-to-side weave: sin(n · freq + phase) · amp ± random
    weaveAmp: 0.0042,
    weaveFreq: 0.57,
    weaveRandom: 0.001,
    shake: 0.12,
  },
  // Viewmodel kick: velocity impulses into six springs [angular frequency, damping ratio].
  kick: {
    back: 0.82,
    rise: 1.5,
    yaw: 0.475,
    roll: 0.85,
    up: 0.11,
    side: 0.09,
    firstShot: 1.4,
    secondShot: 1.2,
    random: 0.12,
    crouch: 0.88,
    ads: { back: 0.75, rot: 0.1, pos: 0.9 },
    springs: { back: [44, 0.55], pitch: [36, 0.5], yaw: [30, 0.45], roll: [31, 0.42], pos: [40, 0.5] },
    arm: [0.55, 0.35], // right, left
  },
  adsSpring: [23, 0.75],
  swaySpring: [13.5, 0.64],
  swayMax: 0.07,
  flash: { scale: 1, light: 45, lightColor: 0xffb020, lightRange: 9, lightTtl: 0.05 },
  rumble: { strong: 0.18, weak: 0.5, ms: 55 },
  wallPull: [1.05, 0.42], // starts / full, metres to the wall ahead
  inspectAfter: 24,
  muzzleSmoke: true,
  // Hip poses for the three "weapon position" settings (Close / Three-quarter / Compact):
  // [x right, y up, z back, pitch, yaw, roll] of the receiver's back end, in view space.
  views: [
    [0.15, -0.09, -0.24, 0.05, 0.28, -0.35],
    [0.17, -0.12, -0.3, 0.04, 0.22, -0.3],
    [0.12, -0.085, -0.25, 0.05, 0.24, -0.3],
  ],
};

export const nine = {
  id: 'nine',
  name: 'NINE',
  slot: 2,
  kind: 'pistol',
  auto: false,
  damage: 34,
  rpm: 420, // cap for semi-auto clicking
  magSize: 15,
  reserve: Infinity, // never runs dry
  range: 120,
  adsTime: 0.14,
  fireBuffer: 0.13, // a click this early still fires
  dryCooldown: 0.12,
  dryReloadDelay: 0.28,
  reload: {
    tactical: 1.5,
    empty: 1.9,
    magOut: 0.18,
    magShow: 0.48,
    magInsert: 0.9,
    magIn: 1.13,
    slideRelease: 1.61, // empty only
  },
  spread: {
    hip: 0.0105,
    ads: 0.0017,
    moveHip: 0.0065,
    moveAds: 0.003,
    bloomHip: 0.0085,
    bloomAds: 0.003,
    air: 0.018,
    crouch: 0.002,
    shot: 0.3,
    decay: 2.8,
  },
  recoil: {
    pitch: 0.0092,
    pitchRandom: [0.9, 1.1],
    yaw: 0.0025, // random ±
    shake: 0.14,
  },
  kick: {
    back: 0.55,
    rise: 6.4,
    yaw: 0.65,
    roll: 1.15,
    up: 0.2,
    side: 0.1,
    firstShot: 1,
    secondShot: 1,
    random: 0.1,
    crouch: 0.9,
    ads: { back: 0.8, rot: 0.42, pos: 0.8 },
    springs: { back: [56, 0.55], pitch: [50, 0.5], yaw: [38, 0.48], roll: [38, 0.45], pos: [46, 0.5] },
    arm: [0.8, 0.6],
  },
  adsSpring: [29.5, 0.75],
  swaySpring: [19, 0.6],
  swayMax: 0.085,
  flash: { scale: 0.55, light: 30, lightColor: 0xffb020, lightRange: 9, lightTtl: 0.05 },
  rumble: { strong: 0.35, weak: 0.6, ms: 55 },
  wallPull: [0.8, 0.32],
  muzzleSmoke: false,
  // Hip poses of the back of the slide for the three "weapon position" settings (see the Chopper).
  views: [
    [0.105, -0.056, -0.36, 0.07, 0.11, -0.18],
    [0.1, -0.075, -0.44, 0.06, 0.11, -0.2],
    [0.075, -0.055, -0.33, 0.07, 0.15, -0.16],
  ],
};

/**
 * The AR-15: the marksman's rifle of the five. Slower than the Chopper, flatter, far tighter: it holds
 * a head at the far end of the avenue.
 */
export const ar15 = {
  id: 'ar15',
  name: 'AR-15',
  slot: 3,
  kind: 'rifle',
  auto: true,
  damage: 31,
  rpm: 640,
  magSize: 30,
  reserve: 120,
  pickup: { rounds: 60, cap: 210 },
  range: 320,
  adsTime: 0.2,
  dryReloadDelay: 0.3,
  // Magazine out with the button, a fresh one straight up into the well; empty: the charging handle.
  reload: {
    tactical: 1.96,
    empty: 2.46,
    magOut: 0.36,
    magShow: 0.76,
    magInsert: 1.1,
    magIn: 1.36,
    tug: 1.48,
    boltBack: 1.8, // empty only
    boltRelease: 2.0,
  },
  spread: {
    hip: 0.011,
    ads: 0.0008,
    moveHip: 0.011,
    moveAds: 0.003,
    bloomHip: 0.005,
    bloomAds: 0.0015,
    air: 0.02,
    crouch: 0.002,
    shot: 0.13,
    decay: 2.0,
  },
  recoil: {
    pitch: 0.0052,
    pitchRandom: [0.9, 1.1],
    lateFrom: 8,
    lateScale: 0.42,
    yawEarly: 0.0008,
    weaveFrom: 5,
    weaveAmp: 0.0026,
    weaveFreq: 0.5,
    weaveRandom: 0.0008,
    shake: 0.1,
  },
  kick: {
    back: 0.7,
    rise: 1.15,
    yaw: 0.36,
    roll: 0.6,
    up: 0.09,
    side: 0.07,
    firstShot: 1.3,
    secondShot: 1.15,
    random: 0.1,
    crouch: 0.88,
    ads: { back: 0.75, rot: 0.1, pos: 0.9 },
    springs: { back: [46, 0.58], pitch: [38, 0.52], yaw: [32, 0.48], roll: [33, 0.45], pos: [42, 0.52] },
    arm: [0.5, 0.32],
  },
  adsSpring: [22, 0.76],
  swaySpring: [13, 0.66],
  swayMax: 0.065,
  flash: { scale: 0.9, light: 42, lightColor: 0xffb020, lightRange: 9, lightTtl: 0.05 },
  rumble: { strong: 0.16, weak: 0.45, ms: 50 },
  wallPull: [1.15, 0.46],
  inspectAfter: 24,
  muzzleSmoke: true,
  views: [
    [0.15, -0.1, -0.2, 0.05, 0.26, -0.33],
    [0.17, -0.13, -0.26, 0.04, 0.2, -0.28],
    [0.12, -0.095, -0.21, 0.05, 0.22, -0.28],
  ],
};

/**
 * The SWITCH: a nine with a switch on the back plate and a long magazine. Empties in under two
 * seconds, climbs hard, rules a doorway.
 */
export const switch9 = {
  id: 'switch9',
  name: 'SWITCH',
  slot: 4,
  kind: 'pistol',
  auto: true,
  damage: 19,
  rpm: 1100,
  magSize: 33,
  reserve: 132,
  pickup: { rounds: 66, cap: 231 },
  range: 110,
  adsTime: 0.13,
  dryCooldown: 0.12,
  dryReloadDelay: 0.26,
  reload: {
    tactical: 1.46,
    empty: 1.86,
    magOut: 0.18,
    magShow: 0.48,
    magInsert: 0.88,
    magIn: 1.1,
    slideRelease: 1.57, // empty only
  },
  spread: {
    hip: 0.014,
    ads: 0.003,
    moveHip: 0.007,
    moveAds: 0.0035,
    bloomHip: 0.02,
    bloomAds: 0.008,
    air: 0.02,
    crouch: 0.002,
    shot: 0.1,
    decay: 1.6,
  },
  recoil: {
    pitch: 0.006,
    pitchRandom: [0.85, 1.15],
    lateFrom: 12,
    lateScale: 0.5,
    yawEarly: 0.002,
    weaveFrom: 3,
    weaveAmp: 0.006,
    weaveFreq: 0.9,
    weaveRandom: 0.002,
    shake: 0.1,
  },
  kick: {
    back: 0.4,
    rise: 3.6,
    yaw: 0.6,
    roll: 1.0,
    up: 0.13,
    side: 0.09,
    firstShot: 1.2,
    secondShot: 1.1,
    random: 0.16,
    crouch: 0.9,
    ads: { back: 0.8, rot: 0.5, pos: 0.8 },
    springs: { back: [58, 0.55], pitch: [48, 0.46], yaw: [38, 0.46], roll: [38, 0.44], pos: [46, 0.5] },
    arm: [0.8, 0.6],
  },
  adsSpring: [29.5, 0.75],
  swaySpring: [19, 0.6],
  swayMax: 0.085,
  flash: { scale: 0.5, light: 28, lightColor: 0xffb020, lightRange: 8, lightTtl: 0.045 },
  rumble: { strong: 0.3, weak: 0.55, ms: 40 },
  wallPull: [0.8, 0.32],
  muzzleSmoke: true,
  views: [
    [0.105, -0.058, -0.36, 0.07, 0.11, -0.18],
    [0.1, -0.077, -0.44, 0.06, 0.11, -0.2],
    [0.075, -0.057, -0.33, 0.07, 0.15, -0.16],
  ],
};

/**
 * The ROCKET: a shoulder launcher, one round up the spout. The round flies straight at `speed` and
 * goes off on whatever it meets (or after `life` seconds): a blast like a propane tank's, of which
 * the player takes `playerScale` (src/weapon/rockets.js). Everything else about it is slow.
 */
export const rocket = {
  id: 'rocket',
  name: 'ROCKET',
  slot: 5,
  kind: 'launcher',
  auto: false,
  damage: 240, // at the centre of the blast, falling to nothing at its radius
  // `fuse`: it also goes off this close to a Vulture it would otherwise fly past; `trail`: metres between two wisps of its smoke.
  projectile: { speed: 62, life: 4, radius: 6.8, playerScale: 0.3, fuse: 0.9, trail: 1.5 },
  rpm: 60,
  magSize: 1,
  reserve: 3,
  pickup: { rounds: 1, cap: 6 },
  range: 220,
  adsTime: 0.24,
  fireBuffer: 0.13,
  dryCooldown: 0.2,
  dryReloadDelay: 0.3,
  reloadAfterShot: 0.5, // the next round is reached for this long after one leaves
  // One timeline: the launcher is only ever reloaded empty. A fresh round comes up from the left and
  // goes in nose out; `magIn` is the moment it is seated and counts.
  reload: {
    tactical: 2.3,
    empty: 2.3,
    magOut: 0.3,
    magShow: 0.8,
    magInsert: 1.34,
    magIn: 1.72,
  },
  spread: {
    hip: 0.012,
    ads: 0.002,
    moveHip: 0.01,
    moveAds: 0.004,
    bloomHip: 0,
    bloomAds: 0,
    air: 0.03,
    crouch: 0.002,
    shot: 0,
    decay: 1,
  },
  recoil: {
    pitch: 0.03,
    pitchRandom: [0.9, 1.1],
    yaw: 0.006, // random ±
    shake: 0.4,
  },
  kick: {
    back: 1.6,
    rise: 2.6,
    yaw: 0.5,
    roll: 1.2,
    up: 0.2,
    side: 0.1,
    firstShot: 1,
    secondShot: 1,
    random: 0.1,
    crouch: 0.9,
    ads: { back: 0.85, rot: 0.6, pos: 0.9 },
    springs: { back: [26, 0.6], pitch: [22, 0.55], yaw: [20, 0.5], roll: [20, 0.5], pos: [24, 0.55] },
    arm: [0.7, 0.5],
  },
  adsSpring: [18, 0.8],
  swaySpring: [10, 0.7],
  swayMax: 0.06,
  flash: { scale: 1.5, light: 70, lightColor: 0xffa040, lightRange: 12, lightTtl: 0.09 },
  rumble: { strong: 0.9, weak: 0.8, ms: 180 },
  wallPull: [1.3, 0.55],
  muzzleSmoke: true,
  views: [
    [0.16, -0.06, -0.1, 0.03, 0.1, -0.1],
    [0.18, -0.08, -0.14, 0.03, 0.08, -0.1],
    [0.14, -0.06, -0.1, 0.03, 0.1, -0.08],
  ],
};

/** Quick strike with whatever is in hand (docs/DESIGN.md 3.1). Kills count as kills, not as shots. */
export const melee = {
  duration: 0.55, // whole strike
  hitAt: 0.16, // the blow lands here
  reach: 2.3,
  cone: (50 * Math.PI) / 180, // full width of the cone, radians
  damage: 60,
  cooldown: 0.75, // between strikes
  cancelsReload: true,
  blockedWhileSwitching: true,
  shake: 0.22, // camera shake when the blow lands on a body (half of it on a wall)
};

/**
 * Aim assist (the `aimAssist` setting, src/weapon/assist.js): pulling the aim trigger locks the view
 * onto the Vulture nearest the crosshair and holds it there while the trigger stays down.
 */
export const assist = {
  range: 75, // metres
  cone: 0.3, // half-angle (rad) around the crosshair in which a target is picked up…
  coneTouch: 0.42, // …wider under a thumb
  keep: 0.6, // a lock lets go past this angle; also how far off the aim the next target may be after a kill
  snap: 14, // 1/s: how fast the view closes on the target while the lock is taken…
  snapSecs: 0.22, // …for this long…
  track: 30, // …then it holds on, recoil included
  lostSecs: 0.45, // out of sight this long: the lock is dropped
  flickRate: 2.6, // rad/s of the player's own look that breaks the lock (a hard flick or a full stick)
  reacquire: 0.18, // seconds before a new lock after a kill or a break
  chest: 0.7, // aim point on a Goon without a body pose: this share of its height
};

/** Rules shared by every gun. */
export const common = {
  order: ['chopper', 'nine', 'ar15', 'switch9', 'rocket'],
  headMultiplier: 2.2, // Goon head only
  holster: 0.28,
  draw: 0.32,
  burstReset: 0.24, // seconds without a shot before the burst counter clears
  maxCatchUpShots: 3, // per frame, keeps the rate of fire frame-rate independent
  spreadRate: 18, // approach rate of the displayed spread
  bloomHold: 0.15, // seconds after a round before its bloom starts to drain
  spreadSpeedRef: 6, // player speed that gives the full movement penalty
  adsRecoilScale: 0.55,
  crouchRecoilScale: 0.85,
  sprintRate: 17, // angular frequency of the (critically damped) sprint-lower blend
  sprintHurry: 1.5, // …times this when the player wants to fire, aim or reload
  sprintFireGate: 0.45, // sprint-lowered blend must fall below this to fire…
  sprintAdsGate: 0.35, // …and this to aim
  firingHold: 0.14, // seconds the state reads 'firing' after a shot
  wallEvery: 0.08, // seconds between forward probes for the wall pull-back
  wallRate: 12, // approach rate of the pull-back
  wallAdsScale: 0.15, // share of the pull-back that survives full aim
  heat: { perShot: 0.05, max: 1.3, cool: 0.2 },
  noise: { radius: 45, every: 0.3 }, // gunfire heard by enemies
  tracer: { color: 0xffe2a8, speed: 260 },
  shake: { decay: 1.7 },
  lowAmmoFraction: 0.27, // of the magazine: HUD "low" cue
  reloadWhenEmpty: 0.6, // an emptied magazine is changed by itself this long after its last round (0: never)
  flashSeconds: [0.036, 0.056],
  adsFlashScale: 0.62,
  explosiveHitFromEnemy: 9, // damage an enemy round does to a propane tank / welding rack
  // How the viewmodel is lit (weapon/viewmodel.js). `env` is the strength of its own reflection box,
  // `fill` a camera-space light that keeps the faces turned to the player from going black.
  // Night: `rim` [floor, gain] is a world-space light coloured by the street lamps around the player.
  // Day: the rim light is the sun (direction and colour from atmos.sun) at `sun` × its intensity, and
  // the box scales with that intensity over `sunRef`, so the gun sits in the same light as the street.
  // Render's viewmodel ambient and key (config/look.js `viewmodel`) are the night's; by day the
  // ambient becomes a neutral sky over warm pavement (`ambient*`) and render's key goes to `key`.
  light: {
    night: { env: 0.55, fill: 0.4, rim: [0.12, 1.3] },
    day: { env: 1.0, fill: 0.45, sun: 0.85, sunRef: 5, ambient: 1.0, ambientSky: 0xc8ccd4, ambientGround: 0x8a7a66, key: 0 },
  },
};
