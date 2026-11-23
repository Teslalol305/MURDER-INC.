# The Unreal box: how to work on it

The rented Linux GPU box (RTX PRO 6000, 16 cores, 64 GB) runs Unreal Engine 5.9.0 (preview 2, changelist 60738873).
It costs about 114 credits per hour while it runs: keep the loop short, stop the editor when done.
Every script below lives in `tools/box/` and is mirrored on the box at `/project/ue/repo/tools/box/`.

## 1. Facts of the box

| Fact | Consequence |
|---|---|
| `/project` is persistent storage on a 9p network file system; everything else is lost when the box stops | The engine (`/project/ue/UnrealEngine`), the repository mirror (`/project/ue/repo`), the cache (`/project/ue/ddc`), the logs (`/project/ue/logs`) and the received art (`/project/ue/art-in`) live there. Never run recursive `du`/`find` over the engine: minutes. |
| The engine, the build tools and git on the mirror refuse root | Every script re-executes itself as user `ue4` (`mi_become_ue4` in `lib.sh`). After a box restart run `/project/ue/setup-box.sh` (re-creates `ue4` and the system packages; `/project/ue/logs/setup.log` ends with `SETUP-DONE`). |
| One command per MCP call, 45 s at most | Anything longer is started detached (`setsid nohup ... &`) and polled: `build.sh`/`build-status.sh`, `test.sh`/`test.sh status`, `block.sh start`/`block.sh wait`. Never `pkill -f`/`pgrep -f` (they match the calling shell): `pkill -x UnrealEditor`, `CrashReportClie`, `ShaderCompileWo` (names cut to 15 characters). |
| The stock Zen local cache cannot be reached | Every editor or `UnrealEditor-Cmd` start passes the file-system cache graph and turns Zen auto-launch off: `-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal) -ini:Engine:[Zen]:AutoLaunch=false` plus `UE-LocalDataCachePath=/project/ue/ddc` (`MI_CACHE_ARGS` in `lib.sh`, `/project/ue/bin/run-editor.sh`). |
| Windows abort the editor (Vulkan bridge PrimusVK) | Headless only: `-RenderOffscreen -unattended -nosplash -NoSound` (`editor.sh`). Pictures come from scene captures (`shot.sh`). |
| The Unreal Build Accelerator asserts on the 9p volume (`rename-while-open ... .gch.tmp`) | `build.sh` always passes `-NoUBA`. |
| The asset registry watches every directory of `Engine/Plugins` (55,000 on 9p: 10 to 25 minutes per editor start) | `-ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1` on every editor process (`MI_EDITOR_ARGS`). Files copied into `Content/` while the editor runs are not seen until a restart or `scan_paths_synchronous`. |
| Scene captures get no real-time sky light (`ReflectionEnvironmentRealTimeCapture.cpp` skips scene-capture views) and no Lumen lighting here: every shade is black, whatever the frame count. The headless level viewport is a main view, but it only draws when asked | `shot.sh ... cam=...` pilots the level editor viewport with a transient camera actor (position, rotation, field of view), forces `frames` redraws through the MCP tool `CaptureEditorViewport` so Lumen, the sky capture, auto exposure and TSR settle, then takes `HighResShot <size>` (written on a later redraw, after `r.HighResScreenshotDelay`). The old scene-capture path stays as `view=capture`. |
| Physically based daylight overflows the default cached-lighting range: "Cached lighting in Lumen and real-time sky capture lighting is going to be clipped" on screen, and darker shade | `r.EyeAdaptation.CachedLightingPreExposure=8` in `Config/DefaultEngine.ini` `[SystemSettings]` (covers EV -4 to 16). |
| Deleting a material that instances use orphans them; each orphan then compiles the default material synchronously on the game thread | `build_block.py` rebuilds the master material and its instances in place, never deletes them. |
| Hardware ray tracing works on this driver (NVIDIA 620.70, Vulkan) | `vulkaninfo` lists `VK_KHR_ray_tracing_pipeline`, `VK_KHR_acceleration_structure`, `VK_KHR_ray_query` on the RTX PRO 6000; editor.log: "Ray tracing is enabled", "Ray tracing shaders are enabled", and the ray-tracing scene buffer is allocated. `Config/DefaultEngine.ini` keeps `r.RayTracing=True` and `r.Lumen.HardwareRayTracing=True`. |
| The first editor start on a fresh box takes about 10 minutes (9p reads, shader maps), later ones about 40 s | Start the editor first, do the local work while it comes up; `editor.sh status` says when MCP answers. |
| Editor tools refuse to run while the editor compiles shaders ("running a slow task") | Retry `block.sh start` / `shot.sh` after a few seconds; the first pictures after a material rebuild wait for the compile. |
| Files reach the box only through git (the box pulls the public repository, it cannot push) and through the user's Higgsfield storage | Commit and push locally, then `sync.sh` on the box. Big binary inputs (the Blender art) go through storage (section 4). |

