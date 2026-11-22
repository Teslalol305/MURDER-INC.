"""Vehicles: the eleven vehicles of the block (docs/unreal/spec/assets/props.json, ids vehicle_*; 05b-props 2.4).

Method: a concept picture (gpt_image_2_6) turned into a textured body by image-to-3D (hunyuan3d_v3, 500k faces,
PBR maps), downloaded to art/out/gen/vehicles/ (ledger: assets/vehicles_gen.json), then cleaned and completed here:

  1. mi.gen3d: import, length on X with the nose at +X, scaled to the brief's box, warped in x so the generated wheels
     sit on the briefed axles (and in z so their hubs sit at the briefed radius).
  2. Faces classified from the generated maps (colour, roughness, metalness) and their position: paint, trim, head /
     tail / amber lamps, glass, wheels.
  3. Wheels cut out and replaced by modelled wheels at the briefed size (tyre with tread blocks, hubcap / steel /
     alloy faces, lug nuts), wheel-well liners behind them.
  4. Glass split off as 5 mm panes (slot MI_Glass_CarTint); the shell is solidified inward so the cabin has walls,
     and a simple dark interior (floor, dashboard, steering wheel, seats) stands behind the glass.
  5. Decimated to about 110-150k triangles; the generated 4K atlas is kept and rewritten as the asset's set
     Vehicle_<Name> (T_*_BC/N/ORM/E): paint texels become a neutral tint mask with the panel lines and crevices kept
     (baked light removed by a masked low-pass division), lamps get an emissive map.

Slots of a generated body: M_Vehicle_<Name>_Paint (clear coat; BC is a tint mask: multiply by the chart colour),
M_Vehicle_<Name>_Trim and M_Vehicle_<Name>_Lamp (emissive E) all read the set Vehicle_<Name>; shared tiling slots
MI_Glass_CarTint, MI_Rubber_Tyre, MI_Chrome_Polished, MI_Paint_WheelSteel, MI_Alloy_Wheel, MI_Plastic_CarInterior,
MI_Fabric_CarSeat; plates M_Vehicle_Plate_<Code> (0..1 UVs); liveries M_Vehicle_<Name>_Decals (alpha-masked cards
shrink-wrapped 2 mm over the paint).

    build.py build vehicles --export                   all vehicles
    build.py build vehicles --only SM_Vehicle_Sedan --export
    build.py build vehicles --preview --only vehicles_sedan_hero --samples 64
"""
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from mi import bake, export, gen3d, geo, mat, paths, render, scene

FAMILY = {"name": "vehicles", "description": "The eleven vehicles: generated bodies cleaned and completed by script"}

GEN = os.path.join(paths.out, "gen", "vehicles")
FONT = "/usr/share/fonts/opentype/inter/"


def hexcol(h):
    h = h.lstrip("#")
    s = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return tuple(float(v) for v in bake.srgb_decode(s))


# Chart colours of the level (05b 2.4.3)
CHART = {"black": "#14161a", "charcoal": "#2a2d33", "silver": "#8f959c", "white": "#d9d7d0", "maroon": "#6e1a1c",
         "navy": "#1b2a4a", "green": "#16342a", "beige": "#b9b4a6", "mustard": "#c9a23a"}

# ------------------------------------------------------------------------------------------------------ the briefs
# size: brief box (x, y, z); axles: front, rear x; r / tw / rim: tyre radius, tyre width, rim radius;
# belt: base of the side glass; cowl, bpillar: x of the windscreen base and the B pillar; floor: cabin floor z;
# wheel: face style; cls: classification overrides.
SPEC = {
    "Sedan": dict(ws_top=0.30, bn=0.90, src="sedan_hunyuan60k.glb", axis="Y", nose=-1, size=(4.61, 1.85, 1.45), axles=(1.42, -1.38),
                  r=0.325, tw=0.21, rim=0.22, belt=1.02, cowl=0.98, bpillar=-0.20, rear_x=-1.52, floor=0.36,
                  wheel="cap", rear_seat=True, plate="HLS2141", paint="maroon", cover=1.08,
                  tris=60000),
    "SUV": dict(ws_top=0.45, bn=1.12, src="suv_hunyuan60k.glb", axis="Y", nose=-1, size=(4.91, 2.0, 1.82), axles=(1.50, -1.42),
                r=0.40, tw=0.27, rim=0.27, belt=1.22, cowl=1.00, bpillar=-0.12, rear_x=-2.12, floor=0.48,
                wheel="alloy", rear_seat=True, plate="TKV9907", paint="black", cover=1.24, tris=62000),
    "Pickup": dict(ws_top=0.72, bn=1.12, src="pickup_hunyuan60k.glb", axis="Y", nose=-1, size=(5.32, 2.0, 1.78), axles=(1.72, -1.50),
                   r=0.39, tw=0.27, rim=0.25, belt=1.25, cowl=1.22, bpillar=0.05, rear_x=-0.45, floor=0.52,
                   wheel="steel", rear_seat=False, plate="KQB5530", paint="charcoal", cover=1.27, tris=62000),
    "Van": dict(ws_top=1.42, side_glass=(0.60, 1.65, 1.21, 1.95), bn=1.02, src="van_hunyuan60k.glb", axis="Y", nose=-1, size=(5.21, 1.96, 2.19), axles=(1.70, -1.50),
                r=0.36, tw=0.24, rim=0.22, belt=1.16, cowl=1.92, bpillar=0.52, rear_x=0.40, floor=0.50,
                wheel="steel", rear_seat=False, plate="TKV9907", paint="white", cover=2.14, tris=62000),
}

TINT_SETS = {}


