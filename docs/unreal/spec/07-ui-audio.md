# 07 — HUD, menus and audio

Port spec for the Unreal Engine 5 rebuild of MURDER INC. The web game is the ground truth. Everything below was read
from the source files listed in 2.1. Values marked **(measured)** are not typed anywhere in the source: they were
obtained by running the game's own code (the production build `dist/index.html` in headless Chromium at a
1920 × 1080 viewport for the screen boxes; the audio synthesis modules in Node 22 for durations and levels).

How to read this document:

- **px** means CSS pixels of the web game. At device pixel ratio 1 a CSS pixel is a screen pixel. All measured boxes
  are `x, y, w × h` from the top-left corner of a 1920 × 1080 viewport, Story mode, player at the start position.
  They were taken with the game's web fonts (Anton, Archivo) loaded; boxes whose size depends on the text shown are
  marked ≈.
- Web units are metres, seconds and radians. +Y is up, north is −Z, east is +X. Yaw 0 faces −Z and grows turning left
  (counter-clockwise seen from above); forward = (−sin yaw, 0, −cos yaw) (`docs/CONTRACT.md:20`). Section 4 gives the
  Unreal values (cm, cm/s, degrees).
- "2D" = played flat, no position. "3D" = panned and attenuated from a world position.
- `τ` is the time constant of an exponential approach (`setTargetAtTime`): 63 % of the way after τ, 95 % after 3 τ.
- A gain of 0.5 is −6.0 dB; dB = 20 · log10(gain).

---------------------------------------------------------------------------------------------------

## 1. Overview

This subsystem is everything the player reads and hears that is not the 3D picture itself. The **HUD** is a flat
layer over the view in one deliberate dark "New York transit sign" identity (black enamel plates, white grotesque
type under a thin white rule, coloured route bullets, taxi yellow as the only accent, signal red for danger): a
mission badge top-left (IPX mark, the three reel bullets, the objective line), a rotating minimap top-right with the
name of the place under it and pause / settings buttons beside it, a weapon bar with ammunition and an always-visible
health bar bottom-centre, a spread-driven crosshair with a three-tier hit marker, damage direction arcs and the
hold-to-grab ring in the centre, a kill feed left-middle, a contact banner top-centre, typed radio subtitles above the
weapon bar, and route-bullet pins that mark the reels and the truck in the world. The **menus** are a title screen
over a fly-through of the block, an intro location card, pause / death / debrief cards and a settings / controls
drawer, all usable by mouse, keyboard and gamepad. The **audio** is fully procedural: 102 named sounds (188 rendered
variants, about 37 MB decoded) cover both guns with separate street and shop tails, reload foley, footsteps and
bullet impacts per surface, hit and kill confirms, explosions, the two enemy types, the El train, day and night
street beds with far one-shots, and an original 92 BPM boom-bap score in F minor made of seven phase-locked eight-bar
stems that are layered by a 0…1 intensity value, with a riser and impact when the fight peaks and four stings for the
moments of a run. A small mixer ducks the block and the beat under gunfire, muffles everything when the player is hit
or killed, and swaps the outdoor reverb for a tight room when the player walks into the chop shop.

---------------------------------------------------------------------------------------------------

## 2. Facts

### 2.1 Source map

| File | Lines | What it holds |
|---|---|---|
| `src/hud.js` | 814 | The HUD: DOM, per-frame updates, public API (`G.hud`) |
| `src/ui/logic.js` | 437 | Pure UI rules: crosshair gap, hit marker, banner, markers, minimap maths, feed, radio queue, card rows |
| `src/ui/minimap.js` | 286 | Minimap: static plan bake and per-frame draw |
| `src/ui/glyphs.js` | 148 | Every pictogram as SVG path data |
| `src/ui/dom.js` | 96 | IPX mark, route bullet, brand tokens → CSS variables |
| `src/ui/copy.js` | 151 | Interface-only copy: settings labels, controls tables |
| `src/ui/panel.js` | 305 | Settings / controls drawer |
| `src/menus.js` | 413 | Title, cards, location card, gamepad navigation (`G.menus`) |
| `src/ui.css`, `src/base.css` | 2326, 280 | Layout, sizes, colours, type, breakpoints; boot screen |
| `src/page.html` | 28 | Page skeleton, boot markup, font link |
| `src/audio.js` | 877 | Mixer, voices, loops, mix state, public API (`G.audio`) |
| `src/audio/dsp.js` | 639 | Sample-level synthesis toolkit (pure) |
| `src/audio/sfx-weapons.js`, `sfx-player.js`, `sfx-world.js`, `sfx-enemies.js`, `sfx-ambience.js` | 238, 173, 224, 253, 399 | Sound definitions |
| `src/audio/music.js` | 430 | The score: stems, riser, impact, stings, boombox mix (pure) |
| `src/audio/library.js`, `queue.js` | 108, 106 | Name → definition, rendering one variant; background render queue |
| `src/audio/conductor.js` | 297 | Music player: phase-locked stems, intensity layers, grid-quantised stings |
| `src/audio/ambience.js` | 266 | Beds, wind, neon, steam, far one-shots, the train, reel boomboxes |
| `src/audio/react.js` | 377 | Game events → sounds; rotor, heartbeat and reel-grab trackers |
| `src/stubs/hud.js`, `menus.js`, `audio.js` | 152, 145, 18 | Minimal stand-ins: they define the smallest API the rest of the game needs |

Read as well, because they feed this subsystem: `src/config/brand.js`, `src/config/text.js`, `src/config/flow.js`
(`timing`, `music`, `pacing`), `src/game.js` and `src/game/music.js`, `radio.js` (who calls the HUD, the menus and the
audio, and when), `src/core/settings.js`, and the `menuNav` / `glyph` / `hint` parts of `src/input.js` and
`src/config/player.js`.

### 2.2 Brand tokens

Single source `src/config/brand.js:24-57`, mirrored as CSS variables in `src/base.css:28-57`. Enter the hex values in
Unreal as **sRGB**; the linear column is for materials.

| Token | sRGB hex | Linear RGB (0…1) | Use |
|---|---|---|---|
| `bg` | `#07080a` | 0.0021, 0.0024, 0.0030 | Page behind the view, boot screen, text on yellow, outlines round HUD marks |
| `plate` | `#0f1114` | 0.0048, 0.0056, 0.0070 | Enamel plates: cards, HUD blocks, drawer |
| `plateEdge` | `#2a2e35` | 0.0232, 0.0273, 0.0356 | Hairlines, slider track, segmented-control border |
| `ink` | `#f4f2ec` | 0.9047, 0.8879, 0.8388 | Primary type, the rule above text, crosshair, health fill |
| `inkDim` | `#b4b2ab` | 0.4564, 0.4452, 0.4072 | Secondary type, inactive weapon slot |
| `inkFaint` | `#8b8983` | 0.2582, 0.2502, 0.2270 | Tertiary type, key hints, footnotes |
| `gold` | `#f6c21a` | 0.9216, 0.5395, 0.0103 | The accent: primary button, active slot, objective label, banner, headshot, player arrow |
| `red` | `#e2222b` | 0.7605, 0.0160, 0.0242 | Danger only: damage arcs, kill marker, feed bar, critical health, enemy pips, alarm cue |
| `oxblood` | `#6b1218` | 0.1470, 0.0060, 0.0091 | Vulture crew colour (not used by the interface) |
| `cyan` | `#39d0e0` | 0.0409, 0.6308, 0.7454 | Neon secondary (not used by the interface) |
| `line1` | `#f2762e` | 0.8879, 0.1812, 0.0273 | Route bullet of reel 1 (orange) |
| `line2` | `#1fa463` | 0.0137, 0.3712, 0.1248 | Route bullet of reel 2 (green) |
| `line3` | `#3b82f0` | 0.0437, 0.2232, 0.8714 | Route bullet of reel 3 (blue) |
| `lineIpx` | `#f6c21a` | = gold | Route bullet of the IPX truck |

Derived surfaces (`src/ui.css:9-22`, `83-103`):

| Name | Definition | Where |
|---|---|---|
| `plate-a` | `plate` at 84 % opacity | Most HUD plates, buttons |
| `plate-b` | `plate` at 93 % opacity | Minimap plate, banner, cards, active slot, radio line |
| `shade` | `bg` at 62 % opacity | Distance tag of a world marker |
| `hair` | 1 px line, `plateEdge` | Table rows, drawer edge |
| `rule` | 2 px line, `ink` | The transit-plate motif: a thin white rule above a block of text |
| HUD text shadow | 0 / 1 px / 2 px blur, `bg` at 70 % | Every HUD text (`src/ui.css:91`) |
| Plate shadow | inset 1 px top highlight `ink` at 8 %, drop 0 / 6 / 18 px `bg` at 35 % | `.plate` (`src/ui.css:100-103`) |

Type (`src/config/brand.js:53-57`, font link `src/page.html:27`):

| Role | Face | Weights in use | Fallback stack |
|---|---|---|---|
| Display | **Anton** | 400 | Impact, Haettenschweiler, a local condensed bold scaled 96 % ("MI Narrow"), a local heavy grotesque scaled 65 % ("MI Heavy"), Arial Narrow (`src/base.css:7-24`) |
| UI | **Archivo** | 400, 500, 600, 700, 800 and 800 italic | Helvetica Neue, Helvetica, Arial, Inter, system-ui |
| Mono | system monospace | — | Debug read-outs only (the stub HUD) |

Numbers use tabular figures everywhere a value changes in place (`.num`, `src/ui.css:24-27`). Base text is
400 15 px / 1.4 (`src/base.css:77`). Uppercase labels are set with wide tracking (0.14 to 0.36 em).

### 2.3 Shared components

| Component | Geometry | Type and colour | Source |
|---|---|---|---|
| **Rule** | 2 px `ink` line across the top of a text block | — | `src/ui.css:14` |
| **Route bullet** | Circle, diameter 1.7 em, border 0.14 em in the line colour, fill `bg`. Done or world marker: filled with the line colour. Codes longer than one character ("IPX"): a pill, padding 0 / 0.55 em / 0 / 0.45 em, filled | Numeral 800 weight, `ink`; pill text italic, `bg`, tracking 0.04 em. At 13 px type the circle is 22.1 px (measured) | `src/ui.css:31-75`, `src/ui/dom.js:72-75` |
| **IPX mark** | The word "IPX" in a lozenge: border 0.1 em in the text colour, fully round, padding 0.1 / 0.6 / 0.08 / 0.48 em | Italic 800, uppercase, tracking 0.05 em, line height 1.05. Sizes: 17 px boot, 16 px title (49 × 22 px measured), 13 px badge and cards (40 × 18 px measured) | `src/base.css:115-128`, `src/ui.css:77-79`, `src/ui/dom.js:64-66` |
| **Button** | Min height 46 px, padding 10 × 16 px, border 1.5 px `ink` at 30 %, radius 4 px, `plate-a`; label left, glyph right | 700 13.5 px, tracking 0.14 em, uppercase. Hover: border `ink`, `plate-b` | `src/ui.css:1044-1067` |
| **Primary button** | Min height 54 px, fill and border `gold`; a 22 px arrow glyph at the right edge | 800 15 px, tracking 0.18 em, text `bg`. Hover: border `ink` | `src/ui.css:1069-1088` |
| **Quiet button** | Transparent, no border | Text `inkDim`; hover: border `ink` at 30 %, text `ink` | `src/ui.css:1090-1099` |
| **Focus ring** | 2 px `gold` outline, 3 px away from the control | Shown for keyboard focus and for gamepad focus | `src/ui.css:1101-1111` |
| **Segmented control** | Container padding 3 px, radius 5 px, `plate-b`, inner 1 px `plateEdge` border; equal-width options, min height 36 px, radius 3 px | 700 12.5 px, tracking 0.06 em, `inkDim`. Selected: fill `ink`, text `bg`. "Implied" (the tier Auto quality picked): fill `ink` at 22 %, text `ink` | `src/ui.css:1122-1158` |
| **Field label** | 2 px `ink` rule above, 6 px gap, 6 px below | 700 10.5 px, tracking 0.22 em, uppercase | `src/ui.css:1160-1169` |
| **Key cap** | Min width 1.6 em, padding 3 / 6 / 2 px, border 1 px `ink` at 35 % with a 2 px bottom edge, radius 3 px, fill `plate` | 700 11 px, tracking 0.04 em | `src/ui.css:1177-1190` |

Pictograms (all drawn by the game as flat single-colour shapes that take the colour of their context;
`src/ui/glyphs.js`). The numbers are the artboard each is drawn on.

| Glyph | Artboard | Description | Lines |
|---|---|---|---|
| CHOPPER | 104 × 36 | Compact carbine in profile, muzzle right: stock, receiver, top rail and rear sight, grip, trigger guard, curved magazine, handguard with three lightening cuts, foregrip, barrel, muzzle device, front sight | 16-29 |
| NINE | 60 × 36 | Service pistol in profile, muzzle right: slide with sights, beavertail, frame, raked grip with two grooves and base plate, trigger guard as an open loop (stroke 1.7) | 32-46 |
| Fist (melee) | 36 × 36 | Closed fist, knuckles up: four rounded fingers, a palm block, a thumb across (rotated −11°), a cuff | 49-59 |
| Pause | 24 × 24 | Two bars 4 × 14, radius 1 | 62-64 |
| Gear (settings) | 24 × 24 | Eight teeth, outer radius 9.6, inner 7.1, hole radius 3.6 | 67-88 |
| Arrow | 24 × 24 | Right arrow, stroke 2.4, square caps | 91-95 |
| Close | 24 × 24 | Cross, stroke 2.2 | 98-102 |
| Record | 64 × 64 | A disc radius 30 with four grooves (radii 26.5, 23, 19.5, 16), two opposite sheen wedges (white at 22 %), a label radius 11 and a spindle hole | 105-119 |
| Damage arc | 200 × 200 | A 48° arc segment of radius 88 (stroke 4) centred on straight up, with a chevron outside it pointing outward (stroke 2.6) | 122-129 |
| Prompt ring | 48 × 48 | Track and progress circles of radius 19, stroke 3; progress starts at 12 o'clock and runs clockwise | 132-148 |
| Touch glyphs | 32 × 32 each | `fire` (a cartridge), `ads` (a reticle), `jump`, `crouch` (figures), `reload` (a magazine), `swap` (two arrows), `melee` (a fist), `interact` (a master reel), `pause`, `sprint` (double chevron). Line art, stroke 2.2, round caps | `src/config/player.js:334-366` |

### 2.4 HUD layout variables

`src/ui.css:9-22`, overrides `1829-1836` and `1944-1951`.

| Variable | Default | Width ≤ 760 px | Height ≤ 520 px |
|---|---|---|---|
| Top inset `hud-top` | 12 px + safe area | — | 8 px + safe area |
| Bottom inset `hud-bottom` | 10 px + safe area | — | 6 px + safe area |
| Side gutters | max(16 px, safe area) (`src/base.css:55-56`) | — | — |
| Minimap side `map` | 150 px | 110 px | 104 px |
| Weapon slot `slot-w` × `slot-h` | 168 × 58 px | 138 × 50 px | height 46 px |
| Melee slot width `melee-w` | 64 px | 52 px | — |
| Weapon bar block height `wbar-h` (where the radio sits above) | 118 px | 104 px | 96 px |

The web HUD does **not** scale with the window: every size above is a fixed pixel size, so the HUD is relatively
smaller on a larger viewport. Only a few display-face sizes follow the viewport (`clamp()` with `vw`). The two
breakpoints exist for phones.

### 2.5 HUD elements

Boxes are measured at 1920 × 1080. "Anchor" is the rule that places the element at any size.

| # | Element | Anchor | Box at 1920 × 1080 | Look | Source |
|---|---|---|---|---|---|
| 1 | **Mission badge** | Left gutter, top inset | 16, 12, ≈277 × ≈100. Width fits content: min 210, max min(320 px, 40 % of the width) | `plate-a`, radius 6, padding 10 / 14 / 11, a 3 px `gold` bar inside the left edge | `src/ui.css:107-118` |
| 1a | Badge top row | — | Height 26 | IPX mark 13 px; three route bullets 13 px, gap 5; count "0/3" pushed right: 700 13 px, tracking 0.06 em, `inkDim` | `src/ui.css:120-147` |
| 1b | Badge rule | 9 px under the top row, 6 px above the label | Full inner width × 2 | `ink` | `src/ui.css:175-180` |
| 1c | Objective label | — | Height 10.5 | "OBJECTIVE", 700 10.5 px, tracking 0.24 em, `gold` | `src/ui.css:182-187` |
| 1d | Objective text | 5 px under the label | One line 20 high; wraps | 700 16 px / 1.25, tracking 0.01 em, `ink` | `src/ui.css:189-195` |
| 1e | Holdout tally | Replaces bullets and count; own line under the IPX mark | — | Anton 21 px, tracking 0.06 em, uppercase | `src/ui.css:149-173` |
| 2 | **Minimap block** | Right gutter, top inset; a row: buttons, 8 px gap, map plate | 1708, 12, 196 × 175 | — | `src/ui.css:204-211` |
| 2a | Pause and settings buttons | Column, 8 px apart, left of the map | 38 × 38 each at 1708, 12 and 1708, 58 | Round, `plate-a`, border 1.5 px `ink` at 55 %, 20 px glyph. Hover / focus: border `gold`. Pressed: fill `gold`, glyph `bg` | `src/ui.css:213-249` |
| 2b | Map plate | — | 1754, 12, 150 × 175 | `plate-b`, radius 14, clipped; outline 1.5 px `ink` at 30 %; drop shadow | `src/ui.css:251-257` |
| 2c | Map | Top of the plate | 150 × 150 | See 2.7 | `src/ui.css:259-269` |
| 2d | Zone band | Under the map | 150 × 25 | Solid `bg`, 2 px `ink` rule on top, padding 6 / 8; 700 11 px, tracking 0.2 em, centred, uppercase, one line with ellipsis | `src/ui.css:275-286` |
| 3 | **Banner** | Centred, top inset + 6 px. Max width: viewport − 2 × (map + 90 px) | ≈747, 18, ≈425 × 52 | Text plate: padding 7 / 18 / 6, 2 px `ink` rule on top, 1 px `ink` at 40 % below, `plate-b`. Anton clamp(20 px, 2.8 % of width, 34 px) = 34 px, line height 1.05, tracking 0.14 em, uppercase, `gold`, one line | `src/ui.css:290-312` |
| 4 | **Centre message** | Centred, top inset + 70 px. Max width min(560 px, viewport − 2 × (map + 70 px)) | ≈762, 82, ≈397 × 32 | `plate-a`, radius 4, padding 7 / 14; 600 13 px / 1.35, tracking 0.04 em, centred | `src/ui.css:314-339` |
| 5 | **Kill feed** | Left gutter, 40 % down the screen; lines stack downward, newest at the bottom, 4 px apart | First line 16, 432, ≈252 × 23.5 | Each line: `plate-a`, 3 px `red` bar on the left, padding 5 / 10 / 5 / 8, gap 8; weapon glyph 13 px high (fist 15) in `inkDim`; text 700 12.5 px, tracking 0.12 em, uppercase; tag: `gold` fill, `bg` text, 10.5 px, tracking 0.14 em, padding 2 / 5 / 1, radius 2 | `src/ui.css:343-393` |
| 6 | **Crosshair** | Screen centre | Four ticks 2 × 9 px and a 2 × 2 px centre dot | `ink` with a 1 px outline of `bg` at 65 %. The gap from the centre to the inner end of each tick is computed (3.6) | `src/ui.css:397-450` |
| 7 | **Hit marker** | Screen centre | A 30 × 30 px frame turned 45°: four bars, each 11 px long, from 4 px to 15 px from the centre | Bars 2 px wide `ink` (hit), 2 px `gold` (head), 3 px `red` (kill); 1 px outline `bg` at 55 % | `src/ui.css:452-504` |
| 8 | **Damage arcs** | Screen centre | A square of min(72 % of the height, 94 % of the width) = 777.6 px; the arc sits at 88 % of its half-size (342 px from the centre), about 15.6 px thick | `red`, soft 3 px dark glow. Four pooled | `src/ui.css:506-522` |
| 9 | **Interaction prompt** | Centred, 61 % down the screen | ≈846, 659, ≈228 × 48 | A 48 px ring disc (`plate-b`; track `ink` at 22 %, progress `gold`, stroke 3) holding the key glyph (800 18 px; 11 px with tracking 0.06 em when longer than one character), 10 px gap, then a text plate: padding 8 / 13, 2 px `ink` rule on top, `plate-a`, 700 14 px / 1.3, tracking 0.03 em. While held: rule and text turn `gold` | `src/ui.css:524-591` |
| 10 | **World marker** | Projected world point (3.13) | Bullet 22.1 px, pointer 8 × 5 px under it, distance tag 6 px under the anchor | Bullet filled with its line colour, ringed 1.5 px `ink`; pointer `ink`; tag: `shade`, padding 2 / 5, radius 2, 700 11 px, tracking 0.05 em. Opacity 0.9 on screen, 0.72 pinned to an edge, 0.22 over the aim point | `src/ui.css:595-665` |
| 11 | **Weapon bar** | Centred, bottom inset; a column: cue, slots, health, 6 px apart | 754, 955, 412 × 115 | — | `src/ui.css:669-678` |
| 11a | Cue line | Centred over the slots | Min height 18 | 800 11.5 px, tracking 0.2 em, uppercase, `gold` on `plate-a`, padding 3 / 9 / 2, radius 2. Alarm: `red`, blinking | `src/ui.css:680-706` |
| 11b | CHOPPER and NINE slots | Row, 6 px apart | 168 × 58 each at 754, 984 and 928, 984 | `plate-a`, border 1.5 px `ink` at 18 %, radius 6, padding 6 / 10 / 8 / 8, content `inkDim`. Active: border 2 px `gold`, `plate-b`, content `ink`, a 3 px halo of `gold` at 22 %. Silhouette box 62 × 30 (NINE 44 × 30); name 800 10.5 px, tracking 0.18 em; count 700 15 px (19 px when active), tracking 0.02 em; key hint top-right 700 9.5 px `inkFaint`; pip row 3 px high along the bottom (active slot only), 9 px in from each side, 1 px between pips | `src/ui.css:713-842` |
| 11c | Melee slot | Right of the two guns | 64 × 58 at 1102, 984 | Same plate; fist glyph 28 px centred; key hint; no text | `src/ui.css:734-738`, `767-788` |
| 11d | **Health bar** | Under the slots | 754, 1048, 412 × 22 | `plate-a`, radius 4, padding 0 / 10, gap 10: label "HP" 800 10.5 px, tracking 0.2 em, `inkDim`; bar 8 px high (≈317 wide), radius 1, track `ink` at 14 %, cut into ten segments by 2 px gaps; number 800 16 px, right-aligned | `src/ui.css:844-906` |
| 12 | **Radio strip** | Centred, its bottom edge `hud-bottom` + `wbar-h` + 14 px = 142 px above the screen bottom. Max width min(620 px, viewport − gutters) | ≈650, 869, 620 × ≈69 (two lines) | Speaker row: a 7 px `gold` dot with a 2 px ring of `gold` at 30 %, then the name 800 10.5 px, tracking 0.26 em, `gold`. Line: 500 17 px / 1.6, `ink`, centred, each text line on its own `plate-b` strip (padding 3 / 9) | `src/ui.css:910-964` |

