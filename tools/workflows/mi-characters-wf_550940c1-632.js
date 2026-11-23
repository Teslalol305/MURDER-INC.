export const meta = {
  name: 'mi-characters',
  description: 'Characters on the UE5 mannequin skeleton: the Unreal-Blender round trip proven with the engine animation set, the first-person arms of the player, then the three Goons',
  phases: [
    { title: 'Pipeline and arms', detail: 'scratch Unreal project, mannequin export, round-trip proof, SK_RuleArms with watch and bracelet' },
    { title: 'Goons', detail: 'three masked Goons with draped clothing, skinned to the mannequin, proven with the engine animations' },
  ],
}

const RESUME = `

RESTART NOTE (newer than everything above): an earlier run of this exact task was cut off partway through by a restart of the local machine, not by any fault of the work. Its files are on disk and its commits are on the branch (uncommitted files were committed afterwards as work in progress); your section of the progress notes (art/blender/PROGRESS.md or docs/unreal/PROGRESS.md), git log and the files themselves show how far it got. Local background processes it started are gone and local renders or bakes that were running must be started again; on the GPU box, look at what is still running under your own project before you start anything, and remember the box may have stopped while idle (follow the box-gone procedure if so). Review and continue from where it stopped; do not start over, and do not repeat generation or downloads whose results are already on disk.`
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'
const BRANCH = 'claude/tender-albattani-5q78qr'
const BOXDIR = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/box'

const CONTEXT = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a browser first-person shooter (three.js) owned by the user that is being REBUILT in Unreal Engine 5.9 with photoreal graphics. Art is authored in Blender by Python scripts (reproducible, reviewable) and exported for Unreal. Setting: Hollis, Queens, a hot clear summer afternoon by default.
The user's standing instruction for this stage: the guns, the characters and every other element must look realistic, with very detailed textures and animation; the whole game has to feel next-gen. The user also pays for every token and for every minute of the GPU box: read selectively, do not redo work that exists, and spend the effort where the camera looks.`

const PIPE = `THE BLENDER PIPELINE
Read art/blender/README.md (conventions, helper reference, how to add a family) and the last sections of art/blender/PROGRESS.md. The library is art/blender/mi/ (scene, geo, mat, bake, export, render, steel, and rig.py for skinned assets), the command line is art/blender/build.py, the families are art/blender/assets/*.py; the gameplay half of assets/props.py shows hero assets with unique baked texture sets. Other agents work in this checkout right now (weapons, furniture and signs in art/blender/assets; Unreal agents elsewhere): you may ADD functions and modules to art/blender/mi/, but never change the behaviour of an existing function and never edit another family's file.
Python with Blender 5.3.0 as a module: ` + PY + ` (import bpy; numpy and pillow installed). Locally there are only 4 CPU cores shared with the other agents (Cycles on CPU, at most 3 threads, long jobs in the background). If local CPU time becomes your bottleneck you may install the same bpy on the box (a Python 3.13 virtual environment under /project/ue/bl, which is persistent) and run heavy simulations, bakes and renders there on its GPU: scripts travel by git, results through storage. Check the running bpy module rather than trusting memory of older Blender versions. No internet locally except art/scans/fetch.py for catalogued Poly Haven files (art/scans/sets.json lists scanned fabric, leather, rubber, plastic and metal sets). Look at every image you render (Read tool).`

