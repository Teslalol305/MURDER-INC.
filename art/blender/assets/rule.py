"""Rule, the player character, as a likeness of the man in the user's reference photo (the user owns the
likeness). Everything that shows the likeness as source material stays in art/out/ (git-ignored): the photo
(art/out/ref/), the generated reference sheet and raw generated meshes (art/out/gen/rule/, jobs in gen_log.json),
the .blend. Preview JPEGs of the finished character are committed.

Assets
  SK_RuleArms          the first-person arms, BARE to the shoulder, on the UE5 mannequin skeleton: anatomical hands
                       (metacarpal knuckles, extensor tendons, nail folds, separate nails), his build, forearm
                       tattoos; slots M_RuleArms_Skin (subsurface profile in Unreal) and M_RuleArms_Nail, both on the
                       unique 4K set RuleArms_Skin (BC, N, ORM; both arms have their own islands: the tattoos differ)
  SK_RuleArms_Gloved   the first version (assets/characters.py, gloved) kept as a variant; its skin slot is renamed
                       M_RuleArms_GlovedSkin and reads the copied set RuleArms_GlovedSkin
  SM_Character_RuleBracelet  chunky silver curb chain on the RIGHT wrist (the photo: the forearm on top is his
                       right; also the first version's socket Socket_Bracelet on lowerarm_twist_01_r), real links
  SK_Rule              the full body for the crew screen and the cards (see build_body)

    venv/bin/python art/blender/build.py build rule --only gloved --export          # the variant, first
    venv/bin/python art/blender/build.py build rule --only arms --bake --res 4096 --export --preview
    venv/bin/python art/blender/build.py build rule --only body --export --preview

The bone and socket contract of the first version is kept: the full SK_Mannequin skeleton, the right arm's bones
read from the imported mannequin, Socket_Bracelet on lowerarm_twist_01_r (art/out/glb/SK_RuleArms.sockets.json;
the watch is not in the photo: its socket entry is kept unchanged, the look does not wear it).
"""
import json
import math
import os
import shutil

import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import char, geo, paths, scene, sdf

from . import characters as C

FAMILY = {"name": "rule", "description": "Rule after the reference photo: bare arms, bracelet, full body"}

H_ARM = 0.0022           # surface nets of the arm (m)
H_HAND = 0.0010          # of the hand
VOXEL = 0.0008           # the joined arm and hand remeshed to one surface
H_NAIL = 0.00016
ARM_TRIS = 64000         # per arm (both arms about 140k with nails and the bracelet)
NAIL_TRIS = 360
HAND_UV_BOOST = 1.75     # texel density of the hand over the arm
BRACELET_S = 0.036       # above the wrist joint, over the ulnar head

# his build: forearm and upper arm thicker than the brief's, the biceps and shoulder fuller (reference sheet)
FOREARM = [(s, w * 1.06, h * 1.06) for s, w, h in C.FOREARM]
UPPER = [(s, w * 1.10, h * 1.10) for s, w, h in C.UPPER]


def _n(v):
    return C._n(v)


def fore_d(R, p, grow=0.0):
    s, x, y = R.fore_coords(p)
    a = C._interp(FOREARM, s, 1) / 2 + grow
    b = C._interp(FOREARM, s, 2) / 2 + grow
    return s, C.ellipse_d(x, y, a, b)


