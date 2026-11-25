"""SHORTY: the compact bullpup carbine of the six-gun roster, skinned for the Unreal import.

The owner's report on the loadout was "all the guns look the same": four of the five offered guns were one purchased-pack
M4. The SHORTY is our own design in the manner of a class of firearm, the compact bullpup carbine: the action and the
magazine sit BEHIND the pistol grip (a 700 mm gun with a 267 mm barrel), a tall olive polymer block with a see-through
carry handle on top, a short ventilated forend and a squat birdcage flash hider. It shares nothing with the other guns.

Assets (art/out/glb, textures in art/out/textures):
    SK_Shorty                           skinned, bones body (root), bolt, trigger, selector, magazine (attach), MuzzleDevice,
                                        IronsFront + the 12 socket bones of the contract (_weapons_shorty.SH);
                                        one slot M_Shorty = the unique 4K set 'Shorty' (BC, N, ORM, E)
    SM_Weapon_ShortyMagazine (+ _TopRound)   static, in place (origin = gun origin), slot M_Weapon_ShortyMagazine = the
                                        unique 2K set 'Weapon_ShortyMagazine'
    TS_GunDetail_Steel / TS_GunDetail_Polymer   the tiling micro detail (20 mm / 12 mm); repeat per UV in the manifest

    build.py build weapons_shorty --bake --export             # everything (4K bake about 25 min on 2 threads)
    build.py build weapons_shorty --bake --res 1024           # draft sets
    build.py build weapons_shorty --only gun|mag [--bake] [--export]
    MI_PREVIEWS=weapons_shorty_hero,... build.py build weapons_shorty --preview     # pictures from the exported files

Geometry: _weapons_shorty.py (contract, body, handle, rails, forend, barrel, hider, sight) and _weapons_shorty_b.py (grip,
trigger group, moving parts, details, magazine, rig); surfaces: _weapons_shorty_tex.py; proof: _weapons_check_shorty.py.
"""
import json
import os

import bpy
import numpy as np

from mi import bake, export, geo, mat, paths, rig, scene
from assets import weapons as W
from assets import _weapons_shorty as S
from assets import _weapons_shorty_b as B
from assets import _weapons_shorty_tex as T
from assets import _weapons_tex as TX

FAMILY = {"name": "weapons_shorty", "description": "SHORTY compact bullpup carbine: SK_Shorty, its magazine and top round"}
scene.THREADS = 2                    # this machine is shared: at most two threads for renders and bakes

RES = {"SK_Shorty": 4096, "SM_Weapon_ShortyMagazine": 2048}
SKINNED = {}


