"""SK_Rule, the full body (crew screen, cards), used by rule.py.

Sources (git-ignored, art/out/gen/rule/, jobs in gen_log.json): body_meshy.glb (meshy_v7 ultra, a-pose, 300k,
PBR, from the A-pose front picture of the reference sheet) and head_meshy.glb (meshy_v7 ultra from the front head
picture: the face is far denser there than on the body, whose head is 5 % of the picture). Hunyuan3d_v3 was tried
on the head as well and drifted (broader face, light eyes): not used.

1. Both meshes loaded, facing -Y, the body standing on z = 0, scaled to the mannequin's height + 1 cm (bandana).
2. Faces classified by their generated colour (shirt red, skin, chain silver). The body loses its head and neck
   above the collar; the head bust loses its shirt and chain. The bust is scaled so that collar-to-crown matches the
   body's, placed on the body's neckline, its neck tucked 2.5 cm into the body's collar (the join is under the
   collar and the chain, never in view).
3. Decimated (head 40k, body 80k triangles), joined: slots M_Rule_Head and M_Rule_Body (the generated 4K maps,
   embedded in the GLB as for the generated Goon: unique to this mesh), plus glossy eye covers (M_Rule_EyeWet).
4. Bound to the unchanged mannequin skeleton with goon_generated's method (limbs posed onto the mesh, weights from
   the posed mannequin surface, mesh moved back into the reference pose), fingers rigid on the hand.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import char, geo, gen3d, paths, scene

from . import goon_generated as GG

GEN = os.path.join(paths.out, "gen", "rule")
BODY = os.path.join(GEN, "body_meshy.glb")
HEAD = os.path.join(GEN, "head_meshy.glb")
NAME = "SK_Rule"
HEAD_TRIS = 50000
BODY_TRIS = 80000
TUCK = 0.045


def _classes(ob, tex):
    rgb, rough, metal = gen3d.face_samples(ob, tex, blur=2)
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    red = (r > 0.08) & (r > 2.4 * g) & (r > 2.4 * b)
    mx, mn = rgb.max(1), rgb.min(1)
    grey = ((mx - mn) < 0.25 * np.maximum(mx, 1e-4)) & (mx > 0.18)
    return red, grey, rgb


def _neckline(c, a, red):
    """Height of the shirt collar: slicing down from the crown, the bandana (mostly red), the head (little red:
    a bandana tail at most), then the first slice that is mostly red again is the collar and shoulders."""
    z = c[:, 2]
    top, bot = z.max(), z.min()
    step = 0.008 * (top - bot)
    seen_head = False
    zz = top
    while zz > bot + step:
        m = (z <= zz) & (z > zz - step)
        if m.sum() >= 8:
            f = float((a[m] * red[m]).sum() / max(a[m].sum(), 1e-12))
            if f < 0.3:
                seen_head = True
            elif seen_head and f > 0.55:
                return float(zz)
        zz -= step
    return float(np.percentile(z, 80))


def _base_colour(ob, tex, path):
    """The generated base colour, found through the BSDF's Base Color link (Meshy's image names do not say
    which map is which, so gen3d.load can take the ORM image for it)."""
    m = ob.data.materials[0]
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    node, seen = b.inputs["Base Color"].links[0].from_node if b.inputs["Base Color"].links else None, 0
    while node is not None and node.type != "TEX_IMAGE" and seen < 6:
        ins = [i for i in node.inputs if i.links]
        node = ins[0].links[0].from_node if ins else None
        seen += 1
    if node is not None and node.image is not None:
        cache = os.path.splitext(path)[0] + "_maps"
        tex["bc"] = gen3d._image_array(node.image, True, cache + "_bc")
        # the generated atlas is 2K: a 4K upscale of it (bytedance upscaler, gen_log.json) replaces it when present
        up = os.path.splitext(path)[0] + "_bc_4k.png"
        if os.path.exists(up):
            img = bpy.data.images.load(up, check_existing=True)
            img.colorspace_settings.name = "sRGB"
            node.image = img
    return tex


def load_parts(col, log=print):
    body, btex = gen3d.load(BODY, NAME, col)
    head, htex = gen3d.load(HEAD, "Rule_Head", col)
    btex = _base_colour(body, btex, BODY)
    htex = _base_colour(head, htex, HEAD)
    for ob in (body, head):
        co = gen3d.verts(ob)
        co -= [(co[:, 0].min() + co[:, 0].max()) / 2, (co[:, 1].min() + co[:, 1].max()) / 2, co[:, 2].min()]
        gen3d.set_verts(ob, co)
        for p in ob.data.polygons:
            p.use_smooth = True
    if GG.facing_check(body) < 0:
        gen3d.set_verts(body, gen3d.verts(body) * [-1, -1, 1])
        log("  body turned to face -Y")
    return body, btex, head, htex


def _mid(v):
    return float((np.percentile(v, 2) + np.percentile(v, 98)) / 2) if len(v) else 0.0


def _largest_part(ob):
    """Keep the largest connected piece (generated busts carry stray sheets)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    seen = np.zeros(len(bm.verts), dtype=bool)
    parts = []
    for v0 in bm.verts:
        if seen[v0.index]:
            continue
        stack, comp = [v0], []
        seen[v0.index] = True
        while stack:
            v = stack.pop()
            comp.append(v.index)
            for e in v.link_edges:
                w = e.other_vert(v)
                if not seen[w.index]:
                    seen[w.index] = True
                    stack.append(w)
        parts.append(comp)
    parts.sort(key=len, reverse=True)
    drop = [bm.verts[i] for p in parts[1:] if len(p) < 0.2 * len(parts[0]) for i in p]
    bmesh.ops.delete(bm, geom=drop, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


NECK_CENTRE = [0.0, 0.0]


def swap_head(body, btex, head, htex, log=print, keep_neck=False):
    """keep_neck (review round 1): the body keeps its own neck, _rule_head.neck_join cuts both on one plane."""
    cb, nb, ab = gen3d.face_arrays(body)
    redb, greyb, _ = _classes(body, btex)
    topb = cb[:, 2].max()
    zb = _neckline(cb, ab, redb)
    sl = (cb[:, 2] > zb + 0.015) & (cb[:, 2] < zb + 0.045) & ~redb & (np.abs(cb[:, 0]) < 0.12)
    hx, hy = _mid(cb[sl, 0]), _mid(cb[sl, 1])                       # centre of the neck's section
    near = np.hypot(cb[:, 0] - hx, cb[:, 1] - hy) < 0.085          # the neck, not the shoulders or arms
    kill = (cb[:, 2] > zb + 0.06) | ((cb[:, 2] > zb - 0.03) & ~redb & near)
    if keep_neck:
        kill = cb[:, 2] > zb + 0.06
    NECK_CENTRE[:] = [hx, hy]
    gen3d.delete_faces(body, kill)
    log("  body: neckline z %.3f of %.3f, head and neck removed (%d faces)" % (zb, topb, kill.sum()))
    ch, nh, ah = gen3d.face_arrays(head)
    redh, greyh, _ = _classes(head, htex)
    toph = ch[:, 2].max()
    zh = _neckline(ch, ah, redh)
    unit = (toph - zh) / (topb - zb)                       # bust units per metre
    chin = zh + 0.035 * unit                              # the back of the collar, below the lips
    killh = (redh & (ch[:, 2] < chin)) | (ch[:, 2] < zh - TUCK * unit)
    gen3d.delete_faces(head, killh)
    _largest_part(head)
    s = (topb - zb) / (toph - zh)
    co = gen3d.verts(head)
    co = (co - [0, 0, zh]) * s
    ch2, _n2, _a2 = gen3d.face_arrays(head)
    ch2 = (ch2 - [0, 0, zh]) * s
    redh2, _g2, _ = _classes(head, htex)
    sl = (ch2[:, 2] > 0.015) & (ch2[:, 2] < 0.045) & ~redh2
    dx, dy = hx - _mid(ch2[sl, 0]), hy - _mid(ch2[sl, 1])
    co += [dx, dy, zb]
    gen3d.set_verts(head, co)
    if keep_neck:
        log("  head: neckline %.3f of %.3f in the bust, scale %.3f, bust moved by (%.3f, %.3f)" % (zh, toph, s, dx, dy))
        return zb
    # the cut edge of the bust's neck is carried 1.8 cm down (and its next ring half as far), so it ends under
    # the body's collar all round instead of just above it at the front
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(head.data)
    edge_v = {v.index for e in bm.edges if len(e.link_faces) == 1 for v in e.verts}
    bm.verts.ensure_lookup_table()
    ring = set()
    for i in edge_v:
        for e in bm.verts[i].link_edges:
            ring.add(e.other_vert(bm.verts[i]).index)
    ring -= edge_v
    bm.free()
    low = co[:, 2] < zb + 0.04
    for idx, d in ((sorted(edge_v), 0.018), (sorted(ring), 0.006)):
        idx = np.array([i for i in idx if low[i]], dtype=np.int64)
        if len(idx):
            co[idx, 2] -= d
    gen3d.set_verts(head, co)
    log("  head: neckline %.3f of %.3f in the bust, scale %.3f, %d faces removed; neck centres body (%.3f, %.3f), "
        "bust moved by (%.3f, %.3f)" % (zh, toph, s, killh.sum(), hx, hy, dx, dy))
    return zb


def eye_covers(head, htex, col):
    """Thin glossy covers over the eyes (the generated head has painted eyes): a tear film that catches the
    light. Found as the darkest small regions on the front of the face around eye height."""
    c, n, a = gen3d.face_arrays(head)
    rgb, _r, _m = gen3d.face_samples(head, htex, blur=1)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    top = c[:, 2].max()
    front = (n[:, 1] < -0.5)
    out = []
    from mi import mat as _mat
    wet = _mat.flat("M_Rule_EyeWet", (0.02, 0.02, 0.02), 0.03, 0.0)
    b = wet.node_tree.nodes.get("Principled BSDF")
    b.inputs["Alpha"].default_value = 0.18
    for sx in (-1, 1):
        m = front & (np.sign(c[:, 0]) == sx) & (np.abs(c[:, 0]) > 0.012) & (np.abs(c[:, 0]) < 0.05) & (c[:, 2] > top - 0.17) & (c[:, 2] < top - 0.08)
        if m.sum() < 10:
            continue
        thr = np.percentile(lum[m], 12)
        e = m & (lum <= thr)
        ctr = np.average(c[e], axis=0, weights=a[e])
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=0.0125, location=(0, 0, 0))
        sp = bpy.context.active_object
        sp.name = "EyeWet_%s" % ("L" if sx > 0 else "R")
        sp.scale = (1.0, 0.42, 0.62)
        sp.location = (ctr[0], ctr[1] - 0.0015 + 0.0125 * 0.42 * 0.2, ctr[2])
        scene.apply_transforms(sp)
        co = gen3d.verts(sp)
        gen3d.delete_faces(sp, np.array([p.center.y > ctr[1] - 0.001 for p in sp.data.polygons]))
        sp.data.materials.append(wet)
        scene.move_to(sp, col)
        out.append(sp)
    return out