const BOX = `THE UNREAL BOX
A rented Linux GPU box (one RTX PRO 6000 with 96 GB, 16 cores, 64 GB RAM) with Unreal Engine 5.9.0 at /project/ue/UnrealEngine. It costs the user about 114 credits per hour while it runs. docs/unreal/BOX.md is the source of truth for working on it (the loop, every pitfall and its fix, how pictures are taken, how files travel): read it first, then the scripts in tools/box/ as working examples (seed-content.sh copies template content into a project; shot.sh and mi_shot.py take pictures through the piloted editor viewport; send-art.sh and receive-art move files through the user's Higgsfield storage; lib.sh holds the editor arguments that work here).
Essentials: reach the box with the MCP tool mcp__Higgsfield__gpu_rental_exec (load schemas with ToolSearch, query "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__gpu_rental,mcp__Higgsfield__gpu_rent,mcp__Higgsfield__media_upload,mcp__Higgsfield__media_confirm"). Its session_id is the single line of the local file ` + BOXDIR + `/session (cat it before your first box call, and again whenever a box call fails: the box may have been replaced). Each call runs one bash command as root in a fresh shell and must finish within 45 seconds (timeout_s 50 at most): start anything longer with setsid nohup ... > /project/ue/logs/<name>.log 2>&1 & and poll its log. Never use pkill -f or pgrep -f (they match your own shell). The engine and the editor refuse to run as root: su ue4 -c "...". Windows do not work: always headless (-RenderOffscreen -unattended -nosplash -NoSound) through /project/ue/bin/run-editor.sh, which adds the cache arguments every editor or UnrealEditor-Cmd start needs on this box. /project is persistent but a slow network file system (no recursive find or du over big trees); everything else is lost when the box stops.
Other agents share the box right now: a LEVEL agent (clone /project/ue/repo, its editor on MCP port 8000) and a GAMEPLAY agent (clone /project/ue/repo-gameplay, port 8001). You work only in your own scratch project /project/ue/chars with MCP port 8002 (/project/ue/bin/mcp.py is shared and may assume port 8000: pass a port or use a copy of your own, do not change its default) and never start, stop, kill or rebuild anything of theirs: pkill -x UnrealEditor kills EVERY editor on the box, so record the process id of what you start and stop it by that id. Run free -g before a heavy process and keep the box total under about 50 GB.
Never call gpu_rental_stop. IF THE BOX IS GONE (a box call says the box is not running AND mcp__Higgsfield__gpu_rental for its session id reports status ended; this has happened twice, cause unknown): (1) cat ` + BOXDIR + `/session again: if it now holds another id, another agent has already replaced the box: use that id. (2) Otherwise rent the replacement yourself. The user has approved exactly this box at this price and nothing else: take the first line of ` + BOXDIR + `/keys that is not in ` + BOXDIR + `/used, append it to ` + BOXDIR + `/used, then call mcp__Higgsfield__gpu_rent with exactly gpu_type "RTX-PRO-6000", gpu_count 1, kind "desktop", cpu 16, memory_gib 64, max_credits_per_hour 114 and idempotency_key = that line (the same key always returns the same box). Poll mcp__Higgsfield__gpu_rental every 30 seconds until status is working, write the new id into ` + BOXDIR + `/session, then run /project/ue/bin/ensure-setup.sh on the box every 30 seconds until it prints SETUP-DONE. /project survived; running processes and /tmp did not: restart what you need and carry on. (3) If no unused key is left or the rent call fails, stop and report. Any other failure is not a reason to rent.
Files travel through the user's Higgsfield storage. Box to local: mcp__Higgsfield__media_upload with a filename gives upload_url, media_id and url; PUT the file from the box (/project/ue/bin/put.sh <file> <upload_url> <content_type>); mcp__Higgsfield__media_confirm with the media_id (type "file" for archives, "image" for pictures); then curl the url locally. Local to box: the same with the PUT done locally (tools/box/send-art.sh shows it). Pictures as JPEG of at most 1920 x 1080, and few of them: each costs several thousand tokens.
Do not call any Higgsfield generation tool (generate_image, generate_3d, generate_video, generate_audio and the like): they spend the user's credits and the user has not approved that.`

const RULES = `WHY THE MANNEQUIN SKELETON
The engine on the box ships a motion-captured animation set on the UE5 mannequin skeleton (SK_Mannequin) under /project/ue/UnrealEngine/Templates/TemplateResources/High/Characters/Content/Mannequins: Meshes (the mannequin skeletal meshes), Rigs, and Anims with Rifle (aimed idle, aim offsets, walk and jog in eight directions, jump, fire, reload, equip, dry fire, eight hit reactions), Pistol (the same set), Unarmed (walk, jog, three attacks, a charged attack, dash) and Death (six directions). Templates/TemplateResources/Standard/Weapons holds the template rifle and pistol. Every human in the game (the player's first-person arms, the three Goons) is a skeletal mesh built in Blender ON THAT SKELETON, so these animations drive it without retargeting. The game project already carries this content under its Content/Characters and Content/Weapons (tools/box/seed-content.sh).

LICENCE RULE
Epic's content may be used and modified for this Unreal game but not published, and this repository is public: nothing derived from the mannequin meshes, skeleton or animations (FBX, GLB, .blend, baked or posed copies) may be committed. Keep such files under art/out/ (git-ignored) and on the box. Scripts, documents and JPEG previews of our own characters are fine.

GIT
Commit your own work as you go, in small working steps (you may be cut off without warning): git add with explicit paths (art/blender/..., art/previews/..., docs/unreal/CHARACTERS.md, your own new files in tools/box/, your sections of docs/unreal/BOX.md; pictures under docs/unreal/shots/ need git add -f because the root .gitignore ignores shots/), never git add -A (other agents have unfinished files here), git commit, git push -u origin ` + BRANCH + `; on index.lock wait a few seconds and retry; never force-push, never touch another branch, never open a pull request. End every commit message with exactly these two lines and put no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4
Keep a section of your own in art/blender/PROGRESS.md current: what is done, the exact next step.`

