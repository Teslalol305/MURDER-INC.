"""Export assets to art/out/glb (and optionally art/out/fbx) and keep art/out/manifest.json up to date.

    from mi import export
    export.export_asset(ob, family="street", collision="box", cover_height=0.9,
                        notes="two-nozzle hydrant", expect_size=(0.45, 0.3, 0.8))

The object is exported with its pivot at the file origin whatever its placement in the scene. Material slots
keep their names (MI_<Surface>_<Variant> -> tiling set TS_<Surface>_<Variant>, M_<Asset> -> unique set <Asset>)
and carry no textures: Unreal binds the T_<Set>_* files listed in the manifest, so a shared set is never copied
into a mesh file. The 'Wear' colour attribute is exported as COLOR_0.

Units and axes:
    glTF   metres, +Y up (the exporter converts). Unreal's glTF importer scales to centimetres on import.
    FBX    written with UnitScaleFactor 100 ('FBX Units Scale') and object scale 1: with 'Convert Scene Unit' on,
           Unreal imports at the right size with actor scale 1.0 (never 0.01 or 100).
    Either way Unreal(X, Y, Z) = (x, -y, z) * 100 of the Blender coordinates.
"""
import json
import os
import re
import time

import bmesh
import bpy
import numpy as np

from . import geo as _geo
from . import mat as _mat
from . import paths
from . import scene as _scene

NAME_RE = re.compile(r"^SM_[A-Z][A-Za-z0-9]*(_[A-Za-z0-9]+)+$")
SLOT_RE = re.compile(r"^(MI_[A-Z][A-Za-z0-9]*_[A-Za-z0-9]+(_[A-Za-z0-9]+)*|M_[A-Z][A-Za-z0-9]*(_[A-Za-z0-9]+)+)$")
MAX_TRIS = 300000

WEAR_DOC = {"attribute": "Wear (exported as COLOR_0, linear)",
            "R": "cavity dirt / grime", "G": "edge wear / chips (ground: traffic wear, fatigue)",
            "B": "downward leak / rust streaks (ground: oil and liquid stains)",
            "A": "ground splash-back on props and walls; wetness on ground surfaces"}

CONVENTIONS = {
    "units": "metres in Blender and in the files; Unreal imports as centimetres",
    "axes": "Blender: Z up, east = +X, north = +Y. Unreal(X, Y, Z) = (x, -y, z) * 100",
    "pivots": {"props": "centre of the footprint on the ground, forward = +X",
               "street pieces": "west end on the centre line (kerb line for kerb and sidewalk), ground level, running +X",
               "wall modules": "bottom-left corner of the outer face, running +X, outer face toward -Y"},
    "textures": {"BC": "sRGB base colour", "N": "tangent-space normal, OpenGL (+Y up); flip green for DirectX",
                 "ORM": "linear, R = ambient occlusion, G = roughness, B = metallic",
                 "H": "height, 16-bit, range in the set's height_range_m", "E": "emissive (sRGB)"},
    "material_slots": "MI_<Surface>_<Variant> uses tiling set TS_<Surface>_<Variant> with world-scale UVs "
                      "(1 UV unit = tile_m metres); M_<Asset> uses the unique set <Asset>",
    "vertex_colour": WEAR_DOC,
}


def slot_set(slot_name):
    """Texture set a slot name stands for: MI_Asphalt_Aged -> TS_Asphalt_Aged, M_Prop_Hydrant -> Prop_Hydrant."""
    if slot_name.startswith("MI_"):
        return "TS_" + slot_name[3:], "tiling"
    if slot_name.startswith("M_"):
        return slot_name[2:], "unique"
    return None, None


# ------------------------------------------------------------------------------------------------------ validation

