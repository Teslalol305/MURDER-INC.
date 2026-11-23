"""The Goons' shared kit: gloves (the player's glove anatomy from assets/characters.py, closed at the wrist and
grown up the forearm under the cuff), socks, sneakers (sole with tread, upper with toe box, collar, tongue and heel
tab, metal eyelets, bar-and-cross laces with a bow), and the trims every outfit uses: zips with teeth and pulls,
drawstrings with aglets, the pouch pocket, the pipe sling.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import cloth, geo, scene, sdf
from assets._goons_cloth import unit, verts, set_verts

SHOE_L, SHOE_W = 0.29, 0.10          # brief


def _smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mesh_field(name, f, lo, hi, h, col, relax=3, cuts=()):
    if cuts:
        return cloth.garment_mesh(name, f, lo, hi, h, cuts=cuts, col=col, relax=relax)
    v, q = sdf.surface_nets(f, lo, hi, h)
    v, q = sdf.keep_largest(v, q)
    v = sdf.project(f, v, 3)
    if relax:
        v = sdf.relax(f, v, q, relax, 0.45)
    return sdf.to_mesh(name, v, q, col)


def decimate(ob, tris):
    n = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if n <= tris:
        return ob
    md = ob.modifiers.new("dec", "DECIMATE")
    md.decimate_type = "COLLAPSE"
    md.ratio = tris / n
    md.use_collapse_triangulate = True
    geo._apply_modifier(ob, md)
    return ob


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# ------------------------------------------------------------------------------------------------ gloves


def glove(arm, body, side, col, top=0.075, h=0.0021, budget=3600):
    """Black leather glove: the hand of assets/characters.py grown by the leather, a wrist tube up the forearm
    to `top` above the wrist joint (inside the sleeve cuff), open there."""
    from assets import characters as C
    R = C.ArmRig(arm, body, side)
    hand = C.hand_sdf(R, 0.0014)

    def f(p):
        d = hand(p)
        s, de = R.forearm_section(p, grow=-0.004)
        tube = np.maximum(de - 0.0035, -s - 0.02)
        return sdf.smin(d, tube, 0.008)
    tips = np.array([R.chain[n]["P"][3] for n in C.FINGERS])
    pts = np.vstack([tips, R.W, R.W - R.af * (top + 0.02)])
    lo, hi = pts.min(axis=0) - 0.03, pts.max(axis=0) + 0.03
    cut = (R.W - R.af * top, -R.af)
    ob = mesh_field("Glove_" + side, f, lo, hi, h, col, relax=3, cuts=[cut])
    decimate(ob, budget)
    return ob, R


# ------------------------------------------------------------------------------------------------ sneakers


class Foot:
    """Sneaker frame on the mannequin's foot: x toward the toe from the back of the heel, y outward (away from the
    body), z up from the ground."""

    def __init__(self, B, side):
        a, b = B.J["foot_" + side], B.J["ball_" + side]
        d = np.array([b[0] - a[0], b[1] - a[1], 0.0])
        self.fx = unit(d)
        out = np.array([1.0 if side == "l" else -1.0, 0, 0])
        fy = out - self.fx * (out @ self.fx)
        self.fy = unit(fy)
        self.fz = np.array([0, 0, 1.0])
        # the back of the heel: the mannequin's heel surface behind the ankle plus the counter
        P = B.pts("foot_" + side)
        P = P[P[:, 2] < 0.06]
        back = ((P - a) @ self.fx).min()
        self.o = np.array([a[0], a[1], 0.0]) + self.fx * (back - 0.012)
        self.side = side

    def local(self, p):
        q = p - self.o
        return q @ self.fx, q @ self.fy, p[:, 2]

    def world(self, x, y, z):
        return self.o + np.outer(x, self.fx) + np.outer(y, self.fy) + np.outer(z, np.array([0, 0, 1.0]))


def _half_width(t):
    """Outsole half width along the shoe (t 0 heel .. 1 toe)."""
    tk = [0.0, 0.04, 0.2, 0.42, 0.6, 0.72, 0.86, 0.95, 1.0]
    wk = [0.022, 0.033, 0.037, 0.038, 0.047, 0.050, 0.046, 0.034, 0.012]
    return np.interp(t, tk, wk)


def _sole_bottom(t):
    return 0.016 * _smooth(0.78, 1.02, t) ** 1.4 + 0.006 * (1 - _smooth(0.0, 0.07, t))


def _upper_top(t, yn):
    """Height of the upper's crown above the ground at t, falling off toward the sides (yn = y / half width)."""
    tk = [0.0, 0.06, 0.16, 0.3, 0.42, 0.55, 0.7, 0.82, 0.92, 1.0]
    hk = [0.085, 0.088, 0.083, 0.090, 0.093, 0.082, 0.066, 0.056, 0.047, 0.034]
    top = np.interp(t, tk, hk)
    fall = np.interp(t, [0, 0.2, 0.5, 0.8, 1.0], [0.012, 0.016, 0.03, 0.026, 0.016])
    return top - fall * np.clip(yn, 0, 1.2) ** 2


