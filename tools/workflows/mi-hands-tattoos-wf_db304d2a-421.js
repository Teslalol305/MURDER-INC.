export const meta = {
  name: 'mi-hands-tattoos',
  description: 'Fix the main character hands and forearm tattoos as the player sees them in the game: find why the tattoos and skin detail do not show in Unreal, fix the skin and tattoos, reshape the hands and their grip on each gun, independent check from in-game pictures, fix pass',
  phases: [
    { title: 'Fix', detail: 'diagnose in Unreal, fix texture/material/mesh, hands and grips, re-import into the game, in-game pictures' },
    { title: 'Check', detail: 'independent in-game check of hands and tattoos against the photo' },
    { title: 'Fix 2', detail: 'fix what the check finds' },
  ],
}
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'
const BOXDIR = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/box'
const HEAD = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a browser shooter being rebuilt in Unreal Engine 5.9 with next-gen realism (read docs/unreal/RESUME.md first: rules, the box, where things are). The player character Rule is a likeness of the man in the owner's reference photo art/out/ref/main_character_look.jpg (git-ignored; never commit it or anything generated from it, never write or send the man's name anywhere, do not identify him). His bare first-person arms are SK_RuleArms (art/blender/assets/rule.py, _rule_tex.py with the tattoo charts and skin texels, _characters_pose.py, _rule_gate.py; exports art/out/glb/SK_RuleArms.glb and art/out/textures/RuleArms_Skin/; docs/unreal/CHARACTERS.md; the Rule section of art/blender/PROGRESS.md; previews art/previews/rule_*.jpg). In the game they are imported by tools/box/fp/import-chars.sh arms (tools/box/fp/mi_fp_import.py, which uses tools/box/chars/mi_chars.py) and drawn by the first-person rig (docs/unreal/GAMEPLAY.md sections 15-19, docs/unreal/ANIMATION.md section 9). In-game pictures: docs/unreal/shots/fp-*.jpg, taken with tools/box/fp/fp-shots.sh.

THE OWNER'S REQUEST (verbatim): "fix the hands and arm tatoos"
What the in-game pictures show (docs/unreal/shots/fp-hip-sun.jpg, fp-goon.jpg, fp-irons.jpg, fp-hip-el.jpg): the forearm and hand read as a smooth, uniform orange-tan tube with NO visible tattoos at all, no pores, veins, knuckle or tendon detail; the hand is a mitten-like shape wrapped round the handguard; under the El the sunlit forearm reads orange-red. In Blender previews the tattoos and detail exist, so suspect the Unreal side first: is the RuleArms_Skin base colour actually bound to the material in the game project (or is the material falling back to a flat colour), are the UVs the ones the texture was baked for, is the texture streaming at a low mip, is the subsurface profile (SP_RuleSkin) washing out the albedo, is sRGB set right on base colour and off on normal/ORM, is the normal map's green channel right for Unreal. Find the real cause with evidence (inspect the material instance's parameters and textures in the editor, a flat unlit debug view of base colour on the arm, a close camera on the forearm), then fix it at the source (the import script, the material, or the texture build).
Then make the tattoos right against the photo: the right forearm's lettering by the elbow and the script line beside it, the left forearm's numerals; healed blue-black ink under the skin, sized and placed as in the photo, readable at first-person distance (the forearm is 20-50 cm from the eye) without looking like a sticker. And the hands: real hand forms (knuckles, tendons on the back of the hand, thenar pad, nails with a lighter free edge, creases at the joints), his skin tone (deep warm brown, not orange; check against the photo under neutral light), and a grip on each gun with palm contact and fingers wrapped round the handguard or grip with no gaps or intersections, as the pack's own animations hold the rifle (the pack clips drive the arms; fix the mesh and weights so the hands deform well in those clips, and use the hand IK the rig already has for the NINE).

TOOLS
Blender: ` + PY + ` (bpy 5.3.0; 4 CPU cores shared: one Blender process at a time, Cycles at most 3 threads, free -g first, long jobs with nohup, one render per process).
The box: mcp__Higgsfield__gpu_rental_exec (ToolSearch "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__gpu_rental,mcp__Higgsfield__gpu_rent,mcp__Higgsfield__media_upload,mcp__Higgsfield__media_confirm"); session_id = the single line of ` + BOXDIR + `/session; docs/unreal/BOX.md is the manual. Test material and texture fixes first in the characters scratch project /project/ue/chars (MCP 8002). The game project is the gameplay clone /project/ue/repo-gameplay (MCP 8001), where a first-person fix agent may still be working: before you start an editor there, check with ps whether an UnrealEditor for repo-gameplay is running; if so, wait and poll every few minutes, and never stop it. Re-import into the game only with import-chars.sh arms, then take your in-game pictures with fp-shots.sh. Stop your own editors by process id. Never call gpu_rental_stop. IF THE BOX IS GONE (a call says not running AND gpu_rental reports status ended): cat the session file again and use a new id if there is one; otherwise take the first line of ` + BOXDIR + `/keys not in ` + BOXDIR + `/used, append it to used, call mcp__Higgsfield__gpu_rent with exactly gpu_type "RTX-PRO-6000", gpu_count 1, kind "desktop", cpu 16, memory_gib 64, max_credits_per_hour 114, idempotency_key = that line; poll until working, write the id into the session file, run /project/ue/bin/ensure-setup.sh every 30 s until SETUP-DONE.
Higgsfield generation is allowed if a texture source helps (for example a high-resolution skin or ink detail): at most 100 credits, balance never below 2,500, never the man's name in a prompt, never upload the photo or anything derived from it to a generator.
GIT: explicit git add paths (never -A); push to claude/tender-albattani-5q78qr (if rejected: git pull --no-rebase --no-edit, then push); never force-push, never a pull request; append to your own PROGRESS sections; never edit src/ (the web game stays untouched). Pictures under docs/unreal/shots/ need git add -f. End every commit message with exactly these two lines and no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4`

const FIX = HEAD + `

