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

## Close-up pass 3 (review round 3: every vehicle graded 2-2.5, the motorbike 3.5), vehicle artist
Method (lead's decision): stop repairing generated detail, replace it. The generated body stays only as the large
painted shell; everything a close camera reads is modelled by the new library module `mi/carparts.py` (shared,
per-vehicle parameters) and fitted to the body by `vehicles.py`.
- Wheels (all vehicles, `carparts.wheel`): tyre = tread band on pitch rings (circumferential grooves, steep-walled
  shoulder lugs) + sidewalls (bulge, rim-protector rib, fine ring) + raised invented lettering ("QUEENSWAY RADIAL",
  size code; trucks "QUEENSWAY HAUL"); faces: Sedan dished hubcap with ten raised spokes, slot windows, badge,
  valve; Taxi / Van / Pickup / Vulture pressed steel with vent slots, five nuts, centre cap (taxi: chrome trim
  ring); SUV five drafted concave spokes, recessed hub carrying the nuts; trucks deep steel disc, hand holes, ten
  nuts, hub nose (inner duals simplified). Disc, hat, dust shield and caliper behind car wheels, finned drums on trucks.
- Lamps and grilles: rectangles from the lamp classes (or `lamps` boxes in SPEC); the body surface there fitted from
  ray casts (`fit_surface`: robust polynomial, clamped to the hits, grazing hits and hits far from the end
  rejected); the rectangle cut cleanly (`cut_rect`: bisect on four planes, delete inside) and filled by
  `surface_lamp` (black bucket, chrome reflector bowls per cell, bulbs and glare caps, 4 mm lens sections clear /
  amber / red, dividers, bezel over the cut) or `surface_grille` (egg-crate blades or bright bars, recessed backing,
  surround). Lens sets carry moulded flutes / prisms as normal maps and an E map. Sedan, Taxi, SUV, Pickup, Van,
  Vulture: heads, tails (SUV upright clusters), grille; BoxTruck, IPX: heads and bar grilles. The SUV's
  suv_fascia (parts laid over the generated fascia) is retired: the fascia is cut and modelled like the others.
- Glass and cabin: generated glass put on fitted surfaces (`clean_glass`: borders smoothed along themselves, side
  glass y = f(x, z), screens x = f(y, z), only crumple-size moves) with a rubber seal swept round every pane; glass
  set lighter (#7d8a86, opacity 0.45 in its note); preview glass lets shadow rays through (Unreal's translucent glass
  casts none). Cars and vans get `carparts.interior`: lofted dash with binnacle hump and visor, three dials (ticks,
  needles, chrome rings), vents with slats, centre stack, glovebox line; steering wheel, column, stalks; bucket
  seats with bolsters, piping and headrests on posts, rear bench, console and lever; door cards (armrest, pull cup,
  inner handle, speaker, crank); carpet with tunnel; parcel shelf; Taxi partition (plexiglass upper half, tray) and
  fare meter. The shell's inside within the cabin reads as headliner cloth. Trucks keep the simple cabin (glass
  above standing eye height; budget); its seats now stop under the cab roof (SPEC roof).
- Body: flanks put on a robust fitted surface (`flatten_flank`: paint vertices only, arches avoided, handle boxes
  forced); real shut lines cut as 6.5 mm grooves with a dark floor (`cut_groove`) at the door lines (Sedan front
  door 1.16 / rear door 0.90 as briefed; SUV, Pickup, Van from cowl, B pillar and arches); SUV tailgate and the box
  truck's lower front flattened the same way; generated handles flattened, modelled pull handles in pockets;
  generated mirrors dropped, modelled mirrors (sail, arm, housing in body colour or black, mirror glass) or West
  Coast truck mirrors (tube stalks, chrome head, convex spot mirror), inside the brief's width.
- Paint: one flat clear-coat tint mask per body (no texture lines, no baked light, faint mottle), grime and
  roughness rising from the sills, a fine orange-peel normal instead of the generated normals.
- Plates 305 x 152 mm in a chrome frame with four screws over a dark recess; the generated holder standing in
  front of the plate is pushed behind it (the black diagonal line across the sedan's plate was generated trim
  standing proud); the Van has its own number RJM·6072. Cowl panel 5 mm below the bonnet's rear edge, 2 cm further
  inside the A pillars; wiper arms bend down onto the glass.
- Others: Burned / Stripped car keep the sedan's 2.80 wheelbase (only the overhangs shrink to 4.38); burned rims are
  the modelled steel wheel in rust; stripped hubs are modelled brakes with studs; the primer slot writes
  paint_default + matte + roughness_override 0.80. Vulture: CargoDark lifted to about 0.13, leaf inner skins in
  primer grey (TS_Paint_PrimerGrey), stencil redrawn as a hunched vulture (drooped ragged wings, ruff, long bare
  neck, hooked beak), scrawls are letterless loops. IPX: flank art laid out round the gun port (lozenge left,
  wordmark right). BoxTruck: clean chrome bumper with tow slot and bolts.
- Triangles (all validated and exported, noses +X, origins kept): Sedan 177.9k, Taxi 177.4k, SUV 167.0k, Pickup
  152.0k, Van 168.7k, Van_Vulture 164.9k, BoxTruck 176.8k, IPXTruck 171.7k (raised from 106-145k, under the 180k
  cap), BurnedCar 82.3k, StrippedCar 70.2k, Motorbike 90.2k.
- Credits: none spent (no regeneration; replacing the detail needed none).
- Builds: memory is shared and a full build was OOM-killed once: build in two groups (cars: Sedan, Taxi, SUV, Pickup,
  Van, BurnedCar, StrippedCar; trucks: Van_Vulture, BoxTruck, IPXTruck, Motorbike) with --force --export, copy each
  saved blend to art/out/blend/vehicles_cars.blend / vehicles_trucks.blend; previews from the cars blend with the
  trucks appended (open vehicles_cars.blend, bpy.data.libraries.load the trucks' SM_Vehicle_* objects, then
  vehicles.on_preview), one preview per process. New previews: vehicles_wheel, vehicles_lamp, vehicles_interior,
  vehicles_taxi.
