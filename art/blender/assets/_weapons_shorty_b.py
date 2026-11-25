"""SHORTY, second half: pistol grip, trigger group, the moving parts (bolt with its left charging handle, trigger,
selector), the moulded details (ribs, screws, pins, the shell deflector, sling points, the magazine release), the
magazine with its top round, and the rig. See _weapons_shorty.py for the contract and the big solids.
"""
import math

import numpy as np

from mi import geo, rig, scene
from assets import weapons as W
from assets import _weapons_kit as K
from assets import _weapons_shorty as S

MM = S.MM
bx, pr, lt, tr = S.bx, S.pr, S.lt, S.tr
OLIVE, PARK, BRIGHT, RUBBER, BORE, TRIT, WHITE = S.OLIVE, S.PARK, S.BRIGHT, S.RUBBER, S.BORE, S.TRIT, S.WHITE
BRASS, COPPER, PRIMER, MAGSTEEL = S.BRASS, S.COPPER, S.PRIMER, S.MAGSTEEL

# ----------------------------------------------------------------------------------------------- pistol grip

GBACK = K.spline([(296.0, -48.0), (290.0, -55.0), (274.0, -95.0), (254.0, -170.0), (253.2, -172.5)], 10)
GFRONT = K.spline([(348.0, -48.0), (342.0, -55.0), (316.0, -95.0), (292.0, -172.5)], 10)
GRIP_TOP, GRIP_BOT = -48.0, -172.5
GROOVES = (-86.0, -101.0, -116.0)          # finger grooves in the front strap: centre Z, 7.2 mm tall, 1.7 mm deep


def groove(z):
    g = 0.0
    for zg in GROOVES:
        d = abs(z - zg)
        if d < 3.6:
            g += 1.7 * 0.5 * (1.0 + math.cos(math.pi * d / 3.6))
    return g


def grip_half_width(z):
    return float(np.interp(z, [-172.5, -95.0, -55.0, -48.0], [14.2, 15.3, 15.9, 16.2]))


def grip_section(z, d=0.0):
    """Egg section (mm -> m): 42 deep and 33 wide at palm height (15.3 half width + the 1.2 mm palm swell), round at the
    back, flatter at the front with the finger grooves; d insets the section (rounded base)."""
    xb = float(K.x_of_z(GBACK, z)) + d
    xf = float(K.x_of_z(GFRONT, z)) - groove(z) - d
    w = grip_half_width(z) - d
    crown = 1.2 * math.exp(-((z + 95.0) / 20.0) ** 2)
    return K.rrect(xb * MM, xf * MM, w * MM, min(w * 0.97, 12.0) * MM, 6.5 * MM, bulge_f=0.4 * MM, crown=crown * MM)


def grip_levels():
    zs = list(np.arange(GRIP_TOP, GRIP_BOT, -3.0))
    for zg in GROOVES:
        zs += list(zg + 3.6 * np.linspace(-1.0, 1.0, 11))
    for k in range(1, 6):
        zs.append(GRIP_BOT + 3.0 * (1.0 - math.cos(k / 5.0 * math.pi / 2.0)))
    zs.append(GRIP_BOT)
    zs = np.array(sorted(set(np.round(zs, 4)), reverse=True))
    return zs[(zs <= GRIP_TOP) & (zs >= GRIP_BOT)]


def build_grip():
    """Pistol grip hanging from the middle of the gun, raked 17 degrees, 33 wide: horizontal sections lofted down the
    rake with a palm swell, three finger grooves in the front strap, a rounded base with a grip-screw recess and the
    4 mm lanyard hole through the heel."""
    zs = grip_levels()
    secs = []
    for z in zs:
        e = z - GRIP_BOT
        d = 0.0
        if e < 3.0:
            d = 3.0 - math.sqrt(max(0.0, 3.0 ** 2 - (3.0 - e) ** 2))
        secs.append(grip_section(float(z), d))
    g = K.loft_z(secs, zs * MM, 56, name="Grip")
    xh = float(K.x_of_z(GBACK, -161.0)) + 7.0
    W.cut(g, lt([(-30, 0), (-30, 2.0), (30, 2.0), (30, 0)], 20, axis="Y", at=(xh, 0.0, -161.0), name="Lanyard"))
    xm = 0.5 * (float(K.x_of_z(GBACK, GRIP_BOT)) + float(K.x_of_z(GFRONT, GRIP_BOT)))
    W.cut(g, lt([(-173.7, 0), (-173.7, 6.2), (-171.9, 6.2), (-171.9, 0)], 40, axis="Z", at=(xm, 0.0, 0.0), name="CapRecess"))
    W.round_edges(g, 0.3 * MM, 1, 60)
    return g


