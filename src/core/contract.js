// docs/CONTRACT.md as data: the members every module has to expose (sections 4 to 6) and the keys every
// event payload carries (section 4.2).
//
// main.js checks each module against MODULES when it is created and, in dev builds, every emitted event
// against EVENTS. A gap is reported as a console error that starts with "[contract]", so a module that
// forgot a member is caught at boot rather than by whichever module calls it first.
// test/contract.test.js keeps these tables and the document from drifting apart.
//
// Member notation:
//   name        a value that must be defined (null is fine: "nothing there right now")
//   name()      a function
//   a.b, a.b()  member b of the object a
//   list[].b    b on every element of the array `list` (an empty list passes)

/** Members of G that exist before the first module is created. */
export const SHARED = [
  'THREE',
  'params',
  'events.on()', 'events.off()', 'events.emit()',
  'rng.next()', 'rng.range()', 'rng.int()', 'rng.pick()', 'rng.sign()', 'rng.chance()', 'rng.fork()',
  'time.t', 'time.dt', 'time.frame', 'time.real',
  'settings.get()', 'settings.set()', 'settings.all()', 'settings.best()', 'settings.setBest()',
  'config.brand', 'config.text', 'config.player', 'config.weapons', 'config.enemies', 'config.flow',
  'config.quality', 'config.catalog', 'config.look',
];

/** Members of G that the renderer publishes when it is created. */
export const RENDER_GLOBALS = ['quality', 'renderer', 'scene', 'camera', 'vmScene', 'vmCamera'];

/** Quality row fields (section 5.3). */
export const QUALITY_FIELDS = ['name', 'scale', 'msaa', 'shadow', 'shadowEvery', 'bloom', 'lights', 'fx', 'pixelBudget', 'maxDpr'];