def sneaker_fields(F):
    L = SHOE_L

    def coords(p):
        x, y, z = F.local(p)
        t = x / L
        return x, y, z, t

    def sole(p):
        x, y, z, t = coords(p)
        w = _half_width(np.clip(t, 0, 1)) + 0.0015
        zb = _sole_bottom(np.clip(t, 0, 1))
        th = np.interp(t, [0, 0.3, 0.65, 1], [0.031, 0.029, 0.022, 0.020])
        # footprint: |y| - w with rounded heel and toe (x beyond 0..L)
        foot = sdf.rect2(x - L / 2, y, L / 2, 1.0, 0.0)
        side = np.abs(y) - w
        d2 = np.maximum(side, foot)
        d = sdf.smax(d2, np.maximum(zb - z, z - (zb + th)), 0.005)
        # tread: herringbone grooves 3.2 mm wide, 2.4 mm deep on the bottom; a plain heel and toe band
        ang = np.radians(32)
        u = x * np.cos(ang) + np.abs(y) * np.sin(ang)
        pitch = 0.0085
        g = np.abs(((u / pitch) % 1.0) - 0.5) * pitch - 0.0016
        g = np.maximum(g, -(np.abs(y) - (w - 0.006)))            # keep a rim
        g = np.where((t > 0.06) & (t < 0.93), g, 1.0)
        groove = np.maximum(-g, z - (zb + 0.0024))
        groove = np.where(g < 0, groove, 1.0)
        d = np.maximum(d, -groove)
        return d

    def upper(p):
        x, y, z, t = coords(p)
        tc = np.clip(t, 0, 1)
        w = _half_width(tc) - 0.002
        foot = sdf.rect2(x - L / 2, y, L / 2 - 0.004, 1.0, 0.0)
        side = sdf.smax(np.abs(y) - w, foot, 0.01)
        top = _upper_top(tc, np.abs(y) / np.maximum(w, 1e-3))
        zb = _sole_bottom(tc) + 0.012
        d = sdf.smax(side, z - top, 0.014)
        d = sdf.smax(d, zb - z, 0.004)
        # padded collar: a rolled ring round the ankle opening
        cx = 0.075
        r = np.sqrt(((x - cx) / 0.06) ** 2 + (y / 0.042) ** 2)
        ring = np.sqrt(((r - 1.0) * 0.045) ** 2 + (z - 0.086 + 0.006 * (np.abs(y) / 0.04)) ** 2) - 0.008
        d = sdf.smin(d, ring, 0.006)
        # tongue: a padded tab rising out of the throat
        tq = np.sqrt(((x - 0.125) / 0.03) ** 2 + (y / 0.024) ** 2)
        tongue = np.maximum(tq - 1.0, np.abs(z - 0.097) - 0.007) * 0.02
        d = sdf.smin(d, tongue, 0.008)
        return d
    return sole, upper


def sneaker(B, side, col, h_upper=0.0019, h_sole=0.0013):
    """(objects dict, Foot frame) of one sneaker: upper, sole, laces, eyelets, heel tab."""
    F = Foot(B, side)
    fs, fu = sneaker_fields(F)
    corners = F.world(np.array([-0.02, -0.02, SHOE_L + 0.02, SHOE_L + 0.02]), np.array([-0.07, 0.07, -0.07, 0.07]),
                      np.zeros(4))
    lo = np.minimum(corners.min(axis=0), 1e9) - np.array([0.01, 0.01, 0.003])
    hi = corners.max(axis=0) + np.array([0.01, 0.01, 0.0])
    up = mesh_field("Upper_" + side, fu, np.array([lo[0], lo[1], 0.005]), np.array([hi[0], hi[1], 0.12]), h_upper, col)
    so = mesh_field("Sole_" + side, fs, np.array([lo[0], lo[1], -0.003]), np.array([hi[0], hi[1], 0.05]), h_sole, col,
                    relax=1)
    decimate(up, 2300)
    decimate(so, 2000)
    out = {"upper": up, "sole": so}
    out.update(laces(F, fu, col))
    out["tab"] = heel_tab(F, fu, col)
    return out, F


