"""NINE, rebuild round 1: the frame as forged/machined parts and lofted sections instead of one extruded outline.

    grip      horizontal sections lofted from the beavertail to the butt: rounded rectangle 23 mm wide (frame), back
              strap convex across (bulge) with a soft S in profile (memory bump under the beavertail, hollow, palm
              hump 60 % down), front strap slightly convex with a 6 mm undercut under the guard; ~52 mm deep at mid
              height. The magazine line keeps its direction (0.250, 0.968) and moves 12 mm back (top round rim just
              behind the breech face), so the front strap can sit 4 mm ahead of the magazine.
    panels    separate shells on the frame sides: 3.4 mm at the crown, wrapping 4.5 mm round the strap corners,
              rounded borders, a relief scallop at the magazine button, countersunk screws in bushings.
    frame     upper frame slab (draft on the sides, frame rails under the slide, hammer ears, beavertail with an
              upturned lip), the trigger web (sections narrowing into the guard), a swept D guard (5.5 x 8 mm,
              squared front), dust cover with a rail (45 deg flanks, three 5.2 mm slots at 0.142, 0.156, 0.170).
    slide     lofted along X: 3 mm top radii, tapered upper flanks, 17 deg nose bevel, seven 1.2 mm deep cuts at
              2 mm pitch, scalloped ejection port, pinned extractor in a slot, closed breech face.
    hammer    9 mm spur with a thumb face, hollowed sides, strut pin.
    magazine  body on the moved line, flat gold base pad following the butt (1 mm overhang, flared front lip).
"""
import math

import numpy as np
from mathutils import Matrix, Vector

from mi import geo
from assets import weapons as W
from assets import _weapons_kit as K

NN = W.NN
P, prism, lathe, box, cut, union, round_edges, pin_head, loft, fix_normals = (
    W.P, W.prism, W.lathe, W.box, W.cut, W.union, W.round_edges, W.pin_head, W.loft, W.fix_normals)
STAINLESS, DARK, BLACKOX, POLYMER, POLISHED, GOLD, BLUED, BORE = (
    W.STAINLESS, W.DARK, W.BLACKOX, W.POLYMER, W.POLISHED, W.GOLD, W.BLUED, W.BORE)

MAG_DX = -0.012                      # the magazine line moves back by this much (direction kept)
A = np.array(NN["mag_axis"], float) / np.linalg.norm(NN["mag_axis"])     # base -> lips
F = np.array([A[2], 0.0, -A[0]])                                       # forward, perpendicular to the axis
BUTT_Z = -0.1275
PAD_Z = -0.1345
FRAME_W = 0.0115                     # grip frame half width (panels add 3.4 mm: 30 mm over the panels)
PANEL_T = 0.0034

# side-view curves (x, z) ------------------------------------------------------------------------------------
# back strap: beavertail underside (web of the hand) -> memory bump -> hollow -> palm hump (60 % down) -> heel
BACK = K.spline([(-0.0330, -0.0128), (-0.0312, -0.0150), (-0.0272, -0.0189), (-0.0226, -0.0238),
                 (-0.0189, -0.0293), (-0.0165, -0.0352), (-0.0161, -0.0400), (-0.0167, -0.0445),
                 (-0.0165, -0.0495), (-0.0175, -0.0570), (-0.0198, -0.0660), (-0.0230, -0.0770),
                 (-0.0258, -0.0870), (-0.0279, -0.0960), (-0.0298, -0.1060), (-0.0314, -0.1150),
                 (-0.0323, -0.1220), (-0.0326, -0.1275)], 10)
# front strap below the guard (slightly convex, ~16 deg rake), the undercut fillet is added in front_x()
FRONT = K.spline([(0.0312, -0.0775), (0.0301, -0.0830), (0.0276, -0.0920), (0.0248, -0.1020),
                  (0.0218, -0.1120), (0.0188, -0.1210), (0.0170, -0.1275)], 10)
GUARD_BOTTOM = -0.0715
UNDERCUT_R = 0.006


def mag_centre_x(z):
    """x of the (moved) magazine axis at height z."""
    c0 = np.array([0.00888 + MAG_DX, 0.0, -0.1182])           # the old base point, moved
    return c0[0] + (z - c0[2]) * A[0] / A[2]


def back_x(z):
    return K.x_of_z(BACK, z)


def front_x(z):
    """Front of the grip section: the convex strap below the undercut, the 6 mm undercut fillet up to the guard
    bottom, and above that a front buried in the trigger web."""
    z = np.asarray(z, dtype=np.float64)
    zc = -0.0775
    x_strap = K.x_of_z(FRONT, np.minimum(z, zc))
    cx = 0.0312 + UNDERCUT_R
    fil = cx - np.sqrt(np.clip(UNDERCUT_R ** 2 - (z - zc) ** 2, 0, None))
    return np.where(z <= zc, x_strap, np.where(z <= GUARD_BOTTOM, fil, 0.0500))


def front_r(z):
    """Front corner radius of the grip section (small where the front is buried in the web)."""
    return np.interp(z, [BUTT_Z, -0.0800, -0.0740, -0.0700], [0.0065, 0.0065, 0.0040, 0.0020])


