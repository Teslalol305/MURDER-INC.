export const meta = {
  name: 'mi-vehicles-verify-fix',
  description: 'Vehicles: an independent review of the exported GLBs from fresh renders (several previews were taken before the last fixes), then a fix pass on what the review finds',
  phases: [
    { title: 'Review', detail: 'fresh turnaround renders of every exported vehicle, fault list per vehicle' },
    { title: 'Fix', detail: 'fix the faults, re-export, final previews' },
    { title: 'Close-up rounds', detail: 'independent close-up review, modelled replacement parts, re-review; up to two rounds' },
  ],
}
const RESUME = `

RESTART NOTE (newer than everything above): an earlier run of this exact task was cut off partway through by a restart of the local machine, not by any fault of the work. Its files are on disk and its commits are on the branch (uncommitted files were committed afterwards as work in progress); your section of the progress notes (art/blender/PROGRESS.md or docs/unreal/PROGRESS.md), git log and the files themselves show how far it got. Local background processes it started are gone and local renders or bakes that were running must be started again; on the GPU box, look at what is still running under your own project before you start anything, and remember the box may have stopped while idle (follow the box-gone procedure if so). Review and continue from where it stopped; do not start over, and do not repeat generation or downloads whose results are already on disk.`
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'
const HEAD = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a browser first-person shooter owned by the user that is being REBUILT in Unreal Engine 5.9 with photoreal graphics. Art is authored in Blender by Python scripts and exported as GLB. Setting: Hollis, Queens, around 2000, a hot clear summer afternoon. The user's standing instruction: every element must look realistic with very detailed textures; the whole game has to feel next-gen. The user pays for every token: read selectively.
Pipeline: art/blender/README.md (conventions), library art/blender/mi/ (gen3d.py holds the clean-up of generated bodies), command line art/blender/build.py, the vehicle family art/blender/assets/vehicles.py, its notes at the end of art/blender/PROGRESS.md, generation records in vehicles_gen.json (find it under art/). Exported GLBs: art/out/glb/SM_Vehicle_*.glb; briefs: docs/unreal/spec/assets/props.json, ids starting with vehicle_ (footprint, height, wheelbase, colours, liveries, what each is for).
Python with Blender 5.3.0 as a module: ` + PY + ` (import bpy). 4 CPU cores shared with other agents: Cycles on CPU with at most 3 threads, long jobs in the background. Look at every image you render (Read tool). Other agents work in this checkout (weapons, buzzard, characters, Unreal): never edit their files; you may add to art/blender/mi/ without changing existing behaviour.`
const GIT = `GIT
Commit your own work in small steps: git add with explicit paths under art/blender/ and art/previews/ (never git add -A), commit, git push -u origin claude/tender-albattani-5q78qr; on index.lock wait and retry; never force-push, never another branch, never a pull request. End every commit message with exactly these two lines and put no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4`

const REVIEW = HEAD + `

