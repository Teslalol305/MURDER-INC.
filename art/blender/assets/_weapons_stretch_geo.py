"""STRETCH (semi-automatic marksman rifle, 7.6 mm class, 1,045 mm): geometry.

Gun space = Blender space: X forward along the bore, Y left, Z up, metres; ORIGIN ON THE BORE AT THE REAR FACE OF THE
RECEIVER (the stock is at negative X, as the CHOPPER's origin is its rear trunnion). Butt X -0.255 (pad face -0.255 at
mid height), muzzle +0.790. All numbers are the brief's (docs: weapons round 4 STRETCH specification); where the brief
is silent the CHOPPER's and NINE's conventions are followed.

Built by section (mm; X from the receiver rear, Z from the bore):
    stock       dark solid walnut, lofted sections with a bent R 150 butt, rubber pad 14 mm, rubber cheek riser in a rebate
    receiver    44 x 72 box, hollow (carrier, bolt, breech inside), left charging slot, right ejection port, mag well
    rail        MI-R (21.2 mm across the 45 deg flanks, lugs 5.3 mm every 10.6 mm), lug tops Z +52, X 0..545, web over the handguard
    handguard   R 26 walnut tube with 3 and 9 o'clock slots (barrel visible inside), steel nut ring and front cap, bottom MI-R
    barrel      R 12.5, free floating, stub R 8.5 under the brake; brake R 15.5 with ports (bone MuzzleDevice)
    grip        raked 14 deg, egg section with palm swell, finger grooves and a stippled panel
    controls    trigger (bone), selector (bone), bolt catch (bone), charging T-handle (bone bolt)
    bipod       base clamp on the underside rail, two folded legs (bone bipod)
    irons       flip-up rear aperture and front post on the rail (bones IronsRear / IronsFront)
Every part is a closed shell finished by P() (face attribute 'mid' = surface recipe, rigid bone tag).
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import geo, rig, scene
from assets import weapons as W
from assets import _weapons_kit as K
from assets import _weapons_chopper as C9

mm = 0.001

BLUED, DARK, BRIGHT, WOOD, COVER, BORE, BRASS, POLYMER, COPPER, PRIMER = (
    W.BLUED, W.DARK, W.BRIGHT, W.WOOD, W.COVER, W.BORE, W.BRASS, W.POLYMER, W.COPPER, W.PRIMER)
RUBBER = 19                                       # new surface id (the painter's rubber)

lathe, box, cut, union, round_edges, fix_normals, prism = W.lathe, W.box, W.cut, W.union, W.round_edges, W.fix_normals, W.prism
rpoly, loft_polys, ccw, offset, end_inset = C9.rpoly, C9.loft_polys, C9.ccw, C9.offset, C9.end_inset

ST = {   # brief numbers, metres (gun space)
    "travel": 0.095, "trigger_pivot": (0.100, 0.0, -0.045), "trigger_deg": 17.0, "selector_pivot": (0.040, 0.0225, -0.010),
    "selector_deg": 16.0, "catch_pivot": (0.125, 0.0225, -0.012), "catch_deg": 7.0, "bipod_hinge": (0.470, 0.0, -0.050),
    "bipod_deg": -100.0, "mag_drop": 0.12,
    "sockets": {"Muzzle": (0.790, 0, 0), "Eject": (0.135, -0.0225, 0.020), "SightRear": (0.028, 0, 0.0645),
                "SightFront": (0.505, 0, 0.0645), "RecoilPivot": (-0.245, 0, -0.030), "MagHinge": (0.157, 0, -0.024),
                "Palm_R": (0.046, -0.0165, -0.085), "Palm_L": (0.300, 0, -0.038), "Optic": (0.150, 0, 0.052),
                "MuzzleMount": (0.715, 0, 0), "Underbarrel": (0.300, 0, -0.038)},
    "bones": {"bolt": (0.195, 0, 0.015), "trigger": (0.100, 0, -0.045), "selector": (0.040, 0.0225, -0.010),
              "bolt_catch": (0.125, 0.0225, -0.012), "magazine": (0, 0, 0), "bipod": (0.470, 0, -0.050),
              "MuzzleDevice": (0.715, 0, 0), "IronsRear": (0.028, 0, 0.052), "IronsFront": (0.505, 0, 0.052)},
    "eject_dir": (-0.15, -0.95, 0.30),
}
RAIL_TOP = 52.0            # lug tops, mm
RAIL_PITCH, RAIL_SLOT = 10.6, 5.3


# ---------------------------------------------------------------------------------------------------- helpers

def P(ob, mid, bone, smooth=50.0):
    """Finish a part (see weapons.P): smooth by angle, weighted normals, surface id, rigid bone."""
    return W.P(ob, mid, bone, smooth)


def pchip(xs, ys):
    """Monotone cubic Hermite interpolation (Fritsch-Carlson) through (xs, ys): returns f(x) (array-safe)."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    h, d = np.diff(xs), np.diff(ys) / np.diff(xs)
    m = np.zeros(len(xs))
    m[1:-1] = np.where(d[:-1] * d[1:] > 0, 2 * d[:-1] * d[1:] / (d[:-1] + d[1:] + 1e-30), 0.0)
    m[0], m[-1] = d[0], d[-1]
    for i in range(len(d)):
        if d[i] == 0:
            m[i] = m[i + 1] = 0.0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                t = 3 / math.sqrt(s)
                m[i], m[i + 1] = t * a * d[i], t * b * d[i]

    def f(x):
        x = np.asarray(x, float)
        i = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def sstep(x, a, b):
    return K.smoothstep(x, a, b)


def to_obj(V, F, name, smooth=None):
    return geo.from_arrays(name, np.asarray(V, float), F, smooth=smooth)


def xcyl(x0, x1, r, seg=32, name="Cyl", at=(0.0, 0.0), cap=True, r1=None):
    """Closed cylinder / cone along X from x0 to x1 (metres), radius r (r1 at the far end), centred (y, z) = at."""
    prof = [(x0, 0.0), (x0, r), (x1, r if r1 is None else r1), (x1, 0.0)]
    return lathe(prof, seg, axis="X", at=(0.0, at[0], at[1]), name=name)


def circle_pts(r, n, a0=0.0):
    a = a0 + np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.stack([r * np.cos(a), r * np.sin(a)], 1)


def stadium(L, Wd, n=8):
    """Closed CCW stadium (slot) outline: length L along u, width Wd along v, round ends (n points per end)."""
    r = Wd / 2
    a = np.linspace(-math.pi / 2, math.pi / 2, n)
    right = np.stack([L / 2 - r + r * np.cos(a), r * np.sin(a)], 1)
    left = np.stack([-L / 2 + r - r * np.cos(a), -r * np.sin(a)], 1)
    return np.vstack([right, left])


def poly_prism(poly, a0, a1, axis="X", name="PP"):
    """Closed prism through a CCW polygon (u, v) between a0 and a1 along `axis`: 'X' (y, z), 'Y' (x, z), 'Z' (x, y).
    Ngon caps; use for cutters."""
    Pp = np.asarray(ccw(poly), float)
    n = len(Pp)
    V = []
    for a in (a0, a1):
        for u, v in Pp:
            V.append((a, u, v) if axis == "X" else ((u, a, v) if axis == "Y" else (u, v, a)))
    F = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    F += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return K.outward(to_obj(V, F, name))


def screw(at, axis="Y", sign=1, r=0.0023, h=0.0008, slot=True, seg=18, mid=BLUED, bone="body", hex_=False):
    """Domed round-head screw on a face whose outward normal is +axis (sign -1: -axis): about 150 triangles; the
    slot is a real notch. hex_: a socket-head screw (hex recess) instead."""
    prof = [(-0.0008, 0.0), (-0.0008, r), (0.0, r), (h * 0.5, r * 0.94), (h * 0.85, r * 0.66), (h, r * 0.28), (h, 0.0)]
    ob = lathe(prof, seg, axis=axis, name="Screw")
    if slot:
        c = {"X": box(h * 0.35, h + 0.001, -r * 1.2, r * 1.2, -0.00028, 0.00028),
             "Y": box(-r * 1.2, r * 1.2, h * 0.35, h + 0.001, -0.00028, 0.00028),
             "Z": box(-r * 1.2, r * 1.2, -0.00028, 0.00028, h * 0.35, h + 0.001)}[axis]
        if axis == "Y":
            c = box(-0.00028, 0.00028, h * 0.35, h + 0.001, -r * 1.2, r * 1.2)
        cut(ob, c)
    if sign < 0:
        geo.transform(ob, scale=(1, -1, 1) if axis == "Y" else ((-1, 1, 1) if axis == "X" else (1, 1, -1)))
    geo.transform(ob, loc=at)
    return P(fix_normals(ob), mid, bone)


