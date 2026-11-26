"""Checker-side mirror of the engine's nav and movement rules, for testing level data before the engine bake exists.

- `layer_grid()`: FMIBoxWorld::RebuildNav (World/MIBoxWorld.cpp 443-519) for the street "plane" layer, and the "boxes"
  layer rule of midtown.md 17.3 for roof layers (a cell is walkable when a support top lies within +-0.45 of the layer's
  y at the cell centre and no nav-blocking collider spans [y + 0.47, y + 1.5], inflated 0.5). Same index arithmetic as
  the C++ (cells whose centre lies within `inflate` of a box, inclusive), outer ring blocked, 4-connected regions,
  8-neighbour A* with the no-corner-cutting rule, octile costs.
- `Rays`: the box ray cast for sight and shots (boxes that block shots: everything but playerOnly).
- `PlayerFlood`: a 0.25 m heightfield flood of where the player's capsule can stand (radius 0.32, height 1.8, step
  0.42, jump 1.0 m), used for reach and the fall check (no drop over 4.02 m, the 13 m/s fall-damage landing).

These are design checks. The file's `nav` grids are written by the engine bake with FMIBoxWorld's own code
(MAPS.md D2); `Levels.<Id>.Nav` compares that bake with a rebuild in the engine, not with this module.
"""

import heapq
import math

import numpy as np

CELL = 0.5
INFLATE = 0.5
BAND_MIN = 0.47
BAND_MAX = 1.5
LAYER_TOL = 0.45
SQRT2 = math.sqrt(2.0)


def blocks_nav(b):
    f = b["flags"]
    return not f["noNav"] and not f["bulletOnly"] and not f["playerOnly"]


def box_arrays(boxes):
    mn = np.array([b["min"] for b in boxes], dtype=float)
    mx = np.array([b["max"] for b in boxes], dtype=float)
    return mn, mx


