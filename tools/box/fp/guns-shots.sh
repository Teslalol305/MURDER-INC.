#!/bin/bash
# The five own guns through the player's eyes (weapons round 4 proof pictures): play in editor in L_Block with the HUD.
# A set-up carries the guns named by GUNS (up to four, slot order), each with the optic named for it (or the irons), a
# Story run starts, and for each gun, the world's time frozen for each picture (MIFreezeAfter / MIFreezeOn):
#   r4-fp-<gun>-hip-sun     hip, on the north lane in the sun
#   r4-fp-<gun>-hip-el      hip under the El
#   r4-fp-<gun>-aim         aimed (the irons, or the optic the set-up fitted)
#   r4-fp-<gun>-reload      mid tactical reload (a few rounds spent)
#   r4-fp-<gun>-fire        0.02 s after a round (the flash lives 0.045 s)
# Run detached with L_Block open (editor.sh start /Game/Maps/L_Block):
#   setsid nohup bash guns-shots.sh [out] > log 2>&1 &
#   GUNS="chopper shorty stretch rattler"      the carried guns, slot 1 to 4 (default)
#   OPTICS="chopper=scope_4x shorty=red_dot"    gun=part pairs fitted before the run (default: none, the irons)
#   MUZZLES="stretch=suppressor"               gun=part pairs for the muzzle slot; MAGS="shorty=mag_ext_rifle" for the magazine
#   FITS="shorty=laser:laser_module stretch=underbarrel:foregrip_vertical"   gun=slot:part for any other slot
#   SHOULDERS="chopper=2,1.1,-12.4 stretch=4,1.1,-12.4"   gun=x,y,z: the arms' shoulders under the eye for that gun (console
#                                              mi.FP.Shoulders; without an entry the data's own value is used)
#   ONLY="chopper:aim shorty:fire"             only those gun:picture pairs (the set-up and the poses still run)
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/fp}
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
guns=${GUNS:-"chopper shorty stretch rattler"}
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
fe() { pie_con "MIMenu fe $*" > /dev/null; }
c() { pie_con "$*" > /dev/null; }
run() { c "MIFreezeAfter $1"; sleep "$(python3 -c "print(max(2.0, $1 * 3.0 + 1.5))")"; }
want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1:$2 "* ]]; }
shot() { settle "${3:-30}"; pie_shot "$out/r4-fp-$1-$2.jpg"; }
pick() { local pair; for pair in $2; do [ "${pair%%=*}" = "$1" ] && echo "${pair#*=}"; done; }

pie_start > /dev/null
for i in $(seq 1 60); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "GUNS SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
# the set-up: the guns in slot order, then the builds on the Workbench
fe home; fe gearup; fe next
n=1
for g in $guns; do fe slot $n $g; n=$((n + 1)); done
while [ $n -le 4 ]; do fe empty $n; n=$((n + 1)); done
for g in $guns; do
  o=$(pick "$g" "${OPTICS:-}"); m=$(pick "$g" "${MUZZLES:-}"); mg=$(pick "$g" "${MAGS:-}"); fx=$(pick "$g" "${FITS:-}")
  [ -n "$o$m$mg$fx" ] || continue
  fe bench "$g"
  [ -n "$fx" ] && { fe benchslot "${fx%%:*}"; fe fit "${fx#*:}"; }
  [ -n "$o" ] && { fe benchslot optic; fe fit "$o"; }
  [ -n "$m" ] && { fe benchslot muzzle; fe fit "$m"; }
  [ -n "$mg" ] && { fe benchslot magazine; fe fit "$mg"; }
  fe done
done
fe next; fe time day; fe next; fe mode mission; fe difficulty hustler; fe hit
sleep 10; settle 10
tail -n +"$mark" "$log" | grep -E "Set-up:|First person:" | tail -8 | cut -c1-260

slot=1
for g in $guns; do
  c "MIInput weapon$slot 1"; run 1.0; c "MIInput weapon$slot 0"
  sh=$(pick "$g" "${SHOULDERS:-}"); if [ -n "$sh" ]; then c "mi.FP.Shoulders \"${sh//,/ }\""; else c "mi.FP.Shoulders data"; fi
  # hip, in the sun on the north lane, then under the El
  c "MIPose 170 -380 0 -35 -4"; run 1.2; want $g hip-sun && shot $g hip-sun
  c "MIPose -2900 80 0 0 -3"; run 1.2; want $g hip-el && shot $g hip-el
  # aimed: the irons, or the optic the set-up fitted
  c "MIInput ads 1"; run 0.9; want $g aim && shot $g aim
  c "MIInput ads 0"; run 0.3
  # mid tactical reload: a few rounds spent, the fresh magazine on its way
  c "MIPose -2900 80 0 0 6"; c "MIInput fire 1"; run 0.3; c "MIInput fire 0"; run 0.3
  c "MIFreezeOn reload 1.2"; c "MIInput reload 1"; sleep 5; c "MIInput reload 0"; want $g reload && shot $g reload; c "slomo 1"; run 3.0
  # one frame of a burst from the hip, 0.02 s after the round
  c "MIPose -2900 80 0 0 -3"; run 0.3
  c "MIFreezeOn fire 0.02"; c "MIInput fire 1"; sleep 4; want $g fire && shot $g fire
  c "MIInput fire 0"; c "slomo 1"; run 0.6
  slot=$((slot + 1))
done
tail -n +"$mark" "$log" | grep -E "First person|Gun assembly|Error" | sort | uniq -c | tail -12 | cut -c1-240
pie_stop > /dev/null
echo "GUNS SHOTS DONE"
