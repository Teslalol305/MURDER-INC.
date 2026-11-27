# Closer: frames over 25 / 50 / 100 ms a minute of a run's CSV profile, from t0 (default 8 s), as SMOOTH.md's table counts them.
#   python3 rate.py <run dir> [t0=8]
import csv,glob,sys
csv.field_size_limit(10**9)
d=sys.argv[1].rstrip('/'); t0=float(sys.argv[2]) if len(sys.argv)>2 else 8.0
f=sorted(glob.glob(d+'/*.csv'))[0]; rows=list(csv.reader(open(f,errors='replace'))); c={n:i for i,n in enumerate(rows[0])}
t=0.0; n=0; secs=0.0; o25=o50=o100=0; worst=0.0; fts=[]
for r in rows[1:]:
    if not r or len(r)<20 or r[0]=='EVENTS' or r[0].startswith('['): continue
    ft=float(r[c['FrameTime']] or 0)
    if t>=t0:
        n+=1; secs+=ft/1000; fts.append(ft); worst=max(worst,ft)
        o25+=ft>25; o50+=ft>50; o100+=ft>100
    t+=ft/1000
m=secs/60 if secs else 1
fts.sort(); low1=1000/(sum(fts[-max(1,len(fts)//100):])/max(1,len(fts)//100)) if fts else 0
print('%s frames %d, %.1f s: over 25/50/100 ms a minute %.1f / %.1f / %.1f (%d/%d/%d), worst %.1f ms, 1%% low %.1f fps'%(d.split('/')[-1],n,secs,o25/m,o50/m,o100/m,o25,o50,o100,worst,low1))
