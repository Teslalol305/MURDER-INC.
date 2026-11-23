"""The solved grips of SK_RuleArms as data for the game (second pass of the hands-and-tattoos work).

In the game the NINE was held by the engine template's third-person pistol idle with both palms pulled onto the gun's
Palm_R / Palm_L sockets: the template's hand shape stayed, so the pistol rested on a flat support hand, the firing
fingers ran straight under the frame and nothing wrapped the grip (the in-game review's worst fault). The previews
already solve both hands onto each gun by contact (_characters_pose.hold: palm seated, every finger closed to 1.5 mm
of the gun or of the other hand, the trigger pad and both thumbs searched). This writes that solve out so the game
can apply it:

    art/out/glb/SK_RuleArms.grips.json   (shipped beside the GLB by tools/box/fp/fp-art.sh; also
                                          unreal/MurderInc/Content/Data/grips.json, which the game reads)

Bone axes differ between Blender, glTF and Unreal (Unreal's glTF import swaps each bone's local Y and Z:
docs/unreal/CHARACTERS.md), so no rotation is written. Every hand is written as POINTS in the gun's own space, in
Unreal's convention (cm; X forward, Y right, Z up; Blender's gun space is X forward, Y left, Z up): the wrist (hand_*
head) and the head of every finger bone from the metacarpal on, plus each finger's tip (the end of its _03 bone). The
game rebuilds the hand's rotation from three of those points and aims each finger bone at its child's point
(UMIFirstPersonRig, MIFirstPersonAnim.cpp FMIFPHandShape), whatever the bones' local axes.

Run (one Blender process at a time):
    venv/bin/python art/blender/assets/_rule_grips.py [nine chopper] [--pose hip|aim]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

FINGERS = ("thumb", "index", "middle", "ring", "pinky")


def _ue(gun_inv, p):
    q = gun_inv @ p
    return [round(q.x * 100, 3), round(-q.y * 100, 3), round(q.z * 100, 3)]


def hand_points(arm, side, gun_M):
    """{bone: [x, y, z] cm in the gun's Unreal space} for the wrist and every finger joint, plus '<finger>_tip'."""
    gi = gun_M.inverted()
    W = arm.matrix_world
    out = {"hand_" + side: _ue(gi, W @ arm.pose.bones["hand_" + side].head)}
    for f in FINGERS:
        names = (["%s_metacarpal_%s" % (f, side)] if f != "thumb" else []) + ["%s_%02d_%s" % (f, k, side) for k in (1, 2, 3)]
        for n in names:
            if n in arm.pose.bones:
                out[n] = _ue(gi, W @ arm.pose.bones[n].head)
        out["%s_tip_%s" % (f, side)] = _ue(gi, W @ arm.pose.bones["%s_03_%s" % (f, side)].tail)
    return out


def wrap_fingers(arm, side, R, obst, fingers=("middle", "ring", "pinky"), full=(88.0, 100.0, 62.0), steps=44,
                 press=0.0025):
    """Second pass: each finger closed with its three joints together (full angles x t) to the most closed pose
    whose every phalanx stays within `press` (skin pressed onto the gun) of the obstacles. The contact search of
    _characters_pose.close_coupled stops at the first touch, and on the NINE that left the firing middle finger
    straight against the trigger guard and the support fingers open (3-6 degrees). Returns {finger: (t, clear mm)}."""
    import math
    from assets import _characters_pose as CP
    out = {}
    for f in fingers:
        across, palm = CP._hinge(arm, side, R, f)
        bones = ["%s_%02d_%s" % (f, k + 1, side) for k in range(3)]

        def pose(t):
            CP.reset_finger(arm, side, f)
            for b_, a_ in zip(bones, full):
                if a_ * t:
                    CP._curl(arm, b_, math.radians(a_ * t), across, palm)
            return CP._chain_clear(arm, side, R, f, (0, 1, 2), obst)
        cs = [pose(i / steps) for i in range(steps + 1)]
        ok = [i for i, c in enumerate(cs) if c >= -press]
        i = max(ok) if ok else int(max(range(len(cs)), key=lambda k: cs[k]))
        pose(i / steps)
        out[f] = (round(i / steps, 3), round(cs[i] * 1000, 1))
    return out


def regrip(arm, Rr, Rl, M, name, log=print):
    """The NINE's fingers re-closed by wrap_fingers (firing middle, ring, little finger round the grip's front strap;
    the support hand's four over them), the solved palms, trigger finger and thumbs kept."""
    from assets import _characters_pose as CP
    CP._armature_mods(arm, False)
    try:
        gun = CP.Obstacles([CP.world_bvh(CP.gun_meshes())])
        rep = {"r": wrap_fingers(arm, "r", Rr, gun)}
        obst_l = CP.Obstacles(gun.bvhs, CP.finger_capsules(arm, "r", Rr, ("index", "middle", "ring", "pinky")))
        rep["l"] = wrap_fingers(arm, "l", Rl, obst_l, fingers=("index", "middle", "ring", "pinky"), full=(80.0, 95.0, 60.0))
    finally:
        CP._armature_mods(arm, True)
        bpy_update()
    log("  regrip %s: %s" % (name, rep))
    return rep


def bpy_update():
    import bpy
    bpy.context.view_layer.update()


def solve(guns=("nine",), poses=("hip",), log=print):
    import bpy
    from mi import char
    from assets import characters as C
    from assets import _characters_pose as CP

    bpy.ops.wm.read_factory_settings(use_empty=True)
    col = bpy.data.collections.new("Grips")
    bpy.context.scene.collection.children.link(col)
    arm, body = char.import_mannequin()
    Rr, Rl = C.ArmRig(arm, body), C.ArmRig(arm, body, "l")
    out = {"note": __doc__.split("\n\n")[2].replace("\n", " "), "units": "cm, gun component space (X forward, Y right, Z up)",
           "guns": {}}
    # second pass: the previews' NINE placement put the firing hand's fingers on the trigger guard (the middle finger
    # met it straight) and the support palm high on the frame; for the game both palms sit lower on the grip so the
    # fingers wrap its front strap under the guard (firing palm 2.2 cm down the grip, was 0.6; support palm 0.6 cm
    # lower and 0.8 cm forward of its socket)
    CP.GRIP_DOWN["nine"] = 0.022
    CP.SUPPORT_OUT["nine"] = (0.008, 0.0, -0.006)
    for name in guns:
        for pose in poses:
            cam, g, M, rep = CP.fp_scene(arm, Rr, Rl, name, pose, col, log=None)
            rep["regrip"] = regrip(arm, Rr, Rl, M, name, log)
            entry = {"r": hand_points(arm, "r", M), "l": hand_points(arm, "l", M),
                     "contacts": {k: rep.get(k) for k in ("fingers_r", "fingers_l", "push_r_m", "push_l_m", "wrist_bend_deg", "regrip")}}
            out["guns"].setdefault(name, {})[pose] = entry
            log("grip %s %s: wrist r %s l %s" % (name, pose, entry["r"]["hand_r"], entry["l"]["hand_l"]))
            for o in [o for o in bpy.data.objects if o.name.startswith("Gun_")]:
                for c in list(o.children_recursive) + [o]:
                    bpy.data.objects.remove(c, do_unlink=True)
            bpy.data.objects.remove(cam, do_unlink=True)
    return out


def main(argv):
    from mi import paths
    guns = [a for a in argv if not a.startswith("--")] or ["nine"]
    poses = ["hip"]
    if "--pose" in argv:
        poses = argv[argv.index("--pose") + 1].split(",")
        guns = [g for g in guns if g not in poses]
    data = solve(tuple(guns), tuple(poses))
    p = os.path.join(paths.glb, "SK_RuleArms.grips.json")
    with open(p, "w") as f:
        json.dump(data, f, indent=1)
    game = os.path.join(HERE, "..", "..", "unreal", "MurderInc", "Content", "Data", "grips.json")
    with open(game, "w") as f:
        json.dump(data, f, indent=1)
    print("wrote", p, "and", os.path.normpath(game))


if __name__ == "__main__":
    main(sys.argv[1:])
