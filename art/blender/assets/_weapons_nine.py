"""NINE, rebuild round 2: a full-size hammer-fired service pistol built the way the real class is made.

    grip      one horizontal-section loft from the beavertail tang down to the butt. The magazine line is the
              brief's again (in place X -0.029..0.045, direction 0.250/0.968), and the grip moved forward with it:
              the front strap rises straight into the back of the trigger guard (opening rear X 0.073, a 4 mm
              radius into the guard bar), the undercut is a 7 mm radius right under the guard's rear (X 0.0605 ..
              0.0675), the strap rakes 19 deg down to the butt; 35 mm from the trigger face to the front strap.
              The tang leaves the back strap in one concave cup (the web of the hand) and runs 13.5 mm behind it,
              19 mm wide, with a rounded tip 4.5 mm thick and 1.5 mm edge radii; no lip, no spike.
    frame     upper frame slab (24.5 mm, 2.5 deg draft, 0.5 mm flat machined along the top edge, 0.3 mm below the
              slide: a shadow gap), hammer ears with 1 mm chamfers, a lofted dust cover (2 deg taper to the nose,
              1.5 mm chamfer, a 21 mm rail with 45 deg dovetail flanks and four 5.2 mm cross slots with 45 deg
              flanks leaving lugs at X 0.142 / 0.156 / 0.170), a guard swept from a 6.5 x 9 mm superellipse along
              a gently curved front, flaring into 3-4 mm fillets at the dust cover and at the grip; a takedown lever.
    panels    one smooth outline per side (front edge X 0.058 with a relief round the magazine button), 3.4 mm with
              a 1 mm crown, 6 mm slotted screws flush in 7.5 mm bushings.
    slide     lofted along X (3 mm top radii, tapered upper flanks, 17 deg nose bevel); nine flat-bottomed 1.1 mm
              serrations at 2.8 mm pitch over 25 mm following the flank; port with 1.2 mm corners and a 0.5 mm
              chamfer; extractor 0.3 mm proud in its own 0.2 mm gap with the claw in the port; both sights in
              dovetails cut across the slide; a 9.5 mm hammer channel in the underside of the slide's rear (the
              static cocked hammer clears the slide through its whole travel).
    hammer    one forged piece: 6 mm body widening to a 9 mm spur along an S, R 9.5 back, flat thumb face.
    controls  slide stop (1.3 mm plate thickening to the pad, 4 mm thumb shelf with 5 serrations, 0.3 mm off the
              frame), thumb safety (lever, flared 3 mm pad with serrations, shaft boss), magazine button.
    magazine  body on the brief's line; gold base pad 75 x 26 x 7 mm, 2 mm top radii, 1.5 mm domed bottom, finger
              flare at the front, a 0.5 mm parting line.
"""
import math

import numpy as np
from mathutils import Vector

from mi import geo
from assets import weapons as W
from assets import _weapons_kit as K

NN = W.NN
P, prism, lathe, box, cut, union, round_edges, pin_head, loft, fix_normals = (
    W.P, W.prism, W.lathe, W.box, W.cut, W.union, W.round_edges, W.pin_head, W.loft, W.fix_normals)
STAINLESS, DARK, BLACKOX, POLYMER, POLISHED, GOLD, BLUED, BORE = (
    W.STAINLESS, W.DARK, W.BLACKOX, W.POLYMER, W.POLISHED, W.GOLD, W.BLUED, W.BORE)

A = np.array(NN["mag_axis"], float) / np.linalg.norm(NN["mag_axis"])     # base -> lips
F = np.array([A[2], 0.0, -A[0]])                                       # forward, perpendicular to the axis
MAG_C0 = (0.00888, -0.1182)          # a point on the brief's magazine line (first-pass position, kept)
BUTT_Z = -0.1275
PAD_Z = -0.1345
FRAME_W = 0.0115                     # grip half width (panels add 3.4 mm: 29.8 mm over the panels)
TANG_W = 0.0095                      # beavertail / hammer housing half width (19 mm)
UPPER_W = 0.01225                    # upper frame half width at the rail line (24.5 mm)
FRAME_TOP = -0.0138                  # 0.3 mm under the slide (rail line -0.0135): the shadow gap
PANEL_T = 0.0034
TOP_Z = -0.0105                      # tang top
GUARD_BOTTOM = -0.0715
OPEN_REAR = 0.073
UNDERCUT = (0.0675, -0.0785, 0.007)  # centre x, z and radius of the undercut under the guard's rear
STRAP_X = UNDERCUT[0] - UNDERCUT[2]  # 0.0605: front strap right under the undercut
STRAP_TAN = (STRAP_X - 0.0430) / (UNDERCUT[1] - BUTT_Z)


def mag_centre_x(z):
    """x of the magazine axis at height z (the brief's line)."""
    return MAG_C0[0] + (z - MAG_C0[1]) * A[0] / A[2]


# side-view back curve (x, z), monotonic in z: tang tip -> underside -> cup -> back strap (palm swell) -> heel
BACK = K.spline([(-0.0306, -0.0105), (-0.0324, -0.0113), (-0.0330, -0.0127), (-0.0325, -0.0140),
                 (-0.0307, -0.0151), (-0.0281, -0.0161), (-0.0256, -0.0176), (-0.0233, -0.0196),
                 (-0.0215, -0.0221), (-0.0204, -0.0250), (-0.0198, -0.0282), (-0.0195, -0.0320),
                 (-0.0192, -0.0370), (-0.0191, -0.0420), (-0.0195, -0.0480), (-0.0206, -0.0560),
                 (-0.0222, -0.0650), (-0.0240, -0.0750), (-0.0256, -0.0860), (-0.0270, -0.0970),
                 (-0.0275, -0.1080), (-0.0279, -0.1180), (-0.0278, -0.1275)], 10)


def back_x(z):
    return K.x_of_z(BACK, z)


def front_x(z):
    """Front of the grip section: buried in the frame above the opening, the opening's rear edge (X 0.073) with a
    4 mm radius into the guard bar, the undercut (R 7) right under the guard's rear, then the raked strap."""
    z = np.asarray(z, dtype=np.float64)
    ux, uz, ur = UNDERCUT
    fil = OPEN_REAR + 0.004 - np.sqrt(np.clip(0.004 ** 2 - (z + 0.061) ** 2, 0, None))
    bar = 0.077 - 0.0095 * K.smoothstep(-z, 0.0650, -GUARD_BOTTOM)
    under = ux - np.sqrt(np.clip(ur ** 2 - (z - uz) ** 2, 0, None))
    t = np.clip((uz - z) / (uz - BUTT_Z), 0, 1)
    strap = STRAP_X - (uz - z) * STRAP_TAN + 0.0009 * np.sin(math.pi * t)
    return np.select([z > -0.0256, z > -0.0610, z > -0.0650, z > GUARD_BOTTOM, z > uz],
                     [-0.0045, OPEN_REAR, fil, bar, under], strap)


