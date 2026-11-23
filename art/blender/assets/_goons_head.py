"""The Goons' heads: the knitted ski mask over the mannequin's head (eye slits recessed into it, black inside), the
hood (draped), the beanie with its turned-up cuff, the backwards cap, the wrap-around glasses and the bandana.
No skin shows anywhere: the mask covers the face and neck and runs down inside the collar.
"""
import os

import numpy as np

from mi import cloth, paths, sdf
from assets import _goons_body as GB
from assets._goons_cloth import unit, verts, set_verts, onto_level

MASK_T = 0.0035              # mask fabric over the head
SLIT = (0.046, 0.017)        # eye slit length x height (brief)
SLIT_TILT = 11.0             # degrees, outer end higher (a hard look)


class Head:
    """The head's local landmarks and a fine distance field of the mannequin's head and neck."""

    def __init__(self, B):
        self.B = B
        self.j = B.J["head"]
        self.neck = B.J["neck_01"]
        lo = self.j + np.array([-0.13, -0.19, -0.20])
        hi = self.j + np.array([0.13, 0.14, 0.22])
        self.F = GB.BodyField(B, h=0.003, lo=lo, hi=hi, cache=os.path.join(paths.out, "goons", "head_field.npz"))
        self.lo, self.hi = lo, hi
        # the face: the frontmost head point at eye height, eyes either side
        P = B.pts("head")
        self.top = P[:, 2].max()
        self.front = P[:, 1].min()
        self.chin_z = self._chin(P)
        eye_z = self.j[2] + 0.073
        self.eye = {}
        for s, sx in (("l", 1), ("r", -1)):
            x = sx * 0.034
            near = P[(np.abs(P[:, 0] - x) < 0.006) & (np.abs(P[:, 2] - eye_z) < 0.006)]
            y = near[:, 1].min() if len(near) else self.front + 0.02
            self.eye[s] = np.array([x, y, eye_z])
        self.face = FaceShape(self)
        # the mouth of the face proxy (the mannequin's long smooth face has none: FaceShape puts it 8 cm under the eyes)
        mz = eye_z - FaceShape.MOUTH_V
        self.mouth = np.array([0.0, self._front_at(P, 0.0, mz) - self.face.bump(np.array([[0.0, self.front, mz]]))[0],
                               mz])

    @staticmethod
    def _front_at(P, x, z):
        near = P[(np.abs(P[:, 0] - x) < 0.008) & (np.abs(P[:, 2] - z) < 0.006)]
        return near[:, 1].min()

    def _chin(self, P):
        front = P[P[:, 1] < self.front + 0.05]
        return front[:, 2].min()

    def __call__(self, p):
        """The head with the face proxy (brow, nose, cheekbones, lips, chin) the knit lies over."""
        return self.F(p) - self.face.bump(p)

    def skin(self, p):
        """The face under the knit: the proxy with its eye sockets."""
        return self.F(p) - self.face.bump(p, sockets=True)


def _g(x, s):
    return np.exp(-(x / s) ** 2)


