#!/bin/bash
# The merged tree through the player's eyes: Canal Street and Midtown with their Goons (the nav layers) and the truck.
# Typed code of a cleared Block opens Canal Street; travel; a fight picture; the live Goons (MICampaign goons); the
# truck to the end (MICampaign finish) and the Canal debrief; Next to Midtown; the fight and its roofs; the Midtown reels
# in (MICampaign reels) and the truck rolling in; the Midtown debrief. Run detached (about 6 minutes):
#   MI_MCP_PORT=8011 setsid nohup bash merged-shots.sh [out_dir] > log 2>&1 &
# The editor must have /Game/Maps/L_Block loaded. Pictures: <out>/merged-<name>.jpg
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
wait_log 'Play in editor total start time' 40 || { echo "MERGED SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 20
for i in 1 2 3; do pie_con "MIViewSize 1920 1080" > /dev/null; settle 6; done
fe gearup; settle 4; fe next; fe next; fe time day; settle 20
fe code 47YZ-MB30; settle 20
fe level chinatown; fe mode mission; fe difficulty hustler; settle 10
fe next; settle 20; fe hit; sleep 25; settle 20
echo "CANAL:"; tail -n +"$mark" "$log" | grep -E "Game: booted|Campaign|Error" | tail -4 | cut -c1-220
sleep 25; settle 30; echo "CANAL goons:"; goons; ui_shot "$out/merged-canal-fight.jpg"
pie_con "MICampaign finish" > /dev/null; sleep 12; settle 30; ui_shot "$out/merged-canal-debrief.jpg"
pie_con "MIMenu confirm" > /dev/null; sleep 30; settle 30
echo "MIDTOWN:"; tail -n +"$mark" "$log" | grep -E "Game: booted|Campaign|Error" | tail -4 | cut -c1-220
sleep 30; settle 30; echo "MIDTOWN goons:"; goons 20; ui_shot "$out/merged-midtown-fight.jpg"
pie_con "MICampaign reels" > /dev/null; sleep 2; settle 20; ui_shot "$out/merged-midtown-truck-roll.jpg"
sleep 2; settle 10; ui_shot "$out/merged-midtown-truck-roll2.jpg"
pie_con "MICampaign finish" > /dev/null; sleep 12; settle 30; ui_shot "$out/merged-midtown-debrief.jpg"
tail -n +"$mark" "$log" | grep -E "Campaign|Error|Fatal|crash" | tail -12 | cut -c1-240
pie_stop > /dev/null
echo "MERGED SHOTS DONE"
