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
