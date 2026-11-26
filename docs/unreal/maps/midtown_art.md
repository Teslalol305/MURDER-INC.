# Midtown art: the roofs, the screens' backs and the scaffold (lane A-MT, stage 1)

What MAPS.md lane A-MT made without Unreal and without the box (2026-11-26), how it measures against
[midtown.md](midtown.md) 11, 12, 14 and 15, every invented name it uses, and what is still open. The code is
`art/blender/assets/midtown.py` and its `_midtown_*.py` modules; the outputs are in `art/out` (git-ignored), the pictures in
`art/previews/maps/mt_*.jpg`.

```
venv/bin/python art/blender/build.py build midtown --export                # 39 meshes, manifests, placements (about 10 s)
venv/bin/python art/blender/build.py build midtown --bake --export         # the same, redrawing the five face sets (about 2 min)
venv/bin/python art/blender/build.py build midtown --preview --samples 12  # mt_roofs, mt_gantry, mt_square, mt_faces
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

## 3. Placements (`art/out/placements/placements_midtown.json`, 720 instances)

The west block's five roofs at their collider heights (A 21.2, B and C 17.6, D and E 14.0): 159 deck panels, 136 parapet
modules broken at every opening of 5.3 (L1 to L4, the planks, the pipe bridge, the drops D1 and D2, the gantry doors, the
service bulkhead), the rooms at their interior boxes of 9.1 with the doors where 9.1 puts them, the four stairs and two
bridges on their 5.3 lines, the gantry and G1 over the west sidewalk, C1 on C's east edge, the scaffold tower's 8 flights,
8 landings, 63 frames and 25 netting panels on the levels of 5.3 (the east landings and the shed-hop lift left open), and the
art-only screens past the bounds. Positions the design leaves open carry `"chosen": true` (WT-A at (-38, -25), WT-B at
(-45, -5), bulkhead B at (-44, 3.5), the HVAC rows, the art-only screens): lane D's colliders win where they differ.

## 4. Every invented name this lane uses (all to be searched, MAPS.md C1)

From midtown.md 12.2 and 12.4, unchanged: ORBELLE (Eau de Nuit), NORTHBOUND AIRWAYS (Fly the late one), KESTREL MOBILE
(Five bars, five boroughs), BRASS & BUN (Burgers till four), THE ALDERWAY THEATRE and its show NIGHT SHIFT (a new
musical), VESPERLINE CRUISES, QUILLON (watches), TAMSIN GRAY (fall collection), HALCYON SODA, DUSKLINE TOURS (The city
after dark), MARLOWE & FINCH (The holiday floor is open), SEVENTH AV SOUVENIRS, MIDTOWN SLICE, 46TH ST CAMERA &
ELECTRONICS, LANTERN SAVINGS, HOTEL CASTELLANE, BRANNIGAN'S CHOP HOUSE, CORNER CHEMISTS, HALVORSEN BUILDING, CORVIN HALL,
KESSLER & ROTH SCAFFOLD, BRIGHTWIRE EVENTS, CITY CROSSTOWN, THE PERCH (listed; its neon is the square lane's), the VLTR tag,
the ticker's three headlines.

Added by this lane (generic words, no business name): the sub-lines STAGING · LIGHTING · SCREENS (Brightwire) and SIDEWALK
SHEDS · SCAFFOLD · HOISTS (Kessler & Roth); the labels ROOF DOOR / KEEP CLOSED, MACHINE ROOM / AUTHORIZED ONLY, DANGER /
HIGH VOLTAGE, TANK 2 / DRINKING WATER; PRESENTS under the IPX mark; NO SIGNAL and STAND BY. No phone number, no web address,
no real brand; IPX is the only real mark. The single source is `art/blender/assets/_midtown_names.py`, and
`art/out/midtown/signs_midtown.json` lists every string with its cell.

## 5. Checks (`_midtown_check.py`; results of 2026-11-26)

english (76 strings, plus 61 in the atlas cells and ticker: ASCII, the middle dot and the degree sign only), names (IPX on
the 3 IPX slides only), validation (39 of 39), budgets (39 of 39), thin (no member over 0.6 m long under 5 cm across),
files (every GLB on disk and in the shared manifest with the same triangles and bounds), atlases (2 x 8 slides, no overlap;
ticker, digits, mask sizes; 18 faces, no overlap), placements (every mesh, face, slide and tile accounted for), emissive (7
screens, 46 MB, no new tiling set), block (facade.py, signs.py, place_buildings.py, level.json and levels.json untouched;
nothing written under unreal/MurderInc): ALL CHECKS PASS.

## 6. Hand-off and what is still open

- Hand-off: `art/out/maps-midtown.tar` with its sha256 and file list in `art/out/midtown/ARCHIVE.json` (the GLBs, the five face
  sets, the lane manifest, signs_midtown.json, placements_midtown.json, midtown.blend), as the Canal lane's archive. The TS_*
  scans the slots name are the Block's (not in the archive).
- **Box and engine (lane B, L, E11):** the import (send-art patterns `SM_Roof_*`, `SM_Scaf_*`, `SM_Sign_LEDWall_*`,
  `SM_Sign_Ticker_4m`, `SM_Sign_TowerStack`), `M_MI_Screen` and its MPC, the per-instance tile offsets, the night rig and the
  picture rounds at V1 to V6; flicker.py at V2 to V4.
- **Lane D:** fit the placements to the Midtown colliders when the layout exists (the decks and parapets follow 2.1 exactly; the
  chosen positions may move).
- **Lane A-MT, still to make:** the square family (the Stand and the Booth, planters, kiosks, carts, café furniture, light
  poles, barriers, generator, cable ramps), THE PERCH's furniture and neon, the city bus, the Midtown facade tables and the
  east podium modules (theatre marquee, hotel canopy), the storefront carriers for the bands in Sign_MT_Atlas1, the crowd's
  leftovers (12.4).
- **Lane C:** the name searches; the sign art is final only after them.
