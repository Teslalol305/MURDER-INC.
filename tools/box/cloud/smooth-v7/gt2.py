# v7 prover: from an Insights export of the game thread (UnrealInsights -OpenTraceFile=<trace> -NoUI -AutoQuit
# -ExecOnAnalysisCompleteCmd="TimingInsights.ExportTimingEvents <name>-gt.csv -threads=GameThread -columns=ThreadId,TimerId,StartTime,EndTime,Duration,Depth"
# and the same with TimingInsights.ExportTimers <name>-timers.csv; one command per call): per frame (FEngineLoop::Tick) the game-thread time
# by timer name at one depth, and which timers are far above their median in the frames with a period over 22 ms.
#   python3 gt2.py <name> [depth=3]      (files under /tmp/v7p/ins/)
import sys, csv, bisect, statistics, collections
n=sys.argv[1]; D=int(sys.argv[2]) if len(sys.argv)>2 else 3
name={}
for r in csv.DictReader(open(f'/tmp/v7p/ins/{n}-timers.csv')): name[int(r['Id'])]=r['Name']
tick=[i for i,s in name.items() if s=='FEngineLoop::Tick'][0]
ticks=[]; ev=[]
for ln in open(f'/tmp/v7p/ins/{n}-gt.csv'):
    p=ln.split(',')
    if len(p)<6 or not p[0].isdigit(): continue
    tid=int(p[1]); d=int(p[5])
    if tid==tick: ticks.append(float(p[2]))
    elif d==D or d==D+1: ev.append((float(p[2]),tid,d,float(p[4])))
ticks.sort(); ev.sort(); st=[e[0] for e in ev]; t0=ticks[0]
rows=[]
for i in range(len(ticks)-1):
    a,b=ticks[i],ticks[i+1]
    if a<t0+8: continue
    k=bisect.bisect_left(st,a); s=collections.defaultdict(float)
    while k<len(ev) and ev[k][0]<b:
        if ev[k][2]==D: s[name.get(ev[k][1],ev[k][1])]+=ev[k][3]*1000
        k+=1
    rows.append((a-t0,(b-a)*1000,s))
names=set(); [names.update(r[2]) for r in rows]
med={nm:statistics.median([r[2].get(nm,0) for r in rows[::5]]) for nm in names}
late=[r for r in rows if r[1]>22]
print(n,'frames',len(rows),'over 22 ms',len(late))
ex=collections.defaultdict(float); cnt=collections.Counter()
for t,pe,s in late:
    for nm,v in s.items():
        d=v-med[nm]
        if d>1.0: ex[nm]+=d; cnt[nm]+=1
for nm,v in sorted(ex.items(),key=lambda x:-x[1])[:10]: print('  %-60s total excess %7.1f ms in %d late frames'%(nm,v,cnt[nm]))
print(' per late frame (period; top excess):')
for t,pe,s in late[:40]:
    top=sorted(((v-med[nm],nm) for nm,v in s.items()),reverse=True)[:3]
    print('  %7.2fs %5.1f | '%(t,pe)+'; '.join('%s +%.1f'%(nm,v) for v,nm in top if v>0.8))
