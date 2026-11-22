# 05 · The block: layout, architecture, the El, yards

Port spec for the level of MURDER INC.: one block of Jamaica Ave in Hollis, Queens. Ground truth is the web game
(three.js r160): `src/level.js`, every file in `src/level/` and `src/stubs/level.js`, read completely, plus
`docs/CONTRACT.md` 6.10, 10 and 11. Nothing here needs the JavaScript to be read again.

How to read this document:

- **Citations** are `path:line`. A path without a directory (`layout.js:21`) is relative to `src/level/`;
  `level.js` alone is `src/level.js`. Everything else is written out (`src/config/catalog.js:70`).
- **Units** are metres, seconds and radians in web coordinates unless a column says otherwise.
- **Effective values.** Where code changes a value after it is authored (spawn and cover points pushed onto walkable
  ground, vehicle paint snapped to a chart, lamp hints contributed by props) the tables give the value the running game
  uses. They were read from a running browser build (real `mats`, `props` and `level` modules, default seed 1994);
  the prop placements and the level's own 316 colliders are identical in the level built in node with
  `test/level-helpers.js`.
- `src/stubs/level.js` is a box testbed with the same API and a similar plan (shop x -20 … -2, deck 12 m long, 12 ground
  + 6 air spawns, 27 cover points, 4 explosives, seal walls 24 m high: `src/stubs/level.js:23-30, 179, 370-419`). It
  only runs when the real level is stubbed or fails at boot (`docs/DEV.md` "How stubs are swapped"). **Do not port its
  numbers**; it is listed here only so nobody mistakes it for the layout.
- Catalogue props (cars, street furniture, shop equipment: `src/config/catalog.js:68-144`) are placed by the level but
  built by the prop factory. This spec gives every placement (2.15) and the size of each prop; their construction is
  in `docs/unreal/spec/05b-props.md` (briefs in `assets/props.json`). Everything else in this document is built by
  the level code itself and has an asset brief in `docs/unreal/spec/assets/level.json`.
- Neighbouring specs, referred to by file name: `01-player.md` (movement and the collision world), `02-weapons-combat.md`
  (hit resolution, explosives), `03-enemies.md` (how the AI uses nav, cover, the El and the shop), `04-flow.md`
  (spawning, objectives, extraction, the title camera), `07-ui-audio.md` (minimap, zone names, ambience),
  `00-unreal-scout.md` (engine names), `06-look-fx.md` (surfaces, the painting of signs, posters and windows, how
  the lamp list is lit, the sky, the train, steam, the city beyond the bounds). Where this document repeats one of
  their facts (the sign list, the lamp list, the prop placements) the numbers were checked to agree.

---------------------------------------------------------------------------------------------------

## 1 Overview

The level is the whole game world: one city block, 92 × 68 m, sealed on every side. Jamaica Avenue runs east–west
through the middle under an elevated railway (the El), between two rows of brick walk-ups with shops at street level.
The player starts at the west end, on the south sidewalk at the foot of the closed 188 St station stair, and fights east
along the avenue through a "maze" of parked, double-parked and abandoned vehicles, barriers and construction clutter to
three master reels: one in the middle of the avenue beside the Vultures' van, one on the floor of V&R AUTO BODY (the
chop shop: the only building that can be entered, with a mezzanine office), and one at centre court in The Cage (a
fenced basketball court). The IPX truck, the extraction point, idles in the south-east corner of the parking lot.
Side spaces turn the street into loops instead of a corridor: an alley beside the shop reached through the shop's side
door, a cut beside the deli that leads to the cage's second gate, a vacant lot whose back opens onto a rear service lane
that runs east into the parking lot, and a construction sidewalk shed whose plywood deck, 2.8 m above the sidewalk, is
the one raised vantage. Two "curtains" of tall objects cross the avenue so that no sightline at eye height runs much
past 45 m. Besides geometry and collision the level publishes the data every other system reads: play bounds, four
zones, the start pose, the three objectives, the extraction zone, 46 enemy spawn points, 100 AI cover points,
21 explosive placements, 90 lamp hints, 6 steam points, the El's deck volume, the vantage, the title-camera path, and
the surface, floor-height and interior queries.

---------------------------------------------------------------------------------------------------

## 2 Facts

### 2.1 Coordinate systems and conversions

| Space | Units | Axes | From web (x, y, z) |
|---|---|---|---|
| Web game (three.js) | m | +Y up, north = -Z, east = +X (`docs/CONTRACT.md` §1) | (x, y, z) |
| Blender | m | Z up, east = +X, north = +Y | (x, -z, y) |
| Unreal | cm | Z up, X = east, Y = south | (x, z, y) × 100 |

- A web rectangle x0 … x1, z0 … z1 is Blender x0 … x1, y -z1 … -z0, and Unreal X 100·x0 … 100·x1, Y 100·z0 … 100·z1.
- The world origin is the centre of the avenue's roadway at road level. The ground is the plane y = 0; sidewalks
  are slabs with their top at 0.15.
- **Object yaw** ψ is `Object3D.rotation.y`: a prop's local +X points along web (cos ψ, -sin ψ) in (x, z)
  (`kit.js:621`). Blender `rotation_euler.z` = ψ. Unreal yaw = -ψ in degrees, **for a mesh whose local axes went
  through the same conversion as positions** (web +X → Unreal +X, web +Z → Unreal +Y). Web props that have a "front"
  face local +Z, except vehicles and the hoop, which face +X (`docs/CONTRACT.md` 6.2 "Facing"); if such a prop is
  re-authored with its front on +X, add +90° to the Unreal yaw (see 6, question 1).
- **Camera / player yaw** ψ: forward = (-sin ψ, 0, -cos ψ) (`docs/CONTRACT.md` §1). Unreal yaw = -90° - ψ°.
- **Walls** are described by the side they face: `+z` = south, `-z` = north, `+x` = east, `-x` = west
  (`buildings.js:18-27`). `u` is the coordinate along the wall (x for walls facing ±z, z for walls facing ±x), "proud"
  means out of the wall plane toward the viewer.

### 2.2 Global constants

| Constant | Value | Meaning | Source |
|---|---|---|---|
| `BOUNDS` | x -46 … 46, z -34 … 34 | play area, 92 × 68 m; also the nav grid extent | `layout.js:21`, `level.js:172` |
| `KERB` | 0.15 m | sidewalk height above the roadway | `layout.js:23` |
| `ROAD_Z` | 7 m | \|z\| of both kerb lines (roadway 14 m wide) | `layout.js:24` |
| `FRONT_Z` | 11 m | \|z\| of both building lines (sidewalks 4 m wide) | `layout.js:25` |
| `GROUND_FLOOR` | 3.8 m | height of the storefront storey | `layout.js:26` |
| `FLOOR` | 3.1 m | height of every storey above it | `layout.js:27` |
| building roof height | 3.8 + (storeys - 1) × 3.1 | | `layout.js:130` |
| `PARAPET` | 0.9 m | parapet above every roof; building colliders end at roof + 0.9 | `buildings.js:10, 435` |
| `BAY` | 3.1 m | width of one window bay | `buildings.js:11` |
| `SEAL` / `SEAL_HEIGHT` | 0.6 m / 8 m | thickness and height of the player-only walls round the block | `level.js:31-32` |
| `INTERIOR_FADE` | 1.5 m | distance over which `interiorAt` falls from 1 to 0 outside the shop | `level.js:30` |
| `NUDGE` | 2.5 m | how far a spawn or cover point may be moved to reach walkable ground | `level.js:33` |
| `FAR` | 96 m | \|x\| to which the avenue, its sidewalks and the El run on as decor | `ground.js:7`, `el.js:11` |
| `KERB_STONE` | 0.28 m | width of the kerb stone along the road edge of a slab | `ground.js:8` |
| `FLARE` | 0.9 m | length of the slope at each end of a dropped kerb | `ground.js:9` |
| `LIFT` | patch 0.008, wet 0.014, paint 0.021, decal 0.028 m | heights of the flat ground layers over the road plane | `ground.js:11` |
| `CROSSWALK` | x 23 … 26.6 | the mid-block crossing | `ground.js:13` |
| `NORTH` / `SOUTH` | z -5.98 / 5.98 | centre lines of the two parking lanes | `street.js:18-19` |
| extraction radius | 2.5 m | horizontal radius of the extraction zone (vertical reach 3.5 m is flow tuning) | `src/config/flow.js:50-52`, `level.js:106` |

### 2.3 Plan, play bounds and zones

North is up; x runs left to right (east = +x), web z runs top to bottom (south = +z). In Blender flip the vertical
axis sign (y = -z); in Unreal the same picture is X to the right, Y down.

```
 web z                                                                                    Blender y
  -34 ┌───────────────┬─┬────────────────────────────┬─────┬─────────┬─┬──────────────────┐  +34
      │ tenement N1   │g│  V&R AUTO BODY (interior)  │alley│ deli N2 │c│ THE CAGE         │
      │ 5 storeys     │a│  mezzanine NW · reel 2     │     │ 3 st.   │u│ reel 3           │
  -11 ├───────────────┴n┴──[roll door]──[bay]────────┴─────┴─────────┴t┴────[gate]───────┤  +11
   -7 │═════ north sidewalk (+0.15) ═════ dropped kerbs at the doors and the alley ═══════│   +7
      │ station · START →   JAMAICA AVE under the El · reel 1         crossing  roadblock │
    7 │═════ south sidewalk (+0.15) ══ [gateway] ═ [ scaffold shed + stair ] ═ [lot entry]│   -7
   11 ├───────────────┬────────────┬────────────┬──────────────────────────┬─────────────┤  -11
      │ station house │ pawn +     │ vacant lot │ S3: chicken, liquor,     │ PARKING LOT │
      │ S1, 3 st.     │ records S2 │ mural wall │ nails, 2 storeys         │ booth,      │
   26 │               │ 4 storeys  │            ├──────────────────────────┤ billboard   │  -26
      │               │            │   rear service lane  → → → → → → → →  │ IPX TRUCK   │
   31 │               │            ├────────────┴── garages ───────────────┤ (extraction)│  -31
   34 └───────────────┴────────────┴───────────────────────────────────────┴─────────────┘  -34
    x -46           -30          -16           -4                          22            46
```
(after `layout.js:5-19`; "gan" is the gangway beside the tenement, "cut" the passage between the deli and the cage.)

Zones are four axis-aligned rectangles that tile the bounds (`layout.js:158-163`). They are tags for spawning, AI and
the HUD, not walls:

| id | Display name | web x | web z | Blender x | Blender y | Unreal X (cm) | Unreal Y (cm) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `west` | WEST END | -46 … -30 | -34 … 34 | -46 … -30 | -34 … 34 | -4600 … -3000 | -3400 … 3400 |
| `shop` | CHOP SHOP | -30 … 22 | -34 … -11 | -30 … 22 | 11 … 34 | -3000 … 2200 | -3400 … -1100 |
| `avenue` | THE AVENUE | -30 … 22 | -11 … 34 | -30 … 22 | -34 … 11 | -3000 … 2200 | -1100 … 3400 |
| `lot` | THE LOT | 22 … 46 | -34 … 34 | 22 … 46 | -34 … 34 | 2200 … 4600 | -3400 … 3400 |

- `west` is the quiet start: no enemy spawn point lies in it (`data.js:21-22`).
- `shop` is the whole strip north of the building line between x -30 and 22: the gangway, the chop shop, the alley
  and the deli. `avenue` is the avenue plus everything south of it between the same x: the vacant lot, S3, the rear
  lane, the garages. `lot` is everything east of x 22: the cut, The Cage, the east end of the avenue with the
  roadblock, the parking lot.
- The HUD's place name splits `lot` at the kerb lines: z < -7 reads `THE CAGE`, z > 7 reads `THE LOT`, the roadway
  between reads `THE AVENUE` (`level.js:127-132`, 3.3).

### 2.4 Footprints of every area

Heights are web y (= Blender z). "Parapet" is the top of the building collider.

| Area | web x | web z | web y (height) | Blender x | Blender y | Notes | Source (src/level/) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Play bounds | -46 … 46 | -34 … 34 | 0 (ground plane) | -46 … 46 | -34 … 34 | 92 × 68 m | layout.js:21 |
| Roadway (kerb to kerb) | -46 … 46 | -7 … 7 | 0 | -46 … 46 | -7 … 7 | asphalt sheet runs on to x ±110, z ±72 as decor | layout.js:24, ground.js:49 |
| North sidewalk band | -46 … 46 | -11 … -7 | 0.15 | -46 … 46 | 7 … 11 | slabs in 2.8; back edge at z -12.2 for x 25 … 46 | layout.js:133-144 |
| South sidewalk band | -46 … 46 | 7 … 11 | 0.15 | -46 … 46 | -11 … -7 | slabs in 2.8 | layout.js:133-144 |
| N1 tenement | -46 … -24 | -34 … -11 | 0 … 16.2 (parapet 17.1) | -46 … -24 | 11 … 34 | gangway pocket x -26.2 … -24, z -16 … -11 left open | layout.js:122 |
| V&R AUTO BODY (chop shop) outer walls | -24 … 6 | -31 … -11 | eave 6.0, roof top 6.3, parapet 6.9 | -24 … 6 | 11 … 31 | walls 0.4 thick | layout.js:51-59 |
| Chop shop clear interior | -23.6 … 5.6 | -30.6 … -11.4 | 0 … 6.0 | -23.6 … 5.6 | 11.4 … 30.6 | 29.2 × 19.2 m floor | shop.js:19-22 |
| Shop mezzanine deck | -23.6 … -15.4 | -30.6 … -25 | deck top 2.8 | -23.6 … -15.4 | 25 … 30.6 | 8.2 × 5.6 m, north-west corner | layout.js:64 |
| Mezzanine office | -23.6 … -17.4 | -30.6 … -27.1 | 2.8 … 5.3 | -23.6 … -17.4 | 27.1 … 30.6 | doorway x -19 … -17.4 in its south front | layout.js:64, shop.js:172-197 |
| Mezzanine stair | -15.4 … -12.04 | -26.3 … -25 | 0 … 2.8 | -15.4 … -12.04 | 25 … 26.3 | 12 risers, climbs west | layout.js:65 |
| Alley | 6 … 11 | -34 … -11 | 0 | 6 … 11 | 11 … 34 | chained gate at z -31.4 | layout.js:80 |
| N2 deli | 11 … 22 | -34 … -11 | 0 … 10.0 (parapet 10.9) | 11 … 22 | 11 … 34 |  | layout.js:123 |
| The cut | 22 … 25 | -34 … -11 | 0 | 22 … 25 | 11 … 34 | paved from z -33.5 | layout.js:81, yards.js:75 |
| The Cage (fence line) | 25 … 45.4 | -33 … -12.2 | mesh to 4.0 | 25 … 45.4 | 12.2 … 33 | gates: south x 33 … 36, west z -29.4 … -26.4 | layout.js:83-93 |
| Court boundary lines | 26.6 … 43.9 | -29.9 … -15.1 | 0 | 26.6 … 43.9 | 15.1 … 29.9 | 17.3 × 14.8 m | layout.js:92 |
| S1 station house | -46 … -30 | 11 … 34 | 0 … 10.0 (parapet 10.9) | -46 … -30 | -34 … -11 |  | layout.js:124 |
| S2 pawn + records | -30 … -16 | 11 … 34 | 0 … 13.1 (parapet 14.0) | -30 … -16 | -34 … -11 | vestibule pocket x -24 … -21.8, z 11 … 13.4 | layout.js:125 |
| Vacant lot | -16 … -4 | 11 … 26 | 0 | -16 … -4 | -26 … -11 | gateway x -11.9 … -8.7 in the hoarding at z 11.14 | layout.js:95 |
| S3 chicken / liquor / nails | -4 … 22 | 11 … 26 | 0 … 6.9 (parapet 7.8) | -4 … 22 | -26 … -11 |  | layout.js:126 |
| Rear service lane | -16 … 22 | 26 … 31 | 0 | -16 … 22 | -31 … -26 | opens east into the lot at x 22 | layout.js:96 |
| Garages | -16 … 22 | 31 … 34 | 0 … 3.8 (collider 4.7) | -16 … 22 | -34 … -31 | 8 roll doors on the lane | layout.js:127 |
| Parking lot | 22 … 46 | 11 … 34 | 0 | 22 … 46 | -34 … -11 | entry x 28.6 … 35 (dropped kerb + gap in the low wall) | layout.js:97-103 |
| Sidewalk shed deck (the vantage) | 1 … 19 | 7.45 … 10.95 | deck top 2.95, parapet top 4.05 | 1 … 19 | -10.95 … -7.45 | 18 × 3.5 m | layout.js:106-112 |
| Shed stair | -2.6 … 1 | 8.95 … 10.95 | 0.15 … 2.95 | -2.6 … 1 | -10.95 … -8.95 | 12 risers, climbs east | layout.js:113 |
| El deck | -46 … 46 | -5.4 … 5.4 | underside 6.5, rail top 6.83 | -46 … 46 | -5.4 … 5.4 | structure continues to x ±96 as decor | layout.js:30-42, el.js:135 |
| Station mezzanine (fare control) | -46 … -39.4 | -4.1 … 4.1 | 3.9 … 6.3 | -46 … -39.4 | -4.1 … 4.1 | hung under the tracks | layout.js:46 |
| Station stair, south | -44.2 … -38.8 | 7.25 … 9.05 | 0.15 … 3.9 | -44.2 … -38.8 | -9.05 … -7.25 | sealed by a folding gate at its foot | layout.js:48 |
| Station stair, north | -44.2 … -38.8 | -9.05 … -7.25 | 0.15 … 3.9 | -44.2 … -38.8 | 7.25 … 9.05 | mirror image | layout.js:48 |
| Station platform, south | -46 … -29.5 | 3.75 … 7.05 | slab 7.55 … 7.75, canopy to 10.5 | -46 … -29.5 | -7.05 … -3.75 | runs on west to x -96 | el.js:249-266 |
| Station platform, north | -46 … -29.5 | -7.05 … -3.75 | slab 7.55 … 7.75, canopy to 10.5 | -46 … -29.5 | 3.75 … 7.05 | runs on west to x -96 | el.js:249-266 |
| Mid-block crossing | 23 … 26.6 | -6.8 … 6.8 | 0 | 23 … 26.6 | -6.8 … 6.8 | ladder bars | ground.js:13, 102-109 |
| Loading dock | 6.4 … 12.4 | 26 … 27.5 | 0 … 1.0 | 6.4 … 12.4 | -27.5 … -26 | steps x 5.4 … 6.4 | yards.js:355-359 |
| Hoist tower | 19.06 … 22 | 7.04 … 10.97 | 0.15 … 9.4 (standards to 9.9) | 19.06 … 22 | -10.97 … -7.04 | closes the south sidewalk | street.js:357-376 |
| Rolling scaffold A | -30.2 … -28.6 | -0.3 … 4.7 | deck 3.7, rail 4.75 | -30.2 … -28.6 | -4.7 … 0.3 | eastbound lane | street.js:61, 199-225 |
| Rolling scaffold B | -1.9 … -0.3 | -4.7 … 0.4 | deck 3.7, rail 4.75 | -1.9 … -0.3 | -0.4 … 4.7 | westbound lane, reel 1 arena | street.js:74 |
| Newsstand kiosk | -30.2 … -27.2 | -9.5 … -7.04 | 0.15 … 2.65 | -30.2 … -27.2 | 7.04 … 9.5 | shutter faces north | street.js:253 |
| Candy kiosk | -45.24 … -42.5 | 9.25 … 10.9 | 0.15 … 2.65 | -45.24 … -42.5 | -10.9 … -9.25 | shutter faces east | street.js:421 |
| Tyre cage | -20.4 … -18 | -10.96 … -8.6 | 0.15 … 2.4 | -20.4 … -18 | 8.6 … 10.96 | against the shop wall | street.js:255 |
| Produce stand | 11.4 … 15.2 | -10.98 … -8.6 | 0.15 … 2.5 | 11.4 … 15.2 | 8.6 … 10.98 | against the deli's front | street.js:281 |
| Utility dig pen | 17.8 … 21.2 | -9.2 … -7.04 | 0.15 … 2.35 (stack to 3.75) | 17.8 … 21.2 | 7.04 … 9.2 | at the north kerb | street.js:312 |
| Site shanty | -17.4 … -14.6 | 8.6 … 10.98 | 0.15 … 2.85 | -17.4 … -14.6 | -10.98 … -8.6 | against the record store's east end and the vacant lot's hoarding | street.js:335 |

### 2.5 Buildings

Besides the chop shop (2.6), the only building that can be entered, six solid buildings stand inside the bounds. Each
is one to three collider boxes from the ground to the top of its parapet, with the pockets (gangway, vestibule) simply
left out (`layout.js:116-128`, `buildings.js:430-441`).

#### 2.5.1 Summary

| id | Name = collider tag | Brick (catalogue colour) | Storeys | Roof y | Collider top | Street front | Collider boxes (x0, x1, z0, z1) | Source |
|---|---|---|---|---|---|---|---|---|
| `n1` | `tenement` | `brick_red` #7a3327 | 5 | 16.2 | 17.1 | faces south at z -11, x -46 … -26.2 | (-46, -26.2, -34, -11), (-26.2, -24, -34, -16) | `layout.js:122` |
| `n2` | `deli` | `brick_tan` #9a8262 | 3 | 10.0 | 10.9 | faces south at z -11, x 11 … 22 | (11, 22, -34, -11) | `layout.js:123` |
| `s1` | `station house` | `brick_brown` #5a4032 | 3 | 10.0 | 10.9 | faces north at z 11, x -46 … -30 | (-46, -30, 11, 34) | `layout.js:124` |
| `s2` | `pawn` | `brick_red` #7a3327 | 4 | 13.1 | 14.0 | faces north at z 11, x -30 … -16 | (-30, -24, 11, 34), (-24, -21.8, 13.4, 34), (-21.8, -16, 11, 34) | `layout.js:125` |
| `s3` | `S3` | `brick_tan` #9a8262 | 2 | 6.9 | 7.8 | faces north at z 11, x -4 … 22 | (-4, 22, 11, 26) | `layout.js:126` |
| `garages` | `garages` | `brick_painted` #b9b4a6 | 1 | 3.8 | 4.7 | faces north at z 31 (onto the rear lane), x -16 … 22 | (-16, 22, 31, 34) | `layout.js:127` |

Brick colours are the night catalogue values (`src/config/catalog.js:18-21`); the material library lightens masonry by
day. Every shop door is a recess 0.36 m deep carved out of the building's collider (door width × y 0.17 … 2.84), so a
round fired into a doorway reaches the door (`buildings.js:180-181, 433-440`, `carve` at `buildings.js:458-475`).

#### 2.5.2 The street-front kit (dimensions shared by all five walk-ups)

All heights are absolute web y; the sidewalk top is 0.15. Storefronts are built by `storefront()`
(`buildings.js:126-199`) between u0 and u1 along the front.

| Part | Dimensions | Material | Source |
|---|---|---|---|
| End piers | 0.32 wide at both ends of each shop, 0.10 proud, y 0.15 … 3.80 | the building's brick | `buildings.js:137-138` |
| Belt course | full shop width, y 3.66 … 3.84, 0.18 proud | concrete | `buildings.js:139` |
| Sign band | between the piers, y 2.92 … 3.66 (0.74 high), 0.13 proud | black paint (laundromat: dark metal) | `buildings.js:140` |
| Sign | centred on the band at y 3.29, 0.15 proud; width = min(clear width between piers - 0.5, 7.5), the deli 8.4; height 0.62 for one line, 0.74 with a sub-line | sign face, lit | `buildings.js:144-146` |
| Sign lamp hint | 0.7 m out from the wall at the shop's centre, y 3.25: kind `neon`, intensity 12 (neon signs) or 9 (box signs), range 9 m, colour = the sign's glow colour | | `buildings.js:147` |
| Display windows | both sides of the door; glass from sill 0.78 to head 2.84, 3.5 cm proud; 6 cm mullions so that no pane is wider than 1.9 m | `glass_store`, or `glass_lit_warm` / `glass_lit_cool` for a lit shop | `buildings.js:157-171` |
| Bulkhead (stall riser) | under the windows, y 0.15 … 0.78, 8 cm proud | white tile, dark metal or wood per shop | `buildings.js:165` |
| Sill and head rails | y 0.73 … 0.78 and 2.84 … 2.92, 12 cm proud, pier to pier | dark metal | `buildings.js:173-174` |
| Door | 1.25 wide in a recess 0.36 deep: brick reveals, 2 cm concrete threshold, glazed leaf (glass y 0.45 … 2.40), kick plate 0.15 … 0.45, solid transom 2.42 … 2.84, 8 cm stiles, chrome push bar at y 1.17 … 1.22; left edge at a + 0.2 + (b - a - 1.65) × `door`, with a = u0 + 0.32, b = u1 - 0.32 | dark metal, glass, chrome | `buildings.js:158-160, 178-190` |
| Interior light hint | a lit shop only: 1.5 m in front of the shop centre at y 1.9, kind `window`, intensity 10, range 9 | | `buildings.js:191` |
| Roll gate (shut shop) | ribbed steel between the piers, y 0.15 … 2.84, 5 … 11 cm proud; roller box y 2.84 … 2.92, 0.20 proud; guide rails 0.10 wide | `roll_gate`, dark metal | `buildings.js:149-155` |
| Awning | fabric lean-to fixed to the wall at y 2.90 … 3.00, projecting 1.35 m, front edge at y 2.52 with a 0.22 valance down to 2.30; runs pier to pier less 5 cm each side; two steel arms 3 × 4 cm at y 2.31. No collision | `fabric_awning` in the shop's colour | `buildings.js:194-198` |
| Bullet skins | bullet-only boxes over the sign band (0.15 deep), the gate (0.10) and the windows (0.06), so rounds stop on the drawn surface instead of the building box behind it | | `buildings.js:143, 155, 176-177` |

Above the shops:

| Part | Dimensions | Source |
|---|---|---|
| Window grid | bays 3.1 m wide, storeys 3.1 m high, one window per bay: opening 1.24 wide × 1.736 high, sill 0.60 above the storey's floor line. On a street front the floor lines are y 3.8, 6.9, 10.0, 13.1, so sills are at 4.40, 7.50, 10.60, 13.70 and heads at 6.14, 9.24, 12.34, 15.44 | `buildings.js:11, 15, 94-98`, `src/mats/layout.js:75-78` |
| Grid placement | n = floor(wall width / 3.1) bays, centred, leaving a solid pier of (width - 3.1 n) / 2 at each end: N1 6 bays (0.60 piers), N2 3 (0.85), S1 5 (0.25), S2 4 (0.80), S3 8 (0.60) | `buildings.js:96-97` |
| Window dressing | painted into the wall material: two-pane sash in a frame, stone or brick or steel lintel, sill, blinds in about 45 % and curtains in 30 % of windows, a window air-conditioner in about 16 % of upper windows; 24 % of windows lit at night (dark reflective glass by day). The three painted layouts are drawn out in `06-look-fx.md` 2.7 | `src/mats/layout.js:104-116`, `buildings.js:15` |
| Side and back walls | the same grid counted from the ground (floor lines y 0, 3.1, 6.2, 9.3, 12.4): the ground row has barred windows and, once per four bays, a door 1.1 × 2.3 in place of a window | `buildings.js:14, 97`, `src/mats/layout.js:86-93` |
| Cornice | on every street front at roof height h: top band y h + 0.05 … h + 0.38 projecting 0.42, lower band y h - 0.18 … h + 0.05 projecting 0.24, dentils 0.22 wide × 0.24 high × 0.20 deep every 0.62 m from u0 + 0.3 (N1 32, N2 17, S1 26, S2 22, S3 42). No collision | `buildings.js:212-218` |
| Roof and parapet | flat roof at h; parapet 0.30 thick × 0.90 high all round in the building's brick, concrete coping 7 cm thick overhanging 4 cm | `buildings.js:202-209` |
| Fire escape | catalogue prop `fire_escape` (3.0 wide × 3.0 high × 1.1 deep), one balcony per storey above the shops, landing at y 3.8 + (k - 1) × 3.1 + 0.25 = 4.05, 7.15, 10.25, 13.35. No collision | `buildings.js:221-223` |
| Service door | concrete surround 1.24 wide × 2.20 high, 5 cm proud; steel leaf 1.00 × 2.10; chrome handle; a caged lamp over it (bracket at y 2.42 … 2.50, lens 0.16 × 0.12 × 0.12 at y 2.30 … 2.42); lamp hint 0.4 m out at y 2.30: kind `street`, intensity 14, range 8, priority 3, colour warm #ffc98a or cool #cfe4ff | `buildings.js:226-234` |

#### 2.5.3 The ten storefronts

Names come from `src/config/text.js:208-222`. "Door x" is the door opening and its centre. A lit shop has a glowing
window group at night; by day all shop glass is dark and reflective.

| # | Sign (sub-line) | Building, face, x range (width) | Sign style and colours | Sign w × h | Door x (centre) | Glass | Bulkhead | Awning | Source |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `24 HR LAUNDROMAT` | N1 south, -46 … -37.2 (8.8) | lit box: ground #0d3550, letters #f4f2ec, glow #cfe4ff; band dark metal | 7.5 × 0.62 | -40.27 … -39.02 (-39.65) | lit, cool | white tile | none | `buildings.js:252` |
| 2 | `CROWN & FADE BARBER` | N1 south, -34.4 … -26.2 (8.2) | neon #ff3030 | 7.06 × 0.62 | -32.99 … -31.74 (-32.37) | dark | white tile | navy #1c2f5a | `buildings.js:261` |
| 3 | `HOLLIS DELI & GROCERY` (`OPEN 24 HRS  ·  COLD CUTS  ·  COFFEE  ·  LOTTO`) | N2 south, 11 … 22 (11.0) | lit box: ground #f2c21a, letters #8a1410, glow #ffd24a | 8.4 × 0.74 | 15.88 … 17.13 (16.50) | lit, warm | dark metal | green #1f5a3a | `buildings.js:297` |
| 4 | `CHECKS CASHED` (`MONEY ORDERS  ·  BILLS PAID`) | S1 north, -46 … -38.3 (7.7) | neon #55ff8a | 6.56 × 0.74 | -43.86 … -42.61 (-43.23) | dark | dark metal | none | `buildings.js:320` |
| 5 | `99¢ PIZZA` (`SLICES ALL NIGHT`) | S1 north, -38.3 … -30 (8.3) | lit box: ground #b3261e, letters #fff1d0, glow #ff5a3a | 7.16 × 0.74 | -33.27 … -32.02 (-32.65) | lit, warm | white tile | red #b3261e | `buildings.js:321` |
| 6 | `PAWN & GOLD` (`WE BUY GOLD  ·  LOANS`) | S2 north, -30 … -24 (6.0) | neon #f6c21a | 4.86 × 0.74 | -26.14 … -24.89 (-25.52) | dark | dark metal | none | `buildings.js:337` |
| 7 | `TAPES · RECORDS · CDs` | S2 north, -21.8 … -16 (5.8) | neon #35e0ff | 4.66 × 0.62 | -20.93 … -19.68 (-20.30) | dark | wood | none | `buildings.js:338` |
| 8 | `GOLDEN BIRD CHICKEN` (`FRIED  ·  WINGS  ·  BISCUITS`) | S3 north, -4 … 5 (9.0) | lit box: ground #f2c21a, letters #b3261e, glow #ffc84a | 7.5 × 0.74 | -1.80 … -0.55 (-1.18) | lit, warm | white tile | none | `buildings.js:377` |
| 9 | `WINES & LIQUORS` | S3 north, 5 … 13.5 (8.5) | neon #ff3030 | 7.36 × 0.62 | 8.63 … 9.88 (9.25) | dark | dark metal | none | `buildings.js:378` |
| 10 | `LUCKY NAILS` (`MANICURE  ·  PEDICURE`) | S3 north, 13.5 … 22 (8.5) | neon #ff3d9a | 7.36 × 0.74 | none: roll gate down | none | none | none | `buildings.js:379` |

