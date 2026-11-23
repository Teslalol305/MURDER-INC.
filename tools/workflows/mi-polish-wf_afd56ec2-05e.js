export const meta = {
  name: 'mi-polish',
  description: 'Polish round before launch: remove the grey blocking boxes from the street, make the player muzzle flash and tracers visible, CHOPPER finger contact, and anything else an in-play review finds that breaks the illusion; independent check',
  phases: [
    { title: 'Polish', detail: 'grey boxes, player flash and tracers, CHOPPER fingers, play frames' },
    { title: 'Check', detail: 'independent play-through of both modes with pictures' },
    { title: 'Fix', detail: 'fix what the check finds' },
  ],
}
const BOXDIR = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/box'
const HEAD = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", rebuilt in Unreal Engine 5.9 (unreal/MurderInc), about to launch on the owner's website by streaming. Read docs/unreal/RESUME.md and docs/unreal/DECISIONS.md first, then GAMEPLAY.md sections 15-19, the latest sections of docs/unreal/PROGRESS.md (first person, the hands and tattoos pass, the demo build) and docs/unreal/BOX.md. The owner wants to launch it as a fully functional game soon: favour fixes that remove visible breaks in normal play over deep art work; work in small committed steps (weekly usage limits have cut jobs off), and keep the 105 automation tests and all golden replays passing.
VISIBLE BREAKS KNOWN NOW (docs/unreal/shots/fp-arms-hip-sun.jpg and fp-arms-nine.jpg show the first two):
1. Big untextured grey blocking boxes in L_Block: the level's colliders are drawn as grey boxes wherever no art covers them (a large one sits right in front of the player at the start, by the El). The level builder unreal/MurderInc/Content/Python/build_block.py (no level agent is running now: you own it for this task) draws colliders by tag; give every visible collider real art from the existing catalogue (art/out/placements, Content/Data/art_catalogue.json, the structures and props families: concrete barriers, plywood hoardings, dumpsters, crates, jersey barriers, parked vehicles, building backs) or hide it when it sits inside art, and make sure no plain grey box is left anywhere a player can see in either mode. Also the two grey-box car colliders without art.
2. The player's own muzzle flash and tracers never appear on screen (the Goons' do). PROGRESS has the investigation so far (the flash cards are 38-44 cm from the eye, set visible, sized right, yet invisible; a test card in the same material placed at 40 cm also fails). Find the real cause (near clip of the first-person view, the first-person render path or depth, the translucent material's depth test against the viewmodel, a lighting channel) and fix it; prove it with a frozen frame 0.01-0.03 s after a shot.
3. CHOPPER support fingers stand 11-20 mm off the handguard and the firing fist can close in the air (art/blender/review/rule_r3_final_review.json): add per-gun finger corrections in the first-person anim instance so the fingers touch the gun in the pack clips' hold, aim and fire.
4. Anything else you see in normal play that breaks the illusion (template leftovers, floating objects, popping, clipping at the near plane, HUD overlaps).
THE BOX: mcp__Higgsfield__gpu_rental_exec (ToolSearch "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__gpu_rental,mcp__Higgsfield__gpu_rent,mcp__Higgsfield__media_upload,mcp__Higgsfield__media_confirm"); session_id = the single line of ` + BOXDIR + `/session. Work in the gameplay clone /project/ue/repo-gameplay (the hands agent has finished; build.sh first, since the demo agent's C++ changes were synced but not built). A release engineer is packaging the cloud build in /project/ue/repo-release: never touch that copy or its processes. Stop your own processes by process id. Never call gpu_rental_stop. IF THE BOX IS GONE (a call says not running AND gpu_rental reports status ended): cat the session file again and use a new id if there is one; otherwise take the first line of ` + BOXDIR + `/keys not in ` + BOXDIR + `/used, append it to used, call mcp__Higgsfield__gpu_rent with exactly gpu_type "RTX-PRO-6000", gpu_count 1, kind "desktop", cpu 16, memory_gib 64, max_credits_per_hour 114, idempotency_key = that line; poll until working, write the id into the session file, run /project/ue/bin/ensure-setup.sh every 30 s until SETUP-DONE. Do not call any Higgsfield generation tool.
LICENCE: never commit pack, Epic or likeness content; never write the partner's name anywhere.
GIT: explicit git add paths (never -A); push to claude/tender-albattani-5q78qr (if rejected: git pull --no-rebase --no-edit, then push); never force-push, never a pull request; never edit src/; append to your own PROGRESS section; pictures under docs/unreal/shots/ need git add -f. End every commit message with exactly these two lines and no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4`

const R = { type: 'object', properties: { summary: { type: 'string' }, fixed: { type: 'array', items: { type: 'string' } }, not_fixed: { type: 'array', items: { type: 'string' } }, tests: { type: 'string' }, pictures: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'fixed', 'not_fixed', 'tests'] }
phase('Polish')
const p = await agent(HEAD + `

ROLE: senior Unreal engineer and level artist, POLISH agent. Fix 1 to 4 above, rebuild L_Block in the gameplay clone, run the full suite, and prove it with play-in-editor pictures from the player's eye (docs/unreal/shots/polish-*.jpg, at most eight, look at each): the start position, the avenue under the El, the lot by the IPX truck, a Hold the Block wave position, a frame just after a shot with the flash and tracer, the CHOPPER aimed. Reply through the structured output.`, { label: 'polish:build', phase: 'Polish', schema: R, effort: 'high', model: 'opus' })
if (!p) return { p: null }
phase('Check')
const c = await agent(HEAD + `

ROLE: an independent player and reviewer; change nothing. The polish agent reports: ` + JSON.stringify(p) + `
In the gameplay clone (your own editor on MCP port 8005; stop it by process id), play through: the set-up flow into a Story run to extraction (use the run-test bot or scripted input), and a Hold the Block run of three waves, taking at most twelve pictures from the player's eye (docs/unreal/shots/review/, not committed). List everything that would embarrass the owner at a public launch, most visible first: grey boxes, missing art, effects not showing, clipping, floating objects, broken animation, HUD or menu faults, crashes, errors in the log. Run the full suite. Reply through the structured output: launch_ready (true or false), problems (where, problem, fix).`, { label: 'polish:check', phase: 'Check', schema: { type: 'object', properties: { launch_ready: { type: 'boolean' }, problems: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['where', 'problem', 'fix'] } } }, required: ['launch_ready', 'problems'] }, effort: 'high', model: 'opus' })
if (!c || !c.problems.length) return { p, c }
phase('Fix')
const f = await agent(HEAD + `

ROLE: the POLISH agent, fix pass. An independent play-through found: ` + JSON.stringify(c) + `
Fix every problem that a player would see, most visible first; rebuild, full suite, retake the polish-*.jpg pictures a fix changes, commit. Reply through the structured output.`, { label: 'polish:fix', phase: 'Fix', schema: R, effort: 'high', model: 'opus' })
return { p, c, f }
