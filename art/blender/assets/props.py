"""Props: scanned street and shop props brought to the conventions, and the hero gameplay props.

Scanned (Poly Haven, CC0; art/scans/sets.json, files in art/out/scans/models/<slug>/), exported as SM_Prop_*:
    one slot M_<Asset>; the scan's own 2k maps are copied (or packed into an atlas when the scan has several
    texture sets) to art/out/textures/<Asset>/T_<Asset>_BC / _N / _ORM. Real size kept, checked against the
    catalogue (docs/unreal/spec/05b-props.md 2.2), pivot at the footprint centre on the ground (wall pieces: on
    the wall plane), length along +X, front toward -Y (05b 4.1).
Gameplay (modelled here, unique baked sets), exported as SM_Gameplay_* (names of docs/unreal/spec/assets/props.json):
    master reel case (body on its hand truck, lid with the hinge as pivot, reel + tape box in three numbered
    variants, beacon), propane tank, welding rack.
"""
import json
import math
import os
import shutil

import bpy
import numpy as np
from mathutils import Matrix

from mi import geo, mat, paths, render, scene

FAMILY = {"name": "props", "description": "Scanned street and shop props (SM_Prop_*) and the gameplay props (SM_Gameplay_*)"}

MODELS = os.path.join(paths.out, "scans", "models")
DECALS = os.path.join(paths.textures, "_decals")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_COND = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"

# ------------------------------------------------------------------------------------------------- scanned props
# (asset, slug, nodes or None for every mesh, rotation xyz deg, scale, catalogue id or None, collision, cover?, notes)
# cover=True: cover height = the mesh height. Catalogue sizes are L x W x H (05b 2.2).
SCANS = [
    ("SM_Prop_Hydrant_Scan", "fire_hydrant", ["fire_hydrant", "fire_hydrant_cap_01", "fire_hydrant_cap_02",
                                              "fire_hydrant_cap_03", "fire_hydrant_chain"], (0, 0, 0), 1, "hydrant",
     "convex", True, "Scanned red post hydrant, clean paint. Catalogue hydrant 0.35 x 0.35 x 0.75; the scan is taller "
     "(0.80). Alternative to the modelled SM_Prop_Hydrant (street family)."),
    ("SM_Prop_Hydrant_ScanAged", "fire_hydrant", ["fire_hydrant_aged", "fire_hydrant_cap_01_aged", "fire_hydrant_cap_02_aged",
                                                  "fire_hydrant_cap_03_aged", "fire_hydrant_chain_aged"], (0, 0, 0), 1,
     "hydrant", "convex", True, "The same hydrant, weathered paint."),
    ("SM_Prop_JerseyBarrier_Scan", "concrete_road_barrier", None, (0, 0, 0), 1, "jersey_barrier", "convex", True,
     "Precast concrete barrier, 1.55 m segment. Catalogue jersey_barrier is 3.0 x 0.6 x 0.81: two segments end to end "
     "make one catalogue barrier (same width and height)."),
    ("SM_Prop_JerseyBarrier_ScanTall", "concrete_road_barrier_02", None, (0, 0, 0), 1, "jersey_barrier", "convex", True,
     "Taller, narrower barrier segment (1.11 m high): full crouch cover where the catalogue barrier is 0.81."),
    ("SM_Prop_OilDrum_Hazard", "Barrel_01", None, (0, 0, 0), 1, "oil_drum", "convex", True,
     "Red steel drum with flammable-hazard labels. Catalogue oil_drum 0.6 x 0.6 x 0.9. Reads as an explosive barrel: "
     "keep it out of fights unless it is made explosive."),
    ("SM_Prop_OilDrum_Blue", "barrel_03", None, (0, 0, 0), 1, "oil_drum", "convex", True,
     "Blue steel drum, worn. Catalogue oil_drum 0.6 x 0.6 x 0.9."),
    ("SM_Prop_TrashCan_Metal", "metal_trash_can", ["metal_trash_can", "metal_trash_can_lid", "metal_trash_can_handle_left",
                                                    "metal_trash_can_handle_right"], (0, 0, 0), 1, "trash_can", "convex", True,
     "Galvanised lidded can. Catalogue trash_can (0.6 x 0.6 x 0.95) is a wire litter basket; this is the alley / "
     "backyard can."),
    ("SM_Prop_TrashCan_Rust", "metal_trash_can", ["metal_trash_can_rust", "metal_trash_can_rust_lid",
                                                   "metal_trash_can_rust_handle_left", "metal_trash_can_rust_handle_right"],
     (0, 0, 0), 1, "trash_can", "convex", True, "The same can, rusted through."),
    ("SM_Prop_ToolChest_Small", "metal_tool_chest", None, (0, 0, 0), 1, "tool_chest", "box", True,
     "Red steel tool chest (lid, hinges, lock, side handles). Catalogue tool_chest is a 1.09 m roller cabinet: this "
     "is only its top-chest scale; use on the workbench or the floor."),
    ("SM_Prop_ShelfRack_Narrow", "steel_frame_shelves_02", None, (0, 0, 0), 1, "shelf_rack", "box", True,
     "Narrow steel-frame shelf with plywood decks, 2.14 m. Catalogue shelf_rack 2.7 x 0.87 x 3.0 (pallet racking)."),
    ("SM_Prop_ShelfRack_Single", "steel_frame_shelves_01", None, (0, 0, 0), 0.1, "shelf_rack", "box", True,
     "Steel-frame shelf bay, 1.10 m wide (the published mesh is 10x too large and is scaled 0.1)."),
    ("SM_Prop_ShelfRack_Drawers", "steel_frame_shelves_03", None, (0, 0, 0), 1, "shelf_rack", "box", True,
     "Long steel-frame shelving with three drawer boxes, 2.35 x 0.72 x 2.31: closest to the catalogue shelf_rack "
     "(2.7 x 0.87 x 3.0)."),
    ("SM_Prop_CrateWood_Small", "wooden_crate_01", None, (0, 0, 0), 1, "crate_wood", "box", True,
     "Small timber crate with lid and latch. Catalogue crate_wood is a 1.1 x 0.9 x 1.0 shipping crate: stack or "
     "use as loose clutter."),
    ("SM_Prop_CrateWood_Long", "wooden_crate_02", None, (0, 0, 90), 1, "crate_wood", "box", True,
     "Long timber crate with lid (turned so its length runs along X)."),
    ("SM_Prop_CardboardBox", "cardboard_box_01", None, (0, 0, 90), 1, "cardboard_boxes", "box", False,
     "One taped carton. Catalogue cardboard_boxes is a pile of five (0.95 x 0.78 x 0.77): build piles from this."),
    ("SM_Prop_StreetLamp_Post", "street_lamp_01", None, (0, 0, 0), 1, None, "box", False,
     "Short ornamental lamp post, 3.87 m (yards, the court). Not the catalogue street_lamp (7.9 m cobra head)."),
    ("SM_Prop_StreetLamp_Wall", "street_lamp_02", None, (0, 0, 0), 1, None, "none", False,
     "Wall bracket lamp: pivot on the wall plane at the centre of the bracket, the lamp reaching out toward -Y."),
    ("SM_Prop_UtilityBox_Small", "utility_box_01", None, (0, 0, 0), 1, None, "box", True,
     "Blue-grey street utility cabinet, 1.12 m. No catalogue id: kerb and lot dressing."),
    ("SM_Prop_UtilityBox_Large", "utility_box_02", None, (0, 0, 0), 1, None, "box", True,
     "Green double utility cabinet, 0.92 m wide, 1.12 m. No catalogue id."),
    ("SM_Prop_Bench_Scan", "painted_wooden_bench", None, (0, 0, 0), 1, "bench", "convex", True,
     "Painted timber bench, 1.17 m. Catalogue bench is a 1.76 m park bench with iron supports: shorter, simpler."),
    ("SM_Prop_PlasticChair", "plastic_monobloc_chair_01", None, (0, 0, 0), 1, None, "convex", False,
     "White monobloc chair (stoops, the lot booth, the shop). No catalogue id."),
    ("SM_Prop_Tyre", "old_tyre", None, (90, 0, 0), 1, "tire_stack", "convex", False,
     "One worn car tyre lying flat, 0.60 across. Catalogue tire_stack is four 0.77 m tyres to 0.97: stack these."),
    ("SM_Prop_FoodCart_Base", "CoffeeCart_01", ["CoffeeCart_01_cart"], (0, 0, 0), 1, "food_cart", "box", True,
     "Stainless street-vendor cart body only (the scan's coffee props and mugs are left out: real-looking brands). "
     "Base for the catalogue food_cart (2.4 x 1.4 x 2.25 with umbrella and hot-dog gear, still to add)."),
    ("SM_Prop_PropaneTank_Scan", "propane_tank", None, (0, 0, 0), 1, "propane_tank", "convex", False,
     "Red scanned LPG bottle, 0.34 x 0.55: dressing only (beside the food cart). The explosive is the modelled "
     "SM_Gameplay_PropaneTank (catalogue size and colours)."),
    ("SM_Prop_Boombox", "boombox", None, (0, 0, 0), 1, "boombox", "none", False,
     "Scanned portable stereo, 0.72 x 0.19 x 0.47 with the handle (catalogue boombox 0.6 x 0.2 x 0.35). Stands beside "
     "each master case; no emissive level meter (the brief's meter needs a small separate mesh)."),
    ("SM_Prop_SecurityCamera_A", "security_camera_01", None, (0, 0, 0), 1, None, "none", False,
     "Wall-mounted bullet camera: pivot on the wall plane, looking toward -Y."),
    ("SM_Prop_SecurityCamera_B", "security_camera_02", None, (0, 0, 0), 1, None, "none", False,
     "Wall-mounted dome-hood camera: pivot on the wall plane, looking toward -Y."),
    ("SM_Prop_FireExtinguisher", "korean_fire_extinguisher_01", None, (0, 0, 0), 1, None, "convex", False,
     "Red powder extinguisher with hose and gauge. Its Korean headline, maker label and inspection tag are painted "
     "out of the texture."),
    ("SM_Prop_Crowbar", "crowbar_01", None, (0, 90, 0), 1, None, "none", False, "Crowbar lying flat, loose prop."),
    ("SM_Prop_Bat", "baseball_bat", None, (0, 90, 0), 1, None, "none", False, "Wooden baseball bat lying flat, loose prop."),
]

# glass / bulb materials of a scan: they mark the lamp head or the lens (wall pieces point that way)
LENS_HINTS = ("glass", "bulb")


def _patch(img, box, dx, dy):
    """Cover box (x0, y0, x1, y1, PIL pixels on 2048) with the same-size patch shifted by (dx, dy)."""
    x0, y0, x1, y1 = box
    src = img.crop((x0 + dx, y0 + dy, x1 + dx, y1 + dy))
    img.paste(src, (x0, y0))


def _fix_textures(slug, role, key, img):
    """Remove lettering and marks that do not belong in Hollis (all marks in the game are invented)."""
    from PIL import ImageFilter
    if slug == "propane_tank" and role == "BC":
        _patch(img, (540, 960, 960, 1230), -440, 0)                 # a maker's mark and 'Warning' on the body
    if slug == "korean_fire_extinguisher_01" and role == "BC":
        if "_body_" in key:
            _patch(img, (30, 55, 640, 245), 0, 290)                 # Korean headline
            _patch(img, (380, 1190, 880, 1390), 0, -230)            # maker's label
        if "_paper_" in key:
            img = img.filter(ImageFilter.GaussianBlur(28))          # inspection tag: blank, stained card
    return img


def _import(slug):
    d = os.path.join(MODELS, slug)
    g = [f for f in os.listdir(d) if f.endswith(".gltf")][0]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(d, g))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        o["mi_scan"] = slug
    return new


def _tex_roles(m):
    """{'BC'|'N'|'ORM': filepath} of a glTF-imported material, plus constant factors."""
    out = {}
    for n in m.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image:
            fn = os.path.basename(n.image.filepath)
            p = bpy.path.abspath(n.image.filepath)
            if "_diff" in fn:
                out["BC"] = p
            elif "_nor_gl" in fn:
                out["N"] = p
            elif "_arm" in fn:
                out["ORM"] = p
    b = mat.principled(m)
    out["_const"] = dict(bc=tuple(b.inputs["Base Color"].default_value)[:3] if b else (0.5, 0.5, 0.5),
                         rough=b.inputs["Roughness"].default_value if b else 0.6,
                         metal=b.inputs["Metallic"].default_value if b else 0.0)
    return out


def _const_img(role, c, size):
    from PIL import Image
    if role == "BC":
        col = tuple(int(255 * min(1, max(0, v)) ** (1 / 2.2)) for v in c["bc"])
    elif role == "N":
        col = (128, 128, 255)
    else:
        col = (255, int(255 * c["rough"]), int(255 * c["metal"]))
    return Image.new("RGB", size, col)