def grip_section(z, inset=0.0):
    zz = float(z)
    x0, x1 = back_x(zz) + inset, float(front_x(zz)) - inset
    w = FRAME_W - inset
    return K.rrect(x0, x1, w, 0.0068 - inset * 0.8, float(front_r(zz)) - inset * 0.8, bulge_b=0.0011, bulge_f=0.0007)


GRIP_TOP = -0.0236
PANEL_TOP, PANEL_BOT = -0.0335, -0.1240
BUTTON = (0.0625, -0.0405)


def grip_levels():
    z = list(np.arange(GRIP_TOP, BUTT_Z + 0.004, -0.0012))
    z += [BUTT_Z + 0.0028, BUTT_Z + 0.0016, BUTT_Z + 0.0008, BUTT_Z + 0.0003, BUTT_Z]
    return np.array(sorted(set(np.round(z, 6)), reverse=True))


def build_grip():
    """Grip frame loft (rounded bottom edge at the butt)."""
    zs = grip_levels()
    secs = []
    for z in zs:
        d = BUTT_Z + 0.0028 - z
        inset = 0.0 if d <= 0 else 0.0028 - math.sqrt(max(0.0, 0.0028 ** 2 - d ** 2))
        secs.append(grip_section(z, inset))
    return K.loft_z(secs, zs, 76, name="Grip")


def panel_front_x(z):
    """Side-view x of the panel's front edge above the undercut (with the relief scallop at the button)."""
    r = 0.019
    sc = BUTTON[0] - np.sqrt(np.clip(r * r - (z - BUTTON[1]) ** 2, 0, None))
    return np.minimum(0.0475, np.where(np.abs(z - BUTTON[1]) < r, sc, 1.0))


def build_panel(side):
    """Grip panel on one side (side=-1 right, +1 left): a shell over the frame side flat that wraps 4.5 mm round
    the back and front corners, 3.4 mm thick at the crown, rounded borders."""
    zs = np.linspace(PANEL_TOP, PANEL_BOT, 64)
    nu = 34
    wrap = 0.0045
    s0, s1 = [], []
    secs = [grip_section(z) for z in zs]
    for z, sec in zip(zs, secs):
        a, b = sec.marks["right"]                      # s at the back and front ends of the right side flat
        x_start = sec.x0 + sec.rb
        sf = a + (panel_front_x(z) - x_start)
        s0.append(a - wrap)
        s1.append(min(sf, b + wrap))
    s0, s1 = np.array(s0), np.array(s1)
    # smooth the front edge through the undercut, then round the four corners (radius 5 mm in (s, z))
    k = np.exp(-0.5 * (np.arange(-6, 7) / 2.5) ** 2)
    k /= k.sum()
    s1 = np.convolve(np.pad(s1, 6, mode="edge"), k, mode="valid")
    Rc = 0.005
    dz = np.minimum(np.abs(zs - PANEL_TOP), np.abs(zs - PANEL_BOT))
    sh = np.where(dz < Rc, Rc - np.sqrt(np.clip(Rc ** 2 - (Rc - dz) ** 2, 0, None)), 0.0)
    s0 += sh
    s1 -= sh
    outer = np.zeros((len(zs), nu, 3))
    inner = np.zeros((len(zs), nu, 3))
    hz = (PANEL_TOP - PANEL_BOT) / 2
    zm = (PANEL_TOP + PANEL_BOT) / 2
    for i, (z, sec) in enumerate(zip(zs, secs)):
        u = np.linspace(0, 1, nu)
        s = s0[i] + (s1[i] - s0[i]) * u
        if side > 0:                                    # left side: mirror the right-side parameter
            s = sec.L / 2 + (sec.L / 2 - s)
            s = s[::-1]
        p = sec.at(s)
        n = sec.normal_at(s)
        L = (s1[i] - s0[i])
        d_edge = np.minimum.reduce([u * L, (1 - u) * L, np.full(nu, abs(z - PANEL_TOP)), np.full(nu, abs(z - PANEL_BOT))])
        if side > 0:
            d_edge = d_edge[::-1]
            uu = u[::-1]
        else:
            uu = u
        crown = (1 - (2 * uu - 1) ** 2) ** 0.75 * (1 - 0.35 * ((z - zm) / hz) ** 2)
        t_core = 0.0016 + (PANEL_T - 0.0016) * crown
        re = 0.0018
        q = np.clip(d_edge / re, 0, 1)
        t = 0.00045 + (t_core - 0.00045) * np.sqrt(1 - (1 - q) ** 2)
        outer[i, :, 0] = p[:, 0] + n[:, 0] * t
        outer[i, :, 1] = p[:, 1] + n[:, 1] * t
        outer[i, :, 2] = z
        inner[i, :, 0] = p[:, 0] - n[:, 0] * 0.0004
        inner[i, :, 1] = p[:, 1] - n[:, 1] * 0.0004
        inner[i, :, 2] = z
    # closed shell: outer grid, inner grid reversed, border walls
    nz = len(zs)
    V = np.concatenate([outer.reshape(-1, 3), inner.reshape(-1, 3)])
    o = lambda i, j: i * nu + j
    q_ = lambda i, j: nz * nu + i * nu + j
    faces = []
    for i in range(nz - 1):
        for j in range(nu - 1):
            faces.append((o(i, j), o(i, j + 1), o(i + 1, j + 1), o(i + 1, j)))
            faces.append((q_(i, j), q_(i + 1, j), q_(i + 1, j + 1), q_(i, j + 1)))
    for i in range(nz - 1):
        faces.append((o(i, 0), o(i + 1, 0), q_(i + 1, 0), q_(i, 0)))
        faces.append((o(i, nu - 1), q_(i, nu - 1), q_(i + 1, nu - 1), o(i + 1, nu - 1)))
    for j in range(nu - 1):
        faces.append((o(0, j), q_(0, j), q_(0, j + 1), o(0, j + 1)))
        faces.append((o(nz - 1, j), o(nz - 1, j + 1), q_(nz - 1, j + 1), q_(nz - 1, j)))
    ob = geo.from_arrays("Panel", V, faces, smooth=None)
    return K.outward(ob)