Shops 8 to 10 stand under the sidewalk shed (2.9.3), which hides their signs from the street; their names hang again
as banners on the shed's parapet.

#### 2.5.4 Building by building

**N1, the tenement** (`buildings.js:248-288`), roof at 16.2:

- Front: laundromat, the residents' entrance (x -37.2 … -34.4), barber; four storeys of windows above (y 3.8 … 16.2);
  cornice; a stack of four fire-escape balconies centred on x -30.6.
- Residents' entrance: brick panel 0.10 proud; a stoop of two concrete steps (first 1.8 wide × 0.16 high reaching 0.75 m
  out of the wall, second 1.4 wide × 0.16 high reaching 0.45 m); a panelled timber door 1.0 wide, y 0.47 … 2.50; a lit
  transom y 2.55 … 3.00; a concrete lintel y 3.00 … 3.20; lamp hint (-35.8, 2.8, -10.5), `window`, #ffc98a, intensity 6,
  range 6. The stoop has no collider (3.8).
- Barber pole beside the barber's door at (x -34.05, z -10.78): a glowing white cylinder r 0.075 from y 1.55 to 2.25
  between two chrome caps (r 0.09, 0.08 high).
- The gangway: a pocket x -26.2 … -24, z -16 … -11 (2.2 m wide, 5 m deep) between the tenement and the shop. Bare
  brick on its west wall and its back wall, a service door in the back wall at x -25.1 (warm lamp). Ground spawn G1
  stands in it.
- East wall above the shop roof (the wall at x -24, z -34 … -16, y 6.0 … 16.2): blind brick carrying a painted
  advert, `V&R AUTO BODY` / `COLLISION  ·  FRAME  ·  PAINT`, 12 × 3.2 m, letters #e9e2cf on #1d2f3f, unlit, centred
  at z -24.5, y 11.4.
- Roof: `water_tower` at (-40, -24), `ac_unit` at (-31, -15) and (-33.5, -27), a brick stair bulkhead x -37 … -34,
  z -20 … -16.5, y 16.2 … 18.8. On every roof the plant has no collision; only the bulkheads do (tag `bulkhead`).

**N2, the deli** (`buildings.js:293-311`), roof at 10.0:

- Front: one shop 11 m wide with a green awning; two storeys of windows; cornice.
- West wall (x 11, the alley side, z -31.4 … -11): windows from the ground; two fire-escape balconies centred on
  z -20.5; a service door at z -15.5 (warm lamp).
- East wall (x 22, the cut, z -33.5 … -11): windows from the ground; a service door at z -27.5 (cool lamp).
- Roof: `ac_unit` at (14, -15) and (18.5, -22), `water_tower` at (16.5, -29).

**S1, the station house block** (`buildings.js:316-328`), roof at 10.0:

- Front: cheque casher and pizza counter (red awning); two storeys of windows; cornice; two fire-escape balconies
  centred on x -42.5. Roof: `ac_unit` at (-41, 15) and (-34, 22).

**S2, pawn shop and record store** (`buildings.js:333-368`), roof at 13.1:

- Front: pawn shop, a shared vestibule, record store; three storeys of windows; cornice; three fire-escape balconies
  centred on x -27.
- The vestibule: a pocket x -24 … -21.8, z 11 … 13.4 (2.2 wide, 2.4 deep) with a floor at sidewalk height
  (`layout.js:147`). Both side walls are display windows (bulkhead to 0.78, glass 0.78 … 2.70, head rail to 2.78); the
  back wall is brick with a roll gate 1.4 wide × 2.25 high (x -23.6 … -22.2); a concrete soffit closes it at
  y 2.78 … 3.80 (solid); a recessed lamp in the soffit, hint (-22.9, 2.6, 12.2), `window`, #ffc98a, intensity 7,
  range 6. Ground spawn G8 stands in it.
- West wall above the station house (x -30, z 11 … 34, y 10.0 … 13.1): bare brick.
- East wall (x -16): bare brick over z 11 … 31 from the ground to 13.1 and over z 31 … 34 above the garages. It is the
  **mural wall** of the vacant lot (2.10.4).
- Roof: `water_tower` at (-23, 24), `ac_unit` at (-27, 16), bulkhead x -21 … -18, z 27 … 30.5, y 13.1 … 15.7.

**S3, chicken, liquor, nails** (`buildings.js:373-399`), roof at 6.9:

- Front: three shops (the nail salon shuttered); one storey of windows; cornice. No fire escape.
- West wall (x -4, the vacant lot, z 11 … 26): windows from the ground; a service door at z 22.8 (warm lamp).
- South wall (z 26, the rear lane, x -4 … 22): windows from the ground; service doors at x -1.6 (warm) and 17.4 (cool);
  a delivery shutter x 13.2 … 15.8, y 0 … 2.70 under a 0.20 header; the loading dock and its shutter (2.10.5).
- East wall (x 22, the parking lot, z 11 … 26): windows from the ground; a painted sign `PARK` / `24 HR  ·  PAY AT
  BOOTH`, 5 × 1.6 m, letters #f4f2ec on #1f4f9a, unlit, centred at z 18.5, y 2.3 (covering part of the ground row).
- Roof: `ac_unit` at (1, 15), (9.5, 22) and (17, 14.5); bulkhead x 11.5 … 14.5, z 19 … 22.5, y 6.9 … 9.4.

**The garages** (`buildings.js:404-426`), roof at 3.8, painted brick, on the south side of the rear lane:

