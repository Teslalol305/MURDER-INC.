export const meta = {
  name: 'mi-art-props-signs',
  description: 'Blender art, three steps in sequence: scanned and gameplay props, street furniture and yard structures, storefront signage',
  phases: [
    { title: 'Props', detail: 'convert the scanned prop models, build reel case, welding rack, explosives' },
    { title: 'Furniture', detail: 'street furniture and yard structures' },
    { title: 'Signage', detail: 'storefront signs, IPX billboard and mural artwork' },
  ],
}

const REPO = '/home/user/MURDER-INC.'
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'

const COMMON = [
  'PROJECT CONTEXT',
  REPO + ' holds "MURDER INC.", a browser first-person shooter owned by the user that is being REBUILT in Unreal Engine 5.9 with photoreal graphics. Art is authored in Blender by Python scripts and exported as GLB for Unreal. Setting: Hollis, Queens: Jamaica Avenue under a riveted steel elevated train line, a hot clear summer afternoon by default. No real brands, no real people; every shop name and livery is invented (the only real mark is the client\'s own: "IPX" and "IPX.EXCHANGE", no slogan).',
  'The user pays for every token: work efficiently, read selectively, do not polish beyond the task. Final look development happens later in Unreal; Blender renders are sanity checks. What matters: correct, detailed, well-UV-mapped geometry at real-world size with sensible material slots, exported and validated.',
  '',
  'START HERE: read art/blender/README.md and art/blender/PROGRESS.md (the pipeline: library art/blender/mi/, command line art/blender/build.py, families in art/blender/assets/: street.py, el.py, facade.py; scan-backed materials from the catalogue art/scans/sets.json with textures in art/out/textures/; scanned prop models under art/out/scans/models/<slug>/; HDRI day rig). Look at art/previews/facade_day_hero.jpg for the current state. Follow the README conventions exactly (axes, pivots, names, tiling sets with world-scale UVs and vertex-colour wear masks, unique baked sets for hero props, outputs, manifest).',
  'What each thing is, its size, colours and collision come from docs/unreal/spec/05b-props.md (the prop catalogue, with dimensions per id) and the briefs in docs/unreal/spec/assets/props.json and level.json; the quality bar is docs/unreal/ART_BIBLE.md. Read the parts you need, not whole documents.',
  '',
  'ENVIRONMENT: Python with Blender 5.3.0 as a module: ' + PY + ' (import bpy; numpy and pillow installed). CPU only, 4 shared cores: Cycles on CPU with 3 threads, renders at most 1280x720 and 64 samples, at most 6 renders in total. Check the running bpy module instead of trusting memory. No internet except art/scans/fetch.py for catalogued Poly Haven files. Write only under art/. Do not commit or push. Look at every image you render. You may be cut off without warning: keep art/blender/PROGRESS.md current (what is done, the exact next step) and leave files runnable after each step.',
].join('\n')

const REPLY = 'Reply through the structured output: summary (at most 150 words), files, previews, assets (exported SM_ names with triangle counts; group similar ones), known_weaknesses (honest, most visible first).'

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

const PROPS = [
  COMMON, '',
  'YOUR TASK: the family art/blender/assets/props.py.',
  '1. Scanned props. The 40 scanned models in art/out/scans/models/ (listed in art/scans/sets.json with their real dimensions) are photoscanned, CC0, with their own 2k textures. Import each one that the game can use, bring it to the conventions (real-world size checked against the catalogue, pivot at the centre of the footprint on the ground, forward +X, transforms applied, one unique material slot M_<Asset> keeping its scanned textures as T_<Asset>_BC/N/ORM), name it after the catalogue id it stands for where one fits (fire hydrant, jersey barrier, barrels and drums, trash can, tool chest, shelf racks, crates and cardboard boxes, street lamp, utility box, payphone, bench, plastic chair, old tyre, coffee cart as the food cart base, propane tank, boombox, security camera, fire extinguisher, crowbar and bat as loose props), and export SM_Prop_<Name>.glb with a manifest entry (collision hint and cover height from the catalogue). Say which catalogue ids are now covered and which are not.',
  '2. Gameplay props, modelled by you at hero quality with unique baked sets: the master reel case (a road case holding a two-inch tape reel, with the IPX tracker tag; three numbered variants 1, 2, 3 as the catalogue describes), the welding rack (the explosive: two gas cylinders chained to a hand cart with regulators and hoses), the propane tank variants the level uses if the scanned tank does not fit the catalogue size, and the resupply crate if the catalogue has one.',
  '3. One preview sheet per group (props_scanned.jpg, props_gameplay.jpg): everything on a ground plane at real size next to a 1.8 m scale box, lit by the day rig. Export, update the manifest, run the export validation, add the family to the README.',
  '', REPLY,
].join('\n')

