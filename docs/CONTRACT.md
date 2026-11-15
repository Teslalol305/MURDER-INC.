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
`{quality:'auto', sens:1, invertY:false, volume:0.8, fov:74, difficulty:'boss', mode:'mission', view:1, time:'day'}` stored as JSON in
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
weapon:melee         {hit}                               the moment the blow lands (0.16 s into the strike)
weapon:swing         {weapon}                            a melee strike starts (the whoosh; weapon = the gun in hand)
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

As built (`src/mats.js`, painters in `src/mats/*`; `?tex=256|512|1024` overrides the tier, `?matfx=0` drops the shader patches):
- **Quads**: everything returned as `{material, w, h}` is one painting for a quad of w × h metres whose UVs run 0 … 1
  across it, exactly like the stub: `planeGeo(s.w, s.h, {facing, uvScale: [1 / s.w, 1 / s.h]})`. Where the texture repeats
  (`material.map.wrapS / wrapT === RepeatWrapping`) that direction takes metre UVs instead and the quad may be any
  length: `decal('lane' | 'lane_yellow')` tiles both ways (the quad is the line; w is its nominal 0.12 m width),
  `decal('crosswalk')` along u (one bar per metre). `decal(kind, variant)` takes a variant index; extra kinds:
  `lane_yellow`, `puddle`.
- **Signs**: `lit` defaults to true except for `painted` (lit only when `lit: true`: gooseneck lamps) and `stencil` (never;
  a transparent overlay like a decal). A `text` that is exactly `IPX` is drawn with `drawIPX`. `plate` takes
  `bullet` (text) and `bulletColor`; neon takes `glow` as its second tube colour. Equal specs share one material.
- **Facades**: one repeat spans `bays × bayW` by `floors × floorH` metres, v = 0 at the wall's foot; it repeats along the
  wall and is bare wall above the top floor. Pass `w` (wall width, the bays divide it exactly) or `bayW` (default 3 m).
  `material.userData.facade = {w, h, bays, floors, bayW, floorH, overlay}`. The windows are a painted layer over the
  tiling base (`base` must be a wall material: brick_*, cinder, concrete*, stucco), so brick stays sharp close up.
- **get()**: every material carries the same five texture slots (1 × 1 stand-ins where unused), so the block stays on a
  few shader programs. `color` multiplies towards the asked colour on any material; `roughness` scales a painted roughness
  map. Also accepted: `vertexColors, flatShading, alphaTest, depthWrite, envMapIntensity`, and `local: true` for a ground
  or masonry material on something that moves (skips the world-space patch: tone variation, wet street, wall grime).
  `chainlink` is an alpha-tested weave in the opaque pass (always double-sided; `transparent` / `opacity` are ignored).
- `drawIPX` leaves the canvas state untouched and takes a CSS colour or a hex number. The real library also has
  `stats()` and `textureSize` (not on the stub).

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

Props as built (`src/props.js`, `src/props/*`; nothing here changes the shape above):
- **Facing.** Vehicles point their nose at +X, and so does the `hoop` (post at −X, rim reaching toward +X). Everything
  else with a front faces **+Z**: benches, booths, shelters, machines, racks, signs, the `billboard` face, the
  `bleachers` (lowest row at +Z), `floodlight_stand`, the open hydrant's jet. Wall pieces (`awning`, `fire_escape`) have
  the wall at −Z. `court_light` is the same all round.
- **Overhang.** Models stay inside their catalogue box except: `street_lamp` (arm and head reach 2.5 m toward +Z at
  7.8 m), `traffic_light` (mast arm 3.25 m toward +Z, heads facing ±X), `tree` (crown about 4.6 m wide above 3 m),
  `court_light` (crown 1.3 m wide at the top), `hydrant_open` (jet and wet patch reach 4 m toward +Z), a `van` with its
  back doors open, `fire_escape` with `variant: 'bottom'` (drop ladder below the landing), and the `master_case`
  light shaft. Colliders never leave the box. Props the catalogue marks `noCollide` return no colliders.