def build_grip_screw():
    xm = 0.5 * (float(K.x_of_z(GBACK, GRIP_BOT)) + float(K.x_of_z(GFRONT, GRIP_BOT)))
    return W.pin_head((xm * MM, 0.0, (GRIP_BOT - 0.15) * MM), "Z", r=0.0034, h=0.0012, sign=-1, slot=True)


# ----------------------------------------------------------------------------------------------- guard and trigger

def d_profile(a, b, p=3.0, M=28):
    pts = K.superellipse(a * MM, b * MM, p, M)
    return pts


def build_guard():
    """Polymer trigger guard: an 8 x 5 mm D section from the grip's front strap along the bottom (Z -100) and up the
    front at X 440 into the forend."""
    path = [(306.0, 0.0, -97.5), (437.5, 0.0, -97.5), (437.5, 0.0, -38.0)]
    pts = geo.fillet([(x * MM, y * MM, z * MM) for x, y, z in path], 13.0 * MM, 9)
    prof = d_profile(2.5, 4.0)
    return K.sweep_var(pts, lambda i, t: prof, name="Guard", cap=True, up=(0.0, 1.0, 0.0))


def trigger_blade_x(z):
    """Centre line of the curved blade (mm): its rear face is X 368.0 at Z -70 (73 mm ahead of Palm_R)."""
    return 370.632 - 0.033 * (z + 68.0) ** 2


def build_trigger():
    """Curved steel blade (5 x 7 mm) hanging from a hub on the pivot (362, 0, -50); pull = +17 deg about +Y."""
    zs = np.linspace(-51.0, -82.0, 20)
    path = [(trigger_blade_x(z) * MM, 0.0, z * MM) for z in zs]
    base = K.superellipse(2.5 * MM, 3.5 * MM, 3.0, 24)

    def prof(i, t):
        s = 1.0 - 0.30 * float(K.smoothstep(t, 0.82, 1.0))
        return base * np.array([s, 1.0])
    blade = K.sweep_var(path, prof, name="Blade", cap=True, up=(0.0, 1.0, 0.0))
    hub = lt([(-3.5, 0), (-3.5, 4.6), (3.5, 4.6), (3.5, 0)], 32, axis="Y", at=(362.0, 0.0, -50.0), name="Hub", fillet=0.4)
    return geo.join([blade, hub], "Trigger")


# ----------------------------------------------------------------------------------------------- bolt

def build_bolt():
    """Bolt carrier (parkerised) with a lightening port, the bright bolt head with a recessed face and firing-pin hole,
    the extractor claw on the right, the charging-handle stem through the left slot and its knob (Y to +40)."""
    parts = []
    car = pr([(300, -6), (388, -6), (388, 24), (300, 24)], -13.0, 13.0, "Y", bevel=0.8, seg=2, fillet=2.5, name="Carrier")
    W.cut(car, pr([(316, 4), (346, 4), (346, 18), (316, 18)], -20.0, 20.0, "Y", bevel=0, fillet=4.0, name="Lighten"))
    W.cut(car, pr([(354, 9), (376, 9), (376, 21), (354, 21)], -20.0, -12.0, "Y", bevel=0, fillet=2.0, name="CamPocket"))
    W.round_edges(car, 0.3 * MM, 1, 50)
    parts.append(("carrier", car, PARK))
    head = lt([(386.0, 0.0), (386.0, 7.0), (394.0, 7.0), (395.0, 6.0), (395.0, 1.35), (393.0, 1.35), (393.0, 0.0)], 40,
              name="BoltHead", fillet=0.25)
    parts.append(("head", head, BRIGHT))
    ext = pr([(384, 0.5), (395.5, 0.5), (396.0, 2.5), (394.5, 5.5), (384, 5.5)], -10.6, -7.0, "Y", bevel=0.35, seg=1,
             fillet=0.6, name="Extractor")
    parts.append(("extractor", ext, BRIGHT))
    stem = pr([(377, 9), (383, 9), (383, 15), (377, 15)], 10.0, 33.5, "Y", bevel=0.5, fillet=1.6, name="Stem")
    parts.append(("stem", stem, PARK))
    knob = lt([(33.0, 0.0), (33.0, 4.2), (34.2, 5.6), (36.0, 6.0), (38.0, 6.0), (39.4, 5.2), (40.0, 3.8), (40.0, 0.0)], 40,
              axis="Y", at=(380.0, 0.0, 12.0), name="Knob", fillet=0.3)
    parts.append(("knob", knob, PARK))
    return parts


