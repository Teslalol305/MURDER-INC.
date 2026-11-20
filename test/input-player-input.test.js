// The real input module (src/input.js) without a browser: createInput(G, env) takes stand-ins for
// window, document and navigator, and the tests fire the events a browser would.
// Covers the pure parts (dead zone, gamepad response curve, edge turning, blast rumble) and the module:
// actions and the gameplay gate, mouse / key / edge look, the pointer-lock fallback, the gamepad
// (curve, boost, aim slow-down, mapping, latched sprint, menu navigation, rumble) and the touch controls.

import test from 'node:test';
import assert from 'node:assert/strict';
import * as TUNING from '../src/config/player.js';
import { MODULES, missingFrom } from '../src/core/contract.js';
import { createEvents } from '../src/core/events.js';
import { blastRumble, createInput, deadzone, edgeTurn, padCurve, padLook } from '../src/input.js';

const DT = 1 / 60;
const P = TUNING.input.pad;

function near(actual, expected, eps, label = '') {
  assert.ok(Math.abs(actual - expected) <= eps, `${label} expected ${expected} ± ${eps}, got ${actual}`);
}

// ------------------------------------------------------------------------------------ fake browser

function classList() {
  const set = new Set();
  return {
    add: (...names) => names.forEach((n) => set.add(n)),
    remove: (...names) => names.forEach((n) => set.delete(n)),
    toggle(name, on = !set.has(name)) {
      if (on) set.add(name);
      else set.delete(name);
      return on;
    },
    contains: (name) => set.has(name),
  };
}

/** Something that takes listeners; fire(type, fields) calls them with an event-like object. */
function target(extra = {}) {
  const handlers = new Map();
  return Object.assign(extra, {
    addEventListener(type, fn) {
      if (!handlers.has(type)) handlers.set(type, []);
      handlers.get(type).push(fn);
    },
    fire(type, fields = {}) {
      const event = {
        type,
        isTrusted: true,
        cancelable: true,
        defaultPrevented: false,
        preventDefault() {
          this.defaultPrevented = true;
        },
        ...fields,
      };
      for (const fn of handlers.get(type) || []) fn(event);
      return event;
    },
    listens: (type) => (handlers.get(type) || []).length,
  });
}

function element(tag) {
  const el = target({
    tagName: tag.toUpperCase(),
    className: '',
    classList: classList(),
    style: {},
    dataset: {},
    attributes: {},
    children: [],
    hidden: false,
    textContent: '',
    offsetWidth: 0,
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    },
    append(...kids) {
      this.children.push(...kids);
    },
  });
  return el;
}

/**
 * A window / document / navigator trio. `lock` decides what the canvas answers to requestPointerLock():
 * 'grant' | 'reject' (a rejected promise) | 'error' (a pointerlockerror event) | 'silent' | 'throw' | 'missing'.
 */
function browser({ lock = 'grant', coarse = false } = {}) {
  let now = 5000; // ms
  let timers = [];
  let nextTimer = 1;
  const ui = element('div');
  const canvas = element('canvas');
  const root = element('html');
  const doc = target({
    documentElement: root,
    body: element('body'),
    activeElement: null,
    hidden: false,
    pointerLockElement: null,
    getElementById: (id) => (id === 'ui' ? ui : id === 'view' ? canvas : null),
    createElement: element,
    exitPointerLock() {
      if (!doc.pointerLockElement) return;
      doc.pointerLockElement = null;
      doc.fire('pointerlockchange');
    },
  });
  const env = { lock, requests: 0 };
  if (lock !== 'missing') {
    canvas.requestPointerLock = () => {
      env.requests++;
      const mode = env.lock;
      if (mode === 'throw') throw new Error('no');
      if (mode === 'grant') {
        doc.pointerLockElement = canvas;
        doc.fire('pointerlockchange');
        return Promise.resolve();
      }
      if (mode === 'error') {
        doc.fire('pointerlockerror');
        return undefined; // older browsers: no promise, just the event
      }
      if (mode === 'reject') {
        const p = Promise.reject(new Error('NotAllowedError'));
        p.catch(() => {});
        return p;
      }
      return undefined; // 'silent': nothing ever happens
    };
  }
  const win = target({
    innerWidth: 1000,
    innerHeight: 500,
    performance: { now: () => now },
    setTimeout(fn, ms) {
      const id = nextTimer++;
      timers.push({ id, at: now + ms, fn });
      return id;
    },
    clearTimeout(id) {
      timers = timers.filter((t) => t.id !== id);
    },
    matchMedia: () => ({ matches: coarse }),
  });
  const navigator = {
    pads: [],
    getGamepads() {
      return this.pads;
    },
  };
  /** Moves the clock and runs the timers that fall due. */
  env.advance = (ms) => {
    now += ms;
    const due = timers.filter((t) => t.at <= now);
    timers = timers.filter((t) => t.at > now);
    for (const t of due) t.fn();
  };
  return Object.assign(env, { window: win, document: doc, navigator, canvas, ui, root });
}

/** A standard-mapping gamepad whose sticks and buttons the test sets. */
function gamepad() {
  const pad = {
    index: 0,
    connected: true,
    mapping: 'standard',
    axes: [0, 0, 0, 0],
    buttons: Array.from({ length: 17 }, () => ({ pressed: false, value: 0 })),
    effects: [],
    vibrationActuator: {
      playEffect(type, params) {
        pad.effects.push({ type, ...params });
        return Promise.resolve('complete');
      },
    },
    press(i, value = 1) {
      pad.buttons[i] = { pressed: value > 0.5, value };
    },
    let(i) {
      pad.buttons[i] = { pressed: false, value: 0 };
    },
  };
  return pad;
}

function setup(opts = {}) {
  const env = browser(opts);
  const events = createEvents();
  const seen = [];
  events.on('input:lock', (e) => seen.push(['lock', e.locked, e.mode]));
  events.on('input:device', (e) => seen.push(['device', e.device]));
  const settings = {
    values: { sens: 1, invertY: false, ...opts.settings },
    get(key) {
      return this.values[key];
    },
  };
  const G = {
    events,
    settings,
    renderer: { domElement: env.canvas },
    config: { weapons: { chopper: { rumble: { strong: 0.18, weak: 0.5, ms: 55 } } } },
    game: { state: 'playing' },
    ...opts.G,
  };
  const input = createInput(G, env);
  G.input = input;
  const frame = (dt = DT) => {
    input.update(dt);
    const snap = { dx: input.look.dx, dy: input.look.dy, x: input.move.x, y: input.move.y };
    input.endFrame();
    env.advance(dt * 1000);
    return snap;
  };
  const key = (code, down = true, extra = {}) => env.window.fire(down ? 'keydown' : 'keyup', { code, repeat: false, metaKey: false, altKey: false, target: env.document.body, ...extra });
  const touch = (el, type, id, x, y) => el.fire(type, { changedTouches: [{ identifier: id, clientX: x, clientY: y }] });
  const button = (action) => env.ui.children[0].children.find((el) => el.className === `touch-btn touch-${action}`);
  return { env, G, input, events, seen, frame, key, touch, button };
}

// ------------------------------------------------------------------------------------ pure parts

test('input: axial dead zone rescales to the full range', () => {
  assert.equal(deadzone(0.1, 0.14), 0);
  assert.equal(deadzone(-0.14, 0.14), 0);
  near(deadzone(0.57, 0.14), 0.5, 1e-12);
  near(deadzone(-0.57, 0.14), -0.5, 1e-12);
  assert.equal(deadzone(1, 0.14), 1);
  assert.equal(deadzone(1.3, 0.14), 1, 'never more than 1');
  assert.equal(deadzone(NaN, 0.14), 0);
});

