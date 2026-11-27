# Midtown art: the roofs, the screens' backs, the scaffold, the square, the set and the facades (lane A-MT, stage 1 and rounds 2 and 3)

What MAPS.md lane A-MT made without Unreal and without the box (2026-11-26), how it measures against
[midtown.md](midtown.md) 11, 12, 14 and 15, every invented name it uses, and what is still open. The code is
`art/blender/assets/midtown.py` and its `_midtown_*.py` modules; the outputs are in `art/out` (git-ignored), the pictures in
`art/previews/maps/mt_*.jpg`.

```
venv/bin/python art/blender/build.py build midtown --export                # 68 meshes, manifests, placements (about 12 s)
venv/bin/python art/blender/build.py build midtown --bake --export         # the same, redrawing the five face sets (about 2 min)
venv/bin/python art/blender/build.py build midtown --preview --samples 12  # mt_roofs, mt_gantry, mt_square, mt_stand, mt_plaza,
                                                                           #   mt_booth, mt_faces (3 threads, under a minute each)
venv/bin/python art/blender/assets/_midtown_check.py [--build]             # the lane's checks
```

## 1. What is built

39 meshes, 143k triangles in all, every one within its cap (midtown.md 14.2; where the design names a group, each asset
gets the group's cap). No collision on the art: the level data decides (MAPS.md lane B). Every member near the path is
6 cm across or more (a check measures it).

| Group | Assets (triangles / cap) |
|---|---|
| Roof surfaces | `SM_Roof_Deck_Gravel_4m` (320 / 2k), `SM_Roof_Deck_Pavers_4m` (1.5k / 2k), `SM_Roof_Parapet_4m_Buff`, `_4m_Red` (1.6k / 3k), `_1m_Buff`, `_1m_Red` (0.5k / 3k): 1.10 m over the roof, 0.30 thick, coping, inner flashing; `SM_Roof_NamePanel_6m` (250 / 1k) |
| Water towers | `SM_Roof_TankStand_4m` (7.4k / 12k), `_2m` (4.8k / 12k): I legs on piers, girts, angle X braces, no tie rods; `SM_Roof_WaterTank_4p6` (8.9k / 12k: WT-A, staves 5.6 m, cone 1.6 m), `_3p6` (7.0k / 12k: WT-B, WT-C) with hoops, hatch, outlet, caged ladder |
| Rooms on the roof | `SM_Roof_Bulkhead_4x4` (5.1k / 8k: I1 and bulkhead B, the stair going down inside), `SM_Roof_Bulkhead_5x6` (5.3k / 8k: I4 over the service shaft), `SM_Roof_TankHouse_6x6` (8.5k / 10k: I2, Reel 7, carries WT-C), `SM_Roof_MachineRoom_6x6` (9.9k / 10k: I3). Every door is 2.0 m (Goon doors, midtown.md 9.1), the leaf open |
| Roof dressing | `SM_Roof_HVAC_RTU_L` (3.9k / 10k), `_M` (2.2k / 6k), `SM_Roof_Skylight_2x3`, `_Vent_Mushroom`, `_ChimneyStack`, `_TarKettle`, `_Dish`, `_Antenna` (panels, no thin elements), `_WorkLight` (sodium lens) |
| Stairs and bridges | `SM_Roof_SteelStair_3p6` (4.7k / 15k: L1 to L4, 18 art risers over the data's 8 collider steps), `SM_Roof_StairHead_2p4`, `SM_Roof_PlankBridge_2p6x2`, `SM_Roof_PipeBridge_2p6x2` |
| Screens' backs | `SM_Roof_Gantry_16m` (10.2k / 25k: grating deck, rail, end frames, knee braces, Reel 8's cabinet), `SM_Sign_LEDWall_16x9` (19.4k / 30k: G1, cabinet backs, posts, girts, braces, outriggers: plate and truss, never lattice), `SM_Roof_BillboardFrame_16x8` (14.4k / 25k: C1's lightbox, legs, catwalk, four floods), `SM_Sign_LEDWall_Tile_2m` (226 / 2k), `SM_Sign_Ticker_4m` (214 / 2k), `SM_Sign_TowerStack` (8.9k / 40k: N1) |
| Scaffold stair (L5) | `SM_Scaf_Flight_2p4` (5 risers of 0.346 over 2.5 m), `SM_Scaf_Landing_2p4`, `SM_Scaf_Bay_Frame`, `SM_Scaf_Netting_Panel` (OPAQUE, no alpha), `SM_Scaf_Sign` |

Surfaces: the catalogued scans only (galvanised, painted steel, buff and red brick, weathered concrete, bitumen, gravel,
checker and bar plate, planks, canvas), tinted where a slot needs it (`MI_Timber_TankStave`, `MI_Fabric_ScaffoldNet`,
`MI_Steel_PaintBeige`, `MI_Steel_PaintBlack`): **no new tiling set** (the design allowed four: TS_Timber_TankStave,
TS_Scaffold_Netting, TS_Steel_Galvanised became tints and an existing set; TS_Granite_Pavers belongs to the square).

Faces (new texture memory about 46 MB with mips, BC1, against the 180 MB of midtown.md 15):

| Set | What |
|---|---|
| `MT_Screens_A`, `MT_Screens_B` | 4096², 8 slides each (16), emissive only: the G1 takeover (WORLD PREMIERE · MIDNIGHT, a clock box, a small oxblood VLTR mark), NO SIGNAL, STAND BY, IPX PRESENTS (three aspects), and the ten ads of 12.2. Each slide is drawn at its screen's aspect and squeezed into its cell, so 0..1 on the screen maps it back unstretched |
| `MT_Ticker` | 4096 x 256, the three headlines; the band maps u 0..`u_per_band` over 24 m and pans 0.35 m/s |
| `MT_Digits` | 512 x 64, 0-9, colon, space, minus: the countdown composited into the takeover's clock box |
| `MT_LEDMask` | 64², one LED pixel (R, G, B bars), faded out 8 to 20 m |
| `Sign_MT_Atlas1` | 4096², BC + ORM + E: C1's lightbox face, nine storefront and canopy bands, two incised name plaques, the contractor's board, the truck and bus panels, four door and cabinet labels (18 faces, 54 % of the page) |

## 2. The screens and the emissive budget (midtown.md 12.3, 15)

- **One master.** Every screen surface is a single face in the slot `M_MI_Screen` on 0..1 UVs: opaque, black base,
  emissive = a slide cell x nits (450 on G1, E1, E3, N1; 300 on the others), a crossfade between two cells, the LED mask
  faded out between 8 and 20 m. No translucency, no world position offset, no video, no render target.
- **Seven large surfaces** (G1, E1, E2a, E2b, E3, N1, S1) plus the ticker, against the ceiling of 9. C1 is a lightbox
  face (`M_Sign_MT_Face`, 200 nits), not a screen.
- **Tiled screens stay one slide.** E1 (12 x 9 tiles), E2a and E2b (4 x 10), E3 (10 x 6, turned 6 degrees apart along a
  54-degree arc) and S1 (6 x 3) are instances of the 2 m tile; each placement carries its column and row, which go into
  PerInstanceCustomData, and the screen's one MI offsets every tile into the screen's cell.
- **The rate rule is the director's** (lane E11): one hero screen changing in any 2 s, each at most every 8 s, 0.6 s
  crossfades, nothing faster than 3 Hz. The art holds no animation.
- **No red field on any slide** (the Goons are oxblood); the VLTR mark is under 5 % of the takeover's height.

## 2a. Fix pass (2026-11-26, after the lane review)

- **No seams on the tiled screens.** SM_Sign_LEDWall_Tile_2m's module rails sit behind the face, so a wall of tiles is
  flush; the bezel is SM_Sign_LEDWall_Edge_H_2m / _V_2m, placed only round each tiled screen's outside (E1, E2a, E2b, E3
  on its arc, S1).
- **N1 shows three ads.** SM_Sign_TowerStack carries a second UV map, FaceIndex (u = 0, 1, 2 from the bottom face up), and
  its placement lists `slides` (HOROVAN, NORTHWEFT, FIZZWICK SODA): M_MI_Screen reads the slide for each face from it.
- **Scaffold flights** draw 10 risers of 0.173 m over 0.25 m treads on the data's 5 collider steps of 0.346 m (as the roof
  stair: art risers finer than the collider steps).
