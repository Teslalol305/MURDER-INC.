"""The three Goons (briefs docs/unreal/spec/assets/characters.json goon_hoodie, goon_puffer, goon_tracksuit): one man on
the UE5 mannequin skeleton (SK_Mannequin) in three outfits, each one skinned mesh SK_Goon_<Outfit>.

    build.py build goons [--only hoodie,puffer,tracksuit] [--bake] [--export] [--preview]
    MI_PREVIEWS=goons_lineup,goons_hoodie_hero,goons_detail,goons_poses,goons_wire   (pictures to render)
    MI_GOONS_REDRAPE=1   ignore the drape cache (art/out/goons/cache_*.npz) and simulate again
    MI_GOONS_SETS=head   with --bake: bake only these sets (cloth, head; default both)

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
from assets import _goons_trim as TR

FAMILY = {"name": "goons", "description": "The three Goons on the UE5 mannequin skeleton (hoodie, puffer, tracksuit)"}

OUTFITS = ("Hoodie", "Puffer", "Tracksuit")
CACHE = os.path.join(paths.out, "goons")

# fabric kinds (face attribute mi_kind; assets/_goons_tex.py draws each)
K = dict(fleece=0, rib=1, denim=2, leather=3, shoe=4, sole=5, maskknit=6, quilt=7, nylon=8, twill=9, tricot=10,
         webbing=11, metal=12, cord=13, aglet=14, captwill=15, lens=16, bandana=17, sock=18, beanie=19, zip=20,
         skin=21, eye=22, plastic=23, tape=24)

# rebuild r2 colourways (art review: three distinct value blocks at 8 m, the oxblood crew mark as the shared tie):
# hoodie in charcoal-grey heather, puffer black nylon with oxblood yoke and much bulkier, tracksuit mid-value navy
# with bold white stripes; charcoal rib-knit balaclavas (base colour under linear 0.15), sneakers at albedo ~0.7.
# r3: oxblood as the brief means it (linear 0.12 / 0.02 / 0.025, r2's #7c151d read fire-engine red), the cuffs and
# beanie cuff darker still; balaclavas in heather knit at albedo 0.06-0.10, a different colour per Goon (hoodie dark
# olive, puffer charcoal, tracksuit dark navy; linear about 0.06, desaturated: at 0.08 the olive read as a pale green
# face in Unreal) instead of r2's near-black; face skin darker (only lids show)
COL = {"hoodie": "#56565b", "pocket": "#48484d", "oxblood": "#62272c", "darkox": "#451d21", "jeans": "#2f3646",
       "mask": "#444447", "mask_hoodie": "#46473b", "mask_puffer": "#444447", "mask_tracksuit": "#373c4e",
       "seam": "#3a3a3e", "slit": "#050506", "glove": "#1a1917", "upper": "#aca79c",
       "sole": "#b9b4a9", "jacket": "#26262b", "quiltseam": "#141416", "trousers": "#2b2c31", "track": "#1e2a4c",
       "black": "#141416", "metal": "#8a8a88", "webbing": "#1a1a1c", "sock": "#18181a", "lens": "#0b0a09",
       "skin": "#4a3327", "eye": "#9e968a", "bandana": "#36322d", "stripe": "#e6e3dc", "capblack": "#18181b",
       "frame": "#121212"}

# r2 budgets: the eye-catching cloth is refined (one subdivision + Taubin, see TR.refine) and decimated to more
# triangles than r1 (hood 6.5k -> 12k); each Goon stays under 120k
BUDGET = {"Hoodie": 26000, "Jeans": 15000, "Hood": 16000, "Waistband": 2400, "Cuff": 1300, "Pocket": 1400,
          "Mask": 9000, "Puffer": 30000, "Collar": 3200, "Trousers": 15000, "TrackJacket": 24000, "TrackTrousers": 15000,
          "Beanie": 2600, "BeanieCuff": 2900, "Cap": 3600, "Bandana": 3400, "Sock": 300, "Sling": 1300, "Skin": 3000}


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
    if ob.data.attributes.get("mi_loft") is None:              # quilt loft 0..1 (the puffer sets it), 0 elsewhere
        a = ob.data.attributes.new("mi_loft", "FLOAT", "POINT")
        a.data.foreach_set("value", np.zeros(len(ob.data.vertices), dtype=np.float32))
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
        g = cached("Glove_%s" % s, "g2", col, lambda: GK.glove(man.arm, man.body, s, col))
        out.append(("Glove_" + s, tag(g, "leather", "glove"), "cloth", ("glove", s)))
        sn, F = GK.sneaker(B, s, col)
        for k, o in sn.items():
            kind, colour = {"upper": ("shoe", "upper"), "sole": ("sole", "sole"), "eyelets": ("metal", "metal"),
                            "laces": ("cord", "upper"), "tab": ("shoe", "oxblood")}[k]
            out.append(("Sneaker_%s_%s" % (k, s), tag(o, kind, colour), "cloth" if k in ("upper", "sole") else "head",
                        ("foot", s)))
        sk = cached("Sock_%s" % s, "s1", col, lambda: GK.sock(man.BF, col, 1 if s == "l" else -1))
        GK.decimate(sk, BUDGET["Sock"])
        out.append(("Sock_" + s, tag(sk, "sock", "sock"), "cloth", ("leg", s)))
    return out


def shoe_collider(man, parts):
    obs = [p[1] for p in parts if p[0].startswith(("Sneaker_upper", "Sneaker_sole"))]
    return collider_of(obs, "Col_Shoes", man.work, ratio=0.6, inflate=0.003)


# ------------------------------------------------------------------------------------------------ hoodie outfit


def _copy(ob, col, name=None):
    c = ob.copy()
    c.data = ob.data.copy()
    c.name = name or ob.name
    col.objects.link(c)
    return c


def _head_set(man, bottom=1.45):
    """The balaclava (with its hems), the face skin and the eyes, built once per process (copies per outfit)."""
    if getattr(man, "_head", None) is None:
        mk, hems = GH.balaclava(man.H, man.work, bottom_z=bottom, neck=man.M.neck)
        GK.decimate(mk, BUDGET["Mask"])
        hem = geo.join(hems, "MaskHems", man.work)
        skin, eyes = GH.face_skin(man.H, man.work)
        GK.decimate(skin, BUDGET["Skin"])
        man._head = (mk, hem, skin, eyes)
        man.log("  balaclava %d tris, hems %d, face skin %d, eyes %d" % (tris(mk), tris(hem), tris(skin), tris(eyes)))
    return man._head


def mask_piece(man, bottom=1.45):
    return _copy(_head_set(man, bottom)[0], man.col, "Mask")


def head_pieces(man, parts, colour="mask"):
    """Balaclava, its rolled hems and eye tunnels, and what the openings show (lids, eyes) - all in the Head set."""
    mk, hem, skin, eyes = _head_set(man)
    m = _copy(mk, man.col, "Mask")
    parts.append(("Mask", tag(m, "maskknit", colour), "head", None))
    parts.append(("MaskHems", tag(_copy(hem, man.col), "maskknit", colour, 6), "head", None))
    parts.append(("FaceSkin", tag(_copy(skin, man.col), "skin", "skin"), "head", "head"))
    parts.append(("Eyes", tag(_copy(eyes, man.col), "eye", "eye"), "head", "head"))
    return m


def rib_bands(man, band_level, cuff_level, hem_top=0.925, band_bot=0.86, cuff=0.045, thick=0.0055):
    """Rib waistband and cuffs as closed double-walled tubes on the body (TR.axis_band): clean welded edges, never
    through unfold or thicken_edges (r1's level-set bands tore into ragged spikes at their cut edges)."""
    B, M, BF, col = man.B, man.M, man.BF, man.col
    out = {}
    zc = 0.5 * (band_bot + hem_top)
    a, fy, by = B.torso_at(zc)
    c0 = np.array([0.0, 0.5 * (fy + by), band_bot])
    out["waistband"] = TR.axis_band("Waistband", BF, band_level, c0, (0, 0, 1), 0.0, hem_top + 0.004 - band_bot,
                                    thick, col, nu=160, ns=10, ref=(0, -1.0, 0))
    for s in "lr":
        p2, n2 = GC.cuff_plane(M, s, -0.014)
        out["cuff_" + s] = TR.axis_band("Cuff_" + s, BF, cuff_level, p2, -M.fore[s], 0.0, cuff + 0.018, thick * 0.9,
                                        col, nu=64, ns=10, ref=(0, 0, 1.0), ease_top=0.003)
    return out


def cloth_piece(ob, budget, smooth_iters=4):
    """Refine (one subdivision + Taubin: the 10 mm drape facets round off, the folds stay), drop degenerate
    triangles, decimate to the budget."""
    TR.refine(ob, smooth_iters)
    TR.clean_degenerate(ob)
    GK.decimate(ob, budget)
    TR.clean_degenerate(ob)
    return ob


def sim_piece(ob, budget):
    """r3: a piece simulated at its final density (7 mm cells): no subdivision or Taubin pass after the drape (r2's
    refine rounded 10 mm facets into a stepped terminator in Unreal), only degenerate triangles out and a light
    decimation to the budget."""
    TR.clean_degenerate(ob)
    GK.decimate(ob, budget)
    TR.clean_degenerate(ob)
    return ob


def hood_piece(man, hoodie, mask, name="Hood", version="h9"):
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
        hd = cloth.garment_mesh("Hood", f, lo, hi, 0.0068, cuts=cuts, col=col, relax=4)      # r3: final density
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
        cloth.drape(hd, [mc, man.body_col], frames=36, pin=pin, shrink=grow, shrink_min=-0.04, bending=1.0,
                    mass=0.2, log=man.log)
        cloth.smooth(hd, 1)
        co = GC.verts(hd)
        face = max(cloth.boundary_loops(hd), key=lambda L: -co[L][:, 1].mean())
        face = max(cloth.boundary_loops(hd), key=lambda L: co[L][:, 2].mean())
        smooth_loop(hd, face, 14)
        co = GC.verts(hd)
        P = co[face]
        nrm = cloth.vertex_normals(hd)[face]
        # the drawstring channel: a rolled edge 11 mm thick, a little inside the opening
        path = P - nrm * 0.002
        path = np.vstack([path, path[:1]])
        rim = geo.pipe([tuple(v) for v in path], radius=0.0055, segments=8, cap=False, name="HoodRim")
        hd = geo.join([hd, rim], "Hood", col)
        return hd
    return cached(name, version, col, make)


def hoodie_outfit(man, parts, shoes):
    B, M, BF, col, log = man.B, man.M, man.BF, man.col, man.log
    jeans = cached("Jeans", "j2", col, lambda: GC.trousers(B, M, BF, col, [man.body_col, shoes], log=log, hem=0.115))
    TR.refine(jeans, 3)
    thicken_edges(jeans, depth=0.02, thickness=0.004, which=lambda P: P[:, 2].mean() < 0.3)
    TR.clean_degenerate(jeans)
    GK.decimate(jeans, BUDGET["Jeans"])
    parts.append(("Jeans", tag(jeans, "denim", "jeans"), "cloth", None))
    jc = collider_of([jeans], "Col_Jeans", man.work, ratio=0.5, inflate=0.002)

    def shell():
        # r3: simulated at the final density (7.5 mm), slimmer sleeves (r2's read as one balloon from shoulder to
        # elbow) and softer bending, so gravity folds form in the fleece instead of a smooth inflated skin
        ob, L = GC.hoodie_shell(B, M, BF, col, [man.body_col, jc], log=log, sleeve=0.014, grow=-0.035, ease=0.020,
                                band_level=0.022, cuff_level=0.012, bending=3.5, h=0.0075)
        cloth.smooth(ob, 1)
        return ob
    hoodie = cached("Hoodie", "hd6", col, shell)       # hd5 (bending 1.5) crumpled like thin jersey: fleece folds wider
    bands = rib_bands(man, band_level=0.022, cuff_level=0.012)
    for k, o in bands.items():
        parts.append((k.capitalize(), tag(o, "rib", "darkox"), "cloth", ("cuff", k[-1]) if k.startswith("cuff") else None))
    mask = head_pieces(man, parts, "mask_hoodie")
    hood = hood_piece(man, hoodie, mask)
    S = GK.Surface(hoodie)
    pocket = GK.panel("Pocket", S, [(-0.155, 0.945), (0.155, 0.945), (0.12, 1.16), (-0.12, 1.16)], col, lift=0.0065)
    cloth.smooth(pocket, 4)                 # r3: the finer drape's small folds poked through a pocket 4 mm off it
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
    sim_piece(hoodie, BUDGET["Hoodie"])
    sim_piece(hood, BUDGET["Hood"])
    parts.append(("Hoodie", tag(hoodie, "fleece", "hoodie"), "cloth", None))
    parts.append(("Hood", tag(hood, "fleece", "hoodie", 2), "cloth", None))
    sling(man, hoodie, parts)
    return parts


def sling(man, garment, parts):
    S = GK.Surface(garment)
    M = man.M
    ob, P, N = GK.strap_loop(S, M.shoulder["r"] + np.array([0.02, 0.06, 0.07]), M.hip["l"] + np.array([0.07, 0.0, -0.02]),
                             man.col)
    parts.append(("Sling", tag(ob, "webbing", "webbing"), "head", None))
    # a tri-glide adjuster on the chest and a second one low on the back (where the pipe's lower strap would sit)
    for score in (lambda Q: -Q[:, 1] - 3.0 * np.abs(Q[:, 2] - 1.24), lambda Q: Q[:, 1] - 3.0 * np.abs(Q[:, 2] - 1.08)):
        i = int(np.argmax(score(P)))
        t = P[(i + 1) % len(P)] - P[i - 1]
        bk = TR.buckle("SlingBuckle", P[i], t, N[i], man.col)
        parts.append(("SlingBuckle", tag(bk, "plastic", "frame"), "head", None))
    return ob


# ------------------------------------------------------------------------------------------------ puffer, tracksuit


def collar(man, garment, name, top, ease, flare, col, h=0.006):
    """Stand-up collar: an elliptic tube round the neck (the neck's own section grown by `ease`), from inside the
    garment's neckline up to `top` (metres above the ground), flaring `flare` at the top; turned edge on top.
    Returns (object, top z, field) - the field is the collar as a solid (for what lies over it)."""
    L, ring = ordered_ring(garment, lambda P: P[:, 2].mean())
    nk = man.M.neck
    rc = np.array([nk[0], nk[1] - 0.006, 0.0])
    zr = float(ring[:, 2].mean())
    bx = (ring[:, 0].max() - ring[:, 0].min()) / 2 + 0.004            # the garment's neckline
    by = (ring[:, 1].max() - ring[:, 1].min()) / 2 + 0.004
    rc0 = np.array([ring[:, 0].mean(), ring[:, 1].mean(), 0.0])
    ax_, ay_ = 0.060 + ease, 0.066 + ease                              # the neck grown by the ease
    z0 = zr - 0.02
    z1 = top

    def f(p):
        t = np.clip((p[:, 2] - z0) / (z1 - z0), 0, 1)
        b = 1 - np.clip((p[:, 2] - zr) / 0.045, 0, 1)
        b = b * b * (3 - 2 * b)                                          # from the neckline in to the neck
        k = 1.0 + flare * t ** 2 / min(ax_, ay_)
        A = (ax_ * k) * (1 - b) + bx * b
        Bq = (ay_ * k) * (1 - b) + by * b
        cx = rc[0] * (1 - b) + rc0[0] * b
        cy = (rc[1] - 0.006 * t) * (1 - b) + rc0[1] * b
        q = np.sqrt(((p[:, 0] - cx) / A) ** 2 + ((p[:, 1] - cy) / Bq) ** 2)
        return (q - 1.0) * np.minimum(A, Bq)
    lo = np.array([rc0[0] - bx - 0.05, rc0[1] - by - 0.05, z0 - 0.02])
    hi = np.array([rc0[0] + bx + 0.05, rc0[1] + by + 0.05, z1 + 0.02])
    ob = cloth.garment_mesh(name, f, lo, hi, h, cuts=[((0, 0, z1), (0, 0, 1)), ((0, 0, z0), (0, 0, -1))], col=col)
    thicken_edges(ob, depth=0.02, thickness=0.004, which=lambda P: P[:, 2].mean() > z0 + 0.01)

    def solid(p):
        return np.maximum(f(p), np.maximum(p[:, 2] - z1, z0 - p[:, 2]))
    return ob, z1, solid


def front_path(man, obs, z_top, length, step=0.006, lift=0.0):
    """Points and normals down the centre front of the given surfaces from z_top, `length` long (ray cast from the
    front at x = 0)."""
    S = GK.Surface(*obs)
    P, N = [], []
    for z in np.arange(z_top, z_top - length - 1e-9, -step):
        loc, n = S.ray((0.0, -0.6, z), (0, 1.0, 0), 1.2)
        if loc is None:
            continue
        if n[1] > 0:
            n = -n
        P.append(loc + n * lift)
        N.append(n)
    P, N = np.array(P[::-1]), np.array(N[::-1])
    for _ in range(4):
        P[1:-1] = 0.5 * P[1:-1] + 0.25 * (P[:-2] + P[2:])
    return P, N


def zipper(man, obs, z_top, length, parts, col, tape_kind="zip", tape_colour="oxblood"):
    P, N = front_path(man, obs, z_top, length, lift=0.0015)
    tapes, teeth = GK.zip_teeth("Zip", P, N, col)
    pull = GK.zip_pull("ZipPull", P[-1], N[-1], P[-1] - P[-2], col)
    parts.append(("ZipTape", tag(tapes, "nylon", tape_colour), "head", None))
    parts.append(("ZipTeeth", tag(teeth, "zip", tape_colour), "head", None))
    parts.append(("ZipPull", tag(pull, "metal", "metal"), "head", None))


def quilt(man, ob, seams_z, arm_rings, loft=0.013, sleeve_loft=1.0, power=0.6, sleeve_mask=None):
    """The puffer's loft: the shell pushed out along its normals between stitched seams (horizontal on the torso,
    rings on the sleeves), down to nothing on each seam line."""
    from assets._goons_tex import AxisCoords
    co = GC.verts(ob)
    n = cloth.vertex_normals(ob)
    ax = AxisCoords(man)(co)
    seg, s = ax[:, 0].astype(int), ax[:, 1]
    out = np.zeros(len(co))
    z = co[:, 2]
    sz = np.asarray(seams_z)
    k = np.clip(np.searchsorted(sz, z) - 1, 0, len(sz) - 2)
    t = (z - sz[k]) / (sz[k + 1] - sz[k])
    body = (seg == 0) if sleeve_mask is None else ~sleeve_mask    # r3: the box's own torso / sleeve split (the
    # nearest-axis test put the chest front on the upper arms: sleeve rings across the chest read as abs and pecs)
    torso = body & (z >= sz[0]) & (z <= sz[-1])
    out[torso] = np.sin(np.pi * np.clip(t[torso], 0, 1)) ** power
    above = body & (z > sz[-1])
    out[above] = 0.7 * np.sin(np.pi * np.clip((z[above] - sz[-1]) / 0.12, 0, 1)) ** power
    for side_segs, rings in ((("uarm_l", "farm_l"), arm_rings), (("uarm_r", "farm_r"), arm_rings)):
        ids = [AxisCoords(man).names.index(nm) for nm in side_segs]
        for sid, (r0, r1) in zip(ids, rings):
            m = (seg == sid) if sleeve_mask is None else ((seg == sid) & sleeve_mask)
            # r2: stitched rings every r1 of the segment's length (about 9 cm), offset r0; a baffle between
            sm = s[m]
            Ls = np.linalg.norm(AxisCoords(man).Bv[sid] - AxisCoords(man).A[sid])
            u = (sm / Ls - r0) / r1
            out[m] = sleeve_loft * np.sin(np.pi * np.mod(u, 1.0)) ** power
    GC.set_verts(ob, co + n * (loft * out)[:, None])
    return out


def binding(name, ob, which, radius, col):
    """A bound edge: a soft tube along the open loop(s) which(points) accepts."""
    co = GC.verts(ob)
    nrm = cloth.vertex_normals(ob)
    tubes = []
    for L in cloth.boundary_loops(ob):
        if not which(co[L]):
            continue
        P = co[L] - nrm[L] * radius * 0.3
        P = np.vstack([P, P[:1]])
        for _ in range(3):
            P[1:-1] = 0.5 * P[1:-1] + 0.25 * (P[:-2] + P[2:])
        tubes.append(geo.pipe([tuple(v) for v in P], radius=radius, segments=8, cap=False, name=name))
    return geo.join(tubes, name, col)


PUFFER_SEAMS = [0.885, 0.972, 1.059, 1.146, 1.233, 1.32, 1.405]     # 8.7 cm baffles (r1: 13 cm, a muscle suit)


def inflate_torso(man, ob, amount):
    """Boxier puffer: the torso pushed out along its normals by `amount` (fading out toward the neckline and the
    hem), more over the chest hollow and the small of the back so the front and back read as flat quilted panels
    instead of following the pecs and the stomach."""
    from assets._goons_tex import AxisCoords
    co = GC.verts(ob)
    n = cloth.vertex_normals(ob)
    ax = AxisCoords(man)(co)
    torso = (ax[:, 0] == 0).astype(float)
    z = co[:, 2]
    w = torso * np.clip((z - 0.87) / 0.05, 0, 1) * np.clip((1.47 - z) / 0.08, 0, 1)
    hol = np.exp(-((z - 1.13) / 0.09) ** 2) * (np.abs(co[:, 1]) > 0.05)
    bnd = cloth.boundary_vertices(ob)
    off = amount * w * (1 + 0.6 * hol)
    off[bnd] = 0
    GC.set_verts(ob, co + n * off[:, None])
    cloth.smooth(ob, 2)


def boxy_puffer(man, ob, front=0.060, side=0.050, back=0.050, sleeve_r=(0.082, 0.064), n=3.6, log=log_default):
    """r3: the puffer as its own boxy shell, not a skin over the body (the art review: r2's baffles followed the
    pecs, the abs and the deltoids, a muscle suit). The torso is set on one rounded-rectangle section (superellipse
    exponent n) from the hem to the chest: the body's widest half-width + `side`, its frontmost point + `front`, its
    backmost + `back`, the same at every height (a flat front, a hanging hem, no waist); above the chest it fades back
    to the draped shoulders. The sleeves become straight tubes round the arm axis, `sleeve_r` (shoulder, cuff)
    radius. Torso / sleeve weights are diffused over the mesh so the armholes blend without a crease."""
    from assets._goons_tex import AxisCoords
    B, J = man.B, man.B.J
    co = GC.verts(ob)
    zs = np.linspace(0.95, 1.36, 30)
    sec = np.array([B.torso_at(z) for z in zs])
    X = float(sec[:, 0].max()) + side
    yf = float(sec[:, 1].min()) - front
    yb = float(sec[:, 2].max()) + back
    cy, Y = 0.5 * (yf + yb), 0.5 * (yb - yf)
    # torso target: the vertex pushed along its horizontal direction from the section centre onto the superellipse
    d = co[:, :2] - np.array([0.0, cy])
    ang = np.arctan2(d[:, 1] / Y, d[:, 0] / X)
    c_, s_ = np.cos(ang), np.sin(ang)
    r = (np.abs(c_) ** n + np.abs(s_) ** n) ** (-1.0 / n)
    T = co.copy()
    T[:, 0] = r * c_ * X
    T[:, 1] = cy + r * s_ * Y
    T[:, 2] = co[:, 2]
    # sleeve target: a straight tube round the shoulder -> wrist axis
    ax = AxisCoords(man)(co)
    seg = ax[:, 0].astype(int)
    A = co.copy()
    warm = np.zeros(len(co))
    sleeve = np.zeros(len(co), dtype=bool)
    for sd in "lr":
        a0, w1 = J["upperarm_" + sd], J["hand_" + sd]
        w = w1 - a0
        L = np.linalg.norm(w)
        w = w / L
        t = np.clip((co - a0) @ w, 0, L)
        q = a0 + t[:, None] * w
        rv = co - q
        rr = np.linalg.norm(rv, axis=1)
        R = sleeve_r[0] + (sleeve_r[1] - sleeve_r[0]) * (t / L)
        # a sleeve point is nearest the arm AND outside the box's side wall (in the A-pose the upper-arm axis runs
        # close to the chest: the nearest-axis test alone put the front of the chest on the sleeve tubes, which
        # carved pecs and lats into the box)
        mine = np.isin(seg, [AxisCoords(man).names.index(nm) for nm in ("uarm_" + sd, "farm_" + sd)]) \
            & (np.abs(co[:, 0]) > X - 0.02) & (np.sign(co[:, 0]) == (1.0 if sd == "l" else -1.0))
        A[mine] = q[mine] + rv[mine] / np.maximum(rr[mine], 1e-6)[:, None] * R[mine, None]
        warm[mine] = 1.0
        sleeve |= mine
    # diffuse the sleeve weight over the mesh (a soft armhole), fade the box above the chest
    idx, ptr = char.adjacency(ob)
    deg = np.maximum(np.diff(ptr), 1).astype(np.float64)
    for _ in range(8):                                      # (25 steps bled the sleeve weight into the chest: the
        warm = 0.5 * warm + 0.5 * np.add.reduceat(warm[idx], ptr[:-1]) / deg      # pecs survived at its edges)
    wt = (1 - warm) * np.clip((1.49 - co[:, 2]) / 0.09, 0, 1)
    wa = warm
    disp = wt[:, None] * (T - co) + wa[:, None] * (A - co)
    for _ in range(6):                                      # no kinks where the targets meet
        disp = 0.5 * disp + 0.5 * np.add.reduceat(disp[idx], ptr[:-1], axis=0) / deg[:, None]
    GC.set_verts(ob, co + disp)
    cloth.smooth(ob, 2)
    log("  boxy puffer: section %.0f x %.0f cm (body + %.0f / %.0f / %.0f cm), sleeves %.0f -> %.0f mm radius" % (
        200 * X, 200 * Y, 100 * side, 100 * front, 100 * back, 1000 * sleeve_r[0], 1000 * sleeve_r[1]))
    return sleeve


def puffer_outfit(man, parts, shoes):
    B, M, BF, col, log = man.B, man.M, man.BF, man.col, man.log
    tr = cached("Trousers", "t1", col, lambda: GC.trousers(B, M, BF, col, [man.body_col, shoes], name="Trousers",
                                                           log=log, hem=0.115, ease_thigh=0.02, ease_shin=0.024))
    TR.refine(tr, 3)
    thicken_edges(tr, depth=0.02, thickness=0.004, which=lambda P: P[:, 2].mean() < 0.3)
    TR.clean_degenerate(tr)
    GK.decimate(tr, BUDGET["Trousers"])
    parts.append(("Trousers", tag(tr, "twill", "trousers"), "cloth", None))
    tc = collider_of([tr], "Col_Trousers", man.work, ratio=0.5, inflate=0.002)
    hem = 0.86

    def shell():
        ob, L = GC.hoodie_shell(B, M, BF, col, [man.body_col, tc], hem_top=hem, neck=1.53, cuff=0.02, ease=0.042,
                                hang=0.05, sleeve=0.024, grow=-0.02, band_level=0.034, cuff_level=0.024, log=log,
                                name="Puffer", bending=5.0, mass=0.35, frames=35)
        cloth.smooth(ob, 3)
        return ob
    # (r2 tried a looser drape, ease 0.062 / hang 0.085: the sleeves fused with the body in the start shape and the
    # shell tore; the bulk comes from inflate_torso and the deeper baffles instead)
    jk = cached("Puffer", "p4", col, shell)
    TR.refine(jk, 4)
    sleeve = boxy_puffer(man, jk, log=log)
    # straight horizontal baffles of constant height on the box, 4-5 rings per sleeve (12 cm), flatter crowns
    loft = quilt(man, jk, PUFFER_SEAMS, [(0.30, 0.42), (0.35, 0.42)], loft=0.017, sleeve_loft=0.6, power=0.4,
                 sleeve_mask=sleeve)
    at = jk.data.attributes.get("mi_loft") or jk.data.attributes.new("mi_loft", "FLOAT", "POINT")
    at.data.foreach_set("value", np.asarray(loft, dtype=np.float32))
    co_, z1, csolid = collar(man, jk, "Collar", man.H.chin_z + 0.004, 0.050, 0.012, col)
    TR.tidy_open_edges(co_)
    GK.decimate(co_, BUDGET["Collar"])
    parts.append(("Collar", tag(co_, "nylon", "jacket", 3), "cloth", None))
    hl = binding("HemBinding", jk, lambda P: P[:, 2].mean() < 1.0, 0.0065, col)
    parts.append(("HemBinding", tag(hl, "nylon", "darkox"), "cloth", None))
    cb = binding("CuffBinding", jk, lambda P: P[:, 2].mean() > 0.95 and abs(P[:, 0].mean()) > 0.3, 0.006, col)
    parts.append(("CuffBinding", tag(cb, "nylon", "jacket"), "cloth", None))
    zipper(man, [jk, co_], z1 - 0.004, 0.40, parts, col)
    TR.clean_degenerate(jk)
    GK.decimate(jk, BUDGET["Puffer"])
    TR.clean_degenerate(jk)
    parts.append(("Puffer", tag(jk, "quilt", "jacket", 3), "cloth", None))
    # head: balaclava under, beanie with its cuff, period wraparound sunglasses on the nose, bandana over nose and mouth
    head_pieces(man, parts, "mask_puffer")
    bn, cf = GH.beanie(man.H, col)
    GK.decimate(bn, BUDGET["Beanie"])
    GK.decimate(cf, BUDGET["BeanieCuff"])
    parts.append(("Beanie", tag(bn, "beanie", "black"), "head", "head"))
    parts.append(("BeanieCuff", tag(cf, "beanie", "darkox"), "head", "head"))
    lens, arms_, frame_ = glasses(man, col)
    parts.append(("Lens", tag(lens, "lens", "lens"), "head", "head"))
    parts.append(("GlassesArms", tag(arms_, "plastic", "frame"), "head", "head"))
    parts.append(("GlassesFrame", tag(frame_, "plastic", "frame"), "head", "head"))
    bd = cached("Bandana", "b9", col, lambda: bandana(man, csolid, col))
    GK.decimate(bd, BUDGET["Bandana"])
    parts.append(("Bandana", tag(bd, "bandana", "bandana"), "head", None))
    sling(man, jk, parts)
    return parts


def glasses(man, col, width=0.162, stand=0.0045):
    """Period (late-90s) wraparound sunglasses: one curved smoked shield resting on the nose bridge (`stand` off the
    knit there, more toward the temples as it wraps), bottom edge cut up over the nose, 2 mm thick, in a moulded
    black frame (a rim round the whole shield), temple arms back along the head to the ears.
    r3: slim 2000-era wraps (the art review: r2's 43 mm shield read as a goggle band, a domino mask): the shield 29 mm
    deep at the lenses, cut up 12 mm over the nose so it reads as two lenses, a 3.4 mm frame, 2.5 x 6 mm temples.
    Returns (lens, arms, frame)."""
    H = man.H
    j = H.j
    ez = H.eye["l"][2] + 0.0005
    mk = mask_piece(man)
    S = GK.Surface(mk)
    bpy.data.objects.remove(mk, do_unlink=True)
    cx, cy = j[0], j[1] + 0.01
    nu, nv = 41, 9
    V = []
    half = width / 2
    for i in range(nu):
        u = -1 + 2 * i / (nu - 1)
        x_t = u * half
        ang = np.arcsin(np.clip(u * 0.98, -1, 1)) * 1.12
        d = np.array([np.sin(ang), -np.cos(ang), 0.0])
        for k in range(nv):
            v = k / (nv - 1)
            top = ez + 0.0145 - 0.004 * u * u + 0.003 * np.exp(-(u * half / 0.012) ** 2)
            bot = ez - 0.0145 + 0.013 * np.exp(-(u * half / 0.013) ** 2) + 0.005 * u * u
            z = bot + (top - bot) * v
            loc, n = S.ray((cx + d[0] * 0.3, cy + d[1] * 0.3, z), -d, 0.4)
            r = np.linalg.norm((loc - np.array([cx, cy, z]))[:2]) if loc is not None else 0.1
            p = np.array([cx, cy, z]) + d * (r + stand + 0.009 * u * u)
            V.append(p)
    V = np.array(V)
    # even out the shield (no head bumps in a rigid lens)
    G = V.reshape(nu, nv, 3)
    for _ in range(6):
        G[1:-1] = 0.5 * G[1:-1] + 0.25 * (G[:-2] + G[2:])
    V = G.reshape(-1, 3)
    F = [(i * nv + k, i * nv + k + 1, (i + 1) * nv + k + 1, (i + 1) * nv + k) for i in range(nu - 1) for k in range(nv - 1)]
    lens = geo.from_arrays("GlassesLens", V, F, col, smooth=None)
    for p_ in lens.data.polygons:
        p_.use_smooth = True
    md = lens.modifiers.new("solid", "SOLIDIFY")
    md.thickness, md.offset = 0.0022, 0.0
    geo._apply_modifier(lens, md)
    arms = []
    for end in (0, nu - 1):
        a = G[end, nv // 2 + 1]
        sx = np.sign(a[0])
        pts = [a]
        for t in np.linspace(0.15, 1.0, 7):
            y = a[1] + t * (j[1] + 0.06 - a[1])
            loc, n = S.ray((sx * 0.3, y, a[2] - 0.006 * t), (-sx, 0, 0), 0.4)
            x = (loc[0] + sx * 0.004) if loc is not None else a[0]
            pts.append(np.array([x, y, a[2] - 0.006 * t]))
        arms.append(geo.sweep(geo.rect_profile(0.0025, 0.006), [tuple(p) for p in pts], name="Temple", up=(0, 0, 1)))
    ar = geo.join(arms, "GlassesArms", col)
    rim = np.vstack([G[:, nv - 1], G[nu - 1, ::-1][1:], G[::-1, 0][1:], G[0, :][1:]])
    for _ in range(2):
        rim = 0.5 * rim + 0.25 * (np.roll(rim, 1, axis=0) + np.roll(rim, -1, axis=0))
    rim = np.vstack([rim, rim[:1]])
    fr = geo.pipe([tuple(x) for x in rim], radius=0.0017, segments=8, cap=False, name="GlassesFrame")
    from mi import scene as _scene
    _scene.move_to(fr, col)
    return lens, ar, fr


def keep_big(v, quads, frac):
    """Keep every connected piece with at least `frac` of the largest piece's vertices."""
    n = len(v)
    parent = np.arange(n)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in sdf.edges_of_quads(quads):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    roots = np.array([find(i) for i in range(n)])
    cnt = np.bincount(roots)
    keep = cnt[roots] >= frac * cnt.max()
    remap = -np.ones(n, dtype=np.int64)
    remap[keep] = np.arange(int(keep.sum()))
    q = quads[keep[quads].all(axis=1)]
    return v[keep], remap[q]


def bandana(man, collar_solid, col):
    """A pale cotton bandana tied over the nose and mouth: 6 mm over the mask from the bridge of the nose down,
    round the sides to the knot at the nape, its front falling to a point over the collar onto the chest."""
    H, BF = man.H, man.BF
    j = H.j
    nose_z = H.eye["l"][2] - 0.028
    def f(p):
        low = p[:, 2] < H.chin_z - 0.045
        d = np.minimum(np.minimum(H(p) - GH.MASK_T - 0.0045, collar_solid(p) - 0.011),
                       np.where(low, BF(p) - 0.068, BF(p) + 0.03))
        # the flap: in front of the throat, a triangle narrowing from the jaw to a point 0.13 m below the chin
        zc = H.chin_z
        w = 0.095 * np.clip((p[:, 2] - (zc - 0.10)) / 0.10, 0, 1) ** 0.9
        flap = np.maximum(np.abs(p[:, 0]) - w, (p[:, 1] - (j[1] - 0.02)))
        flap_d = np.maximum(flap, -(p[:, 1] - (H.front + 0.02 - 0.09)) - 0.2)
        front_face = (j[1] - 0.05) - p[:, 1]
        band = np.maximum(d, p[:, 2] - nose_z - 0.012 * (p[:, 1] - H.front) / 0.2)
        # round the back only the tied band, 5 cm wide, from below the ears to the knot at the nape
        back = np.clip((p[:, 1] - (j[1] - 0.02)) / 0.04, 0, 1)
        band = np.maximum(band, np.where(back > 0, ((nose_z - 0.055) - p[:, 2]) - (1 - back) * 0.1, -1.0))
        # below the chin keep only the flap
        below = (zc + 0.015) - p[:, 2]
        band = np.where(below > 0, np.maximum(band, flap), band)
        return band
    lo = np.array([j[0] - 0.15, j[1] - 0.2, H.chin_z - 0.16])
    hi = np.array([j[0] + 0.15, j[1] + 0.16, nose_z + 0.03])
    v, q = sdf.surface_nets(f, lo, hi, 0.0028)
    v, q = keep_big(v, q, 0.15)
    v = cloth.safe_project(f, v, 3, 0.006)
    return sdf.to_mesh("Bandana", v, q, col)


def track_stripes(man, obs, parts, width=0.036):
    """Bold white stripe tape down the outside of each sleeve (shoulder, elbow, cuff) and each leg (hip to ankle),
    laid on the draped cloth by ray casts (TR.surface_strip): constant width over every fold."""
    J = man.B.J
    for sd, sx in (("l", 1.0), ("r", -1.0)):
        S = GK.Surface(obs["jacket"])
        path = [J["upperarm_" + sd] + np.array([sx * 0.03, 0, 0.02]), J["lowerarm_" + sd],
                J["hand_" + sd] - man.M.fore[sd] * 0.09]
        out = np.array([sx * 0.55, 0.0, 1.0])                   # the outer seam: up and out in the A-pose
        st = TR.surface_strip(S, path, out, width, man.col, name="Stripe_arm_" + sd)
        parts.append(("Stripe", tag(st, "tape", "stripe"), "cloth", None))
        S = GK.Surface(obs["trousers"])
        path = [J["thigh_" + sd] + np.array([0, 0, 0.06]), J["calf_" + sd], J["foot_" + sd] + np.array([0, 0, 0.07])]
        st = TR.surface_strip(S, path, np.array([sx, 0, 0.0]), width, man.col, name="Stripe_leg_" + sd)
        parts.append(("Stripe", tag(st, "tape", "stripe"), "cloth", None))


def unit_(v):
    v = np.asarray(v, dtype=np.float64)
    return v / max(np.linalg.norm(v), 1e-12)


def tracksuit_outfit(man, parts, shoes):
    B, M, BF, col, log = man.B, man.M, man.BF, man.col, man.log
    tr = cached("TrackTrousers", "tt3", col, lambda: GC.trousers(B, M, BF, col, [man.body_col, shoes],
                                                                 name="TrackTrousers", log=log, hem=0.12, ease_seat=0.015,
                                                                 ease_thigh=0.021, ease_shin=0.024, grow=-0.03))
    TR.refine(tr, 3)
    thicken_edges(tr, depth=0.02, thickness=0.004, which=lambda P: P[:, 2].mean() < 0.3)
    TR.clean_degenerate(tr)
    GK.decimate(tr, BUDGET["TrackTrousers"])
    parts.append(("TrackTrousers", tag(tr, "tricot", "track", 5), "cloth", None))
    tc = collider_of([tr], "Col_TrackTrousers", man.work, ratio=0.5, inflate=0.002)

    def shell():
        ob, L = GC.hoodie_shell(B, M, BF, col, [man.body_col, tc], hem_top=0.925, neck=1.535, ease=0.016, hang=0.022,
                                sleeve=0.014, grow=-0.03, band_level=0.017, cuff_level=0.011, log=log,
                                name="TrackJacket", bending=1.2, mass=0.25)
        cloth.smooth(ob, 2)
        return ob
    jk = cached("TrackJacket", "tj3", col, shell)
    cloth_piece(jk, BUDGET["TrackJacket"], smooth_iters=6)
    bands = rib_bands(man, band_level=0.017, cuff_level=0.011, thick=0.0045)
    for k, o in bands.items():
        parts.append((k.capitalize(), tag(o, "rib", "track"), "cloth", ("cuff", k[-1]) if k.startswith("cuff") else None))
    co_, z1, _s = collar(man, jk, "Collar", 1.59, 0.02, 0.006, col)
    TR.tidy_open_edges(co_)
    GK.decimate(co_, BUDGET["Collar"])
    parts.append(("Collar", tag(co_, "tricot", "track", 4), "cloth", None))
    zipper(man, [jk, co_], z1 - 0.003, 0.40, parts, col)
    track_stripes(man, {"jacket": jk, "trousers": tr}, parts)
    parts.append(("TrackJacket", tag(jk, "tricot", "track", 4), "cloth", None))
    head_pieces(man, parts, "mask_tracksuit")
    # r3: a fitted six-panel cap worn forward (r2's backwards cap read as a skullcap with a red tab): one solid black
    # crown (panel seams and eyelets in the normal map: piece 7), a stiff curved 7 cm brim shading the eyes (piece 8)
    cr, br, bt = GH.cap_forward(man.H, col)
    GK.decimate(cr, BUDGET["Cap"])
    parts.append(("Cap", tag(cr, "captwill", "capblack", 7), "head", "head"))
    parts.append(("CapBrim", tag(br, "captwill", "capblack", 8), "head", "head"))
    parts.append(("CapButton", tag(bt, "captwill", "oxblood", 8), "head", "head"))
    sling(man, jk, parts)
    return parts


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
        TR.clean_degenerate(ob)
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
        record_density(set_name_of(outfit, set_name), ob, log)
    return joined


DETAIL_TILE = 0.025          # metres per repeat of the tiling fibre normal (T_GoonFabric_Detail_N) in Unreal


def record_density(set_name, ob, log=log_default):
    """Metres per UV unit of a set (3D area over UV area) -> the detail normal's tiling, in art/out/goons/goons_ue.json
    (packed with the meshes; mi_chars.setup_goons reads it)."""
    me = ob.data
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    co = GC.verts(ob)
    lv = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", lv)
    a3 = auv = 0.0
    for p in me.polygons:
        ls = range(p.loop_start, p.loop_start + p.loop_total)
        P = co[[lv[i] for i in ls]]
        U = uv[list(ls)]
        for k in range(1, len(P) - 1):
            a3 += 0.5 * np.linalg.norm(np.cross(P[k] - P[0], P[k + 1] - P[0]))
            d1, d2 = U[k] - U[0], U[k + 1] - U[0]
            auv += 0.5 * abs(d1[0] * d2[1] - d1[1] * d2[0])
    m_per_uv = float(np.sqrt(a3 / max(auv, 1e-12)))
    path = os.path.join(CACHE, "goons_ue.json")
    data = json.load(open(path)) if os.path.exists(path) else {}
    data[set_name] = {"m_per_uv": round(m_per_uv, 4), "detail_tiling": round(m_per_uv / DETAIL_TILE, 2),
                      "uv_coverage": round(auv, 4), "area_m2": round(a3, 4)}
    json.dump(data, open(path, "w"), indent=1)
    log("  %s: %.3f m per UV unit (%.2f mm per texel at %d), UV coverage %.2f, detail tiling %.1f" % (
        set_name, m_per_uv, 1000 * m_per_uv / (4096 if set_name.endswith("Cloth") else 2048),
        4096 if set_name.endswith("Cloth") else 2048, auv, m_per_uv / DETAIL_TILE))


def _uv_key(ob):
    import hashlib
    co, lt, ls = _mesh_arrays(ob)
    h = hashlib.sha1()
    h.update(np.round(co, 4).astype(np.float32).tobytes())
    h.update(lt.tobytes())
    return h.hexdigest()[:16]


def unwrap(ob):
    """Smart projection (islands of the draped cloth at up to 72 deg), packed; the layout is cached by mesh hash in
    art/out/goons/uv_<name>.npz because smart projection is not reproducible between processes (and the baked sets
    must keep matching their UVs)."""
    path = os.path.join(CACHE, "uv_%s.npz" % ob.name)
    key = _uv_key(ob)
    me = ob.data
    if os.path.exists(path):
        z = np.load(path)
        if str(z["key"]) == key:
            while me.uv_layers:
                me.uv_layers.remove(me.uv_layers[0])
            uv = me.uv_layers.new(name="UVMap")
            uv.data.foreach_set("uv", z["uv"].ravel())
            return
    _unwrap(ob)
    a = np.empty(len(me.loops) * 2, dtype=np.float32)
    me.uv_layers[0].data.foreach_get("uv", a)
    np.savez_compressed(path, uv=a.reshape(-1, 2), key=np.array(key))


def _unwrap(ob):
    me = ob.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name="UVMap")
    scene.select_only(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(72), island_margin=0.002, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(rotate=True, margin_method="FRACTION", margin=0.002, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")
    # r3: r2's Head sets had islands packed over each other (the tracksuit cap crown half oxblood from the brim's
    # island, black 'V' strokes of the sling on the mask): check, and re-pack as convex hulls, then boxes, if so
    for shape in ("CONVEX", "AABB"):
        ov = uv_overlap(ob)
        log_default("  uv %s: %.3f %% of the packed texels claimed by two islands" % (ob.name, 100 * ov))
        if ov < 0.0005:
            break
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(rotate=True, margin_method="FRACTION", margin=0.003, shape_method=shape)
        bpy.ops.object.mode_set(mode="OBJECT")


def uv_overlap(ob, res=1024):
    """Fraction of covered texels (res x res) that triangles of two different UV islands both cover."""
    me = ob.data
    nl = len(me.loops)
    uv = np.empty(nl * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    lv = np.empty(nl, dtype=np.int64)
    me.loops.foreach_get("vertex_index", lv)
    ls = np.empty(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get("loop_total", lt)
    # islands: loops that share a vertex and (nearly) the same UV are one point; faces joined through such points
    key = np.unique(np.stack([lv, np.round(uv[:, 0] * 2e5), np.round(uv[:, 1] * 2e5)], 1), axis=0,
                    return_inverse=True)[1].ravel()
    parent = np.arange(key.max() + 1)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for s0, t in zip(ls, lt):
        r0 = find(key[s0])
        for i in range(s0 + 1, s0 + t):
            r1 = find(key[i])
            if r1 != r0:
                parent[r1] = r0
    isl = np.array([find(key[s0]) for s0 in ls])
    owner = np.full(res * res, -1, dtype=np.int64)
    clash = np.zeros(res * res, dtype=bool)
    tri = [(s0, s0 + i, s0 + i + 1, f) for f, (s0, t) in enumerate(zip(ls, lt)) for i in range(1, t - 1)]
    tri = np.array(tri, dtype=np.int64)
    A, B, C = uv[tri[:, 0]], uv[tri[:, 1]], uv[tri[:, 2]]
    fi = isl[tri[:, 3]]
    g = np.linspace(0.05, 0.95, 7)
    bw = np.array([(a, b) for a in g for b in g if a + b < 0.97])
    for a, b in bw:
        P = A + (B - A) * a + (C - A) * b
        cell = (np.clip(P[:, 1], 0, 0.9999) * res).astype(np.int64) * res + (np.clip(P[:, 0], 0, 0.9999) * res).astype(np.int64)
        o = owner[cell]
        clash[cell[(o >= 0) & (o != fi)]] = True
        owner[cell] = np.where(o < 0, fi, o)
    cov = (owner >= 0).sum()
    return float(clash.sum() / max(cov, 1))


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
    # as M_Goon* in Unreal (Cloth shading model): fuzz = saturate((roughness - 0.55) x 3.3) x 0.8, specular 0.35
    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation, m1.use_clamp = "MULTIPLY_ADD", True
    nt.links.new(sep.outputs["Green"], m1.inputs[0])
    m1.inputs[1].default_value, m1.inputs[2].default_value = 3.3, -0.55 * 3.3
    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    nt.links.new(m1.outputs[0], m2.inputs[0])
    m2.inputs[1].default_value = 0.8
    nt.links.new(m2.outputs[0], b.inputs["Sheen Weight"])
    b.inputs["Sheen Roughness"].default_value = 0.5
    nt.links.new(mix.outputs["Result"], b.inputs["Sheen Tint"])
    b.inputs["Specular IOR Level"].default_value = 0.35
    return m


LAYERS = [  # (inner kinds, outer kinds, mode, reach m): inner layers under an outer one take its weights (they move as
    # one and cannot pass through each other); a trouser hem resting on the sneaker takes the sneaker's weights
    (("maskknit",), ("fleece", "beanie", "captwill", "bandana", "tricot", "quilt", "rib", "nylon"), "inner", 0.05),
    (("denim", "twill"), ("rib", "fleece", "quilt", "nylon"), "inner", 0.05),
    (("tricot",), ("rib", "quilt"), "inner", 0.03),
    (("leather",), ("rib", "fleece", "quilt", "nylon", "tricot"), "inner", 0.04),
    (("shoe", "sole", "sock"), ("denim", "twill", "tricot"), "outer", 0.03),
    (("skin",), ("maskknit",), "inner", 0.02),
    (("tricot",), ("tape",), "outer", 0.03),
    (("webbing",), ("plastic",), "outer", 0.02),
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
    # a vertex left without any influence (a piece far from every source triangle of its bones) takes the weights
    # of its nearest weighted vertex: the exporter cannot write an unweighted vertex on this skeleton
    W = np.nan_to_num(W, nan=0.0, posinf=0.0, neginf=0.0)
    W[W < 0] = 0.0
    zero = W.max(axis=1) < 0.02
    if zero.any():
        from mathutils.kdtree import KDTree
        good = np.nonzero(~zero)[0]
        kd = KDTree(len(good))
        for k, i in enumerate(good):
            kd.insert(co[i], k)
        kd.balance()
        for i in np.nonzero(zero)[0]:
            _p, k, _d = kd.find(co[i])
            W[i] = W[good[k]]
        log("  %d unweighted vertices given their neighbour's weights" % int(zero.sum()))
    char.set_weights(ob, names, W, limit=6)
    n2, W2 = char.weight_matrix(ob)
    left = int((W2.sum(axis=1) < 0.5).sum())
    if left:
        raise RuntimeError("%s: %d vertices still without weights" % (ob.name, left))


def unfold(ob, kinds_skip=("metal", "zip", "lens", "shoe", "sole", "cord", "aglet", "webbing", "rib", "eye", "plastic",
                           "tape", "skin"), iters=160, log=log_default):
    """Smooth out folded-over triangles: where the drape crumpled or the decimation folded the cloth, a face points
    away from its corners' smooth normals and renders as a dark jagged patch in Unreal (Cycles hides it). Only the
    vertices of such faces and their neighbours move (Laplacian steps), topology and UVs stay."""
    me = ob.data
    fk = _face_kinds(ob)
    skip = np.isin(fk, [K[k] for k in kinds_skip])
    nl = np.array([p.loop_total for p in me.polygons])
    lv = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", lv)
    pi = np.repeat(np.arange(len(me.polygons)), nl)
    fixed = np.zeros(len(me.vertices), dtype=bool)
    fixed[np.unique(lv[skip[pi]])] = True
    fixed |= cloth.boundary_vertices(ob)
    idx, ptr = char.adjacency(ob)
    deg = np.maximum(np.diff(ptr), 1).astype(np.float64)
    co = GC.verts(ob)
    first = None
    for it in range(iters):
        GC.set_verts(ob, co)
        me.update()
        fn = np.empty(len(me.polygons) * 3)
        me.polygons.foreach_get("normal", fn)
        fn = fn.reshape(-1, 3)
        vn = cloth.vertex_normals(ob)
        d = np.einsum("ij,ij->i", vn[lv], fn[pi])
        badf = np.zeros(len(me.polygons), dtype=bool)
        np.logical_or.at(badf, pi, d < 0.35)
        badf &= ~skip
        if first is None:
            first = int(badf.sum())
        if not badf.any():
            break
        move = np.zeros(len(co), dtype=bool)
        move[lv[badf[pi]]] = True
        # grow one ring so the fix blends in
        ring = np.zeros(len(co), dtype=bool)
        for v in np.nonzero(move)[0]:
            ring[idx[ptr[v]:ptr[v + 1]]] = True
        move = (move | ring) & ~fixed
        mean = np.add.reduceat(co[idx], ptr[:-1], axis=0) / deg[:, None]
        co[move] += 0.6 * (mean[move] - co[move])
    GC.set_verts(ob, co)
    me.update()
    kinds = {k: int((badf & (fk == v)).sum()) for k, v in K.items() if (badf & (fk == v)).any()}
    # what is left is mostly real creases (turned hems, rolled edges, the pocket's edge): split the normals there
    # so they shade as edges instead of a smeared dark band
    e = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    fn = np.empty(len(me.polygons) * 3)
    me.polygons.foreach_get("normal", fn)
    fn = fn.reshape(-1, 3)
    ek = {}
    for f in me.polygons:
        for a_, b_ in f.edge_keys:
            ek.setdefault((min(a_, b_), max(a_, b_)), []).append(f.index)
    sharp = np.zeros(len(e), dtype=bool)
    for i, (a_, b_) in enumerate(e):
        fs = ek.get((min(a_, b_), max(a_, b_)), [])
        # r2: only between two faces that agree with their corners (a hem's turn); an edge of a folded-over face
        # stays smooth, so the exported normals shade it as the cloth around it (Unreal no longer recomputes them)
        if len(fs) == 2 and fn[fs[0]] @ fn[fs[1]] < 0.2 and not (badf[fs[0]] or badf[fs[1]]):
            sharp[i] = True
    at = me.attributes.get("sharp_edge") or me.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    at.data.foreach_set("value", sharp)
    me.update()
    log("  unfold %s: %d folded faces -> %d %s; %d crease edges split" % (ob.name, first or 0, int(badf.sum()), kinds,
                                                                         int(sharp.sum())))


def tuck_socks(ob, log=log_default, top=0.115, depth=0.007):
    """The sock inside the sneaker is pulled in 7 mm below the shoe's collar (after the bake: UVs and texels stay):
    in r1/r2 it pierced the upper in poses and showed as a dark swoosh-like patch on the side of the shoe."""
    fk = _face_kinds(ob)
    me = ob.data
    lv = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", lv)
    nl = np.array([p.loop_total for p in me.polygons])
    pi = np.repeat(np.arange(len(me.polygons)), nl)
    sock = np.zeros(len(me.vertices), dtype=bool)
    sock[lv[(fk == K["sock"])[pi]]] = True
    co = GC.verts(ob)
    n = cloth.vertex_normals(ob)
    w = sock * np.clip((top - co[:, 2]) / 0.02, 0, 1)
    GC.set_verts(ob, co - n * (depth * w)[:, None])
    log("  socks tucked: %d vertices" % int((w > 0).sum()))


def finish(man, outfit, joined, ctx):
    mats = flat_materials(outfit)
    for s, ob in joined.items():
        m = textured_material(outfit, s) or mats[s]
        ob.data.materials.clear()
        ob.data.materials.append(m)
        ob.data.polygons.foreach_set("material_index", np.zeros(len(ob.data.polygons), dtype=np.int32))
    ob = geo.join([joined["cloth"], joined["head"]], "SK_Goon_%s" % outfit, man.col)
    tuck_socks(ob, ctx.log)
    layer_weights(ob, ctx.log)
    unfold(ob, log=ctx.log)
    bad = ob.data.validate(clean_customdata=False)
    if bad:
        ctx.log("  %s: mesh validation corrected geometry" % ob.name)
    rig.bind(ob, man.arm)
    ctx.log("SK_Goon_%s: %d triangles, %d vertices" % (outfit, tris(ob), len(ob.data.vertices)))
    return ob


BUILDERS = {"Hoodie": hoodie_outfit, "Puffer": puffer_outfit, "Tracksuit": tracksuit_outfit}


def build(ctx):
    man = Man(ctx)
    ctx.log("mannequin measured; head top %.3f, shoulders %.3f, hips %.3f" % (man.H.top, man.M.shoulder["l"][2],
                                                                              man.M.hip["l"][2]))
    want = [o for o in OUTFITS if not ctx.args.only or o.lower() in ctx.args.only]
    if ctx.args.bake:
        from assets import _goons_tex as T
        path, tilt = T.detail_normal()
        ctx.log("detail normal %s (mean tilt %.1f deg)" % (path, tilt))
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
            only_sets = os.environ.get("MI_GOONS_SETS", "cloth,head").split(",")   # e.g. head: re-bake the Head sets
            for s, ob in joined.items():
                if s not in only_sets:
                    continue
                T.bake_set(ob, set_name_of(outfit, s), 4096 if s == "cloth" else 2048, man, ctx.log,
                           res_override=ctx.args.res if ctx.args.res != 2048 else None,
                           others=[o for k, o in joined.items() if k != s])
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
