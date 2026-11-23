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
HINGE = (0.022, -0.028)
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
                     grid_pts(HINGE[0] - 0.012, HINGE[0] + 0.012, HINGE[1] - 0.012, HINGE[1] + 0.012, 0.0012),
                     grid_pts(-0.004, 0.256, -0.040, -0.033, 0.002)])
    rec = slab_pts(outline, -0.016, 0.016, pts, name="Receiver")

    def press(co):
        for s in (1, -1):
            co = crisp_dent(co, s, DIMPLE["x"], DIMPLE["z"], DIMPLE["length"], DIMPLE["width"], DIMPLE["depth"], 0.0010)
            co = K.dent(co, (HINGE[0], s * 0.016, HINGE[1]), (0, s, 0), 0.0007, 0.0105)
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
            parts.append(P(dome_rivet((x, y - s * 0.0001, z), "Y", sign=s), BLUED, "body", REAR))
        parts.append(P(dome_rivet((0.140, y - s * 0.0001, -0.034), "Y", d=0.0040, h=0.0007, sign=s), BLUED, "body", REAR))
    # trigger pin, hammer pin (heads both sides), the bent-wire retainer on the left
    for s in (1, -1):
        parts.append(P(pin_head((0.108, s * 0.016, -0.0375), "Y", r=0.0019, sign=s), DARK, "body", REAR))
        parts.append(P(pin_head((0.080, s * 0.016, -0.029), "Y", r=0.0021, sign=s), DARK, "body", REAR))
    wire = geo.pipe(geo.fillet([(0.066, 0.0168, -0.033), (0.080, 0.0168, -0.029), (0.108, 0.0168, -0.0375),
                                (0.122, 0.0168, -0.031)], 0.004, 4), radius=0.0006, segments=10, name="Wire")
    parts.append(P(wire, DARK, "body", REAR))
    # grip tang of the rear trunnion under the floor, two rivets
    tang = prism([(-0.002, -0.0405), (0.036, -0.0405), (0.040, -0.0410), (0.040, -0.0418), (-0.002, -0.0418)],
                  -0.0085, 0.0085, bevel=0.0004, seg=2, fillet=0.0015, name="Tang")
    parts.append(P(tang, BLUED, "body", FRONT))
    for x in (0.006, 0.030):
        parts.append(P(dome_rivet((x, 0.0, -0.0417), "Z", d=0.0038, h=0.0006, sign=-1), BLUED, "body", FRONT))
    for x in (0.150, 0.158):
        parts.append(P(dome_rivet((x, 0.0, -0.0414), "Z", d=0.0036, h=0.0006, sign=-1), BLUED, "body", REAR))


# ----------------------------------------------------------------------------------------------- handguards

LHG = (0.250, 0.3815)


def lhg_poly(x, inset=0.0):
    """Lower handguard section: 46 mm at the receiver tapering to 41 mm at the ferrule (the last 15 mm flare out
    3 mm into the front lip), a C rather than a U: 16 mm bottom radii, walls bowed 1.2 mm through the lower half
    and a 2 mm finger swell along the upper third."""
    t = float(np.clip((x - LHG[0]) / (LHG[1] - LHG[0]), 0, 1))
    w = 0.0230 - 0.0025 * t + 0.0015 * float(K.smoothstep(x, 0.356, 0.370))
    wi = w - 0.0062
    zt, z0, zi0 = -0.0040, -0.0420, -0.0310
    corners = [(-w, zt), (-w, z0), (w, z0), (w, zt), (wi, zt), (wi, zi0), (-wi, zi0), (-wi, zt)]
    radii = [0.0016, 0.0160, 0.0160, 0.0016, 0.0010, 0.0080, 0.0080, 0.0010]
    nseg = [4, 12, 12, 4, 3, 8, 8, 3]
    nedge = [7, 6, 7, 2, 6, 4, 6, 2]
    Pp = ccw(rpoly(corners, radii, nseg, nedge))
    outer = np.abs(Pp[:, 0]) > wi + 0.001
    zz = Pp[:, 1]
    bow = 0.0012 * np.clip(1 - ((zz + 0.0255) / 0.0150) ** 2, 0, 1)
    swell = (0.0020 * np.clip(1 - ((zz + 0.0105) / 0.0062) ** 2, 0, 1) ** 1.5
             * float(K.smoothstep(x, 0.256, 0.270) * K.smoothstep(0.366 - x, 0.0, 0.012)))
    Pp[:, 0] += np.sign(Pp[:, 0]) * (bow + swell) * outer
    return offset(Pp, -inset) if inset else Pp


