export const meta = {
  name: 'mi-guns-integrate',
  description: 'Weapons round 4, Unreal side: the CHOPPER and NINE with their own art and mounts, the new SHORTY and STRETCH, the RATTLER unhidden, our parts kit on every gun, hands and sights, icons, tests, proof pictures; reviewed and fixed; no packaging',
  phases: [
    { title: 'Plan', detail: 'what exists, what the import and the code must learn' },
    { title: 'Build', detail: 'import, data, code, tests, proof pictures, in the order of the list' },
    { title: 'Review', detail: 'in-game look and function; data, tests, regressions, budgets' },
    { title: 'Fix', detail: 'what the review found' },
  ],
}

const SP = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad'
const BRANCH = 'claude/tender-albattani-5q78qr'

const CONTEXT = `
PROJECT: MURDER INC., a first-person shooter in Unreal Engine 5.9 (C++ project unreal/MurderInc), streamed from a Linux machine by Eagle 3D Streaming (E3DS) into the owner's website. Repo /home/user/MURDER-INC. (branch ${BRANCH}: commit and push there, small commits, each ending with exactly these two lines:
Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4
git pull --no-rebase before every push, git add with explicit paths only (other agents have unfinished files in the tree), never force-push, no pull request; no link, storage address, email, E3DS account or host user name, or person's name in any commit; no model name anywhere else).

THE OWNER'S ASK (2026-11-25): "all the guns look the same and no attachments are able to be added to the guns", then: "the guns need to be priority with attachments". This is the top priority of the whole project today.

WHAT IS TRUE TODAY (verified in the E3DS stream and in the data, 2026-11-25): the rack offers CHOPPER, NINE, SHORTY, STICK and STRETCH. SHORTY, STICK and STRETCH are ONE purchased-pack M4-style carbine in three handguard lengths (they look the same) and their Workbench works: five slots (optic, muzzle, underbarrel, laser, magazine) with the pack's own part meshes at sockets written by tools/box/anim/ue_import_guns.py; the CHOPPER (default gun, slot 1) shows a stand-in rifle and the NINE a stand-in pistol and both say "No attachments" because their mounts are missing; the RATTLER (the SMG the Goons carry) is hidden because its first-person mesh does not exist. Read docs/unreal/LOADOUT.md (section 3.2, 3.3, 6 and 8), docs/unreal/ANIMATION.md (the gun and arm sections), docs/unreal/CHARACTERS.md (hands), unreal/MurderInc/Content/Data/guns.json, attachments.json, presentation.json and grips.json, and the C++ that assembles and shows guns (grep UMIGunAssembly, the viewmodel, the Workbench and the stage in unreal/MurderInc/Source/MurderInc).

WHAT THE ART LANES DELIVER (Blender, scripted; they are working right now, commit as they go, and the first workflow's last stage will add docs/unreal/WEAPONS_R4.md as the hand-off): the designer's specification is docs/unreal/weapons_r4_spec.json (guns, parts, sockets with positions, data_changes A-F, the order list: its steps 6 and 7 are YOUR job). Lane 1: SHORTY (bullpup carbine) and STRETCH (marksman rifle). Lane 2: the CHOPPER and NINE re-exported WITH mounts (committed: sockets and the Booster and FrontSight bones), the PARTS KIT (red dot, 4x scope, suppressor, compensator, pistol suppressor, vertical and angled and wooden grips, laser module, extended magazines) and the RATTLER. Their exports are in art/out/ of THIS container (git-ignored: glb/, textures/, manifest.json, weapons_r4.json, ui/), their Blender code and previews are committed (art/blender/, art/previews/). What is not exported yet when you start will appear while you work: check git log and art/out before each step, and do the steps in the order of your list so that you never wait idle. How art reaches the box: tools/box/send-art.sh here, tools/box/receive-art.sh on the box (read docs/unreal/BOX.md), then tools/box/anim/ue_import_guns.py (read it: it must learn the new meshes, bones, sockets and parts).

BOX AND ETIQUETTE is below. `

