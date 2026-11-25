"""RATTLER: the Goons' compact submachine gun in the player's hands, skinned for the Unreal import, with its stick magazine and the
visible top round.

The owner's report on the loadout was "all the guns look the same". The RATTLER is the sixth gun, hidden from the rack until
its mesh existed (docs/unreal/LOADOUT.md 3.2.2, 6): our own design in the manner of a class of firearm, an open-bolt 9 mm
submachine gun with a stamped sheet-steel box, a round ventilated shroud with a tan strap wrap, a slotted muzzle device, a long
straight stick magazine ahead of the pistol grip and a wire stock folded along the left side. It keeps the Goon SMG's identity
(stamped box, stick magazine, slotted muzzle device) at first-person grade.

Assets (art/out/glb, textures in art/out/textures):
    SK_Rattler                          skinned, bones body (root), bolt, trigger, selector, magazine (attach), stock, MuzzleDevice,
                                        IronsFront, IronsRear + the 10 socket bones of the contract (_weapons_rattler.RT);
                                        one slot M_Rattler = the unique 4K set 'Rattler' (BC, N, ORM; nothing emissive)
    SM_Weapon_RattlerMagazine (+ _TopRound)   static, in place (origin = gun origin), slot M_Weapon_RattlerMagazine = the unique
                                        2K set 'Weapon_RattlerMagazine'
    TS_GunDetail_Steel                  the tiling micro detail (20 mm); repeat per UV in the manifest

    build.py build weapons_rattler --bake --export             # everything (4K bake about 30 min on 1 thread, run it with nice)
    build.py build weapons_rattler --bake --res 1024           # draft sets
    build.py build weapons_rattler --only gun|mag [--bake] [--export]
    MI_PREVIEWS=weapons_rattler_hero,... build.py build weapons_rattler --preview --only none      # pictures from the exported files

Geometry: _weapons_rattler.py (contract, receiver, rail, shroud, barrel, muzzle device, sights) and _weapons_rattler_b.py (grip,
trigger group, bolt, selector, wire stock, wrap, magazine, rig); surfaces: _weapons_rattler_tex.py; pictures:
_weapons_rattler_prev.py; proof: _weapons_check_rattler.py.
"""
import json
import os

import bpy
import numpy as np

from mi import bake, export, geo, mat, paths, rig, scene
from assets import weapons as W
from assets import _weapons_rattler as S
from assets import _weapons_rattler_b as B
from assets import _weapons_tex as TX

FAMILY = {"name": "weapons_rattler", "description": "RATTLER submachine gun: SK_Rattler, its magazine and top round"}
scene.THREADS = 1                    # this machine is shared: one thread for renders and bakes

RES = {"SK_Rattler": 4096, "SM_Weapon_RattlerMagazine": 2048}
SKINNED = {}