def build(ctx):
    if not (os.path.exists(BODY) and os.path.exists(HEAD)):
        ctx.log("SK_Rule: missing %s or %s" % (BODY, HEAD))
        return []
    col = ctx.col
    body, btex, head, htex = load_parts(col, ctx.log)
    # the mannequin: height and the skeleton to bind to
    rig_col = scene.collection("Mannequin_Body")
    arm, mbody = GG.load_mannequin(char.MANNEQUIN, rig_col)
    bco, btris = GG._evaluated(mbody)
    top = bco[:, 2].max() * 1.01
    GG._normalise(body, top)
    from assets import _rule_head as HD
    zb = swap_head(body, btex, head, htex, ctx.log, keep_neck=True)
    HD.check_landmarks(zb, ctx.log)
    hx, hy = NECK_CENTRE
    # review round 1: a clean neck join, the proportions, the ears (on the full-resolution bust)
    ring, plane = HD.neck_join(body, head, None, zb, hx, hy, ctx.log)
    HD.clean_neck_flaps(head, zb, hx, hy, ctx.log)
    HD.warp_face(head, ctx.log)
    HD.ears(head, ctx.log)
    redb, _g, _rgb = _classes(body, btex)
    HD.reshape_body_neck(body, redb, ring, plane, hx, hy, ctx.log)
    HD.tuck_bust(head, plane, hx, hy, ctx.log)
    gen3d.decimate(head, 1.0, target=HEAD_TRIS)
    gen3d.decimate(body, 1.0, target=BODY_TRIS)
    for ob, slot in ((head, "M_Rule_Head"), (body, "M_Rule_Body")):
        if ob.data.materials and ob.data.materials[0]:
            ob.data.materials[0].name = slot
    # real eyes in sockets, then the head's own maps (graded, cleaned, lids, hair, bandana print, pores, ORM)
    cen = HD.eye_geometry(head, col, ctx.log)
    eyes = HD.eye_parts(cen, col, ctx.log)
    res = getattr(ctx.args, "res", None) or 4096
    m = HD.head_textures(head, min(int(res), 4096), log=ctx.log)
    old = head.data.materials[0]
    head.data.materials[0] = m
    if old is not None:
        old.name = "M_Rule_Head__generated"
    m.name = "M_Rule_Head"
    eyes = eyes + [HD.bandana_tail(head, col, ctx.log)]
    from assets import _rule_bodytex as BT
    GG.fit_pose(arm, gen3d.verts(body))
    bpy.context.view_layer.update()
    wrists = [np.array(arm.matrix_world @ arm.pose.bones["hand_" + sd].head) for sd in ("l", "r")]
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    BT.body_textures(body, btex, ctx.log, wrists=wrists)
    red_v = np.zeros(len(body.data.vertices), dtype=bool)
    redf, _g2, _r2 = _classes(body, btex)
    for p in body.data.polygons:
        if redf[p.index]:
            red_v[list(p.vertices)] = True
    skin_v = np.zeros(len(body.data.vertices), dtype=bool)
    for p in body.data.polygons:
        if not redf[p.index]:
            skin_v[list(p.vertices)] = True
    ob = geo.join([body, head] + eyes, NAME, col)
    for p in ob.data.polygons:
        p.use_smooth = True
    n_tri = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    ctx.log("SK_Rule: %d triangles, %.3f m" % (n_tri, gen3d.verts(ob)[:, 2].max()))
    # bind (goon_generated's proven method)
    co = GG._verts(ob)
    rep = GG.fit_pose(arm, co)
    for k, v in rep.items():
        ctx.log("  fit %-12s %5.1f deg, length x%.3f" % (k, v["angle_deg"], v["stretch"]))
    names, BW = GG.body_weights(mbody)
    pco, _t = GG._evaluated(mbody)
    W, dist = GG.transfer_weights(co, pco, btris, BW)
    ctx.log("  weights: surface distance median %.3f m, 99th pct %.3f m" % (np.median(dist), np.percentile(dist, 99)))
    for j, nm in enumerate(names):
        if nm.startswith(GG.FINGERS) and nm[-2:] in ("_l", "_r") and ("hand" + nm[-2:]) in names:
            W[:, names.index("hand" + nm[-2:])] += W[:, j]
            W[:, j] = 0
    # the head and the neck above the collar follow the head and neck bones only (no shoulder or clavicle pull)
    hz = co[:, 2] > zb + 0.02
    keep = [names.index(k) for k in ("head", "neck_01", "neck_02") if k in names]
    if keep:
        Wk = np.zeros_like(W)
        Wk[:, keep] = W[:, keep]
        s = Wk.sum(1)
        ok = hz & (s > 1e-3)
        W[ok] = Wk[ok] / s[ok, None]
    W = GG.limit_normalise(GG.smooth_weights(ob, W), 4)
    # after the smoothing, which would carry the arm's weight back into the shirt
    W = GG.limit_normalise(shirt_weights(co, names, W, red_v, skin_v, ctx.log), 4)
    fits = GG.bone_fit_matrices(arm)
    rest = GG.unpose(co, names, W, fits)
    GG._set_verts(ob, rest)
    GG.write_groups(ob, names, W)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    ob.parent = arm
    ob.matrix_parent_inverse = Matrix.Identity(4)
    md = ob.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    mbody.hide_render = True
    mbody.hide_viewport = True
    GG.fit_pose(arm, co)
    back, _t = GG._evaluated(ob)
    err = np.linalg.norm(back - co, axis=1)
    ctx.log("  round trip: mean %.4f m, max %.4f m" % (err.mean(), err.max()))
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    ob = body_bracelet(ob, arm, col, ctx.log)
    geo.ensure_wear(ob)
    n_tri = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    ctx.body = dict(ob=ob, arm=arm, mbody=mbody, tris=n_tri)
    return [ob]


