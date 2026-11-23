"""Pose tests of SK_RuleArms (used by characters.py on_preview): a reference clip from the mannequin set poses the
arms, the gun is put in the right hand by its briefed palm point, and the first-person camera is placed from the
gun by the web game's viewmodel pose (docs/unreal/spec/02-weapons-combat.md 2.13: vertical field of view 54 deg)."""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import char, paths

GUNS = {
    # gun-space palm points (X forward, Y left, Z up; metres) from the briefs; viewmodel poses (view space x right,
    # y up, z back; radians pitch, yaw, roll applied in three.js XYZ order)
    "chopper": dict(glb="SK_Chopper.glb", palm_r=(0.040, -0.016, -0.085), palm_l=(0.315, 0.0, -0.0615),
                    hip=((0.15, -0.09, -0.24), (0.05, 0.28, -0.35)), aim=((0.0, -0.0555, -0.1365), (0, 0, 0)),
                    size=(0.502, 0.065, 0.292)),
    "nine": dict(glb="SK_Nine.glb", palm_r=(0.014, -0.014, -0.078), palm_l=None,
                 hip=((0.105, -0.056, -0.36), (0.07, 0.11, -0.18)), aim=((0.0, -0.0185, -0.3575), (0, 0, 0)),
                 size=(0.234, 0.031, 0.153)),
}
FOV_V = 54.0


def bone_world(arm, name, point_rest):
    """A rest-pose world point carried by bone `name` into the current pose."""
    b = arm.data.bones[name]
    pb = arm.pose.bones[name]
    loc = b.matrix_local.inverted() @ Vector(point_rest)
    return arm.matrix_world @ pb.matrix @ loc


def palm_rest(R):
    """Centre of the palm's surface in the rest pose (on the glove)."""
    return R.W + R.fwd * 0.052 - R.dors * 0.020 + R.lat * 0.004


def hand_axes(arm, side, R):
    """Posed hand frame (fwd, lat, dors) carried from the rest frame by the hand bone."""
    b = arm.data.bones["hand_" + side]
    Rm = (arm.matrix_world @ arm.pose.bones["hand_" + side].matrix @ b.matrix_local.inverted()).to_3x3()
    return [np.array(Rm @ Vector(v)) for v in (R.fwd, R.lat, R.dors)]


def load_gun(name, col):
    g = GUNS[name]
    path = os.path.join(paths.glb, g["glb"])
    before = set(bpy.data.objects)
    if os.path.exists(path):
        bpy.ops.import_scene.gltf(filepath=path, bone_heuristic="BLENDER", guess_original_bind_pose=False,
                                  disable_bone_shape=True)
        new = [o for o in bpy.data.objects if o not in before]
        root = bpy.data.objects.new("Gun_" + name, None)
        col.objects.link(root)
        for o in new:
            for c in o.users_collection:
                c.objects.unlink(o)
            col.objects.link(o)
            if o.parent is None:
                o.parent = root
        return root, True
    from mi import geo
    L, W, H = g["size"]
    box = geo.box((L, W, H), bevel=0.004, base=False, name="Gun_" + name)
    geo.transform(box, loc=(L / 2 - 0.02, 0, -H * 0.25))
    col.objects.link(box) if box.name not in col.objects else None
    return box, False


