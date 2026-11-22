"""Street section: 20 m of Jamaica Avenue (Hollis, Queens), 22 m wide.

Blender frame: X east along the street, Y north, Z up, origin at the west end on the centre line, z = 0 at the
gutter line. Roadway y -7..7 (two 4.5 m travel lanes, two 2.5 m parking lanes), kerbs 150 mm, sidewalks to +-11.

Assets (all exported with the pivot at their own origin):
    SM_Street_Road_20m          road slab with crown, gutters, patch, lines, tar and crack ribbons, wear masks
    SM_Street_Kerb_4m [_B _Wet] steel-faced concrete kerb; road face at local y = 0 looking -Y, runs +X
    SM_Street_Sidewalk_4m [_B _C _Wet]  concrete flags behind the kerb, local y 0.19..4.0, same pivot as the kerb
    SM_Street_ManholeCover      cast-iron cover in its frame, 0.9 m, flush
    SM_Street_DrainInlet        kerb-side storm drain: frame, grate, basin
    SM_Prop_Hydrant             two-nozzle hydrant, leaking
North side pieces are placed as built at (x, +7); south side pieces are turned 180 degrees and placed at (x + 4, -7).
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix

from mi import bake, export, geo, mat, paths, render, scene

FAMILY = {"name": "street",
          "description": "Jamaica Ave cross-section: road, kerbs, sidewalks, manhole, storm drain, leaking hydrant"}

L = 20.0            # length of the road module (X)
HALF = 7.0          # half width of the roadway
CROWN = 0.045       # height of the centre line above the gutter
GRID = 0.05         # road vertex spacing: wear masks need it
KERB_H = 0.15
KERB_Y = 0.178      # back edge of the kerb concrete
WALK0, WALK1 = 0.19, 4.0   # sidewalk slab, measured from the kerb face
MOD = 4.0           # kerb / sidewalk module length
LANE = 4.5          # travel lane width; the parking lane line sits at |y| = LANE
MANHOLE = (12.6, -1.9)
MANHOLE_R = 0.45
DRAIN = (13.4, 14.6, -7.0, -6.4)       # x0, x1, y0, y1 of the grate frame
PATCH = (6.0, 8.4, -4.0, -2.6)         # utility patch
HYDRANT = (5.0, -7.65)                 # on the south sidewalk, 0.65 m behind the kerb face
YELLOW = (0.50, 0.345, 0.03)
WHITE = (0.60, 0.59, 0.56)


# ------------------------------------------------------------------------------------------------- small helpers

def sstep(a, b, x):
    """numpy smoothstep; a > b gives the falling edge."""
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class Waves:
    """Band-limited noise from plane waves: smooth, deterministic, optionally periodic along x (so the ends of
    a module match). Call it with numpy arrays; values are roughly standard normal."""

    def __init__(self, rng, size, n=28, period_x=None):
        ang = rng.uniform(0, 2 * np.pi, n)
        k = (2 * np.pi / size) * rng.uniform(0.55, 1.7, n)
        self.kx, self.ky = k * np.cos(ang), k * np.sin(ang)
        if period_x:
            q = 2 * np.pi / period_x
            self.kx = np.round(self.kx / q) * q
        self.ph = rng.uniform(0, 2 * np.pi, n)
        self.a = rng.uniform(0.5, 1.0, n)
        self.norm = math.sqrt(float((self.a ** 2).sum()) / 2)

    def __call__(self, x, y):
        x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
        v = np.zeros(np.broadcast(x, y).shape)
        for kx, ky, ph, a in zip(self.kx, self.ky, self.ph, self.a):
            v += a * np.cos(kx * x + ky * y + ph)
        return v / self.norm

    def u(self, x, y):
        """Same field squashed into 0..1."""
        return 0.5 + 0.5 * np.tanh(self(x, y) * 0.75)


def face_centres(ob):
    me = ob.data
    c = np.empty(len(me.polygons) * 3, dtype=np.float32)
    me.polygons.foreach_get("center", c)
    return c.reshape(-1, 3)


def delete_faces(ob, where):
    c = face_centres(ob)
    kill = np.nonzero(where(c[:, 0], c[:, 1], c[:, 2]))[0]
    bm = geo.bm_of(ob)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in kill], context="FACES")
    return geo.bm_to(ob, bm)


# ------------------------------------------------------------------------------------------------------ materials

def materials(ctx):
    """Tiling sets of the street. With --bake they are baked (cached); the materials then read the textures."""
    M = {}
    ts = ctx.tiling_set
    cracked = ts("TS_Asphalt_Cracked", "asphalt", Alligator=1.0, Cracks=0.45, Age=0.8)
    as_kw = dict(dirt_color=(0.105, 0.092, 0.075), leak_color=(0.028, 0.026, 0.024), leak_rough=-0.24,
                 wear_tint=(1.1, 1.1, 1.1), macro=0.16)
    M["asphalt"] = ts("TS_Asphalt_Aged", "asphalt", blend="TS_Asphalt_Cracked", mat_kw=as_kw, Cracks=0.22, Age=0.75)
    M["patch"] = ts("TS_Asphalt_Patch", "asphalt", mat_kw=as_kw, Age=0.15, Aggregate_Scale=150.0, Cracks=0.0,
                    Tint=(0.86, 0.86, 0.88))
    M["yellow"] = ts("TS_RoadPaint_Yellow", "road_paint", blend="TS_Asphalt_Aged", mat_kw=as_kw, Paint_Color=YELLOW,
                     Paint_Wear=0.36)
    M["white"] = ts("TS_RoadPaint_White", "road_paint", blend="TS_Asphalt_Aged", mat_kw=as_kw, Paint_Color=WHITE,
                    Paint_Wear=0.40)
    M["tar"] = ts("TS_Tar_Sealant", "tar", tile_m=1.0, res=1024, mat_kw=dict(macro=0.2, dirt_color=(0.11, 0.1, 0.085)),
                  Dust_Amount=0.35)
    M["crack"] = ts("TS_Asphalt_CrackFill", "tar", tile_m=0.5, res=512, mat_kw=dict(macro=0.0), Dust_Amount=0.1,
                    Matte=1.0)
    M["concrete"] = ts("TS_Concrete_Sidewalk", "concrete", mat_kw=dict(
        dirt_color=(0.125, 0.112, 0.095), wear_tint=(1.07, 1.06, 1.04), wear_rough=-0.1, leak_color=(0.20, 0.105, 0.045),
        macro=0.10), Gum=0.55, Stains=0.4, Broom=0.6, Cracks=0.12, Aggregate=0.25)
    M["steel"] = ts("TS_Steel_Rusted", "steel", tile_m=1.0, res=1024, alpha="wet", mat_kw=dict(
        wear_tint=(1.9, 1.75, 1.6), wear_rough=-0.3, dirt_color=(0.07, 0.062, 0.052), macro=0.2, porosity=0.25),
        Rust=0.72, Mill_Scale=0.35, Scratches=0.5)
    return M


# ------------------------------------------------------------------------------------------------------------ road

class RoadShape:
    """Height of the road surface and everything that depends on position. One instance per build."""

    def __init__(self, rng):
        self.settle = Waves(rng, 6.0, period_x=L)
        self.fine = Waves(rng, 1.4, period_x=L)
        mx, my = MANHOLE
        self.z_mh = CROWN * (1 - (my / HALF) ** 2) - 0.002
        self.z_dr = -0.007 - 0.016

    def base(self, X, Y):
        y = np.abs(Y)
        z = CROWN * (1 - (y / HALF) ** 2)
        z += 0.0030 * self.settle(X, Y) + 0.0009 * self.fine(X, Y)
        for yc in (1.35, 3.15):                                   # ruts in the wheel paths
            z -= 0.0035 * np.exp(-((y - yc) / 0.32) ** 2)
        z -= 0.007 * sstep(6.45, 6.95, y)                         # gutter trough
        return z

    def __call__(self, X, Y):
        X, Y = np.asarray(X, dtype=np.float64), np.asarray(Y, dtype=np.float64)
        z = self.base(X, Y)
        # the patch has settled a few millimetres and is slightly dished
        px0, px1, py0, py1 = PATCH
        inside = sstep(0.0, 0.03, np.minimum.reduce([X - px0, px1 - X, Y - py0, py1 - Y]))
        z += inside * (-0.0035 + 0.0015 * np.sin((X - px0) / (px1 - px0) * np.pi))
        # collar around the manhole frame
        d = np.hypot(X - MANHOLE[0], Y - MANHOLE[1]) - MANHOLE_R
        w = sstep(0.35, 0.0, d)
        z = z * (1 - w) + self.z_mh * w
        # dished apron of the storm drain
        x0, x1, y0, y1 = DRAIN
        d = np.hypot(np.maximum.reduce([x0 - X, X - x1, np.zeros_like(X)]), np.maximum(Y - y1, 0))
        w = sstep(0.5, 0.0, d)
        z = z * (1 - w) + self.z_dr * w
        return z


def crack_path(rng, start, end, wander=0.25, step=0.12, kinks=5):
    """Wandering polyline from start to end: long gentle bends plus a few sharp kinks, like a real crack."""
    a, b = np.array(start, dtype=float), np.array(end, dtype=float)
    n = max(8, int(np.linalg.norm(b - a) / step))
    t = np.linspace(0, 1, n)
    d = b - a
    nrm = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-9)
    off = np.zeros(n)
    for k, amp in ((1.5, 1.0), (3.7, 0.5), (8.3, 0.22)):
        off += amp * np.sin(t * np.pi * k * rng.uniform(0.7, 1.3) + rng.uniform(0, 6.28))
    off += np.cumsum(rng.normal(0, 0.035, n))
    for _ in range(kinks):
        i = rng.integers(2, n - 2)
        off[i:] += rng.normal(0, 0.12)
    off *= np.sin(t * np.pi) ** 0.5 * wander
    return (a[None, :] + t[:, None] * d[None, :] + off[:, None] * nrm[None, :]).tolist()


def build_road(ctx, M):
    rng = ctx.rng("road")
    shape = RoadShape(rng)
    xs = np.linspace(0.0, L, int(round(L / GRID)) + 1)
    ys = np.linspace(-HALF, HALF, int(round(2 * HALF / GRID)) + 1)
    road = geo.heightfield(xs, ys, shape, name="SM_Street_Road_20m", tile_m=2.0)
    # openings: the storm drain is a notch on grid lines, the manhole a clean circle
    x0, x1, y0, y1 = DRAIN
    delete_faces(road, lambda x, y, z: (x > x0) & (x < x1) & (y > y0) & (y < y1))
    ring = [(MANHOLE[0] + MANHOLE_R * math.cos(a), MANHOLE[1] + MANHOLE_R * math.sin(a))
            for a in np.linspace(0, 2 * np.pi, 72, endpoint=False)]
    geo.cut_hole(road, ring, z=shape.z_mh)
    geo.smooth_by_angle(road, 60)
    geo.uv_world_box(road, 2.0)
    # ---- slots by position
    geo.assign(road, M["asphalt"])
    px0, px1, py0, py1 = PATCH
    geo.assign(road, M["patch"], lambda x, y, z: (x > px0) & (x < px1) & (y > py0) & (y < py1))
    geo.assign(road, M["yellow"], lambda x, y, z: (np.abs(y) > 0.05) & (np.abs(y) < 0.15))
    geo.assign(road, M["white"], lambda x, y, z: (np.abs(np.abs(y) - LANE) < 0.05))
    paint_road(ctx, road, shape, rng)
    # ---- ribbons: tar-sealed cracks, the tar band round the patch, open cracks
    parts = [road]
    tar_paths = [crack_path(rng, (0.6, -2.05), (5.6, -2.45), 0.22), crack_path(rng, (8.9, -2.3), (19.3, -1.25), 0.3),
                 crack_path(rng, (15.6, -6.6), (15.1, 0.02), 0.25), crack_path(rng, (15.2, 0.25), (16.4, 6.5), 0.3),
                 crack_path(rng, (2.9, 0.3), (9.8, 2.9), 0.35), crack_path(rng, (10.9, 2.95), (11.9, 6.6), 0.2),
                 crack_path(rng, (3.2, -6.5), (3.9, -4.2), 0.12)]
    for i, pth in enumerate(tar_paths):
        rb = geo.ribbon(pth, width=0.045 * rng.uniform(0.85, 1.25), z=shape, lift=0.0012, name="tar%d" % i, width_jitter=0.45,
                        wander=0.004, seed=i, profile="dome", crown=0.0012, taper=0.05, step=0.04, tile_m=1.0)
        rb.data.materials.append(M["tar"])
        geo.ensure_wear(rb)
        geo.paint(rb, "R", lambda x, y, z: 0.25 + 0.5 * sstep(0.9, 0.0, HALF - np.abs(y)), "set")
        parts.append(rb)
    m = 0.012
    loop = [(px0 - m, py0 - m), (px1 + m, py0 - m), (px1 + m, py1 + m), (px0 - m, py1 + m), (px0 - m, py0 - m)]
    for i in range(4):
        a, b = loop[i], loop[i + 1]
        rb = geo.ribbon([a, b], width=0.05, z=shape.base, lift=0.0012, name="seam%d" % i, width_jitter=0.5, wander=0.006,
                        seed=20 + i, profile="dome", crown=0.001, taper=0.0, step=0.04, tile_m=1.0)
        rb.data.materials.append(M["tar"])
        geo.ensure_wear(rb)
        geo.paint(rb, "R", 0.3, "set")
        parts.append(rb)
    crack_paths = [crack_path(rng, (0.2, 2.4), (6.9, 2.05), 0.3, 0.06, 9), crack_path(rng, (9.2, -5.6), (12.6, -4.6), 0.2, 0.06, 7),
                   crack_path(rng, (16.9, -4.9), (19.8, -5.5), 0.18, 0.06, 6), crack_path(rng, (13.2, 3.9), (19.7, 4.25), 0.3, 0.06, 9),
                   crack_path(rng, (1.1, -5.9), (2.6, -3.7), 0.15, 0.06, 5), crack_path(rng, (17.3, -1.0), (18.4, 1.9), 0.2, 0.06, 6),
                   crack_path(rng, (12.95, -1.6), (14.6, -0.7), 0.1, 0.05, 4), crack_path(rng, (12.3, -2.25), (11.2, -3.6), 0.12, 0.05, 4)]
    for i, pth in enumerate(crack_paths):
        rb = geo.ribbon(pth, width=0.011 * rng.uniform(0.7, 1.5), z=shape, lift=0.0006, name="crack%d" % i, width_jitter=0.9,
                        wander=0.0, seed=40 + i, profile="vee", crown=0.0004, taper=0.2, step=0.02, tile_m=0.5)
        rb.data.materials.append(M["crack"])
        geo.ensure_wear(rb)
        geo.paint(rb, "R", 0.5, "set")
        parts.append(rb)
    road = geo.join(parts, "SM_Street_Road_20m", ctx.col)
    geo.smooth_by_angle(road, 60)
    ctx.asset(road, collision="complex", notes=(
        "Road slab 20 x 14 m with a %.0f mm crown, ruts, gutter troughs, a manhole opening (r 0.45 m at %s) and a storm "
        "drain notch (%s). Slots: aged asphalt (G blends to TS_Asphalt_Cracked), the utility patch, yellow and white "
        "road paint (G blends to TS_Asphalt_Aged: worn paint), raised tar bands and dark crack ribbons lying 0.6-1.2 mm "
        "above the surface. Wet gutter on the south side from the hydrant to the drain is in vertex alpha. Ends match "
        "themselves: tile end to end along X. Collision: use a flat box at z = 0 for gameplay (crown is cosmetic)."
        % (CROWN * 1000, MANHOLE, DRAIN)), pivot="west end on the centre line, z = 0 at the gutter line; runs +X",
        expect_size=(L, 2 * HALF, None))
    return road, shape


def paint_road(ctx, road, shape, rng):
    """Wear masks of the road, from causes: where tyres run, where engines drip, where water and dirt collect."""
    me = road.data
    co, _ = geo.arrays(road)
    X, Y = co[:, 0], co[:, 1]
    y = np.abs(Y)
    blot = Waves(rng, 1.6, period_x=L)
    mid = Waves(rng, 0.45, period_x=L)
    fine = Waves(rng, 0.16, period_x=L)
    b, m_, f_ = blot.u(X, Y), mid.u(X, Y), fine.u(X, Y)
    d_kerb = HALF - y
    d_ring = np.abs(np.hypot(X - MANHOLE[0], Y - MANHOLE[1]) - MANHOLE_R)
    x0, x1, y0, y1 = DRAIN
    d_drain = np.hypot(np.maximum.reduce([x0 - X, X - x1, np.zeros_like(X)]), np.maximum(Y - y1, 0))
    south = Y < 0
    # R: fines and grime. Thick in the gutter, lighter across the parking lane, round the frames
    gut = sstep(0.95, 0.0, d_kerb)
    R = 0.07 + 0.62 * gut ** 1.4 * (0.6 + 0.6 * m_) + 0.16 * sstep(LANE - 0.3, LANE + 0.6, y) * (0.5 + b)
    R += 0.10 * (b - 0.5) + 0.5 * np.exp(-(d_ring / 0.10) ** 2) + 0.55 * np.exp(-d_drain / 0.35) * south
    # G: traffic. Wheel paths polish (below 0.5), a few fatigue areas crack (above 0.5)
    G = np.zeros_like(X)
    for yc in (1.35, 3.15):
        G += 0.36 * np.exp(-((y - yc) / 0.34) ** 2) * (0.75 + 0.5 * b)
    for (cx, cy, rx, ry, amp) in ((16.2, -3.15, 1.3, 0.5, 1.0), (3.4, 1.35, 1.0, 0.45, 0.95), (9.6, 3.2, 1.5, 0.5, 0.9),
                                  (18.6, 1.4, 0.8, 0.4, 0.85), (1.2, -3.1, 0.9, 0.4, 0.8)):
        G = np.maximum(G, amp * np.exp(-((X - cx) / rx) ** 2 - ((Y - cy) / ry) ** 2) * (0.75 + 0.5 * m_))
    G = np.maximum(G, 0.8 * np.exp(-(d_ring / 0.09) ** 2) * (0.6 + 0.6 * f_))
    # B: oil. A faint strip down each lane centre, drip clusters where parked engines sit
    B = 0.20 * np.exp(-((y - 2.25) / 0.36) ** 2) * (0.5 + 0.9 * b)
    for side in (-1, 1):
        for cx in np.arange(1.9, L, 5.6) + rng.uniform(-0.5, 0.5):
            cy = side * (5.72 + rng.uniform(-0.2, 0.2))
            for _ in range(int(rng.integers(5, 12))):
                ox, oy = rng.normal(0, 0.28), rng.normal(0, 0.2)
                r = rng.uniform(0.04, 0.2)
                B = np.maximum(B, rng.uniform(0.5, 1.0) * np.exp(-(((X - cx - ox) ** 2 + (Y - cy - oy) ** 2) / r ** 2)))
    # A: water from the hydrant runs off the kerb at x = 5 and along the south gutter into the drain
    dk = Y + HALF                                           # distance from the south kerb face
    along = sstep(HYDRANT[0] - 0.9, HYDRANT[0] - 0.3, X) * sstep(x1 + 0.05, x1 - 0.5, X)
    width = 0.34 + 0.20 * m_ + 0.75 * np.exp(-((X - HYDRANT[0] - 0.25) / 0.75) ** 2) + 0.25 * sstep(x0 - 1.5, x0, X)
    A = sstep(width, width * 0.25, dk) * along
    A = np.clip(A * (0.82 + 0.3 * f_), 0, 1)
    A = np.maximum(A, 0.9 * np.exp(-(d_drain / 0.16) ** 2) * south)
    geo.set_wear(road, np.stack([R, G, B, A], axis=1))
    # the painted lines wear from their edges inward and where wheels cross them: corners of the paint faces only
    mi_ = np.empty(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("material_index", mi_)
    names = [m.name for m in me.materials]
    long_w = Waves(rng, 2.5, period_x=L)

    def paint_wear(x, y_, z):
        ya = np.abs(y_)
        centre = np.where(ya < 1.0, 0.10, LANE)
        edge = np.abs(ya - centre) / 0.05                    # 0 on the line axis, 1 on its edge
        base = np.where(ya < 1.0, 0.16, 0.36)
        return np.clip(base + 0.30 * edge ** 2 + 0.26 * long_w(x, y_ * 0.2) + 0.10 * (fine.u(x, y_) - 0.5), 0, 1)
    for nm in ("MI_RoadPaint_Yellow", "MI_RoadPaint_White"):
        if nm in names:
            geo.paint(road, "G", paint_wear, "set", faces=names.index(nm))
    if "MI_Asphalt_Patch" in names:
        geo.paint(road, "G", lambda x, y_, z: 0.05 + 0.0 * x, "set", faces=names.index("MI_Asphalt_Patch"))
        geo.paint(road, "R", lambda x, y_, z: 0.04 + 0.05 * blot.u(x, y_), "set", faces=names.index("MI_Asphalt_Patch"))


# ---------------------------------------------------------------------------------------------------------- kerb

def kerb_profile():
    """(y, z, slot) of the kerb's visible skin from the gutter up the steel face, over the rolled corner, along the
    top leg of the angle, the concrete and the joint filler."""
    r = 0.016
    pts = [(0.0, -0.035, "steel"), (0.0, 0.0, "steel"), (0.0, 0.03, "steel"), (0.0, 0.065, "steel"), (0.0, 0.10, "steel"),
           (0.0, KERB_H - r, "steel")]
    for k in range(1, 6):
        a = math.pi - k * (math.pi / 2) / 5
        pts.append((r + r * math.cos(a), KERB_H - r + r * math.sin(a), "steel"))
    pts += [(0.030, KERB_H, "steel"), (0.045, KERB_H, "steel"), (0.0585, KERB_H, "steel"), (0.0600, KERB_H - 0.0006, "steel"),
            (0.0606, KERB_H - 0.0030, "steel"), (0.0624, KERB_H - 0.0030, "concrete"), (0.0632, KERB_H - 0.0006, "concrete"),
            (0.066, KERB_H, "concrete"), (0.085, KERB_H, "concrete"), (0.11, KERB_H, "concrete"), (0.14, KERB_H, "concrete"),
            (0.165, KERB_H, "concrete"), (0.1735, KERB_H - 0.0008, "concrete"), (0.1770, KERB_H - 0.0030, "concrete"),
            (0.1780, KERB_H - 0.0050, "tar"), (0.1815, KERB_H - 0.0042, "tar"), (0.1865, KERB_H - 0.0042, "tar"),
            (WALK0, KERB_H - 0.0050, "tar")]
    return pts


def build_kerb(ctx, M, variant=""):
    name = "SM_Street_Kerb_4m" + ("_" + variant if variant else "")
    rng = ctx.rng("kerb", variant)
    prof = kerb_profile()
    xs = list(np.arange(0.0, MOD + 1e-6, 0.04))
    j = MOD / 2 + (0.6 if variant == "B" else 0.0)            # butt joint of the steel facing
    xs = sorted(set([round(v, 5) for v in xs if abs(v - j) > 0.012] + [j - 0.008, j - 0.0032, j - 0.003, j + 0.003, j + 0.0032, j + 0.008]))
    xs = np.array(xs)
    nx, npf = len(xs), len(prof)
    py = np.array([p[0] for p in prof])
    pz = np.array([p[1] for p in prof])
    slot = [p[2] for p in prof]
    X = np.repeat(xs[:, None], npf, axis=1)
    Yv = np.repeat(py[None, :], nx, axis=0).copy()
    Zv = np.repeat(pz[None, :], nx, axis=0).copy()
    dent = Waves(rng, 0.9, period_x=MOD)
    chip = Waves(rng, 0.11, period_x=MOD)
    chip2 = Waves(rng, 0.35, period_x=MOD)
    is_steel = np.array([s == "steel" for s in slot])
    is_conc = np.array([s == "concrete" for s in slot])
    # the facing is never straight: plough hits push it in, frost pushes it out
    face = (py < 0.002) & is_steel
    Yv[:, face] += 0.0022 * dent(X[:, face], Zv[:, face] * 3)
    # butt joint: a 6 mm gap, 4 mm deep
    gap = (np.abs(xs - j) < 0.0031)[:, None] & is_steel[None, :]
    Yv = np.where(gap & (py[None, :] < 0.002), Yv + 0.004, Yv)
    Zv = np.where(gap & (py[None, :] >= 0.002), Zv - 0.004, Zv)
    # concrete: spalled along the steel and at the back arris, broom-rough on top
    for k in np.nonzero(is_conc)[0]:
        near_edge = math.exp(-((py[k] - 0.064) / 0.012) ** 2) + 0.7 * math.exp(-((py[k] - 0.176) / 0.008) ** 2)
        c = np.clip(chip(xs, xs * 0 + py[k] * 3) * 0.6 + chip2(xs, xs * 0) * 0.7 - 0.75, 0, None)
        Zv[:, k] -= c * 0.011 * near_edge + 0.0004 * (chip.u(xs, xs * 0 + py[k] * 40) - 0.5) * 2
    verts = np.stack([X, Yv, Zv], axis=-1).reshape(-1, 3)
    i = np.arange(nx - 1)[:, None] * npf
    k = np.arange(npf - 1)[None, :]
    faces = np.stack([i + k, i + k + npf, i + k + npf + 1, i + k + 1], axis=-1).reshape(-1, 4)
    ob = geo.from_arrays(name, verts, faces, ctx.col, smooth=50)
    geo.uv_world_box(ob, 2.0)
    # slots: a face takes the slot of its lower profile point
    fslot = np.tile(np.array([slot[q] for q in range(npf - 1)]), nx - 1)
    geo.assign(ob, M["steel"], fslot == "steel")
    geo.assign(ob, M["concrete"], fslot == "concrete")
    geo.assign(ob, M["tar"], fslot == "tar")
    # ---- masks
    co, _ = geo.arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    st = np.tile(is_steel, nx)
    blot = Waves(rng, 0.7, period_x=MOD)
    mid = Waves(rng, 0.18, period_x=MOD)
    bu, mu = blot.u(x, z * 2), mid.u(x, z * 3)
    corner = np.exp(-(((y - 0.012) / 0.02) ** 2 + ((z - KERB_H + 0.012) / 0.022) ** 2))
    Rs = np.clip(0.25 + 0.75 * sstep(0.07, -0.01, z) + 0.2 * (bu - 0.5), 0, 1)             # gutter line grime
    Gs = np.clip(corner * (0.35 + 0.75 * bu) + 0.25 * sstep(0.03, 0.0, np.abs(z - 0.085)) * mu, 0, 1)   # tyre scuffs
    seam = np.exp(-((y - 0.061) / 0.004) ** 2)
    Rc = np.clip(0.32 + 0.3 * (bu - 0.5) + 0.7 * seam + 0.5 * sstep(0.165, 0.178, y), 0, 1)
    Gc = np.clip(0.55 * np.exp(-((y - 0.068) / 0.012) ** 2) * mu + 0.25 * mu * bu, 0, 1)
    streaks = np.zeros_like(x)
    for _ in range(int(rng.integers(4, 9))):
        sx, sw, sl = rng.uniform(0, MOD), rng.uniform(0.008, 0.03), rng.uniform(0.05, 0.14)
        streaks = np.maximum(streaks, np.exp(-((x - sx) / sw) ** 2) * sstep(KERB_H - sl, KERB_H - 0.01, z) * (y < 0.01))
    R = np.where(st, Rs, Rc)
    G = np.where(st, Gs, Gc)
    B = np.where(st, streaks * 0.8, 0.25 * np.clip(mu - 0.6, 0, 1) * 2)
    A = np.zeros_like(x)
    if variant == "Wet":
        # water comes over the kerb in a 0.5 m band, sheets down the face and keeps the foot of the face wet
        hx = MOD - 1.0                                                   # hydrant at local x = 3 (see layout)
        band = np.exp(-((x - hx) / 0.26) ** 2) * (0.8 + 0.3 * mu)
        foot = sstep(0.05, 0.0, z) * sstep(hx + 0.7, hx + 0.2, x) * 0.9  # downstream (-x is east once turned)
        A = np.clip(np.maximum(band, foot), 0, 1)
        B = np.maximum(B, 0.5 * band * (y < 0.01))
    geo.set_wear(ob, np.stack([R, G, B, A], axis=1))
    ctx.asset(ob, collision="box", cover_height=None, notes=(
        "Steel-faced concrete kerb, 150 mm reveal. Road face at local y = 0 looking -Y, body toward +Y, top at "
        "z = 0.15, skin only (open ends and bottom: tile end to end, bury 35 mm). Includes the bitumen joint filler up to "
        "y = 0.19 where the sidewalk slab starts. North side: place at (x, +7, 0). South side: rotate 180 deg about Z and "
        "place at (x + 4, -7, 0). Vertex alpha = wetness (both slots)."),
        pivot="west end, on the gutter line at the foot of the road face (z = 0); runs +X",
        expect_size=(MOD, WALK0, None))
    return ob


# ------------------------------------------------------------------------------------------------------ sidewalk

def build_sidewalk(ctx, M, variant=""):
    name = "SM_Street_Sidewalk_4m" + ("_" + variant if variant else "")
    rng = ctx.rng("walk", variant)
    jx = [0.0, MOD / 3, 2 * MOD / 3, MOD]
    jy = [1.0, 2.5]                                   # rows: kerb strip 0.19..1.0, then two 1.5 m rows
    prof = [0.0, 0.0025, 0.005, 0.008, 0.012, 0.018]

    def axis(lo, hi, joints, step):
        v = set(np.round(np.arange(lo, hi + 1e-6, step), 5).tolist())
        v |= {lo, hi}
        for jv in joints:
            for p in prof:
                for s in (-1, 1):
                    q = round(jv + s * p, 5)
                    if lo <= q <= hi:
                        v.add(q)
        v = sorted(v)
        out = [v[0]]
        for q in v[1:]:
            if q - out[-1] > 0.0012:
                out.append(q)
        out[-1] = hi
        return np.array(out)
    xs = axis(0.0, MOD, jx, 0.03)
    ys = axis(WALK0, WALK1, jy + [WALK0, WALK1], 0.03)
    ni, nj = 3, 3
    off = rng.uniform(-0.0016, 0.0016, (ni, nj))
    tx = rng.uniform(-0.0011, 0.0011, (ni, nj))
    ty = rng.uniform(-0.0011, 0.0011, (ni, nj))
    grime = rng.uniform(0.14, 0.50, (ni, nj))
    new_flag = None
    if variant == "C":
        new_flag = (1, 1)
        grime[new_flag] = 0.0
        off[new_flag] = 0.0022
    if variant == "B":
        grime[0, 2] = 0.62
    und = Waves(rng, 1.1)
    ybounds = [WALK0, 1.0, 2.5, WALK1]

    def flag_of(X, Y):
        I = np.clip((X / (MOD / 3)).astype(int), 0, ni - 1)
        J = np.clip(np.searchsorted(np.array(jy), Y, side="right"), 0, nj - 1)
        return I, J

    def joint_dist(X, Y):
        dx = np.min(np.abs(X[..., None] - np.array(jx)), axis=-1)
        dy = np.min(np.abs(Y[..., None] - np.array(jy + [WALK0 - 0.004, WALK1])), axis=-1)
        return np.minimum(dx, dy)

    def zfun(X, Y):
        X, Y = np.asarray(X, dtype=np.float64), np.asarray(Y, dtype=np.float64)
        I, J = flag_of(X, Y)
        cx = (I + 0.5) * MOD / 3
        cy = np.array([(ybounds[k] + ybounds[k + 1]) / 2 for k in range(nj)])[J]
        fade = sstep(0.0, 0.03, np.minimum(X, MOD - X))            # module ends stay put so variants butt together
        z = KERB_H + fade * (off[I, J] + tx[I, J] * (X - cx) + ty[I, J] * (Y - cy)) + 0.0005 * und(X, Y) * fade
        d = joint_dist(X, Y)
        return z - 0.0065 * sstep(0.0085, 0.0022, d) - 0.0008 * sstep(0.02, 0.0085, d)
    ob = geo.heightfield(xs, ys, zfun, name=name, tile_m=2.0)
    scene.move_to(ob, ctx.col)
    geo.assign(ob, M["concrete"])
    geo.smooth_by_angle(ob, 60)
    # ---- masks
    co, _ = geo.arrays(ob)
    X, Y = co[:, 0], co[:, 1]
    I, J = flag_of(X, Y)
    blot = Waves(rng, 0.9)
    mid = Waves(rng, 0.3)
    fine = Waves(rng, 0.08)
    b, m_, f_ = blot.u(X, Y), mid.u(X, Y), fine.u(X, Y)
    d = joint_dist(X, Y)
    R = grime[I, J] * (0.75 + 0.5 * b) + 0.75 * sstep(0.022, 0.004, d) + 0.16 * sstep(0.09, 0.0, d) * m_
    R += 0.30 * sstep(0.85, WALK0, Y) * (0.5 + m_) + 0.34 * sstep(3.45, 3.98, Y) * (0.5 + m_)
    for _ in range(int(rng.integers(4, 9))):                           # old spills and drips
        cx, cy, r = rng.uniform(0, MOD), rng.uniform(WALK0, WALK1), rng.uniform(0.06, 0.3)
        R = np.maximum(R, rng.uniform(0.4, 0.85) * np.exp(-(((X - cx) ** 2 + (Y - cy) ** 2) / r ** 2)) * (0.6 + 0.6 * f_))
    G = 0.24 * np.exp(-((Y - 2.35) / 0.95) ** 2) * (0.6 + 0.7 * b) + 0.5 * sstep(0.03, 0.008, d) * sstep(0.6, 0.85, m_)
    Bm = np.zeros_like(X)
    for _ in range(int(rng.integers(1, 4))):                           # rust-brown stains
        cx, cy, r = rng.uniform(0.2, MOD - 0.2), rng.uniform(0.4, 3.8), rng.uniform(0.05, 0.16)
        Bm = np.maximum(Bm, rng.uniform(0.4, 0.9) * np.exp(-(((X - cx) ** 2 + ((Y - cy) / 1.8) ** 2) / r ** 2)))
    A = np.zeros_like(X)
    if new_flag is not None:
        sel = (I == new_flag[0]) & (J == new_flag[1]) & (d > 0.012)
        R = np.where(sel, 0.02 + 0.03 * b, R)
        G = np.where(sel, 0.0, G)
    if variant == "Wet":
        hx, hy = MOD - 1.0, -HYDRANT[1] - HALF                         # hydrant in module coordinates: (3.0, 0.65)
        r = np.hypot(X - hx, Y - hy)
        pool = sstep(0.55, 0.16, r * (1.0 + 0.35 * (m_ - 0.5)))
        run = sstep(0.34, 0.08, np.abs(X - hx + 0.12 * (m_ - 0.5)) * (1.0 + 0.6 * (Y - WALK0))) * (Y < hy + 0.1)
        A = np.clip(np.maximum(pool, run) * (0.85 + 0.3 * f_), 0, 1)
        Bm = np.maximum(Bm, 0.75 * sstep(0.34, 0.1, r) * (0.6 + 0.6 * m_))     # rust ring round the hydrant
        Bm = np.maximum(Bm, 0.4 * run * m_)
    geo.set_wear(ob, np.stack([np.clip(R, 0, 1), np.clip(G, 0, 1), Bm, A], axis=1))
    # ---- cracks on some flags: thin dark ribbons lying on the surface
    parts = [ob]
    cracks = {"": [((1.6, 2.5), (2.45, 3.99), 0.10)], "B": [((0.0, 3.1), (1.3, 2.52), 0.12), ((2.7, 0.3), (3.6, 0.98), 0.08)],
              "C": [((2.68, 1.4), (3.99, 2.2), 0.14)], "Wet": [((0.6, 1.02), (1.32, 2.2), 0.10)]}[variant]
    for k, (a, e, wd) in enumerate(cracks):
        rb = geo.ribbon(crack_path(rng, a, e, wd, 0.04, 6), width=0.006 * rng.uniform(0.8, 1.5), z=zfun, lift=0.0005,
                        name="crack", width_jitter=0.9, seed=k + 3, profile="vee", crown=0.0003, taper=0.25, step=0.015, tile_m=0.5)
        rb.data.materials.append(M["crack"])
        geo.ensure_wear(rb)
        geo.paint(rb, "R", 0.6, "set")
        parts.append(rb)
    ob = geo.join(parts, name, ctx.col)
    ctx.asset(ob, collision="box", notes=(
        "Concrete sidewalk, 4 m long, from the kerb joint (local y = 0.19) to the building line (y = 4.0), top at "
        "z = 0.15. Nine flags (1.33 m long; rows 0.81, 1.5 and 1.5 m deep) with tooled joints modelled 6.5 mm deep; "
        "flags sit up to 1.6 mm out of level. Same pivot as SM_Street_Kerb_4m, so both take the same transform. "
        "Variants differ in grime, cracks and stains%s. Vertex alpha = wetness."
        % {"": "", "B": "", "C": "; C has one newly poured flag", "Wet": "; Wet has the hydrant pool at local (3.0, 0.65)"}[variant]),
        pivot="west end, on the gutter line of its kerb (z = 0); slab from y = 0.19 to 4.0; runs +X",
        expect_size=(MOD, WALK1 - WALK0, None))
    return ob


# ------------------------------------------------------------------------------------------------- manhole cover

def build_manhole(ctx):
    name = "SM_Street_ManholeCover"
    rng = ctx.rng("manhole")
    R_COVER = 0.386
    parts = []
    # frame: a ring flush with the road, bevelled, with the seat step
    frame = geo.revolve(geo.fillet([(0.45, -0.06), (0.45, -0.003), (0.447, 0.0), (0.394, 0.0), (0.391, -0.0015), (0.391, -0.045)],
                                   0.002, 2), 96, name="frame")
    parts.append(frame)
    # cover plate: disc with a rim bead, a lettering band between two beads, and a recessed field
    prof = [(0.0, -0.004), (0.250, -0.004), (0.252, -0.001), (0.266, -0.001), (0.268, -0.004), (0.340, -0.004),
            (0.342, -0.001), (0.352, -0.001), (0.354, -0.004), (0.362, -0.004), (0.364, -0.0005), (0.383, -0.0005),
            (R_COVER, -0.0035), (R_COVER, -0.03), (0.0, -0.03)]
    plate = geo.revolve(geo.fillet(prof[::-1], 0.0007, 1), 96, name="plate")     # counter-clockwise: bottom out, top in
    for sx in (-1, 1):                                                 # two pick holes through the plate
        cut = geo.box((0.045, 0.017, 0.08), bevel=0.006, segments=3, name="cut")
        geo.transform(cut, loc=(sx * 0.305, 0.0, -0.05))
        geo.boolean(plate, cut, "DIFFERENCE")
    geo.smooth_by_angle(plate, 30)
    parts.append(plate)
    # studs: waffle of square bosses in the field, worn round
    stud = geo.box((0.019, 0.019, 0.0034), bevel=0.0016, segments=1, name="stud")
    pitch = 0.031
    mats = []
    for i in range(-9, 10):
        for j in range(-9, 10):
            x, y = i * pitch, j * pitch
            if math.hypot(x, y) < 0.236 and not (abs(i) <= 1 and abs(j) <= 1):
                mats.append(Matrix.Translation((x, y, -0.0042)) @ Matrix.Rotation(math.radians(45), 4, "Z"))
    parts.append(geo.instances(stud, mats, "studs"))
    # centre medallion and lettering (generic municipal wording, invented foundry)
    parts.append(geo.revolve(geo.fillet([(0.0, -0.0042), (0.040, -0.0042), (0.040, -0.0008), (0.034, -0.0006), (0.0, -0.0006)], 0.0006, 1), 40, name="boss"))
    for body, deg, size, inside in (("SEWER", 90, 0.058, False), ("EL-LINE FOUNDRY", 270, 0.027, True)):
        t = geo.text_on_arc(body, 0.304 if not inside else 0.306, size, 0.0034, 0.0005, deg, inside=inside, name="txt")
        geo.transform(t, loc=(0, 0, -0.0042))
        parts.append(t)
    t = geo.text("N.Y.", 0.022, 0.0034, 0.0004, name="ny")
    geo.transform(t, loc=(0, 0.0, -0.0042))
    parts.append(t)
    for a in (35, 145, 215, 325):                                      # four cast diamonds between the legends
        dmd = geo.box((0.016, 0.016, 0.0032), bevel=0.0012, name="dmd")
        geo.transform(dmd, loc=(0.305 * math.cos(math.radians(a)), 0.305 * math.sin(math.radians(a)), -0.0042), rot=(0, 0, a + 45))
        parts.append(dmd)
    # dirt packed in the gap between cover and frame, and the dark below the pick holes
    parts.append(geo.revolve([(0.3915, -0.0038), (R_COVER - 0.001, -0.0045)], 96, name="gapdirt"))
    for sx in (-1, 1):
        under = geo.box((0.07, 0.04, 0.004), bevel=0.0, name="under")
        geo.transform(under, loc=(sx * 0.305, 0, -0.045))
        parts.append(under)
    ob = geo.join(parts, name, ctx.col)
    # faces nobody can see: the underside of the plate and the outside of the frame skirt
    delete_faces(ob, lambda x, y, z: ((z < -0.0295) & (np.hypot(x, y) < 0.39) & (np.abs(z + 0.043) > 0.003)) | (np.hypot(x, y) > 0.4495))
    geo.smooth_by_angle(ob, 32)
    geo.densify(ob, 0.02, 3)
    m = mat.make("M_Manhole_Iron", "cast_iron", Rust=0.55, Polish=0.08, Pebble=0.7)
    geo.assign(ob, m)
    # ---- masks: tyres polish everything that stands proud; dirt and rust live in the field and the gap
    w = geo.wear_from_geometry(ob, cavity=1.0, edge=0.5, leak=0.0, splash=0.0, ao_distance=0.02, ao_rays=10)
    co, no = geo.arrays(ob)
    r = np.hypot(co[:, 0], co[:, 1])
    top = sstep(-0.0022, -0.0008, co[:, 2]) * (no[:, 2] > 0.5)
    blot = Waves(rng, 0.25)
    bu = blot.u(co[:, 0], co[:, 1])
    track = 0.55 + 0.45 * np.exp(-((co[:, 1] + 0.12) / 0.2) ** 2)      # one wheel track crosses off centre
    G = np.clip(np.maximum(w[:, 1] * 0.6, top * track * (0.55 + 0.6 * bu)), 0, 1)
    Rm = np.clip(w[:, 0] * 0.9 + 0.55 * sstep(-0.002, -0.004, co[:, 2]) * (0.5 + bu) + 1.0 * (np.abs(r - 0.3885) < 0.004)
                 + 0.8 * (co[:, 2] < -0.02), 0, 1)
    geo.set_wear(ob, np.stack([Rm, G, np.zeros_like(r), np.zeros_like(r)], axis=1))
    dens = geo.uv_unwrap(ob, res=ctx.args.res, angle=60, margin_px=4, weights=lambda x, y, z: np.where(z < -0.006, 0.35, 1.0))
    ctx.log("manhole: %d tris, %.0f px/m" % (geo.stats(ob)["triangles"], dens))
    ctx.unique_set(ob, ground=False)
    ctx.asset(ob, collision="box", notes=(
        "Cast-iron manhole cover (772 mm) in its frame (900 mm), flush: z = 0 is the road surface, the frame skirt "
        "goes 60 mm down. Raised 3.4 mm waffle studs, legend 'SEWER', invented foundry mark 'EL-LINE FOUNDRY', 'N.Y.', "
        "two pick holes. Sits in the 0.45 m opening of SM_Street_Road_20m at (%.1f, %.1f)." % MANHOLE),
        pivot="centre, at the road surface", expect_size=(0.9, 0.9, None))
    return ob


# ---------------------------------------------------------------------------------------------------- storm drain

def build_drain(ctx):
    name = "SM_Street_DrainInlet"
    rng = ctx.rng("drain")
    LX, LY = DRAIN[1] - DRAIN[0], DRAIN[3] - DRAIN[2]                 # 1.2 x 0.6
    parts = []
    # frame: angle iron, 38 mm wide on top, set flush
    rim = 0.038
    path = [(-LX / 2 + rim / 2, -LY / 2 + rim / 2, 0), (LX / 2 - rim / 2, -LY / 2 + rim / 2, 0),
            (LX / 2 - rim / 2, LY / 2 - rim / 2, 0), (-LX / 2 + rim / 2, LY / 2 - rim / 2, 0)]
    frame = geo.sweep([(-rim / 2, -0.05), (rim / 2, -0.05), (rim / 2, 0.0), (-rim / 2, 0.0)], path, closed_path=True,
                      cap=False, name="frame", bevel=0.003, bevel_segments=2)
    parts.append(frame)
    # grate: bars across the flow, three stringers along it
    ix, iy = LX - 2 * rim, LY - 2 * rim
    nb = 24
    bar = geo.box((0.014, iy + 0.004, 0.042), bevel=0.0028, segments=2, name="bar")
    pitch = ix / nb
    parts.append(geo.instances(bar, [Matrix.Translation((-ix / 2 + pitch * (i + 0.5) + rng.normal(0, 0.0008), 0, -0.044 + rng.normal(0, 0.0006))) for i in range(nb)], "bars"))
    for y in (-iy / 3, 0.0, iy / 3):
        st = geo.box((ix + 0.004, 0.022, 0.03), bevel=0.003, segments=2, name="stringer")
        geo.transform(st, loc=(0, y, -0.050))
        parts.append(st)
    for ob_ in parts:
        geo.densify(ob_, 0.03, 3)
    iron = mat.make("M_Drain_Iron", "cast_iron", Rust=0.75, Polish=0.05, Pebble=0.6)
    for ob_ in parts:
        geo.assign(ob_, iron)
    # basin: concrete walls going down into the dark, silt and water at the bottom
    depth = 0.55
    wall = geo.sweep([(0.0, -depth), (0.0, -0.05)], [(-ix / 2, -iy / 2, 0), (ix / 2, -iy / 2, 0), (ix / 2, iy / 2, 0),
                                                     (-ix / 2, iy / 2, 0)], closed_path=True, closed_profile=False, cap=False, name="basin")
    geo.face_toward(wall, (0.0, 0.0, -depth / 2))                      # the walls look inward
    geo.densify(wall, 0.06, 4)
    conc = mat.make("M_Drain_Concrete", "concrete", Broom=0.0, Stains=0.9, Weathering=0.8, Aggregate=0.6, Dirt=0.55, Wetness=0.45,
                    Base_Color=(0.26, 0.245, 0.22))
    geo.assign(wall, conc)
    xs = np.linspace(-ix / 2, ix / 2, 41)
    ys = np.linspace(-iy / 2, iy / 2, 19)
    sw = Waves(rng, 0.2)
    silt = geo.heightfield(xs, ys, lambda X, Y: -depth + 0.05 + 0.025 * sw(X, Y) + 0.12 * np.exp(-((X - 0.3) / 0.25) ** 2), name="silt")
    mud = mat.make("M_Drain_Silt", "tar", alpha="wet", Dust_Amount=0.9, Wetness=0.9, Matte=1.0)
    geo.assign(silt, mud)
    ob = geo.join(parts + [wall, silt], name, ctx.col)
    geo.smooth_by_angle(ob, 35)
    # ---- masks
    w = geo.wear_from_geometry(ob, cavity=1.0, edge=0.8, leak=0.0, splash=0.0, ao_distance=0.05, ao_rays=10)
    co, no = geo.arrays(ob)
    blot = Waves(rng, 0.3)
    bu = blot.u(co[:, 0], co[:, 1])
    top = (co[:, 2] > -0.004) & (no[:, 2] > 0.5)
    G = np.clip(np.maximum(w[:, 1] * 0.7, top * (0.35 + 0.5 * bu)), 0, 1)
    Rm = np.clip(w[:, 0] + 0.6 * sstep(-0.004, -0.03, co[:, 2]) + 0.5 * np.exp(-((co[:, 0] - 0.4) / 0.2) ** 2) * (co[:, 2] < -0.003), 0, 1)
    geo.set_wear(ob, np.stack([Rm, G, np.zeros(len(co)), np.zeros(len(co))], axis=1))
    dens = geo.uv_unwrap(ob, res=ctx.args.res, angle=60, margin_px=4, weights=lambda x, y, z: np.where(z < -0.06, 0.3, 1.0))
    ctx.log("drain: %d tris, %.0f px/m" % (geo.stats(ob)["triangles"], dens))
    ctx.unique_set(ob, ground=False)
    ctx.asset(ob, collision="box", notes=(
        "Kerb-side storm drain: angle-iron frame 1.2 x 0.6 m, grate of 24 bars across the flow on three stringers, "
        "0.55 m concrete basin with silt. z = 0 is the top of the frame; it sits 23 mm below the gutter line in the "
        "notch of SM_Street_Road_20m, long side against the kerb face."),
        pivot="centre of the grate, at the top of the frame", expect_size=(LX, LY, None))
    return ob


# --------------------------------------------------------------------------------------------------------- hydrant

def build_hydrant(ctx):
    name = "SM_Prop_Hydrant"
    rng = ctx.rng("hydrant")
    f = geo.fillet
    black, silver = [], []
    # standpipe, breakaway flange pair, lower barrel with its base bell
    black.append(geo.revolve(f([(0.0, 0.0), (0.118, 0.0), (0.118, 0.012), (0.094, 0.03), (0.094, 0.046), (0.158, 0.046), (0.158, 0.068),
                                (0.150, 0.0705), (0.150, 0.0725), (0.158, 0.075), (0.158, 0.097), (0.108, 0.097), (0.098, 0.125),
                                (0.092, 0.17), (0.092, 0.385), (0.096, 0.40), (0.118, 0.412), (0.126, 0.43), (0.126, 0.60),
                                (0.118, 0.622), (0.146, 0.622), (0.146, 0.640), (0.0, 0.640)], 0.004, 3), 64, name="barrel"))
    # two cast bands on the lower barrel
    for z in (0.215, 0.33):
        black.append(geo.revolve(f([(0.0915, z - 0.012), (0.0965, z - 0.008), (0.0965, z + 0.008), (0.0915, z + 0.012)], 0.002, 2), 64, name="band"))
    # bonnet: flange, dome, weather shield and the pentagon operating nut
    silver.append(geo.revolve(f([(0.0, 0.6425), (0.146, 0.6425), (0.146, 0.661), (0.128, 0.663), (0.124, 0.70), (0.104, 0.742),
                                 (0.070, 0.764), (0.052, 0.768), (0.052, 0.778), (0.034, 0.780), (0.030, 0.792), (0.0, 0.792)], 0.004, 3), 64, name="bonnet"))
    nut5 = geo.revolve(f([(0.0, 0.79), (0.0215, 0.79), (0.0215, 0.826), (0.017, 0.832), (0.0, 0.832)], 0.0015, 1), 5, name="opnut")
    geo.smooth_by_angle(nut5, 20)
    silver.append(nut5)
    # flange bolts: 8 through the breakaway pair (heads up, nuts below), 6 round the bonnet
    silver_bolts = geo.instances(geo.hex_bolt(0.016), geo.ring_matrices(6, 0.134, 0.661, 30), "bonnet_bolts")
    silver.append(silver_bolts)
    black.append(geo.instances(geo.hex_bolt(0.019), geo.ring_matrices(8, 0.137, 0.097, 22.5), "flange_bolts"))
    nuts = geo.instances(geo.nut(0.019), [m @ Matrix.Rotation(math.pi, 4, "X") for m in geo.ring_matrices(8, 0.137, 0.046, 22.5)], "flange_nuts")
    black.append(nuts)
    # hose nozzles on both sides (local +-Y): boss on the barrel, neck, threaded stub, cap with lugs and pentagon nut
    for sy in (-1, 1):
        boss = geo.revolve(f([(0.0, 0.0), (0.082, 0.0), (0.080, 0.118), (0.066, 0.132), (0.060, 0.140), (0.0, 0.140)], 0.004, 2), 40, name="boss")
        cap = geo.revolve(f([(0.0, 0.138), (0.071, 0.138), (0.074, 0.142), (0.074, 0.168), (0.068, 0.176), (0.034, 0.180),
                             (0.030, 0.186), (0.0, 0.186)], 0.003, 2), 40, name="cap")
        lugs = geo.instances(geo.box((0.02, 0.012, 0.026), bevel=0.003, name="lug"),
                             [Matrix.Rotation(a, 4, "Z") @ Matrix.Translation((0.078, 0, 0.142)) for a in np.linspace(0, 2 * np.pi, 4, endpoint=False) + 0.4], "lugs")
        capnut = geo.revolve(f([(0.0, 0.184), (0.019, 0.184), (0.019, 0.210), (0.015, 0.214), (0.0, 0.214)], 0.0012, 1), 5, name="capnut")
        geo.smooth_by_angle(capnut, 20)
        rot = (-90 * sy, 0, 0)                                          # local +Z of the lathe -> +-Y
        for part, group in ((boss, black), (cap, silver), (lugs, silver), (capnut, silver)):
            geo.transform(part, rot=rot)
            geo.transform(part, loc=(0, 0, 0.515))
            group.append(part)
        # chain from a lug on the barrel to the cap
        a = (0.045, sy * 0.132, 0.455)
        b = (0.03, sy * 0.186, 0.47)
        lug = geo.torus(0.012, 0.0035, 16, 8, name="eye")
        geo.transform(lug, rot=(0, 90, 0))
        geo.transform(lug, loc=(0.094, sy * 0.084, 0.43))
        black.append(lug)
        black.append(geo.chain([(0.098, sy * 0.086, 0.422), (0.085, sy * 0.125, 0.36), (0.06, sy * 0.165, 0.40), (0.04, sy * 0.186, 0.452)],
                               link_len=0.024, wire=0.0032, name="chain"))
    # raised casting letters on the barrel front (+X): generic year and an OPEN arrow on the bonnet
    for body, z, size in (("19", 0.30, 0.03), ("87", 0.262, 0.03)):
        t = geo.text(body, size, 0.003, 0.0004, name="cast")
        geo.transform(t, rot=(90, 0, 90))
        geo.transform(t, loc=(0.0905, 0, z))
        black.append(t)
    blk = geo.join(black, "blk")
    slv = geo.join(silver, "slv")
    m_black = mat.make("M_Hydrant_Black", "painted_steel", alpha="wet", Paint_Color=(0.026, 0.026, 0.028), Paint_Roughness=0.30,
                       Old_Coat=(0.36, 0.06, 0.035), Primer_Color=(0.30, 0.10, 0.06), Chipping=0.34, Rust=0.42, Chalking=0.35)
    m_silver = mat.make("M_Hydrant_Silver", "painted_steel", alpha="wet", Paint_Color=(0.56, 0.57, 0.58), Paint_Metallic=0.85,
                        Paint_Roughness=0.40, Old_Coat=(0.03, 0.03, 0.032), Primer_Color=(0.30, 0.10, 0.06), Chipping=0.30,
                        Rust=0.36, Chalking=0.2)
    geo.assign(blk, m_black)
    geo.assign(slv, m_silver)
    ob = geo.join([blk, slv], name, ctx.col)
    geo.smooth_by_angle(ob, 35)
    geo.densify(ob, 0.02, 3)
    # ---- masks from the shape, then the story: rust under every bolt and seam, road dust at the foot,
    #      and the leak: the east nozzle cap weeps, water runs down the barrel to the flange and off the foot
    bolt_src = [(0.137 * math.cos(a), 0.137 * math.sin(a), 0.046) for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)]
    bolt_src += [(0.146 * math.cos(a), 0.146 * math.sin(a), 0.622) for a in np.linspace(0, 2 * np.pi, 10, endpoint=False)]
    bolt_src += [(0.07 * math.cos(a), sy * 0.14, 0.515 + 0.07 * math.sin(a)) for sy in (-1, 1) for a in (-2.4, -1.57, -0.8)]
    w = geo.wear_from_geometry(ob, cavity=0.9, edge=0.9, leak=0.9, splash=0.0, ao_distance=0.05, ao_rays=12,
                               leak_sources=bolt_src, leak_auto=True, leak_length=0.26, leak_width=0.012)
    co, no = geo.arrays(ob)
    x, y, z = co[:, 0], co[:, 1], co[:, 2]
    blot = Waves(rng, 0.12)
    bu = blot.u(x * 1.0 + y, z)
    Rm = np.clip(w[:, 0] + 0.55 * np.exp(-z / 0.07) * (0.6 + 0.6 * bu), 0, 1)                # foot: splash-back dirt
    G = np.clip(w[:, 1] * (0.7 + 0.5 * bu) + 0.25 * (z > 0.79) + 0.2 * sstep(0.17, 0.2, np.abs(y)) * (0.4 + bu), 0, 1)
    Bm = np.clip(w[:, 2], 0, 1)
    ang = np.arctan2(y, x)
    side = np.exp(-((ang - (math.pi / 2 - 0.3)) / 0.33) ** 2)                                # below the +Y nozzle (west once placed)
    weep = side * sstep(0.47, 0.44, z) * (np.hypot(x, y) < 0.17) * (0.75 + 0.4 * bu)
    weep = np.maximum(weep, (y > 0.12) * sstep(0.52, 0.46, z) * (z > 0.42) * 0.9)
    foot = sstep(0.06, 0.0, z) * (0.5 + 0.5 * side)
    A = np.clip(np.maximum(weep, foot), 0, 1)
    Bm = np.maximum(Bm, 0.45 * weep)
    geo.set_wear(ob, np.stack([Rm, G, Bm, A], axis=1))
    geo.weighted_normals(ob)
    dens = geo.uv_unwrap(ob, res=ctx.args.res, angle=60, margin_px=6)
    ctx.log("hydrant: %d tris, %.0f px/m" % (geo.stats(ob)["triangles"], dens))
    ctx.unique_set(ob, ground=True)
    ctx.asset(ob, collision="convex", cover_height=0.83, notes=(
        "Two-nozzle municipal hydrant, 0.83 m: standpipe, breakaway flange pair with 8 bolts, banded barrel, two 2.5 inch "
        "hose nozzles with caps on chains (along local Y), bolted bonnet, pentagon operating nut. Black enamel body, "
        "aluminium-painted bonnet and caps, chipped to an older red coat, primer and rust. Baked with a weep under the "
        "+Y cap. Forward = +X (the street side). In the street scene it is turned +90 deg so the nozzles run along the kerb."),
        pivot="centre of the footprint on the ground; forward +X", expect_size=(None, None, 0.83))
    return ob


# ---------------------------------------------------------------------------------------------------------- layout

def layout(ctx, A):
    """Assemble the 20 x 22 m section from the modules (instances share their mesh)."""
    col = scene.collection("Layout", ctx.col)
    placed = []

    def put(src, loc, rot=0.0, first=[set()]):
        if src.name not in first[0]:
            first[0].add(src.name)
            ob = src
        else:
            ob = scene.duplicate(src, linked=True, col=col)
        scene.place(ob, loc, rot)
        ob["mi_placed"] = True
        placed.append(ob)
        return ob

    put(A["road"], (0, 0, 0))
    north_k = ["", "B", "", "B", ""]
    south_k = ["B", "Wet", "", "B", ""]               # index = module, west to east; the hydrant is in module 1
    north_w = ["B", "", "C", "B", ""]
    south_w = ["C", "Wet", "B", "", "B"]
    for i in range(5):
        x = i * MOD
        put(A["kerb"][north_k[i]], (x, HALF, 0))
        put(A["walk"][north_w[i]], (x, HALF, 0))
        put(A["kerb"][south_k[i]], (x + MOD, -HALF, 0), 180)
        put(A["walk"][south_w[i]], (x + MOD, -HALF, 0), 180)
    put(A["manhole"], (MANHOLE[0], MANHOLE[1], A["shape"].z_mh))
    put(A["drain"], ((DRAIN[0] + DRAIN[1]) / 2, (DRAIN[2] + DRAIN[3]) / 2, A["shape"].z_dr))
    put(A["hydrant"], (HYDRANT[0], HYDRANT[1], KERB_H), 90)
    return placed


def build(ctx):
    M = materials(ctx)
    ctx.log("materials ready (%s)" % ("texture sets" if any(m.get("mi_set") for m in M.values()) else "procedural"))
    road, shape = build_road(ctx, M)
    ctx.log("road: %d tris" % geo.stats(road)["triangles"])
    A = {"road": road, "shape": shape, "kerb": {}, "walk": {}}
    for v in ("", "B", "Wet"):
        A["kerb"][v] = build_kerb(ctx, M, v)
    for v in ("", "B", "C", "Wet"):
        A["walk"][v] = build_sidewalk(ctx, M, v)
    ctx.log("kerbs %d tris, sidewalks %d tris" % (geo.stats(A["kerb"][""])["triangles"], geo.stats(A["walk"][""])["triangles"]))
    A["manhole"] = build_manhole(ctx)
    A["drain"] = build_drain(ctx)
    A["hydrant"] = build_hydrant(ctx)
    ctx.A = A
    ctx.M = M
    ctx.placed = layout(ctx, A)
    return [a["ob"] for a in ctx.assets.values()]


# --------------------------------------------------------------------------------------------------------- previews

def _dress(ctx):
    """Preview-only context so the section does not float in a void: the same modules repeated up and down the
    street (instances), and a dark ground beyond. Nothing here is exported."""
    col = scene.collection("Dressing", ctx.col)
    out = []
    for k in (-2, -1, 1, 2, 3):
        for ob in ctx.placed:
            if ob.data is ctx.A["hydrant"].data:
                continue
            d = scene.duplicate(ob, linked=True, col=col)
            d.location.x += k * L
            out.append(d)
    out.append(render.backdrop(600.0, (0.075, 0.073, 0.07), z=-0.06))
    # stand-in massing at the building lines: a tall blank party wall on the north side (it faces the sun and
    # throws its shadow away from the street) and a low yard wall on the south side
    wall_n = geo.box((220.0, 0.5, 10.5), bevel=0.0, name="DressWallN")
    geo.transform(wall_n, loc=(L / 2, HALF + WALK1 + 0.27, KERB_H))
    wall_s = geo.box((220.0, 0.32, 1.05), bevel=0.01, name="DressWallS")
    geo.transform(wall_s, loc=(L / 2, -(HALF + WALK1 + 0.18), KERB_H))
    cope = geo.box((220.0, 0.42, 0.07), bevel=0.012, name="DressCope")
    geo.transform(cope, loc=(L / 2, -(HALF + WALK1 + 0.18), KERB_H + 1.05))
    brick = ctx.M.get("brick") or mat.flat("M_Dress_Brick", (0.21, 0.095, 0.07), 0.85)
    for wl in (wall_n, wall_s):
        geo.uv_world_box(wl, brick.get("mi_tile_m", (2.0, 2.0)))
        wl.data.materials.append(brick)
        geo.ensure_wear(wl)
        scene.move_to(wl, col)
        out.append(wl)
    geo.uv_world_box(cope, 2.0)
    cope.data.materials.append(ctx.M["concrete"])
    geo.ensure_wear(cope)
    scene.move_to(cope, col)
    out.append(cope)
    return out


def preview(ctx, objs):
    a = ctx.args
    P = paths.previews
    A = ctx.A
    only = set(a.only or [])

    def want(n):
        return not only or n in only
    # tiling proofs
    for set_name, fn in (("TS_Asphalt_Aged", "tiling_asphalt_2x2.jpg"), ("TS_Concrete_Sidewalk", "tiling_concrete_2x2.jpg")):
        if want(fn[:-4]) and os.path.exists(os.path.join(paths.texture_set(set_name), "set.json")):
            bake.tiled_preview(set_name, os.path.join(P, fn), samples=max(24, a.samples // 3))
            ctx.log("preview %s" % fn)
    dress = _dress(ctx)
    render.setup(samples=a.samples)
    # ---- day
    render.rig_day(sun_elevation=45.0, sun_azimuth=235.0)
    if want("street_day_hero"):
        render.cam_look((0.6, -8.55, KERB_H + 1.65), (14.0, -5.6, 0.25), lens=30, name="Cam_Hero")
        _p, sec = render.render_jpeg(os.path.join(P, "street_day_hero.jpg"), a.samples)
        ctx.log("preview street_day_hero.jpg %.0fs" % sec)
    if want("hydrant_day"):
        render.cam_look((HYDRANT[0] - 1.25, HYDRANT[1] + 1.55, KERB_H + 0.62), (HYDRANT[0] + 0.02, HYDRANT[1] - 0.02, KERB_H + 0.40), lens=58,
                        name="Cam_Hydrant")
        _p, sec = render.render_jpeg(os.path.join(P, "hydrant_day.jpg"), a.samples)
        ctx.log("preview hydrant_day.jpg %.0fs" % sec)
    if want("manhole_day"):
        render.cam_look((MANHOLE[0] - 1.05, MANHOLE[1] - 1.0, 0.95), (MANHOLE[0] + 0.05, MANHOLE[1] + 0.05, 0.0), lens=50, name="Cam_Manhole")
        _p, sec = render.render_jpeg(os.path.join(P, "manhole_day.jpg"), a.samples)
        ctx.log("preview manhole_day.jpg %.0fs" % sec)
    if want("street_day_top"):
        for d in dress:
            d.hide_render = True
        bd = render.backdrop(600.0, (0.012, 0.012, 0.012), z=-0.2, name="TopBackdrop")
        cam = render.cam_top(bounds=((0, -11), (L, 11)), margin=1.0)
        cam.data.ortho_scale = 22.0 * 16 / 9
        import tempfile
        from PIL import Image
        tmp = os.path.join(tempfile.gettempdir(), "mi_street_top.png")
        render.render_png(tmp, a.samples)
        img = Image.open(tmp).convert("RGB")
        img = render.label(img, "SM_Street_*  20 x 22 m section, plan, north up  (day rig, sun from the south-west)", (14, 12), 17)
        notes = ["road 14 m: 2 travel + 2 parking lanes", "double yellow, white parking lines (worn)", "utility patch with tar seam",
                 "tar-sealed and open cracks", "manhole 0.9 m, storm drain 1.2 x 0.6 m", "oil under parked engines",
                 "hydrant leak -> wet gutter -> drain", "kerbs 150 mm, sidewalks 4 m: 1.33 x 1.5 m flags"]
        for i, t in enumerate(notes):
            img = render.label(img, t, (14, 60 + i * 28), 13, plate=(0, 0, 0, 120))
        render.save_jpeg(img, os.path.join(P, "street_day_top.jpg"))
        bpy.data.objects.remove(bd, do_unlink=True)
        for d in dress:
            d.hide_render = False
        ctx.log("preview street_day_top.jpg")
    # ---- night: sodium lamps hung under the El line, a pink sign on the south side, a green one across
    if want("street_night_hero"):
        render.rig_night(lamp=(8.5, -3.2, 6.3), lamp_watts=2400.0, extra_lamps=[(27.0, -3.0, 6.3), (44.0, -2.9, 6.3), (-12.0, -3.2, 6.3)],
                         sign=(9.5, -10.9, 3.3), sign_color=(1.0, 0.10, 0.36), sign_watts=420.0, sign_target=(9.5, -7.0, 0.0))
        col = scene.collection("Rig")
        g = bpy.data.lights.new("Sign_Green", "AREA")
        g.shape, g.size, g.size_y, g.energy, g.color = "RECTANGLE", 3.0, 0.8, 700.0, (0.15, 1.0, 0.45)
        go = bpy.data.objects.new("Sign_Green", g)
        go.location = (30.0, 10.9, 3.6)
        from mathutils import Vector
        go.rotation_euler = (Vector((24.0, 0.0, 0.0)) - Vector(go.location)).to_track_quat("-Z", "Y").to_euler()
        col.objects.link(go)
        render.cam_look((0.6, -8.55, KERB_H + 1.65), (14.0, -5.6, 0.25), lens=30, name="Cam_Hero_Night")
        _p, sec = render.render_jpeg(os.path.join(P, "street_night_hero.jpg"), int(a.samples * 1.5))
        ctx.log("preview street_night_hero.jpg %.0fs" % sec)