def arm_sdf(R):
    """The bare arm from the shoulder to the wrist (the hand is hand_field): the first version's anatomy with his
    proportions."""
    def f(p):
        s, d_fore = fore_d(R, p)
        d_fore = np.maximum(d_fore, s - (R.L + 0.035))
        d_fore = np.maximum(d_fore, -s - 0.004)
        su, xu, yu = R.upper_coords(p)
        a = C._interp(UPPER, su, 1) / 2
        b = C._interp(UPPER, su, 2) / 2
        d_up = C.ellipse_d(xu, yu, a, b)
        d_up = np.maximum(d_up, su - (R.Lu + 0.005))
        d_up = np.maximum(d_up, -su - 0.03)
        d = sdf.smin(d_fore, d_up, 0.028)
        for s0, off, rad, k in (
                (0.205, (-0.021, 0.013), (0.085, 0.022, 0.021), 0.016),      # brachioradialis / radial extensors
                (0.195, (0.010, -0.018), (0.090, 0.026, 0.020), 0.016),      # flexor mass
                (0.150, (0.013, 0.017), (0.075, 0.017, 0.016), 0.014)):      # ulnar extensors
            c0, u, v = R.fore_frame(s0)
            c = c0 + u * off[0] + v * off[1]
            d = sdf.smin(d, sdf.ellipsoid(p, c, np.array([R.af, u, v]), rad), k)
        d = sdf.smin(d, sdf.sphere(p, R.E - R.ant * 0.032 + R.bu * 0.004, 0.0170), 0.012)
        d = sdf.smin(d, sdf.sphere(p, R.E + R.latu * 0.036 + R.bu * 0.012, 0.0125), 0.012)
        d = sdf.smin(d, sdf.sphere(p, R.E - R.latu * 0.039 + R.bu * 0.014, 0.0125), 0.012)
        fr = np.array([R.bu, R.latu, R.ant])
        d = sdf.smin(d, sdf.ellipsoid(p, R.E + R.bu * 0.125 + R.ant * 0.024, fr, (0.090, 0.032, 0.033)), 0.018)  # biceps
        d = sdf.smin(d, sdf.ellipsoid(p, R.E + R.bu * 0.165 - R.ant * 0.020, fr, (0.100, 0.038, 0.034)), 0.018)  # triceps
        d = sdf.smin(d, sdf.ellipsoid(p, R.S - R.bu * 0.045 + R.latu * 0.014, fr, (0.080, 0.053, 0.055)), 0.020)  # deltoid
        d = sdf.smin(d, sdf.sphere(p, R.S + R.latu * 0.004 - R.bu * 0.004, 0.050), 0.02)
        return d
    return f


class Hand:
    """The bare hand: the first version's palm and fingers (characters.hand_sdf) with the metacarpal knuckles,
    the extensor tendons over the back of the hand and the nail beds (shallow recess, cuticle fold)."""

    def __init__(self, R):
        self.R = R
        self.base = C.hand_sdf(R, 0.0)
        self.nails = {n: self._nail_frame(n) for n in C.FINGERS}
        self.tendons = []
        for n in C.FINGERS[:4]:
            a = R.W + R.dors * 0.03 + R.lat * (((R.mcp[n] - R.W) @ R.lat) * 0.45) + R.fwd * 0.012
            b = R.mcp[n] + R.dors * 0.03 - R.fwd * 0.006
            a, b = (self._onto(p, R.dors) for p in (a, b))
            self.tendons.append((a, b))

    def _onto(self, p, direction):
        """March from p against `direction` onto the hand's surface."""
        q = np.array([p], dtype=np.float64)
        for _ in range(60):
            d = self.base(q)
            q = q - direction[None] * d[:, None] * 0.9
        return q[0]

    def _nail_frame(self, n):
        c = self.R.chain[n]
        P, r, dv = c["P"], c["r"], c["dors"]
        ax = _n(P[3] - P[2])
        side = _n(np.cross(dv, ax))
        dv = _n(np.cross(ax, side))
        L = float(np.linalg.norm(P[3] - P[2]))
        root = P[2] + ax * (L * 0.38)
        tip = P[3] + ax * r[3] * 0.78
        ctr = (root + tip) / 2
        half_len = float(np.linalg.norm(tip - root) / 2)
        half_w = r[3] * (0.66 if n != "thumb" else 0.70)
        return dict(c=ctr, frame=np.array([ax, side, dv]), hl=half_len, hw=half_w, r=r[3])

    def nail_rect(self, p, n, grow=0.0):
        nf = self.nails[n]
        q = sdf.local(p, nf["c"], nf["frame"])
        d = sdf.rect2(q[:, 0], q[:, 1], nf["hl"] + grow, nf["hw"] + grow, nf["hw"] * 0.75)
        return d, q

    def field(self, recess=True):
        R, base = self.R, self.base

        def f(p):
            d0 = base(p)
            d = d0
            for n in C.FINGERS[:4]:                        # metacarpal heads under the skin of the back of the hand
                r0 = R.chain[n]["r"][0]
                d = sdf.smin(d, sdf.sphere(p, R.mcp[n] + R.dors * r0 * 0.42 - R.fwd * 0.003, r0 * 0.66), r0 * 0.40)
            for a, b in self.tendons:                      # extensor tendons, about 0.8 mm proud
                seg = sdf.capsule(p, a, b, 0.0)
                ridge = np.maximum(d0 - 0.0008, seg - 0.0024)
                d = sdf.smin(d, ridge, 0.0016)
            if recess:
                for n in C.FINGERS:
                    rd, q = self.nail_rect(p, n, 0.0003)
                    up = np.clip(q[:, 2] / max(self.nails[n]["r"] * 0.4, 1e-4), 0, 1)
                    bed = T_smooth(0.0004, -0.0003, rd) * up
                    fold = np.exp(-((q[:, 0] + self.nails[n]["hl"] + 0.0009) / 0.0007) ** 2) * T_smooth(0.0006, -0.0002, np.abs(q[:, 1]) - self.nails[n]["hw"]) * up
                    d = d + 0.00038 * bed - 0.00022 * fold
            return d
        return f