SCREWS = ((0.0330, -0.0470), (-0.0130, -0.1120))


def panel_surface_y(pan, x, z, side):
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(pan, __import__("bpy").context.evaluated_depsgraph_get())
    hit = bvh.ray_cast(Vector((x, side * 0.05, z)), Vector((0, -side, 0)), 0.1)
    return hit[0].y if hit[0] is not None else side * (FRAME_W + PANEL_T)


def nine_panels(parts):
    for side in (-1, 1):
        pan = build_panel(side)
        heads = []
        cutters = []
        for x, z in SCREWS:
            y = panel_surface_y(pan, x, z, side)
            # countersink: cone opening 7.4 mm at the surface, 5.2 mm bushing bore
            cs = lathe([(-0.004, 0.0), (-0.004, 0.0026), (0.0, 0.0026), (0.0011, 0.0037), (0.004, 0.0037), (0.004, 0.0)],
                       32, axis="Y")
            if side < 0:
                geo.transform(cs, scale=(1, -1, 1))
            geo.transform(cs, loc=(x, y - side * 0.0011, z))
            cutters.append(cs)
            heads.append((x, y, z))
        cut(pan, *cutters)
        round_edges(pan, 0.00025, 2, 45)
        parts.append(P(pan, POLYMER, "frame"))
        for x, y, z in heads:
            bush = lathe([(-0.0030, 0.0), (-0.0030, 0.0026), (-0.0012, 0.0026), (-0.0010, 0.0024), (-0.0010, 0.0)],
                         28, axis="Y", fillet=0.0001)
            if side < 0:
                geo.transform(bush, scale=(1, -1, 1))
            geo.transform(bush, loc=(x, y, z))
            parts.append(P(fix_normals(bush), STAINLESS, "frame"))
            parts.append(P(pin_head((x, y - side * 0.0010, z), "Y", r=0.0021, h=0.00055, sign=side, slot=True, seg=28),
                           DARK, "frame"))


# ------------------------------------------------------------------------------------------------- frame

FRAME_OUTLINE = [
    (-0.0330, -0.0122), (-0.0327, -0.0095), (-0.0308, -0.0082), (-0.0286, -0.0091), (-0.0252, -0.0104),
    (-0.0218, -0.0103), (-0.0196, -0.0086), (-0.0174, -0.0061), (-0.0135, -0.0050), (-0.0100, -0.0057),
    (-0.0077, -0.0080), (-0.0063, -0.0116), (-0.0046, -0.0135), (0.1950, -0.0135), (0.1960, -0.0146),
    (0.1960, -0.0230), (0.1944, -0.0245), (0.1338, -0.0245), (0.1306, -0.0262), (0.1292, -0.0300),
    (0.1288, -0.0335), (0.0730, -0.0335), (0.0730, -0.0345), (0.0300, -0.0345), (-0.0150, -0.0345)]


def frame_outline():
    """Upper frame side outline: the hard-coded top and front, the back following the beavertail underside."""
    pts = list(FRAME_OUTLINE)
    tail = [(float(x), float(z)) for x, z in BACK if z >= -0.0345 and z < -0.0128]
    tail.sort(key=lambda p: -p[1])                    # from the grip upward to the tip
    tail = [p for p in tail[::-1]]
    pts += sorted(tail, key=lambda p: p[1])
    return pts


def frame_half_width(x, z):
    """Upper frame half width: 24.5 mm at the rail line with 2.5 deg draft below it; the beavertail narrows to
    19 mm at its lip."""
    w = 0.01225 - np.clip(-0.0135 - z, 0, None) * 0.044
    tail = np.clip((-0.0150 - x) / 0.018, 0, 1)
    return w - tail * (w - 0.0095)


def build_upper_frame():
    ob = K.slab(frame_outline(), -1.0, 1.0, step=0.0022, name="FrameUpper")

    def fn(co):
        co[:, 1] = np.sign(co[:, 1]) * frame_half_width(co[:, 0], co[:, 2])
        return co
    K.deform(ob, fn)
    return K.outward(ob)


