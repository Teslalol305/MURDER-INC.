# Picking up where we left off

Last updated 2026-11-25 (morning, version 3a delivered: section 9) by the release engineer (branch `claude/tender-albattani-5q78qr`, never merged, no pull request).
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
  and `MurderInc.sh`. **E3DS's own upload test passed** (Upload ✔, Test ✔, "Your app is ready to stream"); that check
  turned out not to prove that the build streams (below). Project `Project_MurderInc`. The share link is in the
  owner's E3DS dashboard; it is not written here.
- Viewer settings advised: Locked Mouse, browser cursor off, 1920x1080, video quality High, H264, region Global,
  15 min session with 5 min idle, a password while testing, Unreal log in the browser console on while testing,
  crash-log email on.
- **Version 1 crashed on every real session** (17:46 UTC on the trial, again about 18:55 UTC on Core with ten
  slots): "Crashed ... But no crashlog was found". Version 1 wrote no log at all. Diagnosis and fix: PROGRESS.md,
  "E3DS crash fix". Root cause **not proven** (no log exists). Best fit since E3DS's own documentation was read
  (PROGRESS.md, "Version 2 re-zipped"): E3DS does not add `-RenderOffScreen` and version 1's launcher did not either;
  with no display that build exits 1 after 2.4 s with no log (box run `s-nodisp-noRO`). Also possible: the server's
  NVIDIA driver fails Unreal 5.9's Vulkan SM6 check while version 1 had no SM5 shaders to fall back to (exit 1 at
  7 s, reproduced with `-sm5`), graphics memory at start, a root user.
- **Version 2** (zip of 2026-11-24 evening, game commit `e989cb8`, nine parts; sha256 and parts table in LAUNCH.md
  section 9; download links only in the release report, never committed) handles all of those and **always writes a
  log**: `MurderInc/Saved/Logs/MurderInc.log` in the app's folder on the server (LAUNCH.md section 13), plus the
  engine's crash report in `MurderInc/Saved/Crashes/`. Debug symbols for its crash call stacks are on the box in
  `/project/ue/cloud/symbols/e989cb8/`. Verified on box ec087d85; a browser cannot connect there, but a non-browser
  WebRTC client received the game's 1080p picture and sound (PROGRESS.md, "Independent check of the `82ed886a…` zip").
