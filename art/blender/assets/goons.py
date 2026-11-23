"""The three Goons (briefs docs/unreal/spec/assets/characters.json goon_hoodie, goon_puffer, goon_tracksuit): one man on
the UE5 mannequin skeleton (SK_Mannequin) in three outfits, each one skinned mesh SK_Goon_<Outfit>.

    build.py build goons [--only hoodie,puffer,tracksuit] [--bake] [--export] [--preview]
    MI_PREVIEWS=goons_lineup,goons_hoodie_hero,goons_detail,goons_poses,goons_wire   (pictures to render)
    MI_GOONS_REDRAPE=1   ignore the drape cache (art/out/goons/cache_*.npz) and simulate again

How a Goon is made (every position is read from the imported mannequin, rest A-pose, metres, facing -Y):
  1. shared kit: black leather gloves (the player's glove anatomy, closed up the forearm), socks, sneakers (sole with
     herringbone tread, upper, collar, tongue, eyelets, laces with a bow, oxblood heel tab);
  2. trousers, then the upper garment: start shapes cut from the body as offsets and hanging lofts, open at the
     hems, draped by Blender's cloth solver onto the body (and the sneakers) with their hems pinned and extra
     length grown where real clothes bunch (cuffs, knees, trouser breaks, the blouse over the waistband);
  3. finishing: rib bands (waistband, cuffs, collars) as their own meshes, turned hems with thickness, the hood draped
     over the mask, pocket, drawstrings with aglets, zips with teeth and pulls, the puffer's quilt loft, the sling;
  4. head: the knitted ski mask (eye slits sunk into it), beanie, backwards cap, wrap-around glasses, bandana;
  5. per piece a fabric kind and colour (face attributes for the texel bake: assets/_goons_tex.py), decimation to the
     triangle budget, skin weights transferred from the mannequin's surface and smoothed;
  6. two unique texture sets per outfit: Goon<Outfit>_Cloth (4K: garments, gloves, sneakers) and Goon<Outfit>_Head
     (2K: mask and head pieces, sling, small hardware), slots M_Goon<Outfit>_Cloth and M_Goon<Outfit>_Head.
Drapes are cached in art/out/goons (git-ignored: they are built on Epic's mannequin) by a version key per piece.
"""
import json
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import char, cloth, geo, paths, rig, scene, sdf
from assets import _goons_body as GB
from assets import _goons_cloth as GC
from assets import _goons_head as GH
from assets import _goons_kit as GK

FAMILY = {"name": "goons", "description": "The three Goons on the UE5 mannequin skeleton (hoodie, puffer, tracksuit)"}

OUTFITS = ("Hoodie", "Puffer", "Tracksuit")
CACHE = os.path.join(paths.out, "goons")

# fabric kinds (face attribute mi_kind; assets/_goons_tex.py draws each)
K = dict(fleece=0, rib=1, denim=2, leather=3, shoe=4, sole=5, maskknit=6, quilt=7, nylon=8, twill=9, tricot=10,
         webbing=11, metal=12, cord=13, aglet=14, captwill=15, lens=16, bandana=17, sock=18, beanie=19, zip=20)

COL = {"hoodie": "#232328", "pocket": "#0e0e11", "oxblood": "#7c151d", "darkox": "#4d0d13", "jeans": "#262a36",
       "mask": "#dcd5c5", "seam": "#b5ad9c", "slit": "#050506", "glove": "#0d0d0f", "upper": "#d6d1c4",
       "sole": "#efece4", "jacket": "#28282e", "quiltseam": "#232328", "trousers": "#30323b", "track": "#232328",
       "black": "#141416", "metal": "#8a8a88", "webbing": "#1a1a1c", "sock": "#18181a", "lens": "#050506"}

BUDGET = {"Hoodie": 18000, "Jeans": 11000, "Hood": 6500, "Waistband": 2400, "Cuff": 1100, "Pocket": 900,
          "Mask": 9000, "Puffer": 21000, "Collar": 2400, "Trousers": 11000, "TrackJacket": 17000, "TrackTrousers": 11000,
          "Beanie": 2200, "BeanieCuff": 1400, "Cap": 2600, "Bandana": 2600, "Sock": 500, "Sling": 1300}


