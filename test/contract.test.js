// The contract as data (src/core/contract.js) against the contract as prose (docs/CONTRACT.md), and
// against the modules that can be created without a browser. The rest of the modules are checked by
// main.js when the page boots: any "[contract]" line in window.__errors is a failure there.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import { createCombat } from '../src/combat.js';
import * as quality from '../src/config/quality.js';
import { EVENTS, MODULES, QUALITY_FIELDS, SHARED, missingFrom, missingKeys, missingMembers } from '../src/core/contract.js';
import { createEvents } from '../src/core/events.js';
import { createRng } from '../src/core/rng.js';
import { createSettings } from '../src/core/settings.js';
import { createPhysics } from '../src/physics.js';
import { createAudio } from '../src/stubs/audio.js';
import { createEnemies } from '../src/stubs/enemies.js';
import { createExplosives } from '../src/stubs/explosives.js';
import { createInput } from '../src/stubs/input.js';
import { createPlayer } from '../src/stubs/player.js';
import { createWeapon } from '../src/stubs/weapon.js';

const DOC = readFileSync(new URL('../docs/CONTRACT.md', import.meta.url), 'utf8');

/** The text of one `### n.m` section of the document, up to the next heading or rule. */
function section(number) {
  const start = DOC.indexOf(`### ${number} `);
  assert.ok(start >= 0, `docs/CONTRACT.md has no section ${number}`);
  const rest = DOC.slice(start + 4);
  const end = rest.search(/\n(?:#{2,3} |-{20,})/);
  return end < 0 ? rest : rest.slice(0, end);
}

/** Only the fenced code of a section: that is where the API is listed. */
const code = (text) => [...text.matchAll(/```\n([\s\S]*?)```/g)].map((m) => m[1]).join('\n');

const SECTION_OF = {
  physics: '5.1', combat: '5.2', render: '5.3',
  mats: '6.1', props: '6.2', input: '6.3', player: '6.4', weapon: '6.5', enemies: '6.6', explosives: '6.7',
  fx: '6.8', audio: '6.9', level: '6.10', atmos: '6.11', hud: '6.12', menus: '6.12', game: '6.13',
};

test('contract: the event table is the list in CONTRACT 4.2, name for name and key for key', () => {
  const listed = {};
  for (const line of code(section('4.2')).split('\n')) {
    // "name   {a, b}   comment"; one line carries two events ("ui:click {}   ui:hover {}").
    for (const m of line.matchAll(/(?:^|\s)([a-z]+(?::[A-Za-z]+)?)\s+\{([^}]*)\}/g)) {
      listed[m[1]] = m[2].split(',').map((s) => s.trim()).filter(Boolean);
    }
  }
  assert.ok(Object.keys(listed).length >= 39, `only ${Object.keys(listed).length} events were read from the document`);
  assert.deepEqual(Object.keys(EVENTS).sort(), Object.keys(listed).sort());
  for (const name of Object.keys(listed)) assert.deepEqual(EVENTS[name], listed[name], name);
});

test('contract: every module of the boot order has a member table, and nothing else does', () => {
  // src/modules.js cannot be imported here (its real-module imports only resolve inside the build).
  const registry = readFileSync(new URL('../src/modules.js', import.meta.url), 'utf8');
  const bootOrder = [...registry.matchAll(/^\s+(?:\{ name: '(\w+)'|optional\('(\w+)')/gm)].map((m) => m[1] || m[2]);
  assert.equal(bootOrder.length, 17);
  assert.deepEqual(Object.keys(MODULES).sort(), bootOrder.sort());
  assert.deepEqual(Object.keys(MODULES).sort(), Object.keys(SECTION_OF).sort());
});

test('contract: the member tables and CONTRACT sections 5 and 6 name the same things', () => {
  for (const [name, spec] of Object.entries(MODULES)) {
    const text = section(SECTION_OF[name]);
    // Table → document: every identifier of every member is a word of the section.
    for (const member of spec) {
      for (const word of member.replace(/\(\)|\[\]/g, '').split('.')) {
        assert.match(text, new RegExp(`\\b${word}\\b`), `${name}.${member}: '${word}' is not in section ${SECTION_OF[name]}`);
      }
    }
    // Document → table: everything written as `name.member` in the section's code is in the table.
    const first = new Set(spec.map((member) => member.split('.')[0].replace(/\(\)|\[\]/g, '')));
    for (const m of code(text).matchAll(new RegExp(`(?<![.\\w])${name}\\.([A-Za-z_]+)`, 'g'))) {
      assert.ok(first.has(m[1]), `section ${SECTION_OF[name]} lists ${name}.${m[1]}, the table does not`);
    }
  }
});

test('contract: the shared members of G are the rows of the table in section 4', () => {
  // The table itself plus 4.1, where the settings methods are spelled out.
  const text = DOC.slice(DOC.indexOf('## 4. The shared object'), DOC.indexOf('### 4.2'));
  for (const member of SHARED) {
    for (const word of member.replace(/\(\)/g, '').split('.')) assert.match(text, new RegExp(`\\b${word}\\b`), member);
  }
  for (const field of QUALITY_FIELDS) assert.match(section('5.3'), new RegExp(`\\b${field}\\b`), field);
  for (const row of Object.values(quality.presets)) assert.deepEqual(missingFrom(row, QUALITY_FIELDS), []);
});

test('contract: missingFrom understands values, functions, nesting and lists', () => {
  const target = {
    n: 0,
    nothing: null,
    fn() {},
    notFn: 1,
    inner: { a: false, go() {} },
    list: [{ id: 1, pos: {} }, { id: 2 }],
    empty: [],
    points: [1, null],
  };
  assert.deepEqual(missingFrom(target, ['n', 'nothing', 'fn()', 'inner.a', 'inner.go()', 'list[].id', 'empty[].anything', 'empty[]']), []);
  assert.deepEqual(missingFrom(target, ['gone', 'gone()', 'gone.deeper', 'gone[].x']), ['gone', 'gone()', 'gone.deeper', 'gone[].x']);
  assert.deepEqual(missingFrom(target, ['notFn()', 'fn.x', 'inner.b', 'inner.a()', 'nothing.x']), ['notFn()', 'fn.x', 'inner.b', 'inner.a()', 'nothing.x']);
  // One element without the key is enough, and the member is reported once.
  assert.deepEqual(missingFrom(target, ['list[].pos', 'n[]', 'points[]']), ['list[].pos', 'n[]', 'points[]']);
  assert.deepEqual(missingFrom(null, ['a', 'b()']), ['a', 'b()']);
  assert.deepEqual(missingMembers('not-a-module', {}), []);
  assert.deepEqual(missingMembers('props', { build() {}, has() {} }), ['names()']);
});

test('contract: missingKeys checks contract events only and allocates nothing for a complete payload', () => {
  const complete = { state: 'playing', prev: 'intro' };
  assert.equal(missingKeys('game:state', complete).length, 0);
  assert.equal(missingKeys('game:state', complete), missingKeys('boot:done', undefined));
  assert.deepEqual(missingKeys('game:state', { state: 'playing' }), ['prev']);
  assert.deepEqual(missingKeys('player:hit', { amount: 5, from: null, health: 95, kind: 'bullet' }), []);
  assert.deepEqual(missingKeys('player:hit', undefined), ['amount', 'from', 'health', 'kind']);
  assert.deepEqual(missingKeys('player:hit', 'bullet'), ['amount', 'from', 'health', 'kind']);
  assert.deepEqual(missingKeys('fx:my-own-event', { anything: 1 }), []);
});

test('contract: physics, combat and the stubs that run without a browser expose every member', () => {
  const events = createEvents();
  const G = {
    THREE,
    params: {},
    events,
    rng: createRng(1994),
    time: { t: 0, dt: 1 / 60, frame: 0, real: 0 },
    settings: createSettings(events, null),
    config: { brand: {}, text: {}, player: {}, weapons: {}, enemies: {}, flow: {}, quality, catalog: {}, look: {} },
    scene: new THREE.Scene(),
    camera: new THREE.PerspectiveCamera(74, 16 / 9, 0.08, 700),
    render: { post: { damage: 0, lowHealth: 0, ads: 0 } },
    fx: { tracer() {} },
    level: {
      playerStart: { pos: new THREE.Vector3(), yaw: 0 },
      explosives: [{ type: 'propane', pos: new THREE.Vector3(4, 0, 0), yaw: 0 }, { type: 'rack', pos: new THREE.Vector3(8, 0, 0), yaw: 1 }],
    },
  };
  assert.deepEqual(missingFrom(G, SHARED), []);

  G.physics = createPhysics(G);
  G.input = createInput(G);
  G.audio = createAudio(G);
  G.player = createPlayer(G);
  G.combat = createCombat(G);
  G.explosives = createExplosives(G);
  G.weapon = createWeapon(G);
  G.enemies = createEnemies(G);
  // Lists are checked element by element: give the enemy list one of each.
  G.enemies.spawn('goon', new THREE.Vector3(10, 0, 0));
  G.enemies.spawn('buzzard', new THREE.Vector3(10, 6, 5));
  assert.equal(G.enemies.list.length, 2);
  assert.equal(G.explosives.items.length, 2);

  for (const name of ['physics', 'combat', 'input', 'audio', 'player', 'explosives', 'weapon', 'enemies']) {
    assert.deepEqual(missingMembers(name, G[name]), [], `G.${name}`);
  }
});
