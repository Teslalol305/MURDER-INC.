# MURDER INC. — module contract

Read `docs/DESIGN.md` first (fiction, names, tuning deltas, level blueprint, look, sound).
This file is the technical contract every module is built against. If you must deviate, keep the public
shape described here working and note the deviation in your final report.

`$NOTES` = `/tmp/claude-0/-home-user-MURDER-INC-/8216c869-7bad-590e-a9d0-a1b3aca7a6d7/scratchpad/spec`
(reference notes: `00-overview.md`, `01-player-input.md`, `02-weapons.md`, `03-enemies.md`, `04-game-flow.md`,
`05-ui-audio.md`, `06-world-render.md`, `07-gaps-resolved.md`). They describe the mechanics and numbers of a
reference shooter. Use them for rules, numbers and feel. Never reuse its names, copy, level layout or visual identity.

---------------------------------------------------------------------------------------------------

## 1. Ground rules

- Plain ES modules, no TypeScript, no framework. `import * as THREE from 'three'` (0.160). Addons from
  `three/examples/jsm/...` are allowed (they are bundled). No other dependencies.
- **No asset files and no network at runtime.** Geometry, textures, sounds and music are generated in code.
  (Google Fonts are linked by the page for the DOM UI only and may be blocked: everything must work with fallbacks.)
- Units: metres, seconds, radians. +Y up, north = −Z, east = +X. Yaw 0 looks toward −Z; yaw increases turning left
  (counter-clockwise seen from above); the camera uses rotation order `YXZ`. Forward vector = (−sin yaw, 0, −cos yaw).
- One shared game object **`G`** is passed to every module factory. Modules are closures:
  `export function createFoo(G) { …; return api }` (may be `async`). Never keep module state in globals.
- A module must never throw from `update(dt)` or from an event handler in normal operation, and must tolerate any other
  optional module being a stub (every method exists on stubs, most do nothing).
- Performance is a feature. Share geometries and materials; merge static meshes; pool everything that spawns at runtime;
  no allocations in per-frame hot paths (reuse scratch vectors); no `new THREE.*Light` after boot (use the pool);
  never add or remove lights or change material defines at runtime (it recompiles shaders and hitches).
- Deterministic randomness: use `G.rng` (or a `G.rng.fork()` child kept by your module), not `Math.random()`, for anything
  that affects layout or gameplay. `Math.random()` is fine for pure cosmetics.
- Wrap `localStorage` access in try/catch (use `G.settings` / `core/settings.js` helpers).
- Own only your files (section 9). Do not edit another module's files. Shared files you may append to are marked.
- Keep code readable: short comments where the intent is not obvious, no dead code, no debug leftovers.

---------------------------------------------------------------------------------------------------

## 2. Build, run, test

```
node build.mjs                      # production: dist/index.html (standalone) + dist/artifact.html (page fragment, three from CDN)
node build.mjs --dev                # unminified, sourcemap inline
node build.mjs --dev --only=level,atmos --out=dist/dev-level.html
                                    # your modules real, every other optional module stubbed (use this while building)
node build.mjs --dev --stub=audio   # everything real except the listed modules
node --test test/                   # unit tests (pure logic: physics, nav, rng, formulas)
node tools/shot.cjs dist/dev-level.html --params "autostart=1&q=low" --frames 120 --out shots/level/a.png
node tools/shot.cjs dist/dev-level.html --scenario tools/scenarios/level-walk.cjs
```

- Module names for `--only` / `--stub`: `mats, props, input, level, atmos, fx, audio, player, explosives, weapon,
  enemies, hud, menus, game`. `render`, `physics`, `combat` are always real.
- Always build to **your own** `--out` file (`dist/dev-<you>.html`) so parallel builders never clobber each other, and
  keep the default `--only=<your modules>` while others are still writing theirs. Near the end, also try a full
  `node build.mjs --dev --out=dist/dev-<you>-full.html`; if a module that is not yours fails, report it, do not fix it.
- `tools/shot.cjs` drives headless Chromium (software WebGL, slow: a few fps). It loads the page with `step=1&dt=0.0333`
  so the simulation only advances when the harness asks, which makes runs deterministic regardless of frame rate.
  A scenario is `module.exports = async (page, h) => { … }` with helpers `h.frames(n)`, `h.shot(path)`, `h.eval(fnOrString)`,
  `h.key(code, down)`, `h.mouse(dx, dy)`, `h.errors()`, `h.stats()`. Put scenarios in `tools/scenarios/<you>-*.cjs`,
  screenshots in `shots/<you>/` (git-ignored). Look at your screenshots (Read the PNG) — do not ship what you have not seen.