test('input: gamepad response curve 0.25·m + 0.75·m³', () => {
  assert.equal(padCurve(0, P.curve), 0);
  assert.equal(padCurve(1, P.curve), 1);
  near(padCurve(0.5, P.curve), 0.125 + 0.09375, 1e-12);
  near(padCurve(0.2, P.curve), 0.05 + 0.006, 1e-12, 'fine aim near the centre');
  // Applied to the magnitude: a diagonal push behaves like a straight one.
  const out = { x: 0, y: 0 };
  assert.equal(padLook(0, 0, P.curve, out), 0);
  assert.deepEqual(out, { x: 0, y: 0 });
  near(padLook(0.5, 0, P.curve, out), 0.5, 1e-12);
  near(out.x, 0.21875, 1e-12);
  padLook(0.3, 0.4, P.curve, out);
  near(Math.hypot(out.x, out.y), 0.21875, 1e-12, 'same rate at magnitude 0.5 in any direction');
  near(out.y / out.x, 4 / 3, 1e-12, 'direction kept');
  padLook(1, 1, P.curve, out); // the corner of a square gate
  near(Math.hypot(out.x, out.y), 1, 1e-12, 'capped at the full rate');
});

test('input: edge turning ramps from the zone line to the edge', () => {
  assert.equal(edgeTurn(0.5, 0.12), 0);
  assert.equal(edgeTurn(0.12, 0.12), 0);
  assert.equal(edgeTurn(0.88, 0.12), 0);
  near(edgeTurn(0, 0.12), -1, 1e-12, 'left edge: full turn left');
  near(edgeTurn(1, 0.12), 1, 1e-12);
  near(edgeTurn(0.06, 0.12), -0.5, 1e-12);
  near(edgeTurn(0.94, 0.12), 0.5, 1e-12);
  assert.equal(edgeTurn(1.2, 0.12), 0, 'outside the page');
  assert.equal(edgeTurn(NaN, 0.12), 0);
});

test('input: blast rumble by distance and size', () => {
  const B = TUNING.input.rumble.blast;
  assert.equal(blastRumble(22, 'big', B), null);
  assert.equal(blastRumble(40, 'big', B), null);
  const close = blastRumble(0, 'big', B);
  assert.deepEqual([close.strong, close.ms], [1, 440]);
  near(close.weak, 0.96, 1e-12);
  const mid = blastRumble(11, 'small', B);
  near(mid.strong, 0.5, 1e-12);
  near(mid.weak, 0.4, 1e-12);
  near(mid.ms, 340, 1e-9);
});

// ------------------------------------------------------------------------------------ the module

test('input: exposes the whole contract, with or without a browser', () => {
  const bare = createInput({});
  assert.deepEqual(missingFrom(bare, MODULES.input), []);
  bare.update(DT);
  bare.endFrame();
  bare.requestLock();
  bare.exitLock();
  bare.setGameplay(false);
  bare.rumble(1, 1, 100);
  assert.equal(bare.device, 'kbm');
  assert.equal(bare.aimSlow, 1);
  assert.deepEqual(bare.menuNav(), { x: 0, y: 0, accept: false, back: false, start: false });

  const { input, env } = setup();
  assert.deepEqual(missingFrom(input, MODULES.input), []);
  assert.equal(env.root.dataset.device, 'kbm');
  assert.equal(env.root.dataset.look, 'lock');
  assert.equal(env.root.classList.contains('is-touch'), false);
  for (const action of ['fire', 'ads', 'jump', 'sprint', 'crouch', 'reload', 'interact', 'swap', 'weapon1', 'weapon2', 'melee', 'pause']) {
    assert.equal(input.down(action), false);
    assert.ok(input.glyph(action).length > 0, `glyph for ${action}`);
  }
});

test('input: keys — move vector, edges, repeat, modifiers, focus', () => {
  const { input, frame, key, env } = setup();
  key('KeyW');
  assert.equal(input.pressed('forward'), true);
  assert.deepEqual(frame(), { dx: 0, dy: 0, x: 0, y: 1 });
  assert.equal(input.pressed('forward'), false, 'the edge lasts one frame');
  assert.equal(input.down('forward'), true);
  key('KeyD');
  let f = frame();
  near(f.x, Math.SQRT1_2, 1e-12, 'diagonals are not faster');
  near(f.y, Math.SQRT1_2, 1e-12);
  key('KeyW', false);
  assert.equal(input.released('forward'), true);
  f = frame();
  assert.deepEqual([f.x, f.y], [1, 0]);
  key('KeyD', false);
  key('KeyA');
  key('KeyS');
  f = frame();
  near(f.x, -Math.SQRT1_2, 1e-12);
  near(f.y, -Math.SQRT1_2, 1e-12);
  key('KeyA', false);
  key('KeyS', false);

  // Every binding of the keyboard table.
  const bindings = {
    Space: 'jump', ShiftLeft: 'sprint', ShiftRight: 'sprint', KeyC: 'crouch',
    KeyR: 'reload', KeyE: 'interact', KeyF: 'melee', KeyV: 'melee', KeyQ: 'swap', Digit1: 'weapon1', Digit2: 'weapon2',
    Numpad1: 'weapon1', Numpad2: 'weapon2', Enter: 'fire', NumpadEnter: 'fire', Escape: 'pause', KeyP: 'pause',
  };
  for (const [code, action] of Object.entries(bindings)) {
    key(code);
    assert.equal(input.down(action), true, `${code} → ${action}`);
    key(code, false);
    frame();
    assert.equal(input.down(action), false, `${code} released`);
  }

  // An environment that sends no `code` (remote desktops): the key name stands in.
  env.window.fire('keydown', { code: '', key: 'W', repeat: false, target: env.document.body });
  assert.equal(input.down('forward'), true);
  env.window.fire('keyup', { code: '', key: 'w', target: env.document.body });
  env.window.fire('keydown', { code: '', key: ' ', repeat: false, target: env.document.body });
  assert.equal(input.pressed('jump'), true);
  env.window.fire('keyup', { code: '', key: ' ', target: env.document.body });
  frame();
  assert.equal(input.down('forward') || input.down('jump'), false);

  // Two keys on one action: down until both are up.
  key('ShiftLeft');
  key('ShiftRight');
  key('ShiftLeft', false);
  assert.equal(input.down('sprint'), true);
  assert.equal(input.released('sprint'), false);
  key('ShiftRight', false);
  assert.equal(input.released('sprint'), true);
  frame();

  // A tap that comes and goes between two frames still counts for one frame.
  key('KeyR');
  key('KeyR', false);
  assert.equal(input.pressed('reload'), true);
  assert.equal(input.down('reload'), true);
  frame();
  assert.equal(input.down('reload'), false);

  // Ignored: key repeat, browser shortcuts, typing, Space on a focused button.
  assert.equal(key('KeyE', true, { repeat: true }).defaultPrevented, true, 'a repeat is still kept from the page');
  assert.equal(input.down('interact'), false);
  key('KeyR', true, { metaKey: true });
  key('KeyR', true, { altKey: true });
  key('KeyR', true, { target: { tagName: 'INPUT' } });
  assert.equal(input.down('reload'), false);
  env.document.activeElement = { tagName: 'BUTTON' };
  key('Space');
  key('Enter');
  assert.equal(input.down('jump') || input.down('fire'), false, 'Space / Enter belong to the focused button');
  env.document.activeElement = null;

  // During gameplay the page never sees the game keys (Space scrolling, Ctrl + R reloading), nor Tab.
  assert.equal(key('Space').defaultPrevented, true);
  assert.equal(key('KeyR', true, { ctrlKey: true }).defaultPrevented, true);
  assert.equal(key('Tab').defaultPrevented, true);
  assert.equal(key('Escape').defaultPrevented, false, 'pause is left alone');
  assert.equal(key('F5').defaultPrevented, false);
});

