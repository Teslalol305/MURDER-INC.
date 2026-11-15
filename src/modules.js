// Module registry: what gets created at boot, in which order, and what the loop calls each frame.
//
// Every optional module is imported twice: the real one (`./<name>.js`) and its stub
// (`./stubs/<name>.js`). build.mjs redirects the first import to the stub when the module is stubbed by
// `--only` / `--stub` or its file does not exist yet, so this file never needs editing. At boot the stub
// also stands in for a real module whose factory throws.

import { createCombat } from './combat.js';
import { createPhysics } from './physics.js';
import { createRender } from './render.js';

import * as atmos from './atmos.js';
import * as audio from './audio.js';
import * as enemies from './enemies.js';
import * as explosives from './explosives.js';
import * as fx from './fx.js';
import * as game from './game.js';
import * as hud from './hud.js';
import * as input from './input.js';
import * as level from './level.js';
import * as mats from './mats.js';
import * as menus from './menus.js';
import * as player from './player.js';
import * as props from './props.js';
import * as weapon from './weapon.js';

import * as atmosStub from './stubs/atmos.js';
import * as audioStub from './stubs/audio.js';
import * as enemiesStub from './stubs/enemies.js';
import * as explosivesStub from './stubs/explosives.js';
import * as fxStub from './stubs/fx.js';
import * as gameStub from './stubs/game.js';
import * as hudStub from './stubs/hud.js';
import * as inputStub from './stubs/input.js';
import * as levelStub from './stubs/level.js';
import * as matsStub from './stubs/mats.js';
import * as menusStub from './stubs/menus.js';
import * as playerStub from './stubs/player.js';
import * as propsStub from './stubs/props.js';
import * as weaponStub from './stubs/weapon.js';

/** `fx` → `createFx`: the factory every module exports (CONTRACT section 1). */
const factoryName = (name) => `create${name[0].toUpperCase()}${name.slice(1)}`;

/**
 * Wraps a module namespace as a factory call. The export is looked up when the module is created, not
 * when this file loads, so a module with a wrong export name fails alone (and falls back to its stub).
 */
function factory(name, namespace) {
  return (G) => {
    const create = namespace[factoryName(name)] ?? namespace.default;
    if (typeof create !== 'function') throw new Error(`the ${name} module does not export ${factoryName(name)}(G)`);
    return create(G);
  };
}

const optional = (name, real, stub, boot = {}) => ({
  name,
  create: factory(name, real),
  stub: factory(name, stub),
  ...boot,
});

/**
 * Boot order (CONTRACT section 3). A module may use the ones above it while it is being created and
 * the ones below it only later, from update() or event handlers.
 * `line` / `progress`: the boot-screen line (a key of config/text.js `boot`) shown from this step on.
 * Entries without a stub are foundation modules: if one of them fails, the game cannot start.
 */
export const MODULES = [
  { name: 'render', create: createRender, line: 'render', progress: 0.04 },
  optional('mats', mats, matsStub, { line: 'mats', progress: 0.12 }),
  { name: 'physics', create: createPhysics },
  optional('props', props, propsStub, { line: 'props', progress: 0.24 }),
  optional('input', input, inputStub),
  optional('level', level, levelStub, { line: 'level', progress: 0.36 }),
  optional('atmos', atmos, atmosStub, { line: 'atmos', progress: 0.52 }),
  optional('fx', fx, fxStub, { line: 'fx', progress: 0.64 }),
  optional('audio', audio, audioStub),
  optional('player', player, playerStub),
  { name: 'combat', create: createCombat },
  optional('explosives', explosives, explosivesStub),
  optional('weapon', weapon, weaponStub, { line: 'weapon', progress: 0.74 }),
  optional('enemies', enemies, enemiesStub, { line: 'enemies', progress: 0.82 }),
  optional('hud', hud, hudStub),
  optional('menus', menus, menusStub),
  optional('game', game, gameStub),
];

/** Per-frame update groups, in call order (CONTRACT section 3). */
export const UPDATE = {
  /** While the simulation is live. */
  live: ['player', 'weapon', 'enemies', 'explosives'],
  /** Whenever the game is not paused (the block keeps moving behind the title screen). */
  world: ['fx', 'level', 'atmos', 'mats'],
  /** Every frame. */
  always: ['audio', 'hud', 'menus'],
};
