# Where the long frames go: reads a CSV profile of the Development game (console command "csvprofile start" ...
# "csvprofile stop", written to MurderInc/Saved/Profiling/CSV) and says, for the whole capture and for every frame
# over a limit, how long the game thread, the render thread, the RHI thread and the GPU took, what the render thread
# waited for, and the largest exclusive timers of the game and the render thread in that frame.
#
#   python3 lag_csv.py <profile.csv> [limit ms, default 50] [frames listed, default 12]
#
# The columns are the engine's own (LaunchEngineLoop.cpp, RenderingThread.cpp): FrameTime is the game thread's whole
# frame; GameThreadTime, RenderThreadTime and RHIThreadTime are the busy time of each thread without its waits;
# GPUTime is the GPU's time for the frame as the RHI measures it; RenderThreadIdle/* is what the render thread waited
# on (SwapBuffer: the RHI thread and the GPU behind it at the end of the frame).
import csv
import sys

path = sys.argv[1]
limit = float(sys.argv[2]) if len(sys.argv) > 2 else 50.0
listed = int(sys.argv[3]) if len(sys.argv) > 3 else 12

rows = list(csv.reader(open(path, errors='replace')))
header = rows[0]
frames = []
for r in rows[1:]:
    if not r or r[0] == 'EVENTS' or r[0].startswith('['):
        continue
    if len(r) != len(header):
        continue
    frames.append(r)
col = {name: i for i, name in enumerate(header)}


def val(r, name):
    try:
        return float(r[col[name]])
    except (KeyError, ValueError):
        return 0.0


def stats(name):
    v = sorted(val(r, name) for r in frames)
    if not v:
        return 'no frames'
    return f'avg {sum(v) / len(v):6.2f}  median {v[len(v) // 2]:6.2f}  99 % {v[int(len(v) * 0.99)]:7.2f}  worst {v[-1]:8.2f}'


main = ['FrameTime', 'GameThreadTime', 'RenderThreadTime', 'RHIThreadTime', 'GPUTime']
idle = [n for n in header if n.startswith('RenderThreadIdle/')]
total = sum(val(r, 'FrameTime') for r in frames)
print(f'{len(frames)} frames, {total / 1000:.1f} s, {len(frames) / max(total / 1000, 0.001):.1f} frames a second (all times in ms)')
for n in main + idle:
    if n in col:
        print(f'  {n:34s} {stats(n)}')
over = [(i, r) for i, r in enumerate(frames) if val(r, 'FrameTime') > limit]
print(f'frames over {limit:.0f} ms: {len(over)}; over 100 ms: {sum(1 for r in frames if val(r, "FrameTime") > 100)}; '
      f'over 250 ms: {sum(1 for r in frames if val(r, "FrameTime") > 250)}; over 1 s: {sum(1 for r in frames if val(r, "FrameTime") > 1000)}')

elapsed, t = [], 0.0
for r in frames:
    elapsed.append(t)
    t += val(r, 'FrameTime') / 1000
game = [n for n in header if n.startswith('Exclusive/GameThread/')]
render = [n for n in header if n.startswith('Exclusive/RenderThread/')]


def top(r, names, count=4):
    best = sorted(((val(r, n), n.rsplit('/', 1)[-1] if 'EventWait/' not in n else 'Wait:' + n.rsplit('/', 1)[-1]) for n in names), reverse=True)[:count]
    return ', '.join(f'{name} {v:.1f}' for v, name in best if v >= 0.5)


for i, r in sorted(over, key=lambda x: -val(x[1], 'FrameTime'))[:listed]:
    print(f'frame {i} at {elapsed[i]:6.2f} s: ' + '  '.join(f'{n.replace("Time", "").replace("Thread", "")} {val(r, n):.1f}' for n in main if n in col))
    print('    render thread waits: ' + ', '.join(f'{n.split("/", 1)[1]} {val(r, n):.1f}' for n in idle if val(r, n) >= 0.5))
    print('    game thread: ' + top(r, game))
    print('    render thread: ' + top(r, render))
    events = r[col['EVENTS']] if 'EVENTS' in col else ''
    if events:
        print('    events: ' + events[:200])