test('input: the gameplay gate — only pause gets through, menu presses do not leak into play', () => {
  const { input, frame, key } = setup();
  key('KeyW');
  key('ShiftLeft');
  frame();
  input.setGameplay(false);
  assert.equal(input.down('forward'), false);
  assert.deepEqual(frame(), { dx: 0, dy: 0, x: 0, y: 0 });
  key('Enter'); // activates the Resume button
  key('Space');
  key('KeyP');
  assert.equal(input.down('fire'), false);
  assert.equal(input.pressed('jump'), false);
  assert.equal(input.pressed('pause'), true, 'pause works in menus');
  frame();
  input.setGameplay(true);
  // W and Shift are still physically held: walking and sprinting carry on. Enter and Space do not fire or jump.
  assert.equal(input.down('forward'), true);
  assert.equal(input.down('sprint'), true);
  assert.equal(input.down('fire'), false);
  assert.equal(input.down('jump'), false);
  assert.deepEqual(frame(), { dx: 0, dy: 0, x: 0, y: 1 });
  key('Enter', false);
  key('Enter');
  assert.equal(input.down('fire'), true, 'a fresh press counts');

  // Focus lost: everything is let go, including what is physically held.
  input.setGameplay(false);
  input.setGameplay(true);
  assert.equal(input.down('forward'), true);
  input.setGameplay(false);
  key('KeyW', false);
  input.setGameplay(true);
  assert.equal(input.down('forward'), false, 'released during the pause');
});

test('input: window blur and a hidden tab drop every held input, the presses of this frame included', () => {
  const { input, key, env } = setup();
  key('KeyW');
  env.canvas.fire('mousedown', { button: 0 });
  assert.equal(input.down('fire'), true);
  env.window.fire('blur');
  assert.equal(input.down('forward') || input.down('fire') || input.pressed('fire'), false);
  key('KeyD');
  env.document.hidden = true;
  env.document.fire('visibilitychange');
  assert.equal(input.down('right'), false);
});

test('input: mouse look — 0.0021 rad per pixel × sensitivity, invert, glitch filter, buttons, wheel', () => {
  const { input, frame, env, events } = setup({ settings: { sens: 2 } });
  assert.equal(input.sensitivity, 2);
  env.document.fire('mousemove', { movementX: 100, movementY: -40, clientX: 500, clientY: 250 });
  env.document.fire('mousemove', { movementX: 50, movementY: 10, clientX: 500, clientY: 250 });
  let f = frame();
  near(f.dx, 150 * 0.0021 * 2, 1e-12, 'right is positive');
  near(f.dy, -30 * 0.0021 * 2, 1e-12, 'up is negative');
  assert.deepEqual(frame(), { dx: 0, dy: 0, x: 0, y: 0 }, 'consumed once');
  env.document.fire('mousemove', { movementX: 401, movementY: 0, clientX: 500, clientY: 250 });
  env.document.fire('mousemove', { movementX: 0, movementY: -500, clientX: 500, clientY: 250 });
  assert.equal(frame().dx, 0, 'single events over 400 px are pointer-lock glitches');
  events.emit('settings:change', { key: 'invertY', value: true });
  events.emit('settings:change', { key: 'sens', value: 0.5 });
  env.document.fire('mousemove', { movementX: 10, movementY: 10, clientX: 500, clientY: 250 });
  f = frame();
  near(f.dx, 10 * 0.0021 * 0.5, 1e-12);
  near(f.dy, -10 * 0.0021 * 0.5, 1e-12, 'inverted');

  env.canvas.fire('mousedown', { button: 0 });
  env.canvas.fire('mousedown', { button: 2 });
  const middle = env.canvas.fire('mousedown', { button: 1 });
  assert.equal(input.down('fire') && input.down('ads') && input.down('melee'), true);
  assert.equal(middle.defaultPrevented, true, 'no auto-scroll on the middle button');
  env.window.fire('mouseup', { button: 0 });
  env.window.fire('mouseup', { button: 2 });
  env.window.fire('mouseup', { button: 1 });
  frame();
  assert.equal(input.down('fire') || input.down('ads') || input.down('melee'), false);
  assert.equal(env.canvas.fire('contextmenu').defaultPrevented, true);
  // The thumb buttons would navigate "back" out of the game.
  assert.equal(env.canvas.fire('mousedown', { button: 3 }).defaultPrevented, true);
  assert.equal(env.window.fire('mouseup', { button: 3 }).defaultPrevented, true);
  assert.equal(env.window.fire('mouseup', { button: 0 }).defaultPrevented, false);

  // The wheel steps along the rack: down is the next gun, up the one before, at most one step per 0.12 s.
  let wheel = env.window.fire('wheel', { deltaY: 120 });
  assert.equal(wheel.defaultPrevented, true, 'no page scroll, no Ctrl + wheel zoom');
  assert.equal(input.pressed('swap'), true);
  assert.equal(input.pressed('weaponPrev'), false);
  frame();
  assert.equal(input.pressed('swap'), false);
  env.window.fire('wheel', { deltaY: -120 });
  assert.equal(input.pressed('swap') || input.pressed('weaponPrev'), false, 'debounced');
  env.advance(130);
  env.window.fire('wheel', { deltaY: 0.4 });
  assert.equal(input.pressed('swap') || input.pressed('weaponPrev'), false, 'a nudge under one unit');
  env.window.fire('wheel', { deltaY: -120 });
  assert.equal(input.pressed('weaponPrev'), true, 'up: the gun before');
  assert.equal(input.pressed('swap'), false);
  frame();
  input.setGameplay(false);
  env.advance(300);
  wheel = env.window.fire('wheel', { deltaY: 120 });
  assert.equal(wheel.defaultPrevented, false, 'menus scroll normally');
  assert.equal(input.pressed('swap'), false);
});

test('input: arrow keys and I J K L turn at a fixed rate, whatever sensitivity and invert say', () => {
  const { frame, key } = setup({ settings: { sens: 3, invertY: true } });
  key('ArrowRight');
  key('KeyK');
  let f = frame(0.05);
  near(f.dx, 2.1 * 0.05, 1e-12, 'yaw 2.1 rad/s to the right');
  near(f.dy, 1.26 * 0.05, 1e-12, 'pitch 1.26 rad/s down');
  key('ArrowRight', false);
  key('KeyK', false);
  key('KeyJ');
  key('ArrowUp');
  f = frame(0.05);
  near(f.dx, -2.1 * 0.05, 1e-12);
  near(f.dy, -1.26 * 0.05, 1e-12);
  key('ArrowLeft'); // J and the left arrow together are still one turn
  near(frame(0.05).dx, -2.1 * 0.05, 1e-12);
});

test('input: pointer lock is granted — locked, announced, mouse buttons dropped on unlock', () => {
  const { input, env, seen, key } = setup({ lock: 'grant' });
  input.requestLock();
  assert.equal(input.locked, true);
  assert.equal(input.mode, 'lock');
  assert.deepEqual(seen, [['lock', true, 'lock']]);
  assert.match(input.hint(), /Esc/);
  input.requestLock();
  assert.equal(env.requests, 1, 'already locked: nothing to ask');

  // Esc / alt-tab: the browser takes the lock away.
  key('KeyW');
  env.canvas.fire('mousedown', { button: 0 });
  env.canvas.fire('mousedown', { button: 2 });
  env.document.exitPointerLock();
  assert.equal(input.locked, false);
  assert.equal(input.mode, 'lock', 'once it has worked the mode stays lock');
  assert.deepEqual(seen[1], ['lock', false, 'lock']);
  assert.equal(input.down('fire') || input.down('ads'), false, 'held fire / aim are dropped');
  assert.equal(input.down('forward'), true, 'held keys are kept');
  assert.match(input.hint(), /Click/);

  // A later refusal does not demote a session that has had the lock.
  env.lock = 'reject';
  env.canvas.fire('mousedown', { button: 0 });
  return Promise.resolve().then(() => {
    env.advance(2000);
    assert.equal(input.mode, 'lock');
    assert.equal(seen.length, 2);
  });
});

