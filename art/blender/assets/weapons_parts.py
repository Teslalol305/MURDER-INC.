"""Round 4, lane 2: the PARTS KIT (our own universal parts) and the mounts of the CHOPPER and the NINE.

The owner's report: "all the guns look the same and no attachments are able to be added". Lane 1 and the RATTLER's modeler
make the guns; this family makes what the Workbench puts on them: a compact red dot and a 4x scope (lens slots, SightEye), a
long rifle / SMG suppressor and a pistol suppressor (Muzzle at the far end), a three-chamber compensator, a vertical grip
(rail), a wooden vertical grip with a saddle clamp (the CHOPPER) and an angled grip (SupportHand), a red laser module (Beam)
and three extended magazines with a hideable top round (rifle, SMG, the NINE's canted one). Each part exports as its own GLB
`SM_Part_<Id>` with its mount at the file origin, and the sockets of the specification go to the contract
`art/blender/assets/weapons_parts_contract.json` (a static mesh's sockets are written from it at import).

    build.py build weapons_parts --bake --export                    # everything (two 2K bakes, about 15 min on one thread)
    build.py build weapons_parts --only parts --res 512 --bake      # draft hardware set (every set at 512)
    build.py build weapons_parts --only mags --export
    python art/blender/assets/_weapons_patch.py                     # the CHOPPER's and the NINE's sockets (GLB patch)

Two unique 2K sets: `Weapon_Parts` (slot M_Part_Hardware: BC N ORM E) and `Weapon_PartsMags` (slot M_Part_Mags: BC N ORM). The
lens and the reticle plane are the flat slots `M_Part_Lens` and `M_Part_Reticle` (translucent glass and the collimated additive
dot are made in Unreal, like M_TFA_AR_Glass and M_TFA_AR_Reticle in the pack import). The parts are laid out in a row in one
atlas object for the unwrap, the geometry bakes and the painter (`_weapons_parts_tex.py`), then split back, so a part is
exported once with the atlas's UVs. The UV layout is cached (`textures/<Set>/uv_cache.npz`).
"""
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector

from mi import bake, export, geo, mat, paths, render, rig, scene
from assets import weapons as W
from assets import _weapons_parts_geo as G
from assets import _weapons_parts_geo2 as G2
from assets import _weapons_parts_mags as GM
from assets import _weapons_parts_tex as PT

FAMILY = {"name": "weapons_parts", "description": "Parts kit: optics, muzzle devices, grips, laser, extended magazines (SM_Part_*)"}
GROUPS = ("parts", "mags")
THREADS = 1
CONTRACT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weapons_parts_contract.json")

HW_SET, MAG_SET = "Weapon_Parts", "Weapon_PartsMags"
HW_SLOT, MAG_SLOT = "M_Part_Hardware", "M_Part_Mags"

