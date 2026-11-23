"""Independent art-direction review, round 4, of the main character (Rule): first-person views with both guns (hip
and aimed, day rig and the open shade under the El), close-ups of each hand (back, palm, fist on the grip), the
forearm tattoos and the face against the private photo, the full body in two poses; plus a no-render contact
measurement of the hands on the guns.

Reads only exports: SK_RuleArms.glb with the build's own preview stand-in for M_RuleArms_Skin / SP_RuleSkin
(assets/rule.textured_materials), SM_Character_RuleBracelet.glb on its socket, SK_Rule.glb, SK_Chopper / SK_Nine with
their magazines. The first-person scene is the one the build's previews and export gate share
(assets/_characters_pose.fp_scene): recipe eye, config.json views[0] for the hip, presentation.json sightRear /
relief for the aimed pose, Euler YXZ. Field of view as docs/unreal/ANIMATION.md section 9: 54 deg vertical at the
hip, 38 deg on the irons. 1920 x 1080.

    python art/blender/review/rule_review_r4.py --shot <name> [--samples 64]
    python art/blender/review/rule_review_r4.py --shot measure_<gun>_<pose>     (no render)

Outputs art/blender/review/sheets/rule_r4/<shot>.jpg (not committed); shots that hold the photo go to
art/out/review/rule_r4/ only.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(BL))
for p in (BL, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from mi import render  # noqa: E402
import rule_review as rr  # noqa: E402
import rule_review_r3 as r3  # noqa: E402

OUT = os.path.join(HERE, "sheets", "rule_r4")
PRIVATE = os.path.join(ROOT, "art", "out", "review", "rule_r4")
r3.OUT, r3.PRIVATE = OUT, PRIVATE
FP_RES = (1920, 1080)
FOV = {"hip": 54.0, "aim": 38.0}
LOG = r3.LOG


def load_arms():
    """The export, with the build's preview materials (the stand-in for the Unreal skin material)."""
    from assets import rule
    arm, meshes = rr.load_arms()
    mats = rule.textured_materials()
    for m in meshes:
        for s in m.material_slots:
            if s.material is None:
                continue
            key = s.material.name.split(".")[0]
            if key in mats:
                s.material = mats[key]
    LOG["slots"] = sorted({s.material.name for m in meshes for s in m.material_slots if s.material})
    return arm, meshes


def armed(name, pose):
    from assets import _characters_pose as PZ
    col = bpy.context.scene.collection
    R, Rl = rr.arms_rig()
    arm, meshes = load_arms()
    rr.bracelet(arm)
    cam, g, M, rep = PZ.fp_scene(arm, R, Rl, name, pose, col)
    cam.data.angle_y = math.radians(FOV[pose])
    LOG["hold"] = rep
    return arm, meshes, cam, g, M, R, Rl


def fp(shot, S):
    _, name, pose, light = shot.split("_")
    armed(name, pose)
    render.setup(samples=S, res=FP_RES, threads=3)
    r3.street(light == "shade")
    p = os.path.join(OUT, shot + ".jpg")
    render.render_jpeg(p, S, FP_RES, max_kb=900)
    return p


def grip(name, S):
    """Fist on the grip: the CHOPPER from the right (firing hand), the NINE from the left and below (support hand
    wrapped over the firing hand)."""
    arm, meshes, cam, g, M, R, Rl = armed(name, "hip")
    G = M.to_3x3()
    X, Y, Z = (G @ Vector(v) for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    if name == "chopper":
        t = M @ Vector((0.05, -0.015, -0.07))
        c = t - Y * 0.36 + X * 0.07 - Z * 0.04
    else:
        t = M @ Vector((0.02, 0.01, -0.07))
        c = t + Y * 0.32 + X * 0.10 - Z * 0.06
    render.cam_look(tuple(c), tuple(t), lens=50)
    render.setup(samples=S, res=(1280, 720), threads=3)
    r3.street(False)
    p = os.path.join(OUT, "grip_%s.jpg" % name)
    render.render_jpeg(p, S, (1280, 720), max_kb=600)
    return p


def measure(name, pose):
    """Hand skin against the gun: per vertex weighted to a hand or finger bone, the distance to the nearest gun face
    and which side of it (by that face's normal; approximate on open parts). Fingertip pads: distance per finger."""
    from assets import _characters_pose as PZ
    arm, meshes, cam, g, M, R, Rl = armed(name, pose)
    bvh = PZ.world_bvh(PZ.gun_meshes())
    dg = bpy.context.evaluated_depsgraph_get()
    hand = ("thumb", "index", "middle", "ring", "pinky", "hand")
    out = {"inside_1mm": 0, "inside_3mm": 0, "touch_0_2mm": 0, "hand_verts": 0, "tips": {}}
    for o in meshes:
        names = [vg.name for vg in o.vertex_groups]
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        for v, ve in zip(o.data.vertices, me.vertices):
            gs = [(names[x.group], x.weight) for x in v.groups if x.weight > 0.3]
            if not gs:
                continue
            top = max(gs, key=lambda t: t[1])[0]
            if not top.startswith(hand):
                continue
            p = e.matrix_world @ ve.co
            loc, nrm, _i, d = bvh.find_nearest(p, 0.2)
            if loc is None:
                continue
            out["hand_verts"] += 1
            sd = d if (p - loc).dot(nrm) >= 0 else -d
            if sd < -0.001:
                out["inside_1mm"] += 1
            if sd < -0.003:
                out["inside_3mm"] += 1
            if abs(sd) < 0.002:
                out["touch_0_2mm"] += 1
            if top.endswith("_03_r") or top.endswith("_03_l"):
                k = top[:-5] + top[-2:]
                out["tips"][k] = round(min(out["tips"].get(k, 9), sd) * 1000, 1)
        e.to_mesh_clear()
    LOG["measure"] = out
    return "measure"


def main():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    shot = a[a.index("--shot") + 1]
    S = int(a[a.index("--samples") + 1]) if "--samples" in a else 64
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PRIVATE, exist_ok=True)
    if shot.startswith("fp_"):
        p = fp(shot, S)
    elif shot.startswith("grip_"):
        p = grip(shot[5:], S)
    elif shot.startswith("measure_"):
        _, name, pose = shot.split("_")
        p = measure(name, pose)
    elif shot == "hands_back_palm":
        rr.load_arms = _patched_loader(rr.load_arms)
        p = r3.hands_sheet(S)
    elif shot == "tattoos_photo":
        rr.load_arms = _patched_loader(rr.load_arms)
        p = r3.tattoos(S)
    elif shot.startswith("face_"):
        p = r3.face(float(shot[5:-1]), S)
    elif shot == "body_poses":
        p = r3.body(S)
    else:
        raise SystemExit("unknown shot " + shot)
    print("REVIEW done", p, json.dumps(LOG, default=str))


def _patched_loader(orig):
    def f():
        rr.load_arms = orig
        try:
            return load_arms()
        finally:
            rr.load_arms = f
    return f


if __name__ == "__main__":
    main()