def tex_res(ctx, name):
    """4096 for the gun and 2048 for the magazine at --res >= 2048; smaller --res gives draft sets (1/4096 of the gun's size per px
    of --res); MI_TEXRES=2048 forces a 2048 gun set (1024 magazine) whatever --res says."""
    full = RES[name]
    forced = os.environ.get("MI_TEXRES")
    if forced:
        return max(128, full * int(forced) // 4096)
    return full if ctx.args.res >= 2048 else max(128, full * ctx.args.res // 4096)


# ------------------------------------------------------------------------------------------------------- UV weights

def uv_weights(ob):
    """Per-face UV scale (texel density weights): 1.0 (7,000 px/m at 4096) on the receiver's flanks and cover, the top handle, the rear
    sight and the ribs, 0.86 (6,000) on the grip, the shroud's outside and the strap, 0.57 (4,000) on the muzzle device, the stock
    wires, the magazine well and the guard, 0.3-0.5 on interiors, the barrel inside the shroud and the undersides."""
    me = ob.data
    n = len(me.polygons)

    def attr(name):
        v = np.empty(n, np.float32)
        me.attributes[name].data.foreach_get("value", v)
        return np.rint(v).astype(int)
    mid, bid = attr("mid"), attr("bid")
    c = np.empty(n * 3, np.float32)
    me.polygons.foreach_get("center", c)
    c = c.reshape(-1, 3) / S.MM
    nr = np.empty(n * 3, np.float32)
    me.polygons.foreach_get("normal", nr)
    nr = nr.reshape(-1, 3)
    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    r = np.hypot(y, z)
    w = np.full(n, 0.60, np.float32)
    rec = (mid == S.SHEET) & (bid == 0) & (x > -3.0) & (x < 270.5) & (np.abs(y) < 23.6) & (z > -42.5) & (z < 31.0)
    w[rec] = 1.0
    w[rec & (nr[:, 2] < -0.7)] = 0.60                                                  # the floor
    w[rec & (np.abs(nr[:, 0]) > 0.7)] = 0.55                                           # front and rear plates
    w[rec & (y > 18.0)] = 0.88                                                         # the left flank (the camera sees the right)
    w[(mid == S.SHEET) & (bid == 0) & (z > 29.5)] = 1.0                                # cover top, rail, seam
    w[(mid == S.BLACK) & (bid == 1) & (z > 30.0)] = 1.0                                # the top handle
    w[(mid == S.INNER) & (bid == 0) & (x < 270.5) & (np.abs(y) < 21.5) & (z > -41.5) & (z < 29.5)] = 0.30   # the receiver's inside
    w[(mid == S.INNER) & (bid == 0) & (x > 196.0) & (r < 14.0)] = 0.55                 # the breech seen through the port
    w[(mid == S.INNER) & (bid == 1)] = 0.75                                            # the bolt body seen through the port
    w[bid == 8] = 1.0                                                                  # the rear sight leaf
    w[(bid == 0) & (mid == S.BLACK) & (x < 30.0) & (z > 29.0)] = 0.95                  # its base
    w[(bid == 0) & (mid == S.POLY)] = 0.86                                             # the grip
    w[(bid == 0) & (mid == S.POLY) & (nr[:, 2] < -0.7)] = 0.60
    shroud = (bid == 0) & (mid == S.BLACK) & (x > 269.0) & (x < 411.0) & (r > 21.0) & (r < 28.0)
    w[shroud] = 0.86
    w[shroud & (r < 24.6)] = 0.30                                                      # the tube's inside
    w[(bid == 0) & (mid == S.STRAP)] = 0.86
    w[(bid == 0) & (mid == S.BLACK) & (x > 270.0) & (x < 420.0) & (r < 14.0)] = 0.40   # the barrel inside the shroud
    w[(bid == 0) & (mid == S.BLACK) & (x >= 408.0) & (r < 10.0) & (x < 425.0)] = 0.55  # the stub
    w[(bid == 0) & (mid == S.BLACK) & (x >= 197.0) & (x < 271.0) & (r < 14.0)] = 0.55  # the breech inside the receiver
    w[bid == 6] = 0.57                                                                 # the muzzle device
    w[(bid == 6) & (r < 14.0) & (mid == S.BORE)] = 0.30
    w[bid == 7] = 0.86                                                                 # the front sight
    w[bid == 5] = 0.57                                                                 # the wire stock
    w[(bid == 5) & (x > 240.0)] = 0.75                                                 # the butt plate
    w[(bid == 0) & (mid == S.SHEET) & (z < -40.0) & (x > 140.0) & (x < 191.0)] = 0.57  # the magazine well
    w[(bid == 0) & (mid == S.SHEET) & (z < -44.0) & (x < 150.0) & (x > 80.0)] = 0.57   # the guard
    w[bid == 2] = 0.80                                                                 # the trigger
    w[bid == 3] = 0.95                                                                 # the selector
    w[mid == S.BORE] = 0.30                                                            # interiors
    return w


# ------------------------------------------------------------------------------------------------------ UV cache

def mesh_key(ob, extra=""):
    """Hash of the mesh's geometry and topology (positions to 0.01 mm, loop counts): the cache key of its UV layout."""
    import hashlib
    co, _n = geo.arrays(ob)
    lt = np.empty(len(ob.data.polygons), np.int32)
    ob.data.polygons.foreach_get("loop_total", lt)
    h = hashlib.sha1(np.round(co * 1e5).astype(np.int64).tobytes())
    h.update(lt.tobytes())
    h.update(extra.encode())
    return h.hexdigest()[:20]


def unwrap_cached(ctx, ob, set_name, res, weights, angle=66.0, margin_px=4, pack="CONVEX"):
    """Smart projection is not reproducible between processes, so the layout a set was painted on is kept in
    art/out/textures/<Set>/uv_cache.npz (keyed by the mesh hash and the packing) and reused until the mesh changes: a preview or a
    re-export in a later process then matches the baked textures."""
    path = os.path.join(paths.texture_set(set_name), "uv_cache.npz")
    key = mesh_key(ob, "%s|%s|%s" % (pack, angle, round(float(np.sum(weights)), 2)))
    me = ob.data
    if os.path.exists(path) and not ctx.args.force:
        z = np.load(path)
        if str(z["key"]) == key and len(z["uv"]) == len(me.loops) * 2:
            if not me.uv_layers:
                me.uv_layers.new(name=geo.UV)
            me.uv_layers.active.data.foreach_set("uv", z["uv"])
            me.update()
            ctx.log("%s: UV layout from the cache" % ob.name)
            return geo.uv_texel_density(ob, res, faces=weights >= np.max(weights) - 1e-6)
    dens = geo.uv_unwrap(ob, res=res, angle=angle, margin_px=margin_px, pack=pack, weights=weights)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get("uv", uv)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez(path, key=key, uv=uv)
    return dens


# ------------------------------------------------------------------------------------------------------ texture

def texture(ctx, ob, painter, res, set_name):
    """As weapons.texture: bake the geometry maps, author the channels, write the set (only with --bake when the set is missing or
    stale), then give the object its baked material M_<Set>. With MI_GCACHE=1 the geometry maps of a 4K bake are kept in
    art/out/textures/<Set>/gmaps_<res>.npz (keyed by the mesh and its UV layout) so that a later run that only changes the painter
    skips the ~10 minute map bake; delete the file when done (about 1 GB)."""
    from mi import texpaint as tp
    d = paths.texture_set(set_name)
    old = bake.read_set(set_name)
    uvh = geo.uv_hash(ob)
    stale = not old or old.get("uv_hash") != uvh or old.get("resolution", [0])[0] != res
    if ctx.args.bake and (stale or ctx.args.force or ctx.args.rebake_unique) or not old:
        ctx.log("texture %s at %d px" % (set_name, res))
        cache = os.path.join(d, "gmaps_%d.npz" % res)
        key = mesh_key(ob, uvh)
        G = None
        if os.environ.get("MI_GCACHE") and os.path.exists(cache):
            z = np.load(cache, allow_pickle=False)
            if str(z["__key"]) == key:
                G = {k: z[k] for k in z.files if k != "__key"}
                G["m_px"] = float(G["m_px"])
                G["res"] = int(G["res"])
                ctx.log("  geometry maps from the cache")
        if G is None:
            G = tp.geometry_maps(ob, res=res, samples=8 if res >= 2048 else 16)
            if os.environ.get("MI_GCACHE"):
                np.savez(cache, __key=key, **{k: np.asarray(v) for k, v in G.items()})
        ch = painter(G)
        dens = geo.uv_texel_density(ob, res)
        bake.write_set(set_name, ch, meta={"kind": "unique", "asset": ob.name, "uv_hash": uvh,
                                           "texel_density_px_per_m": round(dens, 1),
                                           "authoring": "mi.texpaint: geometry maps + numpy layers (assets/_weapons_rattler_tex.py)"})
        ctx.log("  wrote %s (%.0f px/m)" % (d, dens))
    elif stale:
        ctx.log("WARNING %s: set is stale (mesh changed); run with --bake" % set_name)
    m = mat.from_texture_set(d, name="M_" + set_name, masks=False, macro=0.0, ao_strength=0.0, alpha="none")
    ob.data.materials.clear()
    ob.data.materials.append(m)
    if set_name not in ctx.sets:
        ctx.sets.append(set_name)
    return m


# ---------------------------------------------------------------------------------------------------------- build

def build_gun(ctx):
    from assets import _weapons_rattler_tex as T
    res = tex_res(ctx, "SK_Rattler")
    gun, arm = B.rattler_build(ctx)
    ctx.log("SK_Rattler: %d tris, %d verts, %d bones" % (geo.stats(gun)["triangles"], geo.stats(gun)["vertices"], len(arm.data.bones)))
    pack = os.environ.get("MI_PACK", "CONVEX")
    wts = uv_weights(gun)
    dens = unwrap_cached(ctx, gun, "Rattler", res, wts, pack=pack)
    ctx.log("SK_Rattler: unwrapped (%s), %.0f px/m on the full-weight faces at %d px" % (pack, dens, res))
    texture(ctx, gun, T.paint_rattler, res, "Rattler")
    geo.ensure_wear(gun)
    SKINNED["SK_Rattler"] = {"ob": gun, "arm": arm, "expect_size": (0.470, 0.072, 0.208), "poses": poses(), "notes": NOTES}
    return [gun, arm]


def build_mag(ctx):
    from assets import _weapons_rattler_tex as T
    mres = tex_res(ctx, "SM_Weapon_RattlerMagazine")
    body, top = B.build_magazine(ctx.col)
    W.mark_piece(body, 0.0)
    W.mark_piece(top, 1.0)
    mag = geo.join([body, top], "SM_Weapon_RattlerMagazine", ctx.col)
    mid = np.empty(len(mag.data.polygons), np.float32)
    mag.data.attributes["mid"].data.foreach_get("value", mid)
    mw = np.where(np.rint(mid) == W.BORE, 0.35, 1.0).astype(np.float32)
    unwrap_cached(ctx, mag, "Weapon_RattlerMagazine", mres, mw, angle=66.0, margin_px=4, pack=os.environ.get("MI_PACK", "CONVEX"))
    texture(ctx, mag, T.paint_rattler_mag, mres, "Weapon_RattlerMagazine")
    top = W.split_off(mag, None, "SM_Weapon_RattlerMagazine_TopRound", ctx.col)
    for o in (mag, top):
        geo.ensure_wear(o)
    ctx.asset(mag, collision="none", expect_size=(0.058, 0.032, 0.188), notes=MAG_NOTES)
    ctx.asset(top, collision="none", expect_size=None, notes=(
        "The RATTLER magazine's visible top round, a separate hideable piece sharing the magazine's set (slot "
        "M_Weapon_RattlerMagazine). Origin = gun origin; a 9 mm round along X, base at X 0.150, 5 mm left of centre, "
        "case axis Z -0.0379."))
    return [mag, top]


def build(ctx):
    scene.setup_cycles(threads=1, samples=ctx.args.samples)
    only = [o.lower() for o in (ctx.args.only or ("gun", "mag"))]
    objs = []
    if "gun" in only:
        objs += build_gun(ctx)
    if "mag" in only:
        objs += build_mag(ctx)
    return objs


def poses():
    RT = S.RT
    t = RT["bolt_travel"]
    return [{"name": "bolt racked by its travel", "bones": {"bolt": {"translate": (-t, 0, 0)}}},
            {"name": "trigger pulled", "bones": {"trigger": {"rotate": ((0, 1, 0), RT["trigger_deg"])}}},
            {"name": "selector to auto", "bones": {"selector": {"rotate": ((0, 1, 0), RT["selector_deg"][2])}}},
            {"name": "magazine dropped", "bones": {"magazine": {"translate": (0, 0, -RT["mag_drop"])}}},
            {"name": "stock deployed", "bones": {"stock": {"rotate": ((0, 0, 1), RT["stock_deg"]), "pivot": RT["stock_hinge"]}}},
            {"name": "muzzle device and both sights moved", "bones": {"MuzzleDevice": {"translate": (0.02, 0, 0)},
                                                                      "IronsFront": {"translate": (0, 0, -0.02)},
                                                                      "IronsRear": {"translate": (0, 0, 0.02)}}}]


NOTES = (
    "Player weapon 6, the RATTLER: the Goons' compact open-bolt 9 mm submachine gun at first-person grade (our own design). Gun "
    "space = Blender: X forward along the bore, Z up, Y left; ORIGIN on the bore axis at the rear face of the receiver (the data's "
    "X_rattler = X_goon + 0.080, Z_rattler = Z_goon - 0.042); muzzle at X 0.465 with the stock folded. Bones (rest orientation = gun "
    "axes: local X along the bore): body (root), bolt (the open bolt + the top T-handle; head (0.215, 0, 0); slides 0.050 back along "
    "-X, the handle runs in its slot in the cover), trigger (pivot (0.127, 0, -0.045); pull = +17 deg about +Y), selector (left "
    "lever, pivot (0.045, 0.0225, -0.014); 0 / +14 / +28 deg about +Y = S / 1 / A), magazine (attach bone at the gun origin, no "
    "vertices: SM_Weapon_RattlerMagazine follows it; the reload drops it (0, 0, -0.14)), stock (the wire frame, its hinge knuckles "
    "and the butt plate; hinge (0, 0.0285, 0), rest = FOLDED along the left flank; rotate (0, 0, 1) by +180 deg about the hinge = "
    "deployed, the plate then stands about 0.25 behind the receiver), MuzzleDevice (the slotted muzzle device, a closed shell; hides "
    "when a muzzle part is fitted: the R 8.5 threaded stub with its bore and the barrel collar stay), IronsFront (the front sight "
    "tower, hides with an optic), IronsRear (the flip-up aperture leaf with its hinge pin, hides with an optic). Sockets (bones "
    "without vertices): Muzzle, Eject (casing direction (0, -0.95, 0.31)), SightRear, SightFront, RecoilPivot, MagHinge, Palm_R, "
    "Palm_L (the strap wrap's underside), Optic (MI-R rail on the cover, lug tops Z 0.042, centre of the rail), MuzzleMount (the "
    "thread shoulder of the barrel stub, X 0.410). No underbarrel and no laser (a round shroud has no rail). One slot M_Rattler = the "
    "unique 4K set Rattler (BC, N, ORM; no emissive texel); tiling detail TS_GunDetail_Steel (20 mm).")
MAG_NOTES = (
    "RATTLER 32-round straight stick magazine, 30 x 42 mm, 182 mm from the feed lips (MagHinge, Z -0.032) to the floor plate (Z "
    "-0.214): stamped grey steel with two ribs per side and a spine seam, folded feed lips, a deep pocket showing three rounds and the "
    "follower, a black floor plate with a drag tab. Origin = gun origin (in place X 0.143..0.200, Z -0.214..-0.032). The reload drops "
    "it (0, 0, -0.14). Top round: SM_Weapon_RattlerMagazine_TopRound.")


# ------------------------------------------------------------------------------------------------ export

def on_export(ctx, objs):
    for name, a in ctx.assets.items():
        export.export_asset(a["ob"], ctx.family, a["collision"], a["cover_height"], a["notes"], a["pivot"],
                            a["expect_size"], slots=a["slots"])
    for name, s in SKINNED.items():
        ob, arm = s["ob"], s["arm"]
        err, warn = rig.validate(ob, arm, s["expect_size"])
        for w in warn:
            print("    warning %s: %s" % (name, w))
        if err:
            raise ValueError("%s failed validation:\n  %s" % (name, "\n  ".join(err)))
        path = rig.export_skinned(ob, arm)
        rep = rig.verify(path, s["poses"])
        ok = rep["ok"] and rep["glb"]["all_axes_are_asset_axes"]
        ctx.log("%s: %s, poses %s, joint axes = gun axes: %s" % (
            name, os.path.relpath(path, paths.art), ", ".join("%s %.1e m" % (p["name"], p["max_error_m"]) for p in rep["poses"]),
            rep["glb"]["all_axes_are_asset_axes"]))
        if not ok:
            raise ValueError("%s: re-import proof failed: %s" % (name, json.dumps(rep)[:2000]))
        sockets = {b.name: [round(v, 5) for v in b.head_local] for b in arm.data.bones if not b.use_deform}
        slots = {}
        for m in ob.data.materials:
            if m is None:
                continue
            meta = bake.read_set(m.name[2:]) or {}
            dens = meta.get("texel_density_px_per_m")
            res = (meta.get("resolution") or [4096])[0]
            slots[m.name] = {"detail_set": TX.DETAIL_SET, "detail_tile_m": TX.DETAIL_TILE_M,
                             "detail_repeat_per_uv": round(res / dens / TX.DETAIL_TILE_M, 2) if dens else None,
                             "detail_blend": "steel tile where ORM.B = 1; the strap (ORM.B = 0) carries its weave in the unique normal map"}
        entry = rig.manifest_entry(ob, arm, ctx.family, path, s["notes"], slots=slots, sockets=sockets, poses_report=rep)
        export.write_manifest([entry], [m.name[2:] for m in ob.data.materials if m and m.name.startswith("M_")] + [TX.DETAIL_SET])
    if SKINNED and (bake.read_set(TX.DETAIL_SET) is None or os.environ.get("MI_REDETAIL")):
        TX.detail_set()
        ctx.log("wrote the tiling detail set %s" % TX.DETAIL_SET)


def on_preview(ctx, objs):
    from assets import _weapons_rattler_prev as PV
    PV.run(ctx)
