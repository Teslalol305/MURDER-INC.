# Progress (art/blender)

Task: library check + README, scan-backed materials + HDRI day rig, the El kit (assets/el.py), look-dev previews.

## Done (earlier runs, reviewed by the current run where marked)
- mi/mat.py: `from_scan(set_name, ...)` / `ctx.scan_set(...)` build materials from catalogued scans (reviewed: in use).
- mi/steel.py: riveted-steel builder (plates, angles, rivets, leak sources for the wear mask).
- assets/el.py: SM_El_Column, SM_El_Bent, SM_El_GirderSpan_10m, SM_El_Deck_10m, SM_El_Lamp + layout + on_preview.
- art/previews/el_wire.jpg rendered (clay): detail reads well.
- art/out/glb/SM_El_*.glb exist from the earlier run (not yet re-validated by this run).

## In progress (this run)
1. `build.py build el --export` : confirm build + validation end to end.
2. Render el_day_hero / el_day_column / el_day_under (`--preview --only <name>`), then street_day_hero refresh.
3. README.md.

## Exact next step
Run: `python art/blender/build.py build el --export` and read the validation output.

## Update (this run)
- `build el --export` passes validation: column 32156, bent 42900, span 108844, deck 62228, lamp 2220 tris.
- Rendered el_day_hero, el_day_column, el_day_under (64 samples, HDRI day rig). README.md written.
- Review round 1 fixes applied in code (el.py on_preview cameras: hero closer to the kerb and aimed under the
  structure, column camera includes the pedestal; lamps off by day; pale blotches removed from the dressing walls).
- Next: re-render `build el --preview --only el_day_hero,el_day_column --samples 64`, then
  `build street --preview --only street_day_hero --samples 64`, look at each, one more fix round at most.
- Round 1 re-renders done (hero, column: good). street_day_hero refresh rendering.
- Round 2 (last): hero aimed further under the structure (target y +3.0); el_day_under re-render with lamps off.
  Command: `build el --preview --only el_day_hero,el_day_under --samples 64`. After that: final `build el --export`
  and `build street --export` to leave manifest and GLBs current, then report.

## State at hand-off: task complete
- Round 2 renders done and looked at: el_day_hero, el_day_under (lamps off), street_day_hero refreshed.
- Final `build el --export` and `build street --export` passed validation; art/out/manifest.json is current.
- Nothing is pending. Known weaknesses (for a later pass): preview dressing is blank brick massing and a low yard
  wall; guard rails are timber only (no steel inner guard rail); the street's utility patch reads as a flat dark
  rectangle; wear masks are per-vertex at about 0.15 m, so rust edges are soft until Unreal adds detail noise.

---------------------------------------------------------------------------------------------------------------
# Facade kit (assets/facade.py), started after the El hand-off

Task: modular street-front kit (ground floor, upper floors, top, fire escape, roof items), assembly helper, sample
of the south block face (S1 + S2 + S3, seven storefronts) with the street and three El bays, four previews
(facade_day_hero / facade_day_street / facade_storefront / facade_wire), GLB export + manifest + validation, README.

## Status
- [x] assets/facade.py written (modules + `assemble_front` / `assemble_shell` helpers + on_preview)
- [x] `build.py build facade --export` passes validation: 77 modules, no warnings (run 3 fixed the mirrored hoop lugs of the water tank)
- [x] previews round 1 rendered and looked at (wire, hero, storefront, street)
- [x] round 1 fixes in code: glass film/dirt much lighter (store glass read milky), hero +0.5 and storefront +0.9 stops,
      cornice run stops 2 mm inside the end block (coplanar caps rendered as a black patch in clay)
- [x] round 2 (last) rendered and looked at: glass clear with reflections, clay corners clean
- [x] README family row; final `build facade --export`: 77 GLBs, no validation errors or warnings, manifest current

## State at hand-off: task complete
Known weaknesses: sign bands are flat colour placeholders; glass shows only reflections (no interior parallax yet); previews under the El stay dark; the roll-gate bay (Nails, S3) is in no preview; no rear walls or N-side buildings in the sample.

---------------------------------------------------------------------------------------------------------------
# Props family (assets/props.py), started after the facade hand-off

Task: (1) scanned Poly Haven props brought to the conventions as SM_Prop_* (one slot M_<Asset>, scanned textures
copied/atlased to art/out/textures/<Asset>/T_<Asset>_BC/N/ORM); (2) hero gameplay props SM_Gameplay_* (master case
body / lid / reel 1-3 / beacon, propane tank, welding rack) with unique baked sets; (3) previews props_scanned.jpg and
props_gameplay.jpg; export + manifest + validation; README family row.
Decisions: payphone (KT / T-money marks), Television (VTech mark), Drill (trade dress), coffee-cart props (real-looking
coffee brands), modular duct/pipe/cable kits, lamps with emissive maps, desk, stool, video camera: not imported.
Catalogue: no resupply item exists (05b 2.5.3), so no resupply crate.

## Status
- [x] scanned part written and exported (`build.py build props --export`): 30 SM_Prop_*, validation clean
- [x] gameplay part written, baked and exported (`build.py build props --only gameplay --bake --export`, 4.5 min):
      SM_Gameplay_MasterCase, _Lid, _Beacon, MasterReel_1/2/3, PropaneTank, WeldingRack, validation clean
