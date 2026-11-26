"""Midtown look-dev pictures (art/previews/maps/, 1280 x 720 JPEG, at most 300 kB each), night, from the placements.

    venv/bin/python art/blender/build.py build midtown --preview --samples 12 [--only mt_roofs,mt_gantry,mt_square,mt_faces]

mt_roofs    from the start roof (V1's eye): A's deck, WT-A, the steel stair, C with the tank house under WT-C, the back of the
            C1 billboard, the gantry wall's truss beyond and the screens of the square glowing past the roofs
mt_gantry   from D's roof: the gantry, the back of G1 (cabinets, posts, girts, outriggers), the service bulkhead, the scaffold head
mt_square   from W 46 St: the scaffold stair tower with its netting and contractor board, G1's takeover slide, the C1 lightbox
mt_faces    the screen atlases A and B, the sign atlas and the ticker strip, downscaled
Stand-ins (not this lane's art, flat and dark): the building masses below the roofs, the east and south facades and the towers
the screens hang on, the street and the plaza. The real ones are the facade kit and the street kit, with the night rig in Unreal.
"""
import json
import math
import os

import bpy

from assets import _midtown_atlas as atlas
from mi import geo, mat, paths, render, scene

PV = os.path.join(paths.previews, "maps")
STRENGTH = {"hero": 5.0, "screen": 3.2, "lightbox": 2.2}


def web(x, y, z):
    return (x, -z, y)


def _img(path):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = "sRGB"
    return im