def bevel_all(ob, w, seg=2, angle=40.0):
    round_edges(ob, w, seg, angle)
    return ob


# ----------------------------------------------------------------------------------------------- STOCK

BUTT_R = 0.150
BUTT_ZC = -0.045                                  # centre height of the butt face


def sag(z, R=BUTT_R):
    d = np.clip(np.asarray(z, float) - BUTT_ZC, -R * 0.99, R * 0.99)
    return R - np.sqrt(R * R - d * d)


def butt_bend(co, full=False, x_end=-0.241, x_free=-0.196):
    """The R 150 butt: x' = x + sag(z) * w(x), w = 1 up to x_end and 0 from x_free (a cylinder about Y);
    full: w = 1 everywhere (the rubber pad, which is bent as a whole)."""
    x, z = co[:, 0], co[:, 2]
    w = np.ones(len(x)) if full else 1.0 - sstep(x, x_end, x_free)
    co[:, 0] = x + w * sag(z)
    return co


# nominal (before the bend) top line, toe line and half width of the stock, mm
TOP = pchip([-255, -241, -226, -205, -190, -150, -110, -75, -40, -15, 0],
            [20.0, 28.0, 36.0, 46.0, 52.0, 56.5, 58.0, 53.8, 48.0, 43.5, 40.0])
TOE = pchip([-255, -241, -226, -200, -170, -130, -90, -50, -20, 0],
            [-110.0, -106.0, -101.5, -92.5, -83.0, -70.0, -54.0, -42.0, -37.0, -35.0])
HW = pchip([-255, -241, -225, -200, -170, -120, -80, -40, 0],
           [19.2, 20.2, 22.5, 26.5, 28.0, 28.0, 27.2, 26.4, 26.0])
PAD0, PAD1, PAD_T = -190.0, -110.0, 5.5          # cheek riser: X range, rubber thickness above the rebate floor


def rebate(x):
    """How far the wood top is lowered under the cheek pad (mm): a rebate with steep 2.5 mm end walls."""
    return PAD_T * sstep(x, PAD0 - 1.0, PAD0 + 1.5) * (1.0 - sstep(x, PAD1 - 1.5, PAD1 + 1.0))


def stock_section(x, grow=0.0, inset=0.0, M=None):
    """Stock cross-section at X (mm) as a CCW polygon in (y, z), metres. grow: oversize (rubber pad); inset: rounding."""
    zt = float(TOP(x)) - float(rebate(x)) + grow
    zb = float(TOE(x)) - grow
    hw = float(HW(x)) + grow
    hwt, hwb = hw, hw - 3.5
    rt = min(6.5, 0.45 * (zt - zb))
    rb = min(10.0, 0.45 * (zt - zb))
    corners = [(-hwb, zb), (hwb, zb), (hwt, zt), (-hwt, zt)]
    pts = rpoly(np.array(corners) * mm, [rb * mm, rb * mm, rt * mm, rt * mm], [7, 7, 6, 6], [10, 12, 10, 12])
    pts = ccw(pts)
    if inset > 0:
        pts = offset(pts, -inset)
    if grow == 0.0:                                                  # the flanks bow out 1.3 mm at mid height (not on the pad)
        bow = 1.3 * float(sstep(x, -228.0, -190.0)) * (1.0 - float(sstep(x, -40.0, -4.0))) * mm
        zc, hh = 0.5 * (zt + zb) * mm, 0.5 * (zt - zb) * mm
        pts = pts.copy()
        pts[:, 0] += np.sign(pts[:, 0]) * bow * np.clip(1.0 - ((pts[:, 1] - zc) / hh) ** 2, 0.0, 1.0)
    return pts


def stock_wood(parts):
    """Walnut stock from X -241 (bent R 150 end) to X +3 (inside the receiver rear plate)."""
    xs = list(np.linspace(-241, -200, 9)) + list(np.linspace(-196, 3, 41))
    xs += [PAD0 - 1.0, PAD0 + 0.5, PAD0 + 1.5, PAD1 - 1.5, PAD1 - 0.5, PAD1 + 1.0]
    xs = np.array(sorted(set(np.round(xs, 3))))
    polys = [stock_section(x) for x in xs]
    ob = loft_polys(polys, xs * mm, "Stock")
    K.deform(ob, butt_bend)
    parts.append(P(ob, WOOD, "body"))
    return ob


def butt_pad(parts):
    """Rubber recoil pad: 14 mm thick curved plate (R 150 rear face), 0.8 mm bigger than the wood, 2.5 mm round-over."""
    xs = np.array(sorted(set(np.round(list(np.linspace(-255, -241, 12)) + [-254.6, -254.0, -253.0, -252.0], 3))))
    polys = []
    for x in xs:
        d = (x + 255.0) * mm                                   # rounded at the rear face only
        ins = 0.0 if d >= 0.0025 else 0.0025 - math.sqrt(max(0.0, 0.0025 ** 2 - (0.0025 - d) ** 2))
        polys.append(stock_section(float(x), grow=0.8, inset=ins))
    ob = loft_polys(polys, xs * mm, "ButtPad")
    K.deform(ob, lambda co: butt_bend(co, full=True))
    parts.append(P(ob, RUBBER, "body"))
    # two slotted pad screws on the rear face (normal tilted with the arc)
    for z in (0.0, -0.090):
        xr = -0.255 + float(sag(z))
        tilt = math.degrees(math.asin((z - BUTT_ZC) / BUTT_R))            # face normal tilts about Y
        s = screw((0, 0, 0), "X", -1, r=0.0033, h=0.0008, seg=22, mid=DARK)
        geo.transform(s, rot=(0, -tilt, 0))
        geo.transform(s, loc=(xr, 0.0, z))
        parts.append(s)
    return ob


def cheek_pad(parts):
    """Stippled rubber cheek riser: 80 mm long, top follows the comb line, 5.5 mm proud of the rebate floor."""
    xs = np.array(sorted(set(np.round(list(np.linspace(PAD0, PAD1, 24)), 3))))
    polys = []
    hw = 17.0
    for x in xs:
        ins = end_inset(x, PAD0, PAD1, 2.0) * mm
        zt = float(TOP(x))
        zb = zt - PAD_T - 0.4
        pts = rpoly(np.array([(-hw, zb), (hw, zb), (hw - 0.8, zt), (-hw + 0.8, zt)]) * mm,
                    [1.2 * mm, 1.2 * mm, 2.6 * mm, 2.6 * mm], [4, 4, 5, 5], [6, 3, 6, 3])
        pts = ccw(pts)
        if ins > 0:
            pts = offset(pts, -ins)
        polys.append(pts)
    ob = loft_polys(polys, xs * mm, "CheekPad")
    parts.append(P(ob, RUBBER, "body"))
    for x in (-178.0, -122.0):                                      # two screws through the pad
        parts.append(screw((x * mm, 0.0, float(TOP(x)) * mm), "Z", 1, r=0.0026, h=0.0007, mid=DARK))
    return ob


def sling_studs(parts):
    """Sling stud under the toe and a swivel boss on the left flank (round heads on necks)."""
    def stud(at, axis, sign):
        prof = [(-0.0030, 0.0), (-0.0030, 0.0042), (-0.0004, 0.0042), (0.0, 0.0030), (0.0030, 0.0030), (0.0033, 0.0046),
                (0.0062, 0.0050), (0.0072, 0.0044), (0.0072, 0.0)]
        s = lathe(prof, 22, axis=axis, name="Stud")
        if sign < 0:
            geo.transform(s, scale=(1, -1, 1) if axis == "Y" else ((-1, 1, 1) if axis == "X" else (1, 1, -1)))
        geo.transform(s, loc=at)
        return P(fix_normals(s), DARK, "body")
    zt = float(TOE(-205.0)) * mm
    parts.append(stud((-0.205, 0.0, zt + 0.0006), "Z", -1))
    parts.append(stud((-0.082, float(HW(-82.0)) * mm - 0.0004, -0.012), "Y", 1))


def flank(x, z):
    """Half width (m) of the wood stock's flank at X (mm) and height Z (m): the section is a trapezoid."""
    zt, zb = float(TOP(x)) - float(rebate(x)), float(TOE(x))
    hw = float(HW(x))
    t = np.clip((z / mm - zb) / (zt - zb), 0, 1)
    return (hw - 3.5 + t * 3.5) * mm


def stock_screws(parts):
    """Stock bolts: two round-head slotted screws on each flank at the receiver joint (domed heads on washers)."""
    for sy in (1, -1):
        for (x, z) in ((-0.0165, 0.0200), (-0.0165, -0.0170)):
            y = flank(x / mm, z)
            w = lathe([(-0.0012, 0.0), (-0.0012, 0.0058), (0.0, 0.0058), (0.0, 0.0)], 22, axis="Y", name="Washer")
            s = screw((0, 0.0, 0), "Y", 1, r=0.0044, h=0.0020, seg=22)
            geo.transform(s, loc=(0, 0.0, 0))
            part = geo.join([w, s], "Screw")
            if sy < 0:
                geo.transform(part, scale=(1, -1, 1))
            geo.transform(part, loc=(x, sy * y, z))
            parts.append(P(fix_normals(part), BLUED, "body"))


