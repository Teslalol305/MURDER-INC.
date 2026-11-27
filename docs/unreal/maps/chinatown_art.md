# Canal Street art, rounds 2 and 3: the other buildings, the signs, the props, the fitted structures, the decals and the LODs (lane A-CT)

What MAPS.md lane A-CT added without Unreal and without the box (2026-11-26), measured against
[chinatown.md](chinatown.md) 4, 13 and 14 and the level data `tools/levels/data/level_chinatown.json`. Round 1 (the kit, the
atlas, the north row N1 to N6) is in `art/blender/README.md`. The code is `art/blender/assets/chinatown.py` and its
`_chinatown_*.py` modules; the outputs are in `art/out` (git-ignored), the pictures in `art/previews/maps/ct_*.jpg`.

```
venv/bin/python art/blender/build.py build chinatown --export                 # 195 meshes, placements, fit report (about 80 s)
venv/bin/python art/blender/build.py build chinatown --export --preview --samples 12   # ct_canal_start, _east, ct_mott,
                                                                               #   ct_square, ct_alley, ct_yard + the round-1 views (8 min)
venv/bin/python art/blender/assets/_chinatown_check.py [--build]               # the lane's checks
```

## 1. What was placed

1947 instances (art/out/placements/placements_chinatown.json), all pure arithmetic on the level's faces
(`_chinatown_streets.py`, no Blender): every building face the player sees is a `Face` (wall plane, outward normal, start,
length) and modules run along it.

| Building | Faces | Ground storey |
|---|---|---|
| W1 (6 storeys) | Canal front, Lantern Alley A wall | the shut hardware store, KioskPhones narrow front, the residents' entrance; the alley wall: three back doors, windows, escapes on bays 1, 4, 6 |
| W3, MOON GATE BAKERY (5) | Canal (the 7.2 m bakery front with its 2.0 m doorway), Mott, the rear and west walls over the kitchen and market roofs | display windows and a held-open door (`SM_Facade_Shopfront_CT_Bakery`) |
| S1, S2, S3 | the backs on Lantern Alley B; S3's Mott front | back doors, barred windows; S3 Mott: jewellery, a coach office door, grocery |
| E1a, E1b | Canal, Mott and Square fronts, the two arcade mouths (a 4.2 m brick head over each) | restaurant with awning, jewellery, grocery, kiosks |
| Arcade | its two side walls: three kiosks behind glass west, the workshop door (BIG LIGHT SIGNS) east | kiosk fronts |
| E2, the banquet hall | `SM_Struct_CT_BanquetFacade` (see 3) | |