- **Thin check at the floor:** 5.5 cm across (the 6 cm floor of midtown.md 15 measured across an octagon), no longer 5 cm;
  the machine room's louvre gaps widened to pass it.
- **Type:** the storefront bands and several slides use their own OFL faces (Bebas Neue, Passion One, Archivo Black, Alfa
  Slab One, Fjalla One, Anton, Old Standard, Inter), all kept in art/blender/fonts (FONTS.md), no longer read from the
  system.
- **Previews re-staged:** the 11:52 PM dome (#6a3e5a at the horizon to #0b0d18 at the zenith, midtown.md 11.1) at exposure
  0.7, stand-in masses with a window grid (about a third lit), screens at their nits rather than washed out.
- Names: the 11 retired names are replaced everywhere (names.md); every name here is on the approved list.

## 3. Placements (`art/out/placements/placements_midtown.json`, 868 instances)

The west block's five roofs at their collider heights (A 21.2, B and C 17.6, D and E 14.0): 159 deck panels, 136 parapet
modules broken at every opening of 5.3 (L1 to L4, the planks, the pipe bridge, the drops D1 and D2, the gantry doors, the
service bulkhead), the rooms at their interior boxes of 9.1 with the doors where 9.1 puts them, the four stairs and two
bridges on their 5.3 lines, the gantry and G1 over the west sidewalk, C1 on C's east edge, the scaffold tower's 8 flights,
8 landings, 63 frames and 25 netting panels on the levels of 5.3 (the east landings and the shed-hop lift left open), and the
art-only screens past the bounds. Positions the design leaves open carry `"chosen": true` (WT-A at (-38, -25), WT-B at
(-45, -5), bulkhead B at (-44, 3.5), the HVAC rows, the art-only screens): lane D's colliders win where they differ.

## 4. Every invented name this lane uses (searched 2026-11-26, docs/unreal/maps/names.md; owner sign-off pending)

From midtown.md 12.2 and 12.4, unchanged: MIRAVESSE (Eau de Nuit), NORTHBOUND AIRWAYS (Fly the late one), KESTREL MOBILE
(Five bars, five boroughs), BRASS & BUN (Burgers till four), THE MERIDALE THEATRE and its show LAMPLIGHT AVENUE (a new
musical), VESPERLINE CRUISES, HOROVAN (watches), NORTHWEFT (fall collection), FIZZWICK SODA, DUSKLINE TOURS (The city
after dark), MARLOWE & FINCH (The holiday floor is open), SEVENTH AV SOUVENIRS, SLICE OF SEVENTH, SHUTTERBOX CAMERA &
ELECTRONICS, BELLHAVEN SAVINGS, HOTEL CASTELLANE, BRANNIGAN'S CHOP HOUSE, ASHBY & CROSS PHARMACY, HALVORSEN BUILDING, CORVIN HALL,
KESSLER & ROTH SCAFFOLD, BRIGHTWIRE EVENTS, CITY CROSSTOWN, THE LOFTLARK (listed; its neon is the square lane's), the VLTR tag,
the ticker's three headlines.

Added by this lane (generic words, no business name): the sub-lines STAGING · LIGHTING · SCREENS (Brightwire) and SIDEWALK
SHEDS · SCAFFOLD · HOISTS (Kessler & Roth); the labels ROOF DOOR / KEEP CLOSED, MACHINE ROOM / AUTHORIZED ONLY, DANGER /
HIGH VOLTAGE, TANK 2 / DRINKING WATER; PRESENTS under the IPX mark; NO SIGNAL and STAND BY. No phone number, no web address,
no real brand; IPX is the only real mark. The single source is `art/blender/assets/_midtown_names.py`, and
`art/out/midtown/signs_midtown.json` lists every string with its cell.

## 5. Checks (`_midtown_check.py`; results of 2026-11-26)

english (76 strings, plus 61 in the atlas cells and ticker: ASCII, the middle dot and the degree sign only), names (IPX on
the 3 IPX slides only), validation (41 of 41), budgets (41 of 41), thin (no member over 0.6 m long under 5.5 cm across),
files (every GLB on disk and in the shared manifest with the same triangles and bounds), atlases (2 x 8 slides, no overlap;
ticker, digits, mask sizes; 18 faces, no overlap), placements (every mesh, face, slide and tile accounted for), emissive (7
screens, 46 MB, no new tiling set), block (facade.py, signs.py, place_buildings.py, level.json and levels.json untouched;
nothing written under unreal/MurderInc): ALL CHECKS PASS.

## 7. Round 2 (2026-11-26): the square, and every placement fitted to the level data

Sections 1 to 5 are the first round as it was made; this section is what changed. The code is
`art/blender/assets/_midtown_square.py` (the kit), `_midtown_place.py` (the fit), `_midtown_roof.py` (the tower and HVAC
variants the fit needed), `_midtown_check.py` (two new checks) and `_midtown_preview.py` (three new views).

### 7.1 The square family: 24 meshes, 30.7k triangles

| Group | Assets (triangles / cap) |
|---|---|
| THE STAND (as the data has it: tiers 1 to 5 in two wings x 10..13 and 19..22 round a front court at plaza level, tiers 6 to 8 the full 12 m over the Booth) | `SM_Sq_Stand_Tier_3m` (380 / 4k: the wings' tiers), `SM_Sq_Stand_Tier_12m` (3.3k / 12k: tiers 6 to 8, deck beams and soffit inside the 0.30 slab, the Booth's ceiling), `SM_Sq_Stand_WingSide` (864 / 6k: stepped side cladding, clad both faces, four placements), `SM_Sq_Stand_Back` (4.5k / 8k: the Booth's back wall and the top tier's guard, a dark opaque scrim on a box-section truss to 6.20 with returns down tier 8's sides, the data's playerOnly boxes). Every tier: checker tread, galvanised nosing with a 6 cm amber strip, amber riser glass 0.40 high in a steel light box |
| THE BOOTH | `SM_Sq_Booth_WallSide` (952 / 6k: 0.60 thick, top under the tier soffits, the 2.0 m Goon door framed on both faces, a label over it both sides; one mesh for both walls), `SM_Sq_Booth_FrontWall` (1.3k / 6k: sill 1.0 and head 2.0 over the plaza, the 6 x 1.0 m broken window framed in steel with glass shards only at its corners: the shoot-through slot stays open), `SM_Sq_Booth_Desk` (680), `SM_Sq_Booth_Rack` (2.1k), `SM_Sq_Booth_MonitorCart` (864), `SM_Sq_Booth_Monitor` (86) |
| The plaza | `SM_Sq_Planter_Granite_4m` (2.2k / 6k: granite walls and coping, soil, a clipped box hedge as a closed mesh: no masked leaves), `SM_Sq_Kiosk_Souvenir` (2.8k / 20k: navy enamel, the shutter half down, lit caps and shirts, a lightbox header front and back), `SM_Sq_FoodCart` (1.2k / 10k: stainless, steam table, opaque sneeze glass, a lit menu, the navy umbrella half down), `SM_Sq_CafeTable`, `SM_Sq_CafeChair`, `SM_Sq_CafeChair_Stack`, `SM_Sq_LightPole_LED` (8.0 m, twin LED heads), `SM_Sq_CableRamp_1p2`, `SM_Sq_CableDrum` |
| Barriers and the premiere's gear | `SM_Sq_Barrier_Jersey_1p8` (one or two modules stretched to each box), `SM_Sq_Barrier_Water_1p9` (orange and white plastic), `SM_Sq_Barrier_Bike_2p4` (crowd-control barrier, no agency mark: 6 cm tube frame and 6 cm flat-bar pickets), `SM_Sq_Generator` (hired generator on a trailer, Label_HighVoltage), `SM_Sq_RoadCase_Stack` (the crew's cases, BRIGHTWIRE stencils) |

Surfaces: still no new tiling set. The square's slots are tints of baked or catalogued sets: `MI_Stone_Granite` (the
aggregate concrete scan, cooled grey: the design's TS_Granite_Pavers as a tint), `MI_Steel_PaintStand`,
`MI_Steel_PaintStandBlack`, `MI_Steel_PaintKiosk`, `MI_Steel_PaintGenerator` (the clean white paint set, tinted: the
premiere's steel is new, not rusted), `MI_Leaf_PrivetClipped`, `MI_Fabric_Scrim`, `MI_Fabric_UmbrellaNavy`,
`MI_Wood_CableDrum`, and the plastics, stainless, shutter and soil sets as they are. Members near the path are 6 cm and up
(checked); the chairs' 3 cm legs and backs are parts under 0.6 m, kept off the hero sightlines as the design says.

Reused from the Block's kits (midtown.md 14.1), placed but not rebuilt: `SM_Street_Bench` (4), `SM_Street_TrashCan` (20),
`SM_Furn_StreetLamp` (the 6 avenue lamps, the davit arm over the roadway). The design's new SM_Sq_Bench was not needed:
the gaps bench is 1.76 x 0.56 x 0.84 against the data's 1.8 x 0.6 x 0.85.

### 7.2 The emissive cost (midtown.md 11.2, 12.3, 15)

Nothing on the square is a screen. `_midtown_check.py --build` adds every emissive slot on the placed square meshes, front
faces only, times its night luminance:

| Slot | Area | Luminance |
|---|---|---|
| `MI_Stand_RiserGlass` (the risers and their nosing strips, opaque) | 26.4 m2 | 40 nits |
| `M_Sign_MT_Face`, lit (2 kiosk headers both sides, 2 cart menus) | 5.1 m2 (largest single face 1.47 m2) | 200 nits |
| `MI_Lamp_LED` (the 4 plaza poles' 8 heads) | 1.8 m2 | the lamp; the light is one of lane L's 12 spots |
| `MI_Lamp_KioskInterior` (strip lights) | 1.7 m2 | 120 nits |
| `M_MI_Screen` (5 booth monitors on a slide, LED mask off) | 1.0 m2 | 300 nits |
| `MI_Lamp_Indicator` (racks, console, generator) | 0.2 m2 | 60 nits |

Area x luminance: 3,122 against the seven screens and the ticker's 641,760 (0.5 %, the check's ceiling 5 %). The large
screen count stays 7 + the ticker (ceiling 9), the new texture memory 46 MB (the four new faces fit Sign_MT_Atlas1, now 56 %
full), no translucent slot.

### 7.3 The fit to tools/levels/data/level_midtown.json

`_midtown_place.py` now reads the level file and puts every piece on its collider: the centre on the box's centre, the
base on its bottom, turned so the mesh's core footprint runs along the box (the rotation that needs the least stretch),
scaled to the box where the mesh is a box (`fit.mode` "scale"), unscaled where the box is only the solid part ("centre":
the bench, the litter baskets, the lamps, the chairs' stacks, the dish, the antenna, the tar kettle; the residual is
recorded), or as named parts ("part": the Stand, the Booth, the rooms, the towers). Every fitted instance records
`fit.colliders` (the level's collider indices). Result: **159 instances on 186 colliders of 33 tags, none of those
colliders left without art.**

The first round's chosen positions, refitted (lane D's colliders win):

- **Water towers**: one stand and one tank per tower, sized to the data. WT-A: legs 4.4 m apart, the tank 5.9 m across with
  5.5 m staves on the 4.0 m stand (25.2 to 30.8); WT-B 3.0 m, 3.9 x 3.9 at (-44, 17.6, -4) (was (-45, -5)); WT-C 5.0 m, 4.9 x
  4.9 on the tank house's roof at 20.7 (was 20.75). The meshes are `SM_Roof_TankStand_A/B/C` and `SM_Roof_WaterTank_A/B/C`
  (they replace `_4m`, `_2m`, `_4p6`, `_3p6`, which are gone from the manifest and art/out).
- **Bulkhead B** at (-46, 17.6, 2), the data's box (was (-44, 3.5)).
- **Roof dressing** on the data's boxes: 7 rooftop units (a square `SM_Roof_HVAC_RTU_S` added for the 2 x 2 boxes; the
  others take the M unit), 2 skylights, the chimney rows (5 stacks on the 6 m box, 1 on the 1 m box), 12 vents, 2 dishes,
  the antenna, the tar kettle. Every unit, vent, dish and mast the first round placed by choice moved onto a data box; the D
  roof's unit had no box and is gone.

Still the lane's own choice and marked `"chosen": true` (with `fit.chosen` saying what): the art-only screens past the
bounds (E1, E2a, E2b, E3, N1, S1), each tank's ladder side, the kiosks', carts' and benches' facings (their boxes are
symmetric), the three monitors on the booth desk and the six cafe chairs (dressing, no collider).

### 7.4 Names (English only; every name on names.json)

Four new printed faces, each with an approved name or generic words only: `Kiosk_SeventhAv` (SEVENTH AV SOUVENIRS, the
storefront's approved name, on its two plaza kiosks), `Cart_Menu` (HOT DOGS · PRETZELS / SODA · WATER · COFFEE, no business
name), `Stencil_Brightwire` (BRIGHTWIRE EVENTS / STAGE LEFT), `Label_CrewOnly` (BROADCAST BOOTH / CREW ONLY). The generic
lines are added to lane C's generic list (tools/names/build_names.py, names.json regenerated: still 50 approved, 15
retired), and the checker now also reads `_midtown_square.py` and `_midtown_place.py`. `python3 tools/names/check_names.py`:
PASS.

