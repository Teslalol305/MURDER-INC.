"""Previews of Rule (used by rule.py on_preview): at most 10 renders.

  rule_arms_hero   studio, the arms in the rifle aim (MF_Rifle_Idle_ADS)
  rule_arms_fp     first-person camera, CHOPPER held (art/out/glb/SK_Chopper.glb), day light
  rule_hands       fist, trigger pull, open hand at 30 cm (three renders)
  rule_body_hero   three-quarter, day rig: aimed idle and jog (two armatures)
  rule_face        head and shoulders at the reference photo's angle (front, eye level)
  rule_turntable   four views in one render
  rule_wire        clay and wire: hand and head (two renders)

Pick with --only rule_arms_hero,... (the build parts follow from the names).
"""
import math
import os
import tempfile

import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import char, paths, render, scene

from . import characters as C
from . import rule as RU

TMP = tempfile.gettempdir()


def _want(ctx, name):
    only = [o for o in (ctx.args.only or []) if o.startswith("rule_")]
    return not only or name in only


def _studio(target, key=(0.6, -0.9, 0.7), strength=1.0):
    C._studio(target, key=key, strength=strength)


def _clay_wire(ob):
    saved = [s.material for s in ob.material_slots]
    clay = bpy.data.materials.new("Clay")
    nt = clay.node_tree
    b = nt.nodes.get("Principled BSDF")
    wf = nt.nodes.new("ShaderNodeWireframe")
    wf.use_pixel_size = True
    wf.inputs[0].default_value = 0.8
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.55, 0.55, 0.56, 1)
    mix.inputs["B"].default_value = (0.03, 0.03, 0.035, 1)
    nt.links.new(wf.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    for s in ob.material_slots:
        s.material = clay
    return saved


def _restore(ob, saved):
    for s, m in zip(ob.material_slots, saved):
        s.material = m


def arms(ctx):
    from assets import _characters_pose as PZ
    r = getattr(ctx, "rule", None)
    if not r or "ob" not in r:
        return
    arm, ob, R, Rl = r["arm"], r["ob"], r["R"], r["Rl"]
    r["body"].hide_render = True
    RU.place_bracelet(r)
    S = ctx.args.samples
    out = paths.previews
    col = scene.collection("Preview")
    if _want(ctx, "rule_arms_fp"):
        char.rest_pose(arm)
        arm.location = (0, 0, 0)
        g, real = PZ.load_gun("chopper", col)
        cam = PZ.eye_camera(arm, col)
        M = PZ.gun_from_camera(cam, "chopper", "hip")
        g.matrix_world = M
        PZ.hold(arm, M, "chopper", R, Rl)
        render.setup(samples=S, res=(1280, 720), threads=3)
        render.rig_day(sun_azimuth=getattr(render, "DESIGN_SUN_BEARING", 235.0))
        _p, sec = render.render_jpeg(os.path.join(out, "rule_arms_fp.jpg"), S)
        ctx.log("preview rule_arms_fp (gun file %s) %.0fs" % (real, sec))
        for o in list(col.objects):
            if o.type != "CAMERA":
                o.hide_render = True
        arm.location = (0, 0, 0)
    if _want(ctx, "rule_hands"):
        shots = []
        for label, fn in (("fist", lambda: PZ.close_fingers(arm, "r", R, 1.0, thumb=1.0)),
                          ("trigger pull", lambda: (PZ.close_fingers(arm, "r", R, 0.9, ("middle", "ring", "pinky"), thumb=0.7),
                                                    PZ.close_fingers(arm, "r", R, 0.42, ("index",), angles=(35, 80, 40)))),
                          ("open hand", lambda: None)):
            char.rest_pose(arm)
            fn()
            hr = (arm.matrix_world @ arm.pose.bones["hand_r"].matrix).to_translation()
            c = Vector(hr) + Vector(R.fwd) * 0.06
            cam_pos = c + Vector(R.dors) * 0.27 + Vector(R.lat) * -0.11 + Vector((0, -0.05, 0.05))
            render.cam_look(tuple(cam_pos), tuple(c), lens=50)
            render.setup(samples=S, res=(640, 720), threads=3)
            _studio(c)
            _studio(c, key=tuple(Vector(R.lat) * 0.7 + Vector(R.dors) * 0.25 + Vector((0, 0.3, 0.5))))
            p = os.path.join(TMP, "rule_hands_%s.png" % label.replace(" ", "_"))
            render.render_png(p, S, (640, 720))
            shots.append(p)
        render.contact_sheet(shots, os.path.join(out, "rule_hands.jpg"), cols=3, labels=["fist", "trigger pull", "open hand"])
        ctx.log("preview rule_hands")
    char.rest_pose(arm)
    if _want(ctx, "rule_arms_hero"):
        char.pose_from_clip(arm, "rifle_idle_ads", 0)
        hl = (arm.matrix_world @ arm.pose.bones["hand_l"].matrix).to_translation()
        hr = (arm.matrix_world @ arm.pose.bones["hand_r"].matrix).to_translation()
        c = (hl + hr) / 2
        render.cam_look(tuple(c + Vector((0.55, -0.75, 0.12))), tuple(c + Vector((0.02, 0.06, -0.03))), lens=45)
        render.setup(samples=S, res=(1280, 720), threads=3)
        _studio(c)
        render.render_jpeg(os.path.join(out, "rule_arms_hero.jpg"), S)
        ctx.log("preview rule_arms_hero")
    char.rest_pose(arm)


def body(ctx):
    from assets import goon_generated as GG
    b = getattr(ctx, "body", None)
    if not b:
        return
    ob, arm = b["ob"], b["arm"]
    S = ctx.args.samples
    out = paths.previews
    if getattr(ctx, "rule", None) and "ob" in ctx.rule:
        ctx.rule["ob"].hide_render = True
        ctx.rule["bracelet"].hide_render = True
    g = GG._ground()
    if _want(ctx, "rule_body_hero"):
        # aimed idle (front three-quarter) and jog beside it: a second armature drives a linked twin
        arm2 = arm.copy()
        arm2.data = arm.data.copy()
        ctx.col.objects.link(arm2)
        arm2.location = (1.05, 0.55, 0)
        twin = ob.copy()
        twin.data = ob.data
        ctx.col.objects.link(twin)
        twin.parent = arm2
        twin.modifiers["Armature"].object = arm2
        char.pose_from_clip(arm, "rifle_idle_ads", 0)
        char.pose_from_clip(arm2, "rifle_jog_fwd", 8)
        for a in (arm, arm2):
            a.pose.bones["root"].matrix_basis = Matrix.Identity(4)
        arm2.rotation_euler = (0, 0, math.radians(35))
        render.setup(samples=S, res=(1280, 720), threads=3)
        render.rig_day(sun_azimuth=215.0, stops=0.4)
        render.cam_look((1.55, -4.2, 1.35), (0.55, 0.15, 0.95), lens=42, name="Cam_Hero")
        _p, sec = render.render_jpeg(os.path.join(out, "rule_body_hero.jpg"), S)
        ctx.log("preview rule_body_hero %.0fs" % sec)
        bpy.data.objects.remove(twin, do_unlink=True)
        bpy.data.objects.remove(arm2, do_unlink=True)
        char.rest_pose(arm)
    if _want(ctx, "rule_face"):
        char.rest_pose(arm)
        bpy.context.view_layer.update()
        hd = (arm.matrix_world @ arm.pose.bones["head"].matrix).to_translation()
        t = Vector(hd) + Vector((0, -0.02, 0.06))
        render.cam_look(tuple(t + Vector((0.0, -1.05, -0.06))), tuple(t + Vector((0, 0, -0.05))), lens=75, name="Cam_Face")
        render.setup(samples=S, res=(1280, 720), threads=3)
        _studio(t, key=(0.5, -0.9, 0.5), strength=0.9)
        render.render_jpeg(os.path.join(out, "rule_face.jpg"), S)
        ctx.log("preview rule_face")
    if _want(ctx, "rule_turntable"):
        char.rest_pose(arm)
        twins = []
        for k, ang in enumerate((0, 90, 180, 270)):
            t = ob.copy()
            t.data = ob.data
            ctx.col.objects.link(t)
            t.parent = None
            t.modifiers["Armature"].object = arm
            t.matrix_world = Matrix.Translation(((k - 1.5) * 0.95, 0, 0)) @ Matrix.Rotation(math.radians(ang), 4, "Z")
            twins.append(t)
        ob.hide_render = True
        render.setup(samples=S, res=(1280, 720), threads=3)
        render.rig_day(sun_azimuth=215.0, stops=0.4)
        render.cam_look((0, -6.4, 1.05), (0, 0, 0.92), lens=40, name="Cam_Turn")
        render.render_jpeg(os.path.join(out, "rule_turntable.jpg"), S)
        for t in twins:
            bpy.data.objects.remove(t, do_unlink=True)
        ob.hide_render = False
        ctx.log("preview rule_turntable")
    g.hide_render = True


def wire(ctx):
    if not _want(ctx, "rule_wire"):
        return
    shots, labels = [], []
    S = max(16, ctx.args.samples // 3)
    r = getattr(ctx, "rule", None)
    if r and "ob" in r:
        ob, R = r["ob"], r["R"]
        for o in bpy.context.scene.objects:
            if o.type == "MESH" and o is not ob:
                o.hide_render = True
        ob.hide_render = False
        char.rest_pose(r["arm"])
        saved = _clay_wire(ob)
        c = Vector(R.W) + Vector(R.fwd) * 0.07
        render.cam_look(tuple(c + Vector(R.dors) * 0.30 + Vector(R.lat) * 0.10 + Vector((0, -0.06, 0.04))), tuple(c), lens=50)
        render.setup(samples=S, res=(640, 720), denoise=False, threads=3)
        _studio(c)
        p = os.path.join(TMP, "rule_wire_hand.png")
        render.render_png(p, S, (640, 720))
        shots.append(p)
        labels.append("SK_RuleArms, hand")
        _restore(ob, saved)
        ob.hide_render = True
    b = getattr(ctx, "body", None)
    if b:
        ob, arm = b["ob"], b["arm"]
        for o in bpy.context.scene.objects:
            if o.type == "MESH" and o is not ob:
                o.hide_render = True
        ob.hide_render = False
        char.rest_pose(arm)
        hd = (arm.matrix_world @ arm.pose.bones["head"].matrix).to_translation()
        t = Vector(hd) + Vector((0, -0.02, 0.0))
        saved = _clay_wire(ob)
        render.cam_look(tuple(t + Vector((0.45, -0.75, 0.05))), tuple(t), lens=60)
        render.setup(samples=S, res=(640, 720), denoise=False, threads=3)
        _studio(t)
        p = os.path.join(TMP, "rule_wire_head.png")
        render.render_png(p, S, (640, 720))
        shots.append(p)
        labels.append("SK_Rule, head")
        _restore(ob, saved)
    if shots:
        render.contact_sheet(shots, os.path.join(paths.previews, "rule_wire.jpg"), cols=len(shots), labels=labels)
        ctx.log("preview rule_wire")


def preview(ctx, objs):
    arms(ctx)
    body(ctx)
    wire(ctx)
