"""The Goons' garments: start shapes cut from the mannequin's surface (offsets plus hanging lofts), gathered into
their rib bands, draped by Blender's cloth solver in the rest A-pose, then finished (bands with turned edges, hem
facings). Used by assets/goons.py.

Every garment is its own mesh. Order matters (each drape collides with what is already dressed): sneakers and
head pieces, trousers, upper garment, hood.
"""
import numpy as np
from mathutils import Vector

from mi import cloth, geo, scene, sdf


def unit(v):
    v = np.asarray(v, dtype=np.float64)
    return v / max(np.linalg.norm(v), 1e-12)


def verts(ob):
    co = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def set_verts(ob, co):
    ob.data.vertices.foreach_set("co", np.asarray(co, dtype=np.float32).ravel())
    ob.data.update()


def onto_level(field, level, v, iters=6):
    """Points moved along the field gradient onto field = level."""
    return sdf.project(lambda p: field(p) - level, v, iters, e=2e-3)


def loops_by_cut(ob, cuts):
    """{cut index: [loop vertex indices]} for the open loops lying on the cut planes."""
    co = verts(ob)
    out = {}
    for L in cloth.boundary_loops(ob):
        P = co[L]
        best, bd = None, 1e9
        for i, c in enumerate(cuts):
            d = np.abs((P - np.asarray(c[0])) @ unit(c[1])).mean()
            if len(c) > 2 and c[2] is not None:
                d += 10.0 * (np.linalg.norm(P.mean(axis=0) - np.asarray(c[0])) > c[2])
            if d < bd:
                best, bd = i, d
        out.setdefault(best, []).extend(L)
    return out


# ------------------------------------------------------------------------------------------------ landmarks


class Marks:
    """Joint-derived landmarks shared by every outfit."""

    def __init__(self, B):
        J = B.J
        self.B = B
        self.neck = J["neck_01"]
        self.head = J["head"]
        self.wrist = {s: J["hand_" + s] for s in "lr"}
        self.elbow = {s: J["lowerarm_" + s] for s in "lr"}
        self.shoulder = {s: J["upperarm_" + s] for s in "lr"}
        self.fore = {s: unit(J["hand_" + s] - J["lowerarm_" + s]) for s in "lr"}      # elbow -> wrist
        self.upper = {s: unit(J["lowerarm_" + s] - J["upperarm_" + s]) for s in "lr"}
        self.hip = {s: J["thigh_" + s] for s in "lr"}
        self.knee = {s: J["calf_" + s] for s in "lr"}
        self.ankle = {s: J["foot_" + s] for s in "lr"}
        self.shin = {s: unit(J["foot_" + s] - J["calf_" + s]) for s in "lr"}


def cuff_plane(M, side, back):
    """(point, normal) of a plane across the forearm `back` metres above the wrist joint (normal toward the hand)."""
    return (M.wrist[side] - M.fore[side] * back, M.fore[side])


# ------------------------------------------------------------------------------------------------ shells


def torso_hang(B, hem, top, ease, taper=0.92, n=2.6, front_drop=0.0):
    """A loft that hangs from the chest: below the chest each section is at least the widest section above it
    (times `taper` toward the hem), the front never comes in further than the chest front."""
    T = B.torso
    st = []
    for z in np.arange(hem - 0.05, top + 0.001, 0.03):
        zz = np.clip(z, T[0, 0], T[-1, 0])
        a, fy, by = B.torso_at(zz)
        above = T[(T[:, 0] >= zz) & (T[:, 0] <= 1.40)]
        if len(above):
            k = np.clip((1.30 - z) / max(1.30 - hem, 1e-3), 0, 1)
            a = max(a, above[:, 1].max() * (1 - (1 - taper) * k))
            fy = min(fy, above[:, 2].min() + front_drop * k)
            by = max(by, np.percentile(above[:, 3], 60) * (1 - 0.3 * k))
        st.append(((0, (fy + by) / 2, z), (1, 0, 0), (0, 1, 0), a + ease, (by - fy) / 2 + ease, n))
    return cloth.Loft(st)


def sleeve_loft(B, M, side, ease, cuff_back, cuff_ease, bulk=1.0):
    secs = B.limb_sections(side, "arm", [-0.15, 0.0, 0.4, 0.8, 1.0, 1.4, 1.75, 2.0])
    out = []
    for i, (c, u, v, a, b) in enumerate(secs):
        e = ease * bulk
        out.append((c, u, v, a * bulk + e, b * bulk + e, 2.0))
    # the end of the sleeve: gathered into the cuff
    return cloth.Loft(out)