# ------------------------------------------------------------------------------------------------------ small sets
def _noise(shape, scale, seed):
    """Smooth value noise in 0..1, tileable (FFT-filtered white noise)."""
    r = np.random.default_rng(seed).standard_normal(shape)
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.fftfreq(shape[1])[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    filt = np.exp(-(f * scale) ** 2)
    a = np.real(np.fft.ifft2(np.fft.fft2(r) * filt))
    a = (a - a.min()) / max(a.max() - a.min(), 1e-9)
    return a.astype(np.float32)


def _normal_from(h, strength):
    gy, gx = np.gradient(h)
    n = np.stack([-gx * strength, gy * strength, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return (n * 0.5 + 0.5).astype(np.float32)


def small_sets(force=False):
    """The shared tiling sets of the vehicles (numpy, 1024 px, seamless). Returns {set: tile_m}."""
    res = 1024
    out = {}

    def done(name):
        return not force and os.path.exists(os.path.join(paths.texture_set(name), "set.json"))

    def put(name, bc, rough, metal, h=None, strength=4.0, tile=0.5, note=""):
        out[name] = tile
        if done(name):
            return
        bc = np.broadcast_to(bc, (res, res, 3)).astype(np.float32)
        ch = {"bc": bc, "rough": np.broadcast_to(rough, (res, res)).astype(np.float32),
              "metal": np.broadcast_to(metal, (res, res)).astype(np.float32)}
        if h is not None:
            ch["normal"] = _normal_from(h, strength)
        bake.write_set(name, ch, meta={"kind": "tiling", "tile_m": tile, "seamless": True, "family": "vehicles",
                                       "note": note, "texel_density_px_per_m": round(res / tile, 1)})

    n1 = _noise((res, res), 60.0, 1)
    n2 = _noise((res, res), 6.0, 2)
    put("TS_Glass_CarTint", np.array(hexcol("#0a0d10")) * (0.95 + 0.1 * n1[..., None]), 0.03 + 0.03 * n1, 0.0,
        note="tinted car glass: translucent in Unreal (opacity about 0.75, IOR 1.52); BC is the tint")
    put("TS_Chrome_Polished", np.full(3, 0.92) * (0.97 + 0.03 * n2[..., None]), 0.05 + 0.06 * n1, 1.0,
        h=n2 * 0.3, strength=1.0)
    put("TS_Alloy_Wheel", np.array([0.62, 0.63, 0.64]) * (0.95 + 0.05 * n2[..., None]), 0.22 + 0.1 * n1, 1.0,
        h=n2 * 0.3, strength=1.0)
    put("TS_Paint_WheelSteel", np.array(hexcol("#2a2c2f")) * (0.85 + 0.25 * n1[..., None]), 0.42 + 0.15 * n1, 0.15,
        h=n2, strength=2.0, note="dark painted steel wheel, dust in the low parts")
    grain = _noise((res, res), 1.2, 3)
    put("TS_Rubber_Tyre", np.array([0.035, 0.034, 0.033]) * (0.85 + 0.3 * n1[..., None]), 0.78 + 0.12 * n1, 0.0,
        h=grain * 0.4 + n1 * 0.2, strength=3.0, note="tyre rubber, slightly greyed")
    put("TS_Plastic_CarInterior", np.array([0.028, 0.027, 0.026]) * (0.9 + 0.2 * n2[..., None]), 0.62 + 0.1 * grain,
        0.0, h=grain, strength=2.5, note="moulded interior plastic with a fine grain")
    yy, xx = np.mgrid[0:res, 0:res]
    weave = (np.sin(xx * 2 * np.pi / 8) * np.sin(yy * 2 * np.pi / 8) * 0.5 + 0.5).astype(np.float32)
    put("TS_Fabric_CarSeat", np.array([0.045, 0.044, 0.046]) * (0.8 + 0.25 * weave[..., None] + 0.2 * n2[..., None]),
        0.92, 0.0, h=weave * 0.5 + n1 * 0.5, strength=3.0, tile=0.25, note="woven seat cloth, charcoal")
    put("TS_Steel_CargoDark", np.array([0.05, 0.05, 0.052]) * (0.8 + 0.4 * n2[..., None]), 0.55 + 0.2 * n1, 0.6,
        h=n1, strength=1.5, tile=1.0, note="bare dark steel of load spaces and engine bays")
    put("TS_Char_Burnt", np.array([0.028, 0.022, 0.018]) * (0.6 + 0.8 * n2[..., None] * n1[..., None] + 0.2 * grain[..., None]),
        0.85 + 0.1 * n1, 0.05, h=n2 * 0.6 + grain * 0.4, strength=4.0, tile=1.0, note="charred, sooty steel and ash")
    return out


def set_material(set_name, slot=None, glass=False, coat=0.0, tint=None, emit_strength=0.0, alpha=False, rough=None):
    """Preview material on a texture set (the set's BC/N/ORM/E files through the UV map). rough: constant
    roughness instead of the ORM's (primer)."""
    slot = slot or ("MI_" + set_name[3:] if set_name.startswith("TS_") else "M_" + set_name)
    m = bpy.data.materials.get(slot)
    if m is not None and m.get("mi_built"):
        return m
    m = m or bpy.data.materials.new(slot)
    m["mi_built"] = True
    m["mi_set"] = set_name
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    d = paths.texture_set(set_name)
    files = mat.find_set_files(d)

    def img(role, srgb):
        if role not in files:
            return None
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(files[role], check_existing=True)
        t.image.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
        return t
    bc = img("BC", True)
    if bc is not None:
        col = bc.outputs["Color"]
        if tint is not None:
            mx = nt.nodes.new("ShaderNodeMix")
            mx.data_type = "RGBA"
            mx.blend_type = "MULTIPLY"
            mx.inputs["Factor"].default_value = 1.0
            nt.links.new(col, mx.inputs["A"])
            mx.inputs["B"].default_value = (*tint, 1.0)
            col = mx.outputs["Result"]
        nt.links.new(col, b.inputs["Base Color"])
        if alpha:
            nt.links.new(bc.outputs["Alpha"], b.inputs["Alpha"])
    orm = img("ORM", False)
    if orm is not None:
        sp = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sp.inputs[0])
        nt.links.new(sp.outputs[1], b.inputs["Roughness"])
        nt.links.new(sp.outputs[2], b.inputs["Metallic"])
    nm = img("N", False)
    if nm is not None:
        nn = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(nm.outputs["Color"], nn.inputs["Color"])
        nt.links.new(nn.outputs[0], b.inputs["Normal"])
    em = img("E", True)
    if em is not None and emit_strength > 0:
        nt.links.new(em.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit_strength
    if rough is not None:
        for l in list(b.inputs["Roughness"].links):
            nt.links.remove(l)
        b.inputs["Roughness"].default_value = rough
    if alpha:
        m.blend_method = "HASHED" if hasattr(m, "blend_method") else None
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.03
    if glass:
        b.inputs["Transmission Weight"].default_value = 1.0
        b.inputs["IOR"].default_value = 1.52
        b.inputs["Roughness"].default_value = 0.02
        if bc is not None:
            for l in list(bc.outputs["Color"].links):
                nt.links.remove(l)
        b.inputs["Base Color"].default_value = (0.42, 0.47, 0.46, 1.0)
        for l in list(b.inputs["Roughness"].links):
            nt.links.remove(l)
    return m


def tiling(name, tile=None):
    """(material, tile_m) of a shared vehicle tiling set by its TS_ name."""
    info = bake.read_set(name) or {}
    t = tile or info.get("tile_m", 0.5)
    m = set_material(name, glass=(name == "TS_Glass_CarTint"))
    m["mi_tile_m"] = t
    return m, t


def put_mat(ob, m, tile=None):
    """Single material (and box UVs in metres for tiling slots)."""
    ob.data.materials.clear()
    ob.data.materials.append(m)
    if tile:
        geo.uv_world_box(ob, tile)
    return ob


# ------------------------------------------------------------------------------------------------------- wheels
def _rot_to_y(ob):
    """Revolved parts are built around +Z; turn them so the axle runs along +Y (outboard face toward +Y)."""
    geo.transform(ob, rot=(-90, 0, 0))
    return ob


def tyre(r, tw, rim_r, seg=72, name="Tyre"):
    """Tyre around +Y: bulged sidewall, shoulders, three circumferential grooves and staggered tread blocks."""
    h = r - rim_r
    w = tw / 2
    prof = [(rim_r + 0.004, -w * 0.80), (rim_r + 0.25 * h, -w * 0.97), (rim_r + 0.62 * h, -w * 1.0),
            (r - 0.022, -w * 0.94), (r - 0.006, -w * 0.84), (r, -w * 0.74)]
    for a in (-0.42, 0.0, 0.42):                      # grooves
        prof += [(r, w * (a - 0.07)), (r - 0.008, w * (a - 0.05)), (r - 0.008, w * (a + 0.05)), (r, w * (a + 0.07))]
    prof += [(r, w * 0.74), (r - 0.006, w * 0.84), (r - 0.022, w * 0.94), (rim_r + 0.62 * h, w * 1.0),
             (rim_r + 0.25 * h, w * 0.97), (rim_r + 0.004, w * 0.80)]
    ob = geo.revolve(prof, seg, name=name)
    co, _ = geo.arrays(ob)
    rr = np.hypot(co[:, 0], co[:, 1])
    ang = np.arctan2(co[:, 1], co[:, 0])
    k = np.floor((ang + np.pi) / (2 * np.pi) * seg).astype(int)
    z = co[:, 2]
    # lateral sipes: every 3rd segment sinks on the outer ribs, offset between the two halves
    tread = rr > r - 0.0015
    sipe = ((k % 3 == 0) & (z > w * 0.1)) | (((k + 1) % 3 == 0) & (z < -w * 0.1))
    s = np.where(tread & sipe, (r - 0.006) / np.maximum(rr, 1e-6), 1.0)
    co[:, 0] *= s
    co[:, 1] *= s
    geo.set_verts(ob, co)
    geo.recalc_normals(ob)
    geo.smooth_by_angle(ob, 40)
    return _rot_to_y(ob)


def rim(style, rim_r, tw, name="Rim"):
    """Wheel face around +Y (outboard +Y). Returns a list of (object, slot key)."""
    w = tw / 2
    parts = []
    # barrel (seen through the spokes and from below)
    barrel = geo.revolve([(rim_r - 0.012, -w * 0.82), (rim_r - 0.012, w * 0.70), (rim_r + 0.012, w * 0.74),
                          (rim_r + 0.014, w * 0.80), (rim_r - 0.004, w * 0.82)], 64, name=name + "_Barrel")
    if style == "steel":
        face = geo.revolve([(rim_r - 0.004, w * 0.82), (rim_r - 0.010, w * 0.72), (rim_r * 0.80, w * 0.62),
                            (rim_r * 0.70, w * 0.66), (rim_r * 0.55, w * 0.56), (rim_r * 0.40, w * 0.40),
                            (0.10, w * 0.44), (0.075, w * 0.48), (0.0, w * 0.48)], 64, name=name + "_Face")
        parts += [(barrel, "steel"), (face, "steel")]
        # vent holes, read as dark pockets
        for i in range(6):
            a = 2 * math.pi * i / 6 + 0.26
            p = geo.cylinder(0.026, 0.006, 16, name=name + "_Vent")
            geo.transform(p, loc=(math.cos(a) * rim_r * 0.62, math.sin(a) * rim_r * 0.62, w * 0.615))
            parts.append((p, "tyre"))
        cap = geo.revolve([(0.058, w * 0.47), (0.056, w * 0.52), (0.045, w * 0.56), (0.0, w * 0.57)], 32, name=name + "_Cap")
        parts.append((cap, "chrome"))
        nuts = 5
    elif style == "cap":
        face = geo.revolve([(rim_r - 0.004, w * 0.82), (rim_r - 0.010, w * 0.74), (rim_r * 0.80, w * 0.66),
                            (0.08, w * 0.50), (0.0, w * 0.50)], 64, name=name + "_Face")
        parts += [(barrel, "steel"), (face, "steel")]
        cap = geo.revolve([(rim_r + 0.006, w * 0.80), (rim_r + 0.008, w * 0.86), (rim_r * 0.96, w * 0.93),
                           (rim_r * 0.88, w * 0.95), (rim_r * 0.84, w * 0.90), (rim_r * 0.72, w * 0.92),
                           (rim_r * 0.42, w * 1.02), (rim_r * 0.36, w * 1.08), (rim_r * 0.30, w * 1.04),
                           (rim_r * 0.12, w * 1.10), (0.0, w * 1.12)], 64, name=name + "_Hubcap")
        parts.append((cap, "chrome"))
        for i in range(10):                          # cooling slots of the hubcap
            a = 2 * math.pi * i / 10
            s = geo.box((0.075, 0.016, 0.012), bevel=0.003, base=False, name=name + "_Slot")
            geo.transform(s, rot=(0, 0, math.degrees(a)))
            geo.transform(s, loc=(math.cos(a) * rim_r * 0.60, math.sin(a) * rim_r * 0.60, w * 0.965))
            parts.append((s, "tyre"))
        nuts = 0
    else:  # alloy, five spokes
        face = geo.revolve([(rim_r - 0.004, w * 0.82), (rim_r - 0.012, w * 0.66), (rim_r - 0.03, w * 0.62),
                            (rim_r - 0.03, w * 0.52)], 64, name=name + "_Lip")
        dish = geo.revolve([(rim_r - 0.03, w * 0.30), (0.0, w * 0.30)], 48, name=name + "_Dish")
        hub = geo.revolve([(0.11, w * 0.40), (0.11, w * 0.62), (0.085, w * 0.70), (0.0, w * 0.71)], 40, name=name + "_Hub")
        parts += [(barrel, "alloy"), (face, "alloy"), (dish, "tyre"), (hub, "alloy")]
        for i in range(5):
            a = 2 * math.pi * i / 5
            L = rim_r - 0.09
            s = geo.box((L, 0.05, 0.05), bevel=0.012, base=False, name=name + "_Spoke")
            co, _ = geo.arrays(s)
            t = (co[:, 0] + L / 2) / L                 # taper and dish the spoke toward the hub
            co[:, 1] *= 1.25 - 0.45 * t
            co[:, 2] += -0.02 * t
            geo.set_verts(s, co)
            geo.transform(s, loc=(0.1 + L / 2 - 0.02, 0, w * 0.60))
            geo.transform(s, rot=(0, 0, math.degrees(a)))
            parts.append((s, "alloy"))
        cap = geo.revolve([(0.04, w * 0.70), (0.0, w * 0.74)], 24, name=name + "_Cap")
        parts.append((cap, "tyre"))
        nuts = 5
    for i in range(nuts):
        a = 2 * math.pi * i / nuts
        n = geo.cylinder(0.011, 0.018, 6, bevel=0.002, name=name + "_Nut")
        rn = 0.072 if style == "steel" else 0.08
        geo.transform(n, loc=(math.cos(a) * rn, math.sin(a) * rn, w * (0.44 if style == "steel" else 0.66)))
        parts.append((n, "chrome"))
    for p, _k in parts:
        _rot_to_y(p)
    return parts


def wheel(spec, name, twin=False):
    """One wheel (tyre + face) at the origin, axle along Y, outboard +Y. Returns {slot key: [objects]}."""
    r, tw, rr = spec["r"], spec["tw"], spec["rim"]
    out = {}
    offs = [0.0] if not twin else [0.0, -(tw + 0.02)]
    for k, dy in enumerate(offs):
        t = tyre(r, tw, rr, name=name + "_Tyre%d" % k)
        geo.transform(t, loc=(0, dy, 0))
        out.setdefault("tyre", []).append(t)
        style = spec["wheel"] if k == 0 else "steel"
        for p, key in rim(style, rr, tw, name=name + "_Rim%d" % k):
            geo.transform(p, loc=(0, dy, 0))
            out.setdefault(key, []).append(p)
    return out


def well_liner(r, depth, name="Well"):
    """Half tube over a wheel (radius r + 0.06), axle along Y from 0 to -depth (the inboard side), with an inner
    wall: hides the hollow body behind a cut-out wheel."""
    R = r + 0.06
    a = np.linspace(-0.12 * math.pi, 1.12 * math.pi, 28)
    pts = [(math.cos(t) * R, math.sin(t) * R) for t in a]
    bm = bmesh.new()
    ring_o = [bm.verts.new((x, 0.0, z)) for x, z in pts]
    ring_i = [bm.verts.new((x, -depth, z)) for x, z in pts]
    for i in range(len(pts) - 1):
        bm.faces.new((ring_o[i], ring_o[i + 1], ring_i[i + 1], ring_i[i]))
    c = bm.verts.new((0.0, -depth, 0.0))
    for i in range(len(pts) - 1):
        bm.faces.new((ring_i[i], ring_i[i + 1], c))
    ob = geo.new(name, bm)
    geo.recalc_normals(ob, inside=True)
    return ob


# ------------------------------------------------------------------------------------------------- body pipeline
CLS = {"paint": 0, "trim": 1, "head": 2, "tail": 3, "amber": 4, "glass": 5, "wheel": 6, "drop": 7, "inside": 9}


def find_wheels(ob, spec):
    """x of the front and rear ground contacts, the outer |y| of the tyres and the hub height of the generated
    wheels (before the warp)."""
    co = gen3d.verts(ob)
    g = co[:, 2] < 0.025
    res = []
    for s in (1, -1):
        sel = g & (co[:, 0] * s > 0.3)
        xa = float(np.median(co[sel, 0]))
        yo = float(np.percentile(np.abs(co[sel, 1]), 98))
        res.append((xa, yo))
    c, n, a = gen3d.face_arrays(ob)
    hubs = []
    for xa, yo in res:
        zc = spec["r"]
        for _ in range(3):           # centroid of the side-facing faces of the wheel disc
            d = np.hypot(c[:, 0] - xa, c[:, 2] - zc)
            k = (d < spec["r"] * 0.9) & (np.abs(c[:, 1]) > yo - spec["tw"]) & (np.abs(n[:, 1]) > 0.6)
            if k.sum() < 20:
                break
            zc = float(np.average(c[k, 2], weights=a[k]))
            xa = float(np.average(c[k, 0], weights=a[k]))
        hubs.append(zc)
    return res, hubs


def face_neighbours(ob, k=3):
    """(n, k) indices of faces sharing an edge with each face (-1 padded)."""
    me = ob.data
    n = len(me.polygons)
    ek = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("edge_index", ek)
    lt = np.empty(n, dtype=np.int64)
    me.polygons.foreach_get("loop_total", lt)
    fi = np.repeat(np.arange(n), lt)
    order = np.argsort(ek, kind="stable")
    e, f = ek[order], fi[order]
    same = e[1:] == e[:-1]
    a, b = f[:-1][same], f[1:][same]
    nb = np.full((n, k), -1, dtype=np.int64)
    cnt = np.zeros(n, dtype=np.int64)
    for x, y in ((a, b), (b, a)):
        for i, j in zip(x, y):
            if cnt[i] < k:
                nb[i, cnt[i]] = j
                cnt[i] += 1
    return nb


def classify(ob, tex, spec):
    """Class per face (CLS) from the generated maps and the face position."""
    c, n, a = gen3d.face_arrays(ob)
    rgb, rough, metal = gen3d.face_samples(ob, tex)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    sat = rgb.max(1) - rgb.min(1)
    L = spec["size"][0] / 2
    k = spec.get("cls", {})
    cls = np.zeros(len(c), dtype=np.int32)
    cls[lum < k.get("trim_lum", 0.06)] = CLS["trim"]
    # glass: dark faces in the greenhouse (above the belt, between the rear screen base and the cowl), not the
    # wipers at the cowl and not the B pillar
    gx0 = spec.get("glass_x0", spec["rear_x"] - 0.12)
    gx1 = spec.get("glass_x1", spec["cowl"] + 0.08)
    glass = ((lum < k.get("glass_lum", 0.06)) & (c[:, 2] > spec["belt"] - 0.05) & (c[:, 0] > gx0) & (c[:, 0] < gx1)
             & (n[:, 2] > -0.3) & (c[:, 2] < spec["size"][2] - 0.08))
    glass &= ~((c[:, 0] > spec["cowl"] - 0.30) & (c[:, 2] < spec["belt"] + 0.07))
    glass &= ~((np.abs(c[:, 0] - spec["bpillar"]) < 0.05) & (np.abs(c[:, 1]) > spec["size"][1] / 2 - 0.35))
    if "ws_top" in spec:              # windscreen by position: everything between the A pillars, cowl to roof
        hwz = spec["size"][1] / 2 - spec.get("ws_inset", 0.17)
        ws = ((c[:, 0] > spec["ws_top"] - 0.03) & (c[:, 0] < spec["cowl"] + 0.03) & (np.abs(c[:, 1]) < hwz)
              & (c[:, 2] > spec["belt"] + 0.03) & (c[:, 2] < spec["size"][2] - 0.05) & (n[:, 0] > 0.25))
        glass |= ws
    if "side_glass" in spec:          # side glass by position (vans with light-coloured glass in the picture)
        x0, x1, z0, z1 = spec["side_glass"]
        glass |= ((c[:, 0] > x0) & (c[:, 0] < x1) & (c[:, 2] > z0) & (c[:, 2] < z1) & (np.abs(n[:, 1]) > 0.75))
    if "glass" in spec:
        glass = spec["glass"](c, n, lum, rough, glass)
    # glass highlights: faces in the greenhouse mostly surrounded by glass become glass (majority filter)
    region = ((c[:, 2] > spec["belt"] - 0.05) & (c[:, 2] < spec["size"][2] - 0.08) & (c[:, 0] > gx0) & (c[:, 0] < gx1)
              & (lum < 0.45))
    nb = face_neighbours(ob)
    for _ in range(8):
        g = glass.astype(np.float32)
        frac = (g[nb] * (nb >= 0)).sum(1) / np.maximum((nb >= 0).sum(1), 1)
        glass = glass | (region & (frac >= 0.6))
    # generated faces inside the cabin below the window line (seen through the glass): interior
    hw = spec["size"][1] / 2
    inside = ((np.abs(c[:, 1]) < hw - 0.25) & (c[:, 2] > spec["floor"] - 0.05) & (c[:, 2] < spec["belt"] + 0.05)
              & (c[:, 0] > spec["rear_x"] + 0.10) & (c[:, 0] < spec["cowl"] - 0.15) & ~glass)
    # the dash top under the windscreen (generated, light): interior as well
    inside |= ((np.abs(c[:, 1]) < hw - 0.25) & (c[:, 2] > spec["belt"] - 0.10) & (c[:, 2] < spec["belt"] + 0.14)
               & (c[:, 0] > spec["cowl"] - 0.45) & (c[:, 0] < spec["cowl"] + 0.02) & ~glass & (n[:, 2] > -0.2)
               & (lum > 0.06))
    cls[glass] = CLS["glass"]
    if spec.get("cabin_inside", True):
        cls[inside] = CLS["inside"]
    bn = spec.get("bn", spec["belt"] - 0.12)
    hz = k.get("head_z", (bn - 0.34, bn - 0.06))
    head = ((c[:, 0] > L - k.get("head_depth", 0.42)) & (c[:, 2] > hz[0]) & (c[:, 2] < hz[1]) & (n[:, 0] > 0.15)
            & (np.abs(c[:, 1]) > k.get("grille_hw", 0.30)) & (lum > 0.08) & (lum < k.get("head_lum", 0.47))
            & (sat < 0.035))
    cls[head] = CLS["head"]
    red = (rgb[:, 0] > 0.08) & (rgb[:, 0] > 3 * rgb[:, 1]) & (c[:, 0] < 0)
    cls[red] = CLS["tail"]
    amber = (rgb[:, 0] > 0.2) & (rgb[:, 1] > 0.05) & (rgb[:, 1] < 0.6 * rgb[:, 0]) & (rgb[:, 2] < 0.4 * rgb[:, 1])
    amber &= (np.abs(n[:, 2]) < 0.6) | (c[:, 2] > spec["size"][2] - 0.15)        # lenses, roof markers; not floors
    amber &= metal < 0.5
    cls[amber] = CLS["amber"]
    return cls, c, n


def wheel_mask(c, spec, wheels):
    m = np.zeros(len(c), dtype=bool)
    r = spec["r"]
    for xa, yo, twin in wheels:
        d = np.hypot(c[:, 0] - xa, c[:, 2] - r)
        rad = np.where(c[:, 2] < r, r + 0.045, r + 0.03)
        inner = yo - spec["tw"] * (2.1 if twin else 1.0) - 0.07
        m |= (d < rad) & (np.abs(c[:, 1]) > inner)
    return m


def raster_classes(ob, cls, size):
    """Class map in UV space (uint8, 255 = no face): every face drawn with its class."""
    from PIL import Image, ImageDraw
    W, H = size
    me = ob.data
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    px = np.stack([uv[:, 0] * W, (1.0 - uv[:, 1]) * H], 1)
    ls = np.empty(len(me.polygons), dtype=np.int64)
    lt = np.empty(len(me.polygons), dtype=np.int64)
    me.polygons.foreach_get("loop_start", ls)
    me.polygons.foreach_get("loop_total", lt)
    im = Image.new("L", (W, H), 255)
    dr = ImageDraw.Draw(im)
    order = np.argsort(np.where(cls == CLS["paint"], 0, 1), kind="stable")      # paint first, details over it
    for i in order:
        s, t = ls[i], lt[i]
        pts = [tuple(p) for p in px[s:s + t]]
        dr.polygon(pts, fill=int(cls[i]), outline=int(cls[i]))
    return np.asarray(im)


def _lowpass(a, m, size=384):
    """Masked low-pass: average of a over the mask m at about 1/size of the map, back at full size."""
    from PIL import Image
    H, W = a.shape
    A = Image.fromarray((a * m).astype(np.float32), "F").resize((size, size), Image.BOX)
    M = Image.fromarray(m.astype(np.float32), "F").resize((size, size), Image.BOX)
    A = np.asarray(A)
    M = np.asarray(M)
    lo = A / np.maximum(M, 1e-4)
    # fill empty cells from their neighbours so the upsample does not pull toward zero
    for _ in range(6):
        e = M < 1e-3
        if not e.any():
            break
        p = np.pad(lo, 1, mode="edge")
        pm = np.pad((~e).astype(np.float32), 1)
        s = sum(np.roll(np.roll(p, dy, 0), dx, 1)[1:-1, 1:-1] * np.roll(np.roll(pm, dy, 0), dx, 1)[1:-1, 1:-1]
                for dy in (-1, 0, 1) for dx in (-1, 0, 1))
        cnt = sum(np.roll(np.roll(pm, dy, 0), dx, 1)[1:-1, 1:-1] for dy in (-1, 0, 1) for dx in (-1, 0, 1))
        lo = np.where(e & (cnt > 0), s / np.maximum(cnt, 1e-6), lo)
        M = np.where(e & (cnt > 0), 1.0, M)
    return np.asarray(Image.fromarray(lo.astype(np.float32), "F").resize((W, H), Image.BILINEAR))


def paint_uv(cmap):
    """UV of a texel deep inside a paint island: parts modelled here (door leaves, frames) map all their UVs to it
    and so carry the plain tint-mask paint of the body."""
    from PIL import Image
    p = Image.fromarray(((cmap == CLS["paint"]) * 255).astype(np.uint8)).resize((256, 256), Image.BOX)
    a = np.asarray(p) > 250
    k = a.copy()
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            k &= np.roll(np.roll(a, dy, 0), dx, 1)
    ys, xs = np.nonzero(k if k.any() else a)
    i = len(ys) // 2
    return [float((xs[i] + 0.5) / 256), float(1.0 - (ys[i] + 0.5) / 256)]


def uv_point(ob, set_name):
    """Every UV of ob at the set's paint_uv (uniform paint from a body atlas)."""
    info = bake.read_set(set_name) or {}
    u, v = info.get("paint_uv", (0.5, 0.5))
    me = ob.data
    uvl = me.uv_layers.get(geo.UV) or me.uv_layers.new(name=geo.UV)
    uvl.data.foreach_set("uv", np.tile(np.array([u, v], np.float32), len(me.loops)))
    return ob


def body_set(set_name, cmap, tex, meta):
    """Rewrite the generated atlas as the asset's set: paint -> tint mask, lamps -> emissive."""
    bc = tex["bc"]
    lum = bc @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    paint = (cmap == CLS["paint"]).astype(np.float32)
    # baked light out: normalise by the median paint brightness, keep crevices and panel lines (darker than the
    # panel around them) and squeeze the rest of the variation
    # (review fix) divide by a coarse masked low-pass (about 85 px cells on a 4K atlas) instead of the global median:
    # the soft blotches of baked light and the shading of the dents go, the panel lines and crevices stay
    if paint.any():
        lo = _lowpass(lum, paint > 0, size=48)
        detail = np.clip(lum / np.maximum(lo, 1e-4), 0.35, 1.25)
    else:
        detail = np.ones_like(lum)
    detail = np.where(detail < 0.78, detail, 0.78 + (detail - 0.78) * 0.30)
    detail = detail / (0.78 + 0.22 * 0.30)
    pbc = np.clip(0.86 * detail, 0.0, 0.95)[..., None] * np.array([1.0, 1.0, 1.0], dtype=np.float32)
    out_bc = np.where(paint[..., None] > 0, pbc, bc).astype(np.float32)
    rough = tex["rough"].copy()
    metal = tex["metal"].copy()
    rough = np.where(paint > 0, 0.30 + 0.06 * (1.0 - detail), rough)
    metal = np.where(paint > 0, 0.0, metal)
    lamps = np.isin(cmap, [CLS["head"], CLS["tail"], CLS["amber"]])
    rough = np.where(lamps, 0.06, rough)
    metal = np.where(lamps, np.minimum(metal, 0.3), metal)
    emit = np.zeros_like(bc)
    s = np.clip(lum / 0.35, 0.35, 1.0)[..., None]
    emit = np.where((cmap == CLS["head"])[..., None], np.array([1.0, 0.93, 0.80]) * s, emit)
    emit = np.where((cmap == CLS["tail"])[..., None], np.array([1.0, 0.06, 0.03]) * np.clip(lum / 0.12, 0.4, 1.0)[..., None], emit)
    emit = np.where((cmap == CLS["amber"])[..., None], np.array([1.0, 0.45, 0.05]), emit)
    # paint normals: the coarse low-pass taken out too (dents, ripples), fine detail kept at 80 %
    nrm = tex["normal"].astype(np.float32)
    if paint.any():
        v = nrm * 2.0 - 1.0
        pm = paint > 0
        for i in (0, 1):
            v[..., i] = np.where(pm, (v[..., i] - _lowpass(v[..., i], pm, size=48)) * 0.8, v[..., i])
        v[..., 2] = np.where(pm, np.sqrt(np.clip(1.0 - v[..., 0] ** 2 - v[..., 1] ** 2, 0.0, 1.0)), v[..., 2])
        nrm = np.clip(v * 0.5 + 0.5, 0.0, 1.0)
    f = np.flipud                       # write_set wants row 0 at the bottom (UV orientation)
    ch = {"bc": f(out_bc), "rough": f(rough.astype(np.float32)), "metal": f(metal.astype(np.float32)),
          "normal": f(nrm), "emit": f(emit.astype(np.float32))}
    info = dict(meta)
    info["paint_uv"] = paint_uv(cmap)
    info.update({"kind": "unique", "note": "generated atlas (hunyuan3d_v3) rewritten: paint texels are a neutral tint "
                 "mask (0.86 x detail, multiply by the chart colour, clear coat), lamps carry E (head, tail, amber)"})
    return bake.write_set(set_name, ch, meta=info)


def solidify(ob, thickness, inner_slot):
    md = ob.modifiers.new("Solidify", "SOLIDIFY")
    md.thickness = thickness
    md.offset = -1.0
    md.use_rim = True
    md.use_even_offset = False
    md.material_offset = inner_slot
    md.material_offset_rim = inner_slot
    scene.select_only(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=md.name)
    mi = np.empty(len(ob.data.polygons), dtype=np.int32)
    ob.data.polygons.foreach_get("material_index", mi)
    gen3d.set_face_materials(ob, np.minimum(mi, len(ob.data.materials) - 1))


def gen_body(ctx, key, spec, name):
    """Load, fit, classify and split a generated body. Returns dict(body, glass, wheels, cls info, plates)."""
    path = os.path.join(GEN, spec["src"])
    ob, tex = gen3d.load(path, name + "_Gen", ctx.col)
    gen3d.orient(ob, spec["axis"], spec["nose"])
    ar = nose_check(ob, key)
    ctx.log("%s: nose check, sloped screen area +X %.4f / -X %.4f" % (key, ar[0], ar[1]))
    gen3d.fit_box(ob, spec["size"])
    geo.recalc_normals(ob)
    contacts, hubs = find_wheels(ob, spec)
    (xf, yf), (xr, yr) = contacts
    L = spec["size"][0] / 2
    ax_f, ax_r = spec["axles"]
    gen3d.warp(ob, 0, [(-L, -L), (xr, ax_r), (xf, ax_f), (L, L)])
    zc = float(np.mean(hubs))
    H = spec["size"][2]
    if abs(zc - spec["r"]) > 0.01:
        gen3d.warp(ob, 2, [(0.0, 0.0), (zc, spec["r"]), (H, H)])
    ctx.log("%s: contacts x %.3f / %.3f -> %.2f / %.2f, hub z %.3f -> %.3f, tyre |y| %.3f" % (
        key, xf, xr, ax_f, ax_r, zc, spec["r"], max(yf, yr)))
    cls, c, n = classify(ob, tex, spec)
    cls = class_vote(ob, cls, spec.get("vote", 2))
    yo = max(yf, yr)
    wheels = [(ax_f, yo, False), (ax_r, yo, spec.get("twin", False))]
    wm = wheel_mask(c, spec, wheels)
    cls[wm] = CLS["wheel"]
    if "drop" in spec:
        cls[spec["drop"](c, n, cls)] = CLS["drop"]
    if "reclass" in spec:
        spec["reclass"](c, n, cls)
    return ob, tex, cls, c, n, yo


# ---------------------------------------------------------------------------------------------------- interior
def interior(spec, name, hw_in):
    """Dashboard, steering wheel (driver on +Y), front seats, rear bench, floor: dark, simple, behind the glass."""
    parts = {"interior": [], "seat": []}
    cowl, bp, belt, fl = spec["cowl"], spec["bpillar"], spec["belt"], spec["floor"]
    w = hw_in
    # floor
    rear = spec.get("cabin_rear", spec["rear_x"] + 0.15)
    f = geo.box((cowl - rear + 0.1, 2 * w, 0.03), bevel=0.0, name=name + "_Floor")
    geo.transform(f, loc=((cowl + rear) / 2 - 0.05, 0, fl - 0.03))
    parts["interior"].append(f)
    # dashboard: a slab under the windscreen base with a rounded top and an instrument hood
    dash = geo.box((0.42, 2 * w - 0.04, belt - fl - 0.12), bevel=0.03, name=name + "_Dash")
    geo.transform(dash, loc=(cowl - 0.30, 0, fl + 0.10))
    hood = geo.box((0.16, 0.42, 0.07), bevel=0.025, name=name + "_Hood")
    geo.transform(hood, loc=(cowl - 0.47, 0.37 * w / 0.8, belt - 0.03))
    parts["interior"] += [dash, hood]
    # steering wheel and column
    sx, sy, sz = cowl - 0.62, 0.37 * w / 0.8, belt - 0.06
    rim_ = geo.torus(0.185, 0.016, 40, 10, name=name + "_Wheel")
    hubw = geo.cylinder(0.05, 0.04, 20, bevel=0.01, base=False, name=name + "_Boss")
    sp = geo.box((0.34, 0.03, 0.012), bevel=0.004, base=False, name=name + "_Spoke")
    col = geo.cylinder(0.03, 0.40, 12, name=name + "_Column")
    geo.transform(col, loc=(0, 0, -0.42))
    sw = geo.join([rim_, hubw, sp, col])
    geo.transform(sw, rot=(0, -62, 0))
    geo.transform(sw, loc=(sx, sy, sz))
    parts["interior"].append(sw)

    av = spec["size"][2] - 0.10 - fl          # floor to the inside of the roof

    def seat(x, y, width, name_):
        cush = geo.box((0.50, width, 0.13 * av), bevel=0.04, name=name_ + "_Cushion")
        geo.transform(cush, loc=(x + 0.05, y, fl + 0.20 * av))
        back = geo.box((0.12, width, 0.55 * av), bevel=0.04, name=name_ + "_Back")
        geo.transform(back, rot=(0, -14, 0))
        geo.transform(back, loc=(x - 0.20, y, fl + 0.30 * av))
        out = [cush, back]
        if width < 0.7:
            hr = geo.box((0.10, 0.26, 0.15 * av), bevel=0.04, name=name_ + "_Rest")
            geo.transform(hr, rot=(0, -14, 0))
            geo.transform(hr, loc=(x - 0.34, y, fl + 0.86 * av))
            out.append(hr)
        return out
    fx = spec.get("seat_x", bp - 0.12)
    for y in (0.38 * w / 0.8, -0.38 * w / 0.8):
        parts["seat"] += seat(fx, y, 0.50, name + "_Seat")
    if spec.get("rear_seat"):
        parts["seat"] += seat(spec.get("bench_x", fx - 0.85), 0.0, 2 * w - 0.16, name + "_Bench")
    return parts


# ------------------------------------------------------------------------------------------------------- plates
PLATES = {"HLS2141": "HLS·2141", "TKV9907": "TKV·9907", "KQB5530": "KQB·5530", "LWG4418": "LWG·4418",
          "T5K83": "T·5K83"}


def plate_set(code, force=False):
    name = "Vehicle_Plate_" + code
    js = os.path.join(paths.texture_set(name), "set.json")
    if not force and os.path.exists(js):
        with open(js) as fh:
            if json.load(fh).get("text_fit"):
                return name
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1024, 512
    taxi = code.startswith("T")
    bgc = (240, 198, 58) if taxi else (241, 239, 230)
    navy = (22, 38, 79)
    im = Image.new("RGB", (W, H), bgc)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, W - 7, H - 7), 36, outline=navy, width=14)
    f1 = ImageFont.truetype(FONT + "Inter-Bold.otf", 70)
    f2 = ImageFont.truetype(FONT + "InterDisplay-Black.otf", 250)
    d.text((W / 2, 70), "NEW YORK", font=f1, fill=navy, anchor="mm")
    tw = d.textlength(PLATES[code], font=f2)
    if tw > 0.85 * W:                      # (review fix) the number fits 85 % of the plate width
        f2 = ImageFont.truetype(FONT + "InterDisplay-Black.otf", int(250 * 0.85 * W / tw))
    d.text((W / 2, 280), PLATES[code], font=f2, fill=navy, anchor="mm")
    d.rectangle((30, H - 100, W - 30, H - 40), fill=navy if taxi else (217, 162, 28))
    for x in (70, W - 70):                                  # mounting screws
        d.ellipse((x - 16, 40 - 16, x + 16, 40 + 16), fill=(150, 150, 150))
    a = np.asarray(im, dtype=np.float32) / 255.0
    lin = bake.srgb_decode(a)
    rng = np.random.default_rng(len(code))
    grime = _noise((H, W), 40.0, len(code))[..., None]
    lin = lin * (0.82 + 0.18 * grime)
    ink = (np.abs(a - np.array(bgc) / 255.0).sum(-1) > 0.2).astype(np.float32)
    h = ink * 0.6 + 0.02 * rng.random((H, W))
    f = np.flipud
    bake.write_set(name, {"bc": f(lin.astype(np.float32)), "rough": f((0.45 - 0.1 * ink).astype(np.float32)),
                          "metal": np.full((H, W), 0.25, np.float32), "normal": f(_normal_from(h.astype(np.float32), 6.0))},
                   meta={"kind": "unique", "family": "vehicles", "text_fit": 0.85, "note": "licence plate %s "
                         "(invented), 0..1 UVs over the face, 0.30 x 0.15 m" % PLATES[code]})
    return name


def plate(code, at, facing, size=(0.30, 0.15), name="Plate"):
    """Plate card at 'at' (centre of the face), facing +X (1) or -X (-1); slot M_Vehicle_Plate_<code>."""
    w, h = size
    ob = geo.box((0.006, w, h), bevel=0.0015, base=False, name=name)
    me = ob.data
    uvl = me.uv_layers.get(geo.UV) or me.uv_layers.new(name=geo.UV)
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            u = (v.y / w + 0.5) if facing > 0 else (0.5 - v.y / w)
            uvl.data[li].uv = (u, v.z / h + 0.5)
    geo.transform(ob, loc=at)
    m = set_material(plate_set(code), slot="M_Vehicle_Plate_" + code)
    ob.data.materials.append(m)
    return ob


def find_plate(c, n, cls, front):
    """Centre and size (w, h) of the generated plate: light faces facing out of the nose or tail, low and central."""
    s = 1 if front else -1
    k = (n[:, 0] * s > 0.7) & (np.abs(c[:, 1]) < 0.25) & (c[:, 2] < 1.1) & (c[:, 0] * s > 0)
    if not k.any():
        return None
    x = c[k, 0]
    xe = x.max() if front else x.min()
    k2 = k & (np.abs(c[:, 0] - xe) < 0.25)
    kw = k2 & (cls == CLS["paint"])
    if kw.sum() > 8:
        y0, y1 = np.percentile(c[kw, 1], [2, 98])
        z0, z1 = np.percentile(c[kw, 2], [2, 98])
        w = float(np.clip(y1 - y0 + 0.02, 0.30, 0.40))
        h = float(np.clip(z1 - z0 + 0.02, 0.15, 0.22))
        zc = (z0 + z1) / 2
        xc = np.percentile(c[kw, 0], 95 if front else 5)
        return np.array([xc, (y0 + y1) / 2, zc, w, h])
    return np.array([np.percentile(c[k2, 0], 95 if front else 5), 0.0, np.median(c[k2, 2]), 0.30, 0.15])


# ------------------------------------------------------------------------------------------------------ assembly
def finish(ob, dirt=0.35):
    """Wear: dirt and road splash rising from the sills, a little everywhere."""
    geo.ensure_wear(ob)
    co, _ = geo.arrays(ob)
    z = co[:, 2]
    w = np.zeros((len(co), 4), dtype=np.float32)
    w[:, 0] = np.clip(0.08 + (0.6 - z) / 0.6, 0, 1) * dirt
    w[:, 3] = np.clip((0.45 - z) / 0.45, 0, 1) * 0.6
    geo.set_wear(ob, w)
    return ob


def dup(ob, name=None):
    cp = scene.duplicate(ob, name=name or ob.name + "_Copy", linked=False)
    return cp


def slot_mats(key, spec):
    """Materials of the generated shell, in slot order: Paint, Trim, Lamp, [Hazard], [Paint2], Interior (last)."""
    set_name = spec.get("set", "Vehicle_" + key)
    base = "M_Vehicle_" + key
    tint = hexcol(CHART[spec["paint"]]) if spec["paint"] in CHART else hexcol(spec["paint"])
    ms = [set_material(set_name, slot=base + "_Paint", coat=1.0, tint=tint),
          set_material(set_name, slot=base + "_Trim"),
          set_material(set_name, slot=base + "_Lamp")]
    if spec.get("hazard_slot"):
        ms.append(set_material(set_name, slot=base + "_Hazard"))
    if spec.get("paint2"):
        t2 = hexcol(spec.get("paint2_colour", "#d9d7d0"))
        ms.append(set_material(set_name, slot=base + "_PaintCab", coat=1.0, tint=t2))
    ms.append(tiling("TS_Plastic_CarInterior")[0])
    return ms


# ------------------------------------------------------------------------------------------------ review fixes
def nose_check(ob, key):
    """The windscreen must be at +X: more up-tilted area facing an end in the upper half of the body at +X than at
    -X (a windscreen slopes, a tail is flat or carries a smaller rear screen). Raises when the nose is reversed."""
    c, n, a = gen3d.face_arrays(ob)
    H = float(c[:, 2].max() - c[:, 2].min())
    z0 = float(c[:, 2].min())
    ar = []
    for s in (1, -1):
        k = (n[:, 0] * s > 0.3) & (n[:, 2] > 0.2) & (c[:, 2] > z0 + 0.55 * H)
        ar.append(float(a[k].sum()))
    if ar[0] <= ar[1]:
        raise AssertionError("%s: nose reversed (sloped screen area +X %.4f <= -X %.4f): flip SPEC nose" % (key, ar[0], ar[1]))
    return ar


def class_vote(ob, cls, iters=2):
    """Majority filter on the face classes: a face whose neighbours agree on another class (2 of 3) takes it.
    Cleans the sawtooth rims between lamps, glass, trim and paint along the triangle edges."""
    nb = face_neighbours(ob)
    ok = nb >= 0
    for _ in range(iters):
        q = np.where(ok, cls[np.maximum(nb, 0)], -1)
        a, b, d = q[:, 0], q[:, 1], q[:, 2]
        maj = np.where((a == b) & (a >= 0), a, np.where((a == d) & (a >= 0), a, np.where((b == d) & (b >= 0), b, -1)))
        cls = np.where((maj >= 0) & (maj != cls), maj, cls).astype(np.int32)
    return cls


def smooth_paint(ob, slots, pairs=12, lam=0.5, mu=-0.53):
    """Taubin smoothing (no shrink) of the vertices that only touch paint faces: takes the lumps and dents of the
    generated panels out; panel edges, trim, lamps, glass rims and open borders stay pinned."""
    me = ob.data
    nv, nf = len(me.vertices), len(me.polygons)
    co = gen3d.verts(ob)
    mi = np.empty(nf, np.int32)
    me.polygons.foreach_get("material_index", mi)
    lt = np.empty(nf, np.int64)
    me.polygons.foreach_get("loop_total", lt)
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    fpaint = np.repeat(np.isin(mi, slots), lt)
    pin = np.zeros(nv, bool)
    pin[lv[~fpaint]] = True
    ev = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ev)
    ev = ev.reshape(-1, 2)
    # open borders: edges used by one face
    ek = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("edge_index", ek)
    use = np.bincount(ek, minlength=len(ev))
    pin[ev[use < 2].ravel()] = True
    free = ~pin
    deg = np.bincount(ev.ravel(), minlength=nv).astype(np.float64)
    for _ in range(pairs):
        for f in (lam, mu):
            s = np.zeros_like(co)
            np.add.at(s, ev[:, 0], co[ev[:, 1]])
            np.add.at(s, ev[:, 1], co[ev[:, 0]])
            d = s / np.maximum(deg, 1)[:, None] - co
            co[free] += f * d[free]
    gen3d.set_verts(ob, co)
    return int(free.sum())