def export(ctx):
    from mi import export as _export
    b = ctx.body
    ob, arm = b["ob"], b["arm"]
    path = os.path.join(paths.glb, NAME + ".glb")
    char.rest_pose(arm)
    ob.data.validate(clean_customdata=False)
    scene.select_only(ob, arm)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=False,
        export_materials="EXPORT", export_image_format="AUTO", export_texcoords=True, export_normals=True,
        export_tangents=False, export_animations=False, export_skins=True, export_def_bones=False,
        export_leaf_bone=False, export_rest_position_armature=True, export_armature_object_remove=True,
        export_influence_nb=4, export_morph=False, export_cameras=False, export_lights=False, export_extras=False,
        export_vertex_color="NONE")
    ctx.log("exported %s (%.1f MB)" % (path, os.path.getsize(path) / 1e6))
    from assets import rule as RU
    RU.export_checks(ob, arm, path, ctx.log)


def shirt_weights(co, names, W, red_v, skin_v, log=print):
    """Review round 1 (the shirt's side and armhole flared like a wing in the jog): the sleeveless shirt follows
    the chest, not the arm. On shirt vertices the upper arm's share goes to the clavicle above the armpit and to
    spine_03 below it; at the armhole's rim 60 % of it is kept (the rim follows the arm), fading to none 8 cm in."""
    from mathutils import kdtree
    nb = len(red_v)
    out = W.copy()
    moved = 0
    for sd in ("l", "r"):
        ups = [names.index(n) for n in names if n.startswith("upperarm") and n.endswith("_" + sd)]
        if not ups:
            continue
        cl = names.index("clavicle_" + sd) if ("clavicle_" + sd) in names else None
        sp = names.index("spine_03") if "spine_03" in names else None
        side = np.sign(co[:nb, 0]) == (1 if sd == "l" else -1)
        rim = np.nonzero(red_v & skin_v & side & (co[:nb, 2] > 1.15) & (np.abs(co[:nb, 0]) > 0.10))[0]
        if not len(rim):
            continue
        z_pit = float(np.percentile(co[rim, 2], 10))
        kd = kdtree.KDTree(len(rim))
        for i, v in enumerate(rim):
            kd.insert(co[v], i)
        kd.balance()
        sel = np.nonzero(red_v & ~skin_v & side & (co[:nb, 2] > 1.0))[0]
        for v in sel:
            _c, _i, d = kd.find(co[v])
            share = W[v, ups].sum()
            if share < 1e-4:
                continue
            keep = 0.60 * (1.0 - min(d / 0.08, 1.0)) ** 1.5
            give = share * (1 - keep)
            out[v, ups] *= keep
            tgt = cl if (co[v, 2] > z_pit + 0.03 and cl is not None) else sp
            if tgt is not None:
                out[v, tgt] += give
            moved += 1
    log("  shirt: upper-arm weight moved to the clavicle / spine_03 on %d vertices" % moved)
    return out


