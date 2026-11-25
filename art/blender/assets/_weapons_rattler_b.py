"""RATTLER, second half: pistol grip, trigger guard and group, the bolt with its top T-handle, the selector, the wire stock with
its hinge, the strap wrap, the sling plate, the small hardware, the stick magazine with its top round, and the rig.
See _weapons_rattler.py for the contract and the big solids.
"""
import math

import numpy as np
from mathutils import Matrix, Vector

from mi import geo, rig
from assets import weapons as W
from assets import _weapons_kit as K
from assets import _weapons_rattler as S

MM = S.MM
bx, pr, lt, tr, rot_x = S.bx, S.pr, S.lt, S.tr, S.rot_x
SHEET, BLACK, BRIGHT, POLY, ZINC, STRAP, BORE, WHITE = S.SHEET, S.BLACK, S.BRIGHT, S.POLY, S.ZINC, S.STRAP, S.BORE, S.WHITE
BRASS, COPPER, PRIMER, MAGSTEEL, INNER = S.BRASS, S.COPPER, S.PRIMER, S.MAGSTEEL, S.INNER
joined = S.joined

# ----------------------------------------------------------------------------------------------- pistol grip

GBACK = K.spline([(33.0, -41.0), (34.2, -60.0), (36.0, -82.0), (38.0, -110.0), (40.0, -141.0), (40.4, -143.5)], 10)
GFRONT = K.spline([(98.0, -41.0), (91.0, -55.0), (84.0, -70.0), (80.6, -90.0), (80.0, -120.0), (80.0, -143.5)], 10)
GRIP_TOP, GRIP_BOT = -41.0, -143.5
GROOVES = (-93.0, -107.0, -121.0)          # shallow finger swells in the front strap: centre Z, 7 mm tall, 1.5 mm deep


def groove(z):
    g = 0.0
    for zg in GROOVES:
        d = abs(z - zg)
        if d < 3.5:
            g += 1.5 * 0.5 * (1.0 + math.cos(math.pi * d / 3.5))
    return g


def grip_half_width(z):
    return float(np.interp(z, [-143.5, -82.0, -70.0, -50.0, -41.0], [14.0, 15.3, 16.0, 17.0, 17.6]))


def grip_section(z, d=0.0):
    """Egg section (mm -> m): ~44 deep and 32 wide at palm height, round at the back, flatter at the front with the finger
    swells; d insets the section (rounded base)."""
    xb = float(K.x_of_z(GBACK, z)) + d
    xf = float(K.x_of_z(GFRONT, z)) - groove(z) - d
    w = grip_half_width(z) - d
    crown = 0.9 * math.exp(-((z + 76.0) / 22.0) ** 2)
    return K.rrect(xb * MM, xf * MM, w * MM, min(w * 0.96, 13.0) * MM, 6.0 * MM, bulge_f=0.4 * MM, crown=crown * MM)


def grip_levels():
    zs = list(np.arange(GRIP_TOP, GRIP_BOT, -3.0))
    for zg in GROOVES:
        zs += list(zg + 3.5 * np.linspace(-1.0, 1.0, 9))
    for k in range(1, 6):
        zs.append(GRIP_BOT + 3.0 * (1.0 - math.cos(k / 5.0 * math.pi / 2.0)))
    zs.append(GRIP_BOT)
    zs = np.array(sorted(set(np.round(zs, 4)), reverse=True))
    return zs[(zs <= GRIP_TOP) & (zs >= GRIP_BOT)]


