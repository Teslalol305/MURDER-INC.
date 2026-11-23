"""Export gate of SK_RuleArms (review round 3): the skin is posed through every arm clip on hand and both gun holds,
and the export fails when skin comes near the eye or leaves its bones.

The round 2 check only tested the rest pose and that every vertex was weighted, and missed 1,867 vertices per arm on
the back of the upper arm that carried hand and thumb weights: when the elbow folded (the NINE hold, reloads, melee)
the hand dragged them across the camera in sheets.

Poses: the mannequin clips in art/out/epic (rifle and pistol aim, both reloads, the unarmed attack, the rifle jog),
every STEP frames; the CHOPPER and the NINE at the game's hip view and aimed (_characters_pose.fp_scene, the hands
solved onto the guns). Checks per pose on the evaluated skin:
  eye       no skin within EYE_CLEAR of the eye (the recipe's eye: the head joint lowered 0.58 cm; in the gun holds
            the first-person camera itself)
  capsule   no vertex more than CAPSULE_OUT outside the capsule of the bones that weight it (each bone's capsule:
            its posed head-tail segment with the rest pose's largest distance of the skin it dominates, + 1 cm)
Writes the report into <glb>.check.json (key "posed_gate") and returns it; rep["ok"] is False on any failure.
"""
import json
import math

import bpy
import numpy as np
from mathutils import Vector

from mi import char, scene

CLIPS = ("rifle_idle_ads", "pistol_idle_ads", "rifle_reload", "pistol_reload", "unarmed_attack", "rifle_jog_fwd")
STEP = 6
EYE_CLEAR = 0.10
CAPSULE_OUT = 0.06
EYE_DROP = 0.0058


def _segments(arm, names, posed):
    out = []
    for n in names:
        b = arm.data.bones.get(n)
        if b is None:
            out.append(None)
            continue
        if posed:
            pb = arm.pose.bones[n]
            a = arm.matrix_world @ pb.head
            t = arm.matrix_world @ pb.tail
        else:
            a = arm.matrix_world @ b.head_local
            t = arm.matrix_world @ b.tail_local
        out.append((np.array(a), np.array(t)))
    return out


def _seg_dist(p, a, t):
    ab = t - a
    L2 = max(float(ab @ ab), 1e-12)
    s = np.clip(((p - a) @ ab) / L2, 0, 1)
    return np.linalg.norm(p - a - s[:, None] * ab[None], axis=1)


def _skin_world(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    me = e.to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    Mn = np.array(e.matrix_world)
    co = co.reshape(-1, 3) @ Mn[:3, :3].T + Mn[:3, 3]
    e.to_mesh_clear()
    return co


class Gate:
    def __init__(self, ob, arm):
        self.ob, self.arm = ob, arm
        names, W = char.weight_matrix(ob)
        self.names, self.W = names, W
        char.rest_pose(arm)
        co = _skin_world(ob)
        segs = _segments(arm, names, False)
        self.radius = np.zeros(len(names))
        for j, sg in enumerate(segs):
            dom = W[:, j] > 0.5
            if sg is None or not dom.any():
                self.radius[j] = 0.05
                continue
            self.radius[j] = float(_seg_dist(co[dom], *sg).max()) + 0.01
        self.rows = []

    def check(self, label, eye):
        co = _skin_world(self.ob)
        d_eye = np.linalg.norm(co - np.array(eye)[None], axis=1)
        segs = _segments(self.arm, self.names, True)
        out = np.full(len(co), 1e9)
        for j, sg in enumerate(segs):
            m = self.W[:, j] > 0.1
            if sg is None or not m.any():
                continue
            out[m] = np.minimum(out[m], _seg_dist(co[m], *sg) - self.radius[j])
        out[out > 1e8] = 0.0
        row = {"pose": label, "eye_min_m": round(float(d_eye.min()), 4), "near_eye": int((d_eye < EYE_CLEAR).sum()),
               "capsule_out_max_m": round(float(out.max()), 4), "outside": int((out > CAPSULE_OUT).sum())}
        row["ok"] = row["near_eye"] == 0 and row["outside"] == 0
        self.rows.append(row)
        return row


def eye_of(arm):
    bpy.context.view_layer.update()
    head = (arm.matrix_world @ arm.pose.bones["head"].matrix).to_translation()
    return head + Vector((0, 0, -EYE_DROP))


def run(ob, arm, R, Rl, log=print, holds=True):
    from assets import _characters_pose as PZ
    g = Gate(ob, arm)
    for clip in CLIPS:
        try:
            src, _act, rng = char.import_clip(clip)
        except Exception as e:                      # a clip missing on this machine is reported, not fatal
            g.rows.append({"pose": clip, "skipped": str(e)[:120], "ok": True})
            continue
        for f in range(rng[0], rng[1] + 1, STEP):
            bpy.context.scene.frame_set(f)
            char.pose_from_armature(arm, src)
            g.check("%s@%d" % (clip, f), eye_of(arm))
        bpy.data.objects.remove(src, do_unlink=True)
        char.rest_pose(arm)
    if holds:
        col = scene.collection("Gate")
        for gun in ("chopper", "nine"):
            for pose in ("hip", "aim"):
                cam, root, M, rep = PZ.fp_scene(arm, R, Rl, gun, pose, col)
                g.check("%s_%s" % (gun, pose), cam.matrix_world.to_translation())
                for o in list(col.objects):
                    bpy.data.objects.remove(o, do_unlink=True)
                arm.location = (0, 0, 0)
                char.rest_pose(arm)
    fails = [r for r in g.rows if not r.get("ok")]
    rep = {"poses": len(g.rows), "failed": len(fails), "ok": not fails, "eye_clear_m": EYE_CLEAR,
           "capsule_out_m": CAPSULE_OUT, "worst_eye_m": min((r["eye_min_m"] for r in g.rows if "eye_min_m" in r), default=None),
           "worst_capsule_m": max((r["capsule_out_max_m"] for r in g.rows if "capsule_out_max_m" in r), default=None),
           "fails": fails[:20]}
    log("  posed gate: %d poses, %d failed, nearest skin to the eye %.3f m, worst capsule excess %.3f m"
        % (rep["poses"], rep["failed"], rep["worst_eye_m"] or -1, rep["worst_capsule_m"] or -1))
    return rep
