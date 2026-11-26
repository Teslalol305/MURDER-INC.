"""Generated Goon: one Higgsfield image-to-3D take on SK_Goon_Hoodie (docs/unreal/spec/assets/characters.json,
goon_hoodie), as a comparison with the hand-built Goons (assets/characters.py).

Source (git-ignored, art/out/gen/goon/): concept1.png (gpt_image_2_6, A-pose front view) converted by
meshy_v7_image_to_3d (texture + PBR, a-pose, ultra, 300k triangles) into goon_meshy.glb.

    venv/bin/python art/blender/build.py build goon_generated --export --preview --samples 64
    venv/bin/python art/blender/build.py build goon_generated --preview --only goon_generated_hero

What the build does
1. Imports the generated GLB, joins it, puts the origin on the ground between the feet, facing -Y.
2. When the mannequin export exists (art/out/epic/: an SKM_Manny* / *Mannequin* skinned GLB, glTF or FBX, from the
   character agent), scales the mesh to the mannequin's height (+3 cm for the hood, 1.78 / 1.75 in the brief),
   measures the mesh's own shoulder-to-wrist and hip-to-ankle lines, poses the mannequin's upper arms, forearms,
   thighs and calves onto them (a rotation at the shoulder / hip, a stretch at the elbow / knee), copies skin weights
   from the posed mannequin mesh (nearest surface point, barycentric, smoothed, 4 influences), and moves the mesh
   back into the mannequin's reference pose by inverting the blended bone transforms per vertex. The mesh is then
   bound to the unchanged mannequin skeleton (same joints, same rest pose as SKM_Manny), so the Epic animations play
   on it without retargeting.
   Without the export the mesh is scaled to the brief (1.78 m over the hood) and exported unskinned.
3. Exports art/out/glb/SK_Goon_Hoodie_Gen.glb (skinned when bound, generated textures embedded: the PBR maps are
   unique to this mesh). Nothing derived from Epic's mannequin is committed: the skeleton only lives in art/out/.

Previews (art/previews, day rig): goon_generated_hero, _detail (3 m and 1 m), _pose (when bound), _wire.
"""
import glob
import math
import os
import tempfile

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from mi import export, geo, mat, paths, render, scene

FAMILY = {"name": "goon_generated", "description": "Generated (Higgsfield image-to-3D) SK_Goon_Hoodie for comparison"}
NAME = "SK_Goon_Hoodie_Gen"
SLOT = "M_Goon_Hoodie_Gen"
GEN = os.path.join(paths.out, "gen", "goon")
SRC = os.environ.get("GOON_SRC") or os.path.join(GEN, "goon_meshy.glb")     # GOON_SRC=... to try another take
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
EPIC = os.path.join(paths.out, "epic")
BRIEF_TOP = 1.78          # over the hood (brief: 1.75 m man in sneakers, 1.78 m over the hood)
HOOD_OVER_HEAD = 1.78 / 1.75

# limbs fitted onto the mesh: (upper bone, lower bone, end bone whose head is the far joint, side sign in X)
LIMBS = [("upperarm_l", "lowerarm_l", "hand_l", 1.0), ("upperarm_r", "lowerarm_r", "hand_r", -1.0),
         ("thigh_l", "calf_l", "foot_l", 1.0), ("thigh_r", "calf_r", "foot_r", -1.0)]


# ------------------------------------------------------------------------------------------------------ helpers

