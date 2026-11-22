#!/bin/bash
# Shared settings and helpers for the box scripts. Sourced by the other scripts, never run on its own.
# The box: /project is persistent, everything else is lost on a stop. The engine and the editor run as user ue4.

MI_BRANCH=${MI_BRANCH:-claude/tender-albattani-5q78qr}
MI_UE=${MI_UE:-/project/ue}
MI_ENGINE=$MI_UE/UnrealEngine
MI_BOX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The clone these scripts belong to (tools/box is two levels below its root). Several clones can share the box:
# /project/ue/repo (the level work, logs in /project/ue/logs, MCP port 8000) and others such as
# /project/ue/repo-gameplay (logs in /project/ue/logs/repo-gameplay, MCP port 8001), each with its own
# Binaries, Intermediate and Saved. Every process a script starts, stops or waits for is matched to this clone's
# project file, never to a bare process name, so one clone never stops another clone's editor or test run.
MI_REPO=$(cd "$MI_BOX_DIR/../.." && pwd)
MI_CLONE=$(basename "$MI_REPO")
MI_PROJECT_DIR=$MI_REPO/unreal/MurderInc
MI_UPROJECT=$MI_PROJECT_DIR/MurderInc.uproject
if [ "$MI_CLONE" = repo ]; then
  MI_LOGS=$MI_UE/logs
  MI_MCP_PORT=${MI_MCP_PORT:-8000}
else
  MI_LOGS=$MI_UE/logs/$MI_CLONE
  MI_MCP_PORT=${MI_MCP_PORT:-8001}
fi
MI_DDC=$MI_UE/ddc
MI_RUN_EDITOR=$MI_UE/bin/run-editor.sh
MI_MCP_URL=${MI_MCP_URL:-http://127.0.0.1:$MI_MCP_PORT/mcp}
export MI_MCP_URL
mkdir -p "$MI_LOGS" 2>/dev/null

# Cache arguments that every editor or commandlet start needs on this box: the stock Zen local cache
# cannot be reached here, so a file-system cache graph is used and Zen auto-launch is off.
# Same values as /project/ue/bin/run-editor.sh (which also sets UE-LocalDataCachePath).
MI_CACHE_ARGS=('-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal)' '-ini:Engine:[Zen]:AutoLaunch=false')

# The asset registry watches the whole Engine/Plugins tree for file changes. On Linux that is one inotify watch per
# directory, set up on the game thread: 55,000 directories on the 9p volume cost 10 to 25 minutes per editor start.
# Off for every editor process on the box. Consequence: files copied into Content while the editor runs are not
# seen until the editor restarts or unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous() runs.
MI_EDITOR_ARGS=('-ini:Engine:[ConsoleVariables]:AssetRegistry.DisableDirectoryWatcher=1')

mi_die() { echo "$*"; exit 1; }

# The environment run-editor.sh gives the editor, for the other engine programs (UnrealEditor-Cmd):
# HOME of ue4, and its Epic settings folder kept on persistent storage.
mi_engine_env() {
  export HOME=/home/ue4 DISPLAY=${DISPLAY:-:1}
  mkdir -p /home/ue4/.config "$MI_UE/home/Epic" "$MI_LOGS"
  [ -L /home/ue4/.config/Epic ] || { rm -rf /home/ue4/.config/Epic; ln -sfn "$MI_UE/home/Epic" /home/ue4/.config/Epic; }
}

# The engine refuses to run as root, and the mirror belongs to ue4: re-run the calling script as ue4.
mi_become_ue4() {
  if [ "$(id -un)" = ue4 ]; then return 0; fi
  id ue4 >/dev/null 2>&1 || mi_die "NO-UE4-USER: run /project/ue/setup-box.sh first (the user is lost when the box stops)"
  exec su ue4 -c "$(printf '%q ' bash "$0" "$@")"
}

# A Python with Pillow when there is one (faster image statistics), else any python3.
mi_python() {
  local p
  for p in /opt/venv/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if [ -x "$p" ] && "$p" -c 'import PIL' >/dev/null 2>&1; then echo "$p"; return; fi
  done
  command -v python3
}

mi_mcp() { "$(mi_python)" "$MI_BOX_DIR/mi_mcp.py" "$@"; }

# Process ids with this name (cut to 15 characters, as pgrep -x sees it) whose command line names this clone's project.
mi_pids_of() {
  local p
  for p in $(pgrep -x "$1"); do
    tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -qF "$MI_UPROJECT" && echo "$p"
  done
}

mi_editor_pid() { mi_pids_of UnrealEditor | head -1; }

# Seconds since a file was last written, or an empty string when it does not exist.
mi_age() { [ -e "$1" ] && echo $(( $(date +%s) - $(stat -c %Y "$1") )); }