# ----------------------------------------------------------------------------------------------- selector

def build_selector():
    """Left-flank selector lever, pivot (300, 28.5, -22): a 3 mm stamped arm reaching back with a ribbed thumb pad and a
    slotted pivot screw. 0 / +14 / +28 deg about +Y = SAFE / SEMI / AUTO (the legends are on the body)."""
    px, pz = 300.0, -22.0
    arm = pr([(px + 0.0, pz + 5.8), (px - 12.0, pz + 3.8), (px - 21.0, pz + 4.4), (px - 26.5, pz + 2.6), (px - 26.5, pz - 2.6),
              (px - 21.0, pz - 4.4), (px - 12.0, pz - 3.2), (px + 0.0, pz - 5.8), (px + 4.0, pz - 3.0), (px + 4.0, pz + 3.0)],
             28.8, 31.6, "Y", bevel=0.35, seg=2, fillet=1.4, name="Lever")
    hub = lt([(28.8, 0.0), (28.8, 6.6), (31.9, 6.6), (31.9, 0.0)], 36, axis="Y", at=(px, 0.0, pz), name="LeverHub", fillet=0.5)
    pad = pr([(px - 26.5, pz + 3.4), (px - 17.0, pz + 3.4), (px - 17.0, pz - 3.4), (px - 26.5, pz - 3.4)], 31.2, 34.3, "Y",
             bevel=0.4, seg=1, fillet=1.2, name="ThumbPad")
    for k in range(4):                                     # ribs across the pad
        xr = px - 25.0 + k * 2.4
        W.cut(pad, bx(xr - 0.5, xr + 0.5, 33.8, 36.0, pz - 4.0, pz + 4.0))
    scr = W.pin_head((px * MM, 31.8 * MM, pz * MM), "Y", r=0.0032, h=0.0013, sign=1, slot=True)
    return geo.join([arm, hub, pad, scr], "Selector")


# ----------------------------------------------------------------------------------------------- details

RIGHT_SCREWS = [(58, 41), (58, -51), (176, 43), (172, -55), (252, 38), (332, -55)]
LEFT_SCREWS = [(58, 41), (58, -51), (176, 43), (172, -55), (252, 38), (346, 34)]


def screws(points, side, r=2.8, h=1.1):
    out = []
    for x, z in points:
        y = 28.0 * side
        out.append(W.pin_head((x * MM, y * MM, z * MM), "Y", r=r * MM, h=h * MM, sign=side, slot=True, seg=20))
    return out


def ribs():
    """Moulded ribs, 1.5 mm proud: six vertical ribs on the rear flank panels and three horizontal ones under the port."""
    out = []
    for side in (-1, 1):
        for x in (52.0, 60.0, 68.0, 76.0, 84.0, 92.0):
            y0, y1 = (28.0 - 0.6, 28.0 + 1.5)
            if side < 0:
                y0, y1 = -y1, -y0
            out.append(bx(x - 1.3, x + 1.3, y0, y1, -44.0, 34.0, bevel=0.45, seg=2, name="Rib"))
    for z in (-52.0, -47.0, -42.0):
        for side in (-1, 1):
            y0, y1 = (28.0 - 0.6, 28.0 + 1.2)
            if side < 0:
                y0, y1 = -y1, -y0
            out.append(bx(262.0, 334.0, y0, y1, z - 1.1, z + 1.1, bevel=0.4, seg=2, name="RibH"))
    return out


