"""Inspect the Tactical FPS Animation Pack (Infima Games) with bpy on the box.

    /opt/blpy/bin/python -I tools/box/anim/bl_inspect.py <pack FBX root> <mannequin glb> <out.json> [clip filter]

Writes facts only (names, numbers), never pack data: the skeleton of the clips compared joint by joint with the
mannequin (names, parents, rest head positions in metres), every clip's frame range, frame rate and length, the FBX
global settings (unit scale, axes, time mode), the weapon rig's bones and the root/IK bones' motion.
"""
import glob
import json
import math
import os
import sys

import bpy
from io_scene_fbx import parse_fbx

ROOT, MANNY, OUT = sys.argv[1:4]
FILTER = sys.argv[4] if len(sys.argv) > 4 else ""

TIME_MODES = {0: "default", 1: 120, 2: 100, 3: 60, 4: 50, 5: 48, 6: 30, 7: "30 drop", 8: "NTSC drop", 9: "NTSC full",
              10: "PAL", 11: 24, 12: 1000, 13: "film full", 14: "custom", 15: 96, 16: 72, 17: 59.94, 18: 119.88}


def fbx_globals(path):
    root, ver = parse_fbx.parse(path)
    out = {"fbx_version": ver}
    for e in root.elems:
        if e.id == b"GlobalSettings":
            for p70 in e.elems:
                if p70.id != b"Properties70":
                    continue
                for p in p70.elems:
                    name = p.props[0].decode()
                    if name in ("UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign",
                                "UnitScaleFactor", "OriginalUnitScaleFactor", "TimeMode", "CustomFrameRate",
                                "TimeSpanStart", "TimeSpanStop"):
                        v = p.props[4]
                        out[name] = v if not isinstance(v, bytes) else v.decode()
        if e.id == b"FBXHeaderExtension":
            for s in e.elems:
                if s.id == b"Creator":
                    out["creator"] = s.props[0].decode(errors="replace")
    tm = out.get("TimeMode")
    out["fps"] = out.get("CustomFrameRate") if tm == 14 else TIME_MODES.get(tm, tm)
    if "TimeSpanStop" in out:
        out["span_s"] = (out["TimeSpanStop"] - out.get("TimeSpanStart", 0)) / 46186158000.0
    return out


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def armature_facts(arm):
    bones = {}
    for b in arm.data.bones:
        h = arm.matrix_world @ b.head_local
        bones[b.name] = {"parent": b.parent.name if b.parent else None,
                         "head": [round(h.x, 5), round(h.y, 5), round(h.z, 5)]}
    return bones


def import_fbx(path):
    clear()
    bpy.ops.import_scene.fbx(filepath=path, use_anim=True, automatic_bone_orientation=False,
                             ignore_leaf_bones=False, use_custom_props=True)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o.name for o in bpy.data.objects if o.type == "MESH"]
    others = [(o.name, o.type) for o in bpy.data.objects if o.type not in ("ARMATURE", "MESH")]
    return arms, meshes, others


def action_facts(arm):
    ad = arm.animation_data
    act = ad.action if ad else None
    if not act:
        return None
    f0, f1 = act.frame_range
    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    moving = {}
    scn = bpy.context.scene
    # which bones move (any channel range > tiny), and the root / ik bones' path
    samples = {}
    track = [n for n in ("root", "ik_hand_root", "ik_hand_gun", "ik_hand_l", "ik_hand_r", "ik_foot_root",
                         "hand_r", "hand_l", "head", "pelvis", "weapon", "camera") if n in arm.pose.bones]
    for fr in range(int(f0), int(f1) + 1, max(1, int((f1 - f0) // 6) or 1)):
        scn.frame_set(fr)
        samples[fr] = {n: [round(v, 4) for v in (arm.matrix_world @ arm.pose.bones[n].head)] for n in track}
    return {"name": act.name, "frames": [f0, f1], "scene_fps": fps, "length_s": round((f1 - f0) / fps, 4),
            "track": samples}


def manny():
    clear()
    bpy.ops.import_scene.gltf(filepath=MANNY, bone_heuristic="BLENDER", guess_original_bind_pose=False)
    arm = [o for o in bpy.data.objects if o.type == "ARMATURE"][0]
    return armature_facts(arm)


def main():
    res = {"mannequin": None, "clips": {}, "skeletons": {}}
    m = manny()
    res["mannequin_bone_count"] = len(m)
    files = sorted(glob.glob(os.path.join(ROOT, "**", "*.fbx"), recursive=True))
    files = [f for f in files if FILTER in f]
    first_char = None
    for f in files:
        rel = os.path.relpath(f, ROOT)
        try:
            g = fbx_globals(f)
            arms, meshes, others = import_fbx(f)
        except Exception as ex:  # noqa
            res["clips"][rel] = {"error": str(ex)}
            continue
        info = {"globals": g, "meshes": meshes, "others": others, "armatures": []}
        for a in arms:
            facts = armature_facts(a)
            key = ",".join(sorted(facts))
            sk = res["skeletons"].setdefault(str(hash(key) & 0xffffffff), {"bones": len(facts), "files": 0,
                                                                         "example": rel, "names": sorted(facts)})
            sk["files"] += 1
            ai = {"name": a.name, "bones": len(facts), "scale": [round(v, 4) for v in a.scale],
                  "rot": [round(math.degrees(v), 2) for v in a.rotation_euler], "action": action_facts(a)}
            if "Character" in rel and set(facts) & set(m) and first_char is None:
                first_char = rel
                cmp = {"missing_in_clip": sorted(set(m) - set(facts)), "extra_in_clip": sorted(set(facts) - set(m)),
                       "parent_diff": {}, "head_diff_mm": {}}
                for n in set(m) & set(facts):
                    if m[n]["parent"] != facts[n]["parent"]:
                        cmp["parent_diff"][n] = [m[n]["parent"], facts[n]["parent"]]
                    # glTF import faces the mannequin to Blender -Y; FBX import keeps its axes: compare both mirror
                    d = [abs(facts[n]["head"][i] - m[n]["head"][i]) for i in range(3)]
                    cmp["head_diff_mm"][n] = round(1000 * math.sqrt(sum(x * x for x in d)), 3)
                cmp["max_head_diff_mm"] = max(cmp["head_diff_mm"].values()) if cmp["head_diff_mm"] else None
                cmp["clip"] = rel
                cmp["clip_heads"] = {n: facts[n]["head"] for n in facts}
                cmp["manny_heads"] = {n: m[n]["head"] for n in m}
                cmp["clip_parents"] = {n: facts[n]["parent"] for n in facts}
                res["compare"] = cmp
            if "Weapon" in rel or "Meshes" in rel:
                ai["bone_tree"] = {n: facts[n]["parent"] for n in facts}
                ai["heads"] = {n: facts[n]["head"] for n in facts}
            info["armatures"].append(ai)
        res["clips"][rel] = info
        print("ok", rel, flush=True)
    for v in res["skeletons"].values():
        if v["bones"] > 120:
            v["names"] = v["names"][:0]
    json.dump(res, open(OUT, "w"), indent=1)
    print("BL-INSPECT-DONE", len(files))


main()
