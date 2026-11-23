"""CHOPPER, rebuild round 1: stamped sheet, forgings and laminated wood built as sections instead of prisms.

    receiver    side outline triangulated with dense points where the sheet is pressed, then dented: magazine-well
                dimples 38 x 9 x 0.8 mm, the recess under the stock hinge; lower edge turned in; 1.2 mm bends;
                front trunnion rivets 3 + 1 (4.5 mm, mushroomed domes), rear trunnion rivets and the grip tang.
    handguards  lower: U-channel lofted along X (46 mm at the receiver with the finger-swell flare, 42 mm at the
                band, 13 mm bottom radius, 6 mm walls), front end in a stamped ferrule with a 1 mm lip, steel liner;
                upper: D section (17 mm top radius) over a steel heat-shield liner; vents with 0.9 mm rounded lips.
    grip        horizontal sections lofted down the rake: oval 30 x 42 mm, front swell at 55 %, palm hump widening
                toward the base, flat base with a steel cap and screw.
    sight block sloping 30 deg front, sides flowing into the trunnion with 3.5 mm fillets, leaf-spring housing,
                handguard retainer lever with a round thumb pad.
    gas block   one forging: barrel collar and gas cylinder joined by a rounded saddle (soft union of the two
                circles, lofted along X with rounded ends), tower tapering 21 -> 14 mm, 2 mm ears with 1 mm tops and
                a lightening hole, sling loop.
    stock       arms pressed as 8 x 4 mm U-channel with a joggle at the hinge, forged hinge block with a large
                axle pin and latch button, curved shoulder piece (R 120 mm) with turned edges, lightening holes and
                a rubber pad.
    guard       11 x 1.5 mm stamped strip with rolled edges and a pressed 4 mm centre rib, flat front tab riveted
                to the floor, rear end in a catch housing; 22 mm catch paddle with a dished thumb pad.
    bolt        rounded carrier top, milled step, bolt head with the extractor claw in the port.
Every part carries a texture-set tag (face attribute 'tset': 0 receiver and rear, 1 furniture, 2 front end).
"""
import math

import numpy as np
from mathutils import Matrix, Vector

from mi import geo, rig, scene
from assets import weapons as W
from assets import _weapons_kit as K

CH = W.CH
P0, prism, lathe, box, cut, union, round_edges, pin_head, loft, fix_normals = (
    W.P, W.prism, W.lathe, W.box, W.cut, W.union, W.round_edges, W.pin_head, W.loft, W.fix_normals)
BLUED, DARK, BRIGHT, WOOD, COVER, BORE, BRASS, POLYMER = (W.BLUED, W.DARK, W.BRIGHT, W.WOOD, W.COVER, W.BORE,
                                                           W.BRASS, W.POLYMER)
REAR, FURN, FRONT = 0, 1, 2
SET_NAMES = ("Chopper", "Chopper_Furniture", "Chopper_Front")


def P(ob, mid, bone, tset, smooth=50.0):
    P0(ob, mid, bone, smooth)
    me = ob.data
    a = me.attributes.get("tset") or me.attributes.new("tset", "FLOAT", "FACE")
    a.data.foreach_set("value", np.full(len(me.polygons), float(tset), np.float32))
    return ob


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------------------------- 2D helpers

def rpoly(corners, radii, nseg, nedge):
    """Closed polygon through `corners` [(u, v)] with every corner rounded by radii[i] using exactly nseg[i] + 1
    points, and the straight run after corner i split into nedge[i] segments. Same counts in, same point count out:
    polygons built with the same lists can be lofted into each other."""
    C = np.asarray(corners, dtype=np.float64)
    n = len(C)
    arcs = []
    for i in range(n):
        p0, p1, p2 = C[i - 1], C[i], C[(i + 1) % n]
        a, b = p0 - p1, p2 - p1
        la, lb = np.linalg.norm(a), np.linalg.norm(b)
        a, b = a / la, b / lb
        ang = math.acos(float(np.clip(np.dot(a, b), -1, 1)))
        k = nseg[i] + 1
        r = radii[i]
        if r <= 0 or ang > math.pi - 1e-4:
            arcs.append(np.repeat(p1[None], k, 0))
            continue
        t = min(r / math.tan(ang / 2), 0.49 * la, 0.49 * lb)
        r = t * math.tan(ang / 2)
        bis = (a + b) / np.linalg.norm(a + b)
        c = p1 + bis * (r / math.sin(ang / 2))
        v0, v1 = p1 + a * t - c, p1 + b * t - c
        sw = math.pi - ang
        f = np.linspace(0, 1, k)
        w0 = np.sin((1 - f) * sw) / math.sin(sw)
        w1 = np.sin(f * sw) / math.sin(sw)
        arcs.append(c[None] + v0[None] * w0[:, None] + v1[None] * w1[:, None])
    out = []
    for i in range(n):
        out.append(arcs[i])
        e0, e1 = arcs[i][-1], arcs[(i + 1) % n][0]
        m = nedge[i]
        if m > 1:
            f = np.linspace(0, 1, m + 1)[1:-1]
            out.append(e0[None] + (e1 - e0)[None] * f[:, None])
    return np.vstack(out)


def ccw(Pp):
    Pp = np.asarray(Pp)
    x, y = Pp[:, 0], Pp[:, 1]
    area = 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
    return Pp if area > 0 else Pp[::-1]


