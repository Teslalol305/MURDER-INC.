# SMOOTH.md v8: busy seconds per 0.5 s on every thread of a window export (depth 0, waits left out), to see which threads work at engine start.
#   python3 busy.py <name>   (files /tmp/v8/ins/<name>-win.csv, -threads.csv, -timers.csv)
import sys,csv,collections
n=sys.argv[1]
th={}
for r in csv.reader(open(f'/tmp/v8/ins/{n}-threads.csv')):
    if r and r[0].isdigit(): th[int(r[0])]=r[1]
name={int(r['Id']):r['Name'] for r in csv.DictReader(open(f'/tmp/v8/ins/{n}-timers.csv'))}
b=collections.defaultdict(lambda: collections.defaultdict(float)); top=collections.defaultdict(lambda: collections.defaultdict(float))
for ln in open(f'/tmp/v8/ins/{n}-win.csv'):
    p=ln.split(',')
    if len(p)<6 or not p[0].isdigit(): continue
    if int(p[5])!=0: continue
    t=int(p[0]); s=float(p[2]); d=float(p[4])
    nm=name.get(int(p[1]),p[1])
    if nm in ('WaitForTasks','Game thread idle time'): continue
    b[t][int(s/0.5)*0.5]+=d; top[t][nm]+=d
print('busy seconds per 0.5 s bucket (depth 0, waits excluded), threads with more than 0.3 s in all')
for t in sorted(b):
    tot=sum(b[t].values())
    if tot<0.3: continue
    print('%3d %-28s total %.2f | '%(t,th.get(t,'')[:28],tot)+' '.join('%.1f:%.2f'%(k,v) for k,v in sorted(b[t].items())))
    print('      top:', ', '.join('%s %.2f'%(k,v) for k,v in sorted(top[t].items(),key=lambda x:-x[1])[:3]))