def front_r(z):
    return float(np.interp(z, [BUTT_Z, -0.0850, -0.0715, -0.0640, -0.0500, -0.0257, -0.0255],
                           [0.0070, 0.0075, 0.0095, 0.0098, 0.0025, 0.0025, 0.0020]))


def back_r(z):
    return float(np.interp(z, [BUTT_Z, -0.0300, -0.0160, TOP_Z], [0.0068, 0.0068, 0.0040, 0.0040]))


def half_w(z):
    """Section half width: the 19 mm tang widens to the 23 mm grip below the web of the hand."""
    return TANG_W + (FRAME_W - TANG_W) * float(K.smoothstep(-z, 0.0195, 0.0300))


def grip_section(z, inset=0.0):
    zz = float(z)
    x0, x1 = float(back_x(zz)) + inset, float(front_x(zz)) - inset
    w = half_w(zz) - inset
    return K.rrect(x0, x1, w, back_r(zz) - inset * 0.8, front_r(zz) - inset * 0.8, bulge_b=0.0011 if zz < -0.02 else 0.0,
                   bulge_f=0.0007 if zz < GUARD_BOTTOM else 0.0)


def grip_levels():
    z = list(np.arange(TOP_Z, BUTT_Z, -0.0014))
    z += [TOP_Z - d for d in (0.00005, 0.0002, 0.0004, 0.0007, 0.0011, 0.0015)]
    z += [-0.0255, -0.0257, -0.0610, -0.0625, -0.0640, -0.0650, GUARD_BOTTOM + 0.0003, GUARD_BOTTOM,
          GUARD_BOTTOM - 0.0003, GUARD_BOTTOM - 0.0010, -0.0735, -0.0760, UNDERCUT[1]]
    z += [BUTT_Z + 0.0028, BUTT_Z + 0.0016, BUTT_Z + 0.0008, BUTT_Z + 0.0003, BUTT_Z]
    z = np.array(sorted(set(np.round(z, 6)), reverse=True))
    return z[(z <= TOP_Z) & (z >= BUTT_Z)]


def build_grip():
    """Frame rear + grip: tang top rounded 1.5 mm, butt edge rounded 2.8 mm."""
    zs = grip_levels()
    secs = []
    for z in zs:
        d = TOP_Z - z
        r = 0.0015
        inset = r - math.sqrt(max(0.0, r * r - (r - d) ** 2)) if d < r else 0.0
        d2 = BUTT_Z + 0.0028 - z
        if d2 > 0:
            inset = 0.0028 - math.sqrt(max(0.0, 0.0028 ** 2 - d2 ** 2))
        secs.append(grip_section(z, inset))
    g = K.loft_z(secs, zs, 64, name="Grip")
    bm = geo.bm_of(g)                                   # fan the caps so the crown can bend them
    caps = [f for f in bm.faces if len(f.verts) > 4]
    W.bmesh.ops.poke(bm, faces=caps)
    geo.bm_to(g, bm)

    def sweep(co):
        # the tang sweeps back and down to its tip (1.2 mm), its top crowned across (0.6 mm)
        x, y, z = co[:, 0], co[:, 1], co[:, 2]
        co[:, 2] = z - 0.0012 * K.smoothstep(-x, 0.018, 0.033) * K.smoothstep(z, -0.0250, -0.0165)
        co[:, 2] -= 0.0006 * (y / TANG_W) ** 2 * K.smoothstep(z, -0.0125, -0.0108) * K.smoothstep(-x, 0.004, 0.012)
        return co
    return K.outward(K.deform(g, sweep))


# ------------------------------------------------------------------------------------------------- panels

PANEL_TOP, PANEL_BOT = -0.0330, -0.1240
BUTTON = (0.0625, -0.0405)
PANEL_FRONT = 0.058
SCREWS = ((0.0340, -0.0460), (0.0060, -0.1130))


def panel_front_x(z):
    """Side-view x of the panel's front edge (X 0.058) with the relief round the magazine button."""
    r = 0.0062
    sc = BUTTON[0] - np.sqrt(np.clip(r * r - (z - BUTTON[1]) ** 2, 0, None))
    return np.minimum(PANEL_FRONT, np.where(np.abs(z - BUTTON[1]) < r, sc, 1.0))


