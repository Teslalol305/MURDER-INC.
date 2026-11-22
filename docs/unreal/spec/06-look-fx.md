# 06 — Look and FX: surfaces, signage, lighting, atmosphere, post, effects

Port spec for the Unreal Engine 5 rebuild of MURDER INC. The web game is the ground truth. Everything below was read
from the source files listed in 2.1. Values marked **(measured)** are not typed anywhere in the source: they were
obtained by booting the production build headless (`dist/index.html`, quality `high`, seed 1994) and reading the live
objects back (`level.lamps`, the lights, the fog, `atmos.stats()`, `mats.stats()`, every `mats.sign / poster / graffiti /
decal` call), or by running the pure modules in node (`src/mats/layout.js`). Values marked **(derived)** are arithmetic
on source constants shown next to them.

How to read this document:

- Web units are metres and seconds. +Y is up, north is −Z, east is +X. Every position and vector is web space unless
  a column says Unreal. Unreal (X, Y, Z) = (x, z, y) × 100 cm; Blender (x, y, z) = (x, −z, y).
- Colours: `#rrggbb` is sRGB (an albedo, a light colour, a paint). `[r, g, b]` is linear, scene-referred radiance: what
  the HDR buffer holds before exposure and tone mapping; 1 is where the night bloom starts, 0.02 is a dark wall at
  night (`src/config/look.js:7`).
- Light numbers are three.js r160 physical-light numbers, not SI. A directional or hemisphere `intensity` E is an
  irradiance: a matte surface of albedo ρ returns the radiance ρ · E / π. A point or spot `intensity` I behaves like
  candela: E = I / d². This file calls them "game lux" and "game cd"; 4.4 maps both to SI.
- `rand(a, b)` is a uniform draw. `k` in the effect tables is the particle density at the spot: `quality.fx` (0.4 … 1),
  halved beyond 55 m from the camera, zero beyond 150 m (`src/fx.js:39`, `src/fx.js:173`).
- Sign, poster and decal positions are the centre of the quad. Text strings are verbatim; where a string has two
  spaces either side of a `·` it is written that way in the source.

---------------------------------------------------------------------------------------------------

## 1. Overview

This subsystem is everything the player sees that is not a shape: what every surface is made of, what is written on the
block, how it is lit, what the air and the sky do, what moves when nobody is fighting, and what a shot, a hit and a
blast look like. The block is one stretch of Jamaica Ave in Hollis, Queens, under an elevated train line, on a hot,
clear afternoon at about 4:15 PM (the default) or at 2:14 AM (the alternate, sodium and neon). By day a high sun in
the west-south-west rakes through the ties of the El and stripes the avenue with hard light and shadow; the street is
dry except where an open hydrant has hosed it down; shop signs are simply signs and windows are glass. By night the
whole street is wet, a field of sodium lamps, neon and lit windows carries the picture, and a train crossing overhead
strobes the roadway. Around the playable block a ring of far buildings and two skyline rings dissolve into haze.
Pigeons, steam, blown paper and a train every 40 to 70 seconds keep the picture alive. On top of that sits the
feedback layer the shooter depends on: muzzle flashes, tracers (warm white-gold for the player, red for the Vultures),
brass, surface-specific impacts with bullet holes, dry dust-and-lint puffs on bodies (no blood, by design), propane
jets, explosions with smoke columns and scorch marks, and a post chain that reddens the screen edge on a hit, drains
colour at low health and flashes on a close blast. The names on the block are invented, the only real brand is IPX
(wordmark `IPX`, address `IPX.EXCHANGE`, no slogan), and the star is Ja Rule, whose name is on the mural and on the
bus-shelter one-sheet.

---------------------------------------------------------------------------------------------------

## 2. Facts

### 2.1 Source map

| File | Lines | What it holds |
|---|---|---|
| `src/config/look.js` | 377 | Every look constant: grade, post feedback, both skies, fog, key light, ambient, lamp kinds, far city, train, street life, per-quality detail, the `times.day` / `times.night` tables |
| `src/config/brand.js` | 57 | Names, IPX marks, colour tokens, font stacks |
| `src/config/catalog.js` | 144 | `MATERIALS`: catalogue name → mean colour, roughness, metalness, glow |
| `src/config/quality.js` | 78 | Quality presets, auto-detection, dynamic-resolution tuning |
| `src/render.js` | 1032 | Renderer, both cameras, the post chain (bloom, grade, output), pooled lights, quality switching, dynamic resolution |
| `src/mats.js` | 843 | Material factory: `LOOKS` (how each catalogue name is dressed), atlas pages, signs, facades, posters, graffiti, decals, day / night switch, neon flicker |
| `src/mats/surfaces.js` | 1279 | The 23 painted surface sets (albedo, height → normal, roughness / metalness) at real scale |
| `src/mats/shader.js` | 287 | World-space layers on ground and masonry: tone variation, the wet street, wall grime, the facade window layer; chain-link cut-out |
| `src/mats/signs.js` | 490 | Seven sign styles and the IPX wordmark |
| `src/mats/paper.js` | 619 | Posters (5 kinds) and graffiti (3 hands + stencilled IPX) |
| `src/mats/decals.js` | 305 | Ground and wall decals, road paint |
| `src/mats/facade.js`, `layout.js` | 295, 137 | The window layer of a building wall: layout rules and painter |
| `src/mats/type.js`, `atlas.js`, `canvas.js`, `noise.js` | 143, 245, 350, 273 | Lettering, atlas packing, canvas helpers, tileable noise |
| `src/atmos.js` | 429 | Atmosphere assembly, `setTime`, interior blend, environment capture |
| `src/atmos/daysky.js`, `sky.js` | 167, 286 | Day and night sky domes; the image-based-light capture |
| `src/atmos/fog.js` | 142 | The haze and its replacement fog shader |
| `src/atmos/lights.js`, `lampfield.js` | 321, 561 | Key light, ambient, the real lamp-light rig; pools, cones and glows for every lamp |
| `src/atmos/farcity.js`, `textures.js`, `plan.js` | 632, 436, 400 | Far blocks, skyline rings, traffic, plane, switching windows; their painted sheets; the pure planning logic |
| `src/atmos/train.js` | 430 | The El train |
| `src/atmos/life.js` | 642 | Steam, moths, loose paper, hydrant spray, pigeons |
| `src/fx.js` | 687 | Effects API, pools, budgets, automatic effects, screen flash |
| `src/fx/recipes.js`, `emitters.js` | 991, 607 | What every effect is made of; the six continuous emitters |
| `src/fx/sim.js`, `particles.js`, `atlas.js` | 377, 283, 375 | Particle simulation, the two billboard pools, the sprite and decal sheets |
| `src/fx/tracers.js`, `bits.js`, `decals.js`, `shared.js` | 215, 408, 215, 149 | Tracers; brass and debris bodies; the decal ring buffer; shared uniforms |
| `src/stubs/mats.js`, `atmos.js`, `fx.js` | 258, 106, 99 | Stand-ins with the same API (flat colours, no lamps, line tracers). Not to be ported: see 3.16 |

Read as well, because they decide what is written where: `src/level/buildings.js`, `street.js`, `yards.js`, `shop.js`,
`el.js`, `ground.js` (sign, poster, graffiti, decal and lamp placement), `src/props/atlas.js`, `materials.js`, `lot.js`,
`vehicles.js`, `street.js` (prop graphics, plates, the billboard), `src/explosives.js`, `src/weapon/logic.js`,
`viewmodel.js`, `material.js`, `src/enemies/goon.js`, `buzzard.js` (who calls which effect), `src/audio/ambience.js`
(train sound cues).

### 2.2 Brand tokens and world palette

Names (`src/config/brand.js:8`): title `MURDER INC.`, sentence-case `Murder Inc.`, presenter `IPX PRESENTS`, star line
`STARRING JA RULE`, wordmark `IPX`, address `IPX.EXCHANGE`. "The only IPX marks allowed in the world and the UI. No
slogan." (`src/config/brand.js:14`).

| Token (`brand.colors`, `src/config/brand.js:24`) | Hex | Used for |
|---|---|---|
| `bg` | `#07080a` | Page behind the canvas, boot screen |
| `plate` | `#0f1114` | Enamel sign plates: cards, HUD blocks, prop tags |
| `plateEdge` | `#2a2e35` | Hairlines, plate borders |
| `ink` | `#f4f2ec` | Primary type, the thin rule above it, the default IPX mark colour |
| `inkDim` / `inkFaint` | `#b4b2ab` / `#8b8983` | Secondary / tertiary type |
| `gold` | `#f6c21a` | Accent: taxi and gold-record yellow; default bullet colour on plates |
| `red` | `#e2222b` | Danger, signal red |
| `oxblood` | `#6b1218` | Vulture crew colour |
| `cyan` | `#39d0e0` | Neon secondary, sparingly |
| `line1` / `line2` / `line3` / `lineIpx` | `#f2762e` / `#1fa463` / `#3b82f0` / `#f6c21a` | Route bullets of reel 1, 2, 3 and the IPX truck |

Fonts (`src/config/brand.js:53`): display `Anton` (tall condensed; fallbacks Impact, Haettenschweiler, Arial Narrow),
UI `Archivo` (grotesque; weights 500, 700, 800, 800 italic are requested: `src/mats/type.js:16`), mono system. Sign
painting waits at most 1.5 s for the web fonts (`src/mats/type.js:15`); the headless measurement ran on the fallbacks.

| World colour (`look.palette`, `src/config/look.js:119`) | Hex | Used for |
|---|---|---|
| `tracerPlayer` | `#ffe2a8` | Player tracers (warm white-gold) |
| `tracerEnemy` | `#ff3a22` | Goon tracers, Buzzard bolts, Buzzard muzzle light |
| `muzzle` | `#ffc880` | Default pooled flash colour |
| `beacon` | `#f6c21a` | Master-reel beacon |
| `hazard` | `#ff8a1a` | Hazard lamps (IPX truck, barricades) |
| `sodium` | `#ffb45e` | Street and El lamps, virtual lamps beyond the bounds |
| `neonPink` / `neonRed` / `neonCyan` / `neonGreen` | `#ff3d9a` / `#ff3030` / `#35e0ff` / `#55ff8a` | Neon tubes |
| `taxi` | `#f2c21a` | Cab paint |
| `buzzardEye` | `#ff2a1a` | Buzzard eye light |

### 2.3 The IPX wordmark

One routine draws the mark everywhere in the world (`drawIPX`, `src/mats/signs.js:50`); a sign whose text is exactly
`IPX` is drawn with it (`src/mats/signs.js:87`). Construction for a mark of height `h`:

| Part | Rule |
|---|---|
| Lettering | `IPX`, Archivo ExtraBold Italic (800 italic), font size 0.58 h, letter spacing 0.05 em, one colour |
| Lozenge | A stadium outline (two half circles joined by straight edges), outer height h, stroke 0.065 h (never under 1 px), no fill |
| Width | text width + 0.86 h (about 1.9 h with Archivo: **derived** estimate, measure it in the real font) |
| Placement | Lettering centred in the lozenge, shifted 0.02 h to the left |
| Colour | `ink #f4f2ec` unless the caller passes another (gold on black, ink on gold, black on cream, cream on oxblood are all used) |

The DOM version is the same mark in CSS: italic 800, letter spacing 0.05 em, border 0.1 em, fully round, padding
0.1 em 0.6 em 0.08 em 0.48 em (`src/base.css:115`). The real IPX logo replaces both in one place each.

### 2.4 Surface catalogue

Every surface in the block is one of 49 catalogue names (`src/config/catalog.js:6`). The hex is the **mean albedo** the
surface ends up with: the factory divides the asked colour by the average of the painted texture
(`src/mats.js:306`). Roughness is likewise the mean: a painted roughness map is scaled so its reference level lands on
the catalogue value (`src/mats.js:414`). "Day" is the albedo the untinted material switches to by day
(`LOOKS.day`, `src/mats.js:70`); a dash means the same colour day and night. "World" is
[tone variation, wetness, wall grime], see 2.6.

