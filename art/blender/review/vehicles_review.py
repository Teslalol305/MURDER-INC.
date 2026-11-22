"""Independent review renders and measurements of the exported vehicle GLBs (art/out/glb/SM_Vehicle_*.glb).

Reads only what is on disk: the GLB, the manifest's slot -> texture records and the props.json briefs. Each GLB is
imported into a fresh scene on the day rig (render.rig_day, scanned clear-sky dome) standing on a worn asphalt plane,
its slots rebuilt from the manifest textures (paint = BC tint mask x paint_default with a clear coat, glass = tint
at Unreal's opacity 0.75, lamps off by day, decals and plates alpha-tested), and rendered as a 2 x 2 contact sheet:
front three-quarter, rear three-quarter, side, and a standing player's eye (1.65 m) 2 m from the body.

    python art/blender/review/vehicles_review.py [--only Sedan,Van] [--samples 16] [--measure-only]
    python art/blender/review/vehicles_review.py --close Van_Vulture --cam x,y,z --target x,y,z --lens 35 --tag doors

Outputs: art/blender/review/sheets/review_<Name>.jpg (1280 x 720), close-ups review_<Name>_close_<tag>.jpg,
measurements printed and written to art/blender/review/sheets/measure.json.
"""
import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BL = os.path.dirname(HERE)
if BL not in sys.path:
    sys.path.insert(0, BL)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from mi import paths, render, scene as _scene  # noqa: E402

REPO = os.path.dirname(os.path.dirname(BL))
OUT = os.path.join(HERE, "sheets")
NAMES = ["Sedan", "Taxi", "SUV", "Pickup", "Van", "Van_Vulture", "BoxTruck", "IPXTruck", "Motorbike",
         "BurnedCar", "StrippedCar"]
# axle positions and wheel diameters stated in the briefs (props.json descriptions)
BRIEF_WHEELS = {
    "Sedan": ((1.42, -1.38), 0.65), "Taxi": ((1.42, -1.38), 0.65), "SUV": ((1.50, -1.42), 0.80),
    "Pickup": ((1.72, -1.50), 0.78), "Van": ((1.70, -1.50), 0.72), "Van_Vulture": ((1.70, -1.50), 0.72),
    "BoxTruck": ((2.95, -2.09), 0.88), "IPXTruck": ((2.05, -1.75), 1.00), "Motorbike": ((0.66, -0.66), 0.62),
    "BurnedCar": ((1.42, -1.38), None), "StrippedCar": (None, None),
}
WHEEL_SLOTS = ("Tyre", "WheelSteel", "Alloy_Wheel")


def manifest():
    with open(paths.manifest) as f:
        m = json.load(f)
    a = m.get("assets", m)
    return a if isinstance(a, dict) else {x["name"]: x for x in a}


def briefs():
    with open(os.path.join(REPO, "docs", "unreal", "spec", "assets", "props.json")) as f:
        d = json.load(f)
    lst = d if isinstance(d, list) else next(v for v in d.values() if isinstance(v, list))
    return {p["name"]: p for p in lst if isinstance(p, dict) and str(p.get("id", "")).startswith("vehicle_")}


# ----------------------------------------------------------------------------------------------------- materials

def _img(nt, path, srgb, uv):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(path, check_existing=True)
    n.image.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    nt.links.new(uv.outputs["UV"], n.inputs["Vector"])
    return n


