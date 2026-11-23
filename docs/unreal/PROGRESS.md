# Unreal rebuild: progress

What is verified on the box, newest first. Every entry says how it was verified. The loop and the pitfalls are in
`docs/unreal/BOX.md`.

## Demo build (release engineer): the game playable from a browser — done

**Verified 2026-11-23** on the box (session d14fa3ab). Owner's guide: `docs/DEMO.md`. Scripts: `tools/box/demo/package.sh`,
`start.sh`, `stop.sh` (copied to `/project/ue/demo/tools/` on the box; the demo-video agent's `capture.sh`, `audio.sh`,
`finish.sh` share the folder).

**Route: the rental's own browser desktop.** The desktop rental already streams its screen (Selkies, websockets mode,
H.264 on the card) to a private page behind the platform's HTTPS link (`Open desktop`, a `*.w.modal.host` address
with a connect token and a session token); that page is the only thing the box exposes to the internet. Pixel
Streaming was not used: it needs its own signalling and media ports reachable from the internet, the rental routes
no other port, and the rental's instructions forbid starting tunnels, VNC or web servers on a desktop box ("the
desktop and its link already exist"). A packaged Mac build is impossible from Linux (it needs a Mac with Xcode and
the engine), and was not needed.

**Windows do work here for the game.** `desktop-run --vulkan` (the box's launcher: primus_vk renders on the RTX PRO 6000
and presents through llvmpipe on the virtual screen) draws the packaged game, and `UnrealEditor <project> -game`,
in a window without aborting; only the editor's own window was ever seen to abort (BOX.md).

**The package.** `package.sh snapshot` copies the gameplay clone's project (Source, Config, Content with all the
imported art, the editor module) to `/project/ue/repo-release` (its own copy: `repo-demo` is the demo-video agent's
clone), `package.sh start` runs BuildCookRun Linux Development: game target 2 min from scratch, cook 1 to 2 min
with the shared cache, 1.7 GB staged in `/project/ue/demo/build/Linux`. Overlay on the copy only: start map
`L_Block`, cook the folders the data loads by path (Art, Audio, Characters, FX, FirstPerson, ThirdParty, Weapons,
Input, Variant_Shooter), stage `Content/Fonts` as files (`UI/MIStyle.cpp` reads them like the data), no Zen store
(the cooker's Zen writer aborts: no Zen server on the box), `-IgnoreCookErrors` (the template's ABP_FP_Pistol and
ABP_FP_Weapon no longer compile and are unused). The package holds pack and Epic content: box only, never committed.

**Found and fixed: mouse look was 14 times too slow outside play in editor.** BaseInput.ini scales MouseX, MouseY
and Mouse2D by 0.07 and Enhanced Input applies it even with the legacy scales off: 300 counts turned 2.5 degrees
(read back with `getall MIPlayerController ControlRotation`) instead of 36. `Config/DefaultInput.ini` now replaces
the three entries with sensitivity 1; after the fix 100 counts turn 12.03 degrees (0.0021 rad per count, exact) and
50 counts down pitch 6.0 degrees down. Play-in-editor input went through `MIInput`, which is why no test saw it.

**Measured through the desktop path** (the X screen the stream sends; input injected with XTEST as the stream's
input is): home screen to the Story run through Crew, Loadout, Block and Briefing with mouse clicks; 1920 x 1080 full
screen, Epic preset, TSR at 73 %: **60 fps locked**, GPU 6.4 to 6.6 ms, game thread 5 ms, draw 7.5 to 7.9 ms;
mouse-move-to-screen 43 to 56 ms (median of 8, includes a 12 ms screen grab). With two other agents' editors
running on the same card: 55 to 60 fps, GPU 14 to 17 ms, 78 ms median delay. The uncooked `-game` run with an
editor alongside managed 36 to 49 fps: the package matters. The desktop icon "MURDER INC." (re)starts the game.
Pictures (box only, they show pack content): `/project/ue/demo/home.jpg`, `g3.jpg`, `ads.jpg`, `fire.jpg`.

