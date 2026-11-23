export const meta = {
  name: 'mi-art-foundation',
  description: 'Build the Blender art pipeline library and two photoreal exemplars (street section, El bay), then art-direct, refine and verify them',
  phases: [
    { title: 'Foundation', detail: 'pipeline library + street-section exemplar' },
    { title: 'El exemplar', detail: 'one bay of the elevated line, built with the library' },
    { title: 'Art direction', detail: 'independent review of the renders and the library' },
    { title: 'Refine', detail: 'fix the review findings and re-render' },
    { title: 'Verify', detail: 'fresh eyes on the refined renders' },
  ],
}

const REPO = '/home/user/MURDER-INC.'
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'

const COMMON = [
  'PROJECT CONTEXT',
  REPO + ' holds "MURDER INC.", a browser first-person shooter (three.js, stylised low-poly, everything procedural) that belongs to the user. It is being REBUILT in Unreal Engine 5 with photoreal, current-generation graphics ("much better graphics and textures, realistic next-gen graphics" is the brief). The art is authored in Blender by Python scripts so it is reproducible and reviewable. Setting: Hollis, Queens: Jamaica Avenue under a riveted steel elevated train line ("the El"), a hot clear summer afternoon about 4:15 PM by default, 02:14 AM night as the alternate look. Read docs/DESIGN.md sections 4, 5 and 8 for the place and the look (ignore its "stylised low-poly, no photo textures" lines: those describe the old web version).',
  'Environment: Python with Blender 5.3.0 as a module: ' + PY + ' (import bpy; numpy and pillow installed). CPU only, 4 cores shared with other agents: set Cycles to CPU with 3 threads and keep renders modest. Cycles renders headless here (a 640x360, 32-sample test took 6 s). EEVEE has no GPU here: use Cycles for everything. FBX, glTF and USD exporters are present. Internet: PyPI and docs.blender.org only; texture and asset sites are blocked, so all textures are procedural for now (design so that scanned texture sets can be dropped in later).',
  'Your knowledge of the bpy API may predate Blender 5.x: verify what you use against the running module (dir(), bl_rna, small throwaway scripts) instead of trusting memory. Known: material.use_nodes and world.use_nodes are deprecated (node trees always exist).',
  'Rules: write only under art/ (plus one line in the repo .gitignore where your task says so). Never touch src/, dist/, test/, tools/, docs/. Do not commit or push. Other agents are working in parallel elsewhere in the same checkout. Look at every image you render (open the JPEG/PNG with the Read tool): a render you have not looked at does not count.',
].join('\n')

const CONV = [
  'SHARED CONVENTIONS (fixed; other agents rely on them)',
  '- Coordinates. Web game (three.js): metres, +Y up, north = -Z, east = +X. Blender: metres, Z up, east = +X, north = +Y, so Blender(x, y, z) = (x_web, -z_web, y_web). Unreal: centimetres, Z up, X = east, Y = south, so Unreal(X, Y, Z) = (x_blender, -y_blender, z_blender) * 100.',
  '- Forward axes and pivots. Props, vehicles and weapons: forward = +X, pivot at the centre of the footprint on the ground (z = 0). Characters face -Y in Blender. Wall/facade modules: pivot at the bottom-left corner of the outer face, running along +X, outer face looking toward -Y. Modular street/structure pieces: pivot at the west end on the centre line, at ground level, running along +X.',
  '- Names. Static meshes SM_<Family>_<Name>[_<Variant>]. Tiling texture sets TS_<Surface>_<Variant>, used through a material slot named MI_<Surface>_<Variant>; unique baked sets are named after their asset, slot name M_<Asset>. Textures T_<Set>_BC (sRGB base colour), T_<Set>_N (tangent-space normal, OpenGL convention as Blender bakes it; say so in the manifest), T_<Set>_ORM (R = ambient occlusion, G = roughness, B = metallic, linear), optional T_<Set>_H (height) and T_<Set>_E (emissive).',
  '- Two material workflows, both required. TILING sets for large and modular surfaces (asphalt, concrete, brick, painted steel): seamless, a stated real-world size per tile (default 2048 px over 2 m), meshes carry world-scale UVs plus vertex-colour wear masks: R = cavity dirt/grime, G = edge wear/chips, B = downward leak/rust streaks, A = ground splash-back/wetness. UNIQUE baked sets for hero props (one 2048 px set per prop by default; 1024 px/m for anything held in first person, 512 px/m for cover props).',
  '- Quality bar: photoreal and physically based. Real-world dimensions. Albedo inside physical ranges (nothing pure black or white: charcoal about 0.02 to 0.05, aged asphalt 0.06 to 0.12, concrete 0.35 to 0.5, white paint at most 0.8). Metallic = 1 only where bare metal shows. Every hard edge bevelled (2 to 10 mm on props, 5 to 20 mm on architecture) so edges catch light. Wear, dirt, rust, leaks and paint chips follow physical causes (cavities, exposed edges, gravity, water paths, foot and tyre traffic), never uniform noise. Nothing stylised or low-poly: Unreal renders the triangles with Nanite, so model real detail (rivets, bolt heads, weld seams, gaskets, conduit) as geometry when it is larger than about 5 mm. Keep each asset under about 300k triangles.',
  '- Outputs. Generated and git-ignored: art/out/blend/<family>.blend, art/out/glb/<SM_name>.glb, art/out/textures/<Set>/T_*.png, art/out/manifest.json. Committed: art/blender/** (scripts and README) and art/previews/*.jpg (1280x720, at most 300 kB each).',
].join('\n')