for (const how of ['missing', 'throw', 'reject', 'error', 'silent']) {
  test(`input: pointer lock unavailable (${how}) — falls back to drag mode and says so`, async () => {
    const { input, env, seen } = setup({ lock: how });
    input.requestLock();
    await Promise.resolve();
    await Promise.resolve();
    if (how === 'silent') {
      env.advance(1100);
      assert.equal(input.mode, 'lock', 'still waiting');
      env.advance(200); // 1.2 s without a grant
    }
    assert.equal(input.mode, 'drag');
    assert.equal(input.locked, false);
    assert.deepEqual(seen, [['lock', false, 'drag']]);
    assert.equal(env.root.dataset.look, 'drag');
    assert.match(input.hint(), /edge/);
    env.advance(5000);
    assert.equal(seen.length, 1, 'announced once');
  });
}

test('input: in drag mode a click keeps asking a few times, and a grant brings lock mode back', async () => {
  const { input, env, seen } = setup({ lock: 'reject' });
  input.requestLock();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(input.mode, 'drag');
  assert.equal(env.requests, 1);
  for (let i = 0; i < 5; i++) {
    env.canvas.fire('mousedown', { button: 0 });
    await Promise.resolve();
    await Promise.resolve();
    env.window.fire('mouseup', { button: 0 });
  }
  assert.equal(env.requests, 1 + TUNING.input.lockRetries, 'three refused clicks, then it stops asking');
  assert.equal(input.mode, 'drag');

  const retry = setup({ lock: 'reject' });
  retry.input.requestLock(); // autostart: no user gesture yet
  await Promise.resolve();
  await Promise.resolve();
  retry.env.lock = 'grant';
  retry.env.canvas.fire('mousedown', { button: 0 }); // the first real click
  assert.equal(retry.input.locked, true);
  assert.equal(retry.input.mode, 'lock');
  assert.deepEqual(retry.seen, [['lock', false, 'drag'], ['lock', true, 'lock']]);
  assert.equal(retry.input.down('fire'), true, 'the click that captured also fires');
  assert.equal(seen.length, 1);
});

test('input: exitLock gives the mouse back, also when the grant arrives late', () => {
  const { input, env, seen } = setup({ lock: 'silent' });
  input.requestLock();
  input.exitLock(); // paused before the browser answered
  env.advance(2000);
  assert.equal(input.mode, 'lock', 'a cancelled request is not a refusal');
  // The grant shows up anyway: hand it straight back.
  env.document.pointerLockElement = env.canvas;
  env.document.fire('pointerlockchange');
  assert.equal(input.locked, false);
  assert.equal(env.document.pointerLockElement, null);
  assert.deepEqual(seen, [['lock', true, 'lock'], ['lock', false, 'lock']]);
});

test('input: drag mode — the free cursor turns the view, and resting it at an edge keeps turning', async () => {
  const { input, env, frame } = setup({ lock: 'reject', settings: { sens: 2 } });
  input.requestLock();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(input.mode, 'drag');
  // Raw movement of the unlocked cursor, at the normal mouse rate.
  env.document.fire('mousemove', { movementX: 20, movementY: 0, clientX: 500, clientY: 250 });
  near(frame().dx, 20 * 0.0021 * 2, 1e-12);
  assert.deepEqual(frame(), { dx: 0, dy: 0, x: 0, y: 0 }, 'mid-screen: no edge turn');

  // Resting at the right edge: 2.4 rad/s × sensitivity; half-way into the 12 % zone, half of that.
  env.document.fire('mousemove', { movementX: 0, movementY: 0, clientX: 1000, clientY: 250 });
  near(frame(0.05).dx, 2.4 * 2 * 0.05, 1e-12);
  // After a pause the cursor sits wherever the Resume button was: the edges stay quiet until it has
  // been back to the middle.
  input.setGameplay(false);
  input.setGameplay(true);
  assert.equal(frame(0.05).dx, 0, 'not armed');
  env.document.fire('mousemove', { movementX: 0, movementY: 0, clientX: 500, clientY: 250 });
  frame(0.05);
  env.document.fire('mousemove', { movementX: 0, movementY: 0, clientX: 1000, clientY: 250 });
  near(frame(0.05).dx, 2.4 * 2 * 0.05, 1e-12, 'armed again');
  env.document.fire('mousemove', { movementX: 0, movementY: 0, clientX: 60, clientY: 250 });
  near(frame(0.05).dx, -0.5 * 2.4 * 2 * 0.05, 1e-12);
  const cue = env.ui.children.find((el) => el.className === 'look-edges');
  assert.ok(cue, 'the edge cue was built');
  near(Number(cue.children[0].style.opacity), 0.5, 1e-9, 'left strip shows the turn rate');
  // Top edge pitches up at 1.2 rad/s (10 % zone).
  env.document.fire('mousemove', { movementX: 0, movementY: 0, clientX: 500, clientY: 0 });
  let f = frame(0.05);
  near(f.dy, -1.2 * 2 * 0.05, 1e-12);
  assert.equal(f.dx, 0);
  input.invertY = true;
  near(frame(0.05).dy, 1.2 * 2 * 0.05, 1e-12, 'invert applies to the edge turn');
  input.invertY = false;

  // The cursor leaves the page: no more turning. Scripted events never move the cursor.
  env.root.fire('mouseleave');
  assert.equal(frame(0.05).dy, 0);
  env.document.fire('mousemove', { movementX: 5, movementY: 0, clientX: 0, clientY: 0, isTrusted: false });
  near(frame(0.05).dx, 5 * 0.0021 * 2, 1e-12, 'movement counts, the (0, 0) position does not');

  // Not while a controller is the active device (its user parked the cursor wherever), nor in menus.
  env.document.fire('mousemove', { movementX: 0, movementY: 0, clientX: 1000, clientY: 250 });
  const pad = gamepad();
  env.navigator.pads = [pad];
  env.window.fire('gamepadconnected', { gamepad: pad });
  pad.axes[0] = 1;
  f = frame(0.05);
  assert.equal(input.device, 'pad');
  assert.equal(f.dx, 0);
  pad.axes[0] = 0;
  env.document.fire('mousemove', { movementX: 10, movementY: 0, clientX: 1000, clientY: 250 });
  assert.equal(input.device, 'kbm', 'moving the mouse takes over again');
  frame(0.05);
  input.setGameplay(false);
  assert.equal(frame(0.05).dx, 0);
  assert.equal(Number(cue.children[1].style.opacity), 0, 'cue off outside gameplay');
});

test('input: edge turning also works in lock mode while the mouse is free, never while it is captured', () => {
  const { input, env, frame } = setup({ lock: 'grant' });
  input.requestLock();
  env.document.fire('mousemove', { movementX: 0, movementY: 0, clientX: 1000, clientY: 250 });
  assert.equal(frame(0.05).dx, 0, 'captured: the cursor position means nothing');
  env.document.exitPointerLock(); // resumed with Esc: playing with a free mouse until the next click
  env.document.fire('mousemove', { movementX: 0, movementY: 0, clientX: 500, clientY: 250 });
  assert.equal(frame(0.05).dx, 0);
  env.document.fire('mousemove', { movementX: 0, movementY: 0, clientX: 1000, clientY: 250 });
  near(frame(0.05).dx, 2.4 * 0.05, 1e-12);
});

test('input: gamepad sticks — dead zone, move, look curve, pitch scale, sensitivity, invert', () => {
  const { input, env, frame, seen } = setup({ settings: { sens: 2 } });
  const pad = gamepad();
  env.navigator.pads = [null, pad];
  pad.axes = [0.1, -0.1, 0.05, 0.13];
  let f = frame();
  assert.deepEqual(f, { dx: 0, dy: 0, x: 0, y: 0 }, 'inside the dead zone');
  assert.equal(input.device, 'kbm', 'drift does not steal the device');

  pad.axes = [0.57, -1, 0, 0];
  f = frame();
  assert.equal(input.device, 'pad');
  assert.deepEqual(seen.at(-1), ['device', 'pad']);
  assert.equal(env.root.dataset.device, 'pad');
  near(Math.hypot(f.x, f.y), 1, 1e-12, 'clamped to unit length');
  near(f.x / f.y, 0.5, 1e-12, 'strafe right 0.5, forward 1');

  // Half deflection to the right: the curve gives 21.9 % of 2.9 rad/s.
  pad.axes = [0, 0, 0.57, 0];
  f = frame(0.05);
  near(f.dx, 0.21875 * 2.9 * 2 * 0.05, 1e-9);
  assert.equal(f.dy, 0);
  // Down: 62 % of the yaw rate.
  pad.axes = [0, 0, 0, 0.57];
  f = frame(0.05);
  near(f.dy, 0.21875 * 2.9 * 0.62 * 2 * 0.05, 1e-9);
  input.invertY = true;
  near(frame(0.05).dy, -0.21875 * 2.9 * 0.62 * 2 * 0.05, 1e-9);
});

