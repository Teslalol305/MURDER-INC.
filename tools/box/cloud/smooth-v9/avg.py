# Measurer: mean frame, game-thread, render-thread and GPU time of a run from 8 s. python3 avg.py <run dir>...
import csv,glob,sys
csv.field_size_limit(10**9)
for d in sys.argv[1:]:
    f=glob.glob(d+'/*.csv')[0]; rows=list(csv.reader(open(f,errors='replace')))
    h=[r for r in rows if r and r[0]=='EVENTS'][-1]; c={n:i for i,n in enumerate(h)}
    t=0; S={'GameThreadTime':[],'RenderThreadTime':[],'GPUTime':[],'FrameTime':[]}
    for r in rows:
        if not r or r[0]=='EVENTS' or r[0].startswith('[') or len(r)<=c['FrameTime']: continue
        try: v={k:float(r[c[k]]) for k in S}
        except: continue
        if t>=8:
            for k in S: S[k].append(v[k])
        t+=v['FrameTime']/1000
    m={k:sum(x)/len(x) for k,x in S.items()}
    gp=sorted(S['GPUTime'])
    print('%-12s frame %.2f game %.2f render %.2f gpu %.2f (gpu p99 %.1f) fps %.1f'%(d,m['FrameTime'],m['GameThreadTime'],m['RenderThreadTime'],m['GPUTime'],gp[int(len(gp)*.99)],1000/m['FrameTime']))
