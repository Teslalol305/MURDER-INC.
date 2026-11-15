// Player and input tuning: body, movement, camera, health, device look rates, touch layout numbers and the
// input module's own copy. Metres, seconds, radians unless a name says otherwise.
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
  standClearance: 0.05, // headroom check starts this far under the crouched head
  footprint: 0.9, // …over this share of the body radius
  headClearance: 0.07, // the eye never rises closer than this to the top of the body (near plane vs. ceilings)
};

/** Target speeds, m/s. */
export const speed = {
  walk: 3.8,
  sprint: 6.4,
  crouch: 1.9,
  ads: 2.4, // cap while fully aimed
  backpedal: 0.82, // multiplier at full backward input
  moving: 0.3, // slower than this counts as standing still (footsteps, stride)
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
export const stride = {
  walk: 1.55,
  sprint: 2.1,
  crouch: 1.05,
  settleRate: 10, // standing still, the stride eases to the nearest whole step
  afterLanding: 0.72, // stride fraction after a landing: the next footstep follows shortly
};

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
  adsBand: [0.02, 0.98], // "in flight" = aim amount strictly between these
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
  // Stairs and kerbs: the body pops up or down a step at once and the eye follows on a critically damped
  // spring of this angular frequency (rad/s), never further behind than `max` metres. The reference has
  // no stair smoothing; frequency 0 switches it off.
  step: { frequency: 24, max: 0.5 },
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
  // Two sines per axis (rad/s): deterministic, no noise.
  freq: { pitch: [43, 72], yaw: [37, 84], roll: [30, 61] },
  onHit: { base: 0.22, perDamage: 1 / 70 },
  onBlast: { range: 28, base: 0.15, scale: 0.9, small: 0.6 }, // 0.15 + 0.9 · (1 − d / 28)², × small for a 'small' blast
  // addShake() calls smaller than `below` are a trickle (a train overhead, every frame): read as trauma
  // per second, they hold the shake at rate / decay, capped at `max`, easing in and out at `rate`.
  sustain: { below: 0.03, max: 0.6, rate: 6 },
};

export const death = {
  collapse: 0.85, // seconds for the camera to reach the floor
  eye: 0.22,
  eyeRate: 18,
  roll: 1.15,
  pitch: -0.25, // settles looking slightly down…
  pitchBounce: 0.12, // …after a small nod on the way
  slide: 5, // damp rate of the body's horizontal speed
  capsuleHeight: 0.6,
  saturation: 0.12, // post targets, eased by the game
  fade: 0.55,
};

/** Device look rates and gamepad handling (details: reference notes 01). */
export const input = {
  mouse: 0.0021, // rad per pixel × sensitivity
  mouseGlitch: 400, // single events larger than this are discarded
  mouseWake: 4, // pixels in one frame before the mouse counts as the active device again
  touch: 0.0052, // rad per CSS pixel × sensitivity
  touchStickRadius: 58,
  touchStickZone: 0.45, // left share of the screen where a touch anchors the move stick
  touchSprint: { magnitude: 0.93, forward: 0.8 },
  // Sprint lock: the stick thumb dragged this many ring radii straight up (the arrow sits at 1.66) arms it,
  // stays armed down to reach × keep, and must not be further than `side` radii off to either side.
  touchSprintLock: { reach: 1.45, keep: 0.85, side: 0.6 },
  touchQuiet: 0.8, // seconds after a touch during which mouse events are ignored (synthetic clicks)
  keyYaw: 2.1, // rad/s, not scaled by sensitivity
  keyPitch: 1.26,
  edgeYaw: 2.4,
  edgePitch: 1.2,
  edgeZoneX: 0.12,
  edgeZoneY: 0.1,
  lockTimeout: 1.2, // seconds before falling back to drag mode
  lockRetries: 3, // in drag mode a click still asks for the lock until this many clicks were refused
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
    boostDecay: 0.17,
    sprintForward: 0.55, // the sprint latch lets go when the stick's forward value drops below this
    aimSlow: 0.55, // look-rate multiplier with an enemy under the crosshair
    aimRange: 60,
    aimEvery: 0.05,
    aimRate: 14,
    probeEvery: 1, // seconds between looks for a pad while none is connected
    nav: { stick: 0.6, first: 0.38, repeat: 0.17 }, // menu navigation: threshold, first repeat, then every
  },
  // Dual-rumble effects the input module plays by itself (the weapon's own are in config/weapons.js).
  rumble: {
    hit: { base: 0.45, perDamage: 1 / 30, weak: 0.3, ms: 160 },
    blast: { range: 22, size: { small: 1, big: 1.2 }, weak: 0.8, ms: 240, msExtra: 200 },
  },
};

