// Every player-facing string (docs/DESIGN.md section 2). The flow and UI code read copy from here by key
// and never hard-code it. Lines that carry a number, a direction or a key glyph are small functions.
//
// Tone: confident, dry, New York. Short sentences.

export const title = {
  eyebrow: 'IPX PRESENTS · HOLLIS, QUEENS',
  wordmark: 'MURDER INC.',
  star: 'STARRING JA RULE',
  premise: 'The Vultures jacked three master reels. Take the block back. Get them to the truck.',
  note: 'Every street, sound and beat is generated in your browser. No art or audio files.',
  start: 'Hit the block',
  settings: 'Settings',
  controls: 'Controls',
};

/**
 * Intro location card: two lines. The first depends on the `time` setting: the game picks it on every
 * run reset, writes it to `place` and also hands `{place, tagline}` to `menus.locationCard(true, data)`.
 */
export const location = {
  place: 'Hollis, Queens · Jamaica Ave · 4:15 PM',
  tagline: 'Three reels. One block. No backup.',
  /** Hold the Block has no reels: its card says this instead. */
  taglineHoldout: 'One block. Endless Vultures.',
  byTime: {
    day: 'Hollis, Queens · Jamaica Ave · 4:15 PM',
    night: 'Hollis, Queens · Jamaica Ave · 02:14 AM',
  },
};

/**
 * Zone display names for the band under the minimap, by `level.zoneAt()` id. The lot zone is two places:
 * the court north of the avenue and the parking lot south of it (see `zoneName`).
 */
export const zones = {
  west: 'WEST END',
  avenue: 'THE AVENUE',
  shop: 'CHOP SHOP',
  lot: 'THE LOT',
  cage: 'THE CAGE',
};

/** Display name of the zone `id` for a point at depth `z` (north is −Z): the lot zone north of the avenue is The Cage. */
export const zoneName = (id, z = 0) => (id === 'lot' && z < -7 ? zones.cage : zones[id] || zones.avenue);

export const modes = {
  mission: {
    name: 'Story',
    note: 'Take back three master reels and reach the IPX truck. About five minutes.',
  },
  holdout: {
    name: 'Hold the Block',
    note: 'Endless waves that keep growing. Resupply between waves. How long can you hold it down?',
  },
};

/** Difficulty keys as stored in settings → display names. Boss is the default. */
export const difficulties = {
  hustler: 'Hustler',
  boss: 'Boss',
  kingpin: 'Kingpin',
};

export const weapons = {
  chopper: { name: 'CHOPPER', blurb: 'Compact automatic carbine, 30 rounds' },
  nine: { name: 'NINE', blurb: '9 mm pistol, 15 rounds, never runs dry' },
  melee: { nine: 'Pistol whip', chopper: 'Rifle butt' },
};

/** The three objectives, in route-bullet order, and the extraction marker. */
export const reels = {
  item: 'Master reel',
  list: [
    { id: 'reel1', code: '1', label: 'Reel 1 — The Avenue' },
    { id: 'reel2', code: '2', label: 'Reel 2 — Chop Shop' },
    { id: 'reel3', code: '3', label: 'Reel 3 — The Cage' },
  ],
};

export const extraction = { label: 'IPX truck', code: 'IPX' };

export const enemies = {
  goon: { name: 'Goon', down: 'Goon down' },
  buzzard: { name: 'Buzzard', down: 'Buzzard down' },
  headshot: 'Headshot',
};

export const explosives = {
  propane: 'Propane tank',
  rack: 'Welding rack',
};

/** Objective tracker lines. `mission[n]` is shown once n reels are secured (n = 3: go to the truck). */
export const objectives = {
  mission: ['Take back the three master reels', 'Two reels left', 'Last reel', 'Get to the IPX truck'],
  holdout: {
    inbound: 'Vultures inbound',
    hold: 'Hold the block',
    breather: 'Catch your breath',
  },
  tally: {
    standby: 'Stand by',
    wave: (n, score) => `Wave ${n} · ${Math.round(score).toLocaleString('en-US')}`,
  },
};

export const prompts = {
  /** "Hold E — Grab reel 1": glyph comes from input.glyph('interact'), code from the reel. */
  grab: (glyph, code) => `Hold ${glyph} — Grab reel ${code}`,
  /** At the truck before all three reels are back. */
  refuse: "Reels still out there — the truck won't roll without all three",
};

