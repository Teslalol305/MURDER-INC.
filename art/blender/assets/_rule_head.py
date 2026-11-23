"""The head of SK_Rule, review round 1 (used by _rule_body): the generated bust made into a head that holds up close.

Geometry (on the placed bust, before decimation unless noted)
  neck_join      one tilted plane under the jaw: the bust is bisected cleanly above it, the body keeps its own neck
                 below it (continuous texture down to the shirt collar) and that neck is reshaped radially to meet
                 the bust's ring, the bust sliding 2 mm down inside it (no torn edge, no crack, no pinched fold)
  warp_face      proportions against the photo: lower third 5 % shorter, zygomatic arch 5 % wider, the brow ridge
                 lower and heavier, deeper nasolabial folds, the mouth corners down
  ears           the generated ears were small and set low: scaled up about their root and raised
  eyes           (after decimation) the eye regions are subdivided and the skin inside a narrower, hooded
                 aperture is pushed back into a socket behind real eyeballs; heavier upper lids; eyeballs with an
                 iris recessed under a transparent cornea, a tear line along both lid margins, a caruncle
Textures (per texel on the bust's own UV atlas, 4K, mi/texel.bake_maps)
  head_textures  skin graded to the shared target (_rule_tex.SKIN_TARGET), cleaned by frequency separation
                 (upscaler blotches, red speckles, bright specks), the old painted eyes repainted as lids with a
                 lash line, a thicker, lower moustache and stubble shadow, the shirt's red bleed on the neck
                 cloned out, the bandana re-printed with a tiling bandana pattern by 3D projection; a normal map
                 (generated relief + pores, micro-wrinkles, stubble, cloth weave and compression folds) and an ORM
                 (oily T-zone, drier cheeks, lips, cloth)

Landmarks (LM) were read off orthographic renders of the placed bust (art/out, git-ignored), world metres. They hold
for the generated head in art/out/gen/rule/ and _rule_body's placement; check_landmarks() warns when those change.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from mi import gen3d, geo, paths, scene

GEN = os.path.join(paths.out, "gen", "rule")
DERIVED = os.path.join(GEN, "derived")          # processed maps of the likeness: git-ignored like their sources

LM = dict(
    zb=1.5607,                 # the body's neckline (swap_head)
    mid_x=-0.0048,             # face midline
    eye_z=1.6925,              # iris centres
    eye_dx=0.0390,             # half the distance between the iris centres
    inner_dx=0.0220,           # inner canthus from the midline (new aperture)
    outer_dx=0.0540,           # outer canthus
    canthus_z=(1.6905, 1.6920),  # inner, outer canthus height (new)
    lid_up=0.0048,             # upper lid rise above the canthal line at mid-eye (new; was ~6.3 mm)
    lid_lo=0.0027,             # lower lid drop below it
    brow_z=1.7135,
    subnasale_z=1.6430,
    lip_top_z=1.6215,
    stomion_z=1.6110,
    corner_dx=0.0300,          # mouth corners from the midline
    menton_z=1.5770,
    alar_dx=0.0240, alar_z=1.6480,
    ear=dict(x=0.0835, y=-0.0270, z=1.6580),   # ear centre (|x| about the midline)
)


def check_landmarks(zb, log=print):
    if abs(zb - LM["zb"]) > 0.004:
        log("  WARNING: neckline %.4f differs from the landmark sheet's %.4f: re-read the landmarks" % (zb, LM["zb"]))


def _smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------------------------------------ neck


def neck_plane(zb, hy):
    """Tilted cut plane under the jaw: z = z0 + (y - y0) * slope, 1.6 cm under the neckline at the throat, rising
    to 2.5 cm over it at the nape (above the shirt's collar all round, below the bust's jaw all round)."""
    y0, z0, slope = hy - 0.020, zb - 0.016, 0.33
    no = Vector((0.0, -slope, 1.0)).normalized()
    return (Vector((0.0, y0, z0)), no, lambda y: z0 + (y - y0) * slope)


def _ring(points, cx, cy, bins=72):
    """Radius about (cx, cy) per angle bin (median), empty bins filled round the circle, smoothed."""
    phi = np.arctan2(points[:, 1] - cy, points[:, 0] - cx)
    r = np.hypot(points[:, 0] - cx, points[:, 1] - cy)
    k = ((phi + np.pi) / (2 * np.pi) * bins).astype(int) % bins
    out = np.full(bins, np.nan)
    for i in range(bins):
        m = k == i
        if m.any():
            out[i] = np.median(r[m])
    ok = ~np.isnan(out)
    if ok.sum() < 3:
        return None
    idx = np.arange(bins)
    out = np.interp(idx, idx[ok], out[ok], period=bins)
    for _ in range(2):
        out = (np.roll(out, 1) + 2 * out + np.roll(out, -1)) / 4
    return out


def _ring_at(ring, phi):
    bins = len(ring)
    f = (phi + np.pi) / (2 * np.pi) * bins - 0.5
    i0 = np.floor(f).astype(int)
    t = f - i0
    return ring[i0 % bins] * (1 - t) + ring[(i0 + 1) % bins] * t


def neck_join(body, head, red_faces, zb, hx, hy, log=print):
    """See the module notes. red_faces: (n_faces,) bool of the body (shirt). The body must still have its own
    neck (swap_head(..., keep_neck=True))."""
    co_p, no, zf = neck_plane(zb, hy)
    # 1. the bust: bisect, keep the part above the plane
    bm = bmesh.new()
    bm.from_mesh(head.data)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6, plane_co=co_p, plane_no=no, clear_inner=True)
    bm.to_mesh(head.data)
    bm.free()
    head.data.update()
    from assets import _rule_body as B
    B._largest_part(head)
    hco = gen3d.verts(head)
    sd = hco[:, 2] - zf(hco[:, 1])
    ring_v = np.nonzero((np.abs(sd) < 0.0008) & (np.hypot(hco[:, 0] - hx, hco[:, 1] - hy) < 0.11))[0]
    ring = _ring(hco[ring_v], hx, hy)
    log("  neck: bust cut on the plane (%d ring vertices, radius %.3f..%.3f m)" % (len(ring_v), ring.min(), ring.max()))
    # 2. the body: faces of the neck region above the plane go, its neck below stays
    cb, _nb, _ab = gen3d.face_arrays(body)
    rb = np.hypot(cb[:, 0] - hx, cb[:, 1] - hy)
    region = (rb < 0.115) & (cb[:, 2] > zb - 0.08) & (cb[:, 2] < zb + 0.10)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bm.faces.ensure_lookup_table()
    sel = [bm.faces[i] for i in np.nonzero(region)[0]]
    verts = {v for f in sel for v in f.verts}
    edges = {e for f in sel for e in f.edges}
    bmesh.ops.bisect_plane(bm, geom=list(verts) + list(edges) + sel, dist=1e-6, plane_co=co_p, plane_no=no,
                           clear_outer=False)
    bm.to_mesh(body.data)
    bm.free()
    body.data.update()
    # the shirt flags follow the faces through the bisect by sampling again (faces split: recompute by colour)
    cb, _nb, _ab = gen3d.face_arrays(body)
    rb = np.hypot(cb[:, 0] - hx, cb[:, 1] - hy)
    above = (cb[:, 2] > zf(cb[:, 1]) + 1e-5) & (rb < 0.115) & (cb[:, 2] < zb + 0.12)
    gen3d.delete_faces(body, above)
    log("  neck: body cut on the plane, %d faces above it removed" % above.sum())
    PLANE[:] = [zf]
    return ring, (co_p, no, zf)


def reshape_body_neck(body, red, ring, plane, hx, hy, log=print):
    """Move the body's neck (vertices of skin faces, radius < 0.10 about the axis, between its collar and the
    plane) radially so that it meets the bust's ring 0.3 mm outside it, blended up from the collar."""
    _co_p, _no, zf = plane
    co = gen3d.verts(body)
    me = body.data
    on_red = np.zeros(len(co), dtype=bool)
    for p in me.polygons:
        if red[p.index]:
            on_red[list(p.vertices)] = True
    phi = np.arctan2(co[:, 1] - hy, co[:, 0] - hx)
    r = np.hypot(co[:, 0] - hx, co[:, 1] - hy)
    sd = co[:, 2] - zf(co[:, 1])
    zone = (r < 0.10) & (sd > -0.06) & (sd <= 1e-4)
    # collar height per angle: the highest shirt vertex in the zone
    bins = 72
    k = ((phi + np.pi) / (2 * np.pi) * bins).astype(int) % bins
    top_red = np.full(bins, np.nan)
    for i in range(bins):
        m = zone & on_red & (k == i)
        if m.any():
            top_red[i] = sd[m].max()
    ok = ~np.isnan(top_red)
    idx = np.arange(bins)
    top_red = np.interp(idx, idx[ok], top_red[ok], period=bins) if ok.any() else np.full(bins, -0.03)
    top_red = np.minimum(top_red, -0.008)
    lo = top_red[k]
    t = np.clip((sd - lo) / np.maximum(-lo, 1e-4), 0, 1)
    w = t * t * (3 - 2 * t)
    w[~zone | on_red] = 0
    rt = _ring_at(ring, phi) + 0.0003
    rn = r + w * (rt - r)
    co[:, 0] = hx + (co[:, 0] - hx) * np.where(r > 1e-6, rn / np.maximum(r, 1e-6), 1)
    co[:, 1] = hy + (co[:, 1] - hy) * np.where(r > 1e-6, rn / np.maximum(r, 1e-6), 1)
    gen3d.set_verts(body, co)
    log("  neck: body neck reshaped to the bust's ring (%d vertices moved, max %.1f mm)"
        % ((w > 0.01).sum(), 1000 * np.abs(w * (rt - r)).max()))