def _write_scan_set(ob, set_name, slug, groups):
    """groups: list of texture-role dicts, one per distinct texture set on the object (material_index order
    already remapped to the group index). One group: the files are copied. Several: packed side by side (2) or
    2 x 2 (3, 4) into one atlas, and the UVs of each group's faces moved into its cell."""
    from PIL import Image
    d = paths.texture_set(set_name)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    n = len(groups)
    cols, rows = (1, 1) if n == 1 else (2, 1) if n == 2 else (2, 2)
    cell = 2048
    files = {}
    stats = {}
    for role in ("BC", "N", "ORM"):
        out = os.path.join(d, "T_%s_%s.jpg" % (set_name, role))
        if n == 1 and role in groups[0] and slug not in ("propane_tank", "korean_fire_extinguisher_01"):
            shutil.copyfile(groups[0][role], out)
            img = Image.open(out).convert("RGB")
        else:
            img = Image.new("RGB", (cell * cols, cell * rows))
            for i, g in enumerate(groups):
                if role in g:
                    t = Image.open(g[role]).convert("RGB")
                    if t.size != (cell, cell):
                        t = t.resize((cell, cell), Image.LANCZOS)
                    t = _fix_textures(slug, role, os.path.basename(g[role]), t)
                else:
                    t = _const_img(role, g["_const"], (cell, cell))
                cx, cy = i % cols, i // cols
                img.paste(t, (cx * cell, (rows - 1 - cy) * cell))          # PIL rows run top-down, UV v bottom-up
            img.save(out, quality=93)
        files[role] = os.path.basename(out)
        small = np.asarray(img.resize((256, 256)), dtype=np.float32) / 255.0
        stats[role] = small
    if n > 1:
        me = ob.data
        nl = len(me.loops)
        uv = np.empty(nl * 2, np.float32)
        me.uv_layers.active.data.foreach_get("uv", uv)
        uv = uv.reshape(-1, 2)
        npoly = len(me.polygons)
        ls = np.empty(npoly, np.int32)
        lt = np.empty(npoly, np.int32)
        mi = np.empty(npoly, np.int32)
        me.polygons.foreach_get("loop_start", ls)
        me.polygons.foreach_get("loop_total", lt)
        me.polygons.foreach_get("material_index", mi)
        pidx = np.repeat(np.arange(npoly), lt)
        # a face whose UVs sit in another repeat (u in 1..2) is brought back to 0..1 first: same texels
        fmin = np.minimum.reduceat(uv, ls, axis=0)
        shift = np.floor(fmin + 1e-4)
        uv = uv - shift[pidx]
        g = mi[pidx]
        cx, cy = (g % cols).astype(np.float32), (g // cols).astype(np.float32)
        inset = 4.0 / cell                                                # keep inside the cell (mip bleed)
        u = np.clip(uv[:, 0], inset, 1 - inset)
        v = np.clip(uv[:, 1], inset, 1 - inset)
        uv = np.stack([(u + cx) / cols, (v + cy) / rows], axis=1)
        me.uv_layers.active.data.foreach_set("uv", uv.ravel())
    bc_lin = stats["BC"] ** 2.2
    lum = bc_lin.reshape(-1, 3) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    rec = mat.scan_info(slug) or {}
    info = {"set": set_name, "kind": "scan_unique", "asset": "SM_" + set_name, "files": files,
            "source": "Poly Haven '%s' (CC0), 2k maps%s" % (slug, "" if n == 1 else ", packed %d x %d" % (cols, rows)),
            "licence": rec.get("licence", "CC0, Poly Haven"),
            "resolution": [cell * cols, cell * rows],
            "convention": {"BC": "sRGB base colour", "N": "tangent-space normal, OpenGL (+Y up)",
                           "ORM": "linear: R = ambient occlusion, G = roughness, B = metallic"},
            "albedo_mean": [round(float(v), 4) for v in bc_lin.reshape(-1, 3).mean(axis=0)],
            "albedo_luminance_p01_p50_p99": [round(float(np.percentile(lum, q)), 4) for q in (1, 50, 99)],
            "roughness_mean": round(float(stats["ORM"][..., 1].mean()), 4),
            "metallic_mean": round(float(stats["ORM"][..., 2].mean()), 4),
            "texel_density_px_per_m": round(geo.uv_texel_density(ob, cell * cols), 1),
            "uv_hash": geo.uv_hash(ob)}
    with open(os.path.join(d, "set.json"), "w") as f:
        json.dump(info, f, indent=1, sort_keys=True)
    return d


def scan_prop(ctx, spec, cache):
    name, slug, nodes, rot, scale, cat_id, collision, cover, notes = spec
    if slug not in cache:
        cache[slug] = _import(slug)
    objs = [o for o in cache[slug] if o.type == "MESH" and (nodes is None or o.name in nodes)]
    if nodes is not None and len(objs) != len(nodes):
        raise RuntimeError("%s: nodes %s not all found in %s" % (name, nodes, [o.name for o in cache[slug]]))
    parts = []
    for o in objs:                                     # world-space copies (the glTF hierarchy is dropped)
        cp = o.copy()
        cp.data = o.data.copy()
        cp.parent = None
        cp.matrix_world = o.matrix_world.copy()
        ctx.col.objects.link(cp)
        scene.select_only(cp)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        parts.append(cp)
    ob = geo.join(parts, name, ctx.col)
    me = ob.data
    # one UV map named as the pipeline expects, no imported colour attributes
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    me.uv_layers[0].name = geo.UV
    for ca in list(me.color_attributes):
        me.color_attributes.remove(ca)
    # orientation and scale, applied through the object so custom normals follow
    ob.rotation_mode = "XYZ"                            # glTF imports use quaternions
    ob.rotation_euler = [math.radians(a) for a in rot]
    ob.scale = (scale, scale, scale)
    scene.select_only(ob)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # wall pieces: the lens / lamp head (glass, bulb faces) points to -Y, the wall is at +Y
    mats = list(me.materials)
    npoly = len(me.polygons)
    mi = np.empty(npoly, np.int32)
    me.polygons.foreach_get("material_index", mi)
    cen = np.empty(npoly * 3, np.float32)
    me.polygons.foreach_get("center", cen)
    cen = cen.reshape(-1, 3)
    wall = collision == "none" and any(h in (m.name.lower() if m else "") for m in mats for h in LENS_HINTS) \
        and slug != "street_lamp_01"
    if wall:
        lens = np.isin(mi, [i for i, m in enumerate(mats) if m and any(h in m.name.lower() for h in LENS_HINTS)])
        lo, hi = scene.bounds(ob)
        d = cen[lens].mean(axis=0)[:2] - (lo[:2] + hi[:2]) / 2
        ang = math.degrees(math.atan2(d[1], d[0]))                 # where the lens points
        turn = -90.0 - ang
        turn = round(turn / 90.0) * 90.0
        if abs(turn) > 1:
            ob.rotation_euler = (0, 0, math.radians(turn))
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        lo, hi = scene.bounds(ob)
        co, _no = geo.arrays(ob)
        near = co[:, 1] > hi[1] - 0.02                             # the mounting plate against the wall
        pz = float(co[near, 2].mean()) if near.any() else float((lo[2] + hi[2]) / 2)
        pivot = ((lo[0] + hi[0]) / 2, hi[1], pz)
        pivot_note = "on the wall plane (+Y face), centre of the mounting plate; looks / reaches toward -Y"
    else:
        lo, hi = scene.bounds(ob)
        pivot = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2])
        pivot_note = "centre of the footprint on the ground; length along X, front toward -Y"
    me.transform(Matrix.Translation((-pivot[0], -pivot[1], -pivot[2])))
    me.update()
    # material: group the slots by texture set, one material slot in the end
    groups, gidx = [], []
    for m in mats:
        r = _tex_roles(m) if m else {"_const": dict(bc=(0.5, 0.5, 0.5), rough=0.6, metal=0.0)}
        sig = tuple(r.get(k) for k in ("BC", "N", "ORM"))
        sigs = [tuple(g.get(k) for k in ("BC", "N", "ORM")) for g in groups]
        if sig in sigs and any(sig):
            gidx.append(sigs.index(sig))
        else:
            groups.append(r)
            gidx.append(len(groups) - 1)
    mi = np.array(gidx, np.int32)[mi] if len(gidx) else mi
    me.polygons.foreach_set("material_index", mi)
    set_name = name[3:]
    d = _write_scan_set(ob, set_name, slug, groups)
    me.materials.clear()
    me.polygons.foreach_set("material_index", np.zeros(npoly, np.int32))
    m = mat.from_texture_set(d, name="M_" + set_name, masks=False, macro=0.0, ao_strength=0.0, alpha="none")
    me.materials.append(m)
    if set_name not in ctx.sets:
        ctx.sets.append(set_name)
    # tidy the scan: merge-free cleanup of degenerate faces only
    _clean(ob)
    lo, hi = scene.bounds(ob)
    size = tuple(round(float(v), 3) for v in hi - lo)
    cat = ""
    if cat_id:
        cat = " Stands for catalogue id '%s'." % cat_id
    full = "%s%s Scan: Poly Haven '%s' (CC0), %s, %d texture set%s. Size %.2f x %.2f x %.2f m." % (
        notes, cat, slug, "real size" if scale == 1 else "scaled %g" % scale, len(groups), "s packed into one atlas" if len(groups) > 1 else "",
        *size)
    ctx.asset(ob, collision=collision, cover_height=round(size[2], 2) if cover else None, notes=full,
              pivot=pivot_note, expect_size=size)
    ob["mi_catalogue_id"] = cat_id or ""
    ctx.log("scan %-30s %-28s %6d tris  %s  groups %d" % (name, slug, geo.stats(ob)["triangles"], size, len(groups)))
    return ob


def _clean(ob):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bad = [f for f in bm.faces if f.calc_area() < 1e-12]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES_ONLY")
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(ob.data)
    bm.free()


def build_scans(ctx):
    cache = {}
    out = []
    for spec in SCANS:
        o = ctx.args.only
        if o and spec[0] not in o and "scans" not in o and not any(k.startswith("props_") for k in o):
            continue
        out.append(scan_prop(ctx, spec, cache))
    for objs in cache.values():                       # drop the imported originals
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
    return out




# ================================================================================================ gameplay props
# Colours from the briefs (sRGB hex) as linear values for the procedural source materials that get baked.

def lin(hexs):
    h = hexs.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(round(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4, 4) for v in c)


_MATS = {}


def pm(key, kind, **kw):
    """Cached procedural source material (baked into the unique set later)."""
    if key not in _MATS:
        _MATS[key] = mat.make("SRC_" + key, kind, alpha="splash", **kw)
    return _MATS[key]


def emissive(key, color, strength=3.0, rough=0.3):
    if key not in _MATS:
        m = mat.flat("SRC_" + key, color, rough, 0.0)
        b = mat.principled(m)
        b.inputs["Emission Color"].default_value = (*color, 1.0)
        b.inputs["Emission Strength"].default_value = strength
        _MATS[key] = m
    return _MATS[key]