def _import(path, col):
    before = set(bpy.data.objects)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=False)
    else:
        raise ValueError(path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    return new


def _verts(ob):
    n = len(ob.data.vertices)
    co = np.empty(n * 3)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(n, 3)


def _set_verts(ob, co):
    ob.data.vertices.foreach_set("co", np.ascontiguousarray(co, dtype=np.float64).ravel())
    ob.data.update()


def _evaluated(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    tris = [tuple(p.vertices) for p in me.polygons]
    M = np.array(ob.matrix_world)
    co = co.reshape(n, 3) @ M[:3, :3].T + M[:3, 3]
    ev.to_mesh_clear()
    return co, tris


# --------------------------------------------------------------------------------------------- generated mesh

def load_generated(col):
    objs = _import(SRC, col)
    meshes = [o for o in objs if o.type == "MESH"]
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in objs:
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    ob = geo.join(meshes, NAME, col) if len(meshes) > 1 else meshes[0]
    ob.name = NAME
    ob.data.name = NAME
    scene.apply_transforms(ob)
    for p in ob.data.polygons:
        p.use_smooth = True
    if ob.material_slots and ob.material_slots[0].material:
        ob.material_slots[0].material.name = SLOT
    _normalise(ob)
    return ob


def _normalise(ob, top=None):
    """Ground at z = 0, the point between the feet at x = y = 0, optional uniform scale to a total height."""
    co = _verts(ob)
    lo, hi = co.min(0), co.max(0)
    if top:
        co = (co - [0, 0, lo[2]]) * (top / (hi[2] - lo[2]))
        lo, hi = co.min(0), co.max(0)
    feet = co[co[:, 2] < lo[2] + 0.06 * (hi[2] - lo[2])]
    c = np.array([(feet[:, 0].min() + feet[:, 0].max()) / 2, (feet[:, 1].min() + feet[:, 1].max()) / 2, lo[2]])
    _set_verts(ob, co - c)


def facing_check(ob):
    """The toes stick out in front of the shins: returns +1 when the mesh faces -Y (the convention)."""
    co = _verts(ob)
    feet = co[co[:, 2] < 0.05]
    shin = co[(co[:, 2] > 0.25) & (co[:, 2] < 0.35)]
    toe_front = feet[:, 1].min() - shin[:, 1].min()       # how far the feet reach to -Y beyond the shins
    toe_back = feet[:, 1].max() - shin[:, 1].max()        # and to +Y
    return 1 if -toe_front > toe_back else -1


# --------------------------------------------------------------------------------------------- the mannequin

def find_mannequin():
    if not os.path.isdir(EPIC):
        return None
    cands = []
    for ext in ("glb", "gltf", "fbx"):
        cands += glob.glob(os.path.join(EPIC, "**", "*.%s" % ext), recursive=True)
    def rank(p):
        b = os.path.basename(p).lower()
        return (0 if "skm_manny" in b else 1 if "manny" in b else 2 if "mannequin" in b else 3, len(b))
    cands = [p for p in cands if rank(p)[0] < 3 and "anim" not in os.path.basename(p).lower()
             and not os.path.basename(p).lower().startswith(("a_", "mm_", "mf_"))]
    return sorted(cands, key=rank)[0] if cands else None


def find_anims():
    """The exported animation clips (A_*.glb; the FBX twins are skipped)."""
    if not os.path.isdir(EPIC):
        return []
    return sorted(glob.glob(os.path.join(EPIC, "A_*.glb")))


def load_mannequin(path, col):
    """The mannequin armature and its skinned body (the GLB from the character agent: metres, facing -Y, identity
    object transforms; a file in centimetres or facing another way is brought to that)."""
    objs = _import(path, col)
    arm = next(o for o in objs if o.type == "ARMATURE")
    meshes = [o for o in objs if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)]
    body = max(meshes, key=lambda o: len(o.data.vertices))
    keep = {arm.name, body.name}
    for o in objs:                                        # bone-shape spheres, extra meshes, empties
        if o.name not in keep:
            for ch in list(o.children):
                if ch.name in keep:
                    mw = ch.matrix_world.copy()
                    ch.parent = None
                    ch.matrix_world = mw
    for nm in [o.name for o in objs if o.name not in keep]:
        bpy.data.objects.remove(bpy.data.objects[nm], do_unlink=True)
    for pb in arm.pose.bones:
        pb.custom_shape = None
    bpy.context.view_layer.update()
    ident = all((np.abs(np.array(o.matrix_world) - np.eye(4)) < 1e-6).all() for o in (arm, body))
    if not ident:
        _apply_object_transform(arm, body)
    co, _t = _evaluated(body)
    h = co[:, 2].max() - co[:, 2].min()
    if h > 10:                                            # centimetres
        _scale_rig(arm, body, 0.01)
    fwd = _forward(arm)
    ang = math.atan2(fwd[0], -fwd[1])                     # rotate so forward is -Y
    if abs(ang) > math.radians(30):                   # splayed feet are about 7 degrees off
        _rotate_rig(arm, body, -ang)
    return arm, body


def _apply_object_transform(arm, body):
    for o in (arm, body):
        o.select_set(False)
    mwb = body.matrix_world.copy()
    body.parent = None
    body.matrix_world = mwb
    scene.apply_transforms(arm)
    scene.apply_transforms(body)
    body.parent = arm
    body.matrix_parent_inverse = Matrix.Identity(4)
    md = next(m for m in body.modifiers if m.type == "ARMATURE")
    md.object = arm


def _scale_rig(arm, body, s):
    arm.scale = (s, s, s)
    body.parent = None
    body.scale = (s, s, s)
    bpy.context.view_layer.update()
    _apply_object_transform(arm, body)


def _rotate_rig(arm, body, ang):
    body.parent = None
    for o in (arm, body):
        o.matrix_world = Matrix.Rotation(ang, 4, "Z") @ o.matrix_world
    bpy.context.view_layer.update()
    _apply_object_transform(arm, body)


def _forward(arm):
    b = arm.data.bones
    for toe, foot in (("ball_l", "foot_l"), ("ball_r", "foot_r")):
        if toe in b and foot in b:
            d = b[toe].head_local - b[foot].head_local
            d.z = 0
            return d.normalized()
    return Vector((0, -1, 0))


def joint(arm, name):
    return np.array(arm.data.bones[name].head_local)


# --------------------------------------------------------------------------------------------- fitting

def mesh_joint(co, start, guess_end, side, end_slice):
    """Where the mesh's limb ends: the centroid of the cross-section of the limb at the far joint.
    start: shoulder or hip (skeleton); guess_end: skeleton wrist or ankle; end_slice: callable(co_side, d, t) -> mask."""
    sel = co[(co[:, 0] * side) > 0.02]
    end = np.array(guess_end, float)
    for _ in range(3):
        d = end - start
        d /= np.linalg.norm(d)
        rel = sel - start
        t = rel @ d
        radial = np.linalg.norm(rel - np.outer(t, d), axis=1)
        mask = end_slice(sel, d, t, radial)
        if mask.sum() < 20:
            break
        end = sel[mask].mean(0)
    return end


def arm_end_slice(length):
    def f(sel, d, t, radial):
        tip = t[radial < 0.12].max()                      # the finger tips along the arm line
        return (t > tip - 0.215) & (t < tip - 0.175) & (radial < 0.09)
    return f


def leg_end_slice(ankle_z):
    def f(sel, d, t, radial):
        return (np.abs(sel[:, 2] - ankle_z) < 0.012) & (radial < 0.12) & (sel[:, 2] > 0.03)
    return f


def fit_pose(arm, co, guess=None):
    """Pose the mannequin's limbs onto the generated mesh. Returns a log of the measured joints.
    guess: optional {upper bone: start point} for the search of the mesh's wrist or ankle (default: the
    skeleton's own joint; vultures.bind passes one when that search finds no cross-section)."""
    report = {}
    pbs = arm.pose.bones
    for pb in pbs:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    for up, lo, end, side in LIMBS:
        if up not in pbs or lo not in pbs or end not in pbs:
            continue
        S, E, W = joint(arm, up), joint(arm, lo), joint(arm, end)
        if up.startswith("upperarm"):
            Wm = mesh_joint(co, S, (guess or {}).get(up, W), side, arm_end_slice(np.linalg.norm(W - S)))
        else:
            Wm = mesh_joint(co, S, (guess or {}).get(up, W), side, leg_end_slice(W[2]))
        a, b = Vector(W - S).normalized(), Vector(Wm - S).normalized()
        R = a.rotation_difference(b).to_matrix().to_4x4()
        T = lambda p: Matrix.Translation(Vector(p))      # noqa: E731
        F_up = T(S) @ R @ T(-S)
        stretch = float(np.linalg.norm(Wm - S) / np.linalg.norm(W - S))
        # the elbow / knee: rotated, and moved along the limb by the length ratio
        E_new = np.array(F_up @ Vector(E))
        E_fit = S + (E_new - S) * stretch
        F_lo = T(E_fit) @ R @ T(-E)
        pbs[up].matrix = F_up @ arm.data.bones[up].matrix_local
        bpy.context.view_layer.update()
        pbs[lo].matrix = F_lo @ arm.data.bones[lo].matrix_local
        bpy.context.view_layer.update()
        # the far joint lands on the mesh's: stretch the end bone's head (wrist / ankle) along the lower bone
        W_now = np.array(pbs[end].head)
        k = Wm - W_now
        pbs[end].matrix = T(k) @ pbs[end].matrix
        bpy.context.view_layer.update()
        report[up] = dict(angle_deg=round(math.degrees(a.angle(b)), 2), stretch=round(stretch, 3),
                          mesh_end=[round(float(v), 3) for v in Wm], skel_end=[round(float(v), 3) for v in W])
    return report


def bone_fit_matrices(arm):
    """Per deform bone: armature-space matrix that takes the rest pose to the current (fitted) pose."""
    out = {}
    for pb in arm.pose.bones:
        b = arm.data.bones[pb.name]
        out[pb.name] = np.array(pb.matrix @ b.matrix_local.inverted())
    return out


# --------------------------------------------------------------------------------------------- weights

def body_weights(body):
    names = [g.name for g in body.vertex_groups]
    n = len(body.data.vertices)
    W = np.zeros((n, len(names)), np.float32)
    for v in body.data.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    return names, W


def transfer_weights(target_co, src_co, src_tris, src_W):
    """Nearest point on the source surface, barycentric blend of its triangle's vertex weights."""
    tris = []
    for t in src_tris:                                    # fan-triangulate quads / ngons
        for i in range(1, len(t) - 1):
            tris.append((t[0], t[i], t[i + 1]))
    tris = np.array(tris)
    bvh = BVHTree.FromPolygons([tuple(map(float, p)) for p in src_co], [tuple(t) for t in tris])
    out = np.zeros((len(target_co), src_W.shape[1]), np.float32)
    dist = np.zeros(len(target_co))
    for i, p in enumerate(target_co):
        loc, _nrm, fi, d = bvh.find_nearest(Vector(p))
        a, b, c = src_co[tris[fi]]
        bc = _bary(np.array(loc), a, b, c)
        out[i] = bc @ src_W[tris[fi]]
        dist[i] = d
    return out, dist


def _bary(p, a, b, c):
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
    d20, d21 = v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-14:
        return np.array([1.0, 0.0, 0.0])
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    bc = np.clip(np.array([1 - v - w, v, w]), 0, 1)
    return bc / bc.sum()


def smooth_weights(ob, W, iterations=6, alpha=0.5):
    me = ob.data
    e = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    n = len(me.vertices)
    deg = np.bincount(e.ravel(), minlength=n).astype(np.float32)
    deg[deg == 0] = 1
    for _ in range(iterations):
        acc = np.zeros_like(W)
        np.add.at(acc, e[:, 0], W[e[:, 1]])
        np.add.at(acc, e[:, 1], W[e[:, 0]])
        W = (1 - alpha) * W + alpha * acc / deg[:, None]
    return W


def limit_normalise(W, k=4):
    idx = np.argsort(-W, axis=1)[:, k:]
    np.put_along_axis(W, idx, 0.0, axis=1)
    W[W < 0.01] = 0
    s = W.sum(1, keepdims=True)
    s[s == 0] = 1
    return W / s


def write_groups(ob, names, W):
    ob.vertex_groups.clear()
    for j, nm in enumerate(names):
        col = W[:, j]
        nz = np.nonzero(col)[0]
        if len(nz) == 0:
            continue
        vg = ob.vertex_groups.new(name=nm)
        for w in np.unique(np.round(col[nz], 4)):
            vg.add([int(i) for i in nz[np.round(col[nz], 4) == w]], float(w), "REPLACE")


def unpose(co, names, W, fits):
    """Inverse linear blend skinning: per vertex, invert the weighted sum of the fitted bone matrices."""
    M = np.zeros((len(co), 4, 4))
    for j, nm in enumerate(names):
        if nm in fits and W[:, j].any():
            M += W[:, j, None, None] * fits[nm][None]
    bad = np.abs(M[:, 3, 3]) < 1e-6
    M[bad] = np.eye(4)
    h = np.concatenate([co, np.ones((len(co), 1))], 1)
    return np.einsum("nij,nj->ni", np.linalg.inv(M), h)[:, :3]


# --------------------------------------------------------------------------------------------- build

def build(ctx):
    if not os.path.exists(SRC):
        raise SystemExit("missing %s (the Higgsfield result)" % SRC)
    ob = load_generated(ctx.col)
    co = _verts(ob)
    ctx.log("generated mesh: %d vertices, %d faces, height %.3f m" % (len(co), len(ob.data.polygons), np.ptp(co[:, 2])))
    if facing_check(ob) < 0:
        ctx.log("the mesh faces +Y: turning it 180 degrees")
        _set_verts(ob, co * [-1, -1, 1])
    ctx.bound = False
    ctx.arm = None
    path = find_mannequin()
    if path is None:
        _normalise(ob, BRIEF_TOP)
        ctx.log("no mannequin export in %s: scaled to the brief, %.2f m over the hood, unbound" % (EPIC, BRIEF_TOP))
    else:
        bind_to_mannequin(ctx, ob, path)
    geo.ensure_wear(ob)
    ctx.ob = ob
    return [ob]


def bind_to_mannequin(ctx, ob, path):
    rig_col = scene.collection("Mannequin")
    arm, body = load_mannequin(path, rig_col)
    bco, btris = _evaluated(body)
    top = bco[:, 2].max()
    _normalise(ob, top * HOOD_OVER_HEAD)
    ctx.log("mannequin %s: %d bones, height %.3f m; mesh scaled to %.3f m" % (os.path.basename(path), len(arm.data.bones),
                                                                              top, top * HOOD_OVER_HEAD))
    co = _verts(ob)
    rep = fit_pose(arm, co)
    for k, v in rep.items():
        ctx.log("  fit %-12s %5.1f deg, length x%.3f, mesh joint %s, skeleton %s" % (k, v["angle_deg"], v["stretch"],
                                                                                     v["mesh_end"], v["skel_end"]))
    names, BW = body_weights(body)
    pco, _t = _evaluated(body)                            # the mannequin in the fitted pose
    ctx.log("transferring weights from %d mannequin vertices to %d" % (len(pco), len(co)))
    W, dist = transfer_weights(co, pco, btris, BW)
    ctx.log("  surface distance: median %.3f m, 99th pct %.3f m" % (np.median(dist), np.percentile(dist, 99)))
    # the generated gloves are spread flat, the mannequin's fingers are relaxed: they do not line up, so the
    # finger weights go to the hand (rigid gloves) rather than bending the wrong fingers
    for j, nm in enumerate(names):
        if nm.startswith(FINGERS) and nm[-2:] in ("_l", "_r") and ("hand" + nm[-2:]) in names:
            W[:, names.index("hand" + nm[-2:])] += W[:, j]
            W[:, j] = 0
    W = limit_normalise(smooth_weights(ob, W), 4)
    fits = bone_fit_matrices(arm)
    rest = unpose(co, names, W, fits)
    _set_verts(ob, rest)
    write_groups(ob, names, W)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    ob.parent = arm
    ob.matrix_parent_inverse = Matrix.Identity(4)
    md = ob.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    body.hide_render = True
    body.hide_viewport = True
    # proof: the fitted pose on the bound mesh gives back the generated mesh
    fit_pose(arm, co)
    back, _t = _evaluated(ob)
    err = np.linalg.norm(back - co, axis=1)
    ctx.log("  round trip (fitted pose on the bound mesh vs the generated mesh): mean %.4f m, max %.4f m"
            % (err.mean(), err.max()))
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    ctx.bound, ctx.arm, ctx.body = True, arm, body


# --------------------------------------------------------------------------------------------- export

def on_export(ctx, objs):
    ob = ctx.ob
    err, warn = export.validate(ob, None, strict_names=False)
    for e in err:
        ctx.log("validate ERROR: %s" % e)
    for w in warn:
        ctx.log("validate warning: %s" % w)
    path = os.path.join(paths.glb, NAME + ".glb")
    sel = [ob] + ([ctx.arm] if ctx.bound else [])
    scene.select_only(*sel)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=False,
        export_materials="EXPORT", export_image_format="AUTO", export_texcoords=True, export_normals=True,
        export_tangents=False, export_animations=False, export_skins=ctx.bound, export_def_bones=False,
        export_leaf_bone=False, export_rest_position_armature=True, export_influence_nb=4, export_morph=False,
        export_cameras=False, export_lights=False, export_extras=False, export_vertex_color="NONE")
    ctx.log("exported %s (%.1f MB, %s)" % (path, os.path.getsize(path) / 1e6, "skinned" if ctx.bound else "static"))