class FaceShape:
    """A face for the featureless mannequin head (rebuild r2: the mask read as a smooth plague-doctor shell). A
    displacement of the head's distance field toward the front, in metres, from the eye line (v = z - eye z):
    brow ridge, nose (bridge 4 mm, tip 17 mm out, 47 mm under the eyes, alae), cheekbones, upper and lower lip,
    a chin 11 cm under the eyes and the long mannequin jaw receded under it (the face reads shorter). With
    sockets=True the eye sockets are carved 3 mm (the skin behind the mask's eye openings)."""
    MOUTH_V = 0.080
    EYE_X, EYE_V = 0.033, 0.002

    def __init__(self, H):
        self.H = H
        self.ez = H.j[2] + 0.073
        self.jy = H.j[1]

    def bump(self, p, sockets=False):
        x, v = p[:, 0], p[:, 2] - self.ez
        ax = np.abs(x)
        wf = np.clip((self.jy - 0.075 - p[:, 1]) / 0.03, 0, 1)          # the front of the face only
        nv = [-0.064, -0.056, -0.047, -0.040, -0.020, 0.0, 0.012, 0.024]
        nh = [0.0, 0.0085, 0.0165, 0.0160, 0.0100, 0.0045, 0.0022, 0.0]
        nw = [0.009, 0.011, 0.0105, 0.0095, 0.0080, 0.0072, 0.0085, 0.010]
        b = np.interp(v, nv, nh) * _g(x, np.interp(v, nv, nw)) ** 1.0
        b += 0.0065 * _g(ax - 0.0155, 0.0065) * _g(v + 0.050, 0.0065)                          # alae
        b += 0.0042 * _g(v - 0.019, 0.0075) * _g(ax - 0.026, 0.024)                            # brow ridge
        b += 0.0045 * _g(ax - 0.048, 0.015) * _g(v + 0.030, 0.013)                             # cheekbones
        b += 0.0030 * _g(x, 0.020) * _g(v + self.MOUTH_V - 0.006, 0.0042)                      # upper lip
        b += 0.0034 * _g(x, 0.018) * _g(v + self.MOUTH_V + 0.007, 0.0045)                      # lower lip
        b += 0.0050 * _g(x, 0.022) * _g(v + 0.108, 0.010)                                      # chin
        b -= 0.0022 * _g(x, 0.024) * _g(v + 0.095, 0.006)                                      # mentolabial fold
        b -= 0.0110 * np.clip((-v - 0.122) / 0.03, 0, 1) * _g(ax, 0.05)                        # jaw receded
        if sockets:
            b -= 0.0032 * _g(ax - self.EYE_X, 0.013) * _g(v - self.EYE_V, 0.009)
        return b * wf

    def eye_centre(self, s):
        """Centre of the eyeball (radius 12 mm) behind the mask's eye opening `s` ('l' / 'r')."""
        sx = 1.0 if s == "l" else -1.0
        x, z = sx * self.EYE_X, self.ez + self.EYE_V
        ys = np.linspace(self.jy - 0.2, self.jy, 800)
        P = np.stack([np.full_like(ys, x), ys, np.full_like(ys, z)], axis=1)
        d = self.H.skin(P)
        y0 = ys[np.argmax(d < 0)]
        return np.array([x, y0 + EYE_R - 0.0028, z])


EYE_R = 0.012


def slit_field(H, p, grow=0.0):
    """Distance to the two eye-slit volumes (flattened capsules leaning into the head)."""
    d = None
    for s, sx in (("l", 1), ("r", -1)):
        c = H.eye[s] + np.array([0, 0.004, 0])
        t = np.radians(SLIT_TILT)
        u = np.array([sx * np.cos(t), 0.0, np.sin(t)])                  # along the slit, outward and up
        w = np.array([0, -1.0, 0])
        v = unit(np.cross(w, u))
        q = sdf.local(p, c, np.array([u, v, w]))
        half = SLIT[0] / 2 + grow
        r = SLIT[1] / 2 + grow
        # a lens: thicker in the middle, pointed at the ends
        t = np.clip(np.abs(q[:, 0]) / half, 0, 1)
        rr = r * np.sqrt(np.maximum(1 - t ** 2.2, 0.02))
        dd = np.maximum(np.abs(q[:, 1]) - rr, np.abs(q[:, 0]) - half)
        dd = np.maximum(dd, np.abs(q[:, 2]) - 0.02)
        d = dd if d is None else np.minimum(d, dd)
    return d


def mask(H, col, bottom_z, h=0.0024, slits=True, neck=None):
    """The knitted ski mask: the head and neck grown by the fabric, open only at the bottom (inside the collar),
    the eye slits sunk 9 mm into it (their floor is the black inside). Below the jaw it is held to a tube round
    the neck (`neck`: the neck joint), so it tucks into the collar instead of spreading over the shoulders."""
    def f(p):
        d = H(p) - MASK_T
        if neck is not None:
            r = np.sqrt((p[:, 0] - neck[0]) ** 2 + ((p[:, 1] - neck[1] + 0.012) / 1.12) ** 2)
            tube = r - 0.072 - 0.2 * np.clip((p[:, 2] - neck[2] - 0.03) / 0.05, 0, 1)
            d = sdf.smax(d, tube, 0.01)
        if slits:
            d = np.maximum(d, -slit_field(H, p))
        return d
    lo, hi = H.lo + 0.01, H.hi - 0.01
    lo = np.array([lo[0], lo[1], bottom_z - 0.01])
    ob = cloth.garment_mesh("Mask", f, lo, hi, h, cuts=[((0, 0, bottom_z), (0, 0, -1))], col=col, relax=3)
    return ob


EYE_HOLE = (0.0185, 0.0088, 5.0)     # eye opening semi-axes (m) and tilt (deg, outer end up)
MOUTH_HOLE = (0.0215, 0.0075)       # mouth opening semi-axes


