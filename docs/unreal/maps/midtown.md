# Level 3: Midtown rooftops / the Square (design)

Level 3 of the three-level story: **MIDTOWN**, at night. The fight starts on the roofs above a bright square, among water
towers and the steel behind giant screens. Rule works his way down the roofs, then down a scaffold stair to the street, and
the run ends with a fight across the square to the IPX truck. This document is the level designer's spec: footprint,
plan and sections, traversal, the movement rules as they apply to height, the story beats, the objectives and extraction,
the enemies, the explosives, the guidance route, the lighting, the assets, the budgets for E3DS, the level data and the
engine changes the level needs.

Status: design only. Nothing is built. The engine changes in section 17 come before any art, because the current nav is
one ground layer and cannot route Goons on the roofs. The level ships in the NEXT release (the three-map story,
DECISIONS.md 2026-11-25 ~21:40), after the guns-and-fixes release. It must meet the same bar: 60 fps on E3DS, story
guidance (objective line, hints, marker, ground path), clean menus, enemy deaths, weapons and attachments. The staged build
plan and its lanes are in [../MAPS.md](../MAPS.md).

**Revision 2 (lead review, 2026-11-25).** The two design reviews found three must-fix problems in this level, and this
revision resolves them with the should-fix items worth doing:

- **Any reel order.** The rules let the player take the reels in any order, so nothing here depends on the count any
  more: the radio's reel lines name no place, the gantry screen dies when *its* reel (reel8) is secured, the IPX
  takeover comes when all three are in, and the guide draws the way to the nearest unsecured reel over a route graph
  of the layers and links, not a fixed list of legs. An out-of-order Story run is a test (6.2, 6.4, 12.2, 19).
- **No safe reel rooms.** Every Goon doorway is 2.0 m wide (the tank house, the booth, the service stair, the
  bulkheads). The tank house and the booth are too low for Buzzards (clear height under 3.5 m), so they are left out
  of the Buzzards' doorway list on purpose, and the booth's front window is a shoot-through slot only, not a way in.
  A check proves every reel room has a Goon path (2.3, 6.2, 9.1, 19).
- **Multi-layer nav in two steps.** Step A (per-layer grids, spawn reach, firing cells, the stranded rule, no links)
  already makes the roofs a ground fight; step B (Goons walking the stair links) follows. The level data works with
  either, and the grey box is played with both (7.2, 17).
- **Reels 7 to 9**, one album with the Block (1 to 3) and Canal (4 to 6). The HUD says "reels", the radio
  "masters" (6.2, 16.4).
- **The truck rolls in.** It is not on the map until the last reel is secured, then it pulls up on W 46 St east of
  the square, so the finale runs down Broadway over new ground instead of back over the plaza, and there is no
  refusal on the way to the booth (6.3).
- **Harder than Canal:** one more Buzzard per wave on boss and kingpin, pursuit +2, through the level's `tuning` (7.1).
- **Readability and the midnight square:** the takeover screen is white on black with a small oxblood mark, the
  palette is cool white, and the square is dressed with what a crowd leaves behind (12).
- Smaller fixes: the clock starts at 11:52 PM so the countdown means something; Broadway runs southbound; `el` is
  absent (no degenerate deck); audio lives in `audio_midtown.json`; the sky dome is hidden while the front-end stage
  shows.

Units are the level data's web units throughout: metres, +Y up, x east, z south (north = -z), yaw 0 looks at -z and
positive yaw turns left. Unreal = (x, z, y) x 100 cm. A facing (fx, fz) is yaw = atan2(-fx, -fz), and an objective's
`rotationY` r has forward (cos r, 0, -sin r), as in level.json.

---

## 1. The level in one page

| | |
|---|---|
| Name (card) | Midtown |
| Place line | Midtown, Manhattan · Seventh Av · 11:52 PM |
| Time | Night only (`times: ["night"]`); a per-level night rig, section 11 |
| Footprint (play bounds) | x -50 .. 31, z -38 .. 37 (81 x 75 m; the Block is 92 x 68) |
| Walk levels | Street 0 (sidewalk and plaza 0.15), roof R1 14.0, roof R2 17.6, roof R3 21.2 |
| Objectives | 3 reels, in any order: Reel 7, The Tank (R2); Reel 8, The Gantry (R1, behind the big LED wall); Reel 9, The Booth (street, under the Stand) |
| Extraction | The IPX truck rolls in on W 46 St, east end, once the last reel is secured (code IPX, radius 2.5) |
| Route length | About 265 m walked in the intended order, 21 m of height lost; target run 5.5 to 7 min (the Block: about 5) |
| Enemies | Goons and Buzzards only; pools stay 12 / 8; the global difficulty tables plus this level's `tuning`: +1 Buzzard per wave on boss and kingpin, pursuit budget +2 |
| Spawns | 30 ground (each tagged with a walk level), 18 air |
| Explosives | 17 (propane and welding racks, the two kinds that exist) |
| Colliders | target 760, cap 820 (the Block: 777) |
| Modes | Story ("mission"); Hold the Square (holdout) offered on the street level, if the lead keeps holdout per level |

