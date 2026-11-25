#!/bin/bash
# The cloud budget measurements (docs/unreal/PROGRESS.md, docs/LAUNCH.md section 10), one run after another, on the
# Development package rendering off screen at 1920 x 1080, 60 fps:
#   story-cloud    the Story run of tools/box/demo/demo.txt with the Cloud profile (-MICloud)
#   story-epic     the same without it (the Epic preset of the desktop game)
#   hold-cloud     Hold the Block (hold.txt) with the Cloud profile
#   shot-cloud / shot-epic   one picture of the home screen each (shot.txt), for the before and after
# Each run's GPU samples (nvidia-smi, once a second: the whole card, other processes included), the game's own Vulkan
# heap peak (r.Vulkan.DumpMemory before it quits), the baseline before it started and the game's probe lines are
# kept in /project/ue/cloud/mem/<run>/; summary.txt has the peaks. Run as root, detached:
#   setsid nohup bash memory-runs.sh [runs...] > /project/ue/cloud/mem/log 2>&1 &
T=$(dirname "$(readlink -f "$0")"); R=/project/ue/cloud/run; M=/project/ue/cloud/mem; mkdir -p "$M"
D=$T/../demo
one() {  # name script args...
  local n=$1 s=$2; shift 2
  bash "$T/stream-test.sh" run "$s" Development -MICloudNoCard -MICloudProbe=2 -benchmark -fps=60 "$@" >/dev/null
  local pid; pid=$(cat "$R/game.pid"); local t=0
  while kill -0 "$pid" 2>/dev/null && [ $t -lt 600 ]; do sleep 5; t=$((t + 5)); done
  kill "$pid" 2>/dev/null; sleep 3
  mkdir -p "$M/$n"; cp "$R/gpu.csv" "$R/gpu-baseline.txt" "$R/game.log" "$M/$n/" 2>/dev/null
  [ -f "$R/shot.png" ] && mv "$R/shot.png" "$M/$n/shot.png"
  python3 - "$M/$n" "$n" >> "$M/summary.txt" <<'PY'
import re, sys
d, n = sys.argv[1], sys.argv[2]
base = int(open(f'{d}/gpu-baseline.txt').read().split()[0])
gpu = [int(l.split(',')[1]) for l in open(f'{d}/gpu.csv') if l.count(',') >= 2]
pr = [dict((k, float(v)) for k, v in re.findall(r'(\w+)=(-?[\d.]+)', l.split('MICloudProbe', 1)[1])) for l in open(f'{d}/game.log', errors='replace') if 'MICloudProbe' in l]
fps = [p['fps'] for p in pr if p.get('state') == 2]
# The game's own Vulkan allocations (r.Vulkan.DumpMemory before quit): the device-local heap's peak, and the
# process's usage of it from the memory-budget extension. Other processes on the card do not count here.
g = open(f'{d}/game.log', errors='replace').read() if __import__('os').path.exists(f'{d}/game.log') else ''
peaks = [float(x) for x in re.findall(r'Total Allocated [\d.]+ MB, Peak ([\d.]+) MB', g)]
use = re.findall(r'HEAP 00 \| +[\d.]+% / +([\d.]+) MB', g)
print(f"{n}: game VRAM peak (heap 0) {max(peaks, default=0):.0f} MB, budget usage at end {use[-1] if use else '?'} MB; gpu peak {max(gpu, default=0)} MiB total, baseline {base} MiB, game about {max(gpu, default=0) - base} MiB; "
      f"rss peak {max((p.get('peakRssMB', 0) for p in pr), default=0):.0f} MiB; "
      f"fps in play min {min(fps, default=0):.1f} mean {sum(fps) / max(len(fps), 1):.1f}; gpu ms max {max((p.get('gpuMs', 0) for p in pr), default=0):.1f}; "
      f"texture pool {max((p.get('poolMB', 0) for p in pr), default=0):.0f} MB; samples {len(gpu)}")
PY
}
for r in "${@:-story-epic hold-cloud shot-cloud shot-epic}"; do
  for x in $r; do
    case $x in
      story-cloud) one story-cloud "$D/demo.txt" -MICloud ;;
      story-epic) one story-epic "$D/demo.txt" ;;
      hold-cloud) one hold-cloud "$T/hold.txt" -MICloud ;;
      hold-epic) one hold-epic "$T/hold.txt" ;;
      shot-cloud) one shot-cloud "$T/shot.txt" -MICloud ;;
      shot-epic) one shot-epic "$T/shot.txt" ;;
    esac
  done
done
echo MEMORY-RUNS-DONE
