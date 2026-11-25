"""Gun silhouettes for the rack and the lineup picture, rendered from the exported GLBs.

    python art/blender/assets/_weapons_icons.py [chopper nine shorty stretch rattler]   # default: chopper nine
    python art/blender/assets/_weapons_icons.py lineup                                  # weapons_lineup.jpg from the five PNGs

T_UI_Gun_<Name>.png: white on transparent, 512 x 192, right side, muzzle right, 2.2 mm per px (every gun at ONE scale,
so a rack of them reads as six different lengths), the bore line at y = 84 px, horizontally centred on the gun's bounding
box (stock, magazine and all), 4x supersampled with the alpha film, flat emission. Written to art/out/ui (git-ignored);
the lineup picture (art/previews/weapons_lineup.jpg, committed) puts the five own silhouettes on one sheet at that scale.
The RATTLER is drawn with its wire stock DEPLOYED (the bone 'stock' turned +180 deg about +Z at the hinge) because the folded
stock hides the shape that tells it from the others; the STICK (a pack rifle) is rendered on the box by bl_icons.py.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
if BL not in sys.path:
    sys.path.insert(0, BL)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from mi import mat, paths, render, rig, scene  # noqa: E402

GUNS = {   # id: (Name, gun glb, [magazine glbs])
    "chopper": ("Chopper", "SK_Chopper", ["SM_Weapon_ChopperMagazine", "SM_Weapon_ChopperMagazine_TopRound"]),
    "nine": ("Nine", "SK_Nine", ["SM_Weapon_NineMagazine", "SM_Weapon_NineMagazine_TopRound"]),
    "shorty": ("Shorty", "SK_Shorty", ["SM_Weapon_ShortyMagazine", "SM_Weapon_ShortyMagazine_TopRound"]),
    "stretch": ("Stretch", "SK_Stretch", ["SM_Weapon_StretchMagazine", "SM_Weapon_StretchMagazine_TopRound"]),
    "rattler": ("Rattler", "SK_Rattler", ["SM_Weapon_RattlerMagazine", "SM_Weapon_RattlerMagazine_TopRound"]),
}
MM_PX = 2.2
SS = 4


def white_material():
    white = mat.flat("M_Silhouette", (1, 1, 1), 1.0)
    nt = white.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return white


def world_bbox(objs):
    lo = np.array([1e9] * 3)
    hi = -lo
    for o in objs:
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            lo = np.minimum(lo, (w.x, w.y, w.z))
            hi = np.maximum(hi, (w.x, w.y, w.z))
    return lo, hi


def render_icon(gid):
    from PIL import Image
    name, glb, mags = GUNS[gid]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene.setup_cycles(threads=2, samples=16, denoise=False)
    arm, meshes, _c = rig.import_glb(os.path.join(paths.glb, glb + ".glb"), "Imp_" + glb)
    objs = [o for o in meshes if o.type == "MESH"]
    for n in mags:
        p = os.path.join(paths.glb, n + ".glb")
        if os.path.exists(p):
            _a, ms, _c2 = rig.import_glb(p, "Imp_" + n)
            objs += [o for o in ms if o.type == "MESH"]
    for o in list(bpy.data.objects):
        if o.type == "MESH" and o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    if gid == "rattler":                                   # stock deployed for the icon
        pb = arm.pose.bones.get("stock")
        if pb is not None:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Matrix.Rotation(math.pi, 4, "Z").to_quaternion()
            bpy.context.view_layer.update()
    objs = [o for o in objs if o in bpy.data.objects.values()]
    white = white_material()
    for o in objs:
        for sl in o.material_slots:
            sl.material = white
        o.hide_render = False
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and o not in objs:
            o.hide_render = True
    # evaluated bounding box (the armature pose moves the mesh)
    dg = bpy.context.evaluated_depsgraph_get()
    lo = np.array([1e9] * 3)
    hi = -lo
    for o in objs:
        eo = o.evaluated_get(dg)
        me = eo.to_mesh()
        for v in me.vertices:
            w = eo.matrix_world @ v.co
            lo = np.minimum(lo, (w.x, w.y, w.z))
            hi = np.maximum(hi, (w.x, w.y, w.z))
        eo.to_mesh_clear()
    cx = float(lo[0] + hi[0]) / 2.0
    cz = -(96 - 84) * MM_PX / 1000.0
    s = bpy.context.scene
    w = bpy.data.worlds.new("SilW")
    s.world = w
    nt = w.node_tree
    nt.nodes.clear()
    bgn = nt.nodes.new("ShaderNodeBackground")
    bgn.inputs["Color"].default_value = (0, 0, 0, 1)
    bgn.inputs["Strength"].default_value = 0.0
    wo = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bgn.outputs[0], wo.inputs["Surface"])
    pw, ph = 512 * SS, 192 * SS
    cam = render.cam_look(Vector((cx, -2.0, cz)), Vector((cx, 0.0, cz)), 50.0, name="Cam_sil")
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 512 * MM_PX / 1000.0
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
    tmp = os.path.join(paths.out, "_sil_%s.png" % gid)
    s.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    im = Image.open(tmp).convert("RGBA")
    a = im.split()[3].resize((512, 192), Image.LANCZOS)
    one = Image.new("L", (512, 192), 255)
    res = Image.merge("RGBA", (one, one, one, a))
    outp = os.path.join(paths.out, "ui", "T_UI_Gun_%s.png" % name)
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    res.save(outp)
    os.remove(tmp)
    arr = np.asarray(a) > 128
    cols = np.nonzero(arr.any(0))[0]
    print("T_UI_Gun_%s: %s  width %.0f mm (%d px), bore row 84, centre x %.1f" % (
        name, outp, (cols[-1] - cols[0] + 1) * MM_PX, cols[-1] - cols[0] + 1, (cols[0] + cols[-1]) / 2.0))
    return outp


def lineup(out=None):
    """One sheet, the five own silhouettes at the common scale, each on its own row with its name and its length, the bore
    lines aligned (the rows share the 512 px width, so lengths compare by eye)."""
    from PIL import Image, ImageDraw, ImageFont
    order = ("chopper", "nine", "shorty", "stretch", "rattler")
    cell_w, cell_h = 512, 192
    W_, H_ = 1280, 720
    sheet = Image.new("RGB", (W_, H_), (22, 24, 26))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    except OSError:
        f = f2 = ImageFont.load_default()
    cols = {"chopper": (214, 168, 120), "nine": (190, 196, 204), "shorty": (150, 168, 96), "stretch": (190, 128, 90),
            "rattler": (170, 176, 184)}
    pos = [(30, 30), (30 + 560, 30), (30, 30 + 220), (30 + 560, 30 + 220), (30, 30 + 440)]
    sx = {}
    for gid, (x0, y0) in zip(order, pos):
        name = GUNS[gid][0]
        p = os.path.join(paths.out, "ui", "T_UI_Gun_%s.png" % name)
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGBA")
        a = np.asarray(im)[..., 3] > 128
        cs = np.nonzero(a.any(0))[0]
        length_mm = (cs[-1] - cs[0] + 1) * MM_PX
        tint = Image.new("RGBA", im.size, cols[gid] + (255,))
        tint.putalpha(im.split()[3])
        d.rectangle([x0, y0, x0 + cell_w, y0 + cell_h], fill=(34, 37, 40))
        d.line([x0, y0 + 84, x0 + cell_w, y0 + 84], fill=(58, 62, 66), width=1)
        sheet.paste(tint, (x0, y0), tint)
        d.text((x0 + 8, y0 + 6), name.upper(), fill=(230, 230, 230), font=f)
        d.text((x0 + 8, y0 + cell_h - 24), "%d mm" % round(length_mm), fill=(160, 166, 172), font=f2)
    d.text((30 + 560, 30 + 440 + 6), "Five own guns, one scale: 2.2 mm per pixel,", fill=(190, 194, 198), font=f2)
    d.text((30 + 560, 30 + 440 + 26), "bore lines aligned. The sixth, the STICK,", fill=(190, 194, 198), font=f2)
    d.text((30 + 560, 30 + 440 + 46), "is a pack rifle (icon from the box).", fill=(190, 194, 198), font=f2)
    out = out or os.path.join(paths.art, "previews", "weapons_lineup.jpg")
    sheet.save(out, quality=88)
    print("lineup", out, os.path.getsize(out))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args and args[0] == "lineup":
        lineup()
    else:
        for g in (args or ["chopper", "nine"]):
            render_icon(g)
