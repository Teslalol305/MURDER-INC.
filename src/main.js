// MURDER INC. — entry point: the shared game object, boot sequence and main loop (CONTRACT section 3).
//
// Debug surface (CONTRACT section 2):
//   window.__G, __frames, __ready (true after the 2nd drawn frame), __fatal, __errors[],
//   __stats(), __setShot({cam: "x,y,z,lx,ly,lz", fov, exposure}), __step
//   plus __skip: with ?step=1, the number of frames to simulate without drawing (fast-forward).
// URL parameters handled here: autostart, shot, mode, seed, noaudio, god, nohud, cam, fov, exposure,
// step, dt. The rest (q, post, bloom, eseed …) belong to the modules that read them from G.params.
//
// Contract checks (src/core/contract.js): every module is held against its member list when it is
// created, and in dev builds every event against its payload keys. A gap is a console error that starts
// with "[contract]", so it lands in __errors and fails a harness run.

import * as THREE from 'three';
import * as brand from './config/brand.js';
import * as catalog from './config/catalog.js';
import * as enemiesConfig from './config/enemies.js';
import * as flow from './config/flow.js';
import * as look from './config/look.js';
import * as playerConfig from './config/player.js';
import * as quality from './config/quality.js';
import * as text from './config/text.js';
import * as weapons from './config/weapons.js';
import { RENDER_GLOBALS, SHARED, missingFrom, missingKeys, missingMembers } from './core/contract.js';
import { createEvents } from './core/events.js';
import { createRng } from './core/rng.js';
import { createSettings } from './core/settings.js';
import { paramNumber, paramOn } from './core/util.js';
import { MODULES, UPDATE } from './modules.js';

/* global __BUILD__ */
const BUILD = typeof __BUILD__ !== 'undefined' ? __BUILD__ : { dev: true, artifact: false, stubbed: [] };

const MAX_DT = 0.05; // below 20 fps the game slows down instead of tunnelling
const STEP_DT = 1 / 30; // ?step=1 without ?dt
const SKIP_BUDGET_MS = 12; // time per animation frame spent on undrawn fast-forward steps
const BOOT_FADE_MS = 700;

// ------------------------------------------------------------------------------------------------
// Error mirror: every console.error and uncaught error lands in window.__errors (for the test harness).
// ------------------------------------------------------------------------------------------------

const errors = (window.__errors = []);
window.__fatal = null;
window.__frames = 0;
window.__ready = false;

function describe(value) {
  if (value instanceof Error) return value.stack || `${value.name}: ${value.message}`;
  if (typeof value === 'object' && value !== null) {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
}

function record(message) {
  if (errors.length < 200) errors.push(String(message).slice(0, 400));
}

const consoleError = console.error.bind(console);
console.error = (...args) => {
  record(args.map(describe).join(' '));
  consoleError(...args);
};
window.addEventListener('error', (e) => {
  record(e.error ? describe(e.error) : `${e.message} (${e.filename}:${e.lineno})`);
});
window.addEventListener('unhandledrejection', (e) => {
  record(`unhandled rejection: ${describe(e.reason)}`);
});

// ------------------------------------------------------------------------------------------------
// The shared game object
// ------------------------------------------------------------------------------------------------

const params = Object.fromEntries(new URLSearchParams(location.search));
const events = createEvents();

// Dev builds hold every event against docs/CONTRACT.md 4.2: a payload that lacks one of its documented
// keys is reported, once per event and key. Events outside the contract pass unchecked.
if (BUILD.dev) {
  const emit = events.emit;
  const reported = new Set();
  events.emit = (name, payload) => {
    const missing = missingKeys(name, payload);
    for (let i = 0; i < missing.length; i++) {
      const id = `${name} ${missing[i]}`;
      if (reported.has(id)) continue;
      reported.add(id);
      console.error(`[contract] event '${name}' was emitted without '${missing[i]}' (docs/CONTRACT.md 4.2)`);
    }
    emit(name, payload);
  };
}

const G = {
  THREE,
  params,
  events,
  rng: createRng(params.seed),
  time: { t: 0, dt: 0, frame: 0, real: 0 },
  settings: createSettings(events),
  config: {
    brand,
    text,
    player: playerConfig,
    weapons,
    enemies: enemiesConfig,
    flow,
    quality,
    catalog,
    look,
  },
  /** How this bundle was built: {dev, artifact, stubbed: [module names]}. */
  build: BUILD,
};
window.__G = G;

const stepMode = paramOn(params, 'step');
const fixedDt = paramNumber(params, 'dt', stepMode ? STEP_DT : 0); // 0 = real time
const godMode = paramOn(params, 'god');
window.__step = stepMode ? 2 : 0; // two frames so __ready can come true, then the harness drives
window.__skip = 0;

if (paramOn(params, 'nohud')) document.documentElement.classList.add('nohud');

// ------------------------------------------------------------------------------------------------
// Boot screen
// ------------------------------------------------------------------------------------------------

const bootEl = document.getElementById('boot');
const bootMsg = document.getElementById('boot-msg');
const bootFill = document.getElementById('boot-fill');

function bootLine(key, progress) {
  if (bootMsg) bootMsg.textContent = text.boot[key];
  if (bootFill) bootFill.style.transform = `scaleX(${progress})`;
}

/** Lets the browser paint the boot line (or moves on after 60 ms when the tab is hidden). */
function paint() {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, 60);
    requestAnimationFrame(() => {
      clearTimeout(timer);
      resolve();
    });
  });
}