- Verdict from the final previews (all eleven rendered after the last asset change, 36-64 samples): the Sedan and
  Taxi pass at arm's length for wheels (hubcap / trim-ring steel wheel, lettered tyres), lamps (fluted lens, chrome
  bowls, amber section, egg-crate grille), framed plate, mirrors and the cabin through the glass (dash, dials,
  wheel, bolstered seats read by day); the flanks are smooth with clean door grooves. Still failing at arm's length:
  the A pillar / windscreen edge (generated trim shards and a brownish strip where the screen meets the pillar),
  the front wing above the arch (outside the flattened region: ripples show in grazing light), the bumper's top edge
  by the wheel (torn white fragments), the bumper indicators (generated). SUV: clean nose and alloys, but the tail
  lamp cut opens a gap round the rear quarter (wire preview) and the quarter glass is still generated. Van and
  Vulture: the windscreen keeps crumpled glass (the fit only moves crumple-size deviations), rear barn-door panes,
  seam and handles not modelled. BoxTruck / IPX: lamps, bar grilles, bumper and West Coast mirrors are modelled,
  the rest of the cab front is generated (fog-lamp holes, crumpled lower panel edges), IPX vault floor still foil and
  hazard fragments on the sill, band not carried over the open leaf. Wrecks: wheelbase and rims / brakes fixed, the
  burned material (rust islands on charcoal), ragged cut edges, engine bay and dash skeleton not done. Motorbike: not
  touched beyond the flat paint (four mirrors remain: the duplicate pair could not be separated reliably on the
  leaned body by position alone).

## Exact next step (close-up pass 3)
Model the A-pillar / windscreen frame (a swept pillar trim over the screen border) and extend the flank flatten over
the wings above the arches; fix the SUV tail cut (limit cut_rect to faces facing -X); clean the van windscreens with
a plane fit; then the Van barn doors, the IPX floor / sill / leaf band, the motorbike mirrors (cut by connected
component near the bar ends) and the burned-car material.

## Close-up pass 4 (review round 4: Sedan / Taxi / SUV / Van / Vulture / trucks / wrecks 2, Pickup 1.5, Motorbike 3.5)
Same method: the generated body is only the painted shell; what a close camera reads is replaced. New library
module `mi/carfix.py` (vehicles only), small additions in `mi/carparts.py`; `vehicles.py` wires them.
- Glass (every vehicle): `carfix.rebuild_panes` throws the generated panes away and rebuilds each one: islands
  under 0.035 m2 dropped (shards, the Van's glass ghost mirror; the generated mirror heads in the glass slot are
  also dropped by `plan_mirrors`), the border loop smoothed along itself and resampled, a smooth low-order surface
  fitted to the pane (side glass y = f(x, z) curved across z; screens x = f(y, z) with a y^4 wrap term; sloped
  screens z = f(x, y)), the inside re-triangulated on it (constrained Delaunay, 4.5 cm grid). Seals 8 mm, moved
  5 mm outward so they cover the shell's cut edge. TS_Glass_CarTint is the brief's near-black #0a0d10 (linear
  0.004), roughness 0.03, opacity 0.55 in its note (rev 4); the preview material is a glossy near-black surface at
  45 % transparency, as Unreal draws it (no refracting clear pane).
- Torn white fragments: they were paint faces folded back into the body (the middle layer of crumpled seams); the
  solidify put their inner layer (light headliner cloth) 1 cm OUTSIDE the paint. `carfix.orient_outward(delete=True)`
  removes paint / trim faces whose front looks at the back of another face while their back sees the outside
  (Sedan 34, SUV 141, Pickup 156, Vulture 121, BoxTruck 44, IPX 232 faces). Flipping them instead broke the
  exporter's winding check (they are wound consistently with their sheet). Headliner cloth only above belt + 0.12.
  `carfix.drop_islands` then removes islands under 40 cm2 and slivers (aspect > 8) within 8 cm of every fitted
  handle, mirror and lamp (Sedan 233, SUV 237, Van 542 faces).
- Grey belt slab: it was the light grey door card seen through the gap between the generated door top and the
  glass (found by casting the preview camera's rays). A black U-section weatherstrip (`carfix.belt_strips`, 75 mm
  wide, cap over the glass base, legs 6 cm down behind the skin) runs along the bottom of every side pane; the
  generated belt trim is paint and its upward sill faces dark plastic. Sedan handles are chrome (brief).
- Headrests: `carfix.settle` lowers each headrest with its posts until it clears the paint and glass by 6 cm seen
  from the cabin's centre line (Sedan / Taxi rear 21 cm, front 5 cm; SUV up to 10 cm). No headrest stands through
  the rear screen.
