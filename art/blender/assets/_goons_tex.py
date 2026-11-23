"""The Goons' unique texture sets, computed per texel from the baked rest position (mi/texel.py), as the player's arms.

Every fabric is drawn at its true size in metres from 3D coordinates round the body's own axes (`AxisCoords`: along
a limb, round it, so knit wales run down a sleeve and twill climbs a trouser leg whatever the UV island's angle):
rib knit 2.4 mm wales, jersey with heathered yarn and pilling where arms rub, denim twill with slub warp streaks and
whiskers, quilted nylon with ripstop and stitch lines, track tricot, pebble-grain glove leather, sneaker leather with
toe creases, scuffs and panel stitching, rubber with dirt, webbing, cord, metal. Dirt gathers at hems, cuffs and knees;
screen prints, stripes, yokes and seams are placed in body space.

Channels: BC (sRGB), N (OpenGL, from the height), ORM (R ambient occlusion: geometry AO x cavity, G roughness,
B metallic). Face attributes from goons.tag(): mi_kind, mi_r / mi_g / mi_b (linear base colour), mi_piece.
"""
import numpy as np

from mi import texel as TX
from assets import _goons_kit as GK

K = dict(fleece=0, rib=1, denim=2, leather=3, shoe=4, sole=5, maskknit=6, quilt=7, nylon=8, twill=9, tricot=10,
         webbing=11, metal=12, cord=13, aglet=14, captwill=15, lens=16, bandana=17, sock=18, beanie=19, zip=20,
         skin=21, eye=22, plastic=23, tape=24)


def lin(h):
    h = h.lstrip("#")
    c = np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(np.float32)


OX, DARKOX, SEAM, SLIT, DUST, TAN = lin("#7c151d"), lin("#4d0d13"), lin("#b5ad9c"), lin("#050506"), lin("#6e655a"), \
    lin("#8c6a3c")


def ss(a, b, x):
    return TX.smoothstep(a, b, x)


class AxisCoords:
    """Nearest body axis per point: (segment id, s along it in metres, arc round it in metres, radius, angle)."""

    def __init__(self, man):
        J = man.B.J
        seg = [(np.array([0, 0.0, 0.84]), J["neck_01"] + np.array([0, 0, 0.0])),        # 0 torso
               (J["neck_01"], J["head"] + np.array([0, 0, 0.20]))]                          # 1 head
        for s in "lr":
            seg += [(J["upperarm_" + s], J["lowerarm_" + s]), (J["lowerarm_" + s], J["hand_" + s] + (J["hand_" + s] - J["lowerarm_" + s]) * 0.6),
                    (J["thigh_" + s], J["calf_" + s]), (J["calf_" + s], J["foot_" + s])]
        self.A = np.array([a for a, b in seg])
        self.Bv = np.array([b for a, b in seg])
        # 2..5 left arm upper, fore, thigh, shin; 6..9 right
        self.names = ["torso", "head", "uarm_l", "farm_l", "thigh_l", "shin_l", "uarm_r", "farm_r", "thigh_r", "shin_r"]

    def __call__(self, P, prefer=None):
        best_d = np.full(len(P), 1e9)
        out = np.zeros((len(P), 5))
        for k in range(len(self.A)):
            a, b = self.A[k], self.Bv[k]
            w = b - a
            L = np.linalg.norm(w)
            w = w / L
            t = (P - a) @ w
            tc = np.clip(t, 0, L)
            q = a + tc[:, None] * w
            r = P - q
            d = np.linalg.norm(r, axis=1)
            if k == 0:
                d = d * 0.85                      # the torso wins at the armpit
            m = d < best_d
            if not m.any():
                continue
            ref = np.array([0, -1.0, 0]) if abs(w[1]) < 0.9 else np.array([1.0, 0, 0])
            u = ref - w * (ref @ w)
            u /= np.linalg.norm(u)
            v = np.cross(w, u)
            ang = np.arctan2(r @ v, r @ u)
            rad = np.linalg.norm(r - (r @ w)[:, None] * w, axis=1)
            best_d = np.where(m, d, best_d)
            out[m, 0] = k
            out[m, 1] = t[m]
            out[m, 2] = (ang * np.maximum(rad, 0.02))[m]
            out[m, 3] = rad[m]
            out[m, 4] = ang[m]
        return out


def knit(s, arc, wale=0.0024, course=0.0019):
    """Jersey / rib relief: wales (columns of V loops) along s; 0..1 height."""
    col = np.abs(np.sin(np.pi * arc / wale))
    loops = 0.5 + 0.5 * np.cos(2 * np.pi * (s / course) + np.pi * np.floor(arc / wale))
    return col ** 0.6 * (0.75 + 0.25 * loops)


