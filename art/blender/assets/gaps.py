"""Gap-filling family: every non-vehicle catalogue id that had no mesh, and properly sized modelled versions of the
items whose scan did not match the brief (names exactly as docs/unreal/spec/assets/props.json gives them, so the
level picks them first).

Street: SM_Street_PhoneBooth, _TrafficLight, _Planter (+_B), _Tree (+_B, _C), _TrashCan (wire basket), _Bench (1.76),
        _FoodCart (umbrella, menus, gear), _SignPost (plate + street-name blade), _JerseyBarrier (3.0 m),
        SM_Sign_PawnBalls, SM_Sign_BarberPole (shop-front extras).
Yard:   SM_Prop_Generator, _FloodlightStand, _PortaPotty, _VendingMachine, _Workbench, _EngineHoist (+_Blue),
        _Compressor (+_Black), _CarLift + _CarLift_Arms, _ToolChest (roller cabinet + top chest), _CrateWood (+_B),
        _CardboardBoxes, _Tire (0.77) and _TireStack (+_B).

Frames (05b 4.1): props pivot on the footprint centre on the ground, front toward -Y (catalogue), long axis +X.
Materials: tiling scan sets with world-scale UVs and the Wear mask (furniture.materials), plus numpy-drawn tiling
sets (bark, leaves, kraft board, brushed stainless: assets/_gaps_art.py), a clean neutral white painted steel
(TS_Steel_PaintWhiteClean, procedural, baked with --bake) and the printed faces M_Sign_<Key>.
Foliage is modelled (opaque leaf polygons cut to the leaf outline, 8 triangles each, no alpha): Nanite renders
opaque geometric foliage cheaply and Lumen lights it correctly, where masked cards cost overdraw, shimmer and
break Nanite's cluster culling; the leaf set is one leaf over 0..1 (two-sided foliage shading in engine).

    build.py build gaps --bake --export            (first run: bakes the white paint set, draws every face)
    build.py build gaps --export --only street|yard|art|<asset names>
    build.py build gaps --preview --only gaps_street,gaps_yard,gaps_graphics
"""
import math
import os

import bpy
import numpy as np

from assets import _gaps_art as ART
from assets import furniture as F
from assets.facade import bar, rod
from assets.furniture import B, board, box, card, lathe, pipe, tube_path
from mi import geo, mat, paths, render, scene, steel

FAMILY = {"name": "gaps", "description": "Catalogue gaps: phone booth, traffic light, planter, trees, yard and garage props, resized street props"}

X, Y, Z = np.eye(3)
WHITE = "TS_Steel_PaintWhiteClean"
WHITE_PARAMS = {"Paint Color": (0.74, 0.74, 0.72), "Paint Roughness": 0.40, "Chipping": 0.10, "Rust": 0.03,
                "Chalking": 0.30, "Old Coat": (0.50, 0.51, 0.51), "Primer Color": (0.42, 0.43, 0.43)}

META = dict(F.SLOT_META)
META.update({
    "MI_Steel_PaintWhiteClean": {"workflow": "tiling", "note": "clean neutral white enamel #e6e4dc, light chips to grey primer"},
    "MI_Steel_Stainless": {"workflow": "tiling", "note": "brushed stainless, grain along u (anisotropy in engine)"},
    "MI_Bark_Pear": {"workflow": "tiling", "note": "u around the stem, v along it"},
    "MI_Leaf_Pear": {"workflow": "foliage", "note": "one leaf over 0..1; opaque two-sided foliage, subsurface #6f8f2a"},
    "MI_Leaf_Privet": {"workflow": "foliage", "note": "one leaf over 0..1; opaque two-sided foliage, subsurface #4f6f22"},
    "MI_Cardboard_Kraft": {"workflow": "tiling"},
    "MI_Ground_ScanSoil": {"workflow": "tiling"},
    "MI_Lamp_Red": {"workflow": "flat", "note": "signal lens, emissive #ff2a1a when lit"},
    "MI_Lamp_Amber": {"workflow": "flat", "note": "signal lens, emissive #ffb020 when lit"},
    "MI_Lamp_Green": {"workflow": "flat", "note": "signal lens, emissive #30ff8a when lit"},
    "MI_Lamp_Flood": {"workflow": "flat", "note": "halogen lens, emissive #fff1d0 when lit"},
    "MI_Plastic_CabinGrey": {"set": "TS_Plastic_White", "workflow": "tiling", "tint": [0.38, 0.41, 0.45], "note": "#8d949a moulded PE"},
    "MI_Plastic_HoseYellow": {"set": "TS_Plastic_White", "workflow": "tiling", "tint": [0.95, 0.52, 0.02], "note": "#d9a21a"},
    "MI_Plastic_Brown": {"set": "TS_Plastic_White", "workflow": "tiling", "tint": [0.20, 0.07, 0.02]},
    "MI_Plastic_LatchGreen": {"set": "TS_Plastic_White", "workflow": "tiling", "tint": [0.03, 0.55, 0.10], "note": "#3ddc6a vacant dot"},
    "MI_Plastic_Tape": {"set": "TS_Plastic_White", "workflow": "tiling", "tint": [0.75, 0.55, 0.30], "note": "#cbb892 packing tape"},
    "MI_Fabric_UmbrellaRed": {"set": "TS_Fabric_ScanCanvas", "workflow": "tiling", "tint": [1.9, 0.09, 0.07], "note": "#c2261e"},
    "MI_Fabric_UmbrellaYellow": {"set": "TS_Fabric_ScanCanvas", "workflow": "tiling", "tint": [2.6, 1.75, 0.10], "note": "#e9c21a"},
    "MI_Metal_Gold": {"workflow": "flat", "note": "gilded metal, base #e7b53a, metallic 1, roughness 0.28"},
})
NEW_SIGNS = {   # key: (flat colour, note)
    "PhoneHead": ((0.02, 0.08, 0.3), "PHONE, white on blue, lit (E), 0.90 x 0.22 on three faces"),
    "PhoneCard": ((0.8, 0.8, 0.78), "instruction card and 25 cents, 0.30 x 0.20"),
    "PedHand": ((0.01, 0.01, 0.01), "orange raised hand on louvres (E), 0.15 x 0.15"),
    "PedWalk": ((0.01, 0.01, 0.01), "white walking figure on louvres (E), 0.15 x 0.15"),
    "Vending": ((0.02, 0.2, 0.5), "ICE COLD SODA back-lit face (E), 0.60 x 1.20"),
    "GenLabel": ((0.8, 0.8, 0.78), "DANGER / HIGH VOLTAGE / 60 kW 480 V, 0.62 x 0.32"),
    "PortaPlate": ((0.02, 0.08, 0.3), "HOLLIS / SITE SERVICES / UNIT 14, 0.30 x 0.22"),
    "FoodCartMenu": ((0.5, 0.02, 0.02), "HOT DOGS menu board, 1.5 x 0.52"),
    "CrateStencil": ((0.02, 0.02, 0.02), "FRAGILE stencil, decal with alpha, 0.66 x 0.44"),
    "VultureStencil": ((0.8, 0.78, 0.74), "crew stencil, decal with alpha, 0.5 x 0.4"),
    "CartonPrint": ((0.02, 0.02, 0.02), "THIS SIDE UP and arrows, decal with alpha, 0.34 x 0.22"),
    "CartonLabel": ((0.8, 0.8, 0.78), "shipping label with barcode, 0.15 x 0.10"),
    "StreetBlade": ((0.02, 0.1, 0.04), "JAMAICA AV street-name blade, 0.60 x 0.17, both faces"),
    "BarberPole": ((0.8, 0.8, 0.78), "red, white and blue helix on 0..1, panned in engine"),
    "LicensePlate": ((0.8, 0.8, 0.78), "licence plate HLS-2141, 0.30 x 0.15; swaps Sign_LicensePlate_TKV9907 / _KQB5530 / _LWG4418 / _Taxi"),
}
for _k, (_c, _d) in NEW_SIGNS.items():
    META["M_Sign_" + _k] = {"workflow": "sign", "uv": "0..1 over the face", "note": _d}


# ------------------------------------------------------------------------------------------------------ materials

def np_set(ctx, set_name, slot=None, alpha="splash", **kw):
    d = paths.texture_set(set_name)
    info = mat.find_set_files(d)
    import json
    with open(os.path.join(d, "set.json")) as f:
        tile = tuple(json.load(f)["tile_m"])
    m = mat.from_texture_set(d, name=slot or "MI_" + set_name[3:], tile_m=tile, alpha=alpha, **kw)
    m["mi_tile_m"] = tile
    if set_name not in ctx.sets:
        ctx.sets.append(set_name)
    return m


def lamp(name, col):
    m = mat.flat(name, col, 0.12, 0.0)
    b = mat.principled(m)
    b.inputs["Emission Color"].default_value = (*col, 1.0)
    b.inputs["Emission Strength"].default_value = 0.0
    return m


def materials(ctx):
    ART.draw_sets(force=False)
    if not os.path.exists(os.path.join(paths.texture_set("Sign_PhoneHead"), "set.json")) or ctx.want("art"):
        ART.furniture_faces()
        ART.new_faces()
    if not os.path.exists(os.path.join(paths.texture_set("Sign_LicensePlate"), "set.json")) or ctx.want("art"):
        ART.plate_faces()
    M = F.materials(ctx)
    sc, ts = ctx.scan_set, ctx.tiling_set
    M["white"] = ts(WHITE, "painted_steel", tile_m=1.0, res=1024, **WHITE_PARAMS)
    M["stain"] = np_set(ctx, "TS_Steel_Stainless", dirt_color=(0.12, 0.10, 0.08))
    M["bark"] = np_set(ctx, "TS_Bark_Pear", dirt_color=(0.05, 0.04, 0.03))
    M["leaf"] = np_set(ctx, "TS_Leaf_Pear", masks=False, macro=0.0)
    M["privet"] = np_set(ctx, "TS_Leaf_Privet", masks=False, macro=0.0)
    M["card"] = np_set(ctx, "TS_Cardboard_Kraft", dirt_color=(0.12, 0.08, 0.05))
    M["soil"] = sc("TS_Ground_ScanSoil", alpha="splash", macro=0.1)
    pw = dict(tile_m=1.0, res=1024, Color=(0.72, 0.72, 0.70), Roughness=0.5, **{"Sun Fade": 0.2, "Scratches": 0.45})
    for key, slot in (("cabin", "MI_Plastic_CabinGrey"), ("hose", "MI_Plastic_HoseYellow"), ("brown", "MI_Plastic_Brown"),
                      ("latch", "MI_Plastic_LatchGreen"), ("tape", "MI_Plastic_Tape")):
        tint = tuple(META[slot]["tint"])
        M[key] = ts("TS_Plastic_White", "plastic", slot=slot, mat_kw=dict(tint=tint), **pw)
        M[key]["mi_tint"] = tint
    for key, slot in (("umbRed", "MI_Fabric_UmbrellaRed"), ("umbYellow", "MI_Fabric_UmbrellaYellow")):
        tint = tuple(META[slot]["tint"])
        M[key] = sc("TS_Fabric_ScanCanvas", slot=slot, tint=tint, alpha="splash", dirt_color=(0.12, 0.09, 0.06), macro=0.15)
    M["lensRed"] = lamp("MI_Lamp_Red", (0.55, 0.04, 0.02))
    M["lensAmber"] = lamp("MI_Lamp_Amber", (0.60, 0.28, 0.02))
    M["lensGreen"] = lamp("MI_Lamp_Green", (0.03, 0.35, 0.15))
    M["lensFlood"] = lamp("MI_Lamp_Flood", (0.85, 0.82, 0.72))
    M["gold"] = mat.flat("MI_Metal_Gold", (0.80, 0.50, 0.12), 0.28, 1.0)
    for k, (c, _d) in NEW_SIGNS.items():
        M["sign" + k] = mat.sign_face(k, c, 0.45)
    return M


# ------------------------------------------------------------------------------------------------------- helpers

def centre(b, z0=True):
    """Move the parts so the footprint centre sits at the origin and the lowest point on z = 0 (no scaling)."""
    V = np.concatenate([p["v"] for p in b.parts])
    lo, hi = V.min(0), V.max(0)
    c = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] if z0 else 0.0])
    for p in b.parts:
        p["v"] = p["v"] - c
        p["uv_org"] = p["uv_org"] - c
    b.leaks = [tuple(np.asarray(l) - c) for l in b.leaks]
    return c


def done(ctx, b, name, M, notes, size=None, collision="box", cover=None, ground=True, ao=0.10, ctr=True, **wkw):
    if ctr:
        centre(b)
    ob = b.finish(name, M, ctx.col)
    F.weather(ctx, b, ob, name, ground=ground, ao=ao, **wkw)
    drop_slivers(ob)
    ctx.asset(ob, collision=collision, cover_height=cover, notes=notes, expect_size=size, slots=META)
    ctx.built.append(ob)
    return ob


def drop_slivers(ob):
    """Delete the faces export validation would call zero-area (lathe poles, coincident profile points)."""
    import bmesh
    me = ob.data
    area = np.empty(len(me.polygons), np.float32)
    me.polygons.foreach_get("area", area)
    bad = np.nonzero(area < 1e-11)[0]
    if len(bad):
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in bad], context="FACES_ONLY")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.to_mesh(me)
        bm.free()


def gob(ob, b, slot, loc=(0, 0, 0), rot=(0, 0, 0), **kw):
    """A Blender primitive moved and turned, taken into the builder."""
    geo.transform(ob, loc=loc, rot=rot)
    return b.absorb(ob, slot, **kw)


def gbox(b, size, slot, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.003):
    return gob(geo.box(size, bevel=bevel, base=False), b, slot, loc, rot)


def cyl(b, r, depth, slot, loc=(0, 0, 0), rot=(0, 0, 0), seg=24, bevel=0.0, axis="Z"):
    return gob(geo.cylinder(r, depth, seg, bevel=bevel, axis=axis, base=False), b, slot, loc, rot)


def frustum(b, p0, p1, r0, r1, slot, n=10, cap=True):
    """Tapered round bar from p0 (radius r0) to p1 (r1)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax = steel.unit(p1 - p0)
    u = steel.unit(np.cross(Z if abs(ax[2]) < 0.9 else X, ax))
    v = np.cross(ax, u)
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring0 = p0 + r0 * (np.cos(a)[:, None] * u + np.sin(a)[:, None] * v)
    ring1 = p1 + r1 * (np.cos(a)[:, None] * u + np.sin(a)[:, None] * v)
    V = np.concatenate([ring0, ring1])
    i = np.arange(n)
    j = (i + 1) % n
    q = np.stack([i, j, j + n, i + n], 1)
    loops = [q.ravel()]
    totals = [np.full(n, 4)]
    if cap:
        loops += [i[::-1], i + n]
        totals += [[n, n]]
    return b._add(V, np.concatenate(loops), np.concatenate(totals), slot, vdir=ax, fdir=u, kind=b.OTHER)


def sign_slot(M, key, w, h):
    M["sign" + key]["mi_tile_m"] = (float(w), float(h))


class Renamer:
    """Wrap ctx so a furniture builder declares its asset under the catalogue's name."""

    def __init__(self, ctx, names):
        self._ctx, self._names = ctx, names

    def __getattr__(self, k):
        return getattr(self._ctx, k)

    def asset(self, ob, **kw):
        if ob.name in self._names:
            ob.name = self._names[ob.name]
            ob.data.name = ob.name
        kw["slots"] = META
        return self._ctx.asset(ob, **kw)


# ------------------------------------------------------------------------------------------------------- leaves

def leaf_polys(leaves, kind="pear"):
    """Leaf meshes from (origin, along, side, normal, length, width, fold) records: 8 vertices, 8 triangles each,
    the outline of the drawn leaf, folded along the midrib. Returns (V, faces, UV per vertex)."""
    lv = np.array([0.0, 0.30, 0.66, 1.0])
    P = ART.leaf_outline(kind, 400)
    half = np.interp(lv, P[:200, 1], P[:200, 0] - 0.5)
    half[0], half[-1] = 0.0, 0.0
    # local (u across 0..1, v along 0..1, lift) of the 8 vertices: base, (L, M, R) x 2, tip
    loc = [(0.5, 0.0, 0.0)]
    for k in (1, 2):
        loc += [(0.5 - half[k], lv[k], 1.0), (0.5, lv[k], 0.0), (0.5 + half[k], lv[k], 1.0)]
    loc.append((0.5, 1.0, 0.0))
    loc = np.array(loc)
    tri = [(0, 1, 2), (0, 2, 3), (1, 4, 5, 2), (2, 5, 6, 3), (4, 7, 5), (5, 7, 6)]     # faces look along the leaf normal
    n = len(leaves)
    O = np.array([l[0] for l in leaves])
    A = np.array([l[1] for l in leaves])
    Sd = np.array([l[2] for l in leaves])
    Nn = np.array([l[3] for l in leaves])
    Ln = np.array([l[4] for l in leaves])[:, None]
    Wd = np.array([l[5] for l in leaves])[:, None]
    Fo = np.array([l[6] for l in leaves])[:, None]
    V = np.zeros((n, 8, 3))
    for i, (u, v, lift) in enumerate(loc):
        V[:, i] = O + A * (v * Ln) + Sd * ((u - 0.5) * Wd) + Nn * (lift * Fo * Wd * 0.25 - 0.06 * Ln * (v - 0.5) ** 2 * 2)
    faces = []
    base = np.arange(n) * 8
    for t in tri:
        faces.append(np.stack([base + k for k in t], 1))
    UV = np.tile(loc[:, :2], (n, 1))
    return V.reshape(-1, 3), faces, UV