def materials():
    P = dict
    return P(
        laminate=pm("Laminate", "plastic", Color=lin("#18191b"), Roughness=0.52, Scratches=0.55, Sun_Fade=0.15),
        alu=pm("Aluminium", "painted_steel", Paint_Color=(0.62, 0.63, 0.64), Paint_Metallic=1.0, Paint_Roughness=0.34,
               Chipping=0.0, Rust=0.0, Chalking=0.25, Old_Coat=(0.3, 0.3, 0.3), Primer_Color=(0.5, 0.5, 0.5)),
        chrome=pm("Chrome", "painted_steel", Paint_Color=(0.86, 0.86, 0.87), Paint_Metallic=1.0, Paint_Roughness=0.1,
                  Chipping=0.0, Rust=0.05, Chalking=0.0, Old_Coat=(0.5, 0.5, 0.5), Primer_Color=(0.4, 0.4, 0.4)),
        galv=pm("Galv", "galvanised", Age=0.55, Rust=0.12),
        rubber=pm("Rubber", "rubber", Age=0.45),
        foam=pm("Foam", "plastic", Color=(0.011, 0.011, 0.012), Roughness=0.96, Scratches=0.0, Sun_Fade=0.0),
        darkplastic=pm("DarkPlastic", "plastic", Color=(0.016, 0.017, 0.019), Roughness=0.42, Scratches=0.4, Sun_Fade=0.1),
        tape=pm("Tape", "plastic", Color=lin("#422a18"), Roughness=0.32, Scratches=0.05, Sun_Fade=0.0),
        gold=pm("Gold", "painted_steel", Paint_Color=lin("#e7b53a"), Paint_Metallic=1.0, Paint_Roughness=0.25,
                Chipping=0.06, Rust=0.0, Chalking=0.05, Old_Coat=(0.3, 0.3, 0.3), Primer_Color=(0.6, 0.6, 0.6)),
        card=pm("Cardboard", "plastic", Color=(0.40, 0.27, 0.14), Roughness=0.88, Scratches=0.3, Sun_Fade=0.35),
        offwhite=pm("OffWhite", "plastic", Color=lin("#f1efe6"), Roughness=0.6, Scratches=0.2, Sun_Fade=0.0),
        led=emissive("LED", lin("#3dff7a"), 6.0),
        lens=emissive("Lens", lin("#f6c21a"), 2.5, 0.15),
        white_paint=pm("WhitePaint", "painted_steel", Paint_Color=lin("#e6e4dc"), Paint_Roughness=0.38, Chipping=0.22,
                       Rust=0.25, Chalking=0.3, Old_Coat=(0.35, 0.36, 0.37), Primer_Color=(0.24, 0.075, 0.05)),
        red_paint=pm("RedPaint", "painted_steel", Paint_Color=lin("#b3261e"), Paint_Roughness=0.36, Chipping=0.25,
                     Rust=0.25, Chalking=0.3, Old_Coat=(0.36, 0.33, 0.10)),
        brass=pm("Brass", "painted_steel", Paint_Color=lin("#b58a3a"), Paint_Metallic=1.0, Paint_Roughness=0.32,
                 Chipping=0.0, Rust=0.08, Chalking=0.2, Old_Coat=(0.2, 0.15, 0.05), Primer_Color=(0.1, 0.25, 0.15)),
        darksteel=pm("DarkSteel", "painted_steel", Paint_Color=lin("#2a2d31"), Paint_Roughness=0.5, Chipping=0.4,
                     Rust=0.45, Chalking=0.2, Old_Coat=(0.2, 0.2, 0.2)),
        o2=pm("O2Green", "painted_steel", Paint_Color=lin("#2f6b4f"), Paint_Roughness=0.4, Chipping=0.3, Rust=0.3,
              Chalking=0.35, Old_Coat=(0.3, 0.3, 0.32)),
        acet=pm("AcetMaroon", "painted_steel", Paint_Color=lin("#7a1a1a"), Paint_Roughness=0.4, Chipping=0.3, Rust=0.3,
                Chalking=0.35, Old_Coat=(0.3, 0.3, 0.32)),
        hose_red=pm("HoseRed", "rubber", Color=(0.36, 0.025, 0.02), Roughness=0.6, Age=0.4),
        hose_green=pm("HoseGreen", "rubber", Color=(0.03, 0.13, 0.05), Roughness=0.6, Age=0.4),
        steel=pm("Steel", "steel", Rust=0.4),
        stencil=pm("Stencil", "plastic", Color=(0.80, 0.80, 0.78), Roughness=0.5, Scratches=0.6, Sun_Fade=0.2),
        board=pm("Board", "plastic", Color=(0.80, 0.80, 0.78), Roughness=0.55, Scratches=0.3, Sun_Fade=0.1),
    )


# ------------------------------------------------------------------------------------------------- decal images

def _font(size, cond=False):
    from PIL import ImageFont
    return ImageFont.truetype(FONT_COND if cond and os.path.exists(FONT_COND) else FONT, size)


def _ctext(d, xy, text, size, fill, cond=False, anchor="mm", italic=False):
    d.text(xy, text, font=_font(size, cond), fill=fill, anchor=anchor)


def _lozenge(d, box, fill, ink, text_size):
    x0, y0, x1, y1 = box
    r = (y1 - y0) // 2
    d.rounded_rectangle(box, radius=r, fill=fill)
    d.rounded_rectangle((x0 + r * 0.12, y0 + r * 0.12, x1 - r * 0.12, y1 - r * 0.12), radius=int(r * 0.88), outline=ink,
                        width=max(2, r // 14))
    _ctext(d, ((x0 + x1) // 2, (y0 + y1) // 2 + r // 14), "IPX", text_size, ink)


def make_decals():
    """Label art for the gameplay props (all text invented; IPX is the client's own mark)."""
    from PIL import Image, ImageDraw
    os.makedirs(DECALS, exist_ok=True)
    out = {}

    def save(img, key):
        p = os.path.join(DECALS, key + ".png")
        img.save(p)
        out[key] = p

    # IPX lozenge, white on the black lid; and the foam-side one
    for key, bg in (("lozenge_lid", (24, 25, 27)), ("lozenge_foam", (20, 20, 21))):
        im = Image.new("RGB", (1200, 500), bg)
        _lozenge(ImageDraw.Draw(im), (0, 0, 1199, 499), (244, 242, 236), (22, 22, 24), 300)
        save(im, key)
    # luggage tag 0.20 x 0.10
    im = Image.new("RGB", (1200, 600), (241, 239, 230))
    d = ImageDraw.Draw(im)
    d.ellipse((40, 255, 130, 345), fill=(205, 200, 185), outline=(150, 145, 130), width=8)
    d.ellipse((66, 281, 104, 319), fill=(60, 58, 54))
    _lozenge(d, (190, 50, 560, 205), (24, 25, 27), (244, 242, 236), 105)
    _ctext(d, (690, 300), "TRACKER", 150, (24, 25, 27), cond=True)
    _ctext(d, (880, 128), "IPX.EXCHANGE", 52, (60, 60, 64), cond=True)
    rng = np.random.default_rng(7)
    x = 200
    while x < 1120:                                     # barcode
        w = int(rng.choice([5, 5, 9, 14]))
        d.rectangle((x, 410, x + w, 545), fill=(20, 20, 22))
        x += w + int(rng.choice([5, 8, 11]))
    _ctext(d, (190, 575), "0 21403 30316 7", 30, (40, 40, 44), anchor="lm")
    d.rectangle((6, 6, 1193, 593), outline=(190, 185, 170), width=6)
    save(im, "tag")
    # tracker LCD 0.084 x 0.035: near black, IPX gold italic, four signal bars (emissive)
    im = Image.new("RGB", (960, 400), (6, 9, 8))
    d = ImageDraw.Draw(im)
    txt = Image.new("RGBA", (600, 300), (0, 0, 0, 0))
    ImageDraw.Draw(txt).text((300, 150), "IPX", font=_font(220), fill=(246, 194, 26, 255), anchor="mm")
    txt = txt.transform(txt.size, Image.AFFINE, (1, 0.22, -40, 0, 1, 0), resample=Image.BICUBIC)   # italic
    im.paste(txt, (40, 50), txt)
    for i in range(4):
        h = 60 + i * 55
        d.rectangle((640 + i * 70, 330 - h, 690 + i * 70, 330), fill=(61, 255, 122) if i < 3 else (30, 70, 40))
    save(im, "lcd")
    # master reel box label 0.26 x 0.26 and spine, three variants
    for n in (1, 2, 3):
        im = Image.new("RGB", (1024, 1024), (230, 223, 200))
        d = ImageDraw.Draw(im)
        ink = (34, 30, 26)
        d.rectangle((24, 24, 999, 999), outline=ink, width=6)
        d.rectangle((24, 24, 999, 170), fill=ink)
        _ctext(d, (512, 100), "MASTER REEL", 104, (230, 223, 200), cond=True)
        _ctext(d, (512, 250), "MURDER INC.", 96, ink)
        d.line((60, 320, 964, 320), fill=ink, width=4)
        _ctext(d, (512, 450), "REEL %d / 3" % n, 150, (150, 24, 20), cond=True)
        d.line((60, 580, 964, 580), fill=ink, width=4)
        _ctext(d, (70, 650), "SPEED 30 IPS", 60, ink, cond=True, anchor="lm")
        _ctext(d, (70, 740), "TAPE 2 IN · 24 TRK", 60, ink, cond=True, anchor="lm")
        _ctext(d, (70, 830), "SIDE A  ·  EQ AES  ·  +6 dB", 44, (80, 72, 64), cond=True, anchor="lm")
        for k in range(4):                                         # hand-ruled track log lines
            d.line((70, 900 + k * 22, 640, 900 + k * 22), fill=(150, 140, 120), width=2)
        _lozenge(d, (700, 860, 960, 968), (34, 30, 26), (230, 223, 200), 70)
        save(im, "reel_label_%d" % n)
        im = Image.new("RGB", (1200, 290), (230, 223, 200))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 1199, 289), outline=ink, width=8)
        _ctext(d, (600, 145), "MURDER INC.  ·  MASTER  ·  REEL %d / 3" % n, 64, ink, cond=True)
        save(im, "reel_spine_%d" % n)
        im = Image.new("RGB", (700, 230), (236, 232, 218))
        d = ImageDraw.Draw(im)
        _ctext(d, (350, 118), "REEL %d / 3" % n, 128, (34, 30, 26), cond=True)
        save(im, "reel_hub_%d" % n)
    # flammable gas diamond (class 2), drawn upright in the square that bounds the diamond
    im = Image.new("RGB", (800, 800), (211, 40, 31))
    d = ImageDraw.Draw(im)
    d.polygon([(400, 30), (770, 400), (400, 770), (30, 400)], outline=(255, 255, 255), width=16)
    flame = [(400, 170), (455, 260), (470, 330), (450, 390), (500, 360), (505, 300), (540, 380), (530, 450), (480, 500),
             (320, 500), (270, 450), (265, 380), (300, 320), (320, 360), (330, 280), (370, 230)]
    d.polygon(flame, fill=(255, 255, 255))
    d.rectangle((300, 515, 500, 530), fill=(255, 255, 255))
    _ctext(d, (400, 640), "2", 140, (255, 255, 255))
    save(im, "hazard")
    # welding placard 0.36 x 0.25
    im = Image.new("RGB", (1080, 750), (246, 245, 240))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1079, 230), fill=(20, 20, 22))
    d.ellipse((90, 30, 990, 200), fill=(194, 38, 30))
    _ctext(d, (540, 118), "DANGER", 150, (255, 255, 255))
    _ctext(d, (540, 340), "FLAMMABLE GAS", 104, (20, 20, 22), cond=True)
    _ctext(d, (540, 495), "NO SMOKING", 104, (20, 20, 22), cond=True)
    _ctext(d, (540, 640), "NO OPEN FLAME", 104, (20, 20, 22), cond=True)
    d.rectangle((4, 4, 1075, 745), outline=(20, 20, 22), width=8)
    save(im, "placard")
    # pressure gauge face
    im = Image.new("RGB", (512, 512), (238, 236, 228))
    d = ImageDraw.Draw(im)
    d.ellipse((6, 6, 506, 506), outline=(30, 30, 30), width=10)
    for k in range(41):
        a = math.radians(225 - k * 270 / 40)
        r0 = 200 if k % 5 else 175
        d.line((256 + r0 * math.cos(a), 256 - r0 * math.sin(a), 256 + 225 * math.cos(a), 256 - 225 * math.sin(a)),
               fill=(25, 25, 25) if k < 33 else (190, 30, 25), width=5 if k % 5 else 9)
    a = math.radians(225 - 0.42 * 270)
    d.line((256, 256, 256 + 190 * math.cos(a), 256 - 190 * math.sin(a)), fill=(20, 20, 20), width=10)
    d.ellipse((236, 236, 276, 276), fill=(20, 20, 20))
    _ctext(d, (256, 380), "PSI", 46, (40, 40, 40))
    save(im, "gauge")
    return out


def decal_mat(key, img_path, rough=0.5, emit=0.0):
    name = "SRC_Decal_" + key
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "Decal"
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(img_path, check_existing=True)
    t.image.colorspace_settings.name = "sRGB"
    t.extension = "EXTEND"
    nt.links.new(uvn.outputs["UV"], t.inputs["Vector"])
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if emit:
        nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    _MATS[name] = m
    return m


def decal(name, material, w, h, shape="rect", n=(6, 4), outline=None):
    """Flat label in XY facing +Z, centred; both UV maps hold the label coordinates (the unique unwrap later
    overwrites UVMap; 'Decal' keeps reading the art). shape: rect, diamond (w, h = the two diagonals) or pill."""
    import bmesh
    bm = bmesh.new()
    if shape == "pill":
        r = h / 2
        pts = []
        for cx, a0 in ((w / 2 - r, -90), (-(w / 2 - r), 90)):
            for k in range(13):
                a = math.radians(a0 + 180 * k / 12)
                pts.append((cx + r * math.cos(a), r * math.sin(a)))
        vs = [bm.verts.new((x, y, 0)) for x, y in pts]
        f = bm.faces.new(vs)
        bmesh.ops.triangulate(bm, faces=[f], quad_method="BEAUTY", ngon_method="BEAUTY")
    else:
        nx, ny = n
        grid = {}
        for i in range(nx + 1):
            for j in range(ny + 1):
                a, b = i / nx, j / ny
                if shape == "diamond":
                    x, y = (a - b) * w / 2, (a + b - 1) * h / 2
                else:
                    x, y = (a - 0.5) * w, (b - 0.5) * h
                grid[i, j] = bm.verts.new((x, y, 0))
        for i in range(nx):
            for j in range(ny):
                bm.faces.new((grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]))
    ob = geo.new(name, bm, smooth=None)
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", vi)
    uv = np.stack([co[vi, 0] / w + 0.5, co[vi, 1] / h + 0.5], axis=1).ravel()
    for nm in (geo.UV, "Decal"):
        lay = me.uv_layers.get(nm) or me.uv_layers.new(name=nm)
        lay.data.foreach_set("uv", uv)
    me.uv_layers.active = me.uv_layers[geo.UV]
    me.materials.append(material)
    return ob