ROLE: character and technical artist. Do the work above: diagnose, fix, re-export, re-import into the game, and prove it with in-game pictures (docs/unreal/shots/fp-arms-*.jpg, at most six, look at each): hip in sun, hip under the El, aimed through irons, a close look at each forearm's tattoos (use the inspect clip or a pose where the forearm turns toward the camera), the hand on the NINE. Also re-render art/previews/rule_arms_fp.jpg and rule_hands.jpg. Update CHARACTERS.md with the cause you found and the fix.
Reply through the structured output: cause (what made the tattoos and detail disappear in the game, with evidence), summary (at most 150 words), fixed, not_fixed, pictures, credits_spent.`
const F_SCHEMA = { type: 'object', properties: { cause: { type: 'string' }, summary: { type: 'string' }, fixed: { type: 'array', items: { type: 'string' } }, not_fixed: { type: 'array', items: { type: 'string' } }, pictures: { type: 'array', items: { type: 'string' } }, credits_spent: { type: 'number' } }, required: ['cause', 'summary', 'fixed', 'not_fixed'] }

phase('Fix')
const RESUME = `

RESTART NOTE (newer than everything above): an earlier run of this exact task was cut off by a usage limit after a lot of work. Its commits are on the branch (git log: 'Arms:' and 'fp-arms-shots:' commits, the work-in-progress commit bfd17cd) and the Rule section of art/blender/PROGRESS.md says how far it got: tattoos moved to the thumb side and darkened, numerals unmirrored, knuckle and tendon forms, tiling skin grain, game skin on the Standard Subsurface model, nails 0.6 mm proud, forearm close-up shots in progress. Also read art/blender/review/rule_r3_final_review.json (an independent review with measured grip gaps). Continue from where it stopped; do not start over. Check on the box what is still running under your projects before you start anything (the box may have been replaced: cat the session file).`
const f1 = await agent(FIX + RESUME, { label: 'arms:fix', phase: 'Fix', schema: F_SCHEMA, effort: 'high', model: 'opus' })
if (!f1) return { f1: null }

phase('Check')
const CHECK = HEAD + `

ROLE: an independent art director who did not do this work. Do not edit anything. The artist reports: ` + JSON.stringify(f1) + `
Take your OWN in-game pictures in the gameplay clone (same coordination rule: wait if another editor of repo-gameplay is running; use MCP port 8005 for yours; stop it by process id), at most eight, saved under docs/unreal/shots/review/ (not committed): the poses the artist used plus mid-reload and inspect frames. Compare the tattoos against the photo (a private side-by-side under art/out/ only) and judge hands against a current AAA first-person shooter (skin with pores and fine hair, knuckle and tendon definition, nails, contact on the gun with no gaps or intersections, believable deformation in the clips).
Reply through the structured output: grade_hands 1-5, grade_tattoos 1-5, verdict (at most 100 words), problems (where, problem, fix) most visible first.`
const check = await agent(CHECK, { label: 'arms:check', phase: 'Check', schema: { type: 'object', properties: { grade_hands: { type: 'number' }, grade_tattoos: { type: 'number' }, verdict: { type: 'string' }, problems: { type: 'array', items: { type: 'object', properties: { where: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' } }, required: ['where', 'problem', 'fix'] } } }, required: ['grade_hands', 'grade_tattoos', 'verdict', 'problems'] }, effort: 'high', model: 'opus' })
if (!check || !check.problems.length) return { f1, check }
log('check: hands ' + check.grade_hands + ', tattoos ' + check.grade_tattoos)

phase('Fix 2')
const f2 = await agent(HEAD + `

ROLE: the same character and technical artist, second pass. An independent art director checked your work in the game:
` + JSON.stringify(check, null, 1) + `
Your first-pass summary: ` + f1.summary + `
Fix every problem, re-import into the game, retake the committed fp-arms-*.jpg pictures a fix changes (look at each), update CHARACTERS.md and PROGRESS, commit.
Reply through the structured output: cause (unchanged or refined), summary (at most 150 words), fixed, not_fixed, pictures, credits_spent.`, { label: 'arms:fix-2', phase: 'Fix 2', schema: F_SCHEMA, effort: 'high', model: 'opus' })
return { f1, check, f2 }