def twill(s, arc, pitch=0.0011, ang=0.38):
    """Diagonal twill lines climbing to the left (denim)."""
    return 0.5 + 0.5 * np.sin(2 * np.pi * (s * np.cos(ang) + arc * np.sin(ang)) / pitch)


def stitch_line(d, along, width=0.0005, pitch=0.003, duty=0.65):
    """Raised stitches on a seam: d distance from the stitch line, along = position along it."""
    on = ((along / pitch) % 1.0) < duty
    return np.where(on, np.clip(1 - np.abs(d) / width, 0, 1), 0.0)


def pills(P, density=900.0, size=0.0011, seed=3):
    f1, f2 = TX.cells(P, density, seed)
    return np.clip(1 - f1 * density * size * 1.4, 0, 1) * (TX.noise(P, 60, seed) > 0.25)


def fibres(P, scale=1.0, seed=31):
    """Brushed-fleece fibre relief (0..1): fine isotropic fuzz at ~0.3 mm over 2 mm fibre clumps."""
    return 0.6 * TX.noise(P, 3000.0 / scale, seed) + 0.4 * TX.fbm(P, 520.0 / scale, 2, seed=seed + 1)


FINGERS = ("index", "middle", "ring", "pinky")


def glove_relief(man, P, N):
    """Work-glove relief from the hand's bones: knuckle pads over the MCP and PIP joints on the back of the hand,
    panel seams along both sides of every finger (fourchettes), flex creases across the palm side of each joint.
    Returns (pad, seam, crease) 0..1 per point."""
    J = man.B.J
    pad = np.zeros(len(P))
    seam = np.zeros(len(P))
    flex = np.zeros(len(P))
    for sd, sx in (("l", 1.0), ("r", -1.0)):
        if "index_01_" + sd not in J:
            continue
        across = J["index_01_" + sd] - J["pinky_01_" + sd]
        fwd = J["middle_02_" + sd] - J["middle_01_" + sd]
        n = np.cross(across, fwd)
        n /= np.linalg.norm(n)
        if n[2] + 0.5 * sx * n[0] < 0:
            n = -n                                                   # the back of the hand (up and out in the A-pose)
        side = (P[:, 0] * sx) > 0.15
        dors = np.clip((N @ n - 0.2) / 0.5, 0, 1)
        palm = np.clip((-(N @ n) - 0.2) / 0.5, 0, 1)
        for f in FINGERS:
            a, b, c = J["%s_01_%s" % (f, sd)], J["%s_02_%s" % (f, sd)], J["%s_03_%s" % (f, sd)]
            for jt, r in ((a, 0.011), (b, 0.008)):
                d = np.linalg.norm(P - jt, axis=1)
                pad = np.maximum(pad, side * dors * np.exp(-(d / r) ** 2))
            tip = c + (c - b) * 0.9
            for p0, p1 in ((a, b), (b, c), (c, tip)):
                w = p1 - p0
                L = np.linalg.norm(w)
                w = w / L
                t = (P - p0) @ w
                q = P - p0 - np.outer(t, w)
                rad = np.linalg.norm(q, axis=1)
                on = side & (t > -0.002) & (t < L + 0.002) & (rad < 0.016)
                rn = (q @ n) / np.maximum(rad, 1e-6)
                seam = np.maximum(seam, on * np.clip(1 - np.abs(rn) / 0.10, 0, 1))
            for jt, w in ((b, b - a), (c, c - b)):
                w = w / np.linalg.norm(w)
                d = np.abs((P - jt) @ w)
                flex = np.maximum(flex, side * palm * (np.linalg.norm(P - jt, axis=1) < 0.016) * np.clip(1 - d / 0.0012, 0, 1))
        # knuckle bar across the back of the hand, the wrist strap seam
        h = J["hand_" + sd]
        flex = np.maximum(flex, side * np.clip(1 - np.abs(np.linalg.norm(P - h, axis=1) - 0.035) / 0.0012, 0, 1) * 0.6)
    return pad, seam, flex


