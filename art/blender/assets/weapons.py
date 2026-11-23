"""Weapons: the player's CHOPPER and NINE (skinned, one bone per moving part, unique 4K sets), their magazines
and top rounds, spent casings, and the Goon's SMG and pipe.

Briefs: docs/unreal/spec/assets/weapons.json (weapon_chopper, weapon_chopper_magazine, weapon_nine,
weapon_nine_magazine, weapon_casing_rifle, weapon_casing_pistol), characters.json (goon_smg, goon_pipe);
viewmodel poses: docs/unreal/spec/02-weapons-combat.md 2.13.

Gun space = Blender space: X forward (bore), Z up, Y left; origin on the bore axis at the back of the receiver
(CHOPPER) or the back face of the slide (NINE). All brief numbers are kept as given.

    build.py build weapons --bake --export --preview          # everything (bakes: ~25 min on 3 threads)
    build.py build weapons --only chopper --bake --export      # one group: chopper, nine, casings, enemy
    build.py build weapons --only chopper --res 512 --bake     # draft bake (every set at 1/8 size)

Textures are authored in UV space with numpy from baked geometry maps (mi.texpaint): every mask is a function
of the 3D position, so seams never show and wear sits where hands, holsters and slings reach.
"""
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

from mi import bake, export, geo, mat, paths, render, rig, scene
from mi import texpaint as tp

FAMILY = {"name": "weapons", "description": "Player guns (skinned SK_Chopper, SK_Nine), magazines, casings, Goon SMG and pipe"}
GROUPS = ("chopper", "nine", "casings", "enemy")

# material ids (face attribute 'mid'): one unique set per asset, the id picks the surface recipe
BLUED, DARK, BRIGHT, WOOD, PAINT, COVER, BORE, BRASS, COPPER, GOLD, STAINLESS, POLYMER, POLISHED, BLACKOX, \
    ZINC, TAPE, ALU, LENS, PRIMER = range(19)


def hexlin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return np.array([x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c], dtype=np.float32)


# ------------------------------------------------------------------------------------------------ modelling kit

def fix_normals(ob):
    """Consistent outward normals (closed meshes are checked by their signed volume)."""
    bm = geo.bm_of(ob)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True) < 0:
        for f in bm.faces:
            f.normal_flip()
    geo.bm_to(ob, bm)
    return ob


def prism(outline, a0, a1, axis="Y", bevel=0.0005, seg=2, name="Prism", corner=30.0, fillet=0.0, fseg=3):
    """Closed 2D outline extruded between a0 and a1 along `axis`, every cap edge and every corner edge bevelled.
    axis 'Y': outline in (x, z) (side view); 'Z': (x, y) (top view); 'X': (y, z) (front view).
    fillet: radius to round the outline's corners first."""
    pts = geo.fillet(outline, fillet, fseg, closed=True) if fillet > 0 else list(outline)
    pts = np.array([p[:2] for p in pts], dtype=np.float64)
    keep = np.ones(len(pts), bool)
    for i in range(len(pts)):
        if np.linalg.norm(pts[i] - pts[i - 1]) < 1e-7:
            keep[i] = False
    pts = pts[keep]
    bm = bmesh.new()

    def to3(p, a):
        return (p[0], a, p[1]) if axis == "Y" else ((p[0], p[1], a) if axis == "Z" else (a, p[0], p[1]))
    v0 = [bm.verts.new(to3(p, a0)) for p in pts]
    v1 = [bm.verts.new(to3(p, a1)) for p in pts]
    n = len(pts)
    bm.faces.new(v0[::-1])
    bm.faces.new(v1)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((v0[i], v0[j], v1[j], v1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bevel > 0:
        edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(corner)]
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=seg, profile=0.5, affect="EDGES", clamp_overlap=True)
    return geo.new(name, bm, smooth=None)


def lathe(prof, seg=48, axis="X", at=(0, 0, 0), name="Lathe", closed=False, fillet=0.0, fseg=2):
    """Revolve a profile [(t, r)] (t along the axis) around an axis through `at`. fillet rounds its corners."""
    if fillet > 0:
        prof = geo.fillet(prof, fillet, fseg, closed=closed)
    ob = geo.revolve([(r, t) for t, r in prof], seg, closed=closed, name=name)
    if axis == "X":
        geo.transform(ob, rot=(0, 90, 0))
    elif axis == "Y":
        geo.transform(ob, rot=(-90, 0, 0))
    geo.transform(ob, loc=at)
    return fix_normals(ob)


def box(x0, x1, y0, y1, z0, z1, bevel=0.0, seg=2, name="Box"):
    ob = geo.box((x1 - x0, y1 - y0, z1 - z0), bevel=bevel, segments=seg, name=name, base=False)
    geo.transform(ob, loc=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return ob


def cut(target, *cutters, solver="EXACT"):
    for c in cutters:
        geo.boolean(target, c, "DIFFERENCE", solver)
    return target


def union(target, *others):
    for c in others:
        geo.boolean(target, c, "UNION", "EXACT")
    return target


def round_edges(ob, width=0.0004, seg=2, angle=50.0):
    """Bevel what booleans left sharp (edges over `angle`), clamped, no hardening (weighted normals later)."""
    md = ob.modifiers.new("bevel", "BEVEL")
    md.width = width
    md.segments = seg
    md.limit_method = "ANGLE"
    md.angle_limit = math.radians(angle)
    md.harden_normals = False
    md.miter_outer = "MITER_ARC"
    md.use_clamp_overlap = True
    geo._apply_modifier(ob, md)
    return ob


def clean(ob):
    bm = geo.bm_of(ob)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges)
    bad = [f for f in bm.faces if f.calc_area() < 1e-11]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    return geo.bm_to(ob, bm)


def mirror_y(ob, name=None):
    cp = ob.copy()
    cp.data = ob.data.copy()
    bpy.context.scene.collection.objects.link(cp)
    geo.transform(cp, scale=(1, -1, 1))
    if name:
        cp.name = name
    return cp


def P(ob, mid, bone, smooth=50.0):
    """Finish a part: smooth + sharp by angle, face-area weighted normals, material id and rigid bone."""
    clean(ob)
    geo.smooth_by_angle(ob, smooth)
    geo.weighted_normals(ob)
    me = ob.data
    for nm in ("mid", "part"):
        a = me.attributes.get(nm) or me.attributes.new(nm, "FLOAT", "FACE")
        v = float(mid) if nm == "mid" else float(np.random.default_rng(len(bpy.data.objects) * 7919).random())
        a.data.foreach_set("value", np.full(len(me.polygons), v, np.float32))
    if bone:
        rig.tag(ob, bone)
    return ob


def rivet(at, axis="Y", r=0.0024, h=0.0009, seg=20, sign=1):
    """Domed rivet head on a face whose outward normal is +axis (sign=-1 for -axis)."""
    prof = [(-0.0006, 0.0), (-0.0006, r * 0.98), (0.0, r), (h * 0.35, r * 0.92), (h * 0.75, r * 0.62), (h, 0.0)]
    ob = lathe(prof, seg, axis=axis, name="Rivet")
    if sign < 0:
        geo.transform(ob, scale=(1, -1, 1) if axis == "Y" else ((-1, 1, 1) if axis == "X" else (1, 1, -1)))
    geo.transform(ob, loc=at)
    return fix_normals(ob)


def pin_head(at, axis="Y", r=0.0022, h=0.0007, sign=1, slot=False, seg=24):
    prof = [(-0.001, 0.0), (-0.001, r), (h * 0.6, r), (h, r * 0.8), (h, 0.0)]
    ob = lathe(prof, seg, axis=axis, name="Pin", fillet=0.00015)
    if slot:
        c = box(-r * 1.2, r * 1.2, -0.00035, 0.00035, h * 0.4, h + 0.001) if axis == "Z" else None
        if axis == "Y":
            c = box(-0.00035, 0.00035, h * 0.4, h + 0.001, -r * 1.2, r * 1.2)
        elif axis == "X":
            c = box(h * 0.4, h + 0.001, -r * 1.2, r * 1.2, -0.00035, 0.00035)
        cut(ob, c)
    if sign < 0:
        geo.transform(ob, scale=(1, -1, 1) if axis == "Y" else ((-1, 1, 1) if axis == "X" else (1, 1, -1)))
    geo.transform(ob, loc=at)
    return fix_normals(ob)


def loft(sections, closed=True, cap0=True, cap1=True, name="Loft"):
    """Mesh through a list of equal-length 3D point rings (n, m, 3)."""
    S = np.asarray(sections, dtype=np.float64)
    n, m = S.shape[:2]
    faces = []
    for i in range(n - 1):
        for j in range(m if closed else m - 1):
            j1 = (j + 1) % m
            faces.append((i * m + j, i * m + j1, (i + 1) * m + j1, (i + 1) * m + j))
    if closed and cap0:
        faces.append(tuple(range(m - 1, -1, -1)))
    if closed and cap1:
        faces.append(tuple((n - 1) * m + j for j in range(m)))
    ob = geo.from_arrays(name, S.reshape(-1, 3), faces, smooth=None)
    return fix_normals(ob)


# ================================================================================================== CHOPPER

CH = {   # brief numbers, metres (gun space)
    "travel": 0.092, "trigger_pivot": (0.108, 0.0, -0.038), "trigger_deg": 19.5, "hinge": (0.222, 0.0, -0.040),
    "mag_deg": 24.0, "sockets": {"Muzzle": (0.4975, 0, 0), "Eject": (0.150, -0.019, 0.018),
                                  "SightRear": (0.0235, 0, 0.0555), "SightFront": (0.409, 0, 0.0555),
                                  "RecoilPivot": (-0.020, 0, -0.030), "MagHinge": (0.222, 0, -0.040),
                                  "Palm_R": (0.040, -0.0155, -0.085), "Palm_L": (0.315, 0.0, -0.0615)},
    "selector_pivot": (0.012, 0.0172, -0.004),
}


def chopper_receiver(parts):
    # stamped receiver shell: 1 mm walls, rear trunnion (8 mm) and front trunnion (66 mm) solid
    rec = prism([(-0.004, -0.040), (0.256, -0.040), (0.256, 0.012), (-0.004, 0.012)], -0.016, 0.016,
                bevel=0.0012, seg=3, name="Receiver")
    cav = box(0.004, 0.190, -0.015, 0.015, -0.039, 0.030)
    well = box(0.1595, 0.2245, -0.0136, 0.0136, -0.050, -0.019, bevel=0.0015)
    port = prism([(0.108, 0.0005), (0.172, 0.0005), (0.172, 0.030), (0.108, 0.030)], -0.030, -0.009, fillet=0.003,
                 bevel=0.0)
    slot = box(0.084, 0.192, 0.009, 0.030, 0.0098, 0.030)
    trig = box(0.098, 0.121, -0.0038, 0.0038, -0.050, -0.030, bevel=0.001)
    bore = lathe([(0.15, 0.0), (0.15, 0.0091), (0.30, 0.0091), (0.30, 0.0)], 32)
    dimples = []
    for s in (1, -1):
        e = geo.sphere(1.0, 32, 16, name="Dimple")
        geo.transform(e, scale=(0.0085, 0.0021, 0.0042))
        geo.transform(e, loc=(0.199, s * (0.016 + 0.0013), -0.026))
        dimples.append(e)
    cut(rec, cav, well, port, slot, trig, bore, *dimples)
    round_edges(rec, 0.0004, 2, 50)
    parts.append(P(rec, BLUED, "body"))
    # rivets: rear trunnion, front trunnion, centre support, trigger guard flanges (both sides)
    for s in (1, -1):
        for x, z in ((0.0045, 0.002), (0.0045, -0.028), (0.214, 0.004), (0.244, 0.004), (0.244, -0.030),
                     (0.140, -0.034)):
            parts.append(P(rivet((x, s * 0.016, z), "Y", sign=s), BLUED, "body"))
    for x in (0.084, 0.092, 0.150, 0.158):
        parts.append(P(rivet((x, 0.0, -0.040), "Z", r=0.0019, h=0.0006, sign=-1), BLUED, "body"))
    # trigger pin, hammer pin (heads both sides), the bent-wire retainer on the left
    for s in (1, -1):
        parts.append(P(pin_head((0.108, s * 0.016, -0.0375), "Y", r=0.0019, sign=s), DARK, "body"))
        parts.append(P(pin_head((0.080, s * 0.016, -0.029), "Y", r=0.0021, sign=s), DARK, "body"))
    wire = geo.pipe(geo.fillet([(0.066, 0.0172, -0.033), (0.080, 0.0172, -0.029), (0.108, 0.0172, -0.0375),
                                (0.122, 0.0172, -0.031)], 0.004, 4), radius=0.0006, segments=10, name="Wire")
    parts.append(P(wire, DARK, "body"))


