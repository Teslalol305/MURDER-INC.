#!/bin/bash
# The game seen through the player's eyes in L_Block (block-v2-play-*.jpg): play in editor on the open map, start a
# Story run past the intro, then three pictures with the HUD: standing at the start, aimed down the avenue, beside a
# parked car. Run detached (about 2 minutes): setsid nohup bash play-shots.sh [out_dir] [prefix] > log 2>&1 &
# The editor must have /Game/Maps/L_Block open (editor.sh start /Game/Maps/L_Block, or block.sh start level).
out=${1:-/project/ue/logs/shots}; p=${2:-block-v2-play}
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
. ./pie.sh
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "PLAY SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4
pie_con "MIStart mission skip" > /dev/null
sleep 6

# pose <x> <y> <feet z> <yaw> <pitch>: the player's pawn there (capsule centre 92 cm over the feet), looking that way.
pose() {
  cat > "$PIE_PY/_pose.py" <<PY
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
pc = unreal.GameplayStatics.get_player_controller(w, 0)
pawn.set_actor_location(unreal.Vector($1, $2, $3 + 92.0), False, True)
pc.set_control_rotation(unreal.Rotator(roll=0.0, pitch=$5, yaw=$4))
l = pawn.get_actor_location()
"pawn at %.0f %.0f %.0f" % (l.x, l.y, l.z)
PY
  pie_mcp py "$PIE_PY/_pose.py"
}
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }

# 1 standing at the start, as the run begins (the player's own start pose)
settle 30
pie_shot "$out/$p-1.jpg"
pie_state | head -3
# 2 aimed down the avenue from under the El, looking east
pose -2900 80 0 0 0
pie_con "MIInput ads 1" > /dev/null
settle 30
pie_shot "$out/$p-2.jpg"
pie_con "MIInput ads 0" > /dev/null
# 3 beside the parked taxi on the north lane
pose 170 -380 0 -35 -6
settle 30
pie_shot "$out/$p-3.jpg"
grep -E 'LogMI|Error' "$log" | tail -n +1 | tail -5
pie_stop > /dev/null
echo "PLAY SHOTS DONE"
