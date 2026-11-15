// Quality presets. `G.quality` is a copy of the active row; render.setQuality(name) switches rows.
//
//   scale        internal render scale relative to the canvas (before dynamic resolution)
//   msaa         samples of the HDR scene target (0 = off)
//   shadow       shadow-map size in pixels (0 = shadows off)
//   shadowEvery  the shadow map is redrawn every n-th frame
//   bloom        bloom pass on / off
//   lights       how many static real point / spot lights atmos may create (the rest are fake glows)
//   fx           multiplier on particle budgets
//   pixelBudget  hard cap on internal pixels per frame
//   maxDpr       cap on devicePixelRatio for the canvas itself

export const presets = {
  // Deterministic screenshots in software GL (`?shot=1`).
  test: { name: 'test', scale: 1, msaa: 0, shadow: 1024, shadowEvery: 1, bloom: true, lights: 4, fx: 0.4, pixelBudget: 1.0e6, maxDpr: 1 },
  low: { name: 'low', scale: 0.7, msaa: 0, shadow: 2048, shadowEvery: 2, bloom: true, lights: 4, fx: 0.5, pixelBudget: 1.0e6, maxDpr: 1.5 },
  medium: { name: 'medium', scale: 0.85, msaa: 2, shadow: 2048, shadowEvery: 2, bloom: true, lights: 6, fx: 0.8, pixelBudget: 1.5e6, maxDpr: 2 },
  high: { name: 'high', scale: 1, msaa: 4, shadow: 4096, shadowEvery: 2, bloom: true, lights: 8, fx: 1, pixelBudget: 2.3e6, maxDpr: 2 },
  ultra: { name: 'ultra', scale: 1, msaa: 4, shadow: 4096, shadowEvery: 1, bloom: true, lights: 12, fx: 1, pixelBudget: 3.7e6, maxDpr: 2 },
};

/** Presets a player can pick, cheapest first. Automatic drops walk this list downward. */
export const ladder = ['low', 'medium', 'high', 'ultra'];

/** Preset used when the name is unknown. */
export const fallback = 'medium';

/**
 * Picks a preset for the device. `ultra` is never chosen automatically.
 * @param {object} env
 * @param {string} [env.userAgent]
 * @param {number} [env.touchPoints]  navigator.maxTouchPoints
 * @param {number} [env.screenMin]    shorter side of the screen, CSS pixels
 * @param {string} [env.gpu]          unmasked WebGL renderer string
 * @returns {'low' | 'medium' | 'high'}
 */
export function autoDetect({ userAgent = '', touchPoints = 0, screenMin = Infinity, gpu = '' } = {}) {
  const mobile = /Android|iPhone|iPad|iPod|Mobile|Silk|Opera Mini/i.test(userAgent);
  if (mobile || (touchPoints > 0 && screenMin < 900)) return 'low';
  // Software rasterisers cannot hold a frame rate at any setting; give them the cheapest one.
  if (/SwiftShader|llvmpipe|Software|Basic Render/i.test(gpu)) return 'low';
  // Mobile-class GPUs on a desktop-sized screen, and integrated Intel graphics other than Arc.
  if (/Mali|Adreno|PowerVR/i.test(gpu)) return 'medium';
  if (/Intel/i.test(gpu) && !/Arc/i.test(gpu)) return 'medium';
  return 'high';
}

/**
 * Dynamic resolution: the internal render scale moves between `min` and 1 to hold the frame rate,
 * and a device that cannot keep up even at `min` is moved one preset down (`quality:auto`).
 */
export const dynamicResolution = {
  settle: 3.5, // seconds after load before measuring
  settleAfterChange: 1,
  windowFrames: 45, // a measuring window closes after this many frames…
  windowMs: 900, // …or this long, whichever comes first
  ignoreAbove: 1500, // ms: a hitch or a hidden tab, not a slow frame
  min: 0.6,
  step: 0.1,
  slow: 21.5, // average frame ms above this: scale down one step…
  slower: 30, // …two steps…
  slowest: 45, // …or straight to `min`
  fast: 17.4, // average below this: scale back up one step
  upWait: 2, // seconds before trying to scale up; doubles after each drop…
  upWaitMax: 60, // …up to this
  dropAbove: 26, // two windows in a row at `min` above this average: drop a preset
  dropScale: 0.8, // dynamic scale right after a drop
};
