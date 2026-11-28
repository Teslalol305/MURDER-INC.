#!/bin/bash
# (Second pass) The merged tree through the player's eyes: Canal Street and Midtown with their Goons (the nav layers) and the truck.
# Typed code of a cleared Block opens Canal Street; travel; a fight picture; the live Goons (MICampaign goons); the
# truck to the end (MICampaign finish) and the Canal debrief; Next to Midtown; the fight and its roofs; the Midtown reels
# in (MICampaign reels) and the truck rolling in; the Midtown debrief. Run detached (about 6 minutes):
#   MI_MCP_PORT=8011 setsid nohup bash roof-shots.sh [out_dir] > log 2>&1 &
# The editor must have /Game/Maps/L_Block loaded. Pictures: <out>/roof-<name>.jpg
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
goons() { local m; m=$(wc -l < "$log"); pie_con "MICampaign goons" > /dev/null; sleep 2; tail -n +"$m" "$log" | grep "MICampaign goons" | cut -c1-200 | tail -${1:-14}; }

pie_start > /dev/null
wait_log 'Play in editor total start time' 40 || { echo "ROOF SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 20
for i in 1 2 3; do pie_con "MIViewSize 1920 1080" > /dev/null; settle 6; done
fe gearup; settle 4; fe next; fe next; fe time day; settle 20
fe code 47YZ-MB30; settle 20
fe level chinatown; fe mode mission; fe difficulty hustler; settle 10
fe next; settle 20; fe hit; sleep 30; settle 20
echo "CANAL ROOF:"; pie_con "MICampaign at -12 5.7 0" > /dev/null; sleep 40; settle 20
goons; ui_shot "$out/roof-canal-roof.jpg"
sleep 30; settle 20; goons; ui_shot "$out/roof-canal-roof2.jpg"
pie_con "MICampaign finish" > /dev/null; sleep 12; pie_con "MIMenu confirm" > /dev/null; sleep 35; settle 30
echo "MIDTOWN ROOF r1:"; pie_con "MICampaign at -30 14 10" > /dev/null; sleep 40; settle 20
goons 20; ui_shot "$out/roof-midtown-roof.jpg"
echo "MIDTOWN TRUCK:"
pie_con "MICampaign reels" > /dev/null; pie_con "MICampaign truck" > /dev/null; sleep 1; settle 8; ui_shot "$out/roof-truck-0.jpg"
sleep 2; settle 8; ui_shot "$out/roof-truck-1.jpg"
sleep 2; settle 8; ui_shot "$out/roof-truck-2.jpg"
sleep 3; settle 8; ui_shot "$out/roof-truck-3.jpg"
tail -n +"$mark" "$log" | grep -E "MICampaign (at|truck|reels)|Error|Fatal" | tail -8 | cut -c1-240
pie_stop > /dev/null
echo "ROOF SHOTS DONE"
