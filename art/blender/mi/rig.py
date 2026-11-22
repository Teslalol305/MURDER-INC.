"""Skinned assets: rigid-part rigs (guns, doors, anything whose bones are its moving parts), skinned GLB export
through the pipeline's material stubs, and proof by re-import.

    from mi import rig
    arm = rig.armature("SKEL_Chopper", [
        rig.Bone("body", (0, 0, 0)),                                  # root
        rig.Bone("bolt", (0.18, 0, 0.0145), "body"),
        rig.Bone("trigger", (0.108, 0, -0.038), "body"),
        rig.Bone("Muzzle", (0.4975, 0, 0), "body", deform=False),     # a socket: a bone without vertices
    ], col)
    rig.tag(part, "bolt")                  # before joining: every vertex of the part -> bone 'bolt', weight 1.0
    gun = geo.join(parts, "SK_Chopper")    # vertex groups merge by name
    rig.bind(gun, arm)                     # parent + Armature modifier (optionally rig.weights(gun, {...}))
    err, warn = rig.validate(gun, arm, expect_size=(0.502, 0.065, 0.292), rigid=True)
    path = rig.export_skinned(gun, arm)    # art/out/glb/SK_Chopper.glb, slots by name, no textures
    rep = rig.inspect_glb(path)            # joints, their rest rotations and translations (glTF space)
    rep = rig.verify(path, poses)          # fresh Blender process: import, pose, measure every vertex

Axes. A bone is created with its tail along +Y and roll 0, so its rest matrix is the identity rotation: the bone's
local X, Y, Z are the asset's X, Y, Z (for a gun: X along the bore, Z up, Y to the left). In the exported glTF
(+Y up) Blender's exporter puts the Z-up -> Y-up turn on the root joint (rotation -90 deg about X) and every
child joint has the identity local rotation, so every joint's axes are still the asset's axes and a translation
along a joint's local X is travel along the asset's X axis in Blender, glTF and Unreal alike.
inspect_glb() reports this per joint ('axes_are_asset_axes', at rest and at bind).

Poses for verify(): a list of {"name": ..., "bones": {bone: {"translate": (x, y, z)} or
{"rotate": (axis (x, y, z), degrees), "pivot": (x, y, z) optional, default the bone head}}}, all in the asset's
space (Blender, Z up). Each vertex weighted to a posed bone must move exactly as that rigid transform predicts;
every other vertex must stay put. Bones are posed in armature space on top of a parent at rest.
"""
import json
import math
import os
import struct
import subprocess
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import export as _export
from . import geo as _geo
from . import paths
from . import scene as _scene

SK_RE = __import__("re").compile(r"^SK_[A-Z][A-Za-z0-9]*(_[A-Za-z0-9]+)*$")
BONE_LEN = 0.02


class Bone:
    """head: pivot in asset space; parent: bone name or None; deform=False for sockets (no vertices).
    length: display length of the bone (its tail is head + (0, length, 0), so the rest orientation is identity)."""

    def __init__(self, name, head, parent=None, deform=True, length=None):
        self.name, self.head, self.parent, self.deform = name, tuple(float(v) for v in head), parent, deform
        self.length = length or (BONE_LEN if deform else BONE_LEN * 0.5)


def armature(name, bones, col=None):
    """Armature object at the origin from a list of Bone (parents listed before children)."""
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    (col or bpy.context.scene.collection).objects.link(ob)
    _scene.select_only(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.edit_bones
    for b in bones:
        e = eb.new(b.name)
        e.head = Vector(b.head)
        e.tail = Vector(b.head) + Vector((0.0, b.length, 0.0))
        e.roll = 0.0
        e.use_deform = b.deform
        if b.parent:
            e.parent = eb[b.parent]
            e.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    ob["mi_bones"] = json.dumps([[b.name, b.head, b.parent, b.deform] for b in bones])
    return ob


def tag(ob, bone, weight=1.0):
    """Put every vertex of a (not yet joined) part into vertex group `bone` with `weight`."""
    vg = ob.vertex_groups.get(bone) or ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(ob.data.vertices))), float(weight), "REPLACE")
    return ob


