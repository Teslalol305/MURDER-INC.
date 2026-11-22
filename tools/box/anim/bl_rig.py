"""Facts of the pack's Blender rig (.blend): objects, armatures, bone hierarchy, constraints, actions, collections.

    /opt/blpy/bin/python -I tools/box/anim/bl_rig.py <rig.blend> <out.json>
"""
import json
import sys

import bpy

SRC, OUT = sys.argv[1:3]
bpy.ops.wm.open_mainfile(filepath=SRC, load_ui=False)
res = {"version": bpy.data.version, "scenes": [], "objects": [], "actions": [], "collections": [], "texts": []}
for s in bpy.data.scenes:
    res["scenes"].append({"name": s.name, "fps": s.render.fps / s.render.fps_base, "unit": s.unit_settings.system,
                          "scale": s.unit_settings.scale_length, "frames": [s.frame_start, s.frame_end],
                          "camera": s.camera.name if s.camera else None})
for o in bpy.data.objects:
    e = {"name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None,
         "parent_bone": o.parent_bone or None, "parent_type": o.parent_type,
         "loc": [round(v, 4) for v in o.location], "scale": [round(v, 4) for v in o.scale],
         "constraints": [{"type": c.type, "name": c.name,
                          "target": getattr(c, "target", None) and c.target.name,
                          "subtarget": getattr(c, "subtarget", None)} for c in o.constraints],
         "collections": [c.name for c in o.users_collection],
         "action": o.animation_data.action.name if o.animation_data and o.animation_data.action else None}
    if o.type == "ARMATURE":
        e["bones"] = {b.name: {"parent": b.parent.name if b.parent else None,
                               "head": [round(v, 4) for v in (o.matrix_world @ b.head_local)],
                               "tail": [round(v, 4) for v in (o.matrix_world @ b.tail_local)],
                               "deform": b.use_deform,
                               "collections": [c.name for c in b.collections]} for b in o.data.bones}
        e["pose_constraints"] = {pb.name: [{"type": c.type, "name": c.name,
                                            "target": getattr(c, "target", None) and c.target.name,
                                            "subtarget": getattr(c, "subtarget", None),
                                            "influence": round(c.influence, 3), "mute": c.mute}
                                           for c in pb.constraints] for pb in o.pose.bones if pb.constraints}
        e["bone_collections"] = [c.name for c in o.data.collections_all]
    if o.type == "MESH":
        e["verts"] = len(o.data.vertices)
        e["vgroups"] = len(o.vertex_groups)
        e["modifiers"] = [(m.type, getattr(m, "object", None) and m.object.name) for m in o.modifiers]
    res["objects"].append(e)
for a in bpy.data.actions:
    res["actions"].append({"name": a.name, "range": list(a.frame_range), "users": a.users,
                           "slots": [s.identifier for s in getattr(a, "slots", [])]})
for c in bpy.data.collections:
    res["collections"].append({"name": c.name, "objects": len(c.objects), "children": [x.name for x in c.children]})
for t in bpy.data.texts:
    res["texts"].append({"name": t.name, "lines": len(t.lines), "head": t.as_string()[:400]})
json.dump(res, open(OUT, "w"), indent=1)
print("BL-RIG-DONE", len(res["objects"]), len(res["actions"]))