const HEAD = CONTEXT + '\n\n' + PIPE + '\n\n' + BOX + '\n\n' + RULES

const ARMS = HEAD + `

ROLE: senior character technical artist. YOUR TASK: the character pipeline and the player's arms.

1. A scratch Unreal project of your own on the box, /project/ue/chars (start from /project/ue/Blank or the engine's TP_Blank; enable the plugins you need, for example the glTF exporter and the MCP plugins the game project enables), with the template's Characters and Weapons content copied in. Use commandlets (UnrealEditor-Cmd ... -run=pythonscript -script=...) or your own headless editor on MCP port 8002.
2. Export from Unreal what Blender needs, to /project/ue/chars/export and then to art/out/epic/ in the local checkout: the mannequin skeletal mesh with its full skeleton in a format Blender imports with the bone rest transforms intact (try the engine's glTF exporter first, FBX as the fallback); as animation clips or baked poses: the aimed idle of the rifle and of the pistol, the rifle and pistol reloads, one jog cycle, one attack, one death; and the template rifle and pistol meshes (they show where the hands sit).
3. ROUND-TRIP PROOF, before any modelling: import the mannequin into Blender and export it again untouched through the exact path our characters will take; import that file in the scratch project onto the EXISTING SK_Mannequin skeleton asset (no new skeleton); play the rifle jog and the rifle reload on it next to the original and bring a picture back from the box. The two must match pose for pose: no twisted limbs, no offset, no scale or axis error, fingers included. Iterate on the export and import settings until they do, then write the settings that work into art/blender/README.md and a new docs/unreal/CHARACTERS.md. Everything later stands on this proof: do not move on without it.
4. Library and family: build on art/blender/mi/rig.py (the weapons agent is writing it right now: armatures, rigid skinning, skinned GLB export, re-import validation; it should be committed by the time you finish step 3: git log shows it; ADD what characters need: weight transfer from a source mesh, smooth skinning, pose import; never change the behaviour of its existing functions). Family file art/blender/assets/characters.py.
5. The player's arms, SK_RuleArms (brief character_rule_arms in docs/unreal/spec/assets/weapons.json, with character_rule_watch and character_rule_bracelet; the web source is src/weapon/arms.js). They are the only part of the player that is ever seen, 30 to 60 cm from the camera for the whole game: a hero asset that must stand comparison with current AAA first-person arms.
 - On the mannequin skeleton with full finger articulation. Take proportions and skin weights from the mannequin's own arms and hands (its fingers are correctly weighted) and rebuild the surface as a real arm in a real glove: an anatomical forearm (the turn of radius and ulna, the wrist bones, tendons, a hint of veins), skin with pores, fine creases, soft mottling and forearm hair suggested in normal and roughness; the glove built from panels with raised seams and visible stitches, a moulded knuckle bar, a wrist strap with its closure, fingertip pads, a suede palm, compression wrinkles at every finger joint and at the wrist. Decide from the reference poses and the first-person field of view how far up the arm the mesh must go: nothing may end in view.
 - Material slots: skin (it gets a subsurface profile in Unreal), glove leather, glove suede and rubber; unique baked sets, 4K for the gloves and 4K for the skin (BC, N, ORM).
 - Watch and bracelet as separate static meshes with real detail (case, bezel, crown, a dial with batons and hands under glass, a link band; gold links), each with an attach bone or socket on the wrist the brief names.
 - About 120,000 triangles for both arms; weighted normals; no faceting on the fingers at 30 cm.
6. Pose test in Blender with the reference poses of step 2: the arms through a first-person camera (field of view and viewmodel pose from docs/unreal/spec/02-weapons-combat.md, search "viewmodel") holding the CHOPPER and the NINE (the guns are being modelled right now in art/blender/assets/weapons.py: use their GLBs from art/out/glb if they exist by then, otherwise boxes of the briefed size at the briefed palm positions), plus a fist, a trigger pull and an open hand to judge finger deformation. Fix the worst faults (two rounds).
7. Proof in Unreal: import SK_RuleArms into the scratch project on SK_Mannequin, play the rifle aimed idle and the rifle reload, one picture back, looked at.

Previews in art/previews/ (1280 x 720, at most 300 kB each, at most 12 renders): arms_hero.jpg (both arms, studio light), arms_fp_chopper.jpg, arms_fp_nine.jpg, arms_hands.jpg (fist, trigger, open), arms_wire.jpg; the Unreal pictures as docs/unreal/shots/chars-roundtrip.jpg and chars-arms.jpg. Stop your editor (by process id) when you finish.

Reply through the structured output: summary (at most 200 words), works (what you verified, each with its evidence), files, previews, known_weaknesses (most visible first), open_issues.`

