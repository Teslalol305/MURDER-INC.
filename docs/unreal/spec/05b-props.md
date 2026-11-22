# 05b — Props and vehicles

Port spec for the prop factory of the web game (`G.props`, docs/CONTRACT.md 6.2): every catalogue prop, the
vehicles in detail, the three gameplay props, and where the level stands them.

**Ground truth.** `src/props.js`, `src/props/{kit,vehicles,street,clutter,gameplay,lot,shop,atlas,materials}.js`,
`src/config/catalog.js`, `src/stubs/props.js` (the factory); `src/level.js` and `src/level/{kit,street,yards,shop,
buildings,ground,data,layout}.js` (placement); `src/game.js`, `src/explosives.js`, `src/config/flow.js` (what drives
the stateful props).

**How to read the numbers.**

- Citations are `path:line` from the repository root. Values marked **(measured)** are not typed anywhere in the
  source: they were read back from the game's own code run headless (see the last bullet).
- Web units: metres, seconds, radians. World: +Y up, east +X, north −Z.
- A prop's local frame: origin on the ground at the footprint centre, length along +X, up +Y
  (src/props.js:11-14). Vehicles and the basketball hoop point their nose at local +X; every other prop with a front
  (bench, booth, sign, lamp arm, hydrant jet) faces local **+Z**; wall-mounted pieces have the wall at −Z
  (docs/CONTRACT.md:338-341).
- Sizes are written **L × W × H** = along local X × along local Z × up. The catalogue stores them as `[L, H, W]`
  (src/config/catalog.js:3). In Blender axes that is `[x, y, z] = [L, W, H]`.
- "Catalogue box" is the nominal size in src/config/catalog.js. "Model" is the bounding box of the geometry the
  builder really makes. "Collider" is what physics gets. All three differ a little; the collider is what gameplay
  feels.
- Counts, seeds, resolved colours and model sizes in this document were measured by running the game's own factory
  and level builder headless in node (real `createProps`, real `createLevel`, default world seed 1994, texture-free
  materials). Nothing here is hand-counted. A different `?seed` changes only the picks the level left to the seed
  (section 3.1).

---------------------------------------------------------------------------------------------------

## 1. Overview

Props are the furniture of the block and almost all of its cover. The level builder asks one factory for 68 named
things (cars, vans, trucks, barriers, trash, shop equipment, court and lot fittings, rooftop plant) and stands 329
of them on the block: 308 static or animated props and 21 explosives. For the player they do four jobs. They are
**cover**: every prop carries one to four box colliders with a surface type, tuned so that a crouched eye (1.05 m)
is hidden behind a car body while a standing eye (1.68 m) shoots over the bonnet, and so that vans, trucks and the
armoured truck are full-height hard cover. They are the **objective**: three master-reel road cases with a gold
beacon, a boombox leaking the beat and an IPX tracker tag, each with a three-state visual (waiting, being grabbed,
taken), and the black IPX vault truck whose rear doors swing open when the player wins. They are **hazards and
tools**: 14 propane tanks and 7 welding racks that stand as solid cover until a round lights their fuse. And they
are the **look of the place**: yellow cabs, a Vulture van with its doors open beside reel 1, a burned-out car, a
food cart, an IPX billboard and an IPX ad in the bus shelter. Nothing drives, nothing breaks except the explosives,
and nothing can be picked up: apart from the reel cases, the truck, the explosives and an open hydrant, every prop on
the block is static.

---------------------------------------------------------------------------------------------------

## 2. Facts

### 2.1 Factory and placement constants

| Fact | Value | Source |
|---|---|---|
| Catalogue size | 68 props: 10 vehicles and carts, 24 street furniture, 14 loose cover and clutter, 8 chop shop, 5 court and lot, 4 rooftop and facade, 3 gameplay | src/config/catalog.js:68-144 |
| Instances on the block | 308 placed by the level + 21 explosives = 329; 62 of the 68 types are used | src/level.js:208, src/level/data.js:119-141 |
| Never placed | `traffic_light`, `sign_post`, `fence_panel`, `fence_tall`, `awning`; `boombox` only as part of `master_case` | measured |
| What `build(name, opts)` returns | `object` (the model), `colliders` (local boxes with surface and flags), `size` and `surface` from the catalogue, and when they apply `dynamic`, `update(dt)`, `setState(state, t)`, `state`, `lights` (lamp hints), `anchors`, `nodes` (named moving parts), `fallback` | docs/CONTRACT.md:318-328, 347-353; src/props.js:161-175 |
| Options | `color`, `seed`, `variant`, `open`, `lit`, `on`, `text`, `spray` | docs/CONTRACT.md:327, 354-364 |
| Seed of an instance | `opts.seed` when finite: `abs(floor(seed))`; else an integer 0…65535 drawn from the factory's own random stream (`fork('props')` of the world seed) | src/props.js:50, 206 |
| Shape variant | `seed mod variants` (specs without `variants` have one shape) | src/props.js:91 |
| Colour | `opts.color`, else the spec's forced colour, else `palette[scramble(seed, 17) mod n]` | src/props.js:128-132 |
| `scramble(seed, salt)` | `((imul(seed + salt, 0x9e3779b1)) >>> 8) & 0xffff` | src/props.js:44 |
| Dome light (parked car's interior light on) | `opts.lit`, else `scramble(seed, 91) / 65535 < dome`; dome = sedan 0.14, taxi 0.30, SUV 0.10, pickup 0.08 | src/props.js:133, src/props/vehicles.js:516, 525, 550, 567 |
| Shadow casting | only props whose catalogue height > 0.3 m; decals, lit quads, lamp lenses and transparent parts never cast | src/props.js:46-47, 140, 154 |
| Dynamic prop | catalogue flag `dynamic`, or the instance has `update` / `setState`: kept out of the static merge | src/props.js:218-221 |
| Missing or failing builder | plain box of the catalogue size, one collider of that size, catalogue surface (`fallback: true`); unknown name: 1 × 1 × 1 m metal box | src/props.js:41, 179-198 |
| Floor height under a prop | 0 on the roadway and yards, 0.15 (`KERB`) on sidewalk slabs, unless the level gives `y` (decks, roofs, the lift) | src/level/kit.js:597, src/level/layout.js:23, 187-191 |
| Walk-over rule | a collider less than 0.2 m tall whose top is under 0.3 m is not registered | src/level/kit.js:618 |
| Vehicle paint chart of the level | 9 colours; applies to `sedan`, `suv`, `van`, `box_truck`, `pickup` (section 2.4.3) | src/level/kit.js:61-62, 163-181 |
| Prop work lights | a prop's `work` lamp hint gets priority 6 when placed (the shop's own four keep 10) | src/level/kit.js:54, 642 |
| Player sizes that define cover | body radius 0.32, height 1.8, crouched 1.15; eye 1.68, crouched eye 1.05; step-up 0.42 | src/config/player.js:6-10, src/physics.js:21 |
| Triangle count of the web catalogue | 31 614 for one of each (first variant); budget test allows < 45 000 | measured; test/props-catalog.test.js:217-218 |

### 2.2 The catalogue

One row per catalogue id. Catalogue box and model are L × W × H in metres. "Collider tops" lists the top of every
collider box (`b` = stops bullets only, `p` = stops the player only; full boxes are in Appendix B). "Var" is the
number of seed-picked shape variants. Zones: W = west end (x < −30), A = avenue zone (x −30…22, z ≥ −11: the
avenue, both sidewalks, the vacant lot, the rear lane), S = shop zone (x −30…22, z < −11: the shop, the alley,
the deli block), L = lot zone (x > 22: the Cage, the east end of the avenue, the parking lot)
(src/level/layout.js:158-182).

| id | Catalogue box | Model **(measured)** | Surface | Collider tops | Var | Count **(measured)** | Zones | Builder |
|---|---|---|---|---|---|---|---|---|
| `sedan` | 4.6 × 1.85 × 1.45 | 4.61 × 1.85 × 1.45 | car | 1.08 / 1.45 | 4 | 13 | W1 A3 S2 L7 | src/props/vehicles.js:513 |
| `taxi` | 4.7 × 1.85 × 1.55 | 4.61 × 1.85 × 1.55 | car | 1.08 / 1.45 | 1 | 3 | A2 L1 | src/props/vehicles.js:523 |
| `suv` | 4.9 × 2 × 1.82 | 4.91 × 2 × 1.82 | car | 1.24 / 1.78 | 2 | 2 | W1 L1 | src/props/vehicles.js:547 |
| `pickup` | 5.3 × 2 × 1.8 | 5.32 × 2 × 1.78 | car | 1.27 / 1.78 | 2 | 2 | A1 L1 | src/props/vehicles.js:564 |
| `van` | 5.2 × 2 × 2.2 | 5.21 × 1.96 × 2.19 | car | 2.14 | 1 | 11 | W1 A8 L2 | src/props/vehicles.js:589 |
| `box_truck` | 7.4 × 2.45 × 3.3 | 7.39 × 2.44 × 3.31 | car | 3.3 / 2.28 | 2 | 3 | A2 L1 | src/props/vehicles.js:599 |
| `burned_car` | 4.5 × 1.8 × 1.3 | 4.38 × 1.72 × 1.3 | car | 0.96 / 1.3 b | 1 | 1 | A1 | src/props/vehicles.js:605 |
| `ipx_truck` | 6.8 × 2.5 × 3 | 6.81 × 2.48 × 2.96 | car | 2.86 / 2.58 | 1 | 1 | L1 | src/props/vehicles.js:622 |
| `motorbike` | 2 × 0.7 × 1.1 | 1.94 × 0.67 × 1.1 | metal | 0.95 | 1 | 3 | A2 L1 | src/props/vehicles.js:610 |
| `food_cart` | 2.4 × 1.4 × 2.25 | 2.39 × 1.33 × 2.24 | metal | 1.25 / 2.25 b | 1 | 1 | A1 | src/props/vehicles.js:615 |
| `jersey_barrier` | 3 × 0.6 × 0.81 | 3 × 0.61 × 0.81 | concrete | 0.81 | 3 | 16 | W4 A5 L7 | src/props/street.js:102 |
| `traffic_barrel` | 0.6 × 0.6 × 1 | 0.6 × 0.57 × 1 | rubber | 0.98 | 1 | 13 | W2 A5 L6 | src/props/street.js:116 |
| `traffic_cone` | 0.36 × 0.36 × 0.7 | 0.36 × 0.36 × 0.7 | rubber | none | 1 | 10 | W3 A4 L3 | src/props/street.js:131 |
| `barricade` | 2.4 × 0.5 × 1.1 | 2.4 × 0.5 × 1.1 | wood | 1 | 1 | 6 | W2 A2 L2 | src/props/street.js:140 |
| `dumpster` | 1.9 × 1.1 × 1.35 | 1.9 × 1.1 × 1.36 | metal | 1.3 | 2 | 6 | A2 S2 L2 | src/props/street.js:158 |
| `trash_can` | 0.6 × 0.6 × 0.95 | 0.6 × 0.6 × 0.96 | metal | 0.95 | 1 | 6 | W2 A2 L2 | src/props/street.js:182 |
| `trash_bags` | 1.4 × 1 × 0.7 | 1.28 × 0.97 × 0.63 | cloth | 0.62 | 3 | 13 | W1 A8 S2 L2 | src/props/street.js:196 |
| `mailbox` | 0.55 × 0.55 × 1.25 | 0.52 × 0.51 × 1.19 | metal | 1.2 | 2 | 2 | W1 A1 | src/props/street.js:215 |
| `newspaper_box` | 0.5 × 0.45 × 1.1 | 0.48 × 0.44 × 1.08 | metal | 1.08 | 1 | 7 | W2 A3 L2 | src/props/street.js:231 |
| `hydrant` | 0.35 × 0.35 × 0.75 | 0.35 × 0.32 × 0.75 | metal | 0.74 | 1 | 2 | L2 | src/props/street.js:247 |
| `hydrant_open` | 0.35 × 0.35 × 0.75 | 2.6 × 4.55 × 0.75 | metal | 0.74 | 1 | 1 | A1 | src/props/street.js:254 |
| `phone_booth` | 0.9 × 0.9 × 2.2 | 0.9 × 0.9 × 2.2 | metal | 2.2 | 2 | 3 | W1 A1 L1 | src/props/street.js:292 |
| `bus_shelter` | 3.6 × 1.5 × 2.5 | 3.6 × 1.5 × 2.48 | glass | 2.3 / 2.2 / 0.5 / 2.48 | 1 | 1 | L1 | src/props/street.js:324 |
| `street_lamp` | 0.4 × 0.4 × 8 | 0.34 × 2.7 × 7.88 | metal | 7.3 | 2 | 9 | W1 A2 L6 | src/props/street.js:359 |
| `traffic_light` | 0.4 × 0.4 × 6 | 0.62 × 3.41 × 5.76 | metal | 5.55 | 1 | 0 | — | src/props/street.js:379 |
| `parking_meter` | 0.2 × 0.2 × 1.3 | 0.17 × 0.17 × 1.3 | metal | 1.3 | 1 | 8 | W1 A5 L2 | src/props/street.js:435 |
| `bench` | 1.8 × 0.6 × 0.85 | 1.76 × 0.55 × 0.84 | wood | 0.47 / 0.85 | 1 | 5 | W1 A1 L3 | src/props/street.js:446 |
| `planter` | 1.2 × 1.2 × 0.8 | 1.2 × 1.2 × 0.79 | concrete | 0.8 | 2 | 3 | L3 | src/props/street.js:465 |
| `tree` | 0.6 × 0.6 × 6 | 4.53 × 4.71 × 5.73 | wood | 0.55 / 3 | 3 | 3 | L3 | src/props/street.js:491 |
| `bollard` | 0.2 × 0.2 × 1 | 0.2 × 0.2 × 1 | metal | 1 | 1 | 4 | A4 | src/props/street.js:526 |
| `sign_post` | 0.6 × 0.08 × 2.8 | 0.34 × 0.04 × 2.8 | metal | 2.8 | 3 | 0 | — | src/props/street.js:536 |
| `fence_panel` | 3 × 0.08 × 2.4 | 3.05 × 0.06 × 2.4 | metal | 2.4 | 1 | 0 | — | src/props/street.js:563 |
| `fence_tall` | 3 × 0.08 × 4 | 3.05 × 0.06 × 4 | metal | 4 | 1 | 0 | — | src/props/street.js:564 |
| `manhole` | 0.9 × 0.9 × 0.02 | 0.9 × 0.9 × 0.02 | metal | none | 1 | 6 | W1 A4 L1 | src/props/street.js:566 |
| `milk_crates` | 0.7 × 0.7 × 1 | 0.68 × 0.68 × 0.85 | rubber | 0.9 | 3 | 10 | A6 S2 L2 | src/props/clutter.js:83 |
| `pallet` | 1.2 × 1 × 0.14 | 1.2 × 1 × 0.14 | wood | 0.14 | 1 | 4 | A2 S1 L1 | src/props/clutter.js:105 |
| `pallet_stack` | 1.2 × 1 × 1.15 | 1.23 × 1.03 × 1.15 | wood | 1.15 | 2 | 9 | W1 A2 S3 L3 | src/props/clutter.js:112 |
| `crate_wood` | 1.1 × 0.9 × 1 | 1.1 × 0.9 × 1 | wood | 1 | 2 | 8 | A4 S2 L2 | src/props/clutter.js:123 |
| `cardboard_boxes` | 1 × 0.8 × 0.8 | 0.95 × 0.78 × 0.77 | wood | 0.72 | 2 | 9 | A4 S3 L2 | src/props/clutter.js:144 |
| `shopping_cart` | 0.9 × 0.55 × 1 | 0.91 × 0.52 × 1.02 | metal | 0.95 | 1 | 5 | A3 L2 | src/props/clutter.js:174 |
| `mattress` | 1.9 × 0.95 × 0.25 | 1.74 × 0.86 × 0.22 | cloth | none | 2 | 1 | A1 | src/props/clutter.js:215 |
| `tire_stack` | 0.8 × 0.8 × 1 | 0.77 × 0.77 × 0.97 | rubber | 0.98 | 2 | 14 | A5 S6 L3 | src/props/clutter.js:227 |
| `oil_drum` | 0.6 × 0.6 × 0.9 | 0.58 × 0.57 × 0.9 | metal | 0.9 | 2 | 14 | A4 S6 L4 | src/props/clutter.js:238 |
| `sandbags` | 2 × 0.6 × 0.9 | 1.95 × 0.56 × 0.9 | dirt | 0.9 | 2 | 5 | A4 L1 | src/props/clutter.js:258 |
| `generator` | 2.2 × 1 × 1.4 | 2.2 × 1 × 1.39 | metal | 1.22 | 1 | 1 | W1 | src/props/clutter.js:279 |
| `floodlight_stand` | 1 × 1 × 2.2 | 0.96 × 0.94 × 2.16 | metal | 2.15 | 1 | 3 | W1 A1 L1 | src/props/clutter.js:308 |
| `porta_potty` | 1.2 × 1.2 × 2.3 | 1.2 × 1.21 × 2.29 | rubber | 2.25 | 1 | 2 | A2 | src/props/clutter.js:338 |
| `boombox` | 0.6 × 0.25 × 0.35 | 0.6 × 0.2 × 0.35 | rubber | none | 1 | 0 | — | src/props/clutter.js:361 |
| `car_lift` | 4.8 × 3.2 × 3.6 | 2.14 × 3.16 × 3.58 | metal | 3.5 / 3.5 | 2 | 2 | S2 | src/props/shop.js:28 |
| `car_on_stands` | 4.5 × 1.85 × 1.6 | 4.38 × 1.72 × 1.6 | car | 1.23 / 1.6 | 1 | 1 | S1 | src/props/shop.js:63 |
| `tool_chest` | 1.1 × 0.55 × 1.1 | 1.09 × 0.54 × 1.09 | metal | 1.09 | 1 | 4 | S4 | src/props/shop.js:87 |
| `workbench` | 2.2 × 0.8 × 0.95 | 2.2 × 0.78 × 0.96 | wood | 0.8 | 1 | 3 | S3 | src/props/shop.js:113 |
| `engine_hoist` | 1.6 × 1.2 × 2 | 1.47 × 1.09 × 1.96 | metal | 1.6 / 1.38 / 0.16 | 1 | 2 | S2 | src/props/shop.js:139 |
| `shelf_rack` | 2.7 × 0.9 × 3 | 2.7 × 0.87 × 3 | metal | 3 | 2 | 5 | S5 | src/props/shop.js:175 |
| `compressor` | 1.2 × 0.6 × 1 | 1.11 × 0.54 × 0.87 | metal | 0.9 | 1 | 2 | S2 | src/props/shop.js:213 |
| `vending_machine` | 0.9 × 0.8 × 1.85 | 0.9 × 0.8 × 1.85 | metal | 1.85 | 1 | 2 | A1 S1 | src/props/shop.js:244 |
| `hoop` | 1.8 × 1.2 × 4 | 1.62 × 1.2 × 3.98 | metal | 3.4 / 4 | 1 | 2 | L2 | src/props/lot.js:18 |
| `bleachers` | 4 × 2 × 1.6 | 4 × 1.96 × 1.6 | metal | 0.42 / 0.78 / 1.14 / 1.5 | 1 | 3 | L3 | src/props/lot.js:43 |
| `court_light` | 0.4 × 0.4 × 9 | 1.3 × 1.3 × 8.86 | metal | 8.55 | 1 | 2 | L2 | src/props/lot.js:65 |
| `lot_booth` | 2.2 × 1.8 × 2.6 | 2.2 × 1.8 × 2.59 | metal | 2.37 | 1 | 1 | L1 | src/props/lot.js:86 |
| `billboard` | 9 × 1.2 × 11 | 9 × 1.15 × 10.8 | metal | 6.7 / 6.7 / 10.8 | 1 | 1 | L1 | src/props/lot.js:120 |
| `water_tower` | 3 × 3 × 5 | 2.8 × 2.74 × 4.98 | wood | none | 1 | 3 | W1 A1 S1 | src/props/lot.js:167 |
| `ac_unit` | 1.2 × 0.9 × 0.9 | 1.2 × 0.9 × 0.9 | metal | 0.86 | 1 | 12 | W4 A4 S4 | src/props/lot.js:194 |
| `fire_escape` | 3 × 1.1 × 3 | 2.99 × 1.07 × 3 | metal | none | 1 | 11 | W6 A3 S2 | src/props/lot.js:210 |
| `awning` | 4 × 1.3 × 0.9 | 4 × 1.29 × 0.9 | cloth | none | 1 | 0 | — | src/props/lot.js:264 |
| `master_case` | 0.9 × 0.6 × 1.05 | 0.94 × 0.63 × 1.25 | metal | 0.66 / 0.35 b / 0.66 p | 1 | 3 | A1 S1 L1 | src/props/gameplay.js:324 |
| `propane_tank` | 0.32 × 0.32 × 0.6 | 0.3 × 0.33 × 0.59 | metal | 0.6 | 1 | 14 | A8 S1 L5 | src/props/gameplay.js:331 |
| `welding_rack` | 0.9 × 0.5 × 1.6 | 0.91 × 0.53 × 1.52 | metal | 1.5 | 1 | 7 | A2 S4 L1 | src/props/gameplay.js:362 |