class Grid:
    def __init__(self, lid, y, rect, kind):
        self.id = lid
        self.y = y
        self.kind = kind
        self.ox = rect["minX"]
        self.oz = rect["minZ"]
        self.cols = max(3, int(math.ceil((rect["maxX"] - rect["minX"]) / CELL - 1e-9)))
        self.rows = max(3, int(math.ceil((rect["maxZ"] - rect["minZ"]) / CELL - 1e-9)))
        self.blocked = np.zeros((self.rows, self.cols), dtype=np.uint8)
        self.region = None

    # index ranges of cells whose centre lies within `inflate` of [a0, a1] (MIBoxWorld.cpp 481-484)
    def _irange(self, a0, a1, origin, n, inflate):
        i0 = max(0, int(math.ceil((a0 - inflate - origin) / CELL - 0.5 - 1e-9)))
        i1 = min(n - 1, int(math.floor((a1 + inflate - origin) / CELL - 0.5 + 1e-9)))
        return i0, i1

    def stamp(self, b, inflate=INFLATE, value=1):
        i0, i1 = self._irange(b["min"][0], b["max"][0], self.ox, self.cols, inflate)
        j0, j1 = self._irange(b["min"][2], b["max"][2], self.oz, self.rows, inflate)
        if i0 <= i1 and j0 <= j1:
            self.blocked[j0:j1 + 1, i0:i1 + 1] = value

    def ring(self):
        self.blocked[0, :] = 1
        self.blocked[-1, :] = 1
        self.blocked[:, 0] = 1
        self.blocked[:, -1] = 1

    def centre(self, i, j):
        return self.ox + (i + 0.5) * CELL, self.oz + (j + 0.5) * CELL

    def cell_at(self, x, z):
        i = int(math.floor((x - self.ox) / CELL))
        j = int(math.floor((z - self.oz) / CELL))
        if 0 <= i < self.cols and 0 <= j < self.rows:
            return i, j
        return None

    def free(self, x, z):
        c = self.cell_at(x, z)
        return c is not None and not self.blocked[c[1], c[0]]

    def label(self):
        lab = np.zeros(self.blocked.shape, dtype=np.int32)
        nid = 0
        R, C = self.blocked.shape
        for j in range(R):
            for i in range(C):
                if self.blocked[j, i] or lab[j, i]:
                    continue
                nid += 1
                stack = [(j, i)]
                lab[j, i] = nid
                while stack:
                    cj, ci = stack.pop()
                    for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nj, ni = cj + dj, ci + di
                        if 0 <= nj < R and 0 <= ni < C and not self.blocked[nj, ni] and not lab[nj, ni]:
                            lab[nj, ni] = nid
                            stack.append((nj, ni))
        self.region = lab
        return nid

    def nearest_free(self, x, z, max_r=None, region=None):
        """Nearest free cell centre to (x, z) by distance from the point (not ring order), optionally within a region."""
        fx = (x - self.ox) / CELL
        fz = (z - self.oz) / CELL
        ci = min(max(int(math.floor(fx)), 0), self.cols - 1)
        cj = min(max(int(math.floor(fz)), 0), self.rows - 1)
        rmax = int(max_r / CELL) + 2 if max_r else max(self.cols, self.rows)
        best, bd = None, 1e18
        for r in range(0, rmax + 1):
            if best is not None and (r - 1) * CELL > math.sqrt(bd):
                break
            for j in range(cj - r, cj + r + 1):
                if j < 0 or j >= self.rows:
                    continue
                step = 1 if (j == cj - r or j == cj + r) else max(1, 2 * r)
                for i in range(ci - r, ci + r + 1, step):
                    if i < 0 or i >= self.cols or self.blocked[j, i]:
                        continue
                    if region is not None and self.region[j, i] != region:
                        continue
                    cx, cz = self.centre(i, j)
                    d = (cx - x) ** 2 + (cz - z) ** 2
                    if d < bd:
                        bd, best = d, (i, j)
        if best is None or (max_r is not None and math.sqrt(bd) > max_r):
            return None, None
        return best, math.sqrt(bd)

    def path(self, a, b):
        """A* from cell a to cell b (i, j): 8 neighbours, no corner cutting, octile; returns (length m, cells) or None."""
        if a == b:
            return 0.0, [a]
        R, C = self.blocked.shape
        bl = self.blocked
        gi, gj = b
        g = {a: 0.0}
        parent = {a: None}
        h0 = self._oct(a, b)
        heap = [(h0, 0.0, a)]
        closed = set()
        dirs = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, SQRT2), (1, -1, SQRT2), (-1, 1, SQRT2), (-1, -1, SQRT2))
        while heap:
            f, gc, cur = heapq.heappop(heap)
            if cur in closed:
                continue
            if cur == b:
                cells = []
                c = cur
                while c is not None:
                    cells.append(c)
                    c = parent[c]
                cells.reverse()
                return gc * CELL, cells
            closed.add(cur)
            ci, cj = cur
            for di, dj, cost in dirs:
                ni, nj = ci + di, cj + dj
                if ni < 0 or nj < 0 or ni >= C or nj >= R or bl[nj, ni]:
                    continue
                if di and dj and (bl[cj, ci + di] or bl[cj + dj, ci]):
                    continue
                ng = gc + cost
                nb = (ni, nj)
                if nb in closed or ng >= g.get(nb, 1e18):
                    continue
                g[nb] = ng
                parent[nb] = cur
                heapq.heappush(heap, (ng + self._oct(nb, b), ng, nb))
        return None

    @staticmethod
    def _oct(a, b):
        ax, az = abs(a[0] - b[0]), abs(a[1] - b[1])
        return ax + (SQRT2 - 1) * az if ax > az else az + (SQRT2 - 1) * ax

    def to_rows(self):
        return ["".join("#" if v else "." for v in row) for row in self.blocked]


def layer_grid(boxes, layer):
    r = layer["rect"]
    g = Grid(layer["id"], layer["y"], r, layer["floor"])
    y = layer["y"]
    if layer["floor"] == "plane":
        for b in boxes:
            if blocks_nav(b) and b["max"][1] >= BAND_MIN and b["min"][1] <= BAND_MAX:
                g.stamp(b)
    else:
        support = np.zeros_like(g.blocked)
        for b in boxes:
            if b["flags"]["bulletOnly"]:
                continue
            if abs(b["max"][1] - y) <= LAYER_TOL:
                i0, i1 = g._irange(b["min"][0], b["max"][0], g.ox, g.cols, 0.0)
                j0, j1 = g._irange(b["min"][2], b["max"][2], g.oz, g.rows, 0.0)
                if i0 <= i1 and j0 <= j1:
                    support[j0:j1 + 1, i0:i1 + 1] = 1
        g.blocked[:] = 1 - support
        for b in boxes:
            if blocks_nav(b) and b["max"][1] >= y + BAND_MIN and b["min"][1] <= y + BAND_MAX:
                g.stamp(b)
    g.ring()
    g.label()
    return g