def validate(ob, expect_size=None, tol=0.05, strict_names=True):
    """Check an asset before export. Returns (errors, warnings) as lists of strings.
    expect_size: (x, y, z) metres from the brief, None entries are skipped; tol is relative (5 %) with a 2 cm floor."""
    err, warn = [], []
    me = ob.data
    if strict_names and not NAME_RE.match(ob.name):
        err.append("name '%s' does not follow SM_<Family>_<Name>[_<Variant>]" % ob.name)
    if max(abs(s - 1.0) for s in ob.scale) > 1e-5:
        err.append("scale not applied: %s" % (tuple(round(s, 5) for s in ob.scale),))
    if max(abs(r) for r in ob.rotation_euler) > 1e-5 and not ob.get("mi_placed"):
        warn.append("object is rotated in the scene (exported unrotated, pivot at the origin)")
    if len(me.polygons) == 0:
        err.append("no faces")
        return err, warn
    area = np.empty(len(me.polygons), dtype=np.float32)
    me.polygons.foreach_get("area", area)
    zero = int((area < 1e-12).sum())
    if zero:
        err.append("%d zero-area faces" % zero)
    bm = bmesh.new()
    bm.from_mesh(me)
    bad = sum(1 for e in bm.edges if e.is_manifold and not e.is_contiguous)
    loose = sum(1 for v in bm.verts if not v.link_faces)
    closed = all(e.is_manifold for e in bm.edges)
    vol = bm.calc_volume(signed=True) if closed else None
    bm.free()
    if bad:
        err.append("%d edges join faces with opposite winding (inconsistent normals)" % bad)
    if loose:
        warn.append("%d loose vertices" % loose)
    if vol is not None and vol < 0:
        err.append("closed mesh is inside out (negative volume)")
    for i, slot in enumerate(ob.material_slots):
        if slot.material is None:
            err.append("material slot %d is empty" % i)
        elif not SLOT_RE.match(slot.material.name):
            err.append("slot '%s' is neither MI_<Surface>_<Variant> nor M_<Asset>" % slot.material.name)
    if not ob.material_slots:
        err.append("no material")
    if not me.uv_layers:
        err.append("no UV map")
    if _geo.WEAR not in me.color_attributes:
        err.append("no 'Wear' colour attribute (a missing one reads as fully wet: call geo.ensure_wear)")
    st = _geo.stats(ob)
    if st["triangles"] > MAX_TRIS:
        warn.append("%d triangles is over the %d budget" % (st["triangles"], MAX_TRIS))
    if expect_size is not None:
        lo, hi = _scene.bounds(ob)
        size = hi - lo
        for ax, want, got in zip("xyz", expect_size, size):
            if want is None:
                continue
            if abs(got - want) > max(0.02, tol * want):
                err.append("size %s = %.3f m, the brief says %.3f m" % (ax, got, want))
    return err, warn


# --------------------------------------------------------------------------------------------------------- export

class _Stubs:
    """Swap every material for a light stand-in of the same name while exporting, so files carry slot names and
    plain PBR factors but no procedural nodes and no shared textures."""

    def __init__(self, ob, embed=False):
        self.ob, self.embed, self.undo = ob, embed, []

    def __enter__(self):
        for slot in self.ob.material_slots:
            m = slot.material
            if m is None:
                continue
            name = m.name
            set_name, _wf = slot_set(name)
            info = None
            if set_name:
                p = os.path.join(paths.texture_set(set_name), "set.json")
                if os.path.exists(p):
                    with open(p) as f:
                        info = json.load(f)
            m.name = name + "__src"
            col = tuple(info["albedo_mean"]) if info else (0.5, 0.5, 0.5)
            stub = _mat.flat(name, col, info["roughness_mean"] if info else 0.6, info["metallic_mean"] if info else 0.0)
            stub.name = name
            if self.embed and info:
                self._textures(stub, set_name, info)
            slot.material = stub
            self.undo.append((slot, m, stub, name))
        return self

    def _textures(self, stub, set_name, info):
        nt = stub.node_tree
        g = _mat.G(nt)
        bsdf = _mat.principled(stub)
        d = paths.texture_set(set_name)
        f = info["files"]
        if "BC" in f:
            t = g.node("ShaderNodeTexImage")
            t.image = _mat._image(os.path.join(d, f["BC"]), True)
            nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        if "ORM" in f:
            t = g.node("ShaderNodeTexImage")
            t.image = _mat._image(os.path.join(d, f["ORM"]), False)
            _ao, ro, me = g.sep_rgb(t.outputs["Color"])
            nt.links.new(ro, bsdf.inputs["Roughness"])
            nt.links.new(me, bsdf.inputs["Metallic"])
        if "N" in f:
            t = g.node("ShaderNodeTexImage")
            t.image = _mat._image(os.path.join(d, f["N"]), False)
            nm = g.node("ShaderNodeNormalMap")
            nt.links.new(t.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])

    def __exit__(self, *exc):
        for slot, m, stub, name in self.undo:
            slot.material = m
            bpy.data.materials.remove(stub)
            m.name = name
        return False


