# v7 prover: in an Insights window export (all threads: ExportTimingEvents with -startTime= -endTime=, no -threads), the frames with a
# period over 22 ms and the events over <ms> on every thread inside them (waits and frame markers left out).
#   python3 win.py <events csv> <timers csv> <ms>
import sys,csv,bisect
f,tf,thr=sys.argv[1],sys.argv[2],float(sys.argv[3])
name={int(r['Id']):r['Name'] for r in csv.DictReader(open(tf))}
tick=[i for i,s in name.items() if s=='FEngineLoop::Tick'][0]
rows=[]; ticks=[]
for ln in open(f):
    p=ln.split(',')
    if len(p)<6 or not p[0].isdigit(): continue
    s=float(p[2]); du=float(p[4])*1000; tid=int(p[1])
    if tid==tick: ticks.append(s)
    elif du>=thr: rows.append((s,du,int(p[0]),name.get(tid,p[1]),int(p[5])))
ticks.sort(); rows.sort()
skip=('Frame','FrameTime','FEngineLoop_UpdateTimeAndHandleMaxTickRate','Game thread tick wait time','Game thread idle time','Frame - %d (CsvFrame %d)','SceneRender- %s','GameThreadWaitForTask','Frame Sync Time')
st=[r[0] for r in rows]
for i in range(len(ticks)-1):
    a,b=ticks[i],ticks[i+1]
    if (b-a)<0.022: continue
    k=bisect.bisect_left(st,a); sub=[]
    while k<len(rows) and rows[k][0]<b:
        if rows[k][3] not in skip and not rows[k][3].startswith(('STAT_FCurl','STAT_EventLoop','Module/','FNodeClass','Create GEngine')): sub.append(rows[k])
        k+=1
    sub.sort(key=lambda r:-r[1])
    print('frame at trace %.3f s, period %.1f ms'%(a,(b-a)*1000))
    for s,du,tid,nm,d in sub[:8]: print('    %6.1f ms thread %3d d%-2d +%.1f ms  %s'%(du,tid,d,(s-a)*1000,nm))