def lower_handguard(parts):
    xs = stations(LHG[0], LHG[1], 0.0040, 0.0016, extra=np.linspace(0.252, 0.272, 6))
    polys = [lhg_poly(x, end_inset(x, LHG[0], LHG[1], 0.0016)) for x in xs]
    lo = loft_polys(polys, xs, "LowerHG")
    slots = []
    for s in (1, -1):
        for x in (0.296, 0.318, 0.340):
            c = prism([(x - 0.0055, -0.0245), (x + 0.0055, -0.0245), (x + 0.0055, -0.0085), (x - 0.0055, -0.0085)],
                      s * 0.0080, s * 0.030, bevel=0, fillet=0.0054, fseg=6)
            slots.append(c)
    cut(lo, *slots)
    K.bevel_where(lo, 0.0010, 1, 40.0, where=lambda c: (np.abs(c[:, 1]) > 0.0150) & (c[:, 2] > -0.0260)
                  & (c[:, 2] < -0.0070) & (c[:, 0] > 0.288) & (c[:, 0] < 0.348))           # 1 mm chamfered vents
    round_edges(lo, 0.0009, 2, 45)
    parts.append(P(lo, WOOD, "body", FURN))
    # steel liner inside the channel (seen through the slots and between the handguards), and the stamped
    # ferrule over the front end (0.8 mm sheet, 1 mm rolled lip at its rear edge): both follow the wood's own
    # contour (index runs of lhg_poly: outer 2..50, channel 56..91)
    def side_normals(Q):
        T = np.gradient(Q, axis=0)
        T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
        return np.stack([T[:, 1], -T[:, 0]], 1)
    xs2 = stations(0.2525, 0.3790, 0.006, 0.0005, 2)
    lp = []
    for x in xs2:
        ch = lhg_poly(x)[56:92]
        n = side_normals(ch)
        lp.append(np.vstack([ch + n * 0.0003, (ch + n * 0.0010)[::-1]]))
    liner = loft_polys([ccw(q) for q in lp], xs2, "LowerLiner")
    parts.append(P(liner, DARK, "body", FRONT))
    fx = np.array([0.3700, 0.3703, 0.3708, 0.3714, 0.3722, 0.3735, 0.3750, 0.3780, 0.3815])
    fp = []
    for x in fx:
        o = lhg_poly(min(x, 0.3814))[2:51]
        n = side_normals(o)
        lip = 0.0010 * float(smoothstep(1 - (x - 0.3700) / 0.0022))
        fp.append(ccw(np.vstack([o + n * (0.0010 + lip), (o + n * (0.0002 + 0.3 * lip))[::-1]])))
    fer = loft_polys(fp, fx, "Ferrule")
    parts.append(P(fer, BLUED, "body", FRONT))
    # retaining band (sheet steel) with its lever, right side
    band_o = [(-0.0245, -0.0115), (-0.0245, -0.0345), (-0.0185, -0.0435), (0.0185, -0.0435), (0.0245, -0.0345),
              (0.0245, -0.0115), (0.0125, 0.0030), (0.0, 0.0122), (-0.0125, 0.0030)]
    band = prism(band_o, 0.3815, 0.3915, axis="X", bevel=0.0007, seg=3, fillet=0.004, name="Band")
    cut(band, lathe([(0.37, 0.0), (0.37, 0.0087), (0.40, 0.0087), (0.40, 0.0)], 48))
    round_edges(band, 0.0004, 2, 50)
    parts.append(P(band, BLUED, "body", FRONT))
    lev = prism([(0.383, -0.020), (0.390, -0.020), (0.392, -0.004), (0.381, -0.004)], -0.0264, -0.0245, bevel=0.0004,
                seg=2, fillet=0.0015, name="BandLever")
    parts.append(P(lev, DARK, "body", FRONT))


UHG = (0.262, 0.372)


