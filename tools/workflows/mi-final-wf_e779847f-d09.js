export const meta = {
  name: 'mi-final',
  description: 'Final launch build: box set-up, build and full tests of the polished game, an independent play-through, fixes, the final Eagle 3D Streaming package uploaded with LAUNCH.md updated, and an independent release check',
  phases: [
    { title: 'Build and test', detail: 'set up the new box, build, full suite, polish shots' },
    { title: 'Play-through', detail: 'independent play of both modes' },
    { title: 'Fix', detail: 'fix what the play-through finds' },
    { title: 'Package', detail: 'final cloud package, upload, LAUNCH.md' },
    { title: 'Release check', detail: 'independent check of the package and the hand-off' },
  ],
}
const BOXDIR = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/box'
const HEAD = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", rebuilt in Unreal Engine 5.9 (unreal/MurderInc), launching on the owner's IPX.exchange Game OS website through Eagle 3D Streaming. READ FIRST: docs/unreal/RESUME.md (especially section 8: the exact next steps), docs/unreal/DECISIONS.md, docs/LAUNCH.md, the latest sections of docs/unreal/PROGRESS.md (polish pass, polish fix pass, cloud build, demo build) and docs/unreal/BOX.md. The owner wants a fully functional game to launch; favour fixes that remove visible breaks in normal play; work in small committed steps (usage and credit limits have cut jobs off before); keep the automation tests and golden replays passing.
THE BOX: a NEW box was just rented after the credits ran out (Higgsfield balance now about 5,000). mcp__Higgsfield__gpu_rental_exec (ToolSearch "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__gpu_rental,mcp__Higgsfield__gpu_rent,mcp__Higgsfield__media_upload,mcp__Higgsfield__media_confirm"); session_id = the single line of ` + BOXDIR + `/session (cat it before the first call and whenever a call fails). If gpu_rental says it is still starting, poll every 30 s until working; then run /project/ue/bin/ensure-setup.sh every 30 s until it prints SETUP-DONE before anything else (running processes and /tmp from the old box are gone; /project survived). Stop your own processes by process id. Never call gpu_rental_stop. IF THE BOX IS GONE (a call says not running AND gpu_rental reports status ended): cat the session file again and use a new id if there is one; otherwise take the first line of ` + BOXDIR + `/keys not in ` + BOXDIR + `/used, append it to used, call mcp__Higgsfield__gpu_rent with exactly gpu_type "RTX-PRO-6000", gpu_count 1, kind "desktop", cpu 16, memory_gib 64, max_credits_per_hour 114, idempotency_key = that line; poll until working, write the id into the session file, run ensure-setup.sh until SETUP-DONE. If renting fails, stop and report. Do not call any Higgsfield generation tool.
LICENCE: never commit pack, Epic or likeness content; deliver packages only to the owner's Higgsfield storage; never write the partner's name anywhere.
GIT: explicit git add paths (never -A); push to claude/tender-albattani-5q78qr (if rejected: git pull --no-rebase --no-edit, then push); never force-push, never a pull request; never edit src/; append to your own PROGRESS section; pictures under docs/unreal/shots/ need git add -f. End every commit message with exactly these two lines and no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4`
const R = { type: 'object', properties: { summary: { type: 'string' }, fixed: { type: 'array', items: { type: 'string' } }, not_fixed: { type: 'array', items: { type: 'string' } }, tests: { type: 'string' }, pictures: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'fixed', 'not_fixed', 'tests'] }
const P = { type: 'object', properties: { launch_ready: { type: 'boolean' }, problems: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['where', 'problem', 'fix'] } } }, required: ['launch_ready', 'problems'] }

phase('Build and test')
const b = await agent(HEAD + `