def _export_copy(ob):
    """A temporary single-user copy at the origin (identity transform): the pivot is the file origin."""
    cp = ob.copy()
    cp.data = ob.data.copy()
    cp.name = ob.name + "__export"
    cp.matrix_world = __import__("mathutils").Matrix.Identity(4)
    bpy.context.scene.collection.objects.link(cp)
    return cp


def export_glb(ob, name=None, path=None, embed_textures=False):
    """Binary glTF of one object. Returns the path."""
    name = name or ob.name
    path = path or os.path.join(paths.glb, name + ".glb")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cp = _export_copy(ob)
    real_name = ob.name
    ob.name = real_name + "__scene"
    cp.name = name
    cp.data.name = name
    try:
        _geo.ensure_wear(cp)
        with _Stubs(cp, embed_textures):
            _scene.select_only(cp)
            bpy.ops.export_scene.gltf(
                filepath=path, export_format="GLB", use_selection=True, export_yup=True, export_apply=False,
                export_materials="EXPORT", export_image_format="AUTO" if embed_textures else "NONE",
                export_vertex_color="ACTIVE", export_all_vertex_colors=False,
                export_active_vertex_color_when_no_material=True, export_texcoords=True, export_normals=True,
                export_tangents=False, export_animations=False, export_skins=False, export_morph=False,
                export_cameras=False, export_lights=False, export_extras=False)
    finally:
        me = cp.data
        bpy.data.objects.remove(cp, do_unlink=True)
        bpy.data.meshes.remove(me)
        ob.name = real_name
    return path


def export_fbx(ob, name=None, path=None):
    """FBX for Unreal: metres declared as UnitScaleFactor 100, object scale 1, triangulated, linear vertex colours."""
    name = name or ob.name
    path = path or os.path.join(paths.fbx, name + ".fbx")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cp = _export_copy(ob)
    real_name = ob.name
    ob.name = real_name + "__scene"
    cp.name = name
    cp.data.name = name
    try:
        _geo.ensure_wear(cp)
        with _Stubs(cp, False):
            _scene.select_only(cp)
            bpy.ops.export_scene.fbx(
                filepath=path, use_selection=True, object_types={"MESH"}, global_scale=1.0, apply_unit_scale=True,
                apply_scale_options="FBX_SCALE_UNITS", axis_forward="-Z", axis_up="Y", use_space_transform=True,
                bake_space_transform=False, mesh_smooth_type="FACE", use_tspace=False, use_triangles=True,
                colors_type="LINEAR", use_mesh_modifiers=True, bake_anim=False, embed_textures=False,
                path_mode="AUTO", use_custom_props=False)
    finally:
        me = cp.data
        bpy.data.objects.remove(cp, do_unlink=True)
        bpy.data.meshes.remove(me)
        ob.name = real_name
    return path


# -------------------------------------------------------------------------------------------------------- manifest

