#!/bin/bash
# The arms proof (docs/unreal/shots/fp-arms-*.jpg): play in editor in L_Block through the player's eyes, the set-up of
# fp-shots.sh (CHOPPER, NINE, STICK). Second pass of the hands-and-tattoos work (the in-game review: "accept as proof
# only unmodified play frames"): every picture is the player's own view, nothing moved, hidden or paused:
#   fp-arms-hip-sun    CHOPPER at the hip in the sun        fp-arms-hip-el     at the hip under the El
#   fp-arms-irons      aimed through the irons               fp-arms-reload     mid tactical reload
#   fp-arms-inspect-<t> the inspect t seconds in             fp-arms-nine       the NINE at the hip
#   fp-arms-nine-ads   the NINE aimed
# plus evidence frames (not committed): ev-unlit (base colour only, the hip-sun frame) and the arms' texture residency
# (ListTextures, "MI-ARMS-TEX" lines). The first pass's close-ups that moved the arms component in front of the eye
# (fp-arms-forearm-l/r) are gone: a player never sees that view.
# Run detached with L_Block open (editor.sh start /Game/Maps/L_Block):  setsid nohup bash fp-arms-shots.sh [out] > log 2>&1 &
# Pictures: <out>/fp-arms-*.jpg (default $MI_LOGS/fp-arms); ends with FP ARMS SHOTS DONE. ONLY="fp-arms-irons ..." limits.
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/fp-arms}
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
fe() { pie_con "MIMenu fe $*" > /dev/null; }
c() { pie_con "$*" > /dev/null; }
run() { c "MIFreezeAfter $1"; sleep "$(python3 -c "print(max(2.0, $1 * 3.0 + 1.5))")"; }
shot() { settle "${2:-30}"; pie_shot "$out/$1.jpg"; }
want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1 "* ]]; }
textures() {   # the arms' textures as the renderer holds them (ListTextures: on disk vs in memory)
  local m; m=$(wc -l < "$log"); c "ListTextures"; sleep 3
  tail -n +"$m" "$log" | grep -E "T_RuleArms" | cut -c1-260 | sed "s/^/MI-ARMS-TEX $1: /"
}

pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "FP ARMS SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
fe home; fe gearup; fe next
fe slot 1 chopper; fe slot 2 nine; fe slot 3 stick; fe empty 4
fe bench stick; fe benchslot optic; fe fit scope; fe benchslot muzzle; fe fit factory; fe benchslot laser; fe fit factory
fe benchslot underbarrel; fe fit grip_vertical; fe done
fe next; fe time day; fe next; fe mode mission; fe difficulty hustler; fe hit
sleep 10; settle 10
tail -n +"$mark" "$log" | grep -E "Set-up:|First person:" | tail -5 | cut -c1-260
c "MIInput weapon1 1"; run 1.0; c "MIInput weapon1 0"

c "MIPose 170 -380 0 -35 -4"; run 1.2; want fp-arms-hip-sun && shot fp-arms-hip-sun
textures hip-sun
if [ -z "${ONLY:-}" ] || want ev; then c "viewmode unlit"; shot ev-unlit 20; c "viewmode lit"; fi
c "MIPose -2900 80 0 0 -3"; run 1.2; want fp-arms-hip-el && shot fp-arms-hip-el
c "MIInput ads 1"; run 0.8; want fp-arms-irons && shot fp-arms-irons
c "MIInput ads 0"; run 0.6
# mid tactical reload (five rounds spent, the fresh magazine on its way up)
if want fp-arms-reload; then
  c "MIPose -2900 80 0 0 6"; c "MIInput fire 1"; run 0.4; c "MIInput fire 0"; run 0.3
  c "MIFreezeOn reload 1.2"; c "MIInput reload 1"; sleep 5; c "MIInput reload 0"; shot fp-arms-reload
  c "slomo 1"; run 3.0
fi
# the inspect, in the sun, at three moments of the clip
for t in ${INSPECT_TIMES:-1.2 2.4 3.6}; do
  if want fp-arms-inspect-$t; then
    c "MIPose 170 -380 0 -35 -4"; run 0.6; c "MIInput inspect 1"; run "$t"; c "MIInput inspect 0"; shot fp-arms-inspect-$t
    c "slomo 1"; run 5.0
  fi
done
# the NINE at the hip and aimed (the solved grip: Content/Data/grips.json)
c "MIInput weapon2 1"; run 1.0; c "MIInput weapon2 0"
c "MIPose 170 -380 0 -35 -6"; run 1.2; want fp-arms-nine && shot fp-arms-nine
# evidence (not committed): the NINE at the hip with other shoulder anchors (console mi.FP.Shoulders "x y z" | off)
k=0
for s in ${NINE_SHOULDERS:-}; do
  k=$((k + 1)); c "mi.FP.Shoulders ${s//,/ }"; run 0.6; shot ev-nine-shoulders-$k; echo "MI-NINE-SHOULDERS $k: $s"
done
[ -n "${NINE_SHOULDERS:-}" ] && { c "mi.FP.Shoulders data"; run 0.4; }
c "MIInput ads 1"; run 0.8; want fp-arms-nine-ads && shot fp-arms-nine-ads
c "MIInput ads 0"; run 0.6
c "MIPose -2900 80 0 0 -3"; run 1.2; want fp-arms-nine-el && shot fp-arms-nine-el
textures end
tail -n +"$mark" "$log" | grep -E "First person: grip|Error" | tail -4 | cut -c1-240
tail -n +"$mark" "$log" | grep -E "First person: shoulders" | awk '!seen[$0]++' | tail -12 | cut -c1-200
pie_stop > /dev/null
echo "FP ARMS SHOTS DONE $out"
