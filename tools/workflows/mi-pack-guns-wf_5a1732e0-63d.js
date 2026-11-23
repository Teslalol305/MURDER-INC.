export const meta = {
  name: 'mi-pack-guns',
  description: 'Turn the purchased rifle pack into the loadout guns: three rifle lengths with open and folded stocks, every attachment with sockets, icons, the first-person camera recipe, then an independent check and a fix pass',
  phases: [
    { title: 'Build', detail: 'import variants and parts, socket pass, attachments mounted, first-person recipe, data update' },
    { title: 'Check', detail: 'independent check on the box from fresh pictures, then fixes' },
  ],
}
const PY = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/bl/venv/bin/python'
const BOXDIR = '/tmp/claude-0/-home-user-MURDER-INC-/143426e3-80dd-56d9-8134-6c37a8961002/scratchpad/box'
const HEAD = `PROJECT CONTEXT
/home/user/MURDER-INC. holds "MURDER INC.", a browser first-person shooter (three.js) owned by the user that is being REBUILT in Unreal Engine 5.9 with photoreal graphics. The user's standing instruction: the guns, the characters and their animation must look realistic and very detailed; the whole game has to feel next-gen. The user pays for every token and every minute of the GPU box: read selectively, do not redo work that exists.

THE USER'S REQUEST THIS WORK SERVES (verbatim): "include all the guns and animations in the sprite pack i downloaded as load out options where a user can pick 4 guns to carry into the game from the home screen. the flow should be. Pick a charachter-pick load out and add weapon attachments then pick level and game style"
The pack is the "Tactical FPS Animation Pack - Assault Rifle" (Infima Games, Fab standard licence), unpacked on the box under /project/ue/packs/tactical-rifle/ (FBX_Files_TacticalAssaultRifle/{Animations, Meshes 29 files, Props, Textures} and Blender_Source_Files_TacticalAssaultRifle/). It holds ONE M4-style rifle in Short / Default / Extended handguard lengths, each with the stock open or folded, plus attachments: angled grip, vertical grip, laser, scope, folding front and rear sights, silencer, standard and transparent magazines; and first- and third-person clips.
The design that decides what these become is docs/unreal/LOADOUT.md: read "Read this first", section 0, 3.2, 3.3, 4.8, 5 and all of section 6 (6.2 is the work order for the import, 6.3 the attachment needs, 6.6 the requests addressed to "the animation agent": that is you). The data it fills: unreal/MurderInc/Content/Data/guns.json (guns shorty, stick, stretch with variants) and attachments.json. A previous agent imported the animations and wrote docs/unreal/ANIMATION.md (read it all: facts about the pack's rig, the project /project/ue/animpack, the scripts under tools/box/anim/, the pitfalls it hit) and docs/unreal/BOX.md (how to work on the box).
LICENCE RULE: the pack may be used in the game but not published, and this repository is public: no file from the pack or derived from it (FBX, GLB, .blend, .uasset, textures, and icons or silhouettes rendered from the pack's meshes alone) may be committed. They stay on the box under /project/ue/ and locally under art/out/ (git-ignored). The same holds for Epic's mannequin content. Scripts, documents, data files and a few JPEG proof pictures of the game scene are fine.

THE BOX
A rented Linux GPU box (RTX PRO 6000 96 GB, 16 cores, 64 GB RAM) with Unreal Engine 5.9.0 at /project/ue/UnrealEngine; about 114 credits per hour. Reach it with mcp__Higgsfield__gpu_rental_exec (ToolSearch "select:mcp__Higgsfield__gpu_rental_exec,mcp__Higgsfield__gpu_rental,mcp__Higgsfield__gpu_rent,mcp__Higgsfield__media_upload,mcp__Higgsfield__media_confirm"); its session_id is the single line of the local file ` + BOXDIR + `/session (cat it before your first call and again whenever a call fails). One bash command per call as root in a fresh shell, finished within 45 seconds (timeout_s 50 at most): longer work with setsid nohup ... > /project/ue/logs/<name>.log 2>&1 & and polling. Never pkill -f or pgrep -f. The engine refuses root: su ue4 -c "...". Headless only (-RenderOffscreen -unattended -nosplash -NoSound) through /project/ue/bin/run-editor.sh. /project is persistent but slow (no recursive find or du over big trees).
Other agents share the box: LEVEL (/project/ue/repo, MCP port 8000), GAMEPLAY (/project/ue/repo-gameplay, 8001), CHARACTER (/project/ue/chars, 8002), AUDIO (/project/ue/repo-audio, 8004). You work only in /project/ue/animpack (MCP port 8003) and /project/ue/packs/tactical-rifle/, and never start, stop, kill or rebuild anything of theirs: pkill -x UnrealEditor kills every editor on the box, so stop your own processes by process id. Run free -g before a heavy process; keep the box total under about 50 GB.
Never call gpu_rental_stop. IF THE BOX IS GONE (a call says it is not running AND mcp__Higgsfield__gpu_rental reports status ended): cat ` + BOXDIR + `/session again and use a new id if there is one; otherwise take the first line of ` + BOXDIR + `/keys that is not in ` + BOXDIR + `/used, append it to ` + BOXDIR + `/used, call mcp__Higgsfield__gpu_rent with exactly gpu_type "RTX-PRO-6000", gpu_count 1, kind "desktop", cpu 16, memory_gib 64, max_credits_per_hour 114 and idempotency_key = that line, poll until working, write the id into ` + BOXDIR + `/session, run /project/ue/bin/ensure-setup.sh every 30 seconds until it prints SETUP-DONE, and carry on. If no key is left or renting fails, stop and report.
Files travel through the user's Higgsfield storage (media_upload gives upload_url and url; PUT with the headers BOX.md gives; media_confirm type "file" or "image"; curl the url on the other side). Pictures as JPEG of at most 1920 x 1080. Do not call any Higgsfield generation tool.
Blender locally: ` + PY + ` (bpy 5.3.0; 4 CPU cores and 15 GB RAM shared with five other agents: one Blender process at a time); Blender on the box under /project/ue/bl if the previous agent installed it there (ANIMATION.md says).

GIT
Commit your own work in small steps (you may be cut off without warning): git add with explicit paths (docs/unreal/ANIMATION.md, your files under tools/box/anim/, the two data files, pictures with git add -f because the root .gitignore ignores shots/), never git add -A, commit, git push -u origin claude/tender-albattani-5q78qr; on index.lock wait and retry; if the push is rejected, git pull --no-rebase --no-edit and push again; never force-push, never another branch, never a pull request. Other agents edit this checkout at the same time: touch only your own files, and in the two data files change only the fields named below. End every commit message with exactly these two lines and put no model name anywhere else:
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HkcHdD7NbyxwnFfuuSpZY4
Stop your editor (by process id) when you finish.`

