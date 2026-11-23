export const meta = {
  name: 'mi-loadout-build',
  description: 'Build the home-screen flow the user asked for (pick a character, pick four guns, add attachments, pick level and game style) in Unreal C++ from docs/unreal/LOADOUT.md, then an independent review and a fix pass',
  phases: [
    { title: 'Build', detail: 'LOADOUT.md build order steps 1-4 and 6-11 in the gameplay clone, tests green' },
    { title: 'Review', detail: 'independent read-and-run review against the user request and the design' },
    { title: 'Fix', detail: 'fix every problem found, with tests' },
  ],
}
const BOXDIR = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/box'
const BRANCH = 'claude/tender-albattani-5q78qr'
const HEAD = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a browser first-person shooter (three.js, src/, the ground truth for gameplay, untouched) owned by the user, being REBUILT in Unreal Engine 5.9 (unreal/MurderInc, C++ plus JSON data in Content/Data, class prefix MI, automation tests MurderInc.*). The user's standing instruction: everything must look and feel next-gen. The user pays for every token and every minute of the GPU box: read selectively, do not redo work that exists.

THE USER'S REQUEST THIS WORK SERVES (verbatim): "include all the guns and animations in the sprite pack i downloaded as load out options where a user can pick 4 guns to carry into the game from the home screen. the flow should be. Pick a charachter-pick load out and add weapon attachments then pick level and game style"
The design is done and reviewed: docs/unreal/LOADOUT.md (read it fully; it is the specification: screens, data, rules, parity with the web game, tests, build order in section 9, defaults for the open questions in section 10 which stand until the user answers). Data: unreal/MurderInc/Content/Data/{guns.json, attachments.json, crew.json, frontend.json, frontend_text.json, levels.json}. The game as built: docs/unreal/GAMEPLAY.md (slices 1 and 2: weapons, player, enemies, flow, menus, save, settings; 18 gameplay tests pass, five whole web-game runs replay with 0 mismatches), docs/unreal/PROGRESS.md, docs/unreal/AUDIO.md (an audio agent owns Source/MurderInc/Audio and its tests; UMIAudioSubsystem::SetCharacter and SetOptions and the suppressed-shot flag are its hooks for you to call), docs/unreal/ANIMATION.md.

PARALLEL WORK YOU MUST NOT COLLIDE WITH: an animation agent is importing the pack's rifle variants and attachments with sockets on the box in /project/ue/animpack (build-order step 5) and will fill guns.json variants.*.mesh and attachments.json presentation.mesh and statuses: do not edit those fields; read them when they appear. An audio agent works in Source/MurderInc/Audio, its tests, Content/Data/voice.json and audio*.json and the box clone /project/ue/repo-audio: do not edit those. A level agent owns build_block.py and L_Block. Art agents work under art/. A clean checkout has no pack meshes (licence: never committed), so the code must run, test and be playable with template stand-ins and show pack guns as not ready exactly as LOADOUT.md 6.7 says.

THE BOX
docs/unreal/BOX.md is the manual (read it first: the exec loop, 45-second calls, setsid nohup, headless editor, sync.sh / build.sh / test.sh / editor.sh / play-shots.sh per clone, pictures back through Higgsfield storage, every pitfall found so far). Reach the box with mcp__Higgsfield__gpu_rental_exec (ToolSearch "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__gpu_rental,mcp__Higgsfield__gpu_rent,mcp__Higgsfield__media_upload,mcp__Higgsfield__media_confirm"); session_id = the single line of ` + BOXDIR + `/session (cat it before your first call and whenever a call fails). Your clone is the gameplay clone /project/ue/repo-gameplay (MCP port 8001). Never start, stop or rebuild another agent's clone or editor; pkill -x UnrealEditor kills them all, so stop yours by process id. Run free -g before heavy work. Never call gpu_rental_stop. IF THE BOX IS GONE (a call says not running AND gpu_rental reports status ended): cat the session file again and use a new id if there is one; otherwise take the first line of ` + BOXDIR + `/keys not in ` + BOXDIR + `/used, append it to used, call mcp__Higgsfield__gpu_rent with exactly gpu_type "RTX-PRO-6000", gpu_count 1, kind "desktop", cpu 16, memory_gib 64, max_credits_per_hour 114, idempotency_key = that line; poll until working, write the id into the session file, run /project/ue/bin/ensure-setup.sh every 30 s until SETUP-DONE, carry on. If no key is left or renting fails, stop and report. Do not call any Higgsfield generation tool.

GIT
Branch ` + BRANCH + ` only; explicit git add paths (never -A); commit small compiled steps; git push -u origin ` + BRANCH + ` (if rejected: git pull --no-rebase --no-edit, then push); never force-push, never a pull request. Append to your own section of docs/unreal/PROGRESS.md, never rewrite the file. Pictures under docs/unreal/shots/ need git add -f. End every commit message with exactly these two lines and no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4`

const BUILD = HEAD + `

