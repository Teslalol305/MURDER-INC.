#!/bin/bash
# Shared settings and helpers for the box scripts. Sourced by the other scripts, never run on its own.
# The box: /project is persistent, everything else is lost on a stop. The engine and the editor run as user ue4.

MI_BRANCH=${MI_BRANCH:-claude/tender-albattani-5q78qr}
MI_UE=${MI_UE:-/project/ue}
MI_ENGINE=$MI_UE/UnrealEngine
MI_REPO=$MI_UE/repo
MI_PROJECT_DIR=$MI_REPO/unreal/MurderInc
MI_UPROJECT=$MI_PROJECT_DIR/MurderInc.uproject
MI_LOGS=$MI_UE/logs
MI_DDC=$MI_UE/ddc
MI_RUN_EDITOR=$MI_UE/bin/run-editor.sh
MI_BOX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MI_MCP_URL=${MI_MCP_URL:-http://127.0.0.1:8000/mcp}
export MI_MCP_URL

# Cache arguments that every editor or commandlet start needs on this box: the stock Zen local cache
# cannot be reached here, so a file-system cache graph is used and Zen auto-launch is off.
# Same values as /project/ue/bin/run-editor.sh (which also sets UE-LocalDataCachePath).
MI_CACHE_ARGS=('-DDC=(ProjectPak,InstalledProjectPak,EnginePak=InstalledEnginePak,EnterprisePak,InstalledLocal)' '-ini:Engine:[Zen]:AutoLaunch=false')

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

mi_editor_pid() { pgrep -x UnrealEditor | head -1; }

# Seconds since a file was last written, or an empty string when it does not exist.
mi_age() { [ -e "$1" ] && echo $(( $(date +%s) - $(stat -c %Y "$1") )); }