def tuck_bust(head, plane, hx, hy, log=print):
    """The bust's lowest ring slides 2 mm down and 0.5 mm in, inside the body's neck: no crack at the join.
    Where the bust's own rim ends above the plane (its removed shirt collar at the nape), its bottom strip is
    first stretched down onto the plane."""
    _co_p, _no, zf = plane
    co = gen3d.verts(head)
    sd = co[:, 2] - zf(co[:, 1])
    bm = bmesh.new()
    bm.from_mesh(head.data)
    bnd = np.array(sorted({v.index for e in bm.edges if len(e.link_faces) == 1 for v in e.verts}), dtype=np.int64)
    bm.free()
    r = np.hypot(co[:, 0] - hx, co[:, 1] - hy)
    rim = bnd[(sd[bnd] < 0.035) & (r[bnd] < 0.115)]
    if len(rim):
        bins = 72
        phi = np.arctan2(co[:, 1] - hy, co[:, 0] - hx)
        k = ((phi + np.pi) / (2 * np.pi) * bins).astype(int) % bins
        low = np.full(bins, np.nan)
        for i in range(bins):
            m = k[rim] == i
            if m.any():
                low[i] = sd[rim][m].min()
        ok = ~np.isnan(low)
        idx = np.arange(bins)
        low = np.interp(idx, idx[ok], low[ok], period=bins)
        low = np.maximum.reduce([low, np.roll(low, 1), np.roll(low, -1)])
        gap = np.maximum(low, 0.0)[k]
        w = _smooth(gap + 0.020, gap, sd) * (r < 0.115) * (gap > 0)
        co[:, 2] -= gap * w
        log("  neck: bust rim stretched down onto the plane where it ended above it (max %.1f mm)" % (1000 * gap.max()))
        sd = co[:, 2] - zf(co[:, 1])
    w = _smooth(0.006, 0.0, sd)
    r = np.hypot(co[:, 0] - hx, co[:, 1] - hy)
    s = np.where(r > 1e-6, (r - 0.0005 * w) / np.maximum(r, 1e-6), 1)
    co[:, 0] = hx + (co[:, 0] - hx) * s
    co[:, 1] = hy + (co[:, 1] - hy) * s
    co[:, 2] -= 0.002 * w
    gen3d.set_verts(head, co)


def clean_neck_flaps(head, zb, hx, hy, log=print):
    """Torn flaps of the bust's own (removed) shirt collar behind the ears: vertices of the neck band that stand
    off a heavily smoothed copy of the surface by more than 3 mm are pulled onto it."""
    co = gen3d.verts(head)
    me = head.data
    zone = (co[:, 2] < zb + 0.075) & (co[:, 1] > -0.010) & (np.hypot(co[:, 0] - hx, co[:, 1] - hy) < 0.12)
    ev = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", ev)
    ev = ev.reshape(-1, 2)
    sm = co.copy()
    deg = np.bincount(ev.ravel(), minlength=len(co)).astype(np.float64)
    for _ in range(30):
        acc = np.zeros_like(sm)
        np.add.at(acc, ev[:, 0], sm[ev[:, 1]])
        np.add.at(acc, ev[:, 1], sm[ev[:, 0]])
        nb = acc / np.maximum(deg, 1)[:, None]
        sm = np.where(zone[:, None], 0.5 * sm + 0.5 * nb, sm)
    off = np.linalg.norm(co - sm, axis=1)
    w = _smooth(0.002, 0.005, off) * zone
    co = co + (sm - co) * w[:, None]
    gen3d.set_verts(head, co)
    log("  neck: %d flap vertices pulled onto the neck (max stand-off %.1f mm)" % ((w > 0.5).sum(), 1000 * off[zone].max()))


# ------------------------------------------------------------------------------------------------ proportions


def warp_face(head, log=print):
    """Proportions against the photo (review round 1), smooth fields on the vertices, metres."""
    co0 = gen3d.verts(head)
    co = warp_points(co0)
    gen3d.set_verts(head, co)
    log("  face: lower third lifted %.1f mm at the chin, zygomatic +5 %%, brow +2 mm forward, folds, corners"
        % (1000 * (co[:, 2] - co0[:, 2]).max()))