const BUILD = HEAD + `

ROLE: the animation and weapon-import agent. YOUR TASK, in this order (commit after each step):
1. LOADOUT.md 6.2 steps 1 to 3 in /project/ue/animpack: list the pack's Meshes/ folder into ANIMATION.md (per rifle: are irons, handguard and stock separate meshes, sections or baked in); import all six rifle variants and every part mesh with the pack's own textures and correct materials (4K where the pack gives it; check normal-map orientation and the packed-channel layout by looking at a lit close-up, not by assumption); the socket pass, script-driven and re-run on every import, with the exact socket names of 6.2 on every variant and on the parts. Place each socket from measured geometry (rail tops, muzzle threads, handguard underside, magazine well), not by eye.
2. Mount every attachment on every variant it is compatible with (attachments.json compatibility) and LOOK at each from the side and from the first-person camera: scope on the rail with the irons folded or hidden as 6.2 describes, silencer coaxial with the bore, grips seated on the lower rail, laser on its rail, transparent magazine showing rounds if the pack's material supports it (the RoundsShown parameter of 6.3 if feasible), stock folded and open. Fix offsets until nothing floats or intersects. For the scope build the lens material with a simple illuminated reticle and put SightEye on the optical axis.
3. THE FIRST-PERSON RECIPE. The previous agent's first-person proof (docs/unreal/shots/anim-fp-aimed.jpg) shows the left forearm sweeping across a third of the frame as a huge tube and gloves clipping the near plane: the camera placement is wrong for clips that animate the whole mannequin body. Work out and document in ANIMATION.md the camera recipe that makes the pack's first-person clips look as the pack intends (look for the author's guidance in the pack's documentation or Unreal project conventions if any file on the box records it; otherwise derive it): camera attached to which bone or at what offset from the head, field of view for the arms layer (a separate first-person FOV of the order of 60 to 75 degrees against the world FOV), near clip, whether the body below the arms is hidden (bone masks or owner-no-see sections), and how aiming aligns SightRear, SightFront or SightEye with the screen centre for irons and for the scope. Prove it with the pack's OWN rifle (these clips fit it natively, with no IK): hip idle, aimed through irons, aimed through the scope, mid tactical reload, mid empty reload at the bolt release, inspect, and a sprint frame.
4. The data (LOADOUT.md 6.2 step 4): in guns.json fill variants.*.mesh for shorty, stick and stretch and move their statuses from inPack to exists; in attachments.json fill presentation.mesh and the measured socket offsets and statuses; measure the pack laser along the bore and apply the 50 mm rule of 6.6 for the NINE. Keep both files valid JSON and change nothing else in them.
5. Icons: per variant a white-on-transparent 512 x 192 side silhouette (T_UI_Gun_Shorty, _Stick, _Stretch) and per part a small pip (T_UI_Att_<id>), rendered on the box and kept on the box only (never committed).
6. Extend tools/box/anim/import-animpack.sh (or add a sibling script) so one command brings rifles, parts, sockets, materials and icons into any project on the box (the game project will run it), and test it on a fresh project copy as the previous agent did.
7. The 6.6 request for the CHOPPER's extra clips (Inspect, MagCheck, ModeSemi, ModeAuto, MeleeA, MeleeB, Equip, Holster, Draw): ANIMATION.md says which were already adapted; adapt the rest with mi_adapt if time allows, otherwise record them as missing. The CHOPPER mesh is being rebuilt by another agent right now, so make sure the whole adaptation can be re-run by one command against a re-exported SK_Chopper and say which command.
Proof pictures, committed (docs/unreal/shots/packguns-*.jpg, at most ten, 1920 x 1080 or smaller, each under 400 kB, git add -f): the three lengths side by side; one rifle with scope, silencer, vertical grip and laser mounted, three-quarter view lit to show the materials; the folded stock; and the first-person frames of step 3. Look at every one before you commit it and re-do any that shows a fault.

Reply through the structured output: summary (at most 200 words), done (each item with its evidence), not_done (each with the reason), camera_recipe (the numbers), pictures, open_issues.`
const BUILD_SCHEMA = { type: 'object', properties: { summary: { type: 'string' }, done: { type: 'array', items: { type: 'string' } }, not_done: { type: 'array', items: { type: 'string' } }, camera_recipe: { type: 'string' }, pictures: { type: 'array', items: { type: 'string' } }, open_issues: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'done', 'not_done', 'camera_recipe'] }

