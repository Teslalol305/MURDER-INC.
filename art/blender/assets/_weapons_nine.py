"""NINE, rebuild round 3: a full-size hammer-fired service pistol built the way the real class is made.

Round 3 (critique NINE 2/5: an 87-90 mm brick of a grip raked 6.5 deg, a tube for a trigger guard, a slab slide):
    grip      one horizontal-section loft from the beavertail tang to the butt, slimmed to a service pistol's
              depth: 56 mm fore-aft at mid grip (was 86-90). The back strap rakes 16 deg from a deep web cup under
              the tang (tang tip still at X -0.033: the length holds), the front strap 18 deg (19-20 deg against the
              bore with the frame's rise), R 7 undercut under the guard. Egg section: 21 mm frame, R 10.5 (the full
              half width) round the back strap, R 6 at the front strap, sides crowned 0.4 mm plus a 1.2 mm palm swell
              per side at 40 % of the grip height. Brief decision (critique): the magazine body stays on the brief's
              line (X 0.250 / Z 0.968, lips at Z -0.037, front at X 0.045) but its gold base pad is a real one, 43 mm
              long instead of the blocky model's 76 mm, so the grip no longer has to reach forward over it.
              The rear edge of the trigger-guard opening sweeps from the magazine button (X 0.0625, Z -0.0405, kept)
              down and back into the front strap, so the frame stays round the button.
    guard     D section 7 mm wide x 5 mm deep (flat sides, 1 mm breaks inside, 2.1 mm round outside) swept round a
              squared, slightly hooked front (1 mm forward at the bottom), R 8 bottom corner, straight bottom into the
              grip; it widens into R 3 fillets at the dust cover and the grip.
    frame     upper frame with a 1 mm chamfer along the top edge under the slide (a shadow line), dust cover tapered
              2 deg with R 1.5 bottom edges and three lugs between 45 deg-flanked cross slots (3 mm floor, 2 mm deep).
    panels    one surface per side following the grip (front edge follows the strap 4 mm back), 3.4 mm at the
              crown tapering to 2 mm at the edges, the checkered field recessed 0.3 mm inside a 2.5 mm border with a
              0.6 mm chamfer; 7 mm slotted screws domed 0.6 mm in dark steel bushings flush with the panel.
    slide     lofted along X: vertical flats, R 3 shoulders into 22 deg slopes and a 7 mm flat top with 0.4 mm
              breaks; nose dehorned 20 deg over its lower 60 % and broken R 1.5 on top; seven serrations 1.5 mm wide,
              1.2 mm deep at 3 mm pitch, flat-bottomed, running up into the shoulder; port with a 0.5 mm chamfer and
              a relieved rear scallop; solid nose with the barrel and spring bores; hammer channel underneath.
    barrel    the hood is a cylinder segment (R 10 crown) with a 5 mm flat top and a 2 mm witness hole.
    hammer    one forged piece: spur 6 mm thick tapering to 4.5 mm at the R 3 tip, 1.2 mm-pitch serrated thumb
              face, 4 mm lightening hole, strut behind it, 3 mm pin heads through the frame ears.
    sights    rear: dovetailed block 9 mm long on top (11 mm at the base), rear face sloped 10 deg (40 LPI lines in the
              normal map), a hex set screw; notch 4.2 x 3.9 mm, top Z 0.0185 (kept).
    magazine  body on the brief's line; one moulded gold base pad 43 x 26 x 7 mm with an R 1.5 top edge, R 3 bottom
              edge and a front lip with a 2 mm finger relief.
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
FRAME_W = 0.0105                     # grip frame half width (21 mm; panels and swell make 29.5-31 mm)
TANG_W = 0.0095                      # beavertail / hammer housing half width (19 mm)
UPPER_W = 0.01225                    # upper frame half width at the rail line (24.5 mm)
FRAME_TOP = -0.0138                  # 0.3 mm under the slide (rail line -0.0135): the shadow gap
PANEL_T = 0.0034
TOP_Z = -0.0105                      # tang top
GUARD_BOTTOM = -0.0715
GUARD_INNER = -0.0665
OPEN_REAR = 0.073
OPEN_TOP = -0.0335                   # underside of the upper frame over the opening
BAND_FRONT = 0.0545                  # grip front inside the root of the guard bar
STRAP_TAN = math.tan(math.radians(18.0))
STRAP_X80 = 0.0419                   # front strap at Z -0.080
BACK_TAN = math.tan(math.radians(16.0))
BACK_X80 = -0.0140                   # back strap at Z -0.080
UC_R = 0.007                         # undercut radius under the guard's rear
UC_Z = GUARD_BOTTOM - UC_R
UC_X = STRAP_X80 + (UC_Z + 0.080) * STRAP_TAN + UC_R / math.cos(math.radians(18.0))
UC_ZT = UC_Z + UC_R * math.sin(math.radians(18.0))      # where the undercut runs into the strap


def mag_centre_x(z):
    """x of the magazine axis at height z (the brief's line)."""
    return MAG_C0[0] + (z - MAG_C0[1]) * A[0] / A[2]


def strap_x(z):
    return STRAP_X80 + (np.asarray(z, dtype=np.float64) + 0.080) * STRAP_TAN


# side-view back curve (x, z), monotonic in z: tang tip -> underside -> web cup -> back strap (16 deg) -> heel
_BACK_PTS = [(-0.0306, -0.0105), (-0.0324, -0.0113), (-0.0330, -0.0127), (-0.0325, -0.0140), (-0.0308, -0.0150),
             (-0.0282, -0.0158), (-0.0252, -0.0167), (-0.0218, -0.0181), (-0.0182, -0.0202), (-0.0146, -0.0230),
             (-0.0112, -0.0265), (-0.0082, -0.0305), (-0.0058, -0.0350), (-0.0045, -0.0385), (-0.0040, -0.0420),
             (-0.0043, -0.0455)]
_BACK_PTS += [(BACK_X80 + (z + 0.080) * BACK_TAN, z) for z in (-0.050, -0.060, -0.070, -0.080, -0.090, -0.100,
                                                               -0.110, -0.120, BUTT_Z)]
BACK = K.spline(_BACK_PTS, 10)

# rear edge of the guard opening: from the opening's top (with an R 3 fillet) past the magazine button, sweeping
# down and back to the bar's inner face
_OPEN_PTS = K.spline([(0.0730, -0.0365), (0.0728, -0.0400), (0.0717, -0.0440), (0.0697, -0.0480), (0.0669, -0.0520),
                      (0.0635, -0.0560), (0.0600, -0.0597), (0.0572, -0.0627), (0.0556, -0.0650), (0.0550, -0.0665)], 8)


def back_x(z):
    return K.x_of_z(BACK, z)


def front_x(z):
    """Front of the grip section: buried in the frame beside the tang, the opening's rear edge (R 3 into the
    opening's top), the guard bar's root, the R 7 undercut, then the 18 deg strap."""
    z = np.asarray(z, dtype=np.float64)
    fil = OPEN_REAR + 0.003 - np.sqrt(np.clip(0.003 ** 2 - (z + 0.0365) ** 2, 0, None))
    edge = K.x_of_z(_OPEN_PTS, z)
    under = UC_X - np.sqrt(np.clip(UC_R ** 2 - (z - UC_Z) ** 2, 0, None))
    return np.select([z > -0.0256, z > -0.0335, z > -0.0365, z > GUARD_INNER, z > GUARD_BOTTOM, z > UC_ZT],
                     [-0.0045, OPEN_REAR + 0.003, fil, edge, BAND_FRONT, under], strap_x(z))


def front_r(z):
    return float(np.interp(z, [BUTT_Z, -0.0800, -0.0740, -0.0700, -0.0640, -0.0400, -0.0257, -0.0255],
                           [0.0058, 0.0060, 0.0050, 0.0035, 0.0022, 0.0022, 0.0022, 0.0020]))


def half_w(z):
    """Section half width: the 19 mm tang widens to the 21 mm grip below the web of the hand."""
    return TANG_W + (FRAME_W - TANG_W) * float(K.smoothstep(-z, 0.0195, 0.0300))


def back_r(z):
    """R 4 round the tang, the full half width (an egg's round back) on the back strap."""
    t = float(K.smoothstep(-z, 0.0160, 0.0320))
    return 0.0040 + (half_w(z) * 0.995 - 0.0040) * t


def crown(z):
    """Outward bow of the grip's sides (egg section) with the palm swell: 1.2 mm per side at 40 % of the height."""
    z = float(z)
    base = 0.0004 * float(K.smoothstep(-z, 0.034, 0.046))
    return base + 0.0012 * math.exp(-((z + 0.0740) / 0.0160) ** 2) * float(K.smoothstep(-z, 0.040, 0.052))


def grip_section(z, inset=0.0):
    zz = float(z)
    x0, x1 = float(back_x(zz)) + inset, float(front_x(zz)) - inset
    w = half_w(zz) - inset
    return K.rrect(x0, x1, w, back_r(zz) - inset * 0.8, front_r(zz) - inset * 0.8,
                   bulge_f=0.0006 if zz < GUARD_BOTTOM else 0.0, crown=crown(zz))


def grip_levels():
    z = list(np.arange(TOP_Z, BUTT_Z, -0.0013))
    z += [TOP_Z - d for d in (0.00005, 0.0002, 0.0004, 0.0007, 0.0011, 0.0015)]
    z += [-0.0255, -0.0257, -0.0334, -0.0336, -0.0345, -0.0355, -0.0365, GUARD_INNER + 0.0004, GUARD_INNER,
          GUARD_INNER - 0.0004, GUARD_BOTTOM + 0.0004, GUARD_BOTTOM, GUARD_BOTTOM - 0.0003, GUARD_BOTTOM - 0.0010,
          GUARD_BOTTOM - 0.0020, GUARD_BOTTOM - 0.0032, UC_ZT, UC_ZT - 0.0010]
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
    g = K.loft_z(secs, zs, 72, name="Grip")
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

PANEL_TOP, PANEL_BOT = -0.0345, -0.1235
BUTTON = (0.0625, -0.0405)
PANEL_CAP = 0.0545                   # the panel's top front stays behind the magazine button
SCREWS = ((0.0245, -0.0450), (0.0040, -0.1135))
PANEL_FIELD = {}                     # side -> (zs, x (nz, nu), d_edge (nz, nu)) for the painter
BORDER = 0.0025                      # smooth border round the checkering
_DB = np.array([0.0, 0.00015, 0.0004, 0.0008, 0.0013, 0.0019, 0.0023, 0.0026, 0.0029, 0.0032, 0.0036])


def panel_front_x(z):
    """Side-view x of the panel's front edge: 4 mm behind the strap, capped behind the magazine button."""
    z = np.asarray(z, dtype=np.float64)
    r = 0.0062
    sc = BUTTON[0] - np.sqrt(np.clip(r * r - (z - BUTTON[1]) ** 2, 0, None))
    return np.minimum.reduce([np.full(z.shape, PANEL_CAP), front_x(z) - 0.0040,
                              np.where(np.abs(z - BUTTON[1]) < r, sc, 1.0)])


def _panel_rows():
    hz = PANEL_TOP - PANEL_BOT
    mid = np.linspace(PANEL_TOP - 0.0040, PANEL_BOT + 0.0040, int(round((hz - 0.008) / 0.0014)) + 1)
    return np.r_[PANEL_TOP - _DB, mid, (PANEL_BOT + _DB)[::-1]]


def build_panel(side):
    """Grip panel on one side (side=-1 right, +1 left): a surface over the frame's side, wrapping 3 mm round the
    back corner and round the front corner along the strap; 2 mm at the edges rising to 3.4 mm at the crown, a
    rounded edge, the checkered field 0.3 mm down inside a 2.5 mm border with a 0.6 mm chamfer. An open shell (its
    back sits in the frame); vertices are placed at the border distances so the chamfer is crisp."""
    zs = _panel_rows()
    nz = len(zs)
    wrap = 0.0030
    # side limits on a fine uniform grid, smoothed, then sampled at the rows
    zf = np.arange(PANEL_TOP, PANEL_BOT - 1e-9, -0.0005)
    s0f, s1f = [], []
    for z in zf:
        sec = grip_section(z)
        a, b = sec.marks["right"]
        x_start = sec.x0 + sec.rb
        sf = a + (float(panel_front_x(z)) - x_start)
        s0f.append(a - wrap)
        s1f.append(min(sf, b + 0.0045))
    k = np.exp(-0.5 * (np.arange(-8, 9) / 3.0) ** 2)
    k /= k.sum()
    s0f = np.convolve(np.pad(np.array(s0f), 8, mode="edge"), k, mode="valid")
    s1f = np.convolve(np.pad(np.array(s1f), 8, mode="edge"), k, mode="valid")
    s0 = np.interp(-zs, -zf, s0f)
    s1 = np.interp(-zs, -zf, s1f)

    def corner(d, R):
        return np.where(d < R, R - np.sqrt(np.clip(R ** 2 - (R - d) ** 2, 0, None)), 0.0)
    dz_top, dz_bot = np.abs(zs - PANEL_TOP), np.abs(zs - PANEL_BOT)
    s0 = s0 + np.maximum(corner(dz_top, 0.005), corner(dz_bot, 0.006))
    s1 = s1 - np.maximum(corner(dz_top, 0.010), corner(dz_bot, 0.007))
    nm = 26
    nu = 2 * len(_DB) + nm
    outer = np.zeros((nz, nu, 3))
    nrm = np.zeros((nz, nu, 3))
    dmap = np.zeros((nz, nu))
    hz_ = (PANEL_TOP - PANEL_BOT) / 2
    zm = (PANEL_TOP + PANEL_BOT) / 2
    for i, z in enumerate(zs):
        sec = grip_section(z)
        L = s1[i] - s0[i]
        du = np.r_[_DB, np.linspace(0.0040, L - 0.0040, nm), L - _DB[::-1]]
        s = s0[i] + du
        d_side = np.minimum(du, L - du)
        uu = du / L
        if side > 0:
            s = sec.L / 2 + (sec.L / 2 - s)
            s, d_side, uu = s[::-1], d_side[::-1], uu[::-1]
        p = sec.at(s)
        n = sec.normal_at(s)
        d_edge = np.minimum(d_side, min(dz_top[i], dz_bot[i]))
        cr = np.clip(1 - (2 * uu - 1) ** 2, 0, 1) ** 0.75 * (1 - 0.35 * ((z - zm) / hz_) ** 2)
        t_core = 0.0020 + (PANEL_T - 0.0020) * cr
        re = 0.0012
        q = np.clip(d_edge / re, 0, 1)
        t = 0.0005 + (t_core - 0.0005) * np.sqrt(1 - (1 - q) ** 2)
        t -= 0.0003 * np.clip((d_edge - BORDER) / 0.0006, 0, 1)          # the field, down a 0.6 mm chamfer
        outer[i, :, 0] = p[:, 0] + n[:, 0] * t
        outer[i, :, 1] = p[:, 1] + n[:, 1] * t
        outer[i, :, 2] = z
        nrm[i, :, 0], nrm[i, :, 1] = n[:, 0], n[:, 1]
        dmap[i] = d_edge
    PANEL_FIELD[side] = (zs.copy(), outer[:, :, 0].copy(), dmap.copy())
    # boundary wall down into the frame
    ring = [(0, j) for j in range(nu)] + [(i, nu - 1) for i in range(1, nz)] + \
        [(nz - 1, j) for j in range(nu - 2, -1, -1)] + [(i, 0) for i in range(nz - 2, 0, -1)]
    V = list(outer.reshape(-1, 3))
    base = len(V)
    for (i, j) in ring:
        V.append(outer[i, j] - nrm[i, j] * 0.0012)
    o = lambda i, j: i * nu + j
    faces = []
    for i in range(nz - 1):
        for j in range(nu - 1):
            faces.append((o(i, j), o(i, j + 1), o(i + 1, j + 1), o(i + 1, j)))
    m = len(ring)
    for r in range(m):
        a, b = ring[r], ring[(r + 1) % m]
        faces.append((o(*b), o(*a), base + r, base + (r + 1) % m))
    ob = geo.from_arrays("Panel", np.array(V), faces, smooth=None)
    bm = geo.bm_of(ob)
    W.bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.faces.ensure_lookup_table()
    f0 = bm.faces[(nz // 2) * (nu - 1) + nu // 2]
    if f0.normal.y * side < 0:
        for f in bm.faces:
            f.normal_flip()
    geo.bm_to(ob, bm)
    return ob


def panel_surface_y(pan, x, z, side):
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromObject(pan, __import__("bpy").context.evaluated_depsgraph_get())
    hit = bvh.ray_cast(Vector((x, side * 0.05, z)), Vector((0, -side, 0)), 0.1)
    return hit[0].y if hit[0] is not None else side * (FRAME_W + PANEL_T)


def nine_panels(parts):
    for side in (-1, 1):
        pan = build_panel(side)
        heads = [(x, panel_surface_y(pan, x, z, side), z) for x, z in SCREWS]
        parts.append(P(pan, POLYMER, "frame"))
        for x, y, z in heads:
            # dark steel bushing flush with the panel (0.1 mm proud, chamfered), 7 mm slotted head domed 0.6 mm
            bush = lathe([(-0.0022, 0.0), (-0.0022, 0.00365), (0.0001, 0.00365), (0.0001, 0.00425), (-0.00005, 0.0044),
                          (-0.0022, 0.0044)], 32, axis="Y", closed=True, fillet=0.00006)
            if side < 0:
                geo.transform(bush, scale=(1, -1, 1))
            geo.transform(bush, loc=(x, y, z))
            parts.append(P(fix_normals(bush), DARK, "frame"))
            prof = [(-0.0020, 0.0), (-0.0020, 0.0035), (-0.0001, 0.0035), (0.00005, 0.0034)]
            prof += [(0.00005 + 0.0006 * (1 - (r / 0.0034) ** 2), r) for r in (0.0030, 0.0024, 0.0017, 0.0009, 0.0)]
            head = lathe(prof, 32, axis="Y", fillet=0.00008)
            cut(head, box(-0.0040, 0.0040, -0.00035, 0.002, -0.00045, 0.00045))
            if side < 0:
                geo.transform(head, scale=(1, -1, 1))
            geo.transform(head, rot=(0, 30 if side > 0 else -55, 0))
            geo.transform(head, loc=(x, y, z))
            parts.append(P(fix_normals(head), DARK, "frame"))


# ------------------------------------------------------------------------------------------------- frame

def upper_hw(x, z):
    """Upper frame half width: 24.5 mm at the rail line with 2.5 deg draft and a 1 mm chamfer along the top edge
    (a shadow line under the slide); it narrows to the grip's width behind the slide."""
    w = UPPER_W - np.clip(FRAME_TOP - z, 0, None) * 0.044
    w = w - np.clip(z - (FRAME_TOP - 0.0010), 0, None)
    # the web over the guard opening steps in 1.7 mm below the dust-cover line (a forged contour, not a plate)
    w = w - 0.0017 * K.smoothstep(-z, 0.0258, 0.0288) * K.smoothstep(x, 0.066, 0.078) * K.smoothstep(0.1300 - x, 0.0, 0.008)
    gw = np.array([half_w(v) for v in np.atleast_1d(z)]).reshape(np.shape(z)) - 0.0002
    t = K.smoothstep(x, -0.004, 0.004)
    return gw + (w - gw) * t


def build_upper_frame():
    outline = [(-0.0060, FRAME_TOP), (0.1310, FRAME_TOP), (0.1310, -0.0240), (0.1296, -0.0262), (0.1274, -0.0302),
               (0.1250, OPEN_TOP), (OPEN_REAR, OPEN_TOP), (OPEN_REAR, -0.0350), (-0.0060, -0.0350)]
    extra = [(x, FRAME_TOP - 0.0010) for x in np.arange(-0.0055, 0.1305, 0.0020)]
    extra += [(x, FRAME_TOP - 0.0017) for x in np.arange(-0.0055, 0.1305, 0.0035)]
    extra += [(x, z) for x in np.arange(0.0640, 0.1300, 0.0016) for z in (-0.0256, -0.0266, -0.0277, -0.0290)]
    extra += [(x, z) for x in (0.0660, 0.0700, 0.0740, 0.0780, 0.1220, 0.1260, 0.1290) for z in np.arange(-0.0250, -0.0334, -0.0009)]
    ob = K.slab(outline, -1.0, 1.0, step=0.0032, name="FrameUpper", extra=extra)

    def fn(co):
        co[:, 1] = np.sign(co[:, 1]) * upper_hw(co[:, 0], co[:, 2])
        return co
    K.deform(ob, fn)
    return K.outward(ob)


DC_X0, DC_X1 = 0.1280, 0.1960


def dust_cover_section(x):
    """Dust cover section (y, z), counter-clockwise: frame flank with draft, the rail's 45 deg dovetail groove,
    21 mm rail, R 1.5 bottom edges; the bottom rises 2 deg toward the nose."""
    dz = (x - 0.1300) * math.tan(math.radians(2.0)) if x > 0.1300 else 0.0
    zb = -0.0245 + dz
    top = FRAME_TOP
    w0 = UPPER_W
    g0 = -0.0180 + dz * 0.6
    r = 0.0015
    arc_ = [(0.0106 - r + r * math.cos(a), zb + r + r * math.sin(a)) for a in np.radians([0, -22.5, -45, -67.5, -90])]
    half = [(w0 - 0.0010, top), (w0, top - 0.0010), (w0 - 0.044 * (top - g0), g0),
            (0.0094, g0 - 0.0027), (0.0094, g0 - 0.0033), (0.0106, g0 - 0.0045)] + arc_
    right = [(-y, z) for y, z in half]
    pts = [(0.0, top)] + right + [(0.0, zb)] + [(y, z) for y, z in half[::-1]]
    return K.poly_section(pts, K=260)


def build_dust_cover():
    xs = np.r_[DC_X0, np.arange(0.1300, DC_X1, 0.005), DC_X1]
    secs = [dust_cover_section(x) for x in xs]
    dc = K.loft_x(secs, xs, 84, name="DustCover")
    slots = []
    for xc in (0.1350, 0.1490, 0.1630, 0.1770):
        zb = -0.0245 + (xc - 0.1300) * math.tan(math.radians(2.0))
        sl = prism([(xc - 0.0040, zb - 0.003), (xc + 0.0040, zb - 0.003), (xc + 0.0040, zb - 0.0005),
                    (xc + 0.0015, zb + 0.0020), (xc - 0.0015, zb + 0.0020), (xc - 0.0040, zb - 0.0005)],
                   -0.02, 0.02, bevel=0, name="Slot")
        slots.append(sl)
    cut(dc, *slots)
    return dc


def _guard_path():
    """Centre line of the guard (x, z): a squared front 1 mm further forward at the bottom (a slight hook), an R 8
    outside corner, a straight bottom into the grip."""
    top, front_bot = (0.1258, -0.0200), (0.1268, -0.0635)
    rc, cz = 0.0055, (0.1268 - 0.0055, -0.0690 + 0.0055)
    pts = [np.array(top) + (np.array(front_bot) - np.array(top)) * t for t in np.linspace(0, 1, 30)]
    pts += [(cz[0] + rc * math.cos(a), cz[1] + rc * math.sin(a)) for a in np.radians(np.linspace(-8, -90, 11))]
    pts += [(x, -0.0690) for x in np.linspace(cz[0] - 0.002, 0.0470, 37)]
    return np.array(pts)


def _d_section(u0, u1, b, r_out, r_in, M=40):
    """Rounded rectangle in (u, v): u0 (outside, round r_out) .. u1 (inside, break r_in), v -b .. b."""
    pts = []
    for cu, cv, r, a0 in ((u1 - r_in, b - r_in, r_in, 0), (u0 + r_out, b - r_out, r_out, 90),
                          (u0 + r_out, -b + r_out, r_out, 180), (u1 - r_in, -b + r_in, r_in, 270)):
        for a in np.radians(np.linspace(a0, a0 + 90, 7)):
            pts.append((cu + r * math.cos(a), cv + r * math.sin(a)))
    return K.resample(pts, M)


def build_guard():
    """Trigger guard: D section 7 mm wide x 5 mm deep swept along _guard_path; it widens into R 3 fillets at the
    dust cover (top) and at the grip (rear)."""
    pth = _guard_path()
    path = np.stack([pth[:, 0], np.zeros(len(pth)), pth[:, 1]], 1)
    L = float(np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1)))
    acc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]

    def prof(i, t):
        s = acc[i]
        f0 = K.smoothstep(0.007 - s, 0.0, 0.007)            # top end: flare into the dust cover
        f1 = K.smoothstep(s - (L - 0.009), 0.0, 0.009)      # rear end: flare into the grip
        u0 = -0.0025 - 0.0012 * f0
        u1 = 0.0025 + 0.0030 * f0 + 0.0020 * f1
        b = 0.0035 + 0.0040 * f0 + 0.0030 * f1
        return _d_section(u0, u1, b, 0.0021, 0.0010)
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
    for x0, x1 in ((0.0010, 0.0500), (0.1220, 0.1840)):
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
    hammer_slot = box(-0.0225, 0.0040, -0.0035, 0.0035, -0.0168, 0.0)
    trig = box(0.0835, 0.0985, -0.0036, 0.0036, -0.0370, -0.0245, bevel=0.0005)
    well = mag_body_solid(0.0103, 0.0174, -0.004, 0.090, name="Well")
    cut(up, hammer_slot, trig, well)
    for r in build_frame_rails():
        union(up, r)
    round_edges(up, 0.00035, 2, 40)
    parts.append(P(up, BLACKOX, "frame"))
    nine_panels(parts)
    # pins: trigger pin through the upper frame, 3 mm hammer pin heads in the ears
    for s in (1, -1):
        y = float(upper_hw(NN["trigger_pivot"][0], NN["trigger_pivot"][2]))
        parts.append(P(pin_head((NN["trigger_pivot"][0], s * y, NN["trigger_pivot"][2]), "Y", r=0.0016, h=0.0003, sign=s),
                       DARK, "frame"))
        parts.append(P(pin_head((NN["hammer_pivot"][0], s * TANG_W, NN["hammer_pivot"][2]), "Y", r=0.0015, h=0.0004,
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
    # magazine button (left) on the frame behind the guard opening, a turned ring round it
    yb = FRAME_W + crown(BUTTON[1]) * 0.3
    btn = lathe([(0.0, 0.0), (0.0, 0.0048), (0.0010, 0.0048), (0.0016, 0.0043), (0.0019, 0.0032), (0.0020, 0.0)], 40,
                axis="Y", at=(BUTTON[0], yb - 0.0006, BUTTON[1]), fillet=0.0002)
    parts.append(P(btn, DARK, "frame"))
    ring = lathe([(0.0, 0.0050), (0.0, 0.0057), (0.0004, 0.0057), (0.0005, 0.0050)], 40, axis="Y", closed=True,
                 at=(BUTTON[0], yb - 0.0002, BUTTON[1]))
    parts.append(P(fix_normals(ring), BLACKOX, "frame"))


# ------------------------------------------------------------------------------------------------- slide

SLIDE_TOP = 0.0125
SLOPE = math.radians(22.0)
FLAT_HW = 0.0035                     # 7 mm flat top
SHOULDER_R = 0.0030
NOSE_X0 = 0.1860                     # 20 deg dehorn over the last 10 mm, lower 60 % of the height
Z60 = -0.0135 + 0.6 * 0.026


def slide_half(x):
    """Half outline (y >= 0) of the slide section at x, bottom -> top: 0.6 mm lower break, vertical flank, R 3
    shoulder into a 22 deg slope, 0.4 mm break into the 7 mm flat top. Rear edge broken, front R 1.5 on top."""
    w = 0.0135
    rear = max(0.0, 0.0015 - x) * 0.8
    fr = 0.0010 - math.sqrt(max(0.0, 0.0010 ** 2 - (x - 0.1950) ** 2)) if x > 0.1950 else 0.0
    top = SLIDE_TOP - rear
    if x > 0.1945:
        top -= 0.0015 - math.sqrt(max(0.0, 0.0015 ** 2 - (x - 0.1945) ** 2))
    zb = -0.0135 + rear * 0.5
    w2 = w - rear - fr
    tn, cs = math.tan(SLOPE), math.cos(SLOPE)
    R = SHOULDER_R
    zc = top + tn * FLAT_HW - tn * (w2 - R) - R / cs
    pts = [(w2 - 0.0006, zb), (w2 - 0.0006 + 0.0006 * math.sin(math.radians(45)), zb + 0.0006 * (1 - math.cos(math.radians(45)))),
           (w2, zb + 0.0006)]
    pts += [(w2, z) for z in np.linspace(zb + 0.0012, zc, 6)]
    pts += [(w2 - R + R * math.cos(a), zc + R * math.sin(a)) for a in np.linspace(0.08, math.pi / 2 - SLOPE, 9)]
    rb = 0.0020                                       # the 0.4 mm break: a 2 mm radius over the 22 deg turn
    tl = rb * math.tan(SLOPE / 2)
    ys = FLAT_HW + tl * cs
    pts += [(ys, top - tn * (ys - FLAT_HW))]
    cy, cz_ = FLAT_HW - tl, top - rb
    pts += [(cy + rb * math.sin(a), cz_ + rb * math.cos(a)) for a in np.linspace(SLOPE * 0.75, SLOPE * 0.25, 3)]
    pts += [(FLAT_HW - tl, top), (0.0, top)]
    hp = np.array(pts)
    if x > NOSE_X0:                                   # dehorn: lower 60 % beveled 20 deg in plan
        ins = (x - NOSE_X0) * math.tan(math.radians(20.0))
        fade = 1.0 - K.smoothstep(hp[:, 1], Z60, Z60 + 0.0025)
        hp[:, 0] = np.maximum(hp[:, 0] - ins * fade, 0.0)
    return hp


def flank_w(x, z):
    """Slide half width at (x, z) (the outer flank of slide_half)."""
    hp = slide_half(x)
    zz = hp[2:-2, 1]
    return float(np.interp(z, zz, hp[2:-2, 0]))


def slide_section(x):
    hp = slide_half(x)
    right = [(-y, z) for y, z in hp[::-1]][:-1]           # top centre -> down the right side (-y)
    left = [(y, z) for y, z in hp][1:-1]                  # bottom -> up the left side
    pts = [(0.0, hp[-1, 1])] + right[1:] + [(0.0, hp[0, 1])] + left
    # counter-clockwise in (y, z): top centre, right flank going down, bottom, left flank going up
    pts = pts[::-1]
    return K.poly_section(pts, K=480)


def serration_cutter(xc, side, width=0.0015, depth=0.0012, z0=-0.0122, z1=0.0098):
    zs = np.linspace(z0, z1, 14)
    inner = [(side * (flank_w(xc, z) - depth), z) for z in zs]
    poly = inner + [(side * 0.025, z1 + 0.004), (side * 0.025, z0)]
    if side < 0:
        poly = poly[::-1]
    sec = K.poly_section(poly, K=140)
    return K.loft_x([sec, sec], [xc - width / 2, xc + width / 2], 28, name="Ser")


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
    xs = np.r_[0.0, 0.0004, 0.0010, 0.0016, np.arange(0.003, 0.186, 0.0060), np.arange(0.186, 0.1945, 0.0012),
               np.arange(0.1945, 0.1960, 0.0003), 0.196]
    secs = [slide_section(x) for x in xs]
    sl = K.loft_x(secs, xs, 96, name="Slide")
    chan = box(0.0045, 0.1860, -0.0104, 0.0104, -0.020, 0.0100)
    grooves = [box(-0.001, 0.25, s * 0.0080, s * 0.0103, -0.020, -0.0106) for s in (1, -1)]
    ham_chan = box(-0.001, 0.048, -0.0034, 0.0034, -0.020, 0.0108)          # hammer channel: 6.8 mm (the spur is 6)
    rails = box(-0.001, 0.0050, -0.0104, 0.0104, -0.020, -0.0075)           # frame ears and rails pass under the breech
    nose = lathe([(0.15, 0.0), (0.15, 0.0072), (0.25, 0.0072), (0.25, 0.0)], 48)
    rod = lathe([(0.15, 0.0), (0.15, 0.0038), (0.25, 0.0038), (0.25, 0.0)], 32, at=(0, 0, -0.0118))
    under = box(0.1800, 0.25, -0.0040, 0.0040, -0.020, -0.0118)               # the rod's bore opens to the dust cover
    # ejection port: top view and side view outlines (1.2 mm corners) intersected
    pa = prism([(0.0860, -0.030), (0.1260, -0.030), (0.1260, 0.0042), (0.0860, 0.0042)], -0.003, 0.030, axis="Z",
               bevel=0, fillet=0.0012, name="PortA")
    pb = prism([(0.0860, -0.0030), (0.1260, -0.0030), (0.1260, 0.030), (0.0860, 0.030)], -0.030, 0.010, bevel=0,
               fillet=0.0012, name="PortB")
    geo.boolean(pa, pb, "INTERSECT", "EXACT")
    scallop = geo.sphere(0.0060, 28, 14, name="Scallop")
    geo.transform(scallop, loc=(0.0880, -0.0178, 0.0010))
    ext_slot = prism([(0.0576, 0.0028), (0.0852, 0.0028), (0.0870, 0.0038), (0.0870, 0.0062), (0.0852, 0.0070),
                      (0.0576, 0.0070)], -0.020, -(0.0135 - 0.0012), bevel=0, fillet=0.0010, name="ExtSlot")
    sers = [serration_cutter(0.0060 + k * 0.0030, s) for s in (1, -1) for k in range(7)]
    cut(sl, chan, *grooves, ham_chan, rails, nose, rod, under, pa, scallop, ext_slot,
        dovetail(0.0070, 0.0180), dovetail(0.1825, 0.1895), *sers)
    # 0.5 mm chamfer round the port mouth, then 0.2 mm edge breaks everywhere
    K.bevel_where(sl, 0.0005, 1, 35.0, where=lambda c: (c[:, 0] > 0.0850) & (c[:, 0] < 0.1270) & (c[:, 1] < 0.0046)
                  & (c[:, 2] > -0.0035) & ((c[:, 2] > 0.0090) | (c[:, 1] < -0.0128)))
    round_edges(sl, 0.0002, 2, 38)
    parts.append(P(sl, STAINLESS, "slide"))
    # rear sight: dovetailed block 9 mm long on top (11 mm at the base), rear face sloped 10 deg, a hex set screw;
    # notch 4.2 x 3.9, top Z 0.0185 over X 0.007..0.018
    rs = prism([(0.0068, 0.0095), (0.0190, 0.0095), (0.0190, 0.0140), (0.0177, 0.0185), (0.0080, 0.0185),
                (0.0069, 0.0123)], -0.0098, 0.0098, bevel=0.0005, seg=2, name="RearSight")
    union(rs, dovetail_key(0.0070, 0.0180, 0.0098))
    cut(rs, box(0.0, 0.03, -0.0021, 0.0021, 0.0146, 0.03),
        box(0.0, 0.03, -0.0036, 0.0036, 0.0, 0.0111))          # clear of the hammer channel as the slide runs back
    set_screw = lathe([(-0.004, 0.0), (-0.004, 0.0013), (0.00002, 0.0013), (0.00002, 0.0)], 24, axis="Z",
                      at=(0.0150, 0.0062, 0.0185), name="SetScrew")
    hexa = prism([(0.0006 * math.cos(a), 0.0006 * math.sin(a)) for a in np.radians(np.arange(0, 360, 60))],
                 0.0180, 0.0200, axis="Z", bevel=0, name="Hex")
    geo.transform(hexa, loc=(0.0150, 0.0062, 0.0))
    cut(set_screw, hexa)
    round_edges(rs, 0.0002, 1, 50)
    parts.append(P(rs, DARK, "slide"))
    parts.append(P(fix_normals(set_screw), DARK, "slide"))
    fs = prism([(0.1820, 0.0098), (0.1900, 0.0098), (0.1888, 0.0150), (0.1885, 0.0185), (0.1835, 0.0185),
                (0.1830, 0.0140)], -0.0017, 0.0017, bevel=0.0003, seg=2, name="FrontSight")
    base = box(0.1818, 0.1902, -0.0048, 0.0048, 0.0112, 0.0128, bevel=0.0004)
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


def hood_section(x, inset=0.0):
    """Barrel hood (y, z): a cylinder segment (R 10 about the bore) clipped to the slide's channel, with a 5 mm flat
    top at Z 0.0097; counter-clockwise."""
    Rh = math.hypot(0.0025, 0.0097) - inset
    yw = 0.0098 - inset
    zt = 0.0097 - inset
    a1 = math.atan2(math.sqrt(max(Rh * Rh - yw * yw, 0.0)), yw)
    a2 = math.atan2(zt, math.sqrt(max(Rh * Rh - zt * zt, 0.0)))
    arc_ = [(Rh * math.cos(a), Rh * math.sin(a)) for a in np.linspace(a1, a2, 12)]
    pts = [(yw, 0.0)] + arc_ + [(-y, z) for y, z in arc_[::-1]] + [(-yw, 0.0)]
    return K.poly_section(pts, K=160)


def nine_barrel(parts):
    b = lathe([(0.062, 0.0), (0.062, 0.0076), (0.064, 0.0078), (0.124, 0.0078), (0.127, 0.0068), (0.2005, 0.0068),
               (0.2010, 0.0060), (0.2010, 0.0050), (0.2005, 0.0046), (0.150, 0.0045), (0.150, 0.0)], 64, name="Barrel",
              fillet=0.0002)
    hx = [0.0640, 0.0644, 0.0650, 0.1226, 0.1234, 0.1240]
    hood = K.loft_x([hood_section(x, ins) for x, ins in zip(hx, (0.0006, 0.0002, 0.0, 0.0, 0.0003, 0.0008))], hx, 72,
                    name="Hood")
    lug = prism([(0.0640, -0.0040), (0.0800, -0.0040), (0.0790, -0.0105), (0.0700, -0.0125), (0.0640, -0.0105)],
                -0.0045, 0.0045, bevel=0.0005, seg=2, fillet=0.0015)
    union(b, hood, lug)
    cut(b, lathe([(0.055, 0.0), (0.055, 0.0047), (0.17, 0.0047), (0.17, 0.0)], 48),
        lathe([(-0.01, 0.0), (-0.01, 0.0021), (0.01, 0.0021), (0.01, 0.0)], 20, axis="Y", at=(0.070, 0, -0.008)),
        lathe([(-0.003, 0.0), (-0.003, 0.0010), (0.003, 0.0010), (0.003, 0.0)], 20, axis="Z", at=(0.0675, 0, 0.0097)))
    round_edges(b, 0.0003, 2, 50)
    parts.append(P(b, POLISHED, "barrel"))
    rod = lathe([(0.090, 0.0), (0.090, 0.0026), (0.1955, 0.0026), (0.1970, 0.0020), (0.1970, 0.0)], 32, at=(0, 0, -0.0118))
    parts.append(P(rod, POLISHED, "frame"))
    spring = []
    for k in range(int((0.184 - 0.100) / 0.0036)):
        x = 0.100 + k * 0.0036
        t = geo.torus(0.0031, 0.0005, 12, 6, name="Coil")
        geo.transform(t, rot=(0, 90 + 8, 0))
        geo.transform(t, loc=(x, 0, -0.0118))
        spring.append(t)
    sp = geo.join(spring, "Spring")
    parts.append(P(sp, DARK, "frame"))


# ------------------------------------------------------------------------------------------------- moving parts

HAMMER = [(-0.0135, -0.0150), (-0.0104, -0.0138), (-0.0091, -0.0110), (-0.0094, -0.0080), (-0.0106, -0.0040),
          (-0.0125, 0.0005), (-0.0150, 0.0050), (-0.0172, 0.0084), (-0.0192, 0.0101), (-0.0215, 0.0105),
          (-0.0240, 0.0103), (-0.0258, 0.0098), (-0.0271, 0.0087), (-0.0278, 0.0071), (-0.0275, 0.0055),
          (-0.0258, 0.0030), (-0.0236, 0.0000), (-0.0210, -0.0035), (-0.0190, -0.0070), (-0.0178, -0.0105),
          (-0.0163, -0.0136)]


def build_hammer():
    """One forged hammer: 6 mm body, the spur tapering to 4.5 mm at its R 3 tip, a 4 mm lightening hole, seven
    1.2 mm-pitch grooves across the thumb face."""
    pts = geo.fillet(HAMMER, 0.0005, 3, closed=True)
    ham = K.slab(pts, -1.0, 1.0, step=0.0011, name="Hammer")

    def fn(co):
        d = np.hypot(co[:, 0] + 0.0135, co[:, 2] + 0.0105)
        hw = 0.0030 - 0.00075 * K.smoothstep(d, 0.0140, 0.0235)
        co[:, 1] = np.sign(co[:, 1]) * hw
        return co
    K.deform(ham, fn)
    K.outward(ham)
    hole = lathe([(-0.01, 0.0), (-0.01, 0.0020), (0.01, 0.0020), (0.01, 0.0)], 28, axis="Y", at=(-0.0200, 0.0, 0.0035))
    grooves = []
    top = K.resample(np.array([(-0.0188, 0.0099), (-0.0200, 0.0104), (-0.0215, 0.0105), (-0.0240, 0.0103),
                               (-0.0258, 0.0098), (-0.0271, 0.0087), (-0.0278, 0.0071)]), 60, closed=False)
    acc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(top, axis=0), axis=1))]
    for k in range(7):
        s = 0.0008 + k * 0.0012
        if s > acc[-1] - 0.0008:
            break
        x = float(np.interp(s, acc, top[:, 0]))
        z = float(np.interp(s, acc, top[:, 1]))
        j = min(int(np.searchsorted(acc, s)), len(top) - 1)
        t = top[j] - top[j - 1]
        nx, nz = -t[1], t[0]                      # outward (up/back) normal of the top edge
        if nz < 0:
            nx, nz = -nx, -nz
        g = box(-0.00028, 0.00028, -0.004, 0.004, -0.0004, 0.002)
        geo.transform(g, rot=(0, math.degrees(math.atan2(nx, nz)), 0))
        geo.transform(g, loc=(x, 0.0, z))
        grooves.append(g)
    cut(ham, hole, *grooves)
    round_edges(ham, 0.00025, 2, 35)
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
    parts.append(P(build_hammer(), DARK, "hammer"))
    # hammer strut: from the hammer's lower rear down and back into the mainspring housing
    a, b = np.array([-0.0170, 0.0, -0.0128]), np.array([-0.0196, 0.0, -0.0250])
    d = b - a
    st_ = lathe([(0.0, 0.0), (0.0, 0.0011), (np.linalg.norm(d), 0.0011), (np.linalg.norm(d), 0.0)], 16, axis="X",
                name="Strut", fillet=0.0002)
    geo.transform(st_, rot=(0, math.degrees(math.atan2(-d[2], d[0])), 0))
    geo.transform(st_, loc=tuple(a))
    parts.append(P(fix_normals(st_), DARK, "hammer"))
    # gold trigger: curved blade, rounded edges
    t = [(0.0870, -0.0290), (0.0950, -0.0290), (0.0965, -0.0380), (0.0955, -0.0460), (0.0920, -0.0545),
         (0.0880, -0.0600), (0.0850, -0.0590), (0.0878, -0.0530), (0.0898, -0.0455), (0.0895, -0.0380)]
    trg = prism(t, -0.0031, 0.0031, bevel=0.0010, seg=3, fillet=0.0012, name="Trigger")
    parts.append(P(trg, GOLD, "trigger"))


