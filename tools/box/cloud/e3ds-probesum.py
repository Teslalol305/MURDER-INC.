"""Summarise the game's probe lines (-MICloudProbe, one line a second) from a browser console log.

  e3ds-probesum.py <console log or a file of its probe lines>

Prints, per field, the count, minimum, average and maximum, then about forty evenly spaced lines. The browser's log
holds every session since the browser started: cut it first (grep MICloudProbe LOG | tail -n N > part.txt).
"""
import re
import sys

rows = []
for line in open(sys.argv[1], errors='replace'):
    if 'MICloudProbe' not in line:
        continue
    d = dict(re.findall(r'(\w+)=([-0-9.]+)', line))
    if 'fps' in d:
        rows.append(d)
print(len(rows), 'probe lines')


def col(k):
    return [float(r[k]) for r in rows if k in r]


for k in ('fps', 'worstMs', 'gpuMs', 'dr', 'qp', 'mbps', 'encMs', 'owed', 'held'):
    v = col(k)
    if v:
        print('%-8s n=%d min=%.2f avg=%.2f max=%.2f' % (k, len(v), min(v), sum(v) / len(v), max(v)))
step = max(1, len(rows) // 40)
for i in range(0, len(rows), step):
    r = rows[i]
    print(i, ' '.join('%s=%s' % (k, r.get(k, '-')) for k in ('state', 'click', 'fps', 'worstMs', 'gpuMs', 'dr', 'owed', 'held', 'qp', 'mbps', 'viewers')))