### 7.5 Checks (2026-11-26, round 2)

`_midtown_check.py`: english (83 strings; 68 in the atlas cells and the ticker), names, files (68 assets), budgets (68
within 14.2, 193,102 triangles), atlases (22 faces, 56 %), placements (1,003 instances of 70 meshes, the 3 reused ones from
the shared manifest), **fit** (above), emissive (7 screens, 46 MB, no new set), block: ALL CHECKS PASS. `--build`:
validation 68 of 68, budgets, thin (none), **sq-emissive** (above), block: ALL CHECKS PASS. `tools/levels/check_level.py
--level midtown`: 36 pass, 1 waived, 0 fail (the level data is unchanged). The archive `art/out/maps-midtown.tar` is re-packed
(86 files; its sha256 in `art/out/midtown/ARCHIVE.json`).

Previews (art/previews/maps, 1280 x 720, 12 samples, at most 300 kB): `mt_stand` (the Stand from the plaza: the kiosk, the
amber risers of the east wing, the court and the Booth's window, the generator), `mt_plaza` (V5's eye from the top tier
south over the planters, kiosks, carts, cafe tables, LED poles and barriers), `mt_booth` (inside the Booth from its west
door: the desk with the program feed on its monitors, the racks, the slot onto the court), and `mt_roofs` re-rendered with
the refitted towers and units.

