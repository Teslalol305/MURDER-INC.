#!/usr/bin/env python3
"""Walk waypoints for the demo script (tools/box/demo/demo.txt) on the Goons' own nav grid (level.json nav).

A* over the free cells (8 neighbours), then string-pulled: a waypoint is dropped when the straight line between its
neighbours stays on free cells (with a margin). Prints one `route <sprint> x y x y ...` line in Unreal cm.

  python3 plan_path.py <x0> <y0> <x1> <y1> [sprint] [margin cells]
"""
import heapq
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEVEL = os.path.join(HERE, '..', '..', '..', 'unreal', 'MurderInc', 'Content', 'Data', 'level.json')


def load():
    d = json.load(open(LEVEL))
    nav = d['nav']
    rows = nav['grid']['cells']
    o = nav['ue']['origin']
    return rows, o['X'], o['Y'], nav['ue']['cell']


def main():
    x0, y0, x1, y1 = (float(a) for a in sys.argv[1:5])
    sprint = len(sys.argv) > 5 and sys.argv[5] == '1'
    margin = int(sys.argv[6]) if len(sys.argv) > 6 else 1
    rows, ox, oy, cell = load()
    H, W = len(rows), len(rows[0])
    free = [[rows[j][i] == '.' for i in range(W)] for j in range(H)]
    # cells with a margin of free cells around them (the walk keeps off the walls)
    safe = [[free[j][i] and all(0 <= j + b < H and 0 <= i + a < W and free[j + b][i + a]
                                 for a in range(-margin, margin + 1) for b in range(-margin, margin + 1))
             for i in range(W)] for j in range(H)]
    cellof = lambda x, y: (int((x - ox) // cell), int((y - oy) // cell))
    centre = lambda i, j: (ox + (i + 0.5) * cell, oy + (j + 0.5) * cell)

    def nearest(i, j):
        best = None
        for r in range(0, 30):
            for a in range(-r, r + 1):
                for b in range(-r, r + 1):
                    ii, jj = i + a, j + b
                    if 0 <= ii < W and 0 <= jj < H and safe[jj][ii]:
                        dd = a * a + b * b
                        if best is None or dd < best[0]:
                            best = (dd, ii, jj)
            if best:
                return best[1], best[2]
        raise SystemExit('no free cell near %d %d' % (i, j))

    s = nearest(*cellof(x0, y0))
    g = nearest(*cellof(x1, y1))
    dist = {s: 0.0}
    prev = {}
    pq = [(0.0, s)]
    while pq:
        _, c = heapq.heappop(pq)
        if c == g:
            break
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                if a == 0 and b == 0:
                    continue
                n = (c[0] + a, c[1] + b)
                if not (0 <= n[0] < W and 0 <= n[1] < H) or not safe[n[1]][n[0]]:
                    continue
                if a and b and not (safe[c[1]][n[0]] and safe[n[1]][c[0]]):
                    continue
                nd = dist[c] + math.hypot(a, b)
                if nd < dist.get(n, 1e18):
                    dist[n] = nd
                    prev[n] = c
                    h = math.hypot(n[0] - g[0], n[1] - g[1])
                    heapq.heappush(pq, (nd + h, n))
    if g not in dist:
        raise SystemExit('no path')
    path = [g]
    while path[-1] != s:
        path.append(prev[path[-1]])
    path.reverse()

    def clear(p, q):
        n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1])) * 3) + 1
        for k in range(n + 1):
            t = k / n
            i = int(round(p[0] + (q[0] - p[0]) * t))
            j = int(round(p[1] + (q[1] - p[1]) * t))
            if not safe[j][i]:
                return False
        return True

    pts = [path[0]]
    k = 0
    while k < len(path) - 1:
        m = len(path) - 1
        while m > k + 1 and not clear(path[k], path[m]):
            m -= 1
        pts.append(path[m])
        k = m
    total = 0.0
    last = (x0, y0)
    xy = []
    for (i, j) in pts[1:-1]:
        x, y = centre(i, j)
        total += math.hypot(x - last[0], y - last[1])
        last = (x, y)
        xy += ['%.0f' % x, '%.0f' % y]
    total += math.hypot(x1 - last[0], y1 - last[1])
    xy += ['%.0f' % x1, '%.0f' % y1]
    print('route %d %s   # %.1f m' % (1 if sprint else 0, ' '.join(xy), total / 100.0))


if __name__ == '__main__':
    main()
