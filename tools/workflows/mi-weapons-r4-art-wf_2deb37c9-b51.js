export const meta = {
  name: 'mi-weapons-r4-art',
  description: 'Blender: three new guns with their own silhouettes (compact bullpup SHORTY, marksman rifle STRETCH, SMG RATTLER), a parts kit and mount sockets so the CHOPPER and NINE take attachments; reviewed for distinctness and budget',
  phases: [
    { title: 'Audit', detail: 'what exists, what each gun must be, the parts and mounts: one spec' },
    { title: 'Model', detail: 'three guns and the parts kit (with the CHOPPER and NINE mounts), in parallel' },
    { title: 'Review', detail: 'silhouette distinctness, realism, rig, budget, export' },
    { title: 'Fix', detail: 'what the review found' },
    { title: 'Deliver', detail: 'archive for the box, hand-off spec for the Unreal integration, docs' },
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
Python with Blender 5.3 as a module: ${PY} (import bpy; numpy and pillow installed). This container has 4 CPU cores shared by up to four agents: Cycles on CPU with at most 2 threads; start bakes and renders in the background and poll them. Do NOT use the GPU test box and do not touch /project there: this task needs only this container. No internet except art/scans/fetch.py. Write only under art/ (and docs/unreal/PROGRESS.md, art/blender/PROGRESS.md for your notes). Look at every image you render (Read tool).

GIT
Commit your own work as you go, in small working steps (you may be cut off): git pull --no-rebase first, git add with explicit paths under art/blender/, art/previews/ and the two PROGRESS files (never git add -A: other agents have unfinished files here), git commit, git push -u origin ${BRANCH}; on index.lock wait a few seconds and retry; never force-push, never touch another branch, never open a pull request. art/out/ is git-ignored and stays so. No link, account name, email or person's name in any commit. End every commit message with exactly these two lines and put no model name anywhere else:
Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4`

const SPEC = {
  type: 'object',
  properties: {
    guns: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, class: { type: 'string' }, silhouette: { type: 'string' }, design: { type: 'string' },
      length_mm: { type: 'number' }, height_mm: { type: 'number' }, width_mm: { type: 'number' },
      moving_parts: { type: 'array', items: { type: 'string' } },
      bones: { type: 'array', items: { type: 'string' } }, sockets: { type: 'array', items: { type: 'string' } },
      triangle_budget: { type: 'number' }, textures: { type: 'string' }, finish: { type: 'string' },
    }, required: ['id', 'class', 'silhouette', 'design', 'length_mm', 'moving_parts', 'bones', 'sockets', 'triangle_budget', 'textures', 'finish'] } },
    parts: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, slot: { type: 'string' }, applies_to: { type: 'array', items: { type: 'string' } },
      socket: { type: 'string' }, design: { type: 'string' }, dims_mm: { type: 'string' }, effect_note: { type: 'string' },
    }, required: ['id', 'slot', 'applies_to', 'socket', 'design', 'dims_mm'] } },
    existing_guns_changes: { type: 'string' },
    data_changes: { type: 'string' },
    order: { type: 'array', items: { type: 'string' } },
    risks: { type: 'string' },
  },
  required: ['guns', 'parts', 'existing_guns_changes', 'data_changes', 'order', 'risks'],
}

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

const REVIEW = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
      where: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' },
    }, required: ['title', 'severity', 'where', 'evidence', 'fix'] } },
    checked_ok: { type: 'array', items: { type: 'string' } },
    grade: { type: 'string' },
  },
  required: ['findings', 'checked_ok', 'grade'],
}

phase('Audit')
const spec = await agent(`${CONTEXT}

${PIPE}

YOU ARE THE WEAPONS DESIGNER AND AUDITOR. About 40 minutes. Do not model anything yet: read, look at the finished guns' previews and the Blender code, and write the specification the modelers will build from.

1. AUDIT what exists: the CHOPPER and NINE (bones, sockets, triangle counts, texture sets: read the manifest entries in art/out/manifest.json if present, else the code), the six roles of a gun in guns.json (ready gates, mounts, art status), the parts and the per-gun compatibility in attachments.json, what the pack rifle (STICK) looks like in docs/unreal/LOADOUT.md (an M4-style carbine; it stays as it is and is not ours to model), and what 6.6 asks of the weapons pipeline (sockets Optic and MuzzleMount and a separate Booster on the CHOPPER; Laser on the NINE; a white-on-transparent 512 x 192 side silhouette per gun for the rack, wheel and bar).

2. DESIGN the three new guns so that, with the CHOPPER (AK pattern: long fixed stock, curved magazine), the NINE (pistol) and the pack carbine STICK (M4 pattern, stays), the six are unmistakable from the side at thumbnail size AND in first person: SHORTY (replaces the pack's short-handguard rifle in the rack: a compact bullpup carbine, magazine behind the grip, short and blocky, a forward ejection-side shell deflector, an integrated top carry handle with a short rail), STRETCH (replaces the extended-handguard rifle: a long marksman rifle, a free-floating long barrel with a muzzle brake, a fixed stock with a cheek riser, a bipod folded under the handguard, a 10-round box magazine, a long top rail; heavy and steady), RATTLER (the SMG the Goons carry, now a first-person-grade gun: compact open-bolt submachine gun with a ventilated shroud, a side-folded wire stock, a long stick magazine ahead of the grip, a top charging handle). Keep each gun's gameplay numbers' intent (guns.json "derivation" text says what each is for). For each give real-world proportions in mm, the moving parts (bolt or slide, charging handle, selector, trigger, magazine, bipod legs if any), bones and sockets by the NAMES the CHOPPER and NINE use (read them; add the mount sockets Optic, MuzzleMount, Underbarrel, Laser, MagHinge where the compatibility table gives the gun a slot; Palm_R, Palm_L where the arms hold it: coordinate with docs/unreal/CHARACTERS.md and the CHOPPER's palm placement so the existing arm rig can hold the gun with IK), triangle budget, texture sizes and a finish (colours and wear: each gun a different material story so that colour and finish also tell them apart: for example an olive polymer and parkerised steel bullpup, a dark wood and blued steel marksman rifle, a grey stamped steel SMG with a tan strap).

3. DESIGN the parts kit: OUR OWN universal parts, shared by the guns: optics (a compact red dot and a 4x scope, each with a lens material slot and a SightEye socket), muzzle devices (a long suppressor with Muzzle at its far end, a compensator), underbarrel (a vertical grip and an angled grip, each with SupportHand), laser (a red laser module with Beam), magazines (an extended magazine per gun class: rifle, SMG, pistol), with mount adapters so one part sits on each gun's own rail or thread (a part is built once at the origin of its socket: the gun carries the socket, the part has a matching "Mount" origin). Say per gun and slot which parts apply, consistent with attachments.json (propose the changes to the compatibility table you need; the Unreal integration engineer applies them). The CHOPPER takes a scope and a suppressor (+ optional red dot on a side rail, vertical grip), the NINE a laser and a suppressor (threaded barrel) and an extended magazine.

4. The existing guns: list exactly what must be ADDED to the CHOPPER's and NINE's Blender code to give them the mount sockets (positions measured on the existing meshes, never moving an existing point), and the booster split of the CHOPPER if the data needs it.

5. ORDER of work and RISKS (CPU budget: 4 shared cores; Cycles bakes are slow: say what to bake at what size).

Return the specification (structured). Be concrete: numbers, names, sockets.`, { label: 'audit', phase: 'Audit', schema: SPEC })

const JOBS = [
  { key: 'shorty', title: 'SHORTY (compact bullpup carbine)', gun: 'shorty' },
  { key: 'stretch', title: 'STRETCH (marksman rifle)', gun: 'stretch' },
  { key: 'rattler', title: 'RATTLER (SMG)', gun: 'rattler' },
]

const gunPrompt = (j) => `${CONTEXT}

${PIPE}

YOU ARE THE MODELER OF ${j.title}. The designer's specification (JSON; follow it, and where it is silent follow the CHOPPER's and NINE's conventions): ${JSON.stringify(spec)}

Build the gun "${j.gun}" as a new family file art/blender/assets/weapons_${j.gun}.py (add it to the family registry the same way the NINE and CHOPPER are registered; read how build.py finds families), in the same way and to the same finish as the CHOPPER and NINE:
- Geometry: the full mechanical detail of its real class, modelled (pins with heads, screws with slots, stamped ribs, weld seams, sight ears, serrations, vents with the barrel or bolt visible inside, a bored and crowned barrel, a hollow magazine well, magazines with feed lips, follower and top round, the ejection port with what lies behind it, sling points, grip texture as normal detail), every edge bevelled at its real radius with weighted normals. Within the triangle budget of the specification. At 30 cm in first person it must show no faceting or flat unmodelled areas.
- Rig: ONE skinned GLB; the bones are the rigid moving parts, every vertex weighted 1.0 to exactly one bone, rest orientation equal to the gun's axes (translation along local X is travel along the bore), socket bones without vertices named exactly as the specification says; use art/blender/mi/rig.py. Magazines are separate meshes with an attach bone, like the CHOPPER's.
- Textures: unique baked sets (4K for the gun, 2K for its magazine), BC, N (OpenGL), ORM, E where there are lit parts. Layered believable wear driven by edge, curvature and AO masks, handling wear where hands rub, oil sheen, scratches along the direction of handling; the finish of the specification (it must differ from the other guns). Uniform texel density, no visible seams on flat faces. Bake CPU, at most 2 threads, in the background.
- Proof: the pipeline's export validation; import the exported GLB into a fresh scene and pose every bone (bolt back, trigger pulled, magazine rocked out...) to prove pivots and weights; a socket-positions report like _weapons_check.py makes for the CHOPPER and NINE (add your gun to a check script of your own, art/blender/assets/_weapons_check_${j.gun}.py).
- Previews in art/previews/ (1280 x 720, at most 300 kB each, look at each, at most 8 renders, two self-review rounds fixing the worst visible fault each round): weapons_${j.gun}_hero.jpg (three-quarter, studio HDRI), weapons_${j.gun}_fp.jpg (through a first-person camera with the same vertical field of view and viewmodel pose the CHOPPER's fp preview uses), weapons_${j.gun}_side.jpg (a flat orthographic left side view on a plain background: this is what a player's eye reads first), weapons_${j.gun}_parts.jpg (posed open, magazine beside it), and the white-on-transparent 512 x 192 side silhouette art/out/ui/T_UI_Gun_${j.gun[0].toUpperCase() + j.gun.slice(1)}.png (not committed).
Another agent builds the parts kit and the CHOPPER/NINE mounts at the same time (art/blender/assets/weapons_parts.py): do not edit its files; your gun's mount sockets (Optic, MuzzleMount, Underbarrel, Laser per the specification) must sit on real rails and threads you modelled.
Add your section to art/blender/PROGRESS.md and your row to the README's family table; commit and push in working steps.
Return through the structured output: summary (at most 150 words), files, previews, assets (exported names with triangle counts and texture sizes), known_weaknesses (honest, most visible first), notes_for_integration (bones, sockets, GLB and texture names, what the Unreal import must do), head_commit.`

const partsPrompt = `${CONTEXT}

${PIPE}

YOU ARE THE PARTS MODELER. The designer's specification (JSON; follow it, and where it is silent follow the CHOPPER's and NINE's conventions): ${JSON.stringify(spec)}

Two jobs, in this order.
1. The mounts on the EXISTING guns. In the CHOPPER's and NINE's Blender code add, without moving any existing point (art/blender/assets/_weapons_check.py must still say ALL FIXED POINTS KEPT), the model detail the mounts need and the sockets the specification names: on the CHOPPER a short top-cover rail (or a side rail) for an optic, a threaded muzzle for a suppressor, a handguard rail for an underbarrel grip, a side rail for a laser; on the NINE a rail under the frame for a laser and a threaded barrel end for a suppressor. Add the mount geometry as part of the gun's own meshes where it belongs to the gun (a rail IS part of the gun, so the gun's GLB changes: keep triangle counts within +10 %), and re-export both guns through the existing export path. Put your code in art/blender/assets/weapons_parts.py (a new family) as functions the existing files do not need to change for, or, where a change to _weapons_chopper.py or _weapons_nine.py is unavoidable, add the mount functions at the end and call them from the end of the build, leaving every earlier line as it is.
2. The parts kit, our own universal parts, built once at the origin of their mount (the specification names each part's socket and dimensions): a compact red dot sight and a 4x scope (lens slots, SightEye sockets), a long suppressor (Muzzle socket at its far end) and a compensator, a vertical grip and an angled grip (SupportHand sockets), a red laser module (Beam socket), and the extended magazines the specification lists. Real-looking and detailed (these are seen at 30 cm): modelled threads, clamp screws, rail clamps, lens rings, knurling; baked unique 2K sets (parts share sets where they share a material); every part exports as its own GLB (SM_Part_<Id>) with its mount origin at the file origin and the socket names the specification gives, validated by the pipeline's export step.
Proof: pose-check by assembling each part on the gun it belongs to in a fresh scene (the CHOPPER with scope + suppressor + vertical grip + laser; the NINE with laser + suppressor + extended magazine; and the three new guns once their files exist: check art/blender/assets for weapons_shorty.py, weapons_stretch.py, weapons_rattler.py and use them when present; if not yet, do those assemblies last, waiting and re-checking) and render assembly previews in art/previews/: weapons_parts_kit.jpg (all parts on a plain background, labelled by position), weapons_chopper_built.jpg and weapons_nine_built.jpg (the guns fully built, three-quarter view), at most 8 renders, two self-review rounds. A part that floats off its rail or intersects the gun is a fault to fix.
Add your section to art/blender/PROGRESS.md and rows to the README family table; commit and push in working steps.
Return through the structured output: summary (at most 150 words), files, previews, assets (exported names with triangle counts and texture sizes), known_weaknesses, notes_for_integration (every socket by name and position per gun and per part, the compatibility table changes needed in attachments.json, what the Unreal import must do), head_commit.`

const built = await parallel([
  ...JOBS.map(j => () => agent(gunPrompt(j), { label: 'model:' + j.key, phase: 'Model', schema: WORK })),
  () => agent(partsPrompt, { label: 'model:parts', phase: 'Model', schema: WORK }),
])
const results = built.map((r, i) => ({ key: i < JOBS.length ? JOBS[i].key : 'parts', result: r }))
log(`modelled: ${results.filter(r => r.result).map(r => r.key).join(', ')}; missing: ${results.filter(r => !r.result).map(r => r.key).join(', ') || 'none'}`)

const LENSES = [
  { key: 'look-and-distinctness', prompt: `YOUR LENS: what a player sees. Look at every preview in art/previews/ named weapons_* (Read tool), the new side views especially, and re-render anything you doubt. Judge: (1) would a player say these guns look the same? Build a contact sheet of the six side silhouettes of CHOPPER, NINE, SHORTY, STRETCH, RATTLER (and say what the pack carbine STICK adds: an M4-pattern carbine) at 512 x 192 and compare them pairwise by eye AND by number (normalise each to the same length, intersection over union of the filled silhouettes: below 0.75 for every pair of our five); (2) realism and finish against the CHOPPER and NINE: surface wear, edge radii, believable detail at 30 cm, texture seams, fake-looking noise; different material stories per gun; (3) the parts: do they sit on real rails and threads, are they believable, do the built guns look like one design; (4) anything that looks like a real maker's mark or trademark. Grade each gun and the kit from 1 to 5 against the CHOPPER and NINE (3 = on a par).` },
  { key: 'rig-export-budget', prompt: `YOUR LENS: the technical contract. Run, do not guess: for every new asset import its exported GLB into a fresh scene, list bones and sockets and compare them with the specification and with the CHOPPER's and NINE's naming; pose every moving bone and check that nothing tears, that pivots are right and travel runs along local X; confirm every vertex has exactly one weight of 1.0; triangle counts against the specification's budget (hard limit 120,000 per gun) and texture sizes; the manifest entries; that _weapons_check.py still says ALL FIXED POINTS KEPT for the CHOPPER and NINE and that their triangle counts grew by at most 10 %; that the family registry builds from a clean checkout of this repository (art/out/ is git-ignored: nothing may depend on a file outside the repository except the pipeline's own scans); that each part's mount origin is at the file origin and its sockets are named as the specification says; that tools/box/anim/ue_import_guns.py would import the GLBs (read it: names, bones it expects, what it would do with a new gun) and list what it needs changed.` },
]

const reviews = (await parallel(LENSES.map(l => () =>
  agent(`${CONTEXT}

${PIPE}

YOU ARE AN ADVERSARIAL REVIEWER of the weapons round 4 art. The specification (JSON): ${JSON.stringify(spec)}
The modelers reported (JSON): ${JSON.stringify(results)}
Do not edit files and do not commit; you may run Blender and Python to measure and render into a scratch folder under the scratchpad or /tmp. ${l.prompt}
Report only real defects with evidence (a command and its output, a preview and what it shows), the concrete failure each causes in the game, and the exact fix. must-fix = the guns would look alike, an asset would not import or would break the existing CHOPPER or NINE, a part would not sit on its mount, a budget is broken, or a real mark is visible; should-fix = real but minor; nit = cosmetic. List what you checked and found correct, and give the grade.`, { label: 'review:' + l.key, phase: 'Review', schema: REVIEW })
    .then(r => r ? { lens: l.key, ...r } : null)
))).filter(Boolean)

const open = reviews.flatMap(r => r.findings.filter(f => f.severity !== 'nit').map(f => ({ lens: r.lens, ...f })))
log(`review: ${open.length} findings above nit (${open.filter(f => f.severity === 'must-fix').length} must-fix); grades: ${reviews.map(r => r.lens + ' ' + r.grade).join('; ')}`)

phase('Fix')
const fixed = open.length === 0 ? null : await agent(`${CONTEXT}

${PIPE}

YOU FIX WHAT THE REVIEW FOUND in the weapons round 4 art. The specification (JSON): ${JSON.stringify(spec)}
The modelers' reports (JSON): ${JSON.stringify(results)}
Review findings (JSON): ${JSON.stringify(open)}
For each finding: check it yourself first (reviewers can be wrong; say so with evidence if you reject one); fix it in the Blender code (not by hand), re-export, re-validate, re-render the affected previews and LOOK at them. Every must-fix is fixed; fix as many should-fix as the time allows (about 2 hours). Keep CPU use to 2 threads. Commit and push in working steps; update the PROGRESS sections. Return through the structured output: summary, files, previews, assets, known_weaknesses (what is still wrong, honestly), notes_for_integration (corrections to what the modelers wrote), head_commit.`, { label: 'fix:review', phase: 'Fix', schema: WORK })

phase('Deliver')
const delivered = await agent(`${CONTEXT}

${PIPE}

YOU PREPARE THE HAND-OFF to the Unreal integration engineer (who works later, on the GPU box, from the repository and an art archive; you do not touch the box).
Reports so far (JSON): SPEC ${JSON.stringify(spec)} MODELERS ${JSON.stringify(results)} FIXES ${JSON.stringify(fixed)} REVIEWS ${JSON.stringify(reviews)}
1. Make sure everything is committed and pushed; run the whole build once from a clean state for every new asset and for the CHOPPER and NINE (export + validation) and confirm all pass; run _weapons_check.py.
2. Make the archive of the exports the way tools/box/send-art.sh and the earlier archive art/out/fp-guns.tar were made (read the script; same layout; name it art/out/fp-guns-r4.tar; it is git-ignored): the GLBs of the three new guns, their textures, the parts kit, the re-exported CHOPPER and NINE, the manifest, the UI silhouettes. Record its sha256 and size in the hand-off.
3. Write docs/unreal/WEAPONS_R4.md: for an engineer who has not seen this work: what was built (a table of every asset: name, triangles, textures, bones, sockets), the roster of six and how each looks, the parts kit and which part fits which gun and slot, the exact data changes needed in guns.json (mesh, mounts status, art status, ready) and attachments.json (presentation meshes, compatibility rows, effect numbers where a part is ours), the Unreal import steps (what ue_import_guns.py needs to learn; sockets to verify with the MurderInc.Loadout.MountsExist test), the first-person arm notes (palms, support hand, the camera recipe, per-gun IK targets), the sound and animation consequences (which clips each new gun can reuse), what is not done, and the known weaknesses. Commit and push it.
4. Return the structured output: summary (at most 200 words, plain English, what the owner will see), files, previews (the ones to show the owner), assets, known_weaknesses, notes_for_integration (a short numbered checklist), head_commit.`, { label: 'deliver', phase: 'Deliver', schema: WORK })

return { spec, results, reviews, fixed, delivered }