def T_smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def whole_field(R, hand):
    arm = arm_sdf(R)
    hf = hand.field(True)

    def f(p):
        return sdf.smin(arm(p), hf(p), 0.011)
    return f


# ------------------------------------------------------------------------------------------------ meshing


def mesh_arm(R, hand, col, log=print):
    """One closed surface of the right arm: arm at H_ARM and hand at H_HAND from surface nets, joined, voxel
    remeshed, every vertex projected onto the exact field, decimated."""
    F = whole_field(R, hand)
    lo = np.minimum.reduce([R.S, R.E, R.W]) - 0.08
    hi = np.maximum.reduce([R.S, R.E, R.W]) + 0.08
    a = C.mesh_field("Arm_R_coarse", F, (lo + hi) / 2, np.eye(3), (hi - lo) / 2, H_ARM, col, relax=1)
    hf = np.array([R.fwd, R.lat, R.dors])
    tips = np.array([R.chain[n]["P"][3] for n in C.FINGERS])
    pts = np.vstack([tips, R.W - R.af * 0.09, R.W])
    loc = (pts - R.W) @ hf.T
    lo2 = np.minimum(loc.min(axis=0), [-0.06, -0.065, -0.05]) - 0.016
    hi2 = np.maximum(loc.max(axis=0), [0.0, 0.055, 0.045]) + 0.016
    ctr = R.W + ((lo2 + hi2) / 2) @ hf
    b = C.mesh_field("Hand_R_fine", F, ctr, hf, (hi2 - lo2) / 2, H_HAND, col, relax=1)
    log("  surface nets: arm %d, hand %d vertices" % (len(a.data.vertices), len(b.data.vertices)))
    ob = geo.join([a, b], "Skin_R", col)
    md = ob.modifiers.new("remesh", "REMESH")
    md.mode = "VOXEL"
    md.voxel_size = VOXEL
    md.adaptivity = 0.0
    md.use_smooth_shade = True
    geo._apply_modifier(ob, md)
    v = C.verts(ob)
    log("  voxel remesh: %d vertices" % len(v))
    out = np.empty_like(v)
    for i in range(0, len(v), 400_000):
        out[i:i + 400_000] = sdf.project(F, v[i:i + 400_000], 3, max_step=0.0015)
    ob.data.vertices.foreach_set("co", out.ravel())
    ob.data.update()
    C.decimate(ob, ARM_TRIS)
    log("  decimated: %d triangles" % sum(len(p.vertices) - 2 for p in ob.data.polygons))
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob, F


def mesh_nails(R, hand, col):
    base = hand.field(False)
    out = []
    for n in C.FINGERS:
        nf = hand.nails[n]

        def f(p, n=n, nf=nf):
            d0 = base(p)
            plate = np.maximum(d0 - 0.00030, -0.00040 - d0)                 # 0.7 mm plate, 0.3 mm proud
            rd, q = hand.nail_rect(p, n, 0.0)
            plate = sdf.smax(plate, rd, 0.0003)
            return sdf.smax(plate, nf["r"] * 0.15 - q[:, 2], 0.0004)          # the top of the finger only
        half = np.array([nf["hl"] + 0.002, nf["hw"] + 0.002, nf["r"] * 0.9])
        ob = C.mesh_field("Nail_%s_R" % n, f, nf["c"], nf["frame"], half, H_NAIL, col, relax=2)
        C.decimate(ob, NAIL_TRIS)
        out.append(ob)
    return out