### 2.6 HUD timing constants

| What | Value | Source |
|---|---|---|
| HUD fade in / out | 0.35 s | `src/ui.css:88` |
| Objective typewriter | 46 characters / s | `src/hud.js:41` (same number in `src/config/flow.js:222`) |
| Objective change flash (badge rule and left bar go `ink` → `gold`) | 0.9 s, ease-out | `src/hud.js:714-720` |
| Radio typewriter | 58 characters / s | `src/hud.js:42` (same number in `src/config/flow.js:221`) |
| Radio strip fade in / out | 0.2 s / 0.3 s | `src/ui.css:923`, `930` |
| Gap between two radio lines | 0.3 s | `src/config/flow.js:224` |
| Banner length | max(3.4 s, the length asked for): contact 3.4 s, holdout wave 3.6 s | `src/hud.js:46`, `765`; `src/config/flow.js:84`, `146` |
| Centre message | Default 3 s; fade in 0.15 s (rises 4 px), fade out 0.3 s | `src/hud.js:776`, `src/ui.css:314-329` |
| Kill feed | 4 lines, each lives 4.2 s and fades over its last 0.6 s (in steps of 0.1); a new line slides in from 10 px left over 0.18 s | `src/hud.js:176`, `src/ui/logic.js:364-389`, `src/ui.css:364`, `388-393` |
| Hit marker | 0.24 s for a hit and a headshot, 0.42 s for a kill; pop scale 1.15 / 1.5 / 1.5 | `src/ui/logic.js:107-111` |
| Damage arc | 1.5 s; opacity 1 until 0.6 s is left, then linear to 0 in steps of 0.05 | `src/hud.js:43`, `src/ui/logic.js:159-161` |
| Health "ghost" | Waits 0.45 s after a loss, then drains 0.9 of the bar per second | `src/hud.js:47`, `564` |
| Critical health blink | Number flips between opacity 1 and 0.35, period 1 s | `src/ui.css:702-706`, `903-906` |
| Alarm cue blink | Same flip, period 0.7 s | `src/ui.css:697-700` |
| Crosshair | Ticks ease to a new gap in 60 ms; the whole crosshair fades in 0.1 s | `src/ui.css:404`, `423` |
| Prompt fade | 0.15 s | `src/ui.css:536` |
| Marker layer fade (aiming) | 0.12 s | `src/ui.css:598` |
| Minimap redraw | At most 32 times a second of real time | `src/hud.js:805` |
| Pool sizes | 4 damage arcs, 5 world markers, at most 60 magazine pips | `src/hud.js:44-48` |

### 2.7 Minimap constants

`src/ui/minimap.js`, rules in `src/ui/logic.js:267-311`.

| Constant | Value | Meaning | Source |
|---|---|---|---|
| View radius | 30 m | From the centre to the middle of an edge: the map shows 60 × 60 m; 2.5 px per metre at 150 px | `src/ui/minimap.js:10`, `204` |
| Margin | 24 m | City painted round the play bounds on the static plan (so the plan covers 140 × 116 m) | `src/ui/minimap.js:11`, `60-63` |
| Backing resolution | side × min(2, device pixel ratio) | — | `src/ui/minimap.js:12`, `164-173` |
| Plan resolution | clamp(round(side × ratio / 60 × 1.25), 3, 8) px per metre: 3 at 150 px, 6 at 150 px on a 2× screen | Static plan, painted once | `src/ui/minimap.js:59` |
| Pin inset | 11 px | A reel or truck bullet outside the view is pinned this far inside the rim | `src/ui/minimap.js:13`, `246` |
| Enemy pin inset | 5 px | Same for enemy pips | `src/ui/minimap.js:232` |
| Fire window | 2 s | An enemy shows this long after it fired | `src/ui/minimap.js:14`, `src/ui/logic.js:291-296` |
| "Tall" threshold | 2.2 m | A collider whose top is higher is drawn as a wall, lower as cover | `src/ui/logic.js:304-311` |
| Left out of the plan | Player-only walls, bullet-only shells, explosives, anything owned by a dynamic object, boxes whose underside is above 0.9 m (the El deck, awnings, the scaffold deck), boxes whose top is below 0.35 m (kerbs) | — | `src/ui/logic.js:305-309` |

Map inks (`src/ui/minimap.js:17-28`; all opaque):

| Ink | sRGB hex | Linear RGB | Painted on |
|---|---|---|---|
| City | `#0c0e11` | 0.0037, 0.0044, 0.0056 | Outside the play bounds |
| Ground | `#2a2f36` | 0.0232, 0.0284, 0.0369 | Inside the bounds by default: sidewalks, floors, the court |
| Road | `#191c21` | 0.0097, 0.0116, 0.0152 | Ground cells whose surface is asphalt |
| Dirt | `#2b2822` | 0.0242, 0.0212, 0.0160 | Ground cells whose surface is dirt (the vacant lot) |
| Court | `#1e2a25` | 0.0130, 0.0232, 0.0185 | Ground cells whose surface is rubber. Never used: the real level reports no rubber ground (`src/level/layout.js:196-203`) |
| Wall | `#454c57` | 0.0595, 0.0723, 0.0953 | Colliders taller than 2.2 m |
| Wall edge | `#9aa1ab` | 0.3231, 0.3564, 0.4072 | 1 px outline of every wall block (55 % opacity) and of the play bounds (50 %) |
| Cover | `#7b828d` | 0.1981, 0.2232, 0.2664 | Colliders up to 2.2 m: cars, barriers, crates |
| Rail | `#4d5460` | 0.0742, 0.0887, 0.1170 | The El's two tracks |
| Enemy | `#e2222b` | = red | Enemy pips |

Live marks, in pixels of a 150 px map (`src/ui/minimap.js:175-272`):

| Mark | Shape | Colour |
|---|---|---|
| Enemy pip | Disc radius 3.4 (2.6 and 60 % opacity when pinned to the rim) | Enemy ink, 1 px `bg` outline |
| Reel bullet | Disc radius 7.5, numeral 700 10.5 px | Line colour fill, 1.5 px `bg` outline, `ink` numeral; 92 % opacity when pinned |
| Truck bullet | Pill 26 × 15, radius 7.5, "IPX" italic 800 9 px | `gold` fill, `bg` text |
| Player arrow | Polygon (0, −8) (6, 6.5) (0, 3.2) (−6, 6.5), always pointing up at the centre | `gold`, 1.5 px `bg` outline |
| View cone | Wedge radius 0.62 × half the map (46.5 px), ±0.62 rad (±35.5°) about straight up | `ink` at 7 % |

### 2.8 HUD copy

Game copy lives in `src/config/text.js`; words only the interface uses live in `src/ui/copy.js`. The style sheet
uppercases labels; the strings below are as stored.

| Where | Text | Source |
|---|---|---|
| Objective label | `Objective` | `src/ui/copy.js:22` |
| Objective line, Story | `Take back the three master reels` → `Two reels left` → `Last reel` → `Get to the IPX truck` (index = reels secured) | `src/config/text.js:96` |
| Objective line, Hold the Block | `Vultures inbound` (before wave 1), `Hold the block` (wave running), `Catch your breath` (between waves) | `src/config/text.js:97-101` |
| Holdout tally | `Stand by`, then `Wave N · 12,345` (score with thousands separators) | `src/config/text.js:102-105` |
| Zone band | `WEST END`, `THE AVENUE`, `CHOP SHOP`, `THE CAGE`, `THE LOT` | `src/config/text.js:36-42` |
| Weapon names | `CHOPPER`, `NINE` | `src/config/text.js:65-69` |
| Ammunition | `mag / reserve`, e.g. `30 / 150`; the NINE shows `15 / ∞` | `src/hud.js:502`, `src/ui/logic.js:29-31` |
| Health label | `HP` | `src/ui/copy.js:24` |
| Cue line | `Reloading`, `Low ammo`, `R — Reload` (alarm), `Empty — Q swaps` (alarm). Touch: `Reload`, `Empty — swap`. The key names follow the device | `src/ui/copy.js:28-34`, `src/ui/logic.js:333-347` |
| Kill feed | `Goon down`, `Buzzard down`; tag `Headshot` | `src/config/text.js:83-87` |
| Interaction prompt | `Hold E — Grab reel 1` (glyph by device: `E`, `X`, `USE`) | `src/config/text.js:110` |
| Refusal at the truck | `Reels still out there — the truck won't roll without all three` | `src/config/text.js:112` |
| Banners | `Contact — NORTH-EAST` (8-way compass word), `Wave N — EAST` | `src/config/text.js:116`, `125-126` |
| Countdown message | `Wave N in 3` (then 2, 1) | `src/config/text.js:127` |
| Marker distance | Whole metres: `42 m` | `src/ui/logic.js:34-36` |
| Radio speaker | `IPX VAULT` | `src/config/text.js:132` |

Radio lines (`src/config/text.js:131-149`). "On screen" = typing time (characters / 58) + hold.

| Trigger | Line | Characters | Hold s | On screen s |
|---|---|---|---|---|
| Story, first start only, 0.9 s into the intro | "Rule, it's the Vault. Vultures stashed your three masters on this block — the avenue, the chop shop, the cage. Bring them home." | 127 | 4.4 | 6.59 |
| Hold the Block, first start only | "Rule, it's the Vault. The Vultures want the whole block back. Hold it down as long as you can." | 94 | 4.0 | 5.62 |
| First enemy alert of a run | "They made you. Goons on foot, Buzzards in the air. Handle it." | 61 | 3.2 | 4.25 |
| Reel 1 of 3 secured | "One reel back in your hands. They felt that — more coming." | 58 | 3.6 | 4.60 |
| Reel 2 of 3 | "Two reels. They're throwing the whole crew at you now." | 54 | 3.6 | 4.53 |
| Reel 3 of 3 | "That's all three. The IPX truck is idling at the south end of the lot. Move." | 76 | 4.5 | 5.81 |
| Health first under 30 | "You're hit bad. Get behind something solid and breathe." | 55 | 3.0 | 3.95 |
| Truck reached | "Masters are in the vault. The block is yours, Rule." | 51 | 2.4 | 3.28 |
| Holdout wave N cleared | "Wave N down. Resupply at your feet — 9 seconds." | 47 | 3.4 | 4.21 |

### 2.9 Menus: sizes and copy

**Title screen** (`src/menus.js:105-143`, `src/ui.css:1227-1371`). The block sits bottom-left, 4 % of the width in
from the left (min 16 px) and 18 px above the lower letterbox bar.

| Element | Box at 1920 × 1080 | Look | Copy |
|---|---|---|---|
| Letterbox bars | Top and bottom, full width × clamp(14 px, 5.5 % of the height, 52 px) = 52 px | Solid `bg`; slide in over 0.7 s | — |
| Veil | Full screen | `bg` gradient: 88 % at the left edge, 55 % at 42 % of the width, clear at 74 %; plus 70 % at the bottom fading out at 38 % of the height | — |
| Title block | 77, 497, 640 × 513 | Width min(640 px, 100 %) | — |
| Eyebrow | 77, 497, 640 × 22 | IPX mark 16 px, 12 px gap, then 700 12 px, tracking 0.26 em, uppercase, `inkDim` | `IPX` + `PRESENTS · HOLLIS, QUEENS` (`src/config/text.js:7`) |
| Wordmark | 10 px below; one line, about 840 px wide: it overhangs the 640 px block by design | Anton clamp(64 px, 12.5 % of the width, 176 px) = 176 px, line height 0.9, tracking 0.01 em, uppercase, soft 30 px dark shadow | `MURDER INC.` |
| Star line | 10 px below | 800 13 px, tracking 0.36 em, `gold` | `STARRING JA RULE` |
| Premise | 18 px below; max 34 em wide | 2 px `ink` rule on top, 12 px gap; 500 16 px / 1.45 | "The Vultures jacked three master reels. Take the block back. Get them to the truck." |
| Pickers | 20 px below; three columns 1.5 : 1.4 : 0.9, 14 px apart; each a field label and a segmented control (66.5 px high together) | — | `Mode`: `Story` / `Hold the Block`. `Difficulty`: `Hustler` / `Boss` / `Kingpin`. `Time`: `Day` / `Night` |
| Mode note | 10 px below | 400 13.5 px, `inkDim` | Story: "Take back three master reels and reach the IPX truck. About five minutes." Hold the Block: "Endless waves that keep growing. Resupply between waves. How long can you hold it down?" |
| Actions | 18 px below; three columns 1.6 : 1 : 1, 10 px apart, 54 px high | Primary, then two plain buttons | `Hit the block`, `Settings`, `Controls` |
| Footnote | 16 px below | 400 12 px, `inkFaint` | "Every street, sound and beat is generated in your browser. No art or audio files." (web-specific: replace) |
| "Controls at a glance" | Right gutter, bottom-aligned with the block, 332 wide; only when the viewport is at least 1180 × 600 | `plate-a`, 2 px `ink` rule on top, padding 14 / 16 / 12; title 800 10.5 px, tracking 0.24 em, `gold`; rows of key caps and verbs (600 12.5 px `inkDim`) | Move `W A S D`, Fire `LMB`, Aim `RMB`, Reload `R`, Swap `Q`, Grab `Hold E`, Sprint `Shift`, Crouch `C`, Melee `F`, Pause `Esc`; Controller: "Sticks · RT fire · LT aim · X reload · Y swap"; Touch: "Left thumb moves · right side looks · the bullet button fires" (`src/ui/copy.js:135-151`) |

**Cards** (`src/menus.js:194-259`, `src/ui.css:1375-1515`). One card, centred on the screen: width
min(440 px, 100 %), side padding 22 px, `plate-b`, a 3 px rule on top, bottom corners radius 8, drop shadow
0 / 20 / 60 px of `bg` at 60 %. Behind it a full-screen veil of `bg` at 60 % (35 % on the death card).

| Card | Top rule | Height (measured) | Head | Body | Buttons |
|---|---|---|---|---|---|
| **Pause** | `ink` | 412 | IPX mark 13 px; kicker `Hold up`; title `Paused` | One hint line about the mouse (400 13 px, `inkFaint`): "Resume locks the mouse back in." / "Click the street once to lock the mouse in." / empty on pad and touch (`src/config/player.js:369-376`) | `Resume` (primary), `Settings`, `Controls`, `Restart run` (quiet) |
| **Death** | `red` | 369 (Story), 444 (Hold the Block) | Kicker `Rule down`; title `Lights out` in `red`; no IPX mark | Stats. Story: `Time on the block` m:ss, `Reels recovered` n/3, `Vultures dropped`. Hold the Block: `Time on the block`, `Waves cleared`, `Vultures dropped`, `Score`, `Best` (with a `New best` flag) | `Run it back` (primary), `Back to title` (quiet) |
| **Debrief** | `gold` | 541 | IPX mark; kicker `Hollis, Queens · Debrief`; title `The block is yours` | Rating row: the record glyph 64 px in `gold`, label `Certification`, the rating name in Anton 44 px `gold` (`Demo`, `Mixtape`, `Single`, `Gold`, `Platinum`, `Diamond`). Stats: `Time` m:ss, `Accuracy` "52 %" (or "—" with no shot fired), `Vultures dropped`, `Retries` | `Run it back` (primary), `Back to title` (quiet); footer `An IPX production` (600 10.5 px, tracking 0.22 em, `inkFaint`) |

Card type: kicker 700 11.5 px, tracking 0.24 em, uppercase, `inkDim`; title Anton clamp(34 px, 6 % of the width,
50 px) = 50 px, line height 0.98; stat rows 37.5 px high separated by hairlines, label 600 13 px `inkDim`, value
800 15 px right-aligned in tabular figures; the `New best` flag is a `gold` chip (10 px, `bg` text); buttons stack
8 px apart, 18 px above and 22 px below. Copy: `src/config/text.js:151-188`, `src/ui/copy.js:39-43`. Formats: time `m:ss`
(`src/ui/logic.js:13-16`), score with thousands separators (`src/ui/logic.js:19-21`), accuracy rounded to whole percent
(`src/ui/logic.js:24-26`).

**Intro location card** (`src/menus.js:150-152`, `302-316`, `src/ui.css:1519-1550`): at 77, 695, ≈628 × 82; left
edge 4 % of the width (min 16 px), bottom edge 28 % of the height above the screen bottom. `plate-a` with a 4 px
`gold` bar on the left, padding 10 / 18 / 12 / 16. Line 1: Anton clamp(22 px, 3 % of the width, 34 px) = 34 px,
tracking 0.06 em, uppercase: `Hollis, Queens · Jamaica Ave · 4:15 PM` by day, `… · 02:14 AM` by night (the time
never breaks from its AM / PM). Line 2: 600 13 px, tracking 0.08 em, `inkDim`: `Three reels. One block. No backup.`
(Story) or `One block. Endless Vultures.` (Hold the Block) (`src/config/text.js:21-30`).

**Settings / controls drawer** (`src/ui/panel.js`, `src/ui.css:1554-1822`): a panel on the right edge, 440 px wide
(or the whole width if narrower), full height, solid `plate`, hairline on its left, shadow to the left; behind it a
scrim of `bg` at 45 % that closes the drawer when clicked. Head 53 px: two tabs `Settings` and `Controls`
(800 13 px, tracking 0.18 em, uppercase, `inkDim`; selected: `ink` with a 3 px `gold` underline) and a `Close` button
(cross glyph 14 px + label, 700 11 px, border 1 px `ink` at 25 %). Body padding 4 / 20 / 24, scrolls. Opens with a
0.25 s slide of 24 px from the right.

| Row | Control | Options or range | Shown as |
|---|---|---|---|
| `Difficulty` | Segmented | `Hustler` / `Boss` / `Kingpin` | — |
| `Weapon position` | Segmented | `Close` / `Three-quarter` / `Compact` (setting `view` 1 / 2 / 3) | — |
| `Graphics quality` | Segmented | `Auto` / `Low` / `Medium` / `High` / `Ultra`; with Auto the tier it picked is also marked "implied" | — |
| `Look sensitivity` | Slider | 0.2 … 3, step 0.05 (gamepad step 0.1) | `1.00×` |
| `Invert Y` | Toggle pill (92 × 32, knob 22 px: `inkFaint` off, `gold` on) | `Off` / `On` | — |
| `Master volume` | Slider | 0 … 100, step 1 (gamepad step 5); stored as 0 … 1 | `80%` |
| `Field of view` | Slider | 60 … 95, step 1 (gamepad step 1) | `74°` |
| `Display` | Button | `Enter fullscreen` / `Exit fullscreen` (only where the platform offers it) | — |
| Notes | Text 400 12.5 px `inkFaint` | "Quality was picked for this device (Medium). Lower it if the frame rate struggles." with Auto, else "Changes apply at once. Shadows and reflections may take a moment to catch up."; "Difficulty changes take effect at once; Vultures already on the block keep their health." | — |

Slider look: track 4 px high, `gold` up to the value and `plateEdge` after it; thumb 18 px `ink` disc with a 2 px
`bg` border; the value in `gold` 800 13 px at the right of the label row (`src/ui.css:1694-1739`). Slider specs:
`src/ui/panel.js:11-15`.

The **Controls** tab lists three tables, the device in use first (`src/ui/panel.js:172-177`); each row is an action, key
caps and an optional remark (`src/ui/copy.js:71-132`):

| Keyboard · Mouse | | Controller | | Touch | |
|---|---|---|---|---|---|
| Move | `W A S D` | Move / look | `L stick`, `R stick` | Move | Left thumb |
| Look | `Mouse` | Fire | `RT` | Look | Drag right side |
| Fire | `LMB` | Aim | `LT` | Fire | fire button: hold; drag to track. A second small trigger on the left |
| Aim | `RMB` | Reload | `X` (hold X at a reel to grab it) | Aim | aim button, toggles |
| Reload | `R` | Swap weapon | `Y`, `D-pad` | Reload, Swap weapon | their buttons; or tap a weapon slot |
| Swap weapon | `Q`, `Wheel`, `1`, `2` | Jump | `A` | Grab a reel | `USE` button, hold it |
| Grab a reel | `Hold E` | Crouch | `B`, `LB` | Jump, Crouch (toggles), Melee | their buttons |
| Jump / Sprint / Crouch / Melee | `Space` / `Shift` / `C` / `F` | Sprint | `L3` | Sprint | Stick pushed all the way forward; an arrow above the stick locks it |
| Pause | `Esc`, `P` | Melee | `RB`, `R3` | Pause | The button beside the map |
| | | Pause | `Start` | | |