def log_default(m):
    print(m, flush=True)


# ------------------------------------------------------------------------------------------------ helpers


def srgb(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def tag(ob, kind, colour, piece=0):
    """Face attributes the texel bake reads: fabric kind, linear base colour, piece number."""
    n = len(ob.data.polygons)
    c = srgb(COL.get(colour, colour))
    for nm, val in (("mi_kind", K[kind]), ("mi_r", c[0]), ("mi_g", c[1]), ("mi_b", c[2]), ("mi_piece", piece)):
        a = ob.data.attributes.get(nm) or ob.data.attributes.new(nm, "FLOAT", "FACE")
        a.data.foreach_set("value", np.full(n, float(val), dtype=np.float32))
    return ob


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def _mesh_arrays(ob):
    me = ob.data
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    lt = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get("vertex_index", lt)
    ls = np.empty(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("loop_total", ls)
    return co.reshape(-1, 3), lt, ls


def _from_arrays(name, co, lt, ls, col):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(co))
    me.vertices.foreach_set("co", np.asarray(co, dtype=np.float32).ravel())
    me.loops.add(len(lt))
    me.loops.foreach_set("vertex_index", np.asarray(lt, dtype=np.int32))
    me.polygons.add(len(ls))
    starts = np.concatenate([[0], np.cumsum(ls)[:-1]]).astype(np.int32)
    me.polygons.foreach_set("loop_start", starts)
    me.update(calc_edges=True)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def cached(key, version, col, fn, log=log_default):
    """Object `key` from art/out/goons/cache_<key>.npz when its version matches, else fn() -> object (or tuple whose
    first item is the object; the rest is not cached) and store it."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "cache_%s.npz" % key)
    if os.path.exists(path) and not os.environ.get("MI_GOONS_REDRAPE"):
        z = np.load(path, allow_pickle=False)
        if str(z["version"]) == version:
            return _from_arrays(key, z["co"], z["lt"], z["ls"], col)
    ob = fn()
    if isinstance(ob, tuple):
        ob = ob[0]
    ob.name = key
    co, lt, ls = _mesh_arrays(ob)
    np.savez_compressed(path, co=co, lt=lt, ls=ls, version=np.array(version))
    log("  cached %s (%d vertices)" % (key, len(co)))
    return ob


def ordered_ring(ob, pick):
    """The open-edge loop chosen by pick(points) -> score (largest wins), as ordered points."""
    co = GC.verts(ob)
    loops = cloth.boundary_loops(ob)
    L = max(loops, key=lambda L: pick(co[L]))
    return L, co[L]


def collider_of(obs, name, col, ratio=0.5, inflate=0.0):
    parts = []
    for o in obs:
        parts.append(cloth.collider(o, name + "_p", ratio=1.0, inflate=0.0, col=col))
    ob = geo.join(parts, name, col)
    if ratio < 1.0:
        md = ob.modifiers.new("dec", "DECIMATE")
        md.ratio = ratio
        geo._apply_modifier(ob, md)
    if inflate:
        n = cloth.vertex_normals(ob)
        GC.set_verts(ob, GC.verts(ob) + n * inflate)
    ob.hide_render = True
    return ob


def smooth_loop(ob, loop, iters=8, lam=0.5):
    """1D smoothing of an open edge along itself (and a little into the next ring), so a draped hem runs clean."""
    co = GC.verts(ob)
    L = np.asarray(loop)
    for _ in range(iters):
        P = co[L]
        co[L] = P + lam * (0.5 * (np.roll(P, 1, axis=0) + np.roll(P, -1, axis=0)) - P)
    GC.set_verts(ob, co)


def thicken_edges(ob, depth=0.018, thickness=0.003, which=None, smooth=0):
    """Turned hems on the open loops (all, or those which(points) accepts)."""
    co = GC.verts(ob)
    loops = [L for L in cloth.boundary_loops(ob) if which is None or which(co[L])]
    if smooth:
        for L in loops:
            smooth_loop(ob, L, smooth)
    if loops:
        cloth.hem_facing(ob, depth=depth, thickness=thickness, steps=1, loops=loops)
    return ob


# ------------------------------------------------------------------------------------------------ the shared man


class Man:
    """The measured mannequin and everything every outfit reads."""

    def __init__(self, ctx):
        self.arm, self.body = char.import_mannequin()
        self.body.hide_render = True
        self.B = GB.Body(self.arm, self.body)
        self.BF = GB.BodyField(self.B, cache=os.path.join(CACHE, "body_field.npz"))
        self.M = GC.Marks(self.B)
        self.H = GH.Head(self.B)
        self.col = ctx.col
        self.work = scene.collection("Goons_Work")
        self.work.hide_render = True
        self.body_col = cloth.collider(self.body, "Col_Body", ratio=0.3, col=self.work)
        self.body_col.hide_render = True
        self.log = ctx.log


def kit(man, outfit):
    """Gloves, socks and sneakers for one outfit (separate copies: each outfit bakes its own set)."""
    col, B = man.col, man.B
    out = []
    for s in "lr":
        g = cached("Glove_%s" % s, "g1", col, lambda: GK.glove(man.arm, man.body, s, col))
        out.append(("Glove_" + s, tag(g, "leather", "glove"), "cloth", ("glove", s)))
        sn, F = GK.sneaker(B, s, col)
        for k, o in sn.items():
            kind, colour = {"upper": ("shoe", "upper"), "sole": ("sole", "sole"), "eyelets": ("metal", "metal"),
                            "laces": ("cord", "upper"), "tab": ("shoe", "oxblood")}[k]
            out.append(("Sneaker_%s_%s" % (k, s), tag(o, kind, colour), "cloth" if k in ("upper", "sole") else "head",
                        ("foot", s)))
        sk = cached("Sock_%s" % s, "s1", col, lambda: GK.sock(man.BF, col, 1 if s == "l" else -1))
        out.append(("Sock_" + s, tag(sk, "sock", "sock"), "cloth", ("leg", s)))
    return out


def shoe_collider(man, parts):
    obs = [p[1] for p in parts if p[0].startswith(("Sneaker_upper", "Sneaker_sole"))]
    return collider_of(obs, "Col_Shoes", man.work, ratio=0.6, inflate=0.003)


# ------------------------------------------------------------------------------------------------ hoodie outfit


def mask_piece(man, bottom=1.45):
    ob = cached("Mask", "m3", man.col, lambda: GH.mask(man.H, man.col, bottom_z=bottom, neck=man.M.neck))
    GK.decimate(ob, BUDGET["Mask"])
    return ob


def hood_piece(man, hoodie, mask, name="Hood", version="h7"):
    """The hood up: an offset of the head and shoulders (more room at the back and the crown, where a hood stands
    off), open at the face (the opening closes under the chin) and at the neckline, draped over the mask with the
    neckline pinned (the crown sags, folds gather at the neck), the face opening turned in as the drawstring channel."""
    H, BF, col = man.H, man.BF, man.col
    j = H.j

    def make():
        L, ring = ordered_ring(hoodie, lambda P: P[:, 2].mean())
        ring_z = float(ring[:, 2].mean())

        rc = ring.mean(axis=0)
        ax_ = (ring[:, 0].max() - ring[:, 0].min()) / 2 + 0.006
        ay_ = (ring[:, 1].max() - ring[:, 1].min()) / 2 + 0.006

        def f(p):
            # below the jaw the hood narrows into the hoodie's neckline (an elliptic wall down to the seam)
            q = np.sqrt(((p[:, 0] - rc[0]) / ax_) ** 2 + ((p[:, 1] - rc[1]) / ay_) ** 2)
            wall = (q - 1.0) * min(ax_, ay_) - 0.12 * np.clip((p[:, 2] - ring_z - 0.05) / 0.06, 0, 1)
            y, z = p[:, 1] - j[1], p[:, 2] - j[2]
            e = 0.026 + 0.045 * np.clip((y + 0.02) / 0.12, 0, 1) * np.clip((z + 0.02) / 0.12, 0.3, 1) \
                + 0.012 * np.clip(z / 0.15, 0, 1)
            e = 0.024 + (e - 0.024) * np.clip((p[:, 2] - ring_z) / 0.07, 0, 1)
            return sdf.smax(np.minimum(H(p), BF(p)) - e, wall, 0.015)
        fc = j + np.array([0, -0.05, 0.035])
        cuts = [((fc[0], fc[1] - 0.035, fc[2]), GH.unit((0, -1.0, -0.42)), 0.10), ((0, 0, ring_z), (0, 0, -1))]
        lo = np.array([j[0] - 0.2, j[1] - 0.2, ring_z - 0.03])
        hi = np.array([j[0] + 0.2, j[1] + 0.22, H.top + 0.09])
        hd = cloth.garment_mesh("Hood", f, lo, hi, 0.0105, cuts=cuts, col=col, relax=4)
        co = GC.verts(hd)
        loops = cloth.boundary_loops(hd)
        if len(loops) != 2:
            raise RuntimeError("hood: expected a face opening and a neckline, got %d open loops" % len(loops))
        bottom = min(loops, key=lambda L: co[L][:, 2].mean())
        pin = np.zeros(len(co))
        pin[bottom] = 1.0
        near = GC.grow_weights(co, co[bottom], 0.05)
        pin = np.maximum(pin, 0.6 * near)
        face = max(loops, key=lambda L: co[L][:, 2].mean())
        pin[face] = np.maximum(pin[face], 0.55)
        grow = GC.grow_weights(co, [j + np.array([0, 0.09, 0.10]), j + np.array([0, 0.03, 0.17])], 0.16)
        grow = np.maximum(grow, 0.3) * (1 - pin)
        mc = collider_of([mask], "Col_Mask", man.work, ratio=0.4, inflate=0.002)
        cloth.drape(hd, [mc, man.body_col], frames=30, pin=pin, shrink=grow, shrink_min=-0.04, bending=1.5,
                    mass=0.2, log=man.log)
        cloth.smooth(hd, 3)
        thicken_edges(hd, depth=0.014, thickness=0.005, which=lambda P: P[:, 1].mean() < j[1] - 0.02, smooth=12)
        return hd
    return cached(name, version, col, make)


def hoodie_outfit(man, parts, shoes):
    B, M, BF, col, log = man.B, man.M, man.BF, man.col, man.log
    jeans = cached("Jeans", "j2", col, lambda: GC.trousers(B, M, BF, col, [man.body_col, shoes], log=log, hem=0.115))
    thicken_edges(jeans, depth=0.02, thickness=0.004, which=lambda P: P[:, 2].mean() < 0.3)
    GK.decimate(jeans, BUDGET["Jeans"])
    parts.append(("Jeans", tag(jeans, "denim", "jeans"), "cloth", None))
    jc = collider_of([jeans], "Col_Jeans", man.work, ratio=0.5, inflate=0.002)

    def shell():
        ob, L = GC.hoodie_shell(B, M, BF, col, [man.body_col, jc], log=log, sleeve=0.019, grow=-0.035, ease=0.022,
                                band_level=0.022, cuff_level=0.012, bending=2.2)
        cloth.smooth(ob, 2)
        return ob
    hoodie = cached("Hoodie", "hd4", col, shell)
    bands = GC.bands_for(B, M, BF, col, band_level=0.022, cuff_level=0.012)
    for k, o in bands.items():
        thicken_edges(o, depth=0.012, thickness=0.004, which=lambda P: P[:, 2].mean() < 0.9 or k != "waistband")
        GK.decimate(o, BUDGET["Waistband" if k == "waistband" else "Cuff"])
        parts.append((k.capitalize(), tag(o, "rib", "darkox"), "cloth", ("cuff", k[-1]) if k.startswith("cuff") else None))
    mask = mask_piece(man)
    hood = hood_piece(man, hoodie, mask)
    S = GK.Surface(hoodie)
    pocket = GK.panel("Pocket", S, [(-0.155, 0.945), (0.155, 0.945), (0.12, 1.16), (-0.12, 1.16)], col, lift=0.004)
    md = pocket.modifiers.new("solid", "SOLIDIFY")
    md.thickness, md.offset = 0.0025, -1.0
    geo._apply_modifier(pocket, md)
    GK.decimate(pocket, BUDGET["Pocket"])
    parts.append(("Pocket", tag(pocket, "fleece", "pocket", 1), "cloth", None))
    # drawstrings from the bottom of the face opening, either side of the throat
    hco = GC.verts(hood)
    S2 = GK.Surface(hoodie, hood)
    for sx in (-1, 1):
        cand = hco[(np.abs(hco[:, 0] - sx * 0.042) < 0.012) & (hco[:, 1] < man.H.j[1] - 0.05)]
        start = cand[np.argmin(cand[:, 2])] + np.array([0, -0.004, 0.0])
        cord, ag = GK.drawstring("Drawstring", S2, start, 0.12, col, radius=0.0034, lift=0.0045, aglet=0.022)
        parts.append(("Drawstring", tag(cord, "cord", "oxblood"), "head", None))
        parts.append(("Aglet", tag(ag, "aglet", "black"), "head", None))
    GK.decimate(hoodie, BUDGET["Hoodie"])
    GK.decimate(hood, BUDGET["Hood"])
    parts.append(("Hoodie", tag(hoodie, "fleece", "hoodie"), "cloth", None))
    parts.append(("Hood", tag(hood, "fleece", "hoodie", 2), "cloth", None))
    parts.append(("Mask", tag(mask, "maskknit", "mask"), "head", None))
    sling(man, hoodie, parts)
    return parts


def sling(man, garment, parts):
    S = GK.Surface(garment)
    M = man.M
    ob, P, N = GK.strap_loop(S, M.shoulder["r"] + np.array([0.02, 0.06, 0.07]), M.hip["l"] + np.array([0.07, 0.0, -0.02]),
                             man.col)
    parts.append(("Sling", tag(ob, "webbing", "webbing"), "head", None))
    return ob


# ------------------------------------------------------------------------------------------------ assembly


def weights(man, name, ob, region):
    """Skin weights from the mannequin's surface: gloves per finger (as the player's arms), sneakers from the foot,
    head pieces rigid on the head, everything else nearest-surface and smoothed (looser garments more)."""
    body = man.body
    if region and region[0] == "glove":
        from assets import characters as C
        s = region[1]
        R = C.ArmRig(man.arm, body, s)
        names, W = char.transfer_weights(ob, body, char.ARM_BONES[s], limit=6,
                                         target_labels=C.glove_regions(R, GC.verts(ob))[0],
                                         source_labels=C.source_labels(body, s))
        char.smooth_weights(ob, iterations=3, strength=0.4, limit=6, names=names, W=W)
        return
    if region and region[0] == "foot":
        s = region[1]
        bones = ["foot_" + s, "ball_" + s, "calf_" + s]
        names, W = char.transfer_weights(ob, body, bones, limit=3)
        char.smooth_weights(ob, iterations=2, strength=0.5, limit=3, names=names, W=W)
        return
    if region and region[0] == "cuff":
        s = region[1]
        bones = [b % s for b in ("upperarm_%s", "upperarm_twist_01_%s", "upperarm_twist_02_%s", "lowerarm_%s",
                                 "lowerarm_twist_01_%s", "lowerarm_twist_02_%s")]
        names, W = char.transfer_weights(ob, body, bones, limit=4)
        char.smooth_weights(ob, iterations=3, strength=0.5, limit=4, names=names, W=W)
        return
    if region == "head":
        char.set_weights(ob, ["head"], np.ones((len(ob.data.vertices), 1)))
        return
    names, W = char.transfer_weights(ob, body, None, limit=6, apply=False)
    loose = {"Hood": 8, "Hoodie": 6, "Puffer": 5, "Sling": 8, "Drawstring": 6, "Pocket": 6}.get(name.split("_")[0], 4)
    char.set_weights(ob, names, W, limit=6)
    char.smooth_weights(ob, iterations=loose, strength=0.5, limit=6, names=names, W=W)


def assemble(man, outfit, parts, ctx):
    """Decimate, weights, UVs per set, join: returns (mesh object, {set: object before the join})."""
    log = ctx.log
    sets = {"cloth": [], "head": []}
    for i, (name, ob, set_name, region) in enumerate(parts):
        if region is None and name in ("Mask",):
            region = None
        weights(man, name, ob, region)
        a = ob.data.attributes.get("mi_piece")
        sets[set_name].append(ob)
    total = sum(tris(o) for o in sum(sets.values(), []))
    log("%s: %d pieces, %d triangles" % (outfit, len(parts), total))
    joined = {}
    for set_name, obs in sets.items():
        ob = geo.join([o for o in obs], "Goon%s_%s" % (outfit, set_name.capitalize()), man.col)
        ob.data.materials.clear()
        ob.data.materials.append(flat_materials(outfit)[set_name])
        ob.data.polygons.foreach_set("material_index", np.zeros(len(ob.data.polygons), dtype=np.int32))
        unwrap(ob)
        joined[set_name] = ob
    return joined


def unwrap(ob):
    me = ob.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name="UVMap")
    scene.select_only(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(62), island_margin=0.002, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin_method="FRACTION", margin=0.002, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")


def slot_name(outfit, set_name):
    return "M_Goon%s_%s" % (outfit, set_name.capitalize())


def set_name_of(outfit, set_name):
    return "Goon%s_%s" % (outfit, set_name.capitalize())


def flat_materials(outfit):
    out = {}
    for s, c in (("cloth", "#303034"), ("head", "#c8c0b0")):
        nm = slot_name(outfit, s)
        m = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Base Color"].default_value = (*srgb(c), 1)
        b.inputs["Roughness"].default_value = 0.8
        out[s] = m
    return out


def textured_material(outfit, s):
    """Preview material on a baked set (Unreal builds its own from the same maps)."""
    nm, sn = slot_name(outfit, s), set_name_of(outfit, s)
    d = paths.texture_set(sn)
    if not os.path.exists(os.path.join(d, "T_%s_BC.png" % sn)):
        return None
    m = bpy.data.materials.get(nm) or bpy.data.materials.new(nm)
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs["Surface"])

    def img(tag_, data):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(os.path.join(d, "T_%s_%s.png" % (sn, tag_)), check_existing=True)
        t.image.colorspace_settings.name = "Non-Color" if data else "sRGB"
        return t
    bc, nm_, orm = img("BC", False), img("N", True), img("ORM", True)
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    nt.links.new(bc.outputs["Color"], mix.inputs["A"])
    nt.links.new(sep.outputs["Red"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(sep.outputs["Green"], b.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], b.inputs["Metallic"])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nm_.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Sheen Weight"].default_value = 0.25
    b.inputs["Sheen Roughness"].default_value = 0.5
    return m


LAYERS = [  # (inner kinds, outer kinds, mode, reach m): inner layers under an outer one take its weights (they move as
    # one and cannot pass through each other); a trouser hem resting on the sneaker takes the sneaker's weights
    (("maskknit",), ("fleece", "beanie", "captwill", "bandana", "tricot", "quilt", "rib", "nylon"), "inner", 0.05),
    (("denim", "twill"), ("rib", "fleece", "quilt", "nylon"), "inner", 0.05),
    (("tricot",), ("rib", "quilt"), "inner", 0.03),
    (("leather",), ("rib", "fleece", "quilt", "nylon", "tricot"), "inner", 0.04),
    (("shoe", "sole", "sock"), ("denim", "twill", "tricot"), "outer", 0.03),
]


def _face_kinds(ob):
    a = np.empty(len(ob.data.polygons), dtype=np.float32)
    ob.data.attributes["mi_kind"].data.foreach_get("value", a)
    return np.rint(a).astype(int)


def layer_weights(ob, log=log_default):
    """Make covered layers share their cover's skin weights (see LAYERS)."""
    from mathutils.bvhtree import BVHTree
    me = ob.data
    names, W = char.weight_matrix(ob)
    W = W.copy()
    co = GC.verts(ob)
    fk = _face_kinds(ob)
    polys = [tuple(p.vertices) for p in me.polygons]
    vkind = {}
    for fi, p in enumerate(polys):
        for v in p:
            vkind.setdefault(v, set()).add(fk[fi])

    def verts_of(kinds):
        ids = {K[k] for k in kinds}
        return np.array([v for v, ks in vkind.items() if ks & ids], dtype=np.int64)

    def faces_of(kinds):
        ids = [K[k] for k in kinds]
        return np.nonzero(np.isin(fk, ids))[0]
    for inner, outer, mode, reach in LAYERS:
        src_f = faces_of(outer if mode == "inner" else inner)
        dst_v = verts_of(inner if mode == "inner" else outer)
        if not len(src_f) or not len(dst_v):
            continue
        bvh = BVHTree.FromPolygons([tuple(v) for v in co], [polys[i] for i in src_f])
        n = 0
        for v in dst_v:
            loc, nrm, fi, d = bvh.find_nearest(Vector(co[v]), reach)
            if loc is None:
                continue
            side = (Vector(co[v]) - loc).dot(nrm)
            if mode == "inner" and side > 0.002:
                continue                                   # not under the cover
            f = polys[src_f[fi]]
            P = co[list(f)]
            wts = 1.0 / np.maximum(np.linalg.norm(P - np.array(loc), axis=1), 1e-5)
            wts /= wts.sum()
            Wsrc = wts @ W[list(f)]
            t = float(np.clip(1.0 - (d - reach * 0.5) / (reach * 0.5), 0, 1))
            W[v] = W[v] * (1 - t) + Wsrc * t
            n += 1
        log("  layers %s -> %s: %d vertices share weights" % ("/".join(inner), "/".join(outer), n))
    char.set_weights(ob, names, W, limit=6)


