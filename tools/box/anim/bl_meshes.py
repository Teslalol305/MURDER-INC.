"""Facts of the pack's Meshes/ folder and of the rig's sockets (bpy on the box; numbers only, never pack data).

    /opt/blpy/bin/python -I tools/box/anim/bl_meshes.py <pack FBX root> <rig.blend> <out.json>

For every FBX under Meshes/: its objects (mesh / armature), vertex and triangle counts, material slots, vertex groups
(bones that skin it), and per material and per bone the bounding box, in the pack's gun space as Unreal sees it
(cm; +Y forward to the muzzle, +X to the gun's left, +Z up: Unreal = Blender (x, -y, z) for these files). Separate
"islands" (connected pieces) are counted so baked-in parts can be told apart. For the rig .blend: the world
transform of every SOCKET_* empty and the world bounding box of every mesh object (constraints evaluated), in the
same space.
"""
import glob
import json
import os
import sys

import bpy
import bmesh
from mathutils import Vector

ROOT, BLEND, OUT = sys.argv[1:4]


def ue(v, s=100.0):
    """Blender world (metres after the FBX importer, or rig units) -> Unreal gun space cm."""
    return [round(v.x * s, 3), round(-v.y * s, 3), round(v.z * s, 3)]


def bbox(points):
    if not points:
        return None
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    return {"min": [round(x, 3) for x in lo], "max": [round(x, 3) for x in hi]}


def islands(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    seen = set()
    out = []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]
        comp = []
        seen.add(v.index)
        while stack:
            x = stack.pop()
            comp.append(x.index)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        out.append(comp)
    bm.free()
    return out


def mesh_facts(o, scale):
    me = o.data
    mw = o.matrix_world
    pts = [ue(mw @ v.co, scale) for v in me.vertices]
    f = {"name": o.name, "verts": len(me.vertices), "tris": sum(len(p.vertices) - 2 for p in me.polygons),
         "materials": [s.material.name if s.material else None for s in o.material_slots],
         "vgroups": [g.name for g in o.vertex_groups], "bbox": bbox(pts),
         "parent": o.parent.name if o.parent else None, "parent_bone": o.parent_bone or None,
         "uv_layers": [u.name for u in me.uv_layers]}
    # per material
    per_mat = {}
    for p in me.polygons:
        per_mat.setdefault(p.material_index, set()).update(p.vertices)
    f["by_material"] = {(f["materials"][i] if i < len(f["materials"]) else str(i)): bbox([pts[k] for k in vs])
                        for i, vs in per_mat.items()}
    # per dominant bone
    if o.vertex_groups:
        dom = {}
        for v in me.vertices:
            if v.groups:
                g = max(v.groups, key=lambda x: x.weight)
                dom.setdefault(o.vertex_groups[g.group].name, []).append(pts[v.index])
        f["by_bone"] = {k: dict(bbox(v), verts=len(v)) for k, v in dom.items()}
    isl = islands(me)
    f["islands"] = len(isl)
    big = sorted(isl, key=len, reverse=True)[:40]
    f["island_boxes"] = [dict(bbox([pts[k] for k in c]), verts=len(c)) for c in big]
    return f


res = {"fbx": {}, "rig": {}}
for path in sorted(glob.glob(os.path.join(ROOT, "Meshes", "*.fbx"))):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    e = {"objects": []}
    for o in bpy.data.objects:
        d = {"name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None,
             "scale": [round(x, 4) for x in o.matrix_world.to_scale()]}
        if o.type == "ARMATURE":
            d["bones"] = {b.name: {"parent": b.parent.name if b.parent else None,
                                   "head": ue(o.matrix_world @ b.head_local)} for b in o.data.bones}
        if o.type == "MESH":
            d.update(mesh_facts(o, 100.0))
        e["objects"].append(d)
    e["images"] = sorted({i.name for i in bpy.data.images})
    res["fbx"][os.path.basename(path)] = e
    print("FBX", os.path.basename(path), len(e["objects"]), flush=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.open_mainfile(filepath=BLEND, load_ui=False)
dg = bpy.context.evaluated_depsgraph_get()
# Rig units: scene scale 0.01, numbers are cm already -> scale 1
for o in bpy.data.objects:
    ob = o.evaluated_get(dg)
    mw = ob.matrix_world
    if o.type == "EMPTY":
        res["rig"][o.name] = {"type": "EMPTY", "loc": ue(mw.translation, 1.0),
                              "x_axis": ue(mw.to_3x3() @ Vector((1, 0, 0)), 1.0),
                              "y_axis": ue(mw.to_3x3() @ Vector((0, 1, 0)), 1.0),
                              "z_axis": ue(mw.to_3x3() @ Vector((0, 0, 1)), 1.0),
                              "parent": o.parent.name if o.parent else None}
    elif o.type == "MESH" and not o.name.startswith("CS_"):
        me = ob.to_mesh()
        pts = [ue(mw @ v.co, 1.0) for v in me.vertices]
        res["rig"][o.name] = {"type": "MESH", "bbox": bbox(pts), "loc": ue(mw.translation, 1.0), "verts": len(pts),
                              "hidden": o.hide_get() or o.hide_render,
                              "materials": [s.material.name if s.material else None for s in o.material_slots]}
        ob.to_mesh_clear()
    elif o.type == "ARMATURE":
        res["rig"][o.name] = {"type": "ARMATURE", "bones": {pb.name: ue(mw @ pb.head, 1.0) for pb in ob.pose.bones
                                                             if not pb.name.startswith("CB_")}}
json.dump(res, open(OUT, "w"), indent=1)
print("BL-MESHES-DONE", len(res["fbx"]), len(res["rig"]))
