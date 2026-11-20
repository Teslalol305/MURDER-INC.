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
    note: 'Four levels: take back the three master reels, then get them to the IPX truck. About ten minutes.',
  },
  holdout: {
    name: 'Hold the Block',
    note: 'Endless waves that keep growing. Resupply between waves. How long can you hold it down?',
  },
};

/** Difficulty keys as stored in settings → display names. Hustler is the default and the easy one. */
export const difficulties = {
  hustler: 'Hustler',
  boss: 'Boss',
  kingpin: 'Kingpin',
};

export const weapons = {
  chopper: { name: 'CHOPPER', blurb: 'Compact automatic carbine, 30 rounds' },
  nine: { name: 'NINE', blurb: '9 mm pistol, 15 rounds, never runs dry' },
  ar15: { name: 'AR-15', blurb: 'Automatic rifle, 30 rounds, flat and tight at range' },
  switch9: { name: 'SWITCH', blurb: 'Full-auto 9 mm pistol, 33 rounds, empties in two seconds' },
  rocket: { name: 'ROCKET', blurb: 'Shoulder launcher, one round at a time, clears a corner' },
  melee: { nine: 'Pistol whip', chopper: 'Rifle butt', ar15: 'Rifle butt', switch9: 'Pistol whip', rocket: 'Tube swing' },
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
    { text: 'One reel back in your hands. They felt that — more coming. Clear them out.', secs: 3.6 },
    { text: "Two reels. They're throwing the whole crew at you now. Put them down.", secs: 3.6 },
    { text: "That's the last one. Here they come — hold your ground.", secs: 3.8 },
  ],
  lowHealth: { text: "You're hit bad. Get behind something solid and breathe.", secs: 3.0 },
  done: { text: 'Masters are in the vault. The block is yours, Rule.', secs: 2.4 },
  waveClear: { text: (n) => `Wave ${n} down. Fresh ammo on the block — 9 seconds.`, secs: 3.4 },
};

/**
 * The story (src/config/story.js has the levels and the camera work, this the words).
 * Two voices: the Vault on the radio, and Rule.
 */
