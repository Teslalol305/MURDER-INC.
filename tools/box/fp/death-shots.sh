#!/bin/bash
# The death pass's proof (docs/unreal/PLAY.md, death lane): play in editor in L_Block, a Story run, and frame sequences
# of Goons killed by the death probe (MI.Goon.Kill: one round from the player's eye, or one blast, through the same
# damage path as the weapon), the world's time frozen for each picture (MIFreezeAfter) so one instant of the fall is
# caught while Lumen settles. Each sequence: the kill, then frames at about 0.05, 0.25, 0.6, 1.5 s and 4 s after it,
# the last two also from beside the body.
# Run detached with L_Block open:  setsid nohup bash death-shots.sh [out] > log 2>&1 &
#   ONLY="front back" takes only those sequences (front head back blast stairs wall ten). OLD=1 runs with the ragdoll
#   switched off (mi.Goon.Ragdoll 0: the death clip as before the pass), for the "before" pictures.
# Pictures: <out>/<sequence>-<n>.jpg (default $MI_LOGS/death); ends with DEATH SHOTS DONE.
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/death}
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
c() { pie_con "$*" > /dev/null; }
run() { c "MIFreezeAfter $1"; sleep "$(python3 -c "print(max(2.0, $1 * 3.0 + 1.5))")"; }
shot() { settle "${2:-24}"; pie_shot "$out/$1.jpg"; }
want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1 "* ]]; }
killed() { tail -n +"$1" "$log" | grep -o 'MI.Goon.Kill: [A-Za-z0-9_]* [a-z]* at [0-9.]* m, shot [a-z ]*' | tail -1; }
# obs <metres> <degrees>: the player beside the last Goon killed (its pelvis), <degrees> round from the line it was
# shot along, looking down at the body
obs() {
  local name; name=$(tail -n +"$m" "$log" | grep -o 'MI.Goon.Kill: [A-Za-z0-9_]*' | tail -1 | awk '{print $2}')
  cat > "$PIE_PY/_obs.py" <<PY
import math, unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
me = pawn.get_actor_location()
g = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if a.get_name() == "$name"]
mesh = g[0].get_components_by_class(unreal.SkeletalMeshComponent)[0]
p = mesh.get_socket_location("pelvis")
a = math.atan2(me.y - p.y, me.x - p.x) + math.radians($2)
x, y = p.x + math.cos(a) * $1 * 100, p.y + math.sin(a) * $1 * 100
yaw = math.degrees(math.atan2(p.y - y, p.x - x))
pitch = -math.degrees(math.atan2(150.0, $1 * 100))   # the eye about 1.6 m up, the body on the ground
feet = g[0].get_actor_location().z - 90.0   # the rules' unit stands where it died: its feet are on the ground there
unreal.SystemLibrary.execute_console_command(w, "MIPose %.0f %.0f %.0f %.1f %.1f" % (x, y, feet, yaw, pitch))
"pelvis %.0f %.0f %.0f" % (p.x, p.y, p.z)
PY
  pie_mcp py "$PIE_PY/_obs.py"
}
# cam <x> <y> <z> <pitch> <yaw>: the pictures from a camera there (the view target), not the player's eye; cam off: back
cam() {
  if [ "$1" = off ]; then
    printf 'import unreal\nw = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()\npc = unreal.GameplayStatics.get_player_controller(w, 0)\npc.set_view_target_with_blend(pc.get_controlled_pawn(), 0.0)\n"cam off"\n' > "$PIE_PY/_cam.py"
  else
    cat > "$PIE_PY/_cam.py" <<PY
import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(w, 0)
cams = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.CameraActor) if a.get_name().startswith("DeathCam")]
if cams:
    c = cams[0]
else:
    c = w.spawn_actor(unreal.CameraActor, unreal.Vector(0, 0, 0), unreal.Rotator()) if hasattr(w, "spawn_actor") else unreal.GameplayStatics.finish_spawning_actor(unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(w, unreal.CameraActor, unreal.Transform()), unreal.Transform())
    c.rename("DeathCam")
