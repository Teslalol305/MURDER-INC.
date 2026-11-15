// Brand tokens: names, wordmarks, palette and type. One place to drop in the real IPX identity later.
//
// The same palette is mirrored as CSS custom properties in src/base.css (`colors.plateEdge` ↔ `--c-plate-edge`,
// `fonts.display` ↔ `--font-display`). Change both together: build.mjs warns when they drift apart.

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
  plateEdge: '#262a30', // hairlines and plate borders
  ink: '#f4f2ec', // primary type and the thin rule above it
  inkDim: '#a9a7a0', // secondary type
  inkFaint: '#6c6b67', // tertiary / disabled
  gold: '#f6c21a', // accent: taxi / gold-record yellow
  red: '#e2222b', // danger: signal red
  oxblood: '#6b1218', // Vulture crew colour
  cyan: '#39d0e0', // neon secondary, used sparingly
};

// Google Fonts with real fallbacks: the game must look right when the fonts are blocked.
export const fonts = {
  display: "'Anton', 'Haettenschweiler', 'Arial Narrow Bold', Impact, 'Arial Narrow', sans-serif", // wordmark, card titles
  ui: "'Archivo', 'Helvetica Neue', Helvetica, Arial, system-ui, sans-serif", // everything else
  mono: "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace", // tabular figures
};