ROLE: senior Unreal gameplay and UI engineer (C++), the LOADOUT agent.
YOUR TASK: implement LOADOUT.md section 9 steps 1 to 4 and 6 to 11 in order, each step compiled, tested and committed before the next, with the tests section 8 names (parity tests first: the default set-up must replay the existing golden runs with 0 mismatches, so the web game's behaviour is unchanged when the player takes the default). Step 10's screens: build the whole flow Home -> Crew -> Loadout (rack, pick up to four) -> Workbench (attachments per gun) -> Block & Style (level and mode) -> Briefing -> run, with the 3D stage (AMIShowroom) showing the selected crew member and the gun with its attachments mounted; Slate or UMG built in C++, keyboard, mouse and gamepad, legible at 1080p and 4K; look and type as frontend.json says (it replaces the slice-2 canvas title for this flow). Wire the audio hooks with the one-line calls AUDIO.md names (crew to SetCharacter, options to SetOptions, the silencer to the suppressed-shot flag) where they belong in your code.
Step 12 only as far as clips have landed (ANIMATION.md).
Proof: play-in-editor pictures (docs/unreal/shots/loadout-*.jpg, at most eight, each under 400 kB, look at every one): each screen of the flow, the Workbench with a gun carrying attachments, the four-slot HUD bar and the weapon wheel in a run. Full test suite at the end (test.sh MurderInc): report the line; failures in other agents' tests are noted, not fixed.

Reply through the structured output: summary (at most 200 words), steps (per build-order step: done or not, the tests that cover it, the commit), tests (the final suite line), pictures, open_issues (most important first), handoffs (exact requests to other agents).`
const B_SCHEMA = { type: 'object', properties: { summary: { type: 'string' }, steps: { type: 'array', items: { type: 'string' } }, tests: { type: 'string' }, pictures: { type: 'array', items: { type: 'string' } }, open_issues: { type: 'array', items: { type: 'string' } }, handoffs: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'steps', 'tests', 'open_issues'] }

phase('Build')
const built = await agent(BUILD, { label: 'loadout:build', phase: 'Build', schema: B_SCHEMA, effort: 'high', model: 'opus' })
if (!built) return { built: null }

phase('Review')
const REVIEW = HEAD + `

ROLE: an independent senior reviewer who did not write this code. Do not edit code; you may build and run tests and play-in-editor in /project/ue/repo-gameplay (coordinate: if the builder's editor is still running there, stop nothing of theirs: start your own on a free MCP port such as 8005 only after the builder has finished, which it has). The builder reports:
` + JSON.stringify(built, null, 1) + `
Check, and report only real problems, most serious first, each with where it is and a concrete fix:
- the user's request literally: from the home screen can a player pick a character, then pick up to four guns, then add attachments, then pick a level and a game style, then play with exactly those guns and attachments in effect? Walk it yourself in play-in-editor with keyboard and with gamepad input simulation, and take your own pictures (not committed; save under docs/unreal/shots/review/);
- parity: the default set-up's golden replays still 0 mismatches (run them);
- the rules of LOADOUT.md sections 3, 4 and 7 against the code: attachment stat maths and clamps, four-gun switching and the wheel, the shared bag of rounds, save data and its migration, the resolver; read the tests and say whether each would fail if the rule broke;
- what a clean checkout without the pack shows (pack guns not offered or marked not ready, nothing crashes);
- UI quality: legibility, focus handling, back navigation, nothing overlapping at 16:9 and 21:9 and 4K scale, text from frontend_text.json not hard-coded;
- collisions with other agents' files (git log and diff: did the builder edit audio, level or animation files beyond the allowed one-line hooks).
Reply through the structured output: verdict (at most 120 words), problems (where, problem, fix), sheets.`
const R_SCHEMA = { type: 'object', properties: { verdict: { type: 'string' }, problems: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['where', 'problem', 'fix'] } }, sheets: { type: 'array', items: { type: 'string' } } }, required: ['verdict', 'problems'] }
const review = await agent(REVIEW, { label: 'loadout:review', phase: 'Review', schema: R_SCHEMA, effort: 'high', model: 'opus' })
if (!review || !review.problems.length) return { built, review }
log(review.problems.length + ' problems found')

phase('Fix')
const FIX = HEAD + `

ROLE: the LOADOUT agent, fix pass. An independent reviewer found these problems in your loadout and front-end work:
` + JSON.stringify(review, null, 1) + `
Your build summary, for orientation: ` + built.summary + `
Fix every problem, each rule fix with a test that fails without it (prove that by breaking the rule once and seeing red, then restore). Re-run the full suite and the parity replays, retake any committed picture a fix changes (look at each), update LOADOUT.md where the build departs from the design and GAMEPLAY.md for what is now built, commit. If a problem cannot be fixed, say exactly why.
Reply through the structured output: summary (at most 150 words), fixed, not_fixed, tests (final suite line), pictures.`
const F_SCHEMA = { type: 'object', properties: { summary: { type: 'string' }, fixed: { type: 'array', items: { type: 'string' } }, not_fixed: { type: 'array', items: { type: 'string' } }, tests: { type: 'string' }, pictures: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'fixed', 'not_fixed', 'tests'] }
const fix = await agent(FIX, { label: 'loadout:fix', phase: 'Fix', schema: F_SCHEMA, effort: 'high', model: 'opus' })
return { built, review, fix }