const RESULT_SCHEMA = {
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

const FOUNDATION_PROMPT = [
  COMMON,
  '',
  'ROLE: senior technical artist and pipeline engineer.',
  'GOAL: (1) a reusable Blender-Python art pipeline under art/blender/ that about ten other artists (agents) will use next to build the whole block; (2) one exemplar family, a street section, that proves the photoreal bar end to end: model, materials, bake, export, preview render.',
  '',
  'STEP 0. Introspect Blender 5.3 with small throwaway scripts and confirm: selecting Cycles on CPU with a thread count; OpenImageDenoise for final renders; bpy.ops.object.bake into image nodes for base colour (diffuse, colour only), roughness, normal, emission and ambient occlusion; the Principled BSDF input names; the identifiers of the mix, colour-ramp, noise, voronoi, brick, bump and attribute nodes; the Sky Texture node options for a physically based sun and sky; glTF and FBX export operator arguments; saving a .blend from the module; colour management (AgX or Filmic) names. Write every non-obvious finding into art/blender/README.md under "Blender 5.3 notes" so nobody rediscovers it.',
  '',
  'STEP 1. The library art/blender/mi/ (small, documented, importable as "mi" when art/blender is on sys.path):',
  '- scene.py: reset to an empty metric scene, collections, a seeded RNG helper, apply transforms, set pivots.',
  '- geo.py: the bmesh helpers modellers need constantly: box with bevelled edges, extruded profile along a path, plates with holes, cylinders/tubes/pipes with bends, linear and radial arrays, instance-then-realise for rivets and bolt heads, boolean cut helper, smooth-by-angle and weighted normals the 5.x way, UV helpers (world-scale box projection at a chosen texel density for tiling sets; smart unwrap and pack for unique sets), and vertex-colour wear-mask painting from geometry (R cavity dirt, G exposed-edge wear, B gravity leak streaks below fasteners and ledges, A splash-back near the ground).',
  '- mat.py: physically based procedural materials as node groups with exposed parameters: asphalt (aged, with visible aggregate, cracks, tar-sealed cracks, utility patches, oil stains, wetness and puddles), concrete (sidewalk flags with scored joints, cast-in-place, weathered, gum stains), brick (running bond with recessed mortar, per-brick colour variation, efflorescence, soot), painted steel (chips to primer and bare metal, rust bleed, grime), raw, galvanised and cast metal, rubber, glass, timber and plywood, plastic, and road paint as a worn blend layer. Every material: real-world scale in metres from object or world coordinates so it never stretches, albedo in physical range, wear driven by the vertex-colour masks (and by pointiness or ambient occlusion where useful), a "wetness" control. Also from_texture_set(directory) that builds the same interface from T_*_BC/N/ORM/H files on disk.',
  '- bake.py: bake any material on any mesh to T_<Set>_BC/N/ORM (and H, E when present) PNG files, ORM packed with numpy; bake_tiling_set(...) that produces SEAMLESS tiling sets for large surfaces: prove seamlessness by rendering a 2x2 tiled preview and by a numeric check (pixel differences across the wrapped edges must be as small as between interior neighbours).',
  '- export.py: export objects to art/out/glb/<SM_name>.glb (textures referenced by the convention, not duplicated into every file when the set is shared) and optionally FBX with settings that import into Unreal at the right size (metres to centimetres, no 0.01 or 100 actor scale); write/merge art/out/manifest.json per asset: name, family, triangles, vertices, bounds in metres, pivot, material slots mapped to set names, texture files and their convention (normal map is OpenGL), texel density, collision hint (box, convex or complex; cover height), notes. Validate on export: transforms applied, no zero-area faces, consistent normals, naming convention, bounds close to the brief.',
  '- render.py: look-dev rigs: DAY (physically based sky and sun for a clear New York summer afternoon about 4:15 PM: sun elevation about 45 degrees, from the south-west) and NIGHT (dark blue sky glow, sodium-vapour street light about 2100 K from above, optional coloured sign light), AgX or Filmic view transform, sensible exposure presets, camera helpers (frame an object, eye-level shot at 1.65 m, three-quarter hero shot, top-down orthographic), render to JPEG at 1280x720 with denoising under 300 kB, a contact-sheet helper.',
  '- art/blender/build.py, the command line: "build.py list", "build.py build <family> [--bake] [--export] [--preview] [--res 2048] [--samples 96]". A family is a module art/blender/assets/<family>.py exposing FAMILY (name and description) and build(ctx) that returns the created objects. It must work both with the bpy module (' + PY + ' art/blender/build.py ...) and inside Blender (blender -b -P art/blender/build.py -- ...).',
  '- art/blender/README.md: setup (pip install bpy==5.3.0 numpy pillow), the conventions, a library reference with short examples, "how to add an asset family" in at most 40 lines, the Blender 5.3 notes, known limits.',
  '- Append "art/out/" to the repo .gitignore (the one edit allowed outside art/).',
  '',
  'STEP 2. The exemplar family art/blender/assets/street.py: a 20 m long (east-west, along X) by 22 m wide cross-section of the avenue:',
  '- Roadway 14 m wide (y from -7 to 7): two travel lanes and two parking lanes, a slight crown and gutters; aged asphalt with visible aggregate, longitudinal and alligator cracks, tar-sealed cracks, one rectangular utility patch, oil drips along the parking lanes, tyre-polished wheel paths; a worn double yellow centre line and worn white parking-lane lines; one cast-iron manhole cover in its frame (generic lettering such as "SEWER", invented foundry mark, no real company names) and one storm-drain inlet with a grate at the kerb.',
  '- Kerbs 150 mm high: concrete with a steel facing angle, chipped and stained; a driveway dropped kerb is not needed.',
  '- Sidewalks 4 m wide on both sides (y from 7 to 11 and -11 to -7): cast concrete flags about 1.5 m square with tooled joints, cracks, patches of newer concrete, chewing-gum spots, stains at the kerb line.',
  '- One fire hydrant on the south sidewalk (generic two-nozzle municipal hydrant with bonnet, nozzle caps and chains, flange bolts; weathered paint), leaking: a wet patch and shallow puddles run from it along the gutter to the drain. The rest of the street is dry.',
  '- Build it as modular pieces with correct pivots: SM_Street_Road_20m, SM_Street_Kerb_4m, SM_Street_Sidewalk_4m, SM_Street_ManholeCover, SM_Street_DrainInlet, SM_Prop_Hydrant; tiling sets TS_Asphalt_Aged and TS_Concrete_Sidewalk (baked and proven seamless), unique sets for the hydrant and the manhole cover. Export everything and write the manifest.',
  '- Previews in art/previews/: street_day_hero.jpg (eye level on the south sidewalk looking east along the street), street_day_top.jpg (orthographic), street_night_hero.jpg (same view under the night rig: the wet gutter must show reflections), hydrant_day.jpg (three-quarter close view), manhole_day.jpg, materials_sheet.jpg (every library material on a 2 m plane and a sphere, labelled), tiling_asphalt_2x2.jpg and tiling_concrete_2x2.jpg.',
  '',
  'STEP 3. Self-review, at least three rounds for the hero shot: open each preview and compare it honestly with a photograph of a real New York street. What gives it away as computer-made (flat even colour, noise that reads as noise, razor-sharp or missing edges, wrong scale of aggregate or cracks, plastic-looking highlights, no contact shadows, no grime at the kerb line)? Fix the worst thing, render again. Stop when further rounds stop improving it, then list honestly what still looks fake.',
  '',
  CONV,
  '',
  'Reply through the structured output: summary (at most 150 words), files (what you wrote under art/blender), previews (paths), assets (exported names), known_weaknesses (honest list).',
].join('\n')

function elPrompt(prev) {
  return [
    COMMON,
    '',
    'ROLE: senior environment artist. The pipeline library was just built by another artist. Their report: ' + (prev ? prev.summary : '(unavailable)') + (prev && prev.known_weaknesses ? ' Known weaknesses: ' + prev.known_weaknesses.join(' | ') : ''),
    'Start by reading art/blender/README.md and the library in art/blender/mi/, and looking at the previews in art/previews/. Use the library; extend it (and its README) where something is missing instead of duplicating code in your family file. If you find a bug in the library, fix it and say so.',
    '',
    'GOAL: the family art/blender/assets/el.py: one 10 m bay of the elevated train line that stands over the avenue. DESIGN.md calls it "the block\'s signature: get it right". Read src/level/el.js for the game\'s layout numbers (column rows and spacing, deck height, widths, stairs) and keep those overall dimensions (columns in two rows near y = +5 and y = -5, bents every 10 m along X, underside of the deck about 6.5 m above the road); then build the real structure those blocks stand for, the way early twentieth-century New York elevated lines are built:',
  '- Columns: built-up riveted steel sections (plates and angles, with batten plates or lacing bars), on concrete pedestals with chipped hazard-yellow paint and scuffs at bumper height, base plates with anchor bolts; old paint in many layers (dark green or black-brown), rust bleeding from rivet lines and seams, grime, stickers and tape residue at hand height.',
  '- Bents: transverse plate girders with stiffener angles and rivet rows, gusset plates and knee braces to the columns.',
  '- Longitudinal plate girders and stringers carrying an open deck: timber ties (about 200 x 250 mm, spaced about 450 mm) with daylight between them, two tracks of running rails at 1.435 m gauge with tie plates and spikes, guard rails, a third rail with its timber cover board on insulators, a steel walkway with pipe railing along one side, cable troughs and conduit.',
  '- Under the deck: conduit runs, junction boxes, and hanging street-light fixtures (emissive lens for the night rig), pigeon spikes on ledges, drip stains on the road below the joints.',
  '- Build as modular pieces with correct pivots so the level builder can repeat them along X: SM_El_Column (with pedestal), SM_El_Bent, SM_El_GirderSpan_10m, SM_El_Deck_10m (ties, rails, third rail, walkway), SM_El_Lamp. Tiling set TS_Steel_Painted_El (seamless, with the wear masks doing the local work) plus a unique baked set for the column (the player takes cover behind it: 512 px/m or better).',
  '- Assemble a look-dev scene: three bays of the El over 30 m of the street family (reuse art/blender/assets/street.py), so the avenue is striped with hard light and shadow by day.',
  '- Previews in art/previews/: el_day_hero.jpg (eye level on the sidewalk looking along the avenue under the structure), el_day_column.jpg (close view of a column and pedestal at eye level), el_day_under.jpg (looking up at the bent, girders and deck with sky between the ties), el_night_hero.jpg (night rig, lamps on), el_top.jpg (orthographic), el_wire.jpg (clay or wireframe view proving the modelled detail).',
  '- Export everything, update the manifest, run the export validation.',
  '',
  'Self-review at least three rounds on el_day_hero.jpg and el_day_column.jpg against real photographs of New York elevated structures: are the rivets the right size and spacing (about 22 mm heads at 75 to 150 mm pitch), do plates have thickness, does paint look layered and chipped rather than noisy, does rust start where water sits, are shadows crisp? Fix the worst thing each round. List honestly what still looks fake.',
    '',
    CONV,
    '',
    'Reply through the structured output: summary (at most 150 words), files, previews, assets, known_weaknesses.',
  ].join('\n')
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string' },
    realism_score: { type: 'number' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string' },
          area: { type: 'string' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['severity', 'area', 'problem', 'fix'],
      },
    },
  },
  required: ['verdict', 'realism_score', 'findings'],
}