def tex_res(ctx, name):
    full = RES[name]
    return full if ctx.args.res >= 2048 else max(128, full * ctx.args.res // 4096)


def uv_weights(ob):
    """Per-face UV scale: 1.0 on what the camera reads (the right flank, top, handle, rail), 0.85 on the left flank, 0.75 on the forend
    and the grip, 0.5 on the barrel, hider, butt pad and the undersides, 0.3-0.45 on interiors and the parts seen
    through slots."""
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
    w = np.ones(n, np.float32)
    w[(nr[:, 2] < -0.7) & (bid == 0)] = 0.50                                            # undersides
    w[(nr[:, 1] > 0.7) & (bid == 0) & (x < 392.0)] = 0.85                               # the left flank (the camera sees the right)
    w[(np.abs(nr[:, 0]) > 0.7) & (bid == 0) & (x < 40.0) & (mid == S.OLIVE)] = 0.45     # the body's rear face (behind the pad)
    w[(mid == S.RUBBER)] = 0.50                                                         # the butt pad
    w[(mid == S.OLIVE) & (bid == 0) & (x > 392.0)] = 0.75                               # forend and deflector
    w[(mid == S.OLIVE) & (bid == 0) & (z < -62.0) & (x > 245.0) & (x < 445.0)] = 0.75   # grip and guard
    w[(mid == S.PARK) & (bid == 0) & (x > 396.0) & (x < 588.0) & (np.abs(y) < 29.0) & (z > -38.0) & (z < 32.0)] = 0.40  # barrel, gas
    w[(mid == S.PARK) & (bid == 0) & (x >= 588.0)] = 0.50                               # barrel past the nose, ring
    w[bid == 5] = 0.50                                                                  # hider
    w[(bid == 1) & (x < 380.0)] = 0.60                                                  # the carrier body
    w[(mid == S.PARK) & (bid == 0) & (z < -40.0) & (x > 455.0) & (x < 565.0)] = 0.75   # the underside rail
    w[mid == S.BORE] = 0.30                                                             # interiors
    return w


def build_gun(ctx):
    res = tex_res(ctx, "SK_Shorty")
    gun, arm = B.shorty_build(ctx)
    ctx.log("SK_Shorty: %d tris, %d bones" % (geo.stats(gun)["triangles"], len(arm.data.bones)))
    pack = os.environ.get("MI_PACK", "CONVEX")
    dens = geo.uv_unwrap(gun, res=res, angle=66.0, margin_px=4, pack=pack, weights=uv_weights(gun))
    ctx.log("SK_Shorty: unwrapped (%s), %.0f px/m at %d px" % (pack, dens, res))
    W.texture(ctx, gun, T.paint_shorty, res, set_name="Shorty")
    geo.ensure_wear(gun)
    SKINNED["SK_Shorty"] = {"ob": gun, "arm": arm, "expect_size": (0.700, 0.083, 0.280), "poses": poses(), "notes": NOTES}
    return [gun, arm]


def build_mag(ctx):
    mres = tex_res(ctx, "SM_Weapon_ShortyMagazine")
    body, top = B.build_magazine(ctx.col)
    W.mark_piece(body, 0.0)
    W.mark_piece(top, 1.0)
    mag = geo.join([body, top], "SM_Weapon_ShortyMagazine", ctx.col)
    W.unwrap(mag, mres)
    W.texture(ctx, mag, T.paint_shorty_mag, mres)
    top = W.split_off(mag, None, "SM_Weapon_ShortyMagazine_TopRound", ctx.col)
    for o in (mag, top):
        geo.ensure_wear(o)
    ctx.asset(mag, collision="none", expect_size=(0.062, 0.026, 0.162), notes=MAG_NOTES)
    ctx.asset(top, collision="none", expect_size=None, notes=(
        "The SHORTY magazine's visible top round, a separate hideable piece sharing the magazine's set (slot "
        "M_Weapon_ShortyMagazine). Origin = gun origin; a 45 mm round along X, base at X 0.184, Z -0.026, 3.8 mm left of centre."))
    return [mag, top]


def build(ctx):
    scene.setup_cycles(threads=2, samples=ctx.args.samples)
    only = [o.lower() for o in (ctx.args.only or ("gun", "mag"))]
    objs = []
    if "gun" in only:
        objs += build_gun(ctx)
    if "mag" in only:
        objs += build_mag(ctx)
    return objs


def poses():
    SH = S.SH
    t = SH["bolt_travel"]
    return [{"name": "bolt back by its travel", "bones": {"bolt": {"translate": (-t, 0, 0)}}},
            {"name": "trigger pulled", "bones": {"trigger": {"rotate": ((0, 1, 0), SH["trigger_deg"])}}},
            {"name": "selector to auto", "bones": {"selector": {"rotate": ((0, 1, 0), SH["selector_deg"][2])}}},
            {"name": "magazine dropped", "bones": {"magazine": {"translate": (0, 0, -SH["mag_drop"])}}},
            {"name": "muzzle device and front sight moved", "bones": {"MuzzleDevice": {"translate": (0.02, 0, 0)},
                                                                      "IronsFront": {"translate": (0, 0, -0.02)}}}]


NOTES = (
    "Player weapon, the compact bullpup carbine (our own design). Gun space = Blender: X forward along the bore, Z up, Y "
    "left; ORIGIN on the bore axis at the rear face of the butt pad (the receiver ends at the butt); muzzle at X 0.700; "
    "length 700, height 280 (rail lug tops Z +0.100 to the magazine floor Z -0.180), width 83 (deflector Y -0.043 to the "
    "charging knob Y +0.040). Bones (rest orientation = gun axes: local X along the bore): body (root), bolt (head "
    "(0.380, 0, 0.012); carrier + left charging handle; slides 0.075 back along -X, locks back on empty), trigger (pivot "
    "(0.362, 0, -0.050); pull = +17 deg about +Y), selector (pivot (0.300, 0.0285, -0.022); 0 / +14 / +28 deg about +Y = "
    "SAFE / SEMI / AUTO), magazine (attach bone at the gun origin, no vertices: SM_Weapon_ShortyMagazine follows it; the "
    "reload drops it (0, 0, -0.13)), MuzzleDevice (the birdcage hider, a closed shell; hides when a muzzle part is fitted: "
    "the R 8.5 threaded stub and the bore stay), IronsFront (the front sight tower; hides when an optic is fitted). "
    "Sockets (bones without vertices): Muzzle, Eject (casing direction (0.55, -0.80, 0.25)), SightRear, SightFront, "
    "RecoilPivot, MagHinge, Palm_R, Palm_L, Optic (MI-R rail on the carry handle, lug tops Z 0.100), MuzzleMount (barrel "
    "thread shoulder), Underbarrel and Laser (MI-R rail under the forend, lug undersides Z -0.052). One slot M_Shorty = the "
    "unique 4K set Shorty (BC, N, ORM, E = the tritium insert); tiling detail TS_GunDetail_Steel (20 mm) where ORM.B = 1 and "
    "TS_GunDetail_Polymer (12 mm) where it is 0 (repeat per UV in the slot record).")
MAG_NOTES = (
    "SHORTY 30-round straight box magazine, 24 x 48 mm, 160 mm from the feed lips (MagHinge, Z -0.020) to the floor plate "
    "(Z -0.180): stamped parkerised steel with three ribs per side and a spine weld, feed lips, follower, the second round of "
    "the double stack, an olive polymer floor plate with a drag tab. Origin = gun origin (in place, X 0.1705..0.232). The same "
    "24 x 48 cross-section as the STRETCH magazine so mag_ext_rifle fits both. Top round: SM_Weapon_ShortyMagazine_TopRound.")


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
            slots[m.name] = {
                "detail_set": TX.DETAIL_SET, "detail_tile_m": TX.DETAIL_TILE_M,
                "detail_repeat_per_uv": round(res / dens / TX.DETAIL_TILE_M, 2) if dens else None,
                "detail_set_polymer": T.DETAIL_POLY, "detail_polymer_tile_m": T.DETAIL_POLY_TILE_M,
                "detail_polymer_repeat_per_uv": round(res / dens / T.DETAIL_POLY_TILE_M, 2) if dens else None,
                "detail_blend": "steel tile where ORM.B = 1, polymer tile where ORM.B = 0"}
        entry = rig.manifest_entry(ob, arm, ctx.family, path, s["notes"], slots=slots, sockets=sockets, poses_report=rep)
        export.write_manifest([entry], [m.name[2:] for m in ob.data.materials if m and m.name.startswith("M_")]
                              + [TX.DETAIL_SET, T.DETAIL_POLY])
    if SKINNED:
        for sname, fn in ((TX.DETAIL_SET, TX.detail_set), (T.DETAIL_POLY, T.detail_polymer)):
            if bake.read_set(sname) is None or os.environ.get("MI_REDETAIL"):
                fn()
                ctx.log("wrote the tiling detail set %s" % sname)


def on_preview(ctx, objs):
    from assets import _weapons_shorty_prev as PV
    PV.render(ctx)