# ------------------------------------------------------------------------------------------------ RECEIVER

REC = dict(x0=0.0, x1=235.0, hw=22.0, zb=-32.0, zt=40.0, wall=3.0, cav0=4.0, cav1=209.5)
PORT = dict(x0=110.0, x1=190.0, z0=4.0, z1=30.0)          # ejection port, right flank
SLOT = dict(x0=88.0, x1=206.0, z0=9.5, z1=20.5)           # charging slot, left flank (stem path 100..195)
WELL = dict(x0=129.0, x1=185.0, hw=15.5, zb=-48.0)        # mag well sleeve, inner 52 x 26 (X 131..183)


def rrect_xz(x0, x1, z0, z1, r, n=6):
    """Rounded rectangle (x, z) CCW, metres from mm."""
    return np.array(ccw(rpoly(np.array([(x0, z0), (x1, z0), (x1, z1), (x0, z1)]) * mm, [r * mm] * 4, [n] * 4, [1] * 4)))


def receiver(parts):
    """The receiver: 44 x 72 x 235 box with 1.5 mm chamfered ends, hollow (cavity 38 x 66 x 205), the right ejection
    port, the left charging slot and the magazine opening cut through, every cut edge round-cornered."""
    st = C9.stations(0.0, REC["x1"], REC["x1"], 1.5, 3)
    polys = []
    for x in st:
        ins = end_inset(x, 0.0, REC["x1"], 1.5) * mm
        pts = rpoly(np.array([(-22, -32), (22, -32), (22, 40), (-22, 40)]) * mm, [4 * mm, 4 * mm, 1.2 * mm, 1.2 * mm],
                    [6, 6, 3, 3], [2, 2, 2, 2])
        pts = ccw(pts)
        polys.append(offset(pts, -ins) if ins > 0 else pts)
    ob = loft_polys(polys, st * mm, "Receiver")
    cav = box(REC["cav0"] * mm, REC["cav1"] * mm, -19 * mm, 19 * mm, -29 * mm, 37 * mm, bevel=0.0008, seg=1, name="Cav")
    cut(ob, cav)
    port = poly_prism(rrect_xz(PORT["x0"], PORT["x1"], PORT["z0"], PORT["z1"], 3.5), -24 * mm, -17.5 * mm, "Y", "Port")
    cut(ob, port)
    slot = poly_prism(rrect_xz(SLOT["x0"], SLOT["x1"], SLOT["z0"], SLOT["z1"], 5.5, 8), 17.5 * mm, 24 * mm, "Y", "Slot")
    cut(ob, slot)
    mo = poly_prism(np.array(ccw(rpoly(np.array([(131, -13), (183, -13), (183, 13), (131, 13)]) * mm, [2.5 * mm] * 4,
                                       [5] * 4, [1] * 4))), -33 * mm, -28 * mm, "Z", "MagOpen")
    cut(ob, mo)
    # milled pockets 0.7 mm deep with R 4-6 corners: left behind the slot (selector well), round the bolt catch and the slot,
    # right round the ejection port and a long panel behind it
    for (x0_, x1_, z0_, z1_, r_, side) in ((8, 80, -30, 7, 5, 1), (100, 163, -23, -0.5, 4, 1), (84, 212, 4, 26, 6, 1),
                                          (98, 204, -3, 37, 6, -1), (8, 92, -28, 33, 6, -1)):
        yy0, yy1 = (21.3, 24.0) if side > 0 else (-24.0, -21.3)
        cut(ob, poly_prism(rrect_xz(x0_, x1_, z0_, z1_, r_, 5), yy0 * mm, yy1 * mm, "Y", "Pocket"))
    round_edges(ob, 0.00035, 2, 50)
    parts.append(P(ob, BLUED, "body"))
    return ob


def receiver_screws(parts):
    """Slotted screws and cross-pin heads on both flanks (pins hold the trunnion block, screws the rear plate)."""
    for sy in (1, -1):
        yf = sy * 22.0 * mm
        for (x, z) in ((12.0, 33.5), (222.0, 33.5), (222.0, -25.0), (12.0, -26.5)):
            parts.append(screw((x * mm, yf, z * mm), "Y", sy, r=0.0024, h=0.0009, seg=18))
        for (x, z) in ((216.0, 19.0), (216.0, -14.0)):
            parts.append(screw((x * mm, yf, z * mm), "Y", sy, r=0.0034, h=0.0010, slot=False, seg=20, bone="body"))


def trunnion_and_ring(parts):
    """Barrel nut ring (castle nut, R 29.5, X 225..242) and the breech block inside the receiver front."""
    prof = [(225.0, 14.2), (225.0, 28.6), (225.9, 29.5), (240.6, 29.5), (242.0, 28.1), (242.0, 14.2)]
    ring = lathe([(t * mm, r * mm) for t, r in prof], 56, axis="X", name="NutRing", closed=True)
    for k in range(8):                                    # eight wrench notches in the front rim
        a = k * 45.0 + 22.5
        n = box(238.8 * mm, 243 * mm, -1.6 * mm, 1.6 * mm, 25.5 * mm, 31 * mm, bevel=0.0)
        geo.transform(n, rot=(a, 0, 0))
        cut(ring, n)
    round_edges(ring, 0.00025, 1, 55)
    parts.append(P(ring, BLUED, "body"))


def dust_cover(parts):
    """The spring dust cover, open: hinged along the port's lower edge on a rod with three knuckles, swung 170 deg so
    it hangs against the flank (it must stay inside Y -0.0287); stamped plate with a rolled bead."""
    x0, x1, hz, hy = PORT["x0"] - 2.5, PORT["x1"] + 2.5, PORT["z0"] - 0.8, -(REC["hw"] + 0.9)
    h = 31.0
    pl = box(x0 * mm, x1 * mm, -0.8 * mm, 0.8 * mm, 0.0, h * mm, bevel=0.0005, seg=1, name="Cover")
    bead = box((x0 + 5) * mm, (x1 - 5) * mm, -1.5 * mm, 0.0, (h - 6) * mm, (h - 3.5) * mm, bevel=0.0007, seg=2)
    pl = geo.join([pl, bead], "Cover")
    geo.transform(pl, rot=(-170.0, 0, 0))                # about the X axis through the hinge (y = 0, z = 0)
    geo.transform(pl, loc=(0, hy * mm, hz * mm))
    parts.append(P(pl, BLUED, "body"))
    xs = np.linspace(x0, x1, 4)
    for i in range(3):                                   # knuckles round the hinge rod
        k = xcyl((xs[i] + 1.0) * mm, (xs[i + 1] - 1.0) * mm if i != 1 else (xs[i + 1] - 1.0) * mm, 2.1 * mm, 16, "Knuckle",
                 at=(hy * mm, hz * mm))
        if i == 1:
            continue
        parts.append(P(k, BLUED, "body"))
    rod = xcyl((x0 - 0.5) * mm, (x1 + 0.5) * mm, 1.1 * mm, 12, "Rod", at=(hy * mm, hz * mm))
    parts.append(P(rod, DARK, "body"))


def mag_well(parts):
    """Magazine well: a rounded sleeve under the receiver floor (X 129..185, 31 wide, 16 mm deep), hollow 52 x 26 and
    flared at the mouth; the release button on the right."""
    xs = [-32.5, -33.0 + 0.0, -46.0, -48.0]
    outer = box(WELL["x0"] * mm, WELL["x1"] * mm, -WELL["hw"] * mm, WELL["hw"] * mm, WELL["zb"] * mm, -31.2 * mm,
                bevel=0.0022, seg=2, name="WellOuter")
    parts_w = outer
    inner_st = [(-49.0, 3.0), (-47.2, 1.2), (-45.5, 0.0), (-30.0, 0.0)]
    polys = []
    for z, grow in inner_st:
        polys.append((ccw(rpoly(np.array([(131 - grow, -13 - grow), (183 + grow, -13 - grow), (183 + grow, 13 + grow),
                                          (131 - grow, 13 + grow)]) * mm, [2.0 * mm] * 4, [4] * 4, [1] * 4)), z))
    cutter = loft_polys([p for p, _ in polys], [z * mm for z, _ in inner_st], "WellCut", axis="Z")
    cut(parts_w, cutter)
    round_edges(parts_w, 0.00025, 1, 55)
    parts.append(P(parts_w, BLUED, "body"))
    # release button, right side: a 8.6 mm cylinder with a domed head, retained by a boss
    prof = [(-0.0016, 0.0), (-0.0016, 0.0062), (0.0, 0.0062), (0.0, 0.0044), (0.0030, 0.0044), (0.0036, 0.0040),
            (0.0040, 0.0024), (0.0042, 0.0)]
    b = lathe(prof, 24, axis="Y", name="MagRelease")
    geo.transform(b, scale=(1, -1, 1))
    geo.transform(b, loc=(171 * mm, -(WELL["hw"] - 0.35) * mm, -40 * mm))
    parts.append(P(fix_normals(b), BLUED, "body"))