def web_front_x(z):
    """Front face of the trigger web = the opening's rear edge (X 0.073) with a 4 mm fillet into the guard bar."""
    r = 0.004
    zc = -0.0656 + r
    f = 0.073 + r - np.sqrt(np.clip(r * r - (z - zc) ** 2, 0, None))
    return np.where(z > zc, 0.073, np.where(z > -0.0656, f, 0.077))


def build_web():
    """Trigger web between the grip and the opening: sections from the frame down to the guard bottom, full grip
    width at the back narrowing toward the opening (23 mm at the top, the guard's 8.6 mm at the bottom)."""
    zs = np.r_[np.linspace(-0.0300, -0.0600, 16), np.linspace(-0.0610, GUARD_BOTTOM, 10)]
    secs = []
    for z in zs:
        xf = float(web_front_x(z))
        t = (-0.030 - z) / (-0.030 - GUARD_BOTTOM)
        wf = 0.0108 + (0.0043 - 0.0108) * t
        xs = np.linspace(0.034, xf, 18)
        w = np.where(xs <= 0.050, FRAME_W, FRAME_W + (wf - FRAME_W) * (xs - 0.050) / max(xf - 0.050, 1e-6))
        right = [(x, -y) for x, y in zip(xs, w)]
        left = [(x, y) for x, y in zip(xs[::-1], w[::-1])]
        poly = right[:-1] + geo.fillet([right[-2], right[-1], left[0], left[1]], 0.0022, 4, closed=False)[1:-1] + left[1:]
        poly = [(0.034, 0.0)] + poly
        secs.append(K.poly_section(poly))
    ob = K.loft_z(secs, zs, 64, name="Web")
    return ob


GUARD_PATH = [(0.12625, 0.0, -0.0240), (0.12625, 0.0, -0.0560), (0.1185, 0.0, -0.06855), (0.0640, 0.0, -0.06855)]


def build_guard():
    """Trigger guard: rounded-rectangle section, 5.5 mm radial x 8.6 mm wide, 1.6 mm outer and 1 mm inner radii,
    swept from the dust cover round the D down to the web (front face squared)."""
    path = geo.fillet(GUARD_PATH, 0.0105, 10)
    h, wd = 0.00275, 0.0043

    # explicit rounded rectangle (counter-clockwise): radial +x outer, y across
    def corner(cx, cy, r, a0):
        return [(cx + r * math.cos(a0 + k * math.pi / 2 / 4), cy + r * math.sin(a0 + k * math.pi / 2 / 4)) for k in range(5)]
    ro, ri = 0.0016, 0.0010
    pts = (corner(h - ro, -wd + ro, ro, -math.pi / 2) + corner(h - ro, wd - ro, ro, 0.0)
           + corner(-h + ri, wd - ri, ri, math.pi / 2) + corner(-h + ri, -wd + ri, ri, math.pi))
    g = geo.sweep(pts, path, up=(0, 1, 0), name="Guard")
    return K.outward(g)


def build_frame_rails():
    out = []
    for x0, x1 in ((0.0005, 0.0500), (0.1220, 0.1900)):
        for s in (1, -1):
            r = box(x0, x1, min(s * 0.0082, s * 0.0102), max(s * 0.0082, s * 0.0102), -0.0137, -0.0108, bevel=0.00025)
            out.append(r)
    return out