test('input: gamepad turn boost builds over 0.45 s at the rim and falls away in 0.17 s', () => {
  const { env, frame } = setup();
  const pad = gamepad();
  env.navigator.pads = [pad];
  pad.axes = [0, 0, 1, 0];
  const first = frame(0.01).dx;
  near(first, 2.9 * (1 + 0.75 * (0.01 / 0.45)) * 0.01, 1e-9, 'starts at the base rate');
  for (let i = 0; i < 50; i++) frame(0.01); // half a second at the rim
  near(frame(0.01).dx, 2.9 * 1.75 * 0.01, 1e-9, 'full boost: × 1.75');
  pad.axes = [0, 0, 0.9, 0]; // just under the 0.92 line
  for (let i = 0; i < 20; i++) frame(0.01);
  const eased = deadzone(0.9, 0.14);
  near(frame(0.01).dx, (0.25 * eased + 0.75 * eased ** 3) * 2.9 * 0.01, 1e-9, 'boost gone after 0.2 s');
});

test('input: gamepad aim slow-down — own ray check, or whatever the weapon writes', () => {
  let onTarget = false;
  let asked = 0;
  const { input, env, frame, G } = setup();
  G.player = { alive: true, eye: {}, forward: {} };
  G.enemies = {
    aimTarget(eye, dir, range) {
      asked++;
      assert.equal(range, 60);
      return onTarget;
    },
  };
  const pad = gamepad();
  env.navigator.pads = [pad];
  pad.axes = [0, 0, 0.57, 0];
  frame(0.05);
  assert.equal(input.aimSlow, 1);
  const free = frame(0.05).dx;
  onTarget = true;
  for (let i = 0; i < 20; i++) frame(0.05);
  near(input.aimSlow, 0.55, 1e-3, 'an enemy under the crosshair: 55 %');
  near(frame(0.05).dx, free * input.aimSlow, 1e-9, 'applied to the stick');
  assert.ok(asked >= 20 && asked <= 23, `one ray per 0.05 s (${asked})`);
  onTarget = false;
  for (let i = 0; i < 20; i++) frame(0.05);
  near(input.aimSlow, 1, 1e-3);

  // The weapon module writes it: that value is in charge while it keeps coming.
  onTarget = true;
  for (let i = 0; i < 10; i++) {
    input.aimSlow = 0.8;
    frame(0.05);
  }
  assert.equal(input.aimSlow, 0.8);
  near(frame(0.05).dx, free * 0.8, 1e-9);
  for (let i = 0; i < 10; i++) frame(0.05); // it stopped writing: back to our own
  near(input.aimSlow, 0.55, 1e-2);

  // Mouse users are never slowed.
  env.document.fire('mousemove', { movementX: 30, movementY: 0, clientX: 500, clientY: 250 });
  assert.equal(input.device, 'kbm');
  assert.equal(input.aimSlow, 1);
});

test('input: gamepad buttons — the standard mapping, analog triggers, contextual X, latched sprint', () => {
  const { input, env, frame, G } = setup();
  const pad = gamepad();
  env.navigator.pads = [pad];
  const map = { 0: 'jump', 1: 'crouch', 4: 'crouch', 3: 'swap', 12: 'swap', 15: 'swap', 13: 'weaponPrev', 14: 'weaponPrev', 5: 'melee', 11: 'melee', 6: 'ads', 7: 'fire', 9: 'pause', 2: 'reload' };
  for (const [index, action] of Object.entries(map)) {
    pad.press(Number(index));
    input.update(DT);
    assert.equal(input.pressed(action), true, `button ${index} → ${action}`);
    assert.equal(input.down(action), true);
    input.endFrame();
    input.update(DT);
    assert.equal(input.pressed(action), false, 'held: no second edge');
    input.endFrame();
    pad.let(Number(index));
    input.update(DT);
    assert.equal(input.released(action), true);
    input.endFrame();
  }
  // Triggers count from 0.35.
  pad.buttons[7] = { pressed: false, value: 0.3 };
  frame();
  assert.equal(input.down('fire'), false);
  pad.buttons[7] = { pressed: false, value: 0.36 };
  input.update(DT);
  assert.equal(input.down('fire'), true);
  input.endFrame();
  pad.let(7);
  frame();

  // X is Interact when a prompt shows at the moment of the press, for that whole hold.
  G.hud = { calls: 0, prompt() { this.calls++; } };
  frame(); // the input module starts listening in on hud.prompt
  G.hud.prompt({ text: 'Hold X — Grab reel 1', glyph: 'X', progress: 0 });
  assert.equal(G.hud.calls, 1, 'the HUD still gets its call');
  pad.press(2);
  input.update(DT);
  assert.equal(input.down('interact'), true);
  assert.equal(input.down('reload'), false);
  input.endFrame();
  G.hud.prompt(null); // the prompt goes away mid-hold
  frame();
  assert.equal(input.down('interact'), true, 'still Interact until X is let go');
  pad.let(2);
  frame();
  pad.press(2);
  input.update(DT);
  assert.equal(input.down('reload'), true, 'no prompt: X reloads');
  input.endFrame();
  pad.let(2);
  frame();
  input.setPrompt(true);
  pad.press(2);
  frame();
  assert.equal(input.down('interact'), true, 'input.setPrompt() does the same');
  pad.let(2);
  input.setPrompt(false);
  frame();

  // A HUD that cannot be listened in on (frozen) is left alone, without breaking the frame.
  G.hud = Object.freeze({ prompt() {} });
  frame();
  frame();

  // L3 latches sprint; easing off the stick lets go.
  pad.axes[1] = -1;
  pad.press(10);
  frame();
  pad.let(10);
  frame();
  assert.equal(input.down('sprint'), true, 'latched after one click');
  pad.axes[1] = -0.7;
  frame();
  assert.equal(input.down('sprint'), true);
  pad.axes[1] = -0.5; // forward 0.42 after the dead zone: under 0.55
  frame();
  assert.equal(input.down('sprint'), false, 'released');
  pad.axes[1] = -1;
  pad.press(10);
  frame();
  pad.let(10);
  frame();
  assert.equal(input.down('sprint'), true);
  input.setGameplay(false);
  input.setGameplay(true);
  frame();
  assert.equal(input.down('sprint'), false, 'a pause clears the latch');

  // Glyphs follow the device.
  assert.equal(input.device, 'pad');
  assert.deepEqual(['fire', 'ads', 'jump', 'reload', 'interact', 'swap', 'pause'].map(input.glyph), ['RT', 'LT', 'A', 'X', 'X', 'Y', 'START']);
  assert.equal(input.hint(), '', 'no mouse talk on a controller');
});

test('input: gamepad disconnect releases everything and hands the device back', () => {
  const { input, env, frame, seen } = setup();
  const pad = gamepad();
  env.navigator.pads = [pad];
  pad.press(7);
  pad.axes[1] = -1;
  frame();
  assert.equal(input.down('fire'), true);
  env.navigator.pads = [null];
  const f = frame();
  assert.equal(input.down('fire'), false);
  assert.equal(f.y, 0);
  assert.equal(input.device, 'kbm');
  assert.deepEqual(seen.at(-1), ['device', 'kbm']);
  // A pad with too few buttons is not a gamepad; a non-standard one is used when nothing better is there.
  env.navigator.pads = [{ connected: true, mapping: '', axes: [0, -1], buttons: [] }];
  for (let i = 0; i < 70; i++) frame();
  assert.equal(input.device, 'kbm');
  const odd = gamepad();
  odd.mapping = '';
  odd.axes[1] = -1;
  env.navigator.pads = [odd, pad];
  pad.axes[1] = 0;
  pad.let(7);
  for (let i = 0; i < 70; i++) frame();
  assert.equal(frame().y, 0, 'the standard-mapping pad is preferred');
});