const BOX = `BOX AND ETIQUETTE (important): GPU box = Higgsfield rental, session id in ${SP}/box/session (now ec087d85-b777-4ece-be42-ccc063d225cf, RTX PRO 6000 Blackwell, 16 CPUs, 64 GB). Tool: mcp__Higgsfield__gpu_rental_exec (load its schema with ToolSearch "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__gpu_rental"), at most 90 s per call (it may time out at 60 s: check before repeating), so start long work detached (setsid nohup ... &) and poll. If the box is gone follow BOX.md's box-gone procedure exactly (same spec only; never more than one box). OTHER JOBS USE THIS BOX: the version 3b release (its engineers package from /project/ue/repo-release and test in /project/ue/repo-gameplay, and run the release gate on the GPU: a long queue of measuring runs, lag-test.sh), the release 3c code engineers (clone /project/ue/repo-3c) and the owner's browser on the box's desktop. Therefore: (1) NEVER touch /project/ue/repo-gameplay, /project/ue/repo-release, /project/ue/cloud/e3ds-upload*, /project/ue/cloud/MurderInc-E3DS.zip, /project/ue/cloud/build-*, the v3a/v3b files in /project/ue/cloud, or the browser (owner-browser, /tmp/e3ds-owner-browser, Firefox). (2) Work in YOUR OWN clone /project/ue/repo-guns (never repo-3c): make it as BOX.md section 7 describes (git clone of the public repository's branch, seed-content.sh, the art and map copies the gameplay clone needs to play a Story run, the audio import if tools/box/audio-import.sh applies, the first build about 12 minutes); if the repository's branch already has what you need use it, and copy generated content (never committed) from the gameplay clone with cp --reflink=auto only, never move it. (3) Run every compile with nice -n 19 and at most 6 parallel jobs (UBT: -MaxParallelActions=6), and start no compile, cook or test suite while a gate run is active (pgrep -f lag-test.sh or a game process of another job: wait and re-check); lag-test.sh already serialises games on the GPU: use it. (4) Several games on one GPU produce the very stall you measure: one game at a time, throw away polluted runs. (5) Do not package, do not upload anything to E3DS, do not touch the owner's Higgsfield storage except for moving pictures and art archives (BOX.md says how). (6) If a gate run is active for hours, do the work that needs no compile first (reading, data, scripts, the art archive transfer), and compile/test when the box is free; say in your report how long you waited.

`

const RULES = `RULES: the gameplay rules must not change: the full automation suite (tools/box/test.sh MurderInc in your clone) must pass, golden replays included, with no test weakened, skipped or re-recorded; a gun's numbers in guns.json stay as they are unless a data_changes item of the specification says otherwise; new behaviour gets new tests; the web game src/ is never touched; no pack, Epic or likeness content, link or account name is ever committed (the pack's meshes are imported on the box and never committed; our own art may be committed as data and scripts only: binaries stay on the box); plain English in docs and commit messages. In a clean checkout (no pack) the pack rifles are not offered and everything else must still work. Be honest in every report: say what was measured, what was only read, what is unproven. LOOK at every picture you make (Read tool) and fix what is visibly wrong before you report.`

const WORK = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    done: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, what: { type: 'string' }, evidence: { type: 'string' } }, required: ['item', 'what', 'evidence'] } },
    not_done: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, why: { type: 'string' } }, required: ['item', 'why'] } },
    pictures: { type: 'array', items: { type: 'string' } },
    tests: { type: 'string' },
    head_commit: { type: 'string' },
    notes_for_release: { type: 'string' },
  },
  required: ['summary', 'done', 'not_done', 'pictures', 'tests', 'head_commit', 'notes_for_release'],
}

const REVIEW = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] },
      where: { type: 'string' }, evidence: { type: 'string' }, failure: { type: 'string' }, fix: { type: 'string' },
    }, required: ['title', 'severity', 'where', 'evidence', 'failure', 'fix'] } },
    checked_ok: { type: 'array', items: { type: 'string' } },
  },
  required: ['findings', 'checked_ok'],
}

phase('Plan')
const plan = await agent(`${CONTEXT}
${BOX}
${RULES}

YOU ARE THE PLANNER (read-only: edit no file, commit nothing, start no box job except reading). In about 20 minutes produce the integration plan the engineer will follow: (1) what each gun needs in the game today and tomorrow: its mesh asset names and paths, skeleton, bones and sockets the art delivers (read art/blender/assets/weapons_*.py, the manifest and the specification) against what tools/box/anim/ue_import_guns.py, UMIGunAssembly, the viewmodel (hands, IK on Palm_R and Palm_L, sights), the Workbench and the stage expect; (2) the exact data changes per file (guns.json art/mounts/variants/ready, attachments.json presentation meshes, compatibility rows and effect numbers where a part is ours, presentation.json, grips.json) with the specification's data_changes A-F checked against the real files; (3) the exact code changes (C++ file, function, what and why), keeping them small and data-driven: for example the Booster that a suppressor hides, the SightEye used for the aimed view when an optic is fitted, a stock variant by re-exporting the RATTLER with its stock posed, the support hand taking the grip's SupportHand socket, magazines on MagHinge; (4) the tests to add or change (names), and what the automation suite must still show; (5) the proof pictures to make with which scripts (loadout-shots.sh, play-shots.sh, shot.sh) and how many; (6) risks and the order of work that finds them first; (7) how long each step should take on this box. Return it as structured text in the schema.`, { label: 'plan', phase: 'Plan', schema: { type: 'object', properties: { plan: { type: 'string' }, steps: { type: 'array', items: { type: 'string' } }, risks: { type: 'array', items: { type: 'string' } } }, required: ['plan', 'steps', 'risks'] } })

