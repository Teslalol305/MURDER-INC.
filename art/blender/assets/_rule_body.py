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


def swap_head(body, btex, head, htex, log=print):
    cb, nb, ab = gen3d.face_arrays(body)
    redb, greyb, _ = _classes(body, btex)
    topb = cb[:, 2].max()
    zb = _neckline(cb, ab, redb)
    sl = (cb[:, 2] > zb + 0.015) & (cb[:, 2] < zb + 0.045) & ~redb & (np.abs(cb[:, 0]) < 0.12)
    hx, hy = _mid(cb[sl, 0]), _mid(cb[sl, 1])                       # centre of the neck's section
    near = np.hypot(cb[:, 0] - hx, cb[:, 1] - hy) < 0.085          # the neck, not the shoulders or arms
    kill = (cb[:, 2] > zb + 0.06) | ((cb[:, 2] > zb - 0.055) & ~redb & near)
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
    # the bottom of the neck narrows a little so its cut edge stays inside the body's collar
    t = np.clip((zb + 0.015 - co[:, 2]) / 0.035, 0, 1)
    k = 1.0 - 0.10 * t
    co[:, 0] = hx + (co[:, 0] - hx) * k
    co[:, 1] = hy + (co[:, 1] - hy) * k
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
