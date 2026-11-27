#!/bin/bash
# SMOOTH.md v8: engine start-up times of runs, in seconds from the game log's first stamped line:
#   open (the bundled pipeline cache opened), saved (the Vulkan driver-cache file written), pso done, engine init, probe (the game's first MICloudProbe line)
#   st.sh <run>...   (runs under /project/ue/smooth/v8/runs)
for r in "$@"; do
  L=/project/ue/smooth/v8/runs/$r/game.log; [ -f $L ] || L=/project/ue/smooth/v8/runs/$r/abs.log
  python3 -I - "$L" "$r" <<'PY'
import sys,re
L,r=sys.argv[1:3]
def ts(l):
    m=re.match(r'\[(\d+)\.(\d+)\.(\d+)-(\d+)\.(\d+)\.(\d+):(\d+)\]',l)
    if not m: return None
    y,mo,d,h,mi,s,ms=map(int,m.groups()); return h*3600+mi*60+s+ms/1000
first=None; marks={}
keys={'open':'Opened FPipelineCacheFile','saved':'Saved device pipeline cache','pso done':'Finished, no jobs remaining','engine init':'Game Engine Initialized','probe':'MICloudProbe fps='}
for l in open(L,errors='replace'):
    t=ts(l)
    if t is None: continue
    if first is None: first=t
    for k,v in keys.items():
        if v in l and k not in marks: marks[k]=t
print(r, ' '.join('%s=%.2f'%(k,marks[k]-first) for k in keys if k in marks))
PY
done