North-row alcoves are now the real recess (`SM_Facade_CT_Alcove_<brick>`: 2.4 m opening, 1.0 m deep, soffit at 2.85 m, the
residents' door in the back wall), replacing the flat entrance. Every wide end pier is made of piers of at most 4.2 m; no
end fill, pier or cornice end is narrower than 0.15 m (E1a's Mott face uses four bays so its fills are 1.65 m, not 0.10).

**No instance is scaled** (checked: 0 of 1947). Piers, fills, parapet fills, cornice ends and fascias are built at the width
the table needs; the ground bays, heads and alcoves are their own meshes.

**Signs.** Every sign of lane D's `signage` list that is not on the north row is placed on its face, except the market's exit box (drawn
into the hall's shell); the decals (graffiti, the alley stencil) are placed since round 3 (4b). 32 shop fronts, every
one with a sign over it (a check). Lane D's points the art moved, each with its reason in the instance (`deviation`):
SEVEN STARS COACH (its 8 m band overlapped both neighbours: mounted on the second storey over the office door), the opera
poster (its point was in the middle of Lantern Alley A: on W1's alley wall at the same z), the rooftop letters (centred on
lane D's four legs), the lanterns (hung at 6.25 m, clear above the banquet band), arcade kiosk 3 (1.05 m out in the aisle:
on the east wall over the one front without another sign). Fronts lane D gave no sign get a generic lightbox or stall board
(KEYS CUT, WATCH REPAIR, ROAST MEAT, FRUIT...: words with no name to search).

**Props** (172 groups on lane D's `propPlacements`): stall counters in four rows with goods, tarps and pendant bulbs, fish
counters with tank and scale, vendor tables with goods, garment rails, crates, pallets, cones, drums, boxes, newspaper boxes,
lamps (arm over the roadway), card tables with stools, benches, hoops, signposts, meters, skylights, condensers. Each tiles
along its collider's long side; the worst overhang is 1.05 m (a 3 m jersey barrier on a shorter box). Round 3 (4b) placed the carts, lions, bags, fruit stand, standpipes, bike racks, chair stacks, grease bins, vents and fans,
the planters, the interiors and the stage. The fixer pass (4c) placed the vehicles and every piece that had a collider and no mesh
(newsstands, shop displays, laundry carts, vendor stools, goods cartons, steam chimneys, alarm pedestals, the phone kiosk, raised beds,
chess tables, shed posts, the scale stand, the arcade pillar). Still not placed, with the reason in `unmappedProps` in the placements
file: the ground air conditioners (no mesh), the barricade (2.4 m against a 1.2 m collider), the tape shelf (0.65 x 2.4 x 2.0 m), the
gas cage frame and the newsstand bundle (small, no mesh).

## 2. Far proxies

`SM_Facade_CT_Far_<building>` now exists for every facade building (N1..N6, W1, W3, S1, S2, S3, E1a, E1b), 10k triangles
each, drawn past 30 m; round-2 proxies keep their world yaw and sit at their first face's start.

## 3. Structures fitted to lane D's colliders

Eight meshes, each measured vertex by vertex against its colliders (tolerance 15 mm, plus named allowed regions for overhead
art, coping, gate hoods and door leaves folded against a wall): 4702 vertices outside the colliders, all inside a named
allowed region, 0 unexplained (`art/out/chinatown/fit_chinatown.json`, check `fit`). Pivot = the colliders' min corner;
placed at that point, yaw 0.

| Mesh | Triangles / cap | What |
|---|---|---|
| `SM_Struct_CT_MarketHall` | 13.9k / 40k | the shell: block walls with the three Canal gates (rolled up under a corrugated fascia), the 1.0 m side door, the rear roll-up, roof slab with gravel, parapets and coping, floor, tile wainscot, four steel beams, fluorescent rows, skylight wells, the green exit box, B0 the storeroom |
| `SM_Struct_CT_YardStair` | 4.5k / 12k | the climbable switchback on its 26 step boxes: diamond-plate treads, stringers, landings on posts, 48 mm rails inside the player-only guards, the solid space under it closed with sheeting |
| `SM_Struct_CT_SidewalkShed_Mott` | 2.0k / 10k | plywood deck and parapet with the missing panel (drop R2), pipe posts in their boxes, joists and lamps |
| `SM_Struct_CT_BakeryKitchen`, `_Arcade`, `_BanquetFacade`, `_ColdRoom`, `_RoofBulkhead_B0` | see the manifest | the one-storey kitchen with its walkable roof, the arcade soffit and frieze, E2's stucco fronts with the red lacquer doors and the raised dub-room roll-up, the cold room with its strip curtain, the roof Goons' door |

## 4. Checks (`_chinatown_check.py`, all pass)

english, names, files (195 assets), budgets (every asset within 13.2; the new rows: alcove 9k, ground bay 4k, struct caps
above), atlas, **fit** (0 unexplained), **stretch** (0 scaled), **signs** (32 of 32 fronts), **props**, placements (209
meshes, none unknown), **views**, block (Block files unchanged); with `--build`: validation (195 assets, 0 failing), budgets,
thin members (none under 34 mm). `tools/levels/check_level.py --level chinatown`: 0 failures. The level data was not changed.

**The worst view** (the start, looking east, every placed piece in the frustum): 3.11 M triangles at LOD0, **0.88 M with the
far proxies** past 30 m and the props' LOD1s past 12 m: under the 1.5 M ceiling and **under the 1.1 M aim** (it was 1.18 M).
The north row's share is 413k (at most 0.55 M).

## 4a. Review fixes (2026-11-26, round 2b)

- **Prop LODs** (`_chinatown_lod.py` PROP_LODS, built by `build_prop_lods`): `<name>_LOD1` for the trash can, stall counter,
  milk crate, vendor table, cardboard boxes, fish counter, citrus display, clothing rail, dry goods and traffic cone, each
  about a quarter of its triangles, switched at 12 m (Unreal: the static mesh's LOD1, same slots). The pallet stack and the
  dumpster have none: their boards and sheets collapse to slivers under the 34 mm floor. `SM_Prop_CT_Hydrant` is the Block's
  hydrant collapsed from 46k to 4.5k (same size and pivot, with a 1.1k LOD1) and is now placed on the 4 hydrant colliders.
  The view counter (`view_triangles`) draws a prop's LOD1 past `PROP_LOD_SWITCH`.
- **Street surface** (`_chinatown_street_look.py`): the roadway was a mirror. Asphalt and concrete are now procedural surfaces
  with roughness variation (puddles, polished tyre tracks in the four wheel paths, cracks, grain bump, oil spots; slab
  joints, damp patches and gum on the concrete), plus the dressing as thin shapes: double yellow centre line, two zebra
  crossings and stop lines, gutters, a patched utility trench and three asphalt patches, five manholes and six drain
  inlets, a heaved sidewalk seam. The same 43 rows in web coordinates are in `tools/levels/data/street_dressing_chinatown.json`
  (paint, gutters and patches are decals, manholes and drains cast-iron pieces: the Unreal side is a decal actor per row;
  nothing the game loads reads it). The look is in `ct_canal_start`, `ct_canal_east` and `ct_mott`. Not done: traffic. The
  vehicles were another lane's then (4c made them); tree pits and bollards (no
  collider names them), steam (an effect) and the hotpot cart.
- **The orange slab** was the back of the cap pegboard (`SM_Prop_CT_Goods_Caps`, a blank plywood board seen from the street
  side). It now has a timber frame, a mid rail, braces and two tags on the back. The produce displays had one flat fruit
  colour on a same-coloured false bottom: the bottom is now a dark crate liner and the fruit mixes two or three colours.
- **The alley's block wall**: the scale is right (the catalogue sets the painted block at 16 x 8 in units, 406 x 203 mm; real
  CMU is larger than brick, so it reads big beside the red brick). The moulded look was the scan's heavy relief: the market hall's
  block now uses half the normal strength and more macro dirt, and the alley floor is the new surface instead of a mirror. Not
  done: alley wall dressing (downpipes, cables, stains) has no collider or prop name in the level data; it is an art pass.
- The checks after these changes: `_chinatown_check.py` all pass (207 assets, 0 GLBs missing, views 0.88 M), with `--build` 0
  failing, budgets met and no thin members; `tools/levels/check_level.py --level chinatown` 0 failures.

## 4b. Round 3 (2026-11-26, lane A-CT): props at their collider sizes, decals, wear, LODs

The code is `assets/_chinatown_props3.py` (street, alley, roof, wall fittings, the hand-built pallet LODs), `_chinatown_props3b.py`
(interiors) and `_chinatown_decals.py` (textures and quads); the mapping is `_chinatown_streets.PROPS`. Every mesh is built at its
collider's size (or an exact divisor that the placement tiles along the collider's long side), pivot at the footprint's centre on
the ground, forward +X; wall pieces turn their back to the wall box they touch (`wall_rot`), so **no instance is scaled** (0 of 2165).
The lane now has 304 meshes, 638k triangles in all, all within budget, and 2165 placements (113 round-3 props, 95 wear decals,
5 decal rows).

| Group | Meshes (`SM_Prop_CT_*`) | Triangles (LOD0) | Placed |
|---|---|---|---|
| Carts | DumplingCart 5.3k (redone in 4c: canopy, menu frame, bowls, lacquer), NutCart 2.9k, HotpotCart 2.5k | steel or glass cabinets, wheels, steamers, roaster drum, burner and pot | 3 food carts, 1 hotpot cart |
| Stone lions | StoneLion_L, _R 7.4k (redone in 4c; were 2.0k) | stepped plinth, haunches with hind paws, straight forelegs with toes, bulging eyes under heavy brows, open mouth with fangs, five rows of spiral curls, tail fan, ball under one paw (a cub for _R) | 2 at the banquet door |
| Street | TrashBags_L 0.8k, _S 0.4k, FruitStand_Small 1.6k (0.8 x 1.0 m, its collider), Standpipe 0.3k, BikeRack 1.6k (2 hoops and a bicycle), ChairStack 1.8k, GreaseBin 0.5k, Planter_S 0.6k, _L 1.1k (replace the 42k Block planter), BucketStack, SandwichBoard, CDRack 2.7k, RoadPlates, DigFence (2.55 m run) | | 12 bag heaps, 9 standpipes, 5 racks, 9 chair stacks, 3 grease bins, planters, fence runs |
| Roof and wall | RoofVent 0.6k, ExhaustFan 0.8k, ExhaustStack, AntennaMast | | 6 vents, 6 fans, stack, mast |
| Bakery and kitchen | BakeryCounter 2.9k (2.3 m, two make the 4.6 m case), BakeryOven 1.2k (1.6 m deck oven), TrayRack 3.4k, FlourSacks, KitchenTable 0.6k, KitchenRange 0.9k, KitchenCounter, KitchenRack | | the whole bakery and the banquet kitchen |
| Dub room, workshop | TapeRack 2.2k (1.7 m), CuttingTable (the record-cutting lathe), DiscBurners 1.4k, KioskCounter, TubeBundles, BendingBench | | |
| Banquet hall | BanquetTable 1.2k (round, cloth, turntable, ten settings), BanquetStage 6.0k (2.8 x 7.8 x 0.5 m deck, gold edge, 4 m red curtain on a rail; placed at its collider's min corner) | | 7 tables, the stage |

**LODs.** `PROP_LODS` (LOD1, past 12 m) and the new `PROP_LOD2` (past 30 m) in `_chinatown_lod.py`; the view counter draws
LOD2 past `PROP_LOD2_SWITCH`. The trash can is now 6.4k / 1.6k / 0.4k, the stall counter 4.3k / 1.2k / 0.3k, the milk crate
1.8k / 0.45k / 0.13k; LOD1s were added for the produce greens, styrofoam boxes, tarp, newspaper box, parking meter, skylight,
condenser, caps board, lantern, traffic barrel and every new prop above 1.5k triangles; LOD2s for the props that stand in rows.
The **pallet stack** (13.3k) now has hand-built LODs (`SM_Furn_PalletStack_A_LOD1` 1.1k, `_LOD2` 0.4k: eight pallets of boxes, same
slot, size and pivot): the collapse left slivers. A signpost's and a street lamp's poles collapse to slivers under the 34 mm
floor, so their LODs are hand-built (below). Every LOD has its LOD0's slots and size (a check).

**Decals** (`SM_Decal_CT_*`, one 2K page `T_CT_Decals` BC with alpha, N, ORM, and a quad per cell with its UVs on its cell, one material
`M_CT_Decals`; in Unreal a decal-domain MI on a decal actor of the quad's size). Graffiti in the level's four invented tags only
(VULTURES, VLTR, RULE, INC: spray paint, dark outline, overspray, drips, flaking; oxblood and gold), the alley stencil "MOTT ST" with
an arrow and stencil bridges, and the near-ground wear pass: a grime band along the foot of every round-2 ground wall (3 m pieces,
two variants), scuffs at door height about every 7 m, rain and rust streaks on the back walls. The four tags and the stencil were
moved along their walls onto plain wall bays (lane D's points were on back doors and in the dub room's raised roll-up, mirrored from
inside in the first picture; each reason is in the instance's `deviation`). The text is checked against the approved list.

**The street blade.** `SM_Sign_CT_StreetBlade` hung from a clamp cylinder through the middle of its face; it now hangs from a bracket
arm over its top edge (two hangers) ending in a wall plate beyond its left end: nothing crosses a face (`ct_mott`).

**Pole LODs.** The sign post (35 placed) and the street lamp (9) were the last props with no LOD: rebuilt as solid members
(`m_pole_lods` in `_chinatown_props3.py`). Worst view 1 is now 0.79 M drawn (was 0.82 M).

**Worst view 1** (the start looking east, every placed piece in the frustum, none hidden by walls): 3.23 M triangles at LOD0,
**0.82 M drawn** (far proxies past 30 m, LOD1 past 12 m, LOD2 past 30 m), under the 1.5 M ceiling and the 1.1 M aim. Round 2b had
0.88 M with 207 assets; the round-3 props add 44k to the count (the interiors are counted although the walls hide them) and
the LODs take 1.33 M (no prop LODs) to 0.82 M. The north row's share is unchanged at 413k.

**Checks.** `_chinatown_check.py` all pass (new: **lods**, **decals**, **props3**; 307 assets, 0 GLBs missing); `--build`: 307 assets, 0
failing validation, 0 over budget, no thin member; `tools/levels/check_level.py --level chinatown` 0 failures; `tools/names/check_names.py`
passes (decal text is on the list). The level data was not changed.

## 4c. Fixer pass (2026-11-27): vehicles, the collider-only pieces, graffiti, dumpster, lions, cart

From the review of round 3 (every item re-checked; the checks and the previews were re-run and looked at).

- **Vehicles.** The Block's sedan, taxi, van, box truck and IPX truck are 168k to 179k triangles each; `_chinatown_lod.VEHICLES` makes a Canal
  version of each (`SM_Vehicle_CT_{Sedan,Taxi,Van,BoxTruck,IPXTruck}`: flat faces dissolved, then collapsed to 16k / 16k / 16k / 18k / 18k, same
  slots, size and pivot) with a LOD1 of 3.8k to 4.5k drawn past 12 m. The thin door-line and grille ribbons of the Block's meshes are dropped
  (the lane's 34 mm floor). The slots keep the Block's textures and `paint_default`; the paint is a tint mask, so every placement carries its own
  `paint` colour (linear RGB, from `_chinatown_streets.PAINT`): silver, white, navy, maroon, green and charcoal sedans, yellow taxis, white, grey,
  blue and red vans and trucks, the IPX truck black. In Unreal the MI parameter is set from that field. 14 colliders (sedan 29, 78, 80, 82, taxi 31, 79,
  van 30, 81, 83, box truck 32, 84, 85, 91, delivery truck 87, IPX truck 86) are dressed; nose with the traffic on Canal (north kerb west, south
  kerb east), alternating on Mott. No instance is scaled; the worst overhang of a body over its box is 0.2 m (a van on a 4.8 m box).
- **The collider-only pieces** (`_chinatown_props4.py`, 9 new meshes, 0.7k to 6.2k triangles): `SM_Prop_CT_{Newsstand, PhoneKiosk, ShopDisplay,
  LaundryCart, SteamChimney, ShedPost, ScaleStand, AlarmPedestal, ArcadePillar}`, each at its collider's size (the check `props3` now lists all 54
  planned kinds); goods cartons, chess tables, vendor stools and the raised beds reuse the cardboard boxes, card table, stool and planter, tiled
  along their boxes. LOD1s for the newsstand, shop display and shed post. Left: `ac_unit`, `barricade`, `gas_cage_frame`, `newsstand_bundle`,
  `tape_shelf` (no mesh or the wrong size, reason in the placements file).
- **Graffiti** (`_chinatown_decals.graffiti`, redone): ragged hand-sprayed edges (a warp of the glyph mask), a denser core and a softer rim, a thin dark
  shadow outline offset down and right and a pale highlight along the upper left, fine overspray mist, 26 drips with beads, faded and flaked top coat, a
  roller-buffed patch of an older cover-up behind it and the ghost of another of the four invented tags, paint thinner on the mortar joints and varied per
  brick, and the brick relief in the normal map. The cell is unchanged (1.6 x 0.6 m, so the placements are too); the tag fills 80 % of it. Text is the
  same approved four names (the ghost is another approved tag). `ct_graffiti` redone.
- **The dumpster** was the Block's: flat toy green, a blank label, one LOD. `SM_Prop_CT_Dumpster` (5.1k, LOD1 2.6k, LOD2 2.1k, hand-built levels
  with the same four slots) is a dark, greyed green steel (`MI_Steel_PaintDumpster`, the green paint scan darkened, more rust showing), ribbed
  sides, dented panels, fork pockets, black lids (one propped open), a hauler plate of stencil bars (no words), a cardboard flap, a bag over the
  rim. The 4 dumpster placements use it.
- **Lions and the dumpling cart** were first-pass: the lions are rebuilt in the temple pose (see the table), the cart has a red-lacquered cabinet,
  a canopy on four poles with a bare bulb, a blank menu frame (the words are a decal), bowls on a serving ledge, a strapped gas bottle and a prop
  stand. Both are nearer to hero grade; neither is a scan-quality asset.
- **Wear.** The grime band and scuffs now also run along the north row N1..N6 (3 m pieces and scuffs: 38 more decals, `wear_north`); the market
  hall's walls and the structures' fronts are still without (they are Unreal materials' job: vertex-painted grime), and the decal page is still 2K.
- **The budget is an estimate.** Worst view 1 is **0.90 M triangles drawn** (3.54 M at LOD0; the vehicles add about 0.11 M). That number assumes
  the far proxies switch in at 30 m, the props' LOD1 at 12 m and LOD2 at 30 m: all Unreal steps nobody has done. With **no proxies at all** (the
  HLOD late) the same view is **2.81 M**, over the 1.5 M ceiling, and the facades' modules have no LOD of their own. The check prints both; measure on
  the box (`stat SceneRendering`, A4000, no Nanite) before trusting either.
- Checks: `_chinatown_check.py` ALL CHECKS PASS (330 assets, 0 GLBs missing, 2264 placements, 0 scaled, lods 80 LOD1 / 22 LOD2 and 0 mismatches);
  `--build`: 330 assets, 0 failing, 0 over budget, no thin member; `tools/levels/check_level.py --level chinatown` and `tools/names/check_names.py`
  pass. Nothing the game loads changed.

## 5. Pictures

`ct_canal_start`, `ct_canal_east`, `ct_mott`, `ct_square`, `ct_alley`, `ct_yard`: night, wet, from the player's eye, 1280 x 720,
24 samples (round 2b; `ct_canal_start`, `ct_square`, `ct_mott` and `ct_alley` redone in round 3 at 14 to 16 samples). Round 3 adds
`ct_props3` and `ct_props3b` (the new street and wall props on a damp sidewalk), `ct_bakery`, `ct_kitchen`, `ct_banquet`, `ct_dub` (the
interiors from inside) and `ct_graffiti` (the VULTURES tag and the grime band on W1's alley wall, reframed so the whole tag shows). The ground is made from the level's `ground.surfaces` with the street surface of 4a; vehicles are in `ct_vehicles` (a row of the Canal vehicles in their placement paints) and, since the fixer pass, in the street views;
`ct_props4` shows the collider-only pieces and the dumpster.

## 6. Open

- The ground air conditioners (0.7 x 1.2 m, no mesh), the barricade (2.4 m mesh on a 1.2 m collider), the tape shelf, the gas cage frame and the
  newsstand bundle (4c).
- The bike rack has one bicycle (the level's collider is 0.1 m deep, a row of hoops); the interiors have banquet tables but no chairs around
  them (the chairs are the stacks). The lions, dumpling cart and dumpster were redone in 4c and are street-distance to mid-range art, not scan
  quality; the vehicles are the Block's models collapsed to 16k to 18k (the hood and glass read at street distance; not close-up cars).
- (Done: pole LODs, `SM_Furn_SignPost_LOD1` and `SM_Furn_StreetLamp_LOD1/2`; the Canal dumpster with its own LOD1/LOD2, 4c.)
- The decal page is 2K at 256 to 640 px per metre; the wear pass covers the round-2 ground walls and the north row (4c) and not the market
  hall's walls or the structures' fronts.
- **Every budget number here is an estimate.** The far proxies, the LOD switch distances and the HLOD are an Unreal step nobody has done; with
  no proxies worst view 1 is 2.81 M triangles against the 1.5 M ceiling (0.90 M with them). Measure on the box before trusting either.
- The Unreal side, not done: import, the placement actors from `placements_chinatown.json` (with each vehicle's `paint` set on its MI), the decals
  as decal actors, the far proxies as LOD1 / HLOD, the LOD1/LOD2 switch distances, a look at the stair, the market, the interiors, the vehicles
  and the graffiti under the real light on the box. Nothing here has been seen in the engine.