- Lamps / grilles: tail-lamp cuts only remove faces that face the lamp's way (`cut_rect(facing=)`), so the rear
  quarters keep their skin (the SUV's black cavity is gone). Grilles rebuilt (`surface_grille`): bars 8 mm square
  with a 2 mm bevel (egg-crate) or 12 mm flat bars, a black backing plate 4 cm behind, a 22 x 16 mm surround frame
  whose top meets the bonnet line (`grille_top`). Plates: the generated holder stays paint (it read as a large grey
  crumpled patch); a black recess card sits behind the plate.
- Paint: orange-peel normal at a sixth of its slope (0.30 -> 0.05: it read as hammered metal in grazing light);
  paint corner normals diffused 30 iterations instead of 10. Body sets regenerated (`--force`).
- Pickup: the generated cab is a regular cab whose back wall stood at x +0.01 while the brief's bed starts at
  -0.56 (the seats ended up in the bed). A second x remap in `gen_body` (`xwarp`: -0.98 -> -0.98, +0.012 -> -0.50,
  +0.06 -> +0.06) compresses the bed ahead of the rear arch and stretches the 5 cm behind the door into the cab's
  rear corner: door, window, cowl and front end are untouched, the cab back wall is now at about -0.50, the seats
  are inside the cab, no glass behind it. Not regenerated: the concept itself is a regular cab, and the brief's
  3.22 wheelbase with a 2.01 bed is an extended-cab length.
- Van: rear barn doors modelled on the generated tail (`van_rear`): the large generated pane is paint, the tail
  flattened, a 6 mm centre seam cut as a groove, two 0.50 x 0.36 panes at 1.62 cut into the shell in rubber seals,
  two chrome pull handles with lock barrels by the seam.
- Van_Vulture: stencil redrawn (side-on perched vulture: hunched shoulders, folded wing set off by cut lines,
  ragged primaries past the tail, spiky ruff, bare S-neck, bald head, big hooked beak, legs and talons on a wire
  running past, overspray haze). Leaves inside: two lock rods with four guides and end keepers each, pressed ribs,
  the pane's seal on both faces, 0.30 strap hinges with three bolts and pin caps, a longer check strap.
- IPX: the gun ports measured on the mesh (centres x -2.16 and -0.37, z 2.04-2.37, both flanks); one panel per
  flank (the art reads from the tail on the right, from the cab on the left) laid out so nothing lies under a port
  or its dark mounting block: right = lozenge | port | IPX.EXCHANGE | port | gold bar; left = gold bar | port |
  wordmark | port | lozenge (checked on rendered flanks). Vault floor is a modelled tread plate
  (MI_Plate_ScanDiamond) on a galvanised sill angle; hazard fragments above z 0.85 at the tail are trim. Door
  leaves: band and lozenge now in front of the armour panel (they were hidden inside it), armour plate in a raised
  frame with 8 bolt heads, port in a frame, lock bar with three guides (2076 tris each, 0.09 deep).
- BoxTruck: amber lamp texels round the headlamps are cab paint (no more yellow patches); the fog-lamp pockets are
  found on a ray-cast grid against a robust fit of the lower panel and filled with modelled fog lamps; HOLLIS has a
  25 mm dark #2a2010 outline and drop shadow.
- Taxi: door lettering moved 4 cm clear of the front handle; the roof-light number on its own full-width region
  (2048 px over the 0.40 face), 60 mm cap height, black on white with a yellow rim.
- Motorbike: the rear pair of mirrors (heads at x 0.12-0.27) and their stems above the bar deleted; the front pair
  on the clamps stays.
- Wrecks: burned shell is rust all over (`M_Vehicle_BurnedCar_Rust`: the rust scan x tint (1.0, 0.8, 0.6), its
  blue patches graded out; tint in the manifest slot), char only above a wavy belt line and inside, and a soot
  overlay (`M_Vehicle_BurnedCar_Soot`, masked alpha rising from the sills to the roof, broken by noise) instead of
  rust islands on charcoal; mirror blobs cut from both wreck shells; both wrecks sit on z = 0 (they sank 8 mm).
- Triangles (all validated, exported, manifest entries kept; noses +X, origins unchanged): Sedan 178.1k,
  Taxi 177.6k, SUV 171.0k, Pickup 152.6k, Van 167.8k, Van_Vulture 167.0k, BoxTruck 178.8k, IPXTruck 173.4k,
  IPXTruck_Door / _Door_Left 2.1k (0.09 deep), BurnedCar 95.9k, StrippedCar 70.4k, Motorbike 89.1k.
- Credits: none spent (no body regenerated; balance not touched).
- Builds: as pass 3, two groups, one Blender process at a time; car group about 4.5 min with --force.
- Previews (11, 1280 x 720, 40 samples, one per process, all after the last change): vehicles_sedan_hero, _close,
  _wheel, _lamp, _interior, _taxi, _lineup_1, _lineup_2, _ipx_truck, _wrecks (framing widened), _wire.
- Verdict from the final previews, honestly: Sedan / Taxi now read clean at 2-3 m: near-black glass on clean
  panes, no headrests through the screen, no white fragments on the flanks, moulded grille, black belt
  weatherstrip, smooth wing reflections, dark plate surround. Still failing at arm's length: the generated sail
  under the door mirror is a crumpled dark lump (my extra drop box did not catch it), torn shards on the bumper top
  by the front arch and under the tail lamps, a crack fragment on the bonnet by the grille corner, a sawtooth at
  the cowl's ends under the A pillars, the light headliner showing through the glass along the roof rail, and the
  cabin is dim through the near-black tint (as briefed). SUV: the rear-quarter cavity is gone; the rear bumper and
  the quarter's corner stay crumpled. Pickup: cab, seats and bed now match the brief; flanks still generated (a
  light strip at the rear arch). Van: barn doors read; the lower rear corners are crumpled. Vulture: the stencil
  reads as a vulture; cartons' tape UVs and plain arch boxes not done. BoxTruck: fog lamps and HOLLIS outline
  done, the cab outside the fitted parts is still the crumpled generated skin, wheel hand holes are still painted,
  battery box plain. IPX: art clear of the ports, tread floor, detailed leaves; mirror stalks, the bar over the
  headlamp lens and the cab's slot window not done. Motorbike: two mirrors; disc and headlamp lens not modelled.
  Burned car: rust + soot blend reads as burned; rims still flat discs, engine bay a box. Stripped car: untouched.

## Exact next step (close-up pass 4)
Delete the mirror sail by connected component inside a 15 cm box round each mirror mount (all faces, then a
modelled sail plate), trim the bumper tops and the cowl ends along fitted curves, then the truck cabs: regenerate
the box truck cab from a flat-lit white conventional-cab concept (about 21 credits) or model the cab clip.

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

## Rebuild r2 (art review of r1: grades 1.5 / 1.5 / 2), same owner
- Cause of the dark stepped folds found by the review and fixed: Interchange turns LOD 0 Recompute Normals on.
  `mi_chars.keep_exported_normals` (SkeletalMeshEditorSubsystem) sets it off (MikkTSpace tangents kept, degenerates
  removed) in `setup_goons`; the hood at 1 m is smooth now (chars-goons-3). `unfold` no longer splits normals on
  folded faces (that split would now show), only real hem creases.
- Unreal materials `goon_material`: Cloth shading model, Cloth = saturate((roughness - 0.55) x 3.3) x 0.8, fuzz =
  BC x 1.5 + 0.03, specular 0.35, two-sided, tiling fibre normal `T_GoonFabric_Detail_N` (25 mm repeat, tiling per
  set from `art/out/goons/goons_ue.json`, scaled by the cloth amount). The Blender preview material matches (sheen
  from the same formula, specular IOR level 0.35). Socket `Weapon_R` on hand_r: SkeletalMeshSocket names are
  read-only from Python in 5.9 (reported, not made; CHARACTERS.md gives the attach offset).
- Head: `FaceShape` face proxy under every head piece; charcoal three-hole balaclava (eye openings 37 x 18 mm,
  mouth 43 x 15 mm, clean ellipse cuts with rolled hems), face skin and eyeballs behind the openings, sweat / breath
  / grime in the texture. Beanie cuff and cap sweatband as closed band tubes; cap brim under the crown edge, 17 deg
  down over the nape; wraparound sunglasses on the nose with a moulded frame; bandana fitted, dark warm grey.
