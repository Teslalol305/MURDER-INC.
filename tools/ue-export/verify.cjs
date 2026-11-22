#!/usr/bin/env node
// Checks the exported data without a browser.
//
//   node tools/ue-export/verify.cjs [--data <dir>] [--reference <dir> | --no-reference] [--verbose]
//
// It re-reads the five JSON files and holds them against
//   - the source of truth: the plain-data modules under src/ (config, level layout and authored points,
//     the settings defaults, the explosive rules, the facade layout), imported here in Node;
//   - docs/DESIGN.md: the landmark coordinates of section 4, the counts it asks for, the difficulty
//     table of section 3.1 and the radio lines of section 2 are read from the document itself;
//   - themselves: every Unreal value against the web value next to it (with its own arithmetic, not
//     lib/convert.cjs), every cross reference, the nav grid against the colliders, every placed prop's
//     colliders and lamps against the catalogue.
// It also checks the reference pictures in docs/unreal/reference (size, count, total weight).
// Exit code 1 on any mismatch.

'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const K = require('./lib/convert.cjs');

const ROOT = path.resolve(__dirname, '..', '..');
const SRC = path.join(ROOT, 'src');
const FILES = ['config.json', 'text.json', 'level.json', 'props.json', 'atmos.json'];
const TOL = 5e-5; // half a unit in the fourth decimal: what rounding may cost

function parseArgs(argv) {
  const opts = { data: path.join(ROOT, 'unreal', 'MurderInc', 'Content', 'Data'), reference: path.join(ROOT, 'docs', 'unreal', 'reference'), verbose: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--data') opts.data = path.resolve(argv[++i]);
    else if (arg === '--reference') opts.reference = path.resolve(argv[++i]);
    else if (arg === '--no-reference') opts.reference = null;
    else if (arg === '--verbose') opts.verbose = true;
    else if (arg === '--help' || arg === '-h') opts.help = true;
    else throw new Error(`unknown argument ${arg}`);
  }
  return opts;
}

// ------------------------------------------------------------------------------------------------
// A tiny check runner: a check collects every mismatch it finds and fails with the first few.
// ------------------------------------------------------------------------------------------------

const results = [];

class Issues {
  constructor() {
    this.list = [];
    this.count = 0;
  }
  add(message) {
    this.list.push(message);
  }
  /** Counts one comparison; records it when it does not hold. */
  ok(cond, message) {
    this.count++;
    if (!cond) this.add(typeof message === 'function' ? message() : message);
    return !!cond;
  }
  near(a, b, tol, what) {
    return this.ok(typeof a === 'number' && typeof b === 'number' && Math.abs(a - b) <= tol, () => `${what}: ${a} is not ${b} (±${tol})`);
  }
  eq(a, b, what) {
    return this.ok(a === b, () => `${what}: ${JSON.stringify(a)} is not ${JSON.stringify(b)}`);
  }
}

function check(name, fn) {
  const issues = new Issues();
  let note = '';
  try {
    note = fn(issues) || '';
  } catch (err) {
    issues.add(`threw: ${err.stack || err.message}`);
  }
  results.push({ name, ok: issues.list.length === 0, count: issues.count, note, issues: issues.list });
}

const importSource = (file) => import(pathToFileURL(path.join(SRC, file)).href);
const isVec = (v) => v && typeof v === 'object' && typeof v.x === 'number' && typeof v.y === 'number' && typeof v.z === 'number';
const isUeVec = (v) => v && typeof v === 'object' && typeof v.X === 'number' && typeof v.Y === 'number' && typeof v.Z === 'number';
const DEG = 180 / Math.PI;
const wrap = (deg) => {
  let d = deg % 360;
  if (d > 180) d -= 360;
  if (d <= -180) d += 360;
  return d;
};
const angleGap = (a, b) => Math.abs(wrap(a - b));
/** Walks every object of a JSON value. */
function walk(value, visit, keys = []) {
  if (!value || typeof value !== 'object') return;
  visit(value, keys);
  if (Array.isArray(value)) value.forEach((v, i) => walk(v, visit, [...keys, i]));
  else for (const k of Object.keys(value)) walk(value[k], visit, [...keys, k]);
}
/** Every number in a text, minus signs and ranges in any typography ("1.9–3.3", "−46"). */
const numbersIn = (text) => (text.replace(/−/g, '-').match(/-?\d+(?:\.\d+)?/g) || []).map(Number);

// ------------------------------------------------------------------------------------------------
// Format
// ------------------------------------------------------------------------------------------------

function checkFormat(data, texts, seed) {
  for (const file of FILES) {
    check(`${file}: canonical form (pretty-printed, 4 decimals, stable)`, (t) => {
      const json = data[file];
      t.eq(json.meta.file, file, 'meta.file');
      t.eq(json.meta.seed, seed, 'meta.seed');
      t.ok(K.stringify(json) === texts[file], 'the file is not what the writer would write from its own content (edited by hand, or numbers with more than 4 decimals)');
      let numbers = 0;
      walk(json, (obj, keys) => {
        const seen = new Map();
        for (const k of Object.keys(obj)) {
          const v = obj[k];
          if (typeof v === 'number') {
            numbers++;
            if (!Number.isFinite(v) || K.round(v) !== v) t.add(`${[...keys, k].join('.')} = ${v} has more than 4 decimals`);
          }
          if (Array.isArray(obj)) continue;
          // Unreal's FJsonObject folds the case of keys: two keys that differ only by case would collide.
          const folded = k.toLowerCase();
          if (seen.has(folded)) t.add(`${keys.join('.')} has keys '${seen.get(folded)}' and '${k}', which Unreal reads as one`);
          seen.set(folded, k);
        }
      });
      t.ok(numbers > 0, 'no numbers');
      return `${numbers} numbers`;
    });
  }
}

// ------------------------------------------------------------------------------------------------
// Tuning against src/config
// ------------------------------------------------------------------------------------------------

/** Holds an exported tree against the source module data it came from. */
function compareTree(t, json, source, where) {
  if (typeof source === 'function') {
    const f = json && (json.$function || json.$template);
    if (!t.ok(!!f, `${where}: a function in the source, ${JSON.stringify(json).slice(0, 60)} in the export`)) return;
    t.eq(f.source, source.toString(), `${where}: source text`);
    if (json.$function) {
      t.ok(f.samples.length > 0, `${where}: no samples`);
      for (const s of f.samples) compareTree(t, s.value, source(...s.args), `${where}(${JSON.stringify(s.args)})`);
    } else {
      if (f.example) t.eq(f.example.value, source(...f.example.args), `${where}: example`);
      // The template itself: filled with its own placeholders it is what the function returns for them,
      // and filled with the example it is the example.
      const marks = f.params.map((p) => `{${p}}`);
      const unformatted = f.params.filter((p) => !(p in f.formats));
      if (unformatted.length === f.params.length) t.eq(f.template, source(...marks), `${where}: template`);
      if (f.example) {
        let line = f.template;
        f.params.forEach((p, i) => {
          const v = f.example.args[i];
          const shown = p in f.formats && /digit grouping/.test(f.formats[p]) ? Math.round(v).toLocaleString('en-US') : String(v);
          line = line.split(`{${p}}`).join(shown);
        });
        t.eq(line, f.example.value, `${where}: template filled with the example`);
      }
    }
    return;
  }
  if (typeof source === 'number') {
    if (!Number.isFinite(source)) return void t.eq(json, String(source), where);
    if (typeof json === 'string' && json.startsWith('#')) return void t.eq(K.hexNumber(json), source, `${where} (colour)`);
    return void t.near(json, source, TOL, where);
  }
  if (source === null || typeof source !== 'object') return void t.eq(json, source, where);
  if (Array.isArray(source)) {
    if (!t.ok(Array.isArray(json) && json.length === source.length, `${where}: an array of ${source.length} in the source`)) return;
    source.forEach((v, i) => compareTree(t, json[i], v, `${where}[${i}]`));
    return;
  }
  if (!t.ok(json && typeof json === 'object' && !Array.isArray(json), `${where}: an object in the source`)) return;
  const want = Object.keys(source).filter((k) => source[k] !== undefined);
  const have = Object.keys(json).filter((k) => k !== 'source');
  t.eq(have.join(','), want.join(','), `${where}: keys`);
  for (const k of want) if (k in json) compareTree(t, json[k], source[k], `${where}.${k}`);
}

function checkConfig(data, src) {
  const config = data['config.json'];
  const names = ['brand', 'catalog', 'enemies', 'flow', 'look', 'player', 'quality', 'weapons'];
  for (const name of names) {
    check(`config.json ${name} = src/config/${name}.js`, (t) => {
      compareTree(t, config[name], { ...src.config[name] }, name);
      return `${t.count} values`;
    });
  }
  check('config.json has every table of src/config (text is in text.json)', (t) => {
    const extra = ['meta', 'settings', 'enemiesResolved', 'explosives'];
    t.eq(Object.keys(config).filter((k) => !extra.includes(k)).sort().join(','), names.join(','), 'tables');
  });
  check('config.json settings.defaults = src/core/settings.js DEFAULTS', (t) => {
    compareTree(t, config.settings.defaults, { ...src.settings.DEFAULTS }, 'settings.defaults');
    t.eq(config.settings.storageKey, src.settings.SETTINGS_KEY, 'storageKey');
  });
  check('config.json enemiesResolved = base tables with each difficulty laid over them', (t) => {
    const E = src.config.enemies;
    for (const name of Object.keys(E.difficulty)) {
      for (const part of ['goon', 'buzzard', 'ai']) {
        const merged = { ...E[part] };
        for (const [k, v] of Object.entries(E.difficulty[name][part] || {})) if (k in E[part]) merged[k] = v;
        compareTree(t, config.enemiesResolved[name][part], merged, `enemiesResolved.${name}.${part}`);
      }
    }
    return `${t.count} values`;
  });
  check('config.json explosives = src/explosives.js', (t) => {
    compareTree(t, config.explosives.kinds, src.explosives.KINDS, 'explosives.kinds');
    const text = fs.readFileSync(path.join(SRC, 'explosives.js'), 'utf8');
    const constant = (name) => Number(new RegExp(`^const ${name} = (-?[0-9.]+);`, 'm').exec(text)[1]);
    const r = config.explosives.rules;
    t.eq(r.popFuse, constant('POP_FUSE'), 'popFuse');
    t.eq(r.playerDamageScale, constant('PLAYER_SCALE'), 'playerDamageScale');
    t.eq(r.damageFromEnemyRound, constant('ENEMY_ROUND'), 'damageFromEnemyRound');
    t.eq(r.shakeReach, constant('SHAKE_REACH'), 'shakeReach');
    t.eq(r.alertRadius, constant('ALERT_RADIUS'), 'alertRadius');
    for (const name of ['chainRange', 'chainFuse', 'sizeFromRadius']) compareTree(t, r[name], src.explosives[name], `explosives.rules.${name}`);
  });
}

// ------------------------------------------------------------------------------------------------
// docs/DESIGN.md
// ------------------------------------------------------------------------------------------------

/** Rows of the markdown tables of a document: [[cell, cell, …], …]. */
function tableRows(text) {
  return text
    .split('\n')
    .filter((line) => line.startsWith('|') && !/^\|\s*-/.test(line))
    .map((line) => line.split('|').slice(1, -1).map((cell) => cell.trim()));
}