def finish(man, outfit, joined, ctx):
    mats = flat_materials(outfit)
    for s, ob in joined.items():
        m = textured_material(outfit, s) or mats[s]
        ob.data.materials.clear()
        ob.data.materials.append(m)
        ob.data.polygons.foreach_set("material_index", np.zeros(len(ob.data.polygons), dtype=np.int32))
    ob = geo.join([joined["cloth"], joined["head"]], "SK_Goon_%s" % outfit, man.col)
    layer_weights(ob, ctx.log)
    rig.bind(ob, man.arm)
    ctx.log("SK_Goon_%s: %d triangles, %d vertices" % (outfit, tris(ob), len(ob.data.vertices)))
    return ob


BUILDERS = {"Hoodie": hoodie_outfit}


def build(ctx):
    man = Man(ctx)
    ctx.log("mannequin measured; head top %.3f, shoulders %.3f, hips %.3f" % (man.H.top, man.M.shoulder["l"][2],
                                                                              man.M.hip["l"][2]))
    want = [o for o in OUTFITS if not ctx.args.only or o.lower() in ctx.args.only]
    ctx.goons = {"man": man, "outfits": {}}
    objs = []
    for outfit in want:
        if outfit not in BUILDERS:
            continue
        sub = scene.collection("Goon_" + outfit)
        man.col = sub
        parts = kit(man, outfit)
        shoes = shoe_collider(man, parts)
        parts = BUILDERS[outfit](man, parts, shoes)
        joined = assemble(man, outfit, parts, ctx)
        if ctx.args.bake:
            from assets import _goons_tex as T
            for s, ob in joined.items():
                T.bake_set(ob, set_name_of(outfit, s), 4096 if s == "cloth" else 2048, man, ctx.log,
                           res_override=ctx.args.res if ctx.args.res != 2048 else None)
        ob = finish(man, outfit, joined, ctx)
        ctx.goons["outfits"][outfit] = ob
        objs.append(ob)
    man.col = ctx.col
    return objs


def on_export(ctx, objs):
    g = getattr(ctx, "goons", None)
    if not g:
        return
    for outfit, ob in g["outfits"].items():
        p = char.export_character(ob, g["man"].arm, name=ob.name)
        ctx.log("exported %s" % p)


def on_preview(ctx, objs):
    from assets import _goons_preview as P
    P.previews(ctx, objs)