function fatal(err) {
  const reason = err && err.message ? err.message : String(err);
  const message = text.boot.fatal(reason);
  window.__fatal = message;
  console.error('[boot] fatal:', err);
  if (bootEl) {
    bootEl.hidden = false;
    bootEl.classList.remove('done');
    bootEl.classList.add('is-fatal');
  }
  if (bootMsg) bootMsg.textContent = message;
}

// ------------------------------------------------------------------------------------------------
// Module creation
// ------------------------------------------------------------------------------------------------

/** Optional modules built for real whose stub runs instead: the factory failed at boot, or `?noaudio=1`. */
const standIns = [];

async function createModule(entry) {
  // Foundation modules have no stand-in: let a failure reach boot() and stop the game.
  if (!entry.stub) return entry.create(G);

  const alreadyStub = BUILD.stubbed.includes(entry.name);
  const forceStub = entry.name === 'audio' && paramOn(params, 'noaudio');
  if (!forceStub) {
    try {
      const api = await entry.create(G);
      if (api === null || typeof api !== 'object') throw new Error('its factory returned no module object');
      return api;
    } catch (err) {
      if (alreadyStub) throw err; // the stub itself is broken: nothing left to fall back to
      console.error(`[boot] ${entry.name} failed, its stub takes over:`, err);
    }
  }
  if (!alreadyStub) standIns.push(entry.name);
  return entry.stub(G);
}

/** Reports every contract member that `target` lacks: a module that is not finished, or a typo. */
function checkContract(label, missing) {
  for (const member of missing) console.error(`[contract] ${label}.${member} is missing (docs/CONTRACT.md)`);
}

// ------------------------------------------------------------------------------------------------
// Fixed camera / FOV / exposure override for screenshots (?cam, ?fov, ?exposure, __setShot)
// ------------------------------------------------------------------------------------------------

const shot = { cam: null, fov: null, exposure: null };

function parseCam(value) {
  if (!value) return null;
  const n = String(value).split(',').map(Number);
  return n.length === 6 && n.every(Number.isFinite) ? n : null;
}

const numberOrNull = (value) => (value === undefined || value === null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value));

/** `cam: ""` (or null) releases the camera; the same goes for fov and exposure. Omitted keys are kept. */
function setShot(spec = {}) {
  if ('cam' in spec) shot.cam = parseCam(spec.cam);
  if ('fov' in spec) shot.fov = numberOrNull(spec.fov);
  if ('exposure' in spec) {
    shot.exposure = numberOrNull(spec.exposure);
    if (shot.exposure === null && G.render) G.render.exposure = 1;
  }
}
setShot({ cam: params.cam, fov: params.fov, exposure: params.exposure });
window.__setShot = setShot;

function applyShot() {
  const camera = G.camera;
  if (shot.cam) {
    camera.position.set(shot.cam[0], shot.cam[1], shot.cam[2]);
    camera.lookAt(shot.cam[3], shot.cam[4], shot.cam[5]);
  }
  if (shot.fov !== null) camera.fov = shot.fov; // render.frame() refreshes the projection
  if (shot.exposure !== null) G.render.exposure = shot.exposure;
  // A fixed camera is an outside view: no first-person weapon floating in it.
  G.vmScene.visible = shot.cam === null;
}

// ------------------------------------------------------------------------------------------------
// Main loop
// ------------------------------------------------------------------------------------------------

const thrown = Object.create(null); // "module.method" → true once its first exception was logged

function reportThrow(name, method, err) {
  const key = `${name}.${method}`;
  if (thrown[key]) return;
  thrown[key] = true;
  console.error(`[loop] ${key} threw:`, err);
}