def warp_points(co):
    """The proportion warp as a function of points (n, 3): used on the bust and on the landmarks."""
    co = np.array(co, dtype=np.float64, copy=True)
    x = co[:, 0] - LM["mid_x"]
    y, z = co[:, 1], co[:, 2]
    front = _smooth(0.015, -0.035, y)                  # the face, not the back of the head (y < -0.035 full)
    # 1. lower third 5 % shorter: everything below the subnasale moves up by 5 % of its distance below it,
    #    held at the chin's 3.3 mm under the chin and faded out down the neck
    sn, me = LM["subnasale_z"], LM["menton_z"]
    lift = 0.05 * np.clip(sn - z, 0, sn - me) * _smooth(me - 0.035, me - 0.005, z)
    lift *= _smooth(0.03, -0.01, y)                     # the jaw and chin, not the nape
    co[:, 2] += lift
    # 2. zygomatic arch 5 % wider: lateral cheek at cheekbone height
    zy = np.exp(-((z - 1.672) / 0.016) ** 2) * _smooth(0.020, 0.045, np.abs(x)) * _smooth(0.02, -0.02, y)
    co[:, 0] += x * 0.05 * zy
    # 3. brow ridge lower and heavier: forward 2 mm and down 1.2 mm over the brows
    br = np.exp(-((z - LM["brow_z"]) / 0.0075) ** 2) * _smooth(0.062, 0.035, np.abs(x)) * front
    co[:, 1] -= 0.0020 * br
    co[:, 2] -= 0.0012 * br
    # 4. nasolabial folds: a groove from the nose wing to past the mouth corner, a fuller cheek beside it
    for s in (-1, 1):
        a = np.array([s * (LM["alar_dx"] + 0.004), LM["alar_z"] - 0.002])
        b = np.array([s * (LM["corner_dx"] + 0.011), LM["stomion_z"] - 0.006])
        ab = b - a
        q = np.stack([x, z], 1) - a
        t = np.clip(q @ ab / (ab @ ab), 0, 1)
        d = np.linalg.norm(q - t[:, None] * ab, axis=1)
        side = np.sign((q[:, 0] * ab[1] - q[:, 1] * ab[0]) * s)       # + toward the cheek
        env = np.sin(np.pi * t) ** 0.6 * front * (np.sign(x) == s)
        co[:, 1] += 0.0012 * np.exp(-(d / 0.0024) ** 2) * env
        co[:, 1] -= 0.0007 * np.exp(-((d - 0.006) / 0.004) ** 2) * env * (side > 0)
    # 5. mouth corners down (his downturned mouth)
    for s in (-1, 1):
        dc = np.hypot(x - s * LM["corner_dx"], z - LM["stomion_z"])
        co[:, 2] -= 0.0014 * np.exp(-(dc / 0.0055) ** 2) * front
    return co


def lm_after_warp(x, z, y=-0.13):
    """A frontal landmark (x about the midline, z) carried through warp_points."""
    q = warp_points(np.array([[LM["mid_x"] + x, y, z]]))[0]
    return q[0] - LM["mid_x"], q[2]


def ears(head, log=print):
    """The ears: 1.35 x about their root (toward the head), raised 6 mm, so they span about brow to nose base."""
    co = gen3d.verts(head)
    e = LM["ear"]
    n = 0
    for s in (-1, 1):
        c = np.array([LM["mid_x"] + s * e["x"], e["y"], e["z"]])
        root = c - np.array([s * 0.010, 0, 0])
        q = (co - c) / np.array([0.020, 0.026, 0.032])
        w = _smooth(1.0, 0.55, np.linalg.norm(q, axis=1)) * (np.sign(co[:, 0] - LM["mid_x"]) == s)
        w *= _smooth(0.060, 0.072, np.abs(co[:, 0] - LM["mid_x"]))   # only what stands off the side of the head
        co += w[:, None] * ((co - root) * 0.35 + np.array([0, 0, 0.006]))
        n += (w > 0.5).sum()
    gen3d.set_verts(head, co)
    log("  ears: %d vertices scaled up about the root and raised" % n)


# ------------------------------------------------------------------------------------------------ eyes


R_EYE = 0.0118
NECK_MEDIAN = list(map(float, (0.150, 0.072, 0.035)))
PLANE = []                                                # the neck join's height function z(y) (neck_join)   # the head's neck just above the join (set by head_textures)


def eye_centres():
    return [np.array([LM["mid_x"] + s * LM["eye_dx"], LM["eye_z"]]) for s in (-1, 1)]


def aperture(x, z, s):
    """Signed distance (m, approximate, negative inside) to the new lid aperture of eye s (-1 his right, +1 his
    left) in the frontal (x, z) plane, and u along the fissure (0 inner canthus, 1 outer)."""
    xm = LM["mid_x"]
    xi, xo = xm + s * LM["inner_dx"], xm + s * LM["outer_dx"]
    W = abs(xo - xi)
    u = (x - xi) / (xo - xi)
    zi, zo = LM["canthus_z"]
    base = zi + (zo - zi) * np.clip(u, 0, 1)
    uc = np.clip(u, 0, 1)
    up = base + LM["lid_up"] * np.clip(np.sin(np.pi * uc), 0, 1) ** 0.75 * (1 + 0.15 * (0.45 - uc))
    lo = base - LM["lid_lo"] * np.clip(np.sin(np.pi * uc), 0, 1) ** 1.1
    d = np.maximum.reduce([z - up, lo - z, -u * W * 0.35, (u - 1) * W * 0.35])
    return d, u, up, lo


def eye_geometry(head, col, log=print):
    """After decimation: subdivide round each eye, push the skin inside the aperture into a socket behind the
    eyeball, roll the lid margins onto it, heavier upper lids. Returns the eyeball centres (world)."""
    co = gen3d.verts(head)
    cen = []
    # eyeball depth: the front surface at each iris centre (ray along +y)
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(head.data)
    tree = BVHTree.FromBMesh(bm)
    for (ex, ez) in eye_centres():
        hit = tree.ray_cast(Vector((ex, -0.5, ez)), Vector((0, 1, 0)))
        ys = hit[0].y if hit[0] is not None else float(co[np.argmin(np.hypot(co[:, 0] - ex, co[:, 2] - ez)), 1])
        cy = ys - 0.0004 + R_EYE + 0.0020                  # cornea apex 0.4 mm in front of the painted surface
        cen.append(np.array([ex, cy, ez]))
    # subdivide the faces round the eyes twice (about 0.8 mm edges)
    for it in range(2):
        bm.faces.ensure_lookup_table()
        fc = np.array([f.calc_center_median() for f in bm.faces])
        sel = np.zeros(len(fc), dtype=bool)
        for c in cen:
            sel |= (np.abs(fc[:, 0] - c[0]) < 0.026) & (np.abs(fc[:, 2] - c[2]) < 0.016) & (fc[:, 1] < c[1] - 0.002)
        edges = {e for i in np.nonzero(sel)[0] for e in bm.faces[i].edges}
        bmesh.ops.subdivide_edges(bm, edges=list(edges), cuts=1, use_grid_fill=True, smooth=0.0)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.to_mesh(head.data)
    bm.free()
    head.data.update()
    co = gen3d.verts(head)
    moved = 0
    for s, c in zip((-1, 1), cen):
        x, y, z = co[:, 0], co[:, 1], co[:, 2]
        d, u, up, lo = aperture(x, z, s)
        near = (np.abs(x - c[0]) < 0.028) & (np.abs(z - c[2]) < 0.018) & (y < c[1] - 0.003)
        rho2 = (x - c[0]) ** 2 + (z - c[2]) ** 2
        inside_sphere = rho2 < (R_EYE * 0.995) ** 2
        ysph = c[1] - np.sqrt(np.maximum(R_EYE ** 2 - rho2, 0))          # the globe's front surface
        # inside the aperture: behind the globe (or 3 mm back past its silhouette at the canthi)
        tgt_in = np.where(inside_sphere, ysph + 0.0016, y + 0.0030)
        w_in = _smooth(0.0, -0.0010, d) * near
        # lid margins: resting on the globe, 0.35 mm in front of it
        tgt_m = np.where(inside_sphere, np.minimum(y, ysph - 0.00035), y)
        w_m = _smooth(0.0018, 0.0002, d) * (d >= 0) * near
        # heavier upper lid: the skin 1-6 mm above the aperture comes forward and down (a hooded fold)
        above = (z > up) & near
        hood = np.exp(-((d - 0.0032) / 0.0022) ** 2) * above * _smooth(-0.05, 0.25, u) * _smooth(1.05, 0.7, u)
        ny = y.copy()
        ny = np.where(w_in > 0, y + (tgt_in - y) * w_in, ny)
        ny = np.where(w_m > 0, ny + (tgt_m - ny) * w_m, ny)
        ny -= 0.0009 * hood
        nz = z - 0.0007 * hood
        moved += int(((w_in > 0.01) | (w_m > 0.01) | (hood > 0.01)).sum())
        co[:, 1] = np.where(near, ny, y)
        co[:, 2] = np.where(near, nz, z)
    gen3d.set_verts(head, co)
    log("  eyes: sockets and lids shaped (%d vertices), globes at %s" % (moved, [tuple(np.round(c, 4)) for c in cen]))
    return cen