c.set_actor_location_and_rotation(unreal.Vector($1, $2, $3), unreal.Rotator(roll=0.0, pitch=$4, yaw=$5), False, True)
c.camera_component.set_field_of_view(50.0)
pc.set_view_target_with_blend(c, 0.0)
"cam at %.0f %.0f %.0f" % ($1, $2, $3)
PY
  fi
  pie_mcp py "$PIE_PY/_cam.py"
}

# kseq <name> <side metres> <side degrees> <MI.Goon.Kill arguments>: one kill and its frames (named kseq: a function
# called seq would hide the seq command that settle and the waits use)
kseq() {
  local n=$1 om=$2 od=$3; shift 3
  want "$n" || return 0
  m=$(wc -l < "$log")
  # the world runs at full speed when the bodies are made: a ragdoll started in the frozen world (time dilation
  # 0.0001) is solved with steps of microseconds and its joints throw it into the air (seen in the first pictures)
  c "slomo 1"; c "MI.Goon.Kill $*"
  run 0.05; shot "$n-1"
  run 0.2; shot "$n-2"
  run 0.35; shot "$n-3"
  run 0.9; shot "$n-4"
  echo "$n: $(killed "$m")"
  if [ "$om" != 0 ]; then obs "$om" "$od"; run 0.05; fi
  run 3.0; shot "$n-5"
  tail -n +"$m" "$log" | grep -E "MI.Goon.Kill (staged|result)" | cut -c1-200
}

# Play in editor asked while the editor still loads the map (the first start of a clone: its game thread is busy for a
# minute or two) is ignored: ask again, up to five times
for k in 1 2 3 4 5; do
  mark=$(wc -l < "$log")
  pie_start > /dev/null
  for i in $(seq 1 30); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
  tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break
  sleep 10
done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "DEATH SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
c "MIStart mission skip"
sleep 8; settle 10
printf 'god 1\n' > "$PIE_PY/_god.txt"; c "MIDemo.Run $PIE_PY/_god.txt"
[ "${OLD:-0}" = 1 ] && c "mi.Goon.Ragdoll 0"
run 1.0

# Staged bodies (MI.Goon.Kill ... x y z [turn]: the body stands there before it falls; the rules' unit stays where it was)
# on the open street where a Story run starts, the player 6 m west of the body, the pictures from a camera 4.5 m to the side
# (the player's own view: the -fp pictures). Then the stairs and a wall, and a natural blast kill seen from beside.
c "MIPose -3740 815 0 0 -4"; run 0.3
cam -3140 380 175 -18 90
kseq front 0 0 1 body 0 0 -3140 815 400
c "MIPose -3740 815 0 0 -4"; run 0.3
kseq head 0 0 1 head 0 0 -3140 815 400
c "MIPose -3740 815 0 0 -4"; run 0.3
kseq back 0 0 1 body 0 0 -3140 815 400 180
cam off
# the same, through the player's eyes
c "MIPose -3740 815 0 0 -4"; run 0.3
kseq frontfp 0 0 1 body 0 0 -3140 815 400
# wall: the body 60 cm in front of the shop fronts on the south side, shot toward the wall, the camera along the wall
c "MIPose -570 -390 0 -90 -4"; run 0.3
cam -170 -760 170 -18 -157
kseq wall 0 0 1 body 0 0 -570 -930 400
# stairs: on the shed's stair (12 risers, X -260 to 100, Y 900 to 1090), shot from the street, the camera beside the stair
c "MIPose -560 640 0 40 8"; run 0.3
cam -360 700 320 -22 45
kseq stairs 0 0 1 body 0 0 -60 1000 600
cam off
# blast: a blast beside the nearest living Goon, wherever it is, seen from beside the body
c "MIFaceEnemy 8"; run 0.4
kseq blast 3.5 90 1 blast 0 0
# ten at once (the cost probe's frames)
if want ten; then
  c "MIPose -2900 80 0 0 -3"; run 0.3
  m=$(wc -l < "$log")
  c "slomo 1"; c "MIFreezeAfter 99"; c "MI.Goon.Kill 10 body 0 1"; sleep 8
  tail -n +"$m" "$log" | grep -E "MI.Goon.Kill" | cut -c1-260
fi
grep -E 'Ensure|Error|LogPhysics' "$log" | tail -n +1 | tail -5
pie_stop > /dev/null
echo "DEATH SHOTS DONE"
