"""Characters on the UE5 mannequin skeleton (SK_Mannequin): import of the reference files, skinned export onto the
existing skeleton, weight transfer, smooth skinning, pose import. Builds on mi.rig (import_glb, inspect_glb).

The reference files are Epic's (licence: usable in this Unreal game, never published) and live only under
art/out/epic/ (git-ignored): SKM_Manny_Simple.glb (mesh + full skeleton, 89 joints) and A_<clip>.glb (the same mesh
and skeleton with one animation). They are written on the box by tools/box/chars/ue_export.py with the engine's
glTF exporter. docs/unreal/CHARACTERS.md has the proof that this path round-trips bone for bone.

    from mi import char
    arm, body = char.import_mannequin()                  # armature 'Mannequin' (bone rests exactly as in Unreal)
    char.transfer_weights(arms_mesh, body, bones=...)    # skin weights from the mannequin's surface
    char.smooth_weights(arms_mesh, iterations=4)
    char.export_character(arms_mesh, arm)                # art/out/glb/SK_RuleArms.glb, full skeleton, metres, +Y up
    char.pose_from_clip(arm, "rifle_idle_ads", frame=0)  # pose our armature with a reference clip

Axes and bones. The glTF importer runs with bone_heuristic BLENDER: every bone is turned +90 deg about its local X
for display and the exporter turns it back (io_scene_gltf2 blender/exp/tree.py), so the joint rest rotations and
translations written by export_character are the ones Unreal wrote, to float precision (round_trip_report).
Blender scene: metres, Z up, the mannequin stands at the origin facing -Y (Unreal +Y). Bone positions are read
from the imported armature, never typed in.
"""
import json
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from . import export as _export
from . import geo as _geo
from . import paths
from . import rig as _rig
from . import scene as _scene

EPIC = os.path.join(paths.out, "epic")
MANNEQUIN = os.path.join(EPIC, "SKM_Manny_Simple.glb")
CLIPS = ("rifle_idle_ads", "pistol_idle_ads", "rifle_reload", "pistol_reload", "rifle_jog_fwd", "unarmed_attack",
         "death_front")

ARM_BONES = {
    side: ["clavicle_" + side, "upperarm_" + side, "upperarm_twist_01_" + side, "upperarm_twist_02_" + side,
           "lowerarm_" + side, "lowerarm_twist_01_" + side, "lowerarm_twist_02_" + side, "hand_" + side]
    + ["%s_%s_%s" % (f, k, side) for f in ("index", "middle", "ring", "pinky") for k in ("metacarpal", "01", "02", "03")]
    + ["thumb_%s_%s" % (k, side) for k in ("01", "02", "03")]
    for side in ("l", "r")}


# ------------------------------------------------------------------------------------------------ import

def import_mannequin(path=MANNEQUIN, name="Mannequin"):
    """(armature, body mesh) of the reference mannequin in a collection 'Ref_Mannequin'."""
    arm, meshes, col = _rig.import_glb(path, "Ref_" + name)
    arm.name = arm.data.name = name
    body = max(meshes, key=lambda o: len(o.data.vertices))
    body.name = name + "_Body"
    return arm, body


def clip_path(clip):
    return os.path.join(EPIC, "A_%s.glb" % clip)


def import_clip(clip):
    """Import a reference clip; returns (armature, action, frame range). The clip's own mesh is deleted."""
    arm, meshes, col = _rig.import_glb(clip_path(clip), "Clip_" + clip)
    for m in meshes:
        bpy.data.objects.remove(m, do_unlink=True)
    act = arm.animation_data.action if arm.animation_data else None
    rng = tuple(int(v) for v in act.frame_range) if act else (0, 0)
    arm.name = "Clip_" + clip
    return arm, act, rng


def pose_from_clip(arm, clip, frame=None, src=None):
    """Pose `arm` (same skeleton, same rests) like the clip at `frame` (default: the first frame).
    Copies every bone's local basis matrix, which is valid because the rests are identical (round-trip proof).
    Returns the source armature so further frames can be taken with pose_from_armature."""
    if src is None:
        src, act, rng = import_clip(clip)
        if frame is None:
            frame = rng[0]
    if frame is not None:
        bpy.context.scene.frame_set(int(frame))
    pose_from_armature(arm, src)
    return src


def pose_from_armature(arm, src):
    bpy.context.view_layer.update()
    for pb in arm.pose.bones:
        sp = src.pose.bones.get(pb.name)
        pb.matrix_basis = sp.matrix_basis.copy() if sp else Matrix.Identity(4)
    bpy.context.view_layer.update()


