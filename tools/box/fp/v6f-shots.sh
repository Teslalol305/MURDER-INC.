#!/bin/bash
# The pictures of the v6 finish pass (docs/unreal/READY.md, "v6 finish"): play in editor on L_Block, the Slate screens and
# the HUD read back with MIShot (as loadout-shots.sh). Run detached with L_Block open (editor.sh start /Game/Maps/L_Block):
#   setsid nohup bash v6f-shots.sh [out_dir] > log 2>&1 &
# Pictures (1920 x 1080), <out>/v6f-<name>.jpg:
#   next-disabled          Loadout with no gun carried: the NEXT button's label (POLISH.md 3)
#   bench-stretch-factory  the STRETCH's Workbench, muzzle slot, nothing fitted
#   bench-stretch-fit      the same with the suppressor fitted: the frame holds it (PLAY.md E8)
#   bench-stretch-removed  after the removal (Factory): the stage shows the gun without it (PLAY.md E7)
#   bench-nine-fit         the NINE's Workbench with its suppressor
#   run-card               the first second of a Story run: the location card on its plate (POLISH.md 5 and 6)
#   run-hud                eight seconds in: objective, weapon strip, health at the frame's scale
out=${1:-/project/ue/logs/v6f}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
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
  "$(mi_python)" -c "from PIL import Image; Image.open('$png').convert('RGB').save('$out/v6f-$1.jpg', quality=88)" && echo "UI SHOT v6f-$1"
}
fe() { pie_con "MIMenu fe $*" > /dev/null; }
pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "V6F SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 20
for i in 1 2 3; do pie_con "MIViewSize 1920 1080" > /dev/null; settle 4; done
fe home; fe gearup; fe next; settle 15
for n in 1 2 3 4; do fe empty $n; done
settle 15; ui_shot next-disabled
fe slot 1 stretch; fe slot 2 nine; settle 10
fe bench stretch; fe benchslot muzzle; settle 25; ui_shot bench-stretch-factory
fe fit suppressor; settle 40; ui_shot bench-stretch-fit
fe fit factory; settle 40; ui_shot bench-stretch-removed
fe done; fe bench nine; fe benchslot muzzle; fe fit suppressor_pistol; settle 40; ui_shot bench-nine-fit
fe done; fe next; fe time day; fe next; fe mode mission; fe difficulty hustler; fe hit
sleep 1.2; settle 3; ui_shot run-card
sleep 7; settle 10; ui_shot run-hud
pie_stop > /dev/null
echo "V6F SHOTS DONE"
