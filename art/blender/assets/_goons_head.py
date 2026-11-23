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
        self.mouth = np.array([0.0, self._front_at(P, 0.0, self.j[2] + 0.012), self.j[2] + 0.012])

    @staticmethod
    def _front_at(P, x, z):
        near = P[(np.abs(P[:, 0] - x) < 0.008) & (np.abs(P[:, 2] - z) < 0.006)]
        return near[:, 1].min()

    def _chin(self, P):
        front = P[P[:, 1] < self.front + 0.05]
        return front[:, 2].min()

    def __call__(self, p):
        return self.F(p)


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


def mask(H, col, bottom_z, h=0.0024, slits=True):
    """The knitted ski mask: the head and neck grown by the fabric, open only at the bottom (inside the collar),
    the eye slits sunk 9 mm into it (their floor is the black inside)."""
    def f(p):
        d = H(p) - MASK_T
        if slits:
            d = np.maximum(d, -slit_field(H, p))
        return d
    lo, hi = H.lo + 0.01, H.hi - 0.01
    lo = np.array([lo[0], lo[1], bottom_z - 0.01])
    ob = cloth.garment_mesh("Mask", f, lo, hi, h, cuts=[((0, 0, bottom_z), (0, 0, -1))], col=col, relax=3)
    return ob


def hood(H, col, neck_ring, h=0.0105, ease=0.024, back=0.035):
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
    cuts = [((fc[0], fc[1] - 0.035, fc[2]), unit((0, -1.0, -0.42))),       # the face opening
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
    """Knitted beanie: a fitted crown over the mask from the brow line, with a 5 cm turned-up cuff that stands
    off the crown by its double thickness."""
    j = H.j
    p0, n0 = _tilted(j, H.eye["l"][2] + 0.040, H.eye["l"][2] + 0.0)
    crown = lambda p: H(p) - MASK_T - 0.0045 - 0.004 * np.clip((p[:, 2] - H.top + 0.05) / 0.05, 0, 1)
    lo = np.array([j[0] - 0.14, j[1] - 0.17, p0[2] - 0.08])
    hi = np.array([j[0] + 0.14, j[1] + 0.15, H.top + 0.04])
    ob = cloth.garment_mesh("Beanie", crown, lo, hi, h, cuts=[(p0, n0)], col=col, relax=3)
    cuff_top = (p0 - n0 * 0.05, n0 * -1)
    band = lambda p: H(p) - MASK_T - 0.0105
    cf = cloth.garment_mesh("BeanieCuff", band, lo, hi, h, cuts=[(p0 + n0 * 0.002, n0), (p0 - n0 * 0.052, -n0)], col=col,
                            relax=3)
    cloth.hem_facing(cf, depth=0.01, thickness=0.006, steps=1)
    return ob, cf


def cap_backwards(H, col, h=0.0035):
    """Fitted baseball cap worn backwards: six-panel crown over the mask (top button), the oxblood brim
    (0.15 m wide, 0.09 m long) at the back, pointing to the rear and tilted up."""
    j = H.j
    p0, n0 = _tilted(j, H.eye["l"][2] + 0.035, H.eye["l"][2] - 0.005)
    crown = lambda p: H(p) - MASK_T - 0.004 - 0.010 * np.clip((p[:, 2] - H.top + 0.06) / 0.06, 0, 1) * np.clip((-(p[:, 1] - j[1]) + 0.04) / 0.1, 0, 1)
    lo = np.array([j[0] - 0.14, j[1] - 0.17, p0[2] - 0.08])
    hi = np.array([j[0] + 0.14, j[1] + 0.16, H.top + 0.04])
    ob = cloth.garment_mesh("CapCrown", crown, lo, hi, h, cuts=[(p0, n0)], col=col, relax=3)
    cloth.hem_facing(ob, depth=0.015, thickness=0.003, steps=1)
    # brim: a curved plate whose inner edge follows the crown's back edge
    back = j + np.array([0, 0.0, 0])
    P = []
    m, k = 13, 7
    ring = []
    for a in np.linspace(-1, 1, m):
        ang = a * 0.95
        d = np.array([np.sin(ang), np.cos(ang), 0.0])
        q = j + np.array([0, 0, p0[2] - j[2] + 0.02 + 0.03])          # near the band height at the back
        # the crown's edge in direction d: march outward on the band plane
        z_band = p0[2] + (-(n0[1]) * 0) - 0.012 + 0.04 * (d[1])
        ray0 = np.array([j[0], j[1], z_band]) + d * 0.2
        best = None
        for t in np.linspace(0, 0.2, 120):
            pp = ray0 - d * t
            if H(pp[None])[0] - MASK_T - 0.004 < 0:
                best = pp + d * 0.002
                break
        ring.append(best if best is not None else ray0 - d * 0.1)
    ring = np.array(ring)
    width = 0.15
    ring[:, 0] *= (width / 2) / max(np.abs(ring[:, 0]).max(), 1e-3) if np.abs(ring[:, 0]).max() > width / 2 else 1.0
    V, F = [], []
    for i, p in enumerate(ring):
        a = np.linspace(-1, 1, m)[i]
        out = unit(np.array([p[0] - j[0], p[1] - j[1], 0.0]))
        L = 0.09 * np.sqrt(max(1 - (a * 0.92) ** 2, 0.05))
        for jj, s in enumerate(np.linspace(0, 1, k)):
            q = p + out * L * s + np.array([0, 0, 0.018 * s * s + 0.004 * s])   # tilted up toward the tip
            q = q - np.array([0, 0, 0.006 * (1 - a * a) * s])                     # the brim's curve
            V.append(q)
    for i in range(m - 1):
        for jj in range(k - 1):
            a = i * k + jj
            F.append((a, a + 1, a + k + 1, a + k))
    from mi import geo
    br = geo.from_arrays("CapBrim", np.array(V), F, col, smooth=None)
    for p in br.data.polygons:
        p.use_smooth = True
    md = br.modifiers.new("solid", "SOLIDIFY")
    md.thickness = 0.004
    md.offset = 0.0
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
