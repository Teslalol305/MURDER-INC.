#!/bin/bash
# Why the player's own muzzle flash never shows (polish pass): play in editor in L_Block, the set-up of fp-arms-shots.sh,
# then evidence frames (not committed) in <out>:
#   ev-fire-hip     frozen 0.02 s after a round at the hip, with the visible effect cards listed (FLASH-LIST lines)
#   ev-cvar-<k>     the same frozen frame after each console variable in PROBE_CVARS ("r.HZBOcclusion=0 ...")
#   ev-fire-ads     frozen 0.02 s after a round aimed
# Run detached with L_Block open: setsid nohup bash flash-diag.sh [out] > log 2>&1 &  (ends with FLASH DIAG DONE)
out=${1:-}
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
. ./pie.sh
out=${out:-$MI_LOGS/flash-diag}
mkdir -p "$out"
log=$MI_LOGS/editor.log
mark=$(wc -l < "$log")
settle() { local i; for i in $(seq 1 "${1:-30}"); do pie_mcp tool SceneCaptureToolset.SceneCaptureToolset.CaptureEditorViewport '{}' > /dev/null 2>&1; done; }
fe() { pie_con "MIMenu fe $*" > /dev/null; }
c() { pie_con "$*" > /dev/null; }
run() { c "MIFreezeAfter $1"; sleep "$(python3 -c "print(max(2.0, $1 * 3.0 + 1.5))")"; }
shot() { settle "${2:-30}"; pie_shot "$out/$1.jpg"; }
probe() { sed "s/^MODE = .*/MODE = \"$1\"/" fp/flash_probe.py > "$PIE_PY/_probe.py"; pie_mcp py "$PIE_PY/_probe.py" | sed "s/^/FLASH-$2: /"; }
fire_frozen() { c "MIFreezeOn fire ${1:-0.02}"; c "MIInput fire 1"; sleep 3; c "MIInput fire 0"; }

pie_start > /dev/null
for i in $(seq 1 40); do tail -n +"$mark" "$log" | grep -q 'Play in editor total start time' && break; sleep 2; done
tail -n +"$mark" "$log" | grep -m1 'Play in editor total start time' || { echo "FLASH DIAG FAILED: play in editor did not start"; exit 1; }
sleep 4; settle 10
for i in 1 2 3; do c "MIViewSize 1920 1080"; settle 4; done
fe home; fe gearup; fe next
fe slot 1 chopper; fe slot 2 nine; fe slot 3 stick; fe empty 4; fe done
fe next; fe time day; fe next; fe mode mission; fe difficulty hustler; fe hit
sleep 10; settle 10
c "log LogMI Verbose"
c "MIInput weapon1 1"; run 1.0; c "MIInput weapon1 0"
c "MIPose ${POSE:-170 -380 0 -35 -4}"; run 1.2
fire_frozen ${FREEZE:-0.02}; probe list fire-hip; shot ev-fire-hip
tail -n +"$mark" "$log" | grep -E "Flash:|Tracer:" | tail -4 | cut -c1-260
k=0
for cv in ${PROBE_CVARS:-}; do
  k=$((k + 1)); c "${cv/=/ }"; shot "ev-cvar-$k"; echo "FLASH-CVAR $k: $cv"
done
c "slomo 1"; run 1.0
c "MIInput ads 1"; run 0.8
fire_frozen ${FREEZE:-0.02}; probe list fire-ads; shot ev-fire-ads
c "slomo 1"; c "MIInput ads 0"; run 0.5
pie_stop > /dev/null
echo "FLASH DIAG DONE $out"