def _on_surface(f, P, lift):
    """Points projected onto f = 0 then lifted `lift` along the gradient."""
    P = sdf.project(f, np.asarray(P, dtype=np.float64), 6, e=5e-4)
    g = sdf.gradient(f, P, 5e-4)
    g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
    return P + g * lift, g


def laces(F, fu, col, pairs=6):
    """Metal eyelets either side of the throat and a lace: straight bars across with the diagonal runs hidden under
    the facing (the classic bar lacing seen from above), a bow at the top with two loops and two ends."""
    L = SHOE_L
    ts = np.linspace(0.43, 0.70, pairs)[::-1]                     # top of the throat first
    eyes = []
    for t in ts:
        half = 0.019 + 0.006 * (t - 0.43) / 0.27
        for s in (-1, 1):
            p = F.world(np.array([t * L]), np.array([s * half]), np.array([0.12]))[0]
            eyes.append(p)
    eyes = np.array(eyes)
    P, N = _on_surface(fu, eyes, 0.0006)
    rings = []
    for p, n in zip(P, N):
        r = geo.torus(0.0032, 0.0009, 10, 4, name="Eyelet")
        M = Matrix.Translation(Vector(p)) @ Vector((0, 0, 1)).rotation_difference(Vector(n)).to_matrix().to_4x4()
        r.data.transform(M)
        rings.append(r)
    ey = geo.join(rings, "Eyelets_" + F.side, col)
    # lace bars: from eyelet to eyelet across the tongue, arched 3 mm over the surface
    paths = []
    for k in range(pairs):
        a, b = P[2 * k], P[2 * k + 1]
        pts = []
        for u in np.linspace(0, 1, 9):
            q = a + (b - a) * u
            pts.append(q)
        q, n = _on_surface(fu, np.array(pts), 0.0)
        lift = 0.0028 + 0.0016 * np.sin(np.linspace(0, np.pi, 9))
        paths.append(q + n * lift[:, None])
    # the bow on the top bar: two loops and two hanging ends
    a, b = P[0], P[1]
    c = (a + b) / 2
    cq, cn = _on_surface(fu, c[None], 0.004)
    c, n = cq[0], cn[0]
    fx = F.fx
    for s in (-1, 1):
        lp = []
        for ang in np.linspace(0, 2 * np.pi, 14):
            lp.append(c + F.fy * s * (0.012 * (1 - np.cos(ang)) * 0.5 + 0.002) + fx * 0.006 * np.sin(ang) + n * 0.003 * np.sin(ang / 2))
        paths.append(np.array(lp))
        end = [c, c + F.fy * s * 0.008 + fx * 0.012 + n * 0.001, c + F.fy * s * 0.014 + fx * 0.026 - np.array([0, 0, 0.004]),
               c + F.fy * s * 0.017 + fx * 0.040 - np.array([0, 0, 0.012])]
        paths.append(np.array(end))
    objs = []
    for pth in paths:
        objs.append(geo.pipe([tuple(v) for v in pth], radius=0.0021, segments=6, cap=True, name="Lace"))
    la = geo.join(objs, "Laces_" + F.side, col)
    scene.move_to(ey, col)
    return {"eyelets": ey, "laces": la}


def heel_tab(F, fu, col):
    """Oxblood pull tab sewn to the back of the collar: a flat strip standing 16 mm proud of the counter."""
    base = F.world(np.array([0.0]), np.array([0.0]), np.array([0.075]))[0]
    P, N = _on_surface(fu, base[None], 0.0012)
    p0 = P[0]
    path = [p0 - np.array([0, 0, 0.022]), p0, p0 + np.array([0, 0, 0.014]) - F.fx * 0.004,
            p0 + np.array([0, 0, 0.020]) - F.fx * 0.001]
    ob = geo.sweep(geo.rect_profile(0.020, 0.0022), [tuple(v) for v in path], name="HeelTab_" + F.side,
                   up=tuple(F.fx))
    scene.move_to(ob, col)
    return ob


# ------------------------------------------------------------------------------------------------ socks


def sock(BF, col, side_x, top=0.26):
    """A black sock up the shin (only ever seen between the trouser hem and the sneaker in motion)."""
    f = lambda p: BF(p) - 0.0035
    lo = np.array([min(side_x * 0.02, side_x * 0.30), -0.16, 0.04])
    hi = np.array([max(side_x * 0.02, side_x * 0.30), 0.14, top + 0.02])
    cuts = [((0, 0, top), (0, 0, 1)), ((0, 0, 0.05), (0, 0, -1))]
    ob = cloth.garment_mesh("Sock", f, lo, hi, 0.009, cuts=cuts, col=col, relax=2)
    return ob


