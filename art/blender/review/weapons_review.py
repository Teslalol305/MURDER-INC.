"""Independent review renders and measurements of the exported player guns (critique round 1).

Reads only what is on disk: art/out/glb/SK_Chopper.glb, SK_Nine.glb, their magazines and top rounds, and the texture
sets under art/out/textures/<set>/ (BC sRGB, ORM linear, N OpenGL, E sRGB). Each gun is imported into a fresh scene
with its magazine in place and lit by Blender's neutral studio HDRI on a grey cyclorama colour.

Views per gun: left, right, top (orthographic), three-quarter front, three-quarter rear (perspective), and the
first-person view from docs/unreal/spec/02-weapons-combat.md 2.13: camera at the eye, vertical field of view 54 deg,
gun origin at the hip pose (view 1 "Close") or the derived aim pose, Euler order YXZ as in src/weapon/handling.js.

    python art/blender/review/weapons_review.py [--only Chopper|Nine] [--views left,right,...] [--samples 48]
    python art/blender/review/weapons_review.py --measure-only

Outputs: art/blender/review/sheets/weapons_<Gun>_<view>.jpg (1280 x 720), measurements in
art/blender/review/sheets/weapons_measure.json.
"""
import argparse
import json
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
from mathutils.bvhtree import BVHTree  # noqa: E402

from mi import render  # noqa: E402

REPO = os.path.dirname(os.path.dirname(BL))
GLB = os.path.join(REPO, "art", "out", "glb")
TEX = os.path.join(REPO, "art", "out", "textures")
OUT = os.path.join(HERE, "sheets")

GUNS = {
    "Chopper": {
        "files": ["SK_Chopper", "SM_Weapon_ChopperMagazine", "SM_Weapon_ChopperMagazine_TopRound"],
        "sets": {"M_Chopper": "Chopper", "M_Weapon_ChopperMagazine": "Weapon_ChopperMagazine"},
        "hip": ((0.15, -0.09, -0.24), (0.05, 0.28, -0.35)),
        "aim": ((0.0, -0.0555, -0.1365), (0.0, 0.0, 0.0)),
    },
    "Nine": {
        "files": ["SK_Nine", "SM_Weapon_NineMagazine", "SM_Weapon_NineMagazine_TopRound"],
        "sets": {"M_Nine": "Nine", "M_Weapon_NineMagazine": "Weapon_NineMagazine"},
        "hip": ((0.105, -0.056, -0.36), (0.07, 0.11, -0.18)),
        "aim": ((0.0, -0.0185, -0.3575), (0.0, 0.0, 0.0)),
    },
}
VIEWS = ["left", "right", "top", "front34", "rear34", "fp_hip", "fp_aim"]


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    render.setup(samples=48, res=(1280, 720), denoise=True, threads=3)
    render.look("AgX", "AgX - Medium High Contrast", exposure=0.0)


def world(strength=1.0, bg=(0.42, 0.42, 0.43)):
    """Studio HDRI for lighting and reflections; camera rays see a flat neutral grey."""
    s = bpy.context.scene
    w = bpy.data.worlds.new("Studio")
    s.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    hd = os.path.join(os.path.dirname(bpy.utils.resource_path("LOCAL")), bpy.app.version_string[:3],
                      "datafiles", "studiolights", "world", "studio.exr")
    if not os.path.exists(hd):
        hd = os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "studiolights", "world", "studio.exr")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(hd)
    bg_hdri = nt.nodes.new("ShaderNodeBackground")
    bg_hdri.inputs["Strength"].default_value = strength
    nt.links.new(env.outputs["Color"], bg_hdri.inputs["Color"])
    bg_flat = nt.nodes.new("ShaderNodeBackground")
    bg_flat.inputs["Color"].default_value = (*bg, 1.0)
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bg_hdri.outputs["Background"], mix.inputs[1])
    nt.links.new(bg_flat.outputs["Background"], mix.inputs[2])
    o = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(mix.outputs["Shader"], o.inputs["Surface"])
    # a soft key from upper left front, as a product shot would have
    ld = bpy.data.lights.new("Key", "AREA")
    ld.energy, ld.size = 60.0, 1.2
    lo = bpy.data.objects.new("Key", ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = (0.6, 0.9, 1.3)
    lo.rotation_euler = (Vector((0.25, 0, 0)) - lo.location).to_track_quat("-Z", "Y").to_euler()


def texture_material(mat, set_name):
    d = os.path.join(TEX, set_name)
    meta = json.load(open(os.path.join(d, "set.json")))
    files = meta["files"]
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(p.outputs["BSDF"], out.inputs["Surface"])
    uv = nt.nodes.new("ShaderNodeUVMap")

    def img(key, srgb):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(d, files[key]), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
        n.interpolation = "Cubic"
        nt.links.new(uv.outputs["UV"], n.inputs["Vector"])
        return n

    bc = img("BC", True)
    nt.links.new(bc.outputs["Color"], p.inputs["Base Color"])
    orm = img("ORM", False)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], p.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], p.inputs["Metallic"])
    nm = img("N", False)
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nm.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], p.inputs["Normal"])
    if "E" in files:
        e = img("E", True)
        nt.links.new(e.outputs["Color"], p.inputs["Emission Color"])
        p.inputs["Emission Strength"].default_value = 1.0