def uhg_poly(x, inset=0.0):
    R, zc = 0.0170, 0.0160
    Ri, zci = 0.0113, 0.0178
    zb = 0.0062
    out = [(-0.0113, zb), (-0.0170, zb)]
    side = [(-R, zb + (zc - zb) * f) for f in (0.33, 0.66)]
    arc = [(-R * math.cos(a), zc + R * math.sin(a)) for a in np.linspace(0, math.pi, 49)]
    side2 = [(R, zb + (zc - zb) * f) for f in (0.66, 0.33)]
    inner = [(Ri * math.cos(a), zci + Ri * math.sin(a)) for a in np.linspace(0, math.pi, 25)]
    Pp = np.array(out + side + arc + side2 + [(R, zb), (0.0113, zb)] + [(Ri, zb + 0.004)] + inner + [(-Ri, zb + 0.004)])
    # round the four bottom corners a little: pull them in
    Pp = ccw(Pp)
    return offset(Pp, -inset) if inset else Pp


def upper_handguard(parts):
    xs = stations(UHG[0], UHG[1], 0.0030, 0.0016)
    polys = [uhg_poly(x, end_inset(x, UHG[0], UHG[1], 0.0016)) for x in xs]
    up = loft_polys(polys, xs, "UpperHG")
    vents = [prism([(x0, 0.0175), (x0 + 0.020, 0.0175), (x0 + 0.020, 0.0265), (x0, 0.0265)], -0.03, 0.03, bevel=0,
                   fillet=0.0044, fseg=6) for x0 in (0.287, 0.322)]
    cut(up, *vents)
    K.bevel_where(up, 0.0010, 1, 40.0, where=lambda c: (np.abs(c[:, 1]) > 0.0120) & (c[:, 2] > 0.0160)
                  & (c[:, 2] < 0.0280) & (c[:, 0] > 0.284) & (c[:, 0] < 0.345))
    round_edges(up, 0.0009, 2, 45)
    parts.append(P(up, WOOD, "body", FURN))
    # heat-shield liner: thin steel D under the wood, its edge showing at both ends and through the vents
    xs2 = stations(0.2605, 0.3735, 0.008, 0.0004, 2)
    lp = []
    for x in xs2:
        a = [(0.0109 * math.cos(t), 0.0178 + 0.0109 * math.sin(t)) for t in np.linspace(0, math.pi, 33)]
        b = [(0.0101 * math.cos(t), 0.0178 + 0.0101 * math.sin(t)) for t in np.linspace(math.pi, 0, 33)]
        lp.append(ccw(np.array(a + [(-0.0109, 0.0070), (-0.0101, 0.0070)] + b + [(0.0101, 0.0070), (0.0109, 0.0070)])))
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
    xs = stations(GB[0], GB[1], 0.0025, 0.0015, 5, extra=np.linspace(0.4150, 0.4215, 8))
    polys = []
    for x in xs:
        ins = end_inset(x, GB[0], GB[1], 0.0015)
        rg = 0.0093
        if x > 0.4155:
            rg = 0.0093 * math.sqrt(max(0.0, 1 - ((x - 0.4155) / 0.0062) ** 2))
        ring = soft_union_ring([(0.0, 0.0, 0.0124 - ins), (0.0, 0.019, max(rg - ins, 0.0))], 0.0070, (0.0, 0.006), 80)
        polys.append(ring)
    gb = loft_polys(polys, xs, "GasBlock")
    # tower: horizontal sections from the block up to the drum, 21 -> 14 mm long and 19 -> 14 mm wide
    zs = np.r_[np.linspace(0.0230, 0.0455, 12)]
    secs = []
    for z in zs:
        t = (z - 0.0230) / (0.0455 - 0.0230)
        L0, L1 = 0.0210 + (0.0140 - 0.0210) * t, 0.0
        wy = 0.0095 + (0.0070 - 0.0095) * t
        xc = 0.4090
        secs.append(K.rrect(xc - L0 / 2, xc + L0 / 2, wy, 0.0025, 0.0025, K=240))
    tower = K.loft_z(secs, zs, 64, name="Tower")
    union(gb, tower)
    cut(gb, lathe([(0.38, 0.0), (0.38, 0.0049), (0.44, 0.0049), (0.44, 0.0)], 32))
    round_edges(gb, 0.0006, 2, 50)
    parts.append(P(gb, BLUED, "body", FRONT))
    for s in (1, -1):
        ear = prism([(0.4015, 0.0400), (0.4165, 0.0400), (0.4155, 0.0610), (0.4140, 0.0630), (0.4040, 0.0630),
                     (0.4025, 0.0610)], s * 0.0068, s * 0.0088, bevel=0.0006, seg=3, fillet=0.0010, name="FEar")
        hole = lathe([(-0.01, 0.0), (-0.01, 0.0020), (0.01, 0.0020), (0.01, 0.0)], 24, axis="Y", at=(0.4092, s * 0.0078, 0.0505))
        cut(ear, hole)
        round_edges(ear, 0.0003, 2, 50)
        parts.append(P(ear, DARK, "body", FRONT))
    drum = lathe([(0.0440, 0.0), (0.0440, 0.0040), (0.0475, 0.0040), (0.0475, 0.0)], 32, axis="Z", at=(0.409, 0, 0),
                 fillet=0.0004)
    parts.append(P(drum, DARK, "body", FRONT))
    post = prism([(0.4080, 0.047), (0.4100, 0.047), (0.4100, 0.0555), (0.4080, 0.0555)], -0.0010, 0.0010, bevel=0.0002,
                 seg=1, name="Post")
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