def nine_frame(parts):
    up = build_upper_frame()
    grip = build_grip()
    web = build_web()
    guard = build_guard()
    union(up, grip, web, guard)
    # cuts: hammer slot, trigger slot, magazine well, rail flank grooves and slots
    hammer_slot = box(-0.040, 0.004, -0.0037, 0.0037, -0.0200, 0.0)
    trig = box(0.0835, 0.0985, -0.0036, 0.0036, -0.0370, -0.0245, bevel=0.0005)
    well = mag_body_solid(0.0103, 0.0174, -0.004, 0.090, name="Well")
    grooves = []
    for s_ in (1, -1):
        d = 0.0110
        v = [(s_ * 0.0104, -0.0205), (s_ * (0.0104 + d), -0.0205 - d), (s_ * (0.0104 + d), -0.0205 + d)]
        grooves.append(prism(v, 0.1330, 0.2050, axis="X", bevel=0, name="Groove"))
    slots = []
    for xc in (0.142, 0.156, 0.170):
        sl = prism([(xc - 0.0026, -0.0262), (xc + 0.0026, -0.0262), (xc + 0.0026, -0.0229), (xc - 0.0026, -0.0229)],
                   -0.02, 0.02, bevel=0, fillet=0.0004, name="Slot")
        slots.append(sl)
    cut(up, hammer_slot, trig, well, *grooves, *slots)
    for r in build_frame_rails():
        union(up, r)
    round_edges(up, 0.00035, 2, 42)
    parts.append(P(up, BLACKOX, "frame"))
    nine_panels(parts)
    # pins through the frame: trigger, hammer (in the ears), slide stop shaft head on the right
    for s in (1, -1):
        y = float(frame_half_width(NN["trigger_pivot"][0], NN["trigger_pivot"][2]))
        parts.append(P(pin_head((NN["trigger_pivot"][0], s * y, NN["trigger_pivot"][2]), "Y", r=0.0016, h=0.0003, sign=s), DARK, "frame"))
        y = float(frame_half_width(NN["hammer_pivot"][0], NN["hammer_pivot"][2]))
        parts.append(P(pin_head((NN["hammer_pivot"][0], s * y, NN["hammer_pivot"][2]), "Y", r=0.0021, h=0.0004, sign=s), DARK, "frame"))
    y = float(frame_half_width(NN["stop_pivot"][0], NN["stop_pivot"][2]))
    parts.append(P(pin_head((NN["stop_pivot"][0], -y, NN["stop_pivot"][2]), "Y", r=0.0021, h=0.0006, sign=-1), DARK, "frame"))
    # thumb safety (left): lever and a domed, serrated pad
    saf = prism([(0.0040, -0.0150), (0.0300, -0.0150), (0.0300, -0.0075), (0.0200, -0.0062), (0.0040, -0.0079)],
                0.01215, 0.0134, bevel=0.0003, seg=2, fillet=0.0015, name="Safety")
    pad = prism([(0.0195, -0.0152), (0.0308, -0.0152), (0.0308, -0.0072), (0.0195, -0.0072)], 0.0125, 0.0158,
                bevel=0.0009, seg=3, fillet=0.0026, name="SafetyPad")
    K.deform(pad, lambda co: np.c_[co[:, 0], co[:, 1] + 0.0006 * np.clip(1 - ((co[:, 0] - 0.0252) / 0.0062) ** 2, 0, 1)
                                  * (co[:, 1] > 0.0150), co[:, 2]])
    union(saf, pad)
    round_edges(saf, 0.0002, 2, 50)
    parts.append(P(saf, DARK, "frame"))
    parts.append(P(pin_head((0.0080, 0.0134, -0.0112), "Y", r=0.0028, h=0.0006), DARK, "frame"))
    # magazine button (left, round, checkered face in the normal map), on the web
    yb = 0.0102
    btn = lathe([(0.0, 0.0), (0.0, 0.0046), (0.0014, 0.0046), (0.0021, 0.0041), (0.0024, 0.0030), (0.0025, 0.0)], 40,
                axis="Y", at=(BUTTON[0], yb - 0.0004, BUTTON[1]), fillet=0.0002)
    parts.append(P(btn, DARK, "frame"))
    ring = lathe([(0.0, 0.0050), (0.0, 0.0058), (0.0005, 0.0058), (0.0006, 0.0050)], 40, axis="Y", closed=True,
                 at=(BUTTON[0], yb - 0.0002, BUTTON[1]))
    parts.append(P(fix_normals(ring), BLACKOX, "frame"))


# ------------------------------------------------------------------------------------------------- slide

def slide_section(x):
    """Outer slide section in (y, z): 27 mm wide, 3 mm top radii, upper flanks tapered 0.5 mm, 0.6 mm lower
    edge breaks; the 17 deg nose bevel narrows the front 13 mm."""
    w = 0.0135
    nose = max(0.0, x - 0.1830) * math.tan(math.radians(17.0))
    rear = max(0.0, 0.0015 - x) * 0.8
    w2 = w - nose - rear
    top = 0.0125 - rear - max(0.0, x - 0.1930) * 0.25
    sec = K.rrect(-0.0135 + rear * 0.5, top, w2, 0.0006, 0.0030)
    P_ = sec.P.copy()
    zz, yy = P_[:, 0].copy(), P_[:, 1].copy()
    taper = np.clip((zz - 0.0030) / (top - 0.0030), 0, 1) * 0.0005
    yy = np.sign(yy) * np.maximum(np.abs(yy) - taper, 0)
    return K.Section(np.stack([yy, zz], 1), sec.s, sec.L)


