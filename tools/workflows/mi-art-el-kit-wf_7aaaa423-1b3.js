export const meta = {
  name: 'mi-art-el-kit',
  description: 'Resume the Blender pipeline: document the library, wire in the scanned texture sets, build the elevated-line kit and refresh the street section',
  phases: [
    { title: 'El kit', detail: 'library README, scan-backed materials, El modules, look-dev renders, GLB export' },
  ],
}

const REPO = '/home/user/MURDER-INC.'
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'

const PROMPT = [
  'PROJECT CONTEXT',
  REPO + ' holds "MURDER INC.", a browser first-person shooter owned by the user that is being REBUILT in Unreal Engine 5.9 with photoreal graphics. Art is authored in Blender by Python scripts (reproducible, reviewable) and exported as GLB for Unreal. Setting: Hollis, Queens: Jamaica Avenue under a riveted steel elevated train line ("the El"), a hot clear summer afternoon by default. Read docs/unreal/ART_BIBLE.md (sections on the target, materials, modelling bar; skim the rest) and the El parts of docs/unreal/spec/05-level.md (search for "El": column rows, spacing, deck height, widths, stairs) before modelling; the web source for the El layout is src/level/el.js.',
  'The user pays for every token: work efficiently, read selectively, and do not polish beyond what the task asks. Final look development happens later in Unreal (Lumen); Blender renders here are sanity checks, not the product. What matters most from you: correct, detailed, well-UV-mapped modular geometry with sensible material slots, exported and validated.',
  '',
  'ENVIRONMENT',
  'Python with Blender 5.3.0 as a module: ' + PY + ' (import bpy; numpy and pillow installed). CPU only, 4 cores shared with other agents: Cycles on CPU with 3 threads; renders at most 1280x720 and 64 samples with denoising; at most about 12 renders in total. Your bpy knowledge may predate Blender 5.x: check the running module instead of trusting memory. Internet: only https://dl.polyhaven.org direct file downloads (CC0), through art/scans/fetch.py; do not call any other site or API.',
  'Rules: write only under art/ (never src/, dist/, test/, tools/, docs/, unreal/). Do not commit or push. Look at every image you render (open it with the Read tool).',
  '',
  'WHAT EXISTS (written by earlier agents that were cut off before finishing; treat it as unreviewed)',
  '- art/blender/mi/: scene.py, geo.py (bmesh helpers, UV helpers, vertex-colour wear masks), mat.py (procedural PBR materials), bake.py, export.py (GLB/FBX export, manifest, validation), render.py (day and night look-dev rigs, cameras, contact sheets); art/blender/build.py (command line: list / build <family> [--bake] [--export] [--preview]); art/blender/assets/street.py (a 20 m street section: road, kerb, sidewalk, manhole, drain, hydrant) with previews in art/previews/ (street_day_hero.jpg and others). There is no README yet.',
  '- art/scans/: sets.json (catalogue of 83 scanned tiling texture sets with measured real-world tile sizes, 25 sky HDRIs, 40 scanned prop models, all CC0 from Poly Haven), fetch.py, calibrate.py, render_sheets.py, README.md; downloaded and converted files under art/out/textures/<Set>/T_<Set>_{BC,N,ORM,H}.*, art/out/hdri/*.hdr, art/out/scans/models/<slug>/; contact sheets art/previews/scans_sheet_*.jpg.',
  '',
  'CONVENTIONS (fixed)',
  '- Blender: metres, Z up, east = +X, north = +Y (web game x, y, z maps to Blender x, -z, y). Unreal later: (x_blender, -y_blender, z_blender) * 100.',
  '- Pivots: props at the centre of the footprint on the ground, forward = +X. Modular street and structure pieces: pivot at the west end on the centre line at ground level, running along +X. Wall modules: pivot at the bottom-left corner of the outer face, running along +X, outer face toward -Y.',
  '- Names: SM_<Family>_<Name>[_<Variant>]. Tiling sets TS_<Surface>_<Variant> used through material slots named MI_<Surface>_<Variant>; unique baked sets named after the asset with slot M_<Asset>. Textures T_<Set>_BC / _N (OpenGL normal) / _ORM (AO, roughness, metallic) / _H.',
  '- Large and modular surfaces use TILING sets with world-scale UVs (the set\'s real tile size from sets.json) plus vertex-colour wear masks (R cavity dirt, G edge wear, B downward leak and rust streaks, A ground splash-back): do not bake unique textures for them. Model real detail as geometry when larger than about 5 mm (rivets, bolt heads, plate edges); bevel hard edges; keep each module under about 300k triangles.',
  '- Outputs: art/out/ (git-ignored) holds .blend, GLB, textures and manifest.json; committed are art/blender/** and art/previews/*.jpg (1280x720, at most 300 kB each).',
  '',
  'YOUR TASK',
  '1. Get oriented quickly: run build.py list and a build of the street family to confirm the library works end to end; fix what is broken. Write art/blender/README.md (set-up: pip install bpy==5.3.0 numpy pillow; conventions; a short reference of the helpers that matter; how to add a family in under 40 lines; Blender 5.3 notes you confirm).',
  '2. Scan-backed materials: make mat.py able to build a material from a catalogued set by name (textures from art/out/textures/<Set>/, real tile size from art/scans/sets.json, the same wear-mask and wetness interface as the procedural materials), and make the DAY look-dev rig light with one of the downloaded clear-sky HDRIs (for example kloofendal_43d_clear_puresky or qwantani_afternoon_puresky) so lighting is physically plausible. Use scanned sets wherever one fits; keep procedural layers for what scans cannot give (road markings, patches, wet gutter).',
  '3. The family art/blender/assets/el.py: the elevated line as a modular kit, keeping the game\'s overall dimensions and building the real structure they stand for (early twentieth-century New York elevated construction): SM_El_Column (built-up riveted steel column from plates and angles with batten plates, on a concrete pedestal with base plate and anchor bolts), SM_El_Bent (transverse plate girder with stiffener angles, rivet rows, gusset plates and knee braces), SM_El_GirderSpan_10m (longitudinal plate girders and stringers), SM_El_Deck_10m (open deck: timber ties with daylight between them, two tracks of running rails at 1.435 m gauge with tie plates, guard rails, third rail with cover board, a steel walkway with pipe railing, cable trough), SM_El_Lamp (the fixture hung under the deck). Material slots on tiling sets (painted steel with rust for the structure, weathered timber for ties, concrete for pedestals) with wear masks painted from the geometry. Export every module as GLB, update the manifest, run the export validation.',
  '4. A look-dev scene: three bays of the El over 30 m of the street family. Previews (art/previews/): el_day_hero.jpg (eye level on the sidewalk looking along the avenue under the structure: the sun must stripe the road through the ties), el_day_column.jpg (a column and pedestal at eye level, close), el_day_under.jpg (looking up at bent, girders and deck), el_wire.jpg (clay or wireframe proving the modelled detail), and a refreshed street_day_hero.jpg using the scan-backed materials and HDRI lighting. Two self-review rounds at most: fix the worst visible fault each round (scale, missing thickness, noise that reads as noise).',
  '',
  'Reply through the structured output: summary (at most 150 words), files (what you wrote or changed), previews (paths), assets (exported SM_ names with triangle counts), known_weaknesses (honest list, most visible first).',
].join('\n')

const SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    previews: { type: 'array', items: { type: 'string' } },
    assets: { type: 'array', items: { type: 'string' } },
    known_weaknesses: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'previews', 'known_weaknesses'],
}

const STATE = [
  '',
  'STATE NOTE: an earlier run of this exact task was cut off by a usage limit after about 12 minutes. It changed the library (art/blender/mi/__init__.py, geo.py, mat.py, render.py, export.py, art/blender/build.py, art/blender/assets/street.py), added art/blender/mi/steel.py and art/blender/assets/el.py, and rendered art/previews/el_wire.jpg. Review that work (look at el_wire.jpg) and continue from it; do not start over. You may be cut off without warning as well: keep art/blender/PROGRESS.md current (what is done, the exact next step) and leave files in a runnable state after each step.',
].join('\n')
phase('El kit')
const r = await agent(PROMPT + STATE, { label: 'art:el-kit', phase: 'El kit', schema: SCHEMA, effort: 'high' })
return r