def build_panel(side):
    """Grip panel on one side (side=-1 right, +1 left): a shell over the frame side flat wrapping 3 mm round the
    back corner and round the front corner below the undercut; 2.4 mm at the edges rising to 3.4 mm (1 mm crown),
    rounded borders."""
    zs = np.linspace(PANEL_TOP, PANEL_BOT, 46)
    nu = 26
    wrap = 0.0030
    s0, s1 = [], []
    secs = [grip_section(z) for z in zs]
    for z, sec in zip(zs, secs):
        a, b = sec.marks["right"]
        x_start = sec.x0 + sec.rb
        sf = a + (float(panel_front_x(z)) - x_start)
        s0.append(a - wrap)
        s1.append(min(sf, b + 0.0045))
    s0, s1 = np.array(s0), np.array(s1)
    k = np.exp(-0.5 * (np.arange(-6, 7) / 2.0) ** 2)
    k /= k.sum()
    s1 = np.convolve(np.pad(s1, 6, mode="edge"), k, mode="valid")
    s0 = np.convolve(np.pad(s0, 6, mode="edge"), k, mode="valid")
    Rc = 0.005
    dz = np.minimum(np.abs(zs - PANEL_TOP), np.abs(zs - PANEL_BOT))
    sh = np.where(dz < Rc, Rc - np.sqrt(np.clip(Rc ** 2 - (Rc - dz) ** 2, 0, None)), 0.0)
    # the top-front corner sweeps round with a 10 mm radius, the bottom-front with 6 mm
    def corner(d, R):
        return np.where(d < R, R - np.sqrt(np.clip(R ** 2 - (R - d) ** 2, 0, None)), 0.0)
    shf = np.maximum(corner(np.abs(zs - PANEL_TOP), 0.010), corner(np.abs(zs - PANEL_BOT), 0.006))
    s0 += sh
    s1 -= np.maximum(sh, shf)
    outer = np.zeros((len(zs), nu, 3))
    inner = np.zeros((len(zs), nu, 3))
    hz = (PANEL_TOP - PANEL_BOT) / 2
    zm = (PANEL_TOP + PANEL_BOT) / 2
    for i, (z, sec) in enumerate(zip(zs, secs)):
        u = np.linspace(0, 1, nu)
        u = 0.5 - 0.5 * np.cos(u * math.pi) * 0.35 + (u - 0.5) * 0.65      # denser at the borders
        s = s0[i] + (s1[i] - s0[i]) * u
        if side > 0:
            s = sec.L / 2 + (sec.L / 2 - s)
            s = s[::-1]
        p = sec.at(s)
        n = sec.normal_at(s)
        L = (s1[i] - s0[i])
        d_edge = np.minimum.reduce([u * L, (1 - u) * L, np.full(nu, abs(z - PANEL_TOP)), np.full(nu, abs(z - PANEL_BOT))])
        uu = u
        if side > 0:
            d_edge = d_edge[::-1]
            uu = u[::-1]
        crown = np.clip(1 - (2 * uu - 1) ** 2, 0, 1) ** 0.75 * (1 - 0.35 * ((z - zm) / hz) ** 2)
        t_core = 0.0024 + (PANEL_T - 0.0024) * crown
        re = 0.0016
        q = np.clip(d_edge / re, 0, 1)
        t = 0.0006 + (t_core - 0.0006) * np.sqrt(1 - (1 - q) ** 2)
        outer[i, :, 0] = p[:, 0] + n[:, 0] * t
        outer[i, :, 1] = p[:, 1] + n[:, 1] * t
        outer[i, :, 2] = z
        inner[i, :, 0] = p[:, 0] - n[:, 0] * 0.0004
        inner[i, :, 1] = p[:, 1] - n[:, 1] * 0.0004
        inner[i, :, 2] = z
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
            # 7.5 mm bushing seat, 2.2 mm deep, with a 0.3 mm chamfer at the surface
            cs = lathe([(-0.004, 0.0), (-0.004, 0.00375), (0.0019, 0.00375), (0.0022, 0.0041), (0.005, 0.0041),
                        (0.005, 0.0)], 28, axis="Y")
            if side < 0:
                geo.transform(cs, scale=(1, -1, 1))
            geo.transform(cs, loc=(x, y - side * 0.0022, z))
            cutters.append(cs)
            heads.append((x, y, z))
        cut(pan, *cutters)
        round_edges(pan, 0.00025, 2, 45)
        parts.append(P(pan, POLYMER, "frame"))
        for x, y, z in heads:
            # stainless bushing ring flush minus 0.15 mm, 6 mm slotted screw head flush minus 0.1 mm
            bush = lathe([(-0.0030, 0.0), (-0.0030, 0.00372), (-0.00015, 0.00372), (-0.00015, 0.0031),
                          (-0.0030, 0.0031)], 28, axis="Y", closed=True, fillet=0.00008)
            if side < 0:
                geo.transform(bush, scale=(1, -1, 1))
            geo.transform(bush, loc=(x, y, z))
            parts.append(P(fix_normals(bush), STAINLESS, "frame"))
            head = lathe([(-0.0030, 0.0), (-0.0030, 0.0030), (-0.0004, 0.0030), (-0.0001, 0.0027), (-0.0001, 0.0)], 28,
                         axis="Y", fillet=0.0001)
            cut(head, box(-0.0035, 0.0035, -0.0008, 0.001, -0.00045, 0.00045))
            if side < 0:
                geo.transform(head, scale=(1, -1, 1))
            geo.transform(head, rot=(0, 30 if side > 0 else -55, 0))
            geo.transform(head, loc=(x, y, z))
            parts.append(P(fix_normals(head), DARK, "frame"))


# ------------------------------------------------------------------------------------------------- frame

def upper_hw(x, z):
    """Upper frame half width: 24.5 mm at the rail line with 2.5 deg draft and a 0.5 mm flat machined along the
    top edge; it narrows to the grip's width behind the slide."""
    w = UPPER_W - np.clip(FRAME_TOP - z, 0, None) * 0.044
    w = w - np.clip(z - (FRAME_TOP - 0.0005), 0, None)
    gw = np.array([half_w(v) for v in np.atleast_1d(z)]).reshape(np.shape(z)) - 0.0002
    t = K.smoothstep(x, -0.004, 0.004)
    return gw + (w - gw) * t


def build_upper_frame():
    outline = [(-0.0060, FRAME_TOP), (0.1310, FRAME_TOP), (0.1310, -0.0240), (0.1296, -0.0262), (0.1274, -0.0302),
               (0.1250, -0.0335), (OPEN_REAR, -0.0335), (OPEN_REAR, -0.0350), (-0.0060, -0.0350)]
    extra = [(x, FRAME_TOP - 0.0005) for x in np.arange(-0.0055, 0.1305, 0.0022)]
    extra += [(x, FRAME_TOP - 0.0013) for x in np.arange(-0.0055, 0.1305, 0.0040)]
    ob = K.slab(outline, -1.0, 1.0, step=0.0032, name="FrameUpper", extra=extra)

    def fn(co):
        co[:, 1] = np.sign(co[:, 1]) * upper_hw(co[:, 0], co[:, 2])
        return co
    K.deform(ob, fn)
    return K.outward(ob)


DC_X0, DC_X1 = 0.1280, 0.1960


def dust_cover_section(x):
    """Dust cover section (y, z), counter-clockwise: frame flank with draft, the rail's 45 deg dovetail groove,
    21 mm rail, 1.5 mm chamfers to the bottom, which rises 2 deg toward the nose."""
    dz = (x - 0.1300) * math.tan(math.radians(2.0)) if x > 0.1300 else 0.0
    zb = -0.0245 + dz
    top = FRAME_TOP
    w0 = UPPER_W
    g0 = -0.0180 + dz * 0.6
    half = [(w0 - 0.0005, top), (w0, top - 0.0005), (w0 - 0.044 * (top - g0), g0),
            (0.0094, g0 - 0.0027), (0.0094, g0 - 0.0033), (0.0106, g0 - 0.0045), (0.0106, zb + 0.0015),
            (0.0091, zb)]
    right = [(-y, z) for y, z in half]
    # counter-clockwise in (y, z) seen from +X: start top centre, go to -y (right), down, across, up the left
    pts = [(0.0, top)] + right + [(0.0, zb)] + [(y, z) for y, z in half[::-1]]
    return K.poly_section(pts, K=240)


def build_dust_cover():
    xs = np.r_[DC_X0, np.arange(0.1300, DC_X1, 0.006), DC_X1]
    secs = [dust_cover_section(x) for x in xs]
    dc = K.loft_x(secs, xs, 76, name="DustCover")
    slots = []
    for xc in (0.1350, 0.1490, 0.1630, 0.1770):
        zb = -0.0245 + (xc - 0.1300) * math.tan(math.radians(2.0))
        d = 0.0016
        sl = prism([(xc - 0.0026, zb - 0.002), (xc + 0.0026, zb - 0.002), (xc + 0.0026, zb), (xc + 0.0026 - d, zb + d),
                    (xc - 0.0026 + d, zb + d), (xc - 0.0026, zb)], -0.02, 0.02, bevel=0, name="Slot")
        slots.append(sl)
    cut(dc, *slots)
    return dc