function checkDesign(data, design) {
  const config = data['config.json'];
  const text = data['text.json'];
  const rows = tableRows(design);
  const row = (label) => rows.find((r) => r[0] === label);

  check('DESIGN 3.1 difficulty table = config.json (enemies resolved per difficulty, flow.difficulty)', (t) => {
    const order = ['hustler', 'boss', 'kingpin'];
    const lines = {
      'Buzzard HP / bolt dmg / telegraph / cooldown': (e) => [e.buzzard.hp, e.buzzard.boltDamage, e.buzzard.telegraph, ...e.buzzard.cooldown],
      'Buzzard spread far → near (rad)': (e) => [e.buzzard.spreadFar, e.buzzard.spreadNear],
      'Goon HP': (e) => [e.goon.hp],
      'Goon shot dmg / burst length / cooldown': (e) => [e.goon.shotDamage, e.goon.burst, ...e.goon.cooldown],
      'Goon spread far → near (rad)': (e) => [e.goon.spreadFar, e.goon.spreadNear],
      'Goon rush (melee) dmg / run speed': (e) => [e.goon.rushDamage, e.goon.runSpeed],
      'Attack tokens (normal / crowd), gap': (e) => [e.ai.tokens, e.ai.tokensCrowd, e.ai.tokenGap],
      'Exposure gain per s': (e) => [e.ai.exposureUp],
      'Player regen delay / rate': (e, f) => [f.regen.delay, f.regen.rate],
      'Starting patrol (Buzzard + Goon)': (e, f) => [f.patrol.buzzard, f.patrol.goon],
      'Waves after reel 1 / 2 / 3 (Buzzard + Goon)': (e, f) => f.waves.flatMap((w) => [w.buzzard, w.goon]),
      'Alive cap': (e, f) => [f.maxAlive],
      'Pursuit interval / budget': (e, f) => [f.pursuitEvery, f.pursuitBudget],
    };
    for (const [label, pick] of Object.entries(lines)) {
      const r = row(label);
      if (!t.ok(!!r, `DESIGN.md has no table row '${label}'`)) continue;
      order.forEach((name, i) => {
        const want = numbersIn(r[i + 1]);
        const have = pick(config.enemiesResolved[name], config.flow.difficulty[name]);
        t.eq(have.join(' '), want.join(' '), `${label} · ${name}`);
      });
    }
    return `${t.count} cells`;
  });

  check('DESIGN 3.1 rules = config.json (melee, weak point, pools, mixes, holdout, explosives)', (t) => {
    const says = (pattern, what) => {
      const m = pattern.exec(design);
      if (!t.ok(!!m, `DESIGN.md no longer says ${what}`)) return null;
      return m.slice(1).map((v) => Number(v.replace(/−/g, '-')));
    };
    const melee = says(/(\d+(?:\.\d+)?) s strike, hits at (\d+(?:\.\d+)?) s, reach (\d+(?:\.\d+)?) m in a (\d+)° cone,\s+(\d+) damage, (\d+(?:\.\d+)?) s between strikes/, 'the melee numbers');
    if (melee) {
      const m = config.weapons.melee;
      t.eq([m.duration, m.hitAt, m.reach, K.round(m.cone * DEG, 2), m.damage, m.cooldown].join(' '), melee.join(' '), 'melee');
    }
    const head = says(/Head weak point × (\d+(?:\.\d+)?) \(Goon only\)\. Goon pool cap (\d+), Buzzard pool cap (\d+)/, 'the weak point and the pool caps');
    if (head) t.eq([config.weapons.common.headMultiplier, config.enemies.pool.goon, config.enemies.pool.buzzard].join(' '), head.join(' '), 'weak point, pools');
    const mix = says(/Pursuit and holdout mixes: (\d+) % Buzzard/, 'the pursuit mix');
    if (mix) t.near(config.flow.pursuit.buzzardShare * 100, mix[0], 1e-9, 'pursuit buzzard share');
    const wave = says(/total `min\((\d+) \+ (\d+)n, (\d+)\)`, Buzzard share\s+`max\((\d+(?:\.\d+)?), (\d+(?:\.\d+)?) − (\d+(?:\.\d+)?)n\)`/, 'the holdout wave formulas');
    if (wave) {
      const h = config.flow.holdout;
      for (const s of h.total.$function.samples) t.eq(s.value, Math.min(wave[0] + wave[1] * s.args[0], wave[2]), `holdout.total(${s.args[0]})`);
      for (const s of h.buzzardShare.$function.samples) t.near(s.value, Math.max(wave[3], wave[4] - wave[5] * s.args[0]), TOL, `holdout.buzzardShare(${s.args[0]})`);
    }
    const score = says(/Holdout score: Buzzard (\d+), Goon (\d+), × \(1 \+ (\d+(?:\.\d+)?) \(wave − 1\)\); wave clear \+ (\d+) × wave\. Resupply: \+(\d+) Chopper reserve\s+\(cap (\d+)\), \+(\d+) HP/, 'the holdout score and resupply');
    if (score) {
      const h = config.flow.holdout;
      t.eq([h.score.buzzard, h.score.goon, h.resupply.reserve, h.resupply.reserveCap, h.resupply.heal].join(' '), [score[0], score[1], score[4], score[5], score[6]].join(' '), 'score, resupply');
      for (const s of h.score.killScale.$function.samples) t.near(s.value, 1 + score[2] * (s.args[0] - 1), TOL, `killScale(${s.args[0]})`);
      for (const s of h.score.waveClear.$function.samples) t.eq(s.value, score[3] * s.args[0], `waveClear(${s.args[0]})`);
    }
    const tank = says(/\*\*propane tank\*\* \(HP (\d+), fuse (\d+(?:\.\d+)?) s with a jet of flame, radius (\d+(?:\.\d+)?),\s+(\d+) \/ (\d+)\)/, 'the propane tank numbers');
    const rack = says(/\*\*welding rack\*\* \(HP (\d+), fuse (\d+(?:\.\d+)?) s, radius (\d+(?:\.\d+)?), (\d+) \/ (\d+)\)/, 'the welding rack numbers');
    for (const [name, want] of [['propane', tank], ['rack', rack]]) {
      if (!want) continue;
      const k = config.explosives.kinds[name];
      t.eq([k.hp, k.fuse, k.radius, k.damage, k.damage * config.explosives.rules.playerDamageScale].join(' '), want.join(' '), `explosive ${name}`);
    }
    const burst = says(/bursts on impact \(r (\d+), (\d+) dmg, (\d+) max to the player\)/, "the Buzzard's crash");
    if (burst) {
      const b = config.enemies.buzzard;
      t.eq([b.burstRadius, b.burstDamage, b.burstDamage * b.burstPlayerScale].join(' '), burst.join(' '), 'buzzard crash');
    }
    const bodies = says(/non-colliding body \(max (\d+) kept/, 'the body cap');
    if (bodies) t.eq(config.enemies.pool.bodies, bodies[0], 'bodies kept');
    const hold = says(/hold Interact (\d+(?:\.\d+)?) s to grab it/, 'the grab time');
    if (hold) t.eq(config.flow.interact.hold, hold[0], 'interact.hold');
    const rounds = says(/`CHOPPER` — compact automatic carbine, (\d+) rounds[\s\S]*?`NINE` — 9 mm pistol, (\d+) rounds, never runs dry/, 'the magazine sizes');
    if (rounds) {
      t.eq([config.weapons.chopper.magSize, config.weapons.nine.magSize].join(' '), rounds.join(' '), 'magazines');
      t.eq(config.weapons.nine.reserve, 'Infinity', 'the NINE never runs dry');
    }
  });

  check('DESIGN 2 and 8.1 copy = text.json (names, objective lines, radio table, ratings, day and night)', (t) => {
    const T = text.text;
    t.eq(text.brand.title, 'MURDER INC.', 'title');
    t.ok(design.includes(`\`${text.brand.presenter}\``) && design.includes(`\`${text.brand.starLine}\``), 'presenter / star line are not the ones in DESIGN.md');
    // Radio table: | trigger | "line" | hold s |
    const radio = {
      'Intro (first start only)': T.radio.intro,
      'First time an enemy engages': T.radio.contact,
      'Reel 1 of 3 secured': T.radio.reel[0],
      'Reel 2 of 3': T.radio.reel[1],
      'Reel 3 of 3': T.radio.reel[2],
      'Health first drops under 30': T.radio.lowHealth,
      'Truck reached': T.radio.done,
      'Holdout wave N cleared': { text: T.radio.waveClear.text.$template.template.replace('{n}', 'N'), secs: T.radio.waveClear.secs },
    };
    for (const [trigger, line] of Object.entries(radio)) {
      const r = row(trigger);
      if (!t.ok(!!r, `DESIGN.md has no radio row '${trigger}'`)) continue;
      t.eq(line.text, r[1].replace(/^"|"$/g, ''), `radio '${trigger}'`);
      t.eq(line.secs, Number(r[2]), `radio '${trigger}' hold`);
    }
    const ladder = /Rating ladder \(0–5 points\): (.+)\./.exec(design);
    if (t.ok(!!ladder, 'DESIGN.md no longer lists the rating ladder')) t.eq(T.ratings.join(', '), ladder[1].replace(/`/g, ''), 'ratings');
    const objective = /Objective lines: (.+)\./.exec(design);
    if (t.ok(!!objective, 'DESIGN.md no longer lists the objective lines')) t.eq(T.objectives.mission.join(' | '), objective[1].split(' → ').map((s) => s.replace(/"/g, '')).join(' | '), 'objective lines');
    for (const [id, name] of [['hustler', 'Hustler'], ['boss', 'Boss'], ['kingpin', 'Kingpin']]) t.ok(T.difficulties[id] === name && design.includes(`\`${name}\``), `difficulty ${id}`);
    t.ok(design.includes(`\`${T.weapons.chopper.name}\``) && design.includes(`\`${T.weapons.nine.name}\``), 'weapon names');
    // Direction v2 (section 8.1) wins over section 2.
    const eyebrow = /title eyebrow `([^`]+)`/.exec(design);
    if (t.ok(!!eyebrow, 'DESIGN.md 8.1 no longer gives the title eyebrow')) t.eq(T.title.eyebrow, eyebrow[1], 'title eyebrow');
    const card = /location card `([^`]+)` by day and\s+`… · ([^`]+)` by night/.exec(design);
    if (t.ok(!!card, 'DESIGN.md 8.1 no longer gives the location card')) {
      t.eq(T.location.byTime.day, card[1], 'location card by day');
      t.ok(T.location.byTime.night.endsWith(`· ${card[2]}`), 'location card by night');
    }
    const boot = /boot line "([^"]+)"/.exec(design);
    if (t.ok(!!boot, 'DESIGN.md 8.1 no longer gives the boot line')) t.eq(T.boot.wait, boot[1], 'boot line');
    for (const name of T.world.storefronts) t.ok(design.includes(`"${name}"`), `storefront '${name}' is not in DESIGN.md`);
    t.eq(data['atmos.json'].meta.default, 'day', 'daylight is the default look');
  });
}

// ------------------------------------------------------------------------------------------------
// text.json against the source
// ------------------------------------------------------------------------------------------------

function checkText(data, src) {
  const text = data['text.json'];
  check('text.json text = src/config/text.js', (t) => {
    compareTree(t, text.text, { ...src.config.text }, 'text');
    return `${t.count} values`;
  });
  check('text.json brand, input = src/config/brand.js, player.js', (t) => {
    const b = src.config.brand;
    compareTree(t, { ...text.brand }, { title: b.title, titlePlain: b.titlePlain, presenter: b.presenter, starLine: b.starLine, ipx: b.ipx }, 'brand');
    const p = src.config.player;
    compareTree(t, { ...text.input }, { glyphs: p.glyphs, hints: p.hints, touchButtons: p.touchButtons }, 'input');
  });
  check('text.json interface = src/ui/copy.js', (t) => {
    compareTree(t, text.interface, { ...src.copy }, 'interface');
    return `${t.count} values`;
  });
  check('text.json page = src/page.html', (t) => {
    const html = fs.readFileSync(path.join(SRC, 'page.html'), 'utf8');
    const inner = (pattern) => {
      const m = pattern.exec(html);
      return m ? m[1].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() : null;
    };
    t.eq(text.page.title, inner(/<title>([^<]*)<\/title>/), 'title');
    t.eq(text.page.boot.wordmark, inner(/class="boot-mark">([\s\S]*?)<\/div>/), 'boot wordmark');
    t.eq(text.page.boot.star, inner(/class="boot-star">([\s\S]*?)<\/div>/), 'boot star line');
    t.eq(text.page.boot.note, inner(/class="boot-note">([\s\S]*?)<\/p>/), 'boot note');
    t.eq(text.page.boot.presenter.join(' '), inner(/class="boot-kicker">([\s\S]*?)<\/div>/), 'boot presenter');
    t.eq(text.page.canvasLabel, inner(/<canvas[^>]*aria-label="([^"]*)"/), 'canvas label');
  });
  check('text.json lettering = the signs of level.json', (t) => {
    const signage = data['level.json'].signage;
    const signs = signage.paintings.filter((p) => p.kind === 'sign');
    const uses = (list) => list.reduce((n, s) => n + s.uses, 0);
    t.eq(uses(text.lettering.signs), uses(signs), 'sign quads');
    t.eq(uses(text.lettering.graffiti), uses(signage.paintings.filter((p) => p.kind === 'graffiti')), 'graffiti quads');
    t.eq(uses(text.lettering.posters), uses(signage.paintings.filter((p) => p.kind === 'poster')), 'poster quads');
    for (const s of signs) t.ok(text.lettering.signs.some((x) => x.text === s.text && x.sub === s.sub && x.style === s.style), `sign '${s.text}' is missing from the lettering table`);
    // Every storefront of the copy deck hangs somewhere, and so does the shop's name.
    for (const name of [...text.text.world.storefronts, text.text.world.shop]) t.ok(signs.some((s) => s.text === name), `no sign says '${name}'`);
  });
}

// ------------------------------------------------------------------------------------------------
// Web ↔ Unreal, everywhere
// ------------------------------------------------------------------------------------------------

const DIRECTIONS = new Set(['right', 'up', 'normal', 'direction', 'toLight', 'aim', 'wall', 'dir', 'toSun', 'toMoon']);
const POINTS = new Set(['pos', 'min', 'max', 'center', 'corner', 'look', 'stairsFoot', 'deck', 'outside', 'inside', 'from', 'to']);
const LENGTHS = new Set(['radius', 'top', 'halfWidth', 'underside', 'railTop', 'cell', 'inflate', 'bandMin', 'bandMax', 'bayWidth', 'floorHeight', 'windowWidth', 'windowHeight', 'sill', 'ground', 'upper', 'roof', 'parapetTop']);
const RENAMED_LENGTHS = { trackZ: 'trackY', minX: 'minX', maxX: 'maxX', minZ: 'minY', maxZ: 'maxY', x: 'X', z: 'Y' };

/**
 * Checks one {web, ue} pair with arithmetic of its own: ue = web (x, z, y) × 100 for a position, the
 * axes swapped for a direction, a yaw for every facing. Returns the web keys it did not know.
 */
function checkPair(t, web, ue, where) {
  const unknown = [];
  const point = (v, u, what) => {
    if (!t.ok(isUeVec(u), `${what}: no Unreal twin`)) return;
    t.ok(Math.abs(u.X - v.x * 100) < 2e-4 && Math.abs(u.Y - v.z * 100) < 2e-4 && Math.abs(u.Z - v.y * 100) < 2e-4, () => `${what}: web ${JSON.stringify(v)} is not ue ${JSON.stringify(u)}`);
  };
  const direction = (v, u, what) => {
    if (!t.ok(isUeVec(u), `${what}: no Unreal twin`)) return;
    t.ok(Math.abs(u.X - v.x) < 2e-4 && Math.abs(u.Y - v.z) < 2e-4 && Math.abs(u.Z - v.y) < 2e-4, () => `${what}: web ${JSON.stringify(v)} is not ue ${JSON.stringify(u)}`);
    const len = Math.hypot(v.x, v.y, v.z);
    t.ok(Math.abs(len - 1) < 2e-4 || len === 0, `${what}: not a unit vector (${len})`);
  };
  const yawOf = (v) => (Math.hypot(v.x, v.z) < 1e-9 ? 0 : Math.atan2(v.z, v.x) * DEG);
  for (const k of Object.keys(web)) {
    const v = web[k];
    const what = `${where}.${k}`;
    if (v === null) {
      t.ok(ue[k] === null || ue[k] === undefined, `${what}: null in web, set in ue`);
    } else if (isVec(v) && POINTS.has(k)) point(v, ue[k], what);
    else if (isVec(v) && DIRECTIONS.has(k)) direction(v, ue[k], what);
    else if (isVec(v) && k === 'scale') t.ok(isUeVec(ue.scale) && ue.scale.X === v.x && ue.scale.Y === v.z && ue.scale.Z === v.y, `${what}`);
    else if (isVec(v) && k === 'size') {
      // An oriented box: full size in the box's own frame → Unreal half extents.
      t.ok(isUeVec(ue.extent) && Math.abs(ue.extent.X - v.x * 50) < 2e-4 && Math.abs(ue.extent.Y - v.z * 50) < 2e-4 && Math.abs(ue.extent.Z - v.y * 50) < 2e-4, () => `${what}: ${JSON.stringify(v)} is not twice ue.extent ${JSON.stringify(ue.extent)}`);
    } else if (isVec(v) && k === 'facing') {
      t.near(Math.hypot(v.x, v.y, v.z), 1, 2e-4, `${what} length`);
      t.ok(angleGap(ue.yaw, yawOf(v)) < 0.02, () => `${what}: ${JSON.stringify(v)} is not yaw ${ue.yaw}`);
    } else if (isVec(v) && k === 'forward') {
      if ('yaw' in ue) t.ok(angleGap(ue.yaw, yawOf(v)) < 0.02, () => `${what}: ${JSON.stringify(v)} is not yaw ${ue.yaw}`);
      if ('rotationY' in web) t.ok(Math.abs(v.x - Math.cos(web.rotationY)) < 2e-4 && Math.abs(v.z + Math.sin(web.rotationY)) < 2e-4 && v.y === 0, `${what}: not the +X axis of rotationY ${web.rotationY}`);
    } else if (isVec(v) && k === 'front') t.ok(angleGap(ue.frontYaw, yawOf(v)) < 0.02, () => `${what}: ${JSON.stringify(v)} is not frontYaw ${ue.frontYaw}`);
    else if (k === 'rotationY') t.ok(angleGap(ue.yaw, -v * DEG) < 0.01, () => `${what}: ${v} rad is not yaw ${ue.yaw}`);
    else if (k === 'yaw') t.ok(angleGap(ue.yaw, Math.atan2(-Math.cos(v), -Math.sin(v)) * DEG) < 0.01, () => `${what}: heading ${v} rad is not yaw ${ue.yaw}`);
    else if (typeof v === 'number' && LENGTHS.has(k)) t.near(ue[k], v * 100, 2e-4, what);
    else if (typeof v === 'number' && k in RENAMED_LENGTHS) t.near(ue[RENAMED_LENGTHS[k]], v * 100, 2e-4, what);
    else if (typeof v === 'number' && (k === 'width' || k === 'height' || k === 'length')) {
      // A face keeps its names; a catalogue size becomes an Unreal box size (length X, width Y, height Z).
      const twin = k in ue ? ue[k] : ue[{ length: 'X', width: 'Y', height: 'Z' }[k]];
      t.near(twin, v * 100, 2e-4, what);
    } else if (Array.isArray(v) && k === 'tracksZ') t.eq(ue.tracksY.join(), v.map((z) => K.round(z * 100)).join(), what);
    else if (Array.isArray(v) && k === 'x') t.eq(ue.X.join(), v.map((x) => K.round(x * 100)).join(), what);
    else if (k === 'origin' && v && typeof v === 'object') t.ok(Math.abs(ue.origin.X - v.x * 100) < 2e-4 && Math.abs(ue.origin.Y - v.z * 100) < 2e-4, what);
    else unknown.push(k);
  }
  // What only the Unreal block has: derived, so derive it again.
  if (isUeVec(ue.min) && isUeVec(ue.max) && ue.center && ue.extent && !('size' in web)) {
    for (const a of ['X', 'Y', 'Z']) {
      t.near(ue.center[a], (ue.min[a] + ue.max[a]) / 2, 2e-4, `${where}.ue.center.${a}`);
      t.near(ue.extent[a], (ue.max[a] - ue.min[a]) / 2, 2e-4, `${where}.ue.extent.${a}`);
      t.ok(ue.extent[a] >= 0, `${where}: min above max on ${a}`);
    }
  }
  if (ue.rotator) {
    const axes = K.ueAxesOfRotator(ue.rotator);
    const same = (a, b) => Math.abs(a.X - b.X) < 5e-4 && Math.abs(a.Y - b.Y) < 5e-4 && Math.abs(a.Z - b.Z) < 5e-4;
    if (ue.right && ue.up && ue.normal) {
      t.ok(same(axes.x, ue.right) && same(axes.z, ue.up) && same(axes.y, ue.normal), () => `${where}: the rotator ${JSON.stringify(ue.rotator)} does not give right / up / normal`);
      // web normal = right × up (right-handed)
      const r = web.right;
      const u = web.up;
      const n = { x: r.y * u.z - r.z * u.y, y: r.z * u.x - r.x * u.z, z: r.x * u.y - r.y * u.x };
      t.ok(Math.abs(n.x - web.normal.x) < 5e-4 && Math.abs(n.y - web.normal.y) < 5e-4 && Math.abs(n.z - web.normal.z) < 5e-4, `${where}: normal is not right × up`);
      if (web.corner) {
        for (const a of ['x', 'y', 'z']) t.near(web.corner[a], web.pos[a] - (r[a] * web.width) / 2 - (u[a] * web.height) / 2, 2e-4, `${where}.web.corner.${a}`);
      }
    } else {
      const along = ue.direction || ue.aim || (ue.pos && ue.look ? (() => {
        const d = { X: ue.look.X - ue.pos.X, Y: ue.look.Y - ue.pos.Y, Z: ue.look.Z - ue.pos.Z };
        const len = Math.hypot(d.X, d.Y, d.Z);
        return { X: d.X / len, Y: d.Y / len, Z: d.Z / len };
      })() : null);
      if (t.ok(!!along, `${where}: a rotator with nothing to point along`)) t.ok(same(axes.x, along), () => `${where}: the rotator ${JSON.stringify(ue.rotator)} does not point along ${JSON.stringify(along)}`);
    }
  }
  return unknown;
}

function checkConversion(data) {
  check('every Unreal value = the web value next to it (ue = web (x, z, y) × 100, yaw = atan2(z, x))', (t) => {
    let pairs = 0;
    const unknown = new Set();
    for (const file of FILES) {
      walk(data[file], (obj, keys) => {
        if (Array.isArray(obj) || !('web' in obj) || !('ue' in obj)) return;
        const where = `${file}:${keys.join('.')}`;
        pairs++;
        if (typeof obj.web === 'string' && typeof obj.ue === 'string') return void pairs--; // a note on the two spaces, not a value
        if (typeof obj.web === 'number') return void t.near(obj.ue, obj.web * 100, 2e-4, where);
        if (!obj.web || typeof obj.web !== 'object' || !obj.ue || typeof obj.ue !== 'object') return void t.add(`${where}: web / ue are not both objects`);
        for (const k of checkPair(t, obj.web, obj.ue, where)) unknown.add(k);
      });
    }
    t.ok(unknown.size === 0, `web fields this check does not know how to convert: ${[...unknown].join(', ')}`);
    return `${pairs} web / ue pairs, ${t.count} comparisons`;
  });
}

// ------------------------------------------------------------------------------------------------
// level.json
// ------------------------------------------------------------------------------------------------

function checkLandmarks(data, design) {
  const level = data['level.json'];
  const props = data['props.json'];
  check('five landmarks: near the coordinates DESIGN.md 4 gives, and converted right', (t) => {
    const says = (pattern, what) => {
      const m = pattern.exec(design);
      if (!t.ok(!!m, `DESIGN.md no longer gives the position of ${what}`)) return null;
      const n = numbersIn(m[1]);
      return { x: n[0], y: n[1], z: n[2] };
    };
    const truck = props.instances.list[level.extraction.truck.prop];
    const marks = [
      ['the start', says(/\*\*Start\*\*[^\n]*near \(([^)]+)\)/, 'the start'), level.playerStart],
      ['reel 1', says(/\*\*Reel 1\*\* sits mid-avenue near \(([^)]+)\)/, 'reel 1'), level.objectives[0]],
      ['reel 2', says(/\*\*Reel 2\*\* on the shop floor near \(([^)]+)\)/, 'reel 2'), level.objectives[1]],
      ['reel 3', says(/\*\*Reel 3\*\* at centre court near \(([^)]+)\)/, 'reel 3'), level.objectives[2]],
      ['the IPX truck', says(/\*\*IPX truck\*\* waits in the south-east corner near \(([^)]+)\)/, 'the IPX truck'), level.extraction.truck],
    ];
    const lines = [];
    for (const [name, want, got] of marks) {
      if (!want) continue;
      const p = got.web.pos;
      const off = Math.hypot(p.x - want.x, p.z - want.z);
      // "The level agent owns the exact coordinates and may adjust them": a few metres, not a different place.
      t.ok(off <= 4 && Math.abs(p.y - want.y) <= 0.2, `${name} is at (${p.x}, ${p.y}, ${p.z}), ${off.toFixed(1)} m from DESIGN.md's (${want.x}, ${want.y}, ${want.z})`);
      // The conversion, spelled out: X = east = x, Y = south = z, Z = up = y, in centimetres.
      const u = got.ue.pos;
      t.ok(u.X === K.round(p.x * 100) && u.Y === K.round(p.z * 100) && u.Z === K.round(p.y * 100), `${name}: web (${p.x}, ${p.y}, ${p.z}) m is not ue (${u.X}, ${u.Y}, ${u.Z}) cm`);
      lines.push(`${name} (${p.x}, ${p.y}, ${p.z}) m → (${u.X}, ${u.Y}, ${u.Z}) cm`);
    }
    // Facings DESIGN.md states: the start faces east; the truck stands nose east (yaw 0 faces +X).
    t.ok(Math.abs(level.playerStart.ue.yaw) < 15, `the start faces yaw ${level.playerStart.ue.yaw}, not east`);
    t.ok(level.playerStart.web.facing.x > 0.95, 'the start does not face east in web space');
    t.eq(level.extraction.truck.ue.yaw, 0, 'the truck does not stand nose east');
    for (const o of level.objectives) t.near(o.ue.yaw, wrap(-o.web.rotationY * DEG), 0.01, `${o.id} yaw`);
    // The same objects from the props side.
    t.ok(truck && truck.name === 'ipx_truck' && truck.role.kind === 'extraction' && truck.ue.pos.X === level.extraction.truck.ue.pos.X && truck.ue.pos.Y === level.extraction.truck.ue.pos.Y, 'the truck of level.json is not the ipx_truck of props.json');
    for (const o of level.objectives) {
      const c = props.instances.list[o.prop];
      t.ok(c && c.name === 'master_case' && c.role.id === o.id && c.ue.pos.X === o.ue.pos.X && c.ue.pos.Y === o.ue.pos.Y && c.ue.yaw === o.ue.yaw, `${o.id} is not a master_case of props.json`);
    }
    const ex = level.extraction;
    const radius = /\*\*extraction\*\*, radius (\d+(?:\.\d+)?)/.exec(design);
    if (t.ok(!!radius, 'DESIGN.md no longer gives the extraction radius')) t.eq(ex.web.radius, Number(radius[1]), 'extraction radius');
    t.eq(ex.ue.radius, ex.web.radius * 100, 'extraction radius in cm');
    return lines.join('; ');
  });
}