# ------------------------------------------------------------------------------------------------- magazine

PAD_X0, PAD_X1, PAD_W = -0.0135, 0.0272, 0.0130


def nine_magazine(col):
    """SM_Weapon_NineMagazine (+ _TopRound) on the brief's line: brushed body 19.5 x 34 mm with three witness holes
    per side, feed lips, the stack, and the moulded gold base pad under the butt."""
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
    """One moulded gold base pad, 43 x 26 x 7 mm: R 1.5 round the top edge, R 3 round the bottom edge, plan corners
    R 6 (rear) and R 4 (front), and a front lip that juts 2.6 mm forward with a 2 mm finger relief under it."""
    T, Bt = 0.0015, 0.0030
    H = BUTT_Z - PAD_Z
    zs = []
    for a in np.linspace(0, math.pi / 2, 7):              # top edge round
        zs.append((BUTT_Z - T * (1 - math.sin(a)), T * (1 - math.cos(a))))
    for z in np.linspace(BUTT_Z - T - 0.0004, PAD_Z + Bt + 0.0004, 7):
        zs.append((z, 0.0))
    for a in np.linspace(0, math.pi / 2, 9)[1:]:          # bottom edge round
        zs.append((PAD_Z + Bt * (1 - math.sin(a)), Bt * (1 - math.cos(a))))
    for q in (0.0012, 0.0030):                            # the flat bottom
        zs.append((PAD_Z, Bt + q))
    zs.sort(key=lambda t: (-t[0], t[1]))
    secs, zz = [], []
    for z, ins in zs:
        d = BUTT_Z - z
        lip = 0.0026 * float(K.smoothstep(d, 0.0004, 0.0026)) - 0.0020 * float(K.smoothstep(d, 0.0038, 0.0062))
        x1 = PAD_X1 + lip
        secs.append(K.rrect(PAD_X0 + ins, x1 - ins, PAD_W - ins, max(0.0060 - ins * 0.7, 0.0006),
                            max(0.0040 - ins * 0.7, 0.0006)))
        zz.append(z)
    return K.loft_z(secs, zz, 112, name="Pad")


def nine_build(ctx):
    parts = []
    nine_slide(parts)
    nine_barrel(parts)
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