- **More fields on the result** (all optional, local space): `lights[].dir` `[x, y, z]` for lamps that aim; `anchors`
  `{name: {pos, dir}}` — attachment points: `steam` (food_cart, manhole), `propane` (food_cart: where its tank
  stands), `smolder` (burned_car), `exhaust` (generator, ipx_truck), `spray` (hydrant_open), `jet` (propane_tank,
  welding_rack: valve and flame direction), `boombox` / `beacon` / `reel` (master_case), `rearDoor` (ipx_truck: a
  point 0.9 m behind the doors); `nodes` `{name: Group}` — the moving parts of stateful props; `state`; `fallback: true`
  on a stand-in box. `hydrant_open` also sets `object.userData.spray = {x, y, z}` (nozzle direction) for atmos.
  The factory also has a debug `stats()` → `{built, fallbacks, shapes}`.
- **Options.** `seed` picks shape variant, paint and plates (same seed, same prop; none = a draw from the props
  stream). `color` repaints whatever is paint on the prop (cars, dumpster, mailbox, newspaper box, hydrant, oil drum,
  generator, porta potty, tool chest, compressor, engine hoist, bollard, awning, the IPX truck). `lit: true | false`
  forces a parked car's dome light, or switches off a lit prop (`phone_booth`, `bus_shelter`, `lot_booth`,
  `vending_machine`, `billboard`, `food_cart`); `on: false` gives a dead `street_lamp` / `court_light` /
  `floodlight_stand` (no lens glow, no lamp hint). Variants: `van` `'vulture'` (doors open unless `open: false`; any
  van takes `open: true`), `car_lift` `'car'` (brings its own raised sedan) and `'down'` (arms lowered; by default
  the arms are up and a car placed at y = 1.95 rests on the pads), `shopping_cart` `'tipped'`, `fence_panel` /
  `fence_tall` `'scrim'`, `fire_escape` `'top'` (ladder to the roof) and `'bottom'`, `sign_post` `'nopark' | 'bus' |
  'oneway' | 'stop'` and `'street'` with `text`, `awning` `'striped'` and `text` (valance lettering via `mats.sign`),
  `hydrant_open` `spray: false` (no built-in jet mesh).
- **State.** `master_case`: lid up with the gold reel on show while `live` / `grabbing`, the progress bar inside the
  lid; `taken` drops the lid (animated when `update` runs), hides the reel and every light. `ipx_truck` `open` swings
  the rear doors over 1.1 s and lights the vault; `idle` shuts them at once. Explosives: `lit` makes the shell glow
  with heat (the flame is the explosives module's fx jet; only when fx is a stub does the prop show its own at the
  valve), `gone` leaves a scorched foot. `traffic_light` cycles on `update`.