# ------------------------------------------------------------------------------------------------ assemble


def regions(R, ob):
    """Per face: 0 arm, 1 back of the hand and fingers, 2 palm side."""
    fc = C.face_centres(ob)
    s, _x, _y = R.fore_coords(fc)
    lab, dors, _cuff = C.glove_regions(R, fc)
    reg = np.where(dors, 1, 2)
    reg[s > 0.022] = 0
    return reg


def set_face_attr(ob, name, vals):
    a = ob.data.attributes.get(name) or ob.data.attributes.new(name, "FLOAT", "FACE")
    a.data.foreach_set("value", np.asarray(vals, dtype=np.float32))


def skin_materials():
    return {"skin": C.flat_material("M_RuleArms_Skin", C.srgb("#7b4e35"), 0.45),
            "nail": C.flat_material("M_RuleArms_Nail", C.srgb("#b88f7f"), 0.25)}


def weights_right(R, body, skin, nails, log=print):
    sl = C.source_labels(body, "r")
    bones = char.ARM_BONES["r"]
    lab = C.glove_regions(R, C.verts(skin))[0]
    names, W = char.transfer_weights(skin, body, bones, limit=6, target_labels=lab, source_labels=sl)
    char.smooth_weights(skin, iterations=3, strength=0.4, limit=6, names=names, W=W)
    log("  weights Skin_R: %d vertices" % len(skin.data.vertices))
    for n, ob in zip(C.FINGERS, nails):
        ob.vertex_groups.clear()
        g = ob.vertex_groups.new(name="%s_03_r" % n)
        g.add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")


