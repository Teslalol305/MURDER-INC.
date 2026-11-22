"""Built-up steelwork (and anything else made of straight members) assembled in numpy.

    from mi import steel
    b = steel.Builder(step=0.15, seed=1)
    b.box((-0.25, -0.24, 0.3), (-0.234, 0.24, 5.27), "steel")                    # a plate, subdivided for the masks
    b.prism(steel.angle(0.10, 0.14, 0.012), heel, a_dir, b_dir, (0, 0, 4.9), "steel")   # a rolled angle
    b.plate_rows([(l0, r0), (l1, r1), (l2, r2)], 0.012, "steel")                 # trapezoid / gusset with a grid
    b.rivets(points, normal, "steel")                                            # 36 mm button heads
    b.absorb(geo.box((1.04, 1.04, 0.26), bevel=0.02), "concrete")                # any Blender mesh
    ob = b.finish("SM_El_Column", {"steel": mat_steel, "concrete": mat_concrete}, col)
    W = b.loops(ob, ao=0.12)            # per-corner position, face normal, convex / concave tags, occlusion
    geo.set_wear(ob, rgba, per="corner")

Why not bmesh: a bent of the El has two thousand rivets and several hundred plates and angles; numpy builds it in
well under a second, every part gets UVs in real metres without stretch (each face is projected in its own plane,
v up the wall, 1 UV unit = the tile of the part's material), and every vertex knows whether it is a convex edge
(paint chips, rust starts) or a concave root (dirt sits), which is what the wear masks are painted from.

Faces are subdivided to about `step` metres so the vertex-colour masks have something to live on.
"""
import math

import bpy
import numpy as np

from . import geo as _geo
from . import scene as _scene


# ------------------------------------------------------------------------------------------------------- profiles
# Lists of (a, b), counter-clockwise. A prism puts a along its u vector and b along its v vector.

def rect(w, h, a0=0.0, b0=0.0, chamfer=0.0):
    c = min(chamfer, 0.45 * w, 0.45 * h)
    if c > 0:
        return [(a0 + c, b0), (a0 + w - c, b0), (a0 + w, b0 + c), (a0 + w, b0 + h - c), (a0 + w - c, b0 + h),
                (a0 + c, b0 + h), (a0, b0 + h - c), (a0, b0 + c)]
    return [(a0, b0), (a0 + w, b0), (a0 + w, b0 + h), (a0, b0 + h)]


def angle(w, h, t, r=None):
    """Rolled angle: heel at (0, 0), one leg along +a (length w), one along +b (length h), thickness t, a root
    fillet and rounded toes."""
    r = 0.8 * t if r is None else r
    k = r * (1.0 - 0.7071)
    c = 0.35 * t
    return [(0, 0), (w, 0), (w, t - c), (w - c, t), (t + r, t), (t + k, t + k), (t, t + r), (t, h - c), (t - c, h), (0, h)]


def ibeam(d, bf, tf, tw):
    """Rolled I beam (tapered flanges): centred on a = 0, b from 0 (bottom) to d (top)."""
    r = 0.9 * tw
    right = [(bf / 2, 0), (bf / 2, 0.72 * tf), (tw / 2 + r, 1.2 * tf), (tw / 2, 1.2 * tf + r), (tw / 2, d - 1.2 * tf - r),
             (tw / 2 + r, d - 1.2 * tf), (bf / 2, d - 0.72 * tf), (bf / 2, d)]
    return right + [(-a, b_) for a, b_ in reversed(right)]


def channel(d, bf, tf, tw):
    """Rolled channel: back on a = 0, flanges toward +a, b from 0 to d."""
    return [(0, 0), (bf, 0), (bf, 0.75 * tf), (tw + 0.8 * tw, 1.25 * tf), (tw, 1.25 * tf + 0.8 * tw), (tw, d - 1.25 * tf - 0.8 * tw),
            (tw + 0.8 * tw, d - 1.25 * tf), (bf, d - 0.75 * tf), (bf, d), (0, d)]


def rail(h=0.140, base=0.140, head=0.070, web=0.0145):
    """Flat-bottom running rail (about 100 lb per yard): centred on a = 0, b from 0 (foot) to h (running surface)."""
    hb, hh, hw = base / 2, head / 2, web / 2
    right = [(hb, 0), (hb, 0.009), (hw + 0.012, 0.022), (hw, 0.034), (hw, h - 0.046), (hh - 0.006, h - 0.036), (hh, h - 0.028),
             (hh, h - 0.008), (hh - 0.008, h)]
    return right + [(-a, b_) for a, b_ in reversed(right)]


