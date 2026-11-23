"""Close-up pass 4 tools for generated vehicle shells (used by assets/vehicles.py; nothing else imports it).

The generated body stays only as the large painted shell; these replace what a close camera reads:
  orient_outward   faces of the shell wound inward (their solidified inner layer, light headliner cloth, stood 1 cm
                   proud of the paint as torn white fragments): flipped by a two-way ray test
  rebuild_panes    every generated pane replaced by a clean pane: its border loop smoothed and resampled, a smooth
                   low-order surface fitted to the pane, the inside re-triangulated (constrained Delaunay) on it;
                   islands smaller than a pane (ghost mirror heads, shards) dropped; returns the seal loops
  drop_islands     loose islands and sliver faces near fitted parts (handles, mirrors, lamps) deleted
  settle           modelled parts (headrests on their posts) lowered until they clear the shell and the glass
  belt_strips      a 25 mm black belt moulding swept along the bottom edge of every side pane
"""
import math

import bmesh
import numpy as np
from mathutils import Vector
from mathutils import geometry as mg
from mathutils.bvhtree import BVHTree

from . import geo


def bvh_of(*obs):
    bm = bmesh.new()
    for ob in obs:
        if ob is None:
            continue
        me = ob.data.copy()
        me.transform(ob.matrix_world)
        bm.from_mesh(me)
        import bpy
        bpy.data.meshes.remove(me)
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t


def orient_outward(ob, keep=None, eps=0.002, reach=5.0):
    """Flip the faces whose normal points into the body: a ray along +n is blocked and a ray along -n escapes.
    keep(c, n) -> bool array limits the test (flanks, the exterior). Returns the number of flipped faces."""
    bm = geo.bm_of(ob)
    bm.faces.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(bm)
    nf = len(bm.faces)
    c = np.array([tuple(f.calc_center_median()) for f in bm.faces]).reshape(-1, 3)
    n = np.array([tuple(f.normal) for f in bm.faces]).reshape(-1, 3)
    sel = np.ones(nf, bool) if keep is None else keep(c, n)
    flip = []
    for i in np.nonzero(sel)[0]:
        nv = Vector(n[i])
        if nv.length < 0.5:
            continue
        cv = Vector(c[i])
        if bvh.ray_cast(cv + nv * eps, nv, reach)[0] is None:
            continue
        if bvh.ray_cast(cv - nv * eps, -nv, reach)[0] is None:
            flip.append(bm.faces[i])
    if flip:
        bmesh.ops.reverse_faces(bm, faces=flip)
    geo.bm_to(ob, bm)
    return len(flip)


# ------------------------------------------------------------------------------------------------------ glass
def _islands(bm):
    bm.faces.ensure_lookup_table()
    seen = np.zeros(len(bm.faces), bool)
    out = []
    for f0 in bm.faces:
        if seen[f0.index]:
            continue
        stack, isl = [f0], []
        seen[f0.index] = True
        while stack:
            f = stack.pop()
            isl.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if not seen[g.index]:
                        seen[g.index] = True
                        stack.append(g)
        out.append(isl)
    return out


def _loops_of(faces):
    """Ordered boundary loops (lists of BMVert) of a set of faces."""
    fs = set(faces)
    nxt = {}
    for f in faces:
        for e in f.edges:
            if sum(1 for g in e.link_faces if g in fs) == 1:
                a, b = e.verts
                nxt.setdefault(a, []).append(b)
                nxt.setdefault(b, []).append(a)
    seen, loops = set(), []
    for s in list(nxt):
        if s in seen:
            continue
        loop, prev, cur = [s], None, s
        seen.add(s)
        while True:
            cand = [v for v in nxt[cur] if v is not prev]
            if not cand:
                break
            n_ = cand[0]
            if n_ is s:
                break
            if n_ in seen:
                break
            loop.append(n_)
            seen.add(n_)
            prev, cur = cur, n_
        if len(loop) >= 6:
            loops.append(loop)
    return loops


def _fit(u, v, w, terms, iters=5):
    um, us = u.mean(), max(np.ptp(u) / 2, 1e-3)
    vm, vs = v.mean(), max(np.ptp(v) / 2, 1e-3)

    def basis(a, b):
        a, b = (np.asarray(a) - um) / us, (np.asarray(b) - vm) / vs
        return np.stack([a ** i * b ** j for i, j in terms], -1)
    A = basis(u, v)
    wt = np.ones(len(w))
    for _ in range(iters):
        cf = np.linalg.lstsq(A * wt[:, None], w * wt, rcond=None)[0]
        r = w - A @ cf
        s = max(1.4826 * np.median(np.abs(r)), 0.0015)
        wt = 1.0 / (1.0 + (r / (2.5 * s)) ** 2)
    return lambda a, b: basis(a, b) @ cf, float(np.median(np.abs(r)))


