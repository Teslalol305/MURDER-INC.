export const meta = {
  name: 'mi-art-weapons-buzzard',
  description: 'Blender: the first-person hero guns (CHOPPER, NINE) with moving parts and 4K textures, magazines, casings, the enemy weapons, then the Buzzard drone',
  phases: [
    { title: 'Weapons', detail: 'CHOPPER and NINE as skinned meshes with moving parts, magazines, casings, Goon SMG and pipe' },
    { title: 'Buzzard', detail: 'the armed quadcopter: six bones, rotor blur, bolt, wreck pieces' },
  ],
}

const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'
const BRANCH = 'claude/tender-albattani-5q78qr'

const CONTEXT = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a browser first-person shooter (three.js) owned by the user that is being REBUILT in Unreal Engine 5.9 with photoreal graphics. Art is authored in Blender by Python scripts (reproducible, reviewable) and exported as GLB for Unreal. Setting: Hollis, Queens: Jamaica Avenue under a riveted steel elevated train line, a hot clear summer afternoon by default.
The user's standing instruction for this stage: the guns, the characters and every other element must look realistic, with very detailed textures and animation; the whole game has to feel next-gen. The user also pays for every token: read selectively, do not redo work that exists, and spend the effort where the camera looks.`

const PIPE = `START HERE
Read art/blender/README.md (conventions, helper reference, how to add a family) and the last two sections of art/blender/PROGRESS.md. The library is art/blender/mi/ (scene, geo, mat, bake, export, render, steel), the command line is art/blender/build.py, the families are art/blender/assets/*.py. The closest example to your task is the gameplay half of assets/props.py: hero props with unique baked texture sets. Follow the conventions of the README exactly (axes, names, outputs, validation).
Other agents are working in this checkout right now (a furniture and signs agent in art/blender/assets, a character agent that builds on the rig code, Unreal agents elsewhere): you may ADD functions and modules to art/blender/mi/, but never change the behaviour of an existing function and never edit another family's file.

ENVIRONMENT
Python with Blender 5.3.0 as a module: ` + PY + ` (import bpy; numpy and pillow installed). CPU only, 4 cores shared with the other agents: Cycles on CPU with at most 3 threads; start long bakes and renders in the background and poll them instead of blocking. Check the running bpy module rather than trusting memory of older Blender versions. No internet except art/scans/fetch.py for catalogued Poly Haven files (art/scans/sets.json lists scanned metal, wood, plastic, rubber and fabric sets; downloaded ones are under art/out/textures/). Write only under art/. Look at every image you render (Read tool).

GIT
Commit your own work as you go, in small working steps (you may be cut off without warning): git add with explicit paths under art/blender/ and art/previews/ (never git add -A: other agents have unfinished files here), git commit, git push -u origin ` + BRANCH + `; on index.lock wait a few seconds and retry; never force-push, never touch another branch, never open a pull request. art/out/ is git-ignored and stays so. End every commit message with exactly these two lines and put no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4
Keep a section of your own in art/blender/PROGRESS.md current: what is done, the exact next step.`

const REPLY = `Reply through the structured output: summary (at most 150 words), files, previews, assets (exported names with triangle counts and texture sizes), known_weaknesses (honest, most visible first).`

