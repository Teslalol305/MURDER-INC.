// Copy that only the interface uses: labels of the settings drawer, the controls tables, small HUD words.
// Everything a player reads about the game itself (objectives, radio, cards) lives in src/config/text.js;
// where that file gains a key these fall back from (see `pick` in menus.js), it wins.

/** Direction v2 (DESIGN 8.1): the title eyebrow no longer carries a time; the location card follows the setting. */
export const title = {
  eyebrow: 'Presents · Hollis, Queens',
  modeLabel: 'Mode',
  difficultyLabel: 'Difficulty',
  timeLabel: 'Time',
  times: { day: 'Day', night: 'Night' },
  timeNotes: { day: '4:15 PM. Sun through the El.', night: '02:14 AM. Sodium and neon.' },
  glance: 'Controls at a glance',
};

export const location = {
  day: 'Hollis, Queens · Jamaica Ave · 4:15 PM',
  night: 'Hollis, Queens · Jamaica Ave · 02:14 AM',
};

export const hud = {
  objective: 'Objective',
  wave: 'Wave',
  hp: 'HP',
  melee: 'Melee',
  pause: 'Pause',
  settings: 'Settings',
  cue: {
    reloading: 'Reloading',
    low: 'Low ammo',
    reload: 'Reload',
    emptySwap: (glyph) => `Empty — ${glyph} for the next gun`,
    emptyTouch: 'Empty — pick another gun',
  },
  /** Zone band under the minimap, by level zone id (the lot zone splits into the court and the car park). */
  zones: { west: 'West End', avenue: 'The Avenue', shop: 'Chop Shop', cage: 'The Cage', lot: 'The Lot' },
};

export const cards = {
  toTitle: 'Back to title',
  newBest: 'New best',
  ipxLine: 'An IPX production',
};

export const panel = {
  label: 'Settings and controls',
  close: 'Close',
  tabs: { settings: 'Settings', controls: 'Controls' },
  difficulty: 'Difficulty',
  aimAssist: 'Aim assist',
  guide: 'Guide line',
  noteHelp: 'Aim assist: hold aim and the sights lock on to the nearest Vulture. The guide line runs along the ground to your next objective.',
  view: 'Weapon position',
  views: { 1: 'Close', 2: 'Three-quarter', 3: 'Compact' },
  quality: 'Graphics quality',
  qualities: { low: 'Low', medium: 'Medium', high: 'High', ultra: 'Ultra' },
  auto: 'Auto',
  sens: 'Look sensitivity',
  invertY: 'Invert Y',
  on: 'On',
  off: 'Off',
  volume: 'Master volume',
  fov: 'Field of view',
  display: 'Display',
  fullscreenEnter: 'Enter fullscreen',
  fullscreenExit: 'Exit fullscreen',
  fullscreenFail: 'Fullscreen is not available here',
  noteAuto: (tier) => `Quality was picked for this device (${tier}). Lower it if the frame rate struggles.`,
  noteManual: 'Changes apply at once. Shadows and reflections may take a moment to catch up.',
  noteDifficulty: 'Difficulty changes take effect at once; Vultures already on the block keep their health.',
};

/** Controls tab: [action, keys…, extra] rows per device. Key caps are drawn from the strings (or glyphs, below). */
export const controls = {
  kbm: {
    title: 'Keyboard · Mouse',
    rows: [
      ['Move', ['W', 'A', 'S', 'D']],
      ['Look', ['Mouse']],
      ['Fire', ['LMB']],
      ['Aim', ['RMB'], 'hold: the sights lock on to the nearest Vulture'],
      ['Reload', ['R']],
      ['Pick a weapon', ['1', '2', '3', '4', '5']],
      ['Next weapon', ['Q', 'Wheel']],
      ['Grab a reel', ['Hold E']],
      ['Jump', ['Space']],
      ['Sprint', ['Shift']],
      ['Crouch', ['C']],
      ['Melee', ['F']],
      ['Pause', ['Esc', 'P']],
    ],
    note:
      "If the browser won't lock the mouse, move it to look and rest it at a screen edge to keep turning. " +
      'Arrows or I J K L turn too, and Enter fires.',
  },
  touch: {
    title: 'Touch',
    /* A key written as { glyph } is drawn with that on-screen button's own glyph (config/player.js
       touchGlyphs), so the table shows exactly what the thumbs see; `label` adds the button's caption. */
    rows: [
      ['Move', ['Left thumb']],
      ['Look', ['Drag right side']],
      ['Fire', [{ glyph: 'fire' }], 'hold; drag to track'],
      ['Fire, left thumb', [{ glyph: 'fire' }], 'the small trigger on the left'],
      ['Aim', [{ glyph: 'ads' }], 'toggles; the sights lock on to the nearest Vulture'],
      ['Reload', [{ glyph: 'reload' }]],
      ['Next weapon', [{ glyph: 'swap' }], 'or tap a weapon on the bar'],
      ['Grab a reel', [{ glyph: 'interact', label: 'USE' }], 'hold it'],
      ['Jump', [{ glyph: 'jump' }]],
      ['Crouch', [{ glyph: 'crouch' }], 'toggles'],
      ['Melee', [{ glyph: 'melee' }]],
      ['Sprint', ['Stick'], 'pushed all the way forward'],
      ['Sprint lock', [{ glyph: 'sprint' }], 'tap the arrow above the stick to keep running'],
      ['Pause', [{ glyph: 'pause' }], 'beside the map'],
    ],
    note: '',
  },
  pad: {
    title: 'Controller',
    rows: [
      ['Move / look', ['L stick', 'R stick']],
      ['Fire', ['RT']],
      ['Aim', ['LT'], 'hold: the sights lock on to the nearest Vulture'],
      ['Reload', ['X'], 'hold X at a reel to grab it'],
      ['Next weapon', ['Y', 'D-pad right']],
      ['Previous weapon', ['D-pad left']],
      ['Jump', ['A']],
      ['Crouch', ['B', 'LB']],
      ['Sprint', ['L3']],
      ['Melee', ['RB', 'R3']],
      ['Pause', ['Start']],
    ],
    note:
      'In menus the D-pad or left stick moves the selection, A accepts, B goes back. Browsers only start sound ' +
      'after a click or a key press, so a controller-only start can be silent until one click.',
  },
};

/** Title screen strip (wide screens only): the essentials, one line per device. */
export const glance = [
  ['Move', ['W', 'A', 'S', 'D']],
  ['Fire', ['LMB']],
  ['Aim', ['RMB']],
  ['Reload', ['R']],
  ['Weapons', ['1', '–', '5']],
  ['Grab', ['Hold E']],
  ['Sprint', ['Shift']],
  ['Crouch', ['C']],
  ['Melee', ['F']],
  ['Pause', ['Esc']],
];

export const glanceOther = [
  ['Controller', 'Sticks · RT fire · LT aim · X reload · Y next weapon'],
  ['Touch', 'Left thumb moves · right side looks · the bullet button fires'],
];