- Cloth: hood / hoodie / jackets / trousers refined (one subdivision + Taubin) and decimated to higher budgets (hood
  12k, hoodie and track jacket 24k, puffer 30k, trousers 15k); degenerates dissolved per piece; rib waistbands and
  cuffs are closed double-walled tubes (no ragged spikes). Puffer: 8.7 cm baffles, torso inflated (no muscle suit),
  loft drives nylon roughness 0.54 crown / 0.78 valley. Tracksuit: navy with white stripe tape laid on the cloth by
  ray casts (constant 36 mm over folds). Hoodie charcoal-grey heather. Gloves 0.62-0.68 rough with knuckle pads,
  finger seams and creases (texture). Denim streaks halved. Sneakers albedo ~0.75 with grime. Sling: two tri-glide
  buckles. Socks tucked 7 mm under the shoe collar after the bake (they pierced the upper as a dark swoosh).
- Totals: SK_Goon_Hoodie 108,176 / _Puffer 112,481 / _Tracksuit 111,664 triangles (cap 120k). Bake: three
  processes, one outfit each (a single three-outfit bake was OOM-killed), about 10 min per outfit.
- Previews re-rendered and looked at: goons_lineup, _hoodie_hero, _poses after the last change; goons_detail and
  _wire one change earlier (before the sock tuck, which neither shows). Unreal: chars-goons-1..3 re-shot after the
  last change (`tools/box/chars/goons-shots.sh`; editor in /project/ue/chars stopped by its pid at the end).
- Credits: none spent (no generation: the face proxy, sunglasses, buckles and bands were reachable procedurally).
- Not done (next): sneaker panels / sole sidewall / visible laces as geometry; jeans waistband, fly, pockets and
  knee bagging as geometry; a high-res fold sculpt baked to the normal map; hood binding with stitching; the
  collar lining for the puffer's death-pose gape; fewer, larger UV islands (puffer cloth atlas only 33 % covered);
  the puffer's sleeve baffles still read as round balloons at 3 m; eyes show a lot of white in close-ups.

## Rebuild r3 (art review of r2: grades 2 / 1.5 / 2; the lead's mask direction first), same owner
- MASKS (lead, non-negotiable): two-hole balaclavas, closed knit over the mouth (no mouth hole; FaceShape has no
  lips any more, one soft muzzle form); eye openings cut 32 x 16 mm with a 3 mm rolled hem (about 26 x 10 mm clear),
  1.5 mm below the eye centre so the knit covers the top of the iris, a 5 mm knit tunnel behind the hem
  (`_goons_trim.cut_ellipse_hole(tunnel=)`), deeper brow; the eyeball fills the opening, so no skin ring shows;
  sclera 0.33, larger dark iris, lids darker. Heather knit at linear ~0.06 per Goon (hoodie dark olive, puffer
  charcoal, tracksuit dark navy), 2.5 mm rib in the height only, no breath ring. Puffer: slim wraps (29 mm deep, two
  lenses, 3.4 mm frame) + bandana. Tracksuit: six-panel cap worn forward (`_goons_head.cap_forward`, seams and
  eyelets in the normal map, stiff curved 7 cm brim over the eyes). Checked at 1, 3 and 8 m in Unreal
  (docs/unreal/shots/review/goons-r3-faces_1m / _faces_3m / _three_8m) and in Blender (scratch head renders).
  Why it cannot read as a caricature: there is no mouth opening and no lip form anywhere; no skin is visible round
  the eyes (the eyeball fills a 10 mm slot that sits in the knit's own shadow); the eye whites are albedo 0.33,
  mostly covered by a dark iris and the upper hem; the knit is a coloured heather at 0.06, not black, so there is
  no black-on-tan contrast; and two of the three faces are further covered (wraps and bandana; a cap brim).
- Dark folds, cause and fix: (1) the stage SkyLight's lower hemisphere was black: ground colour 0.28 / 0.26 / 0.23
  in `mi_chars._floor_and_light`; the game's rig had the same default: fixed in `build_block.py` (the level's
  SkyLight); (2) Lumen did nothing in the captures because the chars scratch project had no renderer settings
  (no mesh distance fields, no hardware ray tracing, skin cache off): its Config/DefaultEngine.ini now carries the
  game's (Lumen GI + reflections, distance fields, r.RayTracing, r.SkinCache.CompileShaders=1, Lumen HWRT, VSM);
  (3) geometry: hood and hoodie simulated at their final density (6.8 / 7.5 mm, `sim_piece`, no subdivide + Taubin
  after the drape). With Lumen working the stage exposure was one stop hot (floor clipped): bias 10 -> 9, and the
  Goon material's fuzz colour BC x 1.5 + 0.03 -> BC x 0.9 + 0.01, specular 0.30. No near-black fold patches in
  chars-goons-3 (hood at 1 m).
- Puffer: `boxy_puffer` (one rounded-rectangle section hem to chest, +5/6/5 cm off the body, straight sleeve tubes;
  sleeve vs torso = nearest axis AND outside the box's side wall: the nearest-axis test put sleeve rings across the
  chest = the six-pack), straight baffles with flatter crowns, 12 cm sleeve baffles, matte ripstop 0.62-0.80, yoke
  only above the torso's top stitch line, oxblood linear 0.12/0.02/0.025 everywhere.
- Also: UV overlap check + re-pack (`uv_overlap`, 0.000 % on all six sets); hoodie side seams, drop-shoulder seams,
  hood centre seam, twin-needle hem topstitch in the texture; fleece bending 3.5; pocket lifted; gloves thinner
  (0.8 mm) and finer (5.6k tris each), leather 0.52-0.6; sneakers albedo ~0.4-0.47; cuffs 6 cm, darker oxblood.
- Totals: 117,508 / 115,733 / 115,009 triangles (cap 120k). Bakes: three processes (about 10 min each), then the
  Head sets again alone (`MI_GOONS_SETS=head`, ~3 min each) for the darker masks.
- Credits: none spent (everything was reachable procedurally).
- Not done (next): corrective shapes / more loops at elbow and armpit (the death-pose balloon); sling skinned
  through the hood; jeans waistband, fly, pockets and ankle stacking as geometry; sneaker toe cap, sidewall and
  lace rows as geometry; glove seams as geometry; puffer collar lining and zip garage; a baked high-res fold
  normal; the tracksuit's raglan seams, rib collar and ankle zips; puffer shoulders still keep some deltoid shape
  above the box; fewer, larger UV islands.

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
## State at hand-off: review round 1 fixes done, re-exported and checked
- Exports: SK_RuleArms (131,594 tris), SM_Character_RuleBracelet (21,504), SK_Rule (197,743 incl. eyes, nape
  flap and its own bracelet; 37.9 MB, 4K head BC/N/ORM + body BC embedded). export_checks: skeleton round trip
  exact, re-import triangles equal, 89 joints, every vertex weighted; mi.export.validate: SK_Rule 3 zero-area faces
  and 4 inconsistently wound edges in the generated body, SK_RuleArms 1 (logged in <glb>.check.json).
