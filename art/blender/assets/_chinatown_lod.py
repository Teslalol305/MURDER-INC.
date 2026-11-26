"""Canal Street north row: far proxies (an HLOD-style merged, reduced facade per building) and the triangle count of the
design's worst view 1 (chinatown.md 14: Canal St from the start, looking east; at most 1.5 M triangles drawn, aim 1.1 M).

    venv/bin/python art/blender/assets/_chinatown_lod.py              # the view counts from the placements and manifests
    (the proxies are built by `build.py build chinatown`, chinatown.build -> build_far_proxies)

Why: the north row alone was about 1.22 M triangles placed (481 instances; the Block's bay windows at 5.1k each), so the
start view went over budget before the south row, the market and the far end were placed. A building past LOD_SWITCH m
from the camera draws one proxy, SM_Facade_CT_Far_<id> (at most 12k triangles: chinatown.md 13.2's far-facade row), made
by merging every placed module of that building (the Block's GLBs and this lane's meshes), mapping each sign's 0..1 face
onto its atlas cell (one sign slot, M_Sign_CT_Atlas1) and collapsing the result. In Unreal the proxies are the
buildings' LOD1 (or an HLOD layer) at the same switch distance; the full modules stay LOD0.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

from mi import paths  # noqa: E402

LOD_SWITCH = 30.0          # metres from the camera to a building's nearest point
PROP_LOD_SWITCH = 12.0     # metres from the camera to a prop's nearest point: a prop past it draws its <name>_LOD1
# Props that are heavy and placed many times: source mesh -> LOD1 triangle target (about a quarter; the thin-member floor
# of the lane's check still holds because the collapse keeps the volume, not the hairlines; the pallet stack and the dumpster
# are left out: their boards and sheets collapse to slivers under 34 mm). The LOD1 is a second mesh of
# the same name + "_LOD1": in Unreal it is the static mesh's LOD1 (same slots), switched at PROP_LOD_SWITCH.
PROP_LODS = {
    "SM_Prop_TrashCan_Metal": 1600, "SM_Prop_CT_StallCounter_2m": 1200, "SM_Furn_MilkCrate": 450,
    "SM_Prop_CT_VendorTable": 900, "SM_Prop_CardboardBoxes": 500, "SM_Prop_CT_FishCounter": 1500, "SM_Prop_CT_Produce_Citrus": 1200,
    "SM_Prop_CT_ClothingRail": 800, "SM_Prop_CT_DryGoods": 900, "SM_Furn_TrafficCone": 400,
}
# Block meshes too heavy to place at all: a lighter Canal version (decimated from the Block's, same slots, same size and
# pivot), which also gets a LOD1 below. source -> (name, triangle target)
LIGHT_VARIANTS = {"SM_Prop_Hydrant": ("SM_Prop_CT_Hydrant", 4500)}
LIGHT_LOD1 = {"SM_Prop_CT_Hydrant": 1100}
FAR_TRIS = 10000           # proxy target (cap 12k)
# worst view 1 (chinatown.md 14.0): the start (web (-40, 0, -24.5), eye 1.68) looking east, the stream's 16:9 at 90 deg
VIEW1 = {"eye": (-40.0, 24.5, 1.68), "dir": (1.0, 0.0, 0.0), "hfov": 90.0, "vfov": 58.7, "far": 120.0}


def _manifest():
    with open(os.path.join(paths.out, "manifest.json")) as f:
        return json.load(f)["assets"]


def _placements():
    with open(os.path.join(paths.out, "placements", "placements_chinatown.json")) as f:
        return json.load(f)["instances"]


def instance_box(e, rec):
    """World AABB (Blender metres) of an instance from its manifest bounds, rotation about Z and scale along X."""
    mn, mx = rec["bounds_m"]["min"], rec["bounds_m"]["max"]
    sx = e.get("scale", [1, 1, 1])[0]
    a = math.radians(e.get("rot_z_deg", 0.0))
    xs, ys = [], []
    for x in (mn[0] * sx, mx[0] * sx):
        for y in (mn[1], mx[1]):
            xs.append(x * math.cos(a) - y * math.sin(a))
            ys.append(x * math.sin(a) + y * math.cos(a))
    p = e["blender_m"]
    return ((p[0] + min(xs), p[1] + min(ys), p[2] + mn[2]), (p[0] + max(xs), p[1] + max(ys), p[2] + mx[2]))


def in_view(box, view):
    """Any corner of the box inside the view frustum (yaw-only camera)."""
    ex, ey, ez = view["eye"]
    dx, dy = view["dir"][0], view["dir"][1]
    th, tv = math.tan(math.radians(view["hfov"] / 2)), math.tan(math.radians(view["vfov"] / 2))
    (x0, y0, z0), (x1, y1, z1) = box
    for x in (x0, x1):
        for y in (y0, y1):
            for z in (z0, z1):
                fwd = (x - ex) * dx + (y - ey) * dy
                if fwd <= 0.1 or fwd > view["far"]:
                    continue
                side = -(x - ex) * dy + (y - ey) * dx
                if abs(side) <= th * fwd and abs(z - ez) <= tv * fwd:
                    return True
    return False


def dist_to_box(p, box):
    (x0, y0, z0), (x1, y1, z1) = box
    dx = max(x0 - p[0], 0, p[0] - x1)
    dy = max(y0 - p[1], 0, p[1] - y1)
    dz = max(z0 - p[2], 0, p[2] - z1)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def view_triangles(view=VIEW1, lod_switch=LOD_SWITCH, prop_lods=True):
    """(triangles drawn in the view with every module at LOD0, the same with the far proxies and the props' LOD1s, per
    building). A prop past PROP_LOD_SWITCH draws its <name>_LOD1 when the manifest has one."""
    man = _manifest()
    inst = _placements()
    by_b = {}
    for e in inst:
        by_b.setdefault(e["building"], []).append(e)
    full = proxy = 0
    rows = {}
    for b, es in sorted(by_b.items()):
        boxes = [(e, instance_box(e, man[e["mesh"]])) for e in es if e["mesh"] in man]
        seen = [(e, bx) for e, bx in boxes if in_view(bx, view)]
        t_full = sum(man[e["mesh"]]["triangles"] for e, _bx in seen)
        t_mod = 0
        for e, bx in seen:
            lod1 = man.get(e["mesh"] + "_LOD1")
            if prop_lods and lod1 and dist_to_box(view["eye"], bx) > PROP_LOD_SWITCH:
                t_mod += lod1["triangles"]
            else:
                t_mod += man[e["mesh"]]["triangles"]
        near = min((dist_to_box(view["eye"], bx) for _e, bx in boxes), default=1e9)
        far_name = "SM_Facade_CT_Far_" + b
        use_proxy = near > lod_switch and far_name in man and seen
        t_lod = man[far_name]["triangles"] if use_proxy else t_mod
        rows[b] = {"instancesInView": len(seen), "trianglesLOD0": t_full, "nearest_m": round(near, 1),
                   "drawn": "proxy" if use_proxy else "modules", "trianglesDrawn": t_lod}
        full += t_full
        proxy += t_lod
    return full, proxy, rows


def _drop_thin_parts(ob, min_w=0.034, min_len=0.6):
    """Delete the loose parts a far proxy cannot show without crawling: longer than min_len and under min_w across
    (blind slats, glazing bars, flat strips). The same rule as the lane's thin check."""
    import bmesh
    import numpy as np
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    seen, kill = set(), []
    for v0 in bm.verts:
        if v0.index in seen:
            continue
        comp, stack = [], [v0]
        seen.add(v0.index)
        while stack:
            v = stack.pop()
            comp.append(v)
            for e in v.link_edges:
                w = e.other_vert(v)
                if w.index not in seen:
                    seen.add(w.index)
                    stack.append(w)
        if len(comp) < 4:
            continue
        P = np.array([v.co[:] for v in comp])
        c = P - P.mean(0)
        _u, _s, vt = np.linalg.svd(c, full_matrices=False)
        ext = np.sort(np.ptp(c @ vt.T, axis=0))[::-1]
        if ext[0] > min_len and ext[1] < min_w:
            kill += comp
    if kill:
        bmesh.ops.delete(bm, geom=list({v for v in kill}), context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()


def build_far_proxies(ctx):
    """Merge each north-row building's placed modules into one mesh, put the sign faces on their atlas cells, collapse
    to FAR_TRIS and register SM_Facade_CT_Far_<id>. Runs inside the chinatown build after the kit and the placements."""
    import bpy
    import numpy as np
    from mi import mat
    from assets import _chinatown_place as place
    man = _manifest()
    inst = place.assemble()
    sign_mat = bpy.data.materials.get("M_Sign_CT_Atlas1")
    if sign_mat is None:
        sign_mat = mat.from_texture_set(paths.texture_set("Sign_CT_Atlas1"), name="M_Sign_CT_Atlas1", alpha="splash", macro=0.0)
    cache = {}

    def source(name):
        if name in ctx.K:
            return ctx.K[name]
        if name in cache:
            return cache[name]
        rec = man.get(name)
        if not rec:
            return None
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(paths.out, rec["glb"]))
        new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        for o in bpy.data.objects:
            if o not in before and o.type != "MESH":
                bpy.data.objects.remove(o)
        ob = new[0] if new else None
        if ob is not None:
            ob.hide_render = True
            ob.hide_viewport = True
        cache[name] = ob
        return ob

    from assets import _chinatown_streets as streets
    pivots = {k: [B["x"][0], place.LINE_Y, place.KERB_H] for k, B in place.ROW.items()}
    pivots.update({k: v["pivot_blender_m"] for k, v in streets.buildings().items()})
    by_b = {}
    for e in inst:
        if e["building"] in pivots and (e["mesh"].startswith("SM_Facade") or e["mesh"].startswith("SM_Sign")):
            by_b.setdefault(e["building"], []).append(e)
    made = []
    for b, es in sorted(by_b.items()):
        parts = []
        x0, y0, z0 = pivots[b]
        for e in es:
            src = source(e["mesh"])
            if src is None:
                continue
            me = src.data.copy()
            ob = bpy.data.objects.new("tmp_" + e["mesh"], me)
            ctx.kit.objects.link(ob)
            sx = e.get("scale", [1, 1, 1])[0]
            ob.scale = (sx, 1.0, 1.0)
            ob.rotation_euler = (0.0, 0.0, math.radians(e.get("rot_z_deg", 0.0)))
            ob.location = (e["blender_m"][0] - x0, e["blender_m"][1] - y0, e["blender_m"][2] - z0)
            if e.get("atlas_uv"):
                u0, v0, u1, v1 = e["atlas_uv"]
                uvl = me.uv_layers[0].data
                face_slots = [i for i, m in enumerate(me.materials) if m is not None and m.name.startswith("M_Sign_CT_Face")]
                for p in me.polygons:
                    if p.material_index in face_slots:
                        for li in p.loop_indices:
                            u, v = uvl[li].uv
                            uvl[li].uv = (u0 + min(max(u, 0), 1) * (u1 - u0), v0 + min(max(v, 0), 1) * (v1 - v0))
                for i in face_slots:
                    me.materials[i] = sign_mat
            if "Wear" not in me.color_attributes:
                ca = me.color_attributes.new("Wear", "FLOAT_COLOR", "CORNER")
                ca.data.foreach_set("color", np.zeros(len(me.loops) * 4, np.float32))
            parts.append(ob)
        if not parts:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        for o in parts:
            o.hide_viewport = False
            o.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = ob.data.name = "SM_Facade_CT_Far_" + b
        _drop_thin_parts(ob)
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        if tris > FAR_TRIS:
            dm = ob.modifiers.new("collapse", "DECIMATE")
            dm.decimate_type = "COLLAPSE"
            dm.ratio = FAR_TRIS / float(tris)
            dm.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=dm.name)
            _drop_thin_parts(ob)                          # what the collapse thinned below the floor
        # merge duplicate slots: the same material from several modules, and the GLB importer's ".001" copies of the kit's
        # materials, under the kit's slot names
        import re
        base = []
        for m in ob.data.materials:
            nm = re.sub(r"\.\d+$", "", m.name)
            tgt = bpy.data.materials.get(nm)
            if tgt is None:
                m.name = nm
                tgt = m
            base.append(tgt)
        uniq = []
        for m in base:
            if m not in uniq:
                uniq.append(m)
        remap = [uniq.index(m) for m in base]
        mi = np.empty(len(ob.data.polygons), np.int32)
        ob.data.polygons.foreach_get("material_index", mi)
        mi = np.array([remap[i] for i in mi], np.int32)
        ob.data.materials.clear()
        for m in uniq:
            ob.data.materials.append(m)
        ob.data.polygons.foreach_set("material_index", mi)
        slots = {}
        for m in uniq:
            if m.name == "M_Sign_CT_Atlas1":
                slots[m.name] = {"workflow": "sign_atlas", "sets": ["Sign_CT_Atlas1"], "uv": "the cell of each placed face"}
        W = round(max(max(abs(e["blender_m"][0] - x0), abs(e["blender_m"][1] - y0)) for e in es) + 3.1, 2)
        ctx.asset(ob, collision="none", slots=slots, cover_height=None,
                  notes="Far proxy of north-row building %s (HLOD-style): every placed module merged, sign faces on their atlas "
                        "cells, collapsed to about %dk triangles. Drawn past %.0f m from the camera (LOD1 / HLOD); pivot at the "
                        "building's first face's start on its wall plane at the sidewalk (the north row: its west end on the facade line); modules "
                        "keep their world yaw (extent about %.1f m)."
                        % (b, FAR_TRIS // 1000, LOD_SWITCH, W))
        ctx.K[ob.name] = ob
        made.append(ob)
    for o in cache.values():
        if o is not None:
            bpy.data.objects.remove(o)
    return made


def _base_materials(ob):
    """The GLB importer's ".001" copies of the kit's materials back under the kit's names."""
    import re
    import bpy
    for i, m in enumerate(ob.data.materials):
        if m is None:
            continue
        nm = re.sub(r"\.\d+$", "", m.name)
        tgt = bpy.data.materials.get(nm)
        if tgt is None:
            m.name = nm
        elif tgt is not m:
            ob.data.materials[i] = tgt


def _collapse(ob, target):
    import bpy
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if tris > target:
        dm = ob.modifiers.new("collapse", "DECIMATE")
        dm.decimate_type = "COLLAPSE"
        dm.ratio = target / float(tris)
        dm.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier=dm.name)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    loose = [v for v in bm.verts if not v.link_faces]          # the collapse leaves vertices of dropped faces behind
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.validate()


def build_prop_lods(ctx):
    """The props' LOD1s and the light Canal versions of the hydrant (see PROP_LODS, LIGHT_VARIANTS)."""
    import bpy
    man = _manifest()
    cache = {}

    def source(name):
        if name in ctx.K:
            return ctx.K[name]
        if name in cache:
            return cache[name]
        rec = man.get(name)
        if not rec:
            return None
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(paths.out, rec["glb"]))
        new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
        for o in bpy.data.objects:
            if o not in before and o.type != "MESH":
                bpy.data.objects.remove(o)
        ob = new[0] if new else None
        if ob is not None:
            ob.hide_render = True
            ob.hide_viewport = True
        cache[name] = ob
        return ob

    def make(src_name, name, target, note):
        src = source(src_name)
        if src is None:
            return None
        ob = bpy.data.objects.new(name, src.data.copy())
        ob.data.name = name
        ctx.kit.objects.link(ob)
        ob.matrix_world = src.matrix_world.copy()
        ob.hide_viewport = False
        _base_materials(ob)
        _collapse(ob, target)
        _base_materials(ob)
        ctx.asset(ob, collision="none", notes=note)
        ctx.K[name] = ob
        return ob

    made = []
    for src_name, (name, target) in LIGHT_VARIANTS.items():
        ob = make(src_name, name, target, "The Block's %s collapsed to about %.1fk triangles (same size, slots and pivot) so it can be placed "
                                          "several times in the start view; collision is the placement's collider." % (src_name, target / 1000.0))
        if ob is not None:
            ctx.assets[name]["collision"] = "box"
            made.append(ob)
    for src_name, target in list(PROP_LODS.items()) + list(LIGHT_LOD1.items()):
        ob = make(src_name, src_name + "_LOD1", target, "LOD1 of %s (about %.1fk triangles), drawn past %.0f m from the camera; same slots." %
                  (src_name, target / 1000.0, PROP_LOD_SWITCH))
        if ob is not None:
            made.append(ob)
    for o in cache.values():
        if o is not None:
            bpy.data.objects.remove(o)
    return made


if __name__ == "__main__":
    full, prox, rows = view_triangles()
    for b, r in rows.items():
        print(b, r)
    print("worst view 1, north row: %d triangles at LOD0, %d with the far proxies (budget 1.5 M, aim 1.1 M)" % (full, prox))