- Useful URL parameters: `autostart=1` (skip title and intro), `shot=1` (autostart + `test` quality + no hints),
  `q=test|low|medium|high|ultra`, `mode=holdout`, `seed`, `eseed`, `noaudio=1`, `god=1` (player takes no damage),
  `nohud=1`, `cam=x,y,z,lx,ly,lz`, `fov`, `exposure`, `post=0`, `bloom=0`, `step=1`, `dt=<sec>`.
- Debug globals: `window.__G`, `__frames`, `__ready` (true after the 2nd rendered frame), `__fatal`, `__errors[]`
  (every `console.error` and window error), `__stats()`, `__setShot({cam:"x,y,z,lx,ly,lz", fov, exposure})`, `__step`.
- Definition of done for any module: builds with `--only=<yours>` and in the full build, zero entries in `__errors`,
  screenshots reviewed, the contract API present and behaving, unit tests for pure logic where it makes sense.

---------------------------------------------------------------------------------------------------

## 3. Boot and main loop (owned by foundation: `src/main.js`)

Static page markup: `#app > canvas#view[tabindex=0]`, `#ui` (HUD, menus and touch controls are injected here by JS), and
`#boot` (`.boot-mark`, `#boot-msg`, `.boot-bar > #boot-fill`).

Boot creates modules in this order, yielding to the browser between steps and updating the boot line:
`render → mats → physics → props → input → level → atmos → fx → audio → player → combat → explosives → weapon →
enemies → hud → menus → game`, then `await G.render.onLevelReady()`, then emits `boot:done`.
At creation time a module may use modules created before it; anything later only lazily (inside `update` or handlers).
If an optional module's factory throws, its stub is used and the error is logged; only `render` is fatal.

Per frame (variable timestep, `dt = min(realDelta, 0.05)`; `?dt=` forces it; `?step=1` advances only while `__step > 0`):

1. `G.time` update → `input.update(dt)`
2. `live = game.update(dt)` — the sim is live when it returns non-false and the state is not `title` / `paused`
3. if live: `player.update`, `weapon.update`, `enemies.update`, `explosives.update` (in that order)
4. if state ≠ `paused`: `fx.update`, `level.update`, `atmos.update`, `mats.update`
5. always: `audio.update`, `hud.update`, `menus.update`
6. `render.frame(dt)`
7. `input.endFrame()`

Every call is individually try/caught; the first exception per module is logged once and the loop keeps running.

---------------------------------------------------------------------------------------------------

## 4. The shared object `G`

| Member | Owner | What |
|---|---|---|
| `THREE` | foundation | the three.js namespace |
| `params` | foundation | `Object.fromEntries(new URLSearchParams(location.search))` |
| `events` | foundation | `on(name, fn) → off()`, `off(name, fn)`, `emit(name, payload)`; handlers are try/caught |
| `rng` | foundation | seeded PRNG (`?seed`, default 1994): `next()`, `range(a,b)`, `int(a,b)`, `pick(arr)`, `sign()`, `chance(p)`, `fork()` |
| `time` | foundation | `{t, dt, frame, real}` sim time, clamped dt, frame counter, wall-clock seconds |
| `settings` | foundation | persisted user settings (4.1) |
| `config` | foundation | `{brand, text, player, weapons, enemies, flow, quality, catalog, look}` = the `src/config/*.js` exports |
| `quality` | render | copy of the active quality preset row |
| `render`, `renderer`, `scene`, `camera`, `vmScene`, `vmCamera` | render | renderer module and its main objects |
| `physics` | foundation | static AABB world + nav grid (5.1) |
| `combat` | foundation | hitscan / explosion resolution and run stats (5.2) |
| `mats`, `props`, `input`, `level`, `atmos`, `fx`, `audio`, `player`, `explosives`, `weapon`, `enemies`, `hud`, `menus`, `game` | their agents | section 6 |

### 4.1 `G.settings`
`{quality:'auto', sens:1, invertY:false, volume:0.8, fov:74, difficulty:'boss', mode:'mission', view:1}` stored as JSON in
`localStorage['murderinc.settings.v1']`, validated and clamped on load. `settings.get(key)`, `settings.set(key, value)`
(saves and emits `settings:change {key, value}`), `settings.all()`. Best holdout score: `settings.best()` /
`settings.setBest(n)` (`murderinc.holdout.best`). Modules apply their own settings on creation and on `settings:change`
(input: `sens`, `invertY`; audio: `volume`; player: `fov`; weapon: `view`; render: `quality`; game: `difficulty`, `mode`).

