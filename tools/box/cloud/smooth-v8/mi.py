# SMOOTH.md v8: the game thread's named scopes of the game ("MI/..." trace scopes in every tick): count, total, max, and every event over 2 ms.
#   python3 mi.py <name>     (files /tmp/v8/ins/<name>-gt.csv and -timers.csv, from ins.sh)
import sys,csv,collections
n=sys.argv[1]
name={int(r['Id']):r['Name'] for r in csv.DictReader(open(f'/tmp/v8/ins/{n}-timers.csv'))}
ev=[]
for ln in open(f'/tmp/v8/ins/{n}-gt.csv'):
    p=ln.split(',')
    if len(p)<6 or not p[0].isdigit(): continue
    ev.append((float(p[2]),int(p[1]),float(p[4])*1000,int(p[5])))
ev.sort()
t0=ev[0][0]
agg=collections.defaultdict(lambda:[0,0.0,0.0])
for s,t,d,dep in ev:
    nm=name.get(t,str(t))
    if nm.startswith('MI/'):
        a=agg[nm]; a[0]+=1; a[1]+=d; a[2]=max(a[2],d)
print('MI scopes (count, total ms, max ms):')
for nm,a in sorted(agg.items(),key=lambda x:-x[1][2]): print('  %-40s %6d %9.1f %8.2f'%(nm,a[0],a[1],a[2]))
print('MI scope events over 2 ms (time since trace start, ms, name):')
for s,t,d,dep in ev:
    nm=name.get(t,'')
    if nm.startswith('MI/') and d>2.0: print('  %8.3f s %7.2f ms d%-2d %s'%(s-t0,d,dep,nm))