def build_deflector():
    """The shell deflector: a moulded polymer vane on the right of the ejection port, X 400..470, standing 16 mm off
    the flank, swept 30 degrees toward the muzzle at its root and rolled at the tip; it throws brass forward and right."""
    cl = np.array([(400.0, -30.6), (404.0, -32.2), (410.0, -34.8), (418.0, -37.6), (428.0, -39.4), (440.0, -40.1),
                   (456.0, -40.3), (468.0, -40.0)])
    t = np.gradient(cl, axis=0)
    t /= np.linalg.norm(t, axis=1, keepdims=True)
    n = np.stack([-t[:, 1], t[:, 0]], 1)
    th = 1.5
    outline = list(map(tuple, cl + n * th)) + list(map(tuple, (cl - n * th)[::-1]))
    vane = pr(outline, -3.0, 37.0, "Z", bevel=0.9, seg=2, fillet=0.0, name="Vane")
    geo.set_verts(vane, _slope_top(geo.arrays(vane)[0] / MM) * MM)
    roll = lt([(-3.0, 0), (-3.0, 3.0), (26.0, 3.0), (26.0, 0)], 28, axis="Z", at=(468.0, -40.0, 0.0), name="VaneRoll",
              fillet=0.6)
    return geo.join([vane, roll], "Deflector")


def _slope_top(co):
    """The vane's top edge falls from Z 37 at the root to Z 26 at the rolled tip."""
    s = K.smoothstep(co[:, 0], 412.0, 466.0)
    up = co[:, 2] > 8.0
    co[:, 2] = np.where(up, 8.0 + (co[:, 2] - 8.0) * (1.0 - 0.38 * s), co[:, 2])
    return co


def build_sling():
    """Sling points: a stamped steel slot plate on the left flank behind the grip's reach and a stud on the forend."""
    parts = []
    plate = pr([(96, -48), (120, -48), (120, -37), (96, -37)], 28.0, 30.4, "Y", bevel=0.45, seg=2, fillet=3.0, name="SlingPlate")
    W.cut(plate, pr([(101, -44.5), (115, -44.5), (115, -40.5), (101, -40.5)], 26.0, 33.0, "Y", bevel=0, fillet=1.9, name="SlingSlot"))
    parts.append(plate)
    for x in (98.5, 117.5):
        parts.append(W.pin_head((x * MM, 30.2 * MM, -42.5 * MM), "Y", r=0.0017, h=0.0008, sign=1, slot=False, seg=14))
    stud = lt([(31.0, 0.0), (31.0, 3.6), (32.0, 3.6), (32.0, 2.6), (34.5, 2.6), (35.2, 3.4), (36.4, 3.4), (36.4, 0.0)], 28,
              axis="Y", at=(548.0, 0.0, -12.0), name="Stud", fillet=0.25)
    parts.append(stud)
    return geo.join(parts, "Sling")


def build_release():
    """Magazine release button on the right flank in front of the well."""
    b = lt([(27.4, 0.0), (27.4, 5.4), (28.4, 5.6), (30.2, 5.6), (30.8, 5.0), (30.8, 0.0)], 36, axis="Y", at=(244.0, 0.0, -43.0),
           name="Release", fillet=0.3)
    geo.transform(b, scale=(1, -1, 1))
    return b


def build_pins():
    out = []
    for side in (-1, 1):
        out.append(W.pin_head((362.0 * MM, 28.0 * side * MM, -50.0 * MM), "Y", r=0.0026, h=0.0010, sign=side, slot=False, seg=18))
    return out


# ----------------------------------------------------------------------------------------------- magazine

def cartridge(name, length=45.0, r=5.0):
    """Our own 5.6 mm-class round (mm): rimless case with a neck, jacketed pointed bullet, primer. Axis +X from the base."""
    case = [(0.0, 0.0), (0.0, r * 0.97), (0.7, r), (1.3, r), (1.6, r * 0.84), (2.6, r * 0.84), (3.3, r * 0.99), (19.0, r * 0.93),
            (22.5, r * 0.68), (28.0, r * 0.62), (28.0, 0.0)]
    bul = [(25.5, 0.0), (25.5, r * 0.56), (29.0, r * 0.57), (length - 8.0, r * 0.57), (length - 2.4, r * 0.30), (length, 0.0)]
    pri = [(-0.15, 0.0), (-0.15, r * 0.40), (0.6, r * 0.40), (0.6, 0.0)]
    c = lt(case, 36, name=name, fillet=0.2)
    b = lt(bul, 36, name=name + "B", fillet=0.15)
    p = lt(pri, 20, name=name + "P")
    return c, b, p