def mesh_object(name, V, face_groups, UV, slots, col=None):
    """Mesh from vertices, face index arrays grouped by size, a per-vertex UV and per-group material index."""
    me = bpy.data.meshes.new(name)
    faces, mats = [], []
    for fa, mi in face_groups:
        faces += [tuple(int(x) for x in f) for f in fa]
        mats += [mi] * len(fa)
    me.from_pydata([tuple(v) for v in V], [], faces)
    me.update()
    uvl = me.uv_layers.new(name=geo.UV)
    vi = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", vi)
    uvl.data.foreach_set("uv", UV[vi].astype(np.float32).ravel())
    for m in slots:
        me.materials.append(m)
    me.polygons.foreach_set("material_index", np.array(mats, np.int32))
    ob = scene.new_object(name, me, col)
    return ob


# =============================================================================================== street

def phone_booth(ctx, M):
    b = B(201)
    sign_slot(M, "PhoneHead", 0.90, 0.22)
    sign_slot(M, "PhoneCard", 0.30, 0.20)
    box(b, (-0.45, -0.45, 0.0), (0.45, 0.45, 0.02), "galv", ch=0.004)                       # base plate
    for (x, y) in ((-0.43, -0.43), (0.43, -0.43), (-0.43, 0.43), (0.43, 0.43)):
        lathe(b, [(0.0, 0.0), (0.012, 0.0), (0.012, 0.006), (0.0, 0.008)], "galv", 8, loc=(x, y, 0.02))
    box(b, (-0.43, 0.40, 0.02), (0.43, 0.43, 1.96), "galv", ch=0.004)                       # back panel 0.86 x 1.94
    for s in (-1, 1):                                                                      # wings
        x0, x1 = (0.42, 0.45) if s > 0 else (-0.45, -0.42)
        box(b, (x0, -0.43, 0.02), (x1, 0.40, 0.92), "galv", ch=0.003)                        # steel to 0.92
        box(b, (x0, -0.45, 0.02), (x1, -0.42, 1.98), "galv", ch=0.003)                       # front post
        for z0 in (0.92, 1.93):
            box(b, (x0, -0.42, z0), (x1, 0.40, z0 + 0.03), "galv", ch=0.002)
        box(b, (min(x0, x1) + 0.01, -0.42, 0.95), (max(x0, x1) - 0.01, 0.40, 1.93), "glass", ch=0.0)
        for zz in (0.25, 0.6):                                                             # kick-panel ribs
            box(b, (x0 - 0.003 * s, -0.40, zz), (x1 + 0.003 * s, 0.38, zz + 0.02), "galv", ch=0.002)
    box(b, (-0.45, -0.45, 1.98), (0.45, 0.45, 2.20), "dark", ch=0.006)                       # head box
    card(b, (-0.45, -0.4515, 1.98), (0.90, 0, 0), (0, 0, 0.22), "signPhoneHead", sign=True)
    card(b, (0.4515, -0.45, 1.98), (0, 0.90, 0), (0, 0, 0.22), "signPhoneHead", sign=True)
    card(b, (-0.4515, 0.45, 1.98), (0, -0.90, 0), (0, 0, 0.22), "signPhoneHead", sign=True)
    box(b, (-0.28, -0.30, 1.972), (0.28, 0.20, 1.98), "lens", ch=0.0)                       # soffit light
    # coin phone 0.36 x 0.52 x 0.13 on the back panel
    box(b, (-0.18, 0.27, 1.0), (0.18, 0.40, 1.52), "stain", ch=0.012)
    card(b, (-0.15, 0.2685, 1.30), (0.30, 0, 0), (0, 0, 0.20), "signPhoneCard", sign=True)
    for i in range(3):                                                                     # 3 x 4 keypad
        for j in range(4):
            x, z = -0.035 + 0.035 * i, 1.235 - 0.032 * j
            box(b, (x - 0.013, 0.262, z - 0.011), (x + 0.013, 0.27, z + 0.011), "chrome", ch=0.002)
    box(b, (-0.06, 0.266, 1.11), (0.06, 0.27, 1.26), "dark", ch=0.0)                       # keypad bezel
    box(b, (0.10, 0.262, 1.45), (0.16, 0.27, 1.49), "chrome", ch=0.002)                     # coin slot plate
    box(b, (0.115, 0.2605, 1.466), (0.145, 0.262, 1.474), "black", ch=0.0)
    box(b, (0.07, 0.255, 1.02), (0.15, 0.27, 1.08), "chrome", ch=0.004)                     # coin return
    box(b, (-0.22, 0.30, 1.22), (-0.18, 0.37, 1.42), "dark", ch=0.004)                     # hook switch cradle
    cyl(b, 0.017, 0.20, "pBlack", loc=(-0.235, 0.33, 1.32), seg=12)                        # handset
    for zc in (1.21, 1.43):
        gbox(b, (0.05, 0.075, 0.05), "pBlack", loc=(-0.235, 0.325, zc), bevel=0.012)
    t = np.linspace(0, 1, 140)                                                             # coiled cord to the body
    path = np.stack([-0.235 + 0.07 * t, 0.33 - 0.02 * t, 1.19 - 0.30 * np.sin(np.pi * t * 0.9)], 1)
    a = t * 2 * np.pi * 30
    path[:, 0] += 0.008 * np.cos(a)
    path[:, 1] += 0.008 * np.sin(a)
    path[-1] = (-0.17, 0.33, 1.08)
    pipe(b, path, 0.0022, "pBlack", seg=6)
    box(b, (-0.26, 0.16, 0.84), (0.26, 0.40, 0.87), "galv", ch=0.003)                       # shelf
    for s in (-1, 1):
        rod(b, (s * 0.24, 0.17, 0.84), (s * 0.24, 0.39, 0.72), 0.008, "galv")
    return done(ctx, b, "SM_Street_PhoneBooth", M, "Catalogue street_phone_booth (generic, no marks): base plate 0.9 x 0.9, "
                "steel back 0.86 x 1.94, wings steel to 0.92 and glass to 1.96, head box 0.9 x 0.9 x 0.22 with the lit "
                "PHONE band on three faces (M_Sign_PhoneHead, emissive) and a soffit light (MI_Lamp_Lens), brushed "
                "stainless coin phone 0.36 x 0.52 x 0.13 with a 3 x 4 keypad, instruction card and 25 cents "
                "(M_Sign_PhoneCard), handset, coiled cord, shelf. Open toward -Y. Scrawl and stickers: decals.",
                (0.9, 0.9, 2.2), cover=2.2)


def traffic_light(ctx, M):
    b = B(202)
    sign_slot(M, "PedHand", 0.15, 0.15)
    sign_slot(M, "PedWalk", 0.15, 0.15)
    lathe(b, [(0.0, 0.0), (0.20, 0.0), (0.20, 0.03), (0.17, 0.06), (0.155, 0.40), (0.14, 0.43), (0.0, 0.43)], "dark", 24)
    for k in range(4):                                                                     # anchor nuts
        a = math.radians(45 + 90 * k)
        lathe(b, [(0.0, 0.0), (0.016, 0.0), (0.016, 0.02), (0.0, 0.022)], "galv", 6, loc=(0.16 * math.cos(a), 0.16 * math.sin(a), 0.03))
    lathe(b, [(0.14, 0.43), (0.135, 1.5), (0.12, 3.5), (0.105, 5.5), (0.11, 5.52), (0.11, 5.80), (0.06, 5.82), (0.0, 5.83)], "dark", 20)
    gbox(b, (0.10, 0.06, 0.34), "dark", loc=(0, -0.125, 5.62))                              # arm clamp plate
    frustum(b, (0, -0.10, 5.62), (0, -3.25, 5.72), 0.06, 0.038, "dark", 14)               # mast arm, slight rise
    lathe(b, [(0.0, 0.0), (0.04, 0.0), (0.04, 0.01), (0.0, 0.012)], "dark", 14, loc=(0, -3.25, 5.72), rot=(90, 0, 0))
    rod(b, (0, -0.10, 5.30), (0, -1.2, 5.66), 0.022, "dark", n=10)                          # brace
    # three-lamp head 0.34 x 0.34 x 1.02 at 3.05 out, lenses on both faces along X
    hy, zt = -3.05, 5.64
    rod(b, (0, hy, 5.70), (0, hy, zt), 0.02, "dark", n=10)
    gbox(b, (0.10, 0.10, 0.05), "yellow", loc=(0, hy, zt + 0.02))
    box(b, (-0.17, hy - 0.17, zt - 1.02), (0.17, hy + 0.17, zt), "yellow", ch=0.02)
    for s in (-1, 1):
        for k, key in enumerate(("lensRed", "lensAmber", "lensGreen")):
            zc = zt - 0.17 - 0.34 * k
            lathe(b, [(0.0, 0.018), (0.06, 0.016), (0.10, 0.006), (0.104, 0.0)], key, 32, loc=(s * 0.17, hy, zc), rot=(0, s * 90, 0))
            lathe(b, [(0.105, 0.0), (0.112, 0.0), (0.112, 0.012), (0.105, 0.012)], "black", 32, closed=True,
                  loc=(s * 0.17, hy, zc), rot=(0, s * 90, 0))
            gob(geo.tube(0.125, 0.118, 0.14, 32, name="vis"), b, "yellow", loc=(s * 0.17, hy, zc), rot=(0, s * 90, 0))
    # pedestrian head 0.36 x 0.36 on the pole at 2.7, facing -Y: hand left, walking figure right
    box(b, (-0.18, -0.36, 2.52), (0.18, -0.15, 2.88), "yellow", ch=0.015)
    for s in (-1, 1):
        box(b, (s * 0.03 - 0.02, -0.15, 2.62 + 0.06 * s), (s * 0.03 + 0.02, -0.10, 2.66 + 0.06 * s), "dark")
    card(b, (-0.165, -0.3615, 2.625), (0.15, 0, 0), (0, 0, 0.15), "signPedHand", sign=True)
    card(b, (0.015, -0.3615, 2.625), (0.15, 0, 0), (0, 0, 0.15), "signPedWalk", sign=True)
    box(b, (-0.18, -0.42, 2.80), (0.18, -0.36, 2.81), "yellow", ch=0.0)                     # visor top
    for s in (-1, 1):
        box(b, (s * 0.18 - 0.005, -0.42, 2.58), (s * 0.18 + 0.005, -0.36, 2.81), "yellow", ch=0.0)
    return done(ctx, b, "SM_Street_TrafficLight", M, "Catalogue street_traffic_light: cast base, tapered pole 5.5 (cap 5.83), "
                "mast arm 3.25 toward -Y at 5.72 with a brace, yellow three-lamp head 0.34 x 0.34 x 1.02 hung at 3.05 out "
                "with 0.20 lenses and tunnel visors on both faces along X (MI_Lamp_Red / _Amber / _Green: separately "
                "emissive), pedestrian head 0.36 at 2.7 facing -Y (M_Sign_PedHand, M_Sign_PedWalk: separate E maps).",
                (0.62, 3.41, None), collision="convex", cover=None, ao=None, ctr=False)


def planter(ctx, M, variant):
    b = B(203 + variant)
    r2 = math.sqrt(2.0)
    prof = [(0.0, 0.0), (0.50, 0.0), (0.50, 0.02), (0.58, 0.55), (0.60, 0.555), (0.60, 0.60), (0.535, 0.60), (0.50, 0.575),
            (0.46, 0.14), (0.0, 0.14)]
    lathe(b, [(r * r2, z) for r, z in prof], "conc", 4, rot=(0, 0, 45))
    lathe(b, [(0.0, 0.0), (0.49 * r2, 0.0), (0.49 * r2, 0.02), (0.0, 0.02)], "soil", 4, loc=(0, 0, 0.50), rot=(0, 0, 45))
    rng = ctx.rng("planter", variant)
    leaves = []
    h0, h1 = 0.52, 0.80
    n = 5200
    for _ in range(n):
        if variant == 0:                                    # clipped box: flat top, slight batter
            face = rng.random()
            if face < 0.42:
                p = np.array([rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), h1])
                nrm = np.array([0, 0, 1.0])
            else:
                s = rng.integers(4)
                t = rng.uniform(-0.5, 0.5)
                z = rng.uniform(h0 + 0.03, h1)
                d = 0.50 + 0.03 * (z - h0) / (h1 - h0)
                p = np.array([[d, t, z], [-d, t, z], [t, d, z], [t, -d, z]][s])
                nrm = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0]][s], float)
            ed = np.clip((np.abs(p[:2]) - 0.42) / 0.08, 0, 1)                       # round the clipped edges
            p[2] -= 0.05 * (ed[0] ** 2 + ed[1] ** 2) * (p[2] > h1 - 0.06)
            p[:2] -= np.sign(p[:2]) * 0.04 * ed * (p[2] > h1 - 0.08)
        else:                                               # rounded dome
            a = rng.uniform(0, 2 * np.pi)
            c = rng.uniform(0.0, 1.0) ** 0.7
            rr = 0.52 * c
            z = h0 + (h1 + 0.02 - h0) * math.sqrt(max(0.0, 1 - c ** 2.2))
            p = np.array([rr * math.cos(a) * 1.02, rr * math.sin(a), z])
            nrm = steel.unit(np.array([p[0] / 0.52, p[1] / 0.52, (z - h0) / 0.3]))
        p = p - nrm * abs(rng.normal(0, 0.025))
        tang = steel.unit(np.cross(nrm, rng.normal(size=3)))
        along = steel.unit(tang * 0.8 + nrm * rng.uniform(0.1, 0.6))
        side = steel.unit(np.cross(nrm, along))
        lnrm = steel.unit(np.cross(along, side))
        L = rng.uniform(0.035, 0.05)
        leaves.append((p, along, side, lnrm, L, L * 0.42, rng.uniform(0.3, 1.0)))
    # dark twiggy core so gaps read as depth, not sky
    core = geo.box((0.92, 0.92, 0.24), bevel=0.08, segments=3) if variant == 0 else geo.sphere(0.46, 24, 12)
    if variant:
        co, _ = geo.arrays(core)
        co[:, 2] = np.maximum(co[:, 2], 0) * 0.55
        geo.set_verts(core, co)
    geo.transform(core, loc=(0, 0, 0.52))
    b.absorb(core, "bark")
    name = "SM_Street_Planter" + ("_B" if variant else "")
    ob = b.finish(name + "_pot", M, ctx.col)
    F.weather(ctx, b, ob, name, ground=True, ao=0.10)
    V, faces, UV = leaf_polys(leaves, "privet")
    lv = mesh_object(name + "_leaves", V, [(faces[0], 0), (faces[1], 0), (faces[4], 0), (faces[5], 0), (faces[2], 0), (faces[3], 0)],
                     UV, [M["privet"]], ctx.col)
    geo.ensure_wear(lv)
    z = V[:, 2]
    geo.set_wear(lv, np.stack([0.15 * (z < 0.6), np.zeros_like(z), np.zeros_like(z), np.zeros_like(z)], 1), per="vertex")
    ob = geo.join([ob, lv], name, ctx.col)
    ctx.asset(ob, collision="box", cover_height=0.80, notes="Catalogue street_planter (%s): square tapered concrete planter, 1.0 at "
              "the foot to a 1.2 lip at 0.60, soil, clipped privet hedge to 0.80 (%d modelled leaves on MI_Leaf_Privet, "
              "dark twig core)." % ("dome-shaped hedge" if variant else "box-clipped hedge", n),
              expect_size=(1.2, 1.2, 0.80 if not variant else None), slots=META)
    ctx.built.append(ob)
    return ob


# ------------------------------------------------------------------------------------------------------- tree

