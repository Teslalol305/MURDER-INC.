export const meta = {
  name: 'mi-generated-vehicles-goon',
  description: 'Generated 3D through Higgsfield (credits approved by the user): the eleven vehicles cleaned up in Blender, and one generated Goon to compare with the cloth-simulated one',
  phases: [
    { title: 'Vehicles', detail: 'concept images, image-to-3D, Blender clean-up, glass and wheels, GLB export' },
    { title: 'Goon test', detail: 'one generated masked Goon conformed to the mannequin skeleton for comparison' },
  ],
}

const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'
const BRANCH = 'claude/tender-albattani-5q78qr'

const HEAD = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a browser first-person shooter (three.js) owned by the user that is being REBUILT in Unreal Engine 5.9 with photoreal graphics. Art is authored in Blender by Python scripts and exported as GLB for Unreal. Setting: Hollis, Queens, around the year 2000, a hot clear summer afternoon.
The user's standing instruction: the guns, the characters and every other element must look realistic, with very detailed textures; the whole game has to feel next-gen.

THE BLENDER PIPELINE
Read art/blender/README.md (conventions: axes, pivots, names, texture naming, outputs, manifest, validation) and the end of art/blender/PROGRESS.md. Library art/blender/mi/, command line art/blender/build.py, families art/blender/assets/*.py. Other agents work in this checkout right now (weapons, characters, signs, Unreal agents): you may ADD functions and modules to art/blender/mi/, never change the behaviour of an existing function, never edit another family's file.
Python with Blender 5.3.0 as a module: ` + PY + ` (import bpy; numpy, pillow). 4 CPU cores shared with other agents: Cycles on CPU with at most 3 threads, long jobs in the background. Check the running bpy module rather than trusting memory. Look at every image you make or render (Read tool).

GENERATED 3D (HIGGSFIELD)
The user has approved spending Higgsfield credits on generation for this work ("spend all the credits you need"). Still spend with care: the same credits pay for the GPU box the other agents run on (about 114 per hour). Call mcp__Higgsfield__balance at the start and the end, never let the balance fall below 2,500, preflight every new kind of call once with get_cost: true, do not regenerate something that is already good enough, and report exactly what you spent.
Load tools with ToolSearch ("select:mcp__Higgsfield__generate_image,mcp__Higgsfield__generate_3d,mcp__Higgsfield__jobs_wait,mcp__Higgsfield__models_explore,mcp__Higgsfield__balance,mcp__Higgsfield__get_workflow_instructions,mcp__Higgsfield__media_upload,mcp__Higgsfield__media_confirm,mcp__Higgsfield__remove_background,mcp__Higgsfield__show_generation_by_ids"). First read mcp__Higgsfield__get_workflow_instructions with workflow "photo-to-3d-model": it says which model to use and the exact field names per provider (a wrong field name is dropped silently). Known prices from a preflight: meshy_v7_image_to_3d with texture, PBR, rigging and ultra_mode about 50 credits; hunyuan3d_v3_image_to_3d at 300,000 faces with PBR about 19. Tripo models failed in the tool's own tests: avoid them. Wait for jobs with jobs_wait (timeout_seconds at most 15, repeat). A transport timeout on a submit does not mean it failed: check before resubmitting. Download results with curl into art/out/gen/ (git-ignored). The mesh reproduces the source picture: make the concept picture first with generate_image (plain neutral background, even soft light, no cast shadows, the whole object in frame, no text, no real brands, logos or number plates), look at it, and only then convert it. Never generate a real person's likeness or a real make of car.

GIT
Commit your own work in small steps (you may be cut off without warning): git add with explicit paths under art/blender/ and art/previews/ (never git add -A), git commit, git push -u origin ` + BRANCH + `; on index.lock wait and retry; never force-push, never touch another branch, never open a pull request. art/out/ stays git-ignored. End every commit message with exactly these two lines and put no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4
Keep a section of your own in art/blender/PROGRESS.md current: what is done, what was spent, the exact next step.`

const VEHICLES = HEAD + `

ROLE: vehicle artist. YOUR TASK: the family art/blender/assets/vehicles.py: the eleven vehicles of the block.

Briefs: docs/unreal/spec/assets/props.json, every entry whose id starts with vehicle_ (sedan, taxi, suv, pickup, van, van_vulture, box_truck, burned_car, stripped_car, ipx_truck and ipx_truck_door, motorbike): dimensions, wheelbase, wheel size, colours, liveries and what each is for in play; docs/unreal/spec/05b-props.md for how they are used (most are cover the player stands right next to; the IPX truck is the extraction point with doors that open). Keep the briefed footprint, height, wheelbase and nose direction (+X) exactly: the collision boxes of the level are built on them. Generic vehicles of about the year 2000, no real makes, badges or plates.

Method: generated body, cleaned and completed in Blender.
1. Start with ONE vehicle, the sedan, end to end, and judge it honestly before doing the rest: a concept picture (three-quarter front view; try a second view and the multi-image model if one view gives a poor far side), image-to-3D at a high face count with PBR textures, compare the two providers once on this vehicle and keep the better.
2. Clean-up in Blender by script: scale and align to the briefed dimensions, ground the wheels, origin per the README; separate what must be its own material: body paint (clear-coat in Unreal), glass (a real glass slot: cut the window regions by colour or position, give the glass thickness and put a simple dark interior with seats, dashboard and steering wheel behind it so the car is not a solid lump), tyres and rims (replace fused generated wheels with clean modelled wheels at the briefed size if they are not round and crisp), lamps (emissive-capable slots for head and tail lamps), chrome and black trim. Fix holes, floating bits and the underside (a plain dark chassis is fine). Reduce to a sensible budget (about 80,000 to 150,000 triangles each; Nanite takes it) and keep or rebake the textures at 4K per vehicle in the pipeline's naming (BC, N, ORM, E where lamps glow), removing baked-in lighting as far as you can.
3. The variants come from the base bodies where the briefs say so, not from new generations where avoidable: taxi from the sedan (yellow, roof light, lettering as the brief gives it), the Vulture van from the van (near-black, rear doors opened to the briefed angles as separate pieces), the burned and the stripped car from the sedan shell (these two may be better generated separately: decide by the result), the IPX truck with its two rear door leaves as separate meshes with hinge pivots, in the livery the brief describes.
4. Export every vehicle as GLB with manifest entries and the pipeline's validation; README family row.

Previews in art/previews/ (1280 x 720, at most 300 kB each, at most 14 renders, on the day rig standing on the street family): vehicles_sedan_hero.jpg first (look hard at it: paint, glass, wheels, panel gaps at 2 m), then vehicles_lineup_1.jpg and _2.jpg, vehicles_ipx_truck.jpg (doors open), vehicles_wrecks.jpg, vehicles_close.jpg (a wheel and a door at arm's length), vehicles_wire.jpg. Two self-review rounds, fixing the worst visible fault each time.
If generated bodies do not hold up at 2 m after an honest attempt, say so plainly, keep the best ones, and model the rest by script.

Reply through the structured output: summary (at most 200 words), credits_spent (number), assets (names with triangle counts and how each was made), previews, known_weaknesses (most visible first).`

const GOON = HEAD + `

ROLE: character technical artist. YOUR TASK: one generated Goon, as a comparison for the user to judge.

Another agent is building the three Goons by hand (a body on the UE5 mannequin skeleton with cloth-simulated garments; files art/blender/assets/characters.py, art/blender/mi/rig.py, docs/unreal/CHARACTERS.md as they appear; its mannequin export lands in art/out/epic/). Read what exists of that work first (git log, the files, art/previews/arms_*.jpg and goons_*.jpg if present). Do not edit its files. Licence rule: nothing derived from Epic's mannequin mesh, skeleton or animations may be committed (the repository is public): such files stay under art/out/.

Brief: docs/unreal/spec/assets/characters.json, entry goon_hoodie (masked gunman in a black hoodie with the hood up, the mask and the colours as described; no face is ever shown). Make a full-body concept picture in an A-pose (front view, arms about 40 degrees from the body, fingers apart, plain background, even light), look at it, then image-to-3D with textures, PBR and the A-pose option at a high polygon count; try at most two generations and keep the better one.
Then, in a new file art/blender/assets/goon_generated.py: scale it to the mannequin skeleton's height and joint positions as well as it allows, and bind it to the mannequin skeleton from art/out/epic/ when that export exists (weights transferred from the mannequin mesh; reuse art/blender/mi/rig.py if it is there). If the export is not there yet after you have finished the mesh work, wait for it in a polling loop for at most 40 minutes while you do the renders, then finish without the binding and say so. Pose it with one or two of the exported animation poses if available.
Previews in art/previews/ (1280 x 720, at most 300 kB each, at most 8 renders, on the day rig): goon_generated_hero.jpg, goon_generated_detail.jpg (hood, mask, hands at 3 m and at 1 m), goon_generated_pose.jpg (if bound), goon_generated_wire.jpg. Export SK_Goon_Hoodie_Gen as GLB under art/out/glb/ (skinned if bound).
Judge it honestly against the quality bar "a current AAA enemy seen from 3 to 40 m": texture sharpness, baked-in lighting, hands, how the cloth reads, how it deforms.

Reply through the structured output: summary (at most 200 words, with your verdict: use generated Goons, use them as a base, or do not use them), credits_spent (number), assets, previews, known_weaknesses (most visible first).`

const SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    credits_spent: { type: 'number' },
    assets: { type: 'array', items: { type: 'string' } },
    previews: { type: 'array', items: { type: 'string' } },
    known_weaknesses: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'credits_spent', 'previews', 'known_weaknesses'],
}

const out = await parallel([
  () => agent(VEHICLES, { label: 'art:vehicles', phase: 'Vehicles', schema: SCHEMA, effort: 'high', model: 'opus' }),
  () => agent(GOON, { label: 'chars:goon-generated', phase: 'Goon test', schema: SCHEMA, effort: 'high', model: 'opus' }),
])
return { vehicles: out[0], goon: out[1] }