- Eight roll doors 3.4 wide × 2.75 high centred on x -13.6, -9.2, -4.8, -0.4, 4.0, 8.4, 12.8, 17.2 (pitch 4.4 m),
  each under a concrete lintel 3.7 wide (y 2.75 … 3.00, 0.12 proud) and a stencilled number `41` … `48` (0.7 × 0.42,
  #e6e4dc) at y 3.3.
- A caged wall lamp to the right of doors 2, 5 and 8: lamp hints (-7.1, 3.0, 30.6), (6.1, 3.0, 30.6), (19.3, 3.0,
  30.6), kind `street`, #ffb45e, intensity 18, range 10, priority 4.
- A concrete coping along the front (y 3.8 … 4.1); the gable end at x 22 (z 31 … 34) closes the lot's south-west
  corner.

#### 2.5.5 The neighbours' backs

Where no building of the block stands on the edge, the back of a neighbouring building just outside the bounds closes
it: a solid slab 3 m deep with a window wall on the side that looks into the block, bare brick on the other three
sides, a brick band and a concrete coping on top (`buildings.js:482-516`). Collider tag `backs`, from the ground to
roof + 0.9.

| # | Closes | web x | web z | Storeys, roof y (collider top) | Brick | Window wall | Windows start at y | Source |
|---|---|---|---|---|---|---|---|---|
| 1 | north, behind the chop shop | -24 … 6 | -37 … -31 | 4, 13.1 (14.0) | `brick_brown` | faces south at z -31 | 6.5 (the shop's parapet hides it below 6.9) | `buildings.js:507` |
| 2 | north, across the end of the alley | 6 … 11 | -37 … -34 | 4, 13.1 (14.0) | `brick_brown` | faces south at z -34 | 0 | `buildings.js:508` |
| 3 | north, behind the cut and the cage | 22 … 49 | -37 … -33.5 | 3, 10.0 (10.9) | `brick_red` | faces south at z -33.5 | 0 | `buildings.js:509` |
| 4 | east, beside the cage | 45.8 … 49 | -33.5 … -12.2 | 3, 10.0 (10.9) | `brick_tan` | faces west at x 45.8 | 0 | `buildings.js:511` |
| 5 | east, beside the parking lot | 46 … 49 | 11 … 37 | 2, 6.9 (7.8) | `brick_brown` | faces west at x 46 | 0 | `buildings.js:512` |
| 6 | south, behind the garages | -16 … 22 | 34 … 37 | 4, 13.1 (14.0) | `brick_red` | faces north at z 34 | 3.8 (above the garages) | `buildings.js:514` |
| 7 | south, behind the parking lot | 22 … 46 | 34 … 37 | 3, 10.0 (10.9) | `brick_tan` | faces north at z 34 | 0 | `buildings.js:515` |

### 2.6 The chop shop: V&R AUTO BODY

A one-storey cinder-block garage on the north side of the avenue, the block's only interior
(`level.interiorBoxes[0]`). All of `shop.js`; numbers from `layout.js:51-78`.

#### 2.6.1 Shell

| Part | Geometry (web) | Source |
|---|---|---|
| Outer footprint | x -24 … 6, z -31 … -11 (30 × 20 m); the south wall is on the building line | `layout.js:52-55` |
| Walls | painted cinder block (#8a8880), 0.40 thick, from the ground to the parapet top at 6.9; collider tag `shop-wall` | `shop.js:11, 31-46`, `layout.js:56, 59` |
| Roof slab | y 6.0 … 6.3 (eave = underside = 6.0), solid, tag `shop-roof` | `shop.js:68`, `layout.js:57-58` |
| Parapet | the walls stand 0.6 above the roof top; concrete coping 8 cm on the south and east walls | `shop.js:324-325` |
| Clear interior | x -23.6 … 5.6, z -30.6 … -11.4, floor to 6.0 | `shop.js:19-22` |
| Interior box | min (-24, 0, -31), max (6, 6.3, -11): what `interiorAt` and the Buzzards' doorway search use | `shop.js:333` |
| Floor | sealed dark concrete (`concrete_dark` #44444a) running out through the three door openings; reports `concrete` | `shop.js:51-54`, `layout.js:197` |
| Floor paint | three yellow bay outlines (lines 0.10 wide: the north edge and both sides, open toward the avenue): x -21.6 … -16.8, z -20.4 … -14.2 (west lift); x -3.4 … 0.8, z -22.6 … -16.6 (east lift); x -14.6 … -9.4, z -18.4 … -12.4 (the car on stands) | `shop.js:55-59` |
| Floor drain | steel grate 0.7 × 0.7 at x -5.2 … -4.5, z -17.3 … -16.6 | `shop.js:60` |
| Oil and grime | eight floor decals at (-19.2, -17.3), (-12.3, -15.6), (-1.3, -19.6), (-9, -24), (-4.5, -13.2), (2.8, -24.5), (-15.5, -21.8), (-7.6, -27.8) | `shop.js:61-65` |
| Dado | inside faces painted dark teal (#27414b) from the floor to 1.35 with a yellow stripe 1.35 … 1.42; on the north wall only east of x -15.4, on the west wall only south of z -25 (not behind the mezzanine) | `shop.js:92-106` |

#### 2.6.2 Openings

| Opening | Wall | Position | Clear size (w × h) | Notes | Source |
|---|---|---|---|---|---|
| Roll-up door | south | x -15 … -9 | 6.0 × 4.3 | rolled up: 0.55 m of slats still hanging under a bottom bar, roller housing 6.2 × 0.42 × 0.34 inside above the head, guide rails at both jambs | `layout.js:60`, `shop.js:123-128` |
| Second bay | south | x -3.2 … 0.6 | 3.8 × 3.5 | the same door, smaller | `layout.js:61` |
| Side door | east (into the alley) | z -23.1 … -21.1 | 2.0 × 2.5 | steel leaf 1.9 × 2.42 swung back flat against the alley wall (x 6 … 6.06, z -21.1 … -19.2); frame head at 2.42 … 2.50 | `layout.js:62`, `shop.js:131-132` |
| Extractor fan | east, over the side door | z -22.7 … -21.5, y 3.9 … 5.1 | 1.2 × 1.2 | wire guards (five bars) on both faces; four blades 0.5 × 0.2 at radius 0.3, pitched 0.5 rad, spinning about the wall's normal at 1.7 rad/s; the opening is solid to rounds and walkers | `shop.js:42-48, 138-156` |
| Skylights (4) | roof | centred on (-18.5, -19.5), (-9, -24.5), (-9, -15.5), (0.5, -20.5) | 2.4 × 3.4 each | glass with a steel grid (bars at x -1.2, 0, +1.2 and z -1.7, 0, +1.7); a galvanised kerb 2.7 × 3.7 × 0.3 on the roof with dark glass on top. The roof collider is continuous: nothing passes a skylight | `layout.js:66-71`, `shop.js:71-79` |

A yellow bollard (catalogue `bollard`, 0.2 × 1.0) stands 0.35 m in front of the wall 0.45 m outside each door jamb:
x -15.45, -8.55, -3.65, 1.05 at z -10.65 (`shop.js:128`).

#### 2.6.3 Roof steel and work lights

| Part | Geometry | Source |
|---|---|---|
| Roof beams | four, spanning north–south at x -18, -12, -6, 0: web 0.22 × 0.45 deep (y 5.55 … 6.0) with a 0.40 × 0.05 bottom flange | `shop.js:81-84` |
| Purlins | four, running east–west at z -27, -22.6, -18.2, -13.8: 0.12 × 0.16 (y 5.84 … 6.0) | `shop.js:85` |
| Columns | two, at (-18, -21) and (-6, -21): steel 0.28 × 0.28, floor to 5.55, with a yellow painted sleeve to 1.2; solid, tag `shop-column` | `shop.js:86-89` |
| Work lights (4) | high-bay lamps at (-18.2, -17.2), (-9.2, -22.4), (-9.2, -14.6), (0.6, -21.2): a 4 cm conduit drop from the purlin line down to 5.32, a spun shade (open cone, radius 0.36 at y 5.08 to 0.11 at 5.34), a glowing disc of radius 0.24 at y 5.06 … 5.10 (#ffd9a8). Lamp hints at y 5.0: kind `work`, colour #ffc48a, intensity 34, range 13, aimed down, priority 10 (the highest in the level) | `layout.js:72-77`, `shop.js:289-296` |

#### 2.6.4 Mezzanine, office and stair (north-west corner)

| Part | Geometry | Source |
|---|---|---|
| Deck | x -23.6 … -15.4, z -30.6 … -25, top at y 2.8: steel plate 0.12 thick; yellow edge beams 0.10 × 0.30 on its south and east edges; solid (tag `mezzanine`, surface metal) | `layout.js:64`, `shop.js:162-167` |
| Posts | four steel posts 0.16 × 0.16, floor to 2.5, at (-15.5, -25.1), (-19.5, -25.1), (-23.5, -25.1), (-15.5, -30.5); solid | `shop.js:168-170` |
| Office | the back of the deck, x -23.6 … -17.4, z -30.6 … -27.1 (6.2 × 3.5 m), walls to y 5.3: a timber panel (#6b5a43) 0.95 high and 0.10 thick, then a band of glass y 3.80 … 5.00 in steel mullions, then a 0.30 steel head. Front wall on z -27.1 from x -23.6 to -19; side wall on x -17.4 | `shop.js:172-192` |
| Office doorway | in the front wall, x -19 … -17.4 (1.6 wide), 2.1 high, no door leaf; solid header above it | `layout.js:64`, `shop.js:194-196` |
| Office glass | player-only collider from y 3.75 to 5.3: rounds pass, walkers do not; the timber panel under it stops both (cover on the deck) | `shop.js:182-186` |
| Office roof | slab y 5.3 … 5.4 over the office; solid | `shop.js:197` |
| Office contents | `workbench` at (-21.2, -29.9), `tool_chest` at (-23.1, -28.2) turned 90°, a steel safe 0.8 × 0.8 × 0.85 at x -18.5 … -17.7, z -30.4 … -29.6 with a chrome handle (solid, tag `safe`), a ceiling tube 1.6 m long at y 5.26; lamp hint (-20.6, 5.0, -28.8), `work`, #fff1d0, intensity 14, range 8, priority 5; posters on the north and west walls | `shop.js:199-206` |
| Railings | yellow tube, top rail at y 3.85 and mid rail at 3.35, posts about every 1.4 m: along the deck's south edge (x -23.6 … -15.4) and its east edge from z -30.6 to -26.3 (the rest of that edge is the stair head). Player-only colliders 8 cm thick, y 2.8 … 3.85 | `shop.js:209-222` |
| Stair | from the deck's east edge down to the floor, x -15.4 (top) … -12.04 (foot), z -26.3 … -25 (1.3 m wide): 12 open steel treads, rise 0.233, going 0.28 (39.8°); two steel stringers 0.06 × 0.26; yellow handrails 1.0 above the nosings on both sides. Each tread has a solid collider from the floor to its top (tag `shop-stair`), so the flight is a wall from the sides and a walkable ramp of low ledges from its foot; a player-only wall on each side from the floor to 3.85 | `layout.js:65`, `shop.js:224-235` |
| Under the deck | `tire_stack` × 2, `oil_drum` × 2, `pallet_stack`, `cardboard_boxes`, `compressor` (2.15); a wall tube 1.2 m long at y 2.62 on the north wall, hint (-20, 2.4, -30.2), `work`, #cfe4ff, intensity 8, range 6, priority 3 | `shop.js:237-246` |

#### 2.6.5 Outside

| Part | Geometry | Source |
|---|---|---|
| Fascia | corrugated steel band painted #1a2b3a across the avenue front, x -23.7 … 5.7, y 4.75 … 6.05, 0.10 proud | `shop.js:303` |
| Main sign | `V&R AUTO BODY`, lit box 8 × 1.05, yellow #f6c21a on #101113, centred over the roll door at (-12, 5.4); lamp hint (-12, 5.4, -10.2), `neon`, #f6c21a, intensity 14, range 10 | `shop.js:304-306` |
| Painted signs | `TIRES  ·  BRAKES  ·  EXHAUST` 5.4 × 0.6 over the second bay at (-1.3, 5.4); `INSPECTIONS  ·  24 HR TOWING` 5.6 × 0.6 at (-19.6, 5.4); letters #e9e2cf on the fascia colour, unlit | `shop.js:307-310` |
| Wall stencil | `FLAT FIX` / `NO APPOINTMENT`, 2.6 × 1.1, #e6e4dc, on the block wall between the doors at (-6.1, 2.6) | `shop.js:311-312` |
| Gooseneck lamps | three over the fascia at x -21.5, -12, -1.3: a stem up the wall from 6.1 to 6.5, an arm reaching 0.72 m out, a shade 0.34 × 0.34 × 0.12 with a lens under it at y 6.31; lamp hints (x, 6.2, -10.28), `street`, #ffc48a, intensity 16, range 10, aimed down, priority 4 | `shop.js:317-323` |
| Side-door lamp | a caged lamp on the alley face over the side door; hint (6.5, 2.85, -22.1), `street`, #ffc48a, intensity 16, range 9, priority 4 | `shop.js:133-136` |
| EXIT sign | inside, over the side door: lit box 0.7 × 0.3, #fff1d0 on #7a1410, at (5.57, 2.85, -22.1); hint `neon`, #ff3030, intensity 4, range 4, priority 2 | `shop.js:114-116` |
| Roof plant | `ac_unit` at (-15, -27) and (2.5, -14.5) on the roof at y 6.3; a galvanised vent stack r 0.22, y 6.3 … 7.6, at (-3, -27.5) | `shop.js:326-328` |
| Paper and tags | posters and graffiti inside and on the front: see 2.16 | `shop.js:107-113, 313-315` |

#### 2.6.6 On the floor

Catalogue props; exact placements are in 2.15 (`shop.js:253-287`).

- **West lift**: a two-post `car_lift` at (-19.2, -17.3) turned 90° (posts 3.5 m high at x -20.6 and -17.8, the car
  axis north to south), arms up, carrying a green sedan raised to y 1.95: the one car in the air. The raised car is
  kept out of the nav grid, so the bay under it stays walkable for the AI.
- **East lift**: a second `car_lift` at (-1.3, -19.6), arms up and empty, with a white sedan standing on the floor
  between its posts, nose south.
- **Car on stands**: a stripped `car_on_stands` at (-12.2, -15.4), nose a little west of north, just inside the roll
  door.
- **The reel 2 arena**: the case at (-9.5, -21.5) with low cover on every side at 2 to 5 m: two tool chests
  (-7.1, -19.5) and (-12.6, -23.1), two oil drums (-12.1, -19.4) and (-11.4, -20.1), two tyre stacks (-6.5, -23.4) and
  (-7.3, -24.1), an engine hoist (-9.9, -25.3), a crate (-13.4, -20.9), milk crates (-9.2, -18.2). The roof column at
  (-6, -21) is the one piece of hard cover; a welding rack stands at the foot of the mezzanine stair (-14.3, -23.4).
- **Along the walls**: on the north wall a workbench, a tool chest and a shelf rack, with a propane tank at the bench
  (-3.4, -30.1) and a pallet stack and boxes in the north-east corner; three shelf racks on the east wall (two north
  of the side door, one south of it) and a vending machine near the front; against the south wall two tyre stacks
  and a drum between the two doors, a workbench west of the roll door and a compressor east of the second bay; a
  shelf rack on the west wall; an engine hoist just inside the front wall west of the roll door; a crate by the east
  lift; a welding rack in the south-west "welding corner" (-20.4, -13.6) and another by the east lift (3.4, -17.6).

### 2.7 The El and the 188 St station

The elevated line over the avenue: everything is `steel_el` (#1f2a26, a dark green-black painted steel) except the
timber ties and planks and the dark rails. All of `el.js`; numbers from `layout.js:29-49`. Only the columns, the
girders, the deck, the station mezzanine, its bridges, stairs and platforms collide.

#### 2.7.1 Structure

Ten bents (column pairs with a cross girder) stand inside the block at x -45, -35, -25, -15, -5, 5, 15, 25, 35, 45
(10 m spacing), columns at z -4.6 and +4.6, between the travel lanes and the parking lanes. Eight simpler bents carry
the line on past both closures at x ±55, ±65, ±75, ±85 (no batten plates, braces or stiffeners, no shadows); the
girders, rails and walkways run from x -96 to 96 (`layout.js:35-36`, `el.js:60-64`).

| Member | Section | Position | Source |
|---|---|---|---|
| Footing | concrete block 1.04 × 1.04 × 0.26 | under each column | `el.js:29` |
| Flared base | four-sided frustum, 0.89 m square at y 0.26 tapering to 0.51 m square at 1.20 | | `el.js:31` |
| Column shaft | built-up H: two flange plates 0.48 wide × 0.06 thick, 0.50 apart over all, facing east and west, joined by a web 0.38 × 0.10; y 1.20 … 5.30 | | `el.js:33-35` |
| Cap plate | 0.62 × 0.62 × 0.22, y 5.08 … 5.30 | | `el.js:36` |
| Batten plates | 0.40 wide × 0.30 high × 0.04, on the north and south faces between the flanges, bottoms at y 1.55, 2.50, 3.45, 4.40 (8 per column) | | `el.js:39-41` |
| Knee brace, transverse | bar 0.16 × 0.14 from (y 4.15, 0.24 m inboard of the column centre) up to (y 5.40, 1.45 m inboard), toward the middle of the street | one per column | `el.js:43` |
| Knee braces, longitudinal | bars 0.14 × 0.14 from (x ± 0.25, y 4.35) to (x ± 1.35, y 5.56) | two per column | `el.js:44` |
| **Column collider** | box 0.64 × 0.64, y 0 … 5.30, surface metal, tag `el-column` | 20 in the block + 16 outside | `el.js:46` |
| Cross girder | plate girder across the street: web 0.40 thick × 1.20 deep (y 5.30 … 6.50), z -5.05 … 5.05 (10.1 m); bottom flange plate 0.66 × 0.07; nine stiffeners 0.54 × 0.06 at z -4, -3, … 4. Collider x ± 0.3, tag `el-girder` | at every bent | `el.js:52-57` |
| Longitudinal girders | web 0.34 thick × 1.00 deep (y 5.50 … 6.50) over each column row (z ±4.6); bottom flange 0.58 × 0.07; stiffeners 0.06 × 0.50 every 2.5 m (three per bay). Collider 0.40 wide, tag `el-girder` | continuous | `el.js:70-77` |
| Deck fascia | plate 0.10 × 0.57 (y 6.15 … 6.72) along each deck edge, z ±5.3 … ±5.4, on cantilevers 0.10 × 0.25 (y 6.25 … 6.50) from the girder every 2.5 m | continuous | `el.js:78-83` |
| Rail stringers | 0.20 wide × 0.58 deep (y 5.92 … 6.50) under each of the four rails, z ±1.3825 and ±2.8175 | continuous | `el.js:86-89` |
| Mid-span cross frames | 0.14 × 0.40 (y 6.02 … 6.42) across z -4.6 … 4.6 at the middle of each span (x -40, -30, … 40) | 9 | `el.js:92-96` |
| Lateral bracing | diagonals 0.09 × 0.09 at y 6.30, zigzagging between the girder and stringer lines; six per span | 54 | `el.js:97-101` |
| Ties | creosoted timber (#2b221b) 0.22 wide × 0.18 deep × 2.70 long, y 6.50 … 6.68 | under each track at 0.56 m pitch (gaps 0.34): 164 per track inside the block; past the closures one slab stands in for them | `el.js:14, 109-116` |
| Running rails | 0.07 wide × 0.15 high (y 6.68 … 6.83) | standard gauge 1.435: z ±1.3825 and ±2.8175 (track centre lines z -2.1 and +2.1) | `layout.js:38-41`, `el.js:117-120` |
| Third rails | 0.08 × 0.11, under a timber cover board 0.26 × 0.03 at y 6.85 … 6.88 | the outer side of each track, z ±3.22 | `el.js:121-124` |
| Walkways | planks (#4a3c2c) 0.06 thick, y 6.58 … 6.64 | between the tracks (z -0.6 … 0.6) and along both edges (z ±3.9 … ±5.3) | `el.js:126-130` |
| Handrails | two rails 0.05 × 0.05 at y 7.25 and 7.75 on posts 0.06 × 0.06 every 2.5 m | z ±5.35 | `el.js:131-133` |
| **Deck collider** | one box, y 6.50 … 6.90, surface metal, tag `el-deck`, not in the nav grid | x -46 … 46, z -5.4 … 5.4 | `el.js:135` |
| Lamps under the deck | sodium lamp: a 5 cm drop from y 6.02 to 5.74, a shade (open cone, radius 0.30 at y 5.58 to 0.09 at 5.76), a glowing disc r 0.20 at y 5.56 … 5.60. Lamp hints at y 5.5: kind `el`, #ffb45e, intensity 30, range 13, aimed down, priority 5 | nine, one per span at x -40, -30, … 40, alternating z +2.1, -2.1, +2.1 … (over the eastbound lane first) | `el.js:141-149` |

`level.el` = `{y: 6.5, minX: -46, maxX: 46, minZ: -5.4, maxZ: 5.4, deckTop: 6.83, tracks: [-2.1, 2.1]}`
(`el.js:153`): the deck's underside, its plan, the rail top and the two track centre lines. The train (`06-look-fx.md`
2.20) runs on those tracks; the Buzzards plan their flight round this volume and never spawn above it.

Headroom over the roadway: 5.30 under the cross girders, 5.50 under the longitudinal girders, 5.92 under the stringers,
6.50 under the ties; the knee braces start at 4.15 beside the columns. The lowest thing over the street is the station
mezzanine at 3.90.

#### 2.7.2 The station (sealed)

"188 ST", at the west end. A fare-control mezzanine hangs under the tracks; a covered bridge leads from each side of
it out over the parking lane to the head of a covered stair that comes down eastward onto each sidewalk; the platforms
are above. It is scenery: a folding gate closes the foot of each stair and coarse colliders fill the flights. The
south stair is mirrored on the north side (negate z). Painted sheet steel is `corrugated` tinted #2f4038, roofing
#1c2224 (`el.js:157-281`).

| Part | Geometry (south side; mirror for north) | Source |
|---|---|---|
| Mezzanine | box x -46 … -39.4, z -4.1 … 4.1: a steel floor 0.16 thick at y 3.90, sheet-steel walls to 6.30. A band of windows y 4.95 … 5.75: six panes 1.1 wide on the east face (the 2nd and 5th lit warm), four panes 1.2 wide on each street side (the 3rd lit); steel trim above and below the east band. Collider y 3.9 … 6.5, tag `station` | `layout.js:46`, `el.js:165-182` |
| Name plate | `188 ST` / `ELEVATED  ·  CLOSED 1 AM – 5 AM`, enamel plate 4.6 × 0.82 on the east face, centre (-39.37, 4.47, 0); lamp hint (-38.8, 5.3, 0), `window`, #ffc98a, intensity 8, range 7 | `el.js:179-181` |
| Bridge | x -45.9 … -44.2 (1.7 wide), from the mezzanine (z 4.1) out to z 9.05: steel floor at 3.90 … 4.06, side panels to 5.15, a roof at 6.20 … 6.30 overhanging 0.15, an end wall. Collider y 3.9 … 6.3 | `layout.js:47`, `el.js:191-198` |
| Posts under the stair head | two steel posts 0.14 × 0.14 at x -45.9 and -44.2, z 8.91 … 9.05, sidewalk to 3.90; solid | `el.js:199-203` |
| Stair | x -44.2 (top, y 3.90) … -38.8 (foot, y 0.15), z 7.25 … 9.05 (1.8 wide): 20 risers of 0.1875 with 0.27 goings (34.8°), closed steel treads | `layout.js:48`, `el.js:206` |
| Balustrades | sheet-steel panels 0.08 thick on both sides following the slope: bottom edge from (x -38.55, y 0.15) to (-44.2, 3.40), top edge from (-38.55, 1.20) to (-44.2, 5.15) | `el.js:209-217` |
| Trestle | at mid-flight (x -41.5): two posts 0.12 × 0.12 to y 1.83 and a cross beam under the flight | `el.js:218-220` |
| Stair roof | a sloping roof 0.08 thick from (x -38.2, y 2.65) up to (-44.3, 6.30), 0.12 wider than the stair on each side | `el.js:221-227` |
| Portal | two posts 0.12 × 0.12 × 2.5 high at the foot (x -38.54, z 7.25 and 9.05), each topped by a short stem and a green globe r 0.17 at y 3.15 (#55ff8a); lamp hint (-38.54, 3.15, 8.15), `neon`, intensity 6, range 6, priority 3 | `el.js:228-234` |
| Folding gate | `roll_gate` across the foot at x -38.63, y 0.15 … 2.65; collider x -38.75 … -38.5, y 0.15 … 2.75; plate `188 ST` / `STATION CLOSED`, 1.5 × 0.42, at (-38.46, 2.39, 8.15) | `el.js:235-239` |
| Flight colliders | five boxes of 1.08 m along the flight, from the sidewalk to 1.1 m above the slope (tops 4.25, 3.50, 2.75, 2.00, 1.25), z 7.2 … 9.1 | `el.js:240-246` |
| Platform | concrete slab y 7.55 … 7.75, z 3.75 … 7.05, from x -96 to -29.5; a yellow edge strip 0.30 wide on the track side; an end plate 1.1 high at x -29.5 | `el.js:249-253, 273` |
| Windscreen | sheet-steel wall on the street edge (z 7.0 … 7.05), y 7.75 … 10.15, to x -31, with six window panes 1.7 × 0.75 centred at y 9.05, x -45.2, -42.8, -40.4, -38.0, -35.6, -33.2 (all lit cool) | `el.js:254-259` |
| Canopy | a roof sloping from y 10.42 … 10.50 over the track edge (z 3.9) down to 10.15 … 10.22 past the windscreen (z 7.25), to x -30.5 | `el.js:260-266` |
| Canopy posts and brackets | at x -85, -75, -65, -55, -45, -35: a post 0.14 × 0.14 at z 6.75 (y 7.75 … 10.20), a cantilever beam under the slab (y 7.40 … 7.55, z 3.8 … 7.0) and a knee brace from (y 6.2, z 4.8) to (y 7.5, z 6.9) | `el.js:267-271` |
| Platform tubes | fluorescent tubes 1.2 m long under the canopy at x -43.5, -38, -32.5, z 5.4, y 10.05; lamp hints (x, 9.9, ±5.4), kind `el`, #cfe4ff, intensity 10, range 9, priority 2 | `el.js:274-277` |
| Platform colliders | the slab (x -46 … -29.5) and the windscreen (x -46 … -31, y 7.75 … 10.2), inside the bounds only | `el.js:278-279` |

### 2.8 The avenue: lanes, kerbs, sidewalks, markings

Lane plan across the street (`street.js:5-6`):

| web z | What |
|---|---|
| -11 … -7 | north sidewalk, raised 0.15 |
| -7 … -5 | north parking lane (cars centred on z -5.98, noses west) |
| ±4.6 | the two rows of El columns, between parking and travel lanes |
| -4 … 0 | westbound travel lane |
| 0 … 4 | eastbound travel lane |
| 5 … 7 | south parking lane (cars centred on z +5.98, noses east) |
| 7 … 11 | south sidewalk, raised 0.15 |

**Ground sheet.** One sheet of asphalt at y 0 from x -110 to 110, z -72 to 72 lies under everything, so nothing ends
in a void (`ground.js:49`).

**Sidewalk slabs.** Eight raised slabs, top at 0.15, each with a kerb stone 0.28 wide (`curb`, a lighter concrete)
along its road edge; each is a solid collider y 0 … 0.15 (tag `sidewalk`), which the player walks up as a step
(`layout.js:133-144`, `ground.js:55-63`):

| # | Side | web x | web z | Blender y | Length (m) |
| --- | --- | --- | --- | --- | --- |
| 1 | north | -46 … -16.2 | -11 … -7 | 7 … 11 | 29.8 |
| 2 | north | -7.8 … -3.6 | -11 … -7 | 7 … 11 | 4.2 |
| 3 | north | 1 … 6 | -11 … -7 | 7 … 11 | 5 |
| 4 | north | 11 … 25 | -11 … -7 | 7 … 11 | 14 |
| 5 | north | 25 … 46 | -12.2 … -7 | 7 … 12.2 | 21 |
| 6 | south | -46 … -12.6 | 7 … 11 | -11 … -7 | 33.4 |
| 7 | south | -8 … 28.6 | 7 … 11 | -11 … -7 | 36.6 |
| 8 | south | 35 … 46 | 7 … 11 | -11 … -7 | 11 |

Outside the bounds the same slabs run on to x ±96 on both sides without colliders (`ground.js:64-68`). The pawn
shop's vestibule floor is a ninth slab at the same height (2.5.4).

**Dropped kerbs.** Between the slabs the sidewalk drops to road level: a concrete apron 4 m deep, a flush kerb stone
3 cm high, and a slope 0.9 m long down from the slab at each end (the slopes are drawn only; the 0.15 step is what
collides) (`layout.js:150-156`, `ground.js:70-79`):

| Dropped kerb | Side | web x | Width (m) | web z |
| --- | --- | --- | --- | --- |
| shop roll-door driveway | north | -16.2 … -7.8 | 8.4 | -11 … -7 |
| shop second-bay driveway | north | -3.6 … 1 | 4.6 | -11 … -7 |
| alley mouth | north | 6 … 11 | 5 | -11 … -7 |
| vacant-lot gateway | south | -12.6 … -8 | 4.6 | 7 … 11 |
| parking-lot entry | south | 28.6 … 35 | 6.4 | 7 … 11 |

**Markings** (all flat paint; white and yellow lines are worn road paint):

| Marking | Geometry | Source |
|---|---|---|
| Double yellow centre line | two lines 0.12 wide at z -0.15 and +0.15, from x -96 to 22.6 and from 27.0 to 96 (broken at the crossing) | `ground.js:86-89` |
| Parking stall ticks | white, 0.12 wide, across each parking lane from \|z\| 5.1 to 6.98, every 5.8 m starting at x -40.6, left out within 1 m of a dropped kerb and within 3 m of the crossing. North side at x -40.6, -34.8, -29, -23.2, -17.4, -5.8, 17.4, 34.8, 40.6; south side at x -40.6, -34.8, -29, -23.2, -17.4, -5.8, 0, 5.8, 11.6, 17.4, 40.6 | `ground.js:92-98` |
| Mid-block crossing | ladder bars (one per metre) across the whole roadway, x 23 … 26.6, z -6.8 … 6.8 | `ground.js:100-109` |
| Stop bars | white, 0.4 wide: at x 21.9 across the eastbound half (z 0.5 … 6.9), at x 27.7 across the westbound half (z -6.9 … -0.5) | `ground.js:110-111` |
| Lane arrows | eastbound at (-29, 2.3) and (15.5, 2.3), westbound at (-12, -2.3) and (34, -2.3) | `ground.js:114-117` |
| Yellow kerbs | the kerb stone painted yellow at the open hydrant (south side, x -16.4 … -12.6) and at the bus stop (north side, x 27.2 … 31.2) | `ground.js:120-123` |

**Repairs.** Fourteen rectangular asphalt patches, 8 mm proud, darker (#121316) or paler (#232427) than the road
(#1b1c1f) (`ground.js:130-148`), as (x0, x1, z0, z1): dark (-41, -37.5, -6.5, -1.2), pale (-33.5, -32.4, -6.8, 6.8),
dark (-27, -9, -3.3, -2.1), pale (-22.5, -19.5, 1.2, 4.4), dark (-14, -12.9, -6.9, 2.4), pale (-3.5, 2.5, -1, 0.6),
dark (3, 21, 2.2, 3.5), pale (8.5, 12, -5.5, -2.6), dark (17.2, 18.3, -6.9, 6.9), pale (28, 33, -4.2, -1.4),
dark (30.5, 43, 1, 2.1), pale (37, 40, 3.2, 6.6), and outside the block dark (50, 61, -5, -1), pale (-64, -52, 0.8, 4).

**Standing water.** The open hydrant on the south kerb at x -12.25 has hosed the street down. 28 irregular wet
patches (an ellipse of the given radii whose rim wanders by up to about ±40 %, `ground.js:16-42`) lie 14 mm over the
road; their centres and smaller radius are published as `level.puddles` for splash and reflection cues
(`ground.js:152-169`; no module of the shipped game reads the list yet). As (x, z, rx, rz, yaw):

- fed by the hydrant: (-11.6, 4.6, 5.2, 2.4, 0.1) at its foot, then the wet south gutter (-6.5, 6.1, 5, 0.8),
  (1.5, 6.2, 4.4, 0.7), (9.5, 6.25, 4.6, 0.6);
- low spots: (-38.5, -6, 3.2, 0.8), (-34, 1.4, 2.6, 1.5, 0.4), (-27.5, 6.2, 3, 0.7), (-24, -1.6, 2.2, 1.3, -0.3),
  (-20.5, -6.15, 4.2, 0.7), (-17.5, 2.9, 1.8, 1.1, 0.8), (-9.5, -4, 3, 1.6, 0.2), (-2.6, -5.9, 3.6, 0.9),
  (-0.5, 1.9, 2.2, 1.4, -0.5), (5.8, -1.8, 2.8, 1.7, 0.3), (12.5, -6.2, 3.8, 0.7), (14.5, 0.8, 2.4, 1.2, 0.6),
  (19.5, 5.2, 2.6, 1.5, -0.2), (21.5, -3.4, 2, 1.2, 0.2), (27.5, 0.6, 3.4, 1.9, 0.1), (31, -6.1, 4, 0.8),
  (33.5, 5.9, 3.5, 0.9), (36.5, -1.4, 2.4, 1.5, -0.4), (40.5, 3.4, 2.2, 1.2, 0.5), (43, -5.4, 2.4, 1.1);
- outside the block: (52, 2, 4, 2, 0.2), (60, -3, 5, 2), (-55, -2.5, 4.5, 1.8, 0.1), (-66, 3, 5, 2.2, -0.2).

By day the material library dries every patch outside the hydrant's reach (`docs/CONTRACT.md` 6.1 "Day and night"),
so the daylight street is dry except round x -12.

**Wear.** Scattered by the level's seeded random stream: 16 crack decals on the roadway (x -44 … 44, z -6 … 6),
14 oil stains in the parking lanes (\|z\| 5.4 … 6.4), 12 strips of gutter grime (\|z\| 6.2 … 6.8)
(`ground.js:172-185`).

**Manholes.** Six cast-iron covers (catalogue `manhole`, 0.9 m, flush, no collision) at (-22.5, -1.8), (-9.5, 2.6),
(6.4, -2.4), (18.6, 1.9), (30.5, -0.9), (-36, 2.2); the first, third and fifth breathe steam (`ground.js:188-192`).

**Hydrants.** Two shut hydrants at the kerbs, (37.4, -7.5) and (38.2, 7.5), and the open one (`hydrant_open`, a
dynamic prop with a jet and a wet patch reaching 4 m) at (-12.25, 7.34) on the vacant lot's dropped kerb, turned 180°
so that it sprays north into the street (`street.js:126, 146, 153`).

### 2.9 Closures and structures on the avenue

#### 2.9.1 West end: road works under the station (`street.js:393-422`)

- A dark green (#23463c) plywood hoarding from wall to wall on x -45.3, 2.7 high: three runs, z -11 … -7 and
  7 … 11 standing on the sidewalks, z -7 … 7 on the road. Behind it a player-only wall x -46 … -45.3, z -11 … 11,
  8 m high.
- On its street face: two `ROAD CLOSED` / `EL STRUCTURE REPAIRS  ·  NO THRU TRAFFIC` signs (3.4 × 1.05, black on
  orange #e8641b) at z -2.6 and 3.4, y 1.75; a `HOLLIS` tag and three posters.
- In front of it: four jersey barriers end to end across the road at x -43.55, traffic barrels in both gutters,
  a generator, a floodlight stand and a pallet stack in the gap behind the barriers, two barricades, three cones
  (2.15).
- The shut `CANDY  ·  SODA` kiosk beside the south stair (2.9.4).

**Hoardings** everywhere are the same construction (`fences.js:34-45`): painted boards 8 cm thick with a timber cap
rail (0.14 × 0.06) and posts 9 × 9 cm on the back every 2.44 m; one collider 8 cm thick, surface wood, tag
`hoarding`. They stop rounds and walkers.

#### 2.9.2 East end: the Vultures' roadblock (`street.js:428-452`)

- A chain-link fence on x 45.25, 2.5 high, in three runs: z -12.2 … -7 and 7 … 11 on the sidewalks, z -7 … 7 on the
  road, posts every 2.4 m, with a dark green (#1f3a2c) scrim 2.1 high tied across its street side and concrete feet
  (0.36 × 0.70 × 0.14) at z -6.6, -4.2, -1.8, 0.6, 3.0, 5.4. Each run is a collider 0.1 thick (tag `roadblock`):
  unlike the cage, this fence stops rounds. Behind it a player-only wall x 45.25 … 46, z -12.2 … 11, 8 m high.
- A jack-knifed box truck at (41.4, 0.3) turned 60°, three jersey barriers, two barricades, two oil drums, a
  floodlight stand on the south sidewalk, a propane tank (2.15, 2.13).
- `VULTURES` and `VLTR` sprayed on the scrim.

**Chain-link** everywhere is the same construction (`fences.js:13-27`): a see-through mesh panel, pipe rails
(r 0.022) just above the bottom and below the top and, when the run is taller than 3 m, at mid-height; line posts
r 0.035 at the stated spacing (default 3 m), end posts r 0.05 standing 0.12 above the mesh.

#### 2.9.3 The sidewalk shed: the vantage (`street.js:458-547`, `layout.js:106-114`)

A construction sidewalk shed over the south sidewalk in front of S3.

| Part | Geometry | Source |
|---|---|---|
| Deck | plywood on timber joists, x 1 … 19, z 7.45 … 10.95 (18 × 3.5 m), top at y 2.95 (2.8 above the sidewalk), 0.16 thick; solid, surface wood, tag `shed-deck`, not in the nav grid. 15 joists 0.08 × 0.14 at 1.2 m | `street.js:486-487` |
| Posts | galvanised tube r 0.045 on timber mud sills, two rows at z 7.6 and 10.8, seven per row at x 1.12, 4.08, 7.04, 10, 12.96, 15.92, 18.88; each a collider 0.14 × 0.14 (tag `shed-post`), so the sidewalk under the deck stays a walkable colonnade 3.2 m wide | `street.js:462-471` |
| Ledgers and braces | tube r 0.035 across at each post pair (y 2.61) and along both rows (y 2.71); knee braces r 0.025 from y 2.05 on each post up to the ledger 0.75 m along: all above head height | `street.js:472-483` |
| Parapet | hoarding boards 1.1 high (y 2.95 … 4.05) along the kerb side (z 7.49, facing the avenue), the east end (x 18.96) and the west end from z 7.45 to 8.95; open where the stair arrives (z 8.95 … 10.95) and along the building. Solid: cover for a crouching player (eye 1.05 above the deck), shot over standing (`test/level-layout.test.js:347-352`) | `street.js:490-493` |
| Skirt | a board 0.5 deep under the kerb-side deck edge (y 2.45 … 2.95) hiding the joists; stencilled `SIDEWALK SHED  ·  PERMIT 0214  ·  STORES OPEN DURING WORK` | `street.js:496-497, 507` |
| Banners | three vinyl banners 4.9 × 0.78 on the kerb-side parapet at y 3.5: `GOLDEN BIRD CHICKEN` at x 4.1 (red #b3261e on yellow #f2c21a), `WINES & LIQUORS` at x 10 (red #ff3030 on black #101113), `LUCKY NAILS` at x 15.9 (pink #ff3d9a on #2a0f1e) | `street.js:498-506` |
| Bulbs | six caged bulbs under the deck at y 2.57, z 9.2, between the post pairs (x 2.6, 5.56, 8.52, 11.48, 14.44, 17.4); lamp hints at the 1st, 3rd and 5th, y 2.45: kind `work`, #fff1d0, intensity 9, range 7, priority 3 | `street.js:509-515` |
| Stair | at the west end against the building, x -2.6 (foot) … 1 (top), z 8.95 … 10.95 (2 m wide): 12 open plywood treads, rise 0.233, going 0.30 (37.9°), on two timber stringers; a tube handrail (rails 0.5 and 1.0 above the slope) on the street side only. Tread colliders as in the shop (tag `shed-stair`, surface wood); a player-only wall under the handrail from the sidewalk to 3.95 | `layout.js:113`, `street.js:517-529` |
| On the deck | two sandbag walls against the parapet at (5.4, 7.9) and (12.8, 7.9), a crate, cardboard boxes, a pallet; a propane tank at (9.3, 10.35) | `street.js:531-536`, `data.js:129` |
| `level.vantage` | `stairsFoot` (-3.2, 0.15, 9.95), 0.6 m west of the first tread, and `deck` (10, 2.95, 9.3), the middle of the deck. Published for the contract; no module of the shipped game reads it, and Goons never climb (`03-enemies.md` 3.7.3) | `street.js:543-546` |

#### 2.9.4 Tall things on the sidewalks (`street.js:232-387`)

Each "curtain" has a piece at the kerb and a piece against the wall a few metres apart, so the sidewalk is a walkable
zigzag but not a firing lane. Every one is a single solid box unless stated.

| Structure | Footprint (web x, z), height | Construction | Source |
|---|---|---|---|
| Newsstand kiosk | x -30.2 … -27.2, z -9.5 … -7.04 (at the north kerb); y 0.15 … 2.65 | sheet-steel box painted #24463a, a flat roof overhanging 0.25, a roll shutter (y 0.95 … 2.20) over a counter shelf on its **north** face, a painted fascia `NEWS  ·  MAGAZINES  ·  LOTTO` (2.4 × 0.26), two posters | `street.js:233-249, 253` |
| Candy kiosk | x -45.24 … -42.5, z 9.25 … 10.9 (beside the south station stair) | the same, shutter on its **east** face, `CANDY  ·  SODA` (1.35 × 0.26) | `street.js:421` |
| Tyre cage | x -20.4 … -18, z -10.96 … -8.6 (against the shop wall); y 0.15 … 2.40 | steel corner posts 8 × 8 cm, chain-link on the front and both ends, a corrugated roof, nine stacks of used tyres inside (r 0.34, 1.55 … 2.15 m high), a price board above the front: `USED TIRES` / `ALL SIZES  ·  MOUNTED FREE`. Collider surface rubber | `street.js:254-277` |
| Produce stand | x 11.4 … 15.2, z -10.98 … -8.6 (against the deli); y 0.15 … 2.50 | green (#2d5a3a) plywood ends, a green canopy sloping from y 3.0 at the wall to 2.4 over the sidewalk (overhang 0.25), three tiers of timber crates (tops 0.5, 0.82 and 1.14 above the sidewalk), 15 crates of fruit (orange, red, yellow, green, purple heaps), two bare bulbs; lamp hint (13.3, 2.4, -9.2), `window`, #ffc98a, intensity 12, range 8, priority 3. Collider surface wood | `street.js:280-309` |
| Utility dig | x 17.8 … 21.2, z -9.2 … -7.04 (at the north kerb); pen to y 2.35 | an orange (#c4571a) plywood pen on all four sides round an open vault; two `DANGER` / `STEAM  ·  KEEP OUT` signs; a steam stack of nine orange and white rings (r 0.21, 0.4 high each) from y 0.15 to 3.75 at (19.5, -8.1), solid above the pen; steam point at (19.5, 3.85, -8.1) | `street.js:310-331` |
| Site shanty | x -17.4 … -14.6, z 8.6 … 10.98 (against the wall, south side); y 0.15 … 2.85 | green plywood hut, a lean-to corrugated roof rising from y 2.87 at the front to 3.15 at the wall, a chained timber door (1.0 × 2.05) on its north face, `POST NO BILLS`, posters; a door lamp, hint (-16, 2.5, 8.2), `work`, #fff1d0, intensity 9, range 7, priority 3 | `street.js:334-350` |
| Portable toilets | two `porta_potty` (1.2 × 1.2 × 2.3) at the south kerb, (-6.8, 7.66) and (-6.8, 8.86) | catalogue props | `street.js:351-352` |
| Hoist tower | x 19.06 … 22, z 7.04 … 10.97 (the full width of the south sidewalk at the east end of the shed) | a green plywood base to y 2.75 (solid); above it a scaffold tower to y 9.4 (four standards to 9.9, ledgers every 1.9 m) wrapped in green debris netting on its street, west and east sides, with a timber top. The netted part is player-only: rounds pass through. Two `SIDEWALK CLOSED` / `USE WALKWAY` signs. A walkway round it in the parking lane is marked by two jersey barriers at (18.4, 5.02) and (21.5, 5.02) and two barrels | `street.js:354-386` |
| Rolling scaffolds (2) | A: x -30.2 … -28.6, z -0.3 … 4.7 (across the eastbound lane); B: x -1.9 … -0.3, z -4.7 … 0.4 (across the westbound lane at reel 1) | the El repair crew's towers: 1.6 wide, about 5 m long, eight standards on castors, ledgers at y 0.45, 2.1 and 3.58, a plywood work deck at y 3.7 with toe boards and a guard rail at 4.7, rust-orange debris netting on both long faces, `EL REPAIRS` / `KEEP CLEAR` signs. One solid box each from the road to y 3.8 (tag `scaffold`): hard cover that blocks sight lines even though the netting is drawn see-through | `street.js:59-61, 74, 166-225` |

#### 2.9.5 What stands on the roadway (`street.js:34-102`)

Catalogue props; exact placements are in 2.15. The intent, lane by lane:

- **North parking lane** (z -5.98, noses west), west to east: van (-38.2), sedan (-27.4), white van (-20.2), a
  motorbike (-5.7), taxi (4), sedan (13.6), van (19.4), sedan (31.4). Gaps every few car lengths are the crossings
  between lanes; the gaps at x -16 … -8 and -3.6 … 1 face the shop's two doors.
- **South parking lane** (z +5.98, noses east): Rule's black SUV (-40.5) just behind the start, taxi (-24.6), van
  (-18.9), van (-3), sedan (4.6), oxblood van (13.4), sedan (39.6). The lane is empty from x 16 to 37 for the hoist
  tower's walkway, the crossing and the lot entry.
- **West stretch of the travel lanes**: a sedan left askew in the westbound lane (-35.2, -2.3); rolling scaffold A
  across the eastbound lane (x -30.2 … -28.6); then the first curtain's truck, a mustard box truck stopped in the
  westbound lane (-19.2, -2.4), with two barrels and a barricade east of it and a motorbike in the eastbound lane.
- **The reel 1 arena** round the case at (-4, 1): the Vultures' black van (-9.4, 1.8) slewed across the eastbound lane,
  nose west-south-west, its back doors open toward the case 3 m away; rolling scaffold B walling off the westbound
  lane east of the case (x -1.9 … -0.3, z -4.7 … 0.4); two jersey barriers (-1.1, 3.1) and (1, -1.9), sandbags
  (-4.3, -2.9), trash bags (-6.2, 4.3), milk crates (0.1, 1.2), a tyre stack (-7.6, -2.5), a crate (-2.4, 4.25);
  `VULTURES` sprayed on the road.
- **The second curtain**: a box truck double-parked in the eastbound lane (5.85, 2.35) and a van in the westbound one
  (16.3, -2.6), with a jersey barrier, barrels, a barricade, trash, sandbags and a tyre stack between them, and a
  propane tank at the barrier chicane (8.9, -1.5).
- **Between the crossing and the roadblock**: two jersey barriers set across the lanes (27.6, 2.6) and (28.4, -2.9),
  three barrels, a sedan (33.8, 2.3), a van (36.9, -2.5), then the roadblock's own truck and barriers (2.9.2).
- Ten traffic cones are scattered along the road (no collision).

### 2.10 The yards

#### 2.10.1 The alley (`yards.js:28-67`, `layout.js:80`)

- x 6 … 11 (5 m wide) between the shop and the deli, open to the north sidewalk at z -11 over a dropped kerb. Dark
  asphalt (#121316) with a concrete gutter 0.7 wide down the middle (x 8.15 … 8.85), two wet patches, four grime
  decals. The shop's side door opens into it at z -23.1 … -21.1.
- North end: a chained chain-link gate on z -31.4, 2.6 high (posts every 2.5 m), with a green tarp 4.6 × 2.1 tied
  across it and a padlocked chain. It is a full collider (it stops rounds) backed by a player-only wall
  z -32 … -31.4, 8 m high. The 2.6 m behind it is unreachable.
- A steam grate (0.8 × 0.8) at (8.5, -24.6). Two dumpsters, trash, crates, a pallet stack, an oil drum (2.15);
  a welding rack beside the side door (2.13). Tags and posters on both walls (2.16).

#### 2.10.2 The cut (`yards.js:73-85`, `layout.js:81`)

- x 22 … 25 (3 m wide) between the deli and the cage, open to the north sidewalk, paved in concrete from z -33.5.
  It leads to the cage's west gate at z -29.4 … -26.4 and dead-ends at the neighbour's wall. A dumpster, trash,
  crates, boxes, a pallet (2.15).

#### 2.10.3 The Cage (`yards.js:91-183`, `layout.js:83-93`)

| Part | Geometry | Source |
|---|---|---|
| Fence line | x 25 … 45.4, z -33 … -12.2 (20.4 × 20.8 m), mesh to y 4.0 | `layout.js:84-88` |
| Fence build | a concrete knee wall 0.2 thick and 0.5 high (solid, tag `cage-plinth`) with chain-link above it to 4.0 (three rails, posts every 3 m). The mesh is a **player-only** collider 0.2 thick from the plinth top to y 8: the court can be seen and shot into and out of, never climbed | `yards.js:97-111`, `layout.js:89` |
| South side | stands on the back edge of the north sidewalk (which is 5.2 m deep here): the plinth top is at 0.65. Runs x 25 … 33 and 36 … 45.4 | `yards.js:112-114` |
| South gate | x 33 … 36 (3 m), open; the court is 0.15 below the sidewalk | `layout.js:90` |
| West gate | z -29.4 … -26.4 (3 m) in the west side, open onto the cut | `layout.js:91` |
| Gates | posts r 0.07 to y 4.5 at each side with a header pipe at 4.4; two leaves 1.45 wide × 2.2 high chained back flat against the inside of the fence, 0.22 inside the line | `yards.js:120-128` |
| Surface | green acrylic (#2f4f46) over the whole enclosure; reports `concrete` | `yards.js:138`, `layout.js:198` |
| Court lines | white, 7 cm wide. Boundary x 26.6 … 43.9, z -29.9 … -15.1; half-court line at x 35.25; centre circle r 1.8 at (35.25, -22.5). At each end: a red (#7a2e26) key 4.6 long × 3.6 wide (x 26.6 … 31.2 and 39.3 … 43.9, z -24.3 … -20.7), a free-throw semicircle r 1.8 on the key's inner end, a three-point arc r 6.2 centred on the hoop (x 27.85 and 42.65) joined to the baseline by straight lines at z -28.7 and -16.3 | `yards.js:132-160` |
| Hoops | catalogue `hoop` at (26.25, -22.5) facing east and (44.25, -22.5) facing west | `yards.js:162-163` |
| Furniture | three bleachers along the north fence at x 29.6, 35.25, 40.9, z -31.7 (rows stepping up to the north, 0.42 … 1.5 high); court lights (9 m masts) in the south-west corner (25.6, -12.95) and the north-east corner (44.8, -32.3); two benches and a bin inside the south fence | `yards.js:164-169` |
| The Vultures' corner | round reel 3 at the centre circle: sandbags, a crate, an oil drum, a motorbike, a pallet stack, milk crates, two tyre stacks; boxes and a cart further out; `VULTURES` sprayed on the court at (38.65, -18.2) | `yards.js:171-182` |
| Unreachable strips | between the north fence and the wall (z -33.5 … -33) and between the east fence and the wall (x 45.4 … 45.8) | `test/level-layout.test.js:631` |

#### 2.10.4 The vacant lot and the mural (`yards.js:189-334`, `layout.js:95`)

- x -16 … -4, z 11 … 26 (12 × 15 m) between the pawn shop and S3: bare dirt (#3a3229, reports `dirt`), two wet
  patches, a scorch mark 5.5 × 4.2 under the burned-out car at (-11.2, 18.6).
- Street side: a dark green hoarding on z 11.14, 2.55 high, in two runs x -16 … -11.9 and -8.7 … -4, bill-posted
  along its length, `POST NO BILLS` stencilled on each run. The gateway between them (x -11.9 … -8.7, 3.2 m) has
  posts r 0.06 to y 2.75 and two chain-link leaves 1.58 × 2.2 standing open inside, parallel to the hoarding at
  z 11.34. The sidewalk drops to road level here (dropped kerb x -12.6 … -8).
- South side: open to the rear lane along z 26.
- Props: the burned car, tyres, a mattress, three shopping carts, trash, a drum, boxes, a pallet, a crate, milk
  crates, a floodlight stand at (-9.6, 13.3) aimed at the back of the hoarding (2.15). A propane tank by the burned
  car (2.13).
- Weeds: 26 tufts of crossed grass blades 0.3 … 0.6 wide and 0.25 … 0.6 high along the walls. No collision
  (`yards.js:321-333`).
- **The mural** on the pawn shop's east wall (x -16, facing east): a painting 12 m wide × 7.6 m high, centre
  (z 18.4, y 4.5), so it spans z 12.4 … 24.4, y 0.7 … 8.3. Seen from the lot (looking west) its left edge is the south
  end. Content, left to right (`yards.js:189-263`): a field graded from night blue (#111a33) through oxblood
  (#3b1420) to near black; a **gold record** (#d9a514, radius 3.04 m, centre 3.6 m from the left edge and 4.04 m
  above the ground) rising like a sun with 18 alternating gold and red rays behind it, dark grooves, an oxblood label
  (#8a1a22) and a spindle hole; **the El in silhouette** (#07080c) along the bottom (a deck band, columns with knee
  braces every 1.38 m, a ground band); the **IPX wordmark** in off-white (#f4f2ec), 1.29 m high, centred 9.24 m from
  the left edge and 3.74 m above the ground, with `IPX.EXCHANGE` under it; a thin gold (#f6c21a) frame. No slogan.
- The same painting is specified layer by layer in `06-look-fx.md` 2.12.
- Over the mural, by a surer hand: `RULE` in gold, 6.4 × 2.3 m, centred at (z 15.6, y 6.55). Smaller tags round its
  foot: `HOLLIS` (z 22.9), `QUEENS` (z 12.6), `NO SLEEP` (z 26.6) (`yards.js:264-268`).

#### 2.10.5 The rear service lane (`yards.js:340-382`, `layout.js:96`)

- x -16 … 22, z 26 … 31 (38 × 5 m) between the back of S3 and the garages; its west end is the vacant lot's back,
  its east end opens into the parking lot. Dark asphalt (#121316) from x -4 east, one pale patch, two wet patches,
  grime and oil.
- **Loading dock** on the back of S3: a concrete platform x 6.4 … 12.4, z 26 … 27.5, 1.0 high (solid, tag `dock`)
  with a yellow edge, three rubber bumpers (0.3 × 0.45 × 0.09 at x 7.4, 9.4, 11.4) and four concrete steps
  (0.25 × 0.25) at its west end, x 5.4 … 6.4, climbing east. Above it a roll shutter x 7.6 … 11.2, y 1.0 … 3.5. A
  pallet stack and boxes stand on it. `NO PARKING` / `LOADING ZONE` stencilled on the wall at x 16.
- Two dumpsters facing each other at x -2, trash, a pallet stack, two drums, a crate, milk crates, a parked van at
  (-7.6, 29.6) and a pickup at (17.4, 29.85) (2.15); a steam grate at (1.8, 28.4); a welding rack between two
  garage doors and a propane tank at the east end (2.13).

#### 2.10.6 The parking lot (`yards.js:388-479`, `layout.js:97-103`)

| Part | Geometry | Source |
|---|---|---|
| Ground | x 22 … 46, z 11 … 34 (24 × 23 m), the avenue's asphalt | |
| Low wall | concrete, 0.3 thick, top at y 0.77, along the sidewalk edge (z 11 … 11.3) on x 22 … 26.05 and 35 … 46, with a pipe rail at y 1.13 on stanchions about every 2.2 m; solid, tag `lot-wall` (waist-high cover) | `yards.js:393-400` |
| Entrance | the gap x 26.05 … 35: the attendant's booth (`lot_booth`, 2.2 × 1.8 × 2.6) at (27.3, 12.55), then the driveway x 28.6 … 35 over a dropped kerb | `yards.js:403`, `layout.js:102` |
| Barrier arm | a yellow post 0.22 × 0.22 × 1.1 at (28.61, 11.61) (solid, tag `lot-gate`) with a white arm 3.1 m long raised 57° toward the east and a red band on it. The arm does not collide | `yards.js:404-407` |
| PARK pylon | a steel pole r 0.09, 5.6 high, at (35.35, 11.65) (solid); a sign box 1.8 wide × 1.6 high × 0.2 thick at y 3.9 … 5.5 with a cyan (#35e0ff) neon `PARK` / `24 HR` panel 1.7 × 1.5 on both faces (the box is bullet-only); lamp hint (34.65, 4.7, 11.65), `neon`, intensity 12, range 9 | `yards.js:408-417` |
| Bay lines | white, 0.10 wide. West row against S3: lines x 22.4 … 27.4 at z 14.2, 16.8, 19.4, 22, 24.6 and a closing line on x 27.4. Middle row: lines x 34 … 39 at z 14.5, 17.1, 19.7, 22.3, 24.9 and a closing line on x 34. South row: lines z 29.2 … 34 at x 23.2, 25.8, 28.4, 31, 33.6 | `yards.js:419-427` |
| Wheel stops | four concrete blocks 0.22 × 1.8 × 0.12 at x 22.5 … 22.72 at the head of the west bays (drawn only) | `yards.js:429` |
| Paint and wear | two arrows at (30.4, 14.2) and (33.2, 14.2); six oil stains, four cracks, three wet patches | `yards.js:430-439` |
| Parked cars | west row: sedan, SUV, (empty bay), pickup; middle row: taxi, van, (empty bay), sedan; two sedans nose-in on the south wall (2.15) | `yards.js:441-449` |
| Loose cover | between the lane mouth and the truck: two pallet stacks, a drum, two jersey barriers, a tyre stack, a dumpster, trash, a cart, two barrels, a crate | `yards.js:451-463` |
| Billboard | catalogue `billboard` (9 wide × 11 high) at (40.7, 12.4): two legs and a panel at y 6.3 … 10.8 whose face looks **south** into the lot, lit by two floods | `yards.js:466` |
| Light poles | `street_lamp` at (39.3, 13.95) reaching south and at (30.9, 33.45) reaching north | `yards.js:467-468` |
| IPX truck | catalogue `ipx_truck` (6.8 × 2.5 × 3.0, dynamic) at (41.3, 29.7), nose east, in the south-east corner; the extraction zone is behind its rear doors (2.13) | `yards.js:469`, `data.js:16-18` |
| Wall art | `VIOLATORS TOWED` / `AT OWNER'S EXPENSE` stencil on the east wall at z 19.5; `188` and `QUEENS` tags; an IPX poster on the south wall | `yards.js:471-477` |

### 2.11 Perimeter sealing

Every edge is something solid that stops rounds, and behind every edge stands a player-only wall 0.6 m thick and
8 m high just outside the bounds (`level.js:83-92`); on top of that the physics clamps every capsule to the bounds
(`docs/CONTRACT.md` 10 "Physics extras"). Nothing can be hopped.

| Edge | Stretch (web) | What you see and hit | Extra player-only wall |
|---|---|---|---|
| North, z -34 | x -46 … -24 | the tenement | |
| | x -24 … 6 | the chop shop's north wall (z -31) and neighbour 1 above it | |
| | x 6 … 11 | the alley gate on z -31.4, neighbour 2 on z -34 | x 6 … 11, z -32 … -31.4 (`yards.js:66`) |
| | x 11 … 22 | the deli | |
| | x 22 … 46 | neighbour 3 on z -33.5 (behind the cut and the cage's north fence on z -33) | |
| East, x 46 | z -33.5 … -12.2 | neighbour 4 on x 45.8 (behind the cage's east fence on x 45.4) | |
| | z -12.2 … 11 | the roadblock fence on x 45.25 | x 45.25 … 46, z -12.2 … 11 (`street.js:436`) |
| | z 11 … 34 | neighbour 5 | |
| South, z 34 | x -46 … -30 | the station house | |
| | x -30 … -16 | the pawn shop | |
| | x -16 … 22 | the garages (z 31) and neighbour 6 above them | |
| | x 22 … 46 | neighbour 7 | |
| West, x -46 | z -34 … -11 | the tenement | |
| | z -11 … 11 | the hoarding on x -45.3 | x -46 … -45.3, z -11 … 11 (`street.js:401`) |
| | z 11 … 34 | the station house | |
| All four | the whole edge | | x -46.6 … -46, x 46 … 46.6, z -34.6 … -34, z 34 … 34.6, y 0 … 8 (`level.js:85-92`) |

Above: the El deck is a solid box 6.5 … 6.9 over the avenue; building colliders reach their parapets; nothing in the
game lifts the player above 2.95 (the shed deck) plus a jump, so the 8 m seal height is ample.

### 2.12 Ground surfaces

"Surface" is the name footsteps and bullet impacts report (`docs/CONTRACT.md` 4.2). For the bare ground plane it comes
from `groundSurfaceAt` (3.3); things standing on the ground report their own (`kit.js:16-51`).

| Area | Drawn material (catalogue name, colour) | Reported surface | Source |
|---|---|---|---|
| Roadway, parking lanes, parking lot | `asphalt` #1b1c1f (night value; lighter and dry by day), with patches #121316 / #232427 and wet patches `asphalt_wet` | `asphalt` | `ground.js:49`, `layout.js:202` |
| Sidewalk slabs, vestibule pad | `sidewalk` #6f6c66, kerb stones `curb` #85827a | `concrete` (box colliders) | `ground.js:55-62` |
| Dropped-kerb aprons | `concrete` #7b7a76 | `concrete` (ground plane, 7 ≤ \|z\| ≤ 11) | `ground.js:74`, `layout.js:201` |
| Chop shop floor and thresholds | `concrete_dark` #44444a | `concrete` | `shop.js:51-54`, `layout.js:197` |
| Mezzanine deck and stair | `metal_dark` #23262a | `metal` | `shop.js:164-165, 225` |
| Alley | `asphalt` tinted #121316, concrete gutter | `asphalt` | `yards.js:31-32` |
| The cut | `concrete` | `asphalt` (it lies outside every surface rectangle: 3.8) | `yards.js:75`, `layout.js:196-203` |
| The Cage | `court` #2f4f46 (green), keys #7a2e26 (red), white lines | `concrete` | `yards.js:138-139`, `layout.js:198` |
| Vacant lot | `dirt` #3a3229 | `dirt` | `yards.js:274`, `layout.js:199` |
| Rear lane | `asphalt` tinted #121316 east of x -4, the base sheet west of it | `asphalt` | `yards.js:343` |
| Loading dock and its steps | `concrete` | `concrete` | `yards.js:356-359` |
| Shed deck and stair | `plywood` #a98a5c | `wood` | `street.js:486, 519` |
| Station stairs, mezzanine, El steel | `steel_el` #1f2a26, `corrugated` | `metal` | `el.js:182, 245` |
| Station platforms | `concrete` | `concrete` | `el.js:278` |

### 2.13 Gameplay data

All of it is authored in `src/level/data.js` as (x, z) on the level's own floor (road 0, sidewalk 0.15) unless a
height is given, and turned into `G.level` members by `level.js:98-143`.

#### 2.13.1 Start pose (`data.js:7`, `level.js:186`)

|  | web (x, y, z) | Blender (x, y, z) | Unreal (X, Y, Z) cm | Facing |
| --- | --- | --- | --- | --- |
| Player start | (-37.4, 0.15, 8.15) | (-37.4, -8.15, 0.15) | (-3740, 815, 15) | web yaw -1.4908 rad (-pi/2 + 0.08); forward (x, z) = (0.9968, -0.0799); Unreal yaw -4.58° |

The player stands on the south sidewalk on the centre line of the south station stair, 1.1 m east of the folding gate
at its foot, looking east and 4.6° toward the avenue. Rule's black SUV is parked at the kerb behind his left shoulder
(-40.5, 5.98); the pizza counter's front is 2.85 m to his right. Nothing taller than a bin stands within 2 m in front
of the pose (`test/level-layout.test.js:95-104`).

#### 2.13.2 Objectives: the three master reels (`data.js:10-14`, `level.js:98-102`)

| id | code | label | zone | web (x, y, z) | case yaw (rad) | Blender (x, y, z) | Unreal (X, Y, Z) cm | Unreal yaw |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `reel1` | 1 | Reel 1 — The Avenue | `avenue` | (-4, 0, 1) | 0.35 | (-4, -1, 0) | (-400, 100, 0) | -20.1° |
| `reel2` | 2 | Reel 2 — Chop Shop | `shop` | (-9.5, 0, -21.5) | -0.5 | (-9.5, 21.5, 0) | (-950, -2150, 0) | 28.6° |
| `reel3` | 3 | Reel 3 — The Cage | `lot` | (35.25, 0, -22.5) | 1.1 | (35.25, 22.5, 0) | (3525, -2250, 0) | -63° |

Each is a catalogue `master_case` (0.9 × 0.6 × 1.05, dynamic, stateful) placed with the yaw shown; ids, codes and
labels come from `src/config/text.js:72-79`. Reel 2 is indoors (`interiorAt` = 1). Each reel sits in a small arena
ringed by at least four pieces of waist-to-chest-high cover at 1.5 to 5 m, with 1.4 m of clear ground all round the
case (`test/level-layout.test.js:215-235`).

#### 2.13.3 Extraction (`data.js:16-18`, `level.js:104-110`)

|  | web (x, y, z) | Blender (x, y, z) | Unreal (X, Y, Z) cm | Notes |
| --- | --- | --- | --- | --- |
| Extraction zone centre | (35.9, 0, 29.7) | (35.9, -29.7, 0) | (3590, 2970, 0) | radius 2.5 m (250 cm); label "IPX truck", code "IPX" |
| IPX truck (prop origin) | (41.3, 0, 29.7) | (41.3, -29.7, 0) | (4130, 2970, 0) | yaw 0: nose east; 6.8 × 2.5 × 3.0 m, so its rear doors are at x 37.9, 2.0 m east of the zone centre |

The zone is a vertical cylinder: horizontal radius 2.5 m from `src/config/flow.js:51`; `04-flow.md` owns the
vertical reach and the refusal rule. `level.extraction.prop` is the truck itself.

#### 2.13.4 Enemy spawn points (`data.js:24-78`, `level.js:134-137`)

`level.enemySpawns` = 29 ground points for Goons and 17 air points for Buzzards, each tagged with the zone it stands
in. None is in `west`.

| zone | ground | air |
| --- | --- | --- |
| `west` | 0 | 0 |
| `shop` | 7 | 4 |
| `avenue` | 12 | 6 |
| `lot` | 10 | 7 |
| **total** | 29 | 17 |

Ground points (y = the floor under the point). Two were moved by the walkability nudge (3.4); use the effective
position, or re-snap the authored one to the Unreal navmesh.

| # | zone | authored web (x, z) | floor y | effective web (x, z) | Unreal (X, Y, Z) cm (effective) | Where | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G1 | `shop` | (-25.1, -14.2) | 0 | same | (-2510, -1420, 0) | the gangway beside the tenement | data.js:26 |
| G2 | `shop` | (-21.4, -28.2) | 0 | same | (-2140, -2820, 0) | under the mezzanine | data.js:27 |
| G3 | `shop` | (-22.4, -15.2) | 0 | same | (-2240, -1520, 0) | behind the west lift | data.js:28 |
| G4 | `shop` | (3.6, -26.6) | 0 | same | (360, -2660, 0) | behind the racks in the north-east corner | data.js:29 |
| G5 | `shop` | (1.7, -23.8) | 0 | same | (170, -2380, 0) | behind the car on the east lift | data.js:30 |
| G6 | `shop` | (8.4, -29.6) | 0 | same | (840, -2960, 0) | the alley's dead end | data.js:31 |
| G7 | `shop` | (8.3, -21.8) | 0 | same | (830, -2180, 0) | the alley, at the side door | data.js:32 |
| G8 | `avenue` | (-22.9, 12.3) | 0.15 | same | (-2290, 1230, 15) | the pawn shop's vestibule | data.js:34 |
| G9 | `avenue` | (-21.5, -9.6) | 0.15 | same | (-2150, -960, 15) | behind the white van, beside the tyre cage | data.js:35 |
| G10 | `avenue` | (-5.7, -9.9) | 0.15 | same | (-570, -990, 15) | behind the food cart | data.js:36 |
| G11 | `avenue` | (16.5, -9.9) | 0.15 | same | (1650, -990, 15) | between the produce stand and the dig | data.js:37 |
| G12 | `avenue` | (-14.4, 12.7) | 0 | same | (-1440, 1270, 0) | vacant lot, behind the hoarding | data.js:38 |
| G13 | `avenue` | (-12.8, 23.6) | 0 | same | (-1280, 2360, 0) | vacant lot, behind the burned car | data.js:39 |
| G14 | `avenue` | (-5.2, 21.2) | 0 | same | (-520, 2120, 0) | vacant lot, at S3's side door | data.js:40 |
| G15 | `avenue` | (-12.4, 29.3) | 0 | same | (-1240, 2930, 0) | rear lane, behind the van | data.js:41 |
| G16 | `avenue` | (0.4, 28.4) | 0 | same | (40, 2840, 0) | rear lane, behind the dumpster | data.js:42 |
| G17 | `avenue` | (4.8, 28.6) | 0 | same | (480, 2860, 0) | rear lane, at the dock steps | data.js:43 |
| G18 | `avenue` | (14.6, 27.4) | 0 | same | (1460, 2740, 0) | rear lane, past the dock | data.js:44 |
| G19 | `avenue` | (20.4, 29.6) | 0 | **(20.75, 29.75)** | (2075, 2975, 0) | rear lane, at the lot corner | data.js:45 |
| G20 | `lot` | (23.5, -31.2) | 0 | same | (2350, -3120, 0) | the far end of the cut | data.js:47 |
| G21 | `lot` | (26.4, -31.6) | 0 | same | (2640, -3160, 0) | cage, behind the bleachers (west) | data.js:48 |
| G22 | `lot` | (44.2, -31.6) | 0 | **(44.25, -31.25)** | (4425, -3125, 0) | cage, behind the bleachers (east) | data.js:49 |
| G23 | `lot` | (43.6, -9.6) | 0.15 | same | (4360, -960, 15) | north sidewalk, at the roadblock | data.js:50 |
| G24 | `lot` | (43.4, 9.4) | 0.15 | same | (4340, 940, 15) | south sidewalk, at the roadblock | data.js:51 |
| G25 | `lot` | (24.2, 25.5) | 0 | same | (2420, 2550, 0) | lot, behind the pickup | data.js:52 |
| G26 | `lot` | (36.5, 21) | 0 | same | (3650, 2100, 0) | lot, the empty bay between the van and the sedan | data.js:53 |
| G27 | `lot` | (27.1, 32.4) | 0 | same | (2710, 3240, 0) | lot, between the cars on the south wall | data.js:54 |
| G28 | `lot` | (44.5, 16.6) | 0 | same | (4450, 1660, 0) | lot, under the billboard | data.js:55 |
| G29 | `lot` | (45, 26.4) | 0 | same | (4500, 2640, 0) | lot, between the dumpster and the truck | data.js:56 |

Air points (absolute height; never above the tracks: every one is more than 1.5 m outside the deck's edge,
`test/level-layout.test.js:171-177`):

| # | zone | web (x, y, z) | Blender (x, y, z) | Unreal (X, Y, Z) cm | Where | Source |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | `shop` | (-17, 9.6, -21) | (-17, 21, 9.6) | (-1700, -2100, 960) | shop roof, west | data.js:61 |
| A2 | `shop` | (-3, 9.3, -17) | (-3, 17, 9.3) | (-300, -1700, 930) | shop roof, east | data.js:62 |
| A3 | `shop` | (8.5, 9.6, -24) | (8.5, 24, 9.6) | (850, -2400, 960) | over the alley | data.js:63 |
| A4 | `shop` | (16.5, 13.6, -21) | (16.5, 21, 13.6) | (1650, -2100, 1360) | deli roof | data.js:64 |
| A5 | `avenue` | (-13, 8.8, -8.8) | (-13, 8.8, 8.8) | (-1300, -880, 880) | beside the El, north | data.js:65 |
| A6 | `avenue` | (10, 9.4, 8.9) | (10, -8.9, 9.4) | (1000, 890, 940) | beside the El, south, over the shed | data.js:66 |
| A7 | `avenue` | (-10, 9.6, 20) | (-10, -20, 9.6) | (-1000, 2000, 960) | over the vacant lot | data.js:67 |
| A8 | `avenue` | (8, 10.8, 18.5) | (8, -18.5, 10.8) | (800, 1850, 1080) | S3 roof | data.js:68 |
| A9 | `avenue` | (-23, 16.2, 22) | (-23, -22, 16.2) | (-2300, 2200, 1620) | pawn shop roof | data.js:69 |
| A10 | `avenue` | (4, 8.6, 28.5) | (4, -28.5, 8.6) | (400, 2850, 860) | over the rear lane | data.js:70 |
| A11 | `lot` | (30, 9.2, -27) | (30, 27, 9.2) | (3000, -2700, 920) | over the court, north-west | data.js:71 |
| A12 | `lot` | (40, 9.6, -18) | (40, 18, 9.6) | (4000, -1800, 960) | over the court, south-east | data.js:72 |
| A13 | `lot` | (35, 9, -8.9) | (35, 8.9, 9) | (3500, -890, 900) | beside the El at the cage | data.js:73 |
| A14 | `lot` | (31, 10, 20) | (31, -20, 10) | (3100, 2000, 1000) | over the lot, west | data.js:74 |
| A15 | `lot` | (41.5, 12.6, 16) | (41.5, -16, 12.6) | (4150, 1600, 1260) | behind the billboard | data.js:75 |
| A16 | `lot` | (43, 9.2, 26.5) | (43, -26.5, 9.2) | (4300, 2650, 920) | over the truck | data.js:76 |
| A17 | `lot` | (40.5, 9.4, 9) | (40.5, -9, 9.4) | (4050, 900, 940) | beside the El at the lot | data.js:77 |

How a point is chosen at run time (scoring, jitter, the alive cap) is in `04-flow.md`
(`src/config/flow.js:57-80`).

#### 2.13.5 Cover points for the AI (`data.js:84-113`, `level.js:139`)

`level.coverPoints` = 100 standing spots beside something solid, each tagged with its zone; 97 on the ground, two on
the shed deck (y 2.95) and one on the mezzanine (y 2.8). 19 ground points were moved by the nudge (3.4):
the bold position is the one the running game uses.

| zone | cover points |
| --- | --- |
| `west` | 3 |
| `shop` | 15 |
| `avenue` | 45 |
| `lot` | 37 |
| **total** | 100 |

| Group | n | Points: authored web (x, z); bold = effective position after the nudge | Source |
| --- | --- | --- | --- |
| avenue, west of the reel | 11 | C1 (-37.2, -3.8); C2 (-33.1, -0.5); C3 (-31.2, 2.2); C4 (-27.6, 2.2); C5 (-24.1, -2.4); C6 (-19.2, 0.5); C7 (-14.4, -0.7); C8 (-24.6, 8.2); C9 (-19.5, 7.9); C10 (-26.3, -8.2); C11 (-21.6, -7.8) | data.js:85-87 |
| the reel 1 arena | 9 | C12 (-13.2, 1.2); C13 (-8.4, -1.4); C14 (-7.6, -3.6); C15 (-4.3, -4); C16 (-3.6, -1.9); C17 (0.9, -1.6) → **(2.25, -1.75)**; C18 (0.2, 4.3); C19 (-6.9, 5.2) → **(-6.75, 5.75)**; C20 (-3, 8.3) | data.js:88-89 |
| the second curtain | 14 | C21 (6.8, -0.8); C22 (2.2, 2.2) → **(2.25, 1.25)**; C23 (11.7, 1.4); C24 (16.3, 1.2); C25 (10.6, -3.5); C26 (11.4, -1); C27 (19.9, -2.4); C28 (19.3, 2); C29 (21.5, 2); C30 (15.2, 3.7); C31 (4, -8.3); C32 (16.5, -9.6); C33 (22.2, -8.6); C34 (20, 6.2) | data.js:90-92 |
| crossing to roadblock | 9 | C35 (26.5, 2.6); C36 (28.7, 2.6); C37 (29.6, -3); C38 (27.2, -3.1); C39 (33.3, 0.5); C40 (36.9, -0.8); C41 (34.4, -2.6) → **(33.75, -2.75)**; C42 (36.4, 3.2) → **(36.75, 3.25)**; C43 (38, 1.4) | data.js:93-94 |
| shop front and interior | 15 | C44 (-17.9, -9.1) → **(-17.25, -8.75)**; C45 (-8.4, -9.9); C46 (3.4, -9.4); C47 (-13.8, -14); C48 (-10.5, -14.6); C49 (-6, -19.3); C50 (-5, -21); C51 (-13.4, -22.2) → **(-13.75, -22.25)**; C52 (-9.9, -26.6); C53 (1.1, -19.6); C54 (-16.2, -17.3); C55 (-22, -17.3); C56 (3.4, -13.9); C57 (-8, -13.2); C58 (-19.5, -26, y 2.8) | data.js:95-98 |
| alley and cut | 4 | C59 (9, -14.4) → **(8.75, -14.25)**; C60 (7.9, -27.1) → **(8.25, -27.25)**; C61 (9.3, -24.6); C62 (24, -18) | data.js:99-100 |
| the cage | 11 | C63 (34.1, -18.1) → **(34.25, -17.75)**; C64 (33.6, -22) → **(34.25, -22.25)**; C65 (31.6, -24.6) → **(31.25, -24.75)**; C66 (36, -27.4) → **(35.75, -27.75)**; C67 (39, -21.6) → **(38.75, -22.25)**; C68 (30.4, -21.7); C69 (29.6, -30); C70 (41, -30); C71 (28.6, -14) → **(28.75, -14.25)**; C72 (32, -10.3); C73 (37, -10.3) | data.js:101-103 |
| vacant lot | 4 | C74 (-13.5, 17); C75 (-9.2, 20.5); C76 (-7.2, 15.8); C77 (-6.1, 20.3) | data.js:104-105 |
| rear lane | 6 | C78 (-10.6, 27.8); C79 (-0.7, 27.7); C80 (4.5, 29.2); C81 (13.2, 27.9); C82 (16.4, 28.9) → **(16.25, 28.25)**; C83 (20.6, 28.3) | data.js:106-107 |
| the lot | 15 | C84 (28.3, 15.5); C85 (28.4, 18.1); C86 (28.7, 23.3); C87 (33.2, 15.8); C88 (33.3, 18.4); C89 (39.9, 18.4); C90 (39.8, 23.6); C91 (32.2, 26.3) → **(31.75, 26.25)**; C92 (30.5, 28.6) → **(30.25, 28.25)**; C93 (32.4, 28.7) → **(32.75, 28.75)**; C94 (34.6, 31.8); C95 (39.6, 27.5); C96 (41.6, 24.9); C97 (41.7, 27); C98 (43.8, 23.6) | data.js:108-110 |
| the shed deck | 2 | C99 (5.4, 8.9, y 2.95); C100 (12.8, 8.9, y 2.95) | data.js:111-112 |

Every ground cover point has a nav-blocking obstacle within 1.5 m (`test/level-layout.test.js:193-213`). The three
raised points (C58, C99, C100) are out of every Goon's reach in the web game: its nav grid is one flat layer and both
stairs are obstacles in it (`03-enemies.md` 3.7.3).

#### 2.13.6 Explosives (`data.js:119-141`, `level.js:143`)

`level.explosives` = 21 placements, 13 propane tanks and 8 welding racks, part of the cover layout and solid until
they blow (`02-weapons-combat.md` owns their behaviour). Catalogue sizes: propane tank 0.32 × 0.32 × 0.6, welding rack
0.9 long × 0.5 deep × 1.6 high (`src/config/catalog.js:142-143`). Rules the layout keeps
(`test/level-layout.test.js:237-273`): 18 to 22 in all, at least 8 propane and 5 racks, none within 7 m of the start
or 2.2 m of a reel, none within 0.8 m of another.

| # | type | zone | web (x, y, z) | web yaw | Unreal (X, Y, Z) cm | Unreal yaw | Where | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| X1 | propane tank | `avenue` | (-4.2, 0.15, -7.85) | 0° | (-420, -785, 15) | 0° | two at the food cart | data.js:120 |
| X2 | propane tank | `avenue` | (-4.2, 0.15, -8.7) | 0° | (-420, -870, 15) | 0° | two at the food cart (second) | data.js:121 |
| X3 | welding rack | `avenue` | (-22.6, 0.15, -10.62) | 0° | (-2260, -1062, 15) | 0° | outside the shop, beside the tyre cage | data.js:122 |
| X4 | welding rack | `shop` | (-20.4, 0, -13.6) | 90° | (-2040, -1360, 0) | -90° | the welding corner inside | data.js:123 |
| X5 | welding rack | `shop` | (3.4, 0, -17.6) | 90° | (340, -1760, 0) | -90° | by the east lift | data.js:124 |
| X6 | welding rack | `shop` | (-14.3, 0, -23.4) | 17.2° | (-1430, -2340, 0) | -17.2° | at the foot of the mezzanine stair | data.js:125 |
| X7 | propane tank | `shop` | (-3.4, 0, -30.1) | 0° | (-340, -3010, 0) | 0° | the north bench | data.js:126 |
| X8 | welding rack | `shop` | (6.55, 0, -19.6) | 90° | (655, -1960, 0) | -90° | the alley, beside the shop's side door | data.js:127 |
| X9 | propane tank | `avenue` | (0.35, 0.15, 7.8) | 0° | (35, 780, 15) | 0° | the foot of the shed | data.js:128 |
| X10 | propane tank | `avenue` | (9.3, 2.95, 10.35) | 0° | (930, 1035, 295) | 0° | on the shed deck | data.js:129 |
| X11 | propane tank | `avenue` | (17.6, 0.15, 10.45) | 0° | (1760, 1045, 15) | 0° | the east end of the shed | data.js:130 |
| X12 | propane tank | `lot` | (25.9, 0, 12.9) | 0° | (2590, 1290, 0) | 0° | the lot booth, both sides | data.js:131 |
| X13 | propane tank | `lot` | (28.8, 0, 13.7) | 0° | (2880, 1370, 0) | 0° | the lot booth, both sides (second) | data.js:132 |
| X14 | propane tank | `avenue` | (-12.9, 0, 16.3) | 0° | (-1290, 1630, 0) | 0° | the vacant lot, by the burned car | data.js:133 |
| X15 | welding rack | `avenue` | (5.9, 0, 30.55) | 0° | (590, 3055, 0) | 0° | the rear lane, between two garage doors | data.js:134 |
| X16 | propane tank | `avenue` | (18.3, 0, 26.5) | 0° | (1830, 2650, 0) | 0° | the rear lane, east end | data.js:135 |
| X17 | propane tank | `lot` | (43.3, 0, -30.5) | 0° | (4330, -3050, 0) | 0° | the cage, by the bleachers | data.js:136 |
| X18 | welding rack | `lot` | (32.6, 0, 33.55) | 0° | (3260, 3355, 0) | 0° | the lot's south wall, short of the truck | data.js:137 |
| X19 | propane tank | `lot` | (39.6, 0, 20.9) | 0° | (3960, 2090, 0) | 0° | the lot's east aisle | data.js:138 |
| X20 | propane tank | `lot` | (39.8, 0, -6.4) | 0° | (3980, -640, 0) | 0° | the roadblock | data.js:139 |
| X21 | propane tank | `avenue` | (8.9, 0, -1.5) | 0° | (890, -150, 0) | 0° | the avenue, at the barrier chicane | data.js:140 |

#### 2.13.7 Steam points (`level.steam`, `level.js:199`)

| # | web (x, y, z) | Unreal (X, Y, Z) cm | What | Source (src/level/) |
| --- | --- | --- | --- | --- |
| 1 | (-22.5, 0.05, -1.8) | (-2250, -180, 5) | manhole, avenue (westbound lane) | ground.js:189-191 |
| 2 | (6.4, 0.05, -2.4) | (640, -240, 5) | manhole, avenue (westbound lane) | ground.js:189-191 |
| 3 | (30.5, 0.05, -0.9) | (3050, -90, 5) | manhole, avenue east of the crossing | ground.js:189-191 |
| 4 | (8.5, 0.05, -24.6) | (850, -2460, 5) | grate in the alley | yards.js:47 |
| 5 | (1.8, 0.05, 28.4) | (180, 2840, 5) | grate in the rear lane | yards.js:380 |
| 6 | (19.5, 3.85, -8.1) | (1950, -810, 385) | top of the striped steam stack in the utility dig | street.js:330 |

#### 2.13.8 Title fly-through (`level.cinematicPath`, `data.js:153-168`)

Fourteen held compositions flown as one centripetal Catmull-Rom curve through the camera positions while the camera
looks along a second curve through the look-at points (`src/game/titlecam.js:13-21`; speed, loop length and sway are
`src/config/flow.js:29-38`). The route: under the El at the station, east along the avenue past the first scaffold and
the Vultures' van to reel 1, into the shop by the roll door, across its floor, out of the side door and down the
alley, east under the El, a look through the cage's south gate at reel 3, a turn to the lot, the truck. Both the
straight legs and the flown curve clear every collider (`test/level-layout.test.js:451-499`).

| # | web camera (x, y, z) | web look-at (x, y, z) | Unreal camera cm | Unreal look-at cm |
| --- | --- | --- | --- | --- |
| 1 | (-38.6, 4.4, -1.6) | (-5, 2, -0.5) | (-3860, -160, 440) | (-500, -50, 200) |
| 2 | (-31.5, 4.2, -2.5) | (-12, 1.8, 0.5) | (-3150, -250, 420) | (-1200, 50, 180) |
| 3 | (-21, 3.3, 2.6) | (-9, 1.4, 1.5) | (-2100, 260, 330) | (-900, 150, 140) |
| 4 | (-13.4, 2.4, -0.4) | (-3, 1, -1.5) | (-1340, -40, 240) | (-300, -150, 100) |
| 5 | (-6.6, 2.2, -4) | (-4, 0.8, 1) | (-660, -400, 220) | (-400, 100, 80) |
| 6 | (-12.4, 2.3, -5.6) | (-11.6, 2, -14) | (-1240, -560, 230) | (-1160, -1400, 200) |
| 7 | (-10.2, 2.1, -13.4) | (-9.5, 0.9, -21.5) | (-1020, -1340, 210) | (-950, -2150, 90) |
| 8 | (-14.2, 4.2, -22.6) | (-4, 1.2, -19) | (-1420, -2260, 420) | (-400, -1900, 120) |
| 9 | (6.4, 2, -22.1) | (8.8, 2.4, -10) | (640, -2210, 200) | (880, -1000, 240) |
| 10 | (12, 3.6, -1.4) | (24, 2, 1) | (1200, -140, 360) | (2400, 100, 200) |
| 11 | (31.5, 3.8, -3) | (35.25, 1, -22.5) | (3150, -300, 380) | (3525, -2250, 100) |
| 12 | (30.5, 4.6, -1) | (40, 2.4, 22) | (3050, -100, 460) | (4000, 2200, 240) |
| 13 | (32.2, 3.4, 14.6) | (40.5, 1.6, 28.5) | (3220, 1460, 340) | (4050, 2850, 160) |
| 14 | (34.6, 1.8, 27.8) | (42, 1.7, 30.2) | (3460, 2780, 180) | (4200, 3020, 170) |

### 2.14 Lamp hints (`level.lamps`)

The level does not create lights. It publishes 90 lamp hints `{pos, color, intensity, range, kind, priority, dir?}`
(`kit.js:571-583`) that the atmosphere module turns into real lights, light pools and cones; 61 are
written by level code, 29 come from the props it places (a prop's hints are transformed with the prop:
`kit.js:637-646`). `intensity` and `range` are three.js point-light numbers as authored (relative weights for the web
renderer, not photometric values). `priority` is the level's ranking of which lamps deserve one of the few real
lights (`kit.js:54`; a prop's own work light ranks 6, `kit.js:642`); the atmosphere uses it only to break ties
(`06-look-fx.md` 3.4). `aim` is a unit vector for lamps that point.

| kind | count | default priority (kit.js:54) |
| --- | --- | --- |
| work | 17 | 10 |
| flood | 4 | 9 |
| street | 22 | 6 |
| el | 15 | 5 |
| neon | 19 | 4 |
| window | 13 | 2 |
| **total** | 90 |  |

| # | What | kind | web (x, y, z) | colour | intensity | range (m) | priority | aim (web x, y, z) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1–9 | El: sodium lamp hung under the deck | el | (-40, 5.5, 2.1) (-30, 5.5, -2.1) (-20, 5.5, 2.1) (-10, 5.5, -2.1) (0, 5.5, 2.1) (10, 5.5, -2.1) (20, 5.5, 2.1) (30, 5.5, -2.1) (40, 5.5, 2.1) | #ffb45e | 30 | 13 | 5 | (0, -1, 0) |
| 10 | station mezzanine window glow | window | (-38.8, 5.3, 0) | #ffc98a | 8 | 7 | 2 | — |
| 11 | station stair green globes, north | neon | (-38.54, 3.15, -8.15) | #55ff8a | 6 | 6 | 3 | — |
| 12–14 | north platform canopy tube | el | (-43.5, 9.9, -5.4) (-38, 9.9, -5.4) (-32.5, 9.9, -5.4) | #cfe4ff | 10 | 9 | 2 | — |
| 15 | station stair green globes, south | neon | (-38.54, 3.15, 8.15) | #55ff8a | 6 | 6 | 3 | — |
| 16–18 | south platform canopy tube | el | (-43.5, 9.9, 5.4) (-38, 9.9, 5.4) (-32.5, 9.9, 5.4) | #cfe4ff | 10 | 9 | 2 | — |
| 19 | sign: 24 HR LAUNDROMAT | neon | (-41.6, 3.25, -10.3) | #cfe4ff | 9 | 9 | 4 | — |
| 20 | laundromat interior | window | (-41.6, 1.9, -9.5) | #cfe4ff | 10 | 9 | 2 | — |
| 21 | tenement residents' transom | window | (-35.8, 2.8, -10.5) | #ffc98a | 6 | 6 | 2 | — |
| 22 | sign: CROWN & FADE BARBER | neon | (-30.3, 3.25, -10.3) | #ff3030 | 12 | 9 | 4 | — |
| 23 | service door, gangway | street | (-25.1, 2.3, -15.6) | #ffc98a | 14 | 8 | 3 | — |
| 24 | sign: HOLLIS DELI & GROCERY | neon | (16.5, 3.25, -10.3) | #ffd24a | 9 | 9 | 4 | — |
| 25 | deli interior | window | (16.5, 1.9, -9.5) | #ffc98a | 10 | 9 | 2 | — |
| 26 | service door, deli alley side | street | (10.6, 2.3, -15.5) | #ffc98a | 14 | 8 | 3 | — |
| 27 | service door, deli cut side | street | (22.4, 2.3, -27.5) | #cfe4ff | 14 | 8 | 3 | — |
| 28 | sign: CHECKS CASHED | neon | (-42.15, 3.25, 10.3) | #55ff8a | 12 | 9 | 4 | — |
| 29 | sign: 99¢ PIZZA | neon | (-34.15, 3.25, 10.3) | #ff5a3a | 9 | 9 | 4 | — |
| 30 | pizza interior | window | (-34.15, 1.9, 9.5) | #ffc98a | 10 | 9 | 2 | — |
| 31 | sign: PAWN & GOLD | neon | (-27, 3.25, 10.3) | #f6c21a | 12 | 9 | 4 | — |
| 32 | sign: TAPES · RECORDS · CDs | neon | (-18.9, 3.25, 10.3) | #35e0ff | 12 | 9 | 4 | — |
| 33 | pawn vestibule soffit lamp | window | (-22.9, 2.6, 12.2) | #ffc98a | 7 | 6 | 2 | — |
| 34 | sign: GOLDEN BIRD CHICKEN | neon | (0.5, 3.25, 10.3) | #ffc84a | 9 | 9 | 4 | — |
| 35 | chicken interior | window | (0.5, 1.9, 9.5) | #ffc98a | 10 | 9 | 2 | — |
| 36 | sign: WINES & LIQUORS | neon | (9.25, 3.25, 10.3) | #ff3030 | 12 | 9 | 4 | — |
| 37 | sign: LUCKY NAILS | neon | (17.75, 3.25, 10.3) | #ff3d9a | 12 | 9 | 4 | — |
| 38 | service door, S3 west (vacant lot) | street | (-4.4, 2.3, 22.8) | #ffc98a | 14 | 8 | 3 | — |
| 39 | service door, S3 back (lane) | street | (-1.6, 2.3, 26.4) | #ffc98a | 14 | 8 | 3 | — |
| 40 | service door, S3 back (lane) | street | (17.4, 2.3, 26.4) | #cfe4ff | 14 | 8 | 3 | — |
| 41–43 | garage wall lamp | street | (-7.1, 3, 30.6) (6.1, 3, 30.6) (19.3, 3, 30.6) | #ffb45e | 18 | 10 | 4 | — |
| 44 | shop: EXIT sign | neon | (5.3, 2.85, -22.1) | #ff3030 | 4 | 4 | 2 | — |
| 45 | shop side door lamp (alley face) | street | (6.5, 2.85, -22.1) | #ffc48a | 16 | 9 | 4 | — |
| 46 | shop office ceiling tube | work | (-20.6, 5, -28.8) | #fff1d0 | 14 | 8 | 5 | — |
| 47 | shop: wall tube under the mezzanine | work | (-20, 2.4, -30.2) | #cfe4ff | 8 | 6 | 3 | — |
| 48 | prop: vending machine (shop) | neon | (4.5, 1.2, -13.3) | #9fd4ff | 12 | 5 | 4 | — |
| 49–52 | shop high-bay work light | work | (-18.2, 5, -17.2) (-9.2, 5, -22.4) (-9.2, 5, -14.6) (0.6, 5, -21.2) | #ffc48a | 34 | 13 | 10 | (0, -1, 0) |
| 53 | sign: V&R AUTO BODY | neon | (-12, 5.4, -10.2) | #f6c21a | 14 | 10 | 4 | — |
| 54–56 | shop gooseneck lamp over the fascia | street | (-21.5, 6.2, -10.28) (-12, 6.2, -10.28) (-1.3, 6.2, -10.28) | #ffc48a | 16 | 10 | 4 | (0, -1, 0) |
| 57–58 | prop: court light | flood | (25.6, 8.5, -12.95) (44.8, 8.5, -32.3) | #dfe8ff | 160 | 30 | 9 | (0, -1, 0) |
| 59 | prop: floodlight stand (vacant lot) | work | (-9.6, 2, 13.05) | #fff1d0 | 60 | 14 | 6 | (0, -0.32, -0.95) |
| 60 | prop: lot booth | window | (27.3, 1.6, 13.55) | #ffc48a | 14 | 6 | 2 | — |
| 61 | prop: lot booth | neon | (27.3, 0.6, 13.55) | #f6c21a | 6 | 4 | 4 | — |
| 62 | PARK pylon sign | neon | (34.65, 4.7, 11.65) | #35e0ff | 12 | 9 | 4 | — |
| 63–64 | prop: billboard flood | flood | (38.5, 7.1, 13) (42.9, 7.1, 13) | #fff1d6 | 40 | 12 | 9 | (0, 0.9, -0.44) |
| 65–66 | prop: street lamp (lot) | street | (39.3, 7.6, 16.11) (30.9, 7.6, 31.29) | #ffb45e | 90 | 20 | 6 | (0, -1, 0) |
| 67–68 | prop: IPX truck headlight | work | (45.3, 0.9, 30.38) (45.3, 0.9, 29.02) | #fff0d0 | 22 | 9 | 6 | (0.97, -0.24, 0) |
| 69 | prop: IPX truck rear-door light | work | (37.5, 2.46, 29.7) | #fff1d6 | 26 | 9 | 6 | (-0.29, -0.96, 0) |
| 70 | prop: floodlight stand (west closure) | work | (-44.9, 2, -2.9) | #fff1d0 | 60 | 14 | 6 | (-0.95, -0.32, 0) |
| 71 | prop: floodlight stand (roadblock) | work | (44.45, 2.15, 7.9) | #fff1d0 | 60 | 14 | 6 | (0.95, -0.32, 0) |
| 72–74 | shed: caged bulbs under the deck | work | (2.6, 2.45, 9.2) (8.52, 2.45, 9.2) (14.44, 2.45, 9.2) | #fff1d0 | 9 | 7 | 3 | — |
| 75 | produce stand bulbs | window | (13.3, 2.4, -9.2) | #ffc98a | 12 | 8 | 3 | — |
| 76 | site shanty door lamp | work | (-16, 2.5, 8.2) | #fff1d0 | 9 | 7 | 3 | — |
| 77 | prop: phone booth | window | (-44.5, 2.05, -10.15) | #dfe8ff | 7 | 4.5 | 2 | — |
| 78 | prop: street lamp | street | (-22.4, 7.75, -9.78) | #ffb45e | 90 | 20 | 6 | (0, -1, 0) |
| 79 | prop: food cart | work | (-5.5, 1.85, -8.2) | #ffd9a0 | 16 | 6 | 6 | — |
| 80 | prop: vending machine (north sidewalk) | neon | (3.4, 1.35, -9.95) | #9fd4ff | 12 | 5 | 4 | — |
| 81–82 | prop: street lamp | street | (2.6, 7.75, -9.78) (23.9, 7.75, -9.78) | #ffb45e | 90 | 20 | 6 | (0, -1, 0) |
| 83 | prop: bus shelter | neon | (27.8, 1.45, -7.85) | #dfe8ff | 12 | 6 | 4 | — |
| 84 | prop: bus shelter | window | (29.6, 2.35, -7.95) | #dfe8ff | 10 | 5 | 2 | — |
| 85–86 | prop: street lamp | street | (41.6, 7.75, -9.78) (-31.4, 7.75, 9.78) | #ffb45e | 90 | 20 | 6 | (0, -1, 0) |
| 87 | prop: phone booth | window | (-29.2, 2.05, 10.15) | #dfe8ff | 7 | 4.5 | 2 | — |
| 88 | prop: street lamp | street | (22.9, 7.75, 9.78) | #ffb45e | 90 | 20 | 6 | (0, -1, 0) |
| 89 | prop: phone booth | window | (27.3, 2.05, 10.15) | #dfe8ff | 7 | 4.5 | 2 | — |
| 90 | prop: street lamp | street | (36.4, 7.75, 9.78) | #ffb45e | 90 | 20 | 6 | (0, -1, 0) |

Lamps are listed in build order. Besides the hints, every fixture has a glowing lens or tube drawn at the position
given in its section (HDR colour × intensity 2.2 … 6, one shared unlit material: `kit.js:210, 689`). How each kind
is drawn, which lamps get a real light and what they do by day is in `06-look-fx.md` 2.17 and 3.4.

### 2.15 Catalogue prop placements

The level places 308 catalogue props of 60 kinds (`kit.place`, `kit.js:596-655`),
34 of them cars, vans and trucks. A prop's origin is on the ground at the centre of its footprint; it
stands on the level's floor at that point (road 0, sidewalk 0.15) unless a height `y` is given. Yaw is the web yaw in
degrees (2.1): 0° leaves a vehicle's nose pointing east and a +Z-fronted prop facing south; 90° turns a nose north;
180° west; -90° south.

Catalogue props the level does not place:
`traffic_light`, `sign_post`, `fence_panel`, `fence_tall`, `boombox`, `awning`.
The two explosives are placed by their own module from the list in 2.13.6.

Sizes and cover heights of the props used. Sizes are the catalogue's (`src/config/catalog.js:68-144`); "collider
tops" are the top heights of the boxes that stop both walkers and rounds, read from the built props (for a car: the
bonnet-and-boot body, then the cabin). The front axis applies to props that have a front (`docs/CONTRACT.md` 6.2).

| prop | placed | catalogue size: length × height × width (m) | collider tops (m) | surface | front axis |
| --- | --- | --- | --- | --- | --- |
| `ac_unit` | 12 | 1.2 × 0.9 × 0.9 | 0.86 | metal | +Z |
| `barricade` | 6 | 2.4 × 1.1 × 0.5 | 1 | wood | +Z |
| `bench` | 5 | 1.8 × 0.85 × 0.6 | 0.47 / 0.85 | wood | +Z |
| `billboard` | 1 | 9 × 11 × 1.2 | 6.7 / 10.8 | metal | +Z |
| `bleachers` | 3 | 4 × 1.6 × 2 | 0.42 / 0.78 / 1.14 / 1.5 | metal | +Z |
| `bollard` | 4 | 0.2 × 1 × 0.2 | 1 | metal | +Z |
| `box_truck` | 3 | 7.4 × 3.3 × 2.45 | 2.28 / 3.3 | car | +X |
| `burned_car` | 1 | 4.5 × 1.3 × 1.8 | 0.96 | car | +X |
| `bus_shelter` | 1 | 3.6 × 2.5 × 1.5 | 0.5 / 2.2 / 2.3 / 2.48 | glass | +Z |
| `car_lift` | 2 | 4.8 × 3.6 × 3.2 | 3.5 | metal | +Z |
| `car_on_stands` | 1 | 4.5 × 1.6 × 1.85 | 1.23 / 1.6 | car | +X |
| `cardboard_boxes` | 9 | 1 × 0.8 × 0.8 | 0.72 | wood | +Z |
| `compressor` | 2 | 1.2 × 1 × 0.6 | 0.9 | metal | +Z |
| `court_light` | 2 | 0.4 × 9 × 0.4 | 8.55 | metal | +Z |
| `crate_wood` | 8 | 1.1 × 1 × 0.9 | 1 | wood | +Z |
| `dumpster` | 6 | 1.9 × 1.35 × 1.1 | 1.3 | metal | +Z |
| `engine_hoist` | 2 | 1.6 × 2 × 1.2 | 0.16 / 1.38 / 1.6 | metal | +Z |
| `fire_escape` | 11 | 3 × 3 × 1.1 | none (no collision) | metal | +Z |
| `floodlight_stand` | 3 | 1 × 2.2 × 1 | 2.15 | metal | +Z |
| `food_cart` | 1 | 2.4 × 2.25 × 1.4 | 1.25 | metal | +Z |
| `generator` | 1 | 2.2 × 1.4 × 1 | 1.22 | metal | +Z |
| `hoop` | 2 | 1.8 × 4 × 1.2 | 3.4 / 4 | metal | +X |
| `hydrant` | 2 | 0.35 × 0.75 × 0.35 | 0.74 | metal | +Z |
| `hydrant_open` | 1 | 0.35 × 0.75 × 0.35 | 0.74 | metal | +Z |
| `ipx_truck` | 1 | 6.8 × 3 × 2.5 | 2.58 / 2.86 | car | +X |
| `jersey_barrier` | 16 | 3 × 0.81 × 0.6 | 0.81 | concrete | +Z |
| `lot_booth` | 1 | 2.2 × 2.6 × 1.8 | 2.37 | metal | +Z |
| `mailbox` | 2 | 0.55 × 1.25 × 0.55 | 1.2 | metal | +Z |
| `manhole` | 6 | 0.9 × 0.02 × 0.9 | none (no collision) | metal | +Z |
| `master_case` | 3 | 0.9 × 1.05 × 0.6 | 0.66 | metal | +Z |
| `mattress` | 1 | 1.9 × 0.25 × 0.95 | none (no collision) | cloth | +Z |
| `milk_crates` | 10 | 0.7 × 1 × 0.7 | 0.9 | rubber | +Z |
| `motorbike` | 3 | 2 × 1.1 × 0.7 | 0.95 | metal | +X |
| `newspaper_box` | 7 | 0.5 × 1.1 × 0.45 | 1.08 | metal | +Z |
| `oil_drum` | 14 | 0.6 × 0.9 × 0.6 | 0.9 | metal | +Z |
| `pallet` | 4 | 1.2 × 0.144 × 1 | walked over (0.14) | wood | +Z |
| `pallet_stack` | 9 | 1.2 × 1.15 × 1 | 1.15 | wood | +Z |
| `parking_meter` | 8 | 0.2 × 1.3 × 0.2 | 1.3 | metal | +Z |
| `phone_booth` | 3 | 0.9 × 2.2 × 0.9 | 2.2 | metal | +Z |
| `pickup` | 2 | 5.3 × 1.8 × 2 | 1.27 / 1.78 | car | +X |
| `planter` | 3 | 1.2 × 0.8 × 1.2 | 0.8 | concrete | +Z |
| `porta_potty` | 2 | 1.2 × 2.3 × 1.2 | 2.25 | rubber | +Z |
| `sandbags` | 5 | 2 × 0.9 × 0.6 | 0.9 | dirt | +Z |
| `sedan` | 13 | 4.6 × 1.45 × 1.85 | 1.08 / 1.45 | car | +X |
| `shelf_rack` | 5 | 2.7 × 3 × 0.9 | 3 | metal | +Z |
| `shopping_cart` | 5 | 0.9 × 1 × 0.55 | 0.95 | metal | +Z |
| `street_lamp` | 9 | 0.4 × 8 × 0.4 | 7.3 | metal | +Z |
| `suv` | 2 | 4.9 × 1.82 × 2 | 1.24 / 1.78 | car | +X |
| `taxi` | 3 | 4.7 × 1.55 × 1.85 | 1.08 / 1.45 | car | +X |
| `tire_stack` | 14 | 0.8 × 1 × 0.8 | 0.98 | rubber | +Z |
| `tool_chest` | 4 | 1.1 × 1.1 × 0.55 | 1.09 | metal | +Z |
| `traffic_barrel` | 13 | 0.6 × 1 × 0.6 | 0.98 | rubber | +Z |
| `traffic_cone` | 10 | 0.36 × 0.7 × 0.36 | none (no collision) | rubber | +Z |
| `trash_bags` | 13 | 1.4 × 0.7 × 1 | 0.62 | cloth | +Z |
| `trash_can` | 6 | 0.6 × 0.95 × 0.6 | 0.95 | metal | +Z |
| `tree` | 3 | 0.6 × 6 × 0.6 | 0.55 / 3 | wood | +Z |
| `van` | 11 | 5.2 × 2.2 × 2 | 2.14 | car | +X |
| `vending_machine` | 2 | 0.9 × 1.85 × 0.8 | 1.85 | metal | +Z |
| `water_tower` | 3 | 3 × 5 × 3 | none (no collision) | wood | +Z |
| `workbench` | 3 | 2.2 × 0.95 × 0.8 | 0.8 | wood | +Z |

Vehicles are painted from a nine-colour chart, #14161a, #2a2d33, #8f959c, #d9d7d0, #6e1a1c, #1b2a4a, #16342a,
#b9b4a6, #c9a23a (`kit.js:61-62`): a colour asked for by the level snaps to the nearest chart entry, and an unpainted
vehicle draws one by its seed (never the mustard #c9a23a) (`kit.js:163-181`). The bracketed colours below are the
effective ones. Taxis are always taxi yellow.

Every placement, grouped by area in build order, as (web x, z[, y]) web yaw [options]. `05b-props.md` Appendix A
lists the same 308 placements grouped by prop, with the shape variant each seed picks.

| Area (props) source | prop | n | placements |
| --- | --- | --- | --- |
| **Avenue manholes** (6) `ground.js:189-192` | `manhole` | 6 | (-22.5, -1.8) 128.9°; (-9.5, 2.6) 14.3°; (6.4, -2.4) 139.3°; (18.6, 1.9) 146.3°; (30.5, -0.9) 131°; (-36, 2.2) 24.8° |
| **Building fronts and roofs** (24) `buildings.js:221-223, 284-398` | `fire_escape` | 11 | (-30.6, -10.45, y 4.05) 0°; (-30.6, -10.45, y 7.15) 0°; (-30.6, -10.45, y 10.25) 0°; (-30.6, -10.45, y 13.35) 0°; (10.45, -20.5, y 4.05) -90°; (10.45, -20.5, y 7.15) -90°; (-42.5, 10.45, y 4.05) -180°; (-42.5, 10.45, y 7.15) -180°; (-27, 10.45, y 4.05) -180°; (-27, 10.45, y 7.15) -180°; (-27, 10.45, y 10.25) -180° |
|  | `water_tower` | 3 | (-40, -24, y 16.2) 0°; (16.5, -29, y 10) 0°; (-23, 24, y 13.1) 0° |
|  | `ac_unit` | 10 | (-31, -15, y 16.2) 17.2°; (-33.5, -27, y 16.2) 68.8°; (14, -15, y 10) 0°; (18.5, -22, y 10) 90°; (-41, 15, y 10) 0°; (-34, 22, y 10) 45.8°; (-27, 16, y 13.1) 0°; (1, 15, y 6.9) 0°; (9.5, 22, y 6.9) 90°; (17, 14.5, y 6.9) 22.9° |
| **Chop shop: door bollards** (4) `shop.js:128` | `bollard` | 4 | (-15.45, -10.65) 0° [#f2c21a]; (-8.55, -10.65) 0° [#f2c21a]; (-3.65, -10.65) 0° [#f2c21a]; (1.05, -10.65) 0° [#f2c21a] |
| **Chop shop: on the mezzanine (y 2.8) and under it** (9) `shop.js:199-244` | `workbench` | 1 | (-21.2, -29.9, y 2.8) 0° |
|  | `tool_chest` | 1 | (-23.1, -28.2, y 2.8) 90° |
|  | `tire_stack` | 2 | (-22.6, -29.6) 0°; (-21.6, -29.9) 0° |
|  | `oil_drum` | 2 | (-17.2, -30) 0°; (-16.4, -29.7) 0° |
|  | `pallet_stack` | 1 | (-19.4, -29.8) 0° |
|  | `cardboard_boxes` | 1 | (-22.8, -26.4) 17.2° |
|  | `compressor` | 1 | (-16.6, -26.6) 90° |
| **Chop shop: floor** (31) `shop.js:253-287` | `car_lift` | 2 | (-19.2, -17.3) 90°; (-1.3, -19.6) 90° |
|  | `sedan` | 2 | (-19.2, -17.3, y 1.95) 90° [#16342a, seed 2]; (-1.3, -19.5) -90° [#d9d7d0, seed 5] |
|  | `car_on_stands` | 1 | (-12.2, -15.4) 96.9° |
|  | `tool_chest` | 3 | (-7.1, -19.5) 22.9°; (-12.6, -23.1) 77.3°; (-4.6, -30.22) 0° |
|  | `oil_drum` | 3 | (-12.1, -19.4) 0°; (-11.4, -20.1) 0°; (-4.2, -11.95) 0° |
|  | `tire_stack` | 4 | (-6.5, -23.4) 0°; (-7.3, -24.1) 0°; (-8.2, -12) 0°; (-7.3, -12.1) 0° |
|  | `engine_hoist` | 2 | (-9.9, -25.3) 11.5°; (-16.9, -12.7) 68.8° |
|  | `crate_wood` | 2 | (-13.4, -20.9) 11.5°; (2.6, -15.2) 22.9° |
|  | `milk_crates` | 1 | (-9.2, -18.2) 0° |
|  | `workbench` | 2 | (-6.5, -30.1) 0°; (-21.6, -11.95) 0° |
|  | `shelf_rack` | 5 | (-0.4, -30.05) 0°; (5.05, -28.5) 90°; (5.05, -25.4) 90°; (5.05, -17.3) 90°; (-23.05, -22.3) 90° |
|  | `pallet_stack` | 1 | (2.9, -29.6) 5.7° |
|  | `cardboard_boxes` | 1 | (1.4, -27.6) 28.6° |
|  | `vending_machine` | 1 | (5.1, -13.2) -90° |
|  | `compressor` | 1 | (3.6, -11.9) 0° |
| **Chop shop: roof** (2) `shop.js:326-327` | `ac_unit` | 2 | (-15, -27, y 6.3) 0°; (2.5, -14.5, y 6.3) 90° |
| **Alley** (9) `yards.js:38-46` | `dumpster` | 2 | (10.3, -12.95) 90°; (6.72, -27.3) 90° |
|  | `trash_bags` | 2 | (10.2, -18.3) 22.9°; (6.9, -29.6) 108.9° |
|  | `milk_crates` | 1 | (10.45, -19.9) 0° |
|  | `cardboard_boxes` | 1 | (10.3, -23.6) 11.5° |
|  | `pallet_stack` | 1 | (10.25, -26.4) 90° |
|  | `oil_drum` | 1 | (6.55, -17.6) 0° |
|  | `pallet` | 1 | (7.1, -14.6) 17.2° |
| **The cut** (5) `yards.js:76-80` | `dumpster` | 1 | (22.62, -16.4) 90° |
|  | `trash_bags` | 1 | (22.7, -19) 68.8° |
|  | `milk_crates` | 1 | (22.5, -30.6) 0° |
|  | `cardboard_boxes` | 1 | (22.6, -31.9) 34.4° |
|  | `pallet` | 1 | (23.4, -13.6) 11.5° |
| **The Cage** (20) `yards.js:162-181` | `hoop` | 2 | (26.25, -22.5) 0°; (44.25, -22.5) -180° |
|  | `bleachers` | 3 | (29.6, -31.7) 0°; (35.25, -31.7) 0°; (40.9, -31.7) 0° |
|  | `court_light` | 2 | (25.6, -12.95) 0°; (44.8, -32.3) 0° |
|  | `bench` | 2 | (28.6, -12.95) 0°; (40.6, -12.95) 0° |
|  | `trash_can` | 1 | (31.3, -12.9) 0° |
|  | `sandbags` | 1 | (34.1, -19.1) 14.3° |
|  | `crate_wood` | 1 | (32.7, -21.3) 28.6° |
|  | `oil_drum` | 1 | (32.5, -24.6) 0° |
|  | `motorbike` | 1 | (31.3, -22.9) 71.6° |
|  | `pallet_stack` | 1 | (35.9, -26.4) 8.6° |
|  | `milk_crates` | 1 | (37.3, -24.7) 0° |
|  | `tire_stack` | 2 | (37.8, -20.2) 0°; (38.6, -20.9) 0° |
|  | `cardboard_boxes` | 1 | (43.3, -17.2) 22.9° |
|  | `shopping_cart` | 1 | (28.4, -16.6) 40.1° |
| **Vacant lot** (15) `yards.js:298-313` | `burned_car` | 1 | (-11.2, 18.6) 51.6° |
|  | `tire_stack` | 2 | (-14.7, 14.1) 0°; (-13.8, 14.9) 0° |
|  | `mattress` | 1 | (-6.3, 14.3) 17.2° |
|  | `shopping_cart` | 3 | (-7.4, 21.9) 68.8°; (-5.4, 23.4) 149°; (-14.2, 22.8) 28.6° |
|  | `trash_bags` | 2 | (-5.1, 12.4) 11.5°; (-15, 24.8) 80.2° |
|  | `oil_drum` | 1 | (-8.3, 15.9) 0° |
|  | `cardboard_boxes` | 1 | (-14.8, 19) 17.2° |
|  | `pallet` | 1 | (-13.3, 19.9) 28.6° |
|  | `crate_wood` | 1 | (-6.2, 19.1) 22.9° |
|  | `milk_crates` | 1 | (-8.9, 24.1) 0° |
|  | `floodlight_stand` | 1 | (-9.6, 13.3) -180° |
| **Rear lane (two props stand on the loading dock)** (13) `yards.js:363-379` | `pallet_stack` | 2 | (11.7, 26.7, y 1) 0°; (-13.8, 30.3) 5.7° |
|  | `cardboard_boxes` | 1 | (7, 26.6, y 1) 17.2° |
|  | `dumpster` | 2 | (-2.3, 26.62) 0°; (-1.7, 30.38) 0° |
|  | `trash_bags` | 2 | (1.5, 30.4) 17.2°; (21.1, 26.7) 63° |
|  | `oil_drum` | 2 | (-15.2, 27.1) 0°; (-14.5, 27.8) 0° |
|  | `crate_wood` | 1 | (4.5, 30.4) 11.5° |
|  | `milk_crates` | 1 | (13.9, 26.45) 0° |
|  | `van` | 1 | (-7.6, 29.6) 2.3° [#b9b4a6] |
|  | `pickup` | 1 | (17.4, 29.85) -180° [#2a2d33, seed 6] |
| **Parking lot** (25) `yards.js:403, 442-469` | `lot_booth` | 1 | (27.3, 12.55) 0° |
|  | `sedan` | 4 | (24.95, 15.5) -180° [#16342a, seed 2]; (36.5, 23.6) -180° [#d9d7d0, seed 0]; (24.5, 31.6) -90° [#14161a, seed 3]; (29.7, 31.55) 90° [#d9d7d0, seed 5] |
|  | `suv` | 1 | (25.05, 18.1) -180° [#8f959c, seed 4] |
|  | `pickup` | 1 | (25.2, 23.3) 0° [#2a2d33, seed 6] |
|  | `taxi` | 1 | (36.5, 15.8) -180° |
|  | `van` | 1 | (36.6, 18.4) 0° [#1b2a4a] |
|  | `pallet_stack` | 2 | (33.2, 26.6) 11.5°; (34.6, 32.8) 5.7° |
|  | `oil_drum` | 1 | (34.4, 27.3) 0° |
|  | `jersey_barrier` | 2 | (31.4, 28.6) 98.6°; (41.6, 25.9) 5.7° |
|  | `tire_stack` | 1 | (39.6, 26.4) 0° |
|  | `dumpster` | 1 | (44.9, 23.6) 90° |
|  | `trash_bags` | 1 | (44.7, 32.9) 34.4° |
|  | `shopping_cart` | 1 | (40.6, 14.9) 45.8° |
|  | `traffic_barrel` | 2 | (30.6, 16.9) 0°; (31.4, 17.6) 0° |
|  | `crate_wood` | 1 | (42.4, 14.4) 17.2° |
|  | `billboard` | 1 | (40.7, 12.4) 0° |
|  | `street_lamp` | 2 | (39.3, 13.95) 0°; (30.9, 33.45) -180° |
|  | `ipx_truck` | 1 | (41.3, 29.7) 0° |
| **West closure** (11) `street.js:411-418` | `jersey_barrier` | 4 | (-43.55, -4.6) 90°; (-43.55, -1.55) 90°; (-43.55, 1.5) 90°; (-43.55, 4.55) 90° |
|  | `traffic_barrel` | 2 | (-43.6, -6.45) 0°; (-43.6, 6.4) 0° |
|  | `generator` | 1 | (-44.68, 3.1) 90° |
|  | `floodlight_stand` | 1 | (-44.65, -2.9) -90° |
|  | `pallet_stack` | 1 | (-44.68, 0.3) 90° |
|  | `barricade` | 2 | (-41.3, -2.3) 104.3°; (-41.5, 2.7) 78.6° |
| **Roadblock (east end)** (9) `street.js:440-448` | `box_truck` | 1 | (41.4, 0.3) 60.2° [#2a2d33] |
|  | `jersey_barrier` | 3 | (43.9, -5.5) 90°; (43.9, 5.6) 90°; (38.9, -5.3) 14.3° |
|  | `barricade` | 2 | (41.6, -6.4) 8.6°; (37.4, 4.4) -17.2° |
|  | `oil_drum` | 2 | (44.2, 2.7) 0°; (43.7, 3.4) 0° |
|  | `floodlight_stand` | 1 | (44.2, 7.9) 90° |
| **Sidewalk shed: on the deck (y 2.95) and under it** (8) `street.js:532-541` | `sandbags` | 2 | (5.4, 7.9, y 2.95) 0°; (12.8, 7.9, y 2.95) 0° |
|  | `crate_wood` | 1 | (17.2, 10.2, y 2.95) 11.5° |
|  | `cardboard_boxes` | 2 | (2.2, 8.4, y 2.95) 22.9°; (8.5, 10.45) 5.7° |
|  | `pallet` | 1 | (8.6, 10.2, y 2.95) 0° |
|  | `milk_crates` | 1 | (14.4, 10.5) 0° |
|  | `trash_can` | 1 | (3.3, 10.45) 0° |
| **South sidewalk blockers and the walkway round the hoist tower** (6) `street.js:351-352, 383-386` | `porta_potty` | 2 | (-6.8, 7.66) 90°; (-6.8, 8.86) 90° |
|  | `jersey_barrier` | 2 | (18.4, 5.02) 0°; (21.5, 5.02) 0° |
|  | `traffic_barrel` | 2 | (23.6, 5.1) 0°; (16.4, 5.1) 0° |
| **Parked at the kerbs (north lane noses west, south lane noses east)** (15) `street.js:38-53` | `van` | 6 | (-38.2, -5.98) -180° [#1b2a4a]; (-20.2, -5.98) -180° [#d9d7d0]; (19.4, -5.98) -180° [#8f959c]; (-18.9, 5.98) 0° [#8f959c]; (-3, 5.98) 0° [#14161a]; (13.4, 5.98) 0° [#6e1a1c] |
|  | `sedan` | 5 | (-27.4, -5.98) -180° [#6e1a1c, seed 1]; (13.6, -5.98) -180° [#2a2d33, seed 4]; (31.4, -5.98) -180° [#14161a, seed 3]; (4.6, 5.98) 0° [#1b2a4a, seed 6]; (39.6, 5.98) 0° [#d9d7d0, seed 0] |
|  | `motorbike` | 1 | (-5.7, -6.35) 4.6° |
|  | `taxi` | 2 | (4, -5.98) -180°; (-24.6, 5.98) 0° |
|  | `suv` | 1 | (-40.5, 5.98) 0° [#14161a] |
| **In the travel lanes, west to east** (31) `street.js:61-102` | `sedan` | 2 | (-35.2, -2.3) 24.1° [#2a2d33, seed 4]; (33.8, 2.3) 17.2° [#6e1a1c, seed 1] |
|  | `box_truck` | 2 | (-19.2, -2.4) -16° [#c9a23a]; (5.85, 2.35) 16° [#b9b4a6] |
|  | `traffic_barrel` | 7 | (-13.6, -2.9) 0°; (-12.9, -2.1) 0°; (9.9, -0.5) 0°; (12.6, -0.3) 0°; (30.2, 0.4) 0°; (31, -0.3) 0°; (30.4, -1.2) 0° |
|  | `motorbike` | 1 | (-14.6, 3.6) 28.6° |
|  | `trash_bags` | 3 | (-25.4, 1.6) 40.1°; (-6.2, 4.3) 28.6°; (6.2, -3.3) 63° |
|  | `barricade` | 2 | (-11.9, -3.6) 14.3°; (2.9, -3.8) -11.5° |
|  | `van` | 3 | (-9.4, 1.8) -148.5° [variant vulture, doors open, #14161a]; (16.3, -2.6) 31.5° [#2a2d33]; (36.9, -2.5) -174.2° [#2a2d33] |
|  | `jersey_barrier` | 5 | (-1.1, 3.1) 4.6°; (1, -1.9) 95.7°; (10.6, -2.3) 2.9°; (27.6, 2.6) 90°; (28.4, -2.9) 101.5° |
|  | `sandbags` | 2 | (-4.3, -2.9) 5.7°; (20.4, 2) 90° |
|  | `milk_crates` | 1 | (0.1, 1.2) 0° |
|  | `tire_stack` | 2 | (-7.6, -2.5) 0°; (15.2, 2.6) 0° |
|  | `crate_wood` | 1 | (-2.4, 4.25) 17.2° |
| **North sidewalk furniture** (25) `street.js:108-129` | `phone_booth` | 1 | (-44.5, -10.25) 0° |
|  | `trash_can` | 1 | (-42.2, -10.4) 0° |
|  | `mailbox` | 2 | (-32, -7.7) 0°; (9.6, -7.7) 0° |
|  | `newspaper_box` | 3 | (-31.2, -7.62) 0°; (1.7, -7.62) 0°; (26.2, -7.62) 0° |
|  | `street_lamp` | 4 | (-22.4, -7.62) -180°; (2.6, -7.62) -180°; (23.9, -7.62) -180°; (41.6, -7.62) -180° |
|  | `tire_stack` | 1 | (-17.3, -10.4) 0° |
|  | `oil_drum` | 1 | (-16.8, -9.6) 0° |
|  | `food_cart` | 1 | (-5.7, -8.3) 0° |
|  | `vending_machine` | 1 | (3.5, -10.55) 0° |
|  | `bus_shelter` | 1 | (29.2, -8.05) 0° |
|  | `bench` | 1 | (30.4, -11.55) 0° |
|  | `planter` | 2 | (32.1, -11.4) 0°; (36.9, -11.4) 0° |
|  | `hydrant` | 1 | (37.4, -7.5) 0° |
|  | `tree` | 1 | (39.8, -8.3) 0° |
|  | `parking_meter` | 4 | (-34.2, -7.42) 0°; (-24.6, -7.42) 0°; (9.2, -7.42) 0°; (33.6, -7.42) 0° |
| **South sidewalk furniture** (27) `street.js:135-157` | `trash_bags` | 2 | (-41.2, 10.3) 11.5°; (-13.6, 10.3) 51.6° |
|  | `newspaper_box` | 4 | (-40.1, 10.5) -180°; (-21.7, 7.62) -180°; (-21.1, 7.62) -180°; (26.9, 7.62) -180° |
|  | `trash_can` | 3 | (-36.4, 7.68) 0°; (-22.7, 7.68) 0°; (41.4, 7.68) 0° |
|  | `bench` | 2 | (-33.6, 10.5) -180°; (-27.1, 10.5) -180° |
|  | `street_lamp` | 3 | (-31.4, 7.62) 0°; (22.9, 7.62) 0°; (36.4, 7.62) 0° |
|  | `phone_booth` | 2 | (-29.2, 10.25) -180°; (27.3, 10.25) -180° |
|  | `milk_crates` | 2 | (-19.7, 10.5) 0°; (-18.9, 10.45) 0° |
|  | `hydrant_open` | 1 | (-12.25, 7.34) -180° |
|  | `tree` | 2 | (25.4, 8.3) 0°; (43.2, 8.3) 0° |
|  | `hydrant` | 1 | (38.2, 7.5) 0° |
|  | `planter` | 1 | (39.6, 10.25) 0° |
|  | `parking_meter` | 4 | (-26.6, 7.42) 0°; (1.6, 7.42) 0°; (7.6, 7.42) 0°; (39.9, 7.42) 0° |
| **Scattered cones** (10) `street.js:160-162` | `traffic_cone` | 10 | (-42.1, -3.9) -172.6°; (-42.4, 0.4) -18.4°; (-41.9, 4.3) 20.7°; (-13.9, -0.6) 180°; (-24.2, 0.9) 175.2°; (11.9, -0.9) 117.3°; (13.4, 1) 25.8°; (29.4, 1.6) 46.4°; (39.2, 4.2) -158.3°; (38.6, -6.2) 97.4° |
| **Master reel cases** (3) `level.js:98-102, data.js:10-14` | `master_case` | 3 | (-4, 1) 20.1°; (-9.5, -21.5) -28.6°; (35.25, -22.5) 63° |

### 2.16 Signs, graffiti and posters

Every sign is a flat panel whose text and colours are given here; the shop signs are in 2.5.3. Styles
(`docs/CONTRACT.md` 6.1): `box` a lit box sign, `neon` tube lettering, `painted` sign-writer's paint on a wall or
board, `stencil` sprayed letters with no background, `plate` a black enamel transit plate with white type, `awning`
vinyl banner lettering. Positions are the panel centre in web coordinates. How each style, poster and tag is painted
is in `06-look-fx.md` 2.8 to 2.11.

| Text (sub-line) | Size w × h | Style, colours | Where: centre (x, y, z), facing | Source |
|---|---|---|---|---|
| `188 ST` (`ELEVATED  ·  CLOSED 1 AM – 5 AM`) | 4.6 × 0.82 | plate | station mezzanine (-39.37, 4.47, 0), east | `el.js:179-180` |
| `188 ST` (`STATION CLOSED`) × 2 | 1.5 × 0.42 | plate | foot of each station stair (-38.46, 2.39, ±8.15), east | `el.js:238-239` |
| `V&R AUTO BODY` (`COLLISION  ·  FRAME  ·  PAINT`) | 12 × 3.2 | painted, #e9e2cf on #1d2f3f | tenement east wall (-23.97, 11.4, -24.5), east | `buildings.js:278-279` |
| `PARK` (`24 HR  ·  PAY AT BOOTH`) | 5 × 1.6 | painted, #f4f2ec on #1f4f9a | S3 east wall (22.03, 2.3, 18.5), east | `buildings.js:393-394` |
| `41` … `48` | 0.7 × 0.42 | stencil #e6e4dc | over each garage door (door x, 3.3, 30.98), north | `buildings.js:414-415` |
| `V&R AUTO BODY` | 8 × 1.05 | box, #f6c21a on #101113 | shop fascia (-12, 5.4, -10.87), south | `shop.js:304-305` |
| `TIRES  ·  BRAKES  ·  EXHAUST` | 5.4 × 0.6 | painted, #e9e2cf on #1a2b3a | shop fascia (-1.3, 5.4, -10.87), south | `shop.js:307-308` |
| `INSPECTIONS  ·  24 HR TOWING` | 5.6 × 0.6 | painted, #e9e2cf on #1a2b3a | shop fascia (-19.6, 5.4, -10.87), south | `shop.js:309-310` |
| `FLAT FIX` (`NO APPOINTMENT`) | 2.6 × 1.1 | stencil #e6e4dc | shop front wall (-6.1, 2.6, -10.98), south | `shop.js:311-312` |
| `EXIT` | 0.7 × 0.3 | box, #fff1d0 on #7a1410, glow #ff3030 | inside the shop over the side door (5.57, 2.85, -22.1), west | `shop.js:114-115` |
| `POST NO BILLS` × 3 | 1.5 × 0.24 | stencil #e6e4dc | vacant-lot hoarding (-13.95, 2.3, 11.09) and (-6.35, 2.3, 11.09), north; shanty (-16, 2.55, 8.59), north | `yards.js:289-290`, `street.js:342` |
| `NO PARKING` (`LOADING ZONE`) | 1.6 × 0.6 | stencil #e6e4dc | S3 back wall (16, 2.6, 26.02), south | `yards.js:367` |
| `PARK` (`24 HR`) × 2 | 1.7 × 1.5 | neon #35e0ff | both faces of the lot pylon (35.35 ± 0.11, 4.7, 11.65), west and east | `yards.js:414-416` |
| `VIOLATORS TOWED` (`AT OWNER'S EXPENSE`) | 3.4 × 0.9 | stencil #e6e4dc | lot east wall (45.98, 2.4, 19.5), west | `yards.js:473` |
| `ROAD CLOSED` (`EL STRUCTURE REPAIRS  ·  NO THRU TRAFFIC`) × 2 | 3.4 × 1.05 | box, unlit, #101113 on #e8641b | west hoarding (-45.25, 1.75, -2.6) and (-45.25, 1.75, 3.4), east | `street.js:402-404` |
| `CANDY  ·  SODA` | 1.35 × 0.26 | painted, #f4f2ec on #24463a | candy kiosk (-42.49, 2.42, 10.08), east | `street.js:245, 421` |
| `NEWS  ·  MAGAZINES  ·  LOTTO` | 2.4 × 0.26 | painted, #f4f2ec on #24463a | newsstand (-28.7, 2.42, -9.51), north | `street.js:245, 253` |
| `GOLDEN BIRD CHICKEN`, `WINES & LIQUORS`, `LUCKY NAILS` | 4.9 × 0.78 each | awning banners, unlit (colours in 2.9.3) | shed parapet (4.1 / 10 / 15.9, 3.5, 7.44), north | `street.js:498-506` |
| `SIDEWALK SHED  ·  PERMIT 0214  ·  STORES OPEN DURING WORK` | 5.6 × 0.24 | stencil #e6e4dc | shed skirt (10, 2.7, 7.41), north | `street.js:507` |
| `USED TIRES` (`ALL SIZES  ·  MOUNTED FREE`) | 2 × 0.5 | stencil #f2c21a on a dark board | over the tyre cage (-19.2, 2.76, -8.5), south | `street.js:274-276` |
| `DANGER` (`STEAM  ·  KEEP OUT`) × 2 | 1.5 × 0.6 | box, unlit, #b3261e on #f4f2ec | dig pen: south face (18.9, 1.65, -6.99), north face (20.1, 1.65, -9.25) | `street.js:320-322` |
| `SIDEWALK CLOSED` (`USE WALKWAY`) × 2 | 2.2 × 0.7 | box, unlit, #101113 on #e8641b | hoist tower: east face (22.01, 1.75, 9), north face (20.53, 1.75, 7.03) | `street.js:377-379` |
| `EL REPAIRS` (`KEEP CLEAR`) × 4 | 1.3 × 0.5 | box, unlit, #101113 on #e8641b | both long faces of each rolling scaffold at y 1.5: (-30.22 and -28.58, 1.5, 2.2), (-1.92 and -0.28, 1.5, -2.15) | `street.js:222-224` |

**Graffiti** (`mats.graffiti(text, seed, colour)`; crew tags are oxblood #8a1a22; default size is the painter's own):

| Tag | Colour | Size | Where | Source |
|---|---|---|---|---|
| `VULTURES` | #8a1a22 | 3.6 × 1.1 | inside the shop, south wall, x -6.1, y 2.5 | `shop.js:113` |
| `VLTR` | #8a1a22 | default | shop front, x 3.6, y 1.5 | `shop.js:313` |
| `VULTURES` | #8a1a22 | 3.2 × 1.0 | alley, shop wall, z -15.2, y 1.7 | `yards.js:53` |
| `188` | default | default | alley, shop wall, z -26.2, y 1.5 | `yards.js:54` |
| `HOLLIS` | default | 2.8 × 1.0 | alley, deli wall, z -24.5, y 1.6 | `yards.js:55` |
| `QNS` | #35e0ff | default | the cut, deli wall, z -22.5, y 1.5 | `yards.js:82` |
| `VULTURES` | #8a1a22 | 4.2 × 1.2 | on the court, centre (38.65, -18.2), turned 14° | `yards.js:182` |
| `RULE` | #f6c21a | 6.4 × 2.3 | over the mural, z 15.6, y 6.55 | `yards.js:265` |
| `HOLLIS` | #f4f2ec | 2.6 × 0.8 | mural wall, z 22.9, y 1.25 | `yards.js:266` |
| `QUEENS` | #35e0ff | 2.2 × 0.75 | mural wall, z 12.6, y 1.05 | `yards.js:267` |
| `NO SLEEP` | default | default | mural wall, z 26.6, y 1.4 (rear lane end) | `yards.js:268` |
| `VLTR` | #8a1a22 | 2.4 × 0.9 | vacant lot, S3 wall, z 15.2, y 1.5 | `yards.js:317` |
| `JAMAICA AVE` | default | default | vacant lot, S3 wall, z 19, y 1.2 | `yards.js:318` |
| `INC` | #f6c21a | default | rear lane, S3 back wall, x 2.4, y 1.5 | `yards.js:365` |
| `188` | #ff3d9a | default | parking lot east wall, z 26.4, y 1.4 | `yards.js:474` |
| `QUEENS` | default | 2.8 × 0.95 | parking lot south wall, x 27.2, y 1.5 | `yards.js:476` |
| `HOLLIS` | #f4f2ec | default | west hoarding, z 0.4, y 0.9 | `street.js:405` |
| `VULTURES` | #8a1a22 | 3.6 × 1.1 | roadblock scrim, z -4.6, y 1.4 | `street.js:450` |
| `VLTR` | #8a1a22 | default | roadblock scrim, z 5.4, y 1.2 | `street.js:451` |
| `188` | default | default | dig pen north face, x 18.9, y 1.05 | `street.js:323` |
| `QNS` | #35e0ff | default | shanty west face, z 9.8, y 0.85 | `street.js:346` |
| `VLTR` | #8a1a22 | default | hoist tower north face, x 19.96, y 0.95 | `street.js:381` |
| `VULTURES` | #8a1a22 | 3.4 × 1.0 | on the road at reel 1, centre (-3.4, -0.7), turned -17° | `street.js:82` |

**Posters** (`mats.poster(kind, seed)`, kinds `ad`, `show`, `wanted`, `torn`, `ipx`; about 0.6 × 0.9 m): three on
the shop's north wall, two on its east wall, one on its west wall, two in the office (one `ipx`), two on the shop
front (`shop.js:107-112, 205-206, 314-315`); three on the alley's deli wall (`yards.js:56-58`); an `ipx` and a `show`
in the cut (`yards.js:83-84`); a row along both runs of the vacant-lot hoarding cycling show, ad, torn, wanted, show,
ipx (`yards.js:282-288`); one on S3's wall in the vacant lot, one on its back wall, an `ipx` on the lot's south wall
(`yards.js:319, 366, 477`); three on the west hoarding (one `ipx`), two on each kiosk, two on the shanty, an `ipx` on
the hoist tower (`street.js:246-247, 344-345, 380, 406-408`). The IPX marks in the level are the mural, these `ipx`
posters, and what the props carry (truck livery, billboard, bus-shelter advert, reel cases).

### 2.17 Collision inventory

The level registers 756 axis-aligned boxes: 440 from the colliders of the props it places and 316 of its
own. The explosives module adds one per explosive later. By tag (`box.tag`), with the kind of each (3.2):

| Tag | n | Kind | What |
|---|---|---|---|
| `sidewalk` | 9 | solid | the eight slabs and the vestibule pad, y 0 … 0.15 |
| `tenement`, `deli`, `station house`, `pawn`, `S3`, `garages` | 10, 5, 9, 12, 9, 1 | solid, brick | the buildings, split where shop doors are carved in; `pawn` includes the vestibule soffit |
| `backs` | 7 | solid, brick | the neighbours' backs |
| `bulkhead` | 3 | solid, off the nav grid | roof stair heads |
| `facade` | 44 | bullet-only | skins over sign bands, shop windows, gates, service doors, garage doors, the PARK wall sign |
| `el-column` | 36 | solid, metal | 20 in the block, 16 beyond the closures |
| `el-girder` | 20 | solid, off the nav grid | 18 cross girders, 2 longitudinal girders |
| `el-deck` | 1 | solid, off the nav grid | the track deck |
| `station` | 23 | solid, metal / concrete | mezzanine, 2 bridges, 4 posts, 2 gates, 10 flight blocks, 2 platforms, 2 windscreens |
| `shop-wall` | 12 | solid | eleven wall pieces and the fan opening |
| `shop-roof`, `shop-column` | 1, 2 | solid | |
| `mezzanine` | 5 | solid, metal | deck and four posts |
| `office`, `office-glass`, `safe` | 4, 2, 1 | solid; glass is player-only | panels, door header, roof; the two glazed walls; the safe |
| `railing` | 5 | player-only | two on the mezzanine, two beside its stair, one beside the shed stair |
| `shop-stair`, `shed-stair` | 12, 12 | solid | one per tread, each from the floor to the tread top |
| `dock` | 5 | solid, concrete | platform and four steps |
| `alley-gate` | 1 | solid, metal | |
| `cage-plinth`, `cage-fence` | 6, 6 | solid; fence is player-only | knee wall; mesh from the plinth to y 8 |
| `hoarding` | 12 | solid, wood | west closure 3, vacant lot 2, shed parapet 3, dig 4 |
| `roadblock` | 3 | solid, metal | the east fence |
| `lot-wall`, `lot-gate`, `lot-sign` | 2, 1, 2 | solid; the sign box is bullet-only | low wall, barrier post, pylon pole and box |
| `kiosk`, `tyre-cage`, `produce-stand`, `dig`, `shanty`, `scaffold` | 2, 1, 1, 2, 1, 2 | solid | one box each (the dig also has its stack) |
| `hoist` | 2 | solid base; netting is player-only | |
| `shed-post`, `shed-deck` | 14, 1 | solid | |
| `seal` | 7 | player-only | four edges, alley end, west closure, roadblock |
| prop names (`sedan`, `jersey_barrier` …) | 440 | per prop | tagged with the catalogue name, `owner` = the prop |

---------------------------------------------------------------------------------------------------

## 3 Behaviour

The level is almost entirely static: it is built once at boot and then only answers queries. The state it owns at
run time is the handful of animated things in 3.5.

### 3.1 Build order (`level.js:59-214`)

`createLevel` is asynchronous and yields one browser frame between phases so the boot screen keeps painting; the
boot bar moves from 0.36 to 0.52 (`level.js:37-57`, shares 0.1, 0.2, 0.4, 0.55, 0.7, 0.85).

1. **Ground**: asphalt sheet, sidewalk slabs and kerbs, dropped kerbs, road paint, repairs, water, wear, manholes
   (`ground.js:44-195`).
2. **El**: bents, longitudinal steel, deck, lamps, then the station (`el.js:17-154`).
3. **Buildings**: N1, N2, S1, S2, S3, the garages, the neighbours' backs, then the building colliders with the door
   recesses carved out (`buildings.js:236-443`).
4. **Shop**: shell, doors, mezzanine, floor props, work lights, outside (`shop.js:15-335`).
5. **Yards**: alley, cut, cage, vacant lot, rear lane, parking lot (`yards.js:10-22`).
6. **Street**: west closure, roadblock, shed, sidewalk blockers, parked vehicles, lane vehicles and cover, sidewalk
   furniture, cones (`street.js:24-164`).
7. Player-only seal walls on the four edges (`level.js:83-92`).
8. Objectives: one `master_case` per reel; the extraction record round the truck (`level.js:98-110`).
9. Data: zones with display names, spawn points, cover points, title path, explosives, interior box
   (`level.js:116-159`).
10. Finish: everything static is merged into one mesh per material (108 meshes, 157 832 triangles in the real build);
    stateful props stay separate; `physics.setBounds(BOUNDS)`; the walkability nudge of 3.4 (`level.js:165-181`).

What stays dynamic (not merged, may change at run time): the three reel cases, the IPX truck, the open hydrant, the
extractor fan's blades. Explosives are not level objects: the explosives module stands its own actor at every entry
of `level.explosives`.

### 3.2 How collision is authored

World collision is a flat list of axis-aligned boxes over an implicit ground plane at y = 0
(`docs/CONTRACT.md` 5.1). The level never uses triangle meshes for collision. A box is given by its extents
(x0, x1, y0, y1, z0, z1) and carries a surface name, a tag and up to three flags:

| Kind | Flags | Stops walkers | Stops rounds and sight | In the nav grid | Used for |
|---|---|---|---|---|---|
| solid | none | yes | yes | yes | walls, buildings, cover, columns, hoardings |
| solid, off the grid | `noNav` | yes | yes | no | things overhead or above walking height: girders, the El deck, roofs, decks, bulkheads, the upper station |
| bullet-only | `bulletOnly` (+ `noNav`) | no | yes | no | facade skins so that bullet marks land on the drawn surface; the PARK sign box |
| player-only | `playerOnly` | yes | no | no | the seals, the cage mesh above its knee wall, the office glass, railings, the hoist tower's netting |

Rules the level follows:

- **Three builders** (`kit.js:283-307`): `box` draws without colliding, `solid` collides without drawing, `block`
  does both with the same extents. Most architecture is `block` or a `box` dressing over one coarse `solid`.
- **Surface** defaults to the material's (`kit.js:16-51`: asphalt reports `asphalt` and dirt `dirt`; sidewalk, kerb,
  court, concrete, cinder block, stucco and tile report `concrete`; every brick reports `brick`; steel, galvanised
  metal, roll gates, corrugated sheet, chain-link and chrome report `metal`; timber, plywood and cardboard report
  `wood`; fabric reports `cloth`; rubber and tyres `rubber`; every glass `glass`). A collider given no material and
  no surface reports `concrete` (`kit.js:295`).
- **Props** bring their own boxes in local space; the level turns them with the prop (`kit.js:612-634`). A prop box
  flatter than 0.2 m whose top is under 0.3 m is skipped, so pallets, manholes and mattresses are walked over
  (`kit.js:617-618`). A box at an off-axis yaw is replaced by up to 10 axis-aligned slices along its long side, each
  shrunk to 86 %; a box within about 5.8° of a right angle (\|sin 2ψ\| ≤ 0.2) snaps to it
  (`src/physics.js:29-31, 118-154`).
- **Stairs** (`kit.js:543-564`): each tread is a solid box from the flight's base up to that tread's top, so a flight
  is a wall from the sides and a staircase of ledges from the front. The player climbs because every rise (0.19 to
  0.25 m) is under the 0.42 m step-up height (`src/physics.js:21`); kerbs (0.15) work the same way.
- **Walk-under and step-over** for the AI's nav grid: a box blocks a 0.5 m nav cell only if it reaches above 0.47 m
  and starts below 1.5 m, and only if it is not `noNav`, bullet-only or player-only; obstacles are grown by 0.5 m
  (`src/physics.js:33-36, 92`). So kerbs do not block paths, and neither do the awnings, girders or decks overhead.
- **Storefront doors** are recesses carved out of the building boxes (2.5.1); every real opening (the chop shop's
  three doors, the gates, the gateways) is simply a gap between boxes.
- **Fences**: chain-link by itself has no collider; the caller decides (`fences.js:9-12`). The cage's mesh is
  player-only (shoot through), the alley gate and the roadblock fence are solid (they have a tarp or scrim on them).
- **No collision at all**: awnings, cornices, fire escapes, water towers, roof plant, the tenement's stoop, wheel
  stops, weeds, cones, mattresses, the barrier arm, the dropped-kerb slopes, signs.

### 3.3 Queries

```
zoneAt(x, z):                                   # layout.js:169-182
    best = 'avenue'; bestD = infinity
    for zone in [west, shop, avenue, lot]:      # in this order; ties keep the earlier zone
        dx = max(zone.minX - x, 0, x - zone.maxX)
        dz = max(zone.minZ - z, 0, z - zone.maxZ)
        d  = dx*dx + dz*dz
        if d < bestD: bestD = d; best = zone.id
    return best                                 # a point outside every rectangle belongs to the nearest one

zoneName(x, z):                                 # level.js:127-132 (the HUD's place name)
    id = zoneAt(x, z)
    if id != 'lot': return name of id           # WEST END, CHOP SHOP, THE AVENUE
    if z < -7: return 'THE CAGE'
    if z >  7: return 'THE LOT'
    return 'THE AVENUE'

floorAt(x, z):                                  # layout.js:187-191
    return 0.15 if (x, z) is inside any sidewalk slab or the vestibule pad (edges included) else 0

groundSurfaceAt(x, z):                          # layout.js:196-203, strict inequalities
    if inside the shop rectangle   (-24 < x < 6,    -31 < z < -11):   return 'concrete'
    if inside the cage rectangle   (25 < x < 45.4,  -33 < z < -12.2): return 'concrete'
    if inside the vacant lot       (-16 < x < -4,    11 < z < 26):    return 'dirt'
    if 7 <= |z| <= 11:                                                return 'concrete'
    return 'asphalt'

interiorAt(pos):                                # level.js:148-159; 0 outdoors … 1 inside the shop
    box = (-24, 0, -31) … (6, 6.3, -11)
    d = distance from pos to the box (0 inside)
    return clamp(1 - d / 1.5, 0, 1)
```

- `zoneAt` on a shared edge returns the earlier zone of the order west, shop, avenue, lot (x = -30 is `west`,
  z = -11 between x -30 and 22 is `shop`).
- `groundSurfaceAt` only answers for the bare ground plane; a hit on a box reports the box's surface. The physics
  module asks it for rays and footsteps that reach y = 0 (`src/physics.js:192`).
- `interiorAt` drives the audio's indoor mix and the atmosphere's indoor exposure
  (`src/audio.js:559`, `src/atmos.js:371`). It is 1 everywhere inside the shop's outer walls up to the roof top and
  fades over 1.5 m outside them in every direction, so it is already about 0.6 on the doorstep of the roll door.
- Display names come from `src/config/text.js:36-42` when present, else from `layout.js:158-166`; they are the same.
- `floorAt`, `puddles` and `stats` are members the real level publishes beyond `docs/CONTRACT.md` 6.10
  (`level.js:203-208`); `stats` (mesh, triangle, prop, collider and lamp counts) is for the boot log and tests only.

### 3.4 Finishing spawn and cover points

```
for each point in coverPoints + enemySpawns:        # level.js:176-181, after physics.setBounds
    if point is an air spawn, or point.y > 0.5, or the nav cell under it is walkable: keep it
    else:
        near = nearest walkable nav cell within 2.5 m
        if near exists: point.pos = (near.x, floorAt(near.x, near.z), near.z)
```

- It runs once at boot, before the explosives stand (their module adds them later).
- Nav cells are 0.5 m and a cell is walkable when its centre is at least 0.5 m from every blocking box, so a moved
  point lands on a cell centre (a multiple of 0.25 m that is not a multiple of 0.5 m).
- The result depends on the props' real colliders: with the real prop factory 21 points move
  (2 ground spawns, 19 cover points); the tables in 2.13 show them. A point's zone tag is
  computed before the nudge and never changes.

### 3.5 What moves at run time

`level.update(dt)` runs every frame while the game is not paused (`docs/CONTRACT.md` 3, step 4) and does two things
(`level.js:209-212`):

1. calls `update(dt)` on every placed prop that has one (the three reel cases and the truck drive their own beacons,
   lids, hazard lights and doors; state changes come from the flow module through `prop.setState`) and on the
   extractor fan, which turns at a constant 1.7 rad/s (97.4°/s, about 16 rpm) (`shop.js:152-156`);
2. re-tints the vertex colours of the tinted asphalt patches when the material library changes the road's day or
   night albedo (a web rendering detail, `level.js:289-326`).

There are no doors that open, no destructible architecture, no moving platforms. The train, the steam, the hydrant's
jet, lamp flicker and the day / night switch are in `06-look-fx.md`; they read the level's data
(`level.el`, `level.steam`, `level.lamps`). Who reads what: the flow reads `playerStart`, `objectives`, `extraction`,
`enemySpawns`, `bounds` and `cinematicPath` (`src/game.js:98, 225-233, 414-422`); Goons read `coverPoints`
(`src/enemies/goon.js:458, 520`); Buzzards read `el` and `interiorBoxes` (`src/enemies/buzzard.js:184-205`); the
explosives module reads `explosives` (`src/explosives.js:292`); the atmosphere reads `lamps`, `steam`, `el`, `bounds`
and `interiorAt` (`src/atmos/lights.js:25`, `src/atmos/life.js:521`, `src/atmos.js:69-70, 371`); the audio reads
`interiorAt`, `el`, `steam` and `objectives` (`src/audio.js:559`, `src/audio/ambience.js:58, 131, 214`); the HUD and
minimap read `zoneName`, `zoneAt`, `bounds`, `groundSurfaceAt` and `el` (`src/hud.js:637-648`,
`src/ui/minimap.js:57-108`); the physics reads `groundSurfaceAt` (`src/physics.js:192`). `vantage` and `puddles` are
published but read by nothing yet.

### 3.6 Determinism

The layout is hand-authored numbers. A seeded stream forked from the world seed (`G.rng.fork('level')`, default seed
1994, `kit.js:197`) decides only cosmetic variation: the yaw of manholes and cones, the positions of the road's
crack, oil and grime decals, the outline of every wet patch, poster spacing on the hoardings, the weeds, which oil or
grime decal lands on the shop floor. The same seed builds the same block, collider for collider
(`test/level-layout.test.js:644-652`). Vehicle paint for unpainted cars is a pure function of the prop's seed and
name (`kit.js:163-167`).

### 3.7 Layout rules the block is tested against

A rebuild that keeps these keeps the encounter design (`test/level-layout.test.js`):

| Rule | Value | Lines |
|---|---|---|
| Start | in `west`, on the south sidewalk, room for a capsule r 0.32, nothing above 1.2 m within 2 m ahead over ±34° | 88-104 |
| Spawns | 26 to 32 ground and 14 to 18 air; at least 6 ground and 4 air in each of `shop`, `avenue`, `lot`; none in `west`; every one more than 14 m from the start | 152-165 |
| Ground spawns | on walkable ground with room for a body (r 0.3, 0.45 to 1.8 m above the floor) | 166-170 |
| Air spawns | y 8 to 17, in open air (r 0.6), more than 1.5 m above the roof under them, more than 1.5 m outside the El deck's edge | 171-177 |
| Hidden spawns | from the start and from five eye points along the travel lanes, a ground spawn's chest (1.2 m) is visible from at most one, and at most 6 spawn / eye pairs see each other in all | 180-191 |
| Cover points | 50 or more; at least 12 in each fighting zone; each beside an obstacle (within 1.5 m) | 193-213 |
| Reel arenas | at least 4 props 0.6 to 1.5 m high standing 1.5 to 5 m from each reel; 1.4 m clear all round the case | 215-235 |
| Explosives | see 2.13.6; each stands on a floor and overlaps nothing | 237-273 |
| Connectivity | paths exist from the start to every reel, the truck, every ground spawn and cover point; every doorway and gate is walkable; the loops exist (vacant lot → lane → lot under 56 m, shop floor → side door → alley under 27 m, both cage gates, the avenue end to end on the road and on both sidewalks) | 275-331 |
| Vantage | the shed stair is climbed by walking; standing on the deck gives a clear shot at reel 1, crouching hides behind the parapet | 333-353 |
| Mezzanine | reached by its stair, risers of 0.25 m or less; office glass stops the player, not a round; the timber panel stops both | 355-390 |
| The cage | visible and shootable from the sidewalk; the knee wall is solid; only the gates let a body through | 392-411 |
| The El | at least 20 slim columns the full height; first steel overhead at 5.2 m or more over the road; at least 9 lamps under the deck | 413-430 |
| Sightlines | at eye height (1.68 m) along the avenue within ±10° of its axis: no clear line longer than 58 m, and fewer than 0.06 % of sampled lines longer than 46 m | 501-527 |
| Perimeter | a round fired outward at chest height from anywhere stops on something solid no more than 3 m outside the bounds; seals 8 m high all round; a running jump at any closure stays inside | 529-567 |
| No pockets | every standable place at ground level connects to the start, except behind the alley gate and behind the cage's north and east fences | 581-642 |

### 3.8 Edge cases and quirks as built

Things a rebuild should either keep on purpose or fix on purpose:

1. **The station is scenery.** Its stairs are gated and filled with colliders; the mezzanine, bridges and platforms
   cannot be reached (2.7.2).
2. **Skylights are not openings.** The roof collider is continuous and the panes are a glowing "sky" material seen
   from below (2.6.2). Buzzards cannot enter the shop through the roof, only through its three doors.
3. **Rolling scaffolds are opaque boxes** to rounds and to the AI's sight although their netting is drawn
   see-through. They are two of the pieces that cut the long sightlines (3.7).
4. **Mesh that stops bullets and mesh that does not.** Cage mesh: shoot through. Hoist-tower netting above 2.75:
   shoot through. Alley gate (tarp) and roadblock fence (scrim): solid. Tyre cage: one solid rubber box.
5. **The tenement's stoop has no collider**: the player walks through two drawn steps that reach 0.75 m onto the
   sidewalk (2.5.4).
6. **Awnings, fire escapes and cornices** neither block movement nor rounds; a shot at an awning hits the wall behind.
7. **The cut is concrete to the eye and asphalt to the ear** (2.12): it lies outside all three surface rectangles
   and north of z -11.
8. **A mailbox and a parking meter stand in the alley's dropped kerb** at road level, (9.6, -7.7) and (9.2, -7.42),
   because the level stands every prop on the floor under its centre.
9. **Back-wall windows are cut by the roof line.** The window grid is 3.1 m high everywhere, counted from the ground
   on side and back walls, while roofs are at 3.8 + 3.1 n: the top of those walls shows 0.7 m of the next storey,
   including a 10 cm sliver of its windows. On S3's east wall a painted sign also covers part of the ground row.
10. **The billboard faces the parking lot**, not the avenue; from the street the player sees its back. The cage's
    two benches (front toward +Z) face the fence, not the court.
11. **Night-time dressing in a daytime game.** The default look is a 4:15 PM afternoon (`docs/DESIGN.md` 8), but the
    block was dressed for 2 AM: the station plate reads `CLOSED 1 AM – 5 AM`, its stairs are gated "for the night",
    the nail salon and every garage are shuttered, signs read `SLICES ALL NIGHT` and `OPEN 24 HRS`
    (`el.js:179, 235`, `buildings.js:150`).
12. **Nothing stands beyond the closures** but the avenue's own asphalt, sidewalks and El out to x ±96; the skyline
    behind them is the atmosphere module's far city (`06-look-fx.md` 2.18).
13. **Colliders exist outside the bounds** for the El's far bents (16 columns, 8 cross girders at x ±55 … ±85) and
    the neighbours' backs; only the backs can ever be hit.
14. **The extraction point is not at the truck**: it is 5.4 m west of the truck's origin, 2.0 m behind its rear doors
    (2.13.3).
15. **Design-document differences** (the code wins): the start is at (-37.4, 0.15, 8.15), not "near (-40, 0, 8)";
    El columns stand at z ±4.6, not ±5; reel 2 is at (-9.5, 0, -21.5) and reel 3 at (35.25, 0, -22.5), not
    (-9, 0, -21) and (33, 0, -22); the truck is at (41.3, 0, 29.7) with the zone centre at (35.9, 0, 29.7), not
    "near (40, 0, 27)"; the shop's front is on z -11, not -12; the vacant lot ends at z 26, not 30; there are 29 + 17
    spawn points, not "about 28 + 16", 100 cover points, not "50+", and 21 explosives; the shed deck is 2.8 m above
    the sidewalk, 2.95 above the road (`docs/DESIGN.md` 4).

Web-only machinery that must **not** be ported: merging per material (`src/core/geo.js:351-424`), shadow hulls for
vehicles and stacks (`kit.js:64-161`), switching off shadows of props the sun never reaches (`level.js:216-287`), the
atlas UV mapping of overlays (`kit.js:408-432`), the `LIFT` heights that keep flat layers from z-fighting
(`ground.js:11`), and the day re-tint of 3.5.

---------------------------------------------------------------------------------------------------

## 4 Unreal mapping

### 4.1 Conversions

| Quantity | Web | Unreal |
|---|---|---|
| Position | (x, y, z) m | (X, Y, Z) = (100 x, 100 z, 100 y) cm |
| Rectangle on the ground | x0 … x1, z0 … z1 | X 100 x0 … 100 x1, Y 100 z0 … 100 z1 |
| Height | y m | Z = 100 y cm |
| Object yaw (`rotation.y` = ψ rad) | local +X → (cos ψ, -sin ψ) in (x, z) | Yaw = -ψ · 180 / π degrees (mesh axes converted like positions) |
| Camera / player yaw ψ rad | forward (-sin ψ, -cos ψ) in (x, z) | Yaw = -90° - ψ · 180 / π |
| Direction vector (aim of a lamp) | (dx, dy, dz) | (dx, dz, dy) |
| Angular speed | rad/s | × 57.2958 = °/s |
| Wall that faces `+z` (south) | | wall module yaw 0°: runs along +X (west to east), pivot at its west end |
| Wall that faces `-z` (north) | | yaw 180°: runs east to west, pivot at its east end |
| Wall that faces `+x` (east) | | yaw -90°: runs south to north, pivot at its south end |
| Wall that faces `-x` (west) | | yaw +90°: runs north to south, pivot at its north end |

The wall rows follow from the shared module convention (pivot at the bottom-left corner of the outer face seen from
outside, running along +X, outer face toward -Y in Blender = +Y in Unreal); in Blender the same four cases are
Z rotations of 0°, 180°, +90° and -90°.

### 4.2 Key values in centimetres

| Value | Web | Unreal |
|---|---|---|
| Play bounds | x ±46, z ±34 | X ±4600, Y ±3400 |
| Kerb height | 0.15 | 15 |
| Kerb lines / building lines | \|z\| 7 / 11 | \|Y\| 700 / 1100 |
| Parking lane centre lines | z ∓5.98 | Y ∓598 |
| Ground storey / upper storey / parapet | 3.8 / 3.1 / 0.9 | 380 / 310 / 90 |
| Roof heights: tenement, pawn, deli and station house, S3, garages | 16.2, 13.1, 10.0, 6.9, 3.8 | 1620, 1310, 1000, 690, 380 |
| Window bay / window opening / sill above floor line | 3.1 / 1.24 × 1.736 / 0.60 | 310 / 124 × 173.6 / 60 |
| Shop door 1 / door 2 / side door (w × h) | 6.0 × 4.3 / 3.8 × 3.5 / 2.0 × 2.5 | 600 × 430 / 380 × 350 / 200 × 250 |
| Shop eave / roof top / parapet | 6.0 / 6.3 / 6.9 | 600 / 630 / 690 |
| Mezzanine deck / office top / railing top | 2.8 / 5.3 / 3.85 | 280 / 530 / 385 |
| Stair rise × going: mezzanine, shed, dock, station | 0.233 × 0.28, 0.233 × 0.30, 0.25 × 0.25, 0.1875 × 0.27 | 23.3 × 28, 23.3 × 30, 25 × 25, 18.75 × 27 |
| El column rows / bent spacing | z ±4.6 / 10 | Y ±460 / 1000 |
| El column top = cross girder underside | 5.3 | 530 |
| El longitudinal girder underside / deck underside / tie top / rail top | 5.5 / 6.5 / 6.68 / 6.83 | 550 / 650 / 668 / 683 |
| El deck half width / track centre lines / gauge / tie pitch | 5.4 / z ±2.1 / 1.435 / 0.56 | 540 / Y ±210 / 143.5 / 56 |
| El column collider | 0.64 × 0.64 × 5.3 | 64 × 64 × 530 |
| Station mezzanine underside / platform top / canopy top | 3.9 / 7.75 / 10.5 | 390 / 775 / 1050 |
| Shed deck top / parapet top / post rows | 2.95 / 4.05 / z 7.6 and 10.8 | 295 / 405 / Y 760 and 1080 |
| Cage fence top / knee wall / gate width | 4.0 / 0.5 (0.65 on the south side) / 3.0 | 400 / 50 (65) / 300 |
| Hoardings: west closure, vacant lot, dig pen, shed parapet | 2.7, 2.55, 2.2 (top 2.35), 1.1 | 270, 255, 220 (top 235), 110 |
| Chain-link: roadblock, alley gate | 2.5, 2.6 | 250, 260 |
| Seal walls | 0.6 thick, 8 high | 60 thick, 800 high |
| Interior fade distance | 1.5 | 150 |
| Extraction radius | 2.5 | 250 |
| Spawn / cover nudge radius, nav cell, nav obstacle growth | 2.5, 0.5, 0.5 | 250, 50, 50 |
| Step-up height (physics) | 0.42 | 42 |
| Extractor fan | 1.7 rad/s | 97.4°/s |
| Player start | (-37.4, 0.15, 8.15), yaw -1.4908 rad | (-3740, 815, 15), yaw -4.58° |
| Reels 1, 2, 3 | (-4, 0, 1), (-9.5, 0, -21.5), (35.25, 0, -22.5) | (-400, 100, 0), (-950, -2150, 0), (3525, -2250, 0) |
| Extraction centre / truck origin | (35.9, 0, 29.7) / (41.3, 0, 29.7) | (3590, 2970, 0) / (4130, 2970, 0) |
| Vantage: stair foot / deck | (-3.2, 0.15, 9.95) / (10, 2.95, 9.3) | (-320, 995, 15) / (1000, 930, 295) |

Footprints of every area in Unreal units (from 2.4):

| Area | Unreal X (cm) | Unreal Y (cm) | Unreal Z (cm) |
| --- | --- | --- | --- |
| Play bounds | -4600 … 4600 | -3400 … 3400 | 0 (ground plane) |
| N1 tenement | -4600 … -2400 | -3400 … -1100 | 0 … 1620 (parapet 1710) |
| V&R AUTO BODY (chop shop) outer walls | -2400 … 600 | -3100 … -1100 | eave 600, roof top 630, parapet 690 |
| Shop mezzanine deck | -2360 … -1540 | -3060 … -2500 | deck top 280 |
| Mezzanine office | -2360 … -1740 | -3060 … -2710 | 280 … 530 |
| Mezzanine stair | -1540 … -1204 | -2630 … -2500 | 0 … 280 |
| Alley | 600 … 1100 | -3400 … -1100 | 0 |
| N2 deli | 1100 … 2200 | -3400 … -1100 | 0 … 1000 (parapet 1090) |
| The cut | 2200 … 2500 | -3400 … -1100 | 0 |
| The Cage (fence line) | 2500 … 4540 | -3300 … -1220 | mesh to 400 |
| S1 station house | -4600 … -3000 | 1100 … 3400 | 0 … 1000 (parapet 1090) |
| S2 pawn + records | -3000 … -1600 | 1100 … 3400 | 0 … 1310 (parapet 1400) |
| Vacant lot | -1600 … -400 | 1100 … 2600 | 0 |
| S3 chicken / liquor / nails | -400 … 2200 | 1100 … 2600 | 0 … 690 (parapet 780) |
| Rear service lane | -1600 … 2200 | 2600 … 3100 | 0 |
| Garages | -1600 … 2200 | 3100 … 3400 | 0 … 380 (collider 470) |
| Parking lot | 2200 … 4600 | 1100 … 3400 | 0 |
| Sidewalk shed deck (the vantage) | 100 … 1900 | 745 … 1095 | deck top 295, parapet top 405 |
| Shed stair | -260 … 100 | 895 … 1095 | 15 … 295 |
| El deck | -4600 … 4600 | -540 … 540 | underside 650, rail top 683 |
| Station mezzanine (fare control) | -4600 … -3940 | -410 … 410 | 390 … 630 |
| Station stair, south | -4420 … -3880 | 725 … 905 | 15 … 390 |
| Station stair, north | -4420 … -3880 | -905 … -725 | 15 … 390 |
| Station platform, south | -4600 … -2950 | 375 … 705 | slab 755 … 775, canopy to 1050 |
| Station platform, north | -4600 … -2950 | -705 … -375 | slab 755 … 775, canopy to 1050 |
| Mid-block crossing | 2300 … 2660 | -680 … 680 | 0 |
| Loading dock | 640 … 1240 | 2600 … 2750 | 0 … 100 |
| Hoist tower | 1906 … 2200 | 704 … 1097 | 15 … 940 (standards to 990) |
| Rolling scaffold A | -3020 … -2860 | -30 … 470 | deck 370, rail 475 |
| Rolling scaffold B | -190 … -30 | -470 … 40 | deck 370, rail 475 |
| Newsstand kiosk | -3020 … -2720 | -950 … -704 | 15 … 265 |
| Candy kiosk | -4524 … -4250 | 925 … 1090 | 15 … 265 |
| Tyre cage | -2040 … -1800 | -1096 … -860 | 15 … 240 |
| Produce stand | 1140 … 1520 | -1098 … -860 | 15 … 250 |
| Utility dig pen | 1780 … 2120 | -920 … -704 | 15 … 235 (stack to 375) |
| Site shanty | -1740 … -1460 | 860 … 1098 | 15 … 285 |

Spawn points, explosives, steam points and the title path are already given in centimetres in 2.13. Cover points,
lamp hints and prop placements convert with the table in 4.1; the exporter's data files in
`unreal/MurderInc/Content/Data/` should carry them converted, and this document is the reference to check them
against.

### 4.3 The natural Unreal Engine 5 feature for each mechanism

| Web mechanism | Unreal Engine 5 |
|---|---|
| One block, built in code at boot | One persistent level, `/Game/Maps/L_Block` (`00-unreal-scout.md` 2), no streaming: the play space is 92 × 68 m plus set extension. Sub-levels or data layers per discipline (architecture, El, street dressing, gameplay, lighting) only for team workflow |
| Static geometry merged per material | Modular static meshes placed as instances (ISM / HISM or Packed Level Actors per building and per El span), Nanite on for the steel, masonry and props; no manual merging |
| Collider list of axis-aligned boxes | Simple collision on every mesh, authored as boxes that match the web extents for anything that is cover or a wall (UCX boxes from Blender or box primitives in the Static Mesh editor). Keep "Use Complex as Simple" off for gameplay geometry so cover edges stay where the tuning expects them |
| Solid / `noNav` / bullet-only / player-only | The channel scheme of `01-player.md` 4.4 on the two custom channels named in `00-unreal-scout.md` 4.5 (`Weapon`, a trace channel; `PlayerOnly`, an object channel). Solid = blocks pawns, weapon and sight traces and affects navigation; bullet-only = blocks weapon and sight traces only; player-only = blocks pawn movement only; `noNav` = "Can Ever Affect Navigation" off. What Goons and Buzzards do at player-only volumes is in `03-enemies.md` (its open questions 7 and 17) |
| Surface names | Physical Materials with a `SurfaceType` per name (asphalt, concrete, metal, wood, rubber, glass, dirt, brick, car, cloth), assigned on the render materials so line traces return them |
| `groundSurfaceAt` | Not needed as a function: the ground is real geometry (one mesh or landscape per area) carrying the right physical material. Decide the cut's surface on purpose (3.8 item 7) |
| `floorAt` | Not needed: spawn and prop heights come from the data or from a downward trace |
| Seal walls | Blocking Volumes with the player-only preset, 60 cm thick just outside each edge and 800 cm high, plus the three inner ones (alley end, west closure, roadblock) |
| Play bounds clamp | A world-bounds check in the character movement, or simply the seals; a Kill-Z far below as a safety net |
| Nav grid (0.5 m cells, obstacles grown 0.5 m) | Recast NavMesh inside a NavMeshBoundsVolume equal to the bounds, agent radius about 50 cm (`01-player.md` 4.4). The web grid is one ground-level layer: to match it, keep the shed stair and deck, the mezzanine and its stair, the loading dock and the bleachers out of the Goon's nav data with nav modifiers (`03-enemies.md` 6, question 1) |
| `zoneAt` | A data asset holding the four rectangles and one function with the nearest-rectangle rule (3.3), used by spawning, AI and HUD alike. Trigger volumes alone cannot answer for points outside every rectangle |
| `zoneName` | The same function plus the split of `lot` at Y -700 and +700 |
| `interiorAt` | One box (the shop's outer shell to the roof top) with a 150 cm falloff: an Audio Volume / reverb send and a post-process or exposure blend with Blend Radius 150, or the same closed-form distance in code where a 0 … 1 number is needed |
| `level.interiorBoxes` for Buzzards | The same box as data; the shop's three doors are the only ways in |
| Player start | A PlayerStart at (-3740, 815, 15 + capsule half height), yaw -4.58° |
| Objectives | Three `BP_MasterCase` actors at the reel transforms; markers and interaction per `04-flow.md` |
| Extraction | A cylinder trigger of radius 250 at (3590, 2970, 0) owned by the truck actor |
| Spawn points | Lightweight actors (or rows of a DataTable imported from the exported JSON) with `Type` (ground / air) and `Zone`; ground ones snapped once to the navmesh within 250 cm, as the web game does |
| Cover points | The same, consumed by the Goon's fire-position query (`03-enemies.md`); the three raised points stay unreachable unless Goons are allowed to climb |
| Explosives | Spawned by the explosives system at the 21 transforms; they are part of the cover, so their collision must exist from the first frame |
| Lamp hints | Real lights in UE5: Point / Spot / Rect lights at the hint positions with the hint colour, plus emissive fixture meshes. The web game's small budget of real lights (`quality.lights`, `docs/CONTRACT.md` 5.3) does not apply with Lumen; `priority` can still order who gets shadow casting when lights are budgeted |
| Sun stripes through the El | Real tie geometry (22 cm ties, 34 cm gaps) lit by the directional light with Virtual Shadow Maps: the stripes on the avenue are the block's signature and must come from the actual ties, not a masked plane |
| Skylights | Real glazed openings so daylight reaches the shop floor (Lumen), with glass that blocks pawns and weapon traces to keep the web behaviour |
| Road paint, patches, stains, wet patches | DBuffer decals or mesh decals on the ground; wetness as a material layer masked round the hydrant; `level.puddles` kept as data for splash effects |
| Signs, posters, graffiti | Sign meshes with baked text textures (one unique set per sign, `M_<Asset>`); posters and graffiti as decals (`06-look-fx.md` 4.4) |
| Steam points | Niagara emitters at the six positions |
| `level.el` | Data for the Buzzard's flight planner (a box X ±4600, Y ±540, Z 650 … 690) and for the train: two splines along Y -210 and +210 with the rail top at Z 683 |
| `level.vantage` | Two named points (stair foot, deck centre). Nothing reads them in the web game; keep them as data for a later "climb to the vantage" behaviour |
| `level.cinematicPath` | A Level Sequence or a spline-driven camera through the 14 keys (centripetal Catmull-Rom, constant pace) |
| Extractor fan | Rotating Movement Component, 97.4°/s about the wall normal |
| Vehicle paint chart | A nine-entry colour table driving a paint parameter on the vehicle material instances |
| Seeded cosmetic variation | Bake it: use the positions of the default seed (2.15) and scatter decals by hand |
| Day / night | One level, two lighting scenarios (targets in `docs/unreal/ART_BIBLE.md` 2); the level's lit glass, neon and lens materials need an emissive scalar the scenario can drive |

### 4.4 Assembly order for the level builder

1. Ground: roadway, sidewalk slabs and dropped kerbs, then the yard surfaces (shop floor, alley, cut, court, dirt,
   lane, lot) from 2.4 and 2.12.
2. Building masses from 2.5.1 and 2.5.5 as blockout boxes with their final collision extents; the shop shell with its
   three doors, mezzanine and stair (2.6).
3. The El: ten bents at X -4500 … 4500 step 1000, columns at Y ±460; spans, deck and lamps; the station (2.7).
4. Closures and sidewalk structures (2.9), yard fences and gates (2.10), the seals (2.11). Walk the perimeter test of
   3.7.
5. Catalogue props from 2.15, area by area. Place the two curtains first, then check the sightline rule: near x -18
   the newsstand, the tyre cage, the box truck at (-19.2, -2.4), the vans parked at the kerbs, the shanty and the
   portable toilets; near x +14 the produce stand, the dig, the box truck at (5.85, 2.35), the van at (16.3, -2.6)
   and the hoist tower.
6. Gameplay data from 2.13; navmesh; check connectivity and the reel arenas.
7. Lights from 2.14, signs and paper from 2.16, decals.
8. Replace blockout with final modules (5.1) without moving any collision face.

---------------------------------------------------------------------------------------------------

## 5 Art and audio implications

The web block is low-poly boxes with painted textures; every piece stands for a real thing, and the rebuild models the
real thing at the same footprint, the same cover heights and the same openings. The art direction is the daylight
look of `docs/DESIGN.md` 8: a hot, clear afternoon about 4:15 PM, hard sun raking through the El, saturated brick,
awnings and signs, reflective glass.

### 5.1 Module list

Everything the level code builds itself, as modules to model in Blender. The full briefs (parts, proportions,
materials, colours, gameplay role, source) are in `docs/unreal/spec/assets/level.json`; ids match. Sizes are metres in
Blender axes (x along the module, y its depth, z its height). Priority 1 = seen up close or defines the block.

**Architecture** (35)

| Brief id | Mesh | Size x × y × z (m) | Count | Priority | Gameplay role |
| --- | --- | --- | --- | --- | --- |
| `storefront_laundromat` | `SM_Architecture_Storefront_Laundromat` | 8.8 × 0.54 × 3.69 | 1 | 1 | none: flush with the building line, no cover; door recess 0.36 m deep |
| `storefront_barber` | `SM_Architecture_Storefront_Barber` | 8.2 × 1.71 × 3.69 | 1 | 1 | none: flush with the building line, no cover; door recess 0.36 m deep; the awning has no collision |
| `storefront_deli` | `SM_Architecture_Storefront_Deli` | 11 × 1.71 × 3.69 | 1 | 1 | none: flush with the building line, no cover; door recess 0.36 m deep; the awning has no collision |
| `storefront_checks_cashed` | `SM_Architecture_Storefront_ChecksCashed` | 7.7 × 0.54 × 3.69 | 1 | 1 | none: flush with the building line, no cover; door recess 0.36 m deep |
| `storefront_pizza` | `SM_Architecture_Storefront_Pizza` | 8.3 × 1.71 × 3.69 | 1 | 1 | none: flush with the building line, no cover; door recess 0.36 m deep; the awning has no collision |
| `storefront_pawn` | `SM_Architecture_Storefront_Pawn` | 6 × 0.54 × 3.69 | 1 | 1 | none: flush with the building line, no cover; door recess 0.36 m deep |
| `storefront_records` | `SM_Architecture_Storefront_Records` | 5.8 × 0.54 × 3.69 | 1 | 1 | none: flush with the building line, no cover; door recess 0.36 m deep |
| `storefront_chicken` | `SM_Architecture_Storefront_Chicken` | 9 × 0.54 × 3.69 | 1 | 2 | none: flush with the building line, no cover; door recess 0.36 m deep |
| `storefront_liquor` | `SM_Architecture_Storefront_Liquor` | 8.5 × 0.54 × 3.69 | 1 | 2 | none: flush with the building line, no cover; door recess 0.36 m deep |
| `storefront_nails` | `SM_Architecture_Storefront_Nails` | 8.5 × 0.54 × 3.69 | 1 | 2 | none: flush with the building line, no cover; door recess 0.36 m deep |
| `residents_entrance` | `SM_Architecture_ResidentsEntrance` | 2.8 × 0.75 × 3.65 | 1 | 2 | none in the web game (the stoop has no collision); give the steps simple collision in the rebuild |
| `pawn_vestibule` | `SM_Architecture_PawnVestibule` | 2.2 × 2.4 × 3.65 | 1 | 2 | a walk-in pocket 2.2 x 2.4 m, 2.63 m headroom; walls solid; ground spawn G8 inside |
| `facade_bay_upper` | `SM_Architecture_FacadeBay_Upper` | 3.1 × 0.3 × 3.1 | 60 | 1 | none (solid wall above the shops, no collision detail) |
| `facade_bay_rear` | `SM_Architecture_FacadeBay_Rear` | 3.1 × 0.3 × 3.1 | 208 | 2 | none (solid wall) |
| `brick_wall_blind` | `SM_Architecture_BrickWall_Blind` | 3.1 × 0.3 × 3.1 | tiling | 2 | none (solid wall) |
| `cornice_dentil` | `SM_Architecture_Cornice` | 3.1 × 0.42 × 0.8 | 28 | 2 | none (no collision) |
| `parapet_coping` | `SM_Architecture_Parapet` | 3.1 × 0.38 × 0.97 | 125 | 3 | none (roofs are out of reach; the building collider ends at the parapet top) |
| `roof_bulkhead` | `SM_Architecture_RoofBulkhead` | 3 × 3.5 × 2.6 | 3 | 3 | solid, on roofs: only a flying Buzzard can meet it |
| `service_door` | `SM_Architecture_ServiceDoor` | 1.24 × 0.22 × 2.5 | 6 | 2 | none (flush; a bullet-only skin 0.07 m deep in the web game) |
| `wall_lamp_caged` | `SM_Architecture_WallLamp_Caged` | 0.3 × 0.3 × 0.22 | 11 | 3 | none |
| `delivery_shutter` | `SM_Architecture_DeliveryShutter` | 3.8 × 0.16 × 2.7 | 2 | 3 | none (flush) |
| `garage_bay` | `SM_Architecture_GarageBay` | 4.4 × 3 × 4.1 | 8 | 2 | solid wall 4.7 m high along the whole south side of the lane; a welding rack stands between doors 45 and 46 |
| `loading_dock` | `SM_Architecture_LoadingDock` | 7 × 1.5 × 1 | 1 | 2 | hard cover 1.0 m high; walkable top reached by its steps; ground spawn G17 at the steps, a pallet stack and boxes on top |
| `neighbour_back` | `SM_Architecture_NeighbourBack` | 38 × 3 × 14 | 7 | 2 | solid perimeter wall, full height; stops rounds |
| `chopshop_shell` | `SM_Architecture_ChopShop_Shell` | 30 × 20 × 6.98 | 1 | 1 | hard cover and the walls of the reel 2 arena; three ways in (two bays on the avenue, the side door to the alley); interior volume for audio and exposure |
| `chopshop_roof` | `SM_Architecture_ChopShop_Roof` | 30 × 20 × 1.05 | 1 | 1 | solid ceiling at 6.0 m (nothing passes a rooflight); the two columns are slim hard cover |
| `chopshop_rollup_door` | `SM_Architecture_ChopShop_RollUpDoor` | 6.2 × 0.58 × 4.72 | 2 | 1 | none: the doors never close; clear opening is the full 4.3 m / 3.5 m height minus the 0.62 m of hanging slats (no collision on the slats) |
| `chopshop_side_door` | `SM_Architecture_ChopShop_SideDoor` | 2 × 1.9 × 2.5 | 1 | 1 | open doorway 2.0 x 2.5 m linking the shop floor and the alley (the leaf has no collision) |
| `chopshop_extractor_fan` | `SM_Architecture_ChopShop_ExtractorFan` | 1.2 × 0.4 × 1.2 | 1 | 2 | none (the opening is solid to rounds and walkers); a looping sound source |
| `chopshop_mezzanine` | `SM_Architecture_ChopShop_Mezzanine` | 8.2 × 5.6 × 3.85 | 1 | 1 | second floor at 2.8 m reached only by its stair; the railing stops walkers but not rounds; one AI cover point on the deck; the space beneath is 2.68 m high (2.5 m under the edge beams) and holds a ground spawn |
| `chopshop_mezz_stair` | `SM_Architecture_ChopShop_MezzStair` | 3.36 × 1.3 × 3.85 | 1 | 1 | walkable flight (every rise under the 0.42 m step-up); solid from the sides; handrails stop walkers only; a welding rack stands at its foot |
| `chopshop_office` | `SM_Architecture_ChopShop_Office` | 6.25 × 3.55 × 2.6 | 1 | 1 | the timber panel is hard cover 0.95 m high on the deck; the glass above stops walkers but not rounds; the safe is solid |
| `gooseneck_lamp` | `SM_Architecture_GooseneckLamp` | 0.34 × 0.9 × 0.4 | 3 | 2 | none |
| `highbay_worklight` | `SM_Architecture_HighBayLight` | 0.72 × 0.72 × 0.78 | 4 | 2 | none (the shop interior is lit by these four) |
| `barber_pole` | `SM_Architecture_BarberPole` | 0.18 × 0.18 × 0.86 | 1 | 3 | none |

**Signs and painted walls** (9)

| Brief id | Mesh | Size x × y × z (m) | Count | Priority | Gameplay role |
| --- | --- | --- | --- | --- | --- |
| `chopshop_fascia` | `SM_Sign_ChopShop_Fascia` | 29.4 × 0.13 × 1.3 | 1 | 1 | none |
| `wall_ad_vr_auto_body` | `SM_Sign_WallAd_VRAutoBody` | 12 × 0.03 × 3.2 | 1 | 2 | none |
| `wall_sign_park` | `SM_Sign_WallSign_Park` | 5 × 0.03 × 1.6 | 1 | 3 | none |
| `mural_ipx_rule` | `SM_Sign_Mural_IPX` | 12 × 0.03 × 7.6 | 1 | 1 | none (landmark of the vacant lot) |
| `park_pylon_sign` | `SM_Sign_ParkPylon` | 1.8 × 0.24 × 5.6 | 1 | 2 | the pole is slim hard cover; the cabinet stops rounds only |
| `station_name_plates` | `SM_Sign_Station_188St` | 4.6 × 0.03 × 0.82 | 3 | 1 | none |
| `construction_signs` | `SM_Sign_Construction_Set` | 3.4 × 0.02 × 1.05 | 10 | 2 | none |
| `shed_banners` | `SM_Sign_ShedBanner` | 4.9 × 0.02 × 0.78 | 3 | 2 | none |
| `stencil_signs` | `SM_Sign_Stencil_Set` | decals | 16 | 3 | none |

**The El** (8)

| Brief id | Mesh | Size x × y × z (m) | Count | Priority | Gameplay role |
| --- | --- | --- | --- | --- | --- |
| `el_column` | `SM_El_Column` | 1.04 × 1.04 × 5.3 | 20 | 1 | hard cover, full height, 0.64 x 0.64 m collider: the most dependable cover on the avenue, between every travel lane and parking lane |
| `el_cross_girder` | `SM_El_CrossGirder` | 0.66 × 10.1 × 1.2 | 10 | 1 | overhead: lowest steel over the road at 5.3 m; stops rounds; blocks flight between 5.3 and 6.5 m |
| `el_span_structure` | `SM_El_Span_Structure` | 10 × 10.8 × 1.22 | 9 | 1 | overhead: girders stop rounds; the two longitudinal girders are 0.4 m wide colliders 5.5 to 6.5 m up |
| `el_span_deck` | `SM_El_Span_Deck` | 10 × 10.8 × 1.27 | 9 | 1 | solid slab to movement and rounds from 6.5 to 6.9 m; the train runs on it; Buzzards pass under or beside it, never over the tracks |
| `el_underdeck_lamp` | `SM_El_UnderdeckLamp` | 0.6 × 0.6 × 0.46 | 9 | 2 | none |
| `el_station_mezzanine` | `SM_El_Station_Mezzanine` | 6.6 × 8.2 × 2.4 | 1 | 1 | solid overhead box from 3.9 m: the lowest thing over the street; not reachable |
| `el_station_stair` | `SM_El_Station_Stair` | 7.85 × 5.1 × 6.25 | 2 | 1 | sealed scenery: the gate and the flight are solid; it is the hard west edge of the south (and north) sidewalk beside the start |
| `el_station_platform` | `SM_El_Station_Platform` | 10 × 3.5 × 4.3 | 14 | 2 | overhead, out of reach; solid slab and windscreen; Buzzards treat it as part of the El |

**Street and yards** (24)

| Brief id | Mesh | Size x × y × z (m) | Count | Priority | Gameplay role |
| --- | --- | --- | --- | --- | --- |
| `street_ground` | `SM_Street_Ground_Block` | 220 × 144 × 0 | 1 | 1 | walking surface at height 0; footstep and impact surfaces: asphalt, concrete (shop, cage, aprons), dirt (vacant lot) |
| `sidewalk_slab` | `SM_Street_Sidewalk` | 3 × 4 × 0.15 | 52 | 1 | walkable step 0.15 m high (walked up without jumping); surface concrete |
| `dropped_kerb` | `SM_Street_DroppedKerb` | 8.4 × 4 × 0.15 | 5 | 2 | road-level gaps in the sidewalk (no step); surface concrete |
| `road_markings` | `SM_Street_RoadMarkings` | decals | tiling | 2 | none |
| `court_surface` | `SM_Street_CourtSurface` | 20.2 × 20.6 × 0 | 1 | 1 | floor of the reel 3 arena (reel at the centre circle); surface concrete; 0.15 m below the sidewalk at the south gate |
| `hoarding_panel` | `SM_Street_Hoarding` | 2.44 × 0.13 × 2.7 | 28 | 1 | hard cover: solid to rounds and walkers at its full height (1.1 m parapet = crouch cover on the shed deck) |
| `chainlink_panel` | `SM_Street_ChainLink_Panel` | 2.4 × 0.36 × 2.62 | 10 | 2 | solid to rounds and walkers here (the scrim makes it opaque); 2.5 m high |
| `alley_gate` | `SM_Street_AlleyGate` | 5 × 0.1 × 2.72 | 1 | 2 | solid dead end (stops rounds too); the 2.6 m behind it is out of bounds |
| `cage_fence_panel` | `SM_Street_CageFence_Panel` | 3 × 0.2 × 4.12 | 26 | 1 | knee wall: low hard cover 0.5 m (0.65 m from the court on the south side). Mesh: stops walkers, lets rounds and sight through. Cannot be climbed |
| `cage_gate` | `SM_Street_CageGate` | 3.14 × 1.7 × 4.5 | 2 | 1 | open gateway 3.0 m wide: the only ways into the court (leaves have no collision) |
| `vacant_lot_gate` | `SM_Street_VacantLotGate` | 3.2 × 1.8 × 2.75 | 1 | 2 | open gateway 3.2 m wide from the south sidewalk into the vacant lot |
| `sidewalk_shed` | `SM_Street_SidewalkShed` | 21.6 × 3.5 × 3.9 | 1 | 1 | vantage: walkable deck 2.8 m above the sidewalk reached by the stair; parapet 1.1 m = crouch cover, shoot over standing; posts are slim cover; the sidewalk underneath stays walkable; two AI cover points and a propane tank on the deck |
| `rolling_scaffold` | `SM_Street_RollingScaffold` | 1.6 × 5 × 4.75 | 2 | 1 | hard cover: one solid box 1.6 x 5 x 3.8 m that blocks rounds and sight (the netting must read as opaque enough to justify it, or the collision must change with it) |
| `hoist_tower` | `SM_Street_HoistTower` | 2.94 × 3.93 × 9.75 | 1 | 2 | base: hard cover 2.6 m high that closes the sidewalk (walk round it in the parking lane). Netting above: stops walkers only, rounds pass |
| `kiosk_news` | `SM_Street_Kiosk` | 3.5 × 2.96 × 2.6 | 2 | 2 | hard cover 2.5 m high, one solid box; the newsstand is the kerb-side piece of the first sightline curtain |
| `tyre_cage` | `SM_Street_TyreCage` | 2.64 × 2.51 × 2.89 | 1 | 2 | hard cover 2.25 m high, one solid box (surface rubber): the wall-side piece of the first sightline curtain |
| `produce_stand` | `SM_Street_ProduceStand` | 4 × 2.63 × 2.85 | 1 | 2 | hard cover 2.35 m high, one solid box (surface wood): the wall-side piece of the second sightline curtain |
| `utility_dig` | `SM_Street_UtilityDig` | 3.4 × 2.24 × 3.6 | 1 | 2 | hard cover 2.2 m high, one solid box: the kerb-side piece of the second sightline curtain; a steam emitter 3.7 m above the sidewalk |
| `site_shanty` | `SM_Street_SiteShanty` | 3.1 × 2.58 × 3.06 | 1 | 2 | hard cover 2.7 m high, one solid box: the wall-side piece of the first sightline curtain on the south sidewalk |
| `lot_wall_rail` | `SM_Street_LotWall` | 3 × 0.3 × 1.13 | 5 | 2 | low hard cover 0.77 m high between the south sidewalk and the lot (crouch cover); the rail has no collision |
| `lot_barrier_arm` | `SM_Street_LotBarrierArm` | 1.9 × 0.22 × 3.65 | 1 | 3 | the housing is a small solid post; the raised boom has no collision |
| `wheel_stop` | `SM_Street_WheelStop` | 0.22 × 1.8 × 0.12 | 4 | 3 | none (walked over) |
| `steam_grate` | `SM_Street_SteamGrate` | 0.8 × 0.8 × 0.02 | 3 | 3 | none (flush); the two outdoor ones are steam emitters |
| `weeds` | `SM_Street_Weeds` | 0.6 × 0.6 × 0.6 | 26 | 3 | none (no collision, nothing to hide behind) |

Catalogue props the level places are **not** in this list (2.15 gives their sizes and positions). The ones that are
architecture in all but name, which the building artist must coordinate with the props artist: `fire_escape`
(11 balconies: three street fronts and the deli's alley side), `water_tower` (3 roofs), `ac_unit` (12, on roofs),
`billboard`, `lot_booth`, `bus_shelter`, `court_light`, `hoop`, `bleachers`, `street_lamp` (9), `bollard` (4 at the
shop doors), `car_lift` (2). The catalogue's `awning` prop (`SM_Architecture_Awning` in `assets/props.json`) is not
placed by the level: the three storefront awnings (7.46, 10.26 and 7.56 m long) are built by the storefront code with
the same section and can share that asset's construction.

Modelling rules that follow from the gameplay:

- **Collision faces do not move.** Model inside or flush with the collider extents of 2.4 to 2.10; relief (piers,
  cornices, awnings, sign boxes, sills) may stand proud by the web amounts (up to 0.42 m at the cornice, 1.35 m for an
  awning 2.15 m above the sidewalk) because none of it collides.
- **Cover heights are tuning.** A crouched player's eye is 1.05 m above the floor, a standing one about 1.68 m
  (`docs/DESIGN.md` 4 "Cover philosophy", `test/level-layout.test.js:347-352`). Keep: shed parapet 1.10, office timber
  panel 0.95, cage knee wall 0.50 (0.65 from the court on the south side), lot wall 0.77 from the lot, loading dock
  1.00, hoardings 2.2 and more, kiosks 2.5, scaffolds 3.8.
- **Openings are tuning.** Shop doors 6.0 × 4.3, 3.8 × 3.5 and 2.0 × 2.5; cage gates 3.0; vacant-lot gateway 3.2; lot
  entry 6.4 between the booth's barrier post and the pylon; alley 5.0 wide; cut 3.0; gangway 2.2; shed colonnade 3.2
  between post rows; headroom 5.3 under the El's cross girders, 3.9 under the station mezzanine.
- **See-through must match shoot-through** (3.8 items 3 and 4): where the web game draws mesh or netting over a solid
  collider, either make the object visibly opaque (tarp, scrim, stacked contents) or change the collision with the
  design lead's agreement.
- **The El must cast real stripes**: ties as separate timbers with 0.34 m gaps, girders with real depth; no alpha
  cards.
- **Wall modules** follow the shared convention (pivot at the bottom-left corner of the outer face, running along
  +X, outer face toward -Y in Blender); 4.1 gives the rotation for each compass face.

### 5.2 Surfaces and colours

Catalogue materials the level builds with (`src/config/catalog.js:6-64`). Colours are the web's night-tuned base
values: by day the library lightens ground and masonry and nothing but rubber and tinted glass may be near black
(`docs/CONTRACT.md` 11.1). Treat them as hue references, not as final albedo.

| Surface | Web colour | Used for in the level | Impact / footstep surface |
|---|---|---|---|
| `asphalt` / `asphalt_wet` | #1b1c1f / #121316 | roadway, lot, lane, alley; wet patches | asphalt |
| `sidewalk`, `curb` | #6f6c66, #85827a | sidewalk flags, kerb stones | concrete |
| `concrete` | #7b7a76 | aprons, cut, dock, lintels, copings, cornices, belt courses, footings, knee walls, lot wall, platforms | concrete |
| `concrete_dark` | #44444a | shop floor and roof slab, roof decks | concrete |
| `court` | #2f4f46 (keys #7a2e26) | the cage's playing surface | concrete |
| `dirt` | #3a3229 | vacant lot | dirt |
| `cinder` | #8a8880 (dado #27414b) | shop walls | concrete |
| `brick_red`, `brick_tan`, `brick_brown`, `brick_painted` | #7a3327, #9a8262, #5a4032, #b9b4a6 | N1 and S2; N2 and S3; S1; garages (and the neighbours' backs) | brick |
| `tile_white` | #d9d6cc | stall risers of the laundromat, barber, pizza, chicken | concrete |
| `steel_el` | #1f2a26 | all El steel, station steel, shop beams, columns, stringers, mezzanine posts | metal |
| `metal_dark` | #23262a | door and window frames, rails, lamp housings, mezzanine deck, stair treads, grates, pylon | metal |
| `metal_galv` | #8d949a | scaffold tube, fence posts and rails, skylight kerbs, fan blades, pipe rails | metal |
| `roll_gate` | #6c7074 | shutters, garage doors, shop door slats, station folding gates | metal |
| `corrugated` | #7c8084, tinted #1a2b3a, #2f4038, #1c2224, #24463a | shop fascia, station panels and roofing, kiosks, the shanty's and the tyre cage's roofs | metal |
| `chainlink` | #9aa0a4 (netting #2c5a3a) | all fences and gate leaves, hoist netting | metal |
| `chrome` | #d8dde2 | push bars, handles, barber-pole caps | metal |
| `wood` | #6d5236 (ties #2b221b, planks #4a3c2c) | ties, walkway planks, hoarding posts and caps, joists, stringers, crates, doors | wood |
| `plywood` | #a98a5c (green #23463c, orange #c4571a, office #6b5a43, stand #2d5a3a) | shed deck and treads, hoardings, shanty, hoist base, office panels, scaffold decks | wood |
| `fabric_awning`, `fabric` | awnings #1c2f5a, #1f5a3a, #b3261e; tarp and scrim #1f3a2c | awnings, produce canopy, tarp, scrim | cloth |
| `rubber`, `tire` | #121212, #0e0e0f | dock bumpers, castors, tyre stacks | rubber |
| `paint_yellow`, `paint_white`, `paint_red`, `plastic_orange` | #f2c21a, #e6e4dc, #b3261e, #e8641b | rails, floor lines, kerbs, barrier arm, steam stack, fruit | (visual only) |
| `glass_store`, `glass_dark`, `glass_lit_warm`, `glass_lit_cool`, `glass_skylight` | dark glass; emissive #ffb45e, #9fd4ff, #314a78 at night | shop windows, upper windows, lit shops and panes, skylights | glass |
| `leaves` | #1f3322 | weeds | (none) |

Three materials are the level's own: the mural painting (`yards.js:261-263`), the rust-orange debris netting of the
rolling scaffolds (a 0.48 m repeating weave, tapes every 6 cm, `street.js:166-193`) and the shared glow of lamp
lenses.

Glow colours of the level's fixtures: sodium #ffb45e (El lamps, garage lamps), work light #ffc48a with a #ffd9a8 lens
(shop), warm window #ffc98a, cool window #cfe4ff (also the station tubes), bulb white #fff1d0 (shed, shanty, office),
station globes #55ff8a, neon red #ff3030, green #55ff8a, gold #f6c21a, cyan #35e0ff, pink #ff3d9a.

### 5.3 Audio

The level makes no sound itself; it fixes where sound comes from and what things sound like.

| Need | Level data | Notes |
|---|---|---|
| Footsteps and bullet impacts per surface | the surface of every collider and of the ground (2.12, 3.2) | ten surfaces occur in the level: asphalt, concrete, metal, wood, rubber, glass, dirt, brick, cloth, and `car` on vehicles. Record or design a set for each; metal stairs and deck (mezzanine), plywood stair and deck (shed), acrylic court (reports concrete), dirt lot |
| Indoor / outdoor mix | `interiorAt` (3.3): the shop box with a 1.5 m fade | one reverb space: a hard block-and-steel garage 29 × 19 × 6 m with three large openings; weapon tails switch between "open street" and "inside the shop" (`docs/DESIGN.md` 7) |
| Under the El | `level.el` | the avenue between the column rows is under a steel deck 6.5 m up: a distinct slap-back for gunfire; the train passes on tracks at z ±2.1, rail top 6.83, over the full 92 m (and beyond to ±96) |
| Steam hiss | six points (2.13.7) | three manholes on the avenue, the alley grate, the lane grate, the dig's vent stack 3.85 m up |
| Hydrant | `hydrant_open` at (-12.25, 0, 7.34), spraying north | water jet and splash; the wet patch is 5.2 × 2.4 m round (-11.6, 4.6) |
| Neon and lit-sign buzz | lamp hints of kind `neon` (2.14) | 19 positions: the ten storefront signs, the shop's main sign and EXIT sign, the PARK pylon, the two pairs of station globes, two vending machines, the bus shelter's advert, the booth |
| Extractor fan | (5.8, 4.5, -22.1) in the shop's east wall | a steady 16 rpm rotor: audible in the shop and in the alley |
| Generator | catalogue `generator` at (-44.68, 0, 3.1), west closure | an idling engine behind the barriers at the west hoarding, feeding the floodlight stand at (-44.65, -2.9); the other two floodlight stands, (44.2, 7.9) and (-9.6, 13.3), have no generator |
| Reel boomboxes, truck idle | the three reel positions and the truck (2.13) | owned by `05b-props.md` and `04-flow.md`; the level fixes the positions |
| Chain-link | cage fence, roadblock, gates | rounds pass the cage mesh silently in the web game; a ricochet / rattle layer would sell it |
| Occlusion | the collider list | the shop, the alley and the yards are separated from the avenue by buildings 7 to 17 m high: sources in the cage or the lot should be occluded from the avenue's west end |

### 5.4 Reference views

`tools/scenarios/level-tour.cjs:17-55` holds 37 fixed cameras, one per place the level has to get right (start,
under the El, each reel, shop interior and mezzanine, alley, both sidewalks, the shed and its deck, the vacant lot and
mural, the lane, the cage, the lot and the truck, both closures, the roofline, four overviews). Render the web game
from them (`docs/DEV.md`, `tools/shot.cjs`) and match each in the rebuild. Web coordinates (convert with 4.1); the
field of view is the vertical angle in degrees, as three.js takes it (an Unreal camera takes the horizontal angle:
2 · atan(tan(vertical / 2) × aspect ratio)):

| # | View | Camera (x, y, z) | Looks at (x, y, z) | FOV |
| --- | --- | --- | --- | --- |
| 1 | start | (-37.4, 1.83, 8.15) | (-20, 1.7, 7.2) | 74 |
| 2 | start-back | (-33, 2.2, 5) | (-44, 3.4, 2) | 70 |
| 3 | avenue-east | (-27.4, 1.7, 1.5) | (10, 2.6, 0.5) | 70 |
| 4 | under-el | (-14, 1.2, -2.6) | (6, 6.2, 0.8) | 78 |
| 5 | el-side | (-21, 3, -10.3) | (-2, 6.4, 3) | 70 |
| 6 | reel1 | (-10.5, 2.4, 6.2) | (-4, 0.8, 0.6) | 68 |
| 7 | reel1-north | (-1, 2.6, -7.6) | (-5, 0.8, 1.5) | 70 |
| 8 | shop-front | (-11, 1.75, -3.2) | (-12, 2.4, -14) | 74 |
| 9 | shop-in | (-12.5, 1.75, -12.6) | (-6, 1.6, -23) | 78 |
| 10 | shop-east | (4.6, 1.75, -13.4) | (-12, 1.9, -23) | 78 |
| 11 | shop-mezz | (-19.5, 4.55, -26) | (-6, 1.2, -19) | 78 |
| 12 | shop-office | (-16.4, 4.4, -28.6) | (-23, 3.9, -29.4) | 78 |
| 13 | alley | (8.4, 1.75, -12.4) | (8.6, 2.4, -31) | 72 |
| 14 | alley-out | (8.5, 1.75, -28.5) | (8.4, 2.2, -8) | 72 |
| 15 | north-walk | (-26, 1.83, -9) | (10, 2.2, -9.4) | 70 |
| 16 | south-walk | (-28, 1.83, 9) | (10, 2.2, 9) | 70 |
| 17 | shed | (-3.2, 1.83, 8.6) | (12, 2.6, 9.4) | 74 |
| 18 | shed-deck | (2.2, 4.63, 9.4) | (-8, 1.2, -4) | 78 |
| 19 | shed-deck-east | (6, 4.63, 9.6) | (30, 2.4, 2) | 74 |
| 20 | vacant | (-10, 1.75, 12.4) | (-13.5, 3.6, 20) | 78 |
| 21 | mural | (-5.2, 1.9, 19) | (-16, 4.4, 18.2) | 74 |
| 22 | lane | (-13, 1.75, 28.6) | (20, 1.9, 28.4) | 70 |
| 23 | lane-west | (20.5, 1.75, 28.5) | (-12, 1.9, 28.6) | 70 |
| 24 | cage-gate | (34.5, 1.83, -8.4) | (35.2, 1.4, -22.5) | 74 |
| 25 | cage-in | (27.5, 1.75, -15) | (38, 1.2, -25) | 78 |
| 26 | cage-reel | (39.5, 2.2, -18.2) | (34.8, 0.9, -22.8) | 70 |
| 27 | cut | (23.5, 1.75, -11.6) | (23.6, 2, -33) | 72 |
| 28 | lot-entry | (31.8, 1.83, 8.6) | (36, 2, 26) | 74 |
| 29 | lot-truck | (33.8, 1.75, 26.2) | (41.5, 1.6, 30) | 70 |
| 30 | lot-north | (43.5, 1.75, 31.5) | (30, 3.4, 12) | 78 |
| 31 | roadblock | (30, 1.75, 1) | (45, 2.2, 0.2) | 70 |
| 32 | west-end | (-33, 1.75, -1) | (-46, 2.6, 0.4) | 74 |
| 33 | roofline | (6, 13, 3) | (-8, 5, -22) | 62 |
| 34 | overview | (0, 104, 1.2) | (0, 0, 0) | 46 |
| 35 | overview-north | (-4, 46, 26) | (-4, 0, -12) | 60 |
| 36 | overview-south | (6, 46, -26) | (6, 0, 12) | 60 |
| 37 | overview-east | (8, 38, 0) | (34, 0, 0) | 62 |

---------------------------------------------------------------------------------------------------

## 6 Open questions and risks

1. **Prop yaw convention.** The shared convention says props face +X; the web catalogue's non-vehicle props face +Z
   (`docs/CONTRACT.md` 6.2). `05b-props.md` 4.1 keeps the web local frame for every prop (length +X, front -Y in
   Blender), and this spec's yaws (2.13, 2.15) assume the same: Unreal yaw = -ψ. If the asset pipeline turns furniture
   fronts to +X instead, every such placement needs +90°. The exporter and the Blender pipeline must use one rule.
2. **Night dressing in a daytime game** (3.8 item 11). Should the station be closed for the El repairs rather than
   "1 AM – 5 AM", and should the nail salon, garages and newsstands be shut at 4:15 PM? The sign copy is level data
   and needs a decision before the sign textures are made.
3. **Collision fidelity versus looks.** The rolling scaffolds, tyre cage, produce stand and dig pen are single solid
   boxes; the alley gate and roadblock fence stop bullets while the cage fence does not. Photoreal versions will
   invite shots through gaps that the web game blocks. Keeping the boxes preserves the 45 m sightline rule and the
   reel 1 arena; changing them needs a balance pass.
4. **Skylights and interior lighting.** Real rooflights will light the shop by day very differently from four
   pooled work lights; reel 2's arena was tuned for the dim interior. Confirm that real openings are wanted, and
   that their glass stays solid to Buzzards and rounds.
5. **Set extension.** Beyond both closures the web game has only road, sidewalks and El to x ±96 and the
   atmosphere's far skyline; behind the neighbours' backs there is nothing. `docs/unreal/ART_BIBLE.md` 4.8 asks for
   the next blocks out to about 300 m and the El running on 150 m each way, but there is no web layout to port for
   them: footprints, heights and what closes the view over each 2.5 … 2.7 m closure need their own blockout.
6. **Rear elevations.** The 3.1 m window grid counted from the ground does not match the 3.8 + 3.1 n floor levels
   (3.8 item 9). The rebuild should redesign the side and back walls on the real floor levels; window positions on
   those walls are therefore not binding.
7. **Shop interiors behind glass.** Nine shops have display windows with nothing behind them in the web game
   (lit panes at night, dark glass by day). Decide between dressed shallow interiors, interior-mapping shaders, or
   blinds and paper in the windows.
8. **Nudged points.** 21 spawn and cover points were moved by the web nav grid, whose cells depend on
   the low-poly prop colliders. The rebuild should take the authored positions and snap them to its own navmesh, then
   re-check the rules of 3.7 (hidden spawns, cover beside an obstacle).
9. **Lamp numbers are not photometric.** Intensities and ranges in 2.14 are three.js values tuned for a night scene
   with a handful of real lights. They give relative weights and colours only; `docs/unreal/ART_BIBLE.md` 2 sets the
   physical targets.
10. **The stoop, the cut's surface, the misplaced mailbox and meter, the billboard's facing, the benches' facing**
    (3.8 items 5, 7, 8, 10) are small as-built quirks; each needs a keep-or-fix call from the design lead.
11. **The station as playable space.** Stairs, mezzanine and platforms are fully modelled volumes that the player
    never reaches. A later mode could open them; if not, they can be built to a lower standard above eye level.
12. **Enemy use of player-only walls and of the decks.** Whether Goons and Buzzards are stopped by the cage mesh,
    railings and seals, and whether Goons may climb to the shed deck and the mezzanine, is decided in
    `03-enemies.md` (its questions 1, 7 and 17); the level only marks the volumes and publishes the three raised
    cover points and `level.vantage`, which nothing uses today.