Notes on the table.

- `taxi`: the body is the sedan body (4.61 long, 1.45 to the roof); only the roof light reaches 1.55. Its
  catalogue box is 0.1 m longer than anything built (src/config/catalog.js:71, src/props/vehicles.js:527).
- `hydrant_open`: the model size includes the two wet patches on the ground (radius 0.9 and 1.3); the hydrant
  itself is the same body as `hydrant`.
- `street_lamp`, `traffic_light`, `tree`, `court_light`: the arm, mast arm, crown and flood heads overhang the
  catalogue footprint on purpose (docs/CONTRACT.md:342-346).
- `car_lift`: the catalogue box (4.8 long) is the lift with a car on it; the lift alone is 2.14 long.
- `master_case`: model height 1.25 is the beacon mast; the beacon lens on top reaches 1.346 and the light shaft
  7.34 (section 2.5.1).
- `propane_tank`, `welding_rack`: the explosives module does **not** use the builder's collider. It registers
  an axis-aligned box of the catalogue size around the rotated footprint (section 2.5.2). Effective tops: 0.60
  and 1.60.
- `ac_unit`, `water_tower`, `fire_escape`: every placed instance sits on a roof or a facade with `collide: false`;
  the roof plant on the brick buildings is also placed with `cast: false` (src/level/buildings.js:69-73, 284-286;
  src/level/shop.js:326-327).
- `pallet` (0.144 tall) falls under the walk-over rule: the four placed pallets have no collision. So do the
  `engine_hoist` legs (0.16).

### 2.3 Cover heights at a glance

Collider tops against the two eye heights (crouched 1.05 m, standing 1.68 m). DESIGN.md section 4 quotes round
numbers; the code values below win.

| Class | Props (collider top in m) |
|---|---|
| Below a crouched eye (< 1.05) | `trash_bags` 0.62, `cardboard_boxes` 0.72, `hydrant` 0.74, `planter` 0.80, `workbench` 0.80, `jersey_barrier` 0.81, `milk_crates` 0.90, `oil_drum` 0.90, `sandbags` 0.90, `compressor` 0.90, `trash_can` 0.95, `shopping_cart` 0.95, `motorbike` 0.95, `burned_car` body 0.96, `traffic_barrel` 0.98, `tire_stack` 0.98, `barricade` 1.00, `crate_wood` 1.00, `bollard` 1.00, `bench` 0.47 seat and 0.85 back, `propane_tank` 0.60, `master_case` 0.66 |
| Hides a crouched eye, a standing eye sees over (1.05…1.68) | car bodies: `sedan` / `taxi` 1.08, `suv` 1.24, `pickup` 1.27, `car_on_stands` 1.23; `newspaper_box` 1.08, `tool_chest` 1.09, `pallet_stack` 1.15, `mailbox` 1.20, `generator` 1.22, `food_cart` 1.25, `dumpster` 1.30, `parking_meter` 1.30, car cabins: `sedan` / `taxi` 1.45, `car_on_stands` 1.60, `welding_rack` 1.60 |
| Full standing cover (> 1.68) | `suv` and `pickup` cabins 1.78, `vending_machine` 1.85, `van` 2.14, `floodlight_stand` 2.15 (a 0.44 m post), `phone_booth` 2.20, `porta_potty` 2.25, `bus_shelter` 2.30, `lot_booth` 2.37, `box_truck` 2.28 cab and 3.30 box, `ipx_truck` 2.58 cab and 2.86 vault, `shelf_rack` 3.00, `car_lift` posts 3.50, lamp and sign poles |

Differences from DESIGN.md section 4 (docs/DESIGN.md:210-212): "car bonnets 1.0" is 1.08 for the whole lower
body of a sedan (src/props/vehicles.js:83); "trash-bag piles 0.7" is 0.62; "milk-crate stacks 1.0" is 0.90 (the model
is 0.85); "traffic barrels 1.0" is 0.98; "newspaper boxes 1.1" is 1.08; "mailboxes 1.25" is 1.20; "dumpsters
1.35" is 1.30.

The cabin box of a car has surface `glass` and is a full collider: it stops rounds and bodies. Car windows do not
break (src/props/vehicles.js:446-456).

### 2.4 Vehicles

No vehicle moves. They are parked, abandoned or wrecked scenery with colliders. The only animated one is the IPX
truck (rear doors, hazard lamps).

#### 2.4.1 One body builder, five body styles

Sedan, taxi, SUV, pickup, van and the cab of the box truck are the same code fed with a table of lengths and
heights (src/props/vehicles.js:352-443). A body is a side outline with wheel arches pushed across the width and
chamfered 0.04, a narrower greenhouse on top with separate glass, four wheels, bumpers, lamps, mirrors and trim.
The body tapers in plan toward nose and tail, tucks under at the sills and leans in above the belt line. x is
measured from the middle of the car, nose at +x; all values in metres.

| Parameter | Sedan and taxi | SUV | Pickup | Van | Box-truck cab |
|---|---|---|---|---|---|
| Source (src/props/vehicles.js) | 40-84 | 462-471 | 473-483 | 485-494 | 497-506 |
| Length L | 4.6 | 4.9 | 5.3 | 5.2 | 2.9 (cab alone; truck 7.4) |
| Roof height H | 1.45 | 1.78 | 1.78 | 2.14 | 2.28 |
| Sheet-metal width (2 × hw) | 1.73 | 1.88 | 1.88 | 1.88 | 2.08 |
| Wheel radius / tyre width / rim radius | 0.325 / 0.21 / 0.22 | 0.40 / 0.27 / 0.27 | 0.39 / 0.27 / 0.25 | 0.36 / 0.24 / 0.22 | 0.44 / 0.28 / 0.27 |
| Wheel style | chrome hubcap or dark steel (sedan variants); steel (taxi) | 5-spoke alloy | steel | steel | steel |
| Front axle x / rear axle x | 1.42 / −1.38 | 1.50 / −1.42 | 1.72 / −1.50 | 1.70 / −1.50 | 0.70 / none |
| Wheelbase | 2.80 | 2.92 | 3.22 | 3.20 | truck: 5.04 |
| Ground clearance | 0.20 | 0.27 | 0.30 | 0.26 | 0.42 |
| Belt line (base of the glass) | 1.02 | 1.22 | 1.25 | 1.16 | 1.50 |
| Bonnet height at nose → at cowl | 0.90 → 1.00 | 1.12 → 1.20 | 1.12 → 1.22 | 1.02 → 1.14 | 1.30 → 1.45 |
| Boot lid height | 1.01 | none (two-box) | load bed, floor 0.92 | none | none |
| Windscreen base x (cowl) / top x | 0.98 / 0.30 | 1.00 / 0.45 | 1.22 / 0.72 | 1.92 / 1.42 | 0.28 / −0.06 |
| Rear screen top x / base x | −1.00 / −1.52 | −2.12 / −2.33 | −0.42 / −0.50 | −2.50 / −2.52 | −1.30 / −1.33 |
| Roof narrower than belt (tumble) | 17 % | 12 % | 12 % | 7 % | 8 % |
| Plan taper nose / tail | 9 % / 6 % | 7 % / 3 % | 6 % / 0 | 4 % / 1.5 % | 8 % / 0 |
| Sill tuck | 3.5 % | 3.5 % | 3.5 % | 3.5 % | 3.5 % |
| B pillar x | −0.20 | −0.12 | 0.05 | 0.52 | −1.00 |
| Side glass | front and rear doors | front, rear and a quarter light | cab only (ends x −0.38) | cab door only (ends x 0.52) | cab only (ends x −0.90) |
| Back glass | yes | yes | yes | no | no |
| Bumpers / grille / mirrors | dark plastic / dark / body colour | body colour / chrome / body colour | chrome / chrome / body colour | dark / dark / dark | chrome, front only / chrome / dark, on stalks |
| Top of the lower collider (`cover`) | 1.08 | 1.24 | 1.27 | (one full-height box) | (one box, 2.28) |

Shared constants (src/props/vehicles.js:13-25, 86): wheel-arch radius = tyre radius + 0.055; bumpers stand 0.06 proud;
greenhouse inset 0.055 per side; glass sits 0.012 proud; wheels are 10-sided. Lamp colours, as unlit glow × HDR
gain: tail `#ff1a10` × 0.6, amber indicator `#ff8a1a` × 0.5, headlamp on `#fff0d0` × 3.2, headlamp off
`#cfd8e0` × 0.2, amber marker `#ffa030` × 1.6.

Collider rule for cars (src/props/vehicles.js:446-456): lower box x ±L/2, z ±(hw + 0.02), y 0…cover, surface `car`;
cabin box x from the middle of the rear screen to the middle of the windscreen, z ±(hw − 0.055)(1 − tumble/2),
y cover…H, surface `glass` (surface `car` when the car has no glass). A car raised by `lift` starts its lower box
at lift + clearance.

#### 2.4.2 What every car carries

From src/props/vehicles.js:391-440, on any body with `trim`:

- **Nose**: a bumper 0.17 deep × 0.19 tall at clearance + 0.30; two headlamp lenses 0.30 wide × 0.125 tall at
  bonnet-nose height − 0.20; a grille 0.115 tall between them; two amber indicators 0.14 × 0.05 in the bumper;
  a front plate 0.30 × 0.15 on the bumper.
- **Tail**: the same bumper; two red tail lamps 0.34 × 0.13 at boot-lid (or belt) height − 0.24; a rear plate
  0.30 × 0.15 between them (not on an open van or a pickup: the pickup carries it on its rear bumper).
- **Flanks**: a mirror 0.11 × 0.08 × 0.07 at the base of each A pillar; a dark rub strip 0.05 tall at clearance
  + 0.42 between the wheel arches; dark door seams 14 mm wide (sedan: at x 0.96, −0.20 and −1.10, so a 1.16 m
  front door and a 0.90 m rear door); a chrome door handle 0.10 × 0.022 on each door at belt − 0.15.
- **Glass**: side windows from belt + 0.035 to roof − 0.085, a windscreen and a back light on the sloping faces.
  Material `glass_car` (`#0a0d10`, roughness 0.05, metalness 0.3): a dark tint that hides the cabin, so no
  interior is modelled. With the dome light on the glass is `glass_car_lit` (emissive `#ffc890` × 0.45), which the
  material library switches off by day (src/config/catalog.js:61-62, docs/CONTRACT.md:307-312).
- **Wheels** (src/props/vehicles.js:293-316): a tyre and one of three faces: `cap` chrome hubcap; `steel` dark steel
  disc with a small chrome centre cap; `alloy` chrome lip, dark dish, five chrome spokes.

#### 2.4.3 Colours

Factory palettes (used when the caller passes no colour):

| Type | Palette | Source |
|---|---|---|
| `sedan` (and the car of `car_lift` variant `car`) | `#8f959c` `#d9d7d0` `#b9bcc0` `#3a3e45` `#9c2320` `#24508f` `#2c5a3e` `#a89878` `#6f8aa8` `#6a1c22` `#1e2b48` `#c9bea4` `#1a1c20` `#5d6168` | src/props/vehicles.js:29-32 |
| `suv` | `#0b0c0e` (twice) `#14161a` `#1c2029` `#2a2c30` `#3a1416` | src/props/vehicles.js:33 |
| `pickup` | `#d9d7d0` `#8f1f1c` `#1b2a4a` `#2a2d33` `#16342a` `#b9bcc0` | src/props/vehicles.js:34 |
| `van` | `#d9d7d0` `#8f959c` `#1b2a4a` `#b9b4a6` `#5a1a1c`; variant `vulture` forces `#1a1c20` | src/props/vehicles.js:35, 37, 592 |
| `box_truck` (cargo box only; the cab is always `#d9d7d0`) | `#d8d6cf` `#b9b4a6` `#c9a23a` `#8a8f96` | src/props/vehicles.js:36, 698 |
| `taxi` | `#f2c21a` | src/config/look.js:130, src/props/vehicles.js:524 |
| `motorbike` (tank, tail, mudguard) | `#8f1f1c` `#14161a` `#1b2a4a` `#c9a23a` | src/props/vehicles.js:611 |
| `ipx_truck` | `#17191d` gloss black, forced | src/props/vehicles.js:625 |
| `car_on_stands` (primer) | `#6b6f73` `#7a3b2c` `#4c5055` `#8a8f96` | src/props/shop.js:9, 64 |
| `burned_car` | body `steel_rust` `#5b3a26`, charred parts `#1c1613` | src/props/vehicles.js:606, 775; src/config/catalog.js:28 |

**Effective colours on the block.** The level repaints every `sedan`, `suv`, `van`, `box_truck` and `pickup` from
its own nine-colour chart, so the factory palettes of those five types are never seen in the shipped level
(src/level/kit.js:61-62, 163-181, 598):

`#14161a` black · `#2a2d33` charcoal · `#8f959c` silver · `#d9d7d0` white · `#6e1a1c` maroon · `#1b2a4a` navy ·
`#16342a` dark green · `#b9b4a6` beige · `#c9a23a` mustard.

```
vehiclePaint(opts, name):
  if opts.color is undefined:
      seed = imul((opts.seed or 0) + 7 * len(name), 0x9e3779b1) as unsigned
      return CHART[(seed >>> 8) mod 8]            # the mustard (index 8) is never drawn by seed
  return the CHART colour nearest to opts.color   # squared distance in 8-bit RGB
```

Consequences worth knowing: Rule's SUV is asked for `#0b0c0e` and gets `#14161a` (src/level/street.js:47); the Vulture
van is asked for `#16181b` and gets `#14161a` (src/level/street.js:73); the roadblock truck is asked for `#5a5d62`
and gets `#2a2d33` (src/level/street.js:440).

#### 2.4.4 Plates and liveries (all invented)

Plates are 0.30 × 0.15 m quads: off-white `#f1efe6` with a navy `#16264f` border and number, the header
`NEW YORK` and a gold `#d9a21c` band along the bottom. The taxi plate is yellow `#f0c63a` with a navy band
(src/props/atlas.js:252-263). There are only four codes plus the taxi's (src/props/atlas.js:20-21, 341-342):

| Atlas region | Text | Carried by |
|---|---|---|
| `plate_0` | `HLS·2141` | sedan variant 0, box truck variant 0 |
| `plate_1` | `TKV·9907` | sedan variant 1, SUV variant 0, every plain van, box truck variant 1 |
| `plate_2` | `KQB·5530` | sedan variant 2, SUV variant 1, pickup variant 0, the IPX truck |
| `plate_3` | `LWG·4418` | sedan variant 3, pickup variant 1, the Vulture van |
| `plate_taxi` | `T·5K83` | every taxi (medallion `5K83`) |

The plate rule is unit-tested: three capitals, a middle dot, four digits, no code that reads as a real person's
initials, no two alike (test/props-copy.test.js:11-18). The same test bans a list of real artists, crews, gangs
and brands from every string in the source (test/props-copy.test.js:21-27).

Liveries and marks painted on vehicles:

| Vehicle | Mark | Size (m) | Where (local x, y, z) | Source |
|---|---|---|---|---|
| Taxi | door lettering `NYC TAXI`, medallion `5K83`, a ruled fare card, black on the yellow door | 0.92 × 0.37 | both front doors, centre x 0.39, y 0.65 | src/props/vehicles.js:535-538, src/props/atlas.js:344-352 |
| Taxi | black and white checker band: two rows of 16 checks, each 0.15 long × 0.035 tall | 2.40 × 0.07 | both flanks under the windows, x −1.47…0.93, y 0.93 | src/props/vehicles.js:539-542, src/props/atlas.js:363-369 |
| Taxi | roof light: lit box 0.16 × 0.40 × 0.085 (`#ffd24a` × 1.15) on a dark foot, medallion `5K83` on its front and rear faces | 0.36 × 0.075 | roof, x −0.17, top at 1.55 | src/props/vehicles.js:529-534, src/props/atlas.js:354-361 |
| Vulture van | crew stencil: a hunched vulture on a wire, bone white `#e9e4d6`, sprayed and worn | 1.15 × 0.92 | both flanks on the upper panel, centre x −1.0, y 1.64 | src/props/vehicles.js:682, src/props/atlas.js:132-199, 330-333 |
| Vulture van | oxblood stripe `#5a0f14` | 3.70 × 0.09 | both flanks, x −2.45…1.25, y 0.78 | src/props/vehicles.js:683 |
| Vulture van | marker scrawl (no letters): oxblood `#8a1820` on the right flank, bone white on the left | 0.66 × 0.29 | by the cab door, centre x 1.1, y 0.98 | src/props/vehicles.js:684, src/props/atlas.js:101-130, 335-336 |
| Box truck | spray tags `RULE` (bone `#e9e4d6`) and `HOLLIS` (gold `#f6c21a`), one per flank, fitted into 2.6 × 1.2 | up to 2.6 × 1.2 | cargo box, centre y 1.90; right flank x −1.76, left flank x −0.96; variant 0: RULE right, HOLLIS left; variant 1 swapped | src/props/vehicles.js:748-764 |
| IPX truck | see 2.4.6 | | | |