def weights(ob, table):
    """Explicit weights: table = {bone: per-vertex array (0..1)}; rows are normalised to sum 1 where non-zero."""
    n = len(ob.data.vertices)
    names = list(table)
    W = np.stack([np.asarray(table[k], dtype=np.float64).reshape(n) for k in names], axis=1)
    s = W.sum(axis=1, keepdims=True)
    W = np.where(s > 0, W / np.maximum(s, 1e-12), 0.0)
    for j, k in enumerate(names):
        vg = ob.vertex_groups.get(k) or ob.vertex_groups.new(name=k)
        idx = np.nonzero(W[:, j] > 0)[0]
        for i in idx:
            vg.add([int(i)], float(W[i, j]), "REPLACE")
    return ob


def bind(ob, arm):
    """Parent the mesh to the armature (no offset) and add the Armature modifier (vertex groups)."""
    ob.parent = arm
    ob.matrix_parent_inverse = Matrix.Identity(4)
    md = ob.modifiers.get("Armature") or ob.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    md.use_vertex_groups = True
    md.use_bone_envelopes = False
    return ob


def weight_table(ob):
    """(names, W) with W (n_vertices, n_groups) float64."""
    n = len(ob.data.vertices)
    names = [g.name for g in ob.vertex_groups]
    W = np.zeros((n, len(names)))
    for v in ob.data.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    return names, W


def validate(ob, arm, expect_size=None, rigid=True, tol=0.05):
    """export.validate (without the SM_ name rule) plus: SK_ name, every vertex group is a deform bone, every
    vertex weighted (rigid: to exactly one bone with weight 1.0; otherwise weights summing to 1), sockets carry
    no vertices, bones have the asset's axes at rest, the mesh sits at the armature origin."""
    err, warn = _export.validate(ob, expect_size, tol, strict_names=False)
    own = "M_" + ob.name[3:]                         # SK_Chopper's unique set 'Chopper' is used through M_Chopper
    err = [e for e in err if not e.startswith("slot '%s' " % own)]
    if not SK_RE.match(ob.name):
        err.append("name '%s' does not follow SK_<Name>" % ob.name)
    bones = {b.name: b for b in arm.data.bones}
    names, W = weight_table(ob)
    for g in names:
        if g not in bones:
            err.append("vertex group '%s' has no bone" % g)
        elif not bones[g].use_deform:
            if W[:, names.index(g)].max() > 0:
                err.append("socket bone '%s' carries vertices" % g)
    nz = (W > 1e-6).sum(axis=1)
    s = W.sum(axis=1)
    if (nz == 0).any():
        err.append("%d vertices have no weight" % int((nz == 0).sum()))
    if rigid:
        if (nz > 1).any():
            err.append("%d vertices are weighted to more than one bone (rigid rig)" % int((nz > 1).sum()))
        if (np.abs(W[W > 1e-6] - 1.0) > 1e-4).any():
            err.append("rigid weights must be 1.0")
    elif (np.abs(s[nz > 0] - 1.0) > 1e-3).any():
        err.append("weights do not sum to 1 on %d vertices" % int((np.abs(s[nz > 0] - 1.0) > 1e-3).sum()))
    for b in arm.data.bones:
        R = b.matrix_local.to_3x3()
        if (np.abs(np.array(R) - np.eye(3)) > 1e-5).any():
            err.append("bone '%s' rest orientation is not the asset's axes" % b.name)
    if (np.abs(np.array(arm.matrix_world) - np.eye(4)) > 1e-6).any() or (np.abs(np.array(ob.matrix_world) - np.eye(4)) > 1e-6).any():
        err.append("armature or mesh is not at the origin with identity transform")
    if ob.parent is not arm:
        err.append("mesh is not parented to the armature")
    used = set(names[j] for j in range(len(names)) if W[:, j].max() > 0)
    for b in arm.data.bones:
        if b.use_deform and b.name not in used:
            warn.append("deform bone '%s' has no vertices (attach bone?)" % b.name)
    return err, warn