def load_gun(name):
    g = GUNS[name]
    objs = []
    for f in g["files"]:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(GLB, f + ".glb"))
        objs += [o for o in bpy.data.objects if o not in before]
    for o in list(objs):
        if o.type == "MESH" and o.name.startswith("Icosphere"):   # importer's bone display shape
            bpy.data.objects.remove(o, do_unlink=True)
            objs.remove(o)
    done = set()
    for o in objs:
        if o.type != "MESH":
            continue
        for slot in o.material_slots:
            m = slot.material
            key = m.name.split(".")[0]
            if m.name not in done and key in g["sets"]:
                texture_material(m, g["sets"][key])
                done.add(m.name)
    meshes = [o for o in objs if o.type == "MESH"]
    return objs, meshes


def bounds(meshes):
    dg = bpy.context.evaluated_depsgraph_get()
    lo, hi = np.full(3, 1e9), np.full(3, -1e9)
    for o in meshes:
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        co = np.array([e.matrix_world @ v.co for v in me.vertices])
        lo, hi = np.minimum(lo, co.min(0)), np.maximum(hi, co.max(0))
        e.to_mesh_clear()
    return lo, hi


def cam(name, loc, target, lens=None, ortho=None, up="Y"):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type, cd.ortho_scale = "ORTHO", ortho
    else:
        cd.lens, cd.sensor_width = lens, 36.0
    cd.clip_start, cd.clip_end = 0.005, 50.0
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", up).to_euler()
    bpy.context.scene.camera = ob
    return ob


def euler_yxz(p, y, r):
    return Matrix.Rotation(y, 4, "Y") @ Matrix.Rotation(p, 4, "X") @ Matrix.Rotation(r, 4, "Z")


def fp_setup(name, pose, objs):
    """World = three.js view space (x right, y up, z toward the viewer). The camera sits at the origin."""
    (px, py, pz), (pitch, yaw, roll) = GUNS[name][pose]
    # gun space in Blender (X forward, Y left, Z up) -> three.js gun space (x right, y up, forward -z)
    m0 = Matrix(((0, -1, 0, 0), (0, 0, 1, 0), (-1, 0, 0, 0), (0, 0, 0, 1)))
    mw = Matrix.Translation((px, py, pz)) @ euler_yxz(pitch, yaw, roll) @ m0
    root = bpy.data.objects.new("ViewRoot", None)
    bpy.context.scene.collection.objects.link(root)
    for o in objs:
        if o.parent is None:
            o.parent = root
    root.matrix_world = mw
    cd = bpy.data.cameras.new("Eye")
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = 24.0
    cd.lens = 12.0 / math.tan(math.radians(54.0) / 2)
    cd.clip_start, cd.clip_end = 0.01, 10.0
    ob = bpy.data.objects.new("Eye", cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (0, 0, 0)
    ob.rotation_euler = (0, 0, 0)
    bpy.context.scene.camera = ob
    # the HDRI is set so that +Z is up: in view space +Y is up, so turn the world mapping
    w = bpy.context.scene.world.node_tree
    env = next(n for n in w.nodes if n.type == "TEX_ENVIRONMENT")
    mp = w.nodes.new("ShaderNodeMapping")
    tc = w.nodes.new("ShaderNodeTexCoord")
    mp.inputs["Rotation"].default_value = (math.pi / 2, 0, 0)   # view (x, y, z) -> HDRI (x, -z, y)
    w.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    w.links.new(mp.outputs["Vector"], env.inputs["Vector"])
    key = bpy.data.objects["Key"]
    key.location = (-0.5, 1.2, 0.6)
    key.rotation_euler = (Vector((0.1, -0.1, -0.3)) - key.location).to_track_quat("-Z", "Y").to_euler()


def studio_cam(view, lo, hi):
    c = (lo + hi) / 2
    size = hi - lo
    if view == "left":     # gun's left = +Y
        return cam("Left", (c[0], 2.0, c[2]), c, ortho=max(size[0], size[2] * 16 / 9) * 1.08)
    if view == "right":
        return cam("Right", (c[0], -2.0, c[2]), c, ortho=max(size[0], size[2] * 16 / 9) * 1.08)
    if view == "top":
        return cam("Top", (c[0], c[1], 2.0), c, ortho=max(size[0], size[1] * 16 / 9) * 1.15)
    r = float(np.linalg.norm(size)) / 2
    lens = 70.0
    dist = r * 0.8 / math.sin(math.atan(10.1 / lens))
    if view == "front34":
        d = Vector((1.0, -0.85, 0.45)).normalized()     # from the muzzle end, right side
    else:
        d = Vector((-1.0, 0.8, 0.5)).normalized()       # from behind, left side
    return cam("Q_" + view, Vector(c) + d * dist, c, lens=lens)


# ---------------------------------------------------------------------------------------------- measurements

def bvh_of(meshes):
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for o in meshes:
        e = o.evaluated_get(dg)
        me = e.to_mesh()
        off = len(verts)
        verts += [e.matrix_world @ v.co for v in me.vertices]
        polys += [[off + i for i in p.vertices] for p in me.polygons]
        e.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys), np.array([tuple(v) for v in verts])