def _locked_update(path, fn):
    """Read-modify-write a JSON file under a lock file, so parallel builds merge instead of overwriting."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lock = path + ".lock"
    t0 = time.time()
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            if time.time() - t0 > 30 or (os.path.exists(lock) and time.time() - os.path.getmtime(lock) > 120):
                try:
                    os.remove(lock)          # stale lock from a crashed build
                except OSError:
                    pass
            time.sleep(0.05)
    try:
        data = {}
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
            except (OSError, ValueError):
                data = {}
        data = fn(data) or data
        tmp = "%s.%d.tmp" % (path, os.getpid())
        with open(tmp, "w") as f:
            json.dump(data, f, indent=1, sort_keys=True)
        os.replace(tmp, path)
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass
    return data


def _rel(p):
    return os.path.relpath(p, paths.out).replace(os.sep, "/")


def set_entry(set_name):
    """Manifest record of a texture set from its set.json (None when the set has not been baked or fetched)."""
    d = paths.texture_set(set_name)
    files = _mat.find_set_files(d)
    if not files:
        return None
    e = {"directory": _rel(d), "textures": {r: _rel(p) for r, p in files.items()},
         "normal_map": "OpenGL (+Y up)", "orm": "R = AO, G = roughness, B = metallic"}
    js = os.path.join(d, "set.json")
    if os.path.exists(js):
        with open(js) as f:
            info = json.load(f)
        for k in ("kind", "surface", "params", "tile_m", "texel_density_px_per_m", "resolution", "height_range_m",
                  "albedo_mean", "roughness_mean", "metallic_mean", "seamless", "seam", "asset",
                  "face_m", "emissive_day", "alpha", "fonts", "note"):
            if k in info:
                e[k] = info[k]
    else:
        rec = _mat.scan_info(set_name)          # a scanned set: the catalogue knows its real size
        if rec:
            e["kind"] = "scan"
            e["source"] = "Poly Haven '%s' (CC0)" % rec.get("slug", "")
            for k in ("surface", "tile_m", "orientation", "px"):
                if rec.get(k):
                    e[k] = rec[k]
            if rec.get("tile_m") and rec.get("px"):
                e["texel_density_px_per_m"] = round(rec["px"][0] / rec["tile_m"][0], 1)
            ms = rec.get("measured") or {}
            if "height_scale_mm" in ms:
                e["height_scale_mm"] = ms["height_scale_mm"]
                e["height_mid"] = ms.get("height_mid")
    return e


def asset_entry(ob, family, collision="box", cover_height=None, notes="", pivot=None, glb=None, fbx=None,
                slots=None, texel_density=None):
    """Manifest record of one asset. slots: optional {slot name: {extra fields}} (e.g. blend sets)."""
    lo, hi = _scene.bounds(ob)
    st = _geo.stats(ob)
    mats = []
    dens = []
    for sl in ob.material_slots:
        m = sl.material
        nm = m.name if m else None
        set_name, wf = slot_set(nm or "")
        rec = {"slot": nm, "workflow": wf, "set": set_name}
        se = set_entry(set_name) if set_name else None
        if se:
            rec["textures"] = se["textures"]
            if "tile_m" in se:
                rec["tile_m"] = se["tile_m"]
            if "texel_density_px_per_m" in se:
                rec["texel_density_px_per_m"] = se["texel_density_px_per_m"]
                dens.append(se["texel_density_px_per_m"])
        else:
            rec["textures"] = None
        if m is not None and m.get("mi_blend_set"):
            rec["blend_set_G"] = m["mi_blend_set"]
        if m is not None and m.get("mi_alpha"):
            rec["alpha_means"] = m["mi_alpha"]
        if m is not None and m.get("mi_tint"):
            rec["tint"] = [round(float(c), 3) for c in m["mi_tint"]]
        if slots and nm in slots:
            rec.update(slots[nm])
        if rec.get("set") and rec["set"] != set_name and "tile_m" not in rec:
            # a tinted slot whose name does not spell its set (MI_Steel_PaintBlack on TS_Steel_ScanPaintGrey):
            # give it the set's real tile and density, as the plainly named slots get theirs
            se2 = set_entry(rec["set"])
            if se2:
                rec.setdefault("textures", None)
                rec["textures"] = rec["textures"] or se2["textures"]
                if "tile_m" in se2:
                    rec["tile_m"] = se2["tile_m"]
                if "texel_density_px_per_m" in se2:
                    rec["texel_density_px_per_m"] = se2["texel_density_px_per_m"]
                    dens.append(se2["texel_density_px_per_m"])
        mats.append(rec)
    u = lambda v: [round(float(v[0]) * 100, 2), round(-float(v[1]) * 100, 2), round(float(v[2]) * 100, 2)]
    return {
        "name": ob.name, "family": family, "glb": _rel(glb) if glb else None, "fbx": _rel(fbx) if fbx else None,
        "triangles": st["triangles"], "vertices": st["vertices"],
        "bounds_m": {"min": [round(float(v), 4) for v in lo], "max": [round(float(v), 4) for v in hi],
                     "size": [round(float(v), 4) for v in (hi - lo)]},
        "bounds_unreal_cm": {"min": [u(lo)[0], u(hi)[1], u(lo)[2]], "max": [u(hi)[0], u(lo)[1], u(hi)[2]]},
        "pivot": pivot or "origin of the file",
        "material_slots": mats,
        "normal_map_convention": "OpenGL (+Y up), as Blender bakes it",
        "vertex_colour": WEAR_DOC,
        "texel_density_px_per_m": texel_density if texel_density is not None else (round(float(np.median(dens)), 1) if dens else None),
        "collision": {"type": collision, "cover_height_m": cover_height},
        "notes": notes,
    }


def write_manifest(assets=(), sets=(), path=None):
    """Merge asset records and texture-set records into art/out/manifest.json."""
    path = path or paths.manifest

    def upd(data):
        data.setdefault("version", 1)
        data["conventions"] = CONVENTIONS
        data.setdefault("assets", {})
        data.setdefault("texture_sets", {})
        for a in assets:
            data["assets"][a["name"]] = a
        for sname in sets:
            e = set_entry(sname)
            if e:
                data["texture_sets"][sname] = e
        data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return data
    return _locked_update(path, upd)


def export_asset(ob, family, collision="box", cover_height=None, notes="", pivot=None, expect_size=None, fbx=False,
                 embed_textures=False, slots=None, strict=True, verbose=True):
    """Validate, export GLB (+ FBX) and record the asset in the manifest. Raises on validation errors when
    strict. collision: 'box', 'convex' or 'complex' (use the render mesh); cover_height: metres of cover the
    asset gives (None when it is not cover)."""
    err, warn = validate(ob, expect_size)
    for w in warn:
        print("    warning %s: %s" % (ob.name, w))
    if err:
        msg = "%s failed validation:\n      " % ob.name + "\n      ".join(err)
        if strict:
            raise ValueError(msg)
        print("    " + msg)
    glb = export_glb(ob, embed_textures=embed_textures)
    fb = export_fbx(ob) if fbx else None
    entry = asset_entry(ob, family, collision, cover_height, notes, pivot, glb, fb, slots)
    sets = [m["set"] for m in entry["material_slots"] if m["set"]]
    sets += [m["blend_set_G"] for m in entry["material_slots"] if m.get("blend_set_G")]
    write_manifest([entry], sets)
    if verbose:
        print("    exported %-34s %7d tris  %s  %.1f kB" % (ob.name, entry["triangles"], "x".join("%.2f" % v for v in entry["bounds_m"]["size"]),
                                                             os.path.getsize(glb) / 1024.0), flush=True)
    return entry
