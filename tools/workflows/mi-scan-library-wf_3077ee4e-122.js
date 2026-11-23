export const meta = {
  name: 'mi-scan-library',
  description: 'Curate free CC0 photoscanned surfaces, skies and props from Poly Haven into the art conventions, then verify them',
  phases: [
    { title: 'Curate', detail: 'download, convert, measure real-world scale, catalogue' },
    { title: 'Verify', detail: 'independent check of files, scale, seams and conventions' },
  ],
}

const REPO = '/home/user/MURDER-INC.'
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'

const COMMON = [
  'PROJECT CONTEXT',
  REPO + ' holds "MURDER INC.", a browser first-person shooter owned by the user that is being REBUILT in Unreal Engine 5 with photoreal graphics; the art is authored in Blender by Python scripts. Setting: Hollis, Queens, New York: Jamaica Avenue under a riveted steel elevated train line, brick tenements, storefronts with roll-down gates, a cinder-block auto body shop, a chain-link ball court, a parking lot; summer afternoon by default, night as the alternate look. Read docs/DESIGN.md sections 4 and 8 for the place.',
  'Environment: Python with Blender 5.3.0 as a module: ' + PY + ' (import bpy; numpy and pillow installed); plain python3 also available. CPU only, 4 cores shared with other agents: Cycles on CPU with 2 threads, small renders only. Your knowledge of bpy may predate Blender 5.x: verify what you use against the running module.',
  'Network: the user approved exactly one asset source for this session: Poly Haven\'s download host https://dl.polyhaven.org (all Poly Haven assets are CC0). Use DIRECT FILE URLS ONLY. Do not call api.polyhaven.com (its terms for automated and commercial use could not be read from here), do not fetch from GitHub or any other site, do not try to route around the proxy. Be a polite client: User-Agent "asset-pipeline/1.0", at most 4 concurrent requests, cache every download and never fetch the same file twice, at most 300 existence probes in total.',
  'URL scheme (verified): textures https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/<slug>/<slug>_diff_2k.jpg (other maps use _nor_gl, _rough, _arm (ambient occlusion, roughness, metallic packed in R, G, B), _ao, _disp; other resolutions 1k, 4k, 8k; png and exr variants live under Textures/png/ and Textures/exr/); skies https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/<slug>_2k.hdr (also exr and 4k); models https://dl.polyhaven.org/file/ph-assets/Models/gltf/2k/<slug>/<slug>_2k.gltf (the .gltf lists its .bin and texture files as relative URIs: download those from the same folder). A HEAD request tells you whether a file exists. art/scans/probe.py already does HEAD probes: "python3 art/scans/probe.py textures|hdris|models slug ...".',
  'Slugs already confirmed to exist. Textures: asphalt_01 asphalt_02 asphalt_04 asphalt_05 asphalt_06 aerial_asphalt_01 asphalt_pit_lane asphalt_track concrete_floor_01 concrete_floor_02 concrete_floor_painted concrete_floor_worn_001 concrete_pavement concrete_pavement_02 concrete_tiles_02 concrete_wall_001 concrete_wall_003 concrete_wall_006 concrete_wall_008 concrete_slab_wall concrete_block_wall red_brick_03 red_bricks_04 red_brick_plaster_patch_02 brick_wall_02 brick_wall_006 brick_4 mixed_brick_wall brick_pavement_02 painted_brick dark_brick_wall brown_brick_02 yellow_bricks rusty_metal_02 rusty_metal_03 rusty_metal_04 rusty_metal_05 rust_coarse_01 metal_plate metal_plate_02 corrugated_iron corrugated_iron_02 corrugated_iron_03 painted_metal_shutter worn_shutter blue_metal_plate green_metal_rust metal_grate_rusty factory_wall rough_plasterbrick_05 plaster_grey_04 painted_plaster_wall white_plaster_02 beige_wall_001 plywood wood_planks_grey old_planks_02 weathered_planks weathered_brown_planks raw_plank_wall gravel_floor_02 gravelly_sand sandy_gravel_02 dirt_floor brown_mud_leaves_01 gravel_concrete_03 cracked_concrete_wall floor_tiles_06 roof_07 rubber_tiles denim_fabric leather_white garage_floor large_square_pattern_01. Skies: kloofendal_43d_clear_puresky kloofendal_48d_partly_cloudy_puresky syferfontein_0d_clear_puresky sunflowers_puresky qwantani_afternoon_puresky qwantani_puresky belfast_sunset_puresky wide_street_01 wide_street_02 urban_street_01 urban_street_02 urban_street_03 urban_street_04 canary_wharf potsdamer_platz shanghai_bund night_bridge rooftop_night satara_night dikhololo_night moonless_golf moonlit_golf rogland_clear_night cobblestone_street_night blaubeuren_night. Models: boombox fire_hydrant street_lamp_01 street_lamp_02 concrete_road_barrier concrete_road_barrier_02 barrel_03 Barrel_01 wooden_crate_02 cardboard_box_01 metal_trash_can utility_box_01 utility_box_02 metal_tool_chest propane_tank korean_fire_extinguisher_01 modular_electric_cables security_camera_01 security_camera_02 Television_01 vintage_video_camera steel_frame_shelves_01 steel_frame_shelves_03 plastic_monobloc_chair_01 folding_wooden_stool. Confirmed missing (do not probe again): cracked_asphalt road_asphalt brick_wall_001 concrete_tiles_01 concrete_brick_wall_001 cinder_blocks red_brick_04 brick_wall_003 church_bricks_02 old_brick_wall factory_brick_wall painted_metal_02 fabric_pattern_07 patterned_concrete_pavement diamond_plate metal_grate galvanized_steel_01 city_night_rooftop traffic_cone barrel_01 trash_can dumpster shopping_cart jerrycan wet_floor_sign_01 plastic_chair mattress tire car_tire wooden_pallet pallet gas_cylinder fire_extinguisher industrial_pipe drill_01 ladder metal_ladder camping_table tool_box bench_vice.',
  'Rules: write only under art/scans/ (scripts, catalogue, README: committed), art/out/ (downloads and converted files: git-ignored, large) and art/previews/ (only files whose names start with "scans_"). Never touch art/blender/ (another team is building the pipeline library there right now), src/, dist/, test/, tools/, docs/. Do not commit or push. Look at every image you produce (open it with the Read tool).',
].join('\n')

