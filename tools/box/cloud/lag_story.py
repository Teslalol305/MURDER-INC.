# The story of an input check run (lag-test.sh with lag-input.txt or lag-pad.txt): one line whenever something the
# game's probe lines report changes, so a run reads as "the magazine went from 30 to 28, the trigger was let go, the
# size became 1920 x 1080 ...". The numbers that move all the time (frame rate, memory) are left out.
#
#   python3 lag_story.py <run folder or game.log> [key ...]      default keys: see KEYS below
import os
import re
import sys

KEYS = ['state', 'click', 'viewers', 'pad', 'fire', 'moveX', 'moveY', 'mag', 'dbl', 'outW', 'outH', 'mouseScale',
        'padRepeats', 'cmdRun', 'cmdRefused', 'spikes', 'target']
path = sys.argv[1]
if os.path.isdir(path):
    path = os.path.join(path, 'game.log')
keys = sys.argv[2:] or KEYS
last, n = None, 0
for line in open(path, errors='replace'):
    if 'MICloudProbe ' not in line:
        continue
    n += 1
    p = dict(re.findall(r'(\w+)=(-?[\d.]+)', line.split('MICloudProbe', 1)[1]))
    now = {k: p[k] for k in keys if k in p}
    if now != last:
        changed = [k for k in now if last is None or now[k] != last.get(k)]
        print(f'probe {n:4d}: ' + ' '.join(f'{k}={now[k]}' for k in now) + ('   <- ' + ', '.join(changed) if last is not None else ''))
        last = now
print(f'{n} probe lines')