function reviewPrompt(a, b) {
  return [
    COMMON,
    '',
    'ROLE: art director and pipeline reviewer with no stake in the work. Two artists built a Blender pipeline library and two exemplar families (a street section and one bay of the elevated line). You did not build any of it. Your job is to find what keeps it from being photoreal and what will hurt the ten artists who must use this library next. Default to scepticism: if a render merely looks "good for procedural", that is a finding.',
    'Their reports. Foundation: ' + (a ? a.summary : '(none)') + ' Weaknesses they admit: ' + (a && a.known_weaknesses ? a.known_weaknesses.join(' | ') : 'none listed') + '. El: ' + (b ? b.summary : '(none)') + ' Weaknesses they admit: ' + (b && b.known_weaknesses ? b.known_weaknesses.join(' | ') : 'none listed') + '.',
    'Do:',
    '1. Open EVERY image in art/previews/ with the Read tool and study it as a photograph. For each: what is the first thing that reveals it as computer-made? Check scale (bricks, aggregate, rivets, kerb height, lane widths, tie spacing), material response (roughness variation, highlights, metal versus paint), wear logic (does dirt gather where it would, does rust start where water sits), edges (bevels catching light), lighting (exposure, shadow sharpness, colour temperature by day and by night, reflections in the wet gutter), composition of the hero shots, and anything missing that a real street has.',
    '2. Render your own extra views if you doubt something (close-ups at 0.5 m, grazing light) with the library: ' + PY + ' art/blender/build.py ...',
    '3. Review the library as an API: read art/blender/README.md and art/blender/mi/*.py. Can a new artist add a family in an hour? Are the helpers correct (bevels, UV texel density, wear masks, bake, seamless tiling proof, export validation, manifest)? Run "build.py list" and a full build of both families from scratch and report anything that fails or is not reproducible. Check art/out/manifest.json against the conventions below and the exported GLB files (re-import one and compare bounds, pivot, slot names).',
    '4. Check conventions: axes, pivots, names, texture packing, albedo ranges (measure the baked base-colour textures numerically), triangle counts.',
    'Report findings ordered by impact on realism first, then pipeline risk. Each finding: severity (blocker, major, minor), area (file or preview), problem, evidence (which image or which measurement), fix (specific and actionable: what to change to what). Give a realism score from 1 (obviously computer-made) to 10 (would pass as a photograph) for the hero shots as they are.',
    '',
    CONV,
  ].join('\n')
}

