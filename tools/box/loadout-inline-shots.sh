#!/bin/bash
# The Loadout with its attachments on the screen (docs/unreal/LOADOUT.md 2.6a), through the player's eyes: play in editor
# on the open map, a gun picked and parts fitted, one picture per state at each viewport size. Run detached:
#   setsid nohup bash loadout-inline-shots.sh [out_dir] ["1920x1080 1280x720"] > log 2>&1 &
# Pictures: <out>/inline-<size>-<state>.jpg  (rack: the CHOPPER picked, its slots; parts: the STICK with a scope, a
# suppressor and a grip fitted, the muzzle slot chosen and the keys in the panel; look: a part looked at; none: a gun
# with no slots).
out=${1:-/project/ue/logs/shots}; sizes=${2:-"1920x1080 1280x720"}
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
key() { pie_con "MIKey $*" > /dev/null; settle 3; }
pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "INLINE SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4
settle 20
for size in $sizes; do
  w=${size%x*}; h=${size#*x}; p=$out/inline-$size
  for i in 1 2 3; do pie_con "MIViewSize $w $h" > /dev/null; settle 6; done
  tail -n +"$mark" "$log" | grep -o 'MIViewSize: viewport.*' | tail -1
  fe gearup; settle 20; fe next; settle 40; ui_shot "$p-arrive.jpg"
  fe carry stick; fe carry stretch; fe carry shorty; fe focusgun stick; settle 40; ui_shot "$p-rack.jpg"
  fe benchslot optic; fe fit scope; fe benchslot muzzle; fe fit silencer; fe benchslot underbarrel; fe fit grip_vertical
  fe benchslot muzzle; settle 60; ui_shot "$p-parts.jpg"
  fe preview compensator; settle 40; ui_shot "$p-look.jpg"
  fe carry chopper; settle 40; ui_shot "$p-chopper.jpg"
  fe carry nine; settle 40; ui_shot "$p-nine.jpg"
  key Escape; key Escape; fe gearup; settle 10
done
grep -E 'LogMI' "$log" | grep -E 'MIMenu|Set-up|Front end|MIViewSize|Error' | tail -14
pie_stop > /dev/null
echo "INLINE SHOTS DONE"