def nine_slide(parts):
    xs = np.r_[0.0, 0.0004, 0.0010, 0.0016, np.arange(0.003, 0.183, 0.0045), np.arange(0.183, 0.1955, 0.0012), 0.196]
    secs = [slide_section(x) for x in xs]
    sl = K.loft_x(secs, xs, 72, name="Slide")
    chan = box(0.0045, 0.250, -0.0104, 0.0104, -0.020, 0.0100)
    nose = lathe([(0.15, 0.0), (0.15, 0.0072), (0.25, 0.0072), (0.25, 0.0)], 48)
    rod = lathe([(0.15, 0.0), (0.15, 0.0034), (0.25, 0.0034), (0.25, 0.0)], 32, at=(0, 0, -0.0118))
    port = prism([(0.086, -0.003), (0.126, -0.003), (0.126, 0.030), (0.086, 0.030)], -0.030, 0.0042, bevel=0,
                 fillet=0.0012)
    scallop = lathe([(-0.03, 0.0), (-0.03, 0.0048), (-0.0122, 0.0048), (-0.0122, 0.0)], 40, axis="Y",
                    at=(0.0915, 0.0, -0.0020))
    firing = lathe([(-0.01, 0.0), (-0.01, 0.0016), (0.0025, 0.0016), (0.0025, 0.0)], 24)
    ext_slot = prism([(0.0575, 0.0026), (0.0870, 0.0026), (0.0870, 0.0072), (0.0575, 0.0072)], -0.020, -0.0129,
                     bevel=0, fillet=0.0012)
    sers = []
    for s in (1, -1):
        for k in range(7):
            x = 0.0090 + k * 0.0020
            c = prism([(x - 0.00075, -0.0118), (x + 0.00075, -0.0118), (x + 0.00075, 0.0082), (x - 0.00075, 0.0082)],
                      s * 0.0123, s * 0.022, bevel=0, fillet=0.00074, fseg=3, name="Ser")
            sers.append(c)
    front_dt = box(0.1815, 0.1905, -0.0050, 0.0050, 0.0105, 0.020)
    rear_dt = box(0.0055, 0.0195, -0.0095, 0.0095, 0.0100, 0.020)
    cut(sl, chan, nose, rod, port, scallop, firing, ext_slot, front_dt, rear_dt, *sers)
    round_edges(sl, 0.00022, 2, 40)
    parts.append(P(sl, STAINLESS, "slide"))
    # firing pin end, recessed 0.5 mm in its hole (the breech face stays closed in front of it)
    parts.append(P(lathe([(0.0005, 0.0), (0.0005, 0.0012), (0.0024, 0.0012), (0.0024, 0.0)], 20, fillet=0.0002),
                   DARK, "slide"))
    # sights: rear notch 4.2 x 3.9, top Z 0.0185, X 0.007..0.018; front blade 3.4 wide, top X 0.1835..0.1885
    rs = prism([(0.0060, 0.0098), (0.0190, 0.0098), (0.0190, 0.0140), (0.0178, 0.0185), (0.0070, 0.0185),
                (0.0060, 0.0172)], -0.0098, 0.0098, bevel=0.0005, seg=2, name="RearSight")
    cut(rs, box(0.0, 0.03, -0.0021, 0.0021, 0.0146, 0.03))
    round_edges(rs, 0.0002, 1, 50)
    parts.append(P(rs, DARK, "slide"))
    fs = prism([(0.1820, 0.0098), (0.1900, 0.0098), (0.1888, 0.0150), (0.1885, 0.0185), (0.1835, 0.0185),
                (0.1830, 0.0140)], -0.0017, 0.0017, bevel=0.0003, seg=2, name="FrontSight")
    base = box(0.1818, 0.1902, -0.0048, 0.0048, 0.0098, 0.0128, bevel=0.0004)
    union(fs, base)
    parts.append(P(fs, DARK, "slide"))
    # extractor: a spring-steel plate in its slot on the right, claw at the port, retaining pin
    ex = prism([(0.0580, 0.0029), (0.0850, 0.0029), (0.0866, 0.0040), (0.0866, 0.0060), (0.0850, 0.0069),
                (0.0580, 0.0069)], -0.0137, -0.0128, bevel=0.00025, seg=2, fillet=0.0008, name="Extractor")
    K.deform(ex, lambda co: np.c_[co[:, 0], co[:, 1] - 0.00025 * np.clip((co[:, 0] - 0.058) / 0.027, 0, 1) * (co[:, 1] < -0.0132), co[:, 2]])
    parts.append(P(ex, STAINLESS, "slide"))
    parts.append(P(pin_head((0.0630, -0.0137, 0.0049), "Y", r=0.0011, h=0.0002, sign=-1, seg=16), DARK, "slide"))


# ------------------------------------------------------------------------------------------------- moving parts