/** Standard-mapping gamepad buttons → actions. X (2) is Interact while a prompt shows; L3 (10) latches sprint. */
export const padButtons = {
  0: 'jump',
  1: 'crouch',
  2: 'reload',
  3: 'swap',
  4: 'crouch',
  5: 'melee',
  6: 'ads',
  7: 'fire',
  9: 'pause',
  10: 'sprint',
  11: 'melee',
  12: 'swap',
  13: 'swap',
  14: 'weapon1',
  15: 'weapon2',
};

/** KeyboardEvent.code → action. */
export const keys = {
  KeyW: 'forward',
  KeyS: 'back',
  KeyA: 'left',
  KeyD: 'right',
  Space: 'jump',
  ShiftLeft: 'sprint',
  ShiftRight: 'sprint',
  KeyC: 'crouch',
  ControlLeft: 'crouch',
  ControlRight: 'crouch',
  KeyR: 'reload',
  KeyE: 'interact',
  KeyF: 'melee',
  KeyV: 'melee',
  KeyQ: 'swap',
  Digit1: 'weapon1',
  Digit2: 'weapon2',
  Numpad1: 'weapon1',
  Numpad2: 'weapon2',
  Enter: 'fire',
  NumpadEnter: 'fire',
  Escape: 'pause',
  KeyP: 'pause',
  ArrowLeft: 'turnL',
  ArrowRight: 'turnR',
  ArrowUp: 'turnU',
  ArrowDown: 'turnD',
  KeyJ: 'turnL',
  KeyL: 'turnR',
  KeyI: 'turnU',
  KeyK: 'turnD',
};

/** MouseEvent.button → action. */
export const mouseButtons = { 0: 'fire', 1: 'melee', 2: 'ads' };

/**
 * What input.glyph(action) answers per device. `code` names the key whose printed letter replaces the
 * keyboard glyph on layouts where it differs (AZERTY prints A on the Q key).
 */
export const glyphs = {
  kbm: {
    fire: 'LMB',
    ads: 'RMB',
    jump: 'SPACE',
    sprint: 'SHIFT',
    crouch: 'C',
    reload: 'R',
    interact: 'E',
    swap: 'Q',
    weapon1: '1',
    weapon2: '2',
    melee: 'F',
    pause: 'ESC',
  },
  pad: {
    fire: 'RT',
    ads: 'LT',
    jump: 'A',
    sprint: 'L3',
    crouch: 'B',
    reload: 'X',
    interact: 'X',
    swap: 'Y',
    weapon1: '←',
    weapon2: '→',
    melee: 'RB',
    pause: 'START',
  },
  touch: {
    fire: 'FIRE',
    ads: 'AIM',
    jump: 'JUMP',
    sprint: 'STICK',
    crouch: 'DUCK',
    reload: 'RLD',
    interact: 'USE',
    swap: 'SWAP',
    weapon1: 'SWAP',
    weapon2: 'SWAP',
    melee: 'HIT',
    pause: 'II',
  },
  layoutCodes: { crouch: 'KeyC', reload: 'KeyR', interact: 'KeyE', swap: 'KeyQ', melee: 'KeyF' },
};

/**
 * On-screen buttons: [id, action, spoken name, caption]. The id names the element (`.touch-<id>`), its
 * glyph in `touchGlyphs` and its held source; `fire2` is the second, smaller trigger on the left for
 * players who aim with the right thumb. Sizes and places are in src/input.css.
 */
export const touchButtons = [
  ['fire', 'fire', 'Fire', ''],
  ['fire2', 'fire', 'Fire (left thumb)', ''],
  ['ads', 'ads', 'Aim', ''],
  ['jump', 'jump', 'Jump', ''],
  ['crouch', 'crouch', 'Crouch', ''],
  ['reload', 'reload', 'Reload', ''],
  ['swap', 'swap', 'Swap weapon', ''],
  ['melee', 'melee', 'Melee strike', ''],
  ['interact', 'interact', 'Use', 'USE'],
  ['pause', 'pause', 'Pause', ''],
];

