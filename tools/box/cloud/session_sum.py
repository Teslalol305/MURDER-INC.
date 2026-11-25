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
#
#   python3 session_sum.py <run folder> --phases
#
#   python3 session_sum.py <run folder> --gpu
#
# the GPU's own utilisation (others.log: nvidia-smi once a second, the whole card, the game alone on it) between the
# session lines of the game that carry the clock ("(game time 12.3 s, 12:37:51 UTC)": Viewer joined, Connection lost,
# Nobody is watching, Back at full speed, Session over): the proof that an idle game costs the card almost nothing.
#
# --phases: one row per "say PHASE <name>" line of the viewer's script (view.log): the viewer's phase is laid on the game's clock
# by the game's "Viewer joined (game time X s)" line and the viewer's "connection connected" time (good to about a
# second), and the frames the viewer received a second in that phase come from its own "frames N" lines (every 5 s).
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
if '--gpu' in sys.argv:
    def secs(h, m, sec):
        return int(h) * 3600 + int(m) * 60 + int(sec)

    events = []
    for l in log.splitlines():
        m = re.search(r'\(game time ([\d.]+) s, (\d\d):(\d\d):(\d\d) UTC\)', l)
        if not m:
            continue
        for key, name in (('Viewer joined', 'a viewer joined'), ('Connection lost', 'the viewer left'), ('Nobody is watching', 'idle starts'),
                          ('Back at full speed', 'idle ends'), ('Session over', 'the game quits')):
            if key in l:
                events.append((secs(*m.groups()[1:]), name, float(m.group(1))))
    util = [(secs(*m.groups()[:3]), int(m.group(4)), int(m.group(5))) for m in
            re.finditer(r'^(\d\d):(\d\d):(\d\d) others=\d+ util=(\d+) mem=(\d+)', read(f'{run}/others.log'), re.M)]
    events.sort()
    print('events (clock, game time):', '; '.join(f'{name} {t // 3600:02d}:{t // 60 % 60:02d}:{t % 60:02d} ({up:.1f} s)' for t, name, up in events))
    for (t0, n0, _), (t1, n1, _) in zip(events, events[1:]):
        w = [u for t, u, m in util if t0 + 1 <= t <= t1 - 1]
        if len(w) >= 3:
            print(f'  GPU utilisation from "{n0}" to "{n1}": {len(w)} s, mean {sum(w) / len(w):.1f} %, highest {max(w)} %, lowest {min(w)} %')
wins = [w for w in args[1:] if ':' in w]
if not wins and '--phases' not in sys.argv and '--gpu' not in sys.argv:
    print(row('whole run', probes))
if '--phases' in sys.argv:
    view = read(f'{run}/view.log')
    join = re.search(r'Viewer joined.*game time ([\d.]+) s', log)
    conn = re.search(r'^\s*([\d.]+) connection connected', view, re.M)
    phases = [(float(m.group(1)), m.group(2)) for m in re.finditer(r'^\s*([\d.]+) > say PHASE (\S+)', view, re.M)]
    frames = [(float(m.group(1)), int(m.group(2))) for m in re.finditer(r'^\s*([\d.]+) frames (\d+) ', view, re.M)]
    if not (join and conn and phases):
        print('no phases: the run has no viewer with PHASE lines, or the game did not log its join')
    else:
        off = float(join.group(1)) - float(conn.group(1))

        def got(t):  # frames received by viewer time t (linear between the 5 s lines)
            pts = [(0.0, 0)] + frames
            for (t0, n0), (t1, n1) in zip(pts, pts[1:]):
                if t0 <= t <= t1:
                    return n0 + (n1 - n0) * (t - t0) / max(t1 - t0, 1e-9)
            return pts[-1][1]

        ends = [t for t, _ in phases[1:]] + [phases[-1][0] + 1e9]
        for (t, name), end in zip(phases, ends):
            if end > 1e8:
                continue
            r = row(name, [p for p in probes if t + off <= p['up'] < end + off])
            print(f'{r} | viewer received {(got(end) - got(t)) / max(end - t, 1e-9):.1f} frames a second')
for w in wins:
    name, span = w.split(':', 1)
    a, b = (float(x) for x in span.split('-'))
    print(row(name, [p for p in probes if a <= p['up'] < b]))
for key in ('Session:', 'Nobody is watching', 'Back at full speed', 'Session over', 'Viewer joined', 'Connection lost', 'Encoder quality', 'Launcher:'):
    for l in log.splitlines():
        if key in l and 'Command line' not in l:
            print('  ' + l.strip()[:300])
