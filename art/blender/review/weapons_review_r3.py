"""Independent review renders and measurements of the exported player guns (critique round 3).

Reuses the round-1 review harness (weapons_review.py: fresh scene, studio HDRI, texture wiring from the sets on disk,
studio and first-person cameras) without changing it. Texture sets are found from the material names in the GLBs
(M_<Set> -> art/out/textures/<Set>/). Adds fixed-point checks: rest position of every bone and socket against the
brief, overall size, sight line, and the travel of each moving part measured by posing its bone.

    python art/blender/review/weapons_review_r3.py [--only Chopper|Nine] [--views left,...] [--samples 32]
    python art/blender/review/weapons_review_r3.py --measure-only

Outputs: art/blender/review/sheets/r3/weapons_<Gun>_<view>.jpg (1280 x 720), measure.json beside them.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import weapons_review as wr  # noqa: E402

wr.OUT = os.path.join(HERE, "sheets", "r3")
for g in wr.GUNS.values():
    g["sets"] = {}

_load = wr.load_gun


def load_gun(name):
    objs, meshes = _load(name)
    done = set()
    for o in meshes:
        for slot in o.material_slots:
            m = slot.material
            key = m.name.split(".")[0]
            set_name = key[2:] if key.startswith("M_") else key
            if m.name not in done and os.path.exists(os.path.join(wr.TEX, set_name, "set.json")):
                wr.texture_material(m, set_name)
                done.add(m.name)
    return objs, meshes


wr.load_gun = load_gun

TRAVEL = {   # bone, local motion to apply (in armature space), what the brief says
    "Chopper": [("bolt", ("loc", (-0.092, 0, 0)), "bolt carrier 92 mm back"),
                ("trigger", ("rot", 0.34), "trigger 19.5 deg")],
    "Nine": [("slide", ("loc", (-0.044, 0, 0)), "slide 44 mm back"),
             ("barrel", ("rot", 0.04), "barrel 2.3 deg about lug X 0.070 Z -0.008"),
             ("trigger", ("rot", 0.30), "trigger 17 deg")],
}


def part_extents(gun):
    mw = gun.matrix_world
    co = np.array([tuple(mw @ v.co) for v in gun.data.vertices])
    vg = {g.index: g.name for g in gun.vertex_groups}
    dom = np.full(len(co), -1)
    best = np.zeros(len(co))
    for v in gun.data.vertices:
        for g in v.groups:
            if g.weight > best[v.index]:
                best[v.index], dom[v.index] = g.weight, g.group
    ext = {}
    for gi, gname in vg.items():
        sel = co[dom == gi]
        if len(sel):
            ext[gname] = {"n": int(len(sel)), "lo": sel.min(0).round(4).tolist(), "hi": sel.max(0).round(4).tolist()}
    return ext, co, dom, vg


def travel(name, objs, gun):
    arm = next(o for o in objs if o.type == "ARMATURE")
    out = {}
    dg = bpy.context.evaluated_depsgraph_get()

    def verts():
        e = gun.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = e.to_mesh()
        c = np.array([tuple(e.matrix_world @ v.co) for v in me.vertices])
        e.to_mesh_clear()
        return c

    rest = verts()
    for bone, (kind, val), note in TRAVEL[name]:
        pb = arm.pose.bones.get(bone)
        if pb is None:
            out[bone] = "missing bone"
            continue
        b = arm.data.bones[bone]
        if kind == "loc":
            # move by val in armature space: convert to bone local
            local = b.matrix_local.to_3x3().inverted() @ Vector(val)
            pb.location = local
        else:
            # rotate about the bone's local axis that is armature +Y (gun left) -> pitch in the X-Z plane
            ax = b.matrix_local.to_3x3().inverted() @ Vector((0, 1, 0))
            pb.rotation_mode = "AXIS_ANGLE"
            pb.rotation_axis_angle = (-val, *ax)
        bpy.context.view_layer.update()
        moved = verts()
        d = moved - rest
        mag = np.linalg.norm(d, axis=1)
        sel = mag > 1e-6
        res = {"note": note, "moved_verts": int(sel.sum()), "head": [round(x, 4) for x in (arm.matrix_world @ b.head_local)]}
        if sel.any():
            res["mean_delta_mm"] = (d[sel].mean(0) * 1000).round(2).tolist()
            res["max_move_mm"] = round(float(mag.max() * 1000), 2)
        out[bone] = res
        pb.location = (0, 0, 0)
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_axis_angle = (0, 0, 1, 0)
        bpy.context.view_layer.update()
    return out


_measure = wr.measure


def measure(name, objs, meshes):
    res = _measure(name, objs, meshes)
    gun = next(o for o in meshes if o.name.startswith("SK_"))
    res["part_extents"], *_ = part_extents(gun)
    res["travel"] = travel(name, objs, gun)
    for o in meshes:
        if o is gun:
            continue
        c = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
        res.setdefault("mag_extents", {})[o.name] = [c.min(0).round(4).tolist(), c.max(0).round(4).tolist()]
    res["empties"] = {o.name: [round(x, 4) for x in o.matrix_world.translation] for o in objs if o.type == "EMPTY"}
    return res


wr.measure = measure

if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--samples" not in argv:
        argv += ["--samples", "32"]
    sys.argv = [sys.argv[0]] + argv
    wr.main()