- Final previews (10 renders after the last change): rule_arms_fp, rule_hands (3), rule_arms_hero, rule_body_hero,
  rule_face, rule_turntable, rule_wire (2). Check renders through the reviewer's loaders went to the scratchpad.
- Known: a lighter band and a faint crease ring just under the jaw (head/body texture and the tuck at the neck
  join); a few beige blotches of the generated print left on the bandana's right side; the aimed idle opens a gap
  at the shirt's armhole (the jog flare is gone); the generated body's thin band on the LEFT wrist is still there;
  fingers still press together in Epic's pistol pose (no corrective shapes); the face's large forms are still the
  generated head's (texture detail is 2K upscaled); the reviewer's body shots add the arms' socket bracelet on top
  of SK_Rule's own one now.
- Higgsfield: 2 credits this round (bandana swatch); the account balance also moves with other agents' jobs.
## Exact next step
Multi-view photos of the man (see the task report) for a head rebuilt from several views; neck-join texture
blend across the two atlases; armhole rim weights per pose (aimed idle); corrective shapes for curled fingers.
- Exported and proven (final bake and export in one run; laminate painted in 1.5 M-texel chunks after two OOM kills
  at 4K): SK_Chopper 150.4k tris (sets Chopper 8,642 px/m, Chopper_Furniture 13,117, Chopper_Front 7,527),
  SM_Weapon_ChopperMagazine 36.4k; SK_Nine 86.0k (Nine 7,754 px/m + T_Nine_A), SM_Weapon_NineMagazine 19.5k.
  `python art/blender/assets/_weapons_check.py`: both guns ALL FIXED POINTS KEPT (bones/sockets 1e-5 m, length,
  height, CHOPPER width -0.0229..0.042, notch/post profiles, sight line, bore ray, Palm_R/L, NINE grip 56.5 / 56.1 mm,
  back strap 16.0 deg, front strap 18.0 deg, magazine X -0.0135..0.0453, slide back 10-44 mm 0 contacts (the
  inverted right rail-groove box was caught here), triggers clear, re-import poses < 1.4e-8 m).
- Final previews after the last change (6 renders): weapons_chopper_hero/_fp, weapons_nine_hero/_fp, weapons_parts,
  weapons_wire.
## Not done in round 3 (next)
- The NINE's trigger sits 90+ mm from the web of the hand: the fixed trigger pivot, the hammer and the tang tip
  leave a long reach, so the guard opening runs back to X 0.050 (the opening's rear edge sweeps from the magazine
  button down into the strap). A shorter reach needs the trigger pivot moved (a fixed point).
- CHOPPER rear trunnion dome is built from scaled rings (soft creases from the corners show at grazing light).
- Magazine sets are flagged "stale" by the preview session (uv_hash rounding); the exported GLBs and their sets
  come from the same run.

---------------------------------------------------------------------------------------------------------------
# Rule, review round 3 rebuild (assets/rule.py, _rule_tex.py, _rule_gate.py, _characters_pose.py, _rule_head.py, _rule_body.py, _rule_bodytex.py), character artist

Review (art/blender/review/rule_review_r3.py, sheets/rule_r3): arms_fp 1.5, hands 2, tattoos 1.5, face 2, body 3.
## Done
- Weights (the worst fault): every bone may only weight its own stretch of the arm, measured along the
  shoulder-elbow-wrist chain (rule.SEGMENT, chain_height, segment_mask before and after the smoothing): 9,004 cross
  segment weights removed per arm, 0 hand / finger weights above 6 cm over the wrist (was 1,867 vertices per arm on the
  triceps); one 5.4 cm wrist ramp between hand and lowerarm_twist_01 (wrist_ramp).
- Posed export gate (_rule_gate.py, run by on_export, result in SK_RuleArms.glb.check.json "posed_gate", a failure
  stops the export): 104 poses (rifle / pistol aim, both reloads, unarmed attack, jog every 6 frames; both guns at the
  hip and aimed with the hands solved): 0 failed, nearest skin to the eye 12.4 cm, worst capsule excess -0.8 cm.
