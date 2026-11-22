# 08 — Data export: the web game's numbers as JSON, and reference pictures

Port spec for the Unreal Engine 5 rebuild of MURDER INC. The web game is the ground truth for tuning, layout and copy.
This document describes the five JSON files that carry that truth into the Unreal project, the tool that writes them,
the tool that checks them, and the reference pictures of the game as it is today.

Nothing in the files is typed in by hand. The exporter boots the real game in headless Chromium and reads it; where a
value is private to a module it is taken from that module's own source, and section 9 says which path each value took.

| What | Where |
|---|---|
| Exported data | `unreal/MurderInc/Content/Data/config.json`, `text.json`, `level.json`, `props.json`, `atmos.json` |
| Exporter | `tools/ue-export/export.cjs` (helpers in `tools/ue-export/lib/`) |
| Self-check | `tools/ue-export/verify.cjs` |
| Reference pictures | `docs/unreal/reference/*.png`, made by `tools/ue-export/reference.cjs` |

What was exported for seed 1994 (the game's default):

| File | Size | Holds |
|---|---|---|
| `config.json` | 89 kB | every tuning table of `G.config` (brand, catalog, enemies, flow, look, player, quality, weapons), the settings defaults, the enemy tuning resolved for each difficulty, the explosive rules |
| `text.json` | 24 kB | every string table: the copy deck, brand lines, input glyphs and hints, interface labels, the page's static text, the lettering painted in the world |
| `level.json` | 1.4 MB | bounds, 4 zones, **777 colliders** (322 oriented prop boxes behind them), start pose, 3 reels, the extraction zone, **29 ground + 17 air spawn points**, **100 cover points**, **21 explosives**, the interior, the El (36 columns on 18 bents, deck, girders, station), the train's path and schedule, the nav grid (184 × 136 cells), 6 buildings, 347 placed signs / posters / graffiti / decals, 192 window panes, 17 window facades with 240 windows, the layout table |
| `props.json` | 477 kB | the catalogue (**68 types**, their variants, colliders, lamps, anchors) and **329 placed props** (308 by the level + the 21 explosives) of 62 types |
| `atmos.json` | 173 kB | the day and night lighting rigs, sky and haze parameters, **90 lamps**, 17 lit signs, 57 lit panes, 79 lit facade windows |

---------------------------------------------------------------------------------------------------

## 1. How to re-run

```
npm install                                  once: esbuild and three (the build needs them)
node tools/ue-export/export.cjs              builds dist/dev-export.html from src/, boots it, writes the five files
node tools/ue-export/verify.cjs              checks them; exits 1 on any mismatch
```

Run the exporter after any change to `src/`, then the verifier. Both need Node 22 and the same Playwright / Chromium the
existing harness (`tools/shot.cjs`) uses; nothing else. On the build machine (software WebGL, shared CPU) the page boots
in 12 to 16 s and the whole export takes 25 to 35 s. The page needs about 3 GB of memory: run one at a time.

Options of `export.cjs`:

| Option | |
|---|---|
| `--page <file.html>` | read an existing build instead of building one: `--page dist/index.html` reads the committed production build and writes byte-identical files |
| `--out <dir>` | where the JSON goes (default `unreal/MurderInc/Content/Data`) |
| `--seed <n>` | world seed (default 1994). Another seed gives another block: prop seeds, paints and a few yaws change |
| `--raw <dir>` | also dump what the page collectors answered, untouched (debugging) |
| `--verbose` | echo the page console |

What the exporter does, in order:

1. Builds `dist/dev-export.html` (`node build.mjs --dev --out=dist/dev-export.html`; `dist/dev-*` is git-ignored).
2. Serves it locally and opens it in headless Chromium with `step=1&dt=0.0333&q=low&noaudio=1&seed=1994`, with every
   outside request refused, exactly like the harness. Before the game's script runs it installs the capture hooks of
   `lib/hooks.cjs` (section 9). It stops if the page logs an error, falls back to a stub, or boots its modules in an
   unexpected order.
3. On the title screen (no run is started) it runs the collectors of `lib/collect.cjs` in the page: tuning, level,
   props, signage, glass, light.
4. Calls every function the game keeps among its tuning (holdout formulas, text lines) with sample inputs.
5. Lets the block run for up to two minutes of game time, undrawn, until the first two El trains have come and gone.
6. Builds every catalogue prop for seeds 0 to 47 (types with a paint palette: 0 to 255) to learn what a seed varies.
7. In Node: adds the Unreal-space twin of every position and direction, rounds, checks its own consistency (section 10
   lists what would stop it) and writes the files.

The output is deterministic: two runs give byte-identical files, and so does a run on the dev build and one on the
production build. No time stamps, no machine names, no random identifiers are written. Quality `low` is forced only to
boot quickly; no exported value depends on the quality preset (the real-light rig, the shadow frustum and the texture
atlas layout do, and are left out for that reason).

---------------------------------------------------------------------------------------------------

## 2. Conventions of all five files

- **Pretty-printed JSON**, two-space indentation, UTF-8, a final newline. An array or object that fits in 132 columns
  is written on one line (a position is one line). Keys are in the order the exporter builds them, which is fixed.
- **Numbers are rounded to 4 decimals.** A web value is rounded first and its Unreal twin is computed from the rounded
  value, so every Unreal number in the files can be reproduced exactly from the web number next to it.
- **`meta`** opens every file: `file`, `about`, `game`, `schema` (1), `generator`, `spec` (this document), `seed`,
  `readFrom`, `units`, `conversion`, `numbers`, and per file `counts` and notes on encodings.
- **`source`**: most sections start with a `source` string saying where the section was read from. It is documentation,
  not data.
- **Two spaces side by side.** A record that has a place in the world carries two blocks:
  `web` (metres, radians, three.js axes: what the web game uses) and `ue` (centimetres, degrees, Unreal axes). The two
  blocks describe the same thing; an Unreal reader only ever needs `ue`. Field names inside the blocks:

  | In `web` | In `ue` | Meaning |
  |---|---|---|
  | `pos`, `min`, `max`, `center`, `corner`, `look`, `from`, `to`, … `{x, y, z}` | same name `{X, Y, Z}` | a point: metres → centimetres, axes swapped |
  | `right`, `up`, `normal`, `direction`, `toLight`, `aim`, `wall`, `dir`, `toSun`, `toMoon` `{x, y, z}` | same name `{X, Y, Z}` | a unit direction: axes swapped, no scale |
  | `rotationY` (radians) + `forward` `{x, y, z}` | `yaw` (degrees) | a prop's turn about the up axis: `Object3D.rotation.y`, and where its local +X points |
  | `yaw` (radians, a heading) + `facing` `{x, y, z}` | `yaw` (degrees) | the player's heading: 0 looks at −Z, positive turns left |
  | `facing` `{x, y, z}` | `yaw` (degrees) | a horizontal facing |
  | `front` `{x, y, z}` | `frontYaw` (degrees) | the way a prop's front looks (section 7.2) |
  | `right`, `up` | `rotator` `{Pitch, Yaw, Roll}` | a flat face (section 3.4) |
  | `aim` / `direction` | `rotator` `{Pitch, Yaw, Roll}` | a light or camera pointing along the direction |
  | `minX, maxX, minZ, maxZ` | `minX, maxX, minY, maxY` | a rectangle on the ground |
  | `radius`, `width`, `height`, `roof`, `top`, … | same name | a length: × 100 |
  | — | `center`, `extent` next to `min`, `max` | an axis-aligned box as Unreal likes it: centre and half size |

  A single length is written as `{ "web": 1.5, "ue": 150 }`.
- **Colours.** A colour the game stores as a `0xRRGGBB` number is written as a `"#rrggbb"` string (sRGB). In
  `atmos.json` and the prop catalogue a colour is `{ "hex": "#rrggbb", "linear": [r, g, b] }`, where `linear` is what an
  `FLinearColor` takes. Arrays `[r, g, b]` in the look tables are linear scene-referred radiance and stay arrays.
- **Infinity.** JSON has none: `weapons.nine.reserve` is the string `"Infinity"` (the NINE never runs dry).
- **Functions.** A function in the tuning tables is written as
  `{"$function": {"params": [...], "source": "<JavaScript text>", "samples": [{"args": [...], "value": ...}, ...]}}`.
  The samples are what the running game answered; `source` is the text of the function in `src/config`.
  A text line that takes values is written as
  `{"$template": {"template": "Wave {n} · {score}", "params": ["n", "score"], "formats": {"score": "rounded to a whole number, en-US digit grouping (12,345)"}, "source": "...", "example": {"args": [3, 12345], "value": "Wave 3 · 12,345"}}}`.
- **Indices.** Every list entry that is referred to from elsewhere carries its own `index`. Cross references are
  indices: a collider's `owner.prop` and a lamp's `prop` point into `props.json` `instances.list`; a prop's `colliders`
  point into `level.json` `colliders.boxes`; a prop's `lamps` into `atmos.json` `lamps.list`; and so on.
- **Key case.** Unreal's `FJsonObject` folds the case of keys. No object in these files has two keys that differ only
  by case (`web` and `ue` exist as separate blocks for that reason: `x` and `X` never share an object). The verifier
  checks this.
- `interior` on a record is true where `level.interiorAt()` is above 0.5 (inside the chop shop).
  `zone` is the game's zone id (`west`, `avenue`, `shop`, `lot`); `place` is the display name the minimap band shows
  there (`WEST END`, `THE AVENUE`, `CHOP SHOP`, `THE CAGE`, `THE LOT`).

---------------------------------------------------------------------------------------------------

## 3. Coordinates

### 3.1 The three spaces

| | Units | Up | East | North | Hand |
|---|---|---|---|---|---|
| Web (three.js) | metres, radians | +Y | +X | −Z | right |
| Blender | metres | +Z | +X | +Y | right |
| Unreal | centimetres, degrees | +Z | +X | −Y (Y is south) | left |

```
Blender (x, y, z) = (x_web, −z_web, y_web)
Unreal  (X, Y, Z) = (x_web,  z_web, y_web) × 100 = (x_blender, −y_blender, z_blender) × 100
```

Web → Unreal only swaps two axes and scales. Swapping two axes turns a right-handed frame into a left-handed one
without mirroring anything: the block reads the same from above in both, and so does the lettering on every sign.

### 3.2 Angles

Three angle conventions meet in the files.

- **A prop's turn** (`web.rotationY`, radians) is `Object3D.rotation.y`: a positive value turns the prop
  counter-clockwise seen from above, and its local +X axis points to `(cos θ, 0, −sin θ)` in the world (`web.forward`).
  In Unreal the same turn is `ue.yaw = −θ` in degrees, wrapped to (−180, 180].
- **A heading** (`playerStart.web.yaw`, radians) follows `docs/CONTRACT.md` section 1: 0 looks at −Z (north), positive
  turns left, forward = `(−sin yaw, 0, −cos yaw)`. Its Unreal yaw is `atan2(forward.z, forward.x)` in degrees.
- **An Unreal yaw** is in degrees: 0 faces +X (east), +90 faces +Y (south), −90 faces north.

For any horizontal web direction `d`: `ue yaw = atan2(d.z, d.x)` in degrees. For any direction:
`Pitch = asin(d.y)`, `Yaw = atan2(d.z, d.x)`, `Roll = 0` (a light pointing straight down has Pitch −90).

### 3.3 Worked examples (values from the files)

**A point: the start pose.** `level.json` `playerStart`:

```
web  pos (x −37.4, y 0.15, z 8.15) m        yaw −1.4908 rad        facing (0.9968, 0, −0.0799)
ue   X = −37.4 × 100 = −3740    Y = 8.15 × 100 = 815    Z = 0.15 × 100 = 15    → (−3740, 815, 15) cm
     facing = (−sin(−1.4908), 0, −cos(−1.4908)) = (0.9968, 0, −0.0799)
     yaw = atan2(−0.0799, 0.9968) = −4.5837°        east, 4.6° toward north
Blender  (−37.4, −8.15, 0.15) m
```

Rule stands on the south sidewalk (Y positive is south of the avenue's centre line), 15 cm above the roadway, facing
east and a little toward the avenue.

**A prop: the Vultures' van beside reel 1.** `props.json` instance 219:

```
web  pos (−9.4, 0, 1.8)    rotationY 3.6916 rad (= π + 0.55)    forward (cos θ, 0, −sin θ) = (−0.8525, 0, 0.5227)
ue   pos (−940, 180, 0)    yaw = −3.6916 × 180 / π = −211.51° → wrapped 148.4873°
     check: atan2(0.5227, −0.8525) = 148.49°            nose pointing west and a little south
```

**A box: an El column.** `level.json` collider 8:

```
web  min (−45.32, 0, −4.92)   max (−44.68, 5.3, −4.28)
ue   min (−4532, −492, 0)     max (−4468, −428, 530)     center (−4500, −460, 265)   extent (32, 32, 265)
```

No axis is flipped, so a box's min stays its min. `extent` is the half size (`UBoxComponent::SetBoxExtent`).

**A direction: the afternoon sun.** `atmos.json` `rigs.day.key`:

```
web  direction (0.5529, −0.7879, −0.271)   the way the light travels: east, down, a little north
ue   direction (0.5529, −0.271, −0.7879)
     rotator   Pitch = asin(−0.7879) = −51.99°   Yaw = atan2(−0.271, 0.5529) = −26.11°   Roll 0
```

Give a `DirectionalLight` that rotator and it shines the way the web game's sun does, 52° above the horizon.

### 3.4 Flat faces: signs, panes, wall faces

Signs, posters, decals, window panes and facade faces are flat rectangles. Each has, in both spaces:

| Field | |
|---|---|
| `pos` | the centre of the rectangle |
| `corner` | its bottom-left corner as seen from in front of it |
| `right` | the direction its width runs: the reading direction of a sign, the viewer's right |
| `up` | the direction its height runs |
| `normal` | the side it shows; in web space `normal = right × up` |
| `width`, `height` | its size |
| `ue.rotator` | the rotation of an actor whose local **+X is `right`, +Z is `up`, +Y is `normal`** |

So a plane mesh modelled in the XZ plane, reading along +X, with its visible side toward +Y in Unreal (toward −Y in
Blender) lands on the face with `SetActorLocationAndRotation(ue.pos, ue.rotator)`. This is the same frame as the
wall-module convention of the art pipeline (pivot at the bottom-left corner of the outer face, running along +X, outer
face toward −Y in Blender): place a wall module at `ue.corner` with `ue.rotator`.
A sign on a wall that faces south has rotator (0, 0, 0); one that faces north has Yaw 180; a decal lying on the ground
with its top toward north has Roll −90.

---------------------------------------------------------------------------------------------------

## 4. `config.json`

Everything in this file is in **web units** (metres, seconds, radians, metres per second). Multiply lengths and speeds
by 100 on the Unreal side. It mirrors `G.config`, the namespace objects of `src/config/*.js`, key for key.

| Key | Source | Content |
|---|---|---|
| `meta` | | see section 2, plus `encoding` (colours, infinity, functions) |
| `settings` | `G.settings.all()` in a clean profile | `storageKey`; `defaults`: `quality`, `sens`, `invertY`, `volume`, `fov`, `difficulty`, `mode`, `view`, `time` |
| `brand` | `G.config.brand` | `title`, `titlePlain`, `presenter`, `starLine`, `ipx {wordmark, url}`, `storagePrefix`, `colors` (the interface palette, CSS strings), `lines` (route-bullet colours by marker code), `fonts` (CSS font stacks) |
| `player` | `G.config.player` | `body` (radius, heights, eye heights, step height), `speed`, `accel`, `jump`, `sprint`, `stride`, `look`, `fov`, `health`, `fall`, `bob`, `recoil`, `shake`, `death`, `input` (device look rates, gamepad curve, touch layout), `keys`, `mouseButtons`, `padButtons`, `glyphs`, `hints`, `touchButtons`, `touchGlyphs` (SVG path data of the web touch buttons) |
| `weapons` | `G.config.weapons` | `chopper` and `nine` (damage, rate, magazine, reserve, range, aim time, reload timeline, spread, recoil, kick springs, flash, rumble, view poses), `melee`, `common` (head multiplier, holster and draw times, spread and sprint rules, tracer, viewmodel lighting) |
| `enemies` | `G.config.enemies` | `goon`, `buzzard`, `ai` (base values = Hustler, plus everything that never changes), `difficulty` (`hustler`, `boss`, `kingpin`: only the fields that differ), `pool` (instance caps), `look` (readability by day and night), `seed` |
| `flow` | `G.config.flow` | `timing`, `post`, `titleCamera`, `interact`, `extraction`, `spawn` (how a spawn point is scored), `pursuit`, `difficulty` (regen, patrol, the three waves, alive cap, pursuit), `holdout` (formulas as `$function`), `rating`, `ratingPoints` (`$function`), `music`, `pacing`, `defaultDifficulty`, `difficulties`, `modes` |
| `quality` | `G.config.quality` | `presets` (test, low, medium, high, ultra), `ladder`, `fallback`, `autoDetect` (`$function`), `dynamicResolution` |
| `catalog` | `G.config.catalog` | `MATERIALS` (name → base colour, roughness, metalness, emissive) and `PROPS` (name → `size` `[length, height, width]`, `surface`, flags). The prop catalogue with everything measured is in `props.json` |
| `look` | `G.config.look` | `grade`, `feedback`, `sky`, `daySky`, `fog`, `dayFogTint`, `ambient`, `sun`, `viewmodel`, `palette`, `env`, `lamps` (how each lamp kind is drawn), `interior`, `city`, `train`, `life`, `detail`, `times` (the day and night rigs), `clearColor` |
| `enemiesResolved` | `G.enemies.debug().tune` after `setDifficulty` | `hustler`, `boss`, `kingpin`: each `{goon, buzzard, ai}` with the base table and that difficulty's overlay merged, as the AI reads it. Use this, not `enemies` + `enemies.difficulty`, to fill a data table per difficulty |
| `explosives` | `G.explosives.items[n].kind`; `src/explosives.js` | `kinds.propane` / `kinds.rack`: `prop`, `hp`, `fuse`, `radius`, `damage`, `size`, `box` `[x, y, z]`, `jet`. `rules`: `popFuse`, `playerDamageScale`, `damageFromEnemyRound`, `shakeReach`, `alertRadius`, and `chainRange(size)`, `chainFuse(dist, roll)`, `sizeFromRadius(radius)` as `$function` |

The functions and their sample inputs:

| Function | Sampled for |
|---|---|
| `flow.holdout.total`, `buzzardShare`, `stagger`, `hpScale`, `damageScale`, `cooldownScale`, `extraAlive`, `score.killScale`, `score.waveClear` | wave n = 1 … 30 (every formula has levelled off by then) |
| `flow.ratingPoints(run)` | 72 runs: time 120 / 269.9 / 270 / 399.9 / 400 / 600 s × accuracy 0 / 29 / 30 / 49 / 50 / 100 % × retries 0 / 1 |
| `quality.autoDetect(env)` | 8 devices (default, a phone, a tablet, a software rasteriser, three GPU strings) |
| `explosives.rules.chainRange` / `chainFuse` / `sizeFromRadius` | the two explosive sizes; distances 0 / 2 / 4 / 6 m × rolls 0 / 0.5 / 1; radii 1 / 3 / 6.5 / 7.5 / 12 m |

Colours are `"#rrggbb"` strings under these keys: `color`, `lightColor`, `arcColor`, `keyColor`, `clearColor`,
`ambientSky`, `ambientGround`, `emissive`, everything in `look.palette`, `sky` / `ground` of an `ambient` block, and
`zenith` / `horizon` / `glow` of `look.sky`.

---------------------------------------------------------------------------------------------------

## 5. `text.json`

| Key | Source | Content |
|---|---|---|
| `brand` | `G.config.brand` | `title` `MURDER INC.`, `titlePlain`, `presenter`, `starLine`, `ipx {wordmark, url}` |
| `text` | `G.config.text` | the copy deck, key for key: `title`, `location` (`place`, `tagline`, `taglineHoldout`, `byTime.day` / `night`), `zones`, `zoneName` (`$function`), `modes`, `difficulties`, `weapons`, `reels` (`item`, `list[] {id, code, label}`), `extraction`, `enemies`, `explosives`, `objectives` (`mission[]`, `holdout`, `tally.standby`, `tally.wave` `$template`), `prompts` (`grab` `$template`, `refuse`), `compass[8]`, `notes`, `banners` (`contact`, `wave`, `countdown`: `$template`), `radio` (`speaker`, and `{text, secs}` for `intro`, `introHoldout`, `contact`, `reel[3]`, `lowHealth`, `done`, `waveClear`), `cards` (`pause`, `dead`, `debrief`), `ratings[6]`, `boot` (the boot lines; `fatal` `$template`), `world` (`shop`, `storefronts[10]`) |
| `input` | `G.config.player` | `glyphs` (`kbm` / `pad` / `touch`: action → label; `layoutCodes`), `hints` (look-mode hints), `touchButtons` (`[id, glyph, label, caption]`) |
| `interface` | `src/ui/copy.js` (Node import) | labels only the HUD and the menus use: `title`, `location`, `hud` (`cue.emptySwap` `$template`), `cards`, `panel` (`noteAuto` `$template`), `controls` (the three control tables), `glance`, `glanceOther` |
| `page` | the page's DOM | `title`, `boot {presenter[2], wordmark, star, note}`, `canvasLabel` |
| `lettering` | hooks on `G.mats.sign` / `graffiti` / `poster` | what is painted in the world: `signs[] {text, sub, style, uses}`, `graffiti[] {text, uses}`, `posters[] {kind, variant, uses}`. Where each one hangs: `level.json` `signage` |

The nine templates: `banners.contact` `Contact — {dir}`, `banners.wave` `Wave {n} — {dir}`, `banners.countdown`
`Wave {n} in {secs}`, `boot.fatal` `Murder Inc. could not start: {error}`, `objectives.tally.wave`
`Wave {n} · {score}`, `prompts.grab` `Hold {glyph} — Grab reel {code}`, `radio.waveClear.text`
`Wave {n} down. Resupply at your feet — 9 seconds.`, `interface.hud.cue.emptySwap` `Empty — {glyph} swaps`,
`interface.panel.noteAuto` `Quality was picked for this device ({tier}). …`.

Where `text` and `interface` overlap (zone names, the location card) `text` wins in the web game (`src/menus.js`).
Section 8.1 of `docs/DESIGN.md` is already applied in the copy: the title eyebrow carries no time, the location card
follows the time of day (`location.byTime`), the boot line is "Waiting on the next train".

---------------------------------------------------------------------------------------------------

## 6. `level.json`

All positions are in both spaces (section 2). Lists are in the game's own order; that order is what indices mean.

### 6.1 Extent and ground

| Key | Fields |
|---|---|
| `bounds` | `web {minX, maxX, minZ, maxZ}` = −46 … 46, −34 … 34; `ue {minX, maxX, minY, maxY}`. The play area and the extent of the nav grid. The ground is the plane y = 0 (Z = 0) |
| `zones[4]` | `id` (`west`, `shop`, `avenue`, `lot`), `name`, rectangle. A point outside every rectangle belongs to the nearest |
| `places.regions[6]` | `name`, `zone`, rectangle: the display name by place. The `lot` zone is `THE CAGE` north of the avenue (z < −7), `THE LOT` south of it (z > 7), `THE AVENUE` on the roadway between them |
| `ground.surfaces[16]` | `surface` (`asphalt`, `concrete`, `dirt`), rectangle: what the bare ground plane is made of (footsteps, impacts). Boxes standing on it report their own surface |
| `ground.floors[25]` | `height {web, ue}` (0 or 0.15 m), rectangle: the level's own walking surface, 0 on the roadway and 15 cm on a sidewalk slab. The slabs are colliders too (tag `sidewalk`) |

The three rectangle lists each cover the block exactly once. They are the answers of `level.zoneName`,
`level.groundSurfaceAt` and `level.floorAt` sampled on a 0.1 m grid (every edge of the layout lies on it).

### 6.2 Points the game flow uses

| Key | Fields |
|---|---|
| `playerStart` | `zone`; `web {pos, yaw, facing}`; `ue {pos, yaw}`. `pos` is the point between the feet |
| `objectives[3]` | `index`, `id` (`reel1` …), `code` (`1` …), `label`, `zone`, `place`, `interior`, `prop` (the `master_case` in `props.json`); `web {pos, rotationY, forward}`; `ue {pos, yaw}`. Interaction rules: `config.json` `flow.interact` |
| `extraction` | `label`, `code`, `zone`, `place`; `web {pos, radius}`; `ue {pos, radius}`: the zone behind the truck's rear doors (radius 2.5 m; vertical reach in `flow.extraction`). `truck {prop, web {pos, rotationY, forward}, ue {pos, yaw}}`: the IPX truck itself, nose east |
| `enemySpawns.points[46]` | `index`, `type` (`ground` \| `air`), `zone`, `place`, `interior`, `facingSource`; `web {pos, facing}`; `ue {pos, yaw}`. Ground points first (29), then air points (17). None in the west zone. **`facing` is derived, not game data** (section 9) |
| `coverPoints.points[100]` | `index`, `zone`, `place`, `interior`, `onDeck` (true for the three on the mezzanine and the shed deck); `web {pos}`; `ue {pos}` |
| `explosives.items[21]` | `index`, `type` (`propane` \| `rack`), `prop` (`propane_tank` \| `welding_rack`), `hp`, `zone`, `place`, `interior`, `collider`; `web {pos, rotationY, forward}`; `ue {pos, yaw}`. Rules per type: `config.json` `explosives` |
| `interior` | `fade {web, ue}` (1.5 m); `boxes[1] {web {min, max}, ue {min, max, center, extent}}`: the chop shop; `doorways[2] {web {outside, inside}, ue {…}}`: the openings the Buzzards fly in through (the roll door and the bay), at flying height. `interiorAt` is 1 inside a box and falls linearly to 0 over `fade` outside it |
| `vantage` | `web {stairsFoot, deck}`, `ue {…}`: the scaffold shed in front of S3 |
| `cinematicPath.points[14]` | `index`; `web {pos, look}`; `ue {pos, look, rotator}`: the title fly-through. The game flies a closed curve through them (`src/game/titlecam.js`, timing in `flow.titleCamera`) |
| `steam.vents[6]` | `web {pos}`, `ue {pos}` |
| `puddles.pools[28]` | `web {x, z, radius}`, `ue {X, Y, radius}`: where water stands at night; by day the street is dry outside the open hydrant's reach |

Spawn points and cover points are the level's values after it moved the ones that were authored inside an obstacle's
margin to the nearest walkable nav cell (21 points moved, 2.5 m at most).

### 6.3 Buildings, the El, the train

| Key | Fields |
|---|---|
| `buildings.storeys` | `web {ground 3.8, upper 3.1}`, `ue`: storey heights |
| `buildings.list[6]` | `id` (`n1`, `n2`, `s1`, `s2`, `s3`, `garages`), `name` (the collider tag: `tenement`, `deli`, `station house`, `pawn`, `S3`, `garages`), `wall` (catalogue material), `floors`, `colliders[]`; `web {minX, maxX, minZ, maxZ, roof, parapetTop}`; `ue {…}`. `roof` is the roof slab, `parapetTop` the top of the colliders (0.9 m higher) |
| `buildings.backs[7]` | collider indices: the backs of the neighbours that seal the north, east and south edges |
| `el.deck` | `web {underside 6.5, railTop 6.83, minX, maxX, minZ, maxZ, tracksZ [−2.1, 2.1]}`; `ue {…, minY, maxY, tracksY}` |
| `el.bents` | `count` 18; `web.x[]`, `ue.X[]`: a column pair every 10 m, ten inside the bounds (−45 … 45) and four more past each closure (decor) |
| `el.columns[36]` | `collider`, `row` (`north` \| `south`), `insideBounds`; `web {x, z, top, halfWidth}`; `ue {X, Y, top, halfWidth}`: centre of the column, its top (5.3 m), half its collider's width (0.32 m). Rows at z = ±4.6 |
| `el.girders[20]` | `collider`, `kind` (`cross` \| `longitudinal`); box in both spaces |
| `el.deckCollider`, `el.station[23]` | collider indices: the deck slab; the sealed station (mezzanine, bridges, stairs, platforms) |
| `el.layout` | `EL` and `STATION` of `src/level/layout.js`: `rowZ`, `half`, `spacing`, `bents`, `far`, `columnTop`, `tracks`, `gauge`, `tieTop`, `railTop`; the station's mezzanine, bridge and stair extents (web metres) |
| `train` | `cars` 5, `carLength`, `carGap`, `carWidth`, `carHeight` (web metres); `length {web 79.8, ue}`; `speed {web 16.5 m/s, ue}`; `runUp {web 145, ue}` |
| `train.tracks[2]` | `dir` (+1 east, −1 west), `heading`, `track` (eastbound runs on the south track), `seconds {approach, over, gone, total}`; `web {from, to, trackZ, railTop, forward}`; `ue {from, to, trackY, railTop, yaw}`. `from` / `to`: where the **nose** appears and where it vanishes, 145 m outside the bounds |
| `train.schedule` | `rule`, `firstOverhead` 20 s, `firstStart` 11.2121 s, `every` [40, 70] s, `firstDir` +1, `alternates` |
| `train.observed[2]` | the first two trains of this boot: `pass`, `dir`, `heading`, `trackZ`, `clock {begins, over, gone, ended}` on the atmosphere's clock (seconds of un-paused time since boot) |

The train is announced three times per pass (`train:pass`): `approach` when it appears (8.79 s before its nose reaches
the block), `over` (10.41 s until its tail has left), `gone` (8.79 s until it vanishes).

### 6.4 Colliders

`colliders.boxes[777]`: every static collision box of the block, in the order `G.physics.boxes` holds them. The web
game's world is nothing but these axis-aligned boxes over a flat ground.

| Field | |
|---|---|
| `index` | position in the list |
| `tag` | what the level calls it (glossary below). For a prop's collider it is the prop's catalogue name |
| `surface` | `asphalt`, `concrete`, `metal`, `wood`, `rubber`, `glass`, `dirt`, `brick`, `car`, `cloth`: impact and footstep material |
| `owner` | `{kind: "level"}`, `{kind: "prop", prop, name}` (index into `props.json` `instances.list`) or `{kind: "explosive", explosive, type}` (index into `explosives.items`) |
| `blocks` | `movement` (bodies), `shots` (rays: rounds and line of sight), `nav` (stamped into the nav grid) |
| `flags` | the game's own three flags: `bulletOnly` (rays only), `playerOnly` (movement only: invisible walls, glass and mesh you can shoot through), `noNav` |
| `orientedBox` | index into `orientedBoxes.boxes`, or null |
| `web {min, max}`, `ue {min, max, center, extent}` | the box |

`colliders.byTag`, `byOwner`, `bySurface` count them. 440 belong to props, 21 to explosives, 316 to the level itself.

`orientedBoxes.boxes[322]`: every box that was asked for at an angle (all of them prop colliders), before the web
game's physics sliced it into up to 10 axis-aligned pieces: `index`, `prop`, `name`, `tag`, `colliders[]`,
`web {center, size, rotationY}`, `ue {center, extent, yaw}` (`extent` = half the length, width, height along the box's
own X, Y, Z). **For a prop, Unreal should use the oriented box (or the mesh's own collision), not the sliced pieces**:
the pieces are an approximation forced by an engine that only knows axis-aligned boxes. They matter for one thing:
the nav grid of the web game was stamped from them.

Tags of the level's own colliders:

| Tag | What |
|---|---|
| `sidewalk` | the nine raised slabs (0.15 m) |
| `tenement`, `deli`, `station house`, `pawn`, `S3`, `garages` | the six buildings, cut around their shop-door recesses; `backs`: the neighbours' backs; `bulkhead`: rooftop stair heads |
| `facade` | bullet-only skins a few centimetres proud of a storefront (sign bands, gates, piers), so a round stops where the wall is drawn |
| `el-column`, `el-girder`, `el-deck`, `station` | the El |
| `shop-wall`, `shop-roof`, `shop-column`, `mezzanine`, `office`, `safe`, `shop-stair` | the chop shop; `office-glass` and `railing` are player-only (rounds pass) |
| `alley-gate`, `cage-plinth`, `cage-fence` (player-only: chain-link), `hoarding`, `dock`, `lot-wall`, `lot-gate`, `lot-sign` | the yards |
| `kiosk`, `tyre-cage`, `produce-stand`, `dig`, `shanty`, `hoist`, `scaffold`, `roadblock`, `shed-post`, `shed-deck`, `shed-stair` | the avenue's closures and sidewalk blockers, the scaffold shed |
| `seal` | player-only walls 8 m high behind every edge of the block: nothing leads out |
| `explosive` | the 21 explosives (removed when one blows, back on reset) |

### 6.5 Nav grid and movement constants

| Key | Fields |
|---|---|
| `nav.web` / `nav.ue` | `cell` (0.5 m), `origin {x, z}` / `{X, Y}` (the north-west corner), `inflate` (0.5 m), `bandMin` (0.47 m), `bandMax` (1.5 m) |
| `nav.cols`, `nav.rows` | 184, 136 |
| `nav.rule` | the rule in words (below) |
| `nav.free`, `nav.blocked` | 9052, 15972 |
| `nav.grid.cells[136]` | one string per row (north to south), one character per cell (west to east): `#` blocked, `.` free |
| `physics` | constants of `src/physics.js`: `STEP_HEIGHT` 0.42, `AIR_STEP` 0.08, `NAV_CELL`, `NAV_INFLATE`, `NAV_BAND_MIN`, `NAV_BAND_MAX`, `SLICE_THRESHOLD`, `SLICE_MAX`, `SLICE_SHRINK` |

Cell (i, j) covers x from `origin.x + i · cell` and z from `origin.z + j · cell`. A cell is blocked when its centre lies
within `inflate` of a collider that blocks nav: not `noNav`, not `bulletOnly`, not `playerOnly`, top at or above
`bandMin` and bottom at or below `bandMax` (lower things are stepped over, higher ones walked under). The outer ring is
always blocked. Goons path with A* over the 8 neighbours and pull the path straight. Unreal will build its own
navigation mesh from collision; the grid is here to compare it against (where can a Goon stand, which pockets are
closed), and it is what the minimap is drawn from.

### 6.6 Signs, glass, facades

| Key | Fields |
|---|---|
| `signage.paintings[87]` | `index`, `kind` (`sign`, `poster`, `graffiti`, `decal`), `uses`, `tiles`, `web {width, height}`, `ue {…}` (its natural size). A sign adds `text`, `sub`, `style` (`neon`, `box`, `painted`, `awning`, `street`, `stencil`, `plate`), `lit`, `fg`, `bg`, `glow`, `bullet`, `bulletColor`; a poster `poster`, `variant`; graffiti `text`, `variant`, `color`; a decal `decal` (`lane`, `lane_yellow`, `crosswalk`, `arrow`, `crack`, `oil`, `grime`, …), `variant` |
| `signage.placements[347]` | `index`, `painting`, `kind`, `label`, `zone`, `place`, `interior`, `onGround`, and the face (section 3.4). A decal, poster or tag may be stretched: the placement's `width` / `height` are the quad's own. A `tiles` painting (lane paint, the crosswalk) repeats along a quad of any length |
| `glazing.panes[192]` | `index`, `material` (`glass_dark`, `glass_store`, `glass_lit_warm`, `glass_lit_cool`, `glass_skylight`), `zone`, `place`, `interior`, and the face. Storefront windows and doors, the station's window bands, transoms, the shop's four skylights, the glass of the bus shelter and the booths. Car glass is part of the vehicle props and is not listed |
| `facades.grids` | by material name (`facade:brick_red`, `facade:brick_tan`, `facade:brick_brown`): `base`, `seed`, `litFraction`, `bays`, `floors`, `web {bayWidth, floorHeight, width, height, windowWidth, windowHeight, sill}`, `ue {…}`, `style {frame, stone, lintel, paired}`, `windowsPerRepeat`, `litPerRepeat`. One repeat is 4 bays × 5 storeys of 3.1 m; it repeats along a wall and is bare above its top floor |
| `facades.faces[17]` | `index`, `grid`, `base`, `zone`, `place`, `gridOrigin {u, v}` (the face's bottom-left corner in grid metres), the face, and `windows[] {floor, bay, state, ac, web {pos}, ue {pos}}`: the centre of every window that is wholly on the face. `state`: `dark`, `warm` (a lamp-lit room) or `tv`; `ac`: a window unit on the sill |

The upper storeys of the web game's buildings are flat walls with a painted window layer. The faces and windows tell
the modular kit where real windows go.

### 6.7 `layout`

`src/level/layout.js` as data (web metres): `BOUNDS`, `KERB` 0.15, `ROAD_Z` 7, `FRONT_Z` 11, `GROUND_FLOOR` 3.8, `FLOOR`
3.1, `EL`, `STATION`, `SHOP` (walls, eave, the roll door, the bay, the side door, the mezzanine, stair, skylights, work
lights), `ALLEY`, `CUT`, `CAGE` (fence, plinth, gates, court), `VACANT`, `LANE`, `LOT`, `SHED`, `BUILDINGS`,
`SIDEWALKS`, `PADS`, `DRIVEWAYS`, `ZONES`, `CAGE_NAME`. Rectangles are `x0, x1, z0, z1`. This is the table the level
is built from; it has no Unreal twin because it is a design table, not placed geometry.

---------------------------------------------------------------------------------------------------

## 7. `props.json`

### 7.1 `catalogue.types` (68 types, by catalogue name)

| Field | |
|---|---|
| `family` | the file under `src/props` that builds it: `vehicles`, `street`, `clutter`, `shop`, `lot`, `gameplay` |
| `surface` | impact material of the type |
| `dynamic` | never merged into the static level: `ipx_truck`, `hydrant_open`, `traffic_light`, `master_case`, `propane_tank`, `welding_rack` |
| `noCollide` | the catalogue says it never collides (`traffic_cone`, `manhole`, `mattress`, `boombox`, `water_tower`, `fire_escape`, `awning`) |
| `stateful`, `state` | has `setState()`; its state after boot (`ipx_truck` idle, `master_case` live, explosives idle) |
| `animated` | has `update(dt)` |
| `front` | `{web, ue, blender}`: the local axis its front looks along (section 7.2) |
| `size` | `web {length, height, width}`: the catalogue box, length along the prop's own X; `ue {X, Y, Z}` |
| `paint` | null, or `palette[]` (the colours a seed can draw, `"#rrggbb"`) and `domeLightShare` (share of seeds 0 … 255 whose interior light is on; cars only) |
| `variants[]` | the shapes a seed can pick: a prop built with seed s is variant `s mod variants.length` |
| `options[]` | the same again for every option set the level uses that changes the shape: `{options, paint, variants[]}` (today only the van with `{open: true, variant: "vulture"}`) |
| `catalogue.neverPlaced` | types the block does not use: `traffic_light`, `sign_post`, `fence_panel`, `fence_tall`, `boombox`, `awning` |

A variant:

| Field | |
|---|---|
| `variant` | its number |
| `shape` | a fingerprint of its geometry (slots, vertex counts, bounds). Variants with the same fingerprint differ only in the small graphics drawn on them (a sedan's number plate) |
| `triangles` | of the web model |
| `materialSlots[]` | material slots of the web model: catalogue material names, `@paint` (the body colour), `@glass`, `@decal`, `@glow`, `@lit`, `@vc` (vertex-coloured), `#rig` |
| `bounds` | the model's own box in its local frame, overhangs included (a lamp's arm, a van's open doors, the reel case's light shaft) |
| `colliders[]` | `surface`, `flags`, `web {min, max}`, `ue {min, max, center, extent}` in the prop's local frame at yaw 0. Colliders flatter than 0.2 m with a top under 0.3 m are walked over (the level does not register them) |
| `lights[]` | lamp hints: `kind`, `color {hex, linear}`, `intensity`, `range {web, ue}`, `web {pos, dir}`, `ue {pos, dir}` (local). Placed, they are entries of `atmos.json` `lamps.list` |
| `anchors` | named attachment points `{web {pos, dir}, ue {pos, dir}}`: `steam`, `propane` (food cart), `smolder` (burned car), `exhaust`, `rearDoor` (IPX truck), `spray` (open hydrant), `jet` (explosives), `boombox`, `beacon`, `reel` (reel case) |
| `movingParts[]` | names of the parts that move: the truck's `doorL`, `doorR`, `hazards`, `vaultLight`; the case's `lid`, `bar`, `reel`, `beacon`, `shaft`, `pool`, `leds`; an explosive's `body`, `flame`, `wreck` |

Types with more than one shape: `sedan` 4; `jersey_barrier`, `trash_bags`, `tree`, `sign_post`, `milk_crates` 3;
`suv`, `pickup`, `box_truck`, `dumpster`, `mailbox`, `phone_booth`, `street_lamp`, `planter`, `pallet_stack`,
`crate_wood`, `cardboard_boxes`, `mattress`, `tire_stack`, `oil_drum`, `sandbags`, `car_lift`, `shelf_rack` 2.

### 7.2 The prop frame, and `front`

A prop's origin is on the ground at the centre of its footprint. Its catalogue **length runs along its own +X**, its
height is up, its width along web +Z. A prop's Unreal mesh is expected to keep that frame:

```
mesh +X = the catalogue length axis        mesh +Y (Unreal) = web local +Z = −Y in Blender        mesh +Z = up
```

`ue.yaw` of an instance is the yaw of that frame. Where the model's *front* is within the frame depends on the type
(`docs/CONTRACT.md` 6.2): vehicles and the hoop point their nose at +X; everything else with a front (benches, booths,
shelters, machines, racks, lamps, the billboard, the bleachers, wall pieces) faces web +Z, which is Unreal +Y and
Blender −Y. `catalogue.types[name].front` says which.

If an asset is authored with its front on +X regardless (the art pipeline's rule for props), use **`ue.frontYaw`**
instead of `ue.yaw`: it is the yaw of the direction the front looks along (`web.front`). For vehicles the two are the
same; for a bench they differ by 90°. A mesh authored that way also has its length along Y: swap `size.ue.X` and `Y`.

### 7.3 `instances.list` (329)

| Field | |
|---|---|
| `index` | position in the list. 0 … 307 are the level's props in the order it placed them; 308 … 328 the explosives |
| `name` | catalogue type |
| `variant` | the named variant the level asked for (`"vulture"` on one van), else null |
| `shapeVariant` | which of the type's `variants` it is (`seed mod variants.length`) |
| `seed`, `seedAuthored` | the seed it was built from; true when the level gave it, false when the factory drew it from the world seed |
| `options` | the build options that shape it (`variant`, `open`, …); empty for most |
| `paint` | its body colour `"#rrggbb"`, or null. Vehicles are painted from the level's own chart of nine colours |
| `domeLight` | a parked car's interior light is on (night only); null for other props |
| `zone`, `place`, `interior` | where it stands |
| `dynamic` | kept as an object of its own in the web game |
| `placedBy` | `level` or `explosives` |
| `role` | `{kind: "dressing"}`, `{kind: "objective", id}` (the three reel cases), `{kind: "extraction"}` (the IPX truck), `{kind: "explosive", explosive, type}` |
| `collides` | has colliders in the level (false for rooftop clutter, wall mounts and non-colliding types) |
| `colliders[]` | indices into `level.json` `colliders.boxes` |
| `lamps[]` | indices into `atmos.json` `lamps.list` |
| `web` | `pos`, `rotationY`, `forward` (local +X in the world), `front`, `scale` (always 1) |
| `ue` | `pos`, `yaw`, `frontYaw`, `scale` |

No prop of the block is tilted or scaled (the exporter stops if one is): position and yaw are the whole transform.
`pos.y` is the height it stands at: 0 on the roadway, 0.15 on a sidewalk, higher on roofs, the mezzanine (2.8), the
shed deck (2.95) or a lift (a sedan at 1.95). `instances.byName` counts them. Rebuild the same prop in the web game with
`G.props.build(name, {...options, color, seed})`.

Roles: 304 dressing, 3 objective, 1 extraction, 21 explosive. Gameplay actors (reel cases, the truck, explosives) are
listed here for their mesh and transform and in `level.json` for their rules; place each once.

---------------------------------------------------------------------------------------------------

## 8. `atmos.json`

### 8.1 `rigs.day`, `rigs.night`

Read from the scene after `G.atmos.setTime(name)`. Day is the default (`meta.default`).

| Key | Fields |
|---|---|
| `key` | the one shadow-casting directional light: `role`, `color {hex, linear}`, `intensity`, `castsShadow`, `elevation` (degrees above the horizon); `web {direction, toLight}`; `ue {direction, toLight, rotator}`; `shadow {radius, normalBias, biasMetres}` (web shadow-map settings). By day it is the sun (5.0, `#ffe6c6`, 52° up, travelling east and a little north). By night it is a steep warm stand-in for the street lights (2.6, `#ffb873`, 64° up), not the moon |
| `ambient` | a hemisphere light: `sky {hex, linear}`, `ground {hex, linear}`, `intensity` (day 1.0, night 1.7) |
| `fog` | `type` `FogExp2`, `color {hex, linear}`, `density` (day 0.0032, night 0.006), `rule`, `opacityAt[] {web, ue, opacity}` for 10 / 25 / 50 / 92 / 150 / 300 m. opacity = 1 − exp(−(density · metres)²). Past the bounds the haze thickens and is tinted by direction (`sky.*.fogTint`, `config.json` `look.fog`) |
| `grade` | `G.render.look`: `toneMapping` (`aces`), `exposure`, `bloomStrength`, `bloomRadius`, `bloomThreshold`, `bloomKnee`, `vignette`, `grain`, `aberration`, `saturation` |
| `exposure` | `toneMapping`, `exposure` (day 1.1, night 1.4), `multiplier` (`G.render.exposure`, 1) |
| `bloom` | `strength`, `radius`, `threshold` (scene-referred, before exposure: day 2.4, night 1.05), `knee` |
| `environment` | the image-based light: `intensity`, stand-in radiances for the facades and the street, by day `skyGain`, by night `lampGain`, `maxLamps` |
| `interior` | what changes inside the shop: `exposure` (× 1.35 by day, × 0.86 by night), `ambient`, `ambientSky`, `fog` |
| `lampGain` | strength of the real lamp lights per kind. By day only `work` (1) and `neon` (0.35) are lit |
| `lampField` | whether the ground pools, cones and fixture glows of the lamps are drawn (night only) |
| `city`, `train`, `life` | the far city sheet, the train's lit windows and their stripes on the street, steam / spray / moths / pigeons |

### 8.2 `sky`

`G.config.look` as the two sky domes read it. `sky.day`: `zenith`, `horizon`, `horizonPower`, `sun {radiance, radius,
aureole, aureoleTight}`, `clouds {amount, coverage, softness, scale, drift, lit, shade}`, `sunDisc {web {toSun},
ue {toSun}}`, `fogTint {west, east}`. `sky.night`: `zenith` / `horizon` / `glow` (sRGB), `zenithRadiance`,
`horizonRadiance`, `glowWest`, `glowEast`, `glowHeight`, `clouds`, `stars`, `moon {direction, radius, radiance, halo}`,
`moonDisc {web {toMoon}, ue {toMoon}, elevation}` (17° up in the east-south-east: decoration, the night key does not
come from it), `fogTint`. Also `clearColor` and `farCity` (the skyline beyond the bounds). Radiance triples are linear
and scene-referred: by night 1 is where bloom starts.

### 8.3 `lamps`

`lamps.kinds`: `G.config.look.lamps` (how each kind is drawn and how strong its real light is: `ref`, `realGain`,
`spot {angle, penumbra}`, `pool`, `glow`, `cone`, `env`, the `rig` rule for sharing out the few real lights).
`lamps.byKind`: el 15, window 13, neon 19, street 22, work 17, flood 4.

`lamps.list[90]`: every light fixture of the block, in the order of `G.level.lamps`.

| Field | |
|---|---|
| `index`, `kind` | `street`, `el` (hung under the deck, and the station's tubes), `work`, `flood`, `neon` (the light of a sign), `window` (the light of a lit shop) |
| `color {hex, linear}`, `intensity`, `range {web, ue}` | as the level gives them |
| `priority` | how much the lamp deserves one of the few real lights (the shop's four work lights 10, the floods 9, …) |
| `zone`, `place`, `interior` | |
| `prop` | the placed prop it belongs to (`props.json` instance), or null for a fixture the level built itself |
| `aimSource` | `dir` (the fixture has its own direction), `wall` (a sign or window: out from the wall behind it and 35° down), `down` |
| `overDeck {web, ue}` | set when the lamp hangs over a floor of the level (a platform, the mezzanine, the shed deck): its light falls on that floor |
| `web {pos, aim, wall}`, `ue {pos, aim, rotator, wall}` | where it is, how it shines, the outward normal of the wall behind a sign or window |

In the web game a lamp is a pool of light on the ground, a glow at the fixture and, for the few lamps nearest the point
the camera looks at, a real spot light (4 to 12 by quality). In Unreal every lamp can simply be a light.

### 8.4 `signLights`, `windowLights`

| Key | Fields |
|---|---|
| `signLights.lamps[19]` | indices of the `neon` lamps |
| `signLights.signs[17]` | every lit sign quad: `placement` (index into `level.json` `signage.placements`), `text`, `sub`, `style`, `fg`, `bg`, `glow`, `zone`, `place`, and the face in both spaces |
| `windowLights.lamps[13]` | indices of the `window` lamps |
| `windowLights.materials` | the glow of `glass_lit_warm`, `glass_lit_cool`, `glass_skylight` (`emissive {hex, linear}`, `emissiveIntensity`); `facade.warm[]` / `curtains[]`: the tones the facade painter draws lit windows and curtains with |
| `windowLights.glass[57]` | the lit panes: `pane` (index into `level.json` `glazing.panes`), `material`, `zone`, `place`, `interior`, and the face |
| `windowLights.facadeWindows[79]` | the lit facade windows: `face` (index into `level.json` `facades.faces`), `grid`, `state` (`warm` \| `tv`), `zone`, `place`, `web {pos, normal}`, `ue {pos, normal}` |

All of it glows at night only. By day signs are lit signage without glow and every window is dark reflective glass.

---------------------------------------------------------------------------------------------------

## 9. Where each value comes from

Read directly from the booted game: `G.config`, `G.settings`, `G.level` (bounds, zones, start, objectives, extraction,
spawns, cover points, explosives, interior, vantage, El, steam, puddles, fly-through, lamps, and its queries `zoneAt`,
`zoneName`, `floorAt`, `groundSurfaceAt`, `interiorAt`), `G.physics.boxes` and `G.physics.nav`, `G.explosives.items`,
`G.enemies.debug()`, `G.atmos` (`sun`, `setTime`, `train`, `stats`), `G.render.look`, `G.scene.fog`, the scene's
hemisphere light, the merged meshes under `G.level.root`, the page's DOM.

Not reachable from `window.__G`, and the path taken instead:

| What | Path |
|---|---|
| The list of placed props | The level's building kit keeps it in a closure and merges the static props away. `lib/hooks.cjs` wraps `G.props.build` before the level is created and remembers every call, the prop it returned and the seed the factory drew; the transform is read from the returned object after the level has placed it. The wrapper only listens: it calls straight through |
| Whole oriented colliders | `G.physics.addOriented` slices a turned box before anyone sees it. The hooks wrap it and keep the call's centre, size and yaw |
| Who added a collider | the same hooks note which module was being created (`level` or `explosives`) |
| Sign texts and their places | the paint is on an atlas page by the time the level stands. The hooks wrap `G.mats.sign / poster / graffiti / decal` and keep the arguments and the atlas rectangle each call returned; a quad of that page's material whose texture coordinates are that rectangle is that painting (all 347 quads matched, every painting placed) |
| Window panes, facade faces | read from the merged level meshes: every four-cornered face of a glass or facade material |
| Facade windows | the hooks keep the `G.mats.facade` specs; the windows are laid out with the painter's own pure layout module, `src/mats/layout.js`, imported in Node |
| Prop variants, palettes, colliders per shape | probed: `G.props.build(name, {seed})` for seeds 0 … 47 (0 … 255 for painted types) in the booted page; shapes are told apart by the geometry objects the factory shares between instances |
| Function source text and parameter names | `src/config/*.js` imported in Node (a production build minifies them). The exporter calls each function in the page and in Node with the same inputs and stops if they differ |
| Interface labels | `src/ui/copy.js` imported in Node (the HUD and menus import it directly) |
| Explosive rule constants | `POP_FUSE`, `PLAYER_SCALE`, `ENEMY_ROUND`, `SHAKE_REACH`, `ALERT_RADIUS` read from the text of `src/explosives.js`; its three exported formulas imported in Node. The per-type rows come from the page |
| Physics and nav constants | read from the text of `src/physics.js`. Proof that they are right: the nav grid rebuilt from the exported colliders with them equals the game's grid cell for cell |
| The layout table, building footprints, El constants | `src/level/layout.js` imported in Node; the booted level is held against it (bounds, zones, sidewalk slabs, building colliders, column positions) |
| The train's path and timing | `trainTimeline()` of `src/atmos/plan.js` run in Node with the game's own bounds, speed, length and run-up; the durations must equal what the running game announced for its first two trains |
| Prop families | which file under `src/props` contains `R.add('<name>'` |
| Facade window tones | `WARM` and `CURTAINS` read from the text of `src/mats/facade.js` |

Derived by the exporter (not game data, and marked so in the files):

| What | How |
|---|---|
| **Spawn point facing** | The game keeps none: a new enemy gets a random yaw (`src/enemies/goon.js`, `buzzard.js`). A ground point looks toward the mean of the walkable nav cells it can reach in a straight line within 6 m, i.e. out of its pocket (`facingSource: "opening"`); an air point toward the middle of the block (`"centre"`) |
| **Lamp aim, wall, overDeck** | re-derived with the rule of `src/atmos/lights.js` (`collectLamps`, `assign`). Checked against the game's own spot lights: with the camera's point of interest moved onto each lamp in turn, 56 of the 90 lamps held a real light and all 56 pointed exactly as exported |
| `place`, `interior`, `zone` of props, lamps, signs | the level's own `zoneName`, `interiorAt`, `zoneAt` at the record's position |
| `blocks.nav` | the nav rule applied to the collider (verified by the grid) |
| Unreal values, `forward`, `front`, `corner`, `elevation`, `opacityAt`, counts | arithmetic on the values next to them |

---------------------------------------------------------------------------------------------------

## 10. What is checked

The exporter stops without writing when: the page logs an error or falls back to a stub; a collider was added behind
the hooks' back; the rebuilt nav grid differs from the game's; a placed prop is tilted, scaled, a fallback box, or not
the catalogue variant its seed says; a painting hangs nowhere or a sign quad matches no painting; an explosive has no
item; a lamp shines another way in the game than the export says; a function answers differently in the page and in
`src/config`; the train's announced durations differ from the plan, or its first two passes are not east then west
within the configured interval.

`verify.cjs` then re-reads the files without a browser: 40 checks, about 52 000 comparisons.

| Check | Against |
|---|---|
| each file is in canonical form: pretty-printed, at most 4 decimals, no keys differing only by case | itself |
| `config.json` brand, catalog, enemies, flow, look, player, quality, weapons; settings defaults; enemies resolved per difficulty; explosives | `src/config/*.js`, `src/core/settings.js`, `src/explosives.js` imported in Node, value by value; every function sample recomputed |
| the difficulty table (13 rows × 3 difficulties), melee, weak point, pool caps, pursuit mix, holdout formulas, score, resupply, explosive numbers, the Buzzard's crash, magazines | the tables and sentences of `docs/DESIGN.md` 3.1, read from the document |
| radio lines and hold times, rating ladder, objective lines, names, the day / night copy of 8.1, storefront names | `docs/DESIGN.md` 2 and 8.1 |
| `text.json` text, brand, input, interface, page, lettering | `src/config/text.js`, `brand.js`, `player.js`, `src/ui/copy.js`, `src/page.html`, `level.json` |
| **every web / ue pair of all five files** (9 600 pairs): positions, directions, boxes, rectangles, lengths, yaws, rotators | its own arithmetic (not `lib/convert.cjs`) |
| **five landmarks**: the start, the three reels, the IPX truck | within 4 m of the coordinates `docs/DESIGN.md` 4 gives; converted exactly; the start faces east, the truck stands nose east; the same objects found in `props.json` |
| **counts**: 29 ground + 17 air spawn points, none in the west zone; 100 cover points; 21 explosives; three reels | "about 28 ground + 16 air", "50+", "about 18–22" of `docs/DESIGN.md` 4 |
| bounds, zones, ground regions, sidewalks, layout table | `src/level/layout.js` |
| start, reels, truck, extraction, spawn points, cover points, explosives, fly-through | `src/level/data.js` (moved points within 2.5 m); no explosive within 7 m of the start or 2.2 m of a reel |
| colliders: sane, referenced both ways; the nav grid rebuilt from the file's colliders; every ground spawn and cover point on a free cell | itself, `src/physics.js` |
| the El, the train's path, timing and schedule, the observed passes | `src/level/layout.js`, `src/config/look.js`, `src/atmos/plan.js`, `docs/DESIGN.md` |
| buildings, the interior box | `src/level/layout.js`, `docs/DESIGN.md` 4 (the shop's footprint and eave) |
| signage, glazing; every facade window laid out again | itself, `src/mats/layout.js` |
| the catalogue: sizes, surfaces, flags, families, colliders inside the catalogue box, cover heights | `src/config/catalog.js`, `src/props/*.js`, `docs/DESIGN.md` 4 |
| instances: roles, references; **every placed prop's colliders and lamps recomputed from the catalogue and its transform** (322 boxes, 29 lamps) | `level.json`, `atmos.json` |
| rigs, sky, lamp kinds | `src/config/look.js` |
| lamps, lit signs, lit panes, lit facade windows | `level.json`; the shop's four work lights and the court's two floods of `docs/DESIGN.md` 4 |
| reference pictures: all there, 1280 × 720, under 12 MB together | `docs/unreal/reference` |

---------------------------------------------------------------------------------------------------

## 11. What is not exported

- **Geometry.** No mesh leaves the web game: not the block's walls, storefronts, cornices, awnings, fire escapes and
  steel, not the props, the guns, the arms, the Goon or the Buzzard. The art is authored anew. What is exported is where
  things are and how big: colliders, the layout table, building footprints and heights, wall faces with their window
  grids, panes, the catalogue boxes and colliders of every prop, the model bounds of every prop shape.
- **Textures and materials.** Every texture of the web game is painted in code at load. Only the catalogue's base
  values (`config.json` `catalog.MATERIALS`) and the sign / poster / graffiti / decal *specs* are exported. Poster
  artwork has no text table. The small graphics on props (number plates, labels) are not listed.
- **Sound and music.** All of it is synthesised by `src/audio/*`; there are no tables to export. See the UI / audio spec.
- **Behaviour.** Code is not data: enemy AI, weapon handling and animation, effects recipes, the HUD's layout and CSS
  are described in the other specs of this folder. Only the tables they read are here.
- **Spawn facings** do not exist in the game (section 9 says how the exported ones are derived).
- **The atmosphere's own scenery**: the far city and skyline, the 40 lamps it continues past the bounds, the two tired
  lamps that flicker (chosen by the world seed, not exposed), steam puffs, moths, loose paper, pigeons, the train's
  car model and textures, the sky domes' shaders, the environment maps, the fitted shadow frustum. Their parameters
  are in `config.json` `look`.
- **Which lamps hold a real light** at a given moment: it follows the camera. The rule is in `look.lamps.rig`.
- **Per-window dressing** of the facades beyond lit state and window units (blinds, curtains).
- **Strings that are not in a table**: a handful of labels built inline by the HUD and menu code. `text.json` has every
  table (`src/config/text.js`, `src/ui/copy.js`, the glyph and hint tables, the page).
- **The fly-through curve**: only its 14 control points; the interpolation is `src/game/titlecam.js`.

---------------------------------------------------------------------------------------------------

## 12. Reference pictures

`docs/unreal/reference/`: 1280 × 720 PNGs of the web game as it is, for before / after comparison and for the artists.

```
node tools/shot.cjs dist/index.html --size 1280x720 --timeout 1500 \
     --params "q=high&dynres=0&god=1&noaudio=1&seed=1994" --scenario tools/ue-export/reference.cjs
```

The scenario runs in the existing harness in step mode with a fixed seed, so the pictures repeat. Quality `high`
(internal scale 1, 4× MSAA, 4096 shadow map). It takes about 8 minutes in software WebGL. `REF_ONLY=name,name` shoots a
subset, `REF_OUT=<dir>` writes elsewhere.

| Picture | What | Camera (web metres: position → look-at, field of view) |
|---|---|---|
| `title.png` | the title screen, 5 s into its fly-through | the game's own |
| `hud-start.png` | the HUD in play at the start pose, CHOPPER in hand | the player's view |
| `day-avenue-east.png` | the avenue under the El at eye level, looking east | (−27.5, 1.68, 0.4) → (20, 2.3, 0.2), 62° |
| `day-chop-shop.png` | inside V&R AUTO BODY: the lifts, reel 2, the mezzanine office | (−1.6, 1.68, −13.4) → (−15, 2.1, −24.5), 68° |
| `day-alley.png` | the alley from its mouth to the gate | (8.6, 1.68, −9.2) → (8.3, 2.6, −30), 62° |
| `day-vacant-lot-mural.png` | the vacant lot and the mural on the pawn shop's wall | (−5.4, 1.68, 20.5) → (−16, 3.6, 18.5), 66° |
| `day-cage.png` | The Cage, reel 3 at centre court | (27.2, 1.68, −13.8) → (38.5, 1.6, −25.5), 66° |
| `day-parking-lot-ipx-truck.png` | the parking lot with the IPX truck | (28.5, 1.68, 19.5) → (41.3, 1.7, 29.7), 62° |
| `night-avenue-east.png`, `night-parking-lot-ipx-truck.png` | the same two cameras by night | as by day |
| `enemy-goon.png` | a Goon in the sun, aiming, three-quarter view | (−10.5, 1.4, −6.1) → (−8.6, 1.0, −8.8), 44° |
| `enemy-buzzard.png` | a Buzzard hovering at 2.2 m | (−10.2, 2.05, −6.4) → (−8.6, 2.2, −8.8), 40° |
| `viewmodel-chopper.png`, `viewmodel-nine.png` | the first-person view with each gun, HUD hidden, at the start pose | the player's view |
| `viewmodel-chopper-side.png`, `viewmodel-nine-side.png` | each gun held up side-on (the game's inspect pose) | the player's view |
| `plan-top-down.png` | the whole block from above, north up | (0, 400, 0.4) → (0, 0, 0), 10.6°, haze off |

Eye level is 1.68 m. The fixed cameras hide the interface and the gun; the block is emptied of enemies for the scenery;
the two Vultures are passive showcase units posed on the shop's driveway apron. The plan is shot from 400 m through a
long lens (the frame is 74 m tall, 131 m wide: the 92 × 68 m block with the neighbours around it) with the haze
switched off for that one frame, because 400 m of it would hide the street.

To fit the directory into 12 MB each picture is rewritten with its colour channels rounded to 40 evenly spaced levels
(`tools/ue-export/lib/png.cjs`, no dependency): the largest change is 3 parts in 255 and the files are half the size.
`REF_LEVELS=256` keeps the frames as the browser wrote them.

---------------------------------------------------------------------------------------------------

## 13. Notes for the Unreal side

- The files are plain JSON under `Content/Data`. They are not assets: read them with `FFileHelper::LoadFileToString`
  from `FPaths::ProjectContentDir() / TEXT("Data")`, and add `Data` to the directories staged as non-asset files when
  packaging, or convert them to data assets at edit time.
- Read `ue` blocks only. Everything in `config.json` is web units: convert lengths and speeds once, where the table is
  loaded (`× 100`), angles from radians where they are angles (`melee.cone`, `ai.fov`, spreads, look limits).
- Level collision: use the 316 colliders whose `owner.kind` is `level` as blocking volumes for the block-out (or as a
  check on the real meshes' collision). Give `flags.playerOnly` ones a profile that blocks pawns and ignores weapon
  traces, `flags.bulletOnly` ones the reverse. Props bring their own collision: the catalogue colliders in the prop's
  frame, or the oriented boxes.
- Props: one actor or instance per `instances.list` entry with `role.kind == "dressing"`; the reel cases, the truck and
  the explosives are gameplay actors placed from `level.json` (their instance entries give the mesh, variant and paint).
- The `shapeVariant` and `paint` of an instance are what made the web block look the way it does. An Unreal variant set
  may be smaller; keep the mapping stable (`shapeVariant mod yourCount`).
- Lighting: `rigs.day` is the look to match. Intensities are three.js values tuned against the exposure of the same
  rig: keep the ratios, re-balance the absolute level against Unreal's exposure.