def build_magazine(col):
    """SM_Weapon_ShortyMagazine (+ _TopRound): 24 x 48 mm straight stamped box, 160 mm from the feed lips (MagHinge,
    Z -20) to the floor plate (Z -180) = 30 rounds, feed lips, follower, the second round, an olive floor plate with a
    drag tab. In place (origin = gun origin)."""
    X0, X1, HW = 182.0, 230.0, 12.0
    zs = [-176.0, -175.5, -175.0] + list(np.linspace(-170.0, -24.0, 15)) + [-22.5, -21.6, -20.9, -20.4, -20.1, -20.0]
    secs = [K.rrect(X0 * MM, X1 * MM, HW * MM, 3.0 * MM, 3.0 * MM) for _z in zs]
    body = K.loft_z(secs, [z * MM for z in zs], 40, name="MagBody")
    W.cut(body, bx(183.0, 229.0, -10.8, 10.8, -41.0, -19.0, bevel=0.5, name="MagPocket"))
    parts = [("body", body, MAGSTEEL)]
    for z in (-70.0, -108.0, -146.0):                                        # stamped ribs on both long faces
        for side in (-1, 1):
            y0, y1 = (HW - 0.5, HW + 0.7)
            if side < 0:
                y0, y1 = -y1, -y0
            parts.append(("rib", bx(190.0, 222.0, y0, y1, z - 1.6, z + 1.6, bevel=0.5, name="MagRib"), MAGSTEEL))
    for side in (-1, 1):                                                      # feed lips: tabs turned in over the rounds
        sgn = float(side)
        lip = pr([(sgn * 11.0, -27.0), (sgn * 11.0, -20.0), (sgn * 8.9, -20.0), (sgn * 8.9, -21.9), (sgn * 10.1, -21.9),
                  (sgn * 10.1, -27.0)], 184.0, 228.0, "X", bevel=0.3, seg=1, name="Lip")
        parts.append(("lip", lip, S.PARK))
    fol = pr([(184, -42.5), (228, -42.5), (228, -38.0), (206, -36.0), (184, -38.0)], -10.0, 10.0, "Y", bevel=0.5, seg=1, fillet=0.8,
             name="Follower")
    parts.append(("follower", fol, OLIVE))
    plate = bx(180.0, 232.0, -13.0, 13.0, -180.0, -175.0, bevel=1.2, seg=2, name="Floor")
    tab = bx(170.5, 184.0, -5.5, 5.5, -180.0, -177.4, bevel=0.8, seg=2, name="Drag")
    geo.join([plate, tab], "FloorPlate")
    parts.append(("floor", plate, OLIVE))
    top_c, top_b, top_p = cartridge("TopRound", 45.0, 5.0)
    tr(top_c, loc=(184.0, 3.8, -26.0))
    tr(top_b, loc=(184.0, 3.8, -26.0))
    tr(top_p, loc=(184.0, 3.8, -26.0))
    sec_c, sec_b, sec_p = cartridge("Round2", 45.0, 5.0)
    for o in (sec_c, sec_b, sec_p):
        tr(o, loc=(184.0, -3.8, -34.7))
    made = []
    for name, ob, mid in parts:
        made.append(S.finish(ob, mid, None))
    made += [S.finish(sec_c, BRASS, None), S.finish(sec_b, COPPER, None), S.finish(sec_p, PRIMER, None)]
    mag = geo.join(made, "SM_Weapon_ShortyMagazine", col)
    top = [S.finish(top_c, BRASS, None), S.finish(top_b, COPPER, None), S.finish(top_p, PRIMER, None)]
    topj = geo.join(top, "SM_Weapon_ShortyMagazine_TopRound", col)
    return mag, topj


# ----------------------------------------------------------------------------------------------- the gun

