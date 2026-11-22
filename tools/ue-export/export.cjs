#!/usr/bin/env node
// Exports the web game's real data for the Unreal rebuild.
//
//   node tools/ue-export/export.cjs                  build a dev page from src/, boot it, write the files
//   node tools/ue-export/export.cjs --page dist/index.html     read an existing build instead
//   node tools/ue-export/verify.cjs                  check what was written (run it after every export)
//
// Options
//   --page <file.html>   a built page to read (default: dist/dev-export.html, rebuilt first)
//   --out <dir>          where the JSON goes (default unreal/MurderInc/Content/Data)
//   --seed <n>           world seed (default 1994, the game's own default)
//   --quality <name>     preset the page boots with: test | low | medium | high | ultra (default low: the
//                        quickest; nothing that is exported depends on it)
//   --raw <dir>          also dump what the page collectors answered, untouched (debugging)
//   --verbose            echo the page console
//
// Writes config.json, text.json, level.json, props.json and atmos.json. Nothing in them is typed in by
// hand: the game is booted in headless Chromium and everything is read from window.__G, from the calls
// the capture hooks listen in on (lib/hooks.cjs), or, for the few things that are private to a module,
// from that module's own source imported here in Node (each such value says so in its `source`).
// The schema of every file is in docs/unreal/spec/08-data-export.md.

