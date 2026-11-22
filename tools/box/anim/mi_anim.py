"""Editor helpers of the animation-pack scratch project (/project/ue/animpack), run through MCP on port 8003:

    MI_MCP_URL=http://127.0.0.1:8003/mcp python3 mi_mcp.py py - <<< 'import sys; sys.path.insert(0, "/project/ue/animpack/scripts"); import mi_anim as A; A.<fn>(...)'

Reading clips: cs(anim, t, bones) gives component-space transforms from an AnimSequence (AnimPose, no actor and no
viewport tick needed). Gun space: the pack's rifle hangs from ik_hand_gun with an identity transform (proved by
attach_report), so G^-1 * bone is a hand in the pack gun's space.
"""
import json
import math

import unreal

PACK = "/Game/ThirdParty/InfimaTFA"
SKELETON = "/Game/Characters/Mannequins/Meshes/SK_Mannequin"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
RIFLE = PACK + "/Weapon/SK_TFA_AR_Default_Combined"
ASSETS = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
WS = unreal.AnimPoseSpaces.WORLD
LS = unreal.AnimPoseSpaces.LOCAL


def _set(obj, **kw):
    for k, v in kw.items():
        obj.set_editor_property(k, v)


def clip(path):
    if not path.startswith("/"):
        path = PACK + "/Character/" + path
    return unreal.load_asset(path)


def _opts():
    o = unreal.AnimPoseEvaluationOptions()
    _set(o, evaluation_type=unreal.AnimDataEvalType.RAW, should_retarget=False, extract_root_motion=False)
    return o


def pose(anim, t):
    return unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, float(t), _opts())


def cs(anim, t, bones, space=WS):
    p = pose(anim, t)
    return {b: unreal.AnimPoseExtensions.get_bone_pose(p, b, space) for b in bones}


def v3(v, nd=2):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def rot3(t, nd=1):
    r = t.rotation.rotator()
    return [round(r.roll, nd), round(r.pitch, nd), round(r.yaw, nd)]


def rel(parent, child):
    """child expressed in parent's frame."""
    return child.multiply(parent.inverse())


def ref_cs(mesh_path):
    """Component-space reference pose of a skeletal mesh's bones."""
    m = unreal.load_asset(mesh_path)
    sk = m.get_editor_property("skeleton")
    p = unreal.AnimPoseExtensions.get_reference_pose(sk)
    names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(p)]
    return {n: unreal.AnimPoseExtensions.get_ref_bone_pose(p, n, WS) for n in names}


PALM = ("hand_{s}", "index_metacarpal_{s}", "middle_metacarpal_{s}", "ring_metacarpal_{s}", "pinky_metacarpal_{s}",
        "index_01_{s}", "middle_01_{s}", "ring_01_{s}", "pinky_01_{s}")


def palm_centre(tr, side):
    pts = [tr[b.format(s=side)].translation for b in PALM]
    c = unreal.Vector(0, 0, 0)
    for p in pts:
        c = c + p
    return c * (1.0 / len(pts))


def hands_in_gun(anim, t, gun_bone="ik_hand_gun"):
    bones = [gun_bone] + [b.format(s=s) for b in PALM for s in "lr"] + ["index_03_r", "thumb_03_l", "middle_03_l",
                                                                        "head", "camera" if False else "neck_01"]
    tr = cs(anim, t, bones)
    g = tr[gun_bone]
    out = {}
    for s in "lr":
        pc = palm_centre(tr, s)
        out["palm_" + s] = v3(g.inverse_transform_location(pc))
        out["hand_" + s] = v3(g.inverse_transform_location(tr["hand_" + s].translation))
        out["hand_%s_rot" % s] = rot3(rel(g, tr["hand_" + s]))
    out["index_tip_r"] = v3(g.inverse_transform_location(tr["index_03_r"].translation))
    out["head"] = v3(g.inverse_transform_location(tr["head"].translation))
    out["gun_cs"] = {"loc": v3(g.translation), "rot": rot3(g)}
    return out


def track(anim, bones, step=1.0 / 30, space=WS, frame=None):
    """Positions of bones over the clip (component space, or in `frame` bone's space)."""
    n = int(round(anim.get_play_length() / step)) + 1
    out = []
    for i in range(n):
        t = min(i * step, anim.get_play_length())
        tr = cs(anim, t, list(bones) + ([frame] if frame else []), space)
        if frame:
            f = tr[frame]
            out.append([round(t, 4)] + [v3(f.inverse_transform_location(tr[b].translation)) for b in bones])
        else:
            out.append([round(t, 4)] + [v3(tr[b].translation) for b in bones])
    return out


def weapon_track(anim, bones, step=1.0 / 30):
    """Weapon bones relative to their reference pose over the clip: (t, {bone: [dx, dy, dz, droll, dpitch, dyaw]})."""
    n = int(round(anim.get_play_length() / step)) + 1
    ref = None
    out = []
    for i in range(n):
        t = min(i * step, anim.get_play_length())
        tr = cs(anim, t, bones, LS)
        p = pose(anim, t)
        row = {}
        for b in bones:
            r = unreal.AnimPoseExtensions.get_ref_bone_pose(p, b, LS)
            d = tr[b].translation - r.translation
            q = rel(r, tr[b]).rotation.rotator()
            row[b] = [round(d.x, 2), round(d.y, 2), round(d.z, 2), round(q.roll, 1), round(q.pitch, 1), round(q.yaw, 1)]
        out.append([round(t, 4), row])
    return out
