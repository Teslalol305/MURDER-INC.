#!/bin/bash
# The guide lane's proof (docs/unreal/PLAY.md, guide lane): play in editor in L_Block, a Story run, and the story's
# guidance at every step: the ground path from the start to Reel 1, under the El, the edge arrow when the step is behind,
# the path into the chop shop, inside it, out to the cage and into it, across to the truck, the marker fading near the
# truck, the hint line, Settings "Path and markers" off, the path toned down in a fight. Then (PLAY=1) the whole story
# walked by the demo director along the drawn route alone (verb guide; god mode, fights what it sees), with pictures on
# the way and MIGuide.Stats at the end.
# Run detached with L_Block open in this clone's editor:  setsid nohup bash guide-shots.sh [out] > log 2>&1 &
#   ONLY="start el behind" takes only those pictures. PLAY=0 skips the walk; PLAY=only does only the walk.
# Pictures: <out>/<name>.jpg (default $MI_LOGS/guide); ends with GUIDE SHOTS DONE.
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/guide}
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
c() { pie_con "$*" > /dev/null; }
shot() { settle "${2:-24}"; pie_shot "$out/$1.jpg"; }
want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1 "* ]]; }
demo() { printf '%s\n' "$@" > "$PIE_PY/_guide_demo.txt"; c "MIDemo.Run $PIE_PY/_guide_demo.txt"; }
stats() { local m; m=$(wc -l < "$log"); c "MIGuide.Stats"; sleep 1; tail -n +"$m" "$log" | grep -o 'MIGuide: .*' | tail -1; }
# pose <x> <y> <z> <yaw> <pitch> (Unreal cm, degrees), then two seconds of play so the guide searches from there
pose() { c "MIPose $*"; sleep 2.5; }

# A first start of a fresh clone loads for many minutes: wait for its MCP (at most 20 minutes)
for i in $(seq 1 240); do bash ./editor.sh status 2>/dev/null | grep -q "MCP ok" && break; sleep 5; done
# Play in editor asked while the editor still settles is ignored: ask again, up to five times
for k in 1 2 3 4 5; do
  mark=$(wc -l < "$log")
  pie_start > /dev/null
  for i in $(seq 1 30); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
  tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break
  sleep 10
done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "GUIDE SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
c "MIStart mission skip"
sleep 8; settle 10
demo "god 1"
sleep 1

if [ "${PLAY:-1}" != only ]; then
  # Reel 1: from the start (west end, looking east down the avenue), under the El, and turned round (the edge arrow)
  want start && { pose -3740 815 15 -4.6 -18; shot start; stats; }
  want el && { pose -1600 700 15 -27 -16; shot el; }
  want behind && { pose -2150 760 15 168 -4; shot behind; }
  # The GPU's cost of the path: ProfileGPU's translucency passes with the path shown and hidden (same view)
  if want gpu; then
    pose -2150 760 15 -12 -9; settle 20
    for on in 1 0 1 0; do
      c "MIGuide.Show $on"; settle 12; m=$(wc -l < "$log"); c "ProfileGPU"; settle 6; sleep 2
      echo "gpu path=$on: $(tail -n +"$m" "$log" | grep -iE 'Translucen' | sed 's/^.*LogRHI: *//' | head -6 | tr -s ' ' | tr '\n' '|')"
    done
    c "MIGuide.Show 1"
  fi
  # The hint: no progress for the (shortened) wait
  if want hint; then
    pose -3740 815 15 -4.6 -18; c "MIGuide.HintAfter 3"; sleep 5; shot hint; c "MIGuide.HintAfter 45"
  fi
  # Settings off: no path, no markers
  if want off; then
    c "MIGuide.Show 0"; sleep 1; shot off; c "MIGuide.Show 1"; sleep 1
  fi
  # Reel 2: from beside Reel 1, the path to the chop shop's bay door; inside the shop
  demo "secure 0"; sleep 1
  want shop && { pose -330 130 0 -95 -18; shot shop; stats; }
  want inside && { pose -150 -1350 0 -140 -20; shot inside; }
  # Reel 3: out of the shop and east along the avenue to the cage; at the cage gate
  demo "secure 1"; sleep 1
  want avenue && { pose 200 -950 15 0 -16; shot avenue; }
  want cage && { pose 3100 -800 15 -63 -16; shot cage; }
  # The truck: down the lot from the avenue; close to the truck (the marker fades)
  demo "secure 2"; sleep 1
  want lot && { pose 2800 -600 0 90 -16; shot lot; stats; }
  want truck && { pose 3000 2000 0 59 -14; shot truck; }
  # A fight: the path toned down while enemies engage
  if want fight; then
    pose 2900 -300 0 75 -18; demo "alert 80"; sleep 6; shot fight; stats
  fi
fi

if [ "${PLAY:-1}" != 0 ]; then
  # The whole story by the drawn route alone: a fresh run, the director walks the guide's route (fighting what it
  # sees on the way), grabs each reel, and walks to the truck.
  c "MIStart mission skip"; sleep 6; c "MIGuide.Reset"
  m=$(wc -l < "$log")
  demo "god 1" "auto 1" "guide 120 1" "grab 8" "guide 120 1" "grab 8" "guide 150 1" "grab 8" "guide 150 1" "waitstate complete 30"
  t0=$(date +%s); n=0
  while [ $(( $(date +%s) - t0 )) -lt 600 ]; do
    sleep 6; n=$((n + 1))
    shot "$(printf 'walk-%02d' "$n")" 6 > /dev/null
    tail -n +"$m" "$log" | grep -qE 'script done' && break
  done
  tail -n +"$m" "$log" | grep -oE 'MIDemo.*(line|guide|grab|waitstate|script done).*' | cut -c1-200 | tail -40
  stats
fi
pie_stop > /dev/null
echo "GUIDE SHOTS DONE"
