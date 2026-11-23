"""Shape kit for the player guns (weapons rebuild round 1): splines, parametric cross-sections with analytic
arc-length, lofts through them, swept and pressed sheet, deformations that dent a surface in place.

Everything here returns plain mesh objects (no materials, no bones); assets/weapons.py finishes them with P().
Units are metres, gun space (X forward along the bore, Y left, Z up).
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from mi import geo


# ----------------------------------------------------------------------------------------------- curves

def spline(pts, n=8, closed=False):
    """Uniform Catmull-Rom through pts (2D or 3D), n samples per span. Open curves end exactly on the last point."""
    P = np.asarray(pts, dtype=np.float64)
    if closed:
        Q = np.vstack([P[-1:], P, P[:2]])
    else:
        Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    if not closed:
        out.append(P[-1])
    return np.array(out)


def x_of_z(curve, z):
    """x on a side-view curve [(x, z)] (any order) at height z (linear between samples)."""
    c = np.asarray(curve)
    o = np.argsort(c[:, 1])
    return np.interp(z, c[o, 1], c[o, 0])


def resample(poly, count, closed=True):
    """Polyline resampled to `count` points evenly spaced by arc length."""
    P = np.asarray(poly, dtype=np.float64)
    Q = np.vstack([P, P[:1]]) if closed else P
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    t = np.linspace(0, d[-1], count, endpoint=not closed)
    return np.stack([np.interp(t, d, Q[:, k]) for k in range(Q.shape[1])], 1)


def arc(c, r, a0, a1, n):
    a = np.linspace(a0, a1, n)
    return np.stack([c[0] + r * np.cos(a), c[1] + r * np.sin(a)], 1)


# ----------------------------------------------------------------------------------------------- sections

class Section:
    """Closed 2D contour (u, v) with an analytic arc-length parameter s (0 at the start, L at the end): dense
    points P (K, 2), s (K,), outward normals N (K, 2). at(s) samples positions, normal_at(s) normals."""

    def __init__(self, P, s, L):
        self.P, self.s, self.L = np.asarray(P), np.asarray(s), float(L)
        T = np.roll(self.P, -1, 0) - np.roll(self.P, 1, 0)
        T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
        self.N = np.stack([T[:, 1], -T[:, 0]], 1)          # counter-clockwise contour: outward is to the right

    def at(self, s):
        s = np.mod(np.asarray(s, dtype=np.float64), self.L)
        ss = np.r_[self.s, self.L]
        PP = np.vstack([self.P, self.P[:1]])
        return np.stack([np.interp(s, ss, PP[:, 0]), np.interp(s, ss, PP[:, 1])], -1)

    def normal_at(self, s):
        s = np.mod(np.asarray(s, dtype=np.float64), self.L)
        ss = np.r_[self.s, self.L]
        NN = np.vstack([self.N, self.N[:1]])
        n = np.stack([np.interp(s, ss, NN[:, 0]), np.interp(s, ss, NN[:, 1])], -1)
        return n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)

    def ring(self, M):
        return self.at(np.linspace(0, self.L, M, endpoint=False))


def rrect(x0, x1, w, rb, rf, bulge_b=0.0, bulge_f=0.0, crown=0.0, K=480):
    """Rounded rectangle in (x, y), x0 back .. x1 front, half width w, corner radii rb (back) and rf (front),
    counter-clockwise seen from +Z, starting at the back centre (x0, 0) heading to -y (the right side).
    bulge_b / bulge_f: the back / front faces bow outward by this much at the middle (convex across their
    width); crown: the sides bow outward by this much at mid length. Returns a Section; its s is the arc length of
    the plain rounded rectangle, so the same s means the same feature on every section of a loft.
    marks: s at the start and end of the right and left side flats."""
    rb, rf = min(rb, w * 0.999, (x1 - x0) * 0.49), min(rf, w * 0.999, (x1 - x0) * 0.49)
    segs = []                                                   # (kind, data, length)
    segs.append(("line", ((x0, 0.0), (x0, -(w - rb))), w - rb))
    segs.append(("arc", ((x0 + rb, -(w - rb)), rb, math.pi, 1.5 * math.pi), 0.5 * math.pi * rb))
    segs.append(("line", ((x0 + rb, -w), (x1 - rf, -w)), x1 - rf - x0 - rb))
    segs.append(("arc", ((x1 - rf, -(w - rf)), rf, 1.5 * math.pi, 2 * math.pi), 0.5 * math.pi * rf))
    segs.append(("line", ((x1, -(w - rf)), (x1, w - rf)), 2 * (w - rf)))
    segs.append(("arc", ((x1 - rf, w - rf), rf, 0.0, 0.5 * math.pi), 0.5 * math.pi * rf))
    segs.append(("line", ((x1 - rf, w), (x0 + rb, w)), x1 - rf - x0 - rb))
    segs.append(("arc", ((x0 + rb, w - rb), rb, 0.5 * math.pi, math.pi), 0.5 * math.pi * rb))
    segs.append(("line", ((x0, w - rb), (x0, 0.0)), w - rb))
    L = sum(s[2] for s in segs)
    pts, ss = [], []
    acc = 0.0
    marks = {}
    for i, (kind, d, ln) in enumerate(segs):
        k = max(2, int(round(K * ln / L)))
        t = np.linspace(0, 1, k, endpoint=False)
        if kind == "line":
            a, b = np.array(d[0]), np.array(d[1])
            p = a[None] + (b - a)[None] * t[:, None]
        else:
            c, r, a0, a1 = d
            ang = a0 + (a1 - a0) * t
            p = np.stack([c[0] + r * np.cos(ang), c[1] + r * np.sin(ang)], 1)
        pts.append(p)
        ss.append(acc + ln * t)
        if i == 2:
            marks["right"] = (acc, acc + ln)
        if i == 6:
            marks["left"] = (acc, acc + ln)
        acc += ln
    P = np.vstack(pts)
    s = np.concatenate(ss)
    hb, hf = max(w - rb, 1e-6), max(w - rf, 1e-6)
    if bulge_b:
        m = P[:, 0] < x0 + rb + 1e-9
        P[m, 0] -= bulge_b * np.clip(1 - (P[m, 1] / (w * 0.98)) ** 2, 0, 1) ** 1.2
    if bulge_f:
        m = P[:, 0] > x1 - rf - 1e-9
        P[m, 0] += bulge_f * np.clip(1 - (P[m, 1] / (w * 0.98)) ** 2, 0, 1) ** 1.2
    if crown:
        xm, hx = (x0 + x1) / 2, (x1 - x0) / 2
        P[:, 1] += np.sign(P[:, 1]) * crown * np.clip(1 - ((P[:, 0] - xm) / hx) ** 2, 0, 1)
    sec = Section(P, s, L)
    sec.marks = marks
    sec.w, sec.x0, sec.x1, sec.rb, sec.rf = w, x0, x1, rb, rf
    return sec


def poly_section(poly, K=480):
    """Section from any closed counter-clockwise polygon (s = arc length of the polygon itself)."""
    P = np.asarray(poly, dtype=np.float64)
    Q = np.vstack([P, P[:1]])
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
    t = np.linspace(0, d[-1], K, endpoint=False)
    R = np.stack([np.interp(t, d, Q[:, 0]), np.interp(t, d, Q[:, 1])], 1)
    return Section(R, t, d[-1])


# ----------------------------------------------------------------------------------------------- meshes

def grid_mesh(V, name="Grid", closed_u=False, closed_v=False, cap=False):
    """Quad mesh through a grid of points V (n, m, 3). closed_v: rows wrap (rings); cap: close the two end rings
    (only with closed_v)."""
    V = np.asarray(V, dtype=np.float64)
    n, m = V.shape[:2]
    faces = []
    for i in range(n - 1 if not closed_u else n):
        i1 = (i + 1) % n
        for j in range(m - 1 if not closed_v else m):
            j1 = (j + 1) % m
            faces.append((i * m + j, i * m + j1, i1 * m + j1, i1 * m + j))
    if cap and closed_v and not closed_u:
        faces.append(tuple(range(m - 1, -1, -1)))
        faces.append(tuple((n - 1) * m + j for j in range(m)))
    ob = geo.from_arrays(name, V.reshape(-1, 3), faces, smooth=None)
    return ob


def outward(ob):
    """Closed mesh: consistent normals pointing out (signed volume)."""
    bm = geo.bm_of(ob)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True) < 0:
        for f in bm.faces:
            f.normal_flip()
    geo.bm_to(ob, bm)
    return ob


def loft_z(sections, zs, M, name="LoftZ", cap=True):
    """Loft horizontal sections (Section objects in (x, y)) at heights zs, M points per ring (same s on every ring)."""
    V = np.zeros((len(zs), M, 3))
    for i, (sec, z) in enumerate(zip(sections, zs)):
        r = sec.ring(M)
        V[i, :, 0], V[i, :, 1], V[i, :, 2] = r[:, 0], r[:, 1], z
    return outward(grid_mesh(V, name, closed_v=True, cap=cap))


def loft_x(sections, xs, M, name="LoftX", cap=True):
    """Loft sections in (y, z) placed at stations xs along X."""
    V = np.zeros((len(xs), M, 3))
    for i, (sec, x) in enumerate(zip(sections, xs)):
        r = sec.ring(M)
        V[i, :, 0], V[i, :, 1], V[i, :, 2] = x, r[:, 0], r[:, 1]
    return outward(grid_mesh(V, name, closed_v=True, cap=cap))


def slab(outline, y0, y1, step=0.0, name="Slab", holes=()):
    """Side-view outline [(x, z)] extruded between y0 and y1, the side faces triangulated by constrained
    Delaunay with interior points every `step` metres (0: none), so the faces can be dented or bent in place.
    holes: closed polygons [(x, z)] cut through."""
    from mathutils import geometry
    poly = np.asarray(outline, dtype=np.float64)
    coords = [Vector((p[0], p[1])) for p in poly]
    faces_in = [list(range(len(poly)))]
    for h in holes:
        st = len(coords)
        coords += [Vector((p[0], p[1])) for p in h]
        faces_in.append(list(range(st, st + len(h))))
    if step > 0:
        lo, hi = poly.min(0), poly.max(0)
        gx, gz = np.meshgrid(np.arange(lo[0] + step / 2, hi[0], step), np.arange(lo[1] + step / 2, hi[1], step))
        cand = np.stack([gx.ravel(), gz.ravel()], 1)
        inside = inside_poly(poly, cand) & (dist_poly(poly, cand) > step * 0.45)
        for h in holes:
            inside &= ~inside_poly(np.asarray(h), cand) & (dist_poly(np.asarray(h), cand) > step * 0.45)
        coords += [Vector((p[0], p[1])) for p in cand[inside]]
    vc, _e, tris, *_ = geometry.delaunay_2d_cdt(coords, [], faces_in, 2, 1e-8)
    bm = bmesh.new()
    a = [bm.verts.new((v.x, y1, v.y)) for v in vc]
    b = [bm.verts.new((v.x, y0, v.y)) for v in vc]
    cnt = {}
    for t in tris:
        bm.faces.new([a[i] for i in t])
        bm.faces.new([b[i] for i in reversed(t)])
        for p, q in zip(t, list(t[1:]) + [t[0]]):
            cnt[(p, q)] = cnt.get((p, q), 0) + 1
    for (p, q) in cnt:
        if (q, p) not in cnt:
            bm.faces.new([a[q], a[p], b[p], b[q]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = geo.new(name, bm, smooth=None)
    return outward(ob)


def inside_poly(poly, pts):
    """Even-odd point in polygon, vectorised: poly (n, 2), pts (k, 2) -> bool (k,)."""
    P = np.asarray(poly, dtype=np.float64)
    x, y = pts[:, 0][:, None], pts[:, 1][:, None]
    x0, y0 = P[:, 0][None], P[:, 1][None]
    x1, y1 = np.roll(P[:, 0], -1)[None], np.roll(P[:, 1], -1)[None]
    cond = (y0 > y) != (y1 > y)
    xi = x0 + (y - y0) * (x1 - x0) / np.where(np.abs(y1 - y0) < 1e-15, 1e-15, y1 - y0)
    return (cond & (x < xi)).sum(1) % 2 == 1


def dist_poly(poly, pts):
    """Distance from each point to the polygon's boundary."""
    P = np.asarray(poly, dtype=np.float64)
    a, b = P[None], np.roll(P, -1, 0)[None]
    q = pts[:, None]
    ab = b - a
    t = np.clip(((q - a) * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-18), 0, 1)
    d = np.linalg.norm(q - (a + ab * t[..., None]), axis=-1)
    return d.min(1)