def hole_frames(H):
    """(name, centre, u, v, a, b) of the three openings of the balaclava, on the face proxy's surface."""
    from assets import _goons_trim as TR
    fs = H.face
    out = []
    for s, sx in (("l", 1.0), ("r", -1.0)):
        t = np.radians(EYE_HOLE[2])
        u = np.array([sx * np.cos(t), 0.0, np.sin(t)]) * sx           # always +x first (a consistent frame)
        v = np.array([-np.sin(t) * sx, 0.0, np.cos(t)])
        c = np.array([sx * fs.EYE_X, H.front, fs.ez + fs.EYE_V])
        out.append(("EyeHem_" + s, c, u, v, EYE_HOLE[0], EYE_HOLE[1]))
    c = np.array([0.0, H.front, H.mouth[2]])
    out.append(("MouthHem", c, np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), MOUTH_HOLE[0], MOUTH_HOLE[1]))
    # the centres onto the surface (along -y from the front)
    res = []
    for nm, c, u, v, a, b in out:
        ys = np.linspace(H.j[1] - 0.22, H.j[1], 900)
        P = np.stack([np.full_like(ys, c[0]), ys, np.full_like(ys, c[2])], axis=1)
        d = H(P) - MASK_T
        res.append((nm, np.array([c[0], ys[np.argmax(d < 0)], c[2]]), u, v, a, b))
    return res


def balaclava(H, col, bottom_z, neck, h=0.0022):
    """A 2000-era three-hole balaclava in charcoal rib knit over the face proxy: the head grown by the fabric
    (open only at the bottom, tucked into the collar), two small eye openings and a mouth opening cut on clean
    ellipses with rolled, hemmed edges. Returns (mask, [hems])."""
    from assets import _goons_trim as TR
    ob = mask(H, col, bottom_z, h=h, slits=False, neck=neck)
    f = lambda p: H(p) - MASK_T
    hems = []
    for nm, c, u, v, a, b in hole_frames(H):
        hems.append(TR.cut_ellipse_hole(ob, f, c, u, v, a, b, depth=0.02, hem_r=0.0022, col=col, name=nm))
    return ob, hems


def face_skin(H, col, h=0.0016):
    """What the openings show: the skin of the face proxy round the eyes and the mouth (eye sockets, lids, lips;
    under the knit by a margin so no gap shows) and two eyeballs set into the sockets (the lids are where they meet
    the skin). Returns (skin, eyes)."""
    from mi import geo, scene as _scene
    fs = H.face
    lo = np.array([-0.075, H.front - 0.03, H.mouth[2] - 0.03])
    hi = np.array([0.075, H.front + 0.045, fs.ez + 0.03])
    v, q = sdf.surface_nets(H.skin, lo, hi, h)
    v = sdf.project(H.skin, v, 3)
    keep = np.zeros(len(v), dtype=bool)
    for nm, c, u, vv, a, b in hole_frames(H):
        d = v - c
        r = np.sqrt(((d @ u) / (a + 0.009)) ** 2 + ((d @ vv) / (b + 0.008)) ** 2)
        keep |= (r < 1.0) & (np.abs(d[:, 1]) < 0.025)
    qk = q[keep[q].all(axis=1)]
    used = np.unique(qk)
    remap = -np.ones(len(v), dtype=np.int64)
    remap[used] = np.arange(len(used))
    skin = sdf.to_mesh("FaceSkin", v[used], remap[qk], col)
    eyes = []
    for s in "lr":
        e = geo.sphere(EYE_R, 24, 14, name="Eye_" + s)
        e.data.transform(np.diag([1.22, 1.0, 0.78, 1.0]).tolist())       # an almond opening where it meets the lids
        e.location = tuple(fs.eye_centre(s))
        _scene.move_to(e, col)
        _scene.apply_transforms(e)
        for p in e.data.polygons:
            p.use_smooth = True
        eyes.append(e)
    return skin, geo.join(eyes, "Eyes", col)


def hood(H, col, neck_ring, h=0.0105, ease=0.024, back=0.035, face_r=0.10):
    """The hood up: the head grown by `ease` (more at the back and the crown, where a hood stands off), open at
    the face, its bottom on the neckline ring `neck_ring` (points of the body's neck opening)."""
    j = H.j

    def f(p):
        y = p[:, 1] - j[1]
        z = p[:, 2] - j[2]
        e = ease + back * np.clip((y + 0.02) / 0.12, 0, 1) * np.clip((z + 0.02) / 0.12, 0.3, 1) + 0.008 * np.clip(z / 0.15, 0, 1)
        return H(p) - e
    ring_z = float(np.mean(neck_ring[:, 2]))
    fc = j + np.array([0, -0.05, 0.035])
    cuts = [((fc[0], fc[1] - 0.035, fc[2]), unit((0, -1.0, -0.42)), face_r),       # the face opening (closes under the chin)
            ((0, 0, ring_z), (0, 0, -1))]
    lo = np.array([j[0] - 0.17, j[1] - 0.19, ring_z - 0.03])
    hi = np.array([j[0] + 0.17, j[1] + 0.20, H.top + 0.08])
    ob = cloth.garment_mesh("Hood", f, lo, hi, h, cuts=cuts, col=col, relax=4)
    return ob, cuts


