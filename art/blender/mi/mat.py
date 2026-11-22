"""Physically based procedural materials as node groups, plus the texture-set material that replaces them.

Two ways to get a material, same wear interface on both:

    m = mat.make("MI_Asphalt_Aged", "asphalt", Cracks=0.4)           # procedural, real-world scale, never stretches
    m = mat.from_texture_set("art/out/textures/TS_Asphalt_Aged")     # baked or scanned T_*_BC/N/ORM/H files

Every surface reads the mesh colour attribute 'Wear' (geo.ensure_wear / geo.wear_from_geometry):
    R cavity dirt, G edge wear, B leak streaks, A splash-back (props) or wetness (ground)
and has uniform controls of the same names plus 'Wetness' (0 dry .. 1 standing water).

Scale: 1 unit = 1 m. Procedural noise is driven by object (or world) position; lattices and directional
detail (brick courses, broom finish, wood grain) by the UV map in metres: world-scale UVs from
geo.uv_world_box, where 1 UV unit = `tile_m`. Heights are metres, so bump strength is physical.

Albedo ranges kept: charcoal 0.02-0.05, aged asphalt 0.06-0.12, concrete 0.35-0.5, white paint <= 0.8.
Metallic is 1 only where bare metal shows.

Seamless tiling: mat.make(..., tile=2.0) builds the same graph on a 4D torus embedding of the UV square, so a bake
over UV 0..1 wraps exactly (see bake.bake_tiling_set).
"""
import math
import os

import bpy

from . import geo as _geo

# ======================================================================================================== node DSL


def _sock(coll, key):
    if isinstance(key, int):
        return coll[key]
    for s in coll:
        if s.identifier == key:
            return s
    for s in coll:
        if s.name == key and s.enabled:
            return s
    return coll[key]