def deform(ob, fn):
    """Move every vertex: co (n, 3) -> fn(co) (n, 3)."""
    co, _n = geo.arrays(ob)
    geo.set_verts(ob, fn(co.copy()))
    return ob


def subdivide(ob, cuts=1, smooth=0.0):
    bm = geo.bm_of(ob)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True, smooth=smooth)
    geo.bm_to(ob, bm)
    return ob


def dent(co, centre, axis, depth, radius, shape="round", length=None, along=None):
    """Press a soft dent (depth > 0 pushes against +axis, i.e. into a face whose outward normal is +axis) into the
    vertices co. radius: falloff radius; shape 'oval' with length along `along` (unit 3-vector) for elongated
    dimples. Returns co (modified in place)."""
    c = np.asarray(centre, dtype=np.float64)
    ax = np.asarray(axis, dtype=np.float64)
    d = co - c
    dist_n = d @ ax
    lat = d - dist_n[:, None] * ax[None]
    if length and along is not None:
        al = np.asarray(along, dtype=np.float64)
        u = lat @ al
        v = lat - u[:, None] * al[None]
        r = np.sqrt((np.maximum(np.abs(u) - (length / 2 - radius), 0) / radius) ** 2 + (np.linalg.norm(v, axis=1) / radius) ** 2)
    else:
        r = np.linalg.norm(lat, axis=1) / radius
    f = np.clip(1 - r * r, 0, 1) ** 2
    near = np.abs(dist_n) < 0.004
    co -= (depth * f * near)[:, None] * ax[None]
    return co