# id, mesh name, builder, applies to, gun mount (socket), slot (Workbench), triangle budget, expected size (m) or None
HARDWARE = [
    dict(id="red_dot", mesh="SM_Part_RedDot", build=G.red_dot, slot="optic", applies=["chopper", "shorty", "stretch", "rattler"],
         mount="Optic", budget=8000, size=(0.064, None, None),
         mount_note="the centre of an MI-R clamp footprint on the lug tops (the rail's lug face is the origin plane)"),
    dict(id="scope_4x", mesh="SM_Part_Scope4x", build=G2.scope_4x, slot="optic", applies=["chopper", "shorty", "stretch"],
         mount="Optic", budget=12000, size=(0.150, None, None),
         mount_note="the centre of an MI-R clamp footprint on the lug tops"),
    dict(id="suppressor", mesh="SM_Part_Suppressor", build=G2.suppressor, slot="muzzle", applies=["chopper", "shorty", "stretch", "rattler"],
         mount="MuzzleMount", budget=6000, size=(0.210, 0.039, 0.039),
         mount_note="the rear face on the bore axis; the collar's recess (R 9.0 x 12 deep) swallows the barrel stub"),
    dict(id="compensator", mesh="SM_Part_Compensator", build=G2.compensator, slot="muzzle", applies=["chopper", "shorty", "rattler"],
         mount="MuzzleMount", budget=3000, size=(0.062, 0.030, 0.030),
         mount_note="the rear face on the bore axis; recess R 9.0 x 10 deep"),
    dict(id="suppressor_pistol", mesh="SM_Part_SuppressorPistol", build=G2.suppressor_pistol, slot="muzzle", applies=["nine"],
         mount="MuzzleMount", budget=4000, size=(0.155, 0.032, 0.032),
         mount_note="the slide's front face on the bore axis; the recess (R 7.2 x 6 deep) swallows the barrel's crown stub"),
    dict(id="foregrip_vertical", mesh="SM_Part_ForegripVertical", build=G2.foregrip_vertical, slot="underbarrel", applies=["shorty", "stretch"],
         mount="Underbarrel", budget=4000, size=(0.040, 0.037, 0.092),
         mount_note="the lug undersides of an underside MI-R rail (the part hangs in -Z)"),
    dict(id="foregrip_vertical_wood", mesh="SM_Part_ForegripVerticalWood", build=G2.foregrip_vertical_wood, slot="underbarrel", applies=["chopper"],
         mount="Underbarrel", budget=4000, size=(0.036, 0.046, None),
         mount_note="the underside of the CHOPPER's folded stock plate (the saddle hugs it); hangs to Z -0.145 in gun space"),
    dict(id="foregrip_angled", mesh="SM_Part_ForegripAngled", build=G2.foregrip_angled, slot="underbarrel", applies=["shorty", "stretch"],
         mount="Underbarrel", budget=4000, size=(None, None, 0.066),
         mount_note="the lug undersides of an underside MI-R rail (the part hangs in -Z)"),
    dict(id="laser_module", mesh="SM_Part_LaserModule", build=G2.laser_module, slot="laser", applies=["nine", "shorty"],
         mount="Laser", budget=4000, size=(0.046, None, 0.031),
         mount_note="the underside plane of the rail (the NINE's dust cover, the SHORTY's forend rail), the middle of the module"),
]
MAGS = [
    dict(id="mag_ext_rifle", mesh="SM_Part_MagRifleExt", build=GM.mag_ext_rifle, slot="magazine", applies=["shorty", "stretch"],
         mount="MagHinge", budget=10000, top_budget=2500, size=(None, 0.026, 0.235),
         mount_note="the centre of the feed lips' top face; the magazine hangs in -Z"),
    dict(id="mag_ext_smg", mesh="SM_Part_MagSmgExt", build=GM.mag_ext_smg, slot="magazine", applies=["rattler"],
         mount="MagHinge", budget=10000, top_budget=2500, size=(None, 0.032, 0.242),
         mount_note="the centre of the feed lips' top face; the magazine hangs in -Z"),
    dict(id="mag_ext_pistol", mesh="SM_Part_MagPistolExt", build=GM.mag_ext_pistol, slot="magazine", applies=["nine"],
         mount="MagHinge", budget=8000, top_budget=2000, size=None,
         mount_note="the NINE's MagHinge (0.0177, 0, -0.0359): modelled pre-canted along the grip axis (0.250, 0, 0.968)"),
]