def sstep_(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def tube_mesh(path, radii, n, u_tile, v_tile, cap=True):
    """Tube along a polyline with a radius per point (parallel-transport frames). UV: u = arc length round the
    stem / u_tile, v = length along / v_tile. Returns (V, quads, tips, UV)."""
    P = np.asarray(path, float)
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    ref = np.array([0.0, 0.0, 1.0]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    U = steel.unit(np.cross(ref, T[0]))
    a = np.linspace(0, 2 * np.pi, n + 1)
    V, UV = [], []
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    for i in range(len(P)):
        if i:
            U = U - np.dot(U, T[i]) * T[i]
            U = steel.unit(U)
        W = np.cross(T[i], U)
        ring = P[i] + radii[i] * (np.cos(a)[:, None] * U + np.sin(a)[:, None] * W)
        V.append(ring)
        UV.append(np.stack([a / (2 * np.pi) * 2 * np.pi * radii[0] / u_tile, np.full(n + 1, s[i] / v_tile)], 1))
    V = np.concatenate(V)
    UV = np.concatenate(UV)
    m = n + 1
    quads = [(i * m + j, i * m + j + 1, (i + 1) * m + j + 1, (i + 1) * m + j) for i in range(len(P) - 1) for j in range(n)]
    tips = []
    if cap:
        last = (len(P) - 1) * m
        tips.append(tuple(last + j for j in range(n)))
    return V, quads, tips, UV


def street_tree(ctx, M, variant):
    """Young Callery pear: leaning trunk 0.26 at the base forking at 2.7 into three boughs, crown about 4.6 wide
    from 3 m to 5.9, 'spur' leaf sprays on the twigs; tree pit 0.58 square with a welded steel guard 0.55 high."""
    rng = ctx.rng("tree", variant)
    lean = np.array([rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), 1.0])
    top = [5.90, 5.75, 5.82][variant]
    crx, cry = [(2.30, 2.35), (2.15, 2.25), (2.25, 2.10)][variant]
    cz0, cz1 = 3.0, top
    ccz, crz = (cz0 + cz1) / 2 + 0.15, (cz1 - cz0) / 2

    def inside(p, k=1.0):
        return ((p[0] - centre_xy[0]) / (crx * k)) ** 2 + ((p[1] - centre_xy[1]) / (cry * k)) ** 2 + ((p[2] - ccz) / (crz * k)) ** 2

    stems = []                 # (path, radii)
    sprays = []                # (point, direction)
    fork = np.array([0.0, 0.0, 0.0]) + steel.unit(lean) * 2.7
    fork[2] = 2.7
    centre_xy = fork[:2] * 1.05
    zs = np.linspace(0, 1, 14)
    trunk = np.outer(zs, fork) + np.stack([0.02 * np.sin(zs * 7 + variant), 0.02 * np.cos(zs * 5), np.zeros_like(zs)], 1) * zs[:, None]
    flare = 1 + 0.35 * np.exp(-zs * 2.7 / 0.25)
    stems.append((trunk, 0.13 * flare * (1 - 0.30 * zs)))
    a0 = rng.uniform(0, 2 * np.pi)
    for k in range(3):
        az = a0 + k * 2 * np.pi / 3 + rng.uniform(-0.3, 0.3)
        tilt = math.radians(rng.uniform(28, 40))
        d0 = np.array([math.sin(tilt) * math.cos(az), math.sin(tilt) * math.sin(az), math.cos(tilt)])
        L = rng.uniform(2.3, 2.9)
        t = np.linspace(0, 1, 12)
        bend = np.outer(t ** 2, np.array([0, 0, 0.35]))                                  # boughs turn upward
        bough = fork + np.outer(t * L, d0) + bend * L * 0.3 + np.outer(np.sin(t * 3.0), rng.normal(0, 0.05, 3))
        stems.append((bough, 0.075 * (1 - 0.75 * t) + 0.012))
        nsec = int(L / 0.17)
        for j in range(nsec):                                                             # secondary branches
            tt = 0.15 + 0.85 * (j + rng.uniform(0, 0.6)) / nsec
            i = min(10, int(tt * 11))
            p0 = bough[i] + (bough[i + 1] - bough[i]) * (tt * 11 - i)
            if p0[2] < cz0 - 0.2:
                continue
            ang = rng.uniform(0, 2 * np.pi)
            out = steel.unit(np.array([math.cos(ang), math.sin(ang), rng.uniform(-0.2, 0.9)]) + 0.8 * d0)
            Lb = rng.uniform(0.6, 1.5)
            pts = [p0]
            for s_ in range(6):
                q = pts[-1] + out * Lb / 6
                if inside(q) > 1.0:
                    break
                pts.append(q)
                out = steel.unit(out + rng.normal(0, 0.12, 3) + np.array([0, 0, 0.05]))
            if len(pts) < 3:
                continue
            pts = np.array(pts)
            rb = 0.024 * (1 - 0.7 * np.linspace(0, 1, len(pts))) + 0.004
            stems.append((pts, rb))
            for m_ in range(1, len(pts)):                                                # twigs with leaf sprays
                for _ in range(3):
                    tw_dir = steel.unit(out + rng.normal(0, 0.7, 3))
                    q0 = pts[m_]
                    q1 = q0 + tw_dir * rng.uniform(0.12, 0.30)
                    if inside(q1) > 1.08:
                        q1 = q0 + (q1 - q0) * 0.4
                    stems.append((np.array([q0, (q0 + q1) / 2, q1]), np.array([0.006, 0.0045, 0.003])))
                    sprays.append((q1, tw_dir))
                    sprays.append(((q0 + q1) / 2, tw_dir))
    # leaves: 14 per spray, petioles on the spur, blades hanging and turned to the light
    leaves = []
    for (p, d) in sprays:
        for _ in range(15):
            o = p + rng.normal(0, 0.05, 3)
            along = steel.unit(rng.normal(0, 1, 3) + 0.6 * d + np.array([0, 0, -0.25]))
            up = steel.unit(np.array([0, 0, 1.0]) + rng.normal(0, 0.45, 3))
            side = steel.unit(np.cross(up, along))
            nrm = steel.unit(np.cross(along, side))
            L = rng.uniform(0.065, 0.095)
            leaves.append((o, along, side, nrm, L, L * 0.62, rng.uniform(0.2, 0.9)))
    # stretch the crown to its brief width (the envelope test keeps it inside but leaves it narrow)
    allp = np.concatenate([np.concatenate([p for p, _ in stems]), np.array([l[0] for l in leaves])])
    lo, hi = allp.min(0) - 0.06, allp.max(0) + 0.06
    sx, sy = 2 * crx / (hi[0] - lo[0]), 2 * cry / (hi[1] - lo[1])
    cxy = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2])

    def stretch(P):
        P = np.array(P, float)
        f = sstep_(2.6, 3.6, P[..., 2])
        P[..., 0] = cxy[0] + (P[..., 0] - cxy[0]) * (1 + (sx - 1) * f)
        P[..., 1] = cxy[1] + (P[..., 1] - cxy[1]) * (1 + (sy - 1) * f)
        return P
    stems = [(stretch(p), r) for p, r in stems]
    leaves = [(stretch(l[0]),) + tuple(l[1:]) for l in leaves]
    # bark mesh
    BV, BQ, BT, BUV = [], [], [], []
    off = 0
    for path, radii in stems:
        n = 12 if radii[0] > 0.05 else (8 if radii[0] > 0.015 else 4)
        V_, Q_, T_, UV_ = tube_mesh(path, radii, n, 0.5, 0.5, cap=True)
        BV.append(V_)
        BUV.append(UV_)
        BQ += [tuple(i + off for i in q) for q in Q_]
        BT += [tuple(i + off for i in t) for t in T_]
        off += len(V_)
    BV, BUV = np.concatenate(BV), np.concatenate(BUV)
    LV, LF, LUV = leaf_polys(leaves, "pear")
    nb = len(BV)
    V = np.concatenate([BV, LV])
    UVv = np.concatenate([BUV, LUV])
    groups = [(BQ, 0), (BT, 0)] + [(f + nb, 1) for f in LF]
    name = "SM_Street_Tree" + ("", "_B", "_C")[variant]
    tree = mesh_object(name + "_crown", V, [g for g in groups if len(g[0])], UVv, [M["bark"], M["leaf"]], ctx.col)
    geo.smooth_by_angle(tree, 60)
    z = V[:, 2]
    north = np.zeros(len(V))
    north[:nb] = np.clip((V[:nb, 1] - fork[1]) * 4, 0, 1) * 0.6                          # algae on the shaded side
    R = np.where(np.arange(len(V)) < nb, 0.15 + 0.4 * np.exp(-z / 0.5), 0.08)
    A = np.where(np.arange(len(V)) < nb, np.exp(-z / 0.25), 0.0)
    geo.ensure_wear(tree)
    geo.set_wear(tree, np.stack([R, north, np.zeros(len(V)), A], 1), per="vertex")
    # tree pit and guard
    b = B(210 + variant)
    box(b, (-0.29, -0.29, -0.03), (0.29, 0.29, 0.0), "soil", ch=0.0)
    for s in (-1, 1):                                                                    # steel pit edge angles
        box(b, (-0.30, s * 0.29 - 0.006, -0.03), (0.30, s * 0.29 + 0.006, 0.002), "dark")
        box(b, (s * 0.29 - 0.006, -0.29, -0.03), (s * 0.29 + 0.006, 0.29, 0.002), "dark")
    g = 0.30
    for (x, y) in ((-g, -g), (g, -g), (g, g), (-g, g)):
        box(b, (x - 0.0125, y - 0.0125, 0.0), (x + 0.0125, y + 0.0125, 0.55), "dark", ch=0.002)
    for z_ in (0.10, 0.53):
        for s in (-1, 1):
            box(b, (-g, s * g - 0.006, z_), (g, s * g + 0.006, z_ + 0.02), "dark", ch=0.0015)
            box(b, (s * g - 0.006, -g, z_), (s * g + 0.006, g, z_ + 0.02), "dark", ch=0.0015)
    for t in np.linspace(-g + 0.1, g - 0.1, 5):
        for s in (-1, 1):
            rod(b, (t, s * g, 0.12), (t, s * g, 0.53), 0.006, "dark", n=6)
            rod(b, (s * g, t, 0.12), (s * g, t, 0.53), 0.006, "dark", n=6)
    for k in range(4):                                                                   # mulch, litter
        F.blob(b, (rng.uniform(0.08, 0.16), rng.uniform(0.06, 0.12), 0.03), (rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), -0.01),
               "soil", int(rng.integers(1000)), lumps=0.01)
    guard = b.finish(name + "_guard", M, ctx.col)
    F.weather(ctx, b, guard, name, ground=True, ao=None)
    ob = geo.join([tree, guard], name, ctx.col)
    h = float(V[:, 2].max())
    ctx.asset(ob, collision="box", cover_height=0.55, notes="Catalogue street_tree (%d of 3): young Callery pear %.2f m, leaning trunk "
              "0.26 at the base forking at 2.7 into three boughs, crown from 3 m (%d modelled leaves, 8 triangles each, "
              "MI_Leaf_Pear: opaque two-sided foliage, no alpha; bark MI_Bark_Pear with world-scale UVs, Wear G = algae "
              "on the north side), tree pit 0.58 with a welded steel guard 0.55. Collision: guard box to 0.55 and a trunk "
              "capsule 0.26 to 3.0 (add in engine); the crown has none." % (variant + 1, h, len(leaves)),
              expect_size=(4.6, 4.7, 5.9) if variant == 0 else None, slots=META)
    ctx.built.append(ob)
    return ob


# ------------------------------------------------------------------------------------------------- bins, bench

def trash_can(ctx, M):
    b = B(220)
    lathe(b, [(0.0, 0.0), (0.225, 0.0), (0.235, 0.01), (0.235, 0.045), (0.0, 0.045)], "galv", 40)
    rad = lambda z: 0.23 + (0.283 - 0.23) * (z - 0.045) / (0.90 - 0.045)
    n = 40
    for k in range(n):                                                                   # vertical wires
        a = 2 * np.pi * k / n
        p0 = (rad(0.045) * math.cos(a), rad(0.045) * math.sin(a), 0.04)
        p1 = (rad(0.90) * math.cos(a), rad(0.90) * math.sin(a), 0.905)
        rod(b, p0, p1, 0.0035, "galv", n=6)
    for z in np.arange(0.12, 0.90, 0.085):                                                # rings
        pts = [(rad(z) * math.cos(a), rad(z) * math.sin(a), z) for a in np.linspace(0, 2 * np.pi, n + 1)]
        tube_path(b, pts, 0.0035, "galv", n=6)
    for z in (0.30, 0.62):                                                                # flat straps
        pts = [((rad(z) + 0.004) * math.cos(a), (rad(z) + 0.004) * math.sin(a), z) for a in np.linspace(0, 2 * np.pi, 49)]
        for p0, p1 in zip(pts[:-1], pts[1:]):
            bar(b, p0, p1, 0.03, 0.004, "galv", up=Z)
    lathe(b, [(0.283 + 0.018 * math.cos(t), 0.92 + 0.018 * math.sin(t)) for t in np.linspace(0, 2 * np.pi, 13)[:-1]][::-1],
          "galv", 48, closed=True)                                                         # rolled rim
    bag = geo.revolve([(0.0, 0.06), (0.20, 0.07), (0.255, 0.60), (0.27, 0.86), (0.295, 0.925), (0.302, 0.94), (0.298, 0.90),
                       (0.296, 0.84)], 40, name="bag")
    geo.densify(bag, 0.05, 3)
    geo.displace(bag, 0.010, 6.0, 3)
    b.absorb(bag, "bagBlack")
    rng = ctx.rng("litter")
    F.blob(b, (0.52, 0.50, 0.12), (0.0, 0.0, 0.83), "bagBlack", 4, lumps=0.03)
    box(b, (-0.17, -0.12, 0.90), (0.13, 0.16, 0.94), "card", ch=0.003)                     # pizza box on top
    lathe(b, [(0.0, 0.0), (0.032, 0.0), (0.044, 0.14), (0.046, 0.142), (0.0, 0.142)], "pWhite", 20, loc=(0.12, -0.10, 0.90),
          rot=(70, 0, 30))                                                                 # cup on its side
    box(b, (-0.05, 0.02, 0.90), (0.15, 0.24, 0.905), "signNewspaper", ch=0.0)
    return done(ctx, b, "SM_Street_TrashCan", M, "Catalogue street_trash_can: city wire litter basket, heavy galvanised wires "
                "flaring from 0.46 at the solid base to 0.57 at the rolled rim (0.90-0.94), two flat straps, black liner "
                "folded over the rim with litter heaped to 0.96 (pizza box, cup, newspaper).", (0.61, 0.61, 0.96),
                collision="convex", cover=0.95, ao=None)


def bench(ctx, M):
    b = B(221)
    sup = [(-0.27, 0.0), (-0.20, 0.0), (-0.17, 0.30), (0.10, 0.30), (0.16, 0.0), (0.23, 0.0), (0.17, 0.40), (0.24, 0.84),
           (0.205, 0.84), (0.135, 0.455), (-0.25, 0.425), (-0.255, 0.395), (-0.20, 0.38)]
    for x in (-0.84, 0.0, 0.84):
        b.poly_plate([(x + 0.02, y, z) for y, z in sup], 0.04, "dark", step=0.5)
    for s in (-1, 1):                                                                    # arm rests at both ends
        x = s * 0.84
        bar(b, (x, -0.29, 0.64), (x, 0.16, 0.66), 0.05, 0.03, "dark")
        rod(b, (x, -0.25, 0.44), (x, -0.27, 0.64), 0.018, "dark")
        lathe(b, [(0.0, 0.0), (0.03, 0.0), (0.03, 0.02), (0.0, 0.03)], "dark", 12, loc=(x, -0.29, 0.64), rot=(90, 0, 0))
    for y in (-0.245, -0.145, -0.045, 0.055):                                             # seat slats at 0.455
        board(b, (-0.88, y, 0.425), (0.88, y + 0.09, 0.455), "plank")
    for zc in (0.56, 0.67, 0.78):                                                         # back slats
        yb = 0.135 + (0.24 - 0.135) * (zc - 0.455) / (0.84 - 0.455) - 0.03
        nrm = steel.unit(np.array([0, -1.0, (0.24 - 0.135) / (0.84 - 0.455)]))
        bar(b, (-0.88, yb, zc), (0.88, yb, zc), 0.09, 0.028, "plank", up=nrm)
    for x in (-0.84, 0.0, 0.84):                                                          # carriage bolts
        for y in (-0.20, -0.10, 0.0, 0.10):
            lathe(b, [(0.0, 0.0), (0.008, 0.0), (0.007, 0.003), (0.0, 0.004)], "galv", 8, loc=(x + 0.02, y, 0.455))
    return done(ctx, b, "SM_Street_Bench", M, "Catalogue street_bench: park bench 1.76 long, three cast-iron supports (plates "
                "0.04 thick), four timber seat slats at 0.455, three back slats to 0.84, arm rests at both ends, carriage "
                "bolts. Seat faces -Y.", (1.76, 0.55, 0.84), cover=0.85)


# ------------------------------------------------------------------------------------------------------- food cart

