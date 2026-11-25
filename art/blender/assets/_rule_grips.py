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
    venv/bin/python art/blender/assets/_rule_grips.py [nine chopper shorty stretch rattler] [--pose hip,aim]
        [--pictures [--samples 24]] [--check]

The guns solved are MERGED into both files (a gun or pose not solved in this run keeps its entry). --pictures renders
each solve as the game frames it (the recipe eye, the gun's view pose, 54 deg) with SK_RuleArms.glb posed like the
solved skeleton: art/previews/grips_<gun>_<pose>.jpg. --check writes nothing: it compares the solve with what
grips.json holds (max difference over every point, cm), the proof that a gun's grip is unchanged.
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
        signed = name in CP.SIGNED_GUNS          # round 4: a finger buried in a solid part is not clear
        gun = CP.Obstacles([CP.world_bvh(CP.gun_meshes())], signed=signed)
        rep = {"r": wrap_fingers(arm, "r", Rr, gun)}
        obst_l = CP.Obstacles(gun.bvhs, CP.finger_capsules(arm, "r", Rr, ("index", "middle", "ring", "pinky")), signed=signed)
        rep["l"] = wrap_fingers(arm, "l", Rl, obst_l, fingers=("index", "middle", "ring", "pinky"), full=(80.0, 95.0, 60.0))
    finally:
        CP._armature_mods(arm, True)
        bpy_update()
    log("  regrip %s: %s" % (name, rep))
    return rep


def bpy_update():
    import bpy
    bpy.context.view_layer.update()


def solve(guns=("nine",), poses=("hip",), log=print, after=None):
    """Solve each gun at each pose; after(name, pose, arm, cam, M, entry), when given, runs on each solved scene
    (pictures) before the gun is removed."""
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
            log("  hold %s %s: %s" % (name, pose, json.dumps({k: rep.get(k) for k in ("rig", "support_palm_gun", "fingers_r", "fingers_l",
                                                                                         "push_r_m", "push_l_m", "wrist_bend_deg")})))
            if after is not None:
                after(name, pose, arm, cam, M, entry)
            for o in [o for o in bpy.data.objects if o.name.startswith("Gun_")]:
                for c in list(o.children_recursive) + [o]:
                    bpy.data.objects.remove(c, do_unlink=True)
            bpy.data.objects.remove(cam, do_unlink=True)
    return out


class Pictures:
    """First-person pictures of the solves: SK_RuleArms.glb (the build's preview skin) posed like the solved
    skeleton, the recipe camera at the gun's view pose (54 deg), asphalt under the design sun, 1280 x 720."""

    def __init__(self, samples=24, out_dir=None, threads=1):
        self.samples, self.threads = samples, threads
        from mi import paths
        self.out_dir = out_dir or paths.previews
        self.arms = None

    def _setup(self, solver_arm):
        import bpy
        from mi import paths, rig
        from assets import rule
        for o in solver_arm.children:                  # the mannequin's own body is the solver's, never drawn
            o.hide_render = True
        arms, meshes, _col = rig.import_glb(os.path.join(paths.glb, "SK_RuleArms.glb"), "Grip_Arms")
        mats = rule.textured_materials()
        for m in meshes:
            for s in m.material_slots:
                if s.material is not None and s.material.name.split(".")[0] in mats:
                    s.material = mats[s.material.name.split(".")[0]]
        me = bpy.data.meshes.new("GripGround")
        me.from_pydata([(-60, -80, 0), (60, -80, 0), (60, 80, 0), (-60, 80, 0)], [], [(0, 1, 2, 3)])
        g = bpy.data.materials.new("GripAsphalt")
        b = g.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.075, 0.072, 0.068, 1)
        b.inputs["Roughness"].default_value = 0.9
        me.materials.append(g)
        bpy.context.scene.collection.objects.link(bpy.data.objects.new("GripGround", me))
        self.arms, self.meshes = arms, meshes

    def pose(self, solver_arm):
        from mi import char
        if self.arms is None:
            self._setup(solver_arm)
        char.pose_from_armature(self.arms, solver_arm)

    def __call__(self, name, pose, arm, cam, M, entry):
        import bpy
        from mi import render
        self.pose(arm)
        render.setup(samples=self.samples, res=(1280, 720), threads=self.threads)
        render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING)
        bpy.context.scene.camera = cam
        p = os.path.join(self.out_dir, "grips_%s_%s.jpg" % (name, pose))
        _p, sec = render.render_jpeg(p, self.samples, (1280, 720), max_kb=290)
        print("picture %s %.0fs" % (p, sec))
        return p


def _max_diff(a, b):
    """Largest difference (cm) between two solved entries over every point both hold; None when nothing matches."""
    d = None
    for side in ("r", "l"):
        for k, v in a.get(side, {}).items():
            w = b.get(side, {}).get(k)
            if w is not None:
                e = max(abs(x - y) for x, y in zip(v, w))
                d = e if d is None else max(d, e)
    return d