def _is_sock(x):
    return isinstance(x, bpy.types.NodeSocket)


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class G:
    """Tiny expression builder over a node tree. Values are python numbers / tuples or output sockets;
    operations on plain numbers are folded in python, so graphs stay small.

        g = G(tree)
        n = g.noise(co, scale=40, detail=3)          # -> socket
        m = g.sstep(0.4, 0.6, n)                     # smoothstep
        c = g.mixc(m, (0.05, 0.05, 0.05), (0.2, 0.18, 0.15))
    """

    def __init__(self, tree):
        self.t = tree
        self.n = tree.nodes
        self.l = tree.links
        self._i = 0

    # ---- plumbing
    def node(self, idname, **props):
        nd = self.n.new(idname)
        for k, v in props.items():
            setattr(nd, k, v)
        nd.location = ((self._i // 14) * 190, -(self._i % 14) * 150)
        self._i += 1
        return nd

    def put(self, sock, value):
        """Link a socket or set a default. Scalars widen to colours/vectors as needed."""
        if value is None:
            return
        if _is_sock(value):
            self.l.new(value, sock)
            return
        t = sock.type
        if t == "RGBA":
            if _num(value):
                value = (value, value, value, 1.0)
            elif len(value) == 3:
                value = (*value, 1.0)
        elif t == "VECTOR":
            if _num(value):
                value = (value, value, value)
            else:
                value = tuple(value)[:3]
        elif t in ("VALUE", "INT"):
            if not _num(value):
                value = sum(value[:3]) / 3.0
        sock.default_value = value

    # ---- scalar math
    _FOLD = {
        "ADD": lambda a, b: a + b, "SUBTRACT": lambda a, b: a - b, "MULTIPLY": lambda a, b: a * b,
        "DIVIDE": lambda a, b: a / b if b else 0.0, "POWER": lambda a, b: math.pow(max(a, 0.0), b),
        "MINIMUM": min, "MAXIMUM": max, "LESS_THAN": lambda a, b: 1.0 if a < b else 0.0,
        "GREATER_THAN": lambda a, b: 1.0 if a > b else 0.0, "MODULO": lambda a, b: math.fmod(a, b) if b else 0.0,
    }
    _FOLD1 = {"ABSOLUTE": abs, "FLOOR": math.floor, "FRACT": lambda a: a - math.floor(a), "SINE": math.sin,
              "COSINE": math.cos, "SQRT": lambda a: math.sqrt(max(a, 0.0)), "ROUND": round, "SIGN": lambda a: (a > 0) - (a < 0)}

    def math(self, op, a, b=None, c=None, clamp=False):
        if _num(a) and (b is None or _num(b)) and c is None:
            if b is None and op in self._FOLD1:
                r = float(self._FOLD1[op](a))
                return min(1.0, max(0.0, r)) if clamp else r
            if b is not None and op in self._FOLD:
                r = float(self._FOLD[op](a, b))
                return min(1.0, max(0.0, r)) if clamp else r
        # cheap identities: keeps graphs small and lets Cycles drop unused branches
        if not clamp:
            if op == "MULTIPLY" and (a == 0 and _num(a) or b == 0 and _num(b)):
                return 0.0
            if op == "MULTIPLY" and _num(b) and b == 1:
                return a
            if op == "MULTIPLY" and _num(a) and a == 1:
                return b
            if op in ("ADD", "SUBTRACT") and _num(b) and b == 0:
                return a
            if op == "ADD" and _num(a) and a == 0:
                return b
        nd = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.put(nd.inputs[0], a)
        if b is not None:
            self.put(nd.inputs[1], b)
        if c is not None:
            self.put(nd.inputs[2], c)
        return nd.outputs[0]

    def add(self, a, b, *more):
        r = self.math("ADD", a, b)
        for m in more:
            r = self.math("ADD", r, m)
        return r

    def sub(self, a, b):
        return self.math("SUBTRACT", a, b)

    def mul(self, a, b, *more):
        r = self.math("MULTIPLY", a, b)
        for m in more:
            r = self.math("MULTIPLY", r, m)
        return r

    def div(self, a, b):
        return self.math("DIVIDE", a, b)

    def pow(self, a, b):
        return self.math("POWER", a, b)

    def min(self, a, b):
        return self.math("MINIMUM", a, b)

    def max(self, a, b):
        return self.math("MAXIMUM", a, b)

    def abs(self, a):
        return self.math("ABSOLUTE", a)

    def floor(self, a):
        return self.math("FLOOR", a)

    def fract(self, a):
        return self.math("FRACT", a)

    def mod(self, a, b):
        return self.math("FLOORED_MODULO", a, b)

    def sin(self, a):
        return self.math("SINE", a)

    def cos(self, a):
        return self.math("COSINE", a)

    def gt(self, a, b):
        return self.math("GREATER_THAN", a, b)

    def lt(self, a, b):
        return self.math("LESS_THAN", a, b)

    def sat(self, a):
        return self.clamp(a)

    def clamp(self, a, lo=0.0, hi=1.0):
        if _num(a):
            return min(hi, max(lo, a))
        nd = self.node("ShaderNodeClamp")
        self.put(nd.inputs["Value"], a)
        nd.inputs["Min"].default_value = lo
        nd.inputs["Max"].default_value = hi
        return nd.outputs[0]

    def inv(self, a):
        return self.math("SUBTRACT", 1.0, a)

    def remap(self, x, a, b, c=0.0, d=1.0, smooth=False, clamp=True):
        """Map x from [a, b] to [c, d]; smooth=True is a smoothstep."""
        if all(_num(q) for q in (x, a, b, c, d)):
            t = (0.0 if x < a else 1.0) if a == b else (x - a) / (b - a)
            if clamp or smooth:
                t = min(1.0, max(0.0, t))
            if smooth:
                t = t * t * (3.0 - 2.0 * t)
            return c + (d - c) * t
        nd = self.node("ShaderNodeMapRange", clamp=clamp, interpolation_type="SMOOTHSTEP" if smooth else "LINEAR")
        self.put(nd.inputs["Value"], x)
        self.put(nd.inputs["From Min"], a)
        self.put(nd.inputs["From Max"], b)
        self.put(nd.inputs["To Min"], c)
        self.put(nd.inputs["To Max"], d)
        return nd.outputs[0]

    def sstep(self, lo, hi, x):
        """smoothstep(lo, hi, x); lo > hi gives the falling edge."""
        if _num(lo) and _num(hi) and lo > hi:
            return self.remap(x, hi, lo, 1.0, 0.0, smooth=True)
        return self.remap(x, lo, hi, 0.0, 1.0, smooth=True)

    def lerp(self, f, a, b):
        """Scalar mix: a at f = 0, b at f = 1."""
        if _num(f):
            if f <= 0:
                return a
            if f >= 1:
                return b
        if _num(a) and _num(b) and a == b:
            return a
        if _num(f) and _num(a) and _num(b):
            return a + (b - a) * f
        nd = self.node("ShaderNodeMix", data_type="FLOAT", clamp_factor=True)
        self.put(_sock(nd.inputs, "Factor_Float"), f)
        self.put(_sock(nd.inputs, "A_Float"), a)
        self.put(_sock(nd.inputs, "B_Float"), b)
        return _sock(nd.outputs, "Result_Float")

    # ---- colour
    def mixc(self, f, a, b, blend="MIX"):
        """Colour mix (blend: MIX, MULTIPLY, OVERLAY, SCREEN, ADD, DARKEN, LIGHTEN, SOFT_LIGHT, COLOR ...)."""
        if _num(f) and f <= 0:
            return a
        if _num(f) and f >= 1 and blend == "MIX":
            return b
        nd = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_factor=True, clamp_result=False)
        self.put(_sock(nd.inputs, "Factor_Float"), f)
        self.put(_sock(nd.inputs, "A_Color"), a)
        self.put(_sock(nd.inputs, "B_Color"), b)
        return _sock(nd.outputs, "Result_Color")

    def tint(self, col, f):
        """Colour times a scalar (or times another colour)."""
        if _num(f) and f == 1:
            return col
        if _num(f) and not _is_sock(col):
            return tuple(ch * f for ch in col[:3]) if not _num(col) else col * f
        if _num(f) or (_is_sock(f) and f.type == "VALUE"):
            nd = self.node("ShaderNodeVectorMath", operation="SCALE")
            self.put(nd.inputs[0], col)
            self.put(nd.inputs["Scale"], f)
            return nd.outputs[0]
        return self.mixc(1.0, col, f, "MULTIPLY")

    def ramp(self, x, stops, interp="LINEAR"):
        """Colour ramp: stops = [(position, grey or (r, g, b)), ...] (2 to 32 stops)."""
        nd = self.node("ShaderNodeValToRGB")
        cr = nd.color_ramp
        cr.interpolation = interp
        els = cr.elements
        while len(els) < len(stops):
            els.new(0.5)
        for e, (pos, col) in zip(els, stops):
            e.position = pos
            e.color = (col, col, col, 1.0) if _num(col) else (*col[:3], 1.0)
        self.put(nd.inputs[0], x)
        return nd.outputs[0]

    def hsv(self, col, h=0.5, s=1.0, v=1.0, fac=1.0):
        nd = self.node("ShaderNodeHueSaturation")
        self.put(nd.inputs["Hue"], h)
        self.put(nd.inputs["Saturation"], s)
        self.put(nd.inputs["Value"], v)
        self.put(_sock(nd.inputs, "Fac"), fac)
        self.put(nd.inputs["Color"], col)
        return nd.outputs[0]

    def lum(self, col):
        nd = self.node("ShaderNodeRGBToBW")
        self.put(nd.inputs[0], col)
        return nd.outputs[0]

    def sep_rgb(self, col):
        nd = self.node("ShaderNodeSeparateColor")
        self.put(nd.inputs[0], col)
        return nd.outputs[0], nd.outputs[1], nd.outputs[2]

    # ---- vectors
    def sep(self, v):
        nd = self.node("ShaderNodeSeparateXYZ")
        self.put(nd.inputs[0], v)
        return nd.outputs[0], nd.outputs[1], nd.outputs[2]

    def comb(self, x=0.0, y=0.0, z=0.0):
        nd = self.node("ShaderNodeCombineXYZ")
        self.put(nd.inputs[0], x)
        self.put(nd.inputs[1], y)
        self.put(nd.inputs[2], z)
        return nd.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        nd = self.node("ShaderNodeVectorMath", operation=op)
        self.put(nd.inputs[0], a)
        if b is not None:
            self.put(nd.inputs[1], b)
        if scale is not None:
            self.put(nd.inputs["Scale"], scale)
        return nd.outputs["Value"] if op in ("LENGTH", "DISTANCE", "DOT_PRODUCT") else nd.outputs[0]

    # ---- textures (co is a Co: vector + optional W)
    def noise(self, co, scale=5.0, detail=2.0, rough=0.5, lac=2.0, distortion=0.0, out="Fac", kind="FBM"):
        """fBM noise, mean 0.5. scale = features per metre. out: 'Fac' or 'Color'."""
        nd = self.node("ShaderNodeTexNoise", noise_dimensions=co.dim, noise_type=kind, normalize=True)
        self.put(nd.inputs["Vector"], co.vec)
        if co.dim == "4D":
            self.put(nd.inputs["W"], co.w)
        self.put(nd.inputs["Scale"], scale)
        self.put(nd.inputs["Detail"], detail)
        self.put(nd.inputs["Roughness"], rough)
        self.put(nd.inputs["Lacunarity"], lac)
        self.put(nd.inputs["Distortion"], distortion)
        return _sock(nd.outputs, out)

    def voronoi(self, co, scale=5.0, feature="F1", randomness=1.0, smoothness=0.5, outs=("Distance",)):
        """Voronoi cells. feature: F1, SMOOTH_F1, DISTANCE_TO_EDGE, F2. outs: any of Distance, Color, Position.
        Returns one socket, or a tuple when several outs are asked for."""
        nd = self.node("ShaderNodeTexVoronoi", voronoi_dimensions=co.dim, feature=feature, distance="EUCLIDEAN")
        self.put(nd.inputs["Vector"], co.vec)
        if co.dim == "4D":
            self.put(nd.inputs["W"], co.w)
        self.put(nd.inputs["Scale"], scale)
        self.put(nd.inputs["Randomness"], randomness)
        if feature == "SMOOTH_F1":
            self.put(nd.inputs["Smoothness"], smoothness)
        res = tuple(_sock(nd.outputs, o) for o in outs)
        return res[0] if len(res) == 1 else res

    def white(self, vec, out="Value"):
        """White noise hashed from a vector (cell ids): one random number (or colour) per distinct input."""
        nd = self.node("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
        self.put(nd.inputs["Vector"], vec)
        return _sock(nd.outputs, out)

    def bump(self, height, normal=None, distance=1.0, strength=1.0):
        nd = self.node("ShaderNodeBump")
        nd.inputs["Strength"].default_value = strength
        nd.inputs["Distance"].default_value = distance
        self.put(nd.inputs["Height"], height)
        if normal is not None:
            self.put(nd.inputs["Normal"], normal)
        return nd.outputs[0]


class Co:
    """A texture coordinate: vector (+ W in tile mode). off(k) decorrelates lookups, scaled() stretches."""

    def __init__(self, g, vec, w=None, dim="3D"):
        self.g, self.vec, self.w, self.dim = g, vec, w, dim

    def off(self, k):
        """Same space, shifted by a constant: use a different k for every independent texture."""
        g = self.g
        v = g.vmath("ADD", self.vec, (17.31 * k, -9.17 * k, 5.73 * k))
        w = g.add(self.w, 3.37 * k) if self.w is not None else None
        return Co(g, v, w, self.dim)

    def scaled(self, sx, sy, sz, sw=None):
        g = self.g
        v = g.vmath("MULTIPLY", self.vec, (sx, sy, sz))
        w = g.mul(self.w, sz if sw is None else sw) if self.w is not None else None
        return Co(g, v, w, self.dim)

    def warp(self, amount, scale, k=0.0):
        """Domain warp: push the coordinate around by a vector noise (metres). Makes cracks and veins wander."""
        g = self.g
        src = self.off(31.0 + k)
        n = g.noise(src, scale=scale, detail=2.0, rough=0.5, out="Color")
        d = g.vmath("SUBTRACT", n, (0.5, 0.5, 0.5))
        v = g.vmath("ADD", self.vec, g.vmath("SCALE", d, scale=amount))
        w = self.w
        if w is not None:
            w = g.add(w, g.mul(g.sub(g.noise(src.off(3.0), scale=scale, detail=1.0), 0.5), amount))
        return Co(g, v, w, self.dim)


class Ctx:
    """What a surface function gets: coordinates, wear masks and its own parameters (all sockets).

    c.P                 isotropic position in metres (3D, or 4D torus in tile mode)
    c.streak(a, b)      P stretched for vertical streaks: a = frequency across, b = frequency down the wall
    c.uvdir(su, sv)     UV-aligned stretched space: broom marks, wood grain, brushed metal (u along the grain)
    c.u, c.v            UV in metres (lattices: bricks, flags, boards)
    c.dirt, c.wear, c.leak, c.splash     wear masks 0..1 (vertex colour + uniform control)
    c.p["Name"]         the surface's own parameters
    """

    def __init__(self, g, vec, w, uvm, tile):
        self.g = g
        self.tile = tile
        dim = "4D" if tile else "3D"
        self.P = Co(g, vec, w if tile else None, dim)
        self.u, self.v, _ = g.sep(uvm)
        self._uvm = uvm
        self.p = {}

    def streak(self, a, b):
        return self.P.scaled(a, a, b)

    def uvdir(self, su, sv):
        if self.tile:
            return self.P.scaled(su, su, sv)
        g = self.g
        return Co(g, g.comb(g.mul(self.u, su), g.mul(self.v, sv), 0.0), None, "2D")

    def cell_hash(self, cu, cv, k=0.0):
        """One random number per lattice cell (cu, cv)."""
        return self.g.white(self.g.comb(cu, cv, 7.77 + k))


# ====================================================================================================== registry

SURFACES = {}


class Surface:
    def __init__(self, fn, name, params, alpha, porosity, relief, doc, sample):
        self.fn, self.name, self.params, self.alpha = fn, name, params, alpha
        self.porosity, self.relief, self.doc, self.sample = porosity, relief, doc, sample


def surface(name, params=(), alpha="splash", porosity=0.3, relief=0.001, sample=None):
    """Register a surface function. params: [(name, default, min, max)], default a float or an (r, g, b).
    alpha: what the Wear alpha channel means for this surface: 'wet' (ground) or 'splash' (props, walls).
    porosity: how much it darkens when wet (asphalt 0.6, steel 0.05). relief: height that standing water must
    climb to cover the surface, metres. sample: parameter overrides for the materials sheet."""
    def deco(fn):
        norm = [(q[0], q[1], q[2] if len(q) > 2 else None, q[3] if len(q) > 3 else None) for q in params]
        SURFACES[name] = Surface(fn, name, norm, alpha, porosity, relief, (fn.__doc__ or "").strip(), sample or {})
        return fn
    return deco


COMMON = [("Dirt", 0.0, 0.0, 1.0), ("Edge Wear", 0.0, 0.0, 1.0), ("Leaks", 0.0, 0.0, 1.0), ("Splash", 0.0, 0.0, 1.0),
          ("Wetness", 0.0, 0.0, 1.0)]
MASKS = ["Mask Dirt", "Mask Wear", "Mask Leak", "Mask Alpha"]


def _iface(tree, name, kind, in_out="INPUT", default=None, lo=None, hi=None):
    s = tree.interface.new_socket(name, in_out=in_out, socket_type=kind)
    if default is not None:
        if kind == "NodeSocketColor" and len(default) == 3:
            default = (*default, 1.0)
        s.default_value = default
    if lo is not None and hasattr(s, "min_value"):
        s.min_value, s.max_value = lo, hi
    return s


def group(kind, tile=False, consts=None, alpha=None):
    """The node group for a surface kind ('asphalt', 'concrete', ...). Built once per file and per mode.
    Inputs: Vector, W, UV (metres), the four masks, the common controls, then the surface's own parameters.
    Outputs: Base Color, Metallic, Roughness, Normal, Height (m), Coat Weight (standing water), Emission.

    consts: {parameter name: value} to freeze into the graph. Frozen parameters are folded in python, so every
    feature they switch off disappears from the node tree (much faster to bake); the masks are frozen to 0 too.
    make(..., fold=True) uses this for tiling bakes."""
    import hashlib
    sf = SURFACES[kind]
    alpha = alpha or sf.alpha
    gname = "MG_%s%s" % (kind.title().replace("_", ""), "_Tile" if tile else "")
    if alpha != sf.alpha:
        gname += "_" + alpha.title()
    if consts is not None:
        gname += "_" + hashlib.md5(repr(sorted((k, repr(v)) for k, v in consts.items())).encode()).hexdigest()[:8]
    if gname in bpy.data.node_groups:
        return bpy.data.node_groups[gname]
    tree = bpy.data.node_groups.new(gname, "ShaderNodeTree")
    _iface(tree, "Vector", "NodeSocketVector")
    _iface(tree, "W", "NodeSocketFloat", default=0.0)
    _iface(tree, "UV", "NodeSocketVector")
    for m in MASKS:
        _iface(tree, m, "NodeSocketFloat", default=0.0, lo=0.0, hi=1.0)
    for (pn, dv, lo, hi) in COMMON + sf.params:
        if _num(dv):
            _iface(tree, pn, "NodeSocketFloat", default=float(dv), lo=lo, hi=hi)
        else:
            _iface(tree, pn, "NodeSocketColor", default=dv)
    for on, ot in (("Base Color", "NodeSocketColor"), ("Metallic", "NodeSocketFloat"), ("Roughness", "NodeSocketFloat"),
                   ("Normal", "NodeSocketVector"), ("Height", "NodeSocketFloat"), ("Coat Weight", "NodeSocketFloat"),
                   ("Emission", "NodeSocketColor"), ("Transmission", "NodeSocketFloat")):
        _iface(tree, on, ot, in_out="OUTPUT")
    g = G(tree)
    gi = g.node("NodeGroupInput")
    go = g.node("NodeGroupOutput")
    I = {s.name: s for s in gi.outputs if s.name}
    defaults = {pn: dv for (pn, dv, _lo, _hi) in COMMON + sf.params}

    def val(pn):
        if consts is None:
            return I[pn]
        v = consts.get(pn, defaults[pn])
        return float(v) if _num(v) else tuple(v)

    def mask(mn):
        return I[mn] if consts is None else 0.0

    c = Ctx(g, I["Vector"], I["W"], I["UV"], tile)
    c.dirt = g.clamp(g.add(mask("Mask Dirt"), val("Dirt")))
    c.wear = g.clamp(g.add(mask("Mask Wear"), val("Edge Wear")))
    c.leak = g.clamp(g.add(mask("Mask Leak"), val("Leaks")))
    if alpha == "wet":
        c.splash = val("Splash")
        wet = g.clamp(g.add(mask("Mask Alpha"), val("Wetness")))
    else:
        c.splash = g.clamp(g.add(mask("Mask Alpha"), val("Splash")))
        wet = val("Wetness")
    c.wet = wet
    c.p = {pn: val(pn) for (pn, _d, _lo, _hi) in sf.params}
    ch = sf.fn(g, c)
    col, rough, height = ch["color"], ch["rough"], ch.get("height", 0.0)
    metal = ch.get("metal", 0.0)
    # ---- water: damp darkening first, then a film that fills the low points and finally stands as a puddle
    por = ch.get("porosity", sf.porosity)
    damp = g.sstep(0.0, 0.55, wet) if _is_sock(wet) else (0.0 if wet <= 0 else min(1.0, wet / 0.55))
    col = g.tint(col, g.lerp(damp, 1.0, g.sub(1.0, g.mul(por, 0.62))))
    rough_wet = g.lerp(damp, rough, g.mul(rough, g.sub(1.0, g.mul(0.55, g.add(0.35, g.mul(por, 0.65))))))
    if _is_sock(wet) or wet > 0.38:
        level = g.mul(g.sstep(0.4, 1.0, wet), sf.relief * 1.35)
        coat = g.sstep(-0.00015, 0.00035, g.sub(level, g.sub(height, ch.get("floor", 0.0))))
        coat = g.mul(coat, g.sstep(0.38, 0.5, wet))
    else:
        coat = 0.0
    normal = g.bump(height) if (not tile and _is_sock(height)) else None
    O = {s.name: s for s in go.inputs if s.name}
    g.put(O["Base Color"], col)
    g.put(O["Metallic"], metal)
    g.put(O["Roughness"], rough_wet)
    if normal is not None:
        g.put(O["Normal"], normal)
    g.put(O["Height"], height)
    g.put(O["Coat Weight"], coat)
    g.put(O["Emission"], ch.get("emission", (0.0, 0.0, 0.0)))
    g.put(O["Transmission"], ch.get("transmission", 0.0))
    return tree


def make(name, kind, tile=None, space="OBJECT", masks=True, tile_m=2.0, fold=None, alpha=None, **params):
    """Create (or rebuild) a procedural material.

    name     material name: MI_<Surface>_<Variant> for tiling slots, M_<Asset> for unique sets
    kind     a key of mat.SURFACES
    tile     None for normal use. A number or (u, v) in metres builds the seamless variant for
             bake.bake_tiling_set: all noise wraps over that distance.
    space    'OBJECT' (default, the texture sticks to the object) or 'WORLD' (continuous across modules)
    masks    read the 'Wear' colour attribute (False: only the uniform controls)
    alpha    what the Wear alpha channel drives: 'wet' or 'splash' (default: the surface's own choice, see
             mat.SURFACES[kind].alpha). Use alpha='wet' on a prop that water runs down
    fold     freeze every parameter into the graph (default: True when tile is given). Features switched off
             by a zero parameter then cost nothing; the material can no longer be tweaked with set_params
    tile_m   metres per UV unit for lattices and directional detail (ignored when tile is given)
    params   any group input by name with spaces as underscores: Cracks=0.5, Paint_Color=(0.5, 0.4, 0.05)
    """
    sf = SURFACES[kind]
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.clear()
    g = G(nt)
    out = g.node("ShaderNodeOutputMaterial")
    bsdf = g.node("ShaderNodeBsdfPrincipled")
    grp = g.node("ShaderNodeGroup")
    if fold is None:
        fold = bool(tile)
    keyed = {k.replace("_", " "): v for k, v in params.items()}
    known = [pn for (pn, _d, _lo, _hi) in COMMON + sf.params]
    for key in keyed:
        if key not in known:
            raise KeyError("%s has no parameter '%s' (has: %s)" % (kind, key, ", ".join(known)))
    grp.node_tree = group(kind, tile=bool(tile), consts=keyed if fold else None, alpha=alpha)
    grp.name = grp.label = "Surface"
    uvn = g.node("ShaderNodeUVMap")
    if tile:
        tu, tv = (tile, tile) if _num(tile) else tile
        u, v, _ = g.sep(uvn.outputs[0])
        au, av = g.mul(u, 2 * math.pi), g.mul(v, 2 * math.pi)
        ru, rv = tu / (2 * math.pi), tv / (2 * math.pi)
        vec = g.comb(g.mul(g.cos(au), ru), g.mul(g.sin(au), ru), g.mul(g.cos(av), rv))
        g.put(grp.inputs["Vector"], vec)
        g.put(grp.inputs["W"], g.mul(g.sin(av), rv))
        g.put(grp.inputs["UV"], g.comb(g.mul(u, tu), g.mul(v, tv), 0.0))
        m["mi_tile_m"] = (float(tu), float(tv))
    else:
        if space == "WORLD":
            pos = g.node("ShaderNodeNewGeometry").outputs["Position"]
        else:
            pos = g.node("ShaderNodeTexCoord").outputs["Object"]
        g.put(grp.inputs["Vector"], pos)
        tu, tv = (tile_m, tile_m) if _num(tile_m) else tile_m
        g.put(grp.inputs["UV"], g.vmath("MULTIPLY", uvn.outputs[0], (tu, tv, 1.0)))
        if masks and not fold:
            att = g.node("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name=_geo.WEAR)
            r, gg, b = g.sep_rgb(att.outputs["Color"])
            g.put(grp.inputs["Mask Dirt"], r)
            g.put(grp.inputs["Mask Wear"], gg)
            g.put(grp.inputs["Mask Leak"], b)
            g.put(grp.inputs["Mask Alpha"], att.outputs["Alpha"])
    for key, val in keyed.items():
        g.put(grp.inputs[key], val)
    _wire_principled(g, bsdf, grp.outputs, sf)
    g.l.new(bsdf.outputs[0], out.inputs["Surface"])
    m["mi_kind"] = kind
    m["mi_relief"] = sf.relief
    m["mi_params"] = repr(sorted((k, repr(v)) for k, v in keyed.items()))
    return m


def _wire_principled(g, bsdf, o, sf=None, glass=False):
    g.l.new(o["Base Color"], bsdf.inputs["Base Color"])
    g.l.new(o["Metallic"], bsdf.inputs["Metallic"])
    g.l.new(o["Roughness"], bsdf.inputs["Roughness"])
    if o["Normal"].is_linked or True:
        g.l.new(o["Normal"], bsdf.inputs["Normal"])
    g.l.new(o["Coat Weight"], bsdf.inputs["Coat Weight"])
    bsdf.inputs["Coat Roughness"].default_value = 0.03
    bsdf.inputs["Coat IOR"].default_value = 1.33
    if sf is not None and sf.name == "glass":
        g.l.new(o["Transmission"], bsdf.inputs["Transmission Weight"])
        bsdf.inputs["IOR"].default_value = 1.52
    if "Emission" in o and sf is not None and sf.name in EMISSIVE:
        g.l.new(o["Emission"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0


EMISSIVE = set()


def surface_node(material):
    """The 'Surface' group node of a material made by make() (None for other materials)."""
    return material.node_tree.nodes.get("Surface") if material and material.node_tree else None


def principled(material):
    """The Principled BSDF that feeds the material output, or None."""
    nt = material.node_tree
    for n in nt.nodes:
        if n.bl_idname == "ShaderNodeOutputMaterial" and n.inputs["Surface"].is_linked:
            src = n.inputs["Surface"].links[0].from_node
            if src.bl_idname == "ShaderNodeBsdfPrincipled":
                return src
    for n in nt.nodes:
        if n.bl_idname == "ShaderNodeBsdfPrincipled":
            return n
    return None


def set_params(material, **params):
    """Change parameters of a material made by make(): mat.set_params(m, Wetness=0.6)."""
    grp = surface_node(material)
    g = G(material.node_tree)
    for k, val in params.items():
        s = grp.inputs[k.replace("_", " ")]
        for ln in list(s.links):
            material.node_tree.links.remove(ln)
        g.put(s, val)
    return material


# ============================================================================================== shared ingredients

RUST = [(0.0, (0.038, 0.022, 0.016)), (0.30, (0.072, 0.036, 0.021)), (0.60, (0.120, 0.056, 0.027)),
        (0.84, (0.185, 0.090, 0.038)), (1.0, (0.250, 0.140, 0.065))]
GRIME = (0.045, 0.040, 0.034)
DUST = (0.215, 0.195, 0.165)


def _rust(g, c, k=0.0):
    """Rust colour, roughness and pitting height for one position: (color, rough, height)."""
    n1 = g.noise(c.P.off(40 + k), scale=38.0, detail=4.0, rough=0.62)
    n2 = g.noise(c.P.off(41 + k), scale=260.0, detail=2.0, rough=0.5)
    t = g.clamp(g.add(g.mul(g.sub(n1, 0.5), 1.7), 0.42, g.mul(g.sub(n2, 0.5), 0.5)))
    col = g.ramp(t, RUST)
    rough = g.lerp(n2, 0.78, 0.96)
    h = g.mul(g.sub(n2, 0.5), 0.00022)
    return col, rough, h


def _grime(g, c, col, rough, amount, colour=GRIME, k=0.0):
    """Dark film that collects where the dirt mask says, broken up so it never reads as a gradient."""
    n = g.noise(c.P.off(50 + k), scale=9.0, detail=4.0, rough=0.6)
    m = g.sstep(0.25, 0.9, g.add(g.mul(amount, 1.25), g.mul(g.sub(n, 0.5), 0.55)))
    m = g.mul(m, g.sstep(0.0, 0.12, amount))
    col = g.mixc(g.mul(m, 0.88), col, colour)
    rough = g.lerp(m, rough, g.max(rough, 0.82))
    return col, rough, m


def _dust(g, c, col, rough, amount, colour=DUST, k=0.0):
    """Pale road dust thrown up from the ground: speckled, strongest where the splash mask is."""
    n = g.noise(c.P.off(60 + k), scale=22.0, detail=5.0, rough=0.7)
    sp = g.noise(c.P.off(61 + k), scale=140.0, detail=2.0, rough=0.6)
    m = g.sstep(0.35, 0.8, g.add(g.mul(amount, 0.95), g.mul(g.sub(n, 0.5), 0.5), g.mul(g.sub(sp, 0.5), 0.35)))
    m = g.mul(m, g.sstep(0.0, 0.15, amount))
    col = g.mixc(g.mul(m, 0.7), col, colour)
    rough = g.lerp(m, rough, 0.9)
    return col, rough, m


# ====================================================================================================== surfaces

@surface("asphalt", alpha="wet", porosity=0.62, relief=0.0016, params=[
    ("Aggregate Scale", 95.0, 30.0, 200.0), ("Age", 0.75, 0.0, 1.0), ("Cracks", 0.25, 0.0, 1.0),
    ("Alligator", 0.0, 0.0, 1.0), ("Sealed Cracks", 0.0, 0.0, 1.0), ("Patches", 0.0, 0.0, 1.0),
    ("Oil", 0.0, 0.0, 1.0), ("Paint", 0.0, 0.0, 1.0), ("Paint Color", (0.52, 0.36, 0.035)),
    ("Paint Wear", 0.35, 0.0, 1.0), ("Tint", (1.0, 1.0, 1.0))],
    sample={"Cracks": 0.6, "Sealed_Cracks": 0.5, "Oil": 0.25})
def asphalt(g, c):
    """Aged road asphalt: stone aggregate in a grey binder, hairline and alligator cracks, tar-sealed cracks,
    utility patches, oil, worn road paint. Wear mask = traffic: polish first, then fatigue cracking.
    Leak mask = oil drips. Dirt mask = fines and grime in the low spots. Alpha = wetness."""
    p, P = c.p, c.P
    age = p["Age"]
    macro = g.noise(P.off(1), scale=0.45, detail=4.0, rough=0.55)
    meso = g.noise(P.off(2), scale=4.5, detail=3.0, rough=0.6)
    grain = g.noise(P.off(3), scale=230.0, detail=1.0, rough=0.55)
    # ---- utility patches (newer, darker, finer mix) on a jittered lattice of the UV plane
    pu, pv = g.div(c.u, 3.3), g.div(c.v, 2.6)
    cu, cv = g.floor(pu), g.floor(pv)
    hr = g.white(g.comb(cu, cv, 3.3), out="Color")
    r1, r2, r3 = g.sep_rgb(hr)
    fu, fv = g.sub(g.fract(pu), g.lerp(r1, 0.35, 0.65)), g.sub(g.fract(pv), g.lerp(r2, 0.35, 0.65))
    du = g.sub(g.abs(fu), g.lerp(r3, 0.12, 0.26))
    dv = g.sub(g.abs(fv), g.lerp(r1, 0.14, 0.30))
    pd = g.max(g.mul(du, 3.3), g.mul(dv, 2.6))                       # signed distance to the patch edge, metres
    exists = g.mul(g.lt(r2, g.mul(p["Patches"], 0.9)), g.gt(p["Patches"], 0.001))
    patch = g.mul(g.sstep(0.004, -0.004, pd), exists)
    seam = g.mul(g.sstep(0.03, 0.012, g.abs(pd)), exists)             # saw cut, overbanded with tar
    # ---- aggregate: every voronoi cell is one crushed stone; binder and fine stone show where the stone stops
    ag_scale = g.lerp(patch, p["Aggregate Scale"], g.mul(p["Aggregate Scale"], 1.7))
    d1, c1 = g.voronoi(P.off(4).warp(0.0028, 140.0), scale=ag_scale, outs=("Distance", "Color"))
    rnd1, rnd1b, rnd1c = g.sep_rgb(c1)
    # the binder weathers away with age and traffic: more stone shows
    expose = g.clamp(g.add(g.mul(age, 0.75), g.mul(c.wear, 0.5), g.mul(g.sub(meso, 0.5), 0.35), g.mul(patch, -0.45)))
    rad = g.add(g.lerp(rnd1b, 0.30, 0.66), g.mul(expose, 0.16))
    stone = g.sstep(g.add(rad, 0.035), g.sub(rad, 0.035), d1)
    d2, c2 = g.voronoi(P.off(5), scale=g.mul(ag_scale, 2.6), outs=("Distance", "Color"))
    rnd2, rnd2b, _ = g.sep_rgb(c2)
    stone2 = g.mul(g.sstep(0.62, 0.50, g.add(d2, g.mul(rnd2b, 0.25))), g.inv(stone))
    stone_col = g.ramp(rnd1, [(0.0, (0.046, 0.046, 0.047)), (0.14, (0.070, 0.069, 0.067)), (0.42, (0.118, 0.114, 0.107)),
                              (0.68, (0.168, 0.160, 0.146)), (0.82, (0.215, 0.186, 0.142)), (0.93, (0.262, 0.250, 0.232)),
                              (1.0, (0.345, 0.335, 0.315))])
    stone_col = g.tint(stone_col, g.lerp(grain, 0.84, 1.14))
    stone2_col = g.ramp(rnd2, [(0.0, (0.050, 0.050, 0.049)), (0.55, (0.105, 0.100, 0.092)), (1.0, (0.225, 0.205, 0.175))])
    binder_fresh = g.mixc(grain, (0.024, 0.024, 0.025), (0.042, 0.041, 0.040))
    binder_aged = g.mixc(grain, (0.050, 0.049, 0.047), (0.082, 0.079, 0.074))
    binder = g.mixc(age, binder_fresh, binder_aged)
    film = g.lerp(expose, 0.62, 0.0)                                  # bitumen still coating the stone tops
    col = g.mixc(stone2, binder, stone2_col)
    col = g.mixc(g.mul(stone, g.inv(film)), col, stone_col)
    col = g.tint(col, g.mul(g.lerp(macro, 0.82, 1.18), g.lerp(meso, 0.90, 1.10)))
    col = g.tint(col, g.lerp(patch, 1.0, 0.70))
    dome = g.clamp(g.sub(1.0, g.div(d1, g.add(rad, 0.05))))
    relief = g.add(g.mul(stone, g.add(g.lerp(expose, 0.0005, 0.0011), g.mul(dome, 0.0004), g.mul(rnd1c, 0.0004))),
                   g.mul(stone2, 0.00045), g.mul(g.sub(grain, 0.5), 0.00022))
    rough = g.lerp(stone, 0.93, g.lerp(c.wear, g.lerp(rnd1c, 0.74, 0.86), 0.50))
    rough = g.add(rough, g.mul(g.sub(grain, 0.5), 0.07))
    # ---- hairline and block cracks: warped cell edges, only where a slow noise allows them
    crk_e = g.voronoi(P.off(6).warp(0.10, 2.0), scale=1.25, feature="DISTANCE_TO_EDGE")
    gate = g.sstep(0.0, 0.25, g.sub(g.add(g.noise(P.off(7), scale=1.3, detail=2.0), g.mul(p["Cracks"], 0.75)), 0.72))
    crack = g.mul(g.sstep(0.0065, 0.0015, crk_e), gate, g.gt(p["Cracks"], 0.001))
    # ---- alligator (fatigue) cracking from the Alligator control and the upper half of the wear mask
    fat = g.clamp(g.add(p["Alligator"], g.mul(g.sub(c.wear, 0.5), 2.0)))
    al_e = g.voronoi(P.off(8).warp(0.035, 6.0, 1.0), scale=7.5, feature="DISTANCE_TO_EDGE")
    al_gate = g.sstep(0.25, 0.75, g.add(fat, g.mul(g.sub(meso, 0.5), 0.5)))
    allig = g.mul(g.sstep(0.05, 0.012, al_e), al_gate, g.gt(fat, 0.001))
    crack_all = g.max(crack, allig)
    spall = g.max(g.mul(g.sstep(0.016, 0.004, crk_e), gate, g.gt(p["Cracks"], 0.001)),
                  g.mul(g.sstep(0.10, 0.03, al_e), al_gate, g.gt(fat, 0.001)))
    col = g.mixc(g.mul(spall, 0.35), col, (0.05, 0.048, 0.045))
    col = g.mixc(crack_all, col, (0.020, 0.019, 0.018))
    rough = g.lerp(crack_all, rough, 0.96)
    height = g.sub(g.sub(relief, g.mul(spall, 0.0012)), g.mul(crack_all, 0.006))
    # ---- oil: dark, slightly glossy, soaked in; from the Oil control and the leak mask
    oil_n = g.noise(P.off(9), scale=3.2, detail=4.0, rough=0.65)
    oil = g.sstep(0.42, 0.72, g.add(g.mul(g.max(p["Oil"], c.leak), 0.9), g.mul(g.sub(oil_n, 0.5), 0.75),
                                    g.mul(g.sub(meso, 0.5), 0.2)))
    oil = g.mul(oil, g.sstep(0.0, 0.08, g.max(p["Oil"], c.leak)))
    col = g.tint(col, g.lerp(oil, 1.0, 0.36))
    rough = g.lerp(oil, rough, g.mul(rough, 0.68))
    # ---- fines and grime settle between the stones
    dm = g.sstep(0.0, 0.5, g.sub(g.add(g.mul(c.dirt, 1.5), g.mul(g.sub(meso, 0.5), 0.4)), g.add(0.25, g.mul(relief, 420.0))))
    dirt_col = g.mixc(grain, (0.085, 0.075, 0.062), (0.150, 0.135, 0.112))
    col = g.mixc(g.mul(dm, 0.9), col, dirt_col)
    rough = g.lerp(dm, rough, 0.94)
    height = g.lerp(g.mul(dm, 0.75), height, g.max(height, 0.0007))
    # ---- tar: sealed cracks (wandering bands) and the patch seam
    sc_e = g.voronoi(P.off(10).warp(0.55, 0.5, 2.0), scale=0.34, feature="DISTANCE_TO_EDGE")
    sc_gate = g.sstep(0.0, 0.2, g.sub(g.add(g.noise(P.off(11), scale=0.3, detail=1.0), g.mul(p["Sealed Cracks"], 0.8)), 0.7))
    band = g.mul(g.sstep(0.0095, 0.0060, g.add(sc_e, g.mul(g.sub(meso, 0.5), 0.004))), sc_gate, g.gt(p["Sealed Cracks"], 0.001))
    tar = g.max(band, seam)
    tar_col = g.mixc(g.mul(grain, g.lerp(macro, 0.2, 0.6)), (0.016, 0.016, 0.018), (0.075, 0.070, 0.062))
    col = g.mixc(tar, col, tar_col)
    rough = g.lerp(tar, rough, g.lerp(grain, 0.28, 0.55))
    height = g.lerp(tar, height, g.add(0.0016, g.mul(g.sub(grain, 0.5), 0.0002)))
    # ---- road paint: stays in the pits, wears off the stone tops and with traffic
    pw = g.add(p["Paint Wear"], g.mul(c.wear, 0.9))
    keep = g.sub(g.add(1.0, g.mul(g.sub(macro, 0.5), 0.5), g.mul(g.sub(meso, 0.5), 0.6)),
                 g.add(g.mul(pw, 1.45), g.mul(relief, g.mul(pw, 420.0)), g.mul(g.sub(grain, 0.5), 0.25)))
    paint = g.mul(g.sstep(0.0, 0.14, keep), p["Paint"], g.inv(crack_all), g.gt(p["Paint"], 0.001))
    pit = g.sstep(0.0009, 0.0001, relief)                              # dirt and rubber stay in the low spots
    soil = g.mul(g.lerp(meso, 0.74, 1.0), g.lerp(c.dirt, 1.0, 0.55), g.lerp(oil, 1.0, 0.5), g.lerp(pit, 1.0, 0.80),
                 g.lerp(grain, 0.93, 1.06))
    col = g.mixc(paint, col, g.tint(p["Paint Color"], soil))
    rough = g.lerp(paint, rough, g.lerp(grain, 0.50, 0.66))
    height = g.add(g.lerp(g.mul(paint, 0.55), height, 0.0009), g.mul(paint, 0.0005))
    col = g.mixc(1.0, col, p["Tint"], "MULTIPLY")
    return {"color": col, "rough": g.clamp(rough, 0.05, 1.0), "height": height, "floor": -0.0002}


@surface("tar", alpha="wet", porosity=0.15, relief=0.0004, params=[("Dust Amount", 0.35, 0.0, 1.0), ("Matte", 0.0, 0.0, 1.0)])
def tar(g, c):
    """Bitumen crack sealant and overbanding: near-black, sun-softened and glossy, grit pressed into it."""
    P = c.P
    grit = g.noise(P.off(1), scale=520.0, detail=2.0, rough=0.6)
    flow = g.noise(P.off(2), scale=14.0, detail=3.0, rough=0.5)
    macro = g.noise(P.off(3), scale=1.1, detail=3.0, rough=0.5)
    dust = g.sstep(0.45, 0.85, g.add(g.mul(grit, 0.6), g.mul(macro, 0.5), g.mul(c.p["Dust Amount"], 0.5), g.mul(c.dirt, 0.6)))
    col = g.mixc(dust, (0.016, 0.016, 0.018), (0.082, 0.076, 0.066))
    rough = g.lerp(dust, g.lerp(flow, 0.20, 0.38), 0.75)
    rough = g.lerp(c.p["Matte"], rough, 0.93)                         # Matte = 1: dirt-packed crack filling
    height = g.add(g.mul(g.sub(flow, 0.5), 0.0006), g.mul(g.sub(grit, 0.5), 0.00025))
    return {"color": col, "rough": rough, "height": height}


@surface("concrete", alpha="wet", porosity=0.5, relief=0.0009, params=[
    ("Base Color", (0.43, 0.41, 0.375)), ("Broom", 0.6, 0.0, 1.0), ("Aggregate", 0.25, 0.0, 1.0),
    ("Stains", 0.35, 0.0, 1.0), ("Gum", 0.0, 0.0, 1.0), ("Cracks", 0.15, 0.0, 1.0),
    ("Joint Spacing", 0.0, 0.0, 6.0), ("Formwork", 0.0, 0.0, 1.0), ("Weathering", 0.3, 0.0, 1.0)],
    sample={"Gum": 0.6, "Joint_Spacing": 1.0, "Stains": 0.5})
def concrete(g, c):
    """Cast concrete: broom-finished sidewalk flags with tooled joints (Joint Spacing > 0), cast-in-place walls
    with form panel seams and tie holes (Formwork), weathering streaks, stains, chewing gum, craze cracks.
    Wear mask = abrasion exposing aggregate. Leak mask = rust-brown run-off. Alpha = wetness."""
    p, P = c.p, c.P
    macro = g.noise(P.off(1), scale=0.5, detail=4.0, rough=0.55)
    meso = g.noise(P.off(2), scale=5.5, detail=4.0, rough=0.62)
    fine = g.noise(P.off(3), scale=120.0, detail=2.0, rough=0.6)
    sand = g.noise(P.off(4), scale=300.0, detail=1.0, rough=0.6)
    # ---- flags: tooled joints on a lattice, each flag its own shade
    sp = g.max(p["Joint Spacing"], 0.05)
    has_j = g.gt(p["Joint Spacing"], 0.051)
    ju, jv = g.div(c.u, sp), g.div(c.v, sp)
    du = g.mul(g.abs(g.sub(g.fract(g.add(ju, 0.5)), 0.5)), sp)
    dv = g.mul(g.abs(g.sub(g.fract(g.add(jv, 0.5)), 0.5)), sp)
    jd = g.min(du, dv)                                                   # metres to the nearest joint line
    joint = g.mul(g.sstep(0.007, 0.0025, jd), has_j)
    lip = g.mul(g.sstep(0.03, 0.006, jd), has_j)                         # the tool's smooth margin
    flag_rnd = g.white(g.comb(g.floor(g.add(ju, 0.5)), g.floor(g.add(jv, 0.5)), 1.7), out="Color")
    f1, f2, _ = g.sep_rgb(flag_rnd)
    flag_tone = g.lerp(has_j, 1.0, g.lerp(f1, 0.86, 1.10))
    # ---- paste, sand and exposed stone
    col = g.tint(p["Base Color"], g.mul(g.lerp(macro, 0.86, 1.12), g.lerp(meso, 0.88, 1.10), flag_tone))
    col = g.tint(col, g.mul(g.lerp(sand, 0.84, 1.13), g.lerp(fine, 0.92, 1.07)))
    # sand grains at the surface: dark and pale specks a millimetre or two across
    kd, kc = g.voronoi(P.off(16), scale=170.0, outs=("Distance", "Color"))
    k1, k2, k3 = g.sep_rgb(kc)
    speck = g.sstep(g.lerp(k2, 0.14, 0.30), g.lerp(k2, 0.08, 0.20), kd)
    col = g.tint(col, g.lerp(g.mul(speck, g.lt(k1, 0.30)), 1.0, g.lerp(k3, 0.45, 0.75)))
    col = g.tint(col, g.lerp(g.mul(speck, g.gt(k1, 0.88)), 1.0, 1.32))
    # cement paste is never one colour: warm and cool patches a hand wide
    hue = g.noise(P.off(17), scale=9.0, detail=3.0, rough=0.6)
    col = g.mixc(g.mul(g.sstep(0.45, 0.75, hue), 0.22), col, g.mixc(1.0, col, (1.06, 0.99, 0.88), "MULTIPLY"))
    craze_e = g.voronoi(P.off(18).warp(0.02, 14.0, 3.0), scale=11.0, feature="DISTANCE_TO_EDGE")
    craze = g.mul(g.sstep(0.022, 0.004, craze_e), g.sstep(0.42, 0.62, g.noise(P.off(19), scale=2.3, detail=2.0)), g.lerp(p["Cracks"], 0.25, 1.0))
    col = g.tint(col, g.lerp(craze, 1.0, 0.72))
    sd, sc = g.voronoi(P.off(5), scale=85.0, outs=("Distance", "Color"))
    sr, sr2, _ = g.sep_rgb(sc)
    expose = g.clamp(g.add(g.mul(p["Aggregate"], 0.8), g.mul(c.wear, 0.9), g.mul(g.sub(meso, 0.5), 0.5), -0.25))
    stone = g.mul(g.sstep(0.5, 0.3, g.add(sd, g.mul(sr2, 0.25))), g.sstep(0.0, 0.5, expose))
    stone_col = g.ramp(sr, [(0.0, (0.16, 0.155, 0.15)), (0.4, (0.30, 0.285, 0.26)), (0.75, (0.40, 0.36, 0.30)),
                            (1.0, (0.52, 0.50, 0.46))])
    col = g.mixc(g.mul(stone, 0.85), col, stone_col)
    # ---- broom finish across the walking direction (u), and the trowelled margin by the joints
    broom_n = g.noise(c.uvdir(230.0, 4.0).off(6), scale=1.0, detail=1.0, rough=0.5)
    broom = g.mul(g.sub(broom_n, 0.5), p["Broom"], g.inv(lip))
    pits_d = g.voronoi(P.off(7), scale=110.0)
    pit_gate = g.sstep(0.55, 0.7, g.noise(P.off(8), scale=30.0, detail=2.0))
    pits = g.mul(g.sstep(0.26, 0.10, pits_d), pit_gate)
    height = g.add(g.mul(broom, 0.0007), g.mul(g.sub(fine, 0.5), 0.00035), g.mul(g.sub(sand, 0.5), 0.00018), g.mul(stone, 0.00025))
    height = g.sub(g.sub(height, g.mul(pits, 0.0012)), g.mul(craze, 0.0003))
    col = g.tint(col, g.lerp(pits, 1.0, 0.5))
    col = g.tint(col, g.lerp(g.mul(g.sstep(0.55, 0.2, broom_n), p["Broom"], g.inv(lip)), 1.0, 0.93))   # fines in the broom grooves
    rough = g.add(0.80, g.mul(g.sub(fine, 0.5), 0.14))
    rough = g.lerp(g.mul(c.wear, g.inv(stone)), rough, 0.68)
    # ---- form panels and tie holes for cast-in-place walls
    fw = p["Formwork"]
    pu_, pv_ = g.div(c.u, 1.22), g.div(c.v, 0.61)
    pdu = g.mul(g.abs(g.sub(g.fract(g.add(pu_, 0.5)), 0.5)), 1.22)
    pdv = g.mul(g.abs(g.sub(g.fract(g.add(pv_, 0.5)), 0.5)), 0.61)
    pseam = g.mul(g.sstep(0.004, 0.001, g.min(pdu, pdv)), fw)
    panel = g.white(g.comb(g.floor(g.add(pu_, 0.5)), g.floor(g.add(pv_, 0.5)), 4.1))
    tie = g.vmath("LENGTH", g.comb(g.sub(g.fract(g.div(c.u, 0.61)), 0.5), g.sub(g.fract(g.div(c.v, 0.61)), 0.5), 0.0))
    tie = g.mul(g.sstep(0.03, 0.022, tie), fw)
    col = g.tint(col, g.lerp(g.mul(fw, 1.0), 1.0, g.lerp(panel, 0.93, 1.05)))
    col = g.tint(col, g.lerp(tie, 1.0, 0.45))
    height = g.add(g.sub(height, g.mul(tie, 0.006)), g.mul(pseam, 0.0012))
    # ---- weathering: rain streaks down walls, blotchy water stains on flats
    streak = g.noise(c.streak(22.0, 0.7).off(9), scale=1.0, detail=3.0, rough=0.6)
    wstreak = g.mul(g.sstep(0.5, 0.78, streak), p["Weathering"], fw)
    blot = g.noise(P.off(10), scale=1.7, detail=5.0, rough=0.68)
    stain = g.mul(g.sstep(0.48, 0.66, g.add(blot, g.mul(g.sub(p["Stains"], 0.5), 0.45))), g.sstep(0.0, 0.1, p["Stains"]))
    col = g.tint(col, g.lerp(g.max(wstreak, g.mul(stain, 0.8)), 1.0, 0.66))
    col = g.mixc(g.mul(stain, 0.25), col, g.mixc(1.0, col, (0.95, 0.86, 0.70), "MULTIPLY"))
    # ---- craze and structural cracks
    cr_e = g.voronoi(P.off(11).warp(0.16, 1.6), scale=0.95, feature="DISTANCE_TO_EDGE")
    cr_gate = g.sstep(0.0, 0.2, g.sub(g.add(g.noise(P.off(12), scale=0.45, detail=2.0), g.mul(p["Cracks"], 0.8)), 0.72))
    crack = g.mul(g.sstep(0.0035, 0.0008, cr_e), cr_gate, g.gt(p["Cracks"], 0.001))
    col = g.mixc(crack, col, (0.035, 0.033, 0.03))
    height = g.sub(height, g.mul(crack, 0.004))
    # ---- joints: recessed, dirt-packed
    height = g.sub(g.lerp(g.mul(lip, 0.8), height, 0.0), g.mul(joint, 0.007))
    col = g.mixc(g.mul(joint, 0.85), col, (0.06, 0.055, 0.048))
    # ---- leak run-off: rust-brown, dirt: grey-brown film in the pores and around the joints
    ln_ = g.noise(P.off(13), scale=7.0, detail=4.0, rough=0.65)
    lk = g.mul(g.sstep(0.25, 0.8, g.add(c.leak, g.mul(g.sub(ln_, 0.5), 0.5))), g.sstep(0.0, 0.1, c.leak))
    col = g.mixc(g.mul(lk, 0.7), col, g.mixc(ln_, (0.20, 0.105, 0.045), (0.11, 0.07, 0.04)))
    dn = g.noise(P.off(14), scale=12.0, detail=4.0, rough=0.65)
    dm = g.sstep(0.2, 0.85, g.add(g.mul(c.dirt, 1.2), g.mul(g.sub(dn, 0.5), 0.6), g.mul(g.sub(meso, 0.5), 0.3)))
    dm = g.mul(dm, g.sstep(0.0, 0.1, c.dirt))
    col = g.mixc(g.mul(dm, 0.72), col, (0.115, 0.105, 0.09))
    rough = g.lerp(dm, rough, 0.9)
    # ---- chewing gum: flattened black discs, the signature of a New York sidewalk
    gd, gc = g.voronoi(P.off(15), scale=6.5, outs=("Distance", "Color"))
    g1, g2, g3 = g.sep_rgb(gc)
    grad = g.lerp(g2, 0.055, 0.125)
    gmask = g.mul(g.sstep(grad, g.mul(grad, 0.8), gd), g.lt(g1, g.mul(p["Gum"], 0.85)), g.gt(p["Gum"], 0.001))
    gum_col = g.mixc(g3, (0.022, 0.022, 0.023), (0.075, 0.072, 0.068))
    col = g.mixc(g.mul(gmask, 0.93), col, gum_col)
    rough = g.lerp(gmask, rough, 0.58)
    height = g.lerp(gmask, height, g.add(0.0006, g.mul(g.sub(sand, 0.5), 0.0001)))
    return {"color": col, "rough": g.clamp(rough, 0.05, 1.0), "height": height, "floor": -0.0003}


@surface("brick", alpha="splash", porosity=0.45, relief=0.004, params=[
    ("Brick Length", 0.2032, 0.1, 0.4), ("Brick Height", 0.0572, 0.03, 0.2), ("Joint", 0.0095, 0.004, 0.02),
    ("Color A", (0.235, 0.075, 0.048)), ("Color B", (0.330, 0.125, 0.075)), ("Color C", (0.115, 0.062, 0.052)),
    ("Mortar Color", (0.33, 0.31, 0.275)), ("Variation", 0.7, 0.0, 1.0), ("Chipping", 0.4, 0.0, 1.0),
    ("Efflorescence", 0.15, 0.0, 1.0), ("Soot", 0.25, 0.0, 1.0), ("Wrap U", 4096.0, 1.0, 4096.0),
    ("Wrap V", 4096.0, 1.0, 4096.0)],
    sample={"Efflorescence": 0.4, "Soot": 0.4})
def brick(g, c):
    """Running-bond brick with recessed mortar: New York common brick 203 x 57 mm on 9.5 mm joints. Per-brick
    colour, burnt headers, chipped arrises, wire-cut faces, efflorescence, soot. Needs world-scale UVs (u along
    the wall, v up). Dirt mask = soot, leak mask = white salt run-off, alpha = splash dirt at the foot."""
    p, P = c.p, c.P
    bl = g.add(p["Brick Length"], p["Joint"])
    bh = g.add(p["Brick Height"], p["Joint"])
    course = g.floor(g.div(c.v, bh))
    shift = g.mul(g.mod(course, 2.0), 0.5)
    bu = g.add(g.div(c.u, bl), shift)
    iu = g.floor(bu)
    fu, fv = g.fract(bu), g.fract(g.div(c.v, bh))
    idu, idv = g.mod(iu, p["Wrap U"]), g.mod(course, p["Wrap V"])
    rnd = g.white(g.comb(idu, idv, 2.2), out="Color")
    r1, r2, r3 = g.sep_rgb(rnd)
    edge_n = g.noise(P.off(1), scale=55.0, detail=3.0, rough=0.6)
    chip_n = g.noise(P.off(2), scale=16.0, detail=3.0, rough=0.6)
    du = g.mul(g.sub(0.5, g.abs(g.sub(fu, 0.5))), bl)
    dv = g.mul(g.sub(0.5, g.abs(g.sub(fv, 0.5))), bh)
    d = g.min(du, dv)                                               # metres from the cell edge
    wear_e = g.add(p["Chipping"], g.mul(c.wear, 0.8))
    d2 = g.sub(d, g.add(g.mul(g.sub(edge_n, 0.5), 0.004), g.mul(g.sstep(0.55, 0.8, chip_n), wear_e, 0.007)))
    half = g.mul(p["Joint"], 0.5)
    face = g.sstep(g.sub(half, 0.0008), g.add(half, 0.0030), d2)    # 1 on the brick face, 0 in the joint
    # ---- brick body colour
    t = g.lerp(p["Variation"], 0.5, r1)
    body = g.mixc(g.sstep(0.0, 0.62, t), p["Color A"], p["Color B"])
    body = g.mixc(g.mul(g.sstep(0.80, 0.97, r2), p["Variation"]), body, p["Color C"])
    body = g.tint(body, g.lerp(r3, 0.86, 1.12))
    drag = g.noise(c.uvdir(18.0, 620.0).off(3), scale=1.0, detail=2.0, rough=0.55)
    sandy = g.noise(P.off(4), scale=700.0, detail=2.0, rough=0.5)
    blot = g.noise(P.off(5), scale=24.0, detail=4.0, rough=0.65)
    body = g.tint(body, g.mul(g.lerp(sandy, 0.86, 1.10), g.lerp(blot, 0.88, 1.08)))
    kiln = g.mul(g.sstep(0.55, 0.9, g.noise(P.off(6), scale=11.0, detail=3.0)), 0.35)
    body = g.mixc(kiln, body, g.tint(body, 0.55))
    # ---- mortar: sandy, weathered back from the face
    m_n = g.noise(P.off(7), scale=300.0, detail=2.0, rough=0.6)
    mortar = g.tint(p["Mortar Color"], g.mul(g.lerp(m_n, 0.82, 1.12), g.lerp(blot, 0.9, 1.05)))
    col = g.mixc(face, mortar, body)
    rough = g.lerp(face, 0.93, g.add(0.80, g.mul(g.sub(sandy, 0.5), 0.12)))
    bulge = g.sstep(0.0, 0.012, g.sub(d2, half))                    # rounded arris
    height = g.add(g.mul(face, g.add(0.0028, g.mul(bulge, 0.0012))), g.mul(g.sub(drag, 0.5), g.mul(face, 0.0005)),
                   g.mul(g.sub(sandy, 0.5), 0.0003), g.mul(g.sub(m_n, 0.5), g.mul(g.inv(face), 0.0008)))
    height = g.sub(height, g.mul(g.sstep(0.6, 0.85, chip_n), wear_e, face, 0.002))
    # ---- efflorescence: salts carried out by water, blooming under leaks and at random
    ef_n = g.noise(P.off(8), scale=2.6, detail=5.0, rough=0.7)
    ef = g.sstep(0.5, 0.82, g.add(g.mul(ef_n, 0.75), g.mul(g.add(p["Efflorescence"], c.leak), 0.55), g.mul(g.sub(sandy, 0.5), 0.25)))
    ef = g.mul(ef, g.sstep(0.0, 0.08, g.add(p["Efflorescence"], c.leak)))
    col = g.mixc(g.mul(ef, 0.75), col, (0.58, 0.565, 0.54))
    # ---- soot and city grime: darker toward sheltered places, heavier in the joints
    so_n = g.noise(c.streak(9.0, 1.4).off(9), scale=1.0, detail=4.0, rough=0.65)
    so = g.sstep(0.3, 0.9, g.add(g.mul(g.add(p["Soot"], g.mul(c.dirt, 1.2)), 0.9), g.mul(g.sub(so_n, 0.5), 0.6), g.mul(g.inv(face), 0.15)))
    so = g.mul(so, g.sstep(0.0, 0.08, g.add(p["Soot"], c.dirt)))
    col = g.mixc(g.mul(so, 0.78), col, (0.040, 0.037, 0.034))
    col, rough, _ = _dust(g, c, col, rough, c.splash)
    return {"color": col, "rough": g.clamp(rough, 0.05, 1.0), "height": height, "floor": 0.0}


@surface("painted_steel", alpha="splash", porosity=0.06, relief=0.0003, params=[
    ("Paint Color", (0.30, 0.035, 0.03)), ("Paint Roughness", 0.36, 0.05, 1.0), ("Paint Metallic", 0.0, 0.0, 1.0),
    ("Primer Color", (0.24, 0.075, 0.05)), ("Chipping", 0.12, 0.0, 1.0), ("Rust", 0.15, 0.0, 1.0),
    ("Chalking", 0.2, 0.0, 1.0), ("Old Coat", (0.36, 0.33, 0.10))],
    sample={"Chipping": 0.45, "Rust": 0.35})
def painted_steel(g, c):
    """Many coats of enamel on steel or cast iron: chips to an older coat, to primer and to bare metal that rusts,
    rust bleeding down from chips and fasteners, grime in the creases, road dust at the foot.
    Wear mask = knocks and rubbing on exposed edges. Leak mask = rust run-off. Dirt mask = grime."""
    p, P = c.p, c.P
    big = g.noise(P.off(1), scale=5.0, detail=4.0, rough=0.6)
    mid = g.noise(P.off(2), scale=42.0, detail=5.0, rough=0.68)
    fine = g.noise(P.off(3), scale=330.0, detail=2.0, rough=0.5)
    peel = g.noise(P.off(4), scale=170.0, detail=2.0, rough=0.5)
    drive = g.add(g.mul(p["Chipping"], 0.5), g.mul(c.wear, 0.72))
    field = g.add(g.mul(g.sub(mid, 0.5), 0.95), g.mul(g.sub(big, 0.5), 0.55), g.mul(g.sub(fine, 0.5), 0.10), drive)
    gate = g.sstep(0.0, 0.06, drive)
    chip_old = g.mul(g.sstep(0.52, 0.535, field), gate)                # down to the previous coat
    chip_primer = g.mul(g.sstep(0.60, 0.615, field), gate)
    chip_metal = g.mul(g.sstep(0.68, 0.70, field), gate)
    chalk = g.mul(p["Chalking"], g.lerp(big, 0.5, 1.0))
    paint = g.mixc(g.mul(chalk, 0.35), p["Paint Color"], g.mixc(0.5, p["Paint Color"], (0.5, 0.5, 0.5)))
    paint = g.tint(paint, g.lerp(big, 0.90, 1.08))
    col = g.mixc(chip_old, paint, g.tint(p["Old Coat"], g.lerp(mid, 0.8, 1.05)))
    col = g.mixc(chip_primer, col, g.tint(p["Primer Color"], g.lerp(fine, 0.85, 1.1)))
    rough = g.lerp(chalk, p["Paint Roughness"], g.max(p["Paint Roughness"], 0.72))
    rough = g.add(rough, g.mul(g.sub(peel, 0.5), 0.05))
    rough = g.lerp(chip_primer, rough, 0.78)
    metal = g.mul(p["Paint Metallic"], g.inv(chip_old))
    # bare metal flashes on the freshest knocks, the rest of the exposed steel has already rusted
    rcol, rrough, rh = _rust(g, c)
    fresh = g.mul(chip_metal, g.sstep(0.55, 0.9, c.wear), g.sstep(0.45, 0.6, fine))
    rusted = g.mul(chip_metal, g.inv(fresh))
    col = g.mixc(rusted, col, rcol)
    col = g.mixc(fresh, col, (0.50, 0.48, 0.46))
    rough = g.lerp(rusted, rough, rrough)
    rough = g.lerp(fresh, rough, 0.36)
    metal = g.lerp(fresh, metal, 1.0)
    # rust creeping under the film around every chip, and surface rust blooming from the Rust control
    creep = g.mul(g.sstep(0.56, 0.68, g.add(field, g.mul(p["Rust"], 0.10))), gate, g.inv(chip_metal))
    bloom_n = g.noise(P.off(5), scale=75.0, detail=4.0, rough=0.7)
    bloom = g.mul(g.sstep(0.62, 0.8, g.add(bloom_n, g.mul(p["Rust"], 0.42), g.mul(g.sub(big, 0.5), 0.3), -0.2)),
                  g.sstep(0.0, 0.1, p["Rust"]))
    stain_m = g.max(g.mul(creep, 0.55), g.mul(bloom, 0.85))
    col = g.mixc(g.mul(stain_m, g.inv(chip_metal)), col, g.tint(rcol, 1.15))
    rough = g.lerp(g.mul(stain_m, g.inv(chip_metal)), rough, 0.82)
    # rust run-off under leaks: thin vertical streaks
    st = g.noise(c.streak(95.0, 2.2).off(6), scale=1.0, detail=3.0, rough=0.6)
    run = g.mul(g.sstep(0.18, 0.8, g.add(g.mul(c.leak, 1.05), g.mul(g.sub(st, 0.5), 0.75))), g.sstep(0.0, 0.08, c.leak))
    col = g.mixc(g.mul(run, 0.78), col, g.mixc(st, (0.27, 0.125, 0.045), (0.14, 0.060, 0.026)))
    rough = g.lerp(run, rough, 0.8)
    col, rough, gm = _grime(g, c, col, rough, c.dirt)
    col, rough, dm = _dust(g, c, col, rough, c.splash)
    metal = g.mul(metal, g.inv(g.max(gm, dm)))
    height = g.add(g.mul(g.sub(peel, 0.5), 0.00005),
                   g.mul(g.inv(chip_old), 0.00022), g.mul(g.inv(chip_primer), 0.00016), g.mul(g.inv(chip_metal), 0.00008),
                   g.mul(rusted, rh), g.mul(bloom, g.mul(g.sub(fine, 0.3), 0.00025)))
    return {"color": col, "rough": g.clamp(rough, 0.05, 1.0), "metal": g.clamp(metal), "height": height, "floor": 0.0002}


@surface("steel", alpha="splash", porosity=0.08, relief=0.0003, params=[
    ("Rust", 0.35, 0.0, 1.0), ("Mill Scale", 0.6, 0.0, 1.0), ("Scratches", 0.4, 0.0, 1.0)],
    sample={"Rust": 0.45})
def steel(g, c):
    """Raw structural steel: blue-grey mill scale flaking to bright metal, rust taking hold from the crevices,
    drawn scratches along u. Wear mask = rubbed bright. Dirt mask = rust and dirt in the crevices."""
    p, P = c.p, c.P
    big = g.noise(P.off(1), scale=3.5, detail=4.0, rough=0.62)
    mid = g.noise(P.off(2), scale=36.0, detail=5.0, rough=0.66)
    fine = g.noise(P.off(3), scale=420.0, detail=2.0, rough=0.5)
    scr = g.noise(c.uvdir(9.0, 900.0).off(4), scale=1.0, detail=2.0, rough=0.6)
    scratch = g.mul(g.sstep(0.68, 0.74, scr), p["Scratches"])
    scale_m = g.mul(g.sstep(0.42, 0.5, g.add(mid, g.mul(g.sub(p["Mill Scale"], 0.5), 0.5))), g.inv(g.sstep(0.3, 0.7, c.wear)))
    bright = (0.50, 0.49, 0.475)
    col = g.mixc(scale_m, bright, g.mixc(big, (0.085, 0.092, 0.105), (0.150, 0.155, 0.165)))
    rough = g.lerp(scale_m, g.lerp(fine, 0.30, 0.42), g.lerp(fine, 0.48, 0.62))
    col = g.mixc(scratch, col, (0.58, 0.57, 0.55))
    rough = g.lerp(scratch, rough, 0.3)
    rcol, rrough, rh = _rust(g, c)
    drive = g.add(g.mul(p["Rust"], 0.8), g.mul(c.dirt, 0.7), g.mul(c.leak, 0.8), g.mul(c.splash, 0.4))
    rm = g.sstep(0.44, 0.60, g.add(g.mul(g.sub(mid, 0.5), 0.9), g.mul(g.sub(big, 0.5), 0.6), drive))
    rm = g.mul(rm, g.sstep(0.0, 0.06, drive), g.inv(g.mul(g.sstep(0.55, 0.9, c.wear), 0.85)))
    thin = g.mul(g.sstep(0.36, 0.5, g.add(g.mul(g.sub(mid, 0.5), 0.9), drive)), g.inv(rm), g.sstep(0.0, 0.06, drive), 0.5)
    col = g.mixc(thin, col, g.tint(rcol, 1.2))
    col = g.mixc(rm, col, rcol)
    rough = g.lerp(g.max(rm, thin), rough, rrough)
    metal = g.inv(g.max(rm, g.mul(thin, 0.6)))
    col, rough, gm = _grime(g, c, col, rough, g.mul(c.dirt, 0.6))
    col, rough, dm = _dust(g, c, col, rough, c.splash)
    metal = g.mul(metal, g.inv(g.max(gm, dm)))
    height = g.add(g.mul(scale_m, 0.00012), g.mul(rm, g.add(0.00015, rh)), g.mul(scratch, -0.00004), g.mul(g.sub(fine, 0.5), 0.00003))
    return {"color": col, "rough": g.clamp(rough, 0.05, 1.0), "metal": g.clamp(metal), "height": height}


@surface("galvanised", alpha="splash", porosity=0.05, relief=0.0002, params=[
    ("Age", 0.4, 0.0, 1.0), ("Spangle Size", 0.018, 0.004, 0.06), ("Rust", 0.1, 0.0, 1.0)],
    sample={"Age": 0.5, "Rust": 0.2})
def galvanised(g, c):
    """Hot-dip galvanised steel: crystalline zinc spangle, dulling to matte grey with white-rust bloom as it ages,
    red rust where the zinc has gone (edges, scratches, leak paths)."""
    p, P = c.p, c.P
    sd, sc, sp_ = g.voronoi(P.off(1), scale=g.div(1.0, p["Spangle Size"]), outs=("Distance", "Color", "Position"))
    s1, s2, _ = g.sep_rgb(sc)
    big = g.noise(P.off(2), scale=2.5, detail=4.0, rough=0.6)
    mid = g.noise(P.off(3), scale=30.0, detail=5.0, rough=0.66)
    fine = g.noise(P.off(4), scale=380.0, detail=2.0, rough=0.5)
    age = g.clamp(g.add(p["Age"], g.mul(g.sub(big, 0.5), 0.4)))
    fresh = g.tint((0.78, 0.80, 0.82), g.lerp(s1, 0.72, 1.0))
    dull = g.tint((0.38, 0.39, 0.40), g.lerp(s1, 0.92, 1.04))
    col = g.mixc(age, fresh, dull)
    rough = g.lerp(age, g.lerp(s2, 0.22, 0.38), g.lerp(fine, 0.52, 0.66))
    wr = g.mul(g.sstep(0.55, 0.75, g.add(mid, g.mul(g.sub(age, 0.5), 0.45), g.mul(c.dirt, 0.3))), g.sstep(0.15, 0.4, age))
    col = g.mixc(g.mul(wr, 0.7), col, (0.62, 0.63, 0.63))
    rough = g.lerp(wr, rough, 0.78)
    metal = g.inv(g.mul(wr, 0.75))
    rcol, rrough, rh = _rust(g, c)
    drive = g.add(g.mul(p["Rust"], 0.7), g.mul(c.wear, 0.8), g.mul(c.leak, 0.9))
    rm = g.mul(g.sstep(0.56, 0.68, g.add(g.mul(g.sub(mid, 0.5), 0.9), g.mul(g.sub(big, 0.5), 0.5), drive)), g.sstep(0.0, 0.06, drive))
    col = g.mixc(rm, col, rcol)
    rough = g.lerp(rm, rough, rrough)
    metal = g.mul(metal, g.inv(rm))
    col, rough, gm = _grime(g, c, col, rough, c.dirt)
    col, rough, dm = _dust(g, c, col, rough, c.splash)
    metal = g.mul(metal, g.inv(g.max(gm, dm)))
    height = g.add(g.mul(g.sub(s1, 0.5), 0.00003), g.mul(wr, 0.00008), g.mul(rm, g.add(0.0001, rh)))
    return {"color": col, "rough": g.clamp(rough, 0.05, 1.0), "metal": g.clamp(metal), "height": height}


@surface("cast_iron", alpha="splash", porosity=0.12, relief=0.0006, params=[
    ("Rust", 0.5, 0.0, 1.0), ("Polish", 0.2, 0.0, 1.0), ("Pebble", 0.6, 0.0, 1.0)],
    sample={"Rust": 0.5})
def cast_iron(g, c):
    """Sand-cast iron (manhole covers, grates, old columns): pebbled skin under a dark brown-black oxide, rust in
    the recesses, graphite-bright metal where tyres and boots polish the high points (wear mask)."""
    p, P = c.p, c.P
    big = g.noise(P.off(1), scale=2.2, detail=4.0, rough=0.6)
    mid = g.noise(P.off(2), scale=26.0, detail=5.0, rough=0.66)
    peb = g.noise(P.off(3), scale=330.0, detail=2.0, rough=0.55)
    pitd = g.voronoi(P.off(4), scale=210.0)
    pits = g.mul(g.sstep(0.2, 0.07, pitd), g.sstep(0.55, 0.7, g.noise(P.off(5), scale=22.0, detail=2.0)))
    height = g.sub(g.mul(g.sub(peb, 0.5), g.mul(p["Pebble"], 0.00055)), g.mul(pits, 0.0007))
    oxide = g.mixc(mid, (0.040, 0.033, 0.029), (0.085, 0.066, 0.052))
    rcol, rrough, rh = _rust(g, c)
    drive = g.add(g.mul(p["Rust"], 0.75), g.mul(c.dirt, 0.6), g.mul(c.leak, 0.8))
    rm = g.mul(g.sstep(0.42, 0.75, g.add(g.mul(g.sub(mid, 0.5), 0.8), g.mul(g.sub(big, 0.5), 0.6), drive, g.mul(g.sub(0.5, peb), 0.3))),
               g.sstep(0.0, 0.06, drive))
    col = g.mixc(g.mul(rm, 0.85), oxide, rcol)
    rough = g.lerp(rm, g.lerp(peb, 0.62, 0.78), rrough)
    # polish: the tops of the pebbling go first, then whole raised faces
    pol = g.clamp(g.add(g.mul(p["Polish"], 0.6), g.mul(c.wear, 1.1)))
    pm = g.mul(g.sstep(0.42, 0.62, g.add(g.mul(pol, 0.85), g.mul(g.sub(peb, 0.5), 0.5), g.mul(g.sub(mid, 0.5), 0.25))), g.sstep(0.0, 0.08, pol))
    col = g.mixc(pm, col, g.mixc(mid, (0.30, 0.285, 0.27), (0.42, 0.40, 0.38)))
    rough = g.lerp(pm, rough, g.lerp(peb, 0.30, 0.44))
    metal = g.max(pm, g.mul(g.inv(rm), 0.35))
    col, rough, gm = _grime(g, c, col, rough, g.mul(c.dirt, 0.8))
    col, rough, dm = _dust(g, c, col, rough, c.splash)
    metal = g.mul(metal, g.inv(g.max(gm, dm)))
    height = g.add(height, g.mul(rm, rh))
    return {"color": col, "rough": g.clamp(rough, 0.05, 1.0), "metal": g.clamp(metal), "height": height, "floor": -0.0002}


@surface("rubber", alpha="splash", porosity=0.1, relief=0.0003, params=[
    ("Color", (0.024, 0.024, 0.026)), ("Roughness", 0.72, 0.1, 1.0), ("Age", 0.4, 0.0, 1.0)],
    sample={"Age": 0.5, "Dirt": 0.3})
def rubber(g, c):
    """Tyres, gaskets, hoses, mats: charcoal black, matte, greying and crazing with age, pale dust in every
    recess, a browner sheen where it is scuffed."""
    p, P = c.p, c.P
    big = g.noise(P.off(1), scale=4.0, detail=3.0, rough=0.6)
    fine = g.noise(P.off(2), scale=480.0, detail=2.0, rough=0.5)
    age = g.clamp(g.add(p["Age"], g.mul(g.sub(big, 0.5), 0.4)))
    col = g.mixc(g.mul(age, 0.6), p["Color"], (0.060, 0.058, 0.055))
    col = g.tint(col, g.lerp(fine, 0.9, 1.1))
    rough = g.add(g.lerp(age, p["Roughness"], g.max(p["Roughness"], 0.85)), g.mul(g.sub(fine, 0.5), 0.06))
    cz = g.voronoi(P.off(3).warp(0.004, 60.0), scale=95.0, feature="DISTANCE_TO_EDGE")
    craze = g.mul(g.sstep(0.05, 0.015, cz), g.sstep(0.5, 0.9, age))
    col = g.tint(col, g.lerp(craze, 1.0, 0.55))
    scuff = g.mul(g.sstep(0.3, 0.8, g.add(c.wear, g.mul(g.sub(big, 0.5), 0.4))), g.sstep(0.0, 0.08, c.wear))
    col = g.mixc(g.mul(scuff, 0.5), col, (0.075, 0.066, 0.058))
    rough = g.lerp(scuff, rough, 0.5)
    dn = g.noise(P.off(4), scale=15.0, detail=4.0, rough=0.65)
    dd = g.max(c.dirt, c.splash)
    dm = g.mul(g.sstep(0.25, 0.8, g.add(g.mul(dd, 1.1), g.mul(g.sub(dn, 0.5), 0.55))), g.sstep(0.0, 0.08, dd))
    col = g.mixc(g.mul(dm, 0.75), col, (0.17, 0.155, 0.135))
    rough = g.lerp(dm, rough, 0.92)
    height = g.sub(g.mul(g.sub(fine, 0.5), 0.00006), g.mul(craze, 0.00025))
    return {"color": col, "rough": g.clamp(rough, 0.05, 1.0), "height": height}


@surface("plastic", alpha="splash", porosity=0.02, relief=0.0002, params=[
    ("Color", (0.62, 0.20, 0.03)), ("Roughness", 0.40, 0.05, 1.0), ("Sun Fade", 0.3, 0.0, 1.0),
    ("Scratches", 0.4, 0.0, 1.0)],
    sample={"Sun_Fade": 0.4, "Scratches": 0.6, "Dirt": 0.25})
def plastic(g, c):
    """Moulded HDPE / polypropylene (barrels, crates, bins, cones): slight mould texture, scuffs and drawn
    scratches that turn pale and matte, chalky sun fade, grime in the recesses, road dust at the foot."""
    p, P = c.p, c.P
    big = g.noise(P.off(1), scale=3.0, detail=3.0, rough=0.6)
    tex = g.noise(P.off(2), scale=260.0, detail=2.0, rough=0.5)
    fade = g.clamp(g.mul(p["Sun Fade"], g.lerp(big, 0.6, 1.3)))
    col = g.mixc(g.mul(fade, 0.55), p["Color"], g.mixc(0.65, p["Color"], (0.62, 0.62, 0.62)))
    rough = g.add(g.lerp(fade, p["Roughness"], g.max(p["Roughness"], 0.7)), g.mul(g.sub(tex, 0.5), 0.05))
    s1 = g.noise(c.uvdir(6.0, 700.0).off(3), scale=1.0, detail=2.0, rough=0.6)
    s2 = g.noise(c.uvdir(520.0, 9.0).off(4), scale=1.0, detail=2.0, rough=0.6)
    amt = g.clamp(g.add(g.mul(p["Scratches"], 0.6), g.mul(c.wear, 0.8)))
    th = g.lerp(amt, 0.80, 0.60)
    scr = g.mul(g.max(g.sstep(th, g.add(th, 0.05), s1), g.mul(g.sstep(g.add(th, 0.06), g.add(th, 0.11), s2), 0.7)), g.sstep(0.0, 0.05, amt))
    scuff = g.mul(g.sstep(0.45, 0.85, g.add(c.wear, g.mul(g.sub(big, 0.5), 0.5))), g.sstep(0.0, 0.08, c.wear))
    mark = g.max(scr, g.mul(scuff, 0.6))
    col = g.mixc(g.mul(mark, 0.45), col, g.mixc(0.6, p["Color"], (0.75, 0.75, 0.75)))
    rough = g.lerp(mark, rough, 0.72)
    col, rough, _ = _grime(g, c, col, rough, c.dirt)
    col, rough, _ = _dust(g, c, col, rough, c.splash)
    height = g.sub(g.mul(g.sub(tex, 0.5), 0.00004), g.mul(scr, 0.00006))
    return {"color": col, "rough": g.clamp(rough, 0.05, 1.0), "height": height}


def _grain(g, c, su, sv, k, warp=0.0):
    """Wood figure: growth rings cut by the board face, stretched along u. Returns (bands 0..1, pores 0..1)."""
    base = c.uvdir(su, sv).off(k)
    if warp:
        base = base.warp(warp, 0.9, k)
    slow = g.noise(base, scale=1.0, detail=2.0, rough=0.55)
    bands = g.add(g.mul(g.sin(g.mul(slow, 95.0)), 0.5), 0.5)
    pores = g.noise(c.uvdir(su * 6.0, sv * 14.0).off(k + 1), scale=1.0, detail=2.0, rough=0.6)
    return bands, pores, slow


@surface("timber", alpha="splash", porosity=0.42, relief=0.0008, params=[
    ("Color", (0.46, 0.30, 0.15)), ("Weathered", 0.4, 0.0, 1.0), ("Knots", 0.4, 0.0, 1.0), ("Checks", 0.4, 0.0, 1.0)],
    sample={"Weathered": 0.6})
def timber(g, c):
    """Sawn softwood lumber (shed posts, pallets, joists): growth-ring figure along u, knots, drying checks,
    weathering from honey to silver-grey with raised grain. Needs UVs with u along the grain.
    Wear mask = fresh pale wood where it is splintered. Leak mask = dark water and nail stains."""
    p, P = c.p, c.P
    bands, pores, slow = _grain(g, c, 0.9, 26.0, 1.0, warp=0.02)
    big = g.noise(P.off(3), scale=1.6, detail=3.0, rough=0.6)
    kd, kc = g.voronoi(c.uvdir(1.6, 5.0).off(4), scale=1.0, outs=("Distance", "Color"))
    k1, _, _ = g.sep_rgb(kc)
    knot = g.mul(g.sstep(0.16, 0.05, kd), g.lt(k1, g.mul(p["Knots"], 0.5)))
    late = g.sstep(0.55, 0.9, bands)
    fresh = g.mixc(late, p["Color"], g.tint(p["Color"], 0.58))
    fresh = g.tint(fresh, g.lerp(pores, 0.9, 1.06))
    fresh = g.mixc(knot, fresh, (0.11, 0.058, 0.03))
    w = g.clamp(g.add(p["Weathered"], g.mul(g.sub(big, 0.5), 0.5)))
    grey = g.mixc(late, (0.33, 0.31, 0.285), (0.17, 0.16, 0.15))
    grey = g.tint(grey, g.lerp(pores, 0.85, 1.08))
    col = g.mixc(g.sstep(0.15, 0.85, w), fresh, grey)
    ck = g.noise(c.uvdir(1.3, 210.0).off(5), scale=1.0, detail=2.0, rough=0.5)
    check = g.mul(g.sstep(0.74, 0.79, ck), g.sstep(0.0, 0.2, g.add(p["Checks"], g.mul(w, 0.5))), g.sstep(0.2, 0.6, g.add(p["Checks"], slow)))
    col = g.mixc(check, col, (0.035, 0.03, 0.026))
    splinter = g.mul(g.sstep(0.35, 0.8, g.add(c.wear, g.mul(g.sub(pores, 0.5), 0.6))), g.sstep(0.0, 0.08, c.wear))
    col = g.mixc(g.mul(splinter, 0.8), col, g.tint(p["Color"], 1.25))
    st = g.noise(c.streak(40.0, 1.5).off(6), scale=1.0, detail=3.0, rough=0.6)
    lk = g.mul(g.sstep(0.25, 0.8, g.add(c.leak, g.mul(g.sub(st, 0.5), 0.6))), g.sstep(0.0, 0.08, c.leak))
    col = g.tint(col, g.lerp(lk, 1.0, 0.45))
    rough = g.lerp(w, g.lerp(late, 0.62, 0.52), 0.86)
    col, rough, _ = _grime(g, c, col, rough, c.dirt)
    col, rough, _ = _dust(g, c, col, rough, c.splash)
    height = g.sub(g.add(g.mul(late, g.lerp(w, 0.00012, 0.0007)), g.mul(g.sub(pores, 0.5), 0.00015), g.mul(knot, 0.0004)),
                   g.mul(check, 0.0025))
    return {"color": col, "rough": g.clamp(rough, 0.05, 1.0), "height": height}


@surface("plywood", alpha="splash", porosity=0.4, relief=0.0006, params=[
    ("Color", (0.50, 0.37, 0.21)), ("Weathered", 0.35, 0.0, 1.0), ("Paint", 0.0, 0.0, 1.0),
    ("Paint Color", (0.035, 0.105, 0.065)), ("Sheet Width", 1.22, 0.3, 3.0), ("Sheet Height", 2.44, 0.3, 3.0)],
    sample={"Weathered": 0.5})
def plywood(g, c):
    """Construction plywood (sidewalk sheds, hoardings, boarded windows): wide rotary-cut cathedral figure, sheet
    edges with a gap and edge swelling, weathering to grey, optional flaking paint (hunter green by default)."""
    p, P = c.p, c.P
    bands, pores, slow = _grain(g, c, 0.55, 6.5, 2.0, warp=0.06)
    big = g.noise(P.off(3), scale=1.3, detail=4.0, rough=0.6)
    su, sv = g.div(c.u, p["Sheet Width"]), g.div(c.v, p["Sheet Height"])
    sheet = g.white(g.comb(g.floor(su), g.floor(sv), 5.5), out="Color")
    h1, h2, _ = g.sep_rgb(sheet)
    eu = g.mul(g.sub(0.5, g.abs(g.sub(g.fract(su), 0.5))), p["Sheet Width"])
    ev_ = g.mul(g.sub(0.5, g.abs(g.sub(g.fract(sv), 0.5))), p["Sheet Height"])
    ed = g.min(eu, ev_)
    gap = g.sstep(0.0022, 0.0008, ed)
    edge = g.sstep(0.09, 0.0, g.add(ed, g.mul(g.sub(big, 0.5), 0.06)))
    late = g.sstep(0.5, 0.92, bands)
    face = g.mixc(late, p["Color"], g.tint(p["Color"], 0.62))
    face = g.tint(face, g.mul(g.lerp(pores, 0.9, 1.07), g.lerp(h1, 0.88, 1.08)))
    w = g.clamp(g.add(p["Weathered"], g.mul(g.sub(big, 0.5), 0.5), g.mul(edge, 0.35)))
    grey = g.tint(g.mixc(late, (0.36, 0.335, 0.30), (0.20, 0.185, 0.165)), g.lerp(pores, 0.85, 1.08))
    col = g.mixc(g.sstep(0.15, 0.85, w), face, grey)
    col = g.tint(col, g.lerp(g.mul(edge, w), 1.0, 0.6))
    rough = g.lerp(w, 0.62, 0.86)
    # paint film, flaking from the edges and with the wear mask
    fl = g.noise(P.off(4), scale=28.0, detail=4.0, rough=0.65)
    keep = g.sstep(0.35, 0.45, g.sub(g.add(fl, 0.55), g.add(g.mul(c.wear, 0.9), g.mul(edge, 0.35), g.mul(w, 0.25))))
    pm = g.mul(keep, p["Paint"], g.gt(p["Paint"], 0.001))
    col = g.mixc(pm, col, g.tint(p["Paint Color"], g.lerp(big, 0.85, 1.1)))
    rough = g.lerp(pm, rough, 0.5)
    col = g.mixc(gap, col, (0.03, 0.027, 0.024))
    st = g.noise(c.streak(30.0, 1.2).off(5), scale=1.0, detail=3.0, rough=0.6)
    lk = g.mul(g.sstep(0.25, 0.8, g.add(c.leak, g.mul(g.sub(st, 0.5), 0.6))), g.sstep(0.0, 0.08, c.leak))
    col = g.tint(col, g.lerp(lk, 1.0, 0.5))
    col, rough, _ = _grime(g, c, col, rough, c.dirt)
    col, rough, _ = _dust(g, c, col, rough, c.splash)
    height = g.sub(g.add(g.mul(late, g.lerp(w, 0.00008, 0.00045)), g.mul(g.sub(pores, 0.5), 0.0001), g.mul(edge, g.mul(w, 0.0006)),
                         g.mul(pm, 0.00012)), g.mul(gap, 0.004))
    return {"color": col, "rough": g.clamp(rough, 0.05, 1.0), "height": height}


@surface("glass", alpha="splash", porosity=0.0, relief=0.0001, params=[
    ("Tint", (0.90, 0.95, 0.93)), ("Roughness", 0.015, 0.0, 1.0), ("Film", 0.25, 0.0, 1.0)],
    sample={"Film": 0.4, "Dirt": 0.2})
def glass(g, c):
    """Window and bottle glass: clear with a faint green tint, a dusty film that kills the transmission where
    the dirt mask and the Film control put it, rain-wash streaks. Model panes with real thickness, or set
    'Thin Wall' on the Principled node for single-sided panes."""
    p, P = c.p, c.P
    big = g.noise(P.off(1), scale=2.0, detail=4.0, rough=0.6)
    st = g.noise(c.streak(60.0, 1.2).off(2), scale=1.0, detail=3.0, rough=0.6)
    sp = g.noise(P.off(3), scale=260.0, detail=2.0, rough=0.6)
    amt = g.clamp(g.add(g.mul(p["Film"], 0.55), g.mul(c.dirt, 0.9), g.mul(c.splash, 0.7)))
    film = g.mul(g.sstep(0.25, 0.95, g.add(g.mul(amt, 0.9), g.mul(g.sub(big, 0.5), 0.4), g.mul(g.sub(st, 0.5), 0.35), g.mul(g.sub(sp, 0.5), 0.2))),
                 g.sstep(0.0, 0.06, amt))
    col = g.mixc(film, p["Tint"], (0.30, 0.28, 0.25))
    rough = g.lerp(film, p["Roughness"], 0.55)
    return {"color": col, "rough": rough, "height": 0.0, "transmission": g.sub(1.0, g.mul(film, 0.85))}


@surface("road_paint", alpha="wet", porosity=0.3, relief=0.0012, params=[
    ("Paint Color", (0.52, 0.36, 0.035)), ("Paint Wear", 0.35, 0.0, 1.0), ("Age", 0.75, 0.0, 1.0)],
    sample={"Paint_Wear": 0.45})
def road_paint(g, c):
    """Road-marking paint over aged asphalt, as a worn blend layer: it survives in the pits between the stones and
    is scrubbed off their tops, more so where the wear mask says traffic runs. Yellow by default; white lines use
    Paint_Color=(0.62, 0.61, 0.58). Use it on the faces under a line; the asphalt around uses 'asphalt'."""
    sub = dict(c.p)
    c.p = {"Aggregate Scale": 95.0, "Age": sub["Age"], "Cracks": 0.25, "Alligator": 0.0, "Sealed Cracks": 0.0,
           "Patches": 0.0, "Oil": 0.0, "Paint": 1.0, "Paint Color": sub["Paint Color"], "Paint Wear": sub["Paint Wear"],
           "Tint": (1.0, 1.0, 1.0)}
    out = asphalt(g, c)
    c.p = sub
    return out


# ================================================================================================== texture sets

ROLES = ("BC", "N", "ORM", "H", "E")
EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".tga")


def find_set_files(directory):
    """{role: path} for the T_<Set>_<ROLE>.<ext> files in a directory (PNG, JPEG, TIFF, EXR or TGA)."""
    out = {}
    if not os.path.isdir(directory):
        return out
    for fn in sorted(os.listdir(directory)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in EXTS or not stem.startswith("T_"):
            continue
        role = stem.rsplit("_", 1)[-1].upper()
        if role in ROLES and role not in out:
            out[role] = os.path.join(directory, fn)
    return out


def _image(path, srgb):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
    return img


def _wet_group():
    """Shared water layer for texture-set materials (the procedural groups have the same logic built in)."""
    name = "MG_Wet"
    if name in bpy.data.node_groups:
        return bpy.data.node_groups[name]
    tree = bpy.data.node_groups.new(name, "ShaderNodeTree")
    _iface(tree, "Color", "NodeSocketColor")
    _iface(tree, "Roughness", "NodeSocketFloat", default=0.5)
    _iface(tree, "Height", "NodeSocketFloat", default=0.5)
    _iface(tree, "Wet", "NodeSocketFloat", default=0.0, lo=0.0, hi=1.0)
    _iface(tree, "Porosity", "NodeSocketFloat", default=0.5, lo=0.0, hi=1.0)
    _iface(tree, "Color", "NodeSocketColor", in_out="OUTPUT")
    _iface(tree, "Roughness", "NodeSocketFloat", in_out="OUTPUT")
    _iface(tree, "Coat Weight", "NodeSocketFloat", in_out="OUTPUT")
    g = G(tree)
    gi, go = g.node("NodeGroupInput"), g.node("NodeGroupOutput")
    col, rough, h, wet, por = gi.outputs[0], gi.outputs[1], gi.outputs[2], gi.outputs[3], gi.outputs[4]
    damp = g.sstep(0.0, 0.55, wet)
    c2 = g.tint(col, g.lerp(damp, 1.0, g.sub(1.0, g.mul(por, 0.62))))
    r2 = g.lerp(damp, rough, g.mul(rough, g.sub(1.0, g.mul(0.55, g.add(0.35, g.mul(por, 0.65))))))
    level = g.mul(g.sstep(0.4, 1.0, wet), 1.35)
    coat = g.mul(g.sstep(-0.1, 0.25, g.sub(level, h)), g.sstep(0.38, 0.5, wet))
    g.put(go.inputs[0], c2)
    g.put(go.inputs[1], r2)
    g.put(go.inputs[2], coat)
    return tree


def from_texture_set(directory, name=None, tile_m=None, masks=True, alpha="wet", blend=None, blend_start=0.5, porosity=0.5,
                     dirt_color=(0.10, 0.09, 0.075), wear_tint=(1.12, 1.12, 1.12), wear_rough=-0.12,
                     leak_color=(0.20, 0.105, 0.045), leak_rough=0.0, ao_strength=0.5, macro=0.12,
                     normal_strength=1.0, Wetness=0.0, uv_map="", tint=None, wear_metal=0.0,
                     wear_color=(0.56, 0.57, 0.58), blend_tile_m=None, blend_tint=None, dirt_rough=0.9):
    """Material from T_<Set>_BC / _N / _ORM (/ _H, _E) files on disk: baked by bake.py or dropped-in scans.
    It has the same wear interface as the procedural surfaces, so swapping one for the other changes nothing
    on the mesh:

        R dirt   darkens toward dirt_color, filling the low points of the height map first
        G wear   polish: multiplies the colour by wear_tint and shifts roughness by wear_rough as G goes 0 -> 0.5.
                 When `blend` is given (directory of e.g. TS_Asphalt_Cracked) the surface then height-blends to
                 that second set as G goes blend_start -> 1 (worn paint uses blend_start=0: no polish stage)
        B leak   stains toward leak_color and shifts roughness by leak_rough (oil: dark and a little glossy)
        A        wetness with height-driven puddles (alpha='wet') or pale road dust (alpha='splash')

    The same formulas are what the Unreal master material implements (README, 'Runtime layers').
    tile_m is only bookkeeping (stored on the material): UVs already carry the scale, 1 UV unit = one tile.
    macro: strength of the metre-scale brightness variation that hides the repeat (0 = off).
    tint: (r, g, b) multiplied into the base colour (creosote on a grey timber scan, the El's bluer green).
    wear_metal: 0..1, how far full G wear goes to bare polished metal of wear_color (rail heads, kerb noses).
    blend_tile_m: tile size of the blend set when it differs from tile_m (its UVs are rescaled to stay real size).
    blend_tint: tint of the blend set. dirt_rough: roughness the R film goes to."""
    files = find_set_files(directory)
    if "BC" not in files:
        raise FileNotFoundError("no T_*_BC.* in %s" % directory)
    set_name = os.path.basename(os.path.normpath(directory))
    m = bpy.data.materials.get(name or set_name) or bpy.data.materials.new(name or set_name)
    nt = m.node_tree
    nt.nodes.clear()
    g = G(nt)
    out = g.node("ShaderNodeOutputMaterial")
    bsdf = g.node("ShaderNodeBsdfPrincipled")
    uv = g.node("ShaderNodeUVMap", uv_map=uv_map).outputs[0]

    def tex(path, srgb, vec=None):
        nd = g.node("ShaderNodeTexImage", interpolation="Linear")
        nd.image = _image(path, srgb)
        g.l.new(vec if vec is not None else uv, nd.inputs["Vector"])
        return nd

    def read(fs, vec=None, tnt=None):
        bc = tex(fs["BC"], True, vec).outputs["Color"]
        if tnt is not None:
            bc = g.mixc(1.0, bc, tuple(tnt), "MULTIPLY")
        if "ORM" in fs:
            ao, ro, me = g.sep_rgb(tex(fs["ORM"], False, vec).outputs["Color"])
        else:
            ao, ro, me = 1.0, 0.6, 0.0
        nrm = tex(fs["N"], False, vec).outputs["Color"] if "N" in fs else (0.5, 0.5, 1.0)
        h = tex(fs["H"], False, vec).outputs["Color"] if "H" in fs else 0.5
        return bc, ao, ro, me, nrm, h

    bc, ao, ro, me, nrm, h = read(files, None, tint)
    if masks:
        att = g.node("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name=_geo.WEAR)
        mr, mg_, mb = g.sep_rgb(att.outputs["Color"])
        ma = att.outputs["Alpha"]
    else:
        mr = mg_ = mb = ma = 0.0
    pos = g.node("ShaderNodeNewGeometry").outputs["Position"]
    P = Co(g, pos)
    big = g.noise(P.off(1), scale=0.37, detail=3.0, rough=0.55)
    mid = g.noise(P.off(2), scale=3.1, detail=3.0, rough=0.6)
    if macro:
        bc = g.tint(bc, g.add(1.0, g.add(g.mul(g.sub(big, 0.5), 2.0 * macro), g.mul(g.sub(mid, 0.5), macro))))
        ro = g.clamp(g.add(ro, g.mul(g.sub(big, 0.5), macro * 0.6)))
    # ---- G: blend to a second set through the height maps, or generic polish
    if _is_sock(mg_) and (blend_start > 0 or not blend):
        top = blend_start if blend else 1.0
        f = g.sstep(0.0, top, g.add(mg_, g.mul(g.sub(mid, 0.5), g.mul(mg_, 0.5))))
        bc = g.mixc(f, bc, g.mixc(1.0, bc, wear_tint, "MULTIPLY"))
        ro = g.clamp(g.add(ro, g.mul(f, wear_rough)))
        if wear_metal:
            # bare metal where the wear is complete: the last third of the mask, broken up by the height map
            fm = g.mul(g.sstep(0.55, 0.9, g.add(mg_, g.mul(g.sub(h, 0.5), 0.25))), wear_metal)
            bc = g.mixc(fm, bc, tuple(wear_color))
            me = g.lerp(fm, me, 1.0)
    if blend and _is_sock(mg_):
        bfiles = find_set_files(blend)
        vec2 = None
        if blend_tile_m is not None and tile_m is not None:
            ta = (float(tile_m),) * 2 if _num(tile_m) else tuple(float(x) for x in tile_m)
            tb = (float(blend_tile_m),) * 2 if _num(blend_tile_m) else tuple(float(x) for x in blend_tile_m)
            if abs(ta[0] - tb[0]) > 1e-6 or abs(ta[1] - tb[1]) > 1e-6:
                mp = g.node("ShaderNodeMapping", vector_type="POINT")
                mp.inputs["Scale"].default_value = (ta[0] / tb[0], ta[1] / tb[1], 1.0)
                g.l.new(uv, mp.inputs["Vector"])
                vec2 = mp.outputs[0]
        bc2, ao2, ro2, me2, nrm2, h2 = read(bfiles, vec2, blend_tint)
        gb = g.remap(mg_, blend_start, 1.0, 0.0, 1.0)
        f = g.sstep(0.0, 0.22, g.sub(g.add(g.mul(gb, 1.35), g.mul(g.sub(mid, 0.5), 0.35)), g.add(0.2, g.mul(h2, 0.9))))
        f = g.mul(f, g.sstep(0.0, 0.05, gb))
        bc = g.mixc(f, bc, bc2)
        ro, me, ao = g.lerp(f, ro, ro2), g.lerp(f, me, me2), g.lerp(f, ao, ao2)
        nrm = g.mixc(f, nrm, nrm2)
        h = g.lerp(f, h, h2)
    # ---- B: leak stains
    if _is_sock(mb):
        f = g.mul(g.sstep(0.2, 0.8, g.add(mb, g.mul(g.sub(mid, 0.5), 0.45))), g.sstep(0.0, 0.05, mb))
        bc = g.mixc(g.mul(f, 0.7), bc, g.mixc(1.0, bc, tuple(min(1.0, c_ * 2.6) for c_ in leak_color), "MULTIPLY"))
        bc = g.mixc(g.mul(f, 0.35), bc, leak_color)
        if leak_rough:
            ro = g.clamp(g.add(ro, g.mul(f, leak_rough)))
    # ---- R: dirt in the low points
    if _is_sock(mr):
        # a film whose thickness follows the mask: thicker in the low points of the height map, broken up in
        # proportion to its own strength so clean areas stay clean and nothing turns into a hard-edged blotch
        f = g.clamp(g.mul(mr, g.add(g.lerp(h, 1.45, 0.75), g.mul(g.sub(mid, 0.5), 0.9), g.mul(g.sub(big, 0.5), 0.5))))
        f = g.sstep(0.0, 1.0, f)
        bc = g.mixc(g.mul(f, 0.88), bc, dirt_color)
        ro = g.lerp(f, ro, g.max(ro, dirt_rough))
        nrm = g.mixc(g.mul(f, 0.5), nrm, (0.5, 0.5, 1.0))
    if ao_strength:
        bc = g.tint(bc, g.lerp(ao_strength, 1.0, ao))
    # ---- A: water or dust
    coat = 0.0
    if alpha == "wet":
        wg = g.node("ShaderNodeGroup")
        wg.node_tree = _wet_group()
        wet = g.clamp(g.add(ma, Wetness)) if _is_sock(ma) else Wetness
        g.put(wg.inputs["Color"], bc)
        g.put(wg.inputs["Roughness"], ro)
        g.put(wg.inputs["Height"], h)
        g.put(wg.inputs["Wet"], wet)
        g.put(wg.inputs["Porosity"], porosity)
        bc, ro, coat = wg.outputs["Color"], wg.outputs["Roughness"], wg.outputs["Coat Weight"]
        wg.name = "Wet"
    elif _is_sock(ma):
        sp = g.noise(P.off(3), scale=120.0, detail=3.0, rough=0.65)
        f = g.mul(g.sstep(0.35, 0.8, g.add(g.mul(ma, 0.95), g.mul(g.sub(mid, 0.5), 0.4), g.mul(g.sub(sp, 0.5), 0.4))), g.sstep(0.0, 0.1, ma))
        bc = g.mixc(g.mul(f, 0.7), bc, DUST)
        ro = g.lerp(f, ro, 0.9)
        me = g.mul(me, g.inv(f))
    nm = g.node("ShaderNodeNormalMap", space="TANGENT", uv_map=uv_map)
    nm.inputs["Strength"].default_value = normal_strength
    g.put(nm.inputs["Color"], nrm)
    g.put(bsdf.inputs["Base Color"], bc)
    g.put(bsdf.inputs["Metallic"], me)
    g.put(bsdf.inputs["Roughness"], ro)
    g.l.new(nm.outputs[0], bsdf.inputs["Normal"])
    g.put(bsdf.inputs["Coat Weight"], coat)
    bsdf.inputs["Coat Roughness"].default_value = 0.03
    bsdf.inputs["Coat IOR"].default_value = 1.33
    if "E" in files:
        g.l.new(tex(files["E"], True).outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 1.0
    g.l.new(bsdf.outputs[0], out.inputs["Surface"])
    m["mi_set"] = set_name
    if tile_m is not None:
        m["mi_tile_m"] = (float(tile_m), float(tile_m)) if _num(tile_m) else tuple(float(x) for x in tile_m)
    return m


# ------------------------------------------------------------------------------------------------ scan catalogue

_CATALOGUE = None


def catalogue():
    """{set name: record} of art/scans/sets.json (tiling sets, HDRIs by slug, models by slug). Cached."""
    global _CATALOGUE
    if _CATALOGUE is None:
        import json
        from . import paths
        p = os.path.join(paths.art, "scans", "sets.json")
        _CATALOGUE = {}
        if os.path.exists(p):
            with open(p) as f:
                for rec in json.load(f).get("sets", []):
                    _CATALOGUE[rec.get("set") or rec.get("slug")] = rec
    return _CATALOGUE


def scan_info(set_name):
    """Catalogue record of a scanned set (tile_m, surface, orientation, measured ...), or None."""
    return catalogue().get(set_name)


def scan_tile(set_name, default=2.0):
    """(u, v) metres covered by one repeat of a set: the catalogue for scans, set.json for baked sets."""
    rec = scan_info(set_name)
    if rec and rec.get("tile_m"):
        t = rec["tile_m"]
        return (float(t[0]), float(t[1]))
    from . import paths
    js = os.path.join(paths.texture_set(set_name), "set.json")
    if os.path.exists(js):
        import json
        with open(js) as f:
            t = json.load(f).get("tile_m", default)
        return (float(t), float(t)) if _num(t) else (float(t[0]), float(t[1]))
    return (float(default), float(default))


def from_scan(set_name, name=None, blend=None, alpha="splash", **kw):
    """Material from a catalogued scan by name: mat.from_scan("TS_Steel_ScanPaintGreen", blend="TS_Steel_ScanRust").
    Textures come from art/out/textures/<Set>/ (art/scans/fetch.py puts them there), the real tile size from
    art/scans/sets.json; the material stores it as m["mi_tile_m"], which is what the UVs must be divided by
    (geo.uv_world_box(ob, mat.scan_tile(set)) or geo.uv_rescale_by_slot). Same wear-mask and wetness interface
    as from_texture_set, whose keyword arguments all pass through. blend: name of a second set (scan or baked)
    that G blends to; it keeps its own real tile size. Default slot name: MI_<Surface>_<Variant>."""
    from . import paths
    rec = scan_info(set_name)
    if rec is None:
        raise KeyError("%s is not in art/scans/sets.json" % set_name)
    d = paths.texture_set(set_name)
    if "BC" not in find_set_files(d):
        raise FileNotFoundError("%s has no textures in %s: run art/scans/fetch.py" % (set_name, d))
    if blend:
        kw.setdefault("blend_tile_m", scan_tile(blend))
    m = from_texture_set(d, name=name or "MI_" + set_name[3:], tile_m=scan_tile(set_name), alpha=alpha,
                         blend=paths.texture_set(blend) if blend else None, **kw)
    m["mi_scan"] = rec.get("slug", "")
    m["mi_alpha"] = alpha
    if blend:
        m["mi_blend_set"] = blend
    if kw.get("tint") is not None:
        m["mi_tint"] = tuple(float(c) for c in kw["tint"])
    return m


def flat(name, color=(0.5, 0.5, 0.5), rough=0.6, metal=0.0):
    """Plain constant material (stand-ins, backdrops, export stubs)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.clear()
    g = G(nt)
    out = g.node("ShaderNodeOutputMaterial")
    bsdf = g.node("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    g.l.new(bsdf.outputs[0], out.inputs["Surface"])
    return m


def sign_face(key, color=(0.5, 0.5, 0.5), rough=0.45):
    """Material M_Sign_<key>: a sign face or painted graphic on 0..1 UVs. It reads the set Sign_<key>
    (T_Sign_<key>_BC / _ORM / _E, drawn by assets/signs.py) when it exists, else a flat stand-in colour.
    An _E map is wired at strength 1 (the night value); m["mi_emit_day"] is the day factor."""
    from . import paths
    d = paths.texture_set("Sign_" + key)
    name = "M_Sign_" + key
    if "BC" in find_set_files(d):
        m = from_texture_set(d, name=name, masks=False, macro=0.0, ao_strength=0.0, alpha="none")
        js = os.path.join(d, "set.json")
        if os.path.exists(js):
            import json
            with open(js) as f:
                info = json.load(f)
            m["mi_emit_day"] = float(info.get("emissive_day", 0.3))
            if info.get("alpha"):
                bsdf = principled(m)
                img = next(n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeTexImage" and "_BC" in n.image.name)
                m.node_tree.links.new(img.outputs["Alpha"], bsdf.inputs["Alpha"])
        return m
    return flat(name, color, rough)


def library():
    """[(kind, one-line description, parameter names)] for every registered surface."""
    return [(k, s.doc.split("\n")[0], [p[0] for p in COMMON + s.params]) for k, s in SURFACES.items()]
