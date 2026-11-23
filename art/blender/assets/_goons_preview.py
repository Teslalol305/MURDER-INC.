"""Pictures of the Goons (art/previews/goons_*.jpg, 1280 x 720): lineup, hoodie hero, detail (hood, mask, hands),
poses (jog, aim, death from Epic's clips in art/out/epic), wire. MI_PREVIEWS=name,... picks pictures."""
import os
import tempfile

import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import char, paths, render, scene

ALL = ("goons_lineup", "goons_hoodie_hero", "goons_detail", "goons_poses", "goons_wire")


def wanted():
    env = os.environ.get("MI_PREVIEWS")
    return env.split(",") if env else list(ALL)


def instance(ob, arm, name, offset=(0, 0, 0), rot_z=0.0, col=None):
    """A posable copy: its own armature (same rests) and a linked mesh bound to it, placed by the armature."""
    col = col or scene.collection("Preview")
    a2 = arm.copy()
    a2.data = arm.data.copy()
    a2.name = name + "_Arm"
    col.objects.link(a2)
    m2 = ob.copy()
    m2.name = name
    col.objects.link(m2)
    m2.parent = a2
    m2.matrix_parent_inverse = Matrix.Identity(4)
    m2.modifiers["Armature"].object = a2
    a2.location = offset
    a2.rotation_euler = (0, 0, rot_z)
    char.rest_pose(a2)
    return a2, m2


def pose(a2, clip, frac):
    src, act, rng = char.import_clip(clip)
    f = int(round(rng[0] + (rng[1] - rng[0]) * frac))
    bpy.context.scene.frame_set(f)
    loc, rot = a2.location.copy(), a2.rotation_euler.copy()
    a2.location, a2.rotation_euler = (0, 0, 0), (0, 0, 0)
    char.pose_from_armature(a2, src)
    a2.location, a2.rotation_euler = loc, rot
    for o in list(bpy.data.objects):
        if o.name.startswith("Clip_"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    return f


def ground():
    me = bpy.data.meshes.new("Ground")
    s = 30.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ob = bpy.data.objects.new("Ground", me)
    scene.collection("Preview").objects.link(ob)
    m = bpy.data.materials.new("Concrete")
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.22, 0.21, 0.2, 1)
    b.inputs["Roughness"].default_value = 0.85
    nt = m.node_tree
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 40
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    me.materials.append(m)
    return ob


def hide_all_but(keep):
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o not in keep


def frame(objs, direction, lens=50.0, margin=1.08, aspect=16 / 9, lift=0.0):
    """Camera along `direction` (from the subject) at the distance where the posed meshes' bounds fill the frame."""
    import math
    from mi import scene as _sc
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        ev = o.evaluated_get(dg)
        m = ev.to_mesh()
        co = np.empty(len(m.vertices) * 3)
        m.vertices.foreach_get("co", co)
        ev.to_mesh_clear()
        co = co.reshape(-1, 3) @ np.array(o.matrix_world)[:3, :3].T + np.array(o.matrix_world)[:3, 3]
        lo, hi = np.minimum(lo, co.min(axis=0)), np.maximum(hi, co.max(axis=0))
    c = (lo + hi) / 2 + np.array([0, 0, lift])
    d = np.asarray(direction, dtype=float)
    d /= np.linalg.norm(d)
    side = np.cross(d, [0, 0, 1.0])
    side /= np.linalg.norm(side)
    ext = hi - lo
    half_w = 0.5 * abs(ext @ np.abs(side)) if False else 0.5 * float(np.abs(side) @ ext)
    half_h = 0.5 * ext[2]
    fh = math.atan(18.0 / lens)
    fv = math.atan(18.0 / lens / aspect)
    dist = max(half_w / math.tan(fh), half_h / math.tan(fv)) * margin + 0.5 * float(np.abs(d) @ ext)
    return render.cam_look(tuple(c + d * dist), tuple(c), lens)


def day():
    render.rig_day(sun_azimuth=225.0)