def _eye_texture(path, res=1024):
    """Iris (near-black brown, radial fibres, a darker collarette and limbal ring), pupil, sclera (warm off-white,
    redder and greyer toward the corners, faint vessels), and a caruncle pink in the corner (0..0.06)."""
    from mi import texel as T
    h = np.linspace(-1, 1, res)
    X, Y = np.meshgrid(h, -h)
    rr = np.hypot(X, Y)                   # 1 = the globe's silhouette (u, v from the front projection)
    th = np.arctan2(Y, X)
    P = np.stack([X.ravel() * 6, Y.ravel() * 6, np.zeros(X.size)], 1)
    n1 = T.fbm(P, 3.0, 3, seed=5).reshape(res, res)
    ri = 6.0 / 11.8                       # iris radius in the projection
    rp = 1.9 / 11.8
    sclera = np.array([0.62, 0.55, 0.48]) * (1 - 0.10 * _smooth(0.55, 1.0, np.abs(X)))[..., None]
    sclera = sclera * (1 + 0.04 * n1[..., None])
    vessels = T.ridged(np.stack([X.ravel() * 3, Y.ravel() * 3, np.zeros(X.size)], 1), 4.0, seed=9).reshape(res, res)
    sclera[..., 1:] *= (1 - 0.35 * vessels * _smooth(0.55, 0.95, np.abs(X)))[..., None]
    sclera[..., 0] *= 1 + 0.15 * _smooth(0.6, 1.0, np.abs(X))
    fib = 0.5 + 0.5 * np.sin(th * 90 + 6 * n1) * (0.6 + 0.4 * np.cos(th * 23 + 3 * n1))
    iris = np.array([0.050, 0.026, 0.014])[None, None] * (0.75 + 0.5 * fib)[..., None]
    iris *= (1 - 0.45 * np.exp(-((rr - ri * 0.45) / (ri * 0.08)) ** 2))[..., None]       # collarette
    iris *= (1 - 0.7 * _smooth(ri * 0.82, ri * 1.0, rr))[..., None]                         # limbal ring
    out = np.where((rr < ri)[..., None], iris, sclera)
    edge = _smooth(ri * 0.98, ri * 1.08, rr)[..., None]
    out = iris * (1 - edge) + out * edge if False else np.where((rr < ri * 1.08)[..., None], iris * (1 - edge) + sclera * edge, out)
    out = np.where((rr < rp)[..., None], np.array([0.006, 0.005, 0.005]), out)
    # caruncle pink patch in a corner of the image (u, v < 0.06)
    out[-int(res * 0.06):, :int(res * 0.06)] = np.array([0.42, 0.16, 0.13])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    gen3d.save_texture(np.clip(out, 0, 1).astype(np.float32), path, srgb=True)
    return path


def eye_materials():
    from mi import mat as _mat
    p = _eye_texture(os.path.join(DERIVED, "T_Rule_Eye_BC.png"))
    eye = bpy.data.materials.get("M_Rule_Eye") or bpy.data.materials.new("M_Rule_Eye")
    nt = eye.node_tree
    b = nt.nodes.get("Principled BSDF")
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(p, check_existing=True)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.10
    b.inputs["Subsurface Weight"].default_value = 0.0
    wet = bpy.data.materials.get("M_Rule_EyeWet") or _mat.flat("M_Rule_EyeWet", (0.02, 0.02, 0.02), 0.02, 0.0)
    bw = wet.node_tree.nodes.get("Principled BSDF")
    bw.inputs["Alpha"].default_value = 0.12
    bw.inputs["Roughness"].default_value = 0.02
    return eye, wet