def build_grip():
    """Black polymer pistol grip: horizontal sections lofted down the rake with a palm swell, shallow finger swells in the
    front strap, a rounded base with a cap recess and the 4 mm lanyard hole through the heel."""
    zs = grip_levels()
    secs = []
    for z in zs:
        e = z - GRIP_BOT
        d = 0.0
        if e < 3.0:
            d = 3.0 - math.sqrt(max(0.0, 3.0 ** 2 - (3.0 - e) ** 2))
        secs.append(grip_section(float(z), d))
    g = K.loft_z(secs, zs * MM, 56, name="Grip")
    xh = float(K.x_of_z(GBACK, -132.0)) + 6.0
    W.cut(g, lt([(-30, 0), (-30, 2.0), (30, 2.0), (30, 0)], 20, axis="Y", at=(xh, 0.0, -132.0), name="Lanyard"))
    xm = 0.5 * (float(K.x_of_z(GBACK, GRIP_BOT)) + float(K.x_of_z(GFRONT, GRIP_BOT)))
    W.cut(g, lt([(-145.0, 0), (-145.0, 6.2), (-143.3, 6.2), (-143.3, 0)], 40, axis="Z", at=(xm, 0.0, 0.0), name="CapRecess"))
    W.round_edges(g, 0.3 * MM, 1, 60)
    return g


def build_grip_hardware():
    out = []
    xm = 0.5 * (float(K.x_of_z(GBACK, GRIP_BOT)) + float(K.x_of_z(GFRONT, GRIP_BOT)))
    out.append(W.pin_head((xm * MM, 0.0, (GRIP_BOT - 0.15) * MM), "Z", r=0.0034, h=0.0012, sign=-1, slot=True))
    for side in (-1, 1):                                              # the two grip bolts through the upper part
        zb = -58.0
        xb = float(K.x_of_z(GBACK, zb)) + 15.0
        y = grip_half_width(zb) * side
        out.append(W.pin_head((xb * MM, y * MM, zb * MM), "Y", r=0.0030, h=0.0011, sign=side, slot=True, seg=20))
    return out


# ----------------------------------------------------------------------------------------------- guard, trigger group

def d_profile(a, b, p=3.5, M=24):
    return K.superellipse(a * MM, b * MM, p, M)


def build_guard():
    """Stamped steel trigger guard: a flat strap 10 mm wide across the gun and 2.4 mm thick (rolled edges) from the receiver's floor
    down the well's rear face to Z -88 and back to the grip's front strap (a D loop around the trigger)."""
    path = [(141.7, -41.0, 0.0), (141.7, -80.0, 0.0), (134.0, -88.0, 0.0), (94.0, -88.0, 0.0), (84.0, -80.0, 0.0), (82.0, -74.0, 0.0)]
    path = [(x * MM, 0.0, z * MM) for x, z, _ in path]
    pts = geo.fillet(path, 8.0 * MM, 8)
    prof = K.superellipse(1.2 * MM, 5.0 * MM, 3.2, 28)
    return K.sweep_var(pts, lambda i, t: prof, name="Guard", cap=True, up=(0.0, 1.0, 0.0))


TRIG_CL = K.spline([(127.0, -45.0), (129.5, -52.0), (134.5, -62.0), (135.8, -70.0), (134.2, -79.0)], 12)