function refinePrompt(review) {
  return [
    COMMON,
    '',
    'ROLE: senior technical artist. An art director reviewed the Blender pipeline library and the two exemplar families (street section, El bay). Fix what they found. Their verdict: ' + (review ? review.verdict : '(none)') + ' Realism score they gave: ' + (review ? review.realism_score : 'n/a') + ' out of 10.',
    'Findings (JSON): ' + JSON.stringify(review ? review.findings : []),
    'Start by reading art/blender/README.md, the library, both family files, and looking at every preview yourself. Work through the findings in order of severity: blockers and majors must all be fixed or explicitly refuted with evidence; minors where cheap. Prefer fixing the library (materials, masks, helpers) over patching one asset, so every later asset benefits. After each group of fixes, rebuild, re-render the affected previews (same file names) and look at them. Keep the README accurate. Re-run the full build of both families from scratch at the end, with bake, export and previews, and make sure the manifest and the seamless-tiling proofs are current.',
    'Then do two more self-review rounds of your own on street_day_hero.jpg, el_day_hero.jpg, el_day_column.jpg and the two night shots: fix the single most computer-made-looking thing each round.',
    '',
    CONV,
    '',
    'Reply through the structured output: summary (at most 200 words: what changed, finding by finding in brief), files, previews, assets, known_weaknesses (what still looks fake and what you would do next with scanned textures or more time).',
  ].join('\n')
}

