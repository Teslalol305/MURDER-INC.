# What a run of a streamed game did, from its own log: the probe lines of the run (one a second with -MICloudProbe=1)
# and the session lines of release 3c, side by side with the viewer's and the box's own records.
#
#   python3 session_sum.py <run folder> [name:from-to ...]
#
# <run folder> is a lag-test.sh run (game.log, view.log, others.log, result.txt, info.txt). Each "name:from-to" is a
# window of the game's own clock, in seconds since its process started (the probe line's up= field; a line without
# one, from an older build, counts by its number); the
# table has one row per window with the mean (and the lowest and highest) of the fields that matter for the session's
# proofs: frame rate, GPU time, idle, viewers, the QP, the QP range the plugin was given, the bitrate, the frames the
# sender captured, encoded and sent a second, the bandwidth it thought it had, the round trip. Without windows: the
# whole run as one window. -v prints every probe line's fields too.
import os
import re
import sys

args = [a for a in sys.argv[1:] if a != '-v']
verbose = '-v' in sys.argv
run = args[0]


def read(path):
    try:
        return open(path, errors='replace').read()
    except OSError:
        return ''


log = read(f'{run}/game.log')
probes = [dict((k, float(v)) for k, v in re.findall(r'(\w+)=(-?[\d.]+)', l.split('MICloudProbe ', 1)[1]))
          for l in log.splitlines() if 'MICloudProbe fps=' in l and 'Command line' not in l]
for i, p in enumerate(probes):
    p.setdefault('up', float(i))
FIELDS = ['fps', 'worstMs', 'gpuMs', 'idle', 'viewers', 'qp', 'qpMin', 'qpMax', 'mbps', 'capFps', 'encFps', 'txFps', 'availMbps', 'capToSendMs', 'rttMs', 'rttN', 'state']


def row(name, rows):
    if not rows:
        return f'{name:>14}: no probe lines'
    parts = []
    for k in FIELDS:
        xs = [r[k] for r in rows if k in r]
        if xs:
            parts.append(f'{k} {sum(xs) / len(xs):.1f}' + (f' ({min(xs):.1f}..{max(xs):.1f})' if min(xs) != max(xs) else ''))
    return f'{name:>14}: {len(rows)} lines | ' + ' | '.join(parts)


print(f'{os.path.basename(os.path.normpath(run))}: {len(probes)} probe lines; result: {read(f"{run}/result.txt").strip() or "none"}')
if verbose:
    for i, p in enumerate(probes):
        print(i, ' '.join(f'{k}={p[k]:g}' for k in ['up'] + FIELDS if k in p))
wins = [w for w in args[1:] if ':' in w]
if not wins:
    print(row('whole run', probes))
for w in wins:
    name, span = w.split(':', 1)
    a, b = (float(x) for x in span.split('-'))
    print(row(name, [p for p in probes if a <= p['up'] < b]))
for key in ('Session:', 'Nobody is watching', 'Back at full speed', 'Session over', 'Viewer joined', 'Connection lost', 'Encoder quality', 'Launcher:'):
    for l in log.splitlines():
        if key in l and 'Command line' not in l:
            print('  ' + l.strip()[:300])
