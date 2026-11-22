# 00 - Unreal scout: engine facts the port depends on

Written 2026-11-22 for the Unreal rebuild of MURDER INC. Nothing Unreal could be compiled or run while this
was written, so every name below is either copied from a source that was read that day or is marked as memory.
Copy names from the code spans verbatim.

## 0. How to read this file

### 0.1 Evidence tags

| Tag | Meaning |
|---|---|
| `[V src]` | **VERIFIED**: read in the cited source on 2026-11-22. |
| `[M+ src]` | **FROM MEMORY**, and a post on Epic's forum (a user's project file, log or statement, not Epic documentation) shows the same thing. |
| `[M]` | **FROM MEMORY** only. Compile or run it before relying on it. |

### 0.2 Source keys

| Key | URL |
|---|---|
| `PY:Name` | Epic's Python API reference, class page for 5.8: `https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/Name?application_version=5.8` (each cited page was fetched) |
| `PY57:Name`, `PY56:Name`, `PY55:Name` | the same page with `application_version=5.7`, `5.6`, `5.5` |
| `PY:index` | `https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/?application_version=5.8` |
| `PY:module` | `https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/module/unreal?application_version=5.8` |
| `F:id` / `F:id/n` | Epic Developer Community forum topic `https://forums.unrealengine.com/t/id` (post `n`); the short URL redirects to the full one |
| `BL:gltf` | Blender 5.3 manual, glTF 2.0: `https://docs.blender.org/manual/en/latest/addons/scene_gltf2.html` |
| `BL:fbx` | Blender 5.3 manual, FBX: `https://docs.blender.org/manual/en/latest/files/import_export/fbx.html` |
| `BL:run` | measured here with Blender 5.3.0 as a Python module (scripts in Appendix A) |
| `LP:file` | Epic's "Unreal Engine Skills for Claude Code" plugin v3.1.1 installed on this machine (author field: an Epic Games address; MIT). Local files, no URL: `README.md`, `skills/unreal-mcp/references/setup.md`, `.../operations.md`, `skills/create-toolset/SKILL.md` |

### 0.3 What could not be read at all

- **Epic's prose documentation and C++ API reference.** `dev.epicgames.com/documentation/...` pages are a JavaScript
  app whose content comes from `/community/api/documentation/document.json`. That endpoint answers with a bot
  challenge that needs `challenges.cloudflare.com`, which this network does not allow, both from `curl` and from the
  pre-installed Chromium. No release notes, no "project settings" page, no C++ class page was read.
- `www.unrealengine.com` (same challenge), `fab.com`, `github.com/EpicGames/UnrealEngine` (not attached to this
  session), `docs.unrealengine.com`.