function verifyPrompt(refined) {
  return [
    COMMON,
    '',
    'ROLE: second art director, fresh eyes. You have not seen this work before. Look at every image in art/previews/ (open each with the Read tool) as if a contractor had delivered them as proof that they can build a photoreal New York street for an Unreal Engine 5 game. The artist reports: ' + (refined ? refined.summary : '(none)'),
    'Judge only what you see. For the hero shots (street_day_hero, el_day_hero, el_day_column, el_day_under, the night shots): a realism score from 1 to 10 each and the first thing that gives the image away. Then list the remaining problems, ordered by impact, each with a specific fix. Check by measurement that the previews follow the size limits and that art/out/manifest.json lists every exported asset with plausible bounds. Do not fix anything yourself.',
    '',
    CONV,
  ].join('\n')
}

phase('Foundation')
const a = await agent(FOUNDATION_PROMPT, { label: 'art:foundation', phase: 'Foundation', schema: RESULT_SCHEMA })
phase('El exemplar')
const b = await agent(elPrompt(a), { label: 'art:el', phase: 'El exemplar', schema: RESULT_SCHEMA })
phase('Art direction')
const review = await agent(reviewPrompt(a, b), { label: 'review:art-director', phase: 'Art direction', schema: REVIEW_SCHEMA })
log('art director: ' + (review ? review.realism_score + '/10, ' + review.findings.length + ' findings' : 'no review'))
phase('Refine')
const refined = await agent(refinePrompt(review), { label: 'art:refine', phase: 'Refine', schema: RESULT_SCHEMA })
phase('Verify')
const verdict = await agent(verifyPrompt(refined), { label: 'review:fresh-eyes', phase: 'Verify', schema: REVIEW_SCHEMA })
return { foundation: a, el: b, review, refined, verdict }
