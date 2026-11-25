export const meta = {
  name: 'mi-guns-parts',
  description: 'Weapons round 4, second modelling lane (runs beside the first): the parts kit with the CHOPPER and NINE mounts, and the RATTLER SMG, so every gun can take attachments and six guns read apart',
  phases: [
    { title: 'Model', detail: 'parts kit with mounts (first) and the RATTLER, in parallel' },
  ],
}

const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'
const BRANCH = 'claude/tender-albattani-5q78qr'

const CONTEXT = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a first-person shooter (a three.js web game, now being REBUILT in Unreal Engine 5.9 with realistic, next-gen graphics and streamed to the owner's website by Pixel Streaming). Art is authored in Blender by Python scripts (reproducible, reviewable) and exported as GLB for Unreal. Setting: Hollis, Queens, a hot summer afternoon under a riveted steel elevated train line.

WHY THIS TASK EXISTS. The owner played the build on E3DS and wrote: "all the guns look the same and no attachments are able to be added to the guns". Both are true and documented in docs/unreal/LOADOUT.md ("Read this first" and section 6): the loadout offers CHOPPER (our own AK-pattern rifle), NINE (our own pistol) and three more rifles, SHORTY, STICK and STRETCH, which are ONE purchased-pack M4-style carbine in three handguard lengths; the SMG (RATTLER, the gun the Goons carry) has a low-detail enemy mesh and is hidden from the rack; and the CHOPPER and NINE have no mounts, so the Workbench offers them no parts ("No attachments"). The owner pays for every token and wants this fixed properly: a player must SEE, at a glance, six different guns, and the Workbench must offer real parts on every gun that has mounts.

THE STANDARD. The guns are on screen for the whole game, 25 to 60 cm from the camera on a 4K display. Match, and where you can exceed, the existing CHOPPER and NINE (look at art/previews/weapons_chopper_hero.jpg, weapons_nine_hero.jpg, weapons_chopper_fp.jpg, weapons_nine_fp.jpg first). All shapes are OUR OWN original designs in the manner of real classes of firearm: no real maker's marks, trademarks, model names, serial formats or logos; invented markings only. The streaming machine is slow (an NVIDIA RTX A4000 shared with other work, SM5 shaders, no Nanite): a gun is at most about 120,000 triangles with at most one 4K texture set (BC, N, ORM, E) plus 2K sets for parts; the parts kit shares sets.`

const PIPE = `START HERE
Read art/blender/README.md (conventions, helper reference) and the weapons sections of art/blender/PROGRESS.md; the code is art/blender/assets/weapons.py with _weapons_kit.py, _weapons_chopper.py, _weapons_nine.py, _weapons_tex.py, _weapons_check.py (the NINE and CHOPPER are built there, with the bones and sockets the Unreal import expects: copy the conventions, never change the behaviour of an existing function, never move an existing bone or socket: _weapons_check.py must keep saying ALL FIXED POINTS KEPT). The skinned-asset module is art/blender/mi/rig.py; the previews of the finished guns are in art/previews/. The design of what a gun must offer (stats, mounts, parts, sockets, the status words) is docs/unreal/LOADOUT.md sections 3.2, 3.3, 6.1 to 6.3 and 6.6 and the data files unreal/MurderInc/Content/Data/guns.json and attachments.json (read the "mounts" and "art" blocks and the compatibility table). How the first-person arms hold a gun (palms, the support hand, the camera recipe) is docs/unreal/CHARACTERS.md and docs/unreal/ANIMATION.md. How guns reach the game: tools/box/anim/ue_import_guns.py and tools/box/send-art.sh (read them: your archive must be importable the same way).

ENVIRONMENT
Python with Blender 5.3 as a module: ${PY} (import bpy; numpy and pillow installed). This container has 4 CPU cores shared by up to six agents (two more modelers of the first lane and reviewers run beside you): Cycles on CPU with at most 1 thread (bpy.context.scene.cycles / render threads = 1, numpy and OpenBLAS threads = 1 via OMP_NUM_THREADS=1), run bakes with nice -n 10, start bakes and renders in the background and poll them. Do NOT use the GPU test box and do not touch /project there: this task needs only this container. No internet except art/scans/fetch.py. Write only under art/ (and docs/unreal/PROGRESS.md, art/blender/PROGRESS.md for your notes). Look at every image you render (Read tool).

GIT
Commit your own work as you go, in small working steps (you may be cut off): git pull --no-rebase first, git add with explicit paths under art/blender/, art/previews/ and the two PROGRESS files (never git add -A: other agents have unfinished files here), git commit, git push -u origin ${BRANCH}; on index.lock wait a few seconds and retry; never force-push, never touch another branch, never open a pull request. art/out/ is git-ignored and stays so. No link, account name, email or person's name in any commit. End every commit message with exactly these two lines and put no model name anywhere else:
Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4`

const WORK = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    previews: { type: 'array', items: { type: 'string' } },
    assets: { type: 'array', items: { type: 'string' } },
    known_weaknesses: { type: 'array', items: { type: 'string' } },
    notes_for_integration: { type: 'string' },
    head_commit: { type: 'string' },
  },
  required: ['summary', 'files', 'previews', 'assets', 'known_weaknesses', 'notes_for_integration', 'head_commit'],
}