Notes under the tables: keyboard: "If the browser won't lock the mouse, move it to look and rest it at a screen edge
to keep turning. Arrows or I J K L turn too, and Enter fires."; controller: "In menus the D-pad or left stick moves
the selection, A accepts, B goes back. …" (the rest of both notes is browser-specific).

**Boot screen** (`src/page.html:6-17`, `src/base.css:134-273`): the same identity as a loading screen. Centred column
520 px wide: IPX mark 17 px + "presents" (600 12 px, tracking 0.26 em, `inkDim`); wordmark Anton clamp(52 px,
20.5 % of the width, 116 px), line height 0.92; `Starring Ja Rule` 700 13 px, tracking 0.34 em, `gold`; a 2 px `ink`
rule; the status line 500 14 px; a 4 px route-line progress bar (`plateEdge` track with a stop every tenth, `gold`
fill easing 0.3 s) ; a 12 px note. Status lines and bar positions, in order (`src/config/text.js:191-205`, `src/modules.js:70-88`,
`src/main.js:361-365`): "Waking up the block" 0 → "Warming up the renderer" 0.04 → "Mixing brick, chrome and neon"
0.12 → "Parking cars on the avenue" 0.24 → "Raising the El" 0.36 → "Lighting the block" 0.52 → "Loading tracers and
smoke" 0.64 → "Racking the Chopper" 0.74 → "Waking the Vultures" 0.82 → "Waiting on the next train" 0.92 → "Ready" 1.
It fades out in 0.6 s. A fatal start-up error turns the rule `red` and shows "Murder Inc. could not start: …".

### 2.10 Settings

Stored as one JSON object under `murderinc.settings.v1`; best holdout score under `murderinc.holdout.best`
(`src/core/settings.js:4-38`). Every change applies at once and is saved.

| Key | Default | Allowed | Set from | Applied by |
|---|---|---|---|---|
| `mode` | `mission` | `mission`, `holdout` | Title picker | Flow, at the next start |
| `difficulty` | `boss` | `hustler`, `boss`, `kingpin` | Title picker, drawer | Flow, at once |
| `time` | `day` | `day`, `night` | Title picker | Atmosphere, on the title at once, else at the next run reset |
| `view` | 1 | 1, 2, 3 | Drawer | Weapon viewmodel position |
| `quality` | `auto` | `auto`, `low`, `medium`, `high`, `ultra` | Drawer | Renderer |
| `sens` | 1 | 0.2 … 3 | Drawer | Input |
| `invertY` | false | boolean | Drawer | Input |
| `volume` | 0.8 | 0 … 1 | Drawer | Audio master volume (2.11) |
| `fov` | 74 | 60 … 95, whole degrees, **vertical** | Drawer | Camera |

### 2.11 Audio engine constants

The mix graph (`src/audio.js:155-226`):

```
world, near, gun, tail (each × its bus gain) ────────────────────────────────┐
  sends: world × 0.5, near × 0.14, gun × 0.10                                 │
     ├──► STREET convolver ──► × 0.8 · (1 − 0.9 · i) ─────────────────────────┤
     └──► SHOP convolver   ──► × 0.9 · i ─────────────────────────────────────┤
amb ──► ambDuck ──► ambLevel ──► ambLowpass ──────────────────────────────────┤
                                                                              ▼
                                                      MUFFLE low-pass ──► PAUSE gain ──┐
dry (UI, hit confirms, hurt, ear ring, heartbeat, reel secured, radio) ────────────────┤
music ──► musicDip ──► musicDuck ──► musicLowpass ─────────────────────────────────────┤
                                                                                       ▼
                                                                                      SUM
SUM ──► compressor ──► × 1.15 ──► soft clip ──► VOLUME (the setting) ──► output
```

`i` is the interior factor 0…1 (3.19). The tail bus has no reverb send (the tails are the reverb of the guns). The
muffle, the pause gain and the reverbs never touch the music or the dry bus.

| Constant | Value | Source |
|---|---|---|
| Bus gains | world 1.05, near 0.95, gun 1.0, tail 0.85, amb 0.7, dry 0.95, music 0.5 | `src/audio.js:27` |
| Voice channels per bus (flat, 3D) | world (0, 26), near (12, 0), gun (6, 0), tail (8, 0), amb (2, 6), dry (10, 0), music (4, 0: unused, the score has its own sources). 70 one-shot voices in all; loops are extra | `src/audio.js:29` |
| Reverb sends | world 0.5, near 0.14, gun 0.10; amb, tail, dry, music none | `src/audio.js:30`, `199-210` |
| Default pitch jitter | ±3.5 % per play (a definition may set its own) | `src/audio.js:31`, `381-382` |
| Per-play level variation | × (1 − U(0, 0.08)) | `src/audio.js:383` |
| Default priority, distance model | priority 5; reference distance 3 m, roll-off 1 | `src/audio.js:374`, `391-392` |
| Cull distance | 160 m: a positioned one-shot farther away is not played | `src/audio.js:32`, `366-369` |
| Distance attenuation | "inverse": gain = ref / (ref + roll · (max(d, ref) − ref)); equal-power panning, no HRTF | `src/audio.js:228-236` |
| Air absorption | Per 3D voice a low-pass at clamp(20000 · e^(−d / 48 m), 1600, 20000) Hz, Q 0.5 | `src/audio.js:306`, `394`, `501-508` |
| Global impact gap | Any two `imp_*` sounds are at least 22 ms apart | `src/audio.js:360-363` |
| Master compressor | Threshold −6 dB, knee 8 dB, ratio 2.5 : 1, attack 6 ms, release 140 ms | `src/audio.js:158-163` |
| Make-up, soft clip | × 1.15, then a curve that is linear up to a level of 0.6 and `0.6 + 0.4 · tanh((level − 0.6) / 0.4)` above it (sign kept), 2× oversampled | `src/audio.js:127-136`, `164-167` |
| Master volume | The `volume` setting (default 0.8), last in the chain, τ 0.03 s | `src/audio.js:168`, `724-727` |
| Street impulse response | 1.4 s, stereo, synthetic: early slaps at 21, 47, 83, 131, 190 ms (gains 0.5, 0.35, 0.3, 0.22, 0.15), tail darkening 5200 → 700 Hz, 80 % density, unit energy | `src/audio.js:248`, `src/audio/dsp.js:620-636` |
| Shop impulse response | 0.8 s, stereo: early reflections at 7, 13, 19, 26 ms (0.6, 0.5, 0.45, 0.35), tail 7000 → 1600 Hz | `src/audio.js:249` |
| Reverb level **(measured)** | With a send of 1.0, the street return carries about −5 to −6 dB of the dry sound's energy, the shop return about −8 to −9 dB (the browser normalises impulse responses itself). A world-bus sound outdoors is therefore about 12 dB wet-below-dry, a gun about 25 dB | Measured in Chromium with the game's impulse responses |
| Music bus trim | × 0.9 inside the conductor (so stems reach the mix at 0.45 × layer gain) | `src/audio/conductor.js:59` |
| Rendering | Every sound is synthesised to a buffer in the background after boot (6 ms slices every 12 ms, guns first); a short sound asked for early is rendered on the spot | `src/audio.js:94-109`, `872-875`, `src/audio/library.js:25-44` |
| Unlock | The audio context is created by the first click, key or touch. Before that one-shots are dropped and loops wait | `src/audio.js:627-663` |

Sample attenuation values (gain at distance, from the formula above):

| ref m · roll | 5 m | 10 m | 20 m | 40 m | 80 m | 160 m | −6 dB at | −20 dB at | Used by |
|---|---|---|---|---|---|---|---|---|---|
| 1.4 · 1.6 | 0.196 | 0.092 | 0.045 | 0.022 | 0.011 | 0.005 | 2.3 m | 9.3 m | `neon_buzz` |
| 1.6 · 1.4 | 0.252 | 0.120 | 0.058 | 0.029 | 0.014 | 0.007 | 2.7 m | 11.9 m | `brass_*` |
| 2.2 · 1.25 | 0.386 | 0.184 | 0.090 | 0.044 | 0.022 | 0.011 | 4.0 m | 18.0 m | `boombox` |
| 2.5 · 1.3 | 0.435 | 0.204 | 0.099 | 0.049 | 0.024 | 0.012 | 4.4 m | 19.8 m | `steam` |
| 2.5 · 0.6 | 0.625 | 0.357 | 0.192 | 0.100 | 0.051 | 0.026 | 6.6 m | 40.0 m | `whizz` |
| 3 · 1.2 | 0.556 | 0.263 | 0.128 | 0.063 | 0.031 | 0.016 | 5.5 m | 25.5 m | `hiss`, enemy footsteps |
| 5 · 1 | 1 | 0.500 | 0.250 | 0.125 | 0.063 | 0.031 | 10 m | 50 m | Impacts (all but flesh, drone), `pipe_swing`, `body_fall` |
| 6 · 1 | 1 | 0.600 | 0.300 | 0.150 | 0.075 | 0.037 | 12 m | 60 m | `ricochet`, `rotor`, `goon_ready` |
| 7 · 1 | 1 | 0.700 | 0.350 | 0.175 | 0.087 | 0.044 | 14 m | 70 m | `imp_flesh`, `imp_drone` |
| 7 · 0.9 | 1 | 0.722 | 0.374 | 0.191 | 0.096 | 0.048 | 14.7 m | 77 m | `goon_rush`, `grunt_hit` |
| 8 · 0.9 | 1 | 0.816 | 0.426 | 0.217 | 0.110 | 0.055 | 16.8 m | 88 m | `buzzard_charge`, `grunt_death` |
| 9 · 0.9 | 1 | 0.909 | 0.476 | 0.244 | 0.123 | 0.062 | 19.0 m | 99 m | `buzzard_death` |
| 10 · 1 | 1 | 1 | 0.500 | 0.250 | 0.125 | 0.063 | 20 m | 100 m | `pigeons` |
| 10 · 0.8 | 1 | 1 | 0.556 | 0.294 | 0.152 | 0.077 | 22.4 m | 122 m | `bolt_shot`, `alert_goon`, `alert_buzzard` |
| 11 · 0.8 | 1 | 1 | 0.604 | 0.322 | 0.166 | 0.084 | 24.7 m | 135 m | `smg_shot` |
| 12 · 0.8 | 1 | 1 | 0.652 | 0.349 | 0.181 | 0.092 | 26.9 m | 147 m | `explosion_small` |
| 12 · 0.75 | 1 | 1 | 0.667 | 0.364 | 0.190 | 0.098 | 27.9 m | 156 m | `train_clack` |
| 14 · 0.7 | 1 | 1 | 0.769 | 0.435 | 0.233 | 0.120 | 33.9 m | 194 m | `train_rumble`, `train_squeal` |
| 18 · 0.7 | 1 | 1 | 0.928 | 0.539 | 0.293 | 0.153 | 43.6 m | 249 m | `explosion_big` |
| 30 · 1 | 1 | 1 | 1 | 0.750 | 0.375 | 0.188 | 60 m | 300 m | Far one-shots (siren, dog, horn, bus, kids, jackhammer, chime) |

Air absorption cut-off by distance: 5 m 18.0 kHz, 10 m 16.2 kHz, 25 m 11.9 kHz, 50 m 7.1 kHz, 75 m 4.2 kHz,
100 m 2.5 kHz, 121 m and beyond 1.6 kHz.

### 2.12 The sound list

102 names, 188 variants **(measured:** 37.25 MB as 32-bit float, rendered in about 2 s in Node 22**)**. Columns: **Var × s** = variants × length in seconds (measured); **kHz** = the rate the sound is
synthesised at; **Peak** = the level it is normalised to (after that a 1.5 ms fade-in and a fade-out of up to 20 ms
are applied to one-shots, so a sound that starts on its transient peaks a little lower); **P · M · G** = priority,
most voices of this name at once, shortest gap between two starts in seconds ("–" = default priority 5, no limit,
no gap); **Jit** = pitch jitter ± (blank = 3.5 %); **Ref · roll** for 3D sounds. Variants rotate in order with a
30 % chance of skipping one when there are more than two (`src/audio.js:298-303`). The level a sound reaches the mix
at is `peak × definition volume (1 unless noted) × event volume × (0.92…1) × bus gain`.

**Guns and hands** — `src/audio/sfx-weapons.js:217-238`. All 2D except the brass.

| Name | What it is | Var × s | kHz | Bus | Peak | P · M · G | Jit | Ref · roll | Trigger and play rule |
|---|---|---|---|---|---|---|---|---|---|
| `chopper_shot` | Carbine shot without tail: a bright crack (noise above 1.7 kHz, τ 7 ms), a mid bark (560–760 Hz), a chest thump sweeping 165–185 → 52 Hz, two bolt-carrier clacks at 27 and 66 ms, saturated | 4 × 0.36 | 44.1 | gun | 0.97 | 10 · 5 · – | 1.2 % | — | Every CHOPPER round, volume 1 |
| `nine_shot` | Pistol shot: crack above 2.6 kHz, bark 1050–1400 Hz, thump 280–320 → 100 Hz, slide clacks at 20 and 50 ms | 4 × 0.26 | 44.1 | gun | 0.93 | 10 · 4 · – | 1.2 % | — | Every NINE round, volume 0.95 × 0.95 = 0.90 (the definition and the event both scale it) |
| `chopper_tail_out` | The shot coming back off the block: a darkening wash (4.6 kHz → 420 Hz) with up to six slap echoes at about 75, 160, 250, 390, 580, 830 ms, each 0.66× the last, 0.9 s reverb | 2 × 1.70 | 44.1 | tail | 0.66 | 6 · 3 · – | | — | With every CHOPPER round, volume cos(i · 90°) · k (3.20) |
| `chopper_tail_in` | The same shot inside the garage: a dense short wash (6.5 → 1.3 kHz), the room's steel ringing (236, 412, 655, 1180 Hz), a 9.3 ms flutter echo | 2 × 0.95 | 44.1 | tail | 0.72 | 6 · 3 · – | | — | With every CHOPPER round, volume sin(i · 90°) · k |
| `nine_tail_out` | Street tail of the pistol (brighter, shorter) | 1 × 1.30 | 44.1 | tail | 0.55 | 6 · 3 · – | | — | As above for the NINE |
| `nine_tail_in` | Shop tail of the pistol | 1 × 0.80 | 44.1 | tail | 0.62 | 6 · 3 · – | | — | As above for the NINE |
| `dry_fire` | Two steel clacks (2.7 kHz, then 1.9 kHz 30–36 ms later) | 2 × 0.12 | 44.1 | near | 0.50 | 7 · 2 · – | | — | Trigger pulled on an empty gun; pitch 1.0 (NINE 1.2) |
| `rifle_magout` | Release click, a scrape, the magazine clearing the well, cloth | 1 × 0.30 | 44.1 | near | 0.55 | 6 · – · – | | — | Reload phase `magout`, CHOPPER |
| `rifle_magin` | Scrape in, the seat thunk, the catch click | 1 × 0.34 | 44.1 | near | 0.62 | 6 · – · – | | — | Reload phase `magin`, CHOPPER |
| `rifle_bolt` | Charging handle back, spring, released 0.13 s later | 1 × 0.36 | 44.1 | near | 0.70 | 6 · – · – | | — | Reload phase `bolt`, CHOPPER (empty reloads) |
| `pistol_magout` | As the rifle's, higher and smaller | 1 × 0.30 | 44.1 | near | 0.50 | 6 · – · – | | — | Reload phase `magout`, NINE |
| `pistol_magin` | — | 1 × 0.34 | 44.1 | near | 0.56 | 6 · – · – | | — | Reload phase `magin`, NINE |
| `pistol_slide` | Slide racked, released 0.09 s later | 1 × 0.36 | 44.1 | near | 0.66 | 6 · – · – | | — | Reload phase `bolt`, NINE |
| `cloth` | Sling and sleeve rustle with a faint hardware tick | 2 × 0.32 | 44.1 | near | 0.30 | 3 · – · – | 8 % | — | Reload start: volume 0.9, pitch 1.0 (NINE 1.12). Reload done: volume 0.5, pitch 1.08 (NINE 1.2) |
| `holster` | Rustle, then the gun dropping on its sling | 1 × 0.40 | 44.1 | near | 0.40 | 4 · – · – | | — | Weapon switch, holster phase: volume 1, pitch 1 (from the NINE: 0.75, 1.18) |
| `draw` | Rustle, then the grip settling in the hand at 0.27 s | 1 × 0.40 | 44.1 | near | 0.42 | 4 · – · – | | — | Weapon switch, draw phase: volume 1, pitch 1 (to the NINE: 0.8, 1.15) |
| `whoosh` | The melee swing: a band of noise sweeping 0.5 → 3.1 → 0.5 kHz | 2 × 0.30 | 44.1 | near | 0.50 | 6 · – · – | 6 % | — | A melee strike starts: volume 0.9, pitch 1.1 |
| `melee_thud` | A gun butt on a body: a dull 150 → 55 Hz thump with a crack of hard plastic | 2 × 0.30 | 44.1 | near | 0.62 | 8 · – · – | 5 % | — | The melee blow lands on an enemy |
| `brass_asphalt` | A spent case on the ground: up to four bright bounces (4.1–5.2 kHz) that speed up and die | 4 × 0.42 | 44.1 | world, 3D | 0.34 | 2 · 3 · 0.04 | 6 % | 1.6 · 1.4 | A shell bounces on anything but metal: volume 0.9 (0.5 on dirt, wood, rubber, cloth); pitch × 1.22 for the NINE, × 0.9 on wood |
| `brass_metal` | The same on metal: longer ring, the surface answering at 700–900 Hz | 3 × 0.55 | 44.1 | world, 3D | 0.36 | 2 · 3 · 0.04 | 6 % | 1.6 · 1.4 | A shell bounces on metal or a car body |

**The player** — `src/audio/sfx-player.js:153-171`.

| Name | What it is | Var × s | kHz | Bus | Peak | P · M · G | Jit | Ref · roll | Trigger and play rule |
|---|---|---|---|---|---|---|---|---|---|
| `step_asphalt`, `step_concrete`, `step_metal`, `step_wood`, `step_dirt` | One footfall, walking: heel, then the sole rolling down; grit on asphalt and dirt, a ringing tread plate on metal, a hollow knock on wood | 4 × 0.24 (metal 0.34) | 44.1 | near | 0.42, 0.44, 0.50, 0.48, 0.38 | 3 · 3 · – | 6 % | — | Player footstep while not sprinting: volume 0.55, pitch 1 |
| `step_<surface>_run` (same five) | The same, harder, shorter, more scuff | 3 × 0.24 (metal 0.34) | 44.1 | near (world, 3D for enemies) | walk peak × 1.3 | 3 · 3 · – | 6 % | 3 · 1.2 (enemies) | Player sprint step: volume 0.8, pitch 1.04. Landing: volume v × 0.6, pitch 0.92. Goon step within 45 m: volume 0.75, pitch 0.88, priority 2 |
| `jump` | Clothes and gear lifting, a push-off scuff | 1 × 0.30 | 44.1 | near | 0.40 | 4 · – · – | 5 % | — | Player jumps: volume 0.8 |
| `land` | A 125 → 48 Hz thump, grit, gear settling a moment later | 2 × 0.40 | 44.1 | near | 0.55 | 5 · – · – | 5 % | — | Player lands: volume v = clamp(0.35 + speed / 10 m/s, 0.35, 1) |
| `hurt` | A punch in the chest (110 → 42 Hz), felt more than heard | 3 × 0.42 | 44.1 | dry | 0.60 | 9 · 3 · 0.06 | 5 % | — | Player takes damage: volume clamp(0.5 + damage / 40, 0.5, 1); pitch 0.85 for a blast |
| `ear_ring` | The whine after a hit: 4130 and 4171 Hz beating, fading over 2.4 s | 1 × 2.40 | 22.05 | dry | 0.22 | 5 · 1 · 1.8 | 1 % | — | A hit of 8 damage or more, at most every 1.8 s: volume clamp(damage / 28, 0.3, 1) |
| `heartbeat` | One lub-dub (62 and 78 Hz thumps 0.23 s apart) | loop 0.86 | 22.05 | dry | 0.50 | — | none | — | Loop while health is under 35 % (3.22) |
| `reel_grab` | Hands on the case: a ratchet (12 ticks per loop) over a 110 Hz flywheel hum | loop 0.60 | 44.1 | near | 0.30 | — | none | — | Loop while the reel's progress bar moves (3.22) |
| `reel_secure` | Latch, lid thump, a bright two-note confirm G6 → D7 (1568, 2349 Hz) | 1 × 1.10 | 44.1 | dry | 0.60 | 8 · – · – | | — | A reel is secured |

**The world** — `src/audio/sfx-world.js:197-224`.

