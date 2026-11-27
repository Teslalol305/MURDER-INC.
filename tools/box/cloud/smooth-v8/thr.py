# SMOOTH.md v8: events of at least <ms> on every thread of a window export, by thread, down to depth 8.
#   python3 thr.py <name> <ms>
import sys,csv
n=sys.argv[1]; thr=float(sys.argv[2])
name={int(r['Id']):r['Name'] for r in csv.DictReader(open(f'/tmp/v8/ins/{n}-timers.csv'))}
th={}
for r in csv.reader(open(f'/tmp/v8/ins/{n}-threads.csv')):
    if r and r[0].isdigit(): th[int(r[0])]=r[1] if len(r)>1 else ''
ev=[]
for ln in open(f'/tmp/v8/ins/{n}-win.csv'):
    p=ln.split(',')
    if len(p)<6 or not p[0].isdigit(): continue
    d=float(p[4])*1000
    if d>=thr: ev.append((int(p[0]),float(p[2]),d,int(p[5]),name.get(int(p[1]),p[1])))
ev.sort()
cur=None
for t,s,d,dep,nm in ev:
    if t!=cur: cur=t; print('== thread',t,th.get(t,''))
    if dep<=8: print('   %7.3f %8.1f ms d%-2d %s%s'%(s,d,dep,'  '*dep,nm))