def cowl_plank(c, n, cls, spec):
    """The generated wiper / cowl plank: dark faces lying on the windscreen base between the A pillars."""
    hw = spec["size"][1] / 2
    cw, belt = spec["cowl"], spec["belt"]
    return ((c[:, 0] > cw - 0.20) & (c[:, 0] < cw + 0.12) & (c[:, 2] > belt - 0.14) & (c[:, 2] < belt + 0.10)
            & (np.abs(c[:, 1]) < hw - 0.10) & (cls == CLS["trim"]) & (n[:, 2] > -0.2))


def cowl_panel(c, k, spec, name):
    """Modelled cowl: a black plastic panel with louvre ribs over the area of the deleted generated plank, fitted
    to the plank faces (x extent, slope of z over x)."""
    x, z = c[k, 0], c[k, 2]
    x0, x1 = np.percentile(x, [4, 96])
    A = np.stack([np.ones_like(x), x - x.mean()], 1)
    za, zb = np.linalg.lstsq(A, z, rcond=None)[0]
    zb = float(np.clip(zb, -1.2, 0.6))
    hw = float(np.percentile(np.abs(c[k, 1]), 97)) + 0.03
    xm = float((x0 + x1) / 2)
    zm = float(za + zb * (xm - x.mean()))
    ln = float(x1 - x0) + 0.04
    parts = [geo.box((ln, 2 * hw, 0.014), bevel=0.003, base=False, name=name + "_Cowl")]
    ny = int(2 * (hw - 0.06) / 0.032)
    for i in range(ny):
        r = geo.box((ln * 0.62, 0.007, 0.008), bevel=0.0, base=False, name=name + "_Louvre")
        geo.transform(r, loc=(0, -hw + 0.06 + 0.032 * (i + 0.5), 0.010))
        parts.append(r)
    ob = geo.join(parts, name + "_Cowl")
    geo.transform(ob, rot=(0, -math.degrees(math.atan(zb)), 0))
    geo.transform(ob, loc=(xm, 0, zm + 0.004))
    return ob