def uv_layout(R, ob, side_attr):
    """Seams: the arm tube (ulnar border, medial upper arm, shoulder cap), the wrist ring, the hand's back / palm
    border; nails are their own islands. Hand islands get HAND_UV_BOOST x the density, then everything is packed.
    Works on the joined two-arm mesh (left arm mirrored: its coordinates are mirrored back for the seams)."""
    me = ob.data
    co = C.verts(ob)
    side = np.zeros(len(co))
    fs = np.zeros(len(me.polygons), dtype=np.float32)
    me.attributes[side_attr].data.foreach_get("value", fs)
    reg = np.zeros(len(me.polygons), dtype=np.float32)
    me.attributes["mi_region"].data.foreach_get("value", reg)
    for p in me.polygons:
        if fs[p.index] > 0.5:
            side[list(p.vertices)] = 1
    q = co.copy()
    q[side > 0.5, 0] *= -1
    tmp = co.copy()
    ob.data.vertices.foreach_set("co", q.ravel())
    seam = C.skin_seams(R, ob)
    ob.data.vertices.foreach_set("co", tmp.ravel())
    fid = (reg * 2 + fs).astype(int)
    seam |= char.seams_between(ob, fid)
    me.edges.foreach_set("use_seam", seam)
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    scene.select_only(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    # density: average the islands on a copy whose hand is scaled up in 3D, then copy the UVs back
    cp = ob.copy()
    cp.data = ob.data.copy()
    bpy.context.scene.collection.objects.link(cp)
    hv = np.zeros(len(co), dtype=bool)
    for p in me.polygons:
        if reg[p.index] > 0.5:
            hv[list(p.vertices)] = True
    c2 = co.copy()
    c2[hv] = c2[hv] * HAND_UV_BOOST
    cp.data.vertices.foreach_set("co", c2.ravel())
    cp.data.update()
    scene.select_only(cp)
    bpy.context.view_layer.objects.active = cp
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin_method="FRACTION", margin=0.0025, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")
    uv = np.empty(len(me.loops) * 2)
    cp.data.uv_layers.active.data.foreach_get("uv", uv)
    me.uv_layers.active.data.foreach_set("uv", uv)
    bpy.data.objects.remove(cp, do_unlink=True)


def _cached_mesh(R, hand, ctx):
    """Meshing takes 10-20 minutes on the shared machine: the decimated skin and the nails are kept in
    art/out/blend/rule_arms_mesh.blend under a hash of the code that shapes them (this file, characters.py, sdf.py)."""
    import hashlib
    here = os.path.dirname(__file__)
    h = hashlib.sha1()
    for f in (os.path.join(here, "rule.py"), os.path.join(here, "characters.py"),
              os.path.join(here, "..", "mi", "sdf.py")):
        src = open(f).read()
        if f.endswith("rule.py"):                          # only the shaping half of this file
            src = src.split(" assemble\n")[0]
        h.update(src.encode())
    key = h.hexdigest()[:12]
    path = os.path.join(paths.blend, "rule_arms_mesh.blend")
    F = whole_field(R, hand)
    if os.path.exists(path) and not ctx.args.force:
        with bpy.data.libraries.load(path, link=False) as (fr, to):
            to.objects = [n for n in fr.objects if n.startswith("Cache_")]
        objs = {o.name: o for o in to.objects if o is not None}
        sk = objs.get("Cache_Skin_R")
        if sk is not None and sk.get("mi_key") == key:
            nails = [objs["Cache_Nail_%s_R" % n] for n in C.FINGERS]
            for o in [sk] + nails:
                ctx.col.objects.link(o)
                o.name = o.name[len("Cache_"):]
            ctx.log("  arm mesh from the cache (%s)" % key)
            return sk, nails, F
        for o in objs.values():
            bpy.data.objects.remove(o, do_unlink=True)
    skin, F = mesh_arm(R, hand, ctx.col, ctx.log)
    nails = mesh_nails(R, hand, ctx.col)
    keep = []
    for o in [skin] + nails:
        c = o.copy()
        c.data = o.data.copy()
        c.name = "Cache_" + o.name
        c["mi_key"] = key
        keep.append(c)
    os.makedirs(paths.blend, exist_ok=True)
    bpy.data.libraries.write(path, set(keep), fake_user=True)
    for c in keep:
        bpy.data.objects.remove(c, do_unlink=True)
    return skin, nails, F


def build_arms(ctx):
    arm, body = char.import_mannequin()
    body.hide_render = True
    R = C.ArmRig(arm, body)
    ctx.log("arm: forearm %.3f m, upper arm %.3f m" % (R.L, R.Lu))
    hand = Hand(R)
    skin, nails, F = _cached_mesh(R, hand, ctx)
    ctx.log("nails: %d triangles" % sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in nails))
    mats = skin_materials()
    weights_right(R, body, skin, nails, ctx.log)
    set_face_attr(skin, "mi_region", regions(R, skin))
    for o in nails:
        set_face_attr(o, "mi_region", np.full(len(o.data.polygons), 3))
    right = geo.join([skin] + nails, "Skin_R", ctx.col)
    reg = np.zeros(len(right.data.polygons), dtype=np.float32)
    right.data.attributes["mi_region"].data.foreach_get("value", reg)
    right.data.materials.clear()
    C.set_material_ids(right, [mats["skin"], mats["nail"]], (reg > 2.5).astype(int))
    set_face_attr(right, "mi_side", np.zeros(len(right.data.polygons)))
    left = char.mirror_x(right, "Skin_L")
    set_face_attr(left, "mi_side", np.ones(len(left.data.polygons)))
    ob = geo.join([right, left], "SK_RuleArms", ctx.col)
    uv_layout(R, ob, "mi_side")
    geo.weighted_normals(ob, weight=50, keep_sharp=False)
    ctx.log("SK_RuleArms: %d triangles" % sum(len(p.vertices) - 2 for p in ob.data.polygons))
    br = bracelet(ctx.col, R)
    geo.ensure_wear(br)
    ctx.asset(br, collision="none", notes="Silver curb chain, attach frame origin on the right forearm axis %d mm above "
              "the wrist; Socket_Bracelet on lowerarm_twist_01_r (SK_RuleArms.sockets.json)." % (BRACELET_S * 1000))
    ctx.log("SM_Character_RuleBracelet: %d triangles" % sum(len(p.vertices) - 2 for p in br.data.polygons))
    ctx.rule = dict(R=R, Rl=C.ArmRig(arm, body, "l"), arm=arm, body=body, ob=ob, bracelet=br, F=F)
    return ob