def umbrella(b, M, c, rx, ry, rim, apex, panels=8):
    """Eight-panel market umbrella: sagging cloth panels in alternating colours, ribs, stretchers, hem."""
    for k in range(panels):
        a0, a1 = 2 * np.pi * k / panels, 2 * np.pi * (k + 1) / panels
        rows, cols = 7, 7
        Fp = np.zeros((rows, cols, 3))
        for i, t in enumerate(np.linspace(0.02, 1.0, rows)):
            for j, s in enumerate(np.linspace(0, 1, cols)):
                a = a0 + (a1 - a0) * s
                sag = 0.03 * math.sin(math.pi * s) * t
                rr = t * (1 - 0.04 * math.sin(math.pi * s))
                z = apex - (apex - rim) * t ** 1.25 - sag
                Fp[i, j] = (c[0] + rr * rx * math.cos(a), c[1] + rr * ry * math.sin(a), z)
        from assets.facade import sheet
        sheet(b, Fp[:, ::-1], 0.002, "umbRed" if k % 2 == 0 else "umbYellow")
    for k in range(panels):
        a = 2 * np.pi * k / panels
        pts = [(c[0] + t * rx * math.cos(a), c[1] + t * ry * math.sin(a), apex - (apex - rim) * t ** 1.25 - 0.006) for t in np.linspace(0.03, 1.0, 6)]
        tube_path(b, pts, 0.004, "dark", n=6)
        mid = pts[3]
        rod(b, (c[0], c[1], apex - 0.42), (mid[0], mid[1], mid[2] - 0.004), 0.0035, "dark", n=6)
        lathe(b, [(0.0, 0.0), (0.008, 0.0), (0.006, 0.02), (0.0, 0.022)], "pBlack", 8, loc=pts[-1], rot=(0, 0, 0))
    lathe(b, [(0.0, 0.0), (0.04, 0.0), (0.03, 0.03), (0.0, 0.05)], "dark", 16, loc=(c[0], c[1], apex - 0.03))


def food_cart(ctx, M):
    b = B(230)
    sign_slot(M, "FoodCartMenu", 1.5, 0.52)
    box(b, (-0.85, -0.43, 0.28), (0.85, 0.43, 1.0), "stain", ch=0.012)                     # body 1.70 x 0.86 x 0.72
    for x0 in (-0.80, -0.02):                                                             # doors on the +Y side
        box(b, (x0, 0.430, 0.33), (x0 + 0.76, 0.436, 0.95), "stain", ch=0.002)
        box(b, (x0 + 0.66, 0.436, 0.60), (x0 + 0.70, 0.45, 0.68), "chrome", ch=0.003)
    box(b, (-0.87, -0.45, 1.0), (0.87, 0.45, 1.02), "stain", ch=0.004)                     # worktop at 1.0
    for s in (-1, 1):                                                                      # menu boards on both long sides
        y = s * 0.43
        box(b, (-0.77, y + s * 0.0, 0.37), (0.77, y + s * 0.012, 0.93), "stain", ch=0.003)
        if s < 0:
            card(b, (-0.75, y - 0.0125, 0.39), (1.5, 0, 0), (0, 0, 0.52), "signFoodCartMenu", sign=True)
        else:
            card(b, (0.75, y + 0.0125, 0.39), (-1.5, 0, 0), (0, 0, 0.52), "signFoodCartMenu", sign=True)
    for s in (-1, 1):                                                                      # wheels 0.40 on an axle
        lathe(b, [(0.12, -0.035), (0.17, -0.04), (0.20, -0.025), (0.20, 0.025), (0.17, 0.04), (0.12, 0.035)], "rubber", 32,
              closed=True, loc=(-0.15, s * 0.48, 0.20), rot=(90, 0, 0))
        lathe(b, [(0.0, -0.03), (0.125, -0.03), (0.125, 0.03), (0.0, 0.03)], "galv", 24, loc=(-0.15, s * 0.48, 0.20), rot=(90, 0, 0))
        box(b, (-0.21, s * 0.43, 0.20), (-0.09, s * 0.445, 0.33), "stain")
    rod(b, (-0.15, -0.50, 0.20), (-0.15, 0.50, 0.20), 0.015, "galv")
    rod(b, (0.85, -0.25, 0.40), (1.30, 0.0, 0.40), 0.02, "dark")                           # tow bar to a hitch
    rod(b, (0.85, 0.25, 0.40), (1.30, 0.0, 0.40), 0.02, "dark")
    lathe(b, [(0.0, -0.03), (0.04, -0.03), (0.045, 0.0), (0.04, 0.03), (0.0, 0.03)], "dark", 16, loc=(1.28, 0, 0.40))
    rod(b, (1.0, 0.0, 0.40), (1.0, 0.0, 0.06), 0.022, "galv")                              # jockey leg
    lathe(b, [(0.0, -0.025), (0.05, -0.025), (0.05, 0.025), (0.0, 0.025)], "rubber", 16, loc=(1.0, 0, 0.05), rot=(90, 0, 0))
    # gear on the worktop
    box(b, (-0.78, -0.25, 1.02), (-0.24, 0.25, 1.16), "stain", ch=0.004)                    # steam pan
    lid = geo.box((0.54, 0.25, 0.012), bevel=0.003)
    gob(lid, b, "stain", loc=(-0.51, 0.125, 1.16), rot=(-24, 0, 0))
    lathe(b, [(0.0, 0.0), (0.02, 0.0), (0.02, 0.015), (0.0, 0.02)], "pBlack", 12, loc=(-0.51, 0.12, 1.25))
    box(b, (-0.16, -0.22, 1.02), (0.34, 0.20, 1.05), "dark", ch=0.003)                      # griddle
    box(b, (-0.16, 0.18, 1.05), (0.34, 0.20, 1.10), "dark")
    for k, key in enumerate(("crateRed", "hose", "brown")):                               # squeeze bottles
        x = 0.48 + 0.08 * k
        lathe(b, [(0.0, 0.0), (0.03, 0.0), (0.032, 0.02), (0.032, 0.15), (0.025, 0.17), (0.012, 0.18), (0.0, 0.18)], key, 20, loc=(x, -0.25, 1.02))
        lathe(b, [(0.0, 0.0), (0.008, 0.0), (0.003, 0.05), (0.0, 0.05)], key, 10, loc=(x, -0.25, 1.20))
    box(b, (0.62, 0.10, 1.02), (0.80, 0.22, 1.13), "chrome", ch=0.006)                      # napkin box
    box(b, (0.64, 0.10, 1.12), (0.78, 0.22, 1.14), "pWhite", ch=0.0)
    for x in (-0.82, 0.0, 0.82):                                                          # sneeze guard along -Y
        rod(b, (x, -0.42, 1.02), (x, -0.42, 1.32), 0.009, "chrome")
    box(b, (-0.84, -0.425, 1.06), (0.84, -0.419, 1.32), "glass", ch=0.0)
    box(b, (-0.84, -0.43, 1.32), (0.84, -0.41, 1.335), "chrome")
    rod(b, (0.0, 0.0, 1.02), (0.0, 0.0, 2.21), 0.019, "galv", n=12)                         # umbrella pole
    lathe(b, [(0.0, 0.0), (0.04, 0.0), (0.04, 0.05), (0.0, 0.05)], "galv", 16, loc=(0, 0, 1.02))
    lathe(b, [(0.0, 0.0), (0.03, 0.0), (0.075, -0.06), (0.0, -0.06)], "black", 20, loc=(0.12, 0.0, 1.80))   # work lamp
    lathe(b, [(0.0, 0.0), (0.07, 0.0), (0.0, 0.004)], "lens", 20, loc=(0.12, 0.0, 1.739))
    rod(b, (0.0, 0.0, 1.80), (0.12, 0.0, 1.80), 0.006, "dark")
    umbrella(b, M, (0.0, 0.0), 1.08, 0.66, 1.90, 2.23)
    return done(ctx, b, "SM_Street_FoodCart", M, "Catalogue street_food_cart: brushed stainless hot-dog cart, body 1.70 x 0.86 x "
                "0.72 on two 0.40 wheels, tow bar to a hitch and jockey leg at +X, worktop at 1.0 with steam pan (lid ajar), "
                "griddle, red / yellow / brown squeeze bottles, napkin box, glass sneeze guard along -Y, menu boards 1.5 x 0.52 "
                "on both long sides (M_Sign_FoodCartMenu), eight-panel red and yellow umbrella 2.16 x 1.32 at rim 1.90, apex "
                "2.23, with ribs, stretchers and a work lamp under it (MI_Lamp_Lens). Place two SM_Gameplay_PropaneTank or "
                "SM_Prop_PropaneTank_Scan beside it.", (2.39, 1.32, 2.24), cover=1.25)


def sign_post(ctx, M):
    b = B(231)
    sign_slot(M, "SignPost", 0.32, 0.44)
    sign_slot(M, "StreetBlade", 0.60, 0.17)
    prof = [(-0.025, 0.0), (0.025, 0.0), (0.025, 0.012), (0.018, 0.012), (0.012, 0.022), (-0.012, 0.022), (-0.018, 0.012), (-0.025, 0.012)]
    b.prism(prof, (0, 0.006, 0), X, -Y, (0, 0, 2.62), "galv", pstep=0.02)
    for zz in np.arange(0.3, 2.6, 0.0254 * 1.0):                                         # punched holes, 1 in. pitch
        box(b, (-0.0045, -0.0165, zz), (0.0045, -0.0155, zz + 0.009), "black", ch=0.0)
    box(b, (-0.16, -0.019, 2.08), (0.16, -0.016, 2.52), "galv", ch=0.0)
    card(b, (-0.16, -0.0195, 2.08), (0.32, 0, 0), (0, 0, 0.44), "signSignPost", sign=True)
    for zz in (2.14, 2.46):
        lathe(b, [(0.0, 0.0), (0.009, 0.0), (0.009, 0.004), (0.0, 0.006)], "galv", 8, loc=(0, -0.0195, zz), rot=(90, 0, 0))
    box(b, (-0.03, -0.03, 2.58), (0.03, 0.03, 2.64), "galv", ch=0.004)                     # blade bracket cap
    box(b, (-0.30, -0.002, 2.63), (0.30, 0.002, 2.80), "galv", ch=0.0)                      # aluminium blade
    card(b, (-0.30, -0.0025, 2.63), (0.60, 0, 0), (0, 0, 0.17), "signStreetBlade", sign=True)
    card(b, (0.30, 0.0025, 2.63), (-0.60, 0, 0), (0, 0, 0.17), "signStreetBlade", sign=True)
    for s in (-1, 1):
        box(b, (-0.02, s * 0.002, 2.63), (0.02, s * 0.012, 2.80), "galv", ch=0.002)
    return done(ctx, b, "SM_Street_SignPost", M, "Catalogue street_sign_post: steel channel post with punched holes, NO PARKING "
                "ANYTIME plate 0.32 x 0.44 facing -Y (M_Sign_SignPost; BUS STOP / ONE WAY / STOP faces are texture swaps), "
                "green street-name blade 0.60 x 0.17 lettered on both faces at the top (M_Sign_StreetBlade, JAMAICA AV).",
                (0.6, None, 2.8), collision="box", ctr=False)


# =============================================================================================== yard and garage

def generator(ctx, M):
    b = B(240)
    sign_slot(M, "GenLabel", 0.62, 0.32)
    for s in (-1, 1):                                                                    # skids: channels with fork pockets
        b.prism(steel.channel(0.16, 0.06, 0.008, 0.006), (-1.10, s * 0.38, 0.0), Y * -s, Z, (2.20, 0, 0), "dark", pstep=0.04)
    for x in (-0.6, 0.6):
        box(b, (x - 0.12, -0.44, 0.03), (x + 0.12, 0.44, 0.13), "dark", ch=0.004)
    box(b, (-1.02, -0.47, 0.16), (1.02, 0.47, 1.22), "yellow", ch=0.02)                    # enclosure 2.04 x 0.94 x 1.06
    box(b, (-1.03, -0.48, 1.20), (1.03, 0.48, 1.23), "yellow", ch=0.008)                   # roof drip edge
    for s in (-1, 1):                                                                     # flanks: doors, louvres, labels
        y = s * 0.47
        for x0, x1 in ((-0.95, -0.42), (-0.38, 0.15)):
            for e in ((x0, x0 + 0.006), (x1 - 0.006, x1)):
                box(b, (e[0], y - 0.002, 0.22), (e[1], y + 0.002, 1.15), "black", ch=0.0)
            for zz in (0.22, 1.144):
                box(b, (x0, y - 0.002, zz), (x1, y + 0.002, zz + 0.006), "black", ch=0.0)
            box(b, (x1 - 0.09, y - s * 0.004, 0.66), (x1 - 0.03, y + s * 0.006, 0.72), "black", ch=0.004)   # recessed handle
            box(b, (x1 - 0.085, y + s * 0.006, 0.675), (x1 - 0.035, y + s * 0.012, 0.705), "chrome", ch=0.002)
        for k in range(10):                                                              # flank louvres near +X
            z = 0.32 + k * 0.08
            p0, p1 = (0.30, y + s * 0.01, z), (0.95, y + s * 0.01, z)
            bar(b, p0, p1, 0.05, 0.004, "yellow", up=steel.unit(np.array([0, s * 1.0, -1.2])))
        box(b, (0.28, y - 0.003, 0.29), (0.97, y + 0.003, 1.12), "black", ch=0.0)
        if s < 0:
            card(b, (-0.31 - 0.36, y - 0.0035, 0.62), (0.62, 0, 0), (0, 0, 0.32), "signGenLabel", sign=True)
        else:
            card(b, (-0.31 + 0.26, y + 0.0035, 0.62), (-0.62, 0, 0), (0, 0, 0.32), "signGenLabel", sign=True)
    for k in range(11):                                                                  # radiator louvres on +X
        z = 0.28 + k * 0.08
        bar(b, (1.03, -0.40, z), (1.03, 0.40, z), 0.055, 0.004, "yellow", up=steel.unit(np.array([1.0, 0, -1.2])))
    box(b, (1.015, -0.42, 0.25), (1.025, 0.42, 1.15), "black", ch=0.0)
    box(b, (-1.03, -0.20, 0.70), (-1.02, 0.20, 1.02), "dark", ch=0.0)                       # gauge panel on -X
    for i, (yy, zz) in enumerate(((-0.12, 0.92), (0.0, 0.92), (0.12, 0.92), (-0.06, 0.80), (0.06, 0.80))):
        lathe(b, [(0.0, 0.0), (0.03, 0.0), (0.03, 0.01), (0.0, 0.012)], "chrome", 16, loc=(-1.03, yy, zz), rot=(0, -90, 0))
        lathe(b, [(0.0, 0.0), (0.025, 0.0), (0.0, 0.002)], "pWhite", 16, loc=(-1.041, yy, zz), rot=(0, -90, 0))
    box(b, (-1.06, 0.14, 0.74), (-1.03, 0.18, 0.78), "lensRed", ch=0.004)
    cyl(b, 0.05, 0.16, "dark", loc=(-0.62, 0.22, 1.30), seg=16)                             # exhaust stack + rain cap
    gbox(b, (0.12, 0.11, 0.006), "dark", loc=(-0.62, 0.22, 1.385), rot=(0, 14, 0), bevel=0.002)
    lathe(b, [(0.0, 0.0), (0.04, 0.0), (0.04, 0.03), (0.032, 0.05), (0.0, 0.05)], "dark", 16, loc=(0.70, -0.30, 1.23))   # filler cap
    gob(geo.torus(0.04, 0.012, 20, 8), b, "galv", loc=(0.0, 0.0, 1.27), rot=(90, 0, 0))     # lifting eye
    box(b, (-0.05, -0.012, 1.23), (0.05, 0.012, 1.25), "galv")
    return done(ctx, b, "SM_Prop_Generator", M, "Catalogue prop_generator: skid-mounted 60 kW set, yellow enclosure 2.04 x 0.94 x "
                "1.06 on two channel skids with fork pockets, radiator louvres on +X and both flanks, two access doors per flank "
                "with recessed handles, gauge panel on -X, exhaust stack with rain cap, lifting eye, filler cap, DANGER / HIGH "
                "VOLTAGE / 60 kW 480 V labels on both flanks (M_Sign_GenLabel).", (2.2, 1.0, 1.39), cover=1.22)