def chopper_cover(parts):
    # half-round top cover, 1 mm sheet, three stamped transverse ribs, closed rear with the guide-rod button
    x0, x1 = 0.002, 0.186
    half = 0.0168

    prof = []
    for k in range(3):
        prof.append((-half, 0.0040 + 0.0025 * k))                       # straight skirt
    nA = 40
    for k in range(nA + 1):
        a = math.pi * k / nA
        prof.append((-half * math.cos(a), 0.0115 + 0.0225 * math.sin(a) ** 0.85))
    for k in range(2, -1, -1):
        prof.append((half, 0.0040 + 0.0025 * k))
    prof = np.array(prof)
    # inner offset (1 mm) by normals of the outer polyline
    tang = np.gradient(prof, axis=0)
    nrm = np.stack([tang[:, 1], -tang[:, 0]], 1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    if nrm[nA // 2 + 4][1] < 0:
        nrm = -nrm
    inner = prof - nrm * 0.001
    ribs = (0.039, 0.048, 0.057)
    xs = sorted(set(np.round(np.concatenate([np.linspace(x0, x1, 24)] + [r + np.array([-0.0035, -0.0024, -0.0012, 0, 0.0012, 0.0024, 0.0035]) for r in ribs]), 5)))
    sections = []
    for x in xs:
        bump = sum(0.0008 * max(0.0, 1 - ((x - r) / 0.0032) ** 2) ** 0.7 for r in ribs)
        top_w = np.clip((prof[:, 1] - 0.016) / 0.012, 0, 1)
        o = prof + nrm * (bump * top_w)[:, None]
        ring = np.concatenate([o, inner[::-1]])
        sections.append([(x, y, z) for y, z in ring])
    cov = loft(sections, name="Cover")
    # rear end plate
    end = prism([tuple(p) for p in prof[::4]] + [(half, 0.004)], x0 - 0.0003, x0 + 0.0010, axis="X", bevel=0.0003, seg=1)
    port = prism([(0.108, 0.0005), (0.172, 0.0005), (0.172, 0.030), (0.108, 0.030)], -0.030, -0.009, fillet=0.003, bevel=0)
    slot = box(0.084, 0.192, 0.009, 0.030, 0.0030, 0.0175)
    button = box(-0.006, 0.012, -0.0035, 0.0035, 0.0155, 0.0245)
    cut(cov, port, slot, button)
    round_edges(cov, 0.00035, 2, 50)
    parts.append(P(cov, COVER, "body"))
    cut(end, box(-0.006, 0.012, -0.0035, 0.0035, 0.0155, 0.0245))
    parts.append(P(end, COVER, "body"))
    btn = prism([(-0.0045, 0.0158), (0.004, 0.0158), (0.004, 0.0242), (-0.0045, 0.0242)], -0.0032, 0.0032, axis="Y",
                bevel=0.0007, seg=2, fillet=0.0012, name="Button")
    parts.append(P(btn, DARK, "body"))
    # rail on the cover: dovetail profile, 10 lugs
    rp = [(-0.0078, 0.0300), (0.0078, 0.0300), (0.0078, 0.0356), (0.0106, 0.0383), (0.0106, 0.0393), (0.0078, 0.0420),
          (-0.0078, 0.0420), (-0.0106, 0.0393), (-0.0106, 0.0383), (-0.0078, 0.0356)]
    rail = prism(rp, 0.062, 0.168, axis="X", bevel=0.0003, seg=2, name="Rail")
    slots = []
    pitch = 0.106 / 10
    for k in range(10):
        xc = 0.062 + pitch * (k + 1.0) - pitch / 2 + pitch / 2
        if xc > 0.166:
            continue
        slots.append(box(xc - 0.0026, xc + 0.0026, -0.02, 0.02, 0.0366, 0.05))
    cut(rail, *slots)
    round_edges(rail, 0.0003, 2, 50)
    parts.append(P(rail, DARK, "body"))
    # rear sight: base on the cover, leaf with the 4.4 x 4.2 mm notch, protective ears
    base = prism([(0.012, 0.028), (0.034, 0.028), (0.034, 0.0375), (0.030, 0.0415), (0.016, 0.0415), (0.012, 0.0375)],
                 -0.0085, 0.0085, bevel=0.0007, seg=2, name="RSBase")
    parts.append(P(base, DARK, "body"))
    leaf = prism([(0.0215, 0.040), (0.0255, 0.040), (0.0255, 0.0555), (0.0215, 0.0555)], -0.0072, 0.0072, bevel=0.0003,
                 seg=2, name="Leaf")
    notch = box(0.018, 0.030, -0.0022, 0.0022, 0.0513, 0.06)
    cut(leaf, notch)
    round_edges(leaf, 0.00025, 2, 50)
    parts.append(P(leaf, DARK, "body"))
    for s in (1, -1):
        ear = prism([(0.016, 0.038), (0.031, 0.038), (0.029, 0.0555), (0.019, 0.0555)], s * 0.0076, s * 0.0102,
                    bevel=0.0004, seg=2, fillet=0.0015, name="Ear")
        parts.append(P(ear, DARK, "body"))


def chopper_front(parts):
    # sight block (rear sight base of the pattern) on the front trunnion
    sb = prism([(0.186, 0.009), (0.256, 0.009), (0.256, 0.026), (0.250, 0.032), (0.196, 0.032), (0.186, 0.024)],
               -0.0135, 0.0135, bevel=0.0018, seg=3, name="SightBlock", fillet=0.002)
    parts.append(P(sb, BLUED, "body"))
    hg_lever = prism([(0.244, 0.016), (0.262, 0.0175), (0.262, 0.0215), (0.244, 0.0225)], -0.0152, -0.0136, bevel=0.0003,
                     seg=1, fillet=0.001, name="Lever")
    parts.append(P(hg_lever, DARK, "body"))
    # barrel: bored, crowned (inside the booster), and the gas tube
    bar = lathe([(0.250, 0.0), (0.250, 0.0085), (0.4335, 0.0085), (0.4345, 0.0072), (0.4345, 0.0045), (0.4335, 0.0040),
                 (0.4320, 0.0039), (0.300, 0.0039), (0.300, 0.0)], 64, name="Barrel")
    parts.append(P(bar, DARK, "body"))
    gt = lathe([(0.255, 0.0), (0.255, 0.0060), (0.256, 0.0065), (0.3935, 0.0065), (0.3935, 0.0)], 48, at=(0, 0, 0.019),
               name="GasTube", fillet=0.0004)
    parts.append(P(gt, DARK, "body"))
    # upper handguard: wood arch over the gas tube, two vents per side
    up = prism([(-0.017, 0.0062), (-0.0092, 0.0062), (-0.0092, 0.019), (-0.0065, 0.0262), (0.0, 0.0278), (0.0065, 0.0262),
                (0.0092, 0.019), (0.0092, 0.0062), (0.0168, 0.0062), (0.0172, 0.0170), (0.0150, 0.0265), (0.0090, 0.0315), (0.0, 0.0330),
                (-0.0090, 0.0315), (-0.0150, 0.0265), (-0.0172, 0.0170)], 0.262, 0.372, axis="X", bevel=0.0022, seg=4,
               fillet=0.0012, name="UpperHG")
    vents = [prism([(x0, 0.0175), (x0 + 0.020, 0.0175), (x0 + 0.020, 0.0265), (x0, 0.0265)], -0.03, 0.03, bevel=0, fillet=0.0042)
             for x0 in (0.287, 0.322)]
    cut(up, *vents)
    round_edges(up, 0.0006, 2, 50)
    parts.append(P(up, WOOD, "body"))
    # lower handguard: wood cradle round the barrel, three cooling slots per side
    lo = prism([(-0.0222, -0.008), (-0.0230, -0.020), (-0.0220, -0.031), (-0.0175, -0.0390), (-0.0090, -0.0420),
                (0.0090, -0.0420), (0.0175, -0.0390), (0.0220, -0.031), (0.0230, -0.020), (0.0222, -0.008),
                (0.020, -0.004), (0.0108, -0.004), (0.0108, -0.0095), (0.0060, -0.0128), (-0.0060, -0.0128),
                (-0.0108, -0.0095), (-0.0108, -0.004), (-0.020, -0.004)], 0.250, 0.385, axis="X", bevel=0.0028, seg=4,
               fillet=0.0015, name="LowerHG")
    geo.densify(lo, 0.004)
    co, _n = geo.arrays(lo)
    t = np.clip((co[:, 0] - 0.250) / 0.135, 0, 1)
    swell = np.sin(np.pi * t) ** 0.6 * 0.0014 * np.clip((np.abs(co[:, 1]) - 0.016) / 0.007, 0, 1)
    co[:, 1] += np.sign(co[:, 1]) * swell
    co[:, 2] -= np.sin(np.pi * t) ** 0.6 * 0.0008 * (co[:, 2] < -0.036)
    geo.set_verts(lo, co)
    slots = []
    for s in (1, -1):
        for x in (0.296, 0.318, 0.340):
            c = prism([(x - 0.0055, -0.024), (x + 0.0055, -0.024), (x + 0.0055, -0.006), (x - 0.0055, -0.006)],
                      s * 0.0075, s * 0.030, bevel=0, fillet=0.0054)
            slots.append(c)
    cut(lo, *slots)
    round_edges(lo, 0.0006, 2, 50)
    parts.append(P(lo, WOOD, "body"))
    # retaining band (sheet steel) with its lever, right side
    band_o = [(-0.0245, -0.0115), (-0.0245, -0.0345), (-0.0185, -0.0435), (0.0185, -0.0435), (0.0245, -0.0345),
              (0.0245, -0.0115), (0.0125, 0.0030), (0.0, 0.0122), (-0.0125, 0.0030)]
    band = prism(band_o, 0.3815, 0.3915, axis="X", bevel=0.0006, seg=2, fillet=0.004, name="Band")
    cut(band, lathe([(0.37, 0.0), (0.37, 0.0087), (0.40, 0.0087), (0.40, 0.0)], 48))
    round_edges(band, 0.0003, 2, 50)
    parts.append(P(band, BLUED, "body"))
    lev = prism([(0.383, -0.020), (0.390, -0.020), (0.392, -0.004), (0.381, -0.004)], -0.0262, -0.0245, bevel=0.0003,
                seg=1, fillet=0.0015, name="BandLever")
    parts.append(P(lev, DARK, "body"))
    # gas block + front sight tower, hooded front sight (ears to Z 0.063), post tip at X 0.409, Z 0.0555
    ring = lathe([(0.3925, 0.0), (0.3925, 0.0124), (0.426, 0.0124), (0.426, 0.0)], 64, fillet=0.0012, name="GasRing")
    cyl = lathe([(0.3925, 0.0), (0.3925, 0.0093), (0.4215, 0.0093), (0.4215, 0.0)], 48, at=(0, 0, 0.019), fillet=0.0012)
    web = prism([(0.3925, 0.0), (0.426, 0.0), (0.421, 0.020), (0.3925, 0.020)], -0.0088, 0.0088, bevel=0.0006, seg=2)
    tower = prism([(0.3985, 0.020), (0.4195, 0.020), (0.4180, 0.0455), (0.4000, 0.0455)], -0.0096, 0.0096, bevel=0.0008,
                  seg=2, fillet=0.0015)
    union(ring, cyl, web, tower)
    cut(ring, lathe([(0.38, 0.0), (0.38, 0.0049), (0.44, 0.0049), (0.44, 0.0)], 32))
    round_edges(ring, 0.0005, 2, 50)
    parts.append(P(ring, BLUED, "body"))
    for s in (1, -1):
        ear = prism([(0.4015, 0.040), (0.4165, 0.040), (0.4155, 0.0605), (0.4135, 0.063), (0.4045, 0.063), (0.4025, 0.0605)],
                    s * 0.0066, s * 0.0092, bevel=0.0004, seg=2, fillet=0.0012, name="FEar")
        parts.append(P(ear, DARK, "body"))
    drum = lathe([(0.0440, 0.0), (0.0440, 0.0040), (0.0475, 0.0040), (0.0475, 0.0)], 32, axis="Z", at=(0.409, 0, 0),
                 fillet=0.0004)
    geo.transform(drum, loc=(0, 0, 0))
    parts.append(P(drum, DARK, "body"))
    post = prism([(0.4080, 0.047), (0.4100, 0.047), (0.4100, 0.0555), (0.4080, 0.0555)], -0.0010, 0.0010, bevel=0.0002,
                 seg=1, name="Post")
    parts.append(P(post, DARK, "body"))
    # detent pin of the booster, front sling loop (left side of the gas block)
    parts.append(P(lathe([(0.0, 0.0), (0.0, 0.0014), (0.0045, 0.0014), (0.0050, 0.0010), (0.0050, 0.0)], 20, axis="Z",
                         at=(0.4235, -0.0080, 0.0065)), DARK, "body"))
    loop = geo.torus(0.0058, 0.0011, 40, 12, name="SlingLoop")
    geo.transform(loop, rot=(90, 0, 0))
    geo.transform(loop, loc=(0.409, 0.0108, -0.0105))
    parts.append(P(loop, DARK, "body"))
    lug = prism([(0.4015, -0.0105), (0.4165, -0.0105), (0.4165, -0.003), (0.4015, -0.003)], 0.0085, 0.0118, bevel=0.0004)
    cut(lug, lathe([(0.0, 0.0), (0.0, 0.0024), (0.03, 0.0024), (0.03, 0.0)], 20, axis="Y", at=(0.409, -0.01, -0.0105)))
    parts.append(P(lug, BLUED, "body"))
    # muzzle booster: body r 12.8 with one groove, flaring to 16.2 at the mouth, hollow expansion cone
    mb = lathe([(0.426, 0.0090), (0.426, 0.0118), (0.4275, 0.0128), (0.4555, 0.0128), (0.4565, 0.0114), (0.4605, 0.0114),
                (0.4615, 0.0128), (0.4755, 0.0128), (0.4965, 0.0162), (0.4975, 0.0156), (0.4975, 0.0138), (0.4800, 0.0062),
                (0.4440, 0.0050), (0.4440, 0.0086), (0.4300, 0.0086), (0.4300, 0.0090)], 64, closed=True, name="Booster",
               fillet=0.0004)
    parts.append(P(mb, BLUED, "body"))


def chopper_lower(parts):
    # raked pistol grip (laminated wood), screw at the bottom
    g = [(0.031, -0.034), (0.071, -0.034), (0.068, -0.042), (0.062, -0.056), (0.0565, -0.071), (0.0535, -0.084),
         (0.0545, -0.093), (0.0515, -0.103), (0.0475, -0.118), (0.0445, -0.135), (0.0425, -0.146), (0.037, -0.1485),
         (0.004, -0.1485), (-0.0015, -0.1445), (0.001, -0.130), (0.009, -0.104), (0.017, -0.080), (0.024, -0.058),
         (0.028, -0.044)]
    grip = prism(g, -0.0145, 0.0145, bevel=0.0095, seg=6, fillet=0.004, fseg=4, name="Grip", corner=20)
    hole = lathe([(-0.16, 0.0), (-0.16, 0.0042), (-0.1425, 0.0042), (-0.1425, 0.0)], 32, axis="Z", at=(0.020, 0, 0))
    cut(grip, hole)
    round_edges(grip, 0.0005, 2, 50)
    parts.append(P(grip, WOOD, "body"))
    sc = pin_head((0.020, 0, -0.1437), "Z", r=0.0034, h=0.0012, sign=-1, slot=True, seg=32)
    parts.append(P(sc, DARK, "body"))
    # trigger guard: 12 mm stamped strip with flanges riveted to the receiver
    path = geo.fillet([(0.080, 0.0, -0.0409), (0.0965, 0.0, -0.0409), (0.0915, 0.0, -0.0775), (0.150, 0.0, -0.0775),
                       (0.1550, 0.0, -0.0409), (0.1600, 0.0, -0.0409)], 0.006, 5)
    tg = geo.sweep(geo.fillet(geo.rect_profile(0.0018, 0.012), 0.0005, 2, closed=True), path, up=(0, 1, 0), name="Guard")
    fix_normals(tg)
    parts.append(P(tg, BLUED, "body"))
    # magazine catch paddle (behind the magazine, in front of the guard)
    catch = prism([(0.1555, -0.0405), (0.1600, -0.0405), (0.1620, -0.052), (0.1665, -0.064), (0.1625, -0.066),
                   (0.1565, -0.054)], -0.0062, 0.0062, bevel=0.0006, seg=2, fillet=0.0012, name="Catch")
    parts.append(P(catch, DARK, "body"))
    # trigger (pivot X 0.108, Z -0.038), curved blade
    t = [(0.1045, -0.0345), (0.1125, -0.0345), (0.1135, -0.044), (0.1125, -0.052), (0.1085, -0.061), (0.1030, -0.0685),
         (0.1005, -0.0675), (0.1040, -0.060), (0.1065, -0.052), (0.1060, -0.044)]
    trg = prism(t, -0.0031, 0.0031, bevel=0.0007, seg=2, fillet=0.0012, name="Trigger")
    parts.append(P(trg, DARK, "trigger"))
    # under-folding stock: two flat arms from the pivot (X 0.022) to the pin (X 0.236), butt plate under the
    # handguard (X 0.234..0.337 at Z -0.06)
    for s in (1, -1):
        arm = prism([(0.016, -0.0225), (0.030, -0.0215), (0.236, -0.0430), (0.243, -0.0485), (0.236, -0.0555),
                     (0.226, -0.0540), (0.030, -0.0335), (0.016, -0.0345)], s * 0.0163, s * 0.0190, bevel=0.0006,
                    seg=2, fillet=0.004, name="StockArm")
        rib = prism([(0.040, -0.0258), (0.220, -0.0450), (0.220, -0.0478), (0.040, -0.0286)], s * 0.0188, s * 0.0196,
                    bevel=0.0003, seg=1, fillet=0.001)
        union(arm, rib)
        round_edges(arm, 0.0003, 2, 50)
        parts.append(P(arm, BLUED, "body"))
        parts.append(P(pin_head((0.022, s * 0.0190, -0.028), "Y", r=0.0046, h=0.0013, sign=s), DARK, "body"))
        parts.append(P(pin_head((0.236, s * 0.0190, -0.0490), "Y", r=0.0030, h=0.0010, sign=s), DARK, "body"))
    nut = geo.cylinder(0.0048, 0.0016, 6, bevel=0.0004, name="Nut")
    geo.transform(nut, rot=(-90, 0, 0))
    geo.transform(nut, loc=(0.022, -0.0204, -0.028))
    parts.append(P(fix_normals(nut), DARK, "body"))
    # butt plate (stamped channel), curled up at the front
    bp = prism([(0.233, -0.0615), (0.330, -0.0615), (0.3385, -0.0585), (0.3395, -0.0520), (0.3360, -0.0500),
                (0.3340, -0.0568), (0.327, -0.0585), (0.240, -0.0585), (0.236, -0.0555), (0.2340, -0.0520),
                (0.2310, -0.0550)], -0.0192, 0.0192, bevel=0.0007, seg=2, fillet=0.0018, name="ButtPlate")
    parts.append(P(bp, BLUED, "body"))
    for s in (1, -1):
        fl = prism([(0.240, -0.0600), (0.332, -0.0600), (0.330, -0.0525), (0.242, -0.0525)], s * 0.0168, s * 0.0192,
                   bevel=0.0005, seg=2, fillet=0.002)
        parts.append(P(fl, BLUED, "body"))
    xbar = lathe([(-0.0192, 0.0), (-0.0192, 0.0032), (0.0192, 0.0032), (0.0192, 0.0)], 28, axis="Y", at=(0.236, 0, -0.049))
    parts.append(P(xbar, BLUED, "body"))
    # rear sling loop (left, under the rear trunnion) and the stock release button
    loop = geo.torus(0.0055, 0.0011, 40, 12, name="RearLoop")
    geo.transform(loop, rot=(90, 0, 0))
    geo.transform(loop, loc=(0.004, 0.0178, -0.0455))
    parts.append(P(loop, DARK, "body"))
    lug = prism([(-0.004, -0.0455), (0.012, -0.0455), (0.012, -0.0380), (-0.004, -0.0380)], 0.0150, 0.0186, bevel=0.0004)
    cut(lug, lathe([(0.0, 0.0), (0.0, 0.0023), (0.03, 0.0023), (0.03, 0.0)], 20, axis="Y", at=(0.004, 0.0, -0.0455)))
    parts.append(P(lug, BLUED, "body"))
    parts.append(P(pin_head((0.0035, 0.016, -0.0145), "Y", r=0.0030, h=0.0016), DARK, "body"))


def chopper_moving(parts):
    # bolt carrier (bare brushed steel) seen through the port, with the bolt, extractor and the gas piston;
    # charging handle on the LEFT (knob 12 mm across at X 0.180, Z 0.0145, reaching Y 0.042)
    car = prism([(0.096, 0.0060), (0.200, 0.0060), (0.204, 0.0100), (0.204, 0.0240), (0.100, 0.0240), (0.096, 0.0200)],
                -0.0094, 0.0094, bevel=0.0008, seg=2, fillet=0.0015, name="Carrier")
    cam = prism([(0.150, 0.0060), (0.166, 0.0060), (0.176, 0.0150), (0.160, 0.0150)], -0.012, -0.0070, bevel=0)
    lighten = prism([(0.110, 0.0115), (0.140, 0.0115), (0.140, 0.0190), (0.110, 0.0190)], -0.012, -0.0078, bevel=0,
                    fillet=0.003)
    cut(car, cam, lighten)
    round_edges(car, 0.0004, 2, 50)
    parts.append(P(car, BRIGHT, "bolt"))
    bolt = lathe([(0.150, 0.0), (0.150, 0.0072), (0.152, 0.0082), (0.203, 0.0082), (0.2055, 0.0076), (0.2055, 0.0028),
                  (0.2050, 0.0), ], 48, name="Bolt")
    parts.append(P(bolt, BRIGHT, "bolt"))
    lugb = prism([(0.162, 0.0060), (0.172, 0.0060), (0.172, 0.0100), (0.162, 0.0100)], -0.0115, -0.0060, bevel=0.0004)
    parts.append(P(lugb, BRIGHT, "bolt"))
    ext = prism([(0.180, -0.0040), (0.2058, -0.0040), (0.2058, 0.0010), (0.180, 0.0010)], -0.0088, -0.0074, bevel=0.0003,
                seg=1)
    parts.append(P(ext, DARK, "bolt"))
    piston = lathe([(0.200, 0.0), (0.200, 0.0045), (0.335, 0.0045), (0.336, 0.0040), (0.336, 0.0)], 24, at=(0, 0, 0.019))
    parts.append(P(piston, BRIGHT, "bolt"))
    stem = prism([(0.172, 0.0100), (0.188, 0.0100), (0.186, 0.0185), (0.174, 0.0185)], 0.0090, 0.0322, bevel=0.0007,
                 seg=2, fillet=0.0015, name="Stem")
    parts.append(P(stem, DARK, "bolt"))
    knob = lathe([(0.0300, 0.0), (0.0300, 0.0048), (0.0318, 0.0058), (0.0336, 0.0060), (0.0352, 0.0055),
                  (0.0362, 0.0060), (0.0378, 0.0060), (0.0388, 0.0055), (0.0398, 0.0060), (0.0412, 0.0058), (0.0420, 0.0050),
                  (0.0420, 0.0)], 40, axis="Y", at=(0.180, 0, 0.0145), fillet=0.0003, name="Knob")
    parts.append(P(knob, DARK, "bolt"))
    # selector lever on the LEFT: pivot disc at the rear, long arm, finger tab
    sp = CH["selector_pivot"]
    sel = prism([(0.006, -0.0095), (0.016, -0.0095), (0.098, -0.0015), (0.104, 0.0005), (0.104, 0.0062), (0.096, 0.0062),
                 (0.016, 0.0010), (0.006, 0.0010)], 0.0162, 0.0177, bevel=0.0003, seg=2, fillet=0.0035, name="Selector")
    tab = prism([(0.096, -0.0015), (0.106, -0.0015), (0.106, 0.0060), (0.096, 0.0060)], 0.0170, 0.0228, bevel=0.0005,
                seg=2, fillet=0.0016)
    union(sel, tab)
    round_edges(sel, 0.0003, 2, 50)
    parts.append(P(sel, DARK, "selector"))
    parts.append(P(pin_head((sp[0], 0.0177, sp[2]), "Y", r=0.0042, h=0.0012), DARK, "selector"))


def chopper_mag_geometry():
    """Centre-line arc of the magazine fitted to the brief's box (X 0.160..0.312, Z -0.229..-0.021) and returns
    (sections builder data)."""
    R = 0.26
    span = math.radians(46.0)

    def frame(a0):
        n0 = np.array([math.cos(a0), math.sin(a0)])
        P0 = np.array([0.160 + 0.031 * n0[0], -0.021 - 0.031 * n0[1]])
        C = P0 + R * n0
        return P0, C

    def extents(a0):
        P0, C = frame(a0)
        a1 = a0 + span
        n1 = np.array([math.cos(a1), math.sin(a1)])
        P1 = C - R * n1
        t1 = np.array([math.sin(a1), -math.cos(a1)])
        corners = [P1 + 0.03175 * n1 + 0.0045 * t1, P1 - 0.03175 * n1 + 0.0045 * t1]
        return max(c[0] for c in corners), min(c[1] for c in corners)
    best = min(np.linspace(0.0, math.radians(14), 281), key=lambda a: abs(extents(a)[0] - 0.312))
    return R, best, best + span, frame(best)


def chopper_magazine(col):
    """SM_Weapon_ChopperMagazine (+ _TopRound): lofted stamped body with side ribs, spine, four cross ribs,
    feed lips, follower, the second round and a wider floor plate. Origin = gun origin."""
    R, a0, a1, (P0, C) = chopper_mag_geometry()
    W = 0.02550 / 2
    parts = []
    # perimeter of one section, in (n, y): n forward (+) / back (-), y across; depth d(s), 62 -> 59 mm
    cross = (0.30, 0.55, 0.80)
    n_st = []
    base = np.linspace(0.0, 1.0, 46)
    extra = []
    for c in cross + (0.98,):
        extra += [c - 0.022, c - 0.012, c - 0.004, c + 0.004, c + 0.012, c + 0.022]
    st = np.unique(np.clip(np.concatenate([base, extra, [0.004, 0.012]]), 0, 1))

    def section(sv, inner=False):
        d = (0.062 + (0.059 - 0.062) * sv) / 2
        a = a0 + (a1 - a0) * sv
        n = np.array([math.cos(a), math.sin(a)])
        Pc = C - R * n
        pts = []
        # side (left, +y), from back to front, longitudinal rib in the middle, cross ribs bump the whole side
        xr = sum(0.0007 * max(0.0, 1 - ((sv - c) / 0.016) ** 2) ** 0.6 for c in cross)
        ns = np.concatenate([np.linspace(-1, -0.55, 4), [-0.30, -0.22, -0.16, 0.16, 0.22, 0.30], np.linspace(0.55, 1, 4)])
        for side in (1, -1):
            seq = ns if side == 1 else ns[::-1]
            for u in seq:
                rib = 0.0008 if abs(u) <= 0.16 else (0.0004 if abs(u) <= 0.22 else 0.0)
                y = side * (W + rib + xr)
                if abs(u) > 0.92:                                   # rounded corners
                    k = (abs(u) - 0.92) / 0.08
                    y = side * (W - 0.0022 * (1 - math.cos(k * math.pi / 2)) + xr)
                nn = u * d
                if u < -0.9 and abs(y) > W * 0.4:                   # spine strip on the back
                    nn -= 0.0006
                pts.append((nn, y))
        pts = np.array(pts)
        if inner:
            pts = pts * np.array([(d - 0.0008) / d, (W - 0.0008) / W])
        return np.array([[Pc[0] + p[0] * n[0], p[1], Pc[1] + p[0] * n[1]] for p in pts])
    body = loft([section(s) for s in st], cap0=False, cap1=True, name="MagBody")
    parts.append(P(body, BLUED, None))
    inner_st = st[st <= 0.16]
    inn = loft([section(s, True) for s in inner_st], cap0=False, cap1=True, name="MagInner")
    bm = geo.bm_of(inn)
    for f in bm.faces:
        f.normal_flip()
    geo.bm_to(inn, bm)
    parts.append(P(inn, BORE, None))
    o, i = section(0.0), section(0.0, True)
    m = len(o)
    verts = np.concatenate([o, i])
    rim = geo.from_arrays("MagRim", verts, [(j, (j + 1) % m, m + (j + 1) % m, m + j) for j in range(m)], smooth=None)
    fix_normals(rim)
    bmr = geo.bm_of(rim)
    up = Vector((-math.sin(a0), 0, math.cos(a0)))
    if sum((f.normal.dot(up) for f in bmr.faces)) < 0:
        for f in bmr.faces:
            f.normal_flip()
    geo.bm_to(rim, bmr)
    parts.append(P(rim, BLUED, None))
    # feed lips: the side walls turned in over the rounds (rear two thirds)
    t0 = np.array([math.sin(a0), -math.cos(a0)])
    n0 = np.array([math.cos(a0), math.sin(a0)])
    for s in (1, -1):
        prof = [(s * W, 0.0), (s * W, 0.0025), (s * (W - 0.0012), 0.0040), (s * (W - 0.0040), 0.0046),
                (s * (W - 0.0050), 0.0040), (s * (W - 0.0008), 0.0016), (s * (W - 0.0008), 0.0)]
        if s < 0:
            prof = prof[::-1]
        secs = []
        for u in np.linspace(-0.030, 0.012, 9):
            base_pt = P0 + u * n0
            secs.append([(base_pt[0] - h * t0[0], y, base_pt[1] - h * t0[1]) for y, h in prof])
        lip = loft(secs, name="Lip")
        parts.append(P(lip, BLUED, None))
    # floor plate: slightly wider (27.8 x 63.5), 3 mm, with the locking-plate dimple
    nb = np.array([math.cos(a1), math.sin(a1)])
    tb = np.array([math.sin(a1), -math.cos(a1)])
    Pb = C - R * nb
    fp = box(-0.03175, 0.03175, -0.0139, 0.0139, -0.0045, -0.0005, bevel=0.0009, seg=2, name="Floor")
    lip_f = box(-0.0300, 0.0300, -0.0139, 0.0139, -0.0015, 0.0010, bevel=0.0004)
    union(fp, lip_f)
    d = geo.sphere(1.0, 24, 12)
    geo.transform(d, scale=(0.006, 0.006, 0.0012))
    geo.transform(d, loc=(-0.012, 0.0, -0.0046))
    cut(fp, d)
    rot = Matrix(((nb[0], 0, tb[0]), (0, 1, 0), (nb[1], 0, tb[1])))
    M = Matrix.Translation((Pb[0], 0, Pb[1])) @ rot.to_4x4() @ Matrix.Diagonal((1, 1, -1, 1))
    fp.data.transform(M)
    fp.data.flip_normals()
    fix_normals(fp)
    parts.append(P(fp, DARK, None))
    # follower edge and the second round (double stack) under the top round
    sec = cartridge(0.050, 0.0056, name="Round2")
    geo.transform(sec, loc=(0.172 - 0.0, -0.0042, -0.0195 - 0.0092))
    geo.transform(sec, rot=(0, 0, 0))
    parts.append(sec)
    top = cartridge(0.050, 0.0056, name="TopRound")
    geo.transform(top, loc=(0.172, 0.0042, -0.0195))
    body = geo.join(parts, "SM_Weapon_ChopperMagazine", col)
    scene.move_to(top, col)
    top.name = top.data.name = "SM_Weapon_ChopperMagazine_TopRound"
    return body, top


def cartridge(length, r, name="Round", bullet=True, rifle=True, seg=40):
    """A loaded round along +X from its base at x = 0: rimless bottle-necked (rifle) or straight (pistol) case,
    extraction groove, primer, jacketed bullet. Case = BRASS, primer = PRIMER, bullet = COPPER."""
    if rifle:
        case_len = 0.0388 * length / 0.050 if length > 0.045 else 0.0388
        sh = case_len * 0.74
        prof = [(0.0, 0.0), (0.0, r * 0.98), (0.0006, r), (0.0012, r), (0.0014, r * 0.84), (0.0024, r * 0.84),
                (0.0030, r * 0.99), (sh, r * 0.89), (sh + 0.0035, r * 0.70), (case_len, r * 0.70), (case_len, 0.0)]
        b0 = case_len
        bprof = [(b0 - 0.004, 0.0), (b0 - 0.004, r * 0.69), (b0 + 0.003, r * 0.69), (length - 0.0045, r * 0.52),
                 (length - 0.0012, r * 0.20), (length, 0.0)]
    else:
        case_len = 0.0192
        prof = [(0.0, 0.0), (0.0, r * 0.98), (0.0006, r), (0.0011, r), (0.0013, r * 0.86), (0.0021, r * 0.86),
                (0.0027, r), (case_len, r * 0.95), (case_len, 0.0)]
        b0 = case_len
        bprof = [(b0 - 0.004, 0.0), (b0 - 0.004, r * 0.93), (b0 + 0.002, r * 0.93), (length - 0.0035, r * 0.70),
                 (length - 0.0008, r * 0.30), (length, 0.0)]
    case = lathe(prof, seg, name=name, fillet=0.00025)
    parts = [P(case, BRASS, None)]
    pr = lathe([(-0.0002, 0.0), (-0.0002, r * 0.42), (0.0006, r * 0.42), (0.0006, 0.0)], 24)
    parts.append(P(pr, PRIMER, None))
    if bullet:
        parts.append(P(lathe(bprof, seg, fillet=0.0002), COPPER, None))
    return geo.join(parts, name)


def chopper_build(ctx):
    parts = []
    chopper_receiver(parts)
    chopper_cover(parts)
    chopper_front(parts)
    chopper_lower(parts)
    chopper_moving(parts)
    gun = geo.join(parts, "SK_Chopper", ctx.col)
    bones = [rig.Bone("body", (0, 0, 0)),
             rig.Bone("bolt", (0.180, 0, 0.0145), "body"),
             rig.Bone("trigger", CH["trigger_pivot"], "body"),
             rig.Bone("selector", CH["selector_pivot"], "body"),
             rig.Bone("magazine", (0, 0, 0), "body")]
    bones += [rig.Bone(k, v, "body", deform=False) for k, v in CH["sockets"].items()]
    arm = rig.armature("SKEL_Chopper", bones, ctx.col)
    rig.bind(gun, arm)
    return gun, arm


# ===================================================================================================== NINE

NN = {   # brief numbers (gun space; origin on the bore axis at the back face of the slide)
    "travel": 0.044, "barrel_lug": (0.070, 0.0, -0.008), "barrel_deg": 2.3, "trigger_pivot": (0.091, 0.0, -0.031),
    "trigger_deg": 17.0, "hammer_pivot": (-0.0135, 0.0, -0.0105), "hammer_down_deg": 36.0,
    "stop_pivot": (0.0955, 0.0, -0.0165), "stop_deg": 7.0, "mag_axis": (0.250, 0.0, 0.968),
    "sockets": {"Muzzle": (0.201, 0, 0), "Eject": (0.105, -0.012, 0.014), "SightRear": (0.0125, 0, 0.0185),
                "SightFront": (0.186, 0, 0.0185), "RecoilPivot": (-0.030, 0, -0.085),
                "Palm_R": (0.014, -0.0146, -0.078), "Palm_L": (0.030, 0.0146, -0.090)},
}


def nine_slide(parts):
    # brushed stainless slide, rounded top edges, hollow, 7 rear serrations per side, port top right
    sec = [(-0.0135, -0.0135), (0.0135, -0.0135), (0.0135, 0.0060), (0.0118, 0.0105), (0.0080, 0.0125),
           (-0.0080, 0.0125), (-0.0118, 0.0105), (-0.0135, 0.0060)]
    sl = prism(sec, 0.0, 0.196, axis="X", bevel=0.0006, seg=2, fillet=0.0025, fseg=4, name="Slide")
    chan = box(0.0045, 0.250, -0.0104, 0.0104, -0.020, 0.0100)
    nose = lathe([(0.15, 0.0), (0.15, 0.0072), (0.25, 0.0072), (0.25, 0.0)], 48)
    rod = lathe([(0.15, 0.0), (0.15, 0.0034), (0.25, 0.0034), (0.25, 0.0)], 32, at=(0, 0, -0.0118))
    port = prism([(0.086, -0.003), (0.126, -0.003), (0.126, 0.030), (0.086, 0.030)], -0.030, 0.0042, bevel=0,
                 fillet=0.0012)
    firing = lathe([(-0.01, 0.0), (-0.01, 0.0016), (0.006, 0.0016), (0.006, 0.0)], 20)
    sers = []
    for s in (1, -1):
        for k in range(7):
            x = 0.0115 + k * 0.0048
            c = prism([(x - 0.0011, -0.0120), (x + 0.0011, -0.0120), (x + 0.0011, 0.0068), (x - 0.0011, 0.0068)],
                      s * 0.0127, s * 0.020, bevel=0, fillet=0.0006)
            sers.append(c)
    front_dt = box(0.1815, 0.1905, -0.0050, 0.0050, 0.0105, 0.020)
    rear_dt = box(0.0055, 0.0195, -0.0095, 0.0095, 0.0100, 0.020)
    cut(sl, chan, nose, rod, port, firing, front_dt, rear_dt, *sers)
    round_edges(sl, 0.0003, 2, 50)
    parts.append(P(sl, STAINLESS, "slide"))
    # sights: rear notch 4.2 x 3.9, top Z 0.0185, X 0.007..0.018; front blade 3.4 wide, top at X 0.1835..0.1885
    rs = prism([(0.0060, 0.0098), (0.0190, 0.0098), (0.0190, 0.0150), (0.0180, 0.0185), (0.0070, 0.0185), (0.0060, 0.0170)],
               -0.0098, 0.0098, bevel=0.0004, seg=2, name="RearSight")
    cut(rs, box(0.0, 0.03, -0.0021, 0.0021, 0.0146, 0.03))
    round_edges(rs, 0.0002, 1, 50)
    parts.append(P(rs, DARK, "slide"))
    fs = prism([(0.1820, 0.0098), (0.1900, 0.0098), (0.1888, 0.0150), (0.1885, 0.0185), (0.1835, 0.0185), (0.1830, 0.0140)],
               -0.0017, 0.0017, bevel=0.0003, seg=2, name="FrontSight")
    base = box(0.1818, 0.1902, -0.0048, 0.0048, 0.0098, 0.0128, bevel=0.0004)
    union(fs, base)
    parts.append(P(fs, DARK, "slide"))
    # extractor on the right of the port
    ex = prism([(0.060, 0.0030), (0.084, 0.0030), (0.0855, 0.0068), (0.060, 0.0068)], -0.0141, -0.0132, bevel=0.0003, seg=1)
    parts.append(P(ex, STAINLESS, "slide"))
    parts.append(P(pin_head((0.068, -0.0136, 0.0010), "Y", r=0.0012, h=0.0004, sign=-1), DARK, "slide"))


def nine_barrel(parts):
    b = lathe([(0.062, 0.0), (0.062, 0.0076), (0.064, 0.0078), (0.124, 0.0078), (0.127, 0.0068), (0.2005, 0.0068),
               (0.2010, 0.0060), (0.2010, 0.0050), (0.2005, 0.0046), (0.150, 0.0045), (0.150, 0.0)], 64, name="Barrel",
              fillet=0.0002)
    hood = prism([(0.0640, 0.0), (0.1240, 0.0), (0.1240, 0.0097), (0.0660, 0.0097)], -0.0068, 0.0068, bevel=0.0005,
                 seg=2, name="Hood")
    lug = prism([(0.0640, -0.0040), (0.0800, -0.0040), (0.0790, -0.0105), (0.0700, -0.0125), (0.0640, -0.0105)],
                -0.0045, 0.0045, bevel=0.0005, seg=2, fillet=0.0015)
    union(b, hood, lug)
    cut(b, lathe([(0.055, 0.0), (0.055, 0.0047), (0.17, 0.0047), (0.17, 0.0)], 48),
        lathe([(-0.01, 0.0), (-0.01, 0.0021), (0.01, 0.0021), (0.01, 0.0)], 20, axis="Y", at=(0.070, 0, -0.008)))
    round_edges(b, 0.0003, 2, 50)
    parts.append(P(b, POLISHED, "barrel"))
    rod = lathe([(0.090, 0.0), (0.090, 0.0026), (0.1955, 0.0026), (0.1970, 0.0020), (0.1970, 0.0)], 32, at=(0, 0, -0.0118))
    parts.append(P(rod, POLISHED, "frame"))
    spring = []
    for k in range(int((0.188 - 0.100) / 0.0036)):
        x = 0.100 + k * 0.0036
        t = geo.torus(0.0031, 0.0005, 14, 6, name="Coil")
        geo.transform(t, rot=(0, 90 + 8, 0))
        geo.transform(t, loc=(x, 0, -0.0118))
        spring.append(t)
    sp = geo.join(spring, "Spring")
    parts.append(P(sp, DARK, "frame"))


def nine_frame(parts):
    out = [(-0.0300, -0.0108), (-0.0060, -0.0135), (0.1960, -0.0135), (0.1960, -0.0238), (0.1350, -0.0245),
           (0.1290, -0.0300), (0.1285, -0.0560), (0.1220, -0.0690), (0.1100, -0.0715), (0.0760, -0.0715),
           (0.0680, -0.0665), (0.0620, -0.0590), (0.0592, -0.0650), (0.0560, -0.0760), (0.0545, -0.0860),
           (0.0505, -0.0990), (0.0465, -0.1130), (0.0430, -0.1280), (-0.0310, -0.1280), (-0.0330, -0.1240),
           (-0.0300, -0.1080), (-0.0262, -0.0900), (-0.0222, -0.0720), (-0.0175, -0.0540), (-0.0142, -0.0400),
           (-0.0150, -0.0300), (-0.0200, -0.0220), (-0.0300, -0.0175)]
    fr = prism(out, -0.0112, 0.0112, bevel=0.0012, seg=3, fillet=0.0025, fseg=3, name="Frame", corner=25)
    opening = prism([(0.0730, -0.0290), (0.1235, -0.0290), (0.1235, -0.0560), (0.1170, -0.0655), (0.0800, -0.0655),
                     (0.0730, -0.0600)], -0.02, 0.02, bevel=0, fillet=0.004)
    hammer_slot = box(-0.040, 0.004, -0.0036, 0.0036, -0.0200, 0.0)
    ax = np.array(NN["mag_axis"])
    well = mag_prism(0.0106, 0.0180, -0.0005, 0.120, extra=0.0)
    rails = []
    for x in (0.149, 0.163, 0.1765):
        rails.append(box(x - 0.0026, x + 0.0026, -0.02, 0.02, -0.0260, -0.0218))
    rails.append(box(0.130, 0.200, -0.02, -0.0095, -0.0228, -0.0205))
    rails.append(box(0.130, 0.200, 0.0095, 0.02, -0.0228, -0.0205))
    trig = box(0.084, 0.098, -0.0035, 0.0035, -0.034, -0.0245, bevel=0.0005)
    cut(fr, opening, hammer_slot, well, trig, *rails)
    round_edges(fr, 0.00035, 2, 50)
    parts.append(P(fr, BLACKOX, "frame"))
    # grip panels (3.4 mm, black checkered: checkering is in the normal map), two slotted screws each
    gp = [(-0.0115, -0.0345), (0.0520, -0.0480), (0.0480, -0.0820), (0.0420, -0.1080), (0.0385, -0.1225),
          (-0.0270, -0.1225), (-0.0220, -0.0960), (-0.0160, -0.0700), (-0.0125, -0.0480)]
    for s in (1, -1):
        pan = prism(gp, s * 0.0110, s * 0.0144, bevel=0.0012, seg=3, fillet=0.004, fseg=3, name="Panel", corner=25)
        geo.densify(pan, 0.004)
        co, _n = geo.arrays(pan)
        outer = np.abs(co[:, 1]) > 0.0120
        # palm swell: the outer face domes by up to 1.3 mm toward the middle of the panel
        dx, dz = (co[:, 0] - 0.016) / 0.036, (co[:, 2] + 0.080) / 0.047
        bulge = np.clip(1 - dx * dx - dz * dz, 0, 1) ** 0.8 * 0.0013
        co[:, 1] += np.where(outer, s * bulge * np.clip((np.abs(co[:, 1]) - 0.0120) / 0.0024, 0, 1), 0)
        geo.set_verts(pan, co)
        holes = [lathe([(-0.01, 0.0), (-0.01, 0.0031), (0.01, 0.0031), (0.01, 0.0)], 28, axis="Y", at=(x, s * 0.0144, z))
                 for x, z in ((0.0365, -0.0530), (-0.0090, -0.1130))]
        cut(pan, *holes)
        round_edges(pan, 0.0003, 2, 50)
        parts.append(P(pan, POLYMER, "frame"))
        for x, z in ((0.0365, -0.0530), (-0.0090, -0.1130)):
            parts.append(P(pin_head((x, s * 0.0138, z), "Y", r=0.0027, h=0.0006, sign=s, slot=True), DARK, "frame"))
    # pins through the frame (trigger, hammer, slide-stop shaft on the right), lanyard loop at the heel
    for s in (1, -1):
        parts.append(P(pin_head((NN["trigger_pivot"][0], s * 0.0112, NN["trigger_pivot"][2]), "Y", r=0.0016, h=0.0003, sign=s), DARK, "frame"))
        parts.append(P(pin_head((NN["hammer_pivot"][0], s * 0.0112, NN["hammer_pivot"][2]), "Y", r=0.0022, h=0.0004, sign=s), DARK, "frame"))
    parts.append(P(pin_head((NN["stop_pivot"][0], -0.0112, NN["stop_pivot"][2]), "Y", r=0.0021, h=0.0006, sign=-1), DARK, "frame"))
    # thumb safety (left), magazine button (left, round, at X 0.0625 Z -0.0405)
    saf = prism([(0.0040, -0.0150), (0.0300, -0.0150), (0.0300, -0.0075), (0.0200, -0.0060), (0.0040, -0.0078)],
                0.0112, 0.0128, bevel=0.0003, seg=2, fillet=0.0015, name="Safety")
    pad = prism([(0.0200, -0.0150), (0.0305, -0.0150), (0.0305, -0.0075), (0.0200, -0.0075)], 0.0122, 0.0160,
                bevel=0.0005, seg=2, fillet=0.0018)
    union(saf, pad)
    parts.append(P(saf, DARK, "frame"))
    parts.append(P(pin_head((0.0080, 0.0128, -0.0112), "Y", r=0.0028, h=0.0006), DARK, "frame"))
    btn = lathe([(0.0, 0.0), (0.0, 0.0046), (0.0012, 0.0046), (0.0020, 0.0040), (0.0024, 0.0), ], 36, axis="Y",
                at=(0.0625, 0.0110, -0.0405), fillet=0.0003)
    parts.append(P(btn, DARK, "frame"))
    loop = geo.torus(0.0034, 0.0008, 28, 10, name="Lanyard")
    geo.transform(loop, rot=(90, 0, 0))
    geo.transform(loop, loc=(-0.0300, 0.0, -0.1290))
    parts.append(P(loop, DARK, "frame"))


def nine_moving(parts):
    # slide stop (left, X 0.058..0.100), hammer (spur up to Z 0.0105), gold trigger
    st = prism([(0.0580, -0.0182), (0.0640, -0.0190), (0.0960, -0.0190), (0.1000, -0.0165), (0.0960, -0.0140),
                (0.0700, -0.0140), (0.0610, -0.0120), (0.0580, -0.0135)], 0.0112, 0.0128, bevel=0.0003, seg=2,
               fillet=0.0012, name="SlideStop")
    tpad = prism([(0.0580, -0.0182), (0.0700, -0.0188), (0.0700, -0.0128), (0.0590, -0.0125)], 0.0124, 0.0150,
                 bevel=0.0005, seg=2, fillet=0.0015)
    union(st, tpad)
    parts.append(P(st, DARK, "slide_stop"))
    parts.append(P(pin_head((NN["stop_pivot"][0], 0.0128, NN["stop_pivot"][2]), "Y", r=0.0023, h=0.0006), DARK, "slide_stop"))
    hp = NN["hammer_pivot"]
    ham = prism([(-0.0195, -0.0150), (-0.0080, -0.0150), (-0.0060, -0.0070), (-0.0115, 0.0030), (-0.0195, 0.0105),
                 (-0.0285, 0.0105), (-0.0300, 0.0080), (-0.0245, 0.0020), (-0.0205, -0.0060)], -0.0031, 0.0031,
                bevel=0.0005, seg=2, fillet=0.0015, name="Hammer")
    cut(ham, lathe([(-0.01, 0.0), (-0.01, 0.0045), (0.01, 0.0045), (0.01, 0.0)], 28, axis="Y", at=(-0.0170, 0, 0.0005)))
    round_edges(ham, 0.0003, 2, 50)
    parts.append(P(ham, DARK, "hammer"))
    t = [(0.0870, -0.0290), (0.0950, -0.0290), (0.0965, -0.0380), (0.0955, -0.0460), (0.0920, -0.0545),
         (0.0880, -0.0600), (0.0850, -0.0590), (0.0878, -0.0530), (0.0898, -0.0455), (0.0895, -0.0380)]
    trg = prism(t, -0.0031, 0.0031, bevel=0.0008, seg=3, fillet=0.0012, name="Trigger")
    parts.append(P(trg, GOLD, "trigger"))


def mag_prism(half_w, half_d, a0, a1, extra=0.0, centre_f=0.0039):
    """Prism along the NINE's magazine axis: cross-section (front/back, width) from a0 to a1 metres along the axis
    measured from the top of the base pad. Used for the well and the body."""
    a = np.array(NN["mag_axis"], float)
    a /= np.linalg.norm(a)
    f = np.array([a[2], 0.0, -a[0]])
    base = nine_mag_base()
    sec = geo.fillet([(-half_d, -half_w), (half_d, -half_w), (half_d, half_w), (-half_d, half_w)], 0.003, 3, closed=True)
    rings = []
    for t in (a0, a1):
        c = base + a * t + f * centre_f
        rings.append([tuple(c + f * u + np.array([0, 1.0, 0]) * v) for u, v in sec])
    return loft(rings, name="MagPrism")


def nine_mag_base():
    """Centre of the top face of the base pad (where the body starts)."""
    a = np.array(NN["mag_axis"], float)
    a /= np.linalg.norm(a)
    f = np.array([a[2], 0.0, -a[0]])
    pc = np.array([0.0080, 0.0, 0.0])
    # lowest point of the pad (front-bottom corner) sits at Z -0.1345: pad 76 long (f), 7 thick (a)
    pc[2] = -0.1345 - (0.038 * f[2] - 0.0035 * a[2])
    return pc + a * 0.0035


def nine_build(ctx):
    parts = []
    nine_slide(parts)
    nine_barrel(parts)
    nine_frame(parts)
    nine_moving(parts)
    gun = geo.join(parts, "SK_Nine", ctx.col)
    bones = [rig.Bone("frame", (0, 0, 0)),
             rig.Bone("slide", (0, 0, 0), "frame"),
             rig.Bone("barrel", NN["barrel_lug"], "frame"),
             rig.Bone("trigger", NN["trigger_pivot"], "frame"),
             rig.Bone("hammer", NN["hammer_pivot"], "frame"),
             rig.Bone("slide_stop", NN["stop_pivot"], "frame"),
             rig.Bone("magazine", (0, 0, 0), "frame")]
    bones += [rig.Bone(k, v, "frame", deform=False) for k, v in NN["sockets"].items()]
    arm = rig.armature("SKEL_Nine", bones, ctx.col)
    rig.bind(gun, arm)
    return gun, arm


def nine_magazine(col):
    """SM_Weapon_NineMagazine (+ _TopRound): 19.5 x 34 mm brushed body raked with the grip, three witness holes
    per side with the stack showing through, feed lips, gold base pad 76 x 26 x 7 mm."""
    a = np.array(NN["mag_axis"], float)
    a /= np.linalg.norm(a)
    f = np.array([a[2], 0.0, -a[0]])
    base = nine_mag_base()
    top_t = (-0.037 - base[2]) / a[2]
    W, D = 0.00975, 0.017
    parts = []
    sec = [(-D, -W), (D - 0.004, -W), (D, -W + 0.004), (D, W - 0.004), (D - 0.004, W), (-D, W)]
    sec = geo.fillet(sec, 0.0018, 3, closed=True)
    inner = [(u * (D - 0.0007) / D, v * (W - 0.0007) / W) for u, v in sec]
    ring = lambda t, s: [tuple(base + a * t + f * u + np.array([0, 1.0, 0]) * v) for u, v in s]
    body = loft([ring(0.0, sec), ring(top_t - 0.004, sec)], cap0=True, cap1=False, name="NMagBody")
    inn = loft([ring(top_t - 0.004 - 0.030, inner), ring(top_t - 0.004, inner)], cap0=True, cap1=False, name="NMagIn")
    bm = geo.bm_of(inn)
    for fc in bm.faces:
        fc.normal_flip()
    geo.bm_to(inn, bm)
    holes = []
    for t in (0.025, 0.045, 0.065):
        c = base + a * t + f * (-0.008)
        holes.append(lathe([(-0.02, 0.0), (-0.02, 0.0015), (0.02, 0.0015), (0.02, 0.0)], 24, axis="Y", at=tuple(c)))
    cut(body, *holes)
    round_edges(body, 0.0003, 2, 50)
    parts.append(P(body, BLUED, None))
    parts.append(P(inn, BORE, None))
    # lips: walls turned in at the top
    o, i = ring(top_t - 0.004, sec), ring(top_t - 0.004, inner)
    m = len(o)
    rim = geo.from_arrays("NRim", np.concatenate([o, i]), [(j, (j + 1) % m, m + (j + 1) % m, m + j) for j in range(m)], smooth=None)
    parts.append(P(fix_normals(rim), BLUED, None))
    for s in (1, -1):
        prof = [(s * W, 0.0), (s * W, 0.0020), (s * (W - 0.0012), 0.0034), (s * (W - 0.0036), 0.0040),
                (s * (W - 0.0044), 0.0034), (s * (W - 0.0007), 0.0012), (s * (W - 0.0007), 0.0)]
        if s < 0:
            prof = prof[::-1]
        secs = []
        for u in np.linspace(-D + 0.001, D * 0.25, 7):
            c = base + a * (top_t - 0.004) + f * u
            secs.append([tuple(c + np.array([0, y, 0]) + a * h) for y, h in prof])
        parts.append(P(loft(secs, name="NLip"), BLUED, None))
    # rounds stacked inside (seen through the witness holes), staggered left / right
    for k in range(1, 9):
        t = top_t - 0.004 - 0.0062 * k
        c = base + a * t + f * (-D + 0.002)
        rd = cartridge(0.030, 0.0047, name="Stack", rifle=False, seg=20)
        geo.transform(rd, loc=(c[0], (0.0035 if k % 2 else -0.0035), c[2]))
        parts.append(rd)
    # base pad: rounded gold block perpendicular to the axis
    pad = prism([(-0.038, -0.0035), (0.038, -0.0035), (0.038, 0.0035), (-0.038, 0.0035)], -0.013, 0.013, axis="Y",
                bevel=0.0022, seg=3, fillet=0.010, fseg=6, name="Pad")
    cut(pad, prism([(-0.006, -0.010), (0.006, -0.010), (0.006, -0.0026), (-0.006, -0.0026)], -0.02, 0.02, bevel=0,
                   fillet=0.0025))
    round_edges(pad, 0.0004, 2, 50)
    rot = Matrix(((f[0], 0, a[0]), (0, 1, 0), (f[2], 0, a[2]))).to_4x4()
    pc = base - a * 0.0035
    pad.data.transform(Matrix.Translation(tuple(pc)) @ rot)
    parts.append(P(fix_normals(pad), GOLD, None))
    body = geo.join(parts, "SM_Weapon_NineMagazine", col)
    # top round: along the bore direction, 33.5 mm below the bore axis, case at the back of the lips
    ctop = base + a * top_t
    top = cartridge(0.030, 0.0048, name="SM_Weapon_NineMagazine_TopRound", rifle=False)
    geo.transform(top, loc=(ctop[0] - 0.0175, 0.0, -0.0335))
    scene.move_to(top, col)
    top.name = top.data.name = "SM_Weapon_NineMagazine_TopRound"
    return body, top


# ================================================================================================== CASINGS

def casing(kind):
    """Spent case at real size (the briefs' drawn sizes are a third larger: scale in the effect if wanted), long
    axis +X, origin at the middle of its length; open mouth, struck primer."""
    if kind == "rifle":
        Lc, r = 0.0390, 0.0057
        prof = [(0.0, 0.0), (0.0, r * 0.97), (0.0004, r), (0.0009, r), (0.0012, r * 0.84), (0.0022, r * 0.84),
                (0.0027, r * 0.99), (0.0300, r * 0.885), (0.0336, r * 0.765), (Lc - 0.0002, r * 0.765), (Lc, r * 0.74),
                (Lc, r * 0.69), (0.0333, r * 0.69), (0.0300, r * 0.80), (0.0050, r * 0.84), (0.0042, 0.0)]
        name = "SM_Weapon_CasingRifle"
    else:
        Lc, r = 0.0192, 0.00495
        prof = [(0.0, 0.0), (0.0, r * 0.97), (0.0004, r), (0.0009, r), (0.0012, r * 0.86), (0.0020, r * 0.86),
                (0.0025, r), (Lc - 0.0002, r * 0.965), (Lc, r * 0.94), (Lc, r * 0.86), (0.0040, r * 0.84),
                (0.0034, 0.0)]
        name = "SM_Weapon_CasingPistol"
    case = lathe(prof, 16 if kind == "rifle" else 20, name=name)
    parts = [P(case, BRASS, None)]
    pr = lathe([(-0.00005, 0.00035), (-0.00005, r * 0.40), (0.0004, r * 0.40), (0.0004, 0.0), (0.00025, 0.0)], 20)
    parts.append(P(pr, PRIMER, None))
    dent = lathe([(0.00025, 0.0), (0.00025, 0.00035), (-0.00005, 0.00035), (-0.00005, 0.0)], 12)
    parts.append(P(dent, PRIMER, None))
    ob = geo.join(parts, name)
    geo.transform(ob, loc=(-Lc / 2, 0, 0))
    return ob


def paint_casing(G, mouth_x):
    S = Surf(G, 303)
    p = S.p
    S.metal_finish(S.sel(BRASS), L["casing"], L["casing"] * 1.25, 0.24, 1.0, np.zeros(len(p), np.float32),
                   wear_amount=0.5, scratch=0.6, orange=0.2)
    S.metal_finish(S.sel(PRIMER), L["casing"] * np.array([0.92, 0.9, 0.86], np.float32), L["casing"], 0.30, 1.0,
                   np.zeros(len(p), np.float32), wear_amount=0.2, scratch=0.2)
    r = np.hypot(p[:, 1], p[:, 2])
    inner = (S.n[:, 1] * p[:, 1] + S.n[:, 2] * p[:, 2]) < -0.2 * np.maximum(r, 1e-6)
    soot = tp.smooth(p[:, 0], mouth_x - 0.008, mouth_x) * 0.75 + inner * 0.9
    tarnish = tp.smooth(S.N.fbm(p, 900.0, 3), 0.1, 0.6) * 0.35
    S.bc *= (1 - tarnish * 0.5)[:, None]
    S.rough += tarnish * 0.15
    S.grime(0.3, carbon=np.clip(soot, 0, 1))
    return S.channels()


def build_casings(ctx):
    out = []
    for kind, size, note in (("rifle", (0.039, 0.0114, 0.0114), "rifle case ejected by the CHOPPER"),
                             ("pistol", (0.0192, 0.0099, 0.0099), "9 mm case ejected by the NINE")):
        ob = casing(kind)
        scene.move_to(ob, ctx.col)
        res = tex_res(ctx, ob.name)
        unwrap(ob, res, angle=60.0)
        Lc = size[0]
        texture(ctx, ob, paint_casing, res, mouth_x=Lc / 2)
        geo.ensure_wear(ob)
        ctx.asset(ob, collision="none", expect_size=size, notes=(
            "Spent %s, real size (%.1f mm long, %.1f mm across; the web game draws it a third larger: scale the "
            "effect if wanted). Long axis +X, origin at the middle of the length, mouth toward +X, struck primer, "
            "scorched mouth. 20 sides (a few pixels on screen)." % (note, size[0] * 1000, size[1] * 1000)))
        out.append(ob)
    return out


# ==================================================================================================== ENEMY

def smg_parts():
    """The Goon's compact pistol-calibre SMG (generic, not a copy of any make). Origin at the firing hand on the
    pistol grip; bore axis 0.042 above it."""
    body, mag, lens = [], [], []
    B = 0.042
    # receiver: stamped box with a top cover seam, ejection port (right), cocking slot (left), rivets
    rec = prism([(-0.080, 0.000), (0.190, 0.000), (0.190, 0.064), (0.184, 0.072), (-0.074, 0.072), (-0.080, 0.066)],
                -0.023, 0.023, bevel=0.0012, seg=2, fillet=0.002, name="SMGRec")
    port = prism([(0.060, 0.040), (0.110, 0.040), (0.110, 0.060), (0.060, 0.060)], -0.04, -0.016, bevel=0, fillet=0.003)
    slot = box(-0.020, 0.120, 0.016, 0.04, 0.050, 0.056)
    seam = box(-0.09, 0.20, -0.0236, -0.0224, 0.0598, 0.0606)
    seam2 = box(-0.09, 0.20, 0.0224, 0.0236, 0.0598, 0.0606)
    cut(rec, port, slot, seam, seam2, box(0.065, 0.107, -0.0152, 0.0152, -0.01, 0.012))
    round_edges(rec, 0.0005, 2, 50)
    body.append(P(rec, BLUED, None))
    body.append(P(box(0.058, 0.116, -0.0186, -0.002, 0.041, 0.059, bevel=0.0008), BRIGHT, None))   # bolt in the port
    for s in (1, -1):
        for x, z in ((-0.070, 0.010), (-0.070, 0.058), (0.180, 0.010), (0.180, 0.058), (0.030, 0.008), (0.140, 0.008)):
            body.append(P(rivet((x, s * 0.023, z), "Y", r=0.0026, h=0.0009, sign=s, seg=12), BLUED, None))
    knob = lathe([(0.0, 0.0), (0.0, 0.0045), (0.008, 0.0050), (0.016, 0.0045), (0.018, 0.0)], 16, axis="Y",
                 at=(0.100, 0.023, 0.053), fillet=0.001)
    body.append(P(knob, DARK, None))
    # magazine well housing
    well = prism([(0.060, 0.002), (0.112, 0.002), (0.110, -0.030), (0.062, -0.030)], -0.0195, 0.0195, bevel=0.0012,
                 seg=2, fillet=0.002, name="Well")
    cut(well, box(0.0635, 0.1085, -0.0152, 0.0152, -0.05, 0.01))
    round_edges(well, 0.0005, 2, 50)
    body.append(P(well, BLUED, None))
    body.append(P(prism([(0.050, -0.010), (0.058, -0.010), (0.058, -0.022), (0.050, -0.022)], -0.006, 0.006,
                        bevel=0.0008, seg=2), POLYMER, None))   # magazine release paddle
    # handguard (polymer, slotted), barrel, muzzle device
    hg = prism([(-0.018, -0.023), (0.018, -0.023), (0.018, 0.023), (-0.018, 0.023)], 0.190, 0.340, axis="X",
               bevel=0.004, seg=3, name="Handguard")
    vents = []
    for s in (1, -1):
        for x in np.arange(0.212, 0.330, 0.022):
            vents.append(prism([(x - 0.007, 0.004), (x + 0.007, 0.004), (x + 0.007, 0.010), (x - 0.007, 0.010)],
                               s * 0.010, s * 0.03, bevel=0, fillet=0.0029))
    cut(hg, *vents)
    geo.transform(hg, loc=(0, 0, B))
    round_edges(hg, 0.0005, 2, 50)
    body.append(P(hg, POLYMER, None))
    body.append(P(lathe([(0.185, 0.0), (0.185, 0.0080), (0.335, 0.0080), (0.335, 0.0)], 32, at=(0, 0, B)), DARK, None))
    md = lathe([(0.330, 0.0040), (0.330, 0.0110), (0.333, 0.0120), (0.388, 0.0120), (0.390, 0.0112), (0.390, 0.0060),
                (0.333, 0.0040)], 40, closed=True, at=(0, 0, B), name="Muzzle")
    slots = [box(x - 0.003, x + 0.003, -0.02, 0.02, 0.006, 0.02) for x in (0.352, 0.364, 0.376)]
    for c in slots:
        geo.transform(c, loc=(0, 0, B))
    cut(md, *slots)
    body.append(P(md, BLUED, None))
    # top rail (0.07 long, top 0.09 above the origin) and a fixed front post
    rail = prism([(-0.0080, 0.0720), (0.0080, 0.0720), (0.0080, 0.0830), (0.0105, 0.0860), (0.0105, 0.0870),
                  (0.0080, 0.0900), (-0.0080, 0.0900), (-0.0105, 0.0870), (-0.0105, 0.0860), (-0.0080, 0.0830)],
                 0.040, 0.110, axis="X", bevel=0.0003, seg=1, name="Rail")
    cut(rail, *[box(x - 0.0026, x + 0.0026, -0.02, 0.02, 0.0855, 0.1) for x in np.arange(0.045, 0.110, 0.010)])
    body.append(P(rail, DARK, None))
    body.append(P(prism([(0.170, 0.072), (0.186, 0.072), (0.184, 0.086), (0.172, 0.086)], -0.006, 0.006,
                        bevel=0.0008, seg=2), DARK, None))
    # pistol grip (polymer, finger grooves, stippled in the normal map) and trigger guard + trigger
    g = [(-0.012, 0.002), (0.034, 0.002), (0.030, -0.020), (0.024, -0.034), (0.026, -0.046), (0.019, -0.060),
         (0.020, -0.072), (0.012, -0.092), (0.008, -0.100), (-0.028, -0.100), (-0.030, -0.090), (-0.022, -0.050)]
    grip = prism(g, -0.0145, 0.0145, bevel=0.007, seg=4, fillet=0.004, name="SMGGrip", corner=20)
    body.append(P(grip, POLYMER, None))
    tgd = geo.sweep(geo.fillet(geo.rect_profile(0.003, 0.010), 0.0008, 2, closed=True),
                    geo.fillet([(0.034, 0, 0.0), (0.036, 0, -0.030), (0.062, 0, -0.031), (0.060, 0, 0.0)], 0.007, 4),
                    up=(0, 1, 0), name="SMGGuard")
    body.append(P(fix_normals(tgd), POLYMER, None))
    body.append(P(prism([(0.040, 0.002), (0.046, 0.002), (0.047, -0.010), (0.044, -0.020), (0.041, -0.019),
                         (0.042, -0.010)], -0.003, 0.003, bevel=0.0007, seg=2), DARK, None))
    # fixed stock: strut (tube) with tape, butt plate 0.085 tall ending 0.25 behind the origin
    strut = geo.pipe([(-0.080, 0, 0.036), (-0.236, 0, 0.028)], radius=0.0085, segments=24, name="Strut")
    body.append(P(strut, BLUED, None))
    low = geo.pipe([(-0.080, 0, 0.008), (-0.236, 0, -0.004)], radius=0.0055, segments=20, name="Strut2")
    body.append(P(low, BLUED, None))
    bp = prism([(-0.250, -0.0125), (-0.236, -0.0125), (-0.236, 0.0725), (-0.250, 0.0725)], -0.020, 0.020, bevel=0.004,
               seg=3, fillet=0.006, name="Butt")
    body.append(P(bp, POLYMER, None))
    for k in range(5):
        x = -0.150 - k * 0.0105
        z = 0.036 + (x + 0.080) / (-0.156) * (0.028 - 0.036)
        t = lathe([(-0.0055, 0.0), (-0.0055, 0.0094), (0.0055, 0.0096), (0.0055, 0.0)], 24, at=(x, 0, z),
                  fillet=0.0004)
        geo.transform(t, loc=(0, 0, 0))
        body.append(P(t, TAPE, None))
    # weapon light under the handguard: housing 0.036 across, 0.075 long, lens 0.032 at X 0.32
    lh = lathe([(0.245, 0.0), (0.245, 0.0150), (0.250, 0.0180), (0.312, 0.0180), (0.320, 0.0172), (0.320, 0.0165),
                (0.318, 0.0160), (0.318, 0.0)], 40, at=(0, 0, -0.002), name="Light", fillet=0.001)
    body.append(P(lh, ALU, None))
    for x in (0.262, 0.270, 0.278, 0.286):
        body.append(P(lathe([(x - 0.002, 0.0), (x - 0.002, 0.0186), (x + 0.002, 0.0186), (x + 0.002, 0.0)], 40,
                            at=(0, 0, -0.002)), ALU, None))
    body.append(P(box(0.255, 0.305, -0.008, 0.008, 0.012, 0.020, bevel=0.002), ALU, None))
    ln = lathe([(0.3175, 0.0), (0.3175, 0.0160), (0.3185, 0.0158), (0.3190, 0.0)], 40, at=(0, 0, -0.002), name="Lens")
    lens.append(P(ln, LENS, None))
    # stick magazine (separate): 0.042 x 0.030 section, 0.17 long, hanging to 0.18 below the origin
    mg = prism([(0.0645, 0.010), (0.1075, 0.010), (0.1075, -0.172), (0.0645, -0.172)], -0.0150, 0.0150, bevel=0.0012,
               seg=2, fillet=0.002, name="SMGMag")
    for z in (-0.050, -0.090, -0.130):
        mg2 = box(0.062, 0.110, -0.0158, 0.0158, z - 0.002, z + 0.002, bevel=0.0007)
        union(mg, mg2)
    body_m = P(mg, POLYMER, None)
    fpl = P(box(0.062, 0.110, -0.0165, 0.0165, -0.180, -0.171, bevel=0.002), POLYMER, None)
    mag += [body_m, fpl]
    return body, mag, lens


def paint_smg(G):
    S = Surf(G, 404)
    p = S.p
    hand = np.clip(gauss(p, (0.0, 0, -0.05), 0.04, 0.8) + gauss(p, (0.17, 0, -0.012), 0.05, 0.8)
                   + gauss(p, (0.10, 0.023, 0.053), 0.03, 0.8) + tp.smooth(p[:, 2], -0.15, -0.18) * 0.7, 0, 1)
    S.metal_finish(S.sel(BLUED), L["smg"], L["chamfer"], 0.45, 0.80, hand, wear_amount=1.2)
    S.metal_finish(S.sel(DARK), L["smg2"], L["chamfer"], 0.48, 0.75, hand)
    S.metal_finish(S.sel(BRIGHT), L["bright"] * 0.8, L["bright"], 0.35, 1.0, hand, brushed=0.6)
    pol = S.sel(POLYMER)
    smg2 = pol & (((p[:, 0] > 0.185) & (p[:, 2] > 0.015)) | (p[:, 2] < -0.005) & (p[:, 0] > 0.05))
    S.plain(pol & ~smg2, L["smg"], 0.62, 0.0, var=0.06, scratch=0.6)
    S.plain(smg2, L["smg2"], 0.60, 0.0, var=0.06, scratch=0.6)
    stip = pol & (p[:, 2] < -0.005) & (p[:, 0] < 0.04)
    S.h += stip * 6e-5 * S.N.fbm(p, 4000.0, 2)
    S.metal_finish(S.sel(ALU), L["smg"] * 1.05, L["chamfer"] * 1.1, 0.42, 0.9, hand, wear_amount=1.0)
    S.plain(S.sel(TAPE), L["tape"], 0.55, 0.0, var=0.15)
    S.plain(S.sel(LENS), L["lens"], 0.08, 0.0, var=0.0, rvar=0.0)
    S.plain(S.sel(BORE), L["bore"], 0.6, 0.3)
    e = tp.smooth(p[:, 0], 0.375, 0.39) * 0.6
    S.grime(1.2, carbon=np.clip(e + gauss(p, (0.085, -0.023, 0.05), 0.03, 0.5) * (p[:, 1] < -0.01), 0, 1))
    return S.channels(height_blur=0.6)


def build_enemy(ctx):
    body, mparts, lens = smg_parts()
    for o in mparts:
        mark_piece(o, 1.0)
    for o in body + lens:
        mark_piece(o, 0.0)
    smg = geo.join(body + lens + mparts, "SM_Weapon_GoonSMG", ctx.col)
    res = tex_res(ctx, "SM_Weapon_GoonSMG")
    unwrap(smg, res)
    texture(ctx, smg, paint_smg, res)
    lens_m = bpy.data.materials.get("M_Weapon_GoonSMG_Lens") or mat.flat("M_Weapon_GoonSMG_Lens", tuple(L["lens"]), 0.08)
    smg.data.materials.append(lens_m)
    mid = np.empty(len(smg.data.polygons), np.float32)
    smg.data.attributes["mid"].data.foreach_get("value", mid)
    mi = np.where(np.rint(mid) == LENS, 1, 0).astype(np.int32)
    smg.data.polygons.foreach_set("material_index", mi)
    smg.data.update()
    magob = split_off(smg, None, "SM_Weapon_GoonSMG_Magazine", ctx.col)
    magob.data.materials.pop(index=1)                      # the lens slot stays on the gun only
    for o in (smg, magob):
        geo.ensure_wear(o)
    socks = {"Muzzle": (0.385, 0, 0.042), "Light": (0.318, 0, -0.002), "SupportHand": (0.17, 0, -0.012),
             "Butt": (-0.235, 0, 0.03)}
    ctx.asset(smg, collision="none", expect_size=(0.64, 0.05, 0.27 - 0.0), notes=(
        "The Goon's SMG (generic compact pistol-calibre SMG with a fixed stock and a weapon light). Origin at the "
        "firing hand on the pistol grip, barrel +X, bore 0.042 above the origin. Sockets (m): %s. Slot "
        "M_Weapon_GoonSMG (set Weapon_GoonSMG, 2K) and slot M_Weapon_GoonSMG_Lens on the light's lens: its own "
        "emissive material, off #2a1c10, lit linear (1, 0.74, 0.42) for 0.5 s before every burst. Magazine: "
        "SM_Weapon_GoonSMG_Magazine (same origin, same set). Lies on its side beside the body after a kill." %
        json.dumps(socks)))
    ctx.assets[smg.name]["expect_size"] = (0.64, 0.05, 0.188)
    ctx.asset(magob, collision="none", expect_size=(0.048, 0.033, 0.19), notes=(
        "The Goon SMG's stick magazine, a separate part in the gun's space (same origin and set)."))
    pipe = goon_pipe()
    scene.move_to(pipe, ctx.col)
    pres = tex_res(ctx, "SM_Weapon_GoonPipe")
    unwrap(pipe, pres, angle=60.0)
    texture(ctx, pipe, paint_pipe, pres)
    geo.ensure_wear(pipe)
    ctx.asset(pipe, collision="none", expect_size=(0.71, 0.05, 0.05), notes=(
        "The Goon's melee pipe: 1 inch galvanised pipe 0.70 m with a threaded coupling on the striking end (+X, 0.52..0.57 "
        "ahead of the origin) and black cloth tape on the grip end (0.115 behind .. 0.035 ahead). Origin at the "
        "centre of the fist."))
    return [smg, magob, pipe]


def goon_pipe():
    parts = []
    r, ri = 0.0168, 0.0133
    thread = []
    for x0, x1 in ((-0.140, -0.122), (0.505, 0.524)):
        for k in range(int((x1 - x0) / 0.0018)):
            thread.append(x0 + k * 0.0018)
    prof = [(-0.140, ri), (-0.140, r - 0.0006)]
    for x in thread:
        prof += [(x + 0.0004, r - 0.0003), (x + 0.0012, r - 0.0010)]
    prof += [(0.560, r), (0.560, ri)]
    body = lathe(prof, 20, closed=True, name="SM_Weapon_GoonPipe")
    parts.append(P(body, ZINC, None))
    cp = lathe([(0.520, 0.0170), (0.520, 0.0235), (0.522, 0.0250), (0.568, 0.0250), (0.570, 0.0235), (0.570, 0.0160),
                (0.565, 0.0150), (0.525, 0.0150)], 20, closed=True, name="Coupling")
    parts.append(P(cp, ZINC, None))
    tape = []
    for k in range(13):
        x = -0.115 + k * 0.0115
        tape.append((x + 0.0010, 0.0199))
        tape.append((x + 0.0112, 0.0193))
    tp_ = lathe([(-0.116, r - 0.0004)] + tape + [(0.0355, 0.0193), (0.036, r - 0.0004)], 16, name="Tape")
    parts.append(P(tp_, TAPE, None))
    return geo.join(parts, "SM_Weapon_GoonPipe")


def paint_pipe(G):
    S = Surf(G, 505)
    p = S.p
    z = S.sel(ZINC)
    S.metal_finish(z, L["zinc"], L["zinc"] * 1.25, 0.55, 0.85, np.zeros(len(p), np.float32), wear_amount=0.8)
    cell, d = S.N.cells(p[z], 0.008)
    S.bc[z] *= (0.85 + 0.3 * cell)[:, None]                  # zinc spangle
    S.rough[z] += 0.12 * (cell - 0.5)
    dents = tp.smooth(S.N.fbm(p[z], 30.0, 2), 0.45, 0.6)
    S.h[z] -= 1.5e-4 * dents
    rust = (tp.smooth(np.abs(p[:, 0] - 0.21), 0.33, 0.36) * z + tp.smooth(-p[:, 0], 0.125, 0.14) * z
            + (S.sel(ZINC) & (np.hypot(p[:, 1], p[:, 2]) < 0.015)) * 0.8)
    rust = np.clip(rust * (0.5 + 0.7 * S.N.fbm(p, 300.0, 3)), 0, 1)
    rc = hexlin("6a3a1e")
    S.bc = S.bc + (rc[None, :] - S.bc) * rust[:, None]
    S.rough = S.rough + (0.85 - S.rough) * rust
    S.metal = S.metal * (1 - rust)
    S.plain(S.sel(TAPE), L["tape"], 0.62, 0.0, var=0.2, rvar=0.08)
    S.grime(0.8)
    return S.channels()


# ================================================================================================ surfaces

COL = {"blued": "5a5e65", "chamfer": "9aa0a8", "cover": "53565c", "dark": "3c3e43", "bright": "b1b6bd",
       "wood": "55301c", "bore": "050506", "paint": "f2f0e4", "brass": "caa23d", "copper": "b5683a",
       "gold": "e7b53a", "stainless": "aeb1b6", "frame": "34363b", "frame_chamfer": "8a9098", "polymer": "1c1c1f",
       "polished": "bbbec4", "magbody": "45484e", "nine_mag": "9da1a7", "casing": "c9a24a", "zinc": "8f949c",
       "tape": "18181a", "smg": "24262c", "smg2": "34373f", "lens": "2a1c10", "soot": "0b0a09", "dust": "6d665b"}
L = {k: hexlin(v) for k, v in COL.items()}


def gauss(p, centre, radius, weight=1.0):
    d2 = ((p - np.asarray(centre, np.float32)) ** 2).sum(1) / (radius * radius)
    return weight * np.exp(-d2)


def rot_pts(p, axis, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    q = p.copy()
    i, j = {"X": (1, 2), "Y": (0, 2), "Z": (0, 1)}[axis]
    q[:, i] = c * p[:, i] - s * p[:, j]
    q[:, j] = s * p[:, i] + c * p[:, j]
    return q


class Surf:
    """Flat per-texel working set of one asset: geometry inputs and the channels being authored."""

    def __init__(self, G, seed):
        m = G["mask"]
        self.G, self.m = G, m
        self.p = G["pos"][m].astype(np.float32)
        self.n = G["nrm"][m].astype(np.float32)
        self.id = G["id"][m]
        self.part = G["part"][m].astype(np.float32)
        self.ao, self.cav, self.edge, self.convex = (G[k][m].astype(np.float32) for k in ("ao", "cav", "edge", "convex"))
        k = len(self.p)
        self.N = tp.Noise(seed)
        self.bc = np.zeros((k, 3), np.float32)
        self.rough = np.full(k, 0.5, np.float32)
        self.metal = np.zeros(k, np.float32)
        self.h = np.zeros(k, np.float32)
        self.emit = np.zeros((k, 3), np.float32)

    def sel(self, *ids):
        return np.isin(self.id, ids)

    def scratches(self, density=1.0, along="X", octave=0, cross=(30.0, -25.0), freq_long=35.0, freq_across=1600.0,
                  sel=None):
        """Fine scratches, mostly along the handling direction, a few at angles. Returns 0..1 (for sel only)."""
        N, p = self.N, (self.p if sel is None else self.p[sel])
        out = np.zeros(len(p), np.float32)
        fl = {"X": (freq_long, freq_across, freq_across), "Z": (freq_across, freq_across, freq_long),
              "Y": (freq_across, freq_long, freq_across)}[along]
        sets = [(p, fl, 1.0)] + [(rot_pts(p, "Y", a), fl, 0.5) for a in cross]
        for i, (q, f, w) in enumerate(sets):
            r = N.ridged(q, f, 2, octave0=octave + 3 * i)
            lines = tp.smooth(r, 0.955, 0.995)
            gate = tp.smooth(N.fbm(q, 45.0, 2, octave0=octave + 3 * i + 1), 0.30 - 0.15 * density, 0.62)
            out = np.maximum(out, lines * gate * w)
        return out

    def fingerprints(self, centres, size=0.009):
        """Oval whorls of finger oil (0..1) at the given (centre, normal axis) spots."""
        out = np.zeros(len(self.p), np.float32)
        for c, ax in centres:
            d = self.p - np.asarray(c, np.float32)
            i, j = {"X": (1, 2), "Y": (0, 2), "Z": (0, 1)}[ax]
            u, v = d[:, i] / size, d[:, j] / (size * 1.35)
            r = np.sqrt(u * u + v * v)
            ridges = 0.5 + 0.5 * np.sin(r * size / 0.00048 * 2 * math.pi + 2.0 * self.N.fbm(self.p, 300, 1))
            blob = np.clip(1 - r, 0, 1) ** 0.5
            out = np.maximum(out, blob * (0.35 + 0.65 * ridges) * (r < 1))
        return out

    def metal_finish(self, sel, base, chamfer, rough0, metal0, handling, wear_amount=1.0, scratch=1.0,
                     brushed=0.0, sheen=None, worn_metal=1.0, worn_rough=0.22, orange=1.0):
        """Steel with layered wear: base colour with macro mottling, edge wear to bright steel driven by the
        convex-edge mask broken up by noise and pushed by handling zones, fine directional scratches, polish
        where hands rub, oil sheen, dust in recesses (done separately)."""
        if not sel.any():
            return
        p, N = self.p[sel], self.N
        mac = N.fbm(p, 30.0, 3, octave0=1)
        mic = N.fbm(p, 700.0, 3, octave0=5)
        col = np.asarray(base)[None, :] * (1.0 + 0.10 * mac[:, None] + 0.04 * mic[:, None])
        col = col * (1.0 + np.array([-0.01, 0.0, 0.025], np.float32) * mac[:, None] * 4)       # hue drift of bluing
        hz = handling[sel]
        brk = N.fbm(p, 520.0, 3, octave0=9)
        e = self.convex[sel]
        brk2 = N.fbm(p, 90.0, 2, octave0=10)
        wear = tp.smooth(e * 1.25 * wear_amount + 0.42 * brk + 0.25 * brk2 + 0.55 * hz - 0.70, 0.0, 0.22)
        wear = np.maximum(wear, tp.smooth(self.edge[sel] * hz * 1.6 + 0.2 * brk - 0.55, 0.0, 0.25) * wear_amount)
        polish = np.clip(hz * (0.55 + 0.45 * N.fbm(p, 120.0, 2, octave0=12)), 0, 1)
        sc = self.scratches(scratch, sel=sel) if scratch > 0 else 0.0
        bright = np.asarray(chamfer)[None, :]
        c = col * (1 + 0.18 * polish[:, None])
        c = c + (bright - c) * np.clip(wear + 0.35 * sc, 0, 1)[:, None]
        r = rough0 + 0.07 * mac + 0.04 * mic - 0.10 * polish
        if brushed > 0:
            br = N.fbm(p, (6.0, 9000.0, 9000.0), 2, octave0=14)
            r = r + brushed * 0.08 * br
            c = c * (1 + brushed * 0.05 * br[:, None])
            self.h[sel] += brushed * 1.0e-6 * br
        r = r + (worn_rough - r) * wear - 0.12 * sc + 0.10 * sc * (mic > 0.3)
        if sheen is not None:
            oil = np.clip(sheen[sel] * (0.5 + 0.5 * N.fbm(p, 80.0, 2, octave0=17)), 0, 1)
            r = r - 0.16 * oil
        m = metal0 + (worn_metal - metal0) * wear
        self.bc[sel] = c
        self.rough[sel] = r
        self.metal[sel] = m
        pits = tp.smooth(N.fbm(p, 5200.0, 1, octave0=22), 0.55, 0.8)
        self.h[sel] += (-1.0e-5 * sc + 3.5e-6 * N.fbm(p, 2600.0, 2, octave0=20) * orange - 6.0e-6 * wear * brk
                        - 4.0e-6 * pits * orange)

    def wood_laminate(self, sel, base, ply_axis=2, ply=0.0016, grain_axis=0, handling=None):
        """Laminated wood: plies of alternating tone stacked along ply_axis (visible as stripes where the shape
        cuts through them and at the cut ends), grain along grain_axis, varnish with chips at the corners."""
        if not sel.any():
            return
        p, N = self.p[sel], self.N
        warp = 0.00022 * N.fbm(p, 60.0, 3, octave0=30)
        s = (p[:, ply_axis] + warp) / ply
        k = np.floor(s)
        f = s - k
        rnd = self.N.vals[(k.astype(np.int64) * 37 + 11) & 255]
        tone = 0.80 + 0.40 * rnd * (1.0 if True else 0)
        tone = np.where((k.astype(np.int64) & 1) == 0, tone * 0.91, tone * 1.04)
        glue = tp.smooth(0.07 - np.minimum(f, 1 - f), 0.0, 0.05)
        fr = [2200.0, 2200.0, 2200.0]
        fr[grain_axis] = 25.0
        grain = N.fbm(p + warp[:, None] * 6, tuple(fr), 3, octave0=33)
        pores = tp.smooth(N.ridged(p, tuple(v * 1.7 for v in fr), 1, octave0=36), 0.93, 0.99)
        col = np.asarray(base)[None, :] * tone[:, None] * (1 + 0.22 * grain[:, None])
        col = col * (1 - 0.30 * glue[:, None]) * (1 - 0.25 * pores[:, None])
        e = self.convex[sel]
        brk = N.fbm(p, 380.0, 3, octave0=40)
        hz = handling[sel] if handling is not None else 0.0
        chip = tp.smooth(e * 1.35 + 0.45 * brk + 0.3 * hz - 0.78, 0.0, 0.12)
        raw = col * np.array([1.55, 1.45, 1.35], np.float32)
        col = col + (raw - col) * chip[:, None]
        r = 0.30 + 0.05 * N.fbm(p, 150.0, 2, octave0=43) + 0.08 * pores
        r = r + (0.72 - r) * chip - 0.06 * hz
        col = col * (1 - 0.18 * hz)[:, None] if handling is not None else col
        self.bc[sel] = col
        self.rough[sel] = r
        self.metal[sel] = 0.0
        self.h[sel] += -3e-5 * pores + 8e-6 * grain - 6e-5 * chip * (0.5 + 0.5 * brk) + 2.5e-6 * N.fbm(p, 3000.0, 1, octave0=46)

    def plain(self, sel, base, rough, metal, var=0.06, rvar=0.05, scratch=0.0):
        if not sel.any():
            return
        p = self.p[sel]
        v = self.N.fbm(p, 200.0, 3, octave0=50)
        self.bc[sel] = np.asarray(base)[None, :] * (1 + var * v[:, None])
        self.rough[sel] = rough + rvar * v
        self.metal[sel] = metal
        if scratch:
            sc = self.scratches(scratch, sel=sel)
            self.rough[sel] -= 0.1 * sc
            self.h[sel] += -2e-6 * sc

    def grime(self, amount=1.0, carbon=None, dust_col=None):
        """Dust and dried oil in the recesses (short-range occlusion), carbon where given (0..1 per texel)."""
        p, N = self.p, self.N
        g = tp.smooth(1.0 - self.cav, 0.10, 0.55) * 0.8 + tp.smooth(1.0 - self.ao, 0.25, 0.85) * 0.45
        g = np.clip(g * (0.55 + 0.6 * N.fbm(p, 220.0, 3, octave0=60)) * amount, 0, 1)
        dc = np.asarray(dust_col if dust_col is not None else L["dust"])
        self.bc = self.bc + (dc[None, :] * 0.55 - self.bc) * (g * 0.75)[:, None]
        self.rough = self.rough + (0.85 - self.rough) * g * 0.8
        self.metal = self.metal * (1 - 0.7 * g)
        if carbon is not None:
            c = np.clip(carbon * (0.65 + 0.5 * N.fbm(p, 400.0, 3, octave0=63)), 0, 1)
            self.bc = self.bc + (L["soot"][None, :] - self.bc) * c[:, None]
            self.rough = self.rough + (0.72 - self.rough) * c
            self.metal = self.metal * (1 - 0.75 * c)

    def dots(self, centres, radius, facing, colour=L["paint"], emit=0.35, depth=2e-5):
        """Painted sight dots / strips: centres = [(x, y, z)], facing = axis sign string like '-X'; a texel is
        painted when it faces that way and lies within radius (number, or (r_a, r_b) half sizes) of a centre."""
        ax = "XYZ".index(facing[-1])
        sg = -1.0 if facing[0] == "-" else 1.0
        ok = self.n[:, ax] * sg > 0.6
        others = [i for i in range(3) if i != ax]
        out = np.zeros(len(self.p), np.float32)
        for c in centres:
            d = self.p - np.asarray(c, np.float32)
            if np.isscalar(radius):
                rr = np.sqrt(d[:, others[0]] ** 2 + d[:, others[1]] ** 2) / radius
            else:
                rr = np.maximum(np.abs(d[:, others[0]]) / radius[0], np.abs(d[:, others[1]]) / radius[1])
            out = np.maximum(out, tp.smooth(1.0 - rr, 0.0, 0.12) * ok * (np.abs(d[:, ax]) < 0.0015))
        sel = out > 0
        self.bc[sel] = self.bc[sel] * (1 - out[sel, None]) + colour[None, :] * out[sel, None]
        self.rough[sel] = self.rough[sel] * (1 - out[sel]) + 0.55 * out[sel]
        self.metal[sel] = self.metal[sel] * (1 - out[sel])
        self.emit[sel] = colour[None, :] * emit * out[sel, None]
        self.h[sel] += depth * out[sel]

    def engrave(self, img, axes, origin, size, facing, depth=8e-5):
        """Stamped or engraved markings from a 2D mask laid on a plane (texpaint.raster_plane)."""
        ax = "XYZ".index(facing[-1])
        sg = -1.0 if facing[0] == "-" else 1.0
        v = tp.raster_plane(img, self.p, axes, origin, size) * (self.n[:, ax] * sg > 0.7)
        self.h -= depth * v
        self.bc *= (1 - 0.45 * v)[:, None]
        self.rough += 0.15 * v
        return v

    def channels(self, height_blur=0.0):
        G, m = self.G, self.m
        h = tp.scatter(m, self.h)
        if height_blur:
            h = tp.blur(h, height_blur, m)
        nrm = tp.tangent_normal(h, G)
        ao = np.clip(G["ao"] * (0.55 + 0.45 * G["cav"]), 0, 1).astype(np.float32)
        ch = {"bc": tp.scatter(m, np.clip(self.bc, 0, 1)), "rough": tp.scatter(m, np.clip(self.rough, 0.04, 1.0)),
              "metal": tp.scatter(m, np.clip(self.metal, 0, 1)), "ao": ao, "normal": nrm,
              "emit": tp.scatter(m, self.emit) if self.emit.max() > 0 else None}
        return tp.finish(ch, G)


def paint_chopper(G):
    S = Surf(G, 101)
    p = S.p
    hand = (gauss(p, (0.045, 0, -0.030), 0.030, 0.8) + gauss(p, (0.192, 0, -0.040), 0.022, 0.9)
            + gauss(p, (0.150, 0.017, 0.012), 0.040, 0.6) + gauss(p, (0.100, 0.020, 0.002), 0.018, 0.9)
            + gauss(p, (0.409, 0, 0.060), 0.012, 0.9) + gauss(p, (0.492, 0, 0.0), 0.016, 0.8)
            + gauss(p, (0.315, 0, -0.0615), 0.045, 0.7) + gauss(p, (0.130, 0, -0.045), 0.06, 0.35)
            + gauss(p, (0.409, 0.011, -0.0105), 0.012, 0.9) + gauss(p, (0.004, 0.018, -0.045), 0.012, 0.9)
            + gauss(p, (0.0, 0, 0.0), 0.02, 0.5) + gauss(p, (0.130, 0.019, -0.040), 0.05, 0.5)
            + gauss(p, (0.180, 0.036, 0.0145), 0.010, 1.0))
    hand = np.clip(hand, 0, 1)
    oil = gauss(p, (0.150, -0.012, 0.012), 0.035, 1.0) + gauss(p, (0.30, 0, 0.0), 0.06, 0.4)
    S.metal_finish(S.sel(BLUED), L["blued"], L["chamfer"], 0.40, 0.88, hand, sheen=oil)
    S.metal_finish(S.sel(COVER), L["cover"], L["chamfer"], 0.43, 0.88, hand, sheen=oil)
    S.metal_finish(S.sel(DARK), L["dark"], L["chamfer"], 0.48, 0.80, hand, wear_amount=0.8, scratch=0.6)
    S.metal_finish(S.sel(BRIGHT), L["bright"], L["bright"] * 1.15, 0.30, 1.0, hand, wear_amount=0.3, brushed=1.0,
                   sheen=oil * 1.5, worn_rough=0.2)
    grip = S.sel(WOOD) & (p[:, 2] < -0.03) & (p[:, 0] < 0.09)
    S.wood_laminate(grip, L["wood"], ply_axis=1, grain_axis=2, handling=gauss(p, (0.035, 0, -0.09), 0.05, 0.7))
    S.wood_laminate(S.sel(WOOD) & ~grip, L["wood"], ply_axis=2, grain_axis=0,
                    handling=gauss(p, (0.315, 0, -0.04), 0.05, 0.6))
    S.plain(S.sel(BORE), L["bore"], 0.6, 0.4)
    S.plain(S.sel(BRASS), L["brass"], 0.3, 1.0)
    # carbon: inside and at the mouth of the booster, the gas block front, round the ejection port
    r = np.sqrt(p[:, 1] ** 2 + p[:, 2] ** 2)
    carbon = tp.smooth(p[:, 0], 0.470, 0.4975) * 0.45 + ((p[:, 0] > 0.428) & (r < 0.0125) & (S.n[:, 0] * 0 + 1 > 0)
                                                         & (np.abs(S.n[:, 1] * p[:, 1] + S.n[:, 2] * p[:, 2]) / np.maximum(r, 1e-6) > 0.3)
                                                         & ((S.n[:, 1] * p[:, 1] + S.n[:, 2] * p[:, 2]) < 0)) * 0.95
    port = gauss(p, (0.150, -0.017, 0.010), 0.03, 0.55) * (p[:, 1] < -0.012) + gauss(p, (0.200, -0.010, 0.008), 0.02, 0.4) * S.sel(BRIGHT)
    S.grime(1.0, carbon=np.clip(carbon + port, 0, 1))
    # sight paint (faintly self-lit): two dots on the rear leaf, a strip on the rear face of the front post
    S.dots([(0.0215, 0.0046, 0.0498), (0.0215, -0.0046, 0.0498)], 0.00095, "-X")
    S.dots([(0.4080, 0.0, 0.0527)], (0.00072, 0.0027), "-X")
    # stamped markings: selector positions beside the lever's tab, a fictional proof mark on the trunnion
    img = tp.text_image([("S", 128, 70, 120), ("A", 128, 250, 120), ("1", 128, 430, 120)], 512)
    S.engrave(img, (0, 2), (0.1075, -0.0215), (0.0105, 0.0315), "+Y", 6e-5)
    pm = tp.text_image([("✶", 256, 256, 330)], 512)
    S.engrave(pm, (0, 2), (0.2195, -0.0125), (0.0085, 0.0085), "+Y", 5e-5)
    sn = tp.text_image([("MI-87", 256, 256, 140)], 512)
    S.engrave(sn, (0, 2), (0.204, -0.0072), (0.024, 0.024), "+Y", 4e-5)
    # knurled charging knob
    kn = S.sel(DARK) & (p[:, 1] > 0.031) & (np.abs(p[:, 0] - 0.180) < 0.008) & (np.abs(p[:, 2] - 0.0145) < 0.008)
    ang = np.arctan2(p[:, 2] - 0.0145, p[:, 0] - 0.180)
    knurl = (np.sin(ang * 36 + p[:, 1] / 0.0007 * 2 * math.pi) * np.sin(ang * 36 - p[:, 1] / 0.0007 * 2 * math.pi))
    S.h += kn * 2.5e-5 * knurl
    return S.channels(height_blur=0.6)


def paint_magazine(G, body_col, floor_col, seed=7, bright_body=False):
    S = Surf(G, seed)
    p = S.p
    hand = np.clip(gauss(p, (0.30, 0, -0.20), 0.05, 0.7) + tp.smooth(-p[:, 2], 0.15, 0.23) * 0.6
                   + gauss(p, (0.19, 0, -0.03), 0.03, 0.6), 0, 1)
    if bright_body:
        S.metal_finish(S.sel(BLUED), body_col, body_col * 1.2, 0.30, 1.0, hand, brushed=0.8, wear_amount=0.5)
    else:
        S.metal_finish(S.sel(BLUED), body_col, L["chamfer"], 0.45, 0.85, hand)
    S.metal_finish(S.sel(DARK), floor_col, L["chamfer"], 0.47, 0.82, hand)
    S.plain(S.sel(BORE), L["bore"], 0.7, 0.3)
    brass = S.sel(BRASS)
    S.metal_finish(brass, L["brass"], L["brass"] * 1.25, 0.26, 1.0, hand * 0, wear_amount=0.4, scratch=0.5, orange=0.3)
    S.metal_finish(S.sel(COPPER), L["copper"], L["copper"] * 1.2, 0.28, 1.0, hand * 0, wear_amount=0.3, scratch=0.3)
    S.plain(S.sel(PRIMER), L["brass"] * np.array([0.95, 0.9, 0.85], np.float32), 0.32, 1.0)
    S.plain(S.sel(GOLD), L["gold"], 0.16, 1.0, var=0.03, rvar=0.03, scratch=0.4)
    S.grime(0.8)
    return S.channels(height_blur=0.5)


def paint_nine(G):
    S = Surf(G, 202)
    p, n = S.p, S.n
    holster = np.clip(tp.smooth(p[:, 0], 0.150, 0.200) * 0.8 + gauss(p, (0.110, 0, -0.070), 0.03, 0.8)
                      + gauss(p, (-0.030, 0, -0.012), 0.015, 0.8) + gauss(p, (0.180, 0, -0.024), 0.03, 0.6)
                      + gauss(p, (0.030, 0, 0.010), 0.03, 0.5) + gauss(p, (0.012, 0, -0.125), 0.04, 0.5)
                      + gauss(p, (0.064, 0.015, -0.016), 0.01, 0.9), 0, 1)
    oil = gauss(p, (0.105, -0.010, 0.010), 0.03, 1.0) + gauss(p, (0.10, 0, -0.012), 0.08, 0.5)
    S.metal_finish(S.sel(STAINLESS), L["stainless"], L["stainless"] * 1.18, 0.30, 1.0, holster, wear_amount=0.7,
                   brushed=1.6, sheen=oil, worn_rough=0.16, orange=0.2)
    fp = S.fingerprints([((0.050, 0.0135, 0.000), "Y"), ((0.140, -0.0135, -0.002), "Y"), ((0.160, 0.0135, 0.001), "Y")], 0.008)
    S.rough -= 0.14 * fp * S.sel(STAINLESS)
    S.metal_finish(S.sel(BLACKOX), L["frame"], L["frame_chamfer"], 0.46, 0.80, holster, wear_amount=1.1, sheen=oil)
    S.metal_finish(S.sel(DARK), L["dark"], L["frame_chamfer"], 0.48, 0.80, holster, wear_amount=0.8, scratch=0.5)
    S.metal_finish(S.sel(POLISHED), L["polished"], L["polished"] * 1.1, 0.14, 1.0, holster * 0.5, wear_amount=0.2,
                   scratch=0.8, orange=0.1)
    S.metal_finish(S.sel(GOLD), L["gold"], L["gold"] * 1.12, 0.15, 1.0, holster * 0, wear_amount=0.4, scratch=0.5,
                   orange=0.1)
    pol = S.sel(POLYMER)
    S.plain(pol, L["polymer"], 0.58, 0.0, var=0.05, rvar=0.04)
    # checkering: 1.25 mm pyramids on the diagonals of the grip's rake, only on the flat of the panel
    ang = math.radians(15.0)
    u = p[:, 0] * math.cos(ang) + p[:, 2] * math.sin(ang)
    v = -p[:, 0] * math.sin(ang) + p[:, 2] * math.cos(ang)
    pitch = 0.00125
    a1, a2 = (u + v) / pitch, (u - v) / pitch
    tri = (np.abs(a1 - np.floor(a1) - 0.5) + np.abs(a2 - np.floor(a2) - 0.5))
    flat = pol & (np.abs(n[:, 1]) > 0.88)
    screws = np.minimum(np.hypot(p[:, 0] - 0.0365, p[:, 2] + 0.0530), np.hypot(p[:, 0] + 0.0090, p[:, 2] + 0.1130))
    flat &= screws > 0.0052
    S.h += flat * (-tri * 2.6e-4)
    tips = flat * tp.smooth(0.25 - tri, 0.0, 0.2)
    S.rough -= 0.20 * tips * (0.5 + 0.5 * S.N.fbm(p, 200.0, 2))
    S.bc[flat] *= (1.0 + 0.6 * tips[flat])[:, None]
    S.plain(S.sel(BORE), L["bore"], 0.6, 0.4)
    # serrations on the gold trigger's face and the hammer spur
    trg = S.sel(GOLD) & (n[:, 0] > 0.5)
    S.h += trg * 4e-5 * np.sin(p[:, 2] / 0.0009 * 2 * math.pi)
    spur = S.sel(DARK) & (p[:, 0] < -0.018) & (p[:, 2] > 0.004)
    S.h += spur * 6e-5 * np.sin((p[:, 0] * 0.6 - p[:, 2] * 0.8) / 0.0008 * 2 * math.pi)
    btn = S.sel(DARK) & (p[:, 1] > 0.0125) & (np.hypot(p[:, 0] - 0.0625, p[:, 2] + 0.0405) < 0.0046)
    S.h += btn * 3e-5 * np.sign(np.sin(p[:, 0] / 0.0007 * math.pi) * np.sin(p[:, 2] / 0.0007 * math.pi))
    carbon = (tp.smooth(p[:, 0], 0.196, 0.2012) * S.sel(POLISHED) * (np.hypot(p[:, 1], p[:, 2]) < 0.0065) * 0.9
              + gauss(p, (0.105, -0.012, 0.010), 0.02, 0.45) * (p[:, 1] < -0.004)
              + gauss(p, (0.0055, 0, 0.0), 0.006, 0.7) * S.sel(STAINLESS))
    S.grime(0.8, carbon=np.clip(carbon, 0, 1))
    S.dots([(0.0060, 0.0045, 0.0160), (0.0060, -0.0045, 0.0160)], 0.00085, "-X")
    S.dots([(0.1832, 0.0, 0.0158)], 0.00080, "-X")
    hood = tp.text_image([("9×19  ✶", 256, 256, 120)], 512)
    S.engrave(hood, (0, 1), (0.0800, -0.018), (0.036, 0.036), "+Z", 3e-5)
    pm = tp.text_image([("✶ HL", 256, 256, 150)], 512)
    S.engrave(pm, (0, 2), (0.106, -0.036), (0.016, 0.016), "+Y", 4e-5)
    return S.channels(height_blur=0.5)


# ================================================================================================ pipeline

SKINNED = {}
TEX = {"SK_Chopper": 4096, "SK_Nine": 4096, "SM_Weapon_ChopperMagazine": 2048, "SM_Weapon_NineMagazine": 2048,
       "SM_Weapon_GoonSMG": 2048, "SM_Weapon_GoonPipe": 1024, "SM_Weapon_CasingRifle": 512,
       "SM_Weapon_CasingPistol": 512}


def set_name_of(ob_name):
    return ob_name.split("_", 1)[1] if ob_name.startswith("SK_") else ob_name.replace("SM_", "", 1)


def tex_res(ctx, name):
    full = TEX[name]
    return full if ctx.args.res >= 2048 else max(128, full * ctx.args.res // 4096)


def unwrap(ob, res, low=(BORE,), low_w=0.35, angle=52.0):
    mid = np.empty(len(ob.data.polygons), np.float32)
    ob.data.attributes["mid"].data.foreach_get("value", mid)
    w = np.where(np.isin(np.rint(mid), low), low_w, 1.0)
    return geo.uv_unwrap(ob, res=res, angle=angle, margin_px=6, pack="AABB", weights=w)


def texture(ctx, ob, painter, res, set_name=None, **kw):
    """Bake the geometry maps, author the channels, write the set (only with --bake or when the set is missing
    or stale), then give the object its baked material M_<Set>."""
    set_name = set_name or set_name_of(ob.name)
    d = paths.texture_set(set_name)
    old = bake.read_set(set_name)
    stale = not old or old.get("uv_hash") != geo.uv_hash(ob) or old.get("resolution", [0])[0] != res
    if ctx.args.bake and (stale or ctx.args.force or ctx.args.rebake_unique) or not old:
        ctx.log("texture %s at %d px" % (set_name, res))
        G = tp.geometry_maps(ob, res=res, samples=8 if res >= 2048 else 16)
        ch = painter(G, **kw)
        dens = geo.uv_texel_density(ob, res)
        bake.write_set(set_name, ch, meta={"kind": "unique", "asset": ob.name, "uv_hash": geo.uv_hash(ob),
                                           "texel_density_px_per_m": round(dens, 1),
                                           "authoring": "mi.texpaint: geometry maps + numpy layers (assets/weapons.py)"})
        ctx.log("  wrote %s (%.0f px/m)" % (d, dens))
    elif stale:
        ctx.log("WARNING %s: set is stale (mesh changed); run with --bake" % set_name)
    m = mat.from_texture_set(d, name="M_" + set_name, masks=False, macro=0.0, ao_strength=0.0, alpha="none")
    ob.data.materials.clear()
    ob.data.materials.append(m)
    if set_name not in ctx.sets:
        ctx.sets.append(set_name)
    return m


def split_off(ob, sel_fn, name, col):
    """Copy the faces for which sel_fn(mid array, centre array) is True into a new object; delete them from ob."""
    me = ob.data
    n = len(me.polygons)
    mid = np.empty(n, np.float32)
    me.attributes["piece"].data.foreach_get("value", mid)
    take = mid > 0.5
    cp = ob.copy()
    cp.data = me.copy()
    col.objects.link(cp)
    for o, keep in ((cp, take), (ob, ~take)):
        bm = geo.bm_of(o)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(~keep)[0]], context="FACES")
        geo.bm_to(o, bm)
    cp.name = cp.data.name = name
    return cp


def mark_piece(ob, value=1.0):
    me = ob.data
    a = me.attributes.get("piece") or me.attributes.new("piece", "FLOAT", "FACE")
    a.data.foreach_set("value", np.full(len(me.polygons), value, np.float32))
    return ob


def build_chopper(ctx):
    res = tex_res(ctx, "SK_Chopper")

    def finish(ob, set_name):
        # one unique 4K set per piece: receiver and rear (the eye is 16 cm away when aimed), furniture, front end
        dens = geo.uv_unwrap(ob, res=res, angle=52.0, margin_px=6, pack="CONVEX",
                             weights=CH9.uv_weights(ob))
        ctx.log("%s: %d tris, %.0f px/m" % (set_name, geo.stats(ob)["triangles"], dens))
        texture(ctx, ob, TX.paint_chopper, res, set_name=set_name)
    gun, arm = CH9.chopper_build(ctx, finish)
    ctx.log("SK_Chopper: %d tris, %d slots" % (geo.stats(gun)["triangles"], len(gun.material_slots)))
    geo.ensure_wear(gun)
    SKINNED["SK_Chopper"] = {"ob": gun, "arm": arm, "expect_size": (0.502, 0.065, None), "poses": chopper_poses(),
                             "notes": CHOPPER_NOTES}
    body, top = CH9.chopper_magazine(ctx.col)
    mark_piece(body, 0.0)
    mark_piece(top, 1.0)
    mag = geo.join([body, top], "SM_Weapon_ChopperMagazine", ctx.col)
    mres = tex_res(ctx, "SM_Weapon_ChopperMagazine")
    unwrap(mag, mres)
    texture(ctx, mag, TX.paint_chopper_mag, mres)
    top = split_off(mag, None, "SM_Weapon_ChopperMagazine_TopRound", ctx.col)
    for o in (mag, top):
        geo.ensure_wear(o)
    ctx.asset(mag, collision="none", expect_size=(0.152, 0.027, 0.208), notes=CHOPPER_MAG_NOTES)
    ctx.asset(top, collision="none", expect_size=None, notes=(
        "The CHOPPER magazine's visible top round, a separate hideable piece: shares the magazine's set "
        "(slot M_Weapon_ChopperMagazine). Origin = gun origin; case X 0.172..0.222, 19.5 mm below the bore, "
        "4.2 mm left of centre (double stack)."))
    return [gun, arm, mag, top]


def chopper_poses():
    t, hz = CH["travel"], CH["hinge"]
    return [{"name": "bolt back by its travel", "bones": {"bolt": {"translate": (-t, 0, 0)}}},
            {"name": "trigger pulled", "bones": {"trigger": {"rotate": ((0, 1, 0), CH["trigger_deg"])}}},
            {"name": "selector to semi", "bones": {"selector": {"rotate": ((0, 1, 0), 14.0)}}},
            {"name": "magazine rocked out", "bones": {"magazine": {"rotate": ((0, 1, 0), -CH["mag_deg"]), "pivot": hz}}}]


CHOPPER_NOTES = (
    "Player weapon 1, skinned. Bones (rest orientation = gun axes: local X along the bore, Z up, Y left): body "
    "(root, origin on the bore axis at the back of the receiver), bolt (carrier + charging handle, head at the "
    "knob X 0.180 Z 0.0145; slides 0.092 back along -X), trigger (pivot X 0.108 Z -0.038; pull = +19.5 deg about "
    "+Y), selector (left side, pivot X 0.012 Z -0.004; safe at rest, about +7 / +14 deg about +Y for auto / "
    "semi, marked S A 1), magazine (attach bone at the gun origin: parent SM_Weapon_ChopperMagazine to it; "
    "rocks -24 deg about +Y through the socket MagHinge). Sockets: Muzzle, Eject, SightRear, SightFront, "
    "RecoilPivot, MagHinge, Palm_R, Palm_L (brief positions). Three slots, each a unique 4K set: M_Chopper (set "
    "Chopper: receiver, cover, rear sight, bolt, trigger group, hinge; E = sight paint), M_Chopper_Furniture (set "
    "Chopper_Furniture: laminated handguards and grip), M_Chopper_Front (set Chopper_Front: sight block, barrel, gas "
    "block, booster, band, liners, stock arms and shoulder piece).")
CHOPPER_MAG_NOTES = (
    "CHOPPER 30-round magazine (stamped steel, side ribs, spine, four cross ribs, feed lips, floor plate) with "
    "the second round of the stack; origin = gun origin (in place X 0.160..0.312, Z -0.229..-0.021). Hinge for "
    "the reload: the gun's socket MagHinge (X 0.222, Z -0.040), 24 deg. Top round: SM_Weapon_ChopperMagazine_TopRound.")


def build_nine(ctx):
    gun, arm = N9.nine_build(ctx)
    res = tex_res(ctx, "SK_Nine")
    dens = unwrap(gun, res)
    ctx.log("SK_Nine: %d tris, %.0f px/m" % (geo.stats(gun)["triangles"], dens))
    texture(ctx, gun, TX.paint_nine, res)
    geo.ensure_wear(gun)
    SKINNED["SK_Nine"] = {"ob": gun, "arm": arm, "expect_size": (0.234, 0.031, 0.153), "poses": nine_poses(),
                          "notes": NINE_NOTES}
    body, top = N9.nine_magazine(ctx.col)
    mark_piece(body, 0.0)
    mark_piece(top, 1.0)
    mag = geo.join([body, top], "SM_Weapon_NineMagazine", ctx.col)
    mres = tex_res(ctx, "SM_Weapon_NineMagazine")
    unwrap(mag, mres)
    texture(ctx, mag, TX.paint_nine_mag, mres)
    top = split_off(mag, None, "SM_Weapon_NineMagazine_TopRound", ctx.col)
    for o in (mag, top):
        geo.ensure_wear(o)
    ctx.asset(mag, collision="none", expect_size=(0.074, 0.026, 0.098), notes=(
        "NINE 15-round magazine: brushed steel body raked with the grip, three witness holes per side (the stack "
        "shows through), feed lips, flat polished gold base pad following the butt (1 mm overhang, flared finger lip). "
        "Origin = pistol origin (in place X -0.034..0.033, Z -0.1345..-0.033: rebuild round 1 moved the magazine "
        "line 12 mm back so the grip is 52 mm deep; direction unchanged); it slides along (X 0.250, Z 0.968), base "
        "to lips. Top round: SM_Weapon_NineMagazine_TopRound."))
    ctx.asset(top, collision="none", expect_size=None, notes=(
        "The NINE magazine's visible top round, a separate hideable piece sharing the magazine's set; origin = "
        "pistol origin, 33.5 mm below the bore axis."))
    return [gun, arm, mag, top]


def nine_poses():
    a = np.array(NN["mag_axis"]) / np.linalg.norm(NN["mag_axis"])
    return [{"name": "slide locked back", "bones": {"slide": {"translate": (-NN["travel"], 0, 0)},
                                                     "slide_stop": {"rotate": ((0, 1, 0), NN["stop_deg"])}}},
            {"name": "barrel tilted", "bones": {"barrel": {"rotate": ((0, 1, 0), NN["barrel_deg"])}}},
            {"name": "hammer down", "bones": {"hammer": {"rotate": ((0, 1, 0), NN["hammer_down_deg"])}}},
            {"name": "trigger pulled", "bones": {"trigger": {"rotate": ((0, 1, 0), NN["trigger_deg"])}}},
            {"name": "magazine dropped 60 mm", "bones": {"magazine": {"translate": tuple(-0.06 * a)}}}]


NINE_NOTES = (
    "Player weapon 2, skinned. Bones (rest orientation = gun axes: local X along the bore, Z up, Y left): frame "
    "(root, origin on the bore axis at the back face of the slide), slide (head at the origin; travels 0.044 back "
    "along -X, locks back), barrel (pivot = the lug X 0.070 Z -0.008; unlock tilt +2.3 deg about +Y, nose down), "
    "trigger (pivot X 0.091 Z -0.031; pull = +17 deg about +Y), hammer (cocked at rest; pivot X -0.0135 Z -0.0105, "
    "down = +36 deg about +Y), slide_stop (left; pivot X 0.0955 Z -0.0165, up = +7 deg about +Y), magazine "
    "(attach bone at the origin for SM_Weapon_NineMagazine; it slides along (0.250, 0, 0.968)). Sockets: Muzzle, "
    "Eject, SightRear, SightFront, RecoilPivot, Palm_R, Palm_L (support hand over the firing hand's fingers). "
    "Grip panels are modelled shells (3.4 mm crown) with 1.3 mm pyramid checkering in the normal map; front and back "
    "straps stippled. One slot M_Nine, set Nine (4K, E = sight dots).")


def build(ctx):
    only = [o.lower() for o in (ctx.args.only or GROUPS)]
    objs = []
    if "chopper" in only:
        objs += build_chopper(ctx)
    if "nine" in only:
        objs += build_nine(ctx)
    if "casings" in only:
        objs += build_casings(ctx)
    if "enemy" in only:
        objs += build_enemy(ctx)
    return objs


def on_export(ctx, objs):
    for name, a in ctx.assets.items():
        export.export_asset(a["ob"], ctx.family, a["collision"], a["cover_height"], a["notes"], a["pivot"],
                            a["expect_size"], slots=a["slots"])
    for name, s in SKINNED.items():
        ob, arm = s["ob"], s["arm"]
        err, warn = rig.validate(ob, arm, s["expect_size"])
        for w in warn:
            print("    warning %s: %s" % (name, w))
        if err:
            raise ValueError("%s failed validation:\n  %s" % (name, "\n  ".join(err)))
        path = rig.export_skinned(ob, arm)
        rep = rig.verify(path, s["poses"])
        ok = rep["ok"] and rep["glb"]["all_axes_are_asset_axes"]
        ctx.log("%s: %s, poses %s, joint axes = gun axes: %s" % (
            name, os.path.relpath(path, paths.art), ", ".join("%s %.1e m" % (p["name"], p["max_error_m"]) for p in rep["poses"]),
            rep["glb"]["all_axes_are_asset_axes"]))
        if not ok:
            raise ValueError("%s: re-import proof failed: %s" % (name, json.dumps(rep)[:2000]))
        sockets = {b.name: [round(v, 5) for v in b.head_local] for b in arm.data.bones if not b.use_deform}
        slots = {}
        for m in ob.data.materials:
            if m is None:
                continue
            meta = bake.read_set(m.name[2:]) or {}
            dens = meta.get("texel_density_px_per_m")
            slots[m.name] = {"detail_set": TX.DETAIL_SET, "detail_tile_m": TX.DETAIL_TILE_M,
                             "detail_repeat_per_uv": round(4096.0 / dens / TX.DETAIL_TILE_M, 2) if dens else None}
        entry = rig.manifest_entry(ob, arm, ctx.family, path, s["notes"], slots=slots, sockets=sockets, poses_report=rep)
        export.write_manifest([entry], [m.name[2:] for m in ob.data.materials if m and m.name.startswith("M_")]
                              + [TX.DETAIL_SET])


# ================================================================================================ previews

STUDIO_HDRI = os.path.join(paths.out, "hdri", "mi_studio_softbox_2k.exr")
VM_FOV_V = 54.0
VIEWMODEL = {   # spec 02-weapons-combat 2.13: hip view 1 "Close" (position x right, y up, z to the viewer; pitch, yaw, roll)
    "SK_Chopper": ((0.15, -0.09, -0.24), (0.05, 0.28, -0.35)),
    "SK_Nine": ((0.105, -0.056, -0.36), (0.07, 0.11, -0.18)),
}


def studio_hdri(path=STUDIO_HDRI, w=2048, h=1024):
    """A studio-like environment written as an EXR: dark graded room, a large key softbox (upper front left), a
    tall strip light behind for the rim, a top light and a dim fill card. Directions in Blender world space."""
    if os.path.exists(path):
        return path
    j, i = np.meshgrid((np.arange(w) + 0.5) / w, (np.arange(h) + 0.5) / h)
    phi = (j - 0.5) * 2 * math.pi
    th = (i - 0.5) * math.pi
    d = np.stack([-np.cos(phi) * np.cos(th), np.sin(phi) * np.cos(th), np.sin(th)], -1)
    img = (0.020 + 0.030 * np.clip(d[..., 2] + 0.2, 0, 1))[..., None] * np.array([1.0, 1.0, 1.03])
    img = np.broadcast_to(img, (h, w, 3)).copy()

    def box(direction, half_w, half_h, radiance, up=(0, 0, 1), soft=0.15, tint=(1, 1, 1)):
        f = np.asarray(direction, float)
        f /= np.linalg.norm(f)
        r = np.cross(f, up)
        if np.linalg.norm(r) < 1e-6:
            r = np.array([1.0, 0, 0])
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        cf = d @ f
        x = np.degrees(np.arctan2(d @ r, cf))
        y = np.degrees(np.arctan2(d @ u, cf))
        a = tp.smooth(1 - np.abs(x) / half_w, 0, soft) * tp.smooth(1 - np.abs(y) / half_h, 0, soft) * (cf > 0)
        img[...] += a[..., None] * radiance * np.asarray(tint)
    box((-0.25, -0.75, 0.62), 22, 15, 9.0, tint=(1.0, 0.98, 0.95))      # key
    box((0.55, 0.80, 0.25), 6, 32, 14.0, tint=(0.95, 0.98, 1.0))        # rim strip behind
    box((0.0, 0.05, 1.0), 26, 26, 2.2, up=(0, 1, 0))                     # top
    box((1.0, -0.35, 0.10), 15, 12, 1.1, tint=(1.0, 0.96, 0.9))         # fill card
    box((-0.9, 0.3, 0.25), 8, 20, 3.0)                                   # kicker for the left side
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = bpy.data.images.new("studio", w, h, alpha=False, float_buffer=True)
    px = np.concatenate([img, np.ones((h, w, 1))], -1).astype(np.float32)
    im.pixels.foreach_set(px.ravel())
    im.filepath_raw = path
    im.file_format = "OPEN_EXR"
    im.save()
    bpy.data.images.remove(im)
    return path


def rig_studio(strength=1.0, exposure=0.0):
    render._clear_rig()
    w, nt = render._world()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(studio_hdri(), check_existing=True)
    nt.links.new(env.outputs[0], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    render.look(render.VIEW, "AgX - Medium High Contrast", exposure)


def view_matrix(pos, rot):
    """Gun space (Blender) -> viewmodel camera space (three.js view: x right, y up, -z forward)."""
    C = Matrix(((0, -1, 0, 0), (0, 0, 1, 0), (-1, 0, 0, 0), (0, 0, 0, 1)))
    R = Euler(rot, "ZYX").to_matrix().to_4x4()           # three.js 'XYZ' order = Rx @ Ry @ Rz
    return Matrix.Translation(pos) @ R @ C


def fp_camera(eye=(0.0, 0.0, 1.62), bearing=150.0, pitch_down=4.0):
    cam = render._cam("Cam_FP", 30.0)
    cam.data.sensor_fit = "VERTICAL"
    cam.data.angle_y = math.radians(VM_FOV_V)
    cam.data.clip_start = 0.01
    cam.location = eye
    cam.rotation_euler = (math.radians(90.0 - pitch_down), 0.0, math.radians(-bearing))
    bpy.context.view_layer.update()
    return cam


def place_in_view(root, cam, pos, rot):
    root.matrix_world = cam.matrix_world @ view_matrix(pos, rot)
    bpy.context.view_layer.update()


def set_pose(arm, bones):
    """Pose the rig in place (asset-space rigid transforms, see rig.pose_imported)."""
    rig.pose_imported(arm, bones)


def wire_material():
    m = bpy.data.materials.get("Clay_Wire") or bpy.data.materials.new("Clay_Wire")
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.42, 0.42, 0.43, 1)
    b.inputs["Roughness"].default_value = 0.5
    wf = nt.nodes.new("ShaderNodeWireframe")
    wf.use_pixel_size = True
    wf.inputs[0].default_value = 0.6
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.42, 0.42, 0.43, 1)
    mix.inputs["B"].default_value = (0.03, 0.05, 0.09, 1)
    nt.links.new(wf.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def _hide_all_but(keep):
    keep = set(keep)
    for o in bpy.context.scene.objects:
        o.hide_render = o not in keep and o.type in ("MESH", "CURVE")


def _ground_day(size=400.0):
    me = bpy.data.meshes.new("Ground")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    bm.to_mesh(me)
    bm.free()
    g = bpy.data.objects.new("Ground", me)
    scene.collection("Rig").objects.link(g)
    geo.uv_world_box(g, mat.scan_tile("TS_Asphalt_ScanWorn"))
    try:
        me.materials.append(mat.from_scan("TS_Asphalt_ScanWorn"))
    except Exception:
        me.materials.append(mat.flat("M_Asphalt", (0.09, 0.09, 0.09), 0.85))
    geo.ensure_wear(g)
    return g


def _el_context():
    """Link a few El pieces (art/out/blend/el.blend) into the FP backdrop when that build exists."""
    p = os.path.join(paths.blend, "el.blend")
    if not os.path.exists(p):
        return []
    want = ["SM_El_Column", "SM_El_GirderSpan_10m", "SM_El_Bent", "SM_El_Deck_10m"]
    with bpy.data.libraries.load(p, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in want]
    out = []
    col = scene.collection("Rig")
    for ob in dst.objects:
        if ob is None:
            continue
        for k in range(-3, 4):
            cp = ob.copy()
            col.objects.link(cp)
            x = 10.0 * k
            if ob.name.startswith("SM_El_Column"):
                for s in (1, -1):
                    c2 = cp if s == 1 else cp.copy()
                    if s == -1:
                        col.objects.link(c2)
                    c2.location = (x, s * 4.6, 0)
                    out.append(c2)
            elif ob.name.startswith("SM_El_Bent"):
                cp.location = (x, 0, 0)
                out.append(cp)
            else:
                cp.location = (x + 0.0, 0, 0)
                out.append(cp)
    return out


def _prev(ctx, name):
    return os.path.join(paths.previews, name + ".jpg")


def preview_hero(ctx, ob, arm, name, direction, focus, lens=85.0, fstop=4.0, extra=()):
    rig_studio()
    _hide_all_but([ob] + list(extra))
    lo, hi = scene.bounds(ob, world=True)
    c = Vector(focus)
    span = float(np.linalg.norm(hi - lo))
    fov = 2 * math.atan(18.0 / lens)
    dist = span * 0.60 / math.tan(fov / 2)
    d = Vector(direction).normalized()
    cam = render.cam_look(c + d * dist, Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)), lens,
                          name="Cam_" + name, dof=((d * dist).length, fstop))
    cam.data.clip_start = 0.01
    render.setup(samples=ctx.args.samples, res=(1280, 720))
    path, sec = render.render_jpeg(_prev(ctx, name), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))