# ------------------------------------------------------------------------------------------------ trims


class Surface:
    """Closest-point and ray queries on a garment (world space, rest pose)."""

    def __init__(self, *obs):
        from mathutils.bvhtree import BVHTree
        V, F, off = [], [], 0
        for ob in obs:
            co = verts(ob)
            V.append(co)
            for p in ob.data.polygons:
                F.append([i + off for i in p.vertices])
            off += len(co)
        self.V = np.concatenate(V)
        self.bvh = BVHTree.FromPolygons([tuple(v) for v in self.V], F)

    def nearest(self, P):
        out, nrm = [], []
        for p in np.asarray(P):
            loc, n, i, d = self.bvh.find_nearest(Vector(p))
            out.append(loc)
            nrm.append(n)
        return np.array(out), np.array(nrm)

    def ray(self, origin, direction, far=1.0):
        loc, n, i, d = self.bvh.ray_cast(Vector(origin), Vector(direction), far)
        return (None, None) if loc is None else (np.array(loc), np.array(n))


def _inside(poly, x, z):
    """Even-odd point in polygon test for arrays x, z."""
    poly = np.asarray(poly)
    inside = np.zeros(len(x), dtype=bool)
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        c = ((z1 > z) != (z2 > z)) & (x < (x2 - x1) * (z - z1) / np.where(z2 - z1 == 0, 1e-12, z2 - z1) + x1)
        inside ^= c
    return inside


def panel(name, S, outline, col, lift=0.0035, step=0.0075, y0=-0.6, direction=(0, 1.0, 0)):
    """A panel sewn onto the front (or back, direction (0, -1, 0), y0 > 0) of a garment: the 2D polygon `outline`
    in (x, z) is filled with a grid (its edge snapped to the outline), each point shot along `direction` onto the
    surface S and lifted `lift` along the surface normal."""
    poly = np.asarray(outline, dtype=np.float64)
    x0, z0 = poly.min(axis=0) - step
    x1, z1 = poly.max(axis=0) + step
    xs = np.arange(x0, x1 + step, step)
    zs = np.arange(z0, z1 + step, step)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    ins = _inside(poly, X.ravel(), Z.ravel()).reshape(X.shape)
    # a cell is kept when any corner is inside; outside corners are pulled onto the outline
    keep = ins[:-1, :-1] | ins[1:, :-1] | ins[1:, 1:] | ins[:-1, 1:]
    used = np.zeros(X.shape, dtype=bool)
    used[:-1, :-1] |= keep
    used[1:, :-1] |= keep
    used[1:, 1:] |= keep
    used[:-1, 1:] |= keep
    P2 = np.stack([X, Z], axis=-1)
    seg_a, seg_b = poly, np.roll(poly, -1, axis=0)
    out_pts = np.argwhere(used & ~ins)
    for i, j in out_pts:
        p = P2[i, j]
        ab = seg_b - seg_a
        t = np.clip(((p - seg_a) * ab).sum(axis=1) / np.maximum((ab * ab).sum(axis=1), 1e-12), 0, 1)
        q = seg_a + ab * t[:, None]
        P2[i, j] = q[np.argmin(np.linalg.norm(q - p, axis=1))]
    idx = -np.ones(X.shape, dtype=np.int64)
    pts = np.argwhere(used)
    idx[used] = np.arange(len(pts))
    V = []
    d = np.asarray(direction, dtype=np.float64)
    for i, j in pts:
        x, z = P2[i, j]
        loc, n = S.ray((x, y0, z), d, 2.0)
        if loc is None:
            loc, n = S.nearest([(x, 0.0, z)])
            loc, n = loc[0], n[0]
        if n @ d > 0:
            n = -n
        V.append(loc + n * lift)
    F = []
    for i, j in np.argwhere(keep):
        q = [idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]]
        F.append(q if d[1] > 0 else q[::-1])
    ob = geo.from_arrays(name, np.array(V), F, col, smooth=None)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def drawstring(name, S, start, length, col, radius=0.0032, lift=0.004, aglet=0.02):
    """A cord hanging from `start` down the surface S for `length`, ending in an aglet (returned separately)."""
    pts = [np.asarray(start, dtype=np.float64)]
    step = 0.012
    p = pts[0].copy()
    for k in range(int(length / step)):
        p = p + np.array([0, -0.002, -step])
        q, n = S.nearest([p])
        p = q[0] + n[0] * lift
        pts.append(p)
    P = np.array(pts)
    cord = geo.pipe([tuple(v) for v in P], radius=radius, segments=8, cap=True, name=name)
    scene.move_to(cord, col)
    d = unit(P[-1] - P[-2])
    tip = [P[-1] - d * 0.003, P[-1] + d * aglet]
    ag = geo.pipe([tuple(v) for v in tip], radius=radius * 1.05, segments=10, cap=True, name=name + "_Aglet")
    scene.move_to(ag, col)
    return cord, ag


