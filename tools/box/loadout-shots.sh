#!/bin/bash
# The set-up flow through the player's eyes (docs/unreal/LOADOUT.md 8.5 picture review): play in editor on the open
# map, then one picture per screen with the Slate UI (Home, Crew, Loadout, Workbench, Block & Style, Briefing), the
# four-slot bar and the weapon wheel in a run. Run detached (about 3 minutes):
#   setsid nohup bash loadout-shots.sh [out_dir] [overlay.json] > log 2>&1 &
# overlay.json (dev only, never committed): MISetup overlay patches pack statuses and meshes in memory, so the pack
# rifles and parts imported on the box can be shown before the pack import writes guns.json / attachments.json.
out=${1:-/project/ue/logs/shots}; overlay=${2:-}
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
. ./pie.sh
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
settle() { local i; for i in $(seq 1 "${1:-20}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
# A picture with the UI: MIShot reads back the game viewport widget with its Slate screens and the HUD.
ui_shot() {
  local png=$MI_LOGS/_uishot.png i
  rm -f "$png"
  pie_con "MIShot $png" > /dev/null
  for i in 1 2 3 4 5 6; do [ -f "$png" ] && break; pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done
  [ -f "$png" ] || { echo "UI SHOT FAILED: $1"; return 1; }
  "$(mi_python)" -c "from PIL import Image; Image.open('$png').convert('RGB').save('$1', quality=86)" && echo "UI SHOT $1"
}
fe() { pie_con "MIMenu fe $*" > /dev/null; }

pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "LOADOUT SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4
[ -n "$overlay" ] && pie_con "MISetup overlay $overlay" > /dev/null
settle 30
ui_shot "$out/loadout-home.jpg"
fe gearup; settle 30; ui_shot "$out/loadout-crew.jpg"
fe next; fe carry stick; fe carry stretch; fe swap 2 4; fe focusgun stick; settle 30
ui_shot "$out/loadout-rack.jpg"
fe bench stick; fe benchslot optic; fe fit scope; fe benchslot muzzle; fe fit silencer; fe benchslot underbarrel; fe fit grip_vertical
fe benchslot laser; fe fit laser; fe benchslot optic; fe preview scope; settle 40
ui_shot "$out/loadout-workbench.jpg"
fe done; fe next; fe time day; settle 30; ui_shot "$out/loadout-where.jpg"
fe next; settle 40; ui_shot "$out/loadout-briefing.jpg"
fe hit; sleep 10; settle 30; ui_shot "$out/loadout-hud.jpg"
pie_con "MIInput swap 1" > /dev/null; sleep 1; pie_con "MIInput wheelx 0.9" > /dev/null; settle 15; ui_shot "$out/loadout-wheel.jpg"
pie_con "MIInput swap 0" > /dev/null
grep -E 'LogMI' "$log" | tail -n +1 | grep -E 'MIMenu|Set-up|overlay|Error' | tail -12
pie_stop > /dev/null
echo "LOADOUT SHOTS DONE"