"Right flank" is local +Z (the driver's right), "left flank" local −Z. Every mark reads the right way round from
outside (src/props/kit.js:621-629).

#### 2.4.5 Vehicle sheets

**Sedan** (`sedan`, src/props/vehicles.js:513-521). A mid-size four-door three-box saloon, 4.61 × 1.85 (mirror to
mirror; 1.73 body) × 1.45, wheelbase 2.80, 0.65 m wheels. Four seed variants that differ only in wheel face and
plate: variants 0 and 2 chrome hubcaps, 1 and 3 dark steel wheels; plate = `plate_<variant>`. 13 on the block: 5 at
the avenue kerbs, 2 askew in the travel lanes, 4 in the parking lot and 2 in the shop (one on the floor between
the posts of the east lift, one raised on the west lift) (2.4.7).

**Yellow cab** (`taxi`, src/props/vehicles.js:523-545). The sedan body in taxi yellow `#f2c21a` with dark steel
wheels, the roof light, door lettering, checker band and the yellow `T·5K83` plate (2.4.4). 3 on the block: north
kerb at x 4, south kerb at x −24.6, one in the lot.

**SUV** (`suv`, src/props/vehicles.js:547-562). A full-size two-box 4×4, 4.91 × 2.00 × 1.82 (1.78 to the roof skin),
wheelbase 2.92, 0.80 m five-spoke alloys, body-colour bumpers, chrome grille, a quarter light behind the rear
door, two roof rails 2.3 m long on three feet each and chrome running boards 2.0 × 0.13. Two seed variants that
differ only in plate (`plate_<1 + variant>`). 2 on the block: a silver one in the lot and **Rule's ride**, black
(`#14161a` effective), at the south kerb beside the start, nose east (src/level/street.js:47). It is the first thing
the player sees up close: build it to hero quality.

**Pickup** (`pickup`, src/props/vehicles.js:564-587). A full-size single-cab long-bed truck, 5.32 × 2.00 × 1.78,
wheelbase 3.22, 0.78 m steel wheels, chrome bumpers and grille. The bed is 2.01 m long behind the cab (from x
−0.56), floor at 0.92, walls 0.35 high, dark liner, with a spare tyre (radius 0.33) and a timber crate 0.5 × 0.42
× 0.4 in it. Rear plate on the bumper. Colliders: body ±2.65 × ±0.96 to 1.27; cab x −0.45…0.97, z ±0.80 to 1.78
(glass). 2 on the block, both charcoal with `KQB·5530`: rear lane and parking lot.

**Panel van** (`van`, src/props/vehicles.js:589-597, 639-687). A full-size cargo van with a short sloping nose, 5.21 ×
1.96 × 2.19 (2.14 to the roof skin, a roof vent 0.5 × 0.5 on top), wheelbase 3.20, 0.72 m steel wheels, no side or
back glass behind the cab doors. Closed, the tail shows a door seam, two chrome handles and two small dark panes
0.50 × 0.36 at y 1.62. One collider, the whole body to 2.14: a van is hard cover. 10 plain vans on the block: 6
at the avenue kerbs, 2 slewed in the travel lanes, 1 in the rear lane, 1 in the lot.

**Vulture van** (`van` with `variant: 'vulture'`; doors open unless `open: false`; any van takes `open: true`)
(src/props/vehicles.js:592-593, 633, 655-686). The same van in near-black with the crew stencil, the oxblood stripe
and the scrawls (2.4.4), plate `LWG·4418`, and both rear barn doors swung open:

- each door leaf is 0.85 wide × 1.44 tall × 0.045 thick with a small pane and a dark inner panel, hinged on the
  rear corner at x −2.53, z ±0.89;
- the right (+Z) leaf stands open 1.95 rad (111.7°), the left (−Z) leaf 1.55 rad (88.8°): the right one reaches
  about 0.3 m outside the flank, the left one 0.78 m behind the tail;
- the load space is bare dark steel, 2.94 long × 1.52 wide × 1.44 high, floor at 0.60, holding two taped cartons
  (0.50 × 0.42 × 0.36 with a 0.40 × 0.36 × 0.30 on top) and a timber crate 0.70 × 0.50 × 0.34;
- the collider does not change with the doors: still the closed body box.

One on the block, slewed across the eastbound lane at (−9.4, 1.8), yaw 3.69 rad, its open tail about 3 m from
reel 1 (src/level/street.js:70-73).

**Box truck** (`box_truck`, src/props/vehicles.js:599-603, 693-768). A medium-duty conventional-cab straight truck
with a dry-freight box, 7.39 × 2.44 × 3.31:

- cab 2.9 long, 2.08 wide, 2.28 high, always white `#d9d7d0`, chrome bumper and grille, mirrors on stalks, five
  amber marker lamps on the roof;
- cargo box 4.56 long × 2.40 wide × 2.25 high (floor 1.05, roof 3.30) in the instance colour, aluminium corner
  rails, a roll-up rear door 2.24 × 2.09, two red marker lamps at the top rear corners;
- ladder frame, front axle at x 2.95, rear axle at x −2.09 with twin tyres (radius 0.44), mud flaps, a step
  bumper at 0.55, a cylindrical fuel tank (radius 0.26, 0.9 long) on the right, a battery box on the left, tail
  lamps and the plate at 0.93 under the door;
- a spray tag on each flank of the box (2.4.4). Two seed variants: plate and which flank carries which tag.

Colliders: box x −3.64…1.12, z ±1.20, 0…3.30; cab x 1.12…3.70, z ±1.06, 0…2.28. 3 on the block: mustard, stopped
dead in the westbound lane at x −19.2; beige, double-parked in the eastbound lane at x 5.85; and the roadblock.

**The "jack-knifed" truck** is the third `box_truck`: charcoal box, variant 1, standing at (41.4, 0.3) with yaw
1.05 rad (60°), so it lies diagonally across the roadway under the El at the east end with its nose toward the
north-east (src/level/street.js:440). It is the ordinary rigid truck turned: the source has no articulated vehicle and
nothing is bent or overturned. DESIGN.md calls it jack-knifed (docs/DESIGN.md:204); the code only slews it.

**Burned-out car** (`burned_car`, src/props/vehicles.js:605-608, 774-802). A sedan shell 4.38 × 1.72 × 1.30 sitting
0.125 lower on four bare rusted rims (no tyres): no glass, no lamps, no bumpers, no trim. The roof stands on six
posts; the cabin holds a charred floor, two front seat backs, a rear bench and a steering wheel; the bonnet is
sprung open 0.27 rad (15°) over a black engine bay. Body rust `#5b3a26`, everything charred `#1c1613`. Colliders:
body ±2.25 × ±0.88 to 0.96; a bullet-only box over the cabin (x −1.30…0.65, z ±0.72, 0.96…1.30) so rounds stop
on the roof frame while bodies and the nav grid ignore it. Anchor `smolder` over the engine bay at (1.5, 1.0, 0).
One on the block, in the vacant lot at (−11.2, 18.6) on a scorch mark 5.5 × 4.2 m (src/level/yards.js:296-298).

**Raised car and lift** (`car_lift`, src/props/shop.js:28-61). A two-post lift: posts 0.30 × 0.26 × 3.46 at local
z ±1.4 in blue `#1a4a8a` on base plates, an overhead beam at 3.52, carriages with four swing arms and round pads
(radius 0.07), a power unit on the +Z post. Arms are up by default: pad tops 2.14 m off the floor, so a car placed
with its wheels 1.95 m up (`LIFT_HEIGHT`) rests on them. Variant `down` lowers the arms to 0.16; variant `car`
brings its own raised sedan. Colliders: the two posts, 0.40 × 0.32 × 3.50 each. The shipped shop does not use the
`car` variant: the west lift at (−19.2, −17.3) has a separate dark-green sedan placed at y 1.95 with `noNav`
(colliders 1.95…3.03 body and 3.03…3.40 cabin, so a standing player walks under it), and the east lift at (−1.3,
−19.6) has its arms up and a white sedan standing on the floor between the posts (src/level/shop.js:253-256).

**Stripped car on stands** (`car_on_stands`, src/props/shop.js:63-85). A sedan shell 4.38 × 1.72 × 1.60 raised 0.15
on four jack stands (0.35 tall, at x ±1.0, z ±0.66): no doors (the openings are cut right through the body), no
glass, no wheels (rusty brake discs on the hubs), no bumpers or lamps, in flat primer (the shipped one is red
oxide `#7a3b2c`), bare floor, gutted dash, open engine bay with one galvanised lump in it. Colliders: body ±2.25
× ±0.88 to 1.23; cabin x −1.26…0.64, z ±0.74, 1.23…1.60, surface `car`. One in the shop at (−12.2, −15.4).

**Motorbike** (`motorbike`, src/props/vehicles.js:610-613, 808-852). A standard naked motorcycle 1.94 long × 1.10
high, 0.62 m wheels 1.32 apart, chrome fork, twin chrome exhausts, round chrome headlamp, painted tank, tail and
front mudguard, black seat, handlebars 0.5 wide with mirrors. It leans 0.12 rad (7°) toward local −Z on its side
stand. (The stand is modelled on the +Z side, opposite the lean: a slip in the source, not something to copy.)
Collider ±0.98 × ±0.30 to 0.95. 3 on the block.

**Food cart** (`food_cart`, src/props/vehicles.js:615-620, 858-917). A stainless hot-dog cart: body 1.70 × 0.86 × 0.72
on two 0.40 m wheels with a jockey leg and a tow bar toward +X, chrome worktop at 1.0 with a steam pan (lid ajar),
a griddle, three squeeze bottles (red, yellow, brown) and a napkin box, a glass sneeze guard on the +Z side, a
menu board on both long sides, and an eight-panel umbrella in red `#c2261e` and yellow `#e9c21a`, 2.16 × 1.32 m
across at rim height 1.90, apex 2.23. A small work lamp under the umbrella when lit. Menu board text: `HOT DOGS`,
`PRETZELS · COLD SODA`, and a price list `HOT DOG 1.50`, `SAUSAGE 2.50`, `PRETZEL 1.25`, `SODA 1.00`
(src/props/atlas.js:586-597). Colliders: body x −0.98…0.78, z ±0.50 to 1.25; umbrella 1.85…2.25 bullet-only. Anchors
`steam` (0.28, 1.1, 0.12) and `propane` (0.95, 0, −0.25). One on the block, on the north sidewalk at (−5.7, −8.3)
with two propane tanks beside it.

#### 2.4.6 The IPX armoured vault truck

`ipx_truck` (src/props/vehicles.js:622-630, 923-1159): the extraction point. A cash-in-transit style armoured truck on
a medium-duty chassis, one welded shell: a short sloped nose, an upright split windscreen, and a vault body a hand
taller than the cab. Gloss black, a gold waist band, the IPX wordmark in white.

| Dimension | Value (m) | Source (src/props/vehicles.js) |
|---|---|---|
| Length / shell width / with mirrors | 6.80 / 2.34 / 2.48 | 924-925, 1039 |
| Vault roof / cab roof | 2.86 / 2.58 (roof hatch and vent reach 2.96) | 926-927, 1055-1056 |
| Cab ends, vault begins | x 0.55 | 948 |
| Vault floor / door sill | 1.02 | 928 |
| Base of the cab glass | 1.72 | 929 |
| Flanks | flat plate, parallel from the tail to x 1.30, then tapering 7 % to the nose | 952, 983-985 |
| Wheels | radius 0.50, width 0.30, dark steel; front axle x 2.05, rear axle x −1.75 (wheelbase 3.80), twin rear tyres | 941, 946-947, 997-1002 |
| Ground clearance | 0.46 | 942 |
| Windscreen | two narrow panes either side of a centre post, y 1.84…2.42 | 1005-1016, 1023 |
| Cab door windows | slots x 0.82…1.50, y 1.90…2.36 | 1018-1020 |
| Rear doors | two leaves 0.89 wide × 1.62 tall × 0.07 thick, hinged at x −3.30, z ±0.91, spanning y 1.05…2.67 | 930, 1088-1093 |
| Door swing / time | 1.9 rad (108.9°) each, outward; 1.1 s | 931-932 |
| Hazard period | 1.1 s, lit for the first half | 933, 1153 |
| Vault interior | 3.58 long × 1.80 wide × 1.56 high (x −3.23…0.35, y 1.02…2.58), galvanised lining | 1075-1079 |
| Colliders | vault x −3.40…0.55, z ±1.17, 0…2.86; cab x 0.55…3.40, z ±1.17, 0…2.58; surface `car` | 1118-1119 |

Parts list (same source, lines 996-1121):

- **Nose**: a dark steel ram bumper 0.30 tall at y 0.68; a dark grille panel 1.0 × 0.34 with four galvanised
  bars; two headlamps 0.24 × 0.17 at z ±0.68, **switched on** (the truck is idling); amber indicators at z ±0.90.
- **Roof**: five amber clearance lamps over the windscreen; a square hatch 0.8 × 0.8 and a small vent on the
  vault roof; two amber marker lamps per flank under the vault roof line (x −3.0 and 0.25, y 2.70).
- **Flanks**: cab door outline, chrome handle, a galvanised step 0.72 × 0.20 at 0.74; two dark gun ports per
  flank on the vault (radius 0.06, x −0.2 and −2.3, y 1.62); a dark mirror on each cab door.
- **Tail**: a step bumper at 0.68 with yellow and black hazard stripes on its rear face (2.14 × 0.10) and a
  galvanised tread; red tail lamps 0.12 × 0.20 at y 1.30; door jambs and header; a lamp over the doors (a white
  strip 0.30 wide at y 2.63); the plate `KQB·5530` right of centre at y 0.86.
- **Each rear door leaf**: a painted panel with a dark inset, the gold band carried across it at y 1.36, a small
  armoured-glass port 0.34 × 0.22 at y 2.20, a chrome lock bar 0.90 tall with a round boss by the centre seam,
  two hinges on the outer edge.
- **Vault** (seen only once the doors swing): three shelves per wall at y 1.45, 1.90 and 2.30 on three uprights
  (racks for the reels), the IPX mark on the bulkhead, a ceiling light panel 1.6 × 0.5.

Livery and wordmark placement:

| Mark | Art (atlas region) | Size (m) | Centre (x, y, z) | Faces | Source |
|---|---|---|---|---|---|
| Flank livery | `ipx_side`: the IPX lozenge, a short gold bar, then `IPX.EXCHANGE`; all white `#f4f2ec` except the bar | 3.50 × 0.875 | (−1.42, 2.10, ±1.176) | outward on both vault flanks | src/props/vehicles.js:1031, src/props/atlas.js:274-279 |
| Bonnet | `ipx_mark`: the lozenge alone | 0.80 × 0.33 | (2.50, 1.417, 0) | up, tipped 9° forward; reads upright from in front of the truck | src/props/vehicles.js:1042 |
| Right rear door (+Z leaf) | `ipx_mark` | 0.62 × 0.26 | (−3.357, 1.75, 0.46) | rearward | src/props/vehicles.js:1100 |
| Left rear door (−Z leaf) | `ipx_url`: `IPX.EXCHANGE` | 0.74 × 0.092 | (−3.357, 1.75, −0.46) | rearward | src/props/vehicles.js:1101 |
| Vault bulkhead (inside) | `ipx_mark` | 1.10 × 0.46 | (0.349, 1.90, 0) | rearward | src/props/vehicles.js:1085 |
| Gold waist band | material `gold` `#e7b53a`, 0.11 tall | vault flanks x −3.25…0.46; cab flanks x 0.62…1.82; across both rear doors | y 1.36 | | src/props/vehicles.js:1029-1030, 1095 |

On the flank art the lozenge sits at the left end of the picture and the address runs to the right. Because the
picture reads left to right from outside on both sides, the lozenge is toward the **tail** on the right flank and
toward the **cab** on the left flank. Within the 3.50 × 0.875 m panel the lozenge is 0.72 m tall, centred 0.85 m
from the picture's left edge; the gold bar is 0.27 m tall; the address is set in bold capitals at a type size of 0.18 m with
wide letter spacing (src/props/atlas.js:274-279: 210, 250, 80 and 54 pixels on a 1024 × 256 sheet).

The wordmark itself (`mats.drawIPX`, src/mats/signs.js:46-67): the letters `IPX` in a heavy italic grotesque (the UI
face, weight 800 italic, letter spacing 0.05 em, type size 0.58 × the mark's height) inside a thin lozenge: a
stadium outline as tall as the mark, line width 6.5 % of the height, 0.86 × height wider than the letters. It is a
typeset stand-in until the real logo is supplied (docs/DESIGN.md:245-246). The only IPX marks allowed are `IPX`
and `IPX.EXCHANGE`; no slogan (src/config/brand.js:14-18, docs/DESIGN.md:220-221).

Lamp hints and anchors of the truck are in 2.10. State behaviour is in 3.4.

#### 2.4.7 Every vehicle on the block

Web position (x, z; y = 0 unless given) and yaw in radians as written in the level; Unreal location in cm and yaw
in degrees by the rule in 4.1. "Dome" is the seed-picked interior light (night only). Sources: src/level/street.js:
38-53, 62-66, 73, 85-86, 101-102, 440; src/level/yards.js:175, 298, 378-379, 442-449, 469; src/level/shop.js:254-257.

| # | Type | Web x, z | Web yaw | Unreal X, Y, Z | Unreal yaw | Paint | Variant | Plate | Dome | Zone |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `sedan` | −19.2, −17.3, y 1.95 | 1.57 | −1920, −1730, 195 | −90 | #16342a | v2 cap | KQB·5530 | off | shop |
| 2 | `sedan` | −1.3, −19.5 | −1.57 | −130, −1950, 0 | 90 | #d9d7d0 | v1 steel | TKV·9907 | off | shop |
| 3 | `sedan` | 24.95, 15.5 | 3.14 | 2495, 1550, 0 | 180 | #16342a | v2 cap | KQB·5530 | off | lot |
| 4 | `sedan` | 36.5, 23.6 | 3.14 | 3650, 2360, 0 | 180 | #d9d7d0 | v0 cap | HLS·2141 | off | lot |
| 5 | `sedan` | 24.5, 31.6 | −1.57 | 2450, 3160, 0 | 90 | #14161a | v3 steel | LWG·4418 | off | lot |
| 6 | `sedan` | 29.7, 31.55 | 1.57 | 2970, 3155, 0 | −90 | #d9d7d0 | v1 steel | TKV·9907 | off | lot |
| 7 | `sedan` | −27.4, −5.98 | 3.14 | −2740, −598, 0 | 180 | #6e1a1c | v1 steel | TKV·9907 | off | avenue |
| 8 | `sedan` | 13.6, −5.98 | 3.14 | 1360, −598, 0 | 180 | #2a2d33 | v0 cap | HLS·2141 | off | avenue |
| 9 | `sedan` | 31.4, −5.98 | 3.14 | 3140, −598, 0 | 180 | #14161a | v3 steel | LWG·4418 | off | lot |
| 10 | `sedan` | 4.6, 5.98 | 0 | 460, 598, 0 | 0 | #1b2a4a | v2 cap | KQB·5530 | on | avenue |
| 11 | `sedan` | 39.6, 5.98 | 0 | 3960, 598, 0 | 0 | #d9d7d0 | v0 cap | HLS·2141 | off | lot |
| 12 | `sedan` | −35.2, −2.3 | 0.42 | −3520, −230, 0 | −24.1 | #2a2d33 | v0 cap | HLS·2141 | off | west |
| 13 | `sedan` | 33.8, 2.3 | 0.3 | 3380, 230, 0 | −17.2 | #6e1a1c | v1 steel | TKV·9907 | off | lot |
| 14 | `taxi` | 36.5, 15.8 | 3.14 | 3650, 1580, 0 | 180 | #f2c21a | — | T·5K83 | on | lot |
| 15 | `taxi` | 4, −5.98 | 3.14 | 400, −598, 0 | 180 | #f2c21a | — | T·5K83 | off | avenue |
| 16 | `taxi` | −24.6, 5.98 | 0 | −2460, 598, 0 | 0 | #f2c21a | — | T·5K83 | on | avenue |
| 17 | `suv` | 25.05, 18.1 | 3.14 | 2505, 1810, 0 | 180 | #8f959c | v0 | TKV·9907 | off | lot |
| 18 | `suv` | −40.5, 5.98 | 0 | −4050, 598, 0 | 0 | #14161a | v0 | TKV·9907 | off | west |
| 19 | `pickup` | 17.4, 29.85 | 3.14 | 1740, 2985, 0 | 180 | #2a2d33 | v0 | KQB·5530 | on | avenue |
| 20 | `pickup` | 25.2, 23.3 | 0 | 2520, 2330, 0 | 0 | #2a2d33 | v0 | KQB·5530 | on | lot |
| 21 | `van` | −7.6, 29.6 | 0.04 | −760, 2960, 0 | −2.3 | #b9b4a6 | — | TKV·9907 | off | avenue |
| 22 | `van` | 36.6, 18.4 | 0 | 3660, 1840, 0 | 0 | #1b2a4a | — | TKV·9907 | off | lot |
| 23 | `van` | −38.2, −5.98 | 3.14 | −3820, −598, 0 | 180 | #1b2a4a | — | TKV·9907 | off | west |
| 24 | `van` | −20.2, −5.98 | 3.14 | −2020, −598, 0 | 180 | #d9d7d0 | — | TKV·9907 | off | avenue |
| 25 | `van` | 19.4, −5.98 | 3.14 | 1940, −598, 0 | 180 | #8f959c | — | TKV·9907 | off | avenue |
| 26 | `van` | −18.9, 5.98 | 0 | −1890, 598, 0 | 0 | #8f959c | — | TKV·9907 | off | avenue |
| 27 | `van` | −3, 5.98 | 0 | −300, 598, 0 | 0 | #14161a | — | TKV·9907 | off | avenue |
| 28 | `van` | 13.4, 5.98 | 0 | 1340, 598, 0 | 0 | #6e1a1c | — | TKV·9907 | off | avenue |
| 29 | `van` | −9.4, 1.8 | 3.69 | −940, 180, 0 | 148.5 | #14161a | vulture, open | LWG·4418 | off | avenue |
| 30 | `van` | 16.3, −2.6 | 0.55 | 1630, −260, 0 | −31.5 | #2a2d33 | — | TKV·9907 | off | avenue |
| 31 | `van` | 36.9, −2.5 | 3.24 | 3690, −250, 0 | 174.2 | #2a2d33 | — | TKV·9907 | off | lot |
| 32 | `box_truck` | 41.4, 0.3 | 1.05 | 4140, 30, 0 | −60.2 | #2a2d33 | v1 | TKV·9907 | off | lot |
| 33 | `box_truck` | −19.2, −2.4 | −0.28 | −1920, −240, 0 | 16 | #c9a23a | v0 | HLS·2141 | off | avenue |
| 34 | `box_truck` | 5.85, 2.35 | 0.28 | 585, 235, 0 | −16 | #b9b4a6 | v0 | HLS·2141 | off | avenue |
| 35 | `burned_car` | −11.2, 18.6 | 0.9 | −1120, 1860, 0 | −51.6 | (rust) | — | — | off | avenue |
| 36 | `car_on_stands` | −12.2, −15.4 | 1.69 | −1220, −1540, 0 | −96.9 | #7a3b2c | — | — | off | shop |
| 37 | `ipx_truck` | 41.3, 29.7 | 0 | 4130, 2970, 0 | 0 | #17191d | — | KQB·5530 | off | lot |
| 38 | `motorbike` | 31.3, −22.9 | 1.25 | 3130, −2290, 0 | −71.6 | #1b2a4a | — | — | off | lot |
| 39 | `motorbike` | −5.7, −6.35 | 0.08 | −570, −635, 0 | −4.6 | #14161a | — | — | off | avenue |
| 40 | `motorbike` | −14.6, 3.6 | 0.5 | −1460, 360, 0 | −28.6 | #1b2a4a | — | — | off | avenue |

Rows 1 and 2 are the two shop cars (1 is the raised one). Row 18 is Rule's SUV. Row 29 is the Vulture van. Row 32
is the roadblock truck. Row 37 is the extraction truck: DESIGN.md puts it "near (40, 0, 27)"
(docs/DESIGN.md:203); the code stands it at (41.3, 29.7), nose east, and centres the extraction zone (radius 2.5)
at (35.9, 29.7), 2.0 m behind its rear face (src/level/data.js:17-18, src/config/flow.js:50-55).

### 2.5 Gameplay props

#### 2.5.1 Master reel case (`master_case`)

The objective. Three on the block, one per reel (src/level.js:98-102, src/level/data.js:10-14): the avenue (−4, 1) yaw
0.35; the shop floor (−9.5, −21.5) yaw −0.5; centre court of the Cage (35.25, −22.5) yaw 1.1. (DESIGN.md says
"near (−9, −21)" and "near (33, −22)" for reels 2 and 3, docs/DESIGN.md:191, 201; the code positions win.)

It is one assembly on a 0.9 × 0.6 footprint (src/props/gameplay.js:24-38, 66-179): a flight case strapped on a hand
truck, its lid thrown open to show the gold reel, a boombox on the ground beside it, and a beacon on a mast.

| Part | Description and dimensions (m, local x / y / z) | Source (src/props/gameplay.js) |
|---|---|---|
| Hand truck | steel sack truck loaded from the left (−X): toe plate 0.30 × 0.30, two tube rails (radius 0.013) rising to 0.86 and bent into a handle at 0.96, two cross bars, an axle with two 0.18 m wheels | 75-86 |
| Road case | black panels, 16 mm aluminium edging, 30 mm chrome ball corners; body 0.42 wide (x) × 0.32 deep (z) × 0.50 tall on the 0.03 toe plate, centred at x −0.19; two chrome latches on the front, a recessed handle on the +X side, dark foam inside | 50-64, 88-93 |
| IPX tag | a luggage-style label on the front: off-white card 0.20 × 0.10 with the IPX lozenge, the word `TRACKER` and a barcode | 94; src/props/atlas.js:289-303 |
| Tracker | a dark unit 0.11 × 0.065 × 0.03 clipped to the front at y 0.32 with a lit LCD 0.084 × 0.035 (`IPX` in gold italic and four signal bars on near-black), a green LED `#3dff7a` and a 0.17 m whip antenna | 95-99, 167; src/props/atlas.js:322-326 |
| Lid | 0.42 × 0.32 × 0.12, same shell, hinged along the back edge at (x −0.19, y 0.53, z −0.16); IPX lozenge 0.30 × 0.125 on top; inside: foam, a second lozenge 0.26 × 0.108 and a dark track 0.36 × 0.045 for the progress bar. Stands open 1.66 rad (95°) while the reel is there | 104-112, 32 |
| Progress bar | a gold strip `#f6c21a` × 3.2 glow, 0.34 × 0.03 × 0.006, inside the lid, growing from its left end (scale x = progress) | 114-116, 196 |
| Reel | a gold reel 0.27 across and 0.038 thick (two flanges and a hub, brown tape pack of radius 0.118 between them), tilted 0.7 rad (40°) and propped on its tape box (0.29 × 0.29 × 0.04 cardboard). Flange art: three wide spokes, gold on dark. Box label: `MASTER REEL`, `MURDER INC.`, `REEL __ / 3`, `SPEED 30 IPS`, `TAPE 2 IN · 24 TRK`, a small IPX lozenge | 118-127; src/props/atlas.js:773-831 |
| Boombox | 0.60 wide × 0.19 deep × 0.28 tall, carry handle to 0.34, chrome top strip with four keys, an aerial; face: two speakers, cassette door, tuner scale. Stands at (0.16, 0, −0.04) turned 1.15 rad so its face looks toward +X and a little +Z. A five-segment level meter on the face (three green `#3dff7a`, two orange-red `#ff5a2a`) | 37, 101-102, 168-170; src/props/clutter.js:71-80; src/props/atlas.js:833-858 |
| Beacon | a thin dark mast clamped to the hand-truck handle, from 0.90 to 1.22, with a base disc and a domed gold lens 0.104 across, top at 1.346: it clears waist-high cover. The mast, clamp and base disc are built into the reel's group, so they vanish with the reel | 119-136 |
| Light shaft | a six-sided cone of additive gold light from y 1.34 to 7.34 (6 m), radius 0.05 at the bottom and 0.14 at the top, fading out upward as (1 − t)^1.6 | 34, 137-146 |
| Ground pool | an additive gold disc of radius 1.0 at y 0.02 centred 0.05 toward −X: brightness 0.5 at the centre, 0.32 at radius 0.45, 0 at the rim | 147-163 |

Colours: beacon, shaft, pool and bar are `palette.beacon` `#f6c21a` (src/config/look.js:123). The reel is the
catalogue `gold` `#e7b53a` (roughness 0.25, metalness 1). Everything else is folded into one matte paint
(src/props/gameplay.js:326).

Colliders (src/props/gameplay.js:173-175): case and hand truck x −0.45…0.03, z ±0.30, 0…0.66, `metal`; boombox
x 0.03…0.45, z ±0.30, 0…0.35, `rubber`, bullets only; and a player-only box over the boombox up to 0.66 so the
player cannot stand in the gap. Anchors (176-178): `boombox` (0.24, 0.16, −0.04), `beacon` (−0.422, 1.30, 0),
`reel` (−0.19, 0.63, 0).

States and timing: 3.3. Interaction numbers (the game's, not the prop's): reach 2.2 m horizontal and 2.5 m
vertical, facing within a dot product of 0.45 unless closer than 0.9 m, hold 2.4 s, progress drains 1.6 per
second when the hold breaks (src/config/flow.js:40-48).

#### 2.5.2 Propane tank and welding rack

Explosive cover. The level only lists them (src/level/data.js:119-141: 14 propane, 7 racks; where they stand: 4.4); the
explosives module builds one template of each with `seed: 1` and draws every item from it (src/explosives.js:78-88).

| | Propane tank (`propane_tank`) | Welding rack (`welding_rack`) |
|---|---|---|
| Real object | a steel LPG cylinder with a guard collar, the kind beside a food cart | an oxy-acetylene bottle cart: two tall oxygen cylinders and one acetylene cylinder chained on a wheel-less rack |
| Model size | 0.30 across × 0.585 tall | 0.905 × 0.53 × 1.52 |
| Parts | dark steel foot ring (radius 0.125, 0.045 tall); white body `#e6e4dc` of radius 0.152 from 0.03 to 0.33; red shoulder `#b3261e` domed to 0.47; a white collar of two arcs (radius 0.10, y 0.45…0.585) with the hand holes open at the sides; brass valve `#b58a3a`; red handwheel; a flammable-gas diamond 0.13 × 0.13 (white flame and the class number 2 on red `#d3281f`) front and back at y 0.215 | steel base plate 0.90 × 0.50 × 0.04 `#2a2d31`; a back frame of two posts (to 1.34) and three rails; a chain bar across the front at 0.82; two oxygen cylinders in dark green `#2f6b4f` (radius 0.115, 1.42 tall) at x −0.28 and 0; one acetylene cylinder in maroon `#7a1a1a` (radius 0.14, 1.12 tall) at x 0.28; brass valves with steel caps; two brass regulators with two white gauges each; a red and a green hose looped over the frame; a brass torch hung on it; a placard 0.36 × 0.25 on a white board: `DANGER`, `FLAMMABLE GAS`, `NO SMOKING`, `NO OPEN FLAME` |
| Source | src/props/gameplay.js:331-360; src/props/atlas.js:702-731 | src/props/gameplay.js:317-321, 362-403; src/props/atlas.js:733-740 |
| Builder collider (unused by the game) | ±0.16 × ±0.16 × 0.60 | ±0.45 × ±0.25 × 1.50 |
| **Effective collider** | axis-aligned box around the rotated 0.32 × 0.32 footprint, 0.60 tall, surface `metal` | axis-aligned box around the rotated 0.90 × 0.50 footprint, **1.60** tall, surface `metal` |
| `jet` anchor | valve, (0, 0.52, 0.07), direction (0, 0.58, 0.81) | acetylene regulator, (0.28, 1.2, 0.03), direction (−0.18, 0.68, 0.71) |
| Lit look | the same mesh with a heat glow: emissive `#b8400f` × 0.6 | the same |
| Own flame (only when fx is stubbed) | additive teardrop `#ffa040`, 0.75 long, 0.07 girth, at the valve | 0.90 long, 0.08 girth |
| Gone look | a scorched, tilted foot ring and one plate shard, soot `#0c0b0a` | a scorched base plate and two bent posts |
| Hit points / fuse / blast radius / damage | 50 / 1.6 s / 6.5 m / 170 | 70 / 1.1 s / 7.5 m / 210 |
| Blast "size" (chain reach 2.2 + 1.6 × size) | 1.9 (5.24 m) | 2.3 (5.88 m) |
| Flame jet scale | 0.9 | 1.2 |

Rule sources: src/explosives.js:19-39 (`KINDS`, `POP_FUSE` 0.06 s, player takes × 0.5, an enemy round always counts
9, shake reach 28 m, alert radius 60 m, rattle 0.035 rad, hiss from volume 0.25); effective collider
src/explosives.js:176-199, 272-281; colours src/props/gameplay.js:255-261; hot paint src/props/materials.js:122-131. The full
damage, falloff and chain rules are in `02-weapons-combat.md` (sections 2.9 and 2.10); section 3.5 here gives the
part the prop shows.

#### 2.5.3 Resupply items

There are none. In Hold the Block the "resupply" after a cleared wave is applied directly to the player: +90
Chopper reserve rounds (cap 240), +35 health, and every explosive restored after each even wave. No crate, bag or
pickup is spawned, although the radio line says "Resupply at your feet" (src/config/flow.js:163-168, src/game.js:699-701,
src/config/text.js:148). Whether the rebuild shows a physical resupply drop is an open question (section 6).

### 2.6 Street furniture

Everything here faces local +Z unless noted. Line numbers in the first column are in `src/props/street.js`. Colliders are in Appendix B.

| id | The real object, parts and dimensions (m) | Colours, text | Variants |
|---|---|---|---|
| `jersey_barrier` (102-114) | precast concrete safety barrier, 3.0 long: 0.60 wide at the foot, 0.33 wide at y 0.33, 0.17 wide at the top (0.81); two fork-lift slots 0.34 × 0.07 at x ±0.8; 2 cm chamfers | concrete | 0 plain; 1 a black marker scrawl 0.8 × 0.34 on the +Z slope; 2 the remains of an orange and white hazard stripe 2.6 × 0.2 |
| `traffic_barrel` (116-129) | channelizer drum: black rubber base ring (radius 0.30), body tapering from radius 0.27 to 0.205, top with a moulded handle at 1.0 | orange `#e8641b` with two white bands (0.30…0.50 and 0.68…0.84) | none |
| `traffic_cone` (131-138) | 0.36 square foot, cone to 0.70 | orange, white collar 0.30…0.48 | none; no collision |
| `barricade` (140-156) | sawhorse barricade: two A-frames, two boards 2.4 long (0.20 tall at y 0.9, 0.14 at 0.5), an amber flasher on one end (steady glow `#ff8a1a` × 1.6) | white frames; boards striped orange and white on both faces | none |
| `dumpster` (158-180) | rear-load steel hopper 1.8 × 1.03 body with a sloping front, rim at 1.16, three ribs, fork pockets on both ends, four casters, two dark plastic lids (one shut, one thrown back with a bag showing) | green `#1f5a3a`; stencil `HOLLIS CARTING` / `718 · 555 · 0144` | 1 adds a white scrawl |
| `trash_can` (182-194) | city wire litter basket: mesh sides flaring from radius 0.23 to 0.285, galvanised rim and base, black liner with litter heaped at the top | galvanised | none |
| `trash_bags` (196-213) | a pile of five tied refuse sacks, each about 0.5 across; the fifth sits on the others | black `#0b0b0c`, one pale grey `#c9c9c2` | 3 piles |
| `mailbox` (215-229) | street collection box: barrel-topped body 0.52 × 0.48, top at 1.20, four legs 0.27 tall, pull-down door with a chrome handle | blue `#1f4f9a`; label `MAIL` (white on navy) | 1 adds a scrawl on the +X side |
| `newspaper_box` (231-245) | coin newspaper rack: box 0.46 × 0.40 × 0.60 on a pedestal, glazed door showing the front page, coin mechanism, chrome pull | one of `#b3261e` `#1f4f9a` `#e9b21a` `#1f5a3a` `#d9d7d0`; paper: `QUEENS NIGHT LEDGER`, headline `THREE REELS GONE` | none |
| `hydrant` (34-45, 247-252) | fire hydrant 0.75 tall: barrel radius 0.10 on a flange, domed bonnet with operating nut, two side nozzles and a larger front nozzle at y 0.47, galvanised caps | red `#b3261e` | none |
| `hydrant_open` (254-290) | the same with the front cap off and lying on the ground, a dark open mouth, a parabolic jet of water toward +Z landing 2.8 m out, and two wet patches (radius 0.9 at z 0.3, radius 1.3 at z 2.7) | red; jet additive `#cfe4ff` | `spray: false` omits the jet mesh |
| `phone_booth` (292-322) | kerbside pay-phone kiosk: steel back 0.86 × 1.94, two side wings (steel to 0.92, glass above), base plate, a head box 0.9 × 0.9 × 0.22 at the top with lit signs on three faces and a soffit light; inside: the phone 0.36 × 0.52 × 0.13 with keypad, handset and cord, a shelf, stickers | galvanised and dark iron; signs `PHONE`; coin plate `25¢` | 1 adds an oxblood scrawl on the +X wing; `lit: false` |
| `bus_shelter` (324-357) | 3.6 × 1.5 shelter: four posts, shallow roof tray at 2.44, glass back in two panes 1.64 × 1.86, a half pane at the +X end, a lit advertising box 1.26 wide closing the −X end, a timber bench 1.9 long at 0.47, a bus-stop flag at the front +X corner, a light strip under the roof | dark iron; ad: the **IPX one-sheet** (2.11) on both faces, 1.14 × 1.72; flag `BUS STOP` / `NO STANDING` | `lit: false` |
| `street_lamp` (359-377) | octagonal tapered steel pole 7.2 tall on a transformer base, a davit arm reaching 1.86 toward +Z with a brace, a cobra head 0.74 long at z 2.16, lens at y 7.7 | galvanised; lens glow sodium `#ffb45e` × 4.5 | 1 adds a sticker patch at 1.5 m; `on: false` dark lens, no lamp hint |
| `traffic_light` (379-433) | pole 5.5 tall, mast arm reaching 3.25 toward +Z at y 5.72, a yellow three-lamp head 0.34 × 0.34 × 1.02 hung at z 3.05 with lenses (radius 0.10) and visors on both ±X faces, a pedestrian head 0.36 × 0.36 on the pole at y 2.7 facing +Z | dark iron pole, yellow head; red `#ff2a1a`, amber `#ffb020`, green `#30ff8a`; orange hand, white walking figure | none (cycle in 3.6); never placed |
| `parking_meter` (435-444) | single-head meter: post to 1.04, head 0.18 across to 1.30, dial on both faces | galvanised post, dark head; `1 HR`, `25¢` | none |
| `bench` (446-463) | park bench 1.76 long: three cast-iron supports, four seat slats at 0.455, three back slats to 0.84, arm rests at the ends | dark iron, timber | none |
| `planter` (465-489) | tapered concrete tub 1.0 square at the foot, 1.2 at the lip (0.60), soil, a low hedge of five clumps to 0.80 | concrete, dark green | 2 hedges |
| `tree` (491-524) | street tree 5.7…5.9 tall: leaning trunk (radius 0.13 → 0.085) forking at 2.7, three boughs, four leaf masses (crown about 4.6 wide from 3 m up), a 0.58 square pit with a steel guard 0.55 high | bark `#6d5236`, leaves `#1f3322` | 3 trees |
| `bollard` (526-534) | steel pipe bollard, radius 0.085, 1.0 tall, domed cap, base flange | yellow `#f2c21a` with a black band 0.70…0.80 | none |
| `sign_post` (536-560) | steel channel post 2.8 tall with one sign: `nopark` 0.32 × 0.44, `bus` 0.32 × 0.44, `oneway` 0.58 × 0.18, `stop` an octagon 0.52 across, or `street`: a green blade 0.60 × 0.17 at 2.7 lettered on both faces | `NO PARKING ANYTIME` red on white; `BUS STOP NO STANDING`; `ONE WAY`; `STOP`; blade default `JAMAICA AV` | seed picks nopark / bus / oneway when no variant is asked; never placed |
| `fence_panel`, `fence_tall` (78-99, 563-564) | chain-link panel 3.0 wide, 2.4 or 4.0 high: two posts, top rail, bottom wire (tall: a mid rail at 2.0 and a centre post), mesh | galvanised; `scrim` variant adds a dark green `#1d3b2a` screen on the +Z side, to 2.1 m on the low panel and 2.3 m on the tall one | `scrim`; never placed (the level builds its fences itself) |
| `manhole` (566-579) | cast-iron cover, radius 0.405, in a concrete collar of radius 0.45, with two raised rings and twelve lugs | dark iron | none; no collision; anchor `steam` |

### 2.7 Loose cover and clutter

Line numbers in the first column are in `src/props/clutter.js`.

| id | The real object, parts and dimensions (m) | Colours, text | Variants |
|---|---|---|---|
| `milk_crates` (17-48, 83-103) | a thrown-down stack of dairy crates, each 0.33 × 0.33 × 0.28 with lattice sides and a solid rim: four on the ground, three on them, one or two on top (0.85 high) | each crate one of `#1f4f9a` `#b3261e` `#202326` `#1f5a3a` | 3 stacks |
| `pallet` (51-61, 105-110) | timber pallet 1.2 × 1.0 × 0.144: three 0.09 bearers, seven top boards, three bottom boards | timber | none; no collision in the level |
| `pallet_stack` (112-121) | eight pallets stacked to 1.15, each a little out of line | timber | 2 stacks |
| `crate_wood` (123-142) | plywood shipping crate 1.04 × 0.84 × 0.90 on two skids, corner posts, top and bottom frames, a diagonal brace on both long sides, a lid | plywood; stencil `FRAGILE`, `HANDLE WITH CARE`, `LOT 0214 · QNS`, an up arrow | 1 adds the Vulture stencil 0.5 × 0.4 on the +X end |
| `cardboard_boxes` (144-172) | five taped cartons, the largest 0.52 × 0.44 × 0.38, two of them stacked, the top one open with its flaps up (0.77 high) | cardboard, tape `#cbb892`; print `THIS SIDE UP`, a shipping label | 1 is mirrored |
| `shopping_cart` (174-213) | supermarket trolley 0.91 long, 0.52 wide: wire basket flaring to the top (0.93), child-seat flap, lower tray, four castors, handle at 1.0 | galvanised wire, red handle `#b3261e` | `tipped`: lying on its side |
| `mattress` (215-225) | a dumped mattress 1.88 × 0.93 × 0.20 lying flat | striped ticking (blue on grey-beige `#b9b3a2`), stained | 1 is tilted 2°; no collision |
| `tire_stack` (63-68, 227-236) | four car tyres stacked to 0.97, each 0.77 across with a 0.245 section | black | 2 stacks |
| `oil_drum` (238-256) | 55-gallon steel drum, 0.58 across × 0.90, two rolling hoops, two bungs in the top | one of `#1f4f9a` `#202326` `#2f5a3a` `#6b4a2e` `#8d949a`; label on variant 0: `MOTOR OIL`, `10W-40`, `55 GAL · 208 L` | 2 (with and without label) |
| `sandbags` (258-277) | a sandbag wall 1.95 long: eleven bags in three courses (4, 3, 4), each 0.55 × 0.59 × 0.335, 0.90 high | hessian `#8f7f5f` | 2 walls |
| `generator` (279-306) | skid-mounted diesel generator in a weather enclosure 2.04 × 0.94 × 1.06, louvres on the radiator end and both flanks, doors with recessed handles, a gauge panel, an exhaust stack with a rain cap, lifting eye, filler | yellow `#f2c21a`; label `DANGER`, `HIGH VOLTAGE`, `60 kW · 480 V` | none; anchor `exhaust` |
| `floodlight_stand` (308-336) | tripod work light: telescopic mast to 2.0, a cross bar 0.84 wide with two halogen heads 0.34 × 0.25 aimed forward and 18° down, a trailing cable | dark stand, yellow heads; lens glow `#fff1d0` × 5 | `on: false` |
| `porta_potty` (338-359) | portable toilet 1.12 square × 1.96 on a 1.2 base, white roof cap, door on +Z with a latch and a green "vacant" dot, vents, a stack | one of `#1f4f9a` `#2f6b4f` `#8d949a`; plate `HOLLIS`, `SITE SERVICES`, `UNIT 14` | none |
| `boombox` (71-80, 361-365) | the portable stereo of 2.5.1 as a prop of its own | black, chrome | none; no collision; never placed alone |

### 2.8 Chop shop

Line numbers in the first column are in `src/props/shop.js`. `car_lift` and `car_on_stands` are in 2.4.5.

| id | The real object, parts and dimensions (m) | Colours, text | Variants |
|---|---|---|---|
| `tool_chest` (87-111) | roller cabinet 1.06 × 0.50 × 0.62 with five drawers, a top chest 1.02 × 0.46 × 0.33 with three, aluminium pulls, four castors, a side handle; 1.09 high | red `#b3261e` | none |
| `workbench` (113-137) | bench 2.2 × 0.78 with a thick timber top at 0.80 on an angle-iron frame, a lower shelf with a toolbox, a carton and a can, a vise on the front corner, a carburettor on a rag, a socket tray and a coffee cup | timber, dark iron, blue vise `#234a7a` | none |
| `engine_hoist` (139-173) | cherry-picker crane: mast 1.5 tall, boom to a tip at (0.44, 1.92), hydraulic ram, splayed legs on castors, pump handle; a V engine block 0.52 × 0.40 × 0.34 hanging from the hook at y 1.08 | one of `#1f4f9a` `#b3261e` `#d9621a` | none |
| `shelf_rack` (175-211) | pallet racking 2.7 × 0.87 × 3.0: two frames, four beam levels (0.14, 0.98, 1.82, 2.62) with plywood decks, loaded with tyres on the bottom, cartons, three parts bins and four cans, a carton and a timber box on top | blue frames `#1a4a8a`, orange beams `#d9621a`, blue bins `#2c5c9a` | 2 loads |
| `compressor` (213-242) | wheeled shop compressor: a horizontal tank 0.92 long, radius 0.20, two 0.24 m wheels and a foot, motor and pump on top under a belt guard, a gauge, a handle with a coiled yellow hose | tank one of `#b3261e` `#1f4f9a` `#202326`; hose `#d9a21a` | none |
| `vending_machine` (244-264) | soda machine 0.90 × 0.76 × 1.84: one tall lit face 0.6 × 1.2, a column of six buttons, coin slot, delivery bin | black cabinet; face `ICE COLD SODA`, `$1.00` on a blue-to-cyan field | `lit: false` |

### 2.9 Court, lot, rooftops and facades

Line numbers in the first column are in `src/props/lot.js`.

| id | The real object, parts and dimensions (m) | Colours, text | Variants |
|---|---|---|---|
| `hoop` (18-41) | playground basketball hoop, long along X: a gooseneck steel post at x −0.78 rising to 3.56 and reaching over to a steel backboard 1.2 wide × 1.05 tall at x 0.12 (centre y 3.45) that faces +X; an orange rim (radius 0.228) at y 3.05, a chain net 0.385 long | dark post, white board with a worn orange rectangle, rim `#d9521a` | none |
| `bleachers` (43-63) | four-row aluminium bleacher 4.0 long × 1.96 deep: plank seats at 0.42, 0.78, 1.14 and 1.50 (the lowest at +Z), foot boards, three steel frames, a back rail at 1.58 | aluminium, dark steel | none; the rows are steps you can climb |
| `court_light` (65-84) | steel mast 8.55 tall with a crown of four flood heads 0.42 × 0.28, one to each side, on a cross arm at 8.7 | galvanised; lens glow `#dfe8ff` × 6 | `on: false` |
| `lot_booth` (86-118) | parking attendant's hut 2.1 × 1.7 on a 2.2 × 1.8 slab: steel to a sill at 1.05, glass above on three sides, a blind back, a door on the +X side, a flat roof with a lip to 2.37, a small roof unit to 2.59 | white `#e6e4dc`; sign `PARK` / `24 HOURS` (gold on black, 1.6 × 0.56) under the front window; tariff `RATES`: `FIRST HOUR $6`, `EACH ADD’L $3`, `ALL NIGHT $14`, `LOST TICKET $30`, `NO IN & OUT` | `lit: false` |
| `billboard` (120-165) | a roadside billboard on a steel frame: two riveted legs 0.34 square at x ±2.6, cross-braced, a face 9.0 × 4.1 from y 6.7 to 10.8, a catwalk with a railing under it at 6.35, a ladder on the +X leg, four lamp arms throwing light up the face | El green steel `#1f2a26`; face: the IPX lozenge, a gold rule and `IPX.EXCHANGE` in white on near-black (2.11) | `lit: false` |
| `water_tower` (167-192) | rooftop water tank: a wooden stave tank 2.6 across from y 2.13 to 4.10 with five iron hoops and a conical roof to 4.98, on a braced steel stand 1.9 tall, a riser pipe, a ladder | timber, dark iron | none |
| `ac_unit` (194-208) | packaged rooftop air conditioner 1.16 × 0.86 × 0.74 on two skids, fan under a guard on top, louvres on +Z, a conduit | galvanised | none |
| `fire_escape` (210-262) | one storey of a fire escape, wall at −Z: a grated landing 2.9 × 1.05 at y 0.25, a railing to 1.20 of square bars, and a steep stair from the +X end up to a hatch at the −X end of the next landing (module height 3.0) | dark iron | `top`: a ladder to the roof instead of the stair; `bottom`: adds the drop ladder hauled up (reaches y −1.6). The level uses only the plain module |
| `awning` (264-303) | shed awning 4.0 wide projecting 1.28 from the wall (−Z), sloping from 0.90 at the wall to 0.34 at the lip, a scalloped valance to 0.10, a pipe frame | fabric `#7a1f24` | `striped` (alternate panels white); `text` letters the valance; never placed (the level builds its awnings itself) |

### 2.10 Lamp hints and anchors

A prop may publish lamp hints: where a real fixture's light is, for the lighting system. Local coordinates,
colour, the web engine's intensity and range numbers, a kind, and an aim. The lighting spec decides what becomes
a real light; these are the fixture positions.

| Prop | Local position | Colour | Intensity / range | Kind | Aim | Source |
|---|---|---|---|---|---|---|
| `street_lamp` | (0, 7.6, 2.16) | `#ffb45e` | 90 / 20 | street | down | src/props/street.js:374 |
| `court_light` | (0, 8.5, 0) | `#dfe8ff` | 160 / 30 | flood | down | src/props/lot.js:81 |
| `floodlight_stand` | (0, 2.0, 0.25) | `#fff1d0` | 60 / 14 | work | (0, −0.32, 0.95) | src/props/clutter.js:333 |
| `billboard` | (±2.2, 7.1, 0.6) | `#fff1d6` | 40 / 12 each | flood | (0, 0.9, −0.44): up the face | src/props/lot.js:160 |
| `ipx_truck` headlamps | (4.0, 0.9, ±0.68) | `#fff0d0` | 22 / 9 each | work | (1, −0.25, 0) | src/props/vehicles.js:1051 |
| `ipx_truck` door lamp | (−3.8, 2.46, 0) | `#fff1d6` | 26 / 9 | work | (−0.3, −1, 0) | src/props/vehicles.js:1071 |
| `food_cart` | (0.2, 1.7, 0.1) | `#ffd9a0` | 16 / 6 | work | none | src/props/vehicles.js:911 |
| `lot_booth` | (0, 1.6, 1.0) and (0, 0.6, 1.0) | `#ffc48a` and `#f6c21a` | 14 / 6 and 6 / 4 | window, neon | none | src/props/lot.js:113-114 |
| `bus_shelter` | (−1.4, 1.3, 0.2) and (0.4, 2.2, 0.1) | `#dfe8ff` | 12 / 6 and 10 / 5 | neon, window | none | src/props/street.js:349-350 |
| `vending_machine` | (−0.1, 1.2, 0.6) | `#9fd4ff` | 12 / 5 | neon | none | src/props/shop.js:261 |
| `phone_booth` | (0, 1.9, 0.1) | `#dfe8ff` | 7 / 4.5 | window | none | src/props/street.js:310 |

Switched off (`on: false` or `lit: false`) a prop publishes no hint. On the block: 9 street lamps, 2 court
lights, 3 floodlight stands, 1 billboard, 1 truck, 1 food cart, 1 booth, 1 shelter, 2 vending machines and 3
phone booths, all switched on.

Anchors are named attachment points (local position and direction) meant for effects and sound:

| Prop | Anchor | Position | Direction | Source |
|---|---|---|---|---|
| `food_cart` | `steam`, `propane` | (0.28, 1.1, 0.12), (0.95, 0, −0.25) | up | src/props/vehicles.js:915-916 |
| `manhole` | `steam` | (0, 0.02, 0) | up | src/props/street.js:577 |
| `burned_car` | `smolder` | (1.5, 1.0, 0) | up | src/props/vehicles.js:801 |
| `generator` | `exhaust` | (0.7, 1.4, 0.2) | up | src/props/clutter.js:304 |
| `ipx_truck` | `rearDoor`, `exhaust` | (−4.3, 0, 0), (0.3, 0.5, −1.07) | −X, −Z | src/props/vehicles.js:1120-1121 |
| `hydrant_open` | `spray` | (0, 0.47, 0.17) | (0, 0.29, 0.96) | src/props/street.js:265 |
| `propane_tank`, `welding_rack` | `jet` | see 2.5.2 | | src/props/gameplay.js:357, 400 |
| `master_case` | `boombox`, `beacon`, `reel` | see 2.5.1 | | src/props/gameplay.js:176-178 |

**In the shipped game nothing reads these anchors** (`anchorAt` in src/level/kit.js:649 has no caller). Steam rises
from three of the six manholes and from grates the level lists itself (src/level/ground.js:187-191); the burned car
does not smoulder, the generator and the truck have no exhaust, the food cart does not steam. The explosives
module aims its flame jet from the bullet hole, or from the top of the item, not from the `jet` anchor
(src/explosives.js:332-347). The reel's boombox sound is placed at the objective position + 0.6 m, not at the anchor
(src/audio/ambience.js:211-222). Only the open hydrant is wired: its nozzle direction (0, 0.29, 0.96) is read by the
atmosphere module for water droplets and by the material library for the wet-street patch (src/props/street.js:274,
src/atmos/life.js:285-290, src/mats.js:364-370).

### 2.11 Painted graphics (all invented)

Every small picture a prop carries is one region of a single 2048 × 1024 sheet, drawn in code (src/props/atlas.js;
half size at low quality, src/props/materials.js:38-39). 51 regions. The vehicle, IPX and gameplay regions are
described where they are used (2.4.4, 2.4.6, 2.5). The rest, with the text a brand reviewer will read:

| Region (base px) | Content | Used on (size in m) |
|---|---|---|
| `ipx_ad` (320 × 480) | one-sheet on a near-black gradient: a white rule, `IPX PRESENTS`, the title in two lines (`MURDER` white, `INC.` gold), `STARRING JA RULE`, a gold rule, the IPX lozenge, `IPX.EXCHANGE` in grey | bus shelter ad box, both faces (1.14 × 1.72) |
| `sign_nopark`, `sign_bus` (128 × 176) | `NO` `PARKING` `ANYTIME` in red on white with a double arrow; a white bus on blue, `BUS` `STOP` in blue, `NO STANDING` in red | sign post (0.32 × 0.44); bus shelter flag (0.26 × 0.36) |
| `sign_oneway` (256 × 80), `sign_stop` (128 × 128) | white arrow on black with `ONE WAY`; red octagon with `STOP` | sign post (0.58 × 0.18; 0.52 × 0.52) |
| `news` (128 × 160) | front page: masthead `QUEENS NIGHT LEDGER`, headline `THREE REELS` `GONE`, a grey photo block, text lines | newspaper box window (0.33 × 0.41) |
| `mail` (128 × 96) | `MAIL` in white on navy over grey text lines | mailbox (0.36 × 0.27) |
| `meter` (64 × 96) | a half dial with a red sector, `1 HR`, `25¢` | parking meter, both faces (0.10 × 0.15) |
| `phone_sign` (192 × 48), `phone_unit` (128 × 160) | a handset glyph on blue and `PHONE`; the phone's face: instruction card, a 3 × 4 keypad, coin slot, `25¢` | phone booth head (0.8 × 0.2, three faces); phone (0.26 × 0.33) |
| `vend` (192 × 384) | blue-to-cyan gradient with bubbles and a white swoosh, `ICE` `COLD` in italic, `SODA`, a gold price tag `$1.00` | vending machine face (0.6 × 1.2) |
| `ped_stop`, `ped_walk` (64 × 64) | an orange raised hand; a white walking figure; both on black | traffic light pedestrian head (0.3 × 0.3) |
| `stickers` (96 × 128) | nine small coloured stickers at odd angles | phone booth (0.3 × 0.4), street lamp variant 1 (0.16 × 0.22) |
| `cart_menu` (320 × 112) | see 2.4.5 (food cart) | food cart, both sides (1.5 × 0.52) |
| `booth_sign` (320 × 112), `booth_rates` (160 × 208) | see 2.9 (`lot_booth`) | booth front (1.6 × 0.56), beside the door (0.5 × 0.65) |
| `dumpster` (320 × 64) | `HOLLIS CARTING`, `718 · 555 · 0144`, worn white stencil | dumpster front (0.5 × 0.1) |
| `crate_stencil` (192 × 128), `cardboard` (128 × 128) | see 2.7 | crate (0.66 × 0.44), carton (0.3 × 0.3) |
| `drum_label` (128 × 80) | `MOTOR OIL`, `10W-40`, `55 GAL · 208 L` | oil drum variant 0 (0.19 × 0.12) |
| `gauges` (128 × 128), `gen_label` (192 × 80) | two dials and four buttons; `DANGER` `HIGH VOLTAGE` `60 kW · 480 V` on yellow | generator (0.34 × 0.34; 0.42 × 0.175, both flanks) |
| `porta` (128 × 96) | `HOLLIS` `SITE SERVICES` `UNIT 14` | portable toilet door (0.44 × 0.33) |
| `backboard` (256 × 160) | an orange border and target rectangle, worn | hoop backboard (1.2 × 1.05) |
| `ticking` (128 × 128) | blue stripes on grey-beige with stains | mattress top (1.62 × 0.76) |
| `tag_a`, `tag_b`, `tag_c` (256 × 112) | marker scrawls without letters: bone white, oxblood, black | Vulture van, dumpster, mailbox, phone booth, jersey barrier |
| `stripes_ow`, `stripes_yb`, `stripes_rw` (256 × 40) | diagonal hazard stripes: orange/white, yellow/black, red/white | barricade boards and a jersey barrier; the IPX truck's step bumper; `stripes_rw` is drawn but used nowhere |

Painted outside the atlas: the **billboard face**, a 1024 × 512 picture of its own: near-black `#0d0e11`, the IPX
lozenge in white 270 px tall centred at (512, 214), a gold `#f6c21a` rule as wide as the lozenge at y 388,
`IPX.EXCHANGE` in bold white capitals at y 440, shaded as if lit from below (src/props/materials.js:185-222); the
**box-truck tags**, the **street-name blade** and the **awning lettering**, which come from the material
library's sign and graffiti painters (src/props/vehicles.js:752, src/props/street.js:543, src/props/lot.js:298).

Real names that appear, by design: the title `MURDER INC.`, `JA RULE` / `RULE`, `IPX`, `IPX.EXCHANGE`, and real
places (`NEW YORK`, `NYC`, `QUEENS`, `QNS`, `HOLLIS`, `JAMAICA AV`). Everything else is made up: the carting
company and its 555 number, the newspaper, the site-services firm, the plates and the medallion.

### 2.12 Materials and colours

Props take their surfaces from the shared material catalogue by name, so they share texture sets with the level
(docs/CONTRACT.md:370-378). Base values from src/config/catalog.js:6-64:

| Catalogue name | Colour | Roughness / metalness | Where props use it |
|---|---|---|---|
| `car_paint` | per instance (2.4.3) | 0.32 / 0.55 | all vehicle bodies, motorbike tank, IPX truck |
| `glass_car` / `glass_car_lit` | `#0a0d10` (lit: emissive `#ffc890` × 0.45) | 0.05 / 0.3 | vehicle glass |
| `tire` / `rubber` | `#0e0e0f` / `#121212` | 0.9 / 0, 0.95 / 0 | tyres; castors, mud flaps, seats, cables |
| `chrome` | `#d8dde2` | 0.12 / 1 | hubcaps, bumpers, handles, case corners |
| `plastic_dark` | `#18191b` | 0.6 / 0 | bumpers, undersides, lids, case panels, boombox |
| `metal_dark` / `metal_galv` | `#23262a` / `#8d949a` | 0.55 / 0.8, 0.5 / 0.85 | cast iron and painted steel; galvanised and stainless steel, aluminium |
| `steel_rust` / `steel_el` | `#5b3a26` / `#1f2a26` | 0.85 / 0.5, 0.6 / 0.7 | burned car, brake discs; billboard and water-tower steel |
| `gold` | `#e7b53a` | 0.25 / 1 | the reel, the truck's waist band |
| `paint_yellow` / `_white` / `_red` / `_blue` / `_green` / `_black` | `#f2c21a` / `#e6e4dc` / `#b3261e` / `#1f4f9a` / `#1f5a3a` / `#101113` | 0.45…0.6 / 0…0.2 | painted street and shop equipment |
| `plastic_orange` | `#e8641b` | 0.6 / 0 | cones, barrels |
| `trash_bag` | `#0b0b0c` | 0.35 / 0 | refuse sacks, bin liners |
| `wood` / `plywood` / `cardboard` | `#6d5236` / `#a98a5c` / `#9a7b52` | 0.85…0.95 / 0 | pallets, crates, benches, cartons |
| `fabric` / `fabric_awning` | `#2b2d33` / `#7a1f24` | 0.95 / 0, 0.9 / 0 | mattress, scrim, rag; umbrella, awning |
| `concrete` / `concrete_dark` / `dirt` / `leaves` | `#7b7a76` / `#44444a` / `#3a3229` / `#1f3322` | 0.9…1 / 0 | barrier, planter, slab; sandbags (tinted); foliage |
| `glass_store` | `#1a2630` at 32 % opacity | 0.06 / 0.2 | booth, shelter, sneeze guard, newspaper box |
| `glass_lit_warm` / `glass_dark` | `#0d1218`, emissive `#ffb45e` × 0.75 / `#0d1218` | 0.08 / 0…0.2 | lot booth panes (lit / unlit), dead lamp lenses |
| `roll_gate` / `chainlink` | `#6c7074` / `#9aa0a4` | 0.55 / 0.75, 0.6 / 0.8 | box-truck door; fence mesh (40 % opacity) |

The props' own materials (src/props/materials.js:96-152, 236-259): atlas decals lit by the scene (roughness 0.7);
atlas decals that glow (unlit, × 1.7); one unlit HDR material for every lamp lens and LED (colour × gain, values
above about 1 bloom); a vertex-coloured matte paint (roughness 0.6, metalness 0.15) and its heat-glowing twin
for the explosives; a cut-out lattice (alpha test 0.5, double-sided, bars 12 % of a cell) for milk crates (26
cells per metre), the wire basket (15), the trolley (22), the hoop net (16), the billboard catwalk (12 × 30) and
the fire-escape deck (9 × 34); and additive unlit materials for the light shaft, pool, water jet and flames.

### 2.13 The stub factory

`src/stubs/props.js` is the stand-in used when the real factory is not built: every prop is a box of its
catalogue size with one collider and one flat colour (src/stubs/props.js:29-66, 173-214). It keeps the contract: the
stub reel case hides its body when taken and shows a gold column 5 m tall and a turning marker
(src/stubs/props.js:111-134); the stub truck shows an `IPX` / `IPX.EXCHANGE` plate on both sides and blinks two rear
hazards on a 1 s period (src/stubs/props.js:136-156); the stub explosives vanish when gone (src/stubs/props.js:158-162).
Nothing in it needs porting; it documents the minimum each stateful prop must do.

---------------------------------------------------------------------------------------------------

## 3. Behaviour

### 3.1 Building an instance

```
build(name, opts):                                   # src/props.js:200-224
  def  = catalogue[name]  or  {size 1×1×1, surface metal} with a one-time warning
  seed = abs(floor(opts.seed)) if finite, else props_stream.int(0, 65535)
  try:
      variant = seed mod spec.variants                # shape; built once per (name, shape options, variant), then shared
      colour  = opts.color ?? spec.forced_colour(opts) ?? spec.palette[scramble(seed, 17) mod n]
      dome    = opts.lit ?? (scramble(seed, 91) / 65535 < spec.dome)      # cars only
      instance = shared geometry + paint colour + lit or dark car glass + own moving parts (stateful props)
  except: instance = plain box of def.size with one collider
  dynamic = def.dynamic or instance has update or setState
```

- Same name, same options, same seed: the same prop, always. The level seeds every sedan, both pickups and one
  SUV explicitly; everything else draws its seed from the factory's stream, so its variant (which pile of bags,
  which plate) is fixed only for a given world seed. The shipped game always runs seed 1994 unless `?seed=` is
  given (docs/CONTRACT.md:102).
- Shape randomness inside a builder (jitter of stacked pallets, which crate is which colour, the lean of a tree)
  comes from a stream keyed by the prop name and variant, so variant k of a prop looks the same in every run and
  every seed (src/props.js:95-99).
- Options that change the shape: `variant`, `open`, `lit` / `on` (lamps and lit signs are built in or left out),
  `text`, `spray` (docs/CONTRACT.md:354-364).

### 3.2 Standing a prop on the block

```
place(name, x, z, yaw, o):                            # src/level/kit.js:596-655
  y = o.y ?? floorAt(x, z)                             # 0 road and yards, 0.15 sidewalks
  if name in {sedan, suv, van, box_truck, pickup}: o.color = vehiclePaint(o, name)     # 2.4.3
  prop = props.build(name, o)
  prop.position = (x, y, z);  prop.rotation.y = yaw   # local +X → world (cos yaw, 0, −sin yaw)
  for each collider c of the prop (unless o.collide is false):
      skip if (c.height < 0.2 and c.top < 0.3)         # walk-over
      register an oriented box (centre and size from c, turned by yaw) with
          surface = c.surface or the prop's, bulletOnly, playerOnly, noNav = c.noNav or o.noNav, tag = name
  for each lamp hint: add it to level.lamps in world space (work lamps at priority 6)
  static props are merged per material; dynamic props stay separate and get update(dt) every frame
```

- The web physics world is axis-aligned boxes only: an off-axis collider is sliced into several small aligned
  boxes (docs/CONTRACT.md:184). That is an implementation limit, not a rule: the intent is an oriented box.
- Collider flags (docs/CONTRACT.md:178-182): `bulletOnly` is hit by rays and ignored by movement and the nav
  grid; `playerOnly` blocks bodies and is ignored by rays and the nav grid; `noNav` is not stamped into the nav
  grid (things overhead).
- Rooftop and facade props are placed with `collide: false` (most roof plant also with `cast: false`).
- A prop no sunlight reaches at any time of day (inside the shop, deep under the shed) stops casting shadows;
  vehicles, pallet stacks and crates cast through a simplified hull (src/level.js:255-287, src/level/kit.js:65-74). These
  are web-renderer savings with no gameplay meaning.

### 3.3 Master reel case

States: `live` → `grabbing` ⇄ `live` → `taken`; reset returns to `live` (mission) or `taken` (Hold the Block).

| State | Lid | Reel | Beacon, shaft, pool, LEDs | Progress bar |
|---|---|---|---|---|
| `live` | open 95° | shown | on, slow pulse | hidden |
| `grabbing` (progress t 0…1) | open 95° | shown | on, brighter and faster with t; the shaft narrows with t | shown when t > 0.005, length = t × 0.34 m |
| `taken` | drops shut in 0.3 s | hidden at once, together with its tape box and the beacon mast | off at once | hidden |

```
setState(next, t):                                    # src/props/gameplay.js:231-239
  state    = next if next in {grabbing, taken} else live
  progress = clamp(t, 0, 1) if state is grabbing else 0
  if state is not taken: shut = 0                      # the lid is up again at once
  elif update() has never been called: shut = 1        # no loop running: just show it shut

update(dt):                                           # src/props/gameplay.js:240-248
  clock += dt
  if state is taken and shut < 1: shut = min(1, shut + dt / 0.3)
  lid angle = 1.66 rad × (1 − shut²)                   # falls faster as it goes

lights, every setState and update:                    # src/props/gameplay.js:209-228
  rate = 2.2 rad/s                    (grabbing: 2.2 + 6.8 × progress)
  wave = 0.5 + 0.5 × sin(clock × rate)
  k    = 0.45 + 0.55 × wave           (grabbing: 0.75 + 0.25 × wave + progress)
  beacon colour  = gold × (1.2 + 3.2 × k)              # HDR: 2.6…4.4 waiting, up to 7.6 at a full grab
  shaft opacity  = 0.16 + 0.30 × k
  pool opacity   = 0.20 + 0.30 × k
  shaft width    = clamp(distance to camera / 9, 0.6, 3.2)   (grabbing: × (1 − 0.45 × progress))
  LEDs lit while sin(clock × 9.2) > −0.3               # about 1.5 flashes a second, lit 60 % of the time
```

- `clock` starts at `(seed mod 7) × 0.9` s so the three cases do not pulse in step (src/props/gameplay.js:201).
- The waiting pulse has a period of 2.86 s; at a full grab 0.70 s.
- The shaft widens with distance so the marker reads from across the block without flaring up close: at 5.4 m
  or nearer it is 0.6 × its modelled radius, from 28.8 m on 3.2 ×.
- What drives it (src/game.js:554-599): while the player holds Interact on a reel in reach, the game adds `dt / 2.4`
  to its progress and calls `setState('grabbing', progress)` every frame. When the hold breaks, the game's
  progress drains at 1.6 per second and the game calls `setState('live', progress)`: the prop ignores the number
  in `live`, so the bar on the lid vanishes at once while the HUD ring drains. At progress 1 the game calls
  `setState('taken', 1)`. A run reset calls `live` for every case in the mission and `taken` in Hold the Block
  (src/game.js:232).
- Taking the reel does not remove the prop: the case, hand truck and boombox stay as cover with their colliders.
  What goes: the reel and its tape box, the beacon with its mast (mast, clamp and base disc sit in the reel's
  group, src/props/gameplay.js:119-135), the shaft, the pool and the LEDs; and the lid drops. The tracker's LCD stays
  lit. (The contract allows "case gone / lid shut" for `taken`, docs/CONTRACT.md:332-333; the built prop shuts
  the lid and keeps the case.)
- The boombox loop is started for every case at every run reset in mission mode (and once when audio is first
  unlocked) and stopped with a 0.25 s fade when its reel is taken; no loop in Hold the Block
  (src/audio/ambience.js:211-229, src/audio/react.js:259-266, 296-301).

### 3.4 IPX truck

States: `idle` → `open` on a win; any other value, and every run reset, returns it to `idle`.

```
setState(next):                                       # src/props/vehicles.js:1143-1150
  state = open if next is open else idle
  if idle: swing = 0                                   # doors shut at once, vault light off

update(dt):                                           # src/props/vehicles.js:1151-1158
  clock += dt
  hazards lit = state is open  or  (clock mod 1.1) < 0.55     # idle: blink, 1.1 s period, half on; open: steady
  if state is open and swing < 1: swing = min(1, swing + dt / 1.1)
  e = swing² × (3 − 2 × swing)                         # smoothstep
  right leaf angle = +1.9 rad × e,  left leaf angle = −1.9 rad × e    (about the vertical hinge; both swing outward)
  vault light lit when swing > 0.15                    # 0.165 s after the doors start
```

- `open` is set at the instant the player stands in the extraction zone with all three reels (src/game.js:649-668);
  the debrief card follows 3.3 s later (src/config/flow.js:17), so the full 1.1 s swing is seen.
- Before that, entering the zone without all reels only shows a message, at most every 8 s (src/config/flow.js:50-55).
- Headlamps, marker lamps and tail lamps are fixed glows. The six hazard lamps (two rear, two front, two side
  repeaters) switch as one group. There is no engine sound, exhaust or body shake in the source although the
  fiction says the truck is idling.
- `update` runs whenever the game is not paused, so the hazards also blink on the title screen
  (docs/CONTRACT.md:86, src/level.js:209-212).

### 3.5 Propane tank and welding rack (what the prop shows)

| State | Body | Extra |
|---|---|---|
| `idle` | normal paint | solid collider |
| `lit` | the same mesh in the heat-glow paint | a flame jet from the fx system at the bullet hole, a rising hiss, the body rattling; solid collider |
| `gone` | hidden; a scorched foot is shown instead | no collider |

```
on a round (player: weapon damage; enemy: always 9):   # src/explosives.js:362-375
  hp -= amount;  if idle: light the fuse (propane 1.6 s, rack 1.1 s);  if hp <= 0: fuse = min(fuse, 0.06)
on another blast within 2.2 + 1.6 × size metres, seen or not:      # src/explosives.js:381-403
  fuse = min(fuse, 0.14 + random(0, 0.3) + 0.03 × distance)        (lights it if idle; costs no hit points)
while lit, every frame:                                 # src/explosives.js:427-447
  fuse -= dt;  build = 1 − fuse / fuse at ignition
  hiss volume = 0.25 + 0.75 × build²
  tilt about x = sin(71 × clock + i) × a,  about z = sin(83 × clock + 2.3 × i) × a,  a = 0.035 rad × (0.3 + 0.7 × build)
at fuse 0:                                              # src/explosives.js:406-425
  remove the collider, show `gone`, explode at the item's mid-height (radius and damage by type, player × 0.5),
  shake the camera by 0.15 + 0.9 × g² with g = 1 − distance / 28,  alert enemies within 60 m
reset():  every item back to idle, full hit points, collider restored      # src/explosives.js:265-283, 291-325
```

- The flame jet comes out of the bullet hole along the hit normal tipped 0.55 upward; when the fuse was lit by a
  chain it comes from the top of the item (0.94 × height) in a random direction (0.55 cos a, 0.85, 0.55 sin a). It
  lasts the fuse + 0.15 s at scale 0.9 (tank) or 1.2 (rack) (src/explosives.js:332-347).
- The prop's own flame mesh is shown only when the fx module is a stub; then it flickers: length × (1 + 0.28
  sin 41t + 0.18 sin(67t + 1.3)), width × (1 + 0.2 sin 53t), spin 9 rad/s, opacity 0.75 + 0.25 sin 59t
  (src/props/gameplay.js:291-312).