def preview_fp(ctx, ob, arm, key, name, extra=()):
    """Through the viewmodel camera (54 deg vertical, hip pose 'Close' of the spec) on the day rig: the gun is
    lit by the day sky and sun (design bearing); the camera sees an urban street plate (canary_wharf, catalogue
    HDRI) behind it, as the game draws the viewmodel over the world."""
    rd = render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING)
    plate = render.hdri_path("canary_wharf")
    if os.path.exists(plate):
        nt = bpy.context.scene.world.node_tree
        out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputWorld")
        sky = out.inputs["Surface"].links[0].from_node
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(plate, check_existing=True)
        bg = nt.nodes.new("ShaderNodeBackground")
        bg.inputs["Strength"].default_value = 2.0 ** (-(rd.get("exposure", 0.0) or 0.0)) * 0.9
        nt.links.new(env.outputs[0], bg.inputs["Color"])
        lp = nt.nodes.new("ShaderNodeLightPath")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
        nt.links.new(sky.outputs[0], mix.inputs[1])
        nt.links.new(bg.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    cam = fp_camera(bearing=170.0, pitch_down=2.0)
    pos, rot = VIEWMODEL[key]
    place_in_view(arm, cam, pos, rot)
    for e in extra:
        e.matrix_world = arm.matrix_world
    _hide_all_but([ob] + list(extra))
    render.setup(samples=ctx.args.samples, res=(1280, 720))
    path, sec = render.render_jpeg(_prev(ctx, name), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))
    arm.matrix_world = Matrix.Identity(4)
    for e in extra:
        e.matrix_world = Matrix.Identity(4)


