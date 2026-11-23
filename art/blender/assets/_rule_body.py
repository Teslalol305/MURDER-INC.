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
HEAD_TRIS = 40000
BODY_TRIS = 80000
TUCK = 0.025


def _classes(ob, tex):
    rgb, rough, metal = gen3d.face_samples(ob, tex, blur=2)
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    red = (r > 0.08) & (r > 2.4 * g) & (r > 2.4 * b)
    mx, mn = rgb.max(1), rgb.min(1)
    grey = ((mx - mn) < 0.25 * np.maximum(mx, 1e-4)) & (mx > 0.18)
    return red, grey, rgb


def _neckline(c, red, x0, top, frac=(0.70, 0.93)):
    """Height of the front of the shirt collar: the highest red face near the front centre line."""
    z = c[:, 2]
    yc = np.median(c[(z > top * frac[0]) & (z < top * frac[1]), 1])
    m = red & (np.abs(c[:, 0] - x0) < 0.035 * top / 1.8) & (c[:, 1] < yc) & (z > top * frac[0]) & (z < top * frac[1])
    return float(z[m].max())


def load_parts(col, log=print):
    body, btex = gen3d.load(BODY, NAME, col)
    head, htex = gen3d.load(HEAD, "Rule_Head", col)
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


def swap_head(body, btex, head, htex, log=print):
    cb, _nb, _ab = gen3d.face_arrays(body)
    redb, greyb, _ = _classes(body, btex)
    topb = cb[:, 2].max()
    zb = _neckline(cb, redb, 0.0, topb)
    above = cb[:, 2] > zb
    hx, hy = float(np.median(cb[above & (cb[:, 2] > zb + 0.08), 0])), float(np.median(cb[above & (cb[:, 2] > zb + 0.08), 1]))
    kill = (cb[:, 2] > zb + 0.012) & (~redb | (cb[:, 2] > zb + 0.05))
    kill |= greyb & (cb[:, 2] > zb - 0.01) & (cb[:, 2] < zb + 0.05)
    gen3d.delete_faces(body, kill)
    log("  body: neckline z %.3f of %.3f, head and neck removed (%d faces)" % (zb, topb, kill.sum()))
    ch, _nh, _ah = gen3d.face_arrays(head)
    redh, greyh, _ = _classes(head, htex)
    toph = ch[:, 2].max()
    zh = _neckline(ch, redh, 0.0, toph, frac=(0.10, 0.62))
    chin = zh + 0.10 * toph
    killh = (redh & (ch[:, 2] < chin)) | (ch[:, 2] < zh - TUCK * toph / 0.9) | (greyh & (ch[:, 2] < chin))
    gen3d.delete_faces(head, killh)
    s = (topb - zb) / (toph - zh)
    co = gen3d.verts(head)
    co = (co - [0, 0, zh]) * s
    ch2 = co[co[:, 2] > 0.08]
    co += [hx - float(np.median(ch2[:, 0])), hy - float(np.median(ch2[:, 1])), zb]
    gen3d.set_verts(head, co)
    log("  head: neckline %.3f of %.3f in the bust, scale %.3f, %d faces removed" % (zh, toph, s, killh.sum()))
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
    zb = swap_head(body, btex, head, htex, ctx.log)
    gen3d.decimate(head, 1.0, target=HEAD_TRIS)
    gen3d.decimate(body, 1.0, target=BODY_TRIS)
    for ob, slot in ((head, "M_Rule_Head"), (body, "M_Rule_Body")):
        if ob.data.materials and ob.data.materials[0]:
            ob.data.materials[0].name = slot
    eyes = eye_covers(head, htex, col)
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
    geo.ensure_wear(ob)
    ctx.body = dict(ob=ob, arm=arm, mbody=mbody, tris=n_tri)
    return [ob]


def export(ctx):
    from mi import export as _export
    b = ctx.body
    ob, arm = b["ob"], b["arm"]
    path = os.path.join(paths.glb, NAME + ".glb")
    char.rest_pose(arm)
    scene.select_only(ob, arm)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=False,
        export_materials="EXPORT", export_image_format="AUTO", export_texcoords=True, export_normals=True,
        export_tangents=False, export_animations=False, export_skins=True, export_def_bones=False,
        export_leaf_bone=False, export_rest_position_armature=True, export_armature_object_remove=True,
        export_influence_nb=4, export_morph=False, export_cameras=False, export_lights=False, export_extras=False,
        export_vertex_color="NONE")
    ctx.log("exported %s (%.1f MB)" % (path, os.path.getsize(path) / 1e6))