/** Calls G[name][method](dt) if it exists; an exception is logged once and never stops the loop. */
function call(name, method, dt) {
  const mod = G[name];
  if (!mod || typeof mod[method] !== 'function') return undefined;
  try {
    return mod[method](dt);
  } catch (err) {
    reportThrow(name, method, err);
    return undefined;
  }
}

function callAll(names, dt) {
  for (let i = 0; i < names.length; i++) call(names[i], 'update', dt);
}

let drawn = 0;

/** One simulation step and, when `draw` is set, one rendered frame. */
function tick(dt, draw) {
  const time = G.time;
  time.dt = dt;
  time.t += dt;
  time.frame++;

  call('input', 'update', dt);
  const proceed = call('game', 'update', dt);
  const state = G.game.state;
  if (godMode) G.player.invulnerable = true;

  if (proceed !== false && state !== 'title' && state !== 'paused') callAll(UPDATE.live, dt);
  if (state !== 'paused') callAll(UPDATE.world, dt);
  callAll(UPDATE.always, dt);

  try {
    applyShot();
    G.render.frame(dt, draw);
  } catch (err) {
    reportThrow('render', 'frame', err);
  }
  call('input', 'endFrame', dt);

  window.__frames++;
  if (draw && ++drawn >= 2) window.__ready = true;
}

let lastNow = 0;
let frameMs = 0; // smoothed real frame time, for the fps readout

function onAnimationFrame(now) {
  requestAnimationFrame(onAnimationFrame);
  const elapsed = lastNow ? now - lastNow : 16.7;
  lastNow = now;
  G.time.real = now / 1000;
  frameMs = frameMs ? frameMs * 0.95 + elapsed * 0.05 : elapsed;

  if (stepMode) {
    // The harness owns time: frames advance only on request, each with the same dt.
    if (window.__skip > 0) {
      const until = performance.now() + SKIP_BUDGET_MS;
      while (window.__skip > 0 && performance.now() < until) {
        window.__skip--;
        tick(fixedDt, false);
      }
    } else if (window.__step > 0) {
      window.__step--;
      tick(fixedDt, true);
    }
    return;
  }
  tick(fixedDt > 0 ? fixedDt : Math.min(elapsed / 1000, MAX_DT), true);
}

window.__stats = () => {
  const p = G.player;
  const round = (n) => Math.round(n * 100) / 100;
  return {
    ...(G.render ? G.render.stats() : null),
    fps: frameMs ? Math.round(10000 / frameMs) / 10 : 0,
    frameMs: round(frameMs),
    frames: window.__frames,
    t: round(G.time.t),
    state: G.game ? G.game.state : 'boot',
    mode: G.game ? G.game.mode : null,
    player: p && p.pos ? { x: round(p.pos.x), y: round(p.pos.y), z: round(p.pos.z), health: round(p.health) } : null,
    enemies: G.enemies && typeof G.enemies.aliveCount === 'function' ? G.enemies.aliveCount() : 0,
    stubbed: [...BUILD.stubbed, ...standIns],
    errors: errors.length,
  };
};

// ------------------------------------------------------------------------------------------------
// Boot
// ------------------------------------------------------------------------------------------------

async function boot() {
  checkContract('G', missingFrom(G, SHARED));
  for (const entry of MODULES) {
    if (entry.line) {
      bootLine(entry.line, entry.progress);
      await paint();
    }
    const t0 = performance.now();
    G[entry.name] = await createModule(entry);
    const ms = performance.now() - t0;
    if (ms > 150) console.info(`[boot] ${entry.name} ${Math.round(ms)}ms`);
    checkContract(`G.${entry.name}`, missingMembers(entry.name, G[entry.name]));
    if (entry.name === 'render') checkContract('G', missingFrom(G, RENDER_GLOBALS));
  }

  bootLine('wait', 0.92);
  await paint();
  await G.render.onLevelReady();

  bootLine('ready', 1);
  events.emit('boot:done', {});

  if (paramOn(params, 'autostart') || paramOn(params, 'shot')) {
    const mode = flow.modes.includes(params.mode) ? params.mode : G.settings.get('mode');
    try {
      G.game.start({ mode, skipIntro: true });
    } catch (err) {
      console.error('[boot] autostart failed:', err); // the title screen is still there
    }
  }

  requestAnimationFrame(onAnimationFrame);
  if (bootEl) {
    bootEl.classList.add('done');
    // Stepped runs are screenshots waiting to happen: no cross-fade over the first frames.
    if (stepMode) bootEl.hidden = true;
    else {
      setTimeout(() => {
        if (!window.__fatal) bootEl.hidden = true;
      }, BOOT_FADE_MS);
    }
  }
}

boot().catch(fatal);
