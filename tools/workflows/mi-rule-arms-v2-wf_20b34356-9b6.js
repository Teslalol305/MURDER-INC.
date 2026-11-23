export const meta = {
  name: 'mi-rule-arms-v2',
  description: 'Main character round 2: the first-person bare tattooed arms brought to next-gen (skin shading, tattoos, hand forms and grips on the rebuilt guns), the remaining face and body faults, an independent re-review',
  phases: [
    { title: 'Review', detail: 'independent fresh renders of arms in first person, face and body; graded faults' },
    { title: 'Rebuild', detail: 'fix the faults, arms first' },
    { title: 'Re-review', detail: 'independent grade after the rebuild' },
  ],
}
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'
const HEAD = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a browser first-person shooter owned by the user, being REBUILT in Unreal Engine 5.9 with photoreal graphics; art is authored in Blender by Python and exported as GLB on the UE5 mannequin skeleton. The user's standing instruction (verbatim): "Make sure the guns and characters and all elements are being rebuilt to look realistic and very detailed textures and animations the entire game needs to feel next gen". The player character Rule is a likeness of the man in the user's reference photo art/out/ref/main_character_look.jpg (git-ignored). The user wrote: "yes this is my business partner we own the likeness so go for full facial realism". Rules: the photo and anything generated from it stay under art/out/ (git-ignored) and are never committed; never write or send the man's name anywhere (files, prompts, requests); do not identify him.
What exists: art/blender/assets/rule.py and _rule_*.py (arms SK_RuleArms bare to the shoulder with tattoos, full body SK_Rule with a generated head and body, bracelet), the gloved first version SK_RuleArms_Gloved (characters.py, _characters_pose.py), the Rule section of art/blender/PROGRESS.md, docs/unreal/CHARACTERS.md, previews art/previews/rule_*.jpg, private comparison pictures under art/out/gen/rule/. The two earlier rounds' known weaknesses are listed at the end of the Rule PROGRESS section. The rebuilt guns are art/out/glb/SK_Chopper.glb and SK_Nine.glb (sockets Palm_R and Palm_L; another agent is still improving them: read, never edit, their files).
The lead's own look at art/previews/rule_arms_fp.jpg: the first-person view, which the player sees for the whole game, is the weakest picture of the set. The forearms read as smooth, pale tan plastic with flat lighting, the tattoos are invisible at that distance, the left hand is a mitten with no knuckle or tendon read, the right hand is mostly out of frame, and the composition (gun small in the lower right, arm entering from the bottom) does not look like a modern shooter's viewmodel.
Python with Blender 5.3.0 as a module: ` + PY + ` (4 CPU cores and 15 GB RAM shared with five other agents: one Blender process at a time, Cycles at most 3 threads, free -g first, long jobs in the background with nohup, one render per process). Higgsfield tools by ToolSearch ("select:mcp__Higgsfield__generate_image,mcp__Higgsfield__generate_3d,mcp__Higgsfield__upscale_image,mcp__Higgsfield__jobs_wait,mcp__Higgsfield__balance,mcp__Higgsfield__media_upload,mcp__Higgsfield__media_confirm").`
const GIT = `GIT
Explicit git add paths (never -A), small commits, git push -u origin claude/tender-albattani-5q78qr (if rejected: git pull --no-rebase --no-edit, then push); never force-push, never another branch, never a pull request. Append to your own section of art/blender/PROGRESS.md, never rewrite it. Never commit anything under art/out/. End every commit message with exactly these two lines and no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4`

const REVIEW = (n, prev) => HEAD + `