def strap_loop(S, a, b, col, name="Sling", width=0.038, thick=0.0026, lift=0.006, n=160):
    """Webbing worn bandolier-style: the loop where the plane through a (over the right shoulder) and b (at the
    left hip) and the body's front-back axis meets the garment surface S, lifted `lift` off it."""
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    c = (a + b) / 2
    u = unit(a - b)
    v = np.array([0, 1.0, 0])
    v = unit(v - u * (u @ v))
    P, N = [], []
    for t in np.linspace(0, 2 * np.pi, n, endpoint=False):
        d = np.cos(t) * u + np.sin(t) * v
        # cast from outside toward the centre: the outermost layer is hit first
        loc, nn = S.ray(c + d * 0.9, -d, 0.9)
        if loc is None:
            continue
        if nn @ d < 0:
            nn = -nn
        P.append(loc + nn * lift)
        N.append(nn)
    P, N = np.array(P), np.array(N)
    # smooth the path (it bridges folds the way a taut strap does)
    for _ in range(6):
        P = 0.5 * P + 0.25 * (np.roll(P, 1, axis=0) + np.roll(P, -1, axis=0))
    from mi import cloth as _cloth
    return _cloth.ribbon(name, P, N, width, thick, col, closed=True), P, N


def zip_teeth(name, path, normals, col, pitch=0.0048, tape=0.026, tooth=(0.0058, 0.0026, 0.0022)):
    """Zip along `path` (bottom to top) on a surface with `normals`: two tapes and interlocking teeth, closed."""
    from mi import cloth as _cloth
    P = np.asarray(path, dtype=np.float64)
    N = np.asarray(normals, dtype=np.float64)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    tapes = _cloth.ribbon(name + "_Tape", P, N, tape, 0.0012, col)
    boxes = []
    for k, s in enumerate(np.arange(0.004, L[-1] - 0.004, pitch / 2)):
        p = np.array([np.interp(s, L, P[:, i]) for i in range(3)])
        n = unit(np.array([np.interp(s, L, N[:, i]) for i in range(3)]))
        t = unit(np.array([np.interp(s + 0.001, L, P[:, i]) for i in range(3)]) - p)
        side = unit(np.cross(t, n))
        off = side * (0.0012 if k % 2 else -0.0012)
        bx = geo.box(size=(tooth[0], tooth[1], tooth[2]), bevel=0.0, segments=1, name="Tooth", base=False)
        Mx = np.eye(4)
        Mx[:3, 0], Mx[:3, 1], Mx[:3, 2], Mx[:3, 3] = side, t, n, p + off + n * 0.0016
        bx.data.transform(Matrix(Mx.tolist()))
        boxes.append(bx)
    teeth = geo.join(boxes, name + "_Teeth", col)
    return tapes, teeth


def zip_pull(name, top, normal, up, col):
    """Slider and a flat pull tab hanging from it, at the top of a zip."""
    n, u = unit(normal), unit(up)
    s = unit(np.cross(u, n))
    body = geo.box(size=(0.011, 0.016, 0.006), bevel=0.0012, segments=2, name=name + "_Slider", base=False)
    M1 = np.eye(4)
    M1[:3, 0], M1[:3, 1], M1[:3, 2], M1[:3, 3] = s, u, n, np.asarray(top) + n * 0.004 - u * 0.008
    body.data.transform(Matrix(M1.tolist()))
    tab = geo.box(size=(0.008, 0.026, 0.0016), bevel=0.0006, segments=1, name=name + "_Tab", base=False)
    M2 = np.eye(4)
    M2[:3, 0], M2[:3, 1], M2[:3, 2], M2[:3, 3] = s, u, n, np.asarray(top) + n * 0.0075 - u * 0.026
    tab.data.transform(Matrix(M2.tolist()))
    ob = geo.join([body, tab], name, col)
    return ob
