export const meta = {
  name: 'mi-hands-real',
  description: 'Realistic hands on every gun in first person: tune the arms, grips, shoulders and views per gun in the packaged game (data is loose, so each try is minutes), judged on real streamed frames, reviewed adversarially, fixed, written back to the repository',
  phases: [
    { title: 'Tune', detail: 'per gun: hip, aimed, firing, reload; data and grips only' },
    { title: 'Review', detail: 'two adversarial looks at the frames: realism, and what a player notices' },
    { title: 'Fix', detail: 'what the review found' },
  ],
}

const BRANCH = 'claude/tender-albattani-5q78qr'
const SP = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad'

const CONTEXT = `PROJECT: MURDER INC., a first-person shooter in Unreal Engine 5.9 (unreal/MurderInc), streamed by Eagle 3D Streaming; repo /home/user/MURDER-INC., branch ${BRANCH}.
THE OWNER JUST SAID: "the hands dont look correct ensure the hands holding the weapons are realistic". This is now the most important visible problem. The guns of weapons round 4 are in the game (CHOPPER, NINE, SHORTY, STICK, STRETCH, RATTLER; docs/unreal/WEAPONS_R4.md, PROGRESS.md entries of 2026-11-25, ANIMATION.md section 11). The frames of the release engineer's trial package (/project/ue/cloud/lag-v6trial/t-guns and t-guns-b on the GPU box: g-gun1..3*.jpg, gb-gun3..4*.jpg, hip, aim, fired, reload) show on the four hand-IK rifles (CHOPPER, SHORTY, STRETCH, RATTLER): the support arm as a cut upper arm ending in a brown ball (the fist seen end-on) floating above the gun, an arm filling a third of the screen in a reload, and the optic housing as a black ring when aimed. The NINE and the pack STICK are held well: use them as the reference of what right looks like.
WHAT DRIVES THE HANDS (read before changing anything): unreal/MurderInc/Content/Data/presentation.json firstPerson.animSets (per gun: kind, shoulders, views, relief, grip, finger curls...), grips.json (solved finger points per gun, art/blender/assets/_rule_grips.py, _characters_pose.py GUNS: the solves and the views they assume), guns.json views, Source/MurderInc/Weapons/MIFirstPersonRig.cpp and MIFirstPersonAnim.cpp (how the arms are placed: shoulder anchor, two-bone IK to Palm_R / Palm_L or the grip's SupportHand, FMIFPHandShape from the grip points), ANIMATION.md section 11. Known from the grip solver: the rifle sets carried the NINE's shoulders [-6, 0, -24], too far for the support hand; the lead set CHOPPER [-8.5, 1.1, -12.4], STRETCH [-6.5, 1.1, -12.4], RATTLER [-2.5, 1.1, -12.4] (commit 87ad3b9, NOT yet seen in play); the SHORTY's hip view is the CHOPPER's numbers on a gun whose origin is its butt pad, so its forend sits about 70 cm out (wrong: fix its view so the butt is at the shoulder, then re-solve its grip). The console variable mi.FP.Shoulders exists for trying shoulder values live.
THE FAST LOOP: the packaged game reads Content/Data as LOOSE files (MurderInc/Content/Data/*.json in the zip /project/ue/cloud/v6trial.zip). So: unpack that zip ONCE into your own folder (/project/ue/hands/zip, never into another job's folder), and for each try copy the repository's data files over its Content/Data, then run ONE stream session with tools/box/cloud/lag-test.sh (read its header: game=ship build=<your folder>, the view scripts tools/box/cloud/guns-keys.txt and guns-keys-b.txt equip every gun, aim, fire and reload; it saves received frames you look at with the Read tool; lag-test.sh serialises games on the GPU and waits for a free one: use it, never start a game beside another). Make a contact sheet of the frames with tools/box/sheet.py, move it here as BOX.md says (media_upload, put, media_confirm, curl), LOOK at it. A try costs a few minutes. If a fix needs C++, you do NOT edit C++ (the box engineer of the integration owns MIFirstPersonRig and the clone /project/ue/repo-guns and is editing them right now in the same working tree): write the exact change (file, function, lines, why, the frame that shows it) in docs/unreal/HANDS_R4.md and say so in your report; the lead applies it.
BOX: Higgsfield GPU box, session ec087d85-b777-4ece-be42-ccc063d225cf, tool mcp__Higgsfield__gpu_rental_exec (load with ToolSearch "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__media_upload,mcp__Higgsfield__media_confirm"), at most 90 s per call, so start longer work detached (setsid nohup ... &) and poll. Never touch the owner's browser (Firefox, /tmp/e3ds-owner-browser), the other jobs' clones (repo-guns, repo-3c, repo-release, repo-gameplay, repo-audio) or /project/ue/cloud/MurderInc-E3DS.zip and e3ds-upload*. Read docs/unreal/BOX.md first.
GIT: commit only data, Blender grip code and docs (unreal/MurderInc/Content/Data/presentation.json, grips.json, guns.json views, art/blender/assets/_characters_pose.py, _rule_grips.py, art/previews/hands_*.jpg, docs/unreal/HANDS_R4.md, PROGRESS.md); explicit paths, git pull --no-rebase before every push, never git add -A, never force-push; commit messages end with exactly these two lines and contain no link, account or person's name:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4
RULES: no gameplay number changes (fire, recoil, spread, timings in guns.json rules stay exactly as they are: only presentation: views, arms, grips); the data checker tools/data/check_guns_data.py must report 0 errors; LOOK at every frame you judge by; be honest about what was seen in play and what was only read.`