# ------------------------------------------------------------------------------------------------- RAILS (MI-R)

def lug_mesh(sign=1):
    """One MI-R lug (mm): 5.3 long, profile above the slot floor with 45 deg flanks, 0.3 chamfers all round.
    sign=1 rail on top (lug tops Z +52), sign=-1 on the underside (lug undersides Z -38)."""
    prof = np.array([(-10.6, 45.3), (10.6, 45.3), (10.6, 49.25), (7.85, 52.0), (-7.85, 52.0), (-10.6, 49.25)])
    xs = np.array([0.0, 0.3, 5.0, 5.3])
    polys = []
    for x in xs:
        ins = max(0.0, 0.3 - min(x, 5.3 - x))
        p = ccw(prof)
        polys.append(offset(p, -ins) if ins > 0 else p)
    # the lug as a loft along X; coordinates in mm here, scaled by the caller
    V = np.zeros((len(xs), len(prof), 3))
    for i, (x, p) in enumerate(zip(xs, polys)):
        V[i, :, 0], V[i, :, 1], V[i, :, 2] = x, p[:, 0], p[:, 1]
    n = len(prof)
    F = []
    for i in range(len(xs) - 1):
        for j in range(n):
            j1 = (j + 1) % n
            F.append((i * n + j, i * n + j1, (i + 1) * n + j1, (i + 1) * n + j))
    F.append(tuple(range(n - 1, -1, -1)))
    F.append(tuple((len(xs) - 1) * n + j for j in range(n)))
    V = V.reshape(-1, 3)
    if sign < 0:
        V = V * np.array([1.0, 1.0, -1.0])
        V[:, 2] += 0.0
        F = [tuple(reversed(f)) for f in F]
    return V, F


def rail_lugs(x_start, n, sign, name="Lugs", z_shift=0.0):
    """n lugs at the MI-R pitch from x_start (mm): one mesh. sign -1: the mirror image about Z 0 (an underside rail:
    pass z_shift so the lug tops/bottoms land: lug undersides at Z -38 need the profile 12 mm tall below the tube)."""
    V0, F0 = lug_mesh(sign)
    V0 = V0.copy()
    V0[:, 2] += z_shift
    Vs, Fs = [], []
    for k in range(n):
        v = V0.copy()
        v[:, 0] += x_start + k * RAIL_PITCH
        Fs += [tuple(i + k * len(V0) for i in f) for f in F0]
        Vs.append(v)
    V = np.vstack(Vs) * mm
    return K.outward(to_obj(V, Fs, name))


def rail_top(parts):
    """The top rail, monolithic over receiver and handguard: slot-floor strip Z 39.8..45.3, 52 lugs, X 0..545.9, and a
    14 mm web from the strip down into the handguard over X 232..545.9."""
    L = 545.9
    strip = box(0.0, L * mm, -10.6 * mm, 10.6 * mm, 39.8 * mm, 45.3 * mm, bevel=0.0003, seg=1, name="RailBase")
    parts.append(P(strip, BLUED, "body"))
    parts.append(P(rail_lugs(0.0, 52, 1, "RailLugs"), BLUED, "body"))
    # web over the handguard: (y, z) polygon with flared feet buried in the wood
    web = ccw(np.array([(-9.2, 21.5), (9.2, 21.5), (9.2, 23.4), (6.4, 25.4), (5.2, 28.2), (5.2, 39.9), (-5.2, 39.9),
                        (-5.2, 28.2), (-6.4, 25.4), (-9.2, 23.4)]) * mm)
    wb = poly_prism(web, 232.0 * mm, L * mm, "X", "RailWeb")
    round_edges(wb, 0.0004, 1, 50)
    parts.append(P(wb, BLUED, "body"))
    # clamp screws on the web's flanks every 90 mm (two sizes would be real; one is enough): none here, kept clean


def rail_bottom(parts):
    """Bottom rail X 284.5..480.6: slot floor strip and 19 lugs hanging down to Z -38 (lug undersides)."""
    x0 = 284.5
    L = 19 * RAIL_PITCH - RAIL_SLOT + 0.0
    strip = box(x0 * mm, (x0 + L) * mm, -10.6 * mm, 10.6 * mm, -31.3 * mm, -21.5 * mm, bevel=0.0003, seg=1, name="RailBaseB")
    parts.append(P(strip, BLUED, "body"))
    # mirror image of the top rail's lug: slot floor at Z -31.3, lug undersides at -38.0 (6.7 deep), tips 15.7 wide
    prof = np.array([(-10.6, -31.3), (-10.6, -35.25), (-7.85, -38.0), (7.85, -38.0), (10.6, -35.25), (10.6, -31.3)])
    xs = np.array([0.0, 0.3, 5.0, 5.3])
    V, F = [], []
    n = len(prof)
    for i, x in enumerate(xs):
        ins = max(0.0, 0.3 - min(x, 5.3 - x))
        p = ccw(prof)
        p = offset(p, -ins) if ins > 0 else p
        for q in p:
            V.append((x, q[0], q[1]))
    for i in range(len(xs) - 1):
        for j in range(n):
            j1 = (j + 1) % n
            F.append((i * n + j, i * n + j1, (i + 1) * n + j1, (i + 1) * n + j))
    F.append(tuple(range(n - 1, -1, -1)))
    F.append(tuple((len(xs) - 1) * n + j for j in range(n)))
    V0 = np.array(V)
    Vs, Fs = [], []
    for k in range(19):
        v = V0.copy()
        v[:, 0] += x0 + k * RAIL_PITCH
        Fs += [tuple(i + k * len(V0) for i in f) for f in F]
        Vs.append(v)
    ob = K.outward(to_obj(np.vstack(Vs) * mm, Fs, "RailLugsB"))
    parts.append(P(ob, BLUED, "body"))


# ---------------------------------------------------------------------------------------- HANDGUARD, BARREL

TUBE = dict(x0=240.0, x1=541.0, r=26.0, ri=23.0)
SLOT_X = [275.0 + 36.0 * k for k in range(7)]


def handguard(parts):
    """Walnut tube R 26 (bore R 23), seven 4 x 24 mm slots on each flank (3 and 9 o'clock) and two 3 mm vents; the
    barrel and the gas block show inside. Steel front cap ring."""
    seg = 64
    th = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    xs = [TUBE["x0"], TUBE["x1"]]
    # closed loop profile revolved: outer wall, front face, inner wall, rear face
    prof = [(TUBE["x0"], TUBE["ri"]), (TUBE["x0"], TUBE["r"] - 1.2), (TUBE["x0"] + 1.2, TUBE["r"]), (TUBE["x1"] - 1.2, TUBE["r"]),
            (TUBE["x1"], TUBE["r"] - 1.2), (TUBE["x1"], TUBE["ri"])]
    ob = lathe([(t * mm, r * mm) for t, r in prof], seg, axis="X", name="Handguard", closed=True)
    cutters = []
    for x in SLOT_X:
        s = poly_prism(stadium(24.0, 4.0, 7) * mm + np.array([x * mm, 0.0]), -30 * mm, 30 * mm, "Y", "HGSlot")
        cutters.append(s)
    cutter = geo.join(cutters, "HGSlots")
    cut(ob, cutter)
    for (x, z) in ((262.0, -14.5), (527.0, -14.5)):          # two 3 mm heat vents, low on the flanks
        for sy in (1,):
            v = lathe([(-30 * mm, 0.0), (-30 * mm, 1.5 * mm), (30 * mm, 1.5 * mm), (30 * mm, 0.0)], 14, axis="Y", name="Vent")
            geo.transform(v, loc=(x * mm, 0.0, z * mm))
            cut(ob, v)
    round_edges(ob, 0.0003, 2, 50)
    parts.append(P(ob, WOOD, "body"))
    # sling socket: a steel cup R 6 on the left flank, low and forward, with a through hole for the loop
    cup = lathe([(0.0246, 0.0), (0.0246, 0.0060), (0.0262, 0.0060), (0.0268, 0.0054), (0.0268, 0.0034), (0.0262, 0.0030),
                 (0.0258, 0.0030), (0.0258, 0.0)], 28, axis="Y", at=(512 * mm, 0.0, -9.0 * mm), name="SlingCup")
    cut(cup, box(508.5 * mm, 515.5 * mm, 25.0 * mm, 28.0 * mm, -10.4 * mm, -7.6 * mm, bevel=0.0))
    parts.append(P(fix_normals(cup), BLUED, "body"))
    # steel front cap ring: R 26.6 outside, R 14.6 bore, 4.5 mm long, chamfered
    cap = [(TUBE["x1"], 14.6), (TUBE["x1"], 26.0), (TUBE["x1"] + 0.8, 26.8), (TUBE["x1"] + 3.8, 26.8), (TUBE["x1"] + 4.5, 26.0),
           (TUBE["x1"] + 4.5, 14.6)]
    ring = lathe([(t * mm, r * mm) for t, r in cap], 48, axis="X", name="HGCap", closed=True)
    round_edges(ring, 0.0002, 1, 55)
    parts.append(P(ring, BLUED, "body"))