| Name | Depicts | Night | Day | Rough | Metal | Set · skin, tile (m) | World |
|---|---|---|---|---|---|---|---|
| `asphalt` | Street asphalt, pale aggregate | `#1b1c1f` | `#56575a` | 0.82 | 0 | asphalt, 4 × 4 | 0.2, 1, 0 |
| `asphalt_wet` | Standing water on asphalt (level-placed blobs) | `#121316` | `#56575a` | 0.28 | 0 | asphalt, normal × 0.45 | 0.2, 0, 0 + soak |
| `sidewalk` | Concrete sidewalk flags | `#6f6c66` | `#9a968e` | 0.9 | 0 | sidewalk, 4.5 × 4.5 | 0.16, 0.5, 0 |
| `curb` | Concrete kerb stone | `#85827a` | `#a4a097` | 0.85 | 0 | concrete, 2.4 | 0.12, 0.3, 0 |
| `court` | Acrylic court coating over asphalt | `#2f4f46` | – | 0.8 | 0 | asphalt · coat, normal × 0.5 | 0.14, 0.5, 0 |
| `dirt` | Packed earth of the vacant lot | `#3a3229` | `#625646` | 1.0 | 0 | dirt, 3 × 3 | 0.2, 0.7, 0 |
| `concrete` | Cast concrete | `#7b7a76` | `#8e8c87` | 0.9 | 0 | concrete, 2.4 | 0.18, 0, 0.5 |
| `concrete_dark` | Sealed dark concrete (shop floor, roofs) | `#44444a` | `#5e5e62` | 0.9 | 0 | concrete | 0.18, 0, 0.4 |
| `cinder` | Cinder block wall | `#8a8880` | – | 0.95 | 0 | cinder, 2.4 | 0.16, 0, 0.6 |
| `brick_red` / `brick_brown` / `brick_tan` | Brick, common bond | `#7a3327` / `#5a4032` / `#9a8262` | – | 0.9 | 0 | brick · red / brown / tan, 2.4 | 0.18, 0, 0.7 |
| `brick_painted` | Red brick under flaking pale paint | `#b9b4a6` | – | 0.85 | 0 | brick · painted | 0.16, 0, 0.8 |
| `stucco` | Lumpy pale render | `#a9a08c` | – | 0.95 | 0 | stucco, 2 × 2 | 0.16, 0, 0.8 |
| `tile_white` | White glazed wall tile | `#d9d6cc` | – | 0.35 | 0 | tile, 0.6 | – |
| `metal_dark` | Dark painted / blackened sheet steel | `#23262a` | – | 0.55 | 0.8 | metal, 1.5 | – |
| `metal_galv` | Galvanised steel (zinc spangle) | `#8d949a` | – | 0.5 | 0.85 | metal · galv | – |
| `steel_el` | Riveted plate under dark green paint (the El) | `#1f2a26` | – | 0.6 | 0.7 | steel_el, 0.6 × 2.4 | – |
| `steel_rust` | Steel left out for years | `#5b3a26` | – | 0.85 | 0.5 | rust, 1.5 | – |
| `roll_gate` | Roll-down security gate, 75 mm slats | `#6c7074` | – | 0.55 | 0.75 | roll_gate, 1.2 | – |
| `corrugated` | Corrugated sheet, 75 mm waves | `#7c8084` | – | 0.6 | 0.7 | corrugated, 1.2 | – |
| `chainlink` | Chain-link mesh (alpha-tested weave, always two-sided) | `#9aa0a4` | – | 0.6 | 0.5 (0.8 in the catalogue, capped: `src/mats.js:455`) | weave, 0.6 (8 diamonds) | – |
| `chrome` / `gold` | Chrome / polished gold | `#d8dde2` / `#e7b53a` | – | 0.12 / 0.25 | 1 | none | – |
| `car_paint` | Clear-coated body paint (vertex-tinted per car) | `#7a1d1d` | – | 0.32 | 0.55 | none (even gloss) | – |
| `paint_yellow` / `white` / `red` / `blue` / `green` / `black` | Enamel on metal or wood | `#f2c21a` / `#e6e4dc` / `#b3261e` / `#1f4f9a` / `#1f5a3a` / `#101113` | – | 0.5 / 0.6 / 0.5 / 0.5 / 0.55 / 0.45 | 0.1 / 0 / 0.1 / 0.1 / 0.1 / 0.2 | paint, 1.5 | – |
| `plastic_dark` / `plastic_orange` | Moulded plastic | `#18191b` / `#e8641b` | – | 0.6 | 0 | relief: pebble, 0.25 | – |
| `rubber` | Rubber | `#121212` | – | 0.95 | 0 | relief: pebble | – |
| `tire` | Tyre tread | `#0e0e0f` | – | 0.9 | 0 | tire, 0.24 | – |
| `trash_bag` | Wrinkled bin-bag plastic | `#0b0b0c` | – | 0.35 | 0 | wrinkle, 0.7 | – |
| `wood` | Weathered boards, 150 mm | `#6d5236` | – | 0.85 | 0 | wood, 1.2 | – |
| `plywood` | Plywood sheet 2.44 × 1.22 m | `#a98a5c` | – | 0.9 | 0 | plywood, 2.44 × 1.22 | – |
| `cardboard` | Corrugated cardboard, kraft liner | `#9a7b52` | – | 0.95 | 0 | cardboard, 1 | – |
| `fabric_awning` / `fabric` | Plain-weave canvas | `#7a1f24` / `#2b2d33` | – | 0.9 / 0.95 | 0 | fabric, 0.25 | – |
| `leaves` | Leaf mass seen from outside (two-sided) | `#1f3322` | – | 0.9 | 0 | leaves, 1.2 | – |
| `skin` | Skin (the player's forearms) | `#7a4a2e` | – | 0.6 | 0 | none | – |
| `glass_dark` | Dark window glass | `#0d1218` | – | 0.08 | 0.2 | gloss: smudge, 1.6 | – |
| `glass_store` | Shop glass, faint interior | `#1a2630` | – | 0.06 | 0.2 | smudge; glow `#3a4a50` × 0.25 (day × 0.05) | – |
| `glass_lit_warm` / `glass_lit_cool` | Lit shop or room glass | `#0d1218` | – | 0.08 | 0 | smudge; glow `#ffb45e` × 0.75 / `#9fd4ff` × 0.7 (day: 0) | – |
| `glass_car` / `glass_car_lit` | Car glass / with the dome light on | `#0a0d10` | – | 0.05 | 0.3 | smudge; lit glow `#ffc890` × 0.45 (day 0); reflections × 0.4 at night | – |
| `glass_skylight` | Shop skylight from below | `#0d1218` | – | 0.08 | 0.2 | smudge; glow `#314a78` × 0.55 at night, `#dfe8f2` × 0.99 by day | – |

Tint variants the level asks for (same set, other mean colour): asphalt patches `#121316` and `#232427`; court key
`#7a2e26`; hoarding plywood green `#23463c`, orange `#c4571a`, stand green `#2d5a3a`, `#6b5a43`; corrugated `#1c2224`,
`#2f4038`, `#24463a`, `#1a2b3a`; shop wall cinder `#8a8880` with a dado `#27414b`; creosoted tie wood `#2b221b`, walkway
plank `#4a3c2c`; scrim fabric `#1f3a2c`; awnings `#1c2f5a` (barber), `#1f5a3a` (deli, produce stand), `#b3261e` (pizza);
green debris netting `#2c5a3a` (chain-link weave). Unknown names render mid grey `#808080`, roughness 0.8
(`src/mats.js:42`).

Texture resolution follows the preset at boot: 256 px (`test`), 512 (`low`), else 1024 per tile, times each set's own
factor (`src/mats.js:146`); anisotropy 8 on ground, 4 on walls, 2 on props (`src/mats.js:150`).

### 2.5 The surface sets at real scale

One repeat covers `tile` metres (`SETS`, `src/mats/surfaces.js:1241`). "Relief" is the height between black and white of
the painted height map, which becomes the normal map.

| Set | Tile (m) | Relief | What is painted, with its real dimensions | Source |
|---|---|---|---|---|
| asphalt | 4 × 4 | 9 mm | Mid-grey binder `#38393c`; aggregate stones 2.5 – 10 mm, 16 % warm, 2.5 % nearly white; damp zones (roughness 0.92 → 0.56) and small puddles (roughness 0.06 where water stands, stones poking out at 0.48); relief flattened to the water level in puddles. Second skin `coat`: pale worn court paint `#eeeeea` with stone showing through | `src/mats/surfaces.js:195` |
| sidewalk | 4.5 × 4.5 | 12 mm | 3 × 3 flags of 1.5 m, each a slightly different grey around `#75726b`; broom strokes across the direction of travel; pits and exposed aggregate 1.5 – 5 mm; three hairline cracks 0.5 – 1.4 m; tooled joints 12 mm wide with 35 mm shoulders, packed dark `#35322e`; chewing gum 11 – 26 mm, about 34 pieces per tile, 12 % fresh and pale, the rest black | `src/mats/surfaces.js:272` |
| dirt | 3 × 3 | 20 mm | Earth `#3d342a`, damp hollows `#231d17`, pale dry patches `#5a4d3c`, pebbles 4 – 22 mm, 3 % green glass bits | `src/mats/surfaces.js:352` |
| brick | 2.4 × 2.4 | 11 mm | Common bond: five stretcher courses then one header course; brick 0.2 m long on a 66.7 mm course (12 × 36 per tile); 11 mm mortar. Skins: red (tones `#7a3327 #6d2d23 #86392b #74311f`, burnt `#45201b`, pale `#9a523b`, mortar `#7b756a`), brown (`#5a4032 #4f382c #654838 #574030`, mortar `#6a645b`), tan (`#9a8262 #8e7759 #a58c6a #94805e`, mortar `#7c7466`), painted (paint `#bcb7a9` with the red brick showing where it flaked, dirty streaks). 10 % of bricks burnt and glazed (roughness 0.62), 7 % pale | `src/mats/surfaces.js:395` |
| cinder | 2.4 × 2.4 | 9 mm | Blocks 0.4 × 0.2 m in running bond (6 × 12 per tile), 11 mm struck joints `#5d5b55`, faces `#8c8a82` with open pits 2 – 7 mm, dirty streaks | `src/mats/surfaces.js:472` |
| concrete | 2.4 × 2.4 | 6 mm | Form lift lines every 0.6 m (dark seam, pale grout fin), panel joints every 1.2 m, tie holes radius 13 mm on a 0.6 m grid of which 40 % weep rust 0.08 – 0.33 m, bug holes 1.5 – 6 mm, water streaks, efflorescence | `src/mats/surfaces.js:499` |
| stucco | 2 × 2 | 8 mm | Pale neutral render `#f0eee8`, lumpy, streaked `#6a665c`, one 0.5 m hairline crack | `src/mats/surfaces.js:571` |
| tile | 0.6 × 0.6 | 3 mm | Glazed tiles 150 × 75 mm in running bond (4 × 8), 4 mm grimy grout `#5d5a52`, 5 % cracked and matt | `src/mats/surfaces.js:589` |
| metal | 1.5 × 1.5 | 0.8 mm | Neutral sheet: faint brushing, 26 scuffs 0.05 – 0.35 m, handling stains. Skin `galv`: zinc spangle crystals about 22 mm | `src/mats/surfaces.js:621` |
| steel_el | 0.6 × 2.4 | 12 mm | One column face: dark green paint `#212d28`, rust `#6b3a1e`; two rows of rivets up the edges (x = 0.06 and 0.54 m) every 0.12 m; a splice plate from 1.05 to 1.35 m with two rows of three rivets; rivet heads radius 16 mm, 40 % weeping a rust drip 0.08 – 0.68 m; about 70 paint chips and rust scabs 4 – 30 mm; metalness 0.45 of the catalogue value under paint, 0.2 where rusted | `src/mats/surfaces.js:659` |
| rust | 1.5 × 1.5 | 4 mm | Scale `#5c3a25` with orange `#7c4420` / `#9a5a26`, dark `#2f2019`, islands of paint that still holds `#464d48`, pits 2 – 8 mm | `src/mats/surfaces.js:751` |
| roll_gate | 1.2 × 1.2 | 14 mm | 16 curved slats of 75 mm, each tucked under the one above; grime in the laps; vertical streaks; rust tint `#6b4a30`; ten dents and scrapes | `src/mats/surfaces.js:776` |
| corrugated | 1.2 × 1.2 | 16 mm | 16 waves of 75 mm running up the wall; dirt in the troughs; a sheet lap with a fixing on every second wave 50 mm below it, 30 % weeping rust 0.3 m | `src/mats/surfaces.js:819` |
| chain-link | 0.6 × 0.6 | – | 8 diamonds per tile (75 mm diagonal period), wire 8.5 % of the period wide, round (brighter crown), one wire family passing over the other; coverage in alpha | `src/mats/surfaces.js:875` |
| paint | 1.5 × 1.5 | 1.2 mm | Neutral enamel: orange peel, runs, grime in low places, about 60 chips 2 – 9 mm showing dark primer; gentle sheen changes only | `src/mats/surfaces.js:907` |
| pebble | 0.25 | 0.9 mm | Fine moulded-plastic grain (relief only) | `src/mats/surfaces.js:927` |
| tire | 0.24 | 7 mm | Four ribs of 60 mm with 12 mm grooves, slanted sipes every 30 mm mirrored rib to rib, road dust | `src/mats/surfaces.js:937` |
| wrinkle | 0.7 | 20 mm | Ridged bin-bag creases (relief and gloss only) | `src/mats/surfaces.js:973` |
| wood | 1.2 × 1.2 | 6 mm | Eight boards of 150 mm along u around `#70543a`, grain, a butt joint with four nail heads per board, knots on half of them, 5 mm gaps, silvered weathering `#8a8578` | `src/mats/surfaces.js:989` |
| plywood | 2.44 × 1.22 | 3 mm | One full sheet: rotary-cut cathedral grain on `#ae8e5f`, five boat-shaped patches 9 – 14 cm, a dark sheet edge with screws every 0.4 m, stains | `src/mats/surfaces.js:1059` |
| cardboard | 1 × 1 | 1.5 mm | Kraft `#9d7e55`, flutes every 8 mm telegraphing through, five creases, one 50 mm band of packing tape | `src/mats/surfaces.js:1119` |
| fabric | 0.25 | 1.4 mm | Plain weave, 4 mm pitch (two over, two under), neutral, faint streaks | `src/mats/surfaces.js:1150` |
| leaves | 1.2 | 20 mm | About 900 overlapping leaves 6 – 13 cm long, `#14261a` in the depth to `#2f4a2c` on top, on near-black `#0c160e` | `src/mats/surfaces.js:1178` |
| smudge | 1.6 | – | Roughness only: dried rain, streaks and handling marks (0.4 base, up to about 1.0) for glass and car bodies | `src/mats/surfaces.js:1219` |

### 2.6 World layers on ground and masonry

Static ground and wall materials get three world-space layers on top of the tiling set (`src/mats/shader.js:1`), all
driven by one four-channel noise texture that repeats every **48 m** (`MACRO_TILE`, `src/mats/shader.js:25`; channels:
puddles with blobs a few metres across, broad damp zones, tone, grime variation).

| Layer | Rule | Source |
|---|---|---|
| Tone variation | albedo × (1 + tone × (1 − 0.4 on sunlit ground by day) × (noise − 0.5) × 2), tone = first number of "World" in 2.4 (± 12 … 20 %) | `src/mats/shader.js:119` |
| Wall grime | On walls only: a band over the first 1.7 m above the ground (strongest at the foot), strength = third "World" number × (0.4 + noise); darkens the albedo by up to half of it and adds 0.3 × it to the roughness | `src/mats/shader.js:120`, `:149` |
| Damp street | On up-facing ground, strength = second "World" number: where the damp noise plus the set's own low spots passes 0.26 … 0.66 the roughness halves and the albedo drops 18 % | `src/mats/shader.js:143` |
| Puddles | Where the puddle noise plus low spots passes 0.66 … 0.72: roughness 0.05, albedo − 30 %, normal map flattened by 94 % (a mirror) | `src/mats/shader.js:144`, `:181` |
| Day sky fill | By day the diffuse image-based light on these materials loses 75 % of its colour (grey), and so does the blurred reflection on rough surfaces (roughness 0.35 … 0.75 ramps it in); sharp reflections keep the sky's blue | `src/mats/shader.js:22`, `:171` |

Day and night for the street (`dry` uniform, `src/mats.js:334`): at night `dry = 0`, the whole street is wet as
above. By day `dry = 1`: wetness only survives inside the open hydrant's reach, a capsule on the ground whose edge is
made ragged (± 0.6 m) by the damp noise and blends over 1 m. Outside it every would-be-wet patch goes matt
(roughness at least 0.86). The capsule (`WET_REACH`, `src/mats.js:50`; `findWetSpot`, `src/mats.js:358`):

| | Value |
|---|---|
| Hydrant (`hydrant_open` prop) | (−12.25, 0, 7.34), south kerb, spraying north (0, 0, −1) **(measured)** |
| Start of the capsule | 2.5 m out along the spray: (−12.25, 4.84), radius 5 m (the sheet of water at its foot) |
| End of the capsule | 24 m east and 1.1 m out from the kerb: (11.75, 6.24), radius 0.9 m (the gutter it feeds) |

The level also lays `asphalt_wet` blobs (irregular 14-sided patches: 28 along the avenue, 4 of them past the
closures, and 9 in the yards; `src/level/ground.js:152`, `src/level/yards.js:33`). At night they are mirrors (roughness
0.28). By day they take the dry street's albedo and only stay dark (− 60 %) and glossy inside the hydrant's reach
(`src/mats/shader.js:148`).

### 2.7 The window layer of building walls

Upper storeys are not modelled in the web game. A wall material carries a painted layer of windows, sills, lintels,
doors and a cornice over the tiling brick, with a matching glow layer (`mats.facade`, `src/mats.js:658`;
`src/mats/facade.js`; `src/mats/layout.js`).

**Effective configuration.** The level passes per-wall `bays`, `seed` and `lit` values, but `facade()` in
`src/level/buildings.js:94` ignores them and asks for one shared layer per wall material (`SHARED_FACADE`,
`src/level/buildings.js:15`). So the whole block has exactly **three** window layouts **(measured)**:

| Wall material | Seed | Repeat | Frame | Stone (sills, lintels) | Lintel | Lit windows of 19 |
|---|---|---|---|---|---|---|
| `brick_red` | 11 | 12.4 m × 15.5 m (4 bays × 5 storeys of 3.1 m) | `#e6e2d6` cream | `#b6ae9e` | soldier course of brick | 4 warm, 1 television |
| `brick_tan` | 23 | same | `#8a8478` grey | `#8f8a80` | stone | 5 warm |
| `brick_brown` | 31 | same | `#3a2a20` dark brown | `#b6ae9e` | stone | 5 warm |

Layout rules (`facadeLayout`, `src/mats/layout.js:63`), with the effective numbers for a 3.1 m bay and storey:

| Element | Size and rule |
|---|---|
| Window opening | 1.24 m wide (0.4 × bay, at most 1.25) × 1.736 m tall (0.56 × storey, at most 1.95), sill 0.60 m above the floor line, centred in its bay |
| Sash | Frame 55 mm, a 50 mm meeting rail: two panes, one above the other |
| Sill | 0.10 m stone, projecting 0.11 m each side, with a 0.08 m shadow under it |
| Lintel | stone: 0.25 m tall, 0.13 m past each jamb; brick: 0.22 m soldier course with a joint every 68 mm; steel: 0.11 m angle |
| Recess | 0.08 m shade under the head, 35 mm down one jamb |
| Blinds | 45 % of windows, let down 15 … 85 %, slats every 50 mm, colour `#9c927c` lit / `#4c4a44` dark |
| Curtains | 30 % of windows, drawn back to both sides (30 % of the pane each), one of `#8a3030 #2f506e #d8cfb8 #5a6a3a #c9a25a` |
| Window AC unit | 16 % of upper-floor windows: 0.62 m wide × 0.42 m, `#8f9290`, louvres, a 0.4 m rust drip under it |
| Bars | Every ground-floor window: bars every 0.13 m over the lower 62 % |
| Door | One per repeat on the ground row: 1.1 m × 2.3 m, `#2a1c14`, two panels, brass knob, a 0.3 m transom that is always lit (`#b98a4a` glow) |
| Cornice | Top 0.44 m of the repeat: pressed metal, dentils 0.16 × 0.16 m every 0.3 m, a 0.14 m shadow under it |
| Lit windows | Exactly round(0.24 × 19) = 5 per repeat; each is "tv" with probability 0.22, else "warm" |
| Warm room | One of `#ffc070 #ffd9a0 #f4a85a #ffcf8a`, brightest behind the upper sash |
| Television room | Blue `#35507a` → `#86b4ff`, brightest behind the lower sash |
| Dark glass | Gradient `#1b2632` → `#070a0e` with one slanting streak of reflection |

Grid as measured (rows from the top storey down; `W` warm, `T` television, `.` dark, `a` AC unit, `b` blind,
`c` curtains):

| Storey | brick_red (seed 11) | brick_tan (seed 23) | brick_brown (seed 31) |
|---|---|---|---|
| 5 | `.b  .  Tc  .` | `.  .bc  .bc  Wc` | `.b  .  Wbc  Wab` |
| 4 | `.b  .  .ab  .` | `.ab  .c  .ac  .ab` | `.b  .c  .c  Wc` |
| 3 | `Wc  .c  .  W` | `Wc  .b  .bc  .c` | `.c  .b  .ab  W` |
| 2 | `.b  W  .  .b` | `Wc  .  .b  Wbc` | `Wb  .c  .  .b` |
| 1 (ground) | `.c  Wb  DOOR  .` | `Wb  DOOR  .  .b` | `.c  DOOR  .  .` |

On street fronts the layer starts one storey below the shop cornice, so the ground row (door, barred windows) is
hidden behind the storefronts and row 2 sits at 3.8 m; on side and back walls the ground row shows
(`src/level/buildings.js:266`, `:301`). The layer repeats along a wall, centred so both ends keep a solid pier, and the
wall is bare above the top storey. Night glow of the layer: emissive × 1.6 (`FACADE_GLOW`, `src/mats.js:161`);
by day × 0, and the glass reads as dark glass with roughness 0.1 against 0.72 for frames and stone
(`src/mats/shader.js:152`). The layout also knows a `shopfront` ground floor (gates, lit and dark shop glass, a fascia
band); the level never asks for it (always `shopfront: false`), the real storefronts are modelled.

### 2.8 Sign styles

`mats.sign(spec)` paints a sign of `w` × `h` metres in one of seven styles (`STYLES`, `src/mats/signs.js:447`). "Glow" is
the emissive value a white texel of a lit sign reaches at night; by day every sign glow is × 0.3 and neon × 0.55
(`src/mats.js:159`, `:553`). Pixel density 256 px / m at the top texture tier (`src/mats/signs.js:14`).

| Style | The real object | Default colours | Glow night → day | Rough | Layout (fractions of the sign height unless noted) |
|---|---|---|---|---|---|
| `neon` | Glass-tube lettering on a dark backing board | tube `#ff3d9a`, board `#0b0b0e` | 2.6 → 1.43 | 0.45 | Outlined capitals in the display face, the outline is the tube; a border tube as a rounded rectangle inset 9 %, corner radius 14 %; tube width min(4.5 % of height, 1.2 % of width) = 28 mm on a 0.62 m sign; headline 46 % tall at mid height (36 % at 40 % with a sub line); sub line 13 % at 76 %, Archivo 700, in the second tube colour; unlit glass on the board is the tube colour mixed 55 % toward grey `#9a9aa2`; lit: a wide halo, a tight glow, a white-hot core 42 % of the tube width (`src/mats/signs.js:111`) |
| `box` | Back-lit plastic box sign in an aluminium frame | type `#b3261e`, face `#f1ede2` | 1.5 → 0.45 | 0.35 | Frame 4.5 %, dark `#1b1c20`; a keyline in the type colour; panel seams every 1.22 m; headline 54 % (40 % with a sub line); sub line 14 % at 78 % **in the `glow` colour**; lit face is brightest along two fluorescent bands at 28 % and 72 % of the height, 62 % at the top and bottom edges, 70 % at both ends (`src/mats/signs.js:168`) |
| `painted` | Hand-painted fascia board or wall advert | type `#f1e6c8`, board by text hash from `#6e1a1f #1b4a36 #1b3565 #1a1b1f #b8891a #4a2a5e` | unlit unless asked (0.85 under gooseneck lamps) | 0.8 | Block capitals 52 % (40 %) with a drop shadow 7 % of the letter height; a pinstripe border inset 8 %; sub line 13 % at 78 %, Archivo 500, tracked 0.14 em; sheet joints every 2.44 m; weathered, paint flaked to the primer (`src/mats/signs.js:217`) |
| `awning` | Lettering on a fabric valance or vinyl banner | type `#f4f2ec`, cloth `#7a1f24` | 0.8 → 0.24 | 0.9 | Headline 50 % at 46 % (38 % at 38 %); sub line 13 % at 72 %; a bound edge 7 % with a stitching line; soft folds between ribs every 0.6 m (`src/mats/signs.js:273`) |
| `street` | Street-name blade | white on green `#0f5c3f` | 0.45 → 0.135 | 0.4 | White keyline, name 46 %, suffix small and high (`src/mats/signs.js:324`) |
| `stencil` | Sprayed stencil lettering straight on a wall or the road | paint `#e9e4d4`, no board | never lit | 0.85 | Headline 72 % (56 % with a sub line 20 % at 82 %); a bridge 4.4 % of the font size through every letter with a counter; overspray ghost; worn through. A transparent overlay, like a decal (`src/mats/signs.js:357`) |
| `plate` | Transit plate: black enamel, white grotesque type | type `#f4f2ec`, enamel `#0d0e11` | 0.45 → 0.135 | 0.25 | A thin white rule 15 % from the top, 2.8 % thick, margins 13 %; text Archivo 700, 33 % at 60 %, left-aligned (25 % at 50 % with a sub line 15 % at 81 % in ink mixed 30 % toward black); optional route bullet, a disc 50 % of the height; four fixing holes (`src/mats/signs.js:395`) |

Faces: headline of `box`, `painted`, `awning`, `stencil` = Anton; `neon` = Anton outlines; `plate`, `street` and every
sub line = Archivo. Neon takes a second tube colour only when a sub line exists and no `glow` is passed (then cyan
`#35e0ff`); every neon sign in the level passes `glow` equal to its tube colour, so each is one colour
(`src/mats/signs.js:471`).

### 2.9 Every sign in the level

42 distinct paintings **(measured)**. `N`, `S`, `E`, `W` is the way the sign faces.

**Storefront bands** (`storefront`, `src/level/buildings.js:145`): band centre 3.29 m up, 0.15 m proud of the wall,
z = −10.85 on the north side (faces S), z = +10.85 on the south side (faces N). A lit band also registers a lamp
(2.17).

| Headline | Sub line | Style | W × H (m) | Colours | x | Side | Source |
|---|---|---|---|---|---|---|---|
| `24 HR LAUNDROMAT` | – | box | 7.5 × 0.62 | `#f4f2ec` on `#0d3550` | −41.6 | N side | `buildings.js:252` |
| `CROWN & FADE BARBER` | – | neon | 7.06 × 0.62 | red `#ff3030` | −30.3 | N side | `:261` |
| `HOLLIS DELI & GROCERY` | `OPEN 24 HRS  ·  COLD CUTS  ·  COFFEE  ·  LOTTO` | box | 8.4 × 0.74 | `#8a1410` on `#f2c21a`, sub `#ffd24a` | 16.5 | N side | `:297` |
| `CHECKS CASHED` | `MONEY ORDERS  ·  BILLS PAID` | neon | 6.56 × 0.74 | green `#55ff8a` | −42.15 | S side | `:320` |
| `99¢ PIZZA` | `SLICES ALL NIGHT` | box | 7.16 × 0.74 | `#fff1d0` on `#b3261e`, sub `#ff5a3a` | −34.15 | S side | `:321` |
| `PAWN & GOLD` | `WE BUY GOLD  ·  LOANS` | neon | 4.86 × 0.74 | gold `#f6c21a` | −27.0 | S side | `:337` |
| `TAPES · RECORDS · CDs` | – | neon | 4.66 × 0.62 | cyan `#35e0ff` | −18.9 | S side | `:338` |
| `GOLDEN BIRD CHICKEN` | `FRIED  ·  WINGS  ·  BISCUITS` | box | 7.5 × 0.74 | `#b3261e` on `#f2c21a`, sub `#ffc84a` | 0.5 | S side | `:377` |
| `WINES & LIQUORS` | – | neon | 7.36 × 0.62 | red `#ff3030` | 9.25 | S side | `:378` |
| `LUCKY NAILS` | `MANICURE  ·  PEDICURE` | neon | 7.36 × 0.74 | pink `#ff3d9a` | 17.75 | S side | `:379` |

The three south-side signs at x 0.5 … 17.75 hang behind the sidewalk shed, which is why the same three names hang
again as banners on its parapet (below). Awnings under the bands: barber navy `#1c2f5a`, deli green `#1f5a3a`, pizza
red `#b3261e`.

**Everything else.**

| Text (headline / sub line) | Style | W × H (m) | Colours | Lit | Centre (x, y, z), facing | Source |
|---|---|---|---|---|---|---|
| `V&R AUTO BODY` | box | 8 × 1.05 | `#f6c21a` on `#101113` | yes | (−12, 5.4, −10.87) S, on the shop's corrugated fascia `#1a2b3a` (y 4.75 … 6.05) | `src/level/shop.js:304` |
| `TIRES  ·  BRAKES  ·  EXHAUST` | painted | 5.4 × 0.6 | `#e9e2cf` on `#1a2b3a` | no | (−1.3, 5.4, −10.87) S | `shop.js:307` |
| `INSPECTIONS  ·  24 HR TOWING` | painted | 5.6 × 0.6 | same | no | (−19.6, 5.4, −10.87) S | `shop.js:309` |
| `FLAT FIX` / `NO APPOINTMENT` | stencil | 2.6 × 1.1 | `#e6e4dc` | no | (−6.1, 2.6, −10.98) S | `shop.js:311` |
| `EXIT` | box | 0.7 × 0.3 | `#fff1d0` on `#7a1410` | yes | (5.57, 2.85, −22.1) W, inside the shop over the side door | `shop.js:114` |
| `V&R AUTO BODY` / `COLLISION  ·  FRAME  ·  PAINT` | painted | 12 × 3.2 | `#e9e2cf` on `#1d2f3f` | no | (−23.97, 11.4, −24.5) E, the tenement's party wall above the shop roof | `buildings.js:278` |
| `PARK` / `24 HR  ·  PAY AT BOOTH` | painted | 5 × 1.6 | `#f4f2ec` on `#1f4f9a` | no | (22.03, 2.3, 18.5) E, wall of S3 on the lot | `buildings.js:393` |
| `188 ST` / `ELEVATED  ·  CLOSED 1 AM – 5 AM` | plate | 4.6 × 0.82 | default | yes | (−39.37, 4.47, 0) E, station mezzanine | `src/level/el.js:179` |
| `188 ST` / `STATION CLOSED` (× 2) | plate | 1.5 × 0.42 | default | yes | (−38.46, 2.39, ±8.15) E, over each stair gate | `el.js:238` |
| `ROAD CLOSED` / `EL STRUCTURE REPAIRS  ·  NO THRU TRAFFIC` (× 2) | box | 3.4 × 1.05 | `#101113` on orange `#e8641b` | no | (−45.25, 1.75, −2.6) and (−45.25, 1.75, 3.4) E, west hoarding | `src/level/street.js:402` |
| `SIDEWALK CLOSED` / `USE WALKWAY` (× 2) | box | 2.2 × 0.7 | same orange | no | (22.01, 1.75, 9.0) E and (20.53, 1.75, 7.03) N, hoist tower | `street.js:377` |
| `EL REPAIRS` / `KEEP CLEAR` (× 4) | box | 1.3 × 0.5 | same orange | no | (−30.22, 1.5, 2.2) W, (−28.58, 1.5, 2.2) E, (−1.92, 1.5, −2.15) W, (−0.28, 1.5, −2.15) E, on the two rolling scaffolds | `street.js:222` |
| `DANGER` / `STEAM  ·  KEEP OUT` (× 2) | box | 1.5 × 0.6 | `#b3261e` on `#f4f2ec` | no | (18.9, 1.65, −6.99) S and (20.1, 1.65, −9.25) N, the dig pen | `street.js:320` |
| `NEWS  ·  MAGAZINES  ·  LOTTO` | painted | 2.4 × 0.26 | `#f4f2ec` on `#24463a` | no | (−28.7, 2.42, −9.51) N, shut news kiosk | `street.js:253` |
| `CANDY  ·  SODA` | painted | 1.35 × 0.26 | same | no | (−42.49, 2.42, 10.08) E, kiosk beside the south stair | `street.js:421` |
| `GOLDEN BIRD CHICKEN` | awning | 4.9 × 0.78 | `#b3261e` on `#f2c21a` | no | (4.1, 3.5, 7.44) N, banner on the shed parapet | `street.js:498` |
| `WINES & LIQUORS` | awning | 4.9 × 0.78 | `#ff3030` on `#101113` | no | (10, 3.5, 7.44) N | `street.js:498` |
| `LUCKY NAILS` | awning | 4.9 × 0.78 | `#ff3d9a` on `#2a0f1e` | no | (15.9, 3.5, 7.44) N | `street.js:498` |
| `SIDEWALK SHED  ·  PERMIT 0214  ·  STORES OPEN DURING WORK` | stencil | 5.6 × 0.24 | `#e6e4dc` | no | (10, 2.7, 7.41) N, shed skirt | `street.js:507` |
| `POST NO BILLS` (× 3) | stencil | 1.5 × 0.24 | `#e6e4dc` | no | (−16, 2.55, 8.59) N shanty; (−13.95, 2.3, 11.09) and (−6.35, 2.3, 11.09) N lot hoarding | `street.js:342`, `src/level/yards.js:289` |
| `USED TIRES` / `ALL SIZES  ·  MOUNTED FREE` | stencil | 2 × 0.5 | yellow `#f2c21a` | no | (−19.2, 2.76, −8.5) S, on a dark steel plate over the tyre cage | `street.js:274` |
| `NO PARKING` / `LOADING ZONE` | stencil | 1.6 × 0.6 | `#e6e4dc` | no | (16, 2.6, 26.02) S, back wall of S3 | `yards.js:367` |
| `VIOLATORS TOWED` / `AT OWNER'S EXPENSE` | stencil | 3.4 × 0.9 | `#e6e4dc` | no | (45.98, 2.4, 19.5) W, lot east wall | `yards.js:473` |
| `41`, `42`, … `48` | stencil | 0.7 × 0.42 | `#e6e4dc` | no | (x, 3.3, 30.98) N over the garage doors, x = −13.6, −9.2, −4.8, −0.4, 4, 8.4, 12.8, 17.2 | `buildings.js:414` |
| `PARK` / `24 HR` (both faces) | neon | 1.7 × 1.5 | cyan `#35e0ff` | yes | (35.24, 4.7, 11.65) W and (35.46, 4.7, 11.65) E: a sign box 0.2 × 1.8 × 1.6 m (y 3.9 … 5.5) on a 5.6 m pole at the lot entrance | `yards.js:414` |

Not placed by the level, but in the kit: the `street` style (prop `sign_post` variant `street`, default text
`JAMAICA AV`, blade 0.58 × 0.15 m: `src/props/street.js:543`) and route bullets on plates.

### 2.10 Posters

`mats.poster(kind, seed)` (`src/mats/paper.js:396`); variant = seed mod variant count. Ink `#0d0e11`, paper `#f1ede2`,
roughness 0.88. Every poster is aged: paste ridges, dirt, about 28 nibbles out of the edges, a corner torn off on 60 %
(`age`, `src/mats/paper.js:55`).

| Kind · variant | Size (m) | Content, top to bottom | Source |
|---|---|---|---|
| `ipx` · 0 / 1 / 2 / 3 | 0.6 × 0.9 | A rule, the IPX mark (at most 30 % of the sheet height), `IPX.EXCHANGE`, a rule. Paper / ink: black / gold, gold / black, cream / black, oxblood `#6b1218` / cream. Nothing else | `paper.js:91` |
| `show` · 0 | 0.6 × 0.9 | Black sheet with a gold band: `ONE NIGHT ONLY` / `RULE` (27 % of the height, black on the band) / `HOLLIS · QUEENS` / IPX mark / `IPX.EXCHANGE` | `paper.js:104` |
| `show` · 1 | 0.6 × 0.9 | Red `#c9281e` with a 24-ray sunburst: `BLOCK` / `PARTY` (cream `#f1e6c8`); black band `SATURDAY · SUNDOWN` (gold); `DJs · OPEN MIC · ALL AGES` | `paper.js:115` |
| `show` · 2 | 0.6 × 0.9 | Blue `#1c3a6e`: a large cassette; `THE HOLLIS` / `SESSIONS` (gold) / `LIVE ON TAPE · VOL. 3` | `paper.js:137` |
| `show` · 3 | 0.6 × 0.9 | Yellow `#f2c21a`: a record (black disc, red label); `TAPE SWAP`; black band `RECORDS · TAPES · CDs`; `EVERY SUNDAY` | `paper.js:163` |
| `wanted` · 0 | 0.45 × 0.6 | Paper `#e9e0c6`, black frame: `WANTED`; a hooded head and shoulders in a pale mask `#d9d4c6` with an oxblood chest band; `THE VULTURES`; `BOOTLEG CREW · REWARD` (red) | `paper.js:210` |
| `wanted` · 1 | 0.45 × 0.6 | `MISSING` (red); three tape reels; `3 MASTER REELS`; `LAST SEEN ON THE AVENUE`; `NO QUESTIONS ASKED` (red) | `paper.js:222` |
| `wanted` · 2 | 0.45 × 0.6 | Paper `#e6d9a8`: a struck-through cassette; `NO BOOTLEGS`; `BUY IT FROM THE ARTIST` | `paper.js:247` |
| `ad` · 0 | 1.2 × 1.8 | Yellow with a red top band: `GOLDEN BIRD` / `CHICKEN`; a 14-point red star with `2 PC` / `$1.99`; `OPEN LATE · JAMAICA AVE` | `paper.js:269` |
| `ad` · 1 | 1.2 × 1.8 | Cream with a green `#1f6b3a` top and a red bottom band: `99¢` / `PIZZA`; one slice; `OPEN LATE` | `paper.js:280` |
| `ad` · 2 | 1.2 × 1.8 | Pink `#f2a6c0` over teal `#1f8a8a`, sparkles: `LUCKY` / `NAILS`; `MANICURE · PEDICURE`; `WALK-INS WELCOME` | `paper.js:312` |
| `ad` · 3 | 1.2 × 1.8 | Blue `#1f4f9a` with bubbles: `24 HR` (gold) / `LAUNDROMAT`; `WASH · DRY · FOLD`; `DROP OFF BY 9` | `paper.js:323` |
| `torn` · 0 / 1 / 2 | 0.5 × 0.7 | What is left of older posters: a tilted word `LIVE` (red sheet), `SALE` (yellow), `TONITE` (blue), three to five ragged tears with white fibre rims | `paper.js:343` |

35 posters are up **(measured)**; `wanted` · 0 and `ipx` · 0 exist but are not placed.

| Where (facing) | Posters as kind · variant at the given spot |
|---|---|
| News kiosk, face at z −9.51 (N) | show · 2 at (−29.7, 0.57); torn · 1 at (−27.75, 0.55) (`street.js:246`) |
| Candy kiosk, face at x −42.49 (E) | show · 2 at (z 9.75, y 0.57); torn · 1 at (z 10.35, y 0.55) |
| West hoarding, x −45.25 (E) | show · 1 at (z −5.6, y 1.4); ipx · 1 at (z −4.9, y 1.45); torn · 2 at (z 5.8, y 1.3) (`street.js:406`) |
| Site shanty, x −17.42 (W) | show · 0 at (z 9.3, y 1.65); ad · 1 at (z 10.05, y 1.6) (`street.js:344`) |
| Hoist tower, x 22.02 (E) | ipx · 1 at (z 10.3, y 1.35) (`street.js:380`) |
| Shop front, z −10.98 (S) | show · 0 at (2.2, 1.7); torn · 1 at (2.95, 1.6) (`shop.js:314`) |
| Shop interior | north wall: ad · 3 (−2.6, 2.3), show · 1 (−1.2, 2.2), wanted · 2 (2.6, 2.0); east wall: show · 1 (z −15, y 2.2), torn · 1 (z −14.2, y 2.05); west wall: ad · 2 (z −17.6, y 2.3); office: ad · 0 (−20.2, 4.5) on its north wall, ipx · 1 (z −28.6, y 4.4) on its west wall (`shop.js:107`, `:205`) |
| Alley, deli wall x 10.98 (W) | show · 1 (z −17.4, y 1.7); torn · 1 (z −16.7, y 1.6); wanted · 2 (z −28.6, y 1.6) (`yards.js:56`) |
| The cut, x 22.02 (E) | ipx · 3 (z −13.2, y 1.8); show · 0 (z −12.5, y 1.75) (`yards.js:83`) |
| Vacant-lot hoarding, z 11.09 (N) | A row, bottom edges 1.05 m up ± 0.06, gaps 0.08 … 0.5 m: west of the gateway show · 0, ad · 1, torn · 0; east of it wanted · 1, show · 1, ipx · 2, show · 3 (`yards.js:282`) |
| Vacant lot, east wall x −4.02 (W) | ad · 3 (z 13.1, y 1.9) (`yards.js:319`) |
| Rear lane, z 26.02 (S) | torn · 1 (4.4, 1.7) (`yards.js:366`) |
| Lot south wall, z 33.98 (N) | ipx · 3 (38.2, 1.8) (`yards.js:477`) |

### 2.11 Graffiti

`mats.graffiti(text, seed, color)` (`src/mats/paper.js:599`). The hand is seed mod 3:

| Hand | Look | Natural size (n letters) |
|---|---|---|
| 0 marker tag | Fat-cap marker, slanted, each letter a little off true; underlined in one stroke ending in an arrowhead; three tick marks over the last letter; a drip on 30 % of the letters | max(1, 0.42 n) × 0.9 m |
| 1 spray tag | Soft edges, a faint wide overspray of the same letters, a ring thrown round the tag, 160 flecks, long drips on 45 % of the letters | max(1, 0.42 n) × 0.9 m |
| 2 throw-up | Bubble letters: fill colour inside a heavy outline (`#0b0b0d`, or cream when the fill is dark), a hard offset shadow, a white shine stroke on every letter, two four-point sparkles, a cloud of a second palette colour behind | max(1.6, 0.62 n + 0.5) × 1.4 m |

Spray palette (`src/mats/paper.js:19`): `#e2222b #f6c21a #39d0e0 #f4f2ec #ff3d9a #55ff8a #9a5cff #ff7a1a`; a tag without a
colour takes entry (5 × seed + n) mod 8. The Vulture colour on walls is `#8a1a22`. Paint misses the pits and joints of
the wall (a 55 % wear mask); roughness 0.7. 23 tags are on the block **(measured)**:

| Text | Seed · hand | Colour | Drawn (m) | Centre (x, y, z), facing | Source |
|---|---|---|---|---|---|
| `VULTURES` | 21 · marker | `#8a1a22` | 3.4 × 1.0 | (−3.4, 0.03, −0.7) on the road at reel 1, yaw −0.3 rad | `street.js:82` |
| `VULTURES` | 5 · throw-up | `#8a1a22` | 3.6 × 1.1 | (45.20, 1.4, −4.6) W, roadblock scrim | `street.js:450` |
| `VLTR` | 3 · marker | `#8a1a22` | 1.68 × 0.9 | (45.20, 1.2, 5.4) W, roadblock | `street.js:451` |
| `VLTR` | 3 · marker | `#8a1a22` | 1.68 × 0.9 | (19.96, 0.95, 7.03) N, hoist tower | `street.js:381` |
| `HOLLIS` | 6 · marker | `#f4f2ec` | 2.52 × 0.9 | (−45.25, 0.9, 0.4) E, west hoarding | `street.js:405` |
| `QNS` | 4 · spray | `#35e0ff` | 1.26 × 0.9 | (−17.42, 0.85, 9.8) W, shanty | `street.js:346` |
| `188` | 2 · throw-up | `#55ff8a` | 2.36 × 1.4 | (18.9, 1.05, −9.25) N, dig pen | `street.js:323` |
| `VULTURES` | 5 · throw-up | `#8a1a22` | 3.2 × 1.0 | (6.02, 1.7, −15.2) E, alley, shop wall | `yards.js:53` |
| `188` | 2 · throw-up | `#55ff8a` | 2.36 × 1.4 | (6.02, 1.5, −26.2) E, alley | `yards.js:54` |
| `HOLLIS` | 9 · marker | `#f4f2ec` | 2.8 × 1.0 | (10.98, 1.6, −24.5) W, alley, deli wall | `yards.js:55` |
| `QNS` | 4 · spray | `#35e0ff` | 1.26 × 0.9 | (22.02, 1.5, −22.5) E, the cut | `yards.js:82` |
| `VULTURES` | 11 · throw-up | `#8a1a22` | 4.2 × 1.2 | (38.65, 0.03, −18.2) on the court floor, yaw 0.25 rad | `yards.js:182` |
| `RULE` | 1 · spray | `#f6c21a` | 6.4 × 2.3 | (−15.97, 6.55, 15.6) E, across the mural | `yards.js:265` |
| `HOLLIS` | 6 · marker | `#f4f2ec` | 2.6 × 0.8 | (−15.97, 1.25, 22.9) E, mural wall | `yards.js:266` |
| `QUEENS` | 8 · throw-up | `#35e0ff` | 2.2 × 0.75 | (−15.97, 1.05, 12.6) E, mural wall | `yards.js:267` |
| `NO SLEEP` | 14 · throw-up | `#9a5cff` | 5.46 × 1.4 | (−15.97, 1.4, 26.6) E, mural wall toward the lane | `yards.js:268` |
| `VLTR` | 3 · marker | `#8a1a22` | 2.4 × 0.9 | (−4.02, 1.5, 15.2) W, vacant lot | `yards.js:317` |
| `JAMAICA AVE` | 10 · spray | `#55ff8a` | 4.62 × 0.9 | (−4.02, 1.2, 19) W, vacant lot | `yards.js:318` |
| `INC` | 12 · marker | `#f6c21a` | 1.26 × 0.9 | (2.4, 1.5, 26.02) S, rear lane | `yards.js:365` |
| `188` | 16 · spray | `#ff3d9a` | 1.26 × 0.9 | (45.98, 1.4, 26.4) W, lot east wall | `yards.js:474` |
| `QUEENS` | 15 · marker | `#f6c21a` | 2.8 × 0.95 | (27.2, 1.5, 33.98) N, lot south wall | `yards.js:476` |
| `VULTURES` | 3 · marker | `#8a1a22` | 3.6 × 1.1 | (−6.1, 2.5, −11.42) N, inside the shop | `shop.js:113` |
| `VLTR` | 7 · spray | `#8a1a22` | 1.68 × 0.9 | (3.6, 1.5, −10.98) S, shop front | `shop.js:313` |

Every box truck also carries `RULE` (cream `#e9e4d6`) on one flank and `HOLLIS` (gold `#f6c21a`) on the other, scaled to
fit 2.6 × 1.2 m (`src/props/vehicles.js:749`).

### 2.12 The mural and the billboard

**The mural** (`buildMural`, `src/level/yards.js:189`): 12 m × 7.6 m, matt (roughness 0.92), never glows, on the pawn
shop's side wall over the vacant lot. Centre (−15.98, 4.5, 18.4), facing east: it spans z 12.4 … 24.4 and y 0.7 … 8.3.
Fractions below are of the mural's width (W) or height (H), measured from the top left.

| Layer | Content |
|---|---|
| Field | Vertical gradient `#111a33` (top) → `#3b1420` (at 62 % H) → `#0b0c12` (bottom) |
| Rays | 18 wedges fanning from the record's centre, alternating gold `rgba(246,194,26,0.20)` and red `rgba(226,34,43,0.14)` |
| Gold record | A disc `#d9a514`, centre at 30 % W, 56 % H, radius 40 % H (3.04 m); groove rings from 42 % to 97 % of the radius, every 4.5 %, dark brown at 55 % opacity; label `#8a1a22`, radius 34 % of the disc; spindle hole `#0b0c12`, 4.5 %. "A gold record rising like a sun behind the El" |
| The El | A silhouette `#07080c` along the bottom: a deck band from 78 % to 82.5 % H, a column with a haunch every 11.5 % W, a ground band over the last 4.5 % H |
| The mark | IPX mark `#f4f2ec`, height 17 % H (1.29 m), centred at 77 % W, 60 % H; `IPX.EXCHANGE`, Archivo 600, font size 5 % H (0.38 m), centred at 77 % W, 72.5 % H. No slogan |
| Frame | A gold `#f6c21a` line, 1.2 % H thick, inset 2 % H |
| On top | `RULE`, a gold spray tag 6.4 × 2.3 m, "sprayed big over the paint by a surer hand than the tags around it" (2.11) |

**The IPX billboard** (prop `billboard`, `src/props/lot.js:120`; face art `billboardFace`, `src/props/materials.js:186`):
at (40.7, 12.4), facing south into the lot. Structure 9.0 m wide and 10.8 m tall in El-green riveted steel: two legs
5.2 m apart with X bracing, a truss behind the face, a grated catwalk 0.35 m under the face with a rail, a ladder, four
lamp arms. Face panel 8.9 m × 4.0 m, underside 6.75 m above the ground (plane z = 12.62).

| Face layer | Content (fractions of the face) |
|---|---|
| Field | `#0d0e11` |
| Mark | IPX mark `#f4f2ec`, height 52.7 % of the face height (2.11 m), centred horizontally, its centre 41.8 % down |
| Bar | Gold `#f6c21a`, as wide as the mark, 1.2 % of the face height (4.7 cm), 75.8 % down |
| Address | `IPX.EXCHANGE`, Archivo 700, font size 9 % of the face height (0.36 m), letter spacing 0.3 em, `#f4f2ec`, 85.9 % down |
| Painted light | Darkened from 62 % at the top edge to nothing at the bottom; a warm wash `rgb(255,214,150)` up to 16 % along the bottom: lit from the catwalk |
| Material | Unlit, × 1.5: it reads the same by day and by night. Four lamp strips `#fff1d6` × 3.2 on the arms; two flood lamp hints (2.17) aimed up the face |

### 2.13 Graphics carried by props (labels, liveries, licence plates)

One 2048 × 1024 sheet (`src/props/atlas.js`), two materials: scene-lit, roughness 0.7, and self-lit × 1.7 for the
regions marked lit (`src/props/materials.js:28`, `:106`). Palette of the sheet: ink `#f4f2ec`, gold `#f6c21a`, plate
`#0f1114`, oxblood `#8a1820`, navy `#16264f`.

| Region | Text and drawing | On | Physical size (m) |
|---|---|---|---|
| `ipx_side` | IPX mark, a gold bar, `IPX.EXCHANGE` (Archivo 700, tracked) | Both flanks of the IPX truck | 3.5 × 0.875 |
| `ipx_mark` | The mark alone | Truck bonnet 0.8 × 0.33, vault wall 1.1 × 0.46, one rear door 0.62 × 0.26; master-case lid 0.3 × 0.125 and inside the lid 0.26 × 0.108 | as listed |
| `ipx_url` | `IPX.EXCHANGE` | The truck's other rear door | 0.74 × 0.092 |
| `ipx_tag` | Cream tag `#f1efe6`: the mark, `TRACKER`, a barcode | Master-case front | 0.2 × 0.1 |
| `tracker_lcd` (lit) | `IPX` in gold italic and four signal bars on `#0a0f0a` | Tracker on the master case | 0.084 × 0.035 |
| `ipx_ad` (lit) | Dark one-sheet: rule, `IPX PRESENTS`, `MURDER` (ink) over `INC.` (gold) in Anton, `STARRING JA RULE`, a gold bar, the IPX mark, `IPX.EXCHANGE` (`#a9a7a0`) | Both faces of the bus shelter's ad panel, centre (27.48, 1.35, −8.05), facing east and west | 1.14 × 1.72 |
| `reel_label` | Cream label: `MASTER REEL`, `MURDER INC.`, `REEL __ / 3`, `SPEED 30 IPS`, `TAPE 2 IN · 24 TRK`, small IPX mark | Tape box in the master case | 0.26 × 0.26 |
| `reel_top` | Gold reel from above: flange `#e7b53a`, three spokes `#f0c75a`, dark tape pack | The reel | ⌀ 0.27 |
| `plate_0` … `plate_3` | Licence plates: `NEW YORK` over `HLS·2141`, `TKV·9907`, `KQB·5530`, `LWG·4418`; cream `#f1efe6`, navy type and keyline, a gold `#d9a21c` band. "Invented codes only" | Sedans, SUVs, pickups, vans, box trucks; the IPX truck wears `KQB·5530` | 0.30 × 0.15 |
| `plate_taxi` | Yellow `#f0c63a` plate `T·5K83` with a navy band | Cabs | 0.30 × 0.15 |
| `taxi_door` | `NYC TAXI` (Anton), medallion `5K83`, a ruled fare box, black | Cab front doors | 0.92 × 0.37 |
| `taxi_roof` (lit) | `5K83` on a cream-to-yellow light box | Cab roof light, both faces | 0.36 × 0.075 |
| `checker` | Black and cream checker band | Cab flanks | band 0.07 tall |
| `vulture` | The crew mark: a hunched vulture on a wire, cut as a spray stencil, cream `#e9e4d6`, worn | Both flanks of the Vultures' van 1.15 × 0.92; some crates 0.5 × 0.4 | as listed |
| `tag_a` / `tag_b` / `tag_c` | Marker scrawls without letters: cream, oxblood, black | Van, dumpster, mailbox, phone booth, barrier | about 0.5 × 0.22 |
| `stripes_ow` / `stripes_yb` / `stripes_rw` | Diagonal hazard stripes: orange / white, yellow / black, red / white | Barricade boards, jersey barrier, IPX truck step bumper | bands 0.1 … 0.2 tall |
| `sign_bus` | `BUS` / `STOP` under a bus pictogram, `NO STANDING` (red); blue `#1f4f9a` on cream | Bus-shelter flag | 0.26 × 0.36 |
| `sign_nopark`, `sign_oneway`, `sign_stop` | `NO` / `PARKING` / `ANYTIME` with a double arrow (red on cream); `ONE WAY` in a white arrow on black; `STOP` on a red octagon | Prop `sign_post` (not placed in the level) | 0.32 × 0.44; 0.58 × 0.18; 0.52 |
| `news` | Front page: `QUEENS NIGHT LEDGER` / `THREE REELS` / `GONE` | Newspaper boxes | 0.33 × 0.41 |
| `mail` | `MAIL` on navy over cream | Mailboxes | 0.36 × 0.27 |
| `meter` | Dial, `1 HR`, `25¢` | Parking meters, both faces | 0.1 × 0.15 |
| `phone_sign` (lit), `phone_unit` | `PHONE` with a handset on blue; keypad, `25¢` | Phone booths | 0.8 × 0.2; 0.26 × 0.33 |
| `vend` (lit) | Blue fizz front: `ICE` / `COLD` / `SODA`, price badge `$1.00` | Vending machines | 0.6 × 1.2 |
| `ped_stop` / `ped_walk` (lit) | Orange hand / white walking figure on black | Pedestrian signal (not placed) | 0.3 × 0.3 |
| `cart_menu` | Red board with yellow bars: `HOT DOGS`, `PRETZELS · COLD SODA`; price list `HOT DOG 1.50`, `SAUSAGE 2.50`, `PRETZEL 1.25`, `SODA 1.00` | Food cart, both sides | 1.5 × 0.52 |
| `booth_sign` (lit) | `PARK` (gold, Anton) / `24` / `HOURS` on black with a yellow keyline | Lot booth, under the window | 1.6 × 0.56 |
| `booth_rates` | `RATES`: `FIRST HOUR $6`, `EACH ADD’L $3`, `ALL NIGHT $14`, `LOST TICKET $30`, `NO IN & OUT` | Lot booth, by the door | 0.5 × 0.65 |
| `dumpster` | `HOLLIS CARTING` / `718 · 555 · 0144`, sprayed and worn | Dumpsters | 0.5 × 0.1 |
| `crate_stencil` | `FRAGILE` / `HANDLE WITH CARE` / `LOT 0214 · QNS`, an up arrow | Wooden crates | 0.66 × 0.44 |
| `cardboard` | Two up arrows, `THIS SIDE UP`, a shipping label with a barcode | Cardboard boxes | 0.3 × 0.3 |
| `drum_label` | `MOTOR OIL` / `10W-40` / `55 GAL · 208 L` | Oil drums | 0.19 × 0.12 |
| `gen_label`, `gauges` | `DANGER` / `HIGH VOLTAGE` / `60 kW · 480 V` on yellow; two dials and four buttons | Generator | 0.42 × 0.175; 0.34 × 0.34 |
| `porta` | `HOLLIS` / `SITE SERVICES` / `UNIT 14` | Portable toilets | 0.44 × 0.33 |
| `flame` | Red hazard diamond with a white flame and `2` | Propane tanks, both sides | 0.13 × 0.13 |
| `gas_placard` | `DANGER` / `FLAMMABLE GAS` / `NO SMOKING` / `NO OPEN FLAME` | Welding rack | 0.36 × 0.25 |
| `boombox`, `backboard`, `ticking`, `stickers` | Boombox face (tuner, two speakers, cassette door); orange backboard lines; striped mattress ticking; nine layered stickers | Boombox, hoops, mattress, lamp posts and booths | – |

Source of every region: `src/props/atlas.js:274` to `:858`; plates `src/props/atlas.js:20`, `:252`.

### 2.14 Road paint, ground and wall decals

`mats.decal(kind, variant)` (`DECALS`, `src/mats/decals.js:17`). All are transparent overlays.

| Kind | Size (m) | Variants | Rough | Look | Where the level uses it |
|---|---|---|---|---|---|
| `lane` | any length × 0.12 | 1 | 0.6 | Worn white road paint `rgb(226,224,214)`, scuffed, pin-holed, cracked crust; tiles every metre | Parking ticks every 5.8 m at both kerbs (\|z\| 5.1 … 6.98), stop bars 0.4 m wide at x 21.9 and 27.7, lot bays 0.1 m, court lines 0.07 m (`src/level/ground.js:94`, `:110`) |
| `lane_yellow` | any × 0.12 | 1 | 0.6 | Worn yellow `rgb(222,170,28)` | Double centre line at z ± 0.15 from x −96 to 22.6 and 27 to 96 (`ground.js:86`) |
| `crosswalk` | 4 × 3 nominal | 1 | 0.6 | Ladder crossing: one bar per metre, 0.45 m wide, running the depth | One mid-block crossing x 23 … 26.6 across 13.6 m of road (`ground.js:102`) |
| `arrow` | 1.2 × 3 | 1 | 0.6 | Straight-ahead lane arrow | Avenue: (−29, 2.3) and (15.5, 2.3) pointing east, (−12, −2.3) and (34, −2.3) pointing west; two in the lot (`ground.js:114`, `yards.js:430`) |
| `oil` | 1.6 × 1.2 | 3 | 0.16 | Sump oil, black at the heart, faint rainbow arcs at the rim | 14 at random along both parking lanes; shop floor; lane; lot |
| `crack` | 2 × 0.6 | 3 | 0.95 | A branching crack with crumbled shoulders | 16 at random across the roadway; 4 in the lot |
| `grime` | 2 × 2 | 3 | 0.95 | Ground-in dirt | 12 along the gutters; alley; lane; shop floor |
| `scorch` | 3 × 3 | 2 | 1.0 | Blast mark: burnt black centre, 46 soot rays | Under the burned-out car in the vacant lot, stretched to 5.5 × 4.2 (`yards.js:296`) |
| `manhole` | 0.9 × 0.9 | 1 | 0.55, metal 0.65 | Cast-iron cover with waffle tread, two pick holes, a tar collar | Available; the six manholes of the level are props |
| `bullet` | 0.12 × 0.12 | 3 | 0.9 | A dark hole in a pale crater with hairline cracks | Available; live bullet holes come from the effects system (2.24) |
| `puddle` | 2.4 × 1.6 | 3 | 0.04 | Standing water, nearly black, firm shoreline | Available; the level uses `asphalt_wet` blobs instead |

Yellow kerb paint (solid `paint_yellow`): south kerb x −16.4 … −12.6 at the hydrant, north kerb x 27.2 … 31.2 at the bus
stop (`ground.js:120`). The random street decals are seeded (same every run with the default seed 1994).

### 2.15 The two rigs: day (default) and night

`atmos.setTime('day' | 'night')` applies one column of this table (`times`, `src/config/look.js:318`; `setTime`,
`src/atmos.js:279`). Both rigs are built at boot; switching changes values and visibility only. All numbers are
effective values **(measured)** against the constants.

| | DAY (default, "4:15 PM") | NIGHT ("02:14 AM") | Source |
|---|---|---|---|
| Key light: what it is | The sun | "Steep, warm, standing in for the street lights". Not the moon | `look.js:95`, `:331` |
| Key: direction the light travels | (0.553, −0.788, −0.271) | (−0.38, −1, −0.3), normalised (−0.342, −0.900, −0.270) | `look.js:316`, `:99` |
| Key: where it stands in the sky **(derived)** | Elevation 52.0°, compass bearing 243.9° (west-south-west) | Elevation 64.2°, bearing 128.3° (south-east) | – |
| Key: colour, intensity | `#ffe6c6`, 5 game lux | `#ffb873`, 2.6 game lux | `look.js:332`, `:97` |
| Key: shadows | One shadow map over the whole block, depth bias 0.03 m, normal bias 0.03 | Same map, bias 0.045 m, normal bias 0.035 | `look.js:336`, `:101` |
| Shadow frustum (fitted, **measured**) | Orthographic 106 m × 107 m, 89 m deep; 2.6 cm texels at 4096, 5.2 cm at 2048 | 115 m × 117 m, 72 m deep; 2.8 cm at 4096 | `src/atmos/plan.js:53` |
| Ambient hemisphere | sky `#c0c6cc`, ground `#b09474`, intensity 1.0: "a near-neutral sky fill: the blue is in the environment map already, and shade must stay grey" | sky `#6e86be`, ground `#4a3a2c`, intensity 1.7: "shadows must stay readable at night: a dark figure against a dim wall at 40 m" | `look.js:340`, `:89` |
| Haze colour (linear) | [0.6, 0.7, 0.86] | [0.03, 0.03, 0.036] | `look.js:342`, `:78` |
| Haze density (squared-exponential) | 0.0032: 1.6 % at 40 m, 8.3 % at 92 m, 34 % at 200 m, 81 % at 400 m | 0.006: 5.6 % at 40 m, 26 % at 92 m, 76 % at 200 m | `look.js:343`, `:79` |
| Haze tint by view direction (× the colour) | toward west [1.1, 1.04, 0.94], toward east [0.93, 0.98, 1.06] | toward west [3.1, 1.5, 0.68] (the city glow), toward east [0.72, 0.9, 1.22] (the moon side) | `look.js:377`, `:80` |
| Haze outside the bounds | Extra: starts 4 m past the bounds, 2 % of the scene left 105 m out (both rigs) | same | `look.js:84` |
| Sky dome | Day sky (2.16) | Night sky (2.16) | `atmos.js:285` |
| Image-based light | Day sky at × 0.6 without the sun disc, over stand-ins: facades [0.24, 0.18, 0.14], street [0.19, 0.17, 0.15] | Night sky over facades [0.03, 0.022, 0.02], street [0.02, 0.017, 0.016], plus a soft blob for each of the 48 strongest lamps (colour × 9 × kind factor) | `look.js:345`, `:138`; `src/atmos/sky.js:193` |
| Tone mapping | ACES filmic (three.js fit, scene × exposure / 0.6) | same | `look.js:12`, `src/render.js:408` |
| Exposure | 1.1 | 1.4 | `look.js:321`, `:13` |
| Bloom: strength / radius / threshold / knee | 0.16 / 0.42 / 2.4 / 0.6 ("only the sun, glints, muzzle flashes and chrome") | 0.4 / 0.62 / 1.05 / 0.4 ("emissive values above about 1 bloom, lit asphalt and brick never do") | `look.js:322`, `:14` |
| Vignette / grain / chromatic aberration / saturation | 0.12 / 0.008 / 0.0004 / 1.05 | 0.34 / 0.03 / 0.001 / 1.08 | `look.js:326`, `:18` |
| Inside the shop | exposure × 1.35 ("the eye opens up"), ambient × 0.62 and its sky colour toward `#d8d0c4`, haze × 0.5 | exposure × 0.86 ("the eye is on bright tungsten"), ambient × 0.62 toward `#a9a0a0`, haze × 0.5 | `look.js:346`, `:228` |
| Real lamp lights by kind (gain) | work 1, neon 0.35, street / el / flood / window 0 | all 1 | `look.js:348`, `:368` |
| Light pools, cones, fixture glows | hidden | shown | `look.js:349`, `:369` |
| Sign glow / neon glow / window layer glow | × 0.3 / × 0.55 / × 0 | × 1 / × 1 / × 1 (window layer emissive 1.6) | `src/mats.js:159` |
| Lit glass (`glass_lit_*`, `glass_car_lit`) | glow 0: dark glass | glows | `mats.js:122` |
| Street | dry; wet only in the hydrant's reach (2.6); ground albedo switches to the day colours | soaked | `mats.js:334` |
| Car paint and car glass reflections | × 1 | × 0.4 (lamp blobs of the single capture would float on the bodies) | `mats.js:100` |
| Far city sheet / skyline | sunlit sheet × [1.08, 1.05, 1.02]; no window glow; skyline sunk 36 % / 56 % into the haze; no lights | dark sheet × [0.952, 0.918, 0.935] (wall 0.56 × window gain 1.7); skyline window gain 1.275; sunk 50 % / 74 %; switching windows, aviation lights, traffic, plane | `look.js:350`, `:370` |
| Train windows | emissive × 0.1, no stripes on the road | emissive × 1, stripes | `look.js:351`, `:371` |
| Steam | colour [0.82, 0.83, 0.86] (sunlit white), opacity × 1.25 | tinted by the lamps near each column, opacity × 1 | `look.js:352`, `:372` |
| Hydrant spray | [0.85, 0.92, 1.0] | [0.1, 0.12, 0.14] | same |
| Moths and dust motes / pigeons | off / on | on / off | same |
| Effects (2.23) | additive × 2.4, tracers × 2.2, both get a dark body; darker blast soot; screen flash × 0.3 | as authored | `src/fx/particles.js:166`, `src/fx/tracers.js:126` |

Notes. The `shadowRadius` constants (1.2 by day, 2.5 at night: `look.js:335`, `:103`) have **no effect**: the renderer
uses the fixed-kernel soft filter (`src/render.js:412`), which ignores the radius, so shadow softness is about two texels
in both rigs. Lamp lenses, tail lights and other self-lit props are not part of the switch: they keep their night
values by day (2.17). The viewmodel has its own two lights (hemisphere `#8fa4cc` / `#4a3626` × 3.5, key `#ffc890`
× 2.6 along the night key's direction: `look.js:109`), which the weapon retunes by day (weapon spec).

### 2.16 The sky domes

Both skies are shaders on a box drawn at the far plane, rotating with the camera only.

**Day sky** (`daySky`, `src/config/look.js:300`; `src/atmos/daysky.js:70`).

| Element | Value |
|---|---|
| Gradient | horizon [0.62, 0.74, 0.92] → zenith [0.085, 0.2, 0.62], mixed by (sine of elevation)^0.5 |
| Sun disc | radiance [60, 54, 44], angular radius 0.0105 rad (0.60°, 2.3 × the real sun), hard edge, hidden behind clouds |
| Aureole | wide: [0.42, 0.33, 0.2] × cos(angle to the sun)^6 × (0.6 + 0.4 × (1 − sine of elevation)); tight: [1.4, 1.1, 0.7] × cos^90 |
| Clouds | Cumulus on one flat layer: big rounded heaps with cauliflower detail at the rim. Coverage threshold 0.6, edge softness 0.2, scale 0.62, drifting (0.006, 0.0018) layer units per second (east and a little south: one heap takes minutes to cross). Sunlit side [1.9, 1.86, 1.78], undersides [0.5, 0.56, 0.68]; thick parts 45 % greyer; a silver lining toward the sun; far clouds sink into the horizon colour × 1.15. Measured cover: 3 … 30 % of the sky above 3° depending on the moment, about a fifth on average **(measured with an emulation of the shader)** |
| Horizon | Below about 5° of elevation the sky blends into the haze colour × its directional tint (the dome is also the "ground" beyond the world) |
| For the image-based light | Captured once at 0.6 × brightness with the disc removed |

**Night sky** (`sky`, `look.js:44`; `src/atmos/sky.js:75`).

| Element | Value |
|---|---|
| Gradient | horizon [0.011, 0.0135, 0.025] → zenith [0.0032, 0.0058, 0.0145], mixed by (sine of elevation)^0.42 |
| City glow | Hugs the horizon: [0.3, 0.115, 0.03] in the west (toward Manhattan) fading to [0.034, 0.026, 0.03] elsewhere; e-folding height 0.14 (sine of elevation) in the west, 0.07 elsewhere |
| Moon | Toward (0.86, 0.29, 0.42): elevation 16.9°, bearing 116.0° (east-south-east, "down the avenue"). A gibbous disc of angular radius 0.017 rad (0.97°, 3.7 × life size), radiance [2.5, 2.35, 2.0], maria mottling, limb darkening, a soft halo (0.22) |
| Stars | A sparse field (0.16 % of cells), brightness 0.55, twinkling at 1.3 … 5.3 rad / s, only above about 6° and washed out by the glow |
| Clouds | Thin wisps: amount 0.75, scale 1.15, stretched (0.5, 1.5) along the avenue, drifting (0.011, 0.0035); lit from below by the glow (× 0.42) and by the moon [0.012, 0.016, 0.026], brightest around the moon |
| Horizon | As by day, into the night haze |

### 2.17 Lamps: the level's list, how each kind is drawn, the real lights

The level registers **90 lamp hints** **(measured)**; the atmosphere adds 40 virtual ones outside the bounds (30 El
lamps every 10 m out to 150 m, 10 street lamps every 31 m). A hint is {position, colour, intensity in game cd, range,
kind, priority, optional aim} (`src/level/kit.js:571`; default priority by kind: work 10, flood 9, street 6, el 5,
neon 4, window 2, `kit.js:54`).

| Group | Count | Kind | Colour | Intensity / range | Where (x, y, z) |
|---|---|---|---|---|---|
| Lamps hung under the El deck | 9 | el | sodium `#ffb45e` | 30 / 13 m | y 5.5; x −40 … 40 every 10 m, z alternating +2.1, −2.1 (starting +2.1); shade cone, aimed down (`src/level/el.js:148`) |
| Station platform tubes | 6 | el | cool `#cfe4ff` | 10 / 9 | (−43.5 / −38 / −32.5, 9.9, ±5.4), priority 2 |
| Station stair globes | 2 | neon | green `#55ff8a` | 6 / 6 | (−38.54, 3.15, ±8.15) |
| Station mezzanine windows | 1 | window | `#ffc98a` | 8 / 7 | (−38.8, 5.3, 0) |
| Cobra-head street lamps | 9 | street | sodium `#ffb45e` | 90 / 20 | Head 7.75 m up, 2.16 m from the pole. North kerb poles x −22.4, 2.6, 23.9, 41.6 (heads at z −9.78); south kerb x −31.4, 22.9, 36.4 (z 9.78); lot (39.3, 7.6, 16.11), (30.9, 7.6, 31.29) (`src/props/street.js:374`) |
| Storefront sign lamps | 10 | neon | the sign's glow: `#cfe4ff` laundromat, `#ff3030` barber, `#ffd24a` deli, `#55ff8a` checks, `#ff5a3a` pizza, `#f6c21a` pawn, `#35e0ff` records, `#ffc84a` chicken, `#ff3030` liquor, `#ff3d9a` nails | 12 (neon signs) or 9 (box signs) / 9 | (sign x, 3.25, ∓10.3) (`src/level/buildings.js:147`) |
| Lit shop interiors | 4 | window | cool `#cfe4ff` laundromat; warm `#ffc98a` deli, pizza, chicken | 10 / 9 | (sign x, 1.9, ∓9.5) |
| Other windows | 8 | window | `#ffc98a`, `#ffc48a`, `#dfe8ff` | 6 … 14 / 4.5 … 8 | Residents' door transom, pawn vestibule, produce stand, lot booth, three phone booths, bus shelter |
| Service-door bulkheads | 6 | street | warm `#ffc98a` (4), cool `#cfe4ff` (2) | 14 / 8 | 2.3 m up over each back door (`buildings.js:233`) |
| Garage lamps | 3 | street | `#ffb45e` | 18 / 10 | (−7.1 / 6.1 / 19.3, 3.0, 30.6) |
| Shop high-bay work lights | 4 | work | `#ffc48a` | 34 / 13 | (−18.2, 5, −17.2), (−9.2, 5, −22.4), (−9.2, 5, −14.6), (0.6, 5, −21.2), aimed down (`src/level/shop.js:295`) |
| Shop: office tube, under-mezzanine tube, side-door lamp, three fascia goosenecks | 6 | work, work, street, street | `#fff1d0`, `#cfe4ff`, `#ffc48a` | 14 / 8, 8 / 6, 16 / 9, 16 / 10 | (−20.6, 5.0, −28.8), (−20, 2.4, −30.2), (6.5, 2.85, −22.1), (−21.5 / −12 / −1.3, 6.2, −10.28) |
| Shop signs and machines | 4 | neon | `#f6c21a`, `#ff3030`, `#9fd4ff` × 2 | 14 / 10, 4 / 4, 12 / 5 | V&R sign (−12, 5.4, −10.2), EXIT (5.3, 2.85, −22.1), vending machines (4.5, 1.2, −13.3) and (3.4, 1.35, −9.95) |
| Cage flood masts | 2 | flood | `#dfe8ff` | 160 / 30 | (25.6, 8.5, −12.95), (44.8, 8.5, −32.3), aimed down (`src/props/lot.js:81`) |
| Billboard floods | 2 | flood | `#fff1d6` | 40 / 12 | (38.5, 7.1, 13.0), (42.9, 7.1, 13.0), aimed (0, 0.9, −0.44) |
| Floodlight stands | 3 | work | `#fff1d0` | 60 / 14 | Vacant lot (−9.6, 2.0, 13.05) aimed north at the hoarding; west closure (−44.9, 2.0, −2.9) aimed west; roadblock (44.45, 2.15, 7.9) aimed east |
| Shed bulbs, shanty lamp, food cart | 5 | work | `#fff1d0`, `#ffd9a0` | 9 / 7, 16 / 6 | (2.6 / 8.52 / 14.44, 2.45, 9.2), (−16, 2.5, 8.2), (−5.5, 1.85, −8.2) |
| IPX truck: two headlights, rear-door lamp | 3 | work | `#fff0d0`, `#fff1d6` | 22 / 9, 26 / 9 | (45.3, 0.9, 29.02 / 30.38) aimed east and down; (37.5, 2.46, 29.7) |
| Lot: booth lamp, `PARK` sign, bus-shelter ad | 3 | neon | `#f6c21a`, `#35e0ff`, `#dfe8ff` | 6 / 4, 12 / 9, 12 / 6 | (27.3, 0.6, 13.55), (34.65, 4.7, 11.65), (27.8, 1.45, −7.85) |

Totals by kind: el 15, window 13, neon 19, street 22, work 17, flood 4.

**How a lamp is drawn at night** (`lamps.kinds`, `src/config/look.js:176`). Every lamp gets a pool of light on the
ground and a glow at the fixture; some get a cone. In the web game these three are additive fakes; only a handful of
lamps carry a real light at any time (3.4).

| Kind | Reference cd | Pool radius (× range, clamped) | Pool brightness | Glow radius, core, halo | Cone half-angle, gain | Real light: gain, spot half-angle, penumbra |
|---|---|---|---|---|---|---|
| street | 90 | 0.36, 4.5 … 8 m (7.2 m for a cobra head) | gain 1, cut by the key light's shadows | 1.5 m, 5, 0.34 | 37°, 0.03 | 1.3, 76°, 0.7 |
| el | 30 | 0.34, 3 … 5 m (4.4 m) | gain 1.2, not shadowed | 0.95 m, 4.2, 0.3 | 34°, 0.028 | 1.5, 76°, 0.7 |
| work | 34 | 0.4, 3.5 … 6.5 m | gain 1.5 | 0.7 m, 4.5, 0.22 | none | 3.4, 76°, 0.7 |
| flood | 160 | 0.36, 7 … 13 m (10.8 m) | gain 3.4, hard edge 0.75, cap 0.5, shadowed | 2.7 m, 9, 0.4 | 30°, 0.02, length 0.95 × range | 1.7, 52°, 0.28 |
| neon | 12 | 0.5, 3 … 5.5 m, an ellipse 1.7 × longer along the wall, lying in front of it | gain 4.5, cap 0.3 | 2.6 m, no core, 0.035 | none | 1.4, 86°, 0.8 |
| window | 10 | 0.5, 2 … 4 m, in front of the wall | gain 0.8 | 1.2 m, no core, 0.08 | none | 1.0, 86°, 0.8 |

Pool brightness at its centre = min(0.05 × gain × intensity / drop², cap or 0.4) × lamp colour, drop = height above the
surface it lights (at least 2 m): 0.078 under a cobra head, 0.060 under an El lamp, 0.10 under a shop work light,
0.38 under a cage flood, 0.28 in front of a neon sign **(derived)** (`src/atmos/lampfield.js:188`). Pools are never an
even disc (a 0.62 … 1.0 noise at 2.4 m and 0.4 m scales) and keep 22 % inside a shadow of the key light. On top, one
faint "sheen" of street light `#f0b888` × 0.02 covers the whole block and is cut by the key's shadows, so near-black
asphalt still carries the stripes of the El and the shadow of whoever stands on it (`look.js:161`). Glows never
shrink below 0.0035 rad, so far lamps stay points of light. Two "tired" sodium lamps (chosen by the seed among
street and El lamps of priority under 6) buzz and drop out (3.6).

**Self-lit lenses** (unlit materials at HDR brightness, the same by day and by night; `mats.emissive`,
`src/mats.js:506`):

| Lens | Colour × intensity |
|---|---|
| El lamp bulbs; cobra-head lenses | sodium `#ffb45e` × 5; × 4.5 |
| Shop high-bay bulbs; fascia goosenecks; side-door lamp | `#ffd9a8` × 6; `#ffc48a` × 4.5; × 4 |
| Station tubes; station stair globes; barber pole | `#cfe4ff` × 3.2; `#55ff8a` × 3.5; `#f4f2ec` × 2.2 |
| Service-door lamps; garage lamps; vestibule; produce-stand bulbs | warm `#ffc98a` or cool `#cfe4ff` × 4; `#ffb45e` × 4; × 3; × 4 |
| Shed and shanty bulbs; office tube; floodlight-stand lens | `#fff1d0` × 3.5; × 3; × 5 |
| Cage flood lenses; billboard lamp strips | `#dfe8ff` × 6; `#fff1d6` × 3.2 |
| Bus shelter strip; phone booth head | `#e9f1ff` × 2.2; × 1.4 |
| Vehicles | headlights on `#fff0d0` × 3.2, off `#cfd8e0` × 0.2; tail `#ff1a10` × 0.6 (IPX truck 1.0, box truck markers 1.2); amber `#ff8a1a` × 0.5; marker `#ffa030` × 1.6; taxi roof `#ffd24a` × 1.15; IPX truck hazards `#ff8a1a` × 3.4 |
| Master-reel case | progress bar `#f6c21a` × 3.2; tracker LED `#3dff7a` × 3; beacon lamp `#f6c21a` × 3 |

### 2.18 The city beyond the bounds

Everything past the player-only walls is the atmosphere's (`src/atmos/farcity.js`, plan in `src/atmos/plan.js:274`).
All of it is unlit and fogged by the haze.

| Layer | Facts |
|---|---|
| The next blocks | 66 buildings, 4,024 triangles **(measured, seed 1994)**: terraces of walk-ups 3 to 6 bays wide (bay 3.2 m), 14 … 19 m deep, ground storey 4.1 m, upper storeys 3.1 m, a 0.6 … 1.4 m parapet. Rows: both sides of the avenue for 130 m past each end (10 … 20 m tall); the backs of the next row across a 4 m alley behind the north and south edges (11 … 20 m); a taller row 40 … 58 m behind that (17 … 30 m, medium quality and up); the fronts across the two cross streets (10 … 22 m). Cross streets 14 m wide, centred 10 m outside each end of the block and 78 m further out |
| Their faces | One shared sheet of 8 bays × 8 rows: a ground row of roll-down gates (60 %) and open shop fronts (40 %) under coloured sign bands (`rgb(255,70,150)`, `(60,220,255)`, `(255,196,60)`, `(255,60,50)`, `(90,255,150)`, `(245,240,225)`), six window rows with stone lintels and sills, sash bars, the odd blind, curtain and air conditioner (14 %), 20 % of windows lit at night (tungsten, kitchen fluorescent, television blue, red curtain), and a row of bare brick for party walls and parapets. Fronts on the avenue or a cross street get the shop row; backs get plain windows; side walls are blank |
| Wall colour | Four brick tints multiplying the sheet: (1.0, 0.74, 0.64), (0.92, 0.84, 0.72), (0.74, 0.74, 0.78), (0.84, 0.66, 0.6); by night brighter at the foot (street light) and cooler toward the top; by day a sunlit sheet (brick `rgb(140,96,80)`, pale mortar and frames, glass that mirrors the sky) shaded per face: 0.5 ambient + 0.12 sky + 0.62 sun facing, 14 % darker at street level |
| Roofs | Tar `(0.36, 0.34, 0.36)`; water towers on 16 … 40 % of the buildings by row (eight-sided tank radius 1.55 m × 3.1 m on 2.4 m legs with a 1.1 m cone, scale 0.85 … 1.15); stair bulkheads 3 × 4 × 2.3 … 3 m on 60 %; chimneys 0.7 × 0.7 × 1.5 … 3 m on 40 % |
| Ground | Asphalt 460 m out in every direction, 6 cm below the level's; sidewalks 4.5 m wide along the avenue to 150 m; the El carried on to 150 m past both ends (deck slab, two girders, rails, a column pair and cross girder between every two lamps) |
| Skyline, near ring | Radius 215 m, 72 m tall, one strip repeated three times round: a roof line of blocks (base 20 % of the height, variance 42 %), roof tanks and masts. Night body `rgb(15,16,22)` with 20 % lit window dots (72 % warm, the rest cool; offices leave whole floors on); day body sunlit stone `rgb(124,104,96)` with darker glass |
| Skyline, far ring | Radius 395 m, 118 m tall, wraps once, with a cluster of towers in the west ("the far downtown", under the glow). Night body `rgb(19,20,28)`, 26 % lit; day `rgb(112,120,136)`. Medium quality and up |
| Sunk into the haze | Near ring 50 % at night, 36 % by day; far ring 74 % / 56 %; 30 % more of the remainder at street level |
| Aviation lights (night) | Red [1, 0.05, 0.03]: up to 5 on the tallest tops of each ring (size 2.4 m, 70 % of them blinking with a 1.6 … 2.6 s period, half on) and 4 on the tallest near roofs (size 1.1 m, period 1.8 … 2.8 s). 13 at the default seed |
| Far traffic (night) | 5 cars as pairs of glows 1.5 m apart, 0.75 m up, on the cross streets (x = ±56 and ±134, ± 2 m), driving north or south at 7 … 12 m / s over a 240 m stretch, one pass every 26 … 60 s; white [1, 0.92, 0.74] or red [1, 0.06, 0.04] |
| A plane on approach (night) | Every 85 s: three lights (a white strobe 0.09 s every 1.3 s, a red beacon, a steady white) crossing 1,100 m at 46 m / s, about 170 m up and 290 m west of the block, heading south-east and descending 3.5 % |
| Switching windows (night, medium and up) | 22 dark windows on faces that look at the block switch on and off: each re-rolls every 7 … 26 s and is on 45 % of the time; 75 % warm [1, 0.66, 0.3], 25 % television [0.3, 0.45, 1.0], flickering |

### 2.19 Street life

| Thing | Facts | Source |
|---|---|---|
| Steam columns | At the 6 `level.steam` points **(measured)**: manholes (−22.5, −1.8), (6.4, −2.4), (30.5, −0.9); the alley grate (8.5, −24.6); the rear-lane grate (1.8, 28.4); the striped vent stack over the dig (19.5, 3.85, −8.1). Each: 11 soft puffs (60 % of them at `low`), rising 6.2 m in 4.96 s (fast out of the grate, slowing), drifting 1.5 m sideways, growing from 0.55 m to 2.6 m radius, opacity 0.2, never opaque within 0.6 … 2.4 m of the camera. Colour: day [0.82, 0.83, 0.86]; night [0.2, 0.18, 0.17] plus the light of lamps within 14 m. Leans west with a 1.1 m / s breeze. On top of each column the effects system runs a `steam` emitter (2.25) | `src/config/look.js:277`, `src/atmos/life.js:28` |
| Open hydrant | 260 droplets in a ballistic arc from the nozzle (−12.25, 0.5, 7.12) heading north: 5.2 m / s out, 1.56 m / s up, ± 7 % spread, landing about 2.7 m out after 0.52 s; two low mist columns where it lands (3.2 m and 1.8 m out, 1.5 m tall, opacity 0.1 and 0.06) | `look.js:280`, `life.js:209`, `:551` |
| Moths and dust (night, medium and up) | Around the 8 brightest open-air lamps: 13 points each, 6 of them moths (orbit radius 0.25 … 0.9 m, 2.2 … 5.5 rad / s, 0.25 m under the lamp), 7 dust motes (0.4 … 2.2 m, 0.08 … 0.3 rad / s, 0.6 … 3.2 m below); 1 … 3.5 px points in the lamp's colour × 1.5 | `look.js:278`, `life.js:136` |
| Loose paper | 7 newspaper sheets 0.22 × 0.30 m on the avenue. A steady draught (−1.1, 0.25) m / s moves only what is already loose (15 %); a gust of 2.2 … 3.6 m / s down the avenue (either way, ± 0.5 rad) every 5 … 13 s for 1.6 … 3.2 s lifts anything; a passing train adds 3.2 m / s along its direction within 8 m of the track. Above 1.1 m / s a sheet lifts (up to 0.28 m) and tumbles; it slides along cars and walls, and re-appears elsewhere if wedged for 6 s out of sight (25 m) | `look.js:279`, `life.js:304` |
| Pigeons (day) | 20 birds in three loose flocks wheeling over the roofs: 9 around (−8, 0) at 15 … 24 m, radius 9 … 22 m; 6 around (36, 20) at 18 … 30 m, radius 6 … 14 m, the other way round; 5 around (−71, −30) at 24 … 34 m, radius 10 … 18 m. 0.16 … 0.26 rad / s, orbits flattened to 55 … 80 % north-south, bobbing ± 1.6 m; wings flap at about 15 … 19 rad / s in bursts and glide in between. Body 0.46 m, wingspan 0.75 m, near-black silhouettes [0.035, 0.036, 0.04] | `look.js:281`, `life.js:444`, `:581` |
| Neon hum | Every neon sign ripples ± 3 % and ± 2 % at two rates (9 … 15 rad / s); a "tired tube" stutter exists (3.6) | `src/mats.js:791` |
| Tired lamps | Two sodium lamps buzz and drop out (3.6) | `look.js:222` |
| The train | 2.20 | |

### 2.20 The El train

Constants (`train`, `src/config/look.js:252`) and the level's track (`src/level/layout.js:30`).

| | Value |
|---|---|
| Consist | 5 cars of 15.4 m with 0.7 m gaps: **79.8 m** nose to tail |
| Car | 2.9 m wide, 3.55 m tall above the rail top; floor 0.42 m above the rail; flat sides to 3.29 m, then roof shoulders set in 0.42 m; underframe box and two trucks 2.5 m long, 2.2 m wide, centred 2.5 m from each end (`src/atmos/train.js:53`) |
| Livery (painted sheet) | Brushed steel `rgb(118,123,130)`, fluted lower panels, a dark skirt, a blue belt line `rgb(24,40,96)`, grime heavier toward the bottom. Four door pairs per side at 11.5 %, 37 %, 63 %, 88.5 % of the length, 1.31 m wide; window band 1.80 … 2.72 m above the rail; an end door between two windows with an amber destination bar `rgb(255,150,30)`. No operator name, no logo (`src/atmos/textures.js:292`) |
| Material | Roughness 0.42, metalness 0.55; window glow [1.9, 2.05, 1.75] ("cool fluorescent interior") × 1 at night, × 0.1 by day; grab poles and the odd rider silhouetted in the windows |
| Lights | Two headlights (radius 1.7 m glows, core 9, colour [1, 0.96, 0.82]) and two tail lights (red [1, 0.05, 0.03], core 5) 0.85 m either side of the centre line, 1.2 m above the rail |
| Rail top | y = 6.83 m; tracks at z = ±2.1 m; the deck's underside is at 6.5 m |
| Speed | 16.5 m / s (59.4 km / h) |
| Direction | First pass eastbound on the south track (z = +2.1), then alternating: westbound on the north track |
| Appears / vanishes | 145 m outside the bounds, "deep in the haze" (x = ∓191 for the nose) |
| Timeline of a pass **(derived)** | Approach 8.79 s (nose reaches the block), over the block 10.41 s (until the tail has left), gone 8.79 s (until it vanishes): 27.99 s in all |
| Schedule | First pass starts at 11.21 s so the nose is overhead 20 s after boot; every later pass starts 40 … 70 s after the previous one started (seeded) |
| Strobe under the deck | While any of the train is within 30 m of the block and within 60 m of the camera along the street: a pooled point light every 0.1 … 0.34 s (never two at once), cool white `#d9e8ff`, 26 … 60 game cd, range 17 m, fading over 0.07 … 0.16 s, placed under the deck (y 6.05) within ± 15 m of the camera along the train and ± 1.3 m of its track |
| Third-rail arcs | 22 % of those flashes: blue `#8fc4ff`, 130 game cd, 0.07 s, with 6 sparks falling |
| Grit | Every 0.16 … 0.42 s a dust puff (scale 0.5 … 1.1) falls from under the deck (y 6.2) within ± 26 m of the camera; plus 150 faint specks falling the 6.25 m in 1.4 … 2.4 s under the train |
| Stripes (night only) | Window light through the ties on the roadway under the train: [0.086, 0.092, 0.079] in bars every 0.62 m, grouped five panes to a car, dark between cars, a Gaussian 2.7 m either side of the track, flickering ± 14 % |
| El lamps | Lamps hung under the deck dim by 28 % ± 24 % (43 rad / s) while a car is over them |
| Camera shake | 0.42 trauma per second right under it, fading to nothing 14 m along the street from the train and 15 m to the side of the deck; only while playing |
| Sound (`src/audio/ambience.js:154`) | Event `train:pass` with phase `approach`, `over`, `gone` and that phase's duration. On `approach`: two loops start at the nearest point of the train to the listener: `train_rumble` (low roar) fading 0.2 → 1.0, `train_clack` (wheels on joints, pitch × speed / 16.5) fading 0 → 1. During `over`: full volume; on 70 % of passes one `train_squeal` (3.2 s flange squeal) at 20 … 60 % of the phase. On `gone`: both fade to 0. The ambience and music buses duck to 72 % while it is over |

### 2.21 Post chain and screen feedback

The chain (`buildPost`, `src/render.js:587`). Everything up to the output step works on linear, scene-referred colour
in a half-float buffer.

| Step | What | Detail | Source |
|---|---|---|---|
| 1 | World | The scene into the HDR target with depth and MSAA (2.22). Camera near 0.08 m, far 700 m, vertical field of view from the setting (default 74°) | `src/render.js:417`, `:591` |
| 2 | First-person weapon | Its own scene and camera (54°, near 0.01 m, far 10 m) into the same target after clearing depth only. It has its own two lights (2.15) and never receives the world's | `src/render.js:353`, `:423` |
| 3 | Bloom | On the image **before** exposure. Bright pass: weight = smoothstep(threshold, threshold + knee, luminance). Five half-resolution levels (each half the size of the last, Gaussian kernels 3, 5, 7, 9, 11 texels), summed with factors mix(f, 1.2 − f, radius) for f = 1.0, 0.8, 0.6, 0.4, 0.2, times `strength`, added to the image | `src/render.js:616`, `:666`; three.js r160 `UnrealBloomPass` |
| 4 | Grade | One full-screen pass, in the order of the next table | `src/render.js:60` |
| 5 | Output | ACES filmic tone mapping (the three.js r160 fit, which multiplies its input by 1 / 0.6 first), then sRGB encoding, stretched to the canvas | `src/render.js:408`, `:624` |

Order inside the grade (`src/render.js:107`). `d` is the distance from the screen centre, 0 in the middle and 1 in the
corners.

| # | Operation | Formula |
|---|---|---|
| 1 | Chromatic aberration | red is read at uv + s, blue at uv − s, green at uv; s = (uv − 0.5) × d² × aberration × 2 |
| 2 | Exposure | colour × (`render.exposure` × `look.exposure`); `render.exposure` is the interior blend (3.3) |
| 3 | Saturation | toward the Rec. 709 luminance by sat = `post.saturation` × `look.saturation` × (1 − 0.65 × lowHealth) × (1 − 0.5 × damage) |
| 4 | Vignette | colour × (1 − min(v, 1) × smoothstep(0.3, 1, d)), v = `look.vignette` + 0.55 × lowHealth + 0.22 × ads |
| 5 | Red edge | rim = smoothstep(0.5, 1.08, d); red = damage × rim × 0.85 + lowHealth × rim² × 0.55 × (0.75 + 0.25 × sin(5 t)); colour mixes toward [0.3, 0.008, 0.006] by min(red, 1) |
| 6 | White-out | colour mixes toward [2.2, 2.2, 2.2] by flash² |
| 7 | Fade | colour × (1 − fade) |
| 8 | Grain | + (hash − 0.5) × grain × (0.08 + 0.9 × luminance) × (1 − fade), a new pattern every frame |

Who drives the feedback values (all 0 … 1; constants `feedback`, `src/config/look.js:25`):

| Value | Driver | Source |
|---|---|---|
| `damage` | Each hit on the player adds 0.35 + damage / 40 (capped at 1); it then falls 1.9 per second | `src/config/player.js:88`, `src/player.js:354`, `:432` |
| `lowHealth` | Target 1 − smoothstep(0.12, 0.55, health fraction), 1 when dead; approached at rate 4 / s (exponential) | `src/config/player.js:89`, `src/player.js:635` |
| `ads` | The weapon's aim blend, 0 at the hip to 1 fully aimed | `src/weapon/logic.js:588` |
| `flash` | A close blast: near² × 0.6 × min(1.2, blast scale), near = 1 − distance / (16 + 8 × scale); × 0.3 by day; decays as e^(−7 t) | `src/fx.js:464`, `:604` |
| `saturation`, `fade` | The game flow: death eases saturation to 0.12 (rate 2.2 / s) and fade to 0.55 (1.4 / s); mission complete to 0.7 (1.4) and 0.72 (1.2); title, intro and resets set them directly | `src/config/flow.js:24`, `src/game.js:756` |

Fallback (no float render targets): no bloom and no grade; both scenes go straight to the canvas with ACES and
exposure × (1 − fade) × (1 + 3 × flash) (`src/render.js:680`). Clear colour `#04050a` (`src/config/look.js:38`).

### 2.22 Quality presets, detail layers, dynamic resolution

Presets (`src/config/quality.js:13`). The player's menu offers `low`, `medium`, `high`, `ultra`; `test` is for
screenshots in software rendering.

| | test | low | medium | high | ultra |
|---|---|---|---|---|---|
| Internal render scale | 1 | 0.7 | 0.85 | 1 | 1 |
| MSAA samples | 0 | 0 | 2 | 4 | 4 |
| Shadow map (one, square) | 1024 | 2048 | 2048 | 4096 | 4096 |
| Shadow map redrawn every n frames | 1 | 2 | 2 | 2 | 1 |
| Bloom | on | on | on | on | on |
| Real lamp lights (2.17) | 4 | 4 | 6 | 8 | 12 |
| Effect density `fx` (2.23) | 0.4 | 0.5 | 0.8 | 1 | 1 |
| Pixel budget per frame | 1.0 M | 1.0 M | 1.5 M | 2.3 M | 3.7 M |
| Device pixel ratio cap | 1 | 1.5 | 2 | 2 | 2 |
| Surface texture size per tile (`src/mats.js:146`) | 256 | 512 | 1024 | 1024 | 1024 |
| Light cones, moths and dust, the taller far rows, the far skyline ring, switching windows (`detail`, `src/config/look.js:285`) | off | off | on | on | on |
| Train grit | on | on | on | on | on |
| Steam puffs per column | 60 % | 60 % | 100 % | 100 % | 100 % |

Automatic choice at first boot (`autoDetect`, `src/config/quality.js:37`): a phone, a tablet or a small touch screen →
`low`; a software rasteriser → `low`; a mobile-class GPU or integrated Intel graphics other than Arc → `medium`;
anything else → `high`. `ultra` is never chosen automatically. Unknown names fall back to `medium`.

Internal resolution = canvas CSS size × min(device pixel ratio, cap) × preset scale × dynamic scale, then scaled down
again if it exceeds the pixel budget (`applySize`, `src/render.js:725`). Dynamic resolution
(`dynamicResolution`, `src/config/quality.js:55`; state machine in 3.14):

| Constant | Value | Meaning |
|---|---|---|
| `settle` / `settleAfterChange` | 3.5 s / 1 s | No measuring after boot, a new run, a resume, the first input / after any change |
| `windowFrames` / `windowMs` / `minFrames` | 45 / 900 ms / 5 | A measuring window; fewer usable frames decide nothing |
| `ignoreAbove` | 1500 ms | A hidden tab, not a frame |
| `hitchMs` / `hitchFactor` | 100 ms / 4 | A frame above max(100 ms, 4 × the running mean) is a hitch, not load |
| `trim` | 1 / 6 | Share cut from each end of a window before averaging |
| `slow` / `slower` / `slowest` | 21.5 / 30 / 45 ms | Mean above: one step down / two steps / straight to the minimum |
| `fast` | 17.4 ms | Mean below: one step up |
| `step` / `min` | 0.1 / 0.6 | Step and floor of the dynamic scale |
| `prove` / `capBand` | 0.08 / 0.1 | A step down must make the frame 8 % faster, or it is undone and held until the frame time moves by more than 10 % |
| `upWait` / `upWaitMax` / `upWaitDecay` | 2 s / 60 s / 45 s | Wait before stepping up; doubles after each step down; resets after 45 s without one |
| `dropAbove` / `dropScale` | 26 ms / 0.8 | Two windows in a row at the floor above this: one preset down, dynamic scale restarts at 0.8 |

### 2.23 Effects: pools, budgets and shared rules

Everything the effects system draws comes out of fixed pools (`src/fx.js:29`). Nothing is allocated during play.

| Pool | Size | Scales with `fx` | When full |
|---|---|---|---|
| Lit billboards: smoke, dust, steam, lint (sorted back to front) | 1,400 | yes | The most spent of 6 random probes is recycled; "soft" spawns (wisps, trails, steam, embers) are refused above 85 % (`src/fx/sim.js:58`, `:134`) |
| Additive billboards: flashes, sparks, flames, embers, glints | 3,040 | yes | same |
| First-person flash sprites | 32 | no | Only used when the weapon has no flash of its own: never in the shipped game |
| Tracers | 48 | no | Entries are overwritten in turn (`src/fx/tracers.js:25`) |
| Debris bodies (chips, splinters, fragments) | 256 | yes | Oldest overwritten |
| Shell casings | 60 | no | Ring buffer: a casing lies where it came to rest until its slot comes round again |
| Decals (bullet holes, scorch) | 256 | no | Ring buffer: the oldest mark disappears |
| Emitters | 24 | no | The finite emitter nearest its end is replaced; endless ones never (`src/fx/emitters.js:506`) |
| Pooled point lights (owned by the renderer) | 6 | no | A flash takes an idle light or the one closest to done; emitters may hold at most 4 (`src/render.js:35`) |
| Effect lights that shine on smoke | 4 | no | The 4 brightest of the frame (`src/fx/shared.js:6`) |

Shared rules:

| Rule | Value | Source |
|---|---|---|
| Density `k` | `fx` of the preset, clamped 0.25 … 1; halved beyond 55 m from the camera; 0 beyond 150 m. Counts in the recipes are multiplied by `k` and rounded at random so that the average is exact | `src/fx.js:37`, `:173`; `src/fx/sim.js:374` |
| Decals ignore `k` | A bullet hole or scorch mark is placed whatever the distance | `src/fx/recipes.js:465`, `:661` |
| Gravity | 9.81 m / s² | `src/fx/sim.js:55` |
| Wind on effects | (0.5 + 0.3 sin(0.31 t) + 0.12 sin(1.7 t), 0.2 + 0.22 sin(0.23 t + 1)) m / s toward east and south | `src/fx.js:49`, `:572` |
| Key shadow | A spawn point that cannot see the key light gets 12 % of it (one ray, 60 m) | `src/fx.js:41`, `:105` |
| Pooled flash | Point light, quadratic falloff to zero at its range, intensity falling linearly to 0 over its time | `src/render.js:514`, `:546` |
| Small flashes | A flash under 20 game cd that does not light smoke (impacts) is allowed once per 0.07 s | `src/fx.js:46`, `:221` |
| Flash distance | No pooled light further than 75 m from the camera | `src/fx.js:47` |
| Tracer smoke trail | At most one per 0.07 s | `src/fx.js:45` |
| Day blend | `uDay` eases between 0 (night) and 1 (day) at 3 / s when the rig switches | `src/fx.js:561` |
| Smallest sprite | 1.25 pixels at the internal resolution; tracers 1.6 px (2.2 by day) | `src/fx.js:566`, `src/fx/tracers.js:120` |
| Clock | Effects time stops while the game is paused | `src/fx.js:137` |

How the two billboard pools are shaded (`src/fx/particles.js`):

| | Lit pool | Additive pool |
|---|---|---|
| Light | albedo × (ambient blended ground to sky by the puff's own shading + key × wrap² × shade + up to 4 effect lights × (1 − 0.7 × day)) / π | none: colour × alpha is added |
| Self glow | `heat` × [2.2, 0.55, 0.07] × (1 − 0.35 × day) in the dense core, cooling at 6 / s (gone in half a second) | – |
| By day | Key = the sun: smoke reads as lit volume | × (1 + 1.4 × day) = 2.4 × hotter, and a dark "body" behind the glow of opacity day × min(0.6, 0.9 × strength), so fire and flashes hide the bright wall behind them instead of vanishing against it |
| Fog | Fogged like the scene | Dimmed by the fog |
| Soft edges | Fades out where it meets the ground; pulled 0.45 m toward the camera in depth so a puff on a wall is not cut by it | same depth pull |

Particle fields a recipe can set (`src/fx/sim.js:11`): position, velocity, life, size at birth and at death with a
curve exponent, rotation and spin, colour at birth and at death with a ramp exponent, peak opacity, fade-in fraction,
fade-out start fraction, drag (1 / s, toward the wind × the particle's wind share), gravity (in g, negative rises),
turbulence (m / s²), stretch (seconds of travel drawn as a streak, at most 45 × the size), sprite cell, floor height,
heat, shade, flags `BOUNCE` (keeps 25 … 55 % of the vertical and 65 % of the horizontal speed, rests under 0.45 m / s),
`DIE` (removed on the floor), `STICK`.

### 2.24 Effects: sprite sheets, the decal sheet, bullet holes

Three sheets of 4 × 2 cells, 128 px a cell, painted by pure functions (`src/fx/atlas.js:14`). They are the same on
every machine and can be re-rendered at any resolution; a photoreal port replaces them with flipbooks (5).

| Sheet | Cells |
|---|---|
| Lit (R density, G internal shading) | `smokeA`, `smokeB`, `smokeC`: lumpy rolling puffs, lit upper left; `wisp`: thin curling strands; `dust`: a soft grainy cloud; `steam`: very soft; `lint`: a scatter of specks and fibres; `roll`: a low ground-hugging roll |
| Additive (R intensity, G white-hot core) | `glow`: soft ball; `streak`: a tapered line; `star`: a four-to-six-point flash; `flameA`, `flameB`: ragged tongues; `ember`: a hot dot; `glint`: a thin cross; `ring`: a shock ring |
| Decals (RGB linear albedo, A opacity) | `stone`: a dark pit (22 % of the radius), a ragged crater of freshly broken material in chip colour [0.3, 0.29, 0.27] and a sooty powder halo; `brick`: the same with chip colour [0.34, 0.13, 0.08]; `metal`: a black hole (17 %), a rim of bare bright metal, flaked paint, a little soot; `glass`: a small hole, a crushed white ring, nine radial cracks joined by two rings; `wood`: a dark hole with pale splinters torn out along the grain; `soot`: a dark smudge with a small hole; `scorchA`, `scorchB`: burnt black heart, streaks thrown outward, a brown singed fringe |

Bullet hole by surface (`HOLE`, `src/fx/recipes.js:49`); the size is the diameter of the whole decal quad.

| Surface | Cell | Size (m) | Opacity |
|---|---|---|---|
| asphalt | stone | 0.24 … 0.34 | 0.95 |
| concrete | stone | 0.25 … 0.36 | 1 |
| brick | brick | 0.25 … 0.36 | 1 |
| metal | metal | 0.12 … 0.17 | 1 |
| car | metal | 0.12 … 0.18 | 1 |
| glass | glass | 0.30 … 0.46 | 0.9 |
| wood | wood | 0.15 … 0.22 | 1 |
| rubber | soot | 0.08 … 0.12 | 0.9 |
| dirt | soot | 0.20 … 0.30 | 0.8 |
| cloth | soot | 0.07 … 0.10 | 0.85 |
| flesh, drone, any body hit | none | – | – |
| any other surface name | none (dust, chips and grit only) | – | – |

Decal placement (`src/fx/decals.js`): a quad on the hit plane, rotated at random (wood: within ± 0.2 rad of the
grain), lifted 8 mm off a wall or 35 mm off a floor, depth-tested 7 cm + 0.3 % of its distance nearer than it is
drawn, lit by the ambient and by the key × the shade measured 0.2 m in front of the wall, fogged. Blast scorch:
`scorchA` or `scorchB`, 3.4 … 4.3 m × blast scale, opacity 0.92, on the ground under a blast whose centre is less
than 2.2 × scale + 0.6 m above it. When an explosive prop blows, marks within 1.3 m of it and at least 1 m above the
ground are removed (`src/fx.js:630`).

Dust and chip colours by surface (`DUST`, `CHIP`, `src/fx/recipes.js:18`, `:34`):

| Surface | Dust (lit puffs) | Chips (solid debris) |
|---|---|---|
| asphalt | `#8a857e` | `#3a3a3c` |
| concrete (and unknown) | `#b5b0a8` | `#8c8a84` |
| brick | `#a8674f` | `#7a3a2a` |
| wood | `#b09468` | `#9a7a4c` |
| dirt | `#8a6f4f` | `#4a3a28` |
| metal / car | `#8c8f96` | `#50545a` / `#44484e` |
| rubber | `#38383a` | `#121213` |
| glass | `#d8e2e6` | `#a8c0c8` |
| cloth | `#b9b6ae` | `#55524c` |
| flesh | `#9a6a64` | – |
| drone | `#4a4c52` | `#2a2c30` |

Other fixed colours: hot sparks [1, 0.78, 0.42] → [1, 0.33, 0.07]; electric sparks [0.62, 0.84, 1] → [0.28, 0.45, 1];
dark smoke [0.13, 0.125, 0.12]; pale smoke [0.5, 0.5, 0.52]; steam `#d9dde0` (`src/fx/recipes.js:72`,
`src/fx/emitters.js:24`).

### 2.25 Effects: the recipes

Counts are at `k` = 1. "Size a → b" is the billboard's diameter at birth and at death in metres; colours in brackets
are linear HDR values (additive) or albedo (lit).

**Muzzle flash, third person** (`muzzleFlash`, `src/fx/recipes.js:576`): what an enemy gun shows, and what a
spectator would see of the player's. `s` = the caller's scale. All flash parts live one draw of 0.036 … 0.056 s.

| Part | Count | Where | Size | Colour | Motion |
|---|---|---|---|---|---|
| Core | 1 glow | 0.05 m ahead of the muzzle | 0.3 s → × 1.5 | [3.6, 2.7, 1.5] | – |
| Star | 1 | 0.08 m ahead | 0.5 s × rand(0.8, 1.3) → × 1.5, random roll | [2.2, 1.5, 0.75] | – |
| Flame tongues | 2 streaks | 0.16 s and 0.32 s ahead | 0.2 s and 0.13 s wide, stretched 0.045 s seconds of travel | [2.4, 1.5, 0.6] | 7 m / s along the bore |
| Sparks | 3 | muzzle | 1.6 … 3 cm → half | hot sparks × 3.5 | cone 0.3 rad, 8 … 17 m / s, life 0.1 … 0.22 s, gravity, bounce |
| Smoke | 1 lit puff (`steam` cell, soft) | 0.2 m ahead | 0.1 s → 0.5 s | `#b5b0a8`, opacity 0.14 | 1.1 m / s forward + 0.35 up, life 0.45 … 0.75 s |

Callers: Goon rifle scale 0.7, with a light `#ff7a3c` 14 game cd, range 7 m, 0.05 s on every other shot
(`src/enemies/goon.js:628`); Buzzard scale 0.6, light `#ff3a22` 10 / 6 m / 0.05 s (`src/enemies/buzzard.js:637`).

**Muzzle flash, first person.** The weapon draws its own flash in the viewmodel (an object named `muzzle-flash`:
`src/weapon/viewmodel.js:73`), so the effects system only adds 2 sparks 0.3 m ahead of the muzzle in the world
(`src/fx.js:343`).

| | CHOPPER | NINE | Source |
|---|---|---|---|
| Shape | A star card facing the shooter plus two crossed cards along the bore (a jet seen from the side) | same | `viewmodel.js:73` |
| Star size / jet length | 0.20 m / 0.34 m | 0.12 m / 0.13 m | `src/weapon/chopper.js:278`, `src/weapon/nine.js:197` |
| Size per shot | × rand(0.8, 1.3) × (1 → 0.62 when aiming) | same | `src/config/weapons.js:197` |
| Life | rand(0.036, 0.056) s; brightness × √(life left / life) | same | `weapons.js:196` |
| Colour | edge [1, 0.42, 0.08] → core [1, 0.93, 0.74], × 9 | same | `src/weapon/material.js:210` |
| Side jet strength | 1 | 0.3 | `viewmodel.js:256` |
| Light on the weapon | point `#ffb060`, range 2.5 m, 1.5 game cd | 1.0 | `viewmodel.js:116` |
| Light on the world | `#ffb020`, 45 game cd, range 9 m, 0.05 s | `#ffb020`, 30 game cd, range 9 m, 0.05 s | `weapons.js:72`, `:145`; `src/weapon/logic.js:478` |
| Barrel smoke | After sustained fire (heat above 0.4): a pale wisp (`fx.smoke` scale 0.22) from the muzzle every 0.085 s for 1.6 s | – | `viewmodel.js:395` |

**Tracers** (`src/fx.js:360`, `src/fx/tracers.js`): one camera-facing ribbon per shot from muzzle to hit point.

| | Value |
|---|---|
| Colour × gain | player `#ffe2a8` × 8; Goon `#ff3a22` × 8 (2.2 × more by day) |
| Speed | 260 m / s for both (a 40 m shot is on screen for about 0.17 s) |
| Streak length | speed × 0.022 s, clamped 2 … 7 m: 5.72 m; it shortens and fades against its target |
| Width | 0.035 m, never thinner than 1.6 px (2.2 px and 1.5 × wider by day) |
| Head | The leading 0.9 m (at most 60 % of the streak) is the bright head; the tail tapers |
| Start | The first 1.1 m of the path is skipped when the path is longer than 3.3 m; shots shorter than 0.5 m draw none (the weapon also skips shots under 0.9 m: `src/weapon/logic.js:18`) |
| By day | A dark rim (opacity 0.55) round the bright core so it reads on a sunlit wall |
| Smoke thread | On paths of 4 m or more, at most once per 0.07 s: 5 pale wisps between 0.8 m and min(length, 7 m) from the muzzle, 0.05 → 0.16 … 0.26 m, life 0.5 … 0.9 s, opacity 0.09, drifting 0.6 m / s along the shot |

Buzzard bolts are not tracers: a red streak 2.4 m long, 0.11 m wide with a 0.34 m head, gain 9, flying at 70 m / s for
at most 1.3 s (`src/enemies/bolts.js:8`, `src/config/enemies.js:72`); see the enemies spec.

**Shell casings** (`src/fx/bits.js:117`): a seven-sided brass cylinder, `#c9a24a`, metalness 0.9, roughness 0.32.

| | Rifle (CHOPPER) | Pistol (NINE) |
|---|---|---|
| Length × diameter in the game | 58 mm × 17 mm | 27 mm × 17 mm |
| Note | "A third larger than life" so it reads; a real 7.62 × 39 case is 38.7 mm × 11.3 mm, a 9 × 19 case 19.2 mm × 9.9 mm | |
| Ejection (weapon's default) | from the ejection port: right × rand(2, 3.2) + up × rand(1.2, 2.0) + forward × rand(−0.5, 0.5) m / s + the player's velocity (`src/weapon/logic.js:430`) | same |
| Spin | up to ± 9, ± 22, ± 16 rad / s about three axes | same |
| Bounce | keeps 32 … 48 % of its vertical and 60 % of its horizontal speed; at most 4 bounces; comes to rest when the rebound is under 0.55 m / s; bounces off the first wall in its way | same |
| Sound cue | `shell:bounce` {position, surface under it} on the first touch | same |
| Lifetime | Stays until 60 newer casings have been thrown | same |

**Debris bodies** (`src/fx/bits.js:247`): faceted lumps (a distorted icosahedron scaled per axis), matt, in the chip
colour × rand(0.7, 1.15); gravity, wall bounce, keeps 30 … 45 % vertical and 55 % horizontal speed, at most 3 bounces,
shrinks away over the last 0.45 s of its life.

**Bullet impact by surface** (`impact`, `src/fx/recipes.js:443`). n = surface normal, r = the shot reflected about
it, m = normalise(0.6 n + 0.4 r): debris leaves along m, ricochets along r. Every strike on a surface with an entry in
2.24 leaves its hole first.

| Surface | What flies |
|---|---|
| asphalt, concrete, brick, unknown | Dust (`dustPuff` × 1, below); 2.6 chips 1.4 … 3.5 cm at 2 … 6 m / s; 3 grit specks (3.5 … 6 cm sprites, 3 … 7.5 m / s, life 0.3 … 0.55 s, chip colour × 0.6, die on the floor); with 45 % chance 1 or 2 ricochet sparks along r (cone 0.5 rad, 7 … 18 m / s, × 4, 0.12 … 0.3 s) |
| metal, car | 14 hot sparks along m (cone 0.85 rad, 5 … 18 m / s, × 4.5, 0.2 … 0.6 s, bounce); 2.5 ricochet streaks along r (cone 0.2, 22 … 34 m / s, × 6, 0.16 … 0.3 s); a glow 0.3 m for 0.05 s [3.2, 2.4, 1.3] and a star 0.42 m for 0.045 s [1.8, 1.3, 0.7]; one thin puff 0.06 → 0.4 m, opacity 0.3; on `car` also 1.2 paint chips 1.2 … 2.5 cm; a light `#ffc070` 6 game cd, range 5 m, 0.06 s, 0.7 m off the surface |
| glass | 12 glints (thin crosses 3.5 … 9 cm, [1.54, 1.98, 2.2], cone 1.1 rad, 1.5 … 6 m / s + 0.8 up, spin ± 14 rad / s, life 0.45 … 0.95 s, fall and die on the floor); dust × 0.7; 2 chips 1.2 … 3 cm |
| wood | 5 long splinters (0.8 … 1.6 cm thick, 3.5 … 6 × longer, 2.5 … 7 m / s); dust × 0.85 |
| rubber | One dark puff 0.08 → 0.45 m (0.4 … 0.6 s, opacity 0.5); 2.5 chips 1.2 … 3 cm |
| dirt | 5 clods 2 … 5 cm at 2 … 5.5 m / s; dust × 1.25 |
| cloth | `puff` × 1 along m (below) |
| flesh (a Goon) | `puff` × 0.9 in `#9a6a64`, thrown back toward the shooter: direction (−0.6 × shot + 0.4 × n) horizontally, 0.2 up. No decal. "Cloth dust and lint, a faint dark-red tint. Nothing wet, nothing left behind" |
| drone (a Buzzard) | 13 electric sparks along m (cone 1.0, 4 … 14 m / s, × 5, 0.15 … 0.45 s); 2 along r (cone 0.3, 16 … 26 m / s, × 6); a glow 0.34 m [1.6, 2.4, 3.4]; a dark wisp 0.1 → 0.6 m (0.6 … 0.9 s); 1.5 chips 1.5 … 3.5 cm; with 35 % chance 3 hot sparks (2 … 6 m / s, 0.5 … 1 s); a light `#9cc8ff` 7 / 5 m / 0.06 s. No decal |

**Building blocks** used above and callable on their own.

| Block | Recipe | Source |
|---|---|---|
| `dustPuff(scale)` | 2 puffs, a third with probability k − 0.5. Fast jet: 3.5 … 6 × √scale m / s along the normal, 0.1 → 0.6 × rand(0.85, 1.2) × scale m, life 0.3 … 0.45 s, opacity 0.7, drag 6. Slow cloud: 0.8 … 1.9 × √scale m / s, 0.16 → 0.95 × scale m, life 0.65 … 1.05 s, opacity 0.5, drag 3.2. Both swell fast then linger (curve 0.55), rise slightly, spin ± 0.9 rad / s. Never thinned out: "without them a hit on masonry does not read at night" | `recipes.js:248` |
| Hot spark | Streak 1.6 … 3 cm → half, colour → 40 % toward the end tint, fade from 55 % of its life, drag 1.3, full gravity, stretched 0.03 … 0.05 s of travel, bounces | `recipes.js:153` |
| `fx.sparks(pos, dir, n = 8)` | n hot sparks in a cone of 0.6 rad round `dir` (or 1.9 rad round straight up without one), 4 … 15 m / s, × 4.2, 0.25 … 0.7 s; a glow 0.22 m for 0.05 s [2.6, 1.9, 1.0] | `recipes.js:344` |
| `fx.smoke(pos, scale)` | scale under 0.35: one pale wisp 0.25 s → 1.1 … 1.6 s (s = scale), life 0.7 … 1.2 s, opacity 0.2, rising 0.25 … 0.5 m / s. Otherwise 3 dark rolling puffs 0.3 s → 1.0 … 1.5 s, life 1.3 … 2.3 × √s seconds, opacity 0.55, rising 0.5 … 1.2 m / s | `recipes.js:359` |
| `fx.dust(pos, scale)` | 3 pale puffs (`#b5b0a8`) 0.25 s → 0.8 … 1.2 s, life 0.8 … 1.3 s, opacity 0.32, spreading ± 0.9 m / s, kept above the ground | `recipes.js:396` |
| `fx.puff(pos, colour, scale)` | A dust puff 0.08 → 0.42 × scale m (0.35 … 0.55 s, opacity 0.5) at 1.6 m / s along the normal, plus lint and grit 0.12 → 0.5 × scale m (0.3 … 0.5 s, opacity 0.85) at 2.6 m / s that falls (gravity 0.25 g) | `recipes.js:424` |
| `fx.debris(pos, n = 6, colour, speed = 5)` | n lumps 3 … 9 cm (up to twice as long), thrown out 0.3 … 1 × speed and up 0.4 … 1.1 × speed, life 1.8 … 3.4 s | `src/fx.js:481` |
| Landing dust | When the player lands faster than 2.5 m / s: 3 + 4 × strength puffs in a ring at 1.2 … 2.4 × (0.6 + strength) m / s, 0.2 → 0.6 … 0.95 × (0.7 + 0.5 × strength) m, life 0.55 … 0.9 s, opacity 0.16 + 0.14 × strength, in the dust colour of the surface. strength = 0.1 below 5 m / s, else clamp((speed − 5) / 6 + 0.4, 0.4, 1) | `recipes.js:941`, `src/fx.js:634` |

**Explosion** (`explosion`, `src/fx/recipes.js:651`). s = blast scale = clamp(blast radius / 6.5, 0.4, 1.6), then
clamped 0.25 … 2.5 (`src/fx.js:453`, `:621`): propane tank (radius 6.5 m) s = 1; welding rack (7.5 m) s = 1.15; a
Buzzard's burst (3 m) s = 0.46 with the `drone` flavour. The centre is lifted to at least 0.35 s above the ground.

| Part | Count (drone) | Motion | Size a → b (m) | Colour | Life (s) |
|---|---|---|---|---|---|
| Light | 1 pooled point light, `#ffa040`, 120 × s^1.5 game cd, range 10 + 8 s m, 0.36 s, 0.5 s above the centre; it also lights the smoke for 0.58 s | – | – | – | – |
| Scorch decal | 1 if grounded (2.24) | – | 3.4 … 4.3 × s | – | permanent |
| Flash | 1 glow | – | 2.2 s → 3.3 s | [4.2, 3.4, 2.2] | 0.07 |
| Wide bloom | 1 glow | – | 6.5 s → 9.75 s | [0.7, 0.36, 0.14] | 0.14 |
| Shock ring | 1 `ring` | – | 1.5 s → 9 s | [0.9, 0.6, 0.35] × 0.22 | 0.2 |
| Fireball flames | 18 √s (9) | outward 3.5 … 12 × s m / s in any direction from −0.25 below to straight up, plus 1.8 s up; drag 3.2, rises (gravity −0.3 g), turbulence 2 | 0.8 … 1.2 s → 2.3 … 3.4 s | [0.85, 0.42, 0.12] → [0.3, 0.03, 0.004], each × 0.42 / max(k, 0.3): dim alone, white where many overlap | 0.32 … 0.68 |
| Core tongues | 4 √s (2) | slow: ± 1.2 s sideways, 1.5 … 3.2 s up; drag 2.4, gravity −0.35 g | 1.6 … 2.1 s → 3.4 … 4.4 s | [0.9, 0.5, 0.16] → [0.32, 0.05, 0.006] × 0.5 | 0.55 … 0.85 |
| Smoke | 26 √s (12) | out 0.3 … 3.4 × s m / s, up 1.2 … 5.6 × √s; drag 1.5, gravity −0.11 g, wind 0.8, turbulence 1.3 | 0.9 g s → 2.8 … 4.0 g s, girth g = 0.6 … 1.25 | soot 0.07 … 0.15 → 0.16 (× 0.55 by day), opacity 0.72 … 0.92, heat 0.4 … 1 (lit from inside while young) | 2.6 … 4.8 × (0.6 + 0.4 s) |
| Smoke column (fuel only) | 6 √s at night, 12 √s by day | straight up 3 … 7.5 × √s m / s (the later the faster); drag 0.9 | 0.8 s → 2.8 … 5.6 s | soot 0.05 … 0.1 → 0.2 (× 0.55 by day), opacity 0.7 … 0.88, heat 0.3 … 0.7 | 4.5 … 6.5 × (0.7 + 0.3 s) |
| Sparks | 34 s (18) | all round and up (cone 1.75 rad about vertical), 8 s … 26 s m / s, bounce | 1.6 … 3 cm | hot × 4.5 | 0.45 … 1.3 |
| Electric sparks (drone only) | 16 | cone 1.9 rad, 5 … 16 m / s | 1.6 … 3 cm | electric × 5.5 | 0.2 … 0.6 |
| Embers | 14 s | out 1 … 5 × s, up 2 … 7 × √s; drag 1.3, gravity 0.22 g, turbulence 3.2; die on the floor | 3.5 … 6.5 cm | [3.2, 1.5, 0.4] → [1.2, 0.2, 0.03] | 1.2 … 2.8 |
| Fragments | 13 s (7) debris bodies | out 3 … 11 × √s, up 3 … 10 × √s | 4 … 11 cm × √s, up to 2.4 × longer | near-black 0.02 … 0.09 | 2.2 … 4 |
| Ground dust ring | 14 √s if grounded | outward along the ground at 7 … 11.5 × s m / s, drag 3.1 | 0.7 s → 1.9 … 2.7 s | `#8a857e`, opacity 0.3 … 0.42 | 0.9 … 1.6 |
| Afterwards (blast under 3 m above the ground) | `smolder` emitter for 5 + 2 s seconds at scale 0.9 s; `embers` emitter for 1.6 + s seconds | | | | |
| Screen flash | 2.21 | | | | |

Flames and smoke are kept out of walls: the free distance is measured in eight directions (up to 6 s metres); a
direction with a wall nearer than 1.4 m is swapped for its opposite when that is more open, and speeds are held to
what the room allows (`src/fx/recipes.js:129`).

**Emitters** (`src/fx/emitters.js`). Rates are per second at k = 1; s = the emitter's scale. One stream never emits
more than 10 particles in a frame.

| Kind | Used by | Streams |
|---|---|---|
| `steam` | The 6 steam points of the level, endless (`src/atmos/life.js:593`) | 13 / s soft lit puffs from a disc of radius 0.16 s: up 0.9 … 1.6 × √s m / s, 0.32 s → 1.3 … 1.9 s, life 2.4 … 3.8 s, `#d9dde0`, opacity 0.13 … 0.2, drag 0.55, full wind, turbulence 0.55 |
| `jet` | A hit propane tank or welding rack until it blows (`src/explosives.js:332`) | Pressure builds: reach = s × (0.75 → 1.25 over the fuse). **Blue cone** 95 / s: 9 … 13 × reach m / s, life 0.06 … 0.095 s, 0.075 s → 0.2 s, [0.55, 0.85, 1.7] → [1.5, 0.85, 0.35] × 0.8, stretched. **Orange tongue** 150 / s: 8 … 12.5 × reach m / s, life 0.13 … 0.24 s, 0.11 s → 0.36 … 0.52 s, [1.15, 0.62, 0.18] → [0.6, 0.08, 0.01] × 0.5, drag 2.6, curls upward (−0.45 g), turbulence 4. **Sparks** 18 / s: 6 … 13 × reach ± 2.4 m / s, life 0.25 … 0.6 s, [4.2, 3, 1.5] → [1.6, 0.5, 0.1], bounce. Never thinned below k = 0.7. Visible flame length about 1.5 × reach **(derived)**: 1.0 m growing to 1.7 m on a propane tank, 1.35 m growing to 2.25 m on the rack. Light: `#ffa050`, 9 ± 5 game cd × s, range 7.5 √s m, one s metre along the jet |
| `smolder` | Every blast site | 9 / s × (share of life left): dark wisps [0.11, 0.105, 0.1], up 0.6 … 1.2 m / s, 0.22 s → 0.9 … 1.4 s, life 1.8 … 3.1 s, opacity 0.26 … 0.4 thinning to 40 % |
| `embers` | Every blast site | 8 / s glowing motes from a 0.25 s disc: up 0.9 … 2.3 m / s, 2.8 … 5 cm, [3, 1.4, 0.35] → [1.1, 0.18, 0.02], life 1.2 … 2.5 s, turbulence 3.4 |
| `fire` | Nothing in the shipped game | 38 / s flame tongues (0.42 … 0.6 s → 0.14 s, life 0.45 … 0.85 s, [1.35, 0.8, 0.28] → [0.75, 0.11, 0.012] × 0.5, up 1.5 … 2.9 √s m / s), a bed glow 7 / s (1.0 s, [0.95, 0.42, 0.1]), smoke 4 / s (0.4 s → 1.4 … 2.0 s, life 2 … 3.4 s), embers 3 / s. Light `#ff8a3a`, 14 ± 10 game cd × s, range 9 √s m |
| `drip` | Nothing in the shipped game | 1.6 drops / s falling under gravity as a 2.2 cm streak [0.55, 0.68, 0.82], with a 3-speck splash where it lands |

Emitter lights: taken from the pool when the camera comes within 42 m, given back beyond 52 m, checked every 0.3 s;
flicker = base + depth × (0.5 sin(17.3 t) sin(6.1 t) + 0.3 sin(31.7 t) + 0.2 × noise) (`src/fx/emitters.js:19`, `:490`).

Explosive props (constants in `src/explosives.js:19`; behaviour in the weapons-and-combat spec):

| | Propane tank | Welding rack |
|---|---|---|
| Fuse after the first hit | 1.6 s | 1.1 s |
| Blast radius → effect scale | 6.5 m → 1.0 | 7.5 m → 1.15 |
| Jet scale | 0.9 | 1.2 |
| Jet origin | The bullet hole, pointing along the hit normal + 0.55 up; else the valve | same |
| While lit | The tank rattles ± 0.035 rad; a `hiss` loop rises from 25 % to full volume | same |
| Camera shake of the blast | 0.15 + 0.9 g², g = 1 − distance / 28 m | same |

Other callers:

| Who | What | Source |
|---|---|---|
| Goon collapsing | `fx.dust` scale 0.8 where the body lands | `src/enemies/goon.js:1037` |
| Buzzard, damaged | `fx.smoke` 0.45 every 0.1 … 0.22 s; 5 sparks every 0.5 … 1.7 s | `src/enemies/buzzard.js:734` |
| Buzzard, killed | 10 sparks, 4 debris lumps `#30333a` at speed 5, smoke 0.8; while falling smoke 0.7 every 0.05 s and 4 sparks every 0.16 s; then its burst (radius 3 m) | `buzzard.js:769`, `:801`, `:818` |
| The train | `fx.dust` 0.5 … 1.1 under the deck, 6 sparks under an arc (2.20) | `src/atmos/train.js:339` |
| The weapon | Barrel smoke wisps (above) | `src/weapon/viewmodel.js:395` |

### 2.26 Defined but never used by the shipped game

Do not spend port effort on these unless a designer asks for them.

| Item | Where | Status |
|---|---|---|
| `shadowRadius` 1.2 (day) / 2.5 (night) | `src/config/look.js:103`, `:335` | Written to the light, ignored by the soft shadow filter in use (`src/render.js:412`) |
| Neon "tired tube" stutter | `src/mats.js:589`, `:791` | The stuttering group is one of three; all 7 neon signs of the level landed in the other two **(measured)**, so no sign stutters |
| `city.aviation` 9 | `src/config/look.js:243` | The builder caps per ring and per roof instead: 13 lights exist |
| Emitter kinds `fire`, `drip` | `src/fx/emitters.js:202`, `:295` | No caller |
| `fx.puff`, `fx.decal`, `fx.explosion` as direct calls | `src/fx.js:440`, `:511`, `:472` | No caller: puffs, decals and blasts all arrive through the `impact` and `explosion` events |
| `viewFlash` and its 32-sprite pool | `src/fx/recipes.js:617` | Fallback for a weapon without its own flash |
| Decal kinds `dent`, `crack`, `soot`, `bullet` by name | `src/fx/recipes.js:63` | Only reachable through `fx.decal` |
| Sign style `street`, route bullets on plates | `src/mats/signs.js:324`, `:395` | Not placed (2.9) |
| Posters `wanted` · 0 and `ipx` · 0 | `src/mats/paper.js:210`, `:91` | Exist, not placed (2.10) |
| Decals `manhole`, `bullet`, `puddle` of the materials module | `src/mats/decals.js:17` | Not placed (2.14) |
| Facade `shopfront` mode; per-wall `bays`, `seed`, `lit`, `floorH` | `src/mats/layout.js:63`, `src/level/buildings.js:94` | Never requested; overridden by the three shared facades (2.7) |
| Traffic-sign faces `sign_nopark`, `sign_oneway`, `sign_stop`, `ped_stop`, `ped_walk` | `src/props/atlas.js` | Their props are not placed |
| Stub modules | `src/stubs/mats.js`, `atmos.js`, `fx.js` | Development stand-ins (3.16) |

### 2.27 Where the design documents and the code differ

The code wins in every case.

| Document says | Code does |
|---|---|
| "Signs are simply lit signage in daylight" (`docs/DESIGN.md` 8.1) | Signs keep 30 % of their night glow by day, neon 55 % (`src/mats.js:159`); lamp lenses, tail lights, the billboard face and the lit prop graphics keep their night values (2.17) |
| "A small budget of real point lights at the key lamps" (DESIGN 5) | The real lights are spot lights, 4 … 12 by preset, not tied to lamps: they migrate to whichever lamps have the highest claim near the camera (3.4). By day only work lights and dimmed neon hold one |
| "sun / moon key light" (`docs/CONTRACT.md` 11.1), "cool moonlit ambient" (DESIGN 5) | The night key is a steep warm light "standing in for the street lights" from the south-east at 64° of elevation; the drawn moon sits 17° up in the east-south-east and lights nothing but the clouds painted round it |
| `atmos.update` does "neon flicker" (CONTRACT 6.11) | Neon flicker lives in the materials module (`src/mats.js:791`) |
| "`fire` and `jet` hold a pooled light while the camera is within about 45 m" (CONTRACT 6.8) | Taken under 42 m, released over 52 m |
| "Real lights for the `quality.lights` highest-priority `level.lamps`" (CONTRACT 6.11, first paragraph) | Superseded by the claim rule in the same section; priority only breaks ties at equal distance |
| "Seven draw calls at most" for effects (CONTRACT 6.8) | Seven objects exist (decals, shells, debris, lit pool, additive pool, tracers, first-person flash); matches |
| "Stylised low-poly realism … No photo textures" (DESIGN 5) | True of the web game; the Unreal rebuild replaces it with photoreal art by decision of the port (this spec) |

---------------------------------------------------------------------------------------------------

## 3. Behaviour

### 3.1 Who updates when

Per frame, in this order (`tick`, `src/main.js:269`; lists in `src/modules.js:91`):

1. Input, then the game flow.
2. While a run is live (not on the title screen, not paused): player, weapon, enemies, explosives. These are the
   callers of every effect.
3. Whenever the game is not paused, so also behind the title screen: **effects**, level, **atmosphere**,
   **materials**. The block keeps living behind the menu: trains pass, steam rises, neon hums.
4. Always: audio, HUD, menus.
5. The frame is drawn (2.21). The shadow map is redrawn every `shadowEvery` frames only (2.22).

Paused means frozen: particles hang in the air, the train stops, the effects clock and the atmosphere clock do not
advance (`src/fx.js:137`, `src/atmos.js:364`). Shader time wraps every 7200 s (`src/atmos.js:34`); the grade's time
every 600 s (`src/render.js:654`).

Inside one effects update (`src/fx.js:546`): read the scene's lights every 0.5 s (key colour and direction, ambient,
fog: this is what smoke is lit with) → ease the day blend → move particles → run emitters (after the move, so a jet
stays attached to its valve) → sort the lit pool back to front → move tracers, casings, debris → pick the 4 lights
that shine on smoke → write the screen flash.

Inside one atmosphere update (`src/atmos.js:366`): interior blend → real-light rig → train → street life → re-fit
the shadow frustum if the shadow map size changed → apply the detail layers if the preset changed.

### 3.2 Switching between day and night

`atmos.setTime(name)` (`src/atmos.js:279`) is instantaneous: there is no dusk. It is called at boot with the user's
`time` setting (default `day`), on every run reset by the game, and at once when the setting changes while the title
screen is up. Nothing is created or destroyed; the steps are:

1. Show one sky dome, hide the other.
2. Key light: colour, intensity, direction, bias values; the shadow frustum is fitted again to the new direction
   (3.5).
3. Ambient hemisphere colours and intensity; remember them as the "outdoor" values of the interior blend.
4. Haze colour and density.
5. Swap the image-based light (two captures baked at boot, 2.15).
6. Copy every grade field of the time into the live look; the exposure keeps the current interior factor.
7. Show or hide pools, glows, cones (cones also need the preset's permission).
8. Per-kind gains of the real lamp lights; the rig re-evaluates on its next update.
9. Far city: sheet tint, window glow, skyline strips and sink, lights on or off.
10. Train: window glow, stripes on or off.
11. Street life: steam colour and opacity, spray colour, moths on or off, pigeons on or off.

Two other modules follow by themselves: the materials module switches sign glow, lit glass, the wet street and the
ground albedo when the time changes (`applyTime`, `src/mats.js:771`); the effects module eases its day blend over
about a second (2.23).

### 3.3 Inside the shop

The atmosphere asks the level every frame whether the camera is inside the shop (`level.interiorAt`, 0 or 1) and
eases a blend value toward it: `interior ← target + (interior − target) × e^(−2.2 × dt)`, snapping when within 0.002
(`src/atmos.js:371`, rate `look.interior.rate`). A caller may override the target with `setInterior(f)`; the override
holds for 0.25 s after the last call. With blend f:

- exposure × lerp(1, 1.35 by day or 0.86 at night, f);
- ambient intensity × lerp(1, 0.62, f) and its sky colour lerped toward `#d8d0c4` (day) or `#a9a0a0` (night);
- haze density × lerp(1, 0.5, f).

About 1 s to settle (63 % in 0.45 s). The key light does not change: the shop is lit through its doors and skylight
by the same sun, plus its four work lights, which are the only lamp kind at full strength by day.

### 3.4 The real lamp lights

The web game cannot afford 90 lights, so a fixed set of spot lights (4 … 12 by preset, none casting shadows) moves
between lamps (`createLightRig`, `src/atmos/lights.js:105`). Unreal does not need this mechanism (4.4); it is
described so nobody mistakes its side effects for intent.

- Candidates: every lamp that is not virtual and not "tired".
- Every 0.2 s: focus = camera position + 6 m along the view direction; each lamp's claim =
  (priority + 1) / (1 + (distance to focus / 14 m)²), × 1.3 if it currently holds a light, −1 if its kind's gain is 0
  at this time of day. The best N claims are "wanted".
- A light whose lamp is no longer wanted fades out over 0.3 s, jumps to the best waiting lamp, fades in over 0.4 s.
- A light on a lamp: position = the lamp; aim = the lamp's own direction if it has one, else out from its wall and
  down (wall normal with y = −0.7), else straight down; cone half-angle and penumbra from its kind (2.17);
  range = lamp range × 1.2; intensity = lamp intensity × kind gain (2.17) × time-of-day gain × fade level.
- Before the first frame the N highest priorities are lit at full.

Consequences visible in the web game: by day the four shop work lights are real at 115.6 game cd (34 × 3.4) with a
15.6 m reach and a 76° half-angle; by night from the start position the eight lights of `high` sit on a street lamp,
four neon signs, two El lamps and a work light **(measured)**.

### 3.5 Fitting the key light's shadow

One orthographic shadow map covers the whole block (`fitShadowFrustum`, `src/atmos/plan.js:53`): the box
bounds × (−0.5 m … min(34, tallest thing + 1)) is projected along the light direction with a 2 m margin, the light
is placed 40 m behind it, the frustum is padded 1 m in depth, and its origin is snapped to whole shadow texels so the
shadow edge does not swim. The depth bias is set in metres (0.03 by day, 0.045 at night) and converted to the depth
range. Measured results are in 2.15.

### 3.6 Things that flicker

| What | Formula (t in seconds) | Source |
|---|---|---|
| Neon signs | brightness × (1 + 0.03 sin(rate × t + φ) + 0.02 sin(2.63 × rate × t + 1.7 φ)), rate 9 … 15 rad / s and phase φ per group. Signs are dealt into 3 groups in the order they are painted (`count mod 3`) | `src/mats.js:589`, `:791` |
| Tired tube (group 1 only; unused, 2.26) | After 2 … 8 s, then every 3 … 11 s: for 0.25 … 0.85 s the brightness drops to × 0.3 whenever sin(47 t + φ) × sin(13.1 t) > 0.12 | `src/mats.js:800` |
| Tired sodium lamps (2 of them; pool, cone and glow together) | on = 1 − (0.22 + 0.2 × sin(37 t + 50 p) × sin(11.3 t + 9 p) + 0.55 × drop); drop = 1 during a random 20 % of the sixth-of-a-second slots, p = the lamp's phase. They never hold a real light | `src/atmos/lampfield.js:15` |
| Lamps under the El while a train is over them | on × (1 − presence × (0.28 + 0.24 sin(43 t + 1.7 x))), for lamps with x inside the train's extent | `lampfield.js:27` |
| Emitter lights (jet, fire) | 2.25 | `src/fx/emitters.js:490` |
| Aviation lights, plane strobe, far windows, stars | 2.18, 2.16 | |
| Train stripes | × (0.86 + 0.14 sin(31 t + 0.7 x)) | `src/atmos/train.js:147` |

### 3.7 The haze

For a surface point at view depth D (metres along the view axis, not the radial distance) and world position P
(`src/atmos/fog.js:79`):

```
outside   = max(|P.xz − centre of the bounds| − (half size of the bounds + 4 m), 0)     per axis
fogged    = 1 − exp(−(density × D)² − (0.01884 × |outside|)²)
west      = (P.x − camera.x) / sqrt(|P.xz − camera.xz|² + 1)                            −1 looking west … +1 east
tint      = lerp(tintWest, tintEast, (west + 1) / 2)                                     day or night pair (2.15)
colour    = lerp(colour, haze × tint, fogged)
```

The second term is extra extinction that depends only on how far outside the playable rectangle the point lies:
3.5 % at 10 m, 20 % at 25 m, 59 % at 50 m, 98 % at 105 m. It is what makes the far blocks dissolve whatever the view
distance. The day or night tint pair is chosen by the haze's own luminance (smoothstep 0.1 … 0.3), so no switch is
needed. Sky domes, pools, glows, steam, the far city and all effects apply the same function.

### 3.8 The El train

States of one train (`src/atmos/train.js:374`; timeline `src/atmos/plan.js:171`); `local` is seconds since the pass
began; L = 79.8 m, v = 16.5 m / s, R = 145 m, bounds x = −46 … 46.

| State | Enter | While in it | Leave |
|---|---|---|---|
| `idle` | boot; after `gone` ends | Train hidden; `atmos.train.active = false`, `phase = null`; lamp stutter and stripes at 0 | when the clock reaches `nextAt` |
| `approach` | `local` = 0. Nose at x = −46 − 145 = −191 (eastbound) or +191 (westbound). Event `train:pass` {phase `approach`, duration 8.79 s, dir} | Nose moves at v. Effects start once any part is within 30 m of the bounds (presence > 0) | `local` ≥ R / v = 8.79 s: the nose crosses the bounds |
| `over` | Event {phase `over`, duration 10.41 s} | The train is above the block | `local` ≥ 8.79 + (92 + L) / v = 19.20 s: the tail has left the bounds |
| `gone` | Event {phase `gone`, duration 8.79 s} | Runs out into the haze | `local` ≥ 27.99 s: hidden, back to `idle` |

Schedule (`createTrainSchedule`, `src/atmos/plan.js:200`): the first pass begins at max(1, 20 − 8.79) = 11.21 s of
un-paused time; each time a pass begins the next is set to begin rand(40, 70) s later (seeded with the run's seed);
direction alternates, starting eastbound. Eastbound trains use the south track (z = +2.1), westbound the north track
(z = −2.1) and are turned round. `atmos.passTrain(dir, lead)` starts one at once, `lead` seconds before it reaches the
block (trailers, tests).

While presence > 0 (presence = overlap of the train with bounds ± 30 m, divided by 12 m, clamped 0 … 1) and the
camera is within 60 m of the train along the street (`effects`, `src/atmos/train.js:339`):

- **Strobe.** When the timer runs out and the previous flash has finished and more than 4 m of train is in reach:
  one pooled light under the deck (2.20). With 22 % chance it is an arc instead (blue, 130 game cd, 0.07 s, plus
  6 sparks falling from it). Next flash in rand(0.1, 0.34) s.
- **Grit.** Every rand(0.16, 0.42) s one `fx.dust` of scale rand(0.5, 1.1) at a random spot under the deck within
  ± 26 m of the camera along the street (clamped to the train's extent).
- **Shake** (only while the game state is `playing`): trauma += 0.42 × a × dt each frame, with
  a = clamp(1 − along / 14) × clamp(1 − side / 15), `along` = metres of street between the camera and the train's
  extent, `side` = metres between the camera and the edge of the deck; skipped when a ≤ 0.02.
- **Stripes and lamp stutter** scale with presence (2.20, 3.6).
- **Paper** gets the train's gust (3.9).

The train casts shadows like any mesh, so by day its shadow sweeps the avenue. It has no collision and cannot be
shot. Sound follows the three events (2.20).

### 3.9 Street life

- **Steam columns** are closed loops, not emitters: each of the 11 puffs has a fixed phase in a 4.96 s cycle. With
  t = phase 0 … 1: height = 6.2 × (1 − (1 − t)²); sideways drift = 1.5 × t in the puff's own direction, plus the breeze
  (−1.1, 0.25) m / s × 4.96 s × 0.55 × t², plus a small wobble; radius grows from 0.55 to 2.6 m with √t; opacity
  fades in over the first 10 % and out from 45 % (`src/atmos/life.js:28`). The fx `steam` emitter at the same point
  adds the lit, wind-blown part (2.25) and is asked for again after every run reset, because a reset clears the
  effects (`src/atmos.js:348`).
- **Paper** (`src/atmos/life.js:359`). Global gust timer: first gust after rand(1.5, 5) s, then every rand(5, 13) s;
  a gust lasts rand(1.6, 3.2) s, blows along the avenue (east or west, 50 / 50) ± 0.5 rad at 3.6 × rand(0.6, 1) m / s.
  Per sheet, each frame: wind = 15 % of the steady draught + the gust if one is blowing + the train's gust if the
  sheet is within 3 m of the train's extent along the street and within 8 m of its track (3.2 m / s along the train's
  direction and 35 % of that away from the track); the sheet's velocity eases toward wind × its own catch factor
  (0.45 … 1) at rate 4.5 / s lying flat or 1.6 / s airborne. It only moves onto walkable navigation cells inside the
  bounds (1 m margin); blocked on one axis it slides on the other and bounces 30 %; blocked on both it bounces 25 %
  and counts time stuck. Stuck for more than 6 s and more than 25 m from the camera: placed again at a random
  walkable spot on the avenue. Airborne amount eases toward clamp((speed − 1.1) / 1.6): above 1.1 m / s it lifts
  (0.16 … 0.28 m), tumbles about the axis across its path at 3.4 rad per metre travelled and turns; slower it
  settles flat on the nearest half turn.
- **Hydrant spray**: 260 droplets on closed ballistic loops from the nozzle (2.19); the water never collides and
  never wets the player. The wet patch on the street is the materials module's (2.6).
- **Moths** orbit their lamp on tilted circles and jitter; dust motes drift on larger, slower ones. Both fade out
  between 30 and 55 m from the camera.
- **Pigeons** (`src/atmos/life.js:444`): each bird circles its flock's centre at its own radius, height and speed
  (2.19), flattened north-south, bobbing ± 1.6 m, banking into the turn; wings beat in bursts and are held out in a
  glide in between. They never land, never react to gunfire, and exist only by day.
- **Far traffic, plane, switching windows**: closed loops with the periods in 2.18.

None of this is gameplay: nothing here has collision, nothing can be shot, nothing makes sound except the train
and (in the audio spec) the steam hiss and neon buzz loops.

### 3.10 A particle's life

Per particle and frame (`integrate`, `src/fx/sim.js:197`), with dt the frame step:

```
k        = drag × dt / (1 + drag × dt)                    implicit, stable at any frame rate
v.xz    += (wind.xz × windShare − v.xz) × k
v.y     −= v.y × k
v.y     −= 9.81 × gravity × dt
v       += turbulence × dt × (sin(a + 3.1 t + 1.7 y), 0.35 sin(1.9 a + 2.3 t), cos(1.3 a + 2.7 t + 1.3 x))     a = 61.7 × seed
p       += v × dt;   rotation += spin × dt
on its floor while falling:  DIE → removed;  BOUNCE → v.y = −v.y × (0.25 … 0.55), v.xz × 0.65, at rest below 0.45 m / s;  STICK → at rest
```

Drawn (`writeInstances`, `src/fx/sim.js:281`), with u = age / life: size = lerp(size0, size1, u^curve); opacity =
peak × (u / fadeIn while u < fadeIn) × ((1 − u) / (1 − fadeOut) once u > fadeOut); colour = lerp(colour0, colour1,
u^ramp); heat = heat0 × e^(−6 × age); a stretched sprite is drawn as long as it travels in `stretch` seconds, capped
at 45 × its size.

### 3.11 A tracer's life

Spawned with its path (start, unit direction, length) and speed. Each frame head += speed × dt; the drawn ribbon runs
from max(0, head − streak) to min(head, length); its brightness falls linearly once it is shorter than 35 % of the
streak; it is removed when head − streak ≥ length (`src/fx/tracers.js:51`). At 260 m / s a 30 m shot lasts
(30 − 1.1 + 5.72) / 260 = 0.13 s. A tracer is purely cosmetic: the hit is resolved instantly by the weapon (hitscan)
before the tracer is spawned, and the impact effect appears at once, not when the streak arrives.

### 3.12 Brass and debris

Rigid points with a spin, not physics bodies (`stepBody`, `src/fx/bits.js:29`): gravity; the floor height under the
body is asked again every 4 frames; one wall is looked for along the throw at spawn (within 1.4 × horizontal speed +
0.3 m) and the body bounces off it; on the floor the vertical speed is reversed and scaled by the restitution, the
horizontal by the grip; after the maximum number of bounces, or a rebound slower than 0.55 m / s, it lies still.
Casings then stay (ring buffer of 60); debris shrinks away at the end of its life. Neither collides with characters,
vehicles' moving parts or each other, and neither affects gameplay. The first floor contact of a casing emits
`shell:bounce` once for the audio module.

### 3.13 An explosion, in order

1. An `explosion` event arrives with position, radius and source (`src/fx.js:618`). Scale and flavour follow 2.25.
   If the source is one of the explosive props, its own foot height is used as the ground (it may stand on a kerb
   the collision world leaves out).
2. Same frame: the pooled light, the scorch decal, every particle group of 2.25 (the fireball is brightest in the
   first two frames, where its sprites overlap), the fragments.
3. Same frame: if the centre is less than 3 m above the ground, a `smolder` emitter and an `embers` emitter start at
   ground level + 0.1 m.
4. Same frame: the screen flash is raised to at least the value in 2.21 and then decays (e^(−7 t): half gone in
   0.1 s). The effects module only writes the flash while nobody else has changed it since its own last write.
5. `explosive:blast` (from the explosives module) removes the bullet holes that were on the prop.
6. 0.36 s: the light is gone; 0.3 … 0.7 s: flames gone; 0.58 s: smoke stops glowing from the blast; 2.6 … 6.5 s:
   smoke thins out; 7 s (propane): the site stops smouldering.

The jet that precedes a blast (`src/explosives.js:332`): on the first damaging hit an emitter `jet` starts at the
bullet hole (or at the valve when the hit was not a bullet) with a life of fuse + 0.15 s and lengthens as the
pressure builds; when the fuse runs out the tank explodes and the emitter ends. Chain reactions and damage are in
the weapons-and-combat spec.

### 3.14 Dynamic resolution

A governor fed one timestamp per drawn frame (`createGovernor`, `src/render.js:174`; constants 2.22).

| State | Rule |
|---|---|
| Settling | No samples are taken for 3.5 s after boot, a new run, a resume or the first input, and for 1 s after any change of scale |
| Measuring | Frame times fill a window of 45 frames or 900 ms (at least 5 frames). Frames over 1.5 s are ignored. The window's verdict is the mean after dropping hitches (frames above max(100 ms, 4 × the running average), unless more than half the window is like that) and trimming a sixth from each end |
| Step down | Verdict above 21.5 ms, not at the floor, not "capped": scale − 0.1 (− 0.2 above 30 ms, straight to 0.6 above 45 ms). The step is on trial; the wait before any step up doubles (2 s → at most 60 s) |
| Trial verdict | Next window not at least 8 % faster: try the floor (0.6) once; if that is no faster either, restore the scale from before the trial and mark the frame time as "capped" (not limited by pixels: a vsync cap or a CPU-bound frame). While capped, no stepping down until the frame time moves by more than 10 % |
| Step up | Verdict below 17.4 ms, scale under 1 and the wait has passed: scale + 0.1, next attempt after 2 s |
| Preset drop | Two windows in a row at the floor above 26 ms, after a proven step down and not capped: one preset down the ladder (`ultra` → `high` → `medium` → `low`) if the host allows, and the scale restarts at 0.8 |
| Reset | Picking a preset by hand returns the scale to 1 |

### 3.15 Edge cases worth keeping

- A hit on a Goon or a Buzzard never leaves a decal, and a hit on a surface without an entry in 2.24 leaves none
  either (it would hang in the air or read wrong).
- Effects further than 150 m from the camera spawn nothing, but decals are still placed (they are cheap and may be
  walked up to).
- Lit puffs spawned under a roof or in a building's shadow are lit at 12 % of the key: smoke in the shade is dark,
  smoke in the sun is bright. The shade is measured once, at birth.
- Blast smoke and flame turn away from a wall closer than 1.4 m (2.25).
- A dust jet and its cloud are always spawned whatever the preset; only the optional third puff depends on density.
- Jets and fires are never thinned below 70 % density: a jet must stay one flame.
- A long frame cannot flood a stream: at most 10 particles per stream per frame, and the surplus is dropped.
- `fx.clear()` (every run reset) removes particles, tracers, casings, debris, decals and finite emitters; endless
  emitters survive, and the atmosphere asks for its steam again anyway.
- The shipped first-person flash never comes from the effects system (2.25).
- By day the pools, cones and glows are hidden but lamp lenses stay self-lit (2.17): a street lamp in the sun shows
  a bright lens and casts no light.
- Light pools lie on whatever the physics world reports as ground under them; a lamp over a deck at least 2.5 m wide
  (a platform, the mezzanine) lights that deck, not the street below (`src/atmos/lights.js:13`).
- Cobra-head arms reach away from the roadway: the heads hang over the sidewalks (z = ± 9.78, kerbs at ± 7), not
  over the road. This is how the level is built; treat it as ground truth for placement.
- Side and back walls 10 m tall show a 0.1 m sliver of a fourth window row at their top edge (the window layer's
  storey is 3.1 m and the layer is not clipped to whole storeys).
- Sub lines on box signs are painted in the sign's glow colour: `OPEN 24 HRS · COLD CUTS · COFFEE · LOTTO` is pale
  yellow `#ffd24a` on taxi yellow and `FRIED · WINGS · BISCUITS` is `#ffc84a` on yellow, both nearly invisible (2.9).
  Almost certainly unintended.
- The stripes under the train use a tie pitch of 0.62 m while the modelled ties are 0.56 m apart
  (`src/level/el.js:14`); the wheel-clack audio assumes 16.3 m cars against 16.1 m (15.4 + 0.7).
- The headless measurement ran with fallback fonts: glyph widths of signs in this spec's tables are layout sizes, not
  measured ink.

### 3.16 Stand-ins that must not be ported

`src/stubs/mats.js`, `src/stubs/atmos.js` and `src/stubs/fx.js` implement the same interfaces with flat colours, a
fixed light and line tracers, so that other modules could be developed alone. They are never loaded by the shipped
build. Nothing in them is a requirement.

---------------------------------------------------------------------------------------------------

## 4. Unreal mapping

### 4.1 How to use this section

Three documents meet here, and each wins on its own ground:

- **This spec**: what the web game does. Layout, positions, timings, sizes, text, colours of signage, counts and
  rules of effects are ground truth and carry over unchanged.
- **`docs/unreal/ART_BIBLE.md`**: what the photoreal picture must look like. It decides light levels in lux and nits,
  exposure ranges, how each sign is built as an object, material rules, effect quality bars and performance tiers
  (its sections 2, 3, 5, 7, 9). Where it departs from the web game on purpose (no fake key light at night, lamps off
  by day, physical emissive levels), it wins.
- **Exported data** (`unreal/MurderInc/Content/Data/`, written by `tools/ue-export/`): the machine-readable twin of the
  tables in section 2, already in both web and Unreal coordinates. `atmos.json`: `rigs.day`, `rigs.night`, `sky`,
  `lamps.list` (the 90 lamps), `signLights`, `windowLights`. `level.json`: `signage.paintings` (42 signs, 16 posters,
  21 graffiti, 8 decals) and `signage.placements` (347), `facades`, `glazing`, `train`, `steam`, `puddles`.
  `config.json`: the `look` and `quality` tables verbatim. `text.json`: `lettering`.

What this section adds: unit-converted values, the web game's light and grade expressed in comparable physical terms
(so the art bible's targets can be checked against what players of the web game see), and the Unreal feature each
mechanic maps to. Values marked **(proposal)** are starting points to tune in the editor; nobody has run them in
Unreal.

### 4.2 Axes, units and the constants that carry over

Unreal (X, Y, Z) cm = (x, z, y) web m × 100. A web direction (dx, dy, dz) is (dx, dz, dy) in Unreal. Yaw 0° faces
east (+X), +90° faces south (+Y). A light's rotation is given for the direction the light **travels**.

| Quantity | Web | Unreal |
|---|---|---|
| Day sun, travel direction | (0.553, −0.788, −0.271) | (0.553, −0.271, −0.788): pitch −52.0°, yaw −26.1° |
| Night key, travel direction | (−0.342, −0.900, −0.270) | (−0.342, −0.270, −0.900): pitch −64.2°, yaw −141.7° |
| Moon, direction toward it | (0.86, 0.29, 0.42) | (0.86, 0.42, 0.29): 16.9° above the horizon at yaw 26.0° |
| Sun disc, moon disc (angular radius) | 0.0105 rad, 0.017 rad | 0.60°, 0.97° (real: 0.27°, 0.26°) |
| Haze, squared-exponential density | 0.0032 (day), 0.006 (night) per m | 0.000032, 0.00006 per cm in the same formula |
| Haze outside the bounds | starts 4 m out, k = 0.01884 per m | starts 400 cm out, k = 0.0001884 per cm |
| El: deck underside, rail top, tracks | y 6.5, y 6.83, z ± 2.1 | Z 650, Z 683, Y ± 210 |
| Train: consist, car, gap, speed | 79.8 m; 15.4 × 2.9 × 3.55 m; 0.7 m; 16.5 m / s | 7,980 cm; 1,540 × 290 × 355 cm; 70 cm; 1,650 cm / s |
| Train: nose path, eastbound | x −191 → 270.8, z 2.1 | X −19,100 → 27,080, Y 210 |
| Train: nose path, westbound | x 191 → −270.8, z −2.1 | X 19,100 → −27,080, Y −210 |
| Train strobe | y 6.05; range 17 m; within ± 15 m of the camera along x, ± 1.3 m of the track | Z 605; attenuation radius 1,700; ± 1,500; ± 130 |
| Train shake falloff | 14 m along the street, 15 m to the side | 1,400; 1,500 |
| Steam column | 6.2 m tall; radius 0.55 → 2.6 m; 4.96 s | 620; 55 → 260 |
| Hydrant jet | 5.2 m / s out, 1.56 m / s up; lands 2.68 m out; apex 0.12 m above the nozzle after 0.16 s **(derived)** | 520, 156 cm / s; 268; 12 |
| Pigeon orbits | radius 6 … 22 m; height 15 … 34 m; 0.16 … 0.26 rad / s | 600 … 2,200; 1,500 … 3,400; 9.2 … 14.9 ° / s |
| Loose paper | 0.22 × 0.30 m; gusts 2.2 … 3.6 m / s; lifts above 1.1 m / s | 22 × 30; 216 … 360 cm / s; 110 cm / s |
| Wind on effects | (0.5, 0.2) m / s toward east and south | (50, 20) cm / s along +X, +Y |
| Breeze on steam columns and paper | (−1.1, 0.25) m / s: toward the west | (−110, 25) cm / s |
| Gravity | 9.81 m / s² | 981 cm / s² |
| Tracer | 260 m / s; streak 5.72 m; width 0.035 m; first 1.1 m skipped | 26,000 cm / s; 572; 3.5; 110 |
| Effect density distances | half beyond 55 m, none beyond 150 m | 5,500; 15,000 |
| Flash light distance limit; emitter light take / release | 75 m; 42 / 52 m | 7,500; 4,200 / 5,200 |
| Blast at scale 1 | light range 18 m; scorch 3.4 … 4.3 m; shock ring to 9 m | 1,800; 340 … 430; 900 |
| Skyline rings | radius 215 m and 395 m; height 72 m and 118 m | 21,500, 39,500; 7,200, 11,800 |
| Far traffic | on x = ± 56 and ± 134; 7 … 12 m / s; 240 m stretch | X = ± 5,600, ± 13,400; 700 … 1,200 cm / s; 24,000 |

### 4.3 Surfaces

- **Texture sets.** Each of the 23 painted sets (2.5) becomes a photoreal tiling set `TS_<Surface>_<Variant>` with
  `T_<Set>_BC`, `_N`, `_ORM` (and `_H` where relief matters), applied as `MI_<Surface>_<Variant>`. The art bible (3.2,
  3.4) and `art/scans/sets.json` choose the actual scans and their tile sizes; what must survive from the web game is
  the **real scale** of each pattern (2.5): brick on a 66.7 mm course, cinder block 0.4 × 0.2 m, sidewalk flags
  1.5 m, roll-gate slats and corrugation waves 75 mm, chain-link diamonds 75 mm, boards 150 mm, plywood sheets
  2.44 × 1.22 m, glazed tile 150 × 75 mm, rivets every 0.12 m on a 0.6 m column face.
- **One master material per family**, with the web game's catalogue name (2.4) as the instance: `asphalt`,
  `sidewalk`, `brick_red` and so on are material instances with a tint and a roughness bias. The catalogue hex values
  are mean albedos tuned for a night scene; the art bible replaces them (its 3.1 forbids anything as dark as the web
  asphalt). Use the **day** column of 2.4 as the nearer guide where both exist.
- **Web set → where to look.** Use an existing set of the art pipeline where one covers the family (for example
  `TS_Asphalt_Aged`, `TS_Concrete_Sidewalk`, `TS_Steel_Rusted`); the names below are proposals for the rest.

| Web set (2.5) | Proposed set | Tile (cm) in the web game |
|---|---|---|
| asphalt (+ court coat) | `TS_Asphalt_*`, `TS_Asphalt_CourtCoat` | 400 × 400 |
| sidewalk | `TS_Concrete_Sidewalk` | 450 × 450 (3 × 3 flags of 150) |
| dirt | `TS_Dirt_Packed` | 300 × 300 |
| brick: red, brown, tan, painted | `TS_Brick_Red`, `_Brown`, `_Tan`, `_Painted` | 240 × 240 (12 stretchers × 36 courses) |
| cinder | `TS_Block_Cinder` | 240 × 240 (6 × 12 blocks) |
| concrete | `TS_Concrete_Cast` | 240 × 240 |
| stucco | `TS_Stucco_Render` | 200 × 200 |
| tile | `TS_Tile_GlazedWhite` | 60 × 60 |
| metal, metal · galv | `TS_Metal_PaintedSheet`, `TS_Metal_Galvanised` | 150 × 150 |
| steel_el | `TS_Steel_RivetedGreen` | 60 × 240 |
| rust | `TS_Steel_Rusted` | 150 × 150 |
| roll_gate | `TS_Metal_RollGate` | 120 × 120 (16 slats) |
| corrugated | `TS_Metal_Corrugated` | 120 × 120 (16 waves) |
| chain-link | `TS_ChainLink_Mesh` (alpha-tested, two-sided) | 60 × 60 (8 diamonds) |
| paint | `TS_Paint_Enamel` (detail set, tinted) | 150 × 150 |
| pebble, wrinkle | detail normals `TS_Plastic_Pebble`, `TS_Plastic_BinBag` | 25; 70 |
| tire | `TS_Rubber_TireTread` | 24 |
| wood, plywood, cardboard | `TS_Wood_Boards`, `TS_Wood_Plywood`, `TS_Cardboard_Kraft` | 120; 244 × 122; 100 |
| fabric | `TS_Fabric_Canvas` | 25 |
| leaves | `TS_Foliage_LeafMass` | 120 |
| smudge | `TS_Glass_Smudge` (roughness only) | 160 |

- **World layers (2.6)** become material functions shared by ground and masonry masters: macro variation from a
  world-aligned noise that repeats every 4,800 cm (± 12 … 20 % on albedo, less on sunlit ground); a grime band over
  the first 170 cm of every wall; wetness. Drive wetness from one Material Parameter Collection (`MPC_Block`
  **(proposal)**): `Wet` = 0 by day, 1 at night; by day the wet patch is a capsule on the ground from
  (−1,225, 484) radius 500 to (1,175, 624) radius 90 (Unreal X, Y in cm), with a ragged edge of ± 60 cm blended over
  100 cm. Damp halves the roughness and darkens 18 %; puddles are roughness 0.05, 30 % darker, normals flattened.
  The 37 `asphalt_wet` blobs of the level (28 on the avenue, listed in `level.json` → `puddles`, and 9 in the
  yards) are the same puddles placed by hand: by day only those inside the capsule stay wet.
- **Upper-storey windows (2.7).** The painted window layer becomes real geometry: window, sill, lintel, AC unit,
  bars, door and cornice modules (briefs `facade_*`), laid out on the grids of 2.7 (`level.json` → `facades.grids`
  and `facades.faces`). Lit rooms at night are emissive interiors or simple room cards behind the glass: 5 of 19
  windows per 12.4 m × 15.5 m repeat, in the pattern of 2.7; by day all glass is reflective.

### 4.4 Signage, posters, graffiti, decals

- **Signs are objects** (art bible 5.2, 5.3 choose the construction of each): a carrier mesh from the briefs
  (`sign_*`), the artwork as a unique texture set, an emissive map for lit ones, and the paired light of 2.17. Sizes
  and centres in 2.9 are the web quads: keep the centre, the width and the height; depth is new. Web signs stand
  0.15 m (15 cm) proud of the storefront wall.
- **Lit or not** is a fact of the web game (2.9, column "Lit"; 17 lit faces). How bright in nits is the art bible's
  (2.7). For reference, the web values: neon 2.6 and box 1.5 at night (6.1 × and 3.5 × scene white at the night
  exposure); by day neon keeps 55 % and every other sign 30 % of that.
- **Neon flicker**: a Material Parameter Collection scalar per group, or a per-sign material parameter, driven by
  the formula in 3.6.
- **Posters** are meshes with a slight curl (briefs `poster_*`) or deferred decals; **graffiti, stencils and the
  mural** are deferred decals (DBuffer) that keep the wall's normal and roughness and replace its colour, with the
  55 % wear mask of 2.11 as opacity. **Road paint and ground stains** are deferred decals or a painted layer of
  the road material; their positions are in `signage.placements` with `onGround: true`.
- **Fonts**: Anton (headlines) and Archivo 500 / 700 / 800 / 800 italic (everything else), both under the SIL Open
  Font Licence. Typeset the artwork with the real fonts: the web measurement ran on fallbacks.
- **The IPX mark** is one master (2.3). Every placement in 2.9 – 2.13 instances it.

### 4.5 Light by day

| Web element | Unreal feature | Values |
|---|---|---|
| Sun (key) | Directional Light, movable or stationary, atmosphere sun light | Rotation as in 4.2. Colour and lux: art bible 2.1, 2.4 |
| Sun shadows | Virtual shadow maps | The web's single map (2.6 … 5.2 cm texels, about two texels of blur) is a floor, not a target: the stripes through the El ties are the identity of the day look and must be sharp at the column feet |
| Hemisphere ambient + image-based light | Sky Light (real-time capture) + Lumen | See the ratio below |
| Day sky | Sky Atmosphere + volumetric clouds (or a painted dome on low tiers) | Cloud cover 3 … 30 %, about a fifth; drifting east; never over the sun (art bible 2.1) |
| Haze | Exponential Height Fog + Sky Atmosphere aerial perspective, or the exact function (4.7) | Table in 4.7 |
| Fixed exposure 1.1, × 1.35 in the shop | Post Process Volume (unbound) + one in the shop | Art bible 2.3, 2.5 |
| Work lights and dimmed neon as the only real lights | All lights real | Art bible 2.4: lamps off by day except the shop's |

The web game in physical terms **(derived)**. three.js and Unreal share the convention "illuminance E on a matte
surface of albedo ρ gives luminance ρ E / π", so only one scale factor is needed. Anchoring the web sun (5 game lux
× colour luminance 0.819) at 100,000 lx gives **1 game lux = 24,400 lx by day**:

| Web quantity | Game units | Physical equivalent |
|---|---|---|
| Sun on a surface facing it | 5 × `#ffe6c6` | 100,000 lx (the anchor) |
| Sun on the road (52° elevation) | 3.23 luminous | 79,000 lx |
| Hemisphere fill on open ground | 0.56 | 13,700 lx |
| Image-based sky fill on open ground | 0.7 (clear) … 1.0 (with clouds) **(estimate from the sky formula, not measured)** | 17,000 … 25,000 lx |
| Sunlit : shaded open ground | (3.23 + 1.4) : 1.4 = about 3.3 : 1 | Shade is lifted: the art bible's physical sky gives about 5.5 : 1 (its sun-to-sky ratio of 4.5 : 1, plus one) |
| Exposure | × 1.1, then ACES with its 1 / 0.6 gain | EV100 ≈ 13.4 if Unreal's curve needs no such gain (check with a grey card) |
| An 18 % card flat in open sun | displays at about sRGB 163 | – |
| The same card in open shade | displays at about sRGB 79 | – |

So the web day picture is exposed about three quarters of a stop brighter than the art bible's open-sun target
(EV100 14.2), and its shade is about three quarters of a stop more open than physics. The art bible reaches the
same readability with local exposure and a clamped auto exposure instead.

### 4.6 Light by night, and the lamps

| Web element | Unreal feature | Notes |
|---|---|---|
| Night key (warm, steep, shadow-casting, from the south-east) | Not ported (art bible 2.6): real lamps with real shadows replace it | It is the web game's stand-in for 90 lamps it could not afford. If night readability fails in playtests, a faint unshadowed fill is the fallback: see 6 |
| Cool hemisphere 1.7 | Sky Light, steel blue, raised for readability | Art bible: 0.6 … 1.0 lx |
| 90 lamps (2.17) | One light actor per lamp from `atmos.json` → `lamps.list` | Kind → light type and photometry: art bible 2.6. Aim: the lamp's `aim`; neon and window lamps face out from their wall and 35° down |
| Light pools, cones, glows, the sheen | Not ported: they are what real lights, volumetric fog and bloom produce | Pool sizes in 2.17 are a check on cone angles: a cobra head lights about 7.2 m radius, an El lamp 4.4 m, a cage flood 10.8 m |
| The moving rig of 4 … 12 real lights | Not ported (MegaLights or a shadow budget per tier: art bible 9.3) | – |
| Virtual lamps beyond the bounds (40) | Cheap unshadowed lights or emissive cards with a ground glow, to 150 m | El row every 10 m, street lamps every 31 m at Y ± 750, Z 770 |
| Tired lamps (2 of the El or door lamps, chosen by the seed) | Two hand-picked lamps with the flicker of 3.6 on light and lens together | Art bible 7 |
| Under-El stutter while a train passes | Light function or Blueprint on the 9 El lamps | 3.6 |
| Night sky | Sky dome material: gradient, western glow, moon, sparse stars, thin clouds (2.16) | Art bible 2.6 gives nits |
| Night image-based light with lamp blobs | Sky Light capture of the real scene | – |

The web night in physical terms **(derived)**: anchoring 20 lx under a cobra head at its nominal 90 game cd gives
**1 game cd = 23.5 cd at night**, EV100 ≈ 3.1.

| Kind | Game cd × real-light gain | Equivalent | Art bible target |
|---|---|---|---|
| street | 90 × 1.3 | 2,750 cd | 3,000 cd |
| el | 30 × 1.5 | 1,060 cd | 1,800 cd |
| work (shop) | 34 × 3.4 | 2,720 cd | to give 500 … 800 lx on the floor |
| flood (cage) | 160 × 1.7 | 6,390 cd | 12,000 … 15,000 cd |
| neon | 12 × 1.4 | 395 cd | rect light per sign |
| window | 10 × 1.0 | 235 cd | rect light inside |
| Night key on the road | 2.6 × 0.568 × 0.9 | 31 lx everywhere the key reaches | none |
| Cool ambient | 1.7 × 0.24 | 9.6 lx | 0.6 … 1.0 lx |

The two anchors differ by a factor of about 1,000 (10 stops), which is the real difference between a sunny street and
a lit street at night. Effect lights and glowing sprites do **not** follow it: a muzzle flash is 45 game cd by day
and by night, so in physical units it must be about 1,000 × stronger by day to look the same. Author effect
brightness relative to the scene exposure (art bible 2.7, "relative to scene white"), not in fixed candela.

### 4.7 Sky, clouds, haze

- **Exact haze** (recommended where parity matters): the formula of 3.7 as a material function. Use it in a
  post-process material placed before translucency for opaque geometry, and call the same function in translucent
  effect and sky materials, as the web game does. It is the only way to reproduce the extra extinction outside the
  bounds, which is what hides the edge of the far city.
- **Native fog** **(proposal, to tune)**: Exponential Height Fog with a very low height falloff. Its extinction is
  plain exponential, so it cannot match a squared-exponential curve everywhere; match the playable range first.

| Distance | Day, web | Night, web | Why it matters |
|---|---|---|---|
| 40 m (4,000 cm) | 1.6 % | 5.6 % | A firefight |
| 68 m (6,800 cm) | 4.6 % | 15.3 % | Across the block, north to south |
| 92 m (9,200 cm) | 8.3 % | 26.3 % | The length of the avenue |
| 150 m (15,000 cm) | 20.6 % | 55.5 % | Longer than the block's diagonal (114 m) |
| 200 m (20,000 cm) | 33.6 % | 76.3 % | Only reached looking out of the block |

These are the view-depth term alone. Anything outside the bounds also gets the second term of 3.7 (20 % at 25 m
out, 59 % at 50 m, 98 % at 105 m), which dominates there; the skyline rings do not use the function at all but a
fixed share of haze (2.18).

- **Directional tint**: by night the haze is three times brighter and orange toward the west and bluish toward the
  east (2.15); by day it is 10 % warmer toward the west. In Unreal: the fog's inscattering cubemap, or the
  directional inscattering colour pointed west at night.
- **Clouds**: day cumulus cover and drift from 2.16. Night: thin wisps lit from below by the western glow.

### 4.8 The city beyond, the train, street life

| Web element | Unreal feature |
|---|---|
| 66 far buildings (2.18) | Instanced low-detail meshes from the brief `architecture_far_walkup` on the plan of 2.18 (the plan is seeded: rebuild it with the same rules, or place by hand), Nanite or HLOD; no collision; they must fade into the haze by 150 m |
| Skyline rings | Two rings of cards or distant meshes at 21,500 and 39,500 cm, sunk 36 … 74 % into the haze (briefs `architecture_skyline_*`) |
| Aviation lights, far traffic, plane, switching windows (night) | Emissive sprites on timelines (Niagara or material animation) with the periods of 2.18 |
| El past the bounds | The level's own El kit continued to 150 m past both ends (the level spec owns the kit) |
| The train | A Blueprint actor on a straight path: five instances of `SM_El_TrainCar` 1,610 cm apart, the state machine of 3.8, events for the audio, window emissive × 0.1 by day. Real shadows by day; at night rect lights inside the cars throw the stripes through the ties (no stripe shader). Strobe: one movable point light with the timing of 3.8. Arc: a blue flash and `NS_Sparks`. Grit: `NS_Dust` puffs and `NS_TrainGrit` under the deck. Camera shake: a shake source whose strength follows 3.8 |
| Steam (6 points) | `NS_Steam`, one per vent of `level.json` → `steam`, lit by the scene |
| Hydrant | `NS_HydrantSpray` at the nozzle; the wet patch is the material capsule of 4.3 |
| Moths and dust | `NS_Moths` on the 8 brightest open-air lamps, night only |
| Loose paper | 7 instances of `SM_Fx_PaperSheet` driven by the rules of 3.9 (a small Blueprint or Niagara with collision); not physics bodies |
| Pigeons | `SK_Pigeon` or a vertex-animated mesh on the three orbits of 2.19, day only. Reacting to gunfire and trains (art bible 7) is new behaviour, not in the web game |

### 4.9 Effects as Niagara systems

One system per recipe of 2.25; counts, speeds, sizes, colours and lifetimes transfer directly (× 100 for cm).
Field mapping: size → sprite size (the web value is the diameter); curve → size-over-life curve u^curve; ramp →
colour-over-life; drag → Drag (same 1 / s value); gravity in g → Gravity Force −981 × g on Z; wind share → a
wind force toward the global wind; turbulence m / s² → Curl Noise or the sine jitter of 3.10, × 100; stretch →
velocity-aligned sprite with length = speed × stretch, capped at 45 × the width; `BOUNCE` / `DIE` → Collision
module (restitution 0.25 … 0.55, friction to keep 65 %) or Kill on collision. Lit pool → a lit translucent
material (volumetric per-vertex or surface lighting, receiving the sun and local lights, soft against opaque
geometry); additive pool → unlit additive.

| System **(proposed names)** | Recipe | Spawned by |
|---|---|---|
| `NS_MuzzleFlash_World` | 2.25, scale parameter | Goon rifle 0.7, Buzzard 0.6 |
| `NS_MuzzleFlash_FirstPerson` | The weapon's cards (brief `fx_muzzle_flash_cards` in `assets/weapons.json`) + 2 sparks | Player weapon |
| `NS_Tracer` | One ribbon or stretched sprite per shot; colour parameter | Player `#ffe2a8`, Goon `#ff3a22` |
| `NS_TracerSmoke` | 5 wisps along the first 7 m | With a tracer, at most every 0.07 s |
| `NS_Impact_Masonry` (dust and chip colour parameters for asphalt, concrete, brick) | 2.25 | `impact` event |
| `NS_Impact_Metal`, `_Car`, `_Glass`, `_Wood`, `_Rubber`, `_Dirt`, `_Cloth` | 2.25 | `impact` event |
| `NS_Impact_Body` | The dry puff: `flesh` | A hit on a Goon |
| `NS_Impact_Drone` | Electric sparks | A hit on a Buzzard |
| `NS_Explosion_Fuel`, `NS_Explosion_Drone` | 2.25 with scale parameter s | `explosion` event |
| `NS_PropaneJet` | Emitter `jet`: scale and a 0 … 1 pressure parameter | Explosive prop, for its fuse |
| `NS_Smolder`, `NS_Embers` | Emitters | Blast site |
| `NS_Steam` | Emitter `steam` + the column of 2.19 | Level vents |
| `NS_Sparks`, `NS_SmokePuff`, `NS_SmokeWisp`, `NS_Dust`, `NS_LandingDust` | Building blocks of 2.25 | Buzzard damage, train, barrel smoke, landings |
| `NS_Fire`, `NS_Drip` | Emitters `fire`, `drip` | Nobody (2.26): build only if wanted |

Budgets map to Niagara scalability (effect types): distance cull at 15,000 cm, half the spawn count beyond
5,500 cm, spawn-count scale 0.4 / 0.5 / 0.8 / 1 / 1 by tier (the art bible's 9.3 uses 40 / 70 / 100 / 100 %), and
hard instance caps in the spirit of 2.23: about 1,400 lit and 3,000 additive sprites, 48 tracers, 256 debris
bodies, 60 casings, 256 decals. Low-priority spawns (wisps, trails, ambience) yield first.

Lights from effects: at most 6 at once in the web game, each a point light that falls linearly to zero
(Niagara light renderer or a small pool of light components); impact glints are rate-limited to one per 0.07 s.
Brightness: see the end of 4.6. In multiples of scene white (web value × exposure / 0.6): night × 2.33; day × 1.83,
and by day additive sprites are another × 2.4 and tracers × 2.2 on top. A player tracer is therefore
8 × 2.33 = 19 × white at night and 8 × 2.2 × 1.83 = 32 × white by day; the art bible's range is 8 … 16.

The day "body" of additive sprites and tracers (2.23): in Unreal a second, alpha-blended dark sprite behind the
additive one, or a single translucent material that both darkens and adds, enabled by the day parameter.

### 4.10 Decals, casings, debris

- **Bullet holes and scorch**: deferred decals from the decal set of 2.24, sizes × 100 (for example brick
  25 … 36 cm, metal 12 … 17 cm, glass 30 … 46 cm, scorch 340 … 430 cm × s), random roll, in a ring buffer of 256
  with no fade. None on characters, none on moving doors. The art bible asks for parallax or mesh-backed holes.
- **Removal**: when an explosive prop blows, delete decals within 130 cm of it that sit at least 100 cm above the
  ground.
- **Casings**: mesh particles or pooled static meshes (briefs in `assets/weapons.json`) with the bounce rules of
  2.25; 60 at most, the oldest replaced; one bounce sound per casing. The web casings are a third oversize.
- **Debris**: mesh particles from the `fx_debris_*` briefs with collision, 256 at most.

### 4.11 Post-processing and feedback

| Web | Unreal |
|---|---|
| HDR target, MSAA | Default deferred renderer; TSR |
| Bloom with threshold | Standard bloom. The web thresholds are on unexposed radiance: 1.05 at night and 2.4 by day are 2.45 and 4.4 after exposure **(derived)**. Art bible 2.3, 2.8 give intensities |
| Exposure, ACES | Manual or clamped auto exposure; the engine's filmic curve |
| Vignette 0.12 / 0.34, grain 0.008 / 0.03, aberration 0.0004 / 0.001, saturation 1.05 / 1.08 (day / night) | Post Process Volume settings per scenario. Aberration moves red and blue apart by about ± 0.8 px by day and ± 1.9 px at night in the corners of a 1,920 px wide frame, and by nothing in the centre |
| Feedback (damage, low health, aim, flash, fade, saturation) | One post-process material with six scalar parameters (2.21), driven by the player and the game flow. The constants are in exposed scene-linear units: the hit tint [0.3, 0.008, 0.006] displays as about sRGB (158, 0, 10) **(derived)**; the white-out reaches 2.2, well past clipping |
| Interior blend | A Post Process Volume in the shop with a 1 s blend, plus the haze and ambient scaling of 3.3 if the exact haze is used |

### 4.12 Scalability

The five web presets map onto the art bible's four tiers (9.1, 9.3). What must hold on every tier, because the web
game keeps it on every preset: bloom, the sun's shadows, impact dust (never thinned out), the train and its grit,
steam (60 % of the puffs on the low tiers), tracers and muzzle flashes at full brightness. What the low web presets
drop: light cones, moths, the taller far rows, the far skyline ring, switching windows. Dynamic resolution (3.14) maps
to Unreal's dynamic resolution or TSR screen percentage; its thresholds (step down above 21.5 ms, up below 17.4 ms,
floor 60 %) describe a 60 Hz target and can seed the engine's settings, but the governor itself is not ported.

---------------------------------------------------------------------------------------------------

## 5. Art and audio implications

**Asset briefs**: `docs/unreal/spec/assets/signs-fx.json` holds one brief per thing this subsystem needs modelled:
the storefront and street signs with their exact text, the construction boards, plates and banners, the mural, poster
and graffiti sets, road markings and ground decals, the window kit of the upper storeys, the El train car, the far
city blocks and skyline rings, the debris meshes, the loose paper sheet, the pigeon, the bullet-hole and scorch decal
sets and the flipbook sources. Related briefs owned by other specs, not repeated there: shell casings and the
first-person flash cards (`assets/weapons.json`), the Buzzard bolt and wreck (`assets/characters.json`), licence
plates, the IPX billboard with its face, the bus shelter with its one-sheet, the IPX truck livery, traffic-sign
faces, street lamps, court lights, floodlight stands and the water tower (`assets/props.json`).

**What the art has to carry that the web game faked:**

- Every surface at real scale with wear that has a cause (2.5 lists the causes the web painters already imply:
  rust weeping from tie holes and rivets, gum on the sidewalk, grime in the laps of roll gates, a dark band at the
  foot of walls, oil in the parking lanes, cracks across the roadway).
- Upper storeys with real windows on three repeating facade grids (2.7), or on per-building variations of them.
- Signs as objects with depth, fixings and a light source (art bible 5.2), artwork exactly as in 2.9.
- A wet state for the whole street (night) and for the hydrant's reach (day).
- Lamp fixtures whose lenses are dark by day and bright at night.
- A train with an interior worth seeing through its windows at night (poles, seats, riders as silhouettes).
- Flipbooks for the fireball, the smoke column, the dust ring, steam and the propane jet, rendered from fluid
  simulations; sprites for sparks, embers and glints can stay procedural.

**Texture sets this subsystem asks for:** the tiling sets of 4.3; unique sets for each sign face, the mural, each
poster variant, the graffiti and stencil decals, the road markings, the ground decals, the bullet-hole and scorch
decals, the train car (exterior and interior), the far walk-up fronts and the two skyline strips.

**Audio cues raised here** (the sounds themselves are in `docs/unreal/spec/07-ui-audio.md`):

| Cue | When | Data |
|---|---|---|
| `train:pass` | Three times per pass: `approach`, `over`, `gone` | phase, duration (8.79 s, 10.41 s, 8.79 s), direction; the train's live extent and track for placing the loops |
| Train squeal | Once on 70 % of passes, 20 … 60 % into `over` | – |
| `shell:bounce` | First floor contact of each casing | position, surface |
| `impact` (consumed, not raised, by effects) | Every bullet strike | point, normal, surface (`asphalt`, `concrete`, `brick`, `wood`, `dirt`, `metal`, `car`, `rubber`, `glass`, `cloth`, `flesh`, `drone`), direction |
| `explosion` (consumed) | Every blast | position, radius, source |
| Propane hiss | While a jet burns: volume rises 25 % → 100 % over the fuse | – |
| Steam hiss, neon buzz | Loops at the 6 vents and near lit neon | positions from the level and the lamp list |
| Arc under the train | With each arc flash (22 % of strobe flashes) | No sound in the web game; a crackle would fit |

---------------------------------------------------------------------------------------------------

## 6. Open questions and risks

1. **Night without the fake key.** The web night leans on a 31 lx warm key and a 9.6 lx cool ambient everywhere
   (4.6). The art bible replaces both with real lamps and a 1 lx sky. Whether a Goon still reads against a wall at
   40 m in the alley, the rear lane and the vacant lot needs a playtest; the bible's answer is extra practicals.
2. **Lamps and signs by day.** The web game leaves lamp lenses, tail lights and the billboard at night brightness
   by day and signs at 30 … 55 %; `docs/DESIGN.md` says "simply lit signage" and the art bible says lamps off. Confirm
   that the web behaviour is an omission and not a wanted look.
3. **Sub lines on the deli and chicken signs** are painted pale yellow on yellow and cannot be read (3.15). Fix
   the colour (the headline colour is the obvious choice) or reproduce the web game?
4. **Neon stutter.** No sign stutters in the web game, by accident of the grouping (2.26). The art bible wants one
   flickering stroke of neon: which sign?
5. **Two winds.** Effects drift east at about 0.5 m / s; steam columns and paper drift west at 1.1 m / s (4.2). One
   wind should be chosen for Unreal; the effects value is the one smoke and blast columns were tuned with.
6. **Exaggerated sizes.** Brass is a third over life size, the sun disc 2.3 × and the moon 3.7 × real. The art bible
   chooses real sizes for sun and brass; small brass on dark asphalt may be invisible in play.
7. **Three facades for the whole block.** The level's per-wall window settings are ignored and three grids repeat
   everywhere (2.7). Port the three grids as they are, or use the ignored per-wall values to vary the buildings?
8. **Fonts and the IPX logo.** All sign metrics here are layout sizes measured with fallback fonts; artwork must be
   typeset in Anton and Archivo, and the IPX lozenge is a typeset placeholder until the real logo arrives.
9. **Flipbook sources.** Blender fluid simulations for fire, smoke and dust are assumed; nobody has rendered one
   yet, and the web sprite sheets are too stylised to reuse except for sparks, glints and rings.
10. **Haze.** The exact formula needs a post-process material and matching calls in translucent materials; the
    native fog cannot reproduce the extinction outside the bounds. Decide early: it sets how the far city is built.
11. **Tone curve calibration.** The exposure equivalents in 4.5 and 4.6 assume Unreal's filmic curve corresponds to
    three.js' ACES fit without its 1 / 0.6 gain. Check with the grey-card values before trusting any EV here.
12. **Image-based fill is an estimate.** The day sky's contribution (0.7 … 1.0 game lux) was integrated from the
    sky formula, not read from a render; the sunlit-to-shade ratio of 3.3 : 1 inherits that uncertainty.
13. **Seed-dependent dressing.** Random street decals, the choice of the two tired lamps, the far-city plan and the
    skyline strips depend on the run seed (default 1994). The tables here are for that seed; which two lamps are
    tired was not recorded.
14. **Pigeons and litter that react.** Birds breaking on gunfire and extra litter are art-bible additions with no
    web behaviour to port; they need their own small design.
15. **Performance of real lights at night.** 90 lamps plus sign and window lights, all shadowed, depend on
    MegaLights or a shadow budget (art bible 9.3); the web game's pools and cones were its way round the same
    problem.
