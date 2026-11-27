"""Midtown look-dev pictures (art/previews/maps/, 1280 x 720 JPEG, at most 300 kB each), night, from the placements.

    venv/bin/python art/blender/build.py build midtown --preview --samples 12 [--only mt_roofs,mt_gantry,mt_square,mt_faces]

mt_roofs    from the start roof (V1's eye): A's deck, WT-A, the steel stair, C with the tank house under WT-C, the back of the
            C1 billboard, the gantry wall's truss beyond and the screens of the square glowing past the roofs
mt_gantry   from D's roof: the gantry, the back of G1 (cabinets, posts, girts, outriggers), the service bulkhead, the scaffold head
mt_square   from W 46 St: the scaffold stair tower with its netting and contractor board, G1's takeover slide, the C1 lightbox
mt_faces    the screen atlases A and B, the sign atlas and the ticker strip, downscaled
mt_stand    (round 2) from the plaza south of the Stand: the two wings, the front court, the Booth's broken window, the
            amber risers, the kiosk, planters, the generator
mt_plaza    (round 2) from the top of the Stand (V5's eye) south over the plaza: planters, kiosks, carts, cafe tables, the LED
            poles, the barriers, W 46 St beyond
mt_booth    (round 2) inside the Booth from its west door: the desk and monitors, the racks, the slot onto the front court
mt_bar      (round 3) from D's roof toward THE LOFTLARK: the raised deck, the bar, the loungers, planters and folded umbrellas, the
            unlit neon on the east parapet, the duct and vent boxes
mt_set      (round 3) from W 46 St up the plaza: the premiere's trucks, trailers, light and truss towers, press walls, tents, booths,
            the sound tower and the speaker stack
mt_bus      (round 3) from the south end of Broadway: the stalled city bus, the hotel front and its canopy, the theatre's marquee beyond
mt_facade   (round 3) from the plaza: the theatre front and its marquee, the bays and cornice of the east facade, the ticker
mt_street   (round 3) from Seventh Av: C's shopfronts and bands, the hoarding, the bays, the west sidewalk's dressing
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


def paint_mat(rgb):
    """A clear-coat car paint in the placement's `paint` colour (linear RGB): what the MI does with the paint slot's tint mask in Unreal."""
    name = "Prev_Paint_%02d%02d%02d" % tuple(int(round(c * 99)) for c in rgb)
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = mat.flat(name, tuple(rgb), 0.30, 0.25)
    p_ = mat.principled(m)
    for k, v in (("Coat Weight", 0.9), ("Coat Roughness", 0.06)):
        if k in p_.inputs:
            p_.inputs[k].default_value = v
    return m


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
        src = ctx.K.get(e["mesh"]) or (reused(e["mesh"], ctx) if e.get("reused") else None)
        if src is None:
            continue
        ob = scene.duplicate(src, linked=True, col=col)
        scene.place(ob, e["blender_m"], e["rot_z_deg"])
        if e.get("scale"):
            ob.scale = e["scale"]
        ob["mi_placed"] = True
        if e.get("paint"):
            for sl in ob.material_slots:                                  # only the paint slot: the trim and lamps are other M_Vehicle_ slots
                if sl.material and sl.material.name.startswith("M_Vehicle_") and ".Paint" not in sl.material.name and "_Paint" in sl.material.name:
                    sl.link = "OBJECT"
                    sl.material = paint_mat(e["paint"])
        if e.get("face"):
            set_slot(ob, "M_Sign_MT_Face", face_mat(e["face"]))
        if e.get("faces"):                                            # several printed faces in one slot: one cell each, in the order they were made
            ob.data = ob.data.copy()
            me = ob.data
            si = [i for i, m in enumerate(me.materials) if m and m.name.startswith("M_Sign_MT_Face")]
            if si:
                base = len(me.materials)
                for key in e["faces"]:
                    me.materials.append(face_mat(key))
                polys = [p for p in me.polygons if p.material_index == si[0]]
                for i, p in enumerate(polys):
                    p.material_index = base + min(i, len(e["faces"]) - 1)
        if e.get("slide"):
            set_slot(ob, "M_MI_Screen", slide_mat(e["slide"], strength=1.2))
        if e.get("slides"):                                           # N1: one ad per face (the FaceIndex UV)
            ob.data = ob.data.copy()
            me = ob.data
            si = [i for i, m in enumerate(me.materials) if m and m.name.startswith("M_MI_Screen")]
            fi = me.uv_layers.get("FaceIndex")
            if si and fi:
                base = len(me.materials)
                for key in e["slides"]:
                    me.materials.append(slide_mat(key, None, STRENGTH["hero"]))
                for p in me.polygons:
                    if p.material_index == si[0]:
                        k = int(fi.data[p.loop_indices[0]].uv[0])
                        p.material_index = base + min(k, len(e["slides"]) - 1)
        elif e.get("screen") and e.get("first_slide") or e.get("screen") == "G1":
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
               "SM_Roof_Gantry_16m": "Label_HighVoltage", "SM_Roof_ConduitBox_1p4": "Label_HighVoltage"}.get(nm)
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


def window_grid(name, base, lit=(1.0, 0.80, 0.55), share=0.35, cool=False):
    """A stand-in facade with a window grid (1.55 x 3.1 m bays), object coordinates in metres so every stand-in keeps the
    storey height. Round-3 rewrite (review: "flat white window rectangles"): each window now has a frame and a recessed pane, a
    mullion and a transom, a sill and a storey ledge, and its own lighting: about `share` of them lit, each lit one with its own
    brightness (a long tail of dim ones), its own colour (tungsten, warm white, fluorescent, TV blue, a little green), a ceiling
    gradient (brighter at the top of the pane), and blinds (slats), curtains (dark side drapes) or bare glass; unlit panes reflect
    the sky. The wall has low-frequency tint drift and vertical grime. This is the look the Midtown facade material has to match
    (docs/unreal/maps/midtown_art.md, "Facade windows")."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])

    def M(op, a_, b_=None, clamp=False):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation, n.use_clamp = op, clamp
        for i, v in enumerate((a_, b_)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                nt.links.new(v, n.inputs[i])
        return n.outputs[0]

    X = M("ADD", sep.outputs["X"], sep.outputs["Y"])                    # windows run round the corners
    Z = sep.outputs["Z"]
    u = M("FRACT", M("DIVIDE", X, 1.55))
    v = M("FRACT", M("DIVIDE", Z, 3.1))

    def band(t, lo, hi):
        return M("MULTIPLY", M("GREATER_THAN", t, lo), M("LESS_THAN", t, hi))

    win = M("MULTIPLY", band(u, 0.17, 0.83), band(v, 0.14, 0.86))        # the window opening
    pane = M("MULTIPLY", band(u, 0.23, 0.77), band(v, 0.20, 0.80))       # the glass inside the frame
    mullion = M("LESS_THAN", M("ABSOLUTE", M("SUBTRACT", u, 0.5)), 0.018)
    transom = M("LESS_THAN", M("ABSOLUTE", M("SUBTRACT", v, 0.64)), 0.012)
    glass = M("MULTIPLY", pane, M("SUBTRACT", 1.0, M("MAXIMUM", mullion, transom)))
    frame = M("SUBTRACT", win, glass, clamp=True)
    sill = M("MULTIPLY", band(u, 0.13, 0.87), band(v, 0.115, 0.15))
    ledge = band(v, 0.955, 1.0)                                          # the storey line

    # one random number per window, from the snapped position (several channels by offsetting the vector)
    snap = nt.nodes.new("ShaderNodeVectorMath")
    snap.operation = "SNAP"
    snap.inputs[1].default_value = (1.55, 3.1, 1.0)
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(X, comb.inputs["X"])
    nt.links.new(Z, comb.inputs["Y"])
    nt.links.new(comb.outputs[0], snap.inputs[0])

    def rnd(k):
        a_ = nt.nodes.new("ShaderNodeVectorMath")
        a_.operation = "ADD"
        a_.inputs[1].default_value = (17.3 * k, 5.1 * k, 3.7 * k)
        nt.links.new(snap.outputs[0], a_.inputs[0])
        n = nt.nodes.new("ShaderNodeTexWhiteNoise")
        n.noise_dimensions = "3D"
        nt.links.new(a_.outputs[0], n.inputs["Vector"])
        return n.outputs["Value"]

    r_on, r_br, r_col, r_cov = rnd(1), rnd(2), rnd(3), rnd(4)
    on = M("LESS_THAN", r_on, share)
    bright = M("ADD", 0.12, M("MULTIPLY", M("POWER", r_br, 2.2), 0.95))     # a long tail of dim windows
    tone = nt.nodes.new("ShaderNodeValToRGB")
    els = tone.color_ramp.elements
    while len(els) < 5:
        els.new(0.5)
    for e, (pos, c) in zip(els, ((0.0, (1.0, 0.46, 0.16)), (0.32, (1.0, 0.72, 0.42)), (0.58, (1.0, 0.90, 0.78)),
                                 (0.80, (0.62, 0.80, 1.0)), (1.0, (0.30, 0.45, 1.0)))):
        e.position, e.color = pos, (*c, 1.0)
    if cool:                                                                 # office towers: fluorescent whites and blues
        for e, (pos, c) in zip(els, ((0.0, (0.80, 0.90, 1.0)), (0.30, (0.70, 0.84, 1.0)), (0.6, (0.92, 0.96, 1.0)),
                                     (0.85, (1.0, 0.86, 0.66)), (1.0, (0.45, 0.62, 1.0)))):
            e.position, e.color = pos, (*c, 1.0)
    nt.links.new(r_col, tone.inputs["Fac"])
    grad = M("ADD", 0.45, M("MULTIPLY", M("SUBTRACT", v, 0.2), 1.1))          # ceiling light: brighter at the top of the pane
    # coverings: 38 % venetian blinds (slats), 22 % curtains (dark drapes at the sides), the rest bare
    slats = M("GREATER_THAN", M("FRACT", M("MULTIPLY", Z, 22.0)), 0.42)
    blind_sel = M("LESS_THAN", r_cov, 0.38)
    drape_sel = M("MULTIPLY", M("GREATER_THAN", r_cov, 0.38), M("LESS_THAN", r_cov, 0.60))
    drapes = M("GREATER_THAN", M("ABSOLUTE", M("SUBTRACT", u, 0.5)), 0.17)
    cover = M("MULTIPLY", M("SUBTRACT", 1.0, M("MULTIPLY", blind_sel, M("SUBTRACT", 1.0, M("ADD", 0.25, M("MULTIPLY", slats, 0.75)))))
              , M("SUBTRACT", 1.0, M("MULTIPLY", drape_sel, M("MULTIPLY", drapes, 0.8))))
    k = M("MULTIPLY", M("MULTIPLY", M("MULTIPLY", on, glass), M("MULTIPLY", bright, grad)), cover)
    nt.links.new(M("MULTIPLY", k, 1.7), p.inputs["Emission Strength"])
    nt.links.new(tone.outputs["Color"], p.inputs["Emission Color"])

    # wall: tint drift, vertical grime streaks, a lighter stone frame, ledge and sill
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.35
    noise.inputs["Detail"].default_value = 5.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    streak = nt.nodes.new("ShaderNodeTexNoise")
    streak.inputs["Scale"].default_value = 4.0
    streak.inputs["Detail"].default_value = 2.0
    sc = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(M("MULTIPLY", X, 3.0), sc.inputs["X"])
    nt.links.new(M("MULTIPLY", Z, 0.12), sc.inputs["Y"])
    nt.links.new(sc.outputs[0], streak.inputs["Vector"])
    tint = nt.nodes.new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.inputs[6].default_value = (*base, 1.0)
    tint.inputs[7].default_value = (base[0] * 1.9, base[1] * 1.6, base[2] * 1.4, 1.0)
    nt.links.new(M("MULTIPLY", noise.outputs["Fac"], 1.4), tint.inputs[0])
    grime = M("MULTIPLY", M("SUBTRACT", streak.outputs["Fac"], 0.35), 0.9, clamp=True)
    wall = nt.nodes.new("ShaderNodeMix")
    wall.data_type = "RGBA"
    nt.links.new(grime, wall.inputs[0])
    nt.links.new(tint.outputs[2], wall.inputs[6])
    wall.inputs[7].default_value = (base[0] * 0.35, base[1] * 0.35, base[2] * 0.35, 1.0)
    stone = nt.nodes.new("ShaderNodeMix")
    stone.data_type = "RGBA"
    nt.links.new(M("MAXIMUM", sill, ledge), stone.inputs[0])
    nt.links.new(wall.outputs[2], stone.inputs[6])
    stone.inputs[7].default_value = (base[0] * 2.4 + 0.02, base[1] * 2.4 + 0.02, base[2] * 2.4 + 0.02, 1.0)
    fr = nt.nodes.new("ShaderNodeMix")                                       # the frame: dark painted metal
    fr.data_type = "RGBA"
    nt.links.new(M("MAXIMUM", frame, M("MULTIPLY", win, M("MAXIMUM", mullion, transom))), fr.inputs[0])
    nt.links.new(stone.outputs[2], fr.inputs[6])
    fr.inputs[7].default_value = (0.012, 0.012, 0.014, 1.0)
    gl = nt.nodes.new("ShaderNodeMix")                                       # the glass: dark, reflective
    gl.data_type = "RGBA"
    nt.links.new(glass, gl.inputs[0])
    nt.links.new(fr.outputs[2], gl.inputs[6])
    gl.inputs[7].default_value = (0.008, 0.010, 0.016, 1.0)
    nt.links.new(gl.outputs[2], p.inputs["Base Color"])
    rough = M("ADD", M("MULTIPLY", glass, -0.5), 0.78)                       # glass 0.28, wall 0.78
    nt.links.new(rough, p.inputs["Roughness"])
    # relief: the pane sits 8 cm behind the frame, the frame 4 cm behind the wall, ledge and sill stand out
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 0.10
    nt.links.new(M("ADD", M("SUBTRACT", 1.0, M("ADD", M("MULTIPLY", win, 0.4), M("MULTIPLY", glass, 0.6))), M("MULTIPLY", M("MAXIMUM", sill, ledge), 0.5)),
                 bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


def night_dome(strength=0.9):
    """midtown.md 11.1: the 11:52 PM dome, #6a3e5a at the horizon (the square's glow on the haze) to #0b0d18 at the zenith."""
    w = bpy.context.scene.world
    for n in w.node_tree.nodes:
        if n.type == "VALTORGB":
            els = n.color_ramp.elements
            while len(els) > 2:
                els.remove(els[-1])
            els[0].position, els[0].color = 0.0, (0.105, 0.036, 0.078, 1.0)                       # below the horizon: the haze of the glow, no black line
            els[1].position, els[1].color = 1.0, (0.0033, 0.0040, 0.0090, 1.0)     # #0b0d18
            e = els.new(0.02)
            e.color = (0.144, 0.048, 0.102, 1.0)                                      # #6a3e5a
            e = els.new(0.30)
            e.color = (0.016, 0.012, 0.024, 1.0)
        if n.type == "BACKGROUND":
            n.inputs["Strength"].default_value = strength


def reused(name, ctx):
    """A mesh of the Block's kits the square reuses (midtown.md 14.1): its GLB from art/out/glb, imported once, hidden."""
    if name in ctx.K:
        return ctx.K[name]
    man = json.load(open(paths.manifest))["assets"].get(name)
    if not man:
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(paths.out, man["glb"]))
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not new:
        return None
    ob = new[0]
    for o in bpy.data.objects:
        if o not in before and o is not ob:
            bpy.data.objects.remove(o, do_unlink=True)
    ob.matrix_world = ob.matrix_world.Identity(4)
    ob.hide_render = True
    ctx.K[name] = ob
    return ob


def standins(col):
    wall = window_grid("Prev_Mass", (0.07, 0.055, 0.045), share=0.24)
    dark = window_grid("Prev_Tower", (0.035, 0.037, 0.045), share=0.34, cool=True)
    road = mat.flat("Prev_WetAsphalt", (0.03, 0.03, 0.032), 0.15)
    walk = mat.flat("Prev_Pavers", (0.10, 0.10, 0.105), 0.3)
    for k, (x0, x1, z0, z1, h) in {"A": (-50, -30, -38, -12, 21.2), "B": (-50, -30, -12, 8, 17.6), "E": (-50, -30, 8, 22, 14.0),
                                   "C": (-28, -8, -38, -4, 17.6), "D": (-28, -8, -4, 22, 14.0)}.items():
        box(col, "PrevMass" + k, x0 + 0.02, x1 - 0.34 if k in ("C", "D") else x1 - 0.02, 0.0, h - 0.1, z0 + 0.02, z1 - 0.34 if k in ("D", "E") else z1 - 0.02, wall)
    box(col, "PrevCourt", -30, -28, 0.0, 10.4, -38, 22, wall)
    box(col, "PrevRoad", -500, 500, -0.05, 0.0, -500, 500, road)
    box(col, "PrevPlaza", 8, 22, 0.0, 0.15, -38, 22, walk)
    box(col, "PrevWalkW", -8, -4, 0.0, 0.15, -38, 22, walk)
    box(col, "PrevWalkE", 28, 30, 0.0, 0.15, -38, 22, walk)
    box(col, "PrevW46S", -50, 31, 0.0, 0.15, 33.5, 36, walk)
    box(col, "PrevEastFacade", 30.34, 33, 0.0, 30.0, -38, 22, dark)                        # the east facades the screens hang on
    box(col, "PrevEastTower", 33.2, 48, 0.0, 70.0, -32, 16, dark)
    box(col, "PrevSouthFacade", -50, 31, 0.0, 24.0, 36.34, 40, dark)
    box(col, "PrevCornerTower", 26, 48, 0.0, 34.0, 22.5, 36, dark)
    box(col, "PrevNorthTower", 0, 24, 0.0, 60.0, -60, -48.6, dark)
    box(col, "PrevWestTowers", -80, -52, 0.0, 45.0, -60, 40, dark)


def rig(col_rig):
    render.rig_night(lamp=(15.0, 0.0, 9.0), extra_lamps=[(15.0, 18.0, 9.0), (15.0, -18.0, 9.0), (-2.0, -26.0, 8.0), (25.0, 8.0, 8.0)],
                     lamp_watts=1400.0, sky=0.9)
    night_dome(0.9)
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

    def point(name, pos, watts, temp):
        L = bpy.data.lights.new(name, "POINT")
        L.energy, L.use_temperature, L.temperature, L.shadow_soft_size = watts, True, temp, 0.1
        o = bpy.data.objects.new(name, L)
        o.location = pos
        col_rig.objects.link(o)
    point("PrevBooth1", web(13.0, 2.0, -32.0), 60.0, 3600.0)                                        # the booth's 2 points (11.1)
    point("PrevBooth2", web(19.0, 2.0, -32.0), 60.0, 3600.0)
    for i, (x, z) in enumerate(((15.0, -12.0), (15.0, 12.0), (20.0, 16.0), (10.5, 16.0))):         # the plaza poles' heads
        for dx in (-0.9, 0.9):
            spot("PrevPole%d%s" % (i, "ab"[dx > 0]), web(x + dx, 7.5, z), web(x + dx, 0.0, z), 900.0, 4000.0, 110.0)


def rig_extra(col, name):
    """Look-dev lights for one picture only (the real rig's lights are lane L's): the lounge's glow, the light towers' heads, the
    bus's lamps. They stand where the design puts a light and are the picture's, not the art's."""
    from mathutils import Vector

    def spot(nm, pos, target, watts, temp, size=80.0):
        L = bpy.data.lights.new(nm, "SPOT")
        L.energy, L.use_temperature, L.temperature = watts, True, temp
        L.spot_size, L.spot_blend, L.shadow_soft_size = math.radians(size), 0.6, 0.2
        o = bpy.data.objects.new(nm, L)
        o.location = pos
        o.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        col.objects.link(o)
    if name == "mt_bar":
        spot("PrevLounge1", web(-21.5, 19.0, 9.0), web(-22.0, 14.6, 5.0), 1400.0, 2700.0, 95.0)
        spot("PrevLounge2", web(-26.0, 19.0, 0.0), web(-24.0, 14.6, 0.0), 800.0, 3200.0, 95.0)
    if name == "mt_set":
        for (x, z) in ((2.7, 14.3), (-0.9, -25.5), (25.0, -11.0), (21.2, -17.7)):
            spot("PrevLT%d" % int(x * 10), web(x, 6.2, z), web(x + 3.0, 0.15, z + 4.0), 1100.0, 4000.0, 110.0)
    if name == "mt_bus":
        spot("PrevMarquee", web(29.0, 3.4, 6.0), web(26.0, 0.15, 6.0), 900.0, 2800.0, 110.0)
        spot("PrevBusLamp", web(24.0, 6.0, 8.0), web(24.0, 1.0, 4.0), 800.0, 4000.0, 100.0)
    if name == "mt_facade":
        spot("PrevMarqueeA", web(29.0, 3.4, -14.0), web(27.5, 0.15, -14.0), 900.0, 2800.0, 120.0)
    if name == "mt_street":
        spot("PrevShop1", web(-6.0, 4.4, -10.0), web(-5.0, 0.15, -10.0), 700.0, 3200.0, 120.0)
        spot("PrevShop2", web(-6.0, 4.4, -23.0), web(-5.0, 0.15, -23.0), 700.0, 3600.0, 120.0)


def view(name):
    eye, at, lens = {
        "mt_roofs": (web(-32.0, 23.6, -13.5), web(-12.0, 20.0, -27.0), 22.0),
        "mt_gantry": (web(-24.5, 16.0, 19.5), web(-6.0, 18.0, 4.0), 20.0),
        "mt_square": (web(6.0, 1.7, 31.0), web(-6.0, 11.0, 6.0), 20.0),
        "mt_stand": (web(8.4, 1.75, -24.6), web(16.0, 1.9, -29.5), 21.0),
        "mt_plaza": (web(16.0, 5.03, -33.0), web(13.0, 1.0, 0.0), 18.0),
        "mt_booth": (web(10.9, 1.62, -31.8), web(19.5, 1.1, -32.0), 16.0),
        "mt_bar": (web(-19.0, 15.75, 12.0), web(-23.5, 15.0, 4.0), 19.0),
        "mt_set": (web(12.0, 2.7, 23.0), web(10.5, 1.8, -12.0), 18.0),
        "mt_bus": (web(21.0, 1.7, 11.5), web(25.0, 1.7, 2.0), 18.0),
        "mt_facade": (web(26.3, 2.3, -6.6), web(30.0, 5.0, -15.0), 17.0),
        "mt_cars": (web(25.2, 1.7, -19.5), web(25.0, 0.9, -32.0), 24.0),
        "mt_street": (web(-4.2, 1.7, -1.0), web(-8.0, 3.0, -17.0), 20.0),
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
    shots = [n for n in ("mt_roofs", "mt_gantry", "mt_square", "mt_stand", "mt_plaza", "mt_booth", "mt_bar", "mt_set", "mt_bus", "mt_facade",
                         "mt_street", "mt_cars") if want(n)]
    if not shots:
        return
    for key, s in (("sodium", 6.0), ("led", 6.0), ("riser", 0.35), ("warm", 1.2), ("indicator", 1.0), ("bulb", 5.0), ("tail", 3.0),
                   ("neonPink", 0.25), ("neonCyan", 0.25)):
        mat.principled(ctx.M[key]).inputs["Emission Strength"].default_value = s
    ctx.kit.hide_render = True
    col = scene.collection("PrevMidtown")
    place_all(ctx, col)
    standins(col)
    rig(scene.collection("Rig"))
    for name in shots:
        render.setup(samples=a.samples, res=(1280, 720))
        render.look(render.VIEW, render.LOOK_NIGHT, getattr(a, "exposure", None) or 0.7)
        view(name)
        cx = scene.collection("RigExtra_" + name)
        rig_extra(cx, name)
        _p, sec = render.render_jpeg(os.path.join(PV, name + ".jpg"), a.samples)
        cx.hide_render = True
        ctx.log("preview %s.jpg %.0fs" % (name, sec))
