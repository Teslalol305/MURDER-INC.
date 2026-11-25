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
# seq <name> <MI.Goon.Kill arguments>: one kill and its frames
seq() {
  local n=$1; shift
  want "$n" || return 0
  m=$(wc -l < "$log")
  c "MI.Goon.Kill $*"
  run 0.05; shot "$n-1"
  run 0.2; shot "$n-2"
  run 0.35; shot "$n-3"
  run 0.9; shot "$n-4"
  echo "$n: $(killed "$m")"
  obs 3.2 70; run 0.05; shot "$n-5"
  run 2.5; shot "$n-6"
  tail -n +"$m" "$log" | grep -E "MI.Goon.Kill (result|before|first|after)" | cut -c1-260
}

pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "DEATH SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
c "MIStart mission skip"
sleep 8; settle 10
printf 'god 1\n' > "$PIE_PY/_god.txt"; c "MIDemo.Run $PIE_PY/_god.txt"
[ "${OLD:-0}" = 1 ] && c "mi.Goon.Ragdoll 0"
run 1.0

# front: a Goon in front at 7 m, one round to the chest
c "MIFaceEnemy 7"; run 0.4
seq front 1 body 12 0
# head: the next one, a head shot
c "MIFaceEnemy 6"; run 0.4
seq head 1 head 12 0
# back: the player behind the next Goon (its back to the gun)
if want back; then
  c "MIFaceEnemy 7"; run 0.3
  cat > "$PIE_PY/_behind.py" <<'PY'
import math, unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
me = pawn.get_actor_location()
best = None
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    if a.get_class().get_name() == 'MIGoon' and a.get_actor_location().z > -50000:
        l = a.get_actor_location()
        d = math.hypot(l.x - me.x, l.y - me.y)
        if best is None or d < best[0]:
            best = (d, a)
g = best[1]
l, f = g.get_actor_location(), g.get_actor_forward_vector()
x, y = l.x - f.x * 600, l.y - f.y * 600
unreal.SystemLibrary.execute_console_command(w, "MIPose %.0f %.0f %.0f %.1f -4" % (x, y, l.z - 90, math.degrees(math.atan2(f.y, f.x))))
"behind %s" % g.get_name()
PY
  pie_mcp py "$PIE_PY/_behind.py"; run 0.02
  seq back 1 body 12 0
fi
# blast: a blast between the player and the next Goon
c "MIFaceEnemy 8"; run 0.4
seq blast 1 blast 12 0
# stairs: staged on the shed's stair (12 risers, X -260 to 100, Y 900 to 1090), shot from the street below
if want stairs; then
  c "MIPose -560 640 0 40 8"; run 0.3
  seq stairs 1 body 0 0 -60 1000 600
fi
# wall: staged 70 cm in front of the shop front on the north lane, shot toward the wall
if want wall; then
  c "MIPose 170 -380 0 -90 -2"; run 0.3
  seq wall 1 body 0 0 170 -900 400
fi
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