/** 8-way compass sectors, clockwise from north (north = −Z, east = +X). */
export const compass = ['NORTH', 'NORTH-EAST', 'EAST', 'SOUTH-EAST', 'SOUTH', 'SOUTH-WEST', 'WEST', 'NORTH-WEST'];

/** Notes shown next to settings. */
export const notes = {
  difficulty: 'Difficulty changes take effect at once; Vultures already on the block keep their health.',
  time: 'Time of day changes when the next run starts.',
};

export const banners = {
  contact: (dir) => `Contact — ${dir}`,
  wave: (n, dir) => `Wave ${n} — ${dir}`,
  countdown: (n, secs) => `Wave ${n} in ${secs}`,
};

/** Radio subtitles. One speaker only. `secs` is how long a line holds after it has typed out. */
export const radio = {
  speaker: 'IPX VAULT',
  intro: {
    text: "Rule, it's the Vault. Vultures stashed your three masters on this block — the avenue, the chop shop, the cage. Bring them home.",
    secs: 4.4,
  },
  /** Hold the Block's first line: no reels, no truck, just the block. */
  introHoldout: { text: "Rule, it's the Vault. The Vultures want the whole block back. Hold it down as long as you can.", secs: 4.0 },
  contact: { text: 'They made you. Goons on foot, Buzzards in the air. Handle it.', secs: 3.2 },
  /** Indexed by reels secured − 1. */
  reel: [
    { text: 'One reel back in your hands. They felt that — more coming.', secs: 3.6 },
    { text: "Two reels. They're throwing the whole crew at you now.", secs: 3.6 },
    { text: "That's all three. The IPX truck is idling at the south end of the lot. Move.", secs: 4.5 },
  ],
  lowHealth: { text: "You're hit bad. Get behind something solid and breathe.", secs: 3.0 },
  done: { text: 'Masters are in the vault. The block is yours, Rule.', secs: 2.4 },
  waveClear: { text: (n) => `Wave ${n} down. Resupply at your feet — 9 seconds.`, secs: 3.4 },
};

export const cards = {
  pause: {
    kicker: 'Hold up',
    title: 'Paused',
    resume: 'Resume',
    settings: 'Settings',
    controls: 'Controls',
    restart: 'Restart run',
  },
  dead: {
    kicker: 'Rule down',
    title: 'Lights out',
    stats: {
      time: 'Time on the block',
      reels: 'Reels recovered', // value "n/3"
      waves: 'Waves cleared',
      kills: 'Vultures dropped',
      score: 'Score',
      best: 'Best',
    },
    retry: 'Run it back',
  },
  debrief: {
    kicker: 'Hollis, Queens · Debrief',
    title: 'The block is yours',
    stats: {
      rating: 'Certification',
      time: 'Time',
      accuracy: 'Accuracy',
      kills: 'Vultures dropped',
      retries: 'Retries',
    },
    again: 'Run it back',
  },
};

/** Debrief certification by rating points 0…5 (see config/flow.js `ratingPoints`). */
export const ratings = ['Demo', 'Mixtape', 'Single', 'Gold', 'Platinum', 'Diamond'];

/** Boot lines in the order they appear. `first` is also the static text in src/page.html. */
export const boot = {
  first: 'Waking up the block',
  render: 'Warming up the renderer',
  mats: 'Mixing brick, chrome and neon',
  props: 'Parking cars on the avenue',
  level: 'Raising the El',
  atmos: 'Lighting the block',
  fx: 'Loading tracers and smoke',
  weapon: 'Racking the Chopper',
  enemies: 'Waking the Vultures',
  wait: 'Waiting on the next train',
  ready: 'Ready',
  fatal: (error) => `Murder Inc. could not start: ${error}`,
  contextLost: 'The graphics context was lost. Reload the page to continue.',
};

/** Invented names for the block (docs/DESIGN.md section 4). No real brands except IPX. */
export const world = {
  shop: 'V&R AUTO BODY',
  storefronts: [
    'HOLLIS DELI & GROCERY',
    'CROWN & FADE BARBER',
    'PAWN & GOLD',
    'TAPES · RECORDS · CDs',
    'GOLDEN BIRD CHICKEN',
    'WINES & LIQUORS',
    'LUCKY NAILS',
    '24 HR LAUNDROMAT',
    'CHECKS CASHED',
    '99¢ PIZZA',
  ],
};