def barrel(parts):
    """R 12.5 barrel from the breech (X 207, chamber hole R 5.5 and bore R 3.8) to the thread shoulder at 715 with the
    0.4 mm step, threaded stub R 8.5 to 727 (hidden by the brake), and the gas block R 16 at X 428..454."""
    seg = 48
    prof = [(207.0, 3.8), (207.0, 10.6), (208.2, 11.8), (212.0, 12.5), (712.0, 12.5), (712.0, 12.1), (715.0, 12.1), (715.0, 8.5),
            (727.0, 8.5), (727.0, 3.8)]
    # bore: a closed loop (the bore runs the whole length, so the barrel is a tube): chamber hole at the breech
    prof = [(207.0, 5.6), (207.0, 10.6), (208.2, 11.8), (212.0, 12.5), (712.0, 12.5), (712.0, 12.1), (715.0, 12.1),
            (715.0, 8.5), (726.0, 8.5), (727.0, 7.5), (727.0, 4.7), (726.2, 3.8), (219.0, 3.8), (219.0, 5.6)]
    ob = lathe([(t * mm, r * mm) for t, r in prof], seg, axis="X", name="Barrel", closed=True)
    parts.append(P(ob, BLUED, "body"))
    gp = [(428.0, 12.0), (428.0, 14.6), (430.0, 16.0), (452.0, 16.0), (454.0, 14.6), (454.0, 12.0)]
    gb = lathe([(t * mm, r * mm) for t, r in gp], 36, axis="X", name="GasBlock", closed=True)
    boss = xcyl(426.0 * mm, 456.0 * mm, 4.6 * mm, 20, "GasBoss", at=(0.0, 16.5 * mm))
    gb = geo.join([gb, boss], "GasBlock")
    parts.append(P(fix_normals(gb), BLUED, "body"))


def muzzle_brake(parts):
    """Muzzle brake (bone MuzzleDevice): closed shell X 715..790, R 15.5, rear socket R 8.9 swallowing the stub, two baffles
    (R 4.2) making three chambers, front wall with the R 3.5 bore, three ports per flank and a top port."""
    outer = [(715.0, 14.0), (716.5, 15.5), (788.5, 15.5), (790.0, 14.0)]
    inner = [(790.0, 3.5), (785.0, 3.5), (785.0, 10.5), (763.0, 10.5), (763.0, 4.2), (761.0, 4.2), (761.0, 10.5), (746.0, 10.5),
             (746.0, 4.2), (744.0, 4.2), (744.0, 10.5), (727.0, 10.5), (727.0, 8.9), (715.0, 8.9)]
    ob = lathe([(t * mm, r * mm) for t, r in outer + inner], 48, axis="X", name="Brake", closed=True)
    cutters = []
    for cx, ln in ((735.0, 10.0), (753.5, 8.0), (774.0, 13.0)):
        for sy in (1, -1):
            c = poly_prism(rrect_xz(cx - ln / 2, cx + ln / 2, -4.0, 4.0, 1.6, 4), 0.0, 20 * mm, "Y", "Port")
            if sy < 0:
                geo.transform(c, scale=(1, -1, 1))
            cutters.append(c)
    top = poly_prism(rrect_xz(766.5, 782.0, -3.5, 3.5, 1.6, 4), 0.0, 20 * mm, "Y", "TopPort")   # polygon in (x, z)
    geo.transform(top, rot=(-90, 0, 0))                                  # now cuts upward from the axis
    geo.transform(top, loc=(0, 0, 0))
    cutters.append(top)
    cut(ob, geo.join(cutters, "BrakePorts"))
    round_edges(ob, 0.0003, 2, 50)
    parts.append(P(ob, BLUED, "MuzzleDevice"))


# ------------------------------------------------------------------------------------------- GRIP, TRIGGER GROUP

GZ = (-30.0, -140.0)
G_BACK = pchip([-140, -85, -40, -30], [5.0, 19.0, 30.0, 32.4])
G_FRONT = pchip([-140, -85, -40, -30], [62.0, 74.0, 85.0, 87.4])
G_GROOVES = ((-62.0, 3.2), (-84.0, 3.6), (-106.0, 3.2))


def grip_section(z, inset=0.0):
    """Egg section (round 1 of the STRETCH): back and front lines of the brief (55 mm fore-aft at the lines), three finger
    grooves in the front strap, a 1.2 mm palm swell per side at palm height (33 mm across), heel rounded."""
    x0 = float(G_BACK(z)) + inset / mm
    x1 = float(G_FRONT(z)) - inset / mm
    for zc, d in G_GROOVES:
        x1 -= d * math.exp(-((z - zc) / 5.5) ** 2)
    dh = z - GZ[1]
    if dh < 6.0:
        x0 += 6.0 - math.sqrt(max(0.0, 6.0 ** 2 - (6.0 - dh) ** 2))
    w = 15.3 + 1.2 * math.exp(-((z + 85.0) / 19.0) ** 2) + 1.3 * float(sstep(z, -50.0, -30.0)) - 1.0 * float(sstep(-z, 125.0, 140.0)) - inset / mm
    a, xc = (x1 - x0) / 2, (x0 + x1) / 2
    th = np.linspace(0, 2 * math.pi, 128, endpoint=False)
    c, s_ = np.cos(th), np.sin(th)
    p = np.where(c < 0, 2.2, 2.5)
    xx = xc + a * np.sign(c) * np.abs(c) ** (2 / p)
    yy = w * np.sign(s_) * np.abs(s_) ** (2 / p) * (1.0 - 0.12 * np.clip(c, 0, 1) ** 1.5)
    sec = K.poly_section(np.stack([xx, yy], 1) * mm, K=480)
    sec.x0, sec.x1 = x0 * mm, x1 * mm
    return sec


def pistol_grip(parts):
    zs = list(np.arange(GZ[0], GZ[1] + 4.0, -3.0)) + [GZ[0] - 0.4, GZ[1] + 3.0, GZ[1] + 1.6, GZ[1] + 0.6, GZ[1]]
    zs = np.array(sorted(set(np.round(zs, 4)), reverse=True))
    secs = []
    for z in zs:
        d = GZ[1] + 3.0 - z
        ins = 0.0 if d <= 0 else (3.0 - math.sqrt(max(0.0, 3.0 ** 2 - d * d))) * mm
        secs.append(grip_section(float(z), ins))
    g = K.loft_z(secs, zs * mm, 64, name="Grip")
    parts.append(P(g, WOOD, "body"))
    # 3 mm steel tang plate under the receiver floor with its two screws, and the heel cap with the grip screw
    top = grip_section(GZ[0], -0.0006)
    pl = K.loft_z([top, top], [(GZ[0] - 0.2) * mm, (GZ[0] + 2.2) * mm], 64, name="GripPlate")
    round_edges(pl, 0.0004, 1, 40)
    parts.append(P(pl, BLUED, "body"))
    cap = grip_section(GZ[1], 0.0)
    xm = (cap.x0 + cap.x1) / 2
    c = lathe([(0.0, 0.0), (0.0, 0.0082), (-0.0003, 0.0082), (-0.0006, 0.0076), (-0.0008, 0.0), ], 28, axis="Z",
              at=(xm, 0.0, GZ[1] * mm + 0.0006), name="GripCap")
    c.data.transform(Matrix.Identity(4))
    parts.append(P(fix_normals(c), BLUED, "body"))
    plate = K.loft_z([grip_section(GZ[1] + 0.5, 0.0008), grip_section(GZ[1], 0.0008)], [(GZ[1] + 2.0) * mm, GZ[1] * mm],
                     64, name="HeelPlate")
    round_edges(plate, 0.0004, 1, 40)
    parts.append(P(plate, BLUED, "body"))