def place_gun(gun, name, arm, Rr, Rl=None):
    """Put the gun's right palm point on the right palm, the bore along the line to the left palm (rifle) or along
    the hand (pistol), the gun's up as close to the hand's thumb side as that allows."""
    g = GUNS[name]
    pr = np.array(bone_world(arm, "hand_r", palm_rest(Rr)))
    fwd, lat, dors = hand_axes(arm, "r", Rr)
    if g["palm_l"] is not None and Rl is not None:
        pl = np.array(bone_world(arm, "hand_l", palm_rest(Rl)))
        dg = np.array(g["palm_l"]) - np.array(g["palm_r"])
        dw = pl - pr
        # rotation taking gun vector dg to world dw, and gun up toward the right hand's -lat (thumb side)
        x = dw / np.linalg.norm(dw)
        up = -lat - x * (x @ -lat)
        up /= np.linalg.norm(up)
        y = np.cross(up, x)
        Rw = np.stack([x, y, up], axis=1)
        a = math.atan2(dg[2], dg[0])                          # the palm line rises in gun space: tilt back
        Rw = Rw @ np.array(Matrix.Rotation(a, 3, "Y"))
    else:
        up = -lat
        x = fwd - up * (fwd @ up)
        x /= np.linalg.norm(x)
        y = np.cross(up, x)
        Rw = np.stack([x, y, up], axis=1) @ np.array(Matrix.Rotation(math.radians(-18), 3, "Y"))
    t = pr - Rw @ np.array(g["palm_r"])
    M = Matrix.Identity(4)
    for i in range(3):
        for j in range(3):
            M[i][j] = Rw[i, j]
        M[i][3] = t[i]
    gun.matrix_world = M
    return M


def viewmodel_camera(gun_M, name, pose="hip", col=None):
    """Camera placed so the gun sits at the web game's viewmodel pose in view space."""
    (px, py, pz), (rx, ry, rz) = GUNS[name][pose]
    C = Matrix(((0, -1, 0, 0), (0, 0, 1, 0), (-1, 0, 0, 0), (0, 0, 0, 1)))   # gun axes -> three.js gun axes
    R = Matrix.Rotation(rx, 4, "X") @ Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rz, 4, "Z")
    V = Matrix.Translation((px, py, pz)) @ R @ C
    cam_M = gun_M @ V.inverted()
    cd = bpy.data.cameras.new("FP")
    cd.sensor_fit = "VERTICAL"
    cd.angle_y = math.radians(FOV_V)
    cd.clip_start = 0.01
    cam = bpy.data.objects.new("FP", cd)
    (col or bpy.context.scene.collection).objects.link(cam)
    cam.matrix_world = cam_M
    bpy.context.scene.camera = cam
    return cam


def close_fingers(arm, side, R, amount, fingers=("index", "middle", "ring", "pinky"), thumb=0.0,
                  angles=((70, 95, 55))):
    """Curl fingers about their hinges toward the palm (on top of the current pose): amount 0..1 of a full grip."""
    fwd, lat, dors = hand_axes(arm, side, R)
    palm = Vector(-dors)
    across = Vector(lat)
    for f in fingers:
        for k, ang in zip(("01", "02", "03"), angles):
            _curl(arm, "%s_%s_%s" % (f, k, side), math.radians(ang * amount), across, palm)
    if thumb:
        for k, ang in (("01", 12), ("02", 25), ("03", 45)):
            _curl(arm, "thumb_%s_%s" % (k, side), math.radians(ang * thumb), Vector(fwd), palm)


def _curl(arm, bone, angle, across, palm):
    """Rotate a finger bone (and its children) about the hinge axis through its head so it flexes toward palm."""
    bpy.context.view_layer.update()
    pb = arm.pose.bones[bone]
    M = arm.matrix_world @ pb.matrix
    head = M.to_translation()
    kid = pb.children[0] if pb.children else None
    tip = (arm.matrix_world @ kid.matrix).to_translation() if kid else M @ Vector((0, pb.bone.length, 0))
    d = (tip - head).normalized()
    axis = (across - d * across.dot(d)).normalized()
    if axis.cross(d).dot(palm) < 0:
        axis = -axis
    Rm = Matrix.Translation(head) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-head)
    pb.matrix = arm.matrix_world.inverted() @ Rm @ M
    bpy.context.view_layer.update()


# ------------------------------------------------------------------------------------------------ arm IK


def _frame(d, n):
    d = d.normalized()
    n = (n - d * n.dot(d)).normalized()
    return Matrix((d, n, d.cross(n))).transposed()