def unit(v):
    v = np.asarray(v, dtype=np.float64)
    return v / max(np.linalg.norm(v), 1e-12)


# -------------------------------------------------------------------------------------------------------- builder

class Builder:
    """Collects parts (vertices, polygons, slot key, wear tags) and turns them into one mesh object."""

    RIVET, MEMBER, OTHER = 1, 0, 2

    def __init__(self, step=0.15, chamfer=0.0, seed=0):
        self.step = step
        self.chamfer = chamfer
        self.rng = np.random.default_rng(seed + 1009)
        self.parts = []
        self.leaks = []            # points that bleed rust (a share of the rivets, connections you add yourself)

    # ---- low level
    def _add(self, verts, loops, totals, slot, tags=None, vdir=(0, 0, 1), fdir=(1, 0, 0), uv_off=None, uv_org=None, kind=0):
        """vdir: direction the texture's v axis follows on this part (up the wall for steel and concrete, along
        the grain for timber); fdir: the fallback for faces square to vdir. uv_off: UV offset (random per part
        by default, so equal members do not show the same piece of the tile); uv_org: point the UVs are
        measured from (with uv_off it pins a known part of the texture to the part, e.g. one board per tie)."""
        verts = np.asarray(verts, dtype=np.float64).reshape(-1, 3)
        if tags is None:
            tags = np.zeros((len(verts), 2))
        p = dict(v=verts, loops=np.asarray(loops, dtype=np.int64), totals=np.asarray(totals, dtype=np.int64), slot=slot,
                 tags=np.asarray(tags, dtype=np.float64), vdir=unit(vdir), fdir=unit(fdir),
                 uv_off=self.rng.uniform(0, 1, 2) if uv_off is None else np.asarray(uv_off, dtype=np.float64),
                 uv_org=np.zeros(3) if uv_org is None else np.asarray(uv_org, dtype=np.float64), kind=kind)
        self.parts.append(p)
        return p

    def merge(self, other, matrix=None):
        """Take the parts of another Builder, moved by a 4x4 matrix (rotation + translation, no mirror)."""
        M = np.eye(4) if matrix is None else np.asarray(matrix, dtype=np.float64)
        R, t = M[:3, :3], M[:3, 3]
        for p in other.parts:
            q = dict(p)
            q["v"] = p["v"] @ R.T + t
            q["vdir"], q["fdir"] = R @ p["vdir"], R @ p["fdir"]
            q["uv_org"] = R @ p["uv_org"] + t
            self.parts.append(q)
        self.leaks += [tuple(R @ np.asarray(l) + t) for l in other.leaks]
        other.parts, other.leaks = [], []
        return self

    # ---- members
    def prism(self, profile, origin, u, v, ext, slot, step=None, pstep=None, caps=True, **kw):
        """Extrude a closed profile [(a, b)] from `origin` along the vector `ext`; a runs along u, b along v
        (unit vectors, perpendicular to ext). Any handedness: the profile is flipped when needed so the faces
        look outward. Convex profile corners are tagged for edge wear, concave ones for dirt."""
        step = step or self.step
        pstep = pstep or step
        prof = np.asarray(profile, dtype=np.float64)
        u, v, ext = np.asarray(u, dtype=np.float64), np.asarray(v, dtype=np.float64), np.asarray(ext, dtype=np.float64)
        length = float(np.linalg.norm(ext))
        ax = ext / length
        if np.dot(np.cross(u, v), ax) < 0:
            prof = prof[::-1]
        k = len(prof)
        prev, nxt = prof[np.arange(k) - 1], prof[(np.arange(k) + 1) % k]
        d1, d2 = prof - prev, nxt - prof
        area2 = float(np.sum(prof[:, 0] * nxt[:, 1] - nxt[:, 0] * prof[:, 1]))        # > 0: counter-clockwise in (a, b)
        turn = (d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]) * (1.0 if area2 >= 0 else -1.0)   # > 0: convex corner
        turn = turn / np.maximum(np.linalg.norm(d1, axis=1) * np.linalg.norm(d2, axis=1), 1e-12)
        pts, tg = [], []
        for i in range(k):
            p0, p1 = prof[i], prof[(i + 1) % k]
            n = max(1, int(math.ceil(np.linalg.norm(p1 - p0) / pstep - 1e-6)))
            for j in range(n):
                pts.append(p0 + (p1 - p0) * j / n)
                tg.append((max(0.0, turn[i]), max(0.0, -turn[i])) if j == 0 else (0.0, 0.0))
        pts, tg = np.array(pts), np.array(tg)
        m = len(pts)
        ns = max(1, int(math.ceil(length / step - 1e-6)))
        t = np.linspace(0.0, length, ns + 1)
        ring = np.asarray(origin, dtype=np.float64)[None, :] + pts[:, :1] * u[None, :] + pts[:, 1:2] * v[None, :]
        verts = (ring[None, :, :] + t[:, None, None] * ax[None, None, :]).reshape(-1, 3)
        tags = np.tile(tg, (ns + 1, 1))
        tags[:m, 0] = np.maximum(tags[:m, 0], 0.6)
        tags[-m:, 0] = np.maximum(tags[-m:, 0], 0.6)
        j = np.arange(ns)[:, None] * m
        i = np.arange(m)[None, :]
        i1 = (i + 1) % m
        quads = np.stack([j + i, j + i1, j + m + i1, j + m + i], axis=-1).reshape(-1, 4)
        loops = [quads.ravel()]
        totals = [np.full(len(quads), 4)]
        if caps:
            loops += [np.arange(m)[::-1], ns * m + np.arange(m)]
            totals += [np.array([m, m])]
        kw.setdefault("fdir", ax)
        kw.setdefault("kind", self.MEMBER if caps else self.OTHER)
        return self._add(verts, np.concatenate(loops), np.concatenate(totals), slot, tags, **kw)

    def box(self, lo, hi, slot, axis=None, chamfer=None, **kw):
        """Axis-aligned plate or bar from corner lo to corner hi, extruded along its longest side (or `axis`)."""
        lo, hi = np.asarray(lo, dtype=np.float64), np.asarray(hi, dtype=np.float64)
        lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
        size = hi - lo
        k = int(np.argmax(size)) if axis is None else "xyz".index(axis) if isinstance(axis, str) else axis
        i, j = (k + 1) % 3, (k + 2) % 3
        e = np.eye(3)
        c = self.chamfer if chamfer is None else chamfer
        return self.prism(rect(size[i], size[j], chamfer=c), lo, e[i], e[j], e[k] * size[k], slot, **kw)

    def plate_rows(self, rows, thickness, slot, step=None, **kw):
        """Flat plate given as rows of (left point, right point), bottom row first; its front face looks along
        (right - left) x (next row - this row) and the plate is `thickness` deep behind it. Two rows make a
        rectangle or trapezoid, more rows any outline that is convex across (wing plates, gussets)."""
        step = step or self.step
        rows = [(np.asarray(a, dtype=np.float64), np.asarray(b_, dtype=np.float64)) for a, b_ in rows]
        nu = max(1, int(math.ceil(max(np.linalg.norm(b_ - a) for a, b_ in rows) / step - 1e-6)))
        s = np.linspace(0, 1, nu + 1)[:, None]
        grid = []
        for r in range(len(rows) - 1):
            (a0, b0), (a1, b1) = rows[r], rows[r + 1]
            nv = max(1, int(math.ceil(max(np.linalg.norm(a1 - a0), np.linalg.norm(b1 - b0)) / step - 1e-6)))
            for q in range(nv + (1 if r == len(rows) - 2 else 0)):
                f = q / nv
                la, rb = a0 + (a1 - a0) * f, b0 + (b1 - b0) * f
                grid.append(la[None, :] + (rb - la)[None, :] * s)
        F = np.array(grid)                                   # (rows, nu + 1, 3)
        nr = F.shape[0]
        n = unit(np.cross(rows[0][1] - rows[0][0], rows[-1][0] - rows[0][0] + rows[-1][1] - rows[0][1]))
        Bk = F - n[None, None, :] * thickness
        nvf = nr * (nu + 1)
        verts = np.concatenate([F.reshape(-1, 3), Bk.reshape(-1, 3)])
        idx = lambda r, c: r * (nu + 1) + c
        r_, c_ = np.meshgrid(np.arange(nr - 1), np.arange(nu), indexing="ij")
        r_, c_ = r_.ravel(), c_.ravel()
        front = np.stack([idx(r_, c_), idx(r_, c_ + 1), idx(r_ + 1, c_ + 1), idx(r_ + 1, c_)], axis=-1)
        back = front[:, ::-1] + nvf
        c = np.arange(nu)
        r = np.arange(nr - 1)
        bottom = np.stack([idx(0, c + 1), idx(0, c), idx(0, c) + nvf, idx(0, c + 1) + nvf], axis=-1)
        top = np.stack([idx(nr - 1, c), idx(nr - 1, c + 1), idx(nr - 1, c + 1) + nvf, idx(nr - 1, c) + nvf], axis=-1)
        left = np.stack([idx(r, 0), idx(r + 1, 0), idx(r + 1, 0) + nvf, idx(r, 0) + nvf], axis=-1)
        right = np.stack([idx(r + 1, nu), idx(r, nu), idx(r, nu) + nvf, idx(r + 1, nu) + nvf], axis=-1)
        quads = np.concatenate([front, back, bottom, top, left, right])
        edge = np.zeros((nr, nu + 1))
        edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = 1.0
        tags = np.zeros((2 * nvf, 2))
        tags[:, 0] = np.concatenate([edge.ravel(), edge.ravel()])
        return self._add(verts, quads.ravel(), np.full(len(quads), 4), slot, tags, **kw)

    def poly_plate(self, outline, thickness, slot, step=None, **kw):
        """Flat plate from a planar outline (counter-clockwise seen from its front), `thickness` deep behind it.
        The faces are n-gons: use it for small gussets; plate_rows gives a grid."""
        step = step or self.step
        P = np.asarray(outline, dtype=np.float64)
        pts = []
        for i in range(len(P)):
            p0, p1 = P[i], P[(i + 1) % len(P)]
            n_ = max(1, int(math.ceil(np.linalg.norm(p1 - p0) / step - 1e-6)))
            pts += [p0 + (p1 - p0) * j / n_ for j in range(n_)]
        P = np.array(pts)
        k = len(P)
        nrm = unit(np.sum(np.cross(P, np.roll(P, -1, axis=0)), axis=0))
        verts = np.concatenate([P, P - nrm[None, :] * thickness])
        i = np.arange(k)
        i1 = (i + 1) % k
        sides = np.stack([i1, i, i + k, i1 + k], axis=-1)
        loops = np.concatenate([i, (i + k)[::-1], sides.ravel()])
        totals = np.concatenate([[k, k], np.full(k, 4)])
        tags = np.zeros((2 * k, 2))
        tags[:, 0] = 1.0
        return self._add(verts, loops, totals, slot, tags, **kw)

    def rivets(self, points, normal, slot, d=0.036, h=0.015, seg=8, jitter=0.0015, leak=0.12):
        """Button-head rivets (36 mm across, 15 mm high: ART_BIBLE 3.4) at `points`, heads rising along
        `normal` (one vector or one per point). A share `leak` of them is remembered as a rust-streak source."""
        P = np.asarray(points, dtype=np.float64).reshape(-1, 3)
        if len(P) == 0:
            return None
        N = np.broadcast_to(np.asarray(normal, dtype=np.float64), P.shape).copy()
        N /= np.linalg.norm(N, axis=1, keepdims=True)
        ref = np.where(np.abs(N[:, 2:3]) > 0.9, np.array([[1.0, 0.0, 0.0]]), np.array([[0.0, 0.0, 1.0]]))
        t1 = np.cross(N, ref)
        t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
        t2 = np.cross(N, t1)
        if jitter:
            P = P + t1 * self.rng.uniform(-jitter, jitter, (len(P), 1)) + t2 * self.rng.uniform(-jitter, jitter, (len(P), 1))
        a = np.linspace(0, 2 * np.pi, seg, endpoint=False)
        r = d / 2
        tpl = np.concatenate([np.stack([r * np.cos(a), r * np.sin(a), np.zeros(seg)], axis=1),
                              np.stack([0.70 * r * np.cos(a), 0.70 * r * np.sin(a), np.full(seg, 0.66 * h)], axis=1),
                              [[0.0, 0.0, h]]])                                          # (2 seg + 1, 3)
        nv = len(tpl)
        verts = (P[:, None, :] + tpl[None, :, 0:1] * t1[:, None, :] + tpl[None, :, 1:2] * t2[:, None, :]
                 + tpl[None, :, 2:3] * N[:, None, :]).reshape(-1, 3)
        i = np.arange(seg)
        i1 = (i + 1) % seg
        quads = np.stack([i, i1, seg + i1, seg + i], axis=-1)
        tris = np.stack([seg + i, seg + i1, np.full(seg, 2 * seg)], axis=-1)
        base = (np.arange(len(P)) * nv)[:, None]
        loops = np.concatenate([(quads.ravel()[None, :] + base).ravel(), (tris.ravel()[None, :] + base).ravel()])
        totals = np.concatenate([np.full(len(P) * seg, 4), np.full(len(P) * seg, 3)])
        tg = np.zeros((nv, 2))
        tg[:seg, 1] = 1.0            # the crevice round the head
        tg[seg:, 0] = 0.5            # the crown
        if leak > 0:
            pick = self.rng.random(len(P)) < leak
            self.leaks += [tuple(p) for p in P[pick]]
        return self._add(verts, loops, totals, slot, np.tile(tg, (len(P), 1)), kind=self.RIVET)

    def absorb(self, ob, slot, kind=2, **kw):
        """Take over a Blender mesh object (it is removed): bevelled boxes, pipes, lathed parts, bolts."""
        me = ob.data
        me.transform(ob.matrix_world)
        co, _ = _geo.arrays(ob)
        nl, npoly = len(me.loops), len(me.polygons)
        lv = np.empty(nl, dtype=np.int32)
        lt = np.empty(npoly, dtype=np.int32)
        me.loops.foreach_get("vertex_index", lv)
        me.polygons.foreach_get("loop_total", lt)
        try:
            cv = _geo.curvature(ob)
            tags = np.stack([np.clip(-cv * 5.0, 0, 1), np.clip(cv * 4.0, 0, 1)], axis=1)
        except Exception:
            tags = None
        p = self._add(co.astype(np.float64), lv, lt, slot, tags, kind=kind, **kw)
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.meshes.remove(me)
        return p

    # ---- output
    def finish(self, name, materials, col=None, smooth=40.0, check=True):
        """Build the object. materials: {slot key: material}; UVs are divided by each material's real tile size
        (material["mi_tile_m"], default 2 m). Slots appear in the order the keys are first used."""
        order = []
        for p in self.parts:
            if p["slot"] not in order:
                order.append(p["slot"])
        nv = np.cumsum([0] + [len(p["v"]) for p in self.parts])
        V = np.concatenate([p["v"] for p in self.parts])
        LV = np.concatenate([p["loops"] + nv[i] for i, p in enumerate(self.parts)])
        LT = np.concatenate([p["totals"] for p in self.parts])
        nface = np.array([len(p["totals"]) for p in self.parts])
        fpart = np.repeat(np.arange(len(self.parts)), nface)
        LS = np.concatenate([[0], np.cumsum(LT)[:-1]])
        lface = np.repeat(np.arange(len(LT)), LT)
        P = V[LV]
        # face normals (Newell) and per-face texture frames
        nxt = np.arange(len(LV)) + 1
        last = LS + LT - 1
        nxt[last] = LS
        cr = np.cross(P, P[nxt])
        FN = np.add.reduceat(cr, LS, axis=0)                              # 2 x vector area of each face
        if check:
            # closed parts must have positive volume (faces looking outward): V = sum(p . area vector) / 3
            c0 = np.array([p["v"].mean(axis=0) for p in self.parts])[fpart]
            vol = np.einsum("ij,ij->i", P[LS] - c0, FN)
            pv = np.add.reduceat(vol, np.concatenate([[0], np.cumsum(nface)[:-1]]))
            bad = [i for i, p in enumerate(self.parts) if p["kind"] == self.MEMBER and pv[i] < 0]
            if bad:
                raise ValueError("%s: %d parts are inside out (first: part %d, slot %s)" % (name, len(bad), bad[0], self.parts[bad[0]]["slot"]))
        FN /= np.maximum(np.linalg.norm(FN, axis=1, keepdims=True), 1e-20)
        vd = np.array([p["vdir"] for p in self.parts])[fpart]
        fd = np.array([p["fdir"] for p in self.parts])[fpart]
        va = vd - np.einsum("ij,ij->i", vd, FN)[:, None] * FN
        weak = np.linalg.norm(va, axis=1) < 0.35
        vb = fd - np.einsum("ij,ij->i", fd, FN)[:, None] * FN
        weak2 = weak & (np.linalg.norm(vb, axis=1) < 0.35)
        vb[weak2] = np.cross(FN[weak2], np.array([0.0, 1.0, 0.0]))
        va[weak] = vb[weak]
        va /= np.maximum(np.linalg.norm(va, axis=1, keepdims=True), 1e-20)
        ua = np.cross(va, FN)
        tiles = np.array([_tile(materials[p["slot"]]) for p in self.parts])[fpart]
        offs = np.array([p["uv_off"] for p in self.parts])[fpart]
        Pr = P - np.array([p["uv_org"] for p in self.parts])[fpart][lface]
        UVc = np.stack([np.einsum("ij,ij->i", Pr, ua[lface]) / tiles[lface, 0] + offs[lface, 0],
                        np.einsum("ij,ij->i", Pr, va[lface]) / tiles[lface, 1] + offs[lface, 1]], axis=1)
        me = bpy.data.meshes.new(name)
        me.vertices.add(len(V))
        me.vertices.foreach_set("co", V.astype(np.float32).ravel())
        me.loops.add(len(LV))
        me.loops.foreach_set("vertex_index", LV.astype(np.int32))
        me.polygons.add(len(LT))
        me.polygons.foreach_set("loop_start", LS.astype(np.int32))
        me.polygons.foreach_set("material_index", np.array([order.index(p["slot"]) for p in self.parts], dtype=np.int32)[fpart])
        me.update(calc_edges=True)
        for key in order:
            me.materials.append(materials[key])
        uvl = me.uv_layers.new(name=_geo.UV)
        uvl.data.foreach_set("uv", UVc.astype(np.float32).ravel())
        ob = _scene.new_object(name, me, col)
        if smooth is not None:
            _geo.smooth_by_angle(ob, smooth)
        _geo.ensure_wear(ob)
        self._out = dict(P=P, N=FN[lface], lv=LV, tags=np.concatenate([p["tags"] for p in self.parts])[LV],
                         kind=np.array([p["kind"] for p in self.parts])[fpart][lface],
                         slot=np.array([order.index(p["slot"]) for p in self.parts])[fpart][lface],
                         part=fpart[lface], order=order)
        return ob

    def loops(self, ob, ao=0.12, rays=8, others=(), seed=1):
        """Per-corner data for painting the Wear mask: a namespace with P (n, 3) positions, N face normals,
        convex and concave tags, kind (RIVET / MEMBER / OTHER), slot (index) and names (slot keys), part (index)
        and ao (0..1, ambient occlusion within `ao` metres; 0 everywhere when ao is None)."""
        o = self._out

        class W:
            pass
        W.P, W.N, W.kind, W.slot, W.names, W.part = o["P"], o["N"], o["kind"], o["slot"], o["order"], o["part"]
        W.convex, W.concave = o["tags"][:, 0], o["tags"][:, 1]
        W.ao = _geo.occlusion(ob, ao, rays, seed, others)[o["lv"]] if ao else np.zeros(len(o["P"]))
        W.is_slot = lambda key: (o["slot"] == o["order"].index(key)) if key in o["order"] else np.zeros(len(o["P"]), dtype=bool)
        return W