def build_material(rec, old):
    slot = rec["slot"]
    tex = rec.get("textures") or {}
    base = (0.5, 0.5, 0.5, 1.0)
    rough, metal = 0.5, 0.0
    if old and old.node_tree:
        p = next((n for n in old.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if p:
            base = tuple(p.inputs["Base Color"].default_value)
            rough = p.inputs["Roughness"].default_value
            metal = p.inputs["Metallic"].default_value
    m = bpy.data.materials.new("R_" + slot)
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    uv = nt.nodes.new("ShaderNodeTexCoord")
    full = {k: os.path.join(paths.out, v) for k, v in tex.items() if v and os.path.exists(os.path.join(paths.out, v))}
    bs.inputs["Base Color"].default_value = base
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal
    col_out = None
    if "BC" in full:
        bc = _img(nt, full["BC"], True, uv)
        col_out = bc.outputs["Color"]
        if "paint_default" in rec:
            mul = nt.nodes.new("ShaderNodeMix")
            mul.data_type = "RGBA"
            mul.blend_type = "MULTIPLY"
            mul.inputs["Factor"].default_value = 1.0
            nt.links.new(col_out, mul.inputs["A"])
            mul.inputs["B"].default_value = (*rec["paint_default"], 1.0)
            col_out = mul.outputs["Result"]
            bs.inputs["Coat Weight"].default_value = 1.0
            bs.inputs["Coat Roughness"].default_value = 0.04
        if "Decals" in slot or "Plate" in slot:
            nt.links.new(bc.outputs["Alpha"], bs.inputs["Alpha"])
    if "ORM" in full:
        orm = _img(nt, full["ORM"], False, uv)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bs.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bs.inputs["Metallic"])
        if col_out is not None:   # AO into the base colour, as the engine's material AO roughly does
            ao = nt.nodes.new("ShaderNodeMix")
            ao.data_type = "RGBA"
            ao.blend_type = "MULTIPLY"
            ao.inputs["Factor"].default_value = 1.0
            nt.links.new(col_out, ao.inputs["A"])
            nt.links.new(sep.outputs["Red"], ao.inputs["B"])
            col_out = ao.outputs["Result"]
    if col_out is not None:
        nt.links.new(col_out, bs.inputs["Base Color"])
    if "N" in full:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        n = _img(nt, full["N"], False, uv)
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    # lamps are off by day: E is not wired
    if "Glass" in slot:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = 0.75          # Unreal opacity of the set (set.json note)
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(bs.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    else:
        nt.links.new(bs.outputs[0], out.inputs["Surface"])
    m["review_textures"] = ",".join(sorted(full))
    return m


def import_glb(path, man):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    obs = [o for o in bpy.data.objects if o not in before]
    for o in obs:
        if o.type != "MESH":
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        recs = {r["slot"]: r for r in man[name]["material_slots"]}
        for i, ms in enumerate(o.material_slots):
            old = ms.material
            key = re.sub(r"\.\d+$", "", old.name) if old else None
            rec = recs.get(key, {"slot": key or "none"})
            o.material_slots[i].material = build_material(rec, old)
    return [o for o in obs if o.type == "MESH"]


def ground():
    import bmesh
    me = bpy.data.meshes.new("Ground")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=30.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Ground", me)
    bpy.context.scene.collection.objects.link(ob)
    tile = 2.0
    try:
        from mi import mat
        m = mat.from_scan("TS_Asphalt_ScanWorn")
        tile = mat.scan_tile("TS_Asphalt_ScanWorn")
    except Exception as e:  # noqa: BLE001
        print("  ground: flat asphalt (%s)" % e)
        from mi import mat
        m = mat.flat("M_Asphalt", (0.07, 0.07, 0.068), 0.85)
    me.materials.append(m)
    uvl = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        tx, ty = (tile, tile) if isinstance(tile, (int, float)) else tuple(tile)[:2]
        uvl.data[loop.index].uv = (co.x / tx, co.y / ty)
    return ob


# ---------------------------------------------------------------------------------------------------- measuring

def mesh_arrays(ob):
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    m = np.array(ob.matrix_world)
    co = co @ m[:3, :3].T + m[:3, 3]
    me.calc_loop_triangles()
    tris = len(me.loop_triangles)
    pm = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", pm)
    ls = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_total", lt)
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", lv)
    return co, tris, pm, ls, lt, lv


def slot_verts(ob, co, pm, ls, lt, lv, pred):
    idx = [i for i, ms in enumerate(ob.material_slots) if ms.material and pred(ms.material.name)]
    sel = np.isin(pm, idx)
    vs = set()
    for s, t in zip(ls[sel], lt[sel]):
        vs.update(lv[s:s + t].tolist())
    return co[sorted(vs)] if vs else np.zeros((0, 3))


def clusters_x(pts, gap=0.25):
    if len(pts) == 0:
        return []
    order = np.argsort(pts[:, 0])
    xs = pts[order, 0]
    cuts = np.where(np.diff(xs) > gap)[0]
    groups = np.split(order, cuts + 1)
    out = []
    for g in groups:
        p = pts[g]
        if len(p) < 30:
            continue
        out.append({"x": round(float((p[:, 0].min() + p[:, 0].max()) / 2), 3),
                    "dia_z": round(float(p[:, 2].max() - p[:, 2].min()), 3),
                    "len_x": round(float(p[:, 0].max() - p[:, 0].min()), 3),
                    "zmin": round(float(p[:, 2].min()), 3), "n": int(len(p))})
    return out


def lamp_colour(ob, name, man):
    """Mean E colour of the lamp slot faces in the front and the rear third (nose direction check)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    rec = next((r for r in man[name]["material_slots"] if r["slot"].endswith("_Lamp")), None)
    if not rec or not rec.get("textures") or not rec["textures"].get("E"):
        return None
    im = np.asarray(Image.open(os.path.join(paths.out, rec["textures"]["E"])).convert("RGB"), np.float32) / 255
    h, w = im.shape[:2]
    me = ob.data
    idx = [i for i, ms in enumerate(ob.material_slots) if ms.material and ms.material.name.endswith("_Lamp")]
    uvl = me.uv_layers[0].data
    lo, hi = np.inf, -np.inf
    for v in me.vertices:
        lo, hi = min(lo, v.co.x), max(hi, v.co.x)
    L = hi - lo
    acc = {"front": [], "rear": []}
    for p in me.polygons:
        if p.material_index not in idx:
            continue
        x = p.center.x
        side = "front" if x > hi - L / 3 else "rear" if x < lo + L / 3 else None
        if not side:
            continue
        u, v = uvl[p.loop_start].uv
        acc[side].append(im[min(h - 1, int((1 - v % 1) * h)), min(w - 1, int((u % 1) * w))])
    return {k: [round(float(c), 2) for c in np.mean(v, axis=0)] if v else None for k, v in acc.items()}


def measure(name, obs, man, brief):
    asset = "SM_Vehicle_" + name
    ob = obs[0]
    co, tris, pm, ls, lt, lv = mesh_arrays(ob)
    lo, hi = co.min(0), co.max(0)
    size = hi - lo
    r = {"asset": asset, "size": [round(float(s), 3) for s in size],
         "brief_size": brief.get("size_m"), "min": [round(float(s), 3) for s in lo], "max": [round(float(s), 3) for s in hi],
         "origin_offset_from_ground_centre": [round(float((lo[0] + hi[0]) / 2), 3), round(float((lo[1] + hi[1]) / 2), 3),
                                              round(float(lo[2]), 3)],
         "triangles": tris, "slots": [ms.material.name[2:] for ms in ob.material_slots if ms.material],
         "verts_below_1cm": int((co[:, 2] < 0.01).sum())}
    wp = slot_verts(ob, co, pm, ls, lt, lv, lambda n: any(k in n for k in WHEEL_SLOTS))
    if name in ("BurnedCar",):
        wp = slot_verts(ob, co, pm, ls, lt, lv, lambda n: True)
        wp = wp[(wp[:, 2] < 0.62) & (np.abs(wp[:, 1]) > 0.55)]
    wh = clusters_x(wp)
    r["wheels"] = wh
    if len(wh) >= 2:
        r["wheelbase"] = round(wh[-1]["x"] - wh[0]["x"], 3)
    bw = BRIEF_WHEELS.get(name)
    if bw and bw[0]:
        r["brief_axles"], r["brief_wheel_dia"] = bw
        r["brief_wheelbase"] = round(bw[0][0] - bw[0][1], 3)
    tp = slot_verts(ob, co, pm, ls, lt, lv, lambda n: "Tyre" in n)
    if len(tp):
        r["tyre_zmin"] = round(float(tp[:, 2].min()), 4)
    r["lamp_E_front_rear"] = lamp_colour(ob, asset, man)
    gp = slot_verts(ob, co, pm, ls, lt, lv, lambda n: "Glass" in n)
    if len(gp):
        r["glass_x_range"] = [round(float(gp[:, 0].min()), 2), round(float(gp[:, 0].max()), 2)]
        r["glass_z_range"] = [round(float(gp[:, 2].min()), 2), round(float(gp[:, 2].max()), 2)]
    sizes = {}
    for rec in man[asset]["material_slots"]:
        for k, v in (rec.get("textures") or {}).items():
            p = os.path.join(paths.out, v)
            if os.path.exists(p):
                from PIL import Image
                sizes[rec["slot"] + "." + k] = "%dx%d" % Image.open(p).size
            else:
                sizes[rec["slot"] + "." + k] = "MISSING"
        if not rec.get("textures"):
            sizes[rec["slot"]] = "no textures in manifest"
    r["textures"] = sizes
    return r


# ------------------------------------------------------------------------------------------------------ views

def bearing(dx, dy):
    return math.degrees(math.atan2(dx, dy)) % 360.0


def view(path, cam, sun_bearing, samples, res=(640, 360)):
    render.rig_day(sun_azimuth=sun_bearing)
    bpy.context.scene.camera = cam
    render.render_jpeg(path, samples, res=res, max_kb=200)
    return path


def clear_cams():
    for o in list(bpy.data.objects):
        if o.type == "CAMERA":
            bpy.data.objects.remove(o, do_unlink=True)


def load_vehicle(name, man):
    obs = import_glb(os.path.join(paths.glb, "SM_Vehicle_%s.glb" % name), man)
    if name == "IPXTruck":     # doors at their hinges (manifest notes), swung open 108.9 degrees
        for nm, hinge, ang in (("IPXTruck_Door", (-3.0, -0.89, 1.05), 108.9),
                               ("IPXTruck_Door_Left", (-3.0, 0.89, 1.05), -108.9)):
            d = import_glb(os.path.join(paths.glb, "SM_Vehicle_%s.glb" % nm), man)
            for o in d:
                o.location = hinge
                o.rotation_euler = (0, 0, math.radians(ang))
            obs += d
        bpy.context.view_layer.update()
    return obs


def sheet(name, man, brief, samples, measure_only=False):
    _scene.reset(threads=3, samples=samples)
    render.setup(samples, res=(640, 360), threads=3)
    obs = load_vehicle(name, man)
    bpy.context.view_layer.update()
    m = measure(name, obs, man, brief)
    print(json.dumps({k: v for k, v in m.items() if k != "textures"}))
    if measure_only:
        return m, None
    ground()
    lo, hi = render._bounds(obs)
    c = (lo + hi) / 2
    L, W = hi[0] - lo[0], hi[1] - lo[1]
    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, "_tmp")
    os.makedirs(tmp, exist_ok=True)
    shots = []
    # front three-quarter from the right (-Y) flank, rear three-quarter from the left (+Y) flank
    for tag, d in (("front 3/4", (1.0, -0.9, 0.42)), ("rear 3/4", (-1.0, 0.9, 0.42))):
        cam = render.cam_hero(obs, direction=d, lens=50, margin=0.72)
        shots.append((tag, cam, bearing(d[0], d[1]) + 40))
    dist = max(L, 2.0) * 1.15 / (2 * math.tan(math.atan(18 / 70)))
    cam = render.cam_look((c[0], lo[1] - dist, max(0.9, c[2])), (c[0], 0, c[2]), lens=70, name="Cam_Side")
    shots.append(("side (right flank)", cam, 200.0))
    if name in ("Van_Vulture", "IPXTruck"):     # the open doors: from the tail, 2 m behind the hinge line
        hx = -2.53 if name == "Van_Vulture" else -3.0
        cam = render.cam_eye((hx - 2.0, 0.35), (hx + 2.0, 0.0), height=1.65, look_height=1.2, lens=22)
        shots.append(("eye 1.65 m, 2 m behind tail", cam, 290.0))
    else:
        ey = hi[1] + 2.0
        cam = render.cam_eye((c[0] + 0.25 * L, ey), (c[0] + 0.05 * L, 0.0), height=1.65, look_height=0.7, lens=22)
        shots.append(("eye 1.65 m, 2 m off left flank", cam, 20.0))
    imgs, labels = [], []
    for i, (tag, cam, sb) in enumerate(shots):
        p = os.path.join(tmp, "%s_%d.jpg" % (name, i))
        view(p, cam, sb % 360, samples)
        imgs.append(p)
        labels.append(("%s  " % name if i == 0 else "") + tag)
    out = os.path.join(OUT, "review_%s.jpg" % name)
    render.contact_sheet(imgs, out, cols=2, labels=labels, size=(1280, 720), max_kb=300)
    for p in imgs:
        os.remove(p)
    print("SHEET", out)
    return m, out


def close(name, man, cam_xyz, target, lens, tag, samples, sun):
    _scene.reset(threads=3, samples=samples)
    render.setup(samples, res=(1280, 720), threads=3)
    load_vehicle(name, man)
    ground()
    cam = render.cam_look(cam_xyz, target, lens=lens, name="Cam_Close")
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, "review_%s_close_%s.jpg" % (name, tag))
    render.rig_day(sun_azimuth=sun)
    bpy.context.scene.camera = cam
    render.render_jpeg(out, samples, res=(1280, 720), max_kb=300)
    print("CLOSE", out)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--measure-only", action="store_true")
    ap.add_argument("--close", default="")
    ap.add_argument("--cam", default="")
    ap.add_argument("--target", default="")
    ap.add_argument("--lens", type=float, default=35.0)
    ap.add_argument("--tag", default="a")
    ap.add_argument("--sun", type=float, default=200.0)
    a = ap.parse_args(argv)
    man, br = manifest(), briefs()
    if a.close:
        f = lambda s: tuple(float(x) for x in s.split(","))  # noqa: E731
        close(a.close, man, f(a.cam), f(a.target), a.lens, a.tag, a.samples, a.sun)
        return
    names = [n for n in (a.only.split(",") if a.only else NAMES) if n]
    res = {}
    mp = os.path.join(OUT, "measure.json")
    if os.path.exists(mp):
        with open(mp) as fh:
            res = json.load(fh)
    for n in names:
        m, _ = sheet(n, man, br.get("SM_Vehicle_" + n, {}), a.samples, a.measure_only)
        res[n] = m
        os.makedirs(OUT, exist_ok=True)
        with open(mp, "w") as fh:
            json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()