def eye_parts(cen, col, log=print):
    """Eyeballs (iris recessed 0.4 mm), corneas, tear lines, caruncles. Returns the objects (joined by side)."""
    eye, wet = eye_materials()
    out = []
    for s, c in zip((-1, 1), cen):
        # globe: UV sphere, pole toward -y; UVs = the front projection of the unit globe
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=32, radius=R_EYE)
        ob = bpy.data.objects.new("Eye_%s" % ("R" if s < 0 else "L"), bpy.data.meshes.new("Eye"))
        bm.to_mesh(ob.data)
        bm.free()
        co = gen3d.verts(ob)
        co = co[:, [0, 2, 1]] * [1, -1, 1]                  # sphere's +z pole -> -y (front)
        rho = np.hypot(co[:, 0], co[:, 2])
        lim = R_EYE * math.sin(math.radians(30.6))
        front = co[:, 1] < 0
        flat = front & (rho < lim)                          # the iris: a shallow cone set back under the cornea
        depth = -R_EYE * math.cos(math.radians(30.6)) + 0.0004 * (1 - rho / lim)
        co[flat, 1] = np.maximum(co[flat, 1], depth[flat])
        gen3d.set_verts(ob, co)
        me = ob.data
        uvl = me.uv_layers.new(name="UVMap")
        lv = np.empty(len(me.loops), dtype=np.int64)
        me.loops.foreach_get("vertex_index", lv)
        uv = np.stack([0.5 + co[lv, 0] / (2 * R_EYE) * s * -1 * -1, 0.5 + co[lv, 2] / (2 * R_EYE)], 1)
        uv[:, 0] = 0.5 + co[lv, 0] / (2 * R_EYE)
        uvl.data.foreach_set("uv", uv.ravel())
        me.materials.append(eye)
        for p in me.polygons:
            p.use_smooth = True
        gen3d.set_verts(ob, co + c)
        col.objects.link(ob)
        parts = [ob]
        # cornea: cap of a 6.77 mm sphere through the limbus, apex 2 mm before the globe
        rc, cc = 0.00677, 0.00703
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=rc)
        cor = bpy.data.objects.new("Cornea", bpy.data.meshes.new("Cornea"))
        bm.to_mesh(cor.data)
        bm.free()
        cco = gen3d.verts(cor)[:, [0, 2, 1]] * [1, -1, 1]
        cco[:, 1] -= cc
        gen3d.set_verts(cor, cco)
        gen3d.delete_faces(cor, np.array([p.center.y > -R_EYE * math.cos(math.radians(30.6)) + 0.0002 for p in cor.data.polygons]))
        cor.data.uv_layers.new(name="UVMap")
        cor.data.materials.append(wet)
        for p in cor.data.polygons:
            p.use_smooth = True
        gen3d.set_verts(cor, gen3d.verts(cor) + c)
        col.objects.link(cor)
        parts.append(cor)
        # tear lines along both lid margins: a strip from 0.4 mm inside the aperture onto the margin
        uu = np.linspace(0.03, 0.97, 40)
        xi = LM["mid_x"] + s * LM["inner_dx"]
        xo = LM["mid_x"] + s * LM["outer_dx"]
        xs = xi + (xo - xi) * uu
        _d, _u, up, lo = aperture(xs, np.full_like(xs, c[2]), s)
        verts, faces = [], []
        for lid, sgn in ((up, 1), (lo, -1)):
            base = len(verts)
            for k in range(len(uu)):
                for off in (-0.0004, 0.0006):
                    zz = lid[k] + sgn * off
                    rho2 = (xs[k] - c[0]) ** 2 + (zz - c[2]) ** 2
                    yy = c[1] - math.sqrt(max(R_EYE ** 2 - rho2, 0.0)) - 0.00025 - (0.00012 if off > 0 else 0)
                    verts.append((xs[k], yy, zz))
            for k in range(len(uu) - 1):
                a = base + 2 * k
                faces.append((a, a + 2, a + 3, a + 1))
        tl = geo.from_arrays("TearLine", np.array(verts), faces, col)
        tl.data.uv_layers.new(name="UVMap") if not tl.data.uv_layers else None
        tl.data.materials.clear()
        tl.data.materials.append(wet)
        parts.append(tl)
        # caruncle: a small pink fold at the inner canthus
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0)
        car = bpy.data.objects.new("Caruncle", bpy.data.meshes.new("Caruncle"))
        bm.to_mesh(car.data)
        bm.free()
        cco = gen3d.verts(car) * [0.0014, 0.0016, 0.0022]
        zc = LM["canthus_z"][0]
        xc = xi + s * 0.0016
        rho2 = (xc - c[0]) ** 2 + (zc - c[2]) ** 2
        yc = c[1] - math.sqrt(max(R_EYE ** 2 - rho2, 0.0)) if rho2 < R_EYE ** 2 else c[1] - 0.002
        gen3d.set_verts(car, cco + [xc, yc - 0.0002, zc])
        cl = car.data.uv_layers.new(name="UVMap")
        cl.data.foreach_set("uv", np.tile([0.02, 0.02], len(car.data.loops)))
        car.data.materials.append(eye)
        for p in car.data.polygons:
            p.use_smooth = True
        col.objects.link(car)
        parts.append(car)
        out.append(geo.join(parts, "Eyes_%s" % ("R" if s < 0 else "L"), col))
    log("  eyes: globes (iris under a cornea), tear lines and caruncles added")
    return out


# ------------------------------------------------------------------------------------------------ textures


def _box(a, r):
    """Box blur of radius r (texels) along both image axes with running sums, edges clamped."""
    if r < 1:
        return a
    out = a.astype(np.float32)
    for ax in (0, 1):
        pad = [(0, 0)] * out.ndim
        pad[ax] = (r + 1, r)
        p = np.pad(out, pad, mode="edge")
        c = np.cumsum(p, axis=ax, dtype=np.float64)
        n = out.shape[ax]
        hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=ax)
        lo = np.take(c, np.arange(0, n), axis=ax)
        out = ((hi - lo) / (2 * r + 1)).astype(np.float32)
    return out


def masked_blur(img, mask, r, passes=3):
    """Normalised convolution: blur of img over the texels of mask only (no bleed from outside it)."""
    m = mask.astype(np.float32)
    a = img * (m[..., None] if img.ndim == 3 else m)
    for _ in range(passes):
        a = _box(a, r)
        m = _box(m, r)
    d = np.maximum(m, 1e-4)
    return a / (d[..., None] if img.ndim == 3 else d), m


def low_pass_3d(P, img, sel, voxel=0.004, passes=2):
    """Low-pass of img (H, W, 3) over the texels of sel, averaged in 3D (voxels of `voxel` metres, smoothed
    over their neighbours `passes` times, read back trilinearly): unlike a blur in UV space it never mixes
    atlas islands that are neighbours in the texture but not on the head. Returns (H, W, 3) (zeros off sel's
    support)."""
    pts = P[sel].astype(np.float64)
    lo = pts.min(0) - 2 * voxel
    dims = np.ceil((pts.max(0) + 2 * voxel - lo) / voxel).astype(int) + 1
    acc = np.zeros((*dims, 3))
    cnt = np.zeros(dims)
    ijk = np.floor((pts - lo) / voxel).astype(int)
    np.add.at(acc, (ijk[:, 0], ijk[:, 1], ijk[:, 2]), img[sel])
    np.add.at(cnt, (ijk[:, 0], ijk[:, 1], ijk[:, 2]), 1)
    for _ in range(passes):
        a2, c2 = acc.copy(), cnt.copy()
        for ax in range(3):
            for sh in (1, -1):
                a2 += np.roll(acc, sh, axis=ax)
                c2 += np.roll(cnt, sh, axis=ax)
        acc, cnt = a2, c2
    grid = acc / np.maximum(cnt, 1e-6)[..., None]
    have = cnt > 1e-6
    out = np.zeros_like(img)
    m = np.abs(P).sum(-1) < 5.0                       # covered texels (uncovered ones sit at the bake offset)
    q = (P[m].astype(np.float64) - lo) / voxel - 0.5
    i0 = np.clip(np.floor(q).astype(int), 0, dims - 2)
    f = np.clip(q - i0, 0, 1)
    res = np.zeros((len(q), 3))
    wsum = np.zeros(len(q))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                ii, jj, kk = i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz
                ok = have[ii, jj, kk]
                res += (w * ok)[:, None] * grid[ii, jj, kk]
                wsum += w * ok
    out[m] = (res / np.maximum(wsum, 1e-6)[:, None]).astype(np.float32)
    return out


def _load_png(path, size, srgb=True):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if im.size != (size, size):
        im = im.resize((size, size), Image.BICUBIC)
    a = np.asarray(im, dtype=np.float32) / 255.0
    a = np.flipud(a).copy()                             # texel maps have row 0 at the bottom
    from mi import bake as _bake
    return _bake.srgb_decode(a) if srgb else a