test('input: a frame that forbids the Gamepad API is asked once', () => {
  const { env, frame } = setup();
  let calls = 0;
  env.navigator.getGamepads = () => {
    calls++;
    throw new Error('SecurityError');
  };
  for (let i = 0; i < 200; i++) frame();
  assert.equal(calls, 1);
});

test('input: menuNav — accept / back / start edges, vertical repeat after 0.38 s then every 0.17 s', () => {
  const { input, env, G } = setup();
  const pad = gamepad();
  env.navigator.pads = [pad];
  const step = (dt = 0.01) => {
    input.update(dt);
    const nav = { ...input.menuNav() };
    const jumped = input.pressed('jump');
    input.endFrame();
    return { ...nav, jumped };
  };
  // During gameplay the menu gets nothing.
  pad.press(0);
  let n = step();
  assert.deepEqual([n.accept, n.jumped], [false, true]);
  pad.let(0);
  step();

  input.setGameplay(false);
  G.game.state = 'paused';
  pad.press(0);
  n = step();
  assert.equal(n.accept, true);
  assert.equal(n.jumped, false);
  assert.equal(step().accept, false, 'one frame');
  // The game resumes on that press with A still down: no jump.
  input.setGameplay(true);
  n = step();
  assert.equal(input.down('jump'), false);
  pad.let(0);
  step();
  input.setGameplay(false);

  pad.press(1);
  assert.equal(step().back, true);
  pad.let(1);
  pad.press(9);
  n = step();
  assert.equal(n.start, true);
  pad.let(9);
  step();

  // D-pad down: at once, then after 0.38 s, then every 0.17 s.
  pad.press(13);
  const times = [];
  let t = 0;
  for (let i = 0; i < 100; i++) {
    if (step(0.01).y === 1) times.push(Math.round(t * 100) / 100);
    t += 0.01;
  }
  assert.deepEqual(times, [0, 0.38, 0.55, 0.72, 0.89]);
  pad.let(13);
  assert.equal(step().y, 0);
  // The left stick past 0.6 does the same, upward.
  pad.axes[1] = -0.59;
  assert.equal(step().y, 0);
  pad.axes[1] = -0.7;
  assert.equal(step().y, -1);
  assert.equal(step().y, 0);
  pad.axes[1] = 0;
  step();
  // Left / right: once per push, no repeat.
  pad.press(15);
  let pushes = 0;
  for (let i = 0; i < 100; i++) pushes += step(0.01).x;
  assert.equal(pushes, 1);
  pad.let(15);
  pad.axes[0] = -1;
  assert.equal(step().x, -1);
  pad.axes[0] = 0;
  step();

  // The pad goes away mid-menu: no signal stays stuck.
  pad.press(0);
  assert.equal(step().accept, true);
  env.navigator.pads = [];
  assert.equal(step().accept, false);
});

test('input: rumble — pad only, clamped, a light tap does not cut a heavy one, played for hits and blasts', () => {
  const { input, env, frame, events, G } = setup();
  const pad = gamepad();
  env.navigator.pads = [pad];
  input.rumble(1, 1, 100);
  assert.equal(pad.effects.length, 0, 'not while the keyboard is the device');
  pad.press(0);
  frame();
  input.rumble(2, -1, 100);
  assert.deepEqual(pad.effects.at(-1), { type: 'dual-rumble', startDelay: 0, duration: 100, weakMagnitude: 0, strongMagnitude: 1 });
  env.advance(200);

  G.player = { eye: { x: 0, y: 1.68, z: 0 } };
  events.emit('explosion', { pos: { x: 11, y: 1.68, z: 0 }, radius: 6.5, size: 'big', source: null });
  const blast = pad.effects.at(-1);
  near(blast.strongMagnitude, 0.6, 1e-9);
  near(blast.duration, 240 + 200 * 0.6, 1e-9);
  const count = pad.effects.length;
  input.rumble(0.18, 0.5, 55); // what the weapon plays for a round
  assert.equal(pad.effects.length, count, 'a round fired does not cut the blast short');
  env.advance(500);
  input.rumble(0.18, 0.5, 55);
  assert.deepEqual([pad.effects.at(-1).strongMagnitude, pad.effects.at(-1).weakMagnitude, pad.effects.at(-1).duration], [0.18, 0.5, 55]);
  env.advance(100);
  events.emit('player:hit', { amount: 15, from: null, health: 85, kind: 'bullet' });
  near(pad.effects.at(-1).strongMagnitude, 0.45 + 15 / 30, 1e-9);
  assert.deepEqual([pad.effects.at(-1).weakMagnitude, pad.effects.at(-1).duration], [0.3, 160]);
  // A pad without motors is fine.
  delete pad.vibrationActuator;
  input.rumble(1, 1, 100);
});

test('input: touch — the first touch switches schemes and builds the controls; hidden outside gameplay', () => {
  const { input, env, seen, touch } = setup();
  assert.equal(env.ui.children.length, 0, 'nothing is built for mouse users');
  input.requestLock();
  assert.equal(input.locked, true);
  env.window.fire('touchstart', { changedTouches: [{ identifier: 1, clientX: 10, clientY: 10 }] });
  assert.equal(input.touch, true);
  assert.equal(input.device, 'touch');
  assert.equal(input.locked, false, 'the pointer lock is given up');
  assert.equal(input.mode, 'drag', 'fingers drag to look');
  assert.deepEqual(seen.slice(-2), [['lock', false, 'drag'], ['device', 'touch']], 'announced as a mode change, not as a lost lock');
  assert.equal(env.root.classList.contains('is-touch'), true);
  assert.equal(env.root.dataset.device, 'touch');
  const layer = env.ui.children[0];
  assert.equal(layer.className, 'touch');
  assert.equal(layer.hidden, false, 'gameplay is on');
  // Every control is a disc with an inline SVG glyph; only USE carries a word as well.
  const names = layer.children
    .filter((el) => el.className.startsWith('touch-btn'))
    .map((el) => {
      const label = el.children.find((c) => c.className === 'touch-label');
      assert.equal(el.children[0].className, 'touch-glyph');
      assert.match(el.children[0].innerHTML, /^<svg viewBox="0 0 32 32"[^>]*>.+<\/svg>$/s, `${el.className} has a glyph`);
      return [el.className.split('touch-')[2], el.attributes['aria-label'], label ? label.textContent : ''];
    });
  assert.deepEqual(names, [
    ['fire', 'Fire', ''], ['fire2', 'Fire (left thumb)', ''], ['ads', 'Aim', ''], ['jump', 'Jump', ''], ['crouch', 'Crouch', ''],
    ['reload', 'Reload', ''], ['swap', 'Swap weapon', ''], ['melee', 'Melee strike', ''], ['interact', 'Use', 'USE'], ['pause', 'Pause', ''],
  ]);
  const stick = layer.children.find((el) => el.className === 'touch-stick');
  assert.ok(stick && stick.children.some((c) => c.className === 'touch-sprint'), 'the move stick carries the sprint-lock arrow');
  assert.equal(input.hint(), '');
  assert.deepEqual(['fire', 'interact', 'crouch', 'melee'].map(input.glyph), ['FIRE', 'USE', 'DUCK', 'HIT']);

  input.setGameplay(false);
  assert.equal(layer.hidden, true);
  input.setGameplay(true);
  assert.equal(layer.hidden, false);
  input.requestLock();
  assert.equal(env.requests, 1, 'no pointer lock on touch');

  // The browser's stand-in mouse events after a tap are ignored…
  touch(env.canvas, 'touchstart', 5, 900, 100);
  touch(env.canvas, 'touchend', 5, 900, 100);
  env.canvas.fire('mousedown', { button: 0 });
  env.document.fire('mousemove', { movementX: 50, movementY: 0, clientX: 900, clientY: 100 });
  assert.equal(input.down('fire'), false);
  assert.equal(input.device, 'touch');
  // …a real mouse 0.8 s later is a laptop with a touch screen: the on-screen controls step aside.
  env.advance(900);
  env.document.fire('mousemove', { movementX: 50, movementY: 0, clientX: 900, clientY: 100 });
  assert.equal(input.device, 'kbm');
  assert.equal(input.touch, false);
  assert.equal(input.mode, 'lock', 'the mouse had the lock before: lock mode again');
  assert.deepEqual(seen.slice(-2), [['lock', false, 'lock'], ['device', 'kbm']]);
  assert.equal(layer.hidden, true);
  assert.equal(env.root.classList.contains('is-touch'), false);
});

