#!/bin/bash
# The story guidance when the reels are taken out of the radio's order (docs/unreal/PLAY.md, guide lane): the guidance
# points at the first reel not taken, then the truck, so a player who takes another reel first is led on new legs:
# from the cage to Reel 1, from Reel 1 to the cage, from the chop shop to Reel 1 and from the chop shop to the truck.
# Play in editor in L_Block, a Story run, reels taken with the demo director's secure verb, the player posed where it
# would stand after the grab, and a picture with the step line, the marker and the ground path; MIGuide.Stats after each.
# Run detached with L_Block open in this clone's editor:  setsid nohup bash guide-orders.sh [out] > log 2>&1 &
#   ONLY="b1 c2" takes only those pictures. Pictures: <out>/<name>.jpg (default $MI_LOGS/guide-orders); ends with
#   GUIDE ORDERS DONE.
#   b (Reel 3 first):  b1 in the cage after Reel 3, looking at the gate (step Reel 1); b2 on the avenue on the way west;
#                      b3 in the chop shop after Reels 3, 1, 2 (step the truck)
#   c (Reel 2 first):  c1 in the chop shop after Reel 2 (step Reel 1); c2 at Reel 1 after Reels 2, 1 (step Reel 3);
#                      c3 the same, under fire (the path toned down)
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/guide-orders}
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
c() { pie_con "$*" > /dev/null; }
shot() { settle "${2:-24}"; pie_shot "$out/$1.jpg"; }
want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1 "* ]]; }
demo() { printf '%s\n' "$@" > "$PIE_PY/_guide_demo.txt"; c "MIDemo.Run $PIE_PY/_guide_demo.txt"; }
stats() { local m; m=$(wc -l < "$log"); c "MIGuide.Stats"; sleep 1; echo "$1: $(tail -n +"$m" "$log" | grep -o 'MIGuide: .*' | tail -1)"; }
pose() { c "MIPose $*"; sleep 3; }
fresh() { c "MIStart mission skip"; sleep 8; settle 6; c "MIGuide.Reset"; demo "god 1"; sleep 1; }

for i in $(seq 1 240); do bash ./editor.sh status 2>/dev/null | grep -q "MCP ok" && break; sleep 5; done
for k in 1 2 3 4 5; do
  mark=$(wc -l < "$log")
  pie_start > /dev/null
  for i in $(seq 1 30); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
  tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break
  sleep 10
done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "GUIDE ORDERS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done

# b: Reel 3 (the cage) first
fresh
demo "secure 2"; sleep 1
want b1 && { pose 3350 -2000 15 115 -14; shot b1; stats b1; }
want b2 && { pose 1600 -350 15 175 -14; shot b2; stats b2; }
demo "secure 0"; sleep 1; demo "secure 1"; sleep 1
want b3 && { pose -950 -1950 0 80 -14; shot b3; stats b3; }

# c: Reel 2 (the chop shop) first
fresh
demo "secure 1"; sleep 1
want c1 && { pose -950 -1950 0 80 -14; shot c1; stats c1; }
demo "secure 0"; sleep 1
want c2 && { pose -330 130 15 -25 -14; shot c2; stats c2; }
if want c3; then
  demo "alert 80"; sleep 6; shot c3; stats c3
fi
tail -n +"$mark" "$log" | grep -E 'Ensure|Error' | tail -5
pie_stop > /dev/null
echo "GUIDE ORDERS DONE"