- Explosives are reset on every run reset and, in Hold the Block, after every even wave (src/game.js:224, 701).

### 3.6 Traffic signal (`traffic_light`, in the catalogue, not on the block)

One cycle is 30 s: green 14 s, amber 3 s, red 13 s. Each signal starts at `(seed × 7.3) mod 30` s into its cycle.
Unlit lenses glow at gain 0.1, the lit one at 4.5. The pedestrian head shows the white walking figure for the
first 8 s of red, then the orange hand flashing (0.5 s on, 0.5 s off) for the last 5 s of red, and the steady hand
through green and amber (src/props/street.js:25, 412-432).

### 3.7 Open hydrant

The jet is a fixed mesh along a ballistic arc: from the front outlet at (0, 0.47, 0.17), speed 1.56 m/s up and
5.2 m/s out along +Z, gravity 9.8, so it lands after 0.507 s at z 2.81; its radius grows from 0.05 by 0.5 m per
second of flight; brightness fades from 1 at the mouth to 0.2 where it lands (src/props/street.js:29-32, 48-76).
Every frame it breathes: scale x = 1 + 0.06 sin 23t, y = 1 + 0.04 sin(17t + 1), z = 1 + 0.03 sin 5t; opacity 0.26
+ 0.08 sin 31t × sin 7t over an additive `#cfe4ff` (src/props/street.js:272-289). The atmosphere module adds 260
droplets along the same arc (src/config/look.js:280). On the block it stands on the south sidewalk at (−12.25, 7.34)
turned 180°, hosing the avenue (src/level/street.js:146); by day the street stays wet only inside its reach
(docs/CONTRACT.md:309-311).

