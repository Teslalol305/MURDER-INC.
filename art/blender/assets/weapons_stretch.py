"""STRETCH: the player's semi-automatic marksman rifle (7.6 mm class, 1,045 mm), skinned, one unique 4K set, with its
magazine and the visible top round.

Briefs: weapons round 4 specification (STRETCH), docs/unreal/LOADOUT.md 3.2, 3.3, 6.1-6.3, 6.6; data
unreal/MurderInc/Content/Data/guns.json (mounts, sockets) and attachments.json (parts that clamp to its rails and thread).

Gun space = Blender space: X forward along the bore, Y left, Z up; origin on the bore axis at the rear face of the
receiver (the stock is at negative X); butt -0.255, muzzle +0.790.

    build.py build weapons_stretch --bake --export                 # gun + magazine (4K bake: ~25 min on 2 threads)
    build.py build weapons_stretch --res 512 --bake                # draft sets (every set at 1/8 size)
    MI_PREVIEWS=hero,fp,side,parts build.py build weapons_stretch --preview

Bones (rest orientation = gun axes: local X along the bore): body (root), bolt (carrier, bolt head, left T-handle),
trigger, selector, bolt_catch, magazine (attach bone at the origin), bipod (hinge, folded legs), MuzzleDevice (the brake
shell), IronsRear / IronsFront (flip-up irons), and the socket bones without vertices Muzzle, Eject, SightRear,
SightFront, RecoilPivot, MagHinge, Palm_R, Palm_L, Optic, MuzzleMount, Underbarrel.
"""
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

from mi import bake, export, geo, mat, paths, render, rig, scene
from mi import texpaint as tp
from assets import weapons as W

FAMILY = {"name": "weapons_stretch", "description": "STRETCH marksman rifle (skinned SK_Stretch, 4K set) and its magazine"}
GROUPS = ("stretch",)

from assets import _weapons_stretch_geo as G  # noqa: E402
from assets import _weapons_stretch_tex as TS  # noqa: E402
from assets import _weapons_tex as TX  # noqa: E402

TEX = {"SK_Stretch": 4096, "SM_Weapon_StretchMagazine": 2048}
SKINNED = {}
THREADS = 2                                  # the build machine is shared: bakes and renders use at most two threads