def rest_pose(arm):
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def bone_frame(arm, bone, posed=False):
    """(head, tail, x_axis, z_axis) of a bone in world space (rest or current pose)."""
    M = arm.matrix_world @ (arm.pose.bones[bone].matrix if posed else arm.data.bones[bone].matrix_local)
    b = arm.data.bones[bone]
    head = M @ Vector((0, 0, 0))
    tail = M @ Vector((0, b.length, 0))
    return head, tail, (M.to_3x3() @ Vector((1, 0, 0))).normalized(), (M.to_3x3() @ Vector((0, 0, 1))).normalized()


# ------------------------------------------------------------------------------------------------ weights

def weight_matrix(ob, names=None):
    """(names, W) like rig.weight_table, optionally restricted/ordered to `names`."""
    n0, W0 = _rig.weight_table(ob)
    if names is None:
        return n0, W0
    W = np.zeros((W0.shape[0], len(names)))
    for j, k in enumerate(names):
        if k in n0:
            W[:, j] = W0[:, n0.index(k)]
    return list(names), W


def set_weights(ob, names, W, limit=4, prune=0.01):
    """Replace every vertex group by the matrix W (n_vertices x len(names)): keep the `limit` largest
    influences per vertex, drop those under `prune`, normalise to 1."""
    W = np.array(W, dtype=np.float64)
    if limit and W.shape[1] > limit:
        idx = np.argsort(-W, axis=1)[:, limit:]
        np.put_along_axis(W, idx, 0.0, axis=1)
    W[W < prune] = 0.0
    s = W.sum(axis=1, keepdims=True)
    W = np.where(s > 0, W / np.maximum(s, 1e-12), 0.0)
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    for j, k in enumerate(names):
        col = W[:, j]
        nz = np.nonzero(col > 0)[0]
        if not len(nz):
            continue
        vg = ob.vertex_groups.new(name=k)
        # group vertices of equal weight are rare: add one by one but in bulk-friendly order
        for i in nz:
            vg.add([int(i)], float(col[i]), "REPLACE")
    return W