const spec = 'THE FILE docs/unreal/weapons_r4_spec.json IN THE REPOSITORY (JSON: guns, parts, existing_guns_changes, data_changes, order, risks): read it in full before anything else'

const JOBS = [
  { key: 'rattler', title: 'RATTLER (SMG)', gun: 'rattler' },
]

const LANE = `
LANE 2 (YOU ARE THE SECOND MODELLING LANE). The owner's top priority right now is: distinct guns AND attachments that really fit. Lane 1 (another workflow, running since 11:36 UTC) models SHORTY and STRETCH; its files are weapons_shorty.py, _weapons_shorty*.py, weapons_stretch.py, _weapons_stretch*.py, _weapons_check_stretch.py: NEVER edit them. You build what lane 1 was going to build last: the PARTS KIT with the CHOPPER and NINE mounts (files weapons_parts.py, _weapons_patch.py, _weapons_check_parts.py) and the RATTLER (weapons_rattler.py, _weapons_rattler*.py, _weapons_check_rattler.py). The designer's specification is the JSON FILE docs/unreal/weapons_r4_spec.json in the repository: read it in full first (its "order" list gives the sequence and the numbers; follow its sections C and N for the CHOPPER and NINE patch, its parts table and its contract). The README at the top of art/blender/ says who builds what: add one line to the README's lane note when you finish (what exists, commit ids). Commit each finished, validated step at once (a working export is worth committing alone) because the Unreal integration engineer will start from whatever is committed: small commits with explicit paths, git pull --no-rebase before every push. Time matters (the owner is waiting): choose the fastest route that still meets the standard; draft bakes at 512 or 1024 to judge, one final bake per set.
`

const gunPrompt = (j) => `${CONTEXT}${LANE}

${PIPE}

YOU ARE THE MODELER OF ${j.title} (lane 2). The designer's specification (JSON; follow it, and where it is silent follow the CHOPPER's and NINE's conventions): ${JSON.stringify(spec)}

Build the gun "${j.gun}" as a new family file art/blender/assets/weapons_${j.gun}.py (add it to the family registry the same way the NINE and CHOPPER are registered; read how build.py finds families), in the same way and to the same finish as the CHOPPER and NINE:
- Geometry: the full mechanical detail of its real class, modelled (pins with heads, screws with slots, stamped ribs, weld seams, sight ears, serrations, vents with the barrel or bolt visible inside, a bored and crowned barrel, a hollow magazine well, magazines with feed lips, follower and top round, the ejection port with what lies behind it, sling points, grip texture as normal detail), every edge bevelled at its real radius with weighted normals. Within the triangle budget of the specification. At 30 cm in first person it must show no faceting or flat unmodelled areas.
- Rig: ONE skinned GLB; the bones are the rigid moving parts, every vertex weighted 1.0 to exactly one bone, rest orientation equal to the gun's axes (translation along local X is travel along the bore), socket bones without vertices named exactly as the specification says; use art/blender/mi/rig.py. Magazines are separate meshes with an attach bone, like the CHOPPER's.
- Textures: unique baked sets (4K for the gun, 2K for its magazine), BC, N (OpenGL), ORM, E where there are lit parts. Layered believable wear driven by edge, curvature and AO masks, handling wear where hands rub, oil sheen, scratches along the direction of handling; the finish of the specification (it must differ from the other guns). Uniform texel density, no visible seams on flat faces. Bake CPU, at most 1 thread (nice -n 10), in the background.
- Proof: the pipeline's export validation; import the exported GLB into a fresh scene and pose every bone (bolt back, trigger pulled, magazine rocked out...) to prove pivots and weights; a socket-positions report like _weapons_check.py makes for the CHOPPER and NINE (add your gun to a check script of your own, art/blender/assets/_weapons_check_${j.gun}.py).
- Previews in art/previews/ (1280 x 720, at most 300 kB each, look at each, at most 8 renders, two self-review rounds fixing the worst visible fault each round): weapons_${j.gun}_hero.jpg (three-quarter, studio HDRI), weapons_${j.gun}_fp.jpg (through a first-person camera with the same vertical field of view and viewmodel pose the CHOPPER's fp preview uses), weapons_${j.gun}_side.jpg (a flat orthographic left side view on a plain background: this is what a player's eye reads first), weapons_${j.gun}_parts.jpg (posed open, magazine beside it), and the white-on-transparent 512 x 192 side silhouette art/out/ui/T_UI_Gun_${j.gun[0].toUpperCase() + j.gun.slice(1)}.png (not committed).
Another agent builds the parts kit and the CHOPPER/NINE mounts at the same time (art/blender/assets/weapons_parts.py): do not edit its files; your gun's mount sockets (Optic, MuzzleMount, Underbarrel, Laser per the specification) must sit on real rails and threads you modelled.
Add your section to art/blender/PROGRESS.md and your row to the README's family table; commit and push in working steps.
Return through the structured output: summary (at most 150 words), files, previews, assets (exported names with triangle counts and texture sizes), known_weaknesses (honest, most visible first), notes_for_integration (bones, sockets, GLB and texture names, what the Unreal import must do), head_commit.`