def floodlight(ctx, M):
    b = B(241)
    hub = np.array([0.0, 0.0, 0.62])
    for k in range(3):                                                                   # tripod
        a = math.radians(-90 + 120 * k)
        foot = np.array([0.525 * math.cos(a), 0.525 * math.sin(a), 0.02])
        rod(b, hub, foot, 0.014, "dark", n=8)
        lathe(b, [(0.0, 0.0), (0.025, 0.0), (0.025, 0.02), (0.0, 0.025)], "rubber", 10, loc=(foot[0], foot[1], 0.0))
        rod(b, (0.0, 0.0, 0.40), hub + (foot - hub) * 0.55, 0.008, "dark", n=6)
    cyl(b, 0.026, 0.06, "dark", loc=(0, 0, 0.40), seg=12)
    rod(b, (0, 0, 0.30), (0, 0, 1.25), 0.022, "galv", n=12)                              # telescopic mast
    cyl(b, 0.03, 0.06, "dark", loc=(0, 0, 1.23), seg=12)
    rod(b, (0, 0, 1.23), (0.06, 0, 1.23), 0.006, "dark")
    gbox(b, (0.02, 0.03, 0.03), "dark", loc=(0.07, 0, 1.23))
    rod(b, (0, 0, 1.2), (0, 0, 2.0), 0.016, "galv", n=12)
    rod(b, (-0.42, 0, 2.0), (0.42, 0, 2.0), 0.014, "dark", n=10)                            # cross bar 0.84
    for s in (-1, 1):                                                                     # two halogen heads, -Y, 18 deg down
        hb = B(242 + s)
        box(hb, (-0.17, -0.05, -0.125), (0.17, 0.05, 0.125), "yellow", ch=0.012)
        box(hb, (-0.15, -0.0515, -0.105), (0.15, -0.05, 0.105), "lensFlood", ch=0.0)
        for zz in (-0.06, 0.0, 0.06):
            rod(hb, (-0.15, -0.056, zz), (0.15, -0.056, zz), 0.002, "chrome", n=6)
        for xx in np.linspace(-0.12, 0.12, 9):                                           # cooling fins on the back
            box(hb, (xx - 0.004, 0.05, -0.11), (xx + 0.004, 0.075, 0.11), "yellow", ch=0.0)
        for sx in (-1, 1):
            rod(hb, (sx * 0.18, 0.0, 0.0), (sx * 0.18, 0.0, -0.14), 0.006, "dark")
        rod(hb, (-0.18, 0.0, -0.14), (0.18, 0.0, -0.14), 0.006, "dark")
        ob = None
        Mx = np.eye(4)
        r = math.radians(18)
        Rx = np.array([[1, 0, 0], [0, math.cos(r), -math.sin(r)], [0, math.sin(r), math.cos(r)]])
        Mx[:3, :3] = Rx
        Mx[:3, 3] = (s * 0.24, -0.03, 2.0 + 0.14 * math.cos(r))
        b.merge(hb, Mx)
    pts = [(0.24, 0.06, 2.0), (0.10, 0.03, 1.95), (0.02, 0.03, 1.6), (0.03, 0.03, 0.9), (0.05, 0.04, 0.5), (0.12, 0.10, 0.15),
           (0.20, 0.25, 0.012), (0.12, 0.36, 0.012), (0.02, 0.40, 0.012)]
    pipe(b, pts, 0.007, "rubber", bend=0.05, seg=8)
    return done(ctx, b, "SM_Prop_FloodlightStand", M, "Catalogue prop_floodlight_stand: tripod legs to r 0.47 with braces, "
                "telescopic mast to 2.0 with a clamp, cross bar 0.84, two yellow halogen flood heads 0.34 x 0.25 x 0.10 aimed "
                "-Y and 18 deg down (lenses MI_Lamp_Flood: emissive #fff1d0 when lit; spot lights in engine), wire guards, "
                "cooling fins, trailing cable.", (0.96, 0.94, 2.17), collision="convex", cover=2.15, ao=None)


def porta_potty(ctx, M):
    b = B(243)
    sign_slot(M, "PortaPlate", 0.30, 0.22)
    box(b, (-0.60, -0.60, 0.0), (0.60, 0.60, 0.10), "cabin", ch=0.02)                      # base 1.2
    box(b, (-0.56, -0.56, 0.10), (0.56, 0.56, 2.06), "cabin", ch=0.03)                     # cabin 1.12 x 1.96
    for s in (-1, 1):                                                                     # moulded ribs on the sides and back
        for t in (-0.32, -0.12, 0.12, 0.32):
            box(b, (s * 0.56 - 0.012, t - 0.025, 0.2), (s * 0.56 + 0.012, t + 0.025, 1.95), "cabin", ch=0.008)
            if s > 0:
                box(b, (t - 0.025, 0.548, 0.2), (t + 0.025, 0.572, 1.95), "cabin", ch=0.008)
        for k in range(6):                                                               # vent slots high on the sides
            z = 1.78 + k * 0.035
            box(b, (s * 0.561 - 0.003, -0.20, z), (s * 0.561 + 0.003, 0.20, z + 0.015), "black", ch=0.0)
    roof = geo.box((1.18, 1.18, 0.23), bevel=0.10, segments=4)
    co, _ = geo.arrays(roof)
    co[:, 2] += 0.05 * np.clip(1 - (co[:, 0] ** 2 + co[:, 1] ** 2) / 0.7, 0, 1) * (co[:, 2] > 0.1)
    geo.set_verts(roof, co)
    gob(roof, b, "pWhite", loc=(0, 0, 2.04))                                             # translucent roof cap
    box(b, (-0.38, -0.575, 0.14), (0.38, -0.56, 1.98), "cabin", ch=0.01)                  # door frame
    box(b, (-0.36, -0.59, 0.16), (0.36, -0.575, 1.96), "cabin", ch=0.012)                 # door
    for z in (0.5, 1.0, 1.5):
        box(b, (-0.30, -0.598, z), (0.30, -0.59, z + 0.05), "cabin", ch=0.006)
    for z in (0.40, 1.70):                                                                # hinges on -X
        box(b, (-0.39, -0.60, z), (-0.35, -0.57, z + 0.12), "dark", ch=0.004)
    box(b, (0.24, -0.605, 1.02), (0.32, -0.59, 1.12), "dark", ch=0.006)                    # latch with vacant dot
    lathe(b, [(0.0, 0.0), (0.012, 0.0), (0.012, 0.004), (0.0, 0.005)], "latch", 16, loc=(0.28, -0.605, 1.09), rot=(90, 0, 0))
    gbox(b, (0.10, 0.03, 0.025), "dark", loc=(0.28, -0.615, 0.98), bevel=0.008)            # pull handle
    card(b, (-0.15, -0.5985, 1.58), (0.30, 0, 0), (0, 0, 0.22), "signPortaPlate", sign=True)
    cyl(b, 0.05, 0.42, "pBlack", loc=(0.42, 0.42, 2.06), seg=16)                          # vent stack
    lathe(b, [(0.0, 0.0), (0.07, 0.0), (0.075, 0.02), (0.0, 0.05)], "pBlack", 16, loc=(0.42, 0.42, 2.27))
    return done(ctx, b, "SM_Prop_PortaPotty", M, "Catalogue prop_porta_potty: moulded grey PE cabin 1.12 x 1.96 on a 1.2 base "
                "with ribs and vent slots, translucent white roof cap to 2.29 (MI_Plastic_White: translucent in engine), door on "
                "-Y with hinges, pull and latch with a green vacant dot (MI_Plastic_LatchGreen), hire plate HOLLIS / SITE "
                "SERVICES / UNIT 14 (M_Sign_PortaPlate), vent stack.", (1.2, 1.21, 2.29), cover=2.25)


def vending(ctx, M):
    b = B(244)
    sign_slot(M, "Vending", 0.60, 1.20)
    for (x, y) in ((-0.40, -0.33), (0.40, -0.33), (-0.40, 0.33), (0.40, 0.33)):
        lathe(b, [(0.0, 0.0), (0.025, 0.0), (0.025, 0.02), (0.0, 0.02)], "dark", 10, loc=(x, y, 0.0))
    box(b, (-0.45, -0.36, 0.02), (0.45, 0.40, 1.84), "black", ch=0.01)                     # cabinet
    box(b, (-0.43, -0.38, 0.52), (0.25, -0.36, 1.80), "black", ch=0.006)                    # face frame
    card(b, (-0.39, -0.3815, 0.56), (0.60, 0, 0), (0, 0, 1.20), "signVending", sign=True)
    box(b, (-0.40, -0.388, 0.55), (0.22, -0.383, 1.77), "glass", ch=0.0)
    box(b, (0.27, -0.375, 1.15), (0.42, -0.36, 1.72), "dark", ch=0.006)                      # selection column
    for k in range(6):
        z = 1.66 - k * 0.09
        box(b, (0.29, -0.385, z - 0.03), (0.40, -0.375, z + 0.03), "chrome", ch=0.004)
        box(b, (0.30, -0.388, z - 0.022), (0.39, -0.385, z + 0.022), "lens", ch=0.0)
    box(b, (0.29, -0.38, 0.98), (0.40, -0.36, 1.12), "chrome", ch=0.006)                     # coin plate
    box(b, (0.33, -0.3815, 1.07), (0.36, -0.38, 1.10), "black", ch=0.0)
    box(b, (0.30, -0.39, 1.0), (0.39, -0.38, 1.03), "chrome", ch=0.003)                     # coin return lever
    box(b, (0.30, -0.3815, 0.80), (0.39, -0.38, 0.92), "black", ch=0.0)                     # bill slot window
    box(b, (0.31, -0.383, 0.84), (0.38, -0.3815, 0.86), "lensGreen", ch=0.0)
    box(b, (-0.38, -0.38, 0.10), (0.22, -0.36, 0.42), "dark", ch=0.008)                     # delivery bin
    flap = geo.box((0.52, 0.012, 0.20), bevel=0.004)
    gob(flap, b, "pBlack", loc=(-0.08, -0.386, 0.14), rot=(-8, 0, 0))
    box(b, (-0.43, -0.37, 0.04), (0.43, -0.36, 0.08), "chrome", ch=0.002)                   # kick plate
    gbox(b, (0.04, 0.03, 0.16), "chrome", loc=(0.43, -0.39, 1.28))                         # door handle / lock
    lathe(b, [(0.0, 0.0), (0.014, 0.0), (0.014, 0.01), (0.0, 0.011)], "chrome", 12, loc=(0.43, -0.405, 1.40), rot=(90, 0, 0))
    return done(ctx, b, "SM_Prop_VendingMachine", M, "Catalogue prop_vending_machine (brandless): black cabinet 0.90 x 0.76 x 1.84 "
                "on levelling feet, back-lit face 0.60 x 1.20 behind glass (M_Sign_Vending: ICE COLD SODA, $1.00, bubbles on a "
                "blue-to-cyan field; E map), six selection buttons with lit inserts (MI_Lamp_Lens), coin plate and return, "
                "bill acceptor, delivery bin flap, lock.", (0.9, 0.8, 1.85), cover=1.85)


def workbench(ctx, M):
    b = B(245)
    for y0 in (-0.39, -0.30, -0.20, -0.10, 0.0, 0.10, 0.20, 0.30):                       # laminated timber top at 0.80
        board(b, (-1.10, y0, 0.745), (1.10, min(y0 + 0.098, 0.39), 0.80), "plank", ch=0.003)
    for (x, y) in ((-1.05, -0.34), (1.05, -0.34), (-1.05, 0.34), (1.05, 0.34)):           # angle-iron legs
        sx, sy = np.sign(x), np.sign(y)
        b.prism(steel.angle(0.05, 0.05, 0.005), (x + sx * 0.025, y + sy * 0.025, 0.0), -sx * X, -sy * Y, (0, 0, 0.745), "dark", pstep=0.04)
        box(b, (x - 0.03, y - 0.03, 0.0), (x + 0.03, y + 0.03, 0.006), "dark")
    for z in (0.70, 0.13):
        for s in (-1, 1):
            box(b, (-1.075, s * 0.365 - 0.004, z), (1.075, s * 0.365 + 0.004, z + 0.04), "dark", ch=0.0015)
            box(b, (s * 1.075 - 0.004, -0.36, z), (s * 1.075 + 0.004, 0.36, z + 0.04), "dark", ch=0.0015)
    box(b, (-1.07, -0.36, 0.17), (1.07, 0.36, 0.188), "ply", ch=0.002)                     # plywood shelf
    # on the shelf: red toolbox, carton, can
    box(b, (-0.85, -0.18, 0.188), (-0.35, 0.10, 0.40), "red", ch=0.008)
    box(b, (-0.86, -0.19, 0.39), (-0.34, 0.11, 0.41), "red", ch=0.006)
    rod(b, (-0.70, -0.04, 0.44), (-0.50, -0.04, 0.44), 0.008, "pBlack")
    for x in (-0.70, -0.50):
        rod(b, (x, -0.04, 0.41), (x, -0.04, 0.44), 0.006, "galv")
    box(b, (-0.15, -0.20, 0.188), (0.30, 0.15, 0.48), "card", ch=0.004)
    box(b, (-0.15, -0.03, 0.48), (0.30, 0.02, 0.482), "tape", ch=0.0)
    lathe(b, [(0.0, 0.0), (0.075, 0.0), (0.078, 0.01), (0.078, 0.18), (0.07, 0.19), (0.0, 0.19)], "red", 24, loc=(0.6, 0.0, 0.188))
    # on the top: vise at the front corner, carburettor on a rag, socket tray, coffee cup
    vx = 0.88
    box(b, (vx - 0.09, -0.36, 0.80), (vx + 0.09, -0.16, 0.83), "blue", ch=0.006)          # vise base
    box(b, (vx - 0.06, -0.38, 0.83), (vx + 0.06, -0.18, 0.92), "blue", ch=0.01)            # body
    box(b, (vx - 0.075, -0.39, 0.90), (vx + 0.075, -0.37, 0.955), "blue", ch=0.006)        # front jaw
    box(b, (vx - 0.075, -0.33, 0.90), (vx + 0.075, -0.31, 0.955), "blue", ch=0.006)
    for y in (-0.37, -0.33):
        box(b, (vx - 0.07, y - 0.004 if y > -0.35 else y, 0.915), (vx + 0.07, y + 0.004 if y > -0.35 else y + 0.004, 0.952), "dark")
    rod(b, (vx, -0.39, 0.87), (vx, -0.47, 0.87), 0.01, "galv")
    rod(b, (vx - 0.09, -0.47, 0.87), (vx + 0.09, -0.47, 0.87), 0.006, "galv")
    F.blob(b, (0.40, 0.32, 0.02), (-0.2, -0.05, 0.80), "burlap", 7, lumps=0.006)              # rag
    box(b, (-0.29, -0.12, 0.81), (-0.11, 0.02, 0.89), "galv", ch=0.01)                    # carburettor body
    cyl(b, 0.035, 0.05, "galv", loc=(-0.20, -0.05, 0.92), seg=20)
    lathe(b, [(0.0, 0.0), (0.06, 0.0), (0.06, 0.01), (0.0, 0.01)], "galv", 24, loc=(-0.20, -0.05, 0.945))
    rod(b, (-0.29, -0.05, 0.86), (-0.33, -0.05, 0.86), 0.006, "galv")
    box(b, (0.20, -0.10, 0.80), (0.50, 0.10, 0.83), "red", ch=0.003)                       # socket tray
    for i in range(10):
        x = 0.22 + 0.028 * i
        lathe(b, [(0.0, 0.0), (0.009 + 0.0007 * i, 0.0), (0.009 + 0.0007 * i, 0.035), (0.0, 0.035)], "chrome", 12, loc=(x, -0.05, 0.83))
    lathe(b, [(0.0, 0.0), (0.03, 0.0), (0.042, 0.11), (0.044, 0.112), (0.0, 0.112)], "pWhite", 20, loc=(-0.65, 0.20, 0.80))
    lathe(b, [(0.0, 0.0), (0.041, 0.0), (0.041, 0.006), (0.0, 0.008)], "pBlack", 20, loc=(-0.65, 0.20, 0.905))
    return done(ctx, b, "SM_Prop_Workbench", M, "Catalogue prop_workbench: 2.2 x 0.78, laminated timber top 55 mm thick at 0.80 "
                "on angle-iron legs and rails, plywood shelf; red toolbox, carton and a can on the shelf; blue bench vise on the "
                "front corner, carburettor on a rag, a tray of sockets and a coffee cup on top.", (2.2, None, 0.96), cover=0.80)