export const MODULES = {
  // ---- foundation (section 5) ----
  render: [
    'renderer', 'scene', 'camera', 'vmScene', 'vmCamera',
    'post.damage', 'post.lowHealth', 'post.ads', 'post.flash', 'post.fade', 'post.saturation',
    'exposure', 'look',
    'lights.flash()', 'lights.acquire()',
    'setQuality()', ...QUALITY_FIELDS.map((field) => `quality.${field}`),
    'setEnvironment()', 'frame()', 'resize()', 'stats()', 'onLevelReady()',
  ],
  physics: [
    'boxes', 'addBox()', 'addOriented()', 'removeBox()', 'removeBoxes()', 'setBounds()',
    'raycast()', 'lineOfSight()', 'moveCapsule()', 'groundHeight()',
    'nav.rebuild()', 'nav.isWalkable()', 'nav.findPath()', 'nav.clearLine()', 'nav.randomPoint()', 'nav.nearestWalkable()',
  ],
  combat: [
    'hitscan()', 'melee()', 'explode()', 'reset()',
    'stats.shots', 'stats.hits', 'stats.kills', 'stats.headshots', 'stats.damageTaken',
  ],

  // ---- optional modules (section 6) ----
  mats: [
    'get()', 'emissive()', 'sign()', 'facade()', 'poster()', 'graffiti()', 'decal()', 'drawIPX()', 'canvasTexture()',
    'names()', 'update()',
  ],
  props: ['build()', 'has()', 'names()'],
  input: [
    'move.x', 'move.y', 'look.dx', 'look.dy',
    'down()', 'pressed()', 'released()',
    'locked', 'mode', 'device', 'touch', 'sensitivity', 'invertY', 'aimSlow',
    'requestLock()', 'exitLock()', 'setGameplay()', 'glyph()', 'hint()', 'rumble()',
    'setPrompt()', 'menuNav()', 'tap()',
    'update()', 'endFrame()',
  ],
  level: [
    'root',
    'bounds.minX', 'bounds.maxX', 'bounds.minZ', 'bounds.maxZ',
    'playerStart.pos', 'playerStart.yaw',
    'objectives[].id', 'objectives[].code', 'objectives[].label', 'objectives[].zone', 'objectives[].pos', 'objectives[].prop',
    'extraction.pos', 'extraction.radius', 'extraction.label', 'extraction.code', 'extraction.prop',
    'enemySpawns[].pos', 'enemySpawns[].zone', 'enemySpawns[].type',
    'zones[].id', 'zones[].name', 'zones[].minX', 'zones[].maxX', 'zones[].minZ', 'zones[].maxZ', 'zoneAt()', 'zoneName()',
    'interiorBoxes[].min', 'interiorBoxes[].max', 'interiorAt()',
    'coverPoints[].pos', 'coverPoints[].zone',
    'cinematicPath[].pos', 'cinematicPath[].look',
    'explosives[].type', 'explosives[].pos', 'explosives[].yaw',
    'lamps[].pos', 'lamps[].color', 'lamps[].intensity', 'lamps[].range', 'lamps[].kind', 'lamps[].priority',
    'steam[]',
    'el.y', 'el.minX', 'el.maxX', 'el.minZ', 'el.maxZ',
    'vantage.stairsFoot', 'vantage.deck',
    'groundSurfaceAt()', 'update()',
  ],
  atmos: [
    'sun', 'time', 'setTime()', 'setInterior()', 'update()',
    'train.active', 'train.phase', 'train.dir', 'train.x', 'train.lo', 'train.hi', 'train.y', 'train.z', 'train.speed', 'train.length',
    'passTrain()',
  ],
  fx: [
    'muzzleFlash()', 'tracer()', 'impact()', 'sparks()', 'smoke()', 'dust()', 'puff()', 'explosion()', 'shell()',
    'debris()', 'decal()', 'addEmitter()', 'clear()', 'stats()', 'update()',
  ],
  audio: [
    'unlock()', 'setVolume()', 'setPaused()', 'setInterior()', 'setMusicIntensity()', 'play()', 'loop()', 'sting()', 'update()',
  ],
  player: [
    'pos', 'vel', 'yaw', 'pitch', 'eye', 'forward',
    'health', 'maxHealth', 'alive', 'onGround', 'sprinting', 'crouching', 'speed', 'ads', 'enabled', 'invulnerable',
    'regen.delay', 'regen.rate',
    'reset()', 'damage()', 'heal()', 'addRecoil()', 'addShake()', 'setFov()', 'surface', 'update()',
  ],
  explosives: [
    'items[].type', 'items[].pos', 'items[].hp', 'items[].state', 'items[].box',
    'reset()', 'raycast()', 'damage()', 'update()',
  ],
  weapon: [
    'current', 'def', 'state', 'mag', 'reserve', 'magSize',
    'other.id', 'other.name', 'other.mag', 'other.reserve',
    'spread', 'cue',
    'reset()', 'setVisible()', 'setView()', 'addReserve()', 'drop()', 'update()',
  ],
  enemies: [
    'list[].id', 'list[].type', 'list[].pos', 'list[].alive', 'list[].hp', 'list[].maxHp', 'list[].radius', 'list[].height',
    'list[].state', 'list[].object',
    'aliveCount()', 'countByType()', 'spawn()', 'clear()', 'raycast()', 'damage()', 'alert()', 'hear()',
    'setDifficulty()', 'setScale()', 'nearestDistance()', 'aimTarget()', 'update()',
  ],
  hud: [
    'show()', 'reset()', 'setObjective()', 'setReels()', 'setTally()', 'setMarkers()', 'prompt()',
    'warn()', 'message()', 'radio()', 'clearRadio()', 'update()',
  ],
  menus: ['show()', 'screen', 'panelOpen', 'locationCard()', 'openPanel()', 'update()'],
  game: [
    'state', 'mode', 'difficulty',
    'run.time', 'run.reels', 'run.total', 'run.retries', 'run.wave', 'run.score', 'run.kills', 'run.shots', 'run.hits',
    'start()', 'pause()', 'resume()', 'restart()', 'retry()', 'redeploy()', 'toTitle()',
    'setDifficulty()', 'debugGrab()', 'update()',
  ],
};