def body_bracelet(ob, arm, col, log=print):
    """The arms' bracelet (rule.bracelet) fitted to SK_Rule's right forearm 3 cm above the wrist, at this body's
    own section there, rigid on lowerarm_twist_01_r; joined into SK_Rule (slots M_Character_RuleBracelet_*)."""
    from assets import rule as RU
    bpy.context.view_layer.update()
    bones = arm.data.bones
    E = np.array(arm.matrix_world @ bones["lowerarm_r"].head_local)
    Wr = np.array(arm.matrix_world @ bones["hand_r"].head_local)
    af = (Wr - E) / np.linalg.norm(Wr - E)
    c = Wr - af * RU.BRACELET_S
    up = np.array([0.0, 0.0, 1.0])
    v = up - af * (up @ af)
    v /= np.linalg.norm(v)
    xax = np.cross(-af, v)
    co = gen3d.verts(ob)
    q = co - c
    t = q @ af
    rad = q - t[:, None] * af
    near = (np.abs(t) < 0.008) & (np.linalg.norm(rad, axis=1) < 0.07)
    # the section's outer surface: the farthest 10 % in each direction
    a = float(np.percentile(np.abs(rad[near] @ xax), 92)) if near.sum() > 20 else 0.030
    b = float(np.percentile(np.abs(rad[near] @ v), 92)) if near.sum() > 20 else 0.024
    br = RU.bracelet(col, sec=(a, b))
    M = Matrix.Identity(4)
    for i in range(3):
        M[i][0], M[i][1], M[i][2], M[i][3] = xax[i], -af[i], v[i], c[i]
    br.matrix_world = M
    scene.apply_transforms(br)
    bone = "lowerarm_twist_01_r" if "lowerarm_twist_01_r" in bones else "lowerarm_r"
    g = br.vertex_groups.new(name=bone)
    g.add(list(range(len(br.data.vertices))), 1.0, "REPLACE")
    n = sum(len(p.vertices) - 2 for p in br.data.polygons)
    ob = geo.join([ob, br])
    log("  bracelet fitted on the right forearm (section %.1f x %.1f mm, %d triangles, rigid on %s)"
        % (2000 * a, 2000 * b, n, bone))
    return ob