# ------------------------------------------------------------------------------------------------ bracelet


def bracelet(col, R):
    """SM_Character_RuleBracelet: a heavy silver curb chain, 22 links of 2.1 mm wire pressed flat and twisted
    against each other, hanging loose round the wrist (3 mm clear, 4 mm sag underneath), with a box clasp.
    Origin = attach frame (characters.attach_frame): X across the arm, Y toward the elbow, Z out of the back."""
    from mi import mat as _mat
    silver = _mat.flat("M_Character_RuleBracelet_Silver", (0.96, 0.95, 0.93), 0.12, 1.0)
    silver2 = _mat.flat("M_Character_RuleBracelet_SilverWorn", (0.90, 0.89, 0.87), 0.22, 1.0)
    a = C._interp(FOREARM, BRACELET_S, 1) / 2 + 0.0030 + 0.0021
    b = C._interp(FOREARM, BRACELET_S, 2) / 2 + 0.0030 + 0.0021
    n = 22
    pts, _t = C._ellipse_path(a, b, 600, sag=0.004)
    seg = np.linalg.norm(np.roll(pts, -1, axis=0) - pts, axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    total = cum[-1]
    parts = []
    for i in range(n):
        d = (i + 0.5) / n * total
        k = int(np.searchsorted(cum, d) - 1) % len(pts)
        p0, p1 = pts[k], pts[(k + 1) % len(pts)]
        mid = p0 + (p1 - p0) * ((d - cum[k]) / max(seg[k], 1e-9))
        tang = (p1 - p0) / max(seg[k], 1e-9)
        if i == 0:                                         # box clasp on the back of the wrist
            bx = geo.box((0.0165, 0.0115, 0.0042), bevel=0.0009, segments=3, base=False, name="Clasp")
            ang = math.degrees(math.atan2(tang[2], tang[0]))
            geo.transform(bx, rot=(0, -ang, 0))
            geo.transform(bx, loc=tuple(mid))
            parts.append(C._mat_all(bx, silver))
            continue
        lk = geo.torus(major=0.0038, minor=0.00105, seg_major=36, seg_minor=12, name="Link",
                       stretch=total / n * 1.55 - 0.0076)
        geo.transform(lk, scale=(1.0, 1.0, 0.62))
        geo.transform(lk, rot=(30 if i % 2 else -30, 0, 0))
        ang = math.degrees(math.atan2(tang[2], tang[0]))
        geo.transform(lk, rot=(0, -ang, 0))
        geo.transform(lk, loc=tuple(mid))
        parts.append(C._mat_all(lk, silver if i % 3 else silver2))
    ob = geo.join(parts, "SM_Character_RuleBracelet", col)
    C._smart_uv(ob)
    return ob


# ------------------------------------------------------------------------------------------------ textures


def bake_skin(ctx, ob, res):
    from assets import _rule_tex as X
    from mi import bake as _bake, texel
    R = ctx.rule["R"]
    maps = texel.bake_maps(ob, res, face_attrs=["mi_region", "mi_side"])
    ctx.log("  RuleArms_Skin: maps baked, coverage %.1f %%" % (100 * maps["mask"].mean()))
    H, W = maps["mask"].shape
    idx = np.nonzero(maps["mask"].ravel())[0]
    bc = np.zeros((H * W, 3), dtype=np.float32)
    ro = np.full(H * W, 0.5, dtype=np.float32)
    hh = np.zeros(H * W, dtype=np.float32)
    Pf, Nf = maps["pos"].reshape(-1, 3), maps["normal"].reshape(-1, 3)
    charts = {"right": X.tattoo_chart("right"), "left": X.tattoo_chart("left")}
    for sl in texel.chunks(idx, 600_000):
        c, r, h = X.skin_texels(R, Pf[sl].astype(np.float64), Nf[sl].astype(np.float64),
                                maps["mi_region"].ravel()[sl], maps["mi_side"].ravel()[sl], charts)
        bc[sl], ro[sl], hh[sl] = c, r, h
    mask = maps["mask"]
    hh = hh.reshape(H, W)
    hd = texel.dilate(hh, mask, 4)
    nrm = texel.normal_from_height(hd, maps["pos"], mask)
    cav = np.clip(texel.blur(hd, 3) - hd, 0, None)
    ao = np.clip(1.0 - cav / 0.00025, 0.6, 1.0)
    aol = _bake._bake_ao(ob, 1024, 16, 0, 0.03, False)
    k = H // 1024
    m1 = mask.reshape(1024, k, 1024, k).mean(axis=(1, 3)) > 0.99
    aol = texel.dilate(np.where(m1, aol, 1.0).astype(np.float32), m1, 12)
    from PIL import Image as _Im
    aol = np.asarray(_Im.fromarray(aol.astype(np.float32), mode="F").resize((W, H), _Im.BILINEAR), dtype=np.float32)
    ao = ao * (0.4 + 0.6 * aol)
    ch = {"bc": texel.dilate(bc.reshape(H, W, 3), mask, 24), "rough": texel.dilate(ro.reshape(H, W), mask, 24),
          "metal": np.zeros((H, W), dtype=np.float32), "normal": texel.dilate(nrm, mask, 24),
          "ao": texel.dilate(ao, mask, 24), "height": hd}
    info = _bake.write_set("RuleArms_Skin", ch, meta={"kind": "unique", "asset": "SK_RuleArms", "resolution_px": res,
                                                      "slots": ["M_RuleArms_Skin", "M_RuleArms_Nail"]})
    ctx.log("  RuleArms_Skin written: %s" % info["files"])


def textured_materials():
    """Preview materials on RuleArms_Skin (Unreal: M_RuleArms_Skin with the subsurface profile SP_RuleSkin,
    M_RuleArms_Nail default lit, both on the same three textures)."""
    out = {}
    d = paths.texture_set("RuleArms_Skin")
    for name, sss, coat in (("M_RuleArms_Skin", 0.30, 0.0), ("M_RuleArms_Nail", 0.05, 0.35)):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        nt = m.node_tree
        for nd in list(nt.nodes):
            nt.nodes.remove(nd)
        o = nt.nodes.new("ShaderNodeOutputMaterial")
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(b.outputs[0], o.inputs["Surface"])

        def img(tag, data):
            t = nt.nodes.new("ShaderNodeTexImage")
            t.image = bpy.data.images.load(os.path.join(d, "T_RuleArms_Skin_%s.png" % tag), check_existing=True)
            t.image.colorspace_settings.name = "Non-Color" if data else "sRGB"
            return t
        bc, nm, orm = img("BC", False), img("N", True), img("ORM", True)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs[0])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(bc.outputs["Color"], mix.inputs["A"])
        nt.links.new(sep.outputs["Red"], mix.inputs["B"])
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
        nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(nm.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], b.inputs["Normal"])
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (1.0, 0.38, 0.18)
        b.inputs["Subsurface Scale"].default_value = 0.003
        if coat:
            b.inputs["Coat Weight"].default_value = coat
            b.inputs["Coat Roughness"].default_value = 0.2
        out[name] = m
    return out


