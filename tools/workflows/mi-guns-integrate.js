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
const dataPrompt = `${CONTEXT}
${BOX}
${RULES}

THE PLAN (from the planner): ${JSON.stringify(plan)}

YOU ARE THE DATA ENGINEER. Two engineers work at the same time on this: you, and the BOX ENGINEER, who owns the box, the clone /project/ue/repo-guns, every C++ file and every automation test. You never touch the box clone, C++ or tests. YOU OWN: unreal/MurderInc/Content/Data/guns.json, attachments.json, presentation.json, the text data (frontend and text json) and anything else under Content/Data, docs/unreal/LOADOUT.md, docs/unreal/WEAPONS_R4*.md, and the checker you write. You do plan step S2 completely (all six guns, all parts, the compatibility rows, the effect numbers and the trade check, presentation, text), the throwaway checker (resolve ids, parts exist in their slot, text keys, trade B/W, every mount socket and hide bone present in art/out/manifest.json, all six guns pass the ready rule), and the data side of S11 (LOADOUT.md statuses). Commit and push each working step at once (explicit paths, git pull --no-rebase first): the box engineer pulls your commits. When a data item depends on art that is not exported yet (the parts kit, final textures), write the data from the specification (docs/unreal/weapons_r4_spec.json) with the paths the plan proposes, say in your report what must be re-checked against art/out/manifest.json and weapons_r4.json, and re-check it when the art appears (look at git log and art/out about every 15 minutes while you work on other items, and once more at the very end). Also write docs/unreal/WEAPONS_R4_TESTS.md: the exact list of existing automation test expectations that your new data makes false (the plan's section 4: DataLoads counting 10 parts, RealArt, OpticTwin, Clips, Frontend.Walk, Save.SetupValidation, Attachments magSize...) and what each must assert instead, so that the box engineer changes them without guessing. Add the dated DECISIONS.md entry the plan asks for (the owner's words reverse the mesh part of the decision of 2026-11-23). Report through the schema.`

const boxPrompt = `${CONTEXT}
${BOX}
${RULES}

THE PLAN (from the planner): ${JSON.stringify(plan)}

YOU ARE THE BOX ENGINEER. Two engineers work at the same time on this: you, and the DATA ENGINEER, who owns unreal/MurderInc/Content/Data/*.json (guns, attachments, presentation, text), docs/unreal/LOADOUT.md and docs/unreal/WEAPONS_R4*.md: you never edit those; pull their commits (git pull --no-rebase) when they appear, and read docs/unreal/WEAPONS_R4_TESTS.md when it exists (the test expectations their data makes false). YOU OWN the box, the clone /project/ue/repo-guns, every C++ file, the tools under tools/box, and every automation test. You do plan steps S1, S3, S4 (C++, tools and tests, everything that is not data), S5 to S9, S11 (tests and proof pictures) and S12 (the hand-off for the release engineer); S10 only if time allows. START AT ONCE with the box work that needs nothing from the data engineer: S1 (the clone), S3 (the art transfer), S5 (the baseline build and the 127 tests: the version 3b release gate is STOPPED and the box is free of measuring runs, but the 3c engineers and the sound engineer compile and test there too: still one game at a time on the GPU, compiles niced with 6 jobs, and check pgrep before starting a game or the editor), then S6 (the probe: bone frames, meshOffset, hidden bones: it decides the C++ you write), then S4, S7 and on. Commit and push small steps (explicit paths, git pull --no-rebase first). When the art lanes export something new (git log, art/out), re-run the import. Report through the schema; say what runtime facts you measured against what you only read.`

const [builtData, builtBox] = await parallel([
  () => agent(dataPrompt, { label: 'data-engineer', phase: 'Build', schema: WORK }),
  () => agent(boxPrompt, { label: 'box-engineer', phase: 'Build', schema: WORK }),
])
const built = { data: builtData, box: builtBox }

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
