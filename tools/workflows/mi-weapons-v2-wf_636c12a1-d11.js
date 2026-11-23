export const meta = {
  name: 'mi-weapons-v2',
  description: 'Hero guns second pass: an independent critic judges the CHOPPER and the NINE against real weapons of their class, an artist rebuilds form and surface, repeated until both pass or three rounds are used',
  phases: [
    { title: 'Critique', detail: 'fresh turnaround and first-person renders of the exported guns, fault list with grades' },
    { title: 'Rebuild', detail: 'form, detail and surface rebuilt against the fault list, re-exported and verified' },
  ],
}
const RESUME = `

RESTART NOTE (newer than everything above): an earlier run of this exact task was cut off partway through by a restart of the local machine, not by any fault of the work. Its files are on disk and its commits are on the branch (uncommitted files were committed afterwards as work in progress); your section of the progress notes (art/blender/PROGRESS.md or docs/unreal/PROGRESS.md), git log and the files themselves show how far it got. Local background processes it started are gone and local renders or bakes that were running must be started again; on the GPU box, look at what is still running under your own project before you start anything, and remember the box may have stopped while idle (follow the box-gone procedure if so). Review and continue from where it stopped; do not start over, and do not repeat generation or downloads whose results are already on disk.`
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'
const HEAD = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a browser first-person shooter owned by the user that is being REBUILT in Unreal Engine 5.9 with photoreal graphics. Art is authored in Blender by Python scripts and exported as GLB. The user's standing instruction: the guns must look realistic with very detailed textures; the whole game has to feel next-gen. The two player guns are on screen for the whole game, 25 to 60 cm from the camera on a 4K display: they are the most looked-at assets in the game.
The guns: the CHOPPER (a short Kalashnikov-pattern carbine with laminated wood furniture, an under-folding stock and a curved magazine) and the NINE (a full-size hammer-fired 9 mm service pistol, stainless slide over a black frame, gold trigger and magazine base pad), with their magazines. Briefs: docs/unreal/spec/assets/weapons.json (weapon_chopper, weapon_chopper_magazine, weapon_nine, weapon_nine_magazine). The numbers in the briefs were measured from the web game's blocky models. FIXED, because gameplay, sights and animation are built on them: the origin and axes, overall length and height, the bore axis, the sight line (SightRear, SightFront heights and positions), every socket (Muzzle, Eject, RecoilPivot, MagHinge, Palm_R, Palm_L), every pivot and travel distance of the moving parts, the bone names, the left-side charging handle of the CHOPPER, the colours. FREE, and to be made like the real class of weapon: every outline, cross-section, curvature, chamfer and detail between those fixed points. No maker's marks, real trademarks or real serial formats.
State: a first pass exists (art/blender/assets/weapons.py with the library modules art/blender/mi/rig.py for skinned export with a re-import check and mi/texpaint.py for textures painted from baked geometry maps; exported GLBs art/out/glb/SK_Chopper.glb, SK_Nine.glb and the magazines, 4K sets under art/out/textures/; previews art/previews/weapons_*.jpg; notes in art/blender/PROGRESS.md and README.md). Its own author judged it below AAA: the NINE's grip is a flat slab and its frame is boxy, the CHOPPER's handguards and sight block are prisms, wear is procedural and even.
Python with Blender 5.3.0 as a module: ` + PY + ` (import bpy). 4 CPU cores shared with other agents: Cycles on CPU with at most 3 threads, long jobs in the background and polled. Look at every image you render (Read tool). Other agents work in this checkout (characters, vehicles, structures, Unreal): never edit their files; add to art/blender/mi/ without changing the behaviour of existing functions (the Buzzard and the characters use rig.py and texpaint.py).`
const GIT = `GIT
Commit your own work in small steps (you may be cut off without warning): git add with explicit paths under art/blender/ and art/previews/ (never git add -A), commit, git push -u origin claude/tender-albattani-5q78qr; on index.lock wait and retry; never force-push, never another branch, never a pull request. End every commit message with exactly these two lines and put no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4
Keep your own section of art/blender/PROGRESS.md current (append; never rewrite the file).`

const critic = (round) => HEAD + `

