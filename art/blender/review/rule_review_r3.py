"""Independent art-direction review, round 3, of the main character (Rule): the first-person view the player sees
for the whole game, the hands, the tattoos, the face against the reference photo and the full body.

Reads only exports: SK_RuleArms.glb (RuleArms_Skin wired as Unreal reads it: BC, N, ORM G roughness / B metallic,
plus a skin subsurface stand-in for the Subsurface Profile), SM_Character_RuleBracelet.glb on its socket, SK_Rule.glb,
and the guns SK_Chopper / SK_Nine with their magazines from GUNS_DIR (default art/out; the review used a snapshot
because the guns were being re-exported). Loaders and the hold solver are reused from rule_review.py and
assets/_characters_pose.py without changing them.

First person follows the game data: camera on the recipe's eye (docs/unreal/ANIMATION.md section 9: the head joint
lowered 0.58 cm), 54 deg vertical field of view, 1920 x 1080; the gun at the web viewmodel pose in view space
(config.json weapons.<gun>.views[0] for the hip, presentation.json sightRear / relief for the aimed pose), Euler
order YXZ as gunPose builds it. Lights: render.rig_day at the design sun, or the same sky in the open shade under
an El deck (+1 stop, as the README says).

    python art/blender/review/rule_review_r3.py --shot <name> [--samples 64]
    python art/blender/review/rule_review_r3.py --list

Outputs art/blender/review/sheets/rule_r3/<shot>.jpg (not committed). The face and tattoo shots are side by side with
the private photo: they are written to art/out/review/rule_r3/ only.
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
from mathutils import Matrix, Vector  # noqa: E402

from mi import char, render  # noqa: E402
import rule_review as rr  # noqa: E402
import weapons_review as wr  # noqa: E402

OUT = os.path.join(HERE, "sheets", "rule_r3")
PRIVATE = os.path.join(ROOT, "art", "out", "review", "rule_r3")
GUNS_DIR = os.environ.get("GUNS_DIR", os.path.join(ROOT, "art", "out"))
PHOTO = rr.PHOTO
FP_RES = (1920, 1080)
FOV_V = 54.0
EYE_DROP = 0.0058           # recipe: the head joint lowered 0.58 cm onto the sight line

GAME = {
    # config.json weapons.<gun>.views[0] (x, y, z, pitch, yaw, roll); presentation.json sightRear, relief
    "chopper": dict(hip=(0.15, -0.09, -0.24, 0.05, 0.28, -0.35), sight=(0, 0.0555, -0.0235), relief=0.16,
                    files=["SK_Chopper", "SM_Weapon_ChopperMagazine", "SM_Weapon_ChopperMagazine_TopRound"]),
    "nine": dict(hip=(0.105, -0.056, -0.36, 0.07, 0.11, -0.18), sight=(0, 0.0185, -0.0125), relief=0.37,
                 files=["SK_Nine", "SM_Weapon_NineMagazine", "SM_Weapon_NineMagazine_TopRound"]),
}

SHOTS = ["fp_chopper_hip_day", "fp_chopper_hip_shade", "fp_chopper_aim_shade", "fp_nine_hip_day",
         "fp_nine_hip_shade", "fp_nine_aim_day", "grip_r_chopper", "hands_back_palm", "tattoos_photo",
         "face_1m", "face_3m", "body_poses"]

LOG = {}


# ---------------------------------------------------------------------------------------------------- loading

def load_gun(name, col):
    """The gun and its magazines under one root empty (gun space: X forward, Y left, Z up), textures wired."""
    wr.TEX = os.path.join(GUNS_DIR, "textures")
    root = bpy.data.objects.new("Gun_" + name, None)
    col.objects.link(root)
    objs = []
    for f in GAME[name]["files"]:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(GUNS_DIR, "glb", f + ".glb"), bone_heuristic="BLENDER",
                                  guess_original_bind_pose=False, disable_bone_shape=True)
        objs += [o for o in bpy.data.objects if o not in before]
    done = set()
    for o in objs:
        if o.parent is None:
            o.parent = root
        if o.type != "MESH":
            continue
        for s in o.material_slots:
            m = s.material
            key = m.name.split(".")[0]
            sn = key[2:] if key.startswith("M_") else key
            if m.name not in done and os.path.exists(os.path.join(wr.TEX, sn, "set.json")):
                wr.texture_material(m, sn)
                done.add(m.name)
    return root, objs


def view_pose(name, pose):
    g = GAME[name]
    if pose == "hip":
        x, y, z, p, yw, r = g["hip"]
    else:   # viewmodel.js adsPose: (-sightRear.x, -sightRear.y, -relief - sightRear.z), no rotation
        sx, sy, sz = g["sight"]
        x, y, z, p, yw, r = -sx, -sy, -g["relief"] - sz, 0.0, 0.0, 0.0
    C = Matrix(((0, -1, 0, 0), (0, 0, 1, 0), (-1, 0, 0, 0), (0, 0, 0, 1)))   # Blender gun axes -> three.js gun axes
    E = Matrix.Rotation(yw, 4, "Y") @ Matrix.Rotation(p, 4, "X") @ Matrix.Rotation(r, 4, "Z")   # Euler YXZ
    return Matrix.Translation((x, y, z)) @ E @ C


def recipe_camera(arm, col):
    bpy.context.view_layer.update()
    head = (arm.matrix_world @ arm.pose.bones["head"].matrix).to_translation()
    eye = head + Vector((0, 0, -EYE_DROP))
    cd = bpy.data.cameras.new("FP")
    cd.sensor_fit = "VERTICAL"
    cd.angle_y = math.radians(FOV_V)
    cd.clip_start = 0.01
    cam = bpy.data.objects.new("FP", cd)
    col.objects.link(cam)
    cam.matrix_world = (Matrix.Translation(eye) @ Matrix.Rotation(math.radians(180), 4, "Z")
                        @ Matrix.Rotation(math.radians(90), 4, "X"))
    bpy.context.scene.camera = cam
    return cam


def armed(name, pose, col):
    """Arms (rest), the recipe camera, the gun at the game's view pose, both arms solved onto it."""
    from assets import _characters_pose as PZ
    R, Rl = rr.arms_rig()
    arm, meshes = rr.load_arms()
    rr.bracelet(arm)
    char.rest_pose(arm)
    cam = recipe_camera(arm, col)
    root, objs = load_gun(name, col)
    M = cam.matrix_world @ view_pose(name, pose)
    root.matrix_world = M
    bpy.context.view_layer.update()
    PZ.hold(arm, M, name, R, Rl)
    LOG["rig_slide_m"] = round(float(arm.location.length), 4)
    return arm, meshes, cam, root, M, R, Rl


