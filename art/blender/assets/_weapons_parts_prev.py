"""Round 4, lane 2: pictures of the parts kit and of the guns with their parts fitted (assembly previews).

Everything is read from the exported files: the guns' GLBs with their baked sets (weapons.import_asset), the parts' GLBs with the
sets Weapon_Parts / Weapon_PartsMags and flat lens and reticle slots, each part placed at the gun's socket of the same name
(the bone head), the hide bones of a fitted part scaled to zero as the game hides them.

    python art/blender/assets/_weapons_parts_prev.py kit|chopper|nine [--samples 64] [--out DIR]
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
for p in (BL, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

from mi import geo, mat, paths, render, rig, scene  # noqa: E402
import weapons as W  # noqa: E402

CONTRACT = os.path.join(HERE, "weapons_parts_contract.json")
SETS = {"M_Part_Hardware": "Weapon_Parts", "M_Part_Mags": "Weapon_PartsMags"}
HIDE = {"optic": {"chopper": ["FrontSight"]}, "muzzle": {"chopper": ["Booster"]}}


def contract():
    return json.load(open(CONTRACT))["parts"]


def part_materials():
    ms = {}
    for slot, sname in SETS.items():
        d = paths.texture_set(sname)
        if os.path.exists(os.path.join(d, "set.json")):
            ms[slot] = mat.from_texture_set(d, name=slot + "_R", masks=False, macro=0.0, ao_strength=0.0, alpha="none")
    g = bpy.data.materials.new("Lens_R")
    nt = g.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfGlass")
    b.inputs["Color"].default_value = (0.55, 0.62, 0.6, 1)
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["IOR"].default_value = 1.05
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    ms["M_Part_Lens"] = g
    r = bpy.data.materials.new("Ret_R")
    nt = r.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    uv = nt.nodes.new("ShaderNodeTexCoord")
    sub = nt.nodes.new("ShaderNodeVectorMath")
    sub.operation = "DISTANCE"
    sub.inputs[1].default_value = (0.5, 0.5, 0.0)
    nt.links.new(uv.outputs["UV"], sub.inputs[0])
    dot = nt.nodes.new("ShaderNodeMath")                     # 1 inside the dot (collimated additive dot)
    dot.operation = "LESS_THAN"
    dot.inputs[1].default_value = 0.05
    nt.links.new(sub.outputs["Value"], dot.inputs[0])
    ring_a = nt.nodes.new("ShaderNodeMath")
    ring_a.operation = "SUBTRACT"
    ring_a.inputs[1].default_value = 0.32
    nt.links.new(sub.outputs["Value"], ring_a.inputs[0])
    ring_b = nt.nodes.new("ShaderNodeMath")
    ring_b.operation = "ABSOLUTE"
    nt.links.new(ring_a.outputs[0], ring_b.inputs[0])
    ring_c = nt.nodes.new("ShaderNodeMath")
    ring_c.operation = "LESS_THAN"
    ring_c.inputs[1].default_value = 0.012
    nt.links.new(ring_b.outputs[0], ring_c.inputs[0])
    mask = nt.nodes.new("ShaderNodeMath")
    mask.operation = "MAXIMUM"
    nt.links.new(dot.outputs[0], mask.inputs[0])
    nt.links.new(ring_c.outputs[0], mask.inputs[1])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (1.0, 0.03, 0.02, 1)
    e.inputs["Strength"].default_value = 8.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mask.outputs[0], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(e.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    ms["M_Part_Reticle"] = r
    return ms


def load_part(pid, mats, at=(0, 0, 0)):
    """Import SM_Part_* (a part id of the contract) and give its slots the materials; returns the object."""
    rec = contract()[pid]
    name = rec["mesh"] if isinstance(pid, str) and pid in contract() else pid
    arm, meshes, _c = rig.import_glb(os.path.join(paths.glb, name + ".glb"), col_name="Part_" + name)
    ob = max(meshes, key=lambda o: len(o.data.vertices))
    for sl in ob.material_slots:
        base = sl.material.name.split(".")[0] if sl.material else ""
        if base in mats:
            sl.material = mats[base]
    ob.location = at
    return ob


def load_gun(key):
    name = {"chopper": "SK_Chopper", "nine": "SK_Nine", "shorty": "SK_Shorty", "stretch": "SK_Stretch", "rattler": "SK_Rattler"}[key]
    arm, meshes = W.import_asset(name)[:2]
    return arm, meshes


def hide_bones(arm, names):
    for n in names:
        pb = arm.pose.bones.get(n)
        if pb is not None:
            pb.scale = (1e-4, 1e-4, 1e-4)
    bpy.context.view_layer.update()


def fit(arm, ob, mount):
    b = arm.data.bones[mount]
    ob.location = arm.matrix_world @ b.head_local
    return ob


def setup(samples, res):
    W.rig_studio(strength=1.25)
    s = render.setup(samples=samples, res=res, threads=1)
    s.cycles.transparent_max_bounces = 12
    return s


def shot(path, loc, tgt, lens=70, res=(1280, 720), samples=64, dof=None):
    cam = render.cam_look(Vector(loc), Vector(tgt), lens, name="Cam", dof=dof)
    cam.data.clip_start = 0.01
    render.render_jpeg(path, samples, res=res)


def assembly(key, fitted, path, view, samples=64, res=(1280, 720), lens=70, look_at=None, dist=None):
    """The gun with the parts `fitted` (part ids), seen from `view` (a direction vector toward the camera, gun space)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup(samples, res)
    arm, meshes = load_gun(key)
    mats = part_materials()
    ct = contract()
    used = []
    for pid in fitted:
        rec = ct[pid]
        ob = load_part(pid, mats)
        fit(arm, ob, rec["gun_socket"])
        used.append(ob)
        if key == "chopper":
            hide_bones(arm, HIDE.get(rec["slot"], {}).get(key, []))
    # the standard magazine of the gun is part of the picture unless an extended one is fitted
    std = {"chopper": "SM_Weapon_ChopperMagazine", "nine": "SM_Weapon_NineMagazine"}.get(key)
    ext = [p for p in fitted if p.startswith("mag_")]
    if std and not ext:
        _a, ms, _c = W.import_asset(std)
    elif ext:
        rec = ct[ext[0]]
        _a, ms, _c = rig.import_glb(os.path.join(paths.glb, rec["top_round_mesh"] + ".glb"), col_name="Top_" + key)
        for o in ms:
            for sl in o.material_slots:
                sl.material = mats["M_Part_Mags"]
            o.location = arm.matrix_world @ arm.data.bones[rec["gun_socket"]].head_local
    pts = []
    for o in bpy.data.objects:
        if o.type == "MESH" and not o.hide_render:
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    P = np.array([tuple(p) for p in pts])
    lo, hi = P.min(0), P.max(0)
    c = Vector(look_at) if look_at else Vector(((lo[0] + hi[0]) / 2, 0.0, (lo[2] + hi[2]) / 2))
    d = Vector(view).normalized()
    right = d.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(d).normalized()
    half_w = max(abs(float(np.dot(P - np.array(c), np.array(right)).min())), abs(float(np.dot(P - np.array(c), np.array(right)).max())))
    half_h = max(abs(float(np.dot(P - np.array(c), np.array(up)).min())), abs(float(np.dot(P - np.array(c), np.array(up)).max())))
    fov_h = 2 * math.atan(18.0 / lens)
    fov_v = 2 * math.atan(18.0 * res[1] / res[0] / lens)
    need = max(half_w / math.tan(fov_h / 2), half_h / math.tan(fov_v / 2)) * 1.12
    shot(path, c + d * (dist or (need + 0.02)), c, lens=lens, res=res, samples=samples)
    return path