def _resample(P, step):
    seg = np.linalg.norm(np.roll(P, -1, 0) - P, axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    k = max(12, int(L / step))
    t = np.linspace(0, L, k, endpoint=False)
    Q = np.empty((k, P.shape[1]))
    Pc = np.vstack([P, P[:1]])
    for d in range(P.shape[1]):
        Q[:, d] = np.interp(t, s, Pc[:, d])
    return Q


def _inside(poly, q):
    x, y = q[:, 0], q[:, 1]
    ins = np.zeros(len(q), bool)
    px, py = poly[:, 0], poly[:, 1]
    qx, qy = np.roll(px, -1), np.roll(py, -1)
    for i in range(len(poly)):
        c = ((py[i] > y) != (qy[i] > y))
        xc = (qx[i] - px[i]) * (y - py[i]) / (qy[i] - py[i] + 1e-12) + px[i]
        ins ^= c & (x < xc)
    return ins


SIDE_TERMS = [(0, 0), (1, 0), (0, 1), (0, 2), (1, 1), (2, 0)]          # y = f(x, z): curved across z (tumblehome)
SCREEN_TERMS = [(0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2), (4, 0)]   # x = f(y, z): wrap across y


def rebuild_panes(ob, min_area=0.035, step=0.03, smooth_iters=30, name="Glass", drop=None):
    """Replace every pane of a generated glass object by a clean one (in place). drop(c) -> bool removes panes
    whose centre it flags. Returns [(loop (k, 3) array, outward normal, kind 'side'/'screen')]."""
    bm = geo.bm_of(ob)
    out_bm = bmesh.new()
    panes = []
    for isl in _islands(bm):
        area = sum(f.calc_area() for f in isl)
        if area < min_area:
            continue
        P = np.array([tuple(v.co) for f in isl for v in f.verts])
        nm = sum((f.normal * f.calc_area() for f in isl), Vector())
        nm = np.array(nm.normalized())
        cen = P.mean(0)
        if drop is not None and drop(cen):
            continue
        loops = _loops_of(isl)
        if not loops:
            continue
        lp = max(loops, key=len)
        L3 = np.array([tuple(v.co) for v in lp])
        if abs(nm[1]) > 0.55:
            ax, (a1, a2), terms, kind = 1, (0, 2), SIDE_TERMS, "side"
        elif abs(nm[0]) >= abs(nm[2]):
            ax, (a1, a2), terms, kind = 0, (1, 2), SCREEN_TERMS, "screen"
        else:
            ax, (a1, a2), terms, kind = 2, (0, 1), SIDE_TERMS, "roof"
        f, res = _fit(P[:, a1], P[:, a2], P[:, ax], terms)
        uv = L3[:, [a1, a2]].copy()
        for _ in range(smooth_iters):                 # the ragged border, smoothed along itself
            uv = 0.5 * uv + 0.25 * (np.roll(uv, 1, 0) + np.roll(uv, -1, 0))
        uv = _resample(uv, step * 0.6)
        lo, hi = uv.min(0), uv.max(0)
        gx, gy = np.meshgrid(np.arange(lo[0] + step / 2, hi[0], step), np.arange(lo[1] + step / 2, hi[1], step))
        g = np.stack([gx.ravel(), gy.ravel()], 1)
        if len(g):
            g = g[_inside(uv, g)]
        if len(g):
            d = np.min(np.linalg.norm(g[:, None, :] - uv[None, :, :], axis=2), axis=1)
            g = g[d > step * 0.45]
        pts = np.vstack([uv, g]) if len(g) else uv
        k = len(uv)
        edges = [(i, (i + 1) % k) for i in range(k)]
        try:
            r = mg.delaunay_2d_cdt([Vector((float(a), float(b))) for a, b in pts], edges, [], 2, 1e-6)
        except Exception:
            continue
        vco, tris = r[0], r[2]
        if not tris:
            continue
        uvn = np.array([(v.x, v.y) for v in vco])
        w = f(uvn[:, 0], uvn[:, 1])
        xyz = np.zeros((len(uvn), 3))
        xyz[:, a1], xyz[:, a2], xyz[:, ax] = uvn[:, 0], uvn[:, 1], w
        vs = [out_bm.verts.new(tuple(p)) for p in xyz]
        made = []
        for t in tris:
            if len(set(t)) < 3:
                continue
            try:
                made.append(out_bm.faces.new([vs[i] for i in t]))
            except ValueError:
                pass
        if made:
            fn = sum((fc.normal for fc in made), Vector())
            if float(np.dot(np.array(fn), nm)) < 0:
                bmesh.ops.reverse_faces(out_bm, faces=made)
        lw = f(uv[:, 0], uv[:, 1])
        L = np.zeros((len(uv), 3))
        L[:, a1], L[:, a2], L[:, ax] = uv[:, 0], uv[:, 1], lw
        panes.append((L, nm, kind))
    bm.free()
    bmesh.ops.remove_doubles(out_bm, verts=out_bm.verts[:], dist=1e-5)
    geo.bm_to(ob, out_bm)
    return panes


def seals(panes, radius=0.0055, grow=0.0, name="Seal"):
    """Rubber seal swept round every pane border (one ring every 3 cm at most), its centre line moved `grow`
    outward in the pane's plane so it covers the shell's cut edge."""
    out = []
    for L, nm, _k in panes:
        if grow:
            d = L - L.mean(0)
            d -= np.outer(d @ nm, nm)
            L = L + grow * d / (np.linalg.norm(d, axis=1)[:, None] + 1e-9)
        pts = [tuple(L[0])]
        for p in L[1:]:
            if np.linalg.norm(p - np.array(pts[-1])) >= 0.03:
                pts.append(tuple(p))
        if len(pts) < 4:
            continue
        pts.append(pts[0])
        out.append(geo.pipe(pts, radius, segments=6, name=name))
    return geo.join(out, name + "s") if out else None


def belt_strips(panes, belt, h=0.025, t=0.008, name="Belt"):
    """A black belt moulding (h tall, t thick, rounded) along the bottom edge of each side pane, just outboard of
    the glass: the run of the border loop lying within 6 cm of the pane's lowest point near the belt."""
    out = []
    for L, nm, kind in panes:
        if kind != "side":
            continue
        zmin = L[:, 2].min()
        if abs(zmin - belt) > 0.12:
            continue
        low = L[:, 2] < zmin + 0.05
        if low.sum() < 4:
            continue
        pts = L[low]
        pts = pts[np.argsort(pts[:, 0])]
        side = 1.0 if nm[1] > 0 else -1.0
        path = [(float(p[0]), float(p[1] + side * (t / 2 + 0.002)), float(p[2] - h / 2 + 0.006)) for p in pts]
        dedup = [path[0]]
        for p in path[1:]:
            if abs(p[0] - dedup[-1][0]) > 0.02:
                dedup.append(p)
        if len(dedup) < 2:
            continue
        prof = [(-t / 2, -h / 2), (t / 2, -h / 2), (t / 2, h / 2), (-t / 2, h / 2)]
        out.append(geo.sweep(prof, dedup, name=name, up=(0, 0, 1), bevel=0.003, bevel_segments=2))
    return out


# ------------------------------------------------------------------------------------------------- the shell
def drop_islands(ob, near, radius=0.06, min_area=0.004, max_aspect=8.0):
    """Delete loose islands (total area < min_area) and sliver faces (longest edge / height > max_aspect) of a
    shell within radius of any point in near [(x, y, z)] (fitted handles, mirrors, lamps, seals).
    Returns the number of deleted faces."""
    if not len(near):
        return 0
    bm = geo.bm_of(ob)
    nearp = np.asarray(near, float)

    def close(p):
        return np.min(np.linalg.norm(nearp - np.array(p), axis=1)) < radius
    kill = set()
    for isl in _islands(bm):
        a = sum(f.calc_area() for f in isl)
        if a < min_area and close(isl[0].calc_center_median()):
            kill.update(isl)
    for f in bm.faces:
        if f in kill or len(f.verts) != 3:
            continue
        a = f.calc_area()
        le = max(e.calc_length() for e in f.edges)
        if le < 1e-6:
            continue
        hgt = 2 * a / le
        if le / max(hgt, 1e-7) > max_aspect and close(f.calc_center_median()):
            kill.add(f)
    bmesh.ops.delete(bm, geom=list(kill), context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    geo.bm_to(ob, bm)
    return len(kill)


def settle(parts, bvh, centre_z, margin=0.06, step=0.01, max_drop=0.24):
    """Lower each group of parts until every vertex clears the shell / glass (bvh) by margin, seen from the
    cabin's centre line at height centre_z. parts: list of lists of objects moved together. Returns drops."""
    drops = []
    for grp in parts:
        co = np.vstack([geo.arrays(o)[0] for o in grp])
        if len(co) > 160:
            co = co[np.linspace(0, len(co) - 1, 160).astype(int)]
        dz = 0.0
        while dz <= max_drop:
            bad = False
            for p in co:
                q = Vector((p[0], p[1] * 0.3, centre_z))
                tgt = Vector((p[0], p[1], p[2] - dz))
                d = tgt - q
                L = d.length
                if L < 1e-4:
                    continue
                h = bvh.ray_cast(q, d / L, L + margin)
                if h[0] is not None:
                    bad = True
                    break
            if not bad:
                break
            dz += step
        if dz > 0:
            for o in grp:
                geo.transform(o, loc=(0, 0, -dz))
        drops.append(round(dz, 3))
    return drops