# ---------------------------------------------------------------------------------------------------- set

def _mat(name, rgb, rough):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def _box(name, lo, hi, mat):
    me = bpy.data.meshes.new(name)
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me.from_pydata(v, [], f)
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def street(shade):
    """Asphalt ground; under the El: a steel deck 5.2-6.0 m up across the sun's side, columns either side."""
    _box("Ground", (-60, -80, -0.05), (60, 80, 0.0), _mat("Asphalt", (0.075, 0.072, 0.068), 0.9))
    if shade:
        steel = _mat("ElSteel", (0.06, 0.058, 0.055), 0.7)
        _box("ElDeck", (-9, -80, 5.2), (9, 80, 6.0), steel)
        for y in range(-70, 71, 10):
            for x in (-6.5, 6.5):
                _box("ElCol", (x - 0.2, y - 0.2, 0), (x + 0.2, y + 0.2, 5.2), steel)
    render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING, stops=1.0 if shade else 0.0)


# ---------------------------------------------------------------------------------------------------- shots

def fp(shot, S):
    _, name, pose, light = shot.split("_")
    col = bpy.context.scene.collection
    arm, meshes, cam, root, M, R, Rl = armed(name, pose, col)
    render.setup(samples=S, res=FP_RES, threads=3)
    street(light == "shade")
    p = os.path.join(OUT, shot + ".jpg")
    render.render_jpeg(p, S, FP_RES, max_kb=900)
    return p


