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

---------------------------------------------------------------------------------------------------------------
# Weapons (assets/weapons.py, mi/rig.py, mi/texpaint.py)

Task: SK_Chopper and SK_Nine (skinned, one bone per moving part, sockets, unique 4K sets T_Chopper_* / T_Nine_*),
their magazines + top rounds (2K), rifle and pistol casings (512), Goon SMG (2K) and pipe (1K); previews
weapons_chopper_hero/_fp, weapons_nine_hero/_fp, weapons_parts, weapons_wire, weapons_enemy; README row.
Decisions: textures are authored in UV space with numpy from baked geometry maps (mi/texpaint.py) instead of
baking node trees; skinned assets export through mi/rig.py (export._Stubs, all bones incl. sockets) and are proven
by re-importing the GLB in a fresh process and posing every bone.

## State at hand-off: task complete (render budget used: 12 of 12)
- Exported, validated, manifest current: SK_Chopper 72.9k tris (4K set Chopper), SK_Nine 35.8k (4K set Nine), both
  proven by re-import in a fresh process (every bone posed, max error 1e-8 m, joint axes = gun axes, SK_*.glb.verify.json);
  SM_Weapon_ChopperMagazine 8.5k + _TopRound 3.2k (2K), SM_Weapon_NineMagazine 13.2k + _TopRound 2.7k (2K),
  SM_Weapon_CasingRifle 596 / _CasingPistol 548 (512), SM_Weapon_GoonSMG 12.8k + _Magazine 0.8k (2K, lens slot), SM_Weapon_GoonPipe 3.0k (1K).
- Previews: weapons_chopper_hero/_fp, weapons_nine_hero/_fp (fp rendered before round 1: older grip outline and set),
  weapons_parts + weapons_wire (one wide render split in two), weapons_enemy. Review rounds: (1) scratches shorter and
  sparser, handguard swell, NINE grip curves, hero framing, FP on the day rig with an urban plate instead of a column
  shadow; (2) parts/wire framing.
