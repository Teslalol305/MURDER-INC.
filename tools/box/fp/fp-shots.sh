#!/bin/bash
# The first-person proof (docs/unreal/shots/fp-*.jpg): play in editor in L_Block through the player's eyes, with the
# HUD. A set-up of CHOPPER, NINE and STICK (scope, vertical grip) is made on the set-up screens, a Story run starts,
# and the world's time is frozen for each picture (MIFreezeAfter / MIFreezeOn: time dilation 0.0001) so one instant
# of a clip or an effect is caught while Lumen settles over 30 redraws.
# Run detached with L_Block open (editor.sh start /Game/Maps/L_Block):  setsid nohup bash fp-shots.sh [out] > log 2>&1 &
# Pictures: <out>/fp-*.jpg (default $MI_LOGS/fp); ends with FP SHOTS DONE.
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/fp}
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
fe() { pie_con "MIMenu fe $*" > /dev/null; }
c() { pie_con "$*" > /dev/null; }
# run <seconds>: let that much game time pass, then freeze (the wall clock waits generously)
run() { c "MIFreezeAfter $1"; sleep "$(python3 -c "print(max(2.0, $1 * 3.0 + 1.5))")"; }
shot() { settle "${2:-30}"; pie_shot "$out/$1.jpg"; }
# ONLY="fp-goon fp-explosion" takes only those pictures (the set-up and the poses before them still run)
want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1 "* ]]; }

pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "FP SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
# the set-up: CHOPPER, NINE, STICK with the scope and the vertical grip, nothing else fitted
fe home; fe gearup; fe next
fe slot 1 chopper; fe slot 2 nine; fe slot 3 stick; fe empty 4
fe bench stick; fe benchslot optic; fe fit scope; fe benchslot muzzle; fe fit factory; fe benchslot laser; fe fit factory
fe benchslot underbarrel; fe fit grip_vertical; fe done
fe next; fe time day; fe next; fe mode mission; fe difficulty hustler; fe hit
sleep 10; settle 10
tail -n +"$mark" "$log" | grep -E "Set-up:|First person:" | tail -5 | cut -c1-260
c "MIInput weapon1 1"; run 1.0; c "MIInput weapon1 0"

# 1 hip, CHOPPER, in the sun on the north lane
c "MIPose 170 -380 0 -35 -4"; run 1.2; want fp-hip-sun && shot fp-hip-sun
# 2 hip under the El
c "MIPose -2900 80 0 0 -3"; run 1.2; want fp-hip-el && shot fp-hip-el
# 3 aimed through the irons
c "MIInput ads 1"; run 0.8; want fp-irons && shot fp-irons
c "MIInput ads 0"
# 3b firing a burst from the hip: frozen 0.02 s after a round (the flash lives 0.045 s), then 0.006 s
c "MIPose -2900 80 0 0 -3"; run 0.3
c "MIFreezeOn fire 0.02"; c "MIInput fire 1"; sleep 4; want fp-fire && shot fp-fire
c "MIInput fire 0"; c "slomo 1"; run 0.6
if want fp-fire-early; then c "MIFreezeOn fire 0.006"; c "MIInput fire 1"; sleep 4; shot fp-fire-early; c "MIInput fire 0"; c "slomo 1"; run 0.6; fi
# 4 mid tactical reload (five rounds spent, the fresh magazine on its way up)
c "MIPose -2900 80 0 0 6"; c "MIInput fire 1"; run 0.4; c "MIInput fire 0"; run 0.3
c "MIFreezeOn reload 1.2"; c "MIInput reload 1"; sleep 5; c "MIInput reload 0"; want fp-reload-tactical && shot fp-reload-tactical
# 5 mid empty reload: the magazine dropped and falling (the auto reload after the last round)
c "MIPose -2900 80 0 0 -18"; run 0.3
c "MIInput fire 1"; c "MIFreezeOn reload 0.50"; sleep 12; c "MIInput fire 0"; want fp-reload-empty && shot fp-reload-empty
run 3.0
# 6 the inspect (a full magazine after the reload)
c "MIPose 170 -380 0 -35 -4"; run 0.5; c "MIInput inspect 1"; run 2.4; c "MIInput inspect 0"; want fp-inspect && shot fp-inspect
run 4.0
# 7 the STICK aimed through the scope
c "MIInput weapon3 1"; run 1.0; c "MIInput weapon3 0"; c "MIPose -2900 80 0 0 0"; c "MIInput ads 1"; run 0.9; want fp-scope && shot fp-scope
c "MIInput ads 0"
# 8 the NINE aimed
c "MIInput weapon2 1"; run 1.0; c "MIInput weapon2 0"; c "MIPose 170 -380 0 -35 -2"; c "MIInput ads 1"; run 0.8; want fp-nine && shot fp-nine
c "MIInput ads 0"; c "MIInput weapon1 1"; run 1.0; c "MIInput weapon1 0"
# 9 a Goon firing at the player from 10 m (frozen on its round)
# (MIFreezeOn enemyfire waits for a Goon in plain sight within 13 m and turns the view onto it)
m2=$(wc -l < "$log"); c "MIFreezeOn enemyfire 0.012"
for i in 1 2 3 4 5 6 7 8; do
  c "MIFaceEnemy 10"; c "slomo 1"; sleep 6
  tail -n +"$m2" "$log" | grep -q "MIFreezeOn: enemyfire" && break