def leg_loft(B, side, ease_thigh, ease_shin, hem_z, straight=True):
    secs = B.limb_sections(side, "leg", [-0.12, 0.0, 0.3, 0.6, 0.9, 1.0, 1.3, 1.6, 1.85])
    out = []
    widest_below_knee = None
    for i, (c, u, v, a, b) in enumerate(secs):
        s = [-0.12, 0.0, 0.3, 0.6, 0.9, 1.0, 1.3, 1.6, 1.85][i]
        e = ease_thigh if s < 1.0 else ease_shin
        if straight and s >= 1.0:
            # a trouser leg hangs straight from the knee: never narrower than at the knee
            a, b = max(a, secs[5][3] * 0.98), max(b, secs[5][4] * 0.98)
        out.append((c, u, v, a + e, b + e, 2.0))
    # extend to the hem height along the shin
    c, u, v, a, b, n = out[-1]
    w = unit(np.asarray(out[-1][0]) - np.asarray(out[-2][0]))
    t = (hem_z - c[2]) / w[2]
    out.append((np.asarray(c) + w * t, u, v, a, b, n))
    return cloth.Loft(out)


def gather_ring(ob, idx, field, level):
    """Move the loop `idx` onto the surface field = level (the band it is sewn into)."""
    co = verts(ob)
    co[idx] = even_loop(onto_level(field, level, co[idx]))
    set_verts(ob, co)


def even_loop(P):
    """Respace an ordered closed loop of points evenly along its own length (keeps the shape, no coincident
    points after a projection)."""
    P = np.asarray(P, dtype=np.float64)
    Q = np.vstack([P, P[:1]])
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))])
    s = np.linspace(0, L[-1], len(P), endpoint=False)
    return np.stack([np.interp(s, L, Q[:, k]) for k in range(3)], axis=1)


def band(name, field, level, cuts, h, col, lo, hi):
    """A rib band (waistband, cuff, collar) as the level set field = level between cut planes."""
    f = lambda p: field(p) - level
    return cloth.garment_mesh(name, f, lo, hi, h, cuts=cuts, col=col, relax=3)


def grow_weights(co, centres, radius, power=1.0):
    """0..1 weights that fall off from the given centres (n, 3) points over `radius`."""
    w = np.zeros(len(co))
    for c in centres:
        d = np.linalg.norm(co - np.asarray(c), axis=1)
        w = np.maximum(w, np.clip(1 - d / radius, 0, 1) ** power)
    return w


# ------------------------------------------------------------------------------------------------ garments


def trousers(B, M, BF, col, colliders, name="Jeans", waist=1.005, hem=0.11, ease_seat=0.012, ease_thigh=0.022,
             ease_shin=0.026, grow=-0.05, h=0.0105, log=None, frames=40, mass=0.3, bending=1.2):
    """Trousers: the body grown by the seat ease, each leg hanging straight from the knee; open at the waist and
    the hems, cut a little long and dropped onto the sneakers so the hems break."""
    legs = {s: leg_loft(B, s, ease_thigh, ease_shin, hem) for s in "lr"}

    knee_z = 0.5 * (M.knee["l"][2] + M.knee["r"][2])

    def f(p):
        d = np.maximum(BF(p) - ease_seat, knee_z - 0.06 - p[:, 2])       # the body above the knees only
        d = sdf.smin(d, legs["l"](p), 0.03)
        d = sdf.smin(d, legs["r"](p), 0.03)
        return d
    cuts = [((0, 0, waist), (0, 0, 1)), ((0, 0, hem), (0, 0, -1))]
    ob = cloth.garment_mesh(name, f, (-0.32, -0.25, hem - 0.03), (0.32, 0.22, waist + 0.03), h, cuts=cuts, col=col)
    L = loops_by_cut(ob, cuts)
    co = verts(ob)
    pin = np.zeros(len(co))
    pin[L[0]] = 1.0
    # the hems grow longer (they stack on the shoe), the knees a little
    g = grow_weights(co, [M.ankle["l"] + np.array([0, 0, 0.08]), M.ankle["r"] + np.array([0, 0, 0.08])], 0.25)
    g = np.maximum(g, 0.6 * grow_weights(co, [M.knee["l"] - np.array([0, 0.05, 0]), M.knee["r"] - np.array([0, 0.05, 0])], 0.12))
    g = np.maximum(g, 0.2) * (1 - pin)
    cloth.drape(ob, colliders, frames=frames, pin=pin, shrink=g, shrink_min=grow, log=log, mass=mass, bending=bending)
    return ob, L