# ------------------------------------------------------------------------------------------------ gloved variant


def build_gloved(ctx):
    """The first version, rebuilt by characters.build, exported as SK_RuleArms_Gloved; its skin slot is renamed
    and the first version's skin set copied, so the bare arms can own RuleArms_Skin."""
    src, dst = paths.texture_set("RuleArms_Skin"), paths.texture_set("RuleArms_GlovedSkin")
    if not os.path.isdir(dst) and os.path.isdir(src):
        meta = os.path.join(src, "set.json")
        is_old = os.path.exists(meta) and "M_RuleArms_Nail" not in open(meta).read()
        if is_old:
            shutil.copytree(src, dst)
            for f in os.listdir(dst):
                if "RuleArms_Skin" in f:
                    os.rename(os.path.join(dst, f), os.path.join(dst, f.replace("RuleArms_Skin", "RuleArms_GlovedSkin")))
            ctx.log("copied the first version's skin set to %s" % dst)
    ctx.args.only = [o for o in (ctx.args.only or []) if o != "gloved"]
    C.build(ctx)
    r = ctx.rule
    ob = r["ob"]
    for s_ in ob.material_slots:
        if s_.material and s_.material.name == "M_RuleArms_Skin":
            m = s_.material.copy()
            m.name = "M_RuleArms_GlovedSkin"
            s_.material = m
    ob.name = "SK_RuleArms_Gloved"
    ctx.assets.clear()
    ctx.gloved = True
    return [ob]