phase('Build')
const built = await agent(`${CONTEXT}
${BOX}
${RULES}

THE PLAN (from the planner): ${JSON.stringify(plan)}

YOU ARE THE INTEGRATION ENGINEER. Do the plan in this order, committing and pushing after each step that works (small commits), re-checking what the art lanes have exported before each step:
1. Your clone on the box and the art there (BOX.md section 7; send-art.sh / receive-art.sh); compile (nice -n 19, at most 6 jobs; wait while a gate run is active, doing steps 2 to 4 in the meantime as far as they need no compile).
2. The CHOPPER and the NINE with their own meshes and their mounts: import (extend ue_import_guns.py), the data (guns.json art and mounts statuses, presentation.json, compatibility rows), so that the rack, the stage, the Workbench and the first-person view show OUR guns, and the Workbench offers slots on both. Until the parts kit is exported, offer only slots whose part meshes exist; with the pack present the pack's parts may be fitted on the CHOPPER's sockets only if they sit right (look at the picture), otherwise keep the slot unoffered.
3. SHORTY and STRETCH as the new guns (their own meshes replace the pack variants for these two ids; the STICK stays the pack carbine): import, sockets, magazines, variants, data, ready flags, hands and sights (Palm_R / Palm_L, SightEye), icons T_UI_Gun_* from art/out/ui.
4. The parts kit on every gun at the sockets (data per gun where a part needs another mesh or offset), the fitting animation in the Workbench, the suppressor hiding the booster or muzzle device, the optic's sight picture, the laser's beam from the Beam socket, the grips' SupportHand, the extended magazines.
5. The RATTLER (unhidden when its mesh and a procedural set of clips exist), its stock variant, its muzzle mount.
6. Tests and the full automation suite; then the proof pictures (rack with all guns; the Workbench on every gun with every slot and one part fitted; first-person view of every gun at the hip and aimed, one shot fired; the side-by-side lineup in game), all looked at and fixed.
7. Docs (LOADOUT.md 6.1 to 6.3 statuses, ANIMATION.md, PROGRESS.md, a section in docs/unreal/WEAPONS_R4.md or a new docs/unreal/WEAPONS_R4_UNREAL.md if the first workflow has not written it), commit, push.
If a lane has not exported something when you reach its step, do everything else first and come back; at the end say exactly what was integrated and what was missing. Report through the schema.`, { label: 'integrate', phase: 'Build', schema: WORK })

phase('Review')
const LENSES = [
  { key: 'in-game', prompt: 'YOUR LENS: what a player sees and does. Look at every picture the engineer made (Read tool) and make your own with the box scripts where you doubt: do the guns read as different guns in the rack, on the stage and in the hands? Does every part sit on its rail or thread without floating, clipping or flipping, at the hip and aimed? Is the sight picture right with each optic (the eye on SightEye), the laser beam from the right place, the support hand on the grip, the magazine seated, the muzzle flash at the muzzle with a suppressor on? Does the Workbench show every slot of every gun, preview and fit with mouse, keyboard and pad (read the code paths), and does a build survive Next, a run, and the next run? Judge the hands and arms with each gun.' },
  { key: 'data-and-regression', prompt: 'YOUR LENS: data, tests, regressions, budgets. Run the full automation suite yourself (tools/box/test.sh MurderInc in the engineer clone after it is idle) and the golden replays; read every changed data file against the schema and LOADOUT.md; a saved set-up from before this change must load (builds for guns whose meshes changed); in a clean checkout (no pack) nothing may reference a missing asset; MountsExist must check every socket of every mesh; the guns must stay within the budget of the streaming machine (an RTX A4000 shared, SM5, no Nanite): triangles per gun at most about 120,000, texture memory, load time of the rack; git status of binaries (no pack, no Epic content, no generated binaries committed).' },
]
const reviews = (await parallel(LENSES.map(l => () =>
  agent(`${CONTEXT}
${BOX}
${RULES}

YOU ARE AN ADVERSARIAL REVIEWER of the weapons integration. The engineer reported (JSON): ${JSON.stringify(built)}
Do not edit files and do not commit; you may run box scripts and Python to measure and to make pictures into a scratch folder. ${l.prompt}
Report only real defects with evidence (a command and its output, a picture and what it shows), the concrete failure each causes in the game, and the exact fix. must-fix = the player sees a broken gun or part, a crash, a failing test, a rule change, a missing asset reference, or a budget broken; should-fix = real but minor; nit = cosmetic. List what you checked and found correct.`, { label: 'review:' + l.key, phase: 'Review', schema: REVIEW })
    .then(r => r ? { lens: l.key, ...r } : null)
))).filter(Boolean)

const open = reviews.flatMap(r => r.findings.filter(f => f.severity !== 'nit').map(f => ({ lens: r.lens, ...f })))
log('review: ' + open.length + ' findings above nit (' + open.filter(f => f.severity === 'must-fix').length + ' must-fix)')

phase('Fix')
const fixed = open.length === 0 ? null : await agent(`${CONTEXT}
${BOX}
${RULES}

YOU FIX WHAT THE REVIEW FOUND. The engineer's report (JSON): ${JSON.stringify(built)}
Findings (JSON): ${JSON.stringify(open)}
For each finding: check it yourself first (reviewers can be wrong; say so with evidence if you reject one), fix it, re-run what proves it (tests, pictures: LOOK at them), commit and push. Every must-fix is fixed; fix as many should-fix as time allows (about 90 minutes). The full automation suite must pass at the end. Report through the schema.`, { label: 'fix:review', phase: 'Fix', schema: WORK })

return { plan, built, reviews, fixed }