- What was readable: the static **Python API reference** (versions 5.4 to 5.8), the **forum** (including posts by
  Epic staff and Epic's release announcements), the **Blender manual**, and Blender itself.

Consequence: class, function, property, enum, module and header **file** names of everything reflected to Python are
verified. Header **folders**, non-reflected C++ (`FFileHelper`, `FJsonSerializer`, `FTimerManager`, Slate, test
macros, `UWorld::LineTrace...`), build command lines and most ini keys are memory, backed where possible by files
that users posted on Epic's forum.

### 0.4 From a Python name to the C++ name

The Python reference lists reflected C++ members in snake_case. The C++ spelling is the PascalCase original:
`max_walk_speed` is `MaxWalkSpeed`; a bool gets the `b` prefix (`use_controller_rotation_yaw` is
`bUseControllerRotationYaw`); `add_movement_input(...)` is `AddMovementInput(...)`, same parameter order; class
`unreal.Character` is `ACharacter` (`A` for actors, `U` for other objects, `F` for structs, `E` for enums). Enum
values keep their C++ spelling in upper case with underscores (`MovementMode.MOVE_WALKING` is
`EMovementMode::MOVE_Walking`). Where a C++ spelling in this file comes only from this rule it is still marked
`[V PY:...]` for the member's existence and order, not for the exact C++ signature.

### 0.5 The short list

The facts most likely to save a failed build or a wrong import. Details and evidence are in the numbered sections.

1. Target **5.8** (5.8.4 or later), `"EngineAssociation": "5.8"`. 5.9 is a Preview. (1.1)
2. MCP server: plugins `ModelContextProtocol` and `AllToolsets`, both referenced with `"Optional": true` and
   `"TargetAllowList": [ "Editor" ]`; endpoint `http://127.0.0.1:8000/mcp`; console `ModelContextProtocol.StartServer`. (1.2, 1.3)
3. Blender `(x, y, z)` metres is expected to arrive as Unreal `(x, -y, z) * 100`. The Blender half is measured, the
   Unreal half is memory: run Appendix A first. (5.1)
4. Meshes: GLB through `unreal.AssetImportTask` with `options = unreal.InterchangePipelineStackOverride()`;
   Nanite with `mesh_pipeline.build_nanite`. (3.2)
5. `AssetImportTask.destination_name` is ignored by Interchange: name each source file after its asset. (3.2)
6. Textures are imported separately and set explicitly; every `T_<Set>_N` gets `flip_green_channel = True`,
   `TC_NORMALMAP`, `srgb = False`; `T_<Set>_ORM` gets `TC_MASKS`, `srgb = False`. (3.4, 5.4)
7. Python traps: `unreal.Rotator(roll, pitch, yaw)`, `unreal.Color(b, g, r, a)`, `unreal.LinearColor` alpha
   defaults to 0. (3.1)
8. Use the subsystems (`LevelEditorSubsystem`, `EditorActorSubsystem`, `StaticMeshEditorSubsystem`);
   `EditorLevelLibrary` and `EditorStaticMeshLibrary` are deprecated. (3.1)
9. Navigation: `RuntimeGeneration=Dynamic` in the ini; a scripted `BuildPaths` right after a level load is silently
   refused in 5.8.3. (3.9)
10. Enhanced Input: fill a context with `MapKey` only; the `Mappings` array is deprecated since 5.7. (4.4)
11. `FPointDamageEvent` needs `#include "Engine/DamageEvents.h"`; deriving from `AAIController` needs the
    `GameplayTasks` module. (4.6, 4.1)
12. `UCameraComponent::FieldOfView` is horizontal; the web game's is vertical. (4.3)
13. Nanite: no translucent materials, masked is allowed, not for skeletal meshes. (5.3)
14. No static lighting (`r.AllowStaticLighting=False`), so no lightmap UVs. (2.2, 5.5)
15. Megascans stopped being free on 2025-01-01, apart from a free selection. (5.6)
16. Headless Python: `-run=pythonscript -script="..."` (no editor ticks) or `-ExecutePythonScript="..."` (full
    editor, exits after the script unless `set_keep_python_script_alive(True)`). (3.10)
17. A reported 5.8.4 problem: the self-updating Fab plugin 0.0.22 stops every C++ project build with a
    `RulesError`. (4.16)
18. Substrate stays off (`r.Substrate=False`); materials use the classic root pins. (2.3)

---

## 1. Engine release, target version, MCP plugins, optional plugin references

### 1.1 Releases

- Unreal Engine **5.8** was released **2026-06-17**. `[V F:2729274]` (Epic's announcement:
  `https://forums.unrealengine.com/t/unreal-engine-5-8-released/2729274`)
- Hotfixes: 5.8.1 on 2026-07-28 `[V F:2738864]`, 5.8.2 on 2026-08-25 `[V F:2746335]`, 5.8.3 on 2026-09-22
  `[V F:2833315]`, **5.8.4 on 2026-10-20** `[V F:2842775]`. No 5.8.5 topic existed on 2026-11-22.
- 5.7 was released 2025-11-12 `[V F:2673913]`, 5.6 on 2025-06-03 `[V F:2538952]`.
- **5.9 exists only as a Preview.** Preview 2 was posted 2026-11-09; Epic writes of "an eventual 5.9 release next
  year". `[V F:2852840]`
- The Python API reference is served for 5.4, 5.5, 5.6, 5.7 and 5.8; the page without a version shows 5.8;
  `application_version=5.9` and `6.0` redirect to a 404 page. `[V PY:EditorAssetLibrary and the same URL with each version]`
- 5.8 highlights that matter here: "MegaLights is now Production-Ready", "Lumen Lite delivers lighting that is up to
  twice as fast as Lumen High Quality", "The new MCP plugin connects LLMs directly to Unreal Engine". `[V F:2729274]`
- 5.7 highlights: "Substrate ... is now production-ready", "MegaLights advances to Beta", Nanite Foliage is
  Experimental. `[V F:2673913]`

**Target: Unreal Engine 5.8, latest hotfix (5.8.4 or later).** `.uproject`: `"EngineAssociation": "5.8"` `[M]`.
Reasons: it is the current production release; it is the first release with the in-editor MCP server; the Python
reference used for every verified name in this file is the 5.8 one. Do not target the 5.9 Preview (Epic: "about a
week of development and a shorter QA pass than usual" `[V F:2852840]`), but nothing below should break on it.

Use at least 5.8.1: its notes list "[ModelContextProtocol][HTTPServer] Fix tools/call response framing". `[V F:2729274]`

### 1.2 The MCP server inside the editor

- It is new in 5.8 and Experimental. `[V F:2729274]`; "Updates to Unreal MCP (Experimental)" in 5.9 Preview `[V F:2852840]`
- `unreal.ToolsetRegistry` exists in the 5.8 Python reference (Plugin `ToolsetRegistry`, Module `ToolsetRegistry`,
  File `UToolsetRegistry.h`) and the same URL for 5.7 redirects to the 404 page. `[V PY:ToolsetRegistry, PY57:ToolsetRegistry]`
- Plugin names to put in the `.uproject`: **`ModelContextProtocol`** (server and transport) and **`AllToolsets`**
  (turns on the toolset plugins; "an editor-only aggregator with `EnabledByDefault` off"). With only
  `ModelContextProtocol` the server starts and offers no tools. `[V LP:setup.md]`
  Epic staff give the same reference for 5.9 Preview:
  `{ "Name": "AllToolsets", "Enabled": true, "TargetAllowList": [ "Editor" ] }`. `[V F:2852840/3]`
  A 5.8.0 user fixed "only AgentSkillToolset is listed" with exactly that entry. `[M+ F:2729455/3]`
- Related plugin names seen: `ToolsetRegistry`, `EditorToolset` (5.8.3 user report `[M+ F:2838948]`);
  `BlueprintToolsets`, `ConsoleToolset`, `LiveCodingToolset` (5.9 Preview `[V F:2852840/3]`).
  "MCP Client Toolset" (`MCPClientToolset`) is Unreal acting as an MCP *client*; it is not needed. `[M+ F:2729488/2]`
- Engine folders: `Engine/Plugins/Experimental/ModelContextProtocol`, `Engine/Plugins/Experimental/ToolsetRegistry`,
  `Engine/Plugins/Experimental/Toolsets/<Name>`. `[V LP:README.md, LP:create-toolset]`; a 5.8 log shows
  `Engine/Plugins/Experimental/Toolsets/MCPClientToolset/` `[M+ F:2729455]`
- Console commands `[V LP:operations.md]`:
  - `ModelContextProtocol.StartServer [port]`
  - `ModelContextProtocol.StopServer`
  - `ModelContextProtocol.RefreshTools`
  - `ModelContextProtocol.GenerateClientConfig <ClaudeCode|Cursor|VSCode|Gemini|Codex|All>`
- Default endpoint **`http://127.0.0.1:8000/mcp`** (port `8000`, path `/mcp`). `[V LP:README.md]`
  Log line in 5.8: `LogModelContextProtocol: Starting MCP server on port 8000 (override with -ModelContextProtocolPort=N).` `[M+ F:2729403]`
- In 5.8 the server is **stopped by default**. Start it with the console command, or per user in
  `<Project>/Saved/Config/<Platform>Editor/EditorPerProjectUserSettings.ini` `[V LP:setup.md]`:

  ```ini
  [/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]
  bAutoStartServer=True
  ServerPortNumber=8000
  ServerUrlPath=/mcp
  bEnableToolSearch=True
  ```

  or on the command line: `-ModelContextProtocolStartServer` and `-ModelContextProtocolPort=<port>`. `[V LP:setup.md]`
  In 5.9 Preview "Unreal MCP launches automatically with the editor". `[V F:2852840]`
- Client file `.mcp.json` (next to the `.uproject` for a launcher build, next to `Engine/` for a source build) `[V LP:setup.md]`:

  ```json
  { "mcpServers": { "unreal-mcp": { "type": "http", "url": "http://127.0.0.1:8000/mcp" } } }
  ```

- With tool search on (default) `tools/list` returns only `list_toolsets`, `describe_toolset`, `call_tool`. `[V LP:operations.md]`
- Toolsets present as classes in the 5.8 Python reference (base `ToolsetDefinition`): `ActorTools`,
  `BlueprintTools`, `StaticMeshTools`, `SkeletalMeshTools`, `MaterialTools`, `MaterialInstanceTools`, `TextureTools`,
  `SceneTools`, `ObjectTools`, `PrimitiveTools`, `DataTableTools`, `ProgrammaticToolset`, `AgentSkillToolset`. All
  but `AgentSkillToolset` (File `AgentSkill.h`) list no C++ source, so they are written in Python.
  `[V PY:ActorTools ... PY:AgentSkillToolset]` Listed in the index and not
  opened: `BehaviorTreeTools`, `ControlRigTools`, `CurveTableTools`, `DataAssetTools`, `SequencerTools` (and six more
  `Sequencer...Tools`), `StateTreeTools`, `StringTableTools`. `[V PY:index]`
- `ProgrammaticToolset.execute_tool_script` runs Python inside the editor process. `[V LP:README.md]`
- A toolset in C++: derive from `UToolsetDefinition` (`ToolsetRegistry/ToolsetDefinition.h`), static functions marked
  `UFUNCTION(meta = (AICallable))`, register with `UToolsetRegistry::RegisterToolsetClass(UMyToolset::StaticClass())`. `[V LP:create-toolset]`

### 1.3 Marking a plugin reference optional in a `.uproject`

- Add **`"Optional": true`** to the entry in the `"Plugins"` array. An enabled optional plugin that the engine does
  not have is skipped without the "plugin could not be found" prompt. `[M+ F:131525/9]` (a user's
  `{ "Name": "ExternalPlugin", "Enabled": false, "Optional": true }`); the engine logs
  `LogPluginManager: Display: Ignored optional reference to 'ConcertSyncClient' plugin from 'LiveLink' plugin`. `[M+ F:1836345/10]`
  Not read in Epic documentation.
- Other keys of a plugin reference: `"Name"`, `"Enabled"`, `"TargetAllowList"` `[V F:2852840/3]`, `"PlatformDenyList"`
  (named by Epic staff in the same post), `"PlatformAllowList"`, `"TargetDenyList"`, `"Description"`, `"MarketplaceURL"` `[M]`.

Recommended `unreal/MurderInc/MurderInc.uproject` `[M]` except the two tagged entries:

```json
{
  "FileVersion": 3,
  "EngineAssociation": "5.8",
  "Category": "",
  "Description": "",
  "Modules": [
    { "Name": "MurderInc", "Type": "Runtime", "LoadingPhase": "Default" }
  ],
  "Plugins": [
    { "Name": "ModelContextProtocol", "Enabled": true, "Optional": true, "TargetAllowList": [ "Editor" ] },
    { "Name": "AllToolsets", "Enabled": true, "Optional": true, "TargetAllowList": [ "Editor" ] },
    { "Name": "PythonScriptPlugin", "Enabled": true },
    { "Name": "EditorScriptingUtilities", "Enabled": true }
  ]
}
```

`PythonScriptPlugin` and `EditorScriptingUtilities` are the verified plugin names of the scripting classes used in
section 3 `[V PY:EditorPythonScripting, PY:EditorAssetLibrary]`; they are believed to be on by default `[M]`.
`EnhancedInput`, `Niagara` and `Interchange` are plugin names too `[V PY:InputAction, PY:NiagaraComponent, PY:InterchangeGenericAssetsPipeline]` and are believed on by default `[M]`.

---

## 2. Project settings for a current-generation look

### 2.1 Where the keys come from

`URendererSettings` is not exposed to Python, so its ini keys are not in the reference. What is verified:

- The enums say which cvar they mirror: `DynamicGlobalIlluminationMethod` "Must match
  r.DynamicGlobalIlluminationMethod, this is used in URendererSettings" with `NONE` 0, `LUMEN` 1, `SCREEN_SPACE` 2,
  `PLUGIN` 3; `ReflectionMethod` "Must match r.ReflectionMethod" with `NONE` 0, `LUMEN` 1, `SCREEN_SPACE` 2.
  `[V PY:DynamicGlobalIlluminationMethod, PY:ReflectionMethod]`
- Lumen needs: "Requires 'Generate Mesh Distance Fields' enabled for Software Ray Tracing and 'Support Hardware Ray
  Tracing' enabled for Hardware Ray Tracing." `[V PY:DynamicGlobalIlluminationMethod]`
- `AntiAliasingMethod`: `AAM_NONE` 0, `AAM_FXAA` 1, `AAM_TEMPORAL_AA` 2, `AAM_MSAA` 3 ("Only supported with forward
  shading. MSAA sample count is controlled by r.MSAACount."), `AAM_TSR` 4, `AAM_SMAA` 5. `[V PY57:AntiAliasingMethod]`
  Epic's TSR author uses `r.AntiAliasingMethod=4` for TSR. `[V F:883977]`
- `AutoExposureMethod`: `AEM_HISTOGRAM` 0, `AEM_BASIC` 1, `AEM_MANUAL` 2. `[V PY:AutoExposureMethod]`
- The section name pattern `[/Script/<Module>.<Class>]` with the C++ property name as key is shown in Epic's own
  text ("[/Script/Engine.Actor] DefaultUpdateOverlapsMethodDuringLevelStreaming = OnlyUpdateMovable"). `[V PY:Character]`

Every other renderer key below was **seen verbatim in a project's `DefaultEngine.ini` that a user posted**: a 5.7
project in an Epic support thread (`F:2687111/5`), a 2026 project (`F:2742734`), a 2025 project in an Epic support
thread (`F:2664001/2`). They are tagged `[M+]`.

### 2.2 `Config/DefaultEngine.ini`

```ini
[/Script/EngineSettings.GameMapsSettings]
GameDefaultMap=/Game/Maps/L_Block.L_Block
EditorStartupMap=/Game/Maps/L_Block.L_Block
GlobalDefaultGameMode=/Script/MurderInc.MIGameMode
GameInstanceClass=/Script/MurderInc.MIGameInstance

[/Script/Engine.RendererSettings]
r.DynamicGlobalIlluminationMethod=1
r.ReflectionMethod=1
r.GenerateMeshDistanceFields=True
r.Shadow.Virtual.Enable=1
r.Nanite.ProjectEnabled=True
r.AntiAliasingMethod=4
r.AllowStaticLighting=False
r.RayTracing=True
r.SkinCache.CompileShaders=True
r.Lumen.HardwareRayTracing=True
r.Lumen.HardwareRayTracing.LightingMode=0
r.RayTracing.Shadows=False
r.VirtualTextures=True
r.VT.EnableAutoImport=False
r.Substrate=False
r.SupportSkyAtmosphere=True
r.SupportSkyAtmosphereAffectsHeightFog=True
r.DefaultFeature.AutoExposure=True
r.DefaultFeature.AutoExposure.Method=0
r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange=True
r.DefaultFeature.Bloom=True
r.DefaultFeature.MotionBlur=False
r.DefaultFeature.LensFlare=False

[/Script/WindowsTargetPlatform.WindowsTargetSettings]
DefaultGraphicsRHI=DefaultGraphicsRHI_DX12
-D3D12TargetedShaderFormats=PCD3D_SM5
+D3D12TargetedShaderFormats=PCD3D_SM6

[/Script/LinuxTargetPlatform.LinuxTargetSettings]
-TargetedRHIs=SF_VULKAN_SM5
+TargetedRHIs=SF_VULKAN_SM6

[/Script/HardwareTargeting.HardwareTargetingSettings]
TargetedHardwareClass=Desktop
AppliedTargetedHardwareClass=Desktop
DefaultGraphicsPerformance=Maximum
AppliedDefaultGraphicsPerformance=Maximum

[/Script/NavigationSystem.RecastNavMesh]
RuntimeGeneration=Dynamic

[/Script/NavigationSystem.NavigationSystemV1]
bWaitForAsyncLoadingBeforeBuildingNavigationAutomatically=False
```

| Key | Value | What it is | Evidence |
|---|---|---|---|
| `GameDefaultMap`, `EditorStartupMap`, `GlobalDefaultGameMode`, `GameInstanceClass` | object path | class `GameMapsSettings`, module `EngineSettings`; properties `game_default_map`, `editor_startup_map`, `global_default_game_mode`, `game_instance_class` | names `[V PY:GameMapsSettings]`; value format `/Game/Folder/Asset.Asset` `[M+ F:1190042/130]`; `/Script/<Module>.<ClassWithoutPrefix>` for a C++ class `[M]` |
| `r.DynamicGlobalIlluminationMethod` | `1` | Lumen global illumination | values `[V PY:DynamicGlobalIlluminationMethod]`, key in files `[M+ F:2687111/5]` |
| `r.ReflectionMethod` | `1` | Lumen reflections | values `[V PY:ReflectionMethod]`, key `[M+ F:2687111/5]` |
| `r.GenerateMeshDistanceFields` | `True` | mesh distance fields, needed by Lumen software ray tracing | need `[V PY:DynamicGlobalIlluminationMethod]`, key `[M+ F:2687111/5]` |
| `r.Shadow.Virtual.Enable` | `1` | virtual shadow maps | `[M+ F:2687111/5]` |
| `r.Nanite.ProjectEnabled` | `True` | Nanite for the project | `[M+ F:2687111/5]` |
| `r.AntiAliasingMethod` | `4` | TSR | values `[V PY57:AntiAliasingMethod]`, `[V F:883977]`; key in files `[M+ F:2687111/5]` |
| `r.AllowStaticLighting` | `False` | no lightmaps, fewer shader permutations | `[M+ F:2687111/5]` |
| `r.RayTracing` | `True` | "Support Hardware Ray Tracing" | `[M+ F:2687111/5]` |
| `r.SkinCache.CompileShaders` | `True` | compute skin cache, written next to `r.RayTracing` in every file seen | `[M+ F:2687111/5, F:2742734]` |
| `r.Lumen.HardwareRayTracing` | `True` | Lumen uses hardware ray tracing when the GPU has it | `[M+ F:2687111/5]` |
| `r.Lumen.HardwareRayTracing.LightingMode` | `0` | 0 surface cache, higher values hit lighting | key `[M+ F:2742734, F:2664001/2]`; meaning `[M]` |
| `r.RayTracing.Shadows` | `False` | keep virtual shadow maps for shadows | `[M+ F:2687111/5]` |
| `r.VirtualTextures`, `r.VT.EnableAutoImport` | `True`, `False` | virtual texture support on, no automatic conversion of imported textures | `[M+ F:2687111/5, F:2673913/149]` |
| `r.Substrate` | `False` | Substrate materials off, see 2.3 | key `[M+ F:2742734, F:2664001/2]` |
| `r.SupportSkyAtmosphere`, `r.SupportSkyAtmosphereAffectsHeightFog` | `True` | sky atmosphere, and its light in height fog | keys `[M+ F:2687111/5]`; "when SupportSkyAtmosphereAffectsHeightFog project setting is true" `[V PY:SkyAtmosphereComponent]` |
| `r.DefaultFeature.AutoExposure` | `True` | auto exposure on by default | `[M+ F:2687111/5]` |
| `r.DefaultFeature.AutoExposure.Method` | `0` | histogram | values `[V PY:AutoExposureMethod]`, key `[M+ F:2687111/5]` |
| `r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange` | `True` | exposure limits in EV100 | key `[M+ F:2687111/5, F:2742734]`; meaning `[M]` |
| `r.DefaultFeature.Bloom`, `r.DefaultFeature.MotionBlur`, `r.DefaultFeature.LensFlare` | | post-process defaults | `[M+ F:2687111/5]` |
| `DefaultGraphicsRHI=DefaultGraphicsRHI_DX12`, `+D3D12TargetedShaderFormats=PCD3D_SM6` | | Direct3D 12 with Shader Model 6 on Windows | `[M+ F:2742734]` |
| `+TargetedRHIs=SF_VULKAN_SM6` | | Vulkan SM6 on Linux | `[M+ F:2742734]` |
| `HardwareTargetingSettings` block | | "Desktop / Maximum" preset | `[M]` (a posted file writes `TargetedHardwareClass=EHardwareClass::Desktop` `[M+ F:2742734]`; check what 5.8 writes) |
| `RuntimeGeneration=Dynamic` | | navmesh is generated at run time, so a level works without an editor nav build | class, module, property and value `[V PY:RecastNavMesh, PY:RuntimeGenerationType]` (`DYNAMIC` 2, `DYNAMIC_MODIFIERS_ONLY` 1, `STATIC` 0); ini form `[M]` |
| `bWaitForAsyncLoadingBeforeBuildingNavigationAutomatically=False` | | see 3.9 | property `[V PY:NavigationSystemV1]`; effect `[M+ F:2849553]` |

Other keys seen in those files, for later use `[M+ F:2687111/5, F:2742734, F:2664001/2]`:
`r.MegaLights.EnableForProject=True`, `r.Lumen.TraceMeshSDFs=0`, `r.Lumen.TranslucencyReflections.FrontLayer.EnableForProject=False`,
`r.RayTracing.RayTracingProxies.ProjectEnabled=True`, `r.Substrate.ProjectGBufferFormat=0`, `r.CustomDepth=3`,
`r.DefaultFeature.LightUnits=2`, `r.DefaultFeature.LocalExposure.HighlightContrastScale=0.8`,
`r.DefaultFeature.LocalExposure.ShadowContrastScale=0.8`, `r.FirstPerson.SelfShadow=1`,
`r.Nanite.AllowTessellation=1`, `r.TemporalAA.Upsampling=True`, `r.MSAACount=2`,
`[/Script/AIModule.AISystem] bForgetStaleActors=True`; and `r.DefaultFeature.AutoExposure.Bias=1.000000` `[M+ F:2693657]`.

### 2.3 Substrate, Lumen, ray tracing: state and choice

- **Substrate** is production-ready since 5.7. `[V F:2673913]` Whether a new 5.8 project has it on by default was not
  verified. Choice for this project: **`r.Substrate=False`**. Materials built by script through the classic root
  pins (`MP_BASE_COLOR`, `MP_ROUGHNESS`, ...) work with it on or off, nothing in this game needs layered slabs, and
  changing the line later costs one full shader compile. `MP_FRONT_MATERIAL` is the Substrate root pin. `[V PY:MaterialProperty]`
- **Lumen** GI and reflections: the two method keys above. Per level they can be overridden in a post-process volume:
  `dynamic_global_illumination_method`, `reflection_method`, `lumen_scene_lighting_quality`, `lumen_scene_detail`,
  `lumen_final_gather_quality`, `lumen_reflection_quality`, `lumen_max_trace_distance`, `lumen_ray_lighting_mode`
  (`LumenRayLightingModeOverride`: `DEFAULT` 0, `SURFACE_CACHE` 1, `HIT_LIGHTING_FOR_REFLECTIONS` 2, `HIT_LIGHTING` 3). `[V PY:PostProcessSettings, PY:LumenRayLightingModeOverride]`
- **Hardware ray tracing** on Linux/Vulkan may be refused by the engine ("Ray tracing is disabled. Reason: disabled
  on current platform" on 5.4 `[M+ F:2844467/2]`). Lumen then runs on software ray tracing, which is why
  `r.GenerateMeshDistanceFields=True` stays on.
- **MegaLights** (many shadowed lights; relevant to the night look) is production-ready in 5.8 `[V F:2729274]`; key
  `r.MegaLights.EnableForProject=True` `[M+ F:2664001/2]`. Its hardware requirements were not verified.
- **Lumen Lite** is new in 5.8 for low-end targets `[V F:2729274]`; its setting name was not found.

### 2.4 Sky, clouds, fog, exposure: actor classes and properties

Spawn these classes in the level (section 3.7) and set properties on their components. All names `[V PY:<class>]`.

| Actor class (`unreal.`) | Component property on the actor | Component properties that matter |
|---|---|---|
| `DirectionalLight` | `light_component` | `intensity`, `light_color`, `use_temperature`, `temperature`, `light_source_angle`, `atmosphere_sun_light`, `atmosphere_sun_light_index`, `cast_shadows`, `cast_cloud_shadows`, `cast_shadows_on_clouds`, `cast_shadows_on_atmosphere`, `indirect_lighting_intensity`, `volumetric_scattering_intensity`, `mobility` |
| `SkyLight` | `light_component` | `real_time_capture`, `source_type`, `intensity`, `light_color`, `lower_hemisphere_is_black`, `lower_hemisphere_color`, `cubemap`; functions `recapture_sky()`, `set_real_time_capture(bool)`, `set_intensity(float)` |
| `SkyAtmosphere` | `sky_atmosphere_component` | `rayleigh_scattering_scale`, `mie_scattering_scale`, `mie_anisotropy`, `multi_scattering_factor`, `aerial_pespective_view_distance_scale` (sic), `height_fog_contribution`, `sky_luminance_factor`, `ground_albedo`, `bottom_radius`, `atmosphere_height` |
| `VolumetricCloud` | `volumetric_cloud_component` | `layer_bottom_altitude`, `layer_height` (kilometres), `tracing_max_distance`, `material` ("must be a Volume domain material"), `view_sample_count_scale`, `sky_light_cloud_bottom_occlusion` |
| `ExponentialHeightFog` | `component` | `fog_density`, `fog_height_falloff`, `fog_inscattering_luminance`, `fog_max_opacity`, `start_distance`, `enable_volumetric_fog` ("Whether to enable Volumetric fog. Scalability settings control the resolution of the fog simulation."), `volumetric_fog_scattering_distribution`, `volumetric_fog_albedo`, `volumetric_fog_extinction_scale`, `volumetric_fog_distance`; functions `set_fog_density`, `set_volumetric_fog(bool)` |
| `PostProcessVolume` | (on the actor) `unbound`, `settings`, `priority`, `blend_weight`, `enabled` | `settings` is a `PostProcessSettings` |

Exposure and grade fields of `PostProcessSettings` `[V PY:PostProcessSettings]`: `auto_exposure_method`,
`auto_exposure_bias`, `auto_exposure_min_brightness`, `auto_exposure_max_brightness`, `auto_exposure_speed_up`,
`auto_exposure_speed_down`, `local_exposure_highlight_contrast_scale`, `local_exposure_shadow_contrast_scale`,
`bloom_intensity`, `vignette_intensity`, `film_grain_intensity`, `scene_fringe_intensity`, `motion_blur_amount`,
`color_saturation`, `color_contrast`, `white_temp`, `film_slope`, `film_toe`, `film_shoulder`, `sharpen`. Each has an
`override_...` bool (seen: `override_auto_exposure_bias`, `override_dynamic_global_illumination_method`,
`override_reflection_method`); in C++ these are `bOverride_<Name>` `[M]`.

The stock "Basic" level template is `/Engine/Maps/Templates/Template_Default` and contains an actor labelled
`Floor`. `[M+ F:2849553]`

---

## 3. Scripted content creation with the editor Python API (module `unreal`)

### 3.1 Module functions and constructor traps

- Module functions `[V PY:module]`: `unreal.load_asset(name)`, `unreal.load_object(outer, name)`,
  `unreal.load_class(outer, name)`, `unreal.find_asset(name)`, `unreal.new_object(type, outer=None, name='')`,
  `unreal.get_editor_subsystem(cls)`, `unreal.get_engine_subsystem(cls)`, `unreal.get_default_object(type)`,
  `unreal.log(arg)`, `unreal.log_warning(arg)`, `unreal.log_error(arg)`, `unreal.log_flush()`, `unreal.is_editor()`,
  `unreal.register_slate_post_tick_callback(callable)`, `unreal.unregister_slate_post_tick_callback(handle)`,
  `unreal.register_ticker_callback(callable, delay=0.0)`, `unreal.get_interpreter_executable_path()`.
- Every reflected object has `get_editor_property(name)` / `set_editor_property(name, value)`. `[V PY:Character]`
- **`unreal.Rotator(roll, pitch, yaw)`**: positional order is roll, pitch, yaw. Always write
  `unreal.Rotator(roll=0.0, pitch=0.0, yaw=90.0)`. `[V PY:Rotator]`
- `unreal.Vector(x, y, z)`; `unreal.Transform(location, rotation, scale)`; `unreal.Vector2D(x, y)`. `[V PY:Vector, PY:Transform, PY:Vector2D]`
- **`unreal.Color(b, g, r, a)`** (blue first) and `unreal.LinearColor(r, g, b, a)` whose alpha defaults to `0.0`. `[V PY:Color, PY:LinearColor]`
- `unreal.Name('x')`, `unreal.Text('x')`, `unreal.SoftObjectPath('/Game/A.A')`. `[V PY:Name, PY:Text, PY:SoftObjectPath]`
- `unreal.EditorLevelLibrary` and `unreal.EditorStaticMeshLibrary` are deprecated ("The Editor Scripting Utilities
  Plugin is deprecated - Use the function in ... Subsystem"); `unreal.EditorAssetLibrary` carries no such note. `[V PY:EditorLevelLibrary, PY:EditorStaticMeshLibrary, PY:EditorAssetLibrary]`

### 3.2 Importing meshes: `AssetImportTask` and Interchange

Classes `[V PY:AssetImportTask, PY:AssetToolsHelpers, PY:AssetTools]`:

- `unreal.AssetImportTask` properties: `filename`, `destination_path`, `destination_name`, `automated` ("Avoid
  dialogs"), `replace_existing`, `replace_existing_settings`, `save`, `options`, `factory`, `async_`,
  `imported_object_paths`; functions `get_objects()`, `is_async_import_complete()`. `result` is deprecated.
- **`destination_name` is ignored when Interchange does the import** ("if you are using interchange the name must be
  set in a pipeline and this field will be ignored"). Name the source file after the asset. `[V PY:AssetImportTask]`
- `unreal.AssetToolsHelpers.get_asset_tools()` returns `unreal.AssetTools`; `import_asset_tasks(import_tasks)`,
  `import_assets_automated(import_data)`, `create_asset(asset_name, package_path, asset_class, factory, calling_context='None', overwrite_existing=False)`,
  `duplicate_asset(asset_name, package_path, original_object)`.
- Passing Interchange settings to a task: `task.options = unreal.InterchangePipelineStackOverride()` and
  `options.add_pipeline(pipeline)`. "This class is used to pass override pipelines in the ImportAssetTask Options
  member." It has `override_pipelines`, `add_pipeline(pipeline_base)`, `add_python_pipeline(...)`,
  `add_blueprint_pipeline(...)`. `[V PY:InterchangePipelineStackOverride]`
- An import task for a format that Interchange supports uses the default Interchange pipeline stack. `[V F:724404/4]` (Epic staff)

Interchange directly `[V PY:InterchangeManager, PY:ImportAssetParameters, PY:InterchangeSourceData]`:

- `unreal.InterchangeManager.get_interchange_manager_scripted()`
- `unreal.InterchangeManager.create_source_data(file_name)` returns `InterchangeSourceData`
- `manager.import_asset(content_path, source_data, import_asset_parameters)` returns `Array[Object] or None`; the 5.8
  text says "Call this to start a synchronous asset import process." (In 5.1 it returned early and broke commandlets;
  Epic called that a bug. `[V F:724404/2]`)
- `manager.import_scene(content_path, source_data, import_asset_parameters)` returns `bool`
- async variants: `scripted_import_asset_async`, `scripted_import_scene_async`; `wait_until_all_tasks_done(cancel)`;
  `is_interchange_active()`; `reimport_asset(object_to_reimport, import_asset_parameters)`
- `unreal.ImportAssetParameters` fields: `is_automated`, `replace_existing`, `destination_name`,
  `override_pipelines` (`Array[SoftObjectPath]`, so asset paths of pipeline assets), `reimport_asset`,
  `reimport_source_index`, `follow_redirectors`, `force_show_dialog`, `import_level`, `on_assets_import_done`, ...
- Module names: `InterchangeEngine` (manager, parameters, project settings), `InterchangeCore` (source data,
  translator base), `InterchangePipelines` (generic pipelines), `InterchangeImport` (glTF and FBX translators),
  `InterchangeEditor` (`InterchangeEditorScriptLibrary`).

`unreal.InterchangeGenericAssetsPipeline` (Plugin `Interchange`, Module `InterchangePipelines`) `[V PY:InterchangeGenericAssetsPipeline]`:
`asset_name`, `use_source_name_for_asset`, `asset_type_sub_folders`, `scene_name_sub_folder`,
`import_offset_translation`, `import_offset_rotation`, `import_offset_uniform_scale`, `reimport_strategy`, and the
read-only sub-objects `mesh_pipeline`, `common_meshes_properties`, `material_pipeline`, `animation_pipeline`,
`common_skeletal_meshes_and_animations_properties`. Change settings on the sub-objects, do not replace them.

`mesh_pipeline` is an `InterchangeGenericMeshPipeline` `[V PY:InterchangeGenericMeshPipeline]`:

| Property | Text from the reference |
|---|---|
| `import_static_meshes`, `import_skeletal_meshes` | import switches |
| **`build_nanite`** | "If enabled, imported meshes will be rendered by Nanite at runtime. Make sure your meshes and materials meet the requirements for Nanite." |
| `nanite_triangle_threshold` | "Minimum triangle count a mesh needs to have in order to get Nanite enabled for it when BuildNanite is enabled." 0 means always |
| `combine_static_meshes_behavior` | `InterchangeCombineStaticMeshesBehavior`: `ALL` 0, `VISIBLE_ONLY` 1, `DO_NOT_COMBINE` 2. `combine_static_meshes` is deprecated |
| `collision` | "If enabled, custom collision will be imported. If enabled and there is no custom collision, a generic collision will be automatically generated. If disabled, no collision will be created or imported." `import_collision` is deprecated |
| `fallback_collision_type` | `InterchangeMeshCollision`: `BOX` 0, `SPHERE` 1, `CAPSULE` 2, `CONVEX10DOP_X` 3, `CONVEX10DOP_Y` 4, `CONVEX10DOP_Z` 5, `CONVEX18DOP` 6, `CONVEX26DOP` 7, `NONE` 255 |
| `import_collision_according_to_mesh_name` | prefixes `UBX_` box, `UCP_` capsule, `USP_` sphere, `UCX_` convex, on a mesh named like the render mesh |
| `one_convex_hull_per_ucx` | one hull per `UCX_` mesh |
| `generate_lightmap_u_vs`, `src_lightmap_index`, `dst_lightmap_index`, `min_lightmap_resolution` | lightmap UV generation |
| `max_lumen_mesh_cards` | "The default is 12." 0 disables card generation |
| `build_scale3d`, `lod_group`, `auto_compute_lod_screen_sizes`, `build_reversed_index_buffer` | build options |

`common_meshes_properties` is an `InterchangeGenericCommonMeshesProperties` (file
`InterchangeGenericAssetsPipelineSharedSettings.h`) `[V PY:InterchangeGenericCommonMeshesProperties]`:
`force_all_mesh_as_type` (`InterchangeForceMeshType`: `IFMT_NONE` 0, `IFMT_STATIC_MESH` 1, `IFMT_SKELETAL_MESH` 2),
`bake_meshes` ("meshes are baked with the scene instance hierarchy transform"), `bake_pivot_meshes`,
`recompute_normals`, `recompute_tangents`, `use_mikk_t_space` ("tangents are recomputed using MikkTSpace"),
`compute_weighted_normals`, `use_high_precision_tangent_basis`, `use_full_precision_u_vs`, `import_lods`,
`import_sockets` (static mesh sockets are nodes named `SOCKET_MeshName_xx`), `keep_sections_separate`,
`remove_degenerates`, `vertex_color_import_option` (`IVCIO_REPLACE` 0, `IVCIO_IGNORE` 1, `IVCIO_OVERRIDE` 2).

`material_pipeline` is an `InterchangeGenericMaterialPipeline` `[V PY:InterchangeGenericMaterialPipeline]`:
`import_materials`, `material_import` (`IMPORT_AS_MATERIALS` 0, `IMPORT_AS_MATERIAL_INSTANCES` 1), `parent_material`,
`create_new_materials`, `reuse_existing_materials`, `search_location`, and the read-only `texture_pipeline`.

`texture_pipeline` is an `InterchangeGenericTexturePipeline` `[V PY:InterchangeGenericTexturePipeline]`:
`import_textures`, `detect_normal_map_texture` ("tests each newly imported texture to see if it is a normal map. If
it is, the SRGB, Compression Settings, and LOD Group properties of that texture will be adjusted."),
**`flip_normal_map_green_channel`** ("the texture's green channel will be inverted for normal maps. This setting is
only used if the Detect Normal Map Texture setting is also enabled or if the texture has been imported as a Normal
map."), `allow_non_power_of_two`, `import_udi_ms`, `prefer_compressed_source_data`.

glTF and FBX specifics:

- `unreal.InterchangeGLTFTranslator` (Module `InterchangeImport`, File `InterchangeGltfTranslator.h`): "glTF
  translator class support import of texture, material, static mesh, skeletal mesh". `unreal.InterchangeGLTFPipeline`
  (File `InterchangeglTFPipeline.h`) exposes no option besides its display name. `[V PY:InterchangeGLTFTranslator, PY:InterchangeGLTFPipeline]`
- `unreal.InterchangeFbxTranslatorSettings`: `convert_scene` ("convert FBX scene axis system to Unreal axis system"),
  `force_front_x_axis` ("force the front axis to be align with X instead of -Y default"), `convert_scene_unit`
  ("convert the scene from FBX unit to UE unit (centimeter)"), `keep_fbx_namespace`, `use_ufbx_parser`,
  `coordinate_system_policy`. `[V PY:InterchangeFbxTranslatorSettings]`
- Old FBX path, still in the 5.8 reference: `unreal.FbxFactory`, `unreal.FbxImportUI` (`import_mesh`,
  `import_as_skeletal`, `import_materials`, `import_textures`, `import_animations`, `mesh_type_to_import` with
  `FBXImportType.FBXIT_STATIC_MESH` 0 / `FBXIT_SKELETAL_MESH` 1 / `FBXIT_ANIMATION` 2, `static_mesh_import_data`,
  `skeletal_mesh_import_data`, `texture_import_data`, `skeleton`, `create_physics_asset`),
  `unreal.FbxStaticMeshImportData` (**`build_nanite`**, `combine_meshes`, `auto_generate_collision`,
  `generate_lightmap_u_vs`, `one_convex_hull_per_ucx`, `normal_import_method` with
  `FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS` 0 / `FBXNIM_IMPORT_NORMALS` 1 / `FBXNIM_IMPORT_NORMALS_AND_TANGENTS` 2,
  `convert_scene`, `force_front_x_axis`, `convert_scene_unit`, `import_uniform_scale`, `import_rotation`,
  `import_translation`, `bake_pivot_in_vertex`, `transform_vertex_to_absolute`),
  `unreal.FbxTextureImportData` (**`invert_normal_maps`**: "this option will cause normal map Y (Green) values to be
  inverted"). `[V PY:FbxImportUI, PY:FbxStaticMeshImportData, PY:FbxTextureImportData, PY:FBXImportType, PY:FBXNormalImportMethod]`
  Whether a 5.8 import task with `options = FbxImportUI` still takes this path, or Interchange takes the file first,
  was not verified.

Import recipe that uses only verified names:

```python
import unreal

def import_static_mesh(glb_path: str, dest: str, nanite: bool) -> list:
    pipe = unreal.InterchangeGenericAssetsPipeline()
    pipe.set_editor_property("use_source_name_for_asset", True)
    mesh = pipe.get_editor_property("mesh_pipeline")
    mesh.set_editor_property("import_static_meshes", True)
    mesh.set_editor_property("import_skeletal_meshes", False)
    mesh.set_editor_property("build_nanite", nanite)
    mesh.set_editor_property("combine_static_meshes_behavior",
                             unreal.InterchangeCombineStaticMeshesBehavior.DO_NOT_COMBINE)
    mesh.set_editor_property("collision", True)
    mesh.set_editor_property("import_collision_according_to_mesh_name", True)
    mesh.set_editor_property("generate_lightmap_u_vs", False)
    common = pipe.get_editor_property("common_meshes_properties")
    common.set_editor_property("force_all_mesh_as_type", unreal.InterchangeForceMeshType.IFMT_STATIC_MESH)
    common.set_editor_property("recompute_tangents", True)
    common.set_editor_property("use_mikk_t_space", True)
    mats = pipe.get_editor_property("material_pipeline")
    mats.set_editor_property("import_materials", False)
    mats.get_editor_property("texture_pipeline").set_editor_property("import_textures", False)

    override = unreal.InterchangePipelineStackOverride()
    override.add_pipeline(pipe)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", glb_path)
    task.set_editor_property("destination_path", dest)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", override)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.get_objects())
```

The recipe assumes one mesh object per GLB (plus optional `UCX_` hulls): with `DO_NOT_COMBINE` a file with several
mesh objects gives several assets, with `ALL` they are merged ("Combine all the meshes into a single Static Mesh").
`[V PY:InterchangeCombineStaticMeshesBehavior]`

Not verified about this recipe: that a pipeline object created with `unreal.InterchangeGenericAssetsPipeline()` and
passed through `add_pipeline` is honoured for `.glb`; that material slots keep the glTF material names when
`import_materials` is `False`; how `UCX_` meshes behave under `ALL`. Run Appendix A.2 once in a real editor.
Fallback: duplicate the engine's default pipeline asset into `/Game`, edit and save it, and pass its path in
`ImportAssetParameters.override_pipelines` `[M]`.

### 3.3 Nanite and collision on an imported static mesh

`unreal.StaticMeshEditorSubsystem` (Module `StaticMeshEditor`) `[V PY:StaticMeshEditorSubsystem]`:

- `get_nanite_settings(static_mesh)` returns `MeshNaniteSettings`; `set_nanite_settings(static_mesh, nanite_settings, apply_changes=True)`
- `add_simple_collisions(static_mesh, shape_type)` with `unreal.ScriptCollisionShapeType`: `BOX` 0, `SPHERE` 1,
  `CAPSULE` 2, `NDOP10_X` 3, `NDOP10_Y` 4, `NDOP10_Z` 5, `NDOP18` 6, `NDOP26` 7 `[V PY:ScriptCollisionShapeType]`
- `set_convex_decomposition_collisions(static_mesh, hull_count, max_hull_verts, hull_precision)`,
  `bulk_set_convex_decomposition_collisions(static_meshes, ...)`, `remove_collisions(static_mesh)`,
  `get_simple_collision_count(static_mesh)`, `get_convex_collision_count(static_mesh)`,
  `get_collision_complexity(static_mesh)` (there is no setter)
- `enable_section_collision(static_mesh, collision_enabled, lod_index, section_index)`,
  `enable_section_cast_shadow(...)`, `set_generate_lightmap_uv(static_mesh, bool)`, `get_lod_count`,
  `get_number_verts(static_mesh, lod_index)`, `get_number_materials`

`unreal.MeshNaniteSettings` (struct, `EngineTypes.h`): `enabled`, `keep_percent_triangles`, `trim_relative_error`,
`fallback_target`, `fallback_percent_triangles`, `fallback_relative_error`, `generate_fallback`,
`position_precision`, `normal_precision`, `explicit_tangents`, `max_edge_length_factor`, `displacement_maps`,
`displacement_uv_channel`. `[V PY:MeshNaniteSettings]`

`unreal.StaticMesh` `[V PY:StaticMesh]`: properties `nanite_settings`, `body_setup`, `static_materials`,
`lod_for_collision`, `complex_collision_mesh`, `support_ray_tracing`, `generate_mesh_distance_field`,
`light_map_resolution`, `light_map_coordinate_index`; functions `get_material_index(material_slot_name)`,
`set_material(material_index, new_material)`, `get_material(material_index)`, `add_material(material)`,
`get_bounding_box()`, `get_bounds()`, `get_num_triangles(lod_index)`, `get_num_nanite_triangles()`, `get_num_lods()`.

Per-polygon ("complex as simple") collision: `mesh.get_editor_property("body_setup")` then
`set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)`. Values:
`CTF_USE_DEFAULT` 0, `CTF_USE_SIMPLE_AND_COMPLEX` 1, `CTF_USE_SIMPLE_AS_COMPLEX` 2, `CTF_USE_COMPLEX_AS_SIMPLE` 3
("Can be used in simulation for static shapes only"). `[V PY:BodySetup, PY:CollisionTraceFlag]`

### 3.4 Importing textures

- Import each file with an `AssetImportTask` (the asset takes the file's base name, see 3.2), then set properties on
  the `unreal.Texture2D`. Property names `[V PY:Texture, PY:Texture2D]`: `srgb`, `compression_settings`,
  `flip_green_channel` ("When true the texture's green channel will be inverted. This is useful for some normal
  maps."), `lod_group`, `mip_gen_settings`, `virtual_texture_streaming`, `never_stream`, `filter`, `address_x`,
  `address_y`, `max_texture_size`, `compression_no_alpha`, `power_of_two_mode`.
- `unreal.TextureCompressionSettings` `[V PY:TextureCompressionSettings]`: `TC_DEFAULT` 0, `TC_NORMALMAP` 1,
  `TC_MASKS` 2 ("Same compression as Default"), `TC_GRAYSCALE` 3, `TC_DISPLACEMENTMAP` 4 ("For Nanite displacement
  use TC_Alpha"), `TC_VECTOR_DISPLACEMENTMAP` 5, `TC_HDR` 6, `TC_EDITOR_ICON` 7, `TC_ALPHA` 8 ("Single channel
  compressed; can also use for displacement and gray"), `TC_DISTANCE_FIELD_FONT` 9, `TC_HDR_COMPRESSED` 10, `TC_BC7` 11
  ("High quality compressed texture, same size as BC3"), `TC_HALF_FLOAT` 12, `TC_SINGLE_FLOAT` 15, `TC_HDR_F32` 16.
- `unreal.TextureGroup` values used here: `TEXTUREGROUP_WORLD`, `TEXTUREGROUP_WORLD_NORMAL_MAP`,
  `TEXTUREGROUP_WORLD_SPECULAR`, `TEXTUREGROUP_CHARACTER`, `TEXTUREGROUP_CHARACTER_NORMAL_MAP`, `TEXTUREGROUP_WEAPON`,
  `TEXTUREGROUP_WEAPON_NORMAL_MAP`, `TEXTUREGROUP_VEHICLE`, `TEXTUREGROUP_UI`, `TEXTUREGROUP_EFFECTS`,
  `TEXTUREGROUP_SKYBOX`. `[V PY:TextureGroup]`
- The old `unreal.TextureFactory` has `compression_settings`, `lod_group`, `mip_gen_settings`,
  `flip_normal_map_green_channel`, `no_alpha`, `create_material`. `[V PY:TextureFactory]`

Settings for this project's texture names:

| File | `srgb` | `compression_settings` | `flip_green_channel` | `lod_group` |
|---|---|---|---|---|
| `T_<Set>_BC` | `True` | `TC_DEFAULT` | `False` | `TEXTUREGROUP_WORLD` |
| `T_<Set>_N` | `False` | `TC_NORMALMAP` | **`True`** (files are OpenGL, see 5.4) | `TEXTUREGROUP_WORLD_NORMAL_MAP` |
| `T_<Set>_ORM` | `False` | `TC_MASKS` | `False` | `TEXTUREGROUP_WORLD` |
| `T_<Set>_H` | `False` | `TC_ALPHA` | `False` | `TEXTUREGROUP_WORLD` |
| `T_<Set>_E` | `True` | `TC_DEFAULT` | `False` | `TEXTUREGROUP_WORLD` |

Because the Interchange texture pipeline may already mark a detected normal map, set all four properties
explicitly after import instead of trusting the defaults. Whether Interchange's own detection also flips green by
default was not verified; the explicit value wins either way.

### 3.5 Materials and material instances

`unreal.MaterialEditingLibrary` (Module `MaterialEditor`) `[V PY:MaterialEditingLibrary]`:

- `create_material_expression(material, expression_class, node_pos_x=0, node_pos_y=0)`
- `connect_material_property(from_expression, from_output_name, property_)`
- `connect_material_expressions(from_expression, from_output_name, to_expression, to_input_name)`
- `get_material_expression_output_names(material_expression)`, `get_material_expression_input_names(material_expression)`
- `recompile_material(material)`, `layout_material_expressions(material)`, `delete_all_material_expressions(material)`
- `set_material_usage(material, usage)`, `set_base_material_usage(material, usage, value=True)`
- `set_material_instance_parent(instance, new_parent)`
- `set_material_instance_texture_parameter_value(instance, parameter_name, value, association=...)`
- `set_material_instance_scalar_parameter_value(...)`, `set_material_instance_vector_parameter_value(...)`,
  `set_material_instance_static_switch_parameter_value(instance, parameter_name, value, association=..., update_material_instance=True)`
- `update_material_instance(instance)`, `clear_all_material_instance_parameters(instance)`
- `get_texture_parameter_names(material)`, `get_scalar_parameter_names(material)`, `get_vector_parameter_names(material)`

Factories (Module `UnrealEd`): `unreal.MaterialFactoryNew`, `unreal.MaterialInstanceConstantFactoryNew`. `[V PY:MaterialFactoryNew, PY:MaterialInstanceConstantFactoryNew]`
Create with `asset_tools.create_asset("M_Standard", "/Game/Materials", unreal.Material, unreal.MaterialFactoryNew())`.

`unreal.MaterialProperty` `[V PY:MaterialProperty]`: `MP_BASE_COLOR`, `MP_METALLIC`, `MP_SPECULAR`, `MP_ROUGHNESS`,
`MP_NORMAL`, `MP_EMISSIVE_COLOR`, `MP_OPACITY`, `MP_OPACITY_MASK`, `MP_AMBIENT_OCCLUSION`, `MP_WORLD_POSITION_OFFSET`,
`MP_SUBSURFACE_COLOR`, `MP_ANISOTROPY`, `MP_TANGENT`, `MP_REFRACTION`, `MP_FRONT_MATERIAL`, `MP_MATERIAL_ATTRIBUTES`.

Expression classes (all Module `Engine`; header named after the class, except `MaterialExpressionSubstrateSlabBSDF`
in `MaterialExpressionSubstrate.h`) `[V PY:<each>]`:
`MaterialExpressionTextureSampleParameter2D` (`parameter_name`, `texture`, `sampler_type`, `group`, `sort_priority`),
`MaterialExpressionTextureSample`, `MaterialExpressionScalarParameter` (`parameter_name`, `default_value`),
`MaterialExpressionVectorParameter` (`parameter_name`, `default_value`), `MaterialExpressionStaticSwitchParameter`,
`MaterialExpressionMultiply` (`const_a`, `const_b`), `MaterialExpressionAdd`, `MaterialExpressionLinearInterpolate`,
`MaterialExpressionComponentMask` (`r`, `g`, `b`, `a`), `MaterialExpressionTextureCoordinate` (`coordinate_index`,
`u_tiling`, `v_tiling`), `MaterialExpressionConstant`, `MaterialExpressionConstant3Vector`,
`MaterialExpressionAppendVector`, `MaterialExpressionOneMinus`, `MaterialExpressionWorldPosition`,
`MaterialExpressionFresnel`, `MaterialExpressionPanner`, `MaterialExpressionSubstrateSlabBSDF`.

`unreal.MaterialSamplerType` `[V PY:MaterialSamplerType]`: `SAMPLERTYPE_COLOR`, `SAMPLERTYPE_LINEAR_COLOR`,
`SAMPLERTYPE_NORMAL`, `SAMPLERTYPE_MASKS`, `SAMPLERTYPE_GRAYSCALE`, `SAMPLERTYPE_LINEAR_GRAYSCALE`, `SAMPLERTYPE_ALPHA`,
and `SAMPLERTYPE_VIRTUAL_...` variants. The sampler type must match the texture's settings (colour for `_BC`, normal
for `_N`, masks for `_ORM`) or the material fails to compile `[M]`.

`unreal.Material` properties `[V PY:Material]`: `blend_mode` (`BLEND_OPAQUE`, `BLEND_MASKED`, `BLEND_TRANSLUCENT`,
`BLEND_ADDITIVE`, `BLEND_MODULATE`, `BLEND_ALPHA_COMPOSITE`, `BLEND_ALPHA_HOLDOUT`, `BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE`),
`shading_model` (`MSM_DEFAULT_LIT`, `MSM_UNLIT`, `MSM_CLEAR_COAT`, `MSM_SUBSURFACE`, `MSM_TWO_SIDED_FOLIAGE`, `MSM_CLOTH`,
`MSM_THIN_TRANSLUCENT`, `MSM_SINGLE_LAYER_WATER`, ...), `two_sided`, `opacity_mask_clip_value`, `material_domain`
(`MD_SURFACE`, `MD_DEFERRED_DECAL`, `MD_LIGHT_FUNCTION`, `MD_VOLUME`, `MD_POST_PROCESS`, `MD_UI`), `used_with_nanite`,
`used_with_skeletal_mesh`, `used_with_instanced_static_meshes`, `used_with_niagara_sprites`,
`used_with_niagara_mesh_particles`, `tangent_space_normal`, `nanite_override_material`, `fully_rough`, `is_sky`.

Output pin names of a texture sample are believed to be `"RGB"`, `"R"`, `"G"`, `"B"`, `"A"`, `"RGBA"` and an empty
string for the first output of single-output nodes `[M]`; read them with `get_material_expression_output_names`
before connecting.

### 3.6 Other assets a script can create

Factories that exist in 5.8 `[V PY:<each>]`: `SoundAttenuationFactory`, `SoundSubmixFactory`, `SoundClassFactory`,
`SoundCueFactoryNew` (Module `AudioEditor`); `PhysicalMaterialFactoryNew`, `DataTableFactory`, `CurveFactory`,
`BlueprintFactory`, `FontFactory`, `FontFileImportFactory`, `WorldFactory` (Module `UnrealEd`). Sounds: a `.wav`
through an `AssetImportTask` becomes a `unreal.SoundWave` (`looping`, `volume`, `pitch`, `sound_group`,
`loading_behavior`, `sound_asset_compression_type`, read-only `duration`, `num_channels`, `sample_rate`); 5.8 has
`InterchangeAudioTranslator_WAV` (also in 5.7) and `InterchangeGenericAudioPipeline` (`import_sounds`); the old
`SoundFactory` (`auto_create_cue`, ...) is still listed. `[V PY:SoundWave, PY:InterchangeAudioTranslator_WAV, PY57:InterchangeAudioTranslator_WAV, PY:InterchangeGenericAudioPipeline, PY:SoundFactory]`

Niagara: the index lists `NiagaraSystemFactoryNew` and `NiagaraEmitterFactoryNew`, but no documented way to add
emitters or modules by script was found. 5.9 Preview announces "expanded Python APIs covering audio, MetaSounds,
modeling, physics, Niagara, materials, PCG, networking, and UI". `[V PY:index, F:2852840]`
Plan effects so that they do not depend on scripted Niagara authoring in 5.8.

### 3.7 Levels and actors

`unreal.LevelEditorSubsystem` (Module `LevelEditor`) `[V PY:LevelEditorSubsystem]`:
`new_level(asset_path, is_partitioned_world=False)`, `new_level_from_template(asset_path, template_asset_path)`,
`load_level(asset_path)`, `save_current_level()`, `save_all_dirty_levels()`, `get_current_level()`,
`set_current_level_by_name(level_name)`, `build_light_maps(...)`, `editor_set_game_view(...)`,
`set_level_viewport_camera_info(camera_location, camera_rotation, viewport_config_key)`.

`unreal.EditorActorSubsystem` (Module `UnrealEd`) `[V PY:EditorActorSubsystem]`:
`spawn_actor_from_class(actor_class, location, rotation=..., transient=False)`,
`spawn_actor_from_object(object_to_use, location, rotation=..., transient=False)` ("The Actor can be created from a
Factory, Archetype, Blueprint, Class or an Asset. The actor will be created in the current level and will be
selected."; a `StaticMesh` asset gives a `StaticMeshActor` `[M]`), `get_all_level_actors()`, `destroy_actor(actor)`,
`destroy_actors(actors)`,
`set_actor_transform(actor, world_transform)`, `duplicate_actor(...)`, `convert_actors(...)`.

`unreal.EditorLoadingAndSavingUtils` (Module `UnrealEd`, File `FileHelpers.h`) `[V PY:EditorLoadingAndSavingUtils]`:
`new_blank_map(save_existing_map)`, `new_map_from_template(path_to_template_level, save_existing_map)`,
`load_map(filename)`, `save_map(world, asset_path)`, `save_current_level()`,
`save_dirty_packages(save_map_packages, save_content_packages)`, `save_packages(packages_to_save, only_dirty)`.

`unreal.UnrealEditorSubsystem`: `get_editor_world()`, `get_game_world()`. `[V PY:UnrealEditorSubsystem]`

On an actor `[V PY:Actor]`: `set_actor_label(new_actor_label, mark_dirty=True)`, `get_actor_label()`,
`set_folder_path(new_folder_path)`, `set_actor_location(new_location, sweep, teleport)`,
`set_actor_rotation(new_rotation, teleport_physics)`, `set_actor_scale3d(new_scale3d)`,
`set_actor_transform(new_transform, sweep, teleport)`, `get_actor_bounds(only_colliding_components, include_from_child_actors=False)`,
`get_component_by_class(cls)`, `get_components_by_class(cls)`, `attach_to_actor(...)`, property `tags`.

`unreal.StaticMeshActor`: read-only `static_mesh_component`, `set_mobility(mobility)` (`ComponentMobility.STATIC`,
`STATIONARY`, `MOVABLE`). `unreal.StaticMeshComponent`: `set_static_mesh(new_mesh)`, `set_material(element_index, material)`,
`set_material_by_name(material_slot_name, material)`, `set_collision_profile_name(collision_profile_name, update_overlaps=True)`,
`set_collision_enabled(new_type)`, `set_cast_shadow(bool)`, properties `override_materials`, `cast_shadow`,
`disallow_nanite`, `can_ever_affect_navigation`, `visible_in_ray_tracing`. `[V PY:StaticMeshActor, PY:StaticMeshComponent, PY:PrimitiveComponent, PY:ComponentMobility]`

`unreal.WorldSettings` (from `world.get_world_settings()`): `default_game_mode`, `kill_z`, `global_gravity_set`,
`global_gravity_z`, `force_no_precomputed_lighting`, `enable_navigation_system`, `enable_ai_system`,
`enable_world_bounds_checks`. `[V PY:WorldSettings, PY:World]`

Other classes to spawn: `unreal.PlayerStart`, `unreal.NavMeshBoundsVolume`, `unreal.BlockingVolume`,
`unreal.TriggerVolume`, `unreal.DecalActor`, `unreal.PostProcessVolume`, `unreal.AmbientSound`, `unreal.AudioVolume`,
`unreal.NavModifierVolume`. `[V PY:<each>]`

### 3.8 Saving

`unreal.EditorAssetLibrary` (Plugin `EditorScriptingUtilities`) `[V PY:EditorAssetLibrary]`:
`save_asset(asset_to_save, only_if_is_dirty=True)` (takes a path), `save_loaded_asset(asset_to_save, only_if_is_dirty=True)`,
`save_loaded_assets(assets, only_if_is_dirty=True)`, `save_directory(directory_path, only_if_is_dirty=True, recursive=True)`,
`does_asset_exist(asset_path)`, `load_asset(asset_path)`, `delete_asset(asset_path_to_delete)`,
`duplicate_asset(source_asset_path, destination_asset_path)`, `rename_asset(source, destination)`,
`make_directory(directory_path)`, `list_assets(directory_path, recursive=True, include_folder=False)`,
`set_metadata_tag(object, tag, value)`, `get_metadata_tag(object, tag)`. "The editor should not be in play in editor
mode. It will not work on assets of the type level." `unreal.EditorAssetSubsystem` has the same functions. `[V PY:EditorAssetSubsystem]`

Levels are saved with `LevelEditorSubsystem.save_current_level()` or `EditorLoadingAndSavingUtils.save_map(world, asset_path)`.

### 3.9 Navigation

- The reference exposes no "build navigation" function. `unreal.NavigationSystemV1` has
  `get_navigation_system(world_context_object)`, `on_navigation_bounds_updated(nav_volume)`,
  `is_navigation_being_built(world_context_object)`, `is_navigation_being_built_or_locked(...)`,
  `project_point_to_navigation(world_context_object, point, nav_data, filter_class, query_extent=...)`,
  `get_random_reachable_point_in_radius(...)`, `find_path_to_location_synchronously(world_context_object, path_start, path_end, pathfinding_context=None, filter_class=None)`,
  `register_navigation_invoker(...)`. `[V PY:NavigationSystemV1]`
- A scripted volume: `spawn_actor_from_class(unreal.NavMeshBoundsVolume, centre)`; its default brush is a 2 m cube,
  so scale it with `set_actor_scale3d`. Build with the console command `BuildPaths` through
  `unreal.SystemLibrary.execute_console_command(world, "BuildPaths")`. `[M+ F:2849553]` (a working 5.8.3 Linux script);
  `execute_console_command(world_context_object, command, specific_player=None)` `[V PY:SystemLibrary]`
- **Trap in 5.8.3:** right after a level loads, the navigation system holds a build lock until asset compilation is
  idle and about 2 s and 16 ticks have passed; an explicit `BuildPaths` during that time logs
  `Build Navigation NOT building because navigation build is locked` and still reports success. A script cannot wait
  for the lock inside one call because the unlock needs editor ticks. `[M+ F:2849553]`
- Therefore: (1) set `RuntimeGeneration=Dynamic` (2.2) so the game does not depend on the saved navmesh; (2) if a
  build is wanted, issue it from a later tick (`unreal.register_slate_post_tick_callback`) or a second editor run,
  and check the result with `project_point_to_navigation` on a known walkable point.
- `unreal.RecastNavMesh` properties: `runtime_generation`, `agent_radius`, `agent_height`, `agent_max_slope`,
  `agent_max_step_height`, `cell_size`, `cell_height`, `tile_size_uu`, `min_region_area`, `force_rebuild_on_load`. `[V PY:RecastNavMesh]`

### 3.10 Running a script without the editor window

- Commandlet: `UnrealEditor-Cmd.exe "<abs>\MurderInc.uproject" -run=pythonscript -script="<abs>\script.py --arg value"`.
  Arguments follow the script path inside the same quotes. Put the project first, flags after it. `[M+ F:724404, F:1771494, F:1538861]`
- Whole editor, script, then exit: `-ExecutePythonScript="<abs>\script.py"`. `[M+ F:2506983]`
  The reference confirms the behaviour: with `bKeepPythonScriptAlive` false (default) "it will close the editor
  during the next tick (when executing a Python script in the editor-environment using the UnrealEditor-Cmd
  commandline tool)". Keep it open with `unreal.EditorPythonScripting.set_keep_python_script_alive(True)` and leave
  with `unreal.SystemLibrary.quit_editor()`. `[V PY:EditorPythonScripting, PY:SystemLibrary]`
- Log to the console: `-stdout -FullStdOutLogOutput`; add `-log` to also write the file. `[M+ F:1538861]`
- Usual companions: `-unattended -nosplash -nullrhi` `[M+ F:2763115]`, `-nopause` `[M]` (`-nullrhi` removes
  rendering, so no screenshots).
- The commandlet does not tick the editor; work that needs ticks (navigation build, asynchronous import, shader
  compilation callbacks) belongs in `-ExecutePythonScript`. `[M+ F:724404, F:2849553]`
- Linux: the same flags on `Engine/Binaries/Linux/UnrealEditor-Cmd` `[M]`; a 2026 CI script runs
  `/home/ue4/UnrealEngine/Engine/Binaries/Linux/UnrealEditor "<uproject>" -execcmds="...;Quit" -stdout -unattended -NOSPLASH -NullRHI`
  inside Epic's container image `ghcr.io/epicgames/unreal-engine:dev-slim-5.6.1`. `[M+ F:2763115]`
- `Content/Python/init_unreal.py` runs at editor start `[M]`; the reference mentions "a plugin's init_unreal.py
  script". `[V PY:PythonTestRunner]`
- Screenshots from a script (needs a real RHI): `unreal.AutomationLibrary.take_high_res_screenshot(res_x, res_y, filename, camera=None, mask_enabled=False, capture_hdr=False, ...)`
  (Module `FunctionalTesting`). `[V PY:AutomationLibrary]`

---

## 4. C++ gameplay framework

### 4.1 Modules for `MurderInc.Build.cs`

```csharp
PublicDependencyModuleNames.AddRange(new string[] {
    "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput",
    "AIModule", "NavigationSystem", "GameplayTasks",
    "UMG", "Slate", "SlateCore",
    "Niagara", "PhysicsCore", "AudioMixer", "DeveloperSettings",
    "Json", "JsonUtilities"
});
```

Verified module names (from the class pages): `Engine`, `CoreUObject` (`PY:AssetData`), `InputCore` (`PY:Key`),
`EnhancedInput`, `AIModule`, `NavigationSystem`, `UMG`, `Slate` (`PY:Anchors`), `SlateCore` (`PY:SlateBrush`),
`Niagara`, `PhysicsCore` (`PY:PhysicalMaterial`), `AudioMixer` (`PY:AudioMixerLibrary`), `DeveloperSettings`
(`PY:DeveloperSettings`), `EngineSettings` (`PY:GameMapsSettings`). `Core`, `Json`, `JsonUtilities`, `GameplayTasks`
are `[M]`; `GameplayTasks` is needed to link a class derived from `AAIController` `[M]`.

Editor-only module names, if an editor module is ever written `[V PY:<class in brackets>]`: `UnrealEd`
(`AssetImportTask`), `AssetTools` (`AssetTools`), `LevelEditor` (`LevelEditorSubsystem`), `MaterialEditor`
(`MaterialEditingLibrary`), `StaticMeshEditor` (`StaticMeshEditorSubsystem`), `SkeletalMeshEditor`,
`InterchangeEngine`, `InterchangeCore`, `InterchangePipelines`, `InterchangeImport`, `EditorScriptingUtilities`,
`PythonScriptPlugin`, `EditorSubsystem`, `Blutility` (`EditorUtilityLibrary`), `FunctionalTesting`, `AudioEditor`,
`ToolsetRegistry`.

Project skeleton `[M]`: `Source/MurderInc.Target.cs` (`Type = TargetType.Game`), `Source/MurderIncEditor.Target.cs`
(`Type = TargetType.Editor`), both with `DefaultBuildSettings = BuildSettingsVersion.Latest;`
`IncludeOrderVersion = EngineIncludeOrderVersion.Latest;` `ExtraModuleNames.Add("MurderInc");`
`Source/MurderInc/MurderInc.Build.cs` with `PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;`
`Source/MurderInc/MurderInc.cpp` with `#include "Modules/ModuleManager.h"` and
`IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, MurderInc, "MurderInc");`. Export macro `MURDERINC_API`.
Every reflected header ends its includes with `#include "<File>.generated.h"`. Include each header you use; do not
rely on `Engine.h`. `UPROPERTY` object members are `TObjectPtr<T>`. `FVector` components are `double`.

### 4.2 Classes, modules and headers

Module and header file name are `[V PY:<Python name>]`. The folder in front of the file name is `[M]`.

| C++ | Python name | Module | `#include` |
|---|---|---|---|
| `AActor` | `Actor` | Engine | `GameFramework/Actor.h` |
| `APawn` | `Pawn` | Engine | `GameFramework/Pawn.h` |
| `ACharacter` | `Character` | Engine | `GameFramework/Character.h` |
| `UCharacterMovementComponent` | `CharacterMovementComponent` | Engine | `GameFramework/CharacterMovementComponent.h` |
| `UCapsuleComponent` | `CapsuleComponent` | Engine | `Components/CapsuleComponent.h` |
| `UCameraComponent` | `CameraComponent` | Engine | `Camera/CameraComponent.h` |
| `USkeletalMeshComponent` | `SkeletalMeshComponent` | Engine | `Components/SkeletalMeshComponent.h` |
| `UStaticMeshComponent` | `StaticMeshComponent` | Engine | `Components/StaticMeshComponent.h` |
| `UInstancedStaticMeshComponent` | `InstancedStaticMeshComponent` | Engine | `Components/InstancedStaticMeshComponent.h` |
| `APlayerController` | `PlayerController` | Engine | `GameFramework/PlayerController.h` |
| `AGameModeBase` | `GameModeBase` | Engine | `GameFramework/GameModeBase.h` |
| `AGameStateBase` | `GameStateBase` | Engine | `GameFramework/GameStateBase.h` |
| `UGameInstance` | `GameInstance` | Engine | `Engine/GameInstance.h` |
| `AHUD` | `HUD` | Engine | `GameFramework/HUD.h` |
| `APlayerCameraManager` | `PlayerCameraManager` | Engine | `Camera/PlayerCameraManager.h` |
| `UGameplayStatics` | `GameplayStatics` | Engine | `Kismet/GameplayStatics.h` |
| `UKismetSystemLibrary` | `SystemLibrary` | Engine | `Kismet/KismetSystemLibrary.h` |
| `UKismetMathLibrary` | `MathLibrary` | Engine | `Kismet/KismetMathLibrary.h` |
| `FHitResult` | `HitResult` | Engine | `Engine/HitResult.h` |
| `ECollisionChannel`, `ECollisionResponse`, `ECollisionEnabled`, `EMovementMode` | `CollisionChannel`, ... | Engine | `Engine/EngineTypes.h` |
| `UDamageType` | `DamageType` | Engine | `GameFramework/DamageType.h` |
| `FDamageEvent`, `FPointDamageEvent`, `FRadialDamageEvent` | `DamageEvent`, ... | Engine | `Engine/DamageEvents.h` |
| `FTimerHandle` | `TimerHandle` | Engine | `Engine/TimerHandle.h` |
| `UGameUserSettings` | `GameUserSettings` | Engine | `GameFramework/GameUserSettings.h` |
| `USaveGame`, `ULocalPlayerSaveGame` | `SaveGame`, `LocalPlayerSaveGame` | Engine | `GameFramework/SaveGame.h` |
| `UAudioComponent` | `AudioComponent` | Engine | `Components/AudioComponent.h` |
| `USoundBase`, `USoundWave`, `USoundCue` | same | Engine | `Sound/SoundBase.h`, `Sound/SoundWave.h`, `Sound/SoundCue.h` |
| `USoundAttenuation` (`FSoundAttenuationSettings`) | `SoundAttenuation` | Engine | `Sound/SoundAttenuation.h` |
| `USoundSubmix`, `USoundClass`, `USoundMix`, `USoundConcurrency` | same | Engine | `Sound/SoundSubmix.h`, `Sound/SoundClass.h`, `Sound/SoundMix.h`, `Sound/SoundConcurrency.h` |
| `UStaticMesh`, `USkeletalMesh`, `UTexture2D` | same | Engine | `Engine/StaticMesh.h`, `Engine/SkeletalMesh.h`, `Engine/Texture2D.h` |
| `UMaterialInterface`, `UMaterialInstanceDynamic` | same | Engine | `Materials/MaterialInterface.h`, `Materials/MaterialInstanceDynamic.h` |
| `UPhysicalMaterial` | `PhysicalMaterial` | PhysicsCore | `PhysicalMaterials/PhysicalMaterial.h` |
| `UDecalComponent` | `DecalComponent` | Engine | `Components/DecalComponent.h` |
| `UBoxComponent`, `USphereComponent` | same | Engine | `Components/BoxComponent.h`, `Components/SphereComponent.h` |
| `UDirectionalLightComponent`, `USkyLightComponent`, `UPointLightComponent`, `USpotLightComponent` | same | Engine | `Components/<Name without U>.h` |
| `APostProcessVolume`, `FPostProcessSettings` | `PostProcessVolume`, `PostProcessSettings` | Engine | `Engine/PostProcessVolume.h`, `Engine/Scene.h` |
| `AWorldSettings`, `APlayerStart` | same | Engine | `GameFramework/WorldSettings.h`, `GameFramework/PlayerStart.h` |
| `UWorld` | `World` | Engine | `Engine/World.h` |
| `UGameInstanceSubsystem`, `UWorldSubsystem`, `ULocalPlayerSubsystem` | same | Engine | `Subsystems/GameInstanceSubsystem.h`, `Subsystems/WorldSubsystem.h`, `Subsystems/LocalPlayerSubsystem.h` |
| `UDeveloperSettings` | `DeveloperSettings` | DeveloperSettings | `Engine/DeveloperSettings.h` |
| `UCameraShakeBase` | `CameraShakeBase` | Engine | `Camera/CameraShakeBase.h` |
| `AAIController` | `AIController` | AIModule | `AIController.h` |
| `UPathFollowingComponent`, `EPathFollowingRequestResult`, `EPathFollowingResult` | same | AIModule | `Navigation/PathFollowingComponent.h` |
| `UPawnSensingComponent` | `PawnSensingComponent` | AIModule | `Perception/PawnSensingComponent.h` |
| `UAIPerceptionComponent` | `AIPerceptionComponent` | AIModule | `Perception/AIPerceptionComponent.h` |
| `UAISenseConfig_Sight`, `UAISenseConfig_Hearing`, `UAISenseConfig_Damage` | same | AIModule | `Perception/AISenseConfig_Sight.h`, `..._Hearing.h`, `..._Damage.h` |
| `UAISense_Sight`, `UAISense_Hearing`, `UAISense_Damage` | same | AIModule | `Perception/AISense_Sight.h`, ... |
| `UAIPerceptionStimuliSourceComponent` | same | AIModule | `Perception/AIPerceptionStimuliSourceComponent.h` |
| `FAIStimulus` | `AIStimulus` | AIModule | `Perception/AIPerceptionTypes.h` |
| `FGenericTeamId` | `GenericTeamId` | AIModule | `GenericTeamAgentInterface.h` |
| `UAIBlueprintHelperLibrary` | `AIHelperLibrary` | AIModule | `Blueprint/AIBlueprintHelperLibrary.h` |
| `UNavigationSystemV1` | `NavigationSystemV1` | NavigationSystem | `NavigationSystem.h` |
| `ARecastNavMesh` | `RecastNavMesh` | NavigationSystem | `NavMesh/RecastNavMesh.h` |
| `ANavMeshBoundsVolume` | `NavMeshBoundsVolume` | NavigationSystem | `NavMesh/NavMeshBoundsVolume.h` |
| `UNavigationPath` | `NavigationPath` | NavigationSystem | `NavigationPath.h` |
| `FNavAgentProperties` | `NavAgentProperties` | Engine | `AI/Navigation/NavigationTypes.h` |
| `UInputAction` | `InputAction` | EnhancedInput | `InputAction.h` |
| `UInputMappingContext` | `InputMappingContext` | EnhancedInput | `InputMappingContext.h` |
| `UEnhancedInputComponent` | `EnhancedInputComponent` | EnhancedInput | `EnhancedInputComponent.h` |
| `UEnhancedInputLocalPlayerSubsystem` | same | EnhancedInput | `EnhancedInputSubsystems.h` |
| `FInputActionValue`, `EInputActionValueType` | `InputActionValue`, ... | EnhancedInput | `InputActionValue.h` |
| `UInputModifier...`, `EInputAxisSwizzle` | `InputModifierNegate`, ... | EnhancedInput | `InputModifiers.h` |
| `UInputTrigger...`, `ETriggerEvent` | `InputTriggerPressed`, `TriggerEvent` | EnhancedInput | `InputTriggers.h` |
| `FEnhancedActionKeyMapping` | `EnhancedActionKeyMapping` | EnhancedInput | `EnhancedActionKeyMapping.h` |
| `FKey`, `EKeys` | `Key` | InputCore | `InputCoreTypes.h` |
| `UUserWidget` | `UserWidget` | UMG | `Blueprint/UserWidget.h` |
| `UWidgetTree` | `WidgetTree` | UMG | `Blueprint/WidgetTree.h` |
| `UCanvasPanel`, `UCanvasPanelSlot`, `UOverlay`, `UHorizontalBox`, `UVerticalBox`, `USizeBox`, `UBorder`, `UImage`, `UTextBlock`, `UProgressBar`, `UButton` | same | UMG | `Components/<Name without U>.h` |
| `UWidgetBlueprintLibrary` | `WidgetLibrary` | UMG | `Blueprint/WidgetBlueprintLibrary.h` |
| `UWidgetLayoutLibrary` | `WidgetLayoutLibrary` | UMG | `Blueprint/WidgetLayoutLibrary.h` |
| `UGameViewportSubsystem` | `GameViewportSubsystem` | UMG | `Blueprint/GameViewportSubsystem.h` |
| `ESlateVisibility` | `SlateVisibility` | UMG | `Components/SlateWrapperTypes.h` |
| `FSlateBrush`, `FSlateColor`, `FSlateFontInfo`, `FMargin` | same | SlateCore | `Styling/SlateBrush.h`, `Styling/SlateColor.h`, `Fonts/SlateFontInfo.h`, `Layout/Margin.h` |
| `FAnchors` | `Anchors` | Slate | `Widgets/Layout/Anchors.h` |
| `UNiagaraFunctionLibrary` | `NiagaraFunctionLibrary` | Niagara | `NiagaraFunctionLibrary.h` |
| `UNiagaraComponent`, `UNiagaraSystem` | same | Niagara | `NiagaraComponent.h`, `NiagaraSystem.h` |
| `ENCPoolMethod` | `NCPoolMethod` | Niagara | `NiagaraComponentPoolMethodEnum.h` |
| `UAudioMixerBlueprintLibrary` | `AudioMixerLibrary` | AudioMixer | `AudioMixerBlueprintLibrary.h` |
| `UQuartzSubsystem` | `QuartzSubsystem` | AudioMixer | `Quartz/QuartzSubsystem.h` |

Not reflected, so `[M]` entirely: `Misc/FileHelper.h`, `Misc/Paths.h`, `Dom/JsonObject.h`,
`Serialization/JsonReader.h`, `Serialization/JsonSerializer.h`, `JsonObjectConverter.h`, `TimerManager.h`,
`Misc/AutomationTest.h`, `CollisionQueryParams.h`, `Engine/Engine.h` (`GEngine`), `Engine/GameViewportClient.h`,
`Widgets/SCompoundWidget.h`, `Widgets/DeclarativeSyntaxSupport.h`, `Widgets/SWeakWidget.h`, `Widgets/SOverlay.h`, `Widgets/SCanvas.h`,
`Widgets/Layout/SConstraintCanvas.h`, `Widgets/Layout/SBox.h`, `Widgets/Layout/SBorder.h`,
`Widgets/Text/STextBlock.h`, `Widgets/Images/SImage.h`, `Widgets/SLeafWidget.h`, `Rendering/DrawElements.h`,
`Styling/CoreStyle.h`.

### 4.3 `ACharacter` and `UCharacterMovementComponent`

Movement properties, all on `UCharacterMovementComponent` `[V PY:CharacterMovementComponent]` (C++ spelling by the
rule in 0.4; the quoted words are from the reference):

| C++ member | Python | Reference text |
|---|---|---|
| `MaxWalkSpeed` | `max_walk_speed` | "The maximum ground speed when walking. Also determines maximum lateral speed when falling." |
| `MaxWalkSpeedCrouched` | `max_walk_speed_crouched` | "The maximum ground speed when walking and crouched." |
| `MaxAcceleration` | `max_acceleration` | "Max Acceleration (rate of change of velocity)" |
| `BrakingDecelerationWalking` | `braking_deceleration_walking` | "Deceleration when walking and not applying acceleration. This is a constant opposing force that directly lowers velocity by a constant value." |
| `BrakingDecelerationFalling` | `braking_deceleration_falling` | "Lateral deceleration when falling and not applying acceleration." |
| `GroundFriction` | `ground_friction` | "Setting that affects movement control. Higher values allow faster changes in direction." Also used for braking, times `BrakingFrictionFactor`, when `bUseSeparateBrakingFriction` is false |
| `BrakingFrictionFactor` | `braking_friction_factor` | "Factor used to multiply actual value of friction used when braking." |
| `BrakingFriction`, `bUseSeparateBrakingFriction` | `braking_friction`, `use_separate_braking_friction` | separate braking drag, "Only used if bUseSeparateBrakingFriction setting is true" |
| `BrakingSubStepTime` | `braking_sub_step_time` | "Time substepping when applying braking friction." |
| `JumpZVelocity` | `jump_z_velocity` | "Initial velocity (instantaneous vertical acceleration) when jumping." |
| `GravityScale` | `gravity_scale` | "Custom gravity scale. Gravity is multiplied by this amount for the character." |
| `AirControl`, `AirControlBoostMultiplier`, `AirControlBoostVelocityThreshold` | `air_control`, ... | "When falling, amount of lateral movement control available to the character." |
| `MaxStepHeight` | `max_step_height` | "Maximum height character can step up" |
| `SetWalkableFloorAngle(float)` | `set_walkable_floor_angle` | "Max angle in degrees of a walkable surface." (`walkable_floor_z` is read-only) |
| crouched half height | `crouched_half_height` | read-write property; in C++ use `SetCrouchedHalfHeight(float)` / `GetCrouchedHalfHeight()` `[M]` |
| `bCanWalkOffLedgesWhenCrouching` | `can_walk_off_ledges_when_crouching` | |
| `NavAgentProps.bCanCrouch` | `nav_agent_props.can_crouch` | "If true, this Pawn is capable of crouching." Must be true or `Crouch()` does nothing `[M]`; in C++ `GetNavAgentPropertiesRef().bCanCrouch = true;` `[M]` |
| `bOrientRotationToMovement`, `RotationRate`, `bUseControllerDesiredRotation` | `orient_rotation_to_movement`, ... | rotation behaviour (for enemies) |
| `SetMovementMode(EMovementMode, uint8)` | `set_movement_mode(new_movement_mode, new_custom_mode=0)` | `MOVE_NONE`, `MOVE_WALKING`, `MOVE_NAV_WALKING`, `MOVE_FALLING`, `MOVE_SWIMMING`, `MOVE_FLYING`, `MOVE_CUSTOM` `[V PY:MovementMode]` |
| `AddImpulse(FVector, bool)`, `DisableMovement()` | `add_impulse(impulse, velocity_change=False)`, `disable_movement()` | |

Deprecated on this component: `fixed_path_braking_distance`, `use_acceleration_for_paths`,
`use_fixed_braking_distance_for_paths`, `update_nav_agent_with_owners_collision` ("please use NavMovementProperties...
instead"), `get_movement_base` (use `get_movement_base_object`). `[V PY:CharacterMovementComponent]`

`ACharacter` `[V PY:Character]`: functions `Jump()`, `StopJumping()`, `CanJump()`, `Crouch(bool bClientSimulation = false)`,
`UnCrouch(bool)`, `CanCrouch()`, `LaunchCharacter(FVector LaunchVelocity, bool bXYOverride, bool bZOverride)`,
`PlayAnimMontage(...)`; properties `JumpMaxCount`, `JumpMaxHoldTime`, `bIsCrouched`, `CrouchedEyeHeight`,
`BaseEyeHeight`; read-only components `mesh`, `capsule_component`, `character_movement` (C++ `GetMesh()`,
`GetCapsuleComponent()`, `GetCharacterMovement()` `[M]`); events `on_landed(hit)`, `on_jumped()`,
`on_start_crouch(half_height_adjust, scaled_half_height_adjust)`, `on_end_crouch(...)`,
`on_movement_mode_changed(prev_movement_mode, new_movement_mode, prev_custom_mode, new_custom_mode)`,
`on_walking_off_ledge(...)` (C++ virtuals `Landed(const FHitResult&)`, `OnStartCrouch`, `OnEndCrouch`,
`OnMovementModeChanged(EMovementMode, uint8)` `[M]`).

`APawn` `[V PY:Pawn]`: `AddMovementInput(FVector WorldDirection, float ScaleValue = 1.0f, bool bForce = false)`,
`AddControllerYawInput(float)`, `AddControllerPitchInput(float)`, `bUseControllerRotationYaw` / `Pitch` / `Roll`,
`AutoPossessAI` (`EAutoPossessAI`), `AIControllerClass`, `SpawnDefaultController()`,
`PawnMakeNoise(float Loudness, FVector NoiseLocation, bool bUseNoiseMakerLocation = true, AActor* NoiseMaker = nullptr)`,
`GetController()`, `IsPlayerControlled()`.

Defaults believed correct `[M]`: capsule radius 34, half height 88; `MaxWalkSpeed` 600; `MaxWalkSpeedCrouched` 300;
`JumpZVelocity` 420; `GravityScale` 1; `MaxAcceleration` 2048; `BrakingDecelerationWalking` 2048; `GroundFriction` 8;
`BrakingFrictionFactor` 2; `AirControl` 0.05; `MaxStepHeight` 45; world gravity -980 cm/s2
(`[/Script/Engine.PhysicsSettings] DefaultGravityZ`, property `default_gravity_z` `[V PY:PhysicsSettings]`). Set every
tuning value explicitly from the web game's numbers (metres times 100) instead of trusting these.

First-person view model (the enum is in the 5.5, 5.6, 5.7 and 5.8 references; the properties were read in 5.8)
`[V PY:PrimitiveComponent, PY:CameraComponent, PY:FirstPersonPrimitiveType, PY57/PY56/PY55:FirstPersonPrimitiveType]`:
`UPrimitiveComponent::FirstPersonPrimitiveType` with `EFirstPersonPrimitiveType`: `NONE` 0, `FIRST_PERSON` 1
("rendered as first person and affected by first person properties on the camera"), `WORLD_SPACE_REPRESENTATION` 2
("the primitive that other players would see and is used to cast shadow onto the ground"); setter
`set_first_person_primitive_type(value)`. Camera: `enable_first_person_field_of_view`, `first_person_field_of_view`,
`enable_first_person_scale`, `first_person_scale`, with setters `set_enable_first_person_field_of_view`,
`set_first_person_field_of_view`, `set_enable_first_person_scale`, `set_first_person_scale`. "These parameters can be
used to render the component with a different field of view and a smaller depth range such that clipping with the
scene can be avoided." Material nodes `MaterialExpressionIsFirstPerson`, `MaterialExpressionFirstPersonOutput` exist. `[V PY:index]`

`UCameraComponent::FieldOfView` is "The horizontal field of view (in degrees)". `[V PY:CameraComponent]` The web game's
three.js camera uses a vertical field of view: convert with `hfov = 2 * atan(tan(vfov / 2) * aspect)`, or set
`[/Script/Engine.LocalPlayer] AspectRatioAxisConstraint=AspectRatio_MaintainYFOV` `[M]`.

### 4.4 Enhanced Input set up entirely in C++

Verified `[V PY:InputAction, PY:InputMappingContext, PY:EnhancedActionKeyMapping, PY:EnhancedInputLocalPlayerSubsystem, PY:InputActionValueType, PY:TriggerEvent, PY:InputAxisSwizzle, PY:InputModifierNegate, PY:InputModifierSwizzleAxis, PY:InputModifierDeadZone, PY:InputModifierScalar, PY:InputTriggerHold, PY:InputTriggerTap, PY:ModifyContextOptions]`:

- `UInputAction` properties: `ValueType` (`EInputActionValueType`: `BOOLEAN` 0, `AXIS1D` 1, `AXIS2D` 2, `AXIS3D` 3;
  C++ `Boolean`, `Axis1D`, `Axis2D`, `Axis3D`), `Triggers`, `Modifiers`, `bConsumeInput`, `bTriggerWhenPaused`,
  `AccumulationBehavior`.
- `UInputMappingContext::MapKey(const UInputAction* Action, FKey ToKey)` returns the mapping
  (`map_key(action, to_key) -> EnhancedActionKeyMapping`); also `UnmapKey`, `UnmapAllKeysFromAction`, `UnmapAll`.
- **The `Mappings` array is deprecated since 5.7** ("Use the DefaultKeyMappings struct instead"; new property
  `default_key_mappings` of type `InputMappingContextMappingData` with a `mappings` array). 5.6 had no such note.
  Build contexts with `MapKey` only. `[V PY:InputMappingContext, PY57:InputMappingContext, PY56:InputMappingContext, PY:InputMappingContextMappingData]`
- `FEnhancedActionKeyMapping` fields: `Action`, `Key`, `Modifiers`, `Triggers`.
- `UEnhancedInputLocalPlayerSubsystem`: `add_mapping_context(mapping_context, priority, options)`,
  `remove_mapping_context(mapping_context, options)`, `clear_all_mappings()`, `has_mapping_context(...)`,
  `request_rebuild_control_mappings(...)`, `query_keys_mapped_to_action(action)`, `inject_input_for_action(action, raw_value, modifiers, triggers)`.
  `FModifyContextOptions`: `bIgnoreAllPressedKeysUntilRelease` (default true), `bForceImmediately`, `bNotifyUserSettings`.
- `ETriggerEvent`: `TRIGGERED` 1, `STARTED` 2, `ONGOING` 4, `CANCELED` 8, `COMPLETED` 16 (C++ `Triggered`, `Started`,
  `Ongoing`, `Canceled`, `Completed`).
- Modifiers: `UInputModifierNegate` (`bX`, `bY`, `bZ`), `UInputModifierSwizzleAxis` (`Order`, `EInputAxisSwizzle`:
  `YXZ` 0 "Swap X and Y axis. Useful for binding 1D inputs to the Y axis for 2D actions.", `ZYX` 1, `XZY` 2, `YZX` 3,
  `ZXY` 4), `UInputModifierDeadZone` (`LowerThreshold`, `UpperThreshold`, `Type`), `UInputModifierScalar` (`Scalar`).
- Triggers: `UInputTriggerPressed`, `UInputTriggerReleased`, `UInputTriggerHold` (`HoldTimeThreshold`, `bIsOneShot`),
  `UInputTriggerTap` (`TapReleaseTimeThreshold`).
- `APlayerController::InputYawScale` / `InputPitchScale` are deprecated: "Use the Enhanced Input plugin Scalar
  Modifier instead. See UInputSettings::bEnableLegacyInputScales to enable legacy behavior". `[V PY:PlayerController]`
- `UInputSettings` properties `DefaultPlayerInputClass`, `DefaultInputComponentClass`, `bEnableLegacyInputScales`. `[V PY:InputSettings]`

`Config/DefaultInput.ini` (property names verified, values `[M]`):

```ini
[/Script/Engine.InputSettings]
DefaultPlayerInputClass=/Script/EnhancedInput.EnhancedPlayerInput
DefaultInputComponentClass=/Script/EnhancedInput.EnhancedInputComponent
bEnableLegacyInputScales=False
```

Code shape `[M]` (names above are verified, the template functions are not reflected):

```cpp
// members: UPROPERTY() TObjectPtr<UInputMappingContext> Context; UPROPERTY() TObjectPtr<UInputAction> MoveAction;
MoveAction = NewObject<UInputAction>(this, TEXT("IA_Move"));
MoveAction->ValueType = EInputActionValueType::Axis2D;
Context = NewObject<UInputMappingContext>(this, TEXT("IMC_Default"));
FEnhancedActionKeyMapping& W = Context->MapKey(MoveAction, EKeys::W);
W.Modifiers.Add(NewObject<UInputModifierSwizzleAxis>(Context));           // W -> +Y
FEnhancedActionKeyMapping& S = Context->MapKey(MoveAction, EKeys::S);
S.Modifiers.Add(NewObject<UInputModifierSwizzleAxis>(Context));
S.Modifiers.Add(NewObject<UInputModifierNegate>(Context));                // S -> -Y
Context->MapKey(MoveAction, EKeys::D);                                     // D -> +X
Context->MapKey(MoveAction, EKeys::A).Modifiers.Add(NewObject<UInputModifierNegate>(Context));

if (const ULocalPlayer* LP = PlayerController->GetLocalPlayer())
    if (UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(LP))
        Sub->AddMappingContext(Context, 0);

// in SetupPlayerInputComponent(UInputComponent* PlayerInputComponent):
if (UEnhancedInputComponent* EIC = Cast<UEnhancedInputComponent>(PlayerInputComponent))
    EIC->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AMIPlayerCharacter::OnMove);

void AMIPlayerCharacter::OnMove(const FInputActionValue& Value) { const FVector2D V = Value.Get<FVector2D>(); }
```

`SetupPlayerInputComponent` can run before `BeginPlay`: create the actions in one function that both call. Keep
every created object in a `UPROPERTY` member or it is garbage collected. Finish with one returned mapping reference
before calling `MapKey` again: the next call can move the array. Mouse look is `EKeys::Mouse2D` on an `Axis2D`
action; check the pitch sign once in play.

### 4.5 Line traces and collision channels

- Blueprint-style library, as the reference lists it:
  `line_trace_single(world_context_object, start, end, trace_channel, trace_complex, actors_to_ignore, draw_debug_type, ignore_self=True, trace_color, trace_hit_color, draw_time=5.0)`
  returning the hit or `None`; also `line_trace_multi`, `line_trace_single_by_profile(..., profile_name, ...)`,
  `line_trace_single_for_objects(..., object_types, ...)`, `sphere_trace_single(..., radius, ...)`,
  `capsule_trace_single`, `box_trace_single`,
  `sphere_overlap_actors(world_context_object, sphere_pos, sphere_radius, object_types, actor_class_filter, actors_to_ignore)`.
  `trace_channel` there is a `TraceTypeQuery`. `[V PY:SystemLibrary, PY:TraceTypeQuery]` In C++ these are
  `UKismetSystemLibrary::LineTraceSingle(...)` etc. with the hit as an out parameter after `DrawDebugType` `[M]`.
- Native call `[M]`:
  `GetWorld()->LineTraceSingleByChannel(FHitResult& OutHit, const FVector& Start, const FVector& End, ECollisionChannel TraceChannel, const FCollisionQueryParams& Params)`;
  `FCollisionQueryParams Params(SCENE_QUERY_STAT(MIWeaponTrace), /*bTraceComplex*/ true, /*IgnoreActor*/ this);`
  `Params.bReturnPhysicalMaterial = true; Params.AddIgnoredActor(Other);` Also `LineTraceMultiByChannel`,
  `SweepSingleByChannel(OutHit, Start, End, FQuat::Identity, Channel, FCollisionShape::MakeSphere(R), Params)`,
  `OverlapMultiByChannel`.
- `FHitResult` fields in the Python constructor: `blocking_hit`, `initial_overlap`, `time`, `distance`, `location`,
  `impact_point`, `normal`, `impact_normal`, `phys_mat`, `hit_actor`, `hit_component`, `hit_bone_name`, `bone_name`,
  `hit_item`, `element_index`, `face_index`, `trace_start`, `trace_end`. `[V PY:HitResult]` C++ members `[M]`:
  `bBlockingHit`, `bStartPenetrating`, `Time`, `Distance`, `Location`, `ImpactPoint`, `Normal`, `ImpactNormal`,
  `PhysMaterial`, `BoneName`, `FaceIndex`, `TraceStart`, `TraceEnd`, and the accessors `GetActor()`, `GetComponent()`.
- `ECollisionChannel` named values: `ECC_WorldStatic`, `ECC_WorldDynamic`, `ECC_Pawn`, `ECC_Visibility`, `ECC_Camera`,
  `ECC_PhysicsBody`, `ECC_Vehicle`, `ECC_Destructible`. `[V PY:CollisionChannel]` Custom ones are
  `ECC_GameTraceChannel1` to `ECC_GameTraceChannel18` `[M]`.
- `ECollisionResponse`: `ECR_Ignore`, `ECR_Overlap`, `ECR_Block`. `ECollisionEnabled`: `NoCollision`, `QueryOnly`,
  `PhysicsOnly`, `QueryAndPhysics`, `ProbeOnly`, `QueryAndProbe`. `[V PY:CollisionResponseType, PY:CollisionEnabled]`
- On a component `[V PY:PrimitiveComponent]`: `SetCollisionProfileName(FName, bool bUpdateOverlaps = true)`,
  `SetCollisionEnabled(ECollisionEnabled::Type)`, `SetCollisionObjectType(ECollisionChannel)`,
  `SetCollisionResponseToChannel(ECollisionChannel, ECollisionResponse)`, `SetCollisionResponseToAllChannels(ECollisionResponse)`,
  `SetSimulatePhysics(bool)`, `AddImpulse(FVector, FName BoneName = NAME_None, bool bVelChange = false)`,
  `GetOverlappingActors(...)`, property `generate_overlap_events` (C++ `SetGenerateOverlapEvents(bool)` `[M]`).
- Naming a custom channel and profile in `DefaultEngine.ini` `[M]`:

  ```ini
  [/Script/Engine.CollisionProfile]
  +DefaultChannelResponses=(Channel=ECC_GameTraceChannel1,DefaultResponse=ECR_Block,bTraceType=True,bStaticObject=False,Name="Weapon")
  +DefaultChannelResponses=(Channel=ECC_GameTraceChannel2,DefaultResponse=ECR_Ignore,bTraceType=False,bStaticObject=False,Name="PlayerOnly")
  ```

- Surface types for impacts and footsteps: `UPhysicalMaterial::SurfaceType` (`EPhysicalSurface`), project list in
  `[/Script/Engine.PhysicsSettings]` property `physical_surfaces`, `UGameplayStatics::GetSurfaceType(const FHitResult&)`. `[V PY:PhysicalMaterial, PY:PhysicsSettings, PY:GameplayStatics]`
  Entry format `+PhysicalSurfaces=(Type=SurfaceType1,Name="Asphalt")` `[M]`.

### 4.6 Damage

Verified, parameter order as listed `[V PY:GameplayStatics]`:

- `UGameplayStatics::ApplyDamage(DamagedActor, BaseDamage, EventInstigator, DamageCauser, DamageTypeClass)` returns float
- `UGameplayStatics::ApplyPointDamage(DamagedActor, BaseDamage, HitFromDirection, HitInfo, EventInstigator, DamageCauser, DamageTypeClass)` returns float
- `UGameplayStatics::ApplyRadialDamage(WorldContextObject, BaseDamage, Origin, DamageRadius, DamageTypeClass, IgnoreActors, DamageCauser = nullptr, InstigatedByController = nullptr, bDoFullDamage = false, DamagePreventionChannel = ECC_Visibility)` returns bool
- `UGameplayStatics::ApplyRadialDamageWithFalloff(WorldContextObject, BaseDamage, MinimumDamage, Origin, DamageInnerRadius, DamageOuterRadius, DamageFalloff, DamageTypeClass, IgnoreActors, DamageCauser = nullptr, InstigatedByController = nullptr, DamagePreventionChannel = ECC_Visibility)` returns bool
- Actor: `bCanBeDamaged` ("Must be true for damage events ... to be called"), delegates `OnTakeAnyDamage`,
  `OnTakePointDamage`, `OnTakeRadialDamage`. `[V PY:Actor]`
- Structs `FDamageEvent`, `FPointDamageEvent`, `FRadialDamageEvent`, `FRadialDamageParams` are in `DamageEvents.h`,
  module Engine. `[V PY:DamageEvent, PY:PointDamageEvent, PY:RadialDamageEvent, PY:RadialDamageParams]`

Native override `[M]`:

```cpp
#include "Engine/DamageEvents.h"
virtual float TakeDamage(float DamageAmount, struct FDamageEvent const& DamageEvent,
                         class AController* EventInstigator, AActor* DamageCauser) override;
// inside:
if (DamageEvent.IsOfType(FPointDamageEvent::ClassID))
{
    const FPointDamageEvent& Point = static_cast<const FPointDamageEvent&>(DamageEvent);
    const FName Bone = Point.HitInfo.BoneName;      // head multiplier
}
```

### 4.7 AI: controller, movement, navigation, senses

- `AAIController` `[V PY:AIController]`:
  `MoveToActor(AActor* Goal, float AcceptanceRadius = -1, bool bStopOnOverlap = true, bool bUsePathfinding = true, bool bCanStrafe = true, TSubclassOf<UNavigationQueryFilter> FilterClass = nullptr, bool bAllowPartialPath = true)`,
  `MoveToLocation(const FVector& Dest, float AcceptanceRadius = -1, bool bStopOnOverlap = true, bool bUsePathfinding = true, bool bProjectDestinationToNavigation = false, bool bCanStrafe = true, TSubclassOf<UNavigationQueryFilter> FilterClass = nullptr, bool bAllowPartialPath = true)`,
  both returning `EPathFollowingRequestResult` (`Failed` 0, `AlreadyAtGoal` 1, `RequestSuccessful` 2 `[V PY:PathFollowingRequestResult]`).
  Also `SetFocus(AActor*)`, `SetFocalPoint(FVector)`, `ClearFocus(...)`, `GetMoveStatus()`,
  `GetPathFollowingComponent()`, `GetAIPerceptionComponent()`, `RunBehaviorTree(UBehaviorTree*)`,
  `SetMoveBlockDetection(bool)`. "AcceptanceRadius has default value or -1 due to Header Parser not being able to
  recognize UPathFollowingComponent::DefaultAcceptanceRadius".
- `EPathFollowingResult`: `Success` 0, `Blocked` 1, `OffPath` 2, `Aborted` 3, `Invalid` 5. `[V PY:PathFollowingResult]`
  Completion callback `virtual void OnMoveCompleted(FAIRequestID RequestID, const FPathFollowingResult& Result) override;` `[M]`
- Stop a move: `StopMovement()` on the controller `[M]`.
- Possession: on the pawn set `AIControllerClass` and `AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned`
  (property names `[V PY:Character]`, enum value spelling `[M]`).
- `UNavigationSystemV1` `[V PY:NavigationSystemV1]`: static `get_navigation_system(world_context_object)`,
  `get_random_reachable_point_in_radius(world_context_object, origin, radius, nav_data=None, filter_class=None)`,
  `project_point_to_navigation(world_context_object, point, nav_data, filter_class, query_extent)`,
  `find_path_to_location_synchronously(world_context_object, path_start, path_end, pathfinding_context=None, filter_class=None)`,
  `get_path_length(...)`, `navigation_raycast(...)`, `is_navigation_being_built(world_context_object)`.
  `GetRandomPointInNavigableRadius` is deprecated in favour of `GetRandomLocationInNavigableRadius`.
  In C++ `[M]`: `UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());`
  `bool Nav->GetRandomReachablePointInRadius(const FVector& Origin, float Radius, FNavLocation& Result)`,
  `bool Nav->ProjectPointToNavigation(const FVector& Point, FNavLocation& OutLocation, const FVector& Extent)`;
  the reflected Blueprint versions of the two point queries carry a `K2_` prefix.
- Flying enemies do not use the navmesh: move them yourself (`MOVE_Flying` or a plain actor).
- `UPawnSensingComponent` `[V PY:PawnSensingComponent]`: `SightRadius`, `SensingInterval`, `bOnlySensePlayers`
  ("Default: true"), `bSeePawns`, `bHearNoises`, `HearingThreshold`, `LOSHearingThreshold`, `HearingMaxSoundAge`,
  `bEnableSensingUpdates`, `SetPeripheralVisionAngle(float)`, `SetSensingInterval(float)`,
  `SetSensingUpdatesEnabled(bool)`; delegates `OnSeePawn`, `OnHearNoise` (handlers `void F(APawn* Pawn)` and
  `void F(APawn* Instigator, const FVector& Location, float Volume)`, both `UFUNCTION()` `[M]`). Noise comes from
  `APawn::PawnMakeNoise` / `AActor::MakeNoise(Loudness, NoiseInstigator, NoiseLocation, MaxRange, Tag)`. `[V PY:Pawn, PY:Actor]`
- `UAIPerceptionComponent` `[V PY:AIPerceptionComponent]`: `senses_config`, `dominant_sense`, delegates
  `OnPerceptionUpdated`, `OnTargetPerceptionUpdated`, `OnTargetPerceptionInfoUpdated`, `OnTargetPerceptionForgotten`;
  functions `GetCurrentlyPerceivedActors(SenseToUse, OutActors)`, `GetKnownPerceivedActors`,
  `GetPerceivedHostileActors`, `GetActorsPerception`, `SetSenseEnabled(SenseClass, bEnable)`, `ForgetAll()`,
  `RequestStimuliListenerUpdate()`. Native setup `ConfigureSense(*Config)`, `SetDominantSense(...)` `[M]`.
- `UAISenseConfig_Sight` `[V PY:AISenseConfig_Sight]`: `SightRadius`, `LoseSightRadius`,
  `PeripheralVisionAngleDegrees` ("the angle measured in relation to the forward vector, not the whole range"),
  `DetectionByAffiliation` (`bDetectEnemies`, `bDetectNeutrals`, `bDetectFriendlies` `[V PY:AISenseAffiliationFilter]`),
  `AutoSuccessRangeFromLastSeenLocation`, `PointOfViewBackwardOffset`, `NearClippingRadius`, `MaxAge`.
  Without team ids every actor is neutral, so `bDetectNeutrals` must be true `[M]`.
- `UAISenseConfig_Hearing`: `HearingRange`, `DetectionByAffiliation`, `MaxAge`. `[V PY:AISenseConfig_Hearing]`
  Events: `UAISense_Hearing::ReportNoiseEvent(WorldContextObject, NoiseLocation, Loudness = 1, Instigator = nullptr, MaxRange = 0, Tag = NAME_None)`,
  `UAISense_Damage::ReportDamageEvent(WorldContextObject, DamagedActor, Instigator, DamageAmount, EventLocation, HitLocation, Tag = NAME_None)`. `[V PY:AISense_Hearing, PY:AISense_Damage]`
- `FAIStimulus`: `Strength`, `StimulusLocation`, `ReceiverLocation`, `Tag`, `Age`, `ExpirationAge`, and
  `successfully_sensed` (C++ `WasSuccessfullySensed()` `[M]`). `[V PY:AIStimulus]`
- `UAIPerceptionStimuliSourceComponent`: `bAutoRegisterAsSource`, `RegisterAsSourceForSenses`,
  `RegisterForSense(SenseClass)`, `RegisterWithPerceptionSystem()`. `[V PY:AIPerceptionStimuliSourceComponent]`

### 4.8 Timers

- Reflected form in `UKismetSystemLibrary`, as the reference lists it:
  `set_timer(object, function_name, time, looping, max_once_per_frame=False, initial_start_delay=0.0, initial_start_delay_variance=0.0)`
  returning a `TimerHandle`, `set_timer_delegate(delegate, time, looping, ...)`, `set_timer_for_next_tick(object, function_name)`,
  `clear_timer_handle(world_context_object, handle)`, `clear_timer(object, function_name)`; `clear_timer_delegate`
  is deprecated ("Use Clear Timer by Handle"). `[V PY:SystemLibrary]` The C++ names carry a `K2_` prefix `[M]`.
- Native `[M]`: `#include "TimerManager.h"`;
  `FTimerHandle Handle; GetWorldTimerManager().SetTimer(Handle, this, &AMyActor::Fire, Rate, /*bLoop*/ true, /*FirstDelay*/ 0.f);`
  `GetWorldTimerManager().ClearTimer(Handle);` `GetWorldTimerManager().SetTimerForNextTick(this, &AMyActor::F);`
  with a lambda: `SetTimer(Handle, FTimerDelegate::CreateWeakLambda(this, [this]{ ... }), Rate, false);`
- Time: `UGameplayStatics::GetTimeSeconds`, `GetRealTimeSeconds`, `GetWorldDeltaSeconds`,
  `SetGlobalTimeDilation(WorldContextObject, TimeDilation)`, `SetGamePaused(WorldContextObject, bPaused)`,
  `IsGamePaused`. `[V PY:GameplayStatics]`

### 4.9 UMG in C++ and Slate

Verified function names `[V PY:Widget, PY:UserWidget, PY:PanelWidget, PY:CanvasPanel, PY:CanvasPanelSlot, PY:Overlay, PY:OverlaySlot, PY:HorizontalBox, PY:VerticalBox, PY:TextBlock, PY:ProgressBar, PY:Image, PY:Border, PY:SizeBox, PY:WidgetLibrary, PY:WidgetLayoutLibrary, PY:GameViewportSubsystem, PY:SlateVisibility, PY:TextJustify, PY:TextLayoutWidget]`:

- `UWidget` (base of everything): `SetVisibility(ESlateVisibility)` with `Visible`, `Collapsed`, `Hidden`,
  `HitTestInvisible`, `SelfHitTestInvisible`; `RemoveFromParent()`, `SetRenderOpacity(float)`, `SetIsEnabled(bool)`,
  `SetRenderTransform`, `SetRenderScale`, `SetRenderTranslation`, `IsVisible()`, `GetDesiredSize()`,
  `GetCachedGeometry()`, `ForceLayoutPrepass()`.
- `UUserWidget`: `AddToViewport(int32 ZOrder = 0)`, `AddToPlayerScreen(int32 ZOrder = 0)` (`RemoveFromViewport` is
  deprecated: "Use RemoveFromParent instead"), `SetPositionInViewport(FVector2D, bool bRemoveDPIScale = true)`,
  `SetDesiredSizeInViewport`, `SetAnchorsInViewport`, `SetAlignmentInViewport`, `SetOwningPlayer`,
  `PlayAnimation(...)`; overridable events `on_initialized`, `pre_construct`, `construct`, `destruct`, `tick`,
  `on_paint`, `on_key_down`, `on_mouse_button_down` (C++ `NativeOnInitialized`, `NativePreConstruct`,
  `NativeConstruct`, `NativeDestruct`, `NativeTick(const FGeometry&, float)`, `NativePaint` `[M]`).
- `UPanelWidget`: `AddChild(UWidget*)`, `ClearChildren()`, `RemoveChild`, `GetChildAt`, `GetChildrenCount`.
- `UCanvasPanel::AddChildToCanvas(UWidget*)` returns `UCanvasPanelSlot*`; slot: `SetAnchors(FAnchors)`,
  `SetAlignment(FVector2D)`, `SetPosition(FVector2D)`, `SetSize(FVector2D)`, `SetAutoSize(bool)`, `SetOffsets(FMargin)`,
  `SetZOrder(int32)`, `SetLayout(FAnchorData)`.
- `UOverlay::AddChildToOverlay`, `UHorizontalBox::AddChildToHorizontalBox`, `UVerticalBox::AddChildToVerticalBox`;
  slots: `SetPadding(FMargin)`, `SetHorizontalAlignment`, `SetVerticalAlignment`, `SetSize` (box slots).
- `UTextBlock`: `SetText(FText)`, `SetColorAndOpacity(FSlateColor)`, `SetFont(FSlateFontInfo)`, `SetOpacity(float)`,
  `SetShadowOffset`, `SetShadowColorAndOpacity`, `SetAutoWrapText`, `SetTextTransformPolicy`, `SetFontSize`.
  Justification belongs to the base class `UTextLayoutWidget` (File `TextWidgetTypes.h`), enum `ETextJustify`:
  `Left`, `Center`, `Right`, `InvariantLeft`, `InvariantRight`; the setter `SetJustification(...)` is `[M]`.
- `UProgressBar`: `SetPercent(float)`, `SetFillColorAndOpacity(FLinearColor)`.
- `UImage`: `SetBrushFromTexture(UTexture2D*, bool bMatchSize = false)`, `SetBrushFromMaterial(UMaterialInterface*)`,
  `SetColorAndOpacity(FLinearColor)`, `SetOpacity(float)`, `SetBrush(const FSlateBrush&)`, `SetDesiredSizeOverride(FVector2D)`,
  `GetDynamicMaterial()`.
- `UBorder`: `SetBrushColor(FLinearColor)`, `SetPadding(FMargin)`, `SetContentColorAndOpacity`, `SetBrushFromTexture`.
- `USizeBox`: `SetWidthOverride`, `SetHeightOverride`, `SetMinDesiredWidth`, ...
- `UWidgetBlueprintLibrary` (Python `WidgetLibrary`): `set_input_mode_game_only(player_controller, flush_input=False)`,
  `set_input_mode_ui_only_ex(player_controller, widget_to_focus=None, mouse_lock_mode=DO_NOT_LOCK, flush_input=False)`,
  `set_input_mode_game_and_ui_ex(player_controller, widget_to_focus=None, mouse_lock_mode=DO_NOT_LOCK, hide_cursor_during_capture=True, flush_input=False)`,
  `get_all_widgets_of_class`, `draw_line`, `draw_box`, `draw_text` (for `on_paint`). C++ spellings
  `SetInputMode_GameOnly`, `SetInputMode_UIOnlyEx`, `SetInputMode_GameAndUIEx` and the native alternative
  `PlayerController->SetInputMode(FInputModeGameOnly())` / `FInputModeUIOnly` / `FInputModeGameAndUI` are `[M]`.
- `UWidgetLayoutLibrary`: `GetViewportSize`, `GetViewportScale`, `ProjectWorldLocationToWidgetPosition(PlayerController, WorldLocation, OutScreenPosition, bPlayerViewportRelative)`,
  `RemoveAllWidgets`. `UGameplayStatics::ProjectWorldToScreen(Player, WorldPosition, OutScreenPosition, bPlayerViewportRelative = false)`. `[V PY:GameplayStatics]`
- `FSlateFontInfo` fields: `FontObject`, `TypefaceFontName`, `Size` ("The font size is a measure in point values. The
  conversion of points to Slate Units is done at 96 DPI."), `LetterSpacing`, `OutlineSettings`, `SkewAmount`. `[V PY:SlateFontInfo]`
- `PlayerController`: `bShowMouseCursor`, `GetHUD()`, `SetViewTargetWithBlend(...)`,
  `ClientStartCameraShake(Shake, Scale = 1, PlaySpace = CameraLocal, UserPlaySpaceRot)`, `GetViewportSize`,
  `ProjectWorldLocationToScreen`. `[V PY:PlayerController]`

Building a widget tree with no Blueprint `[M]`:

```cpp
// UMIHudWidget : public UUserWidget
virtual TSharedRef<SWidget> RebuildWidget() override
{
    if (WidgetTree && !WidgetTree->RootWidget)
    {
        UCanvasPanel* Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("Root"));
        WidgetTree->RootWidget = Root;
        UTextBlock* Hp = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("Hp"));
        UCanvasPanelSlot* HpSlot = Root->AddChildToCanvas(Hp);
        HpSlot->SetAnchors(FAnchors(0.5f, 1.0f)); HpSlot->SetAlignment(FVector2D(0.5, 1.0)); HpSlot->SetAutoSize(true);
    }
    return Super::RebuildWidget();
}
// create: UMIHudWidget* W = CreateWidget<UMIHudWidget>(PlayerController, UMIHudWidget::StaticClass()); W->AddToViewport(0);
```

Do not name a local variable `Slot` inside a widget class: `UWidget` has a member `Slot`, and Unreal builds treat a
local that hides a member as an error `[M]`. The same goes for locals named like any inherited member (`Owner`,
`Instigator`, `Tags`, `RootComponent` in actors).

Slate alone `[M]`: `class SMIHud : public SCompoundWidget { SLATE_BEGIN_ARGS(SMIHud) {} SLATE_END_ARGS() void Construct(const FArguments&); };`
add with `GEngine->GameViewport->AddViewportWidgetContent(SNew(SWeakWidget).PossiblyNullContent(Hud.ToSharedRef()), ZOrder);`
remove with `RemoveViewportWidgetContent(...)`. Custom drawing (minimap, crosshair, damage arcs) in
`virtual int32 OnPaint(const FPaintArgs&, const FGeometry&, const FSlateRect&, FSlateWindowElementList&, int32 LayerId, const FWidgetStyle&, bool) const override`
with `FSlateDrawElement::MakeLines`, `MakeBox`, `MakeText`. A built-in font without assets:
`FCoreStyle::GetDefaultFontStyle("Bold", 24)`.

### 4.10 `UGameUserSettings`

`[V PY:GameUserSettings, PY:WindowMode]`: `UGameUserSettings::GetGameUserSettings()` (static),
`ApplySettings(bool bCheckForCommandLineOverrides)`, `ApplyResolutionSettings(bool)`, `ApplyNonResolutionSettings()`,
`SaveSettings()`, `LoadSettings(bool bForceReload = false)`, `SetToDefaults()`, `ValidateSettings()`,
`SetOverallScalabilityLevel(int32)` / `GetOverallScalabilityLevel()`, `SetScreenResolution(FIntPoint)`,
`GetDesktopResolution()`, `SetFullscreenMode(EWindowMode::Type)` (`Fullscreen`, `WindowedFullscreen`, `Windowed`),
`SetVSyncEnabled(bool)`, `SetFrameRateLimit(float)`, `SetResolutionScaleNormalized(float)`,
`SetDynamicResolutionEnabled(bool)`, and per-group setters `SetViewDistanceQuality`, `SetAntiAliasingQuality`,
`SetShadowQuality`, `SetGlobalIlluminationQuality`, `SetReflectionQuality`, `SetPostProcessingQuality`,
`SetTextureQuality`, `SetVisualEffectQuality`, `SetFoliageQuality`, `SetShadingQuality`, `SetAudioQualityLevel`,
`RunHardwareBenchmark(...)`, `ApplyHardwareBenchmarkResults()`.

A project subclass is registered with `[/Script/Engine.Engine] GameUserSettingsClassName=/Script/MurderInc.MIGameUserSettings`
and stores `UPROPERTY(config)` members in `GameUserSettings.ini` `[M]`. Quality levels run 0 (low) to 3 (epic), 4 is
cinematic `[M]`.

### 4.11 `USaveGame`

`[V PY:GameplayStatics, PY:SaveGame, PY:LocalPlayerSaveGame]`: `UGameplayStatics::CreateSaveGameObject(TSubclassOf<USaveGame>)`,
`SaveGameToSlot(USaveGame*, const FString& SlotName, int32 UserIndex)` returns bool,
`LoadGameFromSlot(SlotName, UserIndex)` returns `USaveGame*`, `DoesSaveGameExist(SlotName, UserIndex)`; asynchronous
variants and `DeleteGameInSlot` exist `[M]`. Members to save are `UPROPERTY()` fields of the subclass `[M]`. Files go
to `<Project>/Saved/SaveGames/<Slot>.sav` `[M]`. `ULocalPlayerSaveGame` adds
`LoadOrCreateSaveGameForLocalPlayer(SaveGameClass, LocalPlayerController, SlotName)`, `SaveGameToSlotForLocalPlayer()`.

### 4.12 Niagara from C++

`[V PY:NiagaraFunctionLibrary, PY:NiagaraComponent, PY:NCPoolMethod]`:

- `UNiagaraFunctionLibrary::SpawnSystemAtLocation(WorldContextObject, SystemTemplate, Location, Rotation = FRotator::ZeroRotator, Scale = FVector(1), bAutoDestroy = true, bAutoActivate = true, PoolingMethod = ENCPoolMethod::None, bPreCullCheck = true)` returns `UNiagaraComponent*`
- `UNiagaraFunctionLibrary::SpawnSystemAttached(SystemTemplate, AttachToComponent, AttachPointName, Location, Rotation, LocationType, bAutoDestroy, bAutoActivate = true, PoolingMethod = ENCPoolMethod::None, bPreCullCheck = true)`
- `ENCPoolMethod`: `None`, `AutoRelease`, `ManualRelease`
- `UNiagaraComponent`: `SetVariableFloat(FName, float)`, `SetVariableVec3(FName, FVector)`,
  `SetVariableLinearColor(FName, const FLinearColor&)`, `SetVariableInt`, `SetVariableBool`, `SetVariablePosition`,
  `SetAsset(UNiagaraSystem*, bool bResetExistingOverrideParameters = true)`, `ResetSystem()`, `ReinitializeSystem()`,
  `SetPaused(bool)`, `SetAutoDestroy(bool)`; activation through `Activate(bool bReset)` / `Deactivate()` of the base
  component `[M]`.
- Module `Niagara`, plugin `Niagara`. A system is an asset; load it with
  `LoadObject<UNiagaraSystem>(nullptr, TEXT("/Game/VFX/NS_X.NS_X"))` `[M]`. See 3.6 on authoring.
- Old particle systems: `UGameplayStatics::SpawnEmitterAtLocation(WorldContextObject, EmitterTemplate, Location, Rotation, Scale, bAutoDestroy, PoolingMethod, bAutoActivateSystem)`.
  Decals: `UGameplayStatics::SpawnDecalAtLocation(WorldContextObject, DecalMaterial, DecalSize, Location, Rotation, LifeSpan = 0)`
  and `SpawnDecalAttached(DecalMaterial, DecalSize, AttachToComponent, AttachPointName, Location, Rotation, LocationType, LifeSpan)`.
  The reference prints the default rotation as `[0.000000, -90.000000, 0.000000]`, which in Python's roll, pitch, yaw
  order is pitch -90 (facing down); pass the rotation explicitly. `[V PY:GameplayStatics]`

### 4.13 Audio

Playback `[V PY:GameplayStatics]`:

- `UGameplayStatics::PlaySoundAtLocation(WorldContextObject, Sound, Location, Rotation, VolumeMultiplier = 1, PitchMultiplier = 1, StartTime = 0, AttenuationSettings = nullptr, ConcurrencySettings = nullptr, OwningActor = nullptr, InitialParams = nullptr)`
- `PlaySound2D(WorldContextObject, Sound, VolumeMultiplier = 1, PitchMultiplier = 1, StartTime = 0, ConcurrencySettings = nullptr, OwningActor = nullptr, bIsUISound = true)`
- `SpawnSoundAtLocation(WorldContextObject, Sound, Location, Rotation, VolumeMultiplier, PitchMultiplier, StartTime, AttenuationSettings, ConcurrencySettings, bAutoDestroy = true)` returns `UAudioComponent*`
- `SpawnSoundAttached(Sound, AttachToComponent, AttachPointName = NAME_None, Location, Rotation, LocationType = KeepRelativeOffset, bStopWhenAttachedToDestroyed = false, VolumeMultiplier, PitchMultiplier, StartTime, AttenuationSettings, ConcurrencySettings, bAutoDestroy)`
- `SpawnSound2D(...)` and `CreateSound2D(WorldContextObject, Sound, VolumeMultiplier, PitchMultiplier, StartTime, ConcurrencySettings, bPersistAcrossLevelTransition = false, bAutoDestroy = true)`
- Mix control: `SetBaseSoundMix`, `PushSoundMixModifier`, `PopSoundMixModifier`, `ClearSoundMixModifiers`,
  `SetSoundMixClassOverride(WorldContextObject, SoundMixModifier, SoundClass, Volume = 1, Pitch = 1, FadeInTime = 1, bApplyToChildren = true)`,
  `ClearSoundMixClassOverride`, `SetGlobalPitchModulation`, `ActivateReverbEffect(WorldContextObject, ReverbEffect, TagName, Priority = 0, Volume = 0.5, FadeTime = 2)`,
  `DeactivateReverbEffect`, `PrimeSound(USoundBase*)`.

`UAudioComponent` `[V PY:AudioComponent]`: `Play(float StartTime = 0)`, `Stop()`, `StopDelayed(float)`,
`SetPaused(bool)`, `IsPlaying()`, `FadeIn(FadeInDuration, FadeVolumeLevel = 1, StartTime = 0, FadeCurve)`,
`FadeOut(FadeOutDuration, FadeVolumeLevel, FadeCurve)`, `AdjustVolume(AdjustVolumeDuration, AdjustVolumeLevel, FadeCurve)`,
`SetSound(USoundBase*)`, `SetVolumeMultiplier(float)`, `SetPitchMultiplier(float)`,
`SetLowPassFilterEnabled(bool)`, `SetLowPassFilterFrequency(float)`, `SetSubmixSend(USoundSubmixBase*, float SendLevel)`,
`AdjustAttenuation(const FSoundAttenuationSettings&)`, `SetUISound(bool)`, `SetFloatParameter(FName, float)`,
`PlayQuantized(...)`; properties `Sound`, `AttenuationSettings` (asset), `bOverrideAttenuation`,
`AttenuationOverrides` (struct), `bAllowSpatialization`, `VolumeMultiplier`, `PitchMultiplier`, `bIsUISound`,
`SoundClassOverride`, `ConcurrencySet`, `bAutoActivate`.

Attenuation `[V PY:SoundAttenuation, PY:SoundAttenuationSettings, PY:AttenuationDistanceModel, PY:AttenuationShape]`:
`USoundAttenuation::Attenuation` is an `FSoundAttenuationSettings` with `bAttenuate`, `bSpatialize`,
`DistanceAlgorithm` (`EAttenuationDistanceModel`: `Linear`, `Logarithmic`, `Inverse`, `LogReverse`, `NaturalSound`,
`Custom`), `AttenuationShape` (`Sphere`, `Capsule`, `Box`, `Cone`), `AttenuationShapeExtents` (for a sphere, X is the
inner radius `[M]`), `FalloffDistance`, `dBAttenuationAtMax`, `bAttenuateWithLPF`, `bEnableOcclusion`,
`bEnableReverbSend`, `SpatializationAlgorithm`, `StereoSpread`, `BinauralRadius`, `CustomAttenuationCurve`.

Routing `[V PY:SoundBase, PY:SoundSubmix, PY:AudioMixerLibrary]`: on a sound `SoundClassObject`, `SoundSubmixObject`
("Submix to route sound output to. If unset, falls back to referenced SoundClass submix."), `SoundSubmixSends`,
`AttenuationSettings`, `ConcurrencySet`, `Priority`, `VirtualizationMode`. On a `USoundSubmix`:
`SetSubmixOutputVolume(WorldContextObject, float)`, `SetSubmixWetLevel`, `SetSubmixDryLevel`,
`SubmixEffectChain`, `StartEnvelopeFollowing`, `AddEnvelopeFollowerDelegate`. Library
`UAudioMixerBlueprintLibrary`: `AddSubmixEffect(WorldContextObject, SoundSubmix, SubmixEffectPreset)`,
`RemoveSubmixEffect`, `ClearSubmixEffects`, `AddMasterSubmixEffect`, `SetSubmixEffectChainOverride(WorldContextObject, SoundSubmix, SubmixEffectPresetChain, FadeTimeSec)`,
`PrimeSoundForPlayback(SoundWave, OnLoadCompletion)`.

`USoundWave`: `bLooping` ("when played directly (not through a sound cue) the wave will be played looping"),
`Volume`, `Pitch`, `SoundGroup`, `LoadingBehavior`. `[V PY:SoundWave]` Runtime-generated audio classes that exist:
`USoundWaveProcedural`, `USynthComponent`, MetaSounds (`UMetaSoundSource`, plugin `Metasound`, module
`MetasoundEngine`). `[V PY:SoundWaveProcedural, PY:SynthComponent, PY:MetaSoundSource]`

### 4.14 Reading a JSON file at run time and staging it

Reading `[M]`:

```cpp
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

FString Text;
const FString Path = FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Data"), TEXT("level.json"));
if (FFileHelper::LoadFileToString(Text, *Path))
{
    TSharedPtr<FJsonObject> Root;
    const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
    if (FJsonSerializer::Deserialize(Reader, Root) && Root.IsValid())
    {
        double Number = 0.0;   Root->TryGetNumberField(TEXT("radius"), Number);
        FString Name;          Root->TryGetStringField(TEXT("name"), Name);
        bool bFlag = false;    Root->TryGetBoolField(TEXT("solid"), bFlag);
        const TArray<TSharedPtr<FJsonValue>>* Items = nullptr;
        if (Root->TryGetArrayField(TEXT("items"), Items))
            for (const TSharedPtr<FJsonValue>& V : *Items)
                if (const TSharedPtr<FJsonObject> Obj = V->AsObject()) { /* ... */ }
        const TSharedPtr<FJsonObject>* Child = nullptr; Root->TryGetObjectField(TEXT("player"), Child);
    }
}
```

Modules `Json` (and `JsonUtilities` for `FJsonObjectConverter::JsonObjectStringToUStruct`, header
`JsonObjectConverter.h`). Use the exact key spelling of the JSON file; do not rely on case-insensitive lookup.
`UKismetSystemLibrary::GetProjectContentDirectory()` exists for Blueprint and Python. `[V PY:SystemLibrary]`

Staging: "Additional Non-Asset Directories to Package (Copy)" is `DirectoriesToAlwaysStageAsUFS` /
`DirectoriesToAlwaysStageAsNonUFS`, **paths relative to the project's `Content` directory**, and everything except
`.uasset` and `.umap` in them is staged. `[V F:2717162/2]` (the answer in an Epic support thread, in Japanese)
In `Config/DefaultGame.ini`:

```ini
[/Script/UnrealEd.ProjectPackagingSettings]
+DirectoriesToAlwaysStageAsNonUFS=(Path="Data")
```

Section and syntax `[M+ F:428070/8]`. "NonUFS" copies loose files next to the pak (readable with `FFileHelper` at
`FPaths::ProjectContentDir()/Data`); "UFS" puts them in the pak, which `FFileHelper` also reads `[M]`. An alternative
named by the same answer is `RuntimeDependencies` in `Build.cs`.

### 4.15 Automation tests

- Spec form, from Epic's toolset guide `[V LP:create-toolset]`:

  ```cpp
  BEGIN_DEFINE_SPEC(FMIDamageSpec, "MurderInc.Damage",
      EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)
  END_DEFINE_SPEC(FMIDamageSpec)

  void FMIDamageSpec::Define()
  {
      Describe("Headshot", [this]()
      {
          It("multiplies by 2.2", [this]() { TestTrue(TEXT("scaled"), true); });
      });
  }
  ```

  with `TestTrue`, `TestFalse`, `AddExpectedError(TEXT("..."))` used there.
- Simple form `[M]`: `#include "Misc/AutomationTest.h"`, wrap in `#if WITH_DEV_AUTOMATION_TESTS`,
  `IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMIFooTest, "MurderInc.Foo", EAutomationTestFlags::EditorContext | EAutomationTestFlags::ProductFilter)`
  and `bool FMIFooTest::RunTest(const FString& Parameters) { TestEqual(TEXT("x"), A, B); return true; }`. Use exactly
  that pair of flags: other flag spellings changed between 5.x versions `[M]`.
- Headless run, from the same guide `[V LP:create-toolset]`:
  `UnrealEditor-Cmd.exe <Project>.uproject -ExecCmds="Automation RunTests AI.MyToolset;quit" -Unattended -NullRHI`
  (it "launches a headless editor instance, runs the specified tests, and exits", about 30 s of start-up).
- A 2026 Linux CI line adds a report and an exit condition `[M+ F:2763115]`:
  `UnrealEditor "<uproject>" -execcmds="Automation RunTests <Filter>;Quit" -stdout -unattended -NOSPLASH -AllowStdOutLogVerbosity -NullRHI -ReportExportPath="<dir>" -AbsLog="<file>" -TestExit="Automation Test Queue Empty"`.
  The report directory receives JSON.
- In a running editor the MCP toolset `AutomationTestToolset` offers `DiscoverTests`, `ListTests`, `RunTests`,
  `GetTestStatus`, `GetTestResults`, and `LiveCodingToolset.CompileLiveCoding` compiles C++ and returns the compiler
  diagnostics. `[V LP:create-toolset]` (neither class is in the 5.8 Python reference)
- Python tests can be registered with `unreal.PythonTestRunner.create(base_name, search_options, timeout_in_seconds=5.0)`
  (plugin `ToolsetRegistry`). `[V PY:PythonTestRunner]` Functional tests: `AFunctionalTest`, module
  `FunctionalTesting`. `[V PY:FunctionalTest]`

### 4.16 Building from the command line

All `[M]`, with the forum lines that show the same shape.

Windows:

```bat
"%UE%\Engine\Build\BatchFiles\Build.bat" MurderIncEditor Win64 Development -Project="%CD%\MurderInc.uproject" -WaitMutex
"%UE%\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun -project="%CD%\MurderInc.uproject" -noP4 -platform=Win64 ^
  -clientconfig=Shipping -build -cook -stage -pak -archive -archivedirectory="%CD%\Build" -utf8output
```

A 2025 user's working line: `RunUAT.bat BuildCookRun -project=... -noP4 -build -cook -pak -prereqs -CrashReporter -utf8output -targetplatform=Win64 -clientconfig=Shipping -stage -archive -archivedirectory=...`. `[M+ F:2577252/14]`

Linux:

```sh
"$UE/Engine/Build/BatchFiles/Linux/Build.sh" MurderIncEditor Linux Development -Project="$PWD/MurderInc.uproject" -WaitMutex
"$UE/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun -project="$PWD/MurderInc.uproject" -noP4 -platform=Linux \
  -clientconfig=Development -build -cook -stage -pak -archive -archivedirectory="$PWD/Build"
```

`Build.sh` runs `dotnet Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll <Target> Linux Development <uproject> -waitmutex`. `[M+ F:1985382]`
A support-style reply gives `Engine/Build/BatchFiles/RunUAT.sh BuildCookRun -project=MyProject.uproject -clientconfig=Development`. `[M+ F:463127/2]`

Things to know before the first build:

- **Reported on 5.8.4 launcher installs (2026-10-29):** after the Fab plugin updated itself to 0.0.22, every C++
  project build stops with `Expecting to find a type to be declared in a module rules named 'FabToolset'` /
  `Result: Failed (RulesError)`. Reported workarounds: add `-DisablePlugin=Fab` to the UnrealBuildTool line, or remove
  the `FabToolset` module entry from `Engine/Plugins/Fab/Fab.uplugin`. `[M+ F:2846816]` Not confirmed by Epic in that topic.
- 5.8.4 recognises the `.slnx` solution format of Visual Studio 2026. `[V F:2842775]` Required compiler and SDK
  versions for 5.8 were not verified.
- Linux editor downloads: `https://www.unrealengine.com/linux` (named in every Epic release post `[V F:2729274]`; the
  page itself could not be opened). Container images `ghcr.io/epicgames/unreal-engine:dev-slim-<version>` need a
  GitHub account linked to Epic. `[M+ F:2763115]`

---

## 5. Art pipeline

### 5.1 Axes and scale, Blender to Unreal

Measured with Blender 5.3.0 (`BL:run`, Appendix A.1). A point at Blender `(x, y, z)` in metres:

| Route | What the file holds | Evidence |
|---|---|---|
| glTF/GLB, `export_yup=True` (the default) | position `(x, z, -y)` in metres. Blender `(1, 2, 3)` became `(1, 3, -2)`; the object location `(10, 20, 30)` became node translation `[10, 30, -20]`; normal `(0, 0, 1)` became `(0, 1, 0)`; triangle order kept | `[V BL:run]`; "Y Up: Export using glTF convention, +Y up." `[V BL:gltf]` |
| glTF UVs | `(u, 1 - v)`: glTF's origin is the top-left corner | `[V BL:run]` |
| FBX, default options (`axis_forward='-Z'`, `axis_up='Y'`, `apply_scale_options='FBX_SCALE_NONE'`, `apply_unit_scale=True`, `bake_space_transform=False`) | header: `UpAxis=1` (Y), `FrontAxis=2` (Z), `CoordAxis=0` (X), `UnitScaleFactor=1.0` (centimetres); mesh vertices unchanged `(1, 2, 3)`; the object carries `Lcl Rotation (-90, 0, 0)` and **`Lcl Scaling (100, 100, 100)`** | `[V BL:run]` |
| FBX, `apply_scale_options='FBX_SCALE_UNITS'` | `UnitScaleFactor=100.0` (metres), no scale on the object, rotation `(-90, 0, 0)` | `[V BL:run]` |
| FBX, `bake_space_transform=True` | vertices baked to `(100, 300, -200)`, no object rotation or scale | `[V BL:run]` |

Units: Epic's glTF exporter has `export_uniform_scale`, "Scale factor used for exporting all assets (0.01 by
default) for conversion from centimeters (Unreal default) to meters (glTF)". `[V PY:GLTFExportOptions]` So Unreal
units are centimetres, glTF units are metres, and the factor between them is 100; that the importer applies it by
itself is the expected mirror image, not something read.

What Unreal does with the axes `[M]` (Unreal is left-handed, Z up):

- glTF import swaps Y and Z and multiplies by 100: glTF `(x, y, z)` becomes Unreal `(x, z, y) * 100`. Combined:
  **Blender `(x, y, z)` m becomes Unreal `(x, -y, z) * 100` cm.** Blender +X stays +X, Blender +Y becomes -Y,
  Blender +Z stays +Z, 1 m becomes 100 units. This equals the project convention
  `Unreal(X, Y, Z) = (x_blender, -y_blender, z_blender) * 100`.
- A prop modelled with forward = Blender +X faces Unreal +X. A character modelled facing Blender -Y faces Unreal +Y
  in mesh space (the mannequin convention; the character class turns the mesh by -90 degrees yaw).
- FBX import with `convert_scene=True` and `force_front_x_axis=False` ends at the same mapping; `convert_scene_unit`
  uses the file's `UnitScaleFactor`. With Blender's default FBX options the object-level scale of 100 is what makes
  static meshes arrive at the right size and what gives skeletons a scaled root; `FBX_SCALE_UNITS` avoids it.
  Property names `[V PY:FbxStaticMeshImportData, PY:InterchangeFbxTranslatorSettings]`, behaviour `[M]`.
- Interchange offers a correction in one place if the first import disagrees: `import_offset_rotation`,
  `import_offset_translation`, `import_offset_uniform_scale` on `InterchangeGenericAssetsPipeline`. `[V PY:InterchangeGenericAssetsPipeline]`
- `bake_meshes` bakes the node transform into the mesh, so export each asset with its pivot at the object origin and
  the object at the world origin. Name `[V PY:InterchangeGenericCommonMeshesProperties]`, advice `[M]`.

Choice: **GLB for static meshes and skeletal meshes** (metres, one axis rule, no scale on objects; the 5.8 glTF
translator "support[s] import of texture, material, static mesh, skeletal mesh" `[V PY:InterchangeGLTFTranslator]`);
FBX only as a fallback, then with `apply_scale_options='FBX_SCALE_UNITS'`.

The Unreal half is memory. **Run the calibration in Appendix A before importing the asset library.**

### 5.2 What a Blender GLB should contain

Measured `[V BL:run]`:

- `export_materials='EXPORT'` writes one glTF material per slot **with the slot name** (`"name": "MI_Brick_Red"`).
  `'PLACEHOLDER'` keeps one primitive per slot but writes no materials, so the names are lost. `'NONE'` merges the
  primitives. To keep slot names without shipping textures inside the GLB use `export_materials='EXPORT'` with
  `export_image_format='NONE'` (enum values: `AUTO`, `JPEG`, `WEBP`, `NONE`).
- A Blender material exports `"doubleSided": true` unless backface culling is enabled on it.
- Defaults: `export_tangents=False`, `export_apply=False` (modifiers not applied), `export_extras=False`,
  `export_texcoords=True`, `export_normals=True`, `use_selection=False`.
- The mesh name and node name are written as given (`SM_Test_Quad`).

Whether Unreal names the static mesh after the file, the node or the mesh, and whether slots keep the glTF material
names, is in section 6.

### 5.3 Nanite

- Enable on import with `build_nanite` (3.2) or afterwards with `set_nanite_settings` (3.3). `[V PY:InterchangeGenericMeshPipeline, PY:StaticMeshEditorSubsystem]`
- "Nanite isn't compatible with translucent materials. Masked materials can be used on Nanite meshes, but they're
  not as efficient as opaque materials." `[V F:2600473/3]` (answer in an Epic support thread, 2025-06) A translucent material on a Nanite
  mesh makes it render its fallback mesh. `[M+ F:2738542/2]` Split glass and other translucent parts into separate
  meshes without Nanite.
- A material needs `used_with_nanite`. `[V PY:Material]` (the editor sets usage flags when it can `[M]`)
- "Nanite Skeletal Mesh feature is still experimental and is not recommended for production use." `[V F:2675029/3]`
  (answer in an Epic support thread, 2025-10-14, so before 5.7) `USkeletalMesh` has a `nanite_settings` property in 5.8. `[V PY:SkeletalMesh]`
  Its 5.8 status was not verified: do not enable Nanite on characters, arms or weapons.
- Mesh guidance from the same Epic post: keep the vertex count below the triangle count where possible (a 2:1
  vertex-to-triangle ratio signals a problem, 3:1 is fully faceted); long thin triangles cluster badly; kitbashing is
  fine but watch overdraw from stacked surfaces. `[V F:2675029/3]`
- Fallback mesh and precision are per mesh in `MeshNaniteSettings` (`fallback_percent_triangles`,
  `fallback_relative_error`, `position_precision`); `r.Nanite 0` turns Nanite rendering off project-wide and LOD0 is
  then built from the fallback settings. `[V PY:MeshNaniteSettings, F:2567476/3]`
- `UStaticMeshComponent::bDisallowNanite` forces the fallback for one component. `[V PY:StaticMeshComponent]`
- Collision does not come from Nanite: give each mesh simple collision or `UCX_` hulls (3.2, 3.3).

### 5.4 Textures: packing and the normal-map convention

- glTF packs occlusion in **R**, roughness in **G**, metallic in **B** of one linear image: "glTF expects the
  metallic values to be encoded in the blue (B) channel, and roughness to be encoded in the green (G) channel",
  "glTF stores occlusion in the red (R) channel, allowing it to optionally share the same image with the roughness
  and metallic channels". `[V BL:gltf]` This is the project's `T_<Set>_ORM`; import it linear with `TC_MASKS` (3.4).
- Blender and glTF normal maps are tangent space with **+Y up** (OpenGL): "Normal Map (tangent space, +Y up)"; bake
  with "space: Tangent, R: +X, G: +Y, B: +Z". `[V BL:gltf]`
- Unreal's normal maps have the green channel the other way: Epic's glTF exporter option `adjust_normalmaps` reads
  "exported normalmaps will be adjusted from Unreal to glTF convention (i.e. the green channel is flipped)".
  `[V PY:GLTFExportOptions]` (users call the Unreal side "DirectX, Y down" `[M+ F:761255/9, F:2725536/6]`) Keep the
  files as Blender bakes them and set `flip_green_channel = True` on every `T_<Set>_N` at import (3.4). `[V PY:Texture]`
- Tangent basis: let Unreal compute MikkTSpace tangents from imported normals (`use_mikk_t_space`,
  `recompute_tangents`) and do not export tangents from Blender (its default). `[V PY:InterchangeGenericCommonMeshesProperties, BL:run]`
  Blender bakes in the same MikkTSpace basis `[M]`.
- Image textures feeding non-colour inputs must be "Non-Color" in Blender. `[V BL:gltf]` In Unreal that is
  `srgb = False`.
- Emissive values above 1 use the glTF extension `KHR_materials_emissive_strength`. `[V BL:gltf]`

### 5.5 Lightmap UVs with Lumen

- With `r.AllowStaticLighting=False` and Lumen there are no baked lightmaps, so meshes need no lightmap UV channel:
  import with `generate_lightmap_u_vs = False`. Key and property names `[M+ F:2687111/5]`, `[V PY:InterchangeGenericMeshPipeline]`; the statement itself `[M]`.
- Lumen builds "mesh cards" per mesh: `max_lumen_mesh_cards`, default 12, 0 disables. `[V PY:InterchangeGenericMeshPipeline]`
  Software ray tracing uses mesh distance fields (`distance_field_resolution_scale`,
  `generate_distance_field_as_if_two_sided`, component `affect_distance_field_lighting`). `[V PY:InterchangeGenericMeshPipeline, PY:StaticMeshComponent]`
  Lumen works best with closed, reasonably thick, modular meshes rather than one merged building `[M]`.
- UV channel 0 only needs to serve the textures.

### 5.6 Fab, Megascans, City Sample

- Fab (`fab.com`) went live for everyone on 2024-10-22; it unifies the Unreal Engine Marketplace, Quixel and
  Sketchfab. `[V F:2083493, F:2033839]`
- **Megascans are not free any more.** "The Megascans library on Fab.com will no longer be free after December 31,
  2024." Assets claimed before that date stay usable under the Fab Standard License. "Beginning January 1, 2025, we
  will offer a selection of 1500+ Megascans assets for free on Fab.com ... under the Fab Standard License." Prices
  from 2025: single assets from $0.99, packs from $24.99. `[V F:2203090, F:2033839]` (Epic)
- The Fab Standard License allows use "in any tool or engine". `[V F:2033839]`
- Whether this project's Epic account claimed the 2024 library decides what is free for it: ask the owner.
- Quixel Megaplants were "currently available for free download in Fab" at the 5.7 release. `[V F:2673913]`
- How content is added: the **Fab plugin inside the editor** ("you can still add assets directly to your Unreal
  Engine project using the Fab plugin" `[M+ F:2282620/2]`); class `InterchangeMegascansPipeline` lives in Plugin
  `Fab`, Module `Fab`. `[V PY:InterchangeMegascansPipeline]` Quixel Bridge is being retired ("Only when Fab offers a
  replacement to Bridge ... will we discontinue Bridge" `[V F:2203090]`; users report the Bridge plugin deprecated in
  5.8 `[M+ F:2839713/3]`). Outside the editor, download from fab.com and import the files.
- In 5.9 Preview "the new Fab toolset lets agents search the catalog, browse your library, and install free or
  purchased assets directly into your projects". `[V F:2852840]` Not in 5.8.
- City Sample (project, Buildings, Vehicles, Crowds): Epic sample content marked "UE-Only Content - Licensed for Use
  Only with Unreal Engine-based Products"; it may ship inside an Unreal game and may not be sold on its own.
  `[M+ F:1528806]` Current listing, price and supported engine versions were not checked (fab.com unreachable).
  Check each asset against this game's rule "no real brands except IPX" before use.
- Imported Fab or Megascans packs often arrive with wrong texture settings and Nanite off (a 2026-11 tool
  announcement lists exactly that `[M+ F:2860134]`): run the same normalising pass over them as over our own assets.

---

## 6. Could not verify

Each line says what to look at first once an editor or the documentation is reachable. Appendix A covers the first
five.

1. **glTF to Unreal axis and scale** (5.1): that Blender `(1, 2, 3)` m lands at Unreal `(100, -200, 300)`. Appendix A.2.
2. **Normal-map green channel on glTF import**: whether Interchange flips it for glTF normal textures by itself. The
   pipeline avoids the question by importing textures separately and setting `flip_green_channel` (3.4).
3. **Interchange pipeline object passed through `InterchangePipelineStackOverride.add_pipeline`** is honoured for
   `.glb` and its sub-pipeline settings (`build_nanite`, `import_materials=False`) take effect (3.2).
4. **Asset and slot naming on glTF import**: static mesh named after file, node or mesh; material slot names equal to
   glTF material names when materials are not imported.
5. **Volumes spawned by script** have a usable brush (reported yes, 2 m cube, on 5.8.3 `[M+ F:2849553]`).
6. **Ini keys not seen in any file**: none in the block of 2.2 except the `HardwareTargetingSettings` values, the
   `RecastNavMesh` line and `GlobalDefaultGameMode=/Script/...`. Open the project once, change one setting in
   Project Settings, and diff the ini.
7. **Substrate default** for new 5.8 projects, and `r.Substrate.ProjectGBufferFormat` values.
8. **Lumen Lite** setting name; **MegaLights** requirements; whether hardware ray tracing is available on Linux in 5.8.
9. **TSR** is the default anti-aliasing for desktop in 5.8 (the value 4 is verified, the default is not).
10. **`"Optional": true`** in Epic documentation, and the exact behaviour when an optional enabled plugin is missing
    in an unattended run.
11. **Plugin default states** in 5.8: `PythonScriptPlugin`, `EditorScriptingUtilities`, `EnhancedInput`, `Niagara`,
    `Interchange`.
12. **Header folders** in the table of 4.2, and every native signature marked `[M]` in section 4 (traces, timers,
    `TakeDamage`, `OnMoveCompleted`, `UWidgetTree::ConstructWidget`, Slate, JSON, automation macros).
13. **`BuildSettingsVersion` / `EngineIncludeOrderVersion`** values for 5.8 (the file uses `.Latest` for both).
14. **Compiler requirements** for 5.8 on Windows and Linux (Visual Studio and MSVC versions, Windows SDK, clang
    toolchain), and the embedded Python version.
15. **Linux**: that `Engine/Binaries/Linux/UnrealEditor-Cmd` exists in the 5.8 download; whether `-nullrhi` editor
    runs can import meshes and build Nanite and distance fields.
16. **`-ExecutePythonScript` arguments**: how to pass arguments to the script (use an environment variable or a job
    file until known).
17. **Legacy FBX path**: whether `AssetImportTask.options = FbxImportUI` still selects the old importer in 5.8.
18. **Nanite on skeletal meshes** status in 5.8.
19. **The Fab 0.0.22 `FabToolset` build failure** on 5.8.4 (4.16): whether it still happens and which workaround
    Epic recommends.
20. **City Sample and Megascans listings** on fab.com today, and which Megascans this project's account owns.
21. **Niagara authoring by script** in 5.8 (3.6).
22. **Case sensitivity of `FJsonObject` keys** and of `FJsonObjectConverter` in 5.8.
23. **Mouse-look pitch sign** with `bEnableLegacyInputScales=False`, and whether that is already the default.

Pages that Epic's own posts link and that would settle most of this (none could be opened here):

- `https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes` (from `F:2729274`)
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-5-7-release-notes` (from `F:2673913`)
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-virtualized-geometry-in-unreal-engine` (from `F:2675029/3`)
- `https://dev.epicgames.com/documentation/en-us/unreal-engine/substrate-materials-in-unreal-engine` and
  `.../megalights-in-unreal-engine` (from `F:2673913`)
- `https://dev.epicgames.com/documentation/unreal-engine/quick-start-guide-for-using-container-images-in-unreal-engine` (from `F:2763115`)
- `https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-9-release-notes` and the roadmap
  `https://dev.epicgames.com/community/unreal-engine/roadmap` (from `F:2852840`)

The engine source (`github.com/EpicGames/UnrealEngine`, tag `5.8.4-release`) would settle item 12 at once; it is not
attached to this session.

---

## Appendix A. Calibration scripts

### A.1 Blender side (run here, results in 5.1 and 5.2)

```python
# <blender python> make_probe.py  ->  writes SM_MI_Probe.glb next to the script
import bpy, os
bpy.ops.wm.read_factory_settings(use_empty=True)
mesh = bpy.data.meshes.new("SM_MI_Probe")
mesh.from_pydata([(1.0, 2.0, 3.0), (2.0, 2.0, 3.0), (1.0, 3.0, 3.0)], [], [(0, 1, 2)])   # metres, Z up
mesh.update()
mat = bpy.data.materials.new("MI_Probe_Slot"); mesh.materials.append(mat)
obj = bpy.data.objects.new("SM_MI_Probe", mesh)
bpy.context.scene.collection.objects.link(obj)
bpy.ops.export_scene.gltf(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "SM_MI_Probe.glb"),
                          export_format="GLB", export_yup=True, export_materials="EXPORT", export_image_format="NONE")
```

The GLB holds positions `(1, 3, -2)`, `(2, 3, -2)`, `(1, 3, -3)`.

### A.2 Unreal side (first thing to run in a real 5.8 editor)

```python
# UnrealEditor-Cmd <abs>/MurderInc.uproject -run=pythonscript -script="<abs>/probe.py"   (set MI_PROBE_GLB first)
import json, os
import unreal

report = {"engine": unreal.SystemLibrary.get_engine_version()}
names = ["InterchangeManager", "InterchangeGenericAssetsPipeline", "InterchangePipelineStackOverride",
         "StaticMeshEditorSubsystem", "LevelEditorSubsystem", "EditorActorSubsystem", "MaterialEditingLibrary",
         "EditorAssetLibrary", "EditorPythonScripting", "NavMeshBoundsVolume", "ToolsetRegistry"]
report["classes"] = {n: hasattr(unreal, n) for n in names}

def has_props(obj, props):
    found = {}
    for prop in props:
        try:
            obj.get_editor_property(prop)
            found[prop] = True
        except Exception:
            found[prop] = False
    return found

pipe = unreal.InterchangeGenericAssetsPipeline()
mesh_pipe = pipe.get_editor_property("mesh_pipeline")
report["mesh_pipeline"] = has_props(mesh_pipe, ["build_nanite", "collision", "generate_lightmap_u_vs",
                                                "combine_static_meshes_behavior", "import_collision_according_to_mesh_name"])
report["common"] = has_props(pipe.get_editor_property("common_meshes_properties"),
                             ["force_all_mesh_as_type", "recompute_tangents", "use_mikk_t_space", "bake_meshes"])

glb = os.environ.get("MI_PROBE_GLB", "")
if glb:
    mesh_pipe.set_editor_property("build_nanite", False)
    mesh_pipe.set_editor_property("generate_lightmap_u_vs", False)
    mats = pipe.get_editor_property("material_pipeline")
    mats.set_editor_property("import_materials", False)
    override = unreal.InterchangePipelineStackOverride()
    override.add_pipeline(pipe)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", glb)
    task.set_editor_property("destination_path", "/Game/_Probe")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    task.set_editor_property("options", override)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = []
    for obj in task.get_objects():
        entry = {"name": obj.get_name(), "class": obj.get_class().get_name()}
        if isinstance(obj, unreal.StaticMesh):
            box = obj.get_bounding_box()
            entry["min"] = [box.min.x, box.min.y, box.min.z]
            entry["max"] = [box.max.x, box.max.y, box.max.z]
            entry["slot_MI_Probe_Slot"] = obj.get_material_index("MI_Probe_Slot")
        imported.append(entry)
    report["imported"] = imported

unreal.log("MI_PROBE " + json.dumps(report))
```

Expected if section 5.1 is right: one static mesh, `min = [100, -300, 300]`, `max = [200, -200, 300]`,
`slot_MI_Probe_Slot = 0`. Any other bounds: put the correction into `import_offset_rotation` /
`import_offset_uniform_scale` in one place and note it in this file. `obj.get_name()` and
`obj.get_class().get_name()` are standard object functions `[M]`.

## Appendix B. Forum topics cited

| Key | Topic | Author |
|---|---|---|
| `F:2729274` | Unreal Engine 5.8 Released (includes 5.8.1 notes) | Epic |
| `F:2738864`, `F:2746335`, `F:2833315`, `F:2842775` | 5.8.1 to 5.8.4 Hotfix Released | Epic |
| `F:2852840` | [Preview 2] Unreal Engine 5.9 Preview; post 3 known issues | Epic |
| `F:2829/20` | Current Available Quick-Fix Solutions (5.9 Preview QFE) | Epic |
| `F:2673913` | Unreal Engine 5.7 Released; post 149 a user's ini | Epic / user |
| `F:2538952` | Unreal Engine 5.6 Released | Epic |
| `F:883977` | TSR feedback thread | Epic (TSR author) |
| `F:724404` | Interchange with Python in an Unreal commandlet; posts 2 and 4 | Epic staff (`UE_` account) |
| `F:2600473/3`, `F:2675029/3`, `F:2567476/3` | Nanite answers in Epic support threads | the answering side of Epic's support forum |
| `F:2717162/2` | Staging non-asset directories (Japanese) | the answering side of Epic's support forum |
| `F:463127/2` | RunUAT on Linux | anonymous, support-style reply |
| `F:2693657` | A project ini with `r.DefaultFeature.AutoExposure.Bias` | user |
| `F:2203090`, `F:2033839`, `F:2083493` | Megascans and Fab transition | Epic |
| `F:2687111/5` | Rendering differences between 5.5 and 5.7: a 5.7 project's renderer ini | customer in Epic support thread |
| `F:2664001/2` | Path tracer thread: renderer ini | customer in Epic support thread |
| `F:2742734` | A 2026 DefaultEngine.ini | user |
| `F:2849553` | 5.8.3 navigation build lock, with a working editor Python script | user |
| `F:2729403`, `F:2729455`, `F:2729488`, `F:2838948` | 5.8 MCP server reports | users |
| `F:2846816` | Fab plugin 0.0.22 breaks C++ builds on 5.8.4 | user |
| `F:2763115` | Unreal tests on GitHub Actions (container image, test command line) | user |
| `F:2506983`, `F:1538861`, `F:1771494` | Python from the command line | users |
| `F:2577252/14`, `F:1985382` | Packaging and Linux build command lines | users |
| `F:131525/9`, `F:1836345/10` | Optional plugin reference, log line | users |
| `F:428070/8` | `DirectoriesToAlwaysStageAsNonUFS` in DefaultGame.ini | user |
| `F:1190042/130` | A DefaultEngine.ini with `GameMapsSettings` | user |
| `F:761255/9`, `F:2725536/6` | Normal-map convention | users |
| `F:2738542/2`, `F:2282620/2`, `F:2839713/3`, `F:1528806`, `F:2860134`, `F:2844467/2` | Nanite fallback, Fab plugin, Bridge, City Sample licence, asset fixes, Linux ray tracing | users |
