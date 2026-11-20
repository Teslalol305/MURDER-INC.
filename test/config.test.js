// Config tables against docs/DESIGN.md: formulas, difficulty rows, presets, copy. Run with `node --test test/`.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as brand from '../src/config/brand.js';
import { MATERIALS, PROPS } from '../src/config/catalog.js';
import * as enemies from '../src/config/enemies.js';
import * as flow from '../src/config/flow.js';
import * as look from '../src/config/look.js';
import * as player from '../src/config/player.js';
import * as quality from '../src/config/quality.js';
import * as story from '../src/config/story.js';
import * as text from '../src/config/text.js';
import * as weapons from '../src/config/weapons.js';

const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps, `expected ${b}, got ${a}`);

test('flow: holdout formulas', () => {
  const H = flow.holdout;
  assert.deepEqual([1, 5, 10, 13, 40].map(H.total), [7, 15, 25, 30, 30]);
  [[1, 0.43], [5, 0.35], [10, 0.25], [30, 0.25]].forEach(([n, share]) => near(H.buzzardShare(n), share));
  [[1, 0.86], [5, 0.7], [14, 0.35], [30, 0.35]].forEach(([n, s]) => near(H.stagger(n), s));
  [[1, 1], [5, 1.28], [23, 2.5], [40, 2.5]].forEach(([n, s]) => near(H.hpScale(n), s, 1e-6));
  [[1, 1], [5, 1.2], [21, 2], [40, 2]].forEach(([n, s]) => near(H.damageScale(n), s));
  [[1, 1], [5, 0.88], [15, 0.6], [40, 0.6]].forEach(([n, s]) => near(H.cooldownScale(n), s));
  assert.deepEqual([1, 2, 5, 10, 30].map(H.extraAlive), [0, 1, 2, 5, 5]);
  assert.deepEqual([H.score.buzzard, H.score.goon], [100, 150]);
  near(H.score.killScale(1), 1);
  near(H.score.killScale(6), 1.5);
  assert.equal(H.score.waveClear(4), 2000);
  assert.deepEqual(H.resupply, { share: 1.5, heal: 35, explosivesEvery: 2 });
});

test('flow: debrief rating points', () => {
  const run = (time, shots, hits, retries) => flow.ratingPoints({ time, shots, hits, retries });
  // Time is the fighting of four levels (the cutscenes are not on the clock): seven minutes, eleven minutes.
  assert.equal(run(100, 100, 60, 0), 5);
  assert.equal(run(419.9, 100, 50, 1), 4);
  assert.equal(run(420, 100, 49, 0), 3); // 1 + 1 + 1
  assert.equal(run(659, 100, 30, 2), 2);
  assert.equal(run(660, 100, 29, 3), 0);
  assert.equal(run(900, 0, 0, 0), 1); // no shots fired: accuracy scores nothing
  assert.equal(text.ratings.length, 6);
  assert.equal(text.ratings[run(100, 10, 10, 0)], 'Diamond');
});

test('flow: per-difficulty rows match the design table', () => {
  assert.deepEqual(Object.keys(flow.difficulty), flow.difficulties);
  assert.equal(flow.defaultDifficulty, 'hustler');
  // regen delay / rate, then per level "patrol b+g → wave b+g", then the alive cap and the pursuit.
  const pair = (x) => (x ? `${x.buzzard}+${x.goon}` : '-');
  const row = (name) => {
    const d = flow.difficulty[name];
    return [d.regen.delay, d.regen.rate, d.levels.map((l) => `${pair(l.patrol)}>${pair(l.wave)}`).join(' '), d.maxAlive, d.pursuitEvery, d.pursuitBudget];
  };
  assert.deepEqual(row('hustler'), [3, 30, '0+2>1+2 0+3>1+3 1+3>2+3 0+2>-', 8, 8, 4]);
  assert.deepEqual(row('boss'), [4, 25, '1+3>2+3 1+3>2+4 2+4>3+5 1+3>-', 9, 7, 6]);
  assert.deepEqual(row('kingpin'), [5.5, 16, '1+4>2+5 2+4>3+6 2+5>4+7 1+4>-', 11, 5.5, 9]);
  // One row per level of the story; only the last (the run to the truck) has no wave.
  for (const name of flow.difficulties) {
    const { levels } = flow.difficulty[name];
    assert.equal(levels.length, story.levels.length, name);
    levels.forEach((l, i) => assert.equal(l.wave === null, story.levels[i].goal === 'truck', `${name} level ${i + 1}`));
  }
  assert.equal(flow.interact.hold, 2.4);
  assert.equal(flow.extraction.radius, 2.5);
  near(flow.pursuit.buzzardShare, 0.35);
});