# --------------------------------------------------------------------------------------------- previews

def _ground():
    g = render.backdrop(size=60.0, color=(0.16, 0.155, 0.15), z=0.0)
    m = mat.from_scan("TS_Sidewalk_ScanBroom") if _has_set("TS_Sidewalk_ScanBroom") else None
    if m:
        g.data.materials.clear()
        g.data.materials.append(m)
        geo.uv_world_box(g, mat.scan_tile("TS_Sidewalk_ScanBroom"))
    return g


def _has_set(name):
    try:
        return os.path.exists(paths.texture_set(name))
    except Exception:
        return False


def apply_anim_pose(ctx, path, frac):
    """Pose ctx.arm like the first armature action in an exported animation file, at a fraction of its length."""
    col = scene.collection("AnimTmp")
    objs = _import(path, col)
    src = next((o for o in objs if o.type == "ARMATURE" and o.animation_data and o.animation_data.action), None)
    if src is None:
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
        return None
    act = src.animation_data.action
    f0, f1 = act.frame_range
    bpy.context.scene.frame_set(int(round(f0 + (f1 - f0) * frac)))
    bpy.context.view_layer.update()
    for pb in ctx.arm.pose.bones:
        s = src.pose.bones.get(pb.name)
        pb.matrix_basis = s.matrix_basis.copy() if s else Matrix.Identity(4)
    if "root" in ctx.arm.pose.bones:                      # keep the figure on its spot (root motion off)
        ctx.arm.pose.bones["root"].matrix_basis = Matrix.Identity(4)
    name = os.path.splitext(os.path.basename(path))[0]
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    return name


