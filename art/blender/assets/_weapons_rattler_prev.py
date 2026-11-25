"""RATTLER pictures, rendered from the exported files (the GLBs re-imported with their baked sets, as the engine reads them):

    weapons_rattler_hero.jpg    three-quarter, studio HDRI
    weapons_rattler_fp.jpg      through the viewmodel camera of the CHOPPER's first-person picture (54 degrees vertical, the same
                                hip pose), the day rig and the street plate behind; the gun placed so its Palm_R lands where the
                                CHOPPER's lands (the stock is folded along the left side)
    weapons_rattler_side.jpg    flat orthographic left side view on a plain background (the muzzle to the left of the picture)
    weapons_rattler_parts.jpg   posed open: bolt racked 50 mm, trigger pulled, selector on AUTO, the wire stock deployed, the
                                magazine out beside the gun
    art/out/ui/T_UI_Gun_Rattler.png   white-on-transparent 512 x 192 right-side silhouette (stock deployed), 2.2 mm per px, the
                                bore at y = 84, horizontally centred, 4x supersampled with the alpha film (not committed)

    MI_PREVIEWS=weapons_rattler_hero,weapons_rattler_fp,... build.py build weapons_rattler --preview --only none
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import geo, mat, paths, render, rig, scene
from assets import weapons as W
from assets import _weapons_rattler as S

PREVIEW_ONLY = os.environ.get("MI_PREVIEWS", "")
if os.environ.get("MI_PREVIEW_DIR"):                      # development renders go elsewhere than art/previews
    paths.previews = os.environ["MI_PREVIEW_DIR"]


def want(name):
    return not PREVIEW_ONLY or name in PREVIEW_ONLY.split(",")


NUDGE = tuple(float(v) for v in os.environ.get("MI_FP_NUDGE", "0.0,0.0,0.0").split(","))


def anchored_view(nudge=(0.0, 0.0, 0.0)):
    """The CHOPPER's hip viewmodel pose (the same rotation), with the gun moved so that its Palm_R sits where the CHOPPER's
    Palm_R sits. nudge: an extra shift in viewmodel space (x right, y up, z toward the viewer), metres."""
    pos, rot = W.VIEWMODEL["SK_Chopper"]
    pc = W.view_matrix(pos, rot) @ Vector(W.CH["sockets"]["Palm_R"])
    p0 = W.view_matrix((0, 0, 0), rot) @ Vector(S.RT["sockets"]["Palm_R"])
    return tuple(pc - p0 + Vector(nudge)), rot


def load():
    """Re-import the exported gun and magazine; returns (gun mesh, armature, [magazine meshes])."""
    arm, meshes, _c = W.import_asset("SK_Rattler", "ImpRattler")
    gun = max(meshes, key=lambda o: len(o.data.vertices))
    mags = []
    for n in ("SM_Weapon_RattlerMagazine", "SM_Weapon_RattlerMagazine_TopRound"):
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


def bbox(objs):
    lo = np.min([scene.bounds(o, world=True)[0] for o in objs], 0)
    hi = np.max([scene.bounds(o, world=True)[1] for o in objs], 0)
    return lo, hi


def hero(ctx, gun, arm, mags, fill=0.56, direction=(0.62, -1.0, 0.40), lens=85.0, name="weapons_rattler_hero"):
    """Three-quarter studio view (the CHOPPER's and NINE's recipe: 85 mm, shallow focus, studio HDRI)."""
    W.rig_studio()
    W._hide_all_but([gun] + list(mags))
    objs = [gun] + list(mags)
    lo, hi = bbox(objs)
    c = Vector(((lo + hi) / 2).tolist()) + Vector((0.0, 0.0, 0.012))
    span = float(np.linalg.norm(hi - lo))
    fov = 2 * math.atan(18.0 / lens)
    dist = span * fill / math.tan(fov / 2)
    d = Vector(direction).normalized()
    cam = render.cam_look(c + d * dist, c, lens, name="Cam_hero", dof=(dist, 5.6))
    cam.data.clip_start = 0.01
    render.setup(samples=ctx.args.samples, res=(1280, 720))
    path, sec = render.render_jpeg(W._prev(ctx, name), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))


def fp(ctx, gun, arm, mags, stops=0.55):
    """Through the viewmodel camera (54 degrees vertical, the CHOPPER's hip pose) on the day rig: the gun is lit by the day sky and
    sun (design bearing) with a soft fill from the left, where the camera sees the folded stock; the camera sees an urban street
    plate behind it, as the game draws the viewmodel over the world. A copy of weapons.preview_fp (which stays as it was) with
    a little more exposure and the fill, because this gun's left flank is in the shade."""
    W.VIEWMODEL["SK_Rattler"] = anchored_view(NUDGE)
    rd = render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING, stops=stops)
    plate = render.hdri_path("canary_wharf")
    if os.path.exists(plate):
        nt = bpy.context.scene.world.node_tree
        out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputWorld")
        sky = out.inputs["Surface"].links[0].from_node
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(plate, check_existing=True)
        bg = nt.nodes.new("ShaderNodeBackground")
        bg.inputs["Strength"].default_value = 2.0 ** (-(rd.get("exposure", 0.0) or 0.0)) * 0.9
        nt.links.new(env.outputs[0], bg.inputs["Color"])
        lp = nt.nodes.new("ShaderNodeLightPath")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
        nt.links.new(sky.outputs[0], mix.inputs[1])
        nt.links.new(bg.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    cam = W.fp_camera(bearing=170.0, pitch_down=2.0)
    pos, rot = W.VIEWMODEL["SK_Rattler"]
    W.place_in_view(arm, cam, pos, rot)
    for e in mags:
        e.matrix_world = arm.matrix_world
    # the fill: a large soft light over the left of the gun, aimed at the folded stock (world space, the camera looks along -bearing)
    c = arm.matrix_world @ Vector((0.20, 0.03, 0.0))
    left = arm.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.25))
    area_light("FpFill", c + left.normalized() * 0.9, c, (0.9, 0.7), 38.0, (1.0, 0.97, 0.92))
    W._hide_all_but([gun] + list(mags))
    render.setup(samples=ctx.args.samples, res=(1280, 720))
    path, sec = render.render_jpeg(W._prev(ctx, "weapons_rattler_fp"), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))
    arm.matrix_world = Matrix.Identity(4)
    for e in mags:
        e.matrix_world = Matrix.Identity(4)