def import_asset(name, col_name=None):
    """Re-import an exported GLB and give its slots the baked materials (the files carry slot names only)."""
    path = os.path.join(paths.glb, name + ".glb")
    arm, meshes, col = rig.import_glb(path, col_name or ("Imp_" + name))
    for o in meshes:
        for sl in o.material_slots:
            if sl.material is None:
                continue
            base = sl.material.name.split(".")[0]
            set_name = base[2:]
            d = paths.texture_set(set_name)
            m = bpy.data.materials.get(base)
            if (m is None or m == sl.material) and os.path.exists(os.path.join(d, "set.json")):
                old = sl.material
                old.name = base + "__stub"
                m = mat.from_texture_set(d, name=base, masks=False, macro=0.0, ao_strength=0.0, alpha="none")
            if m is not None:
                sl.material = m
    return arm, meshes, col


def _move(objs, M):
    for o in objs:
        if o.parent is None:
            o.matrix_world = M @ o.matrix_world
    bpy.context.view_layer.update()


def preview_parts(ctx):
    """Both guns from their re-imported GLBs, posed open (bolt back, trigger pulled, magazine rocked out; slide
    locked back, barrel tilted, hammer down), magazines and top rounds beside them."""
    rig_studio()
    for o in bpy.context.scene.objects:
        o.hide_render = o.type == "MESH"
    shown = []
    ca, cm, _ = import_asset("SK_Chopper")
    rig.pose_imported(ca, {"bolt": {"translate": (-CH["travel"], 0, 0)},
                           "trigger": {"rotate": ((0, 1, 0), CH["trigger_deg"])}})
    _a, mm, _ = import_asset("SM_Weapon_ChopperMagazine")
    _a, mt, _ = import_asset("SM_Weapon_ChopperMagazine_TopRound")
    hz = Vector(CH["hinge"])
    rock = Matrix.Translation(hz) @ Matrix.Rotation(math.radians(-CH["mag_deg"]), 4, "Y") @ Matrix.Translation(-hz)
    _move(mm + mt, Matrix.Translation((0, 0, -0.035)) @ rock)
    na, nm, _ = import_asset("SK_Nine")
    rig.pose_imported(na, {"slide": {"translate": (-NN["travel"], 0, 0)},
                           "slide_stop": {"rotate": ((0, 1, 0), NN["stop_deg"])},
                           "barrel": {"rotate": ((0, 1, 0), NN["barrel_deg"])},
                           "hammer": {"rotate": ((0, 1, 0), NN["hammer_down_deg"])},
                           "trigger": {"rotate": ((0, 1, 0), NN["trigger_deg"])}})
    _a, nmm, _ = import_asset("SM_Weapon_NineMagazine")
    _a, nmt, _ = import_asset("SM_Weapon_NineMagazine_TopRound")
    a = Vector(NN["mag_axis"]).normalized()
    nine_M = Matrix.Translation((0.20, -0.02, -0.205))
    _move([na], nine_M)
    _move(nmm + nmt, nine_M @ Matrix.Translation(-a * 0.11 + Vector((-0.10, 0, 0))))
    for o in cm + mm + mt + nm + nmm + nmt:
        o.hide_render = False
    objs = cm + nm + mm + nmm
    lo = np.min([scene.bounds(o, world=True)[0] for o in objs], 0)
    hi = np.max([scene.bounds(o, world=True)[1] for o in objs], 0)
    c = Vector(((lo + hi) / 2).tolist())
    d = Vector((0.35, -1.0, 0.30)).normalized()
    cam = render.cam_look(c + d * 1.25, c, 60.0, name="Cam_parts", dof=(1.25, 8.0))
    cam.data.clip_start = 0.01
    render.setup(samples=ctx.args.samples, res=(1280, 720))
    path, sec = render.render_jpeg(_prev(ctx, "weapons_parts"), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))
    return cm, nm, mm, nmm, mt, nmt