NOTES = {
    "red_dot": "Compact enclosed red dot (our own tube sight): MI-R clamp 52 x 21.2 mm with a clamp-screw knob, body tube R 16.5 on the "
               "axis Z +24.5 above the lug tops (X -32..+32), flared rear hood, front window, knurled elevation cap (top Z +47), "
               "windage cap on the right, battery cap on the front top. Hollow optical path: the rear and the front window glass is "
               "slot M_Part_Lens (smoked, both windows), the reticle a 10 mm plane at X 0 facing the eye in slot M_Part_Reticle "
               "(collimated additive dot). Socket SightEye (-0.0325, 0, 0.0245): the centre of the rear window on the optical axis. "
               "Black hard-anodised aluminium, bare edges. Presentation relief 0.14.",
    "scope_4x": "Compact fixed 4x tube scope: monolithic 52 mm MI-R clamp with two cross-bolts and the clamp knob, 30 mm main tube on the "
                "axis Z +27.5, objective bell R 21 x 38, ocular bell R 19 x 28, X -65..+85, knurled lens rings, elevation turret on "
                "top (tallest point Z +53.5), windage turret on the RIGHT only (the CHOPPER's charging handle runs on the left). "
                "Hollow tube (ocular bore R 14, dark matte interior) so the view cone passes; glass is slot M_Part_Lens, the "
                "reticle a 20 mm plane at X 0 (slot M_Part_Reticle). SightEye (-0.067, 0, 0.0275) = the centre of the ocular lens "
                "on the axis. Presentation relief 0.085, adsFov 30.",
    "suppressor": "Long rifle / SMG suppressor, 210 mm, body R 19.5, our own shape: rear mount collar R 12.5 x 16 with an internal "
                  "recess R 9.0 x 12 deep (swallows every gun's R 8.5 barrel stub), twelve 0.6 mm flutes, a 2 mm end cap with an 11 mm "
                  "bore, the front 85 mm heat-darkened in the texture. Mount = the rear face centre on the bore; socket Muzzle "
                  "(0.210, 0, 0). Hides the gun's Booster / MuzzleDevice.",
    "compensator": "Three-chamber compensator, 62 mm, R 15: rear collar with a recess R 9.0 x 10, a chamber through the body, three "
                   "4 x 14 mm transverse ports on top and one angled port per side, a solid front face with a 7 mm bore and a "
                   "scalloped crown, carbon in the ports. Black nitrided steel. Mount = the rear face on the bore; socket Muzzle "
                   "(0.062, 0, 0). Not offered on the STRETCH (it has a brake).",
    "suppressor_pistol": "Pistol suppressor, 155 mm, body R 16.0 (top Z +16, 2.5 mm under the NINE's sight line), rear collar R 11.5 x 10 "
                         "with a recess R 7.2 x 6 deep over the barrel's crown stub, ten 0.6 mm flutes, a 10 mm end bore, brushed "
                         "stainless with the front 65 mm heat-darkened. Mount = the slide's front face on the bore; socket Muzzle "
                         "(0.155, 0, 0). The slide cycles back away from it.",
    "foregrip_vertical": "Vertical foregrip for an underside MI-R rail: clamp plate 40 x 21.2 mm with two cross-bolts, a 6 mm neck, body "
                         "O30 with three finger grooves, stippled polymer, a flared O34 cap with a lanyard slot; height 92. Origin = "
                         "the lug undersides plane; the part hangs in -Z. SupportHand (0, 0, -0.052) = mid-body.",
    "foregrip_vertical_wood": "The CHOPPER's vertical grip: a steel saddle that hugs the folded stock's curved shoulder plate (a 2.5 mm "
                              "band, 30 mm wide, the lowest thing under the handguard: underside Z -0.0623 at X 0.305, arc R 120), 36 x "
                              "46 mm with ears rising 17 mm, a strap under the plate and two bolts, and a laminated wooden body O30; "
                              "82.7 mm in all, hanging to Z -0.145 (gun space). Origin = the Underbarrel socket (0.305, 0, -0.0623). "
                              "SupportHand (0, 0, -0.048).",
    "foregrip_angled": "Angled foregrip for an underside MI-R rail: clamp plate 47.5 x 21.2 mm, a wedge body leaning forward and down at "
                       "about 38 deg with a thumb shelf and stippled left / right panels, 2 mm radii; about 62 x 30 x 66 mm. The palm "
                       "rests on the rear ramp: SupportHand (-0.012, 0, -0.030). Nothing above Z -0.0297 reaches past X +0.0195, so it "
                       "clears the laser module on the SHORTY's rail (48 mm apart). Origin = the lug undersides plane, hanging in -Z.",
    "laser_module": "Compact red laser module 46 x 22 x 28 mm for an underside rail (the NINE's dust cover, the SHORTY's forend rail): a "
                    "base plate with two side walls hugging the dovetail's flanks (no hooks and no keys: it seats on either rail), a "
                    "moulded polymer body, a 9 mm emitter window with a red lens ring (E texels), a side wheel and a button. Origin = "
                    "the rail's underside plane at the middle of the module; socket Beam (0.0235, 0, -0.0125), along +X.",
    "mag_ext_rifle": "Extended rifle magazine for the SHORTY's and the STRETCH's wells: 24 x 48 mm straight box, 235 mm tall (the 45-round "
                     "look), stamped steel with four ribs per side, a spine and a weld bead, folded feed lips, a black polymer floor "
                     "plate with a drag tab, the second round in the stack; the visible top round is the separate piece "
                     "SM_Part_MagRifleExt_TopRound (same set). Origin = MagHinge, the centre of the feed lips' top face.",
    "mag_ext_smg": "Extended stick magazine for the RATTLER: 30 x 42 mm, 242 mm from the lips (the 50-round look), grey stamped steel with "
                   "two ribs per side, a spine and a weld bead, a black floor plate with a drag tab; top round "
                   "SM_Part_MagSmgExt_TopRound. Origin = MagHinge.",
    "mag_ext_pistol": "Extended pistol magazine for the NINE: the standard magazine's body (19.5 x 34 mm raked along the grip axis (0.250, 0, "
                      "0.968), three witness holes per side, feed lips, the stack) lengthened by 48 mm, a black polymer sleeve over its "
                      "last 48 mm and the NINE's polished gold base pad carried down with it (in place X -0.0255..0.030, floor Z -0.181). "
                      "Modelled pre-canted about the origin = the NINE's MagHinge socket (0.0177, 0, -0.0359); top round "
                      "SM_Part_MagPistolExt_TopRound.",
}


