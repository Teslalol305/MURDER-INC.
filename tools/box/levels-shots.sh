#!/bin/bash
# The three levels through the player's eyes: the Block & Style screen with its level cards locked, then with the code of a
# cleared Block typed (Canal Street open), then a travel to Canal Street, the run there, and the debrief's Next button.
# Play in editor on the open map; run detached (about 4 minutes):
#   MI_MCP_PORT=8002 setsid nohup bash levels-shots.sh [out_dir] > log 2>&1 &
# Pictures: <out>/levels-<name>.jpg
out=${1:-/project/ue/logs/shots}
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
. ./pie.sh
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
settle() { local i; for i in $(seq 1 "${1:-20}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
ui_shot() {
  local png=$MI_LOGS/_uishot.png i
  rm -f "$png"
  pie_con "MIShot $png" > /dev/null
  for i in 1 2 3 4 5 6; do [ -f "$png" ] && break; pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done
  [ -f "$png" ] || { echo "UI SHOT FAILED: $1"; return 1; }
  "$(mi_python)" -c "from PIL import Image; Image.open('$png').convert('RGB').save('$1', quality=86)" && echo "UI SHOT $1"
}
fe() { pie_con "MIMenu fe $*" > /dev/null; }
wait_log() { local i; for i in $(seq 1 "${2:-30}"); do tail -n +"$mark" "$log" | grep -q "$1" && return 0; sleep 2; done; return 1; }

pie_start > /dev/null
wait_log 'Play in editor total start time' 40 || { echo "LEVELS SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 20
for i in 1 2 3; do pie_con "MIViewSize 1920 1080" > /dev/null; settle 6; done
fe gearup; settle 4; fe next; fe next; fe time day; settle 30; ui_shot "$out/levels-where-locked.jpg"
fe level chinatown; settle 10   # refused: locked
fe code 47YZ-MB30; settle 30; ui_shot "$out/levels-where-code.jpg"
fe level chinatown; fe mode mission; fe difficulty hustler; settle 10
fe next; settle 30; ui_shot "$out/levels-briefing.jpg"
fe hit; settle 3; ui_shot "$out/levels-loading.jpg"
sleep 25; settle 20
echo "AFTER TRAVEL:"; tail -n +"$mark" "$log" | grep -E "Game: booted|Travel|Campaign|Set-up:|Error|MIMenu fe" | tail -12 | cut -c1-260
settle 40; ui_shot "$out/levels-canal-run.jpg"
# Complete Canal Street (dev command), the debrief with Next, then the travel to Midtown.
sleep 12; pie_con "MICampaign finish" > /dev/null; sleep 9; settle 30; ui_shot "$out/levels-debrief.jpg"
pie_con "MIMenu confirm" > /dev/null; sleep 30; settle 30
echo "AFTER NEXT:"; tail -n +"$mark" "$log" | grep -E "Game: booted|Campaign|Travel|Error" | tail -6 | cut -c1-260
ui_shot "$out/levels-midtown-run.jpg"
pie_stop > /dev/null
echo "LEVELS SHOTS DONE"