test('input: a phone starts in the touch scheme before the first tap', () => {
  const { input, env } = setup({ coarse: true });
  assert.equal(input.touch, true);
  assert.equal(input.device, 'touch');
  assert.equal(input.mode, 'drag');
  assert.equal(env.root.classList.contains('is-touch'), true);
  assert.equal(env.ui.children[0].className, 'touch');
});

test('input: touch stick — floating on the left 45 %, unit clamp, auto-sprint; the right side looks', () => {
  const { input, env, frame, touch } = setup({ settings: { sens: 2 } });
  env.window.fire('touchstart', { changedTouches: [] });
  const stick = env.ui.children[0].children[0];
  stick.offsetWidth = 116;
  // Left thumb at (200, 300): the stick anchors there.
  touch(env.canvas, 'touchstart', 1, 200, 300);
  assert.equal(stick.classList.contains('is-active'), true);
  assert.deepEqual([stick.style.left, stick.style.top], ['200px', '300px']);
  assert.deepEqual(frame(), { dx: 0, dy: 0, x: 0, y: 0 });
  touch(env.canvas, 'touchmove', 1, 229, 300 - 29); // half-way out, up and right
  let f = frame();
  near(f.x, 0.5, 1e-12);
  near(f.y, 0.5, 1e-12, 'up the screen is forward');
  assert.equal(input.down('sprint'), false);
  touch(env.canvas, 'touchmove', 1, 200, 100); // far past the rim
  f = frame();
  assert.deepEqual([f.x, f.y], [0, 1], 'clamped to the unit circle');
  assert.equal(input.down('sprint'), true, 'pushed fully forward: sprint');
  assert.equal(stick.classList.contains('is-sprint'), true);
  assert.equal(stick.children[1].style.transform, 'translate3d(0.0px, -58.0px, 0)');
  touch(env.canvas, 'touchmove', 1, 200 + 40, 300 - 45); // forward 0.78: not enough
  frame();
  assert.equal(input.down('sprint'), false);

  // Right thumb: 0.0052 rad per pixel × sensitivity.
  touch(env.canvas, 'touchstart', 2, 800, 200);
  touch(env.canvas, 'touchmove', 2, 830, 190);
  f = frame();
  near(f.dx, 30 * 0.0052 * 2, 1e-12);
  near(f.dy, -10 * 0.0052 * 2, 1e-12);
  // A third finger is ignored; a touch on the left while the stick is taken would look instead.
  touch(env.canvas, 'touchstart', 3, 100, 100);
  touch(env.canvas, 'touchmove', 3, 300, 300);
  assert.equal(frame().dx, 0);
  touch(env.canvas, 'touchend', 2, 830, 190);
  touch(env.canvas, 'touchstart', 4, 150, 150);
  touch(env.canvas, 'touchmove', 4, 160, 150);
  near(frame().dx, 10 * 0.0052 * 2, 1e-12, 'left side, stick busy: a look finger');

  touch(env.canvas, 'touchend', 1, 0, 0);
  f = frame();
  assert.deepEqual([f.x, f.y], [0, 0], 'stick released');
  assert.equal(stick.classList.contains('is-active'), false);
  assert.equal(stick.style.left, '', 'back to its resting corner');
  // A touch that begins right of the 45 % line never becomes the stick.
  touch(env.canvas, 'touchend', 4, 0, 0);
  touch(env.canvas, 'touchstart', 6, 451, 300);
  touch(env.canvas, 'touchmove', 6, 451, 200);
  f = frame();
  assert.equal(f.y, 0);
  near(f.dy, -100 * 0.0052 * 2, 1e-12);
});

test('input: touch buttons — FIRE holds and tracks, AIM and DUCK toggle, USE needs a prompt, pause', () => {
  const { input, env, frame, touch, button } = setup();
  env.window.fire('touchstart', { changedTouches: [] });
  const layer = env.ui.children[0];

  const fire = button('fire');
  const start = touch(fire, 'touchstart', 1, 900, 400);
  assert.equal(start.defaultPrevented, true);
  assert.equal(input.pressed('fire'), true);
  assert.equal(fire.classList.contains('is-on'), true);
  touch(fire, 'touchmove', 1, 880, 410);
  let f = frame();
  near(f.dx, -20 * 0.0052, 1e-12, 'hold FIRE and drag: the view tracks');
  near(f.dy, 10 * 0.0052, 1e-12);
  assert.equal(input.down('fire'), true);
  touch(fire, 'touchend', 1, 880, 410);
  assert.equal(input.released('fire'), true);
  assert.equal(fire.classList.contains('is-on'), false);
  frame();

  const aim = button('ads');
  touch(aim, 'touchstart', 2, 800, 450);
  touch(aim, 'touchend', 2, 800, 450);
  frame();
  assert.equal(input.down('ads'), true, 'AIM stays on after the tap');
  assert.equal(aim.classList.contains('is-latched'), true);
  assert.equal(aim.attributes['aria-pressed'], 'true');
  touch(aim, 'touchstart', 2, 800, 450);
  touch(aim, 'touchend', 2, 800, 450);
  frame();
  assert.equal(input.down('ads'), false, 'and off after the next');
  assert.equal(aim.classList.contains('is-latched'), false);

  const duck = button('crouch');
  touch(duck, 'touchstart', 3, 700, 470);
  touch(duck, 'touchend', 3, 700, 470);
  frame();
  assert.equal(input.down('crouch'), true, 'DUCK is a toggle');
  // Dragging on a button other than FIRE does not turn the view.
  touch(duck, 'touchstart', 3, 700, 470);
  touch(duck, 'touchmove', 3, 600, 400);
  touch(duck, 'touchend', 3, 600, 400);
  assert.equal(frame().dx, 0);
  assert.equal(input.down('crouch'), false);

  for (const [action, name] of [['jump', 'jump'], ['reload', 'reload'], ['swap', 'swap'], ['melee', 'melee']]) {
    const el = button(name);
    touch(el, 'touchstart', 4, 0, 0);
    assert.equal(input.pressed(action), true, `${name} button`);
    touch(el, 'touchend', 4, 0, 0);
    frame();
    assert.equal(input.down(action), false);
  }

  // USE: shown by a prompt, a hold.
  assert.equal(layer.classList.contains('has-prompt'), false);
  input.setPrompt(true);
  assert.equal(layer.classList.contains('has-prompt'), true);
  const use = button('interact');
  touch(use, 'touchstart', 5, 0, 0);
  frame();
  frame();
  assert.equal(input.down('interact'), true);
  input.setPrompt(false); // the reel was grabbed: the button goes, the hold ends
  assert.equal(input.down('interact'), false);
  assert.equal(layer.classList.contains('has-prompt'), false);
  touch(use, 'touchend', 5, 0, 0);

  // Leaving gameplay clears the toggles and whatever was held.
  touch(aim, 'touchstart', 2, 800, 450);
  touch(aim, 'touchend', 2, 800, 450);
  touch(fire, 'touchstart', 1, 900, 400);
  frame();
  const pause = button('pause');
  touch(pause, 'touchstart', 6, 0, 0);
  assert.equal(input.pressed('pause'), true);
  input.setGameplay(false); // the game pauses
  assert.equal(layer.hidden, true);
  input.setGameplay(true);
  assert.equal(input.down('ads') || input.down('fire'), false);
  assert.equal(aim.classList.contains('is-latched'), false);
  assert.equal(fire.classList.contains('is-on'), false);
  touch(fire, 'touchstart', 1, 900, 400);
  assert.equal(input.down('fire'), true, 'the button works again');
});

