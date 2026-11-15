// MURDER INC. — input (CONTRACT 6.3): keyboard + mouse, touch and gamepad behind one set of actions.
//
// Every device keeps its own held sources ("key:KeyW", "mouse:0", "pad:7", "touch:fire"); an action is
// down while any source holds it and pressed on the frame the first one arrives. Outside gameplay only
// `pause` gets through, and nothing that was pressed in a menu (the Enter that hit Resume, the pad's A)
// carries over into play. Movement keys that are still physically down when play resumes do.
//
// Look is handed over once a frame in radians, already scaled by device, sensitivity and invert:
//   mouse   0.0021 rad per pixel (pointer lock, or the unlocked cursor in the fallback)
//   touch   0.0052 rad per pixel on the look finger (and on the FIRE button's finger)
//   keys    arrows / I J K L at a fixed rate, untouched by sensitivity and invert
//   edges   in the fallback, a cursor resting near a screen edge keeps turning
//   pad     right stick through a response curve, a turn boost and the aim slow-down
// Sign convention shared with the player: look.dx > 0 turns right, look.dy > 0 looks down.
//
// Look modes: 'lock' (pointer lock) and 'drag', the fallback for browsers and frames that will not
// capture the mouse. The fallback is chosen when requestPointerLock is missing, throws, rejects, raises
// pointerlockerror or has not engaged after 1.2 s, and only while the lock has never worked in this
// session. In 'drag' a click on the street still asks again a few times, so a first refusal (no user
// gesture yet) does not stick.
//
// Touch controls are built on the first touch and live under #ui > .touch (src/input.css).
// The page root carries the state for CSS: `data-device` (kbm | pad | touch), `data-look` (lock | drag),
// the classes `is-touch` (touch scheme in use) and `in-play` (gameplay controls active).
//
// Beyond the first contract draft: input.menuNav() (gamepad menu signals), input.setPrompt(on) (an
// interaction prompt is showing: reveals the touch USE button and makes pad X mean Interact) and
// input.tap(action) (a one-frame press from the UI: a tap on a weapon slot of the HUD).
// createInput(G, env) accepts stand-ins for window / document / navigator, which is how the unit tests
// drive it without a browser.

import * as TUNING from './config/player.js';
import { clamp01, damp, lerp } from './core/util.js';

/** Actions that carry over from a key held through a pause: holding W across Resume keeps walking. */
const CARRIED = { forward: 1, back: 1, left: 1, right: 1, sprint: 1, crouch: 1, turnL: 1, turnR: 1, turnU: 1, turnD: 1 };
/** KeyboardEvent.key → code, for the few environments (remote desktops, some virtual keyboards) that send no code. */
const KEY_NAMES = {
  w: 'KeyW', a: 'KeyA', s: 'KeyS', d: 'KeyD', c: 'KeyC', r: 'KeyR', e: 'KeyE', f: 'KeyF', v: 'KeyV', q: 'KeyQ', p: 'KeyP',
  i: 'KeyI', j: 'KeyJ', k: 'KeyK', l: 'KeyL', 1: 'Digit1', 2: 'Digit2', ' ': 'Space', spacebar: 'Space', shift: 'ShiftLeft',
  control: 'ControlLeft', enter: 'Enter', escape: 'Escape', esc: 'Escape', tab: 'Tab',
  arrowleft: 'ArrowLeft', arrowright: 'ArrowRight', arrowup: 'ArrowUp', arrowdown: 'ArrowDown',
};
const codeOf = (e) => e.code || KEY_NAMES[String(e.key === undefined ? '' : e.key).toLowerCase()] || '';
/** Keys that belong to a focused button rather than to the game. */
const BUTTON_KEYS = { Space: 1, Enter: 1, NumpadEnter: 1 };
/** Touch buttons that flip on a tap instead of holding. */
const TOGGLES = { ads: 1, crouch: 1 };
const PAD_BUTTON_COUNT = 17;
const AIM_SLOW_STALE = 0.25; // seconds an aimSlow written from outside stays in charge
const EDGE_CUE_STEP = 0.05; // edge cue opacity is written in steps of this

/* ------------------------------------------------------------------------------------ pure parts */

/** Axial dead zone: nothing inside it, 0…1 rescaled beyond it. */
export function deadzone(value, zone) {
  const v = Number.isFinite(value) ? value : 0;
  const m = Math.abs(v);
  if (m <= zone) return 0;
  return Math.sign(v) * Math.min(1, (m - zone) / (1 - zone));
}

/** Gamepad look response: a·m + b·m³ of the stick magnitude (fine aim near the centre). */
export const padCurve = (m, curve) => curve[0] * m + curve[1] * m * m * m;

/**
 * Right-stick look for one frame. (x, y) are dead-zoned axes; the result is written to `out` as the
 * fraction of the full turn rate on each axis, with the curve applied to the magnitude so diagonals
 * behave like straight pushes. Returns the magnitude.
 */
export function padLook(x, y, curve, out) {
  const m = Math.min(1, Math.sqrt(x * x + y * y));
  if (m <= 0) {
    out.x = out.y = 0;
    return 0;
  }
  const k = padCurve(m, curve) / m;
  const over = Math.max(1, Math.sqrt(x * x + y * y)); // a square gate reaches 1.41 in the corners
  out.x = (x / over) * k;
  out.y = (y / over) * k;
  return m;
}

/**
 * Edge turning: how hard a cursor at `fraction` (0…1 across the screen) turns, −1…1. Zero in the
 * middle, ramping linearly from the zone line to the edge.
 */
export function edgeTurn(fraction, zone) {
  if (!(fraction >= 0 && fraction <= 1) || !(zone > 0)) return 0;
  if (fraction < zone) return -(1 - fraction / zone);
  if (fraction > 1 - zone) return (fraction - (1 - zone)) / zone;
  return 0;
}

/** Dual-rumble strengths for a blast `distance` metres away: null when it is out of range. */
export function blastRumble(distance, size, tune) {
  const scale = tune.size[size] ?? tune.size.big;
  const v = clamp01(1 - distance / tune.range) * scale;
  if (!(v > 0)) return null;
  return { strong: Math.min(1, v), weak: Math.min(1, v * tune.weak), ms: tune.ms + tune.msExtra * Math.min(1, v) };
}

/* ---------------------------------------------------------------------------------------- module */

