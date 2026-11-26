#!/bin/bash
# Play-in-editor checks on this clone's headless editor (editor.sh start /Game/Maps/L_GameplayTest first).
# Source it, then:
#   pie_start | pie_stop
#   pie_con "MIInput ads 1;MIInput fire 1"   console commands in the PIE world (MIInput: AMIPlayerController)
#   pie_shot /tmp/x.jpg                      HighResShot of the PIE view (1920 x 1080), saved as JPEG
#   pie_state                                the player, dummies and explosives (location, rotation)
# Python runs on the editor's game thread: wait between calls with sleep here, never inside the Python.
PIE_BOX=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$PIE_BOX/lib.sh"
PIE_PY=$MI_LOGS/py
mkdir -p "$PIE_PY"
pie_mcp() { timeout 30 "$(mi_python)" "$PIE_BOX/mi_mcp.py" "$@"; }
pie_start() { pie_mcp tool EditorToolset.EditorAppToolset.StartPIE '{}'; }
pie_stop() { pie_mcp tool EditorToolset.EditorAppToolset.StopPIE '{}'; }
pie_con() {
  printf 'import unreal\nw = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()\nfor c in %s.split(";"):\n    unreal.SystemLibrary.execute_console_command(w, c)\n"ok"\n' \
    "$("$(mi_python)" -c 'import sys, json; print(json.dumps(sys.argv[1]))' "$1")" > "$PIE_PY/_con.py"
  pie_mcp py "$PIE_PY/_con.py"
}
pie_state() {
  cat > "$PIE_PY/_state.py" <<'PY'
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
rows = []
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    n = a.get_class().get_name()
    if n in ('MITargetDummy', 'MIExplosive', 'MIPlayerCharacter'):
        l, r = a.get_actor_location(), a.get_actor_rotation()
        rows.append('%s at %.0f %.0f %.0f rot %.0f %.0f %.0f' % (n, l.x, l.y, l.z, r.pitch, r.yaw, r.roll))
'\n'.join(rows)
PY
  pie_mcp py "$PIE_PY/_state.py"
}
pie_shot() {
  local dir=$MI_PROJECT_DIR/Saved/Screenshots f="" i
  rm -rf "$dir"
  # no frame while a texture is still building: the editor draws a building texture as a placeholder whose samples read
  # about 0 (the guns' black-mirror finish of HANDS_R4.md 11 and 12.5, in sessions right after a fresh import; 13)
  pie_con "Editor.AsyncTextureCompilationFinishAll" > /dev/null
  pie_con "HighResShot 1920x1080" > /dev/null
  for i in 1 2 3 4 5 6 7 8; do
    pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1
    f=$(find "$dir" -name '*.png' 2>/dev/null | head -1); [ -n "$f" ] && break
  done
  [ -n "$f" ] || { echo "PIE SHOT FAILED: no HighResShot file"; return 1; }
  "$(mi_python)" -c "from PIL import Image; Image.open('$f').convert('RGB').save('$1', quality=85)" && echo "PIE SHOT $1"
}
