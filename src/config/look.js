// The look: tone mapping, bloom and grade defaults for the renderer, and everything the atmosphere
// (src/atmos.js) is tuned with. Night, sodium and neon: a deep blue-black sky with the city glowing on
// the horizon, one steep warm "street light" key, cool moonlit ambient, lamps and signs that bloom.
//
// `grade` becomes `render.look` (a live copy: assign to its fields to retune at runtime).
//
// Colours written as [r, g, b] are scene-referred LINEAR radiance (what the HDR target holds before
// exposure and tone mapping): 1 is where bloom starts, 0.02 is a dark wall at night. Colours written
// as hex are ordinary sRGB.

export const grade = {
  toneMapping: 'aces', // 'aces' | 'agx' | 'reinhard' | 'cineon' | 'linear' (read once at boot)
  exposure: 1.4, // tone-map exposure, multiplied by render.exposure
  bloomStrength: 0.4,
  bloomRadius: 0.62,
  bloomThreshold: 1.05, // scene-referred: emissive values above ~1 bloom, lit asphalt and brick never do
  bloomKnee: 0.4, // soft knee above the threshold (0 = hard cut, shimmers more)
  vignette: 0.34,
  grain: 0.03,
  aberration: 0.001, // red / blue split at the screen corners, in UV units
  saturation: 1.08,
};

/** How gameplay values in render.post bend the grade (render.js reads these once at boot). */
export const feedback = {
  damageTint: [0.3, 0.008, 0.006], // linear RGB of the red on the screen edges (dark, not neon)
  damageEdge: 0.85, // edge opacity at render.post.damage = 1
  damageDesaturate: 0.5,
  lowHealthRim: 0.55, // pulsing rim opacity at render.post.lowHealth = 1
  lowHealthPulse: 5, // rad/s
  lowHealthDesaturate: 0.65,
  lowHealthVignette: 0.55,
  adsVignette: 0.22,
  flashWhite: 2.2, // scene-referred value a full render.post.flash reaches (the mix is flash²)
};

/** Clear colour before atmos installs a sky. */
export const clearColor = 0x04050a;

/**
 * The sky dome. West is −X (toward Manhattan): the sodium glow is strongest there.
 * `zenith`, `horizon` and `glow` (hex) are what the stub atmosphere paints; the dome uses the rest.
 */
export const sky = {
  zenith: 0x070b16,
  horizon: 0x1a1522,
  glow: 0x3a2a26,

  zenithRadiance: [0.0032, 0.0058, 0.0145], // deep blue-black overhead
  horizonRadiance: [0.011, 0.0135, 0.025], // the sky just above the haze, away from the glow
  glowWest: [0.3, 0.115, 0.03], // sodium orange over the far skyline
  glowEast: [0.034, 0.026, 0.03], // what is left of it everywhere else
  glowHeight: [0.07, 0.14], // e-folding height of the glow (sine of elevation): [elsewhere, west]

  clouds: {
    amount: 0.75, // 0 = clear
    scale: 1.15,
    stretch: [0.5, 1.5], // long streaks along the avenue
    drift: [0.011, 0.0035], // layer units per second
    litByGlow: 0.42, // how much of the glow the wisps catch from below
    moonlit: [0.012, 0.016, 0.026],
  },
  stars: {
    density: 0.0016, // fraction of sky cells holding a star
    brightness: 0.55,
  },
  moon: {
    direction: [0.86, 0.29, 0.42], // toward the moon: low in the east-south-east, down the avenue
    radius: 0.017, // radians (a little larger than life)
    radiance: [2.5, 2.35, 2.0],
    halo: 0.22,
  },
};

/** Night haze. Tinted by where you look: warm toward the glow in the west, cool toward the moon. */
export const fog = {
  color: 0x0b0e18, // what the stub atmosphere uses; the real one uses `haze`
  haze: [0.03, 0.03, 0.036], // base haze radiance (dark on screen once tone mapped)
  density: 0.006, // FogExp2: a soft haze, 5 % at 40 m, a quarter at the far end of the avenue
  tintWest: [3.1, 1.5, 0.68],
  tintEast: [0.72, 0.9, 1.22],
  // Outside the block the haze thickens: by `endReach` metres past the bounds nothing is left of the world
  // but lights. Set endReach to 0 to leave three.js' fog shader untouched.
  endReach: 105,
  endClear: 4, // metres past the bounds before it starts
};

/** Cool ambient from the sky, warm bounce from the street. */
export const ambient = {
  sky: 0x6e86be,
  ground: 0x4a3a2c,
  intensity: 1.7, // shadows must stay readable at night: a dark figure against a dim wall at 40 m
};

/** The single shadow-casting key: steep, warm, standing in for the street lights. */
export const sun = {
  color: 0xffb873,
  intensity: 2.6,
  direction: [-0.38, -1, -0.3], // the way the light travels
  shadowBias: -0.0004, // legacy (stub atmosphere); atmos uses shadowBiasMetres
  shadowBiasMetres: 0.045, // depth bias expressed in metres along the light
  shadowNormalBias: 0.035,
  shadowRadius: 2.5,
  shadowHeight: 34, // legacy cap: tallest thing that may cast a shadow inside the bounds
  shadowMargin: 2, // metres of slack around the fitted frustum
};