def texels(man, P, N, kind, base, piece, ao_geo, loft=None):
    """(bc (n, 3) linear, roughness (n,), metallic (n,), height (n,) metres) per texel."""
    n = len(P)
    ax = AxisCoords(man)(P)
    seg, s, arc = ax[:, 0].astype(int), ax[:, 1], ax[:, 2]
    bc = base.copy()
    rough = np.full(n, 0.8, dtype=np.float32)
    metal = np.zeros(n, dtype=np.float32)
    h = np.zeros(n, dtype=np.float32)
    z = P[:, 2]
    big = TX.fbm(P, 9.0, 3, seed=1)              # 10 cm blotches
    mid = TX.fbm(P, 60.0, 3, seed=2)             # 1-2 cm
    fine = TX.noise(P, 700.0, 5)                 # 1.4 mm
    limb = seg >= 2
    # dust: gathers low, at hems and cuffs, in folds (low geometric AO) and on the fronts of the legs
    cuff_zone = np.zeros(n, dtype=np.float32)
    for sx in (1, -1):
        w = man.M.wrist["l" if sx > 0 else "r"]
        cuff_zone = np.maximum(cuff_zone, 1 - ss(0.04, 0.14, np.linalg.norm(P - w, axis=1)))
    knee = np.zeros(n, dtype=np.float32)
    for sd in "lr":
        k = man.M.knee[sd] + np.array([0, -0.06, 0])
        knee = np.maximum(knee, 1 - ss(0.03, 0.12, np.linalg.norm(P - k, axis=1)))
    low = 1 - ss(0.05, 0.45, z)
    dust = np.clip(0.5 * low + 0.6 * cuff_zone + 0.7 * knee * (N[:, 1] < 0.2), 0, 1) * (0.55 + 0.45 * ss(-0.3, 0.6, big))
    dust = dust * (0.7 + 0.3 * ss(0.2, 0.8, 1 - ao_geo))

    def k_(name):
        return kind == K[name]

    # ---------------------------------------------------------------- jersey / fleece (hoodie, pocket, hood, sock)
    m = k_("fleece") | k_("sock")
    if m.any():
        kn = knit(s[m], arc[m], 0.0016, 0.0013)
        # heathered yarn: dark and light fibres mixed, flecks drawn out along the wales (r2: grey heather)
        fl = TX.noise(np.stack([arc[m] * 2600, s[m] * 700, P[m, 0] * 50], 1), 1.0, 9)
        heather = 0.22 * fl + 0.10 * TX.noise(P[m], 900.0, 19) + 0.05 * mid[m]
        fb = fibres(P[m])
        pl = 0.5 * pills(P[m]) * (0.15 + 0.85 * np.clip(cuff_zone[m] + (np.abs(P[m, 0]) > 0.17) * (z[m] > 0.95) * (z[m] < 1.3), 0, 1))
        c = bc[m] * (1 + heather)[:, None]
        c = c * (1 - 0.08 * (1 - kn))[:, None] + pl[:, None] * 0.03
        bc[m] = c
        rough[m] = 0.86 - 0.04 * pl + 0.04 * fb
        h[m] = 0.00010 * kn + 0.00018 * pl + 0.00012 * fb + 0.00025 * mid[m]
    # ---------------------------------------------------------------- rib knit (bands, mask, beanie)
    m = k_("rib") | k_("maskknit") | k_("beanie")
    if m.any():
        wale = np.where(kind[m] == K["maskknit"], 0.0024, 0.0026)
        kn = knit(s[m], arc[m], wale, 0.0017)
        rib = np.abs(np.sin(np.pi * arc[m] / (wale * 2))) ** 0.5
        fz = TX.noise(P[m], 2600.0, 41)                                   # stray acrylic fuzz
        c = bc[m] * (0.80 + 0.20 * rib)[:, None] * (1 + 0.08 * mid[m] + 0.06 * fz)[:, None]
        bc[m] = c
        rough[m] = 0.88 + 0.03 * fz
        h[m] = 0.00045 * rib + 0.0001 * kn + 0.00005 * fz
    # ---------------------------------------------------------------- denim
    m = k_("denim")
    if m.any():
        Pm = P[m]
        tw = twill(s[m], arc[m], 0.0012)
        slub = TX.noise(np.stack([arc[m] * 900, s[m] * 25, Pm[:, 0] * 3], axis=1), 1.0, 11)        # warp streaks
        fade = np.clip(0.6 * ss(0.55, 0.95, ao_geo[m]) + 0.25 * ss(0.2, 0.9, mid[m]), 0, 1)
        # whiskers at the front of the hips, honeycombs behind the knees
        hipw = np.zeros(m.sum(), dtype=np.float32)
        for sx, sd in ((1, "l"), (-1, "r")):
            c0 = man.M.hip[sd] + np.array([sx * 0.02, -0.10, -0.05])
            d = Pm - c0
            ang = np.arctan2(d[:, 2], d[:, 0] * sx)
            hipw = np.maximum(hipw, TX.ridged(np.stack([ang * 4, np.zeros_like(ang), np.zeros_like(ang)], 1), 1.3, 3)
                              * (1 - ss(0.03, 0.12, np.linalg.norm(d, axis=1))) * (Pm[:, 1] < -0.05))
            kb = man.M.knee[sd] + np.array([0, 0.06, 0])
            hipw = np.maximum(hipw, 0.7 * TX.ridged(Pm, 40, 5) * (1 - ss(0.02, 0.07, np.linalg.norm(Pm - kb, axis=1))))
        light = np.clip(0.35 * fade + 0.5 * hipw + 0.06 * slub, -0.1, 1)            # r2: streaks at half strength
        c = bc[m] * (0.93 + 0.14 * tw)[:, None]
        c = c * (1 + 0.9 * light)[:, None] + np.array([0.01, 0.012, 0.02]) * light[:, None]
        bc[m] = c
        rough[m] = 0.78 + 0.08 * tw
        h[m] = 0.00016 * tw + 0.00004 * slub
        # seams with tan thread: outer and inner leg, back pockets and yoke
        sx = np.sign(Pm[:, 0])
        sd_ = np.where(sx > 0, 0, 1)
        legx = np.where(sx > 0, man.M.hip["l"][0], man.M.hip["r"][0])
        outer = np.abs(np.abs(Pm[:, 0]) - (np.abs(legx) + 0.0)) < 1  # placeholder for shape
        a4 = ax[m, 4]
        for target, wdt in ((np.pi / 2, 0.0035), (-np.pi / 2, 0.0035)):
            dd = np.abs(np.angle(np.exp(1j * (a4 - target)))) * ax[m, 3]
            line = (dd < wdt) & (seg[m] >= 4)
            st = stitch_line(dd - 0.0018, s[m], 0.0006, 0.0032)
            bc[m] = np.where(line[:, None], bc[m] * 0.75 + TAN * 0.25 * st[:, None], bc[m])
            h[m] = np.where(line, h[m] - 0.0003 * (dd < 0.0012) + 0.00025 * st, h[m])
        # back pockets: two patches, stitched outline (0.14 x 0.15)
        for sx2 in (1, -1):
            px = Pm[:, 0] - sx2 * 0.085
            pz = Pm[:, 2] - 0.80
            inside = (np.abs(px) < 0.07) & (pz > -0.075 + 0.02 * (1 - np.abs(px) / 0.07)) & (pz < 0.075) & (Pm[:, 1] > 0.02)
            edge = np.minimum(np.minimum(0.07 - np.abs(px), 0.075 - pz), pz + 0.075 - 0.02 * (1 - np.abs(px) / 0.07))
            st = stitch_line(edge - 0.004, px + pz, 0.0006, 0.0032)
            bc[m] = np.where(inside[:, None], bc[m] * 0.93 + TAN * 0.35 * st[:, None], bc[m])
            h[m] = np.where(inside, h[m] + 0.0004 * ss(0.0, 0.003, edge) + 0.0002 * st, h[m])
    # ---------------------------------------------------------------- twill trousers, cap twill, bandana, webbing
    for name, pitch, r0 in (("twill", 0.0009, 0.78), ("captwill", 0.0008, 0.8), ("bandana", 0.0007, 0.84),
                            ("webbing", 0.0016, 0.72), ("tape", 0.0010, 0.62)):
        m = k_(name)
        if m.any():
            tw = twill(s[m], arc[m], pitch, 0.5 if name != "webbing" else 0.9)
            bc[m] = bc[m] * (0.9 + 0.2 * tw)[:, None] * (1 + 0.06 * mid[m])[:, None]
            rough[m] = r0
            h[m] = 0.00012 * tw + 0.0001 * mid[m]
    # ---------------------------------------------------------------- nylon (puffer shell and panels): ripstop, sheen
    m = k_("quilt") | k_("nylon")
    if m.any():
        Pm = P[m]
        g = 0.005
        rip = np.maximum(ss(0.86, 1.0, np.abs(np.sin(np.pi * s[m] / g))), ss(0.86, 1.0, np.abs(np.sin(np.pi * arc[m] / g))))
        # taffeta: 0.45-0.55 on the baffle crowns, 0.75 down in the stitch valleys (the loft drives it)
        lf = np.clip(loft[m], 0, 1) if loft is not None else np.full(m.sum(), 0.8)
        lf = np.where(kind[m] == K["quilt"], lf, 0.8)
        crown = ss(0.25, 0.85, lf)
        bc[m] = bc[m] * (1 + 0.04 * rip + 0.04 * mid[m])[:, None] * (0.82 + 0.18 * crown)[:, None]
        rough[m] = 0.76 - 0.27 * crown + 0.04 * rip + 0.03 * big[m]
        h[m] = 0.00002 * rip
    # ---------------------------------------------------------------- tricot (tracksuit): fine courses, satin sheen
    m = k_("tricot")
    if m.any():
        tr = 0.5 + 0.5 * np.sin(2 * np.pi * s[m] / 0.0009)
        kn = knit(s[m], arc[m], 0.0011, 0.0009)                            # warp-knit loops, a matte face
        bc[m] = bc[m] * (0.95 + 0.06 * tr)[:, None] * (1 + 0.04 * mid[m])[:, None]
        rough[m] = 0.74 + 0.04 * tr + 0.03 * big[m]
        h[m] = 0.00004 * tr + 0.00006 * kn
    # ---------------------------------------------------------------- glove leather
    m = k_("leather")
    if m.any():
        Pm = P[m]
        f1, f2 = TX.cells(Pm, 1400.0, 7)
        grain = np.clip((f2 - f1) * 2.0, 0, 1)
        crease = TX.ridged(Pm, 150, 9) * 0.6
        pad, seam, flex = glove_relief(man, Pm, N[m])
        wear = ss(0.3, 0.9, pad) * (0.6 + 0.4 * TX.noise(Pm, 300, 23))
        bc[m] = bc[m] * (0.9 + 0.2 * grain)[:, None] * (1 + 0.15 * crease)[:, None] * (1 + 0.35 * wear)[:, None]
        rough[m] = 0.62 + 0.06 * (1 - grain) + 0.05 * crease - 0.06 * wear
        h[m] = 0.00012 * grain - 0.00015 * crease + 0.0012 * pad - 0.0004 * seam - 0.00035 * flex
    # ---------------------------------------------------------------- sneakers
    for name in ("shoe", "sole"):
        m = k_(name)
        if not m.any():
            continue
        Pm = P[m]
        xs = np.zeros(m.sum())
        ys = np.zeros(m.sum())
        for sd in "lr":
            F = GK.Foot(man.B, sd)
            sel = (Pm[:, 0] > 0) if sd == "l" else (Pm[:, 0] <= 0)
            x, y, _ = F.local(Pm[sel])
            xs[sel], ys[sel] = x / GK.SHOE_L, y
        zz = Pm[:, 2]
        scuff = ss(0.2, 0.8, TX.fbm(Pm, 120, 3, seed=13)) * (ss(0.82, 1.0, xs) + 0.6 * (1 - ss(0.0, 0.08, xs)) + 0.4 * (zz < 0.03))
        grime = np.clip(0.8 * (1 - ss(0.0, 0.035, zz)) + 0.5 * scuff + 0.3 * ss(0.2, 0.8, mid[m]) + 0.12, 0, 1)
        if name == "shoe":
            f1, f2 = TX.cells(Pm, 2200.0, 17)
            grain = np.clip((f2 - f1) * 2.0, 0, 1)
            # toe-box creases where the foot flexes (t 0.62-0.74)
            cre = TX.ridged(np.stack([xs * 40, ys * 30, zz * 10], 1), 1.0, 4) * (1 - ss(0.0, 0.06, np.abs(xs - 0.68)))
            # panel stitching: toe cap, eyestay, heel counter, mudguard
            st = np.zeros_like(xs)
            for dline in (np.abs(xs - 0.80), np.abs(xs - 0.22) + 0.002 * (zz > 0.07), np.abs(zz - 0.032)):
                st = np.maximum(st, stitch_line(dline, xs * GK.SHOE_L * 1.0 + ys + zz, 0.0006, 0.0028))
            c = bc[m] * (0.95 + 0.06 * grain)[:, None] * (1 - 0.12 * cre)[:, None]
            c = c * (1 - 0.35 * grime)[:, None] + DUST * 0.3 * grime[:, None] - 0.1 * st[:, None] * c
            bc[m] = c
            rough[m] = 0.55 + 0.1 * grain + 0.2 * grime + 0.1 * cre
            h[m] = 0.00006 * grain - 0.0004 * cre + 0.00025 * st
        else:
            band = 0.5 + 0.5 * np.sin(2 * np.pi * zz / 0.0035)
            c = bc[m] * (0.96 + 0.04 * band)[:, None]
            c = c * (1 - 0.45 * grime)[:, None] + DUST * 0.45 * grime[:, None]
            bc[m] = c
            rough[m] = 0.7 + 0.2 * grime
            h[m] = 0.00012 * band
    # ---------------------------------------------------------------- metal, aglets, lens, cord, zip
    m = k_("metal") | k_("zip")
    if m.any():
        metal[m] = 1.0
        bc[m] = np.where((kind[m] == K["zip"])[:, None], bc[m], lin("#8e8c88") * (0.85 + 0.15 * fine[m])[:, None])
        rough[m] = 0.35 + 0.15 * mid[m]
    m = k_("aglet")
    if m.any():
        rough[m] = 0.25
    m = k_("lens")
    if m.any():
        rough[m] = 0.05
        bc[m] = lin("#0b0a09")
    m = k_("plastic")
    if m.any():
        rough[m] = 0.38 + 0.12 * mid[m] + 0.1 * fine[m]
        h[m] = 0.00002 * fine[m]
    m = k_("skin")
    if m.any():
        Pm = P[m]
        pores = TX.noise(Pm, 2500.0, 51)
        mot = TX.fbm(Pm, 200.0, 3, seed=52)
        c = bc[m] * (1 + 0.10 * mot - 0.05 * pores)[:, None]
        # darker, oilier round the eyes (lids) and the lips
        for sd in "lr":
            e = man.H.face.eye_centre(sd)
            de = np.linalg.norm((Pm - e) * np.array([0.8, 1, 1.3]), axis=1)
            c = c * (1 - 0.25 * (1 - ss(0.010, 0.022, de)))[:, None]
        lips = 1 - ss(0.004, 0.013, np.linalg.norm((Pm - man.H.mouth) * np.array([0.45, 1, 1.0]), axis=1))
        c = c * (1 - 0.2 * lips)[:, None] + lin("#5a2c27") * 0.15 * lips[:, None]
        # the mouth line
        ml = 1 - ss(0.0006, 0.0018, np.abs(Pm[:, 2] - man.H.mouth[2]) + 0.15 * ss(0.012, 0.03, np.abs(Pm[:, 0])))
        c = c * (1 - 0.8 * ml)[:, None]
        bc[m] = c
        rough[m] = 0.48 - 0.1 * lips + 0.05 * pores
        h[m] = 0.00004 * pores - 0.0004 * ml
    m = k_("eye")
    if m.any():
        Pm = P[m]
        c = np.tile(lin("#cfc6b8"), (m.sum(), 1))
        for sd in "lr":
            e = man.H.face.eye_centre(sd)
            d = Pm - e
            ang = np.degrees(np.arccos(np.clip(-d[:, 1] / np.maximum(np.linalg.norm(d, axis=1), 1e-9), -1, 1)))
            near = np.linalg.norm(d, axis=1) < 0.02
            iris = near & (ang < 26)
            c[iris] = lin("#3a2416") * (0.8 + 0.4 * TX.noise(Pm[iris], 2000, 61))[:, None]
            c[near & (ang < 11)] = lin("#050403")
            limbal = near & (ang >= 24) & (ang < 29)
            c[limbal] = c[limbal] * 0.5
        bc[m] = c
        rough[m] = 0.04
    m = k_("cord")
    if m.any():
        hel = 0.5 + 0.5 * np.sin(2 * np.pi * (s[m] / 0.003 + ax[m, 4] / np.pi))
        bc[m] = bc[m] * (0.85 + 0.2 * hel)[:, None]
        rough[m] = 0.7
        h[m] = 0.0002 * hel
    # ---------------------------------------------------------------- dirt and dust over the fabrics
    fab = ~(k_("metal") | k_("zip") | k_("lens") | k_("aglet") | k_("shoe") | k_("sole") | k_("eye") | k_("skin")
            | k_("plastic"))
    d = dust * fab
    bc = bc * (1 - 0.25 * d)[:, None] + DUST * 0.12 * d[:, None]
    rough = np.clip(rough + 0.08 * d, 0.03, 1)
    return bc.astype(np.float32), rough.astype(np.float32), metal, h


