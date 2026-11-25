"""SHORTY pictures, rendered from the exported files (the GLBs re-imported with their baked sets, as the engine reads them):

    weapons_shorty_hero.jpg    three-quarter, studio HDRI
    weapons_shorty_fp.jpg      through the viewmodel camera of the CHOPPER's first-person picture (54 degrees vertical, the
                               same hip rotation, the gun moved so its Palm_R lands where the CHOPPER's lands: the origin
                               of a bullpup is its butt, not its grip), the day rig and the street plate behind
    weapons_shorty_side.jpg    flat orthographic left side view on a plain background
    weapons_shorty_parts.jpg   posed open (bolt locked back, trigger pulled, selector on SEMI), the magazine beside it
    art/out/ui/T_UI_Gun_Shorty.png   white-on-transparent 512 x 192 right-side silhouette, 2.2 mm per px, bore at y = 84
                                     (4x supersampled, alpha film; not committed)

    MI_PREVIEWS=weapons_shorty_hero,weapons_shorty_fp,... build.py build weapons_shorty --preview --only none
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import geo, mat, paths, render, rig, scene
from assets import weapons as W
from assets import _weapons_shorty as S

PREVIEW_ONLY = os.environ.get("MI_PREVIEWS", "")


def want(name):
    return not PREVIEW_ONLY or name in PREVIEW_ONLY.split(",")


def anchored_view():
    """The CHOPPER's hip viewmodel pose, with the gun moved so that its Palm_R sits where the CHOPPER's Palm_R sits."""
    pos, rot = W.VIEWMODEL["SK_Chopper"]
    pc = W.view_matrix(pos, rot) @ Vector(W.CH["sockets"]["Palm_R"])
    p0 = W.view_matrix((0, 0, 0), rot) @ Vector(S.SH["sockets"]["Palm_R"])
    return tuple(pc - p0), rot


def load():
    """Re-import the exported gun and magazine; returns (gun mesh, armature, [magazine meshes])."""
    arm, meshes, _c = W.import_asset("SK_Shorty", "ImpShorty")
    gun = max(meshes, key=lambda o: len(o.data.vertices))
    mags = []
    for n in ("SM_Weapon_ShortyMagazine", "SM_Weapon_ShortyMagazine_TopRound"):
        _a, ms, _c2 = W.import_asset(n, "Imp" + n)
        mags += ms
    for o in list(bpy.data.objects):
        if o.type == "MESH" and o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    return gun, arm, mags


def plain_background(colour=(0.20, 0.205, 0.21)):
    """Camera rays see a flat colour; the lighting keeps coming from the world's environment."""
    nt = bpy.context.scene.world.node_tree
    out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputWorld")
    src = out.inputs["Surface"].links[0].from_node
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*colour, 1.0)
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(src.outputs[0], mix.inputs[1])
    nt.links.new(bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def area_light(name, loc, target, size, watts, colour=(1.0, 1.0, 1.0)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = size
    ld.energy = watts
    ld.color = colour
    ob = bpy.data.objects.new(name, ld)
    scene.collection("Rig").objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def hero(ctx, gun, arm, mags):
    W.preview_hero(ctx, gun, arm, "weapons_shorty_hero", (0.60, -1.0, 0.42), (0.35, -0.005, -0.045), lens=85.0, fstop=5.6,
                   extra=mags)


def fp(ctx, gun, arm, mags):
    W.VIEWMODEL["SK_Shorty"] = anchored_view()
    W.preview_fp(ctx, gun, arm, "SK_Shorty", "weapons_shorty_fp", extra=mags)


def side(ctx, gun, arm, mags):
    """Flat orthographic left side view (the camera at +Y looking at the gun's left, the muzzle to the left of the picture
    is avoided: it is mirrored on purpose so the picture reads as the player's left side)."""
    W.rig_studio(strength=1.0)
    plain_background()
    area_light("Fill", (0.35, 1.6, 0.35), (0.35, 0.0, -0.04), (1.6, 1.0), 260.0)
    W._hide_all_but([gun] + list(mags))
    lo, hi = np.min([scene.bounds(o, world=True)[0] for o in [gun] + list(mags)], 0), np.max(
        [scene.bounds(o, world=True)[1] for o in [gun] + list(mags)], 0)
    c = (lo + hi) / 2
    cam = render.cam_look(Vector((c[0], 2.0, c[2])), Vector((c[0], 0.0, c[2])), 50.0, name="Cam_side")
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(hi[0] - lo[0], (hi[2] - lo[2]) * 16 / 9) * 1.10
    cam.data.clip_start, cam.data.clip_end = 0.05, 20.0
    render.setup(samples=ctx.args.samples, res=(1280, 720))
    path, sec = render.render_jpeg(W._prev(ctx, "weapons_shorty_side"), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))


def parts(ctx, gun, arm, mags):
    """The gun posed open: bolt locked back 75 mm, trigger pulled 17 deg, selector on SEMI; the magazine out beside it."""
    SH = S.SH
    rig.pose_imported(arm, {"bolt": {"translate": (-SH["bolt_travel"], 0, 0)},
                            "trigger": {"rotate": ((0, 1, 0), SH["trigger_deg"])},
                            "selector": {"rotate": ((0, 1, 0), SH["selector_deg"][1])}})
    for o in mags:
        o.matrix_world = Matrix.Translation((0.31, -0.095, -0.012)) @ o.matrix_world
    bpy.context.view_layer.update()
    W.rig_studio(strength=1.0)
    W._hide_all_but([gun] + list(mags))
    lo = np.min([scene.bounds(o, world=True)[0] for o in [gun] + list(mags)], 0)
    hi = np.max([scene.bounds(o, world=True)[1] for o in [gun] + list(mags)], 0)
    c = Vector(((lo + hi) / 2).tolist())
    d = Vector((0.30, -1.0, 0.50)).normalized()
    cam = render.cam_look(c + d * 1.45, c + Vector((0.0, 0.0, 0.0)), 62.0, name="Cam_parts", dof=(1.45, 9.0))
    cam.data.clip_start = 0.01
    render.setup(samples=ctx.args.samples, res=(1280, 720))
    path, sec = render.render_jpeg(W._prev(ctx, "weapons_shorty_parts"), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))
    for o in mags:
        o.matrix_world = Matrix.Identity(4)
    rig.pose_imported(arm, {})