def hoodie_shell(B, M, BF, col, colliders, hem_top=0.925, neck=1.535, cuff=0.065, ease=0.024, hang=0.034,
                 sleeve=0.026, grow=-0.045, h=0.0105, band_level=0.016, cuff_level=0.011, log=None, frames=45,
                 name="Hoodie", bending=0.8, mass=0.3):
    """Upper garment shell (hoodie, jacket body and sleeves): the shoulders as an offset of the body, the body
    hanging from the chest, sleeves as lofts; gathered at the hem into the waistband and at the wrists into the
    cuffs; draped with extra length near the cuffs and the hem (the sleeves bunch, the body blouses)."""
    torso = torso_hang(B, hem_top, 1.40, hang)
    sl = {s: sleeve_loft(B, M, s, sleeve, cuff, cuff_level) for s in "lr"}

    def f(p):
        d = sdf.smin(BF(p) - ease, torso(p), 0.06)
        d = sdf.smin(d, sl["l"](p), 0.04)
        return sdf.smin(d, sl["r"](p), 0.04)
    cuts = [((0, 0, hem_top), (0, 0, -1)), ((0, 0, neck), (0, 0, 1), 0.17)]
    for s in "lr":
        p, n = cuff_plane(M, s, cuff)
        cuts.append((p, n, 0.16))
    ob = cloth.garment_mesh(name, f, (-0.64, -0.32, hem_top - 0.05), (0.64, 0.28, neck + 0.05), h, cuts=cuts, col=col)
    L = loops_by_cut(ob, cuts)
    gather_ring(ob, L[0], BF, band_level + 0.003)
    for i in (2, 3):
        gather_ring(ob, L[i], BF, cuff_level + 0.003)
    co = verts(ob)
    pin = np.zeros(len(co))
    for i in (0, 1, 2, 3):
        pin[L[i]] = 1.0
    g = np.maximum(grow_weights(co, [M.wrist[s] - M.fore[s] * 0.13 for s in "lr"], 0.2),
                   0.8 * grow_weights(co, [(x, y, hem_top + 0.03) for x, y in ((0, -0.12), (0, 0.11), (0.16, 0), (-0.16, 0))], 0.2))
    g = np.maximum(g, 0.25) * (1 - pin)
    cloth.drape(ob, colliders, frames=frames, pin=pin, shrink=g, shrink_min=grow, log=log, bending=bending, mass=mass)
    return ob, L


def bands_for(B, M, BF, col, hem_top=0.925, band_bot=0.86, cuff=0.065, band_level=0.016, cuff_level=0.011):
    """Rib waistband and the two rib cuffs."""
    out = {}
    out["waistband"] = band("Waistband", BF, band_level, [((0, 0, hem_top + 0.004), (0, 0, 1)), ((0, 0, band_bot), (0, 0, -1))],
                            0.0075, col, (-0.32, -0.3, band_bot - 0.03), (0.32, 0.3, hem_top + 0.03))
    for s in "lr":
        p, n = cuff_plane(M, s, cuff + 0.004)
        p2, n2 = cuff_plane(M, s, -0.014)
        c = M.wrist[s]
        out["cuff_" + s] = band("Cuff_" + s, BF, cuff_level, [(p, -n, 0.15), (p2, n2, 0.15)], 0.0055, col, c - 0.13, c + 0.13)
    return out


def snap_to_polyline(P, ring):
    """Closest points of the closed polyline `ring` (m, 3) to the points P (n, 3)."""
    A = ring
    Bq = np.roll(ring, -1, axis=0)
    AB = Bq - A
    L2 = np.maximum(np.einsum("ij,ij->i", AB, AB), 1e-12)
    out = np.empty_like(P)
    for i, p in enumerate(P):
        t = np.clip(((p - A) * AB).sum(axis=1) / L2, 0, 1)
        Q = A + AB * t[:, None]
        k = np.argmin(np.linalg.norm(Q - p, axis=1))
        out[i] = Q[k]
    return out