def trigger_group(parts):
    """Trigger housing under the receiver (X 88..131), cross pin with its heads, the trigger blade (bone trigger), the guard
    strap from the grip front to the magazine well, and the magazine catch tab."""
    hs = box(88 * mm, 131 * mm, -12.5 * mm, 12.5 * mm, -52.0 * mm, -31.3 * mm, bevel=0.0018, seg=2, name="TrigHousing")
    cut(hs, box(90 * mm, 122 * mm, -3.8 * mm, 3.8 * mm, -53.0 * mm, -47.5 * mm, bevel=0.0))
    round_edges(hs, 0.0003, 1, 55)
    parts.append(P(hs, BLUED, "body"))
    for sy in (1, -1):
        parts.append(screw((100 * mm, sy * 12.5 * mm, -45 * mm), "Y", sy, r=0.0032, h=0.0010, slot=False, seg=20))
    # trigger blade, 6 mm wide
    outline = np.array([(95, -43), (99, -39.2), (105, -39.2), (108.5, -43.5), (110.5, -50), (113.5, -57), (116, -63),
                        (115.5, -69), (112, -74.5), (107.5, -75.5), (104.5, -72.5), (102, -64), (98.5, -54), (95.5, -47)])
    outline = K.spline(outline, 5, closed=True) * mm
    tr = prism([tuple(p) for p in outline], -3.0 * mm, 3.0 * mm, axis="Y", bevel=0.0006, seg=2, name="Trigger")
    parts.append(P(tr, DARK if False else BLUED, "trigger"))
    # the guard: 3.2 x 12 mm strap, rolled edges, from the grip front under the trigger up the well's rear face
    gp = np.array([(73, -90.5), (77, -96.5), (85, -100.5), (100, -101.8), (118, -101.8), (125, -99.5), (129.2, -92.0), (129.2, -50.0)])
    gp = np.array(K.spline(gp, 10)) * mm
    path = np.stack([gp[:, 0], np.zeros(len(gp)), gp[:, 1]], 1)
    prof = np.array(ccw(rpoly(np.array([(-1.6, -6.0), (1.6, -6.0), (1.6, 6.0), (-1.6, 6.0)]) * mm, [1.0 * mm] * 4, [3] * 4, [2, 4, 2, 4])))
    gd = K.sweep_var(path, lambda i, t: prof, name="Guard")
    parts.append(P(gd, BLUED, "body"))
    for x in (76.0,):                                        # the guard's screw into the grip front
        parts.append(screw((x * mm, 6.0 * mm, -91.5 * mm), "Y", 1, r=0.0028, h=0.0009, seg=18))
    # magazine catch tab behind the well (right side), a stamped lever with a thumb pad
    t = [(131.0, -45.0), (137.0, -45.0), (137.0, -39.0), (133.5, -36.0), (131.0, -37.0)]
    cp = prism([(a * mm, b * mm) for a, b in t], -19.2 * mm, -16.0 * mm, axis="Y", bevel=0.0005, seg=1, name="CatchTab", fillet=0.0008)
    parts.append(P(cp, BLUED, "body"))


# ------------------------------------------------------------------------------------------------ CONTROLS

def selector(parts):
    """Selector lever on the left flank (bone selector, pivot X 40, Z -10): hub R 6.8, thumb lever with serrations."""
    px, pz = 40.0, -10.0
    boss = lathe([(0.0211, 0.0), (0.0211, 0.0068), (0.0236, 0.0068), (0.0244, 0.0059), (0.0244, 0.0)], 28, axis="Y",
                 at=(px * mm, 0.0, pz * mm), name="SelHub")
    lever = np.array([(-4.5, -3.0), (-1, -5.0), (10, -4.0), (22, -3.2), (26.5, -1.8), (27.5, 1.4), (24.5, 3.6), (12, 3.8),
                      (0, 5.0), (-5, 2.5)])
    lever = K.spline(lever, 5, closed=True)
    lv = prism([((px + a) * mm, (pz + b) * mm) for a, b in lever], 24.2 * mm, 27.6 * mm, axis="Y", bevel=0.0005, seg=2,
               name="SelLever")
    rid = [box((px + 16 + 3.0 * k) * mm, (px + 17.4 + 3.0 * k) * mm, 27.2 * mm, 28.0 * mm, (pz - 3.4) * mm, (pz + 3.2) * mm,
               bevel=0.0002, seg=1) for k in range(3)]                          # thumb ridges
    scr = screw((px * mm, 27.6 * mm, pz * mm), "Y", 1, r=0.0026, h=0.0009, seg=18, bone="selector")
    ob = geo.join([boss, lv] + rid, "Selector")
    parts.append(P(fix_normals(ob), BLUED, "selector"))
    parts.append(scr)


def bolt_catch(parts):
    """Bolt catch lever on the left flank (bone bolt_catch, pivot X 125, Z -12): stamped plate with a thumb pad."""
    outline = np.array([(106, -5.5), (111, -3.5), (118, -4.6), (128, -8.5), (143, -10.6), (152, -12.8), (153, -15.8), (148, -17.2),
                        (132, -16.6), (122, -15.6), (116, -12), (110, -8.8)])
    outline = K.spline(outline, 4, closed=True) * mm
    lv = prism([tuple(p) for p in outline], 21.6 * mm, 24.2 * mm, axis="Y", bevel=0.0004, seg=2, name="Catch")
    boss = lathe([(0.0211, 0.0), (0.0211, 0.0046), (0.0246, 0.0046), (0.0246, 0.0)], 24, axis="Y", at=(125 * mm, 0.0, -12 * mm),
                 name="CatchHub")
    ob = geo.join([lv, boss], "BoltCatch")
    parts.append(P(fix_normals(ob), BLUED, "bolt_catch"))
    parts.append(screw((125 * mm, 24.6 * mm, -12 * mm), "Y", 1, r=0.0030, h=0.0009, seg=18, bone="bolt_catch"))


def charging_handle(parts):
    """T-handle on the left of the carrier (bone bolt): stem R 3.4 through the slot, washer on the flank, T-bar 28 x 9 mm
    out to Y +40 with serrations on its outer face."""
    cx, cz = 195.0, 15.0
    stem = lathe([(0.0088, 0.0), (0.0088, 0.0034), (0.0334, 0.0034), (0.0334, 0.0)], 20, axis="Y", at=(cx * mm, 0.0, cz * mm),
                 name="Stem")
    wash = lathe([(0.0213, 0.0), (0.0213, 0.0053), (0.0236, 0.0053), (0.0236, 0.0)], 28, axis="Y", at=(cx * mm, 0.0, cz * mm),
                 name="StemWasher")
    bar = poly_prism(stadium(28.0, 9.0, 8) * mm + np.array([cx * mm, cz * mm]), 32.0 * mm, 40.4 * mm, "Y", "TBar")
    round_edges(bar, 0.0011, 2, 40)
    cuts = [box((cx - 11.0 + 3.4 * k) * mm, (cx - 10.0 + 3.4 * k) * mm, 39.7 * mm, 41.0 * mm, (cz - 3.6) * mm, (cz + 3.6) * mm,
                bevel=0.0) for k in range(7)]
    cut(bar, geo.join(cuts, "Serr"))
    round_edges(bar, 0.0002, 1, 50)
    ob = geo.join([stem, wash, bar], "ChargingHandle")
    parts.append(P(fix_normals(ob), BLUED, "bolt"))


def bolt_group(parts):
    """Bolt carrier (bright) with its lightening pocket and cam groove, bolt head with six lugs and the firing-pin hole,
    extractor claw: all bone bolt. Rest: the head face 0.1 mm off the breech (X 209.4)."""
    car = box(120 * mm, 203 * mm, -9.5 * mm, 9.5 * mm, -5.0 * mm, 23.0 * mm, bevel=0.0012, seg=2, name="Carrier")
    cut(car, box(133 * mm, 176 * mm, -10.5 * mm, -7.2 * mm, 3.0 * mm, 17.0 * mm, bevel=0.0))
    cut(car, box(150 * mm, 190 * mm, -2.8 * mm, 2.8 * mm, 20.5 * mm, 24.0 * mm, bevel=0.0))
    cut(car, box(150 * mm, 168 * mm, 6.5 * mm, 10.5 * mm, 8.0 * mm, 12.0 * mm, bevel=0.0))
    round_edges(car, 0.0004, 1, 50)
    parts.append(P(car, BRIGHT, "bolt"))
    head = lathe([(190.0, 0.0), (190.0, 6.6), (191.0, 7.2), (208.6, 7.2), (209.4, 6.4), (209.4, 1.6), (206.4, 1.6), (206.4, 0.0)][0:0]
                 or [(t * mm, r * mm) for t, r in [(190.0, 0.0), (190.0, 6.6), (191.0, 7.2), (208.6, 7.2), (209.4, 6.4), (209.4, 1.6),
                                                   (206.4, 1.6), (206.4, 0.0)]], 36, axis="X", name="BoltHead")
    lobes = []
    n = 24
    for i in range(n):
        a = 2 * math.pi * i / n
        lug = 0.5 + 0.5 * math.cos(6 * a)                    # six lobes, gap centred on -Y (270 deg)
        lobes.append((math.cos(a) * (7.2 + 1.5 * (1.0 if lug > 0.55 else 0.0)) * mm, math.sin(a) * (7.2 + 1.5 * (1.0 if lug > 0.55 else 0.0)) * mm))
    star = poly_prism(np.array(lobes), 196.0 * mm, 205.0 * mm, "X", "Lugs")
    round_edges(star, 0.0003, 1, 40)
    ext = prism([(196 * mm, -1.6 * mm), (210.0 * mm, -1.6 * mm), (210.6 * mm, -0.2 * mm), (208.6 * mm, 1.8 * mm), (196 * mm, 1.8 * mm)],
                -9.6 * mm, -6.8 * mm, axis="Y", bevel=0.0003, seg=1, name="Extractor")
    ob = geo.join([head, star, ext], "BoltHeadGroup")
    parts.append(P(fix_normals(ob), BRIGHT, "bolt"))