- **Materials.** Surfaces are `mats.get(name[, opts])` by catalogue name, so props merge with level meshes of the
  same material. The props' own: one atlas texture for all small graphics (two overlay materials, lit and unlit),
  one vertex-coloured glow material for every lamp lens, a cut-out lattice, and a vertex-coloured paint for the
  two explosives (one draw call each). The whole catalogue placed once is about 35 000 triangles.

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
input.setPrompt(on)               an interaction prompt is (not) showing: reveals the touch USE button, makes pad X mean Interact
input.menuNav() → {x, y, accept, back, start}   gamepad menu signals for this frame, all zero / false during gameplay
input.update(dt), input.endFrame()
```
Schemes, fallbacks, touch layout and gamepad mapping follow `$NOTES/01-player-input.md`. Touch-control DOM lives under
`#ui > .touch` and is styled in `src/input.css`. Add a touch crouch toggle and a touch melee button (the reference lacked both).
- `menuNav()`: call it once a frame from `menus.update`. `y` is −1 (up / previous) or +1 (down / next) from the D-pad or the
  left stick past 0.6, repeating after 0.38 s and then every 0.17 s; `x` is −1 / +1 once per push (adjust a slider);
  `accept` = A, `back` = B, `start` = Start (the screen's primary action), each true for one frame. Pad only: keyboard
  and mouse use the browser's own focus handling. The object is reused: read it, do not keep it.
- `setPrompt()`: until the HUD or the flow calls it, the input module listens in on `hud.prompt(spec | null)` itself.
- `hint()` knows the state: empty on touch and gamepad, the fallback explanation in `drag` mode, "Esc lets it go" while
  locked, "click to lock" while free, "Resume locks it back in" on the pause card. Use it for the look-mode toasts too.
- `aimSlow`: whatever the weapon writes wins for 0.25 s; when nothing writes it the input module computes the slow-down
  itself from `enemies.aimTarget()`. It always reads 1 unless the gamepad is the active device.
- The input module plays the rumble for `player:hit` and `explosion` itself; the weapon plays its own for rounds and
  strikes through `input.rumble`. A weaker effect never cuts a stronger one short.
- State for CSS on `<html>`: `data-device` (`kbm` | `pad` | `touch`), `data-look` (`lock` | `drag`), the classes `is-touch`
  (touch scheme in use) and `in-play` (gameplay controls active). With `is-touch` the controls take 254 × 250 px up from
  the bottom-right corner, 136 × 136 px in the bottom-left one and 56 × 56 px in the top-right one (plus safe areas):
  keep HUD blocks out of those. On touch `mode` is `drag` (fingers drag to look) and `input:lock` says so.
- A press that comes and goes between two frames still reads as `down()` for one frame. Glyphs, key maps, pad map and
  hint copy are data in `src/config/player.js` (`glyphs`, `keys`, `padButtons`, `hints`).

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
- `addRecoil(pitch, yaw)` in radians, pitch up and yaw left: 35 % goes into `player.pitch` / `yaw` for good and the aim
  vector is refreshed at once (a second round in the same frame already starts from it); the other 65 % is a view offset
  that snaps on and recentres. `player.forward` and the camera both carry it, so rounds follow the kicked view. Shake
  (`addShake`, hits, hard landings, the `explosion` event by distance) turns the camera only, never `forward`.
- `addShake(trauma)`: trauma 0…1 decays at 1.7 per second, the camera moves by trauma². A call smaller than 0.03 is a
  trickle (a train overhead, every frame): it is read as trauma per second and holds the shake at rate / 1.7.
  The player shakes for every `explosion` event itself ("at least 0.15 + 0.9·(1 − d/28)²", × 0.6 for `small`), so an
  extra `addShake` from the blast's owner does not stack with it.
- `player.eye` is the camera position: eye height plus stride bob, the landing dip and the stair glide.
- While disabled only the screen feedback keeps settling (`render.post.damage` decays). Without a weapon module
  `player.ads` follows the aim input; otherwise the weapon must write it every frame.
- The death camera (0.85 s collapse onto the floor and onto the side away from the shot) runs inside `player.update`:
  keep `enabled` true and the live update going in the `dead` state, as the stub game does.
- `damage()` ignores non-positive amounts, a dead or invulnerable player and `?god=1`. `player:hit` always comes before
  `player:dead`; a fatal fall emits `player:land`, `player:hit {kind: 'fall'}`, `player:dead` in that order.
- Read-only extras: `player.stridePhase` (a whole number at every footfall, wraps at 2: sync a viewmodel bob to it),
  `player.eyeHeight`, `player.trauma`. Tuning: `src/config/player.js`.

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
As built (explosives):
- The module builds and places the props itself from `level.explosives` (the level only lists them) and keeps one AABB
  collider per item in `item.box` (`owner: item`, tag `explosive`, surface `metal`). `reset()` puts every item back.
- Rules: propane tank 50 HP / fuse 1.6 s / radius 6.5 m / 170 damage; welding rack 70 / 1.1 s / 7.5 m / 210; the player
  takes half. The first hit lights the fuse (`explosive:lit`, a `jet` emitter at the hole, the prop goes `setState('lit')`);
  0 HP pops it 0.06 s later. `damage(item, amount, from)`: `from` an enemy object always counts 9; `from` 'blast' never
  costs hit points, it only chains.
- Chain: on every `explosion` event the explosives within `2.2 + 1.6 × size` m of it (size 1.9 tank, 2.3 rack, about
  1.2 for a Buzzard) get a fuse of `0.14 + 0…0.3 + 0.03 × distance` s, line of sight or not.
- A prop blast also shakes the camera (`player.addShake(0.15 + 0.9 g²)`, g = 1 − distance / 28) and calls
  `enemies.alert(pos, 60)`.
- Sound: while an item is lit the module holds `audio.loop('hiss', {pos, volume})` and raises its volume from 0.25 to 1
  over the fuse, stopping it at the blast: audio only has to offer a loop named `hiss` (escaping gas) and must not start
  one of its own on `explosive:lit`. That event's payload also carries `fuse` (seconds until it blows) in the real module.

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
As built (fx):
- `muzzleFlash`: `pos` and `dir` are **world space** in both modes, and fx flashes **no light**: the shooter flashes its
  own through `render.lights.flash` (weapon and enemies both do). `world = true` (enemy guns, anything seen from outside):
  flash sprites, sparks and a wisp of smoke in the world. `world = false` (the first-person gun): pass the muzzle point
  the tracer starts from (the one that lines up with the viewmodel on screen); fx spits a few sparks into the world and,
  only when nothing named `muzzle-flash` exists in `G.vmScene` (the weapon's own flash), draws the flash there itself.
- Automatic: every `impact` event → `impact` (no mark on a body), every `explosion` event → `explosion` scaled by its
  radius (6.5 m = 1) with a pooled light, a scorch mark, a smouldering site and a short screen flash when close;
  `player:land` → dust; `explosive:blast` wipes the marks on the prop that is gone. Deaths are the enemies module's.
- `smoke(pos, scale)`: dark rolling smoke; below scale 0.35 a thin pale wisp (barrel smoke). `puff(pos, hex, scale)`.
  `debris(pos, n, hex, speed)`. `decal(point, normal, kind, size)`: kind is a surface name or `bullet`, `dent`, `crack`,
  `soot`, `scorch`; size in metres (omit for the kind's own). `shell` kinds: `rifle` / `chopper`, `pistol` / `nine`.
- `addEmitter` also takes `dir` (a vector: where a `jet` points) and its handle has `setDir(v)`. `fire` and `jet` hold
  a pooled light while the camera is within about 45 m. Without `ttl` an emitter runs until stopped and survives
  `clear()`; emitters with a `ttl` do not. 24 slots: a full house returns a handle that does nothing.
- `stats()` → `{lit, additive, tracers, debris, shells, decals, emitters, budget{…}, spawned, recycled, refused,
  decalsPlaced, quality, ms}` (`ms` = cost of the last `update`). Seven draw calls at most, viewmodel flash included.

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
atmos.time                                     'day' | 'night' (section 11)
atmos.setTime(name)                            switch the whole rig between the day and the night look (between runs)
atmos.setInterior(0..1)                        optional exposure / ambient tweak when inside the shop
atmos.update(dt)                               sky, neon flicker, the El train, steam, moths, far skyline
atmos.train {active, phase, dir, x, lo, hi, y, z, speed, length}   the El train right now (read-only, see below)
atmos.passTrain(dir = 1, lead = null)          send a train now: dir +1 east / −1 west, lead = seconds until it is over the block
```
Owns: sky dome and PMREM environment, fog, ambient, the shadow light, real lights for the `quality.lights` highest-priority
`level.lamps`, additive light pools / cones for all lamps, the far skyline and rooftop silhouettes outside the bounds,
the train that crosses `level.el` (emits `train:pass`), steam emitters at `level.steam`, and the final look tuning
(`render.look`, `src/config/look.js`).
As built (atmos):
- **The train.** One sets off every 40–70 s (the first is overhead 20 s after boot), alternating direction: eastbound on
  the south track, westbound on the north one. `train:pass` comes three times per pass: `approach` (it has appeared in
  the haze 145 m outside the bounds; `duration` = seconds until its nose reaches the block, about 8.8), `over`
  (`duration` = seconds until its tail has left, about 10.4), `gone` (`duration` = seconds until it has vanished, 8.8).
  The payload also carries `dir`. `atmos.train` is live: `x` is the nose, `lo`…`hi` the extent along the street, `y` the
  rail top, `z` the track, `phase` null between trains. Audio can place its loop at `(clamp(listener.x, lo, hi), y, z)`.
  While it is overhead atmos calls `render.lights.flash` (one pooled light at a time), `fx.dust`, `fx.sparks` and trickles
  `player.addShake`. Level hints it uses when present: `level.el.deckTop` (rail top) and `level.el.tracks` ([z, z]).
- **Real lights.** `quality.lights` spot lights are created at boot and never added to or removed. They are not tied
  to fixed lamps: every 0.2 s each lamp's claim is `(priority + 1) / (1 + (d / 14)²)`, d = its distance to the point 6 m
  in front of the camera, and the lights fade over to the lamps with the highest claims. So `priority` still decides
  between lamps at equal distance, and a light is real wherever the player is. Every lamp also gets an additive pool on
  the ground (cut by the key's shadows for open-air kinds), a glow at the fixture and, from `medium` up, a cone.
  Lamp hints: `dir` aims floods and spots; neon and window lamps find the wall behind them with a ray (pools lie in front
  of it); a lamp over a deck at least 2.5 m wide (a platform, a mezzanine) lights that deck, not the street below.
- **Fog.** `scene.fog` is a FogExp2, but atmos replaces three.js' fog shader chunks at boot: the haze thickens outside
  the bounds (2 % left 105 m out) and is tinted warm toward the west, cool toward the east. Custom shaders that use
  `#include <fog_vertex>` / `<fog_fragment>` get this for free; shaders that fog by hand can read `scene.fog.color` and
  `.density` as before. `config/look.js` `fog.endReach = 0` leaves three.js untouched.
- **Beyond the bounds** atmos builds the ground frame, the avenue's sidewalks, the El from wherever the level's own
  steel stops out to 150 m, the next blocks (unlit boxes), two skyline rings, traffic and a plane. The level only needs
  to build what the player can reach or touch.
- **Interior.** atmos follows `level.interiorAt(camera)` by itself; `setInterior(f)` overrides that for 0.25 s per call
  (call it every frame to drive it). Inside: exposure × 0.86, ambient × 0.62 and warmer, haze halved.
- **Quality.** `test` / `low`: no cones, no motes, no far skyline ring, the nearer blocks only. Everything is built once;
  presets only show and hide. Debug extras: `atmos.stats()`, `atmos.settleLights()`, `atmos.interior`.

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

---------------------------------------------------------------------------------------------------

## 10. Foundation notes (as built — these refine the sections above)

The contract is also data: `src/core/contract.js` lists every module's members and every event's payload keys. Each module
is checked against it at boot, and in dev builds every emitted event is checked too. A gap is a console error starting with
`[contract]`, which lands in `__errors` and fails a harness run. `test/contract.test.js` keeps that file and this document
in step, so if you extend an API, add the member in both places (own namespace only).

- **Build**: `--only=<name>` for a module with no `src/<name>.js` yet builds its stub with a warning. `G.build = {dev, artifact, stubbed}`.
- **Fatal modules**: `render`, `physics` and `combat` (they have no stubs). Every other module falls back to its stub.
- **Time**: `G.time.t` advances every frame, including on the title screen and while paused.
- **Config**: `G.config.<file>` is the module namespace of `src/config/<file>.js` (`G.config.weapons.chopper`,
  `G.config.flow.holdout.total(n)`, `G.config.catalog.PROPS`). `text.js` and `flow.js` hold small functions for
  parametrised lines and formulas.
- **Events**: `objective:done.index` is the number of reels secured so far (1…total); a cleared holdout wave is
  `{id:'wave', index:n, total:n}`. `game:state.prev` is null at boot. No `impact` event is emitted when the player is
  hit (`player:hit` is the cue). `enemy:killed.byPlayer` is true for kills by the player's guns, melee, or any blast.
- **Physics extras**: `physics.bounds`, `physics.overlapsCylinder`, an optional reusable result argument on `raycast` /
  `moveCapsule` / `nav.findPath` (use it in hot paths: zero garbage), `nav.cell / cols / rows / origin / grid`.
  The play bounds act as walls in `moveCapsule`. A nav cell is blocked when its centre is within 0.5 m of an obstacle.
- **Combat**: `hitscan` results also carry `item` (an explosive); `explode` accepts `size`. An enemy round does a fixed
  9 damage to an explosive. A ray that stops on an explosive's own collider (`item.box`, or a box whose `owner` is the
  item) counts as a hit on that explosive.
- **Render**: `render.frame(dt, draw = true)`. `lights.acquire()` returns null once 4 lights are held (2 of the 6 stay
  free for flashes). Exposure is `render.exposure × render.look.exposure`, applied in the grade pass; bloom thresholds
  scene values before exposure (emissive above about 1 blooms). `render.look` is a live flat object
  `{toneMapping, exposure, bloomStrength, bloomRadius, bloomThreshold, bloomKnee, vignette, grain, aberration, saturation}`.
  `G.quality` keeps its identity across `setQuality`. `renderer.shadowMap.autoUpdate` is false (render refreshes it).
  Software rasterisers auto-detect to `low`.
- **Viewmodel**: `G.vmCamera` is a child of `G.vmScene` and copies the world camera's transform every frame. Parent the
  weapon rig to `G.vmCamera` to work in view space. Render owns the viewmodel key + hemisphere lights
  (`config/look.js` → `viewmodel`); `setEnvironment` applies to both scenes. A fixed `?cam=` hides the viewmodel scene.
- **Scene ownership**: every module adds its own objects to `G.scene` (the level adds `level.root` itself).
- **Helpers**: `expDecay(value, rate, dt)`, `damp(current, target, rate, dt)`; `rng.int(a, b)` is inclusive;
  `rng.fork('label')` gives a stream that depends only on seed + label. `mergeStatic(root)` returns a NEW group (merged
  meshes plus everything kept: `noMerge` subtrees, lights, lines, instanced meshes) and guts the source root.
  `mats.drawIPX(ctx, cx, cy, h, color)` takes the centre and returns the drawn width.
- **Menus card data**: `menus.show('dead' | 'complete', data)` — the data shape is whatever `src/stubs/game.js` passes
  and `src/stubs/menus.js` reads; the flow and UI engineers keep that shape (`{mode, time, reels, total, wave, kills,
  score, best, newBest, accuracy, retries, rating}`), adding fields only.
- **Page**: the Google Fonts link sits after the boot markup with a 3 s watchdog that drops it if it never arrives.
- **Harness extras**: `--skip N` / `h.skip(n)` (simulate without drawing: over 100 000 steps a second), `--verbose`,
  `--cdn-fail N`, `h.click(selector)`, `h.wait(ms)`, `h.heap()`, `h.page`. `?nohud=1` hides the whole `#ui` layer.
  `tools/scenarios/foundation-slice.cjs` plays the whole stubbed game by script; read it as a worked example.

---------------------------------------------------------------------------------------------------

## 11. Direction v2 (read with DESIGN section 8; wins over earlier sections where they differ)

### 11.1 Day and night
- `G.settings` has `time: 'day' | 'night'` (default `day`). `atmos.time` holds the active one; `atmos.setTime(name)`
  switches the whole rig (sky, sun / moon key light, ambient, fog, environment map, lamp pools and cones, far city, look
  values) without creating or removing lights and without changing shader defines. The game calls it on every run reset
  with the setting, and atmos applies the setting at boot. Both rigs are built once at boot.
- Daylight is the default and the look to polish. Materials must look right under the sun: believable albedo (nothing
  near-black except rubber and tinted glass), windows read as reflective glass by day.

### 11.2 Draw-call and texture budget (measured with `tools/scenarios/census.cjs`)
The first combined build drew 633 calls, 391 k triangles and 221 textures from the start view: the static block alone was
268 meshes with 254 distinct materials. Targets with every module real, start view, quality `low`:
**≤ 300 draw calls including the shadow pass, ≤ 300 k triangles, ≤ 90 textures, static block ≤ 70 materials.**
- **mats** packs every `sign`, `poster`, `graffiti` and `decal` into shared atlas pages. Those four calls return
  `{material, w, h, uv: [u0, v0, u1, v1]}`: `material` is shared by everything on the same page class (opaque lit signs,
  alpha lit signs, alpha unlit paper / paint / decals), and the caller must map its quad's UVs into `uv`
  (`u = u0 + s·(u1 − u0)`, `v = v0 + t·(v1 − v0)`). A missing `uv` means the full 0..1 range (the stub).
  `mats.get(name, {tint: 'vertex'})` returns a shared material with `vertexColors` on, so differently coloured instances
  (car paint, awnings, painted metal) tint through a vertex colour attribute instead of a material per colour.
- **props** keeps the whole catalogue on a small set of shared materials (vertex-colour tints, its own atlas), and marks
  quads that should not cast shadows (`castShadow = false` on decals, plates, lamp lenses).
- **level** applies the atlas `uv` rects, merges per material with `mergeStatic`, keeps decal and sign quads out of the
  shadow pass, and owns the final count: run the census and report it.
- **explosives / enemies / fx / atmos**: one or two draw calls per item or pool; instancing where there are many.

### 11.3 HUD data for the minimap (ui)
The minimap is drawn on a 2D canvas from data already exposed: `G.physics.boxes` (static colliders: anything taller than
about 2.2 m is a building or wall, lower boxes are cover), `G.level.bounds`, `level.zones` / `zoneAt`, `level.objectives`,
`level.extraction`, `G.player.pos / yaw`, and `G.enemies.list` (show an enemy while `enemy.state` is an engaged state or
within 2 s of an `enemy:fire` from it). Render the static plan once to an offscreen canvas, then blit it rotated each frame.

### 11.4 Progress notes
Every engineer keeps `/tmp/claude-0/-home-user-MURDER-INC-/8216c869-7bad-590e-a9d0-a1b3aca7a6d7/scratchpad/progress/<agent>.md`
up to date (10–25 lines: done, in progress, next, known problems, how to verify). Rewrite it after each milestone. If you
are interrupted, the next engineer starts from that file.
