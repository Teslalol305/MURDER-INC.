// The look: tone mapping, bloom and grade defaults for the renderer, and the night-atmosphere defaults
// for atmos. Night, sodium and neon: a deep blue-black sky, one steep warm "street light" key, cool
// moonlit ambient, emissive signs that bloom.
//
// `grade` becomes `render.look` (a live copy: assign to its fields to retune at runtime).

export const grade = {
  toneMapping: 'aces', // 'aces' | 'agx' | 'reinhard' | 'cineon' | 'linear' (read once at boot)
  exposure: 1.5, // tone-map exposure, multiplied by render.exposure
  bloomStrength: 0.55,
  bloomRadius: 0.6,
  bloomThreshold: 1, // scene-referred: emissive values above ~1 bloom
  bloomKnee: 0.35, // soft knee above the threshold (0 = hard cut, shimmers more)
  vignette: 0.3,
  grain: 0.035,
  aberration: 0.0012, // red / blue split at the screen corners, in UV units
  saturation: 1.06,
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

/** Night sky and haze. */
export const sky = {
  zenith: 0x070b16,
  horizon: 0x1a1522, // city glow near the skyline
  glow: 0x3a2a26,
};

export const fog = {
  color: 0x0b0e18,
  density: 0.006, // FogExp2: soft haze that swallows the far end of the avenue
};

/** Cool ambient from the sky, warm bounce from the street. */
export const ambient = {
  sky: 0x6f8fd0,
  ground: 0x4a3a2c,
  intensity: 4.2, // high on purpose: shadows must stay readable at night
};

/** The single shadow-casting key: steep, warm, standing in for the street lights. */
export const sun = {
  color: 0xffb46a,
  intensity: 3.2,
  direction: [-0.38, -1, -0.3], // the way the light travels
  shadowBias: -0.0004,
  shadowNormalBias: 0.03,
  shadowRadius: 2.5,
  shadowHeight: 34, // tallest thing that must cast a shadow inside the bounds
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