test('enemies: difficulty overlays only touch fields the base tables have', () => {
  assert.deepEqual(Object.keys(enemies.difficulty), flow.difficulties);
  for (const [name, table] of Object.entries(enemies.difficulty)) {
    for (const part of ['buzzard', 'goon', 'ai']) {
      for (const key of Object.keys(table[part])) assert.ok(key in enemies[part], `${name}.${part}.${key} has no base value`);
    }
  }
  // Boss is the base row.
  for (const part of ['buzzard', 'goon', 'ai']) {
    for (const [key, value] of Object.entries(enemies.difficulty.boss[part])) assert.deepEqual(enemies[part][key], value, `${part}.${key}`);
  }
  const row = ({ buzzard: b, goon: g, ai }) => [
    ...[b.hp, b.boltDamage, b.telegraph, ...b.cooldown, b.spreadFar, b.spreadNear],
    ...[g.hp, g.shotDamage, g.burst, ...g.cooldown, g.spreadFar, g.spreadNear, g.rushDamage, g.runSpeed],
    ...[ai.tokens, ai.tokensCrowd, ai.tokenGap, ai.exposureUp],
  ];
  // On Hustler the Vultures are also short-sighted: 32 m against the 45 m of the base table.
  assert.deepEqual([enemies.difficulty.hustler.ai.sightRange, enemies.ai.sightRange], [32, 45]);
  // Hustler (the default) is the gentle one: slower, looser, and only one gun on the player at a time.
  assert.deepEqual(row(enemies.difficulty.hustler), [40, 5, 0.65, 2.4, 3.8, 0.08, 0.024, 80, 3, 3, 2.2, 3.6, 0.14, 0.055, 12, 4.2, 1, 2, 1.6, 0.08]);
  assert.deepEqual(row(enemies.difficulty.boss), [45, 7, 0.55, 1.9, 3.3, 0.065, 0.018, 90, 4, 4, 1.8, 3, 0.12, 0.045, 15, 4.5, 2, 3, 1.25, 0.1]);
  assert.deepEqual(row(enemies.difficulty.kingpin), [55, 10, 0.46, 1.4, 2.5, 0.052, 0.016, 110, 6, 5, 1.4, 2.4, 0.095, 0.038, 22, 5, 3, 4, 0.85, 0.14]);
  // Each step up is harder on every count that matters.
  const order = flow.difficulties.map((name) => enemies.difficulty[name]);
  for (let i = 1; i < order.length; i++) {
    const [a, b] = [order[i - 1], order[i]];
    assert.ok(b.goon.hp > a.goon.hp && b.goon.shotDamage > a.goon.shotDamage && b.buzzard.boltDamage > a.buzzard.boltDamage);
    assert.ok(b.ai.tokens > a.ai.tokens && b.ai.tokenGap < a.ai.tokenGap && b.goon.spreadFar < a.goon.spreadFar);
  }
  assert.deepEqual([enemies.pool.goon, enemies.pool.buzzard, enemies.pool.bodies], [12, 8, 6]);
  assert.deepEqual([enemies.buzzard.burstRadius, enemies.buzzard.burstDamage, enemies.buzzard.burstPlayerScale], [3, 30, 0.5]);
});