const partsPrompt = `${CONTEXT}${LANE}

${PIPE}

YOU ARE THE PARTS MODELER (lane 2). PRIORITY ORDER: (a) the sockets and mount geometry on the CHOPPER and NINE and their re-export first (it alone lets the Workbench offer parts on both), (b) then the parts in the order of the specification's step 2, committing each part's validated GLB as soon as it passes, (c) assembly checks and previews last. The designer's specification (JSON; follow it, and where it is silent follow the CHOPPER's and NINE's conventions): ${JSON.stringify(spec)}

Two jobs, in this order.
1. The mounts on the EXISTING guns. In the CHOPPER's and NINE's Blender code add, without moving any existing point (art/blender/assets/_weapons_check.py must still say ALL FIXED POINTS KEPT), the model detail the mounts need and the sockets the specification names: on the CHOPPER a short top-cover rail (or a side rail) for an optic, a threaded muzzle for a suppressor, a handguard rail for an underbarrel grip, a side rail for a laser; on the NINE a rail under the frame for a laser and a threaded barrel end for a suppressor. Add the mount geometry as part of the gun's own meshes where it belongs to the gun (a rail IS part of the gun, so the gun's GLB changes: keep triangle counts within +10 %), and re-export both guns through the existing export path. Put your code in art/blender/assets/weapons_parts.py (a new family) as functions the existing files do not need to change for, or, where a change to _weapons_chopper.py or _weapons_nine.py is unavoidable, add the mount functions at the end and call them from the end of the build, leaving every earlier line as it is.
2. The parts kit, our own universal parts, built once at the origin of their mount (the specification names each part's socket and dimensions): a compact red dot sight and a 4x scope (lens slots, SightEye sockets), a long suppressor (Muzzle socket at its far end) and a compensator, a vertical grip and an angled grip (SupportHand sockets), a red laser module (Beam socket), and the extended magazines the specification lists. Real-looking and detailed (these are seen at 30 cm): modelled threads, clamp screws, rail clamps, lens rings, knurling; baked unique 2K sets (parts share sets where they share a material); every part exports as its own GLB (SM_Part_<Id>) with its mount origin at the file origin and the socket names the specification gives, validated by the pipeline's export step.
Proof: pose-check by assembling each part on the gun it belongs to in a fresh scene (the CHOPPER with scope + suppressor + vertical grip + laser; the NINE with laser + suppressor + extended magazine; and the three new guns once their files exist: check art/blender/assets for weapons_shorty.py, weapons_stretch.py, weapons_rattler.py and use them when present; if not yet, do those assemblies last, waiting and re-checking) and render assembly previews in art/previews/: weapons_parts_kit.jpg (all parts on a plain background, labelled by position), weapons_chopper_built.jpg and weapons_nine_built.jpg (the guns fully built, three-quarter view), at most 8 renders, two self-review rounds. A part that floats off its rail or intersects the gun is a fault to fix.
Add your section to art/blender/PROGRESS.md and rows to the README family table; commit and push in working steps.
Return through the structured output: summary (at most 150 words), files, previews, assets (exported names with triangle counts and texture sizes), known_weaknesses, notes_for_integration (every socket by name and position per gun and per part, the compatibility table changes needed in attachments.json, what the Unreal import must do), head_commit.`


phase('Model')
const built = await parallel([
  () => agent(partsPrompt, { label: 'lane2:parts', phase: 'Model', schema: WORK }),
  ...JOBS.map(j => () => agent(gunPrompt(j), { label: 'lane2:' + j.key, phase: 'Model', schema: WORK })),
])
const results = built.map((r, i) => ({ key: i === 0 ? 'parts' : JOBS[i - 1].key, result: r }))
log('lane 2 modelled: ' + results.filter(r => r.result).map(r => r.key).join(', ') + '; missing: ' + (results.filter(r => !r.result).map(r => r.key).join(', ') || 'none'))
return { results }