## 8. Review fixes (2026-11-26, round 2b): facade windows and the horizon

The review found the square's buildings read as flat white window rectangles on near-black masses, and a hard black horizon
under a flat magenta sky. Both are in the look-dev stand-ins (`_midtown_preview.py`), not in a built asset: the Midtown facade
tables are still unbuilt (section 6), so this is the **specification the facade material must match**.

- **Facade windows** (`window_grid`): a 1.55 x 3.1 m bay with a frame, a recessed pane, a mullion and a transom, a stone sill
  and a storey ledge (a bump of 8 cm for the pane, 4 cm for the frame, ledge and sill out); each window has its own state
  from its snapped position: lit or not (24 percent of the masses, 34 percent of the towers), a brightness with a long tail of
  dim windows (0.12 to 1.0, squared), a colour from tungsten orange through warm white and fluorescent to TV blue (towers lean
  fluorescent), a ceiling gradient (brighter at the top of the pane), and a covering (38 percent venetian blinds, 22 percent
  curtains, the rest bare glass). Unlit panes are dark reflective glass (roughness 0.28). The wall drifts in tint and has
  vertical grime. In Unreal the same is a master material with per-window id from the facade's world position.
- **The horizon**: the stand-in ground is 1 km wide and the sky below the horizon is the haze colour of the glow instead of
  near-black, so the edge disappears. The sky itself is still a gradient: a skyline of far towers and a light haze volume are
  still to do (the far buildings are part of the unbuilt facade tables).