# ------------------------------------------------------------------------------------------------ hats, glasses


def _tilted(j, front_z, back_z):
    """(point, normal) of a plane through the head at front_z (forehead) and back_z (nape), normal down."""
    a = np.array([0, j[1] - 0.12, front_z])
    b = np.array([0, j[1] + 0.12, back_z])
    t = unit(b - a)
    n = unit(np.cross(t, np.array([1.0, 0, 0])))
    if n[2] > 0:
        n = -n
    return a, n


def beanie(H, col, h=0.004):
    """Knitted beanie: a fitted crown over the mask from the brow line (its cut edge tidied), and a 5 cm turned-up
    cuff (4.6 cm) as one closed double-walled band round the head (no cut edges: the r1 cuff tore into jagged holes)."""
    from assets import _goons_trim as TR
    j = H.j
    p0, n0 = _tilted(j, H.eye["l"][2] + 0.030, H.eye["l"][2] - 0.004)
    crown = lambda p: H(p) - MASK_T - 0.0045 - 0.004 * np.clip((p[:, 2] - H.top + 0.05) / 0.05, 0, 1)
    lo = np.array([j[0] - 0.14, j[1] - 0.17, p0[2] - 0.08])
    hi = np.array([j[0] + 0.14, j[1] + 0.15, H.top + 0.04])
    ob = cloth.garment_mesh("Beanie", crown, lo, hi, h, cuts=[(p0, n0)], col=col, relax=3)
    TR.tidy_open_edges(ob)
    c0 = j + n0 * ((p0 - j) @ n0)
    cf = TR.axis_band("BeanieCuff", H, MASK_T + 0.0135, c0, -n0, -0.004, 0.042, 0.0072, col, nu=120, ns=12,
                      ref=(0, -1.0, 0), ease_top=0.002)
    return ob, cf


def cap_backwards(H, col, h=0.0035, brim_drop=17.0):
    """Fitted baseball cap worn backwards: six-panel crown over the mask (top button), its edge tidied and closed by
    a sweatband (a closed band tube round the head, no sawtooth), the oxblood brim (0.15 m wide, 0.09 m long) at the
    back, attached under the crown's edge and lying down over the nape `brim_drop` degrees below the horizontal.
    Rigid on the head bone."""
    from assets import _goons_trim as TR
    from mi import geo
    j = H.j
    p0, n0 = _tilted(j, H.eye["l"][2] + 0.035, H.eye["l"][2] - 0.005)
    crown = lambda p: H(p) - MASK_T - 0.004 - 0.010 * np.clip((p[:, 2] - H.top + 0.06) / 0.06, 0, 1) * np.clip((-(p[:, 1] - j[1]) + 0.04) / 0.1, 0, 1)
    lo = np.array([j[0] - 0.14, j[1] - 0.17, p0[2] - 0.08])
    hi = np.array([j[0] + 0.14, j[1] + 0.16, H.top + 0.04])
    ob = cloth.garment_mesh("CapCrown", crown, lo, hi, h, cuts=[(p0, n0)], col=col, relax=3)
    TR.tidy_open_edges(ob)
    c0 = j + n0 * ((p0 - j) @ n0)
    band = TR.axis_band("CapBand", H, MASK_T + 0.0068, c0, -n0, -0.003, 0.016, 0.0048, col, nu=120, ns=6,
                        ref=(0, -1.0, 0))
    ob = geo.join([ob, band], "CapCrown", col)

    def edge_z(x, y):                                   # the crown's edge plane at (x, y)
        return p0[2] - (n0[0] * (x - p0[0]) + n0[1] * (y - p0[1])) / n0[2]
    m, k = 15, 8
    ring = []
    for a in np.linspace(-1, 1, m):
        ang = a * 0.95
        d = np.array([np.sin(ang), np.cos(ang), 0.0])
        best = None
        for t in np.linspace(0.0, 0.2, 200):
            pp = np.array([j[0], j[1], 0.0]) + d * (0.2 - t)
            pp[2] = edge_z(pp[0], pp[1]) + 0.002
            if H(pp[None])[0] - MASK_T - 0.0068 < 0:
                best = pp
                break
        ring.append(best if best is not None else np.array([j[0], j[1], 0.0]) + d * 0.1)
    ring = np.array(ring)
    width = 0.15
    if np.abs(ring[:, 0]).max() > width / 2:
        ring[:, 0] *= (width / 2) / np.abs(ring[:, 0]).max()
    V, F = [], []
    cd, sd = np.cos(np.radians(brim_drop)), np.sin(np.radians(brim_drop))
    for i, p in enumerate(ring):
        a = np.linspace(-1, 1, m)[i]
        out = unit(np.array([p[0] - j[0], p[1] - j[1], 0.0]))
        L = 0.09 * np.sqrt(max(1 - (a * 0.92) ** 2, 0.05))
        for jj, s in enumerate(np.linspace(0, 1, k)):
            q = p + out * (L * s * cd) - np.array([0, 0, L * s * sd])
            q = q - np.array([0, 0, 0.010 * (a * a) * s])                       # the brim's curve, sides lower
            V.append(q)
    for i in range(m - 1):
        for jj in range(k - 1):
            a = i * k + jj
            F.append((a, a + 1, a + k + 1, a + k))
    br = geo.from_arrays("CapBrim", np.array(V), F, col, smooth=None)
    for p in br.data.polygons:
        p.use_smooth = True
    md = br.modifiers.new("solid", "SOLIDIFY")
    md.thickness = 0.0042
    md.offset = 0.0
    md.use_rim = True
    geo._apply_modifier(br, md)
    md = br.modifiers.new("bev", "BEVEL")
    md.width, md.segments = 0.0012, 2
    geo._apply_modifier(br, md)
    button = geo.sphere(0.0065, 12, 6, name="CapButton")
    top = np.array([j[0], j[1] + 0.005, H.top + 0.02])
    for t in np.linspace(0, 0.06, 80):
        if H(np.array([top - np.array([0, 0, t])]))[0] - MASK_T - 0.004 < 0:
            top = top - np.array([0, 0, t - 0.003])
            break
    button.data.transform(np.diag([1, 1, 0.45, 1]).tolist())
    button.location = tuple(top)
    from mi import scene as _scene
    _scene.move_to(button, col)
    _scene.apply_transforms(button)
    return ob, br, button