### 3.8 Order in a frame, day and night, edge cases

- Frame order (docs/CONTRACT.md:81-91): the game's update sets prop states (grab progress, win); then, only while
  a run is live, `explosives.update` counts fuses; then, in every state except paused, `level.update` runs every
  dynamic prop's `update` (reel cases, truck, hydrant jet). A state set this frame is drawn this frame.
- Daylight is the default. By day the dome-lit car glass is plain dark glass and the lit booth panes stop
  glowing; lamp lenses, tail lamps, the taxi roof light, lit signs and the beacon keep their glow material
  (docs/CONTRACT.md:307-312, src/props/materials.js:111-121). Lamp hints are published at both times of day; whether
  a hint becomes a real light is the lighting system's choice.
- A prop built with an unknown state name falls back to `live` / `idle`.
- `master_case.setState('taken')` on a prop nobody updates shuts the lid instantly.
- The Vulture van's open doors, the lamp arms, tree crowns and the hydrant's jet have no collision: colliders
  never leave the catalogue footprint (docs/CONTRACT.md:346).
- The fence props' collider is a solid 8 cm slab: chain-link stops rounds in the prop catalogue. (The Cage fence
  the level builds itself is different: player-only above a knee wall.)
- The raised sedan is `noNav`: enemies path under it.
- Bleacher rows are 0.36 to 0.42 m steps, at or under the 0.42 m step-up: players and Goons walk up them.