def regions(man, P, N, kind, piece, bc, h, rough):
    """Prints, panels, stripes and seams placed in body space (in place)."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    garment = (kind == K["fleece"]) | (kind == K["quilt"]) | (kind == K["tricot"])
    # the crew mark on the back: an oxblood V of two bars 0.20 x 0.03 leaning 24 deg outward, centred 1.29 m up
    back = garment & (y > 0.02) & (N[:, 1] > 0.25) & (piece != 2)
    a = np.radians(24)
    zb = 1.29 - 0.1 * np.cos(a)
    v_ = np.zeros(len(P), dtype=bool)
    for sx in (1, -1):
        d = np.array([sx * np.sin(a), np.cos(a)])
        rx, rz = x - 0.0, z - zb
        along = rx * d[0] + rz * d[1]
        across = -rx * d[1] + rz * d[0]
        v_ |= (along > -0.012) & (along < 0.20) & (np.abs(across) < 0.015)
    v_ &= back
    crack = TX.ridged(P, 500, 21) > 0.55
    bc[v_] = OX * (0.92 + 0.08 * TX.noise(P[v_], 200, 4))[:, None] * np.where(crack[v_], 0.7, 1.0)[:, None]
    h[v_] += 0.00012
    rough[v_] = 0.55
    J = man.B.J
    # the puffer's oxblood yoke (above the top quilt seam) and shoulder caps
    puff = (kind == K["quilt"]) & (piece == 3)
    if puff.any():
        yoke = np.zeros(len(P), dtype=bool)
        for sd in "lr":
            yoke |= np.linalg.norm(P - J["upperarm_" + sd], axis=1) < 0.115
        yoke |= (z > 1.405) & (np.abs(x) < np.abs(J["upperarm_l"][0]) + 0.02)     # r2: the top stitch line
        yoke &= puff
        bc[yoke] = OX * (0.95 + 0.05 * TX.noise(P[yoke], 80, 2))[:, None]
    # the balaclava: sweat and breath darkening round the mouth and eyes, grime where the hands pull it, pilling
    mk = kind == K["maskknit"]
    if mk.any():
        Pm = P[mk]
        Hd = man.H
        c = bc[mk]
        mouth = np.clip(1 - np.linalg.norm((Pm - Hd.mouth) * np.array([0.8, 1, 1.2]), axis=1) / 0.045, 0, 1)
        eyes = np.zeros(len(Pm))
        for sd in "lr":
            e = Hd.face.eye_centre(sd)
            eyes = np.maximum(eyes, np.clip(1 - np.linalg.norm((Pm - e) * np.array([0.7, 1, 1.2]), axis=1) / 0.035, 0, 1))
        brow = np.clip(1 - np.abs(Pm[:, 2] - (Hd.face.ez + 0.03)) / 0.02, 0, 1) * (Pm[:, 1] < Hd.j[1] - 0.06)
        sweat = np.clip(0.8 * mouth + 0.45 * eyes + 0.3 * brow, 0, 1) * (0.7 + 0.3 * TX.fbm(Pm, 60, 2, seed=71))
        grime = ss(0.55, 0.9, TX.fbm(Pm, 25.0, 3, seed=72)) * 0.5
        c = c * (1 - 0.30 * sweat)[:, None] * (1 - 0.15 * grime)[:, None] + DUST * 0.06 * grime[:, None]
        bc[mk] = c
        rough[mk] = rough[mk] - 0.12 * sweat
    return v_


def vertex_ao(ob, others=(), rays=24, distance=0.07, smooth=3):
    """Per-vertex ambient occlusion (the outfit's other pieces occlude too), smoothed over the mesh and stored as the
    point attribute mi_ao (1 = open). Interpolated across UV seams, so it never steps at an island border the way a
    low-resolution texture bake does on fragmented cloth islands."""
    from mi import geo as _geo
    from mi import char as _char
    occ = _geo.occlusion(ob, distance=distance, rays=rays, seed=3, others=others)
    a = 1.0 - occ
    idx, ptr = _char.adjacency(ob)
    deg = np.maximum(np.diff(ptr), 1).astype(np.float64)
    for _ in range(smooth):
        sums = np.add.reduceat(a[idx], ptr[:-1]) if len(idx) else a
        a = 0.5 * a + 0.5 * sums / deg
    at = ob.data.attributes.get("mi_ao") or ob.data.attributes.new("mi_ao", "FLOAT", "POINT")
    at.data.foreach_set("value", a.astype(np.float32))
    return a


def bake_set(ob, set_name, res, man, log, res_override=None, others=()):
    from mi import bake as _bake
    res = res_override or res
    vertex_ao(ob, others)
    maps = TX.bake_maps(ob, res, face_attrs=["mi_kind", "mi_r", "mi_g", "mi_b", "mi_piece", "mi_ao", "mi_loft"])
    log("  %s: maps baked at %d, coverage %.1f %%" % (set_name, res, 100 * maps["mask"].mean()))
    H, W = maps["mask"].shape
    mask = maps["mask"]
    aol = TX.dilate(np.clip(maps["mi_ao"], 0, 1).astype(np.float32), mask, 4)
    idx = np.nonzero(mask.ravel())[0]
    bc = np.zeros((H * W, 3), dtype=np.float32)
    ro = np.full(H * W, 0.8, dtype=np.float32)
    me = np.zeros(H * W, dtype=np.float32)
    hh = np.zeros(H * W, dtype=np.float32)
    Pf, Nf = maps["pos"].reshape(-1, 3), maps["normal"].reshape(-1, 3)
    kind_f = np.rint(maps["mi_kind"].ravel()).astype(int)
    piece_f = np.rint(maps["mi_piece"].ravel()).astype(int)
    base_f = np.stack([maps["mi_r"].ravel(), maps["mi_g"].ravel(), maps["mi_b"].ravel()], axis=1)
    aof = aol.ravel()
    loftf = maps["mi_loft"].ravel()
    for sl in TX.chunks(idx, 700_000):
        P, N = Pf[sl].astype(np.float64), Nf[sl]
        c, r, mt, h = texels(man, P, N, kind_f[sl], base_f[sl].astype(np.float32), piece_f[sl], aof[sl], loftf[sl])
        regions(man, P, N, kind_f[sl], piece_f[sl], c, h, r)
        bc[sl], ro[sl], me[sl], hh[sl] = c, r, mt, h
    hh = hh.reshape(H, W)
    hd = TX.dilate(hh, mask, 4)
    nrm = TX.normal_from_height(hd, maps["pos"], mask)
    cav = np.clip(TX.blur(hd, 3) - hd, 0, None)
    ao = np.clip(1.0 - cav / 0.0003, 0.6, 1.0) * (0.3 + 0.7 * aol)
    ch = {"bc": TX.dilate(np.clip(bc, 0, 1).reshape(H, W, 3), mask, 24), "rough": TX.dilate(ro.reshape(H, W), mask, 24),
          "metal": TX.dilate(me.reshape(H, W), mask, 24), "normal": TX.dilate(nrm, mask, 24),
          "ao": TX.dilate(ao, mask, 24), "height": hd}
    info = _bake.write_set(set_name, ch, meta={"kind": "unique", "asset": set_name, "resolution_px": res})
    fill_gaps(set_name)
    log("  %s written (gaps filled)" % set_name)
    return info


# ------------------------------------------------------------------------------------------------ gap fill


def pull_push(img, known):
    """Fill every texel outside the UV islands from the islands around it (masked mip pyramid, coarse to fine), so
    no mip level mixes the empty background into the cloth: the fragmented islands of draped cloth otherwise show a
    dark stepped fringe along their borders at a distance (texture streaming reads the small mips)."""
    img = img.astype(np.float32)
    if img.ndim == 2:
        img = img[..., None]
    levels = [(img * known[..., None], known.astype(np.float32))]
    while levels[-1][1].shape[0] > 1:
        c, w = levels[-1]
        H, W = w.shape
        c2 = c.reshape(H // 2, 2, W // 2, 2, -1).sum(axis=(1, 3))
        w2 = w.reshape(H // 2, 2, W // 2, 2).sum(axis=(1, 3))
        levels.append((c2, w2))
    out = levels[-1][0] / np.maximum(levels[-1][1], 1e-6)[..., None]
    for c, w in reversed(levels[:-1]):
        up = np.repeat(np.repeat(out, 2, axis=0), 2, axis=1)
        mine = c / np.maximum(w, 1e-6)[..., None]
        out = np.where((w > 0)[..., None], mine, up)
    return out if out.shape[-1] > 1 else out[..., 0]


def fill_gaps(set_name):
    """Re-write T_<set>_BC / _N / _ORM with the background filled by pull_push (the known texels are those the bake
    and its dilation wrote: everything that is not pure black in BC)."""
    import os
    from PIL import Image
    from mi import paths
    d = paths.texture_set(set_name)
    p = lambda t: os.path.join(d, "T_%s_%s.png" % (set_name, t))
    bc = np.asarray(Image.open(p("BC")).convert("RGB"), dtype=np.float32)
    known = bc.max(axis=2) > 0
    for t in ("BC", "N", "ORM"):
        im = np.asarray(Image.open(p(t)).convert("RGB"), dtype=np.float32)
        f = pull_push(im, known)
        if t == "N":
            v = f / 127.5 - 1.0
            v /= np.maximum(np.linalg.norm(v, axis=2, keepdims=True), 1e-6)
            f = (v + 1.0) * 127.5
        Image.fromarray(np.clip(np.rint(f), 0, 255).astype(np.uint8)).save(p(t), optimize=False)
    return float(known.mean())


# ------------------------------------------------------------------------------------------------ tiling detail


def detail_normal(res=1024, tile_m=0.025, seed=5):
    """T_GoonFabric_Detail_N: a tiling fibre normal (one repeat = `tile_m`, 25 mm) that Unreal adds to every Goon
    set in proportion to the cloth amount (mi_chars.goon_material): isotropic fuzz and 0.3-1 mm fibre clumps, so it
    reads the same on every UV island whatever its angle. Periodic by construction (filtered in Fourier space)."""
    import os
    from PIL import Image
    from mi import paths
    rng = np.random.default_rng(seed)
    f = np.fft.fftfreq(res) * res / tile_m                       # cycles per metre
    fx, fy = np.meshgrid(f, f)
    fr = np.sqrt(fx ** 2 + fy ** 2) + 1e-9
    h = np.zeros((res, res))
    for lam, amp in ((0.0012, 1.0), (0.0005, 0.6), (0.00025, 0.35)):  # clumps, fibres, fuzz (wavelengths in m)
        band = np.exp(-((np.log(fr * lam)) ** 2) / 0.35)
        z = np.fft.fft2(rng.standard_normal((res, res))) * band
        layer = np.real(np.fft.ifft2(z))
        h += amp * layer / layer.std()
    h *= 0.000016                                                # metres of relief: mean tilt about 12 deg
    px = tile_m / res
    gx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) / (2 * px)
    gy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) / (2 * px)
    n = np.stack([-gx, gy, np.ones_like(h)], axis=2)              # OpenGL (green up), as the baked sets
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    d = paths.texture_set("GoonFabric_Detail")
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, "T_GoonFabric_Detail_N.png")
    Image.fromarray(np.clip(np.rint((n + 1) * 127.5), 0, 255).astype(np.uint8)).save(out)
    return out, float(np.degrees(np.arccos(n[..., 2])).mean())
