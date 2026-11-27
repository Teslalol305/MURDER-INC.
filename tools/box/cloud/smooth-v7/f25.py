# v7 prover: every frame over 25 ms of a run's CSV profile (from t0), with the thread times, loads, GC and the events.
#   python3 f25.py <run dir> [t0=8] [-v]
import csv,glob,sys
csv.field_size_limit(10**9)
d=sys.argv[1].rstrip('/'); t0=float(sys.argv[2]) if len(sys.argv)>2 and not sys.argv[2].startswith('-') else 8; vb='-v' in sys.argv
f=sorted(glob.glob(d+'/*.csv'))[0]; rows=list(csv.reader(open(f,errors='replace'))); h=rows[0]; c={n:i for i,n in enumerate(h)}
fr=[r for r in rows[1:] if r and len(r)>20 and r[0]!='EVENTS' and not r[0].startswith('[')]
g=lambda r,n: float(r[c[n]] or 0) if n in c else 0.0
t=0; out=[]; bands={}
for r in fr:
    ft=g(r,'FrameTime')
    if t>=t0:
        b=('<=17' if ft<=17.5 else '17.5-20' if ft<=20 else '20-25' if ft<=25 else '25-33' if ft<=33.4 else '33-50' if ft<=50 else '>50')
        bands[b]=bands.get(b,0)+1
        if ft>25:
            gm,rn,rh,gp=g(r,'GameThreadTime'),g(r,'RenderThreadTime'),g(r,'RHIThreadTime'),g(r,'GPUTime')
            mx=max(gm,rn,rh,gp); nm=['game','render','rhi','gpu'][[gm,rn,rh,gp].index(mx)]
            cl = nm if mx>=ft*0.6 else 'WAIT(no thread >60%)'
            out.append((t,ft,gm,rn,rh,gp,cl,g(r,'Exclusive/GameThread/FlushAsyncLoading'),g(r,'FileIO/GameThread/AsyncLoadingTime'),g(r,'GC/Count'),g(r,'PSO/GraphicsPSOHitch')+g(r,'PSO/ComputePSOHitch'),r[0]))
    t+=ft/1000
tot=sum(bands.values()); print(d, 'frames', tot, 'bands', {k:bands.get(k,0) for k in ['<=17','17.5-20','20-25','25-33','33-50','>50']})
cl={}
for o in out: cl[o[6]]=cl.get(o[6],0)+1
print(' over 25ms:',len(out),'by class',cl,' with FlushAsync>0:',sum(1 for o in out if o[7]>0),' with GC:',sum(1 for o in out if o[9]>0),' with PSO:',sum(1 for o in out if o[10]>0))
if vb:
    for o in out: print('  %7.2fs %5.1fms game %4.1f rt %4.1f rhi %4.1f gpu %4.1f %-22s flush %.1f aload %.1f gc %d pso %d %s'%(o[0],o[1],o[2],o[3],o[4],o[5],o[6],o[7],o[8],o[9],o[10],o[11][:60]))