def nine_moving(parts):
    # slide stop (left, X 0.058..0.100): plate and a domed, serrated thumb pad at the rear
    st = prism([(0.0580, -0.0182), (0.0640, -0.0190), (0.0960, -0.0190), (0.1000, -0.0165), (0.0960, -0.0140),
                (0.0700, -0.0140), (0.0610, -0.0120), (0.0580, -0.0135)], 0.01215, 0.0134, bevel=0.0003, seg=2,
               fillet=0.0012, name="SlideStop")
    tpad = prism([(0.0578, -0.0186), (0.0705, -0.0190), (0.0705, -0.0124), (0.0588, -0.0121)], 0.0128, 0.0153,
                 bevel=0.0008, seg=3, fillet=0.0022)
    K.deform(tpad, lambda co: np.c_[co[:, 0], co[:, 1] + 0.0005 * np.clip(1 - ((co[:, 0] - 0.0640) / 0.0068) ** 2, 0, 1)
                                   * (co[:, 1] > 0.0146), co[:, 2]])
    union(st, tpad)
    round_edges(st, 0.0002, 2, 50)
    parts.append(P(st, DARK, "slide_stop"))
    parts.append(P(pin_head((NN["stop_pivot"][0], 0.0134, NN["stop_pivot"][2]), "Y", r=0.0023, h=0.0006), DARK, "slide_stop"))
    # hammer: body 6.2 mm with hollowed sides, 9 mm spur (thumb face checkered in the normal map), strut pin
    ham = prism([(-0.0185, -0.0150), (-0.0090, -0.0150), (-0.0072, -0.0100), (-0.0080, -0.0040), (-0.0120, 0.0030),
                 (-0.0170, 0.0078), (-0.0195, 0.0098), (-0.0270, 0.0098), (-0.0296, 0.0084), (-0.0300, 0.0066),
                 (-0.0262, 0.0030), (-0.0222, -0.0020), (-0.0200, -0.0080)], -0.0031, 0.0031, bevel=0.0005, seg=2,
                fillet=0.0015, name="Hammer")
    hollows = []
    for s in (1, -1):
        e = geo.sphere(1.0, 32, 16, name="Hollow")
        geo.transform(e, scale=(0.0055, 0.0030, 0.0070))
        geo.transform(e, loc=(-0.0160, s * (0.0031 + 0.0030 - 0.0007), -0.0005))
        hollows.append(e)
    cut(ham, *hollows)
    spur = prism([(-0.0195, 0.0105), (-0.0270, 0.0105), (-0.0296, 0.0092), (-0.0302, 0.0068), (-0.0278, 0.0046),
                  (-0.0205, 0.0058), (-0.0182, 0.0084)], -0.0045, 0.0045, bevel=0.0012, seg=3, fillet=0.0014,
                 name="Spur", corner=25)
    union(ham, spur)
    round_edges(ham, 0.0002, 2, 50)
    parts.append(P(ham, DARK, "hammer"))
    pin = lathe([(-0.0034, 0.0), (-0.0034, 0.0010), (0.0034, 0.0010), (0.0034, 0.0)], 20, axis="Y",
                at=(-0.0160, 0.0, -0.0005), fillet=0.0002)
    parts.append(P(pin, POLISHED, "hammer"))
    # gold trigger: curved blade, rounded edges, serrated face (normal map)
    t = [(0.0870, -0.0290), (0.0950, -0.0290), (0.0965, -0.0380), (0.0955, -0.0460), (0.0920, -0.0545),
         (0.0880, -0.0600), (0.0850, -0.0590), (0.0878, -0.0530), (0.0898, -0.0455), (0.0895, -0.0380)]
    trg = prism(t, -0.0031, 0.0031, bevel=0.0010, seg=3, fillet=0.0012, name="Trigger")
    parts.append(P(trg, GOLD, "trigger"))


# ------------------------------------------------------------------------------------------------- magazine

def mag_base():
    """Point on the moved magazine axis at the butt plane."""
    return np.array([mag_centre_x(BUTT_Z), 0.0, BUTT_Z])


def mag_body_solid(half_w, half_d, t0, t1, name="MagSolid", r=0.0030):
    """Rounded-rectangle prism along the magazine axis between t0 and t1 metres from the butt plane."""
    b = mag_base()
    sec = geo.fillet([(-half_d, -half_w), (half_d, -half_w), (half_d, half_w), (-half_d, half_w)], r, 3, closed=True)
    rings = []
    for t in (t0, t1):
        c = b + A * t
        rings.append([tuple(c + F * u + np.array([0, 1.0, 0]) * v) for u, v in sec])
    return loft(rings, name=name)


def butt_footprint(over=0.001):
    """Butt section (x, y) grown by `over`, with the pad's flared front lip."""
    sec = grip_section(BUTT_Z)
    x0, x1 = sec.x0 - over, sec.x1 + over
    return x0, x1, FRAME_W + over