def offset(Pp, d):
    """Move every point of a closed counter-clockwise polygon outward by d (inward for d < 0)."""
    T = np.roll(Pp, -1, 0) - np.roll(Pp, 1, 0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    N = np.stack([T[:, 1], -T[:, 0]], 1)
    return Pp + N * d


def end_inset(x, x0, x1, r):
    """Inset (m) that rounds the two ends of a loft between x0 and x1 with radius r."""
    d = min(x - x0, x1 - x)
    if d >= r:
        return 0.0
    return r - math.sqrt(max(0.0, r * r - (r - d) ** 2))


def loft_polys(polys, xs, name, axis="X", cap=True):
    """Loft closed polygons (same point count) placed at stations xs. axis 'X': polygons in (y, z); 'Z': in (x, y)."""
    m = len(polys[0])
    V = np.zeros((len(xs), m, 3))
    for i, (Pp, s) in enumerate(zip(polys, xs)):
        if axis == "X":
            V[i, :, 0], V[i, :, 1], V[i, :, 2] = s, Pp[:, 0], Pp[:, 1]
        else:
            V[i, :, 0], V[i, :, 1], V[i, :, 2] = Pp[:, 0], Pp[:, 1], s
    return K.outward(K.grid_mesh(V, name, closed_v=True, cap=cap))


def stations(x0, x1, step, r_end, n_end=4, extra=()):
    s = list(np.arange(x0, x1, step)) + [x1]
    for k in range(1, n_end + 1):
        f = 1 - math.cos(k / n_end * math.pi / 2)
        s += [x0 + r_end * f, x1 - r_end * f]
    s += list(extra)
    return np.array(sorted(set(np.round([v for v in s if x0 <= v <= x1], 6))))


def slab_pts(outline, y0, y1, pts, name="Slab", holes=()):
    """kit.slab with explicit interior points (dense where the sheet is pressed)."""
    from mathutils import geometry
    import bmesh
    poly = np.asarray(outline, dtype=np.float64)
    coords = [Vector((p[0], p[1])) for p in poly]
    faces_in = [list(range(len(poly)))]
    pts = np.asarray(pts, dtype=np.float64)
    keep = K.inside_poly(poly, pts) & (K.dist_poly(poly, pts) > 0.0007)
    coords += [Vector((p[0], p[1])) for p in pts[keep]]
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
    return K.outward(geo.new(name, bm, smooth=None))


def grid_pts(x0, x1, z0, z1, step):
    gx, gz = np.meshgrid(np.arange(x0, x1 + 1e-9, step), np.arange(z0, z1 + 1e-9, step))
    return np.stack([gx.ravel(), gz.ravel()], 1)


def dome_rivet(at, axis="Y", d=0.0045, h=0.0008, sign=1, seg=20):
    """Domed rivet head, slightly mushroomed where it was set (the rim flares past the shank)."""
    r = d / 2
    prof = [(-0.0006, 0.0), (-0.0006, r * 0.96), (0.0, r * 1.02), (h * 0.18, r * 1.0), (h * 0.45, r * 0.86),
            (h * 0.75, r * 0.58), (h * 0.93, r * 0.28), (h, 0.0)]
    ob = lathe(prof, seg, axis=axis, name="Rivet")
    if sign < 0:
        geo.transform(ob, scale=(1, -1, 1) if axis == "Y" else ((-1, 1, 1) if axis == "X" else (1, 1, -1)))
    geo.transform(ob, loc=at)
    return fix_normals(ob)


# ----------------------------------------------------------------------------------------------- receiver

DIMPLE = dict(x=0.1990, z=-0.0262, length=0.038, width=0.009, depth=0.0008)
HINGE = (0.022, -0.0315)               # stock hinge (round 3: in line with the arms)
RECESS = (0.022, -0.028)               # the receiver's pressed recess round the hinge boss
FRONT_RIVETS = ((0.2140, 0.0045), (0.2440, 0.0045), (0.2440, -0.0095), (0.2330, -0.0310))
REAR_RIVETS = ((0.0090, 0.0015), (0.0090, -0.0250))


def stadium_rings(xc, zc, length, width, offsets, step):
    """Points (x, z) on stadium outlines grown by each offset (dense rows along a pressed dimple's shoulder)."""
    out = []
    L2 = length / 2 - width / 2
    for o in offsets:
        r = width / 2 + o
        if r <= 0:
            continue
        per = 4 * L2 + 2 * math.pi * r
        t = np.linspace(0, per, max(8, int(per / step)), endpoint=False)
        for v in t:
            if v < 2 * L2:
                out.append((xc - L2 + v, zc + r))
            elif v < 2 * L2 + math.pi * r:
                a = (v - 2 * L2) / r
                out.append((xc + L2 + r * math.sin(a), zc + r * math.cos(a)))
            elif v < 4 * L2 + math.pi * r:
                out.append((xc + L2 - (v - 2 * L2 - math.pi * r), zc - r))
            else:
                a = (v - 4 * L2 - math.pi * r) / r
                out.append((xc - L2 - r * math.sin(a), zc - r * math.cos(a)))
    return np.array(out)


def crisp_dent(co, side, xc, zc, length, width, depth, shoulder):
    """Press a flat-bottomed stadium dimple into the side wall (outward normal side * +Y) with a crisp shoulder."""
    L2 = length / 2 - width / 2
    d = np.hypot(np.maximum(np.abs(co[:, 0] - xc) - L2, 0.0), co[:, 2] - zc) - width / 2
    f = K.smoothstep(-d, -shoulder / 2, shoulder / 2)
    near = np.abs(co[:, 1] - side * 0.016) < 0.0015
    co[:, 1] -= side * depth * f * near
    return co


def chopper_receiver(parts):
    outline = [(-0.004, -0.040), (0.256, -0.040), (0.256, 0.012), (-0.004, 0.012)]
    pts = np.vstack([grid_pts(-0.004, 0.256, -0.040, 0.012, 0.004),
                     stadium_rings(DIMPLE["x"], DIMPLE["z"], DIMPLE["length"], DIMPLE["width"],
                                   (-0.0030, -0.0015, -0.0008, -0.0004, 0.0, 0.0004, 0.0008, 0.0015, 0.0030), 0.0008),
                     grid_pts(RECESS[0] - 0.012, RECESS[0] + 0.012, RECESS[1] - 0.012, RECESS[1] + 0.012, 0.0012),
                     grid_pts(-0.004, 0.256, -0.040, -0.033, 0.002)])
    rec = slab_pts(outline, -0.016, 0.016, pts, name="Receiver")

    def press(co):
        for s in (1, -1):
            co = crisp_dent(co, s, DIMPLE["x"], DIMPLE["z"], DIMPLE["length"], DIMPLE["width"], DIMPLE["depth"], 0.0010)
            co = K.dent(co, (RECESS[0], s * 0.016, RECESS[1]), (0, s, 0), 0.0007, 0.0105)
        # the lower edge turned in toward the floor
        t = smoothstep((-0.0335 - co[:, 2]) / 0.0065)
        co[:, 1] *= 1.0 - 0.032 * t
        return co
    K.deform(rec, press)
    round_edges(rec, 0.0015, 3, 50)
    cav = box(0.004, 0.190, -0.015, 0.015, -0.039, 0.030)
    well = box(0.1595, 0.2245, -0.0136, 0.0136, -0.050, -0.019, bevel=0.0015)
    port = prism([(0.108, 0.0005), (0.172, 0.0005), (0.172, 0.030), (0.108, 0.030)], -0.030, -0.009, fillet=0.003,
                 bevel=0.0)
    slot = box(0.0790, 0.1930, 0.009, 0.030, 0.0092, 0.030)
    trig = box(0.098, 0.121, -0.0038, 0.0038, -0.050, -0.030, bevel=0.001)
    bore = lathe([(0.15, 0.0), (0.15, 0.0091), (0.30, 0.0091), (0.30, 0.0)], 32)
    rear = box(-0.010, 0.0035, -0.05, 0.05, -0.05, 0.05)                 # the sheet ends: the trunnion shows behind
    cut(rec, cav, well, port, slot, trig, bore, rear)
    round_edges(rec, 0.0005, 2, 50)
    parts.append(P(rec, BLUED, "body", REAR))
    for s in (1, -1):
        y = s * 0.016
        for x, z in FRONT_RIVETS + REAR_RIVETS:
            parts.append(P(swaged_rivet((x, y - s * 0.0001, z), "Y", d=0.0045 if x > 0.1 else 0.0040, sign=s), BLUED,
                           "body", REAR))
        parts.append(P(dome_rivet((0.140, y - s * 0.0001, -0.034), "Y", d=0.0040, h=0.0007, sign=s), BLUED, "body", REAR))
    # trigger pin, hammer pin (heads both sides), the bent-wire retainer on the left
    for s in (1, -1):
        parts.append(P(pin_head((0.108, s * 0.016, -0.0375), "Y", r=0.0019, sign=s), DARK, "body", REAR))
        parts.append(P(pin_head((0.080, s * 0.016, -0.029), "Y", r=0.0021, sign=s), DARK, "body", REAR))
    # grip tang of the rear trunnion under the floor, two rivets
    tang = prism([(-0.002, -0.0405), (0.030, -0.0405), (0.033, -0.0410), (0.033, -0.0418), (-0.002, -0.0418)],
                  -0.0085, 0.0085, bevel=0.0004, seg=2, fillet=0.0015, name="Tang")
    parts.append(P(tang, BLUED, "body", FRONT))
    for x in (0.006, 0.026):
        parts.append(P(swaged_rivet((x, 0.0, -0.0417), "Z", d=0.0038, h=0.0006, sign=-1, ring=0.0002), BLUED, "body", FRONT))
    for x in (0.150, 0.158):
        parts.append(P(dome_rivet((x, 0.0, -0.0414), "Z", d=0.0036, h=0.0006, sign=-1), BLUED, "body", REAR))


# ----------------------------------------------------------------------------------------------- handguards

LHG = (0.250, 0.3815)


def lhg_poly(x, inset=0.0):
    """Lower handguard section (round 3): 40 mm body with sides bowed 1.5 mm, the bottom rolled at R 8, a finger
    flange flaring 3 mm out along each top edge (the classic swell), the front 15 mm tapering 10 deg into the band."""
    t = float(np.clip((x - LHG[0]) / (LHG[1] - LHG[0]), 0, 1))
    taper = max(0.0, x - 0.3665) * math.tan(math.radians(10.0))
    w = 0.0200 - 0.0008 * t - taper
    wi = w - 0.0058
    zt, z0, zi0 = -0.0040, -0.0420 + taper * 0.5, -0.0310
    corners = [(-w, zt), (-w, z0), (w, z0), (w, zt), (wi, zt), (wi, zi0), (-wi, zi0), (-wi, zt)]
    radii = [0.0016, 0.0080, 0.0080, 0.0016, 0.0010, 0.0060, 0.0060, 0.0010]
    nseg = [4, 12, 12, 4, 3, 8, 8, 3]
    nedge = [9, 6, 9, 2, 6, 4, 6, 2]
    Pp = ccw(rpoly(corners, radii, nseg, nedge))
    outer = np.abs(Pp[:, 0]) > wi + 0.001
    zz = Pp[:, 1]
    bow = 0.0015 * np.clip(1 - ((zz + 0.0250) / 0.0160) ** 2, 0, 1)
    flange = 0.0030 * K.smoothstep(zz, -0.0135, -0.0068) * hg_ends(x)
    Pp[:, 0] += np.sign(Pp[:, 0]) * (bow + flange) * outer
    return offset(Pp, -inset) if inset else Pp


def lower_handguard(parts):
    xs = stations(LHG[0], LHG[1], 0.0050, 0.0015, 4, extra=np.r_[np.linspace(0.252, 0.268, 5), np.linspace(0.364, 0.381, 6)])
    polys = [lhg_poly(x, end_inset(x, LHG[0], LHG[1], 0.0015)) for x in xs]
    lo = loft_polys(polys, xs, "LowerHG")
    slots = []
    for s in (1, -1):
        for x in (0.296, 0.318, 0.340):
            c = prism([(x - 0.0055, -0.0250), (x + 0.0055, -0.0250), (x + 0.0055, -0.0090), (x - 0.0055, -0.0090)],
                      s * 0.0080, s * 0.030, bevel=0, fillet=0.0054, fseg=8)
            slots.append(c)
    cut(lo, *slots)
    K.bevel_where(lo, 0.0013, 3, 30.0, where=lambda c: (np.abs(c[:, 1]) > 0.0150) & (c[:, 2] > -0.0265)
                  & (c[:, 2] < -0.0075) & (c[:, 0] > 0.288) & (c[:, 0] < 0.348))           # 1.3 mm round-over
    round_edges(lo, 0.0008, 2, 45)
    parts.append(P(lo, WOOD, "body", FURN))
    # pressed-steel heat-shield liner inside the channel (seen through the slots and between the handguards),
    # with pressed stiffening swages
    def side_normals(Q):
        T = np.gradient(Q, axis=0)
        T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
        return np.stack([T[:, 1], -T[:, 0]], 1)
    xs2 = stations(0.2525, 0.3790, 0.0080, 0.0005, 2)
    lp = []
    i0, i1 = 60, 96
    for x in xs2:
        ch = lhg_poly(x)[i0:i1]
        n = side_normals(ch)
        sw = 0.0
        lp.append(np.vstack([ch + n * (0.0003 + sw), (ch + n * (0.0011 + sw))[::-1]]))
    liner = loft_polys([ccw(q) for q in lp], xs2, "LowerLiner")
    parts.append(P(liner, DARK, "body", FRONT))
    retaining_band(parts)


UHG = (0.262, 0.372)


def uhg_poly(x, inset=0.0):
    """Upper handguard (round 3): a half-round cap 34 mm wide tapering 1.5 mm toward the front, its top dropping
    3 mm over the last 8 mm into a shaped nose; the channel over the gas tube inside."""
    t = float(np.clip((x - UHG[0]) / (UHG[1] - UHG[0]), 0, 1))
    R = 0.0170 - 0.00075 * t
    zb = 0.0062
    drop = 0.0020 * float(K.smoothstep(x, UHG[1] - 0.009, UHG[1]))
    ztop = 0.0330 - 0.0006 * t - drop
    zc = ztop - R
    Ri, zci = 0.0113 - 0.0012 * float(K.smoothstep(x, UHG[1] - 0.012, UHG[1] - 0.002)), 0.0178
    side = [(-R, zb + (zc - zb) * f) for f in (0.33, 0.66)]
    arc = [(-R * math.cos(a), zc + R * math.sin(a)) for a in np.linspace(0, math.pi, 49)]
    side2 = [(y_ * -1, z_) for y_, z_ in side[::-1]]
    inner = [(Ri * math.cos(a), zci + Ri * math.sin(a)) for a in np.linspace(0, math.pi, 25)]
    Pp = np.array([(-0.0113, zb), (-R, zb)] + side + arc + side2 + [(R, zb), (0.0113, zb)] + [(Ri, zb + 0.004)] + inner
                  + [(-Ri, zb + 0.004)])
    Pp = ccw(Pp)
    return offset(Pp, -inset) if inset else Pp


def upper_handguard(parts):
    xs = stations(UHG[0], UHG[1], 0.0045, 0.0016, 4, extra=np.linspace(UHG[1] - 0.010, UHG[1], 6))
    polys = [uhg_poly(x, end_inset(x, UHG[0], UHG[1], 0.0016)) for x in xs]
    up = loft_polys(polys, xs, "UpperHG")
    vents = [prism([(x0, 0.0175), (x0 + 0.020, 0.0175), (x0 + 0.020, 0.0265), (x0, 0.0265)], -0.03, 0.03, bevel=0,
                   fillet=0.0044, fseg=8) for x0 in (0.287, 0.322)]
    cut(up, *vents)
    K.bevel_where(up, 0.0013, 3, 30.0, where=lambda c: (np.abs(c[:, 1]) > 0.0110) & (c[:, 2] > 0.0160)
                  & (c[:, 2] < 0.0280) & (c[:, 0] > 0.284) & (c[:, 0] < 0.345))
    round_edges(up, 0.0008, 2, 45)
    parts.append(P(up, WOOD, "body", FURN))
    # pressed-steel heat-shield liner under the wood, its rear end a stepped lip dropping into the trunnion cut-out
    xs2 = stations(0.2565, 0.3735, 0.011, 0.0004, 2, extra=np.linspace(0.2565, 0.2640, 6))
    lp = []
    for x in xs2:
        step = float(K.smoothstep(0.2610 - x, 0.0, 0.0008))      # the lip: 1.5 mm lower behind the wood
        ro = 0.0109 + 0.0012 * float(K.smoothstep(0.2630 - x, 0.0, 0.0008)) - 0.0015 * step
        ri = ro - 0.0009
        a = [(ro * math.cos(t_), 0.0178 + ro * math.sin(t_)) for t_ in np.linspace(0, math.pi, 33)]
        b = [(ri * math.cos(t_), 0.0178 + ri * math.sin(t_)) for t_ in np.linspace(math.pi, 0, 33)]
        lp.append(ccw(np.array(a + [(-ro, 0.0070), (-ri, 0.0070)] + b + [(ri, 0.0070), (ro, 0.0070)])))
    liner = loft_polys(lp, xs2, "UpperLiner")
    parts.append(P(liner, DARK, "body", FRONT))


# ----------------------------------------------------------------------------------------------- sight block

SB = (0.186, 0.256)


def sb_top(x):
    z = 0.032
    if x < 0.192:
        d = 0.192 - x
        z = 0.032 - (0.006 - math.sqrt(max(0.0, 0.006 ** 2 - d * d)))
    k = math.tan(math.radians(30.0))
    if x > 0.236:
        z = 0.032 - (x - 0.236) * k
    if 0.230 < x < 0.242:                                # soften the break into the slope
        t = (x - 0.230) / 0.012
        z = min(z, 0.032 - k * 0.006 * t * t)
    return z


def sb_poly(x, inset=0.0):
    zb = 0.0110
    zt = sb_top(x) - inset
    w = 0.0125 - inset
    r = 0.0035
    fil = [(-(0.0125 + r) + r * math.cos(a), zb + r + r * math.sin(a)) for a in np.linspace(-math.pi / 2, 0, 7)]
    fil[-1] = (-w, zb + r)
    corners_r = rpoly([(-w, zb + r), (-w, zt), (w, zt), (w, zb + r)], [0, 0.0045, 0.0045, 0], [0, 8, 8, 0], [5, 6, 5, 1])
    right = np.array(fil[:-1])
    left = right[::-1] * np.array([-1, 1])
    body = corners_r                      # from (-w, zb+r) up, across, down to (w, zb+r)
    Pp = np.vstack([right, body, left, [(0.0162, zb - 0.0005), (-0.0162, zb - 0.0005)]])
    return ccw(Pp)


def sight_block(parts):
    xs = stations(SB[0], SB[1], 0.002, 0.0012, extra=np.linspace(0.186, 0.193, 8))
    polys = [sb_poly(x, end_inset(x, SB[0], SB[1], 0.0012)) for x in xs]
    sb = loft_polys(polys, xs, "SightBlock")
    parts.append(P(sb, BLUED, "body", FRONT))
    # leaf-spring housing on top, at the rear
    hs = prism([(0.1915, 0.0300), (0.2120, 0.0300), (0.2120, 0.0330), (0.2095, 0.0346), (0.1945, 0.0346), (0.1915, 0.0330)],
               -0.0060, 0.0060, bevel=0.0008, seg=3, fillet=0.0015, name="SpringHousing")
    parts.append(P(hs, BLUED, "body", FRONT))
    parts.append(P(pin_head((0.2020, 0.0, 0.0346), "Z", r=0.0016, h=0.0003, seg=16), DARK, "body", FRONT))
    # handguard retainer lever, right side: plate from its pivot forward, round domed thumb pad
    lev = prism([(0.2440, 0.0150), (0.2560, 0.0160), (0.2600, 0.0175), (0.2600, 0.0215), (0.2560, 0.0222), (0.2440, 0.0205)],
                -0.0137, -0.0126, bevel=0.0003, seg=2, fillet=0.0018, name="Lever")
    pad = lathe([(0.0, 0.0), (0.0, 0.0038), (0.0008, 0.0038), (0.0016, 0.0032), (0.0020, 0.0018), (0.0021, 0.0)], 32,
                axis="Y", fillet=0.0002)
    geo.transform(pad, scale=(1, -1, 1))
    geo.transform(pad, loc=(0.2590, -0.0132, 0.0193))
    parts.append(P(fix_normals(pad), DARK, "body", FRONT))
    parts.append(P(lev, DARK, "body", FRONT))
    parts.append(P(pin_head((0.2455, -0.0137, 0.0178), "Y", r=0.0018, h=0.0004, sign=-1, seg=16), DARK, "body", FRONT))


# ----------------------------------------------------------------------------------------------- front end

def soft_union_ring(circles, k, centre, M):
    """Closed contour of a smooth union of circles [(cy, cz, r)] (smin with blend k), M points by angle around
    `centre` (the shape must be star-shaped about it)."""
    th = np.linspace(0, 2 * math.pi, M, endpoint=False)
    dirs = np.stack([np.cos(th), np.sin(th)], 1)

    def f(p):
        ds = [np.linalg.norm(p - np.array([c[0], c[1]]), axis=-1) - c[2] for c in circles if c[2] > 1e-5]
        a = ds[0]
        for b in ds[1:]:
            h = np.maximum(k - np.abs(a - b), 0) / k
            a = np.minimum(a, b) - h * h * k / 4
        return a
    lo = np.zeros(M)
    hi = np.full(M, 0.05)
    c = np.asarray(centre)
    for _ in range(40):
        mid = (lo + hi) / 2
        inside = f(c[None] + dirs * mid[:, None]) < 0
        lo = np.where(inside, mid, lo)
        hi = np.where(inside, hi, mid)
    return ccw(c[None] + dirs * lo[:, None])


GB = (0.3925, 0.4260)


def gas_block(parts):
    """Gas block forging (round 3): a barrel collar (R 13, its underside eased to R 10) blending into the gas-port
    housing through an R 4 fillet, a 45 deg chamfered front face; the front-sight base rising from it as a tapered
    trapezoid with R 2 edges and an R 3 foot; 2 mm ears with R 1 tops pierced 2.5 mm; the post on a threaded 5 mm
    drum; sling loop and its lug."""
    xs = stations(GB[0], GB[1], 0.0030, 0.0015, 4, extra=np.linspace(0.4215, 0.4260, 7))
    polys = []
    for x in xs:
        ins = end_inset(x, GB[0], GB[1] + 0.01, 0.0015)
        ch = max(0.0, x - (GB[1] - 0.0030))
        ring = soft_union_ring([(0.0, 0.0, 0.0130 - ins - ch), (0.0, 0.019, max(0.0093 - ins - ch, 0.0))], 0.0105,
                               (0.0, 0.006), 80)
        ring[:, 1] = np.where(ring[:, 1] < 0, ring[:, 1] * 0.86, ring[:, 1])
        polys.append(ring)
    gb = loft_polys(polys, xs, "GasBlock")
    zs = np.r_[np.linspace(0.0245, 0.0310, 8), np.linspace(0.0318, 0.0440, 9)]
    secs = []
    for z in zs:
        t = (z - 0.0245) / (0.0440 - 0.0245)
        e = z - 0.0283                                   # R 3 foot into the housing's top
        foot = 0.0030 if e <= 0 else (0.0030 - math.sqrt(max(0.0, 0.0030 ** 2 - (0.0030 - e) ** 2)) if e < 0.0030 else 0.0)
        L0 = 0.0220 + (0.0140 - 0.0220) * t + 2 * foot
        wy = 0.0088 + (0.0062 - 0.0088) * t + foot
        secs.append(K.rrect(0.4090 - L0 / 2, 0.4090 + L0 / 2, wy, 0.0020, 0.0020, K=240))
    tower = K.loft_z(secs, zs, 72, name="Tower")
    union(gb, tower)
    cut(gb, lathe([(0.38, 0.0), (0.38, 0.0049), (0.44, 0.0049), (0.44, 0.0)], 32))
    round_edges(gb, 0.0006, 2, 45)
    parts.append(P(gb, BLUED, "body", FRONT))
    for s in (1, -1):
        ear = prism([(0.4020, 0.0400), (0.4160, 0.0400), (0.4150, 0.0600), (0.4132, 0.0630), (0.4048, 0.0630),
                     (0.4030, 0.0600)], s * 0.0068, s * 0.0088, bevel=0.0007, seg=3, fillet=0.0010, name="FEar")
        hole = lathe([(-0.01, 0.0), (-0.01, 0.00125), (0.01, 0.00125), (0.01, 0.0)], 24, axis="Y", at=(0.4092, s * 0.0078, 0.0510))
        cut(ear, hole)
        round_edges(ear, 0.0003, 2, 50)
        parts.append(P(ear, DARK, "body", FRONT))
    prof = [(0.0425, 0.0)]
    for k in range(8):
        z0_ = 0.0427 + k * 0.0006
        prof += [(z0_, 0.0025), (z0_ + 0.0003, 0.0022)]
    prof += [(0.0475, 0.0024), (0.0476, 0.0)]
    drum = lathe(prof, 32, axis="Z", at=(0.409, 0, 0))
    parts.append(P(drum, DARK, "body", FRONT))
    post = lathe([(0.0470, 0.0), (0.0470, 0.0010), (0.0555, 0.0010), (0.0555, 0.0)], 20, axis="Z", at=(0.409, 0, 0),
                 fillet=0.0001)
    cut(post, box(0.4060, 0.4120, -0.002, -0.0007, 0.0500, 0.0560), box(0.4060, 0.4120, 0.0007, 0.002, 0.0500, 0.0560))
    parts.append(P(post, DARK, "body", FRONT))
    parts.append(P(lathe([(0.0, 0.0), (0.0, 0.0014), (0.0045, 0.0014), (0.0050, 0.0010), (0.0050, 0.0)], 20, axis="Z",
                         at=(0.4235, -0.0080, 0.0065)), DARK, "body", FRONT))
    loop = geo.torus(0.0058, 0.0011, 40, 12, name="SlingLoop")
    geo.transform(loop, rot=(90, 0, 0))
    geo.transform(loop, loc=(0.409, 0.0108, -0.0105))
    parts.append(P(loop, DARK, "body", FRONT))
    lug = prism([(0.4015, -0.0105), (0.4165, -0.0105), (0.4165, -0.003), (0.4015, -0.003)], 0.0085, 0.0118, bevel=0.0006,
                seg=2, fillet=0.002)
    cut(lug, lathe([(0.0, 0.0), (0.0, 0.0024), (0.03, 0.0024), (0.03, 0.0)], 20, axis="Y", at=(0.409, -0.01, -0.0105)))
    parts.append(P(lug, BLUED, "body", FRONT))


def barrel_booster(parts):
    bar = lathe([(0.250, 0.0), (0.250, 0.0085), (0.4335, 0.0085), (0.4345, 0.0072), (0.4345, 0.0045), (0.4335, 0.0040),
                 (0.4320, 0.0039), (0.300, 0.0039), (0.300, 0.0)], 64, name="Barrel")
    parts.append(P(bar, DARK, "body", FRONT))
    gt = lathe([(0.255, 0.0), (0.255, 0.0060), (0.256, 0.0065), (0.3935, 0.0065), (0.3935, 0.0)], 48, at=(0, 0, 0.019),
               name="GasTube", fillet=0.0004)
    parts.append(P(gt, DARK, "body", FRONT))
    # booster: body with one groove, flaring mouth, crowned edge, internal cone and a stepped throat
    mb = lathe([(0.426, 0.0090), (0.426, 0.0118), (0.4275, 0.0128), (0.4555, 0.0128), (0.4565, 0.0114), (0.4605, 0.0114),
                (0.4615, 0.0128), (0.4755, 0.0128), (0.4962, 0.0162), (0.4975, 0.0154), (0.4975, 0.0146), (0.4962, 0.0134),
                (0.4930, 0.0124), (0.4800, 0.0066), (0.4790, 0.0058), (0.4440, 0.0050), (0.4440, 0.0086), (0.4300, 0.0086),
                (0.4300, 0.0090)], 56, closed=True, name="Booster", fillet=0.00035)
    flats = [box(0.4290, 0.4548, sgn * 0.0110, sgn * 0.030, -0.03, 0.03) if sgn > 0 else
             box(0.4290, 0.4548, -0.030, -0.0110, -0.03, 0.03) for sgn in (1, -1)]
    knurl = []
    for k in range(20):
        g = box(0.4622, 0.4698, -0.00035, 0.00035, 0.0122, 0.0150)
        geo.transform(g, rot=(k * 18.0, 0, 0))
        knurl.append(g)
    cut(mb, *flats, *knurl)
    round_edges(mb, 0.00015, 1, 40)
    parts.append(P(mb, BLUED, "body", FRONT))


# ----------------------------------------------------------------------------------------------- grip

GBACK = K.spline([(0.0300 + 0.005, -0.0420), (0.0290 + 0.005, -0.0440), (0.0230 + 0.005, -0.0600),
                  (0.0175 + 0.005, -0.0800), (0.0112 + 0.005, -0.1000), (0.0035 + 0.005, -0.1200),
                  (-0.0006 + 0.005, -0.1335), (0.0004 + 0.005, -0.1475)], 10)
GZ = (-0.0420, -0.1475)


def grip_front(z):
    lin = 0.0690 - 0.0020 + (z + 0.036) * (0.0270 / 0.1115)
    return lin + 0.0030 * math.exp(-((z + 0.0973) / 0.026) ** 2)


def grip_section(z, inset=0.0):
    """Egg section (round 3): 36 mm fore-aft and 27 mm across at the middle, the back fuller and rounder than the
    front, a 2 mm palm swell per side at 40 % of the height (31 mm there); the heel rounded R 6."""
    x0 = float(K.x_of_z(GBACK, z)) + inset
    dh = z - GZ[1]
    if dh < 0.006:
        x0 += 0.006 - math.sqrt(max(0.0, 0.006 ** 2 - (0.006 - dh) ** 2))
    x1 = grip_front(z) - inset
    w = 0.0135 + 0.0020 * math.exp(-((z + 0.0842) / 0.0190) ** 2) - inset
    w -= 0.0010 * float(K.smoothstep(-z, 0.125, 0.1475))
    a, xc = (x1 - x0) / 2, (x0 + x1) / 2
    th = np.linspace(0, 2 * math.pi, 160, endpoint=False)
    c, s_ = np.cos(th), np.sin(th)
    p = np.where(c < 0, 2.15, 2.45)
    xx = xc + a * np.sign(c) * np.abs(c) ** (2 / p)
    yy = w * np.sign(s_) * np.abs(s_) ** (2 / p) * (1.0 - 0.14 * np.clip(c, 0, 1) ** 1.5)
    sec = K.poly_section(np.stack([xx, yy], 1), K=480)
    sec.x0, sec.x1 = x0, x1
    return sec


def pistol_grip(parts):
    zs = list(np.arange(GZ[0], GZ[1] + 0.004, -0.0026))
    zs += [GZ[0] - 0.0004, GZ[0] - 0.0012, GZ[1] + 0.0030, GZ[1] + 0.0018, GZ[1] + 0.0009, GZ[1] + 0.0003, GZ[1]]
    zs = np.array(sorted(set(np.round(zs, 6)), reverse=True))
    secs = []
    for z in zs:
        d = GZ[1] + 0.0030 - z
        ins = 0.0 if d <= 0 else 0.0030 - math.sqrt(max(0.0, 0.0030 ** 2 - d * d))
        dt = z - (GZ[0] - 0.0012)
        if dt > 0:
            ins = max(ins, 0.0012 - math.sqrt(max(0.0, 0.0012 ** 2 - dt * dt)))
        secs.append(grip_section(z, ins))
    g = K.loft_z(secs, zs, 88, name="Grip")
    parts.append(P(g, WOOD, "body", FURN))
    # 2 mm steel grip plate under the receiver floor, a visible joint line over the wood
    top = grip_section(GZ[0], -0.0006)
    pl = K.loft_z([top, top, grip_section(GZ[0], -0.0002)], [GZ[0] + 0.0020, GZ[0] + 0.0003, GZ[0]], 88, name="GripPlate")
    round_edges(pl, 0.0003, 2, 40)
    parts.append(P(pl, BLUED, "body", FRONT))
    # 16 mm steel grip-screw cap with a slot
    c = grip_section(GZ[1], 0.004)
    xm = (c.x0 + c.x1) / 2
    cap = lathe([(0.0, 0.0), (0.0, 0.0080), (-0.0006, 0.0080), (-0.0010, 0.0076), (-0.0012, 0.0060), (-0.0013, 0.0)], 40,
                axis="Z", at=(xm, 0.0, GZ[1] + 0.0002), fillet=0.0002, name="GripCap")
    cut(cap, box(xm - 0.006, xm + 0.006, -0.0005, 0.0005, GZ[1] - 0.003, GZ[1] - 0.0007))
    parts.append(P(fix_normals(cap), BLUED, "body", FRONT))


# ----------------------------------------------------------------------------------------------- guard, catch, trigger

def guard_profile():
    """10.5 mm stamped strip, 1.5 mm sheet, both edges turned 1 mm outward (away from the trigger) over a rolled
    bend, so the side view shows a 2.5 mm band with a highlight along the bend. (u: the strip's normal, v across.)"""
    pts = [(0.00075, v) for v in np.linspace(-0.0040, 0.0040, 7)]
    for a in np.linspace(0, math.pi / 2, 6)[1:]:
        pts.append((-0.0005 + 0.00125 * math.cos(a), 0.0040 + 0.00125 * math.sin(a)))
    pts.append((-0.00105, 0.00525))
    for a in np.linspace(math.pi / 2, 1.5 * math.pi, 7)[1:-1]:
        pts.append((-0.00135 + 0.00075 * math.cos(a), 0.0045 + 0.00075 * math.sin(a)))
    pts += [(-0.00135, 0.00375), (-0.00075, 0.00375)]
    pts += [(-0.00075, v) for v in np.linspace(0.0030, -0.0030, 5)]
    pts += [(-0.00075, -0.00375), (-0.00135, -0.00375)]
    for a in np.linspace(math.pi / 2, 1.5 * math.pi, 7)[1:-1]:
        pts.append((-0.00135 + 0.00075 * math.cos(a), -0.0045 - 0.00075 * math.sin(a)))
    pts.append((-0.00105, -0.00525))
    for a in np.linspace(math.pi / 2, 0, 6)[:-1]:
        pts.append((-0.0005 + 0.00125 * math.cos(a), -0.0040 - 0.00125 * math.sin(a)))
    return np.array(pts)


def trigger_guard(parts):
    """Trigger guard (round 3): the stamped strip with turned lips along a path with a 12 mm front corner, a straight
    bottom and a rear leg rising 15 deg forward of vertical into the grip, its rear tab riveted to the floor; the
    catch housing; a stamped spoon paddle catch with two pressed ribs and a 1 mm turned-up thumb edge; the trigger."""
    pts = [(0.0790, -0.04095), (0.0950, -0.04095), (0.0850, -0.0782), (0.1560, -0.0782), (0.1560, -0.04095),
           (0.1620, -0.04095)]
    path2 = fillet_open(pts, [0, 0.0030, 0.0040, 0.0120, 0.0030, 0], 8)
    path2 = densify(path2, 0.0035)
    path = np.stack([path2[:, 0], np.zeros(len(path2)), path2[:, 1]], 1)
    prof = guard_profile()

    def build(sign):
        return K.sweep_var(path, lambda i, t: prof * np.array([sign, 1.0]), name="Guard")
    tg = build(1.0)
    co, _n = geo.arrays(tg)
    ctr = np.array([0.122, -0.060])
    lips = np.abs(co[:, 1]) > 0.0049
    d_l = np.linalg.norm(co[lips][:, [0, 2]] - ctr, axis=1).mean()
    d_a = np.linalg.norm(co[np.abs(co[:, 1]) < 0.002][:, [0, 2]] - ctr, axis=1).mean()
    if d_l < d_a:                                  # the lips must turn away from the trigger
        tg = build(-1.0)
    parts.append(P(tg, BLUED, "body", FRONT))
    for x in (0.0820, 0.0890):                     # the rear tab riveted to the receiver floor
        parts.append(P(swaged_rivet((x, 0.0, -0.0418), "Z", d=0.0040, h=0.0007, sign=-1, ring=0.0002), BLUED, "body", FRONT))
    hs = prism([(0.1500, -0.0410), (0.1650, -0.0410), (0.1650, -0.0470), (0.1620, -0.0505), (0.1530, -0.0505), (0.1500, -0.0470)],
               -0.0080, 0.0080, bevel=0.0010, seg=3, fillet=0.0015, name="CatchHousing")
    cut(hs, box(0.1525, 0.1630, -0.0068, 0.0068, -0.060, -0.0430))
    round_edges(hs, 0.0003, 2, 50)
    parts.append(P(hs, BLUED, "body", FRONT))
    for s in (1, -1):
        parts.append(P(pin_head((0.1575, s * 0.0080, -0.0458), "Y", r=0.0016, h=0.0004, sign=s, seg=16), DARK, "body", FRONT))
    # spoon paddle: 1.2 mm sheet 11 mm wide, dished 1 mm toward the thumb, two pressed ribs, the end turned up 1 mm
    cp_path = K.spline([(0.1578, -0.0440), (0.1600, -0.0520), (0.1645, -0.0600), (0.1690, -0.0660)], 8)
    cpath = np.stack([cp_path[:, 0], np.zeros(len(cp_path)), cp_path[:, 1]], 1)
    vs = np.r_[np.linspace(-0.0055, 0.0055, 21)]

    def spoon(i, t):
        hw = 0.0042 + 0.0013 * float(K.smoothstep(t, 0.0, 0.45))
        v = vs * hw / 0.0055
        dish = 0.0010 * (v / 0.0055) ** 2
        rib = sum(0.0005 * K.smoothstep(0.0011 - np.abs(v - c_), 0.0, 0.0008) for c_ in (-0.0022, 0.0022)) * \
            float(K.smoothstep(t, 0.15, 0.30) * K.smoothstep(0.92 - t, 0.0, 0.12))
        turn = 0.0010 * float(K.smoothstep(t, 0.86, 1.0))
        mid = dish + turn - rib
        front = np.stack([mid - 0.0006, v], 1)
        back = np.stack([mid + 0.0006, v], 1)[::-1]
        return np.vstack([front, back])
    cpd = K.sweep_var(cpath, spoon, name="Catch")
    round_edges(cpd, 0.0002, 2, 50)
    parts.append(P(cpd, DARK, "body", FRONT))
    t = [(0.1045, -0.0345), (0.1125, -0.0345), (0.1135, -0.044), (0.1125, -0.052), (0.1085, -0.061), (0.1030, -0.0685),
         (0.1005, -0.0675), (0.1040, -0.060), (0.1065, -0.052), (0.1060, -0.044)]
    trg = prism(t, -0.0031, 0.0031, bevel=0.0011, seg=3, fillet=0.0012, name="Trigger")
    parts.append(P(trg, DARK, "trigger", FRONT))


# ----------------------------------------------------------------------------------------------- stock

def u_channel(sign=1.0):
    """U profile 8 x 4 mm, 1 mm sheet, opening toward the receiver: (a along the height, b across, + outward)."""
    c = [(-0.0040, 0.0020), (0.0040, 0.0020), (0.0040, -0.0020), (0.0030, -0.0020), (0.0030, 0.0010),
         (-0.0030, 0.0010), (-0.0030, -0.0020), (-0.0040, -0.0020)]
    Pp = rpoly(c, [0.0010, 0.0010, 0.0003, 0.0003, 0.0004, 0.0004, 0.0003, 0.0003], [3, 3, 1, 1, 2, 2, 1, 1],
               [2, 1, 1, 1, 2, 1, 1, 1])
    Pp[:, 1] *= sign
    return [tuple(p) for p in ccw(Pp)]


def stock(parts):
    """Under-folding stock (round 3): two stamped channel arms (10.5 x 2.5 mm, pressed rib, rolled edges) along the
    lower receiver flat from the hinge (X 0.022) to the shoulder piece's cross pin (X 0.236), stepping down in front
    of the magazine well; turned hinge bosses (R 6) seated in the receiver's pressed recess, 5 mm domed rivets, a
    stamped spring latch on the left arm; the shoulder piece a 2.5 mm stamping 100 mm long with a 3 mm flange round
    its edge and an R 120 shoulder curve, tucked under the lower handguard. Inside 40 mm overall."""
    xa0, xa1 = HINGE[0] - 0.00525, PIN[0] + 0.00525
    xs = np.unique(np.round(np.r_[np.linspace(xa0, HINGE[0] + 0.0005, 7), np.linspace(HINGE[0] + 0.002, HINGE[0] + 0.016, 6),
                                  np.arange(HINGE[0] + 0.020, 0.196, 0.016), np.linspace(PIN[0] - 0.0005, xa1, 7),
                                  np.linspace(0.196, 0.234, 11)], 6))
    xs = xs[(xs >= xa0) & (xs <= xa1)]
    for s in (1, -1):
        rings = []
        for x in xs:
            d_end = min(x - xa0, xa1 - x)
            hgt = math.sqrt(max(0.0, 1.0 - ((0.00525 - d_end) / 0.00525) ** 2)) if d_end < 0.00525 else 1.0
            hgt = max(hgt, 0.04)
            flat = float(K.smoothstep(0.0115 - min(abs(x - HINGE[0]), abs(x - PIN[0])), 0.0, 0.0045))
            Q = arm_section(flat, hgt)
            zc = HINGE[1] + (arm_z(x) - HINGE[1]) * float(K.smoothstep(x, HINGE[0] + 0.002, HINGE[0] + 0.016))
            yz = np.stack([s * (ARM_Y0 + Q[:, 0]), zc + Q[:, 1]], 1)
            rings.append(ccw(yz))
        arm = loft_polys(rings, xs, "StockArm")
        parts.append(P(arm, BLUED, "body", FRONT))
        # turned hinge boss in the receiver's pressed recess, the 5 mm axle head over the arm's eye
        boss = lathe([(-0.0004, 0.0), (-0.0004, 0.0060), (0.0004, 0.0060), (0.0008, 0.0056), (0.0009, 0.0040),
                      (0.0009, 0.0)], 40, axis="Y", fillet=0.0002, name="HingeBoss")
        if s < 0:
            geo.transform(boss, scale=(1, -1, 1))
        geo.transform(boss, loc=(HINGE[0], s * 0.0153, HINGE[1]))
        parts.append(P(fix_normals(boss), BLUED, "body", REAR))
        parts.append(P(swaged_rivet((HINGE[0], s * (ARM_Y0 + 0.0025), HINGE[1]), "Y", d=0.0050, h=0.0007, sign=s),
                       DARK, "body", REAR))
        parts.append(P(swaged_rivet((PIN[0], s * (ARM_Y0 + 0.0025), PIN[1]), "Y", d=0.0050, h=0.0007, sign=s),
                       DARK, "body", FRONT))
    # stamped spring latch on the left arm: a leaf riveted at its rear, a pressed button at its front
    yl = ARM_Y0 + 0.0025 + 0.0007                  # on the pressed rib
    latch = prism([(0.0400, ARM_Z - 0.0022), (0.0580, ARM_Z - 0.0019), (0.0600, ARM_Z), (0.0580, ARM_Z + 0.0019),
                   (0.0400, ARM_Z + 0.0022)], yl, yl + 0.0006, bevel=0.00015, seg=2, fillet=0.0012, name="Latch")
    parts.append(P(fix_normals(latch), DARK, "body", FRONT))
    parts.append(P(swaged_rivet((0.0430, yl + 0.0006, ARM_Z), "Y", d=0.0026, h=0.0004, ring=0.0002), DARK, "body", FRONT))
    parts.append(P(lathe([(0.0, 0.0), (0.0, 0.0017), (0.0003, 0.0016), (0.0005, 0.0010), (0.0005, 0.0)], 24, axis="Y",
                         at=(0.0555, yl + 0.0006, ARM_Z), fillet=0.0001), DARK, "body", FRONT))
    xbar = lathe([(-0.0172, 0.0), (-0.0172, 0.0031), (0.0172, 0.0031), (0.0172, 0.0)], 28, axis="Y", at=(PIN[0], 0, PIN[1]),
                 fillet=0.0003)
    parts.append(P(xbar, BLUED, "body", FRONT))
    # shoulder piece: 2.5 mm stamping, raised 3 mm flange round its edge, R 120 shoulder curve, lugs to the cross pin
    X0, X1, R, xm = 0.2340, 0.3370, 0.120, 0.2855
    Z_LOW = -0.0640

    def zlow(x):
        return Z_LOW + (x - xm) ** 2 / (2 * R)
    corners = [(-0.0150, 0.0), (0.0150, 0.0), (0.0150, 0.0055), (0.0125, 0.0055), (0.0125, 0.0025), (-0.0125, 0.0025),
               (-0.0125, 0.0055), (-0.0150, 0.0055)]
    radii = [0.0022, 0.0022, 0.0011, 0.0011, 0.0009, 0.0009, 0.0011, 0.0011]
    xs = stations(X0, X1, 0.0065, 0.0030, 4)
    polys = []
    for x in xs:
        d_end = min(x - X0, X1 - x)
        ins = end_inset(x, X0, X1, 0.0030)
        lift = 0.0027 * float(K.smoothstep(0.0040 - d_end, 0.0, 0.0015))      # the flange runs round the ends
        c = [(cx, cz + (lift if 0.0024 < cz < 0.0030 else 0.0)) for cx, cz in corners]
        q = ccw(rpoly(c, radii, [5, 5, 3, 3, 3, 3, 3, 3], [12, 2, 1, 1, 10, 1, 1, 2]))
        q[:, 0] = np.sign(q[:, 0]) * np.maximum(np.abs(q[:, 0]) - ins, 0.0003)
        q[:, 1] += zlow(x)
        polys.append(q)
    bp = loft_polys(polys, xs, "ButtPlate")
    for sgn in (1, -1):                             # lugs from the plate's rear end up round the cross pin
        lug = prism([(0.2340, zlow(0.2340) + 0.0040), (0.2440, zlow(0.2440) + 0.0040), (0.2420, PIN[1] - 0.0010),
                     (0.2395, PIN[1] + 0.0030), (0.2360, PIN[1] + 0.0042), (0.2325, PIN[1] + 0.0030), (0.2310, PIN[1])],
                    sgn * 0.0128, sgn * 0.0148, bevel=0.0004, seg=2, fillet=0.0015, name="PlateLug")
        cut(lug, lathe([(-0.01, 0.0), (-0.01, 0.0032), (0.01, 0.0032), (0.01, 0.0)], 20, axis="Y", at=(PIN[0], 0, PIN[1])))
        union(bp, fix_normals(lug))
    round_edges(bp, 0.0003, 2, 45)
    parts.append(P(bp, BLUED, "body", FRONT))


# ----------------------------------------------------------------------------------------------- moving parts

def moving(parts):
    # bolt carrier: rounded top (lofted), milled step on the right, bare brushed steel
    def cpoly(x, inset=0.0):
        c = [(-0.0094, 0.0060), (0.0094, 0.0060), (0.0094, 0.0240), (-0.0094, 0.0240)]
        Pp = rpoly(c, [0.0008, 0.0008, 0.0065, 0.0065], [2, 2, 10, 10], [4, 4, 3, 4])
        return offset(ccw(Pp), -inset) if inset else ccw(Pp)
    xs = stations(0.096, 0.204, 0.004, 0.0012, 3)
    car = loft_polys([cpoly(x, end_inset(x, 0.096, 0.204, 0.0012)) for x in xs], xs, "Carrier")
    step = box(0.104, 0.152, -0.012, -0.0078, 0.0050, 0.0128)
    cam = prism([(0.150, 0.0060), (0.166, 0.0060), (0.176, 0.0150), (0.160, 0.0150)], -0.012, -0.0070, bevel=0)
    lighten = prism([(0.110, 0.0140), (0.140, 0.0140), (0.140, 0.0200), (0.110, 0.0200)], -0.012, -0.0078, bevel=0,
                    fillet=0.0025)
    cut(car, step, cam, lighten)
    round_edges(car, 0.0004, 2, 45)
    parts.append(P(car, BRIGHT, "bolt", REAR))
    bolt = lathe([(0.150, 0.0), (0.150, 0.0072), (0.152, 0.0082), (0.2030, 0.0082), (0.2055, 0.0076), (0.2055, 0.0042),
                  (0.2050, 0.0034), (0.2035, 0.0034), (0.2035, 0.0)], 48, name="Bolt", fillet=0.0002)
    parts.append(P(bolt, BRIGHT, "bolt", REAR))
    lugb = prism([(0.162, 0.0060), (0.172, 0.0060), (0.172, 0.0100), (0.162, 0.0100)], -0.0115, -0.0060, bevel=0.0004)
    parts.append(P(lugb, BRIGHT, "bolt", REAR))
    ext = prism([(0.180, -0.0040), (0.2040, -0.0040), (0.2062, -0.0020), (0.2062, 0.0006), (0.2048, 0.0012),
                 (0.180, 0.0012)], -0.0090, -0.0074, bevel=0.0003, seg=2, fillet=0.0005, name="Extractor")
    claw = prism([(0.2040, 0.0004), (0.2066, 0.0004), (0.2066, 0.0016), (0.2040, 0.0016)], -0.0079, -0.0058, bevel=0.0002,
                 seg=1)
    union(ext, claw)
    parts.append(P(ext, DARK, "bolt", REAR))
    parts.append(P(pin_head((0.1900, -0.0090, -0.0014), "Y", r=0.0008, h=0.0002, sign=-1, seg=12), DARK, "bolt", REAR))
    piston = lathe([(0.200, 0.0), (0.200, 0.0045), (0.335, 0.0045), (0.336, 0.0040), (0.336, 0.0)], 24, at=(0, 0, 0.019))
    parts.append(P(piston, BRIGHT, "bolt", REAR))
    stem = prism([(0.172, 0.0100), (0.1855, 0.0100), (0.1840, 0.0185), (0.174, 0.0185)], 0.0090, 0.0322, bevel=0.0008,
                 seg=3, fillet=0.0018, name="Stem")
    parts.append(P(stem, DARK, "bolt", REAR))
    knob = lathe([(0.0300, 0.0), (0.0300, 0.0048), (0.0318, 0.0058), (0.0336, 0.0060), (0.0352, 0.0055),
                  (0.0362, 0.0060), (0.0378, 0.0060), (0.0388, 0.0055), (0.0398, 0.0060), (0.0412, 0.0058), (0.0420, 0.0050),
                  (0.0420, 0.0)], 40, axis="Y", at=(0.180, 0, 0.0145), fillet=0.0003, name="Knob")
    parts.append(P(knob, DARK, "bolt", REAR))
    sp = CH["selector_pivot"]
    # selector: 1.5 mm stamped lever bowed 0.7 mm along its length, finger tab at the front bent out 35 deg with a
    # lip, a raised detent pressed into it
    so = geo.fillet([(0.006, -0.0095), (0.016, -0.0095), (0.096, -0.0018), (0.104, 0.0002), (0.104, 0.0062),
                     (0.096, 0.0062), (0.016, 0.0010), (0.006, 0.0010)], 0.0030, 4, closed=True)
    sel = K.slab(so, 0.0162, 0.0177, step=0.0025, name="Selector")

    def bend(co):
        x = co[:, 0]
        co[:, 1] += 0.0007 * np.sin(math.pi * np.clip((x - 0.006) / 0.090, 0, 1))
        co[:, 1] += np.clip(x - 0.094, 0, None) * math.tan(math.radians(35.0))
        return co
    K.deform(sel, bend)
    K.outward(sel)
    det = lathe([(0.0, 0.0), (0.0, 0.0017), (0.0003, 0.0015), (0.0005, 0.0009), (0.0006, 0.0)], 24, axis="Y",
                at=(0.058, 0.0182, -0.0042), fillet=0.0001)
    union(sel, det)
    round_edges(sel, 0.0003, 2, 45)
    parts.append(P(sel, DARK, "selector", REAR))
    parts.append(P(pin_head((sp[0], 0.0177, sp[2]), "Y", r=0.0042, h=0.0012), DARK, "selector", REAR))


# ----------------------------------------------------------------------------------------------- top cover

def cover_profile(half=0.0168, inset=0.0, lip=True):
    """Outer contour (y, z) of the top cover: straight skirts, half-round crown up to Z 0.034, a stamped lip along
    both lower edges (0.5 mm out over the last 1.2 mm); counter-clockwise, closed along the bottom."""
    pts = []
    for z in (0.0040, 0.0046, 0.0052, 0.0060, 0.0075, 0.0095):
        lp = 0.0005 * float(K.smoothstep(0.0052 - z, 0.0, 0.0008)) if lip else 0.0
        pts.append((half + lp, z))
    nA = 44
    for k in range(nA + 1):
        a = math.pi * k / nA
        pts.append((half * math.cos(a), 0.0115 + 0.0225 * math.sin(a) ** 0.85))
    for y, z in pts[:6][::-1]:
        pts.append((-y, z))
    Pp = ccw(np.array(pts))
    return offset(Pp, -inset) if inset else Pp


COVER_RIBS = (0.039, 0.048, 0.057)


def rib_bump(x):
    """Pressed rib height (m) at x: three ribs 3 mm wide, 1 mm high, 0.5 mm shoulder radii."""
    return sum(0.0010 * float(K.smoothstep(0.0015 - abs(x - r), -0.0005, 0.0005)) for r in COVER_RIBS)


def cover_rings(xs, inset, x0, x1, r_end):
    polys = []
    for x in xs:
        Pp = cover_profile(inset=inset, lip=inset == 0.0)
        if x0 is not None:                          # pressed ends: shrink toward the crown's centre
            ins = end_inset(x, x0, x1, r_end)
            c = np.array([0.0, 0.0150])
            Pp = c + (Pp - c) * (1.0 - ins / 0.0185)
        top_w = np.clip((Pp[:, 1] - 0.0175) / 0.010, 0, 1)
        T = np.roll(Pp, -1, 0) - np.roll(Pp, 1, 0)
        T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
        N = np.stack([T[:, 1], -T[:, 0]], 1)
        Pp = Pp + N * (rib_bump(x) * top_w)[:, None]
        polys.append(Pp)
    return polys


def cover(parts):
    """Top cover rebuilt: a 1 mm half-round sheet pressed with three transverse ribs (3 mm wide, 1 mm high, clean
    radii), a stamped lip along the lower edges, its rear end pressed down round the trunnion (3 mm radius) with the
    recoil-spring guide's tab through a 7 x 8 mm hole; the rail (10 lugs, 45 deg dovetail flanks, 5.3 mm slots, two
    cross-bolts) and the first-pass rear sight (notch profile unchanged)."""
    x0, x1 = 0.002, 0.186
    xs = stations(x0, x1, 0.007, 0.003, 4, extra=np.concatenate([r + np.linspace(-0.0024, 0.0024, 11)
                                                                     for r in COVER_RIBS]))
    outer = loft_polys(cover_rings(xs, 0.0, x0, x1, 0.003), xs, "Cover")
    xi = np.r_[x0 + 0.0010, xs[xs > x0 + 0.0012], x1 + 0.004]
    inner = loft_polys(cover_rings(xi, 0.0010, None, None, 0.0), xi, "CoverIn")
    K.deform(inner, lambda co: np.c_[co[:, 0], co[:, 1], co[:, 2] - 0.0012 * (co[:, 2] < 0.0045)])
    cut(outer, inner)
    port = prism([(0.108, 0.0005), (0.172, 0.0005), (0.172, 0.030), (0.108, 0.030)], -0.030, -0.009, fillet=0.003, bevel=0)
    slot = box(0.0790, 0.1930, 0.009, 0.030, 0.0030, 0.0193)
    hole = prism(rpoly([(-0.0035, 0.0160), (0.0035, 0.0160), (0.0035, 0.0240), (-0.0035, 0.0240)], [0.0015] * 4,
                       [4] * 4, [1] * 4), -0.010, 0.0060, axis="X", bevel=0, name="GuideHole")
    cut(outer, port, slot, hole)
    round_edges(outer, 0.0004, 2, 45)
    parts.append(P(outer, COVER, "body", REAR))
    # recoil-spring guide's rear tab through the hole: rounded block with a domed end
    xb = stations(-0.0045, 0.0032, 0.0015, 0.0016, 4)
    tab = loft_polys([offset(ccw(rpoly([(-0.0031, 0.0164), (0.0031, 0.0164), (0.0031, 0.0236), (-0.0031, 0.0236)],
                                       [0.0012] * 4, [4] * 4, [2] * 4)), -end_inset(x, -0.0045, 0.0090, 0.0016))
                      for x in xb], xb, "GuideTab")
    parts.append(P(tab, DARK, "body", REAR))
    # rail on the cover: dovetail profile with 45 deg flanks, 10 lugs, 5.3 mm slots, two cross-bolts
    rp = [(-0.0078, 0.0300), (0.0078, 0.0300), (0.0078, 0.0356), (0.0106, 0.0383), (0.0106, 0.0393), (0.0078, 0.0420),
          (-0.0078, 0.0420), (-0.0106, 0.0393), (-0.0106, 0.0383), (-0.0078, 0.0356)]
    rail = prism(rp, 0.062, 0.168, axis="X", bevel=0.0003, seg=2, name="Rail")
    pitch = 0.106 / 10
    slots, bolts = [], []
    for k in range(10):
        xc = 0.062 + pitch * (k + 1.0)
        if xc > 0.166:
            continue
        slots.append(prism([(xc - 0.00265, 0.0450), (xc + 0.00265, 0.0450), (xc + 0.00265, 0.0369), (xc + 0.00235, 0.0366),
                            (xc - 0.00235, 0.0366), (xc - 0.00265, 0.0369)], -0.02, 0.02, bevel=0, name="RailSlot"))
        if k in (1, 6):
            bolts.append(xc)
    cut(rail, *slots)
    round_edges(rail, 0.0003, 2, 40)
    parts.append(P(rail, DARK, "body", REAR))
    for xc in bolts:
        parts.append(P(lathe([(-0.0098, 0.0), (-0.0098, 0.0016), (0.0098, 0.0016), (0.0098, 0.0)], 16, axis="Y",
                             at=(xc, 0.0, 0.0333)), DARK, "body", REAR))
        for sgn in (1, -1):
            hx = lathe([(0.0, 0.0), (0.0, 0.0026), (0.0012, 0.0026), (0.0016, 0.0020), (0.0016, 0.0)], 6, axis="Y",
                       fillet=0.0001)
            if sgn < 0:
                geo.transform(hx, scale=(1, -1, 1))
            geo.transform(hx, loc=(xc, sgn * 0.0079, 0.0333))
            parts.append(P(fix_normals(hx), DARK, "body", REAR))


def rear_trunnion(parts):
    """Forged rear trunnion inside the receiver sheet (round 3): 0.3 mm inside the sheet's outer face so the sheet's
    rear edge reads as its own step, R 2 on every outer edge, rear face domed 1.5 mm; the stock latch on its left."""
    x0, x1 = -0.0030, 0.0160
    xs = stations(x0, x1, 0.003, 0.0020, 6)
    polys = []
    for x in xs:
        ins = end_inset(x, x0, x1 + 0.01, 0.0020)
        polys.append(offset(ccw(rpoly([(-0.0157, -0.0394), (0.0157, -0.0394), (0.0157, 0.0108), (-0.0157, 0.0108)],
                                      [0.0020] * 4, [6] * 4, [10, 12, 10, 12])), -ins))
    tr = loft_polys(polys, xs, "RearTrunnion")
    cut(tr, box(0.0034, 0.030, -0.0102, 0.0102, 0.0042, 0.030))          # the carrier's path at full travel
    K.deform(tr, lambda co: np.c_[co[:, 0] - 0.0015 * np.clip(1 - (co[:, 1] / 0.0157) ** 2, 0, 1)
                                  * np.clip(1 - ((co[:, 2] + 0.0143) / 0.0251) ** 2, 0, 1) * (co[:, 0] < x0 + 0.0021),
                                  co[:, 1], co[:, 2]])
    round_edges(tr, 0.0004, 2, 40)
    parts.append(P(tr, BLUED, "body", REAR))
    rb = lathe([(0.0, 0.0), (0.0, 0.0058), (-0.0006, 0.0058), (-0.0009, 0.0052), (-0.0010, 0.0030), (-0.0010, 0.0)], 40,
               axis="X", at=(-0.0040, 0.0, -0.0170), fillet=0.0002, name="RearBoss")      # turned buffer-pin boss
    parts.append(P(rb, BLUED, "body", REAR))
    parts.append(P(pin_head((-0.0050, 0.0, -0.0170), "X", r=0.0016, h=0.0003, sign=-1, seg=20), DARK, "body", REAR))
    lugp = prism([(-0.0010, -0.0300), (0.0080, -0.0300), (0.0080, -0.0225), (0.0035, -0.0205), (-0.0010, -0.0225)],
                 0.0157, 0.0172, bevel=0.0004, seg=2, fillet=0.0015, name="SlingLug")
    cut(lugp, lathe([(-0.01, 0.0), (-0.01, 0.0017), (0.01, 0.0017), (0.01, 0.0)], 16, axis="Y", at=(0.0028, 0, -0.0258)))
    parts.append(P(fix_normals(lugp), BLUED, "body", REAR))
    boss = lathe([(0.0, 0.0), (0.0, 0.0032), (0.0006, 0.0032), (0.0010, 0.0027), (0.0010, 0.0)], 32, axis="Y",
                 at=(-0.0002, 0.0155, -0.0120), fillet=0.0002)
    parts.append(P(boss, BLUED, "body", REAR))
    btn = lathe([(0.0, 0.0), (0.0, 0.0020), (0.0016, 0.0020), (0.0021, 0.0016), (0.0022, 0.0)], 32, axis="Y",
                at=(-0.0002, 0.0157, -0.0120), fillet=0.0002)
    parts.append(P(btn, DARK, "body", REAR))


# ----------------------------------------------------------------------------------------------- build

def uv_weights(ob):
    """Per-face UV scale for a CHOPPER piece: hidden faces (inside the receiver and cover, barrel and gas tube
    under the wood, liners, piston, bore) get few texels so the faces the eye sees get the density."""
    me = ob.data
    n = len(me.polygons)
    mid = np.empty(n, np.float32)
    me.attributes["mid"].data.foreach_get("value", mid)
    mid = np.rint(mid).astype(int)
    c = np.empty(n * 3, np.float32)
    me.polygons.foreach_get("center", c)
    c = c.reshape(-1, 3)
    nr = np.empty(n * 3, np.float32)
    me.polygons.foreach_get("normal", nr)
    nr = nr.reshape(-1, 3)
    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    w = np.ones(n, np.float32)
    w[mid == BORE] = 0.35
    w[(mid == BLUED) & (np.abs(y) < 0.0153) & (z > -0.0385) & (z < 0.0105) & (x > 0.0045) & (x < 0.1895)] = 0.3
    w[(mid == COVER) & ((nr[:, 1] * y + nr[:, 2] * (z - 0.0115)) < 0)] = 0.3
    dark = mid == DARK
    w[dark & (x > 0.250) & (x < 0.3815) & (np.hypot(y, z) < 0.0088)] = 0.45
    w[dark & (x > 0.256) & (x < 0.372) & (np.hypot(y, z - 0.019) < 0.0068)] = 0.45
    w[dark & (x > 0.2520) & (x < 0.3795) & (np.abs(y) < 0.0170) & (z < -0.004)] = 0.4
    w[dark & (x > 0.2600) & (x < 0.3740) & (np.hypot(y, z - 0.0178) < 0.0112) & (z > 0.006)] = 0.4
    w[(mid == BRIGHT) & (x > 0.200) & (np.hypot(y, z - 0.019) < 0.0047)] = 0.3
    # round 3: the carrier keeps the receiver's density (seen through the left slot and the port), only its
    # underside and the faces inside the receiver's rails go low
    w[(mid == BRIGHT) & (x < 0.2045) & (nr[:, 2] < -0.7)] = 0.4
    # receiver: the rails under the cover, the trunnion top under the sight block, the floor
    rec = (mid == BLUED) & (np.abs(y) < 0.0165)
    w[rec & (nr[:, 2] > 0.7) & (z > 0.0105) & (z < 0.0125)] = 0.3
    w[rec & (nr[:, 2] < -0.7) & (z < -0.0395) & (x > 0.040) & (x < 0.150)] = 0.6
    return w


def swaged_rivet(at, axis="Y", d=0.0040, h=0.0009, sign=1, ring=0.0003, seg=20):
    """Domed rivet head with the swaged ring the set left round its base (0.3 mm wide, 0.1 mm proud)."""
    r = d / 2
    prof = [(-0.0004, 0.0), (-0.0004, r + ring), (0.00008, r + ring), (0.00013, r),
            (h * 0.35, r * 0.91), (h * 0.68, r * 0.64), (h * 0.92, r * 0.30), (h, 0.0)]
    ob = lathe(prof, seg, axis=axis, name="Rivet")
    if sign < 0:
        geo.transform(ob, scale=(1, -1, 1) if axis == "Y" else ((-1, 1, 1) if axis == "X" else (1, 1, -1)))
    geo.transform(ob, loc=at)
    return fix_normals(ob)


def fillet_open(points, radii, nseg=6):
    """Open polyline (x, z) with each inner corner i rounded by radii[i] (radii[0] and radii[-1] are ignored)."""
    P_ = [np.asarray(p, dtype=np.float64) for p in points]
    out = [P_[0]]
    for i in range(1, len(P_) - 1):
        p0, p1, p2 = P_[i - 1], P_[i], P_[i + 1]
        a, b = p0 - p1, p2 - p1
        la, lb = np.linalg.norm(a), np.linalg.norm(b)
        a, b = a / la, b / lb
        ang = math.acos(float(np.clip(np.dot(a, b), -1, 1)))
        r = radii[i]
        if r <= 0 or ang > math.pi - 1e-4:
            out.append(p1)
            continue
        t = min(r / math.tan(ang / 2), 0.49 * la, 0.49 * lb)
        r = t * math.tan(ang / 2)
        bis = (a + b) / np.linalg.norm(a + b)
        c = p1 + bis * (r / math.sin(ang / 2))
        v0, v1 = p1 + a * t - c, p1 + b * t - c
        sw = math.pi - ang
        for f in np.linspace(0, 1, nseg + 1):
            out.append(c + v0 * math.sin((1 - f) * sw) / math.sin(sw) + v1 * math.sin(f * sw) / math.sin(sw))
    out.append(P_[-1])
    return np.array(out)


def densify(path, step):
    out = []
    for a, b in zip(path[:-1], path[1:]):
        n = max(1, int(np.linalg.norm(b - a) / step))
        for k in range(n):
            out.append(a + (b - a) * k / n)
    out.append(path[-1])
    return np.array(out)


def rear_sight(parts):
    """Rear sight (round 3): base 14 mm long with 8 deg drafted sides and 0.5 mm top breaks, a 2 mm cross pin through
    it; the leaf with a 0.6 mm chamfer on its top rear edge (anti-glare lines in the normal map); ears with rounded
    tops. Notch 4.4 x 4.2 mm, top Z 0.0555 (kept)."""
    tn = math.tan(math.radians(8.0))

    def rsb_poly(x, ins):
        zb, zt = 0.0280, 0.0415 - ins
        wb = 0.0100 - ins
        wt = 0.0100 - (zt - zb) * tn - ins
        c = [(-wb, zb), (wb, zb), (wt, zt), (-wt, zt)]
        return ccw(rpoly(c, [0.0, 0.0, 0.0005, 0.0005], [0, 0, 3, 3], [6, 5, 6, 5]))
    xb0, xb1 = 0.0165, 0.0305
    xs_ = stations(xb0, xb1, 0.0015, 0.0008, 3)
    base = loft_polys([rsb_poly(x, end_inset(x, xb0, xb1, 0.0008)) for x in xs_], xs_, "RSBase")
    parts.append(P(base, DARK, "body", REAR))
    for s in (1, -1):
        y = s * (0.0100 - (0.0320 - 0.0280) * tn)
        parts.append(P(pin_head((0.0270, y, 0.0320), "Y", r=0.0010, h=0.00025, sign=s, seg=16), BLUED, "body", REAR))
    leaf = prism([(0.0215, 0.0400), (0.0255, 0.0400), (0.0255, 0.0555), (0.0221, 0.0555), (0.0215, 0.0549)],
                 -0.0072, 0.0072, bevel=0.00025, seg=2, name="Leaf")
    cut(leaf, box(0.018, 0.030, -0.0022, 0.0022, 0.0513, 0.06))
    round_edges(leaf, 0.0002, 2, 50)
    parts.append(P(leaf, DARK, "body", REAR))
    for s_ in (1, -1):
        ear = prism([(0.0165, 0.0380), (0.0305, 0.0380), (0.0290, 0.0555), (0.0190, 0.0555)], s_ * 0.0076, s_ * 0.0102,
                    bevel=0.0005, seg=3, fillet=0.0018, name="Ear")
        parts.append(P(fix_normals(ear), DARK, "body", REAR))


ARM_Z = -0.0335                      # arm centre line along the lower receiver flat


PIN = (0.236, -0.0455)               # the shoulder piece's cross pin, under the receiver in front of the magazine


ARM_Y0 = 0.0156                      # the arm's rolled edges sit on the receiver sheet


def arm_rib(v, k=1.0):
    return 0.0008 * k * float(K.smoothstep(0.0030 - abs(v), 0.0, 0.0015))


def arm_section(flat=0.0, height=1.0):
    """Stamped arm channel in (u, v): u outward from the receiver sheet, v up. 10.5 mm tall, 2.5 mm deep, 1 mm web
    with a pressed centre rib 0.8 mm high, both edges rolled into 2 mm beads toward the receiver. flat (0..1)
    flattens it into the plain 2 mm bar of the ends; height scales v (the rounded ends)."""
    k = 1.0 - flat
    hb = 0.00425
    pts = []
    for v in np.linspace(-hb, hb, 23):
        pts.append((0.0025 + arm_rib(v, k), v))
    br = 0.0010 * k + 0.00001
    for a in np.linspace(0, 1.5 * math.pi, 13)[1:]:
        pts.append((0.0025 - br + br * math.cos(a), hb + br * math.sin(a)))
    ui = 0.0015 - 0.0010 * flat
    for v in np.linspace(hb - br, -(hb - br), 21):
        pts.append((ui + arm_rib(v, k) * (1.0 if abs(v) < hb - br else 0.0), v))
    for a in np.linspace(0.5 * math.pi, 2.0 * math.pi, 13)[:-1]:
        pts.append((0.0025 - br + br * math.cos(a), -hb + br * math.sin(a)))
    Q = np.array(pts)
    Q[:, 1] *= height
    return Q


def arm_z(x):
    return ARM_Z + (PIN[1] - ARM_Z) * float(K.smoothstep(x, 0.200, 0.234))


def hg_ends(x):
    return float(K.smoothstep(x, 0.252, 0.264) * K.smoothstep(0.370 - x, 0.0, 0.010))


def retaining_band(parts):
    """Retaining band (round 3): a 1.5 mm sheet loop round the handguard's tapered front and the barrel, standing
    0.5 mm proud of the wood, rounded ends; its lever latch on the right."""
    from mathutils import geometry as mg
    xb0, xb1 = 0.3790, 0.3915
    sec = lhg_poly(LHG[1])
    hull_pts = [tuple(p) for p in sec] + [(0.0092 * math.cos(a), 0.0092 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 48, endpoint=False)]
    idx = mg.convex_hull_2d(hull_pts)
    hull = ccw(np.array([hull_pts[i] for i in idx]))
    hull = K.resample(hull, 84)
    hull = ccw(hull)
    outer = offset(hull, 0.0020)
    inner = offset(hull, 0.0005)
    xs = stations(xb0, xb1, 0.0030, 0.0008, 3)
    band = loft_polys([offset(outer, -end_inset(x, xb0, xb1, 0.0008)) for x in xs], xs, "Band")
    hole = loft_polys([inner, inner], [xb0 - 0.002, xb1 + 0.002], "BandIn")
    cut(band, hole)
    round_edges(band, 0.0004, 2, 50)
    parts.append(P(band, BLUED, "body", FRONT))
    yb = float(outer[:, 0].min())
    lev = prism([(0.3810, -0.0215), (0.3900, -0.0215), (0.3925, -0.0050), (0.3880, -0.0025), (0.3800, -0.0045)],
                yb - 0.0014, yb + 0.0001, bevel=0.0004, seg=2, fillet=0.0015, name="BandLever")
    parts.append(P(fix_normals(lev), DARK, "body", FRONT))
    parts.append(P(pin_head((0.3852, yb - 0.0014, -0.0185), "Y", r=0.0015, h=0.0004, sign=-1, seg=16), DARK, "body", FRONT))


def chopper_parts():
    parts = []
    chopper_receiver(parts)
    rear_trunnion(parts)
    cover(parts)
    rear_sight(parts)
    sight_block(parts)
    lower_handguard(parts)
    upper_handguard(parts)
    gas_block(parts)
    barrel_booster(parts)
    pistol_grip(parts)
    trigger_guard(parts)
    stock(parts)
    moving(parts)
    return parts


def chopper_build(ctx, finish=None):
    """Join the parts per texture set (finish(ob, set_name) unwraps and textures each piece), then into SK_Chopper
    with three material slots, and bind to the armature."""
    groups = {REAR: [], FURN: [], FRONT: []}
    for ob in chopper_parts():
        a = ob.data.attributes.get("tset")
        t = int(round(a.data[0].value)) if a is not None and len(ob.data.polygons) else REAR
        groups[t].append(ob)
    pieces = []
    for t in (REAR, FURN, FRONT):
        ob = geo.join(groups[t], "SK_Chopper_" + SET_NAMES[t], ctx.col)
        if finish:
            finish(ob, SET_NAMES[t])
        pieces.append(ob)
    gun = geo.join(pieces, "SK_Chopper", ctx.col)
    bones = [rig.Bone("body", (0, 0, 0)),
             rig.Bone("bolt", (0.180, 0, 0.0145), "body"),
             rig.Bone("trigger", CH["trigger_pivot"], "body"),
             rig.Bone("selector", CH["selector_pivot"], "body"),
             rig.Bone("magazine", (0, 0, 0), "body")]
    bones += [rig.Bone(k, v, "body", deform=False) for k, v in CH["sockets"].items()]
    arm = rig.armature("SKEL_Chopper", bones, ctx.col)
    rig.bind(gun, arm)
    return gun, arm


def chopper_magazine(col):
    """SM_Weapon_ChopperMagazine (+ _TopRound): stamped body lofted along the arc with raised (0.8 mm, soft) ribs
    pressed across the sides and one side rib along the whole arc, spine, feed lips folded from 1 mm sheet, front
    lock lug and rear catch tab, floor plate with its retaining dimple. Origin = gun origin."""
    R, a0, a1, (Pt0, C) = W.chopper_mag_geometry()
    Wd = 0.02550 / 2
    parts = []
    arc_len = R * abs(a1 - a0)
    cross = (0.27, 0.48, 0.69, 0.88)              # four stamped reinforcing ribs across the sides
    base = np.linspace(0.0, 1.0, 60)
    extra = []
    for c in cross:
        extra += list(c + np.linspace(-3.2, 3.2, 13) * 0.001 / arc_len)
    st = np.unique(np.clip(np.concatenate([base, extra, [0.004, 0.012]]), 0, 1))

    def plateau(dist, hw, sh=0.0005):
        """1 on a flat-topped rib of half width hw with sh-wide rounded shoulders, 0 off it."""
        return float(K.smoothstep(hw - dist, -sh / 2, sh / 2))

    def swell(dist):
        """Round 3: a soft pressed swell 6 mm wide (3 mm fillets each side), 1 at its crown."""
        return float(K.smoothstep(0.0030 - dist, 0.0, 0.0030))

    def across(d):
        """Depth samples (metres from the centre line, -d back .. +d front): dense at the long rib's shoulders."""
        u = list(np.linspace(-d, d, 25))
        u += [v * 0.001 for v in np.linspace(-3.2, 3.2, 17)]
        u += [sgn * (d - e * 0.001) for sgn in (1, -1) for e in (0.6, 1.2, 1.8, 2.4)]
        return np.array(sorted(set(np.round(u, 6))))

    def section(sv, inner=False):
        """Flat stamped side walls with crisp raised ribs (2.5 mm wide, 0.8 mm proud, 0.5 mm shoulders): one
        along the arc at mid depth, four across; front and back walls rounded 2.2 mm into the sides."""
        d = (0.062 + (0.059 - 0.062) * sv) / 2
        a = a0 + (a1 - a0) * sv
        n = np.array([math.cos(a), math.sin(a)])
        Pc = C - R * n
        s_m = sv * arc_len
        xr0 = max(swell(abs(s_m - c * arc_len)) for c in cross)
        us = across(d)
        pts = []
        for side in (1, -1):
            seq = us if side == 1 else us[::-1]
            for u in seq:
                lng = swell(abs(u))
                xr = xr0 * plateau(abs(u), d - 0.0060, 0.004)
                y = side * (Wd + 0.0009 * max(lng, xr))
                e = abs(u) - (d - 0.0024)
                if e > 0:                           # 2.2 mm corner radius into the front and back walls
                    k = min(e / 0.0024, 1.0)
                    y = side * (Wd - 0.0022 * (1 - math.sqrt(max(0.0, 1 - k * k))))
                nn = u
                if u < -d + 0.0005 and abs(y) > Wd * 0.4:
                    nn -= 0.0006
                pts.append((nn, y))
        pts = np.array(pts)
        if inner:
            pts = pts * np.array([(d - 0.0010) / d, (Wd - 0.0010) / Wd])
        return np.array([[Pc[0] + p[0] * n[0], p[1], Pc[1] + p[0] * n[1]] for p in pts])
    body = loft([section(s_) for s_ in st], cap0=False, cap1=True, name="MagBody")
    parts.append(P0(body, BLUED, None))
    inner_st = st[st <= 0.16]
    inn = loft([section(s_, True) for s_ in inner_st], cap0=False, cap1=True, name="MagInner")
    import bmesh  # noqa: F401
    bm = geo.bm_of(inn)
    for f in bm.faces:
        f.normal_flip()
    geo.bm_to(inn, bm)
    parts.append(P0(inn, BORE, None))
    o, i = section(0.0), section(0.0, True)
    m = len(o)
    rim = geo.from_arrays("MagRim", np.concatenate([o, i]), [(j, (j + 1) % m, m + (j + 1) % m, m + j) for j in range(m)],
                          smooth=None)
    fix_normals(rim)
    bmr = geo.bm_of(rim)
    up = Vector((-math.sin(a0), 0, math.cos(a0)))
    if sum((f.normal.dot(up) for f in bmr.faces)) < 0:
        for f in bmr.faces:
            f.normal_flip()
    geo.bm_to(rim, bmr)
    parts.append(P0(rim, BLUED, None))
    # feed lips: the side walls folded in over the rounds, 1 mm sheet, rounded fold
    t0 = np.array([math.sin(a0), -math.cos(a0)])
    n0 = np.array([math.cos(a0), math.sin(a0)])
    for s in (1, -1):
        prof = [(Wd, 0.0), (Wd, 0.0022), (Wd - 0.0005, 0.0034), (Wd - 0.0016, 0.0043), (Wd - 0.0034, 0.0048),
                (Wd - 0.0050, 0.0046), (Wd - 0.0056, 0.0040), (Wd - 0.0050, 0.0034), (Wd - 0.0032, 0.0037),
                (Wd - 0.0016, 0.0031), (Wd - 0.0010, 0.0020), (Wd - 0.0010, 0.0)]
        prof = [(s * y, h) for y, h in prof]
        if s < 0:
            prof = prof[::-1]
        secs = []
        for u in np.linspace(-0.030, 0.012, 11):
            bp_ = Pt0 + u * n0
            taper = float(smoothstep((u - 0.004) / 0.008))          # the lips run out toward the front
            secs.append([(bp_[0] - h * (1 - 0.5 * taper) * t0[0], y * (1 - 0.0 * taper), bp_[1] - h * (1 - 0.5 * taper) * t0[1])
                         for y, h in prof])
        parts.append(P0(loft(secs, name="Lip"), BLUED, None))

    def place(ob, sv, along_n, along_t):
        a = a0 + (a1 - a0) * sv
        n = np.array([math.cos(a), math.sin(a)])
        t = np.array([math.sin(a), -math.cos(a)])
        Pc = C - R * n
        rot = Matrix(((n[0], 0, t[0]), (0, 1, 0), (n[1], 0, t[1])))
        M = Matrix.Translation((Pc[0] + n[0] * along_n - t[0] * along_t, 0, Pc[1] + n[1] * along_n - t[1] * along_t)) @ rot.to_4x4()
        ob.data.transform(M)
        return fix_normals(ob)
    # forged front locking lug (10 x 6 mm, hooks into the well at the hinge) and the rear catch lug
    d0 = 0.031
    lug = K.loft_x([K.poly_section(rpoly([(-0.0050, -0.0005), (0.0050, -0.0005), (0.0050, 0.0055), (-0.0050, 0.0055)],
                                         [0.0008, 0.0008, 0.0015, 0.0015], [2, 2, 3, 3], [3, 2, 3, 2]), K=96)] * 2,
                   [0.0, 0.0036], 48, name="Lug")
    K.deform(lug, lambda co: np.c_[co[:, 0] - 0.0012 * K.smoothstep(co[:, 2], 0.0, 0.0055) * (co[:, 0] > 0.002),
                                   co[:, 1], co[:, 2]])
    round_edges(lug, 0.0004, 2, 40)
    place(lug, 0.0, d0 - 0.0004, -0.0022)
    parts.append(P0(lug, BLUED, None))
    tab = W.box(-0.0034, 0.0, -0.0042, 0.0042, 0.0000, 0.0046, bevel=0.0007, seg=2, name="Tab")
    union(tab, W.box(-0.0050, -0.0026, -0.0042, 0.0042, 0.0030, 0.0046, bevel=0.0006, seg=2))
    place(tab, 0.0, -d0 + 0.0002, 0.0060)
    parts.append(P0(tab, BLUED, None))
    # weld seam along the spine (back wall centre line), 0.9 mm bead
    sp = []
    for sv in np.linspace(0.03, 0.985, 70):
        a = a0 + (a1 - a0) * sv
        n = np.array([math.cos(a), math.sin(a)])
        Pc = C - R * n
        d = (0.062 + (0.059 - 0.062) * sv) / 2
        q = Pc + n * (-d - 0.0003)
        sp.append((q[0], 0.0, q[1]))
    spine = K.sweep_var(np.array(sp), lambda i, t: K.superellipse(0.00042, 0.0030, 3.0, 20), name="Spine")
    parts.append(P0(spine, BLUED, None))
    fr_ = []
    for sv in np.linspace(0.04, 0.985, 60):            # the front seam's weld bead
        a = a0 + (a1 - a0) * sv
        n = np.array([math.cos(a), math.sin(a)])
        Pc = C - R * n
        d = (0.062 + (0.059 - 0.062) * sv) / 2
        q = Pc + n * (d + 0.0002)
        fr_.append((q[0], 0.0, q[1]))
    bead = K.sweep_var(np.array(fr_), lambda i, t: K.superellipse(0.00035, 0.0006, 2.0, 10), name="Bead")
    parts.append(P0(bead, BLUED, None))
    # floor plate: 27.8 x 63.5 mm, 1.5 mm edges turned up round the body, a rear retaining tab, the dimple
    nb = np.array([math.cos(a1), math.sin(a1)])
    tb = np.array([math.sin(a1), -math.cos(a1)])
    Pb = C - R * nb
    zs_ = [-0.0046, -0.0040, -0.0032, -0.0020, -0.0008, 0.0010, 0.0016]
    secs = []
    for z in zs_:
        ins = 0.0 if z > -0.0032 else (0.0014 - math.sqrt(max(0.0, 0.0014 ** 2 - (z + 0.0032) ** 2)))
        if z > 0.0012:
            ins = 0.0006
        secs.append(K.rrect(-0.03175 + ins, 0.03175 - ins, 0.0139 - ins, 0.0035 - ins * 0.5, 0.0035 - ins * 0.5, K=200))
    fp = K.loft_z(secs, zs_, 96, name="Floor")
    cut(fp, W.box(-0.0302, 0.0302, -0.0124, 0.0124, -0.0001, 0.003))        # the turned edges stand round the body
    union(fp, W.box(-0.0318, -0.0292, -0.0045, 0.0045, -0.0030, 0.0068, bevel=0.0006, seg=2))   # retaining tab
    dm = geo.sphere(1.0, 24, 12)
    geo.transform(dm, scale=(0.006, 0.006, 0.0012))
    geo.transform(dm, loc=(-0.012, 0.0, -0.0050))
    cut(fp, dm)
    round_edges(fp, 0.0003, 2, 40)
    rot = Matrix(((nb[0], 0, tb[0]), (0, 1, 0), (nb[1], 0, tb[1])))
    M = Matrix.Translation((Pb[0], 0, Pb[1])) @ rot.to_4x4() @ Matrix.Diagonal((1, 1, -1, 1))
    fp.data.transform(M)
    fp.data.flip_normals()
    fix_normals(fp)
    parts.append(P0(fp, DARK, None))
    sec = W.cartridge(0.050, 0.0056, name="Round2")
    geo.transform(sec, loc=(0.172, -0.0042, -0.0195 - 0.0092))
    parts.append(sec)
    top = W.cartridge(0.050, 0.0056, name="TopRound")
    geo.transform(top, loc=(0.172, 0.0042, -0.0195))
    body = geo.join(parts, "SM_Weapon_ChopperMagazine", col)
    scene.move_to(top, col)
    top.name = top.data.name = "SM_Weapon_ChopperMagazine_TopRound"
    return body, top
