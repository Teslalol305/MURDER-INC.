#!/bin/bash
# The guns on the stage and on the Workbench, every gun and every part (weapons round 4 proof pictures; LOADOUT.md 2.10).
# Play in editor on the open map (editor.sh start /Game/Maps/L_Block), the set-up screens at 1920 x 1080, then per gun:
#   r4-rack-<gun>.jpg                    the Loadout screen, that gun focused, factory build (stage only)
#   r4-bench-<gun>.jpg                   the Workbench, the first slot focused, factory build
#   r4-bench-<gun>-<slot>-<part>.jpg     that part fitted (alone), the camera on its mount
#   r4-bench-<gun>-fitted.jpg            the first part of every offered slot fitted at once
#   r4-ui-<gun>-<slot>-<part>.jpg        with PARTS=ui: the same with the Slate screen (effect lines, bars)
# Every picture is the stage (HighResShot of the game view); the "ui" ones are MIShot (the game viewport widget).
# Usage: setsid nohup bash bench-shots.sh [out_dir] > log 2>&1 &            (about 20 s a picture)
#   GUNS="chopper nine shorty stick stretch rattler"   the guns (default: every gun the data names)
#   PARTS=0   only the rack and the whole-gun pictures;  PARTS=ui   also the pictures with the Slate screen
#   ONLY="shorty:optic:red_dot chopper:muzzle:suppressor"   only those gun:slot:part pictures
# The gun / slot / part list comes from guns.json and attachments.json (offered or not: a combination the game does
# not offer is refused by the front end and the picture then repeats the previous one: the log says "refused").
out=${1:-/project/ue/logs/shots}
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
. ./pie.sh
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
data=$MI_PROJECT_DIR/Content/Data
settle() { local i; for i in $(seq 1 "${1:-20}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
fe() { pie_con "MIMenu fe $*" > /dev/null; }
ui_shot() {
  local png=$MI_LOGS/_uishot.png i
  rm -f "$png"
  pie_con "MIShot $png" > /dev/null
  for i in 1 2 3 4 5 6; do [ -f "$png" ] && break; settle 1; done
  [ -f "$png" ] || { echo "UI SHOT FAILED: $1"; return 1; }
  "$(mi_python)" -c "from PIL import Image; Image.open('$png').convert('RGB').save('$1', quality=86)" && echo "UI SHOT $1"
}
want() { [ -z "${ONLY:-}" ] || [[ " $ONLY " == *" $1 "* ]]; }

# gun slot part lines from the data: the slots in compatibility order, every option that is not the factory part
plan=$("$(mi_python)" - "$data" <<'PY'
import json, sys
d = sys.argv[1]
g = json.load(open(d + "/guns.json"))
a = json.load(open(d + "/attachments.json"))
for gun in g["roster"]:
    row = a["compatibility"].get(gun) or {}
    for slot, c in row.items():
        if not isinstance(c, dict):
            continue
        for opt in c.get("options", []):
            part = a["attachments"].get(opt, {})
            if part.get("baseline"):
                continue
            print(gun, slot, opt)
PY
)
guns=${GUNS:-$(echo "$plan" | awk '{print $1}' | awk '!s[$0]++' | tr '\n' ' ')}
[ -n "$guns" ] || guns=$("$(mi_python)" -c "import json; print(' '.join(json.load(open('$data/guns.json'))['roster']))")

pie_start > /dev/null
for i in $(seq 1 60); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "BENCH SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 20
for i in 1 2 3; do pie_con "MIViewSize 1920 1080" > /dev/null; settle 6; done
fe home; fe gearup; fe next; settle 10

for g in $guns; do
  # the rack: the gun focused (carried when there is a free slot), factory build, stage only
  want "$g" || want "$g:rack" || [ -z "${ONLY:-}" ] || continue
  fe carry "$g"; fe focusgun "$g"; settle 30
  pie_shot "$out/r4-rack-$g.jpg"
  fe bench "$g"; settle 30
  pie_shot "$out/r4-bench-$g.jpg"
  [ "${PARTS:-1}" = 0 ] && { fe done; continue; }
  first=""
  while read -r pg slot part; do
    [ "$pg" = "$g" ] || continue
    want "$g:$slot:$part" || [ -z "${ONLY:-}" ] || continue
    fe benchslot "$slot"; fe fit "$part"; settle 40
    pie_shot "$out/r4-bench-$g-$slot-$part.jpg"
    [ "${PARTS:-1}" = ui ] && ui_shot "$out/r4-ui-$g-$slot-$part.jpg"
    first="$first $slot:$part"
    fe fit factory
  done <<< "$plan"
  # fitted whole: the first part of every offered slot at once
  seen=""
  for sp in $first; do
    slot=${sp%%:*}; part=${sp#*:}
    [[ " $seen " == *" $slot "* ]] && continue
    seen="$seen $slot"
    fe benchslot "$slot"; fe fit "$part"
  done
  settle 40
  pie_shot "$out/r4-bench-$g-fitted.jpg"
  # back to the factory build: one fit factory per slot
  for sp in $seen; do fe benchslot "$sp"; fe fit factory; done
  fe done
done
grep -E 'LogMI' "$log" | tail -n +"$mark" | grep -E 'MIMenu fe .*refused|Gun assembly|Error' | sort | uniq -c | head -20
pie_stop > /dev/null
echo "BENCH SHOTS DONE"