def previews(ctx, objs):
    g = getattr(ctx, "goons", None)
    if not g:
        return
    man, outs = g["man"], g["outfits"]
    arm = man.arm
    S = ctx.args.samples
    out = paths.previews
    want = wanted()
    gr = ground()
    for o in man.work.objects:
        o.hide_render = True
    base = list(outs.values())
    for o in base:
        o.hide_render = True

    def shoot(name, res=(1280, 720), samples=None):
        render.setup(samples=samples or S, res=res, threads=3)
        day()
        p = os.path.join(out, name + ".jpg")
        render.render_jpeg(p, samples or S, res, max_kb=300)
        ctx.log("preview %s" % name)

    if "goons_lineup" in want and outs:
        inst = []
        names = [n for n in ("Puffer", "Hoodie", "Tracksuit") if n in outs]
        for i, n in enumerate(names):
            x = (i - (len(names) - 1) / 2) * 1.3
            inst.append(instance(outs[n], arm, "L_" + n, (x, 0, 0), np.radians([18, 0, -18][i] if len(names) == 3 else 0)))
        hide_all_but([m for a, m in inst] + [gr])
        bpy.context.view_layer.update()
        frame([m for a, m in inst], (0.12, -1.0, 0.08), lens=45, margin=1.1)
        shoot("goons_lineup")
    if "goons_hoodie_hero" in want and "Hoodie" in outs:
        a2, m2 = instance(outs["Hoodie"], arm, "H_Hero", (0, 0, 0), np.radians(-28))
        pose(a2, "rifle_idle_ads", 0.3)
        hide_all_but([m2, gr])
        bpy.context.view_layer.update()
        frame([m2], (0.55, -1.0, 0.1), lens=55, margin=1.12)
        shoot("goons_hoodie_hero")
    if "goons_detail" in want and outs:
        n = "Hoodie" if "Hoodie" in outs else list(outs)[0]
        a2, m2 = instance(outs[n], arm, "D_" + n, (0, 0, 0), np.radians(-20))
        hide_all_but([m2, gr])
        shots = []
        bpy.context.view_layer.update()
        M = a2.matrix_world
        hand = (M @ a2.pose.bones["hand_l"].matrix).to_translation()
        for label, loc, tgt in (("hood and mask", M @ Vector((0.20, -0.72, 1.70)), M @ Vector((0.0, -0.02, 1.62))),
                                ("hand", hand + Vector((0.22, -0.30, 0.12)), hand + Vector((0.0, -0.04, 0.0)))):
            render.cam_look(tuple(loc), tuple(tgt), lens=60)
            render.setup(samples=S, res=(640, 720), threads=3)
            day()
            p = os.path.join(tempfile.gettempdir(), "mi_goon_detail_%d.png" % len(shots))
            render.render_png(p, S, (640, 720))
            shots.append(p)
        render.contact_sheet(shots, os.path.join(out, "goons_detail.jpg"), cols=2, labels=["hood and mask", "glove and cuff"])
        ctx.log("preview goons_detail")
    if "goons_poses" in want and outs:
        n = "Hoodie" if "Hoodie" in outs else list(outs)[0]
        inst = []
        for i, (clip, frac) in enumerate((("rifle_jog_fwd", 0.25), ("rifle_idle_ads", 0.5), ("death_front", 1.0))):
            a2, m2 = instance(outs[n], arm, "P%d" % i, ((i - 1) * 1.25, 0.0 if i < 2 else -0.4, 0), np.radians(-25))
            pose(a2, clip, frac)
            inst.append(m2)
        hide_all_but(inst + [gr])
        bpy.context.view_layer.update()
        frame(inst, (0.15, -1.0, 0.18), lens=40, margin=1.1)
        shoot("goons_poses")
    if "goons_wire" in want and outs:
        n = "Hoodie" if "Hoodie" in outs else list(outs)[0]
        a2, m2 = instance(outs[n], arm, "W_" + n, (0, 0, 0), np.radians(-25))
        m2.data = m2.data.copy()
        clay = bpy.data.materials.new("Clay")
        nt = clay.node_tree
        b = nt.nodes.get("Principled BSDF")
        wf = nt.nodes.new("ShaderNodeWireframe")
        wf.use_pixel_size = True
        wf.inputs[0].default_value = 0.8
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs["A"].default_value = (0.5, 0.5, 0.52, 1)
        mix.inputs["B"].default_value = (0.03, 0.03, 0.035, 1)
        nt.links.new(wf.outputs[0], mix.inputs["Factor"])
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
        m2.data.materials.clear()
        m2.data.materials.append(clay)
        m2.data.polygons.foreach_set("material_index", np.zeros(len(m2.data.polygons), dtype=np.int32))
        hide_all_but([m2, gr])
        bpy.context.view_layer.update()
        render.cam_hero([m2], direction=(0.5, -1.0, 0.15), lens=50, margin=1.08)
        shoot("goons_wire", samples=max(16, S // 3))