def glasses(H, col, h=0.0013, width=0.19, stand=0.016):
    """Wrap-around glasses: one curved lens band standing `stand` off the mask, 0.19 m wide, with a thick rim
    and temple arms back over the ears."""
    from mi import geo, scene as _scene
    j = H.j
    ez = H.eye["l"][2] + 0.002
    f = lambda p: H(p) - MASK_T - stand
    # outline: front half of the head, eye band, shaped lower in the middle over the nose
    half = width / 2

    def g(p):
        d = f(p)
        x = np.abs(p[:, 0] - j[0])
        top = ez + 0.021 - 0.004 * (x / half) ** 2
        bot = ez - 0.022 + 0.010 * np.exp(-(x / 0.016) ** 2) + 0.004 * (x / half) ** 2
        d = np.maximum(d, p[:, 2] - top)
        d = np.maximum(d, bot - p[:, 2])
        d = np.maximum(d, (p[:, 1] - (j[1] - 0.03)))                 # front only
        return d
    lo = np.array([j[0] - 0.13, j[1] - 0.20, ez - 0.05])
    hi = np.array([j[0] + 0.13, j[1] + 0.0, ez + 0.05])
    v, q = sdf.surface_nets(lambda p: np.maximum(np.abs(f(p)) - 0.0015, g(p) - 0.0), lo, hi, h)
    v, q = sdf.keep_largest(v, q)
    lens = sdf.to_mesh("GlassesLens", v, q, col)
    # temple arms: from the outer ends of the lens back along the side of the head to above the ears
    arms = []
    for sx in (1, -1):
        pts = []
        for t in np.linspace(0, 1, 9):
            y = (j[1] - 0.05) + t * 0.15
            x = sx * 0.2
            pp = np.array([x, y, ez + 0.012 - 0.01 * t])
            for s in np.linspace(0, 0.15, 150):
                qq = pp - np.array([sx * s, 0, 0])
                if f(qq[None])[0] + stand - 0.004 < 0:
                    pp = qq + np.array([sx * 0.002, 0, 0])
                    break
            pts.append(pp)
        arms.append(geo.sweep(geo.rect_profile(0.0035, 0.009), [tuple(p) for p in pts], name="Temple",
                              up=(0, 0, 1)))
    ar = geo.join(arms, "GlassesArms", col)
    return lens, ar