const WORK = { type: 'object', properties: {
  summary: { type: 'string' }, per_gun: { type: 'array', items: { type: 'object', properties: { gun: { type: 'string' }, state: { type: 'string' }, evidence: { type: 'string' } }, required: ['gun', 'state', 'evidence'] } },
  cpp_needed: { type: 'array', items: { type: 'string' } }, sheets: { type: 'array', items: { type: 'string' } }, head_commit: { type: 'string' } },
  required: ['summary', 'per_gun', 'cpp_needed', 'sheets', 'head_commit'] }
const REVIEW = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: { title: { type: 'string' }, severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit'] }, gun: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['title', 'severity', 'gun', 'evidence', 'fix'] } },
  checked_ok: { type: 'array', items: { type: 'string' } } }, required: ['findings', 'checked_ok'] }

phase('Tune')
const tuned = await agent(`${CONTEXT}

YOU ARE THE HANDS ENGINEER. Goal: on every gun, in the hip view, aimed, firing and reloading, the two hands hold the gun the way a real shooter does, as well as the NINE and the STICK already do: the firing hand wraps the pistol grip with the index finger along or on the trigger and the thumb round the grip; the support hand under or around the handguard or forend (or on the fitted foregrip), palm up the way a rifle is held, the forearm running toward the bottom left of the picture, never a cut limb, ball or floating fist in view; elbows and forearms at believable angles; no fingers through the gun; scale and skin consistent with the NINE. Work gun by gun in the order a player sees them: CHOPPER (slot 1, everybody sees it first), SHORTY, STRETCH, RATTLER, then check the NINE and STICK did not change. For each: first look at the trial frames to see the fault, then fix with data (shoulders, views, relief, IK targets, finger curls, grip choice) and, where the solve is wrong for the gun's real view, re-solve with _rule_grips.py (one Blender process, 1 thread, nice -n 10: python ${SP}/bl/venv/bin/python). Prove each with a fresh stream run's frames (hip, aimed with irons, aimed with an optic fitted if the gun takes one, fired, reloading). Commit each gun's data when its frames look right; put one contact sheet per gun under 300 kB in art/previews/hands_<gun>.jpg. Write docs/unreal/HANDS_R4.md (what was wrong per gun, what was changed, the frames that prove it, any C++ the lead must apply). Report through the schema.`, { label: 'hands:tune', phase: 'Tune', schema: WORK })

phase('Review')
const LENSES = [
  { key: 'realism', prompt: 'YOUR LENS: does it look like a real person holding a real gun? Compare with photographs and footage you know of people shooting carbines, bullpups, marksman rifles, SMGs and pistols: hand placement, wrist angles, the line of the support arm, finger wrap, thumb, how much of the arm a first-person camera at the eye would see, scale of the hands against the gun. Every gun, hip and aimed and reloading.' },
  { key: 'player', prompt: 'YOUR LENS: what a player notices in the first minute: anything floating, cut, clipping, flickering, popping between states (hip to aim, fire, reload, swap), a hand that leaves the gun, an arm that blocks the view, a gun that looks held by nobody. Make your own fresh stream run with the newest data (same fast loop) and look at the frames in motion order.' },
]
const reviews = (await parallel(LENSES.map(l => () => agent(`${CONTEXT}

YOU ARE AN ADVERSARIAL REVIEWER of the hands. The hands engineer reported (JSON): ${JSON.stringify(tuned)}
Do not edit or commit. ${l.prompt} Report only real defects with the frame that shows each, the gun, and the exact fix (data values or the C++ change). must-fix = the owner would say the hands do not look right; should-fix = a careful player would notice; nit = cosmetic. List what you checked and found right.`, { label: 'review:' + l.key, phase: 'Review', schema: REVIEW }).then(r => r ? { lens: l.key, ...r } : null)))).filter(Boolean)

const open = reviews.flatMap(r => r.findings.filter(f => f.severity !== 'nit').map(f => ({ lens: r.lens, ...f })))
log('hands review: ' + open.length + ' above nit, ' + open.filter(f => f.severity === 'must-fix').length + ' must-fix')

phase('Fix')
const fixed = open.length === 0 ? null : await agent(`${CONTEXT}

YOU FIX WHAT THE HANDS REVIEW FOUND. The first engineer's report (JSON): ${JSON.stringify(tuned)}
Findings (JSON): ${JSON.stringify(open)}
Check each against fresh frames (a reviewer can be wrong: say so with the frame), fix every must-fix and as many should-fix as possible with data and grips (C++ only as a written change in HANDS_R4.md for the lead), prove with new frames, commit, update HANDS_R4.md and the contact sheets. Report through the schema.`, { label: 'hands:fix', phase: 'Fix', schema: WORK })

return { tuned, reviews, fixed }