done
tail -n +"$m2" "$log" | grep -m1 "MIFreezeOn: enemyfire" || echo "no Goon fired in sight"
want fp-goon && shot fp-goon
# 10 an explosion: the nearest explosive, from 9 m, shot until it blows
cat > "$PIE_PY/_boom.py" <<'PY'
import math, unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pawn = unreal.GameplayStatics.get_player_pawn(w, 0)
me = pawn.get_actor_location()
best = None
for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
    if a.get_class().get_name() == 'MIExplosive':
        l = a.get_actor_location()
        d = math.hypot(l.x - me.x, l.y - me.y)
        if best is None or d < best[0]:
            best = (d, l, a)
d, l, ex = best
ux, uy = (me.x - l.x) / max(d, 1), (me.y - l.y) / max(d, 1)
fx, fy = l.x + ux * 900, l.y + uy * 900
# the first of 16 bearings (from the player's own) with a clear line from the eye to the tank
for off in [0.0] + [sg * i * math.pi / 8 for i in range(1, 9) for sg in (1, -1)]:
    a = math.atan2(uy, ux) + off
    cx, cy = l.x + math.cos(a) * 900, l.y + math.sin(a) * 900
    try:
        hit = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(cx, cy, 160), unreal.Vector(l.x, l.y, l.z + 30),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [ex], unreal.DrawDebugTrace.NONE, True)
    except Exception:
        break
    if hit is None or not hit.to_tuple()[0]:
        fx, fy = cx, cy
        break
yaw = math.degrees(math.atan2(l.y - fy, l.x - fx))
pitch = math.degrees(math.atan2((l.z + 25) - 160.0, 900))   # street level 0, the eye about 160 cm over the feet
unreal.SystemLibrary.execute_console_command(w, "MIPose %.0f %.0f 0 %.1f %.1f" % (fx, fy, yaw, pitch))
"explosive at %.0f %.0f %.0f" % (l.x, l.y, l.z)
PY
pie_mcp py "$PIE_PY/_boom.py"; run 0.6
c "MIInput ads 1"; run 0.3; c "MIInput ads 0"; run 0.4   # ends any idle inspect
c "MIFreezeOn explosion 0.42"; c "MIBlowNearest"; sleep 6; want fp-explosion && shot fp-explosion
# what is left 1.6 s after the blast (smoke column, dust, scorch)
c "slomo 1"; run 1.18; want fp-explosion-late && shot fp-explosion-late
c "slomo 1"
tail -n +"$mark" "$log" | grep -E "First person|Effects|Error" | tail -8 | cut -c1-240
pie_stop > /dev/null
echo "FP SHOTS DONE"