def _save_png(a, path, srgb=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # bake.save_png takes row 0 at the bottom, as the texel maps are
    gen3d.save_texture(np.nan_to_num(a, nan=0.5).astype(np.float32), path, srgb=srgb)
    return path


def _lum(c):
    return c @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def _tile_sample(tile, u, v):
    """Bilinear sample of a tiling image (h, w, 3) at (u, v) in tiles (wrapped)."""
    h, w = tile.shape[:2]
    x = (u % 1.0) * w - 0.5
    y = (v % 1.0) * h - 0.5
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    x0 %= w
    y0 %= h
    x1, y1 = (x0 + 1) % w, (y0 + 1) % h
    return (tile[y0, x0] * (1 - fx) * (1 - fy) + tile[y0, x1] * fx * (1 - fy)
            + tile[y1, x0] * (1 - fx) * fy + tile[y1, x1] * fx * fy)


def bandana_tile():
    """The bandana print (a generated seamless swatch, gen_log.json), made tileable by a half-offset cross-fade,
    split into (ink colour (h, w, 3), coverage (h, w)) over the red ground."""
    p = os.path.join(GEN, "bandana_tile.png")
    if not os.path.exists(p):
        return None
    from PIL import Image
    im = Image.open(p).convert("RGB")
    w, h = im.size
    im = im.crop((w // 2, h // 2, w, h))                # the clean quadrant (the swatch's corner is smeared)
    a = np.asarray(im.resize((1024, 1024), Image.LANCZOS), dtype=np.float32) / 255.0
    from mi import bake as _bake
    a = _bake.srgb_decode(a)
    b = np.roll(np.roll(a, 512, 0), 512, 1)
    h = np.linspace(0, 1, 1024)
    wx = np.minimum(h, 1 - h) * 2                        # 0 at the tile's edges, 1 in its middle
    wgt = np.minimum.outer(wx, wx)[..., None]
    wgt = _smooth(0.0, 0.35, wgt)
    t = a * wgt + b * (1 - wgt)
    r, g, bl = t[..., 0], t[..., 1], t[..., 2]
    ground = (r > 2.0 * g) & (r > 2.0 * bl)
    cov = 1.0 - _smooth(0.5, 0.9, (r - np.maximum(g, bl)) / np.maximum(r, 1e-4))
    cov = np.clip(cov, 0, 1)
    cov[ground] *= 0.3
    return t, cov


def head_textures(head, res, warped=True, log=print):
    """BC, N, ORM of M_Rule_Head on the bust's own UV atlas (see the module notes). Writes them to DERIVED and
    returns the material (images embedded on export)."""
    from mi import texel as T
    from assets import _rule_tex as RT
    maps = T.bake_maps(head, res)
    mask = maps["mask"]
    H, W = mask.shape
    P = maps["pos"]
    N = maps["normal"]
    bc = _load_png(os.path.join(GEN, "head_meshy_bc_4k.png"), res)
    gn = _load_png(os.path.join(GEN, "head_meshy_maps", "normal.png"), res, srgb=False)
    log("  head maps baked: coverage %.1f %%" % (100 * mask.mean()))
    r_, g_, b_ = bc[..., 0], bc[..., 1], bc[..., 2]
    lum = _lum(bc)
    red = mask & (r_ > 0.05) & (r_ > 2.2 * g_) & (r_ > 2.2 * b_)
    # the bandana: red, plus its print (whites and blacks) inside red islands, above the hairline
    redb, _m = masked_blur(red.astype(np.float32), mask, 6, 2)
    x = P[..., 0] - LM["mid_x"]
    y, z = P[..., 1], P[..., 2]
    hue_skin = (r_ > g_) & (g_ >= b_ * 0.9) & (r_ < 2.6 * g_) & (lum > 0.008) & (lum < 0.45)
    zband = z > 1.630
    # isolated red specks on the face are bleed, not cloth: red counts only where most of the surface within
    # about 6 mm IN 3D is red (a UV neighbourhood can belong to another part of the head)
    red3 = low_pass_3d(P, np.repeat(red[..., None].astype(np.float32), 3, -1), mask, 0.004, 1)[..., 0]
    bandana = mask & ((red & (red3 > 0.40)) | ((red3 > 0.55) & ~hue_skin & zband) | ((red3 > 0.62) & zband))
    skin = mask & ~bandana
    log("  head texels: bandana %.1f %%, skin %.1f %%" % (100 * bandana.sum() / mask.sum(), 100 * skin.sum() / mask.sum()))
    out = bc.copy()
    # ---- skin: grade to the shared target on the face (front, between the brows and the chin)
    face = skin & (z > 1.58) & (z < 1.72) & (y < -0.07) & (np.abs(x) < 0.05) & hue_skin
    graded, k = RT.grade_skin(bc[skin], face[skin])
    out[skin] = graded
    log("  head skin graded: gains %s" % np.round(k, 3).tolist())
    # ---- frequency separation: low (structure), mid (upscaler blotches: attenuated), high (detail)
    L = low_pass_3d(P, out, skin & ~red, 0.004, 2)
    M, _ = masked_blur(out, skin, 2, 2)
    hair = skin & (_lum(M) < 0.55 * _lum(L))                    # brows, moustache, lashes: keep their mid band
    keep_mid = np.where(hair, 1.0, 0.40)[..., None]
    new = L + keep_mid * (M - L) + (out - M)
    # specks and red speckles: texels far off their neighbourhood go to it
    ratio = new[..., 0] / np.maximum(new[..., 1], 1e-4)
    Lr = L[..., 0] / np.maximum(L[..., 1], 1e-4)
    speck = skin & ((_lum(out) > 1.7 * _lum(L)) | (ratio > 1.35 * Lr) | red)
    new[speck] = L[speck]
    out[skin] = new[skin]
    log("  head skin cleaned: %d speck texels" % speck.sum())
    tgt = RT.SKIN_TARGET
    # ---- the neck below the jaw and behind the ears: the shirt's red bleed cloned out
    neck = skin & ((z < LM["menton_z"] + 0.004) | ((y > -0.045) & (z < 1.645)))
    nr = out[..., 0] / np.maximum(out[..., 1], 1e-4)
    bleed = neck & ((nr > 1.25 * tgt[0] / tgt[1]) | (_lum(out) > 1.8 * _lum(tgt)) | (_lum(out) < 0.35 * _lum(tgt)))
    Pm = P[bleed]
    out[bleed] = tgt * (0.96 + 0.06 * T.fbm(Pm, 1 / 0.02, 3, seed=301))[:, None]
    nb = low_pass_3d(P, out, neck, 0.003, 1)
    out[neck] = 0.5 * out[neck] + 0.5 * nb[neck]
    near_join = neck & (z < LM["menton_z"] - 0.010)
    if near_join.any():
        NECK_MEDIAN[:] = np.median(out[near_join], axis=0).tolist()
    log("  neck: %d red-bleed texels cloned out" % bleed.sum())
    # ---- eyes: the painted eyes become lids; a lash line, a wet lower margin, the hooded crease
    rough = np.full((H, W), 0.47, dtype=np.float32)
    for s, (ex, ez) in zip((-1, 1), eye_centres()):
        zone = mask & (np.abs(P[..., 0] - ex) < 0.030) & (np.abs(z - ez) < 0.020) & (y < -0.08)
        if not zone.any():
            continue
        d, u, up, lo = aperture(P[..., 0][zone], z[zone], s)
        ring = (d > 0.004) & (d < 0.008)
        zz = z[zone]
        lid_up = np.median(out[zone][ring & (zz > ez)], axis=0) if (ring & (zz > ez)).any() else tgt
        lid_lo = np.median(out[zone][ring & (zz < ez)], axis=0) if (ring & (zz < ez)).any() else tgt
        c = out[zone]
        lid = np.where((zz > (up + lo) / 2)[:, None], lid_up[None], lid_lo[None])
        Pz = P[zone]
        nz = (0.94 + 0.08 * T.fbm(Pz, 1 / 0.004, 3, seed=310 + s))[:, None]
        old_eye = (d > 0) & (d < 0.0050) & ((_lum(c) > 1.5 * _lum(lid)) | (_lum(c) < 0.45 * _lum(lid)))
        w = np.where(old_eye, 1.0, _smooth(0.0035, 0.0012, d) * (d > 0))[:, None]
        c = c * (1 - w) + lid * nz * w
        above = zz > up
        lash = above & (d >= 0) & (d < 0.0010)
        strokes = _smooth(0.2, 0.7, T.noise(np.stack([u * 140, d * 2000, u * 0], 1), 1.0, 320 + s))
        c[lash] = c[lash] * (1 - 0.9 * (0.6 + 0.4 * strokes[lash]))[:, None] + np.array([0.010, 0.008, 0.007]) * 0.9
        margin = ~above & (d >= 0) & (d < 0.0007)
        c[margin] = c[margin] * 0.4 + np.array([0.11, 0.045, 0.035]) * 0.6
        crease = above & (d > 0.0026) & (d < 0.0048)
        c[crease] *= (1 - 0.28 * np.exp(-((d[crease] - 0.0036) / 0.0007) ** 2))[:, None]
        sock = d < 0
        c[sock] = np.array([0.025, 0.012, 0.009])
        out[zone] = c
        rr = rough[zone]
        rr[margin | (sock)] = 0.30
        rough[zone] = rr
    # ---- moustache lower and thicker, stubble shadow on the upper lip, chin and jaw
    cx, lip = lm_after_warp(0.0, LM["lip_top_z"])
    _cx, cz = lm_after_warp(LM["corner_dx"], LM["stomion_z"])
    front = skin & (y < -0.06)
    ax = np.abs(x)
    zl = lip - 0.0035 * (ax / LM["corner_dx"]) ** 2              # the upper lip's border, falling to the corners
    hgt = 0.0050 - 0.0012 * (ax / 0.035) ** 2
    m_zone = front & (ax < 0.040) & (z > zl + 0.0002) & (z < zl + hgt) & (z < LM["subnasale_z"] - 0.002)
    m_zone |= front & (ax > LM["corner_dx"] - 0.004) & (ax < LM["corner_dx"] + 0.004) & (z > cz - 0.004) & (z < zl + 0.002)
    Pm = P[m_zone]
    sx = np.sign(x[m_zone])
    along = (-z[m_zone] * 0.9 + sx * x[m_zone] * 0.45) / 0.0035
    across = (x[m_zone] * 0.9 - sx * z[m_zone] * 0.45) / 0.00022
    strand = _smooth(0.35, 0.75, T.noise(np.stack([along, across, Pm[:, 1] * 0], 1), 1.0, 330))
    dens = 0.55 + 0.45 * _smooth(-0.3, 0.4, T.fbm(Pm, 1 / 0.004, 2, seed=331))
    hm = np.clip(0.35 + 0.65 * strand, 0, 1) * dens * 0.92
    out[m_zone] = out[m_zone] * (1 - hm)[:, None] + np.array([0.011, 0.008, 0.007]) * hm[:, None]
    rough[m_zone] = 0.58
    beard = front & (((z < cz - 0.004) & (z > LM["menton_z"] - 0.012) & (ax < 0.045))
                     | ((z > zl) & (z < LM["subnasale_z"]) & (ax < 0.045)))
    dots = _smooth(0.45, 0.75, T.noise(P[beard], 1 / 0.00045, 340)) * (0.6 + 0.4 * T.fbm(P[beard], 1 / 0.01, 2, seed=341))
    shade = 0.10 + 0.45 * dots
    chin = (z[beard] < cz - 0.006) & (np.abs(x[beard]) < 0.012)          # the small chin tuft under the lip
    shade = np.where(chin, np.maximum(shade, 0.35 + 0.4 * dots), shade)
    out[beard] = out[beard] * (1 - shade)[:, None] + np.array([0.014, 0.010, 0.009]) * shade[:, None]
    # ---- roughness: oily T-zone, drier cheeks, lips
    tz = skin & (((ax < 0.030) & (z > LM["brow_z"])) | ((ax < 0.014) & (z > LM["subnasale_z"]) & (z < LM["brow_z"]))
                 | ((ax < 0.020) & (z < cz - 0.004) & (z > LM["menton_z"] - 0.004))) & (y < -0.07)
    cheek = skin & (ax > 0.025) & (ax < 0.06) & (z > cz) & (z < LM["eye_z"] - 0.008) & (y < -0.05)
    lips = skin & (ax < LM["corner_dx"]) & (z < lip) & (z > cz - 0.009) & (y < -0.10)
    rough[skin] = 0.47
    rough[tz] = 0.33
    rough[cheek] = 0.53
    rough[lips] = 0.36
    rough[skin] = masked_blur(rough, skin, 6, 2)[0][skin]
    # ---- the bandana: the generated print (scattered blobs) replaced by a tiling bandana print, projected in 3D
    tile = bandana_tile()
    if bandana.any():
        Pb, Nb = P[bandana], N[bandana]
        base_red = np.array([0.40, 0.010, 0.013], dtype=np.float32)   # deeper, as the photo's
        shade_src = _lum(low_pass_3d(P, out, bandana & red, 0.006, 1)[bandana])
        shade = np.clip(shade_src / max(np.median(shade_src), 1e-4), 0.55, 1.25) ** 0.5
        col = base_red[None] * shade[:, None] * (1 + 0.05 * T.fbm(Pb, 1 / 0.003, 2, seed=350))[:, None]
        if tile is not None:
            tcol, tcov = tile
            S = 0.080                                     # metres per tile (paisleys ~12 mm)
            wts = np.abs(Nb) ** 4
            wts /= wts.sum(1, keepdims=True)
            ink = np.zeros((len(Pb), 3), dtype=np.float32)
            cov = np.zeros(len(Pb), dtype=np.float32)
            for axn, (a, b) in enumerate(((1, 2), (0, 2), (0, 1))):
                u, v = Pb[:, a] / S, Pb[:, b] / S
                cc = _tile_sample(tcol, u, v)
                cv = _tile_sample(tcov[..., None], u, v)[:, 0]
                ink += cc * wts[:, axn:axn + 1]
                cov += cv * wts[:, axn]
            col = col * (1 - cov)[:, None] + ink * shade[:, None] * cov[:, None]
        out[bandana] = col
        rough[bandana] = 0.80
    # ---- normal: the generated relief plus pores, micro-wrinkles, stubble, weave and compression folds
    h = np.zeros((H, W), dtype=np.float32)
    ps = P[skin]
    pores = _smooth(0.40, 0.80, T.noise(ps, 1 / 0.00075, 360))
    nose_cheek = np.exp(-((np.abs(x[skin]) - 0.0) / 0.03) ** 2) * (z[skin] > 1.60) * (z[skin] < 1.70)
    h[skin] -= (0.000050 + 0.000040 * nose_cheek) * pores
    h[skin] -= 0.000030 * _smooth(0.55, 0.85, T.noise(ps, 1 / 0.0014, 361))
    h[skin] -= 0.000018 * T.ridged(ps, 1 / 0.0035, seed=362)
    hb = np.zeros(skin.sum(), dtype=np.float32)
    hb[(lips[skin])] = -0.00003 * np.abs(np.sin(x[skin][lips[skin]] / 0.0006))
    h[skin] += hb
    if bandana.any():
        pb = P[bandana]
        weave = (np.sin(pb[:, 0] / 0.00028) * np.sin(pb[:, 2] / 0.00028) + np.sin(pb[:, 1] / 0.00028) * np.sin(pb[:, 2] / 0.00031))
        h[bandana] += 0.000012 * weave
        folds = T.ridged(np.stack([pb[:, 0] * 1.0, pb[:, 1] * 1.0, pb[:, 2] * 3.0], 1), 1 / 0.035, seed=370)
        back = _smooth(-0.04, 0.03, pb[:, 1])
        h[bandana] += 0.0010 * folds * (0.4 + 0.6 * back)
    hd = T.dilate(h, mask, 3)
    dn = T.normal_from_height(hd, P, mask)
    # whiteout blend: the generated relief and the detail relief
    a = gn * 2 - 1
    b = dn * 2 - 1
    n = np.stack([a[..., 0] + b[..., 0], a[..., 1] + b[..., 1], a[..., 2] * b[..., 2]], -1)
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-6)
    nrm = n * 0.5 + 0.5
    ao = np.ones((H, W), dtype=np.float32)
    orm = np.stack([ao, np.clip(rough, 0.05, 1.0), np.zeros_like(ao)], -1)
    out = T.dilate(out, mask, 8)
    nrm = T.dilate(nrm, mask, 8)
    orm = T.dilate(orm, mask, 8)
    paths_ = dict(BC=_save_png(out, os.path.join(DERIVED, "T_Rule_Head_BC.png")),
                  N=_save_png(nrm, os.path.join(DERIVED, "T_Rule_Head_N.png"), srgb=False),
                  ORM=_save_png(orm, os.path.join(DERIVED, "T_Rule_Head_ORM.png"), srgb=False))
    log("  head textures written: %s" % sorted(paths_))
    return textured_material("M_Rule_Head", paths_, sss=0.0)


def textured_material(name, files, sss=0.0):
    """Principled material on BC / N / ORM files (glTF-exportable: base colour, metallic-roughness, normal)."""
    m = bpy.data.materials.new(name + "__new")
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], o.inputs["Surface"])

    def img(path, data):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(path, check_existing=False)
        t.image.colorspace_settings.name = "Non-Color" if data else "sRGB"
        return t
    bc = img(files["BC"], False)
    nt.links.new(bc.outputs["Color"], b.inputs["Base Color"])
    if "ORM" in files:
        orm = img(files["ORM"], True)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    if "N" in files:
        nm = img(files["N"], True)
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(nm.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], b.inputs["Normal"])
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
    return m