const GOONS = HEAD + `

ROLE: senior character artist and technical artist. YOUR TASK: the three Goons.

The agent before you built the character pipeline: read docs/unreal/CHARACTERS.md, the character rows of art/blender/README.md, art/blender/mi/rig.py and art/blender/assets/characters.py, and look at art/previews/arms_*.jpg and docs/unreal/shots/chars-*.jpg. The mannequin export is in art/out/epic/; the scratch Unreal project is /project/ue/chars on the box.

Briefs: docs/unreal/spec/assets/characters.json, entries goon_hoodie, goon_puffer, goon_tracksuit (the body shared by all three, each outfit, the head coverings, the colours), and docs/unreal/spec/03-enemies.md for how they are seen (search "Goon": distances, how many at once, what they do). They are masked: no face is ever shown. Where the brief's joint heights differ from the mannequin skeleton, the skeleton wins (the animations depend on it): build to the skeleton, record the difference, and note the uniform scale Unreal should apply to reach the briefed height.

Quality bar: current AAA enemy characters seen from 3 to 40 m, up to a dozen on screen.
- A shared body on the mannequin skeleton under the clothes (only what can show: neck, wrists, hands, ankles, as the briefs say).
- Clothing that reads as real garments, each its own mesh with thickness at hems, cuffs and collars: drape it over the body with Blender's cloth simulation in the A-pose so the folds at elbows, knees, waist, hood and trouser breaks are real (fall back to modelled folds only where simulation fails, and say where); real loft in the quilting of the puffer; ribbed cuffs and waistbands; zips with teeth and pulls; drawstrings with aglets; the pouch pocket; the stripes; sneakers with soles, tread, eyelets and laces; the hood, beanie, cap, ski mask and wrap-around glasses of the briefs.
- Skin weights transferred from the mannequin body and cleaned, so the garments follow the limbs without poke-through in the jog, reload, hit and death poses (test with the poses in art/out/epic/).
- Textures: unique baked sets per outfit, 4K for body and clothes, 2K for head and accessories (BC, N, ORM), from scanned fabric sets where the catalogue art/scans/sets.json has them (fetch what you need with art/scans/fetch.py), with the weave visible at 3 m, pilling, dirt at cuffs and knees, wear on the sneakers.
- About 70,000 triangles per Goon; one skinned GLB each (SK_Goon_Hoodie, SK_Goon_Puffer, SK_Goon_Tracksuit), origin on the ground between the feet, facing as the brief says.

Proof in Unreal: import the three into the scratch project on SK_Mannequin; the hoodie Goon playing the rifle jog, the reload, one hit reaction and one death, the other two in the aimed idle; pictures back (docs/unreal/shots/chars-goons-1.jpg to -3.jpg), looked at; fix the worst deformation and poke-through faults (two rounds).
Previews in art/previews/ (1280 x 720, at most 300 kB each, at most 12 renders): goons_lineup.jpg (the three side by side on the day rig), goons_hoodie_hero.jpg, goons_detail.jpg (hood, mask and hands close), goons_poses.jpg (jog, aim, death), goons_wire.jpg.
Update docs/unreal/CHARACTERS.md (what exists, how to add an outfit, the animation assets and what each is for, known weaknesses) and the README family row. Stop your editor (by process id) when you finish.

Reply through the structured output: summary (at most 200 words), works (what you verified, each with its evidence), files, previews, known_weaknesses (most visible first), open_issues.`

const SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    works: { type: 'array', items: { type: 'string' } },
    files: { type: 'array', items: { type: 'string' } },
    previews: { type: 'array', items: { type: 'string' } },
    known_weaknesses: { type: 'array', items: { type: 'string' } },
    open_issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'works', 'known_weaknesses'],
}

phase('Pipeline and arms')
const arms = await agent(ARMS, { label: 'chars:pipeline-arms', phase: 'Pipeline and arms', schema: SCHEMA, effort: 'high', model: 'opus' })
phase('Goons')
const goons = await agent(GOONS + RESUME, { label: 'chars:goons', phase: 'Goons', schema: SCHEMA, effort: 'high', model: 'opus' })
return { arms, goons }