# --------------------------------------------------------------------------------------------------- BIPOD, IRONS

def hexnut(at, axis="Y", r=0.0034, h=0.0022, sign=1, bone="body", mid=BLUED):
    prof = [(-0.0008, 0.0), (-0.0008, r), (h, r), (h, 0.0)]
    ob = lathe(prof, 6, axis=axis, name="Nut")
    if sign < 0:
        geo.transform(ob, scale=(1, -1, 1) if axis == "Y" else ((-1, 1, 1) if axis == "X" else (1, 1, -1)))
    geo.transform(ob, loc=at)
    return P(fix_normals(ob), mid, bone)


def bipod(parts):
    """Bipod: base clamp on the bottom rail (X 446..480, body bone), hinge pin and two folded 8 mm legs (bone bipod): legs
    lie backward under the handguard from X 470 to 320 at Z -50, Y +-22, rubber feet; -100 deg about +Y deploys."""
    outline = [(446, -38.0), (480, -38.0), (480, -49), (476.5, -56), (450, -56), (446, -50)]
    blk = prism([(a * mm, b * mm) for a, b in outline], -12.8 * mm, 12.8 * mm, axis="Y", bevel=0.0013, seg=2, name="BipodClamp",
                fillet=0.0018)
    cut(blk, box(447 * mm, 479 * mm, -10.7 * mm, 10.7 * mm, -38.5 * mm, -35.0 * mm, bevel=0.0))      # slot over the rail lugs
    parts.append(P(blk, BLUED, "body"))
    for sy in (1, -1):
        j = box(449.5 * mm, 476.5 * mm, 10.8 * mm, 13.1 * mm, -38.0 * mm, -30.6 * mm, bevel=0.0006, seg=1, name="Jaw")
        if sy < 0:
            geo.transform(j, scale=(1, -1, 1))
        parts.append(P(j, BLUED, "body"))
        e = box(463.5 * mm, 476.5 * mm, 13.0 * mm, 18.2 * mm, -56.0 * mm, -43.5 * mm, bevel=0.0012, seg=2, name="Ear")
        if sy < 0:
            geo.transform(e, scale=(1, -1, 1))
        parts.append(P(e, BLUED, "body"))
    parts.append(screw((460 * mm, -13.1 * mm, -34.2 * mm), "Y", -1, r=0.0034, h=0.0020, slot=False, seg=20))
    parts.append(hexnut((460 * mm, 13.1 * mm, -34.2 * mm), "Y", 0.0036, 0.0024, 1))
    pin = lathe([(-0.0262, 0.0), (-0.0262, 0.0022), (0.0262, 0.0022), (0.0262, 0.0)], 16, axis="Y", at=(470 * mm, 0.0, -50 * mm),
                name="BipodPin")
    parts.append(P(fix_normals(pin), DARK, "bipod"))
    for sy in (1, -1):
        parts.append(screw((470 * mm, sy * 26.2 * mm, -50 * mm), "Y", sy, r=0.0034, h=0.0010, slot=False, seg=18, bone="bipod"))
        kn = lathe([(0.0195, 0.0), (0.0195, 0.0054), (0.0252, 0.0054), (0.0252, 0.0)], 24, axis="Y", at=(470 * mm, 0.0, -50 * mm),
                   name="Knuckle")
        tube = xcyl(341 * mm, 470 * mm, 4.0 * mm, 22, "Leg", at=(0.0, 0.0))
        geo.transform(tube, loc=(0, 0, 0))
        col = xcyl(393 * mm, 400 * mm, 4.8 * mm, 22, "Collar")
        lock = box(405 * mm, 412 * mm, -2.2 * mm, 2.2 * mm, 3.2 * mm, 5.6 * mm, bevel=0.0006, seg=1, name="Lock")
        leg = geo.join([tube, col, lock], "LegTube")
        geo.transform(leg, loc=(0, 0, -50 * mm))
        geo.transform(leg, loc=(0, 0, 0))
        parts_l = [leg, kn]
        # leg sits at Y +-22
        for o in parts_l:
            pass
        if sy > 0:
            geo.transform(leg, loc=(0, 22 * mm, 0))
        else:
            geo.transform(leg, loc=(0, -22 * mm, 0))
            geo.transform(kn, scale=(1, -1, 1))
        parts.append(P(fix_normals(geo.join([leg, kn], "Leg")), DARK, "bipod"))
        foot = lathe([(320.0 * mm, 0.0), (320.0 * mm, 3.2 * mm), (321.6 * mm, 4.7 * mm), (333.0 * mm, 4.7 * mm), (341.0 * mm, 4.0 * mm),
                      (341.0 * mm, 0.0)], 22, axis="X", at=(0.0, sy * 22 * mm, -50 * mm), name="Foot")
        for k in range(5):                                           # tread ribs
            rb = lathe([(0.0, 0.0), (0.0, 4.95 * mm), (1.0 * mm, 4.95 * mm), (1.0 * mm, 0.0)], 22, axis="X",
                       at=(0.0, 0.0, 0.0))
            geo.transform(rb, loc=((324.0 + 2.6 * k) * mm, sy * 22 * mm, -50 * mm))
            foot = geo.join([foot, rb], "Foot")
        parts.append(P(fix_normals(foot), RUBBER, "bipod"))


def irons_rear(parts):
    """Flip-up rear aperture (bone IronsRear, head X 28, Z 52): clamp on the rail, hinge ears and pin, leaf with an 8 mm hole
    centred on the sight line (Z 64.5)."""
    B = "IronsRear"
    cl = box(14 * mm, 42 * mm, -14.4 * mm, 14.4 * mm, 52.0 * mm, 56.0 * mm, bevel=0.0012, seg=2, name="RClamp")
    parts.append(P(cl, DARK, B))
    for sy in (1, -1):
        jw = prism([(14 * mm, 52.0 * mm), (42 * mm, 52.0 * mm), (42 * mm, 46.5 * mm), (14 * mm, 46.5 * mm)], 10.8 * mm, 14.4 * mm,
                   axis="Y", bevel=0.0006, seg=1, name="RJaw")
        if sy < 0:
            geo.transform(jw, scale=(1, -1, 1))
        parts.append(P(jw, DARK, B))
        ear = box(22 * mm, 33 * mm, 7.2 * mm, 10.2 * mm, 56.0 * mm, 61.5 * mm, bevel=0.0008, seg=2, name="REar")
        if sy < 0:
            geo.transform(ear, scale=(1, -1, 1))
        parts.append(P(ear, DARK, B))
    parts.append(screw((24 * mm, -14.4 * mm, 54.0 * mm), "Y", -1, r=0.0030, h=0.0016, slot=False, seg=18, mid=BLUED, bone=B))
    pin = lathe([(-0.0108, 0.0), (-0.0108, 0.0020), (0.0108, 0.0020), (0.0108, 0.0)], 14, axis="Y", at=(27.5 * mm, 0.0, 59.0 * mm),
                name="RPin")
    parts.append(P(fix_normals(pin), BLUED, B))
    ring = circle_pts(7.2 * mm, 28)
    ring[:, 1] += 64.5 * mm
    leaf = poly_prism(np.vstack([ring]), 26.0 * mm, 30.0 * mm, "X", "RLeaf")
    neck = poly_prism(np.array([(-5.0, 58.0), (5.0, 58.0), (5.0, 64.5), (-5.0, 64.5)]) * mm, 26.0 * mm, 30.0 * mm, "X", "RNeck")
    base = poly_prism(np.array([(-8.0, 57.0), (8.0, 57.0), (8.0, 61.0), (-8.0, 61.0)]) * mm, 25.5 * mm, 30.5 * mm, "X", "RBase")
    hole = xcyl(24.0 * mm, 32.0 * mm, 4.0 * mm, 24, "RHole", at=(0.0, 64.5 * mm))
    cut(leaf, hole)
    round_edges(leaf, 0.0004, 1, 45)
    parts.append(P(leaf, DARK, B))
    round_edges(neck, 0.0004, 1, 45)
    parts.append(P(neck, DARK, B))
    round_edges(base, 0.0004, 1, 45)
    parts.append(P(base, DARK, B))