### 4.2 Events (name → payload). Emit exactly these names; add new ones only in your own namespace.

```
boot:done            {}
settings:change      {key, value}
game:state           {state, prev}                       title | intro | playing | paused | dead | complete
game:reset           {mode}                              after game has reset every module for a new run
input:lock           {locked, mode}                      mode: 'lock' | 'drag'
input:device         {device}                            'kbm' | 'pad' | 'touch'
ui:click {}   ui:hover {}
player:step          {pos, surface, sprint}
player:jump          {}
player:land          {speed, surface}
player:hit           {amount, from, health, kind}        from: Vector3 | null; kind: 'bullet'|'bolt'|'melee'|'blast'|'fall'
player:dead          {from}
player:hitEnemy      {enemy, part, killed, damage, weapon}   emitted by combat (drives hit markers and accuracy)
weapon:fire          {weapon, pos, dir, ads}             pos = muzzle in world space
weapon:reload        {weapon, phase, empty}              phase: 'start'|'magout'|'magin'|'bolt'|'done'|'cancel'
weapon:dry           {weapon}
weapon:switch        {from, to, phase}                   phase: 'holster' | 'draw'
weapon:melee         {hit}
shell:bounce         {pos, surface}
impact               {point, normal, surface, dir, from, enemy}   from: 'player' | 'enemy'; enemy set when a body was hit
explosion            {pos, radius, size, source}         size: 'small' | 'big'
explosive:lit        {item, pos}
explosive:blast      {item, pos}
enemy:spawn          {enemy}
enemy:alert          {enemy, pos}                        an enemy goes from unaware to engaging
enemy:telegraph      {enemy, type, duration, pos}
enemy:fire           {enemy, type, pos, dir}
enemy:melee          {enemy, phase, pos}                 phase: 'windup' | 'strike'
enemy:hit            {enemy, part, damage, point}
enemy:killed         {enemy, type, pos, part, byPlayer, weapon}
enemy:step           {enemy, pos, surface}
objective:progress   {id, t}                             t 0..1 while holding
objective:done       {id, index, total}                  id 'wave' for a cleared holdout wave
objective:all        {}
extraction:reached   {}
holdout:wave         {wave, count}
radio:line           {speaker, text, secs}
train:pass           {phase, duration}                   phase: 'approach' | 'over' | 'gone'   (atmos)
quality:auto         {name}
```

Surface names (physics, fx, audio): `asphalt`, `concrete`, `metal`, `wood`, `rubber`, `glass`, `dirt`, `brick`,
`car` (sheet metal), `cloth`, `flesh` (a Goon body), `drone` (a Buzzard).

---------------------------------------------------------------------------------------------------

## 5. Foundation modules

### 5.1 `G.physics` (`src/physics.js`)

World collision is a flat list of axis-aligned boxes; the ground is the implicit plane y = 0.

```
box = { min:Vector3, max:Vector3, surface:'concrete', tag, noNav, bulletOnly, playerOnly, owner }
  bulletOnly  hit by rays, ignored by movement and nav
  playerOnly  blocks capsule movement, ignored by rays and nav (invisible walls, glass you can shoot through)
  noNav       not stamped into the nav grid
physics.boxes                                   the list (do not mutate directly)
physics.addBox({min:[x,y,z]|Vector3, max, surface, tag, noNav, bulletOnly, playerOnly, owner}) → box
physics.addOriented(center:[x,y,z], size:[sx,sy,sz], yaw, opts) → box[]   // off-axis boxes are sliced into AABB pieces
physics.removeBox(box) / physics.removeBoxes(boxes)
physics.setBounds({minX, maxX, minZ, maxZ})    play area (nav grid extent)
physics.raycast(origin, dir, maxDist = 500) → null | {dist, point, normal, surface, box}   // box = null for the ground
physics.lineOfSight(a, b) → boolean
physics.moveCapsule(pos, vel, dt, radius = 0.32, height = 1.8, allowStep = true) → {onGround, hitWall, hitCeil, surface}
      // mutates pos and vel; vertical cylinder vs boxes, sub-stepped, wall slide, 0.42 m step-up, ground snap going down
physics.groundHeight(x, z, maxY = 50) → y      // highest box top under the point (0 if none)
physics.nav.rebuild()                           // lazy; called automatically after boxes change
physics.nav.isWalkable(x, z)
physics.nav.findPath(a, b) → Vector3[] | null   // A* on a 0.5 m grid, string-pulled
physics.nav.clearLine(a, b)                     // straight walkable segment?
physics.nav.randomPoint(center, radius) → Vector3 | null
physics.nav.nearestWalkable(x, z, maxR = 6) → Vector3 | null
```
Behaviour and numbers follow `$NOTES/06-world-render.md` section 4 (minus the sea).