| Name | What it is | Var × s | kHz | Bus | Peak | P · M · G | Jit | Ref · roll | Trigger and play rule |
|---|---|---|---|---|---|---|---|---|---|
| `imp_concrete` | Bullet on concrete: a bright snap, a 1.5 kHz crack, chips | 3 × 0.26 | 44.1 | world, 3D | 0.60 | 4 · 4 · 0.022 | 7 % | 5 · 1 | Round hits concrete (pitch 1) or asphalt (pitch 0.82), or an unknown surface |
| `imp_brick` | Duller crack (950 Hz), crumbs | 3 × 0.26 | 44.1 | world, 3D | 0.60 | 4 · 4 · 0.022 | 7 % | 5 · 1 | Round hits brick |
| `imp_metal` | A ping: steel plate ringing on (0.83–6.1 kHz partials) | 3 × 0.50 | 44.1 | world, 3D | 0.60 | 4 · 4 · 0.022 | 7 % | 5 · 1 | Round hits metal |
| `imp_car` | Sheet metal: a hollow thunk with a short wobble | 3 × 0.38 | 44.1 | world, 3D | 0.66 | 4 · 4 · 0.022 | 7 % | 5 · 1 | Round hits a car body |
| `imp_glass` | A tick, then nine falling fragments | 2 × 0.50 | 44.1 | world, 3D | 0.50 | 4 · 4 · 0.022 | 7 % | 5 · 1 | Round hits glass |
| `imp_wood` | Knock and splinters | 2 × 0.26 | 44.1 | world, 3D | 0.58 | 4 · 4 · 0.022 | 7 % | 5 · 1 | Round hits wood (pitch 1) or rubber (pitch 0.7) |
| `imp_dirt` | A soft low thud | 2 × 0.26 | 44.1 | world, 3D | 0.50 | 4 · 4 · 0.022 | 7 % | 5 · 1 | Round hits dirt (pitch 1) or cloth (pitch 1.25) |
| `imp_flesh` | A body under a coat: dull slap, cloth, no ring | 3 × 0.26 | 44.1 | world, 3D | 0.60 | 6 · 4 · 0.022 | 7 % | 7 · 1 | Round hits a Goon |
| `imp_drone` | Carbon and thin alloy: a brittle clank | 2 × 0.26 | 44.1 | world, 3D | 0.60 | 6 · 4 · 0.022 | 7 % | 7 · 1 | Round hits a Buzzard |
| `ricochet` | The round carrying on: a whine falling from about 3 kHz to 0.9 kHz | 3 × 0.60 | 44.1 | world, 3D | 0.42 | 3 · 2 · 0.22 | 10 % | 6 · 1 | By chance after a world impact: metal 24 %, car 12 %, concrete 7 %, brick 5 %, asphalt 5 %; 12 ms late, volume 0.8 |
| `whizz` | An enemy round passing the head: a band of noise falling in pitch, a crack of air | 3 × 0.24 | 44.1 | world, 3D | 0.60 | 7 · 3 · 0.09 | 10 % | 2.5 · 0.6 | Near miss (3.21) |
| `hit_confirm` | Hit-marker tick (1480 Hz) | 1 × 0.10 | 44.1 | dry | 0.42 | 8 · 3 · 0.03 | 3 % | — | The player's shot hits a body |
| `hit_head` | Higher (2350 Hz), shorter, doubled | 1 × 0.12 | 44.1 | dry | 0.46 | 8 · 3 · 0.03 | 2 % | — | The player's shot hits a head |
| `kill_confirm` | A muted knock and a falling fourth G6 → D6 | 1 × 0.34 | 44.1 | dry | 0.50 | 9 · 2 · 0.05 | 1.5 % | — | The player's shot or blow kills |
| `explosion_small` | A blast: crack, pressure wave (130 → 40 Hz), a rolling brown-noise tail, a slap at 190 ms, 12 bits of debris, 1.1 s reverb | 2 × 2.10 | 32 | world, 3D | 0.90 | 9 · 3 · 0.05 | 6 % | 12 · 0.8 | An explosion announced as small: a Buzzard bursting on the ground |
| `explosion_big` | The same, bigger (95 → 28 Hz), 26 bits of debris, 1.6 s reverb | 2 × 3.40 | 32 | world, 3D | 0.92 | 10 · 3 · 0.05 | 5 % | 18 · 0.7 | An explosion announced as big (radius ≥ 5 m): propane tank, welding rack |
| `hiss` | Gas escaping under pressure: a tight bright hiss with a 3.35 kHz whistle | loop 1.50 | 44.1 | world, 3D | 0.40 | — | none | 3 · 1.2 | Loop at a lit explosive, volume 0.25 rising to 1 with the square of the burnt fuse fraction (`src/explosives.js:30`, `258`, `441`) |
| `ui_click` | A soft switch tick (1245 Hz) with a low thump | 1 × 0.10 | 44.1 | dry | 0.34 | 6 · 2 · – | 1 % | — | Any menu or HUD button, picker, toggle, tab; a slider on release |
| `ui_hover` | A lighter tick (2490 Hz) | 1 × 0.06 | 44.1 | dry | 0.16 | 2 · 2 · 0.03 | 1 % | — | The pointer enters a button; a gamepad focus move |
| `ui_tick` | A tiny tick (3.1 kHz) | 2 × 0.03 | 44.1 | dry | 0.10 | 1 · 2 · 0.025 | 4 % | — | **Never played** (defined only) |
| `radio_in` | The earpiece keying up: a squelch chirp 1.25 → 1.9 kHz and a blip, through a small speaker | 1 × 0.22 | 44.1 | dry | 0.30 | 6 · 1 · – | 1 % | — | A radio line starts |
| `radio_out` | Letting go: a chirp 1.7 → 1.1 kHz | 1 × 0.16 | 44.1 | dry | 0.22 | 5 · 1 · – | 1 % | — | `hold` seconds after the line started (clamped 0.6…12 s) |

**The Vultures** — `src/audio/sfx-enemies.js:237-253`. All on the world bus, 3D; jitter 5 % unless given.

| Name | What it is | Var × s | kHz | Peak | P · M · G | Jit | Ref · roll | Trigger and play rule |
|---|---|---|---|---|---|---|---|---|
| `rotor` | Four motors a few hertz apart (187, 194, 203, 209 Hz and harmonics) under blade wash | loop 1.00 | 22.05 | 0.40 | — | none | 6 · 1 | One loop per living Buzzard (3.22) |
| `buzzard_charge` | The gun spooling up: a whine rising 420 → 2350 Hz over 0.5 s, ticking faster, ending on a blip | 1 × 0.55 | 44.1 | 0.55 | 8 · 3 · 0.05 | 2 % | 8 · 0.9 | Buzzard telegraph: pitch clamp(0.5 / telegraph, 0.6, 2) = 0.91, 1.09, 1.32 for 0.55, 0.46, 0.38 s |
| `bolt_shot` | A bolt leaving: an electric crack with a falling tone and a small thump | 3 × 0.40 | 44.1 | 0.66 | 8 · 4 · 0.03 | 5 % | 10 · 0.8 | Each Buzzard bolt, at its gun |
| `buzzard_death` | Motors dying over 1.6 s: pitch and level falling, sputtering, sparks | 1 × 1.60 | 44.1 | 0.70 | 8 · 2 · – | 5 % | 9 · 0.9 | A Buzzard is killed |
| `smg_shot` | A Goon's SMG from across the street, lighter than the CHOPPER, with one slap and a short wash baked in | 4 × 0.55 | 44.1 | 0.74 | 8 · 5 · 0.035 | 4 % | 11 · 0.8 | Each Goon round, at his muzzle |
| `goon_ready` | The gun coming up: sling rustle, then two bolt clacks at 0.30 and 0.375 s | 1 × 0.50 | 44.1 | 0.42 | 6 · 2 · 0.08 | 3 % | 6 · 1 | Goon telegraph (0.5 s): pitch 1 |
| `goon_rush` | The rush: a growl rising from the chest (88 → 150 Hz) while a pipe drags on the asphalt | 2 × 0.70 | 44.1 | 0.70 | 8 · 2 · 0.10 | 3 % | 7 · 0.9 | Goon melee wind-up: volume 0.9, pitch 1 |
| `pipe_swing` | The pipe coming round: a whoosh with a faint ring | 1 × 0.32 | 44.1 | 0.55 | 7 · 2 · – | 5 % | 5 · 1 | Goon melee strike |
| `grunt_hit` | A wordless grunt behind a mask (135–165 Hz falling) | 4 × 0.17–0.20 | 22.05 | 0.50 | 5 · 2 · 0.12 | 7 % | 7 · 0.9 | A living Goon takes damage (also the hit that kills him) |
| `grunt_death` | A longer falling groan, the air going out | 3 × 0.44–0.55 | 22.05 | 0.60 | 7 · 2 · 0.10 | 7 % | 8 · 0.9 | A Goon is killed |
| `alert_goon` | One sharp rising shout with no word in it (0.24 s) and its echo | 3 × 0.79 | 22.05 | 0.60 | 7 · 2 · 0.12 | 6 % | 10 · 0.8 | A Goon goes from unaware to engaging |
| `alert_buzzard` | Two quick rising chirps (1.5 and 2 kHz) | 1 × 0.36 | 44.1 | 0.50 | 7 · 2 · 0.12 | 4 % | 10 · 0.8 | A Buzzard acquires the player |
| `body_fall` | A body going down on the pavement: thump, the coat, an arm a moment later | 2 × 0.50 | 22.05 | 0.50 | 4 · 2 · – | 8 % | 5 · 1 | 0.42 s after a Goon is killed |

**The block** — `src/audio/sfx-ambience.js:379-399`. All synthesised at 22.05 kHz.

| Name | What it is | Var × s | Bus | Peak | P · M · G | Jit | Ref · roll | Trigger and play rule |
|---|---|---|---|---|---|---|---|---|
| `bed_day` | **Stereo** street bed: a low city wash (below 520 Hz), an air band, ten distant car passes per side, a trace of mains hum | loop 12.0 | amb, 2D | 0.50 | — | none | — | Always running; volume = day mix (3.23) |
| `bed_night` | **Stereo**; quieter, darker (below 380 Hz), four cars, more hum | loop 12.0 | amb, 2D | 0.36 | — | none | — | Volume = 1 − day mix |
| `wind_el` | Wind worrying the El's steel: a breathy band with two girder whistles (610, 935 Hz) that come and go | loop 10.0 | amb, 2D | 0.32 | — | none | — | Always running; volume and pitch follow gusts and the distance to the El (3.23) |
| `neon_buzz` | A neon transformer: 120 Hz and odd harmonics, the gas crackling | loop 1.0 | world, 3D | 0.18 | — | none | 1.4 · 1.6 | At the three nearest neon lamps within 15 m; volume 0.5 by day, 1 by night |
| `steam` | Steam out of a manhole: a soft unsteady roar | loop 3.0 | world, 3D | 0.30 | — | none | 2.5 · 1.3 | At the three nearest steam vents within 24 m |
| `train_rumble` | The El's roar: steel and concrete under load | loop 4.0 | world, 3D | 0.60 | — | none | 14 · 0.7 | While a train passes (3.23) |
| `train_clack` | Wheels on the rail joints: four axle hits per car length | loop 0.988 | world, 3D | 0.62 | — | none | 12 · 0.75 | While a train passes; pitch = speed / 16.5 m/s |
| `train_squeal` | Flanges squealing in the curve (about 3 kHz) | 1 × 3.2 | world, 3D | 0.22 | 5 · 2 · – | 4 % | 14 · 0.7 | Once in 70 % of passes while the train is overhead, volume 0.8 |
| `siren_far` | A far siren through blocks of buildings: a wail (variant 1) or a yelp (variant 2) | 2 × 7.5 | amb, 3D | 0.40 | 1 · 2 · – | 4 % | 30 · 1 | Far one-shot schedule (2.14) |
| `dog_far` | A dog a few blocks over: two to four barks | 2 × 3.0 | amb, 3D | 0.42 | 1 · 2 · – | 4 % | 30 · 1 | Schedule |
| `horn_far` | A car horn two streets away: one long blast or two blips | 3 × 1.6 | amb, 3D | 0.36 | 1 · 2 · – | 4 % | 30 · 1 | Schedule |
| `bus_pull` | A city bus leaving its stop: air brake, then the diesel winding up and away | 1 × 6.5 | amb, 3D | 0.50 | 1 · 2 · – | 4 % | 30 · 1 | Schedule (day) |
| `kids_far` | Kids on a court somewhere: wordless calls, a rubber ball bouncing | 2 × 4.5 | amb, 3D | 0.36 | 1 · 2 · – | 4 % | 30 · 1 | Schedule (day) |
| `pigeons` | Coos and a clatter of wings | 2 × 3.2 | amb, 3D | 0.32 | 1 · 2 · – | 4 % | 10 · 1 | Schedule (day), placed on a ledge nearby |
| `jackhammer` | A jackhammer a block away: two runs at 18–23 hits a second | 1 × 5.0 | amb, 3D | 0.34 | 1 · 2 · – | 4 % | 30 · 1 | Schedule (day) |
| `chime_far` | An original 15-note music-box chime in C major through a tinny, warbling speaker (not any real jingle) | 1 × 5.24 | amb, 3D | 0.34 | 1 · 2 · – | 4 % | 30 · 1 | Schedule (day) |

**The score** — `src/audio/music.js:279-287`, `417-430`. All mono, all 2D except the boombox.

| Name | What it is | Length s | kHz | Bus | Peak | Pan | Trigger and play rule |
|---|---|---|---|---|---|---|---|
| `stem_drums` | Dusty kick and snare with ghost notes, a three-hit turnaround in bar 8; low-passed at 7.4 kHz, saturated, a short room | loop 20.870 | 22.05 | music | 0.85 | 0 | Looping stem, layer gain by intensity (2.13) |
| `stem_hats` | Closed hats on the eighths (accented on the beat), an open hat at the end of every second bar, pickups | loop 20.870 | 22.05 | music | 0.42 | +0.18 | Stem |
| `stem_bass` | Sub bass (a sine with two soft harmonics) on the chord roots, walking into each change | loop 20.870 | 11.025 | music | 0.80 | 0 | Stem |
| `stem_keys` | Rhodes-like electric piano chords and fills, 4.6 Hz tremolo, a dark close room | loop 20.870 | 22.05 | music | 0.50 | −0.22 | Stem |
| `stem_strings` | String-section stabs (three detuned saws per note under a closing filter), long reverb | loop 20.870 | 22.05 | music | 0.60 | +0.25 | Stem (top layer) |
| `stem_bell` | The bell hook, with a dotted-eighth echo and a room | loop 20.870 | 22.05 | music | 0.50 | +0.12 | Stem (top layer) |
| `stem_crackle` | Vinyl hiss and ticks (about 26 a second) | loop 20.870 | 11.025 | music | 0.30 | 0 | Stem |
| `m_riser` | Two bars of noise and tone climbing to the downbeat it lands on; the file ends exactly on that downbeat (only a 4 ms fade) | 5.217 | 22.05 | music | 0.50 | — | Entering the top tier (3.24), gain 0.85 |
| `m_impact` | The downbeat: a sub drop 85 → 30 Hz, a crash, a snare, 2 s reverb | 3.0 | 22.05 | music | 0.70 | — | On the bar line the riser lands on, gain 0.8 |
| `sting_reel` | A kick, an F-minor string stab and a rising four-note bell figure (F5 A♭5 C6 F6) | 3.4 | 22.05 | music | 0.62 | — | A reel secured (not the last); a holdout wave cleared |
| `sting_all` | Three kick-and-stab hits a beat apart climbing D♭ → E♭ → F minor, a five-note bell run, a sub drop | 5.4 | 22.05 | music | 0.66 | — | The last reel secured |
| `sting_dead` | A low minor chord whose pitch sags 45 % like a tape machine losing power, a sub thump | 4.6 | 22.05 | music | 0.60 | — | The player dies |
| `sting_complete` | D♭ · E♭ · F **major**, two beats apart (Rhodes, strings, kick), a closing bell arpeggio: the minor key lifts for once | 7.0 | 22.05 | music | 0.66 | — | The truck is reached |
| `boombox` | The beat and the hook (drums 0.9, hats 0.5, bass 0.7, bell 0.8) through a small overdriven speaker: high-pass 260 Hz, +6 dB at 1.4 kHz, low-pass 3.6 kHz, saturated | loop 20.870 | 11.025 | world, **3D** | 0.50 | — | One loop at every reel still out there, in phase with the score; ref 2.2 m, roll 1.25, volume 0.95 |

### 2.13 Music facts

| Fact | Value | Source |
|---|---|---|
| Tempo, metre | 92 BPM, 4/4. Beat 0.652174 s, bar 2.608696 s, sixteenth 0.163043 s | `src/audio/music.js:11-14` |
| Form | Eight bars, looped: 20.869565 s (460 174 samples at 22.05 kHz, 230 087 at 11.025 kHz) | `src/audio/music.js:15-19` |
| Swing | Odd sixteenths lag 17 % of a sixteenth (27.7 ms); the "and" of each beat lags 4 % (6.5 ms) | `src/audio/music.js:20-25` |
| Key | F minor | `src/audio/music.js:1` |
| Chords (two bars each) | Fm9 · D♭maj9 · B♭m9 · C7(♭9) | `src/audio/music.js:27-38` |
| Bass roots (MIDI) | 41, 41, 37, 37, 34, 34, 36, 36 (F2, D♭2, B♭1, C2) | `src/audio/music.js:28` |
| Keys voicings (MIDI) | Fm9: 53 56 60 63 67. D♭maj9: 49 53 56 60 63. B♭m9: 49 53 56 58 60. C7(♭9): 52 55 58 60 61 | `src/audio/music.js:29-38` |
| Bell hook | 31 notes between MIDI 72 and 85, written for this game; list of [bar, sixteenth, note, length] | `src/audio/music.js:41-50` |
| Drum patterns (sixteenth index, velocity) | Kick A (bars 1–3, 5–7): 0 (1.0), 7 (0.55), 10 (0.92). Kick B (bars 4, 8): 0, 3, 10, 13. Snare on 4 and 12. Ghost snares A: 6, 9, 15; B: 6, 11, 14, 15. Bar 8 adds snares on 13, 14, 15 | `src/audio/music.js:52-55`, `132-147` |
| String stabs | [bar, sixteenth, length in sixteenths]: [0, 0, 10] [2, 6, 3] [2, 10, 3] [4, 0, 10] [6, 0, 4] [6, 6, 3] [7, 10, 2] [7, 14, 2] (bars counted from 0) | `src/audio/music.js:223` |
| Stem routing | Drums and hats pass a shared low-pass (Q 0.8); every stem has its own gain and pan; all stems sum into a "stem bus" that stings and risers duck; stings, riser and impact bypass that bus | `src/audio/conductor.js:61-87` |

Layer gains by intensity `I` (`src/audio/conductor.js:23-43`; formula in 3.24). The game only ever asks for 0.15, 0.6 or 1.0;
the values between are passed through while the level eases.

| I | drums | hats | bass | keys | strings | bell | crackle | drum low-pass |
|---|---|---|---|---|---|---|---|---|
| ≤ 0.25 (**calm 0.15**) | 0.78 | 0.10 | 0.50 | 0 | 0 | 0 | 0.60 | 700 Hz |
| 0.30 | 0.80 | 0.17 | 0.54 | 0 | 0 | 0 | 0.58 | 891 Hz |
| 0.35 | 0.84 | 0.33 | 0.63 | 0 | 0 | 0 | 0.52 | 1.6 kHz |
| 0.40 | 0.89 | 0.55 | 0.75 | 0.10 | 0 | 0 | 0.45 | 3.6 kHz |
| 0.45 | 0.94 | 0.77 | 0.87 | 0.35 | 0 | 0 | 0.38 | 7.8 kHz |
| 0.50 | 0.98 | 0.93 | 0.96 | 0.65 | 0 | 0 | 0.32 | 14.3 kHz |
| 0.55 | 1 | 1 | 1 | 0.90 | 0 | 0 | 0.30 | 18.2 kHz |
| **alert 0.60** … 0.75 | 1 | 1 | 1 | 1 | 0 | 0 | 0.30 | 18.2 kHz |
| 0.80 | 1 | 1 | 1 | 0.98 | 0.16 | 0.14 | 0.30 | 18.2 kHz |
| 0.85 | 1 | 1 | 1 | 0.95 | 0.50 | 0.45 | 0.30 | 18.2 kHz |
| 0.90 | 1 | 1 | 1 | 0.92 | 0.84 | 0.76 | 0.30 | 18.2 kHz |
| ≥ 0.95 (**hot 1.0**) | 1 | 1 | 1 | 0.90 | 1 | 0.90 | 0.30 | 18.2 kHz |
| Title screen | 0.78 | 0.10 | 0.50 | 0.55 | 0 | 0 | 0.60 | 700 Hz |
| Dead | 0 | 0 | 0 | 0.16 | 0 | 0 | 0.55 | 400 Hz |

Reference levels **(measured:** eight bars rendered through the conductor in an offline audio context, at the music
bus output**)**: peak 0.41 / RMS 0.097 at 0.15; peak 0.72 / RMS 0.160 at 0.6; peak 0.78 / RMS 0.163 at 1.0.

Intensity the game asks for (`src/config/flow.js:208-217`, `src/game/music.js:16-23`):

| Level | Value | Condition, checked every frame of a run |
|---|---|---|
| Hot | 1.0 | Every reel is secured (the run for the truck), **or** enemies are still queued to arrive, **or** a wave was queued less than 30 s ago and anything is alive. The 30 s window ends early once the wave has been out 6 s and nobody is left or on the way |
| Alert | 0.6 | An enemy became alerted in the last 10 s, **or** the player was hit in the last 8 s, **or** a living enemy is closer than 26 m |
| Calm | 0.15 | Otherwise; also the title, the start of every run, and when the death or debrief card comes up |

### 2.14 Ambience schedule

Far one-shots (`src/audio/ambience.js:9-25`, `61-92`). Each has its own timer: first after `first × U(0.7, 1.3)` s,
then every `U(min, max)` s. Volume U(0.75, 1). The siren plays at pitch 0.92 three times in ten. Timers stop while
the game is paused or the player is dead; switching between day and night restarts them.

| By day | min–max s | first s | Placed | By night | min–max s | first s | Placed |
|---|---|---|---|---|---|---|---|
| `horn_far` | 14–34 | 6 | far | `siren_far` | 55–115 | 16 | far |
| `bus_pull` | 32–70 | 18 | street | `dog_far` | 24–55 | 9 | far |
| `kids_far` | 24–52 | 10 | far | `horn_far` | 40–85 | 25 | far |
| `pigeons` | 15–36 | 4 | roof | | | | |
| `jackhammer` | 48–100 | 28 | far | | | | |
| `chime_far` | 90–170 | 40 | far | | | | |
| `siren_far` | 85–160 | 55 | far | | | | |
| `dog_far` | 100–180 | 70 | far | | | | |

Placement relative to the listener (`src/audio/ambience.js:67-80`): **far** = 60–150 m away in a random direction, 2–16 m up;
**street** = 45–105 m east or west along the avenue, within ±12 m across it, 1.5 m up; **roof** = 9–27 m away in a
random direction, 7–16 m up.

