"""Canal Street look-dev pictures (art/previews/maps/, 1280 x 720 JPEG, at most 300 kB each), night, wet after rain.

    venv/bin/python art/blender/build.py build chinatown --preview --samples 16 [--only ct_canal_north,ct_market,ct_street,ct_atlas]

ct_canal_north   the north row N1..N6 from placements_chinatown.json (the Block's facade kit + the Canal kit), signs lit from the
                 atlas, vendor tables on the south kerb, from the south sidewalk at eye height
ct_market        the market kit under bare bulbs: stall counters, produce, fish counter, dry goods, boards, tarp, tank, scale
ct_street        the lantern string, the Square's furniture, the neon and the sign carriers on a wall, the roof props
ct_atlas         the sign atlas page, downscaled
The ground is a flat stand-in (dark wet asphalt, damp concrete): the real street is the Block's street kit with wetness in Unreal.
"""
import json
import math
import os

import bpy
import numpy as np

from assets import _chinatown_atlas as atlas
from mi import geo, mat, paths, render, scene

PV = os.path.join(paths.previews, "maps")


def face_material(key, strength=3.0):
    """A preview material that shows one atlas cell on a carrier's 0..1 face (what the MI does in Unreal)."""
    name = "Prev_Face_" + key
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    info = json.load(open(os.path.join(paths.texture_set("Sign_CT_Atlas1"), "set.json")))
    c = info["cells"][key]
    u0, v0, u1, v1 = c["uv"]
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    uv = nt.nodes.new("ShaderNodeUVMap")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (u0, v0, 0.0)
    mp.inputs["Scale"].default_value = (u1 - u0, v1 - v0, 1.0)
    nt.links.new(uv.outputs[0], mp.inputs[0])
    d = paths.texture_set("Sign_CT_Atlas1")
    for role, sock, srgb in (("BC", "Base Color", True), ("E", "Emission Color", True)):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(d, "T_Sign_CT_Atlas1_%s.png" % role), check_existing=True)
        t.image.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
        t.extension = "EXTEND"
        nt.links.new(mp.outputs[0], t.inputs[0])
        nt.links.new(t.outputs["Color"], p.inputs[sock])
    p.inputs["Roughness"].default_value = 0.35
    p.inputs["Emission Strength"].default_value = strength if c["lit"] else 0.0
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


def set_face(ob, key, strength=3.0):
    for i, sl in enumerate(ob.material_slots):
        if sl.material and sl.material.name.startswith("M_Sign_CT_Face"):
            sl.link = "OBJECT"
            sl.material = face_material(key, strength)


def put(src, loc, rot=0.0, scale=1.0, col=None, face=None):
    ob = scene.duplicate(src, linked=True, col=col)
    scene.place(ob, loc, rot)
    ob.scale = (scale, 1.0, 1.0)
    ob["mi_placed"] = True
    ob["mi_uv"] = (float(loc[0]), float(loc[2]) - 0.15, 0.0)
    if face:
        set_face(ob, face)
    return ob