export const story = {
  speakers: { vault: 'IPX VAULT', rule: 'RULE' },
  /** The kicker of a level's title card, and the line over the objective on the HUD. */
  levelOf: (n, total) => `LEVEL ${n} OF ${total}`,
  stage: (n, title) => `LEVEL ${n} · ${title}`,
  /** By level id: its name, what it asks for (title card and location card), the Vault's first word in it. */
  levels: {
    avenue: {
      title: 'THE AVENUE',
      brief: 'Take back the first reel',
      go: { text: 'Reel one is down the avenue, under the El. Follow the line on the ground.', secs: 3.4 },
      clear: { text: 'Avenue is quiet. One down, Rule.', secs: 2.2 },
    },
    shop: {
      title: 'THE CHOP SHOP',
      brief: 'Take back the second reel',
      go: { text: 'Across the avenue and through the roll door. Reel two is on the shop floor.', secs: 3.4 },
      clear: { text: "Shop's yours. Two down.", secs: 2.2 },
    },
    cage: {
      title: 'THE CAGE',
      brief: 'Take back the last reel',
      go: { text: 'Out of the alley and east along the avenue. Reel three is on the court, behind the fence.', secs: 3.6 },
      clear: { text: 'The cage is empty. You have all three.', secs: 2.4 },
    },
    truck: {
      title: 'THE TRUCK',
      brief: 'Get the reels to the IPX truck',
      go: { text: "South through the lot. The truck's doors are open — don't stop for anything.", secs: 3.4 },
    },
  },
  /** The objective line, by what the level wants right now. `guided`: the guide line is on. */
  objectives: {
    reach: (code, guided) => (guided ? `Get to reel ${code} — follow the gold line` : `Get to reel ${code}`),
    grab: (glyph, code) => `Hold ${glyph} at reel ${code} to take it back`,
    clear: (n) => (n <= 1 ? 'One Vulture left — finish it' : `Clear the block — ${n} Vultures left`),
    truck: (guided) => (guided ? 'Get to the IPX truck — follow the gold line' : 'Get to the IPX truck'),
    done: 'Level clear',
  },
  banners: {
    clear: 'Level clear',
    ambush: (dir) => `Ambush — ${dir}`,
  },
  /** The closing title card. */
  end: { kicker: 'AN IPX PRODUCTION', title: 'MURDER INC.', sub: 'STARRING JA RULE' },
  skip: 'Skip',
  /** How-to lines of the first level, one at a time. `glyph` is the device's key cap. */
  /* (Short enough for one line between a phone's thumb clusters.) */
  hints: {
    aim: (glyph) => `Hold ${glyph}: your sights lock on`,
    aimTouch: 'Aim: your sights lock on',
    weapons: 'Five guns: keys 1 to 5, or the wheel',
    weaponsPad: 'Five guns: Y for the next one',
    weaponsTouch: 'Tap a gun on the bar',
    crates: 'Green crates are ammo',
  },
  /** Ammo picked up: a crate, a pouch a Vulture dropped, nothing because every gun is full. */
  pickup: {
    crate: 'Ammo: every gun topped up',
    pouch: 'Ammo picked up',
    full: 'Ammo full',
  },
  /** Cutscene lines, by scene, in the order src/config/story.js cues them. */
  scenes: {
    opening: [
      { who: 'vault', text: "Rule, it's the Vault. The Vultures hit the studio last night. They walked out with your three master reels.", secs: 2.4 },
      { who: 'vault', text: 'They stashed them right here on your block. The first one is sitting on the avenue, out in the open. They want you to see it.', secs: 2 },
      { who: 'rule', text: 'Then they want me to come get it.', secs: 2.8 },
    ],
    shop: [
      { who: 'vault', text: 'One reel back in your hands. The second is inside V&R Auto Body, the chop shop across the avenue.', secs: 2.2 },
      { who: 'vault', text: "They cut cars in there. Tonight they're cutting your records.", secs: 2.2 },
      { who: 'rule', text: 'Not my records.', secs: 2.6 },
    ],
    cage: [
      { who: 'vault', text: 'Two down. The last reel is locked in the cage: the ball court at the east end of the avenue.', secs: 2.2 },
      { who: 'vault', text: 'Every Vulture left on this block is standing on it.', secs: 2.6 },
      { who: 'rule', text: 'Good. Saves me the walk.', secs: 2.8 },
    ],
    truck: [
      { who: 'vault', text: "That's all three. The IPX truck is idling at the south end of the lot.", secs: 2.4 },
      { who: 'vault', text: "Every Vulture in Queens just heard you. Don't stop for anything.", secs: 2.4 },
      { who: 'rule', text: 'Keep the engine running.', secs: 2.6 },
    ],
    ending: [
      { who: 'vault', text: 'Masters are in the vault. The block is yours, Rule.', secs: 2.6 },
      { who: 'rule', text: 'It always was.', secs: 3 },
    ],
  },
};

export const cards = {
  pause: {
    kicker: 'Hold up',
    title: 'Paused',
    resume: 'Resume',
    settings: 'Settings',
    controls: 'Controls',
    restart: 'Restart run',
    restartLevel: 'Restart level',
    quit: 'Back to title',
  },
  dead: {
    kicker: 'Rule down',
    title: 'Lights out',
    stats: {
      time: 'Time on the block',
      level: 'Level', // value "2 of 4 · The Chop Shop"
      reels: 'Reels recovered', // value "n/3"
      waves: 'Waves cleared',
      kills: 'Vultures dropped',
      score: 'Score',
      best: 'Best',
    },
    retry: 'Run it back',
    /** The story's death card: back to the start of the level, with what Rule had when it began. */
    retryLevel: 'Retry level',
    checkpoint: (n, title) => `You go again from the start of level ${n}, ${title}.`,
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