def _set_bone(arm, name, Rw, new_head, rest_head):
    """Pose a bone so that its rest frame is rotated by Rw about its rest head and moved to new_head (world)."""
    b = arm.data.bones[name]
    M = Matrix.Translation(new_head) @ Rw.to_4x4() @ Matrix.Translation(-rest_head) @ (arm.matrix_world @ b.matrix_local)
    arm.pose.bones[name].matrix = arm.matrix_world.inverted() @ M
    bpy.context.view_layer.update()


def ik_arm(arm, side, R, palm_target, hand_axes_target, pole):
    """Two-bone IK of one arm from its (posed) shoulder: the palm point (palm_rest(R)) goes to palm_target, the
    hand's (fwd, lat, dors) to hand_axes_target, the elbow toward `pole` (a world direction). The forearm twist
    is shared by the two twist bones (2/3 and 1/3) so the wrist does not wrap. Fingers keep their pose."""
    bpy.context.view_layer.update()
    # rest heads in WORLD space: reach_forward moves the armature object, and _set_bone composes with
    # arm.matrix_world (armature-local heads here put both palms off by that move)
    MW = arm.matrix_world
    rest = {n: MW @ Vector(arm.data.bones[n + "_" + side].head_local) for n in ("upperarm", "lowerarm", "hand")}
    S = (arm.matrix_world @ arm.pose.bones["upperarm_" + side].matrix).to_translation()
    fwd_t, lat_t, dors_t = (Vector(v).normalized() for v in hand_axes_target)
    Rrest = Matrix((Vector(R.fwd), Vector(R.lat), Vector(R.dors))).transposed()
    Rtgt = Matrix((fwd_t, lat_t, dors_t)).transposed()
    Rhand = Rtgt @ Rrest.inverted()
    palm0 = MW @ Vector(palm_rest(R))
    Wt = Vector(palm_target) - Rhand @ (palm0 - rest["hand"])
    Lu = (rest["lowerarm"] - rest["upperarm"]).length
    Lf = (rest["hand"] - rest["lowerarm"]).length
    d = Wt - S
    D = min(d.length, (Lu + Lf) * 0.999)
    dn = d.normalized()
    a = math.acos(max(-1, min(1, (Lu * Lu + D * D - Lf * Lf) / (2 * Lu * D))))
    pn = (Vector(pole) - dn * Vector(pole).dot(dn)).normalized()
    E = S + (dn * math.cos(a) + pn * math.sin(a)) * Lu
    Wt = S + dn * D
    # upper arm and forearm: rotate the rest segment and the rest arm plane onto the new ones
    nrest = (rest["lowerarm"] - rest["upperarm"]).cross(rest["hand"] - rest["lowerarm"])
    nnew = (E - S).cross(Wt - E)
    Ru = _frame(E - S, nnew) @ _frame(rest["lowerarm"] - rest["upperarm"], nrest).inverted()
    _set_bone(arm, "upperarm_" + side, Ru.to_3x3(), S, rest["upperarm"])
    Rf = _frame(Wt - E, nnew) @ _frame(rest["hand"] - rest["lowerarm"], nrest).inverted()
    # share the hand's roll about the forearm axis with the forearm
    ax = (Wt - E).normalized()
    hx = Rhand @ Vector(R.lat)
    fx = Rf @ Vector(R.lat)
    hx_p = (hx - ax * hx.dot(ax)).normalized()
    fx_p = (fx - ax * fx.dot(ax)).normalized()
    roll = math.atan2(fx_p.cross(hx_p).dot(ax), fx_p.dot(hx_p))
    Rf = Matrix.Rotation(roll * 0.5, 3, ax) @ Rf
    _set_bone(arm, "lowerarm_" + side, Rf.to_3x3(), E, rest["lowerarm"])
    for tw, k in (("lowerarm_twist_01_", 0.35), ("lowerarm_twist_02_", 0.0)):
        b = tw + side
        rh = MW @ Vector(arm.data.bones[b].head_local)
        new_head = E + Rf @ (rh - rest["lowerarm"])
        _set_bone(arm, b, (Matrix.Rotation(roll * k, 3, ax) @ Rf).to_3x3(), new_head, rh)
    _set_bone(arm, "hand_" + side, Rhand.to_3x3(), Wt, rest["hand"])
    return E, Wt