def tex_res(ctx):
    return min(2048, ctx.args.res)


# ------------------------------------------------------------------------------------------------------ plumbing
def mesh_key(ob):
    import hashlib
    co, _n = geo.arrays(ob)
    lt = np.empty(len(ob.data.polygons), np.int32)
    ob.data.polygons.foreach_get("loop_total", lt)
    h = hashlib.sha1(np.round(co * 1e5).astype(np.int64).tobytes())
    h.update(lt.tobytes())
    return h.hexdigest()[:20]


def unwrap_cached(ctx, ob, set_name, res, weights, angle=66.0, margin_px=6, pack="CONVEX"):
    """Smart projection is not reproducible between processes: the layout a set was painted on is kept in
    art/out/textures/<Set>/uv_cache.npz (keyed by the mesh hash) and reused until the mesh changes."""
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
            ctx.log("%s: UV layout from the cache" % set_name)
            return geo.uv_texel_density(ob, res, faces=weights >= np.max(weights) - 1e-6)
    dens = geo.uv_unwrap(ob, res=res, angle=angle, margin_px=margin_px, pack=pack, weights=weights)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers.active.data.foreach_get("uv", uv)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez(path, key=key, uv=uv)
    return dens


def attr_array(ob, name, dtype=np.float32):
    a = np.empty(len(ob.data.polygons), dtype)
    ob.data.attributes[name].data.foreach_get("value", a)
    return a


def extract(ob, keep, name):
    """A copy of ob with only the polygons where keep is True (UVs, attributes and materials kept)."""
    cp = ob.copy()
    cp.data = ob.data.copy()
    cp.name = cp.data.name = name
    bpy.context.scene.collection.objects.link(cp)
    bm = geo.bm_of(cp)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(~np.asarray(keep))[0]], context="FACES")
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    geo.bm_to(cp, bm)
    return cp