function checkLevel(data, src, design) {
  const level = data['level.json'];
  const config = data['config.json'];
  const { layout, points } = src;
  const boxes = level.colliders.boxes;

  check('counts DESIGN.md 4 asks for (spawn points, cover points, explosives, reels)', (t) => {
    const about = (n, want, what) => t.ok(Math.abs(n - want) <= Math.max(2, want * 0.2), `${what}: ${n}, DESIGN.md says about ${want}`);
    const spawn = /Spawn points: about (\d+) ground \+ (\d+) air/.exec(design);
    const ground = level.enemySpawns.points.filter((s) => s.type === 'ground');
    const air = level.enemySpawns.points.filter((s) => s.type === 'air');
    if (t.ok(!!spawn, 'DESIGN.md no longer says how many spawn points')) {
      about(ground.length, Number(spawn[1]), 'ground spawn points');
      about(air.length, Number(spawn[2]), 'air spawn points');
    }
    t.eq(ground.length + air.length, level.enemySpawns.points.length, 'spawn point types');
    t.eq(level.enemySpawns.points.filter((s) => s.zone === 'west').length, 0, 'spawn points in the west zone (DESIGN: none)');
    const cover = /(\d+)\+ hand-placed cover points/.exec(design);
    if (t.ok(!!cover, 'DESIGN.md no longer says how many cover points')) t.ok(level.coverPoints.points.length >= Number(cover[1]), `cover points: ${level.coverPoints.points.length}, DESIGN.md wants ${cover[1]}+`);
    const explosives = /About (\d+)–(\d+) explosives/.exec(design);
    const items = level.explosives.items;
    if (t.ok(!!explosives, 'DESIGN.md no longer says how many explosives')) t.ok(items.length >= Number(explosives[1]) && items.length <= Number(explosives[2]), `explosives: ${items.length}, DESIGN.md wants ${explosives[1]}–${explosives[2]}`);
    t.ok(items.every((e) => e.type === 'propane' || e.type === 'rack'), 'an explosive is neither a propane tank nor a welding rack');
    t.eq(level.objectives.map((o) => o.code).join(), '1,2,3', 'the three reels');
    t.eq(level.objectives.map((o) => o.zone).join(), 'avenue,shop,lot', 'the reels are on the avenue, in the shop, in the cage');
    t.eq(level.interior.boxes.length, 1, 'interiors (DESIGN: the shop is the only one)');
    const c = level.meta.counts;
    t.eq(c.colliders, boxes.length, 'meta.counts.colliders');
    t.eq(`${c.enemySpawns.ground}+${c.enemySpawns.air}`, `${ground.length}+${air.length}`, 'meta.counts.enemySpawns');
    t.eq(c.coverPoints, level.coverPoints.points.length, 'meta.counts.coverPoints');
    t.eq(c.explosives, items.length, 'meta.counts.explosives');
    return `${ground.length} ground + ${air.length} air spawn points, ${level.coverPoints.points.length} cover points, ${items.length} explosives`;
  });

  check('level.json bounds, zones, ground = src/level/layout.js', (t) => {
    compareTree(t, level.bounds.web, layout.BOUNDS, 'bounds');
    const bounds = /Play bounds: x ([^ ]+) … ([^,]+), z ([^ ]+) … ([^ ]+) /.exec(design);
    if (t.ok(!!bounds, 'DESIGN.md no longer gives the play bounds')) t.eq([level.bounds.web.minX, level.bounds.web.maxX, level.bounds.web.minZ, level.bounds.web.maxZ].join(), numbersIn(bounds.slice(1).join(' ')).join(), 'bounds of DESIGN.md');
    t.eq(level.zones.map((z) => z.id).join(), layout.ZONES.map((z) => z.id).join(), 'zone ids');
    level.zones.forEach((z, i) => {
      compareTree(t, z.web, { minX: layout.ZONES[i].minX, maxX: layout.ZONES[i].maxX, minZ: layout.ZONES[i].minZ, maxZ: layout.ZONES[i].maxZ }, `zone ${z.id}`);
      t.eq(z.name, src.config.text.zones[z.id], `zone ${z.id} name`);
    });
    // The sampled regions against the layout's own functions, at points well inside each rectangle.
    const inside = (r) => [[(r.minX + r.maxX) / 2, (r.minZ + r.maxZ) / 2], [r.minX + 0.03, r.minZ + 0.03], [r.maxX - 0.03, r.maxZ - 0.03]];
    for (const f of level.ground.floors) for (const [x, z] of inside(f.web)) t.eq(f.height.web, layout.floorAt(x, z), `floorAt(${x}, ${z})`);
    for (const s of level.ground.surfaces) for (const [x, z] of inside(s.web)) t.eq(s.surface, layout.groundSurfaceAt(x, z), `groundSurfaceAt(${x}, ${z})`);
    for (const p of level.places.regions) for (const [x, z] of inside(p.web)) t.eq(p.zone, layout.zoneAt(x, z), `zoneAt(${x}, ${z})`);
    // Each list covers the whole block exactly once.
    const area = (list) => list.reduce((a, r) => a + (r.web.maxX - r.web.minX) * (r.web.maxZ - r.web.minZ), 0);
    const whole = (layout.BOUNDS.maxX - layout.BOUNDS.minX) * (layout.BOUNDS.maxZ - layout.BOUNDS.minZ);
    for (const [name, list] of [['floors', level.ground.floors], ['surfaces', level.ground.surfaces], ['places', level.places.regions]]) t.near(area(list), whole, 1e-6, `area covered by ${name}`);
    // The sidewalk slabs are colliders too.
    const slabs = boxes.filter((b) => b.tag === 'sidewalk');
    t.eq(slabs.length, layout.SIDEWALKS.length + layout.PADS.length, 'sidewalk colliders');
    for (const s of [...layout.SIDEWALKS, ...layout.PADS]) t.ok(slabs.some((b) => b.web.min.x === s.x0 && b.web.max.x === s.x1 && b.web.min.z === s.z0 && b.web.max.z === s.z1 && b.web.max.y === layout.KERB), `no collider for the sidewalk slab ${JSON.stringify(s)}`);
    compareTree(t, level.layout, Object.fromEntries(Object.entries({ ...layout }).filter(([, v]) => typeof v !== 'function')), 'layout');
    return `${t.count} comparisons`;
  });

  check('level.json start, reels, truck, spawns, cover, explosives, fly-through = src/level/data.js', (t) => {
    const P = points;
    const floor = (x, z) => layout.floorAt(x, z);
    const at = (p, x, y, z, what) => t.ok(Math.abs(p.x - x) < TOL && Math.abs(p.y - y) < TOL && Math.abs(p.z - z) < TOL, () => `${what}: (${p.x}, ${p.y}, ${p.z}) is not (${x}, ${y}, ${z})`);
    at(level.playerStart.web.pos, P.START.x, floor(P.START.x, P.START.z), P.START.z, 'start');
    t.near(level.playerStart.web.yaw, P.START.yaw, TOL, 'start yaw');
    t.eq(level.objectives.length, P.REELS.length, 'reels');
    P.REELS.forEach((r, i) => {
      const o = level.objectives[i];
      at(o.web.pos, r.x, floor(r.x, r.z), r.z, o.id);
      t.near(o.web.rotationY, r.yaw, TOL, `${o.id} yaw`);
      t.eq(o.zone, r.zone, `${o.id} zone`);
      t.eq(o.label, src.config.text.reels.list[i].label, `${o.id} label`);
    });
    at(level.extraction.truck.web.pos, P.TRUCK.x, floor(P.TRUCK.x, P.TRUCK.z), P.TRUCK.z, 'truck');
    at(level.extraction.web.pos, P.EXTRACTION.x, floor(P.EXTRACTION.x, P.EXTRACTION.z), P.EXTRACTION.z, 'extraction');
    t.eq(level.extraction.web.radius, src.config.flow.extraction.radius, 'extraction radius');
    // Spawn and cover points: the level moves a blocked ground point to the nearest walkable cell, 2.5 m at most.
    const NUDGE = 2.5;
    const spawns = level.enemySpawns.points;
    t.eq(spawns.length, P.GROUND_SPAWNS.length + P.AIR_SPAWNS.length, 'spawn points');
    let moved = 0;
    P.GROUND_SPAWNS.forEach(([x, z], i) => {
      const s = spawns[i];
      const d = Math.hypot(s.web.pos.x - x, s.web.pos.z - z);
      if (d > TOL) moved++;
      t.ok(s.type === 'ground' && d <= NUDGE, `ground spawn ${i} is ${d.toFixed(2)} m from where it was authored`);
      t.eq(s.zone, layout.zoneAt(x, z), `ground spawn ${i} zone`);
    });
    P.AIR_SPAWNS.forEach(([x, y, z], i) => {
      const s = spawns[P.GROUND_SPAWNS.length + i];
      t.eq(s.type, 'air', `air spawn ${i} type`);
      at(s.web.pos, x, y, z, `air spawn ${i}`);
    });
    const cover = level.coverPoints.points;
    t.eq(cover.length, P.COVER_POINTS.length, 'cover points');
    P.COVER_POINTS.forEach(([x, z, y], i) => {
      const d = Math.hypot(cover[i].web.pos.x - x, cover[i].web.pos.z - z);
      if (d > TOL) moved++;
      t.ok(d <= NUDGE, `cover point ${i} is ${d.toFixed(2)} m from where it was authored`);
      if (y !== undefined) t.near(cover[i].web.pos.y, y, TOL, `cover point ${i} height`);
    });
    const items = level.explosives.items;
    t.eq(items.length, P.EXPLOSIVES.length, 'explosives');
    P.EXPLOSIVES.forEach(([type, x, z, yaw, y], i) => {
      t.eq(items[i].type, type, `explosive ${i} type`);
      at(items[i].web.pos, x, y ?? floor(x, z), z, `explosive ${i}`);
      t.near(items[i].web.rotationY, yaw, TOL, `explosive ${i} yaw`);
      t.eq(items[i].hp, config.explosives.kinds[type].hp, `explosive ${i} hp`);
    });
    t.eq(level.cinematicPath.points.length, P.CINEMATIC.length, 'fly-through points');
    P.CINEMATIC.forEach(([x, y, z, lx, ly, lz], i) => {
      at(level.cinematicPath.points[i].web.pos, x, y, z, `fly-through ${i}`);
      at(level.cinematicPath.points[i].web.look, lx, ly, lz, `fly-through ${i} look`);
    });
    // Rules the authored data keeps (src/level/data.js): no explosive within 7 m of the start or 2.2 m of a reel.
    const start = level.playerStart.web.pos;
    for (const e of items) {
      t.ok(Math.hypot(e.web.pos.x - start.x, e.web.pos.z - start.z) >= 7, `explosive ${e.index} is within 7 m of the start`);
      for (const o of level.objectives) t.ok(Math.hypot(e.web.pos.x - o.web.pos.x, e.web.pos.z - o.web.pos.z) >= 2.2, `explosive ${e.index} is within 2.2 m of ${o.id}`);
    }
    return `${moved} points were moved to a walkable cell by the level`;
  });

  check('level.json colliders: sane, referenced both ways, and the nav grid follows from them', (t) => {
    const N = level.nav;
    const P = level.physics;
    const tags = {};
    for (const b of boxes) {
      tags[b.tag] = (tags[b.tag] || 0) + 1;
      t.eq(b.index, boxes.indexOf(b), 'collider index');
      t.ok(b.web.min.x <= b.web.max.x && b.web.min.y <= b.web.max.y && b.web.min.z <= b.web.max.z, `collider ${b.index}: min above max`);
      t.ok(typeof b.tag === 'string' && b.tag.length > 0, `collider ${b.index} has no tag`);
      t.eq(b.blocks.movement, !b.flags.bulletOnly, `collider ${b.index} blocks.movement`);
      t.eq(b.blocks.shots, !b.flags.playerOnly, `collider ${b.index} blocks.shots`);
      const nav = !b.flags.noNav && !b.flags.bulletOnly && !b.flags.playerOnly && b.web.max.y >= N.web.bandMin && b.web.min.y <= N.web.bandMax;
      t.eq(b.blocks.nav, nav, `collider ${b.index} blocks.nav`);
      if (b.orientedBox !== null) t.ok(level.orientedBoxes.boxes[b.orientedBox].colliders.includes(b.index), `collider ${b.index}: its oriented box does not list it`);
    }
    t.eq(JSON.stringify(level.colliders.byTag), JSON.stringify(Object.fromEntries(Object.entries(tags).sort(([a], [b]) => (a < b ? -1 : 1)))), 'byTag');
    for (const o of level.orientedBoxes.boxes) for (const i of o.colliders) t.eq(boxes[i].orientedBox, o.index, `oriented box ${o.index} lists collider ${i}`);
    level.explosives.items.forEach((e) => {
      const b = boxes[e.collider];
      t.ok(b && b.owner.kind === 'explosive' && b.owner.explosive === e.index && b.tag === 'explosive', `explosive ${e.index}: collider ${e.collider} is not its own`);
    });
    // Constants of src/physics.js.
    const text = fs.readFileSync(path.join(SRC, 'physics.js'), 'utf8');
    for (const [name, value] of Object.entries(P)) {
      if (name === 'source') continue;
      const m = new RegExp(`^const ${name} = (-?[0-9.]+);`, 'm').exec(text);
      t.ok(m && Number(m[1]) === value, `physics.${name} = ${value} is not what src/physics.js declares`);
    }
    t.eq([N.web.cell, N.web.inflate, N.web.bandMin, N.web.bandMax].join(), [P.NAV_CELL, P.NAV_INFLATE, P.NAV_BAND_MIN, P.NAV_BAND_MAX].join(), 'nav constants');
    t.eq(config.player.body.stepHeight, P.STEP_HEIGHT, 'step height: config.json player.body vs src/physics.js');
    // The grid.
    const { cols, rows } = N;
    const cells = N.grid.cells;
    t.eq(cols, Math.ceil((level.bounds.web.maxX - level.bounds.web.minX) / N.web.cell), 'nav.cols');
    t.eq(rows, Math.ceil((level.bounds.web.maxZ - level.bounds.web.minZ) / N.web.cell), 'nav.rows');
    t.ok(cells.length === rows && cells.every((r) => r.length === cols && /^[#.]+$/.test(r)), 'nav.grid.cells is not rows × cols of # and .');
    const blocked = cells.join('').split('#').length - 1;
    t.eq(blocked, N.blocked, 'nav.blocked');
    t.eq(cols * rows - blocked, N.free, 'nav.free');
    // Rebuild it from the colliders of this file (src/physics.js rebuild()). The file's numbers are rounded
    // to 4 decimals, so a cell whose centre is within that of a grown box edge may differ: none should.
    const grid = new Uint8Array(cols * rows);
    for (let i = 0; i < cols; i++) grid[i] = grid[cols * rows - cols + i] = 1;
    for (let j = 0; j < rows; j++) grid[j * cols] = grid[j * cols + cols - 1] = 1;
    const ox = N.web.origin.x;
    const oz = N.web.origin.z;
    for (const b of boxes) {
      if (!b.blocks.nav) continue;
      const i0 = Math.max(0, Math.ceil((b.web.min.x - N.web.inflate - ox) / N.web.cell - 0.5 - 1e-9));
      const i1 = Math.min(cols - 1, Math.floor((b.web.max.x + N.web.inflate - ox) / N.web.cell - 0.5 + 1e-9));
      const j0 = Math.max(0, Math.ceil((b.web.min.z - N.web.inflate - oz) / N.web.cell - 0.5 - 1e-9));
      const j1 = Math.min(rows - 1, Math.floor((b.web.max.z + N.web.inflate - oz) / N.web.cell - 0.5 + 1e-9));
      for (let j = j0; j <= j1; j++) grid.fill(1, j * cols + i0, j * cols + i1 + 1);
    }
    let differ = 0;
    for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) if ((cells[j][i] === '#') !== (grid[j * cols + i] === 1)) differ++;
    t.eq(differ, 0, 'cells of the nav grid that do not follow from the colliders');
    // Every ground spawn and ground cover point stands on a free cell.
    const free = (p) => cells[Math.floor((p.z - oz) / N.web.cell)][Math.floor((p.x - ox) / N.web.cell)] === '.';
    for (const s of level.enemySpawns.points) if (s.type === 'ground') t.ok(free(s.web.pos), `ground spawn ${s.index} stands on a blocked nav cell`);
    for (const c of level.coverPoints.points) if (!c.onDeck) t.ok(free(c.web.pos), `cover point ${c.index} stands on a blocked nav cell`);
    return `${boxes.length} colliders, ${cols}×${rows} cells, ${N.free} free`;
  });

  check('level.json El and train = src/level/layout.js, src/config/look.js, src/atmos/plan.js', (t) => {
    const E = layout.EL;
    const d = level.el.deck.web;
    t.eq([d.underside, d.railTop, d.minZ, d.maxZ, d.tracksZ.join('/')].join(), [E.y, E.railTop, -E.half, E.half, E.tracks.join('/')].join(), 'deck');
    const xs = [...E.bents, ...E.far].sort((a, b) => a - b);
    t.eq(level.el.bents.web.x.join(), xs.join(), 'bents');
    t.eq(level.el.columns.length, xs.length * 2, 'columns');
    for (const c of level.el.columns) {
      t.ok(xs.includes(c.web.x) && Math.abs(Math.abs(c.web.z) - E.rowZ) < TOL && c.web.top === E.columnTop, `column ${JSON.stringify(c.web)} is not on a bent of the layout`);
      t.eq(c.insideBounds, E.bents.includes(c.web.x), `column at ${c.web.x} insideBounds`);
      t.eq(boxes[c.collider].tag, 'el-column', `column collider ${c.collider}`);
    }
    t.eq(level.el.girders.filter((g) => g.kind === 'cross').length, xs.length, 'cross girders');
    t.eq(level.el.girders.filter((g) => g.kind === 'longitudinal').length, 2, 'longitudinal girders');
    // DESIGN 4: columns in two rows (z ≈ ±5) every 10 m, the deck's underside at about 6.5 m.
    const el = /columns in two rows \(z ≈ ±(\d+)\) every (\d+) m, cross girders, a track deck with its\s+underside at about (\d+(?:\.\d+)?) m/.exec(design);
    if (t.ok(!!el, 'DESIGN.md no longer describes the El')) {
      t.ok(Math.abs(E.rowZ - Number(el[1])) <= 1, `column rows at ±${E.rowZ}, DESIGN.md says about ±${el[1]}`);
      t.eq(E.spacing, Number(el[2]), 'column spacing');
      t.ok(Math.abs(d.underside - Number(el[3])) <= 0.5, 'deck underside');
    }
    // The train.
    const T = level.train;
    const cfg = src.config.look.train;
    t.eq([T.cars, T.carLength, T.carGap, T.carWidth, T.carHeight, T.speed.web, T.runUp.web].join(), [cfg.cars, cfg.carLength, cfg.carGap, cfg.carWidth, cfg.carHeight, cfg.speed, cfg.runUp].join(), 'train numbers');
    t.near(T.length.web, cfg.cars * cfg.carLength + (cfg.cars - 1) * cfg.carGap, TOL, 'train length');
    for (const track of T.tracks) {
      const tl = src.plan.trainTimeline({ minX: layout.BOUNDS.minX, maxX: layout.BOUNDS.maxX, dir: track.dir, speed: cfg.speed, length: T.length.web, runUp: cfg.runUp });
      t.near(track.seconds.approach, tl.approach, TOL, `train ${track.heading} approach`);
      t.near(track.seconds.over, tl.over, TOL, `train ${track.heading} over`);
      t.near(track.seconds.gone, tl.gone, TOL, `train ${track.heading} gone`);
      t.near(track.web.from.x, tl.start, TOL, `train ${track.heading} start`);
      t.near(track.web.to.x, tl.head(tl.tEnd), 1e-3, `train ${track.heading} end`);
      t.eq(track.web.trackZ, track.dir > 0 ? Math.max(...E.tracks) : Math.min(...E.tracks), `train ${track.heading} track`);
      t.eq(track.web.railTop, E.railTop, `train ${track.heading} rail top`);
    }
    t.eq(JSON.stringify(T.schedule.every), JSON.stringify(cfg.every), 'schedule.every');
    t.eq(T.schedule.firstOverhead, cfg.firstPass, 'schedule.firstOverhead');
    // What the running game did: first train overhead about `firstPass` seconds after boot, then the other way.
    const [first, second] = T.observed;
    t.ok(first.dir === 1 && second.dir === -1, 'the first two trains did not run east, then west');
    t.ok(Math.abs(first.clock.over - cfg.firstPass) < 0.1, `the first train was overhead at ${first.clock.over} s, not ${cfg.firstPass}`);
    t.near(first.clock.gone - first.clock.over, T.tracks[0].seconds.over, 0.05, 'observed time over the block');
    const gap = second.clock.begins - first.clock.begins;
    t.ok(gap >= cfg.every[0] && gap <= cfg.every[1] + 0.05, `the second train began ${gap} s after the first`);
    const every = /A train crosses every (\d+)–(\d+) s/.exec(design);
    if (t.ok(!!every, 'DESIGN.md no longer says how often a train crosses')) t.eq(cfg.every.join(), `${every[1]},${every[2]}`, 'train interval of DESIGN.md');
  });

  check('level.json buildings, interior = src/level/layout.js (and DESIGN.md 4 for the shop)', (t) => {
    const B = layout.BUILDINGS;
    t.eq(level.buildings.list.map((b) => b.id).join(), Object.keys(B).join(), 'buildings');
    for (const b of level.buildings.list) {
      const s = B[b.id];
      t.eq([b.name, b.wall, b.floors, b.web.minX, b.web.maxX, b.web.minZ, b.web.maxZ].join(), [s.name, s.base, s.floors, s.x0, s.x1, s.z0, s.z1].join(), `building ${b.id}`);
      t.near(b.web.roof, layout.buildingHeight(s), TOL, `building ${b.id} roof`);
      t.ok(b.web.parapetTop > b.web.roof, `building ${b.id}: parapet under the roof`);
      for (const i of b.colliders) {
        const c = boxes[i];
        t.ok(c.tag === b.name && c.web.min.x >= s.x0 - TOL && c.web.max.x <= s.x1 + TOL && c.web.min.z >= s.z0 - TOL && c.web.max.z <= s.z1 + TOL, `collider ${i} of ${b.id} is outside its footprint`);
      }
    }
    const S = layout.SHOP;
    const box = level.interior.boxes[0].web;
    t.eq([box.min.x, box.max.x, box.min.z, box.max.z, box.min.y].join(), [S.minX, S.maxX, S.minZ, S.maxZ, 0].join(), 'interior box = the shop');
    t.near(box.max.y, S.eave + S.roof, TOL, 'interior box top');
    const shop = /about x ([^…]+)…(\S+),\s+z ([^…]+)…([^,]+), eave (\d+) m/.exec(design);
    if (t.ok(!!shop, 'DESIGN.md no longer gives the shop footprint')) {
      const want = numbersIn(shop.slice(1, 5).join(' '));
      t.ok(Math.abs(box.min.x - want[0]) <= 2 && Math.abs(box.max.x - want[1]) <= 2 && Math.abs(box.min.z - want[2]) <= 2 && Math.abs(box.max.z - want[3]) <= 2, `the shop is at ${JSON.stringify(box)}, DESIGN.md says about x ${want[0]}…${want[1]}, z ${want[2]}…${want[3]}`);
      t.eq(S.eave, Number(shop[5]), 'shop eave');
    }
    t.eq(level.interior.doorways.length >= 2, true, 'doorways the Buzzards use (the roll door and the bay)');
  });

  check('level.json signage, glazing, facades: complete and consistent', (t) => {
    const S = level.signage;
    const uses = new Array(S.paintings.length).fill(0);
    for (const p of S.placements) {
      uses[p.painting]++;
      t.eq(p.kind, S.paintings[p.painting].kind, `placement ${p.index} kind`);
      // A sign hangs at the size it was painted for (the level stretches only decals, posters and graffiti).
      if (p.kind === 'sign') {
        t.near(p.web.width, S.paintings[p.painting].web.width, 2e-3, `placement ${p.index} width`);
        t.near(p.web.height, S.paintings[p.painting].web.height, 2e-3, `placement ${p.index} height`);
      }
      t.ok(p.web.width > 0 && p.web.height > 0, `placement ${p.index} has no size`);
    }
    S.paintings.forEach((p, i) => t.eq(uses[i], p.uses, `painting ${i} uses`));
    t.eq(S.placements.length, level.meta.counts.signagePlacements, 'placements count');
    // Facade windows: lay the painter's own grid over every face again.
    for (const f of level.facades.faces) {
      const g = level.facades.grids[f.grid];
      const spec = src.matsLayout.facadeSpec({ base: g.base, floors: g.floors, bays: g.bays, bayW: g.web.bayWidth, floorH: g.web.floorHeight, lit: g.litFraction, seed: g.seed, shopfront: false });
      const layoutOf = src.matsLayout.facadeLayout(spec);
      let n = 0;
      let lit = 0;
      for (let k = Math.floor(f.gridOrigin.u / spec.w) - 1; k <= Math.ceil((f.gridOrigin.u + f.web.width) / spec.w) + 1; k++) {
        for (const w of layoutOf.windows) {
          const u = w.x + k * spec.w - f.gridOrigin.u;
          const v = w.y - f.gridOrigin.v;
          if (u < -1e-4 || u + w.w > f.web.width + 1e-4 || v < -1e-4 || v + w.h > f.web.height + 1e-4) continue;
          n++;
          if (w.state !== 'dark') lit++;
          const pos = { x: f.web.corner.x + f.web.right.x * (u + w.w / 2) + f.web.up.x * (v + w.h / 2), y: f.web.corner.y + f.web.up.y * (v + w.h / 2), z: f.web.corner.z + f.web.right.z * (u + w.w / 2) + f.web.up.z * (v + w.h / 2) };
          t.ok(f.windows.some((x) => x.state === w.state && Math.abs(x.web.pos.x - pos.x) < 2e-3 && Math.abs(x.web.pos.y - pos.y) < 2e-3 && Math.abs(x.web.pos.z - pos.z) < 2e-3), `face ${f.index}: no ${w.state} window at (${pos.x.toFixed(2)}, ${pos.y.toFixed(2)}, ${pos.z.toFixed(2)})`);
        }
      }
      t.eq(f.windows.length, n, `face ${f.index} windows`);
      t.eq(f.windows.filter((w) => w.state !== 'dark').length, lit, `face ${f.index} lit windows`);
      t.ok(Math.abs(f.web.normal.y) < 1e-6 && f.web.up.y === 1, `face ${f.index} is not an upright wall`);
    }
    const list = data['props.json'].instances.list;
    for (const p of level.glazing.panes) {
      t.ok(/^glass_/.test(p.material) && src.config.catalog.MATERIALS[p.material], `pane ${p.index}: unknown material ${p.material}`);
      // A pane of a prop lies within that prop's reach (its catalogue box, overhangs allowed for).
      if (p.prop !== null) {
        const inst = list[p.prop];
        const size = inst && data['props.json'].catalogue.types[inst.name].size.web;
        t.ok(inst && Math.hypot(p.web.pos.x - inst.web.pos.x, p.web.pos.z - inst.web.pos.z) <= Math.hypot(size.length, size.width) / 2 + 1.5, `pane ${p.index} is not near prop ${p.prop}`);
      }
    }

    return `${S.placements.length} placements of ${S.paintings.length} paintings, ${level.facades.faces.reduce((n, f) => n + f.windows.length, 0)} facade windows, ${level.glazing.panes.length} panes`;
  });
}

// ------------------------------------------------------------------------------------------------
// props.json
// ------------------------------------------------------------------------------------------------

function checkProps(data, src, design) {
  const props = data['props.json'];
  const level = data['level.json'];
  const atmos = data['atmos.json'];
  const types = props.catalogue.types;
  const list = props.instances.list;
  const boxes = level.colliders.boxes;

  check('props.json catalogue = src/config/catalog.js PROPS and the files under src/props', (t) => {
    const P = src.config.catalog.PROPS;
    t.eq(Object.keys(types).join(), Object.keys(P).join(), 'types');
    for (const [name, def] of Object.entries(P)) {
      const c = types[name];
      if (!c) continue;
      t.eq([c.size.web.length, c.size.web.height, c.size.web.width].join(), def.size.join(), `${name} size`);
      t.eq(c.surface, def.surface, `${name} surface`);
      t.eq(c.noCollide, !!def.noCollide, `${name} noCollide`);
      if (def.dynamic) t.ok(c.dynamic, `${name} is dynamic in the catalogue`);
      if (def.noCollide) t.ok(c.variants.every((v) => v.colliders.length === 0), `${name} must not collide`);
      const file = path.join(SRC, 'props', `${c.family}.js`);
      t.ok(fs.existsSync(file) && new RegExp(`R\\.add\\(\\s*'${name}'`).test(fs.readFileSync(file, 'utf8')), `${name}: src/props/${c.family}.js does not register it`);
      t.ok(c.variants.length >= 1, `${name} has no variant`);
      for (const v of c.variants) {
        // "Colliders never leave the box" (docs/CONTRACT.md 6.2).
        for (const k of v.colliders) {
          t.ok(k.web.min.x >= -def.size[0] / 2 - 1e-3 && k.web.max.x <= def.size[0] / 2 + 1e-3 && k.web.min.y >= -1e-3 && k.web.max.y <= def.size[1] + 1e-3 && k.web.min.z >= -def.size[2] / 2 - 1e-3 && k.web.max.z <= def.size[2] / 2 + 1e-3, `${name} variant ${v.variant}: a collider leaves the catalogue box`);
        }
      }
      t.eq(c.front.web, c.family === 'vehicles' || name === 'hoop' ? '+x' : '+z', `${name} front`);
    }
    // Cover heights DESIGN.md 4 lists.
    const cover = /sedan roofs (\d+(?:\.\d+)?), jersey barriers (\d+(?:\.\d+)?), trash-bag piles (\d+(?:\.\d+)?), milk-crate stacks (\d+(?:\.\d+)?),\s+traffic barrels (\d+(?:\.\d+)?), newspaper boxes (\d+(?:\.\d+)?), mailboxes (\d+(?:\.\d+)?), dumpsters (\d+(?:\.\d+)?)/.exec(design);
    if (t.ok(!!cover, 'DESIGN.md no longer lists the cover heights')) {
      const names = ['sedan', 'jersey_barrier', 'trash_bags', 'milk_crates', 'traffic_barrel', 'newspaper_box', 'mailbox', 'dumpster'];
      t.eq(names.map((n) => types[n].size.web.height).join(), cover.slice(1).map(Number).join(), 'cover heights');
    }
    return `${Object.keys(types).length} types`;
  });

  check('props.json instances: roles, references, and their colliders and lamps follow from the catalogue', (t) => {
    const c = props.meta.counts;
    t.eq(list.length, c.instances, 'instances');
    t.eq(list.filter((i) => i.placedBy === 'level').length, c.placedByLevel, 'placed by the level');
    t.eq(list.filter((i) => i.placedBy === 'explosives').length, level.explosives.items.length, 'placed by the explosives module');
    t.eq(list.filter((i) => i.role.kind === 'objective').length, 3, 'objective cases');
    t.eq(list.filter((i) => i.role.kind === 'extraction').length, 1, 'extraction truck');
    const tally = {};
    let matched = 0;
    let lamps = 0;
    for (const inst of list) {
      tally[inst.name] = (tally[inst.name] || 0) + 1;
      t.eq(inst.index, list.indexOf(inst), 'instance index');
      const type = types[inst.name];
      if (!t.ok(!!type, `instance ${inst.index}: '${inst.name}' is not in the catalogue`)) continue;
      t.ok(Number.isInteger(inst.seed) && inst.seed >= 0, `instance ${inst.index}: seed`);
      const set = Object.keys(inst.options).length ? type.options.find((o) => JSON.stringify(o.options) === JSON.stringify(inst.options)) : type;
      if (!t.ok(!!set, `instance ${inst.index} ${inst.name}: no catalogue entry for options ${JSON.stringify(inst.options)}`)) continue;
      t.eq(inst.shapeVariant, inst.seed % set.variants.length, `instance ${inst.index} ${inst.name}: shape variant`);
      const variant = set.variants[inst.shapeVariant];
      if (inst.role.kind === 'explosive') {
        const e = level.explosives.items[inst.role.explosive];
        t.ok(e && e.prop === inst.name && e.ue.pos.X === inst.ue.pos.X && e.ue.pos.Y === inst.ue.pos.Y && e.ue.pos.Z === inst.ue.pos.Z && e.ue.yaw === inst.ue.yaw, `instance ${inst.index}: not explosive ${inst.role.explosive} of level.json`);
        continue;
      }
      // Colliders: what src/level/kit.js place() registers for this prop, from the catalogue's local boxes.
      const theta = inst.web.rotationY;
      const sin = Math.sin(theta);
      const cos = Math.cos(theta);
      const { x, y, z } = inst.web.pos;
      const oriented = [...new Set(inst.colliders.map((i) => boxes[i].orientedBox))].map((i) => level.orientedBoxes.boxes[i]);
      for (const i of inst.colliders) t.ok(boxes[i].owner.kind === 'prop' && boxes[i].owner.prop === inst.index && boxes[i].tag === inst.name, `instance ${inst.index}: collider ${i} does not point back`);
      const expected = !inst.collides
        ? []
        : variant.colliders.filter((k) => !(k.web.max.y - k.web.min.y < 0.2 && k.web.max.y < 0.3));
      if (inst.collides) t.eq(oriented.length, expected.length, `instance ${inst.index} ${inst.name}: collider count`);
      for (const k of expected) {
        const lx = (k.web.min.x + k.web.max.x) / 2;
        const lz = (k.web.min.z + k.web.max.z) / 2;
        const centre = { x: x + lx * cos + lz * sin, y: y + (k.web.min.y + k.web.max.y) / 2, z: z - lx * sin + lz * cos };
        const size = { x: k.web.max.x - k.web.min.x, y: k.web.max.y - k.web.min.y, z: k.web.max.z - k.web.min.z };
        const hit = oriented.find((o) => Math.abs(o.web.center.x - centre.x) < 2e-3 && Math.abs(o.web.center.y - centre.y) < 2e-3 && Math.abs(o.web.center.z - centre.z) < 2e-3 && Math.abs(o.web.size.x - size.x) < 2e-3 && Math.abs(o.web.size.y - size.y) < 2e-3 && Math.abs(o.web.size.z - size.z) < 2e-3);
        if (t.ok(!!hit, `instance ${inst.index} ${inst.name}: the level has no collider where the catalogue box ${JSON.stringify(k.web)} lands`)) {
          matched++;
          t.near(hit.web.rotationY, theta, 2e-4, `instance ${inst.index}: oriented box yaw`);
        }
      }
      // Lamps: the prop's own lamp hints, placed.
      t.eq(inst.lamps.length, variant.lights.length, `instance ${inst.index} ${inst.name}: lamps`);
      for (const hint of variant.lights) {
        const p = { x: x + hint.web.pos.x * cos + hint.web.pos.z * sin, y: y + hint.web.pos.y, z: z - hint.web.pos.x * sin + hint.web.pos.z * cos };
        const lamp = inst.lamps.map((i) => atmos.lamps.list[i]).find((l) => l && Math.abs(l.web.pos.x - p.x) < 2e-3 && Math.abs(l.web.pos.y - p.y) < 2e-3 && Math.abs(l.web.pos.z - p.z) < 2e-3);
        if (t.ok(!!lamp, `instance ${inst.index} ${inst.name}: no lamp where its ${hint.kind} light lands`)) {
          lamps++;
          t.eq(lamp.prop, inst.index, `lamp ${lamp.index} prop`);
          t.eq(lamp.kind, hint.kind, `lamp ${lamp.index} kind`);
          t.eq(lamp.color.hex, hint.color.hex, `lamp ${lamp.index} colour`);
        }
      }
    }
    t.eq(JSON.stringify(props.instances.byName), JSON.stringify(Object.fromEntries(Object.keys(tally).sort().map((n) => [n, tally[n]]))), 'byName');
    t.eq(Object.keys(types).filter((n) => !tally[n]).join(), props.catalogue.neverPlaced.join(), 'neverPlaced');
    for (const b of boxes) if (b.owner.kind === 'prop') t.ok(list[b.owner.prop] && list[b.owner.prop].colliders.includes(b.index) && list[b.owner.prop].name === b.owner.name, `collider ${b.index}: prop ${b.owner.prop} does not list it`);
    return `${list.length} instances, ${matched} catalogue colliders and ${lamps} lamps found where they must be`;
  });
}

// ------------------------------------------------------------------------------------------------
// atmos.json
// ------------------------------------------------------------------------------------------------

function checkAtmos(data, src) {
  const atmos = data['atmos.json'];
  const level = data['level.json'];
  const look = src.config.look;

  check('atmos.json rigs = src/config/look.js times (what atmos.setTime applies)', (t) => {
    for (const name of ['day', 'night']) {
      const rig = atmos.rigs[name];
      const cfg = look.times[name];
      t.eq(K.hexNumber(rig.key.color.hex), cfg.sun.color, `${name} key colour`);
      t.eq(rig.key.intensity, cfg.sun.intensity, `${name} key intensity`);
      const len = Math.hypot(...cfg.sun.direction);
      const d = rig.key.web.direction;
      t.ok(Math.abs(d.x - cfg.sun.direction[0] / len) < 2e-4 && Math.abs(d.y - cfg.sun.direction[1] / len) < 2e-4 && Math.abs(d.z - cfg.sun.direction[2] / len) < 2e-4, `${name} key direction`);
      t.near(rig.key.elevation, Math.asin(-cfg.sun.direction[1] / len) * DEG, 1e-3, `${name} key elevation`);
      // A directional light in Unreal: pitch down by the elevation, yaw to where the light travels.
      t.near(rig.key.ue.rotator.Pitch, -rig.key.elevation, 1e-3, `${name} key pitch`);
      t.ok(angleGap(rig.key.ue.rotator.Yaw, Math.atan2(cfg.sun.direction[2], cfg.sun.direction[0]) * DEG) < 0.01, `${name} key yaw`);
      t.eq([rig.key.shadow.radius, rig.key.shadow.normalBias, rig.key.shadow.biasMetres].join(), [cfg.sun.shadowRadius, cfg.sun.shadowNormalBias, cfg.sun.shadowBiasMetres].join(), `${name} shadow`);
      t.eq([K.hexNumber(rig.ambient.sky.hex), K.hexNumber(rig.ambient.ground.hex), rig.ambient.intensity].join(), [cfg.ambient.sky, cfg.ambient.ground, cfg.ambient.intensity].join(), `${name} ambient`);
      t.eq(rig.fog.color.linear.join(), cfg.fog.haze.join(), `${name} haze`);
      t.eq(rig.fog.density, cfg.fog.density, `${name} fog density`);
      for (const [k, v] of Object.entries(cfg.grade)) t.eq(rig.grade[k], v, `${name} grade.${k}`);
      t.eq([rig.exposure.exposure, rig.exposure.multiplier, rig.bloom.strength, rig.bloom.radius, rig.bloom.threshold, rig.bloom.knee].join(), [cfg.grade.exposure, 1, cfg.grade.bloomStrength, cfg.grade.bloomRadius, cfg.grade.bloomThreshold, cfg.grade.bloomKnee].join(), `${name} exposure and bloom`);
      t.eq(rig.exposure.toneMapping, look.grade.toneMapping, `${name} tone mapping`);
      compareTree(t, rig.environment, cfg.env, `${name}.environment`);
      compareTree(t, rig.interior, cfg.interior, `${name}.interior`);
      compareTree(t, rig.lampGain, cfg.lampGain, `${name}.lampGain`);
      compareTree(t, rig.lampField, cfg.field, `${name}.lampField`);
      compareTree(t, rig.city, cfg.city, `${name}.city`);
      compareTree(t, rig.train, cfg.train, `${name}.train`);
      compareTree(t, rig.life, cfg.life, `${name}.life`);
      // Colours: hex and linear say the same thing.
      for (const c of [rig.key.color, rig.ambient.sky, rig.ambient.ground]) {
        const n = K.hexNumber(c.hex);
        const lin = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => K.srgbToLinear(v / 255));
        t.ok(lin.every((v, i) => Math.abs(v - c.linear[i]) < 1e-4), `${name}: ${c.hex} is not linear ${c.linear}`);
      }
    }
    // By day the sun stands high in the west-south-west and its light travels east and a little north.
    const day = atmos.rigs.day.key;
    t.ok(day.elevation > 40 && day.web.direction.x > 0 && day.web.direction.z < 0, 'the day sun does not travel east and north from high up');
    t.ok(atmos.rigs.day.key.intensity > atmos.rigs.night.key.intensity && atmos.rigs.day.fog.density < atmos.rigs.night.fog.density, 'day is not brighter and clearer than night');
    return `${t.count} values`;
  });

  check('atmos.json sky, lamp kinds = src/config/look.js', (t) => {
    const strip = (o, drop) => Object.fromEntries(Object.entries(o).filter(([k]) => !drop.includes(k)));
    compareTree(t, strip(atmos.sky.day, ['sunDisc', 'fogTint']), look.daySky, 'sky.day');
    compareTree(t, strip(atmos.sky.night, ['moonDisc', 'fogTint']), look.sky, 'sky.night');
    compareTree(t, atmos.sky.day.fogTint, look.dayFogTint, 'sky.day.fogTint');
    compareTree(t, atmos.sky.night.fogTint, { west: look.fog.tintWest, east: look.fog.tintEast }, 'sky.night.fogTint');
    compareTree(t, atmos.sky.farCity, look.city, 'sky.farCity');
    t.eq(K.hexNumber(atmos.sky.clearColor), look.clearColor, 'clear colour');
    const sun = atmos.rigs.day.key.web.toLight;
    const disc = atmos.sky.day.sunDisc.web.toSun;
    t.ok(Math.abs(sun.x - disc.x) < 2e-4 && Math.abs(sun.y - disc.y) < 2e-4 && Math.abs(sun.z - disc.z) < 2e-4, 'the sun disc is not where the key light comes from');
    compareTree(t, atmos.lamps.kinds, look.lamps, 'lamps.kinds');
    return `${t.count} values`;
  });

  check('atmos.json lamps, lit signs, lit windows: complete and consistent with level.json', (t) => {
    const lamps = atmos.lamps.list;
    const kinds = Object.keys(look.lamps.kinds);
    const byKind = {};
    for (const l of lamps) {
      byKind[l.kind] = (byKind[l.kind] || 0) + 1;
      t.eq(l.index, lamps.indexOf(l), 'lamp index');
      t.ok(kinds.includes(l.kind), `lamp ${l.index}: unknown kind ${l.kind}`);
      t.ok(l.intensity > 0 && l.range.web > 0, `lamp ${l.index}: no light`);
      const b = level.bounds.web;
      t.ok(l.web.pos.x >= b.minX - 1 && l.web.pos.x <= b.maxX + 1 && l.web.pos.z >= b.minZ - 1 && l.web.pos.z <= b.maxZ + 1 && l.web.pos.y > 0, `lamp ${l.index} is not on the block`);
      // The aim rule of src/atmos/lights.js.
      if (l.aimSource === 'wall') {
        const w = l.web.wall;
        const len = Math.hypot(1, 0.7);
        t.ok(w && Math.abs(l.web.aim.x - w.x / len) < 2e-4 && Math.abs(l.web.aim.y + 0.7 / len) < 2e-4 && Math.abs(l.web.aim.z - w.z / len) < 2e-4, `lamp ${l.index}: not aimed out from its wall and down`);
        t.ok(l.kind === 'neon' || l.kind === 'window', `lamp ${l.index}: only signs and windows aim from a wall`);
      } else if (l.aimSource === 'down') t.eq([l.web.aim.x, l.web.aim.y, l.web.aim.z].join(), '0,-1,0', `lamp ${l.index} aim`);
    }
    t.eq(JSON.stringify(atmos.lamps.byKind), JSON.stringify(byKind), 'byKind');
    t.eq(lamps.length, atmos.meta.counts.lamps, 'lamp count');
    t.eq(atmos.signLights.lamps.join(), lamps.filter((l) => l.kind === 'neon').map((l) => l.index).join(), 'sign lamps');
    t.eq(atmos.windowLights.lamps.join(), lamps.filter((l) => l.kind === 'window').map((l) => l.index).join(), 'window lamps');
    // DESIGN 4: the shop has four real work lights; the court two flood lights.
    t.eq(lamps.filter((l) => l.kind === 'work' && l.priority === 10).length, 4, "the shop's four work lights");
    t.eq(lamps.filter((l) => l.kind === 'flood' && l.place === 'THE CAGE').length, 2, "the court's two flood lights");
    // Lit signs are the lit sign placements of level.json; lit glass its lit panes; facade windows its lit windows.
    const S = level.signage;
    const lit = S.placements.filter((p) => p.kind === 'sign' && S.paintings[p.painting].lit);
    t.eq(atmos.signLights.signs.map((s) => s.placement).join(), lit.map((p) => p.index).join(), 'lit signs');
    for (const s of atmos.signLights.signs) t.eq(JSON.stringify(s.ue), JSON.stringify(S.placements[s.placement].ue), `lit sign ${s.placement}`);
    const panes = level.glazing.panes.filter((p) => ['glass_lit_warm', 'glass_lit_cool', 'glass_skylight'].includes(p.material));
    t.eq(atmos.windowLights.glass.map((g) => g.pane).join(), panes.map((p) => p.index).join(), 'lit glass');
    const windows = level.facades.faces.flatMap((f) => f.windows.filter((w) => w.state !== 'dark').map((w) => `${f.index}:${w.state}:${w.ue.pos.X},${w.ue.pos.Y},${w.ue.pos.Z}`));
    t.eq(atmos.windowLights.facadeWindows.map((w) => `${w.face}:${w.state}:${w.ue.pos.X},${w.ue.pos.Y},${w.ue.pos.Z}`).join('|'), windows.join('|'), 'lit facade windows');
    for (const name of ['glass_lit_warm', 'glass_lit_cool', 'glass_skylight']) {
      const m = src.config.catalog.MATERIALS[name];
      t.eq([K.hexNumber(atmos.windowLights.materials[name].emissive.hex), atmos.windowLights.materials[name].emissiveIntensity].join(), [m.emissive, m.emissiveIntensity].join(), `${name} glow`);
    }
    return `${lamps.length} lamps, ${lit.length} lit signs, ${panes.length} lit panes, ${windows.length} lit facade windows`;
  });
}

// ------------------------------------------------------------------------------------------------
// Reference pictures
// ------------------------------------------------------------------------------------------------

const REFERENCE = [
  'title', 'hud-start',
  'day-avenue-east', 'day-chop-shop', 'day-alley', 'day-vacant-lot-mural', 'day-cage', 'day-parking-lot-ipx-truck',
  'night-avenue-east', 'night-parking-lot-ipx-truck',
  'enemy-goon', 'enemy-buzzard', 'viewmodel-chopper', 'viewmodel-nine', 'plan-top-down',
];

function checkReference(dir) {
  check('reference pictures: 1280×720 PNGs, all there, under 12 MB together', (t) => {
    if (!t.ok(fs.existsSync(dir), `${path.relative(ROOT, dir)} does not exist (run tools/ue-export/reference.cjs through tools/shot.cjs)`)) return '';
    let total = 0;
    for (const file of fs.readdirSync(dir)) total += fs.statSync(path.join(dir, file)).size;
    for (const name of REFERENCE) {
      const file = path.join(dir, `${name}.png`);
      if (!t.ok(fs.existsSync(file), `${name}.png is missing`)) continue;
      const head = fs.readFileSync(file).subarray(0, 24);
      t.ok(head.toString('latin1', 1, 4) === 'PNG', `${name}.png is not a PNG`);
      t.eq(`${head.readUInt32BE(16)}x${head.readUInt32BE(20)}`, '1280x720', `${name}.png size`);
      t.ok(fs.statSync(file).size > 20000, `${name}.png is suspiciously small (a blank frame?)`);
    }
    t.ok(total < 12 * 1024 * 1024, `the directory weighs ${(total / 1048576).toFixed(1)} MB`);
    return `${REFERENCE.length} pictures, ${(total / 1048576).toFixed(1)} MB`;
  });
}

// ------------------------------------------------------------------------------------------------

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log('usage: node tools/ue-export/verify.cjs [--data <dir>] [--reference <dir> | --no-reference] [--verbose]');
    return;
  }
  const texts = {};
  const data = {};
  for (const file of FILES) {
    const full = path.join(opts.data, file);
    if (!fs.existsSync(full)) throw new Error(`${path.relative(ROOT, full)} does not exist: run node tools/ue-export/export.cjs first`);
    texts[file] = fs.readFileSync(full, 'utf8');
    data[file] = JSON.parse(texts[file]);
  }
  const seed = data['level.json'].meta.seed;
  const design = fs.readFileSync(path.join(ROOT, 'docs', 'DESIGN.md'), 'utf8');

  const src = { config: {} };
  for (const name of ['brand', 'catalog', 'enemies', 'flow', 'look', 'player', 'quality', 'text', 'weapons']) src.config[name] = await importSource(`config/${name}.js`);
  src.settings = await importSource('core/settings.js');
  src.layout = await importSource('level/layout.js');
  src.points = await importSource('level/data.js');
  src.plan = await importSource('atmos/plan.js');
  src.matsLayout = await importSource('mats/layout.js');
  src.copy = await importSource('ui/copy.js');
  src.explosives = await importSource('explosives.js');

  checkFormat(data, texts, seed);
  checkConfig(data, src);
  checkDesign(data, design);
  checkText(data, src);
  checkConversion(data);
  checkLandmarks(data, design);
  checkLevel(data, src, design);
  checkProps(data, src, design);
  checkAtmos(data, src);
  if (opts.reference) checkReference(opts.reference);

  let failed = 0;
  let comparisons = 0;
  for (const r of results) {
    comparisons += r.count;
    if (r.ok) {
      console.log(`  ok    ${r.name}${opts.verbose && r.note ? `\n          ${r.note}` : ''}`);
      continue;
    }
    failed++;
    console.log(`  FAIL  ${r.name}`);
    for (const line of r.issues.slice(0, 12)) console.log(`          ${line}`);
    if (r.issues.length > 12) console.log(`          … and ${r.issues.length - 12} more`);
  }
  console.log(`\n${results.length - failed} of ${results.length} checks passed (${comparisons} comparisons, seed ${seed}).`);
  if (failed) process.exitCode = 1;
}

main().catch((err) => {
  console.error(`verify.cjs: ${err.message}`);
  process.exitCode = 1;
});
