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
        if ctx.args.only and spec[0] not in ctx.args.only and "scans" not in ctx.args.only:
            continue
        out.append(scan_prop(ctx, spec, cache))
    for objs in cache.values():                       # drop the imported originals
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
    return out


# --------------------------------------------------------------------------------------------------------- build

def build(ctx):
    objs = build_scans(ctx)
    return objs