/**
 * The glyphs on the touch controls: the inside of a 32 × 32 SVG, drawn for this game as white line art
 * (stroke = currentColor, round caps; `class="fill"` marks the few solid shapes). `sprint` is the
 * sprint-lock arrow above the move stick.
 */
export const touchGlyphs = {
  // A cartridge, nose up and to the right.
  fire:
    '<g transform="rotate(42 16 16)"><path d="M12 26.5V13.5C12 8.6 14.4 5.2 16 3.4c1.6 1.8 4 5.2 4 10.1v13z"/>' +
    '<path d="M12 14.5h8M12 22.5h8M10.6 26.5h10.8"/></g>',
  // A reticle: ring, four ticks, a dot.
  ads: '<circle cx="16" cy="16" r="8.2"/><path d="M16 2.8v6.4M16 22.8v6.4M2.8 16h6.4M22.8 16h6.4"/><circle class="fill" cx="16" cy="16" r="1.5"/>',
  // A figure in mid-leap, arms thrown up, over a mark on the ground.
  jump:
    '<circle cx="16" cy="5.4" r="2.7"/><path d="M16 9.8v7.4M16 11.6l-6-4.8M16 11.6l6-4.8"/>' +
    '<path d="M16 17.2l-4.8 2.8 1.6 4.6M16 17.2l4.8 2.8-1.6 4.6"/><path d="M9.5 29.2h13"/>',
  // A figure down on one knee.
  crouch:
    '<circle cx="20" cy="9.8" r="2.7"/><path d="M18.2 13.8l-6.8 5.8M17 15l5.6 3.4"/>' +
    '<path d="M11.4 19.6l7.6 1.6-3.4 6.2M11.4 19.6l-2.4 7.6"/><path d="M5.5 29.4h21"/>',
  // A curved box magazine with a round showing at its lips.
  reload:
    '<path d="M10.2 7.2h9.4l3.6 16.6c.3 1.3-.5 2.4-1.8 2.7l-6 1.3c-1.3.3-2.5-.6-2.8-1.9z"/>' +
    '<path d="M11.6 13.2l9.3-1.2M12.9 19.2l9.3-1.6M11 3.6h7.4"/>',
  // Two arrows passing each other.
  swap: '<path d="M6.5 11h18M19.4 6l5.6 5-5.6 5M25.5 21h-18M12.6 16l-5.6 5 5.6 5"/>',
  // A closed fist, knuckles up.
  melee:
    '<path d="M7.6 17.4v-6a2.1 2.1 0 014.2 0V9.6a2.1 2.1 0 014.2 0 2.1 2.1 0 014.2 0v1.8a2.1 2.1 0 014.2 0v8.4' +
    'c0 4-2.8 6.8-6.8 6.8h-3.2c-3.8 0-6.8-2.6-6.8-6.4z"/><path d="M11.8 11.4v4.6M16 9.6v6.4M20.2 9.6v6.4"/>' +
    '<path d="M7.6 16.8h10.2a2.3 2.3 0 010 4.6h-4"/>',
  // A master reel: flange, hub, three windows.
  interact:
    '<circle cx="16" cy="16" r="11.6"/><circle cx="16" cy="16" r="2.2"/>' +
    '<circle cx="16" cy="9.2" r="2.5"/><circle cx="10.1" cy="19.4" r="2.5"/><circle cx="21.9" cy="19.4" r="2.5"/>',
  pause: '<path class="fill" d="M10.5 8.5h3.6v15h-3.6zM17.9 8.5h3.6v15h-3.6z"/>',
  sprint: '<path d="M8.5 16.5l7.5-7.5 7.5 7.5M8.5 24.5l7.5-7.5 7.5 7.5"/>',
};

/** input.hint(): one line about how looking works right now (pause card, look-mode toasts). */
export const hints = {
  locked: 'Mouse is locked in. Esc lets it go.',
  click: 'Click the street once to lock the mouse in.',
  resume: 'Resume locks the mouse back in.',
  drag: "This browser won't lock the mouse: move it to look, rest it at a screen edge to keep turning. Click fires. Arrows or I J K L turn too.",
  pad: '',
  touch: '',
};
