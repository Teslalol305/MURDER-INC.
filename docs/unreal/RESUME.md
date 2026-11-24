# Picking up where we left off

Last updated 2026-11-23 by the lead session (branch `claude/tender-albattani-5q78qr`, never merged, no pull request).
A new session starts here: read this page, then `DECISIONS.md`, then the documents it points to.

## 1. What this project is

The repository's browser shooter (`src/`, three.js, "MURDER INC.") is being rebuilt in **Unreal Engine 5.9** with
next-gen, photoreal graphics. Art is authored in **Blender 5.3 by Python scripts** (`art/blender/`), exported as GLB,
and imported on a **rented GPU box** that runs the Unreal editor headless. The web game stays the ground truth for
gameplay: Unreal replays its runs frame by frame and must match.

The owner's standing instructions (verbatim):

- "rebuild this game using the blender and unreal engine plugins the game needs to have much better. graphics and
  textures/ realistic next gen graphics"
- "Make sure the guns and characters and all elements are being rebuilt to look realistic and very detailed textures
  and animations the entire game needs to feel next gen"
- "spend all the higgsfield credits you need" (still: keep the balance above 2,500 so the box can run)
- "include all the guns and animations in the sprite pack i downloaded as load out options where a user can pick 4
  guns to carry into the game from the home screen. the flow should be. Pick a charachter-pick load out and add weapon
  attachments then pick level and game style"
- The main character looks like the man in the owner's reference photo ("this is my business partner we own the
  likeness so go for full facial realism").
- Voice lines on kills and progress: "It's Murda!", "Holla, holla!", "Rule Baby!", "What's my motherf***in' name?!"
  (crowd answers "R-U-L-E!"), "I-N-C!".
- Use Opus for background agents.
- "this game will live on the IPX.exchange Game OS website": delivered by streaming the Unreal build into the page (Pixel Streaming), the owner's choice (`DECISIONS.md`).

## 2. Rules that stay in force

- **Never commit** pack content (Infima "Tactical FPS Animation Pack - Assault Rifle", Fab licence), Epic template or
  mannequin content, the reference photo or anything generated from it, or renders of the pack's meshes alone. The
  repository is public. These live in git-ignored `art/out/` and on the box under `/project/`.
- **Never write or send the business partner's name** anywhere (files, prompts, requests). Do not identify him from
  photos.
- **Voice:** placeholder takes are generic stock text-to-speech. Never clone or imitate the real voice, never sample
  released recordings. Real recordings replace the files one for one (`AUDIO.md` section 5, `tools/audio/voice_ingest.py`).
- **GPU box:** re-renting is approved only for the same box at the same price (RTX PRO 6000, 16 cores, 64 GB,
  at most 114 credits an hour). A different box or a higher price goes to the owner first.
- The Saltline / "Murder Inc." IPX artifact edition is unpublished: publish only when the owner says so.
- No pull request unless asked. Commit trailer lines are given by the harness at session start.

## 3. Where things are

