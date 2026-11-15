// Brand tokens: names, wordmarks, palette and type. One place to drop in the real IPX identity later.
//
// The same palette is mirrored as CSS custom properties in src/base.css (`colors.plateEdge` ↔ `--c-plate-edge`,
// `fonts.display` ↔ `--font-display`), so the boot screen is right before any script runs; build.mjs warns
// when the two drift apart. At start-up the UI also writes every token below onto :root (src/ui/dom.js
// `applyBrand`), so changing a value here is enough to re-skin the HUD and the menus.

export const title = 'MURDER INC.';
/** Sentence-case form for the browser tab and plain-text messages. */
export const titlePlain = 'Murder Inc.';
export const presenter = 'IPX PRESENTS';
export const starLine = 'STARRING JA RULE';

/** The only IPX marks allowed in the world and the UI. No slogan. */
export const ipx = {
  wordmark: 'IPX',
  url: 'IPX.EXCHANGE',
};

/** Prefix of every localStorage key (see core/settings.js). */
export const storagePrefix = 'murderinc';

// One deliberate dark look: black enamel transit plates, white grotesque type, a taxi-yellow accent.
export const colors = {
  bg: '#07080a', // page behind the canvas, boot screen
  plate: '#0f1114', // enamel sign plates: cards, HUD blocks
  plateEdge: '#2a2e35', // hairlines and plate borders
  ink: '#f4f2ec', // primary type and the thin rule above it
  inkDim: '#b4b2ab', // secondary type
  inkFaint: '#8b8983', // tertiary / disabled
  gold: '#f6c21a', // accent: taxi / gold-record yellow
  red: '#e2222b', // danger: signal red
  oxblood: '#6b1218', // Vulture crew colour
  cyan: '#39d0e0', // neon secondary, used sparingly
  // Route bullets: one line colour per master reel, the accent for the IPX truck.
  line1: '#f2762e',
  line2: '#1fa463',
  line3: '#3b82f0',
  lineIpx: '#f6c21a',
};

/** Route-bullet colour by marker code ('1' | '2' | '3' | 'IPX'), for canvas drawing (the minimap). */
export const lines = {
  1: colors.line1,
  2: colors.line2,
  3: colors.line3,
  IPX: colors.lineIpx,
};

// Google Fonts with real fallbacks: the game must look right when the fonts are blocked. 'MI Narrow' and
// 'MI Heavy' are local-font aliases declared in src/base.css (a condensed bold where the system has one,
// else a heavy grotesque scaled down to the same footprint), so the wordmark keeps its size either way.
export const fonts = {
  display: "'Anton', Impact, 'Haettenschweiler', 'MI Narrow', 'MI Heavy', 'Arial Narrow', sans-serif", // wordmark, card titles
  ui: "'Archivo', 'Helvetica Neue', Helvetica, Arial, 'Inter', system-ui, sans-serif", // everything else
  mono: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace", // debug read-outs
};