- [x] previews rendered and looked at (3 renders): props_scanned.jpg, props_gameplay.jpg; fix round 1 = round gauge faces
- [x] final `build.py build props --export`: 38 assets, no validation errors or warnings; README family row

## State at hand-off: task complete
Catalogue ids covered by scans: jersey_barrier (1.55 m segments), oil_drum, trash_can (lidded can, not the wire basket),
tool_chest (top chest only), shelf_rack, crate_wood (smaller crates), cardboard_boxes (single carton), bench (1.17 m),
tire_stack (single tyre), food_cart (body only), boombox, hydrant (alternative), propane_tank (dressing).
Gameplay: master_case (body, lid, beacon, reels 1-3), propane_tank, welding_rack. No resupply item in the catalogue.
Not done: wrecks (SM_Gameplay_PropaneTank_Wreck / WeldingRack_Wreck), progress-bar strip and boombox level meter
(emissive bits), heat-glow masks, food-cart umbrella and hot-dog gear, phone_booth (payphone scan excluded: real marks).

---------------------------------------------------------------------------------------------------------------
# Furniture family (assets/furniture.py), started after the props hand-off

Task: street furniture and yard structures not covered yet (SM_Furn_*): street items, sidewalk shed + stair,
chain-link panels/posts/gates (alpha card TS_ChainLink_Galv, generated by chainlink_set()), court (hoop, bleachers),
lot booth, cobra street lamp, court light, billboard, roll-up doors, cinder-block wall modules + steel door.
Previews furniture_street.jpg / furniture_structures.jpg; export + manifest + validation; README row.

## State at hand-off: task complete
- 59 SM_Furn_* exported (`build.py build furniture --export --res 1024`), validation clean (no errors, no warnings), manifest current,
  303k triangles in all (billboard 49k, shed 32k, sandbags 25k, the rest under 16k). README family row added.
- Previews rendered and looked at (5 renders): furniture_street.jpg, furniture_structures.jpg (fixes: bag and sandbag shapes, darker
  sacks, booth paint less rusty, framing with the 1.8 m scale box).
- Catalogue ids still not covered (vehicles excluded): phone_booth, traffic_light, planter, tree, generator, floodlight_stand,
  porta_potty, vending_machine, workbench, engine_hoist, compressor, car_lift. Partly covered: trash_can (no wire basket), bench (scan
  is 1.17 m, catalogue 1.76), crate_wood and cardboard_boxes (single small pieces), tool_chest (top chest only), hydrant_open (no jet),
  sign_post (no street-name blade). Level structures not built: hoardings, rolling scaffolds, hoist tower, tyre cage, kiosk, scrim and
  tarp on the fences, the garage's skylights and extractor fan.
- Known weaknesses: white paint (booth, hoop board) comes from a warm, rust-spotted scan and reads dirty; stencils, scrawls and the
  mattress ticking stripes are left to decals; signs are flat placeholder colours; chain-link has no tie wires or knuckled selvage.

---------------------------------------------------------------------------------------------------------------
# Signage (assets/signs.py), started after the furniture hand-off

Task: the ten storefront signs as built objects SM_Sign_<Brief> (briefs in docs/unreal/spec/assets/signs-fx.json),
their faces T_Sign_<Shop>_BC/_ORM(/_E) drawn with PIL (sets Sign_<Shop> = slot M_Sign_<Shop>, shop keys of facade.SHOPS),
IPX billboard (Sign_Billboard), bus-shelter one-sheet (Sign_BusShelter), mural (Sign_Mural + SM_Sign_Mural decal card);
wire into the band / furniture slots, re-export, previews signs_sheet / signs_street / signs_ipx, manifest, README.
Decisions: fonts Inter Display Black (heavy grotesque), set at 70-82 % width as the condensed face (no condensed face is
installed), Inter Bold for sub lines, Inter ExtraBold Italic for the IPX mark, DejaVu Sans Bold / FreeSans Bold for variety.
Types: lightbox (Laundromat, Deli, Pizza, Chicken raised face), exposed neon on pan (Barber, Pawn), neon over painted wood
board (Records), LED flex in acrylic box (Nails), open-face pan letters on a raceway (ChecksCashed, Liquor; the sub line
and the old-sign ghost are on the band face M_Sign_<Shop>).

## Status
- [x] mat.sign_face(key, colour) added; facade.materials and furniture.materials use it (flat fallback without textures)
- [x] assets/signs.py written (textures + meshes); faces drawn (`build signs --force` redraws, ~90 s)
- [x] `build.py build signs --export` passes (11 assets)
- [x] facade SignBand_* and furniture Billboard / BusShelter re-exported with the textured slots (validation clean)
- [x] previews rendered and looked at (4 renders): signs_sheet (twice: originals at the origin showed), signs_street, signs_ipx
- [x] README family row; manifest current

## State at hand-off: task complete
Known weaknesses: no true condensed face (Inter Display Black squeezed); neon tubes follow glyph outlines (double tube per
stroke) as the brief asks, not a sign-bender's single stroke; pan-letter tubes are an inset outline; faces have no normal maps
(seams, wrinkles, flaking are colour only); signs are not in the El hero views; Pawn's gold balls, the barber pole, the S3
shed banners (M_Sign_ShedBanner_*), booth, flag and other furniture graphics still flat colours.