GBACK = K.spline([(0.0300, -0.0360), (0.0290, -0.0400), (0.0230, -0.0600), (0.0175, -0.0800), (0.0112, -0.1000),
                  (0.0035, -0.1200), (-0.0006, -0.1335), (0.0004, -0.1475)], 10)
GZ = (-0.0360, -0.1475)


def grip_front(z):
    lin = 0.0690 + (z + 0.036) * (0.0270 / 0.1115)
    return lin + 0.0030 * math.exp(-((z + 0.0973) / 0.026) ** 2)        # front swell +3 mm at 55 % of the height


def grip_section(z, inset=0.0):
    """Oval grip section (superellipse, 30 x ~42 mm): the back fuller where the palm wraps it, 2 mm narrower at the
    base. Starts at the front centre, counter-clockwise from +Z, 160 points."""
    x0 = float(K.x_of_z(GBACK, z)) + inset
    x1 = grip_front(z) - inset
    w = float(np.interp(z, [-0.1475, -0.120, -0.085, -0.050, -0.036], [0.0140, 0.0144, 0.0150, 0.0150, 0.0146])) - inset
    a, xc = (x1 - x0) / 2, (x0 + x1) / 2
    th = np.linspace(0, 2 * math.pi, 160, endpoint=False)
    c, s_ = np.cos(th), np.sin(th)
    p = 2.35
    xx = xc + a * np.sign(c) * np.abs(c) ** (2 / p)
    full = 1.0 + 0.10 * np.clip(-c, 0, 1) ** 1.5 * float(np.interp(z, [-0.1475, -0.10, -0.06, -0.036], [1.0, 1.0, 0.6, 0.2]))
    yy = w * np.sign(s_) * np.abs(s_) ** (2 / p) * np.minimum(full, 1.0 + 0.10) / (1.0 + 0.05)
    sec = K.poly_section(np.stack([xx, yy], 1), K=480)
    sec.x0, sec.x1 = x0, x1
    return sec


def pistol_grip(parts):
    zs = list(np.arange(GZ[0], GZ[1] + 0.004, -0.0022))
    zs += [GZ[1] + 0.0030, GZ[1] + 0.0018, GZ[1] + 0.0009, GZ[1] + 0.0003, GZ[1]]
    zs = np.array(sorted(set(np.round(zs, 6)), reverse=True))
    secs = []
    for z in zs:
        d = GZ[1] + 0.0030 - z
        ins = 0.0 if d <= 0 else 0.0030 - math.sqrt(max(0.0, 0.0030 ** 2 - d * d))
        secs.append(grip_section(z, ins))
    g = K.loft_z(secs, zs, 80, name="Grip")
    parts.append(P(g, WOOD, "body", FURN))
    # steel base cap and its screw
    c = grip_section(GZ[1], 0.0016)
    zc = [GZ[1] + 0.0004, GZ[1] - 0.0002, GZ[1] - 0.0008, GZ[1] - 0.0010]
    cs = [grip_section(GZ[1], 0.0016 + i) for i in (0.0, 0.0, 0.0003, 0.0009)]
    cap = K.loft_z(cs, zc, 80, name="GripCap")
    parts.append(P(cap, BLUED, "body", FRONT))
    xm = (c.x0 + c.x1) / 2
    parts.append(P(pin_head((xm, 0, GZ[1] - 0.0010), "Z", r=0.0034, h=0.0010, sign=-1, slot=True, seg=32), DARK,
                   "body", FRONT))


