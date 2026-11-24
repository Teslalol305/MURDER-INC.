#!/bin/bash
# The fix pass's proof (docs/unreal/shots/fix-*.jpg, 2026-11-24): play in editor in L_Block (open it first), the set-up
# made on the set-up screens (CHOPPER, NINE, STICK), day, Hustler, Story. Pictures:
#   fix-loadout      the Loadout screen: the dressed stage and the veil's smooth edge (UI read back)
#   fix-briefing     the Briefing over the street: the veil's edge across sky and buildings
#   fix-hud          the run's start with the health band
#   fix-fire         frozen 0.03 s after a CHOPPER round at the hip (flash, light on the forearm, casing)
#   fix-fire-ads     the same aimed (the flash on the muzzle, not over the rear sight)
#   fix-chopshop     the Chop Shop floor round reel 2, from the door side and (2) from the east
#   fix-pause        the pause card
#   fix-cage         where the nav walk from the start to reel 3 ended (fixpass-cage.txt), looking on
#   fix-debrief      the debrief card after extraction (fixpass-debrief.txt), pursuers frozen
# Run detached: setsid nohup bash fp/fixpass-shots.sh [out] > log 2>&1 &   Ends with FIX SHOTS DONE. FROM=cage: only the
# set-up screens, then the Cage walk and the debrief.
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/fixpass}
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
fe() { pie_con "MIMenu fe $*" > /dev/null; }
c() { pie_con "$*" > /dev/null; }
run() { c "MIFreezeAfter $1"; sleep "$(python3 -c "print(max(2.0, $1 * 3.0 + 1.5))")"; }
ui_shot() {
  local png=$MI_LOGS/_uishot.png i
  rm -f "$png"
  c "MIShot $png"
  for i in 1 2 3 4 5 6; do [ -f "$png" ] && break; pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done
  [ -f "$png" ] || { echo "UI SHOT FAILED: $1"; return 1; }
  "$(mi_python)" -c "from PIL import Image; Image.open('$png').convert('RGB').save('$out/$1.jpg', quality=86)" && echo "UI SHOT $1"
}
shot() { settle "${2:-30}"; pie_shot "$out/$1.jpg"; }
fire_frozen() { c "MIFreezeOn fire ${FREEZE:-0.03}"; c "MIInput fire 1"; sleep 3; c "MIInput fire 0"; }
demo() { local m i; m=$(wc -l < "$log"); c "slomo 1"; c "MIDemo.Run $PWD/fp/$1"; for i in $(seq 1 "${2:-60}"); do settle 3; sleep 1; tail -n +"$m" "$log" | grep -q "MIDemo: .*script done" && break; done; tail -n +"$m" "$log" | grep "MIDemo:" | grep -v "event enemy" | tail -8 | sed 's/.*MIDemo:/MIDemo:/' | cut -c1-200; }

pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "FIX SHOTS FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
fe home; fe gearup; fe next
fe slot 1 chopper; fe slot 2 nine; fe slot 3 stick; fe empty 4
settle 40; ui_shot fix-loadout
fe time day; fe briefing
settle 40; ui_shot fix-briefing
fe mode mission; fe difficulty hustler; fe hit
sleep 10; settle 10
c "log LogMI Verbose"
if [ "${FROM:-}" != cage ]; then
run 1.0; shot fix-hud
c "MIPose -2900 80 0 0 -3"; run 1.0
fire_frozen; shot fix-fire
c "slomo 1"; run 1.0
c "MIInput ads 1"; run 1.0
fire_frozen; shot fix-fire-ads
c "slomo 1"; c "MIInput ads 0"; run 0.5
c "MIPose -1000 -1560 0 -80 -32"; run 1.0; shot fix-chopshop
c "MIPose -700 -1700 0 -125 -30"; run 1.0; shot fix-chopshop2
c "MIPose -800 -2068 0 -151 -40"; run 1.0; shot fix-chopshop3   # in front of reel 2's case, as the review's r08
c "MIPauseKey"; settle 20; ui_shot fix-pause
c "MIMenu confirm"; settle 10   # Resume (the pause card takes the key while it is up)
fi
c "MIPose 0 0 0 0 0"; run 0.5
demo fixpass-cage.txt 90
echo "after the Cage walk (reel 3 at 3525 -2250): $(pie_state | grep MIPlayerCharacter)"
run 0.5; shot fix-cage
demo fixpass-debrief.txt 120
settle 20; ui_shot fix-debrief
tail -n +"$mark" "$log" | grep -E "Hold:|Error|missing usage" | sort | uniq -c | sort -rn | head -8 | cut -c1-220
pie_stop > /dev/null
echo "FIX SHOTS DONE $out"
