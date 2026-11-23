export const meta = {
  name: 'mi-art-gaps',
  description: 'Blender: fill the remaining gaps of the street asset library (missing catalogue items, wrecks and lit states of gameplay props, furniture graphics, correctly sized replacements for mismatched scans)',
  phases: [{ title: 'Gaps', detail: 'missing catalogue items, gameplay wrecks and glow masks, furniture graphics' }],
}
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'
const PROMPT = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a browser first-person shooter owned by the user that is being REBUILT in Unreal Engine 5.9 with photoreal graphics. Art is authored in Blender by Python scripts and exported as GLB for Unreal. Setting: Hollis, Queens, around 2000, a hot clear summer afternoon. The user's standing instruction: every element must look realistic, with very detailed textures; the whole game has to feel next-gen. The user pays for every token: read selectively, do not redo what exists.

START HERE
Read art/blender/README.md and the hand-off notes of the props, furniture and signs sections in art/blender/PROGRESS.md (each lists what it left uncovered), then the catalogue docs/unreal/spec/assets/props.json and docs/unreal/spec/05b-props.md for the items below. Library art/blender/mi/ (including texpaint.py for drawn graphics), command line art/blender/build.py, families art/blender/assets/*.py. Other agents are working here right now (weapons.py, buzzard.py, characters.py, vehicles.py, goon_generated.py, and Unreal agents): you may ADD to art/blender/mi/, never change the behaviour of existing functions, and never edit those family files. You may extend props.py, furniture.py and signs.py (their agents have finished) or add a new family file.
Python with Blender 5.3.0 as a module: ` + PY + ` (import bpy). 4 CPU cores shared with other agents: Cycles on CPU with at most 3 threads, long jobs in the background. No internet except art/scans/fetch.py for catalogued Poly Haven files. Write only under art/. Look at every image you render. Vehicles are another agent's job: skip every vehicle_ id.

YOUR TASK, in this order (the level is being assembled in Unreal right now and every missing mesh shows as a grey box):
1. Catalogue ids with no mesh yet: phone_booth (no real marks), traffic_light, planter, tree (a believable street tree with alpha-card or modelled foliage: say which and why), generator, floodlight_stand, porta_potty, vending_machine (fictional brand only), workbench, engine_hoist, compressor, car_lift, the 7.9 m cobra-head street_lamp if the existing SM_Furn_StreetLamp is not it, and any other non-vehicle id of the catalogue that still has no mesh (check the manifest against the catalogue and list what you find).
2. Catalogue items whose scan does not match the briefed size or kind: build properly sized modelled versions (the wire-basket trash can, the 1.8 m bench, the full tool-chest cabinet, the full-size crate and the carton pile, the full food cart with umbrella, menu boards and gear, the 0.77 m tyre, full-length jersey barrier), named as the catalogue names them so the level picks them first.
3. Gameplay props: wrecks of the propane tank and the welding rack, the progress-bar strip and the boombox level meter as emissive pieces, heat-glow emissive masks for the lit states, and fix the master case so the inside of the open lid and the progress track are visible.
4. Graphics that are still flat placeholder colours on the furniture (parking meter dial, newspaper and mail box labels, booth PARK and RATES signs, shed banners, sign plates, bus-stop flag, street-name blades), drawn with mi/texpaint.py with fictional content only; the pawn shop's three gold balls and the barber pole; a clean neutral white painted-steel set so the lot booth and backboard do not read yellow and rusty.
Quality: the same bar as the existing families (real dimensions from the briefs, bevelled edges, tiling scan sets with world-scale UVs and wear masks for large pieces, unique baked sets at 2K for hero pieces seen at arm's length), every asset through the export validation and into the manifest.
Previews in art/previews/ (1280 x 720, at most 300 kB each, at most 8 renders, two self-review rounds): gaps_street.jpg, gaps_yard.jpg, gaps_gameplay.jpg, gaps_graphics.jpg.

GIT
Commit your own work in small steps (you may be cut off without warning): git add with explicit paths under art/blender/ and art/previews/ (never git add -A), commit, git push -u origin claude/tender-albattani-5q78qr; on index.lock wait and retry; never force-push, never another branch, never a pull request. End every commit message with exactly these two lines and put no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4
Keep a section of your own in art/blender/PROGRESS.md current.

Reply through the structured output: summary (at most 200 words), assets (names with triangle counts), previews, still_missing (catalogue ids without a mesh after your work), known_weaknesses (most visible first).`
const SCHEMA = { type: 'object', properties: { summary: { type: 'string' }, assets: { type: 'array', items: { type: 'string' } }, previews: { type: 'array', items: { type: 'string' } }, still_missing: { type: 'array', items: { type: 'string' } }, known_weaknesses: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'previews', 'still_missing', 'known_weaknesses'] }
phase('Gaps')
return await agent(PROMPT, { label: 'art:gaps', phase: 'Gaps', schema: SCHEMA, effort: 'high', model: 'opus' })