def v_engine(b, slot="dark", head="chrome", c=(0, 0, 0)):
    """Small-block V8 0.52 x 0.40 x 0.34 hanging by its lifting chain, crank along X."""
    cx, cy, cz = c
    box(b, (cx - 0.26, cy - 0.13, cz + 0.06), (cx + 0.24, cy + 0.13, cz + 0.22), slot, ch=0.01)           # crankcase
    box(b, (cx - 0.22, cy - 0.10, cz), (cx + 0.20, cy + 0.10, cz + 0.07), "black", ch=0.012)              # oil pan
    for s in (-1, 1):
        hb = geo.box((0.46, 0.12, 0.10), bevel=0.008)
        gob(hb, b, slot, loc=(cx - 0.02, cy + s * 0.12, cz + 0.20), rot=(-s * 45, 0, 0))                 # heads
        vc = geo.box((0.44, 0.09, 0.05), bevel=0.012)
        gob(vc, b, head, loc=(cx - 0.02, cy + s * 0.17, cz + 0.27), rot=(-s * 45, 0, 0))                 # valve covers
    box(b, (cx - 0.20, cy - 0.08, cz + 0.24), (cx + 0.16, cy + 0.08, cz + 0.30), slot, ch=0.01)          # intake manifold
    lathe(b, [(0.0, 0.0), (0.05, 0.0), (0.05, 0.04), (0.0, 0.04)], slot, 20, loc=(cx - 0.02, cy, cz + 0.30))
    for r, x in ((0.08, 0.26), (0.05, 0.29)):                                                          # pulleys, flywheel
        lathe(b, [(0.0, 0.0), (r, 0.0), (r, 0.02), (0.0, 0.02)], "galv", 24, loc=(cx + x, cy, cz + 0.12), rot=(0, 90, 0))
    lathe(b, [(0.0, 0.0), (0.14, 0.0), (0.14, 0.025), (0.0, 0.025)], "dark", 32, loc=(cx - 0.29, cy, cz + 0.14), rot=(0, 90, 0))


def engine_hoist(ctx, M, variant):
    b = B(246 + variant)
    frame = ("red", "blue")[variant]
    mx = -0.50
    for s in (-1, 1):                                                                    # splayed legs on castors
        p0, p1 = (mx, s * 0.12, 0.10), (0.70, s * 0.50, 0.10)
        bar(b, p0, p1, 0.07, 0.07, frame, ch=0.004)
        lathe(b, [(0.0, -0.02), (0.05, -0.02), (0.05, 0.02), (0.0, 0.02)], "rubber", 16, loc=(0.70, s * 0.50, 0.05), rot=(90, 0, 0))
        box(b, (0.67, s * 0.50 - 0.03, 0.06), (0.73, s * 0.50 + 0.03, 0.065), "galv")
    bar(b, (mx - 0.04, -0.30, 0.10), (mx - 0.04, 0.30, 0.10), 0.07, 0.07, frame, ch=0.004)      # back cross member
    for s in (-1, 1):
        lathe(b, [(0.0, -0.02), (0.05, -0.02), (0.05, 0.02), (0.0, 0.02)], "rubber", 16, loc=(mx - 0.04, s * 0.30, 0.05), rot=(90, 0, 0))
    box(b, (mx - 0.045, -0.045, 0.10), (mx + 0.045, 0.045, 1.52), frame, ch=0.004)           # mast 1.5
    for s in (-1, 1):
        b.poly_plate([(mx + 0.045, s * 0.045, 0.14), (mx + 0.30, s * 0.045, 0.14), (mx + 0.045, s * 0.045, 0.40)][::(1 if s < 0 else -1)],
                     0.006, frame)                                                            # gussets
    tip = np.array([0.58, 0.0, 1.88])
    piv = np.array([mx, 0.0, 1.47])
    bar(b, piv, tip, 0.075, 0.075, frame, ch=0.004)                                         # boom to the tip
    for s in (-1, 1):
        box(b, (mx - 0.05, s * 0.046, 1.40), (mx + 0.05, s * 0.052, 1.55), frame)
    ram0, ram1 = np.array([mx + 0.06, 0.0, 0.55]), piv + (tip - piv) * 0.42 - np.array([0, 0, 0.05])
    rod(b, ram0, ram0 + (ram1 - ram0) * 0.6, 0.035, "dark", n=14)                             # hydraulic ram
    rod(b, ram0 + (ram1 - ram0) * 0.55, ram1, 0.018, "chrome", n=12)
    rod(b, ram0 + np.array([0.0, 0.0, 0.08]), ram0 + np.array([-0.10, 0.0, 0.62]), 0.011, "dark", n=8)    # pump handle
    lathe(b, [(0.0, 0.0), (0.016, 0.0), (0.016, 0.10), (0.0, 0.10)], "pBlack", 12, loc=ram0 + np.array([-0.10, 0.0, 0.58]))
    hook = tip - np.array([0.0, 0.0, 0.04])
    gob(geo.torus(0.025, 0.007, 16, 8), b, "galv", loc=hook - np.array([0, 0, 0.03]), rot=(90, 0, 0))
    b.absorb(geo.chain([tuple(hook - np.array([0, 0, 0.06])), (0.58, 0.0, 1.50)], link_len=0.035, wire=0.006), "galv")
    for s in (-1, 1):                                                                    # spreader chains to the block
        b.absorb(geo.chain([(0.58, 0.0, 1.50), (0.58 + s * 0.20, s * 0.05, 1.38)], link_len=0.03, wire=0.005), "galv")
    v_engine(b, "dark", "chrome", (0.60, 0.0, 1.04))
    return done(ctx, b, "SM_Prop_EngineHoist" + ("_Blue" if variant else ""), M, "Catalogue prop_engine_hoist (%s frame): folding "
                "engine crane, splayed legs on castors, mast 1.5, boom to a tip at 1.92, hydraulic ram with pump handle, hook and "
                "chain, a V8 block 0.52 x 0.40 x 0.34 hanging at 1.08 (block 1.04 to 1.38)." % ("blue #1f4f9a" if variant else "red #b3261e"),
                (1.47, None, 1.96), collision="convex", cover=1.60, ao=None)


def compressor(ctx, M, variant):
    b = B(248 + variant)
    paint_ = ("blue", "black")[variant]
    prof = [(0.0, 0.0)] + [(0.20 * math.sin(t), 0.06 * (1 - math.cos(t))) for t in np.linspace(0.2, math.pi / 2, 5)] + \
           [(0.20, 0.80)] + [(0.20 * math.cos(t), 0.80 + 0.06 * math.sin(t)) for t in np.linspace(0.2, math.pi / 2 - 0.15, 5)] + [(0.0, 0.86)]
    lathe(b, prof, paint_, 40, loc=(-0.43, 0.0, 0.30), rot=(0, 90, 0))                      # tank 0.92 x 0.40
    for s in (-1, 1):                                                                     # wheels 0.24 and the foot
        lathe(b, [(0.05, -0.025), (0.10, -0.03), (0.12, -0.015), (0.12, 0.015), (0.10, 0.03), (0.05, 0.025)], "rubber", 24,
              closed=True, loc=(-0.30, s * 0.235, 0.12), rot=(90, 0, 0))
        lathe(b, [(0.0, -0.022), (0.055, -0.022), (0.055, 0.022), (0.0, 0.022)], "galv", 16, loc=(-0.30, s * 0.235, 0.12), rot=(90, 0, 0))
        bar(b, (-0.30, s * 0.20, 0.12), (-0.22, s * 0.12, 0.20), 0.03, 0.006, paint_)
    rod(b, (-0.30, -0.25, 0.12), (-0.30, 0.25, 0.12), 0.01, "galv")
    bar(b, (0.33, 0.0, 0.12), (0.33, 0.0, 0.0), 0.06, 0.06, paint_)
    box(b, (0.29, -0.06, 0.0), (0.37, 0.06, 0.02), "rubber", ch=0.004)
    box(b, (-0.30, -0.14, 0.49), (0.32, 0.14, 0.51), paint_, ch=0.004)                      # saddle plate
    cyl(b, 0.09, 0.26, paint_, loc=(0.16, 0.04, 0.60), rot=(0, 90, 0), seg=24, bevel=0.01)   # motor
    for k in range(8):
        cyl(b, 0.093, 0.006, paint_, loc=(0.06 + k * 0.025, 0.04, 0.60), rot=(0, 90, 0), seg=24)
    lathe(b, [(0.0, 0.0), (0.06, 0.0)] + sum([[(0.08, 0.04 + 0.02 * k), (0.08, 0.05 + 0.02 * k), (0.06, 0.052 + 0.02 * k), (0.06, 0.058 + 0.02 * k)]
                                              for k in range(10)], []) + [(0.05, 0.30), (0.0, 0.30)], "dark", 24, loc=(-0.12, 0.04, 0.51))   # finned pump
    box(b, (-0.20, -0.04, 0.80), (-0.04, 0.12, 0.84), "dark", ch=0.006)                     # head
    box(b, (-0.20, -0.14, 0.52), (0.28, -0.08, 0.76), paint_, ch=0.03)                      # belt guard
    for k in range(6):
        box(b, (-0.12 + 0.06 * k, -0.142, 0.58), (-0.10 + 0.06 * k, -0.138, 0.70), "black", ch=0.0)
    rod(b, (-0.12, 0.10, 0.82), (-0.12, 0.20, 0.82), 0.008, "galv")                         # manifold, gauge, valve
    lathe(b, [(0.0, 0.0), (0.035, 0.0), (0.035, 0.02), (0.0, 0.022)], "chrome", 20, loc=(-0.12, 0.20, 0.82), rot=(-90, 0, 0))
    lathe(b, [(0.0, 0.0), (0.03, 0.0), (0.0, 0.002)], "pWhite", 20, loc=(-0.12, 0.221, 0.82), rot=(-90, 0, 0))
    pipe(b, [(-0.50, -0.15, 0.30), (-0.58, -0.15, 0.40), (-0.58, -0.15, 0.80), (-0.58, 0.15, 0.80), (-0.58, 0.15, 0.40), (-0.50, 0.15, 0.30)],
         0.013, "galv", bend=0.05)                                                           # tow handle
    rod(b, (-0.58, -0.08, 0.80), (-0.58, 0.08, 0.80), 0.017, "pBlack")
    for k in range(5):                                                                    # coiled yellow hose on the handle
        a = k * 0.03
        gob(geo.torus(0.13 + 0.004 * k, 0.007, 40, 8), b, "hose", loc=(-0.595 - 0.01 * k, 0.0, 0.66 - a * 0.2), rot=(0, 90 + 4 * k, 0))
    return done(ctx, b, "SM_Prop_Compressor" + ("_Black" if variant else ""), M, "Catalogue prop_compressor (%s tank): horizontal "
                "tank 0.92 x 0.40 on two 0.24 wheels and a rubber foot, finned pump and motor on a saddle under a slotted belt "
                "guard, pressure gauge, tow handle with a coiled yellow air hose." % ("black" if variant else "blue"),
                (1.11, 0.54, 0.87), collision="box", cover=0.90, ao=None)


def car_lift(ctx, M):
    b = B(250)
    for s in (-1, 1):
        yc = s * 1.40
        box(b, (-0.25, yc - 0.18, 0.0), (0.25, yc + 0.18, 0.02), "blue", ch=0.004)        # base plate
        for (x, y) in ((-0.20, yc - 0.13), (0.20, yc - 0.13), (-0.20, yc + 0.13), (0.20, yc + 0.13)):
            lathe(b, [(0.0, 0.0), (0.012, 0.0), (0.012, 0.025), (0.0, 0.027)], "galv", 6, loc=(x, y, 0.02))
        yo = yc + s * 0.13                                                                # column: C-section open toward the bay
        box(b, (-0.15, yo - s * 0.008, 0.02), (0.15, yo, 3.46), "blue", ch=0.003)
        for sx in (-1, 1):
            box(b, (sx * 0.15 - (0.008 if sx > 0 else 0), yc - 0.13, 0.02), (sx * 0.15 + (0.0 if sx > 0 else 0.008), yc + 0.13, 3.46), "blue", ch=0.003)
            box(b, (sx * 0.15 - sx * 0.10 - 0.004, yc - s * 0.13, 0.02), (sx * 0.15 - sx * 0.10 + 0.004, yc - s * 0.13 + s * 0.02, 3.46), "blue")
            box(b, (sx * 0.08 - 0.03, yc - s * 0.13 - 0.004, 0.02), (sx * 0.08 + 0.03, yc - s * 0.13 + 0.004, 3.46), "blue")
        for z in np.arange(0.4, 2.4, 0.05):                                               # safety-lock ladder inside
            box(b, (-0.03, yc - 0.01, z), (0.03, yc + 0.01, z + 0.012), "galv", ch=0.0)
        box(b, (-0.16, yc - 0.14, 3.40), (0.16, yc + 0.14, 3.46), "blue", ch=0.004)        # column cap
    box(b, (-0.08, -1.56, 3.46), (0.08, 1.56, 3.58), "blue", ch=0.006)                      # overhead beam
    box(b, (-0.10, -0.25, 3.40), (0.10, 0.25, 3.46), "dark", ch=0.004)                      # shut-off bar housing
    cyl(b, 0.075, 0.30, "dark", loc=(0.27, 1.40, 1.45), seg=24, bevel=0.008)                # power unit motor
    box(b, (0.20, 1.30, 1.10), (0.34, 1.50, 1.28), "dark", ch=0.01)                         # pump block
    lathe(b, [(0.0, 0.0), (0.07, 0.0), (0.07, 0.30), (0.05, 0.31), (0.0, 0.31)], "pWhite", 20, loc=(0.27, 1.40, 0.78))   # reservoir
    box(b, (0.15, 1.32, 1.05), (0.20, 1.48, 1.35), "dark", ch=0.004)
    pipe(b, [(0.27, 1.40, 1.10), (0.27, 1.30, 0.6), (0.10, 1.27, 0.3), (0.0, 1.20, 0.25)], 0.008, "rubber", bend=0.05)
    pipe(b, [(0.15, 1.40, 3.40), (0.12, 1.30, 3.50), (0.10, -1.30, 3.50), (0.12, -1.40, 3.40)], 0.008, "rubber", bend=0.05)
    lift = done(ctx, b, "SM_Prop_CarLift", M, "Catalogue prop_car_lift (frame): two-post lift, columns 0.30 x 0.26 x 3.46 (C-section "
                "open toward the bay, lock ladders inside) 2.8 apart along Y on base plates with anchors, overhead beam to 3.58, "
                "power unit (motor, pump, reservoir) on the +Y column, hoses. The carriages and swing arms are "
                "SM_Prop_CarLift_Arms in the same frame: identity = lowered (pad tops 0.16), +1.98 in Z = raised (pad tops 2.14). "
                "A car lies along X.", (None, 3.16, 3.58), collision="box", ao=None, ctr=False)
    a = B(251)
    for s in (-1, 1):
        yc = s * 1.40 - s * 0.20
        box(a, (-0.11, yc - 0.08, 0.05), (0.11, yc + 0.08, 0.70), "blue", ch=0.006)           # carriage
        for sx in (-1, 1):
            piv = np.array([sx * 0.08, yc - s * 0.04, 0.09])
            end = np.array([sx * 1.00, s * 0.78, 0.09])
            bar(a, piv, piv + (end - piv) * 0.55, 0.09, 0.07, "dark", ch=0.004)               # telescoping arm
            bar(a, piv + (end - piv) * 0.5, end, 0.07, 0.05, "dark", ch=0.004)
            lathe(a, [(0.0, 0.0), (0.03, 0.0), (0.03, 0.04), (0.0, 0.04)], "galv", 12, loc=(end[0], end[1], 0.09))
            lathe(a, [(0.0, 0.0), (0.065, 0.0), (0.065, 0.025), (0.0, 0.03)], "rubber", 20, loc=(end[0], end[1], 0.13))
            cyl(a, 0.03, 0.10, "galv", loc=tuple(piv + np.array([0, 0, 0.02])), seg=12)
    arms = done(ctx, a, "SM_Prop_CarLift_Arms", M, "Carriages and four swing arms of SM_Prop_CarLift, in the lift's frame: identity "
                "= lowered (rubber pad tops at 0.16), translate +1.98 in Z for the raised state (pad tops 2.14, a car's wheels at "
                "1.95).", (2.13, None, None), collision="none", ao=None, ctr=False)
    return [lift, arms]