def export_skinned(ob, arm, name=None, path=None, embed_textures=False):
    """Skinned binary glTF of the mesh and its armature (all bones, sockets included), +Y up, materials as
    slot-named stubs without textures (export._Stubs, like export_glb). The mesh must sit at the origin."""
    name = name or ob.name
    path = path or os.path.join(paths.glb, name + ".glb")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _geo.ensure_wear(ob)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    with _export._Stubs(ob, embed_textures):
        _scene.select_only(ob, arm)
        bpy.ops.export_scene.gltf(
            filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=False,
            export_materials="EXPORT", export_image_format="AUTO" if embed_textures else "NONE",
            export_vertex_color="ACTIVE", export_all_vertex_colors=False,
            export_active_vertex_color_when_no_material=True, export_texcoords=True, export_normals=True,
            export_tangents=False, export_animations=False, export_skins=True, export_def_bones=False,
            export_leaf_bone=False, export_rest_position_armature=True, export_influence_nb=4,
            export_morph=False, export_cameras=False, export_lights=False, export_extras=False)
    return path


def read_glb(path):
    """(json dict, binary chunk bytes) of a .glb file."""
    with open(path, "rb") as f:
        data = f.read()
    magic, _ver, _length = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67, "not a GLB"
    off, js, binc = 12, None, b""
    while off < len(data):
        ln, typ = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + ln]
        if typ == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif typ == 0x004E4942:
            binc = chunk
        off += 8 + ln
    return js, binc


def _accessor(js, binc, i):
    a = js["accessors"][i]
    bv = js["bufferViews"][a["bufferView"]]
    comp = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8}[a["componentType"]]
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    arr = np.frombuffer(binc, dtype=comp, count=a["count"] * ncomp, offset=start)
    return arr.reshape(a["count"], ncomp)


def inspect_glb(path):
    """What the file says about its skeleton: per joint the parent, local rest translation and rotation as
    written (glTF, +Y up: Blender's exporter puts the Z-up -> Y-up turn on the root joint), the rest position in
    asset space and whether the joint's axes ARE the asset's axes (local X = asset X ...) at rest and at bind;
    meshes, triangle and vertex counts; materials."""
    js, binc = read_glb(path)
    nodes = js.get("nodes", [])
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    rep = {"file": os.path.relpath(path, paths.art), "joints": {}, "meshes": [], "materials": [m.get("name") for m in js.get("materials", [])]}
    G = {}                                                    # global rest matrices (glTF space)

    def local(n):
        t = n.get("translation", [0, 0, 0])
        x, y, z, w = n.get("rotation", [0, 0, 0, 1])
        from mathutils import Quaternion
        M = np.eye(4)
        M[:3, :3] = np.array(Quaternion((w, x, y, z)).to_matrix())
        M[:3, 3] = t
        return M

    def glob(i):
        if i not in G:
            G[i] = (glob(parent[i]) if i in parent else np.eye(4)) @ local(nodes[i])
        return G[i]
    # glTF (+Y up) -> asset space (Blender, Z up): (x, y, z) -> (x, -z, y)
    C = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float64)
    for sk in js.get("skins", []):
        ibm = _accessor(js, binc, sk["inverseBindMatrices"]).reshape(-1, 4, 4) if "inverseBindMatrices" in sk else None
        for k, j in enumerate(sk["joints"]):
            n = nodes[j]
            Gj = glob(j)
            A = C @ Gj[:3, :3]                                # joint axes in asset space
            rec = {"parent": nodes[parent[j]]["name"] if j in parent and parent[j] in sk["joints"] else None,
                   "local_translation_gltf": [round(v, 5) for v in n.get("translation", [0, 0, 0])],
                   "local_rotation_gltf": [round(v, 6) for v in n.get("rotation", [0, 0, 0, 1])],
                   "rest_position_asset": [round(float(v), 5) for v in C @ Gj[:3, 3]],
                   "axes_are_asset_axes": bool(np.allclose(A, np.eye(3), atol=1e-5))}
            if ibm is not None:
                Bm = np.linalg.inv(ibm[k].T)                  # bind matrix (column-major in the file)
                rec["bind_axes_are_asset_axes"] = bool(np.allclose(C @ Bm[:3, :3], np.eye(3), atol=1e-5))
                rec["bind_position_asset"] = [round(float(v), 5) for v in C @ Bm[:3, 3]]
            rep["joints"][n["name"]] = rec
    rep["all_axes_are_asset_axes"] = all(j["axes_are_asset_axes"] and j.get("bind_axes_are_asset_axes", True)
                                         for j in rep["joints"].values())
    for m in js.get("meshes", []):
        tris = verts = 0
        for p in m["primitives"]:
            verts += js["accessors"][p["attributes"]["POSITION"]]["count"]
            tris += js["accessors"][p["indices"]]["count"] // 3 if "indices" in p else 0
        rep["meshes"].append({"name": m.get("name"), "triangles": tris, "vertices": verts,
                              "attributes": sorted(m["primitives"][0]["attributes"].keys())})
    return rep


