"""Independent review renders of the exported Goons (critique round 1). Reads only the exports (art/out/glb/SK_Goon_*.glb
and their texture sets), wires the maps the way Unreal's M_Goon*_* materials do (BC, ORM: G roughness / B metallic, N;
no sheen, no AO multiply), poses with Epic's clips and lights with the README's day rig. One shot per process.

    python art/blender/review/goons_review_r1.py --shot <name> [--samples 64]
    python art/blender/review/goons_review_r1.py --list

Outputs art/blender/review/sheets/goons_r1/<shot>.jpg (1280 x 720).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(BL))
sys.path.insert(0, BL)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from mi import char, render, rig  # noqa: E402

OUT = os.path.join(HERE, "sheets", "goons_r1")
GLB = os.path.join(ROOT, "art", "out", "glb")
TEX = os.path.join(ROOT, "art", "out", "textures")
POSES = {"aim": ("rifle_idle_ads", 0.5), "jog": ("rifle_jog_fwd", 0.25), "death": ("death_front", 0.45)}

# shot: list of (outfit, pose, x, y, yaw deg), camera (distance m, azimuth deg from -Y, height m, target height m, lens)
SHOTS = {}
for o in ("Hoodie", "Puffer", "Tracksuit"):
    SHOTS["%s_1m_aim" % o.lower()] = ([(o, "aim", 0, 0, 0)], (1.0, -5, None, None, 35))
    SHOTS["%s_3m_jog" % o.lower()] = ([(o, "jog", 0, 0, 0)], (3.0, 30, 1.2, 0.92, 32))
    SHOTS["%s_3m_death" % o.lower()] = ([(o, "death", 0, 0, 0)], (3.0, 60, 1.5, 0.5, 32))
SHOTS["lineup_8m_aim"] = ([("Puffer", "aim", -1.4, 0, 0), ("Hoodie", "aim", 0, 0, 0), ("Tracksuit", "aim", 1.4, 0, 0)],
                          (8.0, 20, 1.65, 1.0, 24))
SHOTS["lineup_8m_jog"] = ([("Puffer", "jog", -1.6, 0.6, 20), ("Hoodie", "jog", 0, 0, -10), ("Tracksuit", "jog", 1.6, -0.5, 30)],
                          (8.0, -25, 1.65, 1.0, 24))
SHOTS["hoodie_1m_hood_side"] = ([("Hoodie", "aim", 0, 0, 0)], (1.0, 100, None, None, 35))


def wire(mat, set_name):
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


def load(outfit, x, y, yaw):
    arm, meshes, col = rig.import_glb(os.path.join(GLB, "SK_Goon_%s.glb" % outfit), "G_" + outfit)
    for m in meshes:
        for s in m.material_slots:
            mat = s.material
            if mat is None:
                continue
            kind = "Head" if "Head" in mat.name else "Cloth"
            sn = "Goon%s_%s" % (outfit, kind)
            if os.path.exists(os.path.join(TEX, sn, "T_%s_BC.png" % sn)) and not mat.get("_wired"):
                wire(mat, sn)
                mat["_wired"] = 1
    print("REVIEW mats", outfit, [s.material.name for m in meshes for s in m.material_slots if s.material])
    return arm, meshes


def pose(arm, key):
    clip, frac = POSES[key]
    src, act, rng = char.import_clip(clip)
    f = int(round(rng[0] + (rng[1] - rng[0]) * frac))
    bpy.context.scene.frame_set(f)
    loc, rot = arm.location.copy(), arm.rotation_euler.copy()
    arm.location, arm.rotation_euler = (0, 0, 0), (0, 0, 0)
    char.pose_from_armature(arm, src)
    arm.location, arm.rotation_euler = loc, rot
    for o in list(bpy.data.objects):
        if o.name.startswith("Clip_"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()


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


def head_pos(arm):
    M = arm.matrix_world
    return (M @ arm.pose.bones["head"].matrix).to_translation(), (M @ arm.pose.bones["spine_05"].matrix).to_translation()


def main():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if "--list" in a:
        print("\n".join(SHOTS))
        return
    shot = a[a.index("--shot") + 1]
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 64
    bpy.ops.wm.read_factory_settings(use_empty=True)
    figs, (dist, az, ch, th, lens) = SHOTS[shot]
    arms = []
    for o, p, x, y, yaw in figs:
        arm, meshes = load(o, x, y, yaw)
        pose(arm, p)
        arm.location = (x, y, 0)
        arm.rotation_euler = (0, 0, math.radians(yaw))
        arms.append(arm)
    bpy.context.view_layer.update()
    ground()
    if ch is None:   # head and shoulders: aim at the point between the head and the upper chest
        h, sp = head_pos(arms[0])
        tgt = (h * 0.6 + sp * 0.4)
        tgt = Vector((tgt.x, tgt.y, tgt.z + 0.03))
        ch_ = tgt.z + 0.05
    else:
        tgt = Vector((0, 0, th))
        ch_ = ch
    d = Vector((math.sin(math.radians(az)), -math.cos(math.radians(az)), 0))
    horiz = math.sqrt(max(dist ** 2 - (ch_ - tgt.z) ** 2, 0.01))
    loc = Vector((tgt.x, tgt.y, 0)) + d * horiz
    loc.z = ch_
    render.cam_look(tuple(loc), tuple(tgt), lens)
    render.setup(samples=samples, res=(1280, 720), threads=3)
    rr = render.rig_day(sun_azimuth=225.0)
    print("REVIEW rig", {k: v for k, v in rr.items() if k in ("hdri", "exposure", "sun_elevation")})
    os.makedirs(OUT, exist_ok=True)
    p, t = render.render_jpeg(os.path.join(OUT, shot + ".jpg"), samples, (1280, 720), max_kb=420)
    # height check on the rest pose would need another process; report the posed head height instead
    print("REVIEW done %s %.0fs" % (p, t))


if __name__ == "__main__":
    main()