## 2. The loop

| Step | Command on the box (`cd /project/ue/repo/tools/box`) | Time measured |
|---|---|---|
| Pull the branch | `bash sync.sh` (says `next: build.sh` when C++ changed) | 2 to 5 s |
| Build the editor target | `bash build.sh` then poll `bash build-status.sh` (`-w` for warnings) | 127 s for the game module after a C++ change; stops a running editor first |
| Tests | `bash test.sh` (all `MurderInc.*`, headless `-NullRHI` in `UnrealEditor-Cmd`), poll `bash test.sh status` | 33 s for the two current tests |
| Editor | `bash editor.sh start [/Game/Maps/L_Block]`, `status`, `stop`, `restart` | MCP answers about 40 s after start |
| Run editor Python | `python3 mi_mcp.py py <file.py or ->` (value of the last expression) | under 45 s per call |
| Build the block | `bash block.sh start [steps] [force]`, `bash block.sh wait` | textures + meshes 138 s (277 textures, 190 GLBs with Nanite), materials 65 to 96 s with force (6 masters, 160 instances; shaders compile afterwards for a minute or two), level 5 to 16 s (1,083 actors, 1,350 instances) |
| Picture | `bash shot.sh /project/ue/logs/shots/x.jpg cam=X,Y,Z,pitch,yaw,roll fov=80 frames=60` | about 12 s at 1920 x 1080 with 60 warm-up redraws (fewer leave Lumen unsettled after a camera jump; 60 and 200 give the same picture) |
| The six block views | `bash block-shots.sh` (detached: about 75 s) | |
| Picture to the local checkout | `media_upload` (filename `mi-x.jpg`), `bash put.sh <jpg> <upload_url> image/jpeg`, `media_confirm` (type image), local `curl -o` the url | about 10 s; several thousand tokens per picture |
| Many pictures at once | `tar -cf /tmp/x.tar block-v2-*.jpg` on the box, one `media_upload` (`.tar`, `application/octet-stream`), `put.sh`, `media_confirm` type `file`, local `curl` + `tar -xf`; look at 2 x 2 sheets made locally | 15 pictures, 4.7 MB in one transfer |
| The game through the player's eyes | `bash play-shots.sh [out] [prefix]` (detached; L_Block open): play in editor, `MIStart mission skip`, three poses with the HUD | about 2 minutes |
| Baked interiors | `block.sh start interiors` (then `materials` so the glass instances take the cubes) | 16 s for six rooms |

