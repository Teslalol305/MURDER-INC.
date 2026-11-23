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

## State at hand-off
- Credits: balance 5254.24 at the start, 4500.02 at the end; the vehicles spent 302 (2 x 13 concept pictures at 2,
  Meshy sedan 44, six 500k Hunyuan bodies at 15, seven 60-100k Hunyuan bodies at 19), every job in
  assets/vehicles_gen.json, matched in the transaction list; the rest of the drop is the GPU box and other agents.
- 13 assets export and validate (`build.py build vehicles --export --force`, about 4 min): Sedan 120k tris, SUV 111k,
  Pickup 105k, Van 119k, Taxi 119k, BurnedCar 77k, StrippedCar 58k, Van_Vulture 118k, BoxTruck 141k, IPXTruck 136k,
  IPXTruck_Door / _Door_Left 0.8k each, Motorbike 90k. Manifest current; README rows (gen3d, vehicles).
- Previews (14 renders, the cap): vehicles_sedan_hero, _close, _lineup_1 (final); vehicles_lineup_2, _ipx_truck and
  _wrecks were rendered BEFORE their last fixes (Van and IPX noses were reversed: fixed; IPX vault still showed a
  generated internal partition: removed and verified on the mesh; wreck engine bays trimmed). vehicles_wire not
  rendered (cap reached). Re-render those four first.
