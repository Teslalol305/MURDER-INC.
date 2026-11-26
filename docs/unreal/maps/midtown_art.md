# Midtown art: the roofs, the screens' backs, the scaffold and the square (lane A-MT, stage 1 and round 2)

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
  `_midtown_place.py` and the fit check names what moved. The roof boxes with no art yet: duct boxes (6), vent boxes (2),
  conduit boxes and run, pipe sleepers (4), the fan housing, the E dunnage deck, THE LOFTLARK's deck, bar, loungers,
  umbrellas and planter boxes.
- **Lane A-MT, still to make:** THE LOFTLARK's furniture and neon, the roof boxes above, the city bus, the Midtown facade
  tables and the east podium modules (theatre marquee, hotel canopy), the storefront carriers for the bands in
  Sign_MT_Atlas1, the premiere's big pieces the data blocks out (broadcast, satellite, catering, cable, staging and
  generator trucks, trailers, light and truss towers, press walls, tents and booths, the info and security booths, the
  speaker stack and sound tower), the plaza's small dressing with colliders (bollard planters, newspaper boxes, newsstands,
  phone kiosks, wayfinding pylons, hydrants, sign poles), and the crowd's leftovers (12.4).
- **Design to confirm (lane D's deviation):** the Stand's wings and front court; the art follows the data.
- **Lane C:** done (names.md); the owner's sign-off on the list, and the US trademark-register search names.md asks for
  before release, are still to come.