test('input: Ctrl is not a game key and the page never questions leaving (Ctrl + W belongs to the browser)', () => {
  const { input, env, key } = setup();
  assert.equal(TUNING.keys.ControlLeft, undefined);
  assert.equal(TUNING.keys.ControlRight, undefined);
  assert.equal(TUNING.keys.KeyC, 'crouch', 'C still crouches');
  key('ControlLeft');
  assert.equal(input.down('crouch'), false);
  assert.equal(env.window.fire('beforeunload').defaultPrevented, false, 'no leave-site guard, even with Ctrl down in a fight');
  key('ControlLeft', false);
  key('KeyC');
  assert.equal(input.down('crouch'), true);
  key('KeyC', false);
});

test('input: hint() follows the look mode and the game state; keyboard glyphs follow the layout', async () => {
  const { input, env, G } = setup({ lock: 'grant' });
  assert.equal(input.hint(), TUNING.hints.click);
  G.game.state = 'paused';
  assert.equal(input.hint(), TUNING.hints.resume);
  input.requestLock();
  // Paused while the lock is still held (P, pad Start, a tab switch: the release arrives later): the
  // pause card must already say how to get the mouse back, not that it is locked in.
  assert.equal(input.locked, true);
  assert.equal(input.hint(), TUNING.hints.resume);
  G.game.state = 'playing';
  assert.equal(input.hint(), TUNING.hints.locked);
  assert.deepEqual(['fire', 'ads', 'jump', 'sprint', 'crouch', 'reload', 'interact', 'swap', 'melee', 'pause'].map(input.glyph),
    ['LMB', 'RMB', 'SPACE', 'SHIFT', 'C', 'R', 'E', 'Q', 'F', 'ESC']);
  assert.equal(input.glyph('nonsense'), '');
  assert.ok(env.requests === 1);

  // An AZERTY keyboard prints A on the key that swaps.
  const azerty = browser();
  azerty.navigator.keyboard = { getLayoutMap: () => Promise.resolve(new Map([['KeyQ', 'a'], ['KeyE', 'e'], ['KeyC', 'c'], ['KeyR', 'r'], ['KeyF', 'f']])) };
  const fr = createInput({ renderer: { domElement: azerty.canvas } }, azerty);
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(fr.glyph('swap'), 'A');
  assert.equal(fr.glyph('interact'), 'E');
});

// ------------------------------------------------------------------- input and player, end to end

test('input + player: keys walk, the mouse turns the way it moves, a pad stick sprints and aims slower', async () => {
  const THREE = await import('three');
  const { createPhysics } = await import('../src/physics.js');
  const { createPlayer } = await import('../src/player.js');
  const { env, G, input, key } = setup();
  G.THREE = THREE;
  G.params = {};
  G.camera = new THREE.PerspectiveCamera(74, 16 / 9, 0.08, 700);
  G.render = { post: { damage: 0, lowHealth: 0 } };
  G.level = { playerStart: { pos: new THREE.Vector3(0, 0, 0), yaw: 0 } }; // facing north (−Z)
  G.weapon = { update() {} };
  G.physics = createPhysics(G);
  G.physics.setBounds({ minX: -46, maxX: 46, minZ: -34, maxZ: 34 });
  const player = (G.player = createPlayer(G));
  const frames = (n, dt = DT) => {
    for (let i = 0; i < n; i++) {
      input.update(dt);
      player.update(dt);
      input.endFrame();
      env.advance(dt * 1000);
    }
  };

  key('KeyW');
  frames(60);
  near(player.speed, 3.8, 1e-9);
  assert.ok(player.pos.z < -3 && Math.abs(player.pos.x) < 1e-9, 'W walks forward: north');
  key('KeyW', false);
  key('KeyD');
  frames(60);
  assert.ok(player.vel.x > 3.7, 'D strafes right: east');
  key('KeyD', false);
  frames(30);

  // Mouse right → the view turns right (north → east); mouse up → looks up.
  env.document.fire('mousemove', { movementX: 748, movementY: 0, clientX: 500, clientY: 250 }); // dropped: > 400 px
  for (let i = 0; i < 4; i++) env.document.fire('mousemove', { movementX: 187, movementY: -25, clientX: 500, clientY: 250 });
  frames(1);
  near(player.yaw, -748 * 0.0021, 1e-9);
  near(player.forward.x, Math.sin(748 * 0.0021) * Math.cos(100 * 0.0021), 1e-9, 'now facing east');
  near(player.pitch, 100 * 0.0021, 1e-9, 'and up');
  near(G.camera.rotation.y, player.yaw, 1e-9);

  // Jump (Space), crouch (C), sprint (Shift + W).
  key('Space');
  frames(1);
  key('Space', false);
  assert.ok(player.vel.y > 5);
  frames(60);
  key('KeyC');
  frames(30);
  assert.equal(player.crouching, true);
  key('KeyC', false);
  key('ShiftLeft');
  key('KeyW');
  frames(60);
  assert.equal(player.sprinting, true);
  near(player.speed, 6.4, 1e-9);
  key('ShiftLeft', false);
  key('KeyW', false);
  frames(30);

  // A controller: left stick forward, L3 to sprint; with full aim the right stick turns at 60 %.
  const pad = gamepad();
  env.navigator.pads = [pad];
  env.window.fire('gamepadconnected', { gamepad: pad });
  pad.axes[1] = -1;
  pad.press(10);
  frames(2);
  pad.let(10);
  frames(60);
  assert.equal(player.sprinting, true, 'latched sprint');
  pad.axes[1] = 0;
  frames(30);
  pad.axes[2] = 0.57;
  const yaw = player.yaw;
  frames(1, 0.05);
  const free = yaw - player.yaw;
  near(free, 0.21875 * 2.9 * 0.05, 1e-9);
  player.ads = 1;
  frames(1, 0.05);
  near(yaw - free - player.yaw, free * 0.6, 1e-9, 'aiming slows the look on every device');

  // Outside gameplay the player gets nothing.
  input.setGameplay(false);
  pad.axes[1] = -1;
  key('KeyW');
  const at = player.pos.clone();
  frames(30);
  assert.ok(player.pos.distanceTo(at) < 0.5, 'coasts to a stop, no input');
  assert.equal(player.speed, 0);
});

test('input: tap(action) — the UI queues a one-frame press, read at the next update, dropped outside gameplay', () => {
  const { input } = setup();
  input.update(DT);
  input.tap('weapon2'); // a HUD weapon slot tapped late in the frame, after the weapon has run…
  assert.equal(input.pressed('weapon2'), false, '…waits for the next update');
  input.endFrame();
  input.update(DT);
  assert.equal(input.pressed('weapon2'), true);
  assert.equal(input.down('weapon2'), true);
  input.endFrame();
  input.update(DT);
  assert.equal(input.pressed('weapon2'), false, 'one frame only');
  assert.equal(input.down('weapon2'), false);
  input.endFrame();
  input.tap(42); // not an action
  input.setGameplay(false);
  input.tap('melee');
  input.update(DT);
  assert.equal(input.pressed('melee'), false, 'nothing gets through a menu but pause');
  input.endFrame();
  input.setGameplay(true);
  input.update(DT);
  assert.equal(input.pressed('melee'), false, 'and nothing is left over afterwards');
});