def side(ctx, gun, arm, mags):
    """Flat orthographic left side view (the camera at +Y looking at the gun's left flank, the muzzle to the left of the picture)."""
    W.rig_studio(strength=1.0)
    plain_background()
    area_light("Fill", (0.20, 1.6, 0.35), (0.20, 0.0, -0.04), (1.6, 1.0), 28.0)
    W._hide_all_but([gun] + list(mags))
    lo, hi = bbox([gun] + list(mags))
    c = (lo + hi) / 2
    cam = render.cam_look(Vector((c[0], 2.0, c[2])), Vector((c[0], 0.0, c[2])), 50.0, name="Cam_side")
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(hi[0] - lo[0], (hi[2] - lo[2]) * 16 / 9) * 1.10
    cam.data.clip_start, cam.data.clip_end = 0.05, 20.0
    render.setup(samples=ctx.args.samples, res=(1280, 720))
    path, sec = render.render_jpeg(W._prev(ctx, "weapons_rattler_side"), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))


def parts(ctx, gun, arm, mags):
    """The gun posed open: bolt racked 50 mm, trigger pulled 17 deg, selector on AUTO, the wire stock deployed; the magazine out."""
    RT = S.RT
    rig.pose_imported(arm, {"bolt": {"translate": (-RT["bolt_travel"], 0, 0)},
                            "trigger": {"rotate": ((0, 1, 0), RT["trigger_deg"])},
                            "selector": {"rotate": ((0, 1, 0), RT["selector_deg"][2])},
                            "stock": {"rotate": ((0, 0, 1), 150.0), "pivot": RT["stock_hinge"]}})
    for o in mags:
        o.matrix_world = Matrix.Translation((0.17, -0.07, -0.012)) @ o.matrix_world
    bpy.context.view_layer.update()
    W.rig_studio(strength=1.0)
    area_light("PortLight", (0.30, -0.55, 0.50), (0.17, -0.01, 0.01), (0.25, 0.25), 22.0)
    W._hide_all_but([gun] + list(mags))
    pts = [rig._evaluated_world_verts(o) for o in [gun] + list(mags)]        # posed: the swung stock is outside the rest bounds
    lo, hi = np.min([q.min(0) for q in pts], 0), np.max([q.max(0) for q in pts], 0)
    c = Vector(((lo + hi) / 2).tolist())
    d = Vector((0.40, -1.0, 0.62)).normalized()
    cam = render.cam_look(c + d * 1.58, c, 60.0, name="Cam_parts", dof=(1.58, 9.0))
    cam.data.clip_start = 0.01
    render.setup(samples=ctx.args.samples, res=(1280, 720))
    path, sec = render.render_jpeg(W._prev(ctx, "weapons_rattler_parts"), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))
    for o in mags:
        o.matrix_world = Matrix.Identity(4)
    rig.pose_imported(arm, {})