'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const K = require('./lib/convert.cjs');
const C = require('./lib/collect.cjs');
const { openGame, buildDevPage } = require('./lib/browser.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const SRC = path.join(ROOT, 'src');
const SCHEMA = 1;

// ------------------------------------------------------------------------------------------------
// Arguments
// ------------------------------------------------------------------------------------------------

function parseArgs(argv) {
  const opts = { page: null, out: path.join(ROOT, 'unreal', 'MurderInc', 'Content', 'Data'), seed: 1994, quality: 'low', raw: null, verbose: false, help: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    const eq = arg.startsWith('--') ? arg.indexOf('=') : -1;
    const flag = eq < 0 ? arg : arg.slice(0, eq);
    const value = () => {
      const v = eq >= 0 ? arg.slice(eq + 1) : argv[++i];
      if (v === undefined) throw new Error(`${flag} needs a value`);
      return v;
    };
    switch (flag) {
      case '--page': opts.page = path.resolve(value()); break;
      case '--out': opts.out = path.resolve(value()); break;
      case '--seed': opts.seed = Number(value()); break;
      case '--quality': opts.quality = value(); break;
      case '--raw': opts.raw = path.resolve(value()); break;
      case '--verbose': opts.verbose = true; break;
      case '--help': case '-h': opts.help = true; break;
      default: throw new Error(`unknown argument ${arg}`);
    }
  }
  if (!Number.isInteger(opts.seed) || opts.seed < 0) throw new Error('--seed needs a whole number');
  if (!['test', 'low', 'medium', 'high', 'ultra'].includes(opts.quality)) throw new Error('--quality needs test, low, medium, high or ultra');
  return opts;
}

const USAGE = 'usage: node tools/ue-export/export.cjs [--page <file.html>] [--out <dir>] [--seed <n>] [--quality <name>] [--raw <dir>] [--verbose]';

/** Stops the export: a check that guards the correctness of the files did not hold. */
function fail(message) {
  throw new Error(`export check failed: ${message}`);
}

const importSource = (file) => import(pathToFileURL(path.join(SRC, file)).href);

// ------------------------------------------------------------------------------------------------
// Sample inputs for the functions the game keeps among its tuning (the inputs are ours, the answers
// are the game's). A new function in src/config needs a row here, or it must be a plain text template.
// ------------------------------------------------------------------------------------------------

const WAVES = Array.from({ length: 30 }, (_, i) => [i + 1]); // holdout wave numbers: every formula has levelled off by 30

const RUNS = [];
for (const time of [120, 269.9, 270, 399.9, 400, 600]) {
  for (const [shots, hits] of [[0, 0], [100, 29], [100, 30], [100, 49], [100, 50], [100, 100]]) {
    for (const retries of [0, 1]) RUNS.push([{ time, shots, hits, retries }]);
  }
}

const FUNCTION_SAMPLES = {
  'flow.holdout.total': WAVES,
  'flow.holdout.buzzardShare': WAVES,
  'flow.holdout.stagger': WAVES,
  'flow.holdout.hpScale': WAVES,
  'flow.holdout.damageScale': WAVES,
  'flow.holdout.cooldownScale': WAVES,
  'flow.holdout.extraAlive': WAVES,
  'flow.holdout.score.killScale': WAVES,
  'flow.holdout.score.waveClear': WAVES,
  'flow.ratingPoints': RUNS,
  'quality.autoDetect': [
    [{}],
    [{ userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile/15E148', touchPoints: 5, screenMin: 390, gpu: 'Apple GPU' }],
    [{ touchPoints: 10, screenMin: 820, gpu: 'Mali-G78' }],
    [{ gpu: 'ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)), SwiftShader driver)' }],
    [{ gpu: 'Mali-G78' }],
    [{ gpu: 'ANGLE (Intel, Intel(R) UHD Graphics 630, OpenGL 4.6)' }],
    [{ gpu: 'ANGLE (Intel, Intel(R) Arc(TM) A770 Graphics, D3D11)' }],
    [{ gpu: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060, D3D11)' }],
  ],
  'text.zoneName': ['west', 'avenue', 'shop', 'lot', 'cage', 'nowhere'].flatMap((id) => [-20, -7, 0, 20].map((z) => [id, z])),
};

/** One worked example for each text template (inputs from docs/DESIGN.md section 2). */
const TEMPLATE_EXAMPLES = {
  'text.banners.contact': ['NORTH-EAST'],
  'text.banners.wave': [3, 'EAST'],
  'text.banners.countdown': [3, 3],
  'text.boot.fatal': ['WebGL is not available'],
  'text.objectives.tally.wave': [3, 12345],
  'text.prompts.grab': ['E', '1'],
  'text.radio.waveClear.text': [3],
  'interface.hud.cue.emptySwap': ['Q'],
  'interface.panel.noteAuto': ['medium'],
};

/** Config values the game stores as 0xRRGGBB numbers: written as "#rrggbb". */
const COLOUR_KEYS = new Set(['color', 'lightColor', 'arcColor', 'keyColor', 'clearColor', 'ambientSky', 'ambientGround', 'emissive']);
const COLOUR_UNDER = { palette: null, ambient: new Set(['sky', 'ground']), sky: new Set(['zenith', 'horizon', 'glow']) };

function isColourPath(pathKeys) {
  const key = pathKeys[pathKeys.length - 1];
  const parent = pathKeys[pathKeys.length - 2];
  if (COLOUR_KEYS.has(key)) return true;
  if (parent in COLOUR_UNDER) return COLOUR_UNDER[parent] === null || COLOUR_UNDER[parent].has(key);
  return false;
}

// ------------------------------------------------------------------------------------------------
// Small helpers
// ------------------------------------------------------------------------------------------------

const at = (obj, keys) => keys.reduce((o, k) => (o == null ? undefined : o[k]), obj);

/** Names of a function's parameters, from its source text (`(n, score) => …`, `function f(run) {…}`). */
function paramNames(fn) {
  const text = fn.toString();
  const open = text.indexOf('(');
  const arrow = text.indexOf('=>');
  if (open < 0 || (arrow >= 0 && arrow < open)) return [text.slice(0, arrow).trim()]; // n => …
  let depth = 0;
  let close = -1;
  for (let i = open; i < text.length; i++) {
    if (text[i] === '(') depth++;
    else if (text[i] === ')' && --depth === 0) {
      close = i;
      break;
    }
  }
  const inner = text.slice(open + 1, close);
  const parts = [];
  let level = 0;
  let current = '';
  for (const ch of inner) {
    if ('{[('.includes(ch)) level++;
    else if ('}])'.includes(ch)) level--;
    if (ch === ',' && level === 0) {
      parts.push(current);
      current = '';
    } else current += ch;
  }
  if (current.trim()) parts.push(current);
  return parts.map((p, i) => {
    const text = p.trim();
    if (text.startsWith('{')) {
      // A destructured options object: name its fields.
      const fields = text.slice(1, text.lastIndexOf('}')).split(',').map((f) => f.split('=')[0].trim()).filter(Boolean);
      return `{ ${fields.join(', ')} }`;
    }
    const name = text.split('=')[0].trim();
    return /^[A-Za-z_$][\w$]*$/.test(name) ? name : `arg${i}`;
  });
}

const sameJson = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/** Every {$fn} placeholder in a plain copy of the config: [{path: [...keys]}]. */
function functionPaths(value, prefix = [], out = []) {
  if (value && typeof value === 'object') {
    if (!Array.isArray(value) && typeof value.$fn === 'string' && Object.keys(value).length === 2) {
      out.push(prefix);
      return out;
    }
    for (const key of Object.keys(value)) functionPaths(value[key], [...prefix, key], out);
  }
  return out;
}

function meta(file, run, about) {
  return {
    file,
    about,
    game: 'MURDER INC.',
    schema: SCHEMA,
    generator: 'tools/ue-export/export.cjs',
    spec: 'docs/unreal/spec/08-data-export.md',
    seed: run.seed,
    readFrom: 'the running web game (window.__G, three.js r' + run.three + '), every module real except audio (stubbed by ?noaudio=1: it holds nothing that is exported)',
    units: {
      web: 'metres, seconds, radians; +Y up, north = -Z, east = +X (right-handed)',
      ue: 'centimetres, degrees; +Z up, X = east, Y = south (left-handed)',
    },
    conversion: 'ue (X, Y, Z) = web (x, z, y) * 100; ue yaw = atan2(web z, web x) of a direction = -rotationY of a prop, in degrees',
    numbers: 'rounded to 4 decimals',
  };
}

// ------------------------------------------------------------------------------------------------
// config.json
// ------------------------------------------------------------------------------------------------

/**
 * Turns a plain copy of a config tree into its exported form: {$fn} placeholders are replaced by
 * `describe(path)`, colour numbers by "#rrggbb".
 */
function encodeConfig(value, pathKeys, describe) {
  if (value && typeof value === 'object') {
    if (!Array.isArray(value) && typeof value.$fn === 'string' && Object.keys(value).length === 2) return describe(pathKeys);
    if (Array.isArray(value)) return value.map((v, i) => encodeConfig(v, [...pathKeys, String(i)], describe));
    const out = {};
    for (const key of Object.keys(value)) out[key] = encodeConfig(value[key], [...pathKeys, key], describe);
    return out;
  }
  if (typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 0xffffff && isColourPath(pathKeys)) return K.hexString(value);
  return value;
}

function buildConfig(run, raw, functions, node) {
  const cfg = raw.config.config;
  const describe = (keys) => functions[keys.join('.')];
  const out = {
    meta: {
      ...meta('config.json', run, "Every tuning table the game runs on: G.config as the booted game holds it, plus the explosive rules and the enemy tuning resolved per difficulty. Web units throughout (metres, seconds, radians): convert lengths with x100 on the Unreal side."),
      encoding: {
        colours: 'a colour the game stores as a 0xRRGGBB number is written as "#rrggbb" (sRGB); [r, g, b] arrays are linear radiance and stay arrays',
        infinity: 'JSON has no Infinity: weapons.nine.reserve is the string "Infinity"',
        functions: 'a function in the tables is written as {"$function": {params, source, samples: [{args, value}]}}: the samples are what the running game answered, the source is the text of the function in src/config',
      },
    },
    settings: {
      source: 'G.settings.all() in a clean browser profile (src/core/settings.js): the defaults a first-time player gets',
      storageKey: `${cfg.brand.storagePrefix}.settings.v1`,
      defaults: raw.config.settings,
    },
  };
  for (const name of Object.keys(cfg)) {
    if (name === 'text') continue; // text.json
    out[name] = encodeConfig(cfg[name], [name], describe);
  }
  out.enemiesResolved = {
    source: 'G.enemies.debug().tune after G.enemies.setDifficulty(G.config.enemies.difficulty[name]): the base tables with that difficulty laid over them, as the AI reads them',
    ...encodeConfig(raw.config.enemiesResolved, ['enemiesResolved'], describe),
  };
  out.explosives = {
    source: 'kinds: the rule row every placed explosive carries (G.explosives.items[n].kind). rules: module constants and formulas of src/explosives.js, imported in Node (they are not reachable from window.__G)',
    kinds: raw.config.explosiveKinds,
    rules: node.explosiveRules,
  };
  return out;
}

// ------------------------------------------------------------------------------------------------
// text.json
// ------------------------------------------------------------------------------------------------

function buildText(run, raw, functions, node, signage) {
  const cfg = raw.config.config;
  const describe = (keys) => functions[keys.join('.')];
  const count = (list, keyOf) => {
    const map = new Map();
    for (const item of list) {
      const key = JSON.stringify(keyOf(item));
      if (!map.has(key)) map.set(key, { ...keyOf(item), uses: 0 });
      map.get(key).uses += item.placed;
    }
    return [...map.values()];
  };
  const signs = signage.paintings.filter((p) => p.kind === 'sign');
  const graffiti = signage.paintings.filter((p) => p.kind === 'graffiti');
  const posters = signage.paintings.filter((p) => p.kind === 'poster');
  return {
    meta: {
      ...meta('text.json', run, 'Every string table a player can read: the copy deck (G.config.text), the brand lines, the input glyph and hint tables, the interface labels, the static text of the page, and the lettering painted in the world.'),
      encoding: {
        templates: 'a line that takes a value is written as {"$template": {template, params, formats, source, example}}: `template` has the parameters as {name}; `formats` says how a number is written',
        functions: 'a function that is not a plain template is written as {"$function": {params, source, samples}}',
      },
    },
    brand: {
      source: 'G.config.brand (src/config/brand.js); its colour and font tokens are in config.json',
      title: cfg.brand.title,
      titlePlain: cfg.brand.titlePlain,
      presenter: cfg.brand.presenter,
      starLine: cfg.brand.starLine,
      ipx: cfg.brand.ipx,
    },
    text: { source: 'G.config.text (src/config/text.js)', ...encodeConfig(cfg.text, ['text'], describe) },
    input: {
      source: 'G.config.player (src/config/player.js): what a control is called on each device, the look-mode hints, the captions of the touch buttons [id, glyph, label, caption]',
      glyphs: cfg.player.glyphs,
      hints: cfg.player.hints,
      touchButtons: cfg.player.touchButtons,
    },
    interface: {
      source: 'src/ui/copy.js imported in Node: the HUD and the menus import this file directly, it is not reachable from window.__G',
      ...node.interfaceCopy,
    },
    page: {
      source: 'the static markup of the page as the browser shows it (src/page.html): tab title, boot screen, canvas label',
      title: raw.meta.page.title,
      boot: {
        presenter: raw.meta.page.bootPresenter,
        wordmark: raw.meta.page.bootMark,
        star: raw.meta.page.bootStar,
        note: raw.meta.page.bootNote,
      },
      canvasLabel: raw.meta.page.canvasLabel,
    },
    lettering: {
      source: 'what the level asked the materials library to paint (G.mats.sign / graffiti / poster, heard by lib/hooks.cjs): `uses` is how many quads carry it. Where each one hangs is in level.json `signage`. Poster artwork is drawn by src/mats/paper.js and has no text table.',
      signs: count(signs, (p) => ({ text: p.args[0].text ?? null, sub: p.args[0].sub ?? null, style: p.args[0].style || 'box' })),
      graffiti: count(graffiti, (p) => ({ text: p.args[0] ?? 'RULE' })),
      posters: count(posters, (p) => ({ kind: p.args[0] ?? 'ad', variant: p.args[1] ?? 0 })),
    },
  };
}

// ------------------------------------------------------------------------------------------------
// level.json
// ------------------------------------------------------------------------------------------------

/** Rebuilds the nav grid from the colliders with the constants of src/physics.js: must equal the page's. */
function rebuildNavGrid(colliders, bounds, k) {
  const cols = Math.max(3, Math.ceil((bounds.maxX - bounds.minX) / k.NAV_CELL - 1e-9));
  const rows = Math.max(3, Math.ceil((bounds.maxZ - bounds.minZ) / k.NAV_CELL - 1e-9));
  const blocked = new Uint8Array(cols * rows);
  for (let i = 0; i < cols; i++) blocked[i] = blocked[cols * rows - cols + i] = 1;
  for (let j = 0; j < rows; j++) blocked[j * cols] = blocked[j * cols + cols - 1] = 1;
  const blocking = [];
  colliders.forEach((c, index) => {
    const blocks = !c.noNav && !c.bulletOnly && !c.playerOnly && c.max.y >= k.NAV_BAND_MIN && c.min.y <= k.NAV_BAND_MAX;
    blocking.push(blocks);
    if (!blocks) return;
    const i0 = Math.max(0, Math.ceil((c.min.x - k.NAV_INFLATE - bounds.minX) / k.NAV_CELL - 0.5 - 1e-9));
    const i1 = Math.min(cols - 1, Math.floor((c.max.x + k.NAV_INFLATE - bounds.minX) / k.NAV_CELL - 0.5 + 1e-9));
    const j0 = Math.max(0, Math.ceil((c.min.z - k.NAV_INFLATE - bounds.minZ) / k.NAV_CELL - 0.5 - 1e-9));
    const j1 = Math.min(rows - 1, Math.floor((c.max.z + k.NAV_INFLATE - bounds.minZ) / k.NAV_CELL - 0.5 + 1e-9));
    for (let j = j0; j <= j1; j++) blocked.fill(1, j * cols + i0, j * cols + i1 + 1);
  });
  const grid = [];
  for (let j = 0; j < rows; j++) {
    let line = '';
    for (let i = 0; i < cols; i++) line += blocked[j * cols + i] ? '#' : '.';
    grid.push(line);
  }
  return { cols, rows, grid, blocking };
}

/**
 * A flat face in both spaces: its centre, its bottom-left corner as seen from in front of it (the pivot
 * of a wall module), its axes, and the rotation that lays a plane mesh on it (see the spec).
 */
function faceBlocks(q) {
  const corner = {
    x: q.pos.x - (q.right.x * q.w) / 2 - (q.up.x * q.h) / 2,
    y: q.pos.y - (q.right.y * q.w) / 2 - (q.up.y * q.h) / 2,
    z: q.pos.z - (q.right.z * q.w) / 2 - (q.up.z * q.h) / 2,
  };
  return {
    web: { pos: K.webPoint(q.pos), corner: K.webPoint(corner), right: K.webDir(q.right), up: K.webDir(q.up), normal: K.webDir(q.normal), width: K.round(q.w), height: K.round(q.h) },
    ue: { pos: K.uePoint(q.pos), corner: K.uePoint(corner), right: K.ueDir(q.right), up: K.ueDir(q.up), normal: K.ueDir(q.normal), rotator: K.ueRotatorOfAxes(q.right, q.up), width: K.ueLength(q.w), height: K.ueLength(q.h) },
  };
}

function buildLevel(run, raw, node, propNames) {
  const L = raw.level;
  const consts = node.physics;

  if (!sameJson(L.bounds, L.physicsBounds)) fail('the play bounds of the level and of the physics differ');

  // -- Colliders
  const nav = rebuildNavGrid(L.colliders, L.bounds, consts);
  if (nav.cols !== L.nav.cols || nav.rows !== L.nav.rows || !sameJson(nav.grid, L.nav.grid)) {
    fail('the nav grid rebuilt from the exported colliders with the constants read from src/physics.js is not the grid the game built');
  }
  const colliders = L.colliders.map((c, index) => {
    if (c.by === null) fail(`collider ${index} (${c.tag}) was added without the hooks seeing it`);
    let owner = { kind: 'level' };
    if (c.prop !== null) owner = { kind: 'prop', prop: c.prop, name: propNames[c.prop] };
    else if (c.explosive !== null) owner = { kind: 'explosive', explosive: c.explosive, type: L.explosives[c.explosive].type };
    return {
      index,
      tag: c.tag,
      surface: c.surface,
      owner,
      blocks: { movement: !c.bulletOnly, shots: !c.playerOnly, nav: nav.blocking[index] },
      flags: { bulletOnly: c.bulletOnly, playerOnly: c.playerOnly, noNav: c.noNav },
      orientedBox: c.oriented,
      web: { min: K.webPoint(c.min), max: K.webPoint(c.max) },
      ue: K.ueBox(c.min, c.max),
    };
  });
  const tally = (list, keyOf) => {
    const out = {};
    for (const item of list) out[keyOf(item)] = (out[keyOf(item)] || 0) + 1;
    return Object.fromEntries(Object.entries(out).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));
  };

  const orientedBoxes = L.oriented.map((o, index) => {
    const first = L.colliders[o.boxes[0]];
    return {
      index,
      prop: first.prop,
      name: first.prop !== null ? propNames[first.prop] : null,
      tag: first.tag,
      colliders: o.boxes,
      web: { center: K.webPoint(o.center), size: K.webPoint(o.size), rotationY: K.round(o.yaw) },
      ue: { center: K.uePoint(o.center), extent: { X: K.round(K.ueLength(o.size.x) / 2), Y: K.round(K.ueLength(o.size.z) / 2), Z: K.round(K.ueLength(o.size.y) / 2) }, yaw: K.ueYawOfRotationY(o.yaw) },
    };
  });

  // -- Zones and ground
  const zoneOf = (r) => {
    const x = (r.minX + r.maxX) / 2;
    const z = (r.minZ + r.maxZ) / 2;
    const zone = L.zoneRects.find((q) => x > q.minX && x < q.maxX && z > q.minZ && z < q.maxZ);
    return zone ? zone.value : null;
  };
  const rect = (r) => ({ web: K.webRect(r), ue: K.ueRect(r) });

  // -- The El
  const tagged = (tag) => colliders.filter((c) => c.tag === tag);
  const columns = tagged('el-column').map((c) => {
    const x = K.round((c.web.min.x + c.web.max.x) / 2);
    const z = K.round((c.web.min.z + c.web.max.z) / 2);
    return {
      collider: c.index,
      row: z < 0 ? 'north' : 'south',
      insideBounds: x > L.bounds.minX && x < L.bounds.maxX,
      web: { x, z, top: c.web.max.y, halfWidth: K.round((c.web.max.x - c.web.min.x) / 2) },
      ue: { X: K.ueLength(x), Y: K.ueLength(z), top: K.ueLength(c.web.max.y), halfWidth: K.ueLength((c.web.max.x - c.web.min.x) / 2) },
    };
  });
  const girders = tagged('el-girder').map((c) => ({
    collider: c.index,
    kind: c.web.max.x - c.web.min.x > c.web.max.z - c.web.min.z ? 'longitudinal' : 'cross',
    web: c.web,
    ue: c.ue,
  }));
  const deckBox = tagged('el-deck');
  if (deckBox.length !== 1) fail(`expected one el-deck collider, found ${deckBox.length}`);
  if (columns.length === 0 || columns.length % 2) fail(`expected pairs of El columns, found ${columns.length}`);
  const bentXs = [...new Set(columns.map((c) => c.web.x))].sort((a, b) => a - b);

  // -- The train (timelines from src/atmos/plan.js with the game's own numbers, checked against a real pass)
  const T = raw.train;
  const trainCfg = raw.config.config.look.train;
  const length = raw.atmos.train.length;
  const tracks = [...L.el.tracks].sort((a, b) => a - b);
  const timelines = {};
  for (const dir of [1, -1]) {
    const tl = node.plan.trainTimeline({ minX: L.bounds.minX, maxX: L.bounds.maxX, dir, speed: trainCfg.speed, length, runUp: trainCfg.runUp });
    const z = dir > 0 ? tracks[tracks.length - 1] : tracks[0];
    const from = { x: tl.start, y: L.el.deckTop, z };
    const to = { x: tl.head(tl.tEnd), y: L.el.deckTop, z };
    timelines[dir] = {
      dir,
      heading: dir > 0 ? 'east' : 'west',
      track: dir > 0 ? 'south' : 'north',
      seconds: { approach: tl.approach, over: tl.over, gone: tl.gone, total: tl.tEnd },
      web: { from: K.webPoint(from), to: K.webPoint(to), trackZ: K.round(z), railTop: K.round(L.el.deckTop), forward: K.webDir({ x: dir, y: 0, z: 0 }) },
      ue: { from: K.uePoint(from), to: K.uePoint(to), trackY: K.ueLength(z), railTop: K.ueLength(L.el.deckTop), yaw: K.ueYawOfDir({ x: dir, y: 0, z: 0 }) },
    };
  }
  // What the game announced while the first two trains crossed.
  const passes = [];
  for (const begun of T.begun) {
    const events = T.events.filter((e) => e.pass === begun.pass);
    const phase = (name) => events.find((e) => e.phase === name);
    const tl = timelines[begun.dir];
    for (const name of ['approach', 'over', 'gone']) {
      const e = phase(name);
      if (!e) fail(`the train's pass ${begun.pass} never announced '${name}'`);
      if (Math.abs(e.duration - tl.seconds[name]) > 1e-9) fail(`train:pass ${name} lasted ${e.duration} s in the game, ${tl.seconds[name]} s by src/atmos/plan.js`);
    }
    if (Math.abs(begun.z - tl.web.trackZ) > 1e-9) fail(`pass ${begun.pass} ran on z ${begun.z}, expected ${tl.web.trackZ}`);
    passes.push({
      pass: begun.pass,
      dir: begun.dir,
      heading: tl.heading,
      trackZ: begun.z,
      clock: { begins: begun.clock, over: phase('over').clock, gone: phase('gone').clock, ended: (phase('ended') || {}).clock ?? null },
    });
  }
  if (passes.length < 2 || passes[0].dir !== 1 || passes[1].dir !== -1) fail('expected the first two trains to run east, then west');
  const gap = passes[1].clock.begins - passes[0].clock.begins;
  if (gap < trainCfg.every[0] || gap > trainCfg.every[1] + 0.1) fail(`the second train began ${gap} s after the first, outside ${trainCfg.every}`);

  // -- Facades: where every window of the painted grids is (src/mats/layout.js, the painter's own layout)
  const grids = {};
  for (const g of raw.glass.grids) {
    if (!g.grid) fail(`facade ${g.material} has no window grid`);
    const spec = node.matsLayout.facadeSpec(g.spec);
    if (Math.abs(spec.w - g.grid.w) > 1e-9 || Math.abs(spec.h - g.grid.h) > 1e-9) fail(`facade ${g.material}: src/mats/layout.js gives another repeat than the page`);
    grids[g.material] = { spec, layout: node.matsLayout.facadeLayout(spec), asked: g.asked };
  }
  const facades = raw.glass.faces.map((f, index) => {
    const g = grids[f.material];
    if (!g) fail(`a wall face uses ${f.material}, which the level never asked for`);
    const { spec, layout } = g;
    // The grid repeats along the wall and stops above its top floor; `u0`/`v0` is the wall's foot corner
    // in grid metres. A window counts when all of it is on the face.
    const windows = [];
    const first = Math.floor(f.u0 / spec.w) - 1;
    const last = Math.ceil((f.u0 + f.w) / spec.w) + 1;
    for (let k = first; k <= last; k++) {
      for (const win of layout.windows) {
        const u = win.x + k * spec.w - f.u0;
        const v = win.y - f.v0;
        if (u < -1e-6 || u + win.w > f.w + 1e-6 || v < -1e-6 || v + win.h > f.h + 1e-6) continue;
        const cu = u + win.w / 2 - f.w / 2;
        const cv = v + win.h / 2 - f.h / 2;
        const pos = { x: f.pos.x + f.right.x * cu + f.up.x * cv, y: f.pos.y + f.right.y * cu + f.up.y * cv, z: f.pos.z + f.right.z * cu + f.up.z * cv };
        windows.push({ floor: win.floor, bay: win.bay, state: win.state, ac: win.ac, bars: win.bars, pos });
      }
    }
    windows.sort((a, b) => a.pos.y - b.pos.y || (a.pos.x - b.pos.x) * f.right.x + (a.pos.z - b.pos.z) * f.right.z);
    return { index, material: f.material, base: spec.base, zone: f.zone, place: f.place, face: f, spec, layout, windows };
  });

  const signage = buildSignage(raw.signage);

  // Window glass. A pane that lies inside a placed prop which is built with that glass (a bus shelter, a
  // booth) belongs to the prop; the rest is the level's own glazing.
  const propOfPane = (pane) => {
    const list = raw.props.instances;
    for (let i = 0; i < list.length; i++) {
      const inst = list[i];
      const d = raw.props.described[inst.name][inst.proto];
      if (!d || !d.bounds || !d.slots.some((slot) => slot.split('|')[0] === pane.material)) continue;
      const dx = pane.pos.x - inst.pos.x;
      const dy = pane.pos.y - inst.pos.y;
      const dz = pane.pos.z - inst.pos.z;
      const cos = Math.cos(inst.rotation.y);
      const sin = Math.sin(inst.rotation.y);
      const lx = dx * cos - dz * sin; // back into the prop's own frame
      const lz = dx * sin + dz * cos;
      const b = d.bounds;
      const e = 0.03;
      if (lx >= b.min.x - e && lx <= b.max.x + e && dy >= b.min.y - e && dy <= b.max.y + e && lz >= b.min.z - e && lz <= b.max.z + e) return i;
    }
    return null;
  };
  const panes = raw.glass.panes.filter((p) => !p.material.startsWith('glass_car')).map((p) => ({ ...p, prop: propOfPane(p) }));

  // -- Buildings: the layout table's footprints, with the colliders the level made of them
  const buildings = Object.entries(node.layout.BUILDINGS).map(([id, b]) => {
    const own = tagged(b.name);
    if (!own.length) fail(`no collider is tagged '${b.name}' (building ${id} of src/level/layout.js)`);
    const roof = node.layout.buildingHeight(b);
    const top = Math.max(...own.map((c) => c.web.max.y));
    const footprint = { minX: b.x0, maxX: b.x1, minZ: b.z0, maxZ: b.z1 };
    return {
      id,
      name: b.name,
      wall: b.base,
      floors: b.floors,
      colliders: own.map((c) => c.index),
      web: { ...K.webRect(footprint), roof: K.round(roof), parapetTop: K.round(top) },
      ue: { ...K.ueRect(footprint), roof: K.ueLength(roof), parapetTop: K.ueLength(top) },
    };
  });

  const level = {
    meta: {
      ...meta('level.json', run, 'The block as the running game built it: bounds, zones, every collider, the points the game flow and the AI use, the El and its train, the nav grid, and where every sign and window is.'),
      counts: {
        colliders: colliders.length,
        orientedBoxes: orientedBoxes.length,
        enemySpawns: { ground: L.spawns.filter((s) => s.type === 'ground').length, air: L.spawns.filter((s) => s.type === 'air').length },
        coverPoints: L.coverPoints.length,
        explosives: L.explosives.length,
        objectives: L.objectives.length,
        signagePaintings: signage.paintings.length,
        signagePlacements: signage.placements.length,
        glazing: panes.length,
        facades: facades.length,
      },
    },
    bounds: { source: 'G.level.bounds (= G.physics.bounds): the play area and the extent of the nav grid; the ground is the plane y = 0', ...rect(L.bounds) },
    zones: L.zones.map((z) => ({ id: z.id, name: z.name, ...rect(z) })),
    places: {
      source: "G.level.zoneName(x, z) sampled on a 0.1 m grid: the name the minimap band shows. The east zone ('lot') is THE CAGE north of the avenue, THE LOT south of it, THE AVENUE on the roadway between them.",
      regions: L.places.map((p) => ({ name: p.value, zone: zoneOf(p), ...rect(p) })),
    },
    ground: {
      source: 'G.level.groundSurfaceAt(x, z) and G.level.floorAt(x, z) sampled on a 0.1 m grid. `surfaces`: what the bare ground plane is made of (footsteps, impacts; boxes standing on it report their own). `floors`: height of the level\'s own walking surface (0 the roadway, 0.15 a sidewalk slab).',
      surfaces: L.surfaces.map((s) => ({ surface: s.value, ...rect(s) })),
      floors: L.floors.map((f) => ({ height: { web: K.round(f.value), ue: K.ueLength(f.value) }, ...rect(f) })),
    },
    playerStart: {
      source: 'G.level.playerStart: feet position and heading (web yaw: 0 looks at -Z, positive turns left)',
      zone: zoneOfPoint(L, L.playerStart.pos),
      web: { pos: K.webPoint(L.playerStart.pos), yaw: K.round(L.playerStart.yaw), facing: K.webDir(K.forwardOfHeading(L.playerStart.yaw)) },
      ue: { pos: K.uePoint(L.playerStart.pos), yaw: K.ueYawOfHeading(L.playerStart.yaw) },
    },
    objectives: L.objectives.map((o, index) => ({
      index,
      id: o.id,
      code: o.code,
      label: o.label,
      zone: o.zone,
      place: o.place,
      interior: o.interior > 0.5,
      prop: o.prop,
      web: { pos: K.webPoint(o.pos), rotationY: K.round(o.yaw), forward: K.webDir(K.forwardOfRotationY(o.yaw)) },
      ue: { pos: K.uePoint(o.pos), yaw: K.ueYawOfRotationY(o.yaw) },
    })),
    extraction: {
      source: 'G.level.extraction: the zone behind the truck\'s rear doors; reaching it with all reels ends the mission',
      label: L.extraction.label,
      code: L.extraction.code,
      zone: L.extraction.zone,
      place: L.extraction.place,
      web: { pos: K.webPoint(L.extraction.pos), radius: K.round(L.extraction.radius) },
      ue: { pos: K.uePoint(L.extraction.pos), radius: K.ueLength(L.extraction.radius) },
      truck: {
        prop: L.extraction.prop,
        web: { pos: K.webPoint(L.extraction.truck.pos), rotationY: K.round(L.extraction.truck.yaw), forward: K.webDir(K.forwardOfRotationY(L.extraction.truck.yaw)) },
        ue: { pos: K.uePoint(L.extraction.truck.pos), yaw: K.ueYawOfRotationY(L.extraction.truck.yaw) },
      },
    },
    enemySpawns: {
      source: `G.level.enemySpawns (after the level moved blocked points to walkable cells). \`facing\` is NOT game data: the game keeps none and gives a new enemy a random yaw. It is derived here: a ground point looks toward the walkable nav cells it can reach in a straight line within ${L.spawnReach} m ('opening'), an air point toward the middle of the block ('centre').`,
      points: L.spawns.map((s, index) => ({
        index,
        type: s.type,
        zone: s.zone,
        place: s.place,
        interior: s.interior > 0.5,
        facingSource: s.facingSource,
        web: { pos: K.webPoint(s.pos), facing: K.webDir(s.facing) },
        ue: { pos: K.uePoint(s.pos), yaw: K.ueYawOfDir(s.facing) },
      })),
    },
    coverPoints: {
      source: 'G.level.coverPoints: standing spots beside something solid that the Goons prefer as fire positions (config.json enemies.goon.cover, positionCost.cover)',
      points: L.coverPoints.map((c, index) => ({ index, zone: c.zone, place: c.place, interior: c.interior > 0.5, onDeck: c.pos.y > 0.5, web: { pos: K.webPoint(c.pos) }, ue: { pos: K.uePoint(c.pos) } })),
    },
    explosives: {
      source: 'G.level.explosives, with the state of the matching G.explosives.items entry. Rules per type: config.json explosives.kinds.',
      items: L.explosives.map((e, index) => {
        if (!e.item) fail(`explosive ${index} has no matching item in G.explosives.items`);
        return {
          index,
          type: e.type,
          prop: e.item.prop,
          hp: e.item.hp,
          zone: e.zone,
          place: e.place,
          interior: e.interior > 0.5,
          collider: e.item.collider,
          web: { pos: K.webPoint(e.pos), rotationY: K.round(e.yaw), forward: K.webDir(K.forwardOfRotationY(e.yaw)) },
          ue: { pos: K.uePoint(e.pos), yaw: K.ueYawOfRotationY(e.yaw) },
        };
      }),
    },
    interior: {
      source: 'G.level.interiorBoxes and G.level.interiorAt(pos): 1 inside a box, falling linearly to 0 over `fade` outside it (audio reverb, exposure). doorways: the openings the Buzzards fly in through, found by the AI itself (G.enemies.debug().doorways).',
      fade: { web: K.round(L.interiorFade), ue: K.ueLength(L.interiorFade) },
      boxes: L.interiorBoxes.map((b) => ({ web: { min: K.webPoint(b.min), max: K.webPoint(b.max) }, ue: K.ueBox(b.min, b.max) })),
      doorways: (L.doorways || []).map(([ox, oz, ix, iz, y]) => ({
        web: { outside: K.webPoint({ x: ox, y, z: oz }), inside: K.webPoint({ x: ix, y, z: iz }) },
        ue: { outside: K.uePoint({ x: ox, y, z: oz }), inside: K.uePoint({ x: ix, y, z: iz }) },
      })),
    },
    vantage: {
      source: 'G.level.vantage: the scaffold shed in front of S3 (foot of its stair, a point on its deck)',
      web: { stairsFoot: K.webPoint(L.vantage.stairsFoot), deck: K.webPoint(L.vantage.deck) },
      ue: { stairsFoot: K.uePoint(L.vantage.stairsFoot), deck: K.uePoint(L.vantage.deck) },
    },
    cinematicPath: {
      source: 'G.level.cinematicPath: the title fly-through, a closed loop through these held compositions (timing: config.json flow.titleCamera)',
      points: L.cinematicPath.map((p, index) => {
        const dir = { x: p.look.x - p.pos.x, y: p.look.y - p.pos.y, z: p.look.z - p.pos.z };
        return { index, web: { pos: K.webPoint(p.pos), look: K.webPoint(p.look) }, ue: { pos: K.uePoint(p.pos), look: K.uePoint(p.look), rotator: K.ueRotatorOfDir(dir) } };
      }),
    },
    steam: {
      source: 'G.level.steam: where steam rises (manholes, the alley, the lane, the dig\'s vent stack)',
      vents: L.steam.map((p) => ({ web: { pos: K.webPoint(p) }, ue: { pos: K.uePoint(p) } })),
    },
    puddles: {
      source: 'G.level.puddles: where water stands on the street (by day the street is dry outside the open hydrant\'s reach)',
      pools: L.puddles.map((p) => ({ web: { x: K.round(p.x), z: K.round(p.z), radius: K.round(p.r) }, ue: { X: K.ueLength(p.x), Y: K.ueLength(p.z), radius: K.ueLength(p.r) } })),
    },
    buildings: {
      source: "the solid buildings inside the bounds: footprint, wall material and storey count from src/level/layout.js BUILDINGS (imported in Node), roof height from its buildingHeight(), and the colliders the booted level tagged with the building's name (`parapetTop` is their top). `backs` are the neighbours' backs that seal the north, east and south edges, just outside the bounds.",
      storeys: { web: { ground: node.layout.GROUND_FLOOR, upper: node.layout.FLOOR }, ue: { ground: K.ueLength(node.layout.GROUND_FLOOR), upper: K.ueLength(node.layout.FLOOR) } },
      list: buildings,
      backs: tagged('backs').map((c) => c.index),
    },
    el: {
      source: 'deck: G.level.el. columns, girders, deckCollider, station: the colliders tagged el-column / el-girder / el-deck / station. layout: the constants of src/level/layout.js (EL, STATION), imported in Node.',
      deck: {
        web: { underside: K.round(L.el.y), railTop: K.round(L.el.deckTop), minX: K.round(L.el.minX), maxX: K.round(L.el.maxX), minZ: K.round(L.el.minZ), maxZ: K.round(L.el.maxZ), tracksZ: L.el.tracks.map((z) => K.round(z)) },
        ue: { underside: K.ueLength(L.el.y), railTop: K.ueLength(L.el.deckTop), minX: K.ueLength(L.el.minX), maxX: K.ueLength(L.el.maxX), minY: K.ueLength(L.el.minZ), maxY: K.ueLength(L.el.maxZ), tracksY: L.el.tracks.map((z) => K.ueLength(z)) },
      },
      bents: { count: bentXs.length, web: { x: bentXs }, ue: { X: bentXs.map((x) => K.ueLength(x)) } },
      columns,
      girders,
      deckCollider: deckBox[0].index,
      station: tagged('station').map((c) => c.index),
      layout: { EL: node.layout.EL, STATION: node.layout.STATION },
    },
    train: {
      source: 'config: G.config.look.train. tracks: src/atmos/plan.js trainTimeline() run in Node with the game\'s own bounds, speed, length and run-up, and checked against the durations the running game announced (train:pass). observed: the first two trains of this boot, timed on the atmosphere\'s clock (seconds of un-paused time since boot).',
      cars: trainCfg.cars,
      carLength: trainCfg.carLength,
      carGap: trainCfg.carGap,
      carWidth: trainCfg.carWidth,
      carHeight: trainCfg.carHeight,
      length: { web: K.round(length), ue: K.ueLength(length) },
      speed: { web: K.round(trainCfg.speed), ue: K.ueLength(trainCfg.speed) },
      runUp: { web: K.round(trainCfg.runUp), ue: K.ueLength(trainCfg.runUp) },
      origin: 'the nose of the train is the moving point; the cars trail behind it; y is the rail top',
      tracks: [timelines[1], timelines[-1]],
      schedule: {
        rule: 'The first train starts so that its nose reaches the block `firstOverhead` seconds after boot; every later one starts `every[0]`..`every[1]` seconds (uniform) after the one before it started. Directions alternate, eastbound first. The clock stops while the game is paused.',
        firstOverhead: trainCfg.firstPass,
        firstStart: K.round(Math.max(1, trainCfg.firstPass - timelines[1].seconds.approach)),
        every: trainCfg.every,
        firstDir: 1,
        alternates: true,
      },
      observed: passes,
    },
    nav: {
      source: 'G.physics.nav: the occupancy grid the Goons path on (A* on cell centres, 8 neighbours, string-pulled). The rule constants are read from src/physics.js; the grid rebuilt from `colliders` with them equals the game\'s cell for cell.',
      web: { cell: L.nav.cell, origin: { x: L.nav.origin.x, z: L.nav.origin.z }, inflate: consts.NAV_INFLATE, bandMin: consts.NAV_BAND_MIN, bandMax: consts.NAV_BAND_MAX },
      ue: { cell: K.ueLength(L.nav.cell), origin: { X: K.ueLength(L.nav.origin.x), Y: K.ueLength(L.nav.origin.z) }, inflate: K.ueLength(consts.NAV_INFLATE), bandMin: K.ueLength(consts.NAV_BAND_MIN), bandMax: K.ueLength(consts.NAV_BAND_MAX) },
      cols: L.nav.cols,
      rows: L.nav.rows,
      rule: 'cell (i, j) covers x origin.x + i*cell .. + cell and z origin.z + j*cell .. + cell. It is blocked when its centre lies within `inflate` of a collider that blocks nav: not noNav, not bulletOnly, not playerOnly, top at or above bandMin and bottom at or below bandMax. The outer ring is always blocked.',
      free: L.nav.free,
      blocked: L.nav.blocked,
      grid: { rows: 'one string per row j (north to south), one character per cell i (west to east): # blocked, . free', cells: L.nav.grid },
    },
    physics: {
      source: 'constants of src/physics.js, read from the source text (module-private): how a body moves over the colliders',
      ...consts,
    },
    colliders: {
      source: 'G.physics.boxes, in the order they were added: every static collision box of the block (axis-aligned). tag: what the level calls it. owner: the placed prop (index into props.json instances) or the explosive (index into `explosives.items`) it belongs to, else the level itself. blocks: movement (bodies), shots (rays: rounds and sight), nav (stamped into the nav grid). A prop that stands at an angle is approximated by several boxes: `orientedBox` points at the true box in `orientedBoxes`.',
      byTag: tally(colliders, (c) => c.tag),
      byOwner: tally(colliders, (c) => c.owner.kind),
      bySurface: tally(colliders, (c) => c.surface),
      boxes: colliders,
    },
    orientedBoxes: {
      source: 'every G.physics.addOriented call (heard by lib/hooks.cjs): the box as it was asked for, before it was sliced into axis-aligned pieces. All of them are prop colliders. extent = half size along the box\'s own X (length), Y (width), Z (height).',
      boxes: orientedBoxes,
    },
    signage,
    glazing: {
      source: "every flat four-cornered face of the level drawn with one of the catalogue's window glass materials (read from the merged level meshes). glass_lit_warm / glass_lit_cool glow at night (config.json catalog.MATERIALS); by day all of them are dark reflective glass. prop: the placed prop the pane is part of (a bus shelter, a booth: props.json instance), null for the level's own windows. Car glass is not listed.",
      byMaterial: tally(panes, (p) => p.material),
      panes: panes.map((p, index) => ({ index, material: p.material, prop: p.prop, zone: p.zone, place: p.place, interior: p.interior > 0.5, ...faceBlocks(p) })),
    },
    facades: {
      source: 'wall faces that carry a painted window grid (G.mats.facade), read from the merged level meshes; the windows are placed with the painter\'s own layout (src/mats/layout.js facadeLayout, imported in Node). The grid repeats along the wall every `grid.width` and is bare wall above its top floor. state: dark | warm (a lamp-lit room) | tv (television blue): lit ones glow at night only.',
      grids: Object.fromEntries(
        Object.entries(grids).map(([name, g]) => [
          name,
          {
            base: g.spec.base,
            seed: g.spec.seed,
            litFraction: g.spec.lit,
            bays: g.spec.bays,
            floors: g.spec.floors,
            web: { bayWidth: g.spec.bayW, floorHeight: g.spec.floorH, width: g.spec.w, height: g.spec.h, windowWidth: K.round(g.layout.windows[0].w), windowHeight: K.round(g.layout.windows[0].h), sill: K.round(g.layout.windows.find((w) => w.floor === 0).y) },
            ue: { bayWidth: K.ueLength(g.spec.bayW), floorHeight: K.ueLength(g.spec.floorH), width: K.ueLength(g.spec.w), height: K.ueLength(g.spec.h), windowWidth: K.ueLength(g.layout.windows[0].w), windowHeight: K.ueLength(g.layout.windows[0].h), sill: K.ueLength(g.layout.windows.find((w) => w.floor === 0).y) },
            style: { frame: K.hexString(g.layout.style.frame), stone: K.hexString(g.layout.style.stone), lintel: g.layout.style.lintel, paired: g.layout.style.paired },
            windowsPerRepeat: g.layout.windows.length,
            litPerRepeat: g.layout.windows.filter((w) => w.state !== 'dark').length,
          },
        ]),
      ),
      faces: facades.map((f) => ({
        index: f.index,
        grid: f.material,
        base: f.base,
        zone: f.zone,
        place: f.place,
        gridOrigin: { u: K.round(f.face.u0), v: K.round(f.face.v0) },
        ...faceBlocks(f.face),
        windows: f.windows.map((w) => ({ floor: w.floor, bay: w.bay, state: w.state, ac: w.ac, web: { pos: K.webPoint(w.pos) }, ue: { pos: K.uePoint(w.pos) } })),
      })),
    },
    layout: {
      source: 'src/level/layout.js imported in Node: the table of footprints, heights and openings the level is built from. It is module data, not reachable from window.__G; the booted level is checked against it (bounds, zones, sidewalks, the El). Web metres; boxes are [x0, x1, z0, z1].',
      ...node.layoutTables,
    },
  };
  return { level, facades, panes };
}

function zoneOfPoint(L, p) {
  const zone = L.zoneRects.find((q) => p.x >= q.minX && p.x <= q.maxX && p.z >= q.minZ && p.z <= q.maxZ);
  return zone ? zone.value : null;
}

/** Signs, posters, graffiti and decals: what was painted, and every quad that carries it. */
function buildSignage(S) {
  if (S.unmatched) fail(`${S.unmatched} quads of the sign atlas could not be matched to a painting`);
  const unplaced = S.paintings.filter((p) => !p.placed);
  if (unplaced.length) fail(`${unplaced.length} paintings were asked for but hang nowhere: ${JSON.stringify(unplaced.map((p) => p.args))}`);
  const colourOf = (n) => (typeof n === 'number' ? K.hexString(n) : n ?? null);
  const paintings = S.paintings.map((p, index) => {
    const base = { index, kind: p.kind, uses: p.placed, tiles: p.tiles, web: { width: K.round(p.w), height: K.round(p.h) }, ue: { width: K.ueLength(p.w), height: K.ueLength(p.h) } };
    if (p.kind === 'sign') {
      const s = p.args[0] || {};
      const style = s.style || 'box';
      // src/mats.js: a sign is lit unless it is painted (lit only when asked) or a stencil (never).
      const lit = style === 'stencil' ? false : style === 'painted' ? s.lit === true : s.lit !== false;
      return { ...base, text: s.text ?? null, sub: s.sub ?? null, style, lit, fg: colourOf(s.fg), bg: colourOf(s.bg), glow: colourOf(s.glow), bullet: s.bullet ?? null, bulletColor: colourOf(s.bulletColor) };
    }
    if (p.kind === 'poster') return { ...base, poster: p.args[0] ?? 'ad', variant: p.args[1] ?? 0 };
    if (p.kind === 'graffiti') return { ...base, text: p.args[0] ?? 'RULE', variant: p.args[1] ?? 0, color: colourOf(p.args[2]) };
    return { ...base, decal: p.args[0] ?? 'grime', variant: p.args[1] ?? 0 };
  });
  const placements = S.quads.map((q, index) => ({
    index,
    painting: q.painting,
    kind: paintings[q.painting].kind,
    label: paintings[q.painting].text ?? paintings[q.painting].poster ?? paintings[q.painting].decal ?? null,
    zone: q.zone,
    place: q.place,
    interior: q.interior > 0.5,
    onGround: q.normal.y > 0.9,
    ...faceBlocks(q),
  }));
  const kinds = {};
  for (const p of paintings) kinds[p.kind] = (kinds[p.kind] || 0) + 1;
  return {
    source: "paintings: every G.mats.sign / poster / graffiti / decal the level asked for (heard by lib/hooks.cjs). placements: the quads that carry them, read from the level's meshes (a quad of an atlas page whose texture rectangle is a painting's rectangle is that painting). right = reading direction, up = up the picture, normal = the side it shows. A tiling painting (road paint, a crosswalk) repeats along a quad of any length.",
    counts: { paintings: kinds, placements: placements.length },
    paintings,
    placements,
  };
}

// ------------------------------------------------------------------------------------------------
// props.json
// ------------------------------------------------------------------------------------------------

/** Keys of a kit.place() options object that place the prop rather than shape it (src/level/kit.js). */
const PLACEMENT_KEYS = new Set(['y', 'collide', 'noNav', 'lamps', 'priority', 'cast']);

const shapeOptions = (opts) => Object.fromEntries(Object.entries(opts).filter(([k]) => !PLACEMENT_KEYS.has(k) && k !== 'seed' && k !== 'color').sort(([a], [b]) => (a < b ? -1 : 1)));
const optionsKey = (opts) => JSON.stringify(shapeOptions(opts));

/** Smallest period of a sequence (a seed picks variant seed % n). */
function periodOf(list) {
  for (let p = 1; p <= list.length / 2; p++) {
    if (list.every((v, i) => v === list[i % p])) return p;
  }
  return list.length;
}

function colliderBlocks(c) {
  return {
    surface: c.surface,
    flags: { bulletOnly: c.bulletOnly, playerOnly: c.playerOnly, noNav: c.noNav },
    web: { min: K.webPoint(c.min), max: K.webPoint(c.max) },
    ue: K.ueBox(c.min, c.max),
  };
}

function buildProps(run, raw, node) {
  const P = raw.props;
  const L = raw.level;
  const catalog = raw.config.config.catalog.PROPS;
  const probes = new Map(raw.probe.map((p) => [`${p.name}|${optionsKey(p.opts)}`, p]));
  const objectiveOf = new Map(L.objectives.map((o) => [o.prop, o.id]));

  if (L.propsStats && L.propsStats.fallbacks.length) fail(`prop builders failed and plain boxes stand in: ${L.propsStats.fallbacks.join(', ')}`);

  // -- Catalogue
  const types = {};
  for (const name of Object.keys(catalog)) {
    const def = catalog[name];
    const probe = probes.get(`${name}|{}`);
    if (!probe) fail(`the catalogue probe has no default build of '${name}'`);
    if (probe.error) fail(`props.build('${name}') threw: ${probe.error}`);
    const family = node.propFamilies[name];
    if (!family) fail(`no file under src/props registers '${name}'`);
    const front = family === 'vehicles' || name === 'hoop' ? 'x' : 'z';
    const [length, height, width] = def.size;
    const variantsOf = (p) => {
      const n = periodOf(p.protos);
      return Array.from({ length: n }, (_, v) => {
        const d = p.described[p.protos[v]];
        return {
          variant: v,
          shape: d.shape,
          triangles: d.triangles,
          materialSlots: d.slots,
          bounds: d.bounds ? { web: { min: K.webPoint(d.bounds.min), max: K.webPoint(d.bounds.max) }, ue: K.ueBox(d.bounds.min, d.bounds.max) } : null,
          colliders: d.colliders.map(colliderBlocks),
          lights: d.lights.map((l) => ({
            kind: l.kind,
            color: typeof l.color === 'number' ? K.colour(l.color) : null,
            intensity: l.intensity,
            range: l.range === null ? null : { web: K.round(l.range), ue: K.ueLength(l.range) },
            web: { pos: K.webPoint(l.pos), dir: l.dir ? K.webDir(l.dir) : null },
            ue: { pos: K.uePoint(l.pos), dir: l.dir ? K.ueDir(l.dir) : null },
          })),
          anchors: Object.fromEntries(Object.entries(d.anchors).map(([id, a]) => [id, { web: { pos: K.webPoint(a.pos), dir: K.webDir(a.dir) }, ue: { pos: K.uePoint(a.pos), dir: K.ueDir(a.dir) } }])),
          movingParts: d.nodes,
        };
      });
    };
    const d0 = probe.described[probe.protos[0]];
    const paints = [...new Set(probe.paints.filter((p) => p !== null))];
    const domes = probe.domes.filter((x) => x !== null);
    types[name] = {
      family,
      surface: def.surface,
      dynamic: !!def.dynamic || d0.dynamic,
      noCollide: !!def.noCollide,
      stateful: d0.stateful,
      animated: d0.animated,
      state: d0.state,
      front: { web: `+${front}`, ue: front === 'x' ? '+X' : '+Y', blender: front === 'x' ? '+X' : '-Y' },
      size: { web: { length, height, width }, ue: { X: K.ueLength(length), Y: K.ueLength(width), Z: K.ueLength(height) } },
      paint: paints.length ? { palette: paints.map((c) => K.hexString(c)), domeLightShare: domes.length ? K.round(domes.filter(Boolean).length / domes.length) : null } : null,
      variants: variantsOf(probe),
      options: [...probes.values()]
        .filter((p) => p.name === name && optionsKey(p.opts) !== '{}')
        .map((p) => {
          if (p.error) fail(`props.build('${name}', ${JSON.stringify(p.opts)}) threw: ${p.error}`);
          const pp = [...new Set(p.paints.filter((c) => c !== null))];
          return { options: shapeOptions(p.opts), paint: pp.length ? pp.map((c) => K.hexString(c)) : null, variants: variantsOf(p) };
        }),
    };
  }

  // -- Instances the level placed
  const instances = P.instances.map((inst, index) => {
    if (!(inst.name in catalog)) fail(`placed prop ${index} '${inst.name}' is not in the catalogue`);
    if (inst.fallback) fail(`placed prop ${index} '${inst.name}' is a fallback box: its builder failed`);
    if (Math.abs(inst.rotation.x) > 1e-9 || Math.abs(inst.rotation.z) > 1e-9) fail(`placed prop ${index} '${inst.name}' is tilted: the export only carries a yaw`);
    if (Math.abs(inst.scale.x - 1) > 1e-9 || Math.abs(inst.scale.y - 1) > 1e-9 || Math.abs(inst.scale.z - 1) > 1e-9) fail(`placed prop ${index} '${inst.name}' is scaled`);
    if (inst.seed === null) fail(`placed prop ${index} '${inst.name}': the seed it was built from was not captured`);
    const probe = probes.get(`${inst.name}|${optionsKey(inst.opts)}`);
    if (!probe) fail(`the catalogue probe did not build '${inst.name}' with ${optionsKey(inst.opts)}`);
    const variants = periodOf(probe.protos);
    const shapeVariant = inst.seed % variants;
    // The same options and seed give the same cached shape: the probe must have met this very one.
    if (probe.protos[shapeVariant] !== inst.proto) fail(`placed prop ${index} '${inst.name}' (seed ${inst.seed}) is not variant ${shapeVariant} of ${variants}`);
    const theta = inst.rotation.y;
    const front = types[inst.name].front.web === '+x' ? K.forwardOfRotationY(theta) : { x: Math.sin(theta), y: 0, z: Math.cos(theta) };
    const options = shapeOptions(inst.opts);
    let role = { kind: 'dressing' };
    if (objectiveOf.has(index)) role = { kind: 'objective', id: objectiveOf.get(index) };
    else if (L.extraction.prop === index) role = { kind: 'extraction' };
    return {
      index,
      name: inst.name,
      variant: typeof inst.opts.variant === 'string' ? inst.opts.variant : null,
      shapeVariant,
      seed: inst.seed,
      seedAuthored: inst.seedGiven,
      options,
      paint: inst.paint === null ? null : K.hexString(inst.paint),
      domeLight: inst.dome,
      zone: inst.zone,
      place: inst.place,
      interior: inst.interior > 0.5,
      dynamic: inst.dynamic,
      placedBy: 'level',
      role,
      collides: inst.opts.collide !== false && inst.colliders.length > 0,
      colliders: inst.colliders,
      lamps: inst.lamps,
      web: { pos: K.webPoint(inst.pos), rotationY: K.round(theta), forward: K.webDir(K.forwardOfRotationY(theta)), front: K.webDir(front), scale: K.webPoint(inst.scale) },
      ue: { pos: K.uePoint(inst.pos), yaw: K.ueYawOfRotationY(theta), frontYaw: K.ueYawOfDir(front), scale: { X: 1, Y: 1, Z: 1 } },
    };
  });

  // -- The explosives stand as props too: placed by their own module, one instanced batch per type
  const template = Object.fromEntries(P.others.map((o) => [o.name, o]));
  L.explosives.forEach((e, n) => {
    const name = e.item.prop;
    const built = template[name];
    if (!built) fail(`the explosives module never built a '${name}'`);
    const probe = probes.get(`${name}|{}`);
    const variants = periodOf(probe.protos);
    const theta = e.yaw;
    const front = { x: Math.sin(theta), y: 0, z: Math.cos(theta) };
    instances.push({
      index: instances.length,
      name,
      variant: null,
      shapeVariant: built.seed % variants,
      seed: built.seed,
      seedAuthored: true,
      options: {},
      paint: built.paint === null ? null : K.hexString(built.paint),
      domeLight: null,
      zone: e.zone,
      place: e.place,
      interior: e.interior > 0.5,
      dynamic: true,
      placedBy: 'explosives',
      role: { kind: 'explosive', explosive: n, type: e.type },
      collides: true,
      colliders: [e.item.collider],
      lamps: [],
      web: { pos: K.webPoint(e.pos), rotationY: K.round(theta), forward: K.webDir(K.forwardOfRotationY(theta)), front: K.webDir(front), scale: { x: 1, y: 1, z: 1 } },
      ue: { pos: K.uePoint(e.pos), yaw: K.ueYawOfRotationY(theta), frontYaw: K.ueYawOfDir(front), scale: { X: 1, Y: 1, Z: 1 } },
    });
  });

  const byName = {};
  for (const inst of instances) byName[inst.name] = (byName[inst.name] || 0) + 1;
  const placedNames = Object.keys(byName).sort();
  const unused = Object.keys(catalog).filter((n) => !byName[n]);

  return {
    meta: {
      ...meta('props.json', run, 'The prop catalogue (what each type is, how big, what it collides with, which variants a seed can pick) and every prop that stands on the block.'),
      frames: {
        prop: 'a prop\'s origin is on the ground at the centre of its footprint; its catalogue length runs along its own +X, its height is up, its width along web +Z (Unreal +Y)',
        yaw: 'ue.yaw assumes the Unreal mesh keeps that frame (mesh +X = the catalogue length axis). catalogue[type].front says which way the model\'s front looks in it; ue.frontYaw is the yaw of that front direction, i.e. the yaw for a mesh authored with its front on +X.',
      },
      counts: { types: Object.keys(types).length, typesPlaced: placedNames.length, instances: instances.length, placedByLevel: P.instances.length, placedByExplosives: L.explosives.length, dynamic: instances.filter((i) => i.dynamic).length },
    },
    catalogue: {
      source: 'G.config.catalog.PROPS (size, surface, flags), the file under src/props that registers the builder (family), and the factory itself: every type was built for seeds 0..' + (run.probeSeeds - 1) + ' (G.props.build) to count the shapes a seed can pick and the paints it draws, and each shape was measured. front follows docs/CONTRACT.md 6.2: vehicles and the hoop face +X, everything else with a front faces web +Z.',
      neverPlaced: unused,
      types,
    },
    instances: {
      source: "placedBy 'level': every G.props.build call the level made (heard by lib/hooks.cjs), with the transform the level gave the result. placedBy 'explosives': G.level.explosives, which the explosives module draws from one built prop per type. role: dressing | objective (a master reel case) | extraction (the IPX truck) | explosive. Build the same prop in the web game with G.props.build(name, {...options, seed}).",
      byName: Object.fromEntries(placedNames.map((n) => [n, byName[n]])),
      list: instances,
    },
  };
}

// ------------------------------------------------------------------------------------------------
// atmos.json
// ------------------------------------------------------------------------------------------------

function buildAtmos(run, raw, node, built) {
  const A = raw.atmos;
  const look = raw.config.config.look;
  const describe = () => null;
  if (A.aimCheck.mismatched.length) fail(`${A.aimCheck.mismatched.length} lamps shine another way in the game than the export says: ${JSON.stringify(A.aimCheck.mismatched.slice(0, 3))}`);
  if (!A.hasAmbient) fail('the hemisphere light of the atmosphere was not found');

  const colourBlock = (c) => ({ hex: K.hexString(c.hex), linear: c.linear.map((v) => K.round(v)) });
  const rigs = {};
  for (const name of ['day', 'night']) {
    const t = A.times[name];
    const cfg = look.times[name];
    if (t.time !== name) fail(`atmos.setTime('${name}') left the rig at '${t.time}'`);
    const toLight = { x: -t.sun.direction.x, y: -t.sun.direction.y, z: -t.sun.direction.z };
    rigs[name] = {
      key: {
        role: name === 'day' ? 'the sun' : 'one steep warm key standing in for the street lights (the moon in the sky is `sky.night.moon`)',
        color: colourBlock(t.sun.color),
        intensity: t.sun.intensity,
        castsShadow: t.sun.castShadow,
        elevation: K.round(Math.asin(-K.unit(t.sun.direction).y) * (180 / Math.PI)),
        web: { direction: K.webDir(t.sun.direction), toLight: K.webDir(toLight) },
        ue: { direction: K.ueDir(t.sun.direction), toLight: K.ueDir(toLight), rotator: K.ueRotatorOfDir(t.sun.direction) },
        shadow: { radius: t.sun.shadowRadius, normalBias: t.sun.shadowNormalBias, biasMetres: cfg.sun.shadowBiasMetres },
      },
      ambient: { type: 'hemisphere', sky: colourBlock(t.ambient.sky), ground: colourBlock(t.ambient.ground), intensity: t.ambient.intensity },
      fog: {
        type: t.fog.type,
        color: K.colourOfLinear(t.fog.color.linear),
        density: t.fog.density,
        rule: 'opacity = 1 - exp(-(density * distance in metres)^2) (three.js FogExp2); past the play bounds the haze thickens (config.json look.fog.endReach / endClear) and is tinted warm toward the west, cool toward the east (look.fog.tintWest / tintEast by night, look.dayFogTint by day)',
        opacityAt: [10, 25, 50, 92, 150, 300].map((d) => ({ web: d, ue: K.ueLength(d), opacity: K.round(1 - Math.exp(-((t.fog.density * d) ** 2))) })),
      },
      grade: t.look,
      exposure: { toneMapping: t.look.toneMapping, exposure: t.look.exposure, multiplier: t.exposure, note: 'final exposure = exposure x multiplier (G.render.exposure), applied before the tone map; inside the shop it is multiplied by `interior.exposure`' },
      bloom: { strength: t.look.bloomStrength, radius: t.look.bloomRadius, threshold: t.look.bloomThreshold, knee: t.look.bloomKnee, note: 'threshold is scene-referred linear radiance before exposure' },
      environment: encodeConfig(cfg.env, ['look', 'times', name, 'env'], describe),
      interior: encodeConfig(cfg.interior, ['look', 'times', name, 'interior'], describe),
      lampGain: cfg.lampGain,
      lampField: cfg.field,
      city: cfg.city,
      train: cfg.train,
      life: cfg.life,
    };
  }

  // -- Lamps
  const lamps = A.lamps.map((l, index) => ({
    index,
    kind: l.kind,
    color: K.colour(l.color),
    intensity: l.intensity,
    range: { web: K.round(l.range), ue: K.ueLength(l.range) },
    priority: l.priority,
    zone: l.zone,
    place: l.place,
    interior: l.interior > 0.5,
    prop: l.prop,
    aimSource: l.aimSource,
    overDeck: l.floor > 0 ? { web: K.round(l.floor), ue: K.ueLength(l.floor) } : null,
    web: { pos: K.webPoint(l.pos), aim: K.webDir(l.aim), wall: l.wall ? K.webDir(l.wall) : null },
    ue: { pos: K.uePoint(l.pos), aim: K.ueDir(l.aim), rotator: K.ueRotatorOfDir(l.aim), wall: l.wall ? K.ueDir(l.wall) : null },
  }));
  const byKind = {};
  for (const l of lamps) byKind[l.kind] = (byKind[l.kind] || 0) + 1;

  // -- Signs that are lit, lit glass, lit facade windows
  const signs = built.signage;
  const litSigns = signs.placements
    .filter((p) => p.kind === 'sign' && signs.paintings[p.painting].lit)
    .map((p) => {
      const s = signs.paintings[p.painting];
      return { placement: p.index, text: s.text, sub: s.sub, style: s.style, fg: s.fg, bg: s.bg, glow: s.glow, zone: p.zone, place: p.place, web: p.web, ue: p.ue };
    });
  const materials = raw.config.config.catalog.MATERIALS;
  const litGlass = built.panes
    .map((p, index) => ({ p, index }))
    .filter(({ p }) => ['glass_lit_warm', 'glass_lit_cool', 'glass_skylight'].includes(p.material))
    .map(({ p, index }) => ({ pane: index, material: p.material, prop: p.prop, zone: p.zone, place: p.place, interior: p.interior > 0.5, ...faceBlocks(p) }));
  const litWindows = [];
  for (const f of built.facades) {
    for (const w of f.windows) {
      if (w.state === 'dark') continue;
      litWindows.push({ face: f.index, grid: f.material, state: w.state, zone: f.zone, place: f.place, web: { pos: K.webPoint(w.pos), normal: K.webDir(f.face.normal) }, ue: { pos: K.uePoint(w.pos), normal: K.ueDir(f.face.normal) } });
    }
  }
  const glassMaterial = (name) => {
    const m = materials[name];
    return { emissive: K.colour(m.emissive), emissiveIntensity: m.emissiveIntensity };
  };

  const moon = look.sky.moon.direction;
  const sunTravel = look.times.day.sun.direction;
  return {
    meta: {
      ...meta('atmos.json', run, 'Light and sky: both lighting rigs as the running game sets them, the sky and haze parameters, every lamp of the block, the lit signs and the windows that glow at night.'),
      colours: '`hex` is sRGB, `linear` is linear RGB (what an FLinearColor takes); radiance triples are scene-referred linear values where 1 is where bloom starts at night',
      intensities: 'three.js r160 light units as the game sets them (the key and the ambient as directional / hemisphere intensities, a lamp as the intensity of the spot light it gets). They were tuned by eye against the exposure of the same rig: use them for the balance between lights, not as photometric values.',
      counts: { lamps: lamps.length, lampsByKind: byKind, litSigns: litSigns.length, litGlass: litGlass.length, litFacadeWindows: litWindows.length },
      default: raw.meta.time,
    },
    rigs: {
      source: 'read from the scene after G.atmos.setTime(name): G.atmos.sun (the one shadow-casting directional light), the hemisphere light, scene.fog, G.render.look (the grade). The remaining fields of each rig are G.config.look.times[name].',
      ...rigs,
    },
    sky: {
      source: 'G.config.look (src/config/look.js): what the two sky domes are painted from. Radiance triples are linear.',
      day: {
        ...encodeConfig(look.daySky, ['look', 'daySky'], describe),
        sunDisc: {
          note: 'the disc stands where the key light comes from',
          web: { toSun: K.webDir({ x: -sunTravel[0], y: -sunTravel[1], z: -sunTravel[2] }) },
          ue: { toSun: K.ueDir({ x: -sunTravel[0], y: -sunTravel[1], z: -sunTravel[2] }) },
        },
        fogTint: look.dayFogTint,
      },
      night: {
        ...encodeConfig(look.sky, ['look', 'sky'], describe),
        moonDisc: {
          note: 'the moon is sky decoration; the night key light does not come from it',
          web: { toMoon: K.webDir({ x: moon[0], y: moon[1], z: moon[2] }) },
          ue: { toMoon: K.ueDir({ x: moon[0], y: moon[1], z: moon[2] }) },
          elevation: K.round(Math.asin(K.unit({ x: moon[0], y: moon[1], z: moon[2] }).y) * (180 / Math.PI)),
        },
        fogTint: { west: look.fog.tintWest, east: look.fog.tintEast },
      },
      clearColor: K.hexString(look.clearColor),
      farCity: encodeConfig(look.city, ['look', 'city'], describe),
    },
    lamps: {
      source: 'G.level.lamps: every light fixture of the block (the lamp hints of placed props included: `prop` is the index into props.json instances). aim: how the lamp shines when it holds one of the real lights, by the rule of src/atmos/lights.js (its own direction; a flood without one at the nearest reel; a sign or lit window out from the wall behind it and 35 degrees down; anything else straight down), checked by the exporter against the game\'s own spot lights. overDeck: the lamp hangs over a floor of the level (a platform, the mezzanine, the shed deck) at that height. By day only `work` lamps and dimmed `neon` lamps are lit (rigs.day.lampGain).',
      kinds: {
        source: 'G.config.look.lamps: how each kind is drawn (ground pool, fixture glow, cone) and how strong its real light is',
        ...encodeConfig(look.lamps, ['look', 'lamps'], describe),
      },
      byKind,
      list: lamps,
    },
    signLights: {
      source: "lamps: the `neon` entries of `lamps.list` (the light a sign throws on the sidewalk). signs: every lit sign quad (level.json signage; style 'neon' flickers, the others are lit boards), with its colours.",
      lamps: lamps.filter((l) => l.kind === 'neon').map((l) => l.index),
      signs: litSigns,
    },
    windowLights: {
      source: "lamps: the `window` entries of `lamps.list` (the light a lit shop throws out). glass: the level's lit panes (level.json glazing: storefronts, the station, transoms, the shop's skylights). facadeWindows: the lit windows of the painted facade grids (level.json facades). All of it glows at night only.",
      lamps: lamps.filter((l) => l.kind === 'window').map((l) => l.index),
      materials: {
        glass_lit_warm: glassMaterial('glass_lit_warm'),
        glass_lit_cool: glassMaterial('glass_lit_cool'),
        glass_skylight: glassMaterial('glass_skylight'),
        facade: {
          source: 'src/mats/facade.js, read from the source text: a warm window takes one of `warm`; a tv window is a blue gradient',
          warm: node.facadeTones.warm,
          curtains: node.facadeTones.curtains,
        },
      },
      glass: litGlass,
      facadeWindows: litWindows,
    },
  };
}

// ------------------------------------------------------------------------------------------------
// Things only the source has
// ------------------------------------------------------------------------------------------------

/** Module-private constants of a source file, read from its text: `const NAME = <number>;`. */
function scrapeConstants(file, names) {
  const text = fs.readFileSync(path.join(SRC, file), 'utf8');
  const out = {};
  for (const name of names) {
    const m = new RegExp(`^const ${name} = (-?[0-9.]+);`, 'm').exec(text);
    if (!m) fail(`src/${file} no longer declares a number called ${name}`);
    out[name] = Number(m[1]);
  }
  return out;
}

/** Which file under src/props registers each catalogue prop (`R.add('name', …)`). */
function scrapePropFamilies() {
  const dir = path.join(SRC, 'props');
  const out = {};
  for (const file of fs.readdirSync(dir).sort()) {
    const text = fs.readFileSync(path.join(dir, file), 'utf8');
    for (const m of text.matchAll(/R\.add\(\s*'([a-z_0-9]+)'/g)) out[m[1]] = file.replace(/\.js$/, '');
  }
  return out;
}

/** A module-private list of colours, read from a source file: `const NAME = [0x…, 0x…];` → ["#…"] (null if gone). */
function scrapeColourList(file, name) {
  const text = fs.readFileSync(path.join(SRC, file), 'utf8');
  const m = new RegExp(`^const ${name} = \\[([^\\]]+)\\];`, 'm').exec(text);
  if (!m) return null;
  const list = m[1].split(',').map((v) => Number(v.trim()));
  return list.every((n) => Number.isInteger(n) && n >= 0 && n <= 0xffffff) ? list.map((n) => K.hexString(n)) : null;
}

/** Plain copy of module data for JSON (functions dropped, Infinity kept as a string). */
function plainData(value) {
  if (typeof value === 'function') return undefined;
  if (typeof value === 'number') return Number.isFinite(value) ? value : String(value);
  if (Array.isArray(value)) return value.map(plainData);
  if (value && typeof value === 'object') {
    const out = {};
    for (const key of Object.keys(value)) {
      const v = plainData(value[key]);
      if (v !== undefined) out[key] = v;
    }
    return out;
  }
  return value;
}

async function readSources() {
  const [layout, plan, matsLayout, copy, explosives] = await Promise.all([
    importSource('level/layout.js'),
    importSource('atmos/plan.js'),
    importSource('mats/layout.js'),
    importSource('ui/copy.js'),
    importSource('explosives.js'),
  ]);
  const config = {};
  for (const name of ['brand', 'catalog', 'enemies', 'flow', 'look', 'player', 'quality', 'text', 'weapons']) config[name] = await importSource(`config/${name}.js`);

  const ex = scrapeConstants('explosives.js', ['POP_FUSE', 'PLAYER_SCALE', 'ENEMY_ROUND', 'SHAKE_REACH', 'ALERT_RADIUS']);
  const distances = [0, 2, 4, 6];
  return {
    config,
    copy,
    layout,
    plan,
    matsLayout,
    physics: scrapeConstants('physics.js', ['STEP_HEIGHT', 'AIR_STEP', 'NAV_CELL', 'NAV_INFLATE', 'NAV_BAND_MIN', 'NAV_BAND_MAX', 'SLICE_THRESHOLD', 'SLICE_MAX', 'SLICE_SHRINK']),
    propFamilies: scrapePropFamilies(),
    facadeTones: { warm: scrapeColourList('mats/facade.js', 'WARM'), curtains: scrapeColourList('mats/facade.js', 'CURTAINS') },
    layoutTables: plainData({ ...layout }),
    explosiveRules: {
      popFuse: ex.POP_FUSE,
      playerDamageScale: ex.PLAYER_SCALE,
      damageFromEnemyRound: ex.ENEMY_ROUND,
      shakeReach: ex.SHAKE_REACH,
      alertRadius: ex.ALERT_RADIUS,
      chainRange: {
        $function: {
          params: paramNames(explosives.chainRange),
          source: explosives.chainRange.toString(),
          samples: Object.values(explosives.KINDS).map((k) => ({ args: [k.size], value: explosives.chainRange(k.size) })),
        },
      },
      chainFuse: {
        $function: {
          params: paramNames(explosives.chainFuse),
          source: explosives.chainFuse.toString(),
          samples: distances.flatMap((d) => [0, 0.5, 1].map((roll) => ({ args: [d, roll], value: explosives.chainFuse(d, roll) }))),
        },
      },
      sizeFromRadius: {
        $function: {
          params: paramNames(explosives.sizeFromRadius),
          source: explosives.sizeFromRadius.toString(),
          samples: [1, 3, 6.5, 7.5, 12].map((r) => ({ args: [r], value: explosives.sizeFromRadius(r) })),
        },
      },
    },
    explosivesModule: explosives,
  };
}

// ------------------------------------------------------------------------------------------------
// Functions and templates
// ------------------------------------------------------------------------------------------------

const NUMBER_FORMATS = [
  [(n) => Math.round(n).toLocaleString('en-US'), 'rounded to a whole number, en-US digit grouping (12,345)'],
  [(n) => n.toLocaleString('en-US'), 'en-US digit grouping'],
  [(n) => String(Math.round(n)), 'rounded to a whole number'],
  [(n) => String(n), 'as written'],
];

/**
 * A text line that takes values, as a template: called once with "{name}" for every parameter, and again
 * with numbers for the parameters that did not come through as text (a line that formats a number).
 * `call(args)` → the line. Returns null when the function is not a plain template.
 */
async function templateOf(call, params) {
  const marks = params.map((p) => `{${p}}`);
  let line = await call(marks);
  if (typeof line !== 'string') return null;
  const formats = {};
  const missing = params.map((p, i) => i).filter((i) => !line.includes(marks[i]));
  if (missing.length) {
    const numbers = missing.map((_, k) => 1234567.4 + k * 1111111);
    const args = marks.slice();
    missing.forEach((i, k) => {
      args[i] = numbers[k];
    });
    line = await call(args);
    if (typeof line !== 'string') return null;
    for (let k = 0; k < missing.length; k++) {
      const i = missing[k];
      const format = NUMBER_FORMATS.find(([write]) => line.includes(write(numbers[k])));
      if (!format) return null;
      line = line.replace(format[0](numbers[k]), marks[i]);
      formats[params[i]] = format[1];
    }
  }
  if (!marks.every((m) => line.includes(m))) return null;
  return { template: line, formats };
}

/** Describes every function of the config: samples from the page, source text from src/config. */
async function describeFunctions(page, raw, node) {
  const cfg = raw.config.config;
  const out = {};
  const callPage = async (keys, calls) => {
    const [answers] = await page.evaluate(C.callConfigFunctions, [{ path: keys, calls }]);
    if (!answers) fail(`G.config.${keys.join('.')} is not a function in the page`);
    for (const a of answers) if (a && a.$error) fail(`G.config.${keys.join('.')} threw: ${a.$error}`);
    return answers;
  };
  for (const keys of functionPaths(cfg)) {
    const id = keys.join('.');
    const fn = at(node.config, keys);
    if (typeof fn !== 'function') fail(`${id} is a function in the page but not in src/config`);
    const params = paramNames(fn);
    const source = fn.toString();
    if (FUNCTION_SAMPLES[id]) {
      const calls = FUNCTION_SAMPLES[id];
      const answers = await callPage(keys, calls);
      // The source text comes from src/config: it must be the function the page runs.
      calls.forEach((args, i) => {
        const here = JSON.parse(JSON.stringify(fn(...args)));
        if (!sameJson(here, answers[i])) fail(`${id}(${JSON.stringify(args)}) is ${JSON.stringify(answers[i])} in the page but ${JSON.stringify(here)} in src/config`);
      });
      out[id] = { $function: { params, source, samples: calls.map((args, i) => ({ args, value: answers[i] })) } };
      continue;
    }
    const t = await templateOf(async (args) => (await callPage(keys, [args]))[0], params);
    if (!t) fail(`${id} is neither sampled (FUNCTION_SAMPLES in export.cjs) nor a plain text template`);
    const example = TEMPLATE_EXAMPLES[id];
    const entry = { template: t.template, params, formats: t.formats, source };
    if (example) {
      const [value] = await callPage(keys, [example]);
      if (fn(...example) !== value) fail(`${id}(${JSON.stringify(example)}) differs between the page and src/config`);
      entry.example = { args: example, value };
    }
    out[id] = { $template: entry };
  }
  return out;
}

/** src/ui/copy.js as data: its two template functions described like the config's. */
async function interfaceCopy(copy) {
  const walk = async (value, keys) => {
    if (typeof value === 'function') {
      const params = paramNames(value);
      const t = await templateOf(async (args) => value(...args), params);
      if (!t) fail(`src/ui/copy.js ${keys.join('.')} is not a plain text template`);
      const entry = { template: t.template, params, formats: t.formats, source: value.toString() };
      const example = TEMPLATE_EXAMPLES[`interface.${keys.join('.')}`];
      if (example) entry.example = { args: example, value: value(...example) };
      return { $template: entry };
    }
    if (Array.isArray(value)) return Promise.all(value.map((v, i) => walk(v, [...keys, String(i)])));
    if (value && typeof value === 'object') {
      const out = {};
      for (const key of Object.keys(value)) out[key] = await walk(value[key], [...keys, key]);
      return out;
    }
    return value;
  };
  return walk({ ...copy }, []);
}

// ------------------------------------------------------------------------------------------------
// Main
// ------------------------------------------------------------------------------------------------

const PROBE_SEEDS = 48; // 48 = 2^4 * 3: any number of shape variants up to 24 shows as a period
const PAINT_SEEDS = 256;
const DT = 0.0333;

async function collect(opts) {
  let file = opts.page;
  if (!file) {
    file = path.join(ROOT, 'dist', 'dev-export.html');
    buildDevPage(ROOT, file);
  }
  if (!fs.existsSync(file)) throw new Error(`${file} does not exist`);
  const node = await readSources();
  node.interfaceCopy = await interfaceCopy(node.copy);

  const game = await openGame(file, { q: opts.quality, noaudio: '1', seed: String(opts.seed) }, { verbose: opts.verbose });
  try {
    const { page } = game;
    await page.evaluate(C.installHelpers);
    const raw = {};
    raw.meta = await page.evaluate(C.collectMeta);
    if (raw.meta.build.stubbed.length) fail(`the page was built with stubs: ${raw.meta.build.stubbed.join(', ')}`);
    if (raw.meta.stubbed.join() !== 'audio') fail(`modules fell back to their stubs: ${raw.meta.stubbed.join(', ')}`);
    if (raw.meta.seed !== opts.seed) fail(`the page runs seed ${raw.meta.seed}, not ${opts.seed}`);
    raw.config = await page.evaluate(C.collectConfig);
    raw.level = await page.evaluate(C.collectLevel);
    raw.props = await page.evaluate(C.collectProps);
    raw.signage = await page.evaluate(C.collectSignage);
    raw.glass = await page.evaluate(C.collectGlass);
    raw.atmos = await page.evaluate(C.collectAtmos);
    const functions = await describeFunctions(page, raw, node);

    // The El train: let the block run until the first two trains have come and gone.
    await page.evaluate(C.startTrainWatch);
    const cfg = raw.config.config.look.train;
    const length = raw.atmos.train.length;
    const passSeconds = (2 * cfg.runUp + (raw.level.bounds.maxX - raw.level.bounds.minX) + length) / cfg.speed;
    const worst = cfg.firstPass + cfg.every[1] + passSeconds + 5;
    let watched = null;
    for (let t = 0; t < worst; t += 10) {
      await game.skip(Math.ceil(10 / DT));
      watched = await page.evaluate(C.readTrainWatch);
      if (watched.events.filter((e) => e.phase === 'ended').length >= 2) break;
    }
    await page.evaluate(C.stopTrainWatch);
    raw.train = watched;

    // Last: build every catalogue prop over and over to learn what a seed varies.
    const names = Object.keys(raw.config.config.catalog.PROPS);
    const requests = names.map((name) => ({ name, opts: {} }));
    const seen = new Set(requests.map((r) => `${r.name}|{}`));
    for (const inst of raw.props.instances) {
      const key = `${inst.name}|${optionsKey(inst.opts)}`;
      if (seen.has(key)) continue;
      seen.add(key);
      requests.push({ name: inst.name, opts: shapeOptions(inst.opts) });
    }
    raw.probe = await page.evaluate(C.probeCatalog, { requests, seeds: PROBE_SEEDS });
    // Types that draw their paint from a palette: more seeds, so that no colour of it is missed.
    const painted = raw.probe.filter((p) => new Set(p.paints).size > 1).map((p) => ({ name: p.name, opts: p.opts }));
    const more = await page.evaluate(C.probeCatalog, { requests: painted, seeds: PAINT_SEEDS });
    for (const m of more) {
      const p = raw.probe.find((q) => q.name === m.name && optionsKey(q.opts) === optionsKey(m.opts));
      p.paints = m.paints;
      p.domes = m.domes;
    }

    const errors = await page.evaluate(() => (window.__errors || []).slice());
    if (errors.length || game.pageErrors.length) fail(`the page reported errors while it was read:\n  ${[...errors, ...game.pageErrors].join('\n  ')}`);
    return { raw, node, functions, bootMs: game.bootMs };
  } finally {
    await game.close();
  }
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log(USAGE);
    return;
  }
  const t0 = Date.now();
  const { raw, node, functions, bootMs } = await collect(opts);
  if (opts.raw) {
    fs.mkdirSync(opts.raw, { recursive: true });
    for (const [name, value] of Object.entries(raw)) fs.writeFileSync(path.join(opts.raw, `${name}.json`), JSON.stringify(value, null, 1));
  }

  const run = { seed: raw.meta.seed, three: raw.meta.three, probeSeeds: PROBE_SEEDS };
  const propNames = raw.props.instances.map((i) => i.name);
  const built = buildLevel(run, raw, node, propNames);
  built.signage = built.level.signage;
  const files = {
    'config.json': buildConfig(run, raw, functions, node),
    'text.json': buildText(run, raw, functions, node, raw.signage),
    'level.json': built.level,
    'props.json': buildProps(run, raw, node),
    'atmos.json': buildAtmos(run, raw, node, built),
  };

  fs.mkdirSync(opts.out, { recursive: true });
  for (const [name, value] of Object.entries(files)) {
    const text = K.stringify(value);
    JSON.parse(text);
    fs.writeFileSync(path.join(opts.out, name), text);
    console.log(`${path.relative(ROOT, path.join(opts.out, name)).padEnd(46)} ${(text.length / 1024).toFixed(0).padStart(5)} kB`);
  }
  const L = files['level.json'].meta.counts;
  const P = files['props.json'].meta.counts;
  console.log(
    `seed ${run.seed}: ${L.colliders} colliders, ${P.instances} props (${P.placedByLevel} level + ${P.placedByExplosives} explosives) of ${P.typesPlaced} types, ` +
      `${L.enemySpawns.ground} ground + ${L.enemySpawns.air} air spawn points, ${L.coverPoints} cover points, ${L.explosives} explosives, ` +
      `${files['atmos.json'].meta.counts.lamps} lamps (the aim of ${raw.atmos.aimCheck.held} checked against the game's own lights). ` +
      `Booted in ${(bootMs / 1000).toFixed(1)} s, done in ${((Date.now() - t0) / 1000).toFixed(1)} s.`,
  );
}

main().catch((err) => {
  console.error(`export.cjs: ${err.message}`);
  process.exitCode = 1;
});