### 5.2 `G.combat` (`src/combat.js`)

```
combat.hitscan({origin, dir, range, damage, from, weapon, headMult = 1}) → result
   from: 'player' or an enemy object. Player shots test world, enemies and explosives; enemy shots test world, explosives
   and the player (never other enemies). Applies the damage, emits `impact` (and `player:hitEnemy` for player shots).
   result = {type:'none'|'world'|'enemy'|'explosive'|'player', point, normal, dist, surface, enemy, part, killed, box}
combat.melee({origin, dir, reach, cone, damage}) → result          // nearest enemy in the cone with line of sight
combat.explode({pos, radius, damage, playerScale = 0.5, source})   // linear falloff, needs line of sight; hurts enemies,
                                                                    // player (× playerScale) and explosives (chain); emits `explosion`
combat.stats = {shots, hits, kills, headshots, damageTaken}         // weapon increments shots; combat the rest
combat.reset()
```
Combat talks to the other modules only through: `enemies.raycast`, `enemies.damage`, `enemies.list`, `explosives.raycast`,
`explosives.damage`, `explosives.items`, `player.pos / eye / crouching / alive`, `player.damage`.

### 5.3 `G.render` (`src/render.js`)

```
render.renderer, render.scene, render.camera          world camera: perspective, FOV from settings, near 0.08, far 700, order YXZ
render.vmScene, render.vmCamera                       viewmodel scene and camera (FOV 54, near 0.01, far 10): drawn after the
                                                      world with depth cleared, so the weapon never clips into walls
render.post = {damage:0, lowHealth:0, ads:0, flash:0, fade:0, saturation:1}   gameplay-driven, 0..1 (saturation 1 = normal)
render.exposure = 1                                   global multiplier
render.look = {...}                                   bloom strength / radius / threshold, vignette, grain, tone-map exposure
                                                      (defaults from src/config/look.js; atmos may tune)
render.lights.flash(pos, color = 0xffc880, intensity = 30, range = 10, ttl = 0.06)   pooled point light, fades to 0
render.lights.acquire() → {light, release()} | null   persistent pooled light (fires, the reel beacon)
render.setQuality(nameOrRow), render.quality          presets in src/config/quality.js: test, low, medium, high, ultra
render.setEnvironment(texture)                        scene.environment (atmos provides a PMREM of the night sky)
render.frame(dt), render.resize(), render.stats()
render.onLevelReady() → Promise                       shadow pass, shader pre-compile; called once by boot
```
- Colour: three.js colour management on, sRGB output, tone mapping in the output pass (plain forward fallback if the
  post chain fails to compile). HDR half-float targets; emissive values above ~1 bloom.
- Shadows: `renderer.shadowMap` is enabled by quality (`quality.shadow` = map size, 0 = off). **atmos** owns the single
  shadow-casting directional light and fits its shadow camera to the level bounds. Render refreshes the shadow map every
  `quality.shadowEvery` frames.
- Quality row fields: `{name, scale, msaa, shadow, shadowEvery, bloom, lights, fx, pixelBudget, maxDpr}`.
  `quality.lights` = how many *static* real point/spot lights atmos may create; `quality.fx` scales particle budgets.
- Layers: world objects on layer 0; viewmodel objects live in `vmScene` (no layer tricks needed).

### 5.4 Shared helpers (`src/core/`)

- `core/util.js`: `clamp, lerp, damp(current, target, rate, dt), smoothstep, wrapAngle, angleDelta, moveToward, expDecay, v3(x,y,z)`.
- `core/geo.js`: `boxGeo(w, h, d, opts)` (UVs in metres so textures tile at real scale), `planeGeo`, `cylGeo`,
  `tubeGeo(points, radius)`, `mergeGeos(list)`, `bakeTransform(mesh)`, and
  `mergeStatic(root) → Group` which merges every mesh under `root` per material (after baking world matrices), skipping
  subtrees with `userData.noMerge`. Vertex attributes are normalised to position / normal / uv (+ colour when present).