const FURNITURE = [
  COMMON, '',
  'YOUR TASK: the family art/blender/assets/furniture.py: every street-furniture and yard item of the catalogue that is not yet covered (art/blender/PROGRESS.md and art/out/manifest.json say what exists; the props family before you covered the scanned models and the gameplay props). Build, at real size, on tiling scan sets with wear masks (unique baked sets only where a tiling set cannot work):',
  '- Street: dumpster (two sizes if the catalogue has them), mailbox, newspaper box, traffic barrel and cone, jersey barrier if no scanned one fits, bus shelter with an advertising panel slot (M_Sign_BusShelter, 0..1 UVs), trash-bag pile, milk-crate stack, pallet, sandbag row, oil drum, tyre stack, shopping cart, mattress, parking meter or sign posts if the catalogue lists them.',
  '- Structures: the construction sidewalk shed (steel scaffold with plywood deck, parapet and stair, per the level spec), chain-link fence panel, post and gate in the heights the level uses (alpha-tested mesh card on a real pipe frame), the basketball court set (hoop with backboard and pole, bleacher), the parking attendant booth, a light pole for the lot, the billboard steel frame with its panel slot (M_Sign_Billboard), a roll-up garage door and the cinder-block wall module for the auto body shop with its lintel and steel door.',
  '- Preview sheets (furniture_street.jpg, furniture_structures.jpg) at real size next to a 1.8 m scale box. Export, update the manifest, run the export validation, add the family to the README, and list which catalogue ids are still not covered after your run (vehicles are a separate job: do not build vehicles).',
  '', REPLY,
].join('\n')

const SIGNS = [
  COMMON, '',
  'YOUR TASK: signage. The facade kit left named sign slots without artwork (M_Sign_<Shop> on the SM_Facade_SignBand_* modules, 0..1 UVs), and the furniture family left M_Sign_BusShelter and M_Sign_Billboard. docs/unreal/spec/06-look-fx.md lists every sign, poster, the mural and the billboard verbatim with palettes, sizes and positions (search for the signage section); docs/unreal/ART_BIBLE.md section 5 says how each should be built as a real sign type.',
  '1. art/blender/assets/signs.py: for each of the ten storefronts produce the sign as its real type: internally lit box sign with a printed face, painted fascia, or channel letters as geometry, following the bible; lettering exactly as the spec gives it. Use fonts that are available on this machine (list them with fc-list; pick a heavy grotesque and a condensed face, and say which); render flat sign faces to textures T_Sign_<Shop>_BC (and _E for lit faces) with pillow or Blender, at a resolution that holds up at 3 m, with believable sign-shop design (borders, phone-number style details invented and obviously fictional, slight sun fade), and model channel letters as bevelled geometry where the bible asks for them.',
  '2. The IPX billboard artwork, the bus-shelter IPX advertisement and the mural on the pawn shop side wall ("IPX" wordmark and "RULE", painted-wall look with brick showing through), as the spec describes them. Only "IPX" and "IPX.EXCHANGE" as brand text, no slogan.',
  '3. Wire the textures into the sign slots of the existing modules (re-export what changes), render signs_sheet.jpg (all ten shop signs side by side at the same scale) and signs_street.jpg (the sample block face from the facade family with its signs on), update the manifest and README, run the export validation.',
  '', REPLY,
].join('\n')

phase('Props')
const a = await agent(PROPS, { label: 'art:props', phase: 'Props', schema: SCHEMA, effort: 'high', model: 'opus' })
phase('Furniture')
const b = await agent(FURNITURE, { label: 'art:furniture', phase: 'Furniture', schema: SCHEMA, effort: 'high', model: 'opus' })
phase('Signage')
const c = await agent(SIGNS, { label: 'art:signs', phase: 'Signage', schema: SCHEMA, effort: 'high', model: 'opus' })
return { props: a, furniture: b, signs: c }