ROLE: senior Unreal engineer. Do RESUME section 8 steps 1 and 2: wait for the box and set it up; in /project/ue/repo-gameplay run sync.sh and build.sh (the 36-card flash pool, commit 9e55db3, was never compiled), then tools/box/test.sh MurderInc (all tests and golden replays) and fix any failure; then fp/polish-shots.sh and look at every picture. Also fix the two known faults: the first frame of every run faces a trash can 1.1 m away (move prop 270 in build_block.py or turn the PlayerStart so the first frame looks clearly down the street), and the 7 brick building backs and the skyline towers that read as blockout (dress them with the facade kit's window and frame modules or give the window material real recessed frames, glass and interior; rebuild L_Block). Retake the polish pictures that change. Reply through the structured output.`, { label: 'final:build', phase: 'Build and test', schema: R, effort: 'high', model: 'opus' })
if (!b) return { b: null }

phase('Play-through')
const c = await agent(HEAD + `

ROLE: an independent player and reviewer; change nothing. The engineer reports: ` + JSON.stringify(b) + `
In the gameplay clone (your own editor on MCP port 8005; stop it by process id), play through the set-up flow into a Story run to extraction (run-test bot or scripted input) and a Hold the Block run of three waves, taking at most twelve pictures from the player's eye (docs/unreal/shots/review/, not committed). List everything that would embarrass the owner at a public launch, most visible first: grey boxes, missing art, effects not showing, clipping, floating objects, broken animation, HUD or menu faults, crashes, log errors. Run the full suite. Reply through the structured output.`, { label: 'final:play', phase: 'Play-through', schema: P, effort: 'high', model: 'opus' })

let f = null
if (c && c.problems.length) {
  phase('Fix')
  f = await agent(HEAD + `

ROLE: senior Unreal engineer, fix pass. An independent play-through found: ` + JSON.stringify(c) + `
Fix every problem a player would see, most visible first; rebuild, full suite green, retake the pictures a fix changes, commit. Reply through the structured output.`, { label: 'final:fix', phase: 'Fix', schema: R, effort: 'high', model: 'opus' })
}

phase('Package')
const pk = await agent(HEAD + `

ROLE: release engineer. Do RESUME section 8 step 4: from the gameplay clone (no editor of it may be running: check ps), package.sh snapshot then tools/box/cloud/package-cloud.sh all (with the 800 MB texture pool); confirm the package starts on the box with the click-to-play card and reaches a run; upload the parts to the owner's Higgsfield storage as before; verify by downloading all parts, joining and checking the sha256 and unzip -t; then update docs/LAUNCH.md: remove the 'do not upload' warning, put the new part links and sha256 in, and keep the rest accurate. Commit. Reply through the structured output: summary, package_urls (in order), sha256, size_mb, tests (the suite line of the packaged commit), launch_md_updated (true or false).`, { label: 'final:package', phase: 'Package', schema: { type: 'object', properties: { summary: { type: 'string' }, package_urls: { type: 'array', items: { type: 'string' } }, sha256: { type: 'string' }, size_mb: { type: 'number' }, tests: { type: 'string' }, launch_md_updated: { type: 'boolean' } }, required: ['summary', 'package_urls', 'sha256', 'launch_md_updated'] }, effort: 'high', model: 'opus' })
if (!pk) return { b, c, f, pk: null }

phase('Release check')
const rc = await agent(HEAD + `

ROLE: independent release checker; change nothing. The release engineer reports: ` + JSON.stringify(pk) + `
Download every part, join in order, check the sha256 against the one in docs/LAUNCH.md and unzip -t; check the zip layout against E3DS's Linux rules as LAUNCH.md states them (the .sh at the root and its name, Pixel Streaming 2 plugin files present, only one streaming plugin); confirm the package was made from the commit whose suite passed and contains the polish fixes (the rebuilt L_Block, the flash pool); read LAUNCH.md start to finish as the non-technical owner would and list anything unclear or wrong; confirm no pack, Epic or likeness content was committed. Reply through the structured output: ok (true or false), problems (each with a fix).`, { label: 'final:release-check', phase: 'Release check', schema: { type: 'object', properties: { ok: { type: 'boolean' }, problems: { type: 'array', items: { type: 'string' } } }, required: ['ok', 'problems'] }, effort: 'high', model: 'opus' })
return { build: b, playthrough: c, fix: f, package: pk, release_check: rc }