def irons_front(parts):
    """Flip-up front post (bone IronsFront, head X 505, Z 52): clamp, riser, two protecting ears, a 2.5 mm post with its tip
    on the sight line (Z 64.5)."""
    B = "IronsFront"
    cl = box(493 * mm, 517 * mm, -14.4 * mm, 14.4 * mm, 52.0 * mm, 56.0 * mm, bevel=0.0012, seg=2, name="FClamp")
    parts.append(P(cl, DARK, B))
    for sy in (1, -1):
        jw = prism([(493 * mm, 52.0 * mm), (517 * mm, 52.0 * mm), (517 * mm, 46.5 * mm), (493 * mm, 46.5 * mm)], 10.8 * mm,
                   14.4 * mm, axis="Y", bevel=0.0006, seg=1, name="FJaw")
        if sy < 0:
            geo.transform(jw, scale=(1, -1, 1))
        parts.append(P(jw, DARK, B))
        ear = box(499 * mm, 511 * mm, 6.2 * mm, 9.0 * mm, 56.0 * mm, 63.4 * mm, bevel=0.0009, seg=2, name="FEar")
        if sy < 0:
            geo.transform(ear, scale=(1, -1, 1))
        parts.append(P(ear, DARK, B))
    parts.append(screw((498 * mm, 14.4 * mm, 54.0 * mm), "Y", 1, r=0.0030, h=0.0016, slot=False, seg=18, mid=BLUED, bone=B))
    riser = box(499 * mm, 511 * mm, -4.4 * mm, 4.4 * mm, 56.0 * mm, 59.0 * mm, bevel=0.0007, seg=1, name="FRiser")
    parts.append(P(riser, DARK, B))
    post = prism([(503.6 * mm, 58.5 * mm), (506.4 * mm, 58.5 * mm), (506.4 * mm, 63.2 * mm), (505.9 * mm, 64.5 * mm),
                  (504.1 * mm, 64.5 * mm), (503.6 * mm, 63.2 * mm)], -1.25 * mm, 1.25 * mm, axis="Y", bevel=0.0003, seg=1, name="FPost")
    parts.append(P(post, DARK, B))


# -------------------------------------------------------------------------------------------------------- MAGAZINE

MAG = dict(x0=133.0, x1=181.0, hy=12.0, zt=-24.0, zb=-135.0)


def stretch_magazine(col):
    """SM_Weapon_StretchMagazine (+ _TopRound): 24 x 48 mm straight box, 111 mm from the feed lips (Z -24) to the floor plate
    (Z -135): stamped steel body with two raised ribs per side, folded feed lips, follower, the second round, a black
    polymer floor plate with a drag tab; the top round is a separate piece. Origin = gun origin (in place)."""
    parts = []
    x0, x1, hy = MAG["x0"], MAG["x1"], MAG["hy"]

    def rect(gx, gy, r=3.4):
        return ccw(rpoly(np.array([(x0 - gx, -hy - gy), (x1 + gx, -hy - gy), (x1 + gx, hy + gy), (x0 - gx, hy + gy)]) * mm,
                         [r * mm] * 4, [5] * 4, [4, 2, 4, 2]))
    outer = loft_polys([rect(0, 0), rect(0, 0)], np.array([MAG["zb"] + 0.0, MAG["zt"]]) * mm, "MagBody", axis="Z")
    cav_st = [(-129.0, -0.9), (-28.0, -0.9), (-25.4, -0.9)]
    cp = []
    for z, g in cav_st:
        cp.append(rect(g, g, 2.6))
    lip = rect(-0.9, -0.9, 2.6).copy()
    lip[:, 1] *= 0.78                                   # lips folded in over the rounds
    cp.append(lip)
    cutter = loft_polys(cp, np.array([-129.0, -28.0, -25.2, -23.0]) * mm, "MagCavity", axis="Z")
    cut(outer, cutter)
    round_edges(outer, 0.0003, 2, 50)
    parts.append(P(outer, BLUED, None))
    # two stamped ribs on each side wall: 3 mm wide, 0.8 mm proud, 30 mm long, rounded
    for z in (-64.0, -101.0):
        for sy in (1, -1):
            ya, yb = (hy - 0.15, hy + 1.0) if sy > 0 else (-hy - 1.0, -hy + 0.15)
            rb = box((x0 + 8.0) * mm, (x1 - 8.0) * mm, ya * mm, yb * mm, (z - 2.4) * mm, (z + 2.4) * mm, bevel=0.0009, seg=2, name="Rib")
            parts.append(P(rb, BLUED, None))
    # the vertical weld seam on the front wall (a 1.2 mm bead) and a rolled bead under the lips
    wd = box((x1 - 0.5) * mm, (x1 + 0.45) * mm, -1.4 * mm, 1.4 * mm, -128.0 * mm, -27.0 * mm, bevel=0.0004, seg=2, name="Weld")
    parts.append(P(wd, BLUED, None))
    # follower: stamped plate under the second round with a centre rib
    fl = box((x0 + 1.5) * mm, (x1 - 1.5) * mm, -9.8 * mm, 9.8 * mm, -50.5 * mm, -48.8 * mm, bevel=0.0005, seg=1, name="Follower")
    fr = box((x0 + 12) * mm, (x1 - 12) * mm, -3.0 * mm, 3.0 * mm, -53.2 * mm, -50.4 * mm, bevel=0.0006, seg=1, name="FollowerRib")
    fl = geo.join([fl, fr], "Follower")
    parts.append(P(fl, DARK, None))
    # floor plate: black polymer 26 x 50 x 8 mm with the drag tab and a retaining step
    fp_ = box((x0 - 1.0) * mm, (x1 + 1.0) * mm, -(hy + 1.0) * mm, (hy + 1.0) * mm, -135.0 * mm, -127.0 * mm, bevel=0.0018, seg=2, name="Floor")
    tab = box((x1 + 0.5) * mm, (x1 + 8.5) * mm, -5.5 * mm, 5.5 * mm, -135.0 * mm, -130.0 * mm, bevel=0.0012, seg=2, name="DragTab")
    cut(tab, lathe([(-4 * mm, 0.0), (-4 * mm, 2.4 * mm), (4 * mm, 2.4 * mm), (4 * mm, 0.0)], 14, axis="Z", at=((x1 + 5.2) * mm, 0.0, -136 * mm)))
    fp_ = geo.join([fp_, tab], "Floor")
    parts.append(P(fix_normals(fp_), POLYMER, None))
    # second round in the stack (right column, 9.2 mm below the top round)
    r2 = W.cartridge(0.044, 0.0056, name="Round2", seg=28)
    geo.transform(r2, loc=((x0 + 2.2) * mm, -3.6 * mm, (-24.0 - 6.0 - 9.2) * mm))
    parts.append(r2)
    top = W.cartridge(0.044, 0.0056, name="TopRound", seg=32)
    geo.transform(top, loc=((x0 + 2.2) * mm, 3.6 * mm, (-24.0 - 6.0) * mm))
    body = geo.join(parts, "SM_Weapon_StretchMagazine", col)
    scene.move_to(top, col)
    top.name = top.data.name = "SM_Weapon_StretchMagazine_TopRound"
    return body, top


# ---------------------------------------------------------------------------------------------------- ASSEMBLY

def stretch_parts():
    parts = []
    for fn in (stock_wood, butt_pad, cheek_pad, sling_studs, stock_screws, receiver, receiver_screws, trunnion_and_ring, dust_cover, mag_well,
               rail_top, rail_bottom, handguard, barrel, muzzle_brake, pistol_grip, trigger_group, selector, bolt_catch,
               charging_handle, bolt_group, bipod, irons_rear, irons_front):
        fn(parts)
    return parts


def stretch_bones():
    bones = [rig.Bone("body", (0, 0, 0))]
    for k in ("bolt", "trigger", "selector", "bolt_catch", "magazine", "bipod", "MuzzleDevice", "IronsRear", "IronsFront"):
        bones.append(rig.Bone(k, ST["bones"][k], "body"))
    bones += [rig.Bone(k, v, "body", deform=False) for k, v in ST["sockets"].items()]
    return bones


def stretch_build(ctx, finish=None):
    parts = stretch_parts()
    gun = geo.join(parts, "SK_Stretch", ctx.col)
    if finish:
        finish(gun)
    arm = rig.armature("SKEL_Stretch", stretch_bones(), ctx.col)
    rig.bind(gun, arm)
    return gun, arm