def tex_res(ctx, name):
    full = TEX[name]
    return full if ctx.args.res >= 2048 else max(128, full * ctx.args.res // 4096)


# ------------------------------------------------------------------------------------------------------- UV weights

def uv_weights(ob):
    """Per-face UV scale (texel density weights) for the whole gun: 1.0 on what the camera reads at 30 cm (receiver flanks,
    top, rail, controls, charging handle, grip, bolt through the port), 0.8 on the walnut flanks and handguard, 0.6 on the
    barrel, brake, bipod and the rest, 0.3-0.5 on hidden faces (receiver cavity, tube inside, stock end caps, web feet)."""
    me = ob.data
    n = len(me.polygons)
    mid = np.empty(n, np.float32)
    me.attributes["mid"].data.foreach_get("value", mid)
    mid = np.rint(mid).astype(int)
    c = np.empty(n * 3, np.float32)
    me.polygons.foreach_get("center", c)
    c = c.reshape(-1, 3)
    nr = np.empty(n * 3, np.float32)
    me.polygons.foreach_get("normal", nr)
    nr = nr.reshape(-1, 3)
    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    r = np.hypot(y, z)
    w = np.full(n, 0.50, np.float32)
    blued, wood, bright, dark, rub, bore = (mid == G.BLUED), (mid == G.WOOD), (mid == G.BRIGHT), (mid == G.DARK), (mid == G.RUBBER), (mid == G.BORE)
    # walnut: the stock flanks and the handguard sides are the big read; grip and tube a little finer
    stock = wood & (x < 0.004)
    w[stock] = 0.62
    w[stock & (np.abs(nr[:, 1]) > 0.6)] = 0.78
    hg = wood & (x > 0.2) & (x < 0.55)
    w[hg] = 0.72
    w[hg & (r < 0.0235)] = 0.30                              # the tube's inside, seen through the slots
    w[wood & (x > 0.0) & (x < 0.1) & (z < -0.028)] = 0.95     # grip
    # receiver: outer flanks, top and rear read; the cavity does not
    rec = blued & (x > 0.0) & (x < 0.2352) & (np.abs(y) < 0.0222) & (z > -0.0322) & (z < 0.0402)
    w[rec] = 1.0
    cav = rec & (np.abs(y) < 0.0194) & (z > -0.0292) & (z < 0.0372) & (x > 0.0038) & (x < 0.2098)
    w[cav] = 0.28
    w[cav & (y < -0.012) & (z > -0.004) & (x > 0.09) & (x < 0.215)] = 0.55   # far wall seen through the port / near wall through the slot
    w[rec & (nr[:, 0] > 0.8) | rec & (nr[:, 0] < -0.8)] = 0.5
    w[rec & (nr[:, 2] < -0.8)] = 0.6
    # rails: lugs read from above, the web's feet and flank run hidden
    lugs = blued & (z > 0.0452) & (z < 0.0522) & (np.abs(y) < 0.0107)
    w[lugs] = 0.85
    w[blued & (z > 0.0225) & (z < 0.0402) & (x > 0.2352) & (np.abs(y) < 0.0095)] = 0.45       # web
    w[blued & (z < -0.0215) & (z > -0.0382) & (x > 0.2845) & (x < 0.4815) & (np.abs(y) < 0.0107)] = 0.55   # bottom rail
    # controls, charging handle, bolt group, grip hardware: full
    w[(blued | dark) & (y > 0.0220)] = 1.0
    w[bright] = 1.0
    w[(blued | dark) & (x > 0.088) & (x < 0.152) & (z < -0.030) & (z > -0.105)] = 0.95       # trigger group
    w[(blued | dark) & (x > 0.075) & (x < 0.190) & (z < -0.030) & (z > -0.050)] = 0.8        # magazine well
    # steel furniture
    w[blued & (r < 0.0127) & (x > 0.235) & (x < 0.545)] = 0.30                               # barrel inside the handguard
    w[blued & (r < 0.0127) & (x > 0.209) & (x <= 0.235)] = 0.25
    w[blued & (r < 0.0128) & (x >= 0.545) & (x < 0.716)] = 0.50
    w[blued & (x > 0.7149)] = 0.50
    w[bore] = 0.30
    w[rub & (x < -0.20)] = 0.55
    w[dark & (z > 0.052)] = 0.75                                                              # flip-up irons
    w[(dark | blued | rub) & (x > 0.31) & (x < 0.485) & (z < -0.040)] = 0.50                 # bipod
    return w


# ------------------------------------------------------------------------------------------------------ UV cache

def mesh_key(ob):
    """Hash of the mesh's geometry and topology (positions to 0.01 mm, loop counts): the cache key of its UV layout."""
    import hashlib
    co, _n = geo.arrays(ob)
    lt = np.empty(len(ob.data.polygons), np.int32)
    ob.data.polygons.foreach_get("loop_total", lt)
    h = hashlib.sha1(np.round(co * 1e5).astype(np.int64).tobytes())
    h.update(lt.tobytes())
    return h.hexdigest()[:20]


def unwrap_cached(ctx, ob, set_name, res, weights, angle=85.0, margin_px=3, pack="CONVEX"):
    """Smart projection is not reproducible between processes, so the layout a set was painted on is kept in
    art/out/textures/<Set>/uv_cache.npz (keyed by the mesh hash) and reused until the mesh changes: a preview or a
    re-export in a later process then matches the baked textures."""
    path = os.path.join(paths.texture_set(set_name), "uv_cache.npz")
    key = mesh_key(ob)
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


# ---------------------------------------------------------------------------------------------------------- build

def build_stretch(ctx):
    scene.setup_cycles(bpy.context.scene, threads=THREADS, samples=ctx.args.samples)
    res = tex_res(ctx, "SK_Stretch")
    gun, arm = G.stretch_build(ctx)
    ctx.log("SK_Stretch: %d tris, %d verts" % (geo.stats(gun)["triangles"], geo.stats(gun)["vertices"]))
    wts = uv_weights(gun)
    dens = unwrap_cached(ctx, gun, "Stretch", res, wts)
    ctx.log("SK_Stretch UV: %.0f px/m on the full-weight faces" % dens)
    W.texture(ctx, gun, TS.paint_stretch, res, set_name="Stretch")
    geo.ensure_wear(gun)
    SKINNED["SK_Stretch"] = {"ob": gun, "arm": arm, "expect_size": (1.045, 0.068, None), "poses": stretch_poses(),
                             "notes": STRETCH_NOTES}
    body, top = G.stretch_magazine(ctx.col)
    W.mark_piece(body, 0.0)
    W.mark_piece(top, 1.0)
    mag = geo.join([body, top], "SM_Weapon_StretchMagazine", ctx.col)
    mres = tex_res(ctx, "SM_Weapon_StretchMagazine")
    mid = np.empty(len(mag.data.polygons), np.float32)
    mag.data.attributes["mid"].data.foreach_get("value", mid)
    mw = np.where(np.rint(mid) == W.BORE, 0.35, 1.0).astype(np.float32)
    unwrap_cached(ctx, mag, "Weapon_StretchMagazine", mres, mw, angle=66.0, margin_px=4)
    W.texture(ctx, mag, TS.paint_stretch_mag, mres)
    top = W.split_off(mag, None, "SM_Weapon_StretchMagazine_TopRound", ctx.col)
    for o in (mag, top):
        geo.ensure_wear(o)
    ctx.asset(mag, collision="none", expect_size=(0.057, 0.025, 0.112), notes=STRETCH_MAG_NOTES)
    ctx.asset(top, collision="none", expect_size=None, notes=(
        "The STRETCH magazine's visible top round, a separate hideable piece sharing the magazine's set (slot "
        "M_Weapon_StretchMagazine). Origin = gun origin; case X 0.135..0.177, 30 mm below the bore, 3.6 mm left of centre."))
    return [gun, arm, mag, top]


def stretch_poses():
    S = G.ST
    return [{"name": "bolt back by its travel", "bones": {"bolt": {"translate": (-S["travel"], 0, 0)}}},
            {"name": "trigger pulled", "bones": {"trigger": {"rotate": ((0, 1, 0), S["trigger_deg"])}}},
            {"name": "selector to semi", "bones": {"selector": {"rotate": ((0, 1, 0), S["selector_deg"])}}},
            {"name": "bolt catch up", "bones": {"bolt_catch": {"rotate": ((0, 1, 0), S["catch_deg"])}}},
            {"name": "magazine dropped", "bones": {"magazine": {"translate": (0, 0, -S["mag_drop"])}}},
            {"name": "bipod deployed", "bones": {"bipod": {"rotate": ((0, 1, 0), S["bipod_deg"]), "pivot": S["bipod_hinge"]}}},
            {"name": "brake, rear iron and front iron moved away", "bones": {
                "MuzzleDevice": {"translate": (0.05, 0, 0)}, "IronsRear": {"translate": (0, 0, 0.05)},
                "IronsFront": {"translate": (0, 0, 0.05)}}}]


STRETCH_NOTES = (
    "Player weapon 5, skinned: the STRETCH, a semi-automatic marksman rifle (7.6 mm class), 1,045 mm, a free-floating 515 mm "
    "barrel, a fixed walnut stock, a 195 mm top rail and a folding bipod. Bones (rest orientation = gun axes: local X along the "
    "bore, Z up, Y left): body (root, origin on the bore axis at the rear face of the receiver; the stock is at negative X), "
    "bolt (carrier + bolt head + left T-handle; head X 0.195 Z 0.015; slides 0.095 back along -X, the knob runs in its left "
    "slot), trigger (pivot X 0.100 Z -0.045; pull = +17 deg about +Y), selector (left, pivot X 0.040 Z -0.010; 0 SAFE / +16 deg "
    "SEMI about +Y), bolt_catch (left lever, pivot X 0.125 Z -0.012; +7 deg about +Y when the bolt locks back), magazine "
    "(attach bone at the origin for SM_Weapon_StretchMagazine; the reload drops it (0, 0, -0.12)), bipod (hinge X 0.470 Z -0.050, "
    "both legs, knuckles and the pin; rest = folded backward under the handguard, rotate (0, 1, 0) by -100 deg = deployed), "
    "MuzzleDevice (the brake shell: hide it when a suppressor is fitted), IronsRear and IronsFront (flip-up irons on the rail, "
    "hide when an optic is fitted). Sockets (bones without vertices, brief positions): Muzzle, Eject (casing direction "
    "(-0.15, -0.95, 0.30)), SightRear, SightFront, RecoilPivot, MagHinge, Palm_R, Palm_L, Optic (on the lug tops, X 0.150), "
    "MuzzleMount (the thread shoulder, X 0.715) and Underbarrel (the lug undersides, X 0.300, Z -0.038). One slot M_Stretch, set "
    "Stretch (4096: BC, N, ORM; no E map: nothing emissive). MI-R rails: 21.2 mm across the 45 deg flanks, 5.3 mm lugs every "
    "10.6 mm, lug tops Z +0.052 (top) and lug undersides Z -0.038 (bottom, X 0.2845..0.4806).")
STRETCH_MAG_NOTES = (
    "STRETCH 10-round box magazine, 24 x 48 mm, 111 mm from the feed lips (MagHinge X 0.157, Z -0.024) to the floor plate (Z "
    "-0.135): stamped steel body, two raised ribs per side, folded lips, follower, the second round and a black polymer floor "
    "plate with a drag tab. Origin = gun origin (in place X 0.132..0.190, Z -0.135..-0.024). The drop of the reload is (0, 0, "
    "-0.12). Same cross-section as the SHORTY's magazine so mag_ext_rifle fits both. Top round: "
    "SM_Weapon_StretchMagazine_TopRound.")


def build(ctx):
    only = [o.lower() for o in (ctx.args.only or GROUPS)]
    objs = []
    if "stretch" in only:
        objs += build_stretch(ctx)
    return objs


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
            slots[m.name] = {"detail_set": TX.DETAIL_SET, "detail_tile_m": TX.DETAIL_TILE_M,
                             "detail_repeat_per_uv": round(4096.0 / dens / TX.DETAIL_TILE_M, 2) if dens else None}
        entry = rig.manifest_entry(ob, arm, ctx.family, path, s["notes"], slots=slots, sockets=sockets, poses_report=rep)
        export.write_manifest([entry], [m.name[2:] for m in ob.data.materials if m and m.name.startswith("M_")]
                              + [TX.DETAIL_SET])


# ================================================================================================ previews

PREVIEW_ONLY = os.environ.get("MI_PREVIEWS", "")
if os.environ.get("MI_PREVIEW_DIR"):                      # development renders go elsewhere than art/previews
    paths.previews = os.environ["MI_PREVIEW_DIR"]
W.VIEWMODEL["SK_Stretch"] = ((0.15, -0.09, -0.24), (0.05, 0.28, -0.35))      # guns.json stretch views[0], the CHOPPER's pose


def _plain_background(grey=0.22):
    """Studio light for the gun, a plain grey for the camera's own rays."""
    nt = bpy.context.scene.world.node_tree
    out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputWorld")
    src = out.inputs["Surface"].links[0].from_node
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (grey, grey, grey * 1.02, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(src.outputs[0], mix.inputs[1])
    nt.links.new(bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def preview_hero_s(ctx, gun, extra, name="weapons_stretch_hero", direction=(0.62, -1.0, 0.36), lens=70.0, strength=1.9, exposure=0.7):
    """Three-quarter view from the right-front on the studio HDRI (brighter than the default: the gun is the darkest of the
    set and the glossy blued steel only shows what it reflects)."""
    W.rig_studio(strength=strength, exposure=exposure)
    W._hide_all_but([gun] + [e for e in extra if e is not None])
    lo, hi = scene.bounds(gun, world=True)
    c = Vector(((lo[0] + hi[0]) / 2, 0.0, (lo[2] + hi[2]) / 2 + 0.005))
    span = float(np.linalg.norm(hi - lo))
    fov = 2 * math.atan(18.0 / lens)
    d = Vector(direction).normalized()
    dist = span * 0.52 / math.tan(fov / 2)
    cam = render.cam_look(c + d * dist, c, lens, name="Cam_hero", dof=(dist, 5.6))
    cam.data.clip_start = 0.01
    render.setup(samples=ctx.args.samples, res=(1280, 720), threads=THREADS)
    path, sec = render.render_jpeg(W._prev(ctx, name), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))


def preview_side(ctx, gun, extra, name="weapons_stretch_side"):
    """Flat orthographic LEFT side view (camera on +Y, muzzle to the left) on a plain background: the first thing a player's
    eye reads."""
    W.rig_studio(strength=1.9, exposure=0.6)
    _plain_background(0.26)
    W._hide_all_but([gun] + list(extra))
    lo, hi = scene.bounds(gun, world=True)
    c = Vector(((lo[0] + hi[0]) / 2, 0.0, (lo[2] + hi[2]) / 2))
    cam = render.cam_look(c + Vector((0.0, 1.6, 0.0)), c, 50.0, name="Cam_side")
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 1.12
    cam.data.clip_start, cam.data.clip_end = 0.1, 6.0
    render.setup(samples=ctx.args.samples, res=(1280, 720), threads=THREADS)
    path, sec = render.render_jpeg(W._prev(ctx, name), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))


def preview_parts_open(ctx, gun, arm, mag, top, name="weapons_stretch_parts"):
    """Posed open: the bolt locked back (95 mm), trigger pulled, selector on SEMI, bolt catch up, bipod deployed, the magazine
    dropped beside the rifle with its top round; a three-quarter view from the right-front over the open ejection port."""
    S = G.ST
    W.rig_studio(strength=1.9, exposure=0.6)
    rig.pose_imported(arm, {"bolt": {"translate": (-S["travel"], 0, 0)}, "trigger": {"rotate": ((0, 1, 0), S["trigger_deg"])},
                            "selector": {"rotate": ((0, 1, 0), S["selector_deg"])},
                            "bolt_catch": {"rotate": ((0, 1, 0), S["catch_deg"])},
                            "bipod": {"rotate": ((0, 1, 0), S["bipod_deg"]), "pivot": S["bipod_hinge"]}})
    M = Matrix.Translation((0.0, -0.075, -0.150))
    for o in (mag, top):
        o.matrix_world = M @ Matrix.Rotation(math.radians(-8.0), 4, "Y")
    W._hide_all_but([gun, mag, top])
    lo, hi = scene.bounds(gun, world=True)
    c = Vector(((lo[0] + hi[0]) / 2 - 0.05, -0.02, (lo[2] + hi[2]) / 2 - 0.02))
    d = Vector((0.30, -1.0, 0.50)).normalized()
    cam = render.cam_look(c + d * 1.55, c, 55.0, name="Cam_parts", dof=(1.55, 8.0))
    cam.data.clip_start = 0.01
    render.setup(samples=ctx.args.samples, res=(1280, 720), threads=THREADS)
    path, sec = render.render_jpeg(W._prev(ctx, name), ctx.args.samples)
    ctx.log("preview %s (%.0f s)" % (path, sec))
    rig.pose_imported(arm, {})
    for o in (mag, top):
        o.matrix_world = Matrix.Identity(4)


def render_silhouette(ctx, gun, extra, path=None):
    """T_UI_Gun_Stretch: white on transparent, 512 x 192, right side (camera on -Y, muzzle to the right), 2.2 mm per px, the bore
    line at y = 84 px, centred horizontally, 4x supersampled, alpha film. Written to art/out/ui (not committed)."""
    from PIL import Image
    path = path or os.path.join(paths.out, "ui", "T_UI_Gun_Stretch.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    wm = bpy.data.materials.new("Sil")
    nt = wm.node_tree
    nt.nodes.clear()
    o_ = nt.nodes.new("ShaderNodeOutputMaterial")
    e_ = nt.nodes.new("ShaderNodeEmission")
    e_.inputs["Color"].default_value = (1, 1, 1, 1)
    nt.links.new(e_.outputs[0], o_.inputs["Surface"])
    objs = [gun] + [o for o in extra if o is not None]
    saved = [(o, [sl.material for sl in o.material_slots]) for o in objs]
    for o in objs:
        for sl in o.material_slots:
            sl.material = wm
    W._hide_all_but(objs)
    render._clear_rig()
    w, wnt = render._world()
    bgn = wnt.nodes.new("ShaderNodeBackground")
    bgn.inputs["Color"].default_value = (0, 0, 0, 1)
    wout = wnt.nodes.new("ShaderNodeOutputWorld")
    wnt.links.new(bgn.outputs[0], wout.inputs["Surface"])
    render.look("Standard", "None", 0.0)
    ss, wpx, hpx, mm_px = 4, 512, 192, 2.2
    mid_x = 0.5 * (G.ST["sockets"]["Muzzle"][0] + (-0.255))                 # centre the 1,045 mm of length
    cam = render.cam_look(Vector((mid_x, -3.0, 0.0)), Vector((mid_x, 0.0, 0.0)), 50.0, name="Cam_sil")
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = wpx * mm_px / 1000.0                             # width of the frame in metres
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.clip_start, cam.data.clip_end = 0.1, 8.0
    cam.data.shift_y = -((hpx / 2 - 84) * mm_px / 1000.0) / cam.data.ortho_scale     # bore line (Z 0) at y = 84 px
    s = bpy.context.scene
    render.setup(samples=16, res=(wpx * ss, hpx * ss), threads=THREADS)
    s.render.film_transparent = True
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    tmp = os.path.join(paths.out, "ui", "_sil_tmp.png")
    s.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    im = Image.open(tmp).convert("RGBA")
    a = np.asarray(im, dtype=np.float32)[..., 3] / 255.0
    a = a.reshape(hpx, ss, wpx, ss).mean(axis=(1, 3))
    out = np.zeros((hpx, wpx, 4), np.uint8)
    out[..., :3] = 255
    out[..., 3] = np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(path)
    os.remove(tmp)
    for o, mats in saved:
        for sl, m in zip(o.material_slots, mats):
            sl.material = m
    ctx.log("silhouette %s" % path)
    return path


def on_preview(ctx, objs):
    want = lambda n: not PREVIEW_ONLY or n in PREVIEW_ONLY.split(",")
    if "SK_Stretch" not in SKINNED:
        return
    s = SKINNED["SK_Stretch"]
    gun, arm = s["ob"], s["arm"]
    mag = bpy.data.objects.get("SM_Weapon_StretchMagazine")
    top = bpy.data.objects.get("SM_Weapon_StretchMagazine_TopRound")
    if want("hero"):
        preview_hero_s(ctx, gun, (mag, top))
    if want("fp"):
        W.preview_fp(ctx, gun, arm, "SK_Stretch", "weapons_stretch_fp", extra=(mag, top))
    if want("side"):
        preview_side(ctx, gun, (mag, top))
    if want("parts"):
        preview_parts_open(ctx, gun, arm, mag, top)
    if want("sil"):
        render_silhouette(ctx, gun, (mag, top))
