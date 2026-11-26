#!/bin/bash
# The Crew screen (the first 3D thing a new player sees), in play in editor: crew-home.jpg, crew-1.jpg, crew-2.jpg.
# Run detached with L_Block open:  setsid nohup bash crew-shots.sh [out] > log 2>&1 &
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/crew}; mkdir -p "$out"
log=$MI_LOGS/editor.log
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
fe() { pie_con "MIMenu fe $*" > /dev/null; }
c() { pie_con "$*" > /dev/null; }
for k in 1 2 3 4 5; do
  mark=$(wc -l < "$log"); pie_start > /dev/null
  for i in $(seq 1 30); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
  tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break
  sleep 10
done
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
fe home; sleep 2; settle 20; pie_shot "$out/crew-home.jpg"
fe gearup; sleep 2; settle 40; pie_shot "$out/crew-1.jpg"
sleep 3; settle 30; pie_shot "$out/crew-2.jpg"
pie_stop > /dev/null
echo "CREW SHOTS DONE"