# ------------------------------------------------------------------------------------------------ build


def build(ctx):
    only = ctx.args.only or []
    if "gloved" in only:
        return build_gloved(ctx)
    objs = []
    arm_pics = {"rule_arms_hero", "rule_arms_fp", "rule_hands", "rule_wire"}
    body_pics = {"rule_body_hero", "rule_face", "rule_turntable", "rule_wire"}
    if not only or "arms" in only or arm_pics & set(only):
        ob = build_arms(ctx)
        if ctx.args.bake:
            bake_skin(ctx, ob, ctx.args.res)
        if os.path.exists(os.path.join(paths.texture_set("RuleArms_Skin"), "T_RuleArms_Skin_BC.png")):
            meta = os.path.join(paths.texture_set("RuleArms_Skin"), "set.json")
            if os.path.exists(meta) and "M_RuleArms_Nail" in open(meta).read():
                textured_materials()
        from mi import rig
        rig.bind(ob, ctx.rule["arm"])
        objs += [ob, ctx.rule["bracelet"]]
    if not only or "body" in only or body_pics & set(only):
        from assets import _rule_body as B
        objs += B.build(ctx)
    return objs


def on_export(ctx, objs):
    if getattr(ctx, "gloved", False):
        p = char.export_character(ctx.rule["ob"], ctx.rule["arm"], name="SK_RuleArms_Gloved")
        ctx.log("exported %s" % p)
        old = os.path.join(paths.glb, "SK_RuleArms.sockets.json")
        if os.path.exists(old):
            shutil.copy(old, os.path.join(paths.glb, "SK_RuleArms_Gloved.sockets.json"))
        return
    from mi import export as _export
    r = getattr(ctx, "rule", None)
    if r and "ob" in r:
        p = char.export_character(r["ob"], r["arm"], name="SK_RuleArms")
        ctx.log("exported %s" % p)
        a = ctx.assets["SM_Character_RuleBracelet"]
        _export.export_asset(r["bracelet"], ctx.family, "none", None, a["notes"], None, None, slots=None, strict=False)
        M = C.attach_frame(r["R"], BRACELET_S)
        sk_path = os.path.join(paths.glb, "SK_RuleArms.sockets.json")
        sockets = json.load(open(sk_path)) if os.path.exists(sk_path) else {}
        sockets["SM_Character_RuleBracelet"] = {"socket": "Socket_Bracelet", "bone": "lowerarm_twist_01_r",
                                                "blender_world_rest": [round(v, 6) for row in M for v in row]}
        if "SM_Character_RuleWatch" in sockets:
            sockets["SM_Character_RuleWatch"]["worn"] = False
        with open(sk_path, "w") as f:
            json.dump(sockets, f, indent=1)
        ctx.log("sockets: %s" % list(sockets))
    if getattr(ctx, "body", None):
        from assets import _rule_body as B
        B.export(ctx)


def place_bracelet(r):
    arm, j = r["arm"], r["bracelet"]
    bone = "lowerarm_twist_01_r"
    j.parent = arm
    j.parent_type = "BONE"
    j.parent_bone = bone
    bpy.context.view_layer.update()
    rest_bone = arm.matrix_world @ arm.data.bones[bone].matrix_local @ Matrix.Translation((0, arm.data.bones[bone].length, 0))
    j.matrix_parent_inverse = rest_bone.inverted()
    j.matrix_basis = C.attach_frame(r["R"], BRACELET_S)


def on_preview(ctx, objs):
    from assets import _rule_preview as PV
    PV.preview(ctx, objs)