# ------------------------------------------------------------------------------------------------ bandana tail


def bandana_tail(head, col, log=print):
    """The bandana's corner hanging over the nape (a bandana knotted at the front leaves its third corner at
    the back): a soft triangular flap 10 cm wide and 6.5 cm long, 1.2 mm thick, lying 3-5 mm off the back of
    the head and the neck with a few loose folds. UVs are taken from the bandana surface it hangs from (nearest
    point, barycentric), so it carries the same print in M_Rule_Head. Returns the object."""
    from mathutils.bvhtree import BVHTree
    me = head.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    uvl = bm.loops.layers.uv.active
    nu, nv = 14, 8
    verts, faces = [], []
    for j in range(nv + 1):
        v = j / nv
        z = 1.652 - v * 0.046
        hw = 0.050 * (1 - v) ** 1.15 + 0.003
        for i in range(nu + 1):
            u = -1 + 2 * i / nu
            x = LM["mid_x"] + u * hw
            hit = tree.ray_cast(Vector((x, 0.40, z)), Vector((0, -1, 0)))
            yb = hit[0].y if hit[0] is not None else 0.05
            fold = 0.0016 * math.sin(u * math.pi * 2.6 + v * 1.7) * (0.3 + 0.7 * v) + 0.0006 * v
            verts.append((x, yb + 0.0026 + 0.0008 * (1 - u * u) + fold, z))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    ob = geo.from_arrays("BandanaTail", np.array(verts), faces, col, smooth=None)
    md = ob.modifiers.new("solid", "SOLIDIFY")
    md.thickness = 0.0012
    md.offset = 0.0
    geo._apply_modifier(ob, md)
    tm = ob.data
    for p in tm.polygons:
        p.use_smooth = True
    uv = tm.uv_layers[0] if tm.uv_layers else tm.uv_layers.new(name="UVMap")
    out = np.zeros((len(tm.loops), 2), dtype=np.float32)
    vuv = []
    for vtx in tm.vertices:
        # as if folded down from the bandana: the flap's point mirrored up about its top edge onto the cloth
        zq = 1.652 + (1.652 - vtx.co.z) + 0.004
        hq = tree.ray_cast(Vector((vtx.co.x, 0.40, zq)), Vector((0, -1, 0)))
        qp = hq[0] if hq[0] is not None else Vector((vtx.co.x, vtx.co.y - 0.004, zq))
        loc, _n, fi, _d = tree.find_nearest(qp)
        f = bm.faces[fi]
        a, b, c = (l.vert.co for l in f.loops)
        from mathutils.geometry import barycentric_transform
        uva = [Vector((l[uvl].uv.x, l[uvl].uv.y, 0)) for l in f.loops]
        q = barycentric_transform(loc, a, b, c, *uva)
        vuv.append((q.x, q.y))
    vuv = np.array(vuv, dtype=np.float32)
    lv = np.empty(len(tm.loops), dtype=np.int64)
    tm.loops.foreach_get("vertex_index", lv)
    out = vuv[lv]
    uv.data.foreach_set("uv", out.ravel())
    tm.materials.clear()
    tm.materials.append(me.materials[0])
    bm.free()
    log("  bandana: hanging corner over the nape (%d triangles)" % sum(len(p.vertices) - 2 for p in tm.polygons))
    return ob