/** Event name → the keys its payload must carry (section 4.2). */
export const EVENTS = {
  'boot:done': [],
  'settings:change': ['key', 'value'],
  'game:state': ['state', 'prev'],
  'game:reset': ['mode'],
  'input:lock': ['locked', 'mode'],
  'input:device': ['device'],
  'ui:click': [],
  'ui:hover': [],
  'player:step': ['pos', 'surface', 'sprint'],
  'player:jump': [],
  'player:land': ['speed', 'surface'],
  'player:hit': ['amount', 'from', 'health', 'kind'],
  'player:dead': ['from'],
  'player:hitEnemy': ['enemy', 'part', 'killed', 'damage', 'weapon'],
  'weapon:fire': ['weapon', 'pos', 'dir', 'ads'],
  'weapon:reload': ['weapon', 'phase', 'empty'],
  'weapon:dry': ['weapon'],
  'weapon:switch': ['from', 'to', 'phase'],
  'weapon:melee': ['hit'],
  'weapon:swing': ['weapon'],
  'shell:bounce': ['pos', 'surface'],
  impact: ['point', 'normal', 'surface', 'dir', 'from', 'enemy'],
  explosion: ['pos', 'radius', 'size', 'source'],
  'explosive:lit': ['item', 'pos'],
  'explosive:blast': ['item', 'pos'],
  'enemy:spawn': ['enemy'],
  'enemy:alert': ['enemy', 'pos'],
  'enemy:telegraph': ['enemy', 'type', 'duration', 'pos'],
  'enemy:fire': ['enemy', 'type', 'pos', 'dir'],
  'enemy:melee': ['enemy', 'phase', 'pos'],
  'enemy:hit': ['enemy', 'part', 'damage', 'point'],
  'enemy:killed': ['enemy', 'type', 'pos', 'part', 'byPlayer', 'weapon'],
  'enemy:step': ['enemy', 'pos', 'surface'],
  'objective:progress': ['id', 't'],
  'objective:done': ['id', 'index', 'total'],
  'objective:all': [],
  'extraction:reached': [],
  'holdout:wave': ['wave', 'count'],
  'radio:line': ['speaker', 'text', 'secs'],
  'train:pass': ['phase', 'duration'],
  'quality:auto': ['name'],
};

/** Walks one member path (already split on '.') from `value`; pushes `label` on `out` when it is not there. */
function walk(value, parts, at, label, out) {
  if (value === null || value === undefined) {
    if (!out.includes(label)) out.push(label);
    return;
  }
  if (at === parts.length) return;
  let key = parts[at];
  const isCall = key.endsWith('()');
  const isList = key.endsWith('[]');
  if (isCall || isList) key = key.slice(0, -2);
  const next = value[key];
  if (isCall ? typeof next !== 'function' : isList ? !Array.isArray(next) : next === undefined) {
    if (!out.includes(label)) out.push(label);
    return;
  }
  if (isList) {
    // Every element has to be there, and has to carry whatever follows in the path.
    for (let i = 0; i < next.length; i++) walk(next[i], parts, at + 1, label, out);
  } else if (at + 1 < parts.length) {
    walk(next, parts, at + 1, label, out);
  }
}

/**
 * The members of `spec` (a list in the notation above) that `target` does not have.
 * @returns {string[]} empty when the object is complete
 */
export function missingFrom(target, spec) {
  const out = [];
  if (target === null || typeof target !== 'object') return spec.slice();
  for (const member of spec) walk(target, member.split('.'), 0, member, out);
  return out;
}

/** Contract members the module `name` does not expose (none for names the contract does not know). */
export function missingMembers(name, api) {
  const spec = MODULES[name];
  return spec ? missingFrom(api, spec) : [];
}

const NONE = Object.freeze([]);

/**
 * Keys the payload of event `name` should carry and does not. Events outside the contract (a module's
 * own namespace) are never checked. Allocates nothing when the payload is complete.
 * @returns {readonly string[]}
 */
export function missingKeys(name, payload) {
  const keys = EVENTS[name];
  if (!keys || keys.length === 0) return NONE;
  if (payload === null || typeof payload !== 'object') return keys;
  let out = null;
  for (let i = 0; i < keys.length; i++) {
    if (!(keys[i] in payload)) (out || (out = [])).push(keys[i]);
  }
  return out || NONE;
}