- `core/rng.js`, `core/events.js`, `core/settings.js`.

---------------------------------------------------------------------------------------------------

## 6. Module APIs

Every module may expose more; these members are the contract. `update(dt)` is called by the loop when present.

### 6.1 `G.mats` — materials and generated textures  (agent: mats)
```
mats.get(name, opts?) → MeshStandardMaterial     cached by name + opts; names in src/config/catalog.js MATERIALS
                                                  opts: {color, roughness, metalness, emissive, emissiveIntensity, doubleSide, transparent, opacity}
mats.emissive(color, intensity = 2) → Material    unlit HDR-bright material for lamps, LEDs, neon tubes (blooms)
mats.sign(spec) → {material, w, h}                canvas sign. spec {text, sub, w, h (metres), style:'neon'|'box'|'painted'|'awning'|'street'|'stencil'|'plate',
                                                  fg, bg, glow, lit:true}   lit signs carry an emissive map
mats.facade(spec) → Material                      building wall with a window grid: {base:'brick_red', floors, bays, floorH, lit:0..1, seed, shopfront:false}
mats.poster(kind, seed) → {material, w, h}        'ipx' | 'show' | 'wanted' | 'ad' | 'torn'    (transparent quads, polygonOffset)
mats.graffiti(text, seed, color?) → {material, w, h}
mats.decal(kind) → {material, w, h}               'oil' | 'crack' | 'manhole' | 'grime' | 'scorch' | 'bullet' | 'crosswalk' | 'arrow' | 'lane'
mats.drawIPX(ctx, x, y, h, color)                 draws the IPX wordmark on a 2D canvas (used by signs, truck livery, HUD fallback)
mats.canvasTexture(w, h, draw(ctx, w, h), opts) → CanvasTexture   {srgb:true, repeat:[u,v], aniso}
mats.names(), mats.update(dt)                     update = neon flicker etc.
```
Textures tile in metres: geometry UVs are in metres (core/geo.js), each material sets its own `map.repeat`.
Texture size respects `G.quality` (`test` 256, low 512, else 1024). Wait for `document.fonts.ready` (max 1.5 s) before
drawing text.

### 6.2 `G.props` — prop factory  (agent: props)
```
props.build(name, opts?) → {
   object: THREE.Group,          origin on the ground at the footprint centre; length along +X
   colliders: [{min:[x,y,z], max:[x,y,z], surface, bulletOnly?, playerOnly?, noNav?}],   local space, yaw 0
   size: [L, H, W], surface,
   dynamic?: true,               must not be merged (animated or state-changing); also set object.userData.noMerge = true
   update?(dt), setState?(state, t), lights?: [{pos:[x,y,z], color, intensity, range, kind}]   lamp hints for atmos (local space)
}
props.has(name), props.names()
opts: {color, seed, variant, open, lit, on}
```
Catalogue (names, sizes, surfaces) is `src/config/catalog.js` PROPS. A builder that is missing or throws falls back to a
plain box of the catalogue size. Colliders flatter than 0.2 m with a top under 0.3 m are walk-over (skipped by level).
Stateful props:
- `master_case` — the objective. `setState('live' | 'grabbing' | 'taken', t)`: live = gold beacon pulsing, boombox thumping;
  grabbing = progress `t` 0..1 shown on the case; taken = case gone / lid shut, beacon off. Needs `update(dt)`.
- `ipx_truck` — extraction. Hazard lights and rear door light; `setState('idle' | 'open')`.
- `propane_tank`, `welding_rack` — explosive visuals; `setState('idle' | 'lit' | 'gone')`.

### 6.3 `G.input`  (agent: input-player)
```
input.move {x, y}                 strafe right +x, forward +y, magnitude ≤ 1
input.look {dx, dy}               yaw and pitch delta for this frame, radians, already scaled by device, sensitivity and invert
input.down(action) / input.pressed(action) / input.released(action)
        actions: fire, ads, jump, sprint, crouch, reload, interact, swap, weapon1, weapon2, melee, pause
input.locked, input.mode ('lock' | 'drag'), input.device ('kbm' | 'pad' | 'touch'), input.touch (boolean)
input.sensitivity, input.invertY, input.aimSlow = 1        look-rate multiplier set by weapon (gamepad aim assist)
input.requestLock(), input.exitLock(), input.setGameplay(on)   on = gameplay controls active (shows touch controls, grabs keys)
input.glyph(action) → string      label for the current device: 'E', 'X', 'USE', 'LMB', 'RT' …
input.hint() → string             one-line look-mode description for the pause card
input.rumble(strong, weak, ms)
input.update(dt), input.endFrame()
```
Schemes, fallbacks, touch layout and gamepad mapping follow `$NOTES/01-player-input.md`. Touch-control DOM lives under
`#ui > .touch` and is styled in `src/input.css`. Add a touch crouch toggle and a touch melee button (the reference lacked both).