GUARD_PTS = [(0.1238, -0.0205), (0.1254, -0.0290), (0.12675, -0.0420), (0.1258, -0.0530), (0.1214, -0.0630),
             (0.1130, -0.06825), (0.1000, -0.06825), (0.0860, -0.06825), (0.0720, -0.06825), (0.0640, -0.0680)]


def build_guard():
    """Trigger guard swept from a 6.5 x 9 mm superellipse (flatter faces) round a gently curved front; it flares
    into fillets at the dust cover (top) and at the grip (rear)."""
    pth = K.spline(GUARD_PTS, 6)
    path = np.stack([pth[:, 0], np.zeros(len(pth)), pth[:, 1]], 1)
    L = float(np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1)))

    def prof(i, t):
        s = t * L
        f0 = K.smoothstep(0.010 - s, 0.0, 0.010)            # top end: flare into the dust cover
        f1 = K.smoothstep(s - (L - 0.012), 0.0, 0.012)      # rear end: flare into the grip
        a = 0.00325 + 0.0022 * f0 + 0.0020 * f1
        b = 0.0045 + 0.0060 * f0 + 0.0055 * f1
        return K.superellipse(a, b, 2.6, 28)
    return K.sweep_var(path, prof, name="Guard")


def build_ears():
    out = []
    for s in (1, -1):
        e = prism([(-0.0220, -0.0140), (-0.0220, -0.0118), (-0.0190, -0.0082), (-0.0085, -0.0082),
                   (-0.0056, -0.0105), (-0.0056, -0.0140)], s * 0.0034, s * (TANG_W - 0.0001), bevel=0.0009, seg=1,
                  corner=25, name="Ear")
        out.append(fix_normals(e))
    return out


def build_frame_rails():
    out = []
    for x0, x1 in ((0.0010, 0.0500), (0.1220, 0.1900)):
        for s in (1, -1):
            out.append(box(x0, x1, min(s * 0.0082, s * 0.0100), max(s * 0.0082, s * 0.0100), -0.0139, -0.0110,
                           bevel=0.00025))
    return out


def mag_base():
    return np.array([mag_centre_x(BUTT_Z), 0.0, BUTT_Z])


def mag_body_solid(half_w_, half_d, t0, t1, name="MagSolid", r=0.0030):
    b = mag_base()
    sec = geo.fillet([(-half_d, -half_w_), (half_d, -half_w_), (half_d, half_w_), (-half_d, half_w_)], r, 3, closed=True)
    rings = []
    for t in (t0, t1):
        c = b + A * t
        rings.append([tuple(c + F * u + np.array([0, 1.0, 0]) * v) for u, v in sec])
    return loft(rings, name=name)


def nine_frame(parts):
    up = build_upper_frame()
    grip = build_grip()
    dc = build_dust_cover()
    guard = build_guard()
    union(up, grip, dc, guard, *build_ears())
    hammer_slot = box(-0.0255, 0.0040, -0.0035, 0.0035, -0.0220, 0.0)
    trig = box(0.0835, 0.0985, -0.0036, 0.0036, -0.0370, -0.0245, bevel=0.0005)
    well = mag_body_solid(0.0103, 0.0174, -0.004, 0.090, name="Well")
    cut(up, hammer_slot, trig, well)
    for r in build_frame_rails():
        union(up, r)
    round_edges(up, 0.00035, 2, 40)
    parts.append(P(up, BLACKOX, "frame"))
    nine_panels(parts)
    # pins: trigger pin through the upper frame, hammer pin in the ears
    for s in (1, -1):
        y = float(upper_hw(NN["trigger_pivot"][0], NN["trigger_pivot"][2]))
        parts.append(P(pin_head((NN["trigger_pivot"][0], s * y, NN["trigger_pivot"][2]), "Y", r=0.0016, h=0.0003, sign=s),
                       DARK, "frame"))
        parts.append(P(pin_head((NN["hammer_pivot"][0], s * TANG_W, NN["hammer_pivot"][2]), "Y", r=0.0019, h=0.0004,
                                sign=s), DARK, "frame"))
    nine_controls(parts)


def plate(outline, y0, t, name="Plate", fillet=0.0008, bevel=0.0003):
    """Left-side lever plate: outline (x, z), inner face at y0, thickness t (both +Y)."""
    return fix_normals(prism(outline, y0, y0 + t, bevel=bevel, seg=2, fillet=fillet, name=name))


def serrate(ob, xs, width, y0, y1, z0, z1):
    """Cut cross serrations: one groove box per x (width along X) spanning y0..y1, z0..z1."""
    cut(ob, *[box(x - width / 2, x + width / 2, y0, y1, z0, z1) for x in xs])
    return ob


def nine_controls(parts):
    """Thumb safety, takedown lever and magazine button (frame bone; the slide stop has its own bone)."""
    y0 = float(upper_hw(0.010, -0.018)) + 0.0003
    # thumb safety: shaft boss at X 0.008, lever plate forward to a 3 mm pad that flares out beside the slide
    lev = plate([(0.0045, -0.0215), (0.0120, -0.0222), (0.0230, -0.0205), (0.0300, -0.0190), (0.0300, -0.0150),
                 (0.0200, -0.0144), (0.0080, -0.0142), (0.0045, -0.0160)], y0, 0.0013, "Safety")
    pad = K.loft_x([K.poly_section([(y0 + 0.0008, -0.0200), (y0 + 0.0022, -0.0196), (y0 + 0.0032, -0.0172),
                                    (y0 + 0.0034, -0.0124), (y0 + 0.0024, -0.0112), (y0 + 0.0016, -0.0136)], K=120)] * 2,
                   [0.0215, 0.0300], 60, name="SafetyPad")
    K.deform(pad, lambda co: np.c_[co[:, 0], co[:, 1] + 0.0003 * K.smoothstep(co[:, 0], 0.0215, 0.0300) *
                                   (co[:, 1] > y0 + 0.002), co[:, 2]])
    union(lev, pad)
    serrate(lev, [0.0228 + k * 0.0016 for k in range(5)], 0.0006, y0 + 0.0018, y0 + 0.010, -0.0118, -0.0100)
    round_edges(lev, 0.00018, 2, 40)
    parts.append(P(lev, DARK, "frame"))
    boss = lathe([(-0.0003, 0.0), (-0.0003, 0.0036), (0.0010, 0.0036), (0.0016, 0.0030), (0.0018, 0.0012),
                  (0.0018, 0.0)], 40, axis="Y", at=(0.0080, y0 + 0.0010, -0.0180), fillet=0.00015)
    parts.append(P(boss, DARK, "frame"))
    # takedown lever above the trigger (left): boss and a short lever with a ridge
    yt = float(upper_hw(0.115, -0.022)) + 0.0002
    tk = plate([(0.1060, -0.0250), (0.1140, -0.0262), (0.1215, -0.0245), (0.1215, -0.0185), (0.1150, -0.0178),
                (0.1060, -0.0215)], yt, 0.0011, "Takedown", fillet=0.0012)
    union(tk, box(0.1072, 0.1082, yt + 0.0008, yt + 0.0017, -0.0247, -0.0213, bevel=0.0002))
    round_edges(tk, 0.00015, 2, 40)
    parts.append(P(tk, DARK, "frame"))
    parts.append(P(lathe([(-0.0002, 0.0), (-0.0002, 0.0025), (0.0011, 0.0025), (0.0015, 0.0018), (0.0015, 0.0)], 32,
                         axis="Y", at=(0.1180, yt + 0.0009, -0.0215), fillet=0.0001), DARK, "frame"))
    # magazine button (left) in the panel's relief, a turned ring round it
    yb = FRAME_W
    btn = lathe([(0.0, 0.0), (0.0, 0.0048), (0.0010, 0.0048), (0.0016, 0.0043), (0.0019, 0.0032), (0.0020, 0.0)], 40,
                axis="Y", at=(BUTTON[0], yb - 0.0006, BUTTON[1]), fillet=0.0002)
    parts.append(P(btn, DARK, "frame"))
    ring = lathe([(0.0, 0.0050), (0.0, 0.0057), (0.0004, 0.0057), (0.0005, 0.0050)], 40, axis="Y", closed=True,
                 at=(BUTTON[0], yb - 0.0002, BUTTON[1]))
    parts.append(P(fix_normals(ring), BLACKOX, "frame"))