- Known weaknesses: NINE grip reads as a large flat slab (brief's 76 mm butt); ngon caps give long slivers in the wire;
  parts picture overlaps the rocked magazine and the NINE; wood handguards are still blocky in profile; no follower model
  in the CHOPPER magazine (the second round fills the lips); SMG is mid-detail (12.8k of 25k).
- Exact next step if resumed: give the NINE grip finger grooves + stippled front strap, re-bake Nine
  (`build.py build weapons --only nine --bake --rebake-unique --export`), then re-render weapons_nine_hero/_fp.

---------------------------------------------------------------------------------------------------------------
# Vehicles (assets/vehicles.py), vehicle artist

Task: the eleven vehicles of props.json (vehicle_*), generated bodies (Higgsfield) cleaned and completed by script,
GLB + manifest + validation, previews vehicles_*.jpg, README row.
Method: concept picture (gpt_image_2_6, 2 credits) -> hunyuan3d_v3_image_to_3d (60-100k faces, PBR, 19 credits)
-> mi/gen3d.py (new module: load GLB + maps, weld seams, orient, fit to the brief box, warp x onto the briefed axles,
per-face texture sampling) -> vehicles.py (classify faces by colour/roughness/position into paint, trim, lamps,
glass, cabin; modelled wheels, glass panes, solidified shell, interiors, plates, liveries as shrink-wrapped decals).
Ledger of every generation: art/blender/assets/vehicles_gen.json (job ids, models, credits, files, verdicts).

## Decisions
- Provider comparison on the sedan: Meshy 7 (44 credits) clean but flat underside and 2K maps; Hunyuan3D v3
  (15-19 credits) 4K maps, modelled underside, better detail. Hunyuan kept for every body.
- 500k-face bodies cannot be decimated once their UV seams are welded (faces across seams scramble the atlas):
  bodies regenerated at 60k (cars), 80k (trucks), 100k (motorbike) and used undecimated.
- Variants from base bodies: taxi, burned and stripped car from the sedan, Vulture van from the van (same atlases).
- Glass is see-through (tinted, translucent) with a dark interior behind it rather than the brief's opaque near-black:
  the task asks for interiors; Unreal can still darken the tint.

## Status
- [x] Credits: balance 5254.24 at start; vehicles spent 302 (ledger, checked against the transaction list).
- [x] `build.py build vehicles --export --force` (about 4 min): 13 assets validate and export, 58k-149k triangles
      (Sedan 120k, SUV 111k, Pickup 105k, Van 122k, Taxi 119k, BurnedCar 77k, StrippedCar 58k, Van_Vulture 119k,
      BoxTruck 141k, IPXTruck 149k, IPXTruck_Door / _Door_Left 0.8k, Motorbike 90k); manifest current.
- [x] Hero round 1 fixed: texture rows (write_set wants row 0 at the bottom), glass rule (dark + greenhouse +
      windscreen by position + majority fill), plate orientation, dash and plate backing to the interior slot.
- [ ] Previews: hero, close, lineup_1, lineup_2, ipx_truck, wrecks rendering from the saved blend (no rebuild):
      scratch script opens art/out/blend/vehicles.blend and calls vehicles.on_preview; then vehicles_wire.

## Exact next step
Look at art/previews/vehicles_*.jpg, fix the worst fault, re-render that one (`build.py build vehicles --export`
then `--preview --only <name> --samples 40`, or the blend-only script), then vehicles_wire, then final report.

---------------------------------------------------------------------------------------------------------------
# Generated Goon (assets/goon_generated.py), character technical artist: a Higgsfield image-to-3D comparison

Task: one generated goon_hoodie (concept picture -> image-to-3D, textured, PBR, A-pose, high poly), scaled and bound to
the mannequin skeleton from art/out/epic/ (weights from the mannequin mesh; nothing Epic-derived is committed),
previews goon_generated_{hero,detail,pose,wire}.jpg, art/out/glb/SK_Goon_Hoodie_Gen.glb, and a verdict.

## Status
- [x] concept front (gpt_image_2_6 high 2k, 2 cr) and back view with the crew V (2 cr): art/out/gen/goon/concept1*.png
- [x] take 1: meshy_v7_image_to_3d, texture + PBR + a-pose + ultra, 300k target (44 cr): 311k tris, one 2k atlas
      (BC, metal-rough, normal): goon_meshy.glb. KEPT (black reads black, mask slits modelled, closest to the brief)
- [x] take 2: hunyuan3d_v3_image_to_3d front + back views, PBR, 300k faces (23 cr): 4k maps, but washed-out greys,
      shiny light jeans, an invented red glyph on the chest, flat mask: goon_hunyuan.glb (not used;
      GOON_SRC=art/out/gen/goon/goon_hunyuan.glb build ... runs it through the same script)
- [x] bound to SKM_Manny_Simple (89 bones): limbs posed onto the mesh, weights copied from the posed mannequin body,
      fingers folded into the hands, inverse skinning back to Manny's reference pose; round trip exact; exported
      joints equal SKM_Manny_Simple.glb's (quaternions within 1e-6), so UE5 animations play without retargeting
- [x] `build.py build goon_generated --export --preview --samples 64` (8.5 min): art/out/glb/SK_Goon_Hoodie_Gen.glb
      (24.3 MB, skinned to the 89 Manny joints, generated 2k maps embedded); previews looked at:
      goon_generated_hero / _detail (3 m, 1 m) / _pose (A_rifle_jog_fwd, A_rifle_idle_ads) / _wire. 9 renders in all
      (2 test heroes, one per take, then 7 final): one over the budget of 8.
Spent: 71 credits (2 + 44 + 2 + 23, matched in the transaction list); balance 5260.03 at the start, 4902.42 at the
end (the rest of the drop is the GPU box and the other agents' generations).

## State at hand-off: task complete. Verdict: do not use the generated Goon as the game asset (at most as a
## silhouette / proportion reference)
Against "a current AAA enemy seen from 3 to 40 m": from 10 m and beyond it reads right (black figure, oxblood
accents, pale mask, good jeans); at 3 m and closer it fails. Weaknesses, most visible first: the hoodie reads as
glossy vinyl (flat roughness 0.7, no fabric sheen, no weave), baked seam cracks and smudges from a 2k atlas cut into
hundreds of islands (about 7 px/cm, a hero enemy wants 4-8 4k sets), shading baked into the colour (folds darkened in
the albedo); one fused shell (hoodie, jeans, gloves, mask in one surface, no layers to cloth-simulate, no inner hood
or neck), irregular triangles with no edge loops at shoulders, elbows, knees (deformation is skinning-only and will
crease and collapse at the armpit, crotch and a kneel), small tears on the left upper arm; gloves modelled flat and
spread (fingers are bound rigid to the hands, so no grip); no crew V on the back and the back is invented; the mask is
white rather than bone; 311k triangles with no LODs.
Next step (if wanted): none for this asset. The hand-built Goons (assets/characters.py) stay the plan; the generated
mesh can serve as a fold/proportion reference. To redo the comparison with the other take:
`GOON_SRC=art/out/gen/goon/goon_hunyuan.glb venv/bin/python art/blender/build.py build goon_generated --export --preview`.

---------------------------------------------------------------------------------------------------------------
# Catalogue gaps (assets/gaps.py, assets/_gaps_art.py), started after the signs hand-off

Task: (1) every non-vehicle catalogue id without a mesh; (2) properly sized modelled versions of the mismatched scans,
named as the catalogue names them; (3) gameplay wrecks, progress strip, boombox meter, heat masks, master-case lid fix;
(4) the flat placeholder graphics drawn, gold balls and barber pole, a clean white painted-steel set. Previews
gaps_street / gaps_yard / gaps_gameplay / gaps_graphics.
Decisions: trees and hedges have MODELLED leaves (8-triangle polygons cut to the drawn leaf outline, opaque, no alpha):
Nanite draws opaque geometric foliage cheaply and Lumen lights it correctly, masked cards cost overdraw and break
Nanite culling. No bark or leaf scan is catalogued, so bark, leaves, kraft board and brushed stainless are drawn with
numpy as tiling sets. SM_Furn_StreetLamp already is the 7.88 m cobra head (0.34 x 2.74 x 7.88): no new lamp.

## Status
- [x] _gaps_art.py: numpy sets TS_Bark_Pear, TS_Leaf_Pear, TS_Leaf_Privet, TS_Cardboard_Kraft, TS_Steel_Stainless; 30 faces
      (furniture graphics, new faces, five licence plates)
- [x] gaps.py: 36 assets exported, validation clean (`build.py build gaps --bake --export --res 1024`), incl. the two ids found
      with no mesh at all besides the briefed list: street_hydrant_open (SM_Street_Hydrant_Open), sign_license_plate
- [x] props.py `build_gaps_pass`: PropaneTank_Wreck, WeldingRack_Wreck (unique bakes), MasterCase_Progress, Boombox_Meter,
      heat masks T_Gameplay_<Name>_Heat.png (`--only heat`), lid track + lozenge moved to the free edge (lid rebaked)
- [x] furniture: drawn faces picked up, white = TS_Steel_PaintWhiteClean; re-exported (`build furniture --export --res 1024`)
- [x] previews: 8 renders in two rounds (gaps_gameplay x2, gaps_street x2, gaps_yard, gaps_graphics x3 incl. a fix check)
- [x] README family row

## State at hand-off
Every non-vehicle catalogue id now has a mesh. Ids whose mesh exists only under another family's name (SM_Furn_*, SM_Facade_*,
SM_Prop_* scans, SM_Gameplay_MasterReel_1/2/3, SM_Street_ManholeCover): the level must map them (aliases not exported).
Known weaknesses: trees are 200k triangles each (Nanite only; build a LOD/impostor for non-Nanite paths) and their branching is
procedural, not a botanical model; the props unique unwrap is not deterministic between runs (MasterCase warns "re-unwrapped"
when rebuilt without --bake: always export it together with --bake); vulture stencil reads more hen than vulture; licence-plate
characters are printed, not embossed; heat masks are distance fields round the valves, not a simulated scorch.