### 6.4 `G.player`  (agent: input-player)
```
player.pos (feet), vel, yaw, pitch, eye:Vector3, forward:Vector3
player.health, maxHealth, alive, onGround, sprinting, crouching, speed, ads (0..1, written by weapon each frame), enabled, invulnerable
player.regen = {delay, rate}                  written by game per difficulty
player.reset({pos, yaw}), player.damage(amount, from, kind), player.heal(n)
player.addRecoil(pitch, yaw), player.addShake(trauma), player.setFov(deg), player.surface (surface underfoot)
player.update(dt)                             moves, sets G.camera, emits player:* events
```
When `enabled` is false the player does not move or look, and does not touch the camera (title fly-through, debrief).

### 6.5 `G.weapon`  (agent: weapon)
```
weapon.current ('chopper' | 'nine'), weapon.def, weapon.state ('idle'|'firing'|'reloading'|'switching'|'melee'|'lowered')
weapon.mag, weapon.reserve (Infinity for the Nine), weapon.magSize, weapon.other {id, name, mag, reserve}
weapon.spread (current cone half-angle, rad), weapon.cue ('' | 'reloading' | 'low' | 'reload' | 'empty')
weapon.reset(), weapon.setVisible(on), weapon.setView(1|2|3), weapon.addReserve(n, cap), weapon.drop()
weapon.update(dt)                             reads input; fires through G.combat.hitscan; writes player.ads; drives fx and events
```
Viewmodel and arms are built in code and live in `G.vmScene`. Rule's forearms: bare, brown skin, a gold watch.

### 6.6 `G.enemies`  (agent: enemies)
```
enemy = {id, type:'goon'|'buzzard', pos:Vector3 (feet for goons, centre for buzzards), alive, hp, maxHp, radius, height, state, object}
enemies.list                                  live + dying
enemies.aliveCount(), enemies.countByType(type)
enemies.spawn(type, pos, {alerted, target}) → enemy | null     null when the pool is full
enemies.clear()
enemies.raycast(origin, dir, maxDist) → null | {enemy, dist, point, normal, part:'head'|'body'}
enemies.damage(enemy, amount, {point, dir, part, from, weapon}) → {killed}
enemies.alert(pos, radius)                    everyone within radius investigates / engages toward pos
enemies.hear(pos, radius)                     softer: unaware enemies investigate
enemies.setDifficulty(table)                  table = config.enemies.difficulty[name]
enemies.setScale({hp, damage, cooldown})      holdout wave multipliers (1 = base)
enemies.nearestDistance() → metres to the closest living enemy (Infinity if none)
enemies.aimTarget(origin, dir, maxDist) → boolean   unoccluded enemy under the ray? (gamepad aim slow-down)
enemies.update(dt)
```
AI, perception, tokens, spawn-in behaviour and both attack patterns follow `$NOTES/03-enemies.md` with the numbers in
DESIGN.md 3.1. Enemy guns use `G.combat.hitscan({from: enemy, …})`; Buzzard bolts are simulated projectiles.

### 6.7 `G.explosives`  (agent: fx)
```
explosives.items = [{type:'propane'|'rack', pos, hp, state:'idle'|'lit'|'gone', box}]
explosives.reset()                            rebuild from level.explosives
explosives.raycast(origin, dir, maxDist) → null | {item, dist, point, normal}
explosives.damage(item, amount, from)
explosives.update(dt)
```
Visuals come from `G.props.build('propane_tank' | 'welding_rack')`; each has a collider (solid cover until it blows).