def grip_r(S):
    col = bpy.context.scene.collection
    arm, meshes, cam, root, M, R, Rl = armed("chopper", "hip", col)
    G = M.to_3x3()
    X, Y, Z = (G @ Vector(v) for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    t = M @ Vector((0.06, -0.015, -0.07))
    c = t - Y * 0.34 + X * 0.06 - Z * 0.05
    render.cam_look(tuple(c), tuple(t), lens=50)
    render.setup(samples=S, res=(1280, 720), threads=3)
    street(False)
    p = os.path.join(OUT, "grip_r_chopper.jpg")
    render.render_jpeg(p, S, (1280, 720), max_kb=500)
    return p


def _dup_rig(arm, meshes, extra=()):
    a2 = arm.copy()
    a2.data = arm.data.copy()
    bpy.context.scene.collection.objects.link(a2)
    for m in list(meshes) + list(extra):
        t = m.copy()
        t.data = m.data
        bpy.context.scene.collection.objects.link(t)
        t.parent = a2
        for md in t.modifiers:
            if md.type == "ARMATURE":
                md.object = a2
    return a2


def _orient(src_cols, dst_cols, sign):
    """Rotation taking an orthonormal source frame (columns a, b, c) onto a destination (a', b', c')."""
    S_ = Matrix([list(v) for v in src_cols]).transposed()
    a, c = dst_cols
    b = c.cross(a) * sign
    D = Matrix([list(a), list(b), list(c)]).transposed()
    return D @ S_.inverted()


def hands_sheet(S):
    """Each hand in its rest pose, back and palm, hanging fingers down, side by side: R back, R palm, L back, L palm."""
    R, Rl = rr.arms_rig()
    arm, meshes = rr.load_arms()
    j = rr.bracelet(arm)
    char.rest_pose(arm)
    rigs = [arm] + [_dup_rig(arm, meshes) for _ in range(3)]
    order = [("r", R, 1), ("r", R, -1), ("l", Rl, 1), ("l", Rl, -1)]
    xs = [-0.21, -0.07, 0.07, 0.21]
    for a, (side, RR, face), x in zip(rigs, order, xs):
        fwd, lat, dors = (Vector(v).normalized() for v in (RR.fwd, RR.lat, RR.dors))
        sign = 1.0 if dors.cross(fwd).dot(lat) > 0 else -1.0
        Rm = _orient((fwd, lat, dors), (Vector((0, 0, -1)), Vector((0, -face, 0))), sign)
        c = Vector(RR.W) + fwd * 0.07
        a.matrix_world = Matrix.Translation((x, 0, 1.0)) @ Rm.to_4x4() @ Matrix.Translation(-c)
    bpy.context.view_layer.update()
    render.cam_look((0, -0.95, 1.0), (0, 0, 1.0), lens=50)
    render.setup(samples=S, res=(1280, 720), threads=3)
    rr.studio(Vector((0, 0, 1.0)), key=(0.5, -0.9, 0.6), strength=0.8)
    p = os.path.join(OUT, "hands_back_palm.jpg")
    render.render_jpeg(p, S, (1280, 720), max_kb=500)
    return p


TATTOO_UV = {"a": ((0.737, 0.806), (0.639, 0.714)), "b": ((0.789, 0.842), (0.304, 0.360))}


def _tattoo_site(arm, meshes, box):
    """World centroid and mean normal (rest pose) of the skin faces whose UV centre lies in box."""
    (u0, u1), (v0, v1) = box
    pts, nrm = [], []
    for m in meshes:
        me = m.data
        uv = me.uv_layers.active.data
        for poly in me.polygons:
            u = sum(uv[li].uv[0] for li in poly.loop_indices) / poly.loop_total
            v = sum(uv[li].uv[1] for li in poly.loop_indices) / poly.loop_total
            if u0 <= u <= u1 and v0 <= v <= v1:
                pts.append(m.matrix_world @ poly.center)
                nrm.append((m.matrix_world.to_3x3() @ poly.normal))
    if not pts:
        return None, None
    c = sum(pts, Vector()) / len(pts)
    n = (sum(nrm, Vector()) / len(nrm)).normalized()
    return c, n


def tattoos(S):
    R, Rl = rr.arms_rig()
    arm, meshes = rr.load_arms()
    char.rest_pose(arm)
    bpy.context.view_layer.update()
    sites = {k: _tattoo_site(arm, meshes, b) for k, b in TATTOO_UV.items()}
    LOG["tattoo_sites"] = {k: (list(map(lambda f: round(f, 3), c)) if c else None) for k, (c, n) in sites.items()}
    a2 = _dup_rig(arm, meshes)
    zs = {"a": 0.075, "b": -0.075}
    for a, k in ((arm, "a"), (a2, "b")):
        c, n = sites[k]
        side = "r" if c.x < 0 else "l"
        RR = R if side == "r" else Rl
        ax = Vector(RR.af).normalized()
        n = (n - ax * n.dot(ax)).normalized()
        sign = 1.0
        Rm = _orient((ax, n.cross(ax), n), (Vector((1, 0, 0)), Vector((0, -1, 0))), sign)
        if Rm.determinant() < 0:
            Rm = _orient((ax, n.cross(ax), n), (Vector((1, 0, 0)), Vector((0, -1, 0))), -1.0)
        a.matrix_world = Matrix.Translation((0, 0, 1.0 + zs[k])) @ Rm.to_4x4() @ Matrix.Translation(-c)
        LOG["tattoo_side_" + k] = side
    bpy.context.view_layer.update()
    render.cam_look((0, -0.75, 1.0), (0, 0, 1.0), lens=50)
    render.setup(samples=S, res=(1280, 720), threads=3)
    rr.studio(Vector((0, 0, 1.0)), key=(0.3, -1.0, 0.45), strength=0.8)
    tmp = os.path.join(PRIVATE, "_tat.png")
    render.render_png(tmp, S, (1280, 720))
    p = os.path.join(PRIVATE, "tattoos_photo.jpg")
    _side_by_side(tmp, p)
    return p


def _side_by_side(tmp, p, crop_w=None):
    from PIL import Image
    sheet = Image.new("RGB", (1280, 720), (16, 16, 16))
    ph = Image.open(PHOTO).convert("RGB")
    ph = ph.resize((int(ph.width * 720 / ph.height), 720), Image.LANCZOS)
    sheet.paste(ph, (0, 0))
    r = Image.open(tmp).convert("RGB")
    w = 1280 - ph.width - 4
    x0 = (1280 - w) // 2
    sheet.paste(r.crop((x0, 0, x0 + w, 720)), (ph.width + 4, 0))
    render.save_jpeg(sheet, p, max_kb=500)
    os.remove(tmp)


def face(dist, S):
    arm, meshes = rr.load_body()
    char.rest_pose(arm)
    hb = arm.pose.bones["head"]
    piv = hb.head.copy()       # the photo: chin down
    hb.matrix = (Matrix.Translation(piv) @ Matrix.Rotation(math.radians(10), 4, "X") @ Matrix.Translation(-piv)) @ hb.matrix
    bpy.context.view_layer.update()
    h = rr.bone_pos(arm, "head")
    t = Vector((h.x, h.y - 0.03, h.z + 0.02))
    d = Vector((math.sin(math.radians(6)), -math.cos(math.radians(6)), 0))
    lens = 55
    if dist > 2:      # 3 m: frame the head and shoulders a little lower
        t = t + Vector((0, 0, -0.12))
    render.cam_look(tuple(t + d * dist + Vector((0, 0, 0.10))), tuple(t), lens=lens)
    render.setup(samples=S, res=(1280, 720), threads=3)
    rr.studio(t, key=(0.25, -1.0, 0.35), strength=0.7)
    tmp = os.path.join(PRIVATE, "_face.png")
    render.render_png(tmp, S, (1280, 720))
    p = os.path.join(PRIVATE, "face_%dm.jpg" % int(dist))
    _side_by_side(tmp, p)
    return p


def body(S):
    arm, meshes = rr.load_body()
    a2 = _dup_rig(arm, meshes)
    arm.location = (-0.55, 0, 0)
    a2.location = (0.55, 0, 0)
    char.rest_pose(arm)
    char.rest_pose(a2)
    rr.clip_pose(arm, "pistol_idle_ads", 0.0)
    rr.clip_pose(a2, "rifle_jog_fwd", 0.3)
    for a in (arm, a2):
        a.pose.bones["root"].matrix_basis = Matrix.Identity(4)
    arm.rotation_euler = (0, 0, math.radians(25))
    bpy.context.view_layer.update()
    render.cam_look((0.35, -3.1, 1.2), (0, 0, 0.92), lens=28)
    render.setup(samples=S, res=(1280, 720), threads=3)
    street(False)
    p = os.path.join(OUT, "body_poses.jpg")
    render.render_jpeg(p, S, (1280, 720), max_kb=500)
    return p


def _blank(path):
    from PIL import Image
    Image.new("RGB", (1280, 720)).save(path)
    return path


def _dry_report():
    """Screen position (0..1, y down) and depth of the hands, the wrists and the gun in the scene camera."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    cam = sc.camera
    bpy.context.view_layer.update()
    out = {}
    for o in sc.objects:
        if o.type == "ARMATURE" and o.pose and "hand_r" in o.pose.bones:
            for b in ("hand_r", "hand_l", "lowerarm_r", "lowerarm_l", "upperarm_r", "upperarm_l", "middle_03_r"):
                w = o.matrix_world @ o.pose.bones[b].head
                v = world_to_camera_view(sc, cam, w)
                out[o.name[:12] + ":" + b] = (round(v.x, 3), round(1 - v.y, 3), round(v.z, 3))
        if o.name.startswith("Gun_"):
            for k, pt in (("origin", (0, 0, 0)), ("muzzle", (0.45, 0, 0))):
                v = world_to_camera_view(sc, cam, o.matrix_world @ Vector(pt))
                out[o.name + ":" + k] = (round(v.x, 3), round(1 - v.y, 3), round(v.z, 3))
    print("DRY", json.dumps(out))


def main():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if "--list" in a:
        print("\n".join(SHOTS))
        return
    shot = a[a.index("--shot") + 1]
    S = int(a[a.index("--samples") + 1]) if "--samples" in a else 64
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if "--dry" in a:            # build the scene, report where things land in the frame, render nothing
        render.render_jpeg = lambda path, *k, **kw: (_dry_report(), (path, 0))[1]
        render.render_png = lambda path, *k, **kw: (_dry_report(), _blank(path))[1]
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PRIVATE, exist_ok=True)
    if shot.startswith("fp_"):
        p = fp(shot, S)
    elif shot == "grip_r_chopper":
        p = grip_r(S)
    elif shot == "hands_back_palm":
        p = hands_sheet(S)
    elif shot == "tattoos_photo":
        p = tattoos(S)
    elif shot.startswith("face_"):
        p = face(float(shot[5:-1]), S)
    elif shot == "body_poses":
        p = body(S)
    else:
        raise SystemExit("unknown shot " + shot)
    print("REVIEW done", p, json.dumps(LOG))


if __name__ == "__main__":
    main()
