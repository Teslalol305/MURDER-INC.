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
| The MCP capture tool renders one frame without temporal history: Lumen, the sky light and TSR have not settled (black shadows) | `shot.sh ... cam=...` renders the view for 24 editor ticks through a persistent scene capture (`Content/Python/mi_shot.py`) and keeps the last frame. |
| Deleting a material that instances use orphans them; each orphan then compiles the default material synchronously on the game thread | `build_block.py` rebuilds the master material and its instances in place, never deletes them. |
| Files reach the box only through git (the box pulls the public repository, it cannot push) and through the user's Higgsfield storage | Commit and push locally, then `sync.sh` on the box. Big binary inputs (the Blender art) go through storage (section 4). |

## 2. The loop

| Step | Command on the box (`cd /project/ue/repo/tools/box`) | Time measured |
|---|---|---|
| Pull the branch | `bash sync.sh` (says `next: build.sh` when C++ changed) | 2 to 5 s |
| Build the editor target | `bash build.sh` then poll `bash build-status.sh` (`-w` for warnings) | 127 s for the game module after a C++ change; stops a running editor first |
| Tests | `bash test.sh` (all `MurderInc.*`, headless `-NullRHI` in `UnrealEditor-Cmd`), poll `bash test.sh status` | 33 s for the two current tests |
| Editor | `bash editor.sh start [/Game/Maps/L_Block]`, `status`, `stop`, `restart` | MCP answers about 40 s after start |
| Run editor Python | `python3 mi_mcp.py py <file.py or ->` (value of the last expression) | under 45 s per call |
| Build the block | `bash block.sh start [steps] [force]`, `bash block.sh wait` | see section 5 |
| Picture | `bash shot.sh /project/ue/logs/shots/x.jpg cam=X,Y,Z,pitch,yaw,roll fov=80` | 5 to 10 s for 24 frames at 1920 x 1080 |
| Picture to the local checkout | `media_upload` (filename `mi-x.jpg`), `bash put.sh <jpg> <upload_url> image/jpeg`, `media_confirm` (type image), local `curl -o` the url | about 10 s; several thousand tokens per picture |

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

1. Local: `tools/box/send-art.sh pack` makes `art/out/mi-art.tar`: the GLBs of the El, the street kit and the hydrant
   (patterns are arguments), every texture set their slots name (BC, N, ORM; height maps left out), the grey-box sets
   and `manifest.json`. 163 MB for 16 meshes and 21 sets.
2. `mcp__Higgsfield__media_upload` with filename `mi-art-<date>.tar` gives `upload_url`, `url` and `media_id`. The
   upload address is signed for the headers `content-type` and `if-none-match`: send
   `Content-Type: application/octet-stream` (the type the tool states) and `If-None-Match: *`.
3. Local: `tools/box/send-art.sh put "<upload_url>" application/octet-stream` (19 s for 163 MB; retries with
   `If-None-Match: *` on 403).
4. `mcp__Higgsfield__media_confirm` with the `media_id` and type `file`.
5. Box: `bash receive-art.sh "<url>"` downloads and unpacks to `/project/ue/art-in/` (4 s).

## 5. GLB import: what turned out to be true

(Filled in from the first block build; see `docs/unreal/PROGRESS.md` for the state.)