const CONV = [
  'CONVENTIONS (fixed; other agents rely on them)',
  '- Tiling texture sets are named TS_<Surface>_<Variant> (for scans use a variant that says so, e.g. TS_Asphalt_ScanA). Files: art/out/textures/<Set>/T_<Set>_BC.jpg (sRGB base colour), T_<Set>_N.jpg (tangent-space normal, OpenGL convention), T_<Set>_ORM.jpg (R = ambient occlusion, G = roughness, B = metallic, linear), T_<Set>_H.png (height/displacement, 16-bit if the source is). Keep the source JPEG bytes where no conversion is needed.',
  '- Skies go to art/out/hdri/<slug>_2k.hdr. Scanned prop models go to art/out/scans/models/<slug>/ exactly as downloaded (another agent will re-export them later).',
  '- Blender axes: metres, Z up, east = +X, north = +Y. Props: forward = +X, pivot at the centre of the footprint on the ground.',
  '- Physical correctness matters more than anything: each tiling set must state the real-world size in metres that one tile covers, measured, not guessed (count brick courses: a US modular brick course is 67 mm including the joint, a block course 203 mm; asphalt aggregate is mostly 5 to 20 mm; sidewalk broom finish lines are 2 to 4 mm; roll-shutter slats are 50 to 75 mm).',
].join('\n')

const RESULT_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    sets: { type: 'array', items: { type: 'string' } },
    skies: { type: 'array', items: { type: 'string' } },
    models: { type: 'array', items: { type: 'string' } },
    gaps: { type: 'array', items: { type: 'string' } },
    disk_mb: { type: 'number' },
  },
  required: ['summary', 'sets', 'gaps'],
}