- Skin (_rule_tex.skin_texels rewritten, no longer the first version's recoloured patterns): target albedo
  0.115 / 0.062 / 0.038 (R/B 3.0, was 4.3; shared with the head and the body), melanin variation, lighter inner
  forearm, darker elbows / knuckles / nail folds, veins as soft raised forms with a slight cool shift, skin-line grooves,
  creases round the limb and the forearm's own skin lines, pores only as a light breakup, hair as soft strands lying
  toward the elbow; roughness 0.55-0.7 with cavity and low-frequency breakup; the streak layer is gone; AO / cavity blur
  normalised by the island mask (no smearing at island edges). Preview material: subsurface 1.0, radius
  1.0 / 0.4 / 0.25 (3.5 mm scale), specular 0.35, a thin coat as the second lobe (SP_RuleSkin values in CHARACTERS.md).
- Palms: by the surface's own direction against the back of the hand / finger, blended over about 1-1.4 cm round
  the palmar border, 15-25 % lighter and warmer; flexion creases, thenar / hypothenar and finger pads as height.
- Tattoos: UnifrakturMaguntia (blackletter), Pinyon Script, Old Standard Bold (OFL, art/blender/fonts) at the photo's
  scale (word 28 mm caps, script 17 mm, numerals 22 mm in two rows), blue-black ink (linear 0.02-0.03) bled 0.4 mm with
  a halo, roughness calmed over it. The private tattoos.json now sets the word as the game's name (no real name).
- Hands on the guns (_characters_pose.hold): palm on the gun's Palm_R / Palm_L (read from the file), the rig placed by
  a search over slide, drop and the hand's tilt for the least wrist bend, fingers brought together, then each finger
  closed onto the gun's BVH (coupled sweep, then the end joints) to 1.5 mm, trigger pad and both thumbs on a grid, the
  NINE's support hand over the firing fingers, the CHOPPER's support knuckles at the handguard's lower right edge; the
  aimed CHOPPER is solved on the aimed pose itself.
- Preview tooling: recipe eye (head joint - 0.58 cm), Euler YXZ, views read from config.json; FP previews at 1920x1080.
- Framing: config views[0] re-authored (CHOPPER 0.125, -0.07, -0.215, 0.05, 0.24, -0.34; NINE 0.06, -0.045, -0.26,
  0.06, 0.09, -0.16) in src/config/weapons.js and config.json (verify.cjs: the views agree; its two failing checks,
  canonical decimals and level glazing, were failing before).
- Face (_rule_head.warp_points): brows 5 mm lower with the lid skin folded under them, lid aperture 3.6 mm (was 4.8:
  the lids cover the iris top), heavier hood, face 3.5 % shorter below the eyes, jaw angle and cheek mass +7 / +6 %;
  low thick brows painted with strokes; less shiny forehead (T-zone 0.42). Bandana: paisley 2.5x, white border print.
- Body: SK_RuleArms' skin and tattoos on the body's forearms and upper arms (arm rig from the fitted pose), palms
  toward SK_RuleArms' palm; shirt cleaned to its fold shading with a jersey knit, ghosts of the generated print removed.
- Nails: AO floored at 0.92 on the nail texels (the 1K AO bake made them read black).
- Exports: SK_RuleArms 131,594 tris (check ok), SM_Character_RuleBracelet 21,504, SK_Rule 204,482 (56 MB).
- Previews after the last change: rule_arms_fp, rule_fp_nine (new), rule_hands, rule_arms_hero, rule_body_hero,
  rule_face, rule_turntable, rule_wire. Higgsfield: 0 credits this round.
## Not done (next)
- Corrective shapes (MCP / PIP knuckle crease, pad compression, wrist flexion): none in the GLB; the wrist still pleats
  in deep flexion (rule_arms_hero) and the elbow crease folds on the upper arm.
- The firing wrist sits at the bottom edge of the frame at the hip: the grip is 8.5 cm under the receiver, so only a
  much higher or farther gun would show it; to be judged in the engine with look.viewmodel's lights.
- The per-gun hand poses are previews only: export them as pose clips on SK_Mannequin for the game's hands.
- NINE support hand: fingers over the firing fingers read better, but its thumb and the left index are not ideal.
- Face: no new multi-view photos, so the large forms and the skin texture are still the generated head's (2K upscaled);
  the neck join still shows a faint band and crease. Bandana: still the generated cap shape (no folded band, knot
  remodel or bare scalp above it).


### Lead note: independent re-review of Rule round 3 (for the hands and tattoos pass)

Grades: arms in first person 2, hands 2, tattoos 2, face 2, body 3. The full fault list with measured contact gaps and fixes is in `art/blender/review/rule_r3_final_review.json`: read it before working on the hands. Most visible: the forearm is a smooth tan tube with only a faint smudge for the tattoo; arms go nearly black under the El (the viewmodel needs its own fill light); the firing hand is cropped at the bottom edge; CHOPPER support fingers stand 11-20 mm off the handguard and the firing fist closes in the air; the NINE two-hand hold intersects (1,428 vertices inside) and needs a thumbs-forward hold; fingers glow red from too much subsurface; nails render black.

---------------------------------------------------------------------------------------------------------------
# Rule arms, hands-and-tattoos pass (the owner: "fix the hands and arm tatoos"), character and technical artist

Cause, fix and the in-game proof: `docs/unreal/CHARACTERS.md`, "SK_RuleArms, hands-and-tattoos pass".
## Done
- Tattoos (`_rule_tex.tattoo_chart`): every line across the forearm, letters' tops toward the elbow (the photo); the
  word in heavy serif capitals 21 mm (Old Standard Bold: the photo's lettering is a serif roman), the script line 16 mm
  beside it toward the wrist, the numerals XVII / XXIII 14 mm (r3's IIIXX was the mirror reading; the left chart is now
  drawn mirrored because the left arm is the mirror of the right arm's frame); centred 2.6-3.2 cm toward the thumb side.
  Ink at a fifth of the skin's luminance (r3 a third), 90 % cover, ragged 0.15 mm edge, 0.4 mm bleed, faint halo.
- Hands (`rule.Hand.field`, `bare_palm_sdf`): extensor tendons 1.1 mm (0.5), PIP / DIP knuckle swell, finger shafts slimmed
  0.35-0.45 mm between joints, fuller thenar pad; knuckle wrinkles 120 um (75) in the normal map.
- Nails: the plates now 0.6 mm proud (0.3): the 64k decimation had smoothed the nail bed away and the skin covered the
  middle of every plate (measured: 30 % of nail faces under the skin, now 0 %); the Cycles stand-in has no subsurface on
  the plates. `rule_hands.jpg` now shows pale nails with the lighter free edge (they were black slits).
- `_rule_detail.py`: the tiling skin grain T_RuleArms_SkinDetail_N (24 mm tile, 1024 px) written by the bake; set.json
  records the forearm's texel density (3,902 px/m at 4K) for its tiling in Unreal.
- Export: 131,598 triangles, posed gate 104 poses, 0 failed. Previews rule_arms_fp, rule_hands re-rendered.
  Higgsfield: 0 credits.
## Restart after the usage limit (same pass)
- The in-game forearm close-ups of the cut-off run showed no ink. Cause found: not the art. The tattoo centres measured
  on the exported mesh (vertices in each tattoo's UV box) put the numerals 18.3 cm and the word 19.4 cm above the wrist,
  4.3-4.4 cm off the forearm axis; comparing the GLB's bone frames with the imported asset showed that Unreal's glTF
  import swaps every bone's local Y and Z, so the close-up camera, aimed by glTF-frame axes, looked at the wrong side.
  `tools/box/fp/fp-arms-shots.sh` now aims at the measured point; both tattoos read in play (`docs/unreal/shots/fp-arms-forearm-l/r.jpg`).
- Game skin: less red scatter (`SubsurfaceTint` 0.26 / 0.14 / 0.09, `Scatter` 0.6, `SkinTint` B 1.08) after the sunlit
  forearm under the El still read salmon; re-imported with `import-chars.sh arms`, all six arms pictures retaken.
- No art change (no re-export): the GLB and textures of 15:03 are the ones in the game. Previews `rule_arms_fp`,
  `rule_hands` are from that export. Higgsfield: 0 credits.
- Not done: per-gun finger poses in the game (the NINE rests on the firing hand, fingers straight); corrective shapes.
## Second pass after the in-game review (hands 1.5, tattoos 2.5; same owner)
Cause, fix and the play-frame proof: `docs/unreal/CHARACTERS.md`, "SK_RuleArms, second pass after the in-game review".
- Tattoos (`_rule_tex.TATTOO_LAYOUT`): the left numerals at 11.2 / 14.1 cm above the wrist (were 16.8 / 19.4, off screen
  in play) in 18 mm capitals, plus the photo's second, half-hidden group (XII / XX stand in, 5.3 / 7.7 cm, 17 mm);
  centred 1.0 cm round from the back toward the ulna, the face a probe in play says the eye sees (the first pass's
  "thumb side" was 57-64 degrees off). Script line 19 mm with a 0.45 mm heavier stroke.
- Skin: `SKIN_TARGET` 0.130 / 0.063 / 0.034 (hue 24, saturation 0.50; shared with the head and body, which pick it up
  on their next build).
- Hands: knuckle heads about 1 mm higher, tendons 1.7 mm, tapered distal phalanges with flatter pads, knuckle wrinkles
  220 um on a 0.35 mm joint rise, hand veins 0.8 mm, a form-scale cavity term in AO and base colour, darker sparser
  5 mm hair strands; nails 0.18 mm proud under a cuticle fold that overlaps the root, a lower, narrower free edge.
- ORM blue now carries the pore-detail mask (no metal on skin); `_rule_detail.py` deeper pores and a 2-4 mm undulation.
- `_rule_grips.py` (new): the NINE grip solved on SK_Nine (palms lower on the grip, `wrap_fingers`) written as joint
  points to `unreal/MurderInc/Content/Data/grips.json` and `art/out/glb/SK_RuleArms.grips.json`.
- Export: 131,594 triangles, posed gate 104 poses, 0 failed. Previews not re-rendered (`rule_*.jpg` are from the first
  pass). Higgsfield: 0 credits.
- Not done: CHOPPER inspect / reload finger corrections, hair cards, an inspect roll that shows the word near the right
  elbow with the CHOPPER.
## Second pass, retake after a restart (same owner request)
- The left numerals centred 7.2 cm (main rows) / 6.4-6.8 cm (second group) round from the back toward the radius
  (`_rule_tex.TATTOO_LAYOUT`): the play probe's first reading (1.0 cm toward the ulna) had the rotation reversed and no ink
  showed. Export 18:07 (131,594 triangles, posed gate 0 failed), re-imported into the game; the numerals read in the hip
  and El play frames (`docs/unreal/shots/fp-arms-hip-sun.jpg`, `fp-arms-hip-el.jpg`).
- The NINE: the arms now placed by their shoulders under the eye (`presentation.json` `animSets.pistol.shoulders`,
  `MIFirstPersonRig.cpp` `GripShoulderTranslation`), the solved grip of `_rule_grips.py` reached by the IK: no upper-arm
  stump in the view, both hands round the grip (`fp-arms-nine.jpg`, `fp-arms-nine-ads.jpg`).
- Previews `rule_arms_fp.jpg`, `rule_hands.jpg` re-rendered from the 18:07 export. Open: the hands preview shows the nails
  as dark V shapes (the mesh measures sound: plate 0.42 mm above the bed, nail texels pale; not seen in play frames).
- Not done: CHOPPER inspect / reload finger corrections, hair cards, an inspect forearm roll (the pack inspect keeps the
  support forearm out of frame). Higgsfield: 0 credits.

---------------------------------------------------------------------------------------------------------------
# Weapons round 4: the SHORTY (assets/weapons_shorty.py, _weapons_shorty.py, _weapons_shorty_b.py, _weapons_shorty_tex.py, _weapons_shorty_prev.py, _weapons_check_shorty.py), weapons modeler

Why: the owner played the build on E3DS and wrote "all the guns look the same and no attachments are able to be added to the
guns". True: four of the five offered guns were one purchased-pack M4 (docs/unreal/LOADOUT.md, "Read this first"). The SHORTY
is the first of three new guns of our own, built from the round-4 designer's specification (the contract is `_weapons_shorty.SH`;
the code works in mm, the files are metres). A compact bullpup carbine, 5.6 mm class: the action and the magazine sit BEHIND
the pistol grip, so a 700 mm gun carries a 267 mm barrel. It shares no shape with the CHOPPER, the NINE or the pack rifle:
a tall olive polymer block, a see-through carry handle (150 x 24 mm window) on top, a short ventilated forend, a squat
birdcage hider. Our own design in the manner of the class: markings are invented ('CARBINE S-5.6', 'SAFE SEMI AUTO',
a proof star, serial 'S2-0417').

## State at hand-off: exported and proven (`python art/blender/assets/_weapons_check_shorty.py`: SHORTY ALL FIXED POINTS KEPT, 63 of 63)
- `build.py build weapons_shorty --bake --export` (about 10 min on 2 threads: geometry maps 300 s, per-texel paint 290 s):
  `SK_Shorty` 67,168 triangles (plan 95k, cap 120k; grip 9.7k, butt pad 5.7k, screws 8.6k, barrel 4.6k, body 4.3k, hider 4.3k,
  forend 3.1k, ribs 3.6k, handle + ring 3.5k ...), one slot `M_Shorty` on the unique 4K set `Shorty` (BC, N, ORM, E = the tritium
  insert), 7 deform bones (body root, bolt, trigger, selector, magazine (attach, no vertices), MuzzleDevice, IronsFront) + the 12
  socket bones of the contract, every vertex on one bone with weight 1.0, every bone at rest with the gun's axes, re-import proof
  in a fresh process (all five poses < 5e-8 m); `SM_Weapon_ShortyMagazine` 6,292 + `_TopRound` 2,804 triangles (in place, origin =
  gun origin, 2K set `Weapon_ShortyMagazine`, slot `M_Weapon_ShortyMagazine`); new tiling `TS_GunDetail_Polymer` (12 mm; the steel
  tile is the existing 20 mm one; the slot record gives the repeat per UV: blend by ORM.B, 1 = steel tile, 0 = polymer tile).
- Texel density: 6,120 px/m at 4K on the weight-1 faces (both flanks, top, handle, rail), 75 % on the forend and grip, 50 % on
  the barrel, hider, butt pad and undersides, 30-45 % on interiors; median over all faces 4,570; the magazine 8,033 px/m.
  The specification asks 7,000 on the flanks: the 4K square holds about 0.26 m2 of weighted surface at 60 % packing; unwrap =
  smart project 66 deg, margin 4 (at 2048), CONVEX pack (coverage 56 % of the square), weights from `weapons_shorty.uv_weights`.
- The proof (all measured on the re-imported files): every bone and socket 1e-5 m; box 0..0.700 x -0.043..+0.040 x -0.180..+0.100;
  aperture 9 mm round, centred Z 0.060, front post tip Z 0.060, sight radius 441, the line from the aperture to the post clear
  (first hit the post at X 0.5734); the window 150 x 24 see-through; BOTH MI-R rails tooth by tooth (handle: 12 lugs of 5.3 mm,
  lug tops Z 0.100, slot floors 5.4 mm down, 21.2 mm across the flanks; underside: 10 lugs, lug undersides Z -0.052); Optic,
  Underbarrel, Laser, Palm_L on the rails, MuzzleMount on the thread shoulder (barrel R 9.5 -> R 8.2 at X 0.652); Palm_R 0.01 mm
  from the grip's right face, trigger's rear face X 0.368 = 73 mm ahead of it, grip to magazine gap 24 mm at the bottom, the grip
  33 x 42 mm at palm height; bolt 0..75 mm (1.0-3.0 mm clear of the cavity, the stem 5.3 mm clear of its slot), trigger 0..17
  deg (2.0 mm clear), selector 0 / 14 / 28 deg (0.3 mm), magazine in place and dropped 130 mm: no contact; with MuzzleDevice or
  IronsFront removed no edge opens (the barrel stub R 8.05-8.5 and the bore, R 2.8 to X 0.600, stay); the eye corridors of the
  irons (relief 0.12), the red dot (0.14) and the 4x scope (0.085) are clear.
- Pictures (8 renders, 4 + 4): `art/previews/weapons_shorty_hero.jpg`, `_fp.jpg`, `_side.jpg`, `_parts.jpg`, rendered from the
  exported GLBs with their baked sets; `art/out/ui/T_UI_Gun_Shorty.png` (512 x 192, 2.2 mm per px, bore at y = 84, centred,
  alpha film, the window transparent; not committed) via `MI_PREVIEWS=... build.py build weapons_shorty --preview --only none`.

## Decisions (where the specification was silent, short or inconsistent)
- The carry handle's FRONT leg (X 300..330) would stand in the sight line (Z 60): an 18 x 14 mm sight port is cut through it;
  the proof checks that the line from the aperture ends on the post. The aperture is a lathe cut: 9 mm at X 130..137 (SightRear
  X 0.134), flaring to 19 mm at the front face; the 20 mm ring is a separate solid (a union on the tangent circle left cracks).
- Underside rail: the specification's X 455..560 is 19.8 half-pitches; 10 lugs + 9 slots (100.7 mm) are laid from X 459.95 so
  that Palm_L (0.505) and Laser (0.536) land on lugs; Underbarrel (0.488) falls in a slot (the grip's cross-bolt sits there).
  The top rail is 12 lugs + 11 slots from X 160.0, centred on the Optic socket (a slot centre).
- The ejection port (X 340..400, Z 0..32) cuts the body and the first 5 mm of the forend; the deflector vane starts at its
  front edge (X 400), reaches Y -0.043 (the specification's width), is swept 30 deg at its root, its top falls from Z 37 to 26 and
  its tip is rolled. Vent slots (3 rows x 4 columns of 5 x 14 mm per side) sit at X 480..525 so the vane does not hide them.
- Inside: a carrier cavity (X 215..398, Y +-16, Z -10..33) holds the bolt carrier (bright head, extractor, left stem through the
  slot X 298..386, knob to Y +0.040); the forend is hollow with the barrel, the gas block and a gas tube behind the slots. The
  feed path from the magazine well (X 180..232) to the chamber (X 397) is NOT modelled (the carrier is a block).
- Shells with weapons.P: `weapons_shorty.finish()` (module `_weapons_shorty`) welds coincident vertices before it smooths; P's
  `clean()` deletes faces under 1e-11 m2, which opened the shell after a clamped bevel (the old functions are untouched).
- The first-person picture: the camera sees the gun's LEFT flank (the gun hangs at the right of the picture), which faces away
  from the design sun of 260: the sun is moved to bearing 325 for this picture. The gun sits at the CHOPPER's viewmodel rotation
  with Palm_R on the CHOPPER's Palm_R (the origin of a bullpup is its butt: views[0] = [0.2229, -0.0925, 0.0046, 0.05, 0.28, -0.35]
  in the game's units does that), nudged 6 cm toward the centre so the whole arch is in the frame.
- Texture memory: the per-texel painters run in pieces of 1.5 M texels and free the position, normal and id maps once the flat
  arrays exist (measured peak 1.6 GB at a 2048 draft; the 4K run took 10 min with the other agents' jobs running).

## Known weaknesses (most visible first)
- The parkerised steel (barrel, hider, trigger, magazine) reads near black in the studio pictures: #3b3e39 at metallic 1 mirrors a dark
  room. In the day rig it is a dark green-grey. The magazine body is a lighter phosphate (#4a4d46) for the same reason.
- The flanks are 6,120 px/m, not 7,000; the left flank and the top got the full weight, the forend and the grip 75 %.
- The polymer's wear is restrained: chalky edges, darker handled flats, thin scuffs along X, faint grime runs; the big flanks stay
  mostly clean (no painted variation by hand). Steel wear is bright edges plus scratches, no rust or paint.
- The trigger guard is the specification's 8 x 5 mm D section and reads as a wire loop from the side; the deflector vane is a
  blocky plate (stipple on its flank).
- Nothing was tried in Unreal: no hand pose or IK solve on Palm_R / Palm_L, no part fitted on the rails (the parts kit is another
  agent's), no sight picture through an optic; the proof is geometric (fit rules, corridors, clearances).

## Exact next step
The Unreal integration (docs and data: guns.json shorty -> mesh SK_Shorty, mounts Optic / MuzzleMount (hide MuzzleDevice) /
Underbarrel / Laser / MagHinge, optic.hide IronsFront, no stock slot, parts.bolt.bone 'bolt' travel 0.075, trigger.bone 'trigger',
magazine.bone 'magazine', meshOffset pos [0,0,0] rot [0, 1.5708, 0], eject direction (0.55, -0.80, 0.25), relief 0.12 / 0.14 / 0.085,
views[0] as above) and the animation work on Palm_R / Palm_L. If the art changes: `build.py build weapons_shorty --bake --export`
then `python art/blender/assets/_weapons_check_shorty.py` (a draft is `--res 1024`, about 2 min).