def sights(path, samples=48, res=(1280, 720)):
    """The sight pictures: the camera at the eye (SightEye shifted back by the relief of the specification), looking along the
    bore through the optic fitted on the CHOPPER (front sight hidden), left the red dot (relief 0.14, 45 deg), right the 4x
    scope (relief 0.085, 30 deg), in front of a range backdrop with a target."""
    from PIL import Image
    shots = []
    for pid, relief, fov in (("red_dot", 0.14, 45.0), ("scope_4x", 0.085, 30.0)):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        setup(samples, (res[0] // 2, res[1]))
        arm, meshes = load_gun("chopper")
        mats = part_materials()
        ob = load_part(pid, mats)
        rec = contract()[pid]
        fit(arm, ob, rec["gun_socket"])
        hide_bones(arm, ["FrontSight"])
        # a backdrop: a pale wall 12 m ahead with a target, a ground plane
        wall = bpy.data.objects.new("Wall", bpy.data.meshes.new("Wall"))
        bm = __import__("bmesh").new()
        __import__("bmesh").ops.create_grid(bm, x_segments=1, y_segments=1, size=6.0)
        bm.to_mesh(wall.data)
        bm.free()
        bpy.context.scene.collection.objects.link(wall)
        wall.rotation_euler = (0, math.radians(90), 0)
        wall.location = (12.0, 0, 1.5)
        wm = bpy.data.materials.new("WallM")
        nt = wm.node_tree
        nt.nodes.clear()
        o = nt.nodes.new("ShaderNodeOutputMaterial")
        b = nt.nodes.new("ShaderNodeBsdfDiffuse")
        chk = nt.nodes.new("ShaderNodeTexChecker")
        chk.inputs["Scale"].default_value = 6.0
        chk.inputs["Color1"].default_value = (0.55, 0.52, 0.45, 1)
        chk.inputs["Color2"].default_value = (0.30, 0.28, 0.25, 1)
        co = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(co.outputs["Object"], chk.inputs["Vector"])
        nt.links.new(chk.outputs["Color"], b.inputs["Color"])
        nt.links.new(b.outputs[0], o.inputs["Surface"])
        wall.data.materials.append(wm)
        eye = arm.matrix_world @ arm.data.bones[rec["gun_socket"]].head_local + Vector(rec["sockets_m"]["SightEye"]) - Vector((relief, 0, 0))
        cam = render.cam_look(eye, eye + Vector((1, 0, 0)), 50.0, name="CamEye")
        cam.data.sensor_fit = "VERTICAL"
        cam.data.angle_y = math.radians(fov)
        cam.data.clip_start = 0.005
        path_i = path + "_%s.jpg" % pid
        render.render_jpeg(path_i, samples, res=(res[0] // 2, res[1]))
        shots.append(path_i)
    ims = [Image.open(p_).convert("RGB") for p_ in shots]
    sheet = Image.new("RGB", (res[0], res[1]))
    for i, im in enumerate(ims):
        sheet.paste(im, (i * (res[0] // 2), 0))
    render.save_jpeg(sheet, path, 300)
    for p_ in shots:
        os.remove(p_)


def kit(path, samples=64, res=(1280, 720)):
    """Every part on a plain background in a flat side view, three groups: the optics and muzzle devices (top row), the grips and
    the laser (second row), the three magazines with their top rounds (right, standing). Labelled by position."""
    from PIL import Image, ImageDraw, ImageFont
    from bpy_extras.object_utils import world_to_camera_view
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup(samples, res)
    mats = part_materials()
    ct = contract()
    width = 0.90                                              # metres across the frame
    layout = [("red_dot", 0.02, 0.32), ("scope_4x", 0.12, 0.32), ("suppressor", 0.30, 0.32), ("compensator", 0.54, 0.32),
              ("suppressor_pistol", 0.02, 0.17), ("foregrip_vertical", 0.21, 0.17), ("foregrip_vertical_wood", 0.30, 0.17),
              ("foregrip_angled", 0.40, 0.17), ("laser_module", 0.52, 0.17),
              ("mag_ext_rifle", 0.65, 0.30), ("mag_ext_smg", 0.73, 0.30), ("mag_ext_pistol", 0.81, 0.30)]
    placed = {}
    for pid, x0, ztop in layout:
        ob = load_part(pid, mats)
        lo, hi = scene.bounds(ob)
        ob.location = (x0 - width / 2 - lo[0], 0.0, ztop - hi[2])
        placed[pid] = ob
        rec = ct[pid]
        if rec.get("top_round_mesh"):
            _a, ms, _c = rig.import_glb(os.path.join(paths.glb, rec["top_round_mesh"] + ".glb"), col_name="Top_" + pid)
            for o in ms:
                for sl in o.material_slots:
                    sl.material = mats["M_Part_Mags"]
                o.location = ob.location
    s = bpy.context.scene
    cam = render.cam_look(Vector((0.0, -2.0, 0.17)), Vector((0.0, 0.0, 0.17)), 50.0, name="CamKit")
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = width
    cam.data.clip_start, cam.data.clip_end = 0.1, 6.0
    cam.data.shift_y = 0.0
    out, _sec = render.render_jpeg(path, samples, res=res)
    im = Image.open(out).convert("RGB")
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    except OSError:
        f = ImageFont.load_default()
    names = {"red_dot": "RED DOT", "scope_4x": "4X SCOPE", "suppressor": "SUPPRESSOR", "compensator": "COMPENSATOR",
             "suppressor_pistol": "PISTOL SUPPRESSOR", "foregrip_vertical": "VERTICAL GRIP", "foregrip_vertical_wood": "WOOD GRIP (CHOPPER)",
             "foregrip_angled": "ANGLED GRIP", "laser_module": "LASER", "mag_ext_rifle": "RIFLE MAG", "mag_ext_smg": "SMG MAG",
             "mag_ext_pistol": "NINE MAG"}
    for pid, ob in placed.items():
        lo, hi = scene.bounds(ob, world=True)
        p = world_to_camera_view(s, cam, Vector(((lo[0] + hi[0]) / 2, 0.0, lo[2] - 0.004)))
        x, y = p.x * res[0], (1 - p.y) * res[1]
        txt = names[pid]
        w = d.textlength(txt, font=f)
        y += (22 if pid in ("foregrip_vertical_wood", "laser_module", "mag_ext_smg") else 0)
        d.rectangle([x - w / 2 - 4, y - 2, x + w / 2 + 4, y + 19], fill=(0, 0, 0))
        d.text((x - w / 2, y), txt, fill=(235, 235, 235), font=f)
    render.save_jpeg(im, path, 300)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "kit"
    out = os.environ.get("OUT", paths.previews)
    samples = int(os.environ.get("SAMPLES", "64"))
    if what == "kit":
        kit(os.path.join(out, "weapons_parts_kit.jpg"), samples)
    elif what == "sights":
        sights(os.path.join(out, "weapons_parts_sights.jpg"), samples)
    elif what == "chopper":
        assembly("chopper", ["scope_4x", "suppressor", "foregrip_vertical_wood"], os.path.join(out, "weapons_chopper_built.jpg"),
                 (0.55, -0.85, 0.30), samples, (1280, 720), lens=60)
    elif what == "nine":
        assembly("nine", ["laser_module", "suppressor_pistol", "mag_ext_pistol"], os.path.join(out, "weapons_nine_built.jpg"),
                 (0.35, -0.9, 0.25), samples, (1280, 720), lens=70)