### 2.15 Event → sound table

What the audio does on each game event (`src/audio/react.js`, events defined in `docs/CONTRACT.md:119-164`). "Meter"
is the conductor's own combat meter (3.24): `+x` adds, `≥ x` raises it to at least x.

| Event | Sound and rule | Mixer side effects | Lines |
|---|---|---|---|
| `weapon:fire` | `<weapon>_shot` + `<weapon>_tail_out` and / or `<weapon>_tail_in` (3.20) | Duck ambience and music to 0.45 (NINE 0.55) for 85 ms, release τ 0.1 s. Meter +0.012 | 35-61 |
| `weapon:dry` | `dry_fire`, pitch 1 (NINE 1.2) | — | 63 |
| `weapon:reload` | By phase: `start` → `cloth`; `magout`, `magin`, `bolt` → the rifle or pistol sound; `done` → `cloth` (quieter, higher); `cancel` → nothing | — | 65-87 |
| `weapon:switch` | `holster` then `draw` (one event per phase) | — | 89-93 |
| `weapon:swing` | `whoosh` | — | 95 |
| `weapon:melee` | `melee_thud` if the blow hit | — | 96-98 |
| `shell:bounce` | `brass_metal` or `brass_asphalt` at the bounce point | — | 100-107 |
| `player:step` | `step_<surface>` (walk) or `step_<surface>_run` (sprint). Surface map: asphalt, concrete, metal, wood, dirt as named; brick and glass → concrete; rubber, cloth, flesh → dirt; car, drone → metal; anything else → concrete | — | 7, 111-116 |
| `player:jump` | `jump` | — | 117 |
| `player:land` | `land` + one run step of the surface | — | 118-122 |
| `player:hit` | `hurt`; `ear_ring` for 8 damage or more | Muffle to clamp(damage / 40, 0.2, 0.7), then it recovers. Meter +0.15 | 124-135 |
| `player:dead` | — (the game also plays the `dead` sting) | Muffle to 1, settling at 0.85 until the next run | 137 |
| `player:hitEnemy` | `kill_confirm` if it killed, else `hit_head` or `hit_confirm` | — | 139-143 |
| `impact` | `imp_<surface>` at the point (table in 2.12); volume 0.9 for the player's rounds on the world, 0.8 for enemy rounds, 1.0 on a body. Then the ricochet roll (world impacts only) | — | 9-14, 147-159 |
| `enemy:fire` | `bolt_shot` (Buzzard) or `smg_shot` (Goon) at the muzzle; then the near-miss test (3.21) | Duck ambience only to 0.85 for 60 ms, release τ 0.12 s. Meter +0.04 | 176-187 |
| `enemy:telegraph` | `buzzard_charge` or `goon_ready`, pitch clamp(0.5 / duration, 0.6, 2) | Meter ≥ 0.6 | 189-194 |
| `enemy:melee` | Wind-up → `goon_rush`; strike → `pipe_swing` | — | 196-200 |
| `enemy:alert` | `alert_buzzard` or `alert_goon` | Meter ≥ 0.6 | 202-209 |
| `enemy:hit` | `grunt_hit` (Goons only) | — | 211-215 |
| `enemy:killed` | Buzzard: `buzzard_death`, its rotor loop stops. Goon: `grunt_death`, then `body_fall` 0.42 s later | — | 217-226 |
| `enemy:step` | The run step of the surface, in 3D at the Goon | — | 228-231 |
| `enemy:spawn` | A Buzzard gets its `rotor` loop | — | 233-236 |
| `explosion` | `explosion_big` or `explosion_small` at the blast | Within 20 m: muffle to 0.8 (small 0.56) × clamp(1 − (d − 5 m) / 15 m, 0, 1). Duck ambience and music to 0.4 for 0.4 s, release τ 0.45 s (small: 0.6, 0.15 s, 0.2 s). Music dips to 0.3 (small 0.45) and recovers. Meter ≥ 0.6 | 238-248 |
| `objective:progress` | The `reel_grab` loop, pitch 0.85 + 0.4 × progress | — | 252-257 |
| `objective:done` | `reel_secure` and that reel's boombox stops (not for a holdout wave) | — | 259-266 |
| `radio:line` | `radio_in` now, `radio_out` after the line's hold time | — | 268-272 |
| `ui:click`, `ui:hover` | `ui_click`, `ui_hover` | — | 274-275 |
| `train:pass` | Train loops and squeal (3.23) | Train duck | 276 |
| `game:state` | — | Title: muffle released, music mode `title`, ambience × 0.6. Intro / playing: muffle released (not when coming from pause), music mode `play`, ambience × 1. Dead: ambience × 0.7. Complete: ambience × 0.8 | 278-294 |
| `game:reset` | Reel boomboxes restart, rotor loops are dropped | Muffle released | 296-301 |

Called directly by the game (`src/game.js`): `audio.sting('reel')` when a reel that is not the last is secured and
when a holdout wave is cleared (`617`, `705`); `sting('all')` on the last reel (`617`); `sting('complete')` at the
truck (`667`); `sting('dead')` on death (`889`); `setMusicIntensity` every frame of a run (`782`), and to calm on the
title (`796`), at the start of a run (`249`), back on the title (`315`) and when a card comes up (`753`);
`setPaused(state === 'paused')` on every state change (`149`); `unlock()` from every menu button (`src/menus.js:55`,
`93`).

### 2.16 Public interface

What the rest of the game calls (`docs/CONTRACT.md:571-596`, `675-693`). Everything else these modules do, they do
by listening to events. The stubs (`src/stubs/hud.js`, `menus.js`, `audio.js`) implement exactly this surface.

| Module | Call | Meaning |
|---|---|---|
| HUD | `show(on)`, `reset()` | Fade the HUD in or out; clear objective, reels, tally, markers, feed, radio, banner, message, arcs, hit marker, prompt and the health ghost for a new run |
| HUD | `setObjective(text)` | New objective line, typed out (3.2) |
| HUD | `setReels(done, total)`, `setTally(text)` | Story: reel bullets and count. Hold the Block: the tally line |
| HUD | `setMarkers(list)` | World markers, minimap bullets and which badge bullets are filled; at most five (3.13) |
| HUD | `prompt(spec or null)` | Interaction ring with `{text, glyph, code, progress}` (3.10) |
| HUD | `warn(text, secs)`, `message(text, secs)` | Banner; centre message (3.12) |
| HUD | `radio(speaker, text, secs)`, `clearRadio()` | Queue a subtitle line; drop all lines (3.14) |
| Menus | `show(screen, data)`, `screen` | `none`, `title`, `paused`, `dead`, `complete`; the card data of 3.16 |
| Menus | `locationCard(on, data)` | Intro card with `{place, tagline}` |
| Menus | `openPanel(tab)`, `panelOpen` | Settings / controls drawer over the current screen. `panelOpen` stays true until the end of the frame the drawer closed in, so the key that closed it does not also resume the game (`src/menus.js:399-403`) |
| Audio | `unlock()` | Start the audio on a user gesture (a browser rule; not needed in Unreal) |
| Audio | `play(name, options)` → handle or nothing | One-shot (3.18); the handle can stop, set volume, pitch and position |
| Audio | `loop(name, options)` → handle | Loop with `setPos`, `setVolume`, `setPitch`, `stop` (3.18) |
| Audio | `sting(name)` | `reel`, `all`, `dead`, `complete` (3.24) |
| Audio | `setMusicIntensity(0…1)` | The game's music level (2.13) |
| Audio | `setPaused(on)`, `setVolume(0…1)` | Pause mix; master volume |
| Audio | `setInterior(0…1)` | Overrides the interior factor for 0.25 s per call. Nothing calls it: the mixer reads the level's interior box itself (`src/audio.js:732-735`, `556-560`) |

---------------------------------------------------------------------------------------------------

## 3. Behaviour

### 3.1 What is on screen in each game state, and the order within a frame

The flow owns the state machine `title → intro → playing ⇄ paused`, `playing → dead | complete`
(`src/game.js:139-154`). The HUD is shown in `intro` and `playing` only.

| State | HUD | Radio strip | Menu layer | Sound |
|---|---|---|---|---|
| `title` | Hidden | Hidden | Title screen, letterbox bars, veil; the drawer on request | Score in `title` mode at intensity 0.15; ambience × 0.6 |
| `intro` (2.4 s on a first start, 1.1 s on a retry) | Fades in (0.35 s) | Visible | None. On a first start the location card from 0.25 s until the intro ends | Score in `play` mode |
| `playing` | Visible | Visible | None | — |
| `paused` | Hidden | Hidden; its clock and the kill feed's stand still | Pause card; the drawer on request | Effects and ambience silent, music at 45 % behind a 1.3 kHz low-pass; UI sounds still play |
| `dead` | Hidden at once | Cleared | Nothing for 1.5 s, then the death card | `dead` sting; effects muffled; stems drop to crackle and a trace of keys; ambience × 0.7 |
| `complete` | Hidden at once | Visible: "Masters are in the vault…" plays over the debrief | Nothing for 3.3 s, then the debrief card | `complete` sting; stems ducked to 0.12 for 7 s; ambience × 0.8 |

Sources: `src/game.js:143-153`, `809-826`; `src/hud.js:612`, `785-790`; `src/config/flow.js:9-20`.

Order within a frame (`docs/CONTRACT.md:81-91`):

1. Input, then the flow (it may set the objective, raise a banner, a message, a radio line or the prompt, show a
   card, ask for a sting or a music level), then player, weapon, enemies, explosives. Events are synchronous: a hit
   marker is armed and a sound is started inside the very call that emitted the event.
2. `audio.update` (`src/audio.js:747-764`): listener from the camera → mix state (3.19) → conductor (3.24) → loops
   that could not start yet, air absorption of running loops → ambience (3.23) → trackers (3.22).
3. `hud.update` (`src/hud.js:785-809`): radio and kill-feed clocks (with a time step of 0 while paused) → if the HUD
   is shown: objective typewriter, banner, message, hit marker → crosshair, damage arcs, world markers, weapon bar,
   health, prompt ring, zone name → minimap (at most 32 times a second).
4. `menus.update`: gamepad navigation, the location card's wipe.
5. The picture is drawn.

Every HUD write is change-detected: a text, class or style is only touched when its value changed
(`src/ui/dom.js:35-58`). Keep that habit in the port: most HUD values change a few times a second at most.

### 3.2 Mission badge

- `hud.setObjective(text)` (`src/hud.js:707-721`): a new text restarts the typewriter:
  `shown = text[0 … clamp(floor(t · 46), 0, length)]` with `t` the seconds since the call (`src/ui/logic.js:43-45`).
  The longest objective (32 characters) takes 0.70 s. At the same moment the badge flashes for 0.9 s: its left bar
  jumps to `ink` and returns to `gold`; the rule warms from `ink` to `gold` and drops back to `ink` at the end. An
  empty text hides the label and the line.
- Reel bullets (`src/hud.js:352-370`): one bullet per reel, in code order 1, 2, 3. A bullet is filled ("done") when
  the truck marker is among the world markers (all reels in), else when its code is not among the open reel markers.
  So the badge shows **which** reels are back, not only how many. The count reads `done/total`.
- Hold the Block (`src/hud.js:730-737`): bullets and count are replaced by the tally line.
- The flow sets all of this: `src/game.js:330-353`.

### 3.3 Minimap

**Static plan**, painted once to an off-screen image and again every time the HUD is shown
(`src/ui/minimap.js:54-162`, `src/hud.js:674-681`). It covers the play bounds plus 24 m on every side. Paint order:

1. Everything in city ink; the play bounds in ground ink.
2. Ground by surface, one cell per square metre sampled at the cell centre: asphalt → road ink, dirt → dirt ink.
3. The El: for each track centre line (z = −2.1 m and +2.1 m) two rails 0.75 m either side of it, across the whole
   plan, line width max(1 px, 0.22 × plan scale); a tie across the two rails every 2 m.
4. Every static collider's footprint (2.7 says which are skipped): first all cover boxes in cover ink, then all
   wall boxes in wall ink (at least 1 px each way).
5. A 1 px wall-edge outline (55 %) round every wall box at least 3 px wide and deep; the play bounds outlined (50 %).

**Every draw** (`src/ui/minimap.js:196-273`):

1. Clear. Draw the plan turned about the map centre by the player's yaw (clockwise on screen for a positive web
   yaw), scaled to `side / 60` px per metre, shifted so the player's position is the centre; bilinear filtering.
2. Enemy pips: every living enemy whose state or mode name contains one of `engage`, `attack`, `chase`, `rush`,
   `fire`, `combat`, `strafe`, `lunge`, `melee`, or that fired in the last 2 s (`src/ui/logic.js:288-296`).
3. Objective bullets: the same list the world markers use (open reels, then the truck once every reel is in).
4. The view cone, then the player arrow, fixed at the centre and pointing up.

Map position of a world point (dx metres east and dz metres south of the player; `src/ui/logic.js:267-285`):

```
x = (dx · cos(yaw) − dz · sin(yaw)) · scale        # right of the centre, px
y = (dx · sin(yaw) + dz · cos(yaw)) · scale        # below the centre, px
pin to the rim: over = max(|x|, |y|) / half;  if over > 1: x /= over, y /= over      # a square rim, not a circle
```

`half` is half the map side minus the pin inset (11 px for bullets, 5 px for enemies).

### 3.4 Zone band

The band shows `level.zoneName(x, z)` of the player's position, re-read every frame (`src/hud.js:631-658`). The level
divides the block into four rectangles (a point outside all of them belongs to the nearest;
`src/level/layout.js:158-182`) and names them (`src/level.js:127-132`):

| Zone id | Rectangle (web metres) | Name shown |
|---|---|---|
| `west` | x −46 … −30, any z | `WEST END` |
| `shop` | x −30 … 22, z −34 … −11 | `CHOP SHOP` |
| `avenue` | x −30 … 22, z −11 … 34 | `THE AVENUE` |
| `lot` | x 22 … 46, any z | `THE CAGE` where z < −7, `THE LOT` where z > 7, `THE AVENUE` on the roadway between |

### 3.5 Weapon bar and cue line

`src/hud.js:501-549`, rules `src/ui/logic.js:324-347`, cue source `src/weapon/logic.js:166-172`.

