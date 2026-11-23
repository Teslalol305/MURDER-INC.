"""Pose tests of SK_RuleArms (used by characters.py and rule.py previews and the export gate): the gun is put at the
game's viewmodel pose in front of the first-person camera, both arms are solved onto its Palm_R / Palm_L sockets and
every finger is closed onto the gun's surface (contact solve).

Review round 3: the camera is the recipe's eye (docs/unreal/ANIMATION.md section 9: the head joint lowered 0.58 cm),
the view pose is read from the game's data (config.json weapons.<gun>.views[0]; aimed: presentation.json relief and
the rear sight) and turned in Euler order YXZ as the game's gunPose builds it, so the previews show what the game
shows (vertical field of view 54 deg)."""
import json
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from mi import char, paths

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "unreal", "MurderInc", "Content",
                     "Data")


def _game_view(gun, fallback):
    """views[0] of config.json as ((x, y, z), (pitch, yaw, roll))."""
    try:
        v = json.load(open(os.path.join(_DATA, "config.json")))["weapons"][gun]["views"][0]
        return (tuple(v[:3]), tuple(v[3:6]))
    except (OSError, KeyError, ValueError, IndexError):
        return fallback


GUNS = {
    # gun-space palm points (X forward, Y left, Z up; metres): the guns' Palm_R / Palm_L sockets (read from the
    # file when it is loaded); viewmodel poses (view space x right, y up, z back; radians pitch, yaw, roll, Euler YXZ)
    "chopper": dict(glb="SK_Chopper.glb", parts=("SM_Weapon_ChopperMagazine.glb", "SM_Weapon_ChopperMagazine_TopRound.glb"),
                    palm_r=(0.040, -0.0155, -0.085), palm_l=(0.315, 0.0, -0.0615),
                    hip=_game_view("chopper", ((0.15, -0.09, -0.24), (0.05, 0.28, -0.35))),
                    aim=((0.0, -0.0555, -0.16 + 0.0235), (0, 0, 0)), size=(0.502, 0.065, 0.292)),
    "nine": dict(glb="SK_Nine.glb", parts=("SM_Weapon_NineMagazine.glb", "SM_Weapon_NineMagazine_TopRound.glb"),
                 palm_r=(0.014, -0.0146, -0.078), palm_l=(0.030, 0.0146, -0.090),
                 hip=_game_view("nine", ((0.105, -0.056, -0.36), (0.07, 0.11, -0.18))),
                 aim=((0.0, -0.0185, -0.37 + 0.0125), (0, 0, 0)), size=(0.234, 0.031, 0.153)),
}
FOV_V = 54.0
EYE_DROP = 0.0058           # the recipe's eye: the head joint lowered 0.58 cm onto the sight line


def view_rotation(pitch, yaw, roll):
    """three.js Euler(pitch, yaw, roll, 'YXZ') as a matrix: Ry(yaw) @ Rx(pitch) @ Rz(roll)."""
    return Matrix.Rotation(yaw, 4, "Y") @ Matrix.Rotation(pitch, 4, "X") @ Matrix.Rotation(roll, 4, "Z")


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
        for f in (g["glb"],) + tuple(g.get("parts", ())):        # the gun and its magazine (gun space)
            if os.path.exists(os.path.join(paths.glb, f)):
                bpy.ops.import_scene.gltf(filepath=os.path.join(paths.glb, f), bone_heuristic="BLENDER",
                                          guess_original_bind_pose=False, disable_bone_shape=True)
        new = [o for o in bpy.data.objects if o not in before]
        root = bpy.data.objects.new("Gun_" + name, None)
        col.objects.link(root)
        for o in new:
            for c in o.users_collection:
                c.objects.unlink(o)
            col.objects.link(o)
            if o.parent is None:
                o.parent = root
            if o.type == "MESH":
                for sl in o.material_slots:
                    if sl.material is not None:
                        texture_gun_material(sl.material)
            if o.type == "MESH" and "trigger" in o.vertex_groups and o.parent is not None:
                # the trigger's face (gun space): the front of the vertices the trigger bone carries
                gi = o.vertex_groups["trigger"].index
                tv = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices
                               if any(e.group == gi and e.weight > 0.5 for e in v.groups)])
                if len(tv):
                    lo = tv[:, 2] < np.percentile(tv[:, 2], 60)
                    face = tv[lo] if lo.any() else tv
                    g["trigger_pad"] = (float(face[:, 0].max()), 0.0, float(np.median(face[:, 2])))
            if o.type == "ARMATURE":                        # the sockets as the file has them
                for k, b in (("palm_r", "Palm_R"), ("palm_l", "Palm_L")):
                    if b in o.data.bones:
                        g[k] = tuple(round(v, 5) for v in (o.matrix_world @ o.data.bones[b].head_local))
        return root, True
    from mi import geo
    L, W, H = g["size"]
    box = geo.box((L, W, H), bevel=0.004, base=False, name="Gun_" + name)
    geo.transform(box, loc=(L / 2 - 0.02, 0, -H * 0.25))
    col.objects.link(box) if box.name not in col.objects else None
    return box, False