`mi_mcp.py` is the MCP client: `toolsets [text]`, `describe <Toolset> [Tool]`, `tool <Toolset.Tool> '<json>'`,
`py`, `level`, `shot`. A play-in-editor session left running blocks level queries ("Cannot get the current level
while PIE is active"): `python3 mi_mcp.py tool EditorToolset.EditorAppToolset.StopPIE '{}'`.

## 3. Generated content

Nothing under `unreal/MurderInc/Content/` is committed except `Data/*.json` and `Python/*.py`. Generated content is
rebuilt on the box by committed scripts:

| Content | Script |
|---|---|
| Template placeholder art (arms, weapons, input) | `seed-content.sh` (editor stopped) |
| `/Game/Maps/L_Bootstrap` | `mi_mcp.py py unreal/MurderInc/Content/Python/mi_bootstrap_map.py` |
| `/Game/Art/*` and `/Game/Maps/L_Block` | `send-art.sh` (local) + `receive-art.sh` (box) + `block.sh start all` |

## 4. Art transfer (Blender outputs to the box)

The Blender outputs (`art/out/`, git-ignored) travel as one tar through the user's Higgsfield storage:

1. Local: `tools/box/send-art.sh pack` makes `art/out/mi-art-<k>.tar` parts of at most 240 MB (the storage's upload
   front answers 413 above about 500 MB): every `SM_El_*`, `SM_Street_*`, `SM_Facade_*`, `SM_Prop_*`,
   `SM_Gameplay_*`, `SM_Furn_*` GLB (patterns are arguments), every texture set their slots name (BC, N, ORM, E;
   height maps left out), the grey-box sets, `manifest.json` and `placements/*.json`. 611 MB in 3 parts for 190
   meshes and 96 sets; with the structures, signs and vehicles (block-v2) 1,344 MB in 7 parts, 279 GLBs, 222 sets
   (the seven PUTs in parallel about 2 minutes, `receive-art.sh` about 3 minutes).
2. `mcp__Higgsfield__media_upload` with one filename per part (`files` takes several) gives `upload_url`, `url` and
   `media_id` each. The upload address is signed for the headers `content-type` and `if-none-match`: send
   `Content-Type: application/octet-stream` (the type the tool states) and `If-None-Match: *`.
3. Local: `tools/box/send-art.sh put "<upload_url>" application/octet-stream art/out/mi-art-<k>.tar` per part (the
   three in parallel: about 60 s; retries with `If-None-Match: *` on 403).
4. `mcp__Higgsfield__media_confirm` with the `media_ids` and type `file`.
5. Box: `bash receive-art.sh "<url1>" "<url2>" ...` downloads and unpacks all parts to `/project/ue/art-in/` (about
   30 s for 611 MB: start it detached). Several pictures come back the same way as one tar (type `file`): no image
   tokens until a picture is opened.

## 5. GLB import: what turned out to be true

Measured on the first block build (2026-11-22, `build_block.py`, every result line in
`<project>/Saved/BuildBlock/status.txt`):

| Question | Answer |
|---|---|
| Importer | Interchange glTF through `unreal.InterchangeManager.get_interchange_manager_scripted().import_asset(dest, create_source_data(glb), ImportAssetParameters)`; the pipeline is a transient `InterchangeGenericAssetsPipeline` passed as `override_pipelines = [SoftObjectPath(pipeline.get_path_name())]`. Synchronous; returns `(ok, objects)`. |
| Axes | Right as they come. Blender metres (+X east, +Y north, Z up) exported with `export_yup` land as Unreal X east, Y south, Z up, unmirrored: glTF (x, y, z) becomes Unreal (x, z, y) x 100 (`GLTFCore/Private/GLTF/ConversionUtilities.h`), which is Blender (x, -y, z) x 100. No import rotation, no negative scale. |
| Scale | Metres to centimetres by the importer. All 16 meshes match the manifest's `bounds_unreal_cm` to 0.0 cm (e.g. `SM_Street_Kerb_4m` X 0..400, Y -19..0, Z -3.5..15; `SM_El_Deck_10m` X 0..1000, Z 650..778.6). Pivots arrive as authored. |
| Slot names | Kept exactly: the static material slots are named after the Blender materials (`MI_Steel_ScanPaintGreen`, `M_Prop_Hydrant`), so instances are assigned by name. With `material_pipeline.import_materials = False` and `texture_pipeline.import_textures = False` no stray material or texture assets are made. |
| Combine | `mesh_pipeline.combine_static_meshes_behavior = InterchangeCombineStaticMeshesBehavior.ALL` (the old `combine_static_meshes` is deprecated in 5.9 and raises in Python). One GLB gives one `StaticMesh` named after the file (`asset_name`). |
| Nanite | `mesh_pipeline.build_nanite = True`; the 234k-triangle road builds in 19 s. |
| Normal maps | The sets are OpenGL (+Y up). Imported as plain textures (`AssetImportTask`), then `srgb = False`, `compression_settings = TC_NORMALMAP`, `flip_green_channel = True`, `lod_group = TEXTUREGROUP_WORLD_NORMAL_MAP`. ORM: `srgb = False`, `TC_MASKS` (sampler type Masks in the material). |
| Vertex colours (`Wear`, COLOR_0) | Arrive, but the static mesh build stores them sRGB-encoded (`StaticMeshBuilder.cpp`: `LinearColor.ToFColor(true)`) and the vertex factory reads them back raw: the master material decodes RGB with `pow(x, 2.2)`; alpha is stored linearly. Still to prove with a ramp test asset (art bible 3.3). |
| Material graph from Python | `MaterialExpressionCustom` inputs and outputs are built as structs property by property (`CustomInput()` then `set_editor_property`: the constructor takes no keywords). Vector parameters and the vertex colour node give float3 on their main output: alpha comes from the `"A"` output. Never delete a material that instances use: rebuild its graph in place (`delete_all_material_expressions`). |

## 6. Level assembly: what turned out to be true

| Question | Answer |
|---|---|
| Instanced meshes from Python | `SubobjectDataSubsystem.k2_gather_subobject_data_for_instance(actor)[0]` as parent, `add_new_subobject(AddNewSubobjectParams(new_class=InstancedStaticMeshComponent))`, `SubobjectDataBlueprintFunctionLibrary.get_object(get_data(handle))` gives the component; `add_instances(transforms, False, True)` (world space). Saved with the level like a component added in the details panel. One holder actor per building, props, structures and backdrop. |
| Collision | The art carries none (`NO_COLLISION`); every movement-blocking collider of level.json stays a box: visible in a material by tag where no art draws it, hidden (`set_visibility(False)`, no shadow, no distance field) under the art. |
| Glass | Opaque, Nanite, black base, specular 0.5, roughness 0.02: full Lumen reflections; the room behind is emission (110 nits windows, 200 nits shops), so reflections win at grazing angles as on real glass. |
| Alpha cards | A second master `M_MI_SurfaceMasked` (two-sided, opacity mask = BC alpha); the manifest slot's `alpha` key selects it. On the opaque master the chain-link drew as a grey sheet. |
| Decals | Deferred decal material (`MD_DEFERRED_DECAL`, translucent) with the shapes drawn in decal UV by HLSL; DecalActor `decal_size` is (depth, width, height); pitch -90 projects down. |
| Catalogue ids | One table: `Content/Data/art_catalogue.json` (id -> meshes picked by seed, variant overrides, paint slot, parts; `gameplay` ids are drawn by the gameplay actors). |
| Car paint | `M_MI_CarPaint` is the surface master with `MSM_CLEAR_COAT` (CustomData0 = clear coat 1, CustomData1 = its roughness 0.03); one instance per paint slot and props.json colour, set on the instanced component with `set_material_by_name(slot, ...)`. Vehicle sets carry lamp colours in `E`: `EmissiveScale` 0 by day. |
| Vertex colours | Arrive in the shader linear (ramp test `mi_ramp_test.py`: COLOR_0 k/10 reads back k/10 in 8-bit steps through Interchange). No decode in the material. |
| Interiors by cube map | A `SceneCaptureCube` (`SCS_SCENE_COLOR_HDR`) does see direct lights here (only Lumen and the sky light are missing in captures), so small rooms lit by point lights plus a shadowless fill bake well. `RenderingLibrary.render_target_create_static_texture_cube_editor_only(rt, "/Game/...full path", TC_HDR, ...)` makes the asset; a re-bake writes into the existing one with `convert_render_target_to_texture_cube_editor_only`. `capture_scene()` renders on a later tick: capture and save in different build units. |
| LoadLevel in 5.9 | `LevelEditorSubsystem.load_level` refuses while the open map is dirty (picture cameras, play in editor): `load_level(path, unreal.LevelEditorUnsavedChangesPolicy.DISCARD)` (`build_block.load_level`). |
| Gameplay actors and the art | The explosives, reel cases and the IPX truck are spawned at play by the game; their meshes come from `presentation.json` (`explosives.<kind>.mesh`, `objectives.case.art`, `objectives.truck.art`). `build_block.py` places hidden-in-game previews of them so editor pictures show them. |
| Scene capture readback | `RenderingLibrary.read_render_target_raw(world, rt, False)` gives the whole float target as a list (row-major); a capture looking +Y has Unreal +X running to the left of the image. |


## 7. Gameplay clone and C++: what turned out to be true

| Fact | Consequence |
|---|---|
| Two clones share the box: `/project/ue/repo` (level, logs in `/project/ue/logs`, MCP 8000) and `/project/ue/repo-gameplay` (logs in `/project/ue/logs/repo-gameplay`, MCP 8001) | Every script takes the clone from its own location (`lib.sh`) and stops only processes whose command line names its own project. Run `seed-content.sh` once per clone (208 template assets). |
| The first build of a clone on a fresh box takes about 12 minutes (makefile, UHT 88 s, the module); later C++ changes 60 to 270 s | Any change to `Config/DefaultEngine.ini` invalidates the makefile and adds about a minute. |
| 5.9: `FJsonObject::Values` keys are `UE::TSharedString`, not `FString` | Iterate with `const auto& Pair`, convert with `FString(*Pair.Key)`. |
| `FMath::CeilToInt(double)` returns `int64`: `Printf("%d")` fails at compile time (consteval format check) | Use `CeilToInt32`. `FOverlapResult` needs `Engine/OverlapResult.h`. |
| The engine's JSON reader can return 1/60 one unit in the last place off JavaScript's `1 / 60`; nine steps then cross a 0.15 s hold a frame early | The golden tests take a step within 1e-12 of 1/n as exactly `1.0 / n` (`StepOf`). |
| A character's movement component already ticks before its actor: making it wait for the actor's tick is a cycle (`LogTick` warning every frame, the prerequisite is dropped) | `AMIPlayerCharacter` runs its frame in two own tick functions: pre-physics (a prerequisite of the movement component) and post-physics (after it). |
| A bare `UWorld::CreateWorld(Game)` has no game mode: `BeginPlay` does not reach the actors | Tests call `GetWorldSettings()->NotifyBeginPlay()` and `World->EndPlay` before destroying it (`Tests/MIWorldTests.cpp`). |
| Play in editor works headless on the level viewport; `HighResShot` from the PIE world writes `Saved/Screenshots/LinuxEditor/*.png` after a few `CaptureEditorViewport` redraws. A second shot in the same session once captured the editor camera instead | `tools/box/pie.sh` (`pie_start`, `pie_con`, `pie_shot`, `pie_state`); input by console: `MIInput <action> <value>`. Python sent through MCP runs inside the editor: it does not see the client's environment, and sleeping in it stops the game. |
| `unreal.Rotator(a, b, c)` in Python is (roll, pitch, yaw) | Name the fields. |
| In a hand-made test world (`UWorld::CreateWorld`) actor and custom tick functions run once per engine frame (`GFrameCounter`): an automation test that calls `World->Tick` in a loop ticks only tickable objects after the first step | Advance `GFrameCounter` after each `World->Tick`, as the engine's `FTestWorldWrapper::TickTestWorld` does (`Tests/MIRunTests.cpp`). |
| A static-mobility mesh component refuses `SetStaticMesh` once the world has begun play (the grey block is built then): nothing is drawn, no error | Components built at run time are movable (`AMIBlockGeometry`). |
| Play in editor right after `editor.sh start` can be ignored while the editor still loads; a picture then shows the editor camera | Check `PIE: Play in editor total start time` in `editor.log` before `pie_con` / `pie_shot`. |
| The art map can be played in the gameplay clone | Copy `/project/ue/repo/unreal/MurderInc/Content/Art` and `Maps/L_Block.umap` (561 MB, about a minute) into `/project/ue/repo-gameplay/unreal/MurderInc/Content/` (generated content, never committed); `load_level('/Game/Maps/L_Block')`, then `pie_start`. `L_GreyBlock` comes from `Content/Python/mi_greyblock_map.py`. |