phase('Build')
const build = await agent(BUILD, { label: 'packguns:build', phase: 'Build', schema: BUILD_SCHEMA, effort: 'high', model: 'opus' })
if (!build) return { build: null }

const CHECK = HEAD + `

ROLE: an independent checker who did not do this work. Another agent reports the following about turning the pack into loadout guns:
` + JSON.stringify(build, null, 1) + `
Do not take it on trust and do not fix anything. On the box, in /project/ue/animpack (start its editor if it is not running; stop it by process id when you finish), check from the assets themselves and from FRESH pictures you take:
- every one of the six rifle variants exists and carries every socket LOADOUT.md 6.2 names; print each socket's transform and judge whether it is where the name says (Optic on the rail top, MuzzleMount at the muzzle face on the bore axis, and so on);
- every attachment mounted on every compatible variant: render a side view and a first-person aimed view of each combination that the data allows (contact sheets are fine) and look for floating, intersecting, mirrored or wrongly scaled parts, the scope reticle on the screen centre when aimed, irons hidden or folded under the scope;
- materials: lit close-ups of the receiver, handguard and magazine: do they read as real anodised aluminium, polymer and steel with correct normals, or flat, inverted or plastic;
- the first-person recipe: set the camera as documented and step through hip idle, aimed, fire, both reloads, inspect and sprint at five moments each: any frame where an arm fills the view, a hand clips the near plane, the gun leaves the hands, or the magazine is not in the hand;
- the data: guns.json and attachments.json are valid JSON, the mesh paths in them resolve to assets that exist, and git diff shows the previous agent changed only the fields it was allowed to;
- the licence rule: git log and git status show no pack-derived file committed (list any committed file under the paths the build agent touched that is a mesh, texture, uasset or an icon of a pack mesh);
- the import script: run it on a fresh project copy and see the guns arrive with sockets.
Reply through the structured output: verdict (at most 120 words), grade from 1 to 5 for how the pack rifle looks in first person (5 = current AAA shooter), faults (each with where it shows and a concrete fix, most visible first), sheets (paths of pictures you saved under docs/unreal/shots/review/, not committed).`
const CHECK_SCHEMA = { type: 'object', properties: { verdict: { type: 'string' }, grade: { type: 'number' }, faults: { type: 'array', items: { type: 'object', properties: { fault: { type: 'string' }, fix: { type: 'string' } }, required: ['fault', 'fix'] } }, sheets: { type: 'array', items: { type: 'string' } } }, required: ['verdict', 'grade', 'faults'] }

phase('Check')
const check = await agent(CHECK, { label: 'packguns:check', phase: 'Check', schema: CHECK_SCHEMA, effort: 'high', model: 'opus' })
if (!check || !check.faults.length) return { build, check }
log('check grade ' + check.grade + ', ' + check.faults.length + ' faults')

const FIX = HEAD + `

ROLE: the animation and weapon-import agent, fix pass. An independent checker reviewed the pack-gun work and found these faults (most visible first):
` + JSON.stringify(check, null, 1) + `
The build agent's own report, for orientation: ` + build.summary + `
Fix every fault, re-run the socket pass and the import script test, retake the committed proof pictures that a fix changes (docs/unreal/shots/packguns-*.jpg, look at each), update ANIMATION.md and the two data files where a fix changes a number, and commit. If a fault cannot be fixed, say exactly why.
Reply through the structured output: summary (at most 150 words), fixed, not_fixed, pictures.`
const FIX_SCHEMA = { type: 'object', properties: { summary: { type: 'string' }, fixed: { type: 'array', items: { type: 'string' } }, not_fixed: { type: 'array', items: { type: 'string' } }, pictures: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'fixed', 'not_fixed'] }
const fix = await agent(FIX, { label: 'packguns:fix', phase: 'Check', schema: FIX_SCHEMA, effort: 'high', model: 'opus' })
return { build, check, fix }