def cell_material(name, image_path, uv, sub=None, strength=3.0, base=None, rough=0.6):
    """Emission (and base colour) from one atlas cell over 0..1 UVs; sub = (col, row, cols, rows) picks a tile's piece."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    u0, v0, u1, v1 = uv
    du, dv = u1 - u0, v1 - v0
    loc, scl = (u0, v0), (du, dv)
    if sub:
        c, r, nc, nr = sub
        loc, scl = (u0 + du * c / nc, v0 + dv * r / nr), (du / nc, dv / nr)
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    uvn = nt.nodes.new("ShaderNodeUVMap")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (loc[0], loc[1], 0.0)
    mp.inputs["Scale"].default_value = (scl[0], scl[1], 1.0)
    nt.links.new(uvn.outputs[0], mp.inputs[0])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = _img(image_path)
    t.extension = "EXTEND"
    nt.links.new(mp.outputs[0], t.inputs[0])
    nt.links.new(t.outputs["Color"], p.inputs["Emission Color"])
    if base:
        tb = nt.nodes.new("ShaderNodeTexImage")
        tb.image = _img(base)
        tb.extension = "EXTEND"
        nt.links.new(mp.outputs[0], tb.inputs[0])
        nt.links.new(tb.outputs["Color"], p.inputs["Base Color"])
    else:
        p.inputs["Base Color"].default_value = (0.01, 0.01, 0.012, 1.0)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Emission Strength"].default_value = strength
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


def slide_mat(key, sub=None, strength=3.0):
    for p in ("A", "B"):
        info = json.load(open(os.path.join(paths.texture_set("MT_Screens_" + p), "set.json")))
        if key in info["cells"]:
            img = os.path.join(paths.texture_set("MT_Screens_" + p), "T_MT_Screens_%s_E.png" % p)
            nm = "Prev_Slide_%s%s" % (key, "" if not sub else "_%d_%d" % (sub[0], sub[1]))
            return cell_material(nm, img, info["cells"][key]["uv"], sub, strength)
    raise KeyError(key)


def face_mat(key):
    d = paths.texture_set("Sign_MT_Atlas1")
    c = json.load(open(os.path.join(d, "set.json")))["cells"][key]
    return cell_material("Prev_Face_" + key, os.path.join(d, "T_Sign_MT_Atlas1_E.png"), c["uv"], None,
                         STRENGTH["lightbox"] if c["lit"] else 0.0, base=os.path.join(d, "T_Sign_MT_Atlas1_BC.png"), rough=0.4)


def set_slot(ob, slot_name, m):
    for sl in ob.material_slots:
        if sl.material and sl.material.name.startswith(slot_name):
            sl.link = "OBJECT"
            sl.material = m


def ticker_mat(i):
    d = paths.texture_set("MT_Ticker")
    info = json.load(open(os.path.join(d, "set.json")))
    per = info["u_per_band"] / 6.0
    return cell_material("Prev_Ticker_%d" % i, os.path.join(d, "T_MT_Ticker_E.png"), (0.1 + i * per, 0.0, 0.1 + (i + 1) * per, 1.0),
                         None, STRENGTH["screen"])


def place_all(ctx, col):
    pl = json.load(open(os.path.join(paths.out, "placements", "placements_midtown.json")))
    n = 0
    for e in pl["instances"]:
        src = ctx.K.get(e["mesh"])
        if src is None:
            continue
        ob = scene.duplicate(src, linked=True, col=col)
        scene.place(ob, e["blender_m"], e["rot_z_deg"])
        if e.get("scale"):
            ob.scale = e["scale"]
        ob["mi_placed"] = True
        if e.get("face"):
            set_slot(ob, "M_Sign_MT_Face", face_mat(e["face"]))
        if e.get("screen"):
            sid = e["screen"]
            hero = sid in ("G1", "E1", "E3", "N1")
            key = {"G1": "G1_Takeover"}.get(sid, e.get("first_slide"))
            sub = None
            if e.get("tile"):
                sub = (e["tile"][0], e["tile"][1], e["tiles"][0], e["tiles"][1])
            set_slot(ob, "M_MI_Screen", slide_mat(key, sub, STRENGTH["hero" if hero else "screen"]))
        if e["mesh"] == "SM_Sign_Ticker_4m":
            set_slot(ob, "M_MT_Ticker", ticker_mat(e.get("module", 0)))
        n += 1
    # the labels on the doors and cabinets
    for o in col.objects:
        nm = o.data.name if o.data else ""
        key = {"SM_Roof_Bulkhead_4x4": "Label_RoofDoor", "SM_Roof_Bulkhead_5x6": "Label_RoofDoor",
               "SM_Roof_MachineRoom_6x6": "Label_MachineRoom", "SM_Roof_TankHouse_6x6": "Label_HighVoltage",
               "SM_Roof_HVAC_RTU_L": "Label_HighVoltage", "SM_Roof_HVAC_RTU_M": "Label_HighVoltage",
               "SM_Roof_Gantry_16m": "Label_HighVoltage"}.get(nm)
        if key:
            set_slot(o, "M_Sign_MT_Face", face_mat(key))
    ctx.log("placed %d instances" % n)
    return pl


def box(col, name, x0, x1, y0, y1, z0, z1, m):
    """A stand-in box between web coordinates (x0..x1, y0..y1 height, z0..z1)."""
    o = geo.box((x1 - x0, z1 - z0, y1 - y0), bevel=0.0, name=name)
    geo.transform(o, loc=((x0 + x1) / 2, -(z0 + z1) / 2, y0))
    o.data.materials.append(m)
    scene.link(o, col)
    return o


def standins(col):
    wall = mat.flat("Prev_Mass", (0.07, 0.055, 0.045), 0.85)
    dark = mat.flat("Prev_Tower", (0.035, 0.037, 0.045), 0.6)
    road = mat.flat("Prev_WetAsphalt", (0.03, 0.03, 0.032), 0.15)
    walk = mat.flat("Prev_Pavers", (0.10, 0.10, 0.105), 0.3)
    for k, (x0, x1, z0, z1, h) in {"A": (-50, -30, -38, -12, 21.2), "B": (-50, -30, -12, 8, 17.6), "E": (-50, -30, 8, 22, 14.0),
                                   "C": (-28, -8, -38, -4, 17.6), "D": (-28, -8, -4, 22, 14.0)}.items():
        box(col, "PrevMass" + k, x0 + 0.02, x1 - 0.02, 0.0, h - 0.1, z0 + 0.02, z1 - 0.02, wall)
    box(col, "PrevCourt", -30, -28, 0.0, 10.4, -38, 22, wall)
    box(col, "PrevRoad", -60, 60, -0.05, 0.0, -60, 50, road)
    box(col, "PrevPlaza", 8, 22, 0.0, 0.15, -38, 22, walk)
    box(col, "PrevWalkW", -8, -4, 0.0, 0.15, -38, 22, walk)
    box(col, "PrevWalkE", 28, 30, 0.0, 0.15, -38, 22, walk)
    box(col, "PrevW46S", -50, 31, 0.0, 0.15, 33.5, 36, walk)
    box(col, "PrevEastFacade", 30, 33, 0.0, 30.0, -38, 22, dark)                        # the east facades the screens hang on
    box(col, "PrevEastTower", 33.2, 48, 0.0, 70.0, -32, 16, dark)
    box(col, "PrevSouthFacade", -50, 31, 0.0, 24.0, 36.5, 40, dark)
    box(col, "PrevCornerTower", 26, 48, 0.0, 34.0, 22.5, 36, dark)
    box(col, "PrevNorthTower", 0, 24, 0.0, 60.0, -60, -48.6, dark)
    box(col, "PrevWestTowers", -80, -52, 0.0, 45.0, -60, 40, dark)


def rig(col_rig):
    render.rig_night(lamp=(15.0, 0.0, 9.0), extra_lamps=[(15.0, 18.0, 9.0), (15.0, -18.0, 9.0), (-2.0, -26.0, 8.0), (25.0, 8.0, 8.0)],
                     lamp_watts=1400.0, sky=3.0)
    for o in bpy.data.objects:                                       # the plaza poles are 4000 K LED (11.1)
        if o.type == "LIGHT" and o.name.startswith("Sodium"):
            o.data.temperature = 4000.0
    sun = bpy.data.lights.new("PrevSquareGlow", "SUN")              # the key: the square's glow from the east, 22 degrees up
    sun.energy, sun.color, sun.angle = 0.22, (0.79, 0.76, 1.0), math.radians(6.0)
    so = bpy.data.objects.new("PrevSquareGlow", sun)
    so.rotation_euler = (math.radians(90.0 - 22.0), 0.0, math.radians(90.0))
    col_rig.objects.link(so)

    def spot(name, pos, target, watts, temp, size=70.0):
        from mathutils import Vector
        L = bpy.data.lights.new(name, "SPOT")
        L.energy, L.use_temperature, L.temperature = watts, True, temp
        L.spot_size, L.spot_blend, L.shadow_soft_size = math.radians(size), 0.5, 0.15
        o = bpy.data.objects.new(name, L)
        o.location = pos
        o.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        col_rig.objects.link(o)

    spot("PrevTankFlood", web(-19.0, 20.2, -28.3), web(-19.0, 17.6, -24.0), 900.0, 2200.0, 100.0)     # roof work lights
    spot("PrevDoorFlood", web(-9.5, 16.3, 3.6), web(-10.0, 14.0, 1.0), 700.0, 2200.0, 100.0)
    spot("PrevBulkheadB", web(-41.8, 20.0, 3.5), web(-40.0, 17.6, 3.5), 500.0, 2200.0, 100.0)
    spot("PrevBridge", web(-31.0, 16.6, 17.0), web(-29.0, 14.0, 17.0), 400.0, 2200.0, 100.0)

    def rect(name, pos, facing, size, colour, watts):
        from mathutils import Vector
        L = bpy.data.lights.new(name, "AREA")
        L.shape, L.size, L.size_y, L.energy, L.color = "RECTANGLE", size[0], size[1], watts, colour
        o = bpy.data.objects.new(name, L)
        o.location = pos
        o.rotation_euler = Vector(facing).to_track_quat("-Z", "Y").to_euler()
        o.visible_camera = False
        col_rig.objects.link(o)
    rect("PrevG1", web(-3.9, 20.7, 6.0), (1, 0, -0.15), (9.0, 16.0), (0.85, 0.85, 0.9), 2500.0)       # 4 rect lights (11.1)
    rect("PrevE1", web(32.6, 19.0, -18.0), (-1, 0, -0.1), (18.0, 24.0), (0.45, 0.40, 0.95), 4000.0)
    rect("PrevE3", web(30.0, 20.0, 21.5), (-1, 1, -0.1), (12.0, 18.0), (0.6, 0.6, 0.9), 2500.0)
    rect("PrevN1", web(12.0, 35.0, -47.0), (0, -1, -0.1), (14.0, 26.0), (0.85, 0.85, 0.9), 3000.0)


def view(name):
    eye, at, lens = {
        "mt_roofs": (web(-32.0, 23.6, -13.5), web(-12.0, 20.0, -27.0), 22.0),
        "mt_gantry": (web(-24.5, 16.0, 19.5), web(-6.0, 18.0, 4.0), 20.0),
        "mt_square": (web(6.0, 1.7, 31.0), web(-6.0, 11.0, 6.0), 20.0),
    }[name]
    render.cam_look(eye, at, lens=lens, name="Cam_" + name)


def render_all(ctx):
    a = ctx.args
    os.makedirs(PV, exist_ok=True)
    only = set(a.only or [])
    want = lambda n: not only or n in only
    if want("mt_faces"):
        atlas.preview_sheet(os.path.join(PV, "mt_faces.jpg"), 1280)
        ctx.log("preview mt_faces.jpg")
    shots = [n for n in ("mt_roofs", "mt_gantry", "mt_square") if want(n)]
    if not shots:
        return
    for key, s in (("sodium", 6.0), ("led", 8.0)):
        mat.principled(ctx.M[key]).inputs["Emission Strength"].default_value = s
    ctx.kit.hide_render = True
    col = scene.collection("PrevMidtown")
    place_all(ctx, col)
    standins(col)
    rig(scene.collection("Rig"))
    for name in shots:
        render.setup(samples=a.samples, res=(1280, 720))
        render.look(render.VIEW, render.LOOK_NIGHT, getattr(a, "exposure", None) or 1.6)
        view(name)
        _p, sec = render.render_jpeg(os.path.join(PV, name + ".jpg"), a.samples)
        ctx.log("preview %s.jpg %.0fs" % (name, sec))