def wrap_cyl(ob, r, phi0=0.0, z0=0.0):
    """Bend a flat part (XY plane, +Z outward) round a vertical cylinder of radius r: x becomes arc length,
    y height above z0, z the offset from the surface. phi0 = 0 faces -Y (the front), 180 the back."""
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    phi = math.radians(phi0) + co[:, 0] / r
    R = r + co[:, 2]
    new = np.stack([R * np.sin(phi), -R * np.cos(phi), z0 + co[:, 1]], axis=1)
    me.vertices.foreach_set("co", new.astype(np.float32).ravel())
    me.update()
    return ob


def prism(pts, z0, z1, name="Prism"):
    """Straight prism of a closed (x, y) polygon (counter-clockwise) between z0 and z1."""
    n = len(pts)
    v = [(x, y, z0) for x, y in pts] + [(x, y, z1) for x, y in pts]
    faces = [list(range(n - 1, -1, -1)), list(range(n, 2 * n))]
    faces += [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    return geo.from_arrays(name, v, faces)


def part(ob, material):
    geo.assign(ob, material)
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name=geo.UV)
    return ob


def X(ob, loc=(0, 0, 0), rot=(0, 0, 0)):
    return geo.transform(ob, loc=loc, rot=rot) or ob


def _degenerate(ob):
    """Booleans and curve meshes leave slivers: dissolve them, then drop what is still zero-area."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
    bad = [f for f in bm.faces if f.calc_area() < 1e-10]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    me = ob.data                                       # the same test as export.validate (float32 areas)
    area = np.empty(len(me.polygons), np.float32)
    me.polygons.foreach_get("area", area)
    if (area < 1e-11).any():
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(area < 1e-11)[0]], context="FACES_ONLY")
        bm.to_mesh(me)
        bm.free()


def finish_hero(ctx, parts, name, res, wear_kw=None, densify=0.03, weights=None):
    """Join, wear masks from the shape, unique unwrap, bake (or reuse) the unique set, drop the decal UVs."""
    ob = geo.join(parts, name, ctx.col)
    me = ob.data
    me.uv_layers.active = me.uv_layers[geo.UV]
    me.uv_layers[geo.UV].active_render = True
    _degenerate(ob)
    geo.smooth_by_angle(ob, 40)
    if densify:
        geo.densify(ob, densify, 2)
    kw = dict(cavity=0.9, edge=0.8, leak=0.4, splash=0.7, ao_distance=0.04, ao_rays=8, leak_auto=True,
              leak_length=0.12, leak_width=0.006)
    kw.update(wear_kw or {})
    geo.wear_from_geometry(ob, **kw)
    _degenerate(ob)
    geo.weighted_normals(ob)
    dens = geo.uv_unwrap(ob, res=res, angle=60, margin_px=6, weights=weights)
    ctx.log("%s: %d tris, %.0f px/m at %d" % (name, geo.stats(ob)["triangles"], dens, res))
    ctx.unique_set(ob, res=res, ground=True)
    dl = me.uv_layers.get("Decal")
    if dl is not None:
        me.uv_layers.remove(dl)
    me.uv_layers.active = me.uv_layers[geo.UV]
    return ob


# ------------------------------------------------------------------------------------------- master reel case
# Blender frame of the whole assembly (05b 2.5.1 converted by 4.1): footprint centre on the ground, the case
# front (latches, tag, tracker) toward -Y, the hand truck on the -X side, the boombox toward +X.

CX, CW, CD, Z0, Z1 = -0.19, 0.42, 0.32, 0.03, 0.53          # case body centre x, width, depth, bottom, top
REEL_C = (CX, -0.045, 0.630)                                   # reel centre, tilted back 40 deg on its box
REEL_TILT = 50.0                                               # rotation about X of the reel's axis (+Z -> front-up)
BOX_C = (CX, 0.026, 0.616)
HINGE = (CX, CD / 2, Z1)
LID_OPEN = -95.0
TRACK_Y, LOZ_Y = -0.268, -0.168                                # lid frame: progress track and inside lozenge


def _edges(M, x0, x1, y0, y1, z0, z1, bar=0.018, proud=0.002, top=True, bottom=True, verticals=True):
    """Aluminium edge extrusions along the edges of a box, standing proud of its faces."""
    off = bar / 2 - proud
    out = []
    lx, ly = x1 - x0 - 2 * off, y1 - y0 - 2 * off
    for z, want in ((z0 + off, bottom), (z1 - off, top)):
        if not want:
            continue
        for y in (y0 + off, y1 - off):
            out.append(X(geo.box((lx + bar, bar, bar), bevel=0.002, base=False), ((x0 + x1) / 2, y, z)))
        for x in (x0 + off, x1 - off):
            out.append(X(geo.box((bar, ly - bar, bar), bevel=0.002, base=False), (x, (y0 + y1) / 2, z)))
    if verticals:
        for x in (x0 + off, x1 - off):
            for y in (y0 + off, y1 - off):
                out.append(X(geo.box((bar, bar, z1 - z0 - 2 * off - bar), bevel=0.002, base=False), (x, y, (z0 + z1) / 2)))
    return [part(o, M["alu"]) for o in out]


def _balls(M, pts, r=0.015):
    return [part(X(geo.sphere(r, 20, 12), p), M["chrome"]) for p in pts]


def build_case_body(ctx, M, D):
    P = []
    x0, x1, y0, y1 = CX - CW / 2, CX + CW / 2, -CD / 2, CD / 2
    shell = X(geo.box((CW - 0.004, CD - 0.004, 0.485), bevel=0.004), (CX, 0, Z0))
    P.append(part(shell, M["laminate"]))
    P += _edges(M, x0, x1, y0, y1, Z0, Z1, top=True)
    P.append(part(X(geo.box((CW - 0.034, CD - 0.034, 0.02), bevel=0.003), (CX, 0, 0.49)), M["foam"]))
    o = 0.006
    P += _balls(M, [(x, y, Z0 + o) for x in (x0 + o, x1 - o) for y in (y0 + o, y1 - o)])
    # two butterfly latches on the front, hanging open (the lid is up)
    for lx in (CX - 0.12, CX + 0.12):
        P.append(part(X(geo.box((0.052, 0.005, 0.046), bevel=0.0015, base=False), (lx, y0 - 0.0045, 0.488)), M["chrome"]))
        bf = X(geo.box((0.034, 0.006, 0.026), bevel=0.002, base=False), (0, 0, -0.012))
        X(bf, (lx, y0 - 0.010, 0.478), (-25, 0, 0))
        P.append(part(bf, M["chrome"]))
        ring = X(geo.torus(0.009, 0.0022, 16, 6), (0, 0, 0), (90, 0, 0))
        P.append(part(X(ring, (lx, y0 - 0.014, 0.455)), M["chrome"]))
        P.append(part(X(geo.box((0.036, 0.004, 0.016), bevel=0.0012, base=False), (lx, y0 - 0.004, 0.508)), M["chrome"]))
    # recessed handle on the +X end: chrome dish and a rubber grip
    P.append(part(X(geo.box((0.004, 0.17, 0.085), bevel=0.0015, base=False), (x1 + 0.002, 0, 0.36)), M["chrome"]))
    P.append(part(X(geo.box((0.016, 0.12, 0.018), bevel=0.005, base=False), (x1 + 0.009, 0, 0.352)), M["darkplastic"]))
    # luggage tag on the front, on a strap from the left latch
    tag = part(X(geo.box((0.2, 0.0014, 0.1), bevel=0.0005, base=False), (0, 0, 0)), M["offwhite"])
    lab = decal("tag_art", decal_mat("tag", D["tag"], 0.6), 0.198, 0.098)
    X(lab, (0, 0, 0.00072), (0, 0, 0))
    X(lab, (0, 0, 0), (90, 0, 0))          # +Z -> -Y face
    tagp = geo.join([tag, lab], "tag")
    X(tagp, (CX - 0.07, y0 - 0.006, 0.355), (0, -4, 0))
    P.append(tagp)
    P.append(part(geo.pipe([(CX - 0.165, y0 - 0.006, 0.36), (CX - 0.175, y0 - 0.011, 0.41), (CX - 0.13, y0 - 0.012, 0.455)],
                           radius=0.0025, segments=8, bend_radius=0.02), M["darkplastic"]))
    # IPX tracker clipped to the front: body, LCD, green LED, whip antenna
    tx, tz = CX + 0.115, 0.32
    P.append(part(X(geo.box((0.11, 0.03, 0.065), bevel=0.006, base=False), (tx, y0 - 0.017, tz)), M["darkplastic"]))
    P.append(part(X(geo.box((0.03, 0.012, 0.09), bevel=0.002, base=False), (tx, y0 + 0.001 - 0.006, tz + 0.02)), M["darkplastic"]))
    lcd = decal("lcd", decal_mat("lcd", D["lcd"], 0.2, emit=2.0), 0.084, 0.035)
    X(lcd, (0, 0, 0), (90, 0, 0))
    X(lcd, (tx - 0.008, y0 - 0.0325, tz + 0.006))
    P.append(lcd)
    P.append(part(X(geo.sphere(0.0042, 12, 8), (tx + 0.042, y0 - 0.032, tz - 0.022)), M["led"]))
    P.append(part(X(geo.cylinder(0.0018, 0.17, 8), (tx + 0.04, y0 - 0.017, tz + 0.0325)), M["darkplastic"]))
    P.append(part(X(geo.sphere(0.0032, 10, 6), (tx + 0.04, y0 - 0.017, tz + 0.2025)), M["darkplastic"]))
    P.append(part(X(geo.cylinder(0.006, 0.014, 12), (tx + 0.04, y0 - 0.017, tz + 0.0325)), M["darkplastic"]))
    # hand truck: toe plate, two rails bent into the handle, cross bars, axle, two 0.18 m wheels
    rx = x0 - 0.026
    P.append(part(X(geo.box((0.31, 0.30, 0.008), bevel=0.002), (rx + 0.155, 0, 0.022)), M["galv"]))
    P.append(part(X(geo.box((0.012, 0.30, 0.05), bevel=0.002), (rx, 0, 0.022)), M["galv"]))
    path = [(rx, -0.17, 0.03), (rx, -0.17, 0.86), (rx - 0.02, -0.10, 0.96), (rx - 0.02, 0.10, 0.96), (rx, 0.17, 0.86), (rx, 0.17, 0.03)]
    P.append(part(geo.pipe(path, radius=0.013, segments=14, bend_radius=0.06, bend_segments=8), M["galv"]))
    P.append(part(X(geo.cylinder(0.0175, 0.15, 16, axis="Y", base=False), (rx - 0.02, 0, 0.96)), M["rubber"]))
    for z in (0.32, 0.62):
        P.append(part(X(geo.cylinder(0.009, 0.34, 12, axis="Y", base=False), (rx, 0, z)), M["galv"]))
    ax, az = rx - 0.03, 0.09
    P.append(part(X(geo.cylinder(0.009, 0.50, 12, axis="Y", base=False), (ax, 0, az)), M["galv"]))
    for sy in (-1, 1):
        br = X(geo.box((0.05, 0.006, 0.09), bevel=0.0015, base=False), (rx - 0.015, sy * 0.17, 0.08))
        P.append(part(br, M["galv"]))
        tyre = geo.revolve(geo.fillet([(0.05, -0.022), (0.08, -0.024), (0.09, -0.012), (0.09, 0.012), (0.08, 0.024),
                                       (0.05, 0.022)], 0.006, 2), 40, closed=True, name="tyre")
        X(tyre, (0, 0, 0), (90, 0, 0))
        P.append(part(X(tyre, (ax, sy * 0.215, az)), M["rubber"]))
        hub = geo.cylinder(0.05, 0.036, 24, bevel=0.004, axis="Y", base=False)
        P.append(part(X(hub, (ax, sy * 0.215, az)), M["galv"]))
    return finish_hero(ctx, P, "SM_Gameplay_MasterCase", 2048)


def build_case_lid(ctx, M, D):
    """Lid in its own frame: hinge line along X through the origin, closed it runs to y = -0.32 and up to 0.12."""
    P = []
    x0, x1, y0, y1 = -CW / 2, CW / 2, -CD, 0.0
    P.append(part(X(geo.box((CW - 0.004, CD - 0.004, 0.095), bevel=0.004), (0, -CD / 2, 0.025)), M["laminate"]))
    P += _edges(M, x0, x1, y0, y1, 0.0, 0.12)
    o = 0.006
    P += _balls(M, [(x, y, 0.12 - o) for x in (x0 + o, x1 - o) for y in (y0 + o, y1 - o)])
    P.append(part(X(geo.box((CW - 0.034, CD - 0.034, 0.02), bevel=0.003), (0, -CD / 2, 0.012)), M["foam"]))
    # outside: IPX lozenge 0.30 x 0.125 on top, reading from the front when closed
    top = decal("lozenge_top", decal_mat("lozenge_lid", D["lozenge_lid"], 0.4), 0.30, 0.125, shape="pill")
    P.append(X(top, (0, -CD / 2, 0.1206)))
    # inside (faces -Z): lozenge 0.26 x 0.108 and the dark track 0.36 x 0.045 for the progress bar
    ins = decal("lozenge_in", decal_mat("lozenge_foam", D["lozenge_foam"], 0.7), 0.26, 0.108, shape="pill")
    X(ins, (0, 0, 0), (180, 0, 0))
    # (gaps pass) the lozenge and the track sit toward the free edge of the lid: open, that edge is the top, above
    # the reel and its tape box, so the track and its progress bar read from the front
    P.append(X(ins, (0, LOZ_Y, 0.0114)))
    trk = X(geo.box((0.36, 0.045, 0.004), bevel=0.0012, base=False), (0, TRACK_Y, 0.0105))
    P.append(part(trk, M["darkplastic"]))
    P.append(part(X(geo.box((0.372, 0.057, 0.002), bevel=0.0006, base=False), (0, TRACK_Y, 0.0118)), M["alu"]))
    # hinge knuckles along the back edge
    for hx in (-0.13, 0.13):
        P.append(part(X(geo.cylinder(0.006, 0.07, 12, axis="X", base=False), (hx, 0.003, 0.0)), M["chrome"]))
    return finish_hero(ctx, P, "SM_Gameplay_MasterCase_Lid", 1024, wear_kw=dict(splash=0.0))


def build_reel(ctx, M, D, n):
    """Reel and its tape box, in the assembly frame. 2-inch tape: flanges 0.27 across, 0.057 overall."""
    P = []
    half = 0.0285
    for sz in (-1, 1):
        fl = geo.cylinder(0.135, 0.0025, 72, bevel=0.0008)
        X(fl, (0, 0, sz * (half - 0.00125) - 0.00125))
        cut = []
        for c in (30, 150, 270):
            pts = [(0.062 * math.cos(math.radians(a)), 0.062 * math.sin(math.radians(a))) for a in np.linspace(c - 26, c + 26, 9)]
            pts += [(0.112 * math.cos(math.radians(a)), 0.112 * math.sin(math.radians(a))) for a in np.linspace(c + 30, c - 30, 13)]
            cut.append(prism(pts[::-1], -0.03, 0.03))
        cutter = geo.join(cut, "cut")
        X(cutter, (0, 0, sz * (half - 0.00125)))
        geo.boolean(fl, cutter, "DIFFERENCE", "EXACT")
        P.append(part(fl, M["gold"]))
    P.append(part(X(geo.tube(0.118, 0.058, 2 * half - 0.005, 96), (0, 0, -half + 0.0025)), M["tape"]))
    P.append(part(X(geo.tube(0.058, 0.0381, 2 * half, 48, bevel=0.001), (0, 0, -half)), M["darkplastic"]))
    hub = decal("hub_label", decal_mat("reel_hub_%d" % n, D["reel_hub_%d" % n], 0.5), 0.07, 0.023)
    P.append(X(hub, (0, 0.088, half + 0.0002)))
    reel = geo.join(P, "reel")
    X(reel, (0, 0, 0), (REEL_TILT, 0, 0))
    X(reel, REEL_C)
    # tape box behind it, its label facing front-up
    B = []
    B.append(part(geo.box((0.29, 0.29, 0.07), bevel=0.003, base=False), M["card"]))
    B.append(part(X(geo.box((0.296, 0.296, 0.022), bevel=0.003, base=False), (0, 0, 0.025)), M["card"]))   # lid rim
    lab = decal("box_label", decal_mat("reel_label_%d" % n, D["reel_label_%d" % n], 0.6), 0.26, 0.26)
    B.append(X(lab, (0, 0, 0.0362)))
    sp = decal("box_spine", decal_mat("reel_spine_%d" % n, D["reel_spine_%d" % n], 0.6), 0.27, 0.062)
    X(sp, (0, 0, 0), (-90, 0, 0))
    B.append(X(sp, (0, 0.1482, 0.0)))
    box = geo.join(B, "box")
    X(box, (0, 0, 0), (REEL_TILT, 0, 0))
    X(box, BOX_C)
    return finish_hero(ctx, [reel, box], "SM_Gameplay_MasterReel_%d" % n, 1024, wear_kw=dict(splash=0.0, leak=0.0, cavity=0.3, edge=0.15),
                       densify=0.02)


def build_beacon(ctx, M):
    P = []
    bx = CX - CW / 2 - 0.026 + 0.004                      # beside the handle bar (anchor beacon x -0.422)
    P.append(part(X(geo.cylinder(0.008, 0.32, 16), (bx + 0.0, 0, 0.90)), M["darkplastic"]))
    P.append(part(X(geo.box((0.03, 0.05, 0.05), bevel=0.004, base=False), (bx - 0.012, 0, 0.96)), M["darkplastic"]))
    P.append(part(X(geo.cylinder(0.055, 0.012, 40, bevel=0.003), (bx, 0, 1.22)), M["darkplastic"]))
    P.append(part(X(geo.tube(0.054, 0.046, 0.016, 40, bevel=0.002), (bx, 0, 1.228)), M["chrome"]))
    lens = geo.revolve(geo.fillet([(0.0, 1.232), (0.052, 1.232), (0.052, 1.27), (0.045, 1.31), (0.028, 1.338), (0.0, 1.346)],
                                  0.004, 2), 48, name="lens")
    P.append(part(X(lens, (bx, 0, 0)), M["lens"]))
    return finish_hero(ctx, P, "SM_Gameplay_MasterCase_Beacon", 512, wear_kw=dict(splash=0.0), densify=0.02)


# --------------------------------------------------------------------------------------------- propane tank

def build_propane(ctx, M, D):
    P = []
    f = geo.fillet
    body = geo.revolve(f([(0.0, 0.034), (0.10, 0.04), (0.142, 0.056), (0.152, 0.08), (0.152, 0.36), (0.146, 0.40),
                          (0.124, 0.438), (0.085, 0.462), (0.03, 0.472), (0.0, 0.473)], 0.01, 3), 72, name="body")
    part(body, M["white_paint"])
    geo.assign(body, M["red_paint"], lambda x, y, z: z > 0.33)
    P.append(body)
    P.append(part(X(geo.torus(0.1525, 0.0028, 72, 8), (0, 0, 0.33)), M["white_paint"]))           # girth weld
    P.append(part(geo.tube(0.125, 0.114, 0.045, 64, bevel=0.002), M["darksteel"]))                    # foot ring
    P.append(part(X(geo.tube(0.118, 0.10, 0.006, 64, bevel=0.001), (0, 0, 0.038)), M["darksteel"]))
    for c in (90, 270):                                                                               # collar arcs
        arc = geo.revolve(f([(0.095, 0.44), (0.101, 0.44), (0.101, 0.578), (0.098, 0.585), (0.095, 0.578)], 0.002, 1, closed=True),
                          40, closed=True, angle=110, name="arc")
        X(arc, (0, 0, 0), (0, 0, c - 55))
        P.append(part(arc, M["white_paint"]))
    # valve: brass body, POL outlet to the front (-Y), relief stub, red handwheel
    P.append(part(X(geo.cylinder(0.015, 0.06, 6, bevel=0.002), (0, 0, 0.468)), M["brass"]))
    P.append(part(X(geo.cylinder(0.019, 0.012, 24, bevel=0.002), (0, 0, 0.466)), M["brass"]))
    out = geo.cylinder(0.009, 0.045, 16, bevel=0.0015, axis="Y", base=False)
    P.append(part(X(out, (0, -0.03, 0.508)), M["brass"]))
    P.append(part(X(geo.cylinder(0.011, 0.012, 6, axis="Y", base=False), (0, -0.05, 0.508)), M["brass"]))
    P.append(part(X(geo.cylinder(0.007, 0.03, 12, axis="X", base=False), (0.022, 0, 0.50)), M["brass"]))
    P.append(part(X(geo.cylinder(0.005, 0.03, 10), (0, 0, 0.528)), M["brass"]))
    wheel = [X(geo.torus(0.029, 0.0045, 40, 8), (0, 0, 0.553))]
    for a in (0, 120, 240):
        sp = X(geo.box((0.03, 0.006, 0.005), bevel=0.001, base=False), (0.015, 0, 0))
        wheel.append(X(sp, (0, 0, 0.553), (0, 0, a)))
    wheel.append(X(geo.cylinder(0.009, 0.012, 16, bevel=0.002), (0, 0, 0.547)))
    for w in wheel:
        P.append(part(w, M["red_paint"]))
    # flammable-gas diamonds front and back at 0.215
    for phi in (0, 180):
        dm = decal("hazard", decal_mat("hazard", D["hazard"], 0.45), 0.184, 0.184, shape="diamond", n=(8, 8))
        X(dm, (0, 0, 0.0003))
        P.append(wrap_cyl(dm, 0.152, phi, 0.215))
    return finish_hero(ctx, P, "SM_Gameplay_PropaneTank", 2048, densify=0.02,
                       wear_kw=dict(leak_sources=[(0.0, -0.05, 0.508), (0.1, 0.0, 0.44), (-0.1, 0.0, 0.44)]))


# --------------------------------------------------------------------------------------------- welding rack

def _cylinder_shell(r, z0, z1, neck=0.035):
    f = geo.fillet
    return geo.revolve(f([(0.0, z0 + 0.004), (r * 0.8, z0 + 0.008), (r, z0 + 0.035), (r, z1 - r * 1.25), (r * 0.93, z1 - r * 0.8),
                          (r * 0.7, z1 - r * 0.35), (neck * 1.25, z1 - 0.02), (neck, z1 - 0.012), (neck, z1), (0.0, z1)],
                         0.012, 3), 64, name="cyl")


def _regulator(M, D, x, y, z, flip=1):
    """Brass two-gauge regulator on a cylinder valve outlet at (x, y, z); gauges face the front (-Y)."""
    P = []
    P.append(part(X(geo.cylinder(0.026, 0.06, 24, bevel=0.003, axis="Y", base=False), (x, y - 0.035, z)), M["brass"]))
    P.append(part(X(geo.cylinder(0.008, 0.035, 12, axis="Y", base=False), (x, y - 0.075, z)), M["brass"]))
    P.append(part(X(geo.cylinder(0.006, 0.05, 12, axis="Y", base=False), (x, y - 0.1, z)), M["chrome"]))     # T screw
    P.append(part(X(geo.cylinder(0.004, 0.06, 10, axis="X", base=False), (x, y - 0.122, z)), M["chrome"]))
    for sx in (-1, 1):
        gx = x + sx * 0.052
        P.append(part(X(geo.cylinder(0.006, 0.04, 10, axis="X", base=False), (x + sx * 0.03, y - 0.035, z + 0.012)), M["brass"]))
        bez = geo.cylinder(0.031, 0.022, 32, bevel=0.003, axis="Y", base=False)
        P.append(part(X(bez, (gx, y - 0.04, z + 0.02)), M["chrome"]))
        face = decal("gauge", decal_mat("gauge", D["gauge"], 0.15), 0.052, 0.052, shape="pill")
        X(face, (0, 0, 0), (90, 0, 0))
        P.append(X(face, (gx, y - 0.0512, z + 0.02)))
    P.append(part(X(geo.cylinder(0.006, 0.03, 10), (x, y - 0.035, z - 0.05)), M["brass"]))           # outlet
    return P


def build_welding_rack(ctx, M, D):
    P = []
    P.append(part(geo.box((0.90, 0.50, 0.04), bevel=0.004), M["darksteel"]))
    yb = 0.22
    for sx in (-1, 1):
        P.append(part(X(geo.box((0.04, 0.04, 1.30), bevel=0.003), (sx * 0.43, yb, 0.04)), M["darksteel"]))
        P.append(part(X(geo.box((0.046, 0.046, 0.006), bevel=0.002), (sx * 0.43, yb, 1.34)), M["darksteel"]))
        gus = geo.plate(outline=[(0, 0), (0.16, 0), (0, 0.16)], thickness=0.006)
        X(gus, (0, 0, 0), (90, 0, 90))
        P.append(part(X(gus, (sx * 0.43 - 0.003, yb - 0.02, 0.04), (0, 0, 180)), M["darksteel"]))
    for z in (0.30, 0.82, 1.30):
        P.append(part(X(geo.box((0.82, 0.03, 0.03), bevel=0.002, base=False), (0, yb, z)), M["darksteel"]))
    # cylinders: oxygen x -0.28 (capped spare) and 0 (regulated), acetylene x +0.28 (regulated)
    yc = 0.045
    for x, r, top, key in ((-0.28, 0.115, 1.40, "o2"), (0.0, 0.115, 1.40, "o2"), (0.28, 0.14, 1.10, "acet")):
        c = _cylinder_shell(r, 0.04, top)
        P.append(part(X(c, (x, yc, 0)), M[key]))
        P.append(part(X(geo.torus(0.04, 0.006, 32, 8), (x, yc, top - 0.004)), M["darksteel"]))       # neck ring
        P.append(part(X(geo.cylinder(0.02, 0.06, 6, bevel=0.002), (x, yc, top)), M["brass"]))          # valve
        P.append(part(X(geo.cylinder(0.01, 0.03, 12, axis="Y", base=False), (x, yc - 0.025, top + 0.035)), M["brass"]))
        P.append(part(X(geo.cylinder(0.018, 0.01, 16, bevel=0.002), (x, yc, top + 0.06)), M["darksteel"]))   # spindle knob
        word = "OXYGEN" if key == "o2" else "ACETYLENE"
        t = geo.text(word, 0.042, 0.0004, 0.0, name="stencil")
        X(t, (0, 0, 0.0002))
        P.append(part(wrap_cyl(t, r, 0, top - 0.48 if key == "o2" else top - 0.40), M["stencil"]))
    cap = geo.revolve(geo.fillet([(0.0, 1.37), (0.052, 1.37), (0.052, 1.47), (0.04, 1.51), (0.0, 1.52)], 0.006, 2), 40, name="cap")
    P.append(part(X(cap, (-0.28, yc, 0)), M["darksteel"]))
    P += _regulator(M, D, 0.0, yc, 1.475)
    P += _regulator(M, D, 0.28, yc, 1.195)
    # chains across the front at 0.82 and 0.45
    for z in (0.82, 0.45):
        pts = [(-0.43, yb - 0.02, z), (-0.41, -0.06, z), (-0.30, -0.085, z), (-0.14, -0.06, z), (0.0, -0.085, z),
               (0.16, -0.10, z), (0.30, -0.112, z), (0.41, -0.05, z), (0.43, yb - 0.02, z)]
        P.append(part(geo.chain(pts, link_len=0.032, wire=0.0045), M["galv"]))
    # placard on a white board hung from the top chain
    P.append(part(X(geo.box((0.38, 0.006, 0.27), bevel=0.002, base=False), (-0.14, -0.105, 0.655)), M["board"]))
    pl = decal("placard", decal_mat("placard", D["placard"], 0.5), 0.36, 0.25)
    X(pl, (0, 0, 0), (90, 0, 0))
    P.append(X(pl, (-0.14, -0.1082, 0.655)))
    for hx in (-0.29, 0.01):
        P.append(part(X(geo.torus(0.012, 0.0022, 16, 6), (0, 0, 0), (0, 90, 0)), M["galv"]))
        P[-1] = part(X(P[-1], (hx, -0.10, 0.80)), M["galv"])
    # twin hose, green (oxygen) and red (fuel), from the regulators over the top rail in two loops to the torch
    for dx, key, sx in ((0.0, "hose_green", 0.0), (0.016, "hose_red", 0.28)):
        start = (sx, yc - 0.035, (1.425 if sx == 0 else 1.145))
        pts = [start, (sx + dx, yc - 0.03, start[2] - 0.06), (0.12 + dx, 0.12, 1.36), (0.10 + dx, yb, 1.345),
               (0.08 + dx, yb + 0.06, 1.25), (0.05 + dx, yb + 0.08, 0.95), (-0.05 + dx, yb + 0.075, 0.90),
               (-0.12 + dx, yb + 0.06, 1.0), (-0.16 + dx, yb + 0.03, 1.33), (-0.18 + dx, yb - 0.02, 1.35),
               (-0.22 + dx, yb - 0.06, 1.30), (-0.25 + dx, yb + 0.07, 1.05), (-0.32 + dx, yb + 0.075, 0.98),
               (-0.40 + dx, yb + 0.045, 1.05), (-0.43 + dx * 0.3, yb - 0.035, 1.02)]
        P.append(part(geo.pipe(pts, radius=0.0062, segments=10, bend_radius=0.035, bend_segments=5), M[key]))
    # brass torch hung on a hook on the left post
    P.append(part(X(geo.cylinder(0.004, 0.05, 8, axis="Y", base=False), (-0.43, yb - 0.045, 1.13)), M["darksteel"]))
    T = []
    T.append(X(geo.cylinder(0.012, 0.20, 20, bevel=0.002), (0, 0, 0)))
    T.append(X(geo.cylinder(0.016, 0.03, 20, bevel=0.003), (0, 0, 0.20)))
    for kz in (0.205, 0.22):
        T.append(X(geo.cylinder(0.009, 0.035, 12, axis="X", base=False), (0.018, 0, kz)))
    T.append(geo.pipe([(0, 0, 0.23), (0, 0, 0.40), (0, -0.05, 0.47)], radius=0.0055, segments=10, bend_radius=0.04))
    T.append(X(geo.cylinder(0.006, 0.025, 10, axis="Y", base=False), (0, -0.06, 0.475)))
    torch = geo.join(T, "torch")
    X(torch, (0, 0, 0), (180, 0, 0))
    P.append(part(X(torch, (-0.43, yb - 0.075, 1.12)), M["brass"]))
    return finish_hero(ctx, P, "SM_Gameplay_WeldingRack", 2048, densify=0.03)


def build_gameplay(ctx):
    M = materials()
    D = make_decals()
    out = []

    def want(*names):
        o = ctx.args.only
        return not o or "gameplay" in o or any(n in o for n in names) or any(k.startswith("props_") for k in o)

    if want("SM_Gameplay_MasterCase"):
        ob = build_case_body(ctx, M, D)
        ctx.asset(ob, collision="box", cover_height=0.66, expect_size=(None, None, 0.97), notes=(
            "Master reel case (objective, 05b 2.5.1): black laminate flight case 0.42 x 0.32 x 0.50 with aluminium "
            "edging, chrome ball corners, two butterfly latches (front, -Y), recessed handle (+X), IPX luggage tag and "
            "clipped tracker (emissive LCD and LED, whip antenna), on a steel hand truck loaded from -X (toe plate, "
            "rails bent into a handle at 0.96, two 0.18 m wheels). Colliders (05b App. B): case and truck x -0.45..0.03, "
            "y +-0.30, 0..0.66; the boombox (SM_Prop_Boombox) stands at (0.24, 0.04, 0) yawed 66 deg. Separate meshes "
            "in the same frame: SM_Gameplay_MasterReel_1/2/3, SM_Gameplay_MasterCase_Beacon; the lid "
            "SM_Gameplay_MasterCase_Lid hinges at (-0.19, 0.16, 0.53), open = -95 deg about X."),
            pivot="assembly origin: centre of the 0.9 x 0.6 footprint on the ground")
        out.append(ob)
        lid = build_case_lid(ctx, M, D)
        lid.location = HINGE
        lid.rotation_euler = (math.radians(LID_OPEN), 0, 0)
        lid["mi_placed"] = True
        ctx.asset(lid, collision="none", cover_height=None, expect_size=(0.42, 0.32, 0.12), notes=(
            "Lid of the master case, built closed with its pivot on the hinge line (back lower edge, along X). "
            "Outside: IPX lozenge 0.30 x 0.125. Inside: foam, a second lozenge and the dark track 0.36 x 0.045 that "
            "holds the progress bar (SM_Gameplay_MasterCase_Progress at lid-local (-0.17, -0.268, 0.0077)), placed toward the "
            "free edge so it shows above the reel when open. Open: -95 deg about X at (-0.19, 0.16, 0.53)."),
            pivot="hinge line: x centre, back lower edge")
        out.append(lid)
        bc = build_beacon(ctx, M)
        ctx.asset(bc, collision="none", cover_height=None, notes=(
            "Beacon of the master case: dark mast clamped to the hand-truck handle (0.90 to 1.22), base disc and a domed "
            "gold emissive lens 0.104 across (top 1.346). Hidden with the reel. Light shaft and ground glow are engine effects."),
            pivot="assembly origin (place at identity under the case)")
        out.append(bc)
    for n in (1, 2, 3):
        if want("SM_Gameplay_MasterReel_%d" % n):
            r = build_reel(ctx, M, D, n)
            ctx.asset(r, collision="none", cover_height=None, notes=(
                "Master reel %d of 3: gold two-inch 24-track reel (0.27 across, 0.057 thick: real 2-inch tape, see the "
                "spec's open question on 0.038) with three spoke windows, brown tape pack, dark hub and a REEL %d / 3 "
                "sticker, tilted 40 deg back on its cardboard tape box (0.29 x 0.29 x 0.07) whose label reads MASTER REEL, "
                "MURDER INC., REEL %d / 3, SPEED 30 IPS, TAPE 2 IN · 24 TRK. Reel centre at (-0.19, -0.045, 0.63) "
                "(05b anchor reel (-0.19, 0, 0.63))." % (n, n, n)),
                pivot="assembly origin (place at identity under the case)")
            if n > 1:
                r.location = (0.0, -1.2 * (n - 1) + 0.6, 0.0)
                r["mi_placed"] = True
            out.append(r)
    if want("SM_Gameplay_PropaneTank"):
        ob = build_propane(ctx, M, D)
        ctx.asset(ob, collision="box", cover_height=0.60, expect_size=(0.30, None, 0.59), notes=(
            "Propane tank (explosive, 05b 2.5.2): dark foot ring, white body r 0.152 to 0.33, red domed shoulder, white "
            "two-arc guard collar to 0.585 open at the sides, brass valve with the outlet toward -Y (jet anchor "
            "(0, -0.07, 0.52) direction (0, -0.81, 0.58)), red handwheel, class-2 flammable-gas diamonds front and back "
            "at 0.215. Effective collider: axis-aligned 0.32 x 0.32 x 0.60 around the rotated footprint. The heat glow "
            "of the lit state (#b8400f x 0.6) is a material parameter in engine."),
            pivot="centre of the footprint on the ground")
        out.append(ob)
    if want("SM_Gameplay_WeldingRack"):
        ob = build_welding_rack(ctx, M, D)
        ctx.asset(ob, collision="box", cover_height=1.60, expect_size=(0.91, None, 1.52), notes=(
            "Welding rack (explosive, 05b 2.5.2): steel base plate 0.90 x 0.50 x 0.04, back frame of two posts to "
            "1.34 with three rails and gussets, two chains across the front (0.82, 0.45), two dark green oxygen "
            "cylinders (x -0.28 capped, x 0 regulated) and a maroon acetylene cylinder (x +0.28) with stencilled names, "
            "brass valves, two brass regulators with two gauges each, green and red twin hose looped over the top rail "
            "to a brass torch hung on the left post, DANGER / FLAMMABLE GAS / NO SMOKING / NO OPEN FLAME placard on a "
            "white board. The catalogue's rack has no wheels. Jet anchor: acetylene regulator (0.28, -0.03, 1.2). "
            "Effective collider 0.90 x 0.50 x 1.60."),
            pivot="centre of the footprint on the ground")
        out.append(ob)
    out += build_gaps_pass(ctx, M, D)
    return out


# ------------------------------------------------------------------------------------- gaps pass (assets/gaps.py)
# Added by the catalogue-gaps run: wrecks of the two explosives, the progress strip of the case lid, the boombox
# level meter, and the heat-glow masks of the lit state. --only names: SM_Gameplay_PropaneTank_Wreck,
# SM_Gameplay_WeldingRack_Wreck, SM_Gameplay_MasterCase_Progress, SM_Prop_Boombox_Meter, heat.

def _lamp(name, col):
    m = bpy.data.materials.get(name) or mat.flat(name, col, 0.2, 0.0)
    b = mat.principled(m)
    b.inputs["Emission Color"].default_value = (*col, 1.0)
    b.inputs["Emission Strength"].default_value = 4.0
    return m


def _flat_asset(ctx, parts, name):
    ob = geo.join(parts, name, ctx.col)
    _degenerate(ob)
    geo.uv_world_box(ob, 0.25)
    geo.ensure_wear(ob)
    return ob


def build_progress(ctx):
    """The gold strip 0.34 x 0.03 that fills the lid's track: pivot at its LEFT end (viewer's left with the lid open),
    so a scale along X from 0 to 1 grows it from that end."""
    s = part(X(geo.box((0.34, 0.03, 0.0015), bevel=0.0005, base=False), (0.17, 0.0, 0.0)), _lamp("MI_Lamp_Gold", lin("#f6c21a")))
    return _flat_asset(ctx, [s], "SM_Gameplay_MasterCase_Progress")


def boombox_face_y(x, z):
    """Front face of the scanned boombox at (x, z), from its exported GLB (ray cast toward +Y)."""
    from mathutils import Vector
    p = os.path.join(paths.glb, "SM_Prop_Boombox.glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=p)
    new = [o for o in bpy.data.objects if o not in before]
    ob = next(o for o in new if o.type == "MESH")
    bpy.context.view_layer.update()
    mw = ob.matrix_world
    inv = mw.inverted()
    best = None
    for dx in (-0.004, 0.0, 0.004):
        for dz in (-0.004, 0.0, 0.004):
            o = inv @ Vector((x + dx, -1.0, z + dz))
            d = (inv.to_3x3() @ Vector((0, 1, 0))).normalized()
            hit, loc, _n, _i = ob.ray_cast(o, d)
            if hit:
                y = (mw @ loc).y
                best = y if best is None else min(best, y)
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    return best if best is not None else -0.085


METER_X, METER_Z = -0.105, 0.201


def build_meter(ctx, M):
    """Five-segment level meter over the scan's printed meter area, in SM_Prop_Boombox's frame: three green and two
    orange-red segments, each its own lens (MI_Lamp_MeterGreen / _MeterRed); the engine lights 0..5 of them."""
    y = boombox_face_y(METER_X, METER_Z)
    ctx.log("boombox face at y %.4f" % y)
    P = [part(X(geo.box((0.084, 0.004, 0.017), bevel=0.0012, base=False), (METER_X, y - 0.0015, METER_Z)), mat.flat("MI_Plastic_Black", (0.012, 0.012, 0.013), 0.4))]
    green, red = _lamp("MI_Lamp_MeterGreen", lin("#3dff7a")), _lamp("MI_Lamp_MeterRed", lin("#ff5a2a"))
    for k in range(5):
        x = METER_X - 0.032 + 0.016 * k
        P.append(part(X(geo.box((0.012, 0.002, 0.009), bevel=0.0006, base=False), (x, y - 0.0040, METER_Z)), green if k < 3 else red))
    return _flat_asset(ctx, P, "SM_Prop_Boombox_Meter")


def _jag(ob, amount, freq, seed, axis_fn):
    """Tear an edge: move vertices near the boundary chosen by axis_fn(co) -> weight by noise."""
    co, _ = geo.arrays(ob)
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.3, 3)
    n = np.sin(co[:, 0] * freq + ph[0]) * np.sin(co[:, 1] * freq * 1.3 + ph[1]) + 0.5 * np.sin(co[:, 2] * freq * 2.1 + ph[2])
    w = axis_fn(co)
    co[:, 2] -= amount * w * (0.5 + 0.5 * n)
    geo.set_verts(ob, co)


def wreck_materials():
    return dict(
        soot=pm("Soot", "painted_steel", Paint_Color=lin("#0c0b0a"), Paint_Roughness=0.92, Chipping=0.55, Rust=0.4, Chalking=0.7,
                Old_Coat=(0.05, 0.045, 0.07), Primer_Color=(0.12, 0.06, 0.035)),
        blued=pm("HeatBlue", "painted_steel", Paint_Color=(0.055, 0.05, 0.095), Paint_Metallic=1.0, Paint_Roughness=0.42,
                 Chipping=0.45, Rust=0.35, Chalking=0.15, Old_Coat=(0.16, 0.08, 0.035), Primer_Color=(0.03, 0.03, 0.03)),
        scorched=pm("ScorchedPaint", "painted_steel", Paint_Color=lin("#6a6660"), Paint_Roughness=0.8, Chipping=0.7, Rust=0.5,
                    Chalking=0.8, Old_Coat=(0.02, 0.02, 0.02), Primer_Color=(0.10, 0.05, 0.03)),
    )


def build_propane_wreck(ctx, M):
    W = wreck_materials()
    P = []
    ring = geo.tube(0.125, 0.114, 0.045, 64, bevel=0.002)
    geo.densify(ring, 0.01, 3)
    geo.displace(ring, 0.004, 25.0, 11)
    part(ring, W["soot"])
    geo.assign(ring, W["blued"], lambda x, y, z: (z > 0.03) & (x > -0.02))
    X(ring, (0, 0, 0), (5, -3, 0))
    P.append(X(ring, (-0.01, 0.0, 0.004)))
    # torn-open floor of the shell inside the ring: the bottom dome with petals curled out
    dome = geo.revolve(geo.fillet([(0.0, 0.034), (0.10, 0.04), (0.142, 0.056), (0.150, 0.075), (0.146, 0.088)], 0.008, 2), 64, name="dome")
    geo.densify(dome, 0.012, 3)
    co, _ = geo.arrays(dome)
    a = np.arctan2(co[:, 1], co[:, 0])
    r = np.hypot(co[:, 0], co[:, 1])
    tear = (0.5 + 0.5 * np.sin(a * 5 + 1.3)) * np.clip((r - 0.11) / 0.04, 0, 1)
    co[:, 2] -= 0.03 * tear
    co[:, 0] *= 1 + 0.25 * tear * np.clip((co[:, 2] - 0.05) / 0.03, 0, 1)
    co[:, 1] *= 1 + 0.25 * tear * np.clip((co[:, 2] - 0.05) / 0.03, 0, 1)
    geo.set_verts(dome, co)
    geo.displace(dome, 0.003, 30.0, 12)
    part(dome, W["blued"])
    geo.assign(dome, W["soot"], lambda x, y, z: z < 0.05)
    P.append(X(dome, (-0.01, 0.0, -0.03), (5, -3, 0)))
    # the torn plate shard 0.16 x 0.11 lying beside it, painted face up, scorched
    sh = geo.plate(outline=[(-0.08, -0.05), (-0.02, -0.058), (0.05, -0.052), (0.08, -0.02), (0.07, 0.03), (0.03, 0.055),
                            (-0.03, 0.05), (-0.07, 0.035), (-0.085, -0.01)], thickness=0.0025)
    geo.densify(sh, 0.01, 3)
    co, _ = geo.arrays(sh)
    co[:, 2] += 0.152 - np.sqrt(np.maximum(0.152 ** 2 - co[:, 0] ** 2, 0))                     # cylinder curvature
    geo.set_verts(sh, co)
    part(sh, W["scorched"])
    geo.assign(sh, W["soot"], lambda x, y, z: z < 0.0012)
    P.append(X(sh, (0.07, 0.07, 0.008), (8, -6, 35)))
    for k, (x, y, sz) in enumerate(((-0.12, -0.10, 0.02), (0.10, -0.09, 0.015), (-0.08, 0.12, 0.018))):
        f = geo.box((sz * 1.6, sz, 0.002), bevel=0.0005)
        P.append(part(X(f, (x, y, 0.0), (rng_ := k * 13 % 7, 0, k * 47)), W["soot"]))
    ob = finish_hero(ctx, P, "SM_Gameplay_PropaneTank_Wreck", 1024, densify=0.015,
                     wear_kw=dict(leak=0.0, splash=1.0, cavity=1.0, edge=0.6))
    return ob


def build_rack_wreck(ctx, M):
    W = wreck_materials()
    P = []
    pl = geo.box((0.86, 0.46, 0.035), bevel=0.003)
    geo.densify(pl, 0.03, 4)
    co, _ = geo.arrays(pl)
    co[:, 2] += 0.035 * np.sin(np.pi * (co[:, 0] / 0.86 + 0.5)) * (0.4 + co[:, 1] / 0.46) + 0.02 * (co[:, 0] > 0.3) * ((co[:, 0] - 0.3) / 0.13) ** 2
    geo.set_verts(pl, co)
    geo.displace(pl, 0.003, 12.0, 21)
    part(pl, W["soot"])
    geo.assign(pl, W["blued"], lambda x, y, z: (np.sin(x * 9.0 + 1.0) + np.cos(y * 11.0) + 0.6 * np.sin(x * 23 + y * 17)) > 0.9)
    P.append(pl)
    for sx in (-1, 1):                                                       # two bent posts leaning out
        path = [(sx * 0.41, 0.20, 0.03), (sx * 0.42, 0.21, 0.18), (sx * 0.47, 0.24, 0.31), (sx * 0.55, 0.28, 0.40), (sx * 0.57, 0.29, 0.43)]
        post = geo.pipe(path, radius=0.02, segments=4, bend_radius=0.08, bend_segments=6)
        part(post, W["soot"])
        geo.assign(post, W["blued"], lambda x, y, z: z > 0.3)
        P.append(post)
        stub = geo.box((0.04, 0.04, 0.06), bevel=0.003)
        P.append(part(X(stub, (sx * 0.41, 0.20, 0.03)), W["soot"]))
    for k, (x, y, rz, ang, h) in enumerate(((-0.22, -0.22, 20, 80, 0.30), (0.22, -0.24, -35, 110, 0.36), (0.36, 0.05, 70, 60, 0.24),
                                             (-0.40, 0.10, 120, 90, 0.20))):
        r = 0.115 if k != 1 else 0.14                                            # burst cylinder shells lying on the ground
        sh = geo.revolve([(r, 0.0), (r, h)], 24, angle=ang, name="shell")
        geo.densify(sh, 0.02, 3)
        co, _ = geo.arrays(sh)
        co[:, 0] += 0.02 * np.sin(co[:, 2] * 25 + k)
        geo.set_verts(sh, co)
        _jag(sh, 0.0, 1.0, k, lambda c: 0 * c[:, 0])
        sol = geo.revolve([(r - 0.004, 0.0), (r, 0.0), (r, h), (r - 0.004, h)], 24, closed=True, angle=ang, name="shellT")
        bpy.data.objects.remove(sh, do_unlink=True)
        part(sol, W["blued"] if k % 2 == 0 else W["soot"])
        X(sol, (-h / 2, 0, 0), (0, 90, 0))
        X(sol, (0, 0, 0), (rz * 0.5, 0, 0))
        co_, _ = geo.arrays(sol)
        X(sol, (0, 0, -float(co_[:, 2].min()) - 0.004))
        P.append(X(sol, (x, y, 0.0), (0, 0, rz)))
    brass = pm("BrassScorch", "painted_steel", Paint_Color=lin("#7a5a2a"), Paint_Metallic=1.0, Paint_Roughness=0.55, Chipping=0.5,
               Rust=0.3, Chalking=0.4, Old_Coat=(0.03, 0.03, 0.03), Primer_Color=(0.05, 0.04, 0.03))
    P.append(part(X(geo.cylinder(0.02, 0.06, 6, bevel=0.002, axis="X", base=False), (0.15, 0.22, 0.02), (0, 0, 30)), brass))
    P.append(part(X(geo.cylinder(0.026, 0.05, 20, bevel=0.003, axis="Y", base=False), (-0.18, -0.27, 0.026)), brass))
    P.append(part(geo.chain([(-0.40, -0.05, 0.04), (-0.2, -0.12, 0.006), (0.05, -0.16, 0.006), (0.3, -0.12, 0.04)], link_len=0.032,
                            wire=0.0045), W["soot"]))
    return finish_hero(ctx, P, "SM_Gameplay_WeldingRack_Wreck", 2048, densify=0.03,
                       wear_kw=dict(leak=0.0, splash=1.0, cavity=1.0, edge=0.6))


def heat_masks(ctx, M, D):
    """Heat-glow masks of the lit state through the unique UVs of the two explosives: T_<Set>_Heat.png (linear 0..1,
    multiply by #b8400f x 0.6 x the burn parameter in engine) - hot where the flame licks: round the valve and the
    shoulder of the tank, the regulators, valves and the tops of the cylinders on the rack, broken by blotches."""
    from mi import texpaint as tp
    from PIL import Image
    for name, fn, hot in (("PropaneTank", build_propane, [((0.0, -0.05, 0.50), 0.09), ((0.0, 0.0, 0.46), 0.11)]),
                          ("WeldingRack", build_welding_rack, [((0.28, -0.03, 1.20), 0.16), ((0.0, -0.03, 1.47), 0.13), ((0.28, 0.045, 1.08), 0.15)])):
        ob = fn(ctx, M, D)
        G = tp.geometry_maps(ob, res=1024, samples=4)
        m = G["mask"]
        p = G["pos"][m]
        N = tp.Noise(7)
        h = np.zeros(len(p), np.float32)
        for c, r in hot:
            d = np.linalg.norm(p - np.asarray(c), axis=1)
            h = np.maximum(h, np.exp(-(d / r) ** 2))
        blot = 0.5 + 0.5 * N.fbm(p, 18.0, 4)
        h = np.clip(h * (0.45 + 1.0 * blot) - 0.25, 0, 1) ** 1.5 * (0.6 + 0.4 * G["ao"][m])
        img = tp.dilate(tp.scatter(m, h), m, 8)
        d = paths.texture_set("Gameplay_" + name)
        fn_ = "T_Gameplay_%s_Heat.png" % name
        Image.fromarray((np.clip(img[::-1], 0, 1) * 255).astype(np.uint8), "L").save(os.path.join(d, fn_))
        js = os.path.join(d, "set.json")
        import json
        with open(js) as f:
            info = json.load(f)
        info["files"]["Heat"] = fn_
        info.setdefault("convention", {})["Heat"] = "linear heat-glow mask of the lit state: emissive = Heat x #b8400f x 0.6 x burn"
        with open(js, "w") as f:
            json.dump(info, f, indent=1, sort_keys=True)
        ctx.log("heat mask %s: %s (mean %.3f)" % (name, fn_, float(h.mean())))
        bpy.data.objects.remove(ob, do_unlink=True)


def build_gaps_pass(ctx, M, D):
    o = ctx.args.only or []
    out = []
    if "SM_Gameplay_MasterCase_Progress" in o or not o:
        ob = build_progress(ctx)
        ctx.asset(ob, collision="none", expect_size=(0.34, 0.03, None), notes=(
            "Progress bar of the master case: gold emissive strip 0.34 x 0.03 (MI_Lamp_Gold, #f6c21a) under the lid's track. "
            "Pivot at its left end: attach to SM_Gameplay_MasterCase_Lid at lid-local (-0.17, -0.268, 0.0077) and scale X "
            "0..1 over the 2.4 s grab."), pivot="left end of the strip")
        out.append(ob)
    if "SM_Prop_Boombox_Meter" in o or not o:
        ob = build_meter(ctx, M)
        ctx.asset(ob, collision="none", notes=(
            "Five-segment level meter of SM_Prop_Boombox, in its frame (place at identity under the boombox): segments 1-3 "
            "MI_Lamp_MeterGreen #3dff7a, 4-5 MI_Lamp_MeterRed #ff5a2a, each a separate lens; light 0..5 of them to the music."),
            pivot="SM_Prop_Boombox frame")
        out.append(ob)
    if "SM_Gameplay_PropaneTank_Wreck" in o or not o:
        ob = build_propane_wreck(ctx, M)
        ctx.asset(ob, collision="none", notes=(
            "What is left after the propane tank blows (gone state): the scorched foot ring tilted, the torn-open floor of the "
            "shell with petals curled out, a torn plate shard 0.16 x 0.11 and small fragments; soot black and heat-blued "
            "steel. Nothing above 0.1 m; no collision."), pivot="centre of the tank's footprint")
        out.append(ob)
    if "SM_Gameplay_WeldingRack_Wreck" in o or not o:
        ob = build_rack_wreck(ctx, M)
        ctx.asset(ob, collision="none", expect_size=(1.18, None, None), notes=(
            "What is left after the welding rack blows (gone state): the scorched, buckled base plate 0.86 x 0.46, two bent "
            "frame posts leaning out of it, four burst cylinder shells, a brass valve and regulator body, the fallen chain. "
            "Soot black and heat-blued; no collision."), pivot="centre of the rack's footprint")
        out.append(ob)
    if "heat" in o:
        heat_masks(ctx, M, D)
    return out


# --------------------------------------------------------------------------------------------------------- build

def build(ctx):
    objs = build_scans(ctx)
    objs += build_gameplay(ctx)
    return objs


def on_export(ctx, objs):
    """Export every asset this run built (build() already applied --only, including the group names
    'scans' and 'gameplay')."""
    from mi import export
    for name, a in ctx.assets.items():
        export.export_asset(a["ob"], ctx.family, a["collision"], a["cover_height"], a["notes"], a["pivot"],
                            a["expect_size"], fbx=ctx.args.fbx, slots=a["slots"])


# ------------------------------------------------------------------------------------------------------ previews

SCAN_LAYOUT = {   # asset: (x, y, z, yaw deg); wall pieces hang on the preview wall (front face y = 3.0)
    "SM_Prop_StreetLamp_Wall": (-2.2, 3.0, 2.2, 0), "SM_Prop_SecurityCamera_A": (-0.6, 3.0, 2.4, 0),
    "SM_Prop_SecurityCamera_B": (0.2, 3.0, 2.4, 0),
    "SM_Prop_ShelfRack_Drawers": (-3.7, 2.45, 0, 0), "SM_Prop_ShelfRack_Single": (-1.6, 2.5, 0, 0),
    "SM_Prop_ShelfRack_Narrow": (-0.5, 2.5, 0, 0), "SM_Prop_StreetLamp_Post": (1.0, 2.3, 0, 0),
    "SM_Prop_UtilityBox_Small": (2.0, 2.5, 0, 0), "SM_Prop_UtilityBox_Large": (3.0, 2.5, 0, 0),
    "SM_Prop_JerseyBarrier_Scan": (-4.0, 1.0, 0, 0), "SM_Prop_JerseyBarrier_ScanTall": (-2.2, 1.0, 0, 0),
    "SM_Prop_FoodCart_Base": (-0.4, 1.1, 0, 0), "SM_Prop_Bench_Scan": (1.2, 1.1, 0, 0),
    "SM_Prop_ToolChest_Small": (2.5, 1.1, 0, 0), "SM_Prop_CrateWood_Long": (3.7, 1.1, 0, 0),
    "SM_Prop_Hydrant_Scan": (-4.4, -0.3, 0, 0), "SM_Prop_Hydrant_ScanAged": (-3.9, -0.3, 0, 0),
    "SM_Prop_OilDrum_Hazard": (-3.2, -0.3, 0, 0), "SM_Prop_OilDrum_Blue": (-2.5, -0.3, 0, 0),
    "SM_Prop_TrashCan_Metal": (-1.6, -0.3, 0, 0), "SM_Prop_TrashCan_Rust": (-0.7, -0.3, 0, 0),
    "SM_Prop_PlasticChair": (0.2, -0.3, 0, 0), "SM_Prop_CrateWood_Small": (1.15, -0.3, 0, 0),
    "SM_Prop_CardboardBox": (2.0, -0.3, 0, 0), "SM_Prop_Tyre": (2.7, -0.3, 0, 0),
    "SM_Prop_PropaneTank_Scan": (3.35, -0.3, 0, 0), "SM_Prop_FireExtinguisher": (3.9, -0.3, 0, 0),
    "SM_Prop_Boombox": (-1.2, -1.3, 0, 0), "SM_Prop_Crowbar": (-0.2, -1.3, 0, 20), "SM_Prop_Bat": (0.6, -1.3, 0, -15),
}


def _scale_box(loc):
    b = geo.box((0.4, 0.4, 1.8), bevel=0.01, name="ScaleBox_1m80")
    X(b, loc)
    b.data.materials.append(mat.flat("M_Preview_Grey", (0.18, 0.18, 0.18), 0.8))
    scene.move_to(b, scene.collection("Rig"))
    return b


def on_preview(ctx, objs):
    a = ctx.args
    only = set(a.only or [])
    assets = {n: v["ob"] for n, v in ctx.assets.items()}
    render.setup(samples=a.samples, res=(1280, 720))
    render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING)
    render.backdrop(color=(0.16, 0.155, 0.15))
    if not only or "props_scanned" in only:
        for n, ob in assets.items():
            ob.hide_render = n not in SCAN_LAYOUT
            if n in SCAN_LAYOUT:
                x, y, z, yaw = SCAN_LAYOUT[n]
                ob.location = (x, y, z)
                ob.rotation_euler = (0, 0, math.radians(yaw))
        wall = geo.box((10.0, 0.2, 3.0), bevel=0.0, name="PreviewWall")
        X(wall, (0, 3.1, 0))
        wall.data.materials.append(mat.flat("M_Preview_Wall", (0.30, 0.29, 0.27), 0.85))
        box = _scale_box((4.6, 2.4, 0))
        render.cam_look((0.6, -8.2, 3.9), (0.1, 0.9, 0.7), lens=30)
        p, sec = render.render_jpeg(os.path.join(paths.previews, "props_scanned.jpg"), a.samples)
        ctx.log("preview %s %.0fs" % (p, sec))
        for o in (wall, box):
            bpy.data.objects.remove(o, do_unlink=True)
    if not only or "props_gameplay" in only:
        place = {
            "SM_Gameplay_MasterCase": (0, 0, 0, 0), "SM_Gameplay_MasterCase_Beacon": (0, 0, 0, 0),
            "SM_Gameplay_MasterReel_1": (0, 0, 0, 0), "SM_Prop_Boombox": (0.21, 0.05, 0, 66),
            "SM_Gameplay_MasterReel_2": (0.95, -0.75, -0.475, 0), "SM_Gameplay_MasterReel_3": (1.35, -0.6, -0.475, -25),
            "SM_Gameplay_PropaneTank": (-1.05, -0.2, 0, 0), "SM_Prop_PropaneTank_Scan": (-1.45, 0.35, 0, 0),
            "SM_Gameplay_WeldingRack": (1.75, 0.75, 0, -20),
        }
        for n, ob in assets.items():
            ob.hide_render = n not in place and n != "SM_Gameplay_MasterCase_Lid"
            if n in place:
                x, y, z, yaw = place[n]
                ob.location = (x, y, z)
                ob.rotation_euler = (0, 0, math.radians(yaw))
        box = _scale_box((-2.0, 0.9, 0))
        render.cam_look((0.05, -4.0, 1.75), (0.1, 0.35, 0.55), lens=32)
        p, sec = render.render_jpeg(os.path.join(paths.previews, "props_gameplay.jpg"), a.samples)
        ctx.log("preview %s %.0fs" % (p, sec))
    if "gaps_gameplay" in only:
        _gaps_gameplay_preview(ctx, assets)


def _heat_glow(ob, name, strength=2.5):
    """Preview only: light the lit state (heat mask x #b8400f) on the baked material."""
    d = paths.texture_set("Gameplay_" + name)
    p = os.path.join(d, "T_Gameplay_%s_Heat.png" % name)
    if not os.path.exists(p):
        return
    for sl in ob.material_slots:
        m = sl.material
        nt = m.node_tree
        b = mat.principled(m)
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(p, check_existing=True)
        t.image.colorspace_settings.name = "Non-Color"
        mul = nt.nodes.new("ShaderNodeMixRGB")
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(t.outputs["Color"], mul.inputs[1])
        mul.inputs[2].default_value = (*lin("#b8400f"), 1.0)
        nt.links.new(mul.outputs[0], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = strength


def _gaps_gameplay_preview(ctx, assets):
    a = ctx.args
    place = {
        "SM_Gameplay_MasterCase": (0, 0, 0, 0), "SM_Gameplay_MasterCase_Beacon": (0, 0, 0, 0),
        "SM_Gameplay_MasterReel_1": (0, 0, 0, 0), "SM_Prop_Boombox": (0.21, 0.05, 0, 66), "SM_Prop_Boombox_Meter": (0.21, 0.05, 0, 66),
        "SM_Gameplay_PropaneTank": (-1.10, 0.25, 0, 0), "SM_Gameplay_PropaneTank_Wreck": (-0.95, -0.55, 0, 0),
        "SM_Gameplay_WeldingRack": (1.55, 0.9, 0, -20), "SM_Gameplay_WeldingRack_Wreck": (1.25, -0.45, 0, -10),
    }
    for n, ob in assets.items():
        ob.hide_render = n not in place and n not in ("SM_Gameplay_MasterCase_Lid", "SM_Gameplay_MasterCase_Progress")
        if n in place:
            x, y, z, yaw = place[n]
            ob.location = (x, y, z)
            ob.rotation_euler = (0, 0, math.radians(yaw))
    lid, strip = assets.get("SM_Gameplay_MasterCase_Lid"), assets.get("SM_Gameplay_MasterCase_Progress")
    if lid and strip:
        strip.parent = lid
        strip.location = (-0.17, TRACK_Y, 0.0077)
        strip.scale = (0.62, 1.0, 1.0)
    for n in ("PropaneTank", "WeldingRack"):
        if "SM_Gameplay_" + n in assets:
            _heat_glow(assets["SM_Gameplay_" + n], n)
    for n in ("SM_Prop_Boombox_Meter",):
        ob = assets.get(n)
        if ob:
            for k, sl in enumerate(ob.material_slots):
                if "Meter" in sl.material.name:
                    mat.principled(sl.material).inputs["Emission Strength"].default_value = 6.0
    render.cam_look((0.15, -3.3, 1.45), (0.15, 0.2, 0.55), lens=32)
    p, sec = render.render_jpeg(os.path.join(paths.previews, "gaps_gameplay.jpg"), a.samples)
    ctx.log("preview %s %.0fs" % (p, sec))