def tool_chest(ctx, M):
    b = B(252)
    box(b, (-0.53, -0.25, 0.13), (0.53, 0.25, 0.75), "red", ch=0.008)                      # roller cabinet 1.06 x 0.50 x 0.62
    z = 0.15
    for h in (0.16, 0.13, 0.10, 0.08, 0.08):                                             # five drawers
        box(b, (-0.51, -0.258, z + 0.004), (0.51, -0.25, z + h - 0.004), "red", ch=0.003)
        box(b, (-0.45, -0.275, z + h - 0.03), (0.45, -0.258, z + h - 0.012), "galv", ch=0.003)
        z += h + 0.0
    for (x, y) in ((-0.46, -0.19), (0.46, -0.19), (-0.46, 0.19), (0.46, 0.19)):            # castors
        box(b, (x - 0.04, y - 0.04, 0.115), (x + 0.04, y + 0.04, 0.13), "galv")
        box(b, (x - 0.02, y - 0.03, 0.06), (x + 0.02, y + 0.03, 0.115), "galv")
        lathe(b, [(0.0, -0.016), (0.055, -0.016), (0.06, 0.0), (0.055, 0.016), (0.0, 0.016)], "rubber", 16, loc=(x, y, 0.06), rot=(90, 0, 0))
    pipe(b, [(0.53, -0.18, 0.65), (0.58, -0.18, 0.66), (0.58, 0.18, 0.66), (0.53, 0.18, 0.65)], 0.012, "galv", bend=0.025)   # side handle
    box(b, (-0.51, -0.23, 0.75), (0.51, 0.23, 1.02), "red", ch=0.008)                      # top chest 1.02 x 0.46 x 0.33
    box(b, (-0.515, -0.235, 1.02), (0.515, 0.235, 1.08), "red", ch=0.012)                   # lid
    z = 0.77
    for h in (0.07, 0.08, 0.10):
        box(b, (-0.49, -0.238, z + 0.003), (0.49, -0.23, z + h - 0.003), "red", ch=0.002)
        box(b, (-0.43, -0.25, z + h - 0.025), (0.43, -0.238, z + h - 0.01), "galv", ch=0.002)
        z += h
    for x in (-0.25, 0.25):
        box(b, (x - 0.06, -0.01, 1.08), (x + 0.06, 0.01, 1.09), "galv", ch=0.002)
    box(b, (0.42, -0.243, 1.03), (0.46, -0.235, 1.06), "chrome", ch=0.002)                  # lock
    return done(ctx, b, "SM_Prop_ToolChest", M, "Catalogue prop_tool_chest: red mechanic's roller cabinet 1.06 x 0.50 x 0.62 with "
                "five drawers on four castors and a top chest 1.02 x 0.46 x 0.33 with three drawers and a lid, full-width "
                "aluminium pulls, side handle, lock. Drawers face -Y.", (1.11, 0.54, 1.09), cover=1.09)


def crate_wood(ctx, M, variant):
    b = B(253 + variant)
    sign_slot(M, "CrateStencil", 0.66, 0.44)
    sign_slot(M, "VultureStencil", 0.5, 0.4)
    x0, x1, y0, y1, z0, z1 = -0.52, 0.52, -0.42, 0.42, 0.10, 1.0
    for s in (-1, 1):                                                                    # 4 x 4 skids
        board(b, (-0.55, s * 0.30 - 0.045, 0.0), (0.55, s * 0.30 + 0.045, 0.10), "plank", ch=0.006)
    box(b, (x0 + 0.02, y0 + 0.02, z0), (x1 - 0.02, y1 - 0.02, z1 - 0.02), "ply", ch=0.004)    # plywood box
    c, t = 0.09, 0.022
    for s in (-1, 1):                                                                     # cleats on the long faces with a diagonal brace
        y = y0 if s < 0 else y1
        o = -t if s < 0 else 0.0
        for zz in (z0, z1 - c):
            board(b, (x0, y + o, zz), (x1, y + o + t, zz + c), "plank")
        for xx in (x0, x1 - c):
            board(b, (xx, y + o, z0 + c), (xx + c, y + o + t, z1 - c), "plank")
        p0, p1 = np.array([x0 + c, y + o + t / 2, z0 + c]), np.array([x1 - c, y + o + t / 2, z1 - c])
        bar(b, p0 + (p1 - p0) * 0.02, p1 - (p1 - p0) * 0.02, c, t, "plank", up=Y)
    for s in (-1, 1):                                                                     # ends: frame only
        x = x0 - t if s < 0 else x1
        for zz in (z0, z1 - c):
            board(b, (x, y0, zz), (x + t, y1, zz + c), "plank")
        for yy in (y0, y1 - c):
            board(b, (x, yy, z0 + c), (x + t, yy + c, z1 - c), "plank")
    for xx in (x0 + 0.05, 0.0, x1 - 0.05):                                                 # lid battens
        board(b, (xx - 0.045, y0, z1 - 0.02), (xx + 0.045, y1, z1), "plank")
    for (x, y) in ((x0 + 0.04, y0 - t), (x1 - 0.04, y0 - t)):                              # nail heads
        for zz in np.linspace(z0 + 0.04, z1 - 0.04, 6):
            lathe(b, [(0.0, 0.0), (0.004, 0.0), (0.0, 0.0012)], "galv", 6, loc=(x, y, zz), rot=(90, 0, 0))
    card(b, (-0.33, y0 - t - 0.0012, z0 + 0.23), (0.66, 0, 0), (0, 0, 0.44), "signCrateStencil", sign=True)
    if variant:
        card(b, (x1 + t + 0.0012, -0.25, z0 + 0.25), (0, 0.5, 0), (0, 0, 0.4), "signVultureStencil", sign=True)
    return done(ctx, b, "SM_Prop_CrateWood" + ("_B" if variant else ""), M, "Catalogue prop_crate_wood%s: plywood shipping crate "
                "1.04 x 0.84 x 0.90 on two 4 x 4 skids, timber cleats round every face, diagonal brace on both long sides, "
                "battened lid, nails; black stencil FRAGILE / HANDLE WITH CARE / LOT 0214 QNS and an up arrow on -Y "
                "(M_Sign_CrateStencil, alpha = paint: masked decal material)%s." % (
                    " (variant 2)" if variant else "", "; bone-white crew stencil on the +X end (M_Sign_VultureStencil)" if variant else ""),
                (1.1, 0.9, 1.0), cover=1.0)


def carton(M, size, seed, open_=False, printed=True, label=True):
    """One corrugated carton at the origin (footprint centre, base on z = 0), front -Y."""
    b = B(seed)
    w, d, h = size
    if not open_:
        box(b, (-w / 2, -d / 2, 0.0), (w / 2, d / 2, h), "card", ch=0.006)
        box(b, (-w / 2 - 0.001, -0.025, h - 0.0005), (w / 2 + 0.001, 0.025, h + 0.0012), "tape", ch=0.0)
        for s in (-1, 1):
            box(b, (s * w / 2 - (0.0012 if s < 0 else 0), -0.025, h - 0.07), (s * w / 2 + (0.0012 if s > 0 else 0), 0.025, h), "tape", ch=0.0)
        box(b, (-w / 2 + 0.01, -0.0006, h + 0.0002), (w / 2 - 0.01, 0.0006, h + 0.0004), "black", ch=0.0)   # flap seam
    else:
        t = 0.005
        box(b, (-w / 2, -d / 2, 0.0), (w / 2, d / 2, t), "card", ch=0.0)
        for s in (-1, 1):
            box(b, (-w / 2, s * d / 2 - (t if s > 0 else 0), 0.0), (w / 2, s * d / 2 + (0 if s > 0 else t), h), "card", ch=0.001)
            box(b, (s * w / 2 - (t if s > 0 else 0), -d / 2, 0.0), (s * w / 2 + (0 if s > 0 else t), d / 2, h), "card", ch=0.001)
        rng = np.random.default_rng(seed)
        for s in (-1, 1):                                                                 # flaps standing up and out
            f = geo.box((w, t, d / 2), bevel=0.0)
            gob(f, b, "card", loc=(0, s * d / 2, h), rot=(-s * rng.uniform(28, 40), 0, 0))
            f = geo.box((t, d, w / 2 * 0.8), bevel=0.0)
            gob(f, b, "card", loc=(s * w / 2, 0, h), rot=(0, s * rng.uniform(45, 65), 0))
        F.blob(b, (w * 0.7, d * 0.6, 0.1), (0, 0, h * 0.55), "pWhite", seed, lumps=0.02)       # packing paper inside
    if printed and w >= 0.28:
        sc = min(1.0, (w - 0.04) / 0.34)
        card(b, (-0.13, -d / 2 - 0.0012, h * 0.35), (0.26, 0, 0), (0, 0, 0.168), "signCartonPrint", sign=True)
    if label and not open_:
        card(b, (w / 2 + 0.0012, -0.075, h * 0.3), (0, 0.15, 0), (0, 0, 0.10), "signCartonLabel", sign=True)
    return b


def cardboard_boxes(ctx, M):
    sign_slot(M, "CartonPrint", 0.26, 0.168)
    sign_slot(M, "CartonLabel", 0.15, 0.10)
    b = B(260)
    from assets.facade import sub
    sub(b, carton(M, (0.52, 0.44, 0.38), 261), 4, (-0.18, 0.05, 0.0))
    sub(b, carton(M, (0.40, 0.32, 0.26), 262, open_=True, printed=False, label=False), -6, (-0.17, 0.06, 0.38))
    sub(b, carton(M, (0.36, 0.30, 0.28), 263), -12, (0.22, -0.14, 0.0))
    sub(b, carton(M, (0.30, 0.28, 0.24), 264), 25, (0.24, 0.30, 0.0))
    sub(b, carton(M, (0.26, 0.22, 0.20), 265, label=False), 50, (0.12, -0.12, 0.28))
    return done(ctx, b, "SM_Prop_CardboardBoxes", M, "Catalogue prop_cardboard_boxes: loose pile of five corrugated cartons sealed "
                "with packing tape (MI_Cardboard_Kraft, MI_Plastic_Tape), the largest 0.52 x 0.44 x 0.38 with an open one on top "
                "(flaps up, packing paper), THIS SIDE UP and arrows (M_Sign_CartonPrint, alpha decal) and shipping labels with a "
                "barcode (M_Sign_CartonLabel). Second pile: mirror in engine.", (0.95, 0.78, 0.77), cover=0.72, ao=None)


def tyres(ctx, M):
    b = B(270)
    F.tyre(b, M)
    out = [done(ctx, b, "SM_Prop_Tire", M, "Car tyre 0.77 across, 0.245 section, 0.40 bore, four tread grooves, lying flat "
                "(the scanned SM_Prop_Tyre is a smaller tyre).", (0.77, 0.77, 0.245), collision="convex", cover=0.25)]
    R = Renamer(ctx, {"SM_Furn_TyreStack_A": "SM_Prop_TireStack", "SM_Furn_TyreStack_B": "SM_Prop_TireStack_B",
                      "SM_Furn_JerseyBarrier": "SM_Street_JerseyBarrier"})
    out += F.tyre_stacks(R, M)
    out.append(F.jersey_barrier(R, M))
    return out


# =============================================================================================== shop-front extras

def pawn_balls(ctx, M):
    """Three gilded balls on a scrolled wrought bracket: pivot on the wall plane (back plate at y = 0), the bracket
    projecting toward -Y."""
    b = B(280)
    box(b, (-0.08, 0.0, -0.20), (0.08, 0.012, 0.20), "black", ch=0.004)                     # wall plate
    for zz in (-0.15, 0.15):
        lathe(b, [(0.0, 0.0), (0.012, 0.0), (0.012, 0.008), (0.0, 0.01)], "galv", 6, loc=(0, -0.0, zz), rot=(90, 0, 0))
    rod(b, (0.0, 0.0, 0.10), (0.0, -0.62, 0.10), 0.016, "black", n=10)                     # arm
    pts = [(0.0, 0.0, -0.15)] + [(0.0, -0.05 - 0.55 * t, -0.15 + 0.25 * t ** 0.7) for t in np.linspace(0.1, 1, 8)]
    tube_path(b, pts, 0.01, "black", n=8)                                                   # brace
    for k in range(3):                                                                    # scroll in the angle
        a = np.linspace(0, 2 * np.pi * 0.85, 20)
        r = 0.06 * (1 - a / (2 * np.pi))
        sp = [(0.0, -0.16 - 0.1 * k + r_ * math.cos(a_), -0.02 + r_ * math.sin(a_)) for a_, r_ in zip(a, r)]
        tube_path(b, sp, 0.005, "black", n=6)
    bx_ = -0.62
    rod(b, (-0.22, bx_, 0.10), (0.22, bx_, 0.10), 0.012, "black", n=8)                      # cross bar
    for (x, zt, zb_) in ((-0.20, 0.10, -0.20), (0.20, 0.10, -0.20), (0.0, 0.10, -0.42)):
        rod(b, (x, bx_, zt), (x, bx_, zb_ + 0.13), 0.004, "black", n=6)
        gob(geo.torus(0.012, 0.003, 12, 6), b, "gold", loc=(x, bx_, zb_ + 0.135), rot=(90, 0, 0))
        lathe(b, [(0.0, -0.125)] + [(0.125 * math.sin(t), -0.125 * math.cos(t)) for t in np.linspace(0.1, math.pi - 0.1, 24)] + [(0.0, 0.125)],
              "gold", 40, loc=(x, bx_, zb_))
        lathe(b, [(0.0, 0.0), (0.02, 0.0), (0.016, 0.012), (0.0, 0.014)], "gold", 16, loc=(x, bx_, zb_ + 0.117))
    return done(ctx, b, "SM_Sign_PawnBalls", M, "The pawnbroker's three gilded balls 0.25 across (art bible addition to PAWN & GOLD) "
                "hanging from a cross bar on a wrought bracket 0.62 deep with a brace and scrolls. Pivot on the wall plane, "
                "projecting toward -Y. Mount on the Pawn shop pier beside the sign band, pivot about 3.3 m above the sidewalk. "
                "MI_Metal_Gold: gilded metal (base #e7b53a, metallic 1, roughness 0.28, dulled toward the tops).",
                None, collision="none", ao=None, ctr=False, ground=False)


def barber_pole(ctx, M):
    """Wall-mounted barber pole: chrome dome and base, glass cylinder, the striped inner cylinder that turns."""
    sign_slot(M, "BarberPole", 1.0, 1.0)
    b = B(281)
    yc, r = -0.17, 0.085
    box(b, (-0.05, 0.0, 0.10), (0.05, 0.012, 0.95), "chrome", ch=0.004)                     # back strap
    for zz in (0.18, 0.86):
        bar(b, (0.0, 0.0, zz), (0.0, yc + r, zz), 0.03, 0.012, "chrome")
    lathe(b, [(0.0, 0.0), (0.06, 0.0), (0.10, 0.04), (0.10, 0.10), (0.095, 0.11), (0.0, 0.11)], "chrome", 40, loc=(0, yc, 0.0))
    lathe(b, [(0.0, 0.0), (0.095, 0.0), (0.10, 0.01), (0.10, 0.05), (0.07, 0.10), (0.03, 0.12), (0.0, 0.125)], "chrome", 40, loc=(0, yc, 0.83))
    gob(geo.sphere(0.04, 24, 12), b, "chrome", loc=(0, yc, 1.0))
    gob(geo.tube(r + 0.004, r, 0.72, 40, name="glass"), b, "glass", loc=(0, yc, 0.11))
    pole = b.finish("SM_Sign_BarberPole_frame", M, ctx.col)
    F.weather(ctx, b, pole, "barber", ground=False, ao=None)
    V, Q, T, UV = tube_mesh(np.array([[0, yc, 0.11], [0, yc, 0.83]]), np.array([0.075, 0.075]), 40, 2 * np.pi * 0.075, 0.72, cap=False)
    UV[:, 1] = (V[:, 2] - 0.11) / 0.72
    UV[:, 0] = np.tile(np.linspace(0, 1, 41), 2)
    inner = mesh_object("pole_inner", V, [(Q, 0)], UV, [M["signBarberPole"]], ctx.col)
    geo.ensure_wear(inner)
    ob = geo.join([pole, inner], "SM_Sign_BarberPole", ctx.col)
    ctx.asset(ob, collision="none", notes="Wall-mounted barber pole for CROWN FADE BARBER (art bible addition): chrome base and "
              "dome with a ball, glass cylinder 0.18 across, the inner cylinder 0.15 across x 0.72 carries the red, white and "
              "blue helix (M_Sign_BarberPole on 0..1: u round, v up; pan V to turn it, lit from inside at night). Pivot on the "
              "wall plane, standing off toward -Y; mount on the Barber shop pier, base about 2.2 m above the sidewalk.",
              expect_size=(0.2, None, 1.04), slots=META)
    ctx.built.append(ob)
    return ob