const CURATE_PROMPT = [
  COMMON,
  '',
  'ROLE: texture and asset librarian.',
  'GOAL: a curated, physically calibrated library of scanned surfaces, skies and props for this block, in the project conventions, reproducible by one command (art/out/ is git-ignored, so the scripts and the catalogue are the deliverable).',
  '1. art/scans/sets.json: the catalogue. For each entry: set (TS_... name, or the slug for skies and models), slug, kind (texture, hdri, model), use (where on the block it goes), tile_m (real size of one tile in metres, [x, y]) with how it was measured, resolution, files, colour notes (does it need grading toward New York brick, grime, etc.), licence ("CC0, Poly Haven"). Cover at least: road asphalt (2 variants: aged with cracks, and patched), parking-lot and ball-court asphalt, sidewalk concrete (flags), kerb/cast concrete, garage floor, red and brown tenement brick (3 or more variants), painted brick, cinder block (the auto body shop), plaster/stucco, roll-down shutter steel (2), corrugated metal, painted steel with rust (for the elevated structure: dark green/brown/black paint), bare rusty steel, metal plate, timber (railway ties: weathered planks) and plywood (the scaffold deck, hoardings), gravel and dirt (the vacant lot), flat-roof surface, rubber. Probe for more candidate slugs where the confirmed list has gaps (chain-link, tar or bitumen roofing, awning fabric, floor tiles, graffiti-free painted metal, galvanised steel, cast iron, cardboard, tarp).',
  '2. art/scans/fetch.py: "python3 art/scans/fetch.py [--res 2k|4k] [--only set ...]" downloads what the catalogue lists (cached under art/out/scans/raw/), writes the convention files, builds the packed ORM from separate maps when no _arm file exists, verifies every image opens and has the expected size, and prints a table. Standard library plus pillow and numpy only. Idempotent.',
  '3. Run it at 2k for everything in the catalogue. Download the confirmed models with their .bin and texture files; for each, read the glTF to record real dimensions (bounding box in metres), triangle count and texture list in the catalogue, and note what must be fixed to meet the conventions (pivot, forward axis, scale).',
  '4. Calibrate: for every tiling set measure the real-world tile size from the image itself (count courses, slats, joints, aggregate) and record the method. Check each tiles seamlessly (compare wrapped edges numerically with interior neighbours) and record any that do not.',
  '5. Pictures in art/previews/ (1280x720 JPEG, at most 300 kB each): scans_sheet_1.jpg, scans_sheet_2.jpg ... rendered in Blender with Cycles: each surface on a 4 m x 4 m ground or wall panel at its measured scale, lit by one of the downloaded clear-sky HDRIs, with a 1.8 m tall grey human-scale box and a 1 m stick beside it, labelled with the set name; scans_models.jpg: every downloaded model on a ground plane at its real size next to the same scale box, labelled; scans_skies.jpg: a small render of a chrome and a grey sphere under each sky. Look at them: wrong scale is obvious next to the scale box. Fix the catalogue until every surface reads at the right scale.',
  '6. art/scans/README.md: what this is, the licence (CC0), the direct-download rule, how to re-run, the table of sets with their real sizes and intended uses, what is still missing and would have to be made procedurally or photographed.',
  '',
  CONV,
  '',
  'Reply through the structured output: summary (at most 150 words), sets (the TS_ names), skies, models, gaps (surfaces or props the block needs that Poly Haven does not provide), disk_mb (size of art/out after your run).',
].join('\n')

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string' },
    problems: {
      type: 'array',
      items: {
        type: 'object',
        properties: { severity: { type: 'string' }, item: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' }, fixed: { type: 'boolean' } },
        required: ['severity', 'item', 'problem', 'fix'],
      },
    },
  },
  required: ['verdict', 'problems'],
}

function verifyPrompt(r) {
  return [
    COMMON,
    '',
    'ROLE: reviewer. A librarian just built a scanned-asset library under art/scans/ (catalogue sets.json, fetch.py, README.md), converted files under art/out/textures/, skies under art/out/hdri/, models under art/out/scans/models/, and pictures art/previews/scans_*.jpg. Their report: ' + (r ? r.summary : '(none)') + ' Gaps they list: ' + (r && r.gaps ? r.gaps.join(' | ') : 'none'),
    'Check independently and assume errors exist:',
    '1. Reproducibility: move art/out/textures aside (rename it), run "python3 art/scans/fetch.py" and confirm it rebuilds everything from the cache with no new downloads and no errors; restore if anything goes wrong.',
    '2. Files: every catalogue entry has its files; images open; BC is sRGB-looking colour, N is a tangent normal map in OpenGL convention (mostly blue, green pointing up: test by checking that a surface lit from above looks raised where the height map is high), ORM has roughness in G and near-zero metallic in B for non-metals; names follow the conventions exactly.',
    '3. Scale: re-measure the real-world tile size of at least eight sets yourself (count brick courses, block courses, shutter slats, plank widths) and compare with the catalogue; anything off by more than 15 percent is a problem. Look at every scans_*.jpg picture: does each surface read at the right scale next to the 1.8 m box?',
    '4. Seams: verify numerically that each set tiles (wrapped edge difference against interior neighbour difference) and agree or disagree with what the catalogue says.',
    '5. Fitness: for each intended use on the block, is the chosen scan plausible for outer-borough New York (brick colour and bond, concrete flags, shutters)? Name better confirmed slugs where the choice is weak.',
    '6. Models: dimensions in the catalogue against the glTF data; flag anything not at real-world scale.',
    'Fix what is cheap and unambiguous yourself (catalogue values, README), re-run fetch.py if you change the catalogue, and report the rest. Each problem: severity (blocker, major, minor), item, problem, fix, fixed (true if you fixed it).',
    '',
    CONV,
  ].join('\n')
}

phase('Curate')
const lib = await agent(CURATE_PROMPT, { label: 'scans:librarian', phase: 'Curate', schema: RESULT_SCHEMA })
phase('Verify')
const check = await agent(verifyPrompt(lib), { label: 'scans:verify', phase: 'Verify', schema: VERIFY_SCHEMA })
return { library: lib, check }