### 3.9 Named moving parts in the source

The stateful props expose their moving parts as named groups (`nodes`). The exported data and any tooling that
reads the web scene will meet these names.

| Prop | Node | Pivot (local x, y, z) | Driven how |
|---|---|---|---|
| `ipx_truck` | `doorL` | (−3.30, 1.86, 0.91) | turns +1.9 rad about the vertical when open. Despite the name it is the leaf on the truck's **right** (local +Z), which is also the viewer's right from behind the truck |
| | `doorR` | (−3.30, 1.86, −0.91) | turns −1.9 rad; the leaf on the truck's left |
| | `hazards` | origin | shown or hidden as one group |
| | `vaultLight` | origin | shown while the swing is past 0.15 |
| `master_case` | `lid` | (−0.19, 0.53, −0.16) | tips back 1.66 rad about the local X axis when open |
| | `bar` | (−0.36, 0.521, 0.09), carried by the lid | stretched along x by the progress |
| | `reel` | (−0.19, 0.53, 0) | shown or hidden: reel, tape box, beacon mast, clamp and base |
| | `beacon` | (−0.422, 1.22, 0) | the lens: colour pulse |
| | `shaft` | (−0.422, 1.34, 0) | widened in x and z, opacity pulse |
| | `pool` | (0, 0.02, 0) | opacity pulse |
| | `leds` | origin | tracker LED and boombox meter, blinked together |
| `propane_tank`, `welding_rack` | `body`, `flame`, `wreck` | flame at (0, 0.52, 0.07) / (0.28, 1.2, 0.03) | one shown per state (the flame only with stub fx) |
| `traffic_light` | `red`, `amber`, `green`, `stop`, `walk` | origin | shown or hidden by the cycle |
| `hydrant_open` | `jet` | origin | scaled and faded every frame |

Sources: src/props/vehicles.js:1087-1116, src/props/gameplay.js:104-171, 333-351, 364-393, src/props/street.js:267-269, 401-409.

---------------------------------------------------------------------------------------------------

## 4. Unreal mapping

### 4.1 Coordinates, local frames and the placement rule

World positions follow the shared convention: Unreal (X, Y, Z) cm = (x, z, y) web metres × 100.

**Local frame of every prop asset: keep the web local frame.**

| | Web (three.js) | Blender | Unreal |
|---|---|---|---|
| Length axis, a vehicle's nose | +X | +X | +X |
| Up | +Y | +Z | +Z |
| Web local +Z: a vehicle's right side; the *front* of furniture (bench seat, booth opening, sign face, lamp arm, hydrant jet) | +Z | −Y | +Y |
| A local point (x, y, z) | (x, y, z) m | (x, −z, y) m | (x, z, y) × 100 cm |
| Pivot | footprint centre on the ground | same | same |