def hydrant_open(ctx, M):
    """Catalogue street_hydrant_open: red post hydrant with its front (pumper) cap off and lying on the ground, the
    open dark mouth toward -Y. The jet and the wet patches are engine effects."""
    b = B(290)
    lathe(b, [(0.0, 0.0), (0.15, 0.0), (0.15, 0.025), (0.125, 0.03), (0.105, 0.06), (0.10, 0.11), (0.11, 0.125), (0.11, 0.145),
              (0.098, 0.15), (0.095, 0.56), (0.11, 0.57), (0.11, 0.59), (0.0, 0.59)], "red", 48)          # foot flange, barrel
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        lathe(b, [(0.0, 0.0), (0.012, 0.0), (0.012, 0.012), (0.0, 0.014)], "galv", 6, loc=(0.128 * math.cos(a), 0.128 * math.sin(a), 0.03))
    for z in (0.30, 0.42):
        lathe(b, [(0.094, z - 0.01), (0.1, z - 0.006), (0.1, z + 0.006), (0.094, z + 0.01)], "red", 48, closed=True)
    lathe(b, [(0.0, 0.0), (0.112, 0.0), (0.112, 0.02), (0.10, 0.025), (0.09, 0.07), (0.06, 0.11), (0.035, 0.12), (0.0, 0.122)],
          "drumGrey", 48, loc=(0, 0, 0.59))                                                               # bonnet
    lathe(b, [(0.0, 0.0), (0.02, 0.0), (0.02, 0.035), (0.0, 0.035)], "drumGrey", 5, loc=(0, 0, 0.71))      # operating nut
    for s in (-1, 1):                                                                                     # side hose nozzles, capped
        lathe(b, [(0.0, 0.0), (0.05, 0.0), (0.045, 0.07), (0.0, 0.07)], "red", 32, loc=(s * 0.06, 0, 0.46), rot=(0, s * 90, 0))
        lathe(b, [(0.0, 0.0), (0.048, 0.0), (0.05, 0.005), (0.05, 0.035), (0.03, 0.04), (0.0, 0.04)], "drumGrey", 32,
              loc=(s * 0.13, 0, 0.46), rot=(0, s * 90, 0))
        lathe(b, [(0.0, 0.0), (0.016, 0.0), (0.016, 0.02), (0.0, 0.02)], "drumGrey", 5, loc=(s * 0.17, 0, 0.46), rot=(0, s * 90, 0))
    # front pumper outlet toward -Y, cap off: threaded nozzle and the open, dark, wet mouth
    lathe(b, [(0.0, 0.0), (0.075, 0.0), (0.068, 0.07), (0.0, 0.07)], "red", 36, loc=(0, -0.06, 0.47), rot=(90, 0, 0))
    gob(geo.tube(0.066, 0.052, 0.04, 36), b, "galv", loc=(0, -0.13, 0.47), rot=(90, 0, 0))
    for k in range(5):
        gob(geo.torus(0.066, 0.0016, 36, 6), b, "galv", loc=(0, -0.135 - 0.006 * k, 0.47), rot=(90, 0, 0))
    lathe(b, [(0.0, 0.0), (0.054, 0.0), (0.0, 0.001)], "interior", 24, loc=(0, -0.10, 0.47), rot=(90, 0, 0))
    # the pumper cap lying on the ground, chain to it
    cap = [(0.0, 0.0), (0.075, 0.0), (0.078, 0.006), (0.078, 0.05), (0.05, 0.058), (0.0, 0.06)]
    lathe(b, cap, "drumGrey", 32, loc=(0.16, -0.20, 0.0), rot=(0, 0, 0))
    lathe(b, [(0.0, 0.0), (0.024, 0.0), (0.024, 0.025), (0.0, 0.025)], "drumGrey", 5, loc=(0.16, -0.20, 0.06))
    b.absorb(geo.chain([(0.05, -0.08, 0.40), (0.06, -0.14, 0.16), (0.10, -0.18, 0.02), (0.14, -0.20, 0.03)], link_len=0.024, wire=0.0032), "galv")
    return done(ctx, b, "SM_Street_Hydrant_Open", M, "Catalogue street_hydrant_open: red post hydrant (#b3261e, grey #8d949a bonnet "
                "and caps) with the front pumper cap off - the open dark mouth (MI_Interior_Dark) at 0.47 toward -Y - and the cap "
                "lying on the ground 0.2 away on its chain. Jet (2.8 m arc toward -Y) and wet patches are engine effects; jet "
                "anchor (0, -0.15, 0.47).", (0.44, None, None), collision="convex", cover=0.74, ctr=False)


def license_plate(ctx, M):
    """Catalogue sign_license_plate: pressed steel plate 0.30 x 0.15 with a rounded outline, raised rim and four
    mounting slots; the face is M_Sign_LicensePlate (swap the texture set for the other codes)."""
    sign_slot(M, "LicensePlate", 0.30, 0.15)
    b = B(291)
    ol = [(0.15 - 0.012 + 0.012 * math.cos(a), 0.075 - 0.012 + 0.012 * math.sin(a)) for a in np.linspace(0, math.pi / 2, 4)]
    ol = ol + [(-x, y) for x, y in ol[::-1]]
    ol = ol + [(x, -y) for x, y in ol[::-1]]
    b.poly_plate([(x, 0.0, z) for x, z in ol][::-1], 0.0012, "galv", step=0.5)
    card(b, (-0.15, -0.0002, -0.075), (0.30, 0, 0), (0, 0, 0.15), "signLicensePlate", sign=True)
    for s in (-1, 1):
        box(b, (-0.145, -0.0018, s * 0.072 - 0.0015), (0.145, -0.0002, s * 0.072 + 0.0015), "galv", ch=0.0)
        box(b, (s * 0.147 - 0.0015, -0.0018, -0.07), (s * 0.147 + 0.0015, -0.0002, 0.07), "galv", ch=0.0)
    return done(ctx, b, "SM_Sign_LicensePlate", M, "Catalogue sign_license_plate: pressed steel plate 0.30 x 0.15, rounded corners, "
                "raised rim, face toward -Y (M_Sign_LicensePlate = HLS-2141; the other invented codes are the texture sets "
                "Sign_LicensePlate_TKV9907, _KQB5530, _LWG4418 and the yellow taxi plate _Taxi, T-5K83). Pivot at the plate "
                "centre on its back face.", (0.30, None, 0.15), collision="none", ground=False, ao=None, ctr=False)


# =============================================================================================== build

GROUPS = {
    "street": ["SM_Street_PhoneBooth", "SM_Street_TrafficLight", "SM_Street_Planter", "SM_Street_Planter_B", "SM_Street_Tree",
               "SM_Street_Tree_B", "SM_Street_Tree_C", "SM_Street_TrashCan", "SM_Street_Bench", "SM_Street_FoodCart",
               "SM_Street_SignPost", "SM_Sign_PawnBalls", "SM_Sign_BarberPole", "SM_Street_Hydrant_Open", "SM_Sign_LicensePlate"],
    "yard": ["SM_Prop_Generator", "SM_Prop_FloodlightStand", "SM_Prop_PortaPotty", "SM_Prop_VendingMachine", "SM_Prop_Workbench",
             "SM_Prop_EngineHoist", "SM_Prop_EngineHoist_Blue", "SM_Prop_Compressor", "SM_Prop_Compressor_Black", "SM_Prop_CarLift",
             "SM_Prop_ToolChest", "SM_Prop_CrateWood", "SM_Prop_CrateWood_B", "SM_Prop_CardboardBoxes", "SM_Prop_Tire"],
}
PREVIEWS = {"gaps_street": "street", "gaps_yard": "yard"}
GRAPHICS = ["SM_Street_PhoneBooth", "SM_Street_SignPost", "SM_Sign_PawnBalls", "SM_Sign_BarberPole", "SM_Prop_VendingMachine",
            "SM_Prop_CrateWood_B", "SM_Prop_CardboardBoxes", "SM_Street_FoodCart"]


def build(ctx):
    ctx.built = []
    o = ctx.args.only
    M = materials(ctx)

    def want(name):
        if not o:
            return True
        for g, names in GROUPS.items():
            if g in o and name in names:
                return True
        for p, g in PREVIEWS.items():
            if p in o and name in GROUPS[g]:
                return True
        if "gaps_graphics" in o and name in GRAPHICS:
            return True
        if "gaps_street" in o and name == "SM_Prop_Tire":
            return True
        return name in o

    jobs = [("SM_Street_PhoneBooth", phone_booth), ("SM_Street_TrafficLight", traffic_light),
            ("SM_Street_Planter", lambda c, m: planter(c, m, 0)), ("SM_Street_Planter_B", lambda c, m: planter(c, m, 1)),
            ("SM_Street_Tree", lambda c, m: street_tree(c, m, 0)), ("SM_Street_Tree_B", lambda c, m: street_tree(c, m, 1)),
            ("SM_Street_Tree_C", lambda c, m: street_tree(c, m, 2)), ("SM_Street_TrashCan", trash_can),
            ("SM_Street_Bench", bench), ("SM_Street_FoodCart", food_cart), ("SM_Street_SignPost", sign_post),
            ("SM_Sign_PawnBalls", pawn_balls), ("SM_Sign_BarberPole", barber_pole),
            ("SM_Prop_Generator", generator), ("SM_Prop_FloodlightStand", floodlight), ("SM_Prop_PortaPotty", porta_potty),
            ("SM_Prop_VendingMachine", vending), ("SM_Prop_Workbench", workbench),
            ("SM_Prop_EngineHoist", lambda c, m: engine_hoist(c, m, 0)), ("SM_Prop_EngineHoist_Blue", lambda c, m: engine_hoist(c, m, 1)),
            ("SM_Prop_Compressor", lambda c, m: compressor(c, m, 0)), ("SM_Prop_Compressor_Black", lambda c, m: compressor(c, m, 1)),
            ("SM_Prop_CarLift", car_lift), ("SM_Prop_ToolChest", tool_chest),
            ("SM_Prop_CrateWood", lambda c, m: crate_wood(c, m, 0)), ("SM_Prop_CrateWood_B", lambda c, m: crate_wood(c, m, 1)),
            ("SM_Prop_CardboardBoxes", cardboard_boxes), ("SM_Prop_Tire", tyres),
            ("SM_Street_Hydrant_Open", hydrant_open), ("SM_Sign_LicensePlate", license_plate)]
    for name, fn in jobs:
        if want(name):
            ctx.log("building %s" % name)
            fn(ctx, M)
    ctx.M = M
    return ctx.built


def on_export(ctx, objs):
    """Export every asset this run built (build() already applied --only and the group names)."""
    from mi import export
    for name, a in ctx.assets.items():
        export.export_asset(a["ob"], ctx.family, a["collision"], a["cover_height"], a["notes"], a["pivot"],
                            a["expect_size"], fbx=ctx.args.fbx, slots=a["slots"])


# =============================================================================================== previews

class Quiet:
    """ctx stand-in for building furniture pieces into a preview without declaring them as assets of this family."""

    def __init__(self, ctx):
        self._ctx, self.built = ctx, []

    def __getattr__(self, k):
        return getattr(self._ctx, k)

    def asset(self, ob, **kw):
        geo.ensure_wear(ob)
        return ob


def ground(set_name, x0, x1, y0, y1, name="Ground"):
    xs, ys = np.linspace(x0, x1, int((x1 - x0) * 2) + 1), np.linspace(y0, y1, int((y1 - y0) * 2) + 1)
    pl = geo.heightfield(xs, ys, lambda X_, Y_: X_ * 0.0, name=name, tile_m=mat.scan_tile(set_name))
    pl.data.materials.append(mat.from_scan(set_name, alpha="splash"))
    geo.ensure_wear(pl)
    scene.move_to(pl, scene.collection("Rig"))
    return pl


def wall(set_name, x0, x1, y, h, name="Wall"):
    w = geo.box((x1 - x0, 0.3, h), bevel=0.0, name=name)
    geo.transform(w, loc=((x0 + x1) / 2, y + 0.15, 0))
    geo.uv_world_box(w, mat.scan_tile(set_name))
    w.data.materials.append(mat.from_scan(set_name, alpha="splash"))
    geo.ensure_wear(w)
    scene.move_to(w, scene.collection("Rig"))
    return w


def put(assets, layout):
    for n, ob in assets.items():
        ob.hide_render = n not in layout
        if n in layout:
            x, y, *r = layout[n]
            ob.location = (x, y, r[1] if len(r) > 1 else 0.0)
            ob.rotation_euler = (0, 0, math.radians(r[0] if r else 0.0))
            ob["mi_placed"] = True


STREET_VIEW = {"SM_Street_Tree": (-6.6, 2.2, 0), "SM_Street_Tree_B": (7.2, 3.4, 40), "SM_Street_Planter": (-3.9, 0.9, 0),
               "SM_Street_Planter_B": (-4.3, -0.8, 20), "SM_Street_PhoneBooth": (-2.3, 1.3, 0), "SM_Street_TrashCan": (-1.0, -0.2, 0),
               "SM_Street_Bench": (0.6, 1.2, 0), "SM_Street_SignPost": (1.9, -0.4, 0), "SM_Street_FoodCart": (4.0, 0.9, -8),
               "SM_Street_TrafficLight": (6.0, 5.0, 180), "SM_Street_JerseyBarrier": (0.5, -2.3, 4),
               "SM_Prop_TireStack": (-2.3, -1.6, 0)}
YARD_VIEW = {"SM_Prop_CarLift": (-4.6, 2.4, 0), "SM_Prop_CarLift_Arms": (-4.6, 2.4, 0, 1.98), "SM_Prop_Generator": (-0.9, 3.6, 0),
             "SM_Prop_PortaPotty": (2.0, 3.7, 0), "SM_Prop_VendingMachine": (3.7, 3.8, 0), "SM_Prop_Workbench": (-1.2, 1.3, 0),
             "SM_Prop_ToolChest": (1.0, 1.4, 0), "SM_Prop_EngineHoist": (2.9, 1.1, -25), "SM_Prop_Compressor_Black": (4.6, 0.6, 20),
             "SM_Prop_CrateWood": (-3.3, -0.6, 12), "SM_Prop_CrateWood_B": (-2.0, -1.4, -8), "SM_Prop_CardboardBoxes": (-0.4, -1.0, 0),
             "SM_Prop_TireStack_B": (0.9, -1.2, 0), "SM_Prop_Tire": (1.7, -1.7, 0), "SM_Prop_FloodlightStand": (5.4, -0.9, 25),
             "SM_Prop_Compressor": (3.7, -1.6, -60)}
GRAPHICS_VIEW = {"SM_Sign_PawnBalls": (-1.0, 2.0, 0, 2.6), "SM_Sign_BarberPole": (1.6, 2.0, 0, 1.15), "SM_Street_PhoneBooth": (-2.7, 0.9, 0),
                 "SM_Street_SignPost": (0.35, -0.5, 0), "SM_Prop_VendingMachine": (2.9, 1.3, 0), "SM_Prop_CrateWood_B": (1.1, 0.0, -60),
                 "SM_Prop_CardboardBoxes": (2.1, -0.9, -15), "_meter": (-1.6, -0.9, 0), "_news": (-1.15, 1.3, 0), "_mail": (-0.35, 1.35, 0),
                 "_booth": (5.2, 1.6, 0), "_banner": (0.0, 1.98, 0, 3.4)}


def on_preview(ctx, objs):
    a = ctx.args
    only = set(a.only or [])
    assets = {n: v["ob"] for n, v in ctx.assets.items()}
    render.setup(samples=a.samples, res=(1280, 720), threads=3)
    render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING)
    render.backdrop(color=(0.16, 0.155, 0.15))
    if "gaps_street" in only:
        g = ground("TS_Sidewalk_ScanWorn", -12, 12, -6, 10)
        put(assets, STREET_VIEW)
        render.cam_look((0.3, -12.0, 2.0), (0.3, 1.5, 1.9), lens=27)
        p, sec = render.render_jpeg(os.path.join(paths.previews, "gaps_street.jpg"), a.samples)
        ctx.log("preview %s %.0fs" % (p, sec))
        bpy.data.objects.remove(g, do_unlink=True)
    if "gaps_yard" in only:
        g = ground("TS_Floor_ScanGarage", -10, 10, -6, 8)
        w = wall("TS_Block_ScanPainted", -9, 9, 5.0, 4.5)
        put(assets, YARD_VIEW)
        render.cam_look((0.2, -9.0, 2.3), (0.2, 1.4, 1.0), lens=26)
        p, sec = render.render_jpeg(os.path.join(paths.previews, "gaps_yard.jpg"), a.samples)
        ctx.log("preview %s %.0fs" % (p, sec))
        for o in (g, w):
            bpy.data.objects.remove(o, do_unlink=True)
    if "gaps_graphics" in only:
        M = ctx.M
        Q = Quiet(ctx)
        extra = {"_meter": F.parking_meter(Q, M), "_news": F.newspaper_box(Q, M), "_mail": F.mailbox(Q, M), "_booth": F.lot_booth(Q, M)}
        bb = B(299)
        F.sign_slot(M, "ShedBanner_Chicken", 4.9, 0.78)
        box(bb, (-2.5, 0.0, -0.05), (2.5, 0.03, 0.83), "plyGreen")
        card(bb, (-2.45, -0.002, 0.0), (4.9, 0, 0), (0, 0, 0.78), "signShedBanner_Chicken", sign=True)
        extra["_banner"] = bb.finish("Banner", M, ctx.col)
        geo.ensure_wear(extra["_banner"])
        assets.update(extra)
        g = ground("TS_Sidewalk_ScanBroom", -10, 10, -6, 6)
        w = wall("TS_Brick_ScanRed", -8, 8, 2.0, 5.0)
        put(assets, GRAPHICS_VIEW)
        render.cam_look((0.2, -6.2, 1.75), (0.6, 1.2, 1.45), lens=24)
        p, sec = render.render_jpeg(os.path.join(paths.previews, "gaps_graphics.jpg"), a.samples)
        ctx.log("preview %s %.0fs" % (p, sec))