/** Lighting for the viewmodel scene (render owns it; the weapon has no lights of its own). */
export const viewmodel = {
  ambientSky: 0x8fa4cc,
  ambientGround: 0x4a3626,
  ambientIntensity: 3.5,
  keyColor: 0xffc890,
  keyIntensity: 2.6,
  keyDirection: [-0.38, -1, -0.3], // world space, matches the street key
};

/** World-space colours shared by fx, props and enemies. */
export const palette = {
  tracerPlayer: 0xffe2a8, // warm white-gold
  tracerEnemy: 0xff3a22, // red
  muzzle: 0xffc880,
  beacon: 0xf6c21a, // master-reel beacon: gold
  hazard: 0xff8a1a,
  sodium: 0xffb45e,
  neonPink: 0xff3d9a,
  neonRed: 0xff3030,
  neonCyan: 0x35e0ff,
  neonGreen: 0x55ff8a,
  taxi: 0xf2c21a,
  buzzardEye: 0xff2a1a,
};

/**
 * The image-based light (a PMREM of the sky plus stand-ins for the block: dark facades, the street and
 * a blob for every lamp, so paint, glass and wet asphalt have something to mirror).
 */
export const env = {
  intensity: 1, // scales everything in the capture
  facade: [0.03, 0.022, 0.02], // the building band around the probe
  street: [0.02, 0.017, 0.016],
  lampGain: 9, // radiance of a lamp blob = lamp colour × this × the per-kind `env` below
  maxLamps: 48,
};

/**
 * How each kind of `level.lamps` entry is drawn. Every lamp gets a ground pool and a glow at the
 * fixture; `cone` adds a soft shaft of light under it; `realGain` and `spot` shape the real light a
 * lamp gets while it holds one of the `quality.lights` (see `rig`).
 *   ref:   the intensity (cd) a typical lamp of this kind has: glows and cones scale against it
 *   pool:  radius = range × radius (clamped to [min, max] m), brightness = gain × intensity / height²
 *          (capped at `cap`); `hard` 0…1 sharpens the edge; `shadowed` pools are cut by the key's shadows
 *   glow:  size in metres, core / halo radiance multipliers of the lamp colour
 *   cone:  half-angle in degrees, gain, optional length as a fraction of the lamp's range
 */
export const lamps = {
  poolGain: 0.05,
  poolShadowFloor: 0.22, // what is left of a pool inside a shadow of the key light
  // A faint sheet of street light over the whole block, cut by the key's shadows: it lets near-black
  // asphalt carry the stripes of the El and the shadow of whoever stands on it. gain 0 switches it off.
  sheen: { gain: 0.02, color: 0xf0b888, cell: 2.3 },
  glowMinAngle: 0.0035, // glows never shrink below this many radians: far lamps stay points of light
  realGain: 1,
  // The `quality.lights` real lights are spots that move to whichever lamps matter most from where the
  // camera is: claim = (priority + 1) / (1 + (distance to the point looked at / reach)²).
  rig: {
    reach: 14, // metres at which a lamp's claim has halved
    lookAhead: 6, // the point of interest sits this far in front of the camera
    keep: 1.3, // advantage of a lamp that already holds a light (no flip-flopping)
    interval: 0.2, // seconds between evaluations
    fadeOut: 0.3,
    fadeIn: 0.4,
    rangeScale: 1.2,
    spot: { angle: 76, penumbra: 0.7 }, // default cone (half-angle, degrees): a shaded fixture
  },
  kinds: {
    street: {
      ref: 90, realGain: 1.3,
      pool: { radius: 0.36, min: 4.5, max: 8, gain: 1, shadowed: true },
      glow: { size: 1.5, core: 5, halo: 0.34 },
      cone: { angle: 37, gain: 0.03 },
      env: 1,
    },
    el: {
      ref: 30, realGain: 1.5,
      pool: { radius: 0.34, min: 3, max: 5, gain: 1.2 }, // hung under the deck: its shadow is not theirs
      glow: { size: 0.95, core: 4.2, halo: 0.3 },
      cone: { angle: 34, gain: 0.028 },
      env: 0.8,
    },
    work: {
      ref: 34, realGain: 3.4,
      pool: { radius: 0.4, min: 3.5, max: 6.5, gain: 1.5 },
      glow: { size: 0.7, core: 4.5, halo: 0.22 },
      cone: null,
      env: 0.9,
    },
    flood: {
      ref: 160, realGain: 1.7, spot: { angle: 52, penumbra: 0.28 },
      pool: { radius: 0.36, min: 7, max: 13, gain: 3.4, hard: 0.75, cap: 0.5, shadowed: true },
      glow: { size: 2.7, core: 9, halo: 0.4 },
      cone: { angle: 30, gain: 0.02, length: 0.95 },
      env: 1.3,
    },
    neon: {
      ref: 12, realGain: 1.4, spot: { angle: 86, penumbra: 0.8 },
      pool: { radius: 0.5, min: 3, max: 5.5, gain: 4.5, cap: 0.3, stretch: 1.7 }, // an ellipse along the wall
      glow: { size: 2.6, core: 0, halo: 0.035 },
      cone: null,
      env: 1.2,
    },
    window: {
      ref: 10, realGain: 1, spot: { angle: 86, penumbra: 0.8 },
      pool: { radius: 0.5, min: 2, max: 4, gain: 0.8 },
      glow: { size: 1.2, core: 0, halo: 0.08 },
      cone: null,
      env: 0.5,
    },
  },
  fallbackKind: 'street',
  // A couple of tired lamps buzz and drop out now and then (they never carry a real light).
  flicker: { count: 2, kinds: ['street', 'el'], belowPriority: 6 },
  // The avenue goes on past the bounds: receding rows of lamps under the El and along the kerbs.
  beyond: { reach: 150, streetEvery: 31, streetIntensity: 90, streetRange: 20, streetHeight: 7.7, elIntensity: 30, elRange: 12 },
};