def merge(path, data):
    """data's guns merged into the file at path (a gun or pose not in data keeps its entry)."""
    try:
        old = json.load(open(path))
    except (OSError, ValueError):
        old = {}
    out = {"note": data["note"], "units": data["units"], "guns": dict(old.get("guns", {}))}
    for name, poses in data["guns"].items():
        out["guns"].setdefault(name, {}).update(poses)
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    json.load(open(path))                      # it reads back as JSON
    return sorted(out["guns"])


RIFLES = ("chopper", "shorty", "stretch", "rattler")


def tidy_support(entry, middle_deg=0.0, distal_deg=20.0):
    """The support hand of a rifle solve, its middle and end phalanges laid along the forend's right face (hands pass,
    weapons round 4, docs/unreal/HANDS_R4.md). In the solves the end segment of every support finger points away from
    the gun (the '_tip' point, the tail of the _03 bone, runs 2 cm out to the right: middle finger 03 -> tip
    (-0.9, +2.1, +0.9) cm on the CHOPPER), so in the game, aimed, four straight fingers stood out to the right of the
    handguard like an open hand (stream runs h2 and h3, 01-chopper-aim, 21-stretch-aim). The metacarpal, knuckle (_01)
    and proximal joint (_02) points stay as the contact solve put them (knuckles at the forend's lower right edge, the
    proximal phalanx up its face); the middle phalanx continues the proximal one turned `middle_deg` toward the gun's
    centre line, the end one a further `distal_deg`: the fingers lie on the face instead of leaving it. Segment
    lengths are kept; points only (the game aims each finger bone at its child's point). Pure geometry: no Blender."""
    import math
    pts = entry["l"]

    def sub(a, b):
        return [a[i] - b[i] for i in range(3)]

    def length(a):
        return math.sqrt(sum(x * x for x in a))

    def norm(a):
        n = length(a) or 1.0
        return [x / n for x in a]

    for f in ("index", "middle", "ring", "pinky"):
        p1, p2, p3, tip = (pts["%s_%s_l" % (f, k)] for k in ("01", "02", "03", "tip"))
        u = norm(sub(p2, p1))
        d = -u[1]                                       # inward (gun space -Y: the right face's inside) along u
        n = norm([0.0 - d * u[0], -1.0 - d * u[1], 0.0 - d * u[2]])
        l2, l3 = length(sub(p3, p2)), length(sub(tip, p3))

        def turned(deg):
            a = math.radians(deg)
            return [u[i] * math.cos(a) + n[i] * math.sin(a) for i in range(3)]
        t2, t3 = turned(middle_deg), turned(middle_deg + distal_deg)
        q3 = [p2[i] + t2[i] * l2 for i in range(3)]
        qt = [q3[i] + t3[i] * l3 for i in range(3)]
        pts["%s_03_l" % f] = [round(x, 3) for x in q3]
        pts["%s_tip_l" % f] = [round(x, 3) for x in qt]
    return entry


def tidy_file(path, guns=RIFLES, poses=("hip", "aim")):
    """tidy_support on the rifle entries of a grips file (written back); returns what changed."""
    data = json.load(open(path))
    done = []
    for g in guns:
        for p in poses:
            e = data.get("guns", {}).get(g, {}).get(p)
            if e and "l" in e:
                tidy_support(e)
                done.append("%s/%s" % (g, p))
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
    json.load(open(path))
    return done


def main(argv):
    if "--tidy" in argv:
        # after a rifle solve: python _rule_grips.py --tidy [guns...]  (no Blender: grips.json's points only). The
        # proximal points are kept and the rest rebuilt from them with the same lengths, so a second run changes nothing.
        game = os.path.normpath(os.path.join(HERE, "..", "..", "unreal", "MurderInc", "Content", "Data", "grips.json"))
        glb = os.path.normpath(os.path.join(HERE, "..", "out", "glb", "SK_RuleArms.grips.json"))
        guns = [a for a in argv if not a.startswith("--")] or list(RIFLES)
        for f in (glb, game):
            if os.path.exists(f):
                print("tidied", f, tidy_file(f, guns))
        return
    from mi import paths
    flags = ("--pose", "--samples")
    guns = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in flags)] or ["nine"]
    poses = argv[argv.index("--pose") + 1].split(",") if "--pose" in argv else ["hip"]
    after = None
    if "--pictures" in argv:
        after = Pictures(samples=int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 24)
    data = solve(tuple(guns), tuple(poses), after=after)
    game = os.path.normpath(os.path.join(HERE, "..", "..", "unreal", "MurderInc", "Content", "Data", "grips.json"))
    if "--check" in argv:
        held = json.load(open(game)).get("guns", {})
        for name, ps in data["guns"].items():
            for pose, entry in ps.items():
                old = held.get(name, {}).get(pose)
                d = _max_diff(entry, old) if old else None
                print("check %s %s: %s" % (name, pose, "not in grips.json" if old is None else
                                           "max difference %.3f cm over every point" % d))
        return
    p = os.path.join(paths.glb, "SK_RuleArms.grips.json")
    for f in (p, game):
        print("wrote", f, "guns", merge(f, data))


if __name__ == "__main__":
    main(sys.argv[1:])