class Rays:
    """Segment tests against the boxes that block shots and sight (the box ray cast; playerOnly boxes let rays pass)."""

    def __init__(self, boxes):
        sel = [b for b in boxes if not b["flags"]["playerOnly"]]
        self.mn, self.mx = box_arrays(sel)

    def clear(self, a, b, skip_inside=False):
        a = np.asarray(a, float)
        d = np.asarray(b, float) - a
        with np.errstate(divide="ignore", invalid="ignore"):
            inv = np.where(np.abs(d) > 1e-12, 1.0 / d, np.inf)
            t1 = (self.mn - a) * inv
            t2 = (self.mx - a) * inv
        lo = np.where(np.abs(d) > 1e-12, np.minimum(t1, t2), np.where((a >= self.mn) & (a <= self.mx), -np.inf, np.inf))
        hi = np.where(np.abs(d) > 1e-12, np.maximum(t1, t2), np.where((a >= self.mn) & (a <= self.mx), np.inf, -np.inf))
        tmin = lo.max(axis=1)
        tmax = hi.min(axis=1)
        hit = (tmax >= np.maximum(tmin, 0.0)) & (tmin <= 1.0) & (tmax >= 0.0)
        if skip_inside:
            hit &= tmin > 1e-6
        return not hit.any()

    def clear_many(self, a, targets):
        """Visibility from one point a to many targets (N x 3): bool array."""
        a = np.asarray(a, float)
        T = np.asarray(targets, float)
        out = np.ones(len(T), dtype=bool)
        for k, t in enumerate(T):
            out[k] = self.clear(a, t)
        return out


def dist_point_box(p, mn, mx):
    d = np.maximum(np.maximum(mn - p, 0.0), p - mx)
    return float(np.sqrt((d * d).sum(axis=-1)).min()) if d.ndim > 1 else float(np.sqrt((d * d).sum()))