def build_trigger():
    """Curved steel blade (5 x 7 mm; its rear face is X 132.0 at Z -62) hanging from a hub on the pivot (127, 0, -45); the hub is a
    ring round the 3 mm pin; pull = +17 deg about +Y."""
    n = 40
    cl = np.array([(float(np.interp(t, np.linspace(0, 1, len(TRIG_CL)), TRIG_CL[:, 0])),
                    float(np.interp(t, np.linspace(0, 1, len(TRIG_CL)), TRIG_CL[:, 1]))) for t in np.linspace(0.0, 1.0, 4 * n)])
    cl = cl[cl[:, 1] <= -47.8]                                       # the blade starts under the hub's bore (R 1.7 round the pin)
    path = [(x * MM, 0.0, z * MM) for x, z in cl[:: max(1, len(cl) // n)]] + [(cl[-1][0] * MM, 0.0, cl[-1][1] * MM)]
    base = K.superellipse(2.5 * MM, 3.5 * MM, 3.0, 24)

    def prof(i, t):
        s = 1.0 - 0.28 * float(K.smoothstep(t, 0.80, 1.0))
        return base * np.array([s, 1.0])
    blade = K.sweep_var(path, prof, name="Blade", cap=True, up=(0.0, 1.0, 0.0))
    hub = lt([(-3.4, 2.0), (-3.4, 4.6), (3.4, 4.6), (3.4, 2.0)], 32, axis="Y", at=(127.0, 0.0, -45.0), name="Hub", fillet=0.4, closed=True)
    return geo.join([blade, hub], "Trigger")


def build_trigger_bracket():
    """The stamped hanger under the floor that carries the trigger pin: two 1.6 mm cheeks and the pin with its heads."""
    out = []
    for s in (1, -1):
        y0, y1 = (6.2, 7.8) if s > 0 else (-7.8, -6.2)
        out.append(pr([(116.0, -41.0), (138.0, -41.0), (138.0, -49.0), (134.0, -52.5), (120.0, -52.5), (116.0, -49.0)], y0, y1, "Y",
                      bevel=0.35, seg=1, fillet=1.5, name="Cheek"))
        out.append(W.pin_head((127.0 * MM, (7.8 if s > 0 else -7.8) * MM, -45.0 * MM), "Y", r=0.0027, h=0.0010, sign=s, slot=False, seg=18))
    out.append(lt([(-7.9, 0.0), (-7.9, 1.5), (7.9, 1.5), (7.9, 0.0)], 16, axis="Y", at=(127.0, 0.0, -45.0), name="TriggerPin"))
    return out


# ----------------------------------------------------------------------------------------------- bolt and handle

def build_bolt():
    """Open bolt (parkerised): a 108 x 30 x 28 mm block with R 2.5 edges, a face with a cup and the firing-pin hole, the ejection
    channel on the right, the stem seat and the spring recess; the extractor claw (bright) on the right of the face. The top
    handle: a stem through the cover slot and the T head. Returns [(object, id)]."""
    parts = []
    body = bx(90.0, 197.4, -15.0, 15.0, -14.0, 14.0, bevel=2.6, seg=3, name="BoltBody")
    W.cut(body, lt([(196.4, 0.0), (196.4, 5.6), (200.0, 5.6), (200.0, 0.0)], 40, name="FaceCup"))
    W.cut(body, bx(150.0, 199.0, -16.0, -10.0, 2.0, 11.0, bevel=0.0, name="EjectChannel"))
    W.cut(body, lt([(88.0, 0.0), (88.0, 6.5), (108.0, 6.5), (108.0, 0.0)], 40, name="SpringRecess"))
    W.cut(body, bx(100.0, 140.0, -5.0, 5.0, 10.0, 16.0, bevel=0.0, name="TopRelief"))
    W.round_edges(body, 0.35 * MM, 1, 50)
    parts.append((body, INNER))
    pin = lt([(195.0, 0.0), (195.0, 1.1), (197.6, 1.1), (197.6, 0.0)], 16, name="FiringPin", fillet=0.2)
    parts.append((pin, BRIGHT))
    facering = lt([(196.2, 5.0), (196.2, 5.6), (197.2, 5.6), (197.2, 5.0)], 40, name="FaceLip", closed=True)
    parts.append((facering, BRIGHT))
    ext = pr([(178.0, 3.8), (197.3, 3.8), (197.3, 5.0), (196.6, 7.4), (178.0, 7.4)], -14.6, -10.2, "Y", bevel=0.35, seg=1, fillet=0.7,
             name="Extractor")
    parts.append((ext, BRIGHT))
    stem = pr([(92.0, 13.0), (104.0, 13.0), (104.0, 39.5), (92.0, 39.5)], -2.9, 2.9, "Y", bevel=0.5, seg=1, fillet=1.2, name="Stem")
    parts.append((stem, BLACK))
    head = pr([(80.0, 38.0), (104.0, 38.0), (104.0, 48.0), (80.0, 48.0)], -9.5, 9.5, "Y", bevel=1.3, seg=3, fillet=2.5, name="THead")
    cuts = []
    for k in range(4):                                             # grip ribs across the rear of the head's top
        cuts.append(bx(81.5 + k * 3.0, 83.0 + k * 3.0, -8.5, 8.5, 47.2, 49.0, bevel=0.0, name="HeadGroove"))
    S.cut_many(head, cuts)
    W.round_edges(head, 0.3 * MM, 1, 50)
    parts.append((head, BLACK))
    parts.append((W.pin_head((98.0 * MM, 2.9 * MM, 26.0 * MM), "Y", r=0.0016, h=0.0007, sign=1, slot=False, seg=14), BRIGHT))
    return parts


# ----------------------------------------------------------------------------------------------- selector

def build_selector():
    """Left-flank selector lever, pivot (45, 22.5, -14): a 2.6 mm stamped arm reaching forward to a ribbed thumb pad, a
    slotted pivot screw. 0 / +14 / +28 deg about +Y = S / 1 / A (legends on the receiver)."""
    px, pz = 45.0, -14.0
    outline = [(px - 5.5, pz), (px - 3.8, pz - 4.8), (px, pz - 6.2), (px + 8.0, pz - 4.2), (px + 20.0, pz - 4.0), (px + 27.0, pz - 4.2),
               (px + 29.0, pz - 2.0), (px + 29.0, pz + 2.0), (px + 27.0, pz + 4.2), (px + 20.0, pz + 4.0), (px + 8.0, pz + 4.2),
               (px, pz + 6.2), (px - 3.8, pz + 4.8)]
    arm = pr(outline, 22.45, 25.05, "Y", bevel=0.3, seg=1, fillet=1.6, name="Lever")
    ribs = []
    for k in range(4):
        xr = px + 19.0 + k * 3.0
        ribs.append(bx(xr - 0.7, xr + 0.7, 24.9, 25.55, pz - 3.4, pz + 3.4, bevel=0.3, seg=1, name="PadRib"))
    scr = W.pin_head((px * MM, 25.0 * MM, pz * MM), "Y", r=0.0030, h=0.00065, sign=1, slot=True, seg=20)
    return geo.join([arm, scr] + ribs, "Selector")


# ----------------------------------------------------------------------------------------------- wire stock

STOCK_Y = 29.0
WIRES = (14.0, -18.0)


def build_hinge_body():
    """The fixed half of the stock hinge on the receiver's left rear corner (bone body): a stamped bracket plate, two ears and
    the vertical pin with its domed heads, a spring detent button."""
    out = []
    out.append(pr([(3.0, -27.0), (17.0, -27.0), (17.0, 21.0), (3.0, 21.0)], 22.0, 24.4, "Y", bevel=0.4, seg=1, fillet=2.2, name="Bracket"))
    for z0, z1 in ((18.4, 20.8), (-26.8, -24.4)):
        out.append(pr([(-4.4, 22.0), (9.0, 22.0), (9.0, 33.0), (-4.4, 33.0)], z0, z1, "Z", bevel=0.35, seg=1, fillet=4.0, name="HingeEar"))
    pin = lt([(-28.2, 0.0), (-28.2, 2.4), (-27.2, 3.2), (-26.8, 2.1), (20.8, 2.1), (21.4, 3.2), (22.4, 2.8), (22.8, 0.0)], 24, axis="Z",
             at=(0.0, 28.5, 0.0), name="HingePin", fillet=0.3)
    out.append(pin)
    out.append(W.pin_head((10.0 * MM, 24.4 * MM, 14.0 * MM), "Y", r=0.0024, h=0.0009, sign=1, slot=False, seg=16))
    out.append(W.pin_head((10.0 * MM, 24.4 * MM, -20.0 * MM), "Y", r=0.0024, h=0.0009, sign=1, slot=False, seg=16))
    return out


def wire(z, x0, x1, r=2.75):
    path = [(x0 * MM, STOCK_Y * MM, z * MM), (x1 * MM, STOCK_Y * MM, z * MM)]
    return geo.pipe(path, radius=r * MM, segments=14, cap=True, name="Wire")


def build_stock():
    """The U-frame (bone stock, rest = folded along the left flank): two 5.5 mm wires at Z +14 / -18 from hollow knuckles on
    the hinge pin to the butt plate near the shroud, a cross wire, the butt plate with two lightening slots. Returns the
    list of objects (all ZINC)."""
    out = []
    for z in WIRES:
        out.append(wire(z, 3.4, 247.0))
        k = lt([(z - 4.0, 2.6), (z - 4.0, 4.4), (z + 4.0, 4.4), (z + 4.0, 2.6)], 28, axis="Z", at=(0.0, 28.5, 0.0), name="Knuckle",
               closed=True, fillet=0.4)
        out.append(k)
    out.append(geo.pipe([(150.0 * MM, STOCK_Y * MM, (WIRES[1] - 1.0) * MM), (150.0 * MM, STOCK_Y * MM, (WIRES[0] + 1.0) * MM)],
                        radius=0.0020, segments=12, cap=True, name="CrossWire"))
    plate = pr([(24.4, -34.0), (42.4, -34.0), (42.4, 36.0), (24.4, 36.0)], 243.0, 249.5, "X", bevel=0.9, seg=2, fillet=5.0, name="ButtPlate")
    S.cut_many(plate, [pr([(29.0, -22.0), (38.0, -22.0), (38.0, -8.0), (29.0, -8.0)], 240.0, 253.0, "X", bevel=0.0, fillet=3.0, name="LSlot1"),
                       pr([(29.0, 4.0), (38.0, 4.0), (38.0, 20.0), (29.0, 20.0)], 240.0, 253.0, "X", bevel=0.0, fillet=3.0, name="LSlot2")])
    W.round_edges(plate, 0.3 * MM, 1, 50)
    out.append(plate)
    return out


# ----------------------------------------------------------------------------------------------- strap wrap

def arc_pts(r, a0, a1, n):
    """(y, z) points on a circle: angle a (deg) from +Z toward -Y (the right side), as rot_x does."""
    a = np.radians(np.linspace(a0, a1, n))
    return [(-r * math.sin(t), r * math.cos(t)) for t in a]


def build_wrap():
    """The tan strap wrap round the shroud, X 290..350, 2 mm thick (R 25.5..27.5), with the overlapping tail (a 1.8 mm layer on
    the right side, from 28 to 112 deg) and the stitched box that holds it: modelled, not a decal."""
    out = []
    ring = lt([(290.0, 25.5), (290.0, 26.9), (290.6, 27.5), (349.4, 27.5), (350.0, 26.9), (350.0, 25.5)], 72, name="Wrap", closed=True)
    out.append(ring)
    outer = arc_pts(29.3, 28.0, 112.0, 28)
    inner = arc_pts(27.3, 112.0, 28.0, 28)
    tail = pr(outer + inner, 296.0, 344.0, "X", bevel=0.6, seg=2, name="WrapTail", corner=25.0)
    out.append(tail)
    st = []
    r = 29.3
    a0, a1 = 38.0, 102.0
    for k in range(13):                                          # stitches along the two long edges (axial direction)
        x = 300.5 + k * 3.2
        for a in (a0, a1):
            s = bx(x - 1.4, x + 1.4, -0.45, 0.45, r - 0.2, r + 0.45, bevel=0.25, seg=1, name="Stitch")
            rot_x(s, a)
            st.append(s)
    for k in range(7):                                           # and along the two short edges (tangential direction)
        a = a0 + 4.0 + k * (a1 - a0 - 8.0) / 6.0
        for x in (300.5, 300.5 + 12 * 3.2):
            s = bx(x - 0.45, x + 0.45, -1.4, 1.4, r - 0.2, r + 0.45, bevel=0.25, seg=1, name="StitchT")
            rot_x(s, a)
            st.append(s)
    out.append(joined(st, "Stitches"))
    return out


# ----------------------------------------------------------------------------------------------- details

def build_sling():
    """Sling plate at the rear top-left (stamped, a 14 x 3.6 slot) with two rivets."""
    plate = pr([(8.0, 17.0), (34.0, 17.0), (34.0, 28.0), (8.0, 28.0)], 22.0, 23.8, "Y", bevel=0.4, seg=1, fillet=3.5, name="SlingPlate")
    W.cut(plate, pr([(14.0, 20.0), (28.0, 20.0), (28.0, 24.0), (14.0, 24.0)], 20.0, 26.0, "Y", bevel=0, fillet=1.9, name="SlingSlot"))
    out = [plate]
    for x in (11.5, 30.5):
        out.append(W.pin_head((x * MM, 23.8 * MM, 22.5 * MM), "Y", r=0.0019, h=0.0008, sign=1, slot=False, seg=14))
    return out


def build_front_stud():
    """A sling stud on the shroud's nose ring, underneath."""
    return lt([(-27.0, 0.0), (-27.0, 3.4), (-29.5, 3.4), (-29.5, 2.4), (-31.5, 2.4), (-32.2, 3.2), (-33.4, 3.2), (-33.4, 0.0)], 24,
              axis="Z", at=(404.0, 0.0, 0.0), name="Stud", fillet=0.25)


def build_catch():
    """Magazine catch button on the right of the well and its screw."""
    b = lt([(17.0, 0.0), (17.0, 5.8), (18.0, 6.0), (20.4, 6.0), (21.0, 5.4), (21.0, 0.0)], 32, axis="Y", at=(148.0, 0.0, -58.0), name="Catch",
           fillet=0.3)
    geo.transform(b, scale=(1, -1, 1))
    return b


def build_rivets():
    out = []
    for side in (-1, 1):
        for x, z in ((262.0, -34.0), (262.0, -6.0), (262.0, 19.0)):
            out.append(W.rivet((x * MM, 22.0 * side * MM, z * MM), "Y", r=0.0023, h=0.0009, sign=side, seg=14))
    for x, z in ((8.0, -34.0), (8.0, 20.0)):
        out.append(W.rivet((x * MM, -22.0 * MM, z * MM), "Y", r=0.0023, h=0.0009, sign=-1, seg=14))
    return out


def build_flange_screws():
    """Four socket-head screws round the shroud's rear flange (face X 277.5): R 1.9 heads with a round recess."""
    out = []
    for k in range(4):
        a = 45.0 + 90.0 * k
        c = lt([(277.0, 0.0), (277.0, 1.8), (278.0, 1.9), (279.4, 1.9), (279.4, 0.9), (278.6, 0.9), (278.6, 0.0)], 20, name="FlangeScrew",
               fillet=0.15)
        tr(c, loc=(0.0, 0.0, 25.4))
        out.append(rot_x(c, a))
    return out


# ----------------------------------------------------------------------------------------------- magazine

def build_magazine(col):
    """SM_Weapon_RattlerMagazine (+ _TopRound): 30 x 42 mm straight stamped stick, 182 mm from the feed lips (MagHinge, Z -32) to
    the floor (Z -214) = 32 rounds, two stamped ribs per side and a spine seam, folded feed lips, a deep pocket with the stack
    visible, a black floor plate with a drag tab. In place (origin = gun origin)."""
    X0, X1, HW = 145.0, 187.0, 15.0
    zs = [-214.0 + 5.2, -208.5] + list(np.linspace(-204.0, -62.0, 14)) + [-60.0, -50.0, -40.0, -36.0, -34.0, -33.0, -32.4, -32.0]
    zs = sorted(set(np.round(zs, 4)))
    secs = [K.rrect(X0 * MM, X1 * MM, HW * MM, 2.4 * MM, 2.4 * MM) for _z in zs]
    body = K.loft_z(secs, [z * MM for z in zs], 44, name="MagBody")
    W.cut(body, bx(146.6, 185.4, -13.4, 13.4, -60.5, -31.0, bevel=0.5, name="MagPocket"))
    parts = [("body", body, MAGSTEEL)]
    for xr in (156.0, 176.0):                                        # two stamped ribs per side along the stick
        for side in (-1, 1):
            y0, y1 = (HW - 0.6, HW + 0.9)
            if side < 0:
                y0, y1 = -y1, -y0
            parts.append(("rib", pr([(xr - 2.2, -200.0), (xr + 2.2, -200.0), (xr + 2.2, -78.0), (xr - 2.2, -78.0)], y0, y1, "Y", bevel=0.8,
                                    seg=2, fillet=2.1, name="MagRib"), MAGSTEEL))
    parts.append(("seam", bx(143.9, 146.0, -1.0, 1.0, -202.0, -44.0, bevel=0.55, seg=2, name="MagSeam"), MAGSTEEL))
    for side in (-1, 1):                                             # feed lips: the long walls turned in over the stack
        sgn = float(side)
        lip = pr([(sgn * 15.0, -39.0), (sgn * 15.0, -31.6), (sgn * 11.6, -31.6), (sgn * 11.6, -33.3), (sgn * 13.4, -33.3),
                  (sgn * 13.4, -39.0)], 147.0, 185.0, "X", bevel=0.3, seg=1, name="Lip")
        parts.append(("lip", lip, MAGSTEEL))
    fol = pr([(147.0, -60.0), (185.0, -60.0), (185.0, -57.0), (166.0, -55.5), (147.0, -57.0)], -12.8, 12.8, "Y", bevel=0.5, seg=1,
             fillet=0.8, name="Follower")
    parts.append(("follower", fol, S.POLY))
    plate = bx(142.8, 189.2, -16.4, 16.4, -214.0, -208.6, bevel=1.6, seg=2, name="Floor")
    tab = bx(188.0, 200.0, -5.5, 5.5, -214.0, -210.6, bevel=1.0, seg=2, name="Drag")
    plate = geo.join([plate, tab], "FloorPlate")
    parts.append(("floor", plate, S.POLY))
    made = []
    for name, ob, mid in parts:
        made.append(S.finish(ob, mid, None))
    rd = 0.00496
    sec = W.cartridge(0.0297, rd, name="Round2", rifle=False, seg=28)
    geo.transform(sec, loc=(0.1500, -0.0050, -0.0422))
    third = W.cartridge(0.0297, rd, name="Round3", rifle=False, seg=28)
    geo.transform(third, loc=(0.1500, 0.0050, -0.0512))
    made += [sec, third]
    top = W.cartridge(0.0297, rd, name="TopRound", rifle=False, seg=28)
    geo.transform(top, loc=(0.1500, 0.0050, -0.0379))
    mag = geo.join(made, "SM_Weapon_RattlerMagazine", col)
    from mi import scene as _sc
    _sc.move_to(top, col)
    top.name = top.data.name = "SM_Weapon_RattlerMagazine_TopRound"
    return mag, top


# ----------------------------------------------------------------------------------------------- the gun

BONES = [("body", (0.0, 0.0, 0.0), None, True),
         ("bolt", S.RT["bolt_head"], "body", True),
         ("trigger", S.RT["trigger_pivot"], "body", True),
         ("selector", S.RT["selector_pivot"], "body", True),
         ("magazine", (0.0, 0.0, 0.0), "body", True),
         ("stock", S.RT["stock_hinge"], "body", True),
         ("MuzzleDevice", S.RT["muzzle_head"], "body", True),
         ("IronsFront", S.RT["irons_front_head"], "body", True),
         ("IronsRear", S.RT["irons_rear_head"], "body", True)]


def expand(box, e=0.3):
    x0, x1, y0, y1, z0, z1 = box
    return (x0 - e, x1 + e, y0 - e, y1 + e, z0 - e, z1 + e)


def rattler_parts():
    """Every part of the gun, finished (material id, rigid bone): a list of objects ready to join."""
    P = S.finish
    out = []
    rec = P(S.build_receiver(), SHEET, "body")
    S.inside_boxes(rec, S.rec_interior_boxes(), INNER)
    out.append(rec)
    out.append(P(joined(S.build_ribs(), "Ribs"), SHEET, "body"))
    out.append(P(joined(S.build_welds(), "Welds"), SHEET, "body"))
    out.append(P(joined(S.build_seam(), "Seams"), SHEET, "body"))
    out.append(P(S.build_rail(), SHEET, "body"))
    out.append(P(joined(S.build_rail_bed(), "RailBed"), SHEET, "body"))
    out.append(P(S.build_rear_cap(), SHEET, "body"))
    out.append(P(W.pin_head((-2.2 * MM, 0.0, 0.0), "X", r=0.0034, h=0.0012, sign=-1, slot=True), BLACK, "body"))
    out.append(P(S.build_well(), SHEET, "body"))
    out.append(P(joined(S.build_rear_frame(), "RearFrame"), SHEET, "body"))
    out.append(P(S.build_port_frame(), SHEET, "body"))
    out.append(P(S.build_takedown(), BLACK, "body"))
    out.append(P(S.build_shroud(), BLACK, "body"))
    barrel = P(S.build_barrel(), BLACK, "body")
    S.inside_boxes(barrel, [(197.0, 425.0, -4.6, 4.6, -4.6, 4.6)], BORE)
    S.inside_boxes(barrel, [(197.0, 270.5, -14.0, 14.0, -14.0, 14.0)], INNER)
    out.append(barrel)
    dev = P(S.build_device(), BLACK, "MuzzleDevice")
    S.inside_boxes(dev, [(409.0, 466.0, -7.3, 7.3, -7.3, 7.3)], BORE)
    out.append(dev)
    for t in S.build_front_sight():
        out.append(P(t, BLACK, "IronsFront"))
    out.append(P(joined(S.build_rear_base(), "RearBase"), BLACK, "body"))
    for t in S.build_rear_leaf():
        out.append(P(t, BLACK, "IronsRear"))
    out.append(P(build_grip(), POLY, "body"))
    for t in build_grip_hardware():
        out.append(P(t, BLACK, "body"))
    out.append(P(build_guard(), SHEET, "body"))
    out.append(P(build_trigger(), BLACK, "trigger"))
    out.append(P(joined(build_trigger_bracket(), "Hanger"), BLACK, "body"))
    for ob, mid in build_bolt():
        out.append(P(ob, mid, "bolt"))
    out.append(P(build_selector(), BLACK, "selector"))
    out.append(P(joined(build_hinge_body(), "Hinge"), BLACK, "body"))
    for ob in build_stock():
        out.append(P(ob, ZINC, "stock"))
    wr = build_wrap()
    for ob in wr:
        out.append(P(ob, STRAP, "body"))
    out.append(P(joined(build_sling(), "Sling"), BLACK, "body"))
    out.append(P(build_front_stud(), BLACK, "body"))
    out.append(P(build_catch(), BLACK, "body"))
    out.append(P(joined(build_rivets(), "Rivets"), SHEET, "body"))
    out.append(P(joined(build_flange_screws(), "FlangeScrews"), BLACK, "body"))
    return out


def rattler_build(ctx):
    parts = rattler_parts()
    gun = geo.join(parts, "SK_Rattler", ctx.col)
    bones = [rig.Bone(n, h, p, d) for n, h, p, d in BONES]
    bones += [rig.Bone(k, v, "body", deform=False) for k, v in S.RT["sockets"].items()]
    arm = rig.armature("SKEL_Rattler", bones, ctx.col)
    rig.bind(gun, arm)
    return gun, arm