def height_at(bvh, x, y, top=0.3):
    hit = bvh.ray_cast(Vector((x, y, top)), Vector((0, 0, -1)), 1.0)
    return None if hit[0] is None else round(hit[0].z, 5)


def measure(name, objs, meshes):
    gun = next(o for o in meshes if o.name.startswith("SK_"))
    arm = next(o for o in objs if o.type == "ARMATURE")
    res = {"bones": {b.name: [round(v, 4) for v in (arm.matrix_world @ b.head_local)] for b in arm.data.bones}}
    lo, hi = bounds([gun])
    res["gun_bbox"] = [lo.round(4).tolist(), hi.round(4).tolist()]
    lo2, hi2 = bounds(meshes)
    res["all_bbox"] = [lo2.round(4).tolist(), hi2.round(4).tolist()]
    bvh, V = bvh_of([gun])
    if name == "Chopper":
        sx, fx, sz = 0.0235, 0.409, 0.0555
        between = (V[:, 0] > 0.035) & (V[:, 0] < 0.392)
    else:
        sx, fx, sz = 0.0125, 0.186, 0.0185
        between = (V[:, 0] > 0.020) & (V[:, 0] < 0.181)
    res["max_z_between_sights"] = round(float(V[between, 2].max()), 5)
    # rear notch profile across Y at the rear sight X, front post height on the centre line
    ys = np.arange(-0.008, 0.0081, 0.0002)
    prof = [height_at(bvh, sx, float(y)) for y in ys]
    res["rear_sight_profile"] = {"y_mm": (ys * 1000).round(1).tolist(), "z_mm": [None if z is None else round(z * 1000, 2) for z in prof]}
    xs = np.arange(fx - 0.012, fx + 0.012, 0.0005)
    res["front_post_profile"] = {"x_mm": (xs * 1000).round(1).tolist(), "z_mm": [None if (z := height_at(bvh, float(x), 0.0)) is None else round(z * 1000, 2) for x in xs]}
    # sight line clear: ray from just behind the rear notch along +X at the sight height minus 0.3 mm
    h = bvh.ray_cast(Vector((sx + 0.002, 0, sz - 0.0003)), Vector((1, 0, 0)), 1.0)
    res["sight_line_first_hit_x"] = None if h[0] is None else round(h[0].x, 4)
    # bore: ray from in front of the muzzle back along the axis
    h = bvh.ray_cast(Vector((0.7, 0, 0)), Vector((-1, 0, 0)), 2.0)
    res["bore_ray_hit_x"] = None if h[0] is None else round(h[0].x, 4)
    # vertices per bone group and their travel when the bone is moved
    vg = {g.index: g.name for g in gun.vertex_groups}
    counts = {}
    for v in gun.data.vertices:
        for g in v.groups:
            if g.weight > 0.5:
                counts[vg[g.group]] = counts.get(vg[g.group], 0) + 1
    res["verts_per_group"] = counts
    res["triangles"] = sum(len(p.vertices) - 2 for p in gun.data.polygons)
    res["mag_triangles"] = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes if o is not gun)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--views", default=",".join(VIEWS))
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--measure-only", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    a = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    names = [n for n in GUNS if not a.only or n in a.only.split(",")]
    mpath = os.path.join(OUT, "weapons_measure.json")
    allm = json.load(open(mpath)) if os.path.exists(mpath) else {}
    for name in names:
        fresh()
        objs, meshes = load_gun(name)
        allm[name] = measure(name, objs, meshes)
        print(json.dumps({name: {k: v for k, v in allm[name].items() if "profile" not in k}}, indent=1))
        json.dump(allm, open(mpath, "w"), indent=1)
        if a.measure_only:
            continue
        for view in a.views.split(","):
            fresh()
            world()
            objs, meshes = load_gun(name)
            if view.startswith("fp_"):
                fp_setup(name, view[3:], objs)
                flat = next(n for n in bpy.context.scene.world.node_tree.nodes
                            if n.type == "BACKGROUND" and n.inputs["Strength"].default_value == 1.0 and not n.inputs["Color"].links)
                flat.inputs["Color"].default_value = (0.16, 0.16, 0.165, 1.0)
            else:
                lo, hi = bounds(meshes)
                studio_cam(view, lo, hi)
            path = os.path.join(OUT, "weapons_%s_%s.jpg" % (name, view))
            p, t = render.render_jpeg(path, samples=a.samples, max_kb=600)
            print("RENDERED", p, round(t, 1), "s", flush=True)


if __name__ == "__main__":
    main()
