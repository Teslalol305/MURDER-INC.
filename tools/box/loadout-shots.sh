#!/bin/bash
# The set-up flow through the player's eyes (docs/unreal/LOADOUT.md 8.5 picture review): play in editor on the open
# map; first a pad walk with real key events through Slate (MIKey: Start is Next on every set-up screen), then one
# picture per screen with the Slate UI at each viewport size (MIViewSize resizes the window around the game viewport),
# then the four-slot bar and the weapon wheel in a run. Run detached (about 6 minutes for three sizes):
#   setsid nohup bash loadout-shots.sh [out_dir] ["1920x1080 2560x1080 3840x2160"] > log 2>&1 &
# Pictures: <out>/loadout-<size>-<screen>.jpg, and loadout-hud.jpg, loadout-wheel.jpg at 1920 x 1080.
out=${1:-/project/ue/logs/shots}; sizes=${2:-"1920x1080 2560x1080 3840x2160"}
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
key() { pie_con "MIKey $*" > /dev/null; settle 2; }

pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "LOADOUT SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4
settle 20
# The pad walk, every press a Slate key event, from Crew (Gear up: a returning player's Start on Home starts the run):
# Crew -> Loadout -> Block & Style -> Briefing with Start, back with B, the View+Start chord, then the keyboard: Esc
# twice, Tab twice to Next on Loadout, Enter.
fe gearup; settle 4
for k in Gamepad_Special_Right Gamepad_Special_Right Gamepad_Special_Right; do key "$k"; done
key Gamepad_FaceButton_Right; key Gamepad_FaceButton_Right
key "Gamepad_Special_Left down"; key Gamepad_Special_Right; key "Gamepad_Special_Left up"
key Escape; key Escape; key Tab; key Tab; key Enter
echo "KEY WALK:"; tail -n +"$mark" "$log" | grep -o 'MIKey .*' | head -20

for size in $sizes; do
  w=${size%x*}; h=${size#*x}; p=$out/loadout-$size
  for i in 1 2 3; do pie_con "MIViewSize $w $h" > /dev/null; settle 6; done
  tail -n +"$mark" "$log" | grep -o 'MIViewSize: viewport.*' | tail -1
  fe home; settle 30; ui_shot "$p-home.jpg"
  fe gearup; settle 30; ui_shot "$p-crew.jpg"
  fe next; fe carry stick; fe carry stretch; fe carry shorty; fe focusgun stick; settle 30; ui_shot "$p-rack.jpg"
  fe bench stick; fe benchslot optic; fe fit scope; fe benchslot muzzle; fe fit silencer; fe benchslot underbarrel; fe fit grip_vertical
  fe benchslot laser; fe fit laser; fe benchslot optic; fe preview scope; settle 40; ui_shot "$p-bench-optic.jpg"
  fe benchslot muzzle; settle 30; ui_shot "$p-bench-muzzle.jpg"
  fe benchslot underbarrel; settle 30; ui_shot "$p-bench-grip.jpg"
  fe done; fe next; fe time day; settle 30; ui_shot "$p-where.jpg"
  fe next; settle 40; ui_shot "$p-briefing.jpg"
done
for i in 1 2 3; do pie_con "MIViewSize 1920 1080" > /dev/null; settle 6; done
fe hit; sleep 10; settle 30; ui_shot "$out/loadout-hud.jpg"
pie_con "MIInput swap 1" > /dev/null; sleep 1; pie_con "MIInput wheelx 0.9" > /dev/null; settle 15; ui_shot "$out/loadout-wheel.jpg"
pie_con "MIInput swap 0" > /dev/null
grep -E 'LogMI' "$log" | grep -E 'MIMenu|Set-up|Front end|MIViewSize|Error' | tail -14
pie_stop > /dev/null
echo "LOADOUT SHOTS DONE"