const WEAPONS = CONTEXT + '\n\n' + PIPE + `

YOUR TASK: the family art/blender/assets/weapons.py

Briefs: docs/unreal/spec/assets/weapons.json, entries weapon_chopper, weapon_chopper_magazine, weapon_nine, weapon_nine_magazine, weapon_casing_rifle, weapon_casing_pistol; docs/unreal/spec/assets/characters.json, entries goon_smg and goon_pipe. Each brief gives dimensions, parts, pivots, travel distances, sockets and colours measured from the web game: keep those numbers exactly (sight alignment, hand positions and the reload animation are built on them) and add the real-world detail a brief does not list. For how the guns sit on screen read the viewmodel and sight parts of docs/unreal/spec/02-weapons-combat.md (search "viewmodel"). No maker's marks, real trademarks or real serial formats anywhere; small fictional markings (selector positions, a fictional proof mark) are welcome.

FIRST, within your first half hour: a small module art/blender/mi/rig.py for skinned assets (build an armature from a list of named bones with pivots and parents, bind mesh parts rigidly or with given weights, export a skinned GLB through the pipeline's exporter, validate it by importing the file into a fresh scene and posing bones), committed and pushed: the character agent and the agent after you depend on it.

Quality bar. The CHOPPER and the NINE are on screen for the whole game, 25 to 60 cm from the camera on a 4K display, turning in the light as the player moves. They are the most looked-at assets in the game and must stand comparison with current AAA first-person weapons.
- Geometry: the full mechanical detail of the real class of weapon, modelled: pins with their heads, rivets, screws with slots, stamped ribs and dimples, weld seams, sight ears and notches, serrations, vents and slots cut through with the barrel or the bolt carrier visible inside, a bored barrel with a crowned muzzle, a hollow magazine well, magazines with feed lips, follower and the visible top round, the ejection port with what lies behind it, sling loops, grip checkering (as geometry or as baked normal detail: decide by what holds up at 30 cm and say which), laminate plies at the cut ends of the wood. Every edge bevelled at its real radius (0.2 to 1 mm) with weighted normals: no razor edges, no faceted cylinders (at least 32 sides where a silhouette shows). Budgets: CHOPPER up to about 150,000 triangles, NINE up to about 90,000, magazines 15,000 each, a casing 600, the Goon SMG 25,000, the pipe 3,000.
- Rig: each player gun is ONE skinned GLB whose bones are its rigid moving parts, every vertex weighted 1.0 to exactly one bone: CHOPPER body (root), bolt (carrier and charging handle), trigger, selector, magazine (an attach bone at the gun origin for the separate magazine mesh); NINE frame (root), slide, barrel, trigger, hammer, slide_stop, magazine. Add socket bones without vertices named exactly Muzzle, Eject, SightRear, SightFront, RecoilPivot, MagHinge (CHOPPER), Palm_R, Palm_L at the brief's positions. Give every bone a rest orientation equal to the gun's axes, so that a translation along local X is travel along the bore, and confirm it in the exported file. Magazines, the top rounds, casings, the SMG and the pipe are static GLBs with the origins the briefs give.
- Textures: unique baked sets, 4K for each player gun (T_Chopper_*, T_Nine_*: BC, N in the README's convention, ORM, and E for the faintly self-lit sight dots), 2K for magazines and the SMG, 1K for the pipe, 512 for casings. Uniform texel density, no visible seams on flat faces, mirroring only where both halves can never be seen together. Author the surfaces as layered, believable wear, not uniform noise: bluing worn to bright steel on edges and where hands, slings and holsters rub (drive it from bevel, curvature and ambient-occlusion masks), oil sheen and fingerprints in the roughness, fine scratches along the direction of handling, carbon at the muzzle and the ejection port, dust in the recesses, laminated wood with ply lines and chipped varnish at the corners, brushed stainless steel with directional micro-scratches on the slide flats, a polished gold trigger, brass with a scorched mouth.
- Proof: the pipeline's export validation for every asset; for each player gun import the exported GLB into a fresh scene and pose the bones (bolt back by its travel, trigger pulled, magazine rocked out; slide locked back, barrel tilted, hammer down) to prove pivots and weights.

Previews in art/previews/ (1280 x 720, at most 300 kB each; look at each; at most 12 renders in total; two self-review rounds, fixing the worst visible fault each round): weapons_chopper_hero.jpg and weapons_nine_hero.jpg (three-quarter view, studio-like HDRI lighting, shallow depth of field), weapons_chopper_fp.jpg and weapons_nine_fp.jpg (through a first-person camera with the vertical field of view and the viewmodel pose of the spec, on the day rig), weapons_parts.jpg (both guns posed open from the re-imported GLBs, magazines beside them), weapons_wire.jpg (clay with wire overlay), weapons_enemy.jpg (SMG and pipe).

Order: rig.py; the CHOPPER and its magazine complete with textures and previews before the NINE; then the NINE; then casings; then the SMG and the pipe. Add the family row to the README.

` + REPLY

const BUZZARD = CONTEXT + '\n\n' + PIPE + `

YOUR TASK: the family art/blender/assets/buzzard.py

Briefs: docs/unreal/spec/assets/characters.json, entries buzzard, buzzard_rotor_blur, buzzard_bolt, buzzard_wreck (dimensions, part positions, bones and colours measured from the web game: keep the numbers exactly; mind the orientation rule in the brief: nose toward +X). How it behaves is in docs/unreal/spec/03-enemies.md (search "Buzzard"): it hovers and strafes a few metres from the player, usually seen from below and from the side against the sky and the El, and it is shot down often: the underside, the gun and the rotors matter most.
The agent before you wrote art/blender/mi/rig.py (armatures, rigid skinning, skinned GLB export and its validation) and the weapons family art/blender/assets/weapons.py: read both and reuse them.

Quality bar: a believable heavy-lift commercial quadcopter that a crew has fitted with a gun, at the standard of a current AAA enemy model seen from 4 m.
- Geometry: carbon-fibre arms and plates, motor bells with the windings visible through their vents, two-blade props with real aerofoil twist, landing skids, a battery pack with strap and connector, wiring looms with connectors and zip ties, antennae, a camera gimbal with a glass lens, cooling fins, fasteners, the improvised gun mount (brackets, hose clamps, a feed, a solenoid on the trigger), the navigation lights the brief names. About 120,000 triangles for SK_Buzzard; every edge bevelled, weighted normals.
- Rig: one skinned GLB with the six bones of the brief (body, four props that spin about their hub axes, the gimbal), rigid weights, plus socket bones for the muzzle and the lights; bone rest orientation equal to the model axes.
- Textures: a unique baked 4K set for the drone (BC, N, ORM, E for the lights): carbon weave visible at 1 m, anodised metal, dust, scuffs, oil streaks behind the motors, chipped paint on the oxblood panels; 512 sets for the rotor blur disc (with the radial alpha the brief describes) and the bolt.
- The wreck set (brief buzzard_wreck) as separate static pieces with their own pivots, sharing the drone's set where possible plus a small set for the broken ends.
- Proof: export validation; re-import the GLB and pose the bones (props turned, gimbal pitched).

Previews in art/previews/ (1280 x 720, at most 300 kB each; look at each; at most 8 renders; two self-review rounds): buzzard_hero.jpg (three-quarter from below against a sky HDRI), buzzard_under.jpg (as the player sees it from 5 m), buzzard_detail.jpg (the gun mount and gimbal close), buzzard_wire.jpg, buzzard_wreck.jpg. Add the family row to the README.

` + REPLY

const SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    previews: { type: 'array', items: { type: 'string' } },
    assets: { type: 'array', items: { type: 'string' } },
    known_weaknesses: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'previews', 'known_weaknesses'],
}

phase('Weapons')
const weapons = await agent(WEAPONS, { label: 'art:weapons', phase: 'Weapons', schema: SCHEMA, effort: 'high', model: 'opus' })
phase('Buzzard')
const buzzard = await agent(BUZZARD, { label: 'art:buzzard', phase: 'Buzzard', schema: SCHEMA, effort: 'high', model: 'opus' })
return { weapons, buzzard }
