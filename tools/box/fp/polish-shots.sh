#!/bin/bash
# The polish pass's proof (docs/unreal/shots/polish-*.jpg): play in editor in L_Block from the player's eye, the set-up
# made on the set-up screens (CHOPPER, NINE, STICK), day, Hustler. Unmodified play frames:
#   RUN=mission (default)
#     polish-start      the run's first view at the player start
#     polish-avenue     the avenue under the El
#     polish-lot        the lot by the IPX truck
#     polish-fire       frozen FREEZE s (0.02) after a CHOPPER round at the hip: the flash and the tracer
#     polish-fire-ads   the same aimed
#     polish-chopper-aim the CHOPPER aimed (the support fingers on the handguard)
#   RUN=holdout
#     polish-hold       Hold the Block, a wave coming in, turned onto the nearest Goon
# plus "MI-GRIP" lines (MIGripProbe: each finger's gap to the gun and the curl to contact) at the hip, aimed and
# just after a round. Run detached with L_Block open: setsid nohup bash polish-shots.sh [out] > log 2>&1 &
# Ends with POLISH SHOTS DONE. ONLY="polish-lot ..." limits the pictures.
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/polish}
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
fe() { pie_con "MIMenu fe $*" > /dev/null; }
c() { pie_con "$*" > /dev/null; }
run() { c "MIFreezeAfter $1"; sleep "$(python3 -c "print(max(2.0, $1 * 3.0 + 1.5))")"; }
want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1 "* ]]; }
shot() { want "$1" || return 0; settle "${2:-30}"; pie_shot "$out/$1.jpg"; }
grip() { c "MIGripProbe $1"; sleep 8; tail -n +"$mark" "$log" | grep "MI-GRIP $1 " | sed 's/.*MI-GRIP/MI-GRIP/' | cut -c1-200; }
fire_frozen() { c "MIFreezeOn fire ${FREEZE:-0.02}"; c "MIInput fire 1"; sleep 3; c "MIInput fire 0"; }

pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "POLISH SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
fe home; fe gearup; fe next
fe slot 1 chopper; fe slot 2 nine; fe slot 3 stick; fe empty 4; fe done
fe next; fe time day; fe next; fe mode "${RUN:-mission}"; fe difficulty hustler; fe hit
sleep 10; settle 10
c "log LogMI Verbose"
if [ "${RUN:-mission}" = holdout ]; then
  run 6.0; c "MIFaceEnemy -1"; run 0.5; shot polish-hold
else
  run 1.0; shot polish-start
  grip hip-start
  c "MIPose -2900 80 0 0 -3"; run 1.2; shot polish-avenue
  grip hip
  c "MIPose 2850 2250 0 30 -4"; run 1.2; shot polish-lot
  c "MIPose -2900 80 0 0 -3"; run 1.0
  fire_frozen; grip fire; shot polish-fire
  tail -n +"$mark" "$log" | grep -E "Flash:|Tracer:" | tail -3 | cut -c1-220
  c "slomo 1"; run 1.0
  c "MIInput ads 1"; run 1.0; shot polish-chopper-aim
  grip aim
  fire_frozen; shot polish-fire-ads
  c "slomo 1"; c "MIInput ads 0"; run 0.5
fi
pie_stop > /dev/null
echo "POLISH SHOTS DONE $out"