# ------------------------------------------------------------------------------------------------- slide

SLIDE_TOP = 0.0125


def flank_w(x, z):
    """Slide half width at (x, z) (the outer flank of slide_section)."""
    w = 0.0135
    nose = max(0.0, x - 0.1830) * math.tan(math.radians(17.0))
    rear = max(0.0, 0.0015 - x) * 0.8
    taper = np.clip((z - 0.0030) / (SLIDE_TOP - 0.0030), 0, 1) * 0.0005
    return w - nose - rear - taper


def slide_section(x):
    """Outer slide section in (y, z): 27 mm wide, 3 mm top radii, upper flanks tapered 0.5 mm, 0.6 mm lower
    edge breaks; the 17 deg nose bevel narrows the front 13 mm."""
    w = 0.0135
    nose = max(0.0, x - 0.1830) * math.tan(math.radians(17.0))
    rear = max(0.0, 0.0015 - x) * 0.8
    w2 = w - nose - rear
    top = SLIDE_TOP - rear - max(0.0, x - 0.1930) * 0.25
    sec = K.rrect(-0.0135 + rear * 0.5, top, w2, 0.0006, 0.0030)
    P_ = sec.P.copy()
    zz, yy = P_[:, 0].copy(), P_[:, 1].copy()
    taper = np.clip((zz - 0.0030) / (top - 0.0030), 0, 1) * 0.0005
    yy = np.sign(yy) * np.maximum(np.abs(yy) - taper, 0)
    return K.Section(np.stack([yy, zz], 1), sec.s, sec.L)


def serration_cutter(xc, side, width=0.0014, depth=0.0011, z0=-0.0120, z1=0.0090):
    zs = np.linspace(z0, z1, 10)
    inner = [(side * (flank_w(xc, z) - depth), z) for z in zs]
    poly = inner + [(side * 0.025, z1), (side * 0.025, z0)]
    if side < 0:
        poly = poly[::-1]
    sec = K.poly_section(poly, K=120)
    return K.loft_x([sec, sec], [xc - width / 2, xc + width / 2], 24, name="Ser")


def dovetail(xa, xb, depth=0.0015, ang=60.0):
    """Dovetail slot across the slide (along Y): top width xa..xb at the slide top, wider at the bottom."""
    u = depth / math.tan(math.radians(ang))
    z0 = SLIDE_TOP - depth
    return prism([(xa - u, z0), (xb + u, z0), (xb, SLIDE_TOP), (xb, 0.03), (xa, 0.03), (xa, SLIDE_TOP)],
                 -0.03, 0.03, bevel=0, name="Dovetail")


def dovetail_key(xa, xb, hw, depth=0.0015, ang=60.0, top=SLIDE_TOP + 0.0003, clear=0.00006):
    u = depth / math.tan(math.radians(ang))
    z0 = SLIDE_TOP - depth + clear
    return prism([(xa - u + clear, z0), (xb + u - clear, z0), (xb - clear, SLIDE_TOP), (xb - clear, top),
                  (xa + clear, top), (xa + clear, SLIDE_TOP)], -hw, hw, bevel=0.0001, seg=1, name="Key")


