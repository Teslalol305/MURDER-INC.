# per-run: frames over 25/50/100 ms a minute from t0, worst, 1% low, and where the over-25 frames cluster (per 10 s bucket)
import csv,glob,sys
csv.field_size_limit(10**9)
d=sys.argv[1].rstrip('/'); t0=float(sys.argv[2]) if len(sys.argv)>2 else 8.0
f=sorted(glob.glob(d+'/*.csv'))[0]; rows=list(csv.reader(open(f,errors='replace')))
hdr=[r for r in rows if r and r[0]=='EVENTS'][-1] if any(r and r[0]=='EVENTS' for r in rows) else rows[0]
c={n:i for i,n in enumerate(hdr)}; k=c['FrameTime']
t=0.0;n=0;secs=0.0;o=[0,0,0];worst=0.0;fts=[];bk={};wt=0
for r in rows:
    if not r or r[0]=='EVENTS' or r[0].startswith('[') or len(r)<=k: continue
    try: ft=float(r[k] or 0)
    except ValueError: continue
    if t>=t0:
        n+=1;secs+=ft/1000;fts.append(ft)
        if ft>worst: worst=ft;wt=t
        for i,x in enumerate((25,50,100)): o[i]+=ft>x
        if ft>25: bk[int(t//10)*10]=bk.get(int(t//10)*10,0)+1
    t+=ft/1000
m=secs/60 if secs else 1
fts.sort();q=max(1,len(fts)//100);low=1000/(sum(fts[-q:])/q) if fts else 0
print('%s frames %d %.0fs: >25/50/100 per min %.1f/%.1f/%.1f (%d/%d/%d) worst %.1f@%.0fs 1%%low %.1f | >25 by 10s: %s'%(d.split('/')[-1],n,secs,o[0]/m,o[1]/m,o[2]/m,*o,worst,wt,low,' '.join('%d:%d'%kv for kv in sorted(bk.items()))))
