"""Independent review renders of the exported main character (Rule). Reads only the exports: art/out/glb/SK_Rule.glb
(textures embedded), SK_RuleArms.glb with the RuleArms_Skin texture set wired the way Unreal's material reads it
(BC, ORM: G roughness / B metallic, N), and SM_Character_RuleBracelet.glb on its socket from SK_RuleArms.sockets.json.
Poses come from Epic's clips in art/out/epic/. One shot per process.

    python art/blender/review/rule_review.py --shot <name> [--samples 48]
    python art/blender/review/rule_review.py --list

Outputs art/out/review/rule/<shot>.jpg (1280 x 720). The outputs show the likeness, so they stay in art/out/
(git-ignored).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(BL))
sys.path.insert(0, BL)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from mi import char, render, rig  # noqa: E402

OUT = os.path.join(ROOT, "art", "out", "review", "rule")
GLB = os.path.join(ROOT, "art", "out", "glb")
TEX = os.path.join(ROOT, "art", "out", "textures")
PHOTO = os.path.join(ROOT, "art", "out", "ref", "main_character_look.jpg")
SHOTS = ["face_photo", "head_front", "head_34", "head_profile", "body_front", "body_back", "arms_fp",
         "hand_fist", "hand_trigger", "hand_open"]


def skin_sss(mat, weight=0.12):
    for nd in mat.node_tree.nodes:
        if nd.type == "BSDF_PRINCIPLED":
            nd.inputs["Subsurface Weight"].default_value = weight
            nd.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
            nd.inputs["Subsurface Scale"].default_value = 0.006


def wire_set(mat, set_name):
    d = os.path.join(TEX, set_name)
    nt = mat.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs["Surface"])

    def img(tag, data):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(d, "T_%s_%s.png" % (set_name, tag)), check_existing=True)
        t.image.colorspace_settings.name = "Non-Color" if data else "sRGB"
        return t
    bc, n, orm = img("BC", False), img("N", True), img("ORM", True)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs[0])
    nt.links.new(bc.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(n.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])


def load_body():
    arm, meshes, col = rig.import_glb(os.path.join(GLB, "SK_Rule.glb"), "Rule_Body")
    for m in meshes:
        for s in m.material_slots:
            if s.material and "Head" in s.material.name:
                skin_sss(s.material, 0.10)
    print("REVIEW body mats", [s.material.name for m in meshes for s in m.material_slots if s.material])
    return arm, meshes


def load_arms():
    arm, meshes, col = rig.import_glb(os.path.join(GLB, "SK_RuleArms.glb"), "Rule_Arms")
    for m in meshes:
        for s in m.material_slots:
            if s.material and not s.material.get("_wired"):
                wire_set(s.material, "RuleArms_Skin")
                if "Skin" in s.material.name:
                    skin_sss(s.material)
                s.material["_wired"] = 1
    return arm, meshes


def bracelet(arm):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(GLB, "SM_Character_RuleBracelet.glb"))
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    j = new[0]
    for o in new[1:]:
        bpy.data.objects.remove(o, do_unlink=True)
    for s in j.material_slots:      # the GLB carries stub materials; Unreal's are polished / worn silver
        for nd in s.material.node_tree.nodes:
            if nd.type == "BSDF_PRINCIPLED":
                nd.inputs["Base Color"].default_value = (0.92, 0.92, 0.93, 1)
                nd.inputs["Metallic"].default_value = 1.0
                nd.inputs["Roughness"].default_value = 0.18 if s.material.name.endswith("Silver") else 0.32
    sk = json.load(open(os.path.join(GLB, "SK_RuleArms.sockets.json")))["SM_Character_RuleBracelet"]
    v = sk["blender_world_rest"]
    M = Matrix([v[0:4], v[4:8], v[8:12], v[12:16]])
    bone = sk["bone"]
    j.parent = arm
    j.parent_type = "BONE"
    j.parent_bone = bone
    bpy.context.view_layer.update()
    b = arm.data.bones[bone]
    rest_bone = arm.matrix_world @ b.matrix_local @ Matrix.Translation((0, b.length, 0))
    j.matrix_parent_inverse = rest_bone.inverted()
    j.matrix_basis = M
    bpy.context.view_layer.update()
    return j


def clip_pose(arm, clip, frac):
    src, act, rng = char.import_clip(clip)
    f = int(round(rng[0] + (rng[1] - rng[0]) * frac))
    bpy.context.scene.frame_set(f)
    char.pose_from_armature(arm, src)
    for o in list(bpy.data.objects):
        if o.name.startswith("Clip_"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()


def studio(target, key=(0.6, -0.9, 0.7), strength=1.0):
    from assets import characters as C
    C._studio(target, key=key, strength=strength)


def ground():
    me = bpy.data.meshes.new("Ground")
    s = 40.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("Ground", me)
    bpy.context.scene.collection.objects.link(ob)
    m = bpy.data.materials.new("Concrete")
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.24, 0.23, 0.215, 1)
    b.inputs["Roughness"].default_value = 0.88
    me.materials.append(m)


def bone_pos(arm, name):
    return (arm.matrix_world @ arm.pose.bones[name].matrix).to_translation()


def head_shot(shot, S):
    arm, meshes = load_body()
    char.rest_pose(arm)
    hb = arm.pose.bones["head"]
    if shot == "face_photo":      # the photo: chin down, camera a touch above the eyes and to his left
        piv = hb.head.copy()
        hb.matrix = (Matrix.Translation(piv) @ Matrix.Rotation(math.radians(10), 4, "X") @ Matrix.Translation(-piv)) @ hb.matrix
    bpy.context.view_layer.update()
    h = bone_pos(arm, "head")
    t = Vector((h.x, h.y - 0.03, h.z + 0.02))
    az = {"face_photo": 6, "head_front": 0, "head_34": 38, "head_profile": 90}[shot]
    el = {"face_photo": 0.10}.get(shot, 0.0)
    d = Vector((math.sin(math.radians(az)), -math.cos(math.radians(az)), 0))
    render.cam_look(tuple(t + d * 1.0 + Vector((0, 0, el))), tuple(t), lens=55)
    render.setup(samples=S, res=(1280, 720), threads=3)
    if shot == "face_photo":      # harsh frontal flash, as in the photo
        studio(t, key=(0.25, -1.0, 0.35), strength=0.7)
    else:
        studio(t, key=(0.6, -0.9, 0.6), strength=0.6)
    p = os.path.join(OUT, shot + ".jpg")
    if shot == "face_photo":
        tmp = os.path.join(OUT, "_face_tmp.png")
        render.render_png(tmp, S, (1280, 720))
        from PIL import Image
        sheet = Image.new("RGB", (1280, 720), (16, 16, 16))
        ph = Image.open(PHOTO).convert("RGB")
        ph = ph.resize((int(ph.width * 720 / ph.height), 720), Image.LANCZOS)
        sheet.paste(ph, (0, 0))
        r = Image.open(tmp).convert("RGB")
        w = 1280 - ph.width - 4
        x0 = (1280 - w) // 2
        sheet.paste(r.crop((x0, 0, x0 + w, 720)), (ph.width + 4, 0))
        sheet.save(p, quality=92)
        os.remove(tmp)
    else:
        render.render_jpeg(p, S, (1280, 720), max_kb=420)
    return p


def body_shot(shot, S):
    arm, meshes = load_body()
    j = bracelet(arm)
    arm2 = arm.copy()
    arm2.data = arm.data.copy()
    bpy.context.scene.collection.objects.link(arm2)
    for m in meshes:
        t = m.copy()
        t.data = m.data
        bpy.context.scene.collection.objects.link(t)
        t.parent = arm2
        for md in t.modifiers:
            if md.type == "ARMATURE":
                md.object = arm2
    j2 = bracelet(arm2)
    arm.location = (-0.5, 0, 0)
    arm2.location = (0.5, 0, 0)
    char.rest_pose(arm)
    clip_pose(arm2, "rifle_jog_fwd", 0.3)
    arm2.pose.bones["root"].matrix_basis = Matrix.Identity(4)
    if shot == "body_back":
        arm.rotation_euler = (0, 0, math.radians(180))
        arm2.rotation_euler = (0, 0, math.radians(180))
        arm.location, arm2.location = (0.5, 0, 0), (-0.5, 0, 0)
    bpy.context.view_layer.update()
    ground()
    render.cam_look((0.25, -2.6, 1.15), (0, 0, 0.93), lens=24)
    render.setup(samples=S, res=(1280, 720), threads=3)
    render.rig_day(sun_azimuth=215.0 if shot == "body_front" else 35.0, stops=0.4)
    p = os.path.join(OUT, shot + ".jpg")
    render.render_jpeg(p, S, (1280, 720), max_kb=420)
    return p


def arms_rig():
    from assets import characters as C
    marm, mbody = char.import_mannequin()
    mbody.hide_render = True
    mbody.hide_viewport = True
    R, Rl = C.ArmRig(marm, mbody, "r"), C.ArmRig(marm, mbody, "l")
    kill = [o for o in bpy.data.objects if o.name.startswith("Mannequin") or o.parent == marm]
    for o in kill:
        bpy.data.objects.remove(o, do_unlink=True)
    return R, Rl


def arms_fp(S):
    from assets import _characters_pose as PZ
    R, Rl = arms_rig()
    arm, meshes = load_arms()
    bracelet(arm)
    col = bpy.context.scene.collection
    char.rest_pose(arm)
    arm.location = (0, 0, 0)
    g, real = PZ.load_gun("chopper", _col("Gun"))
    cam = PZ.eye_camera(arm, col)
    M = PZ.gun_from_camera(cam, "chopper", "hip")
    g.matrix_world = M
    PZ.hold(arm, M, "chopper", R, Rl)
    render.setup(samples=S, res=(1280, 720), threads=3)
    render.rig_day(sun_azimuth=235.0)
    p = os.path.join(OUT, "arms_fp.jpg")
    render.render_jpeg(p, S, (1280, 720), max_kb=420)
    print("REVIEW gun real", real)
    return p


def _col(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def hand_shot(shot, S):
    from assets import _characters_pose as PZ
    R, Rl = arms_rig()
    arm, meshes = load_arms()
    bracelet(arm)
    char.rest_pose(arm)
    if shot == "hand_fist":
        clip_pose(arm, "unarmed_attack", FIST_FRAC)
    elif shot == "hand_trigger":
        clip_pose(arm, "pistol_idle_ads", 0.0)
    arm.pose.bones["root"].matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    fwd, lat, dors = (Vector(v) for v in PZ.hand_axes(arm, "r", R))
    hr = bone_pos(arm, "hand_r")
    c = hr + fwd * 0.06
    cam = c + dors * 0.27 + lat * -0.11 + fwd * -0.05
    render.cam_look(tuple(cam), tuple(c), lens=40)
    render.setup(samples=S, res=(1280, 720), threads=3)
    studio(c, key=tuple(dors * 0.7 + fwd * -0.4 + Vector((0, -0.2, 0.4))))
    p = os.path.join(OUT, shot + ".jpg")
    render.render_jpeg(p, S, (1280, 720), max_kb=420)
    return p


FIST_FRAC = 0.35


def main():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if "--list" in a:
        print("\n".join(SHOTS))
        return
    shot = a[a.index("--shot") + 1]
    S = int(a[a.index("--samples") + 1]) if "--samples" in a else 48
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(OUT, exist_ok=True)
    if shot.startswith("head") or shot == "face_photo":
        p = head_shot(shot, S)
    elif shot.startswith("body"):
        p = body_shot(shot, S)
    elif shot == "arms_fp":
        p = arms_fp(S)
    else:
        p = hand_shot(shot, S)
    print("REVIEW done", p)


if __name__ == "__main__":
    main()