def nine_slide(parts):
    xs = np.r_[0.0, 0.0004, 0.0010, 0.0016, np.arange(0.003, 0.183, 0.0060), np.arange(0.183, 0.1955, 0.0016), 0.196]
    secs = [slide_section(x) for x in xs]
    sl = K.loft_x(secs, xs, 76, name="Slide")
    chan = box(0.0045, 0.250, -0.0104, 0.0104, -0.020, 0.0100)
    ham_chan = box(-0.001, 0.048, -0.00475, 0.00475, 0.0005, 0.0108)        # hammer channel: 9.5 mm at the spur,
    ham_neck = box(-0.001, 0.048, -0.0034, 0.0034, -0.020, 0.0010)          # 6.8 mm at the neck
    rails = box(-0.001, 0.0050, -0.0104, 0.0104, -0.020, -0.0075)           # frame ears and rails pass under the breech
    nose = lathe([(0.15, 0.0), (0.15, 0.0072), (0.25, 0.0072), (0.25, 0.0)], 48)
    rod = lathe([(0.15, 0.0), (0.15, 0.0034), (0.25, 0.0034), (0.25, 0.0)], 32, at=(0, 0, -0.0118))
    # ejection port: top view and side view outlines (1.2 mm corners) intersected
    pa = prism([(0.0860, -0.030), (0.1260, -0.030), (0.1260, 0.0042), (0.0860, 0.0042)], -0.003, 0.030, axis="Z",
               bevel=0, fillet=0.0012, name="PortA")
    pb = prism([(0.0860, -0.0030), (0.1260, -0.0030), (0.1260, 0.030), (0.0860, 0.030)], -0.030, 0.010, bevel=0,
               fillet=0.0012, name="PortB")
    geo.boolean(pa, pb, "INTERSECT", "EXACT")
    ext_slot = prism([(0.0576, 0.0028), (0.0852, 0.0028), (0.0870, 0.0038), (0.0870, 0.0062), (0.0852, 0.0070),
                      (0.0576, 0.0070)], -0.020, -(0.0135 - 0.0012), bevel=0, fillet=0.0010, name="ExtSlot")
    sers = [serration_cutter(0.0065 + k * 0.0028, s) for s in (1, -1) for k in range(9)]
    cut(sl, chan, ham_chan, ham_neck, rails, nose, rod, pa, ext_slot, dovetail(0.0070, 0.0180), dovetail(0.1825, 0.1895), *sers)
    # 0.5 mm chamfer round the port mouth, then 0.2 mm edge breaks everywhere
    K.bevel_where(sl, 0.0005, 1, 35.0, where=lambda c: (c[:, 0] > 0.0850) & (c[:, 0] < 0.1270) & (c[:, 1] < 0.0046)
                  & (c[:, 2] > -0.0035) & ((c[:, 2] > 0.0099) | (c[:, 1] < -0.0128)))
    round_edges(sl, 0.00018, 2, 40)
    parts.append(P(sl, STAINLESS, "slide"))
    # sights: rear notch 4.2 x 3.9, top Z 0.0185, X 0.007..0.018; front blade 3.4 wide, top X 0.1835..0.1885
    rs = prism([(0.0060, 0.0120), (0.0190, 0.0120), (0.0190, 0.0140), (0.0178, 0.0185), (0.0070, 0.0185),
                (0.0060, 0.0172)], -0.0098, 0.0098, bevel=0.0005, seg=2, name="RearSight")
    union(rs, dovetail_key(0.0070, 0.0180, 0.0098))
    cut(rs, box(0.0, 0.03, -0.0021, 0.0021, 0.0146, 0.03))
    round_edges(rs, 0.0002, 1, 50)
    parts.append(P(rs, DARK, "slide"))
    fs = prism([(0.1820, 0.0098), (0.1900, 0.0098), (0.1888, 0.0150), (0.1885, 0.0185), (0.1835, 0.0185),
                (0.1830, 0.0140)], -0.0017, 0.0017, bevel=0.0003, seg=2, name="FrontSight")
    base = box(0.1818, 0.1902, -0.0048, 0.0048, 0.0115, 0.0128, bevel=0.0004)
    union(fs, base, dovetail_key(0.1825, 0.1895, 0.0048, top=0.0118))
    parts.append(P(fs, DARK, "slide"))
    # extractor: spring-steel plate 0.3 mm proud in its slot (0.2 mm gap), claw hooking into the port, pin
    yo = -(0.0135 + 0.0003)
    ex = prism([(0.0578, 0.0030), (0.0850, 0.0030), (0.0868, 0.0040), (0.0868, 0.0060), (0.0850, 0.0068),
                (0.0578, 0.0068)], yo, -(0.0135 - 0.0012), bevel=0.00022, seg=2, fillet=0.0008, name="Extractor")
    claw = prism([(0.0858, 0.0036), (0.0880, 0.0036), (0.0880, 0.0060), (0.0858, 0.0060)], yo + 0.0004, -0.0098,
                 bevel=0.0002, seg=1, name="Claw")
    union(ex, claw)
    parts.append(P(ex, STAINLESS, "slide"))
    parts.append(P(pin_head((0.0630, yo, 0.0049), "Y", r=0.0010, h=0.00015, sign=-1, seg=16), DARK, "slide"))


# ------------------------------------------------------------------------------------------------- moving parts

HAMMER = [(-0.0205, 0.0105), (-0.0258, 0.0091), (-0.0277, 0.0075), (-0.0289, 0.0051), (-0.0292, 0.0026),
          (-0.0286, 0.0006), (-0.0266, -0.0004), (-0.0240, -0.0010), (-0.0217, -0.0030), (-0.0203, -0.0065),
          (-0.0201, -0.0105), (-0.0206, -0.0150), (-0.0150, -0.0195), (-0.0090, -0.0170), (-0.0073, -0.0110),
          (-0.0075, -0.0062), (-0.0087, -0.0028), (-0.0110, 0.0012), (-0.0135, 0.0052), (-0.0160, 0.0086),
          (-0.0184, 0.0103)]


def build_hammer():
    """One forged hammer: body 6 mm wide widening to a 9 mm spur along an S, R 9.5 back, flat thumb face."""
    pts = geo.fillet(HAMMER, 0.0006, 3, closed=True)
    ham = K.slab(pts, -1.0, 1.0, step=0.0013, name="Hammer")

    def fn(co):
        hw = 0.0030 + 0.0015 * K.smoothstep(co[:, 2], 0.0006, 0.0060)
        co[:, 1] = np.sign(co[:, 1]) * hw
        return co
    K.deform(ham, fn)
    K.outward(ham)
    round_edges(ham, 0.0003, 2, 35)
    return ham


def nine_moving(parts):
    # slide stop (left, X 0.058..0.100): 1.3 mm plate 0.3 mm off the frame, thickening to the pad; 4 mm thumb
    # shelf with five cross serrations; pivot boss
    y0 = float(upper_hw(0.080, -0.017)) + 0.0003
    st = plate([(0.0585, -0.0205), (0.0700, -0.0206), (0.0900, -0.0200), (0.0975, -0.0198), (0.0995, -0.0180),
                (0.0995, -0.0152), (0.0975, -0.0142), (0.0700, -0.0142), (0.0598, -0.0142), (0.0585, -0.0160)],
               y0, 0.0013, "SlideStop", fillet=0.0012)
    K.deform(st, lambda co: np.c_[co[:, 0], np.where(co[:, 1] > y0 + 0.0006, co[:, 1] + 0.0005 *
                                                     K.smoothstep(0.0760 - co[:, 0], 0.0, 0.012), co[:, 1]), co[:, 2]])
    shelf = K.loft_x([K.poly_section([(y0 + 0.0010, -0.0204), (y0 + 0.0026, -0.0204), (y0 + 0.0033, -0.0196),
                                      (y0 + 0.0033, -0.0170), (y0 + 0.0026, -0.0163), (y0 + 0.0010, -0.0163)], K=120)] * 2,
                     [0.0588, 0.0700], 60, name="Shelf")
    union(st, shelf)
    serrate(st, [0.0602 + k * 0.0020 for k in range(5)], 0.0007, y0 + 0.0029, y0 + 0.010, -0.0210, -0.0160)
    round_edges(st, 0.00018, 2, 40)
    parts.append(P(st, DARK, "slide_stop"))
    parts.append(P(lathe([(-0.0003, 0.0), (-0.0003, 0.0030), (0.0008, 0.0030), (0.0012, 0.0024), (0.0012, 0.0)], 32,
                         axis="Y", at=(NN["stop_pivot"][0], y0 + 0.0013, NN["stop_pivot"][2]), fillet=0.0001),
                   DARK, "slide_stop"))
    ham = build_hammer()
    parts.append(P(ham, DARK, "hammer"))
    pin = lathe([(-0.0031, 0.0), (-0.0031, 0.0010), (0.0031, 0.0010), (0.0031, 0.0)], 20, axis="Y",
                at=(-0.0165, 0.0, -0.0040), fillet=0.0002)
    parts.append(P(pin, POLISHED, "hammer"))
    # gold trigger: curved blade, rounded edges
    t = [(0.0870, -0.0290), (0.0950, -0.0290), (0.0965, -0.0380), (0.0955, -0.0460), (0.0920, -0.0545),
         (0.0880, -0.0600), (0.0850, -0.0590), (0.0878, -0.0530), (0.0898, -0.0455), (0.0895, -0.0380)]
    trg = prism(t, -0.0031, 0.0031, bevel=0.0010, seg=3, fillet=0.0012, name="Trigger")
    parts.append(P(trg, GOLD, "trigger"))