def _tile(material):
    t = material.get("mi_tile_m") if material is not None else None
    return (float(t[0]), float(t[1])) if t is not None else (2.0, 2.0)


def streaks(P, N, sources, length=0.5, width=0.03, seed=0):
    """Leak mask (0..1) for corners at P with face normals N: rust runs down steep faces below each source point.
    Each run is `length` (x 0.35..1) long and widens as it falls."""
    out = np.zeros(len(P))
    if len(sources) == 0:
        return out
    S = np.asarray(sources, dtype=np.float64)
    r = np.random.default_rng(seed + 5)
    steep = np.clip(1.0 - np.abs(N[:, 2]) * 1.3, 0, 1)
    idx = np.nonzero(steep > 0.05)[0]
    Pp = P[idx]
    order = np.argsort(Pp[:, 0])
    Pp, idx = Pp[order], idx[order]
    Ls = length * (0.35 + 0.65 * r.random(len(S)))
    Ws = width * (0.6 + 0.9 * r.random(len(S)))
    for s, L, w in zip(S, Ls, Ws):
        a, b = np.searchsorted(Pp[:, 0], [s[0] - 4 * w - 0.08, s[0] + 4 * w + 0.08])
        if b <= a:
            continue
        q = Pp[a:b]
        dz = s[2] - q[:, 2]
        dh = np.hypot(q[:, 0] - s[0], q[:, 1] - s[1])
        m = (dz > -0.01) & (dz < L) & (dh < 4 * w + 0.08)
        if not m.any():
            continue
        fall = np.exp(-(dh[m] / (w * (1.5 + 2.0 * dz[m] / L))) ** 2) * (1 - dz[m] / L) ** 0.7
        ii = idx[a:b][m]
        out[ii] = np.maximum(out[ii], fall)
    return out * steep
