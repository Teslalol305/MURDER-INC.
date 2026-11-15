// Weapon tuning. Both guns are hitscan from the eye, one ray per shot, no falloff, no penetration.
// Metres, seconds, radians. Spread values are cone half-angles.

export const chopper = {
  id: 'chopper',
  name: 'CHOPPER',
  slot: 1,
  auto: true,
  damage: 26,
  rpm: 720,
  magSize: 30,
  reserve: 150, // at the start of every run
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
    [0.1, -0.115, -0.24, 0.01, 0.045, 0],
    [0.14, -0.17, -0.38, 0.02, 0.1, -0.05],
    [0.16, -0.165, -0.33, 0.015, 0.075, -0.03],
  ],
};

export const nine = {
  id: 'nine',
  name: 'NINE',
  slot: 2,
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
    [0.07, -0.105, -0.37, 0, 0.03, 0],
    [0.105, -0.14, -0.43, 0.01, 0.07, -0.04],
    [0.115, -0.135, -0.4, 0.01, 0.06, -0.03],
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

/** Rules shared by both guns. */
export const common = {
  order: ['chopper', 'nine'],
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
  flashSeconds: [0.036, 0.056],
  adsFlashScale: 0.62,
  explosiveHitFromEnemy: 9, // damage an enemy round does to a propane tank / welding rack
  // How the viewmodel is lit (weapon/viewmodel.js). `env` is the strength of its own reflection box,
  // `fill` a camera-space light that keeps the faces turned to the player from going black.
  // Night: `rim` [floor, gain] is a world-space light coloured by the street lamps around the player.
  // Day: the rim light is the sun (direction and colour from atmos.sun) at `sun` × its intensity, and
  // the box scales with that intensity over `sunRef`, so the gun sits in the same light as the street.
  light: {
    night: { env: 0.55, fill: 0.4, rim: [0.12, 1.3] },
    day: { env: 1.05, fill: 0.55, sun: 0.75, sunRef: 3 },
  },
};