# ------------------------------------------------------------------------------------------------- magazine

def butt_footprint(over=0.0003):
    """Pad footprint: the butt section (with the straps' bulges) grown by `over`."""
    sec = grip_section(BUTT_Z)
    return sec.x0 - 0.0011 - over, sec.x1 + 0.0007 + over, 0.0130


def nine_magazine(col):
    """SM_Weapon_NineMagazine (+ _TopRound) on the brief's line: brushed body 19.5 x 34 mm with three witness holes
    per side, feed lips, the stack, and the gold base pad under the butt."""
    b = mag_base()
    top_t = (-0.037 - b[2]) / A[2]
    Wm, D = 0.00975, 0.017
    parts = []
    sec = [(-D, -Wm), (D - 0.004, -Wm), (D, -Wm + 0.004), (D, Wm - 0.004), (D - 0.004, Wm), (-D, Wm)]
    sec = geo.fillet(sec, 0.0018, 3, closed=True)
    inner = [(u * (D - 0.0007) / D, v * (Wm - 0.0007) / Wm) for u, v in sec]
    ring = lambda t, s: [tuple(b + A * t + F * u + np.array([0, 1.0, 0]) * v) for u, v in s]

    def ring_flat(zt, s):
        out = []
        for u, v in s:
            c = b + F * u + np.array([0, 1.0, 0]) * v
            out.append(tuple(c + A * ((zt - c[2]) / A[2])))
        return out
    body = loft([ring_flat(BUTT_Z - 0.0030, sec), ring(top_t - 0.004, sec)], cap0=True, cap1=False, name="NMagBody")
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
    parts.append(P(build_pad(), GOLD, None))
    body = geo.join(parts, "SM_Weapon_NineMagazine", col)
    ctop = b + A * top_t
    top = W.cartridge(0.030, 0.0048, name="SM_Weapon_NineMagazine_TopRound", rifle=False)
    geo.transform(top, loc=(ctop[0] - 0.0175, 0.0, -0.0335))
    W.scene.move_to(top, col)
    top.name = top.data.name = "SM_Weapon_NineMagazine_TopRound"
    return body, top


def build_pad():
    """Gold base pad 75 x 26 x 7 mm under the butt: 2 mm top radii, a 0.5 mm parting line, a finger flare at the
    front, 2 mm bottom edge radii and a 1.5 mm domed bottom."""
    x0, x1, wp = butt_footprint()
    rings = []                                        # (z, inset, flare)

    def flare(z):
        return 0.0010 * float(np.clip((BUTT_Z - 0.0030 - z) / 0.0040, 0, 1)) ** 1.4
    r = 0.0020
    for d in (0.0, 0.0001, 0.0003, 0.0006, 0.0010, 0.0015, 0.0020):
        rings.append((BUTT_Z - d, r - math.sqrt(max(0.0, r * r - (r - d) ** 2))))
    rings += [(BUTT_Z - 0.0026, 0.0), (BUTT_Z - 0.00265, 0.0003), (BUTT_Z - 0.00315, 0.0003), (BUTT_Z - 0.0032, 0.0)]
    zb = PAD_Z + 0.0015                               # the edge of the dome
    for d in (0.0, 0.0006, 0.0012):
        rings.append((zb + 0.0020 - d, 0.0))
    for a_ in np.linspace(0.15, 1.0, 6):              # 2 mm edge radius
        ang = a_ * math.pi / 2
        rings.append((zb + 0.0020 - 0.0020 * math.sin(ang), 0.0020 * (1 - math.cos(ang))))
    for q in (0.0035, 0.0055, 0.0075, 0.0095, 0.0112, 0.0124):   # dome toward the centre
        rings.append((zb - 0.0015 * (1 - (1 - q / 0.0126) ** 2) ** 0.5, q))
    rings.sort(key=lambda t: -t[0] + 1e-6 * t[1])
    zs = [z for z, _ in rings]
    secs = []
    for z, ins in rings:
        fl = flare(z)
        secs.append(K.rrect(x0 + ins, x1 + fl - ins, wp - ins, max(0.0062 - ins * 0.6, 0.0008),
                            max(0.0062 - ins * 0.6, 0.0008)))
    return K.loft_z(secs, zs, 96, name="Pad")


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


# ------------------------------------------------------------------------------------------------- slide UVs

