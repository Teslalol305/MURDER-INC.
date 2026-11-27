# v7 prover: in frames over <ms> (from 8 s), the stat columns far above their median in the run: the cause of a long frame.
#   python3 top.py <run dir> <ms>
import csv,glob,sys,statistics
csv.field_size_limit(10**9)
d=sys.argv[1].rstrip('/'); thr=float(sys.argv[2]); t0=8
f=sorted(glob.glob(d+'/*.csv'))[0]; rows=list(csv.reader(open(f,errors='replace'))); h=rows[0]; c={n:i for i,n in enumerate(h)}
fr=[r for r in rows[1:] if r and len(r)>20 and r[0]!='EVENTS' and not r[0].startswith('[')]
def num(r,i):
    try: return float(r[i])
    except: return 0.0
ft=c['FrameTime']; t=0; sel=[]; allr=[]
for r in fr:
    x=num(r,ft)
    if t>=t0:
        allr.append(r)
        if x>thr: sel.append((t,r))
    t+=x/1000
names=[n for n in h if n.startswith(('Exclusive/','Ticks/','Scheduler/')) or n.endswith(('Time','Count')) and not n.startswith(('CsvProfiler',))]
med={n:statistics.median([num(r,c[n]) for r in allr[::7]]) for n in names}
print(d,'frames over',thr,':',len(sel))
for tt,r in sel:
    ex=sorted(((num(r,c[n])-med[n],n) for n in names),reverse=True)[:6]
    print(' %6.2fs %5.1f ms | '%(tt,num(r,ft))+'; '.join('%s +%.1f'%(n.replace('Exclusive/',''),v) for v,n in ex if v>0.5))