def preview_wire(ctx, groups):
    """Clay with the wireframe over it: CHOPPER and NINE side by side (from the re-imported files)."""
    wm = wire_material()
    for o in bpy.context.scene.objects:
        o.hide_render = o.type == "MESH"
    shown = []
    for objs in groups:
        for o in objs:
            o.hide_render = False
            for sl in o.material_slots:
                sl.material = wm
            shown.append(o)
    rig_studio(strength=1.3)
    lo = np.min([scene.bounds(o, world=True)[0] for o in shown], 0)
    hi = np.max([scene.bounds(o, world=True)[1] for o in shown], 0)
    c = Vector(((lo + hi) / 2).tolist())
    cam = render.cam_look(c + Vector((0.05, -1.0, 0.12)).normalized() * 0.80, c, 50.0, name="Cam_wire")
    cam.data.clip_start = 0.01
    render.setup(samples=max(32, ctx.args.samples // 2), res=(1280, 720))
    path, sec = render.render_jpeg(_prev(ctx, "weapons_wire"), max(32, ctx.args.samples // 2))
    ctx.log("preview %s (%.0f s)" % (path, sec))


def preview_enemy(ctx):
    rig_studio()
    smg = bpy.data.objects.get("SM_Weapon_GoonSMG")
    mg = bpy.data.objects.get("SM_Weapon_GoonSMG_Magazine")
    pipe = bpy.data.objects.get("SM_Weapon_GoonPipe")
    _hide_all_but([smg, mg, pipe])
    pipe.matrix_world = Matrix.Translation((0.02, 0.16, -0.16)) @ Matrix.Rotation(math.radians(-8), 4, "Z")
    lm = bpy.data.materials.get("M_Weapon_GoonSMG_Lens")
    b = mat.principled(lm)
    b.inputs["Emission Color"].default_value = (1.0, 0.74, 0.42, 1)
    b.inputs["Emission Strength"].default_value = 6.0
    c = Vector((0.07, 0.06, -0.04))
    cam = render.cam_look(c + Vector((0.45, -1.0, 0.38)).normalized() * 1.55, c, 70.0, name="Cam_enemy",
                          dof=(1.55, 5.6))
    render.setup(samples=ctx.args.samples, res=(1280, 720))
    path, sec = render.render_jpeg(_prev(ctx, "weapons_enemy"), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))
    b.inputs["Emission Strength"].default_value = 0.0
    pipe.matrix_world = Matrix.Identity(4)


def _layout(prefix, posed):
    """Import both guns and their magazines; CHOPPER at the origin, NINE below its muzzle, magazines beside.
    posed: open the actions (bolt back, trigger pulled, magazine rocked out; slide locked back, barrel tilted,
    hammer down, slide stop up, magazine dropped). Returns the meshes."""
    ca, cm, _ = import_asset("SK_Chopper", prefix + "Chopper")
    _a, mm, _ = import_asset("SM_Weapon_ChopperMagazine", prefix + "ChopperMag")
    _a, mt, _ = import_asset("SM_Weapon_ChopperMagazine_TopRound", prefix + "ChopperTop")
    na, nm, _ = import_asset("SK_Nine", prefix + "Nine")
    _a, nmm, _ = import_asset("SM_Weapon_NineMagazine", prefix + "NineMag")
    _a, nmt, _ = import_asset("SM_Weapon_NineMagazine_TopRound", prefix + "NineTop")
    a = Vector(NN["mag_axis"]).normalized()
    if posed:
        rig.pose_imported(ca, {"bolt": {"translate": (-CH["travel"], 0, 0)},
                               "trigger": {"rotate": ((0, 1, 0), CH["trigger_deg"])}})
        hz = Vector(CH["hinge"])
        rock = Matrix.Translation(hz) @ Matrix.Rotation(math.radians(-CH["mag_deg"]), 4, "Y") @ Matrix.Translation(-hz)
        _move(mm + mt, Matrix.Translation((0.0, 0, -0.03)) @ rock)
        rig.pose_imported(na, {"slide": {"translate": (-NN["travel"], 0, 0)},
                               "slide_stop": {"rotate": ((0, 1, 0), NN["stop_deg"])},
                               "barrel": {"rotate": ((0, 1, 0), NN["barrel_deg"])},
                               "hammer": {"rotate": ((0, 1, 0), NN["hammer_down_deg"])},
                               "trigger": {"rotate": ((0, 1, 0), NN["trigger_deg"])}})
    nine_M = Matrix.Translation((0.36, -0.03, -0.165))
    _move([na], nine_M)
    _move(nmm + nmt, nine_M @ Matrix.Translation(-a * (0.045 if posed else 0.0)))
    return cm + mm + mt + nm + nmm + nmt


def preview_parts_wire(ctx):
    """One wide render split in two pictures: left half weapons_parts (both guns from their re-imported GLBs,
    posed open, magazines out), right half weapons_wire (the same files at rest in clay with the wireframe)."""
    from PIL import Image
    rig_studio()
    for o in bpy.context.scene.objects:
        o.hide_render = o.type == "MESH"
    left = _layout("ImpA_", True)
    right = _layout("ImpB_", False)
    _move([o for o in right if o.parent is None] + [o.parent for o in right if o.parent is not None], Matrix.Translation((0.80, 0, 0)))
    wm = wire_material()
    for o in right:
        for sl in o.material_slots:
            sl.material = wm
    for o in left + right:
        o.hide_render = False
    c = Vector((0.265 + 0.40, 0.0, -0.140))
    d = Vector((0.0, -1.0, 0.20)).normalized()
    cam = render.cam_look(c + d * 2.70, c, 55.0, name="Cam_partswire", dof=(2.70, 11.0))
    cam.data.clip_start = 0.05
    render.setup(samples=ctx.args.samples, res=(2560, 720))
    tmp = os.path.join(paths.out, "weapons_partswire.png")
    render.render_png(tmp, ctx.args.samples, (2560, 720))
    im = Image.open(tmp)
    for name, box_ in (("weapons_parts", (0, 0, 1280, 720)), ("weapons_wire", (1280, 0, 2560, 720))):
        render.save_jpeg(im.crop(box_), _prev(ctx, name))
        ctx.log("preview %s" % _prev(ctx, name))


PREVIEW_ONLY = os.environ.get("MI_PREVIEWS", "")


def on_preview(ctx, objs):
    want = lambda n: not PREVIEW_ONLY or n in PREVIEW_ONLY.split(",")
    if "SK_Chopper" in SKINNED:
        s = SKINNED["SK_Chopper"]
        mag = bpy.data.objects.get("SM_Weapon_ChopperMagazine")
        top = bpy.data.objects.get("SM_Weapon_ChopperMagazine_TopRound")
        if want("weapons_chopper_hero"):
            preview_hero(ctx, s["ob"], s["arm"], "weapons_chopper_hero", (0.55, -1.0, 0.42), (0.16, -0.02, 0.0),
                         extra=(mag, top))
        if want("weapons_chopper_fp"):
            preview_fp(ctx, s["ob"], s["arm"], "SK_Chopper", "weapons_chopper_fp", extra=(mag, top))
    if "SK_Nine" in SKINNED:
        s = SKINNED["SK_Nine"]
        mag = bpy.data.objects.get("SM_Weapon_NineMagazine")
        top = bpy.data.objects.get("SM_Weapon_NineMagazine_TopRound")
        if want("weapons_nine_hero"):
            preview_hero(ctx, s["ob"], s["arm"], "weapons_nine_hero", (0.55, -1.0, 0.40), (0.07, -0.014, -0.02),
                         extra=(mag, top))
        if want("weapons_nine_fp"):
            preview_fp(ctx, s["ob"], s["arm"], "SK_Nine", "weapons_nine_fp", extra=(mag, top))
    if bpy.data.objects.get("SM_Weapon_GoonSMG") and want("weapons_enemy"):
        preview_enemy(ctx)
    have = all(os.path.exists(os.path.join(paths.glb, n + ".glb")) for n in ("SK_Chopper", "SK_Nine"))
    both = "SK_Chopper" in SKINNED and "SK_Nine" in SKINNED
    if have and (want("weapons_parts") or want("weapons_wire")) and (both or PREVIEW_ONLY):
        preview_parts_wire(ctx)


# rebuild round 1: the new part builders (they use the kit above, so they are imported last)
from assets import _weapons_kit as KIT  # noqa: E402
from assets import _weapons_nine as N9  # noqa: E402
from assets import _weapons_tex as TX  # noqa: E402
from assets import _weapons_chopper as CH9  # noqa: E402