So an asset's bounding box in Blender is `[L, W, H]`, vehicles point their nose at +X as the shared convention
asks, and anything with a front (the web's "+Z" props) presents it toward **−Y in Blender**, exactly like a
facade module. With that, one rule places every prop:

```
Unreal location = (x × 100, z × 100, y × 100)        # y = 0 road, 0.15 sidewalk, or the level's own height
Unreal yaw (°)  = −(web yaw in radians) × 180 / π     # pitch = roll = 0 for every placed prop
```

Why the sign flips: the web engine's rotation about +Y by θ turns local +X to (cos θ, 0, −sin θ); Unreal's yaw
ψ turns +X to (cos ψ, sin ψ, 0); with Unreal Y = web z, ψ = −θ. Check: a car with web yaw π/2 points north (−z),
Unreal yaw −90° points −Y, north. Every local quantity in this document (collider boxes, lamp hints, anchors,
hinge pivots, mark positions) converts with the "local point" row and needs no other change. Direction vectors
convert the same way.

Hinge rotations, stated geometrically so no sign convention is needed:

- Truck doors: the hinge lines are vertical at local Unreal (X −330, Y ±91). Each leaf, closed, runs from its
  hinge toward the centre line; open, it has swung 108.9° outward and backward. As Unreal yaw on a component
  whose pivot is the hinge: −108.9° for the +Y (right) leaf, +108.9° for the −Y (left) leaf.
- Case lid: the hinge line runs along local X at (Y −16, Z 53). Open, the lid's front edge has travelled up and
  back through 95.1° and the lid stands just past vertical behind the case.
- Vulture van doors (static, modelled open): hinge lines vertical at (X −253, Y ±89); right leaf at 111.7°, left
  leaf at 88.8° from closed.

### 4.2 Converted reference values

| Quantity | Web | Unreal |
|---|---|---|
| Crouched eye / standing eye / step-up | 1.05 / 1.68 / 0.42 m | 105 / 168 / 42 cm |
| Sidewalk height under props | 0.15 m | 15 cm |
| Sedan, taxi: length × width × roof; cover tops | 4.61 × 1.85 × 1.45 m; 1.08, 1.45 | 461 × 185 × 145 cm; 108, 145 |
| SUV | 4.91 × 2.00 × 1.82 m; 1.24, 1.78 | 491 × 200 × 182 cm; 124, 178 |
| Pickup | 5.32 × 2.00 × 1.78 m; 1.27, 1.78 | 532 × 200 × 178 cm; 127, 178 |
| Van | 5.21 × 1.96 × 2.19 m; 2.14 | 521 × 196 × 219 cm; 214 |
| Box truck | 7.39 × 2.44 × 3.31 m; cab 2.28, box 3.30 | 739 × 244 × 331 cm; 228, 330 |
| IPX truck | 6.80 × 2.34 (2.48 mirrors) × 2.86 m; cab 2.58; vault floor 1.02; cab/vault break x 0.55 | 680 × 234 (248) × 286 cm; 258; 102; X 55 |
| IPX truck wheels | radius 0.50, axles x 2.05 and −1.75, track centres z ±0.97, inner rear tyre z ±0.64 | 50; X 205 and −175; Y ±97; Y ±64 |
| IPX truck door leaf | 0.89 × 1.62 × 0.07, hinge (−3.30, ±0.91), spans y 1.05…2.67 | 89 × 162 × 7; hinge (X −330, Y ±91); Z 105…267 |
| IPX truck door swing | 1.9 rad in 1.1 s, smoothstep | 108.9° in 1.1 s, smoothstep (ease in and out) |
| IPX truck hazards | 1.1 s period, 50 % duty; steady when open | same |
| IPX truck lamp hints | headlamps (4.0, 0.9, ±0.68) aim (1, −0.25, 0); door lamp (−3.8, 2.46, 0) aim (−0.3, −1, 0) | (X 400, Y ±68, Z 90) aim (1, 0, −0.25); (X −380, Y 0, Z 246) aim (−0.3, 0, −1) |
| Extraction zone relative to the truck | centre 5.4 m behind the truck's pivot, radius 2.5 m, ±3.5 m vertical | local X −540, radius 250, ±350 |
| Reel case footprint and colliders | see 2.5.1 | case X −45…3, Y ±30, Z 0…66; boombox X 3…45, Y ±30, Z 0…35 (bullets) and Z 0…66 (player) |
| Reel case lid | hinge (−0.19, 0.53, −0.16), open 1.66 rad, shuts in 0.3 s as 1 − s² | hinge (X −19, Y −16, Z 53), 95.1°, 0.3 s ease-in |
| Reel, tape box | 0.27 across × 0.038; box 0.29 × 0.29 × 0.04; tilt 0.7 rad | Ø 27 × 3.8; 29 × 29 × 4; 40° |
| Beacon lens / shaft / pool | lens top 1.346; shaft y 1.34…7.34, radius 0.05…0.14 × (0.6…3.2); pool radius 1.0 | 134.6; Z 134…734, radius 5…14 × (0.6…3.2); 100 |
| Shaft width rule | clamp(distance / 9 m, 0.6, 3.2) | clamp(distance / 900 cm, 0.6, 3.2) |
| Beacon pulse | 2.2 rad/s waiting (2.86 s period), up to 9 rad/s grabbing (0.70 s) | 0.35 Hz, up to 1.43 Hz |
| Interaction with a reel | reach 2.2 m, ±2.5 m vertical, free within 0.9 m, hold 2.4 s, drain 1.6 /s | 220, ±250, 90 cm; 2.4 s; 1.6 /s |
| Boombox sound source | objective position + 0.6 m | + 60 cm |
| Propane tank | 0.30 across × 0.585; collider 0.32 × 0.32 × 0.60; blast 6.5 m; chain reach 5.24 m | Ø 30 × 58.5; 32 × 32 × 60; 650; 524 |
| Welding rack | 0.905 × 0.53 × 1.52; collider 0.90 × 0.50 × 1.60 (around the rotated footprint); blast 7.5 m; chain reach 5.88 m | 90.5 × 53 × 152; 90 × 50 × 160; 750; 588 |
| Lit explosive rattle | 0.035 rad × (0.3 + 0.7 × build) at 71 and 83 rad/s | 2.0° × (0.3 + 0.7 × build) at 11.3 and 13.2 Hz |
| Blast camera shake reach / enemy alert radius | 28 m / 60 m | 2800 / 6000 cm |
| Hydrant jet | from (0, 0.47, 0.17); 1.56 m/s up, 5.2 m/s out; lands at 2.81 m after 0.507 s; g 9.8 | (X 0, Y 17, Z 47); 156 and 520 cm/s; 281 cm; 980 cm/s² |
| Signal cycle | green 14 s, amber 3 s, red 13 s; walk 8 s; flash 0.5 s | same |

Appendix B gives every collider box in Unreal local centimetres.

### 4.3 Which Unreal feature for which mechanic

| Mechanic | In the web game | In Unreal Engine 5 |
|---|---|---|
| A prop | one group of meshes, merged per material with the rest of the block | one Static Mesh asset per brief in `assets/props.json` (Nanite on for opaque meshes), placed as static mesh actors from the exported placement data. Identical meshes instance automatically; nothing needs merging |
| Collision | 1 to 4 boxes per prop | simple collision on the Static Mesh: box primitives copied from Appendix B. Gameplay queries (movement, weapon traces, AI sight) use the simple boxes so cover behaves as tuned; a second trace against the render mesh may place the impact decal on the visible surface |
| Surface type | a string per collider | Physical Materials (car, metal, concrete, wood, rubber, cloth, glass, dirt). A Static Mesh carries one simple-collision physical material, so props with two surfaces (car body and glass cabin, bus shelter, bench) need a small Blueprint or a second collision-only component for the other surface |
| `bulletOnly`, `playerOnly`, `noNav` | flags on a box | collision channels: the weapon trace channel (`Bullet` in spec 02) and the pawn object channel. Bullets-only boxes block the weapon trace and ignore pawns; player-only boxes block pawns and ignore traces; neither affects navigation. `noNav` boxes are overhead: turn off "can ever affect navigation" on them |
| Walk-over rule | flat colliders dropped by the level | give `pallet` and the `engine_hoist` legs no blocking collision |
| Paint colour per instance | vertex colour on a shared material | one car-paint Material Instance with the colour in Custom Primitive Data (or a per-actor dynamic instance); the nine chart colours, taxi yellow, the IPX black and the primers are the whole set |
| Plates, shape variants | atlas regions, seed-picked meshes | a plate mesh whose texture index is per-instance data; wheel faces as two or three interchangeable wheel meshes |
| Glowing lenses, LEDs, lit signs | unlit HDR materials | the emissive channel of each asset's texture set (`T_<Set>_E`) with the gains listed in this document as starting points |
| Dome-lit car glass | emissive glass, night only | night variant only: an emissive interior or a weak point light inside the cabin; nothing by day |
| Lamp hints | `level.lamps` entries | light components placed at the converted positions; type, units and budget belong to the lighting spec |
| Reel case | a rig with `setState` and `update` | an Actor with separate components for hand truck + case, lid, reel + tape box, boombox, beacon lens, shaft and pool; an enum state; a Timeline for the lid (0.3 s); the bar as a scaled mesh or a material scalar; the beacon and shaft driven by one dynamic material parameter from the pulse formula; an audio component for the loop; the hold-to-grab logic stays in the game flow |
| IPX truck | a rig with `setState` and `update` | an Actor: body mesh, two door-leaf meshes attached at the hinge sockets, a Timeline (1.1 s, smoothstep) for the swing, a looping timer for the hazards' emissive parameter, a light for the vault that switches on 0.165 s into the swing |
| Explosives | one module, instanced meshes, three looks per type | one Actor class with two data rows (2.5.2): health, fuse timer, chain rule, radial damage; `lit` = an emissive heat parameter plus a Niagara gas-flame jet at the hit point and an audio loop; `gone` = swap to the wreck mesh (a fractured mesh is optional polish, not parity) |
| Traffic signal, hydrant jet | small rigs | a timer-driven Actor (not on the block); a Niagara water jet on the ballistic arc with a wet-surface decal under it |
| Anchors | named points nobody reads | Static Mesh sockets with the same names: `steam`, `propane`, `smolder`, `exhaust`, `spray`, `jet`, `boombox`, `beacon`, `reel`, `rearDoor` |
| Random picks | seeded streams | bake the seed-1994 result (Appendix A and the exported placement data); do not re-roll at run time |
| Shadow hulls, per-material merging, the texture atlas, triangle budgets | web renderer economies | not ported |

### 4.4 Gameplay props on the block, in both spaces

| Prop | Web x, z (y) | Web yaw | Unreal X, Y, Z | Unreal yaw | Source |
|---|---|---|---|---|---|
| Reel 1 case (avenue) | −4, 1 | 0.35 | −400, 100, 0 | −20.1° | src/level/data.js:11 |
| Reel 2 case (shop floor) | −9.5, −21.5 | −0.5 | −950, −2150, 0 | 28.6° | src/level/data.js:12 |
| Reel 3 case (centre court) | 35.25, −22.5 | 1.1 | 3525, −2250, 0 | −63.0° | src/level/data.js:13 |
| IPX truck | 41.3, 29.7 | 0 | 4130, 2970, 0 | 0° (nose east) | src/level/data.js:17 |
| Extraction zone centre | 35.9, 29.7 | | 3590, 2970, 0 | | src/level/data.js:18 |
| Rule's SUV | −40.5, 5.98 | 0 | −4050, 598, 0 | 0° | src/level/street.js:47 |
| Vulture van | −9.4, 1.8 | 3.69 | −940, 180, 0 | 148.5° | src/level/street.js:73 |
| Open hydrant | −12.25, 7.34 (0) | 3.14 | −1225, 734, 0 | 180° | src/level/street.js:146 |
| Food cart | −5.7, −8.3 (0.15) | 0 | −570, −830, 15 | 0° | src/level/street.js:115 |

The 21 explosives (src/level/data.js:119-141; 14 tanks, 7 racks). Their exact positions in both spaces are tabulated
in `02-weapons-combat.md` section 2.10 and are not repeated here. Roughly, west to east: a rack outside the shop
beside the tyre cage and one in the welding corner inside; a rack at the foot of the mezzanine stair; two tanks
beside the food cart; a tank on the shop's north bench; a rack by the east lift and one in the alley by the shop's
side door; tanks at the foot, on the deck and at the east end of the scaffold shed; a tank at the barrier chicane in
the roadway; a tank in the vacant lot by the burned car; a rack and a tank in the rear lane; two tanks at the lot
booth; a rack on the lot's south wall and a tank in its east aisle; a tank in the Cage by the bleachers; a tank at
the roadblock. Every tank stands at yaw 0; a rack's collider box follows its yaw (2.5.2). Items on a sidewalk
stand at y 0.15, the one on the shed deck at y 2.95.

Placement rules the level tests (src/level/data.js:116-117): no explosive within 7 m of the player start or within
2.2 m of a reel.

---------------------------------------------------------------------------------------------------

## 5. Art and audio implications

### 5.1 What must be modelled

`docs/unreal/spec/assets/props.json` lists one brief per mesh: 75 briefs, with sizes in Blender axes, counts,
colours, materials, gameplay role, source line and priority. The rules behind them:

- **Model the real object at the code's size.** The low-poly originals are boxes, lathes and extrusions; the
  rebuild models what they stand for (a real sedan, a real steel drum) inside the same envelope. Length, width,
  height, wheelbase and the heights that matter to play (bonnet, belt line, roof, cover tops) must match section
  2 to about a centimetre, because the collider boxes and the cover tuning are kept.
- **The silhouette must fill the collider.** A player hides behind the box, so the visible mesh may not be
  smaller than its collider where it counts: a sedan's bonnet in the source is 0.90…1.00 m high under a 1.08 m
  collider; do not lower it further, and keep trash-bag piles, crates and stacks at their stated heights.
- **Vehicles are static props.** No drive train, no suspension rig, no destruction. They need believable
  undersides and wheel wells (the player crouches beside them) and, if the glass is made less opaque than the
  source's near-black tint, a simple interior. The source hides the cabin behind dark glass; a photoreal
  daylight look will want medium tint and seats, a dash and a wheel.
- **Hero assets** (priority 1): the IPX truck inside and out, the reel case assembly, Rule's SUV, the Vulture
  van with its load space, the yellow cab, the box truck, the propane tank and the welding rack, and the cover
  props that fill the avenue.
- **Variants to build as separate meshes or swaps**: van closed / Vulture open; hydrant capped / open; fire
  escape plain (the `top` and `bottom` forms are unused); jersey barrier plain / tagged / striped (decals);
  three trash-bag piles, three milk-crate stacks, three trees, two pallet stacks, two sandbag walls, two tyre
  stacks, two carton piles, two rack loads, two planters; sedan wheel faces; explosive intact / wreck.
- **Separate parts for things that move or hide**: truck door leaves (pivot on the hinge line), case lid, reel
  with its tape box, progress bar, beacon lens.
- The catalogue items that are never placed (`traffic_light`, `sign_post`, `fence_panel`, `fence_tall`,
  `awning`, the tipped trolley, the lowered lift) are briefed at priority 3: build them only if the level
  dressing pass wants them.
- Things on the street that are **not** catalogue props and belong to the level spec: the two rolling repair
  scaffolds, the two shut kiosks, the tyre cage, the produce stand, the utility dig with its steam stack, the
  site shanty, the hoist tower (src/level/street.js:199-225, 233-249, 253-382), the lot's barrier arm and PARK sign
  pole (src/level/yards.js:403-417), the loading dock (src/level/yards.js:355-362), the shop's extractor fan and the
  office safe (src/level/shop.js:138-156, 201-202).

### 5.2 What must be textured

- Surfaces map to the shared texture sets by the catalogue names in 2.12; vehicles get unique sets.
- **Livery and label art** has to be redrawn at print quality from the descriptions in 2.4.4, 2.4.6, 2.5 and
  2.11: the IPX flank livery, lozenge and address; the IPX one-sheet; the billboard face; the Vulture stencil
  and scrawls; the taxi door lettering, checker band and roof light; five plates; the reel box label and flange
  art; the tracker tag and LCD; the gas diamond and the gas placard; every sign, label and stencil in 2.11. All
  strings are listed there; none may be replaced by a real brand.
- The IPX wordmark is a typeset stand-in. Keep it a swappable texture so the real logo can replace it
  everywhere at once.
- Paint: the nine-colour vehicle chart, taxi yellow, IPX gloss black, the four primers, rust and char (2.4.3).
- Wear appropriate to a hot afternoon on a working block: dust on horizontal surfaces, brake dust, stone chips,
  sun-faded plastics; the source carries only a few painted tags and stencils.

### 5.3 What must be animated

- IPX truck: two door leaves, 108.9° in 1.1 s; hazard lamps blinking at 1.1 s; a vault light.
- Reel case: lid dropping shut in 0.3 s; a progress bar growing left to right; a pulsing beacon, shaft and
  ground glow; a five-segment meter on the boombox flickering at about 1.5 Hz.
- Lit explosive: a 2° rattle that grows with the fuse.
- Open hydrant: a breathing water jet. Traffic signal: lamp switching (if used).
- Nothing else moves. Loose clutter is not simulated in the source (cones have no collision at all).

### 5.4 What must be simulated or built as effects

- A gas-flame jet (0.75 to 0.9 m, scale 0.9 / 1.2), the blast, and the swap to a scorched wreck for the two
  explosives; a heat glow on the lit shell.
- The reel beacon: a gold shaft of light 6 m tall that widens with distance, and a 1 m gold glow on the ground;
  in daylight the mast and lens silhouette do most of the work, so the lens must be visibly emissive against a
  bright street.
- The hydrant's water arc, mist and wet patch (4 m reach).
- Optional, from the unused anchors: steam off the food cart's pan, smoke off the burned car's engine bay,
  exhaust haze at the generator and the truck.

### 5.5 What must be recorded or synthesised

Sounds the source already plays for props:

- the **boombox loop** at each untaken reel: the game's own beat through a small overdriven speaker, phase-locked
  to the music, volume 0.95, reference distance 2.2 m, roll-off 1.25, placed 0.6 m above the reel's ground point
  (src/audio/music.js:324-325, 424; src/audio/ambience.js:211-229);
- the **gas hiss** loop on a lit explosive, volume 0.25 rising to 1 with the square of the fuse progress
  (src/explosives.js:30, 254-263, 441), and the explosion;
- reel grab and reel secure cues, and bullet impacts by surface: `car` (sheet metal), `glass`, `metal`,
  `concrete`, `wood`, `rubber`, `cloth`, `dirt`.

Sounds the source does not have and a photoreal build will be judged without: the truck idling, its hazard
relay, the vault doors swinging and latching, the case lid dropping, water from the hydrant, the generator. They
are additions, not parity (section 6).

---------------------------------------------------------------------------------------------------

## 6. Open questions and risks

1. **Front axis of furniture.** This spec keeps the web local frame for every asset (length +X, front −Y in
   Blender, +Y in Unreal) so that one yaw rule places everything and every local number converts directly. If
   the asset pipeline instead turns furniture fronts to +X, every such placement needs +90° and every local box
   in Appendix B must be turned too. All pipelines must agree before assets are exported.
2. **Resupply has no object.** The source applies ammunition and health directly; the radio line says "at your
   feet". Should the rebuild drop a visible resupply crate? Nothing in the source sizes or places one.
3. **The "jack-knifed" truck is a rigid box truck turned 60°.** A rigid truck cannot jack-knife. Keep it as a
   slewed truck, or replace it with an articulated wreck of the same collider footprint?
4. **Car glass stops bullets and never breaks.** Parity keeps cabins as hard cover. Photoreal expectations
   suggest breakable glass; making it penetrable would change cover on every lane.
5. **Paint snapping.** Rule's SUV and the Vulture van are asked for deeper blacks than the chart gives
   (`#0b0c0e` and `#16181b` become `#14161a`). Ship the effective colour or the intended one?
6. **Plates repeat.** Four codes serve 32 vehicles (the three cabs share a fifth); all ten plain vans carry
   `TKV·9907` and stand within sight of each other. More invented codes are needed for close-up realism; they must pass the same rules as
   the source's test.
7. **Unused anchors.** Steam at the food cart, smoke at the burned car, exhaust at the generator and the idling
   truck are prepared in the data but never shown. Add them?
8. **Unseeded picks depend on the world seed.** Appendix A is the seed-1994 block. If the Unreal build keeps a
   seed option, the factory's draw order must be reproduced exactly; baking is far safer.
9. **Reel proportions.** The label says two-inch tape, but the modelled reel is 38 mm thick. A real two-inch
   reel of this diameter is about 57 mm across the flanges. Follow the label or the mesh?
10. **Propane cylinder class.** 0.30 m across and 0.585 m tall is taller than the common barbecue cylinder and
    close to the next size up. Model the real cylinder nearest the collider (0.32 × 0.60) rather than a named
    product.
11. **Motorbike side stand** is on the wrong side in the source; the rebuild should lean the bike onto its stand.
12. **Lamp intensities** are the web engine's numbers and are further scaled by the atmosphere module; they are
    relative weights, not photometric values.
13. **`NYC TAXI`, `NEW YORK` plates and a 718 area code** are real-world references that the source's own copy
    test allows (real places). Confirm with the brand partner that generic taxi lettering is acceptable.
14. **Props without collision that a player will expect to touch**: cones, the mattress, single pallets, the
    Vulture van's open doors, tree crowns. Parity keeps them intangible.
15. **The truck's sounds and exhaust** do not exist in the source (5.5). A silent idling armoured truck will
    read as a bug in a photoreal build.
16. **Box colliders are bigger than the shapes.** A sedan's body box is 1.08 m high over a bonnet that is 0.90 to
    1.00 m; a van is one box that includes the air over its sloped nose; chain-link fence props are solid slabs.
    In the source rounds stop on these boxes in thin air. Keeping the boxes keeps the tuned cover; tracing the
    render mesh instead looks right but opens sight lines the level was not balanced for.

---------------------------------------------------------------------------------------------------

## Appendix A — Every placement (web coordinates, world seed 1994) **(measured)**

`(x, z)` in metres, then `y` when the prop does not stand on the local floor (0 on the roadway and yards, 0.15
on sidewalk slabs), then `@ yaw` in **web degrees** (omitted when 0; Unreal yaw is the negative), then the
seed-picked variant `[vN]` or the asked variant. Sources: src/level/street.js:38-162, 351-352, 383-386, 411-418,
440-448, 532-541; src/level/yards.js:38-46, 76-80, 162-181, 298-313, 363-379, 403, 442-469; src/level/shop.js:128,
199-200, 238-244, 253-287, 326-327; src/level/buildings.js:222, 284-286, 308-310, 326-327, 365-366, 397;
src/level/ground.js:189-190; src/level.js:100. The exported placement data carries the same list with full precision.

| Prop | Count | Placements |
|---|---|---|
| `ac_unit` | 12 | (−31, −15, y 16.2 @ 17.2°) (−33.5, −27, y 16.2 @ 68.8°) (14, −15, y 10) (18.5, −22, y 10 @ 90°) (−41, 15, y 10) (−34, 22, y 10 @ 45.8°) (−27, 16, y 13.1) (1, 15, y 6.9) (9.5, 22, y 6.9 @ 90°) (17, 14.5, y 6.9 @ 22.9°) (−15, −27, y 6.3) (2.5, −14.5, y 6.3 @ 90°) |
| `barricade` | 6 | (−41.3, −2.3 @ 104.3°) (−41.5, 2.7 @ 78.6°) (41.6, −6.4 @ 8.6°) (37.4, 4.4 @ −17.2°) (−11.9, −3.6 @ 14.3°) (2.9, −3.8 @ −11.5°) |
| `bench` | 5 | (28.6, −12.95) (40.6, −12.95) (30.4, −11.55) (−33.6, 10.5 @ 180°) (−27.1, 10.5 @ 180°) |
| `billboard` | 1 | (40.7, 12.4) |
| `bleachers` | 3 | (29.6, −31.7) (35.25, −31.7) (40.9, −31.7) |
| `bollard` | 4 | (−15.45, −10.65) (−8.55, −10.65) (−3.65, −10.65) (1.05, −10.65) |
| `box_truck` | 3 | (41.4, 0.3 @ 60.2° [v1]) (−19.2, −2.4 @ −16° [v0]) (5.85, 2.35 @ 16° [v0]) |
| `burned_car` | 1 | (−11.2, 18.6 @ 51.6°) |
| `bus_shelter` | 1 | (29.2, −8.05) |
| `car_lift` | 2 | (−19.2, −17.3 @ 90° [v1]) (−1.3, −19.6 @ 90° [v1]) |
| `car_on_stands` | 1 | (−12.2, −15.4 @ 96.9°) |
| `cardboard_boxes` | 9 | (−22.8, −26.4 @ 17.2° [v1]) (1.4, −27.6 @ 28.6° [v0]) (10.3, −23.6 @ 11.5° [v1]) (22.6, −31.9 @ 34.4° [v0]) (43.3, −17.2 @ 22.9° [v1]) (−14.8, 19 @ 17.2° [v1]) (7, 26.6, y 1 @ 17.2° [v1]) (2.2, 8.4, y 2.95 @ 22.9° [v0]) (8.5, 10.45 @ 5.7° [v1]) |
| `compressor` | 2 | (−16.6, −26.6 @ 90°) (3.6, −11.9) |
| `court_light` | 2 | (25.6, −12.95) (44.8, −32.3) |
| `crate_wood` | 8 | (−13.4, −20.9 @ 11.5° [v0]) (2.6, −15.2 @ 22.9° [v1]) (32.7, −21.3 @ 28.6° [v1]) (−6.2, 19.1 @ 22.9° [v0]) (4.5, 30.4 @ 11.5° [v1]) (42.4, 14.4 @ 17.2° [v1]) (17.2, 10.2, y 2.95 @ 11.5° [v0]) (−2.4, 4.25 @ 17.2° [v1]) |
| `dumpster` | 6 | (10.3, −12.95 @ 90° [v1]) (6.72, −27.3 @ 90° [v0]) (22.62, −16.4 @ 90° [v1]) (−2.3, 26.62 [v0]) (−1.7, 30.38 [v0]) (44.9, 23.6 @ 90° [v0]) |
| `engine_hoist` | 2 | (−9.9, −25.3 @ 11.5°) (−16.9, −12.7 @ 68.8°) |
| `fire_escape` | 11 | (−30.6, −10.45, y 4.05) (−30.6, −10.45, y 7.15) (−30.6, −10.45, y 10.25) (−30.6, −10.45, y 13.35) (10.45, −20.5, y 4.05 @ −90°) (10.45, −20.5, y 7.15 @ −90°) (−42.5, 10.45, y 4.05 @ 180°) (−42.5, 10.45, y 7.15 @ 180°) (−27, 10.45, y 4.05 @ 180°) (−27, 10.45, y 7.15 @ 180°) (−27, 10.45, y 10.25 @ 180°) |
| `floodlight_stand` | 3 | (−9.6, 13.3 @ 180°) (−44.65, −2.9 @ −90°) (44.2, 7.9 @ 90°) |
| `food_cart` | 1 | (−5.7, −8.3) |
| `generator` | 1 | (−44.68, 3.1 @ 90°) |
| `hoop` | 2 | (26.25, −22.5) (44.25, −22.5 @ 180°) |
| `hydrant` | 2 | (37.4, −7.5) (38.2, 7.5) |
| `hydrant_open` | 1 | (−12.25, 7.34 @ 180°) |
| `ipx_truck` | 1 | (41.3, 29.7) |
| `jersey_barrier` | 16 | (31.4, 28.6 @ 98.6° [v2]) (41.6, 25.9 @ 5.7° [v1]) (−43.55, −4.6 @ 90° [v0]) (−43.55, −1.55 @ 90° [v0]) (−43.55, 1.5 @ 90° [v0]) (−43.55, 4.55 @ 90° [v1]) (43.9, −5.5 @ 90° [v0]) (43.9, 5.6 @ 90° [v1]) (38.9, −5.3 @ 14.3° [v1]) (18.4, 5.02 [v0]) (21.5, 5.02 [v1]) (−1.1, 3.1 @ 4.6° [v2]) (1, −1.9 @ 95.7° [v2]) (10.6, −2.3 @ 2.9° [v2]) (27.6, 2.6 @ 90° [v0]) (28.4, −2.9 @ 101.5° [v1]) |
| `lot_booth` | 1 | (27.3, 12.55) |
| `mailbox` | 2 | (−32, −7.7 [v1]) (9.6, −7.7 [v0]) |
| `manhole` | 6 | (−22.5, −1.8 @ 128.9°) (−9.5, 2.6 @ 14.3°) (6.4, −2.4 @ 139.3°) (18.6, 1.9 @ 146.3°) (30.5, −0.9 @ 131°) (−36, 2.2 @ 24.8°) |
| `master_case` | 3 | (−4, 1 @ 20.1°) (−9.5, −21.5 @ −28.6°) (35.25, −22.5 @ 63°) |
| `mattress` | 1 | (−6.3, 14.3 @ 17.2° [v1]) |
| `milk_crates` | 10 | (−9.2, −18.2 [v2]) (10.45, −19.9 [v0]) (22.5, −30.6 [v0]) (37.3, −24.7 [v1]) (−8.9, 24.1 [v0]) (13.9, 26.45 [v1]) (14.4, 10.5 [v0]) (0.1, 1.2 [v1]) (−19.7, 10.5 [v1]) (−18.9, 10.45 [v0]) |
| `motorbike` | 3 | (31.3, −22.9 @ 71.6°) (−5.7, −6.35 @ 4.6°) (−14.6, 3.6 @ 28.6°) |
| `newspaper_box` | 7 | (−31.2, −7.62) (1.7, −7.62) (26.2, −7.62) (−40.1, 10.5 @ 180°) (−21.7, 7.62 @ 180°) (−21.1, 7.62 @ 180°) (26.9, 7.62 @ 180°) |
| `oil_drum` | 14 | (−17.2, −30 [v1]) (−16.4, −29.7 [v1]) (−12.1, −19.4 [v0]) (−11.4, −20.1 [v0]) (−4.2, −11.95 [v0]) (6.55, −17.6 [v1]) (32.5, −24.6 [v0]) (−8.3, 15.9 [v1]) (−15.2, 27.1 [v0]) (−14.5, 27.8 [v0]) (34.4, 27.3 [v0]) (44.2, 2.7 [v0]) (43.7, 3.4 [v0]) (−16.8, −9.6 [v1]) |
| `pallet` | 4 | (7.1, −14.6 @ 17.2°) (23.4, −13.6 @ 11.5°) (−13.3, 19.9 @ 28.6°) (8.6, 10.2, y 2.95) |
| `pallet_stack` | 9 | (−19.4, −29.8 [v1]) (2.9, −29.6 @ 5.7° [v0]) (10.25, −26.4 @ 90° [v1]) (35.9, −26.4 @ 8.6° [v0]) (11.7, 26.7, y 1 [v0]) (−13.8, 30.3 @ 5.7° [v1]) (33.2, 26.6 @ 11.5° [v0]) (34.6, 32.8 @ 5.7° [v0]) (−44.68, 0.3 @ 90° [v0]) |
| `parking_meter` | 8 | (−34.2, −7.42) (−24.6, −7.42) (9.2, −7.42) (33.6, −7.42) (−26.6, 7.42) (1.6, 7.42) (7.6, 7.42) (39.9, 7.42) |
| `phone_booth` | 3 | (−44.5, −10.25 [v1]) (−29.2, 10.25 @ 180° [v0]) (27.3, 10.25 @ 180° [v1]) |
| `pickup` | 2 | (17.4, 29.85 @ 180° [v0]) (25.2, 23.3 [v0]) |
| `planter` | 3 | (32.1, −11.4 [v1]) (36.9, −11.4 [v0]) (39.6, 10.25 [v1]) |
| `porta_potty` | 2 | (−6.8, 7.66 @ 90°) (−6.8, 8.86 @ 90°) |
| `sandbags` | 5 | (34.1, −19.1 @ 14.3° [v1]) (5.4, 7.9, y 2.95 [v0]) (12.8, 7.9, y 2.95 [v1]) (−4.3, −2.9 @ 5.7° [v1]) (20.4, 2 @ 90° [v1]) |
| `sedan` | 13 | (−19.2, −17.3, y 1.95 @ 90° [v2]) (−1.3, −19.5 @ −90° [v1]) (24.95, 15.5 @ 180° [v2]) (36.5, 23.6 @ 180° [v0]) (24.5, 31.6 @ −90° [v3]) (29.7, 31.55 @ 90° [v1]) (−27.4, −5.98 @ 180° [v1]) (13.6, −5.98 @ 180° [v0]) (31.4, −5.98 @ 180° [v3]) (4.6, 5.98 [v2]) (39.6, 5.98 [v0]) (−35.2, −2.3 @ 24.1° [v0]) (33.8, 2.3 @ 17.2° [v1]) |
| `shelf_rack` | 5 | (−0.4, −30.05 [v0]) (5.05, −28.5 @ 90° [v0]) (5.05, −25.4 @ 90° [v0]) (5.05, −17.3 @ 90° [v1]) (−23.05, −22.3 @ 90° [v1]) |
| `shopping_cart` | 5 | (28.4, −16.6 @ 40.1°) (−7.4, 21.9 @ 68.8°) (−5.4, 23.4 @ 149°) (−14.2, 22.8 @ 28.6°) (40.6, 14.9 @ 45.8°) |
| `street_lamp` | 9 | (39.3, 13.95 [v1]) (30.9, 33.45 @ 180° [v1]) (−22.4, −7.62 @ 180° [v1]) (2.6, −7.62 @ 180° [v1]) (23.9, −7.62 @ 180° [v1]) (41.6, −7.62 @ 180° [v1]) (−31.4, 7.62 [v0]) (22.9, 7.62 [v0]) (36.4, 7.62 [v0]) |
| `suv` | 2 | (25.05, 18.1 @ 180° [v0]) (−40.5, 5.98 [v0]) |
| `taxi` | 3 | (36.5, 15.8 @ 180°) (4, −5.98 @ 180°) (−24.6, 5.98) |
| `tire_stack` | 14 | (−22.6, −29.6 [v0]) (−21.6, −29.9 [v0]) (−6.5, −23.4 [v1]) (−7.3, −24.1 [v0]) (−8.2, −12 [v0]) (−7.3, −12.1 [v1]) (37.8, −20.2 [v0]) (38.6, −20.9 [v1]) (−14.7, 14.1 [v0]) (−13.8, 14.9 [v1]) (39.6, 26.4 [v1]) (−7.6, −2.5 [v1]) (15.2, 2.6 [v1]) (−17.3, −10.4 [v1]) |
| `tool_chest` | 4 | (−23.1, −28.2, y 2.8 @ 90°) (−7.1, −19.5 @ 22.9°) (−12.6, −23.1 @ 77.3°) (−4.6, −30.22) |
| `traffic_barrel` | 13 | (30.6, 16.9) (31.4, 17.6) (−43.6, −6.45) (−43.6, 6.4) (23.6, 5.1) (16.4, 5.1) (−13.6, −2.9) (−12.9, −2.1) (9.9, −0.5) (12.6, −0.3) (30.2, 0.4) (31, −0.3) (30.4, −1.2) |
| `traffic_cone` | 10 | (−42.1, −3.9 @ −172.6°) (−42.4, 0.4 @ −18.4°) (−41.9, 4.3 @ 20.7°) (−13.9, −0.6 @ 180°) (−24.2, 0.9 @ 175.2°) (11.9, −0.9 @ 117.3°) (13.4, 1 @ 25.8°) (29.4, 1.6 @ 46.4°) (39.2, 4.2 @ −158.3°) (38.6, −6.2 @ 97.4°) |
| `trash_bags` | 13 | (10.2, −18.3 @ 22.9° [v1]) (6.9, −29.6 @ 108.9° [v0]) (22.7, −19 @ 68.8° [v2]) (−5.1, 12.4 @ 11.5° [v2]) (−15, 24.8 @ 80.2° [v1]) (1.5, 30.4 @ 17.2° [v1]) (21.1, 26.7 @ 63° [v0]) (44.7, 32.9 @ 34.4° [v2]) (−25.4, 1.6 @ 40.1° [v0]) (−6.2, 4.3 @ 28.6° [v2]) (6.2, −3.3 @ 63° [v2]) (−41.2, 10.3 @ 11.5° [v2]) (−13.6, 10.3 @ 51.6° [v1]) |
| `trash_can` | 6 | (31.3, −12.9) (3.3, 10.45) (−42.2, −10.4) (−36.4, 7.68) (−22.7, 7.68) (41.4, 7.68) |
| `tree` | 3 | (39.8, −8.3 [v1]) (25.4, 8.3 [v0]) (43.2, 8.3 [v2]) |
| `van` | 11 | (−7.6, 29.6 @ 2.3°) (36.6, 18.4) (−38.2, −5.98 @ 180°) (−20.2, −5.98 @ 180°) (19.4, −5.98 @ 180°) (−18.9, 5.98) (−3, 5.98) (13.4, 5.98) (−9.4, 1.8 @ −148.5° [vulture]) (16.3, −2.6 @ 31.5°) (36.9, −2.5 @ −174.2°) |
| `vending_machine` | 2 | (5.1, −13.2 @ −90°) (3.5, −10.55) |
| `water_tower` | 3 | (−40, −24, y 16.2) (16.5, −29, y 10) (−23, 24, y 13.1) |
| `workbench` | 3 | (−21.2, −29.9, y 2.8) (−6.5, −30.1) (−21.6, −11.95) |

## Appendix B — Collider boxes in Unreal local space (cm)

X = along the length (web x), Y = across (web z), Z = up (web y); pivot at the footprint centre on the ground.
Default shape of each prop; variants with different boxes are listed separately. `propane_tank` and
`welding_rack` show the builder's boxes: the game uses the effective boxes of 2.5.2 instead.

| Prop | X | Y | Z | Surface | Flags |
|---|---|---|---|---|---|
| `sedan` | −230…230 | −88.5…88.5 | 0…108 | car |  |
|  | −126…64 | −74.1…74.1 | 108…145 | glass |  |
| `taxi` | −230…230 | −88.5…88.5 | 0…108 | car |  |
|  | −126…64 | −74.1…74.1 | 108…145 | glass |  |
| `suv` | −245…245 | −96…96 | 0…124 | car |  |
|  | −222.5…72.5 | −83.2…83.2 | 124…178 | glass |  |
| `pickup` | −265…265 | −96…96 | 0…127 | car |  |
|  | −45…97 | −80…80 | 127…178 | glass |  |
| `van` | −260…260 | −96…96 | 0…214 | car |  |
| `box_truck` | −364…112 | −120…120 | 0…330 | car |  |
|  | 112…370 | −106…106 | 0…228 | car |  |
| `burned_car` | −225…225 | −88…88 | 0…96 | car |  |
|  | −130…65 | −72…72 | 96…130 | car | bullets only |
| `ipx_truck` | −340…55 | −117…117 | 0…286 | car |  |
|  | 55…340 | −117…117 | 0…258 | car |  |
| `motorbike` | −98…98 | −30…30 | 0…95 | metal |  |
| `food_cart` | −98…78 | −50…50 | 0…125 | metal |  |
|  | −95…75 | −50…50 | 185…225 | cloth | bullets only, no nav |
| `jersey_barrier` | −150…150 | −30…30 | 0…81 | concrete |  |
| `traffic_barrel` | −28…28 | −28…28 | 0…98 | rubber |  |
| `traffic_cone` | — | — | — | — | no collision |
| `barricade` | −120…120 | −25…25 | 0…100 | wood |  |
| `dumpster` | −95…95 | −55…55 | 0…130 | metal |  |
| `trash_can` | −29…29 | −29…29 | 0…95 | metal |  |
| `trash_bags` | −66…68 | −48…46 | 0…62 | cloth |  |
| `mailbox` | −27…27 | −25…25 | 0…120 | metal |  |
| `newspaper_box` | −24…24 | −21…21 | 0…108 | metal |  |
| `hydrant` | −16…16 | −16…16 | 0…74 | metal |  |
| `hydrant_open` | −16…16 | −16…16 | 0…74 | metal |  |
| `phone_booth` | −45…45 | −45…36 | 0…220 | metal |  |
| `bus_shelter` | −176…176 | −69…−63 | 0…230 | glass |  |
|  | −180…−164 | −63…63 | 0…220 | metal |  |
|  | −45…145 | −60…−24 | 0…50 | wood |  |
|  | −180…180 | −75…75 | 238…248 | metal | no nav |
| `street_lamp` | −13…13 | −13…13 | 0…730 | metal |  |
| `traffic_light` | −14…14 | −14…14 | 0…555 | metal |  |
| `parking_meter` | −9…9 | −9…9 | 0…130 | metal |  |
| `bench` | −88…88 | −26…26 | 0…47 | wood |  |
|  | −88…88 | −30…−18 | 47…85 | wood |  |
| `planter` | −60…60 | −60…60 | 0…80 | concrete |  |
| `tree` | −30…30 | −30…30 | 0…55 | metal |  |
|  | −14…14 | −14…14 | 55…300 | wood |  |
| `bollard` | −9…9 | −9…9 | 0…100 | metal |  |
| `sign_post` | −4…4 | −4…4 | 0…280 | metal |  |
| `fence_panel` | −150…150 | −4…4 | 0…240 | metal |  |
| `fence_tall` | −150…150 | −4…4 | 0…400 | metal |  |
| `manhole` | — | — | — | — | no collision |
| `milk_crates` | −34…34 | −34…34 | 0…90 | rubber |  |
| `pallet` | −60…60 | −50…50 | 0…14.4 | wood |  |
| `pallet_stack` | −60…60 | −50…50 | 0…115 | wood |  |
| `crate_wood` | −55…55 | −45…45 | 0…100 | wood |  |
| `cardboard_boxes` | −50…50 | −40…40 | 0…72 | wood |  |
| `shopping_cart` | −45…45 | −26…26 | 0…95 | metal |  |
| `shopping_cart (tipped)` | −50…50 | −50…50 | 0…50 | metal |  |
| `mattress` | — | — | — | — | no collision |
| `tire_stack` | −39…39 | −39…39 | 0…98 | rubber |  |
| `oil_drum` | −29…29 | −29…29 | 0…90 | metal |  |
| `sandbags` | −100…100 | −30…30 | 0…90 | dirt |  |
| `generator` | −110…110 | −50…50 | 0…122 | metal |  |
| `floodlight_stand` | −22…22 | −22…22 | 0…215 | metal |  |
| `porta_potty` | −60…60 | −60…60 | 0…225 | rubber |  |
| `boombox` | — | — | — | — | no collision |
| `car_lift` | −20…20 | 124…156 | 0…350 | metal |  |
|  | −20…20 | −156…−124 | 0…350 | metal |  |
| `car_lift (car)` | −20…20 | 124…156 | 0…350 | metal |  |
|  | −20…20 | −156…−124 | 0…350 | metal |  |
|  | −230…230 | −88.5…88.5 | 215…303 | car | no nav |
|  | −126…64 | −74.1…74.1 | 303…340 | glass | no nav |
| `car_on_stands` | −225…225 | −88…88 | 0…123 | car |  |
|  | −126…64 | −73.7…73.7 | 123…160 | car |  |
| `tool_chest` | −54…54 | −27…27 | 0…109 | metal |  |
| `workbench` | −110…110 | −39…39 | 0…80 | wood |  |
| `engine_hoist` | −70…−50 | −10…10 | 0…160 | metal |  |
|  | 4…77 | −30…30 | 85…138 | metal |  |
|  | −70…76 | −55…55 | 0…16 | metal |  |
| `shelf_rack` | −135…135 | −45…45 | 0…300 | metal |  |
| `compressor` | −55…58 | −28…28 | 0…90 | metal |  |
| `vending_machine` | −45…45 | −40…38 | 0…185 | metal |  |
| `hoop` | −86…−70 | −8…8 | 0…340 | metal |  |
|  | 7…15 | −60…60 | 290…400 | metal | no nav |
| `bleachers` | −200…200 | 49.5…98.5 | 0…42 | metal |  |
|  | −200…200 | 0.5…49.5 | 0…78 | metal |  |
|  | −200…200 | −48.5…0.5 | 0…114 | metal |  |
|  | −200…200 | −97.5…−48.5 | 0…150 | metal |  |
| `court_light` | −14…14 | −14…14 | 0…855 | metal |  |
| `lot_booth` | −110…110 | −90…90 | 0…237 | metal |  |
| `billboard` | −280…−240 | −40…0 | 0…670 | metal |  |
|  | 240…280 | −40…0 | 0…670 | metal |  |
|  | −450…450 | −10…60 | 630…1080 | metal | no nav |
| `water_tower` | — | — | — | — | no collision |
| `ac_unit` | −60…60 | −45…45 | 0…86 | metal |  |
| `fire_escape` | — | — | — | — | no collision |
| `awning` | — | — | — | — | no collision |
| `master_case` | −45…3 | −30…30 | 0…66 | metal |  |
|  | 3…45 | −30…30 | 0…35 | rubber | bullets only |
|  | 3…45 | −30…30 | 0…66 | — | player only |
| `propane_tank` | −16…16 | −16…16 | 0…60 | metal |  |
| `welding_rack` | −45…45 | −25…25 | 0…150 | metal |  |