Story beat (the reader's proposal, for the owner to confirm): the Vultures' buyer means to premiere the stolen album on the
square's big screens at midnight. The last three masters are up on the roofs and down in the booth that runs the
premiere. Reel 8 sits in the control cabinet of the big LED wall; securing it kills that screen. Reel 9 is in the booth.
When the last of the three is in, whichever it is, the screens turn to IPX and the truck rolls up on Forty-Sixth.
Then Rule runs the square to it.

---

## 2. Footprint and walk levels

### 2.1 Buildings in play (the west block, art fitted to these boxes)

| Id | Name on the art | Mass collider (x, z) | Roof top y | Storeys (art) | Role |
|---|---|---|---|---|---|
| A | HALVORSEN BUILDING | x -50..-30, z -38..-12 | 21.2 (R3) | ground 4.7 + 5 x 3.30 | Start roof, water tower WT-A |
| B | (no name, back building) | x -50..-30, z -12..8 | 17.6 (R2) | ground 4.7 + 4 x 3.225 | Flank roof: machine room, WT-B, bulkhead B (where waves come up) |
| E | (back building) | x -50..-30, z 8..22 | 14.0 (R1) | ground 4.7 + 3 x 3.10 | Flank roof: the pipe bridge to D |
| C | CORVIN HALL | x -28..-8, z -38..-4 | 17.6 (R2) | ground 4.7 + 4 x 3.225 | The tank house and WT-C (Reel 7), the roof billboard on its east edge |
| D | (taller lower floors, the setback) | x -28..-8, z -4..22, minus the stair shaft x -13..-8, z 4..10 | 14.0 (R1) | ground 4.7 + 3 x 3.10 | Roof lounge THE LOFTLARK (closed), service stair, doors to the gantry |
| Light court | (void between the columns) | x -30..-28, z -38..22, filled to y 10.4 | 10.4 | | Never walkable; guarded on both sides |

The roof surface is the top of the mass collider. Parapets are 0.30 m thick and 1.10 m tall on every roof edge, broken only
at the openings listed in section 5.3. The mass colliders' storey tables go to the facade kit (section 14).

### 2.2 The street (y 0, slabs 0.15)

| Strip | x | z | y | Notes |
|---|---|---|---|---|
| West sidewalk | -8..-4 | -38..22 | 0.15 | Under the gantry (z -2..14) and the scaffold tower (z 14..20) |
| SEVENTH AV roadway (southbound) | -4..8 | -38..24.5 | 0 | Closed for the premiere: concrete barriers, 5 parked cars, the production truck (x 1..3.5, z -37..-29, nose north) |
| The plaza | 8..22 | -38..22 | 0.15 | Granite pavers, 14 planters, kiosks (x 15..18 at z -19.5..-17.5 and z 5..7), two food carts, café tables; THE STAND at the north end |
| BROADWAY roadway (southbound, as the real one; Seventh Av runs southbound too) | 22..28 | -38..24.5 | 0 | A stalled city bus (x 22.5..25.3, z -6..6, facing south), 3 parked cars, water barriers; the finale's lane (6.3) |
| East sidewalk | 28..30 | -38..22 | 0.15 | Theatre and hotel doors (spawns); facade colliders x 30..31, 30 m tall |
| W 46 ST north sidewalk | -50..31 | 22..24.5 | 0.15 | |
| W 46 ST roadway | -50..31 | 24.5..33.5 | 0 | Empty until the last reel; then the IPX truck stops at x 16..24 (centre 20.0, 29.0) |
| W 46 ST south sidewalk | -50..31 | 33.5..36 | 0.15 | South facade colliders z 36..37 |

The square continues north past z -38 and east past x 30 as art only (the bow-tie, the towers and their screens), closed
to play by a parked production truck, concrete barriers and a playerOnly fence at the bound.

### 2.3 The Stand and the Booth

THE STAND is an invented tiered viewing stand (grey steel, warm-lit amber riser glass; not a copy of any real structure),
x 10..22, z -34..-22, facing south. 8 tiers, each 1.5 m deep and 0.40 m higher than the last (tops 0.55 to 3.35): the
player can walk up it (0.40 is under the 0.42 step), so it is a vantage over the square. THE BOOTH is a room inside the
Stand under tiers 6 to 8: interior x 10.6..21.4, z -34..-29.5, floor 0.15, ceiling 2.25 to 3.05 (the tier slabs are 0.30
thick). Doors **2.0 m** wide in both side walls at z -33.0..-31.0, so Goons come in from both sides: the booth is the
hardest room of the campaign, not a safe one. The front wall (z -29.5) has a sill to 1.0 and a head from 2.0: the 1.0 to
2.0 band is a broken window, a **shoot-through slot only**. A playerOnly frame box fills it, so shots and sight pass but
nobody walks or jumps through (the player capsule is 1.8 m tall standing and 1.15 m crouched; the slot is 1.0 m). Goons
outside fire in through it, and Buzzards over the plaza fire in through it. The booth is too low for Buzzards (clear
height 2.25 to 3.05 m, under minHeight 2.2 plus ceilingClearance 1.3), so it has no Buzzard doorway on purpose (9.1).

---

## 3. Top-down plan

2 m per cell, north up. x along the top, z down the left (each row label is the row's north edge).

```
x:   -50       -40       -30       -20       -10       0         10        20        30        
 -38 hhhhhhhhhhhhhhhhhhhh~~mmmmmmmmmmmmmmmmmmmm::::............::::::::::::::......::##
 -36 hhhhhhPPhhhhhhhhhhhh~~mmmmmmTTTTTTmmmm||||::::............::::::::::::::......::##
 -34 hhhhhhhhhhhhhhhhhhhh~~mmmmmmTT77TTmmmm||||::::............::bbbbbb99bbbb......::##
 -32 hhhhhhhhhhhhhhhhxxhh~~mmmmmmTTTTTTmmmm||||::::............::bbbbbbbbbbbb......::##
 -30 hhhhhhhhhhhhhhhhhhhh~~mmmmmmmmmmmmmmmm||||::::............::^^^^^^^^^^^^......::##
 -28 hhhhhhhhhhhhhhhhhhhh~~mmmmmmmmmmmmmmmm||||::::......xx....::^^^^^^^^^^^^......::##
 -26 hhhhhhhhhhhhTThhhhhh~~mmmmmmmmmmmmmmmm||||::::............::^^^^^^^^^^^^......::##
 -24 hhhhhhhhhhhhhhhhhhhh~~mmmmmmmmmmmmmmxx||||::::............::^^^^^^^^^^^^......::##
 -22 hhhhhhhhhhhhhhhhhhhh==ssssmmmmmmmmmmmm||||::::............::::::::::::xx......::##
 -20 hhhhhhhhhhhhhhhhhhhh~~mmmmmmmmmmmmmmmmmmmm::::............::::::::::::::......::##
 -18 hhhhhhhhhhhhxxhhhhhh~~mmmmmmxxmmmmmmmmmmmm::::............::::::::::::::......::##
 -16 hhhhhhhhhhhhhhhhhhhh~~mmmmmmmmmmmmmmmmmmmm::::............::::::::::::::......::##
 -14 hhhhhhhhhhhhhhhhhhhh~~mmmmmmmmmmmmmmmmmmmm::::............::::::::::::::......::##
 -12 mmmmmmssmmmmmmmmxxmm~~mmmmmmmmmmmmmmmmmmmm::::............::::::::::xx::......::##
 -10 mmmmmmssmmmmmmmmmmmm==mmmmmmmmmmmmmmmmmmmm::::............::::::::::::::......::##
  -8 mmmmmmmmmmmmmmmmmmmm~~mmmmmmmmmmmmmmmmmmmm::::............::::::::::::::..xx..::##
  -6 mmmmTTmmmmmmmmmmmmmm~~mmmmmmmmmmmmmmmmmmmm::::............::::::::::::::......::##
  -4 mmmmmmmmmmmmmmmmmmmm~~llllllllllllssllllll::::............::::::::::::::......::##
  -2 mmmmmmmmmmmmmmmmmmmm~~llllllllllllssllllllgg88............::::::::::::::......::##
   0 mmmmmmmmmmmmmmmmmmmm~~llllllllllllllllllllgggg............::::::::::::::......::##
   2 mmmmmmmmmmmmmmmmmmmm~~llllllllllllllllllllgggg............::::::::::::::......::##
   4 mmmmmmmmmmmmmmmmmmmm~~llllllllllllllddddddgggg............::::::::::::::......::##
   6 mmxxmmmmmmmmmmmmmmmm~~llllllllllllllddddddgggg............::::xx::::::::......::##
   8 llllllllllllllssllll~~llllllllllllllddddddgggg............::::::::::::::......::##
  10 llllllllllllllssllll~~llllllxxllllllllllllgggg............::::::::::::::......::##
  12 llllllllllllllllllll~~llllllllllllllllllllxxgg............::::::::::::::......::##
  14 llllllllllllllllllll~~llllllllllllllllllllffff............::::::::::::::......::##
  16 llllllllllllllllllll==llllllllllllllllllllffff..xx........::::::::::::::......::##
  18 llllllllllxxllllllll~~llllllllllllxxllllllffff............::::::::::::::......::##
  20 llllllllllllllllllll~~llllllllllllllllllll::::............::::::::::::::......::##
  22 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::##
  24 ................................................................................##
  26 ................................................................................##
  28 ................................................................EEKKKKKKKKK.....##
  30 ................................................................................##
  32 ................................................................................##
  34 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::xx::::::::##
  36                                                                                   
```

Legend: `h` roof R3 21.2 · `m` roof R2 17.6 · `l` roof R1 14.0 · `~` light court (void, 10.4) · `.` roadway 0 · `:`
sidewalk or plaza 0.15 · `T` water tower / tank house · `|` billboard or LED wall · `g` gantry deck 14.0 · `f` scaffold
stair tower · `d` service stair shaft · `s` roof-to-roof stair · `=` bridge (steel stair head, planks, pipe bridge) · `^` the
Stand · `b` the Booth · `K` IPX truck · `E` extraction · `P` player start · `7 8 9` reels · `x` explosive · `#` east facade
(the bound).

---

## 4. Sections (the vertical read)

1.2 m per row, 2 m per column, cut planes looking north.

```
Section S1, looking north, cut at z = -21 (A, steel stair, C, roof billboard, street, the Stand)
 33.6                                                                                   
 32.4                                                                                 ##
 31.2           AAAA                                                                  ##
 30.0         TTTTTTTT                                                                ##
 28.8         TTTTTTTT                                                                ##
 27.6         TTTTTTTT                                                                ##
 26.4         TTTTTTTT                      ||||                                      ##
 25.2         TTTTTTTT                      ||||                                      ##
 24.0           IIII                        ||||                                      ##
 22.8           IIII                        ||||                                      ##
 21.6 ----------IIII------                  ||||                                      ##
 20.4 ####################====              ||||                                      ##
 19.2 ####################  ssssss          ||||                                      SS
 18.0 ####################  ssssss          ++++                                      ##
 16.8 ####################  ####################                                      ##
 15.6 ####################  ####################                                      ##
 14.4 ####################  ####################                                      ##
 13.2 ####################  ####################                                      ##
 12.0 ####################  ####################                                      SS
 10.8 ####################  ####################                                      ##
  9.6 ##########################################                                      ##
  8.4 ##########################################                                      ##
  7.2 ##########################################                                      ##
  6.0 ##########################################                                      ##
  4.8 ##########################################                                      ##
  3.6 ##########################################                                      ##
  2.4 ##########################################                  ^^^^^^^^^^^^        ##
  1.2 ##########################################                  ^^^^^^^^^^^^        ##
  0.0 ##########################################                  ^^^^^^^^^^^^        ##
      -50       -40       -30       -20       -10       0         10        20        30        

Section S2, looking north, cut at z = +6 (B, D, service stair, gantry and LED wall, street, plaza)
 33.6                                                                                   
 32.4                                                                                 ##
 31.2                                                                                 ##
 30.0                                                                                 ##
 28.8                                                                                 ##
 27.6                                                                                 ##
 26.4                                                                                 ##
 25.2                                                                                 ##
 24.0                                             ||||                                ##
 22.8                                             ||||                                ##
 21.6                                             ||||                                SS
 20.4                                             ||||                                ##
 19.2                                             ||||                                ##
 18.0 ----xx--------------                        ||||                                ##
 16.8 ####################                        ||||                                ##
 15.6 ####################                dddddd  ||||                                ##
 14.4 ####################        xx      ddddDD88++++                                ##
 13.2 ####################  ##############ddddddgggg                                  SS
 12.0 ####################  ##############dddddd                                      ##
 10.8 ####################  ##############dddddd                                      ##
  9.6 ####################################dddddd                                      ##
  8.4 ####################################dddddd                                      ##
  7.2 ####################################dddddd                                      SS
  6.0 ####################################dddddd                                      ##
  4.8 ####################################dddddd                                      ##
  3.6 ####################################dddddd                                      ##
  2.4 ####################################dddddd                                      ##
  1.2 ####################################dddddd                                      ##
  0.0 ####################################dddddd                    xx                ##
      -50       -40       -30       -20       -10       0         10        20        30        
```

S1 legend: `#` solid mass · `-` parapet · `=` steel-stair head bridge (21.2) over the light court · `s` the steel stair down to
C (8 collider steps of 0.40) · `I` / `T` / `A` WT-A on its 4 m stand (tank 25.2 to 30.8, roof cone to 32.4) · `|` C's
roof billboard face (19.6 to 27.6) on its legs `+` · `^` the Stand · `S` east-facade LED screens (art, out of bounds).

S2 legend: `d` the service stair shaft and bulkhead in D · `g` the gantry deck (13.6 to 14.0) · `|` the gantry LED wall (16.2
to 25.2) · `+` the gantry front guard (playerOnly, 14.0 to 16.2: the letterbox the player sees and shoots through is 15.1 to
16.2 over the rail) · `8` Reel 8 (at z -0.6, projected) · `D` the gantry doors in D's east parapet.

Section S3 (described, x = -6 looking west): the gantry deck runs z -2..14 at 14.0. At z 14 it meets the scaffold tower (z
14..20), which falls in 8 flights to the sidewalk and leaves the player under the gantry at z 13.5. The sidewalk shed (deck
top 3.2) runs z 20..30 beside the tower's south face. From the tower's south landing at 5.35 an opening steps onto the shed
roof, and the shed's east edge is a 3.05 m drop to the roadway (the "shed hop", optional).

---

## 5. Movement and height: how the existing rules behave here

### 5.1 The rules (config.json player, unchanged)

| Rule | Value | What it means for Midtown |
|---|---|---|
| Step height | 0.42 (air 0.08) | Every walkable height change is a step of 0.42 or less. Collider stairs use 0.40 (roof stairs) or 0.346 (towers); art stairs keep real 0.17 to 0.20 risers, one collider step per two art risers |
| Jump | gravity 21, apex 1.0 m, launch 6.48 m/s, coyote 0.12 s | Air time 0.62 s on the flat: 2.3 m forward at walk (3.8 m/s), 3.9 m at sprint (6.4 m/s). A 1.1 m parapet cannot be jumped onto from the roof |
| Fall damage | (land speed - 13) x 7 when over 13 m/s | Free up to a 4.02 m drop. See the table below |
| Fall out | below y -30 back to the last ground | Never reached: the street is at 0 |
| Bounds | the player is clamped to the bounds | The east and south bounds sit inside the facade colliders |
| No ladders, no climbing, no moving platforms | | Every vertical link is a stair or a drop of 3.6 m or less. No elevator (it would need moving-platform code) |

| Drop | Land speed | Damage |
|---|---|---|
| 1.0 (a jump) | 6.5 | 0 |
| 3.6 (R3 to R2, R2 to R1: the drop-downs) | 12.3 | 0 |
| 4.0 | 13.0 | 0 (the limit) |
| 7.2 (R2 into the light court) | 17.4 | 31 |
| 13.85 (R1 to the sidewalk) | 24.1 | 78 |
| 17.45 (R2 to the sidewalk) | 27.1 | 98 |
| 17.73 or more (R3 to the street: 21.05) | 27.3 or more | death |

### 5.2 Edges: no accidental falls

The stream adds latency and the jump is short, so the level never asks for a precision jump, and nobody falls off a roof
by mistake.

- Every exterior roof edge and both sides of the light court get a 1.10 m parapet plus an **edge guard**: a playerOnly
  box on the parapet's outer face from the roof to roof + 3.0. A parapet alone is not enough, because a 0.42 box next to it
  plus a 1.0 jump clears it. The guard blocks movement only, so shots and sight pass. Goons never reach an edge anyway: a
  roof-layer cell with no floor is blocked (section 17.3).
- Bridges and planks have playerOnly side rails to 1.2 m over the deck.
- The gantry's front guard runs from the deck to the underside of the LED wall (14.0 to 16.2). Its ends rise to 17.0.
- The scaffold tower's outer faces are playerOnly from the street to 15.0, except the shed-hop opening at the 5.35 landing.
- The only deliberate drops are the three below. Each is 3.6 m or less and takes no damage. A test checks every authored
  drop and walks the rest of the edges (section 19).

| Drop | From | To | Height | Use |
|---|---|---|---|---|
| D1 | C south edge, parapet gap x -24..-22 at z -4 (17.6) | D roof (14.0) at about (-23, 14.0, -3) | 3.6 | Shortcut from Reel 7 to D, one way |
| D2 | B south edge, gap x -48..-46 at z 8 (17.6) | E roof (14.0) | 3.6 | Flank, one way |
| D3 | Scaffold south landing at 5.35, onto the shed roof (3.2), then off the shed's east edge to the roadway (0) | | 2.15, then 3.2 | Skips the last three flights |

### 5.3 Traversal links (every way between walk levels)

All links are 2.0 m wide or more, so the nav can pass them: a 0.5 m cell plus 0.5 m of inflation each side needs at least
1.5 m clear. The tower flights are 2.4 m.

| Link | Between | Geometry (colliders) | Path for Goons (nav link polyline) |
|---|---|---|---|
| L1 STEEL STAIR | A (R3) to C (R2) | Head bridge x -30..-27.6, z -22..-20, top 21.2 over the light court; 8 steps going east, x -27.6..-23.6, tops 20.8 to 18.0 (0.40 each, tread 0.5), each standing on C's roof; playerOnly rails both sides; parapet openings at z -22..-20 on A (x -30) and C (x -28) | (-31.0, 21.2, -21.0) → (-30.0, 21.2, -21.0) → (-27.6, 21.2, -21.0) → (-23.6, 17.6, -21.0) → (-23.0, 17.6, -21.0) |
| L2 TANK STAIR | A (R3) to B (R2) | 8 steps going south on B's roof, x -44..-42, z -12..-8, tops 20.8 to 18.0; A parapet opening x -44..-42 at z -12 | (-43.0, 21.2, -13.0) → (-43.0, 21.2, -12.0) → (-43.0, 17.6, -8.0) → (-43.0, 17.6, -7.0) |
| L3 BACK STAIR | B (R2) to E (R1) | 8 steps going south on E, x -36..-34, z 8..12, tops 17.2 to 14.4 | (-35.0, 17.6, 7.0) → (-35.0, 17.6, 8.0) → (-35.0, 14.0, 12.0) → (-35.0, 14.0, 13.0) |
| L4 BILLBOARD STAIR | C (R2) to D (R1) | 8 steps going south on D, x -16..-14, z -4..0, tops 17.2 to 14.4 | (-15.0, 17.6, -5.0) → (-15.0, 17.6, -4.0) → (-15.0, 14.0, 0.0) → (-15.0, 14.0, 1.0) |
| L5 SCAFFOLD | D and gantry (R1) to street | Pipe-scaffold stair tower x -8..-3, z 14..20: two flight columns x -8..-5.6 and -5.4..-3.0, spine x -5.6..-5.4; 8 flights of 5 steps of 0.346 (tread 0.5); landings N z 14..15.5 and S z 18..20 at 14.0, 12.27, 10.54, 8.81, 7.08, 5.35, 3.62, 1.88 and 0.15; flight k runs N to S when k is odd, S to N when even. Top: the gantry deck continues into the N landing. Bottom: the N landing opens north onto the sidewalk under the gantry | Generated: the landing centres and flight ends, top (-6.2, 14.0, 13.0) to bottom (-6.0, 0.15, 13.0) |
| L6 SERVICE STAIR | D (R1) to street | Enclosed concrete stair, shaft x -13..-8, z 4..10 (interior box): columns x -13..-10.6 and -10.4..-8, spine -10.6..-10.4; 8 flights of 5 steps of 0.346 (tread 0.6, run z 5.5..8.5); landings N z 4..5.5 and S z 8.5..10; bulkhead over the shaft to 16.8 with its 2.0 m door in the west face at z 4.2..6.2 (x -13); 2.0 m street door in D's east face at z 4.2..6.2 (x -8) | (-14.2, 14.0, 4.8) → (-12.2, 14.0, 4.8) → generated flights → (-9.0, 0.15, 4.8) → (-7.0, 0.15, 4.8) |
| PLANKS (same level) | B (R2) to C (R2) | Scaffold-board deck x -30.3..-27.7, z -10..-8, top 17.6 (0.1 thick), playerOnly rails; parapet openings both sides | Nav (same layer) |
| PIPE BRIDGE (same level) | E (R1) to D (R1) | Steel catwalk x -30.3..-27.7, z 16..18, top 14.0, playerOnly rails | Nav (same layer) |
| GANTRY DOORS (same level) | D roof to the gantry deck | Openings in D's east parapet at z 0.5..2.5 and z 11..13 (the service stair bulkhead takes the edge at z 4..10) | Nav (same layer) |

Under the stairs the stair boxes are solid down to the roof below: nobody walks under a roof stair.

---

## 6. The critical path, objectives and extraction

### 6.1 Player start

`playerStart`: feet (-43.2, 21.2, -35.0), yaw -2.3710, facing (0.6965, 0, 0.7175). This looks south-east across A toward
the steel stair, with the glow of the square beyond C's billboard. Unreal: pos (-4320, -3500, 2120), yaw 45.86.
The start pitch is -4 degrees (a per-level `startPitch`; the Block keeps 7). He has just come up the stairs: bulkhead A is
x -48..-44, z -37..-33, and its 2.0 m door faces east at z -36.0..-34.0.

### 6.2 Objectives (any order; the HUD shows all unsecured reels, as on the Block)

| # | id / code | Label | Zone / place | Position | rotationY (faces) | Interior | Where |
|---|---|---|---|---|---|---|---|
| 0 | reel7 / 7 | Reel 7 — The Tank | tanks / THE TANKS | (-19.0, 17.6, -33.0) | -1.5708 (south, to its door) | yes | Inside the tank house under WT-C on C (house x -22..-16, z -35..-29, roof 20.4; a **2.0 m** door on the south side x -20..-18) |
| 1 | reel8 / 8 | Reel 8 — The Gantry | gantry / THE GANTRY | (-6.0, 14.0, -0.6) | -1.5708 (south, along the deck) | no | North end of the gantry deck, at the LED wall's control cabinet (x -8..-6.6, z -2..-1.4) |
| 2 | reel9 / 9 | Reel 9 — The Booth | square / THE BOOTH | (16.0, 0.15, -32.6) | -1.5708 (south, to the window) | yes | The premiere desk in the booth under the Stand (2.0 m doors on both sides, 2.3) |

Reach rules (unchanged): 2.2 m range, 2.5 m vertical, facing 0.45, hold 2.4 s. Each case is at least 2.6 m from any wall
on its approach side, so the reach cone is never blocked.

**The order is the player's.** The rules let him secure the reels in any order: the HUD marks every unsecured reel, the
radio's reel line is chosen by the count (`radio.reel[n-1]`) and the wave by the count too. The intended order (7, 8, 9)
is the one the level is built around, but a player can skip the tank house, or run down the scaffold to the booth before
the gantry. So everything in this level keys on the **id** or on "all in", never on the count:

- The radio's three reel lines name no reel and no place (16.4): "One back. Every roof heard that. More coming." /
  "Two. One left out there. They're throwing everything at you now." / "That's all three. The IPX truck's rolling up
  on Forty-Sixth, east of the square. Move." The last one plays only when all three are in, so it may name the truck.
- The gantry screen G1 dies when **reel8** is secured, whenever that is (12.2). The IPX takeover and the truck's arrival
  come with **all three** (6.3, 12.2).
- The guide and the hints aim at the nearest unsecured reel (6.4).
- Neither reel room is safe: both have 2.0 m Goon doors and are on the nav (check in 19, `...ReelRooms`).

### 6.3 Extraction: the truck rolls in

- **Until the last reel is in, there is no truck.** The IPX truck (the existing AMITruck and SM_Vehicle_IPXTruck) is
  hidden, its colliders are out of the box world, and the extraction zone is inactive, so the refusal prompt never
  plays on this level (`extraction.arrival: "afterAll"`, 16.3; the Block and Canal keep the idling truck and the
  refusal). The player who comes off the scaffold walks past an empty W 46 St on his way north.
- **When the last reel is secured**, whichever it is: the radio line "rolling up on Forty-Sixth", the hero screens turn
  to IPX (12.2), and the truck pulls in from beyond the west bound along W 46 St over 5 s, headlights sweeping the
  south end of the plaza, and stops at (20.0, 0, 29.0), rotationY 0 (nose east). It is a presentation move: the truck's
  colliders (owner kind `truck`, `noNav`) join the box world when it stops, and nothing it passes is pushed. The IPX
  marker appears with it, as on every level.
- The zone is behind its rear doors at (14.6, 0, 29.0), radius 2.5, code IPX, label IPX truck, zone w46: the Block's
  offset, truck x minus 5.4. Unreal: zone (1460, 2900, 0) r 250; truck (2000, 2900, 0) yaw 0.
- **Why.** In the first draft the player passed the idling truck 10 m away on his way to the booth, was refused, and then
  ran 66 m back over ground he had just cleared. Now the last leg runs out of the booth's east door and south down
  Broadway, past the stalled bus and the theatre and hotel doors, ground the route has not used, to a truck that was
  not there before. The pursuit pushes from the north barricades behind him.

### 6.4 Guidance (feeds the PLAY.md ground path, hints and markers; data only)

The route changes walk level five times, so no single nav search can draw it, and the player may take the reels in any
order. The level file therefore carries a small **route graph**, `guide.graph` (16.3):

- **Nodes:** every link end (L1 to L6, the planks, the pipe bridge, the gantry doors), the top and bottom of each
  authored drop (D1 to D3), each reel's approach point, the extraction zone, each tagged with its layer.
- **Edges:** within a layer, the layer's own path search at run time; across layers, the link polylines (stairs, both
  ways) and the drops (down only).

The guidance draws the way from the player to the **nearest unsecured reel** by route length (to the extraction once all
are in), as a shortest path over this graph. It re-plans when the player changes layer or a reel is secured. Two biases
keep the line steady and on the landmark route: the target changes only when another reel is at least 15 % shorter, and
the service stair (L6) and the drops cost 10 m more than they measure, so the scaffold (L5) is the drawn way down.

Every drawn point lies on a walking surface. Each change of level along the drawn path carries a `step` mark {kind:
stair | drop | bridge, link, height}, which the path and the hint use. The marker label adds the height difference when
it is over 3 m ("[8] 24m ▼"), a small per-level addition the PLAY.md lane can take or leave. For the Block and Canal the
guidance stays the single-layer search it is today: `guide.graph` is read only when a level has nav layers above the
street.

In the intended order the graph draws these legs (design numbers; the generator recomputes them):

| Leg | From → to | Points (x, y, z) and steps | Length |
|---|---|---|---|
| 0 | start → Reel 7 | (-43.2, 21.2, -35.0) → (-38.0, 21.2, -29.0) → (-31.0, 21.2, -21.0) → (-27.6, 21.2, -21.0) **step: stair down 3.6 (L1)** → (-23.0, 17.6, -21.0) → (-20.5, 17.6, -26.5) → (-19.0, 17.6, -28.6) door → (-19.0, 17.6, -32.0) | 37 m |
| 1 | Reel 7 → Reel 8 | (-19.0, 17.6, -28.6) → (-17.0, 17.6, -14.0) → (-15.0, 17.6, -5.0) **step: stair down 3.6 (L4)** → (-15.0, 14.0, 1.0) → (-11.0, 14.0, 1.5) → (-8.2, 14.0, 1.5) door → (-6.3, 14.0, 1.5) → (-6.0, 14.0, 0.6) | 47 m |
| 2 | Reel 8 → Reel 9 | (-6.0, 14.0, 0.6) → (-6.3, 14.0, 12.8) **step: scaffold down 13.85 (L5, 8 flights; the path is drawn on every flight and landing)** → (-6.0, 0.15, 13.0) → (-1.0, 0, 6.0) → (5.0, 0, -8.0) → (9.0, 0.15, -18.0) → (9.0, 0.15, -32.0) → (10.3, 0.15, -32.0) door → (15.2, 0.15, -32.0) | 108 m |
| 3 | Reel 9 → IPX | (15.2, 0.15, -32.0) → (21.7, 0.15, -32.0) east door → (23.5, 0.15, -32.0) → (25.0, 0, -24.0) → (26.6, 0, -8.0) past the bus → (26.6, 0, 8.0) → (25.5, 0, 20.0) → (22.0, 0, 26.0) → (14.6, 0, 29.0) | 75 m |

**Hints are keyed by reel id**, not by leg, and say where the reel is from anywhere on the map (`guide.hints`, 16.4):

| Target | Hint after no progress |
|---|---|
| reel7 | "The tanks are one roof down from the top. Steel stair on the east side of the high roof." |
| reel8 | "The gantry's behind the big screen, on the low roof. Stairs at the south edge of the tank roof." |
| reel9 | "The booth's under the stand, north end of the square. Scaffold off the gantry, or the service stair inside." |
| extraction | "The truck's on Forty-Sixth, east of the square. Down Broadway, past the bus." |

The objective line and the markers work as on the Block: all unsecured reels, then IPX.

### 6.5 Pacing (target, hustler, intended order)

| Phase | Where | Time | What happens |
|---|---|---|---|
| Intro | A | 0:00 to 0:05 | Location card at 0.25 s, intro radio at 0.9 s; the patrol is 32 m or more away (C's south half, B). G1's countdown reads 8:00 |
| Approach 1 | A → C | 0:05 to 1:10 | First contact at the steel stair head: Goons on C below, a Buzzard over C |
| Reel 7 | Tank house | 1:10 to 1:20 | Hold 2.4 s inside the house while Goons come to its door; wave 1 comes over the planks from B and down the tank stair from A |
| Approach 2 | C → D → gantry | 1:20 to 2:40 | Fight on C and D, the drop D1 as a shortcut |
| Reel 8 | Gantry | 2:40 to 2:50 | G1 glitches and goes dark at about 5:10 on its clock (12.2); wave 2: Buzzards up from the square, Goons out of the service stair bulkhead and over the pipe bridge, street Goons firing up through the letterbox |
| Descent | Scaffold | 2:50 to 3:40 | 8 flights under Buzzard fire, landings open to the square |
| Approach 3 | The square, south to north | 3:40 to 4:40 | Street fight up the west roadway and the plaza past an empty W 46 St, the Stand as high ground |
| Reel 9 | Booth | 4:40 to 4:50 | Goons in through both doors and firing in through the slot. The screens turn to IPX; the truck rolls in; wave 3 from both ends of W 46 St, the north barricades and the theatre doors |
| Finale | Broadway, north to south | 4:50 to 6:00 | Pursuit (budget 7 / 10 / 14 with this level's +2) and Buzzards over the plaza, down the east lane to the truck |

---

## 7. Enemies

### 7.1 What stays the same, and what is one notch harder

The same Goon and Buzzard rules, the same pools (12 Goons, 8 Buzzards, 6 bodies), the same global difficulty tables
(hustler, boss and kingpin: patrol, three waves, maxAlive 9 / 11 / 13, pursuit). The wave index stays one per reel, as on
the Block: with exactly 3 reels everything lines up, and nothing in flow rules changes.

The level's `tuning.difficulty` (16.3; the Block has none) makes the last level the hardest:

- `waveAdd` {buzzard: 1} on boss and kingpin: one more Buzzard in each of the three waves. This is the level built for
  them (open air over every roof, a 36 m ceiling). The pool of 8 still caps the number alive.
- `pursuitBudgetAdd` 2: pursuit budgets 7, 10 and 14.
- `spawn.excludePlayerRoom` true: no Goon spawns inside the interior box the player is in (the booth, the tank house,
  the service stair), so they come through the doors.

### 7.2 What the level adds (data plus the code in section 17)

The multi-layer nav comes in **two steps** (17.3 to 17.6; MAPS.md lane N). The level data carries what both need, and
the grey box is played with each.

- **Walk levels for Goons (step A).** Every ground spawn and cover point carries a `layer` (street, r1, r2, r3). Each
  layer has its own grid. Goons spawn on allowed layers (spawn reach, below) and path only on their own layer's grid.
- **Firing cells (step A).** A Goon whose target is on another layer does not path toward the target's (x, z). It moves
  to the nearest cell of its own layer within 30 m that has a line of sight to the target and fights from there: roof
  Goons along the parapets above the player, street Goons on the plaza firing up at the gantry letterbox. This alone
  makes the roofs a ground fight.
- **Links (step B).** Goons also cross between layers along the links L1 to L6, walking the link polylines, so they
  follow the player down the scaffold and up the stairs. The level data's `nav.links` is read only from step B.
- **Spawn reach.** A ground spawn is a candidate only when its layer is within reach of the player's current layer:

| Player on | Ground spawns allowed on |
|---|---|
| r3 | r3, r2 |
| r2 | r2, r3, r1 |
| r1 | r1, r2, street |
| street | street, r1 |

  The fallback ring (26 m) and the patrol's 32 m minimum keep their meaning in plan distance, but only within the allowed
  layers. On a roof layer the fallback picks the nearest allowed authored point instead of a ring point, because a ring
  point would land on the street.
- **Stranded Goons.** A Goon with no firing cell and no link path to the player, out of his view, not having seen him for
  10 s, is quietly returned to the pool: no kill, no score, no event, and its wave slot goes back to the queue. That
  frees its maxAlive slot for a Goon near the player. This only applies when a level has more than one layer, so the
  Block never does it.
- **Buzzards.** A per-level `tuning.buzzard.maxAltitude` of **36** (Block: 15, absolute). The orbit height is already
  relative to the player (player y + 4.8 to 7.2), so over R3 they orbit at 26 to 28.4. The highest flight solid in bounds
  is WT-A's cone at 32.4. Midtown has no El, so the level file has no `el` section (17.2) and the deck logic is skipped.
- **If step A slips.** A review suggested a data-only fallback: the roofs as one stepped heightfield on today's single
  grid. It does not work here: today's nav band is measured from y = 0 (a cell is blocked by anything between 0.47 and
  1.5 m above the street), so no roof at 14 to 21 m can be walkable on it, stepped or not. Step A is therefore the
  minimum for roof Goons. The only fallback is the first draft's: roofs held by Buzzards (two more per wave through
  `tuning`) with street Goons firing up from firing positions authored as points, which is not the level the owner
  asked for. That is why step A starts in stage 1, in parallel with the loader, on a Midtown grey box (MAPS.md).

### 7.3 Ground spawns (30)

| # | Layer | Zone | Position | Notes |
|---|---|---|---|---|
| g0 | r3 | high | (-34.0, 21.2, -14.0) | behind HVAC, A's south-east |
| g1 | r3 | high | (-47.0, 21.2, -21.0) | behind WT-A's legs |
| g2 | r3 | high | (-32.5, 21.2, -36.5) | chimney stacks, NE corner |
| g3 | r3 | high | (-40.0, 21.2, -13.5) | head of the tank stair |
| g4 | r2 | tanks | (-43.0, 17.6, 2.0) | bulkhead B door (x -48..-44, z 0..4, door east): the main reinforcement door on the roofs |
| g5 | r2 | tanks | (-37.0, 17.6, -9.0) | behind the machine room (x -40..-34, z -8..-2) |
| g6 | r2 | tanks | (-33.0, 17.6, 6.5) | B's south-east |
| g7 | r2 | tanks | (-48.0, 17.6, -2.0) | B's west edge |
| g8 | r2 | tanks | (-25.5, 17.6, -36.5) | C's NW corner |
| g9 | r2 | tanks | (-13.5, 17.6, -12.0) | C's HVAC row south of the billboard |
| g10 | r2 | tanks | (-26.0, 17.6, -6.0) | C's SW corner, by drop D1 |
| g11 | r2 | tanks | (-14.0, 17.6, -37.0) | behind the billboard's north leg |
| g12 | r1 | gantry | (-26.5, 14.0, 2.0) | D's west edge |
| g13 | r1 | gantry | (-20.0, 14.0, 20.5) | D's south edge |
| g14 | r1 | gantry | (-14.2, 14.0, 4.8) | service stair bulkhead door |
| g15 | r1 | gantry | (-10.0, 14.0, 20.5) | D's SE corner, over W 46 St |
| g16 | r1 | back | (-47.0, 14.0, 20.5) | E's SW |
| g17 | r1 | back | (-34.0, 14.0, 14.0) | E, at the foot of the back stair |
| g18 | street | square | (-6.0, 0.15, -36.5) | west sidewalk, north barricade |
| g19 | street | square | (5.5, 0, -36.0) | behind the production truck |
| g20 | street | square | (25.0, 0, -36.5) | Broadway north |
| g21 | street | square | (29.2, 0.15, -14.0) | theatre doors (THE MERIDALE) |
| g22 | street | square | (29.2, 0.15, 6.0) | hotel doors (HOTEL CASTELLANE) |
| g23 | street | square | (25.0, 0, 18.0) | behind the water barriers, Broadway south |
| g24 | street | w46 | (29.0, 0, 30.0) | W 46 St east end |
| g25 | street | w46 | (14.0, 0.15, 35.0) | south sidewalk, shop door |
| g26 | street | w46 | (-46.0, 0, 29.0) | W 46 St west end |
| g27 | street | w46 | (-24.0, 0.15, 35.0) | south sidewalk west |
| g28 | street | square | (-7.0, 0.15, 4.8) | service stair street door |
| g29 | street | square | (13.8, 0.15, -18.5) | behind the souvenir kiosk south of the Stand (kiosk x 15..18, z -19.5..-17.5) |

### 7.4 Air spawns (18; y absolute)

Roofs: a0 (-44, 28.0, -36), a1 (-32, 28.0, -14), a2 (-16, 26.0, -36), a3 (-12, 26.0, -8), a4 (-46, 25.0, 4), a5 (-34,
25.0, 12), a6 (-22, 22.0, 2), a7 (-14, 22.0, 18), a8 (-40, 22.0, 20).
Square: a9 (0, 11.0, -36), a10 (16, 12.0, -20), a11 (26, 12.0, -30), a12 (2, 10.0, -10), a13 (18, 10.0, 0), a14 (26, 11.0,
12), a15 (-2, 10.0, 30), a16 (16, 10.0, 30), a17 (28, 12.0, 34).
Air spawns need no layer filter. The existing chooser (distance, hidden, recent) works as is. Facing: toward the centre of
their zone.

### 7.5 What each wave does here (the global tables, read through spawn reach)

- **Patrol (start, player on r3):** from r3 and r2 points 32 m or more away, so in practice C's south half (g9, g10) and B
  (g4 to g7). 1 or 2 Buzzards from a1 to a5.
- **Wave 1 (the first reel; in the intended order Reel 7, player in the tank house on r2):** r2, r3, r1. In practice it comes over the planks from B (g4 to g7),
  down the tank and steel stairs from A (g0 to g3), and from D (g12) up the billboard stair. Buzzards from the roof air
  points.
- **Wave 2 (the second reel; intended Reel 8, player on the gantry, r1):** r1, r2, street: out of the service stair bulkhead (g14), over the pipe
  bridge (g16, g17), from C above (g9, g10: the high ground), and from the square (g18 to g23, firing up at the letterbox:
  14 m up, 18 to 30 m away). Buzzards from the square air points come up past the screen.
- **Wave 3 and pursuit (the third reel; intended Reel 9, player on the street):** street and r1: both ends of W 46 St (g24, g26, g27), the north
  barricades (g18 to g20), the theatre and hotel doors (g21, g22), and Goons on D's east edge (g13, g15). Those come down
  the scaffold or the service stair (links), or fire from the roof edge until they do.

### 7.6 Cover points (target 110; `layer` on each)

The generator places cover points on the walking side of every movement collider 0.9 to 1.6 m tall (HVAC, planters,
barriers, car bodies, the bar counter, tank-stand plinths), one every 3 m along long faces, and along the inner face of
parapets (every 4 m, so a Goon can fire over a parapet). It skips points with no line to the open side. It keeps only
points on a walkable cell of their layer. Target counts: r3 14, r2 C 16, r2 B 14, r1 D 14, gantry 4, r1 E 8, street square
30, W 46 St 10. The existing filter |cover.y - goon.y| ≤ 1.0 (goon.cover.maxStep) already keeps Goons to covers on their
own level.

---

## 8. Explosives (17; the two existing kinds)

Radius: propane 6.5, rack 7.5. Chain range 5.2 to 5.9 m. None sits within 7.5 m of a reel case. Chains are deliberate only
where noted.

| # | Kind | Layer | Position | Rot | Story dressing |
|---|---|---|---|---|---|
| x0 | propane | r3 | (-36.5, 21.2, -17.5) | 0 | roofer's torch tank by a tar kettle |
| x1 | rack | r3 | (-33.0, 21.2, -31.0) | 1.5708 | welding rack by the chimney repair |
| x2 | propane | r2 | (-21.5, 17.6, -18.0) | 0 | 2 m from the foot of the steel stair (punishes a Goon crowd at the stair) |
| x3 | rack | r2 | (-12.5, 17.6, -24.0) | 1.5708 | under the roof billboard frame (sign crew's kit) |
| x4 | propane | r2 | (-33.0, 17.6, -11.0) | 0 | B, by the planks |
| x5 | propane | r2 | (-46.5, 17.6, 6.0) | 0 | B, by bulkhead B (punishes the wave door) |
| x6 | propane | r1 | (-22.0, 14.0, 10.0) | 0 | THE LOFTLARK's patio heater tank |
| x7 | rack | r1 | (-16.0, 14.0, 19.0) | 0 | D, roof repair |
| x8 | propane | r1 | (-40.0, 14.0, 18.5) | 0 | E |
| x9 | rack | r1 | (-6.6, 14.0, 12.6) | 1.5708 | gantry south end, at the scaffold head (12.6 m from Reel 8) |
| x10 | propane | street | (12.0, 0.15, 6.0) | 0 | food cart (plaza) |
| x11 | propane | street | (18.5, 0.15, -12.0) | 0 | food cart (plaza) |
| x12 | propane | street | (21.0, 0.15, -20.5) | 0 | the premiere's generator by the Stand (8.9 m from x11: no chain) |
| x13 | rack | street | (2.2, 0, -27.6) | 0 | behind the production truck's tail lift |
| x14 | propane | street | (20.0, 0.15, 34.5) | 0 | W 46 St south sidewalk, restaurant heater |
| x15 | rack | street | (-2.0, 0, 16.5) | 0 | at the scaffold's foot, in the parking lane |
| x16 | propane | street | (25.0, 0, -8.0) | 0 | off the stalled bus's front |

Each explosive has its own collider (owner kind explosive), as on the Block.

---

## 9. Interiors, doorways, zones

### 9.1 Interior boxes (audio reverb, exposure, the spawn rule; Buzzard doorways)

The interior boxes drive reverb, exposure and `excludePlayerRoom`. The doorways serve only the Buzzards' indoor routing
(MIEnemies.cpp 1786-1795), and a Buzzard needs a clear height of minHeight 2.2 + ceilingClearance 1.3 = **3.5 m**. None
of Midtown's rooms has it, so **no room has a Buzzard doorway, on purpose**: Buzzards fight the player through doors and
the booth's slot from outside. Goons enter every room on the nav through its 2.0 m doors. (Lane E checks that a room
with no doorway loads and routes; the Block always has doorways.)

| Id | Box min → max | Goon doors (2.0 m) | Buzzard doorways |
|---|---|---|---|
| I1 bulkhead A | (-48, 21.2, -37) → (-44, 24.0, -33) | east face, z -36.0..-34.0 | none (2.8 m) |
| I2 tank house (Reel 7) | (-22, 17.6, -35) → (-16, 20.4, -29) | south face, x -20..-18 | none (2.8 m) |
| I3 machine room | (-40, 17.6, -8) → (-34, 20.6, -2) | south face, x -38..-36 | none (3.0 m) |
| I4 service stair | (-13, 0, 4) → (-8, 16.8, 10) | roof: west face z 4.2..6.2; street: east face z 4.2..6.2 | none (a stair shaft) |
| I5 the Booth (Reel 9) | (10.6, 0.15, -34) → (21.4, 2.25, -29.5) | west and east faces, z -33.0..-31.0 | none (2.25 to 3.05 m); the front slot is shoot-through only (2.3) |

`fade` 1.5 as on the Block.

### 9.2 Zones and place names (first match wins; zones are 2D)

| Order | id | Name | Rect |
|---|---|---|---|
| 1 | high | HALVORSEN ROOF | x -50..-30, z -38..-12 |
| 2 | gantry | THE GANTRY | x -28..-3, z -4..22 (D, the gantry, the scaffold; the sidewalk under them reads THE GANTRY too) |
| 3 | tanks | THE TANKS | x -50..-8, z -38..8 (B and C) |
| 4 | back | BACK ROOFS | x -50..-28, z 8..22 (E) |
| 5 | square | THE SQUARE | x -8..31, z -38..22 |
| 6 | w46 | W 46 ST | x -50..31, z 22..37 |

`places.regions` repeats these with the names. The objective place for Reel 9 is THE BOOTH.

---

## 10. Combat spaces and sightlines

- **Halvorsen Roof (A, R3, 20 x 26 m).** The opening. WT-A on four 0.45 m legs (cover, and a silhouette against the glow),
  two HVAC units, two skylights, a chimney row along the north party wall, a tar kettle. High ground over C (3.6 m down,
  20 to 30 m lines) and over B. One way down to each: L1 east and L2 south. No Goon spawn within 32 m of the start.
- **The Tanks (C and B, R2).** C (20 x 34): the tank house with WT-C on top (Reel 7 inside; one 2.0 m door, the room is 6 x 6, so
  the reel hold is a corner the player must clear), an HVAC row, the roof billboard along the east edge (x -11..-8.8, z
  -36..-20: its legs and catwalk are a cover line, its lit face points at the square). B (20 x 20): the machine room,
  WT-B (short stand), bulkhead B (the wave door), the planks to C. Lines: about 30 m across C, 45 m from B's west edge to
  C's billboard.
- **The Gantry (D and the gantry deck, R1).** D (20 x 26): THE LOFTLARK, a closed rooftop lounge (bar counter, stacked
  loungers, folded umbrellas, planters: the cover), the service stair bulkhead, the two doors to the gantry (z 0.5..2.5
  and 11..13). The gantry (3.5 x 16 m) sits behind the LED wall. Standing, the player sees the square through a letterbox between the front rail
  (15.1) and the wall's bottom edge (16.2), and the street sees his head. It is the most exposed place in the level and is
  meant to be short.
- **The Scaffold.** 8 flights, 2.4 m wide. Each landing opens east to the square (1.5 m openings): Buzzards circle the tower,
  Goons below fire up. The service stair is the safe, blind alternative.
- **The Square.** Three lanes north to south: the west roadway (12 m: parked cars, concrete barriers staggered every 12 m),
  the plaza (14 m: planters, kiosks, carts, café tables, the Stand), Broadway (6 m: the stalled bus at z -6..6, water
  barriers). Breakers keep any open ground line under 45 m (the Goons' sight range): the production truck (north), the
  bus, the kiosk line at z -18 and z 6, the Stand. Typical ranges are 8 to 25 m. The Stand is the street's high ground
  (3.35 m), facing south down the whole plaza.
- **W 46 St.** The extraction strip: a 9 m roadway, the truck, the scaffold foot, cross-fire from both ends.

---

## 11. Lighting: night over a bright square

The level is lit by its screens. The rig is built to be cheap on SM5: one shadowed directional, few shadowed locals, no
volumetric clouds, a static sky.

### 11.1 Rig `night_midtown` (atmos_midtown.json; starting values, tuned on the box)

| Element | Setting | Why |
|---|---|---|
| Key: "the square's glow" | One movable directional from the east, elevation 22°, azimuth from +x toward the square's centre, lavender-white #c9c2ff, about 8 lux; shadows: 2 cascades to 60 m, contact shadow 0.03 | Gives the roofs and the west facades a direction and shadows from where the screens are, for the cost of the Block's sun |
| Sky | No SkyAtmosphere, no VolumetricCloud: an unlit sky dome (radius 3 km) with a city-glow gradient (horizon #6a3e5a to zenith #0b0d18) and one painted cloud layer lit from below, panning 0.002 UV/s. The dome is a sky-only mesh hidden while the front-end stage is shown: at 3 km it would enclose the stage room 1 km up | Clouds cost about 16 % of the GPU (PROGRESS.md 3c); a dome is near free |
| SkyLight | Static: captured once at build time from the dome, never at run time | Removes the run-time sky capture (part of the 0.40 ms "cloud reconstruction plus sky capture" on the box) |
| Height fog | Exponential, density 0.012, falloff 0.08, inscatter #3b2f4a, directional inscatter from the key, start 15 m, max opacity 0.85 | Glow over the square, depth between towers; about zero at 1 km, so the front-end stage room at (0, 0, 1000 m) is untouched |
| Volumetric fog | Off by default; a top quality step only after measuring | Cost |
| Screens' light | Lumen software GI from the screens' emissive (static between slides) plus 4 rect lights, one per hero screen (gantry wall G1, E1, E3 corner, N1 north stack), no shadows, source sized to the screen, attenuation 35 m, colour = the current slide's average (set when the slide changes) | Direct coloured spill on the plaza that Lumen at 0.5 render scale would make blotchy |
| Street lamps | 12 spots, 4000 K LED, no shadows, attenuation 14 m, on the twin-head plaza poles and the avenue poles | Floor pools between screens |
| Roof work lights | 4 sodium (2200 K) spots: the tank house flood (shadowed, 1024), the gantry door flood (shadowed, 1024), bulkhead B, the pipe bridge (no shadows) | Warm against the cool square; the objectives read |
| Stairwell and booth | 4 small points in the service stair, 2 in the booth, no shadows; booth monitors emissive | |
| Post | Histogram auto exposure EV100 2.5 to 5.5 (up 3, down 1.5), local exposure (highlights 0.6, shadows 0.7), bloom 0.35, vignette 0.2, white balance 5200 K, **no film grain and no chromatic aberration** (both cost encoder bitrate at QP 34) | Screens bright without crushing the roofs |

Totals: 1 directional, 26 local lights, of which 2 are shadowed (art bible 2.8: 24 shadowed at most, 4 to 6 per pixel).
At most 6 lights overlap on any pixel on the critical path; the worst spot is the plaza centre.

Both shadowed locals are spots (a shadowed point light renders six faces on SM5, which has no virtual shadow maps), and
the lights never move, so whole-scene shadow caching keeps their static depths cached.

The night rig, level-driven emissives and the `times: ["night"]` path in MIGameSubsystem are one piece of work shared
with Chinatown (MAPS.md lane L), built and measured in a grey box before any art. The Block keeps its day rig as is.

**Palette (readability).** The Goons wear oxblood on black. Midtown is the cool level: lavender-white key, white LED
lamps, blue and white screens. The only warm light is the sodium work lights on the roofs, and no screen behind a fight
from the critical path shows a red field (12.2). The readability check of chinatown.md 17 (check 11) runs in V1 to V6.

### 11.2 Emissive levels (night)

| Surface | Nits (cd/m²) | Notes |
|---|---|---|
| Hero LED screens (G1, E1, E3, N1) | 450 | The Block's signs are 900 by day; night exposure is about 9 stops lower |
| Secondary screens and the ticker | 300 | |
| Lightboxes (C billboard, kiosks, storefronts) | 200 | |
| Exposed neon (THE LOFTLARK, marquees' script) | 250 | MI_Neon_* at night strength |
| Marquee bulb bands | 350 | One bulb texture with a slow chase (3 s cycle, no flashing) |
| Window grid on the backdrop towers | 25 to 60 | The existing window-grid material, night lit fraction 0.35 |

---

## 12. Billboards, screens and signs

### 12.1 Rules

- Invented names only. No real brand, logo, product, show, trade dress or look-alike. That includes the "heart" state
  slogan, any real theatre's show titles, the transit operator's marks and globes, any police booth or insignia, and the
  look of any specific real tower's screen stack. Real place names are fine: TIMES SQ, BROADWAY, SEVENTH AV, W 46 ST, NEW
  YORK, MIDTOWN. No phone numbers (212 needs the owner's approval: ART_BIBLE 5.7). IPX is the only real mark (the owner's).
- Each name below is checked against a trademark search before its art is final. A name that turns out to be real is
  replaced, never kept. **Searched 2026-11-26 (lane C): the approved list, each query and what it found are in
  [names.md](names.md).** Eleven names collided with a real business or mark, or with a famous title or a real
  person's name, and are replaced in 12.2 and 12.4 (names.md 5 gives the old names and the evidence). English only,
  like Canal Street: no other script on any screen or sign. The art's list and the level layout still carry the old
  names until their lanes change them: `python3 tools/names/check_names.py` lists every line and passes when none is
  left.
- A sign is an object first (cabinet, frame, power, mounting), then its face (ART_BIBLE 5.1).

### 12.2 Screens (all opaque; one master material)

| Id | Where | Size | Slides (cycle) |
|---|---|---|---|
| G1 | The gantry LED wall, facing east over the square (playable behind it) | 16 x 9 m | Until **reel8** is secured: a Vulture takeover, "WORLD PREMIERE · MIDNIGHT" in white on black with a small oxblood VLTR mark in one corner (not a red field behind the Goons on the gantry), and a countdown clock (digits atlas). The clock starts at 8:00 at the intro, matching the 11:52 PM place line; if it reaches 0:00 first it reads "STAND BY" and the premiere waits (no gameplay effect). When reel8 is secured: a 0.4 s glitch, then black with a dim "NO SIGNAL". When all three are in: "IPX PRESENTS" |
| E1 | East tower podium, facing west | 24 x 18 m | MIRAVESSE · Eau de Nuit (perfume) → NORTHBOUND AIRWAYS · Fly the late one |
| E2a, E2b | East hotel, two verticals | 8 x 20 m each | KESTREL MOBILE · Five bars, five boroughs / BRASS & BUN · Burgers till four |
| E3 | Corner screen at x 30, z 22 (curved) | 20 x 12 m | THE MERIDALE THEATRE presents LAMPLIGHT AVENUE, a new musical → VESPERLINE CRUISES |
| N1 | North tower stack beyond z -38 (three screens) | 3 x 14 x 8 m | HOROVAN watches / NORTHWEFT fall collection / FIZZWICK SODA |
| S1 | W 46 St south facade | 12 x 6 m | DUSKLINE TOURS · The city after dark |
| Ticker | Band on the theatre at y 8.0 to 8.8, x 30, z -30..-6 | 24 x 0.8 m | Invented headlines: "SQUARE CLOSED TONIGHT FOR A PREMIERE", "CROSSTOWN TRAFFIC HEAVY", "FORECAST: CLEAR, 41°" |
| C1 | C's roof billboard (a lightbox, not LED), facing east | 16 x 8 m | MARLOWE & FINCH · The holiday floor is open |

When the last reel is secured, whichever it is, every hero screen (G1, E1, E3, N1) changes to an IPX slide for 6 s, then goes back to its cycle (the
"the city's yours" beat).

### 12.3 How the screens stay cheap

- **One master `M_MI_Screen`:** opaque, black base, roughness 0.6, emissive = atlas tile × nits, a crossfade between two
  tiles, and an LED-pixel mask (a 64 x 64 tiling texture) faded out between 8 and 20 m, so the pixel grid never moirés
  at render scale 0.5. No translucency, no world position offset, no video, no render targets.
- **Two atlases** `T_MT_Screens_A` and `_B`, 4096² BC1 sRGB with mips (about 11 MB each), 8 slides each. The ticker is one
  4096 x 256 strip panned at 0.35 m/s. The countdown digits are a 512 x 64 strip.
- **A slide director** (presentation only: AMIScreenDirector, data in props_midtown.json) drives one Material Parameter
  Collection. It changes no more than one hero screen in any 2 s, each screen at most every 8 s, with a 0.6 s crossfade.
  So the encoder never sees a large area change at once and Lumen reconverges between changes. Story events (`objective:secured`
  for reel8, and all reels in) trigger the scripted slides. Nothing flashes faster than 3 Hz (also a photosensitivity rule).
- **Lumen fallback:** if the screens make the GI blotch or crawl at render scale 0.50 on the box, set the screen meshes'
  Affect Dynamic Indirect Lighting off and let the rect lights carry the spill.
- **Bloom**, not geometry, makes the glow: no light cards, no glare sprites.

### 12.4 Storefronts and lettering (invented)

West facades (C and D, ground floor): SEVENTH AV SOUVENIRS, SLICE OF SEVENTH, SHUTTERBOX CAMERA & ELECTRONICS, a closed bank
lobby (BELLHAVEN SAVINGS). East: THE MERIDALE THEATRE marquee, HOTEL CASTELLANE canopy. South (W 46 St): a steakhouse
(BRANNIGAN'S CHOP HOUSE), a pharmacy (ASHBY & CROSS PHARMACY). Roofs: HALVORSEN BUILDING in raised letters on A's parapet,
CORVIN HALL on C's cornice, THE LOFTLARK in neon on D (unlit: the lounge is closed). The scaffold carries an invented
contractor's sign (KESSLER & ROTH SCAFFOLD). The production truck: BRIGHTWIRE EVENTS, with VLTR sprayed over it.
Graffiti tags as on the Block (VULTURES, VLTR, RULE, INC.). The stalled bus: an invented operator (CITY CROSSTOWN, plain
blue and white, no real livery).

**Midnight, after the crowd.** An empty square at 11:52 PM reads as a set, so the plaza and the roadways carry what a
crowd leaves behind: dropped merch (VLTR premiere caps and folded flyers in the gutters), cardboard sign boards from fans,
food carts still lit and steaming with their awnings half down, a line of taxis and a cab queue beyond the north and
south barricades (art only, past the bounds, headlights on), spent crowd-control barriers pushed into a pile, police-style
sawhorses with no agency mark, trash cans overflowing, pigeons. The sound bed carries a distant crowd behind the
barricades (13). All of it is dressing: no collider is added for anything under 0.5 m.

---

## 13. Audio (per-level data; global audio.json untouched)

| Zone | Box | Bed |
|---|---|---|
| roofs | x -50..-3, y 12..40, z -38..22 | wind, HVAC hum (point sources on 6 units), distant traffic, the square's sound bed from below at -10 dB |
| square | x -8..31, y 0..12, z -38..22 | the premiere's instrumental loop from the screens' speakers (invented, no real songs), a distant crowd murmur behind the north barricades, barricade rattles, generator hum by the Stand, sparse distant horns and a siren far away (no PA voice) |
| w46 | x -50..31, y 0..12, z 22..37 | traffic; the IPX truck's engine and air brakes when it rolls in (6.3), then its idle |
| interiors | I1 to I5 | reverb from the interior boxes, as on the Block |

The zones and beds live in `Content/Data/audio_midtown.json` (audio.json's schema), named by levels.json `data.audio`,
as for Canal. The El and its train (audio.json zones underEl, ambience.train) do not exist in Midtown, so the file
declares no train.
The G1 glitch and the IPX takeover each get one sting.

---

## 14. Assets: reused and new

### 14.1 Reused (existing families; same names, materials and import)

| Family | Assets |
|---|---|
| street | SM_Street_Road_20m, Sidewalk_4m, Kerb, Manhole, Drain, Hydrant (the road is 234k triangles: check its SM5 fallback first, section 15) |
| facade | Bays and BayWindow / BayBlank (Brick Buff, Brown, Painted), Cornice, Parapet, PartyWallCap, RoofPanel_4m, WaterTank, StairBulkhead_Red/Buff, AirConditioner, WindowBlind; FireEscape modules on back facades only (thin-steel flicker, READY.md R3) |
| furniture | Dumpster, TrashBags, MilkCrates, Pallets, Cardboard, NewspaperBox, Mailbox, SignPost, Bollard, SidewalkShed (the shed by the scaffold), RollUpDoor, Billboard (C1 frame reference) |
| gaps | TrafficLight, Planter, TrashCan, FoodCart (x10, x11), VendingMachine |
| props | SM_Prop_* scans; propane tank, welding rack (explosives); SM_Gameplay_MasterCase and MasterReel_1..3 |
| signs | signs.py builders (lightbox, exposed neon, LED flex, pan letters), MI_Neon_* |
| vehicles | Taxi, Van, BoxTruck (production truck base), Sedan, SUV, SM_Vehicle_IPXTruck |
| backdrop | build_backdrop towers (glass curtain wall, stone with punched windows, setbacks) with a Midtown seed, 300 m tall at most; the window-grid material and interior cube maps TC_* |
| characters | Goons, Buzzard, unchanged |
| materials | The six masters; TS_Roof_ScanGravel and TS_Roof_ScanBitumen, the bricks, stucco, steel plates, tiles, pavers |

### 14.2 New (Blender families, script-built, existing conventions)

All new meshes are authored at the density SM5 draws. They are imported with the Nanite fallback at 100 % of their
triangles, so what is authored is what E3DS draws. The triangle figures are caps.

| Family file | Asset | Tris cap | Notes |
|---|---|---|---|
| assets/roof.py | SM_Roof_TankStand_4m, _2m | 12k | steel stand (mi/steel.py), members at least 6 cm; tie rods only on backdrop tanks |
| | SM_Roof_TankHouse_6x6 | 10k | brick base under WT-C; doorway; work light |
| | SM_Roof_SteelStair_3p6 (2 m wide, 18 art risers) and SM_Roof_StairHead_2p4 | 15k, 6k | galvanised, solid stringers |
| | SM_Roof_PlankBridge_2p6x2, SM_Roof_PipeBridge_2p6x2 | 6k each | scaffold boards with pipe rails at least 6 cm |
| | SM_Roof_HVAC_RTU_L, _M; SM_Roof_Skylight_2x3; SM_Roof_Vent_Mushroom; SM_Roof_ChimneyStack; SM_Roof_TarKettle; SM_Roof_Dish; SM_Roof_Antenna; SM_Roof_WorkLight | 10k / 6k / 3k / 4k / 4k / 3k / 2k / 2k | rooftop dressing |
| | SM_Roof_Lounge_Bar, _Lounger_Stack, _Umbrella_Folded, _PlanterBox | 8k / 4k / 3k / 3k | THE LOFTLARK |
| assets/gantry.py | SM_Roof_Gantry_16m (deck, grating, rails, cabinet) | 25k | grating as a texture on plates, not open mesh |
| | SM_Sign_LEDWall_16x9 (cabinet tiles, truss back) | 30k | the playable back is plate and truss, not lattice |
| | SM_Roof_BillboardFrame_16x8 (C1) | 25k | catwalk, 4 lamps |
| | SM_Sign_LEDWall_Tile_2m, SM_Sign_TowerStack, SM_Sign_Ticker_4m, SM_Facade_Marquee_A / _B | 2k / 40k / 2k / 30k | east and north screens (art only) |
| assets/scaffold.py | SM_Scaf_Flight_2p4, SM_Scaf_Landing_2p4, SM_Scaf_Bay_Frame, SM_Scaf_Netting_Panel, SM_Scaf_Sign | 8k / 4k / 6k / 0.5k / 1k | netting is opaque woven texture, NOT alpha (thin-geometry and masked cost) |
| assets/square.py | SM_Sq_Stand_Tier_12m, SM_Sq_Stand_SideWall, SM_Sq_Booth_Desk, _Rack, _Monitor | 12k / 6k / 8k / 4k / 1k | riser glass lit from inside by an emissive strip |
| | SM_Sq_Planter_Granite_4m, SM_Sq_Bench, SM_Sq_CafeTable, SM_Sq_CafeChair, SM_Sq_Kiosk_Souvenir, SM_Sq_LightPole_LED, SM_Sq_Barrier_Jersey, SM_Sq_Barrier_Water, SM_Sq_Generator, SM_Sq_CableRamp | 6k / 4k / 2k / 1.5k / 20k / 5k / 2k / 3k / 8k / 1k | chairs have 3 cm legs at least, kept off the hero sightlines |
| assets/vehicles.py | SM_Vehicle_CityBus (invented operator) | 90k | the only new vehicle; also the biggest single mesh |
| facade tables | Midtown building tables A to E (storey overrides 3.30 / 3.225 / 3.10, ground 4.70); shopfront modules Souvenir, Slice, Camera, Bank; east podiums (theatre, hotel) | per module 2k to 30k | facade.py and place_buildings.py take a per-level table (section 17.10) |
| textures | T_MT_Screens_A/B (4096², BC1), T_MT_Ticker (4096 x 256), T_MT_Digits, T_MT_LEDMask (64²), T_Sign_Midtown atlas (4096²: every lightbox, storefront, marquee and kiosk face), TS_Timber_TankStave (2k), TS_Scaffold_Netting (2k), TS_Granite_Pavers (2k), TS_Steel_Galvanised (2k, if the steel plates do not fit) | | 4 new tiling sets at most, 4 atlases; no new 8K sets; no per-shop unique 4096 x 512 sets |

---

## 15. Budgets for E3DS (RTX A4000, 8 threads, SM5, no Nanite, 1920 x 1080, render scale 0.50 to 0.63)

The bar is the Block's own measured number on the same box load: `lag-test.sh ... load=1:0.05:0:1024` (l20), compared in
the same run. Absolute ceilings are the Block's E3DS envelope.

| Budget | Midtown target | Ceiling | Notes |
|---|---|---|---|
| GPU frame, Story with a fight (13 alive, kingpin) | ≤ 12.0 ms on the A4000 | 13.3 ms | About 4 ms in hand at 60 fps, as the Block has. The removed clouds and sky capture (about 16 to 20 %) pay for the 4 rect lights, 26 locals and the screens |
| Game thread | ≤ 5 ms | 6 ms | Rays are brute force over the colliders: keep them under the Block's |
| Render thread (8 threads) | ≤ 6.5 ms | 7.5 ms | The 16-core box measured 7.7 on the Block: E3DS-class runs are needed |
| Colliders (box world) | 760 | 820 | Breakdown below |
| Actors in the map | ≤ 900 | 1,083 (the Block) | Repeated modules as ISM components, per building holder |
| Draw calls in the worst view (V3, the gantry letterbox) | ≤ 1,300 | 1,500 | |
| Triangles drawn in the worst view | ≤ 1.3 M | 1.5 M | Fallback meshes count: measure the Block's baseline first (`stat rhi`, `stat scenerendering`, `stat initviews`) |
| Lights | 1 directional (2 cascades) + 26 local, 2 shadowed local | 24 shadowed (art bible), 6 per pixel | |
| Large emissive screens | 7 big surfaces + ticker | 9 | Static between 0.6 s crossfades; at most one hero screen changing in any 2 s |
| Translucency | none on the critical path | 4 layers | Glass is the opaque M_MI_Glass; no masked netting or chain-link near the path |
| Particles | steam from 4 roof vents, small | | No volumetric smoke |
| New texture memory resident | ≤ 180 MB | | The Block already wants 717 to 865 MB of the 600 MB pool. Midtown assumes READY.md R4's 1000 MB pool, measured at V1 (the widest view) |
| Cooked size for the map | ≤ 400 MB | | Both new maps together at most +1.0 GB (Canal ≤ 600 MB): every E3DS session copies the whole zip to a cold machine, and storage is 10 GB at 2.1 to 2.2 GB per version today |
| Thin geometry | members at least 6 cm within 25 m of the path | | READY.md R3 flicker at render scale 0.50; check V2 to V4 with flicker.py rev8 |

Collider breakdown (planned):

| Group | Count |
|---|---|
| Ground slabs, sidewalks, plaza | 10 |
| Building masses, facade setbacks, light-court fill, south and east facades | 24 |
| Parapets (with openings) | 34 |
| Edge guards (playerOnly) | 22 |
| The Stand and the Booth | 26 |
| Plaza and street furniture (planters, benches, tables, kiosks, poles, bins, hydrants) | 67 |
| Barriers | 26 |
| Parked vehicles (8, sliced) + the bus | 46 |
| IPX truck, production truck, generator | 12 |
| Sidewalk shed | 14 |
| Scaffold tower | 54 |
| Service stair | 56 |
| Roof stairs L1 to L4 and their heads | 43 |
| Planks and pipe bridge | 8 |
| Bulkheads, machine room, tank house | 23 |
| Water towers (3) | 18 |
| Roof billboard C1, gantry, LED wall | 17 |
| Rooftop dressing | 76 |
| Explosives | 17 |
| **Planned** | **593** |
| Contingency (glazing, bulletOnly details, art fixes) | 167 |
| **Target** | **760** |

Nav: four grids. Street 162 x 150 = 24,300 cells (the Block's grid is 25,024). r1 92 x 52 = 4,784, r2 84 x 92 = 7,728, r3
40 x 52 = 2,080. Each has its own A* expansion cap, max(9000, cells/2).

Shot views for the box and the gates (positions as eye points, looking at):

| View | Eye | Look at | Why |
|---|---|---|---|
| V1 start | (-43.2, 22.88, -35.0) | (10, 10, -10) | widest view: the roofs, the screens, the backdrop |
| V2 tank house door | (-19.3, 19.28, -27.0) | (-5, 22, -10) | WT-C stand, billboard back, thin steel |
| V3 gantry letterbox | (-6.2, 15.68, 6.0) | (20, 3, 6) | worst view: the whole square plus every screen |
| V4 scaffold mid landing | (-5.0, 8.6, 17.0) | (15, 3, 0) | scaffold steel against bright screens (flicker) |
| V5 top of the Stand | (16.0, 5.03, -33.0) | (10, 2, 20) | the plaza south, emissive density |
| V6 at the truck | (0.0, 1.68, 26.0) | (12, 6, -20) | the finale, looking up the square |

---

## 16. The level data

### 16.1 Files (names as proposed; MAPS.md may rename)

| File | Content |
|---|---|
| Content/Data/level_midtown.json | The level file, same schema as level.json (section 16.3), written by the shared layout tool and the engine's bake step |
| Content/Data/props_midtown.json | Prop placements (catalogue ids), the screen director's screens and slides |
| Content/Data/atmos_midtown.json | Rig `night_midtown`, lamps, sign and window lights |
| Content/Data/audio_midtown.json | Audio zones and beds (section 13), audio.json's schema |
| Content/Data/levels.json | New entry `midtown`; it joins `order` only in the change that ships the split screens and travel (progression.md 7.1) |
| Content/Data/frontend_text.json | `frontend.levels.midtown` and `frontend.story.midtown.*` (section 16.4) |
| Content/Data/art_catalogue.json | New ids for the new props (added, existing ids untouched) |
| tools/levels/layouts/midtown.py | The hand-authored layout table (this document's boxes and points), in the one layout schema shared with Canal |
| tools/levels/build_level.py | The shared layout tool: layout table → colliders, points, layers, links, the guide graph, drops, tuning |
| `-run=MILevelBake` (engine) | Writes `nav` per layer, filters cover onto walkable cells, and writes the reach and drop report with FMIBoxWorld's own code, so no second copy of the nav rules exists (MAPS.md lane D) |
| /Game/Maps/L_Midtown, /Game/Maps/L_GreyMidtown | Generated on the box, never committed |

### 16.2 levels.json entry

```json
"midtown": {
  "id": "midtown",
  "text": "frontend.levels.midtown",
  "map": "/Game/Maps/L_Midtown",
  "data": { "level": "level_midtown.json", "props": "props_midtown.json", "atmos": "atmos_midtown.json", "audio": "audio_midtown.json" },
  "place": { "night": "frontend.story.midtown.location.byTime.night" },
  "number": 3, "par": 6.5, "story": "frontend.story.midtown", "greyMap": "/Game/Maps/L_GreyMidtown",
  "times": ["night"],
  "provides": {
    "playerStart": true, "objectives": 3, "extraction": true,
    "enemySpawns": { "ground": 30, "air": 18 }, "nav": true, "coverPoints": true,
    "explosives": true, "titlePath": true, "showroom": null
  },
  "preview": { "camera": "titlePath", "thumbnail": { "asset": "T_UI_Level_Midtown", "status": "missing",
    "notes": "a 16:9 frame from title key 2: the gantry LED wall over the square" } }
}
```

### 16.3 level_midtown.json: sections

Required, as the loader reads them today (web units plus a `ue` mirror, like level.json):

- `meta` (file, schema 1, generator `tools/levels/build_level.py`, seed 4646, units, conversion, counts).
- `bounds` {minX -50, maxX 31, minZ -38, maxZ 37}.
- `zones` and `places` (section 9.2).
- `playerStart` (section 6.1).
- `objectives[3]` (section 6.2: reel7, reel8, reel9), `extraction` with `truck` (section 6.3) and the new optional
  `arrival: "afterAll"`.
- `enemySpawns.points[48]` (section 7.3 and 7.4), each with `type`, `zone`, `place`, `interior`, `facing`, and the new
  `layer`.
- `coverPoints.points[~110]`, each with the new `layer`.
- `explosives.items[17]` (section 8) with their collider indices.
- `interior.boxes[5]`, `interior.doorways[]` empty on purpose (section 9.1), `fade` 1.5.
- `cinematicPath.points[14]` (section 18).
- `colliders.boxes[~760]`, same fields (tag, surface, owner, flags bulletOnly / playerOnly / noNav, index). Surfaces:
  concrete, asphalt, granite, gravel (roofs), bitumen, steel, grating, timber, glass, brick.
- `ground` (surfaces and floors on the 0.1 m grid, for footsteps and impacts; floors now also cover roofs).
- `el`: **absent** (17.2, done once for both new levels). No degenerate deck.

New optional sections (the Block has none, so nothing changes for it):

```json
"nav": {
  "cell": 0.5, "inflate": 0.5, "bandMin": 0.47, "bandMax": 1.5,
  "layers": [
    { "id": "street", "y": 0.0,  "rect": { "minX": -50, "maxX": 31, "minZ": -38, "maxZ": 37 }, "floor": "plane" },
    { "id": "r1",     "y": 14.0, "rect": { "minX": -50, "maxX": -4, "minZ": -4,  "maxZ": 22 }, "floor": "boxes" },
    { "id": "r2",     "y": 17.6, "rect": { "minX": -50, "maxX": -8, "minZ": -38, "maxZ": 8 },  "floor": "boxes" },
    { "id": "r3",     "y": 21.2, "rect": { "minX": -50, "maxX": -30, "minZ": -38, "maxZ": -12 }, "floor": "boxes" }
  ],
  "links": [
    { "id": "steelStair", "a": "r3", "b": "r2", "path": [[-31.0,21.2,-21.0],[-30.0,21.2,-21.0],[-27.6,21.2,-21.0],[-23.6,17.6,-21.0],[-23.0,17.6,-21.0]] },
    { "id": "tankStair",  "a": "r3", "b": "r2", "path": [[-43.0,21.2,-13.0],[-43.0,21.2,-12.0],[-43.0,17.6,-8.0],[-43.0,17.6,-7.0]] },
    { "id": "backStair",  "a": "r2", "b": "r1", "path": [[-35.0,17.6,7.0],[-35.0,17.6,8.0],[-35.0,14.0,12.0],[-35.0,14.0,13.0]] },
    { "id": "billboardStair", "a": "r2", "b": "r1", "path": [[-15.0,17.6,-5.0],[-15.0,17.6,-4.0],[-15.0,14.0,0.0],[-15.0,14.0,1.0]] },
    { "id": "scaffold",   "a": "r1", "b": "street", "path": "generated: tower landings and flight ends, (-6.2,14.0,13.0) to (-6.0,0.15,13.0)" },
    { "id": "serviceStair", "a": "r1", "b": "street", "path": "generated: (-14.2,14.0,4.8) to (-7.0,0.15,4.8)" }
  ],
  "spawnReach": { "r3": ["r3","r2"], "r2": ["r2","r3","r1"], "r1": ["r1","r2","street"], "street": ["street","r1"] },
  "firingCellRange": 30,
  "strandedAfter": 10
},
"guide": {
  "graph": { "nodes": [ "link ends, drop tops and bottoms, reel approach points, the extraction; each {id, layer, pos}" ],
             "edges": [ "links (both ways), drops (down only), with step marks {kind: stair|drop|bridge, link, height} and a cost bias" ] },
  "targetHysteresis": 0.15
},
"drops": [ "D1, D2, D3 of section 5.2: from, to, height" ],
"tuning": {
  "buzzard": { "maxAltitude": 36 },
  "difficulty": { "waveAdd": { "buzzard": 1 }, "waveAddOn": ["boss", "kingpin"], "pursuitBudgetAdd": 2 },
  "spawn": { "excludePlayerRoom": true },
  "rating": { "time": [[330, 2], [480, 1]] },
  "startPitch": -4
}
```

(The bake step writes the generated link paths out as point lists. The strings above stand for those lists. `nav.links`
is read from nav step B; with step A only, the layers, spawn reach, firing cells and the stranded rule apply. The guide
graph's hints are in the text overlay, keyed by objective id, 16.4.)

### 16.4 Text (frontend_text.json `frontend.story.midtown`; never shadows a text.json key)

The full overlay is in progression.md 7.2, in the shared schema: text.json's own key paths, radio entries `{text, secs}`,
`{name}` for the crew (it resolves to "Rule" for Rule), and a fallback to text.json for any key the overlay lacks. What
changed from the first draft:

- **Reels 7 to 9**: `reels.list` reel7 / 7 / "Reel 7 — The Tank", reel8 / 8 / "Reel 8 — The Gantry", reel9 / 9 /
  "Reel 9 — The Booth".
- **The HUD says reels, the radio says masters**: objectives "Take back the last three master reels", "Two reels left",
  "Last reel", "Get to the IPX truck".
- **Radio reel lines that hold in any order** (6.2), and a done line with `{name}`. The place line moves to 11:52 PM
  (`location.byTime.night`).
- **Hints keyed by objective id** (`guide.hints` {reel7, reel8, reel9, extraction}, 6.4), not by leg.
- The Hold name and tagline move to `modes.holdout.name` and `location.taglineHoldout`. `prompts.refuse` is not
  needed here (the truck is not there to refuse, 6.3), and it falls back to text.json if ever shown.

The Block keeps reading text.json exactly as now: these keys are looked up only when the loaded level is midtown.

---

## 17. Engine changes this level needs (all golden-safe: the Block's data has none of the new sections)

The item codes in brackets are MAPS.md's lanes and items.

| # | Change | Where | Block behaviour |
|---|---|---|---|
| 17.1 | Per-level loader (E1): FMILevelData::ForLevel(Id) from levels.json `data.level`; Get() stays the Block | World/MILevelData.cpp, Flow/MIGameSubsystem.cpp Boot | Same file, same singleton result |
| 17.2 | `el` optional (E2): Level->bHasDeck; Buzzard spawn clamping, flight solids and PlanAroundDeck skip the deck when absent. A room with no doorway loads and is never entered by Buzzards (E12) | World/MILevelData.cpp, Enemies/MIEnemies.cpp 1715-1718, 1932-1950 | bHasDeck true, same code path |
| 17.3 | **Nav step A, grids (N1):** one grid per `nav.layers` entry. A "boxes" layer cell is walkable when a support top lies within ±0.45 of the layer's y at the cell centre AND no nav-blocking collider spans [y + 0.47, y + 1.5] (inflated 0.5). The "plane" layer is today's rule. Goon layer = the highest layer whose y ≤ goon y + 0.5 with a walkable cell under it. FindPath, IsWalkable, RandomPoint and NearestWalkable take the layer; a Goon spawned on a layer is snapped within that layer only | World/MIBoxWorld.*, Enemies/MIEnemies.cpp 739-751, 816 | No `layers` means one plane layer, built by the current code: Golden.World diff 0 |
| 17.4 | **Nav step A, behaviour (N2 to N4):** `layer` on spawns and covers; spawn reach and the layer-aware fallback; firing cells (a target on another layer → the nearest own-layer cell within 30 m with sight of it); the stranded rule (7.2) | Flow/MIGameRules.cpp ChoosePosition 353-437, Enemies/MIEnemies.cpp | No layers: every point allowed, the 26 m ring as now, no firing cells, no recycling |
| 17.5 | **Nav step B, links (N5):** a path to a goal on another layer = path to the best link end (straight-line estimate over the few links) + the link polyline walked with MoveCapsule + path on the far layer. Replan when the goal's layer changes | Enemies/MIEnemies.cpp | No links |
| 17.6 | The bake step (D2): `-run=MILevelBake --level <id>` writes `nav` per layer, the generated link polylines, the cover filter and the reach and drop report, with the runtime's code | new commandlet in Source/MurderInc/Tools | Not run on the Block's file (exported from the web game) |
| 17.7 | Per-level `tuning` merged over config (E7): buzzard.maxAltitude, flow.rating.time, presentation startPitch, difficulty `waveAdd` / `pursuitBudgetAdd` / `maxAliveAdd`, `spawn.excludePlayerRoom` (E8) | Enemies/MIEnemyTune.cpp, Flow/MIGameRules.cpp, MIGameSubsystem.cpp 51-66 | No tuning block: config as now |
| 17.8 | Per-level text overlay `frontend.story.<level>.*` with fallback to text.json (E5) | Flow/MIFlowRules.cpp FMIText, UI/MIHUD.cpp 344-348 | Falls back to text.json: same strings, Golden.Directors unchanged |
| 17.9 | Per-level rig and audio zones (E4, E6, L1): `night_midtown` from atmos_midtown.json, audio_midtown.json; `times: ["night"]` honoured per level | MIGameSubsystem.cpp ~180-212, Audio/MIAudioData.cpp | Day rig, global audio zones |
| 17.10 | Extraction arrival (E10): with `extraction.arrival: "afterAll"`, the truck is hidden and its colliders (owner kind `truck`, `noNav`) are out of the box world until all reels are in; then the 5 s roll-in, the colliders join, the zone goes live; no refusal before | Flow/MIGameRules.cpp UpdateExtraction 675-694, World/MITruck.cpp, World/MIBoxWorld.cpp | No `arrival`: the idling truck and the refusal as now |
| 17.11 | Screen director (E11, presentation only): MPC slides from props_midtown.json; listens to `objective:secured` by id (reel8) and to all reels in | new AMIScreenDirector | Not spawned on the Block |
| 17.12 | Guidance over the route graph (G2, G3) when the level has nav layers above the street: nearest unsecured reel, hysteresis, step marks, hints by id, the marker's height | the PLAY.md lane's guidance code | Block path unchanged |
| 17.13 | Art builder (A0, B1): build_block.py becomes build_level.py --level <id>; facade.py and place_buildings.py take per-level tables; mi_greyblock_map.py --level midtown → L_GreyMidtown | Content/Python, art/blender, tools/box/block.sh | `--level block` reproduces L_Block exactly, proved by a dump-and-diff |
| 17.14 | Boot and packaging (E3, T1): the boot gate reads levels.json `map` and `greyMap`; MapsToCook and -map add /Game/Maps/L_Midtown; map travel from game code (the console refuses `open`) | Flow/MIGameMode.cpp, Config/DefaultGame.ini, tools/box/cloud/package-cloud.sh | Block start map unchanged |

17.3 and 17.4 (step A) are the hard dependency: without them Goons on the roofs get snapped to the street, and no
data-only fallback exists (7.2). Step A starts in MAPS.md stage 1, in parallel with the loader, and is gated on the
Midtown grey box in stage 2; step B (17.5) follows and is in the release if it passes its gate, but the level is complete
without it.

---

## 18. Title camera path (14 keys, a loop at the existing 1.15 speed)

| Key | Position | Look at |
|---|---|---|
| 0 | (24, 30, 34) | (10, 6, -10) |
| 1 | (18, 24, 24) | (6, 6, -18) |
| 2 | (10, 18, 10) | (-6, 20, 6) |
| 3 | (3, 17, 3) | (-6, 21, 6) |
| 4 | (-2, 22, -6) | (-12, 22, -24) |
| 5 | (-6, 26, -16) | (-19, 25, -32) |
| 6 | (-14, 28, -24) | (-38, 28, -26) |
| 7 | (-24, 30, -30) | (-40, 26, -24) |
| 8 | (-34, 29, -36) | (-30, 20, -10) |
| 9 | (-44, 27, -26) | (-20, 16, 0) |
| 10 | (-40, 24, -8) | (-6, 14, 6) |
| 11 | (-30, 22, 4) | (10, 6, -6) |
| 12 | (-12, 20, 10) | (16, 4, -20) |
| 13 | (8, 26, 30) | (10, 6, -10) |

Key 2 to 3 passes 7 m in front of G1 (the thumbnail frame). Every key is inside 60 m of the bounds and under 40 m high.

---

## 19. Verification (the same bar as the Block, without touching its goldens)

| Test | Checks |
|---|---|
| MurderInc.Levels.Midtown.Loads | every required section present, `el` absent; counts equal levels.json `provides` (3, 30 ground, 18 air, 17 explosives, 14 title keys) |
| ...Nav | the bake's `nav` equals FMIBoxWorld's rebuild per layer, cell for cell (a guard against hand edits and stale files) |
| ...Reach | with step A: every spawn and cover point on a walkable cell of its layer, and each layer's points on one component; with step B: from playerStart through the layers and links, a path to each objective's approach point and to the extraction, and every link end walkable |
| ...ReelRooms | the tank house and the booth: every door at least 2.0 m clear; a Goon path from at least two ground spawns into each; the booth's slot passes a ray and blocks the player capsule (standing, crouched, jumping) |
| ...Edges | a sprinting capsule pushed outward, with jumps, along every roof edge, bridge, stair and the scaffold every 1 m never leaves its surface except at D1 to D3; every authored drop ≤ 4.0 m and takes no damage under config.json `player.fall` |
| ...Budgets | colliders ≤ 820; nav cells per layer as planned; no collider thinner than 0.05 m that blocks movement |
| ...Story | Run.Midtown.StoryComplete: a bot walks the drawn guide (invulnerable) in the intended order, grabs the three reels, reaches IPX; flow events in order; the Midtown strings appear and no Block string does ("Hollis", "the block is yours", "south end of the lot") |
| ...StoryAnyOrder | the same run in the orders 9, 7, 8 and 8, 9, 7: the radio lines read right (no line names a reel or a place before the last), G1 dies exactly when reel8 is secured, the truck rolls in only when all three are in, the guide always targets an unsecured reel and never flips between two targets more than once in 5 s, and no refusal prompt is ever shown |
| ...Holdout | ground and air spawns on the street level |
| ...NavStepA | a Goon spawned on each roof layer stays on it, reaches a firing cell when the player is on another layer, and is recycled when stranded; a Goon on the street never walks under a roof toward the player's (x, z) |
| ...NavStepB | a Goon walks from every roof spawn to the street over each link and back, within twice the link's length in time |
| Block goldens | Golden.World, Enemies, EnemyLogic, Blast, FlowRules, Directors, PlayerSim, Loadout.DataLoads: unchanged and passing |
| Box | grey-box playtest with step A only and with step B (route time, fight readability); then art at V1 to V6; l20 load against the Block in the same run; flicker.py rev8 at render scale 0.50 at V2 to V4; the readability check (chinatown.md 17, check 11) at V1 to V6 |
| E3DS | the three-map package: a full Midtown Story run on kingpin with the frame-time capture, the stream at 1920 x 1080 |

---

## 20. Build order

MAPS.md section 3 schedules this level's work in stages and lanes. In short:

1. **Data and code, no GPU:** the Midtown layout table in the shared layout tool, the bake, level_midtown.json; the
   loader, tuning and text (17.1, 17.2, 17.7, 17.8) and nav step A (17.3, 17.4) with the tests in 19 (headless, like
   the run tests). Gate: every test passes, and the Block goldens are unchanged.
2. **Grey box on the box:** L_GreyMidtown (data boxes drawn grey, night rig placeholder). Playtest the route on all three
   difficulties with step A, then with step B when it lands; tune spawn reach, firing cells, covers, link widths and the
   rating times. Gate: a Story run completes in 5.5 to 7 min on boss, and roof fights happen on every roof.
3. **Blender:** the new families (roof, gantry, scaffold, square, bus), Midtown facade tables, the sign and screen atlases
   (names cleared). Gate: previews, the triangle caps, the manifest bounds.
4. **Unreal build:** build_level.py --level midtown; the night rig; the screen director. Gate: V1 to V6 pictures reviewed.
5. **Performance:** l20 against the Block in the same run; fix to budget. Gate: the section 15 targets.
6. **Package and E3DS:** three maps cooked, start map unchanged, travel from the debrief; the E3DS run. Gate: 60 fps held,
   guidance on every leg in any order, clean menus, deaths, weapons and attachments.

---

## 21. Open questions (for the owner or the lead)

Decided in revision 2: the extraction is the IPX truck, rolling in on W 46 St after the last reel (6.3); the campaign
resets health and stats per level and ends on the album card (progression.md); Midtown leans on Buzzards through
`tuning` (7.1). Still open:

1. Night (recommended, "bright square") or dusk? Dusk keeps the day rig's sky but loses most of the screens' punch, and
   brings the cloud cost back.
2. The invented brand list in 12.2 and 12.4: approve, change or add. Searched 2026-11-26, eleven replaced; the list
   for the owner's sign-off is [names.md](names.md). And are IPX slides on every screen after the last reel wanted?
3. Hold the Square on this map: ship it, with a best score per map?