def wipers(glass, spec, name):
    """Two parked wipers lying on the windscreen base: pivot caps, arms and blades (spine and rubber), fitted to the
    glass by ray casts from above."""
    from mathutils.bvhtree import BVHTree
    if glass is None:
        return []
    bm_t = bmesh.new()
    bm_t.from_mesh(glass.data)
    bvh = BVHTree.FromBMesh(bm_t)
    bm_t.free()

    def hit(x, y):
        h = bvh.ray_cast(Vector((x, y, 8.0)), Vector((0, 0, -1)), 16.0)
        return None if h[0] is None else Vector(h[0])
    cw = spec["cowl"]
    hw = spec["size"][1] / 2 - spec.get("ws_inset", 0.17)
    lb = min(0.60, 0.68 * hw)
    m_int, t_int = tiling("TS_Plastic_CarInterior")
    m_rub, t_rub = tiling("TS_Rubber_Tyre")
    out = []
    for yp in (0.62 * hw, -0.06):
        yc = yp - 0.85 * lb
        base = None
        for x in np.arange(cw + 0.10, cw - 0.60, -0.01):
            base = hit(float(x), yc)
            if base is not None:
                break
        if base is None:
            continue
        xb = base.x - 0.05
        ends = [hit(xb, yc + lb / 2), hit(xb, yc), hit(xb, yc - lb / 2)]
        if any(e is None for e in ends):
            continue
        up = Vector((0, 0, 1))
        spine = [e + up * 0.016 for e in ends]
        rub = [e + up * 0.005 for e in ends]
        piv = Vector((base.x + 0.035, yp, base.z + 0.005))
        tip = ends[1] + up * 0.026
        arm = geo.pipe([tuple(piv), tuple(piv + up * 0.03), tuple(tip)], 0.0065, segments=8, name=name + "_WiperArm")
        cap = geo.cylinder(0.019, 0.03, 16, bevel=0.004, name=name + "_WiperCap")
        geo.transform(cap, loc=tuple(piv - up * 0.01))
        sp_ = geo.pipe([tuple(p) for p in spine], 0.0055, segments=8, name=name + "_WiperBlade")
        rb = geo.pipe([tuple(p) for p in rub], 0.0035, segments=6, name=name + "_WiperRubber")
        out += [put_mat(arm, m_int, t_int), put_mat(cap, m_int, t_int), put_mat(sp_, m_int, t_int),
                put_mat(rb, m_rub, t_rub)]
    return out


def slot_records(ob, extra=None):
    """Manifest records of the M_Vehicle_* slots of ob that read another set (texture paths, shading notes,
    paint_default): what declare() writes, for the assets that call ctx.asset themselves."""
    slots = {}
    for sl in ob.material_slots:
        m = sl.material
        sname = m.get("mi_set") if m is not None else None
        if not sname or not m.name.startswith("M_Vehicle_") or sname == m.name[2:]:
            continue
        se = export.set_entry(sname)
        rec = {"set": sname, "textures": se["textures"] if se else None}
        if m.name.endswith("_Paint") or m.name.endswith("_PaintCab"):
            rec["shading"] = "clear-coat car paint; BC is a tint mask: multiply by the paint colour"
            mx = m.node_tree.nodes.get("Mix")
            rec["paint_default"] = [round(float(v), 4) for v in list(mx.inputs["B"].default_value)[:3]] if mx else None
        elif m.name.endswith("_Primer"):
            rec["shading"] = "matte primer: tint #7a3b2c, roughness 0.78, no clear coat"
            rec["tint"] = [round(float(v), 4) for v in hexcol("#7a3b2c")]
            rec["roughness"] = 0.78
        elif m.name.endswith("_Lamp") or m.name.endswith("_Hazard"):
            rec["shading"] = "lamp lenses; E is the lit colour: scale by a lamp parameter (off by day)"
        slots[m.name] = rec
    for k, v in (extra or {}).items():
        slots.setdefault(k, {}).update(v)
    return slots


def make_parts(ctx, key):
    """The generated body of SPEC[key] cleaned and completed, as separate parts (not joined):
    P = dict(raw=shell before solidify (slots as slot_mats), shell, glass, wheels, wells, interior, seats, plates
    (list of (centre, facing)), yo=tyre outer |y|)."""
    spec = SPEC[key]
    name = "SM_Vehicle_" + key
    set_name = spec.get("set", "Vehicle_" + key)
    ob, tex, cls, c, n, yo = gen_body(ctx, key, spec, name)
    if spec.get("paint2"):
        k = (cls == CLS["paint"]) & spec["paint2"](c)
        cls[k] = 8
    if os.environ.get("VEH_DEBUG"):
        debug_classes(ob, cls, os.path.join(GEN, "debug_%s.jpg" % key))
    plates = []
    for front in (True, False):
        pc = find_plate(c, n, cls, front)
        if pc is not None and not (not front and spec.get("no_rear_plate")):
            plates.append((pc, 1 if front else -1))
            # the generated plate under the modelled one: dark backing (interior plastic)
            # (review fix) the generated plate is larger and lower than the modelled card: the whole holder area
            under = ((np.abs(c[:, 0] - pc[0]) < 0.12) & (np.abs(c[:, 1] - pc[1]) < pc[3] / 2 + 0.05)
                     & (c[:, 2] > pc[2] - pc[4] / 2 - 0.10) & (c[:, 2] < pc[2] + pc[4] / 2 + 0.04)
                     & (cls == CLS["paint"]) & (n[:, 0] * (1 if front else -1) > 0.5))
            cls[under] = CLS["inside"]
    cowl_ob = None
    if spec.get("wipers"):
        ck = cowl_plank(c, n, cls, spec)
        ctx.log("%s: cowl plank %d faces" % (key, int(ck.sum())))
        if ck.sum() >= 30:
            cowl_ob = cowl_panel(c, ck, spec, name)
            cls[ck] = CLS["drop"]
    js = os.path.join(paths.texture_set(set_name), "set.json")
    if not spec.get("set") and (ctx.args.force or not os.path.exists(js) or ctx.args.bake):
        cm = cls.copy()
        cm[cm == 8] = CLS["paint"]
        cm[cm == CLS["inside"]] = CLS["trim"]
        cmap = raster_classes(ob, cm, tex["size"])
        body_set(set_name, cmap, tex, {"asset": name, "family": "vehicles",
                                       "source": "art/out/gen/vehicles/" + spec["src"]})
        ctx.log("%s: set %s written" % (key, set_name))
    del tex
    gmask = cls == CLS["glass"]
    glass = gen3d.split_faces(ob, gmask, name + "_Glass") if gmask.any() else None
    cls = cls[~gmask]
    kill = np.isin(cls, [CLS["wheel"], CLS["drop"]])
    gen3d.delete_faces(ob, kill)
    cls = cls[~kill]
    ms = slot_mats(key, spec)
    ob.data.materials.clear()
    for m in ms:
        ob.data.materials.append(m)
    hz = 3 if spec.get("hazard_slot") else 2
    p2 = len(ms) - 2 if spec.get("paint2") else 0
    idx = np.select([cls == CLS["paint"], cls == CLS["trim"], cls == CLS["amber"], cls == 8, cls == CLS["inside"]],
                    [0, 1, hz, p2, len(ms) - 1], 2)
    gen3d.set_face_materials(ob, idx)
    tri0 = geo.stats(ob)["triangles"]
    gen3d.decimate(ob, 1.0, target=spec["tris"])
    if spec.get("smooth", 12):
        nfree = smooth_paint(ob, [0] + ([p2] if p2 else []), pairs=spec.get("smooth", 12))
        ctx.log("%s: paint panels smoothed (%d free vertices)" % (key, nfree))
    W, D, H = spec["size"]
    gen3d.clamp_box(ob, (-W / 2, -D / 2, 0.0), (W / 2, D / 2, H))
    geo.smooth_by_angle(ob, 50)
    raw = dup(ob, name + "_Raw")
    raw.hide_render = True
    raw.hide_viewport = True
    if spec.get("solid", True):
        solidify(ob, 0.010, len(ms) - 1)
    ctx.log("%s: shell %d -> %d tris" % (key, tri0, geo.stats(ob)["triangles"]))
    P = dict(raw=raw, shell=ob, glass=None, wheels=[], wells=[], interior=[], seats=[], extra=[], plates=plates,
             yo=yo, spec=spec, name=name)
    if glass is not None:
        m_glass, t_glass = tiling("TS_Glass_CarTint")
        gen3d.decimate(glass, 1.0, target=spec.get("glass_tris", 6000))
        put_mat(glass, m_glass, t_glass)
        solidify(glass, 0.005, 0)
        geo.smooth_by_angle(glass, 50)
        P["glass"] = glass
    if spec.get("wheel"):
        P["wheels"], P["wells"] = make_wheels(spec, name, yo, spec["wheel"])
    if spec.get("interior", True):
        hw_in = spec["size"][1] / 2 - 0.20
        ip = interior(spec, name, hw_in)
        m_int, t_int = tiling("TS_Plastic_CarInterior")
        m_seat, t_seat = tiling("TS_Fabric_CarSeat")
        P["interior"] = [put_mat(p, m_int, t_int) for p in ip["interior"]]
        P["seats"] = [put_mat(p, m_seat, t_seat) for p in ip["seat"]]
    if spec.get("wipers"):
        m_int, t_int = tiling("TS_Plastic_CarInterior")
        if cowl_ob is not None:
            P["extra"].append(put_mat(cowl_ob, m_int, t_int))
        P["extra"] += wipers(P["glass"], spec, name)
    return P


WHEEL_MATS = {"tyre": "TS_Rubber_Tyre", "chrome": "TS_Chrome_Polished", "steel": "TS_Paint_WheelSteel",
              "alloy": "TS_Alloy_Wheel"}


def make_wheels(spec, name, yo, style, axles=None, hub_z=None, tyres=True, mats=None):
    """Four (or six with twin rears) modelled wheels on the briefed axles plus their well liners."""
    sp = dict(spec)
    sp["wheel"] = style
    out, wells = [], []
    yc = yo - spec["tw"] / 2
    m_int, t_int = tiling("TS_Plastic_CarInterior")
    hz = spec["r"] if hub_z is None else hub_z
    for i, ax in enumerate(axles or spec["axles"]):
        twin = spec.get("twin", False) and i == 1
        for side in (1, -1):
            wp = wheel(sp, "%s_W%d%d" % (name, i, side), twin=twin)
            for k, obs in wp.items():
                if k == "tyre" and not tyres:
                    keep = []
                    for o in obs:
                        if "_Tyre" in o.name:
                            bpy.data.objects.remove(o, do_unlink=True)
                        else:
                            keep.append(o)
                    obs = keep
                m, t = (mats or {}).get(k) or tiling(WHEEL_MATS[k])
                for p in obs:
                    if side < 0:
                        geo.transform(p, rot=(0, 0, 180))
                    geo.transform(p, loc=(ax, side * yc, hz))
                    out.append(put_mat(p, m, t))
            if tyres:
                wl = well_liner(spec["r"], 0.42 if not twin else 0.70, name + "_Well")
                if side < 0:
                    geo.transform(wl, rot=(0, 0, 180))
                geo.transform(wl, loc=(ax, side * (yo + 0.02), hz))
                wells.append(put_mat(wl, m_int, t_int))
    return out, wells


def make_plates(P, code, y=None):
    return [plate(code, (pc[0] + f * 0.004, pc[1] if y is None else y, pc[2]), f, size=(pc[3], pc[4]),
                  name=P["name"] + "_Plate") for pc, f in P["plates"]]


def assemble(ctx, name, objs, dirt=0.35):
    objs = [o for o in objs if o is not None]
    for o in objs:
        o.hide_render = False
        o.hide_viewport = False
    ob = geo.join(objs, name, ctx.col)
    finish(ob, dirt)
    return ob