def silhouette(ctx, gun, arm, mags):
    """T_UI_Gun_Rattler: white on transparent, 512 x 192, right side, muzzle right, 2.2 mm per px, the bore line at y = 84,
    horizontally centred, 4x supersampled with the alpha film. The stock is DEPLOYED (the rack icon shows the wire stock)."""
    from PIL import Image
    RT = S.RT
    rig.pose_imported(arm, {"stock": {"rotate": ((0, 0, 1), RT["stock_deg"]), "pivot": RT["stock_hinge"]}})
    bpy.context.view_layer.update()
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
    pts = [rig._evaluated_world_verts(o) for o in objs]      # the POSED vertices (the deployed stock reaches X -0.256)
    lo, hi = np.min([q.min(0) for q in pts], 0), np.max([q.max(0) for q in pts], 0)
    cx = float((lo[0] + hi[0]) / 2)                          # the gun's length centre (stock deployed)
    cz = -(96 - 84) * mm_px / 1000.0                         # the bore line sits 12 px above the middle row
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
    tmp = os.path.join(paths.out, "_sil_rattler.png")
    s.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    im = Image.open(tmp).convert("RGBA")
    a = im.split()[3].resize((512, 192), Image.LANCZOS)
    res = Image.merge("RGBA", (Image.new("L", (512, 192), 255), Image.new("L", (512, 192), 255), Image.new("L", (512, 192), 255), a))
    outp = os.path.join(paths.out, "ui", "T_UI_Gun_Rattler.png")
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    res.save(outp)
    os.remove(tmp)
    ctx.log("silhouette %s (gun spans X %.3f .. %.3f)" % (outp, lo[0], hi[0]))
    rig.pose_imported(arm, {})
    return outp


def render_all(ctx):
    gun, arm, mags = load()
    print("armature matrix identity:", np.allclose(np.array(arm.matrix_world), np.eye(4), atol=1e-6))
    if want("weapons_rattler_hero"):
        hero(ctx, gun, arm, mags)
    if want("weapons_rattler_fp"):
        fp(ctx, gun, arm, mags)
        bpy.context.view_layer.update()
    if want("weapons_rattler_side"):
        side(ctx, gun, arm, mags)
    if want("weapons_rattler_parts"):
        parts(ctx, gun, arm, mags)
    if want("T_UI_Gun_Rattler"):
        silhouette(ctx, gun, arm, mags)


def run(ctx):
    render_all(ctx)