- Both gun slots always show their own ammunition (the holstered gun's from `weapon.other`).
- The active slot is the gun in hand. During a melee strike the melee slot is the active one and neither gun is.
- **Low**: active, magazine not empty and at most ceil(0.27 × magazine size): 9 rounds of the CHOPPER's 30, 5 of
  the NINE's 15. The count and the unspent pips turn `gold`. **Empty**: the count turns `red`.
- Pips: one per round of the magazine; spent rounds dim from the right end (`ink` at 18 %).
- Key hints: `1`, `2`, `F` on a keyboard, `←`, `→`, `RB` on a gamepad, none on touch.
- The slots are buttons: a click or tap on a holstered gun switches to it, on the fist it strikes. Both play
  `ui_click`. The two round buttons beside the map pause, and pause and open the settings drawer (`src/hud.js:281-300`).
- Cue line, from the weapon's `cue`: nothing while switching weapons; `Reloading` during a reload; with an empty
  magazine `R — Reload` if rounds are left in reserve, else `Empty — Q swaps` (both in alarm style); `Low ammo` at
  the low threshold.

### 3.6 Crosshair

```
cone = weapon.spread                      # radians: half-angle of the fire cone (0.012 if unknown)
half = tan(vfov · π / 360)                # vfov = the camera's effective vertical field of view in degrees
px   = tan(cone) / half · (viewport height / 2) + 4 + (player is sprinting ? 10 : 0)
gap  = round(clamp(px, 4, 70) · 2) / 2    # px from the centre to the inner end of each tick
```

`src/ui/logic.js:99-104`, `src/hud.js:372-384`. The crosshair is hidden when the player is dead, when the aim blend
is above 0.6 (the sights take over), and when the weapon is lowered (sprinting or dropped). The gap therefore shows
the real cone: at 1080 px and 74° the CHOPPER at rest (0.0125 rad) gives 13 px, the NINE (0.0105 rad) 11.5 px, a
moving, blooming CHOPPER about 27 px; the ceiling is 70 px. Spread values and how they move belong to the weapons
spec.

### 3.7 Hit marker

`src/hud.js:306-313`, `386-392`; `src/ui/logic.js:107-125`. Driven by `player:hitEnemy {part, killed}`.

```
tier = killed ? kill : part == head ? head : hit          # a new event restarts the marker
k    = seconds since the event / duration                 # 0.24 s (hit, head), 0.42 s (kill)
k < 0.35:  scale = pop + (1 − pop) · k / 0.35,  opacity = 1           # pop 1.15 / 1.5 / 1.5
else:      u = (k − 0.35) / 0.65;  scale = 1 − 0.08 · u,  opacity = 1 − u
k ≥ 1:     hidden
```

Colour and bar width by tier (2.5, row 7). With reduced motion the marker does not pop (scale 1).

### 3.8 Damage arcs

`src/hud.js:321-334`, `394-416`; `src/ui/logic.js:150-161`. On `player:hit` with a source position a free arc is
taken (if all four are busy, the one with the least life left) and remembers the source's world x, z.

```
life    = 1.5 s, counting down
opacity = round(clamp(life / 0.6, 0, 1) · 20) / 20
angle   = atan2(sx − px, −(sz − pz)) + yaw        # clockwise from straight up, wrapped to (−π, π]
```

The arc glyph is rotated by `angle` about the screen centre every frame, so it slides round as the player turns.
Damage with no source (a fall) shows no arc.

### 3.9 Health bar

`src/hud.js:551-567`, `src/ui/logic.js:350-357`.

```
value    = ceil(health)                              # the number
fill     = round(health / max · 200) / 200           # the white bar, as a fraction
critical = health > 0 ? ceil(health / max · 10) ≤ 3 : true          # 30 % or less
when fill drops:  ghostHold = 0.45 s        when fill rises above ghost:  ghost = fill
each frame, while ghost > fill:  ghostHold > 0 ? ghostHold −= dt : ghost = max(fill, ghost − 0.9 · dt)
```

The ghost is a `red` bar (75 % opacity) behind the white one: it shows what was just lost, then drains. Critical:
the fill turns `red`, the number turns `red` and blinks. Regeneration and the low-health screen treatment belong to
the player spec.

### 3.10 Interaction prompt

`hud.prompt(spec)` with `{text, glyph, code, progress}` or `null` (`src/hud.js:743-761`, `660-667`). The flow shows it
while a reel is in reach and updates `progress` every frame (`src/game.js:554-594`): holding Interact fills the ring
in 2.4 s; letting go drains it at 1.6 per second (`src/config/flow.js:40-48`). The ring's progress stroke covers
`progress` of the circle from 12 o'clock clockwise (rounded to 0.005); while `progress > 0` the rule and the text of
the plate turn `gold`. The glyph is the Interact key of the device in use (`E`, `X`, `USE`).

### 3.11 Kill feed

Every `enemy:killed` adds a line, whoever caused the kill (`src/hud.js:315-319`, `569-590`): the weapon glyph
(`chopper`, `nine`, `melee`; none for a blast), `Goon down` or `Buzzard down`, and the `Headshot` tag when the part
was the head. A fifth line pushes the oldest out. Lines keep their time while the game is paused.

### 3.12 Banner and centre message

Banner (`hud.warn(text, secs)`, `src/hud.js:592-600`, `762-768`; `src/ui/logic.js:131-140`), with `k` = elapsed / length:

| k | Opacity | Horizontal stretch of the text |
|---|---|---|
| 0 → 0.08 | 0 → 1 | 1.22 → 1.08 |
| 0.08 → 0.14 | 1 → 0.35 (one flicker) | → 1.02 |
| 0.14 → 0.20 | 0.35 → 1 | → 1.00 |
| 0.20 → 0.82 | 1 | 1.00 |
| 0.82 → 1 | 1 → 0 | 1.00 |

Stretch = 1 + 0.22 · (1 − k / 0.2)² for k < 0.2. With reduced motion: solid until 90 %, then gone, no stretch.
The flow raises it when a reel's reinforcement wave is queued (`Contact — <direction>`, `src/game.js:612-613`) and
when a holdout wave starts (`Wave N — <direction>`, `src/game.js:685-686`). The direction is the 8-way compass sector
of the sum of the wave's spawn offsets from the player: `sector = round(atan2(dx, −dz) / 45°) mod 8`, 0 = NORTH,
clockwise (`src/game/spawn.js:11-14`, `src/game.js:463-480`).

Centre message (`hud.message(text, secs)`, `src/hud.js:769-778`): one line, replaced by the next. Used for the truck
refusal (3.5 s, at most every 8 s; `src/game.js:656-658`), the holdout countdown (`Wave N in 3`, `2`, `1`, one second
each; `src/game.js:726-729`) and, on desktop browsers only, the mouse-capture hint (`src/game.js:363-378`).

### 3.13 World markers

`hud.setMarkers([{id, code, label, pos, kind}])`: the open reels (`kind: 'reel'`), then the truck (`kind: 'exit'`)
once every reel is in (`src/game.js:330-341`). Per marker, every frame (`src/hud.js:418-499`,
`src/ui/logic.js:170-257`):

```
hide the whole layer while the aim blend ≥ 0.5
hide this marker when its horizontal distance to the player < 3 m
P        = marker position + 1.9 m up (reel) or + 1.2 m up (truck)
(x, y)   = P in normalised device coordinates (−1 … 1, y up);  behind = P is behind the camera
if behind: (x, y) = (−x, −y)
over     = max(|x| / 0.9,  y ≥ 0 ? y / 0.78 : −y / limDown)
on screen (not behind and over ≤ 1):  drawn at (x, y)
otherwise pinned:                     drawn at (x / over, y / over); dead behind → bottom centre
limDown  = clamp(2 · (top of the weapon bar − 34 px) / viewport height − 1, 0.2, 0.9)      # 0.706 at 1080 px
```

- On screen: opacity 0.9; 0.22 when `hypot(x, 0.6 · y) < 0.16` (it would cover the aim point).
- Pinned: opacity 0.72, then moved to where it can be read. A pin occupies 14 px either side of its anchor, 30 px
  above and 22 px below. It must stay 46 px (across) or 54 px (up and down) from every pin already placed this
  frame and 2 px clear of every HUD block: the kill feed while it has lines, the badge, the minimap block, the radio
  strip and the prompt while shown, the location card, and the touch controls. Search order: (1) along its own edge,
  one gap at a time, alternating sides, inside the allowed span (side edges: from 11 % of the height down to the
  bottom limit; top and bottom edges: from 5 % to 95 % of the width); (2) in from the edge 8 px at a time, up to
  30 % (or 70 %) of the screen, trying up to two gaps either way at each step; (3) along the edge again, ignoring the
  blocks; (4) stay.
- The tag shows the horizontal distance in whole metres.

The glowing beacon on a reel case and the truck's lights are world props, not HUD (level and props specs).

### 3.14 Radio subtitles

Two queues work together.

- The flow's queue (`src/game/radio.js:12-55`, `src/game.js:114-133`): `say(text, hold)` appends a line. When
  nothing is up the next line starts: the queue is busy for `length / 58 + hold + 0.3` s. Starting a line calls
  `hud.radio('IPX VAULT', text, hold)` and emits `radio:line` (the squelch sounds). The queue is emptied on a run
  reset, on death, on reaching the truck (before the last line is queued) and on going back to the title.
- The HUD's queue (`src/ui/logic.js:51-87`, `src/hud.js:608-629`): types the line at 58 characters a second and
  removes it at `length / 58 + hold`, so the strip is empty for 0.3 s between two lines.

The strip is shown only while a line is up and the state is neither `paused` nor `title`. It is announced to screen
readers as a polite live region. There is **no voice**: the radio is text plus two squelch sounds.

### 3.15 Small screens, touch, reduced motion

The web HUD rearranges itself for phones (`src/ui.css:1829-2312`). Summary, for a port that also targets handhelds:

| Condition | Changes |
|---|---|
| Width ≤ 760 px | Smaller map and slots (2.4). Banner and message move under the map row and may use the full width. Title pickers and buttons reflow to two columns |
| Height ≤ 520 px | The radio moves up beside the top row (top inset + 92 px), clipped to two lines showing the newest words. Prompt and message sit just above the weapon bar; the message hides while a prompt is up. Cards use two stat columns |
| Height ≤ 520 px and width ≤ 800 px | The badge narrows and drops its `OBJECTIVE` label; banner type 17 px |
| Touch in use | The kill feed moves up under the badge (the left thumb's stick owns the left-middle). The location card sits centred over the weapon bar. In portrait everything that talks stacks in the upper half: feed, banner, radio, then the aim point, prompt and message 36 px under it |
| Small landscape touch (≤ 520 high, ≤ 720 wide) | The melee slot is removed (the thumb button does it) |
| Reduced motion | Transitions and animations are cut to 1 ms; the banner does not flicker or stretch; the hit marker does not pop; the location card shows at once |

The thumb controls themselves (stick, fire, aim, jump, crouch, reload, swap, melee, use) belong to the input spec;
they reserve 214 × 236 units at the bottom right and 206 × 196 at the bottom left (`src/input.css:19-24`).

### 3.16 Menus: screens, timers, what the buttons do

`menus.show(screen, data)` with `'none' | 'title' | 'paused' | 'dead' | 'complete'` (`src/menus.js:265-295`): closes
the drawer, rebuilds the card, fades the veil (0.5 s) and the screen (0.45 s) in, and puts the focus on the screen's
primary button 30 ms later.

| Moment | What happens | Source |
|---|---|---|
| Title: a picker option | Writes the setting at once (`mode`, `difficulty`, `time`); the mode note follows | `src/menus.js:75-90`, `177-184` |
| Title: `Hit the block`, or Enter with no control focused, or gamepad Start | Unlocks audio, captures the mouse, `game.start({mode})` | `src/menus.js:92-96`, `src/game.js:793-800`, `932-945` |
| First start: intro, 2.4 s | The picture fades in from black between 0.05 s and 1.3 s; the location card appears at 0.25 s and leaves when the intro ends (about 2.15 s on screen); its first line is wiped in left to right in 28 steps over 1.1 s; the first radio line starts at 0.9 s. The player has control throughout | `src/config/flow.js:9-20`, `src/game.js:836-848`, `src/menus.js:399-410` |
| Retry, restart, redeploy: quick intro, 1.1 s | Fade only: no card, no radio line | `src/game.js:255-259`, `271-285` |
| Pause | By the pause key (Esc, P, Start), the HUD's pause button, the HUD's gear (pauses, then opens the drawer), losing the mouse capture, the window losing focus or being hidden. Pausing during the intro ends the intro | `src/game.js:287-292`, `918-930` |
| Resume | `Resume`, the pause key once the card has been up 0.35 s, gamepad B | `src/game.js:803-807`, `src/menus.js:377-380` |
| `Restart run` (pause) and `Run it back` (death) | A new run of the same mode, counted as a retry | `src/game.js:270-279` |
| `Run it back` (debrief) | A new run with the retry count back at 0 | `src/game.js:281-285` |
| `Back to title` | Everything reset, title screen | `src/game.js:300-318` |
| Death | HUD off at once, `dead` sting; the picture eases to 12 % saturation and a 55 % dark fade; the card after 1.5 s | `src/game.js:809-816`, `879-893`; `src/config/flow.js:23-26` |
| Truck reached | HUD off, `complete` sting, the last radio line; the picture eases to 70 % saturation and a 72 % fade; the card after 3.3 s | `src/game.js:662-672`, `818-826` |
| A card comes up | Music level back to calm; the holdout best score is stored | `src/game.js:744-754` |

Card data handed to the death and debrief cards (`src/game/stats.js:14-35`): `mode`, `difficulty`, `time`, `reels`,
`total`, `wave` (holdout waves cleared), `kills`, `headshots`, `shots`, `hits`, `score`, `best`, `newBest`,
`accuracy` (hits / shots; absent when no shot was fired), `retries`, `rating`, `ratingName`. Rating points 0…5
(`src/config/flow.js:172-205`): time under 270 s 2 points, under 400 s 1; accuracy at least 50 % 2 points, at least
30 % 1; no retries 1. Names in 2.9.

### 3.17 Menus: navigation

- **Pointer**: click or tap. The pointer entering a button plays `ui_hover` (not for touch); every activation plays
  `ui_click` (`src/menus.js:52-73`).
- **Keyboard**: Tab and Shift+Tab walk the focus order; Enter or Space activates; arrow keys move a focused slider
  by one step. In the drawer the focus is trapped (Tab wraps), Left / Right on a tab switches tabs, Esc closes the
  drawer without resuming (so does P) (`src/ui/panel.js:252-277`, `src/menus.js:387-393`). On the pause card Esc or P
  resumes.
- **Gamepad** (`src/menus.js:322-383`; signals `src/input.js:994-1021`; timing `src/config/player.js:197`):

| Input | Effect |
|---|---|
| D-pad up / down, or left stick past 0.6 | Moves the focus through the current scope (the drawer when open, else the title or the card), wrapping at the ends. First repeat after 0.38 s, then every 0.17 s. With nothing focused, down takes the first control and up the last (`src/ui/logic.js:396-400`) |
| D-pad left / right, or stick | Once per push. On a drawer tab: switch tab. On a slider: one gamepad step (sensitivity 0.1, volume 5, field of view 1). Inside a segmented control: focus the neighbouring option, no wrap (A then selects it). Anywhere else: like up / down |
| A | Activates the focused button; with none focused, the screen's primary button |
| B | Closes the drawer; on the pause card, resumes |
| Start | Title: starts the run. Death and debrief: the primary button. Pause: resumes |

  Every focus move plays `ui_hover`. While the gamepad drives the menu the focus ring is always drawn; moving the
  mouse turns that off again.

Focus orders: title: Story, Hold the Block, Hustler, Boss, Kingpin, Day, Night, **Hit the block**, Settings,
Controls. Pause: **Resume**, Settings, Controls, Restart run. Death and debrief: **Run it back**, Back to title.
Drawer: the selected tab, Close, then the rows top to bottom. Opening the drawer remembers what opened it and gives
the focus back on closing (`src/ui/panel.js:225-250`). The drawer re-reads every setting when it opens and whenever a
setting changes (`src/ui/panel.js:191-218`).

### 3.18 Audio: one-shots, loops, the listener

`audio.play(name, {pos, volume, pitch, delay, bus, ref, roll, prio})` (`src/audio.js:345-413`):

1. **Refused** when: the audio is not unlocked; the game is paused and the bus is not `dry` or `music`; the sound
   was started less than its gap ago; it is an impact within 22 ms of another impact; it has a position more than
   160 m from the listener.
2. **Space**: 3D when a position is given and the bus has 3D channels (`world`, `amb`), else flat.
3. **Channel**: if the name already plays its maximum number of voices, the oldest of them is replaced; else a
   free channel of the bus; else the busy channel with the lowest priority not above the new sound's (the oldest
   among equals); else refused. A replaced voice fades with τ 4 ms and the new one starts 6 ms late.
4. **Variation**: next variant; playback rate = `pitch · (1 ± jitter)`, clamped 0.25…4 (pitch and length change
   together); gain = `definition volume · event volume · (1 − U(0, 0.08))`.
5. **3D**: position, reference distance and roll-off are set, and the air low-pass for the distance at that moment.

`audio.loop(name, {pos, volume, pitch, phaseLock})` (`src/audio.js:419-520`): a loop has its own nodes outside the
channel pools. It starts as soon as the audio is unlocked and its buffer exists, at a random point in the first 90 %
of the buffer (phase-locked loops: at the score's position), and fades in with τ 0.08 s. `setVolume` τ 0.06 s,
`setPitch` τ 0.05 s (0.25…4), `stop(fade)` fades with τ = max(5 ms, fade / 3). A loop with a position is 3D and
refreshes its air low-pass whenever the cut-off moved by more than 200 Hz. Loops get no pitch jitter.

The listener is the camera: position, forward and up, every frame (`src/audio.js:598-619`).

### 3.19 Mix state

Every frame (`src/audio.js:554-596`):

```
i  += (level.interiorAt(listener) − i) · min(1, 3 · dt)                # interior factor
ambDuck   = min(depth of every duck still held)                         # 1 when none
musDuck   = min(depth of the held ducks that include the music)
release   = max(0.1 s, release of every duck that is held or ended less than 4 of its release times ago)
musicDip += (1 − musicDip) · min(1, 3.5 · dt)
muffle   += (floor − muffle) · min(1, dt · (floor > 0 ? 3 : 0.9))

MUFFLE cut-off       = 20000 · 0.03^muffle Hz, Q 0.6      τ 0.02 s closing, 0.08 s opening
PAUSE gain           = paused ? 0 : 1                     τ 0.08 s
ambDuck gain         = ambDuck · trainDuck                τ 0.012 s down, `release` up
musicDuck gain       = musDuck · (0.6 + 0.4 · trainDuck) · (paused ? 0.45 : 1)        same time constants
musicDip gain        = musicDip                           τ 0.03 s down, 0.15 s up
musicLowpass cut-off = paused ? 1300 Hz : 20 kHz, Q 0.6   τ 0.2 s
ambLevel gain        = ambState · (paused ? 0 : 1) · (1 − 0.55 · i)                   τ 0.6 s down, 0.4 s up
ambLowpass cut-off   = 20000 · 0.08^i Hz, Q 0.5           τ 0.2 s
STREET return        = 0.8 · (1 − 0.9 · i);   SHOP return = 0.9 · i                   τ 0.1 s
```

- **Ducks** (`duck(depth, hold, release, musicToo)`, `src/audio.js:541-545`): a duck holds its depth for `hold`
  seconds and then lets go with time constant `release`. Who ducks what: 2.15.
- **Muffle** (`muffleTo(m, floor)`, `src/audio.js:691-694`): `muffle = max(muffle, m)`; `floor` is where it settles
  (0 normally, 0.85 while dead). Cut-offs: 0.2 → 9.9 kHz, 0.4 → 4.9 kHz, 0.56 → 2.8 kHz, 0.7 → 1.7 kHz,
  0.8 → 1.2 kHz, 0.85 → 1.0 kHz, 1 → 600 Hz. A 20-damage hit (muffle 0.5) closes the top to 3.5 kHz and it
  reopens with a time constant of 1.1 s.
- **Interior** (street versus shop): `level.interiorAt` is 1 inside the shop's box (x −24…6, y 0…6.3,
  z −31…−11 m) and falls linearly to 0 over 1.5 m outside it (`src/level.js:30`, `147-159`, `src/level/shop.js:333`),
  and the mixer follows it with a time constant of a third of a second. Fully inside: the ambience drops to 45 %
  behind a 1.6 kHz low-pass (5.7 kHz half-way), the street reverb falls to a tenth and the shop reverb comes up; the
  guns swap their street tail for the shop tail (3.20).
- **Ambience state**: 0.6 on the title, 1 in a run, 0.7 dead, 0.8 on the debrief (`src/audio/react.js:278-294`).

### 3.20 Gun tails

A shot is three samples: the dry shot and one or two tails (`src/audio/react.js:35-61`).

```
since = seconds since the previous shot
k     = since < 0.45 ? 0.4 + 0.6 · since / 0.45 : 1
the previous shot's tails are turned down to 0.25 · k
out = cos(i · 90°),  in = sin(i · 90°)                         # equal-power split by the interior factor
play <weapon>_tail_out at out · k (if out > 0.05) and <weapon>_tail_in at in · k (if in > 0.05)
if k < 1: 105 ms later, if no newer shot came, raise these tails to out and in
```

In automatic fire (CHOPPER: 83 ms between rounds, k = 0.51) every new tail starts low, the earlier ones are pushed
down, and only the last tail of the burst is let up to full: a burst ends on one clean slap off the block.

### 3.21 Near miss

On every enemy shot (`src/audio/react.js:162-187`), with `pos` and `dir` of the round:

```
along   = (listener − pos) · dir;          if along < 2 m: nothing
closest = pos + dir · along;  d = |closest − listener|
if d > 3.2 m or d < 0.25 m: nothing        # too wide, or it hit (the hurt sound covers that)
if the world blocks the line from pos to closest: nothing
play whizz at closest, volume clamp(1.15 − d / 3.5, 0.3, 1),
     delayed by min(1.5 s, along / 70 m/s) for a Buzzard bolt, not delayed for a Goon's hitscan round
```

### 3.22 Trackers

`src/audio/react.js:310-372`.

- **Rotors**: every living Buzzard carries a `rotor` loop at its position, with its own tune U(0.96, 1.06).
  Rate = tune · (0.94 + 0.3 · clamp(speed / 10 m/s, 0, 1)). Every 0.25 s the Buzzards are ranked by distance: the six
  nearest within 90 m play at volume 1, the rest at 0. The loop stops (0.12 s) when the Buzzard dies.
- **Heartbeat**: while playing and alive with a health fraction h < 0.35: `k = clamp((0.35 − h) / 0.25, 0, 1)`,
  volume 0.25 + 0.4 k, rate 1 + 0.35 k (70 beats a minute rising to 94 at h ≤ 0.10). It stops with a 0.4 s fade.
- **Reel grab**: the first `objective:progress` starts the loop (volume 0.8), every further one sets the rate to
  0.85 + 0.4 · progress. It stops (0.08 s) when 0.3 s pass without progress, when the reel is secured, on pause and
  when the state leaves `playing`.
- **Fuse hiss**: started by the explosives when a tank or rack is lit, 3D at the item, volume
  0.25 + 0.75 · (burnt fraction of the fuse)², stopped at the blast (`src/explosives.js:250-262`, `432-441`).

### 3.23 Ambience

`src/audio/ambience.js`.

- **Beds**: the day mix `m` moves toward 1 by day and 0 by night at 0.5 per second; `bed_day` plays at `m`,
  `bed_night` at `1 − m`. Time of day only changes between runs.
- **Wind**: a gust target U(0.15, 1) is drawn every U(3, 9) s and approached at 0.5 per second.
  `near = clamp(1 − (horizontal distance to the El deck's footprint) / 25 m, 0, 1)`; the footprint is x −46…46,
  z −5.4…5.4 m (`src/level/el.js:153`).
  Volume = (0.35 + 0.25 · (1 − m)) · (0.45 + 0.75 · near) · (0.3 + 0.7 · gust); rate = 0.9 + 0.22 · gust.
- **Neon and steam**, re-chosen every 0.5 s: a loop at each of the three nearest neon lamps within 15 m (volume
  0.5 + 0.5 · (1 − m)) and each of the three nearest steam vents within 24 m (volume 1). A source that drops out
  fades for 0.5 s.
- **Far one-shots**: the schedule in 2.14.
- **The El train**. The atmosphere sends `train:pass` three times per pass (a train every 40–70 s, 16.5 m/s, five
  cars, 79.8 m long): `approach` (about 8.8 s), `over` (about 10.4 s), `gone` (about 8.8 s) (`src/config/look.js:252-263`,
  `src/atmos/plan.js:171-193`). With `u` = time in the phase / its duration:

| | approach | over | gone |
|---|---|---|---|
| `train_rumble` volume | 0.2 + 0.8 u | 1 | 1 − u |
| `train_clack` volume | (0.2 + 0.8 u) · u | 1 | 1 − u |
| Train duck target | 1 − 0.2 u | 0.72 | 0.8 + 0.2 u |

  Both loops sit at the point of the train nearest the listener: x = the listener's x clamped to the train's
  extent, y = the rail top (6.83 m), z = its track (eastbound +2.1 m, westbound −2.1 m), updated every frame. Clack
  rate = clamp(speed / 16.5 m/s, 0.5, 1.6). In 70 % of passes `train_squeal` plays once, 20–60 % into `over`. The duck
  approaches its target at 1.5 per second and returns to 1 afterwards; it scales the ambience fully and the music by
  0.6 + 0.4 · duck (0.89 at the deepest). At the end the rumble fades 1.2 s, the clack 0.8 s.
- **Reel boomboxes**: one `boombox` loop 0.6 m above every reel that is still out, phase-locked to the score, so
  walking up to a reel you hear the same beat coming out of the case. Its loop fades (0.25 s) when the reel is
  secured; all restart on a run reset; none in Hold the Block (`src/audio/ambience.js:211-229`).

### 3.24 The music conductor

`src/audio/conductor.js`. One shared clock starts 0.15 s after the audio unlocks. Every stem is a loop started on
that clock; a stem whose buffer arrives later joins at offset `(now − clock start) mod 20.8696 s`. The stems never
stop: only their gains move. The score therefore plays in every state.

**Intensity**, every frame (`src/audio/conductor.js:195-209`):

```
meter = max(0.15, meter − 0.06 · dt)                       # the conductor's own combat meter (inputs: 2.15)
want  = mode == play ? max(target, meter) : mode == title ? 0.15 : target      # target = what the game asked for
I    += (want − I) · min(1, 2 · dt)
if mode is dead or complete: I = min(I, 0.2)
tier  = 2 if I ≥ 0.8 (or tier was 2 and I ≥ 0.68);  1 if I ≥ 0.4 (or tier ≥ 1 and I ≥ 0.32);  else 0
```

A firefight alone can open the top tier: an alert lifts the meter to 0.6; from there the player's own fire adds
0.144 a second at the CHOPPER's rate against the decay of 0.06 a second, every enemy round adds 0.04 and every hit
taken 0.15, so a few seconds of exchange reach 0.8.

**Layer gains** (`src/audio/conductor.js:23-43`), applied with τ 0.5 s (0.22 s in `dead` mode); the drum low-pass with τ 0.35 s:

```
smooth(a, b, x) = t² · (3 − 2t),  t = clamp((x − a) / (b − a), 0, 1)
o = smooth(0.25, 0.55, I);   k = smooth(0.35, 0.60, I);   r = smooth(0.75, 0.95, I) · gate
drums = 0.78 + 0.22 o     hats = 0.10 + 0.90 o     bass = 0.50 + 0.50 o     crackle = 0.60 − 0.30 o
keys  = title mode ? max(k, 0.55) : k · (1 − 0.1 r)        strings = r        bell = 0.9 r
drum low-pass = 700 · 26^o Hz
dead mode: every stem 0 except crackle 0.55 and keys 0.16; drum low-pass 400 Hz
```

**Riser and impact** (`src/audio/conductor.js:154-218`). When the tier becomes 2 in `play` mode and no riser is in flight:

- Only if the last riser started more than 25 s ago, or the `all` sting forces one. Otherwise the top layers simply
  fade in.
- Impact time = the first bar line at least 1.4 s ahead (2.6 s if a sting started in the last 1.5 s).
- `m_riser` must end on the impact: it starts 5.217 s before it, or, when that moment has passed, now, from the
  matching point inside the file. Gain 0.85. `m_impact` plays on the bar line at gain 0.8.
- `gate = 0`: strings and bell are faded to 0 (τ 0.15 s) and jump to their gains on the impact. The whole stem bus
  dips to 0.5 from half a second before the impact (τ 0.12 s) and jumps back to 1 on it.
- If `I` falls below 0.68 while more than 0.6 s remain, riser and impact are stopped and the gate reopens.

**Stings** (`src/audio/conductor.js:265-290`, `src/audio.js:742-746`). They play at gain 1 beside the stems, not under the
stem bus.

| Sting | Starts | Stems | Also |
|---|---|---|---|
| `reel` | On the next beat at least 40 ms ahead | Stem bus to 0.4 for 3.4 s (τ 0.06 s down, 0.5 s up) | — |
| `all` | Same | Same | Forces a riser at the next update in the top tier (the game goes hot at the same moment): the impact lands on a bar line at least 2.6 s later |
| `complete` | Same; **refused** if another sting started less than 6 s ago | Stem bus to 0.12 for 7 s | Mode `complete` |
| `dead` | At once | Mode `dead`; a riser in flight is cancelled | Effects muffled to 1, settling at 0.85 |

**Modes**: `title` and `play` follow the game state (title → `title`; intro and playing → `play`); `dead` and
`complete` are set by their stings; entering `title` or `play` cancels a riser in flight (`src/audio/conductor.js:256-264`).

### 3.25 As built: quirks, dead ends, differences from the design documents

Where `docs/DESIGN.md` and the code disagree, the code wins. Each line says what a port should do.

| Item | As built | Suggestion |
|---|---|---|
| Compass | `docs/DESIGN.md:242` and `docs/CONTRACT.md:683` still mention a compass strip. There is none: the minimap replaced it (`docs/DESIGN.md:312`). A hidden "N" element remains (`src/ui.css:271-273`) | No compass |
| Title eyebrow, boot line, location time | The code follows Direction v2: `IPX PRESENTS · HOLLIS, QUEENS`, "Waiting on the next train", the location card's clock by time of day | Use the code's copy |
| HUD typing speeds | Hard-coded in `src/hud.js:41-42`; equal to `src/config/flow.js:221-222`, which only the flow reads | One shared constant |
| `radio_out` | Plays `hold` seconds after the line **starts**, on a real-time timer: for the 127-character intro line that is 4.4 s in, while the line stays up until 6.6 s, and pausing does not delay it (`src/audio/react.js:268-272`) | Play it when the line leaves the strip |
| Head-hit pitch on body impacts | `src/audio/react.js:153` raises the impact pitch 25 % for `part === 'head'`, but the `impact` event carries no `part` (`src/combat.js:204`): never happens | Drop, or wire it deliberately |
| Goon voice pitch | `src/audio/react.js:214`, `223` read `enemy.voice`; nothing sets it: every Goon has pitch 1 | Give each Goon a voice pitch (say 0.92–1.08) or drop it |
| Hit grunt on the killing shot | `enemy:hit` is emitted before the Goon is marked dead, so the last hit plays `grunt_hit` and `grunt_death` together | Skip the hit grunt on a kill |
| `goon_rush` length | The sound is 0.7 s ("0.6 s wind-up" in its comment); the wind-up is 0.28 s and the dash 0.36 s (`src/config/enemies.js:183-185`), so it covers both | Keep as one "rush" sound, or split |
| `train_clack` loop | Built for a 16.3 m car at 16.5 m/s (0.988 s); the train's cars repeat every 16.1 m | Negligible; match the final train model |
| `complete` sting | Refused, and the music mode not changed, if the truck is reached within 6 s of another sting. Not reachable in practice (the truck is far from every reel) | Always play it |
| NINE shot level | Scaled 0.95 twice (definition and event) | Use 0.90 |
| Kill feed | Lists every enemy death without asking who caused it (a Goon caught by a falling Buzzard's burst or by a chain explosion gets a line too, with no weapon glyph) | Keep |
| Defined, never used | Sound `ui_tick`; the "court" map ink; `copy.title.timeNotes`, `text.notes.time`; the melee names `Pistol whip` / `Rifle butt` (the melee slot shows no text); the `music` channel pool | Leave out |
| Minimap plan | Repainted every time the HUD is shown, although nothing it draws changes during a run | Bake once per level |
| Web-only copy and controls | "generated in your browser" (title footnote, boot note), mouse-capture hints, the browser paragraph of the controller note, the fullscreen row | Rewrite for the platform |

---------------------------------------------------------------------------------------------------

## 4. Unreal mapping

Asset names in this section (`WBP_…`, `SCL_…`, `SMX_…`, `ATT_…`, `SW_…`) are proposals: the shared conventions
only fix names for meshes and textures.

### 4.1 Units and conversions

Unreal(X, Y, Z) = (x_web, z_web, y_web) × 100. X is east, Y is south, Z is up.

| Web value | Unreal value |
|---|---|
| Reference screen 1920 × 1080 px | Author the widgets at 1920 × 1080 with the same numbers as Slate units; scale with the DPI rule (4.2) |
| CSS font size in px | Slate font size = px × 0.75 at the default 96 DPI font setting (16 px → size 12); with the project's font DPI set to 72, size = px |
| CSS letter spacing in em | Slate letter spacing = em × 1000 (0.24 em → 240) |
| Web yaw θ (radians, 0 = north, growing counter-clockwise) | Unreal yaw ψ = −90° − θ in degrees (0 = east, growing clockwise seen from above). North is −Y |
| Offset to a point: dx east, dz south (m) | ΔX / 100, ΔY / 100 |
| Vertical field of view 74° (range 60…95) | Keep the **vertical** angle fixed across aspect ratios; as a horizontal angle at 16:9 it is 106.5° (range 91.5°…125.5°) |
| Weapon cone 0.0125 rad (CHOPPER), 0.0105 rad (NINE), 0.012 rad (fallback) | 0.716°, 0.602°, 0.688° |
| Marker anchor: reel +1.9 m, truck +1.2 m; hidden inside 3 m | +190 cm, +120 cm on Z; 300 cm |
| Minimap: view radius 30 m, plan margin 24 m, 2.5 px per m | 3000 cm, 2400 cm, 0.025 px per cm. The plan covers X −7000…7000, Y −5800…5800 |
| Plan thresholds: wall above 2.2 m; skip undersides above 0.9 m and tops below 0.35 m | 220 cm, 90 cm, 35 cm (Z) |
| Minimap view cone ±0.62 rad; damage arc 48° | ±35.5°; 48° |
| Zone rectangles (3.4) | `west` X −4600…−3000. `shop` X −3000…2200, Y −3400…−1100. `avenue` X −3000…2200, Y −1100…3400. `lot` X 2200…4600: THE CAGE where Y < −700, THE LOT where Y > 700 |
| Reels (−4, 0, 1), (−9.5, 0, −21.5), (35.25, 0, −22.5); truck zone (35.9, 0, 29.7) (`src/level/data.js:10-18`) | (−400, 100, 0), (−950, −2150, 0), (3525, −2250, 0); (3590, 2970, 0) |
| Shop interior box x −24…6, y 0…6.3, z −31…−11; fade 1.5 m | X −2400…600, Y −3100…−1100, Z 0…630; 150 cm |
| El deck footprint x −46…46, z −5.4…5.4; wind falls off over 25 m | X −4600…4600, Y −540…540; 2500 cm |
| Train: rail top 6.83 m, tracks z ±2.1 m, 16.5 m/s, 79.8 m long | Z 683 cm, Y ±210 cm (eastbound on +210), 1650 cm/s, 7980 cm |
| Audio reference distances (2.11, 2.12) | × 100 (5 m → 500 cm) |
| Cull 160 m; air-absorption constant 48 m (floor of 1.6 kHz reached at 121 m) | 16 000 cm; 4800 cm (12 100 cm) |
| Near miss: at least 2 m ahead, passing between 0.25 and 3.2 m; bolt 70 m/s | 200 cm; 25…320 cm; 7000 cm/s |
| Rotors: audible within 90 m; pitch reference speed 10 m/s | 9000 cm; 1000 cm/s |
| Landing volume 0.35 + speed / 10 m/s | 0.35 + speed / 1000 cm/s |
| Explosion muffle: full inside 5 m, none beyond 20 m | 500 cm, 2000 cm |
| Neon within 15 m, steam within 24 m, Goon steps within 45 m | 1500 cm, 2400 cm, 4500 cm |
| Boombox 0.6 m above the reel position | +60 cm on Z |
| Far one-shots: 60–150 m (2–16 m up); street 45–105 m along X, ±12 m across, 1.5 m up; roof 9–27 m, 7–16 m up | × 100 |
| Music: 92 BPM, bar 2.608696 s, loop 20.869565 s | Quartz clock: 92 BPM, 4/4; eight bars |

Camera-relative directions need no yaw conversion at all if they are built from the camera's own horizontal
forward `F` and right `R` vectors. With `o` the horizontal offset from the player to a point:

```
minimap:      x = (o · R) · scale        y = −(o · F) · scale                (px right of / below the centre)
damage arc:   angle = atan2(o · R, o · F)                                    (clockwise from straight up)
world marker: nx = (v · R) / (|v · F| · tan(hfov / 2))    ny = (v · U) / (|v · F| · tan(vfov / 2))    behind = v · F < 0
              (v = camera to anchor in 3D, U = camera up; then the clamp of 3.13 with nx, ny)
```

### 4.2 Structure of the interface

| Web | Unreal |
|---|---|
| One HUD layer over the canvas | `WBP_HUD` added to the viewport by the player controller's HUD; child widgets per block (`WBP_Badge`, `WBP_Minimap`, `WBP_WeaponBar`, `WBP_Crosshair`, `WBP_KillFeed`, `WBP_Banner`, `WBP_Prompt`, `WBP_Radio`, `WBP_MarkerLayer`). Canvas Panel anchors: top-left, top-right, top-centre, left-middle, centre, bottom-centre |
| Fixed CSS pixels | Project DPI scale rule "Shortest Side", scale 1.0 at 1080, linear above and below, so the HUD keeps its share of the screen at any resolution. (The web keeps pixels instead; decide in section 6) |
| Safe-area insets and 16 px gutters | A Safe Zone widget round the HUD and the menus, plus the 16 px / 12 px / 10 px paddings of 2.4 |
| Brand tokens as CSS variables | One data asset (or a struct in a developer-settings class) with the fourteen colours and the font assets; every widget style reads from it, so the real IPX identity can be dropped in later |
| Anton, Archivo web fonts with fallbacks | Import the font files as Font Face assets and build two fonts: `F_Display` (Anton Regular) and `F_UI` (Archivo 400, 500, 600, 700, 800, 800 italic). No fallback stack is needed once the fonts ship with the game |
| Tabular figures | Slate does not expose OpenType features: use the font's monospaced-digit rendering where the engine version offers it ("force monospaced" on the font info), or right-align numbers in fixed-width boxes |
| Change-detected DOM writes, CSS transforms | Event-driven widgets: set text and visibility only on change; move things with render transforms, not layout. No property bindings polled every frame |
| CSS transitions and keyframes | UMG animations for the fixed ones (HUD fade, feed slide-in, blink, drawer slide); code-driven values for the formula ones (banner pose, hit marker, arcs, ghost bar) |
| `prefers-reduced-motion` | An accessibility setting that applies the reduced-motion column of 3.15 |
| Title, cards, drawer | CommonUI: one activatable widget per screen on a stack (`WBP_Title`, `WBP_Card_Pause`, `WBP_Card_Death`, `WBP_Card_Debrief`, `WBP_SettingsDrawer`), Common Button styles for the three button kinds, a Common Tab List for the two tabs |
| Location card | `WBP_LocationCard` shown by the flow during the first intro; the wipe is a clipping animation in 28 steps over 1.1 s |
| Boot screen | The loading screen: same layout, the route-line bar driven by level-load progress |
| `text.js`, `copy.js` | A string table (or the exported JSON, 4.8) keyed like the web files; no player-facing string typed into a widget |
| Device-dependent key names (`E`, `X`, `USE`) | CommonInput's active input type plus the Enhanced Input mapping of the action; show a key cap for keyboards and the platform's button glyph for gamepads |

### 4.3 HUD mechanics

| Mechanic | Web | Unreal feature and values |
|---|---|---|
| HUD visibility | `hud.show(on)`, 0.35 s fade | Flow state change → play a 0.35 s opacity animation; collapse when hidden |
| Objective typewriter | 46 characters / s | A timer in the badge widget revealing `floor(t · 46)` characters; the 0.9 s flash as a widget animation |
| Reel bullets | DOM bullets, filled when secured | Three small widgets with a ring material (line colour border, `bg` fill) and a filled state |
| Minimap plan | 2D canvas painted from colliders and ground surfaces | A plan texture, either baked offline from the exported level data or drawn once at level start into a canvas render target with the rules of 3.3. 8 px per metre gives 1120 × 928 px. Because X is east and Y is south, U follows X and V follows Y with no flip: u = (X + 7000) / 14000, v = (Y + 5800) / 11600 |
| Minimap turn | Canvas rotated by the yaw | A UI material on a 150 × 150 image: sample the plan around the player's UV, rotated so the camera's forward is up (rotation = −(ψ + 90°) clockwise), covering 6000 cm; rounded-corner mask of radius 14. Update at 30 Hz (a Retainer Box, or only pushing the material parameters every other frame) |
| Minimap marks | Canvas discs and text | Child widgets positioned with the 4.1 formula; enemy pips from a pool; pin to the square rim |
| Zone band | `level.zoneName` | The rectangles of 4.1, or trigger volumes named after the zones |
| Weapon bar | DOM buttons | Widgets fed by weapon events (ammo changed, weapon changed, cue changed). Silhouettes as textures (5.1). The pip row: a horizontal box of thin images, or a tiling material with a "spent" parameter |
| Crosshair gap | Formula 3.6 | Same formula in Slate units: use the viewport height in Slate units (pixels / DPI scale) and the vertical field of view; the four ticks are images moved by render translation with a 60 ms interpolation |
| Hit marker, damage arcs | Formulas 3.7, 3.8 | One widget each, rotated and faded by code. The arc is a texture or a material drawing a 48° ring segment at 88 % radius |
| Health bar | Scale transforms | A progress material with fill, ghost and a ten-segment mask; logic as 3.9 |
| Prompt ring | SVG stroke dash | A radial-progress material (start at 12 o'clock, clockwise) |
| Kill feed | Rebuilt list | A vertical box with a pool of four entry widgets |
| Banner, message | Per-frame opacity and stretch | Code-driven opacity and X scale of the text block (3.12); the message is a simple fade |
| Radio subtitles | Typewriter over a per-line plate | A text block revealed by character count; the per-line strip needs a rich-text decorator or a custom Slate text highlighter, or accept one plate behind the whole block. Also feed the engine's subtitle / accessibility path |
| World markers | NDC projection and clamp | Screen-space widgets in `WBP_MarkerLayer`; project with the player controller or the 4.1 vectors; apply 3.13. Not world-space widget components: the pins must clamp to the screen edge |
| Pin separation | Reads the HUD blocks' boxes | Cache the geometry of the blocks named in 3.13 when the layout changes and run the same search |
| HUD buttons (pause, gear, slots) | Clickable while the mouse is free or on touch | Only relevant with a visible cursor or on touch; on gamepad and captured mouse they are indicators |
| Stub HUD | A debug text block | Useful as a first milestone: state, health, ammo, objective, markers with distances, last banner / message / radio line, prompt with a progress bar, a centre dot that flashes on hits (`src/stubs/hud.js`) |

### 4.4 Menus and settings

| Mechanic | Web | Unreal feature and values |
|---|---|---|
| Title backdrop | Fly-through camera, veil gradient, letterbox bars | A camera rail or sequence (flow spec); the veil and bars are widgets; bars 52 units high at 1080, sliding in 0.7 s |
| Focus and navigation | DOM focus, `menuNav` | CommonUI input routing and UMG navigation. Explicit navigation rules to reproduce 3.17: wrap up / down in the scope; left / right inside segmented controls without wrap; left / right on sliders nudge by the gamepad step; left / right on tabs switch tabs |
| Analog repeat | Stick threshold 0.6, first repeat 0.38 s, then 0.17 s | A custom navigation config with those three values |
| Accept / back / start | A, B, Start | CommonUI default click and back actions; a bound "start" action per screen (3.17) |
| Focus ring | 2 px gold outline, offset 3 | A focused style on the button styles; shown for gamepad and keyboard, hidden while the mouse drives |
| Hover and click sounds | `ui:hover`, `ui:click` events | Hovered and pressed sounds on the Common Button styles (`ui_hover`, `ui_click`); also on focus moves from the gamepad |
| Pause | `game.pause()`; HUD off; card | Set the game paused; the pause card and the drawer must tick while paused; resume debounce 0.35 s |
| Death and debrief timing | Card after 1.5 s / 3.3 s | Flow timers; cards fade in 0.45 s over a veil fading in 0.5 s |
| Settings storage | `localStorage` JSON | A save-game object with the same nine keys and the best holdout score |
| `quality` | Renderer presets, Auto | Game User Settings scalability levels (Low, Medium, High, Epic for low … ultra); Auto = run the hardware benchmark and apply; show the picked tier as "implied" |
| `fov` | Vertical degrees | Camera spec; keep the slider in vertical degrees or relabel and convert |
| `volume` | Last gain of the master chain | Volume of the master Sound Class (or a master control bus), 0…1, applied with a 30 ms ramp |
| `sens`, `invertY` | Input | Enhanced Input modifiers on the look action |
| `difficulty`, `mode`, `time`, `view` | Flow, atmosphere, viewmodel | Their specs; the pickers only write the setting |
| Fullscreen row | Browser fullscreen | Window mode (windowed / borderless / fullscreen) and resolution from Game User Settings |
| Stub menus | Four bare cards | A first milestone: title with start, mode and difficulty; pause with resume and restart; death and debrief with their stats (`src/stubs/menus.js`) |

### 4.5 Audio assets and routing

| Web bus | Sound Class | Volume | Submix | Notes |
|---|---|---|---|---|
| `gun` | `SCL_Gun` | 1.00 (0 dB) | `SMX_SFX`, street / shop reverb send 0.10 | 2D. A passive sound mix on this class ducks ambience and music (4.6) |
| `tail` | `SCL_Tail` | 0.85 (−1.4 dB) | `SMX_SFX`, no reverb send | 2D |
| `near` | `SCL_Near` | 0.95 (−0.4 dB) | `SMX_SFX`, reverb send 0.14 | 2D |
| `world` | `SCL_World` | 1.05 (+0.4 dB) | `SMX_SFX`, reverb send 0.5 | 3D, attenuation assets of 2.11 |
| `amb` | `SCL_Ambience` | 0.70 (−3.1 dB) | `SMX_Ambience` → `SMX_SFX` | Beds and wind 2D; far one-shots 3D |
| `dry` | `SCL_UI` | 0.95 (−0.4 dB) | `SMX_UI` → master | 2D, flagged as UI sound: plays while paused, never muffled |
| `music` | `SCL_Music` | 0.45 (−6.9 dB: bus 0.5 × trim 0.9) | `SMX_Music` → master | 2D, keeps playing while paused |

- `SMX_SFX` carries the **muffle** low-pass (20 kHz … 600 Hz) and feeds the master. The two reverb returns
  (`SMX_Reverb_Street`, `SMX_Reverb_Shop`) feed `SMX_SFX` too, so they are muffled with the rest.
- Master submix: a dynamics processor (threshold −6 dB, ratio 2.5, knee 8 dB, attack 6 ms, release 140 ms, output
  gain +1.2 dB) followed by a soft clipper or limiter with its knee at −4.4 dB (0.6).
- Import every WAV as a Sound Wave named `SW_<name>_<nn>`. A sound with variants becomes a Sound Cue (Random node
  without replacement, a Modulator for pitch and volume) or a MetaSound source doing the same; loops are single
  looping waves.

### 4.6 Audio mechanics

| Mechanic | Web | Unreal feature and values |
|---|---|---|
| Variants | Rotation with a 30 % skip | Random without replacement over the variants |
| Pitch and level variation | Rate × (1 ± jitter); gain × (0.92…1) | Modulator: pitch min / max = 1 ∓ jitter (2.12; default 0.965…1.035), volume 0.92…1. Event pitch and volume multiply on top |
| Voice limits | Channel pools per bus; per-name `max`; priority | Sound Concurrency: one asset per bus with the pool size (world 26, near 12, gun 6, tail 8, ambience 8, UI 10) resolving by lowest priority then oldest, and per-sound limits (`max`) with "stop oldest". Sound priority = the P column |
| Minimum gap | `gap` per name; 22 ms across all impacts | The concurrency retrigger time per sound; one shared concurrency group with a 22 ms retrigger for the impacts |
| Distance | Inverse model | Sound Attenuation assets with a custom curve sampled from `ref / (ref + roll · (d − ref))`: inner radius = ref × 100 cm, curve out to 16 000 cm. About twenty pairs (2.11); merge close ones if wanted |
| Air absorption | Low-pass by distance | The attenuation's air absorption with a custom curve: 20 kHz at 0, 16.2 kHz at 1000 cm, 11.9 kHz at 2500 cm, 7.1 kHz at 5000 cm, 4.2 kHz at 7500 cm, 2.5 kHz at 10 000 cm, 1.6 kHz from 12 100 cm |
| Panning | Equal power, no HRTF | Default panning spatialisation |
| Cull | Not started beyond 160 m | Attenuation max distance 16 000 cm with virtualisation off for one-shots |
| Street reverb | Convolver, 1.4 s synthetic response, return 0.8 | A convolution reverb submix effect with `IR_street.wav` (5.3), or an algorithmic outdoor preset tuned to it (early slaps 21–190 ms, about 1.4 s, dark tail). Match the wet level by measurement: about 5–6 dB under the dry sound at a send of 1 |
| Shop reverb and interior | Interior factor from the shop box | An Audio Volume on the shop interior (4.1) with the shop reverb (`IR_shop.wav`, 0.8 s, bright, dense early reflections), interior fade about 0.33 s, and ambient-zone settings: exterior sounds at 0.45 behind a 1.6 kHz low-pass. Outside it, the street reverb is the default. Feed the same 0…1 interior value to the gun tails |
| Gun tails | Equal-power pair, burst logic | A MetaSound per gun with the shot and both tails and an `Interior` input, or three components driven by the weapon code with the rule of 3.20 |
| Muffle | Low-pass on effects and ambience | A low-pass on `SMX_SFX` (submix effect or a modulation control bus on the classes): cut-off 20000 · 0.03^m Hz, Q 0.6; `m` handled in code as 3.19 |
| Ducking by gunfire and blasts | Timed ducks | Passive sound mixes (or a control-bus mix pushed from code): `SCL_Gun` playing → ambience and music to 0.45 (pistol 0.55), attack about 10 ms, hold 85 ms, release about 0.1 s; enemy fire → ambience to 0.85; blasts → ambience and music to 0.4 for 0.4 s, release 0.45 s (small: 0.6, 0.15 s, 0.2 s), plus the music dip to 0.3 / 0.45 recovering at 3.5 per second |
| Pause | Effects and ambience silent, music thinned | Pausing the game pauses non-UI sounds; push a "pause" mix on `SCL_Music`: volume 0.45, low-pass 1.3 kHz, 0.2 s |
| Ambience state | × 0.6 / 1 / 0.7 / 0.8 | A control-bus value or sound-mix per flow state, 0.4–0.6 s ramps |
| Rotor, heartbeat, grab, hiss loops | Loop handles with volume and rate | Audio components with pitch and volume set from code (3.22); the rotor component attached to the Buzzard |
| Six nearest rotors | Ranked every 0.25 s | A concurrency group of 6 resolving by "stop farthest", or the same ranking in code |
| Neon, steam | Three nearest inside a radius | Ambient sound actors on the lamps and vents with the attenuations of 2.11 and a concurrency of 3 ("stop farthest"); neon volume × 0.5 by day |
| Train | Two loops sliding along the train, a squeal, a duck | An audio component whose position is the point of the train nearest the listener, playing both loops; volumes by phase (3.23); a mix for the duck |
| Far one-shots | Timers and random placement | An ambience manager with the schedule of 2.14, spawning sounds at offsets from the listener |
| Near miss | Geometry test at the shot | The same test in the enemy fire code; spawn `whizz` at the closest point with the delay |
| Day and night beds | Crossfade by the day mix | Two looping 2D components on `SCL_Ambience`, crossfaded when the time of day is applied |
| Listener | The camera | The default listener (camera) |

### 4.7 Music

| Mechanic | Web | Unreal feature and values |
|---|---|---|
| Seven phase-locked stems | Looping buffers on one clock | One MetaSound source with seven looping wave players started by the same trigger (sample-locked), a gain and a pan per stem, and the shared drum low-pass (Q 0.8) on drums and hats. Inputs: seven gains, the cut-off, the stem-bus gain |
| Layer gains | `layerGains(I, mode, gate)`, τ 0.5 s | Compute the row of 2.13 in code from `I` (formula 3.24) and interpolate the MetaSound inputs with the same time constants |
| Intensity | Game target, combat meter, easing, tiers | A music director object (subsystem or actor component) holding target, meter, `I`, tier, mode, gate, exactly as 3.24; it listens to the same gameplay events as 2.15 |
| Beat and bar grid | `nextGrid(t0, now, lead, step)` | A Quartz clock at 92 BPM, 4/4, started with the stems. Stings: play quantised to the next beat. Impact: quantised to a bar line at least 1.4 s (2.6 s) ahead; the riser starts two bars earlier, or immediately from an offset |
| Stem-bus ducks and gate | Scheduled gain ramps | The stem-bus input of the MetaSound, ramped by the director: 0.4 for 3.4 s, 0.12 for 7 s, the pre-impact dip to 0.5; strings and bell held at 0 until the impact |
| Stings, riser, impact | One-shots beside the stems | Separate 2D sounds on `SCL_Music` (not through the stem bus) |
| Boombox in phase | Loop started at the score's phase | Start the boombox components on the same Quartz bar as the stems and keep them running (volume 0 once their reel is taken), or start them with a start time equal to the clock's position in the eight bars |
| While paused | Music at 45 %, low-passed | `SCL_Music` flagged to play while paused, plus the pause mix |

### 4.8 Data: what is already exported and what is missing

The level exporter already writes most of what this subsystem reads, under `unreal/MurderInc/Content/Data/`:

| File | Keys this subsystem uses |
|---|---|
| `text.json` | `text` (the copy deck of `src/config/text.js`: objectives, banners, radio, cards, ratings, zones, boot lines), `interface` (`src/ui/copy.js`: HUD words, cue lines, settings labels, controls tables), `input.glyphs` and `input.hints`, `brand` (title, presenter and star lines, the IPX marks). Parametrised lines are stored as templates |
| `config.json` | `brand.colors`, `brand.fonts`, `brand.lines`; `settings.defaults`; `flow.music`, `flow.pacing`, `flow.timing`, `flow.interact`, `flow.rating`; `player.input.pad.nav` |
| `level.json` | Minimap: `colliders.boxes` (box, tag, owner, `flags.playerOnly` / `bulletOnly`, in web and Unreal units), `bounds`, `ground.surfaces`, `el.layout` (tracks). Zone band: `places.regions` (the named rectangles of 3.4). Markers: `objectives`, `extraction`. Audio: `interior` (boxes and fade), `steam.vents`, `el`, `train` |
| `atmos.json` | `lamps.list` filtered by `kind: "neon"` (19 lamps) for the neon emitters |

Not exported anywhere yet (nothing in those files mentions audio):

- The sound definitions of 2.12 (bus, variants, rate, measured length, peak, volume, jitter, priority, max voices,
  gap, reference distance, roll-off, loop and stereo flags, pan): a suggested `audio.json`, written by the same
  script that renders the WAV files (5.3).
- The event table of 2.15, the ambience schedule of 2.14, the mixer constants of 2.11 and the music tables of 2.13.
  They are small: carry them in `audio.json` too, or type them into the Unreal data assets from this spec.
- The ten map inks of 2.7 and the derived opacities of 2.2 (they live in `src/ui/minimap.js` and `src/ui.css`, not
  in the brand file).

---------------------------------------------------------------------------------------------------

## 5. Art and audio implications

### 5.1 Interface art

The web game has **no** image files: every plate is a flat colour and every pictogram is vector path data
(`src/ui/glyphs.js`, `src/config/player.js:334-366`), which can be written out as SVG files verbatim. The flat
transit-sign identity is deliberate and stays flat in the rebuild: the photoreal target is the world, not the HUD.

Reference pictures of every screen can be regenerated at any time with the existing harness, for example
`node tools/shot.cjs dist/index.html --size 1920x1080 --params "autostart=1&q=low" --frames 60 --out <file>.png`
for the HUD at the start position and the same without `autostart=1` for the title (`docs/CONTRACT.md:46-64`). The
harness blocks the web fonts, so those pictures show the fallback faces; the measurements in this spec were taken
with Anton and Archivo loaded.

| Asset | Shown at (px at 1080) | Produce |
|---|---|---|
| IPX mark | 40 × 18 (badge, cards), 49 × 22 (title), about 52 × 23 (loading) | Typeset placeholder until the client's logo arrives: one widget, so it is swapped in one place. Only "IPX" and "IPX.EXCHANGE" may appear; no slogan (`src/config/brand.js:14-18`) |
| Route bullets 1, 2, 3, IPX | 22 px (HUD, markers), 15 px (minimap) | A circle material (ring and filled states, line colour parameter) plus a text block; or four textures at 128 px |
| CHOPPER silhouette | 62 × 30 in the slot, 13 px high in the feed | White on transparent, artboard 104 × 36, at 4× or more (416 × 144). Redraw it from the final weapon model (orthographic side view, muzzle right) so the icon matches what the player holds |
| NINE silhouette | 44 × 30, 13 px high | Same, artboard 60 × 36 (240 × 144) |
| Fist, pause, gear, arrow, close | 28, 20, 20, 22, 14 px | 128 px textures or the SVG shapes as they are |
| Record disc | 64 px (46 px on short screens) | 256 px, tinted `gold`; grooves and label cut-outs in `plate` |
| Damage arc | 778 px square, 48° segment 15.6 px thick at 342 px radius, chevron outside | A material (ring segment + chevron) or a 1024 px texture |
| Prompt ring, health bar, pip row | 48 px; 317 × 8; 146 × 3 | Materials (radial progress; fill + ghost + ten-segment mask; tiling pips) |
| Minimap plan | 150 × 150 window on a 140 × 116 m plan | 1120 × 928 texture at 8 px per metre in the ten inks of 2.7, baked from the final collision so it always agrees with what blocks the player |
| Touch glyphs (ten) | 32 × 32 artboards | Only if handhelds are a target |
| Fonts | — | Anton Regular; Archivo 400, 500, 600, 700, 800 and 800 italic (both are open-licensed Google Fonts families: confirm the licence files ship with the build) |
| Gamepad button glyphs | In prompts, key hints, the controls tab | The platform holder's glyph sets through CommonInput; the web shows letters in key caps |

### 5.2 Things in the world that this subsystem needs to exist

Every positioned sound should have something to come from. The art list must include:

| Source | Sound | Dimension notes |
|---|---|---|
| A boombox at every master-reel case | `boombox` (the score, band-limited, in phase) | The emitter sits 0.6 m above the reel's floor point; the prop is in the props spec (its front is about 0.58 × 0.23 m, `src/props/clutter.js:74`) |
| Neon signs with their transformers | `neon_buzz` within 15 m | One emitter per neon lamp of the level |
| Manhole and street steam vents | `steam` within 24 m | One emitter per vent |
| The El train | `train_rumble`, `train_clack`, `train_squeal` | Five cars of 15.4 m with 0.7 m gaps (79.8 m), 16.5 m/s. The clack rhythm assumes two trucks per car 10.4 m apart with axles 2.4 m apart (`src/audio/sfx-ambience.js:350-362`): model the trucks to match or re-time the loop |
| The El's steel deck and girders | `wind_el` rises within 25 m of the deck | Deck 10.8 m wide over the whole avenue, underside at 6.5 m |
| Propane tanks, welding racks | `hiss` while the fuse burns (1.6 s, 1.1 s), then `explosion_big` | A visible jet or valve for the hiss to belong to |
| Buzzard | `rotor` (four motors), `buzzard_charge`, `bolt_shot`, `buzzard_death` | Four rotors; the gun as the source of charge and bolt |
| Goon | `smg_shot`, `goon_ready`, `goon_rush`, `pipe_swing`, grunts, `body_fall`, steps | The SMG muzzle, a steel pipe that can drag on the ground |
| Shell casings | `brass_*` at every bounce | Ejected cases that bounce at least once |

Animation must emit the same moments the web emits as events, as notifies: the reload phases (`start`, `magout`,
`magin`, `bolt`, `done`), holster and draw, the melee swing and its hit, the Goon's and the Buzzard's telegraphs,
the rush wind-up and strike, footfalls of the player and of Goons, shell bounces, and the body reaching the ground
0.42 s after a Goon dies. The times are in the weapons and enemies specs.

### 5.3 Can every sound and every stem be rendered to WAV files? Yes

All synthesis is plain sample arithmetic in `src/audio/dsp.js`, the five `src/audio/sfx-*.js` files and
`src/audio/music.js`: no Web Audio node is involved until playback. The modules are ES modules with no browser dependency, so **Node renders
them directly; no OfflineAudioContext and no browser are needed for the assets themselves**.

Which functions produce the buffers:

| Function | File | Returns |
|---|---|---|
| `SOUNDS` | `src/audio/library.js:17` | The table of all 102 definitions: generator `gen`, variants `n`, rate `sr` (44.1 kHz when absent), `peak`, playback defaults |
| `renderVariant(name, variant)` | `src/audio/library.js:66-98` | A generator; its return value is `{name, variant, sr, channels: Float32Array[]}`. It seeds the sound's random stream from its name and variant (the same buffers on every machine), runs `gen`, removes any offset, normalises to `peak`, and gives one-shots a 1.5 ms fade-in and a fade-out of up to 20 ms |
| `renderNow(name, variant)` | `src/audio/library.js:101-106` | The same, run to the end synchronously: the one call a script needs |
| `variantsOf(name)`, `renderOrder()` | `src/audio/library.js:108`, `39-44` | Variant count; all names |
| `impulse(sr, secs, rnd, options)` | `src/audio/dsp.js:620-636` | One channel of a reverb impulse response; the two calls with their options are at `src/audio.js:248-249` (seeds 11 and 23, +31 for the right channel) |
| `createConductor(context, destination, getBuffer)` | `src/audio/conductor.js:57` | The music player on any audio context, also an offline one: only needed to bounce **mixed** music references |
| `audio.debug.renderMusic(I, bars, options)` | `src/audio.js:818-857` | In the running game: eight bars of the score at a fixed intensity through an `OfflineAudioContext` (stereo, 22.05 kHz); options solo a stem or return the samples |

What a render script looks like (a single Node file, about 60 lines with the WAV writer):

```
import { renderNow, renderOrder, variantsOf, SOUNDS } from 'src/audio/library.js'
import { impulse, seeded } from 'src/audio/dsp.js'
for name in renderOrder():
    for v in 0 … variantsOf(name) − 1:
        r = renderNow(name, v)                                  # {sr, channels}
        write a PCM WAV (24-bit, r.sr, r.channels.length channels) → <out>/<name>_<v + 1>.wav
for (file, secs, seed, options) in the two impulse responses:
    write a stereo WAV of [impulse(48000, secs, seeded(seed), options), impulse(48000, secs, seeded(seed + 31), options)]
write audio.json from SOUNDS and the measured lengths (4.8)
```

This was run as a scratch test for this spec (not committed): 188 WAV files and 2 impulse responses, 28.6 MB as
24-bit PCM, rendered and written in 2.2 s, no sample above full scale. The optional browser step was tested too:
the bundled modules loaded into headless Chromium, the stems rendered there and mixed by `createConductor` on an
`OfflineAudioContext`, at 22.05 kHz and at 48 kHz, giving the reference levels of 2.13. Use that step only to bounce
"what the web game plays at intensity 0.15 / 0.6 / 1.0" files for A/B listening against the Unreal music director.

Where the files should go is not fixed by the shared conventions; `art/out/audio/` (generated, git-ignored) as the
import source for `/Game/Audio/` is the obvious place.

### 5.4 What the WAV files do not contain

| Not in the files | Why | Rebuild it as |
|---|---|---|
| Bus gains, event volumes and pitches | Applied at play time | Sound Class volumes (4.5); the event rules of 2.15 in code or in the cues |
| Pitch jitter, the 0–8 % level variation, variant rotation | Per play | Modulator and Random nodes (4.6) |
| Distance attenuation, panning, air absorption | Per voice | Attenuation assets |
| Both reverbs, and the split of the gun tails by interior | Convolvers and the interior factor | The two impulse responses are exportable (5.3); the routing is 4.6 |
| Ducking, muffle, pause thinning, ambience state, train duck | Mixer state | 4.6 |
| Master compressor, make-up, soft clip, volume | Master chain | Master submix (4.5) |
| Stem layering, pans, drum low-pass, riser gate, sting timing | The conductor | The music director and MetaSound (4.7). The stems are mono: the pans of 2.12 are not baked |
| Voice limits, priorities, gaps | Mixer bookkeeping | Concurrency (4.6) |
| Schedules, emitter choice, trackers | Game-side logic | 3.22, 3.23 |

What **is** preserved: loudness relations (every file sits at its `peak`), the baked tails (gun tails, the SMG's own
slap, explosion and sting reverbs), and seamless loops. Loops are built to wrap sample-exactly (stems fold their
reverb tail back onto the start; beds and noise loops are cross-faded), so they must be imported whole and looped
whole; keep the short loops (`rotor` 1.0 s, `train_clack` 0.988 s, `heartbeat` 0.86 s, `reel_grab` 0.6 s,
`neon_buzz` 1.0 s) uncompressed or check their seams after compression.

Fidelity: the files carry the web game's deliberately economical rates. Music, ambience and voices are 22.05 kHz
(nothing above 11 kHz), the bass, the crackle and the boombox 11.025 kHz, the explosions 32 kHz, everything else
44.1 kHz. The synthesis takes its rate as a parameter, so a 48 kHz render is a one-line change per definition and
was tested: every sound renders, every length is unchanged, but the result is not bit-identical (noise layers gain
top end; at equal peak the RMS of five sounds moves by more than 1.5 dB, the most being `stem_crackle` at −5.7 dB).
Render at the native rates for parity; treat a 48 kHz render as a new master that needs a listening pass.

### 5.5 Sound for a photoreal game

The rendered files are exact references for timing, loudness, variation count and behaviour, but they are
synthesised: wordless formant voices, noise-and-sine gunshots, a 22 kHz score. Next to photoreal pictures they will
read as placeholders. Recommended path:

1. **Parity pass**: ship the rendered WAVs through the Unreal mix of section 4 and match the web game by ear and by
   the levels of 2.12 and 2.13. This proves the event wiring, the mixer and the music director.
2. **Replacement pass**, category by category, at 48 kHz, keeping each name, its role, its length within about
   20 %, its peak target, at least as many variants, and the same triggers:

| Priority | Category | Replace with | Constraints |
|---|---|---|---|
| 1 | Guns: 2 shots × 4, 4 tails | Recorded or library carbine and 9 mm pistol; separate close shot and tail layers; a street tail (slap echoes off facades, about 1.3–1.7 s) and a garage tail (dense, about 0.8–0.95 s) per gun | Shot without tail 0.26–0.36 s; the tail pair must crossfade cleanly |
| 2 | Impacts × 9 surfaces, footsteps × 5 surfaces × walk / run, brass | Foley per final material: asphalt, concrete, brick, metal, sheet metal, glass, wood, dirt, cloth / body, drone shell | 2–4 variants each, 0.24–0.5 s |
| 3 | Explosions, fuse hiss | Recorded or designed gas blasts with a long street tail | 2.1 s and 3.4 s; two variants |
| 4 | Goon voice: hit, death, alert, rush | An actor's wordless efforts and shouts through a mask | No words, nothing stronger than the tone rules of `docs/DESIGN.md:30` |
| 5 | Buzzard: rotor, charge, bolt, death | Designed drone; the 1 s rotor loop must stay seamless and pitch well between 0.9 and 1.3 | The charge is pitched to the telegraph (0.38–0.55 s) |
| 6 | The El train, beds, far one-shots | Field recordings of an elevated line and of a Queens afternoon and night; the beds are stereo loops of 12 s or longer | No recognisable music, voices, brands or jingles (`docs/DESIGN.md:27-28`); the chime must stay an original tune |
| 7 | Reload foley, cloth, holster, melee | Foley to the final weapon animations | Cut to the reload notifies |
| 8 | UI ticks, hit and kill confirms, radio squelch, reel sounds | Keep the designed character; re-render or re-make at 48 kHz | Confirms must stay short (0.1–0.34 s) and dry |
| 9 | The score | Keep the composition (it is original and written for this game: `docs/DESIGN.md:259-262`); re-produce the seven stems, riser, impact and four stings with better instruments, or re-render at 48 kHz | Stems exactly eight bars at 92 BPM (20.869565 s), tails folded so they loop seamlessly, same layer roles; stings and riser at the lengths of 2.12; the boombox version derived from the new stems |
| — | Radio voice | The web game has no voice-over. Nine short lines for one speaker (2.8) would be new work | A production decision (section 6) |

---------------------------------------------------------------------------------------------------

## 6. Open questions and risks

Open questions:

1. **Radio voice-over.** The web game shows the IPX VAULT lines as typed subtitles with squelch sounds only. Should
   the rebuild record the nine lines? If yes, line lengths replace the `characters / 58 + hold` timing.
2. **Audio fidelity target.** Ship the rendered WAVs as they are (parity), re-render at 48 kHz, or replace by
   recordings (5.5)? This decides the audio budget and schedule; nothing in the source answers it.
3. **HUD scale policy.** The web HUD is fixed-size pixels (it shrinks relative to a bigger window). The mapping
   proposes scaling with the shortest screen side from a 1080 reference. Confirm, and whether a HUD-scale setting is
   wanted.
4. **Platforms.** Are touch devices and narrow screens targets? If not, the breakpoints of 3.15, the touch glyphs
   and the clickable HUD buttons can be dropped.
5. **Field of view.** The web setting is vertical degrees (74). Which convention does the camera spec use, and does
   the settings slider keep vertical numbers?
6. **Real IPX identity.** The mark is typeset and the palette is a stand-in "so the real IPX colours, fonts and
   logo can be dropped in later" (`docs/DESIGN.md:243-246`). When do the real assets arrive?
7. **Quirks of 3.25.** Reproduce or fix: the `radio_out` timing, the hit grunt on a killing shot, identical Goon
   voices, the dead head-hit pitch on body impacts, the 6-second rule of the `complete` sting.
8. **Where audio lives.** The shared conventions name no folder or prefix for sounds, fonts or widgets; this spec
   proposes `art/out/audio/` as the WAV source and the prefixes of section 4.
9. **Not found in the source**: any loudness target (LUFS) for the mix; any subtitle or colour-blind options; any
   per-category volume sliders (there is one master volume only).

Risks:

- **The mix will not match by numbers alone.** The browser's compressor, its convolver normalisation and its
  inverse distance model have no exact Unreal twins. Budget a calibration pass with A/B files (5.3); the measured
  figures in 2.11 and 2.13 are the anchors.
- **Phase lock.** The score depends on seven stems, the stings and the in-world boombox sharing one clock. Start
  them from one MetaSound trigger and one Quartz clock; never restart a single stem. At 22.05 kHz the loop is
  460 174 samples, 3.9 µs longer than eight exact bars, so a free-running beat grid drifts 0.7 ms per hour:
  harmless, but re-derive the grid from the playing loop if a session can last days.
- **Loop seams after compression** for the sub-second loops (5.4).
- **Text metrics.** The boxes marked ≈ depend on the text shown: lay out by the rules (padding, type size,
  tracking), not by those widths. Slate tracking and line height differ slightly from CSS, so expect small shifts.
- **Minimap truth.** The web plan is drawn from the same boxes that block the player. A hand-painted or
  mesh-rendered plan can drift from the collision; bake it from the collision export.
- **Marker clamp.** World-space widget components cannot pin to the screen edge or dodge HUD blocks; the markers
  must be screen-space widgets with the logic of 3.13.
- **Pause.** The web keeps the radio line and the kill feed frozen behind the pause card and refuses new world
  sounds; Unreal pauses running sounds instead. Check that stings, the heartbeat and loops resume cleanly.
- **Synthetic sound against photoreal pictures** (5.5): the largest perceived-quality risk in this subsystem.