**Limits** (the rental's stream settings, not the game): no sound in the browser (Selkies runs with audio off; the
game's audio device does not open for user ue4 either: "ALSA: Couldn't open audio device"), no gamepad through the
browser (gamepad input off), Safari has no keyboard lock (Esc leaves gaming mode). The game window does not follow
a later resize of the desktop: restart it with the icon. Seen in play: a black half disc below the left forearm in
the hip pose (art, first-person agent), vertical banding on the set-up stage for a few frames after a camera cut.

## First person (the player's arms and guns, the Goons, the effects) — first pass done

Built in the gameplay clone `/project/ue/repo-gameplay` (MCP 8001). Contracts: `docs/unreal/GAMEPLAY.md` 15 to 19.

**Verified 2026-11-23**
- **Art in the game project** by one re-runnable command (`tools/box/fp/fp-art.sh pack | put | unpack`, then
  `tools/box/fp/import-chars.sh all`, 2 to 3 minutes headless): `SK_RuleArms` on SK_Mannequin (Recompute Normals off,
  `M_RuleArms_Skin` with `SP_RuleSkin`, `M_RuleArms_Nail`, the silver bracelet), the three Goons r3 by
  `mi_chars.setup_goons` (Cloth shading, exported normals), `SK_Nine` with its magazine, `SM_Weapon_GoonSMG`, `SK_Buzzard`,
  the CHOPPER's dark-earth instances on the pack's own textures, and the /Game/FX materials. The pack was already in the
  project (the loadout agent's `import-animpack.sh all`): not re-imported. Re-run after any re-export by the character
  agents: assets are replaced in place, no data change.
- **The real paths are data** (the dev overlay is gone): presentation.json `firstPerson.arms`, `.jewels`, `.recipe`,
  `.animSets`, `guns.chopper.realMesh` + `real` (the Short pack rifle, its sockets, `animSet` and finish), `guns.nine.realMesh`
  + `real` (SK_Nine), `enemies.goon.variants` (the Goons, `variantsFallback` the mannequins), `meshScale` 0.98, the SMG on
  `hand_r`; guns.json `animSet` on SHORTY, STICK, STRETCH; `opticMesh` read by `FMIReadiness::BaseMesh`. A clean checkout
  keeps the templates (`FirstPerson.RealArt` checks both ways).
- **Pictures through the player's eyes** (`tools/box/fp/fp-shots.sh`, play in editor in L_Block, Story on Hustler, set-up
  CHOPPER + NINE + STICK with scope and vertical grip made on the set-up screens; 1920 x 1080, each looked at):
  `shots/fp-hip-sun.jpg`, `fp-hip-el.jpg` (the CHOPPER as the pack's Short rifle in its dark-earth finish, the bare
  tattooed arms in the pack's idle), `fp-irons.jpg` (Aim_Pose, the rear aperture on the screen centre at 38 degrees),
  `fp-scope.jpg` (the STICK, irons folded under the scope, the window on the eye line at 32 degrees),
  `fp-reload-tactical.jpg` (Reload_Quick warped onto 2.24 s), `fp-reload-empty.jpg` (Reload_Empty onto 2.72 s, the
  magazine dropped as a body: logged at 1.1 to 1.4 m/s), `fp-inspect.jpg`, `fp-nine.jpg` (SK_Nine in both hands, the
  palms pulled onto its Palm sockets, the bracelet), `fp-goon.jpg` (a Goon at about 12 m firing at the player: its
  SMG's flash and the tracer; frozen on its round), `fp-explosion.jpg` (a propane tank blown at 9 m).
- **Rules untouched.** The pack's clips play at the rules' times (reloads warped piecewise onto the stage times), never
  the other way round; `Loadout.ParityGolden` and every `Golden.*` replay still pass with 0 mismatches.
- **Suite** (`tools/box/test.sh MurderInc`, 2026-11-23, after the web sound files were copied into the clone from a local
  `node tools/ue-export/audio.mjs` output): **TESTS OK passed=104 failed=0** (new: `FirstPerson.RealArt`, `.OpticTwin`,
  `.Clips`: 31 clips on the right skeletons).

**Open (most important first)**
1. **The translucent puffs do not show in play** (smoke, dust, blood mist): they are spawned, placed, sized and faded
   (read back from Python during a blast: 47 visible cards of 1.8 to 2.1 m, opacity 0.47 to 0.49, on M_FX_Smoke,
   which compiles: 483 instructions), lit or unlit alike, yet no picture shows them; the additive cards (flashes,
   sparks), tracers, lights and debris bodies do. So `fp-explosion.jpg` (0.42 s) shows the blast's light, the fireball's
   glow and the debris but no smoke. Next: one puff in front of the camera in a test map to find the cause, or a
   Niagara sprite system for the puffs (none is built: every effect is code on pooled components). The strike marks
   (MD_FX_Mark) and the casings were not caught in a picture.
2. The bare forearm in direct sun reads orange-red under the El (`fp-hip-el`, `fp-irons`) even with the game's shorter
   scatter (`SP_RuleSkin` 0.22 cm, Opacity 0.45): for the character agent (skin albedo / profile), see Handoffs.
3. The scope's reticle dot (1.5 mrad) is about 3 px at 32 degrees and sits under the HUD crosshair: hide the crosshair
   while aimed through an optic, or enlarge the dot (`M_TFA_AR_Reticle`, animation agent).
4. NINE: template third-person pistol clips (idle, fire); no pistol reload, holster, draw or inspect clips (the rig's
   procedural poses play them). A first-person pistol pack is still the recommended route (DECISIONS.md).
5. Goons: template rifle anim set with the SMG on `hand_r` at the CHARACTERS.md offset; no left-hand IK onto the SMG,
   no fire, reload or hit montages; the Buzzard is still the placeholder (`SK_Buzzard` imported, not driven).
6. A run started with the console `MIStart` (no set-up screens) uses presentation.json's own guns: the template way.
   The set-up flow (`fe hit`, the saved set-up) resolves the real art.
7. The CHOPPER's mounts stay `missing` (parity): DECISIONS.md allows the Short rifle's parts; not offered yet.

### First-person fix pass (independent review, 2026-11-23: grades 2 and 2)

Box re-rented (the old one had ended idle). Everything below was verified in the gameplay clone, play in editor in
L_Block, pictures retaken with `tools/box/fp/fp-shots.sh` and looked at.

**Fixed, most visible first**
- **The NINE's magazine** sits in the grip: `SM_Weapon_NineMagazine` is modelled in the pistol's space, so it rides
  the `magazine` bone at the inverse of that bone's reference pose (`UMIFirstPersonRig::MeshSpacePartOnBone`).
  New test `FirstPerson.NineMagazine`: magazine box (-1.35..4.53, +-1.3, -13.45..-3.3) cm inside SK_Nine's box, below
  the bore, centred, upright (`fp-nine.jpg`).
- **Casings** leave the port on screen (drawn at the first-person depth and size: `FirstPersonToNearWorld`), and the
  dropped magazine the same way. **Muzzle flash and tracer: still not seen in a picture** (see Not fixed). Found and
  fixed on the way: the headless editor plays at 10 to 20 frames a second and one long step aged the 0.045 s flash
  and the 0.09 s tracer past their life before they were drawn (the cards were read back hidden); flashes, lights and
  tracers now advance at most 1/60 s a frame and a tracer starts one frame in flight. Read back after that fix, the
  three flash cards are visible, 38 to 44 cm from the eye, sized right, frozen 0.02 s after a round, and a test card of
  the same material placed 40 cm in front of the eye by hand draws; yet the cards at the muzzle drew nothing. The
  flash now goes through the effects' world cards (`WorldFlash`, the Goons' flash path) at the muzzle's first-person
  point; that build was not looked at in a picture (the clone's editor was restarted by another session, see below).
- **Smoke, dust and blood mist** never drew: a bright card on M_FX_Smoke showed, 53 smoke-coloured cards at opacity
  0.5 facing the camera at 7 to 9 m left the street untouched (`fx_diag.py`, read-back from Python). M_FX_Smoke is now
  a lit, masked, dithered card (DitherTemporalAA, TSR resolves it): it takes the sun and Lumen; blast smoke lighter
  (albedo 0.07) (`fp-explosion.jpg` 0.42 s, `fp-explosion-late.jpg` 1.6 s).
- **Aiming.** The HUD crosshair fades out with smoothstep(Ads); the irons are zeroed (the front sight's direction in
  the clip's aimed pose turned onto the camera axis, per gun); the support elbow drops when aimed
  (`supportElbowDrop`, the hand kept on the handguard); the optic's reticle lit to 25,000 nits and the glass nearly
  clear (`firstPerson.opticMaterials`) (`fp-irons.jpg`, `fp-scope.jpg`).
- **Tactical reload stows** the partly used magazine (hidden at magOut, no body); only the empty reload drops one,
  drawn at the first-person depth so it is seen leaving the well (`fp-reload-tactical.jpg`, `fp-reload-empty.jpg`
  0.1 s after magOut).
- **Damage** at the edges (twelve bands, a 9 % centre wash, not the old 25 % full-frame tint) with a red wedge toward
  the hit for 1.5 s (`fp-explosion-late.jpg`).
- **MIStart** resolves the saved (or parity) set-up through the loadout resolver: a console run draws the pack rifle
  and the real arms ("chopper drawn with the pack's clips" in the log). **MIFaceEnemy** finds a walkable spot at the
  asked distance with a clear line (10.4 m for 10; `fp-goon.jpg`, and `fp-goon-5.jpg` at 5 m).
- **The Buzzard** is SK_Buzzard (props spun, gimbal on the eye, lens lit), the grey disc only in a clean checkout.
- **Goons:** the support hand is pulled onto the SMG's SupportHand point by two-bone IK after the animation
  blueprint (`UMIGoonMeshComponent`), and the drawn body turns onto the rules' aim. Not yet seen up close: at 10 m
  (`fp-goon.jpg`) the hands are a few pixels, and the 5 m picture caught no Goon in sight (not committed).
- **NINE:** a finger-only layer (the pack idle's wrap) on the support hand, and in a reload the support hand follows
  the magazine's base pad. In `fp-nine.jpg` the support fingers still read straight: the wrap needs its own pose.
- Arms re-imported from the current export (`fp-art.sh pack|put|unpack`, `import-chars.sh arms`); the dev overlay
  file on the box is deleted (the data path is presentation.json since the first pass).
- Suite: **TESTS OK passed=105 failed=0** (every `Golden.*` replay and `Loadout.ParityGolden` among them).

**Not fixed (why)**
- **The player's muzzle flash and tracer in pictures** (above). Next step: with `log LogMI Verbose`, fire with
  `MIFreezeOn fire 0.02` and read the logged muzzle point in camera space ("Flash: world cards ... muzzle in camera
  space ..."); project it to the screen and check what covers it (the support hand or the front sight at the hip),
  and take `fp-fire.jpg` aimed, where the muzzle is clear of the hands. `fp-fire.jpg` is not committed.
- The suite was last run after the effects-clamp build (6f794e2: 105 passed, 0 failed, every `Golden.*` and
  `Loadout.ParityGolden`); the two later C++ commits (the flash through `WorldFlash`, a tracer's first frame, verbose
  logs) are presentation only and were built (OK) but not run through the suite: another session restarted this
  clone's editor at 15:08 and killed the shells on the box.
- The arms' skin (saturated orange, red stripes at the El's slat shadows, tattoos, hair, pores) is the character
  agent's pass in progress (commit 5667229: resident textures, detail normal, shorter scatter, re-lettered tattoos);
  the game picks it up by re-running `fp-art.sh` + `import-chars.sh arms`. Support fingers wrapping the rail at the
  hip need per-finger targets on the rail: not done (the elbow drop only acts when aimed).
- The grey-box blockers in L_Block are the level's colliders drawn by tag (`build_block.py`, level agent): hand-off.
- Goon motion stays the template rifle set (no SMG or pistol aim set exists in the project); mask and cloth
  materials are the Goons agent's.
- NINE reload, draw and holster clips do not exist (no pistol pack); the rig's procedural poses play them.
- Effects remain code on pooled components, not Niagara systems (no scriptable Niagara authoring here); no smoke
  flipbook texture exists.

## Rule's arms in the game: hands-and-tattoos pass (character and technical artist)

**Verified 2026-11-23** in the gameplay clone (`import-chars.sh arms`, then `tools/box/fp/fp-arms-shots.sh`, play in
editor in L_Block; pictures `shots/fp-arms-*.jpg`, each looked at). Cause and fix: `CHARACTERS.md`, "SK_RuleArms,
hands-and-tattoos pass". In play `ListTextures` lists the four arms textures at full size and not streamed; the skin is
on the Standard Subsurface model (no red fringes on the sun-stripe shadow edges), R/B 2.5 brown; knuckle wrinkles,
wrist creases and the thumb nail read at the hip; the tattoos sit on the thumb side of the upper forearm (outside the
hip frame, as in the photo: `fp-arms-forearm-l/r` turn the arms to the eye to show them).
Restart (same day): the forearm close-ups now aim at the tattoo centres measured on the mesh (Unreal's glTF import
swaps the bones' local Y and Z, which had pointed the earlier close-ups at bare skin), and both tattoos read in play;
the skin's scatter is toned down (`SubsurfaceTint` 0.26 / 0.14 / 0.09, `Scatter` 0.6) after the sunlit forearm under
the El read salmon. All six `fp-arms-*.jpg` retaken after `import-chars.sh arms`.
Open (for the next pass): the NINE's support hand and the hip hold still come from the template pistol clip (the gun
rests on the palm, the fingers do not wrap); no per-gun finger pose ships; the pack clips' finger poses were not
measured against this hand's thickness.

## Exact next step (level)

1. Still boxes in L_Block, with no art anywhere: the building backs (`backs`, 7 brick masses with the window grid),
   the shanty (568), the hoist tower (571, 572), the lot sign pole (423). The 12 `ac_unit` props have no mesh and no
   `art_catalogue.json` entry (not drawn).
2. Baked interiors (`mi_interiors.py`): six rooms from the art; the racks are empty and the homes' furniture is boxes
   in the art's materials. Next: stock the shelves (the deck heights of `SM_Prop_ShelfRack_*` are not in the
   manifest), modelled sofas and beds from the art side, a lamps-on variant for the night rig.
3. Day only: vehicle lamps, neon and station lamps have day values (vehicle `E` scaled 0, neon 550 nits); the night
   rig needs lamp parameters driven by the level.
4. Not checked in a picture: the rust-streak decals' direction (none in frame in `block-v2-upper`), and the facade
   modules' seams at arm's length: `block-v2-seams.jpg` (north sidewalk at X -2600, looking east) shows the chop
   shop's block wall and the tyre cage, not facade modules: move it to n1/n2's shop fronts.
5. Backdrop: parapets and tar roofs everywhere, roof clutter (water tanks, bulkheads, condensers) within 300 m only;
   from far above it still reads as boxes with a window grid.

## Level (block-v2: the art in the level, the game played in it)

**Verified 2026-11-23** (`/project/ue/repo`, MCP 8000; pictures `docs/unreal/shots/block-v2-*.jpg`, 1920 x 1080)
- **Art transfer**: `send-art.sh pack` with the new defaults (`SM_Struct_*`, `SM_Sign_*`, `SM_Vehicle_*` added):
  1,344 MB in 7 parts, 279 GLBs, 222 texture sets (4K scans, the 8K roof bitumen); vehicles as exported at 00:52
  (the 13 `SM_Vehicle_*` in the manifest at pack time, 02:22). Import: 845 texture and material units in 104 s,
  meshes 473 s with the level; every mesh's bounds equal the manifest's to 0.0 cm. Checked in the editor:
  `T_TS_Roof_ScanBitumen_BC` 8192 x 8192, Steel_ScanRust, Brick_ScanRedCommon, Sidewalk_ScanWorn, Asphalt_ScanWorn,
  Wood_ScanPlankDark, Concrete_ScanFormed 4096 x 4096 (Galvanised_Aged stays 2048, as the art side made it). Every
  sign and tree is Nanite (the dense neon, e.g. `SM_Sign_WinesLiquors`, needs no LODs).
- **One data table for catalogue id -> mesh**: `Content/Data/art_catalogue.json` (64 ids; gameplay ids marked);
  `build_block.py` places 283 props of 57 ids (85 mesh-and-paint groups), the old note parsing is gone.
- **Vehicles** at their props.json poses: `M_MI_CarPaint` (clear coat: `MSM_CLEAR_COAT`, CustomData0 1, roughness
  0.03) with one instance per paint slot and props.json colour (`MI_Vehicle_<Car>_Paint_<RRGGBB>`), vehicle lamps
  off by day, tinted glass dark and sharp (`MI_Glass_CarTint`), chrome, rubber, plates from their sets; the crew's
  van is `SM_Vehicle_Van_Vulture` (props.json variant `vulture`).
- **Gameplay props drawn by the gameplay actors with the real meshes** (`presentation.json` `objectives.case.art`,
  `objectives.truck.art`, `explosives.<kind>.mesh`; `AMIReelCase` with lid on its hinge, reel per objective and
  beacon, `AMITruck` with `SM_Vehicle_IPXTruck` and both door leaves on their hinges (+-108.9 deg), `AMIExplosive`
  propane tank / welding rack and their wrecks as modelled). Without the art in the project the basic shapes stay.
  The level draws hidden-in-game previews of them for editor pictures and no boxes for them. Build green at e2cfe9c
  (113 s); `test.sh`: 35 of 38 pass, every `Run.*` and `Golden.*` with the changed actors; the 3 failures are
  `MurderInc.Audio.EventTable`, `.VoiceDirector`, `.VoiceRateHoldout` (the audio work in progress, not these files).
- **Structures family**: 38 instances from `placements/structures.json` (station mezzanine, stairs, bridges,
  platforms, kiosks, produce stand, hoardings, dig pen, dock, garages, the chop shop's floor, roof, mezzanine,
  stair, safe, fan); new rules: chain-link on the roadblock and the alley gate, jersey barriers across the road
  end, the tyre cage fenced with tyre stacks, the lot's knee walls, seals and railings invisible. Visible boxes
  left: 11 (item 1 above), from 30.
- **Interiors**: `mi_interiors.py` (build_block step `interiors`) builds six rooms from the art (grocery, parlour,
  store; living room, bedroom, vacant), lights them and captures HDR cube maps `/Game/Art/Interiors/TC_*` (1024);
  `M_MI_Glass` looks a cube up per window cell (one of three, half mirrored, lamp level varied); `block-v2-3` and
  `block-v2-interior` show the parlour (menu board, tiles, chairs, vending machine) through the pizza window.
- **Vertex-colour ramp test** (`mi_ramp_test.py`, art bible 3.3): an 11-step COLOR_0 ramp through the art's import
  path, captured as BaseColor into a float target: the shader receives the linear value (0.0977, 0.2012 ... 0.8945,
  1.0 for 0.1 ... 1.0: 8-bit steps), so the master's `pow(x, 2.2)` decode was wrong (0.5 became 0.216): removed.
- **Backdrop** in five brick and concrete finishes with parapets, tar roofs, water tanks, bulkheads, condensers.
- **The game in L_Block** (`tools/box/play-shots.sh`, play in editor headless): "Game: booted (art map, 757 boxes,
  21 explosives, 20 enemy slots, 3 reels)", 927 art collision primitives off; `block-v2-play-1` the start pose with
  the HUD (objective, health 100, CHOPPER 30/150), `-2` aimed down the avenue, `-3` beside the parked taxi.
- Two review rounds: round 1 fixed the vehicle view (inside the Cage's fence), the dark wood interior, the crude
  backdrop and the play pose inside the box truck; round 2 moved the seam view off a hoarding. Editor stopped at the
  end (by process id).

## Audio (voice lines and the game's sound) — first cut, in progress

Contracts and how-tos: `docs/unreal/AUDIO.md`. Built and tested in `/project/ue/repo-audio` (logs in
`/project/ue/logs/repo-audio`; no editor, no MCP port used).

**Verified 2026-11-23**
- **Build green; `test.sh MurderInc` 32 of 32 pass** (the 14 new `MurderInc.Audio.*` with every gameplay test, 32 s).
  Audio: `VoiceData` (the six lines word for word, 21 takes on disk, 48 kHz mono), `VoiceCooldowns` (line and global
  cooldowns, how-often rare / often / off), `VoiceChances` (chance 0.25 over 4,000 triggers: 0.254; same seed, same
  sequence), `VoiceNoRepeats` (300 plays, no take twice in a row, all three used), `VoicePriority` (window, crowd
  answer after the take, interruption by margin, the uninterruptible line, the queue), `VoiceCleanLanguage` (swap,
  bleep, untouched clean lines), `VoiceCharacters` (own set, empty set silent), `VoiceTriggers` (every trigger from bus
  events, streaks, last kill of a wave, the Hold the Block card), `VoiceRate` (typical Story run, 20 seeds: **2.76 lines
  a minute, 1.3 a minute on kills, 6.5 of 36 kills speak**), `EventTable` (61 bus keys incl. 28 flow lines scanned
  from the gameplay source: 21 play, 24 rules, 17 silent; all 83 replacement files present), `Director` (burst tails,
  ducks, blast muffle and recovery, pause refusal and music low-pass, death muffle, voice duck and subtitle), `Mixdown`,
  `Assets` (289 of 289 WAVs imported as Sound Waves, lengths equal, 22 loops), `EngineRender` (warns without a device).
- **Offline mix-down of a recorded fight**: `Content/Data/audio_fight.json` (52 s scripted Story fight, 799 bus events)
  replayed through the director, `Saved/Audio/fight_mixdown.wav` on the box (55.9 s stereo 48 kHz, 501 voices, peak
  -0.1 dBFS after the soft clip, RMS -17 dBFS; 7 lines: I-N-C at the start, Holla twice, Rule Baby on the last reel,
  What's my name and the crowd's R-U-L-E at the truck, I-N-C on the card).
- **The engine's own audio mixer plays it** (`tools/box/audio-engine-render.sh`, SDL dummy driver, no `-NoSound`): an
  audio device comes up ("Using Audio Hardware Device System audio playback device"), the stream replayed in real time
  started 479 audio components on the imported Sound Waves with 0 missing assets, and the master-submix recording's
  header announced 55.5 s of 6-channel audio; the file was cut short when the process quit before the background WAV
  writer finished. The test now waits for the full file; that re-run is still to do.
- **Import**: `tools/box/audio-import.sh` (headless, about 90 s): 289 Sound Waves under `/Game/Audio`, 0 failed.
- **Material**: 190 web variants rendered by `node tools/ue-export/audio.mjs` (3 s, 26.7 MB, not committed; on the box
  through the storage as `mi-audio-web.tar`), 21 placeholder voice files (generic stock voice, -18 LUFS), 79 generated
  effects + the bleep (9.8 MB); the committed audio tree is 15.5 MB. Generation spent about 53 credits (49 effects,
  about 3.5 voice); balance 3,392 at the end.

**Next**: re-run `audio-engine-render.sh` and listen to both renders; options screen wiring (`SetOptions`), crew
(`SetCharacter`), silencer (`SetSuppressed` / `bSuppressed`); music riser and Quartz grid; neon, steam and boombox
emitters; Goon step surfaces; the real voice recordings (AUDIO.md section 5).

### Audio fix pass (independent audio review, 2026-11-23)

**Verified**: build green, **`test.sh` 94 of 94 pass** (21 of them `MurderInc.Audio.*`; VoiceData warns with the placeholder count, EngineRender warns under -NoSound by design); `audio-engine-render.sh` passes with a device.

Every problem of the review addressed; AUDIO.md rewritten where the rules changed (2.1, 2.2, 2.3, 2.5, 3.3, 4, 5, 6, 7).

- **The voice rules** (`FMIVoiceRules`, `FMIVoiceTriggers`, voice.json): the win is `always` (no cooldown, no decay,
  priority 100, waits 6 s behind a line it may not cut) and shouted; takes follow the moment's `intensity`; a kill
  bark never cuts or chains onto another kill bark (`barkTriggers`); a repeat decay (x 0.8 per play of a line in a
  run); Hold the Block gets `wave.milestone` (waves 5, 10, 15 ...) and `score.newBest` feeding "What's my name", the
  last kill of a wave 0.5, the wave's "Rule Baby!" only when the kill bark did not speak; It's Murda! cooldown 40 s,
  Holla 25 s; a restart (`player:reset`, an intro not from the title) silences the voice and its queue and answer.
- **New tests** (`Tests/MIAudioVoiceTests.cpp`): `VoiceWin`, `VoiceBurst`, `VoiceDirector` (burst, pause in a line,
  restart, interruption through the whole director), `VoiceRate` (Story on Boss from config.json: **2.56 lines a
  minute, 13 % of kills speak, the win called and answered in all 20 runs**), `VoiceRateHoldout` (spec 04 2.11, 12
  waves: **2.61 lines a minute, It's Murda! 0.73 a minute, worst run 0.89; What's my name by wave 10 in every run**),
  `GenFiles` (variant length and loudness per set, silenced under open shots), `MasterChain`; extended: `VoiceData`
  (lengths, inner gaps, tails, bleep ranges, placeholder count), `VoiceTriggers` (kill after death, restart,
  milestones, new best), `VoiceIntensity`, `EventTable` (every delegate of Core/MIEvents.h must be bound: it caught
  the new `WeaponMode` at once; bound, with a selector click, and `bSuppressed` read in OnWeaponFire).
- **Proven red** before green: on the old data `VoiceData` (inc_01 3.09 s, gaps 0.78 / 0.59 s), `GenFiles`
  (chopper_close_03 11 dB off its set), `VoiceBurst` (2 lines), `VoiceRate` (3.86 a minute), `VoiceRateHoldout`
  (1.16 a minute); with the rule broken on the box clone: `VoiceWin` (no `always`: no win line in any seed),
  `VoiceData` (clean mode bleep with empty ranges), and with code breaks built on the box clone (never committed): no silence on reset or restart (`VoiceTriggers`, `VoiceDirector`: the old crowd answer played after a restart), kill barks allowed to cut each other (`VoiceBurst`: 5 cuts), intensity ignored (`VoiceIntensity`, `VoiceWin`: 2 of 10 wins shouted), a delegate left out (`EventTable`); and the engine render with the make-up at 0.0001 (peak -80.8 dBFS: red).
- **Placeholders re-cut** (`voice_placeholders.py`: gate, inner pauses 0.12 / 0.14 s, pitch-keeping tightening at
  most x 1.35): 21 takes 0.98 to 1.91 s (It's Murda! 0.98 to 1.19 s, I-N-C! 1.31 to 1.91 s, the chant 1.89 to 1.92 s),
  longest inner gap 0.08 s, -18 LUFS; the six breathed takes regenerated at a neutral rate (same preset voice, same
  text, 1.2 credits). **Effects re-cut and levelled** (`sfx_process.py`, from the same generated files): one loudness
  per variant set (momentary maximum within 0.8 dB), matched to the web sound, minimum lengths, DC and 20 Hz
  high-pass; the silenced shots 10.7 / 11.0 dB under the open ones; 31 sets pass `GenFiles`.
- **The mix**: the master chain of spec 07 2.11 (compressor, x 1.15, soft clip) on the main submix in the engine and
  in the offline mix; the ambience low-pass by interior; the music bus 0.5; master trim 1.0 (the game's volume is
  the device's primary volume, applied after the chain by UMIGameSubsystem).
- **Placeholders visible**: the log line "voice: 21 of 21 takes are placeholders", a "placeholder voice" tag under the
  subtitle in non-shipping builds, the VoiceData warning, `"placeholder": true` on the 40 generated replace layers,
  README.txt in Content/Audio/Voice/rule and Content/Audio/Gen.
- **Real recordings**: `tools/audio/voice_ingest.py` (any format, 48 kHz 24-bit mono, trim with 100 / 300 ms pads,
  -18 LUFS and -1 dBFS peaks, length and gap report, placeholder false, new takes by name, bleep marks); AUDIO.md 5
  is now a brief for a phone and for a studio with a release note. Prompt plans committed: `tools/audio/voice_plan.json`,
  `sfx_plan.json`.
- **Engine render**: **it works**: 55.57 s of 6-channel audio recorded from the main submix (the device's clock 55.57 s, the stream 54.9 s), 500 components, peak -0.0 dBFS with no clipped sample, **-16.5 LUFS integrated**, loudest 3 s -9.8 LUFS; the offline mix-down of the same stream 55.91 s, -12.5 LUFS, peak -0.0 dBFS; the six voice moments measured in both (AUDIO.md 7). Three engine-side causes found and fixed on the way: a stale complete WAV passed the wait, the dummy driver's clock drifts up to 3 % from the wall clock, and master-submix effects added at run time ran on default settings until their settings are pushed to the instances the device creates (`FMIMasterChain::Refresh`). `tools/audio/render_report.py` measures any render.
- Generation this pass: 1.2 credits (balance 3,282.7 at the start, 2,721.95 at the end). Balance figure of the first
  pass corrected to 3,358.6.

**Hand-offs** (one line each in other packages; the audio side is ready): `UMIGameSubsystem::ApplySettings`
(Flow/MIGameSubsystem.cpp) calls `UMIAudioSubsystem::Get(this)->SetOptions(...)` with the options screen's voice and
category settings; the loadout's crew apply calls `UMIAudioSubsystem::Get(this)->SetCharacter(Loadout.Crew)`;
`FMIGameRules` (Flow/MIGameRules.cpp, after `C.bNewBest = Host->SetBest(C.Score);`) emits
`if (C.bNewBest) Note(TEXT("score:best"), FString(), C.Score, C.Best);`. Clean language stays off by default: a decision
for the user (voice.json `settings.options.cleanLanguage`).

## Animation pack (Tactical FPS Animation Pack - Assault Rifle) on the CHOPPER — done

Details, mapping and what is missing: `docs/unreal/ANIMATION.md`. Scratch project `/project/ue/animpack` (MCP 8003).

**Verified 2026-11-23**
- The pack's 109 character clips are the UE5 mannequin skeleton bone for bone (88 bones, rest pose within 0.014 mm,
  30 fps, cm): imported onto SK_Mannequin with no retargeting, 139 of 139 imports (clips, rifle, magazine, weapon
  clips). Proof `shots/anim-pack-rifle.jpg`.
- 44 clips adapted by hand IK onto SK_Chopper (`Palm_R`, `Palm_L`, sights on the eye line, 16 cm eye relief) and 4
  reloads (FP and TP, tactical 2.233 s and empty 2.733 s) adjusted on the rules' marks: magazine rocked about
  `MagHinge`, LEFT-side charging handle, left-hand IK error 0.0 cm on every frame. Five SK_Chopper part clips
  (fire, dry fire, idle, two reloads). Proofs `shots/anim-fp-aimed.jpg`, `anim-grip.jpg`, `anim-fp-reload.jpg`,
  `anim-bolt-racked.jpg`, `anim-tp-reload.jpg`.
- 53 adapted assets as .uasset and FBX with `manifest.json` in `/project/ue/packs/tactical-rifle/adapted/` (never
  in git); `tools/box/anim/import-animpack.sh` imports the pack (`pack`) or copies the adapted set (`adapted`) into
  any project; both tested on a fresh copy of the mannequin project.

## Loadout (crew, four guns, attachments, block and style) — steps 1-4 and 6-11 of LOADOUT.md 9

Spec: `docs/unreal/LOADOUT.md`. Built and tested in `/project/ue/repo-gameplay` (MCP 8001).

**Verified 2026-11-23**
- **Parity holds through the new path.** `Loadout.ParityResolve`: the resolver's JSON for the default set-up (Rule,
  CHOPPER + NINE, no parts) is byte-equal to config.json's and presentation.json's objects, its `FMIWeaponDef`s equal
  `Config.Weapons` field by field (doubles compared exactly) and its view data equals `FMIViewmodelData::Load`.
  `Loadout.ParityGolden` replays the 13 weapon golden scenarios through the resolved data and
  `Loadout.ParityNextPrevious` replays all of them again with the swap press as next and as previous: 0 mismatches.
  Every existing `Golden.*` (five whole web-game runs included), `Weapons.*`, `Run.*` test still passes.
- **Data** (`FMILoadoutData`, its own error path in `UMIDataSubsystem`): `$ref`s resolved, `Loadout.DataLoads` checks
  every rule of 3.1 that needs only the data and the block's `provides` against level.json (3 reels, 29 / 17 spawns,
  21 explosives, 14 title keys).
- **Rules** (`FMIWeaponRules`): slots 1-4, quick swap to the last gun used, next / previous, retarget mid-holster,
  per-gun holster and draw, one shared bag (150, `AddReserve` once per pool), fire modes with the Selector activity
  (blocks fire, holds a pending auto reload, cancelled by a swap), falloff and noise radius in the shot, the aimed
  field of view and look per gun. `Weapons.FourGuns` covers each case of 8.3 including the mixed-timing reversal
  (`0.27 x (1 - T / 0.24)`) and the re-holster mid-draw.
- **Input** (`FMISwitchInput` in `AMIPlayerController`): Q / Y on press with one or two guns, tap-on-release and
  hold-for-wheel with three or more, the wheel by mouse travel or right stick (dead zone 0.5), the debounced mouse
  wheel, View tap (selector) and hold (inspect). `Player.ControllerSwitching`; `Core.GameClasses` now 68 mappings.
- **Attachments**: effects applied to the gun's JSON in web units before parsing. `Attachments.<part>.<stat>` (40
  cases from attachments.json: 37 effects and 3 baselines), `Attachments.Builds` (the six builds of 3.3, and the
  CHOPPER with scope and silencer at 20 / 37.5 / 60 m: 26, 24.05, 22.1), `.Ops`, `.Clamps`, `.Falloff`.
- **Flow** (`FMIFrontEndRules`, `UMIRunSetupSubsystem`, the set-up in the save game): `Frontend.Walk` (8.5 steps 1-8 on
  the rules), `Save.SetupRoundTrip`, `Save.SetupValidation` (each rule of 7, and a clean checkout degrading a saved
  STICK to the parity guns), `Frontend.WalkWorld` and `Loadout.ParityPIE` (the flow in a world with the real player:
  Hit the block from the Briefing, the weapon's data is the resolver's parity output, a 1 s Q hold with two guns is
  one swap on the press frame and no wheel, Change set-up on the death card opens the Briefing).
- **Screens** (Slate, `SMIFrontEnd` + `UMIFrontEnd`, replacing the canvas title): Home (the web title with the
  pickers, Hit the block, Gear up, the summary links), Crew, Loadout (rack three wide, class tabs, stat bars, the four
  slots, melee, the bag note), Workbench (carried-gun strip, slot tabs, options with Fitted, effect lines from the
  resolver with their marks, bars before / after, hold to reset), Block & Style, Briefing (four lines with Change, the
  controls strip); keyboard, mouse and gamepad through one `Act()`; console twin `MIMenu fe <action>`. The 3D stage
  `AMIShowroom` (closed room 1 km up, own lights and fixed exposure, turntable with `UMIGunAssembly`, the arms at the
  eye with first-person rendering). The four-slot HUD bar (pips, AUTO / SEMI, attachment pips, melee, the bag) and the
  weapon wheel. Pictures `shots/loadout-*.jpg` (`tools/box/loadout-shots.sh`; the pack rifles and parts through the
  dev-only `MISetup overlay`, because guns.json / attachments.json do not yet name the imported meshes).
- Audio hooks: crew to `SetCharacter`, each gun's silencer to `SetSuppressed`, the volume setting to `SetOptions`
  (master), and `FMIShotFiredEvent.bSuppressed` / `NoiseRadius` on every round.

**Open (most important first)**
1. The pack import's data (LOADOUT.md 6.2, animation agent): guns.json `variants.*.mesh` / statuses for Short,
   Extended and the folded stocks, the mounts' `exists`, attachments.json `presentation.mesh`, and the socket pass
   (`Optic`, `MuzzleMount`, ...). Until then the Workbench shows "No parts on this gun yet" outside the dev overlay,
   and parts sit at the data's provisional markers instead of sockets.
2. Crew phase-1 material instances (6.4, characters): only Rule is offered; the code applies a look by material slot
   on the arms and the template lines for DEUCE, SMOKE and KEYS.
3. Step 12 (pack clips: inspect, magazine check, selector, swings, quick and empty-retain reloads, dry tap-rack): no
   pack clip is in the gameplay project yet; the inspect and selector inputs reach the rules and the HUD only.
4. Not built: the probes in play of 8.2 (aim frames, view field of view, kick sum, the Goon behind a wall hearing a
   silenced round), a second level (the split Block / Style screens and level travel), the gun silhouettes and part
   pips as icons (names and squares stand in), `Ops` / `Clamps` fixtures as files (built in code).
5. `Audio.EventTable` asks for the new `WeaponMode` bus delegate to be bound in `FMIAudioDirector` (audio agent).
6. Seen in the pictures: the Crew stage shows the first gun first-person but not the template arms; the rack's
   turntable frames the CHOPPER stand-in as a close-up (the STICK on the Workbench frames whole); pack parts sit at
   the provisional markers (the vertical grip reads, the scope and silencer do not yet). Headless pictures are the
   editor's play viewport (1013 x 550), so the type is smaller than at 1080p.

Final suite before the fix pass (2026-11-23): `test.sh MurderInc` TESTS FAILED passed=93 failed=1 (`Audio.EventTable`: 188 web sound
files missing, the audio agent's).

Correction (fix pass below): items 1 and 6 above and the note on the pictures are out of date. The animation agent's
commit 464cb44 already names the pack meshes in guns.json and attachments.json, and the box offers SHORTY, STICK,
STRETCH and every part but the folded stock with no overlay. `loadout-shots.sh` no longer takes an overlay.

### Loadout fix pass (independent review, 2026-11-23)

- **Order on a pad and the keyboard.** Start is Next on every set-up screen (Hit the block on Home and the Briefing);
  the jump to the Briefing is Ctrl+Enter or View+Start. Next takes the focus: Tab cycles rack, slots, Next; Down past
  the last row lands on it; Enter / A there advances. `Frontend.WalkWorld` (keyboard) and `Frontend.WalkPad` walk Home
  to the run with real key events only (`UMIFrontEnd::PressKey` → `FSlateApplication::ProcessKeyDownEvent`; the
  screens sit in a virtual window in the test world). Console `MIKey <key>` does the same in play in editor.
- **Glyphs.** Marks, arrows and pips are shapes (`SMIMark`); every face falls back to the engine's Droid Sans Fallback
  (Noto Sans Symbols 2 was tried: it has no arrows). The front end logs characters no face has; `Frontend.Glyphs`
  reads the fonts' character maps and fails on any character of frontend_text.json or text.json without a glyph.
  Key names come from `frontend.glyphs.<kbm|pad>` (new keys back, next, toBriefing, prevGun, nextGun, reset, bench,
  melee, empty, panes) for the device used last; no string is written in the code (the HUD's "Pick a gun" too).
- **Layout.** Every control of every set-up screen lives in the left 40 % column (the slots are a strip under the
  rack, the effect lines wrap beside the bars, the Briefing's Carrying line wraps name plus pips, the controls strip
  wraps); focus rings pad their row; the smallest text is 14 pt. The world's objective markers hide while the wheel
  is open. `MIViewSize <w> <h>` resizes the window around the play viewport for pictures at 16:9, 21:9 and 4K.
- **Stage.** The turntable fits the gun from its mesh bounds into the free 60 % at the viewport's aspect ratio; on the
  Workbench it aims at the slot's mount socket (frontend.json offset only without a socket), turns that side to the
  camera, stops spinning and lights the mount with its own spot; the room lights aim at the gun (they aimed 86 cm
  below it). Crew shows the member's own arms (placed on the grip every frame, as in play) or, while those arms are
  not in the project, the turntable; the Briefing hides the template arms (hand-off below).
- **NEW.** The card focused when Loadout opens is seen; `WalkWorld` checks a focused card loses NEW and keeps it
  through a save.
- **Tests added:** `Loadout.MountsExist` (13 pack meshes, 83 sockets on the box; says so and passes when the pack is
  absent), `Loadout.BuildPIE` (STICK with scope and silencer plus a bare CHOPPER through the run reset: the weapon's
  data is the resolver's, the view at full aim 30°, the silenced round heard at 15 m and not 30 m, the bare one at
  30 m), `Enemies.GunfireRadius` (the throttle exception), `Player.ControllerKeys` (a local player and the
  controller's own mapping context through `InputKey`: 3, Q tap and hold, D-pad right, wheel, B), `Frontend.WalkPad`,
  `Frontend.Glyphs`. Each was seen red with its rule broken on the box (Start back to the Briefing jump, Next not
  focusable, no seen-on-arrival, no throttle exception, no symbol face, no `ApplyRun`, noise / 10 instead of / 100,
  the 3 key unmapped), then green.
- Found while retaking the pictures: parts fitted while the rack's swap had the turntable scaled out came out 16 times
  too big (they kept their world scale); they now take the gun's scale (`Loadout.PartsScale`, seen red first). The
  title camera kept a 16:9 constraint and pillarboxed Home and Block & Style at 21:9; it now fills the screen.
- Pictures (play in editor, `tools/box/loadout-shots.sh`, no overlay): `shots/loadout-{home,crew,rack,workbench,
  workbench-muzzle,workbench-grip,where,briefing,hud,wheel}.jpg` at 1918 x 1086, and every set-up screen at 21:9
  (2561 x 1086) and 4K (3836 x 2166, stored at 1920 wide) in `shots/loadout-sizes/`. The layout is the same at each
  size: every panel in the left column, the gun whole in the free part.
- `MISetup overlay`, `MIKey`, `MIViewSize` and `EditLoadoutForDev` are compiled out of shipping builds.
- **Hand-off (characters / animation):** in first person the template body's upper arm and a black disc cover the
  lower left, the support arm stretches sideways when aiming and the pack STICK sits low; hide or cull the template
  upper arm and clamp the support-hand reach. The Briefing hides the arms until then.

Final suite after the fix pass (2026-11-23, 644d4d2): `test.sh MurderInc` TESTS FAILED passed=100 failed=1 (only
`Audio.EventTable`, the audio agent's: 188 web sound files missing). `Loadout.ParityGolden` and
`Loadout.ParityNextPrevious` replay the 13 weapon scenarios with 0 mismatches; every `Golden.*` passes.

## Gameplay (slice 2: the enemies and the flow) — in progress

Contracts: `docs/unreal/GAMEPLAY.md` sections 6 to 11. Built and tested in `/project/ue/repo-gameplay` (MCP 8001).

**Verified 2026-11-23**
- **Build green, 18 of 18 tests pass** (`test.sh` TESTS OK passed=18 failed=0, 32 s for the whole suite).
- `MurderInc.Golden.FlowRules` and `MurderInc.Golden.Directors` (FMIGameRules = `src/game.js` with the enemies on the
  box world: a whole Story run to the IPX truck, a Story run that dies, four waves of Hold the Block, replayed frame by
  frame against the web game: state, clocks, reels, waves, score, queue, alive count, caps, pursuit, music, hold
  progress and every flow event): pass, 0 mismatches.
- **The game in a world** (`UMIGameSubsystem`, `MurderInc.Run.*`, headless world with collision, real player
  character and weapon, enemy actors with hit volumes, engine traces):
  - `Run.StoryComplete`: a bot that follows the objective data took the three reels and reached the truck in 82.3 s
    of game time on Boss: 35 kills (all by the CHOPPER's rounds through the Goons' and Buzzards' hit volumes), 189
    rounds, 148 hits, 46 enemy rounds fired, 16 hits on the player; debrief card "Diamond", truck doors open, cases
    taken, menu on the debrief.
  - `Run.StoryDeath`: on Kingpin a bot that does not fight dies after 9.7 s (16 enemy rounds, 10 hits); the death
    card at 1.5 s; Run it back: intro, one retry, full health at the start, no reel.
  - `Run.HoldTheBlock`: three waves cleared in 77.7 s, score 6,905 from 27 kills, two resupplies, the death card with
    score and a new best.
  - `Run.Menus`: settings validation as the web game (fov 200 to 95, 74.6 to 75, sens 0.01 to 0.2, volume 2 to 1,
    quality 'test' refused, best rounding); title menu, mode picker, start, intro to playing, pause card with the
    0.35 s debounce, settings from the pause card, resume.
- Pitfall found: in a hand-made test world tick functions run once per engine frame; the test advances
  `GFrameCounter` per step as the engine's `FTestWorldWrapper` does (without it nothing but tickable objects ticks).
- `Golden.Directors` now also replays Story on Hustler (4,000 frames, 53,520 checks) and Hold the Block on Kingpin
  (3,000 frames, 39,306 checks): 0 mismatches; all five whole runs of the web game agree with the C++.
- **Play in editor, the same code in both maps** (`L_GreyBlock` from `mi_greyblock_map.py`; `L_Block` copied from the
  level clone): the game boots from `AMIGameMode` (`BlockMaps`), "art map: 923 art collision primitives switched off,
  the data's boxes decide", 757 boxes, 21 explosives, 20 enemy slots, 3 reels. Pictures: `shots/gameplay-v2-title.jpg`
  (title menu), `gameplay-v2-greybox.jpg` (the block as grey boxes, objective markers), `gameplay-v2-block.jpg` (the
  art map, objective and markers), `gameplay-v2-goon.jpg` (two Goons with the template rifle animation blueprint
  aiming from the rules, a Buzzard above, the player already hit: HEALTH 32).

**Open (most important first)**
1. Enemy animation: the template rifle animation blueprint on the mannequin follows the rules' velocity and aim
   pitch; no aim offset yaw, telegraph, fire, rush or hit-reaction montages yet (the presentation contract exposes
   them: `FMIEnemyView`); the Buzzard is a basic-shape placeholder. Effects and sounds are hooks on the event bus.
2. The weapon-position setting (`view`) is stored and validated but the viewmodel does not read it yet.
3. Gamepad look curve and aim slow-down, rumble (slice 1 leftovers) are still open.
4. The title fly-through is linear along the level's cinematic keys (no centripetal curve, no sway, no fade-out of
   the loop); the menus are canvas text, not UMG/CommonUI.
5. `L_Block` still draws its own grey boxes for the 21 explosives and 3 cases (their collision is switched off at
   run time); `build_block.py` could skip owner kinds `explosive` and `objective` (LEVEL agent).

## Gameplay (slice 1: the player and the two guns)

Contracts: `docs/unreal/GAMEPLAY.md`. Built and tested in the second clone `/project/ue/repo-gameplay` (MCP 8001).

**Verified 2026-11-22**
- **Build green, 9 of 9 tests pass** (`build-status.sh` BUILD OK; `test.sh` TESTS OK passed=9 failed=0, 22 s):
  `MurderInc.Core.DataLoads`, `Core.GameClasses` (38 key mappings), `Golden.Rng`, `Golden.PlayerPure`,
  `Golden.PlayerSim`, `Golden.Weapon`, `Golden.Blast` (the C++ rules replay every frame of the web game's own
  modules: `node tools/ue-export/golden.mjs` writes `Content/Data/golden/*.json`), `Weapons.ViewmodelRig` (aimed, the
  rear sight sits on the view axis within 0.02 cm at 16.0 cm relief for the CHOPPER and 37.0 cm for the NINE; a round
  kicks the gun more than 2 mm and it settles within 0.3 mm), `Weapons.HitscanDummyBlast` (in a world with collision:
  a body round deals 26, a head round 26 x 2.2, a miss misses, a player round lights a propane tank, the fuse runs
  out and the blast hurts the dummy by 170 x (1 - d / 650 cm)).
- **Play in editor** on `/Game/Maps/L_GameplayTest` (`mi_gameplay_testmap.py`, `tools/box/pie.sh`): the player stands
  (feet on the floor, eye 168 cm), the HUD draws health, ammunition and the crosshair, the template rifle sits at the
  CHOPPER's hip pose (`docs/unreal/shots/gameplay-v0-hip.jpg`); `MIInput ads 1` brings the sight onto the crosshair
  (`gameplay-v0-ads.jpg`); `MIInput fire 1` for 0.6 s killed the dummy 7 m ahead (it keeled over). No tick cycle
  warnings after moving the frame into two tick functions.
- `config.json` numbers were rounded to 4 decimals by the exporter (shake.onHit.perDamage 0.0143 for 1/70);
  `golden.mjs` restores full precision for the player, weapon and explosive tables (3 numbers changed).

**Open (most important first)**
1. The arms are the template mannequin placed by its right-hand socket on the gun's grip, playing one ADS idle: the
   left hand does not hold the handguard at the hip and the reload, draw and strike have no hand animation. Needs the
   animation layer (two-bone IK to `Palm_R` / `Palm_L`, reload montages to spec 02 3.17) on the real arms.
2. Not ported yet: the air step (8 cm), the play-bounds clamp and fall-out teleport, gamepad look curve and aim
   slow-down input, the mouse-wheel swap debounce, rumble, muzzle flash, casings, impact effects, sounds, the
   damage post-process, the explosives' wreck meshes and jets (grey boxes), the settings menu.
3. Tracers are line-batcher streaks (no Niagara yet). The dummy and the explosive are engine basic shapes.
4. The movement is the stock walking and falling with the rules' velocity: the golden replay covers the rules on
   flat ground; steps, ledges and the parity table of spec 01 4.9 are not measured in a level yet.

## 2026-11-22

- **block-v1: the avenue with the facade kit, props, furniture, decals and backdrop** (`docs/unreal/shots/block-v1-1.jpg`
  ... `-6.jpg`, 1920 x 1080, `shot.sh` through the piloted viewport, 60 warm-up frames): 1 eye level at the start pose
  looking east; 2 the south block face from the north sidewalk; 3 the pizza shop front up close; 4 under the El
  looking up; 5 the avenue from mid-block looking west; 6 high overview. Three picture rounds (sheets looked at each
  time): round 1 found every remaining box textured as concrete, cameras inside the produce stand and behind vans,
  pastel shop interiors and black shade; round 2 found the chain-link drawn opaque, gum spots too dense, the backdrop
  brick too pink; round 3 is the committed set.
  - **Facade kit on the five street-facing buildings** n1, n2, s1, s2, s3: 985 instances of 77 modules from
    `art/out/placements/buildings.json` (`art/blender/place_buildings.py`: the kit's own `assemble_front` /
    `assemble_shell` plus closing walls for the backs), one actor per building with one InstancedStaticMeshComponent
    per module (added through `SubobjectDataSubsystem`, saved with the level), no collision; awnings per shop colour
    (`MI_Fabric_ScanCanvas_<Shop>`). The buildings' 337 colliders stay as invisible blocking boxes (`Block/Collision`):
    the tuned cover and openings are unchanged. Every imported mesh matched its manifest bounds to 0.0 cm (190 GLBs).
  - **Props from props.json** by catalogue id where a mesh exists (catalogue ids parsed from the manifest notes; the
    modelled furniture before the scans): 217 dressing props of 36 ids, footprint centre aligned to the catalogue
    shape's (the fire-escape balcony's pivot is its left end); fire escapes the facade kit already draws are skipped.
  - **Level structures from the furniture family**: the auto body shop's block walls tiled along its colliders with
    the 6.0 x 4.3 and 3.8 x 3.5 openings, open roll-up doors and the side-door module; the Cage's knee walls,
    chain-link panels and end posts; chain-link round both rolling scaffolds; the sidewalk shed and its stair at the
    manifest's placement. Remaining boxes wear the material of what they are (`TAG_SURFACE`: El green steel for the
    station, plywood hoardings, painted block, brick backs with windows); vehicles are dark paint.
  - **Materials**: `M_MI_Surface` gained a detail layer (the set's own normal and roughness at 4.37 x, faded in within
    3 m), macro variation (value, hue and roughness noise at 4 and 14 m), sign emission (E maps, 900 nits) and a
    window grid for world-projected masses; `M_MI_SurfaceMasked` (two-sided, BC alpha clip) for chain-link;
    `M_MI_Glass` (opaque glass, Lumen reflections, a world-space interior room per window: wall paint, furniture or
    shop shelving, lamp on in one room in six, grime at the sill); `M_MI_Flat` for chrome, aluminium, blinds, lenses and
    sign stand-ins; `M_MI_Decal` with seven procedural kinds.
  - **Decals by rule** (seeded): 153 (22 road cracks, 7 patches, 32 oil, 10 tyre marks, 48 gum patches, 18 stains at
    the manholes and under the El's edges and rails, 16 rust streaks under window sills).
  - **Sky and backdrop**: volumetric clouds (engine simple cloud material, layer 1.6 to 7.6 km), far ground to 5 km,
    the avenue's street walls continued to 450 m, 318 city and skyline masses out to 4.5 km, all with windows.
    Exposure: auto exposure EV100 12.3 to 14.2, local exposure shadow contrast 0.45, sun shafts (volumetric scattering
    3, volumetric fog extinction x 5): the shade under the El reads and the shafts show through the ties.
  - **Hardware ray tracing on this box's Vulkan driver**: NVIDIA 620.70 exposes VK_KHR_ray_tracing_pipeline,
    VK_KHR_acceleration_structure and VK_KHR_ray_query; editor.log says "Ray tracing is enabled", "Ray tracing
    shaders are enabled" and allocates the ray-tracing scene (`FRayTracingScene::SceneBuffer`); the project sets
    `r.RayTracing=True`, `r.Lumen.HardwareRayTracing=True` (BOX.md section 1).
  - Editor stopped at the end (`editor.sh stop`, by process id).

- **The block in Unreal, first pictures** (`docs/unreal/shots/block-v0-1.jpg` ... `-4.jpg`, 1920 x 1080, through
  `tools/box/block-shots.sh`): eye level at the player start looking east under the El; a south-row column and its
  pedestal; under the deck looking up at a bent; a high overview of the block. Two review rounds: round 1 fixed
  black shade (scene captures had no sky light and no Lumen: pictures now come from the piloted editor viewport and
  HighResShot), clipped cached lighting (pre-exposure 8), too dark exposure (clamped auto exposure EV100 12.9 to
  14.2) and brick on the roofs of the massing (concrete on upward faces); round 2 moved the column and deck cameras
  out of grey-box clutter.
- **`/Game/Maps/L_Block` assembled from data** by `unreal/MurderInc/Content/Python/build_block.py` (`block.sh start
  level`, 7 s, 920 actors, saved): 7 road pieces and 140 kerb and sidewalk modules along the avenue (X -70 to +70 m,
  gutter lines at Y +-700); the El from `level.json` `el` (18 bents, 17 girder spans and decks, 36 columns, 9 lamps
  at the `atmos.json` El lamp positions; deck underside at Z 650 as the mesh bounds show); 657 grey-box cubes, one per
  movement-blocking static collider of `level.json` (bullet-only colliders and the ones the El and street meshes
  draw are skipped), with world-projected scanned brick or concrete by collider surface; 12 ground slabs from
  `ground.surfaces` off the avenue and a far ground plane; a player start at `playerStart`; the day rig from
  `atmos.json` `rigs.day`: sun at pitch -52.0 yaw -26.1 and 99,956 lx (5 game lux x 24,400 lx x colour
  luminance, spec 06 4.5), source angle 0.5357, atmosphere sun light; sky atmosphere with 2.5 x Mie scattering; real-time
  sky light; height fog for about half of the web haze at 92 m (density 0.0047) with volumetric fog; unbound
  post-process volume with Lumen GI and reflections, clamped auto exposure, bloom 0.25 without threshold, vignette
  0.15, white balance 6,300 K, local exposure, saturation 1.05.
- **Art imported** (`block.sh start textures,materials,meshes`): 60 textures of 20 sets, the master material
  `M_MI_Surface` (base colour, normal, ORM, tint, optional second set on G, the four `Wear` masks with a value-noise
  breakup, world box projection for the grey-box) and 30 instances, 16 meshes with Nanite. Every mesh's bounds equal
  the manifest's Unreal bounds to 0.0 cm: axes and scale right, unmirrored (BOX.md section 5). The lamp lens slot
  (`TS_Glass_SodiumLens`, no texture set yet) uses a warm-tinted concrete stand-in.
- **Art transfer** works: `send-art.sh pack` (163 MB, 16 GLBs, 21 sets), `send-art.sh put` (19 s), `media_confirm`
  type file, box download and unpack to `/project/ue/art-in` (4 s). `receive-art.sh` is the box half.
- **Build and tests green**: `build-status.sh` BUILD OK (127 s game module build), `test.sh` TESTS OK passed=2
  failed=0 (29 s), run again after the last change. Editor stopped at the end.
- `docs/unreal/BOX.md` written: the loop, timings, every pitfall the scripts encode.

## Before 2026-11-22 (the bootstrap)

- The project `unreal/MurderInc` compiles on the box (`-NoUBA`), the headless editor starts with its MCP server, the
  bootstrap map `L_Bootstrap` is built by `mi_bootstrap_map.py`, and a picture of it came back through the transfer
  procedure (`docs/unreal/shots/bootstrap.jpg`; its black shade is the scene-capture limit found later).