def debug_classes(ob, cls, path):
    """Flat-colour render of the face classes (VEH_DEBUG=1)."""
    cols = [(0.8, 0.8, 0.8), (0.05, 0.05, 0.05), (0.2, 0.9, 0.2), (0.9, 0.05, 0.05), (1, 0.4, 0), (0.1, 0.3, 0.9),
            (0.9, 0.0, 0.9), (0.0, 0.9, 0.9), (0.9, 0.8, 0.5), (0.5, 0.2, 0.0)]
    cp = dup(ob, "Debug")
    cp.data.materials.clear()
    for i, cc in enumerate(cols):
        m = bpy.data.materials.new("dbg%d" % i)
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*cc, 1)
        cp.data.materials.append(m)
    gen3d.set_face_materials(cp, cls)
    for o in bpy.context.scene.objects:
        o.hide_render = o is not cp
    sc = bpy.context.scene
    render.setup(samples=8, res=(900, 500))
    w = bpy.data.worlds.new("dbgw")
    sc.world = w
    w.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    from PIL import Image
    tiles = []
    L = max(scene.bounds(cp)[1][0], 1.0)
    for i, (pp, t) in enumerate([((2.4 * L, -2.0 * L, 1.0 * L), (0, 0, 0.5)), ((-2.4 * L, 2.0 * L, 1.0 * L), (0, 0, 0.5)),
                                 ((0.3, -3.2 * L, 0.6), (0, 0, 0.6)), ((-3.2 * L, 0, 1.2), (0, 0, 0.8))]):
        render.cam_look(pp, t, lens=40)
        f = path + "_%d.png" % i
        render.render_png(f, 8, (900, 500))
        tiles.append(Image.open(f).convert("RGB"))
    sh = Image.new("RGB", (1800, 1000))
    for i, t in enumerate(tiles):
        sh.paste(t, ((i % 2) * 900, (i // 2) * 500))
    sh.save(path, quality=85)
    bpy.data.objects.remove(cp, do_unlink=True)
    for o in bpy.context.scene.objects:
        o.hide_render = False


# ------------------------------------------------------------------------------------------------------- decals
def decal_set(name, img, note=""):
    """Write an RGBA decal set (T_<Set>_BC.png with alpha, ORM, flat N). img: PIL RGBA image."""
    from PIL import Image
    d = paths.texture_set(name)
    os.makedirs(d, exist_ok=True)
    img.save(os.path.join(d, "T_%s_BC.png" % name))
    W, H = img.size
    a = np.asarray(img, dtype=np.float32) / 255.0
    orm = np.stack([np.ones((H, W)), np.full((H, W), 0.45), np.zeros((H, W))], -1)
    Image.fromarray((orm * 255).astype(np.uint8)).save(os.path.join(d, "T_%s_ORM.png" % name))
    Image.fromarray(np.full((H, W, 3), (128, 128, 255), np.uint8)).save(os.path.join(d, "T_%s_N.png" % name))
    lin = bake.srgb_decode(a[..., :3])
    al = a[..., 3]
    info = {"set": name, "kind": "decal", "alpha": "masked (BC alpha)", "resolution": [W, H], "family": "vehicles",
            "files": {"BC": "T_%s_BC.png" % name, "ORM": "T_%s_ORM.png" % name, "N": "T_%s_N.png" % name},
            "albedo_mean": [round(float(v), 4) for v in (lin * al[..., None]).reshape(-1, 3).sum(0) / max(al.sum(), 1)],
            "roughness_mean": 0.45, "metallic_mean": 0.0, "note": note}
    with open(os.path.join(d, "set.json"), "w") as f:
        json.dump(info, f, indent=1)
    return name


def decal(target, name, x0, x1, z0, z1, side, uv, m, nx=40, nz=12, lift=0.0025):
    """Card shrink-wrapped onto target's flank: the rectangle x0..x1, z0..z1 projected along -side*Y onto the
    surface, lifted 2.5 mm along the hit normal. uv = (u0, v0, u1, v1) region of the decal atlas; the art reads
    left to right from outside on either flank. Faces whose rays miss are dropped."""
    from mathutils.bvhtree import BVHTree
    bm_t = bmesh.new()
    bm_t.from_mesh(target.data)
    bm_t.transform(target.matrix_world)
    bvh = BVHTree.FromBMesh(bm_t)
    bm_t.free()
    u0, v0, u1, v1 = uv
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new(geo.UV)
    grid = {}
    ok = {}
    for i in range(nx + 1):
        for j in range(nz + 1):
            x = x0 + (x1 - x0) * i / nx
            z = z0 + (z1 - z0) * j / nz
            hit = bvh.ray_cast(Vector((x, side * 3.0, z)), Vector((0, -side, 0)), 6.0)
            if hit[0] is None:
                ok[i, j] = False
                grid[i, j] = bm.verts.new((x, side * 0.5, z))
                continue
            ok[i, j] = True
            nrm = hit[1] if hit[1].y * side > 0 else -hit[1]
            grid[i, j] = bm.verts.new(hit[0] + nrm * lift)
    for i in range(nx):
        for j in range(nz):
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            if not all(ok[k] for k in q):
                continue
            vs = [grid[k] for k in q]
            if side < 0:
                vs = vs[::-1]
                q = q[::-1]
            f = bm.faces.new(vs)
            for lp, (a, b) in zip(f.loops, q):
                s_ = a / nx
                u = u0 + (u1 - u0) * (s_ if side < 0 else 1.0 - s_)
                lp[uvl].uv = (u, v0 + (v1 - v0) * b / nz)
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    ob = geo.new(name, bm, uv=False, smooth=60)
    ob.data.materials.append(m)
    return ob


def _font(name, size):
    from PIL import ImageFont
    return ImageFont.truetype(FONT + name, size)


def taxi_decals():
    """Atlas 2048 x 1024: door panel (0..1 x 0..0.5 of the left half), checker band, medallion."""
    from PIL import Image, ImageDraw
    W, H = 2048, 1024
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ink = (12, 12, 13, 255)
    # door panel 0.92 x 0.37 -> region (0, 0)-(1024, 412)
    d.text((512, 120), "NYC TAXI", font=_font("InterDisplay-Black.otf", 150), fill=ink, anchor="mm")
    d.text((300, 300), "5K83", font=_font("InterDisplay-Black.otf", 110), fill=ink, anchor="mm")
    x0 = 600
    d.rectangle((x0, 235, x0 + 380, 395), outline=ink, width=6)
    for k, t in enumerate(["RATE OF FARE", "$2.00 UPON ENTRY", "30c EACH 1/5 MILE", "NIGHT 50c"]):
        d.text((x0 + 14, 246 + k * 36), t, font=_font("Inter-Bold.otf", 26), fill=ink)
    # checker band 2.40 x 0.07: two rows of 16 -> region (0, 512)-(2048, 572)
    cw = W / 16
    for row in range(2):
        for k in range(16):
            c = (240, 240, 236, 255) if (k + row) % 2 else ink
            d.rectangle((int(k * cw), 512 + row * 30, int((k + 1) * cw) - 1, 512 + row * 30 + 29), fill=c)
    # medallion for the roof light faces: region (1024, 0)-(2048, 200) on a lit yellow ground
    d.rectangle((1024, 0, 2047, 200), fill=(255, 214, 90, 255))
    d.text((1536, 100), "5K83", font=_font("InterDisplay-Black.otf", 150), fill=ink, anchor="mm")
    return decal_set("Vehicle_Taxi_Decals", im, "taxi lettering (invented: no real fleet or medallion), checker band, "
                     "roof-light medallion (the roof light region is lit: E = BC there)")


def spray(d, text, box, font, colour, rng, drips=True):
    """Spray-painted letters: an overspray halo, the letters, drips."""
    from PIL import Image, ImageDraw, ImageFilter
    x0, y0, x1, y1 = box
    W, H = x1 - x0, y1 - y0
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    size = int(H * 0.8)
    f = _font(font, size)
    while ld.textlength(text, font=f) > W * 0.92 and size > 20:
        size -= 8
        f = _font(font, size)
    ld.text((W / 2, H / 2), text, font=f, fill=colour, anchor="mm")
    halo = lay.filter(ImageFilter.GaussianBlur(size * 0.04))
    a = np.asarray(halo).copy()
    a[..., 3] = (a[..., 3] * 0.45).astype(np.uint8)
    base = Image.alpha_composite(Image.fromarray(a), lay)
    if drips:
        bd = ImageDraw.Draw(base)
        al = np.asarray(lay)[..., 3]
        cols = np.nonzero(al.max(0) > 128)[0]
        for _ in range(max(4, len(cols) // 60)):
            cx = int(rng.choice(cols))
            ys = np.nonzero(al[:, cx] > 128)[0]
            yb = int(ys.max())
            L = int(rng.uniform(0.05, 0.25) * H)
            bd.line((cx, yb, cx, min(H - 1, yb + L)), fill=colour, width=max(2, size // 40))
    # wear: knock holes out of the paint
    n = _noise((H, W), 12.0, int(rng.integers(1000)))
    b = np.asarray(base).copy()
    b[..., 3] = (b[..., 3] * np.clip((n - 0.18) * 3.0, 0, 1)).astype(np.uint8)
    d._image.paste(Image.fromarray(b), (x0, y0), Image.fromarray(b))


def vulture_decals():
    """Atlas 2048 x 2048: vulture stencil (left half top), stripe, two scrawls."""
    from PIL import Image, ImageDraw, ImageFilter
    W = 2048
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    bone = (233, 228, 214, 255)
    # stencil 1.15 x 0.92 -> (0,0)-(1280,1024): hunched vulture on a wire, cut-stencil style with bridges
    st = Image.new("L", (1280, 1024), 0)
    sd = ImageDraw.Draw(st)
    sd.line((40, 900, 1240, 860), fill=255, width=18)                         # the wire
    sd.polygon([(420, 880), (520, 560), (640, 420), (820, 380), (930, 430), (980, 560), (930, 760), (800, 880)], fill=255)
    sd.polygon([(520, 560), (300, 520), (200, 600), (330, 640), (470, 700)], fill=255)        # folded wing tip
    sd.ellipse((800, 230, 930, 360), fill=255)                                 # head
    sd.polygon([(880, 230), (980, 120), (1000, 200), (930, 300)], fill=255)   # neck ruff
    sd.polygon([(920, 280), (1060, 300), (1000, 340), (930, 330)], fill=255)  # hooked beak
    sd.polygon([(640, 880), (660, 960), (700, 960), (690, 880)], fill=255)    # talons over the wire
    sd.polygon([(760, 880), (780, 960), (820, 960), (800, 880)], fill=255)
    for y in (480, 600, 720):                                                   # stencil bridges
        sd.line((560, y, 960, y - 40), fill=0, width=14)
    sd.ellipse((850, 260, 880, 290), fill=0)                                   # eye
    st = st.filter(ImageFilter.GaussianBlur(3))
    n = _noise((1024, 1280), 10.0, 7)
    a = np.asarray(st, dtype=np.float32) / 255.0 * np.clip((n - 0.12) * 2.5, 0, 1)
    lay = np.zeros((1024, 1280, 4), np.uint8)
    lay[..., :3] = bone[:3]
    lay[..., 3] = (np.clip(a, 0, 1) * 235).astype(np.uint8)
    im.paste(Image.fromarray(lay), (0, 0))
    d = ImageDraw.Draw(im)
    # oxblood stripe 3.70 x 0.09 -> (0, 1100)-(2048, 1160)
    d.rectangle((0, 1100, W - 1, 1160), fill=(90, 15, 20, 255))
    # scrawls 0.66 x 0.29 -> (0, 1300)-(900, 1700) oxblood, (1000, 1300)-(1900, 1700) bone white
    rng = np.random.default_rng(4418)
    for ox, col in ((0, (138, 24, 32, 255)), (1000, bone)):
        pts = []
        x = ox + 40
        while x < ox + 860:
            pts.append((x, 1500 + rng.normal(0, 90)))
            x += rng.uniform(25, 70)
        d.line(pts, fill=col, width=16, joint="curve")
        for _ in range(3):
            cx, cy = ox + rng.uniform(100, 800), 1500 + rng.uniform(-120, 120)
            d.arc((cx - 80, cy - 60, cx + 80, cy + 60), rng.uniform(0, 180), rng.uniform(200, 360), fill=col, width=12)
    return decal_set("Vehicle_VanVulture_Decals", im, "crew livery: vulture stencil (sprayed, worn), oxblood stripe, "
                     "two letterless marker scrawls")


def boxtruck_decals():
    from PIL import Image, ImageDraw
    W = 2048
    im = Image.new("RGBA", (W, 2048), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(7)
    spray(d, "RULE", (0, 0, 2048, 945), "InterDisplay-BlackItalic.otf", (233, 228, 214, 255), rng)
    spray(d, "HOLLIS", (0, 1024, 2048, 1969), "InterDisplay-BlackItalic.otf", (246, 194, 26, 255), rng)
    return decal_set("Vehicle_BoxTruck_Decals", im, "spray tags RULE (bone) and HOLLIS (gold), 2.6 x 1.2 each")


def ipx_decals():
    """Atlas 2048 x 2048: (0,0)-(2048,512) flank art panel 3.50 x 0.875; (0,600)-(2048,664) gold band;
    (0,800)-(1024,1222) lozenge alone; (1024,800)-(2048,928) wordmark alone."""
    from PIL import Image, ImageDraw
    W = 2048
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    white = (244, 242, 236, 255)
    gold = (231, 181, 58, 255)
    ink = (23, 25, 29, 255)

    def lozenge(cx, cy, w, h, fill, text_col):
        d.polygon([(cx - w / 2, cy), (cx - w / 2 + h / 2, cy - h / 2), (cx + w / 2 - h / 2, cy - h / 2),
                   (cx + w / 2, cy), (cx + w / 2 - h / 2, cy + h / 2), (cx - w / 2 + h / 2, cy + h / 2)], fill=fill)
        f = _font("Inter-ExtraBoldItalic.otf", int(h * 0.62))
        d.text((cx, cy + h * 0.02), "IPX", font=f, fill=text_col, anchor="mm")
    d.rectangle((0, 0, W - 1, 511), fill=white)
    lozenge(330, 256, 520, 420 * 0.5 * 1.7, ink, white)
    d.rectangle((640, 236, 760, 276), fill=(246, 194, 26, 255))
    d.text((1400, 256), "IPX.EXCHANGE", font=_font("Inter-ExtraBoldItalic.otf", 150), fill=ink, anchor="mm")
    d.rectangle((0, 600, W - 1, 663), fill=gold)
    lozenge(512, 1011, 980, 400, white, ink)
    d.text((1536, 864), "IPX.EXCHANGE", font=_font("Inter-ExtraBoldItalic.otf", 112), fill=white, anchor="mm")
    return decal_set("Vehicle_IPXTruck_Decals", im, "IPX livery: flank art panel, gold waist band, bonnet and door "
                     "lozenge, door wordmark. The lozenge is a typeset stand-in for the real logo: swap this texture")


def decal_mat(set_name):
    return set_material(set_name, slot="M_" + set_name, alpha=True)


# ------------------------------------------------------------------------------------------------- the vehicles
def v_simple(ctx, key, notes, keep=False):
    P = make_parts(ctx, key)
    sp = P["spec"]
    if keep:                                   # copies for the variants (taxi, wrecks): the parts are joined below
        K = dict(P)
        for k in ("shell", "glass"):
            K[k] = dup(P[k], P[k].name + "_Keep")
        for k in ("interior", "seats", "extra"):
            K[k] = [dup(o, o.name + "_Keep") for o in P[k]]
        for o in [K["shell"], K["glass"]] + K["interior"] + K["seats"] + K["extra"]:
            o.hide_render = True
        P_keep = K
    parts = [P["shell"], P["glass"]] + P["wheels"] + P["wells"] + P["interior"] + P["seats"]
    parts += make_plates(P, sp["plate"]) + P.get("extra", [])
    extra = sp.get("extra")
    if extra:
        parts += extra(ctx, P)
    ob = assemble(ctx, P["name"], parts)
    declare(ctx, ob, key, notes, sp["cover"])
    return ob, (P_keep if keep else P)


def v_taxi(ctx, P):
    """From the sedan parts: yellow paint, steel wheels, roof light, door lettering, checker band, taxi plate."""
    sp = SPEC["Sedan"]
    shell = dup(P["shell"], "Taxi_Shell")
    mp = set_material("Vehicle_Sedan", slot="M_Vehicle_Taxi_Paint", coat=1.0, tint=hexcol("#f2c21a"))
    shell.material_slots[0].material = mp
    glass = dup(P["glass"], "Taxi_Glass")
    parts = [shell, glass] + [dup(o) for o in P["interior"] + P["seats"] + P.get("extra", [])]
    w, wl = make_wheels(sp, "SM_Vehicle_Taxi", P["yo"], "steel")
    parts += w + wl
    parts += [plate("T5K83", (pc[0] + f * 0.004, pc[1], pc[2]), f, size=(pc[3], pc[4]), name="Taxi_Plate")
              for pc, f in P["plates"]]
    dset = taxi_decals()
    dm = decal_mat(dset)
    for side in (1, -1):
        parts.append(decal(shell, "Taxi_Door", 0.39 - 0.46, 0.39 + 0.46, 0.73 - 0.185, 0.73 + 0.185, side,
                           (0.0, 1 - 412 / 1024, 0.5, 1.0), dm, nx=30, nz=10))
        parts.append(decal(shell, "Taxi_Check", -1.47, 0.93, 0.93 - 0.035, 0.93 + 0.035, side,
                           (0.0, 1 - 572 / 1024, 1.0, 1 - 512 / 1024), dm, nx=60, nz=2))
    # roof light: lit box 0.16 x 0.40 x 0.085 on a dark foot, top at 1.55, medallion on front and rear faces
    co = gen3d.verts(P["raw"])
    near = co[(np.abs(co[:, 0] + 0.17) < 0.12) & (np.abs(co[:, 1]) < 0.2)]
    roof = float(near[:, 2].max()) if len(near) else 1.45
    m_int, t_int = tiling("TS_Plastic_CarInterior")
    foot = geo.box((0.22, 0.30, max(0.01, 1.55 - 0.085 - roof + 0.01)), bevel=0.006, name="Taxi_LightFoot")
    geo.transform(foot, loc=(-0.17, 0, roof - 0.01))
    parts.append(put_mat(foot, m_int, t_int))
    box = geo.box((0.16, 0.40, 0.085), bevel=0.01, name="Taxi_Light")
    geo.transform(box, loc=(-0.17, 0, 1.55 - 0.085))
    me = box.data
    uvl = me.uv_layers.get(geo.UV) or me.uv_layers.new(name=geo.UV)
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            fx = 1 if p.normal.x >= 0 else -1
            u = 0.5 + 0.5 * (0.5 + fx * v.y / 0.40)
            uvl.data[li].uv = (min(max(u, 0.5), 1.0), 1 - 200 / 1024 + (v.z - (1.55 - 0.085)) / 0.085 * (200 / 1024))
    lm = set_material(dset, slot="M_Vehicle_Taxi_RoofLight", emit_strength=0.0)
    box.data.materials.append(lm)
    parts.append(box)
    ob = assemble(ctx, "SM_Vehicle_Taxi", parts)
    declare(ctx, ob, "Taxi", "Yellow cab from the sedan body (same set Vehicle_Sedan, paint tinted #f2c21a), dark steel "
            "wheels, roof light (slot M_Vehicle_Taxi_RoofLight: lit, emissive = BC), door lettering and checker band "
            "on M_Vehicle_Taxi_Decals (alpha mask), plate T·5K83. Cover 1.08 / 1.45.", 1.08,
            expect=(4.61, 1.85, 1.55))
    return ob


def _shell_variant(P, name, keep_bonnet=True):
    """Unsolidified sedan shell copy for the wrecks, with lamps and bumpers removed."""
    sh = dup(P["raw"], name)
    sh.hide_render = False
    sh.hide_viewport = False
    c, n, a = gen3d.face_arrays(sh)
    mi = np.empty(len(sh.data.polygons), dtype=np.int32)
    sh.data.polygons.foreach_get("material_index", mi)
    kill = (mi == 2) | ((mi == 1) & (c[:, 2] < 0.68) & (np.abs(c[:, 0]) > 1.80))
    kill |= (mi == 1) & (np.abs(c[:, 1]) > 0.86)                 # rub strips and mirror heads
    # (review fix) bumpers in any colour, the plate holders and the dark lamp lenses: the brief has none
    kill |= (np.abs(c[:, 0]) > 2.04) & (c[:, 2] < 0.64)
    kill |= (mi >= 1) & (np.abs(c[:, 0]) > 1.92) & (c[:, 2] < 1.0) & (np.abs(c[:, 1]) > 0.35)
    gen3d.delete_faces(sh, kill)
    return sh


def _bonnet(sh, cowl=0.98):
    c, n, a = gen3d.face_arrays(sh)
    k = (c[:, 0] > cowl + 0.02) & (c[:, 2] > 0.80) & (n[:, 2] > 0.30) & (np.abs(c[:, 1]) < 0.78)
    return k


def bay(name, x0, x1, hw, z0, z1, m, t):
    """Open-top box seen from inside (engine bay, load space)."""
    ob = geo.box((x1 - x0, 2 * hw, z1 - z0), bevel=0.0, name=name)
    geo.transform(ob, loc=((x0 + x1) / 2, 0, z0))
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    top = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.delete(bm, geom=top, context="FACES")
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    return put_mat(ob, m, t)


def v_burned(ctx, P):
    sp = SPEC["Sedan"]
    sh = _shell_variant(P, "Burned_Shell")
    k = _bonnet(sh)
    bon = gen3d.split_faces(sh, k, "Burned_Bonnet")
    rust = set_material("TS_Steel_ScanRustHeavy", slot="MI_Steel_ScanRustHeavy")
    t_rust = mat.scan_tile("TS_Steel_ScanRustHeavy")
    char, t_char = tiling("TS_Char_Burnt")
    for o in (sh, bon):
        o.data.materials.clear()
        o.data.materials.append(rust)
        o.data.materials.append(char)
        gen3d.set_face_materials(o, np.zeros(len(o.data.polygons), np.int32))
        solidify(o, 0.008, 1)
        geo.uv_world_box(o, t_rust)
    # bonnet sprung 15 degrees on its hinge at the cowl
    hb = gen3d.verts(bon)
    hx, hz = float(hb[:, 0].min()), float(hb[hb[:, 0] < hb[:, 0].min() + 0.1, 2].mean())
    geo.transform(bon, loc=(-hx, 0, -hz))
    geo.transform(bon, rot=(0, -15, 0))
    geo.transform(bon, loc=(hx, 0, hz))
    parts = [sh, bon]
    parts.append(bay("Burned_Bay", 1.0, 1.95, 0.60, 0.32, 0.78, char, t_char))
    eng = geo.box((0.55, 0.60, 0.38), bevel=0.04, name="Burned_Engine")
    geo.transform(eng, loc=(1.55, 0, 0.32))
    parts.append(put_mat(eng, char, t_char))
    # seat frames, bench frame, steering wheel: charred tubes
    for y in (0.36, -0.36):
        parts.append(put_mat(geo.pipe([(-0.05, y - 0.22, 0.55), (-0.55, y - 0.22, 0.55), (-0.62, y - 0.22, 1.10),
                                       (-0.62, y + 0.22, 1.10), (-0.55, y + 0.22, 0.55), (-0.05, y + 0.22, 0.55),
                                       (-0.05, y - 0.22, 0.55)], 0.012, name="Burned_Frame"), char, t_char))
    parts.append(put_mat(geo.pipe([(-0.90, -0.62, 0.52), (-1.40, -0.62, 0.52), (-1.45, -0.62, 1.0), (-1.45, 0.62, 1.0),
                                   (-1.40, 0.62, 0.52), (-0.90, 0.62, 0.52), (-0.90, -0.62, 0.52)], 0.012,
                                  name="Burned_Bench"), char, t_char))
    swr = geo.torus(0.185, 0.014, 32, 8, name="Burned_Wheel")
    geo.transform(swr, rot=(0, -62, 0))
    geo.transform(swr, loc=(0.36, 0.37, 0.96))
    parts.append(put_mat(swr, char, t_char))
    fl = geo.box((2.6, 1.40, 0.02), bevel=0.0, name="Burned_Floor")
    geo.transform(fl, loc=(-0.3, 0, 0.33))
    parts.append(put_mat(fl, char, t_char))
    # bare rusted rims on the ground
    w, _ = make_wheels(sp, "Burned", P["yo"], "steel", tyres=False, mats={"steel": (rust, t_rust),
                                                                            "chrome": (rust, t_rust),
                                                                            "tyre": (char, t_char)})
    for o in w:
        geo.transform(o, loc=(0, 0, -(sp["r"] - sp["rim"] - 0.012)))
    ob = geo.join(parts, "SM_Vehicle_BurnedCar", ctx.col)
    # the shell sits 0.125 lower and is the smaller 4.38 x 1.72 x 1.30 box
    lo, hi = scene.bounds(ob)
    co = gen3d.verts(ob)
    co[:, 0] = (co[:, 0] - (lo[0] + hi[0]) / 2) * 4.38 / (hi[0] - lo[0])
    co[:, 1] = (co[:, 1] - (lo[1] + hi[1]) / 2) * 1.72 / (hi[1] - lo[1])
    co[:, 2] = (co[:, 2] - 0.125) * 1.30 / (hi[2] - 0.125)
    gen3d.set_verts(ob, co)
    wj = geo.join(w, "Burned_Rims")
    co = gen3d.verts(wj)
    co[:, 0] *= 4.38 / 4.61
    co[:, 1] *= 1.72 / (hi[1] - lo[1])
    gen3d.set_verts(wj, co)
    ob = geo.join([ob, wj], "SM_Vehicle_BurnedCar", ctx.col)
    finish(ob, 0.8)
    ctx.asset(ob, collision="box", cover_height=0.96, notes="Burned-out saloon from the sedan shell: rusted "
              "(MI_Steel_ScanRustHeavy), charred inside (MI_Char_Burnt), no glass, lamps, bumpers or tyres, bonnet "
              "sprung 15 degrees over a black bay, seat frames and steering wheel, bare rims. Bullet-only box over the "
              "cabin x -1.30..0.65, y +-0.72, z 0.96..1.30. Anchor 'smolder' at (1.5, 0, 1.0).",
              expect_size=(4.38, 1.72, 1.30))
    return ob


def jack_stand(m, t, name="Stand"):
    parts = []
    for a in range(3):
        ang = math.radians(a * 120 + 30)
        parts.append(geo.pipe([(math.cos(ang) * 0.17, math.sin(ang) * 0.17, 0.0), (0, 0, 0.20)], 0.012, name=name))
    parts.append(geo.cylinder(0.025, 0.30, 12, name=name + "_Post"))
    sad = geo.box((0.10, 0.06, 0.05), bevel=0.005, name=name + "_Saddle")
    geo.transform(sad, loc=(0, 0, 0.30))
    parts.append(sad)
    ob = geo.join(parts)
    return put_mat(ob, m, t)


def v_stripped(ctx, P):
    sp = SPEC["Sedan"]
    sh = _shell_variant(P, "Stripped_Shell")
    c, n, a = gen3d.face_arrays(sh)
    doors = (np.abs(c[:, 1]) > 0.55) & (c[:, 0] > -1.10) & (c[:, 0] < 0.96) & (c[:, 2] > 0.30) & (c[:, 2] < 1.04)
    gen3d.delete_faces(sh, doors | _bonnet(sh))
    primer = set_material("Vehicle_Sedan", slot="M_Vehicle_StrippedCar_Primer", tint=hexcol("#7a3b2c"), rough=0.78)
    bare, t_bare = tiling("TS_Steel_CargoDark")
    mi = np.empty(len(sh.data.polygons), dtype=np.int32)
    sh.data.polygons.foreach_get("material_index", mi)
    sh.data.materials.clear()
    for m in (primer, bare):
        sh.data.materials.append(m)
    gen3d.set_face_materials(sh, np.where(mi == 1, 1, 0))
    solidify(sh, 0.008, 1)
    galv = set_material("TS_Galvanised_Aged", slot="MI_Galvanised_Aged")
    t_galv = (bake.read_set("TS_Galvanised_Aged") or {}).get("tile_m", 1.0)
    parts = [sh, bay("Stripped_Bay", 1.0, 1.95, 0.60, 0.32, 0.80, bare, t_bare)]
    lump = geo.box((0.45, 0.40, 0.30), bevel=0.03, name="Stripped_Lump")
    geo.transform(lump, loc=(1.50, 0.12, 0.34))
    parts.append(put_mat(lump, galv, t_galv))
    fl = geo.box((2.3, 1.30, 0.02), bevel=0.0, name="Stripped_Floor")
    geo.transform(fl, loc=(-0.3, 0, 0.33))
    parts.append(put_mat(fl, bare, t_bare))
    dash = geo.box((0.30, 1.30, 0.22), bevel=0.02, name="Stripped_Dash")
    geo.transform(dash, loc=(0.70, 0, 0.72))
    parts.append(put_mat(dash, bare, t_bare))
    rust = set_material("TS_Steel_ScanRust", slot="MI_Steel_ScanRust")
    t_rust = mat.scan_tile("TS_Steel_ScanRust")
    for ax in sp["axles"]:
        for side in (1, -1):
            disc = geo.cylinder(0.14, 0.022, 32, bevel=0.003, base=False, name="Stripped_Disc")
            hub = geo.cylinder(0.07, 0.08, 20, bevel=0.005, base=False, name="Stripped_Hub")
            geo.transform(hub, loc=(0, 0, 0.04))
            dd = geo.join([disc, hub])
            _rot_to_y(dd)
            if side < 0:
                geo.transform(dd, rot=(0, 0, 180))
            geo.transform(dd, loc=(ax, side * (P["yo"] - 0.16), sp["r"]))
            parts.append(put_mat(dd, rust, t_rust))
    ob = geo.join(parts, "SM_Vehicle_StrippedCar", ctx.col)
    lo, hi = scene.bounds(ob)
    co = gen3d.verts(ob)
    co[:, 0] = (co[:, 0] - (lo[0] + hi[0]) / 2) * 4.38 / (hi[0] - lo[0])
    co[:, 1] = (co[:, 1] - (lo[1] + hi[1]) / 2) * 1.72 / (hi[1] - lo[1])
    co[:, 2] += 1.60 - hi[2]
    gen3d.set_verts(ob, co)
    stands = []
    for x in (1.0, -1.0):
        for y in (0.66, -0.66):
            s = jack_stand(galv, t_galv)
            geo.transform(s, loc=(x, y, 0))
            stands.append(s)
    ob = geo.join([ob] + stands, "SM_Vehicle_StrippedCar", ctx.col)
    finish(ob, 0.6)
    ctx.asset(ob, collision="box", cover_height=1.23, notes="Sedan shell stripped in the chop shop: red-oxide primer "
              "(M_Vehicle_StrippedCar_Primer reads Vehicle_Sedan; tint #7a3b2c, roughness 0.78, no clear coat), "
              "door apertures cut through, no glass, wheels, bumpers or lamps, rusty discs on the hubs, gutted dash, "
              "open bay with one galvanised lump, raised 0.15 on four jack stands. Cabin box x -1.26..0.64, y +-0.74, "
              "z 1.23..1.60.", expect_size=(4.38, 1.72, 1.60), slots=slot_records(ob))
    return ob


def v_vulture(ctx):
    """The van with both rear doors swung open, load space, cargo, crew livery."""
    P = make_parts(ctx, "VanVulture")
    sp = P["spec"]
    parts = [P["shell"], P["glass"]] + P["wheels"] + P["wells"] + P["interior"] + P["seats"] + P["extra"]
    parts += [plate("LWG4418", (pc[0] + f * 0.004, pc[1], pc[2]), f, size=(pc[3], pc[4]), name="Vulture_Plate")
              for pc, f in P["plates"] if f > 0]
    bare, t_bare = tiling("TS_Steel_CargoDark")
    # load space 2.94 x 1.52 x 1.44, floor 0.60, open at the tail
    ls = geo.box((2.94, 1.52, 1.44), bevel=0.0, name="Vulture_Load")
    geo.transform(ls, loc=(-2.53 + 1.47 + 0.02, 0, 0.60))
    bm = bmesh.new()
    bm.from_mesh(ls.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.x < -0.9], context="FACES")
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(ls.data)
    bm.free()
    parts.append(put_mat(ls, bare, t_bare))
    # door frame around the opening
    fr = []
    for (sx, sy, sz, x, y, z) in ((0.06, 1.78, 0.08, -2.55, 0, 2.06), (0.06, 1.78, 0.06, -2.55, 0, 0.56),
                                  (0.06, 0.10, 1.52, -2.55, 0.84, 0.56), (0.06, 0.10, 1.52, -2.55, -0.84, 0.56)):
        b = geo.box((sx, sy, sz), bevel=0.01, name="Vulture_Frame")
        geo.transform(b, loc=(x, y, z))
        fr.append(b)
    mpaint = P["shell"].material_slots[0].material
    parts += [uv_point(put_mat(b, mpaint), "Vehicle_Van") for b in fr]
    # the two leaves
    dm = decal_mat(vulture_decals())
    m_glass, t_glass = tiling("TS_Glass_CarTint")
    m_int, t_int = tiling("TS_Plastic_CarInterior")
    chrome, t_chrome = tiling("TS_Chrome_Polished")
    for side, ang in ((-1, 111.7), (1, -88.8)):
        leaf = geo.box((0.045, 0.85, 1.44), bevel=0.008, name="Vulture_Leaf")
        geo.transform(leaf, loc=(0, -side * 0.425, 0))
        uv_point(put_mat(leaf, mpaint), "Vehicle_Van")
        inner = geo.box((0.012, 0.70, 1.20), bevel=0.004, name="Vulture_LeafInner")
        geo.transform(inner, loc=(0.028, -side * 0.425, 0.10))
        put_mat(inner, m_int, t_int)
        pane = geo.box((0.012, 0.50, 0.36), bevel=0.004, name="Vulture_Pane")
        geo.transform(pane, loc=(-0.020, -side * 0.45, 1.62 - 0.60 - 0.18))
        put_mat(pane, m_glass, t_glass)
        hnd = geo.box((0.03, 0.14, 0.03), bevel=0.006, name="Vulture_Handle")
        geo.transform(hnd, loc=(-0.035, -side * 0.78, 0.55))
        put_mat(hnd, chrome, t_chrome)
        lf = geo.join([leaf, inner, pane, hnd], "Vulture_Door")
        geo.transform(lf, loc=(0, 0, 0.60))
        geo.transform(lf, rot=(0, 0, ang))
        geo.transform(lf, loc=(-2.53, side * 0.89, 0))
        parts.append(lf)
    # cargo
    card = set_material("TS_Fabric_ScanBurlap", slot="MI_Fabric_ScanBurlap") if os.path.exists(
        paths.texture_set("TS_Fabric_ScanBurlap")) else m_int
    wood = set_material("TS_Wood_ScanPallet", slot="MI_Wood_ScanPallet")
    t_wood = mat.scan_tile("TS_Wood_ScanPallet")
    c1 = geo.box((0.50, 0.42, 0.36), bevel=0.01, name="Vulture_Carton")
    geo.transform(c1, rot=(0, 0, 8))
    geo.transform(c1, loc=(-1.9, 0.35, 0.60))
    c2 = geo.box((0.40, 0.36, 0.30), bevel=0.01, name="Vulture_Carton")
    geo.transform(c2, rot=(0, 0, -5))
    geo.transform(c2, loc=(-1.88, 0.33, 0.96))
    cr = geo.box((0.70, 0.50, 0.34), bevel=0.008, name="Vulture_Crate")
    geo.transform(cr, loc=(-1.6, -0.40, 0.60))
    cardboard = set_material("Prop_CardboardBox", slot="M_Prop_CardboardBox") if os.path.exists(
        paths.texture_set("Prop_CardboardBox")) else card
    for o in (c1, c2):
        parts.append(put_mat(o, cardboard, 0.6))
    parts.append(put_mat(cr, wood, t_wood))
    # livery on both flanks
    sh = P["shell"]
    for side in (1, -1):
        parts.append(decal(sh, "Vulture_Bird", -1.0 - 0.575, -1.0 + 0.575, 1.64 - 0.46, 1.64 + 0.46, side,
                           (0.0, 1.0 - 1024 / 2048, 1280 / 2048, 1.0), dm, nx=24, nz=20))
        ar = sp["axles"][1]
        for xa, xb_ in ((-2.45, ar - 0.48), (ar + 0.48, sp["axles"][0] - 0.48)):     # stops at the arch edges
            f0, f1 = (xa + 2.45) / 3.70, (xb_ + 2.45) / 3.70
            parts.append(decal(sh, "Vulture_Stripe", xa, xb_, 0.78 - 0.045, 0.78 + 0.045, side,
                               (f0, 1 - 1160 / 2048, f1, 1 - 1100 / 2048), dm, nx=max(4, int(70 * (f1 - f0))), nz=2))
        u0 = 0.0 if side < 0 else 1000 / 2048
        parts.append(decal(sh, "Vulture_Scrawl", 1.1 - 0.33, 1.1 + 0.33, 0.98 - 0.145, 0.98 + 0.145, side,
                           (u0, 1 - 1700 / 2048, u0 + 900 / 2048, 1 - 1300 / 2048), dm, nx=16, nz=8))
    ob = assemble(ctx, "SM_Vehicle_Van_Vulture", parts, dirt=0.6)
    declare(ctx, ob, "VanVulture", "The crew's van: the cargo van body near-black, both barn doors open (right 111.7, "
            "left 88.8 degrees, hinges at x -2.53, y +-0.89), bare dark load space with two taped cartons and a crate, "
            "vulture stencil, oxblood stripe and scrawls (M_Vehicle_VanVulture_Decals), plate LWG·4418. Collision: the "
            "closed body box only (to 2.14).", 2.14, expect=(5.99, 2.21, 2.19))
    return ob


def ipx_door(ctx, right=True):
    """One rear vault door leaf, pivot on its hinge line (outer edge), closed position: the leaf extends from the
    hinge toward the centre seam (+Y for the right leaf), outer face toward -X."""
    name = "SM_Vehicle_IPXTruck_Door" + ("" if right else "_Left")
    paint = set_material("Vehicle_IPXTruck", slot="M_Vehicle_IPXTruck_Paint", coat=1.0, tint=hexcol("#17191d"))
    s = 1 if right else -1
    panel = geo.box((0.06, 0.89, 1.62), bevel=0.010, name=name + "_Panel")
    geo.transform(panel, loc=(0, s * 0.445, 0))
    uv_point(put_mat(panel, paint), "Vehicle_IPXTruck")
    dark, t_dark = tiling("TS_Steel_CargoDark")
    inset = geo.box((0.012, 0.66, 0.70), bevel=0.004, name=name + "_Inset")
    geo.transform(inset, loc=(-0.033, s * 0.46, 0.12))
    m_glass, t_glass = tiling("TS_Glass_CarTint")
    port = geo.box((0.02, 0.34, 0.22), bevel=0.006, name=name + "_Port")
    geo.transform(port, loc=(-0.027, s * 0.46, 1.25))
    chrome, t_chrome = tiling("TS_Chrome_Polished")
    bar = geo.cylinder(0.014, 0.90, 16, name=name + "_LockBar")
    geo.transform(bar, loc=(-0.042, s * 0.80, 0.36))
    boss = geo.cylinder(0.045, 0.02, 24, bevel=0.005, base=False, name=name + "_Boss", axis="X")
    geo.transform(boss, loc=(-0.042, s * 0.80, 0.82))
    parts = [panel, put_mat(inset, dark, t_dark), put_mat(port, m_glass, t_glass), put_mat(bar, chrome, t_chrome),
             put_mat(boss, chrome, t_chrome)]
    for z in (0.25, 1.35):
        h = geo.cylinder(0.025, 0.16, 16, name=name + "_Hinge")
        geo.transform(h, loc=(-0.012, s * 0.01, z))
        parts.append(put_mat(h, chrome, t_chrome))
    dm = decal_mat(ipx_decals())
    # gold band across the leaf at truck height 1.36 (door base at 1.05) and the art at 1.75
    band = geo.box((0.002, 0.88, 0.11), bevel=0.0, name=name + "_Band")
    geo.transform(band, loc=(-0.031, s * 0.445, 1.36 - 1.05 - 0.055))
    _uv_card(band, (0.0, 1 - 663 / 2048, 1.0, 1 - 600 / 2048), s)
    parts.append(put_mat(band, dm))
    if right:
        art = geo.box((0.002, 0.62, 0.26), bevel=0.0, name=name + "_Art")
        _uv_card(art, (0.0, 1 - 1222 / 2048, 0.5, 1 - 800 / 2048), s)
    else:
        art = geo.box((0.002, 0.74, 0.092), bevel=0.0, name=name + "_Art")
        _uv_card(art, (0.5, 1 - 928 / 2048, 1.0, 1 - 800 / 2048), s)
    geo.transform(art, loc=(-0.032, s * 0.445, 1.75 - 1.05 - art.dimensions.z / 2))
    parts.append(put_mat(art, dm))
    ob = geo.join(parts, name, ctx.col)
    finish(ob, 0.25)
    ctx.asset(ob, collision="none", cover_height=None, notes="IPX vault door leaf (%s), pivot on the hinge line at the "
              "outer edge, closed pose: outer face toward -X, leaf toward the centre seam. On the truck: hinge at "
              "(%.2f, %+.3f, 1.05); opens %s108.9 degrees about Z in 1.1 s. No collision." %
              (IPX_DOOR_X, "right, -Y side of the truck" if right else "left, +Y side", -0.89 * s, "+" if right else "-"),
              expect_size=(0.07, 0.89, 1.62), slots=slot_records(ob))
    return ob


def _uv_card(ob, uv, s):
    """0..1 planar UVs over a card facing -X (reads left to right from behind the truck: +Y is to the right)."""
    u0, v0, u1, v1 = uv
    me = ob.data
    lo, hi = scene.bounds(ob)
    uvl = me.uv_layers.get(geo.UV) or me.uv_layers.new(name=geo.UV)
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            fu = (hi[1] - v.y) / max(hi[1] - lo[1], 1e-6)
            fv = (v.z - lo[2]) / max(hi[2] - lo[2], 1e-6)
            uvl.data[li].uv = (u0 + (u1 - u0) * fu, v0 + (v1 - v0) * fv)


IPX_DOOR_X = -3.00          # x of the rear door plane of the generated IPX body (measured on the fitted mesh)


def v_ipx(ctx):
    P = make_parts(ctx, "IPXTruck")
    sp = P["spec"]
    parts = [P["shell"], P["glass"]] + P["wheels"] + P["wells"] + P["interior"] + P["seats"]
    parts += [plate("KQB5530", (pc[0] + f * 0.004, pc[1], pc[2]), f, size=(pc[3], pc[4]), name="IPX_Plate")
              for pc, f in P["plates"]]
    galv = set_material("TS_Galvanised_Aged", slot="MI_Galvanised_Aged")
    t_galv = (bake.read_set("TS_Galvanised_Aged") or {}).get("tile_m", 1.0)
    tail = -sp["size"][0] / 2
    door_x = IPX_DOOR_X                         # the generated rear door plane (the step bumper reaches the tail)
    # vault lining 3.58 x 1.80 x 1.56, floor 1.02, open at the tail
    x1 = door_x + 0.02
    lin = geo.box((3.58, 1.80, 1.56), bevel=0.0, name="IPX_Vault")
    geo.transform(lin, loc=(x1 + 1.79, 0, 1.02))
    bm = bmesh.new()
    bm.from_mesh(lin.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.x < -0.9], context="FACES")
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(lin.data)
    bm.free()
    parts.append(put_mat(lin, galv, t_galv))
    for side in (1, -1):
        for z in (1.40, 1.80, 2.20):
            sh = geo.box((3.2, 0.30, 0.025), bevel=0.004, name="IPX_Shelf")
            geo.transform(sh, loc=(x1 + 1.9, side * 0.74, z))
            parts.append(put_mat(sh, galv, t_galv))
    lp = geo.box((1.2, 0.5, 0.03), bevel=0.006, name="IPX_CeilingLight")
    geo.transform(lp, loc=(x1 + 1.8, 0, 1.02 + 1.56 - 0.035))
    lm = P["shell"].material_slots[2].material
    parts.append(put_mat(lp, lm))
    geo.uv_world_box(lp, 50.0)
    dm = decal_mat(ipx_decals())
    bulk = geo.box((0.002, 0.80, 0.33), bevel=0.0, name="IPX_Bulkhead")
    _uv_card(bulk, (0.0, 1 - 1222 / 2048, 0.5, 1 - 800 / 2048), 1)
    geo.transform(bulk, loc=(x1 + 3.575, 0, 1.95))
    parts.append(put_mat(bulk, dm))
    # livery: art panel 3.50 x 0.875 centred x -1.42, height 2.10; gold band 0.11 at 1.36 along the vault and 1.2 m
    # of the cab; lozenge 0.80 x 0.33 on the bonnet
    sh = P["shell"]
    for side in (1, -1):
        parts.append(decal(sh, "IPX_Panel", -1.42 - 1.75, -1.42 + 1.75, 2.10 - 0.4375, 2.10 + 0.4375, side,
                           (0.0, 1 - 512 / 2048, 1.0, 1.0), dm, nx=50, nz=10))
        parts.append(decal(sh, "IPX_Band", tail + 0.05, 0.55 + 1.2, 1.36 - 0.055, 1.36 + 0.055, side,
                           (0.0, 1 - 663 / 2048, 1.0, 1 - 600 / 2048), dm, nx=90, nz=2))
    # bonnet lozenge: projected from above
    bon = geo.grid_on_top(sh, "IPX_Bonnet", 2.95, 0.0, 0.80, 0.33, (0.0, 1 - 1222 / 2048, 0.5, 1 - 800 / 2048), dm) \
        if hasattr(geo, "grid_on_top") else top_decal(sh, "IPX_Bonnet", 2.95, 0.0, 0.80, 0.33,
                                                       (0.0, 1 - 1222 / 2048, 0.5, 1 - 800 / 2048), dm)
    if bon is not None:
        parts.append(bon)
    ob = assemble(ctx, "SM_Vehicle_IPXTruck", parts, dirt=0.25)
    declare(ctx, ob, "IPXTruck", "Extraction truck: armoured cash-in-transit body (generated, cleaned), gloss black "
            "(#17191d) with the IPX livery as decals (M_Vehicle_IPXTruck_Decals, swappable lozenge), galvanised vault "
            "lining 3.58 x 1.80 x 1.56 with shelves and a ceiling light (Lamp slot), hazard lamps on their own slot "
            "M_Vehicle_IPXTruck_Hazard (E). Rear door leaves are separate: SM_Vehicle_IPXTruck_Door (right) and "
            "_Door_Left. Hard cover: vault 2.86, cab 2.58.", 2.86)
    return ob


def top_decal(target, name, cx, cy, w, h, uv, m, nx=16, ny=8, lift=0.003):
    """Card projected from above onto the target (bonnet marks); reads from the front of the vehicle."""
    from mathutils.bvhtree import BVHTree
    bm_t = bmesh.new()
    bm_t.from_mesh(target.data)
    bvh = BVHTree.FromBMesh(bm_t)
    bm_t.free()
    u0, v0, u1, v1 = uv
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new(geo.UV)
    g = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            x = cx - h / 2 + h * j / ny
            y = cy - w / 2 + w * i / nx
            hit = bvh.ray_cast(Vector((x, y, 5.0)), Vector((0, 0, -1)), 10.0)
            if hit[0] is None:
                return None
            nrm = hit[1] if hit[1].z > 0 else -hit[1]
            g[i, j] = bm.verts.new(hit[0] + nrm * lift)
    for i in range(nx):
        for j in range(ny):
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            f = bm.faces.new([g[k] for k in q])
            for lp, (a, b) in zip(f.loops, q):
                lp[uvl].uv = (u0 + (u1 - u0) * a / nx, v0 + (v1 - v0) * b / ny)
    ob = geo.new(name, bm, uv=False, smooth=60)
    geo.recalc_normals(ob)
    ob.data.materials.append(m)
    return ob


def v_boxtruck(ctx):
    P = make_parts(ctx, "BoxTruck")
    sp = P["spec"]
    parts = [P["shell"], P["glass"]] + P["wheels"] + P["wells"] + P["interior"] + P["seats"]
    parts += make_plates(P, sp["plate"])
    dm = decal_mat(boxtruck_decals())
    sh = P["shell"]
    # variant 0: RULE on the right flank (-Y) at x -1.76, HOLLIS on the left (+Y) at x -0.96; centre height 1.90
    for side, xc, v in ((-1, -1.76, (0.0, 1 - 945 / 2048, 1.0, 1.0)), (1, -0.96, (0.0, 1 - 1969 / 2048, 1.0, 1 - 1024 / 2048))):
        parts.append(decal(sh, "Truck_Tag", xc - 1.3, xc + 1.3, 1.90 - 0.6, 1.90 + 0.6, side, v, dm, nx=40, nz=18))
    ob = assemble(ctx, "SM_Vehicle_BoxTruck", parts, dirt=0.45)
    declare(ctx, ob, "BoxTruck", "Medium-duty straight truck with a dry-freight box (generated, cleaned): cab always "
            "white (M_Vehicle_BoxTruck_PaintCab), box in the instance colour (M_Vehicle_BoxTruck_Paint, tint mask), "
            "twin rear tyres, spray tags RULE / HOLLIS (variant 0 placement) on M_Vehicle_BoxTruck_Decals. Colliders: "
            "box x -3.64..1.12, y +-1.20, 0..3.30; cab x 1.12..3.70, y +-1.06, 0..2.28.", 3.30)
    return ob


def v_moto(ctx):
    """The motorbike keeps its generated wheels; paint / trim / lamps split by colour, leaned 7 degrees onto a side
    stand on its left (+Y)."""
    key = "Motorbike"
    sp = SPEC[key]
    name = "SM_Vehicle_Motorbike"
    ob, tex = gen3d.load(os.path.join(GEN, sp["src"]), name + "_Gen", ctx.col)
    gen3d.orient(ob, sp["axis"], sp["nose"])
    gen3d.fit_box(ob, (1.94, 0.62, 1.10))
    c, n, a = gen3d.face_arrays(ob)
    rgb, rough, metal = gen3d.face_samples(ob, tex)
    red = (rgb[:, 0] > 0.08) & (rgb[:, 0] > 3 * rgb[:, 1])
    if red.any() and c[red, 0].mean() > 0:            # tail lamp at +X: turn round
        co = gen3d.verts(ob)
        co[:, :2] *= -1
        gen3d.set_verts(ob, co)
        c, n, a = gen3d.face_arrays(ob)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    cls = np.full(len(c), CLS["trim"], np.int32)
    blue = (rgb[:, 2] > 1.35 * rgb[:, 0]) & (rgb[:, 2] > 0.02) & (metal < 0.5)
    cls[blue] = CLS["paint"]
    red = (rgb[:, 0] > 0.08) & (rgb[:, 0] > 3 * rgb[:, 1]) & (c[:, 0] < -0.5)
    cls[red] = CLS["tail"]
    amber = (rgb[:, 0] > 0.2) & (rgb[:, 1] > 0.05) & (rgb[:, 1] < 0.6 * rgb[:, 0]) & (rgb[:, 2] < 0.4 * rgb[:, 1])
    cls[amber] = CLS["amber"]
    head = (c[:, 0] > 0.6) & (c[:, 2] > 0.75) & (c[:, 2] < 1.0) & (n[:, 0] > 0.5) & (lum > 0.25) & (metal < 0.5)
    cls[head] = CLS["head"]
    # (review fix) the seat is black vinyl, not tank paint
    seat = (cls == CLS["paint"]) & (c[:, 0] > -0.55) & (c[:, 0] < 0.05) & (c[:, 2] > 0.75) & (n[:, 2] > 0.2)
    cls[seat] = CLS["trim"]
    if os.environ.get("VEH_DEBUG"):
        debug_classes(ob, cls, os.path.join(GEN, "debug_%s.jpg" % key))
    set_name = "Vehicle_Motorbike"
    if ctx.args.force or ctx.args.bake or not os.path.exists(os.path.join(paths.texture_set(set_name), "set.json")):
        body_set(set_name, raster_classes(ob, cls, tex["size"]), tex, {"asset": name, "family": "vehicles",
                                                                       "source": "art/out/gen/vehicles/" + sp["src"]})
    del tex
    ms = [set_material(set_name, slot="M_Vehicle_Motorbike_Paint", coat=1.0, tint=hexcol(CHART[sp["paint"]])),
          set_material(set_name, slot="M_Vehicle_Motorbike_Trim"),
          set_material(set_name, slot="M_Vehicle_Motorbike_Lamp")]
    ob.data.materials.clear()
    for m in ms:
        ob.data.materials.append(m)
    gen3d.set_face_materials(ob, np.select([cls == CLS["paint"], cls == CLS["trim"]], [0, 1], 2))
    gen3d.decimate(ob, 1.0, target=sp["tris"])
    geo.smooth_by_angle(ob, 50)
    # side stand on the left, then lean onto it
    galv, t_galv = tiling("TS_Paint_WheelSteel")
    # the foot sits 0.30 * tan 7 above the ground before the lean, so after it the tyres and the foot both touch
    fz = 0.30 * math.tan(math.radians(7.0))
    stand = geo.pipe([(-0.10, 0.10, 0.30), (-0.22, 0.30, fz + 0.012)], 0.011, name="Moto_Stand")
    foot = geo.box((0.07, 0.04, 0.01), bevel=0.002, name="Moto_Foot")
    geo.transform(foot, loc=(-0.22, 0.30, fz))
    ob = geo.join([ob, put_mat(stand, galv, t_galv), put_mat(foot, galv, t_galv)], name, ctx.col)
    geo.transform(ob, rot=(-7.0, 0, 0))
    co = gen3d.verts(ob)
    co[:, 2] -= co[:, 2].min()
    co[:, 2] *= 1.10 / co[:, 2].max()
    co[:, 1] -= (co[:, 1].min() + co[:, 1].max()) / 2
    gen3d.set_verts(ob, co)
    finish(ob, 0.3)
    se = export.set_entry(set_name)
    slots = {m.name: {"set": set_name, "textures": se["textures"] if se else None} for m in ms}
    slots[ms[0].name]["shading"] = "clear-coat paint (tank, tail, mudguard); BC is a tint mask"
    slots[ms[0].name]["paint_default"] = [round(float(v), 4) for v in hexcol(CHART[sp["paint"]])]
    slots[ms[0].name]["paint_default_srgb"] = CHART[sp["paint"]]
    ctx.asset(ob, collision="box", cover_height=0.95, notes="Standard naked motorcycle (generated, cleaned), leaned 7 "
              "degrees onto its side stand (+Y). Paint slot is a tint mask (#1b2a4a or #14161a on the block).",
              expect_size=(1.94, None, 1.10), slots=slots)
    return ob


def pickup_extra(ctx, P):
    """Spare tyre lying flat and a timber crate in the bed (the generated bed contents were dropped)."""
    sp = SPEC["Pickup"]
    out = []
    # (review fix) cab back wall with the rear window, measured on the shell: the roof's rear edge
    c, n, _ = gen3d.face_arrays(P["raw"])
    H = sp["size"][2]
    roof = (n[:, 2] > 0.8) & (c[:, 2] > H - 0.15) & (np.abs(c[:, 1]) < 0.5)
    cab_x = float(np.percentile(c[roof, 0], 1)) if roof.sum() > 20 else -0.45
    roof_z = float(np.percentile(c[roof, 2], 50)) if roof.sum() > 20 else H - 0.03
    hw = sp["size"][1] / 2 - 0.11
    z0, zw0, zw1, z1 = 0.56, sp["belt"] + 0.04, roof_z - 0.11, roof_z - 0.025
    wy = 0.56
    t_ = 0.035
    xw = cab_x + 0.004 + t_ / 2
    mpaint = P["shell"].material_slots[0].material
    wall = []
    for (sy, sz, y, z) in ((2 * hw, zw0 - z0, 0.0, z0), (2 * hw, z1 - zw1, 0.0, zw1),
                           (hw - wy, zw1 - zw0, (hw + wy) / 2, zw0), (hw - wy, zw1 - zw0, -(hw + wy) / 2, zw0)):
        b = geo.box((t_, sy, sz), bevel=0.006, name="Pickup_CabBack")
        geo.transform(b, loc=(xw, y, z))
        wall.append(uv_point(put_mat(b, mpaint), "Vehicle_Pickup"))
    out += wall
    m_glass, t_glass = tiling("TS_Glass_CarTint")
    pane = geo.box((0.006, 2 * wy + 0.02, zw1 - zw0 + 0.02), bevel=0.002, name="Pickup_RearGlass")
    geo.transform(pane, loc=(xw - t_ / 2 + 0.004, 0, zw0 - 0.01))
    out.append(put_mat(pane, m_glass, t_glass))
    m_rub, t_rub = tiling("TS_Rubber_Tyre")
    xs = xw - t_ / 2 - 0.004
    seal = geo.pipe([(xs, -wy, zw0), (xs, wy, zw0), (xs, wy, zw1), (xs, -wy, zw1), (xs, -wy, zw0)], 0.009,
                    segments=8, bend_radius=0.04, name="Pickup_RearSeal")
    out.append(put_mat(seal, m_rub, t_rub))
    # the seats inside the cab: headrest back 0.08 ahead of the wall
    fx = sp.get("seat_x", sp["bpillar"] - 0.12)
    shift = max(0.0, cab_x + t_ + 0.42 - fx)
    for o in P["seats"]:
        geo.transform(o, loc=(shift, 0, 0))
    ctx.log("Pickup: cab back at x %.3f (roof %.3f), seats moved %.2f forward" % (cab_x, roof_z, shift))
    t = tyre(0.33, 0.22, 0.20, name="Pickup_Spare")
    geo.transform(t, rot=(90, 0, 0))
    geo.transform(t, loc=(-1.75, 0.25, 0.92 + 0.11))
    out.append(put_mat(t, *tiling("TS_Rubber_Tyre")))
    disc = geo.cylinder(0.20, 0.12, 32, bevel=0.01, base=False, name="Pickup_SpareRim")
    geo.transform(disc, loc=(-1.75, 0.25, 0.92 + 0.11))
    out.append(put_mat(disc, *tiling("TS_Paint_WheelSteel")))
    wood = set_material("TS_Wood_ScanPallet", slot="MI_Wood_ScanPallet")
    cr = geo.box((0.50, 0.42, 0.40), bevel=0.01, name="Pickup_Crate")
    geo.transform(cr, rot=(0, 0, 12))
    geo.transform(cr, loc=(-1.05, -0.35, 0.92))
    out.append(put_mat(cr, wood, mat.scan_tile("TS_Wood_ScanPallet")))
    return out


SPEC.update({
    "VanVulture": dict(SPEC["Van"], set="Vehicle_Van", paint="black", plate="LWG4418",
                       drop=lambda c, n, cls: (c[:, 0] < -2.45) & (c[:, 2] > 0.58) & (c[:, 2] < 2.08) & (np.abs(c[:, 1]) < 0.87)),
    "BoxTruck": dict(bn=1.30, ws_top=2.18, ws_inset=0.30, cabin_inside=False, src="boxtruck_hunyuan80k.glb", axis="Y", nose=-1, size=(7.39, 2.44, 3.31), axles=(2.95, -2.09),
                     r=0.44, tw=0.28, rim=0.27, belt=1.50, cowl=2.55, bpillar=1.65, rear_x=1.20, floor=1.0,
                     cabin_rear=1.25, seat_x=1.55, wheel="steel", twin=True, rear_seat=False, plate="HLS2141",
                     paint="mustard", paint2=lambda c: c[:, 0] > _box_front(c) + 0.03, paint2_colour="#d9d7d0", cover=3.30, tris=48000),
    "IPXTruck": dict(bn=1.30, ws_top=1.57, ws_inset=0.30, cabin_inside=False, src="ipx_hunyuan80k.glb", axis="Y", nose=-1, size=(6.81, 2.48, 2.96), axles=(2.05, -1.75),
                     r=0.50, tw=0.30, rim=0.30, belt=1.75, cowl=2.30, bpillar=0.70, rear_x=0.60, floor=1.05,
                     cabin_rear=0.62, seat_x=1.00, wheel="steel", twin=True, rear_seat=False, plate="KQB5530",
                     paint="#17191d", hazard_slot=True, cover=2.86, tris=50000,
                     drop=lambda c, n, cls: _ipx_drop(c, n, cls)),
    "Motorbike": dict(src="moto_hunyuan100k.glb", axis="X", nose=1, paint="navy", tris=90000),
})
def _box_front(c):
    """x of the cargo box's front face: the front of everything above the cab roof (2.28)."""
    k = c[:, 2] > 2.45
    return float(np.percentile(c[k, 0], 99.5)) if k.sum() > 50 else 1.0


def _ipx_drop(c, n, cls):
    """Generated rear door leaves (replaced by the separate door parts) and the generated partitions inside the vault.
    The door plane is measured here on the fitted mesh: the flat rear faces at door height."""
    global IPX_DOOR_X
    k = (n[:, 0] < -0.85) & (c[:, 2] > 1.25) & (c[:, 2] < 2.50) & (np.abs(c[:, 1]) < 0.80) & (c[:, 0] < -2.4)
    if k.sum() > 30:
        IPX_DOOR_X = round(float(np.median(c[k, 0])), 3)
    SPEC["IPXTruck"]["door_x"] = IPX_DOOR_X
    dx = IPX_DOOR_X + 0.18
    leaves = (c[:, 0] < dx) & (c[:, 2] > 1.03) & (c[:, 2] < 2.69) & (np.abs(c[:, 1]) < 0.95)
    # partitions inside the vault; the outer skin (|y| > 0.85) stays
    inner = (c[:, 0] < 0.50) & (c[:, 0] > dx) & (c[:, 2] > 1.06) & (c[:, 2] < 2.78) & (np.abs(c[:, 1]) < 0.85)
    return leaves | inner


def _pickup_reclass(c, n, cls):
    """The bed inside reads as black bedliner (the generated paint / trim sawtooth on the arch housings goes)."""
    bed = (c[:, 0] < -0.70) & (c[:, 0] > -2.55) & (np.abs(c[:, 1]) < 0.96) & (c[:, 2] > 0.50) & (c[:, 2] < 1.10)
    inner = bed & ((n[:, 2] > 0.6) | (n[:, 1] * np.sign(c[:, 1]) < -0.3) | (n[:, 0] > 0.6))
    cls[inner & np.isin(cls, [CLS["paint"], CLS["trim"], CLS["inside"]])] = CLS["trim"]


def _bed_contents(c, n, cls):
    bed = (c[:, 0] < -0.75) & (c[:, 0] > -2.45) & (np.abs(c[:, 1]) < 0.70)
    up = bed & (n[:, 2] > 0.85) & (c[:, 2] < 1.2)
    floor = float(np.percentile(c[up, 2], 10)) if up.sum() > 20 else 0.92
    return bed & (c[:, 2] > floor + 0.04) & (c[:, 2] < 1.5)


SPEC["Pickup"]["drop"] = _bed_contents
SPEC["Pickup"]["reclass"] = _pickup_reclass
for _k in ("Sedan", "SUV", "Pickup", "Van", "VanVulture"):
    SPEC[_k]["wipers"] = True
SPEC["SUV"]["side_glass"] = (-2.08, -1.42, 1.27, 1.68)        # quarter lights (review fix)
SPEC["Pickup"]["extra"] = pickup_extra


def declare(ctx, ob, key, notes, cover, collision="box", expect=None):
    spec = SPEC.get(key, {})
    slots = slot_records(ob)
    ctx.asset(ob, collision=collision, cover_height=cover, notes=notes,
              expect_size=expect or spec.get("size"), slots=slots)


# ------------------------------------------------------------------------------------------------------- family
NOTES = {
    "Sedan": "Generic year-2000 saloon (generated body, cleaned): paint slot is a tint mask (chart colours), glass "
             "with a dark interior behind it, chrome hubcaps (variants: dark steel wheels). Cover 1.08 body, 1.45 cabin.",
    "SUV": "Full-size two-box 4x4 (generated body, cleaned), five-spoke alloys, roof rails, running boards. Rule's ride "
           "is the black one (#14161a). Cover 1.24 body, 1.78 cabin.",
    "Pickup": "Single-cab long-bed pickup (generated body, cleaned), steel wheels, spare tyre and crate in the bed. "
              "Cover 1.27 body, 1.78 cab.",
    "Van": "Cargo panel van (generated body, cleaned), steel wheels, glass in the cab only. Hard cover to 2.14.",
}


def build(ctx):
    small_sets(ctx.args.force)
    only = ctx.args.only or []
    previews = [o for o in only if o.startswith("vehicles_")]
    need = {
        "vehicles_sedan_hero": ["Sedan"], "vehicles_lineup_1": ["Sedan", "Taxi", "SUV", "Pickup", "Van"],
        "vehicles_lineup_2": ["VanVulture", "BoxTruck", "Motorbike"], "vehicles_ipx_truck": ["IPXTruck"],
        "vehicles_wrecks": ["BurnedCar", "StrippedCar"], "vehicles_close": ["Sedan"], "vehicles_wire": ["VanVulture", "SUV"],
    }
    want = set()
    for p in previews:
        want.update(need.get(p, []))
    for o in only:
        if o.startswith("SM_Vehicle_"):
            k = o[len("SM_Vehicle_"):].replace("Van_Vulture", "VanVulture").replace("IPXTruck_Door_Left", "IPXTruck") \
                .replace("IPXTruck_Door", "IPXTruck")
            want.add(k)
    every = not only
    W = lambda k: every or k in want
    out = []
    sedan = None
    if W("Sedan") or W("Taxi") or W("BurnedCar") or W("StrippedCar"):
        ob, sedan = v_simple(ctx, "Sedan", NOTES["Sedan"], keep=True)
        out.append(ob)
    for k in ("SUV", "Pickup", "Van"):
        if W(k):
            out.append(v_simple(ctx, k, NOTES[k])[0])
    if W("Taxi"):
        out.append(v_taxi(ctx, sedan))
    if W("BurnedCar"):
        out.append(v_burned(ctx, sedan))
    if W("StrippedCar"):
        out.append(v_stripped(ctx, sedan))
    if W("VanVulture"):
        out.append(v_vulture(ctx))
    if W("BoxTruck"):
        out.append(v_boxtruck(ctx))
    if W("IPXTruck"):
        out.append(v_ipx(ctx))
        out.append(ipx_door(ctx, True))
        out.append(ipx_door(ctx, False))
    if W("Motorbike"):
        out.append(v_moto(ctx))
    return out


# ------------------------------------------------------------------------------------------------------ previews
def _street(ctx):
    """A strip of street for the cars to stand on: the street family's scanned asphalt, kerb concrete, brick wall."""
    items = []
    road = geo.box((160.0, 14.0, 0.2), bevel=0.0, name="PV_Road")
    geo.transform(road, loc=(0, -2.0, -0.2))
    put_mat(road, set_material("TS_Asphalt_ScanWorn", slot="MI_Asphalt_ScanWorn"), mat.scan_tile("TS_Asphalt_ScanWorn"))
    walk = geo.box((160.0, 4.0, 0.15), bevel=0.01, name="PV_Walk")
    geo.transform(walk, loc=(0, 7.0, 0.0))
    put_mat(walk, set_material("TS_Concrete_ScanWeathered", slot="MI_Concrete_ScanWeathered"),
            mat.scan_tile("TS_Concrete_ScanWeathered"))
    wall = geo.box((160.0, 0.4, 9.0), bevel=0.0, name="PV_Wall")
    geo.transform(wall, loc=(0, 9.2, 0))
    put_mat(wall, set_material("TS_Brick_ScanRed", slot="MI_Brick_ScanRed"), mat.scan_tile("TS_Brick_ScanRed"))
    items += [road, walk, wall]
    return items


def _show(assets, placed):
    for n, o in assets.items():
        o.hide_render = n not in placed
        if n in placed:
            x, y, yaw = placed[n]
            o.location = (x, y, 0)
            o.rotation_euler = (0, 0, math.radians(yaw))


def on_preview(ctx, objs):
    a = ctx.args
    only = set(a.only or [])
    render.setup(samples=a.samples, res=(1280, 720))
    render.rig_day(sun_azimuth=render.DESIGN_SUN_BEARING)
    _street(ctx)
    assets = {n: v["ob"] for n, v in ctx.assets.items()}
    for o in bpy.context.scene.objects:
        if o.name.endswith("_Raw"):
            o.hide_render = True

    def want(p):
        return not only or p in only

    def shot(fname):
        p, sec = render.render_jpeg(os.path.join(paths.previews, fname), a.samples)
        ctx.log("preview %s %.0fs" % (p, sec))

    if want("vehicles_sedan_hero") and "SM_Vehicle_Sedan" in assets:
        _show(assets, {"SM_Vehicle_Sedan": (0, 3.9, 0)})
        render.cam_look((3.55, 2.05, 1.45), (0.9, 4.05, 0.72), lens=30)
        shot("vehicles_sedan_hero.jpg")
    if want("vehicles_close") and "SM_Vehicle_Sedan" in assets:
        _show(assets, {"SM_Vehicle_Sedan": (0, 3.9, 0)})
        render.cam_look((2.05, 2.25, 0.95), (0.95, 3.05, 0.58), lens=28)
        shot("vehicles_close.jpg")
    if want("vehicles_lineup_1"):
        _show(assets, {"SM_Vehicle_Sedan": (-8.4, 3.9, 0), "SM_Vehicle_Taxi": (-2.9, 3.9, 0),
                       "SM_Vehicle_SUV": (2.8, 3.85, 0), "SM_Vehicle_Pickup": (8.9, 3.85, 0)})
        render.cam_look((15.5, -2.6, 1.9), (-0.5, 3.9, 0.85), lens=30)
        shot("vehicles_lineup_1.jpg")
    if want("vehicles_lineup_2"):
        _show(assets, {"SM_Vehicle_BoxTruck": (-10.5, 3.6, 0), "SM_Vehicle_Van": (-2.6, 3.85, 0),
                       "SM_Vehicle_Van_Vulture": (4.2, 1.9, 200), "SM_Vehicle_Motorbike": (9.3, 4.45, 20)})
        render.cam_look((13.6, -1.0, 1.75), (-1.0, 3.5, 1.05), lens=32)
        shot("vehicles_lineup_2.jpg")
    if want("vehicles_ipx_truck") and "SM_Vehicle_IPXTruck" in assets:
        pl = {"SM_Vehicle_IPXTruck": (0, 3.6, 180), "SM_Vehicle_IPXTruck_Door": (0, 0, 0),
              "SM_Vehicle_IPXTruck_Door_Left": (0, 0, 0)}
        _show(assets, pl)
        # doors open 108.9 degrees on their hinges; the truck is turned 180 so its tail faces +X
        L = 6.81 / 2
        for nm, s_ in (("SM_Vehicle_IPXTruck_Door", 1), ("SM_Vehicle_IPXTruck_Door_Left", -1)):
            d = assets[nm]
            hx, hy = IPX_DOOR_X, -0.89 * s_
            d.location = (-hx, 3.6 - hy, 1.05)
            d.rotation_euler = (0, 0, math.radians(180 + s_ * 108.9))
        render.cam_look((10.6, 1.0, 2.0), (3.0, 3.55, 1.6), lens=28)
        shot("vehicles_ipx_truck.jpg")
    if want("vehicles_wrecks"):
        _show(assets, {"SM_Vehicle_BurnedCar": (-2.8, 3.4, 12), "SM_Vehicle_StrippedCar": (3.0, 3.3, -8)})
        render.cam_look((0.4, -4.6, 2.5), (0.2, 3.4, 0.7), lens=28)
        shot("vehicles_wrecks.jpg")
    if want("vehicles_wire"):
        _show(assets, {"SM_Vehicle_Van_Vulture": (-3.4, 3.7, 200), "SM_Vehicle_SUV": (3.2, 3.85, 0)})
        clay = bpy.data.materials.new("PV_Clay")
        clay.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1)
        vl = bpy.context.view_layer
        old = vl.material_override
        vl.material_override = clay
        sc = bpy.context.scene
        sc.render.use_freestyle = True
        vl.use_freestyle = True
        ls = vl.freestyle_settings.linesets[0] if vl.freestyle_settings.linesets else vl.freestyle_settings.linesets.new("L")
        ls.select_by_visibility = True
        ls.select_by_edge_types = True
        ls.select_silhouette = ls.select_border = ls.select_crease = True
        ls.linestyle.thickness = 0.6
        ls.linestyle.color = (0.05, 0.05, 0.06)
        vl.freestyle_settings.crease_angle = math.radians(140)
        render.cam_look((1.6, -4.6, 2.6), (0.0, 3.8, 0.9), lens=28)
        shot("vehicles_wire.jpg")
        vl.material_override = old
        sc.render.use_freestyle = False