test('weapons: the five guns and the melee strike', () => {
  const { chopper, nine, ar15, switch9, rocket, melee, common } = weapons;
  const gun = (w) => [w.name, w.kind, w.auto, w.damage, w.rpm, w.magSize, w.reserve, w.range];
  assert.deepEqual(gun(chopper), ['CHOPPER', 'rifle', true, 26, 720, 30, 150, 300]);
  assert.deepEqual(gun(nine), ['NINE', 'pistol', false, 34, 420, 15, Infinity, 120]);
  assert.deepEqual(gun(ar15), ['AR-15', 'rifle', true, 31, 640, 30, 120, 320]);
  assert.deepEqual(gun(switch9), ['SWITCH', 'pistol', true, 19, 1100, 33, 132, 110]);
  assert.deepEqual(gun(rocket), ['ROCKET', 'launcher', false, 240, 60, 1, 3, 220]);
  assert.deepEqual(common.order, [chopper.id, nine.id, ar15.id, switch9.id, rocket.id]);

  for (const id of common.order) {
    const w = weapons[id];
    assert.equal(w.id, id, 'a gun is exported under its own id');
    assert.equal(w.slot, common.order.indexOf(id) + 1, `${id}: its place on the weapon bar`);
    const r = w.reload;
    assert.ok(r.magOut < r.magShow && r.magShow < r.magInsert && r.magInsert < r.magIn, `${id}: the magazine comes out, a fresh one shows, goes in, is seated`);
    assert.ok(r.magIn < r.tactical && r.tactical <= r.empty, `${id}: rounds count before the reload is over`);
    assert.equal(w.views.length, 3, `${id}: three selectable hip views`);
    // A drop is worth something to every gun that can run dry, and never lifts it past its cap.
    if (Number.isFinite(w.reserve)) assert.ok(w.pickup.rounds > 0 && w.pickup.cap >= w.reserve, `${id}: pickup`);
    else assert.equal(w.pickup, undefined, `${id} never runs dry`);
  }
  // The launcher's round: fast enough to lead a Buzzard, a blast like a propane tank's, kind to its owner.
  const p = rocket.projectile;
  assert.ok(p.speed >= 40 && p.life * p.speed >= 150);
  assert.ok(p.radius >= 5 && p.playerScale < 0.5 && p.fuse > 0);
  assert.ok(rocket.reloadAfterShot > 0);

  assert.deepEqual([melee.duration, melee.hitAt, melee.reach, melee.damage, melee.cooldown], [0.55, 0.16, 2.3, 60, 0.75]);
  near(melee.cone, (50 * Math.PI) / 180);
  assert.equal(common.headMultiplier, 2.2);
});

test('player: body and movement numbers', () => {
  const b = player.body;
  assert.deepEqual([b.radius, b.height, b.crouchHeight, b.eye, b.crouchEye, b.stepHeight], [0.32, 1.8, 1.15, 1.68, 1.05, 0.42]);
  assert.deepEqual([player.speed.walk, player.speed.sprint, player.speed.crouch, player.speed.ads], [3.8, 6.4, 1.9, 2.4]);
  near(Math.sqrt(2 * player.jump.gravity * player.jump.apex), 6.48, 0.01);
  assert.equal(player.health.max, 100);
  assert.deepEqual([player.fov.base, player.fov.ads, player.fov.viewmodel], [74, 52, 54]);
});

