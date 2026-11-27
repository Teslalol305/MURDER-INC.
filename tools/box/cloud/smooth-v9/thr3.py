# Measurer: split the frames over 25 ms of a run (from 8 s) by which thread was busy in them:
# game (game thread >= 10 ms), render (render thread >= 15 ms), gpu (GPU >= 20 ms), else "none" (every thread idle, the frame period
# was spent waiting). python3 thr3.py <run dir>...
import csv,glob,sys
csv.field_size_limit(10**9)
print('run  secs  over25 | gamebound(g>=10) renderbound(r>=15) gpubound(gpu>=20) nonebusy | over25 per min total, game-bound per min')
for d in sys.argv[1:]:
    f=glob.glob(d+'/*.csv')[0]; rows=list(csv.reader(open(f,errors='replace')))
    h=[r for r in rows if r and r[0]=='EVENTS'][-1]; c={n:i for i,n in enumerate(h)}
    t=0; s=0; gb=rb=pb=nb=n25=0
    for r in rows:
        if not r or r[0]=='EVENTS' or r[0].startswith('[') or len(r)<=c['FrameTime']: continue
        try: ft=float(r[c['FrameTime']]); g=float(r[c['GameThreadTime']]); rt=float(r[c['RenderThreadTime']]); gp=float(r[c['GPUTime']])
        except: continue
        if t>=8:
            s+=ft/1000
            if ft>25:
                n25+=1
                if g>=10: gb+=1
                elif rt>=15: rb+=1
                elif gp>=20: pb+=1
                else: nb+=1
        t+=ft/1000
    print('%-12s %4.0f %3d | game %2d render %2d gpu %2d none %3d | %.1f/min, game-bound %.2f/min'%(d,s,n25,gb,rb,pb,nb,n25/s*60,gb/s*60))