def night_on(M):
    """Bulbs, lantern paper and lit interiors on (their slots are emissive at 0 by day)."""
    for key, s in (("bulb", 12.0), ("paper", 0.45), ("interiorLit", 0.3)):
        mat.principled(M[key]).inputs["Emission Strength"].default_value = s
    mat.principled(M["paper"]).inputs["Emission Color"].default_value = (1.0, 0.06, 0.02, 1.0)
    m = M["chain"]                                                       # masked chain-link: BC alpha as opacity
    img = next((n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeTexImage" and n.image and "_BC" in n.image.name), None)
    if img is not None:
        m.node_tree.links.new(img.outputs["Alpha"], mat.principled(m).inputs["Alpha"])


def ground(col, x0, x1, y0, y1, kerb_y=None, side=+1):
    """Wet asphalt with a sidewalk strip: flat stand-ins."""
    asph = mat.flat("Prev_WetAsphalt", (0.035, 0.034, 0.033), 0.12)
    walk = mat.flat("Prev_DampConcrete", (0.11, 0.105, 0.10), 0.32)
    a = geo.box((x1 - x0, y1 - y0, 0.02), bevel=0.0, name="PrevRoad")
    geo.transform(a, loc=((x0 + x1) / 2, (y0 + y1) / 2, -0.02))
    a.data.materials.append(asph)
    scene.link(a, col)
    if kerb_y is not None:
        yy0, yy1 = (kerb_y, y1) if side > 0 else (y0, kerb_y)
        w = geo.box((x1 - x0, yy1 - yy0, 0.15), bevel=0.0, name="PrevWalk")
        geo.transform(w, loc=((x0 + x1) / 2, (yy0 + yy1) / 2, 0.0))
        w.data.materials.append(walk)
        scene.link(w, col)


def lamps(col, pts, watts=1400.0, temp=4000.0, size=90.0):
    for i, p in enumerate(pts):
        L = bpy.data.lights.new("PrevLamp%d" % i, "SPOT")
        L.energy, L.use_temperature, L.temperature = watts, True, temp
        L.spot_size, L.spot_blend, L.shadow_soft_size = math.radians(size * 1.6), 0.6, 0.15
        o = bpy.data.objects.new(L.name, L)
        o.location = p
        o.rotation_euler = (0.0, 0.0, 0.0)
        col.objects.link(o)


def wash(col, p, colour, watts=120.0, size=(3.0, 0.6), facing=(0.0, -1.0, 0.0)):
    from mathutils import Vector
    L = bpy.data.lights.new("PrevWash", "AREA")
    L.shape, L.size, L.size_y, L.energy = "RECTANGLE", size[0], size[1], watts
    h = colour.lstrip("#")
    L.color = tuple((int(h[i:i + 2], 16) / 255.0) ** 2.2 for i in (0, 2, 4))
    o = bpy.data.objects.new("PrevWash", L)
    o.location = p
    o.rotation_euler = Vector(facing).to_track_quat("-Z", "Y").to_euler()
    o.visible_camera = False
    col.objects.link(o)


# ================================================================================================= pictures

def canal_north(ctx, a):
    from assets import facade
    T0 = type(ctx)
    fctx = T0("facade", a)
    facade.build(fctx)
    fctx.kit.hide_render = True
    ctx.kit.hide_render = True
    col = scene.collection("PrevCanal")
    pl = json.load(open(os.path.join(paths.out, "placements", "placements_chinatown.json")))
    n = 0
    for e in pl["instances"]:
        src = ctx.K.get(e["mesh"]) or fctx.K.get(e["mesh"])
        if src is None:
            continue
        sc = e.get("scale", [1.0])[0]
        put(src, e["blender_m"], e["rot_z_deg"], sc, col, e.get("face"))
        n += 1
    ctx.log("canal north: %d instances" % n)
    lit = mat.flat("Prev_RoomLit", (0.2, 0.18, 0.15), 0.8)                     # about 35 % of the upper windows lit (11.3)
    p_ = mat.principled(lit)
    p_.inputs["Emission Color"].default_value = (1.0, 0.78, 0.52, 1.0)
    p_.inputs["Emission Strength"].default_value = 0.4
    rnd = np.random.default_rng(7)
    for o in col.objects:
        if o.data and o.data.name.startswith("SM_Facade_BayWindow") and rnd.random() < 0.35:
            for sl in o.material_slots:
                if sl.material and sl.material.name.startswith("MI_Interior_Dark"):
                    sl.link = "OBJECT"
                    sl.material = lit
    ground(col, -60, 60, 10, 40, kerb_y=29.8, side=+1)
    walk2 = geo.box((120, 5.0, 0.15), bevel=0.0, name="PrevWalkS")
    geo.transform(walk2, loc=(0, 16.5, 0.0))
    walk2.data.materials.append(bpy.data.materials["Prev_DampConcrete"])
    scene.link(walk2, col)
    for i, x in enumerate((-38.0, -34.0, -30.0, -26.0)):                        # the vendor table strip (web z -18.8..-17.8)
        put(ctx.K["SM_Prop_CT_VendorTable"], (x + 0.9, 18.3, 0.15), 0.0, 1.0, col)
        put(ctx.K["SM_Prop_CT_Goods_" + ("Bags", "Caps", "TShirts", "Discs")[i]], (x + 0.9, 18.3, 0.15 + 0.753), 0.0, 1.0, col)
        put(ctx.K["SM_Sign_CT_Placard"], (x + 0.4, 17.95, 0.15 + 0.753), 0.0, 1.0, col,
            ("PlacardBags", "PlacardThree", "PlacardThree", "PlacardCDs")[i])
    put(ctx.K["SM_Prop_CT_MarketUmbrella"], (-31.0, 17.4, 0.15), 0.0, 1.0, col)
    put(ctx.K["SM_Prop_CT_EBike"], (-22.5, 29.2, 0.15), 180.0, 1.0, col)
    render.rig_night(lamp=(-30.0, 21.0, 8.0), extra_lamps=[(-6.0, 21.0, 8.0), (18.0, 21.0, 8.0), (-36.0, 30.4, 8.0), (-12.0, 30.4, 8.0),
                                                       (12.0, 30.4, 8.0)], lamp_watts=1800.0, sky=0.8)
    sun = bpy.data.lights.new("PrevCityGlow", "SUN")                            # the rig's key: cool city glow, no shadow (11.1)
    sun.energy, sun.color, sun.use_shadow = 0.04, (0.56, 0.65, 0.84), False
    so = bpy.data.objects.new("PrevCityGlow", sun)
    so.rotation_euler = (math.radians(55.0), 0.0, math.radians(200.0))
    scene.collection("Rig").objects.link(so)
    for o in bpy.data.objects:
        if o.type == "LIGHT" and o.data.type == "SPOT" and o.name.startswith("Sodium"):
            o.data.temperature = 4000.0
    rig = scene.collection("Rig")
    for e in pl["instances"]:                                                    # sign wash in each sign's glow colour
        if e.get("face") and e["role"] in ("sign band", "blade"):
            from assets import _chinatown_names as names
            F = names.FACES[e["face"]]
            if F.get("glow"):
                x, y, z = e["blender_m"]
                if e["role"] == "sign band":
                    wash(rig, (x + F["w"] / 2, y - 0.6, z + 0.45), F["glow"], 90.0, (F["w"], 0.9), (0, -1, -0.4))
                else:
                    wash(rig, (x, y - 1.0, z + F["h"] / 2), F["glow"], 60.0, (0.6, F["h"]), (0, -1, -0.2))
    render.look(render.VIEW, render.LOOK_NIGHT, 0.2)
    render.cam_look((-43.0, 14.8, 1.75), (-16.0, 33.0, 8.5), lens=20, name="Cam_CanalNorth")


def market(ctx, a):
    ctx.kit.hide_render = True
    col = scene.collection("PrevMarket")
    floor = geo.box((14, 10, 0.02), bevel=0.0, name="PrevFloor")
    geo.transform(floor, loc=(0, 0, -0.02))
    floor.data.materials.append(mat.flat("Prev_Floor", (0.09, 0.085, 0.08), 0.25))
    scene.link(floor, col)
    wall = geo.box((14, 0.2, 5.4), bevel=0.0, name="PrevWall")
    geo.transform(wall, loc=(0, 4.0, 0))
    wall.data.materials.append(mat.flat("Prev_Wall", (0.30, 0.30, 0.28), 0.8))
    scene.link(wall, col)
    K = ctx.K
    for i, x in enumerate((-4.0, -2.0, 0.0)):
        put(K["SM_Prop_CT_StallCounter_2m"], (x, 0.0, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_Produce_Citrus"], (-4.0, -1.55, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_Produce_Greens"], (-2.4, -1.55, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_Produce_Mixed"], (-0.8, -1.55, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_FishCounter"], (3.0, 2.6, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_FishTank"], (5.0, 3.3, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_DryGoods"], (2.0, -1.4, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_StyrofoamBoxes"], (3.9, -0.6, 0.0), 15.0, 1.0, col)
    put(K["SM_Prop_CT_HandTruck"], (4.6, -1.6, 0.0), 200.0, 1.0, col)
    put(K["SM_Prop_CT_HangingScale"], (2.6, 2.3, 1.25), 0.0, 1.0, col)
    put(K["SM_Prop_CT_Tarp"], (-2.0, 0.0, 3.1), 0.0, 1.0, col)
    for x, key in ((-4.8, "StallFruit"), (-2.6, "StallVeg"), (2.3, "StallFish"), (0.2, "StallDry")):
        put(K["SM_Sign_CT_StallBoard"], (x, -0.7, 2.45), 0.0, 1.0, col, key)
    put(K["SM_Sign_CT_Kiosk_1m"], (-5.6, 3.85, 2.4), 0.0, 1.0, col, "ColdRoom")
    for x in (-4.0, -1.0, 2.0, 4.6):
        put(K["SM_Prop_CT_PendantBulb"], (x, -1.5, 2.6), 0.0, 1.0, col)
    render.rig_night(lamp=(0.0, -1.0, 5.2), lamp_watts=500.0, sky=0.3)
    rig = scene.collection("Rig")
    for x in (-4.0, -1.0, 2.0, 4.6):
        L = bpy.data.lights.new("PrevBulb", "POINT")
        L.energy, L.use_temperature, L.temperature, L.shadow_soft_size = 60.0, True, 3600.0, 0.05
        o = bpy.data.objects.new("PrevBulb", L)
        o.location = (x, -1.5, 2.62)
        rig.objects.link(o)
    for x in (-3.0, 2.0):                                                         # fluorescent rects, 5000 K (11.2)
        L = bpy.data.lights.new("PrevTube", "AREA")
        L.shape, L.size, L.size_y, L.energy, L.use_temperature, L.temperature = "RECTANGLE", 1.2, 0.15, 220.0, True, 5000.0
        o = bpy.data.objects.new("PrevTube", L)
        o.location = (x, -2.2, 4.6)
        rig.objects.link(o)
    render.look(render.VIEW, render.LOOK_NIGHT, -0.4)
    render.cam_look((-7.5, -7.2, 2.3), (-0.6, 0.8, 0.9), lens=28, name="Cam_Market")


def street(ctx, a):
    ctx.kit.hide_render = True
    col = scene.collection("PrevStreet")
    ground(col, -16, 16, -10, 6, None)
    wall = geo.box((22, 0.3, 7.0), bevel=0.0, name="PrevWall")
    geo.transform(wall, loc=(0, 4.15, 0))
    wall.data.materials.append(mat.flat("Prev_Brick", (0.16, 0.07, 0.05), 0.85))
    scene.link(wall, col)
    K = ctx.K
    put(K["SM_Sign_CT_Neon_MoonGate"], (-9.5, 4.0, 3.9), 0.0, 1.0, col)
    put(K["SM_Sign_CT_Band_6m"], (-10.4, 3.79, 2.7), 0.0, 1.0, col, "MoonGate")
    put(K["SM_Facade_Shopfront_CT_Wide"], (-10.4, 4.0, 0.0), 0.0, 1.0, col)
    put(K["SM_Sign_CT_Neon_SilverWave"], (-2.5, 4.0, 3.7), 0.0, 1.0, col)
    put(K["SM_Facade_Shopfront_CT_Shut"], (-3.4, 4.0, 0.0), 0.0, 1.0, col)
    put(K["SM_Sign_CT_Arch"], (3.2, 3.8, 3.9), 0.0, 1.0, col, "PlumBlossom")
    put(K["SM_Sign_CT_Blade_6m"], (8.2, 4.0, 2.6), 0.0, 1.0, col, "JadeTeapot")
    put(K["SM_Sign_CT_Kiosk_3m"], (3.7, 3.85, 2.4), 0.0, 1.0, col, "CleverHands")
    put(K["SM_Sign_CT_Neon_Mahjong"], (4.3, 4.0, 5.3), 0.0, 1.0, col)
    put(K["SM_Sign_CT_Poster_B"], (1.0, 3.99, 1.2), 0.0, 1.0, col, "OperaGala")
    put(K["SM_Sign_CT_Board"], (9.6, 3.99, 2.9), 0.0, 1.0, col, "LanternAlley")
    s = put(K["SM_Prop_CT_LanternString_14m"], (-7.0, -1.0, 4.6), 0.0, 1.0, col)
    for hx, hy, hz in getattr(ctx, "lantern_hooks", []):
        put(K["SM_Prop_CT_Lantern"], (-7.0 + hx, -1.0 + hy, 4.6 + hz), 0.0, 1.0, col)
    put(K["SM_Prop_CT_ParkBench"], (-6.0, -4.2, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_CardTable"], (-2.0, -4.0, 0.0), 0.0, 1.0, col)
    for dx, dy in ((-0.6, 0), (0.6, 0), (0, -0.6)):
        put(K["SM_Prop_CT_Stool"], (-2.0 + dx, -4.0 + dy, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_FruitStand"], (-6.5, 1.6, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_EBike"], (1.5, 1.8, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_CardboardBale"], (5.5, 2.8, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_Stanchions"], (6.0, 0.8, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_ChainLinkEdging_3m"], (2.0, -6.0, 0.0), 0.0, 1.0, col)
    put(K["SM_Prop_CT_BasketballHoop"], (10.5, -3.0, 0.0), 180.0, 1.0, col)
    put(K["SM_Prop_CT_Condenser"], (12.5, 2.2, 0.0), 0.0, 1.0, col)
    render.rig_night(lamp=(-3.0, -2.5, 7.5), extra_lamps=[(7.0, -3.0, 7.5)], lamp_watts=1600.0, sky=0.6)
    for o in bpy.data.objects:
        if o.type == "LIGHT" and o.name.startswith("Sodium"):
            o.data.temperature = 4000.0
    rig = scene.collection("Rig")
    wash(rig, (-7.4, 3.0, 3.2), "#ff8fc8", 160.0, (6.0, 1.0), (0, -1, -0.5))
    wash(rig, (-0.7, 3.0, 4.0), "#7fe8ff", 80.0, (3.6, 1.0), (0, -1, -0.5))
    wash(rig, (5.2, 3.0, 4.2), "#8affd0", 80.0, (4.0, 0.8), (0, -1, -0.5))
    render.look(render.VIEW, render.LOOK_NIGHT, -0.3)
    render.cam_look((-1.0, -14.5, 2.6), (0.0, 2.0, 2.6), lens=22, name="Cam_Street")


def render_all(ctx):
    a = ctx.args
    os.makedirs(PV, exist_ok=True)
    only = set(a.only or [])
    want = lambda n: not only or n in only
    from assets import _chinatown_kit as kit
    night_on(ctx.M)
    if want("ct_atlas"):
        cells = json.load(open(os.path.join(paths.texture_set("Sign_CT_Atlas1"), "set.json")))["cells"]
        atlas.preview_sheet(os.path.join(PV, "ct_sign_atlas.jpg"), cells, 1280)
        ctx.log("preview ct_sign_atlas.jpg")
    for name, fn in (("ct_market", market), ("ct_street", street), ("ct_canal_north", canal_north)):
        if not want(name):
            continue
        for c in list(bpy.data.collections):
            if c.name.startswith("Prev") or c.name in ("Rig",):
                for o in list(c.objects):
                    bpy.data.objects.remove(o, do_unlink=True)
        render.setup(samples=a.samples, res=(1280, 720))
        fn(ctx, a)
        _p, sec = render.render_jpeg(os.path.join(PV, name + ".jpg"), a.samples)
        ctx.log("preview %s.jpg %.0fs" % (name, sec))