class PlayerFlood:
    """Where the player's capsule can stand, on a 0.25 m heightfield over the bounds.

    State = (cell, floor height). A move to a 4-neighbour cell is allowed when no movement-blocking box (inflated by
    the capsule radius) rises above the climb limit (0.42 walking, 1.08 with a jump) within the body's height at the
    crossing, and the new cell is clear of boxes over its new floor; the new floor is the highest support top under the
    cell's footprint (0.7 x radius, as ScanColumn) within the climb limit (or the ground plane). A new floor more than 4.024 m below the old one is a
    damaging fall (config.json player.fall: damage above a 13 m/s landing, gravity 21).
    """

    def __init__(self, boxes, bounds, cell=0.25, radius=0.32, height=1.8, margin=0.4, footprint=0.7):
        self.cell = cell
        self.h = height
        self.ox = bounds["minX"] + margin
        self.oz = bounds["minZ"] + margin
        self.cols = int(math.floor((bounds["maxX"] - margin - self.ox) / cell))
        self.rows = int(math.floor((bounds["maxZ"] - margin - self.oz) / cell))
        solid = [b for b in boxes if not b["flags"]["bulletOnly"]]
        self.solid = solid
        self.inflated = [[] for _ in range(self.cols * self.rows)]
        self.support = [[] for _ in range(self.cols * self.rows)]
        for k, b in enumerate(solid):
            (x0, y0, z0), (x1, y1, z1) = b["min"], b["max"]
            # walls: within the capsule radius (MoveCapsule's push); floor: the footprint square of half-size 0.7 r
            # (ScanColumn), so the floor rises onto a stair tread before the next riser becomes a wall
            for lst, pad in ((self.inflated, radius), (self.support, footprint * radius)):
                i0 = max(0, int(math.ceil((x0 - pad - self.ox) / cell - 0.5 - 1e-9)))
                i1 = min(self.cols - 1, int(math.floor((x1 + pad - self.ox) / cell - 0.5 + 1e-9)))
                j0 = max(0, int(math.ceil((z0 - pad - self.oz) / cell - 0.5 - 1e-9)))
                j1 = min(self.rows - 1, int(math.floor((z1 + pad - self.oz) / cell - 0.5 + 1e-9)))
                for j in range(j0, j1 + 1):
                    base = j * self.cols
                    for i in range(i0, i1 + 1):
                        lst[base + i].append((y0, y1, k))

    def centre(self, c):
        return self.ox + (c % self.cols + 0.5) * self.cell, self.oz + (c // self.cols + 0.5) * self.cell

    def cell_at(self, x, z):
        i = int(math.floor((x - self.ox) / self.cell))
        j = int(math.floor((z - self.oz) / self.cell))
        if 0 <= i < self.cols and 0 <= j < self.rows:
            return j * self.cols + i
        return None

    def floor_at(self, c, h, climb):
        f = 0.0
        for y0, y1, _ in self.support[c]:
            if y1 <= h + climb + 1e-6 and y1 > f:
                f = y1
        return f

    def can_stand(self, c, f):
        for y0, y1, _ in self.inflated[c]:
            if y1 > f + 0.42 + 1e-6 and y0 < f + self.h - 1e-6:
                return False
        return True

    def crossing_ok(self, c, h, climb):
        for y0, y1, _ in self.inflated[c]:
            if y1 > h + climb + 1e-6 and y0 < h + self.h - 1e-6:
                return False
        return True

    def flood(self, start, jump=False, max_states=2_000_000):
        # a jump lifts the feet 1.0 m (launch 6.48 m/s, gravity 21) and an airborne body lands on tops within AIR_STEP
        # 0.08 of its feet, so a jump climbs 1.08 m; walking climbs STEP_HEIGHT 0.42. Chains (a crate, then a jump) come
        # from the flood itself.
        climb = 1.08 if jump else 0.42
        c0 = self.cell_at(start[0], start[2])
        f0 = self.floor_at(c0, start[1], 0.1)
        seen = {}
        falls = []
        q = [(c0, round(f0, 2))]
        seen[(c0, round(f0, 2))] = None
        cols = self.cols
        n = cols * self.rows
        k = 0
        while k < len(q):
            c, h = q[k]
            k += 1
            i = c % cols
            for d in (1, -1, cols, -cols):
                nb = c + d
                if nb < 0 or nb >= n or (d == 1 and i == cols - 1) or (d == -1 and i == 0):
                    continue
                f = self.floor_at(nb, h, climb)
                # the engine scans the floor under the 0.7 r footprint before the next riser comes within the radius
                # (MoveCapsule then ScanColumn), so the wall test runs from the higher of the two floors
                if not self.crossing_ok(nb, max(h, f), climb):
                    continue
                if not self.can_stand(nb, f):
                    if f >= h - climb:
                        continue
                    # stepping off an edge: the body falls past the wall it stood on and is pushed out from it while
                    # falling, so it lands a cell or two further on
                    ok = False
                    for _ in range(2):
                        nb2 = nb + d
                        if nb2 < 0 or nb2 >= n or (d == 1 and nb % cols == cols - 1) or (d == -1 and nb % cols == 0):
                            break
                        if not self.crossing_ok(nb2, h, climb):
                            break
                        nb = nb2
                        f = self.floor_at(nb, h, climb)
                        if self.can_stand(nb, f):
                            ok = True
                            break
                    if not ok:
                        continue
                key = (nb, round(f, 2))
                if h - f > 4.024:
                    falls.append((c, h, nb, f))
                if key in seen:
                    continue
                seen[key] = c
                q.append(key)
                if len(q) > max_states:
                    raise RuntimeError("flood too large")
        return seen, falls

    def reach_heights(self, seen):
        """cell -> list of floor heights reached."""
        out = {}
        for (c, h) in seen:
            out.setdefault(c, []).append(h)
        return out