ROLE: an independent art director for first-person weapons who did not build these guns. This is critique round ` + round + `. Do not edit weapons.py and do not re-export anything.
Render the guns as they are exported NOW (import the GLBs with their textures into a fresh scene; your own small script under art/blender/review/): for each gun a left side, right side, top, three-quarter front and three-quarter rear on a neutral studio HDRI, and the first-person view (camera at the eye, gun at the viewmodel pose and vertical field of view of docs/unreal/spec/02-weapons-combat.md, search "viewmodel", hip and aimed), 1280 x 720, modest samples: at most 14 renders. Then judge each gun as you would judge a hero weapon for a current AAA shooter, part by part, against how real weapons of this class are actually shaped and made: silhouette and proportions; every cross-section (is anything a plain box or prism where the real part is forged, stamped, machined or moulded into curves?); the grip in the hand (palm swell, back strap and front strap curvature, beavertail, undercut trigger guard, grip panel shape and checkering); slide and receiver machining (flats, radii, serration depth and spacing, ejection port, rails); furniture (handguard taper, finger swell, vents, ferrules, laminate); sights; controls; the muzzle; pins, rivets, screws and welds; bevel quality and shading; texture quality at 30 cm (material definition, wear logic, scratches, oil, dust, colour and roughness variation, anything that reads flat, uniform, noisy or procedural); and whether anything FIXED by the brief was broken (measure the sockets, sight heights, overall size and part travels in the GLB).
Grade each gun from 1 (placeholder) to 5 (ships in an AAA game). Reply through the structured output: for each gun its grade and its faults, most visible first, each with the part, what is wrong and a concrete instruction for the modeller (shape language, dimensions or radii, what to model and how it should catch light); broken_fixed_points (empty if none); renders (paths); verdict (at most 100 words).`
const CRIT_SCHEMA = { type: 'object', properties: { guns: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, grade: { type: 'number' }, faults: { type: 'array', items: { type: 'object', properties: { part: { type: 'string' }, wrong: { type: 'string' }, instruction: { type: 'string' } }, required: ['part', 'wrong', 'instruction'] } } }, required: ['name', 'grade', 'faults'] } }, broken_fixed_points: { type: 'array', items: { type: 'string' } }, renders: { type: 'array', items: { type: 'string' } }, verdict: { type: 'string' } }, required: ['guns', 'verdict'] }

const builder = (round, crit) => HEAD + '\n\n' + GIT + `

ROLE: senior weapon artist. This is rebuild round ` + round + `. An independent art director judged the exported guns; their renders are under art/blender/review/. THE CRITIQUE:
` + JSON.stringify(crit.guns, null, 1) + `
Fixed points reported broken: ` + JSON.stringify(crit.broken_fixed_points || []) + `
Verdict: ` + crit.verdict + `

YOUR TASK: rebuild what the critique names, most visible faults first, the lower-graded gun first. This is a form and surface pass, not a patch: where a part is a box or a prism, replace its construction (lofted cross-sections, subdivision surfaces with supporting loops, boolean cuts with clean bevels, curve-swept parts) so it has the curvature and machining of the real class of weapon; keep every FIXED point exactly and prove it. Keep the rig contract (bone names, rigid weights, socket bones, bone axes equal to gun axes) and the re-import pose check of mi/rig.py passing. Raise the texture work with the shapes: material definition per part (blued, parkerised, stainless brushed along the machining direction, polished, cast, laminated wood with ply lines following the form, moulded polymer or rubber with real checkering depth in the normal map), wear that follows use (holster and hand contact, edges, the path of the bolt handle and the slide stop, magazine insertion marks, carbon), fine detail that survives a 4K display at 30 cm. Stay within about 150,000 triangles for the CHOPPER and 90,000 for the NINE; 4K sets as before.
Then re-export everything that changed through the pipeline's validation, and render final previews AFTER the last change (1280 x 720, at most 300 kB each, at most 10 renders): weapons_chopper_hero.jpg, weapons_chopper_fp.jpg, weapons_nine_hero.jpg, weapons_nine_fp.jpg, weapons_parts.jpg (bolt back, magazine out, slide locked), weapons_wire.jpg.

Reply through the structured output: summary (at most 150 words), changed (part: what was rebuilt and how), not_done (what remains and why), fixed_points_verified (how you proved them), previews.`
const BUILD_SCHEMA = { type: 'object', properties: { summary: { type: 'string' }, changed: { type: 'array', items: { type: 'string' } }, not_done: { type: 'array', items: { type: 'string' } }, fixed_points_verified: { type: 'string' }, previews: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'changed', 'not_done', 'previews'] }

const history = []
let last = null
for (let round = 1; round <= 3; round++) {
  const crit = await agent(critic(round), { label: 'weapons:critic-' + round, phase: 'Critique', schema: CRIT_SCHEMA, effort: 'high', model: 'opus' })
  if (!crit) { log('critic ' + round + ' returned nothing'); break }
  last = crit
  log('round ' + round + ': ' + crit.guns.map(g => g.name + ' ' + g.grade).join(', '))
  const pass = crit.guns.length > 0 && crit.guns.every(g => g.grade >= 4) && !(crit.broken_fixed_points || []).length
  history.push({ round, grades: crit.guns.map(g => ({ name: g.name, grade: g.grade })), verdict: crit.verdict })
  if (pass) break
  const built = await agent(builder(round, crit) + RESUME, { label: 'weapons:rebuild-' + round, phase: 'Rebuild', schema: BUILD_SCHEMA, effort: 'high', model: 'opus' })
  history[history.length - 1].rebuild = built
  if (round === 3) {
    const fin = await agent(critic(4), { label: 'weapons:critic-final', phase: 'Critique', schema: CRIT_SCHEMA, effort: 'high', model: 'opus' })
    if (fin) { last = fin; history.push({ round: 4, grades: fin.guns.map(g => ({ name: g.name, grade: g.grade })), verdict: fin.verdict }) }
  }
}
return { history, final_critique: last }