ROLE: an independent reviewer who did not build these vehicles. YOUR TASK: judge the thirteen exported vehicle GLBs as they are on disk now. Do not trust the existing previews (three were rendered before later fixes) and do not edit vehicles.py or re-export anything.
Write a small render script of your own under art/blender/review/ that imports each exported GLB into a fresh scene on the day rig (the README's look-dev rig, standing on the street family or a plain asphalt plane) and renders a contact sheet per vehicle: front three-quarter, rear three-quarter, side, and one view from a standing player's eye 2 m away (1280 x 720 per sheet, low samples are fine: these are for judging, not for showing). Thirteen sheets at most, plus up to four close-ups where a fault needs confirming. Also measure each mesh against its brief: length, width, height, wheelbase and wheel diameter from the geometry, nose direction, origin, ground contact, triangle count, material slots, texture sizes.
Judge each vehicle against "a parked car the player takes cover behind in a current AAA shooter, seen from 2 m": silhouette and proportions, squashed or stretched areas, the far side and rear (generated from one view: are they plausible?), panel surfaces (lumps, baked-in light), glass (is every window glass, does it show an interior, is anything that should be glass painted), wheels and arches, lamps, trim, wipers, plates and liveries (no real makes or brands; lettering the brief asks for), doors of the Vulture van and the IPX truck (angles, hinges, what is visible inside), the wrecks.
Reply through the structured output: for every vehicle its name, measured-versus-brief verdict, a grade from 1 (unusable) to 5 (AAA), and its faults, most visible first, each with a concrete suggested fix (a script fix in vehicles.py or gen3d.py, a modelled replacement part, or regenerate the body from a better concept picture); plus sheets (paths of your contact sheets) and overall (at most 120 words).`

const REVIEW_SCHEMA = { type: 'object', properties: {
  vehicles: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, measurements: { type: 'string' }, grade: { type: 'number' }, faults: { type: 'array', items: { type: 'object', properties: { fault: { type: 'string' }, fix: { type: 'string' } }, required: ['fault', 'fix'] } } }, required: ['name', 'grade', 'faults'] } },
  sheets: { type: 'array', items: { type: 'string' } },
  overall: { type: 'string' } }, required: ['vehicles', 'overall'] }

phase('Review')
const review = await agent(REVIEW, { label: 'vehicles:review', phase: 'Review', schema: REVIEW_SCHEMA, effort: 'high', model: 'opus' })
if (!review) return { review: null }
const worst = review.vehicles.filter(v => v.grade < 4 && v.faults.length)
log(review.vehicles.map(v => v.name + ' ' + v.grade).join(', '))

const FIX = HEAD + '\n\n' + GIT + `

GENERATED 3D: the user has approved spending Higgsfield credits on generation for this work. Regenerate a body only where the review says the body itself is the problem and a script cannot fix it: load tools with ToolSearch ("select:mcp__Higgsfield__generate_image,mcp__Higgsfield__generate_3d,mcp__Higgsfield__jobs_wait,mcp__Higgsfield__balance,mcp__Higgsfield__media_upload,mcp__Higgsfield__media_confirm"), follow exactly how vehicles.py and vehicles_gen.json record the earlier generations (same model and fields: Hunyuan won the comparison), never let the balance fall below 2,500, spend at most 250 credits in this pass, and report what you spent. No real makes, badges or plates.

ROLE: vehicle artist. YOUR TASK: fix what an independent review found, most visible faults first, then re-export and show the result.
THE REVIEW (grades 1 to 5; contact sheets under art/blender/review/):
` + JSON.stringify(review.vehicles, null, 1) + `
Reviewer's summary: ` + review.overall + `

Work through the vehicles graded below 4 first, then the remaining faults of the others if time allows. Keep every briefed dimension, wheelbase, nose direction and origin. Typical fixes: correct glass detection per vehicle and give every window real glass with the interior behind it; replace squashed or warped regions (prefer adjusting the warp or regenerating from a concept with the right proportions over stretching); flatten baked-in light in the paint; model wipers, mirrors, door handles, lamps lenses and plates as real parts where the generated ones read as lumps; add tyre sidewall detail; give liveries and lettering proper decal art. Every re-exported vehicle must pass the pipeline's validation and keep its manifest entry.
Final previews in art/previews/ (1280 x 720, at most 300 kB each, at most 10 renders, all taken AFTER the last change): vehicles_sedan_hero.jpg, vehicles_lineup_1.jpg, vehicles_lineup_2.jpg, vehicles_ipx_truck.jpg (doors open, vault visible), vehicles_wrecks.jpg, vehicles_close.jpg (a wheel and a door at arm's length), vehicles_wire.jpg. Update the vehicle notes in art/blender/PROGRESS.md (your own section only: do not rewrite the file).

Reply through the structured output: summary (at most 200 words), credits_spent, fixed (vehicle: what changed), not_fixed (what remains and why), previews.`
const FIX_SCHEMA = { type: 'object', properties: { summary: { type: 'string' }, credits_spent: { type: 'number' }, fixed: { type: 'array', items: { type: 'string' } }, not_fixed: { type: 'array', items: { type: 'string' } }, previews: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'credits_spent', 'fixed', 'not_fixed', 'previews'] }

phase('Fix')
const fix = await agent(FIX + RESUME, { label: 'vehicles:fix', phase: 'Fix', schema: FIX_SCHEMA, effort: 'high', model: 'opus' })

// ---- Round 3 onward: close-up quality (added after the first fix pass was judged "fine at street distance, not next-gen close up")
const LOCAL = `
LOCAL MACHINE: 4 CPU cores and 15 GB RAM shared with five other running agents. Run ONE Blender process at a time, Cycles with at most 3 threads, and check free -g first (wait if less than 4 GB is available). Long jobs in the background with nohup; a batch of renders in one process was killed for memory before: one render per process.`
const REVIEW_N = (n, prev) => REVIEW + LOCAL + `

ROUND NOTE (newer than everything above): this is review round ` + n + `. A fix pass has run since the earlier review` + (prev ? ` and reported:
FIXED: ` + JSON.stringify(prev.fixed) + `
NOT FIXED: ` + JSON.stringify(prev.not_fixed) : '') + `
Do not take that report on trust. Reuse the earlier review scripts under art/blender/review/ and write this round's sheets to art/blender/review/sheets/vehicles_r` + n + `/. The owner's verdict on the last previews was: acceptable at street distance, NOT acceptable close up (a crumpled crease at the sedan's front door and wing seam, flat toy-like hubcaps, hazy lamp units with stray coloured patches, cropped oversized plates, box interiors, torn edges at glass). So this round the judging distance is arm's length as well as 2 m: for every DISTINCT body (sedan and taxi share one; van and Vulture share one) add four close-ups: a front wheel with its arch, a headlamp with the grille corner, the front door seam with mirror and handle, and the interior through the driver's glass. The player takes cover against these vehicles and looks straight at them from 0.5 m. Grade 4 means "passes at arm's length in a current AAA shooter"; grade honestly and name what would lift each one to 4.`
const FIX_N = (n, rev) => HEAD + LOCAL + '\n\n' + GIT + `

GENERATED 3D: the user has approved spending Higgsfield credits on generation for this work ("spend all the higgsfield credits you need"). Load tools with ToolSearch ("select:mcp__Higgsfield__generate_image,mcp__Higgsfield__generate_3d,mcp__Higgsfield__jobs_wait,mcp__Higgsfield__balance,mcp__Higgsfield__media_upload,mcp__Higgsfield__media_confirm"), follow how vehicles.py and vehicles_gen.json record the earlier generations, never let the balance fall below 2,500, spend at most 250 credits in this pass, and report what you spent. No real makes, badges or plates.

ROLE: vehicle artist, close-up pass ` + n + `. YOUR TASK: lift every vehicle the review grades below 4 to "passes at arm's length", most-seen vehicles first (sedan/taxi, SUV, pickup, van/Vulture, IPX truck, box truck, wrecks).
THE REVIEW (grades 1 to 5; contact sheets and close-ups under art/blender/review/sheets/vehicles_r` + n + `/):
` + JSON.stringify(rev.vehicles, null, 1) + `
Reviewer's summary: ` + rev.overall + `

METHOD (decided by the lead after two passes of patching generated surfaces): stop repairing generated detail and REPLACE it. Keep a generated body only as the large painted shell. Everything a close camera reads becomes a modelled part built by script in art/blender/mi/ and shared across vehicles with per-vehicle parameters:
- Wheels: delete the generated wheels entirely; model tyre (rounded shoulder, tread blocks or ribs in geometry or a strong normal map, sidewall ribs and raised generic lettering), rim with real depth (steel wheel with slots and a pressed hubcap for the sedan/taxi/van, alloys for the SUV, plain steel with lug nuts for trucks), brake disc or drum visible behind, lug nuts, valve stem.
- Lamps: modelled housings with a reflector bowl, bulb, clear or ribbed lens with thickness and a chrome or body-colour bezel; amber indicators; red tail clusters with separate lens sections. No painted lamp faces left.
- Glass and interior: every window a clean modelled pane in a rubber seal; behind it a modelled dashboard with instrument binnacle and vents, steering wheel with column, seats with headrests and seam lines, door cards, rear shelf, floor; the taxi gets its partition and meter.
- Panel lines: where the generated shell has a crumpled or wandering seam (the sedan's front door / wing seam is the worst), flatten the region (project it to a smooth fitted surface or regenerate the body from a flat-lit, shadowless, single-colour three-quarter concept picture) and then cut clean shut lines as real grooves 4 to 6 mm wide with a dark inner face; door handles, mirrors on stalks with mirror glass, wipers as arm and blade, fuel flap, antenna, rubbing strips and bumpers as modelled parts.
- Paint: one clean material per body with clear coat, fine orange-peel normal, dirt gradient rising from the sills, dust in recesses, stone chips at the nose; no baked highlights or shadows in the base colour (low-pass or repaint the base colour to a flat hue wherever lighting was baked in).
- Plates: correct size (US 305 x 152 mm), centred in a recess with a frame, text fitted inside the border, fictitious.
Keep every briefed dimension, wheelbase, nose direction (+X; the pipeline's nose assert must keep passing) and origin; stay inside the triangle budgets of the README (raise a vehicle to at most 180k triangles if the modelled parts need it and say so); texture sets at the sizes the README gives. Every re-exported vehicle must pass the pipeline's validation and keep its manifest entry.
Final previews in art/previews/ (1280 x 720, at most 300 kB each, at most 12 renders, all taken AFTER the last change, one render per process): the seven existing names (vehicles_sedan_hero, vehicles_lineup_1, vehicles_lineup_2, vehicles_ipx_truck with the sun on the open vault, vehicles_wrecks, vehicles_close, vehicles_wire) plus vehicles_wheel.jpg, vehicles_lamp.jpg, vehicles_interior.jpg (through the driver's glass) and vehicles_taxi.jpg. Look at each one and be honest about what still fails. Append to the vehicle notes in art/blender/PROGRESS.md (your own section only: never rewrite the file).

Reply through the structured output: summary (at most 200 words), credits_spent, fixed (vehicle: what changed), not_fixed (what remains and why), previews.`

phase('Close-up rounds')
let lastFix = fix, lastReview = null
const rounds = []
for (let n = 3; n <= 4; n++) {
  const rev = await agent(REVIEW_N(n, lastFix), { label: 'vehicles:review-' + n, phase: 'Close-up rounds', schema: REVIEW_SCHEMA, effort: 'high', model: 'opus' })
  if (!rev) break
  lastReview = rev
  log('round ' + n + ': ' + rev.vehicles.map(v => v.name.replace('SM_Vehicle_', '') + ' ' + v.grade).join(', '))
  if (rev.vehicles.every(v => v.grade >= 4)) { rounds.push({ n, review: rev }); break }
  const f = await agent(FIX_N(n, rev), { label: 'vehicles:fix-' + n, phase: 'Close-up rounds', schema: FIX_SCHEMA, effort: 'high', model: 'opus' })
  rounds.push({ n, review: rev, fix: f })
  if (!f) break
  lastFix = f
}
const finalReview = (rounds.length && rounds[rounds.length - 1].fix)
  ? await agent(REVIEW_N(5, lastFix), { label: 'vehicles:review-final', phase: 'Close-up rounds', schema: REVIEW_SCHEMA, effort: 'high', model: 'opus' })
  : lastReview
return { first_review_grades: review.vehicles.map(v => ({ name: v.name, grade: v.grade })), first_fix: fix, rounds, final_grades: finalReview ? finalReview.vehicles.map(v => ({ name: v.name, grade: v.grade, top_fault: v.faults[0] ? v.faults[0].fault : null })) : null, final_overall: finalReview ? finalReview.overall : null }