def eye_camera(arm, col=None, ahead=0.11, up=0.075, pitch=0.0):
    """First-person camera at the eyes (from the head bone), level, looking along -Y (the mannequin's front)."""
    bpy.context.view_layer.update()
    head = (arm.matrix_world @ arm.pose.bones["head"].matrix).to_translation()
    eye = head + Vector((0, -ahead, up))
    cd = bpy.data.cameras.new("FP")
    cd.sensor_fit = "VERTICAL"
    cd.angle_y = math.radians(FOV_V)
    cd.clip_start = 0.01
    cam = bpy.data.objects.new("FP", cd)
    (col or bpy.context.scene.collection).objects.link(cam)
    cam.matrix_world = (Matrix.Translation(eye) @ Matrix.Rotation(math.radians(180), 4, "Z")
                        @ Matrix.Rotation(math.radians(90 + pitch), 4, "X"))
    bpy.context.scene.camera = cam
    return cam


def gun_from_camera(cam, name, pose="hip"):
    """World matrix of the gun at the viewmodel pose in front of `cam`."""
    (px, py, pz), (rx, ry, rz) = GUNS[name][pose]
    C = Matrix(((0, -1, 0, 0), (0, 0, 1, 0), (-1, 0, 0, 0), (0, 0, 0, 1)))
    Rm = Matrix.Rotation(rx, 4, "X") @ Matrix.Rotation(ry, 4, "Y") @ Matrix.Rotation(rz, 4, "Z")
    return cam.matrix_world @ Matrix.Translation((px, py, pz)) @ Rm @ C


def reach_forward(arm, targets, slack=0.90, forward=Vector((0, -1, 0)), limit=0.09):
    """First-person arms are placed for the camera, not the neck: slide the whole rig forward (and the
    shoulders with it) until every palm target is within `slack` of the arm's reach."""
    bpy.context.view_layer.update()
    need = 0.0
    for side, p, R in targets:
        S = (arm.matrix_world @ arm.pose.bones["upperarm_" + side].matrix).to_translation()
        reach = (R.Lu + R.L + 0.06) * slack
        for k in range(60):
            d = k * 0.01
            if ((S + forward * d) - Vector(p)).length <= reach:
                break
        need = max(need, d)
    need = min(need, limit)                  # the shoulders must stay behind the camera
    arm.location = arm.location + forward * need
    bpy.context.view_layer.update()
    return need


def protract(arm, side, target, R, slack=0.93, max_deg=32.0):
    """Bring a shoulder forward and in (the clavicle swings about its sternal end, as the support shoulder does
    on a long gun) until the palm target is within `slack` of the arm's reach, at most max_deg."""
    bpy.context.view_layer.update()
    reach = (R.Lu + R.L + 0.06) * slack
    cb = "clavicle_" + side
    if cb not in arm.pose.bones:
        return 0.0
    pb = arm.pose.bones[cb]
    M0 = arm.matrix_world @ pb.matrix
    piv = M0.to_translation()
    S0 = (arm.matrix_world @ arm.pose.bones["upperarm_" + side].matrix).to_translation()
    tgt = Vector(target)
    best = 0.0
    for k in range(0, int(max_deg) + 1):
        ang = math.radians(k)
        # swing about the vertical through the sternal end, toward the target's side, and a little down
        sgn = 1.0 if (S0 - piv).cross(tgt - piv).z > 0 else -1.0
        Rm = Matrix.Rotation(sgn * ang, 3, "Z")
        S = piv + Rm @ (S0 - piv)
        best = k
        if (S - tgt).length <= reach:
            break
    Rm4 = Matrix.Translation(piv) @ Matrix.Rotation(sgn * math.radians(best), 4, "Z") @ Matrix.Translation(-piv)
    pb.matrix = arm.matrix_world.inverted() @ Rm4 @ M0
    bpy.context.view_layer.update()
    return best