def planar_uv(ob, axes=(1, 2)):
    """UVs 0..1 over the object's bounds in the plane `axes` (a lens disc, the reticle plane)."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name=geo.UV)
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", lv)
    lo, hi = co[:, list(axes)].min(0), co[:, list(axes)].max(0)
    uv = (co[lv][:, list(axes)] - lo) / np.maximum(hi - lo, 1e-9)
    me.uv_layers.active.data.foreach_set("uv", uv.astype(np.float32).ravel())
    return ob


_flat = {}


def flat_material(name, colour, rough, metal=0.0, emit=None):
    if name in _flat:
        return _flat[name]
    m = mat.flat(name, colour, rough, metal)
    _flat[name] = m
    return m


def uv_weights(ob):
    """Per-face UV scale: the dark inside and what cannot be seen weigh 0.35, the rest 1."""
    mid = np.rint(attr_array(ob, "mid")).astype(int)
    w = np.ones(len(mid), np.float32)
    w[mid == G.BORED] = 0.35
    return w


def layout_row(objs, gap=0.09):
    """Offsets (x) that lay the objects out in a row, `gap` between their bounds. Returns {index: (x, 0, 0)}."""
    off, x = {}, 0.0
    for k, ob in enumerate(objs):
        lo, hi = scene.bounds(ob)
        off[k] = (x - float(lo[0]) + gap, 0.0, 0.0)
        x += (float(hi[0]) - float(lo[0])) + gap
    return off


def build_set(ctx, specs, set_name, slot, painter, tag):
    """Build the parts of one texture set: a joined object per part, the atlas (parts in a row), the UV, the bake and paint, the
    split back, the flat lens and reticle slots, and the declared assets. Returns the exported objects."""
    res = tex_res(ctx)
    hw, extras, socks, tops = [], {}, {}, {}
    for k, sp in enumerate(specs):
        r = sp["build"](pi=k)
        if len(r) == 3:                                       # a magazine: (objects, top round, sockets)
            objs, top, sk = r
            tops[k] = top
        else:
            objs, sk = r
        socks[sp["id"]] = sk
        mids = [int(round(float(o.data.attributes["mid"].data[0].value))) if len(o.data.polygons) else -1 for o in objs]
        main = [o for o, m_ in zip(objs, mids) if m_ not in (G.LENS, G.RET)]
        extras[k] = [o for o, m_ in zip(objs, mids) if m_ in (G.LENS, G.RET)]
        part = geo.join(main, "HW_" + sp["id"], ctx.col)
        if k in tops:                                          # the top round shares the atlas: flag its faces
            for o_, v in ((part, 0.0), (tops[k], 1.0)):
                a = o_.data.attributes.get("piece") or o_.data.attributes.new("piece", "FLOAT", "FACE")
                a.data.foreach_set("value", np.full(len(o_.data.polygons), v, np.float32))
            part = geo.join([part, tops[k]], "HW_" + sp["id"], ctx.col)
        hw.append(part)
    off = layout_row(hw)
    for k, ob in enumerate(hw):
        geo.transform(ob, loc=off[k])
    atlas = geo.join(hw, set_name + "_Atlas", ctx.col)
    ctx.log("%s atlas: %d tris" % (set_name, geo.stats(atlas)["triangles"]))
    dens = unwrap_cached(ctx, atlas, set_name, res, uv_weights(atlas))
    ctx.log("%s UV: %.0f px/m on the full-weight faces" % (set_name, dens))
    m = W.texture(ctx, atlas, painter, res, set_name=set_name, offsets=off)
    m.name = slot
    # split the atlas back into the parts (and the top rounds), undo the layout
    out = []
    pidx = np.rint(attr_array(atlas, "part")).astype(int)
    piece = attr_array(atlas, "piece") if "piece" in atlas.data.attributes else np.zeros(len(pidx), np.float32)
    for k, sp in enumerate(specs):
        body = extract(atlas, (pidx == k) & (piece < 0.5), sp["mesh"])
        geo.transform(body, loc=tuple(-v for v in off[k]))
        pieces = [body]
        for o in extras[k]:
            mid = int(round(float(o.data.attributes["mid"].data[0].value)))
            planar_uv(o, (1, 2))
            o.data.materials.clear()
            o.data.materials.append(flat_material(G.LENS_SLOT, (0.020, 0.035, 0.040), 0.04) if mid == G.LENS else
                                    flat_material(G.RET_SLOT, (1.0, 0.0, 0.0), 0.5))
            pieces.append(o)
        ob = geo.join(pieces, sp["mesh"], ctx.col)
        geo.ensure_wear(ob)
        slots = {slot: {"set": set_name}}
        ctx.asset(ob, collision="none", expect_size=sp.get("size"), notes=NOTES[sp["id"]], slots=slots)
        out.append(ob)
        if k in tops:
            top = extract(atlas, (pidx == k) & (piece > 0.5), sp["mesh"] + "_TopRound")
            geo.transform(top, loc=tuple(-v for v in off[k]))
            geo.ensure_wear(top)
            top.data.materials.clear()
            top.data.materials.append(m)
            ctx.asset(top, collision="none", expect_size=None, slots={slot: {"set": set_name}}, notes=(
                "The top round of %s, a separate hideable piece sharing the magazine's set (slot %s): hide it when the magazine is "
                "empty. Same origin as the magazine." % (sp["mesh"], slot)))
            out.append(top)
        sp["_tris"] = geo.stats(ob)["triangles"]
    # the atlas object and its joined parts leave the scene (the exported objects carry the material)
    me = atlas.data
    bpy.data.objects.remove(atlas, do_unlink=True)
    bpy.data.meshes.remove(me)
    for ob in out:
        for sl in ob.material_slots:
            if sl.material is not None and sl.material.name.startswith("M_" + set_name):
                sl.material = m
    return out, socks


# --------------------------------------------------------------------------------------------------------- build
def build_parts(ctx):
    scene.setup_cycles(bpy.context.scene, threads=THREADS, samples=ctx.args.samples)
    out, socks = build_set(ctx, HARDWARE, HW_SET, HW_SLOT, PT.paint_parts, "hw")
    SOCKETS.update(socks)
    return out


def build_mags(ctx):
    scene.setup_cycles(bpy.context.scene, threads=THREADS, samples=ctx.args.samples)
    out, socks = build_set(ctx, MAGS, MAG_SET, MAG_SLOT, PT.paint_mags, "mags")
    SOCKETS.update(socks)
    return out


SOCKETS = {}


def build(ctx):
    only = [o.lower() for o in (ctx.args.only or GROUPS)]
    objs = []
    if "parts" in only:
        objs += build_parts(ctx)
    if "mags" in only:
        objs += build_mags(ctx)
    return objs


# -------------------------------------------------------------------------------------------------------- contract
def write_contract(ctx, specs):
    """art/blender/assets/weapons_parts_contract.json: every part, its slots, its mount, its sockets (metres in the part frame and
    Unreal centimetres), its size and triangle count, the gun sockets of the CHOPPER and the NINE that this round added."""
    u = lambda v: [round(float(v[0]) * 100, 3), round(-float(v[1]) * 100, 3), round(float(v[2]) * 100, 3)]
    data = {"about": "Round 4 parts kit and mounts (lane 2). Part frame: X forward along the bore, Y left, Z up, metres; the part's origin is "
                     "its mount. Unreal = (x, -y, z) x 100. A static mesh's sockets are written from here at import "
                     "(ue_import_guns._put_static_socket). The part sets: Weapon_Parts (slot M_Part_Hardware), Weapon_PartsMags (slot "
                     "M_Part_Mags); lens and reticle are the flat slots M_Part_Lens and M_Part_Reticle.",
            "sets": {HW_SET: {"slot": HW_SLOT, "resolution": 2048, "maps": ["BC", "N", "ORM", "E"]},
                     MAG_SET: {"slot": MAG_SLOT, "resolution": 2048, "maps": ["BC", "N", "ORM"]}},
            "parts": {}}
    old = json.load(open(CONTRACT))["parts"] if os.path.exists(CONTRACT) else {}
    data["parts"].update(old)
    for sp in specs:
        if sp["id"] not in SOCKETS:
            continue
        a = ctx.assets.get(sp["mesh"])
        ob = a["ob"] if a else None
        lo, hi = scene.bounds(ob) if ob is not None else (np.zeros(3), np.zeros(3))
        rec = {"mesh": sp["mesh"], "slot": sp["slot"], "applies_to": sp["applies"], "gun_socket": sp["mount"], "mount": sp["mount_note"],
               "material_slots": [HW_SLOT if sp in HARDWARE else MAG_SLOT] + ([G.LENS_SLOT, G.RET_SLOT] if sp["id"] in ("red_dot", "scope_4x") else []),
               "sockets_m": {k: [round(float(c), 5) for c in v] for k, v in SOCKETS[sp["id"]].items()},
               "sockets_unreal_cm": {k: u(v) for k, v in SOCKETS[sp["id"]].items()},
               "bounds_m": {"min": [round(float(c), 4) for c in lo], "max": [round(float(c), 4) for c in hi]},
               "triangles": sp.get("_tris"), "triangle_budget": sp["budget"]}
        if sp["id"].startswith("mag_"):
            rec["top_round_mesh"] = sp["mesh"] + "_TopRound"
        data["parts"][sp["id"]] = rec
    data["gun_sockets_added_to_the_exported_guns"] = {
        "SK_Chopper": {"Optic": [0.115, 0.0, 0.042], "MuzzleMount": [0.426, 0.0, 0.0], "Underbarrel": [0.305, 0.0, -0.0623],
                       "bones": {"Booster": [0.426, 0.0, 0.0], "FrontSight": [0.409, 0.0, 0.031]}},
        "SK_Nine": {"Laser": [0.156, 0.0, -0.0236], "MuzzleMount": [0.196, 0.0, 0.0], "MagHinge": [0.0177, 0.0, -0.0359]}}
    with open(CONTRACT, "w") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    return data


def on_export(ctx, objs):
    for name, a in ctx.assets.items():
        export.export_asset(a["ob"], ctx.family, a["collision"], a["cover_height"], a["notes"], a["pivot"], a["expect_size"], slots=a["slots"])
    specs = [s for s in HARDWARE + MAGS if s["mesh"] in ctx.assets]
    write_contract(ctx, specs)
    # the part's sockets also go next to its GLB (like SK_RuleArms.sockets.json) and into its manifest record
    m = json.load(open(paths.manifest))
    for sp in specs:
        sk = {k: [round(float(c), 5) for c in v] for k, v in SOCKETS.get(sp["id"], {}).items()}
        with open(os.path.join(paths.glb, sp["mesh"] + ".sockets.json"), "w") as f:
            json.dump({"mesh": sp["mesh"], "frame": "part frame = mount at the origin; X bore, Y left, Z up (metres)",
                       "gun_socket": sp["mount"], "sockets": sk}, f, indent=1)
        e = m["assets"].get(sp["mesh"])
        if e is not None:
            e["sockets"] = sk
            e["mount"] = {"gun_socket": sp["mount"], "note": sp["mount_note"], "applies_to": sp["applies"], "slot": sp["slot"]}
            export.write_manifest([e], [])
    ctx.log("contract %s" % CONTRACT)