/** What changes while the camera is inside the shop (atmos.setInterior). */
export const interior = {
  exposure: 0.86, // the eye is on bright tungsten: the street outside falls away
  ambient: 0.62, // less sky gets in
  ambientSky: 0xa9a0a0, // and what does is warmer
  fog: 0.5,
  rate: 2.2, // how fast the nudge follows the camera (per second)
  holdExplicit: 0.25, // seconds a value passed to setInterior() beats the camera position
};

/** The city beyond the bounds. */
export const city = {
  wall: [0.56, 0.54, 0.55], // multiplies the facade sheet (the sheet itself is dark brick and lit windows)
  windowGain: 1.7, // HDR lift for lit windows: just into the bloom
  litWindows: 0.2, // fraction of windows that are lit
  switchers: 22, // windows that go on and off while you watch
  aviation: 9, // blinking red lights on the tallest roofs
  skylineRadius: [215, 395], // the two rings of far cards
  skylineHeight: [72, 118],
  skylineHaze: [0.5, 0.74], // how far each ring has sunk into the haze
  traffic: 5, // far headlights crossing the avenue
  plane: { every: 85, height: 150, distance: 360, speed: 46 },
};

/** The El train. */
export const train = {
  firstPass: 20, // seconds after boot until the first train is overhead
  every: [40, 70], // seconds between one train starting its run and the next
  speed: 16.5, // m/s
  cars: 5,
  carLength: 15.4,
  carGap: 0.7,
  carWidth: 2.9,
  carHeight: 3.55,
  railOffset: 0.33, // rail top above level.el.y (the deck underside), when the level does not say (el.deckTop)
  trackOffset: 0.2, // track centres as a fraction of the deck width either side of its middle (or el.tracks)
  runUp: 145, // metres outside the bounds where the train appears and disappears, deep in the haze
  windowRadiance: [1.9, 2.05, 1.75], // cool fluorescent interior
  headlight: [9, 8.6, 7.4],
  tail: [5, 0.25, 0.15],
  stripeGain: 0.045, // window light falling through the ties onto the street
  flash: { every: [0.1, 0.34], intensity: [26, 60], range: 17, ttl: [0.07, 0.16], color: 0xd9e8ff, arcColor: 0x8fc4ff, arcChance: 0.22, arcIntensity: 130 },
  grit: { every: [0.16, 0.42], scale: [0.5, 1.1], reach: 26 },
  shake: 0.42, // trauma per second with the train right overhead
  shakeReach: 15, // metres from the deck edge where the rumble fades out
  gust: 3.2, // m/s kick the loose paper gets
};

/** Small things that move. */
export const life = {
  steam: { puffs: 11, rise: 1.25, height: 6.2, spread: 1.5, size: [0.55, 2.6], alpha: 0.2, color: [0.2, 0.18, 0.17] },
  motes: { lamps: 8, perLamp: 13, size: 2.4, radiance: 1.5 },
  paper: { sheets: 7, wind: [-1.1, 0.25], gustEvery: [5, 13], gust: 3.6 },
  hydrant: { drops: 260, speed: 5.2, lift: 0.3, spread: 0.07, radiance: [0.1, 0.12, 0.14] },
};

/** Which optional layers each quality preset draws (everything is built once; these only show and hide). */
export const detail = {
  test: { cones: false, motes: false, cityFull: false, farRing: false, switchers: false, grit: true, steamPuffs: 0.6 },
  low: { cones: false, motes: false, cityFull: false, farRing: false, switchers: false, grit: true, steamPuffs: 0.6 },
  medium: { cones: true, motes: true, cityFull: true, farRing: true, switchers: true, grit: true, steamPuffs: 1 },
  high: { cones: true, motes: true, cityFull: true, farRing: true, switchers: true, grit: true, steamPuffs: 1 },
  ultra: { cones: true, motes: true, cityFull: true, farRing: true, switchers: true, grit: true, steamPuffs: 1 },
};