# ----------------------------------------------------------------------------------------------- guard, catch, trigger

def guard_profile(rib_sign=1.0):
    """11 mm stamped strip, 1.5 mm sheet: a pressed centre rib 4 mm wide standing 0.8 mm (the sheet follows it),
    both edges rolled into 1.1 mm beads."""
    pts = []
    ys = np.r_[-0.0044, -0.0030, np.linspace(-0.0024, 0.0024, 7), 0.0030, 0.0044]
    rib = lambda y: rib_sign * 0.0008 * float(K.smoothstep(0.0020 - abs(y), 0.0, 0.0008))
    for y in ys:
        pts.append((0.00075 + rib(y), y))
    for a in np.linspace(math.pi / 2, -math.pi / 2, 7)[1:-1]:
        pts.append((0.0011 * math.sin(a) * 0.95, 0.0044 + 0.0011 * math.cos(a)))
    for y in ys[::-1]:
        pts.append((-0.00075 + rib(y), y))
    for a in np.linspace(-math.pi / 2, -3 * math.pi / 2, 7)[1:-1]:
        pts.append((0.0011 * math.sin(a) * -0.95, -0.0044 + 0.0011 * math.cos(a)))
    return pts


def trigger_guard(parts):
    path = geo.fillet([(0.0790, 0.0, -0.04095), (0.0920, 0.0, -0.04095), (0.0870, 0.0, -0.0782), (0.1500, 0.0, -0.0782),
                       (0.1550, 0.0, -0.0505), (0.1560, 0.0, -0.04095), (0.1620, 0.0, -0.04095)], 0.006, 6)
    path = np.array(path)
    # densify the path so the strip bends smoothly
    seg = []
    for a, b in zip(path[:-1], path[1:]):
        n = max(1, int(np.linalg.norm(b - a) / 0.004))
        for k in range(n):
            seg.append(a + (b - a) * k / n)
    seg.append(path[-1])
    tg = geo.sweep(guard_profile(1.0), seg, up=(0, 1, 0), name="Guard")
    fix_normals(tg)
    # which way is the pressed rib? it must stand out of the loop (away from the trigger)
    co, _n = geo.arrays(tg)
    mid = np.abs(co[:, 1]) < 0.0008
    ctr = np.array([0.122, -0.060])
    d_mid = np.linalg.norm(co[mid][:, [0, 2]] - ctr, axis=1).mean()
    d_all = np.linalg.norm(co[np.abs(co[:, 1]) > 0.003][:, [0, 2]] - ctr, axis=1).mean()
    if d_mid < d_all:
        tg = geo.sweep(guard_profile(-1.0), seg, up=(0, 1, 0), name="Guard")
        fix_normals(tg)
    parts.append(P(tg, BLUED, "body", FRONT))
    for x in (0.0820, 0.0880):                      # the rear tab riveted to the receiver floor
        parts.append(P(dome_rivet((x, 0.0, -0.0418), "Z", d=0.0040, h=0.0007, sign=-1), BLUED, "body", FRONT))
    # catch housing: the rear end of the strip widens into a pressed box round the catch pivot
    hs = prism([(0.1500, -0.0410), (0.1650, -0.0410), (0.1650, -0.0470), (0.1620, -0.0505), (0.1530, -0.0505), (0.1500, -0.0470)],
               -0.0080, 0.0080, bevel=0.0010, seg=3, fillet=0.0015, name="CatchHousing")
    cut(hs, box(0.1525, 0.1630, -0.0068, 0.0068, -0.060, -0.0430))
    round_edges(hs, 0.0003, 2, 50)
    parts.append(P(hs, BLUED, "body", FRONT))
    for s in (1, -1):
        parts.append(P(pin_head((0.1575, s * 0.0080, -0.0458), "Y", r=0.0016, h=0.0004, sign=s, seg=16), DARK, "body", FRONT))
    # catch paddle: 22 mm stamped lever with a dished thumb pad facing back
    pad_c = (0.1660, 0.0, -0.0645)
    cp = prism([(0.1560, -0.0440), (0.1600, -0.0440), (0.1625, -0.0540), (0.1680, -0.0610), (0.1640, -0.0650),
                (0.1585, -0.0560)], -0.0058, 0.0058, bevel=0.0005, seg=2, fillet=0.0014, name="Catch")
    dish = lathe([(0.0, 0.0), (0.0, 0.0068), (0.0010, 0.0071), (0.0018, 0.0066), (0.0020, 0.0044), (0.0012, 0.0)], 40,
                 axis="X", fillet=0.0003, name="CatchPad")
    geo.transform(dish, rot=(0, -35, 0))
    geo.transform(dish, loc=pad_c)
    union(cp, dish)
    hollow = geo.sphere(1.0, 32, 16)
    geo.transform(hollow, scale=(0.0016, 0.0062, 0.0062))
    geo.transform(hollow, rot=(0, -35, 0))
    geo.transform(hollow, loc=(pad_c[0] - 0.0011, 0.0, pad_c[2] - 0.0008))
    cut(cp, hollow)
    round_edges(cp, 0.0003, 2, 50)
    parts.append(P(cp, DARK, "body", FRONT))
    # trigger (pivot X 0.108, Z -0.038), curved blade with a rounded face
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
    for s in (1, -1):
        path = [(0.0220, 0.0, -0.0280), (0.0400, 0.0, -0.0300), (0.2360, 0.0, -0.0490)]
        dense = []
        for a, b in zip(path[:-1], path[1:]):
            a, b = np.array(a), np.array(b)
            n = max(1, int(np.linalg.norm(b - a) / 0.004))
            dense += [tuple(a + (b - a) * k / n) for k in range(n)]
        dense.append(path[-1])
        arm = geo.sweep(u_channel(1.0), dense, up=(0, 1, 0), name="StockArm")
        co, _n = geo.arrays(arm)
        if co[:, 1].mean() < 0:                                # web must face +Y before placing
            geo.transform(arm, scale=(1, -1, 1))
        # joggle: the arm steps out 2 mm over the hinge block, rounded ends
        y0 = 0.0180

        def jog(co):
            co[:, 1] = co[:, 1] + y0 + 0.0022 * smoothstep((0.046 - co[:, 0]) / 0.010)
            return co
        K.deform(arm, jog)
        fix_normals(arm)
        if s < 0:
            geo.transform(arm, scale=(1, -1, 1))
            fix_normals(arm)
        round_edges(arm, 0.0003, 2, 50)
        parts.append(P(arm, BLUED, "body", FRONT))
        # forged hinge block (sits in the receiver's pressed recess), big axle pin head, pin at the front end
        hb = prism([(0.0110, -0.0200), (0.0330, -0.0215), (0.0345, -0.0290), (0.0315, -0.0368), (0.0125, -0.0368),
                    (0.0095, -0.0290)], s * 0.0150, s * 0.0188, bevel=0.0010, seg=3, fillet=0.0035, name="HingeBlock")
        parts.append(P(hb, BLUED, "body", REAR))
        parts.append(P(dome_rivet((HINGE[0], s * 0.0228, HINGE[1]), "Y", d=0.0100, h=0.0018, sign=s, seg=40), DARK,
                       "body", REAR))
        parts.append(P(pin_head((0.236, s * 0.0201, -0.0490), "Y", r=0.0030, h=0.0010, sign=s), DARK, "body", FRONT))
    xbar = lathe([(-0.0192, 0.0), (-0.0192, 0.0032), (0.0192, 0.0032), (0.0192, 0.0)], 28, axis="Y", at=(0.236, 0, -0.049),
                 fillet=0.0003)
    parts.append(P(xbar, BLUED, "body", FRONT))
    # shoulder piece folded under the handguard: 2.5 mm sheet curved R 120 mm (convex side up, its crown 2 mm under
    # the handguard), long edges turned down 4 mm, two lightening holes in the rear half, rubber pad inside the
    # front half with its edge showing, hinge lugs up to the cross pin
    X0, X1, R, xm = 0.2340, 0.3370, 0.120, 0.2855
    Z_TOP = -0.0440

    def ztop(x):
        return Z_TOP - (x - xm) ** 2 / (2 * R)
    corners = [(-0.0150, 0.0), (-0.0150, -0.0040), (-0.0126, -0.0040), (-0.0126, -0.0025), (0.0126, -0.0025),
               (0.0126, -0.0040), (0.0150, -0.0040), (0.0150, 0.0)]
    base = ccw(rpoly(corners, [0.0030, 0.0004, 0.0004, 0.0006, 0.0006, 0.0004, 0.0004, 0.0030], [5, 1, 1, 2, 2, 1, 1, 5],
                     [2, 1, 1, 10, 1, 1, 2, 10]))
    xs = stations(X0, X1, 0.004, 0.0025)
    polys = []
    for x in xs:
        ins = end_inset(x, X0, X1, 0.0025)
        q = base.copy()
        q[:, 0] = np.sign(q[:, 0]) * np.maximum(np.abs(q[:, 0]) - ins, 0.0003)
        q[:, 1] += ztop(x)
        polys.append(q)
    bp = loft_polys(polys, xs, "ButtPlate")
    holes = []
    for xc in (0.2480, 0.2650):
        holes.append(prism(rpoly([(xc - 0.0055, -0.0045), (xc + 0.0055, -0.0045), (xc + 0.0055, 0.0045), (xc - 0.0055, 0.0045)],
                                 [0.0040] * 4, [6] * 4, [1] * 4), -0.075, -0.035, axis="Z", bevel=0, name="Hole"))
    cut(bp, *holes)
    for sgn in (1, -1):                             # hinge lugs from the plate's rear end up to the cross pin
        lug = prism([(0.2318, ztop(0.2318) - 0.0020), (0.2440, ztop(0.2440) - 0.0020), (0.2430, -0.0478),
                     (0.2380, -0.0448), (0.2330, -0.0460), (0.2310, -0.0500)], sgn * 0.0128, sgn * 0.0149,
                    bevel=0.0004, seg=2, fillet=0.0012, name="PlateLug")
        cut(lug, lathe([(-0.01, 0.0), (-0.01, 0.0033), (0.01, 0.0033), (0.01, 0.0)], 20, axis="Y", at=(0.236, 0, -0.049)))
        union(bp, fix_normals(lug))
    round_edges(bp, 0.0003, 2, 45)
    parts.append(P(bp, BLUED, "body", FRONT))
    pz = [-0.0055, -0.0050, -0.0040, -0.0026]
    ps = [K.rrect(0.2780 + 0.0006 * (z < -0.0052), 0.3335 - 0.0006 * (z < -0.0052), 0.0122 - 0.0006 * (z < -0.0052),
                  0.0030, 0.0030, K=200) for z in pz]
    pad = K.loft_z(ps, pz, 64, name="Pad")
    K.deform(pad, lambda co: np.c_[co[:, 0], co[:, 1], co[:, 2] + Z_TOP - (co[:, 0] - xm) ** 2 / (2 * R)])
    parts.append(P(pad, POLYMER, "body", FRONT))


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
    # rear sight: base on the cover, leaf with the 4.4 x 4.2 mm notch, protective ears (first-pass profile)
    base = prism([(0.012, 0.028), (0.034, 0.028), (0.034, 0.0375), (0.030, 0.0415), (0.016, 0.0415), (0.012, 0.0375)],
                 -0.0085, 0.0085, bevel=0.0007, seg=2, name="RSBase")
    parts.append(P(base, DARK, "body", REAR))
    leaf = prism([(0.0215, 0.040), (0.0255, 0.040), (0.0255, 0.0555), (0.0215, 0.0555)], -0.0072, 0.0072, bevel=0.0003,
                 seg=2, name="Leaf")
    cut(leaf, box(0.018, 0.030, -0.0022, 0.0022, 0.0513, 0.06))
    round_edges(leaf, 0.00025, 2, 50)
    parts.append(P(leaf, DARK, "body", REAR))
    for s_ in (1, -1):
        ear = prism([(0.016, 0.038), (0.031, 0.038), (0.029, 0.0555), (0.019, 0.0555)], s_ * 0.0076, s_ * 0.0102,
                    bevel=0.0004, seg=2, fillet=0.0015, name="Ear")
        parts.append(P(ear, DARK, "body", REAR))