def transfer_weights(target, source, bones=None, limit=4):
    """Skin weights from the surface of `source` (a skinned mesh in the same rest pose) onto `target`: each
    target vertex takes the barycentric blend of the weights at the nearest point of the source surface.
    `bones`: only these groups are transferred (the rest renormalised). Returns (names, W)."""
    names, Ws = weight_matrix(source, bones)
    me = source.data
    Ms = np.array(source.matrix_world)
    co = np.array([Ms[:3, :3] @ np.array(v.co) + Ms[:3, 3] for v in me.vertices])
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(source.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.faces.ensure_lookup_table()
    tri = np.array([[v.index for v in f.verts] for f in bm.faces])
    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    Mt = target.matrix_world
    Wt = np.zeros((len(target.data.vertices), len(names)))
    for v in target.data.vertices:
        p = Mt @ v.co
        loc, _n, fi, _d = bvh.find_nearest(p)
        if fi is None:
            continue
        a, b, c = co[tri[fi]]
        bc = _barycentric(np.array(loc), a, b, c)
        Wt[v.index] = bc @ Ws[tri[fi]]
    return names, set_weights(target, names, Wt, limit=limit)


def _barycentric(p, a, b, c):
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
    d20, d21 = v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-18:
        return np.array([1.0, 0.0, 0.0])
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    u = 1.0 - v - w
    bc = np.clip(np.array([u, v, w]), 0, 1)
    return bc / max(bc.sum(), 1e-12)


def adjacency(ob):
    """Vertex adjacency as (indices, indptr) CSR arrays from the mesh edges."""
    me = ob.data
    e = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    n = len(me.vertices)
    a = np.concatenate([e[:, 0], e[:, 1]])
    b = np.concatenate([e[:, 1], e[:, 0]])
    order = np.argsort(a, kind="stable")
    a, b = a[order], b[order]
    indptr = np.zeros(n + 1, dtype=np.int64)
    np.add.at(indptr, a + 1, 1)
    return b, np.cumsum(indptr)


def smooth_weights(ob, iterations=4, strength=0.5, mask=None, limit=4, names=None, W=None):
    """Laplacian smoothing of the skin weights over the mesh (each pass moves a vertex `strength` of the way to
    the mean of its neighbours); `mask` (n,) 0..1 scales it per vertex (e.g. keep fingers rigid, smooth the
    wrist). Returns (names, W)."""
    if W is None:
        names, W = weight_matrix(ob, names)
    idx, ptr = adjacency(ob)
    deg = np.diff(ptr).astype(np.float64)
    m = np.ones(len(W)) if mask is None else np.asarray(mask, dtype=np.float64)
    for _ in range(iterations):
        sums = np.add.reduceat(W[idx], ptr[:-1], axis=0) if len(idx) else W * 0
        sums[deg == 0] = W[deg == 0]
        mean = sums / np.maximum(deg, 1)[:, None]
        W = W + (strength * m)[:, None] * (mean - W)
    return names, set_weights(ob, names, W, limit=limit)


# ------------------------------------------------------------------------------------------------ export

def export_character(ob, arm, name=None, path=None, influences=8, stub_materials=True):
    """Skinned GLB of one mesh on the FULL mannequin skeleton (every bone, deforming or not, so Unreal maps it
    onto SK_Mannequin), metres, +Y up, the armature object node removed so 'root' is the top joint as in the
    file Unreal wrote. The settings are the ones proven by the round trip (docs/unreal/CHARACTERS.md)."""
    name = name or ob.name
    path = path or os.path.join(paths.glb, name + ".glb")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rest_pose(arm)
    for b in arm.data.bones:
        b.use_deform = True
    ctx = _export._Stubs(ob, False) if stub_materials else _Null()
    with ctx:
        _scene.select_only(ob, arm)
        bpy.ops.export_scene.gltf(
            filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=False,
            export_materials="EXPORT", export_image_format="NONE",
            export_vertex_color="NONE", export_texcoords=True, export_normals=True, export_tangents=False,
            export_animations=False, export_skins=True, export_def_bones=False, export_leaf_bone=False,
            export_rest_position_armature=True, export_armature_object_remove=True,
            export_influence_nb=influences, export_all_influences=False, export_morph=False,
            export_cameras=False, export_lights=False, export_extras=False)
    return path


class _Null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def joint_table(path):
    """{joint: (parent, translation (3,), rotation quat xyzw (4,))} as written in a GLB."""
    js, _b = _rig.read_glb(path)
    nodes = js["nodes"]
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    out = {}
    for j in js["skins"][0]["joints"]:
        n = nodes[j]
        p = nodes[parent[j]].get("name") if j in parent else None
        q = np.array(n.get("rotation", [0, 0, 0, 1]), dtype=np.float64)
        out[n["name"]] = (p, np.array(n.get("translation", [0, 0, 0]), dtype=np.float64), q)
    return out


def round_trip_report(src, dst):
    """Joint by joint: same names, same parents, translation and rotation differences (metres, degrees)."""
    a, b = joint_table(src), joint_table(dst)
    rep = {"joints_src": len(a), "joints_dst": len(b), "missing": sorted(set(a) - set(b)),
           "extra": sorted(set(b) - set(a)), "parent_mismatch": [], "max_translation_m": 0.0, "max_rotation_deg": 0.0}
    for k in a:
        if k not in b:
            continue
        if a[k][0] != b[k][0]:
            rep["parent_mismatch"].append((k, a[k][0], b[k][0]))
        dt = float(np.linalg.norm(a[k][1] - b[k][1]))
        dr = _quat_angle_deg(a[k][2], b[k][2])
        if dt > rep["max_translation_m"]:
            rep["max_translation_m"], rep["worst_translation"] = dt, k
        if dr > rep["max_rotation_deg"]:
            rep["max_rotation_deg"], rep["worst_rotation"] = dr, k
    js_a, _ = _rig.read_glb(src)
    js_b, _ = _rig.read_glb(dst)
    rep["src_root_nodes"] = [js_a["nodes"][i].get("name") for i in js_a["scenes"][0]["nodes"]]
    rep["dst_root_nodes"] = [js_b["nodes"][i].get("name") for i in js_b["scenes"][0]["nodes"]]
    rep["ok"] = (not rep["missing"] and not rep["extra"] and not rep["parent_mismatch"]
                 and rep["max_translation_m"] < 1e-5 and rep["max_rotation_deg"] < 1e-3)
    return rep


def _quat_angle_deg(qa, qb):
    """Angle between two rotations given as xyzw quaternions (atan2 form: exact near zero)."""
    from mathutils import Quaternion
    A = Quaternion((qa[3], qa[0], qa[1], qa[2])).normalized()
    B = Quaternion((qb[3], qb[0], qb[1], qb[2])).normalized()
    d = A.rotation_difference(B)
    v = np.linalg.norm([d.x, d.y, d.z])
    return float(np.degrees(2 * np.arctan2(v, abs(d.w))))


def skinned_vertices(ob):
    """World positions of the evaluated (posed) mesh."""
    return _rig._evaluated_world_verts(ob)


def save_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