def nine_magazine(col):
    """SM_Weapon_NineMagazine (+ _TopRound) on the moved axis: brushed body 19.5 x 34 mm with three witness holes
    per side, feed lips, the stack, and a flat gold base pad following the butt (1 mm overhang, flared lip)."""
    b = mag_base()
    top_t = (-0.037 - b[2]) / A[2]
    Wm, D = 0.00975, 0.017
    parts = []
    sec = [(-D, -Wm), (D - 0.004, -Wm), (D, -Wm + 0.004), (D, Wm - 0.004), (D - 0.004, Wm), (-D, Wm)]
    sec = geo.fillet(sec, 0.0018, 3, closed=True)
    inner = [(u * (D - 0.0007) / D, v * (Wm - 0.0007) / Wm) for u, v in sec]
    ring = lambda t, s: [tuple(b + A * t + F * u + np.array([0, 1.0, 0]) * v) for u, v in s]
    t_lo = -0.004
    body = loft([ring(t_lo, sec), ring(top_t - 0.004, sec)], cap0=True, cap1=False, name="NMagBody")
    inn = loft([ring(top_t - 0.004 - 0.030, inner), ring(top_t - 0.004, inner)], cap0=True, cap1=False, name="NMagIn")
    bm = geo.bm_of(inn)
    for fc in bm.faces:
        fc.normal_flip()
    geo.bm_to(inn, bm)
    holes = []
    for t in (0.030, 0.048, 0.066):
        c = b + A * t + F * (-0.008)
        holes.append(lathe([(-0.02, 0.0), (-0.02, 0.0015), (0.02, 0.0015), (0.02, 0.0)], 24, axis="Y", at=tuple(c)))
    cut(body, *holes)
    round_edges(body, 0.0003, 2, 50)
    parts.append(P(body, BLUED, None))
    parts.append(P(inn, BORE, None))
    o, i = ring(top_t - 0.004, sec), ring(top_t - 0.004, inner)
    m = len(o)
    rim = geo.from_arrays("NRim", np.concatenate([o, i]), [(j, (j + 1) % m, m + (j + 1) % m, m + j) for j in range(m)],
                          smooth=None)
    parts.append(P(fix_normals(rim), BLUED, None))
    for s in (1, -1):
        prof = [(s * Wm, 0.0), (s * Wm, 0.0020), (s * (Wm - 0.0012), 0.0034), (s * (Wm - 0.0036), 0.0040),
                (s * (Wm - 0.0044), 0.0034), (s * (Wm - 0.0007), 0.0012), (s * (Wm - 0.0007), 0.0)]
        if s < 0:
            prof = prof[::-1]
        secs = []
        for u in np.linspace(-D + 0.001, D * 0.25, 7):
            c = b + A * (top_t - 0.004) + F * u
            secs.append([tuple(c + np.array([0, y, 0]) + A * h) for y, h in prof])
        parts.append(P(loft(secs, name="NLip"), BLUED, None))
    for k in range(1, 10):
        t = top_t - 0.004 - 0.0062 * k
        c = b + A * t + F * (-D + 0.002)
        rd = W.cartridge(0.030, 0.0047, name="Stack", rifle=False, seg=20)
        geo.transform(rd, loc=(c[0], (0.0035 if k % 2 else -0.0035), c[2]))
        parts.append(rd)
    # base pad: flat plate under the butt, 7 mm, 2 mm edge radii, front finger lip flared down and forward
    x0, x1, wp = butt_footprint(0.001)
    out = K.rrect(x0, x1, wp, 0.0062, 0.0060)
    zs = [BUTT_Z, BUTT_Z - 0.0006, BUTT_Z - 0.0016, BUTT_Z - 0.0032, BUTT_Z - 0.0050, PAD_Z + 0.0014, PAD_Z + 0.0005, PAD_Z]
    secs = []
    for z in zs:
        dt = max(0.0, z - (BUTT_Z - 0.0012))                    # top edge radius (small: it sits flush)
        db = max(0.0, (PAD_Z + 0.0020) - z)                     # bottom edge radius 2 mm
        inset = 0.0008 - math.sqrt(max(0, 0.0008 ** 2 - min(dt, 0.0008) ** 2)) if dt > 0 else 0.0
        if db > 0:
            inset = 0.0020 - math.sqrt(max(0, 0.0020 ** 2 - min(db, 0.0020) ** 2))
        lip = 0.0030 * np.clip((BUTT_Z - 0.0010 - z) / 0.0055, 0, 1) ** 1.5    # the front flares forward going down
        secs.append(K.rrect(x0 + inset, x1 + lip - inset, wp - inset, 0.0062 - inset * 0.7, 0.0060 - inset * 0.7))
    pad = K.loft_z(secs, zs, 64, name="Pad")
    # finger lip: the front underside curls slightly down
    K.deform(pad, lambda co: np.c_[co[:, 0], co[:, 1], co[:, 2] - 0.0006 * np.clip((co[:, 0] - (x1 - 0.004)) / 0.006, 0, 1)
                                   * (co[:, 2] < BUTT_Z - 0.004)])
    parts.append(P(pad, GOLD, None))
    body = geo.join(parts, "SM_Weapon_NineMagazine", col)
    ctop = b + A * top_t
    top = W.cartridge(0.030, 0.0048, name="SM_Weapon_NineMagazine_TopRound", rifle=False)
    geo.transform(top, loc=(ctop[0] - 0.0175, 0.0, -0.0335))
    W.scene.move_to(top, col)
    top.name = top.data.name = "SM_Weapon_NineMagazine_TopRound"
    return body, top


def nine_build(ctx):
    parts = []
    nine_slide(parts)
    W.nine_barrel(parts)
    nine_frame(parts)
    nine_moving(parts)
    gun = geo.join(parts, "SK_Nine", ctx.col)
    bones = [W.rig.Bone("frame", (0, 0, 0)),
             W.rig.Bone("slide", (0, 0, 0), "frame"),
             W.rig.Bone("barrel", NN["barrel_lug"], "frame"),
             W.rig.Bone("trigger", NN["trigger_pivot"], "frame"),
             W.rig.Bone("hammer", NN["hammer_pivot"], "frame"),
             W.rig.Bone("slide_stop", NN["stop_pivot"], "frame"),
             W.rig.Bone("magazine", (0, 0, 0), "frame")]
    bones += [W.rig.Bone(k, v, "frame", deform=False) for k, v in NN["sockets"].items()]
    arm = W.rig.armature("SKEL_Nine", bones, ctx.col)
    W.rig.bind(gun, arm)
    return gun, arm