- **Next:** the owner uploads version 2 as a **new version of the build `MurderInc`** (LAUNCH.md section 9, step 5)
  and opens the link in a fresh Incognito window (DECISIONS.md). If it crashes again: get the log (LAUNCH.md section
  13: browser console, launch option `-MIDev` for E3DS's crash-log feature, or E3DS support) and give it to Claude.
  If it streams: Cursor embeds the link on the IPX Game OS page and deploys (`docs/CURSOR_HANDOFF.md`).
- **Version 2 streamed, and lagged** (the owner's test, 2026-11-24): "the game is sticky", "when the player turns it
  slows down; it is not a viable experience". Version 3 is being built in two releases (DECISIONS.md, 2026-11-25).
- **Version 3, release A (2026-11-25): the lag, explained and ended in the code; not packaged yet.** A game that
  renders off screen never waits for the GPU, so on a GPU slower than the frame rate the unfinished frames pile up
  while the view turns and one frame then lasts seconds (reproduced on the box: frames of 1 to 8 s). Version 3 holds
  itself back (a pacer), draws a smaller picture when the GPU is busy (dynamic resolution) and lowers its frame-rate
  target (60, 45, 30); the pause card shows the numbers the owner could never read. Everything measured is in
  PROGRESS.md, "Version 3, release A: the lag"; the gameplay part (mouse, controller, cards) is the entry below it.
  A second way to the same complaint was seen and cannot be fixed on the server: on a thin connection the sender
  drops most frames of a turning picture while the game holds 60. The pause card's line tells the two apart
  (LAUNCH.md section 7).
- **Release A reviewed and fixed (2026-11-25, 06:30 UTC; PROGRESS.md, "Version 3, release A: the review's
  findings").** Two reviews found ten faults; all were real. The two that could have sunk the launch: on a server
  with 8 hyper-threaded CPUs or fewer the pacer froze the game for 250 ms in every frame the GPU was the limit
  (the box has 16 CPUs and never showed it; held to 6 it did), and two quick clicks left the fire button held
  when the page sends the browser's double-click message with no release, as the review read E3DS's page (shown
  on the box with a viewer that sends it so). Also fixed: a controller's first press, what a viewer held when the
  connection was cut, X reloading at a reel, the pause in a run's intro, the frame-rate target's way back up, what
  a visitor may set, the Development game behind a key. The gate was repeated with the final code and passes,
  its three lines on 6 CPUs included; two more runs on 4 CPUs held their rates.
- **Version 3a (release A) is packaged, gated and in the owner's storage (2026-11-25; PROGRESS.md, "Version 3a:
  packaged, gated and delivered").** Zip sha256 `de41a708…58e4`, 2,254,962,151 bytes, nine parts named
  `MurderInc-E3DS-v3a-part<k>-of-9.zip` (fingerprints, join and upload steps, the E3DS settings: LAUNCH.md section 9;
  download links and the Development game's key only in the release report). Game and launcher `6c4d810`, 119 of
  119 tests. The release gate was run on the zip itself, unpacked as a new user with an empty home into a fresh
  folder and started with E3DS's arguments: at every load, on 16 CPUs and on 6, no frame over 50 ms in play (38 ms in
  the Shipping game's Story runs), memory flat, a clean stop; 60.0 frames a second on a free GPU. Play was proven through the stream with mouse and
  keyboard and with a controller only.
- **New knowledge from that gate: a cold machine.** With an empty home (no graphics-driver shader cache), which is
  what E3DS gives every session, the game's first frame takes 3 to 4.5 s (nobody is connected yet) and **the first
  set-up screen (Crew) costs one frame of about 0.85 s**; nothing else is long, and the play is not touched. Warm,
  both are gone. PREFLIGHT V3-12 (release B) is the place for it.
- **Version 3a checked independently (2026-11-25, 09:20 UTC; PROGRESS.md, "Version 3a: the independent release
  check").** The zip from the storage, joined with the owner's own commands; a session started the way E3DS starts
  one; the gate repeated with a viewer whose turns stop dead (worst frame 48 ms under the lag's load, 60.0 frames a
  second on a free card); version 2 as the control under the same load (frames of 1.3 s, 498 fence lines); a fight,
  Hold the Block and its "LIGHTS OUT" card (click, Enter and a controller's A each go on), six minutes of play, two
  games on one card; 119 of 119 tests. **The stall is gone.**
- **THE GAME HAS NO SOUND, and never had in any package** (found by that check: every Opus packet of a session is 3
  bytes of silence). The Sound Wave assets were only ever imported in the audio clone (`/project/ue/repo-audio`);
  the gameplay clone, which every package's Content comes from, has the WAV files and no asset, and the pak has no
  `/Content/Audio/` entry. **First thing in the next build**: `tools/box/audio-import.sh` in the gameplay clone,
  package, check the pak's list and listen through the stream (PREFLIGHT.md V3-14). LAUNCH.md tells the owner that
  version 3a is silent. Not to go public before this is in.
- **Version 3b: the sound is in and packaged (2026-11-25, noon UTC; PROGRESS.md, "Version 3b: sound").** Zip sha256
  `aa7cc478…8deb`, 2,259,930,775 bytes, nine parts `MurderInc-E3DS-v3b-part<k>-of-9.zip` in `/project/ue/cloud/parts`
  on the box: the game of `3dd4053` (121 of 121 tests), the launcher with the cleanup of leftover games. **Not
  uploaded, and the lag gate has not been repeated on it** (the release engineer's step; LAUNCH.md still describes
  version 3a and calls the build silent). The 289 Sound Waves are in the pak, and a package without them can no
  longer be zipped (`package-cloud.sh`), pass the tests or come out of a clone that is brought up to date. Sound was
  proven through the stream by measurement, kind by kind, in both games of the zip (`tools/box/cloud/rtcaudio.py`,
  `audio_find.py`, `sound_table.py`, `sound-gate.txt`). The listening found three faults of the port, fixed with
  tests: four of the six guns had no shot sound, the menus never played theirs, and the first round of each gun
  sample came about 110 ms late. A server needs no sound card (SDL's dummy device; the launcher names it itself,
  because a host environment that names another driver silenced the game). **Known and not fixed:** in the first
  half minute after a cold start on a machine whose CPUs are all busy the stream's music has gaps of 30 to 50 ms
  (never after it, never in play); the sound's clock runs 1 % fast. **Nobody has heard it yet**: the owner's first
  session with version 3b is the first time ears meet it (the speaker button on E3DS's page; the Volume row on the
  Settings card).
- **Still unknown:** which graphics card E3DS's Linux sessions get, and everything a real browser, a real
  controller and a real connection add. The box is not E3DS.
- **Next, the owner:** join the nine parts, upload the zip as a new version of the build `MurderInc`, set the
  settings of LAUNCH.md 9.1 (Browser Resolution Custom 1920 x 1080, launch options empty), play a Story run, press
  P after a fast turn or a stutter and send back a screenshot of the pause card (its bottom line names the server's
  card, both frame rates with their lowest values, the GPU's time, the picture's size and the build).
- **Next, engineering (release B):** the sound first (V3-14, above), then the rest of PREFLIGHT.md section 2:
  quality steps on slow cards (V3-2), the hand-to-picture delay (V3-4), Browser Resolution Dynamic with the HUD at
  small sizes (V3-6), the rest of the controller path (V3-7: the home screen names the keyboard's keys until a
  second controller press; a whole Story and Hold the Block run through the stream), the cold start (V3-12), the
  smaller items (V3-13). The owner's screenshot decides the order after the sound: a slow card makes V3-2 next.
