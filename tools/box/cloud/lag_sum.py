# One line per lag test run (lag-test.sh): what the game itself measured while a viewer played, what Pixel Streaming
# logged and sent, what the viewer received, and whether the run had the GPU to itself.
#
#   python3 lag_sum.py [-v] <run folder> [<run folder> ...]
#
# The game's side is read from its probe lines ("MICloudProbe fps=... worstMs=... gpuMs=...", one a second), only
# those written in a run (state=2) with a viewer who has clicked; "turning" is the part of them in which the view's
# yaw changed. The engine's capture complaints exist only in the Development game's log (Shipping has no engine log):
# "n/a" then. Received frame rates come from the Python viewer, whose decoder falls behind under fast motion at 1080p
# (docs/unreal/DECISIONS.md): a rough check only.
import os
import re
import sys

verbose = '-v' in sys.argv
runs = [a for a in sys.argv[1:] if a != '-v']


def read(path):
    try:
        return open(path, errors='replace').read()
    except OSError:
        return ''


def num(d, key, default=None):
    try:
        return float(d[key])
    except (KeyError, ValueError):
        return default


def avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')


def f(x, digits=1):
    return 'n/a' if x != x else f'{x:.{digits}f}'


for run in runs:
    name = os.path.basename(os.path.normpath(run))
    info = dict(l.split('=', 1) for l in read(f'{run}/info.txt').splitlines() if '=' in l)
    log = read(f'{run}/game.log')
    probes = [dict(re.findall(r'(\w+)=(-?[\d.]+)', l.split('MICloudProbe', 1)[1])) for l in log.splitlines() if 'MICloudProbe ' in l]
    for a, b in zip(probes, probes[1:]):
        dy = abs(num(b, 'yaw', 0) - num(a, 'yaw', 0))
        b['turning'] = min(dy, 360 - dy) >= 0.5
    play = [p for p in probes if num(p, 'state') == 2 and num(p, 'viewers', 0) >= 1 and num(p, 'click', 0) == 0]
    turn = [p for p in play if p.get('turning')]
    still = [p for p in play if not p.get('turning')]
    dev = 'LogMICloud' in log
    fence = len(re.findall(r'Timed out waiting for fence', log))
    skipped = len(re.findall(r'No frames available for capture', log))
    commit = re.search(r'Build: .*?commit ([0-9a-f]{7})', log)

    # The viewer: frames received in each phase.
    view = read(f'{run}/view.log')
    counts, phases = [], []
    for l in view.splitlines():
        m = re.match(r'\s*([\d.]+)\s+(.*)', l)
        if not m:
            continue
        t, rest = float(m.group(1)), m.group(2)
        c = re.match(r'frames (\d+)', rest)
        if c:
            counts.append((t, int(c.group(1))))
        if 'PHASE' in rest:
            phases.append((t, rest.split('PHASE', 1)[1].strip()))
    received = []
    for (a, label), (b, _) in zip(phases, phases[1:]):
        inside = [x for x in counts if a - 2.5 <= x[0] <= b + 2.5]
        if len(inside) >= 2 and inside[-1][0] > inside[0][0]:
            received.append(f'{label} {(inside[-1][1] - inside[0][1]) / (inside[-1][0] - inside[0][0]):.0f}')
    end = re.search(r'END (\{.*\})', view)

    # Did anything else use the GPU?
    others = [l for l in read(f'{run}/others.log').splitlines() if 'others=' in l]
    foreign = sum(1 for l in others if not re.search(r'others=0\b', l))
    util = avg([float(m.group(1)) for l in others for m in [re.search(r'util=(\d+)', l)] if m])
    result = read(f'{run}/result.txt').strip()

    targets = sorted({int(num(p, 'target', 0)) for p in play if num(p, 'target', 0)}, reverse=True)
    drs = [num(p, 'dr') for p in play if num(p, 'dr', -1) > 0]
    parts = [
        f"{name} {'dev' if dev else 'ship'} {commit.group(1) if commit else '?'} load={info.get('load', '0')} sp={info.get('sp', '-')}",
        f"play {len(play)} s: fps {f(avg([num(p, 'fps') for p in play]))} (min {f(min([num(p, 'fps') for p in play], default=float('nan')))}), "
        f"worst frame {f(max([num(p, 'worstMs') for p in play], default=float('nan')), 0)} ms",
        f"turning {len(turn)} s: fps {f(avg([num(p, 'fps') for p in turn]))}, worst {f(max([num(p, 'worstMs') for p in turn], default=float('nan')), 0)} ms"
        f"; still: worst {f(max([num(p, 'worstMs') for p in still], default=float('nan')), 0)} ms",
        f"gpu {f(avg([num(p, 'gpuMs') for p in play]))} ms (max {f(max([num(p, 'gpuMs') for p in play], default=float('nan')))})",
    ]
    if any('target' in p for p in play):
        parts.append(f"target {'/'.join(str(t) for t in targets) or '?'}, picture {f(min(drs, default=float('nan')), 2)}-{f(max(drs, default=float('nan')), 2)}"
                     f", owed {f(max([num(p, 'owed', 0) for p in play], default=0), 0)}, held {f(sum(num(p, 'held', 0) for p in play), 0)} frames"
                     f" (worst wait {f(max([num(p, 'worstWaitMs', 0) for p in play], default=0))} ms, time-outs {f(sum(num(p, 'pacerTimeOuts', 0) for p in play), 0)})")
    parts.append(f"fence time-outs {fence}, skipped captures {skipped}" if dev else 'capture log n/a (Shipping)')
    if any('txFps' in p for p in play):
        sent = [p for p in play if 'txFps' in p]
        parts.append(f"sender: captured {f(avg([num(p, 'capFps') for p in sent]), 0)}, encoded {f(avg([num(p, 'encFps') for p in sent]), 0)}, sent {f(avg([num(p, 'txFps') for p in sent]), 0)} a second"
                     f" (turning {f(avg([num(p, 'txFps') for p in sent if p.get('turning')]), 0)}), QP {f(avg([num(p, 'qp') for p in sent]), 0)}, {f(avg([num(p, 'mbps') for p in sent]))} Mbit/s, encode {f(avg([num(p, 'encMs') for p in sent]))} ms")
    parts.append('received a second: ' + (', '.join(received) or 'no phases') + (f" (total {__import__('json').loads(end.group(1)).get('video')} frames)" if end else ' (viewer did not finish)'))
    parts.append(('CLEAN' if foreign == 0 and others else f'POLLUTED: another game ran in {foreign} of {len(others)} samples' if others else 'no watcher log')
                 + f", GPU use {f(util, 0)} %; {result or 'no result'}")
    print(' | '.join(parts))
    if verbose:
        for p in play:
            print('   ', ' '.join(f'{k}={p[k]}' for k in ('fps', 'worstMs', 'gpuMs', 'target', 'dr', 'owed', 'held', 'worstWaitMs', 'gameMs', 'renderMs', 'rhiMs', 'capFps', 'encFps', 'txFps', 'qp', 'yaw') if k in p),
                  'TURN' if p.get('turning') else '')