### 6.8 `G.fx`  (agent: fx)
```
fx.muzzleFlash(pos, dir, scale = 1, world = true)
fx.tracer(from, to, color = 0xffe2a8, speed = 260)
fx.impact(point, normal, surface, dir)        surface-appropriate burst + decal (also fired automatically on every `impact` event)
fx.sparks(pos, dir, n), fx.smoke(pos, scale), fx.dust(pos, scale), fx.puff(pos, color, scale)
fx.explosion(pos, scale = 1)                  also fired automatically on every `explosion` event
fx.shell(pos, vel, kind = 'rifle')            ejected brass with bounce (emits shell:bounce)
fx.debris(pos, n, color, speed), fx.decal(point, normal, kind, size)
fx.addEmitter(pos, kind, {ttl, scale}) → {stop(), setPos(v)}     kinds: steam, smolder, embers, fire, drip, jet
fx.clear(), fx.stats(), fx.update(dt)
```
Budgets scale with `G.quality.fx`. Two billboard pools (lit / additive), pooled tracers, debris, shells and decals.

### 6.9 `G.audio`  (agent: audio)
```
audio.unlock()                                call from the first user gesture (menus do this)
audio.setVolume(0..1), audio.setPaused(on), audio.setInterior(0..1), audio.setMusicIntensity(0..1)
audio.play(name, {pos, volume, pitch}) → handle | null      one-shots; without pos = non-spatial
audio.loop(name, {pos, volume}) → {setPos(v), setVolume(x), stop()}
audio.sting(name)                             'reel' | 'all' | 'dead' | 'complete'
audio.update(dt)                              listener follows G.camera
```
Audio subscribes to the events in 4.2 itself (weapon, player, impact, explosion, enemy, objective, train, ui).
`?noaudio=1` → the stub is used.

### 6.10 `G.level`  (agent: level)
```
level.root: Group                              merged static meshes + dynamic props
level.bounds {minX, maxX, minZ, maxZ}
level.playerStart {pos:Vector3, yaw}
level.objectives [{id:'reel1'|'reel2'|'reel3', code:'1'|'2'|'3', label, zone, pos:Vector3, prop}]   prop = props.build('master_case')
level.extraction {pos:Vector3, radius:2.5, label:'IPX truck', code:'IPX', prop}
level.enemySpawns [{pos:Vector3, zone, type:'ground'|'air'}]
level.zones [{id:'west'|'avenue'|'shop'|'lot', name, minX, maxX, minZ, maxZ}], level.zoneAt(x, z) → id
level.interiorBoxes [{min:Vector3, max:Vector3}], level.interiorAt(pos) → 0..1
level.coverPoints [{pos:Vector3, zone}]
level.cinematicPath [{pos:Vector3, look:Vector3}]            title fly-through, 10–14 points, start → reel 1 → shop → cage → truck
level.explosives [{type:'propane'|'rack', pos:Vector3, yaw}]
level.lamps [{pos:Vector3, color, intensity, range, kind:'street'|'el'|'work'|'flood'|'neon'|'window', priority, dir?:Vector3}]
level.steam [Vector3], level.el {y, minX, maxX, minZ, maxZ} (track deck), level.vantage {stairsFoot, deck}
level.groundSurfaceAt(x, z) → surface
level.update(dt)                               animated props (objective beacons, truck hazards, fans)
```
The level builds everything inside the play bounds, registers all colliders with `G.physics`, and calls `physics.setBounds`.

### 6.11 `G.atmos` — sky, light and life  (agent: atmos)
```
atmos.sun                                      the single shadow-casting DirectionalLight
atmos.setInterior(0..1)                        optional exposure / ambient tweak when inside the shop
atmos.update(dt)                               sky, neon flicker, the El train, steam, moths, far skyline
```
Owns: sky dome and PMREM environment, fog, ambient, the shadow light, real lights for the `quality.lights` highest-priority
`level.lamps`, additive light pools / cones for all lamps, the far skyline and rooftop silhouettes outside the bounds,
the train that crosses `level.el` (emits `train:pass`), steam emitters at `level.steam`, and the final look tuning
(`render.look`, `src/config/look.js`).

### 6.12 `G.hud` and `G.menus`  (agent: ui)
```
hud.show(on), hud.reset()
hud.setObjective(text)                         typed out
hud.setReels(done, total) | hud.setTally(text) reel bullets "n/3", or the holdout tally line
hud.setMarkers([{id, code, label, pos:Vector3, kind:'reel'|'exit'}])
hud.prompt(null | {text, glyph, progress})     interaction ring
hud.warn(text, secs), hud.message(text, secs), hud.radio(speaker, text, secs), hud.clearRadio()
hud.update(dt)                                 compass, crosshair (from weapon.spread), ammo block, health block, markers, kill feed,
                                               hit markers, damage arcs — all read from G.* and events
menus.show(screen, data?)                      'none' | 'title' | 'paused' | 'dead' | 'complete'; data = stats for the cards
menus.screen, menus.panelOpen
menus.locationCard(on)                         intro card
menus.update(dt)
```
Menus call the game through `G.game` only: `game.start({mode})`, `game.resume()`, `game.restart()`, `game.retry()`,
`game.redeploy()`; settings through `G.settings.set`. The HUD listens to `player:hitEnemy`, `enemy:killed`, `player:hit`
itself. Full inventory and behaviour: `$NOTES/05-ui-audio.md`, restyled per DESIGN.md 6.