- Known weaknesses: generated paint keeps some soft blotches of baked light; glass detection is per-vehicle rules
  (the van's rear doors keep large windows, light glass in the picture read as paint); wipers/cowl read as a black
  plank; the van's front overhang is squashed by the warp onto the briefed axles (generated wheelbase 2.8 vs 3.2);
  the stripped car is a gutted shell with a crude floor; interiors are simple boxes; decals are flat cards.

## Review pass (independent review, art/blender/review/: grades 1-3)
- Noses: the Van, Van_Vulture and IPX GLBs were still reversed (SPEC nose was +1). Now nose=-1 and gen_body runs
  nose_check(): more sloped screen area facing +X than -X in the upper body, else AssertionError (logged per body:
  Van 0.106 / 0.015, IPX 0.072 / 0.012, Sedan 0.097 / 0.078, SUV 0.085 / 0.065, Pickup 0.072 / 0.028).
- Positions re-measured on the turned bodies (texel grids of lum / roughness): Van windscreen x 1.62-2.12 below
  z 2.02, cab side glass x 1.00-1.95 z 1.40-2.02, rear door glass, all dark texels (glass_boxes in SPEC); IPX is a
  conventional cab (windscreen x 1.36-1.62, z 2.22-2.74), rear door plane measured by _ipx_drop at x -3.259
  (IPX_DOOR_X), partition rule only inside |y| < 0.85 so the vault skin and the flank art stay.
- Every generated body: class_vote() majority filter on face classes (sawtooth rims); smooth_paint() Taubin pass on
  paint-only vertices; smooth_normals() bilateral diffusion of the paint normals written as custom split normals
  (dents and ripples gone from the clear-coat reflections, silhouettes kept); body_set() divides paint by a coarse
  masked low-pass (48 cells) instead of the global median and high-passes the paint normals (baked blotches out).
- Cowl and wipers (Sedan, Taxi, SUV, Pickup, Van, Vulture): the generated plank and the dash 'teeth' deleted
  (cowl_fit), a 8 mm louvred panel fitted from the bonnet's rear edge to under the glass base (ray casts), two
  parked wipers (pivot caps, arms, blades with rubber) laid on the glass.
- Plates: number fitted to 85 % of the plate width (sets regenerate, text_fit in set.json); the generated holder
  under the card goes to the dark backing; cards kept inside the briefed length.
- Manifest: slot_records() writes textures + shading for the stripped car's primer (tint #7a3b2c, roughness 0.78),
  the IPX door paint, the motorbike paint_default (#1b2a4a).
- Vulture: load space 2.94 x 1.40 x 1.30 with hat-section ribs, roof ribs, cant rails, wheel-arch boxes and
  tie-downs; painted aperture frame and rubber seal; leaves with pressed outer panel, inner skin with lightening
  holes, lock rod, window, handle, two hinges each, check strap, hinge brackets; stripe stops at the rear arch.
- Box truck: the generated (crumpled) cargo box deleted and modelled (truck_box: skin in the Paint slot, side
  posts, galvanised rails and corner posts, roll-up slat door with handle and hasp, red top markers on the Lamp slot
  via the set's tail_uv); cab white split at the measured box front.
- Pickup: seats were standing behind the generated cab back wall: moved 0.57 forward into the cab; the bed inside
  (amber/paint sawtooth, the floor was read as amber lamp) is black bedliner (trim).
- SUV: quarter lights are glass (side_glass), headlamps by a position box (head_box). Taxi door lettering 0.08
  higher, clear of the rub strip. Motorbike seat is trim (black), side-stand foot meets the ground after the lean.
- Wrecks: bumpers, plate holders and lens faces cut from the shells; burned car charred by position (roof, window
  frames, bonnet rear) cleaned by the majority filter; stripped car keeps sills and B pillars.
- Credits: none spent in this pass (no regeneration was needed for the faults fixed).
- Still open: SUV front fascia keeps some generated jaggies (a cleaner concept + regeneration would fix it); the
  stripped car's door cut edges are ragged; the box truck's fuel tank is the generated lump; hubcaps are plain;
  the burned car's rust scan still streaks along X; interiors are simple boxes.
- Review renderer: `python art/blender/review/vehicles_review.py --only Van,...` renders contact sheets from the
  exported GLBs (it applies paint_default to Paint slots only, so the primer renders white there).

## Review pass, continued after a machine restart (same task)
- Checked first: the export after the pass above had completed (all 13 GLBs validated); the preview run was cut.
  Fresh review sheets of Van, Van_Vulture, IPX, SUV from the exported GLBs: noses correct (+X), Vulture load space
  and leaves at the real tail, IPX vault and leaves at the tail, flank art on both IPX flanks.
- Box truck: generated tank / step lumps under the cab corners dropped; modelled fuel tank (0.52 x 0.90, polished,
  two black straps with rubber liners, brackets, filler neck and cap, diamond-plate step) on the right and a black
  battery box with lid, latch and diamond-plate step on the left (truck_tank); chassis paint below the box floor is
  trim (mud flaps, brackets no longer mustard); red top markers and two modelled tail lamps in chrome bezels read
  the sedan atlas's red lens (slot M_Vehicle_BoxTruck_Marker_Lamp: the box truck atlas has no red-lens texels).
- Every generated body: shard filter (fragment_mask) drops loose islands of < 12 faces or < 15 cm2 left by the
  class deletions (Sedan 15, SUV 40, Pickup 34, Van 13 faces); guarded against unwelded bodies.
- Stripped car: door apertures cut on straight planes (clean_cut: bisect, then delete inside the box), bonnet lifted
  off along straight shut lines, loose fragments dropped, pressed floor pan (tunnel, cross-members, heel kick,
  ribs). Burned car: soot by height in coherent 0.22 m blotches (black cabin and roof, patchy flanks, rust low and
  on the arches), rust scan rotated so its streaks run down the panels, hanging overhang fragments cut.
- SUV (hero): modelled fascia fitted by ray casts (suv_fascia): chrome grille bars and surround (curves fitted, not
  the crumpled surface) over a black backing, per side a headlamp unit (chrome reflector card, two reflector bowls
  with bulbs, bulged lens on MI_Glass_CarTint, chrome bezel).
- IPX: the band and panel decals reject ray hits through the open doorway (decal(min_y)): no gold strip across it.
- Cowl (Sedan, Taxi, SUV, Pickup, Van, Vulture): the panel's rear edge follows a curve fitted to the front-most
  glass-base hits (the ragged glass border pulled grey 'teeth' up the windscreen), it is no wider than the glass
  base (no block past the A pillar), the plank kill reaches the A pillars, and the generated dash top under the
  glass base is dropped so the modelled dash shows (Sedan 188, SUV 284, Pickup 49 faces).
- Previews: _show() set rotation_euler on objects in QUATERNION mode, so every preview yaw was ignored (that is
  why older IPX / Vulture previews showed the cabs): rotation_mode is now XYZ. All seven previews re-rendered
  after the last asset change, one preview per process (the shared memory cgroup OOM-killed a batch run).
- Credits: none spent (no body needed regeneration for the faults fixed).
- Still open: SUV rear quarter panel keeps a light crumpled patch at the C pillar and a corner-lamp shard; the
  stripped car's fender tops and rear-screen frame keep some ragged edges; the Van's windscreen base still shows
  torn white edges at the cowl; the sedan's front door / fender seam shows a generated crease in reflections;
  interiors are simple boxes; Pickup bed is reclassed, not a modelled liner.

## Exact next step
Previews are rendered from the saved blend without a rebuild (scratch: open art/out/blend/vehicles.blend,
ctx.assets = SM_Vehicle_* objects, vehicles.on_preview(ctx, [])). Next: the SUV quarter panel and corner lamp
(regenerate from a flat-lit black concept, about 21 credits, or a position box for the quarter), the Van cowl edge.

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

---------------------------------------------------------------------------------------------------------------
# Characters (mi/char.py, mi/sdf.py, mi/texel.py, assets/characters.py, tools/box/chars/), pipeline and the player's arms

Task: scratch Unreal project /project/ue/chars (MCP 8002); Epic mannequin, clips and template guns exported to
art/out/epic (never committed); round-trip proof; SK_RuleArms on SK_Mannequin (skin, glove leather, glove suede,
rubber; 4K sets), SM_Character_RuleWatch, SM_Character_RuleBracelet; pose tests; proof in Unreal.

## Status
- [x] scratch project, export (glTF + FBX) of SKM_Manny_Simple, 7 clips, SM_Rifle, SM_Pistol -> art/out/epic
- [x] round-trip proof (docs/unreal/CHARACTERS.md, shots/chars-roundtrip.jpg): 0.00008 cm per bone in Unreal
- [x] SK_RuleArms: SDF anatomy and glove on the mannequin's bones, glove-pattern UVs, per-finger weight transfer,
      mirrored left arm, 108,398 triangles, two 4K sets computed per texel; watch and bracelet with attach frames
- [x] pose tests (viewmodel camera at 54 deg, arm IK onto SK_Chopper / SK_Nine, finger curls): two fix rounds
- [x] Unreal: imported on SK_Mannequin with textures, subsurface skin, jewels on their bones, rifle idle and reload

Next step: the hands are the weakest part (rounded fingers without knuckle definition, grips are hinge curls, not
authored grip poses): sculpt-level finger shapes (flatter backs, knuckle creases), per-gun grip poses from the briefed
grip sizes, a socket on SK_RuleArms made by hand in the editor (numbers in docs/unreal/CHARACTERS.md), then the Goons
on the same pipeline (mi/char.transfer_weights, export_character).

---------------------------------------------------------------------------------------------------------------
# Buzzard (assets/buzzard.py), drone artist

Task: SK_Buzzard (skinned, six bones + sockets, unique 4K set Buzzard), SM_Fx_BuzzardRotorBlur, SM_Fx_BuzzardBolt
(+ _Head), the wreck pieces SM_Fx_BuzzardWreck_*, previews buzzard_hero/_under/_detail/_wire/_wreck, README row.
Decisions: reuse weapons.py's modelling kit and texpaint Surf; one unique 4K set read by three slots (M_Buzzard with no
emission, M_Buzzard_Eye, M_Buzzard_Strobe: the game scales E per slot); the UV layout is cached by mesh hash
(art/out/textures/Buzzard/uv_cache.npz) because smart projection differs between processes; wreck pieces are cut
from the skinned mesh (same UVs and set, slot M_Buzzard_Wreck) with jagged caps on the tiling set TS_Composite_Fracture.

## Status
- [x] airframe, rig, skinned export + re-import proof (props turned, gimbal pitched 77 down / 29 up, yawed 86: 5e-8 m)
- [x] 4K set Buzzard (geometry maps 4.4 min + numpy layers 2.5 min on 3 threads), UV layout cached
- [x] effects (blur disc, bolt, head: sets 512), 14 wreck pieces + TS_Composite_Fracture (512); all validate and export
- [x] previews (8 renders, two review rounds): buzzard_hero x2 (backlit, then the sun side), buzzard_under x2 (blur discs
      read as hoops, then translucent), buzzard_detail, buzzard_wire, buzzard_wreck x2 (cropped, then tighter)
- [x] README family row

## State at hand-off: task complete
Known weaknesses: SK_Buzzard is 140k triangles (over the ~120k aim: bells, stators and screws are the bulk); the
underside reads dark against the sky (sun above; Unreal's rim light from the spec will help); surface wear is subtle at
2 m (dust on the deck tops is the strongest layer); the gun is box-built (receiver, rail, holes) rather than machined;
the wreck preview rests pieces on bounding-box corners (some float a few mm) and two bent props touch the frame;
the wreck arms are 17k triangles each (fine for Nanite, heavy for debris without it); no animation clips (the rig is
driven by the game: spin, gimbal, bank).

## Exact next step
None required. If resumed: drop the stator teeth under the windings and the bell's 56-segment rings to 40 to get to
~120k, re-bake (`build.py build buzzard --bake --rebake-unique --force --export`: the mesh hash changes, the UV cache
is rebuilt), then re-render `MI_PREVIEWS=buzzard_hero,buzzard_detail`.

---------------------------------------------------------------------------------------------------------------
# Structures (assets/structures.py, assets/_structures_art.py, upgrade_sets.py), level-structure artist

Task: the level structures still drawn as boxes in Unreal (El station stairs / mezzanine / bridges / platforms,
kiosks, produce stand, hoardings, dig pen, loading dock, garages, the chop shop's inside), fitted to their colliders,
placement data art/out/placements/structures.json; texture-density pass (9 scans to 4K, galvanised + road paint
re-baked at 2048, tile sizes for the tinted slots); previews structures_*.jpg.

## Status
- [x] 4K scans fetched (`fetch.py --res 4k --only ...`, 41 s); TS_Galvanised_Aged, TS_RoadPaint_White/_Yellow re-baked at
      2048 (upgrade_sets.py); manifest: 167 slots given a tile size; mi/export.py fills it for future exports
- [x] 16 faces drawn (Sign_StationName ... Sign_LoadingZone), 27 assets built and exported, validation clean
- [x] fit: every asset measured against its colliders: no vertex outside them or its listed overhead regions, except
      SM_Struct_Kiosk_Candy (18 vertices of the padlock, 16 mm)
- [ ] previews round 1 (5 renders), round 2

## Exact next step
Look at art/previews/structures_*.jpg, fix, re-render the worst (at most 3 more renders), commit.

---------------------------------------------------------------------------------------------------------------
# Weapons rebuild round 1 (senior weapon artist): form and surface pass after the art director's critique

Critique: CHOPPER 2/5, NINE 1.5/5 (extruded outlines, hard edges, non-binary metalness, procedural wear).
Order: NINE first (grip/frame, panels, guard, slide, base pad, hammer, textures), then the CHOPPER (handguards,
receiver, guard, grip, sight blocks, stock, bolt, magazine, booster, 3 x 4K sets + detail maps).
New code: assets/_weapons_kit.py (sections, splines, lofts), assets/_weapons_nine.py, assets/_weapons_chopper.py,
assets/_weapons_tex.py; weapons.py keeps the pipeline (rig, export, previews).
## Status
- started: reading the briefs, the critique and the review measurements.
- (resumed after the restart) NINE rebuilt and exported: SK_Nine 83.9k tris, set Nine 4K at 7,380 px/m (Weapon_NineMagazine
  2K 9,100 px/m), re-import proof ok. Grip 54.7 mm horizontal / 53 mm across the rake at mid height (was 72), 29.8 mm wide;
  forged hammer (one piece, 9 mm spur, hollows, pin); magazine line 12 mm back (direction kept), body seated level in a
  flat pad ending at Z -0.1345 (brief); bore ray now stops at the breech face (X 0.0045, was the hammer at -0.010).
- Surfaces: assets/_weapons_tex.py (Surf2: metallic 1.0 on all steel/gold, dirt/carbon switch it off with a narrow step;
  wear = convex x handling; brushed / machined direction in the height; checkering 1.3 mm with a 2 mm border; stipple).
- CHOPPER rebuilt (assets/_weapons_chopper.py), 137.8k tris; three 4K sets: Chopper (receiver, cover, rear sight, bolt:
  10,074 px/m), Chopper_Furniture (12,568), Chopper_Front (~8,400); hidden faces get UV weight 0.3-0.45.
- Proof script: `python art/blender/assets/_weapons_check.py` (director's measure() on the re-imported GLBs vs the brief and
  the first-pass measurement) -> art/out/glb/weapons_fixed_points.json.
- Next: 4K CHOPPER bake + export (running), fixed-point check, previews (MI_PREVIEWS=... build weapons --only chopper,nine
  --preview), commit.

---------------------------------------------------------------------------------------------------------------
# Rule, the main character from the user's reference photo (assets/rule.py), senior character artist

Task: the player character as a likeness of the man in the reference photo (art/out/ref/, git-ignored; the user owns
the likeness): reference sheet, SK_RuleArms rebuilt as bare arms with anatomical hands (gloved build kept as
SK_RuleArms_Gloved), full body SK_Rule for the crew screen and cards, previews rule_*.jpg.
Privacy: the photo, generated pictures, raw generated meshes and .blend files stay in art/out/ (gen/rule/); no name
in any prompt, file or request; tattoo lettering is read from art/out/ref/tattoos.json (not committed).
## Status
- [x] reference sheet: 7 pictures (nano_banana_pro, 2 credits each) in art/out/gen/rule/: head front, three-quarter,
      profile; body front/back; A-pose front/back. All plainly the same man (face shape, brow, eyes, nose, thin
      moustache, chin hair, skin tone); the profile is slightly leaner in the cheek. Generated tattoos are invented.
- [x] head 3D: meshy_v7 ultra kept (closest to the photo), hunyuan3d_v3 drifted (broad face, light eyes);
      body 3D: meshy_v7 a-pose ultra; both base colour atlases (2K) upscaled to 4K (bytedance, 2 credits each).
      Credits spent by this task: 125 (7 x 2 images, 2 x 44 meshy, 19 hunyuan, 2 x 2 upscale).
- [x] SK_RuleArms_Gloved exported (characters.build, skin slot M_RuleArms_GlovedSkin, set RuleArms_GlovedSkin)
- [x] SK_RuleArms bare: 131,594 tris (64k skin per arm + 10 nails), RuleArms_Skin 4K baked (hand 6.9k px/m,
      forearm 3.9k, upper arm 2.7k), tattoos from charts; bracelet silver on the right wrist (24k tris)
- [x] SK_Rule: 120,624 tris, head bust on the generated body at the collar, bound, exported (46 MB, 4K maps)
- [x] previews round 1 (10 renders, committed). Worst faults: arms: a swollen ring at the wrist (a wide smooth
      union of the arm and the hand's coincident wrist piece), palm colour on the back of the hand, speckled
      normals on island edges, orange skin; body: the bust's neck edge just above the collar at the front
- [x] round 2: worst faults found: a step from the wrist down to the back of the hand (the hand's own wrist
      piece) and palm colour on the back of the hand. Fixed: the hand has no wrist piece (bare_palm_sdf), the
      forearm flattens and widens into the heel (74 mm); back / palm by face normal; finger labels and knuckle
      darkening not applied behind the knuckles; bust neck edge carried 1.8 cm under the collar.
      Final: SK_RuleArms 131,594 tris (UV: hand 7.2k px/m, forearm 4.0k, upper arm 2.8k at 4K), bracelet 13,988,
      SK_Rule 120,621, SK_RuleArms_Gloved 108,398. Renders: 10 (round 1) + 5 (round 2) + 5 (wrist fix) + 3 x 3
      hands re-renders while fixing the back of the hand: over the 12 asked for.
- Known: the CHOPPER hold pose is the first version's (left hand beside the handguard, not round it);
  rule_arms_fp / rule_arms_hero predate the last texture fix of the back of the hand (rule_hands is current);
  the face is the generated head (painted eyes under glossy covers, no mouth interior, 2K maps upscaled to 4K);
  the full body's arms are the generated ones (invented tattoos), not SK_RuleArms; small streak on the throat
  where the bust's neck edge was carried down.
## Exact next step
None required. Improvements: better photos (see the task report), then a head from several views; a gun-grip
solve for the bare hands; re-render rule_arms_fp and rule_arms_hero.

---------------------------------------------------------------------------------------------------------------
# Goons (assets/goons.py, _goons_*.py, mi/cloth.py), senior character artist: SK_Goon_Hoodie / _Puffer / _Tracksuit

Task: the three Goons on SK_Mannequin (briefs characters.json goon_hoodie/_puffer/_tracksuit): draped garments,
weights from the mannequin, unique sets (Cloth 4K, Head 2K per outfit), GLBs, proof in Unreal (chars-goons-1..3),
previews goons_lineup/_hoodie_hero/_detail/_poses/_wire, CHARACTERS.md.

## Status
- [x] goons.py: shared man, kit, three outfits draped in the A-pose (drape and UV caches in art/out/goons);
      67,043 / 74,049 / 68,961 triangles; weights (transfer, smoothing, per-finger gloves, forearm-only cuffs, rigid
      hats, LAYERS sharing), unfold pass, GLBs in art/out/glb/SK_Goon_*.glb
- [x] six sets: GoonHoodie/Puffer/Tracksuit_Cloth (4096) and _Head (2048), BC/N/ORM, per-vertex AO, gaps filled
- [x] Unreal (scratch project /project/ue/chars): imported on SK_Mannequin, materials, shots chars-goons-1..3 after two
      fix rounds; editor stopped by its pid
- [x] previews goons_lineup, _hoodie_hero, _detail, _poses, _wire (11 renders); CHARACTERS.md, README row

## State at hand-off: task complete
Known weaknesses (CHARACTERS.md has the list): dark stepped patches in the deepest hood folds in Unreal close-ups
(textures, normal map, back faces, shadow bias, VSM and RT shadows ruled out); puffer quilting follows the chest too
closely; tracksuit sleeve stripes broken into patches; many small UV islands; long smooth mask face (mannequin head).

## Exact next step
In the editor, open SK_Goon_Hoodie's LOD 0 build settings, turn off Recompute Normals (and Remove Degenerates),
rebuild, and look at the hood at 1 m (`/tmp/goons_shots.sh` pattern, shot 3). If the patches stay, raise the hood's
budget (BUDGET['Hood'] 6500 -> 12000) and smooth the drape more before decimation (cached piece version bump), then
`build.py build goons --export` (no re-bake needed while the UV cache key holds; a geometry change before the unwrap
re-unwraps: then also --bake).

---------------------------------------------------------------------------------------------------------------
# Structures, continued after the machine restart (assets/structures.py), level-structure artist

## Status
- [x] Previews round 1 looked at: station and station_up were silhouettes (the stair foot faces east, the design
      sun at 260 stands behind it), the street shot missed the produce stand and the hoarding, chopshop not rendered.
- [x] Fixes: station shots light the dome with a mid-morning sun (80) and expose for the shade (+3.0 / +4.2 stops);
      street shot moves the news kiosk (shutter to the road) and the LotW hoarding beside the produce stand for that
      one picture; `MI_PROBE=<dir>` renders 192 x 108 exposure probes with logged luminance instead of previews.
- [x] Round 2: structures_station.jpg, structures_street.jpg, structures_chopshop.jpg rendered and looked at;
      structures_station_up.jpg re-render running (two attempts were OOM-killed: the dressed block took 5.2 GB while
      other agents' jobs filled the shared limit; previews now cap Cycles textures at 2K, which cuts that sharply).
- [x] TS_Roof_ScanBitumen fetched at 8K (4K over its 5.4 m tile was still 758 px/m; now 1,517); upgrade_sets.py
      lists it under SCANNED_8K; manifest densities refreshed.
- Renders this task: 8 (4 in round 1, 4 in round 2), plus 4 tiny probes.

## Still boxes (no module anywhere): rolling scaffolds (600, 626), hoist tower (571, 572), tyre cage (560), shanty
(568), lot walls (419, 420), lot signs (423, 424). The `seal` and `railing` colliders are invisible player blockers.

## Notes for the next agent
- `fetch.py` without `--res` puts the 2K files back: after any such run, re-run the 4K list and then the 8K bitumen.
- Known weaknesses: green globe lamps read as flat uniform spheres; the mezzanine office in the chop shop is dark;
  oil stains are soft uniform blobs; open-web joists read as plain beams from the floor; the kiosk padlock pokes
  16 mm outside collider 490.
- [x] structures_station_up.jpg rendered (2K texture cap, 966 s) and looked at: treads, nosings, lattice
      balustrades, canopy and bridge enclosure read; the doorway into the bridge at the head is black (no daytime light
      inside the bridge). Task complete; all five previews in art/previews.

---------------------------------------------------------------------------------------------------------------
# Weapons rebuild round 2 (senior weapon artist): critique NINE 2/5, CHOPPER 2.5/5
Order: NINE first (grip junction with the magazine line restored to the brief, beavertail + hammer, guard / dust
cover / rail, slide machining, panels, slide stop + safety, base pad, hammer channel; then the slide finish, frame
wear, panel checkering), then the CHOPPER (trigger clearance, rear trunnion / cover, magazine, handguards, grip,
guard, stock, controls, front end, finishes). Code: assets/_weapons_nine.py, _weapons_chopper.py, _weapons_tex.py,
_weapons_kit.py (my files); mi/ untouched.
## Status
- started (the first attempt of round 2 left no changes on disk).
- NINE rebuilt (assets/_weapons_nine.py): magazine line back on the brief (in place X -0.029..0.045), grip loft
  from the tang to the butt with the front strap rising into the guard (undercut R 7 at X 0.0605..0.0675, trigger
  face to strap 35 mm), swept 19 mm tang (13.5 mm behind the back strap, 4.5 mm tip), forged S hammer, 6.5 x 9 mm
  superellipse guard flaring into the dust cover and grip, lofted dust cover (2 deg taper, 1.5 mm chamfer, 21 mm
  rail, 45 deg cross slots), 0.3 mm shadow gap and 0.5 mm top flat, 9 serrations at 2.8 mm, port chamfer, proud
  extractor with claw, dovetailed sights, hammer channel (slide clears the static hammer over its whole travel:
  0 overlaps at 10/20/30/44 mm), lever controls, 1 mm crowned panels, gold pad. 78.7k tris.
- NINE surfaces: slide skin = one UV shell with U along +X (pinned rotation, 90 % of faces), brushed stainless
  #aeb1b6 (+-1.5 %), roughness 0.30-0.38 grain, polished edges 0.17; oxide frame blotches +-0.08; 20 LPI
  checkering (panels 0.45 mm, front strap band 0.4 mm), hammer thumb face, rear sight 40 LPI; gold pad wear.
- CHOPPER (assets/_weapons_chopper.py): trigger guard rear upright 4.5 mm back (19.5 deg pull clears), strip
  with rolled edges and rib, rear tab rivets; receiver sheet ends at X 0.0035 over a forged rear trunnion (domed,
  chamfered), rivet pair, 24 mm hinge block, 10 mm axle; new top cover (1 mm sheet, 3 crisp ribs, stamped lip,
  pressed rear end with the guide tab through a 7 x 8 mm hole), rail with 5.3 mm slots and two cross-bolts;
  magazine with flat sides and crisp 2.5 x 0.8 mm ribs, forged lug, catch lug, spine weld, turned floor plate;
  handguard 46->41 mm C section with finger swell and chamfered vents; oval grip; butt plate seated 2 mm under the
  handguard; stamped bowed selector with detent; crisp dimple; booster flats + grooved ring; charging slot widened.
- NINE exported (4K set Nine at 7,145 px/m with UV weights; SK_Nine 79.1k tris) and proven: `_weapons_check.py`
  Nine ALL FIXED POINTS KEPT (bones/sockets 1e-5 m, length -0.0329..0.201, height -0.1345..0.0185, width 31.0 mm,
  notch and post profiles, sight line, magazine in place X -0.0292..0.0453 (brief -0.029..0.045), trigger face to
  front strap 34.7 mm, slide back 10/20/30/44 mm: 0 overlaps, trigger 17 deg clear, re-import poses < 1.4e-8 m).
  Previews weapons_nine_hero / weapons_nine_fp rendered after the NINE's last change. CHOPPER 4K bake running.
- CHOPPER exported (SK_Chopper 138.8k tris; sets Chopper 9,137 px/m, Chopper_Furniture 12,755, Chopper_Front
  7,569; SM_Weapon_ChopperMagazine 30.9k tris) and proven: `_weapons_check.py` both guns ALL FIXED POINTS KEPT
  (CHOPPER: height -0.2294 (floor tab kept inside the plate), notch/post profiles, sight line, bore ray, Palm_R
  1.26 mm, Palm_L 1.21 mm on the new 10 mm recoil pad, trigger 14 / 19.5 deg: 0 contacts, 2.35 / 1.86 mm clear,
  charging-handle stem >= 0.52 mm from the slot over the whole 92 mm, re-import poses < 1.1e-8 m). Butt plate crown
  2 mm under the handguard.
- Final previews after the last change (6 renders): weapons_chopper_hero/_fp, weapons_nine_hero/_fp,
  weapons_parts, weapons_wire. Note: the preview build re-unwraps and flags Chopper_Front / ChopperMagazine "stale"
  (uv_hash rounding differs between sessions); the pictures show no mismatch and the exported GLBs were baked and
  written in the same run, so they match their sets.
## Not done in round 2 (next)
- NINE grip is 86 mm deep at the undercut: the brief's magazine line (fixed) sits ~20 mm behind a real pistol's
  relative to the fixed trigger, so the critique's front strap position leaves thick frame in front of the
  magazine; slimming it needs a decision on the brief.
- Anisotropy: tangents follow the slide's U (along X); no separate anisotropy texture is written (the set format
  has no slot for it). CHOPPER gas-block tower / sight-ear shapes only lightly touched; CHOPPER UV hash rounding.

---------------------------------------------------------------------------------------------------------------
# Weapons rebuild round 3 (senior weapon artist): critique NINE 2/5, CHOPPER 2.5/5
Order: NINE first (grip slimmed to a real service-pistol depth with the brief decision below, D-section guard
flush with the frame, slide section / nose / serrations / port hood, hammer, sights, screws, moulded pad; then
the slide finish and edge-driven frame wear), then the CHOPPER (rear trunnion and rear sight, handguards, 3D-field
laminate, stock, steel wear, guard and catch, front end, magazine, grip, stamp, bolt UV).
Code: assets/_weapons_nine.py, _weapons_chopper.py, _weapons_tex.py, _weapons_kit.py (my files); mi/ untouched.
## Status
- started (no earlier round-3 changes were on disk after the restart).
- NINE rebuilt (assets/_weapons_nine.py, 86.1k tris): grip slimmed from 86-90 mm to 56 mm fore-aft at mid grip
  (back strap 16 deg from a deep web cup under the tang, front strap 18 deg, R 7 undercut), egg section (21 mm frame,
  R 10.5 back, R 6 front, 0.4 mm crown + 1.2 mm palm swell at 40 %), width 29.3 mm at Palm_R; D-section guard 7 x 5 mm
  (hooked squared front, R 8 corner, R 3 flares); 1 mm chamfer under the slide, stepped web over the opening, dust
  cover R 1.5 edges and 45 deg slots (3 mm floor, 2 mm deep); panels as one surface with the checkered field recessed
  0.3 mm inside a 2.5 mm border (0.6 mm chamfer), 3.4 -> 2 mm; 7 mm domed slotted screws in flush dark bushings;
  slide section with R 3 shoulders, 22 deg slopes, 7 mm flat top, 0.4 mm break, 20 deg dehorn over the lower 60 %,
  R 1.5 top front, seven 1.5 x 1.2 mm serrations at 3 mm pitch running into the shoulder, port scallop, solid nose;
  hood a cylinder segment with a 5 mm flat and 2 mm witness hole; forged hammer 6 -> 4.5 mm, R 3 tip, 1.2 mm grooves,
  4 mm hole, strut, 3 mm pins (the polished pin that made the white speck is gone); rear sight block 9 mm on top,
  10 deg rear face, set screw; moulded 43 mm gold pad (R 1.5 / R 3, finger relief).
- BRIEF DECISION (critique): the magazine body stays on the brief's line (lips front X 0.045, axis 0.250/0.968);
  the blocky model's 76 mm pad (rear X -0.029) is now a real 43 mm pad (X -0.0135..0.030). In-place span
  X -0.0135..0.045. Palm_R, RecoilPivot and all bones/sockets unchanged.
- NINE surfaces (_weapons_tex.py): brushed bands 0.22-0.34 along X, hairline streaks, bead-blasted top flat 0.45,
  polished breaks 0.12, holster bands on edges only, finger-oil smears, no tinted serration patch; frame even with
  edge-driven wear and grime at pins/controls; 20 LPI on panels (read back from the panel grid), front and back
  straps; guard front serrations; 40 LPI on the sight and slide rear faces, firing-pin stop plate seam; new map
  T_Nine_A (anisotropy along the mesh tangent; set.json files.A).
- CHOPPER rebuilt (_weapons_chopper.py, 150.8k tris): rear trunnion R 2 everywhere, 1.5 mm dome, 0.3 mm inside the
  sheet (step), turned buffer boss, sling lug; swaged 4/4.5 mm rivets; rear sight base 14 mm, 8 deg draft, 0.5 mm
  breaks, 2 mm cross pin, leaf with 0.6 mm chamfer and 0.5 mm anti-glare lines; stock arms as stamped channels
  (10.5 x 2.5 mm, 0.8 mm rib, 2 mm rolled edges) along the receiver from the hinge X 0.022 to the cross pin X 0.236,
  turned R 6 bosses, 5 mm rivets, spring latch; shoulder piece 2.5 mm stamping, 3 mm flange, R 120, Palm_L on it;
  body 45.8 mm wide (was 52.8); lower handguard 40 mm with 1.5 mm bow, R 8 bottom, 3 mm finger flange, 10 deg front
  taper, 1.3 mm round-overs, steel liner; upper half-round tapering 1.5 mm, shaped nose, stepped heat-shield lip;
  sheet retaining band with lever; gas block R 13 collar + R 4 blend, 45 deg front, eased underside, trapezoid sight
  base R 2 with R 3 foot, 2.5 mm ear holes, threaded 5 mm drum, round post; guard strip 10.5 x 1.5 mm with turned
  lips, R 12 front, 15 deg rear leg; spoon catch with two ribs and turned edge; egg grip 36 x 31 mm with palm swell,
  R 6 heel, 2 mm grip plate, 16 mm slotted cap; magazine swells 6 mm / 0.9 mm, spine strip, front weld bead.
- CHOPPER surfaces: laminate from a 3D ply field (ply normal = Y, 1.8 mm, #4a2515/#6b3a22 +-8 %, per-ply grain,
  pores, varnish 0.28 -> 0.5 on flanges and grip front, dents, crushed corners, bare edges, no specks); blued sheet
  with +-3 % orange peel, 0.35-0.55, curvature x handling edge wear (stronger at well lip, handle path, ribs, ears,
  booster), packed grime at rivet rings and the cover seam, oil at the port and gas block, milled trunnions, ground
  carrier (UV weight back to 1); stamps flipped to read from the left, the "MI-87" code removed, one proof star.
- Exports: final bake-and-export of both guns in one run (running); then _weapons_check.py, then the six previews.

---------------------------------------------------------------------------------------------------------------
# Rule, review round 1 fixes (assets/rule.py, _rule_tex.py, _rule_head.py, _rule_bodytex.py, _rule_body.py), senior character artist

Review (art/blender/review/rule_review.py, renders in art/out/review/rule/): likeness 2.5, hands 2.5, body 2.5.
## Done
- Skin tone: one shared albedo target (_rule_tex.SKIN_TARGET, linear median 0.165/0.079/0.038, the photo's hue)
  applied to T_RuleArms_Skin_BC (forearm median), the head map (face median) and the body map (forearm median);
  the body's neck is matched to the head's neck colour just above the join. Checked side by side under one light.
- First-person grip: _characters_pose.ik_arm mixed armature-local rest heads with world targets, so both palms
  were off by reach_forward's slide (9-12 cm); now in world space. Support shoulder protracts (clavicle swing,
  `protract`), rig slide limit 12 cm; the left palm cups the CHOPPER's handguard (palm error 0 / the 1.2 cm flesh
  offset), fingers curl 0.8 round the 46 mm handguard, thumb along its left side.
- Eyes: real eyeballs (iris recessed under a transparent cornea, near-black brown iris), sockets cut by pushing
  the skin inside a narrower, hooded aperture (7.5 mm, was 9) behind the globes, lid margins resting on them, a
  hooded upper-lid fold, tear lines on both margins (M_Rule_EyeWet), caruncles; the old painted eyes repainted as
  lids with a lash line, a wet lower margin and a crease shadow. Eye texture is procedural (derived/T_Rule_Eye_BC).
- Neck: one tilted cut plane under the jaw; the bust bisected above it, the body keeps its own neck below it,
  reshaped radially to the bust's ring; the bust's rim stretched down where it ended above the plane and tucked
  2 mm inside; torn collar flaps behind the ears pulled onto the neck; the shirt's red bleed cloned out.
- Face surface: frequency separation with a 3D (voxel) low-pass (a UV blur mixed atlas islands), specks and red
  speckles removed, pores / micro-wrinkles / lip lines in a detail normal over the generated one, ORM with an
  oily T-zone, drier cheeks, wetter lips; a lower, thicker moustache, stubble shadow and a small chin tuft.
- Proportions (_rule_head.warp_points): lower third 5 % shorter, zygomatic arch +5 %, brow ridge 2 mm forward and
  1.2 mm lower, nasolabial grooves, mouth corners down; ears 1.35x about their root and raised 6 mm.
- Nails: pink-brown bed matched to the skin, faint lunula, free edge under 1 mm, darker cuticle / nail folds,
  roughness 0.35. Hands: darker knuckles and palm creases, pores, fine hair, warmer fingertips; no palm patch on
  the back of the wrist (back half of the hand forced to the back region, majority filter); forearm veins at 40 %.
- Bracelet: a curb chain of 5.2 mm wire, a link every 7.2 mm, twisted flat, 1.5 mm clear of the wrist; exported with its silver values
  (metallic 1, roughness 0.16 / 0.28: rule.export_plain); the same bracelet fitted on SK_Rule's right forearm at the
  body's own section, rigid on lowerarm_twist_01_r; the generated wrist bands painted out.
- Bandana: a generated seamless bandana swatch (2 credits, art/out/gen/rule/bandana_tile.png) printed by
  triplanar projection over the bandana texels, deeper red, cloth weave and compression folds in the normal map,
  roughness 0.8; its third corner hanging over the nape (bandana_tail, UVs transferred from the surface above).
- Shirt: upper-arm weight on shirt vertices moved to the clavicle (above the armpit) / spine_03 (below), 60 % kept
  at the armhole rim fading out over 8 cm (after the weight smoothing); deeper red; "Murder Inc." lettering over the cleaned generated print.
- Export checks (rule.export_checks): mi.export.validate, skeleton round trip vs the mannequin, re-import
  (triangles, joints, materials, every vertex weighted) -> <glb>.check.json.
- Credits: 2 (one bandana swatch, nano_banana_pro). Balance 2818.76 before.