def silhouette(ctx, gun, arm, mags):
    """T_UI_Gun_Shorty: white on transparent, 512 x 192, right side, muzzle right, 2.2 mm per px, the bore line at y = 84,
    horizontally centred, 4x supersampled with the alpha film (the carry handle's window stays transparent)."""
    from PIL import Image
    s = bpy.context.scene
    objs = [gun] + list(mags)
    white = mat.flat("M_Silhouette", (1, 1, 1), 1.0)
    nt = white.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    for o in objs:
        for sl in o.material_slots:
            sl.material = white
    W._hide_all_but(objs)
    w = bpy.data.worlds.new("SilW")
    s.world = w
    nt = w.node_tree
    nt.nodes.clear()
    bgn = nt.nodes.new("ShaderNodeBackground")
    bgn.inputs["Color"].default_value = (0, 0, 0, 1)
    bgn.inputs["Strength"].default_value = 0.0
    wo = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bgn.outputs[0], wo.inputs["Surface"])
    ss = 4
    pw, ph = 512 * ss, 192 * ss
    mm_px = 2.2
    cx = 0.350                                              # the gun's length centre (X 0 .. 0.700)
    cz = -(96 - 84) * mm_px / 1000.0                        # the bore line sits 12 px above the middle row
    cam = render.cam_look(Vector((cx, -2.0, cz)), Vector((cx, 0.0, cz)), 50.0, name="Cam_sil")
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 512 * mm_px / 1000.0
    cam.data.clip_start, cam.data.clip_end = 0.05, 20.0
    s.render.resolution_x, s.render.resolution_y = pw, ph
    s.render.resolution_percentage = 100
    s.render.film_transparent = True
    s.cycles.samples = 16
    s.cycles.use_denoising = False
    s.cycles.use_adaptive_sampling = False
    s.view_settings.view_transform = "Standard"
    s.view_settings.look = "None"
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    tmp = os.path.join(paths.out, "_sil_shorty.png")
    s.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    im = Image.open(tmp).convert("RGBA")
    a = im.split()[3].resize((512, 192), Image.LANCZOS)
    res = Image.merge("RGBA", (Image.new("L", (512, 192), 255), Image.new("L", (512, 192), 255), Image.new("L", (512, 192), 255), a))
    outp = os.path.join(paths.out, "ui", "T_UI_Gun_Shorty.png")
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    res.save(outp)
    os.remove(tmp)
    ctx.log("silhouette %s" % outp)
    return outp


def render_all(ctx):
    gun, arm, mags = load()
    print("armature matrix identity:", np.allclose(np.array(arm.matrix_world), np.eye(4), atol=1e-6))
    if want("weapons_shorty_hero"):
        hero(ctx, gun, arm, mags)
    if want("weapons_shorty_fp"):
        fp(ctx, gun, arm, mags)
    if want("weapons_shorty_side"):
        side(ctx, gun, arm, mags)
    if want("weapons_shorty_parts"):
        parts(ctx, gun, arm, mags)
    if want("T_UI_Gun_Shorty"):
        silhouette(ctx, gun, arm, mags)


def render(ctx):
    render_all(ctx)