def rear_trunnion(parts):
    """Forged rear trunnion inside the receiver sheet: it shows 7.5 mm behind the sheet's rear edge, rear face
    domed 1 mm, 3 mm radii at the bottom, 1.5 mm at the top, 0.5 mm chamfers; the stock latch on its left."""
    x0, x1 = -0.0034, 0.0160
    xs = stations(x0, x1, 0.003, 0.0025, 5)
    polys = []
    for x in xs:
        ins = end_inset(x, x0, x1 + 0.01, 0.0025)
        polys.append(offset(ccw(rpoly([(-0.0149, -0.0392), (0.0149, -0.0392), (0.0149, 0.0108), (-0.0149, 0.0108)],
                                      [0.0030, 0.0030, 0.0015, 0.0015], [6, 6, 4, 4], [8, 10, 8, 10])), -ins))
    tr = loft_polys(polys, xs, "RearTrunnion")
    cut(tr, box(0.0034, 0.030, -0.0102, 0.0102, 0.0042, 0.030))          # the carrier's path at full travel
    K.deform(tr, lambda co: np.c_[co[:, 0] - 0.0010 * np.clip(1 - (co[:, 1] / 0.015) ** 2, 0, 1)
                                  * np.clip(1 - ((co[:, 2] + 0.0142) / 0.026) ** 2, 0, 1) * (co[:, 0] < x0 + 0.002),
                                  co[:, 1], co[:, 2]])
    round_edges(tr, 0.0004, 2, 40)
    parts.append(P(tr, BLUED, "body", REAR))
    boss = lathe([(0.0, 0.0), (0.0, 0.0032), (0.0006, 0.0032), (0.0010, 0.0027), (0.0010, 0.0)], 32, axis="Y",
                 at=(-0.0004, 0.0146, -0.0120), fillet=0.0002)
    parts.append(P(boss, BLUED, "body", REAR))
    btn = lathe([(0.0, 0.0), (0.0, 0.0020), (0.0016, 0.0020), (0.0021, 0.0016), (0.0022, 0.0)], 32, axis="Y",
                at=(-0.0004, 0.0148, -0.0120), fillet=0.0002)
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
    # carrier faces other than its right side (the port) are seen only through the left slot
    w[(mid == BRIGHT) & (x < 0.2045) & (nr[:, 1] > -0.5)] = np.minimum(w[(mid == BRIGHT) & (x < 0.2045) & (nr[:, 1] > -0.5)], 0.55)
    # receiver: the rails under the cover, the trunnion top under the sight block, the floor
    rec = (mid == BLUED) & (np.abs(y) < 0.0165)
    w[rec & (nr[:, 2] > 0.7) & (z > 0.0105) & (z < 0.0125)] = 0.3
    w[rec & (nr[:, 2] < -0.7) & (z < -0.0395) & (x > 0.040) & (x < 0.150)] = 0.6
    return w