- Pictures `mt_plaza` and `mt_roofs` re-rendered at 24 samples. `_midtown_check.py` all pass; no asset changed.

## 6. Hand-off and what is still open

- Hand-off: `art/out/maps-midtown.tar` with its sha256 and file list in `art/out/midtown/ARCHIVE.json` (the GLBs, the five face
  sets, the lane manifest, signs_midtown.json, placements_midtown.json, midtown.blend), as the Canal lane's archive. The TS_*
  scans the slots name are the Block's (not in the archive).
- **Box and engine (lane B, L, E11):** the import (`send-art.sh pack --maps 'SM_Roof_*' 'SM_Scaf_*' 'SM_Sign_LEDWall_*'
  'SM_Sign_Ticker_4m' 'SM_Sign_TowerStack' 'SM_Sq_*'`: the default pack leaves the map families out), `M_MI_Screen` and its
  MPC (per-instance tile offsets, the FaceIndex slide choice for N1, and the booth monitors' `slide` with the LED mask off),
  the night rig and the picture rounds at V1 to V6; flicker.py at V2 to V4 (the bike barriers' pickets and the scrim truss
  are new thin-ish steel in V5's view).
- **Lane D (round 2 done here):** the placements now follow the level file; if the layout moves a collider, re-run
  `_midtown_place.py` and the fit check names what moved. The roof boxes that had no art are done in round 3 (section 9).
- **Lane A-MT:** round 3 (section 9) made the rest: THE LOFTLARK's furniture and neon, the roof boxes, the bus, the facade tables and the east podium, the storefront carriers, the premiere's set and the plaza's small dressing. What is still open is section 9.5 (the parked cars, the sawhorse, the decals).
- **Design to confirm (lane D's deviation):** the Stand's wings and front court; the art follows the data.
- **Lane C:** done (names.md); the owner's sign-off on the list, and the US trademark-register search names.md asks for
  before release, are still to come.

## 9. Round 3 (2026-11-27): THE LOFTLARK, the roof boxes, the bus, the premiere's set, the facades

Round 3 makes everything section 6 listed as still to make, except the parked cars (below). 96 new meshes, 173,887 triangles
(70 meshes and 26 LOD1s; the lane is now 164 meshes, 366,989 triangles, every one under its cap), 1,677 placements of 144 meshes
(was 1,003 of 70). Code: `_midtown_dress.py` (the roof and the plaza's small dressing), `_midtown_set.py` (the premiere's set and the
bus), `_midtown_facade.py` (the facade tables' modules, the carriers, the east podium), `_midtown_place.py` (`dressing`, `facades`),
`midtown.py` (`LOD1`, `build_lods`), `_midtown_check.py` (`views`, `fac-emissive`). Names: every string is a generic word or an
approved name (names.md): no new business name, `check_names.py` PASS.

### 9.1 What is built

| Group | Meshes (triangles) |
|---|---|
| THE LOFTLARK (D) | `SM_Roof_Lounge_Bar` (4.8k: a guest counter with a foot rail and six stools, a back bar of bottle shelves, the island inside the data's 1.0 m box), `SM_Roof_Lounger` (0.4k), `SM_Roof_Lounger_Stack` (2.1k), `SM_Roof_Umbrella_Folded` (0.5k), `SM_Roof_PlanterBox` (1.0k), `SM_Roof_LoungeDeck_9x7` (11.3k: the raised timber deck, 0.6 m, a 0.30 m step on its open sides), `SM_Roof_Loftlark_Neon_4m` (7.2k: THE LOFTLARK in 13 mm neon tubes on a black pan, a cyan border tube; on D's east parapet coping facing the square, unlit: the lounge is closed) |
| Roof boxes with no art | `SM_Roof_DuctBox_1p6` (6 placed), `SM_Roof_VentBox_1x1` (2), `SM_Roof_ConduitBox_1p4` (2, Label_HighVoltage), `SM_Roof_ConduitRun_4m`, `SM_Roof_PipeSleepers_1p6` (4), `SM_Roof_FanHousing_1p6`, `SM_Roof_DunnageDeck_6x6` (4.4k: E's steel dunnage platform): 0.6 to 1.0k each |
| Parked cars | `SM_Vehicle_MT_{Sedan,Taxi,SUV,Van}` (14k to 15k, LOD1 3.6k to 3.9k), 10 placed |
| The bus | `SM_Vehicle_CityBus` (9.1k of the design's 90k cap, LOD1 2.4k): 12 m, white with a blue skirt and window band, eleven tinted bays, two doors on the kerb side, a lit destination sign (Panel_CityCrosstown) and Bus_Side on each flank, six wheels, mirrors, lamps, a roof pod, an interior silhouette behind the glass. CITY CROSSTOWN, no real livery. Placed nose south with the doors on the east kerb |
| Trucks and trailers | `SM_Sq_Truck_Production` (BRIGHTWIRE EVENTS, nose north, tail lift stowed), `SM_Sq_Van_Broadcast_6p8` (two), `SM_Sq_Truck_Satellite`, `_Catering`, `_Generator`, `_Cable`, `_Staging`, `SM_Sq_Trailer_Production_6m` / `_6p4`, `SM_Sq_ScreenTrailer` (parked and dark): 1.8k to 7.4k, each with a LOD1 of 0.8k to 2k |
| Towers, walls, tents, booths | `SM_Sq_LightTower` (7: the mast raised to 5.6 m), `SM_Sq_TrussTower` (6: 6 cm chords), `SM_Sq_PressWall_3p4` (3), `SM_Sq_VipTent_3x3`, `SM_Sq_MerchBooth`, `_CoatCheck`, `_SecurityBooth`, `_InfoBooth`, `_PhotoBooth`, `SM_Sq_PortableToilets`, `SM_Sq_CameraRiser`, `SM_Sq_SpeakerStack`, `SM_Sq_SoundTower` |
| Plaza small dressing | `SM_Sq_BollardPlanter`, `SM_Sq_Newsstand` (3), `SM_Sq_PhoneKiosk` (2), `SM_Sq_WayfindingPylon` (2, the real street names), `SM_Sq_ATM_Kiosk`, `SM_Sq_Standpipe` (2), `SM_Sq_ValetStand`, `SM_Sq_LuggageCart`, `SM_Sq_Crates_Stack`, `SM_Sq_Hoarding_6m`, `SM_Sq_FanSign` (8 dropped on the plaza), `SM_Sq_TrashCan` (20: replaces the Block's 17k-triangle wire basket, which put 307k triangles in the start view; this one is 0.8k), `SM_Sq_Sawhorse` (built, not placed: a 1.0 m object needs a collider from lane D) |
| Reused, placed | the Canal kit's `SM_Prop_CT_Hydrant` (9), `SM_Street_SignPost` (24), `SM_Furn_NewspaperBox` (6), `SM_Furn_TrashBags_A/_B` (3), `SM_Furn_BusShelter` (stretched to its box) |
| Facade modules | `SM_Facade_MT_Bay_{Red,Buff,Stone}_3p1` (0.7k, LOD1 0.2k: one storey of one bay, the wall in the brick or stone slot, a recessed window, the pane in the window-grid slot `M_MT_WindowGrid`), `SM_Facade_MT_Cornice_3p1`, `SM_Facade_MT_Ground_Blank_3p1`, six shopfronts `SM_Facade_MT_Shop_{Souvenir,Slice,Camera,Bank,Chop,Pharmacy}` (1.5k to 3.0k; the bank is shuttered and dark), `SM_Sign_MT_Band_{6,7,8,10}m` (the storefront carriers: a lit face 0.9 high, one per band of the atlas) |
| East podium | `SM_Facade_MT_TheatreFront_8m` (THE MERIDALE THEATRE's six-leaf brass door and poster cases), `SM_Facade_MT_HotelFront_8m` (HOTEL CASTELLANE's revolving door), `SM_Facade_Marquee_A` (4.9k: THE MERIDALE THEATRE over LAMPLIGHT AVENUE, A NEW MUSICAL, three rows of bulbs, on I-beam brackets), `SM_Facade_Marquee_B` (1.2k: the hotel's canopy with its lit fascia) |

Faces: 16 new in `Sign_MT_Atlas1` (now 38 faces, 70 % of the page; the packer is first-fit, the small labels are a new 640 px/m kind):
the info, security, coat check, merch, photo booth, VIP, valet, phone kiosk and cash machine labels, the newsstand header, the
street-name pylon face, the marquee's show board, the press wall (WORLD PREMIERE and MIDNIGHT repeated, a small oxblood VLTR),
the catering, broadcast and bus panels. The sign atlas is the only texture that changed (same 4096 page: new texture memory still
46 MB); no new tiling set (the vehicle paints, tents, brass, hoarding and cushions are tints of the clean paint, canvas, plank
and flat slots). No translucent slot anywhere (the glass is the opaque M_MI_Glass).

### 9.2 The facade tables (midtown.md 2.1, 12.4, 14.2, 17.13)

The Block's facade kit and `place_buildings.py` are untouched (the block check); the per-level table is in `_midtown_place.FRONTAGES`.
Each frontage is a run along a facade collider's outer plane, in the Block's module frame (the face toward -Y, running +X):

| Frontage | Run | Ground storey (4.70) | Upper storeys |
|---|---|---|---|
| East (x 30) | z -38..22, 60 m | base, THE MERIDALE THEATRE's two front modules (z -22..-6) with the marquee over the doors at z -14, base, HOTEL CASTELLANE's front (z 2..10) with the canopy over the doors at z 6, base | 8 x 3.16, stone (buff over the hotel) |
| South (z 36) | x 31..-50, 81 m | BRANNIGAN'S CHOP HOUSE (x 22..14), ASHBY & CROSS PHARMACY (x 6..-1), bases | 5 x 3.06, buff and stone |
| West C (x -8, CORVIN HALL) | z -4..-38, 34 m | SEVENTH AV SOUVENIRS (z -6..-14), the hoarding's closed shop (z -14..-20, bases), SLICE OF SEVENTH (z -20..-26), bases | 4 x 3.225, red |
| West D (x -8) | z 22..-4, 26 m | BELLHAVEN SAVINGS closed (z 22..14, behind the scaffold), SHUTTERBOX CAMERA & ELECTRONICS (z 12..2), bases | 3 x 3.10, red |
| W 46 St north (z 22) | x -50..-30 (E) and -28..-8 (D), the light court left open | bases | 3 x 3.10, red |

535 placements: bays at the building tables' storey heights (a z scale of 0.93 to 1.0 on the 3.30 module), a cornice at each roof line (the
west blocks' parapets are the roofs' own art), the carriers 3.6 up. The window pane is the slot `M_MT_WindowGrid`: the look-dev
stand-in of section 8 (24 percent of the masses lit, 34 percent of the towers, a long tail of dim windows, tungsten to TV blue, blinds
and curtains) is its specification, and the previews now draw the real bays with it. Brick UVs are metres from the module pivot, so the
placed instance's position along the run offsets them (or the material goes world-aligned).

### 9.3 Fit and budgets

- **Fit.** `fit` passes for 824 instances on 328 colliders of 84 dressed tags (was 159 on 186 of 33): none left without art. The
  vehicles are authored at their boxes' sizes (nose +X; south, the avenues' direction, except the production truck: north); the light
  towers' raised masts and the bar's back bar are over their boxes (`above`: shots pass). Not dressed on purpose: the parked cars
  (sedan, taxi, SUV, van: the Block's vehicles are 170k triangles each, 14 of them would be 2.4 M: they need light variants first, as
  Canal made for the hydrant), the arriving IPX truck, G1's cabinet (part of the gantry mesh). 492 chosen positions are marked.
- **Triangles.** The new pieces are light: the bus 9k, a truck 4.7k, a bay 0.7k. LOD1s (a quarter of the triangles, same slots and pivot):
  the facade modules and the east podium at 25 m, the vehicles, decks and bar at 12 m (`_LOD1` meshes, the static mesh's LOD1 in Unreal).
  The new check `views` counts the lane's placed art in the six shot views: **V1 1.10 M at LOD0, 0.83 M with the LOD1s** (the worst), V2 0.60,
  V3 0.20, V4 0.31, V5 0.68, V6 0.52. The street, the backdrop and the Block's vehicles are not in it: the target is 1.3 M for the whole view.
- **Emissive.** `fac-emissive`: the facades', vehicles' and neon's slots are 57.6 m2 of lit faces (the largest the marquee's 8 x 1.4 board,
  11.2 m2, a lightbox: no screen slot), 3.2 m2 of marquee bulbs at 350 nits; with the square's, **2.4 % of the screens' light** (ceiling 5 %).
  The unlit printed faces (the trucks, the bus flanks) are not counted; the neon is off. Still 7 large screens and the ticker.
- **Thin.** No member over 0.6 m long under 5.5 cm across in any of the 164 meshes (the checks fixed the vehicles' door lines, grille
  slats, the booths' strip lights and the marquee's brass trims).

### 9.4 Checks and pictures (2026-11-27)

`_midtown_check.py`: english, names, files (164), budgets, atlases (38 faces), placements (1,677), fit, **views**, emissive: ALL CHECKS PASS;
`--build`: validation 164 of 164, budgets, thin, sq-emissive, **fac-emissive**: ALL CHECKS PASS. `tools/levels/check_level.py --level
midtown`: 36 pass, 1 waived, 0 fail (the level data is unchanged); `tools/names/check_names.py` PASS (the three new modules are in its
scan); `_chinatown_check.py`: ALL CHECKS PASS. The archive `art/out/maps-midtown.tar` is re-packed (`art/out/midtown/ARCHIVE.json`).

Previews (art/previews/maps, 1280 x 720, 12 samples, each under 300 kB): `mt_bar` (THE LOFTLARK from the south: the bar, its stools and back
bar, the raised deck, the folded umbrellas), `mt_set` (up the plaza from W 46 St: the toilets, the press wall, truss towers, trailers, the
marquee and the hotel beyond), `mt_bus` (the bus's nose and kerb flank, the hotel front and its canopy, the newsstand, a speaker stack
and truss towers), `mt_facade` (THE MERIDALE THEATRE's marquee from the plaza: the name and the show board, the bulbs, the soffit
lights), `mt_street` (Seventh Av: SEVENTH AV SOUVENIRS under its band, the phone kiosk, the crates, the bays); `mt_roofs`, `mt_gantry`,
`mt_square`, `mt_plaza`, `mt_stand` are re-rendered with the facades and the set in. The look-dev lights of each picture (the lounge's glow, the
light towers' heads, the marquee) are the picture's, in `_midtown_preview.rig_extra`; the neon is shown nearly dark, as designed.

### 9.5 Still open

- **Parked cars** (14 colliders of sedan, taxi, SUV, van): light variants of the Block's vehicles, with LODs, then placed on their sliced boxes.
- **The sawhorse and the crowd's smaller leftovers** (caps, flyers, a pile of spent barriers): the sawhorse is built; it and any piece over
  0.5 m need a collider from lane D. The VLTR spray over the production truck and the graffiti are decals (the Block's decal kit).
- **Facade colour work**: the window master's per-window look is a specification until the box has `M_MT_WindowGrid`; the far buildings
  (the bow-tie, the towers the screens hang on) are still the backdrop kit's (midtown.md 14.1) and the stand-ins in the previews.
- **Box and engine** as section 6: the import (`send-art.sh pack --maps ... 'SM_Facade_MT_*' 'SM_Facade_Marquee_*' 'SM_Sign_MT_Band_*'
  'SM_Vehicle_CityBus*'` as well), the night rig and picture rounds, the marquee's bulb chase and the neon's night strength, the owner's
  sign-off on the names list.