### 6.13 `G.game` — flow  (agent: flow)
```
game.state, game.mode ('mission' | 'holdout'), game.difficulty
game.run {time, reels, total, retries, wave, score, kills, shots, hits}
game.start({mode, skipIntro, quick}), game.pause(), game.resume(), game.restart(), game.retry(), game.redeploy(), game.toTitle()
game.setDifficulty(name), game.debugGrab()     debugGrab instantly secures the next reel
game.update(dt) → live:boolean
```
Owns the state machine, the run reset, objectives and interaction, reinforcement waves, pursuit, extraction, holdout,
radio queue, rating, the music-intensity driver, the title fly-through camera, post fades (`render.post.fade / saturation`).

---------------------------------------------------------------------------------------------------

## 7. Config files (`src/config/`, plain data, created by foundation)

| File | Content | May be edited by |
|---|---|---|
| `brand.js` | title, presenter, star line, IPX wordmark text, URL text, colour tokens, storage prefix | ui |
| `text.js` | every player-facing string from DESIGN.md 2 | flow, ui |
| `player.js` | movement, camera, health numbers | input-player |
| `weapons.js` | both weapons, melee, spread / recoil tables | weapon |
| `enemies.js` | base stats, per-difficulty tables, AI constants | enemies |
| `flow.js` | timings, wave tables per difficulty, pursuit, holdout formulas, rating thresholds | flow |
| `quality.js` | quality presets | (foundation) |
| `catalog.js` | `MATERIALS` (name → base colour / roughness / metalness) and `PROPS` (name → size, surface) | mats, props, level (append only, re-read before each edit) |
| `look.js` | exposure, bloom, fog, grade defaults | atmos |

## 8. Page, CSS, branding

- `src/page.html` is the page fragment (title, meta, font links, markup). `src/base.css` (page, `#app`, canvas, boot screen,
  CSS custom properties from the brand tokens), `src/ui.css` (HUD + menus) and `src/input.css` (touch controls) are
  concatenated in that order.
- The page is a full-bleed one-screen app: `html, body { height: 100% }`, `#app { position: fixed; inset: 0 }`.
  Anything pinned to a screen edge adds that edge's `env(safe-area-inset-*, 0px)`; side gutters are
  `max(16px, env(safe-area-inset-left|right, 0px))`. It must work at phone width (about 400 px) and in landscape phones.
- All colours come from CSS custom properties defined on `:root` (single deliberate dark look, `color-scheme: dark`).

## 9. File ownership

| Agent | Files |
|---|---|
| foundation | `build.mjs`, `package.json`, `src/main.js`, `src/modules.js`, `src/stubs/*`, `src/core/*`, `src/config/*` (initial), `src/physics.js`, `src/combat.js`, `src/render.js`, `src/page.html`, `src/base.css`, `tools/shot.cjs`, `test/*` |
| mats | `src/mats.js`, `src/mats/*` |
| props | `src/props.js`, `src/props/*` |
| level | `src/level.js`, `src/level/*` |
| atmos | `src/atmos.js`, `src/atmos/*`, `src/config/look.js` |
| fx | `src/fx.js`, `src/fx/*`, `src/explosives.js` |
| audio | `src/audio.js`, `src/audio/*` |
| input-player | `src/input.js`, `src/input.css`, `src/player.js`, `src/config/player.js` |
| weapon | `src/weapon.js`, `src/weapon/*`, `src/config/weapons.js` |
| enemies | `src/enemies.js`, `src/enemies/*`, `src/config/enemies.js` |
| ui | `src/hud.js`, `src/menus.js`, `src/ui.css`, `src/ui/*`, `src/base.css`, `src/page.html`, `src/config/brand.js` |
| flow | `src/game.js`, `src/game/*`, `src/config/flow.js`, `src/config/text.js` |

Everyone: scenarios in `tools/scenarios/<agent>-*.cjs`, tests in `test/<agent>-*.test.js`.
If you find a bug in a foundation file, make the smallest fix and say so in your report.