def chopper_parts():
    parts = []
    chopper_receiver(parts)
    rear_trunnion(parts)
    cover(parts)
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
        extra += list(c + np.array([-2.4, -1.75, -1.5, -1.25, -1.0, -0.6, 0.0, 0.6, 1.0, 1.25, 1.5, 1.75, 2.4]) * 0.001 / arc_len)
    st = np.unique(np.clip(np.concatenate([base, extra, [0.004, 0.012]]), 0, 1))

    def plateau(dist, hw, sh=0.0005):
        """1 on a flat-topped rib of half width hw with sh-wide rounded shoulders, 0 off it."""
        return float(K.smoothstep(hw - dist, -sh / 2, sh / 2))

    def across(d):
        """Depth samples (metres from the centre line, -d back .. +d front): dense at the long rib's shoulders."""
        u = list(np.linspace(-d, d, 25))
        u += [v * 0.001 for v in (-1.75, -1.5, -1.25, -1.0, -0.75, 0.75, 1.0, 1.25, 1.5, 1.75)]
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
        xr0 = max(plateau(abs(s_m - c * arc_len), 0.00125) for c in cross)
        us = across(d)
        pts = []
        for side in (1, -1):
            seq = us if side == 1 else us[::-1]
            for u in seq:
                lng = plateau(abs(u), 0.00125)
                xr = xr0 * plateau(abs(u), d - 0.0060, 0.002)
                y = side * (Wd + 0.0008 * max(lng, xr))
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
        q = Pc + n * (-d - 0.0006)
        sp.append((q[0], 0.0, q[1]))
    seam = K.sweep_var(np.array(sp), lambda i, t: K.superellipse(0.00045, 0.00055, 2.0, 10), name="Seam")
    parts.append(P0(seam, BLUED, None))
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
    union(fp, W.box(-0.0360, -0.0300, -0.0045, 0.0045, -0.0036, 0.0060, bevel=0.0006, seg=2))   # retaining tab
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