# ------------------------------------------------------------------------------------- re-import and pose (proof)

def _pose_matrix(spec, head):
    if "translate" in spec:
        return Matrix.Translation(Vector(spec["translate"]))
    axis, deg = spec["rotate"]
    p = Vector(spec.get("pivot", head))
    return Matrix.Translation(p) @ Matrix.Rotation(math.radians(deg), 4, Vector(axis).normalized()) @ Matrix.Translation(-p)


def pose_imported(arm, bones):
    """Pose bones of an (imported) armature by asset-space rigid transforms {bone: spec} (see module doc).
    Works whatever rest orientation the importer chose: the pose is applied in world space."""
    W = arm.matrix_world
    Wi = W.inverted()
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    order = sorted(arm.pose.bones, key=lambda p: len(p.parent_recursive))
    for pb in order:
        if pb.name not in bones:
            continue
        spec = bones[pb.name]
        head_world = W @ pb.bone.head_local
        T = _pose_matrix(spec, tuple(head_world))
        pb.matrix = Wi @ T @ W @ pb.bone.matrix_local
        bpy.context.view_layer.update()


def import_glb(path, col_name=None):
    """Import a GLB into a new collection of the current scene; returns (armature or None, [meshes], collection)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path, import_shading="NORMALS", guess_original_bind_pose=False,
                              bone_heuristic="BLENDER", disable_bone_shape=True, import_scene_as_collection=False)
    new = [o for o in bpy.data.objects if o not in before]
    col = _scene.collection(col_name or ("Import_" + os.path.splitext(os.path.basename(path))[0]))
    for o in new:
        _scene.move_to(o, col)
    arm = next((o for o in new if o.type == "ARMATURE"), None)
    meshes = [o for o in new if o.type == "MESH"]
    return arm, meshes, col


def _evaluated_world_verts(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    co = co.reshape(-1, 3).astype(np.float64)
    M = np.array(ob.matrix_world)
    return co @ M[:3, :3].T + M[:3, 3]


def check_poses(path, poses):
    """In the current scene: import the file, then for each pose move the bones and measure every vertex
    against the rigid prediction. Returns a report dict (max errors in metres, moved vertex counts)."""
    arm, meshes, col = import_glb(path)
    rep = {"file": os.path.relpath(path, paths.art), "armature": arm.name if arm else None,
           "bones": [b.name for b in arm.data.bones] if arm else [], "poses": []}
    if arm is None:
        rep["error"] = "no armature in the file"
        rep["ok"] = False
        return rep, None, meshes, col
    ob = max(meshes, key=lambda o: (len(o.vertex_groups) > 0, len(o.data.vertices)))
    groups = {g.index: g.name for g in ob.vertex_groups}
    owner = np.full(len(ob.data.vertices), -1)
    wmax = np.zeros(len(ob.data.vertices))
    for v in ob.data.vertices:
        for g in v.groups:
            if g.weight > wmax[v.index]:
                wmax[v.index], owner[v.index] = g.weight, g.group
    names = np.array([groups.get(i, "") for i in owner])
    rest = _evaluated_world_verts(ob)
    rep["vertices"] = int(len(rest))
    rep["vertices_per_bone"] = {k: int((names == k).sum()) for k in sorted(set(names.tolist()))}
    for pose in poses:
        pose_imported(arm, pose["bones"])
        now = _evaluated_world_verts(ob)
        expect = rest.copy()
        for bname, spec in pose["bones"].items():
            pb = arm.pose.bones.get(bname)
            if pb is None:
                continue
            T = np.array(_pose_matrix(spec, tuple(arm.matrix_world @ pb.bone.head_local)))
            sel = names == bname
            # children of a posed bone follow it
            kids = [c.name for c in pb.children_recursive]
            sel |= np.isin(names, kids) & np.array([k not in pose["bones"] for k in names])
            expect[sel] = rest[sel] @ T[:3, :3].T + T[:3, 3]
        d = np.linalg.norm(now - expect, axis=1)
        moved = np.linalg.norm(now - rest, axis=1) > 1e-6
        rep["poses"].append({"name": pose["name"], "max_error_m": float(d.max()), "moved_vertices": int(moved.sum()),
                             "moved_by_bone": {k: int((moved & (names == k)).sum()) for k in pose["bones"]},
                             "ok": bool(d.max() < 1e-5)})
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    rep["ok"] = all(p["ok"] for p in rep["poses"])
    return rep, arm, meshes, col


def verify(path, poses, keep_report=True):
    """Fresh Blender process (python with the bpy module, or this Blender binary): factory scene, import the
    GLB, pose, measure; plus inspect_glb. Writes <file>.verify.json next to the GLB and returns the report."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pj = path + ".poses.json"
    with open(pj, "w") as f:
        json.dump(poses, f)
    code = ("import sys, json; sys.path.insert(0, %r)\n"
            "import bpy\n"
            "bpy.ops.wm.read_factory_settings(use_empty=True)\n"
            "from mi import rig\n"
            "rep = rig.check_poses(%r, json.load(open(%r)))[0]\n"
            "rep['glb'] = rig.inspect_glb(%r)\n"
            "json.dump(rep, open(%r, 'w'), indent=1)\n") % (here, path, pj, path, path + ".verify.json")
    if "python" in os.path.basename(sys.executable).lower() or not bpy.app.binary_path:
        cmd = [sys.executable, "-c", code]                    # the bpy module
    else:
        cmd = [bpy.app.binary_path, "-b", "--factory-startup", "--python-expr", code]
    r = subprocess.run(cmd, capture_output=True, text=True)
    os.remove(pj)
    out = path + ".verify.json"
    if r.returncode != 0 or not os.path.exists(out):
        raise RuntimeError("verify failed:\n" + r.stdout[-2000:] + r.stderr[-3000:])
    with open(out) as f:
        rep = json.load(f)
    if not keep_report:
        os.remove(out)
    return rep


def manifest_entry(ob, arm, family, glb, notes="", slots=None, sockets=None, poses_report=None):
    """Manifest record of a skinned asset: the static record plus the skeleton (bones, parents, heads in Blender
    metres and Unreal centimetres), sockets and the re-import proof."""
    e = _export.asset_entry(ob, family, "none", None, notes, "asset origin (see notes)", glb, None, slots)
    u = lambda v: [round(float(v[0]) * 100, 3), round(-float(v[1]) * 100, 3), round(float(v[2]) * 100, 3)]
    e["kind"] = "skeletal"
    e["skeleton"] = {b.name: {"parent": b.parent.name if b.parent else None, "head_m": [round(float(c), 5) for c in b.head_local],
                              "head_unreal_cm": u(b.head_local), "deform": b.use_deform,
                              "rest_orientation": "identity: local X = asset X (bore), Z = up, Y = left"}
                     for b in arm.data.bones}
    if sockets:
        e["sockets"] = sockets
    if poses_report:
        e["proof"] = {"poses": poses_report.get("poses"), "ok": poses_report.get("ok")}
    return e
