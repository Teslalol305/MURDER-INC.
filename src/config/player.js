// Player tuning: body, movement, camera, health. Metres, seconds, radians unless a name says otherwise.
// Regeneration is per difficulty (config/flow.js) and written to `player.regen` by the game.

export const body = {
  radius: 0.32,
  height: 1.8,
  crouchHeight: 1.15,
  eye: 1.68,
  crouchEye: 1.05,
  eyeRate: 11, // damp rate of the eye height (≈ 90 % in 0.2 s)
  stepHeight: 0.42, // walk-up step while grounded
  airStepHeight: 0.08, // obstacle clearance while airborne
  boundsMargin: 0.4, // kept this far inside the physics bounds
};

/** Target speeds, m/s. */
export const speed = {
  walk: 3.8,
  sprint: 6.4,
  crouch: 1.9,
  ads: 2.4, // cap while fully aimed
  backpedal: 0.82, // multiplier at full backward input
};

/** Velocity moves toward the wish velocity at a constant rate (move-toward, not friction), m/s². */
export const accel = {
  ground: 34,
  groundStop: 26,
  air: 9,
  airStop: 0.6,
};

export const jump = {
  gravity: 21,
  apex: 1.0, // jump speed = sqrt(2 · gravity · apex) ≈ 6.48 m/s
  coyote: 0.12,
  buffer: 0.13,
  terminal: 40,
};

/** Sprint needs all of these; it is unlimited. */
export const sprint = {
  minForward: 0.55,
  maxStrafe: 0.6,
  maxAds: 0.35,
  minSpeedFrac: 0.6, // of walk speed, before the sprinting flag turns on
};

/** Metres travelled per footstep. */
export const stride = { walk: 1.55, sprint: 2.1, crouch: 1.05 };

export const look = {
  pitchLimit: 1.5, // aim pitch clamp
  viewPitchLimit: 1.55, // rendered pitch clamp (with recoil)
  adsScale: 0.6, // look-rate multiplier at full aim
};

/** Degrees. */
export const fov = {
  base: 74, // default of the user setting (60–95)
  min: 55,
  max: 100,
  sprintAdd: 6,
  ads: 52,
  rate: 7, // damp rate normally…
  rateAds: 30, // …and while the aim transition is in flight
  viewmodel: 54,
  title: 50,
};

export const health = {
  max: 100,
  regenDelay: 5.5, // defaults = Boss; overwritten per difficulty
  regenRate: 16,
  lowWarning: 30, // first time below this: radio line
  hurtPulse: { base: 0.35, perDamage: 1 / 40, decay: 1.9 }, // feeds render.post.damage
  lowHealth: { from: 0.55, to: 0.12, rate: 4 }, // health fraction → render.post.lowHealth 0…1
};

export const fall = {
  landMinAir: 0.12, // airborne longer than this counts as a landing
  damageFrom: 13, // m/s (about a 4 m drop)
  damagePerSpeed: 7,
  shakeFrom: 7.5,
  shakePerSpeed: 0.06,
  shakeMax: 0.5,
  dipPerSpeed: 0.36, // landing spring impulse
  dipMax: 3.2,
};

/** View bob, strafe roll and the landing spring. */
export const bob = {
  rate: 9,
  vertical: 0.024,
  lateral: 0.013,
  rollFromLateral: 0.35,
  sprintScale: 1.9,
  crouchScale: 0.7,
  adsScale: 0.22,
  strafeRoll: 0.02,
  strafeRollRate: 8,
  strafeRollAds: 0.4,
  spring: { stiffness: 150, damping: 17, min: -0.2, max: 0.05, pitch: 0.12 },
};

/** How weapon kicks reach the camera. */
export const recoil = {
  keep: 0.35, // share applied permanently to the aim
  maxPitch: 0.3, // clamp of the recoverable part
  maxYaw: 0.2,
  chase: 34,
  hold: 0.09, // seconds after the last shot before recentring
  recover: 6.5,
};

export const shake = {
  decay: 1.7, // trauma per second; magnitude = trauma²
  pitch: 0.03,
  yaw: 0.03,
  roll: 0.045,
  onHit: { base: 0.22, perDamage: 1 / 70 },
  onBlast: { range: 28, base: 0.15, scale: 0.9 }, // 0.15 + 0.9 · (1 − d / 28)²
};

export const death = {
  collapse: 0.85, // seconds for the camera to reach the floor
  eye: 0.22,
  roll: 1.15,
  capsuleHeight: 0.6,
  saturation: 0.12, // post targets, eased by the game
  fade: 0.55,
};

/** Device look rates and gamepad handling (details: reference notes 01). */
export const input = {
  mouse: 0.0021, // rad per pixel × sensitivity
  mouseGlitch: 400, // single events larger than this are discarded
  touch: 0.0052, // rad per CSS pixel × sensitivity
  touchStickRadius: 58,
  touchSprint: { magnitude: 0.93, forward: 0.8 },
  keyYaw: 2.1, // rad/s, not scaled by sensitivity
  keyPitch: 1.26,
  edgeYaw: 2.4,
  edgePitch: 1.2,
  edgeZoneX: 0.12,
  edgeZoneY: 0.1,
  lockTimeout: 1.2, // seconds before falling back to drag mode
  wheelDebounce: 0.28,
  pad: {
    deadzone: 0.14,
    trigger: 0.35,
    yaw: 2.9,
    pitchScale: 0.62,
    curve: [0.25, 0.75], // rate = a·m + b·m³
    boost: 1.75,
    boostFrom: 0.92,
    boostTime: 0.45,
    aimSlow: 0.55, // look-rate multiplier with an enemy under the crosshair
    aimRange: 60,
    aimEvery: 0.05,
    aimRate: 14,
  },
};
