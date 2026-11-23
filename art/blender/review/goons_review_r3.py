"""Independent review renders of the exported Goons (critique round 3). Reads only the exports (art/out/glb/SK_Goon_*.glb
and their texture sets), wires the maps the way Unreal's M_Goon*_* materials do (BC, ORM: G roughness / B metallic, N;
Cloth shading emulated: sheen = saturate((rough-0.55)*3.3)*0.8 tinted BC*0.9+0.01 (r3), specular 0.30, tiling fibre detail normal), poses with Epic's clips and lights with the README's day rig. One shot per process.

    python art/blender/review/goons_review_r3.py --shot <name> [--samples 64]
    python art/blender/review/goons_review_r3.py --list

Outputs art/blender/review/sheets/goons_r3/<shot>.jpg (1280 x 720).
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
from mathutils import Vector  # noqa: E402

from mi import char, render, rig  # noqa: E402

OUT = os.path.join(HERE, "sheets", "goons_r3")
GLB = os.path.join(ROOT, "art", "out", "glb")
TEX = os.path.join(ROOT, "art", "out", "textures")
POSES = {"aim": ("rifle_idle_ads", 0.5), "jog": ("rifle_jog_fwd", 0.25), "death": ("death_front", 0.45)}

# shot: list of (outfit, pose, x, y, yaw deg), camera (distance m, azimuth deg from -Y, height m, target height m, lens)
SHOTS = {}
for o in ("Hoodie", "Puffer", "Tracksuit"):
    SHOTS["%s_1m_aim" % o.lower()] = ([(o, "aim", 0, 0, 0)], (1.0, -20, None, None, 35))
    SHOTS["%s_3m_jog" % o.lower()] = ([(o, "jog", 0, 0, 0)], (3.0, 30, 1.2, 0.92, 32))
    SHOTS["%s_3m_death" % o.lower()] = ([(o, "death", 0, 0, 0)], (3.0, 60, 1.5, 0.5, 32))
SHOTS["lineup_8m_aim"] = ([("Puffer", "aim", -1.4, 0, 0), ("Hoodie", "aim", 0, 0, 0), ("Tracksuit", "aim", 1.4, 0, 0)],
                          (8.0, 20, 1.65, 1.0, 24))
SHOTS["lineup_8m_mixed"] = ([("Puffer", "jog", -1.6, 0.6, 20), ("Hoodie", "death", 0, 0, -10), ("Tracksuit", "jog", 1.6, -0.5, 30)],
                          (8.0, -25, 1.65, 1.0, 24))
SHOTS["hoodie_1m_hood_side"] = ([("Hoodie", "aim", 0, 0, 0)], (1.0, 100, None, None, 35))


META = json.load(open(os.path.join(ROOT, "art", "out", "goons", "goons_ue.json")))
DETAIL = os.path.join(TEX, "GoonFabric_Detail", "T_GoonFabric_Detail_N.png")


def wire(mat, set_name):
    d = os.path.join(TEX, set_name)
    nt = mat.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    L = nt.links.new
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    L(b.outputs[0], out.inputs["Surface"])
    b.inputs["Specular IOR Level"].default_value = 0.30
    mat.use_backface_culling = False

    def img(path, data, vec=None):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(path, check_existing=True)
        t.image.colorspace_settings.name = "Non-Color" if data else "sRGB"
        if vec is not None:
            L(vec, t.inputs["Vector"])
        return t
    P = lambda tag: os.path.join(d, "T_%s_%s.png" % (set_name, tag))
    bc, n, orm = img(P("BC"), False), img(P("N"), True), img(P("ORM"), True)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    L(orm.outputs["Color"], sep.inputs[0])
    L(bc.outputs["Color"], b.inputs["Base Color"])
    L(sep.outputs["Green"], b.inputs["Roughness"])
    L(sep.outputs["Blue"], b.inputs["Metallic"])
    # cloth amount = saturate((rough - 0.55) * 3.3) * 0.8
    m1 = nt.nodes.new("ShaderNodeMath"); m1.operation = "SUBTRACT"; m1.inputs[1].default_value = 0.55
    L(sep.outputs["Green"], m1.inputs[0])
    m2 = nt.nodes.new("ShaderNodeMath"); m2.operation = "MULTIPLY"; m2.inputs[1].default_value = 3.3; m2.use_clamp = True
    L(m1.outputs[0], m2.inputs[0])
    cl = nt.nodes.new("ShaderNodeMath"); cl.operation = "MULTIPLY"; cl.inputs[1].default_value = 0.8
    L(m2.outputs[0], cl.inputs[0])
    L(cl.outputs[0], b.inputs["Sheen Weight"])
    b.inputs["Sheen Roughness"].default_value = 0.5
    tint = nt.nodes.new("ShaderNodeVectorMath"); tint.operation = "MULTIPLY_ADD"
    L(bc.outputs["Color"], tint.inputs[0]); tint.inputs[1].default_value = (0.9, 0.9, 0.9); tint.inputs[2].default_value = (0.01, 0.01, 0.01)
    L(tint.outputs[0], b.inputs["Sheen Tint"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    L(n.outputs["Color"], nm.inputs["Color"])
    nrm = nm.outputs["Normal"]
    if os.path.exists(DETAIL):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        t = float(META.get(set_name, {}).get("detail_tiling", 160.0))
        mp.inputs["Scale"].default_value = (t, t, 1)
        L(tc.outputs["UV"], mp.inputs["Vector"])
        dn = img(DETAIL, True, mp.outputs["Vector"])
        dnm = nt.nodes.new("ShaderNodeNormalMap")
        L(dn.outputs["Color"], dnm.inputs["Color"])
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sub = nt.nodes.new("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"
        L(dnm.outputs["Normal"], sub.inputs[0]); L(geo.outputs["Normal"], sub.inputs[1])
        sc = nt.nodes.new("ShaderNodeVectorMath"); sc.operation = "SCALE"
        L(sub.outputs[0], sc.inputs[0]); L(cl.outputs[0], sc.inputs["Scale"])
        ad = nt.nodes.new("ShaderNodeVectorMath"); ad.operation = "ADD"
        L(nrm, ad.inputs[0]); L(sc.outputs[0], ad.inputs[1])
        no = nt.nodes.new("ShaderNodeVectorMath"); no.operation = "NORMALIZE"
        L(ad.outputs[0], no.inputs[0])
        nrm = no.outputs[0]
    L(nrm, b.inputs["Normal"])


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
