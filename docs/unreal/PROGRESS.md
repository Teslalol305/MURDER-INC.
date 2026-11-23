# Unreal rebuild: progress

What is verified on the box, newest first. Every entry says how it was verified. The loop and the pitfalls are in
`docs/unreal/BOX.md`.

## Exact next step

1. Level structures still drawn as boxes in their material (05-level): the El station stairs and mezzanine
   (`station`, 23 colliders, the biggest walk-up box at the player start), the kiosk, the produce stand, hoardings,
   the dock, the garages, the chop shop's office, mezzanine, stair and roof. Each needs a furniture-family module
   (art side) or a placement rule in `build_block.py` `structure_placements` like the shop walls and the Cage.
2. Texture sets under about 1,024 px/m near the player (manifest `texel_density_px_per_m`): roof bitumen 379,
   galvanised 512, road paint 512, El column concrete 756, Steel_ScanRust 931, Brick_ScanRedCommon 946,
   Sidewalk_ScanWorn 975, Asphalt_ScanWorn 985, Shutter 990, Asphalt_ScanFresh 994, Wood_ScanPlankDark 996:
   `art/scans/fetch.py` can fetch 4K versions. The tinted paint slots (Steel_Paint*) carry no tile size.
3. Vehicles stay dark-paint masses until the vehicle family arrives; the explosives (21) and the master cases (3) are
   gameplay actors (props.json role `explosive` / `objective`) and stay boxes in L_Block until the gameplay side
   spawns them.
4. Prove the vertex-colour decode with a ramp test asset (art bible 3.3), BOX.md section 5.
5. Signs: 14 `Sign_*` sets were in the transfer (BC, ORM, E); the signs family was still being made. Re-run
   `send-art.sh pack` + transfer + `block.sh start textures,materials force` + `block.sh start meshes,level` when it
   is finished: sign slots without a set show the neutral stand-in `SIGN_STAND_IN`.

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