def on_preview(ctx, objs):
    a = ctx.args
    want = lambda n: not a.only or n in a.only            # noqa: E731
    P = paths.previews
    ob = ctx.ob
    render.setup(samples=a.samples)
    _ground()
    tmp = tempfile.gettempdir()

    if want("goon_generated_hero"):
        # front three-quarter and a back three-quarter (the crew mark) side by side in the design sun
        twin = ob.copy()
        twin.data = ob.data
        ctx.col.objects.link(twin)
        if ctx.bound:
            twin.modifiers["Armature"].object = ctx.arm
        twin.parent = None
        twin.matrix_world = Matrix.Translation((1.45, 0.45, 0)) @ Matrix.Rotation(math.radians(160), 4, "Z")
        ob_mw = ob.matrix_world.copy()
        render.rig_day(sun_azimuth=215.0, stops=0.4)
        render.cam_look((1.05, -4.9, 1.25), (0.7, 0.1, 0.92), lens=40, name="Cam_Hero")
        _p, sec = render.render_jpeg(os.path.join(P, "goon_generated_hero.jpg"), a.samples)
        bpy.data.objects.remove(twin, do_unlink=True)
        ob.matrix_world = ob_mw
        ctx.log("preview goon_generated_hero.jpg %.0fs" % sec)

    if want("goon_generated_detail"):
        render.rig_day(sun_azimuth=215.0, stops=0.4)
        shots = []
        render.cam_look((0.9, -2.85, 1.55), (0.0, 0.0, 1.12), lens=40, name="Cam_3m")
        p1 = os.path.join(tmp, "goon_det_3m.png")
        render.render_png(p1, a.samples, (640, 720))
        shots.append(p1)
        render.cam_look((0.45, -0.95, 1.5), (0.17, 0.0, 1.38), lens=40, name="Cam_1m")
        p2 = os.path.join(tmp, "goon_det_1m.png")
        render.render_png(p2, a.samples, (640, 720))
        shots.append(p2)
        render.contact_sheet(shots, os.path.join(P, "goon_generated_detail.jpg"), cols=2,
                             labels=["3 m", "1 m"])
        ctx.log("preview goon_generated_detail.jpg")

    if want("goon_generated_pose") and ctx.bound:
        anims = find_anims()
        # a run and a shouldered aim (the brief's deformation cases), else whatever clips there are
        pref = ("A_rifle_jog_fwd", "A_rifle_idle_ads", "A_unarmed_attack", "A_death_front")
        picks = [p for k in pref for p in anims if os.path.basename(p).startswith(k)][:2] or anims[:2]
        shots, labels = [], []
        render.rig_day(sun_azimuth=215.0, stops=0.4)
        for i, p in enumerate(picks or [None]):
            name = apply_anim_pose(ctx, p, 0.3) if p else None
            if not name:                                  # no animation file: a hand-posed swing and kneel
                hand_pose(ctx.arm, i)
                name = "hand pose %d" % (i + 1)
            render.cam_look((1.6, -3.4, 1.3), (0.0, 0.0, 0.85), lens=40, name="Cam_Pose")
            pp = os.path.join(tmp, "goon_pose_%d.png" % i)
            render.render_png(pp, a.samples, (640, 720))
            shots.append(pp)
            labels.append(name)
        for pb in ctx.arm.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        render.contact_sheet(shots, os.path.join(P, "goon_generated_pose.jpg"), cols=2, labels=labels)
        ctx.log("preview goon_generated_pose.jpg (%s)" % ", ".join(labels))

    if want("goon_generated_wire"):
        clay = mat.flat("Clay", (0.5, 0.5, 0.5), 0.6)
        wire = ob.copy()
        wire.data = ob.data.copy()
        ctx.col.objects.link(wire)
        wire.data.materials.clear()
        wire.data.materials.append(mat.flat("WireInk", (0.02, 0.02, 0.025), 0.5))
        wm = wire.modifiers.new("Wire", "WIREFRAME")
        wm.thickness = 0.0007
        wm.use_replace = True
        wm.use_even_offset = False
        if ctx.bound:
            wire.modifiers.move(len(wire.modifiers) - 1, 0)
        old = [s.material for s in ob.material_slots]
        for s in ob.material_slots:
            s.material = clay
        render.rig_day(sun_azimuth=215.0, stops=0.2)
        render.cam_look((0.35, -1.25, 1.45), (0.08, 0.0, 1.3), lens=40, name="Cam_Wire")
        p1 = os.path.join(tmp, "goon_wire_close.png")
        render.render_png(p1, max(24, a.samples // 2), (640, 720))
        wire.hide_render = True
        render.cam_look((0.8, -4.2, 1.0), (0.0, 0.0, 0.9), lens=40, name="Cam_Clay")
        p2 = os.path.join(tmp, "goon_wire_clay.png")
        render.render_png(p2, max(24, a.samples // 2), (640, 720))
        for s, m in zip(ob.material_slots, old):
            s.material = m
        bpy.data.objects.remove(wire, do_unlink=True)
        render.contact_sheet([p2, p1], os.path.join(P, "goon_generated_wire.jpg"), cols=2,
                             labels=["clay", "wire, 1.3 m"])
        ctx.log("preview goon_generated_wire.jpg")


def hand_pose(arm, which):
    """Two poses from the brief without animation files: 0 = right arm overhead swing, 1 = kneel on the right knee."""
    pbs = arm.pose.bones

    def rot(name, axis, deg):
        if name in pbs:
            b = arm.data.bones[name]
            head = b.head_local
            R = Matrix.Translation(head) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-head)
            pbs[name].matrix = R @ pbs[name].matrix
            bpy.context.view_layer.update()

    for pb in pbs:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    if which == 0:
        rot("upperarm_r", "X", 150)
        rot("lowerarm_r", "X", 35)
        rot("upperarm_l", "X", -25)
        rot("spine_03", "X", -8)
    else:
        rot("thigh_r", "X", 80)
        rot("calf_r", "X", -95)
        rot("thigh_l", "X", -80)
        rot("calf_l", "X", 85)
        rot("upperarm_l", "X", -50)
        rot("upperarm_r", "X", -50)