def texture_gun_material(m):
    """Wire a gun material to its baked set (art/out/textures/<set>/set.json) as Unreal reads it: BC, ORM (G
    roughness, B metallic), N. Materials without a set keep the file's factors."""
    key = m.name.split(".")[0]
    sn = key[2:] if key.startswith("M_") else key
    d = paths.texture_set(sn)
    if m.get("mi_wired") or not os.path.exists(os.path.join(d, "set.json")):
        return
    files = json.load(open(os.path.join(d, "set.json"))).get("files", {})
    if "BC" not in files:
        return
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(p.outputs["BSDF"], out.inputs["Surface"])

    def img(k, srgb):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(d, files[k]), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
        return n
    nt.links.new(img("BC", True).outputs["Color"], p.inputs["Base Color"])
    if "ORM" in files:
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(img("ORM", False).outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], p.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], p.inputs["Metallic"])
    if "N" in files:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(img("N", False).outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    m["mi_wired"] = True


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
    V = Matrix.Translation((px, py, pz)) @ view_rotation(rx, ry, rz) @ C
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


def eye_camera(arm, col=None, ahead=0.0, up=-EYE_DROP, pitch=0.0):
    """First-person camera at the recipe's eye (the head joint lowered 0.58 cm; review round 3: was 11 cm ahead and
    7.5 cm above it), level, looking along -Y (the mannequin's front)."""
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
    return cam.matrix_world @ Matrix.Translation((px, py, pz)) @ view_rotation(rx, ry, rz) @ C


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




# ------------------------------------------------------------------------------------------------ contact solve
#
# Review round 3 (the hands read as mittens: fingers curled in the air with gaps, the support fingers open beside
# the CHOPPER's handguard): each finger is closed joint by joint onto the gun's surface (a BVH of the posed gun),
# proximal joint first, until one of its phalanges comes within CONTACT_GAP of the surface, and then backed off to
# that gap. Phalanges are capsules on the finger chain with the hand's own radii (characters.ArmRig.chain), the
# palm's surface point is seated on the gun's Palm_R / Palm_L socket. The support hand on the NINE also closes onto
# the firing hand's fingers.

CONTACT_GAP = 0.0015        # skin left between a phalanx and the gun (m): 1-2 mm, the pads compress onto it
STEP_DEG = 2.0


def gun_meshes():
    out = []
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or o.hide_render:
            continue
        r = o
        while r.parent is not None:
            r = r.parent
        if r.name.startswith("Gun_"):
            out.append(o)
    return out


def world_bvh(objs):
    """One BVH of the evaluated, world-space triangles of objs (None when empty)."""
    dg = bpy.context.evaluated_depsgraph_get()
    V, T = [], []
    n = 0
    for o in objs:
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        me.calc_loop_triangles()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        Mn = np.array(e.matrix_world)
        co = co.reshape(-1, 3) @ Mn[:3, :3].T + Mn[:3, 3]
        tr = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
        me.loop_triangles.foreach_get("vertices", tr)
        V.append(co)
        T.append(tr.reshape(-1, 3) + n)
        n += len(co)
        e.to_mesh_clear()
    if not V:
        return None
    V = np.vstack(V)
    T = np.vstack(T)
    return BVHTree.FromPolygons([tuple(v) for v in V], [tuple(t) for t in T], all_triangles=True)


class Obstacles:
    """Clearance of spheres against BVHs and capsules (m)."""

    def __init__(self, bvhs=(), capsules=()):
        self.bvhs = [b for b in bvhs if b is not None]
        self.capsules = list(capsules)

    def clear(self, p, r):
        p = Vector(p)
        best = 1e9
        for b in self.bvhs:
            # unsigned: the guns are not closed shells everywhere (internal parts, open faces), so the nearest
            # face's normal cannot say inside from outside; fingers start outside and close in small steps
            loc, _nrm, _i, d = b.find_nearest(p, 0.25)
            if loc is None:
                continue
            best = min(best, d - r)
        for a, b, ra, rb in self.capsules:
            ab = b - a
            t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
            best = min(best, (p - (a + ab * t)).length - (ra + (rb - ra) * t) - r)
        return best


def _armature_mods(arm, on):
    for o in arm.children:
        for md in getattr(o, "modifiers", []):
            if md.type == "ARMATURE":
                md.show_viewport = on


def phalanx(arm, side, R, f, k):
    """Posed (a, b, ra, rb) of phalanx k (0..2) of finger f."""
    c = R.chain[f]
    bone = "%s_%02d_%s" % (f, k + 1, side)
    a = bone_world(arm, bone, c["P"][k])
    b = bone_world(arm, bone, c["P"][k + 1])
    return a, b, float(c["r"][k]), float(c["r"][k + 1])


def finger_capsules(arm, side, R, fingers=("index", "middle", "ring", "pinky", "thumb")):
    return [phalanx(arm, side, R, f, k) for f in fingers for k in range(3)]


def seg_clear(obst, a, b, ra, rb, n=6, t0=0.0):
    best = 1e9
    for i in range(n + 1):
        t = t0 + (1 - t0) * i / n
        best = min(best, obst.clear(a + (b - a) * t, ra + (rb - ra) * t))
    return best


def _chain_clear(arm, side, R, f, ks, obst):
    """Clearance of the phalanges ks; the first one's root (its knuckle, pressed onto the gun with the palm by
    design) is left out, so a joint is stopped by its phalanx's body or tip."""
    return min(seg_clear(obst, *phalanx(arm, side, R, f, k), t0=0.45 if i == 0 else 0.0) for i, k in enumerate(ks))


def _hinge(arm, side, R, f):
    fwd, lat, dors = hand_axes(arm, side, R)
    if f == "thumb":
        return Vector(fwd), Vector(-dors)
    return Vector(lat), Vector(-dors)


def close_onto(arm, side, R, f, obst, max_deg=(85, 105, 75), start=(0, 0, 0), joints=(0, 1, 2), gap=CONTACT_GAP):
    """Close finger f joint by joint (proximal first) until a phalanx at or beyond the joint is `gap` from the
    obstacles; returns {joint: (angle deg, final clearance m or None when it never touched)}."""
    out = {}
    for k, a0 in zip(range(3), start):
        if a0:
            across, palm = _hinge(arm, side, R, f)
            _curl(arm, "%s_%02d_%s" % (f, k + 1, side), math.radians(a0), across, palm)
    for k in joints:
        bone = "%s_%02d_%s" % (f, k + 1, side)
        ks = range(k, 3)
        c0 = _chain_clear(arm, side, R, f, ks, obst)
        ang, step, touched = 0.0, STEP_DEG, None
        if c0 < gap:
            # already through a part (a straight finger across the trigger guard): close until it is clear, or
            # leave the joint where it was if closing never clears it
            across, palm = _hinge(arm, side, R, f)
            while ang + step <= max_deg[k] - start[k] and c0 < gap:
                _curl(arm, bone, math.radians(step), across, palm)
                ang += step
                c0 = _chain_clear(arm, side, R, f, ks, obst)
            if c0 < gap:
                _curl(arm, bone, -math.radians(ang), across, palm)
                out[k] = (start[k], round(c0, 4))
                continue
        while ang + step <= max_deg[k] - start[k] + 1e-6:
            across, palm = _hinge(arm, side, R, f)
            _curl(arm, bone, math.radians(step), across, palm)
            c = _chain_clear(arm, side, R, f, ks, obst)
            if c < gap:
                _curl(arm, bone, -math.radians(step), across, palm)
                if step > 0.6:
                    step = 0.5
                    continue
                touched = _chain_clear(arm, side, R, f, ks, obst)
                break
            ang += step
        out[k] = (round(start[k] + ang, 1), None if touched is None else round(touched, 4))
    return out


def trigger_finger(arm, R, gun, gun_M, name):
    """The firing index: the three joints searched on a grid for the pose whose end pad lands on the trigger's
    face (GUNS[name]['trigger_pad'], from the file) with no phalanx through the gun (2 mm of skin pressed at most)."""
    tp = GUNS[name].get("trigger_pad")
    if not tp:
        return close_onto(arm, "r", R, "index", gun, start=(INDEX_MCP[name], 0, 0), joints=(1, 2))
    T = gun_M @ Vector(tp)
    across, palm = _hinge(arm, "r", R, "index")
    best = None
    for mcp in range(-5, 46, 5):
        for pip in range(0, 91, 10):
            for dip in range(0, 61, 15):
                reset_finger(arm, "r", "index")
                for k, ang in enumerate((mcp, pip, dip)):
                    if ang:
                        _curl(arm, "index_%02d_r" % (k + 1), math.radians(ang), across, palm)
                c = _chain_clear(arm, "r", R, "index", (0, 1, 2), gun)
                a_, b_, ra, rb = phalanx(arm, "r", R, "index", 2)
                pad = a_ + (b_ - a_) * 0.55 + _pad_dir(arm, R) * rb
                d = (pad - T).length
                score = d + max(-0.002 - c, 0) * 10
                if best is None or score < best[0]:
                    best = (score, (mcp, pip, dip), d, c)
    reset_finger(arm, "r", "index")
    for k, ang in enumerate(best[1]):
        if ang:
            _curl(arm, "index_%02d_r" % (k + 1), math.radians(ang), across, palm)
    return {"angles": best[1], "pad_mm": round(best[2] * 1000, 1), "clear_mm": round(best[3] * 1000, 1),
            "trigger_pad": [round(v, 4) for v in tp]}


THUMB_AIM = {   # gun space: where each thumb tip goes (firing: round the grip's left side; support: along the gun)
    ("chopper", "r"): (0.058, 0.030, -0.052), ("chopper", "l"): (0.400, 0.032, -0.030),
    ("nine", "r"): (0.055, 0.028, -0.018), ("nine", "l"): (0.080, 0.030, -0.032)}


def aim_thumb(arm, side, R, gun_M, name, obst):
    """The thumb on a grid: its first bone swung about the hand's forward and back axes, the other two closed;
    keep the pose whose tip lands nearest THUMB_AIM with no part of the thumb through the gun (or the other
    hand: 1.5 mm of pressed skin at most)."""
    tgt = gun_M @ Vector(THUMB_AIM[(name, side)])
    fwd, lat, dors = (Vector(v) for v in hand_axes(arm, side, R))
    across, palm = _hinge(arm, side, R, "thumb")
    pb = arm.pose.bones["thumb_01_" + side]
    best = None

    def pose(a1, a2, c2, c3):
        reset_finger(arm, side, "thumb")
        head = (arm.matrix_world @ pb.matrix).to_translation()
        M = arm.matrix_world @ pb.matrix
        Rm = (Matrix.Translation(head) @ Matrix.Rotation(math.radians(a2), 4, dors)
              @ Matrix.Rotation(math.radians(a1), 4, fwd) @ Matrix.Translation(-head))
        pb.matrix = arm.matrix_world.inverted() @ Rm @ M
        bpy.context.view_layer.update()
        if c2:
            _curl(arm, "thumb_02_" + side, math.radians(c2), across, palm)
        if c3:
            _curl(arm, "thumb_03_" + side, math.radians(c3), across, palm)
    sgn = 1.0 if side == "r" else -1.0
    for a1 in range(-30, 91, 10):
        for a2 in range(-40, 41, 10):
            for c2 in (0, 15, 30, 45):
                for c3 in (0, 20, 40):
                    pose(a1 * sgn, a2, c2, c3)
                    c = _chain_clear(arm, side, R, "thumb", (0, 1, 2), obst)
                    tip = bone_world(arm, "thumb_03_" + side, R.chain["thumb"]["P"][3])
                    d = (tip - tgt).length
                    score = d + max(-0.0015 - c, 0) * 20
                    if best is None or score < best[0]:
                        best = (score, (a1 * sgn, a2, c2, c3), d, c)
    pose(*best[1])
    return {"angles": best[1], "tip_mm": round(best[2] * 1000, 1), "clear_mm": round(best[3] * 1000, 1)}


def _pad_dir(arm, R):
    """The index end phalanx's palmar direction (posed)."""
    b = arm.data.bones["index_03_r"]
    Rm = (arm.matrix_world @ arm.pose.bones["index_03_r"].matrix @ b.matrix_local.inverted()).to_3x3()
    return (Rm @ Vector(-R.chain["index"]["dors"])).normalized()


def reset_finger(arm, side, f):
    for k in ("01", "02", "03"):
        arm.pose.bones["%s_%s_%s" % (f, k, side)].matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def adduct(arm, side, R, keep=0.35):
    """Close the gaps between the fingers (the mannequin's rest hand is splayed): each finger's first bone turns
    about the back-of-hand axis toward the middle finger's direction, keeping `keep` of its splay."""
    fwd, lat, dors = (Vector(v) for v in hand_axes(arm, side, R))
    mid = (bone_world(arm, "middle_02_" + side, R.chain["middle"]["P"][1]) -
           bone_world(arm, "middle_01_" + side, R.chain["middle"]["P"][0]))
    mid = (mid - dors * mid.dot(dors)).normalized()
    for f in ("index", "ring", "pinky"):
        pb = arm.pose.bones["%s_01_%s" % (f, side)]
        head = (arm.matrix_world @ pb.matrix).to_translation()
        d = bone_world(arm, "%s_02_%s" % (f, side), R.chain[f]["P"][1]) - head
        d = (d - dors * d.dot(dors)).normalized()
        ang = math.atan2(d.cross(mid).dot(dors), d.dot(mid)) * (1 - keep)
        M = arm.matrix_world @ pb.matrix
        Rm = Matrix.Translation(head) @ Matrix.Rotation(ang, 4, dors) @ Matrix.Translation(-head)
        pb.matrix = arm.matrix_world.inverted() @ Rm @ M
        bpy.context.view_layer.update()


def close_coupled(arm, side, R, f, obst, max_deg=(85, 100, 70), ratio=(1.0, 1.15, 0.8), steps=48, gap=CONTACT_GAP):
    """Close finger f with its three joints together (ratio), sweeping from open to max_deg: stop where the
    finger first comes to `gap` from the obstacles after having been clear (a finger that starts across a thin
    part, the trigger guard, sweeps through it first; one that never clears keeps the clearest pose); then the
    middle and end joints close on by themselves until they touch. Returns the angles and clearances."""
    across, palm = _hinge(arm, side, R, f)
    bones = ["%s_%02d_%s" % (f, k + 1, side) for k in range(3)]
    full = [min(m, 120.0 * r) for m, r in zip(max_deg, ratio)]

    def pose(t):
        reset_finger(arm, side, f)
        for b, a in zip(bones, full):
            if a * t:
                _curl(arm, b, math.radians(a * t), across, palm)
        return _chain_clear(arm, side, R, f, (0, 1, 2), obst)
    cs = [pose(i / steps) for i in range(steps + 1)]
    t_stop, was_clear = None, False
    for i, c in enumerate(cs):
        if c >= gap:
            was_clear = True
        elif was_clear:
            t_stop = (i - 1) / steps
            break
    if t_stop is None:
        t_stop = 1.0 if was_clear else int(np.argmax(cs)) / steps
    pose(t_stop)
    res = {"t": round(t_stop, 3), "angles": [round(a * t_stop, 1) for a in full]}
    more = close_onto(arm, side, R, f, obst, max_deg=tuple(m for m in max_deg), joints=(1, 2),
                      start=(0, 0, 0))
    res["more"] = more
    res["clear_mm"] = round(_chain_clear(arm, side, R, f, (0, 1, 2), obst) * 1000, 1)
    return res


def palm_point(arm, side, R):
    return bone_world(arm, "hand_" + side, palm_rest(R))


def hand_frame_on_grip(G, side, sgn, rake_deg=17.0, roll_deg=0.0):
    """(fwd, lat, dors) of a hand on a pistol grip: fingers forward round the grip's front, little finger down the
    grip (raked back), back of the hand away from the grip (right hand: to the gun's right)."""
    X, Y, Z = (G @ Vector(v) for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    rake = math.radians(rake_deg)
    down = (-Z * math.cos(rake) - X * math.sin(rake)).normalized()
    fwd = (X - down * X.dot(down)).normalized()
    if roll_deg:
        fwd = Matrix.Rotation(math.radians(roll_deg), 3, down) @ fwd
    lat = down
    dors = (fwd.cross(lat) * sgn).normalized()
    return fwd, lat, dors


def _sgn(R):
    return 1.0 if Vector(R.dors).dot(Vector(R.fwd).cross(Vector(R.lat))) > 0 else -1.0


def seat_palm(arm, side, R, target, axes, pole, obst, out_dir, depth=0.0012, max_push=0.03):
    """IK the hand so its palm point sits `depth` into the surface at `target` (flesh pressed on the gun), then
    push it out along out_dir while the palm's skin would sit inside the obstacles."""
    t = Vector(target) - Vector(out_dir) * depth
    E, Wt = ik_arm(arm, side, R, t, axes, pole)
    pushed = 0.0
    if obst is not None:
        for _ in range(30):
            pr = palm_point(arm, side, R)
            if obst.clear(pr, 0.0) >= -depth - 0.0005 or pushed >= max_push:
                break
            pushed += 0.002
            ik_arm(arm, side, R, t + Vector(out_dir) * pushed, axes, pole)
    return pushed


def wrist_bend_deg(arm, side, R):
    """Angle between the posed forearm axis and the hand's direction, less the rest pose's angle (deg)."""
    E = bone_world(arm, "lowerarm_" + side, R.E)
    W = bone_world(arm, "hand_" + side, R.W)
    fwd = Vector(hand_axes(arm, side, R)[0])
    af = (W - E).normalized()
    rest = math.degrees(math.acos(max(-1, min(1, float(np.dot(R.af, R.fwd))))))
    return round(math.degrees(af.angle(fwd)) - rest, 1)


POLE_R = Vector((0.3, 0.6, -1))
POLE_L = {"chopper": Vector((0.1, 0.2, -1)), "nine": Vector((-0.4, 0.4, -1))}


def support_axes(G, name, pose, sl, turn=0.0):
    X, Y, Z = (G @ Vector(v) for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    if name == "chopper":
        fwd_l = (-Y * 0.80 + X * (0.50 if pose == "hip" else 0.40) + Z * 0.10).normalized()
        if turn:                                    # the hand turned in the plane of the palm (about the up axis)
            fwd_l = Matrix.Rotation(math.radians(turn), 3, Z) @ fwd_l
        dors_l = -Z
        lat_l = (dors_l.cross(fwd_l) * sl).normalized()
        dors_l = (fwd_l.cross(lat_l) * sl).normalized()
        return fwd_l, lat_l, dors_l
    return hand_frame_on_grip(G, "l", sl, rake_deg=12.0 + turn)


INDEX_MCP = {"chopper": 10.0, "nine": 8.0}      # trigger finger: first joint (deg), then closed onto the trigger
GRIP_RAKE = {"chopper": 0.0, "nine": 16.0}      # the hand frame's tilt on the grip (deg): the CHOPPER's long grip
                                                # takes the wrist-knuckle line level, the NINE's short one its rake
GRIP_BACK = {"chopper": 0.016, "nine": 0.012}   # the firing palm's centre behind the grip socket: knuckles at the front strap
GRIP_DOWN = {"chopper": 0.009, "nine": 0.006}   # and below it: the index at the trigger, the middle finger under the guard
HANDGUARD_EDGE_Y = -0.026     # gun space: the CHOPPER handguard's right face is at y -0.0226
SUPPORT_OUT = {"chopper": (0.0, 0.008, 0.0), "nine": (0.0, 0.0, 0.016)}   # gun space: the support palm toward the near side


def place_rig(arm, Rr, Rl, pr_fn, pl, ax_r_fn, ax_l_fn, name):
    """Review round 3 (wrists bent sharply, the forearm coming straight up from below the frame): first-person
    arms are placed for the camera, so slide the rig (shoulders) forward or back and up or down, turn the firing
    hand in the plane of its palm on the grip (the grip lies diagonally across a real palm), protract the support
    shoulder on a long gun, and keep the placement where both wrists bend least while both palms are reached.
    pr_fn(axes) and ax_r_fn(rake) give the firing palm's target and frame, ax_l_fn(turn) the support frame."""
    fwd = Vector((0, -1, 0))
    best = None
    base = arm.location.copy()
    rk = GRIP_RAKE[name]
    for rake in (rk - 6, rk, rk + 6):
        ax_r = ax_r_fn(rake)
        pr = pr_fn(ax_r)
        for dz in (-0.04, -0.02, 0.0, 0.02, 0.04, 0.06):
            for k in range(-16, 13, 2):
                d = k * 0.01
                arm.location = base + fwd * d + Vector((0, 0, dz))
                char_clav(arm)
                bpy.context.view_layer.update()
                ik_arm(arm, "r", Rr, pr, ax_r, POLE_R)
                miss = (palm_point(arm, "r", Rr) - Vector(pr)).length
                wr = wrist_bend_deg(arm, "r", Rr)
                if name == "chopper":
                    protract(arm, "l", pl, Rl)
                ik_arm(arm, "l", Rl, pl, ax_l_fn(0.0), POLE_L[name])
                miss += (palm_point(arm, "l", Rl) - Vector(pl)).length
                wl = wrist_bend_deg(arm, "l", Rl)
                # a firing wrist on a pistol grip is extended 20-30 deg in a natural hold: bends count above that
                score = (max(wr - 25.0, 0) ** 2 + 0.6 * max(wl - 15.0, 0) ** 2) / 100.0 + (miss * 1000.0) ** 2 \
                    + abs(d) * 20 + abs(dz) * 30 + abs(rake - rk) * 0.3
                if best is None or score < best[0]:
                    best = (score, d, dz, rake, wr, wl, miss)
    _s, d, dz, rake, wr, wl, miss = best
    arm.location = base + fwd * d + Vector((0, 0, dz))
    char_clav(arm)
    bpy.context.view_layer.update()
    deg = protract(arm, "l", pl, Rl) if name == "chopper" else 0
    # the support hand's own turn, with the shoulders where they are
    tb = min(range(-20, 11, 5), key=lambda t: _ik_wrist(arm, Rl, pl, ax_l_fn(t), POLE_L[name]) + abs(t) * 0.8)
    return {"slide_m": round(d, 3), "drop_m": round(dz, 3), "rake_r_deg": rake, "turn_l_deg": tb, "protract_deg": deg,
            "wrist_r": wr, "wrist_l": _ik_wrist(arm, Rl, pl, ax_l_fn(tb), POLE_L[name]),
            "palm_miss_mm": round(miss * 1000, 1)}


def _ik_wrist(arm, Rl, pl, ax, pole):
    ik_arm(arm, "l", Rl, pl, ax, pole)
    if (palm_point(arm, "l", Rl) - Vector(pl)).length > 0.003:
        return 999.0
    return wrist_bend_deg(arm, "l", Rl)


def char_clav(arm):
    for s in ("l", "r"):
        for b in ("clavicle_", "upperarm_", "lowerarm_", "hand_"):
            arm.pose.bones[b + s].matrix_basis = Matrix.Identity(4)


def hold(arm, gun_M, name, Rr, Rl, pose="hip", gun_objs=None, log=None):
    """Both arms onto the gun at gun_M and every finger closed onto it. Returns a report (contacts per finger,
    palm push-out, wrist bends)."""
    G = gun_M.to_3x3()
    X, Y, Z = (G @ Vector(v) for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    g = GUNS[name]
    sr, sl = _sgn(Rr), _sgn(Rl)
    gun = Obstacles([world_bvh(gun_objs if gun_objs is not None else gun_meshes())])
    rep = {"gun": name, "pose": pose}
    pr = gun_M @ Vector(g["palm_r"])
    pl = gun_M @ Vector(g["palm_l"])
    _armature_mods(arm, False)
    try:
        reset_fingers(arm, "r")
        reset_fingers(arm, "l")
        # firing hand: palm on the grip's right face (the socket), little finger down the raked grip
        pl = pl + G @ Vector(SUPPORT_OUT[name])
        rep["rig"] = place_rig(arm, Rr, Rl, lambda ax: pr - ax[0] * GRIP_BACK[name] + ax[1] * GRIP_DOWN[name], pl,
                               lambda rk: hand_frame_on_grip(G, "r", sr, rake_deg=rk),
                               lambda t: support_axes(G, name, pose, sl, t), name)
        ax_r = hand_frame_on_grip(G, "r", sr, rake_deg=rep["rig"]["rake_r_deg"])
        ax_l = support_axes(G, name, pose, sl, rep["rig"]["turn_l_deg"])
        rep["push_r_m"] = seat_palm(arm, "r", Rr, pr - ax_r[0] * GRIP_BACK[name] + ax_r[1] * GRIP_DOWN[name], ax_r, POLE_R,
                                    gun, -Y)
        adduct(arm, "r", Rr)
        f_r = {}
        for f in ("middle", "ring", "pinky"):
            f_r[f] = close_coupled(arm, "r", Rr, f, gun)
        # trigger finger: through the guard onto the trigger's face (its pad), first joint set, the others closed
        f_r["index"] = trigger_finger(arm, Rr, gun, gun_M, name)
        f_r["thumb"] = aim_thumb(arm, "r", Rr, gun_M, name, gun)
        rep["fingers_r"] = f_r
        bpy.context.view_layer.update()
        if name == "chopper":
            # support hand under the 46 mm handguard: palm up, fingers up its right face, thumb along its left
            rep["push_l_m"] = seat_palm(arm, "l", Rl, pl, ax_l, POLE_L["chopper"], gun, -Z)
            # the knuckles at the handguard's lower right edge, so the fingers can wrap up its right face
            Gi = gun_M.inverted()
            for _ in range(3):
                mcp = Gi @ (arm.matrix_world @ arm.pose.bones["middle_01_l"].head)
                dy = HANDGUARD_EDGE_Y - mcp.y
                if abs(dy) < 0.002:
                    break
                pl = pl + Y * dy
                seat_palm(arm, "l", Rl, pl, ax_l, POLE_L["chopper"], gun, -Z)
            rep["support_palm_gun"] = [round(v, 4) for v in Gi @ pl]
            obst_l = gun
            adduct(arm, "l", Rl)
            f_l = {f: close_coupled(arm, "l", Rl, f, obst_l, max_deg=(80, 100, 70)) for f in ("index", "middle", "ring", "pinky")}
            f_l["thumb"] = aim_thumb(arm, "l", Rl, gun_M, name, obst_l)
        else:
            # two hands on the NINE: support palm on the grip's left face (its socket), fingers round the front
            # over the firing hand's, thumb forward along the frame under the slide
            obst_l = Obstacles(gun.bvhs, finger_capsules(arm, "r", Rr, ("index", "middle", "ring", "pinky")))
            rep["push_l_m"] = seat_palm(arm, "l", Rl, pl, ax_l, POLE_L["nine"], obst_l, Y)
            adduct(arm, "l", Rl)
            f_l = {f: close_coupled(arm, "l", Rl, f, obst_l, max_deg=(80, 100, 70)) for f in ("index", "middle", "ring", "pinky")}
            f_l["thumb"] = aim_thumb(arm, "l", Rl, gun_M, name, Obstacles(gun.bvhs, finger_capsules(arm, "r", Rr)))
        rep["fingers_l"] = f_l
        rep["wrist_bend_deg"] = {"r": wrist_bend_deg(arm, "r", Rr), "l": wrist_bend_deg(arm, "l", Rl)}
        rep["rig_slide_m"] = round(arm.location.length, 4)
    finally:
        _armature_mods(arm, True)
        bpy.context.view_layer.update()
    if log:
        log("  hold %s %s: %s" % (name, pose, json.dumps(rep)))
    return rep


def reset_fingers(arm, side):
    for f in ("index", "middle", "ring", "pinky", "thumb"):
        for k in ("01", "02", "03"):
            arm.pose.bones["%s_%s_%s" % (f, k, side)].matrix_basis = Matrix.Identity(4)
    for f in ("index", "middle", "ring", "pinky"):
        arm.pose.bones["%s_metacarpal_%s" % (f, side)].matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def grip(arm, name, Rr, Rl):
    """Kept for the gloved variant's previews: hold() now closes the hands by contact."""
    reset_fingers(arm, "r")
    reset_fingers(arm, "l")
    close_fingers(arm, "r", Rr, 0.86, ("middle", "ring", "pinky"), thumb=0.85)
    close_fingers(arm, "r", Rr, 1.0, ("index",), angles=(38, 62, 30))
    if name == "chopper":
        close_fingers(arm, "l", Rl, 0.80, angles=(55, 70, 40))
        close_fingers(arm, "l", Rl, 0.6, (), thumb=0.6)
    else:
        close_fingers(arm, "l", Rl, 0.82, thumb=0.55)


def fp_scene(arm, Rr, Rl, name, pose, col, log=None):
    """The first-person test scene the previews and the export gate share: rest arms, the recipe camera, the gun at
    the game's view pose, both hands solved onto it. Returns (camera, gun root, gun matrix, report)."""
    char.rest_pose(arm)
    arm.location = (0, 0, 0)
    g, _real = load_gun(name, col)
    cam = eye_camera(arm, col)
    M = gun_from_camera(cam, name, pose)
    g.matrix_world = M
    bpy.context.view_layer.update()
    rep = hold(arm, M, name, Rr, Rl, pose=pose, log=log)
    return cam, g, M, rep