def straighten_slide_uv(ob, margin_px=6):
    """Re-map the slide's outer skin (both flanks and the top, one connected surface) as a single straightened UV
    shell: U along X (the brushing direction, so Unreal's tangent runs along the slide), V the arc length round the
    section. The shell keeps the smart-project texel scale, is pinned for rotation, and every island is re-packed.
    Faces inside the serrations, port, dovetails and slots keep their own islands. Returns the shell's face count."""
    import bpy
    me = ob.data
    vg = ob.vertex_groups.get("slide")
    if vg is None:
        return 0
    nv = len(me.vertices)
    w = np.zeros(nv)
    for v in me.vertices:
        for g in v.groups:
            if g.group == vg.index:
                w[v.index] = g.weight
    co = np.empty(nv * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    npoly = len(me.polygons)
    mid = np.empty(npoly, np.float32)
    me.attributes["mid"].data.foreach_get("value", mid)
    cen = np.empty(npoly * 3)
    me.polygons.foreach_get("center", cen)
    cen = cen.reshape(-1, 3)
    nrm = np.empty(npoly * 3)
    me.polygons.foreach_get("normal", nrm)
    nrm = nrm.reshape(-1, 3)
    ls = np.empty(npoly, np.int32)
    lt = np.empty(npoly, np.int32)
    me.polygons.foreach_get("loop_start", ls)
    me.polygons.foreach_get("loop_total", lt)
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", lv)
    uv = np.empty(len(me.loops) * 2, np.float32)
    lay = me.uv_layers.active
    lay.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)

    def contour(x):
        sec = slide_section(x)
        N_ = sec.N * (1.0 if sec.N[np.argmax(sec.P[:, 1]), 1] > 0 else -1.0)      # outward
        return sec.P, sec.s, N_, sec.L
    stations = np.r_[np.arange(0.0, 0.183, 0.01), np.arange(0.183, 0.1961, 0.002)]
    refs = [contour(x) for x in stations]

    def param(pts):
        """(n, 3) -> s (n,), distance (n,), contour normal (n, 2) on the station nearest in x."""
        s_out = np.zeros(len(pts))
        d_out = np.zeros(len(pts))
        n_out = np.zeros((len(pts), 2))
        k = np.clip(np.searchsorted(stations, pts[:, 0]), 0, len(stations) - 1)
        for j in np.unique(k):
            m = k == j
            C, S, N, L = refs[j]
            q = pts[m][:, 1:3]
            d2 = ((q[:, None, :] - C[None]) ** 2).sum(-1)
            i = d2.argmin(1)
            s_out[m] = S[i]
            d_out[m] = np.sqrt(d2[np.arange(len(i)), i])
            n_out[m] = N[i]
        return s_out, d_out, n_out
    pv = np.array([w[me.polygons[i].vertices].min() for i in range(npoly)])
    cand = np.nonzero((np.rint(mid) == STAINLESS) & (pv > 0.5) & (cen[:, 0] > 0.0005) & (cen[:, 0] < 0.1955)
                      & (np.abs(nrm[:, 0]) < 0.3))[0]
    s_c, d_c, n_c = param(cen[cand])
    agree = (nrm[cand, 1] * n_c[:, 0] + nrm[cand, 2] * n_c[:, 1]) > 0.93
    sel = cand[agree & (d_c < 0.00045)]
    if not len(sel):
        return 0
    # texel scale of the current layout (UV units per metre) from the stainless faces
    ratios = []
    for i in cand[:4000]:
        idx = np.arange(ls[i], ls[i] + lt[i])
        if lt[i] < 3:
            continue
        a3 = me.polygons[i].area
        p = uv[idx]
        a2 = 0.5 * abs(np.dot(p[:, 0], np.roll(p[:, 1], -1)) - np.dot(p[:, 1], np.roll(p[:, 0], -1)))
        if a3 > 1e-10 and a2 > 0:
            ratios.append(a2 / a3)
    kuv = math.sqrt(float(np.median(ratios)))
    loops = np.concatenate([np.arange(ls[i], ls[i] + lt[i]) for i in sel])
    s_l, _d, _n = param(co[lv[loops]])
    uv[loops, 0] = 2.0 + co[lv[loops], 0] * kuv
    uv[loops, 1] = s_l * kuv
    lay.data.foreach_set("uv", uv.ravel())
    print("    slide shell before packing: corr(x, u) %.3f" % np.corrcoef(co[lv[loops], 0], uv[loops, 0])[0, 1], flush=True)
    pin = np.zeros(len(me.loops), bool)
    pin[loops] = True
    lay.pin_ensure()
    lay.pin.foreach_set("value", pin)
    W.scene.select_only(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    import os
    if os.environ.get("MI_SHELL_DEBUG"):
        bm = W.bmesh.from_edit_mesh(me)
        uvl = bm.loops.layers.uv.active
        npin = sum(1 for f in bm.faces for l in f.loops if l[uvl].pin_uv)
        print("    pinned loops in edit mode:", npin, flush=True)
    # other islands may turn; the pinned shell keeps its rotation (U along +X)
    bpy.ops.uv.pack_islands(rotate=True, rotate_method="ANY", margin_method="FRACTION", margin=margin_px / 2048.0,
                            shape_method="AABB", pin=True, pin_method="ROTATION")
    bpy.ops.object.mode_set(mode="OBJECT")
    lay = me.uv_layers.active                       # layer references do not survive edit mode
    pa = me.attributes.get(".pn." + lay.name)
    if pa is not None:
        me.attributes.remove(pa)
    # report the shell's direction after packing (U should still run along X)
    lay = me.uv_layers.active
    uv = np.empty(len(me.loops) * 2, np.float32)
    lay.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    # per face: does U follow +X? (edge vectors: d(u) against d(x), d(v) against d(x))
    good, n_ = 0, 0
    for i in sel:
        idx = np.arange(ls[i], ls[i] + lt[i])
        dx = np.diff(co[lv[idx], 0], append=co[lv[idx[0]], 0])
        du_ = np.diff(uv[idx, 0], append=uv[idx[0], 0])
        dv_ = np.diff(uv[idx, 1], append=uv[idx[0], 1])
        if np.abs(dx).max() < 1e-6:
            continue
        n_ += 1
        good += float(np.dot(dx, du_)) > 0 and abs(float(np.dot(dx, dv_))) < 0.2 * abs(float(np.dot(dx, du_)))
    print("    slide shell: %d faces, U along +X on %.1f %% of them" % (len(sel), 100.0 * good / max(n_, 1)), flush=True)
    return len(sel)


def uv_weights(ob):
    """Per-face UV scale for SK_Nine: faces the eye never sees (inside the slide, under it, in the magazine well,
    the recoil spring and the barrel under the slide) get few texels so the outside gets the density."""
    me = ob.data
    n = len(me.polygons)
    mid = np.empty(n, np.float32)
    me.attributes["mid"].data.foreach_get("value", mid)
    mid = np.rint(mid).astype(int)
    c = np.empty(n * 3, np.float32)
    me.polygons.foreach_get("center", c)
    c = c.reshape(-1, 3)
    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    w = np.ones(n, np.float32)
    w[mid == BORE] = 0.3
    w[(mid == STAINLESS) & (np.abs(y) < 0.0106) & (z < 0.0102) & (x > 0.0040) & (x < 0.1965)] = 0.3     # slide inside
    w[(mid == POLISHED) & (x > 0.127) & (x < 0.1985)] = 0.3                                               # barrel under the slide
    w[(mid == POLISHED) & (z < -0.006)] = 0.3                                                             # guide rod
    w[(mid == DARK) & (x > 0.098) & (x < 0.190) & (np.abs(y) < 0.0045) & (np.abs(z + 0.0118) < 0.0045)] = 0.3   # spring
    w[(mid == BLACKOX) & (np.abs(y) < 0.0105) & (z > -0.0140) & (x > 0.0)] = 0.3                          # frame under the slide
    inwell = np.abs((x - mag_centre_x(z)) * A[2]) < 0.0178
    w[(mid == BLACKOX) & inwell & (np.abs(y) < 0.0104) & (z < -0.036) & (z > BUTT_Z + 0.001)] = 0.3       # magazine well
    w[(mid == DARK) & (z < -0.0140) & (x < -0.006) & (x > -0.024) & (np.abs(y) < 0.0034)] = 0.4            # hammer in the frame
    return w