BONES = [("body", (0.0, 0.0, 0.0), None, True),
         ("bolt", S.SH["bolt_head"], "body", True),
         ("trigger", S.SH["trigger_pivot"], "body", True),
         ("selector", S.SH["selector_pivot"], "body", True),
         ("magazine", (0.0, 0.0, 0.0), "body", True),
         ("MuzzleDevice", S.SH["muzzle_head"], "body", True),
         ("IronsFront", S.SH["irons_front_head"], "body", True)]


def joined(objs, name):
    objs = [o for o in objs if o is not None]
    return geo.join(objs, name) if len(objs) > 1 else objs[0]


def expand(box, e=0.3):
    x0, x1, y0, y1, z0, z1 = box
    return (x0 - e, x1 + e, y0 - e, y1 + e, z0 - e, z1 + e)


def shorty_parts():
    """Every part of the gun, finished (material id, rigid bone): a list of objects ready to join."""
    P = S.finish
    out = []
    body = P(S.build_body(), OLIVE, "body")
    S.inside_boxes(body, [expand(S.CAV), expand(S.WELL, 0.4), (351.0, 381.0, -5.7, 5.7, -64.2, -40.8)], BORE)
    out.append(body)
    out.append(P(S.build_pad(), RUBBER, "body"))
    hnd, ring = S.build_handle()
    out.append(P(hnd, OLIVE, "body"))
    out.append(P(ring, OLIVE, "body"))
    out.append(P(S.build_rail_top(), PARK, "body"))
    out.append(P(joined(S.build_gussets(), "Gussets"), OLIVE, "body"))
    fore = P(S.build_forend(), OLIVE, "body")
    S.inside_boxes(fore, [(395.0, 584.2, -27.3, 27.3, -36.3, 30.3), expand(S.CAV)], BORE)
    out.append(fore)
    out.append(P(S.build_rail_under(), PARK, "body"))
    out.append(P(S.build_nose_ring(), PARK, "body"))
    out.append(P(S.build_barrel(), PARK, "body"))
    for g in S.build_gas():
        out.append(P(g, PARK, "body"))
    out.append(P(S.build_hider(), PARK, "MuzzleDevice"))
    tower = S.build_front_sight()
    for t in tower:
        out.append(P(t, PARK, "IronsFront"))
    trit = lt([(572.5, 0.0), (572.5, 1.05), (573.4, 1.05), (573.4, 0.0)], 20, axis="X", at=(0.0, 0.0, 55.0), name="Tritium")
    out.append(P(trit, TRIT, "IronsFront"))
    grip = P(build_grip(), OLIVE, "body")
    out.append(grip)
    out.append(P(build_grip_screw(), PARK, "body"))
    out.append(P(build_guard(), OLIVE, "body"))
    out.append(P(build_trigger(), PARK, "trigger"))
    for _n, ob, mid in build_bolt():
        out.append(P(ob, mid, "bolt"))
    out.append(P(build_selector(), PARK, "selector"))
    out.append(P(lt([(27.8, 0.0), (27.8, 9.6), (28.5, 9.6), (28.5, 0.0)], 40, axis="Y", at=(300.0, 0.0, -22.0), name="Washer",
                    fillet=0.2), PARK, "body"))
    out.append(P(joined(ribs(), "Ribs"), OLIVE, "body"))
    out.append(P(joined(screws(RIGHT_SCREWS, -1) + screws(LEFT_SCREWS, 1), "Screws"), PARK, "body"))
    out.append(P(joined(build_pins(), "Pins"), PARK, "body"))
    out.append(P(build_deflector(), OLIVE, "body"))
    out.append(P(build_sling(), PARK, "body"))
    out.append(P(build_release(), PARK, "body"))
    return out


def lt(*a, **k):
    return S.lt(*a, **k)


def shorty_build(ctx):
    parts = shorty_parts()
    gun = geo.join(parts, "SK_Shorty", ctx.col)
    bones = [rig.Bone(n, h, p, d) for n, h, p, d in BONES]
    bones += [rig.Bone(k, v, "body", deform=False) for k, v in S.SH["sockets"].items()]
    arm = rig.armature("SKEL_Shorty", bones, ctx.col)
    rig.bind(gun, arm)
    return gun, arm