export function createInput(G, env = {}) {
  const win = env.window || (typeof window !== 'undefined' ? window : null);
  const doc = env.document || (typeof document !== 'undefined' ? document : null);
  const nav = env.navigator || (typeof navigator !== 'undefined' ? navigator : null);
  const root = doc && doc.documentElement ? doc.documentElement : null;
  const ui = doc && typeof doc.getElementById === 'function' ? doc.getElementById('ui') : null;
  const canvas =
    (G.renderer && G.renderer.domElement) || (doc && typeof doc.getElementById === 'function' && doc.getElementById('view')) || null;

  const override = (G.config && G.config.player) || {};
  const T = { ...TUNING.input, ...override.input };
  const P = { ...TUNING.input.pad, ...(override.input && override.input.pad) };
  const KEYS = override.keys || TUNING.keys;
  const MOUSE = override.mouseButtons || TUNING.mouseButtons;
  const PAD = override.padButtons || TUNING.padButtons;
  const HINTS = { ...TUNING.hints, ...override.hints };
  const GLYPHS = {
    kbm: { ...TUNING.glyphs.kbm },
    pad: TUNING.glyphs.pad,
    touch: TUNING.glyphs.touch,
  };

  const seconds = () => (win && win.performance && typeof win.performance.now === 'function' ? win.performance.now() : Date.now()) / 1000;
  const later = (fn, ms) => (win && typeof win.setTimeout === 'function' ? win.setTimeout(fn, ms) : setTimeout(fn, ms));
  const cancel = (id) => (win && typeof win.clearTimeout === 'function' ? win.clearTimeout(id) : clearTimeout(id));
  const emit = (name, payload) => G.events && G.events.emit(name, payload);
  const listen = (target, type, fn, opts) => {
    if (target && typeof target.addEventListener === 'function') target.addEventListener(type, fn, opts);
  };

  /* ------------------------------------------------------------------------------ action state */

  const sources = new Map(); // held source → action
  const held = Object.create(null); // action → number of sources holding it
  const pressedNow = Object.create(null); // edges of the current frame
  const releasedNow = Object.create(null);
  const keysDown = new Map(); // keys physically down right now (also while gameplay is off): code → action
  let gameplay = true; // until the game says otherwise

  // Outside gameplay only `pause` gets through.
  const open = (action) => gameplay || action === 'pause';

  function press(source, action) {
    if (!open(action) || sources.has(source)) return false;
    sources.set(source, action);
    held[action] = (held[action] || 0) + 1;
    if (held[action] === 1) pressedNow[action] = true;
    return true;
  }

  function release(source) {
    const action = sources.get(source);
    if (action === undefined) return;
    sources.delete(source);
    if (--held[action] === 0) releasedNow[action] = true;
  }

  /**
   * Takes inputs away (focus lost, gameplay off, mouse freed, pad unplugged) rather than seeing them let
   * go: unlike a normal release, the press edge of this frame goes too, so nothing fires after the fact.
   */
  function drop(test) {
    for (const source of [...sources.keys()]) {
      if (!test(source)) continue;
      const action = sources.get(source);
      release(source);
      if (!(held[action] > 0)) pressedNow[action] = false;
    }
  }

  const everything = () => true;

  /** A press with no hold behind it (mouse wheel). */
  function pulse(action) {
    if (open(action) && !(held[action] > 0)) pressedNow[action] = true;
  }

  const isHeld = (action) => held[action] > 0;

  // Presses asked for by the UI (a tapped weapon slot). They wait for the next update, so a tap made
  // late in a frame (from hud.update, after the weapon has run) is not wiped by endFrame() unread.
  const taps = [];
  function tap(action) {
    if (typeof action === 'string' && action && taps.length < 16) taps.push(action);
  }

  /* ----------------------------------------------------------------------------------- the API */

  let assist = 1; // aim slow-down computed here…
  let assistTimer = 0;
  let assistTarget = 1;
  let outsideSlow = 1; // …unless another module keeps writing input.aimSlow
  let outsideAge = Infinity;

  const menu = { x: 0, y: 0, accept: false, back: false, start: false };

  const input = {
    move: { x: 0, y: 0 },
    look: { dx: 0, dy: 0 },
    locked: false,
    mode: 'lock',
    device: 'kbm',
    touch: false,
    sensitivity: 1,
    invertY: false,
    /**
     * Gamepad look-rate multiplier. Written by the weapon (aim assist); when nothing writes it, the input
     * module works it out itself from enemies.aimTarget(). Always 1 on other devices.
     */
    get aimSlow() {
      if (input.device !== 'pad') return 1;
      return outsideAge < AIM_SLOW_STALE ? outsideSlow : assist;
    },
    set aimSlow(value) {
      if (!Number.isFinite(value)) return;
      outsideSlow = clamp01(value);
      outsideAge = 0;
    },
    // A press that came and went between two frames still reads as down for that one frame.
    down: (action) => open(action) && (held[action] > 0 || pressedNow[action] === true),
    pressed: (action) => open(action) && pressedNow[action] === true,
    released: (action) => open(action) && releasedNow[action] === true,
    requestLock: () => requestLock(false),
    exitLock,
    setGameplay,
    setPrompt,
    tap,
    glyph: (action) => GLYPHS[input.device][action] || '',
    hint,
    menuNav: () => menu,
    rumble,
    update,
    endFrame,
  };

  /* ----------------------------------------------------------------------------- device, state */

  function setRootState() {
    if (!root) return;
    if (root.dataset) {
      root.dataset.device = input.device;
      root.dataset.look = input.mode;
    }
    if (root.classList) {
      root.classList.toggle('is-touch', input.touch);
      root.classList.toggle('in-play', gameplay);
    }
  }

  /** The device that just produced real input becomes the active one. */
  function wake(device) {
    let touchChanged = false;
    if (device === 'touch' && !input.touch) {
      input.touch = touchChanged = true;
      // Fingers drag to look: nobody waits for a pointer lock now. Saying so before the lock is given
      // back keeps the game from reading its loss as "the player tabbed away" and pausing.
      const silent = !input.locked && input.mode === 'drag'; // nothing changes for the listeners
      input.mode = 'drag';
      if (input.locked) exitLock(); // announces through pointerlockchange
      else if (!silent) announce();
      buildTouch();
    } else if (device === 'kbm' && input.touch) {
      // A mouse or a keyboard on a touch-screen laptop: the on-screen controls step aside.
      input.touch = false;
      touchChanged = true;
      dropTouches();
      const mode = fellBack && !everLocked ? 'drag' : 'lock';
      if (mode !== input.mode) {
        input.mode = mode;
        announce();
      }
    }
    const deviceChanged = input.device !== device;
    if (!deviceChanged && !touchChanged) return;
    input.device = device;
    if (device !== 'pad') {
      assist = assistTarget = 1;
      boost = 0;
    }
    setRootState();
    showTouch();
    if (deviceChanged) emit('input:device', { device });
  }

  let promptOn = false;

  /** An interaction prompt is (not) showing: the touch USE button appears, pad X means Interact. */
  function setPrompt(on) {
    on = !!on;
    if (on === promptOn) return;
    promptOn = on;
    if (layer && layer.classList) layer.classList.toggle('has-prompt', on);
    if (!on) release('touch:interact');
  }

  // The HUD prompt is the one place that knows a reel is in reach. Until whoever shows it calls
  // input.setPrompt() itself, listen in on hud.prompt(): cheap, and exact.
  let tappedHud = null;
  function tapHud() {
    const hud = G.hud;
    if (!hud || hud === tappedHud || typeof hud.prompt !== 'function') return;
    tappedHud = hud;
    const show = hud.prompt;
    try {
      hud.prompt = function prompt(spec) {
        setPrompt(!!spec);
        return show.apply(this, arguments);
      };
    } catch {
      /* a frozen HUD object: it has to call input.setPrompt() itself */
    }
  }

  function setGameplay(on) {
    on = !!on;
    if (on === gameplay) return;
    gameplay = on;
    if (on) {
      // Whatever still has focus from the menu must not swallow Space, or be clicked by it.
      const focus = doc && doc.activeElement;
      if (focus && focus !== (doc && doc.body) && focus !== canvas && typeof focus.blur === 'function' && /^(BUTTON|A)$/.test(focus.tagName || '')) {
        focus.blur();
      }
      for (const [code, action] of keysDown) if (CARRIED[action]) press(`key:${code}`, action);
      edgeArmed = false;
    } else {
      drop(everything);
      for (const action in pressedNow) if (action !== 'pause') pressedNow[action] = false;
      taps.length = 0;
      dropTouches();
      latch = false;
      mouseX = mouseY = touchX = touchY = 0;
      setPrompt(false);
    }
    setRootState();
    showTouch();
    showEdges(0, 0);
  }

  function hint() {
    if (input.touch || input.device === 'touch') return HINTS.touch;
    if (input.device === 'pad') return HINTS.pad;
    if (input.mode === 'drag') return HINTS.drag;
    if (input.locked) return HINTS.locked;
    return G.game && G.game.state === 'paused' ? HINTS.resume : HINTS.click;
  }

  /* ------------------------------------------------------------------------------ pointer lock */

  let everLocked = false;
  let fellBack = false; // drag mode was chosen because the lock would not come
  let wantLock = false; // the game asked for the mouse and has not given it back
  let lockPending = false;
  let lockByClick = false; // the pending request came from a click on the street
  let lockTimer = 0;
  let clickRefusals = 0; // requests made from a real click that still failed

  const announce = () => emit('input:lock', { locked: input.locked, mode: input.mode });

  /** The lock will not come: fall back to drag mode, but only while it has never worked. */
  function useDrag() {
    if (everLocked || input.mode === 'drag') return;
    fellBack = true;
    input.mode = 'drag';
    setRootState();
    announce();
  }

  function lockFailed() {
    if (!lockPending) return;
    lockPending = false;
    cancel(lockTimer);
    // A request without a user gesture behind it (autostart, a start from the gamepad) is refused by
    // every browser: only a refused click says something about this page.
    if (lockByClick) clickRefusals++;
    useDrag();
  }

  function requestLock(byClick = false) {
    wantLock = true;
    if (!canvas || input.locked || lockPending || input.touch) return;
    if (typeof canvas.requestPointerLock !== 'function') {
      useDrag();
      return;
    }
    lockPending = true;
    lockByClick = byClick === true;
    cancel(lockTimer);
    lockTimer = later(lockFailed, T.lockTimeout * 1000);
    try {
      const asked = canvas.requestPointerLock();
      if (asked && typeof asked.then === 'function') asked.then(null, lockFailed);
    } catch {
      lockFailed();
    }
  }

  function exitLock() {
    wantLock = false;
    lockPending = false;
    cancel(lockTimer);
    if (doc && doc.pointerLockElement && typeof doc.exitPointerLock === 'function') doc.exitPointerLock();
  }

  function onLockChange() {
    const locked = !!canvas && doc.pointerLockElement === canvas;
    if (locked === input.locked) return;
    input.locked = locked;
    lockPending = false;
    cancel(lockTimer);
    if (locked) {
      everLocked = true;
      if (!input.touch) input.mode = 'lock';
      setRootState();
      announce();
      // A grant that arrives after the game gave the mouse back (paused meanwhile) is handed back.
      if (!wantLock && typeof doc.exitPointerLock === 'function') doc.exitPointerLock();
    } else {
      // The mouse is free: buttons held on the street would stick. Keys are kept.
      drop((source) => source.startsWith('mouse:'));
      announce();
    }
  }

  /* ---------------------------------------------------------------------------- keyboard, mouse */

  let mouseX = 0; // pixels since the last update
  let mouseY = 0;
  let mouseTravel = 0; // pixels moved since the last update, whatever the direction
  let cursorX = 0;
  let cursorY = 0;
  let cursorIn = false; // a real cursor is over the page
  let edgeArmed = false; // the cursor has been mid-screen since gameplay began
  let lastWheel = -Infinity;
  let lastTouch = -Infinity;

  const typing = (el) => !!el && /^(INPUT|SELECT|TEXTAREA)$/.test(el.tagName || '');
  const onButton = (el) => !!el && (el.tagName || '') === 'BUTTON';
  /** Mouse events right after a touch are the browser's stand-ins for it. */
  const afterTouch = () => seconds() - lastTouch < T.touchQuiet;

  function onKeyDown(e) {
    const code = codeOf(e);
    const action = KEYS[code];
    if (!action) {
      if (gameplay && code === 'Tab') e.preventDefault(); // focus stays on the game
      return;
    }
    if (e.metaKey || e.altKey || typing(e.target)) return;
    if (BUTTON_KEYS[code] && (onButton(e.target) || onButton(doc && doc.activeElement))) return;
    // Space must not scroll, Ctrl (crouch) + R must not reload the page, Ctrl + S must not save it.
    if (gameplay && action !== 'pause') e.preventDefault();
    if (e.repeat) return;
    wake('kbm');
    keysDown.set(code, action);
    press(`key:${code}`, action);
  }

  function onKeyUp(e) {
    const code = codeOf(e);
    keysDown.delete(code);
    release(`key:${code}`);
  }

  function onMouseMove(e) {
    if (afterTouch()) return;
    if (e.isTrusted !== false) {
      // Scripted events carry no cursor position worth trusting.
      cursorX = e.clientX;
      cursorY = e.clientY;
      cursorIn = true;
    }
    const dx = e.movementX || 0;
    const dy = e.movementY || 0;
    if (Math.abs(dx) > T.mouseGlitch || Math.abs(dy) > T.mouseGlitch) return; // pointer-lock hiccup
    // A nudge of the desk does not take the device back from a controller; a few pixels in one frame do.
    mouseTravel += Math.abs(dx) + Math.abs(dy);
    if (mouseTravel >= T.mouseWake) wake('kbm');
    if (!gameplay) return;
    mouseX += dx;
    mouseY += dy;
  }

  function onCanvasMouseDown(e) {
    if (afterTouch()) return;
    wake('kbm');
    if (!gameplay) return;
    // The first click both captures and fires. In drag mode it keeps asking, until a few clicks were refused.
    if (!input.locked && (input.mode === 'lock' || clickRefusals < T.lockRetries)) requestLock(true);
    const action = MOUSE[e.button];
    if (action) press(`mouse:${e.button}`, action);
    // No auto-scroll cursor on the middle button, no history navigation on the thumb buttons.
    if (e.button === 1 || e.button > 2) e.preventDefault();
  }

  function onMouseUp(e) {
    release(`mouse:${e.button}`);
    if (gameplay && e.button > 2 && e.cancelable !== false) e.preventDefault(); // "back" must not leave the game
  }

  function onWheel(e) {
    if (!gameplay) return;
    if (e.cancelable !== false) e.preventDefault(); // no page scroll, no Ctrl + wheel zoom in a crouch
    if (Math.abs(e.deltaY) < 1) return;
    const now = seconds();
    if (now - lastWheel < T.wheelDebounce) return;
    lastWheel = now;
    wake('kbm');
    pulse('swap');
  }

  function dropAll() {
    drop(everything);
    keysDown.clear();
    dropTouches();
    latch = false;
    cursorIn = false;
  }

  /* ------------------------------------------------------------------------------------- touch */

  let layer = null; // #ui > .touch
  let stickEl = null;
  let nubEl = null;
  let pauseEl = null;
  const buttons = []; // {el, id, action, finger, x, y}
  const toggled = Object.create(null); // toggle action → on
  let stickFinger = null;
  let stickX = 0; // anchor
  let stickY = 0;
  let stickRadius = T.touchStickRadius;
  let stickMoveX = 0; // output, −1…1
  let stickMoveY = 0;
  let stickSprint = false;
  let runArmed = false; // the stick finger is up on the sprint-lock arrow: letting go there keeps running
  let runLocked = false; // running forward with no finger on the stick
  let runFinger = null; // a finger that went down on the arrow itself
  let lookFinger = null;
  let lookX = 0;
  let lookY = 0;
  let touchX = 0; // look pixels since the last update
  let touchY = 0;

  function make(tag, className) {
    const el = doc.createElement(tag);
    el.className = className;
    return el;
  }

  /** A glyph from config/player.js as an inline SVG (line art in the current colour). */
  function glyphOf(name) {
    const icon = make('span', 'touch-glyph');
    icon.setAttribute('aria-hidden', 'true');
    icon.innerHTML = `<svg viewBox="0 0 32 32" focusable="false">${TUNING.touchGlyphs[name] || ''}</svg>`;
    return icon;
  }

  function buildTouch() {
    if (layer || !doc || !ui || typeof doc.createElement !== 'function') return;
    layer = make('div', 'touch');
    layer.hidden = true;
    if (promptOn) layer.classList.add('has-prompt');

    // The move stick: a ring, a knob, and the sprint-lock arrow above them.
    stickEl = make('div', 'touch-stick');
    nubEl = make('div', 'touch-stick-nub');
    const ring = make('div', 'touch-stick-ring');
    ring.setAttribute('aria-hidden', 'true');
    nubEl.setAttribute('aria-hidden', 'true');
    const arrow = make('div', 'touch-sprint');
    arrow.setAttribute('role', 'button');
    arrow.setAttribute('aria-label', 'Sprint lock');
    arrow.setAttribute('aria-pressed', 'false');
    arrow.append(glyphOf('sprint'));
    listen(arrow, 'touchstart', onArrowStart, { passive: false });
    listen(arrow, 'touchend', onArrowEnd, { passive: false });
    listen(arrow, 'touchcancel', onArrowEnd, { passive: false });
    listen(arrow, 'contextmenu', (e) => e.preventDefault());
    stickEl.append(ring, nubEl, arrow);
    stickEl.arrow = arrow;
    layer.append(stickEl);

    for (const [id, action, name, caption] of TUNING.touchButtons) {
      const el = make('div', `touch-btn touch-${id}`);
      el.setAttribute('role', 'button');
      el.setAttribute('aria-label', name);
      if (TOGGLES[action]) el.setAttribute('aria-pressed', 'false');
      el.append(glyphOf(action));
      if (caption) {
        const text = make('span', 'touch-label');
        text.textContent = caption;
        el.append(text);
      }
      const button = { el, id, action, finger: null, x: 0, y: 0 };
      buttons.push(button);
      if (id === 'pause') pauseEl = el;
      listen(el, 'touchstart', (e) => onButtonStart(e, button), { passive: false });
      listen(el, 'touchmove', (e) => onButtonMove(e, button), { passive: false });
      listen(el, 'touchend', (e) => onButtonEnd(e, button), { passive: false });
      listen(el, 'touchcancel', (e) => onButtonEnd(e, button), { passive: false });
      listen(el, 'contextmenu', (e) => e.preventDefault());
      layer.append(el);
    }
    ui.append(layer);
    showTouch();
  }

  /**
   * A HUD that draws its own pause button (the v2 HUD has one beside the minimap) makes ours a double:
   * it steps aside. The HUD says so with `data-hud-pause` on <html>, or simply by having a control
   * labelled "Pause" somewhere under #ui.
   */
  function yieldPause() {
    if (!pauseEl || !ui || typeof ui.querySelector !== 'function') return;
    let theirs = !!(root && root.dataset && root.dataset.hudPause !== undefined);
    if (!theirs) {
      try {
        theirs = !!ui.querySelector(':scope > :not(.touch) [aria-label="Pause" i], :scope > :not(.touch) [data-action="pause"]');
      } catch {
        theirs = false; // a selector this browser does not know: ours stays
      }
    }
    if (layer.classList) layer.classList.toggle('no-pause', theirs);
  }

  /** The overlay shows only while gameplay controls are active and touch is the device in use. */
  function showTouch() {
    if (!layer) return;
    const show = gameplay && input.touch && input.device === 'touch';
    if (show && layer.hidden) yieldPause();
    layer.hidden = !show;
  }

  function setLatched(button, on) {
    toggled[button.action] = on;
    if (button.el.classList) button.el.classList.toggle('is-latched', on);
    button.el.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (on) press(`touch:${button.id}`, button.action);
    else release(`touch:${button.id}`);
  }

  function onButtonStart(e, button) {
    lastTouch = seconds();
    if (e.cancelable !== false) e.preventDefault();
    if (button.finger !== null || !e.changedTouches || !e.changedTouches.length) return;
    const t = e.changedTouches[0];
    button.finger = t.identifier;
    button.x = t.clientX;
    button.y = t.clientY;
    if (button.el.classList) button.el.classList.add('is-on');
    if (TOGGLES[button.action]) setLatched(button, !toggled[button.action]);
    else press(`touch:${button.id}`, button.action);
  }

  function onButtonMove(e, button) {
    lastTouch = seconds();
    if (e.cancelable !== false) e.preventDefault();
    if (button.action !== 'fire' || button.finger === null) return;
    // Hold FIRE and drag: the same finger keeps tracking the target.
    for (let i = 0; i < e.changedTouches.length; i++) {
      const t = e.changedTouches[i];
      if (t.identifier !== button.finger) continue;
      if (gameplay) {
        touchX += t.clientX - button.x;
        touchY += t.clientY - button.y;
      }
      button.x = t.clientX;
      button.y = t.clientY;
    }
  }

  function onButtonEnd(e, button) {
    lastTouch = seconds();
    if (e.cancelable !== false) e.preventDefault();
    for (let i = 0; i < e.changedTouches.length; i++) {
      if (e.changedTouches[i].identifier !== button.finger) continue;
      button.finger = null;
      if (button.el.classList) button.el.classList.remove('is-on');
      if (!TOGGLES[button.action]) release(`touch:${button.id}`);
    }
  }

  function placeStick(dx, dy) {
    if (nubEl && nubEl.style) nubEl.style.transform = `translate3d(${dx.toFixed(1)}px, ${dy.toFixed(1)}px, 0)`;
  }

  function setStickSprint(on) {
    if (on === stickSprint) return;
    stickSprint = on;
    if (on) press('touch:sprint', 'sprint');
    else release('touch:sprint');
    if (stickEl && stickEl.classList) stickEl.classList.toggle('is-sprint', on);
  }

  function setRunArmed(on) {
    if (on === runArmed) return;
    runArmed = on;
    if (stickEl && stickEl.classList) stickEl.classList.toggle('is-armed', on);
  }

  /** Sprint lock: Rule keeps running forward with no finger on the stick. */
  function setRunLocked(on) {
    if (on === runLocked) return;
    runLocked = on;
    if (on) {
      stickMoveX = 0;
      stickMoveY = 1;
      placeStick(0, -stickRadius);
    } else if (stickFinger === null) {
      stickMoveX = stickMoveY = 0;
      placeStick(0, 0);
    }
    setStickSprint(on || (stickFinger !== null && stickSprint));
    if (stickEl) {
      if (stickEl.classList) stickEl.classList.toggle('is-locked', on);
      if (stickEl.arrow) stickEl.arrow.setAttribute('aria-pressed', on ? 'true' : 'false');
    }
  }

  function moveStick(x, y) {
    let dx = (x - stickX) / stickRadius;
    let dy = (y - stickY) / stickRadius;
    const m = Math.sqrt(dx * dx + dy * dy);
    // Dragged on past the ring, up onto the arrow: sprint lock is armed (and stays armed until the
    // thumb has come most of the way back).
    const L = T.touchSprintLock;
    const reach = runArmed ? L.reach * L.keep : L.reach;
    setRunArmed(-dy > reach && Math.abs(dx) < L.side);
    if (m > 1) {
      dx /= m;
      dy /= m;
    }
    stickMoveX = dx;
    stickMoveY = -dy; // up the screen is forward
    placeStick(dx * stickRadius, dy * stickRadius);
    // Pushed all the way forward: sprint.
    setStickSprint(Math.min(1, m) > T.touchSprint.magnitude && stickMoveY > T.touchSprint.forward);
  }

  /** The stick's finger is gone. Lifted off the arrow, the run goes on; otherwise everything stops. */
  function dropStick(lock = false) {
    stickFinger = null;
    const keep = lock && runArmed && gameplay;
    setRunArmed(false);
    if (stickEl) {
      if (stickEl.classList) stickEl.classList.remove('is-active');
      if (stickEl.style) stickEl.style.left = stickEl.style.top = stickEl.style.bottom = '';
      // Back at rest the ring has its resting size again.
      stickRadius = stickEl.offsetWidth > 0 ? stickEl.offsetWidth / 2 : T.touchStickRadius;
    }
    if (keep) {
      runLocked = false; // (re-enter, so the knob is placed for the resting ring)
      setRunLocked(true);
      return;
    }
    runLocked = false;
    if (stickEl) {
      if (stickEl.classList) stickEl.classList.remove('is-locked');
      if (stickEl.arrow) stickEl.arrow.setAttribute('aria-pressed', 'false');
    }
    stickMoveX = stickMoveY = 0;
    setStickSprint(false);
    placeStick(0, 0);
  }

  /** A tap on the arrow itself switches the sprint lock on and off. */
  function onArrowStart(e) {
    lastTouch = seconds();
    if (e.cancelable !== false) e.preventDefault();
    if (typeof e.stopPropagation === 'function') e.stopPropagation();
    if (!gameplay || runFinger !== null || stickFinger !== null || !e.changedTouches || !e.changedTouches.length) return;
    runFinger = e.changedTouches[0].identifier;
    setRunLocked(!runLocked);
  }

  function onArrowEnd(e) {
    lastTouch = seconds();
    if (e.cancelable !== false) e.preventDefault();
    for (let i = 0; e.changedTouches && i < e.changedTouches.length; i++) {
      if (e.changedTouches[i].identifier === runFinger) runFinger = null;
    }
  }

  /** Lets go of every finger and every latch (gameplay off, focus lost, another device took over). */
  function dropTouches() {
    dropStick();
    runFinger = null;
    lookFinger = null;
    touchX = touchY = 0;
    for (const button of buttons) {
      button.finger = null;
      if (button.el.classList) button.el.classList.remove('is-on');
      if (TOGGLES[button.action] && toggled[button.action]) setLatched(button, false);
    }
    drop((source) => source.startsWith('touch:'));
  }

  function onAnyTouch() {
    lastTouch = seconds();
    wake('touch');
  }

  function onCanvasTouchStart(e) {
    lastTouch = seconds();
    if (!gameplay) return; // menus get their taps untouched
    if (e.cancelable !== false) e.preventDefault();
    const width = (win && win.innerWidth) || 1;
    for (let i = 0; i < e.changedTouches.length; i++) {
      const t = e.changedTouches[i];
      if (stickFinger === null && t.clientX < width * T.touchStickZone) {
        // The left thumb, anywhere on its side: the stick appears under it (and takes a locked run back).
        if (runLocked) setRunLocked(false);
        stickFinger = t.identifier;
        stickX = t.clientX;
        stickY = t.clientY;
        if (stickEl) {
          const size = stickEl.offsetWidth;
          stickRadius = size > 0 ? size / 2 : T.touchStickRadius;
          if (stickEl.style) {
            stickEl.style.left = `${stickX}px`;
            stickEl.style.top = `${stickY}px`;
            stickEl.style.bottom = 'auto';
          }
          if (stickEl.classList) stickEl.classList.add('is-active');
        }
        moveStick(stickX, stickY);
      } else if (lookFinger === null) {
        lookFinger = t.identifier;
        lookX = t.clientX;
        lookY = t.clientY;
      }
    }
  }

  function onCanvasTouchMove(e) {
    lastTouch = seconds();
    if (!gameplay) return;
    if (e.cancelable !== false) e.preventDefault();
    for (let i = 0; i < e.changedTouches.length; i++) {
      const t = e.changedTouches[i];
      if (t.identifier === stickFinger) {
        moveStick(t.clientX, t.clientY);
      } else if (t.identifier === lookFinger) {
        touchX += t.clientX - lookX;
        touchY += t.clientY - lookY;
        lookX = t.clientX;
        lookY = t.clientY;
      }
    }
  }

  function onCanvasTouchEnd(e) {
    lastTouch = seconds();
    for (let i = 0; i < e.changedTouches.length; i++) {
      const id = e.changedTouches[i].identifier;
      if (id === stickFinger) dropStick(e.type !== 'touchcancel');
      else if (id === lookFinger) lookFinger = null;
    }
  }

  /* ----------------------------------------------------------------------------------- gamepad */

  const padHeld = new Uint8Array(PAD_BUTTON_COUNT);
  const padEdge = new Uint8Array(PAD_BUTTON_COUNT); // went down this frame
  const stickOut = { x: 0, y: 0 };
  let pad = null; // the pad polled this frame
  let padKnown = false; // a pad has shown up (stop polling blind)
  let padBlocked = false; // getGamepads() is not allowed here
  let probe = 0;
  let padMoveX = 0;
  let padMoveY = 0;
  let padLookX = 0; // fraction of the full turn rate, after curve and boost
  let padLookY = 0;
  let boost = 0;
  let latch = false; // sprint, latched by L3
  let navY = 0; // direction held on the menu's vertical axis
  let navX = 0;
  let navTimer = 0;
  let rumbleUntil = -Infinity;
  let rumbleLevel = 0;

  function findPad() {
    if (padBlocked || !nav || typeof nav.getGamepads !== 'function') return null;
    let pads;
    try {
      pads = nav.getGamepads();
    } catch {
      padBlocked = true; // a frame without the gamepad permission: never ask again
      return null;
    }
    let first = null;
    for (let i = 0; pads && i < pads.length; i++) {
      const p = pads[i];
      if (!p || p.connected === false || !p.buttons || !p.axes || p.buttons.length < 10 || p.axes.length < 4) continue;
      if (p.mapping === 'standard') return p;
      if (!first) first = p;
    }
    return first;
  }

  function padGone() {
    pad = null;
    padHeld.fill(0);
    padEdge.fill(0);
    padMoveX = padMoveY = padLookX = padLookY = boost = 0;
    latch = false;
    drop((source) => source.startsWith('pad:'));
    if (input.device === 'pad') wake(input.touch ? 'touch' : 'kbm');
  }

  function padDown(index) {
    if (index === 10) {
      // L3 latches sprint: one click starts it, easing off the stick (or a second click) ends it.
      if (!gameplay) return;
      latch = !latch;
      if (latch) press('pad:sprint', 'sprint');
      else release('pad:sprint');
      return;
    }
    let action = PAD[index];
    if (!action) return;
    // X reloads, unless a prompt is showing at the moment of the press: then it interacts, for that whole hold.
    if (index === 2 && promptOn) action = 'interact';
    press(`pad:${index}`, action);
  }

  function pollPad(dt) {
    padEdge.fill(0);
    menu.x = menu.y = 0;
    menu.accept = menu.back = menu.start = false;
    if (!padKnown) {
      // No pad yet: look only now and then (getGamepads allocates).
      probe -= dt;
      if (probe > 0) return;
      probe = P.probeEvery;
    }
    const found = findPad();
    if (!found) {
      if (pad) padGone();
      padKnown = false;
      return;
    }
    padKnown = true;
    pad = found;

    let active = false;
    const count = Math.min(PAD_BUTTON_COUNT, pad.buttons.length);
    for (let i = 0; i < count; i++) {
      const b = pad.buttons[i];
      const on = !!b && (b.pressed === true || b.value > P.trigger) ? 1 : 0;
      if (on) active = true;
      if (on === padHeld[i]) continue;
      padHeld[i] = on;
      if (on) {
        padEdge[i] = 1;
        padDown(i);
      } else {
        release(`pad:${i}`);
      }
    }

    const lx = deadzone(pad.axes[0], P.deadzone);
    const ly = deadzone(pad.axes[1], P.deadzone);
    const rx = deadzone(pad.axes[2], P.deadzone);
    const ry = deadzone(pad.axes[3], P.deadzone);
    if (lx !== 0 || ly !== 0 || rx !== 0 || ry !== 0) active = true;
    if (active) wake('pad');

    padMoveX = lx;
    padMoveY = -ly; // stick up is forward
    if (latch && (padMoveY < P.sprintForward || !gameplay)) {
      latch = false;
      release('pad:sprint');
    }

    // Right stick: response curve on the magnitude, and a boost that builds while it is held at the rim.
    const m = padLook(rx, ry, P.curve, stickOut);
    boost = m > P.boostFrom ? Math.min(1, boost + dt / P.boostTime) : Math.max(0, boost - dt / P.boostDecay);
    const fast = lerp(1, P.boost, boost);
    padLookX = stickOut.x * fast;
    padLookY = stickOut.y * fast;

    pollMenu(dt);
  }

  /** Menu signals while gameplay is off: accept / back / start edges, and a direction with key repeat. */
  function pollMenu(dt) {
    if (gameplay || !pad) {
      navX = navY = 0;
      return;
    }
    menu.accept = padEdge[0] === 1;
    menu.back = padEdge[1] === 1;
    menu.start = padEdge[9] === 1;
    const sx = Number.isFinite(pad.axes[0]) ? pad.axes[0] : 0;
    const sy = Number.isFinite(pad.axes[1]) ? pad.axes[1] : 0;
    const y = (padHeld[13] || sy > P.nav.stick ? 1 : 0) - (padHeld[12] || sy < -P.nav.stick ? 1 : 0);
    const x = (padHeld[15] || sx > P.nav.stick ? 1 : 0) - (padHeld[14] || sx < -P.nav.stick ? 1 : 0);
    if (y !== navY) {
      navY = y;
      navTimer = P.nav.first;
      menu.y = y;
    } else if (y !== 0) {
      navTimer -= dt;
      if (navTimer <= 0) {
        navTimer += P.nav.repeat;
        menu.y = y;
      }
    }
    if (x !== navX) {
      navX = x;
      menu.x = x; // left / right adjust once per push
    }
  }

  /** Aim slow-down for the pad: with an enemy under the crosshair the stick turns the view at 55 %. */
  function updateAssist(dt) {
    outsideAge += dt;
    if (input.device !== 'pad' || !gameplay) {
      assist = assistTarget = 1;
      return;
    }
    assistTimer -= dt;
    if (assistTimer <= 0) {
      assistTimer = P.aimEvery;
      assistTarget = 1;
      const { player, enemies } = G;
      if (player && player.alive !== false && player.eye && enemies && typeof enemies.aimTarget === 'function') {
        try {
          if (enemies.aimTarget(player.eye, player.forward, P.aimRange)) assistTarget = P.aimSlow;
        } catch {
          assistTarget = 1;
        }
      }
    }
    assist = damp(assist, assistTarget, P.aimRate, dt);
  }

  function rumble(strong, weak, ms) {
    if (input.device !== 'pad' || !pad) return;
    const motor = pad.vibrationActuator;
    if (!motor || typeof motor.playEffect !== 'function') return;
    const s = clamp01(Number(strong) || 0);
    const w = clamp01(Number(weak) || 0);
    const length = Math.max(0, Math.min(2000, Number(ms) || 0));
    if (length === 0 || (s === 0 && w === 0)) return;
    // A light tap (a round fired) does not cut a heavy one (a blast) short.
    const now = seconds();
    const level = Math.max(s, w * 0.5);
    if (now < rumbleUntil && level < rumbleLevel * 0.7) return;
    rumbleUntil = now + length / 1000;
    rumbleLevel = level;
    try {
      const played = motor.playEffect('dual-rumble', { startDelay: 0, duration: length, weakMagnitude: w, strongMagnitude: s });
      if (played && typeof played.then === 'function') played.then(null, () => {});
    } catch {
      /* a pad without the motors it advertises */
    }
  }

  /* ---------------------------------------------------------------------------------- edge cue */

  let edges = null; // {l, r, t, b} strips shown while the cursor's edge turn is at work
  const edgeShown = { l: 0, r: 0, t: 0, b: 0 };

  function showEdge(side, amount) {
    const level = Math.round(amount / EDGE_CUE_STEP) * EDGE_CUE_STEP;
    if (edgeShown[side] === level) return;
    edgeShown[side] = level;
    if (edges[side].style) edges[side].style.opacity = level.toFixed(2);
  }

  function showEdges(ex, ey) {
    if (!edges) {
      if ((ex === 0 && ey === 0) || !doc || !ui || typeof doc.createElement !== 'function') return;
      const box = make('div', 'look-edges');
      box.setAttribute('aria-hidden', 'true');
      edges = {};
      for (const side of ['l', 'r', 't', 'b']) {
        edges[side] = make('div', `look-edge look-edge-${side}`);
        box.append(edges[side]);
      }
      ui.append(box);
    }
    showEdge('l', Math.max(0, -ex));
    showEdge('r', Math.max(0, ex));
    showEdge('t', Math.max(0, -ey));
    showEdge('b', Math.max(0, ey));
  }

  /* ------------------------------------------------------------------------------------ frames */

  function update(dt) {
    if (!(dt > 0)) dt = 0;
    tapHud();
    for (let i = 0; i < taps.length; i++) pulse(taps[i]);
    taps.length = 0;
    pollPad(dt);
    updateAssist(dt);

    let dx = 0;
    let dy = 0;
    let mx = 0;
    let my = 0;
    if (gameplay) {
      const sens = input.sensitivity;
      const flip = input.invertY ? -1 : 1;
      dx += (mouseX * T.mouse + touchX * T.touch) * sens;
      dy += (mouseY * T.mouse + touchY * T.touch) * sens * flip;

      // Key turning: a fixed rate, whatever the sensitivity and invert settings say.
      dx += ((isHeld('turnR') ? 1 : 0) - (isHeld('turnL') ? 1 : 0)) * T.keyYaw * dt;
      dy += ((isHeld('turnD') ? 1 : 0) - (isHeld('turnU') ? 1 : 0)) * T.keyPitch * dt;

      // A free cursor resting near a screen edge keeps turning.
      let ex = 0;
      let ey = 0;
      if (!input.locked && !lockPending && !input.touch && input.device === 'kbm' && cursorIn && win) {
        ex = edgeTurn(cursorX / (win.innerWidth || 1), T.edgeZoneX);
        ey = edgeTurn(cursorY / (win.innerHeight || 1), T.edgeZoneY);
        // A cursor left near an edge by the click on a menu button does not start turning on its own:
        // the edges wake up once it has been to the middle of the screen.
        if (ex === 0 && ey === 0) edgeArmed = true;
        else if (!edgeArmed) ex = ey = 0;
        dx += ex * T.edgeYaw * sens * dt;
        dy += ey * T.edgePitch * sens * flip * dt;
      }
      showEdges(ex, ey);

      if (pad) {
        const rate = P.yaw * sens * input.aimSlow * dt;
        dx += padLookX * rate;
        dy += padLookY * rate * P.pitchScale * flip;
      }

      mx = (isHeld('right') ? 1 : 0) - (isHeld('left') ? 1 : 0) + padMoveX + stickMoveX;
      my = (isHeld('forward') ? 1 : 0) - (isHeld('back') ? 1 : 0) + padMoveY + stickMoveY;
      const m = mx * mx + my * my;
      if (m > 1) {
        const k = 1 / Math.sqrt(m);
        mx *= k;
        my *= k;
      }
    }
    mouseX = mouseY = mouseTravel = touchX = touchY = 0;
    input.look.dx = dx;
    input.look.dy = dy;
    input.move.x = mx;
    input.move.y = my;
  }

  function endFrame() {
    for (const action in pressedNow) pressedNow[action] = false;
    for (const action in releasedNow) releasedNow[action] = false;
    input.look.dx = input.look.dy = 0;
  }

  /* ------------------------------------------------------------------------------------ wiring */

  function applySetting(key, value) {
    if (key === 'sens' && value > 0) input.sensitivity = value;
    if (key === 'invertY') input.invertY = !!value;
  }
  if (G.settings) {
    applySetting('sens', G.settings.get('sens'));
    applySetting('invertY', G.settings.get('invertY'));
  }

  if (G.events) {
    G.events.on('settings:change', (e) => e && applySetting(e.key, e.value));
    G.events.on('boot:done', tapHud);
    // Rumble the input module plays by itself: every hit taken, every blast nearby. (The weapon plays
    // its own for rounds fired and strikes landed, through input.rumble.)
    G.events.on('player:hit', (e) => {
      const R = T.rumble.hit;
      if (e && e.amount > 0) rumble(Math.min(1, R.base + e.amount * R.perDamage), R.weak, R.ms);
    });
    G.events.on('explosion', (e) => {
      const eye = G.player && G.player.eye;
      if (!e || !e.pos || !eye) return;
      const r = blastRumble(Math.hypot(e.pos.x - eye.x, e.pos.y - eye.y, e.pos.z - eye.z), e.size, T.rumble.blast);
      if (r) rumble(r.strong, r.weak, r.ms);
    });
  }

  if (win && doc) {
    listen(win, 'keydown', onKeyDown);
    listen(win, 'keyup', onKeyUp);
    listen(win, 'blur', dropAll);
    listen(doc, 'visibilitychange', () => {
      if (doc.hidden) dropAll();
    });
    listen(doc, 'mousemove', onMouseMove);
    listen(root, 'mouseleave', () => {
      cursorIn = false;
    });
    listen(win, 'mouseup', onMouseUp);
    listen(win, 'wheel', onWheel, { passive: false });
    listen(doc, 'pointerlockchange', onLockChange);
    listen(doc, 'pointerlockerror', lockFailed);
    listen(win, 'touchstart', onAnyTouch, { capture: true, passive: true });
    // Safari's pinch gesture would zoom the page out from under the thumbs.
    listen(doc, 'gesturestart', (e) => {
      if (gameplay) e.preventDefault();
    });
    listen(win, 'gamepadconnected', () => {
      padKnown = true;
    });
    listen(win, 'gamepaddisconnected', (e) => {
      if (pad && e.gamepad && e.gamepad.index === pad.index) padGone();
    });
    // Crouch is also on Ctrl, and Ctrl + W closes the tab: with Ctrl down in a fight, ask first.
    listen(win, 'beforeunload', (e) => {
      if (!gameplay || !(keysDown.has('ControlLeft') || keysDown.has('ControlRight'))) return undefined;
      e.preventDefault();
      e.returnValue = '';
      return '';
    });

    if (canvas) {
      listen(canvas, 'mousedown', onCanvasMouseDown);
      listen(canvas, 'contextmenu', (e) => e.preventDefault());
      listen(canvas, 'touchstart', onCanvasTouchStart, { passive: false });
      listen(canvas, 'touchmove', onCanvasTouchMove, { passive: false });
      listen(canvas, 'touchend', onCanvasTouchEnd, { passive: false });
      listen(canvas, 'touchcancel', onCanvasTouchEnd, { passive: false });
    }

    // A phone or a tablet: start out in the touch scheme, before the first tap lands.
    try {
      if (typeof win.matchMedia === 'function' && win.matchMedia('(hover: none) and (pointer: coarse)').matches) {
        input.touch = true;
        input.device = 'touch';
        input.mode = 'drag';
        buildTouch();
      }
    } catch {
      /* no media queries: the first touch switches schemes */
    }

    // Keyboard glyphs follow the printed letters: the swap key reads A on a French keyboard.
    try {
      const keyboard = nav && nav.keyboard;
      if (keyboard && typeof keyboard.getLayoutMap === 'function') {
        keyboard.getLayoutMap().then((map) => {
          for (const action in TUNING.glyphs.layoutCodes) {
            const letter = map.get(TUNING.glyphs.layoutCodes[action]);
            if (typeof letter === 'string' && /^[a-z0-9]$/i.test(letter)) GLYPHS.kbm[action] = letter.toUpperCase();
          }
        }, () => {});
      }
    } catch {
      /* not available here: the QWERTY letters stand */
    }
  }
  setRootState();

  return input;
}
