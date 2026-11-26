"""Canal Street's road and sidewalk surface for the look-dev pictures, and the street dressing list for Unreal.

The review found the roadway an empty mirror: one flat roughness, no paint, no manholes, no drains, no patches, no wear. This
module makes (1) procedural surface materials that vary the way a wet city street does: roughness patches and puddles, polished
tyre tracks, cracks, grain bump, slab joints on the concrete; (2) the paint and cast-iron dressing as thin low-poly shapes:
double yellow centre line, two zebra crossings, stop line, gutters, trench and asphalt patches, manholes, drain inlets, a
sidewalk crack seam; (3) `tools/levels/data/street_dressing_chinatown.json`, the same list in the level's web coordinates, so
Unreal places the same decals and cast-iron pieces (the engine side is a decal actor per row; nothing the game loads changes).

    venv/bin/python art/blender/assets/_chinatown_street_look.py        # writes the json

Coordinates: web (x, z) as in level_chinatown.json; Blender y = -z. Canal's asphalt is web z -29.8..-19 (Blender y 19..29.8),
Mott's is x 10..16 from web z -19 on (Blender y 19 down to -32).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.dirname(HERE) not in sys.path:
    sys.path.insert(0, os.path.dirname(HERE))

REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT_JSON = os.path.join(REPO, "tools", "levels", "data", "street_dressing_chinatown.json")

CANAL_Y = (19.0, 29.8)
CENTRE_Y = 24.4
MOTT_X = (10.0, 16.0)

# ---- the list (Blender metres: x, y; sizes along x and y before rotation; rot in degrees about Z) -------------------------

def _zebra(cx, cy, along, n, pitch, bar_len, bar_w, rot):
    """n bars of a zebra crossing: bars of bar_len x bar_w, centred on (cx, cy), stepping `pitch` along the crossing."""
    items = []
    for i in range(n):
        o = (i - (n - 1) / 2.0) * pitch
        if along == "y":
            items.append(("paint_white", cx, cy + o, bar_len, bar_w, rot))
        else:
            items.append(("paint_white", cx + o, cy, bar_w, bar_len, rot))
    return items


def items():
    L = []
    # double yellow centre line of Canal, broken at Mott's mouth
    for x0, x1 in ((-44.0, 3.6), (18.4, 44.0)):
        for dy in (-0.075, 0.075):
            L.append(("paint_yellow", (x0 + x1) / 2, CENTRE_Y + dy, x1 - x0, 0.10, 0.0))
    # zebra across Canal west of Mott (bars along the traffic, stepping across the road), stop lines before it
    L += _zebra(6.4, 24.4, "y", 11, 0.9, 2.6, 0.45, 0.0)
    L.append(("paint_white", 3.9, 21.9, 0.35, 5.2, 0.0))     # stop line, westbound? lane (south half)
    L.append(("paint_white", 8.9, 26.9, 0.35, 5.2, 0.0))
    # zebra across Mott's mouth (bars along Mott, stepping across it)
    L += _zebra(13.0, 16.6, "x", 7, 0.9, 2.6, 0.45, 0.0)
    L.append(("paint_white", 11.5, 18.1, 3.0, 0.35, 0.0))
    # gutters along both kerbs (darker, rough, silt)
    L.append(("gutter", 0.0, CANAL_Y[0] + 0.18, 88.0, 0.36, 0.0))
    L.append(("gutter", 0.0, CANAL_Y[1] - 0.18, 88.0, 0.36, 0.0))
    # a utility trench patched across Canal, an old long patch along the south lane, two small pothole fills
    L.append(("patch_trench", -12.0, 24.4, 0.9, 10.8, 0.0))
    L.append(("patch", -27.0, 21.6, 3.4, 1.3, 0.0))
    L.append(("patch", 21.0, 27.0, 1.2, 2.2, 0.0))
    L.append(("patch", 33.0, 22.2, 0.8, 0.7, 12.0))
    # cast iron
    for x, y, r in ((-22.0, 22.6, 0.0), (-3.0, 26.7, 0.0), (28.0, 22.9, 0.0), (12.8, 6.0, 0.0), (14.2, -14.0, 0.0)):
        L.append(("manhole", x, y, 0.9, 0.9, r))
    for x, y, r in ((-30.0, 19.35, 0.0), (-8.0, 19.35, 0.0), (1.5, 19.35, 0.0), (-26.0, 29.45, 0.0), (6.0, 29.45, 0.0), (30.0, 29.45, 0.0)):
        L.append(("drain", x, y, 1.2, 0.5, r))
    # a heaved seam in the north sidewalk, and the sidewalk's gum and oil are in the shader
    L.append(("seam", -15.0, 31.6, 0.04, 4.2, 0.0))
    return L


def write_json(path=OUT_JSON):
    rows = []
    for kind, x, y, sx, sy, rot in items():
        rows.append({"kind": kind, "web": {"x": round(x, 3), "z": round(-y, 3)}, "size_m": [sx, sy], "rot_z_deg": rot})
    doc = {"about": "Canal Street street dressing (assets/_chinatown_street_look.py): road paint, gutters, patches, manholes, drain "
                    "inlets in the level's web coordinates (x, z). Paint, gutters and patches are decals on the asphalt; manholes and "
                    "drains are cast-iron pieces 5 to 15 mm proud. Look-dev picture shows each; in Unreal a decal actor per row. "
                    "Nothing the game loads reads this file.",
           "paint": {"yellow_rgb": [0.70, 0.52, 0.07], "white_rgb": [0.72, 0.72, 0.67], "wear": "noise mask, about 30 percent lost"},
           "count": len(rows), "items": rows}
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    return len(rows)


# ---- materials and shapes (Blender only) --------------------------------------------------------------------------------

def _nodes(name):
    import bpy
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    return m, nt


def _noise(nt, pos, scale, detail=4.0, rough=0.55):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    nt.links.new(pos, n.inputs["Vector"])
    return n.outputs["Fac"]


def _math(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _ramp(nt, fac, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    els = r.color_ramp.elements
    while len(els) > len(stops):
        els.remove(els[-1])
    while len(els) < len(stops):
        els.new(0.5)
    for e, (p, c) in zip(els, stops):
        e.position, e.color = p, c if len(c) == 4 else (*c, 1.0)
    nt.links.new(fac, r.inputs["Fac"])
    return r.outputs["Color"]


def _bump(nt, height, strength, dist, bsdf):
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = dist
    nt.links.new(height, b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bsdf.inputs["Normal"])


def asphalt():
    """Wet asphalt: aggregate colour drift, puddles (low roughness) where a big noise dips, polished tyre tracks on both
    lanes, hairline cracks, grain bump, oil-dark spots. Uses world position, so every ground piece shares one street."""
    import bpy
    m, nt = _nodes("Prev_WetAsphalt")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pos = nt.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    big = _noise(nt, pos, 0.22, 5.0)
    mid = _noise(nt, pos, 1.6, 6.0)
    grain = _noise(nt, pos, 70.0, 3.0)
    spot = _noise(nt, pos, 4.0, 2.0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(pos, sep.inputs[0])
    # tyre tracks: bands along x at the wheel paths of the four lanes (centre line 24.4, lanes 2.7 m off, tracks 0.75 apart)
    track = None
    for c in (21.5, 23.0, 25.8, 27.3):
        d = _math(nt, "SUBTRACT", sep.outputs["Y"], c)
        d2 = _math(nt, "MULTIPLY", d, d)
        g = _math(nt, "EXPONENT", _math(nt, "MULTIPLY", d2, -7.0))      # e^(-7 d^2): about 0.4 m wide
        track = g if track is None else _math(nt, "ADD", track, g)
    track = _math(nt, "MULTIPLY", track, _math(nt, "ADD", 0.55, _math(nt, "MULTIPLY", mid, 0.7)), clamp=True)
    # puddles: where the big noise is below a threshold (about 22 percent of the street)
    pud = _math(nt, "SUBTRACT", 0.50, big)
    pud = _math(nt, "MULTIPLY", pud, 9.0, clamp=True)
    # cracks: thin voronoi edges, only where the mid noise is high (so they come in groups, not as a mesh)
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 0.9
    nt.links.new(pos, vor.inputs["Vector"])
    crack = _math(nt, "SUBTRACT", 0.035, vor.outputs["Distance"])
    crack = _math(nt, "MULTIPLY", crack, 60.0, clamp=True)
    crack = _math(nt, "MULTIPLY", crack, _math(nt, "SUBTRACT", mid, 0.52), clamp=True)
    crack = _math(nt, "MULTIPLY", crack, 6.0, clamp=True)
    col = _ramp(nt, _math(nt, "ADD", _math(nt, "MULTIPLY", big, 0.6), _math(nt, "MULTIPLY", grain, 0.25)),
                [(0.15, (0.020, 0.020, 0.021)), (0.55, (0.036, 0.035, 0.034)), (0.85, (0.060, 0.056, 0.052))])
    dark = nt.nodes.new("ShaderNodeMix")
    dark.data_type = "RGBA"
    nt.links.new(_math(nt, "MULTIPLY", spot, 0.0), dark.inputs[0])       # placeholder wire: spots are in the colour ramp below
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[7].default_value = (0.008, 0.008, 0.009, 1.0)
    nt.links.new(_math(nt, "ADD", _math(nt, "MULTIPLY", track, 0.5), crack, clamp=True), mix.inputs[0])
    nt.links.new(col, mix.inputs[6])
    nt.links.new(mix.outputs[2], p.inputs["Base Color"])
    # roughness: dry 0.38..0.62 by the grain, polished tracks 0.12, puddles 0.04, cracks 0.7
    dry = _math(nt, "ADD", 0.20, _math(nt, "MULTIPLY", _math(nt, "ADD", mid, grain), 0.17))   # rained on: satin, not matte
    r1 = _math(nt, "MULTIPLY", dry, _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", track, 0.7)))
    r2 = _math(nt, "ADD", _math(nt, "MULTIPLY", r1, _math(nt, "SUBTRACT", 1.0, pud)), _math(nt, "MULTIPLY", pud, 0.04))
    r3 = _math(nt, "ADD", _math(nt, "MULTIPLY", r2, _math(nt, "SUBTRACT", 1.0, crack)), _math(nt, "MULTIPLY", crack, 0.7))
    nt.links.new(r3, p.inputs["Roughness"])
    p.inputs["Specular IOR Level"].default_value = 0.6
    _bump(nt, _math(nt, "SUBTRACT", _math(nt, "MULTIPLY", grain, 0.8), crack), 0.5, 0.02, p)
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


def sidewalk():
    """Damp concrete slabs: 1.5 m joints with a dark open seam, colour drift, damp patches, small dark spots (gum, oil)."""
    m, nt = _nodes("Prev_DampConcrete")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pos = nt.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    big = _noise(nt, pos, 0.3, 5.0)
    grain = _noise(nt, pos, 55.0, 3.0)
    spot = nt.nodes.new("ShaderNodeTexVoronoi")
    spot.feature = "F1"
    spot.inputs["Scale"].default_value = 9.0
    nt.links.new(pos, spot.inputs["Vector"])
    gum = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 0.085, spot.outputs["Distance"]), 40.0, clamp=True)
    gum = _math(nt, "MULTIPLY", gum, _math(nt, "SUBTRACT", _noise(nt, pos, 2.2, 2.0), 0.52), clamp=True)
    gum = _math(nt, "MULTIPLY", gum, 8.0, clamp=True)
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset, br.squash = 0.0, 1.0
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.02
    br.inputs["Mortar Smooth"].default_value = 0.3
    br.inputs["Brick Width"].default_value = 1.5
    br.inputs["Row Height"].default_value = 1.5
    br.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1.0)
    br.inputs["Color2"].default_value = (0.9, 0.9, 0.9, 1.0)
    br.inputs["Mortar"].default_value = (0.0, 0.0, 0.0, 1.0)
    nt.links.new(pos, br.inputs["Vector"])
    joint = br.outputs["Fac"]          # 1 on a slab, 0 in the joint
    col = _ramp(nt, _math(nt, "ADD", _math(nt, "MULTIPLY", big, 0.7), _math(nt, "MULTIPLY", grain, 0.2)),
                [(0.2, (0.075, 0.072, 0.068)), (0.6, (0.115, 0.110, 0.102)), (0.9, (0.16, 0.152, 0.140))])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[7].default_value = (0.012, 0.012, 0.012, 1.0)
    nt.links.new(_math(nt, "ADD", _math(nt, "SUBTRACT", 1.0, joint), gum, clamp=True), mix.inputs[0])
    nt.links.new(col, mix.inputs[6])
    nt.links.new(mix.outputs[2], p.inputs["Base Color"])
    damp = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 0.5, big), 3.0, clamp=True)      # damp where the big noise dips
    rough = _math(nt, "ADD", _math(nt, "MULTIPLY", _math(nt, "ADD", 0.58, _math(nt, "MULTIPLY", grain, 0.25)), _math(nt, "SUBTRACT", 1.0, damp)),
                  _math(nt, "MULTIPLY", damp, 0.22))
    nt.links.new(rough, p.inputs["Roughness"])
    _bump(nt, _math(nt, "ADD", _math(nt, "MULTIPLY", grain, 0.6), _math(nt, "MULTIPLY", joint, 1.5)), 0.6, 0.02, p)
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


def paint(kind):
    """Road paint, worn: 35 percent of it lost to a noise mask (the asphalt shows through), satin where it is whole."""
    rgb = {"paint_yellow": (0.70, 0.52, 0.07), "paint_white": (0.72, 0.72, 0.67)}[kind]
    m, nt = _nodes("Prev_" + kind)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pos = nt.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    n = _noise(nt, pos, 6.0, 5.0)
    fine = _noise(nt, pos, 45.0, 3.0)
    worn = _math(nt, "SUBTRACT", _math(nt, "ADD", _math(nt, "MULTIPLY", n, 0.7), _math(nt, "MULTIPLY", fine, 0.3)), 0.34)
    worn = _math(nt, "MULTIPLY", worn, 12.0, clamp=True)                     # 1 where the paint is whole
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (0.03, 0.03, 0.03, 1.0)
    mix.inputs[7].default_value = (*rgb, 1.0)
    nt.links.new(worn, mix.inputs[0])
    nt.links.new(mix.outputs[2], p.inputs["Base Color"])
    nt.links.new(_math(nt, "ADD", 0.7, _math(nt, "MULTIPLY", worn, -0.25)), p.inputs["Roughness"])
    nt.links.new(worn, p.inputs["Alpha"])
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    m.blend_method = "BLEND" if hasattr(m, "blend_method") else None
    return m


def _flat(name, rgb, rough, metal=0.0, bump=None):
    m, nt = _nodes(name)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    pos = nt.nodes.new("ShaderNodeNewGeometry").outputs["Position"]
    n = _noise(nt, pos, 18.0, 5.0)
    col = nt.nodes.new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs[6].default_value = (*rgb, 1.0)
    col.inputs[7].default_value = (rgb[0] * 0.45, rgb[1] * 0.42, rgb[2] * 0.4, 1.0)
    nt.links.new(n, col.inputs[0])
    nt.links.new(col.outputs[2], p.inputs["Base Color"])
    nt.links.new(_math(nt, "ADD", rough - 0.12, _math(nt, "MULTIPLY", n, 0.24)), p.inputs["Roughness"])
    p.inputs["Metallic"].default_value = metal
    if bump:
        _bump(nt, n, bump, 0.01, p)
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    return m


def materials():
    return {
        "asphalt": asphalt(), "walk": sidewalk(), "paint_yellow": paint("paint_yellow"), "paint_white": paint("paint_white"),
        "gutter": _flat("Prev_Gutter", (0.020, 0.019, 0.017), 0.8, bump=0.6),
        "patch": _flat("Prev_Patch", (0.016, 0.016, 0.017), 0.62, bump=0.3),
        "patch_trench": _flat("Prev_PatchTrench", (0.045, 0.044, 0.042), 0.5, bump=0.25),
        "iron": _flat("Prev_CastIron", (0.045, 0.040, 0.036), 0.55, metal=0.85, bump=0.5),
        "seam": _flat("Prev_Seam", (0.012, 0.012, 0.012), 0.9),
    }


def build(col, M=None):
    """The dressing as thin shapes in collection `col`. Returns the number made."""
    import bpy
    from mi import geo, scene
    M = M or materials()
    n = 0
    for kind, x, y, sx, sy, rot in items():
        if kind == "manhole":
            ob = geo.cylinder(0.45, 0.012, segments=40, name="PrevManhole")
            z0, mkey = 0.0, "iron"
        elif kind == "drain":
            ob = geo.box((sx, sy, 0.012), bevel=0.003, name="PrevDrain")
            z0, mkey = 0.0, "iron"
        elif kind in ("paint_yellow", "paint_white"):
            ob = geo.box((sx, sy, 0.004), bevel=0.0, name="PrevPaint")
            z0, mkey = 0.0, kind
        elif kind == "seam":
            ob = geo.box((sx, sy, 0.012), bevel=0.0, name="PrevSeam")
            z0, mkey = 0.15, "seam"
        else:
            ob = geo.box((sx, sy, 0.006), bevel=0.0, name="Prev" + kind.title())
            z0, mkey = 0.0, kind
        geo.transform(ob, loc=(x, y, z0), rot=(0, 0, rot))
        ob.data.materials.append(M[mkey])
        scene.link(ob, col)
        n += 1
    return n


if __name__ == "__main__":
    print("street dressing:", write_json(), "rows ->", OUT_JSON)
