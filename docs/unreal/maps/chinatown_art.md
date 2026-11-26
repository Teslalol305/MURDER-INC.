# Canal Street art, round 2: the other buildings, the signs, the props and the fitted structures (lane A-CT)

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

**Signs.** Every sign of lane D's `signage` list that is not on the north row is placed on its face, except the decals
(graffiti, the alley stencil: not built yet) and the market's exit box (drawn into the hall's shell). 32 shop fronts, every
one with a sign over it (a check). Lane D's points the art moved, each with its reason in the instance (`deviation`):
SEVEN STARS COACH (its 8 m band overlapped both neighbours: mounted on the second storey over the office door), the opera
poster (its point was in the middle of Lantern Alley A: on W1's alley wall at the same z), the rooftop letters (centred on
lane D's four legs), the lanterns (hung at 6.25 m, clear above the banquet band), arcade kiosk 3 (1.05 m out in the aisle:
on the east wall over the one front without another sign). Fronts lane D gave no sign get a generic lightbox or stall board
(KEYS CUT, WATCH REPAIR, ROAST MEAT, FRUIT...: words with no name to search).

**Props** (172 groups on lane D's `propPlacements`): stall counters in four rows with goods, tarps and pendant bulbs, fish
counters with tank and scale, vendor tables with goods, garment rails, crates, pallets, cones, drums, boxes, newspaper boxes,
lamps (arm over the roadway), card tables with stools, benches, hoops, signposts, meters, skylights, condensers. Each tiles
along its collider's long side; the worst overhang is 1.05 m (a 3 m jersey barrier on a shorter box). Not placed, with
the reason in `unmappedProps` in the placements file: the vehicles (their lane), hydrants (placed since round 2b, see 4a),
planters (42k and 1.2 m against 0.8 x 0.6 colliders), dumpling and hotpot carts, the bakery, kitchen, dub-room, workshop and banquet interior props (no meshes
yet), the fruit stand (2.4 m against a 0.8 m collider), small trash bags, standpipes, bike racks, chair stacks, grease bins,
roof vents and fans, antenna, dig fences, road plates, sandwich boards.

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
  vehicles are another lane's (sedan, van, taxi, box truck stay in `unmappedProps`), as are tree pits and bollards (no
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

## 5. Pictures

`ct_canal_start`, `ct_canal_east`, `ct_mott`, `ct_square`, `ct_alley`, `ct_yard`: night, wet, from the player's eye, 1280 x 720,
24 samples (round 2b). The ground is made from the level's `ground.surfaces` with the street surface of 4a; vehicles are not in
the pictures.

## 6. Open

- A light planter, the pallet stack's and the dumpster's LODs (they need a different reduction than a collapse).
- The interior props (bakery, kitchen, dub room, workshop, banquet tables, stage), the carts, the stone lions, the vehicles.
- The decals (graffiti, the alley stencil) and the near-ground wear on the new faces.
- The Unreal side: import, the placement actors from `placements_chinatown.json`, the far proxies as LOD1 / HLOD, a look at the
  stair and the market under the real light on the box. Nothing here has been seen in the engine.
- The street sign's post crosses its "CANAL ST" face in `ct_mott` (cosmetic, from the carrier).