test('quality: every preset has the contract row fields; auto-detect never picks ultra', () => {
  const fields = ['name', 'scale', 'msaa', 'shadow', 'shadowEvery', 'bloom', 'lights', 'fx', 'pixelBudget', 'maxDpr'];
  assert.deepEqual(Object.keys(quality.presets), ['test', 'low', 'medium', 'high', 'ultra']);
  for (const [name, row] of Object.entries(quality.presets)) {
    assert.deepEqual(Object.keys(row), fields, name);
    assert.equal(row.name, name);
  }
  assert.ok(quality.ladder.every((name) => quality.presets[name]));
  assert.ok(quality.presets[quality.fallback]);

  const detect = quality.autoDetect;
  assert.equal(detect({ userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)', gpu: 'Apple GPU' }), 'low');
  assert.equal(detect({ userAgent: 'Mozilla/5.0 (Linux; Android 14) Mobile', gpu: 'Adreno (TM) 740' }), 'low');
  assert.equal(detect({ userAgent: 'Macintosh', touchPoints: 5, screenMin: 820, gpu: 'Apple GPU' }), 'low'); // small tablet
  assert.equal(detect({ userAgent: 'Macintosh', touchPoints: 5, screenMin: 1024, gpu: 'Apple GPU' }), 'high'); // big tablet
  assert.equal(detect({ userAgent: 'X11; Linux', gpu: 'ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device))' }), 'low');
  assert.equal(detect({ userAgent: 'Windows NT 10.0', gpu: 'ANGLE (Intel, Intel(R) UHD Graphics 620)' }), 'medium');
  assert.equal(detect({ userAgent: 'Windows NT 10.0', gpu: 'ANGLE (Intel, Intel(R) Arc(TM) A770 Graphics)' }), 'high');
  assert.equal(detect({ userAgent: 'Windows NT 10.0', gpu: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060)' }), 'high');
  assert.equal(detect({ userAgent: 'X11; CrOS', gpu: 'Mali-G72' }), 'medium');
  assert.equal(detect(), 'high');
});

test('text: every line the design lists is there', () => {
  assert.equal(text.title.wordmark, 'MURDER INC.');
  assert.equal(text.title.start, 'Hit the block');
  assert.deepEqual(Object.keys(text.modes), flow.modes);
  assert.deepEqual(Object.keys(text.difficulties), flow.difficulties);
  assert.deepEqual(text.reels.list.map((r) => `${r.id}:${r.code}`), ['reel1:1', 'reel2:2', 'reel3:3']);
  assert.equal(text.objectives.mission.length, 4);
  assert.equal(text.compass.length, 8);
  assert.equal(text.prompts.grab('E', '1'), 'Hold E — Grab reel 1');
  assert.equal(text.banners.contact('NORTH-EAST'), 'Contact — NORTH-EAST');
  assert.equal(text.banners.wave(3, 'EAST'), 'Wave 3 — EAST');
  assert.equal(text.banners.countdown(4, 3), 'Wave 4 in 3');
  assert.equal(text.objectives.tally.wave(2, 12345), 'Wave 2 · 12,345');
  assert.equal(text.radio.speaker, 'IPX VAULT');
  const R = text.radio;
  const holds = [R.intro, R.contact, ...R.reel, R.lowHealth, R.done, R.waveClear].map((line) => line.secs);
  assert.deepEqual(holds, [4.4, 3.2, 3.6, 3.6, 3.8, 3, 2.4, 3.4]);
  assert.equal(text.radio.waveClear.text(7), 'Wave 7 down. Fresh ammo on the block — 9 seconds.');
  // The story: a name, a brief, a first word from the Vault for every level; a line for every gun.
  const S = text.story;
  assert.deepEqual(Object.keys(S.levels), story.levels.map((l) => l.id));
  for (const [id, words] of Object.entries(S.levels)) {
    assert.ok(words.title === words.title.toUpperCase() && words.title.length > 4, id);
    assert.ok(words.brief && words.go && words.go.text && words.go.secs > 0, id);
  }
  assert.equal(S.levelOf(2, 4), 'LEVEL 2 OF 4');
  assert.equal(S.stage(2, 'THE CHOP SHOP'), 'LEVEL 2 · THE CHOP SHOP');
  assert.equal(S.objectives.reach('1', true), 'Get to reel 1 — follow the gold line');
  assert.equal(S.objectives.reach('1', false), 'Get to reel 1');
  assert.equal(S.objectives.clear(4), 'Clear the block — 4 Vultures left');
  assert.equal(S.objectives.clear(1), 'One Vulture left — finish it');
  assert.equal(S.banners.ambush('EAST'), 'Ambush — EAST');
  assert.deepEqual(Object.keys(S.speakers), ['vault', 'rule']);
  for (const id of weapons.common.order) assert.equal(text.weapons[id].name, weapons[id].name, id);
  assert.equal(text.boot.fatal('no WebGL'), 'Murder Inc. could not start: no WebGL');
  // The static first boot line in the page is the one in the text table.
  assert.ok(readFileSync(new URL('../src/page.html', import.meta.url), 'utf8').includes(`<div id="boot-msg">${text.boot.first}</div>`));
});

test('brand tokens are mirrored in base.css', () => {
  const css = readFileSync(new URL('../src/base.css', import.meta.url), 'utf8');
  const kebab = (s) => s.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);
  for (const [name, value] of Object.entries(brand.colors)) assert.ok(css.includes(`--c-${kebab(name)}: ${value};`), name);
  for (const [name, value] of Object.entries(brand.fonts)) assert.ok(css.includes(`--font-${kebab(name)}: ${value};`), name);
});

test('catalogue and look tables are well formed', () => {
  for (const [name, def] of Object.entries(PROPS)) {
    assert.ok(Array.isArray(def.size) && def.size.length === 3 && def.size.every((n) => n > 0), name);
    assert.equal(typeof def.surface, 'string', name);
  }
  for (const [name, def] of Object.entries(MATERIALS)) assert.equal(typeof def.color, 'number', name);
  for (const key of ['exposure', 'bloomStrength', 'bloomRadius', 'bloomThreshold', 'bloomKnee', 'vignette', 'grain', 'aberration', 'saturation']) {
    assert.equal(typeof look.grade[key], 'number', key);
  }
  assert.equal(look.feedback.damageTint.length, 3);
});