def hold(arm, gun_M, name, Rr, Rl):
    """IK both arms onto the gun: right palm on the grip, left palm under the handguard (rifle) or over the
    firing hand (pistol). Hand frames are built in gun space and carried to the world."""
    G = gun_M.to_3x3()
    X, Y, Z = (G @ Vector(v) for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    g = GUNS[name]
    sr = 1.0 if Vector(Rr.dors).dot(Vector(Rr.fwd).cross(Vector(Rr.lat))) > 0 else -1.0
    sl = 1.0 if Vector(Rl.dors).dot(Vector(Rl.fwd).cross(Vector(Rl.lat))) > 0 else -1.0
    # right hand: fingers forward round the grip's front, index at the top, palm on the right face
    rake = math.radians(17)
    down = (-Z * math.cos(rake) - X * math.sin(rake)).normalized()
    fwd = (X - down * X.dot(down)).normalized()
    lat = down
    dors = (fwd.cross(lat) * sr).normalized()
    pr = gun_M @ Vector(g["palm_r"])
    pl0 = gun_M @ Vector(g["palm_l"] if g["palm_l"] else (0.020, 0.036, -0.080))
    # the rig may come 12 cm forward of the neck (first-person arms are placed for the camera); the support
    # shoulder protracts for the rest of a long gun's reach
    reach_forward(arm, [("r", pr, Rr), ("l", pl0, Rl)], slack=0.93, limit=0.12)
    if name == "chopper":
        protract(arm, "l", pl0, Rl)
    ik_arm(arm, "r", Rr, pr, (fwd, lat, dors), Vector((0.3, 0.6, -1)))
    if name == "chopper":
        # left hand cupping the 46 mm handguard from below: palm up under it, fingers wrapping up its right
        # side, thumb along its left side; the palm's flesh 1.2 cm under the handguard's lower face
        pl = gun_M @ Vector(g["palm_l"]) + Z * -0.012
        fwd_l = (-Y * 0.80 + X * 0.50 + Z * 0.10).normalized()
        dors_l = -Z
        lat_l = (dors_l.cross(fwd_l) * sl).normalized()
        dors_l = (fwd_l.cross(lat_l) * sl).normalized()
        ik_arm(arm, "l", Rl, pl, (fwd_l, lat_l, dors_l), Vector((0.1, 0.2, -1)))
    else:
        pl = gun_M @ Vector((0.020, 0.036, -0.080))
        fwd_l = (X * 0.75 - Z * 0.45 - Y * 0.2).normalized()
        lat_l = (-Z - fwd_l * (-Z).dot(fwd_l)).normalized()
        dors_l = (fwd_l.cross(lat_l) * sl).normalized()
        ik_arm(arm, "l", Rl, pl, (fwd_l, lat_l, dors_l), Vector((-0.4, 0.4, -1)))
    grip(arm, name, Rr, Rl)


def reset_fingers(arm, side):
    for f in ("index", "middle", "ring", "pinky", "thumb"):
        for k in ("01", "02", "03"):
            arm.pose.bones["%s_%s_%s" % (f, k, side)].matrix_basis = Matrix.Identity(4)
    for f in ("index", "middle", "ring", "pinky"):
        arm.pose.bones["%s_metacarpal_%s" % (f, side)].matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def grip(arm, name, Rr, Rl):
    """Close the hands on the gun: firing hand round the grip with the index on the trigger, support hand
    round the handguard (rifle) or over the firing hand (pistol)."""
    reset_fingers(arm, "r")
    reset_fingers(arm, "l")
    close_fingers(arm, "r", Rr, 0.86, ("middle", "ring", "pinky"), thumb=0.85)
    close_fingers(arm, "r", Rr, 1.0, ("index",), angles=(38, 62, 30))
    if name == "chopper":
        # round a 46 mm handguard: the four fingers curl up its right side, the thumb lies along its left
        close_fingers(arm, "l", Rl, 0.80, angles=(55, 70, 40))
        close_fingers(arm, "l", Rl, 0.6, (), thumb=0.6)
    else:
        close_fingers(arm, "l", Rl, 0.82, thumb=0.55)