ROLE: an independent character art director who did not build this. Do not edit the build scripts or exports.` + (prev ? ' A rebuild pass has run and reports: ' + JSON.stringify(prev) + ' Do not take it on trust.' : '') + `
Take FRESH renders (at most 12, 1280 x 720, saved under art/blender/review/sheets/rule_r` + (n + 2) + `/, not committed except the review script; look at each): the first-person view with the CHOPPER and with the NINE at the game's first-person field of view (presentation data in unreal/MurderInc/Content/Data/presentation.json and docs/unreal/ANIMATION.md describe the camera; use a 1920 x 1080 frame with the game's hip and aimed placement) in the README's day rig AND in the open shade under the El; close-ups of each hand (back, palm, fist on the grip); each forearm tattoo against the photo; the face at 1 m and 3 m against the photo (private side-by-side only under art/out/); the full body in two poses.
Judge against a current AAA first-person shooter's hands and arms at the first-person camera (the bar: skin with subsurface scattering, visible pores and fine hair, tendon and knuckle definition, veins, nails, believable grip contact with no gaps or intersections), and the face against the photo.
Reply through the structured output: grades 1-5 for arms_fp, hands, tattoos, face_likeness, body; faults (part, wrong, fix), most visible in play first; overall (at most 100 words).`
const R_SCHEMA = { type: 'object', properties: { arms_fp: { type: 'number' }, hands: { type: 'number' }, tattoos: { type: 'number' }, face_likeness: { type: 'number' }, body: { type: 'number' }, faults: { type: 'array', items: { type: 'object', properties: { part: { type: 'string' }, wrong: { type: 'string' }, fix: { type: 'string' } }, required: ['part', 'wrong', 'fix'] } }, overall: { type: 'string' } }, required: ['arms_fp', 'hands', 'face_likeness', 'faults', 'overall'] }

const FIX = (rev) => HEAD + '\n\n' + GIT + `

GENERATION: the user approved spending Higgsfield credits ("spend all the higgsfield credits you need"); spend at most 200 in this pass, never let the balance fall below 2,500, preflight with get_cost where offered, record every generation privately under art/out/gen/rule/. Never put the man's name in a prompt.

ROLE: the character artist who owns Rule, rebuild pass. An independent art director reviewed Rule:
` + JSON.stringify(rev, null, 1) + `
Fix every fault, the first-person arms and hands first (that is what the player sees all game). Expected directions unless you find better: skin shading that reads in first person (subsurface radius and colour for his deep warm skin, a detail normal for pores and fine creases at a scale that survives at 30 to 60 cm, a cavity and roughness map so knuckles and creases catch light, fine arm hair as cards or a strand-like normal, veins on the back of the hand and forearm); tattoos as healed ink under the skin with correct size and contrast so they read at first-person distance; hand forms with real knuckle, tendon and thenar definition and grips authored per gun (CHOPPER pistol grip and handguard, NINE two-handed grip) with palm contact and no gaps; a viewmodel framing for the preview that matches the game's camera. Then the remaining face and body faults. Re-export through the pipeline's validation; re-render the committed previews art/previews/rule_*.jpg after the last change (look at each) and add rule_fp_nine.jpg. Update CHARACTERS.md if anything the Unreal import needs changes (slot names, the nail slot, the silver material) and your PROGRESS section.
Reply through the structured output: summary (at most 200 words), credits_spent, fixed, not_fixed, previews.`
const F_SCHEMA = { type: 'object', properties: { summary: { type: 'string' }, credits_spent: { type: 'number' }, fixed: { type: 'array', items: { type: 'string' } }, not_fixed: { type: 'array', items: { type: 'string' } }, previews: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'credits_spent', 'fixed', 'not_fixed'] }

phase('Review')
const r1 = await agent(REVIEW(1, null), { label: 'rule:review', phase: 'Review', schema: R_SCHEMA, effort: 'high', model: 'opus' })
if (!r1) return { r1: null }
log('review: arms ' + r1.arms_fp + ', hands ' + r1.hands + ', face ' + r1.face_likeness)
phase('Rebuild')
const f1 = await agent(FIX(r1), { label: 'rule:rebuild', phase: 'Rebuild', schema: F_SCHEMA, effort: 'high', model: 'opus' })
if (!f1) return { r1, f1: null }
phase('Re-review')
const r2 = await agent(REVIEW(2, { summary: f1.summary, fixed: f1.fixed, not_fixed: f1.not_fixed }), { label: 'rule:review-2', phase: 'Re-review', schema: R_SCHEMA, effort: 'high', model: 'opus' })
return { first: { arms_fp: r1.arms_fp, hands: r1.hands, tattoos: r1.tattoos, face: r1.face_likeness, body: r1.body }, rebuild: f1, final: r2 }