| What | Where |
|---|---|
| Owner decisions | `docs/unreal/DECISIONS.md` |
| Progress log (every agent's section) | `docs/unreal/PROGRESS.md`, `art/blender/PROGRESS.md` |
| The box: how to work on it, every pitfall | `docs/unreal/BOX.md`, scripts in `tools/box/` |
| Gameplay as built (slices 1 and 2) | `docs/unreal/GAMEPLAY.md` |
| Loadout and home-screen flow design | `docs/unreal/LOADOUT.md` (data in `unreal/MurderInc/Content/Data/`) |
| Pack import, clips, first-person camera recipe | `docs/unreal/ANIMATION.md` (sections 8 and 9 for the pack rifles) |
| Characters pipeline | `docs/unreal/CHARACTERS.md`, `art/blender/README.md` |
| MetaHuman Creator on the box (offline preview and meshes; assembly needs an Epic login) | `docs/unreal/METAHUMAN.md`, scripts in `tools/box/metahuman/`, project `/project/ue/metahuman` (MCP 8006) |
| Audio and voice lines, recording brief | `docs/unreal/AUDIO.md` |
| Port specs from the web game | `docs/unreal/spec/` |
| Pictures of results | `art/previews/`, `docs/unreal/shots/` |
| The workflow scripts that ran the agents | `tools/workflows/*.js` |
| Git-ignored art outputs (11 GB) | `art/out/`, backed up to the box at `/project/backup/art-out/`; restore with `tools/box/restore-art-out.sh` |

**The box.** Higgsfield GPU rental, desktop kind. Last session id `8b816116-3377-4331-9a05-d201df758d97`; it stops by
itself after 10 idle minutes, and `/project` survives. To re-rent: `mcp__Higgsfield__gpu_rent` with gpu_type
`RTX-PRO-6000`, gpu_count 1, kind `desktop`, cpu 16, memory_gib 64, max_credits_per_hour 114 and a fresh idempotency
key; then run `/project/ue/bin/ensure-setup.sh` until it prints `SETUP-DONE`. Projects on the box: level clone
`/project/ue/repo` (MCP port 8000), gameplay clone `/project/ue/repo-gameplay` (8001), characters
`/project/ue/chars` (8002), pack and animation `/project/ue/animpack` (8003), audio `/project/ue/repo-audio` (8004).
`pkill -x UnrealEditor` kills every editor: stop editors by process id.

**Local tools.** Blender as a Python module in a venv in the session scratchpad (lost with the container). To
recreate it, follow `art/blender/README.md` (pip install of `bpy` 5.3.0).

## 4. State at the end of 2026-11-23

Done and verified:

- Port specs; Blender art pipeline; full prop, facade, sign, furniture and structures catalogue; the Buzzard drone.
- Unreal: the art street `L_Block` (283 props, 13 vehicles, 38 structures, shop interiors, clouds, ray tracing);
  gameplay slices 1 and 2. A whole run plays (enemies, reels, extraction, Hold the Block, menus, save). Five web-game
  runs replay with 0 mismatches.
- Audio and voice lines: 94 tests pass; engine render proven; placeholder voice.
- The purchased rifle pack: all clips and six rifles imported with sockets and attachments; the first-person camera
  recipe is worked out (`ANIMATION.md` 9).
- Three cloth-simulated Goons (round 1).
- Main character likeness, arms and body (round 2; face 3.5/5 by the builder's estimate).
- Vehicles: one review and fix pass (close-up rounds still running).
- The CHOPPER and NINE rebuild: stopped after three rounds at 2.5/5 and 2/5. **The owner decided the pack rifle
  stands in for the CHOPPER** (`DECISIONS.md`).

Still running when the lead session went idle (each commits its own work as it goes; check `git log` and the
PROGRESS sections to see how far each got):

| Workflow | Script in `tools/workflows/` | What it does |
|---|---|---|
| Vehicles close-up rounds | `mi-vehicles-verify-fix-*.js` | modelled wheels, lamps, glass, interiors; independent grade each round |
| Goons round 2 | `mi-goons-v2-*.js` | masks with real head structure, cloth materials, fits, sneakers; review, rebuild, re-review |
| Main character arms round 3 | `mi-rule-arms-v2-*.js` | first-person bare tattooed arms and hands, grips; review, rebuild, re-review |
| Goons round 3 | `mi-goons-v2-*.js` | masks redesigned (round 2's read as a racial caricature: must never ship), fold lighting, cloth; re-review |
| First-person in the game | `mi-first-person-*.js` | step 2 below: pack rifle as CHOPPER, bare arms, camera recipe, Goons as enemies, effects; review and fix |

The loadout flow finished: all six screens work with keyboard, mouse and gamepad; 100 of 101 tests pass (the one failure
is the audio test that needs `node tools/ue-export/audio.mjs` run on the box); parity replays show 0 mismatches.

## 5. Next steps, in order

1. **Read the results** of the four workflows above (their commits, PROGRESS sections and pictures). Re-run any that
   stopped partway with a restart note asking it to continue from the files on disk.
2. **First-person presentation in the game** (the most visible gap: the game still shows Unreal's white template arms
   and rifle). One agent in the gameplay clone, after the loadout flow lands, because both change the same code:
   - the CHOPPER drawn by the pack rifle, Short handguard, with its own dark-earth material instance; the pack's clips
     played natively at rates that hit the web game's reload stage times (`DECISIONS.md`);
   - `SK_RuleArms` (bare tattooed arms) as the arms mesh, imported into the game project;
   - the camera recipe of `ANIMATION.md` 9: camera at the head, 1 cm near clip, arms field of view 54 degrees
     vertical at the hip blending to 38 on irons and 32 with an optic;
   - `UMIGunAssembly` reads `variants.open.opticMesh` so the irons fold under a scope;
   - magazines: hide the reserve until in hand, spawn a dropped magazine in the dropping reloads (`ANIMATION.md` 9.1);
   - the NINE with `SK_Nine` and the template pistol clips;
   - the Goons (`SK_Goon_*`) as the enemies with the template rifle clips, scaled 0.98, replacing the mannequins;
   - play-in-editor pictures from the player's eye, and an independent review.
3. **Update `LOADOUT.md`**: the pack's "_Folded" rifles fold the iron sights, not the stock, so there is no stock
   option; the NINE has no laser (the pack laser is 155 mm).
4. **Effects**: muzzle flash, shell ejection, impacts, blood, explosions, tracers (all are event-bus hooks today).
5. **Remaining art**: the RATTLER (player SMG), crew looks for DEUCE, SMOKE and KEYS, menu stage and icons, the last
   grey boxes in `L_Block` (building backs, shanty, hoist), a night lighting set.
6. **Final review** of the whole rebuild against the owner's instructions.

## 6. Waiting on the owner

- **Photos of the business partner**: head straight on, three-quarter both sides, both profiles, at eye level in even
  light; one front and one side without the bandana; square-on close-ups of each forearm tattoo with readable text; the
  bracelet close up; optional full body front and back.
- **MetaHuman sign-in (the biggest quality lever for characters).** A scout proved that MetaHuman Creator runs headless
  on the box and builds far more realistic people than the Blender Goons (`docs/unreal/METAHUMAN.md`,
  `docs/unreal/shots/metahuman-goon-1m.jpg`). The last step, turning a character into a game-ready MetaHuman, needs
  Epic's cloud face auto-rig and texture download, which need one Epic account sign-in. Options: the owner signs in
  to MetaHuman Creator in a windowed Unreal Editor 5.9 on their own computer, runs Auto-Rig and Download Texture
  Sources per character, and the saved assets travel to the box; or a one-time sign-in on the box's desktop is tried.
  Never ask for or type the owner's password.
- **Real voice recordings** of the five lines and the crowd answer, per `AUDIO.md` section 5.
- Optional purchases that would lift quality most: a pistol pack with first-person animations (for the NINE), Epic's
  free City Sample Vehicles and Game Animation Sample.
- The open defaults in `LOADOUT.md` section 10 (three pack guns, one to four guns carried, placeholder names, cosmetic
  crew, and so on) stand until the owner answers.

## 7. Credits

Higgsfield generation spent so far: about 373 on vehicles and the generated Goon, 127 on the main character, 54 on
audio. The rest of the spend is the GPU box at about 114 credits an hour. Balance was about 2,960 at the last check.
Agents stop generating below 2,500.


## 8. Exact next steps (written 2026-11-23 evening, when Higgsfield credits ran out)

The box ended at 19:48 with credits exhausted. Nothing on the box can run until the owner tops up (keep the balance
above about 2,500). Then, in order:

**2026-11-24: steps 1 and 2 are done** on box d6f06d9d (PROGRESS.md, "Box back"): the fix pass and the 36-card
pool built, 105 of 105 tests and golden replays pass, the polish pictures retaken; also fixed there: the start view
(pitched 7 degrees up, no trash can), the neighbours' backs dressed with the facade kit's window bays, the backdrop's
framed windows and glass towers, the crosshair hidden when aimed. Only the gameplay clone's L_Block was rebuilt.
Re-verified on box 8b816116 at `b1d321f`: build OK, 105 of 105. Next is step 3.

**2026-11-24 evening: step 3's fix pass is done** on box 8b816116 (PROGRESS.md, "Fix pass after the independent
play-through"): Night out of the offer, styled in-game cards and health band, the flash aimed and its light, the
casing, the veil gradient, the frozen field and cleared shots at the debrief, last-enemy marks and the stuck-Buzzard
fallback in Hold the Block, the dressed loadout stage, never-streamed interior cubes, the Chop Shop oil card, and a
`usage` step in `package-cloud.sh`; 105 of 105 tests. Next is step 4 (repackage: `package-cloud.sh all` now sets the
usage flags itself), then grep the packaged log for `missing usage flag` and look at an explosion frame.

**2026-11-24, 16:55: step 4 is done** (PROGRESS.md, "Repackage for the website"): the package of `0f23081` is in the
owner's storage as ten parts, sha256 `8378eedd...`, checked from the storage; LAUNCH.md section 9 has it. Step 5's
old zip is superseded. Next is step 6 (the owner's E3DS trial) and the explosion frame.

1. Re-rent the same box (RESUME section 3) and run `/project/ue/bin/ensure-setup.sh` until `SETUP-DONE`.
2. In `/project/ue/repo-gameplay`: `sync.sh`, `build.sh` (the 36-card flash pool, commit 9e55db3, was never compiled),
   then `tools/box/test.sh MurderInc` (105 tests and golden replays: not run since the polish changes), then
   `fp/polish-shots.sh`.
3. Re-run the independent play-through review (the polish workflow's check stage, `tools/workflows/mi-polish-*.js`,
   resume it) and fix what it finds. Known still open: the first frame faces a trash can 1.1 m away (move prop 270 or
   turn the PlayerStart), the 7 brick building backs and the skyline towers read as blockout.
4. Re-package for the website: `package.sh snapshot` from repo-gameplay, then `tools/box/cloud/package-cloud.sh all`
   (it also brings the 800 MB texture pool), upload the parts, and put the new sha256 and links in `docs/LAUNCH.md`.
5. **Do not let the owner upload the zip currently linked in LAUNCH.md (sha256 4ff06998...)**: it was packaged before
   the polish and still shows the grey slabs at the start and has no visible player muzzle flash.
6. The owner then tests on the Eagle 3D Streaming free trial (LAUNCH.md section 4): the stream itself, sound,
   gamepad and delay have never been tested, because the box's sandbox blocks WebRTC.

## 9. Launch status (2026-11-24, from the owner's screenshots)

- The owner downloaded and joined the zip on their Mac: sha256 `8378eedd…e570a` matched.
- E3DS (new "Projects" dashboard): the zip was uploaded as build `MurderInc`. E3DS detected Linux, Pixel Streaming
  and `MurderInc.sh`. **E3DS's own upload test passed** (Upload ✔, Test ✔, "Your app is ready to stream"), so the
  Unreal 5.9 Linux build streams on their machines. Project `Project_MurderInc`. The share link is in the owner's
  E3DS dashboard; it is not written here.
- Viewer settings advised: Locked Mouse, browser cursor off, 1920x1080, video quality High, H264, region Global,
  15 min session with 5 min idle, a password while testing, Unreal log in the browser console on while testing,
  crash-log email on.
- Next: the owner plays the link in Chrome (LAUNCH.md section 4). Cursor then embeds the link on the IPX Game OS
  page and deploys (`docs/CURSOR_HANDOFF.md`).
